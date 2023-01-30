@rem PATH=%PATH%;c:\Users\%USERNAME%\AppData\Roaming\Python\Python310\Scripts
python -m nuitka --follow-imports --onefile --assume-yes-for-downloads --include-data-files=./icon.png=./icon.png --include-data-files=./LICENSE=./LICENSE --include-data-files=./keyboard.shortcuts.txt=./keyboard.shortcuts.txt --enable-plugin=tk-inter ./dude.py
