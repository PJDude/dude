CCFLAGS='-Ofast -static' python3.10 -m nuitka --follow-imports --follow-stdlib --onefile --linux-icon=./icon.ico --show-scons --show-progress --show-modules --include-data-files=./icon.png=./icon.png --include-data-files=./LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude --lto=yes ./dude.py 
