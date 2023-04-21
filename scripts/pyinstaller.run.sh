#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

VERSION=`cat ./version.txt`
VERSION=${VERSION:1:10}
echo VERSION=$VERSION

outdir=build-pyinstaller-lin$venvname

rm -rf ../$outdir
mkdir ../$outdir

echo running-pyinstaller

echo python:`python --version` >> distro.info.txt
echo pyinstaller:`pyinstaller --version` > distro.info.txt

pyinstaller --noconsole --clean --add-data="distro.info.txt:." --add-data="version.txt:." --add-data="../LICENSE:." --icon=icon.ico --distpath=../$outdir/ ./dude.py
cd ../$outdir/
zip -9 -r -m ./dude.pyinstaller.lin.zip ./dude
cd ../src
pyinstaller --noconsole --clean --add-data="distro.info.txt:." --add-data="version.txt:." --add-data="../LICENSE:." --icon=icon.ico --distpath=../$outdir/ --onefile ./dude.py


