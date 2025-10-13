# move_target_files_into_a_folder

* NOTE: 日本語版のREADMEは[`README-ja.md`](./README-ja.md)を参照。

## Overview

This repository provides a Python script that consolidates files scattered across multiple locations on your PC into a single folder. To ensure the move is reversible, it incorporates a mechanism that encodes the absolute path of each file into its new filename after relocation. It also includes a Python script that performs an undo operation based on these new filenames.
1. The first script, [`move_target_files_into_a_folder.py`](#1-move_target_files_into_a_folderpy), consolidates multiple files listed in a TXT file into a single destination folder, encoding their original absolute paths into the filenames.
2. The second script, [`undo_move_target_files_into_a_folder.py`](#2-undo_move_target_files_into_a_folderpy), restores those files back to their original locations based on the encoded filenames.

Both scripts perform strict pre-validation before any file operation to ensure consistency, prevent accidental overwrites, and verify folder integrity.

### Example
For example, suppose the original files are located as follows:
```
/photos/family/birthday.jpg
/photos/pets/dog.png
```

After running `move_target_files_into_a_folder.py`, both files are moved into one folder such as:
```
/merged/file1.txt/photos_family_birthday.jpg
/merged/file2.txt/photos_pets_dog.png
```

Then, running `undo_move_target_files_into_a_folder.py` restores them back to their original paths.

### Disclaimer
The developer assumes no responsibility for any issues that may arise if you move files by these scripts.

---

## License & Developer

- **License**: See [`LICENSE`](./LICENSE) in this repository.
- **Developer**: U-MAN Lab. ([https://u-man-lab.com/](https://u-man-lab.com/))

---

## 1. `move_target_files_into_a_folder.py`

### 1.1. Description

[`move_target_files_into_a_folder.py`](./move_target_files_into_a_folder.py) moves multiple files into one destination folder while maintaining traceability of their original paths.  
Each moved file’s name includes the original folder structure, joined by a customizable character (e.g., `_` or `@`).

---

### 1.2. Installation & Usage

#### (1) Install Python

Install Python from the [official Python website](https://www.python.org/downloads/).  
The scripts may not work properly if the version is lower than the verified one. Refer to the [`.python-version`](./.python-version).

#### (2) Clone the repository

```bash
git clone https://github.com/u-man-lab/move_target_files_into_a_folder.git
# If you don't have "git", copy the scripts and YAMLs manually to your environment.
cd ./move_target_files_into_a_folder
```

#### (3) Install Python dependencies

The scripts may not work properly if the versions are lower than the verified ones.
```bash
pip install --upgrade pip
pip install -r ./requirements.txt
```

#### (4) Prepare TXT files
Create TXT files listing the absolute path of each target file on separate lines. Multiple TXT files can be prepared. Subfolders with the same name as the TXT files will be created in the destination folder, and the files specified in the corresponding TXT file will be moved into them.

#### (5) Edit the configuration file

Open the configuration file [`configs/move_target_files_into_a_folder.yaml`](./configs/move_target_files_into_a_folder.yaml) and edit the values according to the comments in the file.

#### (6) Run the script

```bash
python ./move_target_files_into_a_folder.py ./configs/move_target_files_into_a_folder.yaml
```

Before executing the actual restoration, the script performs a dry-run validation of all files. You will be prompted to confirm the operation (type `yes` to proceed).

---

### 1.3. Expected Output

On success, stderr will include logs similar to:

```
2025-10-11 23:27:27,262 [INFO] __main__: "move_target_files_into_a_folder.py" start!
2025-10-11 23:27:27,271 [INFO] __main__:   2 files on the file "data\target_file_absolute_paths_txt\test.txt".
2025-10-11 23:27:27,271 [INFO] __main__:   1 files on the file "data\target_file_absolute_paths_txt\test2.txt".
2025-10-11 23:27:27,271 [INFO] __main__: 3 files in total.
2025-10-11 23:27:35,700 [INFO] __main__: All files are successfully moved. Please see the move log "results\move_log.csv".
2025-10-11 23:27:35,700 [INFO] __main__: "move_target_files_into_a_folder.py" done!
```

The resulting CSV will be like:

```
move_from,move_to
C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.bak,results\moved_files\test.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.bak
C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.log,results\moved_files\test.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.log
C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.txt,results\moved_files\test2.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.txt
```

---

### 1.4. Common Errors

For full details, see the script source. Common errors include:

- **Missing config path argument**
  ```
  2025-10-11 09:46:05,471 [ERROR] __main__: This script needs a config file path as an arg.
  ```
- **Invalid or missing config field**
  ```
  2025-10-11 09:47:40,930 [ERROR] __main__: Failed to parse the config file.: "configs\move_target_files_into_a_folder.yaml"
  Traceback (most recent call last):
  :
  ```

---

## 2. `undo_move_target_files_into_a_folder.py`

### 2.1. Description

[`undo_move_target_files_into_a_folder.py`](./undo_move_target_files_into_a_folder.py) restores files moved by the above script back to their original locations.  
This script reconstructs the original file paths by decoding the filenames in the destination folder. It validates every file and folder before performing any move operation to ensure the folder structure is consistent and safe for restoration.

---

### 2.2. Usage

Before running, ensure you have already:

- Installed Python
- Cloned the repository
- Installed dependencies

(See [Chapter 1](#1-move_target_files_into_a_folderpy) for setup details.)

#### (1) Edit the configuration file

Open the configuration file [`configs/undo_move_target_files_into_a_folder.yaml`](./configs/undo_move_target_files_into_a_folder.yaml) and edit the values according to the comments in the file. 
Configuration is similar to `move_target_files_into_a_folder.yaml`, except that the `MOVE_FROM` section is intentionally omitted.

#### (2) Run the script

```bash
python ./undo_move_target_files_into_a_folder.py ./configs/undo_move_target_files_into_a_folder.yaml
```

Before executing the actual move, the script performs a dry-run validation of all files. You will be prompted to confirm the operation (type `yes` to proceed).

---

### 2.3. Expected Output

On success, stderr will include logs similar to:

```
2025-10-13 19:11:30,991 [INFO] __main__: "undo_move_target_files_into_a_folder.py" start!
2025-10-13 19:11:30,997 [INFO] __main__:   2 files in the folder "results\moved_files\test.txt".
2025-10-13 19:11:30,997 [INFO] __main__:   1 files in the folder "results\moved_files\test2.txt".
2025-10-13 19:11:30,997 [INFO] __main__: 3 files in total.
2025-10-13 19:11:33,017 [INFO] __main__: All files are successfully undo-moved. Please see the move log "results\undo_move_log.csv".
2025-10-13 19:11:33,018 [INFO] __main__: "undo_move_target_files_into_a_folder.py" done!
```

The resulting CSV will be like:

```
move_from,move_to
results\moved_files\test.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.bak,C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.bak
results\moved_files\test.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.log,C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.log
results\moved_files\test2.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.txt,C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.txt
```

---

### 2.4. Common Errors

For full details, see the script source. Common errors are the same as [`move_target_files_into_a_folder.py`](#1-move_target_files_into_a_folderpy).
