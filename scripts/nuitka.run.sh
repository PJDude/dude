#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

VERSION=`cat ./version.txt`
VERSION=${VERSION:1:10}
echo VERSION=$VERSION

outdir=../build-nuitka$venvname

rm -rf $outdir
mkdir $outdir

echo ''
echo running-nuitka
echo wd:`pwd`

echo `python3 --version` > distro.info.txt
echo nuitka `python -m nuitka --version` >> distro.info.txt

echo ''
echo running-nuitka-stage_dude
python3 -m nuitka --include-data-file=./distro.info.txt=./distro.info.txt --include-data-file=./version.txt=./version.txt --include-data-file=../LICENSE=./LICENSE --enable-plugin=tk-inter --lto=yes --follow-stdlib  --assume-yes-for-downloads --windows-disable-console --output-dir=$outdir --standalone ./dude.py --output-filename=dude

echo ''
echo running-nuitka-stage_dudecmd
python3 -m nuitka --include-data-file=./distro.info.txt=./distro.info.txt --include-data-file=./version.txt=./version.txt --include-data-file=../LICENSE=./LICENSE --output-dir=$outdir --lto=yes --follow-stdlib  --assume-yes-for-downloads --standalone ./dudecmd.py --output-filename=dudecmd

mv -v $outdir/dudecmd.dist/dudecmd $outdir/dude.dist
mv -v $outdir/dude.dist $outdir/dude

echo ''
echo packing
cd $outdir
zip -9 -r -m ./dude.lin.zip ./dude

