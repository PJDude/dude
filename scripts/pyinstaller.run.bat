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

@echo|set /p="exifread    " >> distro.info.txt
@python -c "import exifread; print(exifread.__version__)" >> distro.info.txt

@echo|set /p="imagehash   " >> distro.info.txt
@python -c "import imagehash; print(imagehash.__version__)" >> distro.info.txt

@echo|set /p="pillow      " >> distro.info.txt
@python -c "import PIL; print(PIL.__version__)" >> distro.info.txt

@echo|set /p="pi_heif     " >> distro.info.txt
@python -c "import pi_heif; print(pi_heif.__version__)" >> distro.info.txt

@echo.
@echo running-pyinstaller-stage_dude
pyinstaller --noconfirm --clean ^
    --version-file=version.pi.dude.txt --icon=icon.ico --windowed ^
    --add-data="distro.info.txt:." --add-data="version.txt;." --add-data="../LICENSE;." ^
    --contents-directory=internal --distpath=%OUTDIR% --name dude --additional-hooks-dir=. ^
    --collect-binaries tkinterdnd2 --hidden-import="PIL._tkinter_finder" ^
    ^
    --exclude-module sklearn.datasets ^
    --exclude-module sklearn.decomposition ^
    --exclude-module sklearn.ensemble ^
    --exclude-module sklearn.feature_extraction ^
    --exclude-module sklearn.feature_selection ^
    --exclude-module sklearn.gaussian_process ^
    --exclude-module sklearn.isotonic ^
    --exclude-module sklearn.kernel_approximation ^
    --exclude-module sklearn.linear_model ^
    --exclude-module sklearn.manifold ^
    --exclude-module sklearn.metrics ^
    --exclude-module sklearn.mixture ^
    --exclude-module sklearn.model_selection ^
    --exclude-module sklearn.naive_bayes ^
    --exclude-module sklearn.neighbors ^
    --exclude-module sklearn.neural_network ^
    --exclude-module sklearn.preprocessing ^
    --exclude-module sklearn.semi_supervised ^
    --exclude-module sklearn.svm ^
    --exclude-module sklearn.tree ^
    --exclude-module sklearn.utils ^
    --exclude-module sklearn._loss ^
    ^
    --exclude-module numpy.testing ^
    --exclude-module numpy.f2py ^
    --exclude-module scipy.io ^
    --exclude-module scipy.signal ^
    --exclude-module scipy.stats ^
    --exclude-module scipy.fftpack ^
    --exclude-module scipy.interpolate ^
    --exclude-module scipy.integrate ^
    --exclude-module scipy.linalg ^
    --exclude-module scipy.odr ^
    --exclude-module scipy.optimize ^
    --exclude-module scipy.constants ^
    --exclude-module scipy.cluster ^
    --exclude-module scipy.sparse.linalg ^
    --exclude-module scipy.spatial.distance ^
    ^
    --optimize 2 dude.py || exit /b 2

@echo.
@echo running-pyinstaller-dudecmd
pyinstaller --noconfirm --clean ^
    --version-file=version.pi.dudecmd.txt --icon=icon.ico ^
    --add-data="distro.info.txt:." --add-data="version.txt;." --add-data="../LICENSE;." ^
    --distpath=%OUTDIR% --console --contents-directory=internal --name dudecmd ^
    --optimize 2 console.py || exit /b 1

move %OUTDIR%\dudecmd\dudecmd.exe %OUTDIR%\dude

@echo.
@echo packing
powershell Compress-Archive %OUTDIR%\dude %OUTDIR%\dude.win.zip
