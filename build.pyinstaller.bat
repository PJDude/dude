rem PATH=%PATH%;c:\Users\%USERNAME%\AppData\Roaming\Python\Python310\Scripts

pyinstaller --onefile --clean --add-data="LICENSE;." --add-data="keyboard.shortcuts.txt;."  --add-data="icon.png;." --icon=icon.ico ./dude.py
