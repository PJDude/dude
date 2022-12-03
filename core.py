from collections import defaultdict

import subprocess
from subprocess import Popen, PIPE

import os

import logging
from threading import Thread

import time

import pathlib

#import configparser

from appdirs import *

CACHE_DIR = os.sep.join([user_cache_dir('dude'),"cache"])

class CORE:
    filesOfSize=defaultdict(set)
    filesOfSizeOfCRC=defaultdict(lambda : defaultdict(set))
    cache={}
    sumSize=0
    devs=set()
    info=''

    windows=False

    def INIT(self):
        self.filesOfSize=defaultdict(set)
        self.filesOfSizeOfCRC=defaultdict(lambda : defaultdict(set))
        self.devs.clear()
        self.limit=0
        self.CrcCutLen=128
        self.crccut={}
        self.ScannedPaths=[]
        self.ExcludeRegExp=False
        self.ExcludeList=[]

        self.windows = (os.name=='nt')

    def __init__(self):
        self.CRCExec='certutil' if self.windows else 'sha1sum'
        self.CRCExecParams='-hashfile' if self.windows else '-b'

        self.GetCrc=(lambda string : string.split('\n')[1]) if self.windows else (lambda string : string[:40])

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

        if self.windows:
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

    AbortAction=False
    def Abort(self):
        self.AbortAction=True

    InfoPathNr=0
    InfoPathToScan=''
    InfoCounter=0
    InfoSizeSum=0

    def Scan(self):
        logging.info('')
        logging.info('SCANNING')

        if self.ExcludeList:
            logging.info('ExcludeList:' + ' '.join(self.ExcludeList))

        self.InfoPathNr=0
        self.InfoPathToScan=''

        self.AbortAction=False

        pathNr=0
        self.InfoCounter=0
        self.InfoSizeSum=0

        for PathToScan in self.Paths2Scan:
            loopList=[PathToScan]

            while loopList:
                try:
                    path = loopList.pop(0)
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
                                            self.InfoSizeSum+=stat.st_size

                                            subpath=path.replace(PathToScan,'')
                                            self.filesOfSize[stat.st_size].add( (pathNr,subpath,file,round(stat.st_mtime),round(stat.st_ctime),stat.st_dev,stat.st_ino) )

                                self.InfoCounter+=1

                                self.InfoPathNr=pathNr
                                self.InfoPathToScan=PathToScan

                                if self.AbortAction:
                                    break

                        except Exception as e:
                            logging.error(e)
                except Exception as e:
                    logging.error(e)

                if self.AbortAction:
                    break

            pathNr+=1
            if self.AbortAction:
                break

        if self.AbortAction:
            return False

        self.devs={dev for size,data in self.filesOfSize.items() for pathnr,path,file,mtime,ctime,dev,inode in data}

        ######################################################################
        #inodes collision detection
        knownDevInodes=defaultdict(int)
        for size,data in self.filesOfSize.items():
            for pathnr,path,file,mtime,ctime,dev,inode in data:
                index=(dev,inode)
                knownDevInodes[index]+=1

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
        return True

    def CheckCRC(self):
        stream=subprocess.Popen([self.CRCExec,self.CRCExecParams,os.path.join(os.path.dirname(__file__),'LICENSE')], stdout=PIPE, stderr=PIPE,bufsize=1,universal_newlines=True, shell=self.windows)

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

    SubprocessStream=None

    def Run(self,command):
        try:
            self.SubprocessStream=subprocess.Popen(command, stdout=PIPE, stderr=PIPE,bufsize= 1,universal_newlines=True,shell=self.windows )
            stdout, stderr = self.SubprocessStream.communicate()

            if stderr:
                logging.error(f"command:{command}->{stderr}")
                return None
            elif exitCode:=self.SubprocessStream.poll():
                logging.error(f"command:{command}->exitCode:{exitCode}")
                return None

        except Exception as e:
            logging.error(e)
            return None

        return self.GetCrc(stdout)

    def Kill(self):
        try:
            if self.SubprocessStream:
                self.SubprocessStream.kill()
        except Exception as e:
            logging.error(e)

    writeLog=False

    InfoProgSize=0
    InfoProgQuant=0
    InfoSizeDone=0
    InfoFileNr=0
    InfoCurrentSize=0
    total=1
    InfoFoundSum=0

    def CrcCalc(self):
        self.ReadCRCCache()

        self.ScannedPaths=self.Paths2Scan.copy()

        self.InfoSizeDone=0

        self.AbortAction=False

        self.InfoFoundSum=0
        self.InfoFileNr=0

        self.total = len([ 1 for size in self.filesOfSize for pathnr,path,file,mtime,ctime,dev,inode in self.filesOfSize[size] ])

        PathsToRecheckSet=set()

        LimitReached=False
        for size in list(sorted(self.filesOfSize,reverse=True)):
            if self.AbortAction:
                break

            self.InfoCurrentSize=size
            for pathnr,path,file,mtime,ctime,dev,inode in self.filesOfSize[size]:
                if self.AbortAction:
                    break

                if (not LimitReached) or (LimitReached and (pathnr,path) in PathsToRecheckSet):

                    self.InfoFileNr+=1
                    self.InfoSizeDone+=size

                    CacheKey=(int(inode),int(mtime))
                    if CacheKey in self.CRCCache[dev]:
                        crc=self.CRCCache[dev][CacheKey]
                    else:
                        if crc:=self.Run([self.CRCExec,self.CRCExecParams,self.Path2ScanFull(pathnr,path,file)]):
                            self.CRCCache[dev][CacheKey]=crc

                    if crc:
                        self.filesOfSizeOfCRC[size][crc].add( (pathnr,path,file,ctime,dev,inode) )

            if size in self.filesOfSizeOfCRC:
                self.CheckCrcPoolAndPrune(size)

            if size in self.filesOfSizeOfCRC:
                if self.limit:
                    self.InfoFoundSum+=len(self.filesOfSizeOfCRC[size])
                    if self.InfoFoundSum>=self.limit:
                        LimitReached=True

                if not LimitReached:
                    for crc in self.filesOfSizeOfCRC[size]:
                         for (pathnr,path,file,ctime,dev,inode) in self.filesOfSizeOfCRC[size][crc]:
                            PathsToRecheckSet.add((pathnr,path))

        if not self.AbortAction:
            self.filesOfSize.clear()
            self.CalcCrcMinLen()

        self.WriteCRCCache()

        if self.writeLog:
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
