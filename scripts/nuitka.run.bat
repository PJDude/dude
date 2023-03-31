@cd "%~dp0..\src"

@echo building main app raw
python -m nuitka --follow-imports --follow-stdlib --onefile --show-scons --show-progress --show-modules --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude.exe --output-dir=.. --lto=yes ./dude.py
@rem --include-data-file=./icon.png=./icon.png

move dude.exe ../dude.exe
move ../dude.dist ../dude

cd ..
powershell Compress-Archive dude dude-raw.zip
