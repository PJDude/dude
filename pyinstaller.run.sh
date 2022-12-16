echo running-pyinstaller
pyinstaller --noconsole --onefile --clean  --add-data="LICENSE:." --add-data="keyboard.shortcuts.txt:." --add-data="icon.png:." --icon=icon.ico ./dude.py 2>&1 | tee ./dist/pyinstaller.lin.log
