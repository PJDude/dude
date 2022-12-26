#!/usr/bin/python3

import os
import pathlib
import random
import string

def generate(Dir, MaxSubDirsQuant=4, MaxFilesQuant=128,NextLevels=7,MaxSize=65536):
    print(f'generating test dir:{Dir} ...')
    random.seed(111)
    generateCore(Dir, MaxSubDirsQuant, MaxFilesQuant,NextLevels,MaxSize)
    print('Done.')
    
Traps = ' \'"{}[]`!@#$%^&,.()' if os.name=='nt' else ' \'"{}[]`!@#$%^&*,.<>():;'
#Traps = string.ascii_letters

def TrapChar():
    return random.choice(Traps)
    
def generateCore(Dir, MaxSubDirsQuant, MaxFilesQuant,NextLevels,MaxSize):
    pathlib.Path(Dir).mkdir(parents=True,exist_ok=True)

    for i in range(random.randint(1,MaxFilesQuant)):
        try:
            with open(os.sep.join((Dir,TrapChar() + TrapChar() + TrapChar())) + '.txt', "w") as f:
                f.seek(random.randint(1,MaxSize))
                f.write(random.choice(string.ascii_uppercase))
        except:
            pass
            
    if NextLevels:
        for i in range(random.randint(1,MaxSubDirsQuant)):
            generateCore(os.sep.join((Dir,TrapChar() + TrapChar() + TrapChar())), MaxSubDirsQuant, MaxFilesQuant,NextLevels-1,MaxSize)

if __name__ == "__main__":
    generate('testdir')
