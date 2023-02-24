@cd "%~dp0..\src"

@echo writing timestamp
python ver_time.py

@echo building main app
python -m nuitka --follow-imports --follow-stdlib --onefile --show-scons --show-progress --show-modules --disable-console --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --include-data-file=./ver_time.txt=./ver_time.txt --include-data-file=./icon.png=./icon.png --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --remove-output --output-filename=dudegui.exe --lto=yes --remove-output ./dude.py
@rem --force-stdout-spec=dude.std.log --force-stderr-spec=dude.std.log

@echo building console wrapper
python -m nuitka --follow-imports --follow-stdlib --onefile --show-scons --show-progress --show-modules --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --include-data-file=./ver_time.txt=./ver_time.txt --remove-output --output-filename=dude.exe --lto=yes --remove-output ./console.py
@rem --include-data-file=dudeg.exe=dudegui.exe

move dudegui.exe ../dudegui.exe
move dude.exe ../dude.exe
