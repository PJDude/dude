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

mkdir %OUTDIR%

mkdir %OUTDIR_C%
mkdir %OUTDIR_G%

python -m nuitka --version > distro.info.txt || exit /b 1

@rem --show-scons --show-progress --show-modules

@rem --file-reference-choice=runtime
@rem Nuitka-Options:INFO: Using default file reference mode 'runtime' need not be specified.

@rem --follow-imports
@rem Nuitka-Options:INFO: Following all imports is the default for onefile mode and need not be specified.

python -m nuitka --follow-stdlib --onefile --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --include-data-file=./distro.info.txt=./distro.info.txt --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --output-filename=dudecmd.exe --output-dir=%OUTDIR_C% --lto=yes --product-name=dudecmd --product-version=%VERSION% --copyright="2022-2023 Piotr Jochymek" --file-description="DUplicates DEtector" ./console.py || exit /b 2

python -m nuitka --onefile --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --include-data-file=./distro.info.txt=./distro.info.txt --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude.exe --output-dir=%OUTDIR_G% --lto=yes --product-name=dude --product-version=%VERSION% --copyright="2022-2023 Piotr Jochymek" --file-description="DUplicates DEtector" --disable-console ./dude.py || exit /b 3

move %OUTDIR_C%\console.dist\dudecmd.exe %OUTDIR_G%\dude.dist
move %OUTDIR_G%\dude.dist %OUTDIR_G%\dude

del %OUTDIR%\dude.nuitka.win.zip
powershell Compress-Archive %OUTDIR_G%\dude %OUTDIR%\dude.nuitka.win.zip

exit
