dir="$(readlink -m $(dirname "$0"))"
cd $dir/../src

echo writing version
python3.10 version.py
