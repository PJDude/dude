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
echo "pi_heif     " `python3 -c "import pi_heif; print(pi_heif.__version__)"` >> distro.info.txt

echo ''
echo running-pyinstaller-stage_dude
pyinstaller --noconfirm --noconsole --clean \
    --add-data="distro.info.txt:." --add-data="version.txt:." --add-data="../LICENSE:." \
    --contents-directory=internal --distpath=$outdir --additional-hooks-dir=. \
    --collect-binaries tkinterdnd2 --hidden-import='PIL._tkinter_finder' \
    \
    --exclude-module sklearn.datasets \
    --exclude-module sklearn.decomposition \
    --exclude-module sklearn.ensemble \
    --exclude-module sklearn.feature_extraction \
    --exclude-module sklearn.feature_selection \
    --exclude-module sklearn.gaussian_process \
    --exclude-module sklearn.isotonic \
    --exclude-module sklearn.kernel_approximation \
    --exclude-module sklearn.linear_model \
    --exclude-module sklearn.manifold \
    --exclude-module sklearn.metrics \
    --exclude-module sklearn.mixture \
    --exclude-module sklearn.model_selection \
    --exclude-module sklearn.naive_bayes \
    --exclude-module sklearn.neighbors \
    --exclude-module sklearn.neural_network \
    --exclude-module sklearn.preprocessing \
    --exclude-module sklearn.semi_supervised \
    --exclude-module sklearn.svm \
    --exclude-module sklearn.tree \
    --exclude-module sklearn.utils \
    --exclude-module sklearn._loss \
    \
    --exclude-module numpy.testing \
    --exclude-module numpy.f2py \
    --exclude-module scipy.io \
    --exclude-module scipy.signal \
    --exclude-module scipy.stats \
    --exclude-module scipy.fftpack \
    --exclude-module scipy.interpolate \
    --exclude-module scipy.integrate \
    --exclude-module scipy.linalg \
    --exclude-module scipy.odr \
    --exclude-module scipy.optimize \
    --exclude-module scipy.constants \
    --exclude-module scipy.cluster \
    --exclude-module scipy.sparse.linalg \
    --exclude-module scipy.spatial.distance \
    \
    --optimize 2 ./dude.py

echo ''
echo packing
cd $outdir
zip -9 -r -m ./dude.lin.zip ./dude
