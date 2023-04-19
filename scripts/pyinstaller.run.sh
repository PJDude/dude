#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

VERSION=`cat ./version.txt`
VERSION=${VERSION:1:10}
echo VERSION=$VERSION

rm -rf ../build-pyinstaller-lin
mkdir ../build-pyinstaller-lin

echo running-pyinstaller

pyinstaller --noconsole --clean --add-data="version.txt:." --add-data="../LICENSE:." --icon=icon.ico --distpath=../build-pyinstaller-lin/ ./dude.py
cd ../build-pyinstaller-lin/
zip -9 -r -m ./dude.pyinstaller.lin.zip ./dude
cd ../src
pyinstaller --noconsole --clean --add-data="version.txt:." --add-data="../LICENSE:." --icon=icon.ico --distpath=../build-pyinstaller-lin/ --onefile ./dude.py


