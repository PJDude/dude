# DUDE (DUplicates DEtector)

GUI utility for finding duplicated files, delete or link them to save space.

## Features
- **scanning for duplicated with multiple criteria**
    - **on up to 8 specified paths**
    - **with specified file size range**
    - **limit scanning results to arbitrary number of groups of biggest files**

    - **caching of calculated sha1 sums**
    - **use of reliable and fast sha1 calculation tools**
      - **sha1sum (linux)**
      - **certutil (windows)**


- **Files display on two synchronized panels**
  - **files grouped by the same sha1 value**
  - **directory content of selected file**


- **Two stage operation on found duplicated files**
  - **marking of files**
      - **Multiple files marking criteria**
        - **by change time**
        - **by common path**
        - **by regular expression**
        - **arbitrary manual**
  - **taking action on marked files**

    - **Multiple taken action ranges**
      - **on all files**
      - **on single duplicates group**
      - **in single directory**

    - **Confirmation required before any destructive action**

- **Persistent Logging**
- **Supported platforms: Linux, Windows**
- **Written in Python3 + Tkinter**
- **included scripts to create single standalone executable with PyInstaller**
- **MIT license**


###### main window:
![image info](./screenshots/main.png)

###### scan dialog:
![image info](./screenshots/scan.png)

###### settings dialog:
![image info](./screenshots/settings.png)
