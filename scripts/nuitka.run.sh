#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

VERSION=`cat ./version.txt`
VERSION=${VERSION:1:10}
echo VERSION=$VERSION

rm -rf ../build-nuitka-lin
mkdir ../build-nuitka-lin

echo running-nuitka
CCFLAGS='-Ofast -static' python3.10 -m nuitka --follow-imports --follow-stdlib --onefile --linux-icon=./icon.ico --show-scons --show-progress --show-modules --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=../build-nuitka-lin/dude --output-dir=../build-nuitka-lin --lto=yes ./dude.py
# --file-description='DUplicates DEtector'
# --copyright='2022-2023 Piotr Jochymek'
#--product-version=$VERSION
#--product-name='dude'
cd ../build-nuitka-lin

mv ./dude ./dude-temp
mv ./dude.dist ./dude

zip -9 -r -m ./dude.nuitka.lin.zip ./dude

mv ./dude-temp ./dude
