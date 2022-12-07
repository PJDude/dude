#!/usr/bin/python3

import os
import pathlib
from random import randint
from random import choice
import string

def generate(Dir, MaxSubDirsQuant=4, MaxFilesQuant=64,NextLevels=6,MaxSize=65536):
    print(f'generating test dir:{Dir} ...')
    generateCore(Dir, MaxSubDirsQuant, MaxFilesQuant,NextLevels,MaxSize)
    print('Done.')
    
def generateCore(Dir, MaxSubDirsQuant, MaxFilesQuant,NextLevels,MaxSize):
    pathlib.Path(Dir).mkdir(parents=True,exist_ok=True)
    
    for i in range(randint(1,MaxFilesQuant)):
        with open(os.sep.join((Dir,'file' + str(i))) + '.txt', "w") as f:
            f.seek(randint(1,MaxSize))
            f.write(choice(string.ascii_letters))
    
    if NextLevels:
        for i in range(randint(1,MaxSubDirsQuant)):
            generateCore(os.sep.join((Dir,choice(string.ascii_letters))), MaxSubDirsQuant, MaxFilesQuant,NextLevels-1,MaxSize)

if __name__ == "__main__":
    generate('testdir')
