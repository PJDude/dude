#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

VERSION=`cat ./version.txt`
VERSION=${VERSION:1:10}
echo VERSION=$VERSION

CCFLAGS='-Ofast -static' python3.10 -m nuitka --follow-imports --follow-stdlib --onefile --linux-icon=./icon.ico --show-scons --show-progress --show-modules --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude --lto=yes ./dude.py
# --file-description='DUplicates DEtector'
# --copyright='2022-2023 Piotr Jochymek'
#--product-version=$VERSION
#--product-name='dude'

mv dude ../dude
