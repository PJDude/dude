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

SET OUTDIR_O_C=%OUTDIR%\O_C
SET OUTDIR_O_G=%OUTDIR%\O_G

pyinstaller --clean --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=%OUTDIR_C% --console --name dudecmd console.py
pyinstaller --clean --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=%OUTDIR_G% --windowed --name dude dude.py
pyinstaller --clean --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=%OUTDIR_O_C% --console --name dudecmd --onefile console.py
pyinstaller --clean --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=%OUTDIR_O_G% --windowed --name dude --onefile dude.py

move %OUTDIR_C%\dudecmd\dudecmd.exe %OUTDIR_G%\dude

del %OUTDIR%\dude.pyinstaller.win.zip
powershell Compress-Archive %OUTDIR_G%\dude %OUTDIR%\dude.pyinstaller.win.zip

rem uploadowane pojedynczo
rem move %OUTDIR_O_C%\dudecmd.exe %OUTDIR_O_G%
rem powershell Compress-Archive %OUTDIR_O_G%\*.exe ..\dude.pyinstaller.win.onefile.zip

exit

