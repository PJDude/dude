@cd "%~dp0..\src"

@set /p VERSION=<version.txt
@SET VERSION=%VERSION:~1,10%
@echo VERSION=%VERSION%

@echo building main app raw
python -m nuitka --follow-imports --follow-stdlib --onefile --show-scons --show-progress --show-modules --assume-yes-for-downloads --windows-icon-from-ico=./icon.ico --include-data-file=./version.txt=./version.txt --include-data-file=./../LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude.exe --output-dir=.. --lto=yes --product-name=dude --product-version=%VERSION% --copyright="2022-2023 Piotr Jochymek" --file-description="DUplicates DEtector" ./dude.py

move dude.exe ../dude.exe
move ../dude.dist ../dude

cd ..
powershell Compress-Archive dude dude-raw.zip
