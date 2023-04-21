set VENVNAME=3.11

rmdir /s /q %VENVNAME%

virtualenv -p python3.11 %VENVNAME%
call ./%VENVNAME%/Scripts/activate.bat
pip install -r .\..\requirements.txt

start /WAIT /B pyinstaller.run.bat
start /WAIT /B nuitka.run.bat
