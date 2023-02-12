echo running-nuitka

python3.10 -m nuitka --follow-imports --follow-stdlib --onefile --include-data-files=./icon.png=./icon.png --include-data-files=./LICENSE=./LICENSE --include-data-files=./keyboard.shortcuts.txt=./keyboard.shortcuts.txt --enable-plugin=tk-inter -output-filename=dude --remove-output ./dude.py
