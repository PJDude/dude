#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

python ver_time.py

CCFLAGS='-Ofast -static' python3.10 -m nuitka --follow-imports --follow-stdlib --onefile --linux-icon=./icon.ico --show-scons --show-progress --show-modules --include-data-file=./icon.png=./icon.png --include-data-file=./ver_time.txt=./ver_time.txt --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude --lto=yes --remove-output ./dude.py
mv dude ../dude
