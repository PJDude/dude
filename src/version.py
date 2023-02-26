#!/usr/bin/python3

MAIN_VERSION=1
VERSION_DATE="2023.02.01"

VERSION_FILE='version.txt'

##############################################################
import datetime
import time
import math

ref_time = datetime.datetime.strptime(VERSION_DATE, '%Y.%m.%d').timestamp()

time_diff = time.time()-ref_time
DAYS_MINS=24*60

time_diff_mins=round(math.floor(time_diff/60))
time_diff_days=round(math.floor(time_diff_mins/DAYS_MINS))

mins_rest=time_diff_mins-time_diff_days*DAYS_MINS

time_diff_days_str=str(time_diff_days).zfill(4)
mins_rest_by2_str=str(round(mins_rest/2)).zfill(3)

version='v%s.%s.%s' % (MAIN_VERSION,time_diff_days_str,mins_rest_by2_str)
with open(VERSION_FILE,'w' ) as f:
    f.write(version)

print(version)
