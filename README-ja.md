# move_target_files_into_a_folder

* NOTE: See [`README.md`](./README.md) for English README.

## 概要

このリポジトリは、PC上の複数箇所に散在しているファイルを1つのフォルダに移動させて集約するPythonスクリプトを提供します。移動が可逆的になるように、移動前のファイルの絶対パスを移動後の新しいファイル名にエンコードする仕組みを有していて、その新しいファイル名を元に、移動の切り戻し（undo）を実行するPythonスクリプトについても、あわせて提供しています。
1. 最初のスクリプト[`move_target_files_into_a_folder.py`](#1-move_target_files_into_a_folderpy)は、TXTファイルにリストアップされた複数のファイルを単一のフォルダに統合し、元の絶対パスをファイル名にエンコードします。
2. 2つ目のスクリプト、[`undo_move_target_files_into_a_folder.py`](#2-undo_move_target_files_into_a_folderpy)は、エンコードされたファイル名に基づいて、それらのファイルを元の場所に戻します。

両スクリプトは、一貫性を確保し、誤った上書きを防止し、フォルダの整合性を確認するために、ファイル操作の前に厳格な事前検証を実行します。

### 例
例えば、元のファイルが以下のように配置されているとします。
```
/photos/family/birthday.jpg
/images/pets/dog.png
```

`move_target_files_into_a_folder.py`を実行すると、両ファイルは以下のような単一フォルダ配下に移動されます。
```
/target_folder/file1.txt/photos@family@birthday.jpg
/target_folder/file2.txt/images@pets@dog.png
```

その後、`undo_move_target_files_into_a_folder.py`を実行すると、ファイルは元のパスに戻ります。

### 免責事項
これらのスクリプトによるファイル移動で生じた問題について、開発者は一切の責任を負いません。

---

## ライセンス & 開発者

- **ライセンス**: このリポジトリ内の[`LICENSE`](./LICENSE)を参照してください。
- **開発者**: U-MAN Lab. ([https://u-man-lab.com/](https://u-man-lab.com/))

---

## 1. `move_target_files_into_a_folder.py`

### 1.1. 概要

[`move_target_files_into_a_folder.py`](./move_target_files_into_a_folder.py)は、複数のファイルを1つのフォルダに移動しながら、元の絶対パスを復元可能な状態で維持します。  
移動された各ファイルの名前には、カスタマイズ可能な文字（例：`_`や`@`）で連結された元の絶対パスのフォルダ構造が含まれます。

---

### 1.2. インストールと使用方法

#### (1) Pythonをインストールする

[公式サイト](https://www.python.org/downloads/)を参照してPythonをインストールしてください。  
開発者が検証したバージョンより古い場合、スクリプトが正常に動作しない可能性があります。[`.python-version`](./.python-version)を参照してください。

#### (2) リポジトリをクローンする

```bash
git clone https://github.com/u-man-lab/move_target_files_into_a_folder.git
# gitコマンドを利用できない場合は、別の方法でスクリプトファイルとYAML設定ファイルを環境に配置してください。
cd ./move_target_files_into_a_folder
```

#### (3) Pythonライブラリをインストールする

開発者が検証したバージョンより古い場合、スクリプトが正常に動作しない可能性があります。
```bash
pip install --upgrade pip
pip install -r ./requirements.txt
```

#### (4) 入力用のTXTファイルを用意する

移動対象のファイルの絶対パスを改行区切りで記載したTXTファイルを作成します。TXTファイルは複数用意できます。移動先のフォルダにはTXTファイルと同じ名前のサブフォルダが作成され、その中に対応するTXTファイルに記載されたファイルが移動されます。

#### (5) 設定ファイルを編集する

設定ファイル[`configs/move_target_files_into_a_folder.yaml`](./configs/move_target_files_into_a_folder.yaml)を開き、ファイル内のコメントに従って値を編集します。

#### (6) スクリプトを実行する

```bash
python ./move_target_files_into_a_folder.py ./configs/move_target_files_into_a_folder.yaml
```

実際の移動を実行する前に、スクリプトは全ファイルの移動の検証を行います。その後、実行の確認を求められるので、続行するには`yes`と入力してください。

---

### 1.3. 期待される出力

成功した場合、標準エラー出力(stderr)に次のようなログが出力されます。:

```
2025-10-11 23:27:27,262 [INFO] __main__: "move_target_files_into_a_folder.py" start!
2025-10-11 23:27:27,271 [INFO] __main__:   2 files on the file "data\target_file_absolute_paths_txt\test.txt".
2025-10-11 23:27:27,271 [INFO] __main__:   1 files on the file "data\target_file_absolute_paths_txt\test2.txt".
2025-10-11 23:27:27,271 [INFO] __main__: 3 files in total.
2025-10-11 23:27:35,700 [INFO] __main__: All files are successfully moved. Please see the move log "results\move_log.csv".
2025-10-11 23:27:35,700 [INFO] __main__: "move_target_files_into_a_folder.py" done!
```
参考までに、18,942件の写真・動画ファイルの移動に3分15秒かかりました。Synology DS218（Realtek RTD1296、4コア 1.4 GHz、2GB DDR4）に、2×4TB WD Red（SMR）をRAID1で構成したNAS上で実行しました。

生成されるCSVは次のような形式になります。:

```
move_from,move_to
C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.bak,results\moved_files\test.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.bak
C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.log,results\moved_files\test.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.log
C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.txt,results\moved_files\test2.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.txt
```

---

### 1.4. よくあるエラー

詳細については、スクリプトのソースコードを参照してください。よくあるエラーには以下のものが含まれます。:

- **スクリプトに引数を渡していない**
  ```
  2025-10-11 09:46:05,471 [ERROR] __main__: This script needs a config file path as an arg.
  ```
- **設定ファイルの値がおかしい**
  ```
  2025-10-11 09:47:40,930 [ERROR] __main__: Failed to parse the config file.: "configs\move_target_files_into_a_folder.yaml"
  Traceback (most recent call last):
  :
  ```

---

## 2. `undo_move_target_files_into_a_folder.py`

### 2.1. 概要

[`undo_move_target_files_into_a_folder.py`](./undo_move_target_files_into_a_folder.py)は、上記スクリプトによって移動されたファイルを元の場所に戻します。  
このスクリプトは、移動先フォルダ内のファイル名をデコードすることで元のファイルパスを再構築します。移動操作を実行する前に、すべてのファイルとフォルダを検証し、フォルダ構造が整合性を保ち安全に復元できることを保証します。

---

### 2.2. 実行方法

実行するために、以下の準備が完了していることを確認してください。:

- Pythonをインストールする
- リポジトリをクローンする
- Pythonライブラリをインストールする

（詳細は[1章](#1-move_target_files_into_a_folderpy)を参照してください。）

#### (1) 設定ファイルを編集する

設定ファイル[`configs/undo_move_target_files_into_a_folder.yaml`](./configs/undo_move_target_files_into_a_folder.yaml)を開き、ファイル内のコメントに従って値を編集してください。設定は`move_target_files_into_a_folder.yaml`と同様ですが、`MOVE_FROM`セクションは不要です。

#### (2) スクリプトを実行する

```bash
python ./undo_move_target_files_into_a_folder.py ./configs/undo_move_target_files_into_a_folder.yaml
```

実際の復元を実行する前に、スクリプトは全ファイルの移動の検証を行います。その後、実行の確認を求められるので、続行するには`yes`と入力してください。

---

### 2.3. 期待される出力

成功した場合、標準エラー出力(stderr)に次のようなログが出力されます。:

```
2025-10-13 19:11:30,991 [INFO] __main__: "undo_move_target_files_into_a_folder.py" start!
2025-10-13 19:11:30,997 [INFO] __main__:   2 files in the folder "results\moved_files\test.txt".
2025-10-13 19:11:30,997 [INFO] __main__:   1 files in the folder "results\moved_files\test2.txt".
2025-10-13 19:11:30,997 [INFO] __main__: 3 files in total.
2025-10-13 19:11:33,017 [INFO] __main__: All files are successfully undo-moved. Please see the move log "results\undo_move_log.csv".
2025-10-13 19:11:33,018 [INFO] __main__: "undo_move_target_files_into_a_folder.py" done!
```

生成されるCSVファイルは次のような形式になります。:

```
move_from,move_to
results\moved_files\test.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.bak,C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.bak
results\moved_files\test.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.log,C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.log
results\moved_files\test2.txt\Users@u-man-lab@move_target_files_into_a_folder@data@org_files@hoge.txt,C:\Users\u-man-lab\move_target_files_into_a_folder\data\org_files\hoge.txt
```

---

### 2.4. よくあるエラー

詳細については、スクリプトのソースコードを参照してください。よくあるエラーは、[`move_target_files_into_a_folder.py`](#1-move_target_files_into_a_folderpy)と同様です。
