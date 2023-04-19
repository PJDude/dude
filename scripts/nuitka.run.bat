@cd "%~dp0.."

@rmdir /s /q build-nuitka-win
@mkdir build-nuitka-win

@cd src

@set /p VERSION=<version.txt
@SET VERSION=%VERSION:~1,10%
@echo VERSION=%VERSION%

@echo building with nuitka

python -m nuitka --follow-imports --follow-stdlib --onefile --show-scons --show-progress --show-modules --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude.exe --output-dir=../build-nuitka-win --lto=yes --product-name=dude --product-version=%VERSION% --copyright="2022-2023 Piotr Jochymek" --file-description="DUplicates DEtector" ./dude.py

move dude.exe ../build-nuitka-win/dude.exe
move ../build-nuitka-win/dude.dist ../build-nuitka-win/dude
powershell Compress-Archive ../build-nuitka-win/dude ../build-nuitka-win/dude.nuitka.win.zip
