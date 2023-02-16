#!/usr/bin/python3

####################################################################################
#
#  Copyright (c) 2022 Piotr Jochymek
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
from sys import exit
from subprocess import Popen
from subprocess import DEVNULL
import version

def ParseArgs(ver):
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            prog = 'dude.exe' if (os.name=='nt') else 'dude',
            description = f"dude version {ver}\nCopyright (c) 2022 Piotr Jochymek\n\nhttps://github.com/PJDude/dude",
            )

    parser.add_argument('paths'                 ,nargs='*'          ,help='path to scan')

    parser.add_argument('-e','--exclude'        ,nargs='*'          ,help='exclude expressions')
    parser.add_argument('-er','--excluderegexp' ,nargs='*'          ,help='exclude regular expressions')
    parser.add_argument('--norun'           ,action='store_true'    ,help='don\'t run scanning, only show scan dialog')
    parser.add_argument('-l','--log' ,nargs='?'                     ,help='specify log file')
    parser.add_argument('-d','--debug' ,action='store_true'         ,help='set debug logging level')

    return parser.parse_args()

#windows console problem case
if __name__ == "__main__":
    args=ParseArgs(version.VERSION)

    GuiMainApp='dudegui.exe'
    command =[GuiMainApp]

    if args.norun:
        command.append('--norun')

    if args.exclude:
        command.append('--exclude')
        command.extend(args.exclude)

    if args.excluderegexp:
        command.append('--excluderegexp')
        command.extend(args.excluderegexp)

    if args.log:
        command.append('--log')
        command.append(args.log)

    if args.debug:
        command.append('--debug')

    if args.paths:
        command.extend(args.paths)

    if os.path.exists(GuiMainApp):
        try:
            Popen(command,stdin=DEVNULL,stdout=DEVNULL,stderr=DEVNULL)
            #dont wait with open console for main process
            os.kill(os.getppid(),signal.SIGTERM)
        except Exception as e:
            print(e)
            exit()
    else:
        print(f'Cannot find {GuiMainApp}')
        exit()
