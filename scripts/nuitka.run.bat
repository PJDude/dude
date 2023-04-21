@cd "%~dp0.."

SET OUTDIR=build-nuitka-win%VENVNAME%

@rmdir /s /q %OUTDIR%
@mkdir %OUTDIR%

@cd src

@set /p VERSION=<version.txt
@SET VERSION=%VERSION:~1,10%
@echo VERSION=%VERSION%

@echo running-nuitka

python -m nuitka --version > distro.info.txt

python -m nuitka --file-reference-choice=runtime --follow-imports --follow-stdlib --onefile --show-scons --show-progress --show-modules --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --include-data-file=./distro.info.txt=./distro.info.txt --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude.exe --output-dir=../%OUTDIR% --lto=yes --product-name=dude --product-version=%VERSION% --copyright="2022-2023 Piotr Jochymek" --file-description="DUplicates DEtector" ./dude.py

move dude.exe ../%OUTDIR%/dude.exe
move ../%OUTDIR%/dude.dist ../%OUTDIR%/dude
powershell Compress-Archive ../%OUTDIR%/dude ../%OUTDIR%/dude.nuitka.win.zip

exit
