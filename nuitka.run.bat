@echo building main app
python -m nuitka --follow-imports --follow-stdlib --onefile --show-scons --show-progress --show-modules --disable-console --assume-yes-for-downloads --windows-icon-from-ico=./src/icon.ico --include-data-file=./src/icon.png=./icon.png --include-data-file=./LICENSE=./LICENSE --enable-plugin=tk-inter --remove-output --output-filename=dudegui.exe --lto=yes --remove-output ./src/dude.py
rem --force-stdout-spec=dude.std.log --force-stderr-spec=dude.std.log

@echo building console wrapper
@rem --include-data-file=dudeg.exe=dudegui.exe
python -m nuitka --follow-imports --follow-stdlib --onefile --show-scons --show-progress --show-modules --assume-yes-for-downloads --windows-icon-from-ico=./src/icon.ico --remove-output --output-filename=dude.exe --lto=yes --remove-output ./src/console.py
