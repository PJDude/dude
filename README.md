# DUDE (DUplicates DEtector)

GUI utility for finding duplicated files, delete or link them to save space.

## Features
- **scanning for duplicated files with multiple criteria**
    - **up to 8 search paths**
    - **limit scanning results number**
    - **use of regular expressions to filter results**
    - **use of reliable and fast sha1 calculation tools**
      - **sha1sum (Linux),certutil (Windows)**
    - **caching of calculated sha1 sums**

- **Files display on two synchronized panels**
  - **duplicated files grouped by the same sha1 value**
  - **directory of selected file**
  - **user actions possible on both panels**

- **Two stage operation on found duplicated files**
  - **marking of files with multiple criteria**
  - **taking action on marked files**
  - **Confirmation required before any destructive action**

- **Persistent Logging**
- **Supported platforms: Linux, Windows**
- **Written in Python3 + Tkinter**
- **included scripts to create single standalone executable with PyInstaller**
- **MIT license**

## How to start dude
run dude.py in python3 interpreter with Tkinter

- *pip install -r requirements.txt*
- *python3 ./dude.py*

or prepare standalone executable:

## How to create standalone exe with pyinstaller
- *build.pyinstaller.sh*
- *build.pyinstaller.bat*

## How to use
- **open Scan dialog** (S)
- **specify paths to scan** (Add Paths Alt+A)
- **scan for duplicate files** (Alt+S)
- **mark files for processing** (Try Tab, space, arrows, A, I etc. )
- **take action on marked files** (D Hotkey for Delete files)

###### main window:
![image info](./screenshots/main.png)

###### scan dialog:
![image info](./screenshots/scan.png)

###### settings dialog:
![image info](./screenshots/settings.png)
