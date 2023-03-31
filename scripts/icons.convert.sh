#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

python3.10 png.2.py.py
