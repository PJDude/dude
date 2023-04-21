export venvname=3.11

rm -fr ./$venvname

virtualenv -p python3.11 $venvname
. ./$venvname/bin/activate
pip install -r ../requirements.txt

./nuitka.run.sh
./pyinstaller.run.sh
