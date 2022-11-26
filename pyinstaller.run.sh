echo running-pyinstaller
python -m PyInstaller --noconsole --onefile --clean  --add-data="LICENSE:." --add-data="keyboard.shortcuts.txt:." --add-data="icon.png:." --icon=icon.ico ./dude.py
