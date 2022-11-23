#!/usr/bin/python3

import os
import pathlib
from random import randint
from random import choice
import string

def generate(Dir, MaxSubDirsQuant=4, MaxFilesQuant=16,NextLevels=10,MaxSize=65536):
    pathlib.Path(Dir).mkdir(parents=True,exist_ok=True)
    
    for i in range(randint(1,MaxFilesQuant)):
        with open(os.sep.join((Dir,'file' + str(i))) + '.txt', "w") as f:
            f.seek(randint(1,MaxSize))
            f.write(choice(string.ascii_letters))
    
    if NextLevels:
        for i in range(randint(1,MaxSubDirsQuant)):
            generate(os.sep.join((Dir,choice(string.ascii_letters))), MaxSubDirsQuant, MaxFilesQuant,NextLevels-1)

generate('testdir')
