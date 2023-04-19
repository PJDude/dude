@cd "%~dp0.."

@rmdir /s /q build-pyinstaller-win
@mkdir build-pyinstaller-win

@cd src

@set /p VERSION=<version.txt
@SET VERSION=%VERSION:~1,10%
@echo VERSION=%VERSION%

@echo building with pyinstaller

pyinstaller --clean --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=../build-pyinstaller-win dude.py

powershell Compress-Archive ../build-pyinstaller-win/dude ../build-pyinstaller-win/dude.pyinstaller.win.zip

pyinstaller --clean --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=../build-pyinstaller-win --onefile dude.py
