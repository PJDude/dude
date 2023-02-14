#!/usr/bin/python3.11

from collections import defaultdict
from queue import Queue
from threading import Thread

import os
import pathlib
import fnmatch
import re

import time
import io, hashlib, hmac

k=1024
M=k*1024
G=M*1024
T=G*1024

multDict={'k':k,'K':k,'M':M,'G':G,'T':T}
def bytes2str(num,digits=2):
    kb=num/k

    if kb<k:
        string=str(round(kb,digits))
        if string[0:digits+1]=='0.00'[0:digits+1]:
            return str(num)+'B'
        else:
            return str(round(kb,digits))+'kB'
    elif kb<M:
        return str(round(kb/k,digits))+'MB'
    elif kb<G:
        return str(round(kb/M,digits))+'GB'
    else:
        return str(round(kb/G,digits))+'TB'

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

class DudeCore:
    ScanResultsBySize=defaultdict(set)
    filesOfSizeOfCRC=defaultdict(lambda : defaultdict(set))

    sumSize=0
    devs=[]
    info=''
    windows=False

    def INIT(self):
        self.ScanResultsBySize=defaultdict(set)
        self.filesOfSizeOfCRC=defaultdict(lambda : defaultdict(set))
        self.devs.clear()
        self.CrcCutLen=128
        self.crccut={}
        self.ScannedPaths=[]

        self.ExcludeList=[]

    def __init__(self,CacheDir,Log):
        self.CacheDir=CacheDir
        self.Log=Log
        self.windows = (os.name=='nt')

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
        self.ExclFn = (lambda expr,string : re.search(expr,string)) if RegExp else (lambda expr,string : fnmatch.fnmatch(string,expr))

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
    CanAbort=True

    def Abort(self):
        self.AbortAction=True

    InfoPathNr=0
    InfoPathToScan=''
    InfoCounter=0
    InfoSizeSum=0

    ScanDirCache={}
    def StatScanDir(self,path,pathctime=None):

        if not pathctime:
            try:
                PathStat = os.stat(path)
                pathctime=round(PathStat.st_ctime)
            except Exception as e:
                logging.error(f'ERROR:{e}')
                return (0,tuple([]))


        if path not in self.ScanDirCache or self.ScanDirCache[path][0]!=pathctime:
            try:
                with os.scandir(path) as res:
                    reslist=[]
                    for entry in res:
                        name = entry.name
                        
                        #islink=entry.is_symlink()
                        #faster ?
                        islink=os.path.islink(entry)
                        
                        is_dir=entry.is_dir()
                        is_file=entry.is_file()
                        
                        mtime=None
                        ctime=None
                        dev=None
                        inode=None
                        size=None
                        nlink=None

                        if not islink:
                            try:
                                stat = os.stat(os.path.join(path,name))

                                mtime=round(stat.st_mtime)
                                ctime=round(stat.st_ctime)
                                dev=stat.st_dev
                                inode=stat.st_ino
                                size=stat.st_size
                                nlink=stat.st_nlink

                            except Exception as e:
                                self.Log.error('scandir(stat): DUPA %s islink:%s is_dir:%s' % (str(e),str(islink),str(is_dir) ) )

                        reslist.append( (name,islink,is_dir,is_file,mtime,ctime,dev,inode,size,nlink) )
                        
                    self.ScanDirCache[path] = ( pathctime,tuple(reslist) )

            except Exception as e:
                self.Log.error('scandir: %s' % str(e))
                self.ScanDirCache[path] = (0,tuple([]))

        return self.ScanDirCache[path]

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

        #self.ScanDirCache={}

        for PathToScan in self.Paths2Scan:
            loopList=[(PathToScan,None)]

            while loopList:
                try:
                    path,pathctime = loopList.pop(0)
                    for file,islink,isdir,isfile,mtime,ctime,dev,inode,size,nlink in self.StatScanDir(path,pathctime)[1]:

                        fullpath=os.path.join(path,file)
                        if self.ExcludeList:
                            if any({self.ExclFn(expr,fullpath) for expr in self.ExcludeList}):
                                self.Log.info(f'skipping by Exclude Mask:{fullpath}')
                                continue
                        try:
                            if islink :
                                self.Log.debug(f'skippping link: {path} / {file}')
                            elif isdir:
                                loopList.append((os.path.join(path,file),ctime))
                            elif isfile:

                                if mtime: #stat succeeded
                                    if nlink!=1:
                                        self.Log.debug(f'scan skipp - hardlinks {nlink} - {pathNr},{path},{file}')
                                    else:
                                        if size>0:
                                            self.InfoSizeSum+=size

                                            subpath=path.replace(PathToScan,'')
                                            self.ScanResultsBySize[size].add( (pathNr,subpath,file,mtime,ctime,dev,inode) )

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

        self.devs=list({dev for size,data in self.ScanResultsBySize.items() for pathnr,path,file,mtime,ctime,dev,inode in data})

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

    def ReadCRCCache(self):
        self.Info='Reading cache ...'
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
        self.Info='Writing cache ...'
        pathlib.Path(self.CacheDir).mkdir(parents=True,exist_ok=True)
        for dev in self.CRCCache:
            self.Log.debug(f'writing cache:{self.CacheDir}:device:{dev}')
            with open(os.sep.join([self.CacheDir,str(dev)]),'w' ) as cfile:
                for (inode,mtime),crc in self.CRCCache[dev].items():
                    cfile.write(' '.join([str(x) for x in [inode,mtime,crc] ]) +'\n' )
        del self.CRCCache

    writeLog=False

    InfoSizeDone=0
    InfoFileDone=0
    #InfoAvarageSize=0
    InfoTotal=1
    InfoFoundGroups=0
    InfoFoundFolders=0
    InfoDuplicatesSpace=0
    infoSpeed=0

    CacheSizeTheshold=64
    InfoThreads='?'

    Status=''

    CRCBUfferSize=4*1024*1024

    #############################################################
    def ThreadedCrcCalcOnOpenedFilesQueue(self,TIndex,SrcQ,ResQ):
        #,TotalList,FileInfoList,ProgressList
        buf = bytearray(self.CRCBUfferSize)
        view = memoryview(buf)

        FilesDone=0
        SizeDone=0

        while True:
            Task = SrcQ.get()
            SrcQ.task_done()

            if Task:
                File,IndexTuple,size,mtime = Task
                h = hashlib.sha1()

                self.CrcThreadProgressInfo[TIndex]=0

                self.CrcThreadFileInfo[TIndex]=(size,IndexTuple)
                while rsize := File.readinto(buf):
                    h.update(view[:rsize])
                    self.CrcThreadProgressInfo[TIndex]+=rsize

                    if self.AbortAction:
                        break

                if not self.AbortAction:
                    ResQ.put((File,IndexTuple,size,mtime,h.hexdigest()))
                    FilesDone+=1
                    SizeDone+=size
                    self.CrcThreadTotalInfo[TIndex]=(FilesDone,SizeDone)

                self.CrcThreadProgressInfo[TIndex]=0
                self.CrcThreadFileInfo[TIndex]=None

                File.close()
            else:
                break

        return
    #############################################################

    InfoLine=None
    def CrcCalc(self):
        self.ReadCRCCache()

        self.ScannedPaths=self.Paths2Scan.copy()

        self.InfoSizeDone=0

        self.AbortAction=False
        self.CanAbort=True

        self.InfoFoundGroups=0
        self.InfoFoundFolders=0
        self.InfoDuplicatesSpace=0
        self.InfoFileDone=0
        self.infoSpeed=0

        self.InfoTotal = len([ 1 for size in self.ScanResultsBySize for pathnr,path,file,mtime,ctime,dev,inode in self.ScanResultsBySize[size] ])

        start = time.time()

        ScanResultsSizes = list(self.ScanResultsBySize)
        ScanResultsSizes.sort(reverse=True)

        MaxThreads = os.cpu_count()
        
        FileNamesQueue={}
        OpenedFilesQueue={}
        FilesCrcQueue={}

        TIndexes = self.devs

        self.CrcThreadTotalInfo={}
        self.CrcThreadFileInfo={}
        self.CrcThreadProgressInfo={}

        CRCThread={}
        ThreadStarted={}

        for TIndex in TIndexes:
            FileNamesQueue[TIndex]=Queue()
            OpenedFilesQueue[TIndex]=Queue()
            FilesCrcQueue[TIndex]=Queue()

            self.CrcThreadTotalInfo[TIndex]=(0,0)
            self.CrcThreadFileInfo[TIndex]=None
            self.CrcThreadProgressInfo[TIndex]=0

            ThreadStarted[TIndex]=False

            CRCThread[TIndex] = Thread(target=self.ThreadedCrcCalcOnOpenedFilesQueue,args=(TIndex,OpenedFilesQueue[TIndex],FilesCrcQueue[TIndex],),daemon=True)

        #########################################################################################################
        for size in ScanResultsSizes:
            if self.AbortAction:
                break
            for pathnr,path,file,mtime,ctime,dev,inode in self.ScanResultsBySize[size]:
                if self.AbortAction:
                    break

                IndexTuple=(pathnr,path,file,ctime,dev,inode)
                TIndex = dev

                if size>self.CacheSizeTheshold:
                    CacheKey=(inode,mtime)
                    if CacheKey in self.CRCCache[dev]:
                        if crc:=self.CRCCache[dev][CacheKey]:
                            self.InfoSizeDone+=size
                            self.InfoFileDone+=1

                            self.filesOfSizeOfCRC[size][crc].add( IndexTuple )
                            continue

                FileNamesQueue[TIndex].put((size,pathnr,path,file,mtime,ctime,dev,inode))
        #########################################################################################################

        InfoSizeDoneFromCache=self.InfoSizeDone
        InfoFileDoneFromCache=self.InfoFileDone

        OpenedFilesPerDevLimit=32

        MeasuresPool=[]

        LastTimeStats = 0

        Info=''
        PrevNow=0

        prevLineInfo={}
        prevLineShowSameMax={}

        for TIndex in TIndexes:
            prevLineInfo[TIndex]=''
            prevLineShowSameMax[TIndex]=0

        while True:
            ########################################################################
            # files opening
            AnythingOpened=False
            for TIndex in TIndexes:
                while not self.AbortAction and FileNamesQueue[TIndex].qsize()>0 and OpenedFilesQueue[TIndex].qsize()<OpenedFilesPerDevLimit:
                    NameCombo = FileNamesQueue[TIndex].get()
                    FileNamesQueue[TIndex].task_done()

                    size,pathnr,path,file,mtime,ctime,dev,inode = NameCombo

                    try:
                        File=open(self.Path2ScanFull(pathnr,path,file),'rb')
                    except Exception as e:
                        self.Log.error(e)
                    else:
                        IndexTuple=(pathnr,path,file,ctime,dev,inode)
                        OpenedFilesQueue[TIndex].put((File,IndexTuple,size,mtime))
                        AnythingOpened=True

            ########################################################################
            # CRC data processing
            AnythingProcessed=False
            for TIndex in TIndexes:
                while FilesCrcQueue[TIndex].qsize()>0:
                    Task = FilesCrcQueue[TIndex].get()
                    FilesCrcQueue[TIndex].task_done()

                    File,IndexTuple,size,mtime,crc = Task

                    self.filesOfSizeOfCRC[size][crc].add( IndexTuple )
                    AnythingProcessed=True

                    if size>self.CacheSizeTheshold:
                        dev=IndexTuple[4]
                        inode=IndexTuple[5]
                        CacheKey=(inode,mtime)
                        self.CRCCache[dev][CacheKey]=crc

            ########################################################################
            # threads starting/finishing

            AliveThreads=sum([1 if CRCThread[TIndex].is_alive() else 0 for TIndex in TIndexes])
            AllCrcProcessed=all(FilesCrcQueue[TIndex].qsize()==0 for TIndex in TIndexes)

            NothingStarted=True
            if AliveThreads<MaxThreads:
                for TIndex in TIndexes:
                    if not ThreadStarted[TIndex] and not CRCThread[TIndex].is_alive():
                        CRCThread[TIndex].start()
                        ThreadStarted[TIndex]=True
                        NothingStarted=False
                        break


            for TIndex in TIndexes:
                if self.AbortAction or (FileNamesQueue[TIndex].qsize()==0 and OpenedFilesQueue[TIndex].qsize()==0):
                    if CRCThread[TIndex].is_alive():
                        OpenedFilesQueue[TIndex].put(None)

            if NothingStarted and AliveThreads==0 and AllCrcProcessed:
                break
            elif not AnythingOpened and not AnythingProcessed and NothingStarted:
                self.InfoThreads=str(AliveThreads)
                time.sleep(0.01)

            ########################################################################
            # info/stats
            now=time.time()

            if now-PrevNow>0.02 and not self.AbortAction:
                PrevNow=now

                InfoSizeDoneTemp=InfoSizeDoneFromCache
                InfoFilesDoneTemp=InfoFileDoneFromCache

                for TIndex in TIndexes:
                    FilesDone,SizeDone= self.CrcThreadTotalInfo[TIndex]
                    InfoSizeDoneTemp+=SizeDone
                    InfoSizeDoneTemp+=self.CrcThreadProgressInfo[TIndex]
                    InfoFilesDoneTemp+=FilesDone

                self.InfoFileDone=InfoFilesDoneTemp
                self.InfoSizeDone=InfoSizeDoneTemp

                MeasuresPool=[(PoolTime,FSize,FQuant) for (PoolTime,FSize,FQuant) in MeasuresPool if (now-PoolTime)<3]
                MeasuresPool.append((now,InfoSizeDoneTemp,InfoFilesDoneTemp))

                first=MeasuresPool[0]

                if LastPeriodTimeDiff := now - first[0]:
                    LastPeriodSizeSum  = InfoSizeDoneTemp - first[1]
                    self.infoSpeed=int(LastPeriodSizeSum/LastPeriodTimeDiff)

                ################################################
                #stats
                if now-LastTimeStats>2:
                    LastTimeStats=now

                    TempInfoFoundGroups=0
                    TempInfoFoundFolders=set()
                    TempInfoDuplicatesSpace=0

                    for size,sizeDict in self.filesOfSizeOfCRC.items():
                        for crcDict in sizeDict.values():
                            if len(crcDict)>1:
                                TempInfoFoundGroups+=1
                                for pathnr,path,file,ctime,dev,inode in crcDict:
                                    TempInfoDuplicatesSpace+=size
                                    TempInfoFoundFolders.add((pathnr,path))

                    self.InfoFoundGroups=TempInfoFoundGroups
                    self.InfoFoundFolders=len(TempInfoFoundFolders)
                    self.InfoDuplicatesSpace=TempInfoDuplicatesSpace


                LineInfoList=[]
                for TIndex in TIndexes:
                    #size,pathnr,path,file
                    if self.CrcThreadProgressInfo[TIndex] and self.CrcThreadFileInfo[TIndex]:
                        currLineInfoFileSize=self.CrcThreadFileInfo[TIndex][0]

                        if currLineInfoFileSize==prevLineInfo[TIndex]:
                            if now-prevLineShowSameMax[TIndex]>1:
                                LineInfoList.append( (currLineInfoFileSize,bytes2str(self.CrcThreadProgressInfo[TIndex]) + '/' + bytes2str(currLineInfoFileSize)) )
                        else:
                            prevLineShowSameMax[TIndex]=now
                            prevLineInfo[TIndex]=currLineInfoFileSize

                self.InfoLine = '    '.join([elem[1] for elem in sorted(LineInfoList,key=lambda x : x[0],reverse=True)])
            ########################################################################

        self.CanAbort=False

        for TIndex in TIndexes:
            CRCThread[TIndex].join()

        self.Info='Pruning data ...'
        for size in ScanResultsSizes:
            self.CheckCrcPoolAndPrune(size)

        self.WriteCRCCache()
        self.Crc2Size = {crc:size for size,sizeDict in self.filesOfSizeOfCRC.items() for crc in sizeDict}

        end=time.time()
        self.Log.debug(f'total time = {end-start}s')

        self.CalcCrcMinLen()

        if self.writeLog:
            self.Info='Writing log ...'
            self.LogScanResults()

    def CheckGroupFilesState(self,size,crc):
        resProblems=[]
        toRemove=[]

        if self.filesOfSizeOfCRC[size][crc]:
            for pathnr,path,file,ctime,dev,inode in self.filesOfSizeOfCRC[size][crc]:
                FullPath=self.Path2ScanFull(pathnr,path,file)
                problem=False
                try:
                    stat = os.stat(FullPath)
                except Exception as e:
                    resProblems.append(f'{e}|RED')
                    problem=True
                else:
                    if stat.st_nlink!=1:
                        resProblems.append(f'file became hardlink:{stat.st_nlink} - {pathNr},{path},{file}')
                        problem=True
                    else:
                        if (size,ctime,dev,inode) != (stat.st_size,round(stat.st_ctime),stat.st_dev,stat.st_ino):
                            resProblems.append(f'file changed:{size},{ctime},{dev},{inode} vs {stat.st_size},{round(stat.st_ctime)},{stat.st_dev},{stat.st_ino}')
                            problem=True
                if problem:
                    IndexTuple=(pathnr,path,file,ctime,dev,inode)
                    toRemove.append(IndexTuple)
        else :
            resProblems.append('no data')

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
        self.Info='CRC min length calculation ...'
        allCrcLen=len(AllCrcs:={crc for size,sizeDict in self.filesOfSizeOfCRC.items() for crc in sizeDict})

        lenTemp=1
        while len({crc[0:lenTemp] for crc in AllCrcs})!=allCrcLen:
            lenTemp+=1

        self.CrcCutLen=lenTemp
        self.crccut={crc:crc[0:self.CrcCutLen] for crc in AllCrcs }
        self.Info=''

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
        print(f'CrcCalc...{core.InfoFileDone}/{core.InfoTotal}                 ',end='\r')
        time.sleep(0.04)

    ScanThread.join()

    print('')
    print('Done')

