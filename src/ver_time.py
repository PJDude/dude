#!/usr/bin/python3

import time
import os
import math
import pathlib

VERSION_FILE='ver_main.txt'

try:
    stat = os.stat(VERSION_FILE)
    starttime=round(stat.st_mtime)
except Exception as e:
    print(e)
    exit(1)

try:
    version=str(pathlib.Path(VERSION_FILE).read_text(encoding='ASCII')).strip()
except Exception as e:
    print(e)
    exit(1)
    
time_diff = time.time()-starttime
DAYS_MINS=24*60

time_diff_mins=round(math.floor(time_diff/60))

time_diff_days=round(math.floor(time_diff_mins/DAYS_MINS))

mins_rest=time_diff_mins-time_diff_days*DAYS_MINS

timestamp = str(time.strftime('%Y%m%d.%H%M',time.localtime(time.time()) ))[2:]

with open('ver_time.txt','w' ) as f:
    f.write('%s.%s.%s' % (version,time_diff_days,mins_rest) )
