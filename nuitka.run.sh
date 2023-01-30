echo running-nuitka

python3.10 -m nuitka --follow-imports --onefile --include-data-files=./icon.png=./icon.png --include-data-files=./LICENSE=./LICENSE --include-data-files=./keyboard.shortcuts.txt=./keyboard.shortcuts.txt --enable-plugin=tk-inter ./dude.py
