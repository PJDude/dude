#!/usr/bin/python3

from sys import exit

import fnmatch
import shutil
import os
import os.path
import pathlib
from appdirs import *
import re

import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import scrolledtext

import time

from tkinter.filedialog import askdirectory

import configparser

from threading import Thread

import subprocess
from subprocess import Popen, PIPE

import pyperclip
import logging

import psutil

class Runner(Thread):
    exitCode=0

    def go(self,command):
        self.command=command
        self.start()

    stream=None
    res=None
    resValid=False
    
    def __INIT__(self):
        super().__init__()
        self.res=None
        self.stream=None
        self.exitCode=0

    def run(self):
        self.resValid=True
        try:
            self.stream=subprocess.Popen(self.command, stdout=PIPE, stderr=PIPE,bufsize= 1,universal_newlines=True,shell=windows )
            stdout, stderr = self.stream.communicate()
            self.res=stdout
            if stderr:
                logging.error(f"command:{self.command}->{stderr}")
                self.resValid=False

            self.exitCode=self.stream.poll()
        except Exception as e:
            self.resValid=False
            logging.error(e)

    def kill(self):
        if self.stream:
            self.stream.kill()
            self.resValid=False

    def GetRes(self):
        if self.exitCode==0 and self.res!='' and self.resValid:
            return self.res
        else:
            return None

CACHE_DIR = os.sep.join([user_cache_dir('dude'),"cache"])
LOG_DIR = user_log_dir('dude')
CONFIG_DIR = user_config_dir('dude')

k=1024
M=k*1024
G=M*1024
T=G*1024

multDict={'k':k,'K':k,'M':M,'G':G,'T':T}

windows = (os.name=='nt')
nums='①②③④⑤⑥⑦⑧⑨⑩' if windows else '⓵⓶⓷⓸⓹⓺⓻⓼⓽⓾'

def bytes2str(num):
    kb=num/k

    if kb<k:
        return str(round(kb,2))+'kB'
    elif kb<M:
        return str(round(kb/k,2))+'MB'
    elif kb<G:
        return str(round(kb/M,2))+'GB'
    else:
        return str(round(kb/G,2))+'TB'


def str2bytes(string):
    if not string:
        return None
    elif match := re.search('^\s*(\d+)\s*([kKMGT]?)B?\s*$',string):
        res = int(match.group(1))

        if (multChar := match.group(2)) in multDict:
            res*=multDict[multChar]
        return res
    else:
        return None

class CORE:
    filesOfSize={}
    filesOfSizeOfCRC={}
    cache={}
    sumSize=0
    devs=set()

    @staticmethod
    def CRCStdout2CRC(string):
        return string[:40]

    @staticmethod
    def getStdout2CrcCertuitil(string):
        return string.split('\n')[1]

    def INIT(self):
        self.filesOfSize={}
        self.filesOfSizeOfCRC={}
        self.devs.clear()
        self.limit=0
        self.CrcCutLen=128
        self.crccut={}
        self.ScannedPaths=[]
        self.ExcludeRegExp=False
        self.ExcludeList=[]
        
    def __init__(self):
        self.CRCExec='certutil' if windows else 'sha1sum'
        self.CRCExecParams='-hashfile' if windows else '-b'

        self.GetCrc=self.getStdout2CrcCertuitil if windows else self.CRCStdout2CRC

        self.CheckCRC()
        
        self.INIT()

    def setLimit(self,limit):
        self.limit=limit

    def Path2ScanFull(self,pathnr,path,file):
        return os.path.join(self.Paths2Scan[pathnr]+path,file)

    def ScannedPathFull(self,pathnr,path,file):
        return os.path.join(self.ScannedPaths[pathnr]+path,file)

    def SetPathsToScan(self,paths):
        pathsLen=len(paths)
        abspaths=[os.path.abspath(path) for path in paths]

        if windows:
            abspaths=[path.replace('/','\\').upper() for path in abspaths]

        for path in abspaths:
            if not os.path.exists(path) or not os.path.isdir(path):
                return  path + '\n\nnot a directory'

        apaths=list(zip(abspaths,paths))

        for i1 in range(pathsLen):
            for i2 in range(pathsLen):
                if i1!=i2:
                    path1,orgpath1=apaths[i1]
                    path2,orgpath2=apaths[i2]
                    if path2==path1:
                        return  orgpath2 + '\n\nis equal to:\n\n' +  orgpath1 + '\n'
                    elif path2.startswith(path1 + os.sep):
                        return  orgpath2 + '\n\nis a subpath of:\n\n' +  orgpath1 + '\n'

        self.Paths2Scan=abspaths
        return False

    def SetExcludeMasks(self,RegExp,MasksList):
        self.ExcludeRegExp=RegExp
        
        if RegExp:
            self.ExclFn = lambda expr,string : re.search(expr,string)
        else:
            self.ExclFn = lambda expr,string : fnmatch.fnmatch(string,expr)
            
        teststring='abc'
        for exclmask in MasksList:
            if '|' in exclmask:
                return f"mask:'{exclmask}' - character:'|' not allowed."
            try:
                self.ExclFn(exclmask,teststring)
            except Exception as e:
                return "Expression: '" + exclmask + "' ERROR:" + str(e)
        
        self.ExcludeList=MasksList
        return False
        
    def scan(self,updateCallback):
        logging.info('')
        logging.info('SCANNING')
        
        if self.ExcludeList:
            logging.info('ExcludeList:' + ' '.join(self.ExcludeList))

        pathNr=0
        counter=0
        SizeSum=0

        keepGoing=1

        for PathToScan in self.Paths2Scan:
            loopList=[PathToScan]

            while loopList:
                path = loopList.pop(0)
                subpath=path.replace(PathToScan,'')
                try:
                    for entry in os.scandir(path):
                        file=entry.name
                        fullpath=os.path.join(path,file)
                        if self.ExcludeList:
                            if any({self.ExclFn(expr,fullpath) for expr in self.ExcludeList}):
                                logging.info(f'skipping by Exclude Mask:{fullpath}')
                                continue
                        
                        try:
                            if os.path.islink(entry) :
                                logging.debug(f'skippping link: {path} / {file}')
                            elif entry.is_dir():
                                loopList.append(os.path.join(path,file))
                            elif entry.is_file():
                                
                                    
                                try:
                                    stat = os.stat(fullpath)
                                except Exception as e:
                                    logging.error(f'scan skipp {e}')
                                else:
                                    if stat.st_nlink!=1:
                                        logging.debug(f'scan skipp - hardlinks {stat.st_nlink} - {pathNr},{path},{file}')
                                    else:
                                        if stat.st_size>0:
                                            SizeSum+=stat.st_size
                                            if not stat.st_size in self.filesOfSize:
                                                self.filesOfSize[stat.st_size]=set()
                                            self.filesOfSize[stat.st_size].add( (pathNr,subpath,file,round(stat.st_mtime),round(stat.st_ctime),stat.st_dev,stat.st_ino) )
                                            
                                counter+=1
                                
                                keepGoing = updateCallback(nums[pathNr] + '\n' + PathToScan + '\n' + str(counter) + '\n' + bytes2str(SizeSum),'unprog')
                                if not keepGoing:
                                    break

                        except Exception as e:
                            logging.error(e)
                except Exception as e:
                    logging.error(e)
            
                if not keepGoing:
                    break
            
            pathNr+=1
            if not keepGoing:
                break

        self.devs={dev for size,data in self.filesOfSize.items() for pathnr,path,file,mtime,ctime,dev,inode in data}

        ######################################################################
        #inodes collision detection
        knownDevInodes={}
        for size,data in self.filesOfSize.items():
            for pathnr,path,file,mtime,ctime,dev,inode in data:
                index=(dev,inode)
                if index not in knownDevInodes:
                    knownDevInodes[index]=1
                else:
                    knownDevInodes[index]=knownDevInodes[index]+1

        self.blacklistedInodes = {index for index in knownDevInodes if knownDevInodes[index]>1}

        for size in list(self.filesOfSize):
            for pathnr,path,file,mtime,ctime,dev,inode in list(self.filesOfSize[size]):
                index=(dev,inode)
                if index in self.blacklistedInodes:
                    thisIndex=(pathnr,path,file,mtime,ctime,dev,inode)
                    logging.warning('ignoring conflicting inode entry:' + str(thisIndex))
                    self.filesOfSize[size].remove(thisIndex)

        ######################################################################
        self.sumSize=0
        for size in list(self.filesOfSize):
            quant=len(self.filesOfSize[size])
            if quant==1 :
                del self.filesOfSize[size]
            else:
                self.sumSize += quant*size
        ######################################################################

    def CheckCRC(self):
        stream=subprocess.Popen([self.CRCExec,self.CRCExecParams,os.path.join(os.path.dirname(__file__),'LICENSE')], stdout=PIPE, stderr=PIPE,bufsize=1,universal_newlines=True, shell=windows)

        stdout, stderr = stream.communicate()
        res=stdout
        if stderr:
            logging.error(f"Cannot execute {self.CRCExec}")
            logging.error(stderr)
            logging.error('exiting ')
            exit(10)
        elif exitCode:=stream.poll():
            logging.error(f'exit code:{exitCode}')
            exit(11)
        else:
            logging.debug(f"all fine. stdout:{stdout} crc:{self.GetCrc(stdout)}")
    
    def ReadCRCCache(self):
        self.CRCCache={}
        for dev in self.devs:
            self.CRCCache[dev]=dict()
            try:
                logging.debug(f'reading cache:{CACHE_DIR}:device:{dev}')
                with open(os.sep.join([CACHE_DIR,str(dev)]),'r' ) as cfile:
                    while line:=cfile.readline() :
                        inode,mtime,crc = line.rstrip('\n').split(' ')
                        if crc==None or crc=='None' or crc=='':
                            logging.warning(f"CRCCache read error:{inode},{mtime},{crc}")
                        else:
                            self.CRCCache[dev][(int(inode),int(mtime))]=crc

            except Exception as e:
                logging.warning(e)
                self.CRCCache[dev]=dict()
        
    def WriteCRCCache(self):
        pathlib.Path(CACHE_DIR).mkdir(parents=True,exist_ok=True)
        for dev in self.CRCCache:
            logging.debug(f'writing cache:{CACHE_DIR}:device:{dev}')
            with open(os.sep.join([CACHE_DIR,str(dev)]),'w' ) as cfile:
                for (inode,mtime),crc in self.CRCCache[dev].items():
                    cfile.write(' '.join([str(x) for x in [inode,mtime,crc] ]) +'\n' )
                    
    def SingleCrc(self,size,sizeBytesInfo,sumSizeStr,pathnr,path,file,mtime,ctime,dev,inode,updateCallback):
        FileValid=True
        CacheKey=(int(inode),int(mtime))
        self.fileNr+=1

        if CacheKey in self.CRCCache[dev]:
            crc=self.CRCCache[dev][CacheKey]
            self.sizeDone+=size
            keepGoing=True
        else:
            fullpath=self.Path2ScanFull(pathnr,path,file)

            ProgSize=100.0*self.sizeDone/self.sumSize
            ProgQuant=100.0*self.fileNr/self.total

            (keepGoing,crc)=self.GetFileCrc(fullpath,lambda : updateCallback('\ngroups found:' + self.FoundSumStr + sizeBytesInfo,ProgSize,ProgQuant,progress1Right=bytes2str(self.sizeDone) + sumSizeStr,progress2Right=str(self.fileNr) + self.totalStr) )

            if FileValid:=crc:
                self.CRCCache[dev][CacheKey]=crc
                self.sizeDone+=size

        if keepGoing and FileValid:
            if size not in self.filesOfSizeOfCRC:
                self.filesOfSizeOfCRC[size]={}

            if crc not in self.filesOfSizeOfCRC[size]:
                self.filesOfSizeOfCRC[size][crc]=set()

            self.filesOfSizeOfCRC[size][crc].add( (pathnr,path,file,ctime,dev,inode) )
        return keepGoing
            
    def crcCalc(self,writeLog,updateCallback):
        self.ReadCRCCache()

        self.sizeDone=0

        keepGoing=1
        FoundSum=0
        self.fileNr=0

        self.total = len([ 1 for size in self.filesOfSize for pathnr,path,file,mtime,ctime,dev,inode in self.filesOfSize[size] ])
        self.totalStr = '/' + str(self.total)

        sumSizeStr='/' + bytes2str(self.sumSize)
        self.FoundSumStr='0'

        SizeDone=set()
        PathsToRecheckSet=set()
        
        LimitReached=False
        for size in list(sorted(self.filesOfSize,reverse=True)):
            if keepGoing:
                sizeBytesInfo='\ncurrent size: ' + bytes2str(size)
                SizeDone.add(size)
                for pathnr,path,file,mtime,ctime,dev,inode in self.filesOfSize[size]:
                    if keepGoing:
                        if (not LimitReached) or (LimitReached and (pathnr,path) in PathsToRecheckSet):
                            keepGoing=self.SingleCrc(size,sizeBytesInfo,sumSizeStr,pathnr,path,file,mtime,ctime,dev,inode,updateCallback)
                
                if keepGoing:
                    ######################################################################
                    if size in self.filesOfSizeOfCRC:
                        self.CheckCrcPoolAndPrune(size)
                
                    if size in self.filesOfSizeOfCRC:
                        if self.limit:
                            FoundSum+=len(self.filesOfSizeOfCRC[size])
                            self.FoundSumStr=str(FoundSum)
                            if FoundSum>=self.limit:
                                LimitReached=True
                        
                        if not LimitReached:
                            for crc in self.filesOfSizeOfCRC[size]:
                                 for (pathnr,path,file,ctime,dev,inode) in self.filesOfSizeOfCRC[size][crc]:
                                    PathsToRecheckSet.add((pathnr,path))
                else:
                    break
    
        self.filesOfSize.clear()

        self.ScannedPaths=self.Paths2Scan.copy()

        self.CalcCrcMinLen()
        
        self.WriteCRCCache()
        
        if writeLog:
            self.LogScanResults()
        
    def LogScanResults(self):
        logging.info('#######################################################')
        logging.info('scan and crc calculation complete')
        logging.info('')
        logging.info('scanned paths:')
        for (nr,path) in enumerate(self.Paths2Scan):
            logging.info(f'  {nr}  <->  {path}',)

        for size in self.filesOfSizeOfCRC:
            logging.info('')
            logging.info(f'size:{size}')
            for crc in self.filesOfSizeOfCRC[size]:
                logging.info(f'  crc:{crc}')
                for IndexTuple in self.filesOfSizeOfCRC[size][crc]:
                    logging.info('    ' + ' '.join( [str(elem) for elem in list(IndexTuple) ]))
        logging.info('#######################################################')
    
    def GetFileCrc(self,Fullpath,updateCallbackFn):
        (thread := Runner()).go([self.CRCExec,self.CRCExecParams,Fullpath])

        UpdateCalled=False

        while thread.is_alive():
            UpdateCalled=True
            if updateCallbackFn():
                time.sleep(0.001)
            else :
                thread.kill()
                return (None,None)

        thread.join()
        if not UpdateCalled:
            updateCallbackFn()
        if not (result:=thread.GetRes()):
            return (True,None)
        elif not (crc:=self.GetCrc(result)):
            return (True,None)
        else:
            return (True,crc)

    def CheckCrcPoolAndPrune(self,size):
        for crc in list(self.filesOfSizeOfCRC[size]):
            if len(self.filesOfSizeOfCRC[size][crc])<2 :
                del self.filesOfSizeOfCRC[size][crc]

        if len(self.filesOfSizeOfCRC[size])==0 :
            del self.filesOfSizeOfCRC[size]

    def CalcCrcMinLen(self):
        allCrcLen=len(AllCrcs:={crc for size,sizeDict in self.filesOfSizeOfCRC.items() for crc in sizeDict})

        lenTemp=1
        while len({crc[0:lenTemp] for crc in AllCrcs})!=allCrcLen:
            lenTemp+=1

        self.CrcCutLen=lenTemp
        self.crccut={crc:crc[0:self.CrcCutLen] for crc in AllCrcs }

    @staticmethod
    def RenameFile(src,dest):
        logging.info(f'renaming file:{src}->{dest}')
        try:
            os.rename(src,dest)
            return False
        except Exception as e:
            logging.error(e)
            return 'Rename error:' + str(e)

    @staticmethod
    def DeleteFile(file):
        logging.info(f'deleting file:{file}')
        try:
            os.remove(file)
            return False
        except Exception as e:
            logging.error(e)
            return 'Delete error:' + str(e)

    @staticmethod
    def CreateSoftLink(src,dest,relative=True):
        logging.info(f'soft-linking {src}<-{dest} (relative:{relative})')
        try:
            if relative:
                destDir = os.path.dirname(dest)
                srcRel = os.path.relpath(src, destDir)
                os.symlink(srcRel,dest)
            else:
                os.symlink(src,dest)
            return False
        except Exception as e:
            logging.error(e)
            return 'Error on soft linking:' + str(e)

    @staticmethod
    def CreateHardLink(src,dest):
        logging.info(f'hard-linking {src}<-{dest}')
        try:
            os.link(src,dest)
            return False
        except Exception as e:
            logging.error(e)
            return 'Error on hard linking:' + str(e)

    def ReduceCrcCut(self,size,crc):
        if size not in self.filesOfSizeOfCRC or crc not in self.filesOfSizeOfCRC[size]:
            del self.crccut[crc]

    def RemoveFromDataPool(self,size,crc,IndexTuple):
        logging.debug(f'RemoveFromDataPool:{size},{crc},{IndexTuple}')
        self.filesOfSizeOfCRC[size][crc].remove(IndexTuple)

        self.CheckCrcPoolAndPrune(size)
        self.ReduceCrcCut(size,crc)

    def DeleteFileWrapper(self,size,crc,IndexTuple):
        logging.debug(f"DeleteFileWrapper:{size},{crc},{IndexTuple}")

        (pathnr,path,file,ctime,dev,inode)=IndexTuple
        FullFilePath=self.ScannedPathFull(pathnr,path,file)

        if IndexTuple in self.filesOfSizeOfCRC[size][crc]:
            if message:=self.DeleteFile(FullFilePath):
                self.Info('Error',message,self.main)
                return message
            else:
                self.RemoveFromDataPool(size,crc,IndexTuple)
        else:
            return 'DeleteFileWrapper - Internal Data Inconsistency:' + FullFilePath + ' / ' + str(IndexTuple)

    def LinkWrapper(self,\
            soft,relative,size,crc,\
            IndexTupleRef,IndexTuplesList):

        logging.debug(f'LinkWrapper:{soft},{relative},{size},{crc}:{IndexTupleRef}:{IndexTuplesList}')

        (pathnrKeep,pathKeep,fileKeep,ctimeKeep,devKeep,inodeKeep)=IndexTupleRef

        FullFilePathKeep=self.ScannedPathFull(pathnrKeep,pathKeep,fileKeep)

        if IndexTupleRef not in self.filesOfSizeOfCRC[size][crc]:
            return 'LinkWrapper - Internal Data Inconsistency:' + FullFilePathKeep + ' / ' + str(IndexTupleRef)
        else :
            for IndexTuple in IndexTuplesList:
                (pathnr,path,file,ctime,dev,inode)=IndexTuple
                FullFilePath=self.ScannedPathFull(pathnr,path,file)

                if IndexTuple not in self.filesOfSizeOfCRC[size][crc]:
                    return 'LinkWrapper - Internal Data Inconsistency:' + FullFilePath + ' / ' + str(IndexTuple)
                else:
                    tempFile=FullFilePath+'.temp'

                    if not self.RenameFile(FullFilePath,tempFile):
                        if soft:
                            AnyProblem=self.CreateSoftLink(FullFilePathKeep,FullFilePath,relative)
                        else:
                            AnyProblem=self.CreateHardLink(FullFilePathKeep,FullFilePath)

                        if AnyProblem:
                            self.RenameFile(tempFile,FullFilePath)
                            return AnyProblem
                        else:
                            if message:=self.DeleteFile(tempFile):
                                self.Info('Error',message,self.main)
                            #self.RemoveFromDataPool(size,crc,IndexTuple)
                            self.filesOfSizeOfCRC[size][crc].remove(IndexTuple)
            if not soft:
                #self.RemoveFromDataPool(size,crc,IndexTupleRef)
                self.filesOfSizeOfCRC[size][crc].remove(IndexTupleRef)

            self.CheckCrcPoolAndPrune(size)
            self.ReduceCrcCut(size,crc)

###########################################################################################################################################

CFG_KEY_STARTUP_ADD_CWD='add_cwd_at_startup'
CFG_KEY_STARTUP_SCAN='scan_at_startup'
CFG_KEY_SHOW_OTHERS='show_other'
CFG_KEY_FULLCRC='show_full_crc'
CFG_KEY_FULLPATHS='show_full_paths'
CFG_KEY_REL_SYMLINKS='relative_symlinks'
CFG_KEY_USE_REG_EXPR='use_reg_expr'

CFG_KEY_GEOMETRY='geometry'
CFG_KEY_GEOMETRY_DIALOG='geometry_dialog'

CFG_KEY_EXCLUDE='exclude'
CFG_KEY_EXCLUDE_REGEXP='excluderegexpp'

MARK='M'
FILE='2'
SINGLE='3'
DIR='0'
LINK='1'
CRC='C'

VERSION='0.90'

class Config:
    def __init__(self,ConfigDir):
        logging.debug(f'Initializing config: {ConfigDir}')
        self.config = configparser.ConfigParser()
        self.config.add_section('main')

        self.path = ConfigDir
        self.file = self.path + '/cfg.ini'

    def Write(self):
        logging.debug('writing config')
        pathlib.Path(self.path).mkdir(parents=True,exist_ok=True)
        with open(self.file, 'w') as configfile:
            self.config.write(configfile)

    def Read(self):
        logging.debug('reading config')
        if os.path.isfile(self.file):
            try:
                with open(self.file, 'r') as configfile:
                    self.config.read_file(configfile)
            except Exception as e:
                logging.error(e)
        else:
            logging.warning(f'no config file:{self.file}')

    def Set(self,key,val):
        self.config.set('main',key,val)

    def Get(self,key,default=None):
        try:
            res=self.config.get('main',key)
        except Exception as e:
            logging.warning(f'gettting config key {key}')
            logging.warning(e)
            res=default
            self.Set(key,str(default))
        return res

def CenterToParentGeometry(widget,parent):
    x = int(parent.winfo_rootx()+0.5*(parent.winfo_width()-widget.winfo_width()))
    y = int(parent.winfo_rooty()+0.5*(parent.winfo_height()-widget.winfo_height()))
            
    return f'+{x}+{y}'
    
def CenterToScreenGeometry(widget):
    x = int(0.5*(widget.winfo_screenwidth()-widget.winfo_width()))
    y = int(0.5*(widget.winfo_screenheight()-widget.winfo_height()))
            
    return f'+{x}+{y}'

###########################################################
class LongActionDialog:
    progressSigns='◐◓◑◒'
    prevMessage=''

    def getNow(self):
        return time.time()*1000.0

    def __init__(self,parent,title,LongActionCommand,ProgressMode1=None,ProgressMode2=None,Progress1LeftText=None,Progress2LeftText=None):
        now=self.getNow()
        self.psIndex =0
        self.CalcNextTime(now)

        self.ProgressMode1=ProgressMode1
        self.ProgressMode2=ProgressMode2

        self.counter=0
        self.AdaptiveCountLimit=1

        self.dialog = tk.Toplevel(parent)
        self.dialog.wm_transient(parent)

        self.dialog.protocol("WM_DELETE_WINDOW", self.Abort)
        self.dialog.bind('<Escape>', self.Abort)

        self.dialog.wm_title(title)
        self.dialog.iconphoto(False, iconphoto)

        (f0:=ttk.Frame(self.dialog)).pack(expand=1,fill='both',side='top')
        (f1:=ttk.Frame(self.dialog)).pack(expand=1,fill='both',side='top')

        self.progr1var = DoubleVar()
        self.progr1=ttk.Progressbar(f0,orient=HORIZONTAL,length=100, mode=ProgressMode1,variable=self.progr1var)
        
        if ProgressMode1:
            self.progr1.grid(row=0,column=1,padx=1,pady=4,sticky='news')

        self.progr1LabLeft=ttk.Label(f0,width=17)
        if Progress1LeftText:
            self.progr1LabLeft.grid(row=0,column=0,padx=1,pady=4)
            self.progr1LabLeft.config(text=Progress1LeftText)

        self.progr1LabRight=ttk.Label(f0,width=17)

        if self.ProgressMode1=='determinate':
            self.progr1LabRight.grid(row=0,column=2,padx=1,pady=4)
            self.Progress1Func=(lambda progress1 : self.progr1var.set(progress1) )
        elif self.ProgressMode1=='indeterminate':
            self.Progress1Func=(lambda progress1 : self.progr1.start())
        else :
            self.Progress1Func=lambda args : None
            
        self.progr2var = DoubleVar()
        self.progr2=ttk.Progressbar(f0,orient=HORIZONTAL,length=100, mode=ProgressMode2,variable=self.progr2var)
        self.progr2LabRight=ttk.Label(f0,width=17)

        if ProgressMode2:
            self.dialog.minsize(550, 60)
            self.progr2.grid(row=1,column=1,padx=1,pady=4,sticky='news')

            if Progress2LeftText:
                self.progr2LabLeft=ttk.Label(f0,width=17)
                self.progr2LabLeft.grid(row=1,column=0,padx=1,pady=4)
                self.progr2LabLeft.config(text=Progress2LeftText)

            self.progr2LabRight.grid(row=1,column=2,padx=1,pady=4)
        else:
            self.dialog.minsize(300, 60)

        f0.grid_columnconfigure(1, weight=1)

        self.message=tk.StringVar()
        ttk.Label(f1,textvariable=self.message,anchor='n',justify='center',width=20).pack(side='top',padx=8,pady=8,expand=1,fill='x')
        ttk.Button(f1, text='Abort', width=10 ,command=self.Abort ).pack(side='bottom',padx=8,pady=8)

        self.LastTimeNoSign=now

        self.dialog.grab_set()
        self.dialog.update()
        self.dialog.geometry(CenterToParentGeometry(self.dialog,parent))

        prevParentCursor=parent.cget('cursor')
        parent.config(cursor="watch")
        
        ####################
        self.KeepGoing=1
        self.NaturalEnd=1
        ####################
        LongActionCommand(self.Update)
        ####################
        self.End()
        
        parent.config(cursor=prevParentCursor)

    def CalcNextTime(self,now):
        self.NextCallTime=now+50.0

    def Abort(self,event=None):
        self.NaturalEnd=0
        self.End()

    def End(self):
        self.KeepGoing=0

        self.dialog.grab_release()
        self.dialog.destroy()

    def Update(self,message,progress1=None,progress2=None,progress1Right=None,progress2Right=None):
        now=self.getNow()
        if now>self.NextCallTime:
            prefix=''
            if self.prevMessage==message:
                if now>self.LastTimeNoSign+1000.0:
                    prefix=str(self.progressSigns[self.psIndex])
                    self.psIndex=(self.psIndex+1)%4
            else:
                self.prevMessage=message
                self.LastTimeNoSign=now

                self.Progress1Func(progress1)
                self.progr1LabRight.config(text=progress1Right)
                self.progr2var.set(progress2)
                self.progr2LabRight.config(text=progress2Right)

            self.message.set(f'{prefix}\n{message}')
            self.dialog.update()

            self.CalcNextTime(now)

        return self.KeepGoing
###########################################################

raw = lambda x : x 

class Gui:

    MAX_PATHS=10

    SelPathnr=None
    SelPath=None
    SelFile=None
    SelCrc=None
    
    pyperclipOperational=True
    
    def WatchCursor(f):
        def wrapp(self,*args,**kwargs):
            if 'parent' in kwargs.keys():
                parent=kwargs['parent']
                prevParentCursor=parent.cget('cursor')
                parent.config(cursor="watch")
                #parent.update()

                res=f(self,*args,**kwargs)
                
                parent.config(cursor=prevParentCursor)
                return res
            else:
                return f(self,*args,**kwargs)
                
        return wrapp
    
    def CheckClipboard(self):
        TestString='Dude-TestString'
        try:
            PrevVal=pyperclip.paste()
            pyperclip.copy(TestString)
        except Exception as e:
            logging.error(e)
            self.pyperclipOperational=False
            logging.error('Clipboard test error. Copy options disabled.')
        else:            
            if pyperclip.paste() != TestString:
                self.pyperclipOperational=False
                logging.error('Clipboard test error. Copy options disabled.')
                if not windows :
                    logging.error('try to install xclip or xsel.')
            else:
                pyperclip.copy(PrevVal)
                logging.info('pyperclip test passed.')
    
    def __init__(self,cwd):
        self.D = CORE()
        self.cwd=cwd

        self.cfg = Config(CONFIG_DIR)
        self.cfg.Read()

        self.PathsToScanFrames=[]
        self.ExcludeFrames=[]

        self.PathsToScanFromDialog=[]
        
        self.CheckClipboard()

        ####################################################################
        self.main = tk.Tk()
        self.main.title(f'Dude (DUplicates DEtector) v{VERSION}')
        self.main.protocol("WM_DELETE_WINDOW", self.exit)
        self.main.minsize(1200, 800)
        self.main.bind('<FocusOut>', self.FocusOut)

        global iconphoto
        iconphoto = PhotoImage(file = os.path.join(os.path.dirname(__file__),'icon.png'))
        self.main.iconphoto(False, iconphoto)

        ####################################################################
        style = ttk.Style()

        if os.name=='posix':
            style.theme_create("dummy", parent='clam')
            self.bg = style.lookup('TFrame', 'background')
            style.theme_use("dummy")
        else:
            style.theme_use("xpnative")

            self.bg = style.lookup('TTButton', 'background')

        ttk.Style().configure("TButton", anchor = "center")

        style.map("TButton",  relief=[('disabled',"flat"),('',"raised")] )
        style.map("TButton",  fg=[('disabled',"gray"),('',"black")] )

        style.map("Treeview.Heading",  relief=[('','raised')] )
        style.configure("Treeview",rowheight=18)

        style.map('Treeview', background=[('focus','#90DD90'),('selected','#AAAAAA'),('',self.bg)],fieldbackground=[('',self.bg)] )

        ttk.Style().map("Treeview.Heading",background = [('pressed', '!focus', 'white'),('active', 'darkgray'),('disabled', '#ffffff')])

        #######################################################################
        self.menubar = tk.Menu(self.main,bg=self.bg,relief='raised')
        self.main.config(menu=self.menubar)
        #######################################################################

        self.StatusVarAllSize=tk.StringVar()
        self.StatusVarAllQuant=tk.StringVar()
        self.StatusVarGroups=tk.StringVar()
        self.StatusVarFullPath=tk.StringVar()
        self.StatusVarPathSize=tk.StringVar()
        self.StatusVarPathQuant=tk.StringVar()

        self.paned = PanedWindow(self.main,orient=tk.VERTICAL,relief='sunken',showhandle=0,bd=0,bg=self.bg)
        self.paned.pack(fill='both',expand=1)

        paned_top = ttk.Frame(self.paned)
        self.paned.add(paned_top)
        paned_bottom = ttk.Frame(self.paned)
        self.paned.add(paned_bottom)

        self.paned.update()
        self.paned.sash_place(0,0,self.cfg.Get('sash_coord',400))

        FrameTop = ttk.Frame(paned_top)
        FrameBottom = ttk.Frame(paned_bottom)

        FrameTop.grid(row=0,column=0,sticky='news')
        FrameBottom.grid(row=0,column=0,sticky='news')

        FrameTop.grid_rowconfigure(0, minsize=400)
        FrameBottom.grid_rowconfigure(0,minsize=400)

        self.main.bind('<KeyPress>', self.KeyPressGlobal )

        (UpperStatusFrame := ttk.Frame(FrameTop)).pack(side='bottom', fill='x')
        self.StatusVarGroups.set('0')
        self.StatusVarFullPath.set('')
        
        tk.Label(UpperStatusFrame,width=10,textvariable=self.StatusVarAllQuant,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=16,text="All marked files # ",relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=10,textvariable=self.StatusVarAllSize,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=18,text='All marked files size: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=10,textvariable=self.StatusVarGroups,borderwidth=2,bg=self.bg,relief='groove',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=10,text='Groups: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=12,text='Full file path: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='left')
        tk.Label(UpperStatusFrame,textvariable=self.StatusVarFullPath,relief='flat',borderwidth=2,bg=self.bg,anchor='w').pack(fill='x',expand=1,side='left')

        (LowerStatusFrame := ttk.Frame(FrameBottom)).pack(side='bottom',fill='both')

        self.SelectedSearchPathCode=tk.StringVar()
        self.SelectedSearchPath=tk.StringVar()

        tk.Label(LowerStatusFrame,width=10,text='Scan Path: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='left')
        tk.Label(LowerStatusFrame,width=2,textvariable=self.SelectedSearchPathCode,borderwidth=2,bg=self.bg,relief='groove',anchor='w').pack(expand=0,side='left')
        tk.Label(LowerStatusFrame,width=30,textvariable=self.SelectedSearchPath,borderwidth=2,bg=self.bg,relief='groove',anchor='w').pack(fill='x',expand=1,side='left')

        tk.Label(LowerStatusFrame,width=10,textvariable=self.StatusVarPathQuant,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(LowerStatusFrame,width=16,text='Marked files # ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(LowerStatusFrame,width=10,textvariable=self.StatusVarPathSize,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(expand=0,side='right')
        tk.Label(LowerStatusFrame,width=18,text='Marked files size: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')

        self.main.unbind_class('Treeview', '<KeyPress-Next>')
        self.main.unbind_class('Treeview', '<KeyPress-Prior>')
        self.main.unbind_class('Treeview', '<KeyPress-space>')
        self.main.unbind_class('Treeview', '<KeyPress-Return>')
        self.main.unbind_class('Treeview', '<KeyPress-Left>')
        self.main.unbind_class('Treeview', '<KeyPress-Right>')
        self.main.unbind_class('Treeview', '<Double-Button-1>')
        
        self.main.bind_class('Treeview','<KeyPress>', self.KeyPressTreeCommon )
        self.main.bind_class('Treeview','<Control-i>',  lambda event : self.MarkOnAll(self.InvertMark) )
        self.main.bind_class('Treeview','<Control-I>',  lambda event : self.MarkOnAll(self.InvertMark) )
        self.main.bind_class('Treeview','<Control-o>',  lambda event : self.MarkOnAllByCTime('oldest',self.SetMark) )
        self.main.bind_class('Treeview','<Control-O>',  lambda event : self.MarkOnAllByCTime('oldest',self.UnsetMark) )
        self.main.bind_class('Treeview','<Control-y>',  lambda event : self.MarkOnAllByCTime('youngest',self.SetMark) )
        self.main.bind_class('Treeview','<Control-Y>',  lambda event : self.MarkOnAllByCTime('youngest',self.UnsetMark) )
        self.main.bind_class('Treeview','<p>',          lambda event : self.MarkLowerPane(self.SetMark) )
        self.main.bind_class('Treeview','<P>',          lambda event : self.MarkLowerPane(self.UnsetMark) )
        self.main.bind_class('Treeview','<Control-j>',  lambda event : self.MarkLowerPane(self.InvertMark) )
        self.main.bind_class('Treeview','<Control-J>',  lambda event : self.MarkLowerPane(self.InvertMark) )
        self.main.bind_class('Treeview','<BackSpace>',  lambda event : self.GoToMaxFolder(1) )
        self.main.bind_class('Treeview','<FocusIn>',    self.TreeEventFocusIn )
        self.main.bind_class('Treeview','<FocusOut>',   self.TreeFocusOout )
        self.main.bind_class('Treeview','<ButtonPress-1>',          self.TreeButtonPress)
        self.main.bind_class('Treeview','<Control-ButtonPress-1>',  lambda event :self.TreeButtonPress(event,True) )
        
        if self.pyperclipOperational:
            self.main.bind_class('Treeview','<Control-c>',  lambda event : self.ClipCopyPath() )
            self.main.bind_class('Treeview','<Control-C>',  lambda event : self.ClipCopyFile() )

        self.main.bind_class('Treeview','<Shift-BackSpace>',            lambda event : self.GoToMaxFolder(0) )
        self.main.bind_class('Treeview','<Control-BackSpace>',          lambda event : self.GoToMaxGroup(1) )
        self.main.bind_class('Treeview','<Control-Shift-BackSpace>',    lambda event : self.GoToMaxGroup(0) )

        self.main.bind_class('Treeview','<Delete>',         lambda event : self.ProcessFiles('delete',0) )
        self.main.bind_class('Treeview','<Shift-Delete>',   lambda event : self.ProcessFiles('delete',1) )

        self.main.bind_class('Treeview','<Insert>',         lambda event : self.ProcessFiles('softlink',0) )
        self.main.bind_class('Treeview','<Shift-Insert>',   lambda event : self.ProcessFiles('softlink',1) )

        self.main.bind_class('Treeview','<Control-Insert>',         lambda event : self.ProcessFiles('hardlink',0) )
        self.main.bind_class('Treeview','<Control-Shift-Insert>',   lambda event : self.ProcessFiles('hardlink',1) )

        self.main.bind_class('Treeview','<KP_Add>',         lambda event : self.MarkExpression('both',self.SetMark,'Mark files') )
        self.main.bind_class('Treeview','<plus>',           lambda event : self.MarkExpression('both',self.SetMark,'Mark files') )
        self.main.bind_class('Treeview','<KP_Subtract>',    lambda event : self.MarkExpression('both',self.UnsetMark,'Unmark files') )
        self.main.bind_class('Treeview','<minus>',          lambda event : self.MarkExpression('both',self.UnsetMark,'Unmark files') )

        self.tree1=ttk.Treeview(FrameTop,takefocus=True,selectmode='none',show=('tree','headings') )

        self.OrgLabel={}
        self.OrgLabel['path']='Subpath'
        self.OrgLabel['file']='File'
        self.OrgLabel['sizeH']='Size'
        self.OrgLabel['instances']='Copies'
        self.OrgLabel['ctimeH']='Change Time'

        self.tree1["columns"]=('pathnr','path','file','size','sizeH','ctime','dev','inode','crc','instances','ctimeH','kind')
        
        #pathnr,path,file,ctime,dev,inode
        self.IndexTupleIndexesWithFnCommon=((int,0),(raw,1),(raw,2),(int,5),(int,6),(int,7))

        self.tree1["displaycolumns"]=('path','file','sizeH','instances','ctimeH')

        self.tree1.column('#0', width=120, minwidth=100, stretch=tk.NO)
        self.tree1.column('path', width=100, minwidth=10, stretch=tk.YES )
        self.tree1.column('file', width=100, minwidth=10, stretch=tk.YES )
        self.tree1.column('sizeH', width=80, minwidth=80, stretch=tk.NO)
        self.tree1.column('instances', width=80, minwidth=80, stretch=tk.NO)
        self.tree1.column('ctimeH', width=150, minwidth=100, stretch=tk.NO)

        self.tree1.heading('#0',text='CRC / Scan Path',anchor=tk.W)
        self.tree1.heading('path',anchor=tk.W,command=lambda : self.ColumnSort(self.tree1, 'path', 'path', False,False,True) )
        self.tree1.heading('file',anchor=tk.W,command=lambda : self.ColumnSort(self.tree1, 'file','file', False,False,True) )
        self.tree1.heading('sizeH',anchor=tk.W,command=lambda : self.ColumnSort(self.tree1,'sizeH', 'size', False,True,True))
        self.tree1.heading('ctimeH',anchor=tk.W,command=lambda : self.ColumnSort(self.tree1, 'ctimeH','ctime', False,True,True))
        self.tree1.heading('instances',anchor=tk.W,command=lambda : self.ColumnSort(self.tree1, 'instances', 'instances', False,True,False))

        vsb1 = tk.Scrollbar(FrameTop, orient='vertical', command=self.tree1.yview,takefocus=False,bg=self.bg)
        self.tree1.configure(yscrollcommand=vsb1.set)

        vsb1.pack(side='right',fill='y',expand=0)
        self.tree1.pack(fill='both',expand=1, side='left')

        

        self.tree1.bind('<KeyRelease>',             self.Tree1KeyRelease )
        self.tree1.bind('<Double-Button-1>',        self.TreeEventOpenFile)
        
        self.tree1.bind('<Control-a>', lambda event : self.MarkOnAll(self.SetMark) )
        self.tree1.bind('<Control-A>', lambda event : self.MarkOnAll(self.SetMark) )
        self.tree1.bind('<Control-n>', lambda event : self.MarkOnAll(self.UnsetMark) )
        self.tree1.bind('<Control-N>', lambda event : self.MarkOnAll(self.UnsetMark) )

        self.tree1.bind('<a>', lambda event : self.MarkInCRCGroup(self.SetMark) )
        self.tree1.bind('<A>', lambda event : self.MarkInCRCGroup(self.SetMark) )
        self.tree1.bind('<n>', lambda event : self.MarkInCRCGroup(self.UnsetMark) )
        self.tree1.bind('<N>', lambda event : self.MarkInCRCGroup(self.UnsetMark) )

        self.tree1.bind('<o>', lambda event : self.MarkInCRCGroupByCTime('oldest',self.InvertMark) )
        self.tree1.bind('<O>', lambda event : self.MarkInCRCGroupByCTime('oldest',self.InvertMark) )
        self.tree1.bind('<y>', lambda event : self.MarkInCRCGroupByCTime('youngest',self.InvertMark) )
        self.tree1.bind('<Y>', lambda event : self.MarkInCRCGroupByCTime('youngest',self.InvertMark) )
        
        self.tree1.bind('<i>', lambda event : self.MarkInCRCGroup(self.InvertMark) )
        self.tree1.bind('<I>', lambda event : self.MarkInCRCGroup(self.InvertMark) )

        self.tree2=ttk.Treeview(FrameBottom,takefocus=True,selectmode='none')

        self.tree2['columns']=('pathnr','path','file','size','sizeH','ctime','dev','inode','crc','instances','instancesnum','ctimeH','kind')
        
        self.tree2['displaycolumns']=('file','sizeH','instances','ctimeH')

        self.tree2.column('#0', width=120, minwidth=100, stretch=tk.NO)

        self.tree2.column('file', width=200, minwidth=100, stretch=tk.YES)
        self.tree2.column('sizeH', width=80, minwidth=80, stretch=tk.NO)
        self.tree2.column('instances', width=80, minwidth=80, stretch=tk.NO)
        self.tree2.column('ctimeH', width=150, minwidth=100, stretch=tk.NO)

        self.tree2.heading('#0',text='CRC',anchor=tk.W)
        self.tree2.heading('path',anchor=tk.W)
        self.tree2.heading('file',anchor=tk.W,command=lambda : self.ColumnSort(self.tree2, 'file', 'file', False))
        self.tree2.heading('sizeH',anchor=tk.W,command=lambda : self.ColumnSort(self.tree2, 'sizeH', 'size', False, 1))
        self.tree2.heading('ctimeH',anchor=tk.W,command=lambda : self.ColumnSort(self.tree2, 'ctimeH', 'ctime', False,1))
        self.tree2.heading('instances',anchor=tk.W,command=lambda : self.ColumnSort(self.tree2, 'instances', 'instancesnum', False,1))

        for tree in [self.tree1,self.tree2]:
            for col in tree["displaycolumns"]:
                if col in self.OrgLabel:
                    tree.heading(col,text=self.OrgLabel[col])

        self.tree2.heading('sizeH', text='Size \u25BC')

        vsb2 = tk.Scrollbar(FrameBottom, orient='vertical', command=self.tree2.yview,takefocus=False,bg=self.bg)
        self.tree2.configure(yscrollcommand=vsb2.set)

        vsb2.pack(side='right',fill='y',expand=0)
        self.tree2.pack(fill='both',expand=1,side='left')

        self.tree2.bind('<KeyRelease>',             self.Tree2KeyRelease )
        self.tree2.bind('<Double-Button-1>',        self.TreeEventOpenFile)
        
        self.tree2.bind('<a>', lambda event : self.MarkLowerPane(self.SetMark) )
        self.tree2.bind('<A>', lambda event : self.MarkLowerPane(self.SetMark) )
        self.tree2.bind('<n>', lambda event : self.MarkLowerPane(self.UnsetMark) )
        self.tree2.bind('<N>', lambda event : self.MarkLowerPane(self.UnsetMark) )

        self.tree2.bind('<i>', lambda event : self.MarkLowerPane(self.InvertMark) )
        self.tree2.bind('<I>', lambda event : self.MarkLowerPane(self.InvertMark) )

        paned_top.grid_columnconfigure(0, weight=1)
        paned_top.grid_rowconfigure(0, weight=1,minsize=200)

        paned_bottom.grid_columnconfigure(0, weight=1)
        paned_bottom.grid_rowconfigure(0, weight=1,minsize=200)

        self.tree1.tag_configure(MARK, foreground='red')
        self.tree2.tag_configure(MARK, foreground='red')

        self.tree1.tag_configure(CRC, foreground='gray')

        self.tree2.tag_configure(SINGLE, foreground='gray')
        self.tree2.tag_configure(DIR, foreground='blue2')
        self.tree2.tag_configure(LINK, foreground='darkgray')

        self.SetDefaultGeometryAndShow(self.main,None)

        #######################################################################
        #scan dialog

        self.ScanDialog = tk.Toplevel(self.main)
        self.ScanDialog.protocol("WM_DELETE_WINDOW", self.ScanDialogClose)
        self.ScanDialog.minsize(600, 400)
        self.ScanDialog.wm_transient(self.main)
        self.ScanDialog.update()
        self.ScanDialog.withdraw()
        self.ScanDialog.iconphoto(False, iconphoto)

        self.ScanDialogMainFrame = ttk.Frame(self.ScanDialog)
        self.ScanDialogMainFrame.pack(expand=1, fill='both')

        self.ScanDialog.config(bd=0, relief=FLAT)

        #font1 = font.Font(name='TkCaptionFont', exists=True)
        #font1.config(family='courier new', size=10)

        self.ScanDialog.title('Scan')

        self.sizeMinVar=tk.StringVar()
        self.sizeMaxVar=tk.StringVar()
        self.ResultsLimitVar=tk.StringVar()
        self.WriteScanToLog=tk.BooleanVar()

        self.ResultsLimitVar.set(self.cfg.Get('resultsLimit','1000'))
        self.WriteScanToLog.set(False)

        self.ScanDialogMainFrame.grid_columnconfigure(0, weight=1)
        self.ScanDialogMainFrame.grid_rowconfigure(0, weight=1)
        self.ScanDialogMainFrame.grid_rowconfigure(1, weight=1)

        self.ScanDialog.bind('<Escape>', self.ScanDialogClose)
        self.ScanDialog.bind('<Alt_L><a>',lambda event : self.AddPathDialog())
        self.ScanDialog.bind('<Alt_L><A>',lambda event : self.AddPathDialog())
        self.ScanDialog.bind('<Alt_L><s>',lambda event : self.Scan())
        self.ScanDialog.bind('<Alt_L><S>',lambda event : self.Scan())
    
        self.ScanDialog.bind('<Alt_L><D>',lambda event : self.AddDrives())
        self.ScanDialog.bind('<Alt_L><d>',lambda event : self.AddDrives())
        
        self.ScanDialog.bind('<Alt_L><E>',lambda event : self.AddExckludeMaskDialog())
        self.ScanDialog.bind('<Alt_L><e>',lambda event : self.AddExckludeMaskDialog())

        ##############
        self.pathsFrame = tk.LabelFrame(self.ScanDialogMainFrame,text='Paths To Scan:',borderwidth=2,bg=self.bg)
        self.pathsFrame.grid(row=0,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        self.AddPathButton = ttk.Button(self.pathsFrame,width=10,text="Add Path ...",command=self.AddPathDialog,underline=0)
        self.AddPathButton.grid(column=0, row=100,pady=4,padx=4)
        
        self.AddDrivesButton = ttk.Button(self.pathsFrame,width=10,text="Add drives",command=self.AddDrives,underline=4)
        self.AddDrivesButton.grid(column=1, row=100,pady=4,padx=4)

        self.ClearListButton=ttk.Button(self.pathsFrame,width=10,text="Clear List",command=self.ClearPaths )
        self.ClearListButton.grid(column=2, row=100,pady=4,padx=4)

        self.pathsFrame.grid_columnconfigure(1, weight=1)
        self.pathsFrame.grid_rowconfigure(99, weight=1)
        
        ##############
        self.ScanExcludeRegExpr=tk.BooleanVar()
        self.ScanExcludeRegExpr.set(self.cfg.Get(CFG_KEY_EXCLUDE_REGEXP,False) == 'True')
        
        self.ExcludeFRame = tk.LabelFrame(self.ScanDialogMainFrame,text='Exclude from scan:',borderwidth=2,bg=self.bg)
        self.ExcludeFRame.grid(row=1,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        self.AddExckludeMaskButton = ttk.Button(self.ExcludeFRame,width=16,text="Add Exclude Mask ...",command=self.AddExckludeMaskDialog,underline=4)
        self.AddExckludeMaskButton.grid(column=0, row=100,pady=4,padx=4)

        self.ClearExcludeListButton=ttk.Button(self.ExcludeFRame,width=10,text="Clear List",command=self.ClearExcludeMasks )
        self.ClearExcludeListButton.grid(column=2, row=100,pady=4,padx=4)

        self.ExcludeFRame.grid_columnconfigure(1, weight=1)
        self.ExcludeFRame.grid_rowconfigure(99, weight=1)
        ##############
        
        tk.Label(self.ScanDialogMainFrame,text='Limit scan groups main results number to biggest:',borderwidth=2,anchor='w',bg=self.bg).grid(row=2,column=0,sticky='news',padx=4,pady=4,columnspan=3)
        ttk.Button(self.ScanDialogMainFrame,textvariable=self.ResultsLimitVar,command=self.setResultslimit,width=10).grid(row=2,column=3,sticky='wens',padx=8,pady=3)
        
        ttk.Checkbutton(self.ScanDialogMainFrame,text='Write scan results to application log',variable=self.WriteScanToLog).grid(row=3,column=0,sticky='news',padx=8,pady=3,columnspan=3)

        frame2 = ttk.Frame(self.ScanDialogMainFrame)
        frame2.grid(row=6,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        ttk.Button(frame2,width=12,text="Scan",command=self.Scan,underline=0).pack(side='right',padx=4,pady=4)
        ttk.Button(frame2,width=12,text="Cancel",command=self.ScanDialogClose ).pack(side='left',padx=4,pady=4)

        #######################################################################
        #Settings Dialog
        self.SetingsDialog = tk.Toplevel(self.main)
        self.SetingsDialog.protocol("WM_DELETE_WINDOW", self.SettingsDialogClose)
        self.SetingsDialog.minsize(400, 300)
        self.SetingsDialog.wm_transient(self.main)
        self.SetingsDialog.update()
        self.SetingsDialog.withdraw()
        self.SetingsDialog.iconphoto(False, iconphoto)

        self.addCwdAtStartup = tk.BooleanVar()
        self.addCwdAtStartup.set(self.cfg.Get(CFG_KEY_STARTUP_ADD_CWD,True))

        self.scanAtStartup = tk.BooleanVar()
        self.scanAtStartup.set(self.cfg.Get(CFG_KEY_STARTUP_SCAN,True))

        self.showothers = tk.BooleanVar()
        self.showothers.set(self.cfg.Get(CFG_KEY_SHOW_OTHERS,False))

        self.fullCRC = tk.BooleanVar()
        self.fullCRC.set(self.cfg.Get(CFG_KEY_FULLCRC,False))

        self.fullPaths = tk.BooleanVar()
        self.fullPaths.set(self.cfg.Get(CFG_KEY_FULLPATHS,False))

        self.relSymlinks = tk.BooleanVar()
        self.relSymlinks.set(self.cfg.Get(CFG_KEY_REL_SYMLINKS,False))

        self.useRegExpr = tk.BooleanVar()
        self.useRegExpr.set(self.cfg.Get(CFG_KEY_USE_REG_EXPR,False))

        self.SetingsDialog.wm_title('Settings')

        fr=ttk.Frame(self.SetingsDialog)
        fr.pack(expand=1,fill='both')

        def AddPathAtStartupChange(self):
            if not self.addCwdAtStartup.get():
                self.scanAtStartup.set(False)

        def ScanAtStartupChange(self):
            if self.scanAtStartup.get():
                self.addCwdAtStartup.set(True)

        row = 0
        self.AddCwdCB=ttk.Checkbutton(fr, text = 'At startup add current directory to paths to scan', variable=self.addCwdAtStartup,command=lambda : AddPathAtStartupChange(self) )
        self.AddCwdCB.grid(row=row,column=0,sticky='wens') ; row+=1
        self.StartScanCB=ttk.Checkbutton(fr, text = 'Start scanning at startup', variable=self.scanAtStartup,command=lambda : ScanAtStartupChange(self)                              )
        self.StartScanCB.grid(row=row,column=0,sticky='wens') ; row+=1

        ttk.Checkbutton(fr, text = 'Show other files on Directory pane', variable=self.showothers               ).grid(row=row,column=0,sticky='wens') ; row+=1
        ttk.Checkbutton(fr, text = 'Show full CRC', variable=self.fullCRC                                       ).grid(row=row,column=0,sticky='wens') ; row+=1
        ttk.Checkbutton(fr, text = 'Show full paths', variable=self.fullPaths                                   ).grid(row=row,column=0,sticky='wens') ; row+=1
        ttk.Checkbutton(fr, text = 'Create relative Symbolic links', variable=self.relSymlinks                  ).grid(row=row,column=0,sticky='wens') ; row+=1
        ttk.Checkbutton(fr, text = 'Use regular expressions matching', variable=self.useRegExpr                 ).grid(row=row,column=0,sticky='wens') ; row+=1

        bfr=ttk.Frame(fr)
        fr.grid_rowconfigure(row, weight=1); row+=1

        bfr.grid(row=row,column=0) ; row+=1

        ttk.Button(bfr, text=' Set Defaults ', width=14, command=self.SettingsDialogReset).pack(side='left', anchor='n',padx=5,pady=5)
        ttk.Button(bfr, text='OK', width=14, command=self.SettingsDialogOK ).pack(side='left', anchor='n',padx=5,pady=5)

        self.SetingsDialogDefault=ttk.Button(bfr, text='Close', width=14 ,command=self.SettingsDialogClose )
        self.SetingsDialogDefault.pack(side='right', anchor='n',padx=5,pady=5)

        fr.grid_columnconfigure(0, weight=1)

        self.SetingsDialog.bind('<Escape>', self.SettingsDialogClose )

        try:
            self.license=pathlib.Path(os.path.join(os.path.dirname(__file__),'LICENSE')).read_text()
        except Exception as e:
            logging.error(e)
            self.exit()

        try:
            self.keyboardshortcuts=pathlib.Path(os.path.join(os.path.dirname(__file__),'keyboard.shortcuts.txt')).read_text()
        except Exception as e:
            logging.error(e)
            self.exit()
        #######################################################################
        #menu

        def MarkCascadePathFill():
            row=0
            MarkCascadePath.delete(0,END)
            for path in self.D.ScannedPaths:
                MarkCascadePath.add_command(label = nums[row] + '  =  ' + path,    command  = lambda pathpar=path: self.ActionOnSpecifiedPath(pathpar,self.SetMark)  )
                row+=1

        def UnmarkCascadePathFill():
            UnmarkCascadePath.delete(0,END)
            row=0
            for path in self.D.ScannedPaths:
                UnmarkCascadePath.add_command(label = nums[row] + '  =  ' + path,  command  = lambda pathpar=path: self.ActionOnSpecifiedPath(pathpar,self.UnsetMark)  )
                row+=1

        MainCascade= Menu(self.menubar,tearoff=0,bg=self.bg)
        MainCascade.add_command(label = 'Scan',command = self.ScanDialogShow, accelerator="S")
        MainCascade.add_separator()
        MainCascade.add_command(label = 'Settings',command=self.SettingsDialogShow, accelerator="F2")
        MainCascade.add_separator()
        MainCascade.add_command(label = 'go to biggest group (size sum)',command = lambda : self.GoToMaxGroup(1) , accelerator="Ctrl+Backspace")
        MainCascade.add_command(label = 'go to biggest group (quantity)',command = lambda : self.GoToMaxGroup(0) , accelerator="Ctrl+Shift+Backspace")
        MainCascade.add_command(label = 'go to biggest folder (size sum)',command = lambda : self.GoToMaxFolder(1),accelerator="Backspace")
        MainCascade.add_command(label = 'go to biggest folder (quantity)',command = lambda : self.GoToMaxFolder(0) ,accelerator="Shift-Backspace")
        MainCascade.add_separator()
        MainCascade.add_command(label = 'Open File',command = self.TreeEventOpenFile,accelerator="F3 / Return")
        MainCascade.add_command(label = 'Open Folder',command = self.OpenFolder)
        MainCascade.add_separator()
        MainCascade.add_command(label = 'Copy File Name To Clipboard',command = self.ClipCopyFile,accelerator="Ctrl+Shift+C",state = 'normal' if self.pyperclipOperational else 'disabled')
        MainCascade.add_command(label = 'Copy Path To Clipboard',command = self.ClipCopyPath,accelerator="Ctrl+C",state = 'normal' if self.pyperclipOperational else 'disabled')
        MainCascade.add_separator()
        MainCascade.add_command(label = 'Erase CRC Cache',command = self.CleanCache)
        MainCascade.add_separator()
        MainCascade.add_command(label = 'Exit',command = self.exit)
        self.menubar.add_cascade(label = 'File',menu = MainCascade,accelerator="Alt+F")

        MarkCascade= Menu(self.menubar,tearoff=0,bg=self.bg)
        MarkCascade.add_command(label = "All files",        command = lambda : self.MarkOnAll(self.SetMark),accelerator="Ctrl+A")
        MarkCascade.add_separator()
        MarkCascade.add_command(label = "Oldest files",     command = lambda : self.MarkOnAllByCTime('oldest',self.SetMark),accelerator="Ctrl+O")
        MarkCascade.add_command(label = "Youngest files",   command = lambda : self.MarkOnAllByCTime('youngest',self.SetMark),accelerator="Ctrl+Y")
        MarkCascade.add_separator()
        MarkCascade.add_command(label = "Files on the same path",  command = lambda : self.MarkPathOfFile(self.SetMark),accelerator="Ctrl+P")
        MarkCascade.add_command(label = "Specified Directory ...",   command = lambda : self.MarkSubpath(self.SetMark))
        MarkCascadePath = Menu(self.menubar, tearoff = 0,postcommand=MarkCascadePathFill,bg=self.bg)
        MarkCascade.add_cascade(label = "Scan path",             menu = MarkCascadePath)
        MarkCascade.add_separator()
        MarkCascade.add_command(label = "Expression on file  ...",          command = lambda : self.MarkExpression('file',self.SetMark,'Mark files'))
        MarkCascade.add_command(label = "Expression on sub-path ...",       command = lambda : self.MarkExpression('path',self.SetMark,'Mark files'))
        MarkCascade.add_command(label = "Expression on file with path ...", command = lambda : self.MarkExpression('both',self.SetMark,'Mark files'),accelerator="+")

        UnmarkCascade= Menu(self.menubar,tearoff=0,bg=self.bg)
        UnmarkCascade.add_command(label = "All files",   command = lambda : self.MarkOnAll(self.UnsetMark),accelerator="Ctrl+Shift+A / Ctrl+N")
        UnmarkCascade.add_separator()
        UnmarkCascade.add_command(label = "Oldest files",         command = lambda : self.MarkOnAllByCTime('oldest',self.UnsetMark),accelerator="Ctrl+Shift+O")
        UnmarkCascade.add_command(label = "Youngest files",       command = lambda : self.MarkOnAllByCTime('youngest',self.UnsetMark),accelerator="Ctrl+Shift+Y")
        UnmarkCascade.add_separator()
        UnmarkCascade.add_command(label = "Files on the same path",             command = lambda : self.MarkPathOfFile(self.UnsetMark),accelerator="Ctrl+Shift+P")
        UnmarkCascade.add_command(label = "Specified Directory ...",            command = lambda : self.MarkSubpath(self.UnsetMark))
        UnmarkCascadePath = Menu(self.menubar, tearoff = 0,postcommand=UnmarkCascadePathFill,bg=self.bg)
        UnmarkCascade.add_cascade(label = "Scan path",             menu = UnmarkCascadePath)
        UnmarkCascade.add_separator()
        UnmarkCascade.add_command(label = "Expression on file ...",           command = lambda : self.MarkExpression('file',self.UnsetMark,'Unmark files'))
        UnmarkCascade.add_command(label = "Expression on sub-path ...",       command = lambda : self.MarkExpression('path',self.UnsetMark,'Unmark files'))
        UnmarkCascade.add_command(label = "Expression on file with path ...", command = lambda : self.MarkExpression('both',self.UnsetMark,'Unmark files'),accelerator="-")

        MarkingCommonCascade= Menu(self.menubar,tearoff=0,bg=self.bg)
        MarkingCommonCascade.add_cascade(label = 'Set',menu = MarkCascade)
        MarkingCommonCascade.add_cascade(label = 'Unset',menu = UnmarkCascade)
        MarkingCommonCascade.add_command(label = 'Invert',command = lambda : self.MarkOnAll(self.InvertMark),accelerator="Ctrl+I / *")
        self.menubar.add_cascade(label = 'Mark',menu = MarkingCommonCascade)

        ActionCascade= Menu(self.menubar,tearoff=0,bg=self.bg)

        ActionCascade.add_command(label = 'Remove Local Marked Files',command=lambda : self.ProcessFiles('delete',0),accelerator="Delete")
        ActionCascade.entryconfig(3,foreground='red',activeforeground='red')
        ActionCascade.add_command(label = 'Remove All Marked Files',command=lambda : self.ProcessFiles('delete',1),accelerator="Shift+Delete")
        ActionCascade.entryconfig(4,foreground='red',activeforeground='red')
        ActionCascade.add_separator()
        ActionCascade.add_command(label = 'Softlink Local Marked Files',command=lambda : self.ProcessFiles('softlink',0),accelerator="Insert")
        ActionCascade.entryconfig(6,foreground='red',activeforeground='red')
        ActionCascade.add_command(label = 'Softlink All Marked Files',command=lambda : self.ProcessFiles('softlink',1),accelerator="Shift+Insert")
        ActionCascade.entryconfig(7,foreground='red',activeforeground='red')
        ActionCascade.add_separator()
        ActionCascade.add_command(label = 'Hardlink Local Marked Files',command=lambda : self.ProcessFiles('hardlink',0),accelerator="Ctrl+Insert")
        ActionCascade.entryconfig(9,foreground='red',activeforeground='red')
        ActionCascade.add_command(label = 'Hardlink All Marked Files',command=lambda : self.ProcessFiles('hardlink',1),accelerator="Shift+Ctrl+Insert")
        ActionCascade.entryconfig(10,foreground='red',activeforeground='red')
        self.menubar.add_cascade(label = 'Action',menu = ActionCascade)

        HelpCascade= Menu(self.menubar,tearoff=0,bg=self.bg)
        HelpCascade.add_command(label = 'About',command=self.About)
        HelpCascade.add_command(label = 'Keyboard Shortcuts',command=self.KeyboardShortcuts,accelerator="F1")
        HelpCascade.add_command(label = 'License',command=self.License)
        self.menubar.add_cascade(label = 'Help',menu = HelpCascade)

        #######################################################################

        if (self.cfg.Get(CFG_KEY_STARTUP_ADD_CWD,'True')=='True'):
            self.addPath(cwd)

        self.ScanDialogShow()

        if (self.cfg.Get(CFG_KEY_STARTUP_SCAN,'True')=='True'):
            self.ScanDialogMainFrame.after(0, self.Scan)

        self.ColumnSortLastParams={}
        self.ColumnSortLastParams[self.tree1]=['sizeH','size',1,1,False]
        self.ColumnSortLastParams[self.tree2]=['sizeH','size',1,1,True]

        self.ShowData()
        self.main.mainloop()

    def GetIndexTupleTree1(self,item):
        return self.GetIndexTuple(item,self.tree1)

    def GetIndexTupleTree2(self,item):
        return self.GetIndexTuple(item,self.tree2)

    def GetIndexTuple(self,item,tree):
        return tuple([ fn(tree.item(item)['values'][index]) for fn,index in self.IndexTupleIndexesWithFnCommon ])

    def exit(self):
        self.GeometryStore(self.main)
        self.ScanDialog.destroy()
        self.SetingsDialog.destroy()
        self.StoreSplitter()
        exit()

    def WidgetId(self,widget):
        wid=widget.wm_title()
        wid=wid.replace(' ','_')
        wid=wid.replace('!','_')
        wid=wid.replace('?','_')
        wid=wid.replace('(','_')
        wid=wid.replace(')','_')
        wid=wid.replace('.','_')
        return 'geo_' + wid
    
    def SetDefaultGeometryAndShow(self,widget,parent):
        if parent :
            parent.update()
        widget.update()
        
        CfgGeometry=self.cfg.Get(self.WidgetId(widget),None)
        
        if CfgGeometry != None and CfgGeometry != 'None':
            widget.geometry(CfgGeometry)
        elif parent :
            widget.geometry(CenterToParentGeometry(widget,parent))
        else:
            widget.geometry(CenterToScreenGeometry(widget))
            
        widget.update()
        widget.deiconify()

    def GeometryStore(self,widget):
        self.cfg.Set(self.WidgetId(widget),str(widget.geometry()))
        self.cfg.Write()

    def DialogWithEntry(self,title,prompt,parent,initialvalue='',OnlyInfo=False):
        parent.config(cursor="watch")
        
        dialog = tk.Toplevel(parent)
        dialog.minsize(400, 140)
        dialog.wm_transient(parent)
        dialog.update()
        dialog.withdraw()
        dialog.wm_title(title)
        dialog.config(bd=2, relief=FLAT,bg=self.bg)
        dialog.iconphoto(False, iconphoto)
        
        res=set()
        
        EntryVar=tk.StringVar(value=initialvalue)

        def over():
            self.GeometryStore(dialog)
            dialog.destroy()
            parent.config(cursor="")
            try:
                dialog.update()
            except Exception as e:
                pass

        def Yes(event=None):
            over()
            nonlocal res
            nonlocal EntryVar
            res.add(EntryVar.get())

        def No(event=None):
            over()
            nonlocal res
            res.add(False)

        dialog.protocol("WM_DELETE_WINDOW", No)
        
        def ReturnPressed(event=None):
            nonlocal dialog
            nonlocal ok
            nonlocal entry
            
            focus=dialog.focus_get()
            if focus==ok or focus==entry:
                Yes()
            else:
                No()

        ttk.Label(dialog,text=prompt,anchor='n',justify='center').grid(sticky='news',row=0,column=0,padx=5,pady=5)
        if not OnlyInfo:
            (entry:=ttk.Entry(dialog,textvariable=EntryVar)).grid(sticky='news',row=1,column=0,padx=5,pady=5)
        
        (bfr:=ttk.Frame(dialog)).grid(sticky='news',row=2,column=0,padx=5,pady=5)
        
        if OnlyInfo:
            ok=default=ttk.Button(bfr, text='OK', width=10 ,command=No )
            ok.pack()
        else:
            ok=ttk.Button(bfr, text='OK', width=10, command=Yes)
            ok.pack(side='left', anchor='e',padx=5,pady=5)
            default=cancel=ttk.Button(bfr, text='Cancel', width=10 ,command=No )
            cancel.pack(side='right', anchor='w',padx=5,pady=5)

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        dialog.bind('<Escape>', No)
        dialog.bind('<KeyPress-Return>', ReturnPressed)
        
        PrevGrab = dialog.grab_current() 
        
        self.SetDefaultGeometryAndShow(dialog,parent)
            
        if OnlyInfo:
            ok.focus_set()
        else:
            entry.focus_set()
        
        dialog.grab_set()
        parent.wait_window(dialog)
        
        if PrevGrab:
            PrevGrab.grab_set()
        else:
            dialog.grab_release()

        return next(iter(res))
        
    def dialog(self,parent,title,message,OnlyInfo=False,textwidth=128,width=800,height=400):
        parent.config(cursor="watch")
        
        dialog = tk.Toplevel(parent)
        dialog.minsize(width,height)
        dialog.wm_transient(parent)
        dialog.update()
        dialog.withdraw()
        dialog.wm_title(title)
        dialog.config(bd=2, relief=FLAT,bg=self.bg)
        dialog.iconphoto(False, iconphoto)
        
        res=set()
        
        def over():
            self.GeometryStore(dialog)
            dialog.destroy()
            parent.config(cursor="")
            try:
                dialog.update()
            except Exception as e:
                pass

        def Yes(event=None):
            over()
            nonlocal res
            res.add(True)

        def No(event=None):
            over()
            nonlocal res
            res.add(False)
        
        dialog.protocol("WM_DELETE_WINDOW", No)

        def ReturnPressed(event=None):
            nonlocal dialog
            nonlocal default
            
            focus=dialog.focus_get()
            if focus==default:
                No()
            else:
                Yes()
                
        st=scrolledtext.ScrolledText(dialog,relief='groove', bd=2,bg=self.bg,width = textwidth )
        st.frame.config(bg=self.bg,takefocus=False)
        st.vbar.config(bg=self.bg,takefocus=False)

        st.insert(END,message)
        st.configure(state=DISABLED)
        st.grid(row=0,column=0,sticky='news',padx=5,pady=5)

        bfr=ttk.Frame(dialog)
        bfr.grid(row=2,column=0)

        if OnlyInfo:
            default=ttk.Button(bfr, text='OK', width=10 ,command=No )
            default.pack()
        else:
            ttk.Button(bfr, text='OK', width=10, command=Yes).pack(side='left', anchor='e',padx=5,pady=5)
            default=ttk.Button(bfr, text='Cancel', width=10 ,command=No )
            default.pack(side='right', anchor='w',padx=5,pady=5)

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        dialog.bind('<Escape>', No)
        dialog.bind('<KeyPress-Return>', ReturnPressed)
        
        PrevGrab = dialog.grab_current() 
        
        self.SetDefaultGeometryAndShow(dialog,parent)
        
        dialog.grab_set()
        default.focus_set()
        parent.wait_window(dialog)
        
        if PrevGrab:
            PrevGrab.grab_set()
        else:
            dialog.grab_release()

        return next(iter(res))

    def Ask(self,title,message,top,width=1000,height=400):
        return self.dialog(top,title,message,False,width=width,height=height)

    def Info(self,title,message,top,textwidth=128,width=400,height=200):
        return self.dialog(top,title,message,True,textwidth=textwidth,width=width,height=height)

    def ToggleSelectedTag(self,tree, *items):
        for item in items:
            if tree.set(item,'kind')==FILE:
                self.InvertMark(item, self.tree1)
                try:
                    self.tree2.item(item,tags=self.tree1.item(item)['tags'])
                except Exception :
                    pass

        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()
    
    def KeyPressGlobal(self,event):
        if event.keysym=='F1':
            self.KeyboardShortcuts()
        elif event.keysym=='F2':
            self.SettingsDialogShow()
        elif event.keysym in ('s','S') :
            self.ScanDialogShow()
    
    def TreeEventFocusIn(self,event):
        tree=event.widget
        
        item=tree.focus()
        if not item:
            item=tree.selection()
        
        tree.selection_remove(tree.selection())

        if item:
            if tree==self.tree1:
                self.Tree1SelChange(item,True)
            else:
                self.Tree2SelChange(item)
                
            tree.see(item)
            tree.focus(item)
            tree.update()

        if len(self.tree2.get_children())==0:
            self.tree1.focus_set()
            
    def TreeFocusOout(self,event):
        tree=event.widget
        tree.selection_set(tree.focus())
    
    def TreeButtonPress(self,event,toggle=False):
        tree=event.widget
        tree.selection_remove(tree.selection())
        
        item=tree.identify('item',event.x,event.y)
        
        if item:
            tree.focus(item)
            
        if self.main.focus_get()!=tree:
            self.main.focus_set()
            tree.focus_set()
            SelChangeDone=True
        else:
            SelChangeDone=False
        
        if item:
            if tree.identify("region", event.x, event.y) != 'heading':
                
                if not SelChangeDone:
                    if tree==self.tree1:
                        self.Tree1SelChange(item)
                    else:
                        self.Tree2SelChange(item)
                
                if toggle:
                    self.ToggleSelectedTag(tree,item)
                    
    def KeyPressTreeCommon(self,event):
        if event.keysym in ("Up",'Down') :
            return
        elif event.keysym == "Right":
            self.GotoNextMark(event.widget,1)
        elif event.keysym == "Left":
            self.GotoNextMark(event.widget,-1)
        elif event.keysym == "Tab":
            tree=event.widget
            tree.selection_set(tree.focus())
        elif event.keysym=='KP_Multiply' or event.keysym=='asterisk':
            self.MarkOnAll(self.InvertMark)
        elif event.keysym=='F3' or event.keysym=='Return':
            tree=event.widget
            item=tree.focus()
            if item:
                if tree.set(item,'kind')!=CRC:
                    self.TreeEventOpenFile()
        else:
            #print(event.keysym)
            pass

    def ColumnSort(self, tree, colname, col, reverse, asnumber=0,level2=False):
        prev_colname,prev_col,prev_reverse,prev_asnumber,prev_level2=self.ColumnSortLastParams[tree]
        self.ColumnSortLastParams[tree]=[colname,col,reverse,asnumber,level2]

        l = [(tree.set(item,col), item) for item in tree.get_children('')]
        l.sort(reverse=reverse,key=lambda x: (float(x[0]) if x[0].isdigit() else 0) if asnumber else x[0])

        for index, (val,k) in enumerate(l):
            tree.move(k, '', index)

        if level2:
            for topItem in tree.get_children():
                l = [(tree.set(item,col), item) for item in tree.get_children(topItem)]
                l.sort(reverse=reverse,key=lambda x: (float(x[0]) if x[0].isdigit() else 0) if asnumber else x[0])

                for index, (val,item) in enumerate(l):
                    tree.move(item, topItem, index)

        tree.see(tree.focus() if tree.focus() else tree.selection())
        tree.update()

        # reverse sort next time + indicator
        tree.heading(prev_colname, text=self.OrgLabel[prev_colname])
        tree.heading(colname, command=lambda : self.ColumnSort(tree, colname, col, not reverse,asnumber,level2 ), text=self.OrgLabel[colname] + ' ' + str(u'\u25BC' if reverse else u'\u25B2') )

    def addPath(self,path):
        if len(self.PathsToScanFromDialog)<10:
            self.PathsToScanFromDialog.append(path)
            self.UpdatePathsToScan()
        else:
            logging.error(f'cant add:{path}. limit exceeded')

    def Scan(self):
        resultslimitStr=self.ResultsLimitVar.get()

        try:
            resultslimit = int(resultslimitStr)
        except Exception as e:
            self.DialogWithEntry(title='Error',prompt='Results limit wrong format: \'' + resultslimitStr + '\'\n' + e,parent=self.ScanDialog,OnlyInfo=True)
            return

        self.cfg.Set('resultslimit',resultslimitStr)

        self.cfg.Write()

        self.D.INIT()
        self.ShowData()

        self.D.setLimit(resultslimit)

        PathsToScanFromEntry = [var.get() for var in self.PathsToScanEntryVar.values()]
        
        ExcludeVarsFromEntry = [var.get() for var in self.ExcludeEntryVar.values()]
        
        if not PathsToScanFromEntry:
            self.DialogWithEntry(title='Error. No paths to scan.',prompt='Add paths to scan.',parent=self.ScanDialog,OnlyInfo=True)

        if res:=self.D.SetPathsToScan(PathsToScanFromEntry):
            self.Info('Error. Fix paths selection.',res,self.ScanDialog)
            return

        if res:=self.D.SetExcludeMasks(self.cfg.Get(CFG_KEY_EXCLUDE_REGEXP,False) == 'True',ExcludeVarsFromEntry):
            self.Info('Error. Fix Exclude masks.',res,self.ScanDialog)
            return
        
        self.cfg.Set(CFG_KEY_EXCLUDE,'|'.join(ExcludeVarsFromEntry))
        
        self.main.update()
        if LongActionDialog(self.ScanDialogMainFrame,'scanning files ...',lambda UpdateCallback : self.D.scan(UpdateCallback)).NaturalEnd:
            
            if self.D.sumSize==0:
                self.DialogWithEntry(title='Cannot Proceed.',prompt='No Duplicates.',parent=self.ScanDialog,OnlyInfo=True)
            elif LongActionDialog(self.ScanDialogMainFrame,'crc calculation ...',lambda UpdateCallback : self.D.crcCalc(self.WriteScanToLog.get(),UpdateCallback),'determinate','determinate',Progress1LeftText='Total size:',Progress2LeftText='Files number:').NaturalEnd:

                self.ShowData()
                self.ScanDialogClose()

    def ScanDialogShow(self):
        if self.D.ScannedPaths:
            self.PathsToScanFromDialog=self.D.ScannedPaths.copy()
        
        self.UpdateExcludeMasks()
        self.UpdatePathsToScan()

        self.ScanDialog.grab_set()
        self.main.config(cursor="watch")

        self.SetDefaultGeometryAndShow(self.ScanDialog,self.main)
        
    def ScanDialogClose(self,event=None):
        self.ScanDialog.grab_release()
        self.main.config(cursor="")
        self.GeometryStore(self.ScanDialog)
        
        self.ScanDialog.withdraw()
        try:
            self.ScanDialog.update()
        except Exception as e:
            pass

    def UpdatePathsToScan(self) :
        for subframe in self.PathsToScanFrames:
            subframe.destroy()

        self.PathsToScanFrames=[]
        self.PathsToScanEntryVar={}

        row=0
        for path in self.PathsToScanFromDialog:
            (fr:=ttk.Frame(self.pathsFrame)).grid(row=row,column=0,sticky='news',columnspan=3)
            self.PathsToScanFrames.append(fr)

            tk.Label(fr,text=' ' + nums[row] + ' ' , relief='groove',bg=self.bg).pack(side='left',padx=2,pady=1,fill='y')

            self.PathsToScanEntryVar[row]=tk.StringVar(value=path)
            ttk.Entry(fr,textvariable=self.PathsToScanEntryVar[row]).pack(side='left',expand=1,fill='both',pady=1)

            ttk.Button(fr,text='❌',command=lambda pathpar=path: self.RemovePath(pathpar),width=3).pack(side='right',padx=2,pady=1,fill='y')

            row+=1

        if len(self.PathsToScanFromDialog)==self.MAX_PATHS:
            self.AddPathButton.configure(state=DISABLED,text='')
            self.AddDrivesButton.configure(state=DISABLED,text='')
            self.ClearListButton.focus_set()
        else:
            self.AddPathButton.configure(state=NORMAL,text='Add path ...')
            self.AddDrivesButton.configure(state=NORMAL,text='Add drives ...')
    
    def ScanExcludeRegExprCommand(self):
        self.cfg.Set(CFG_KEY_EXCLUDE_REGEXP,str(self.ScanExcludeRegExpr.get()))

    def UpdateExcludeMasks(self) :
        for subframe in self.ExcludeFrames:
            subframe.destroy()

        self.ExcludeFrames=[]
        self.ExcludeEntryVar={}

        ttk.Checkbutton(self.ExcludeFRame,text='Use regular expressions matching',variable=self.ScanExcludeRegExpr,command=lambda : self.ScanExcludeRegExprCommand()).grid(row=0,column=0,sticky='news',columnspan=3)
        
        row=1
        
        for entry in self.cfg.Get(CFG_KEY_EXCLUDE,'').split('|'):
            if entry:
                (fr:=ttk.Frame(self.ExcludeFRame)).grid(row=row,column=0,sticky='news',columnspan=3)
                self.ExcludeFrames.append(fr)

                self.ExcludeEntryVar[row]=tk.StringVar(value=entry)
                ttk.Entry(fr,textvariable=self.ExcludeEntryVar[row]).pack(side='left',expand=1,fill='both',pady=1)

                ttk.Button(fr,text='❌',command=lambda entrypar=entry: self.RemoveExcludeMask(entrypar),width=3).pack(side='right',padx=2,pady=1,fill='y')

                row+=1

    def AddDrives(self):
        for (device,mountpoint,fstype,opts,maxfile,maxpath) in psutil.disk_partitions():
            if fstype != 'squashfs':
                self.addPath(mountpoint)
        
    def AddPathDialog(self):
        if res:=tk.filedialog.askdirectory(title='select Directory',initialdir=self.cwd,parent=self.ScanDialogMainFrame):
            self.addPath(res)

    def AddExckludeMaskDialog(self):
        if (mask := self.DialogWithEntry(title=f'Specify Exclude Expression',prompt='Expression:', initialvalue='',parent=self.ScanDialog)):
            orglist=self.cfg.Get(CFG_KEY_EXCLUDE,'').split('|')
            orglist.append(mask)
            self.cfg.Set(CFG_KEY_EXCLUDE,'|'.join(orglist))
            self.UpdateExcludeMasks()
            
    def RemovePath(self,path) :
        self.PathsToScanFromDialog.remove(path)
        self.UpdatePathsToScan()
    
    def RemoveExcludeMask(self,mask) :
        orglist=self.cfg.Get(CFG_KEY_EXCLUDE,'').split('|')
        orglist.remove(mask)
        if '' in orglist:
            orglist.remove('')
        self.cfg.Set(CFG_KEY_EXCLUDE,'|'.join(orglist))
        self.UpdateExcludeMasks()
        
    def FocusOut(self,event):
        self.ScandirCache={}
        self.StatCache={}

    def License(self):
        self.Info('License',self.license,self.main,textwidth=80,width=600)

    def About(self):
        info=[]
        info.append('==============================================================================')
        info.append('                                                                              ')
        info.append(f'                       DUDE (DUplicates DEtector) v{VERSION}                    ')
        info.append('                              Piotr Jochymek                                  ')
        info.append('                          PJ.soft.dev.x@gmail.com                             ')
        info.append('                                                                              ')
        info.append('==============================================================================')
        info.append('                                                                              ')
        info.append('CACHE DIRECTORY    :  '+CACHE_DIR)
        info.append('LOGS DIRECTORY     :  '+LOG_DIR)
        info.append('SETTINGS DIRECTORY :  '+CONFIG_DIR)
        info.append('MESSAGE_LEVEL      :  '+ (MESSAGE_LEVEL if MESSAGE_LEVEL else 'INFO(Default)') )

        self.Info('About DUDE','\n'.join(info),self.main,textwidth=80,width=600)

    def KeyboardShortcuts(self):
        self.Info('Keyboard Shortcuts',self.keyboardshortcuts,self.main,textwidth=80,width=600)
    
    def setConfVar(self,title,prompt,parent,tkvar,initialvalue,configkey,validation):
        if (res := self.DialogWithEntry(title,prompt, initialvalue=initialvalue,parent=parent)):
            if (validation(res)):
                tkvar.set(res)
                self.cfg.Set(configkey,res)
                self.cfg.Write()
            else:
                self.setConfVar(title,prompt,parent,tkvar,res,configkey,validation)

    def StoreSplitter(self):
        try:
            coords=self.paned.sash_coord(0)
            self.cfg.Set('sash_coord',str(coords[1]))
            self.cfg.Write()
        except Exception as e:
            logging.error(e)

    def setResultslimit(self):
        self.setConfVar("Results Quantity Limit (0 - 10000)","value:",self.ScanDialog,self.ResultsLimitVar,self.ResultsLimitVar.get(),'resultslimit',lambda x : True if str2bytes(x) and int(x)<10001 and int(x)>0 else False)

    def ClearExcludeMasks(self):
        self.cfg.Set(CFG_KEY_EXCLUDE,'')
        self.UpdateExcludeMasks()
        
    def ClearPaths(self):
        self.PathsToScanFromDialog.clear()
        self.UpdatePathsToScan()

    def SettingsDialogShow(self):
        self.preFocus=self.main.focus_get()
        
        self.SetingsDialog.grab_set()
        self.main.config(cursor="watch")

        self.SetDefaultGeometryAndShow(self.SetingsDialog,self.main)
        
        self.SetingsDialogDefault.focus_set()

    def SettingsDialogClose(self,event=None):
        self.SetingsDialog.grab_release()
        if self.preFocus:
            self.preFocus.focus_set()
        else:
            self.main.focus_set()
        
        self.main.config(cursor="")
        self.GeometryStore(self.SetingsDialog)
        
        self.SetingsDialog.withdraw()
        try:
            self.SetingsDialog.update()
        except Exception as e:
            pass

    def SettingsDialogOK(self):
        self.cfg.Set(CFG_KEY_STARTUP_ADD_CWD,str(self.addCwdAtStartup.get()))
        self.cfg.Set(CFG_KEY_STARTUP_SCAN,str(self.scanAtStartup.get()))

        update1=False
        update2=False

        if (self.cfg.Get(CFG_KEY_SHOW_OTHERS,False)!=self.showothers.get()):
            self.cfg.Set(CFG_KEY_SHOW_OTHERS,str(self.showothers.get()))
            update2=True

        if self.cfg.Get(CFG_KEY_FULLCRC,False)!=self.fullCRC.get():
            self.cfg.Set(CFG_KEY_FULLCRC,str(self.fullCRC.get()))
            update1=True
            update2=True

        if self.cfg.Get(CFG_KEY_FULLPATHS,False)!=self.fullPaths.get():
            self.cfg.Set(CFG_KEY_FULLPATHS,str(self.fullPaths.get()))
            update1=True
            update2=True

        if self.cfg.Get(CFG_KEY_REL_SYMLINKS,False)!=self.relSymlinks.get():
            self.cfg.Set(CFG_KEY_REL_SYMLINKS,str(self.relSymlinks.get()))

        if self.cfg.Get(CFG_KEY_USE_REG_EXPR,False)!=self.useRegExpr.get():
            self.cfg.Set(CFG_KEY_USE_REG_EXPR,str(self.useRegExpr.get()))

        self.cfg.Write()

        if update1:
            self.Tree1CrcAndPathUpdate()
        if update2:
            item=self.tree1.focus()

            if item and item!='' and self.tree1.set(item,'kind')==FILE:
                self.UpdatePathTree(item)
            else:
                self.UpdatePathTreeNone()
        self.SettingsDialogClose()


    def SettingsDialogReset(self):
        self.addCwdAtStartup.set(True)
        self.scanAtStartup.set(True)
        self.showothers.set(False)
        self.fullCRC.set(False)
        self.fullPaths.set(False)
        self.relSymlinks.set(False)
        self.useRegExpr.set(False)

    def fileid(self,inode,dev):
        return str(inode)+'-'+str(dev)

    def fileidSimple(self,inode,dev):
        return inode

    def UpdateCrcNode(self,crc):
        size=int(self.tree1.set(crc,'size'))
        logging.debug(f'UpdateCrcNode:{crc},{size}')

        if not size in self.D.filesOfSizeOfCRC:
            self.tree1.delete(crc)
            logging.debug('UpdateCrcNode-1 ' + crc)
        elif crc not in self.D.filesOfSizeOfCRC[size]:
            self.tree1.delete(crc)
            logging.debug('UpdateCrcNode-2 ' + crc)
        else:
            crcDict=self.D.filesOfSizeOfCRC[size][crc]
            for item in list(self.tree1.get_children(crc)):
                IndexTuple=self.GetIndexTupleTree1(item)

                if IndexTuple not in crcDict:
                    self.tree1.delete(item)
                    logging.debug('UpdateCrcNode-3 ' + item)

            if not self.tree1.get_children(crc):
                self.tree1.delete(crc)
                logging.debug('UpdateCrcNode-4 ' + crc)

    def ByPathCacheUpdate(self):
        self.ByPathCache = { (pathnr,path,file):(size,ctime,dev,inode,crc,self.D.crccut[crc]) for size,sizeDict in self.D.filesOfSizeOfCRC.items() for crc,crcDict in sizeDict.items() for pathnr,path,file,ctime,dev,inode in crcDict }

    def tree1ItemsUpdate(self):
        self.tree1Items=[]
        groupsQuant=0
        for crc in self.tree1.get_children():
            self.tree1Items.append(crc)
            groupsQuant+=1
            for item in self.tree1.get_children(crc):
                self.tree1Items.append(item)
        self.StatusVarGroups.set(groupsQuant)

    def InitialFocus(self):
        if self.tree1.get_children():
            firstNodeFile=next(iter(self.tree1.get_children(next(iter(self.tree1.get_children())))))
            self.tree1.focus_set()
            self.tree1.focus(firstNodeFile)
            self.tree1.see(firstNodeFile)
            self.Tree1SelChange(firstNodeFile)

            self.Tree1CrcAndPathUpdate()
        else:
            self.UpdatePathTreeNone()

    def ShowData(self):
        self.idfunc=self.fileid if len(self.D.devs)>1 else self.fileidSimple

        logging.debug('self.D.devs=' + str(self.D.devs) )
        logging.debug('self.idfunc=' + self.idfunc.__name__)

        self.tree1.delete(*self.tree1.get_children())
        
        for size,sizeDict in self.D.filesOfSizeOfCRC.items() :
            for crc,crcDict in sizeDict.items():
                crcitem=self.tree1.insert(parent='', index=END,iid=crc, values=('','','',str(size),bytes2str(size),'','','',crc,len(crcDict),'',CRC),tags=[CRC],open=True)

                for pathnr,path,file,ctime,dev,inode in crcDict:
                    self.tree1.insert(parent=crcitem, index=END,iid=self.idfunc(inode,dev), values=(\
                                                            pathnr,\
                                                            path,\
                                                            file,\
                                                            str(size),\
                                                            '',\
                                                            ctime,\
                                                            dev,\
                                                            inode,\
                                                            crc,\
                                                            '',\
                                                            time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime)) ,FILE),tags=[])
        
        self.ByPathCacheUpdate()
        self.CalcMarkStatsAll()
        self.tree1ItemsUpdate()

        self.InitialFocus();
        
        self.ColumnSort(self.tree1,*self.ColumnSortLastParams[self.tree1])

    def Tree1CrcAndPathUpdate(self):
        fullcrc = self.cfg.Get(CFG_KEY_FULLCRC,False) == 'True'
        fullPaths = self.cfg.Get(CFG_KEY_FULLPATHS,False) == 'True'

        for size,sizeDict in self.D.filesOfSizeOfCRC.items() :
            for crc,crcDict in sizeDict.items():
                self.tree1.item(crc,text=crc if fullcrc else self.D.crccut[crc])
                for pathnr,path,file,ctime,dev,inode in crcDict:
                    self.tree1.item(self.idfunc(inode,dev),text=self.D.ScannedPaths[pathnr] if fullPaths else nums[pathnr])

    def UpdateMainTreeNone(self):
        self.tree1.selection_remove(self.tree1.selection())

    def UpdateMainTree(self,item):
        self.tree1.selection_set(item)
        crc=self.tree1.set(item,'crc')

        self.main.after_idle(lambda : self.tree1.see(item))
        self.tree1.update()

    ScandirCache={}
    StatCache={}

    def RedrawPathTree(self):
        pathnr=self.SelPathnr
        path=self.SelPath
        
        CacheIndex=(pathnr,path)
        pathnr=int(pathnr)
        
        #pathnrstr=self.D.ScannedPaths[pathnr]

        fullpaths = self.cfg.Get(CFG_KEY_FULLPATHS,False) == 'True'

        fullcrc = self.cfg.Get(CFG_KEY_FULLCRC,False) == 'True'
        ShowOthers = self.cfg.Get(CFG_KEY_SHOW_OTHERS,'False') == 'True'

        fullpath=self.SelSearchPath+path

        if CacheIndex not in self.ScandirCache:
            try:
                self.ScandirCache[CacheIndex]=list(os.scandir(fullpath))
            except Exception as e:
                logging.error('ERROR!',e)
                return

        itemsToInsert=[]
        i=0
        for DirEntry in self.ScandirCache[CacheIndex]:
            istr=str(i)
            file=DirEntry.name
            #print('checking key:',(pathnr,path,file) )
            if (pathnr,path,file) in self.ByPathCache:
                size,ctime,dev,inode,crc,crccut = self.ByPathCache[(pathnr,path,file)]

                #print('size,crc',size,crc)
                itemsToInsert.append( tuple([ crc if fullcrc else crccut, \
                                            file\
                                            ,size\
                                            ,ctime\
                                            ,dev\
                                            ,inode\
                                            ,crc\
                                            ,instances:=len(self.D.filesOfSizeOfCRC[size][crc])\
                                            ,instances,FILEID:=self.idfunc(inode,dev),\
                                            self.tree1.item(FILEID)['tags'],\
                                            FILE,\
                                            FILEID,\
                                            bytes2str(size) ]) )

            elif ShowOthers:
                if os.path.islink(DirEntry) :
                    itemsToInsert.append( ( '➝',file,size,0,0,0,'','',1,0,LINK,LINK,istr+'L','' ) )
                    i+=1
                elif DirEntry.is_dir():
                    itemsToInsert.append( ('⛁',file,0,0,0,0,'','',1,0,DIR,DIR,istr+'L','' ) )
                    i+=1
                elif DirEntry.is_file():
                    if (FullFilePath:=os.path.join(fullpath,file)) not in self.StatCache:
                        try:
                            stat = os.stat(FullFilePath)
                        except Exception as e:
                            logging.error('ERROR!',e)
                            continue
                        self.StatCache[FullFilePath] = tuple([ ctime:=round(stat.st_ctime) , dev:=stat.st_dev , inode:=stat.st_ino , size:=stat.st_size , FILEID:=self.idfunc(inode,dev) ])
                    else:
                        ctime,dev,inode,size,FILEID = self.StatCache[FullFilePath]
                    itemsToInsert.append( ( '',file,size,ctime,dev,inode,'','',1,FILEID,SINGLE,SINGLE,istr+'O',bytes2str(size) ) )
                    i+=1
                else:
                    logging.error(file,'what is it ?')

        #colnameSort,colSort,reverseSort,asnumberSort,level2Sort = self.ColumnSortLastParams[self.tree2]
        colSort,reverseSort,asnumberSort = self.ColumnSortLastParams[self.tree2][1:4]

        if colSort=='file':
            sortIndex=1
        elif colSort=='size':
            sortIndex=2
        elif colSort=='ctime':
            sortIndex=4
        elif colSort=='instancesnum':
            sortIndex=9
        else :
            sortIndex=-1

        self.tree2.delete(*self.tree2.get_children())
        for (text,file,size,ctime,dev,inode,crc,instances,instancesnum,FILEID,tags,kind,iid,sizeH) in sorted(itemsToInsert,key=lambda x : float(x[sortIndex]) if asnumberSort else x[sortIndex],reverse=reverseSort):
            self.tree2.insert(parent="", index=END, iid=iid , text=text, values=(pathnr,path,file,size,sizeH,ctime,dev,inode,crc,instances,instancesnum,time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime)) if crc or kind==SINGLE else '',kind),tags=tags)

    def UpdatePathTreeNone(self):
        self.tree2.delete(*self.tree2.get_children())
        self.CalcMarkStatsPath()
        self.StatusVarPathSize.set('')
        self.StatusVarPathQuant.set('')
        self.SelectedSearchPath.set('')
        self.SelectedSearchPathCode.set('')

    def PathTreeUpdateMarks(self):
        for item in self.tree2.get_children():
            if self.tree2.set(item,'kind')==FILE:
                self.tree2.item( item,tags=self.tree1.item(item)['tags'] )

    def UpdatePathTree(self,item):
        #pathnr_par=self.tree1.set(item,'pathnr')
        #path_par=self.tree1.set(item,'path')

        self.RedrawPathTree()

        self.tree2.selection_set(item)
        self.tree2.see(item)
        self.CalcMarkStatsPath()
        self.tree2.update()

    def CalcMarkStatsAll(self):
        self.CalcMarkStatsCore(self.tree1,self.StatusVarAllSize,self.StatusVarAllQuant)

    def CalcMarkStatsPath(self):
        self.CalcMarkStatsCore(self.tree2,self.StatusVarPathSize,self.StatusVarPathQuant)

    def CalcMarkStatsCore(self,tree,varSize,varQuant):
        marked=tree.tag_has(MARK)
        varQuant.set(len(marked))
        varSize.set(bytes2str(sum(int(tree.set(item,'size')) for item in marked)))

    def MarkInSpecifiedCRCGroupByCTime(self, action, crc, reverse,select=False):
        item=sorted([ (item,self.tree1.set(item,'ctime') ) for item in self.tree1.get_children(crc)],key=lambda x : float(x[1]),reverse=reverse)[0][0]
        action(item,self.tree1)
        if select:
            self.tree1.see(item)
            self.tree1.focus(item)
            self.Tree1SelChange(item)
            self.tree1.update()

    @WatchCursor
    def MarkOnAllByCTime(self,orderStr, action):
        reverse=1 if orderStr=='oldest' else 0

        { self.MarkInSpecifiedCRCGroupByCTime(action, crc, reverse) for crc in self.tree1.get_children() }
        self.PathTreeUpdateMarks()
        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    @WatchCursor
    def MarkInCRCGroupByCTime(self,orderStr,action):
        reverse=1 if orderStr=='oldest' else 0
        self.MarkInSpecifiedCRCGroupByCTime(action,self.tree1.set(self.tree1.focus(),'crc'),reverse,True)
        self.PathTreeUpdateMarks()
        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    def MarkInSpecifiedCRCGroup(self,action,crc):
        { action(item,self.tree1) for item in self.tree1.get_children(crc) }

    @WatchCursor
    def MarkInCRCGroup(self,action):
        self.MarkInSpecifiedCRCGroup(action,self.tree1.set(self.tree1.focus(),'crc'))
        self.PathTreeUpdateMarks()
        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    @WatchCursor
    def MarkOnAll(self,action):
        { self.MarkInSpecifiedCRCGroup(action,crc) for crc in self.tree1.get_children() }
        self.PathTreeUpdateMarks()

        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    @WatchCursor
    def MarkLowerPane(self,action):
        { (action(item,self.tree2),action(item,self.tree1)) for item in self.tree2.get_children() if self.tree2.set(item,'kind')==FILE }

        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    def MarkPathOfFile(self,action):
        if self.SelSearchPath and self.SelPath:
            self.ActionOnSpecifiedPath(self.SelSearchPath+self.SelPath,action)

    def SetMark(self,item,tree):
        tree.item(item,tags=[MARK])

    def UnsetMark(self,item,tree):
        tree.item(item,tags=[])

    def InvertMark(self,item,tree):
        tree.item(item,tags=[] if tree.item(item)['tags'] else [MARK])

    @WatchCursor
    def ActionOnSpecifiedPath(self,pathParam,action):
        selCount=0
        for crcitem in self.tree1.get_children():
            for item in self.tree1.get_children(crcitem):
                fullpath = self.FullPath1(item)

                if fullpath.startswith(pathParam + os.sep):
                    action(item,self.tree1)
                    selCount+=1

        if selCount==0 :
            self.DialogWithEntry(title='No files found for specified path', prompt=pathParam,parent=self.main,OnlyInfo=True)
        else:
            self.PathTreeUpdateMarks()
            self.CalcMarkStatsAll()
            self.CalcMarkStatsPath()

    regexp={'file':'.','path':'.','both':'.'}
    regexpDesc={'file':'file','path':'subpath','both':'entire file path'}
    
    def MarkExpression(self,field,action,ActionLabel):
        tree=self.main.focus_get()

        if self.regexp[field]:
            initialvalue=self.regexp[field]
        else:
            initialvalue='.*'

        UseRegExpr = True if self.cfg.Get(CFG_KEY_USE_REG_EXPR,False)=='True' else False

        desc=self.regexpDesc[field]
        
        prompt=ActionLabel + (' (regular expression syntax)' if UseRegExpr else ' (symplified syntax)')
        
        if (regexp := self.DialogWithEntry(title=f'Specify Expression for {desc}.',prompt=prompt, initialvalue=initialvalue,parent=self.main)):
            self.regexp[field]=regexp
            selCount=0
            if field=='file':
                for crcitem in self.tree1.get_children():
                    for item in self.tree1.get_children(crcitem):
                        file=self.tree1.set(item,'file')
                        try:
                            if (UseRegExpr and re.search(regexp,file)) or (not UseRegExpr and fnmatch.fnmatch(file,regexp) ):
                                action(item,self.tree1)
                                selCount+=1
                        except Exception as e:
                            self.DialogWithEntry(title='Expression Error !',prompt='                                                                \n' + str(e),parent=self.main,OnlyInfo=True)
                            tree.focus_set()
                            return
            elif field=='path':
                for crcitem in self.tree1.get_children():
                    for item in self.tree1.get_children(crcitem):
                        path=self.tree1.set(item,'path')
                        try:
                            if (UseRegExpr and re.search(regexp,path)) or (not UseRegExpr and fnmatch.fnmatch(path,regexp) ):
                                action(item,self.tree1)
                                selCount+=1
                        except Exception as e:
                            self.DialogWithEntry(title='Expression Error !',prompt='                                                                \n' + str(e),parent=self.main,OnlyInfo=True)
                            tree.focus_set()
                            return
            else:
                for crcitem in self.tree1.get_children():
                    for item in self.tree1.get_children(crcitem):
                        fullpath = self.FullPath1(item)
                        try:
                            if (UseRegExpr and re.search(regexp,fullpath)) or (not UseRegExpr and fnmatch.fnmatch(fullpath,regexp) ):
                                action(item,self.tree1)
                                selCount+=1
                        except Exception as e:
                            self.DialogWithEntry(title='Expression Error !',prompt='                                                                \n' + str(e),parent=self.main,OnlyInfo=True)
                            tree.focus_set()
                            return


            if selCount==0 :
                self.DialogWithEntry(title='No files found.',prompt='                                                     \n'+regexp,parent=self.main,OnlyInfo=True)
            else:
                self.PathTreeUpdateMarks()
                self.CalcMarkStatsAll()
                self.CalcMarkStatsPath()

        tree.focus_set()

    def MarkSubpath(self,action):
        if path:=tk.filedialog.askdirectory(title='Select Directory',initialdir=self.cwd):
            self.ActionOnSpecifiedPath(path,action)

    def GotoNextMark(self,tree,direction):
        marked=tree.tag_has(MARK)
        if marked:
            item=tree.focus()
            if not item:
                item=tree.selection()

            pool=marked if tree.tag_has(MARK,item) else self.tree1Items if tree==self.tree1 else tree.get_children()
            poollen=len(pool)

            index = pool.index(item)

            while True:
                index=(index+direction)%poollen
                NextItem=pool[index]
                if MARK in tree.item(NextItem)['tags']:
                    tree.see(NextItem)
                    tree.focus(NextItem)

                    if tree==self.tree1:
                        self.Tree1SelChange(NextItem)
                    else:
                        self.Tree2SelChange(NextItem)
                    break

    def GoToMaxGroup(self,sizeFlag=0):
        biggestsizesum=0
        biggestcrc=None
        for crcitem in self.tree1.get_children():
            sizesum=sum([(int(self.tree1.set(item,'size')) if sizeFlag else 1) for item in self.tree1.get_children(crcitem)])
            if sizesum>biggestsizesum:
                biggestsizesum=sizesum
                biggestcrc=crcitem

        if biggestcrc:
            self.tree1.focus_set()
            self.tree1.focus(biggestcrc)
            self.tree1.see(biggestcrc)

            self.UpdatePathTreeNone()

    def GoToMaxFolder(self,sizeFlag=0):
        PathStat={}

        Biggest={}
        FileidOfBiggest={}

        for size,sizeDict in self.D.filesOfSizeOfCRC.items() :
            for crc,crcDict in sizeDict.items():
                for pathnr,path,file,ctime,dev,inode in crcDict:
                    pathindex=(pathnr,path)
                    PathStat[pathindex] = PathStat.get(pathindex,0) + (size if sizeFlag else 1)
                    if size>Biggest.get(path,0):
                        Biggest[path]=size
                        FileidOfBiggest[path]=self.idfunc(inode,dev)

        if PathStat:
            PathStatList=[(path,number) for (pathnr,path),number in PathStat.items()]
            PathStatList.sort(key=lambda x : x[1],reverse=True)

            [path,num] = PathStatList[0]

            FILEID=FileidOfBiggest[path]

            self.UpdatePathTree(FILEID)

            self.tree2.focus_set()
            self.tree2.focus(FILEID)
            self.tree2.see(FILEID)

            self.UpdateMainTree(FILEID)

    def FullPath1(self,item):
        return self.FullPath(item,self.tree1)

    def FullPath2(self,item):
        return self.FullPath(item,self.tree2)

    def FullPath(self,item,tree):
        pathnr=int(tree.set(item,'pathnr'))
        path=tree.set(item,'path')
        file=tree.set(item,'file')
        return os.path.abspath(self.D.ScannedPathFull(pathnr,path,file))

    def CheckFileState(self,item):
        fullpath = self.FullPath1(item)
        logging.info(f'checking file:{fullpath}')
        try:
            stat = os.stat(fullpath)
            ctimeCheck=str(round(stat.st_ctime))
        except Exception as e:
            mesage = f'cant check file: {fullpath}:{e}'
            logging.error(mesage)
            return mesage

        if ctimeCheck != (ctime:=self.tree1.set(item,'ctime')) :
            message = {f'ctime inconsistency {ctimeCheck} vs {ctime}'}
            #self.Info('ABORTING! Inconsistency of Remaining File \'Change Time\' ','crc:' + crc + '\n' + str(fullpath) + '\n' + str(ctimeCheck) + ' vs ' + str(ctime) + '\n\nFile was modified !',self.main)
            return message

    def ProcessFiles(self,action,all=0):
        logging.info(f'ProcessFiles:{action},{all}')

        tree=self.main.focus_get()
        if not tree:
            return

        ProcessedItems={}
        ShowFullPath=1

        if all:
            ScopeTitle='All Marked Files.'
            for crc in self.tree1.get_children():
                if tempList:=[item for item in self.tree1.get_children(crc) if self.tree1.tag_has(MARK,item)]:
                    ProcessedItems[crc]=tempList
        else:
            item=tree.focus()
            if not item:
                return

            if tree==self.tree1:
                #tylko na gornym drzewie, na dolnym moze byc inny plik
                crc=tree.set(item,'crc')
                if not crc:
                    return
                ScopeTitle='Single CRC group.'
                if tempList:=[item for item in tree.get_children(crc) if tree.tag_has(MARK,item)]:
                    ProcessedItems[crc]=tempList
            else:
                #jezeli dzialamy na katalogu pozostale markniecia w crc nie sa uwzglednione
                #ale w katalogu moze byc >1 tego samego crc
                ScopeTitle='Selected Directory:\n' + self.FullPath2(item)
                #ShowFullPath=0
                for item in tree.get_children():
                    if tree.tag_has(MARK,item):
                        crc=tree.set(item,'crc')
                        if crc not in ProcessedItems:
                            ProcessedItems[crc]=[]
                        ProcessedItems[crc].append(item)

        if not ProcessedItems:
            self.DialogWithEntry(title='No Files Marked For Processing !',prompt='            Mark files first.            ',parent=self.main,OnlyInfo=True)
            return

        logging.info('Scope ' + ScopeTitle)

        #############################################
        #check remainings
        ToKeep={}

        for crc in ProcessedItems:
            ToKeep[crc]=set(self.tree1.get_children(crc))-set(ProcessedItems[crc])

        if action=="hardlink":
            for crc in ProcessedItems:
                if len(ProcessedItems[crc])==1:
                    self.DialogWithEntry(title='Error - Cant hardlink single file.',prompt="                    Mark more files.                    ",parent=self.main,OnlyInfo=True)

                    self.tree1.see(crc)
                    self.tree1.focus(crc)
                    self.Tree1SelChange(crc)
                    self.tree1.update()
                    return

        elif action in ("delete","softlink"):
            for crc in ProcessedItems:
                if len(ToKeep[crc])==0:
                    self.DialogWithEntry(title=f'        Error {action} - All files marked        ',prompt="  Keep at least one file unmarked.  ",parent=self.main,OnlyInfo=True)

                    self.tree1.see(crc)
                    self.tree1.focus(crc)
                    self.Tree1SelChange(crc)
                    self.tree1.update()
                    return

        logging.warning('###########################################################################################')
        logging.warning(f'action:{action}')

        message=[]
        for crc in ProcessedItems:
            message.append('')
            message.append('CRC:' + crc)
            message.append('  marked:')
            for item in ProcessedItems[crc]:
                message.append('    ' + (self.FullPath1(item) if ShowFullPath else tree.set(item,'file')) )

            if ToKeep[crc]:
                message.append('')
                message.append('  remaining:')
                for item in ToKeep[crc]:
                    message.append('    ' + (self.FullPath1(item) if ShowFullPath else self.tree1.set(item,'file')) )

        if action=='delete':
            if not self.Ask('Delete marked files ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return
        elif action=='softlink':
            if not self.Ask('Soft-Link marked files ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return
        elif action=='hardlink':
            if not self.Ask('Hard-Link marked files ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return

        {logging.warning(line) for line in message}
        logging.warning('###########################################################################################')
        logging.warning('Confirmed.')

        #############################################
        for crc in ProcessedItems:
            for item in ToKeep[crc]:
                if res:=self.CheckFileState(item):
                    self.Info(res)
                    logging.error('aborting.')
                    return
        logging.info('remaining files checking complete.')
        #############################################
        if action=='hardlink':
            for crc in ProcessedItems:
                if len({int(self.tree1.set(item,'dev')) for item in ProcessedItems[crc]})>1:
                    message1='Can\'t create hardlinks.'
                    message2=f"Files on multiple devices selected. Crc:{crc}"
                    logging.error(message1)
                    logging.error(message2)
                    self.DialogWithEntry(title=message1,prompt=message2,parent=self.main,OnlyInfo=True)
                    return

        #####################################
        #action

        if action=='delete':
            for crc in ProcessedItems:
                for item in ProcessedItems[crc]:
                    size=int(self.tree1.set(item,'size'))
                    IndexTuple=self.GetIndexTupleTree1(item)

                    if resmsg:=self.D.DeleteFileWrapper(size,crc,IndexTuple):
                        logging.error(resmsg)
                        self.Info('Error',resmsg,self.main)
                        break
                self.UpdateCrcNode(crc)

        if action=='softlink':
            RelSymlink = True if self.cfg.Get(CFG_KEY_REL_SYMLINKS,False)=='True' else False
            for crc in ProcessedItems:

                #toKeepItem=list(ToKeep[crc])[0]
                toKeepItem.tree1.focus()
                IndexTupleRef=self.GetIndexTupleTree1(toKeepItem)
                size=int(self.tree1.set(toKeepItem,'size'))

                if resmsg:=self.D.LinkWrapper(True, RelSymlink, size,crc, IndexTupleRef, [self.GetIndexTupleTree1(item) for item in ProcessedItems[crc] ] ):
                    logging.error(resmsg)
                    self.Info('Error',resmsg,self.main)

                self.UpdateCrcNode(crc)

        if action=='hardlink':
            for crc in ProcessedItems:

                refItem=ProcessedItems[crc][0]
                IndexTupleRef=self.GetIndexTupleTree1(refItem)
                size=int(self.tree1.set(refItem,'size'))

                if resmsg:=self.D.LinkWrapper(False, False, size,crc, IndexTupleRef, [self.GetIndexTupleTree1(item) for item in ProcessedItems[crc][1:] ] ):
                    logging.error(resmsg)
                    self.Info('Error',resmsg,self.main)

                self.UpdateCrcNode(crc)

        self.ScandirCache={}
        self.StatCache={}

        self.ByPathCacheUpdate()
        self.CalcMarkStatsAll()
        self.tree1ItemsUpdate()
        self.InitialFocus()
        #selekcja!

    def CleanCache(self):
        try:
            shutil.rmtree(CACHE_DIR)
        except Exception as e:
            logging.error(e)

    def ClipCopyPath(self):
        if tree:=self.main.focus_get():
            if item:=tree.focus():
                if path := tree.set(item,'path'):
                    pathnr=int(tree.set(item,'pathnr'))
                    pyperclip.copy(self.D.ScannedPaths[pathnr]+path)
                else:
                    crc=tree.set(item,'crc')
                    pyperclip.copy(crc)

    def ClipCopyFile(self):
        if tree:=self.main.focus_get():
            if item:=tree.focus():
                if file:=tree.set(item,'file'):
                    pyperclip.copy(file)
                else:
                    crc=tree.set(item,'crc')
                    pyperclip.copy(crc)

    def OpenFolder(self):
        if tree:=self.main.focus_get():
            if item:=tree.focus():
                pathnr=int(tree.set(item,'pathnr'))
                #pathnrstr=self.D.ScannedPaths[pathnr]
                path = tree.set(item,'path')
                os.system("xdg-open " + '"' + self.SelSearchPath + path + '"')

    def TreeEventOpenFile(self,event=None):
        if event :
            tree=event.widget
            item=tree.identify('item',event.x,event.y)

            if tree.identify("region", event.x, event.y) == 'heading':
                return
        else:

            if tree:=self.main.focus_get():
                item = tree.focus()
            else:
                return

        if item:
            kind=tree.set(item,'kind')

            if kind!=CRC:
                pathnr=int(tree.set(item,'pathnr'))
                #pathnrstr=self.D.ScannedPaths[pathnr]
                path=tree.set(item,'path')
                file=tree.set(item,'file')

                if kind==FILE or kind==LINK or kind==SINGLE:
                    os.system("xdg-open "+ '"' + os.sep.join([self.SelSearchPath+path,file]) + '"')
                    #os.startfile()
                elif kind==DIR:
                    os.system("xdg-open " + '"' + self.SelSearchPath + path + '"')

    def SetCommonVar(self,val=None):
        self.StatusVarFullPath.set(os.sep.join([self.SelSearchPath+self.SelPath,self.SelFile]))
        
    def Tree1SelChange(self,item,force=False):
        pathnr=self.tree1.set(item,'pathnr')
        path=self.tree1.set(item,'path')
        
        self.SelFile = self.tree1.set(item,'file')
        self.SelCrc = self.tree1.set(item,'crc')

        if path!=self.SelPath or pathnr!=self.SelPathnr or force:
            self.SelPathnr = pathnr
            
            if pathnr: #non crc node
                pathnrInt= int(pathnr) 
                self.SelSearchPath = self.D.ScannedPaths[pathnrInt]
                self.SelectedSearchPathCode.set(nums[pathnrInt])
                self.SelectedSearchPath.set(self.SelSearchPath)
                self.SelPath = path
            else :
                pathnrInt= None
                self.SelSearchPath = None
                self.SelectedSearchPathCode.set(None)
                self.SelectedSearchPath.set(None)
                self.SelPath = None
        
            UpdateTree2=True
        else:
            UpdateTree2=False
            
        if self.tree1.set(item,'kind')==FILE:
            self.SetCommonVar()
            if UpdateTree2 :
                self.UpdatePathTree(item)
        else:
            self.StatusVarFullPath.set("")
            if UpdateTree2 :
                self.UpdatePathTreeNone()
            

    def Tree2SelChange(self,item):
        self.SelCrc = self.tree2.set(item,'crc')
        self.SelFile = self.tree2.set(item,'file')
        self.SetCommonVar()
        
        if self.tree2.set(item,'kind')==FILE:
            self.UpdateMainTree(item)
        else:
            self.UpdateMainTreeNone()

    def Tree1KeyRelease(self,event):
        item=self.tree1.focus()

        if event.keysym in ("Up","Down"):
            self.tree1.see(item)
            self.Tree1SelChange(item)
        elif event.keysym in ("Prior","Next"):
            itemsPool=self.tree1.get_children()
            itemsPoolLen=len(itemsPool)
            selcrc=self.tree1.set(item,'crc')
            selindex=itemsPool.index(selcrc)
            NextItem=itemsPool[(selindex+(1 if event.keysym=="Next" else -1)) % itemsPoolLen]
            self.tree1.focus(NextItem)
            self.main.after_idle(lambda : self.tree1.see(NextItem))
            self.Tree1SelChange(NextItem)
            self.tree1.update()
        elif event.keysym in ("Home","End"):
            itemNew=self.tree1.get_children()[0 if event.keysym=="Home" else -1]
            if itemNew:
                self.main.after_idle(lambda : self.tree1.see(itemNew))
                self.tree1.focus(itemNew)
                self.Tree1SelChange(itemNew)
                self.tree1.update()
        elif event.keysym == "space":
            if self.tree1.set(item,'kind')==CRC:
                self.ToggleSelectedTag(self.tree1,*self.tree1.get_children(item))
            else:
                self.ToggleSelectedTag(self.tree1,item)

    def Tree2KeyRelease(self,event):
        item=self.tree2.focus()

        if event.keysym in ("Up",'Down') :
            self.tree2.see(item)
            self.Tree2SelChange(item)
        elif event.keysym in ('Prior','Next'):
            itemsPool=self.tree2.get_children()
            itemsPoolLen=len(itemsPool)
            selindex=itemsPool.index(item)

            NextItem=itemsPool[(selindex+(5 if event.keysym=='Next' else -5)) % itemsPoolLen]

            self.tree2.see(NextItem)
            self.tree2.focus(NextItem)
            self.Tree2SelChange(NextItem)
            self.tree2.update()
        elif event.keysym in ("Home","End"):
            if itemNew:=self.tree2.get_children()[0 if event.keysym=='Home' else -1]:
                self.tree2.see(itemNew)
                self.tree2.focus(itemNew)
                self.Tree2SelChange(itemNew)
                self.tree2.update()
        elif event.keysym == "space":
            self.ToggleSelectedTag(self.tree2,self.tree2.focus())

LoggingLevels={'DEBUG':logging.DEBUG,'INFO':logging.INFO,'WARNING':logging.WARNING,'ERROR':logging.ERROR,'CRITICAL':logging.CRITICAL}

if __name__ == "__main__":
    pathlib.Path(LOG_DIR).mkdir(parents=True,exist_ok=True)
    log=LOG_DIR + os.sep + time.strftime('%Y_%m_%d_%H_%M_%S',time.localtime(time.time()) ) +'.log'

    MESSAGE_LEVEL = os.environ.get('MESSAGE_LEVEL')

    logginLevel = LoggingLevels[MESSAGE_LEVEL] if MESSAGE_LEVEL in LoggingLevels else logging.INFO

    print('Logging started:',log)
    logging.basicConfig(level=logginLevel,format='%(asctime)s %(levelname)s %(message)s', filename=log,filemode='w')

    try:
        Gui(os.getcwd())
    except Exception as e:
        print(e)
        logging.error(e)
        