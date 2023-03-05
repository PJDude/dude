@cd "%~dp0..\src"

@echo building main app
python -m nuitka --follow-imports --follow-stdlib --onefile --show-scons --show-progress --show-modules --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --include-data-file=./version.txt=./version.txt --include-data-file=./icon.png=./icon.png --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --remove-output --output-filename=dude.exe --lto=yes --remove-output ./dude.py

move dude.exe ../dude.exe
