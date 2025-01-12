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

@echo|set /p="numpy       " >> distro.info.txt
@python -c "import numpy; print(numpy.__version__)" >> distro.info.txt

@echo|set /p="scipy       " >> distro.info.txt
@python -c "import scipy; print(scipy.__version__)" >> distro.info.txt

@echo|set /p="sklearn     " >> distro.info.txt
@python -c "import sklearn; print(sklearn.__version__)" >> distro.info.txt

@echo|set /p="zstandard   " >> distro.info.txt
@python -c "import zstandard; print(zstandard.__version__)" >> distro.info.txt

@echo|set /p="imagehash   " >> distro.info.txt
@python -c "import imagehash; print(imagehash.__version__)" >> distro.info.txt

@echo|set /p="pillow      " >> distro.info.txt
@python -c "import PIL; print(PIL.__version__)" >> distro.info.txt

@echo.
@echo running-pyinstaller-stage_dude
pyinstaller --version-file=version.pi.dude.txt --noconfirm --clean --add-data="distro.info.txt:." --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=%OUTDIR% --windowed --contents-directory=internal --name dude --additional-hooks-dir=. --collect-binaries tkinterdnd2 --collect-binaries numpy --collect-binaries scipy --collect-data scipy --hidden-import="PIL._tkinter_finder" --optimize 2 dude.py || exit /b 2

@echo.
@echo running-pyinstaller-dudecmd
pyinstaller --version-file=version.pi.dudecmd.txt --noconfirm --clean --add-data="distro.info.txt:." --add-data="version.txt;." --add-data="../LICENSE;." --icon=icon.ico --distpath=%OUTDIR% --console --contents-directory=internal --name dudecmd --optimize 2 console.py || exit /b 1

move %OUTDIR%\dudecmd\dudecmd.exe %OUTDIR%\dude

@echo.
@echo packing
powershell Compress-Archive %OUTDIR%\dude %OUTDIR%\dude.win.zip
