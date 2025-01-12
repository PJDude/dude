#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

VERSION=`cat ./version.txt`
VERSION=${VERSION:1:10}
echo VERSION=$VERSION

outdir=../build-pyinstaller$venvname

rm -rf $outdir
mkdir $outdir

echo ''
echo running-pyinstaller
echo wd:`pwd`

echo `python3 --version` > distro.info.txt
echo ""  >> distro.info.txt

echo "pyinstaller " `pyinstaller --version` >> distro.info.txt
echo "numpy       " `python3 -c "import numpy; print(numpy.__version__)"` >> distro.info.txt
echo "scipy       " `python3 -c "import scipy; print(scipy.__version__)"` >> distro.info.txt
echo "sklearn     " `python3 -c "import sklearn; print(sklearn.__version__)"` >> distro.info.txt
echo "zstandard   " `python3 -c "import zstandard; print(zstandard.__version__)"` >> distro.info.txt
echo "exifread    " `python3 -c "import exifread; print(exifread.__version__)"` >> distro.info.txt
echo "imagehash   " `python3 -c "import imagehash; print(imagehash.__version__)"` >> distro.info.txt
echo "pillow      " `python3 -c "import PIL; print(PIL.__version__)"` >> distro.info.txt

echo ''
echo running-pyinstaller-stage_dude
pyinstaller --strip --noconfirm --noconsole --clean --add-data="distro.info.txt:." --add-data="version.txt:." --add-data="../LICENSE:." --contents-directory=internal --distpath=$outdir --additional-hooks-dir=. --collect-binaries tkinterdnd2 --collect-binaries numpy --collect-binaries scipy --collect-data scipy --hidden-import='PIL._tkinter_finder' --optimize 2 ./dude.py

echo ''
echo packing
cd $outdir
zip -9 -r -m ./dude.lin.zip ./dude

