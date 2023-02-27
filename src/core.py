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

def bytes_to_str(num,digits=2):
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

class DudeCore:
    scan_results_by_size=defaultdict(set)
    files_of_size_of_crc=defaultdict(lambda : defaultdict(set))

    sim_size=0
    devs=[]
    info=''
    windows=False

    def reset(self):
        self.scan_results_by_size=defaultdict(set)
        self.files_of_size_of_crc=defaultdict(lambda : defaultdict(set))
        self.devs.clear()
        self.CrcCutLen=40
        self.crccut={}
        self.scanned_paths=[]

        self.ExcludeList=[]

    def __init__(self,CacheDir,Log):
        self.CacheDir=CacheDir
        self.Log=Log
        self.windows = (os.name=='nt')

        self.reset()

    def get_full_path_to_scan(self,pathnr,path,file):
        return os.path.join(self.Paths2Scan[pathnr]+path,file)

    def get_full_path_scanned(self,pathnr,path,file):
        return os.path.join(self.scanned_paths[pathnr]+path,file)

    def set_paths_to_scan(self,paths):
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

    def set_exclude_masks(self,RegExp,MasksList):
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

    abort_action=False
    can_abort=True

    def abort(self):
        self.abort_action=True

    info_path_nr=0
    info_path_to_scan=''
    info_counter=0
    info_size_sum=0

    ScanDirCache={}
    def set_scan_dir(self,path,PathCTime=None):

        if not PathCTime:
            try:
                PathCTime=round(os.stat(path).st_ctime)
            except Exception as e:
                self.Log.error(f'ERROR:{e}')
                return (0,tuple([]))

        if path not in self.ScanDirCache or self.ScanDirCache[path][0]!=PathCTime:
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
                                self.Log.error('scandir(stat): %s islink:%s is_dir:%s' % (str(e),str(islink),str(is_dir) ) )

                        reslist.append( (name,islink,is_dir,is_file,mtime,ctime,dev,inode,size,nlink) )

                    self.ScanDirCache[path] = ( PathCTime,tuple(reslist) )

            except Exception as e:
                self.Log.error('scandir: %s' % str(e))
                self.ScanDirCache[path] = (0,tuple([]))

        return self.ScanDirCache[path]

    def scan(self):
        self.Log.info('')
        self.Log.info('SCANNING')

        if self.ExcludeList:
            self.Log.info('ExcludeList:' + ' '.join(self.ExcludeList))

        self.info_path_nr=0
        self.info_path_to_scan=''

        self.abort_action=False

        pathNr=0
        self.info_counter=0
        self.info_size_sum=0

        self.scan_results_by_size.clear()

        #self.ScanDirCache={}

        for PathToScan in self.Paths2Scan:
            loopList=[(PathToScan,None)]

            while loopList:
                try:
                    path,PathCTime = loopList.pop(0)
                    for file,islink,isdir,isfile,mtime,ctime,dev,inode,size,nlink in self.set_scan_dir(path,PathCTime)[1]:

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
                                            self.info_size_sum+=size

                                            subpath=path.replace(PathToScan,'')
                                            self.scan_results_by_size[size].add( (pathNr,subpath,file,mtime,ctime,dev,inode) )

                                self.info_counter+=1

                                self.info_path_nr=pathNr
                                self.info_path_to_scan=PathToScan

                                if self.abort_action:
                                    break

                        except Exception as e:
                            self.Log.error(e)
                except Exception as e:
                    self.Log.error(f"scanning:'{PathToScan}' - '{e}'")

                if self.abort_action:
                    break

            pathNr+=1
            if self.abort_action:
                break

        if self.abort_action:
            self.reset()
            return False

        self.devs=list({dev for size,data in self.scan_results_by_size.items() for pathnr,path,file,mtime,ctime,dev,inode in data})

        ######################################################################
        #inodes collision detection
        knownDevInodes=defaultdict(int)
        for size,data in self.scan_results_by_size.items():
            for pathnr,path,file,mtime,ctime,dev,inode in data:
                index=(dev,inode)
                knownDevInodes[index]+=1

        self.blacklistedInodes = {index for index in knownDevInodes if knownDevInodes[index]>1}

        for size in list(self.scan_results_by_size):
            for pathnr,path,file,mtime,ctime,dev,inode in list(self.scan_results_by_size[size]):
                index=(dev,inode)
                if index in self.blacklistedInodes:
                    thisIndex=(pathnr,path,file,mtime,ctime,dev,inode)
                    self.Log.warning('ignoring conflicting inode entry:' + str(thisIndex))
                    self.scan_results_by_size[size].remove(thisIndex)

        ######################################################################
        self.sim_size=0
        for size in list(self.scan_results_by_size):
            quant=len(self.scan_results_by_size[size])
            if quant==1 :
                del self.scan_results_by_size[size]
            else:
                self.sim_size += quant*size
        ######################################################################
        return True

    def crc_cache_read(self):
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

    def crc_cache_write(self):
        self.Info='Writing cache ...'
        pathlib.Path(self.CacheDir).mkdir(parents=True,exist_ok=True)
        for dev in self.CRCCache:
            self.Log.debug(f'writing cache:{self.CacheDir}:device:{dev}')
            with open(os.sep.join([self.CacheDir,str(dev)]),'w' ) as cfile:
                for (inode,mtime),crc in self.CRCCache[dev].items():
                    cfile.write(' '.join([str(x) for x in [inode,mtime,crc] ]) +'\n' )
        del self.CRCCache

    writeLog=False

    info_size_done=0
    info_files_done=0

    info_total=1
    info_found_groups=0
    info_found_folders=0
    info_found_dupe_space=0
    info_speed=0

    info_threads='?'

    Status=''

    CRCBUfferSize=1024*1024

    #############################################################
    def threaded_crc_calc_on_opened_files(self,dev,SrcQ,ResQ):
        buf = bytearray(self.CRCBUfferSize)
        view = memoryview(buf)

        SizeDone=0
        FilesDone=0

        while True:
            Task = SrcQ.get()
            SrcQ.task_done()

            if Task:
                File,index_tuple,size,mtime = Task
                h = hashlib.sha1()

                self.CrcThreadProgressInfo[dev]=0

                self.CrcThreadFileInfo[dev]=(size,index_tuple)
                while rsize := File.readinto(buf):
                    h.update(view[:rsize])
                    self.CrcThreadProgressInfo[dev]+=rsize

                    if self.abort_action:
                        break

                if not self.abort_action:
                    ResQ.put((File,index_tuple,size,mtime,h.hexdigest()))
                    SizeDone+=size
                    FilesDone+=1
                    self.CrcThreadTotalInfo[dev]=(FilesDone,SizeDone)

                self.CrcThreadProgressInfo[dev]=0
                self.CrcThreadFileInfo[dev]=None

                File.close()
            else:
                break

        return
    #############################################################

    InfoLine=None
    def crc_calc(self):
        self.crc_cache_read()

        self.scanned_paths=self.Paths2Scan.copy()

        self.info_size_done=0
        self.info_files_done=0

        self.abort_action=False
        self.can_abort=True

        self.info_found_groups=0
        self.info_found_folders=0
        self.info_found_dupe_space=0
        self.info_speed=0

        self.info_total = len([ 1 for size in self.scan_results_by_size for pathnr,path,file,mtime,ctime,dev,inode in self.scan_results_by_size[size] ])

        start = time.time()

        MaxThreads = os.cpu_count()

        FileNamesQueue={}
        OpenedFilesQueue={}
        FilesCrcQueue={}

        self.CrcThreadTotalInfo={}
        self.CrcThreadFileInfo={}
        self.CrcThreadProgressInfo={}

        CRCThread={}
        ThreadStarted={}

        for dev in self.devs:
            FileNamesQueue[dev]=Queue()
            OpenedFilesQueue[dev]=Queue()
            FilesCrcQueue[dev]=Queue()

            self.CrcThreadTotalInfo[dev]=(0,0)
            self.CrcThreadFileInfo[dev]=None
            self.CrcThreadProgressInfo[dev]=0

            ThreadStarted[dev]=False

            CRCThread[dev] = Thread(target=self.threaded_crc_calc_on_opened_files,args=(dev,OpenedFilesQueue[dev],FilesCrcQueue[dev],),daemon=True)

        ScanResultsSizes = list(self.scan_results_by_size)
        ScanResultsSizes.sort(reverse=True)

        #########################################################################################################
        self.InfoLine="Using cached CRC data ..."

        for size in ScanResultsSizes:
            if self.abort_action:
                break

            for pathnr,path,file,mtime,ctime,dev,inode in self.scan_results_by_size[size]:
                if self.abort_action:
                    break

                CacheKey=(inode,mtime)
                if CacheKey in self.CRCCache[dev]:
                    if crc:=self.CRCCache[dev][CacheKey]:
                        self.info_size_done+=size
                        self.info_files_done+=1

                        index_tuple=(pathnr,path,file,ctime,dev,inode)
                        self.files_of_size_of_crc[size][crc].add( index_tuple )
                        continue

                FileNamesQueue[dev].put((size,pathnr,path,file,mtime,ctime,inode))
        #########################################################################################################

        InfoSizeNotCalculated=self.info_size_done
        InfoFilesNotCalculated=self.info_files_done

        OpenedFilesPerDevLimit=32

        MeasuresPool=[]

        LastTimeInfoUpdate=0
        LastTimeResultsCheck = 0
        LastTimeLineInfoUpdate = 0

        Info=''

        prevLineInfo={}
        prevLineShowSameMax={}

        for dev in self.devs:
            prevLineInfo[dev]=''
            prevLineShowSameMax[dev]=0

        self.InfoLine="CRC calculation ..."

        while True:
            ########################################################################
            # files opening
            AnythingOpened=False
            for dev in self.devs:
                while not self.abort_action and FileNamesQueue[dev].qsize()>0 and OpenedFilesQueue[dev].qsize()<OpenedFilesPerDevLimit:
                    NameCombo = FileNamesQueue[dev].get()
                    FileNamesQueue[dev].task_done()

                    size,pathnr,path,file,mtime,ctime,inode = NameCombo

                    try:
                        File=open(self.get_full_path_to_scan(pathnr,path,file),'rb')
                    except Exception as e:
                        self.Log.error(e)
                        InfoSizeNotCalculated+=size
                        InfoFilesNotCalculated+=1
                    else:
                        index_tuple=(pathnr,path,file,ctime,dev,inode)
                        OpenedFilesQueue[dev].put((File,index_tuple,size,mtime))
                        AnythingOpened=True

            ########################################################################
            # CRC data processing
            AnythingProcessed=False
            for dev in self.devs:
                while FilesCrcQueue[dev].qsize()>0:
                    Task = FilesCrcQueue[dev].get()
                    FilesCrcQueue[dev].task_done()

                    File,index_tuple,size,mtime,crc = Task

                    self.files_of_size_of_crc[size][crc].add( index_tuple )
                    AnythingProcessed=True

                    dev=index_tuple[4]
                    inode=index_tuple[5]
                    CacheKey=(inode,mtime)
                    self.CRCCache[dev][CacheKey]=crc

            ########################################################################
            # threads starting/finishing

            AliveThreads=sum([1 if CRCThread[dev].is_alive() else 0 for dev in self.devs])
            AllCrcProcessed=all(FilesCrcQueue[dev].qsize()==0 for dev in self.devs)

            NothingStarted=True
            if AliveThreads<MaxThreads:
                for dev in self.devs:
                    if not ThreadStarted[dev] and not CRCThread[dev].is_alive():
                        CRCThread[dev].start()
                        ThreadStarted[dev]=True
                        NothingStarted=False
                        break

            for dev in self.devs:
                if self.abort_action or (FileNamesQueue[dev].qsize()==0 and OpenedFilesQueue[dev].qsize()==0):
                    if CRCThread[dev].is_alive():
                        OpenedFilesQueue[dev].put(None)

            if NothingStarted and AliveThreads==0 and AllCrcProcessed:
                break
            elif not AnythingOpened and not AnythingProcessed and NothingStarted:
                self.info_threads=str(AliveThreads)
                time.sleep(0.01)

            ########################################################################
            # info
            now=time.time()

            if now-LastTimeInfoUpdate>0.02 and not self.abort_action:
                LastTimeInfoUpdate=now

                #######################################################
                #sums info
                InfoSizeDoneTemp=InfoSizeNotCalculated
                InfoFilesDoneTemp=InfoFilesNotCalculated

                for dev in self.devs:
                    FilesDone,SizeDone= self.CrcThreadTotalInfo[dev]
                    InfoSizeDoneTemp+=SizeDone
                    InfoSizeDoneTemp+=self.CrcThreadProgressInfo[dev]
                    InfoFilesDoneTemp+=FilesDone

                self.info_size_done=InfoSizeDoneTemp
                self.info_files_done=InfoFilesDoneTemp
                #######################################################
                #speed
                MeasuresPool=[(PoolTime,FSize,FQuant) for (PoolTime,FSize,FQuant) in MeasuresPool if (now-PoolTime)<3]
                MeasuresPool.append((now,InfoSizeDoneTemp,InfoFilesDoneTemp))

                first=MeasuresPool[0]

                if LastPeriodTimeDiff := now - first[0]:
                    LastPeriodSizeSum  = InfoSizeDoneTemp - first[1]
                    self.info_speed=int(LastPeriodSizeSum/LastPeriodTimeDiff)

                #######################################################
                #found
                if now-LastTimeResultsCheck>2 and not self.abort_action:
                    LastTimeResultsCheck=now

                    temp_info_groups=0
                    temp_info_folders=set()
                    temp_info_dupe_space=0

                    for size,sizeDict in self.files_of_size_of_crc.items():
                        for crcDict in sizeDict.values():
                            if len(crcDict)>1:
                                temp_info_groups+=1
                                for pathnr,path,file,ctime,dev,inode in crcDict:
                                    temp_info_dupe_space+=size
                                    temp_info_folders.add((pathnr,path))

                    self.info_found_groups=temp_info_groups
                    self.info_found_folders=len(temp_info_folders)
                    self.info_found_dupe_space=temp_info_dupe_space

                #######################################################
                #status line info
                if now-LastTimeLineInfoUpdate>0.25 and not self.abort_action:
                    LastTimeLineInfoUpdate=now

                    LineInfoList=[]
                    for dev in self.devs:
                        #size,pathnr,path,file
                        if self.CrcThreadProgressInfo[dev] and self.CrcThreadFileInfo[dev]:
                            currLineInfoFileSize=self.CrcThreadFileInfo[dev][0]
                            currLineInfoFileName=self.CrcThreadFileInfo[dev][1][2]

                            if currLineInfoFileSize==prevLineInfo[dev]:
                                if now-prevLineShowSameMax[dev]>1:
                                    LineInfoList.append( (currLineInfoFileSize,str(currLineInfoFileName) + ' [' + bytes_to_str(self.CrcThreadProgressInfo[dev]) + '/' + bytes_to_str(currLineInfoFileSize) + ']') )
                            else:
                                prevLineShowSameMax[dev]=now
                                prevLineInfo[dev]=currLineInfoFileSize

                    self.InfoLine = '    '.join([elem[1] for elem in sorted(LineInfoList,key=lambda x : x[0],reverse=True)])

            ########################################################################

        self.can_abort=False

        for dev in self.devs:
            CRCThread[dev].join()

        self.Info='Pruning data ...'
        for size in ScanResultsSizes:
            self.check_crc_pool_and_prune(size)

        self.crc_cache_write()
        self.Crc2Size = {crc:size for size,sizeDict in self.files_of_size_of_crc.items() for crc in sizeDict}

        end=time.time()
        self.Log.debug(f'total time = {end-start}s')

        self.CalcCrcMinLen()

        if self.writeLog:
            self.Info='Writing log ...'
            self.log_scan_results()

    def check_group_files_state(self,size,crc):
        resProblems=[]
        toRemove=[]

        if self.files_of_size_of_crc[size][crc]:
            for pathnr,path,file,ctime,dev,inode in self.files_of_size_of_crc[size][crc]:
                FullPath=self.get_full_path_to_scan(pathnr,path,file)
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
                    index_tuple=(pathnr,path,file,ctime,dev,inode)
                    toRemove.append(index_tuple)
        else :
            resProblems.append('no data')

        return (resProblems,toRemove)

    def log_scan_results(self):
        self.Log.info('#######################################################')
        self.Log.info('scan and crc calculation complete')
        self.Log.info('')
        self.Log.info('scanned paths:')
        for (nr,path) in enumerate(self.Paths2Scan):
            self.Log.info(f'  {nr}  <->  {path}',)

        for size in self.files_of_size_of_crc:
            self.Log.info('')
            self.Log.info(f'size:{size}')
            for crc in self.files_of_size_of_crc[size]:
                self.Log.info(f'  crc:{crc}')
                for index_tuple in self.files_of_size_of_crc[size][crc]:
                    self.Log.info('    ' + ' '.join( [str(elem) for elem in list(index_tuple) ]))
        self.Log.info('#######################################################')

    def check_crc_pool_and_prune(self,size):
        for crc in list(self.files_of_size_of_crc[size]):
            if len(self.files_of_size_of_crc[size][crc])<2 :
                del self.files_of_size_of_crc[size][crc]

        if len(self.files_of_size_of_crc[size])==0 :
            del self.files_of_size_of_crc[size]

    def CalcCrcMinLen(self):
        self.Info='CRC min length calculation ...'
        allCrcLen=len(AllCrcs:={crc for size,sizeDict in self.files_of_size_of_crc.items() for crc in sizeDict})

        lenTemp=1
        while len({crc[0:lenTemp] for crc in AllCrcs})!=allCrcLen:
            self.Info='CRC min length calculation ... (%s)' % lenTemp
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

    def delete_file(self,file):
        self.Log.info(f'deleting file:{file}')
        try:
            os.remove(file)
            return False
        except Exception as e:
            self.Log.error(e)
            return 'Delete error:' + str(e)

    def do_soft_link(self,src,dest,relative=True):
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

    def do_hard_link(self,src,dest):
        self.Log.info(f'hard-linking {src}<-{dest}')
        try:
            os.link(src,dest)
            return False
        except Exception as e:
            self.Log.error(e)
            return 'Error on hard linking:' + str(e)

    def reduce_crc_cut(self,size,crc):
        if size not in self.files_of_size_of_crc or crc not in self.files_of_size_of_crc[size]:
            del self.crccut[crc]

    def remove_from_data_pool(self,size,crc,index_tuple_list):
        for index_tuple in index_tuple_list:
            self.Log.debug(f'remove_from_data_pool:{size},{crc},{index_tuple}')
            self.files_of_size_of_crc[size][crc].remove(index_tuple)

        self.check_crc_pool_and_prune(size)
        self.reduce_crc_cut(size,crc)

    def get_path(self,index_tuple):
        (pathnr,path,file,ctime,dev,inode)=index_tuple
        return self.scanned_paths[pathnr]+path

    def delete_file_wrapper(self,size,crc,index_tuple_list):
        Messages=[]
        index_tuples_list_done=[]
        for index_tuple in index_tuple_list:
            self.Log.debug(f"delete_file_wrapper:{size},{crc},{index_tuple}")

            (pathnr,path,file,ctime,dev,inode)=index_tuple
            full_file_path=self.get_full_path_scanned(pathnr,path,file)

            if index_tuple in self.files_of_size_of_crc[size][crc]:
                if message:=self.delete_file(full_file_path):
                    #self.Info('Error',message,self.main)
                    Messages.append(message)
                else:
                    index_tuples_list_done.append(index_tuple)
            else:
                Messages.append('delete_file_wrapper - Internal Data Inconsistency:' + full_file_path + ' / ' + str(index_tuple))

        self.remove_from_data_pool(size,crc,index_tuples_list_done)

        return Messages

    def link_wrapper(self,\
            soft,relative,size,crc,\
            index_tuple_ref,index_tuple_list):

        self.Log.debug(f'link_wrapper:{soft},{relative},{size},{crc}:{index_tuple_ref}:{index_tuple_list}')

        (path_nr_keep,path_keep,file_keep,ctime_keep,dev_keep,inode_keep)=index_tuple_ref

        full_file_path_keep=self.get_full_path_scanned(path_nr_keep,path_keep,file_keep)

        if index_tuple_ref not in self.files_of_size_of_crc[size][crc]:
            return 'link_wrapper - Internal Data Inconsistency:' + full_file_path_keep + ' / ' + str(index_tuple_ref)
        else :
            for index_tuple in index_tuple_list:
                (pathnr,path,file,ctime,dev,inode)=index_tuple
                full_file_path=self.get_full_path_scanned(pathnr,path,file)

                if index_tuple not in self.files_of_size_of_crc[size][crc]:
                    return 'link_wrapper - Internal Data Inconsistency:' + full_file_path + ' / ' + str(index_tuple)
                else:
                    tempFile=full_file_path+'.temp'

                    if not self.RenameFile(full_file_path,tempFile):
                        if soft:
                            AnyProblem=self.do_soft_link(full_file_path_keep,full_file_path,relative)
                        else:
                            AnyProblem=self.do_hard_link(full_file_path_keep,full_file_path)

                        if AnyProblem:
                            self.RenameFile(tempFile,full_file_path)
                            return AnyProblem
                        else:
                            if message:=self.delete_file(tempFile):
                                self.Log.error(message)
                                #self.Info('Error',message,self.main)
                            #self.remove_from_data_pool(size,crc,index_tuple)
                            self.files_of_size_of_crc[size][crc].remove(index_tuple)
            if not soft:
                #self.remove_from_data_pool(size,crc,index_tuple_ref)
                self.files_of_size_of_crc[size][crc].remove(index_tuple_ref)

            self.check_crc_pool_and_prune(size)
            self.reduce_crc_cut(size,crc)

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

    core.set_paths_to_scan([TestDir])
    core.set_exclude_masks(False,[])

    core.writeLog=True

    ScanThread=Thread(target=core.scan,daemon=True)
    ScanThread.start()

    while ScanThread.is_alive():
        print('Scanning ...', core.info_counter,end='\r')
        time.sleep(0.04)

    ScanThread.join()

    ScanThread=Thread(target=core.crc_calc,daemon=True)
    ScanThread.start()

    while ScanThread.is_alive():
        print(f'crc_calc...{core.info_files_done}/{core.info_total}                 ',end='\r')
        time.sleep(0.04)

    ScanThread.join()

    print('')
    print('Done')

