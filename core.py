#!/usr/bin/python3.11

from collections import defaultdict

import subprocess
from subprocess import Popen, PIPE

import os
import pathlib
import fnmatch
import re

import time
import io, hashlib, hmac

class DudeCore:
    ScanResultsBySize=defaultdict(set)
    filesOfSizeOfCRC=defaultdict(lambda : defaultdict(set))
    cache={}
    sumSize=0
    devs=set()
    info=''
    windows=False

    def INIT(self):
        self.ScanResultsBySize=defaultdict(set)
        self.filesOfSizeOfCRC=defaultdict(lambda : defaultdict(set))
        self.devs.clear()
        self.CrcCutLen=128
        self.crccut={}
        self.ScannedPaths=[]
        self.ExcludeRegExp=False
        self.ExcludeList=[]

    def __init__(self,CacheDir,Log):
        self.CacheDir=CacheDir
        self.Log=Log
        self.windows = (os.name=='nt')
        self.CRCExec='certutil' if self.windows else 'sha1sum'
        self.CRCExecParams='-hashfile' if self.windows else '-b'
        self.GetCrc=(lambda string : string.split('\n')[1]) if self.windows else (lambda string : string[:40])

        self.CheckCRC()

        self.INIT()

    def Path2ScanFull(self,pathnr,path,file):
        return os.path.join(self.Paths2Scan[pathnr]+path,file)

    def ScannedPathFull(self,pathnr,path,file):
        return os.path.join(self.ScannedPaths[pathnr]+path,file)

    def SetPathsToScan(self,paths):
        pathsLen=len(paths)

        if self.windows:
            paths=[path + ('\\' if path[-1]==':' else '') for path in paths ]
            paths=[path.replace('/','\\').upper() for path in paths]

        abspaths=[os.path.abspath(path) for path in paths]

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
        self.Log.info('')
        self.Log.info('SCANNING')

        if self.ExcludeList:
            self.Log.info('ExcludeList:' + ' '.join(self.ExcludeList))

        self.InfoPathNr=0
        self.InfoPathToScan=''

        self.AbortAction=False

        pathNr=0
        self.InfoCounter=0
        self.InfoSizeSum=0

        self.ScanResultsBySize.clear()

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
                                self.Log.info(f'skipping by Exclude Mask:{fullpath}')
                                continue
                        try:
                            if os.path.islink(entry) :
                                self.Log.debug(f'skippping link: {path} / {file}')
                            elif entry.is_dir():
                                loopList.append(os.path.join(path,file))
                            elif entry.is_file():
                                try:
                                    stat = os.stat(fullpath)
                                except Exception as e:
                                    self.Log.error(f'scan skipp {e}')
                                else:
                                    if stat.st_nlink!=1:
                                        self.Log.debug(f'scan skipp - hardlinks {stat.st_nlink} - {pathNr},{path},{file}')
                                    else:
                                        if stat.st_size>0:
                                            self.InfoSizeSum+=stat.st_size

                                            subpath=path.replace(PathToScan,'')
                                            self.ScanResultsBySize[stat.st_size].add( (pathNr,subpath,file,round(stat.st_mtime),round(stat.st_ctime),stat.st_dev,stat.st_ino) )

                                self.InfoCounter+=1

                                self.InfoPathNr=pathNr
                                self.InfoPathToScan=PathToScan

                                if self.AbortAction:
                                    break

                        except Exception as e:
                            self.Log.error(e)
                except Exception as e:
                    self.Log.error(f"scanning:'{PathToScan}' - '{e}'")

                if self.AbortAction:
                    break

            pathNr+=1
            if self.AbortAction:
                break

        if self.AbortAction:
            return False

        self.devs={dev for size,data in self.ScanResultsBySize.items() for pathnr,path,file,mtime,ctime,dev,inode in data}

        ######################################################################
        #inodes collision detection
        knownDevInodes=defaultdict(int)
        for size,data in self.ScanResultsBySize.items():
            for pathnr,path,file,mtime,ctime,dev,inode in data:
                index=(dev,inode)
                knownDevInodes[index]+=1

        self.blacklistedInodes = {index for index in knownDevInodes if knownDevInodes[index]>1}

        for size in list(self.ScanResultsBySize):
            for pathnr,path,file,mtime,ctime,dev,inode in list(self.ScanResultsBySize[size]):
                index=(dev,inode)
                if index in self.blacklistedInodes:
                    thisIndex=(pathnr,path,file,mtime,ctime,dev,inode)
                    self.Log.warning('ignoring conflicting inode entry:' + str(thisIndex))
                    self.ScanResultsBySize[size].remove(thisIndex)

        ######################################################################
        self.sumSize=0
        for size in list(self.ScanResultsBySize):
            quant=len(self.ScanResultsBySize[size])
            if quant==1 :
                del self.ScanResultsBySize[size]
            else:
                self.sumSize += quant*size
        ######################################################################
        return True

    def CheckCRC(self):
        stream=subprocess.Popen([self.CRCExec,self.CRCExecParams,os.path.join(os.path.dirname(__file__),'LICENSE')], stdout=PIPE, stderr=PIPE,bufsize=1,universal_newlines=True, shell=self.windows)

        stdout, stderr = stream.communicate()
        res=stdout
        if stderr:
            self.Log.error(f"Cannot execute {self.CRCExec}")
            self.Log.error(stderr)
            self.Log.error('exiting ')
            exit(10)
        elif exitCode:=stream.poll():
            self.Log.error(f'exit code:{exitCode}')
            exit(11)
        else:
            self.Log.debug(f"all fine. stdout:{stdout} crc:{self.GetCrc(stdout)}")

    def ReadCRCCache(self):
        self.CRCCache={}
        for dev in self.devs:
            self.CRCCache[dev]=dict()
            try:
                self.Log.debug(f'reading cache:{self.CacheDir}:device:{dev}')
                with open(os.sep.join([self.CacheDir,str(dev)]),'r' ) as cfile:
                    while line:=cfile.readline() :
                        inode,mtime,crc = line.rstrip('\n').split(' ')
                        if crc==None or crc=='None' or crc=='':
                            self.Log.warning(f"CRCCache read error:{inode},{mtime},{crc}")
                        else:
                            self.CRCCache[dev][(int(inode),int(mtime))]=crc

            except Exception as e:
                self.Log.warning(e)
                self.CRCCache[dev]=dict()

    def WriteCRCCache(self):
        pathlib.Path(self.CacheDir).mkdir(parents=True,exist_ok=True)
        for dev in self.CRCCache:
            self.Log.debug(f'writing cache:{self.CacheDir}:device:{dev}')
            with open(os.sep.join([self.CacheDir,str(dev)]),'w' ) as cfile:
                for (inode,mtime),crc in self.CRCCache[dev].items():
                    cfile.write(' '.join([str(x) for x in [inode,mtime,crc] ]) +'\n' )
        del self.CRCCache

    SubprocessStream=None

    def Run(self,command):
        try:
            self.SubprocessStream=subprocess.Popen(command, stdout=PIPE, stderr=PIPE,bufsize= 1,universal_newlines=True,shell=self.windows )
            stdout, stderr = self.SubprocessStream.communicate()

            if stderr:
                self.Log.error(f"command:{command}->{stderr}")
                return None
            elif exitCode:=self.SubprocessStream.poll():
                self.Log.error(f"command:{command}->exitCode:{exitCode}")
                return None

        except Exception as e:
            self.Log.error(e)
            return None

        return self.GetCrc(stdout)

    def Kill(self):
        try:
            if self.SubprocessStream:
                self.SubprocessStream.kill()
        except Exception as e:
            self.Log.error(e)

    writeLog=False

    InfoSizeDone=0
    InfoFileNr=0
    InfoCurrentSize=0
    InfoCurrentFile=''
    InfoTotal=1
    InfoFoundGroups=0
    InfoFoundFolders=0
    InfoDuplicatesSpace=0
    infoSpeed=0

    #SizeThreshold=64*1024*1024
    CacheSizeTheshold=1024

    def CrcCalc(self):
        self.ReadCRCCache()

        self.ScannedPaths=self.Paths2Scan.copy()

        self.InfoSizeDone=0

        self.AbortAction=False

        self.InfoFoundGroups=0
        self.InfoFoundFolders=0
        self.InfoDuplicatesSpace=0
        self.InfoFileNr=0
        self.infoSpeed=0

        self.InfoTotal = len([ 1 for size in self.ScanResultsBySize for pathnr,path,file,mtime,ctime,dev,inode in self.ScanResultsBySize[size] ])

        MeasuresPool=[]
        MeasuresPoolLen=64

        start = time.time()

        for size in list(sorted(self.ScanResultsBySize,reverse=True)):
            if self.AbortAction:
                break

            self.InfoCurrentSize=size
            UseCache = True if size>self.CacheSizeTheshold else False

            for pathnr,path,file,mtime,ctime,dev,inode in self.ScanResultsBySize[size]:
                self.InfoCurrentFile=file
                if self.AbortAction:
                    break

                self.InfoFileNr+=1
                self.InfoSizeDone+=size

                crc=None

                if UseCache:
                    CacheKey=(int(inode),int(mtime))
                    if CacheKey in self.CRCCache[dev]:
                        crc=self.CRCCache[dev][CacheKey]

                if not crc:
                    FullPath=self.Path2ScanFull(pathnr,path,file)

                    try:
                        with open(FullPath,'rb') as f:
                            crc = hashlib.file_digest(f, "sha1").hexdigest()

                    except Exception as e:
                        self.Log.error(e)
                        crc=None
                    else:
                        if UseCache:
                            self.CRCCache[dev][CacheKey]=crc

                if crc:
                    self.filesOfSizeOfCRC[size][crc].add( (pathnr,path,file,ctime,dev,inode) )

                now=time.time()
                MeasuresPool.append((now,self.InfoSizeDone))

                MeasuresPool=MeasuresPool[-MeasuresPoolLen:]

                LastPeriodTimeDiff = now - MeasuresPool[0][0]
                LastPeriodSizeSum = self.InfoSizeDone - MeasuresPool[0][1]

                if LastPeriodTimeDiff:
                    if LastPeriodTimeDiff<3:
                        MeasuresPoolLen+=1
                    elif LastPeriodTimeDiff>4:
                        MeasuresPoolLen-=1

                    self.infoSpeed=int(LastPeriodSizeSum/LastPeriodTimeDiff)

            if size in self.filesOfSizeOfCRC:
                self.CheckCrcPoolAndPrune(size)

            if size in self.filesOfSizeOfCRC:
                self.InfoFoundGroups+=len(self.filesOfSizeOfCRC[size])
                self.InfoDuplicatesSpace += size*sum([1 for crcDict in self.filesOfSizeOfCRC[size].values() for pathnr,path,file,ctime,dev,inode in crcDict])

            self.InfoFoundFolders = len({(pathnr,path) for sizeDict in self.filesOfSizeOfCRC.values() for crcDict in sizeDict.values() for pathnr,path,file,ctime,dev,inode in crcDict})

        end=time.time()
        self.Log.debug(f'total time = (end-start)s')

        self.CalcCrcMinLen()

        self.WriteCRCCache()

        if self.writeLog:
            self.LogScanResults()

    def CheckGroupFilesState(self,size,crc):
        #print('CheckGroupFilesState',size,crc,self.filesOfSizeOfCRC[size][crc])
        resProblems=[]
        toRemove=[]
        if not self.filesOfSizeOfCRC[size][crc]:
            resProblems.append('no data')
            #print('no data')
        else :
            for pathnr,path,file,ctime,dev,inode in self.filesOfSizeOfCRC[size][crc]:
                FullPath=self.Path2ScanFull(pathnr,path,file)
                problem=False
                #print(FullPath)
                try:
                    stat = os.stat(FullPath)
                    #print(stat)
                except Exception as e:
                    resProblems.append(f'{e}|RED')
                    #print(e)
                    problem=True
                else:
                    if stat.st_nlink!=1:
                        resProblems.append(f'file became hardlink:{stat.st_nlink} - {pathNr},{path},{file}')
                        #print('problem1')
                        problem=True
                    else:
                        if  (size,ctime,dev,inode) != (stat.st_size,round(stat.st_ctime),stat.st_dev,stat.st_ino):
                            resProblems.append(f'file changed:{size},{ctime},{dev},{inode} vs {stat.st_size},{round(stat.st_ctime)},{stat.st_dev},{stat.st_ino}')
                            problem=True
                            #print('problem2')
                if problem:
                    #print('removing data',pathnr,path,file,ctime,dev,inode)
                    IndexTuple=(pathnr,path,file,ctime,dev,inode)
                    toRemove.append(IndexTuple)


        return (resProblems,toRemove)

    def LogScanResults(self):
        self.Log.info('#######################################################')
        self.Log.info('scan and crc calculation complete')
        self.Log.info('')
        self.Log.info('scanned paths:')
        for (nr,path) in enumerate(self.Paths2Scan):
            self.Log.info(f'  {nr}  <->  {path}',)

        for size in self.filesOfSizeOfCRC:
            self.Log.info('')
            self.Log.info(f'size:{size}')
            for crc in self.filesOfSizeOfCRC[size]:
                self.Log.info(f'  crc:{crc}')
                for IndexTuple in self.filesOfSizeOfCRC[size][crc]:
                    self.Log.info('    ' + ' '.join( [str(elem) for elem in list(IndexTuple) ]))
        self.Log.info('#######################################################')

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

    def RenameFile(self,src,dest):
        self.Log.info(f'renaming file:{src}->{dest}')
        try:
            os.rename(src,dest)
            return False
        except Exception as e:
            self.Log.error(e)
            return 'Rename error:' + str(e)

    def DeleteFile(self,file):
        self.Log.info(f'deleting file:{file}')
        try:
            os.remove(file)
            return False
        except Exception as e:
            self.Log.error(e)
            return 'Delete error:' + str(e)

    def CreateSoftLink(self,src,dest,relative=True):
        self.Log.info(f'soft-linking {src}<-{dest} (relative:{relative})')
        try:
            if relative:
                destDir = os.path.dirname(dest)
                srcRel = os.path.relpath(src, destDir)
                os.symlink(srcRel,dest)
            else:
                os.symlink(src,dest)
            return False
        except Exception as e:
            self.Log.error(e)
            return 'Error on soft linking:' + str(e)

    def CreateHardLink(self,src,dest):
        self.Log.info(f'hard-linking {src}<-{dest}')
        try:
            os.link(src,dest)
            return False
        except Exception as e:
            self.Log.error(e)
            return 'Error on hard linking:' + str(e)

    def ReduceCrcCut(self,size,crc):
        if size not in self.filesOfSizeOfCRC or crc not in self.filesOfSizeOfCRC[size]:
            del self.crccut[crc]

    def RemoveFromDataPool(self,size,crc,IndexTuplesList):
        for IndexTuple in IndexTuplesList:
            self.Log.debug(f'RemoveFromDataPool:{size},{crc},{IndexTuple}')
            self.filesOfSizeOfCRC[size][crc].remove(IndexTuple)

        self.CheckCrcPoolAndPrune(size)
        self.ReduceCrcCut(size,crc)

    def GetPath(self,IndexTuple):
        (pathnr,path,file,ctime,dev,inode)=IndexTuple
        #FullFilePath=self.ScannedPathFull(pathnr,path,file)
        return self.ScannedPaths[pathnr]+path

    def DeleteFileWrapper(self,size,crc,IndexTuplesList):
        Messages=[]
        IndexTuplesListDone=[]
        for IndexTuple in IndexTuplesList:
            self.Log.debug(f"DeleteFileWrapper:{size},{crc},{IndexTuple}")

            (pathnr,path,file,ctime,dev,inode)=IndexTuple
            FullFilePath=self.ScannedPathFull(pathnr,path,file)

            if IndexTuple in self.filesOfSizeOfCRC[size][crc]:
                if message:=self.DeleteFile(FullFilePath):
                    #self.Info('Error',message,self.main)
                    Messages.append(message)
                else:
                    IndexTuplesListDone.append(IndexTuple)
            else:
                Messages.append('DeleteFileWrapper - Internal Data Inconsistency:' + FullFilePath + ' / ' + str(IndexTuple))

        self.RemoveFromDataPool(size,crc,IndexTuplesListDone)

        return Messages

    def LinkWrapper(self,\
            soft,relative,size,crc,\
            IndexTupleRef,IndexTuplesList):

        self.Log.debug(f'LinkWrapper:{soft},{relative},{size},{crc}:{IndexTupleRef}:{IndexTuplesList}')

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
                                self.Log.error(message)
                                #self.Info('Error',message,self.main)
                            #self.RemoveFromDataPool(size,crc,IndexTuple)
                            self.filesOfSizeOfCRC[size][crc].remove(IndexTuple)
            if not soft:
                #self.RemoveFromDataPool(size,crc,IndexTupleRef)
                self.filesOfSizeOfCRC[size][crc].remove(IndexTupleRef)

            self.CheckCrcPoolAndPrune(size)
            self.ReduceCrcCut(size,crc)

############################################################################################
if __name__ == "__main__":
    import logging
    from threading import Thread
    import test
    import time

    LOG_DIR = "./test/log"
    pathlib.Path(LOG_DIR).mkdir(parents=True,exist_ok=True)

    log=LOG_DIR + os.sep + time.strftime('%Y_%m_%d_%H_%M_%S',time.localtime(time.time()) ) +'.log'

    print('log:',log)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s', filename=log,filemode='w')

    print('dude core test ...')
    core=DudeCore('./test/cache',logging)

    TestDir='test/files'
    if not os.path.exists(TestDir):
        test.generate(TestDir)

    #core.setLimit(100)
    core.SetPathsToScan([TestDir])
    core.SetExcludeMasks(False,[])

    core.writeLog=True

    ScanThread=Thread(target=core.Scan,daemon=True)
    ScanThread.start()

    while ScanThread.is_alive():
        print('Scanning ...', core.InfoCounter,end='\r')
        time.sleep(0.04)

    ScanThread.join()

    ScanThread=Thread(target=core.CrcCalc,daemon=True)
    ScanThread.start()

    while ScanThread.is_alive():
        print(f'CrcCalc...{core.InfoFileNr}/{core.InfoTotal} (size:{core.InfoCurrentSize})                ',end='\r')
        time.sleep(0.04)

    ScanThread.join()

    print('')
    print('Done')

