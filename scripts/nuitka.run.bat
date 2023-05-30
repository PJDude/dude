@cd "%~dp0.."
@echo building with nuitka
@cd src

@set /p VERSION=<version.txt
@SET VERSION=%VERSION:~1,10%
@echo VERSION=%VERSION%

SET OUTDIR=..\build-nuitka-win%VENVNAME%
rmdir /s /q %OUTDIR%

SET OUTDIR_C=%OUTDIR%\C
SET OUTDIR_G=%OUTDIR%\G

rem SET OUTDIR_O_C=%OUTDIR%\O_C
rem SET OUTDIR_O_G=%OUTDIR%\O_G

mkdir %OUTDIR%

mkdir %OUTDIR_C%
mkdir %OUTDIR_G%

rem mkdir %OUTDIR_O_C%
rem mkdir %OUTDIR_O_G%

python -m nuitka --version > distro.info.txt

python -m nuitka --file-reference-choice=runtime --follow-imports --follow-stdlib --onefile --show-scons --show-progress --show-modules --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --include-data-file=./distro.info.txt=./distro.info.txt --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --output-filename=dudecmd.exe --output-dir=%OUTDIR_C% --lto=yes --product-name=dudecmd --product-version=%VERSION% --copyright="2022-2023 Piotr Jochymek" --file-description="DUplicates DEtector" ./console.py

python -m nuitka --file-reference-choice=runtime --follow-imports --onefile --show-scons --show-progress --show-modules --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --include-data-file=./distro.info.txt=./distro.info.txt --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude.exe --output-dir=%OUTDIR_G% --lto=yes --product-name=dude --product-version=%VERSION% --copyright="2022-2023 Piotr Jochymek" --file-description="DUplicates DEtector" --disable-console ./dude.py

move %OUTDIR_C%\console.dist\dudecmd.exe %OUTDIR_G%\dude.dist
move %OUTDIR_G%\dude.dist %OUTDIR_G%\dude

rem uploadowane pojedynczo
rem powershell Compress-Archive -Path %OUTDIR_G%\dudecmd.exe,%OUTDIR_G%\dude.exe -DestinationPath %OUTDIR%\dude.nuitka.win.onefile.zip
REM move %OUTDIR_C%\dudecmd.exe %OUTDIR_G%


del %OUTDIR%\dude.nuitka.win.zip
powershell Compress-Archive %OUTDIR_G%\dude %OUTDIR%\dude.nuitka.win.zip

exit
