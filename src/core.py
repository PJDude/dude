#!/usr/bin/python3

####################################################################################
#
#  Copyright (c) 2022-2024 Piotr Jochymek
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
from threading import Thread

from pathlib import Path
from fnmatch import fnmatch
from re import search

from time import sleep
from time import strftime
from time import localtime
from time import time
from hashlib import sha1

from os import stat
from os import scandir
from os import sep
from os import symlink
from os import link
from os import cpu_count
from os import name as os_name
from os import rename as os_rename
from os import remove as os_remove

from os.path import dirname
from os.path import relpath
from os.path import normpath
from os.path import join as path_join
from os.path import abspath as abspath
from os.path import exists as path_exists
from os.path import isdir as path_isdir

from send2trash import send2trash

def bytes_to_str(num):
    if num < 1024:
        return "%sB" % num

    numx100=num*100

    for unit in ('kB','MB','GB','TB'):
        numx100 //= 1024
        if numx100 < 102400:
            s=str(numx100)
            s_main,s_frac=s[:-2],s[-2:]

            if s_frac_strip := s_frac.rstrip('0'):
                return "%s.%s%s" % (s_main,s_frac_strip,unit)

            return "%s%s" % (s_main,unit)

    return "BIG"

class CRCThreadedCalc:
    def __init__(self,log):
        self.log=log
        self.source=[]
        self.source_other_data=[]

        self.results=[]
        self.file_info=(0,None)
        self.progress_info=0
        self.abort_action=False
        self.started=False
        self.thread = Thread(target=self.calc,daemon=True)
        self.log.info('CRCThreadedCalc %s initialized',self)
        self.size_done = 0
        self.files_done = 0
        self.thread_is_alive = self.thread.is_alive

    def __del__(self):
        self.log.info("CRCThreadedCalc %s gets destroyed",self)

    def abort(self):
        self.abort_action=True

    def calc(self):
        CRC_BUFFER_SIZE=4*1024*1024
        buf = bytearray(CRC_BUFFER_SIZE)
        view = memoryview(buf)

        self.started=True

        #preallocate
        self.results=[None]*len(self.source)

        self_results=self.results

        self.size_done = 0
        self.files_done = 0

        for fullpath,size in self.source:
            try:
                file_handle=open(fullpath,'rb')
                file_handle_readinto=file_handle.readinto
            except Exception as e:
                self.log.error(e)

                if self.abort_action:
                    return
            else:
                hasher = sha1()
                hasher_update=hasher.update

                #faster for smaller files
                if size<CRC_BUFFER_SIZE:
                    hasher_update(view[:file_handle_readinto(buf)])
                else:
                    while rsize := file_handle_readinto(buf):
                        hasher_update(view[:rsize])

                        if rsize==CRC_BUFFER_SIZE:
                            #still reading
                            self.progress_info+=rsize

                        if self.abort_action:
                            break

                    self.progress_info=0

                file_handle.close()

                if self.abort_action:
                    return

                #only complete result
                self_results[self.files_done]=hasher.hexdigest()

            self.size_done += size
            self.files_done += 1

    def start(self):
        self.log.info('CRCThreadedCalc %s start',self)
        return self.thread.start()

    def join(self):
        self.log.info('CRCThreadedCalc %s join',self)
        self.thread.join()

class DudeCore:
    def handle_sigint(self):
        print("Received SIGINT signal")
        self.log.warning("Received SIGINT signal")
        self.abort()

    def reset(self):
        self.scan_results_by_size=defaultdict(set)
        self.files_of_size_of_crc=defaultdict(lambda : defaultdict(set))
        self.files_of_size_of_crc_items=self.files_of_size_of_crc.items
        self.devs=()
        self.crc_cut_len=40
        self.scanned_paths=[]
        self.exclude_list=[]

    def __init__(self,cache_dir,log_par):
        self.cache_dir=cache_dir
        self.log=log_par
        self.windows = bool(os_name=='nt')

        self.name_func = (lambda x : x.lower()) if self.windows else (lambda x : x)

        self.reset()

    def get_full_path_to_scan(self,pathnr,path,file_name):
        return path_join(self.paths_to_scan[pathnr]+path,file_name)

    def get_full_path_scanned(self,pathnr,path,file_name):
        return path_join(self.scanned_paths[pathnr]+path,file_name)

    def set_paths_to_scan(self,paths):
        paths_len=len(paths)

        if self.windows:
            paths=[path.replace('/',chr(92)) + (chr(92) if path[-1]==':' else '') for path in paths ]

        abspaths=[normpath(abspath(path)) for path in paths]

        for path in abspaths:
            if not path_exists(path) or not path_isdir(path):
                return  path + '\n\nnot a directory'

        abspaths_osnorm=[self.name_func(path) for path in abspaths]

        apaths=list(zip(paths,abspaths_osnorm))

        for p_index1 in range(paths_len):
            for p_index2 in range(paths_len):
                if p_index1!=p_index2:
                    orgpath1,osnorm_path1=apaths[p_index1]
                    orgpath2,osnorm_path2=apaths[p_index2]
                    if osnorm_path2==osnorm_path1:
                        return  orgpath2 + '\n\nis equal to:\n\n' +  orgpath1 + '\n'

                    if osnorm_path1.startswith(osnorm_path2.rstrip(sep) + sep):
                        return  'subpaths selected:\n\n' +  orgpath1 + '\n' + orgpath2

        self.paths_to_scan=abspaths
        return False

    reg_exp=False
    def set_exclude_masks(self,reg_exp,masks_list):
        self.reg_exp=reg_exp

        self.excl_fn = (lambda expr,string : search(expr,string)) if reg_exp else (lambda expr,string : fnmatch(string,expr))

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

    log_skipped = False

    scan_update_info_path_nr=None
    def scan(self):
        self.log.info('')
        self.log.info('SCANNING')
        self.log.info('paths to scan: %s',' '.join(self.paths_to_scan))
        self.log.info('exclude_reg_exp: %s',self.reg_exp)
        self.log.info('exclude_list: %s',' '.join(self.exclude_list))

        self.info_path_nr=0
        self.info_path_to_scan=''

        self.abort_action=False

        path_nr=0
        self.info_counter=0
        self.info_size_sum=0

        self_scan_results_by_size=self.scan_results_by_size

        self_scan_results_by_size.clear()

        self_log_skipped = self.log_skipped
        self_log_error=self.log.error

        self_exclude_list=self.exclude_list
        any_exclude_list = bool(self_exclude_list)
        self_excl_fn=self.excl_fn

        self.sum_size=0
        self.info_size_done_perc=0
        self.info_files_done_perc=0

        self_log_info=self.log.info
        skipping_action = lambda *args : self_log_info(*args) if self_log_skipped else None

        for path_to_scan in self.paths_to_scan:
            self.info_path_to_scan=path_to_scan
            self.info_path_nr=path_nr

            if self.scan_update_info_path_nr:
                self.scan_update_info_path_nr(path_nr)

            loop_list=[]
            loop_list_append=loop_list.append
            loop_list_append(path_to_scan)

            loop_list_pop=loop_list.pop

            while loop_list:
                path = loop_list_pop()
                self.info_line=path

                ##############################################
                try:
                    with scandir(path) as res:
                        folder_size=0
                        folder_counter=0

                        for entry in res:
                            if self.abort_action:
                                break

                            if entry.is_symlink() :
                                skipping_action('skippping link: %s / %s',path,entry.name)
                            else:
                                if any_exclude_list:
                                    fullpath=path_join(path,entry.name)
                                    if any({self_excl_fn(expr,fullpath) for expr in self_exclude_list}):
                                        skipping_action('skipping by Exclude Mask:%s',fullpath)
                                        continue

                                if entry.is_dir():
                                    loop_list_append(path_join(path,entry.name))
                                elif entry.is_file():
                                    try:
                                        stat_res = stat(entry)
                                    except Exception as e:
                                        skipping_action('scandir(stat):%s error:%s',entry.name,e )
                                    else:
                                        nlink = stat_res.st_nlink
                                        if nlink>1:
                                            skipping_action('scan skipp - hardlinks %s - %s,%s,%s',nlink,path_nr,path,entry.name)
                                        else:
                                            if size:=stat_res.st_size:
                                                folder_size+=size

                                                subpath=path.replace(path_to_scan,'')
                                                self_scan_results_by_size[size].add( (path_nr,subpath,entry.name,stat_res.st_mtime_ns,stat_res.st_ctime_ns,stat_res.st_dev,stat_res.st_ino) )

                                    folder_counter+=1
                                else:
                                    skipping_action('skipping another:%s',path)

                        self.info_size_sum+=folder_size
                        self.info_counter+=folder_counter

                except Exception as e:
                    skipping_action('scandir %s: error:%s',path,e)

                ##############################################

                if self.abort_action:
                    break

            path_nr+=1
            if self.abort_action:
                break

        if self.abort_action:
            self.reset()
            return False

        self.devs=tuple(list({dev for size,data in self_scan_results_by_size.items() for pathnr,path,file_name,mtime,ctime,dev,inode in data}))

        ######################################################################
        #inodes collision detection
        self.info='Inode collision detection'
        known_dev_inodes=defaultdict(int)
        for size,data in self_scan_results_by_size.items():
            for pathnr,path,file_name,mtime,ctime,dev,inode in data:
                index=(dev,inode)
                known_dev_inodes[index]+=1

        blacklisted_inodes = {index for index in known_dev_inodes if known_dev_inodes[index]>1}

        #self_scan_results_by_size = self.scan_results_by_size
        for size in list(self_scan_results_by_size):
            for pathnr,path,file_name,mtime,ctime,dev,inode in list(self_scan_results_by_size[size]):
                index=(dev,inode)
                if index in blacklisted_inodes:
                    this_index=(pathnr,path,file_name,mtime,ctime,dev,inode)
                    self.log.warning('ignoring conflicting inode entry: %s',this_index)
                    self_scan_results_by_size[size].remove(this_index)

        ######################################################################
        sum_size = 0
        for size in list(self_scan_results_by_size):
            quant=len(self_scan_results_by_size[size])
            if quant==1 :
                del self_scan_results_by_size[size]
            else:
                sum_size += quant*size

        self.sum_size = sum_size
        ######################################################################
        return True

    def crc_cache_read(self):
        self.info='Reading cache ...'
        self.crc_cache={}
        self_crc_cache=self.crc_cache
        for dev in self.devs:
            self_crc_cache_int_dev = self_crc_cache[dev]={}
            try:
                self.log.info('reading cache:%s:device:%s',self.cache_dir,dev)
                with open(sep.join([self.cache_dir,str(dev)]),'r',encoding='ASCII' ) as cfile:
                    while line:=cfile.readline() :
                        inode,mtime,crc = line.rstrip('\n').split(' ')
                        if crc is None or crc=='None' or crc=='':
                            self.log.warning("crc_cache read error:%s,%s,%s",inode,mtime,crc)
                        else:
                            self_crc_cache_int_dev[(int(inode),int(mtime))]=crc
            except Exception as e:
                self.log.warning(e)
                self_crc_cache[dev]={}
        self.info=''

    def crc_cache_write(self):
        self.info='Writing cache ...'

        Path(self.cache_dir).mkdir(parents=True,exist_ok=True)
        for (dev,val_dict) in self.crc_cache.items():

            self.log.info('writing cache:%s:device:%s',self.cache_dir,dev)
            with open(sep.join([self.cache_dir,str(dev)]),'w',encoding='ASCII') as cfile:
                for (inode,mtime),crc in sorted(val_dict.items()):
                    cfile.write(' '.join([str(x) for x in [inode,mtime,crc] ]) +'\n' )

        del self.crc_cache
        self.info=''

    info_size_done=0
    info_files_done=0

    info_total=1

    info_speed=0
    info_threads='?'

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

        self_scan_results_by_size = self.scan_results_by_size

        self.info_total = len([ 1 for size in self_scan_results_by_size for pathnr,path,file_name,mtime,ctime,dev,inode in self_scan_results_by_size[size] ])

        start = time()

        crc_core={}
        self.log.info('creating crc cores')
        for dev in self.devs:
            self.log.info('...%s',dev)
            crc_core[dev]=CRCThreadedCalc(self.log)

        scan_results_sizes = list(self_scan_results_by_size)

        #########################################################################################################

        scan_results_sizes.sort(reverse=True)
        #########################################################################################################

        self.info="Preparing optimal calculation order ..."
        folders_by_biggest_files_in_order=[]
        folders_by_biggest_files_in_order_append = folders_by_biggest_files_in_order.append
        folders_by_biggest_files_in_order_set=set()
        folders_by_biggest_files_in_order_set_add = folders_by_biggest_files_in_order_set.add
        folder_to_sizes=defaultdict(set)

        for size in scan_results_sizes:
            for pathnr,path,_,_,_,_,_ in self_scan_results_by_size[size]:
                index = (pathnr,path)
                folder_to_sizes[index].add(size)
                if index not in folders_by_biggest_files_in_order_set:
                    folders_by_biggest_files_in_order_append(index)
                    folders_by_biggest_files_in_order_set_add(index)

        folders_by_biggest_files_in_order_set.clear()

        best_sizes=[]
        best_sizes_append = best_sizes.append
        best_sizes_set=set()
        best_sizes_set_add = best_sizes_set.add

        for index in folders_by_biggest_files_in_order:
            for size in sorted(folder_to_sizes[index],reverse=True):
                if size not in best_sizes_set:
                    best_sizes_append(size)
                    best_sizes_set_add(size)

        best_sizes_set.clear()
        folder_to_sizes.clear()

        #########################################################################################################

        self.info="Initializing data structures ..."
        #strange initialization affecting tree order and cleaning time ....
        for size in scan_results_sizes:
            self.files_of_size_of_crc[size]=defaultdict(set)

        sto_by_self_sum_size = 100.0/self.sum_size
        sto_by_self_info_total = 100.0/self.info_total

        #########################################################################################################

        self.info="Using cached CRC data ..."
        self.log.info('using cache')

        for size in best_sizes:
            if self.abort_action:
                break

            for pathnr,path,file_name,mtime,ctime,dev,inode in self_scan_results_by_size[size]:
                if self.abort_action:
                    break

                self_crc_cache_dev=self.crc_cache[dev]

                cache_key=(inode,mtime)
                self_files_of_size_of_crc_size=self.files_of_size_of_crc[size]
                if cache_key in self_crc_cache_dev:
                    if crc:=self_crc_cache_dev[cache_key]:
                        self.info_size_done+=size
                        self.info_files_done+=1

                        index_tuple=(pathnr,path,file_name,ctime,dev,inode)
                        self_files_of_size_of_crc_size[crc].add( index_tuple )

                        self.info_size_done_perc = sto_by_self_sum_size*self.info_size_done
                        self.info_files_done_perc = sto_by_self_info_total*self.info_files_done

                        continue

                fullpath=self.get_full_path_to_scan(pathnr,path,file_name)

                crc_core[dev].source.append( (fullpath,size) )
                crc_core[dev].source_other_data.append( (pathnr,path,file_name,mtime,ctime,inode) )

        self.info=''
        self.log.info('using cache done.')
        #########################################################################################################
        self_scan_results_by_size.clear()

        size_done_cached = self.info_size_done
        files_done_cached = self.info_files_done

        measures_pool=[]

        last_time_info_update=0
        last_time_results_check = 0
        last_time_threads_check = 0

        prev_line_info={}
        prev_line_show_same_max={}

        for dev in self.devs:
            prev_line_info[dev]=''
            prev_line_show_same_max[dev]=0

        thread_pool_need_checking=True
        alive_threads=0

        max_threads = cpu_count()
        self_devs=self.devs

        self_files_of_size_of_crc = self.files_of_size_of_crc
        self_files_of_size_of_crc_items = self.files_of_size_of_crc_items

        while True:
            ########################################################################
            #propagate abort
            if self.abort_action:
                for dev in self_devs:
                    if crc_core[dev].thread_is_alive():
                        crc_core[dev].abort()

            # threads starting/finishing
            alive_threads=len({dev for dev in self_devs if crc_core[dev].thread_is_alive()})

            no_thread_started=True
            if thread_pool_need_checking:
                if alive_threads<max_threads:
                    for dev in self_devs:
                        crc_core_dev = crc_core[dev]
                        if not crc_core_dev.started and not crc_core_dev.thread_is_alive():
                            crc_core_dev.start()
                            no_thread_started=False
                            break

                all_started=True
                for dev in self_devs:
                    if not crc_core[dev].started:
                        all_started=False
                        break
                if all_started:
                    thread_pool_need_checking=False

            ########################################################################
            # info
            now=time()
            if not self.abort_action and now-last_time_info_update>0.15:
                last_time_info_update=now

                #######################################################
                #sums info
                self.info_size_done = size_done_cached + sum([crc_core[dev].size_done + crc_core[dev].progress_info for dev in self_devs])
                self.info_size_done_perc = sto_by_self_sum_size*self.info_size_done

                self.info_files_done = files_done_cached + sum([crc_core[dev].files_done for dev in self_devs])
                self.info_files_done_perc = sto_by_self_info_total*self.info_files_done

                if now-last_time_results_check>2:
                    last_time_results_check=now

                    crc_to_combo=defaultdict(set)

                    for dev in self_devs:
                        for (fullpath,size),crc in zip(crc_core[dev].source,crc_core[dev].results):
                            if crc:
                                crc_to_combo[crc].add( (size,dirname(fullpath)) )

                    for size,size_dict in self_files_of_size_of_crc_items():
                        for crc,crc_dict in size_dict.items():
                            for pathnr,path,file_name,_,_,_ in crc_dict:
                                dirpath =self.paths_to_scan[pathnr]+path
                                crc_to_combo[crc].add( (size,dirpath) )

                    temp_info_groups=0
                    temp_info_dupe_space=0
                    temp_info_folders_set=set()

                    for crc,crc_combo in crc_to_combo.items():
                        len_crc_combo = len(crc_combo)
                        if len_crc_combo>1:
                            temp_info_groups+=1
                            for size,dirpath in crc_combo:
                                temp_info_dupe_space+=size
                                temp_info_folders_set.add(dirpath)

                    self.info_found_groups=temp_info_groups
                    self.info_found_dupe_space=temp_info_dupe_space
                    self.info_found_folders=len(temp_info_folders_set)
                    temp_info_folders_set.clear()

            elif alive_threads==0 and no_thread_started:
                break
            else:
                sleep(0.02)

        self.can_abort=False
        ########################################################################
        self.info='Merging data ...'
        self.log.info('merging data')

        for dev in self_devs:
            crc_core_dev = crc_core[dev]
            if crc_core_dev.started:
                crc_core_dev.join()

            for (fullpath,size),(pathnr,path,file_name,mtime,ctime,inode),crc in zip(crc_core_dev.source,crc_core_dev.source_other_data,crc_core_dev.results):
                if crc:
                    index_tuple=(pathnr,path,file_name,ctime,dev,inode)

                    self_files_of_size_of_crc[size][crc].add( index_tuple )

                    cache_key=(inode,mtime)
                    self.crc_cache[dev][cache_key]=crc
        del crc_core
        ########################################################################

        self.info='Pruning data ...'
        self.log.info('pruning data')

        self_check_crc_pool_and_prune = self.check_crc_pool_and_prune
        for size in scan_results_sizes:
            self_check_crc_pool_and_prune(size)

        self.crc_cache_write()

        end=time()
        self.log.info('total time = %s',end-start)

        self.calc_crc_min_len()

    def check_group_files_state(self,size,crc):
        self.log.info('check_group_files_state: %s %s',size,crc)

        self_get_full_path_to_scan = self.get_full_path_to_scan
        res_problems=[]
        res_problems_append = res_problems.append
        to_remove=[]
        to_remove_append = to_remove.append

        if self.files_of_size_of_crc[size][crc]:
            for pathnr,path,file_name,ctime,dev,inode in self.files_of_size_of_crc[size][crc]:
                full_path=self_get_full_path_to_scan(pathnr,path,file_name)

                problem=False
                try:
                    stat_res = stat(full_path)
                except Exception as e:
                    self.log.error('check_group_files_state: %s',e)
                    res_problems_append('%s|RED' % e)
                    problem=True
                else:
                    if stat_res.st_nlink>1:
                        res_problems_append('file became hardlink:%s - %s,%s,%s' % (stat_res.st_nlink,pathnr,path,file_name) )
                        problem=True
                    else:
                        if (size,ctime,dev,inode) != (stat_res.st_size,stat_res.st_ctime_ns,stat_res.st_dev,stat_res.st_ino):
                            res_problems_append('file changed:%s,%s,%s,%s vs %s,%s,%s,%s' % (size,ctime,dev,inode,stat_res.st_size,stat_res.st_ctime_ns,stat_res.st_dev,stat_res.st_ino) )
                            problem=True
                if problem:
                    index_tuple=(pathnr,path,file_name,ctime,dev,inode)
                    to_remove_append(index_tuple)
        else :
            res_problems_append('no data')

        return (res_problems,to_remove)

    def write_csv(self,file_name):
        self.log.info('writing csv file: %s',file_name)

        with open(file_name,'w') as csv_file:
            csv_file_write = csv_file.write
            csv_file_write('#size,crc,filepath\n#no checking if the path contains a comma\n')
            for size,crc_dict in self.files_of_size_of_crc_items():
                for crc,index_tuple_list in crc_dict.items():
                    csv_file_write('%s,%s,\n' % (size,crc) )
                    for index_tuple in sorted(index_tuple_list,key= lambda x : x[5]):
                        (pathnr,path,file_name,ctime,dev,inode)=index_tuple
                        full_path = self.scanned_paths[pathnr]+path

                        csv_file_write(',,%s\n' % full_path )
            self.log.info('#######################################################')

    def check_crc_pool_and_prune(self,size):
        if size in self.files_of_size_of_crc:
            for crc in list(self.files_of_size_of_crc[size]):
                if len(self.files_of_size_of_crc[size][crc])<2 :
                    del self.files_of_size_of_crc[size][crc]

            if len(self.files_of_size_of_crc[size])==0 :
                del self.files_of_size_of_crc[size]

    def calc_crc_min_len(self):
        self.info='CRC min length calculation ...'
        all_crcs_len=len(all_crcs:={crc for size,size_dict in self.files_of_size_of_crc_items() for crc in size_dict})

        len_temp=4
        while len({crc[0:len_temp] for crc in all_crcs})!=all_crcs_len:
            self.info='CRC min length calculation ... (%s)' % len_temp
            len_temp+=1

        self.crc_cut_len=len_temp
        self.info=''

    def rename_file(self,src,dest,l_info):
        l_info('renaming file:%s->%s',src,dest)
        try:
            os_rename(src,dest)
            return False
        except Exception as e:
            self.log.error(e)
            return 'Rename error:' + str(e)

    def delete_file(self,file_name,l_info):
        l_info('deleting file:%s',file_name)
        try:
            os_remove(file_name)
            return False
        except Exception as e:
            self.log.error(e)
            return 'Delete error:' + str(e)

    def delete_file_to_trash(self,file_name,l_info):
        l_info('deleting file to trash:%s',file_name)
        try:
            send2trash(file_name)
            return False
        except Exception as e:
            self.log.error(e)
            return 'Delete error:' + str(e)

    def do_soft_link(self,src,dest,relative,l_info):
        l_info('soft-linking %s<-%s (relative:%s)',src,dest,relative)
        try:
            if relative:
                dest_dir = dirname(dest)
                src_rel = relpath(src, dest_dir)
                symlink(normpath(src_rel),normpath(dest))
            else:
                symlink(src,dest)
            return False
        except Exception as e:
            self.log.error(e)
            return 'Error on soft linking:%s' % e

    def do_hard_link(self,src,dest,l_info):
        l_info('hard-linking %s<-%s',src,dest)
        try:
            link(normpath(src),normpath(dest))
            return False
        except Exception as e:
            self.log.error(e)
            return 'Error on hard linking:%s' % e

    def remove_from_data_pool(self,size,crc,index_tuple_list):
        self.log.info('remove_from_data_pool size:%s crc:%s tuples:%s',size,crc,index_tuple_list)

        if size in self.files_of_size_of_crc:
            if crc in self.files_of_size_of_crc[size]:
                for index_tuple in index_tuple_list:
                    try:
                        self.files_of_size_of_crc[size][crc].remove(index_tuple)
                    except Exception as e:
                        self.log.error('  %s',e)
                        self.log.error('  index_tuple: %s',index_tuple)
                        self.log.error('  self.files_of_size_of_crc[%s][%s]:%s',size,crc,self.files_of_size_of_crc[size][crc])
            else:
                self.log.warning('remove_from_data_pool - crc already removed')

            self.check_crc_pool_and_prune(size)
        else:
            self.log.warning('remove_from_data_pool - size already removed')

    def delete_file_wrapper(self,size,crc,index_tuple_set,to_trash=False):
        messages=set()
        messages_add = messages.add

        index_tuples_list_done=[]
        l_info = self.log.info
        self_get_full_path_scanned = self.get_full_path_scanned
        self_files_of_size_of_crc_size_crc = self.files_of_size_of_crc[size][crc]

        index_tuples_list_done_append = index_tuples_list_done.append

        delete_command = self.delete_file_to_trash if to_trash else self.delete_file

        for index_tuple in index_tuple_set:
            (pathnr,path,file_name,ctime,dev,inode)=index_tuple
            full_file_path=self_get_full_path_scanned(pathnr,path,file_name)

            if index_tuple in self_files_of_size_of_crc_size_crc:

                if message:=delete_command(full_file_path,l_info):
                    messages_add(message)
                else:
                    index_tuples_list_done_append(index_tuple)
            else:
                messages_add('delete_file_wrapper - Internal Data Inconsistency:%s / %s' % (full_file_path,str(index_tuple)) )

        self.remove_from_data_pool(size,crc,index_tuples_list_done)

        return messages

    def link_wrapper(self,\
            soft,relative,size,crc,\
            index_tuple_ref,index_tuple_list):
        l_info = self.log.info

        l_info('link_wrapper:%s,%s,%s,%s,%s,%s',soft,relative,size,crc,index_tuple_ref,index_tuple_list)

        (path_nr_keep,path_keep,file_keep,ctime_keep,dev_keep,inode_keep)=index_tuple_ref

        self_get_full_path_scanned = self.get_full_path_scanned
        self_files_of_size_of_crc_size_crc = self.files_of_size_of_crc[size][crc]

        self_rename_file = self.rename_file
        self_delete_file = self.delete_file

        full_file_path_keep=self_get_full_path_scanned(path_nr_keep,path_keep,file_keep)

        link_command = (lambda p : self.do_soft_link(full_file_path_keep,p,relative,l_info)) if soft else (lambda p : self.do_hard_link(full_file_path_keep,p,l_info))

        if index_tuple_ref not in self_files_of_size_of_crc_size_crc:
            return 'link_wrapper - Internal Data Inconsistency:%s / %s' % (full_file_path_keep,index_tuple_ref)

        res=[]
        tuples_to_remove = set()
        for index_tuple in index_tuple_list:
            (pathnr,path,file_name,ctime,dev,inode)=index_tuple
            full_file_path=self_get_full_path_scanned(pathnr,path,file_name)

            if index_tuple not in self_files_of_size_of_crc_size_crc:
                res.append('link_wrapper - Internal Data Inconsistency:%s / %s' % (full_file_path,index_tuple))
                break

            temp_file='%s.temp' % full_file_path

            rename_file_res1 = self_rename_file(full_file_path,temp_file,l_info)

            if rename_file_res1:
                res.append(rename_file_res1)
                break
            else:
                if linking_problem:=link_command(full_file_path):
                    rename_file_back_res = self_rename_file(temp_file,full_file_path,l_info)
                    res.append(("%s\n%s" % (linking_problem,rename_file_back_res)) if rename_file_back_res else ("%s" % linking_problem))
                    break

                if message:=self_delete_file(temp_file,l_info):
                    self.log.error(message)
                    res.append(message)
                    break

                tuples_to_remove.add(index_tuple)

                if not soft:
                    tuples_to_remove.add(index_tuple_ref)

        self.remove_from_data_pool(size,crc,tuples_to_remove)

        l_info('link_wrapper done')

        if res:
            return '\n'.join(res)
        else:
            return ''

############################################################################################
if __name__ == "__main__":
    import logging

    import test

    LOG_DIR = "./test/log"
    Path(LOG_DIR).mkdir(parents=True,exist_ok=True)

    log=LOG_DIR + sep + strftime('%Y_%m_%d_%H_%M_%S',localtime(time()) ) +'.log'

    print('log:',log)
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s', filename=log,filemode='w')

    print('dude core test ...')
    core=DudeCore('./test/cache',logging)

    TEST_DIR='test/files'
    if not path_exists(TEST_DIR):
        test.generate(TEST_DIR)

    core.set_paths_to_scan([TEST_DIR])
    core.set_exclude_masks(False,[])

    scan_thread=Thread(target=core.scan,daemon=True)
    scan_thread.start()

    while scan_thread.is_alive():
        print('Scanning ...', core.info_counter,end='\r')
        sleep(0.04)

    scan_thread.join()

    if core.sum_size:
        scan_thread=Thread(target=core.crc_calc,daemon=True)
        scan_thread.start()

        while scan_thread.is_alive():
            print(f'crc_calc...{core.info_files_done}/{core.info_total}                 ',end='\r')
            sleep(0.04)

        scan_thread.join()

    print('')
    print('Done')
