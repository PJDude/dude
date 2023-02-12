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
