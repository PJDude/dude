@cd "%~dp0.."
@echo building with nuitka
@cd src

@set /p VERSION=<version.txt
@SET VERSION=%VERSION:~1,10%
@echo VERSION=%VERSION%

@SET OUTDIR=..\build-nuitka

@if exist %OUTDIR% rmdir /s /q %OUTDIR%
@mkdir %OUTDIR%

@echo.
@echo running-nuitka
@echo wd:%CD%

@echo|set /p="Nuitka " > distro.info.txt
python -m nuitka --version >> distro.info.txt

@echo.
@echo running-nuitka-stage_dude
python -m nuitka --windows-icon-from-ico=./icon.ico --include-data-file=./distro.info.txt=./distro.info.txt --include-data-file=./version.txt=./version.txt --include-data-file=../LICENSE=./LICENSE --output-dir=%outdir% --standalone --lto=yes --follow-stdlib --assume-yes-for-downloads --product-version=%VERSION% --copyright="2022-2026 Piotr Jochymek" --file-description="DUplicates DEtector" --enable-plugin=tk-inter --disable-console --output-filename=dude ./dude.py || exit /b 2

@echo.
@echo running-nuitka-stage_dudecmd
python -m nuitka --windows-icon-from-ico=./icon.ico --include-data-file=./distro.info.txt=./distro.info.txt --include-data-file=./version.txt=./version.txt --include-data-file=../LICENSE=./LICENSE --output-dir=%outdir% --standalone --lto=yes --follow-stdlib --assume-yes-for-downloads --product-version=%VERSION% --copyright="2022-2026 Piotr Jochymek" --file-description="DUplicates DEtector" ./console.py --enable-console --output-filename=dudecmd || exit /b 2

move %OUTDIR%\console.dist\dudecmd.exe %OUTDIR%\dude.dist
move %OUTDIR%\dude.dist %OUTDIR%\dude

@echo.
@echo packing
powershell Compress-Archive %OUTDIR%\dude %OUTDIR%\dude.win.zip

