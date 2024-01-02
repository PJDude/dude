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
echo pyinstaller `pyinstaller --version` >> distro.info.txt

echo ''
echo running-pyinstaller-stage_dude
pyinstaller --strip --noconfirm --noconsole --clean --add-data="distro.info.txt:." --add-data="version.txt:." --add-data="../LICENSE:." --contents-directory=internal --distpath=$outdir ./dude.py

echo ''
echo running-pyinstaller-stage_dudecmd
pyinstaller --strip --noconfirm --console --clean --add-data="distro.info.txt:." --add-data="version.txt:." --add-data="../LICENSE:." --contents-directory=internal --distpath=$outdir ./dudecmd.py -n dudecmd

mv -v $outdir/record/record $outdir/dude

echo ''
echo packing
cd $outdir
zip -9 -r -m ./dude.lin.zip ./dude

