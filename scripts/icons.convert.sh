#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

python png.2.py.py
