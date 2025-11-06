import codecs
import os
import re
import shutil
import sys
import tempfile
from logging import DEBUG, INFO, basicConfig, getLogger
from pathlib import Path
from typing import Any, ClassVar, Final, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    DirectoryPath,
    Field,
    NewPath,
    PrivateAttr,
    StrictBool,
    StrictStr,
    field_validator,
    model_validator,
)


class EncodingStr:
    """Represents a validated string that must be a valid text encoding name.

    Validates whether the provided string is a supported encoding.
    """

    def __init__(self, value: Any):
        self.__validate_value(value)
        self.__value: str = value

    def __str__(self) -> str:
        return self.__value

    @staticmethod
    def __validate_value(arg: Any) -> str:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')

        try:
            codecs.lookup(arg)
        except LookupError as err:
            raise ValueError(f'"{arg}" is not supported as an encoding string.') from err
        return arg


class FilesContainingFolder:
    """Represents a folder that directly contains files to be processed.

    This class validates that the specified folder exists, is readable,
    and contains only files (no subfolders). It also provides access
    to the folder path and its contained file paths as immutable tuples.

    Attributes:
        __path (Path): Path object of the target folder.
        __file_paths (tuple[Path, ...]): Tuple of file paths contained in the folder.

    Raises:
        PermissionError: If the folder cannot be read due to insufficient permissions.
        FileNotFoundError: If the folder is empty, or
                           if a non-file object (e.g., subdirectory) exists in the folder.
    """

    def __init__(self, path: Path):
        self.__path = path

        if not self.__path.is_dir():
            raise ValueError(f'It is not an existing folder.: "{self.__path}"')

        try:
            child_paths = tuple(self.__path.iterdir())
        except PermissionError as err:
            raise PermissionError(f'No read permission for the folder.: "{self.__path}"') from err

        if not child_paths:
            raise ValueError(f'No files were found in the folder.: "{self.__path}"')

        for child_path in child_paths:
            if not child_path.is_file():
                raise ValueError(f'Non-file object in the folder.: "{self.__path}"')
        self.__file_paths = child_paths

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def file_paths(self) -> tuple[Path, ...]:
        return self.__file_paths


class TxtsInFolderConfig(BaseModel):
    """Configuration for txt files which encoding is the same in a folder.

    Attributes:
        ENCODING: Encoding of the txts.
        FOLDER_PATH: Paths of a folder in which the txts are put.
    """

    ENCODING: EncodingStr
    FOLDER_PATH: FilesContainingFolder

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

    @field_validator('ENCODING', mode='before')
    @classmethod
    def __convert_str_to_encoding_str_and_validate(cls, arg: Any) -> EncodingStr:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return EncodingStr(arg.strip())

    @field_validator('FOLDER_PATH', mode='before')
    @classmethod
    def __convert_str_to_files_containing_folder_and_validate(
        cls, arg: Any
    ) -> FilesContainingFolder:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return FilesContainingFolder(Path(arg.strip()))


class MoveFromConfig(BaseModel):
    """MOVE_FROM section of the configuration.

    Attributes:
        TARGET_FILE_ABSOLUTE_PATHS_TXT: Configuration of txts including source file info in a folder.
    """

    TARGET_FILE_ABSOLUTE_PATHS_TXT: TxtsInFolderConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class CharsToEscapeInPath:
    """Utility for defining characters that must be escaped in file paths."""

    __CHARS = r'"<>:/\|?*'

    def __new__(cls, *args, **kwargs):
        raise AttributeError('An instance cannot be generate from this class.')

    def __init__(self, *args, **kwargs):
        raise AttributeError('An instance cannot be generate from this class.')

    # @classmethod
    # def get_match_char_regex(cls) -> str:
    #     """Return a regex pattern that matches characters to be escaped.

    #     Returns:
    #         str: Regex pattern string.
    #     """

    #     return fr'[{re.escape(cls.__CHARS)}]'

    @classmethod
    def get_unmatch_char_regex(cls) -> str:
        """Return a regex pattern that matches any character not in the escape list.

        Returns:
            str: Regex pattern string.
        """

        return fr'[^{re.escape(cls.__CHARS)}]'


class MoveToConfig(BaseModel):
    """MOVE_TO section of the configuration.

    Attributes:
        FOLDER_PATH: Path of a folder to which target files will be moved.
        TARGET_FILES_PATH_JOIN_CHAR: Char to join original absolute path into a file name.
    """

    FOLDER_PATH: DirectoryPath  # Must be existing directory
    TARGET_FILES_PATH_JOIN_CHAR: StrictStr = Field(
        min_length=1, max_length=1, pattern=CharsToEscapeInPath.get_unmatch_char_regex()
    )

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    @field_validator('FOLDER_PATH', mode='before')
    @classmethod
    def __convert_str_to_path(cls, arg: Any) -> Path:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return Path(arg.strip())

    @field_validator('FOLDER_PATH', mode='after')
    @classmethod
    def __validate_folder_path(cls, path: DirectoryPath) -> Path:
        """Validate that the folder is a writable & readable blank folder."""

        temp_file_path = path / '.tempfile'
        try:
            temp_file_path.touch()
        except PermissionError as err:
            raise PermissionError(f'No write permission for the folder.: "{path}"') from err
        os.remove(temp_file_path)

        try:
            child_paths = list(path.iterdir())
        except PermissionError as err:
            raise PermissionError(f'No read permission for the folder.: "{path}"') from err

        if child_paths:
            raise FileExistsError(f'MOVE_TO folder must be a blank folder.: "{path}"')

        return path


class NewTxtConfig(BaseModel):
    """Configuration for creating a new text file with specific encoding.

    Ensures that the specified path does not already exist and that its parent
    directory does exist. Validates the encoding type as well.

    Attributes:
        PATH (NewPath): Path to the new text file. Must not exist yet, and its
            parent directory must exist.
        ENCODING (EncodingStr): Encoding to be used when creating or writing the new text file.
    """

    PATH: NewPath  # Must not exist & parent must exist
    ENCODING: EncodingStr

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

    @field_validator('PATH', mode='before')
    @classmethod
    def __convert_str_to_file_path_and_validate(cls, arg: Any) -> Path:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return Path(arg.strip())

    @field_validator('ENCODING', mode='before')
    @classmethod
    def __convert_str_to_encoding_str_and_validate(cls, arg: Any) -> EncodingStr:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return EncodingStr(arg.strip())


class Config(BaseModel):
    """Main configuration object loaded from YAML.

    Attributes:
        MOVE_FROM: Move source configuration.
        MOVE_TO: Move destination configuration.
        MOVE_LOG_PATH: Move log file path.
        DO_COPY:
            If false, files will be moved.
            If true, files will be copied and will remain in the original path.
    """

    MOVE_FROM: MoveFromConfig
    MOVE_TO: MoveToConfig
    MOVE_LOG_CSV: NewTxtConfig
    DO_COPY: StrictBool

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    @classmethod
    def from_yaml(cls, path: str | Path) -> 'Config':
        """Loads the configuration from a YAML file.

        Args:
            path: Path to the YAML config file.

        Returns:
            Config: Parsed configuration object.
        """

        with open(path, 'r', encoding='utf-8') as fr:
            content = yaml.safe_load(fr)
        return cls(**content)


class PathsListingFile:
    """Represents a text file that lists file paths.

    Reads a text file containing paths (one per line), and parses them into ``Path`` objects.

    Attributes:
        __path (Path): Path to the listing text file.
        __encoding (EncodingStr): Encoding used to read the file.
    """

    def __init__(self, path: Path, encoding: EncodingStr):
        self.__path = path
        self.__encoding = encoding

    def get_paths(self) -> list[Path]:
        """Reads and parses file paths from the listing file.

        Returns:
            list[Path]: List of parsed and validated paths from the file.

        Raises:
            ValueError: If the file contains no valid paths or duplicated paths.
        """

        content = self.__path.read_text(encoding=str(self.__encoding))
        lines = content.split('\n')
        paths = [Path(stripped_line) for line in lines if (stripped_line := line.strip())]

        if not paths:
            raise ValueError(f'No valid paths are listed in the file.: "{self.__path}"')

        duplicated_paths: list[Path] = []
        seen: set[Path] = set()
        for path in paths:
            if path not in seen:
                seen.add(path)
                continue
            if path not in duplicated_paths:
                duplicated_paths.append(path)

        if duplicated_paths:
            joined_paths = '", "'.join(str(path) for path in duplicated_paths)
            raise ValueError(
                f'Some paths in the file "{self.__path}" are duplicated.: "{joined_paths}"'
            )

        return paths


class ExistingAbsoluteFilePath:
    """Represents an existing file path that must be absolute.

    Ensures that the given path refers to a real file and is an absolute path.

    Attributes:
        __PATH (Path): The validated absolute file path.
    """

    def __init__(self, path: Path):

        if not isinstance(path, Path):
            raise TypeError(f'The arg must be a pathlib.Path, but [{type(path)}]')

        self.__PATH = path
        if not self.__PATH.is_file():
            raise ValueError(f'A file of the arg path does not exist.: "{path}"')
        if not self.__PATH.is_absolute():
            raise ValueError(
                f'A file of the arg path exists, but the path is not absolute.: "{path}"'
            )

    def __str__(self) -> str:
        return self.__PATH.__str__()

    @property
    def parts(self) -> tuple[str, ...]:
        return self.__PATH.parts

    @property
    def parent(self) -> Path:
        return self.__PATH.parent


class MoveFileAsAbsolutePathJoinedNameConfig(BaseModel):
    """Configuration for moving a file with a destination name derived
    from its absolute path.

    Attributes:
        source_file_path (ExistingAbsoluteFilePath): The source file to move.
        destination_folder_path (Path): Target folder where the file will be moved.
        path_join_char (str): Character used to join path components to form the new filename.
        do_copy (bool):
            If false, files will be moved.
            If true, files will be copied and will remain in the original path.
        __destination_file_path (Path): Final computed destination file path.
        __verified_file_path_len (int): Path length already verified to be able to exist.
    """

    source_file_path: ExistingAbsoluteFilePath
    destination_folder_path: Path
    path_join_char: StrictStr = Field(
        min_length=1, max_length=1, pattern=CharsToEscapeInPath.get_unmatch_char_regex()
    )
    do_copy: StrictBool

    __destination_file_path: Path = PrivateAttr()
    __verified_file_path_len: ClassVar[int] = 0

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

    @field_validator('source_file_path', mode='after')
    @classmethod
    def __validate_source_file_path(
        cls, arg: ExistingAbsoluteFilePath
    ) -> ExistingAbsoluteFilePath:
        """Validates that the source file is readable and its parent directory is writable.

        Args:
            arg (ExistingAbsoluteFilePath): The source file path to validate.

        Returns:
            ExistingAbsoluteFilePath: The validated source file path.

        Raises:
            PermissionError: If the source file is not readable or its parent folder is not writable.
        """

        try:
            with open(str(arg), 'rb'):
                pass
        except PermissionError as err:
            raise PermissionError(f'No read permission for source file.: "{arg}"') from err

        src_parent_path = arg.parent
        temp_file_path = src_parent_path / '.tempfile'
        try:
            temp_file_path.touch()
        except PermissionError as err:
            raise PermissionError(
                f'No write permission on parent folder of source file.: "{src_parent_path}"'
            ) from err
        os.remove(temp_file_path)

        return arg

    @classmethod
    def __check_path_length(cls, arg: Path):
        """Validate path length by actually testing file creation in a temp directory.

        Args:
            arg (Path): Path to check (not actually created).

        Raises:
            ValueError: If the simulated path length exceeds the file system limit.
        """

        if os.name == 'nt':  # Windows
            file_path_len = len(str(arg))
        else:  # Other OS
            file_path_len = len(str(arg).encode('utf-8'))

        if file_path_len <= cls.__verified_file_path_len:
            return
        else:
            cls.__verified_file_path_len = file_path_len

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                file_name_len = max(1, file_path_len - len(tmpdir) - 1)  # 1 = len of "/"
                dummy_path = Path(tmpdir) / ('x' * file_name_len)
                dummy_path.touch(exist_ok=False)
        except OSError as err:
            raise ValueError(
                f'Path length "{file_path_len}" likely exceeds this file system\'s limit.: "{arg}"'
            ) from err

    @field_validator('destination_folder_path', mode='after')
    @classmethod
    def __validate_destination_folder_path(cls, arg: Path) -> Path:
        """Validates the destination folder path.

        Ensures that the parent folder exists and is writable, and checks path
        length limitations for different operating systems.

        Args:
            arg (Path): Destination folder path.

        Returns:
            Path: The validated destination folder path.

        Raises:
            FileNotFoundError: If the parent of the destination folder does not exist.
            PermissionError: If the parent folder is not writable.
            ValueError: If the destination path length exceeds OS-specific limits.
        """

        dst_parent_path = arg.parent
        if not dst_parent_path.exists():
            raise FileNotFoundError(
                f'Parent of destination folder does not exist.: "{dst_parent_path}"'
            )

        temp_file_path = dst_parent_path / '.tempfile'
        try:
            temp_file_path.touch()
        except PermissionError as err:
            raise PermissionError(
                f'No write permission to create destination folder in "{dst_parent_path}".'
            ) from err
        os.remove(temp_file_path)

        cls.__check_path_length(arg)

        return arg

    @model_validator(mode='after')
    def __validate_path_join_char(self) -> Self:
        """Ensures that the joining character is not already present in the source or destination paths.

        Returns:
            Self: The validated instance.

        Raises:
            ValueError: If the path join character appears in the source or destination paths.
        """

        if self.path_join_char in str(self.source_file_path):
            raise ValueError(
                f'Path joining char "{self.path_join_char}" is already in the source file path.: {self.source_file_path}'
            )
        if self.path_join_char in str(self.destination_folder_path):
            raise ValueError(
                f'Path joining char "{self.path_join_char}" is already in the destination folder path.: {self.destination_folder_path}'
            )
        return self

    def __validate_destination_file_path(self):
        """Validates the computed destination file path.

        Raises:
            FileExistsError: If the destination file already exists.
            ValueError: If the destination file path length exceeds OS-specific limits.
        """

        if self.__destination_file_path.exists():
            raise FileExistsError(
                f'Destination file already exists.: "{self.__destination_file_path}"'
            )

        self.__class__.__check_path_length(self.__destination_file_path)

    def __init__(self, **data):
        """Initializes the configuration and computes the destination file path."""

        super().__init__(**data)

        # Head "/" (or "C:\\" on Windows) will be removed by [1:].
        new_file_name = self.path_join_char.join(self.source_file_path.parts[1:])
        self.__destination_file_path = self.destination_folder_path / new_file_name

        self.__validate_destination_file_path()

    def execute(self):
        """Executes the file move or copy operation.

        Creates the destination folder if it does not exist and moves or copies the file
        to the computed destination path.
        """

        self.destination_folder_path.mkdir(exist_ok=True)
        if not self.do_copy:
            shutil.move(str(self.source_file_path), self.__destination_file_path)
        else:
            shutil.copy2(str(self.source_file_path), self.__destination_file_path)

    @property
    def destination_file_path(self) -> Path:
        return self.__destination_file_path


def __read_arg_config_path() -> Config:
    """Parses the configuration file path from command-line arguments and loads the config.

    Returns:
        Config: Loaded configuration object.

    Raises:
        SystemExit: If the config path is not provided or cannot be parsed.
    """

    logger = getLogger(__name__)

    if len(sys.argv) != 2:
        logger.error('This script needs a config file path as an arg.')
        sys.exit(1)
    config_path = Path(sys.argv[1])

    try:
        CONFIG: Final[Config] = Config.from_yaml(config_path)
    except Exception:
        logger.exception(f'Failed to parse the config file.: "{config_path}"')
        sys.exit(1)

    return CONFIG


def __read_input_txts(input_txts_in_folder_config: TxtsInFolderConfig) -> dict[Path, list[Path]]:
    """Reads and parses input TXT files containing paths.

    Args:
        input_txts_in_folder_config (TxtsInFolderConfig): Configuration object
            specifying the folder and encoding for TXT files.

    Returns:
        dict[Path, list[Path]]: Mapping of TXT file paths to lists of parsed paths.

    Raises:
        ExceptionGroup: If any errors occur while reading or parsing the TXT files.
    """

    txt_path_to_listed_paths: dict[Path, list[Path]] = {}
    listed_path_to_txt_paths: dict[Path, list[Path]] = {}
    exceptions: list[Exception] = []

    for txt_path in input_txts_in_folder_config.FOLDER_PATH.file_paths:

        try:
            listed_paths = PathsListingFile(
                txt_path, input_txts_in_folder_config.ENCODING
            ).get_paths()
        except Exception as err:
            exceptions.append(err)
            continue

        txt_path_to_listed_paths[txt_path] = listed_paths
        for listed_path in listed_paths:
            listed_path_to_txt_paths.setdefault(listed_path, []).append(txt_path)

    for listed_path, txt_paths in listed_path_to_txt_paths.items():
        if len(txt_paths) <= 1:
            continue
        joined_paths = '", "'.join(str(path) for path in txt_paths)
        exceptions.append(
            ValueError(f'Path "{listed_path}" appears in multiple files.: "{joined_paths}"')
        )

    if exceptions:
        raise ExceptionGroup('Some errors happened while reading TXTs.', exceptions)

    return txt_path_to_listed_paths


def __prepare_to_move(
    txt_path_to_listed_paths: dict[Path, list[Path]], move_to_config: MoveToConfig, do_copy: bool
) -> dict[Path, list[MoveFileAsAbsolutePathJoinedNameConfig]]:
    """Prepares move configurations for each path listed in TXT files.

    Args:
        txt_path_to_listed_paths (dict[Path, list[Path]]): Mapping of TXT files
            to their listed paths.
        move_to_config (MoveToConfig): Configuration specifying the move destination.
        do_copy (bool):
            If false, files will be moved.
            If true, files will be copied and will remain in the original path.

    Returns:
        dict[Path, list[MoveFileAsAbsolutePathJoinedNameConfig]]: Mapping of TXT
            paths to lists of move configurations.

    Raises:
        ExceptionGroup: If any errors occur while validating or preparing moves.
    """

    txt_path_to_move_configs: dict[Path, list[MoveFileAsAbsolutePathJoinedNameConfig]] = {}
    exceptions: list[Exception] = []

    for txt_path, listed_paths in txt_path_to_listed_paths.items():

        move_to_folder_path = move_to_config.FOLDER_PATH / txt_path.name

        move_configs: list[MoveFileAsAbsolutePathJoinedNameConfig] = []
        for path in listed_paths:

            try:
                move_from_path = ExistingAbsoluteFilePath(path)
            except Exception as err:
                exceptions.append(err)
                continue

            try:
                move_configs.append(
                    MoveFileAsAbsolutePathJoinedNameConfig(
                        source_file_path=move_from_path,
                        destination_folder_path=move_to_folder_path,
                        path_join_char=move_to_config.TARGET_FILES_PATH_JOIN_CHAR,
                        do_copy=do_copy,
                    )
                )
            except Exception as err:
                exceptions.append(err)

        txt_path_to_move_configs[txt_path] = move_configs

    if exceptions:
        raise ExceptionGroup('Some errors happened while preparing to move.', exceptions)

    return txt_path_to_move_configs


def __move_and_log(
    txt_path_to_move_configs: dict[Path, list[MoveFileAsAbsolutePathJoinedNameConfig]],
    move_log_csv_config: NewTxtConfig,
):
    """Moves files according to the prepared configs and logs the operations.

    Args:
        txt_path_to_move_configs (dict[Path, list[MoveFileAsAbsolutePathJoinedNameConfig]]):
            Mapping of TXT paths to their associated move configurations.
        move_log_csv_config (NewTxtConfig): Configuration specifying where to log the moves.

    Side Effects:
        - Creates a log CSV file with source and destination paths.
        - Moves files from source to destination.
    """

    with move_log_csv_config.PATH.open('w', encoding=str(move_log_csv_config.ENCODING)) as fw:
        fw.write('move_from,move_to\n')

        for _, move_configs in txt_path_to_move_configs.items():
            for move_config in move_configs:
                move_config.execute()
                fw.write(f'{move_config.source_file_path},{move_config.destination_file_path}\n')
                fw.flush()


def __move_target_files_into_a_folder():

    basicConfig(level=INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    logger = getLogger(__name__)

    logger.info(f'"{os.path.basename(__file__)}" start!')

    CONFIG: Final[Config] = __read_arg_config_path()

    action_str = 'MOVE' if not CONFIG.DO_COPY else 'COPY'
    if CONFIG.DO_COPY:
        logger.warning('Running as "DO_COPY" mode. The original files will be remain.')

    try:
        txt_path_to_listed_paths = __read_input_txts(
            CONFIG.MOVE_FROM.TARGET_FILE_ABSOLUTE_PATHS_TXT
        )
    except ExceptionGroup:
        logger.exception('Script aborted because some errors happened while reading TXTs.')
        sys.exit(1)

    try:
        txt_path_to_move_configs = __prepare_to_move(
            txt_path_to_listed_paths, CONFIG.MOVE_TO, CONFIG.DO_COPY
        )
    except ExceptionGroup:
        logger.exception('Script aborted because some errors happened while preparing to move.')
        sys.exit(1)

    # Confirm on console.
    total_paths_count = 0
    for txt_path, move_configs in txt_path_to_move_configs.items():
        listed_paths_count = len(move_configs)
        total_paths_count += listed_paths_count
        logger.info(f'  {listed_paths_count} files on the file "{txt_path}".')
    logger.info(f'{total_paths_count} files in total.')

    input_value = input(f'Are you sure to {action_str} the files? ("yes" or others): ')
    if input_value != 'yes':
        logger.info(f'"{os.path.basename(__file__)}" is CANCELED.')
        return

    try:
        __move_and_log(txt_path_to_move_configs, CONFIG.MOVE_LOG_CSV)
    except Exception:
        logger.exception(
            f'Script aborted because some errors happened while {action_str}ing a file.'
        )
        sys.exit(1)

    logger.info(
        f'All files are successfully {action_str}ed. Please see the {action_str} log "{CONFIG.MOVE_LOG_CSV.PATH}".'
    )

    logger.info(f'"{os.path.basename(__file__)}" done!')


if __name__ == '__main__':
    __move_target_files_into_a_folder()
