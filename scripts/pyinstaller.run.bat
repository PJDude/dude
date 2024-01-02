@cd "%~dp0.."
@echo building with pyinstaller
@cd src

@set /p VERSION=<version.txt
@SET VERSION=%VERSION:~1,10%
@echo VERSION=%VERSION%

@SET OUTDIR=..\build-pyinstaller

@if exist %OUTDIR% rmdir /s /q %OUTDIR%
@mkdir %OUTDIR%

@echo.
@echo running-pyinstaller
@echo wd:%CD%

@python --version > distro.info.txt
@echo|set /p="pyinstaller " >> distro.info.txt
@pyinstaller --version >> distro.info.txt

@echo.
@echo running-pyinstaller-stage_dude
pyinstaller --version-file=version.pi.dudecmd.txt --noconfirm --clean --add-data="distro.info.txt:." --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=%OUTDIR% --windowed --contents-directory=internal --name dude dude.py  || exit /b 2

@echo.
@echo running-pyinstaller-dudecmd
pyinstaller --version-file=version.pi.dude.txt --noconfirm --clean --add-data="distro.info.txt:." --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=%OUTDIR% --console --contents-directory=internal --name dudecmd console.py  || exit /b 1

move %OUTDIR%\dudecmd\dudecmd.exe %OUTDIR%\dude

@echo.
@echo packing
powershell Compress-Archive %OUTDIR_G%\dude %OUTDIR%\dude.pyinstaller.win.zip
