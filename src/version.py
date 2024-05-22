#!/usr/bin/python3

####################################################################################
#
#  Copyright (c) 2022-2024 Piotr Jochymek
#
#  MIT License
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
#
####################################################################################

MAIN_VERSION=2
VERSION_DATE="2024.05.22"

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

ver_num = '%s.%s.%s' % (MAIN_VERSION,time_diff_days_str,mins_rest_by2_str)
version='v%s' % ver_num
with open(VERSION_FILE,'w' ) as f:
    f.write(version)

for template,result in (('version.pi.template.dude.txt','version.pi.dude.txt'),('version.pi.template.dudecmd.txt','version.pi.dudecmd.txt')):
    with open(template,'r' ) as fr:
        with open(result,'w' ) as f:
            f.write(fr.read().replace('VER_TO_REPLACE',ver_num))

print(version)
