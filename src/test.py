#!/usr/bin/python3

import os
import pathlib
import random
import string

def generate(Dir, MaxSubDirsQuant=4, MaxFilesQuant=128,NextLevels=6,MaxSize=65536):
    print(f'generating test dir:{Dir} ...')
    random.seed(111)
    generateCore(Dir, MaxSubDirsQuant, MaxFilesQuant,NextLevels,MaxSize)
    print('Done.')
    
Traps = ' \'"{}[]`!@#$%^&,.()' if os.name=='nt' else ' \'"{}[]`!@#$%^&*,.<>():;'
Traps = string.ascii_letters

def TrapChar():
    return random.choice(Traps)
    
def generateCore(Dir, MaxSubDirsQuant, MaxFilesQuant,NextLevels,MaxSize):
    try:
        pathlib.Path(Dir).mkdir(parents=True,exist_ok=True)
    except Exception as e:
        print(e)
            
    for i in range(random.randint(1,MaxFilesQuant)):
        try:
            FilePath1=os.sep.join((Dir,TrapChar() + TrapChar() + TrapChar()))
            FilePath2=os.sep.join((Dir,TrapChar() + TrapChar() + TrapChar()))
            with open(FilePath1, "w") as f:
                f.seek(random.randint(1,MaxSize))
                f.write(random.choice(string.ascii_uppercase))
                
            os.symlink(pathlib.Path(os.path.abspath(FilePath1)),pathlib.Path(os.path.abspath(FilePath2)))
        except Exception as e:
            print(e)
            
    if NextLevels:
        for i in range(random.randint(1,MaxSubDirsQuant)):
            DirPath1=os.sep.join((Dir,TrapChar() + TrapChar() + TrapChar()))
            DirPath2=os.sep.join((Dir,TrapChar() + TrapChar() + TrapChar()))
            #DirPath3=os.sep.join((Dir,TrapChar() + TrapChar() + TrapChar()))
            generateCore(DirPath1, MaxSubDirsQuant, MaxFilesQuant,NextLevels-1,MaxSize)
            try:
                os.symlink(pathlib.Path(os.path.abspath(DirPath1)),pathlib.Path(os.path.abspath(DirPath2)))
            except Exception as e:
                print(e)
            #os.symlink('./..',DirPath2)

if __name__ == "__main__":
    generate('testdir')
