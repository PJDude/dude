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

import argparse
import os
import signal
#from sys import exit
from subprocess import DEVNULL
import pathlib
import sys

VERSION_FILE='version.txt'

def get_ver_timestamp():
    try:
        timestamp=pathlib.Path(os.path.join(os.path.dirname(__file__),VERSION_FILE)).read_text(encoding='ASCII').strip()
    except Exception as e_ver:
        print(e_ver)
        timestamp=''
    return timestamp

def parse_args(ver):
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            prog = 'dude.exe' if (os.name=='nt') else 'dude',
            description = f"dude version {ver}\nCopyright (c) 2022-2024 Piotr Jochymek\n\nhttps://github.com/PJDude/dude",
            )

    parser.add_argument('paths',nargs='*',help='path to scan')

    parser.add_argument('-ad','--appdirs',action='store_true',help="don't write files in portable mode (folder \"dude.data\" in the executable directory). Use platform specific folders provided by \"appdirs\" module.")
    parser.add_argument('-l','--log' ,nargs=1,help='specify log file')

    exclude_group = parser.add_mutually_exclusive_group()
    exclude_group.add_argument('-e','--exclude',nargs='*'          ,help='exclude expressions')
    exclude_group.add_argument('-er','--exclude-regexp',nargs='*'          ,help='exclude regular expressions')

    run_mode_group = parser.add_mutually_exclusive_group()
    run_mode_group.add_argument('--norun',action='store_true',help='don\'t run scanning, only show scan dialog')

    c_help='do not run the gui. run the scan and save the result to the specified csv file. Implies -nh' if os.name=='nt' else 'do not run the gui. run the scan and save the result to the specified csv file.'
    run_mode_group.add_argument('-c','--csv' ,nargs=1,help=c_help)

    parser.add_argument('-i','--images' ,action='store_true',help='Images similarity mode')
    parser.add_argument('-ih' ,nargs=1,help='Images similarity mode hash size',choices=('4','6','8','10','12','14','16','18','20','22','24','26','28','30','32'))
    parser.add_argument('-id' ,nargs=1,help='Images similarity mode divergence value',choices=('0','1','2','3','4','5','6','7','8','9'))
    parser.add_argument('-ir' ,action='store_true',help='Images similarity mode process all rotations')
    parser.add_argument('-imin' ,nargs=1,help='Images similarity mode minimum image size (pixels)',type=int)
    parser.add_argument('-imax' ,nargs=1,help='Images similarity mode maximum image size (pixels)',type=int)
    parser.add_argument('-igps' ,action='store_true',help='Images GPS proximity mode')

    parser_help=parser.format_help().split('\n')
    help_parts=[parser_help[0]] + parser_help[7::]

    return parser.parse_args()

#windows console wrapper
if __name__ == "__main__":
    GUI_MAIN_WIN_APP_NAME='dude.exe'
    VER_TIMESTAMP = get_ver_timestamp()

    args=parse_args(VER_TIMESTAMP)

    command =[GUI_MAIN_WIN_APP_NAME]

    if args.norun:
        command.append('--norun')

    if args.exclude:
        command.append('--exclude')
        command.extend(args.exclude)

    if args.exclude_regexp:
        command.append('--exclude-regexp')
        command.extend(args.exclude_regexp)

    if args.log:
        command.append('--log')
        command.append(args.log)

    if args.images or args.ih or args.id or args.ir:
        command.append('--images')

    if args.ih:
        command.append('-ih')
        command.append(args.ih)

    if args.id:
        command.append('-id')
        command.append(args.id)

    if args.ir:
        command.append('-ir')

    if args.imin:
        command.append('-imin')
        command.append(args.imin)

    if args.imax:
        command.append('-imax')
        command.append(args.imax)

    if args.igps:
        command.append('-igps')
        command.append(args.igps)

    if args.paths:
        command.extend(args.paths)

    if os.path.exists(GUI_MAIN_WIN_APP_NAME):
        try:
            os.system("start %s" % ' '.join(command))
        except Exception as e_gui:
            print(e_gui)
            sys.exit()
    else:
        print(f'Cannot find {GUI_MAIN_WIN_APP_NAME}')
        sys.exit()
