@cd "%~dp0.."

SET OUTDIR=build-pyinstaller-win%VENVNAME%

@rmdir /s /q %OUTDIR%
@mkdir %OUTDIR%

@cd src

@set /p VERSION=<version.txt
@SET VERSION=%VERSION:~1,10%
@echo VERSION=%VERSION%

@echo building with pyinstaller

pyinstaller --clean --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=../%OUTDIR% dude.py

powershell Compress-Archive ../%OUTDIR%/dude ../%OUTDIR%/dude.pyinstaller.win.zip

pyinstaller --clean --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=../%OUTDIR% --onefile dude.py

exit

