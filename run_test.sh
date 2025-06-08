python3 -m venv _venv_test
source _venv_test/bin/activate

python3 -m pip install -r requirements.txt

python3 -m pytest --disable-warnings ./src/test_core.py


