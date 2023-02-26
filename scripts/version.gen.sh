dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

echo writing version
python version.py
