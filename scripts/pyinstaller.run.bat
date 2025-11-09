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
@echo. >> distro.info.txt
@echo|set /p="pyinstaller " >> distro.info.txt
@pyinstaller --version >> distro.info.txt

@echo.
@echo running-pyinstaller-stage_dude
pyinstaller --noconfirm --clean --optimize 2 --noupx ^
    --version-file=version.pi.dude.txt --icon=icon.ico --windowed ^
    --add-data="distro.info.txt:." --add-data="version.txt;." --add-data="../LICENSE;." ^
    --contents-directory=internal --distpath=%OUTDIR% --name dude --additional-hooks-dir=. ^
    --collect-binaries tkinterdnd2 ^
    --hidden-import="PIL._tkinter_finder" ^
    --hidden-import="sklearn.cluster._dbscan_inner_" ^
    dude.py || exit /b 2

@echo.
@echo running-pyinstaller-dudecmd
pyinstaller --noconfirm --clean --optimize 2 --noupx ^
    --version-file=version.pi.dudecmd.txt --icon=icon.ico ^
    --add-data="distro.info.txt:." --add-data="version.txt;." --add-data="../LICENSE;." ^
    --distpath=%OUTDIR% --console --contents-directory=internal --name dudecmd ^
    console.py || exit /b 1

move %OUTDIR%\dudecmd\dudecmd.exe %OUTDIR%\dude

@echo.
@echo packing
powershell Compress-Archive %OUTDIR%\dude %OUTDIR%\dude.win.zip
