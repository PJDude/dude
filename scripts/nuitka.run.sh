#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

VERSION=`cat ./version.txt`
VERSION=${VERSION:1:10}
echo VERSION=$VERSION

outdir=build-nuitka-lin$venvname

rm -rf ../$outdir
mkdir ../$outdir

echo running-nuitka

python3 -m nuitka --version > distro.info.txt

CCFLAGS='-Ofast -static' python3 -m nuitka --file-reference-choice=runtime --follow-imports --follow-stdlib --onefile --show-scons --show-progress --show-modules --assume-yes-for-downloads --linux-icon=./icon.ico --include-data-file=./distro.info.txt=./distro.info.txt --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude --output-dir=../$outdir --lto=yes ./dude.py

mv ./dude ../$outdir/dude

# --file-description='DUplicates DEtector'
# --copyright='2022-2023 Piotr Jochymek'
#--product-version=$VERSION
#--product-name='dude'
cd ../$outdir

mv ./dude ./dude-temp
mv ./dude.dist ./dude

zip -9 -r -m ./dude.nuitka.lin.zip ./dude

mv ./dude-temp ./dude
