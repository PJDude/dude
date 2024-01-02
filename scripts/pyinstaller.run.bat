@cd "%~dp0.."
@echo building with pyinstaller
@cd src

@set /p VERSION=<version.txt
@SET VERSION=%VERSION:~1,10%
@echo VERSION=%VERSION%

SET OUTDIR=..\build-pyinstaller-win%VENVNAME%
@rmdir /s /q %OUTDIR%
@mkdir %OUTDIR%

SET OUTDIR_C=%OUTDIR%\C
SET OUTDIR_G=%OUTDIR%\G

pyinstaller --clean --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=%OUTDIR_C% --console --name dudecmd console.py  || exit /b 1
pyinstaller --clean --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=%OUTDIR_G% --windowed --name dude dude.py  || exit /b 2

move %OUTDIR_C%\dudecmd\dudecmd.exe %OUTDIR_G%\dude

del %OUTDIR%\dude.pyinstaller.win.zip
powershell Compress-Archive %OUTDIR_G%\dude %OUTDIR%\dude.pyinstaller.win.zip

exit

