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
#from multiprocessing import Process

import os
import pathlib
import fnmatch
import re

import time
import hashlib

k=1024
M=k*1024
G=M*1024
T=G*1024

MAX_THREADS = os.cpu_count()

OPENED_FILES_PER_DEV_LIMIT=32

def bytes_to_str(num,digits=2):

    if num<512:
        return '%sB' % num
    if (kb:=num/k)<k:
        return '%skB' % round(kb,digits)
    if kb<M:
        return '%sMB' % round(kb/k,digits)
    if kb<G:
        return '%sGB' % round(kb/M,digits)

    return '%sTB' % round(kb/G,digits)

class DudeCore:
    scan_results_by_size=defaultdict(set)
    files_of_size_of_crc=defaultdict(lambda : defaultdict(set))

    sim_size=0
    devs=()
    info=''
    windows=False
    debug=False

    def reset(self):
        self.scan_results_by_size=defaultdict(set)
        self.files_of_size_of_crc=defaultdict(lambda : defaultdict(set))
        self.devs=()
        self.crc_cut_len=40
        self.crc_cut={}
        self.scanned_paths=[]

        self.exclude_list=[]

    def __init__(self,cache_dir,log_par,debug=False):
        self.cache_dir=cache_dir
        self.log=log_par
        self.windows = bool(os.name=='nt')
        self.debug=debug

        self.reset()

    def get_full_path_to_scan(self,pathnr,path,file_name):
        return os.path.join(self.paths_to_scan[pathnr]+path,file_name)

    def get_full_path_scanned(self,pathnr,path,file_name):
        return os.path.join(self.scanned_paths[pathnr]+path,file_name)

    def set_paths_to_scan(self,paths):
        paths_len=len(paths)

        if self.windows:
            paths=[path + ('\\' if path[-1]==':' else '') for path in paths ]
            paths=[path.replace('/','\\').upper() for path in paths]

        abspaths=[os.path.abspath(path) for path in paths]

        for path in abspaths:
            if not os.path.exists(path) or not os.path.isdir(path):
                return  path + '\n\nnot a directory'

        apaths=list(zip(abspaths,paths))

        for p_index1 in range(paths_len):
            for p_index2 in range(paths_len):
                if p_index1!=p_index2:
                    path1,orgpath1=apaths[p_index1]
                    path2,orgpath2=apaths[p_index2]
                    if path2==path1:
                        return  orgpath2 + '\n\nis equal to:\n\n' +  orgpath1 + '\n'
                    if path2.startswith(path1 + os.sep):
                        return  orgpath2 + '\n\nis a subpath of:\n\n' +  orgpath1 + '\n'

        self.paths_to_scan=abspaths
        return False

    def set_exclude_masks(self,reg_exp,masks_list):
        self.excl_fn = (lambda expr,string : re.search(expr,string)) if reg_exp else (lambda expr,string : fnmatch.fnmatch(string,expr))

        teststring='abc'
        for exclmask in masks_list:
            if '|' in exclmask:
                return f"mask:'{exclmask}' - character:'|' not allowed."
            try:
                self.excl_fn(exclmask,teststring)
            except Exception as e:
                return "Expression: '" + exclmask + "'\nERROR:" + str(e)

        self.exclude_list=masks_list
        return False

    abort_action=False
    can_abort=True

    def abort(self):
        self.abort_action=True

    info_path_nr=0
    info_path_to_scan=''
    info_counter=0
    info_size_sum=0

    scan_dir_cache={}
    def set_scan_dir(self,path,path_ctime=None):
        if not path_ctime:
            try:
                path_ctime=round(os.stat(path).st_ctime)
            except Exception as e:
                self.log.error('st_ctime ERROR:%s',e)
                return (0,tuple([]),str(e))

        if path not in self.scan_dir_cache or self.scan_dir_cache[path][0]!=path_ctime:
            try:
                with os.scandir(path) as res:
                    reslist=[]
                    for entry in res:
                        name = entry.name

                        #is_link=entry.is_symlink()
                        #faster ?
                        is_link=os.path.islink(entry)

                        is_dir=entry.is_dir()
                        is_file=entry.is_file()

                        if is_link:
                            mtime=None
                            ctime=None
                            dev=None
                            inode=None
                            size=None
                            nlink=None
                        else:
                            try:
                                stat = os.stat(os.path.join(path,name))

                                mtime=str(round(stat.st_mtime))
                                ctime=str(round(stat.st_ctime))
                                dev=str(stat.st_dev)
                                inode=str(stat.st_ino)
                                size=stat.st_size
                                nlink=stat.st_nlink

                            except Exception as e:
                                self.log.error('scandir(stat): %s is_link:%s is_dir:%s',e,is_link,is_dir )
                                continue

                        reslist.append( (name,is_link,is_dir,is_file,mtime,ctime,dev,inode,size,nlink) )

                    self.scan_dir_cache[path] = ( path_ctime,tuple(reslist) )

            except Exception as e:
                self.log.error('scandir: %s',e)
                self.scan_dir_cache[path] = (0,tuple([]),str(e))

        return self.scan_dir_cache[path]

    def scan(self):
        self.log.info('')
        self.log.info('SCANNING')

        if self.exclude_list:
            self.log.info('exclude_list:' + ' '.join(self.exclude_list))

        self.info_path_nr=0
        self.info_path_to_scan=''

        self.abort_action=False

        path_nr=0
        self.info_counter=0
        self.info_size_sum=0

        self.scan_results_by_size.clear()

        for path_to_scan in self.paths_to_scan:
            loop_list=[(path_to_scan,None)]

            while loop_list:
                try:
                    path,path_ctime = loop_list.pop()
                    for file_name,is_link,isdir,isfile,mtime,ctime,dev,inode,size,nlink in self.set_scan_dir(path,path_ctime)[1]:

                        if self.exclude_list:
                            fullpath=os.path.join(path,file_name)
                            if any({self.excl_fn(expr,fullpath) for expr in self.exclude_list}):
                                self.log.info('skipping by Exclude Mask:%s',fullpath)
                                continue
                        try:
                            if is_link :
                                self.log.debug('skippping link: %s / %s',path,file_name)
                            elif isdir:
                                loop_list.append((os.path.join(path,file_name),ctime))
                            elif isfile:
                                if mtime: #stat succeeded
                                    if nlink!=1:
                                        self.log.debug('scan skipp - hardlinks %s - %s,%s,%s',nlink,path_nr,path,file_name)
                                    else:
                                        if size:
                                            self.info_size_sum+=size

                                            subpath=path.replace(path_to_scan,'')
                                            self.scan_results_by_size[size].add( (path_nr,subpath,file_name,mtime,ctime,dev,inode) )

                                self.info_counter+=1

                                self.info_path_nr=path_nr
                                self.info_path_to_scan=path_to_scan

                                if self.abort_action:
                                    break

                        except Exception as e:
                            self.log.error(e)
                except Exception as e:
                    self.log.error("scanning:'%s' - %s",path_to_scan,e)

                if self.abort_action:
                    break

            path_nr+=1
            if self.abort_action:
                break

        if self.abort_action:
            self.reset()
            return False

        self.devs=tuple(list({dev for size,data in self.scan_results_by_size.items() for pathnr,path,file_name,mtime,ctime,dev,inode in data}))

        ######################################################################
        #inodes collision detection
        known_dev_inodes=defaultdict(int)
        for size,data in self.scan_results_by_size.items():
            for pathnr,path,file_name,mtime,ctime,dev,inode in data:
                index=(dev,inode)
                known_dev_inodes[index]+=1

        self.blacklisted_inodes = {index for index in known_dev_inodes if known_dev_inodes[index]>1}

        for size in list(self.scan_results_by_size):
            for pathnr,path,file_name,mtime,ctime,dev,inode in list(self.scan_results_by_size[size]):
                index=(dev,inode)
                if index in self.blacklisted_inodes:
                    this_index=(pathnr,path,file_name,mtime,ctime,dev,inode)
                    self.log.warning('ignoring conflicting inode entry: %s',this_index)
                    self.scan_results_by_size[size].remove(this_index)

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
        self.info='Reading cache ...'
        self.crc_cache={}
        for dev in self.devs:
            self.crc_cache[dev]={}
            try:
                self.log.debug('reading cache:%s:device:%s',self.cache_dir,dev)
                with open(os.sep.join([self.cache_dir,dev]),'r',encoding='ASCII' ) as cfile:
                    while line:=cfile.readline() :
                        inode,mtime,crc = line.rstrip('\n').split(' ')
                        if crc is None or crc=='None' or crc=='':
                            self.log.warning("crc_cache read error:%s,%s,%s",inode,mtime,crc)
                        else:
                            self.crc_cache[dev][(inode,mtime)]=crc

            except Exception as e:
                self.log.warning(e)
                self.crc_cache[dev]={}

    def crc_cache_write(self):
        self.info='Writing cache ...'

        pathlib.Path(self.cache_dir).mkdir(parents=True,exist_ok=True)
        for (dev,val_dict) in self.crc_cache.items():

            self.log.debug('writing cache:%s:device:%s',self.cache_dir,dev)
            with open(os.sep.join([self.cache_dir,str(dev)]),'w',encoding='ASCII') as cfile:
                for (inode,mtime),crc in val_dict.items():
                    cfile.write(' '.join([str(x) for x in [inode,mtime,crc] ]) +'\n' )

        del self.crc_cache

    write_log=False

    info_size_done=0
    info_files_done=0

    info_total=1
    info_found_groups=0
    info_found_folders=0
    info_found_dupe_space=0
    info_speed=0

    info_threads='?'

    Status=''

    CRC_BUFFER_SIZE=1024*1024

    #############################################################
    def threaded_crc_calc_on_opened_files(self,dev,src_queue,res_queue):
        buf = bytearray(self.CRC_BUFFER_SIZE)
        view = memoryview(buf)

        while True:
            if task := src_queue.get():
                src_queue.task_done()

                file_handle,index_tuple,size,mtime = task
                self.crc_thread_file_info[dev]=(size,index_tuple)

                hasher = hashlib.sha1()
                while rsize := file_handle.readinto(buf):
                    hasher.update(view[:rsize])
                    self.crc_thread_progress_info[dev]+=rsize

                    if self.abort_action:
                        file_handle.close()
                        return

                file_handle.close()

                res_queue.put((index_tuple,size,mtime,hasher.hexdigest()))
                self.crc_thread_progress_info[dev]=0

            else:
                break

    #############################################################

    info_line=None
    def crc_calc(self):
        self.crc_cache_read()

        self.scanned_paths=self.paths_to_scan.copy()

        self.info_size_done=0
        self.info_files_done=0

        self.abort_action=False
        self.can_abort=True

        self.info_found_groups=0
        self.info_found_folders=0
        self.info_found_dupe_space=0
        self.info_speed=0

        self.info_total = len([ 1 for size in self.scan_results_by_size for pathnr,path,file_name,mtime,ctime,dev,inode in self.scan_results_by_size[size] ])

        start = time.time()

        file_names_queue={}
        opened_files_queue={}
        files_crc_queue={}

        self.crc_thread_file_info={}
        self.crc_thread_progress_info={}

        crc_thread={}
        threads_started={}

        for dev in self.devs:
            file_names_queue[dev]=Queue()
            opened_files_queue[dev]=Queue()
            files_crc_queue[dev]=Queue()

            self.crc_thread_file_info[dev]=None
            self.crc_thread_progress_info[dev]=0

            threads_started[dev]=False

            crc_thread[dev] = Thread(target=self.threaded_crc_calc_on_opened_files,args=(dev,opened_files_queue[dev],files_crc_queue[dev],),daemon=True)
            #crc_thread[dev] = Process(target=self.threaded_crc_calc_on_opened_files,args=(dev,opened_files_queue[dev],files_crc_queue[dev],),daemon=True)

        scan_results_sizes = list(self.scan_results_by_size)
        scan_results_sizes.sort(reverse=True)

        #########################################################################################################
        self.info_line="Using cached CRC data ..."

        for size in scan_results_sizes:
            if self.abort_action:
                break

            for pathnr,path,file_name,mtime,ctime,dev,inode in self.scan_results_by_size[size]:
                if self.abort_action:
                    break

                cache_key=(inode,mtime)
                if cache_key in self.crc_cache[dev]:
                    if crc:=self.crc_cache[dev][cache_key]:
                        self.info_size_done+=size
                        self.info_files_done+=1

                        index_tuple=(pathnr,path,file_name,ctime,dev,inode)
                        self.files_of_size_of_crc[size][crc].add( index_tuple )
                        continue

                file_names_queue[dev].put((size,pathnr,path,file_name,mtime,ctime,inode))
        #########################################################################################################

        size_done_cached = self.info_size_done
        files_done_cached = self.info_files_done

        size_done_skipped = 0
        files_done_skipped = 0

        size_done_calculated = 0
        files_done_calculated = 0

        measures_pool=[]

        last_time_info_update=0
        last_time_results_check = 0

        info=''

        prev_line_info={}
        prev_line_show_same_max={}

        for dev in self.devs:
            prev_line_info[dev]=''
            prev_line_show_same_max[dev]=0

        self.info_line="CRC calculation ..."

        thread_pool_need_checking=True
        alive_threads=0

        while True:
            ########################################################################
            # files opening
            anything_opened=False
            for dev in self.devs:
                while not self.abort_action and file_names_queue[dev].qsize()>0 and opened_files_queue[dev].qsize()<OPENED_FILES_PER_DEV_LIMIT:
                    name_combo = file_names_queue[dev].get()
                    file_names_queue[dev].task_done()

                    size,pathnr,path,file_name,mtime,ctime,inode = name_combo

                    try:
                        file_handle=open(self.get_full_path_to_scan(pathnr,path,file_name),'rb')
                    except Exception as e:
                        self.log.error(e)
                        size_done_skipped += size
                        files_done_skipped += 1
                    else:
                        index_tuple=(pathnr,path,file_name,ctime,dev,inode)
                        opened_files_queue[dev].put((file_handle,index_tuple,size,mtime))
                        anything_opened=True

            ########################################################################
            # CRC data processing
            anything_processed=False
            for dev in self.devs:
                while files_crc_queue[dev].qsize()>0:
                    task = files_crc_queue[dev].get()
                    files_crc_queue[dev].task_done()

                    index_tuple,size,mtime,crc = task

                    self.files_of_size_of_crc[size][crc].add( index_tuple )
                    anything_processed=True

                    dev=index_tuple[4]
                    inode=index_tuple[5]
                    cache_key=(inode,mtime)
                    self.crc_cache[dev][cache_key]=crc

                    size_done_calculated+=size
                    files_done_calculated+=1

            ########################################################################
            # threads starting/finishing

            any_thread_started=False
            alive_threads=len({dev for dev in self.devs if crc_thread[dev].is_alive()})

            if thread_pool_need_checking:
                if alive_threads<MAX_THREADS:
                    for dev in self.devs:
                        if not threads_started[dev] and not crc_thread[dev].is_alive():
                            crc_thread[dev].start()
                            threads_started[dev]=True
                            any_thread_started=True
                            break

                all_started=True
                for dev in self.devs:
                    if not threads_started[dev]:
                        all_started=False
                        break
                if all_started:
                    thread_pool_need_checking=False

            for dev in self.devs:
                if self.abort_action or (file_names_queue[dev].qsize()==0 and opened_files_queue[dev].qsize()==0):
                    if crc_thread[dev].is_alive():
                        opened_files_queue[dev].put(None)

            ########################################################################
            # info

            now=time.time()
            if now-last_time_info_update>0.05 and not self.abort_action:
                last_time_info_update=now

                #######################################################
                #sums info
                self.info_size_done = size_done_cached + size_done_skipped + size_done_calculated + sum([self.crc_thread_progress_info[dev] for dev in self.devs])
                self.info_files_done = files_done_cached + files_done_skipped + files_done_calculated

                if self.debug:
                    self.info_threads=str(alive_threads)

                    #######################################################
                    #speed
                    measures_pool=[(pool_time,FSize) for (pool_time,FSize) in measures_pool if (now-pool_time)<3] + [(now,self.info_size_done)]

                    first=measures_pool[0]
                    if last_period_time_diff := now - first[0]:
                        last_period_size_sum  = self.info_size_done - first[1]
                        self.info_speed=int(last_period_size_sum/last_period_time_diff)

                    #######################################################
                    #status line info

                    line_info_list=[]
                    for dev in self.devs:
                        #size,pathnr,path,file_name
                        if self.crc_thread_progress_info[dev] and self.crc_thread_file_info[dev]:
                            curr_line_info_file_size=self.crc_thread_file_info[dev][0]
                            curr_line_info_file_name=self.crc_thread_file_info[dev][1][2]

                            if curr_line_info_file_size==prev_line_info[dev]:
                                if now-prev_line_show_same_max[dev]>1:
                                    line_info_list.append( (curr_line_info_file_size,str(curr_line_info_file_name) + ' [' + bytes_to_str(self.crc_thread_progress_info[dev]) + '/' + bytes_to_str(curr_line_info_file_size) + ']') )
                            else:
                                prev_line_show_same_max[dev]=now
                                prev_line_info[dev]=curr_line_info_file_size

                    self.info_line = '    '.join([elem[1] for elem in sorted(line_info_list,key=lambda x : x[0],reverse=True)])

                #######################################################
                #found
                if now-last_time_results_check>2 and not self.abort_action:
                    last_time_results_check=now

                    temp_info_groups=0
                    temp_info_folders=set()
                    temp_info_dupe_space=0

                    for size,size_dict in self.files_of_size_of_crc.items():
                        for crc_dict in size_dict.values():
                            if len(crc_dict)>1:
                                temp_info_groups+=1
                                for pathnr,path,file_name,ctime,dev,inode in crc_dict:
                                    temp_info_dupe_space+=size
                                    temp_info_folders.add((pathnr,path))

                    self.info_found_groups=temp_info_groups
                    self.info_found_folders=len(temp_info_folders)
                    self.info_found_dupe_space=temp_info_dupe_space
            elif not anything_opened and not anything_processed and not any_thread_started:
                if alive_threads==0:
                    #all_crc_processed
                    if all(files_crc_queue[dev].qsize()==0 for dev in self.devs):
                        break
                else:
                    time.sleep(0.01)

            ########################################################################

        self.can_abort=False

        for dev in self.devs:
            crc_thread[dev].join()

        self.info='Pruning data ...'
        for size in scan_results_sizes:
            self.check_crc_pool_and_prune(size)

        self.crc_cache_write()
        self.crc_to_size = {crc:size for size,size_dict in self.files_of_size_of_crc.items() for crc in size_dict}

        end=time.time()
        self.log.debug('total time = %s',end-start)

        self.calc_crc_min_len()

        if self.write_log:
            self.info='Writing log ...'
            self.log_scan_results()

    def check_group_files_state(self,size,crc):
        res_problems=[]
        to_remove=[]

        if self.files_of_size_of_crc[size][crc]:
            for pathnr,path,file_name,ctime,dev,inode in self.files_of_size_of_crc[size][crc]:
                full_path=self.get_full_path_to_scan(pathnr,path,file_name)
                problem=False
                try:
                    stat = os.stat(full_path)
                except Exception as e:
                    res_problems.append('%s|RED' % e)
                    problem=True
                else:
                    if stat.st_nlink!=1:
                        res_problems.append('file became hardlink:%s - %s,%s,%s' % (stat.st_nlink,pathnr,path,file_name) )
                        problem=True
                    else:
                        if (size,ctime,dev,inode) != (stat.st_size,str(round(stat.st_ctime)),str(stat.st_dev),str(stat.st_ino)):
                            res_problems.append('file changed:%s,%s,%s,%s vs %s,%s,%s,%s' % (size,ctime,dev,inode,stat.st_size,round(stat.st_ctime),stat.st_dev,stat.st_ino) )
                            problem=True
                if problem:
                    index_tuple=(pathnr,path,file_name,ctime,dev,inode)
                    to_remove.append(index_tuple)
        else :
            res_problems.append('no data')

        return (res_problems,to_remove)

    def log_scan_results(self):
        self.log.info('#######################################################')
        self.log.info('scan and crc calculation complete')
        self.log.info('')
        self.log.info('scanned paths:')
        for (index,path) in enumerate(self.paths_to_scan):
            self.log.info('  %s  <-> %s',index,path)

        for size in self.files_of_size_of_crc:
            self.log.info('')
            self.log.info('size:%s',size)
            for crc in self.files_of_size_of_crc[size]:
                self.log.info('  crc:%s',crc)
                for index_tuple in self.files_of_size_of_crc[size][crc]:
                    self.log.info('    ' + ' '.join( [str(elem) for elem in list(index_tuple) ]))
        self.log.info('#######################################################')

    def write_csv(self,file_name):
        self.log.info('writing csv file: %s',file_name)

        with open(file_name,'w') as csv_file:
            csv_file.write('#size,crc,filepath\n#no checking if the path contains a comma\n')
            for size in self.files_of_size_of_crc:
                for crc in self.files_of_size_of_crc[size]:
                    csv_file.write('%s,%s,\n' % (size,crc) )
                    for index_tuple in sorted(self.files_of_size_of_crc[size][crc],key= lambda x : x[5]):
                        #(pathnr,path,file_name,ctime,dev,inode)
                        csv_file.write(',,%s\n' % self.get_path(index_tuple) )
            self.log.info('#######################################################')

    def check_crc_pool_and_prune(self,size):
        for crc in list(self.files_of_size_of_crc[size]):
            if len(self.files_of_size_of_crc[size][crc])<2 :
                del self.files_of_size_of_crc[size][crc]

        if len(self.files_of_size_of_crc[size])==0 :
            del self.files_of_size_of_crc[size]

    def calc_crc_min_len(self):
        self.info='CRC min length calculation ...'
        all_crcs_len=len(all_crcs:={crc for size,size_dict in self.files_of_size_of_crc.items() for crc in size_dict})

        len_temp=1
        while len({crc[0:len_temp] for crc in all_crcs})!=all_crcs_len:
            self.info='CRC min length calculation ... (%s)' % len_temp
            len_temp+=1

        self.crc_cut_len=len_temp
        self.crc_cut={crc:crc[0:self.crc_cut_len] for crc in all_crcs }
        self.info=''

    def rename_file(self,src,dest):
        self.log.info('renaming file:%s->%s',src,dest)
        try:
            os.rename(src,dest)
            return False
        except Exception as e:
            self.log.error(e)
            return 'Rename error:' + str(e)

    def delete_file(self,file_name):
        self.log.info('deleting file:%s',file_name)
        try:
            os.remove(file_name)
            return False
        except Exception as e:
            self.log.error(e)
            return 'Delete error:' + str(e)

    def do_soft_link(self,src,dest,relative=True):
        self.log.info('soft-linking %s<-%s (relative:%s)',src,dest,relative)
        try:
            if relative:
                dest_dir = os.path.dirname(dest)
                src_rel = os.path.relpath(src, dest_dir)
                os.symlink(src_rel,dest)
            else:
                os.symlink(src,dest)
            return False
        except Exception as e:
            self.log.error(e)
            return 'Error on soft linking:' + str(e)

    def do_hard_link(self,src,dest):
        self.log.info('hard-linking %s<-%s',src,dest)
        try:
            os.link(src,dest)
            return False
        except Exception as e:
            self.log.error(e)
            return 'Error on hard linking:' + str(e)

    def reduce_crc_cut(self,size,crc):
        if size not in self.files_of_size_of_crc or crc not in self.files_of_size_of_crc[size]:
            del self.crc_cut[crc]

    def remove_from_data_pool(self,size,crc,index_tuple_list):
        for index_tuple in index_tuple_list:
            self.log.debug('remove_from_data_pool:%s,%s,%s',size,crc,index_tuple)
            self.files_of_size_of_crc[size][crc].remove(index_tuple)

        self.check_crc_pool_and_prune(size)
        self.reduce_crc_cut(size,crc)

    def get_path(self,index_tuple):
        (pathnr,path,file_name,ctime,dev,inode)=index_tuple
        return self.scanned_paths[pathnr]+path

    def delete_file_wrapper(self,size,crc,index_tuple_list):
        messages=[]
        index_tuples_list_done=[]
        for index_tuple in index_tuple_list:
            self.log.debug("delete_file_wrapper:%s,%s,%s",size,crc,index_tuple)

            (pathnr,path,file_name,ctime,dev,inode)=index_tuple
            full_file_path=self.get_full_path_scanned(pathnr,path,file_name)

            if index_tuple in self.files_of_size_of_crc[size][crc]:
                if message:=self.delete_file(full_file_path):
                    #self.info('Error',message,self.main)
                    messages.append(message)
                else:
                    index_tuples_list_done.append(index_tuple)
            else:
                messages.append('delete_file_wrapper - Internal Data Inconsistency:' + full_file_path + ' / ' + str(index_tuple))

        self.remove_from_data_pool(size,crc,index_tuples_list_done)

        return messages

    def link_wrapper(self,\
            soft,relative,size,crc,\
            index_tuple_ref,index_tuple_list):

        self.log.debug('link_wrapper:%s,%s,%s,%s:%s:%s',soft,relative,size,crc,index_tuple_ref,index_tuple_list)

        (path_nr_keep,path_keep,file_keep,ctime_keep,dev_keep,inode_keep)=index_tuple_ref

        full_file_path_keep=self.get_full_path_scanned(path_nr_keep,path_keep,file_keep)

        if index_tuple_ref not in self.files_of_size_of_crc[size][crc]:
            return 'link_wrapper - Internal Data Inconsistency:' + full_file_path_keep + ' / ' + str(index_tuple_ref)

        for index_tuple in index_tuple_list:
            (pathnr,path,file_name,ctime,dev,inode)=index_tuple
            full_file_path=self.get_full_path_scanned(pathnr,path,file_name)

            if index_tuple not in self.files_of_size_of_crc[size][crc]:
                return 'link_wrapper - Internal Data Inconsistency:' + full_file_path + ' / ' + str(index_tuple)

            temp_file=full_file_path+'.temp'

            if not self.rename_file(full_file_path,temp_file):
                if soft:
                    any_problem=self.do_soft_link(full_file_path_keep,full_file_path,relative)
                else:
                    any_problem=self.do_hard_link(full_file_path_keep,full_file_path)

                if any_problem:
                    self.rename_file(temp_file,full_file_path)
                    return any_problem

                if message:=self.delete_file(temp_file):
                    self.log.error(message)
                    #self.info('Error',message,self.main)
                #self.remove_from_data_pool(size,crc,index_tuple)
                self.files_of_size_of_crc[size][crc].remove(index_tuple)
        if not soft:
            #self.remove_from_data_pool(size,crc,index_tuple_ref)
            self.files_of_size_of_crc[size][crc].remove(index_tuple_ref)

        self.check_crc_pool_and_prune(size)
        self.reduce_crc_cut(size,crc)
        return ''

############################################################################################
if __name__ == "__main__":
    import logging

    import test

    LOG_DIR = "./test/log"
    pathlib.Path(LOG_DIR).mkdir(parents=True,exist_ok=True)

    log=LOG_DIR + os.sep + time.strftime('%Y_%m_%d_%H_%M_%S',time.localtime(time.time()) ) +'.log'

    print('log:',log)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s', filename=log,filemode='w')

    print('dude core test ...')
    core=DudeCore('./test/cache',logging)

    TEST_DIR='test/files'
    if not os.path.exists(TEST_DIR):
        test.generate(TEST_DIR)

    core.set_paths_to_scan([TEST_DIR])
    core.set_exclude_masks(False,[])

    core.write_log=True

    scan_thread=Thread(target=core.scan,daemon=True)
    scan_thread.start()

    while scan_thread.is_alive():
        print('Scanning ...', core.info_counter,end='\r')
        time.sleep(0.04)

    scan_thread.join()

    scan_thread=Thread(target=core.crc_calc,daemon=True)
    scan_thread.start()

    while scan_thread.is_alive():
        print(f'crc_calc...{core.info_files_done}/{core.info_total}                 ',end='\r')
        time.sleep(0.04)

    scan_thread.join()

    print('')
    print('Done')
