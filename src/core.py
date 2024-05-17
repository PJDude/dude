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

from time import sleep,strftime,localtime,time
from hashlib import sha1

from os import stat,scandir,sep,symlink,link,cpu_count,name as os_name,rename as os_rename,remove as os_remove

from os.path import dirname,relpath,normpath,join as path_join,abspath as abspath,exists as path_exists,isdir as path_isdir

from subprocess import run as subprocess_run

if os_name=='nt':
    from subprocess import CREATE_NO_WINDOW

from sys import exit as sys_exit
from pickle import dumps,loads
from zstandard import ZstdCompressor,ZstdDecompressor

from send2trash import send2trash

#from PIL import Image
from PIL.Image import open as image_open,new as image_new, alpha_composite as image_alpha_composite
from imagehash import average_hash,phash,dhash,whash,colorhash,hex_to_hash

from sklearn.cluster import DBSCAN,MiniBatchKMeans
from numpy import array as numpy_array

DELETE=0
SOFTLINK=1
HARDLINK=2
WIN_LNK=3

def localtime_catched(t):
    try:
        #mtime sometimes happens to be negative (Virtual box ?)
        return localtime(t)
    except:
        return localtime(0)

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

def fnumber(num):
    return str(format(num,',d').replace(',',' '))

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

        self.files_of_images_groups=defaultdict(set)

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
    similarity_mode = False

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
        self_similarity_mode = self.similarity_mode

        self_scan_results_images = self.scan_results_images = set()
        #############################################################################################
        if self_similarity_mode:
            self_log_skipped = self.log_skipped

            self_exclude_list=self.exclude_list
            any_exclude_list = bool(self_exclude_list)
            self_excl_fn=self.excl_fn

            self.sum_size=0
            self.info_size_done_perc=0
            self.info_files_done_perc=0

            self_log_info=self.log.info
            skipping_action = lambda *args : self_log_info(*args) if self_log_skipped else None

            self_scan_results_images_add = self_scan_results_images.add

            sum_size = 0
            for path_to_scan in self.paths_to_scan:
                self.info_path_to_scan=path_to_scan
                self.info_path_nr=path_nr

                if self.scan_update_info_path_nr:
                    self.scan_update_info_path_nr()

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
                                                entry.name
                                                extension = Path(entry).suffix
                                                #print('extension:',extension,entry.name)

                                                if size:=stat_res.st_size:
                                                    folder_size+=size
                                                    if extension.lower() in ('.jpeg','.jpg','.png'):
                                                        sum_size+=size
                                                        subpath=path.replace(path_to_scan,'')
                                                        self_scan_results_images_add( (path_nr,subpath,entry.name,stat_res.st_mtime_ns,stat_res.st_ctime_ns,stat_res.st_dev,stat_res.st_ino,size) )

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

            #print(f'{self_scan_results_images=}')
            self.sum_size = sum_size

            self.devs=tuple(list({dev for pathnr,path,file_name,mtime,ctime,dev,inode,size in self_scan_results_images}))

            return True
            #############################################################################################
        else:
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
                    self.scan_update_info_path_nr()

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

            self.log.info('reading cache:%s:device:%s',self.cache_dir,dev)
            try:
                with open(sep.join([self.cache_dir,f'{dev}.dat']), "rb") as dat_file:
                    self.crc_cache[dev] = loads(ZstdDecompressor().decompress(dat_file.read()))
            except Exception as e1:
                self.log.warning(e1)
            else:
                self.log.info(f'cache loaded for dev: {dev}')
        self.info=''

    def crc_cache_write(self):
        self.info='Writing cache ...'

        Path(self.cache_dir).mkdir(parents=True,exist_ok=True)

        for (dev,val_dict) in self.crc_cache.items():
            try:
                self.log.info(f'writing cache for dev: {dev}')
                with open(sep.join([self.cache_dir,f'{dev}.dat']), "wb") as dat_file:
                    dat_file.write(ZstdCompressor(level=9,threads=-1).compress(dumps(val_dict)))
                    self.log.info(f'writing cache for dev: {dev} done.')
            except Exception as e:
                self.log.error(f'writing cache for dev: {dev} error: {e}.')

        del self.crc_cache

        self.info=''

    info_size_done=0
    info_files_done=0

    info_total=1

    info_speed=0
    info_threads='?'

    def images_hashes_cache_read(self):
        self.info='image hashes cache read'

        self.images_hashes_cache = {}

        self.log.info('reading image hashes cache')
        try:
            with open(sep.join([self.cache_dir,'ihashes.dat']), "rb") as dat_file:
                self.images_hashes_cache = loads(ZstdDecompressor().decompress(dat_file.read()))
                #print('ddddd:',self.images_hashes_cache)
        except Exception as e1:
            self.log.warning(e1)
        else:
            self.log.info(f'image hashes cache loaded.')
        self.info=''

    def images_hashes_cache_write(self):
        self.info='Writing ih cache ...'

        Path(self.cache_dir).mkdir(parents=True,exist_ok=True)

        self.log.info(f'writing images hashes cache')
        try:
            with open(sep.join([self.cache_dir,'ihashes.dat']), "wb") as dat_file:
                dat_file.write(ZstdCompressor(level=9,threads=-1).compress(dumps(self.images_hashes_cache)))
                self.log.info('writing images hashes cache')
        except Exception as e:
            self.log.error(f'writing images hashes cache error: {e}.')

        del self.images_hashes_cache

        self.info=''

    def imagehsh_calc_in_thread(self,i,hash_size,all_rotations,source_dict,result_dict):
        def my_hash_combo(file,hash_size):
            seq_hash = []
            seq_hash_extend = seq_hash.extend

            for hash_row in average_hash(file,hash_size).hash:
                seq_hash_extend(hash_row)

                for hash_row in phash(file,hash_size).hash:
                    seq_hash_extend(hash_row)

                for hash_row in dhash(file,hash_size).hash:
                    seq_hash_extend(hash_row)

                #colorhash(file).hash.tolist()

            return tuple(seq_hash)

        for index_tuple,fullpath in sorted(source_dict.items(), key = lambda x : x[0][7], reverse=True):
            if self.abort_action:
                break

            try:
                file = image_open(fullpath)
                if file.mode == 'RGBA':
                    file = image_alpha_composite(image_new('RGBA', file.size, (255,255,255)), file)

            except Exception as e:
                self.log.error(f'opening file: {fullpath} error: {e}.')
                continue

            if all_rotations:
                file_rotate = file.rotate
                try:
                    result_dict[index_tuple]=( my_hash_combo(file,hash_size),my_hash_combo(file_rotate(90),hash_size),my_hash_combo(file_rotate(180),hash_size),my_hash_combo(file_rotate(270),hash_size) )

                except Exception as e:
                    self.log.error(f'hashing file: {fullpath} error: {e}.')
                    continue
            else:
                try:
                    result_dict[index_tuple]=(my_hash_combo(file,hash_size),None,None,None)

                except Exception as e:
                    self.log.error(f'hashing file: {fullpath} error: {e}.')
                    continue

        sys_exit() #thread

    info=''
    def image_hashing(self,hash_size,all_rotations):
        self.images_hashes_cache_read()
        self.scanned_paths=self.paths_to_scan.copy()

        self.info_size_done=0
        self.info_files_done=0

        self.abort_action=False
        self.can_abort=True

        self.info = 'Cache reading'
        self.info_line = 'Cache reading ...'

        anything_new=False

        self.scan_results_images_hashes={}

        max_threads = cpu_count()

        imagehash_threads_sets_source = {i:{} for i in range(max_threads)}
        imagehash_threads_sets_results = {i:{} for i in range(max_threads)}
        imagehash_threads = {i:Thread(target=lambda iloc=i: self.imagehsh_calc_in_thread(iloc,hash_size,all_rotations,imagehash_threads_sets_source[iloc],imagehash_threads_sets_results[iloc]),daemon=True) for i in range(max_threads)}

        thread_index=0

        images_quantity_cache_read=0
        images_quantity_need_to_calculate=0

        size_from_cache = 0
        size_to_calculate = 0

        rotations_list = (0,1,2,3) if all_rotations else (0,)
        for pathnr,path,file_name,mtime,ctime,dev,inode,size in sorted(self.scan_results_images, key = lambda x : x[7], reverse=True):
            all_rotations_from_cache = True
            for rotation in rotations_list:
                dict_key = (dev,inode,mtime,hash_size,rotation)
                if dict_key in self.images_hashes_cache:
                    if val := self.images_hashes_cache[dict_key]:
                        self.scan_results_images_hashes[(pathnr,path,file_name,mtime,ctime,dev,inode,size,rotation)] = val
                else:
                    all_rotations_from_cache = False
                    break

            if all_rotations_from_cache:
                images_quantity_cache_read+=1
                size_from_cache += size
            else:
                fullpath=self.get_full_path_to_scan(pathnr,path,file_name)

                imagehash_threads_sets_source[thread_index][(pathnr,path,file_name,mtime,ctime,dev,inode,size)]=fullpath

                thread_index = (thread_index+1) % max_threads

                images_quantity_need_to_calculate += 1
                size_to_calculate += size

        #self.images_quantity_need_to_calculate = images_quantity_need_to_calculate
        #self.images_quantity_cache_read = images_quantity_cache_read

        self.info_total = images_quantity_cache_read + images_quantity_need_to_calculate
        self.sum_size = size_from_cache + size_to_calculate

        print(f'{images_quantity_need_to_calculate=}')
        print(f'{images_quantity_cache_read=}')

        self.info = self.info_line = 'Images hashing ...'

        for i in range(max_threads):
            imagehash_threads[i].start()

        self.info_size_done=0
        self.info_files_done=0

        self.info_size_done_perc = 0
        self.info_files_done_perc = 0

        sto_by_self_info_total = 100.0/self.info_total
        sto_by_self_sum_size = 100.0/self.sum_size

        #self.info = f'Threads:{max_threads}'

        while True:
            all_dead=True
            for i in range(max_threads):
                if imagehash_threads[i].is_alive():
                    all_dead=False

            if all_dead:
                break
            else:
                self.info_size_done = size_from_cache + sum([size for pathnr,path,file_name,mtime,ctime,dev,inode,size in imagehash_threads_sets_results[i] for i in range(max_threads)])
                self.info_files_done = images_quantity_cache_read + sum([len(imagehash_threads_sets_results[i]) for i in range(max_threads)])

                self.info_size_done_perc = sto_by_self_sum_size*self.info_size_done
                self.info_files_done_perc = sto_by_self_info_total*self.info_files_done
                sleep(0.02)

        for i in range(max_threads):
            imagehash_threads[i].join()

        self.info = self.info_line = 'Data merging ...'
        for i in range(max_threads):
            for (pathnr,path,file_name,mtime,ctime,dev,inode,size),ihash_rotations in imagehash_threads_sets_results[i].items():
                for rotation,ihash in enumerate(ihash_rotations):
                    if (rotation in rotations_list) and ihash:
                        self.scan_results_images_hashes[(pathnr,path,file_name,mtime,ctime,dev,inode,size,rotation)]=numpy_array(ihash)
                        self.images_hashes_cache[(dev,inode,mtime,hash_size,rotation)]=ihash

                        anything_new=True

        if anything_new:
            self.info = self.info_line = 'Writing cache ...'
            self.images_hashes_cache_write()

        sys_exit() #thread

    def similarity_clustering(self,hash_size,distance,all_rotations):
        pool = []
        keys = []

        self.info_line = self.info = 'Preparing data pool ...'

        for key,imagehash in sorted(self.scan_results_images_hashes.items(), key=lambda x :x[0][7],reverse = True) :
            pool.append(imagehash)
            keys.append( key )

        de_norm_distance = distance*hash_size*0.33*0.25+0.001

        self.info_line = self.info = 'Clustering ...'

        model = DBSCAN(eps=de_norm_distance, min_samples=2,n_jobs=-1)
        fit = model.fit(pool)

        labels = fit.labels_

        unique_labels = set(labels)
        groups = defaultdict(set)

        self.info_line = self.info = 'Separating groups ...'

        for label,key in zip(labels,keys):
            if label!=-1:
                groups[label].add(key)

        self_files_of_images_groups = self.files_of_images_groups = defaultdict(set)

        for label,lab_keys in groups.items():
            self_files_of_images_groups_str_label_add = self_files_of_images_groups[str(label)].add
            for key in lab_keys:
                self_files_of_images_groups_str_label_add(key)

        del model

        sys_exit() #thread

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
                    self.log.error(f'check_group_files_state:{e}')
                    res_problems_append('%s|RED' % e)
                    problem=True
                else:
                    if stat_res.st_nlink>1:
                        res_problems_append(f'file became hardlink:{stat_res.st_nlink},{pathnr},{path},{file_name}')
                        problem=True
                    else:
                        if (size,ctime,dev,inode) != (stat_res.st_size,stat_res.st_ctime_ns,stat_res.st_dev,stat_res.st_ino):
                            res_problems_append(f'file changed:{size},{ctime},{dev},{inode},{stat_res.st_size},{stat_res.st_ctime_ns},{stat_res.st_dev},{stat_res.st_ino}' )
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

    def check_crc_pool_and_prune(self,size,crc_callback=None):
        if size in self.files_of_size_of_crc:
            for crc in list(self.files_of_size_of_crc[size]):
                if len(self.files_of_size_of_crc[size][crc])<2 :
                    del self.files_of_size_of_crc[size][crc]
                    if crc_callback:
                        crc_callback(size,crc)

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
        l_info(f'deleting file:{file_name}')
        try:
            os_remove(file_name)
            return False
        except Exception as e:
            self.log.error(e)
            return f'Deletion error:{e}'

    def delete_file_to_trash(self,file_name,l_info):
        l_info(f'deleting file to trash:{file_name}')
        try:
            send2trash(file_name)
            return False
        except Exception as e:
            self.log.error(e)
            return f'send2trash error:{e}'

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

    def do_win_lnk_link(self,src,dest,l_info):
        l_info('win-lnk-linking %s<-%s',src,dest)
        try:
            powershell_cmd = f'$ol=(New-Object -ComObject WScript.Shell).CreateShortcut("{dest}")\n\r$ol.TargetPath="{src}"\n\r$ol.Save()'
            l_info(f'{powershell_cmd=}')

            res = subprocess_run(["powershell", "-Command", powershell_cmd], capture_output=True,creationflags=CREATE_NO_WINDOW)

            if res.returncode != 0:
                return f"Error on win lnk code: {res.returncode} error: {res.stderr}"

        except Exception as e:
            self.log.error(e)
            return 'Error on win lnk linking:%s' % e

    def do_hard_link(self,src,dest,l_info):
        l_info('hard-linking %s<-%s',src,dest)
        try:
            link(normpath(src),normpath(dest))
            return False
        except Exception as e:
            self.log.error(e)
            return 'Error on hard linking:%s' % e

    def remove_from_data_pool(self,size,crc,index_tuple_list,file_callback=None,crc_callback=None):
        self.log.info('remove_from_data_pool size:%s crc:%s tuples:%s',size,crc,index_tuple_list)

        if size in self.files_of_size_of_crc:
            if crc in self.files_of_size_of_crc[size]:
                for index_tuple in index_tuple_list:
                    try:
                        self.files_of_size_of_crc[size][crc].remove(index_tuple)
                        if file_callback(size,crc,index_tuple):
                            file_callback()
                    except Exception as e:
                        self.log.error('  %s',e)
                        self.log.error('  index_tuple: %s',index_tuple)
                        self.log.error('  self.files_of_size_of_crc[%s][%s]:%s',size,crc,self.files_of_size_of_crc[size][crc])
            else:
                self.log.warning('remove_from_data_pool - crc already removed')

            self.check_crc_pool_and_prune(size,crc_callback)
        else:
            self.log.warning('remove_from_data_pool - size already removed')

    def delete_file_wrapper(self,size,crc,index_tuple_set,to_trash,file_callback=None,crc_callback=None):
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

        self.remove_from_data_pool(size,crc,index_tuples_list_done,file_callback,crc_callback)

        return messages

    def link_wrapper(self,\
            kind,relative,size,crc,\
            index_tuple_ref,index_tuple_list,to_trash,file_callback=None,crc_callback=None):

        l_info = self.log.info
        delete_command = self.delete_file_to_trash if to_trash else self.delete_file

        l_info('link_wrapper:%s,%s,%s,%s,%s,%s',kind,relative,size,crc,index_tuple_ref,index_tuple_list)

        (path_nr_keep,path_keep,file_keep,ctime_keep,dev_keep,inode_keep)=index_tuple_ref

        self_get_full_path_scanned = self.get_full_path_scanned
        self_files_of_size_of_crc_size_crc = self.files_of_size_of_crc[size][crc]

        self_rename_file = self.rename_file

        full_file_path_keep=self_get_full_path_scanned(path_nr_keep,path_keep,file_keep)

        link_command = (lambda p : self.do_soft_link(full_file_path_keep,p,relative,l_info)) if kind==SOFTLINK else (lambda p : self.do_win_lnk_link(full_file_path_keep,str(p) + ".lnk",l_info)) if kind==WIN_LNK else (lambda p : self.do_hard_link(full_file_path_keep,p,l_info))

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

            temp_file='%s.dude_pre_delete_temp' % full_file_path

            rename_file_res1 = self_rename_file(full_file_path,temp_file,l_info)

            if rename_file_res1:
                res.append(rename_file_res1)
                break
            else:
                if linking_problem:=link_command(full_file_path):
                    rename_file_back_res = self_rename_file(temp_file,full_file_path,l_info)
                    res.append(("%s\n%s" % (linking_problem,rename_file_back_res)) if rename_file_back_res else ("%s" % linking_problem))
                    break

                if message:=delete_command(temp_file,l_info):
                    self.log.error(message)
                    res.append(message)
                    break

                tuples_to_remove.add(index_tuple)

                if kind==HARDLINK:
                    tuples_to_remove.add(index_tuple_ref)

        self.remove_from_data_pool(size,crc,tuples_to_remove,file_callback,crc_callback)

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

    log=LOG_DIR + sep + strftime('%Y_%m_%d_%H_%M_%S',localtime_catched(time()) ) +'.log'

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
            print(f'crc_calc...{fnumber(core.info_files_done)}/{fnumber(core.info_total)}                 ',end='\r')
            sleep(0.04)

        scan_thread.join()

    print('')
    print('Done')
