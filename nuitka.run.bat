@echo building main app
python -m nuitka --follow-imports --follow-stdlib --onefile --disable-console --assume-yes-for-downloads --force-stdout-spec=dude.stdout.log --force-stderr-spec=dude.stderr.log --windows-icon-from-ico=./icon.ico --include-data-files=./icon.png=./icon.png --include-data-files=./LICENSE=./LICENSE --include-data-files=./keyboard.shortcuts.txt=./keyboard.shortcuts.txt --enable-plugin=tk-inter --remove-output --output-filename=dudegui.exe ./dude.py

@echo building console wrapper
@rem --include-data-files=dudeg.exe=dudegui.exe
python -m nuitka --follow-imports --follow-stdlib --onefile --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --remove-output --output-filename=dude.exe ./console.py
