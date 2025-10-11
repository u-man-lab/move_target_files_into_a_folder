import os
import shutil
import sys
from logging import DEBUG, INFO, basicConfig, getLogger
from pathlib import Path
from typing import Any, Final

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    DirectoryPath,
    Field,
    PrivateAttr,
    StrictStr,
    field_validator,
)

from move_target_files_into_a_folder import CharsToEscapeInPath, NewTxtConfig


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

        try:
            self.__file_paths = tuple(self.__path.iterdir())
        except PermissionError as err:
            raise PermissionError(f'No read permission for the folder.: "{self.__path}"') from err

        if not self.__file_paths:
            raise ValueError(f'No files were found in the folder.: "{self.__path}"')

        for file_path in self.__file_paths:
            if not file_path.is_file():
                raise ValueError(f'Non-file object in the folder.: "{self.__path}"')

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def file_paths(self) -> tuple[Path, ...]:
        return self.__file_paths


class UndoMoveToConfig(BaseModel):
    """MOVE_TO section of the configuration.

    Attributes:
        FOLDER_PATH: Path of a folder to which files were moved by "move_target_files_into_a_folder.py".
        TARGET_FILES_PATH_JOIN_CHAR: Char used to join original absolute path into a file name.
    """

    FOLDER_PATH: DirectoryPath  # Must be existing directory
    TARGET_FILES_PATH_JOIN_CHAR: StrictStr = Field(
        min_length=1, max_length=1, pattern=CharsToEscapeInPath.get_unmatch_char_regex()
    )

    __files_containing_folders: tuple[FilesContainingFolder, ...] = PrivateAttr()

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
        """Validate that the folder is a writable & readable folder."""

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

        if not child_paths:
            raise ValueError(f'No folders were found in MOVE_TO folder.: "{path}"')

        for child_path in child_paths:
            if not child_path.is_dir():
                raise ValueError(f'Non-folder object in the folder.: "{path}"')

        return path

    def __init__(self, **data):
        """Initializes the configuration and computes the files containing folders."""

        super().__init__(**data)

        self.__files_containing_folders = tuple(
            FilesContainingFolder(child_path) for child_path in self.FOLDER_PATH.iterdir()
        )

    @property
    def files_containing_folders(self) -> tuple[FilesContainingFolder, ...]:
        return self.__files_containing_folders


class Config(BaseModel):
    """Main configuration object loaded from YAML.

    Attributes:
        MOVE_TO: Undo-move configuration.
        MOVE_LOG_PATH: Move log file path.
    """

    MOVE_TO: UndoMoveToConfig
    MOVE_LOG_CSV: NewTxtConfig

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


class AbsolutePathJoinedNameFilePath:
    """Represents a moved file whose name encodes its original absolute path.

    A file moved by the "move_target_files_into_a_folder.py" script has a
    file name composed of its original absolute path parts joined with a
    specific character (e.g., "@"). This class reconstructs the original
    absolute file path from that encoded file name.

    Attributes:
        __path (Path): The current file path of the moved file.
        __original_absolute_file_path (Path):
            The reconstructed absolute path where the file originally existed.
    """

    def __init__(self, path: Path, path_join_char: str):

        if not isinstance(path, Path):
            raise TypeError(f'The argument must be a Path object, got "{path}" [{type(path)}].')
        self.__path = path

        if not isinstance(path_join_char, str) or len(path_join_char) != 1:
            raise TypeError(
                f'The argument must be a char, got "{path_join_char}" [{type(path_join_char)}].'
            )

        self.__original_absolute_file_path = self.__reconstruct_original_absolute_file_path(
            self.__path.name, path_join_char
        )

    @staticmethod
    def __reconstruct_original_absolute_file_path(file_name: str, path_join_char: str) -> Path:

        parts = file_name.split(path_join_char)
        if len(parts) == 1:
            raise ValueError(
                f'Path joining char "{path_join_char}" is not in the file name.: "{file_name}"'
            )

        # NOTE: Assume that the file is on the same drive as this script file.
        drive = Path.cwd().drive
        if drive:  # Windows (e.g. 'C:', '\\\\server\\share'
            root = drive + '\\'
        else:
            root = '/'

        return Path(root, *parts)

    def __str__(self) -> str:
        return self.__path.__str__()

    @property
    def parent(self) -> Path:
        return self.__path.parent

    @property
    def original_absolute_file_path(self) -> Path:
        return self.__original_absolute_file_path


class UndoMoveAbsolutePathJoinedNameFileConfig(BaseModel):
    """Configuration for restoring a moved file to its original absolute location.

    This class validates the accessibility of the moved file, reconstructs
    its original absolute path, ensures that the destination path is valid
    (parent exists, file does not already exist), and executes the undo-move
    operation.

    Attributes:
        source_file_path (AbsolutePathJoinedNameFilePath):
            The moved file path object representing the file to restore.
        __destination_file_path (Path):
            The reconstructed original destination path where the file should be restored.
    """

    source_file_path: AbsolutePathJoinedNameFilePath

    __destination_file_path: Path = PrivateAttr()

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

    @field_validator('source_file_path', mode='after')
    @classmethod
    def __validate_source_file_path(
        cls, arg: AbsolutePathJoinedNameFilePath
    ) -> AbsolutePathJoinedNameFilePath:
        """Validates that the source file is readable and its parent directory is writable.

        Args:
            arg (AbsolutePathJoinedNameFilePath): The source file path to validate.

        Returns:
            AbsolutePathJoinedNameFilePath: The validated source file path.

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

    def __validate_destination_file_path(self):
        """Validates the computed destination file path.

        Raises:
            FileExistsError: If the destination file already exists.
            FileNotFoundError: If the parent of the destination file does not exist.
        """

        if self.__destination_file_path.exists():
            raise FileExistsError(
                f'Destination file already exists.: "{self.__destination_file_path}"'
            )

        if not self.__destination_file_path.parent.exists():
            raise FileNotFoundError(
                f'Parent of destination file does not exist.: "{self.__destination_file_path}"'
            )

    def __init__(self, **data):
        """Initializes the configuration and computes the destination file path."""

        super().__init__(**data)

        self.__destination_file_path = self.source_file_path.original_absolute_file_path
        self.__validate_destination_file_path()

    def execute(self):
        """Executes the file move operation."""

        shutil.move(str(self.source_file_path), self.__destination_file_path)

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


def __prepare_to_undo_move(
    undo_move_to_config: UndoMoveToConfig,
) -> dict[Path, list[UndoMoveAbsolutePathJoinedNameFileConfig]]:
    """Prepares undo-move configurations for each file in folders.

    Args:
        undo_move_to_config (UndoMoveToConfig): Configuration specifying the undo-move destination.

    Returns:
        dict[Path, list[UndoMoveAbsolutePathJoinedNameFileConfig]]: Mapping of
            folder paths to lists of move configurations.

    Raises:
        ExceptionGroup: If any errors occur while validating or preparing undo-moves.
    """

    folder_path_to_undo_move_configs: dict[
        Path, list[UndoMoveAbsolutePathJoinedNameFileConfig]
    ] = {}
    exceptions: list[Exception] = []

    for files_containing_folder in undo_move_to_config.files_containing_folders:

        undo_move_configs: list[UndoMoveAbsolutePathJoinedNameFileConfig] = []
        for path in files_containing_folder.file_paths:

            try:
                move_from_path = AbsolutePathJoinedNameFilePath(
                    path, undo_move_to_config.TARGET_FILES_PATH_JOIN_CHAR
                )
            except Exception as err:
                exceptions.append(err)
                continue

            try:
                undo_move_configs.append(
                    UndoMoveAbsolutePathJoinedNameFileConfig(source_file_path=move_from_path)
                )
            except Exception as err:
                exceptions.append(err)

        folder_path_to_undo_move_configs[files_containing_folder.path] = undo_move_configs

    if exceptions:
        raise ExceptionGroup('Some errors happened while preparing to undo-move.', exceptions)

    return folder_path_to_undo_move_configs


def __undo_move_and_log(
    folder_path_to_undo_move_configs: dict[Path, list[UndoMoveAbsolutePathJoinedNameFileConfig]],
    move_log_csv_config: NewTxtConfig,
):
    """Undo-moves according to the prepared configs and logs the operations.

    Args:
        folder_path_to_undo_move_configs (dict[Path, list[UndoMoveAbsolutePathJoinedNameFileConfig]]):
            Mapping of folder paths to their associated undo-move configurations.
        move_log_csv_config (NewTxtConfig): Configuration specifying where to log the moves.

    Side Effects:
        - Creates a log CSV file with source and destination paths.
        - Moves files from source to destination.
    """

    with move_log_csv_config.PATH.open('w', encoding=str(move_log_csv_config.ENCODING)) as fw:
        fw.write('move_from,move_to\n')

        for _, undo_move_configs in folder_path_to_undo_move_configs.items():
            for undo_move_config in undo_move_configs:
                undo_move_config.execute()
                fw.write(
                    f'{undo_move_config.source_file_path},{undo_move_config.destination_file_path}\n'
                )
                fw.flush()


def __undo_move_target_files_into_a_folder():

    basicConfig(level=INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    logger = getLogger(__name__)

    logger.info(f'"{os.path.basename(__file__)}" start!')

    CONFIG: Final[Config] = __read_arg_config_path()

    try:
        folder_path_to_undo_move_configs = __prepare_to_undo_move(CONFIG.MOVE_TO)
    except ExceptionGroup:
        logger.exception(
            'Script aborted because some errors happened while preparing to undo-move.'
        )
        sys.exit(1)

    # Confirm on console.
    total_files_count = 0
    for folder_path, undo_move_configs in folder_path_to_undo_move_configs.items():
        containing_files_count = len(undo_move_configs)
        total_files_count += containing_files_count
        logger.info(f'  {containing_files_count} files in the folder "{folder_path}".')
    logger.info(f'{total_files_count} files in total.')

    input_value = input('Are you sure to undo-move the files? ("yes" or others): ')
    if input_value != 'yes':
        logger.info(f'"{os.path.basename(__file__)}" is CANCELED.')
        return

    try:
        __undo_move_and_log(folder_path_to_undo_move_configs, CONFIG.MOVE_LOG_CSV)
    except Exception:
        logger.exception('Script aborted because some errors happened while undo-moving a file.')
        sys.exit(1)

    logger.info(
        f'All files are successfully undo-moved. Please see the move log "{CONFIG.MOVE_LOG_CSV.PATH}".'
    )

    logger.info(f'"{os.path.basename(__file__)}" done!')


if __name__ == '__main__':
    __undo_move_target_files_into_a_folder()
