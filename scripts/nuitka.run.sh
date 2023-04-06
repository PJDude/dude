#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

CCFLAGS='-Ofast -static' python3.10 -m nuitka --follow-imports --follow-stdlib --onefile --linux-icon=./icon.ico --show-scons --show-progress --show-modules --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude --lto=yes ./dude.py
mv dude ../dude
