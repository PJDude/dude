# DUDE (DUplicates DEtector)

GUI utility for finding duplicated files, delete or link them to save space.

## Features:
- Scanning for duplicated files
- Two synchronized panels
  - duplicates groups
  - directory of selected file
- Two stage processing
  - marking of files with multiple criteria
  - taking action on marked files
- Command Line parameters for integration with favorite file manager (e.g. Double Commander)

## Dude GUI (gif not up to date):
![image info](./info/dude.gif)

## Download page:
The portable executable for Linux and Windows can be downloaded from the Releases site:

https://github.com/PJDude/dude/releases

## SOFTPEDIA review:
https://www.softpedia.com/get/System/File-Management/Dude-DUplicates-DEtector.shtml

## General usage:
- scan for duplicate files
- mark files for processing
- take action on marked files (delete, softlink, hardlink)

## Usage tips:
- use keyboard shortcuts. All are described in the context menus of the main panels. As a general rule, actions with **Ctrl** key apply to all files/groups, without **Ctrl** work locally. Start by utilizing just **Tab**, **arrows**, **F5**, **space**, and **Delete**.
- sometimes it is more efficient to operate on entire folders than on CRC groups, so don't ignore lower panel, use **Tab** and **F5** (**F6**)
- narrow down the scanning area, exclude from scanning unnecessary folders (e.g. Windows system folder which is full of duplicates), you can always add multiple (up to 8) independent scan paths
- unzip the portable executable somewhere on your **PATH**, than **dude** command will be available everywhere
- the performance of the scanning process (or of any other software that requires frequent or extensive access to files in general) may be degraded by the **atime** attribute of the scanned file system. Disabling it on Linux file systems may be done usually by applying the **noatime** attribute in **fstab**, on Windows/NTFS it is the **disablelastaccess** option available with the **fsutil** command or by modifying the registry.

## Supported platforms:
- Linux
- Windows

## Command line examples:
* Start scanning for duplicates in current directory:
```
dude .
```
* Start scanning in specified directories:
```
dude c:\order d:\mess
```
* Generate csv with report, exclude some paths:
```
dude ~ --exclude "*.git/*" --csv result.csv ; note the quotation marks on asterisks
dude.exe c:\ --exclude *windows* --csv result.csv
```
* check full set of available parameters:
```
dude --help
```

## Technical information
- Scanning process analyzes selected paths and groups files with the same size. **Dude** compare files by calculated **SHA1** hash of file content. CRC calculation is done in order, from the largest files to the smallest files, in separate threads for every identified device (drive). Number of active threads is limited by available CPU cores. Aborting of CRC calculation gives only partial results - not all files may be identified as duplicates. Restarted scanning process will use cached data. The CRC is always calculated based on the entire contents of the file.
- Calculated CRC is stored in internal cache which allows re-use it in future operation and speedup of searching of duplicates (e.g. with different set of search paths). Key of cache database is pair of inode of file and file modification time stored separately for every device-id, so any file modification or displacement will result in invalidation of obsolete data and recalculation of CRC.
- Marking files does not cause any filesystem change. Any file deletion or linking needs confirmation and is logged.
- Just before files processing, state of files (ctime) is compared with stored data. In case of inconsistency (state of files was changed somehow during operation between scanning/CRC calculation and files processing) action is aborted and data invalidated.
- **Dude** is written in **python3** with **Tkinter** and compiled to single binary executable with **[Nuitka](https://github.com/Nuitka/Nuitka)** (great tool) for better performance. GitHub build for linux platform is done in **ubuntu-20.04** container. In case of **glibc** incompatibility it is always possible to build Your own binary (**nuitka.run.sh**) or run python script (**dude.py**)
- **Dude** for windows ~~is build as two binary executables: **dude.exe** and **dudegui.exe**. They should be saved in the same path. **dude.exe** is basically only to respond on console to --help parameter or for passing command line parameters (if correct) to dudegui.exe. **dudegui.exe** will also accept parameters but will not respond to the console.~~ hides the console when starting the GUI. To keep the console untouched, use the --nohide parameter.
- standard **Dude** Windows distribution causes Windows Defender false positive. To avoid this inconvenience, another distribution **windows.raw** is built, which contains a zipped folder with uncompressed necessary files and dude.exe. Last time I checked, it didn't trigger any antivirus alerts. Choose any distro you prefer.

- ***Soft links*** to **directories** are skipped during the scanning process. ***Soft links*** to **files** are ignored during scanning. Both appear in the bottom "folders" pane.
- ***Hard links*** (files with stat.st_nlink>1) currently are ignored during the scanning process and will not be identified as duplicates (within the same inode obviously, as with other inodes). No action can be performed on them. They will only appear in the bottom "folders" pane. This may change in the future versions.

###### Manual build (linux):
```
pip install -r requirements.txt
./scripts/nuitka.run.sh
```
###### Manual build (windows):
```
pip install -r requirements.txt
.\scripts\nuitka.run.bat
```
###### Manual running of python script:
```
pip install pywin32 ; #windows only
pip install appdirs

python ./src/dude.py
```

## Licensing
- **dude** is licensed under **[MIT license](./LICENSE)**
