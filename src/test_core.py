import pytest
from tempfile import NamedTemporaryFile
import os,sys

from core import CRCThreadedCalc
from time import sleep
from sys import exit as sys_exit
import subprocess

class DUMMYLOG():
    def info(txt,obj=None):
        print(txt)

def sha1sum_system(filepath):
    result = subprocess.run(['sha1sum', filepath], capture_output=True, text=True)
    if result.returncode == 0:
        hash_value = result.stdout.split()[0]
        return hash_value
    else:
        raise RuntimeError(f"sha1sum failed: {result.stderr.strip()}")

def test_crccalc():
    wd=os.getcwd()
    print(f'{wd=}')

    log=DUMMYLOG

    icons_path=wd + os.sep + "src/icons"
    print(f'{icons_path=}')

    #not important in this case
    pathnr=0
    path=""
    file_name=""
    mtime=0
    ctime=0
    inode=0

    crc_tc = CRCThreadedCalc(log)

    for f in os.listdir(icons_path):
        fullpath = icons_path + os.sep + f
        size = os.path.getsize(fullpath)

        crc_tc.data_dict[(size,fullpath)]=(pathnr,path,file_name,mtime,ctime,inode)

    crc_tc.start()

    while crc_tc.thread_is_alive():
        sleep(0.001)
        print('loopin...')

    for (size,fullpath),(pathnr,path,file_name,mtime,ctime,inode,crc) in crc_tc.data_dict.items():
        print(crc,fullpath)
        sys_res = sha1sum_system(fullpath)

        assert crc == sys_res
