# DUDE (DUplicates DEtector)

GUI utility for finding duplicated files, delete or link them to save space.

## Features:
- Scanning for duplicated files
-Files display on two synchronized panels
  - duplicates groups
  - directory of selected file
- Two stage processing on found duplicated files
  - marking of files with multiple criteria
  - taking action on marked files
  - Confirmation is required before any file processing
- Command line parameters for integration with favorite file manager (e.g. Double Commander)


## Supported platforms:
- Linux
- Windows

## Licensing
- **dude** is licensed under **MIT license**

## Dude GUI (gif not up to date):
![image info](./dude.gif)

## Download page:

https://pjdude.github.io/dude/

## General usage:
- **scan for duplicate files**
- **mark files for processing**
- **take action on marked files (delete, softlink, hardlink)**



## Command line:
Scan parameters (paths, excluding expressions etc.) can be passed as command line parameters. Examples:
* Start scanning for duplicates in current directory:
```
dude .
```
* Start scanning in specified directories:
```
dude c:\order d:\mess
```
* Set scan paths but do not start scanning:
```
dude c:\19 x:\9\11 j:\f\k n:\wo --norun
```
* check full set of available parameters:
```
dude --help
```


## Technical information
- Scanning process analyses selected paths and creates groups files with the same size. **Dude** compares files by calculated **SHA1** hash of file content. CRC calculation is done in order, from the largest files to the smallest files, in separate threads for every identified device (drive). Number of active threads is limited by available CPU cores. Aborting of CRC calculation gives only partial results - not all files may be identified as duplicates. Restarted scanning process will use cached data.
- Calculated CRC is stored in internal cache which allows re-use it in future operation and speedup searching of duplicates (e.g. with different set of search paths). Key of cache database is pair of inode of file and file modification time stored separately for every device-id, so any file modification or displacement will result in invalidation of obsolete data and recalculation of CRC.
- Marking files does not cause any filesystem change. Any file deletion or linking needs confirmation and is logged.
- Just before files processing, state of files (ctime) is compared with stored data. In case of inconsistency (state of files was changed somehow during operation between scanning/CRC calculation and files processing) action is aborted and data invalidated.
- **Dude** is written in **python3** with **Tkinter** and compiled to single binary executable with **[Nuitka](https://github.com/Nuitka/Nuitka)** (great tool) for better performance. GitHub build for linux platform is done in **ubuntu-20.04** container. In case of **glibc** incompatibility it is always possible to build Your own binary (**nuitka.run.sh**) or run python script (**dude.py**)
- **Dude** for windows is build as two binary executables: **dude.exe** & **dudegui.exe**. They should be saved in the same path. Both can start **dude** but only **dude.exe** can properly respond on windows console. Both will accept command line parameters.

###### Manual build:
```
pip install -r requirements.txt
nuitka.run.sh
```
###### Manual run python script:
```
python3 ./dude.py
```
###### Stage of development
Dude is in working, pre-release stage.
