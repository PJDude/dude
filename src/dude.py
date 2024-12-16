#!/usr/bin/python3

####################################################################################
#
#  Copyright (c) 2022-2025 Piotr Jochymek
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

from pathlib import Path
from re import search

from signal import signal,SIGINT

from tkinter import Tk,Toplevel,PhotoImage,Menu,PanedWindow,Label,LabelFrame,Frame,StringVar,BooleanVar,IntVar
from tkinter.ttk import Checkbutton,Radiobutton,Treeview,Scrollbar,Button,Entry,Combobox,Scale,Style
from tkinter.filedialog import askdirectory,asksaveasfilename
from tkinterdnd2 import DND_FILES, TkinterDnD

from collections import defaultdict
from traceback import format_stack

from fnmatch import fnmatch

from time import sleep,strftime,time,perf_counter

import sys
from sys import exit as sys_exit
import logging

from platform import node

from os import sep,stat,scandir,readlink,rmdir,system,getcwd,name as os_name,environ as os_environ
from gc import disable as gc_disable, enable as gc_enable,collect as gc_collect,set_threshold as gc_set_threshold, get_threshold as gc_get_threshold

from os.path import abspath,normpath,dirname,join as path_join,isfile as path_isfile,split as path_split,exists as path_exists,isdir, splitext as path_splitext

#lazyfied
#from configparser import ConfigParser
#from subprocess import Popen
#from shutil import rmtree
#from PIL import Image, ImageTk
#from PIL.ImageTk import PhotoImage as ImageTk_PhotoImage
#from PIL.Image import BILINEAR,open as image_open

windows = bool(os_name=='nt')

if windows:
    from os import startfile

from send2trash import send2trash

from core import *
import console
from dialogs import *

from dude_images import dude_image

l_info = logging.info
l_warning = logging.warning
l_error = logging.error

###########################################################################################################################################

CFG_KEY_FULL_CRC='show_full_crc'
CFG_KEY_SHOW_TOOLTIPS_INFO='show_tooltips_info'
CFG_KEY_SHOW_TOOLTIPS_HELP='show_tooltips_help'
CFG_KEY_PREVIEW_AUTO_UPDATE='preview_auto_update'
CFG_KEY_FULL_PATHS='show_full_paths'
CFG_KEY_SHOW_MODE='show_mode'
CFG_KEY_REL_SYMLINKS='relative_symlinks'

CFG_KEY_EXCLUDE_REGEXP='excluderegexpp'

CFG_ERASE_EMPTY_DIRS='erase_empty_dirs'
CFG_ABORT_ON_ERROR='abort_on_error'
CFG_SEND_TO_TRASH='send_to_trash'
CFG_CONFIRM_SHOW_CRCSIZE='confirm_show_crcsize'
CFG_CONFIRM_SHOW_LINKSTARGETS='confirm_show_links_targets'

CFG_ALLOW_DELETE_ALL='allow_delete_all'
CFG_SKIP_INCORRECT_GROUPS='skip_incorrect_groups'
CFG_ALLOW_DELETE_NON_DUPLICATES='allow_delete_non_duplicates'

CFG_KEY_EXCLUDE='exclude'
CFG_KEY_WRAPPER_FILE = 'file_open_wrapper'
CFG_KEY_WRAPPER_FOLDERS = 'folders_open_wrapper'
CFG_KEY_WRAPPER_FOLDERS_PARAMS = 'folders_open_wrapper_params'

CFG_KEY_SEARCH_TXT_STRING = 'search_txt_string'
CFG_KEY_SEARCH_TXT_CS = 'search_txt_cs'

CFG_KEY_FIND_STRING_0 = 'find_string_0'
CFG_KEY_FIND_STRING_1 = 'find_string_1'

CFG_KEY_FIND_RE_0 = 'find_re_0'
CFG_KEY_FIND_RE_1 = 'find_re_1'

CFG_KEY_MARK_STRING_0 = 'mark_string_0'
CFG_KEY_MARK_STRING_1 = 'mark_string_1'

CFG_KEY_MARK_RE_0 = 'mark_re_0'
CFG_KEY_MARK_RE_1 = 'mark_re_1'

CFG_KEY_SHOW_PREVIEW = 'preview_shown'

cfg_defaults={
    CFG_KEY_FULL_CRC:False,
    CFG_KEY_SHOW_TOOLTIPS_INFO:True,
    CFG_KEY_SHOW_TOOLTIPS_HELP:True,
    CFG_KEY_PREVIEW_AUTO_UPDATE:True,
    CFG_KEY_FULL_PATHS:False,
    CFG_KEY_SHOW_MODE:'0',
    CFG_KEY_REL_SYMLINKS:True,
    CFG_KEY_EXCLUDE_REGEXP:False,
    CFG_ERASE_EMPTY_DIRS:True,
    CFG_ABORT_ON_ERROR:True,
    CFG_SEND_TO_TRASH:True,
    CFG_CONFIRM_SHOW_CRCSIZE:False,
    CFG_CONFIRM_SHOW_LINKSTARGETS:True,
    CFG_ALLOW_DELETE_ALL:False,
    CFG_SKIP_INCORRECT_GROUPS:True,
    CFG_ALLOW_DELETE_NON_DUPLICATES:False,
    CFG_KEY_WRAPPER_FILE:'',
    CFG_KEY_WRAPPER_FOLDERS:'',
    CFG_KEY_WRAPPER_FOLDERS_PARAMS:'2',
    CFG_KEY_EXCLUDE:'',
    CFG_KEY_SEARCH_TXT_STRING:'',
    CFG_KEY_SEARCH_TXT_CS:False,
    CFG_KEY_FIND_STRING_0:'*',
    CFG_KEY_FIND_STRING_1:'*',
    CFG_KEY_FIND_RE_0:False,
    CFG_KEY_FIND_RE_1:False,
    CFG_KEY_MARK_STRING_0:'*',
    CFG_KEY_MARK_STRING_1:'*',
    CFG_KEY_MARK_RE_0:False,
    CFG_KEY_MARK_RE_1:False,
    CFG_KEY_SHOW_PREVIEW:False
}

NAME={DELETE:'Delete',SOFTLINK:'Softlink',HARDLINK:'Hardlink',WIN_LNK:'.lnk file'}

HOMEPAGE='https://github.com/PJDude/dude'

TEXT_EXTENSIONS = ('.txt','.bat','.sh','.md','.html','.py','.cpp','.h','.ini','.tcl','.xml','.url','.lnk','.diz','.lng','.log','.rc','.csv','.ps1','.js','.v','.sv','.do')

#DE_NANO = 1_000_000_000

class Config:
    def __init__(self,config_dir):
        from configparser import ConfigParser

        #l_debug('Initializing config: %s', config_dir)
        self.config = ConfigParser()
        self.config.add_section('main')
        self.config.add_section('geometry')
        #self.config.add_section('preview')

        self.path = config_dir
        self.file = self.path + '/cfg.ini'

    def write(self):
        l_info('writing config')
        Path(self.path).mkdir(parents=True,exist_ok=True)
        try:
            with open(self.file, 'w',encoding='utf-8') as configfile:
                self.config.write(configfile)
        except Exception as e:
            l_error(e)

    def read(self):
        l_info('reading config')
        if path_isfile(self.file):
            try:
                with open(self.file, 'r',encoding='utf-8') as configfile:
                    self.config.read_file(configfile)
            except Exception as e:
                l_error(e)
        else:
            l_warning('no config file: %s',self.file)

    def set(self,key,val,section='main'):
        self.config.set(section,key,str(val))

    def set_bool(self,key,val,section='main'):
        self.config.set(section,key,('0','1')[val])

    def get(self,key,default='',section='main'):
        try:
            res=self.config.get(section,key)
        except Exception as e:
            l_warning('gettting config key: %s',key)
            l_warning(e)
            res=default
            if not res or res=='':
                res=cfg_defaults[key]

            self.set(key,res,section=section)

        return str(res)

    def get_bool(self,key,section='main'):
        try:
            res=self.config.get(section,key)
            return res=='1'

        except Exception as e:
            l_warning('gettting config key: %s',key)
            l_warning(e)
            res=cfg_defaults[key]
            self.set_bool(key,res,section=section)
            return res

###########################################################
def measure(func):
    def wrapper(*args,**kwargs):
        t0=perf_counter()
        res = func(*args,**kwargs)
        t1=perf_counter()

        print(f'timed {func.__name__}:',t1-t0)
        return res

    return wrapper
###########################################################
class Image_Cache:
    def __init__(self,tkwindow):
        from threading import Thread
        from queue import Queue

        self.paths_queue = Queue()
        self.scaled_images_data_queue = Queue()

        self.init_all()

        self.pre_and_next_range=10

        if env_dude_preload:=os_environ.get('DUDE_PRELOAD'):
            print(f'{env_dude_preload=}')
            try:
                env_dude_preload_int = int(env_dude_preload)
            except Exception as e:
                print('DUDE_PRELOAD Error:',e)
                sys_exit(5)
            else:
                if env_dude_preload_int>0:
                    self.pre_and_next_range=env_dude_preload_int
                else:
                    print('DUDE_PRELOAD !<0:',e)
                    sys_exit(6)

        #self.limit_full=2*self.pre_and_next_range
        #self.limit_scaled=self.limit_full
        #self.limit_scaled_photoimage=self.limit_scaled
        #print('self.limit_full:',self.limit_full)

        self.window_size = (100,100)
        self.txt_label_heigh = 0

        self.current_ratio = 1.0
        self.read_ahead_enabled = True
        self.threads_keeep_looping = True

        max_threads = cpu_count()

        self.read_ahead_threads = {}

        #self.scaled_images_dict={}
        #self.scaled_photo_images_dict={}

        for i in range(max_threads):
            self.read_ahead_threads[i] = Thread(target=lambda i = i : self.read_ahead_threaded_loop(i),daemon=True)
            self.read_ahead_threads[i].start()

        #self.eternal_photo_imagination(tkwindow)
        tkwindow.after(10,lambda : self.eternal_photo_imagination(tkwindow))

    def init_all(self):
        from collections import deque
        from queue import Queue

        self.cache_full={}
        self.cache_scaled={}
        self.cache_scaled_photoimage={}

        #self.cache_full_deque=deque()
        #self.cache_scaled_deque=deque()
        #self.cache_scaled_photoimage_deque=deque()

        self.read_ahead_queue=Queue()

    ###############################################################
    #def threaded_paths_queue_processor(self):
    #    self_paths_queue_get = self.paths_queue.get
    #    self_paths_queue_task_done = self.paths_queue.task_done
    #    self_scaled_images_data_queue_put = self.scaled_images_data_queue.put
    #    while self.threads_keeep_looping:
    #        path = self_paths_queue_get()
    #        try:
    #            scaled_image,width,height,ratio = self.read_scale_convert(path)
    #            if scaled_image:
    #                print('threaded_paths_queue_processor put',path)
    #                self_scaled_images_data_queue_put(path,scaled_image,width,height,ratio)
    #        except Exception as e:
    #            print('threaded_paths_queue_processor error:',e)
    #        self_paths_queue_task_done()
    #    sys_exit()

    def read_ahead_threaded_loop(self,thread_id):
        from queue import Empty
        #print('read_ahead_threaded_loop started',thread_id)
        #self_read_ahead_queue_get = self.read_ahead_queue.get
        #self_read_ahead_queue_task_done = self.read_ahead_queue.task_done

        #self_get_cached_scaled_image = self.get_cached_scaled_image

        self_scaled_images_data_queue_put = self.scaled_images_data_queue.put
        self_cache_scaled_photoimage = self.cache_scaled_photoimage

        while self.threads_keeep_looping:
            try:
                if self.read_ahead_enabled:

                    try:
                        path = self.read_ahead_queue.get(True,0.01)
                    except Empty:
                        #print('ra q empty')
                        #sleep(0.1)
                        pass
                    else:
                        #print(thread_id,'processing - done:',path)
                        self.read_ahead_queue.task_done()

                        if path:
                            if path not in self_cache_scaled_photoimage:
                                scaled_image,width,height,ratio = self.read_scale_convert(path)

                                if scaled_image:
                                    #print('self_scaled_images_data_queue_put',path,width,height)
                                    self_scaled_images_data_queue_put( (path,scaled_image,width,height,ratio) )
                                    continue
                                else:
                                    print('no scaled_image')

                                #self_get_cached_scaled_image(path)
                                #print('cached:',path,len(self.read_ahead_queue))
                        else:
                            sleep(0.1)
                else:
                    print('not enabled')
                    sleep(0.01)
            except Exception as e:
                print('read_ahead_threaded_loop error',e)
                sleep(1)

        #print('read_ahead_threaded_loop ended')
        sys_exit()

    def eternal_photo_imagination(self,tkwindow):
        from queue import Empty

        #print('eternal_photo_imagination')

        from PIL.ImageTk import PhotoImage as ImageTk_PhotoImage
        self_cache_scaled_photoimage = self.cache_scaled_photoimage

        #wait_var=BooleanVar()
        #wait_var_set = wait_var.set
        #wait_var_set(False)

        tkwindow_after = tkwindow.after

        self_scaled_images_data_queue_get = self.scaled_images_data_queue.get

        if self.threads_keeep_looping:
            #print('a0',self.scaled_images_data_queue )

            try:
                got = self_scaled_images_data_queue_get(True,0.01)
            except Empty:
                tkwindow_after(50,lambda : self.eternal_photo_imagination(tkwindow))
            else:
                #print('a2',got,':')
                path,scaled_image,width,height,ratio = got
                #print('a3')
                self.photo_imagining_in_progress=True
                self_cache_scaled_photoimage[path] = ImageTk_PhotoImage(scaled_image),width,height,ratio
                self.eternal_photo_imagination(tkwindow)
                self.photo_imagining_in_progress=False

                #print('a4')
                #tkwindow_after(1,lambda : self.eternal_photo_imagination(tkwindow))
                #print('a5')


            #print('a5')

            #print('a6')
            #self_main_wait_variable(wait_var)
    ###############################################################

    def end(self):
        self.init_all()
        self.threads_keeep_looping=False

        for thread in self.read_ahead_threads.values():
            thread.join()

    def set_window_size(self,window_size,txt_label_heigh):
        from collections import deque

        if self.window_size != window_size or self.txt_label_heigh != txt_label_heigh:
            self.window_size = window_size
            self.txt_label_heigh = txt_label_heigh

            self.cache_scaled={}
            self.cache_scaled_photoimage={}
            #self.cache_scaled_deque=deque()
            #self.cache_scaled_photoimage_deque=deque()

    def reset_read_ahead(self):
        from queue import Queue

        #print('reset_read_ahead')
        #self.read_ahead_queue.clear()
        self.read_ahead_queue=Queue()

    def add_image_to_read_ahead(self, path):
        #print('add_image_to_read_ahead',path)
        self.read_ahead_queue.put(path)

    ##############################################################################

    #def get_cached_full_image(self,path):
    #    from PIL.Image import open as image_open

    #    if not path_isfile(path):
    #        return None

    #    self_cache_full = self.cache_full
    #    if path not in self_cache_full:
    #        try:
    #            image = image_open(path)
    #            if image.mode != 'RGBA':
    #                image = image.convert("RGBA")

    #            self_cache_full_deque = self.cache_full_deque
    #            if len(self_cache_full_deque)>self.limit_full:
    #                path_to_remove = self_cache_full_deque.popleft()
    #                del self_cache_full[path_to_remove]

    #            self_cache_full_deque.append(path)

    #            self_cache_full[path]=image

    #            return image
    #        except Exception as e:
    #            print('get_cached_full_image Error:',e)
    #            return None
    #    else:
    #        return self_cache_full[path]

    #def get_cached_scaled_image(self,path):
    #    from PIL.Image import BILINEAR
        #from PIL.ImageTk import PhotoImage as ImageTk_PhotoImage

    #    self_cache_scaled = self.cache_scaled

    #    if path not in self_cache_scaled:
    #        if full_image:=self.get_cached_full_image(path):
    #            window_size_width,window_size_height = self.window_size

    #            height = full_image.height
    #            ratio_y = height/(window_size_height-self.txt_label_heigh)

    #            width = full_image.width
    #            ratio_x = width/window_size_width

    #            self_cache_scaled_deque = self.cache_scaled_deque
    #            if self_cache_scaled_deque and len(self_cache_scaled_deque)>self.limit_scaled:
    #                path_to_remove = self_cache_scaled_deque.popleft()
    #                del self_cache_scaled[path_to_remove]

    #            current_ratio = max(ratio_x,ratio_y,1)
    #            self_cache_scaled[path] = image_combo = full_image if current_ratio==1 else full_image.resize( ( int (width/current_ratio), int(height/current_ratio)) ,BILINEAR),width,height,current_ratio
    #            self_cache_scaled_deque.append(path)

    #            return image_combo
    #        else:
    #            return None,0,0,1
    #    else:
    #        return self_cache_scaled[path]

    photo_imagining_in_progress = False
    def get_cached_scaled_photo_image(self,path,tkwindow):
        #from PIL.ImageTk import PhotoImage as ImageTk_PhotoImage

        self_cache_scaled_photoimage = self.cache_scaled_photoimage

        while True:
            if path in self_cache_scaled_photoimage:
                return self_cache_scaled_photoimage[path]
            else:
                if self.photo_imagining_in_progress:
                    print('...wait photo_imagining_in_progress')
                    tkwindow.after(100)

                    continue

                #if scaled_image_combo:=self.get_cached_scaled_image(path):
                    #scaled_image,width,height,ratio = scaled_image_combo

                    #self_cache_scaled_photoimage_deque = self.cache_scaled_photoimage_deque
                    #if self_cache_scaled_photoimage_deque and len(self_cache_scaled_photoimage_deque)>self.limit_scaled_photoimage:
                    #    path_to_remove = self_cache_scaled_photoimage_deque.popleft()
                    #    del self_cache_scaled_photoimage[path_to_remove]

                    #self_cache_scaled_photoimage_deque.append(path)

                    #self_cache_scaled_photoimage[path] = photoimage_combo = ImageTk_PhotoImage(scaled_image),width,height,ratio
                    #self_cache_scaled_photoimage[path] = photoimage_combo = scaled_image,width,height,ratio

                    #return photoimage_combo
                #else:
                return None,0,0,1

    def read_scale_convert(self,path):
        from PIL.Image import open as image_open
        from PIL.Image import BILINEAR
        #from PIL.ImageTk import PhotoImage as ImageTk_PhotoImage

        if not path_isfile(path):
            return None

        window_size_width,window_size_height = self.window_size

        try:
            full_image = image_open(path)
            if full_image.mode != 'RGBA':
                full_image = full_image.convert("RGBA")

            height = full_image.height
            ratio_y = height/(window_size_height-self.txt_label_heigh)

            width = full_image.width
            ratio_x = width/window_size_width

            ratio = max(ratio_x,ratio_y,1)

            return full_image if ratio==1 else full_image.resize( ( int (width/ratio), int(height/ratio)) ,BILINEAR),width,height,ratio

        except Exception as e:
            print('get_cached_full_image Error:',e)
            return None,None,None,None

    #read_ahead_enabled=True

    def get_photo_image(self,path,tkwindow):
        #print('get_photo_image',path)

        #self.read_ahead_enabled=False
        scaled_image,width,height,current_ratio=self.get_cached_scaled_photo_image(path,tkwindow)
        #self.read_ahead_enabled=True

        if scaled_image:
            return scaled_image,f'{width} x {height} pixels' + (f' ({round(100.0/current_ratio)}%)' if current_ratio>1 else '')
        else:
            return None,f'get_photo_image error:1 {width},{height},{current_ratio}'

###########################################################

class Gui:
    MAX_PATHS=8

    sel_path_full=''

    block_processing_stack=['init']
    block_processing_stack_append = block_processing_stack.append
    block_processing_stack_pop = block_processing_stack.pop

    def processing_off(self,caller_id=None):
        self.block_processing_stack_append(caller_id)

        disable = lambda menu : self.menubar_entryconfig(menu, state="disabled")

        _ = {disable(menu) for menu in ("File","Navigation","Help") }

        self.menubar_config(cursor='watch')
        self.main_config(cursor='watch')

    def processing_on(self):
        self.block_processing_stack_pop()

        if not self.block_processing_stack:
            norm = lambda menu : self.menubar_entryconfig(menu, state="normal")

            _ = {norm(menu) for menu in ("File","Navigation","Help") }

            self.main_config(cursor='')
            self.menubar_config(cursor='')

    #####################################################
    def block_and_log(func):
        def block_and_log_wrapp(self,*args,**kwargs):
            self.processing_off(f'b&l_wrapp:{func.__name__}')
            l_info("b&l '%s' start",func.__name__)

            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('block_and_log_wrapp func:%s error:%s args:%s kwargs:%s' % (func.__name__,e,args,kwargs) )
                l_error('block_and_log_wrapp func:%s error:%s args:%s kwargs: %s',func.__name__,e,args,kwargs)
                l_error(''.join(format_stack()))
                self.get_info_dialog_on_main().show('INTERNAL ERROR block_and_log_wrapp',f'{func.__name__}\n' + str(e))
                res=None

            self.processing_on()

            l_info("b&l '%s' end",func.__name__)
            return res
        return block_and_log_wrapp

    def block(func):
        def block_wrapp(self,*args,**kwargs):
            self.processing_off(f'block_wrapp:{func.__name__}')

            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('block_wrapp func:%s error:%s args:%s kwargs:%s' % (func.__name__,e,args,kwargs) )
                l_error('block_wrapp func:%s error:%s args:%s kwargs: %s',func.__name__,e,args,kwargs)
                l_error(''.join(format_stack()))
                self.get_info_dialog_on_main().show('INTERNAL ERROR block_wrapp',f'{func.__name__}\n' + str(e))
                res=None

            self.processing_on()

            return res
        return block_wrapp

    def catched(func):
        def catched_wrapp(self,*args,**kwargs):
            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('catched_wrapp func:%s error:%s args:%s kwargs:%s' % (func.__name__,e,args,kwargs) )
                l_error('catched_wrapp func:%s error:%s args:%s kwargs: %s',func.__name__,e,args,kwargs)
                l_error(''.join(format_stack()))
                self.get_info_dialog_on_main().show('INTERNAL ERROR catched_wrapp','%s %s' % (func.__name__,str(e)) )
                res=None
            return res
        return catched_wrapp

    def logwrapper(func):
        def logwrapper_wrapp(self,*args,**kwargs):
            l_info("logwrapper '%s' start",func.__name__)
            start = perf_counter()
            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('logwrapper_wrapp func:%s error:%s args:%s kwargs:%s' % (func.__name__,e,args,kwargs) )
                l_error('logwrapper_wrapp func:%s error:%s args:%s kwargs: %s',func.__name__,e,args,kwargs)
                l_error(''.join(format_stack()))
                self.get_info_dialog_on_main().show('INTERNAL ERROR logwrapper_wrapp','%s %s' % (func.__name__,str(e)) )
                res=None

            l_info("logwrapper '%s' end. BENCHMARK TIME:%s",func.__name__,perf_counter()-start)
            return res
        return logwrapper_wrapp

    def restore_status_line(func):
        def restore_status_line_wrapp(self,*args,**kwargs):

            prev=self.status_curr_text
            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('restore_status_line_wrapp:%s:%s args:%s kwargs:%s' % (func.__name__,e,args,kwargs) )
                l_error('restore_status_line_wrapp:%s:%s args:%s kwargs:%s',func.__name__,e,args,kwargs)
                l_error(''.join(format_stack()))
                self.get_info_dialog_on_main().show('INTERNAL ERROR restore_status_line_wrapp',str(e))
                res=None
            else:
                self.status(prev)

            return res
        return restore_status_line_wrapp

    #######################################################################
    action_abort=False

    def progress_dialog_abort(self):
        self.status("Abort pressed ...")
        l_info("Abort pressed ...")
        self.action_abort=True

    other_tree={}

    def handle_sigint(self):
        self.status("Received SIGINT signal")
        l_warning("Received SIGINT signal")
        self.action_abort=True

    def preview_yscrollcommand(self,v1,v2):
        if v1=='0.0' and v2=='1.0':
            self.preview_text_vbar.grid_forget()
        else:
            self.preview_text_vbar.set(v1,v2)
            self.preview_text_vbar.grid(row=0,column=1,sticky='ns')

    def preview_xscrollcommand(self,v1,v2):
        if v1=='0.0' and v2=='1.0':
            self.preview_text_hbar.grid_forget()
        else:
            self.preview_text_hbar.set(v1,v2)
            self.preview_text_hbar.grid(row=1,column=0,sticky='we')

    def __init__(self,cwd,paths_to_add=None,exclude=None,exclude_regexp=None,norun=None,images_mode_tuple=None,size_min_str=0,size_max_str=0):
        images,ihash,idivergence,rotations,imin,imax,igps = images_mode_tuple if images_mode_tuple else (False,0,0,False,0,0,False)

        gc_disable()

        self.cwd=cwd
        self.last_dir=self.cwd

        self.preview_shown=False

        self.cfg = Config(CONFIG_DIR)
        self.cfg.read()

        self.cfg_get_bool=self.cfg.get_bool
        self.cfg_get=self.cfg.get

        self.exclude_frames=[]

        self.paths_to_scan_from_dialog=[]

        self.current_folder_items_dict = {}

        signal(SIGINT, lambda a, k : self.handle_sigint())

        self.tree_children={}
        self.tree_children_sub={} #only groups_tree has sub children

        self.two_dots_condition = lambda path : Path(path)!=Path(path).parent if path else False

        self.tagged=set()
        self.tagged_add=self.tagged.add
        self.tagged_discard=self.tagged.discard

        self.current_folder_items_tagged_discard=self.current_folder_items_tagged.discard
        self.current_folder_items_tagged_add=self.current_folder_items_tagged.add

        self.operation_mode = MODE_CRC
        ####################################################################
        #self_main = self.main = Tk()
        self_main = self.main = TkinterDnD.Tk()

        self_main.drop_target_register(DND_FILES)
        self_main.dnd_bind('<<Drop>>', lambda e: self.main_drop(e.data) )

        self.main_config = self.main.config

        self_main.title(f'Dude (DUplicates DEtector) {VER_TIMESTAMP}')
        self_main.protocol("WM_DELETE_WINDOW", self.delete_window_wrapper)
        self_main.withdraw()

        ####################################
        self.preview = preview = Toplevel(self_main,takefocus=False)
        preview_bind = preview.bind
        preview.minsize(200,200)

        if windows:
            preview.wm_attributes("-toolwindow", True)

        try:
            preview.attributes('-type', 'dialog')
        except:
            pass

        preview.transient(self_main)

        preview.withdraw()
        preview.update()
        preview.protocol("WM_DELETE_WINDOW", lambda : self.hide_preview())

        preview_frame_txt=self.preview_frame_txt=Frame(preview)

        preview_bind('F11', lambda event : self.hide_preview() )
        preview_bind('<FocusIn>', lambda event : self.preview_focusin() )
        preview_bind('<Configure>', self.preview_conf)

        ####################################
        preview_frame_txt.grid_columnconfigure(0, weight=1)
        preview_frame_txt.grid_rowconfigure(0, weight=1)

        self.preview_text = Text(preview_frame_txt, bg='white',relief='groove',bd=2,wrap='none')
        self.preview_text.grid(row=0,column=0,sticky='news')

        self.preview_text_vbar = Scrollbar(preview_frame_txt, orient='vertical', command=self.preview_text.yview)
        self.preview_text_vbar.grid(row=0,column=1,sticky='ns')

        self.preview_text_hbar = Scrollbar(preview_frame_txt, orient='horizontal', command=self.preview_text.xview)
        self.preview_text_hbar.grid(row=1,column=0,sticky='we')

        self.preview_text.config(yscrollcommand=self.preview_yscrollcommand, xscrollcommand=self.preview_xscrollcommand)

        ####################################
        self.preview_label_txt=Label(preview,relief='groove',bd=2,anchor='w')
        self.preview_label_txt_configure = self.preview_label_txt.configure

        self.preview_label_img=Label(preview,bd=2,anchor='nw')
        self.preview_label_img_configure = self.preview_label_img.configure

        self.preview_label_txt.pack(fill='x',side='top',anchor='nw')
        self.preview_label_img.pack(fill='both',side='top',anchor='nw')
        preview_frame_txt.pack(fill='both',side='top',anchor="nw",expand=1)

        self.main_update = self_main.update
        self.main_update()

        self_main.minsize(800, 600)

        if self_main.winfo_screenwidth()>=1600 and self_main.winfo_screenheight()>=1024:
            self_main.geometry('1200x800')
        elif self_main.winfo_screenwidth()>=1200 and self_main.winfo_screenheight()>=800:
            self_main.geometry('1024x768')

        self_ico = self.ico = { img:PhotoImage(data = img_data) for img,img_data in dude_image.items() }

        self.icon_nr={ i:self_ico[str(i+1)] for i in range(self.MAX_PATHS) }

        hg_indices=('01','02','03','04','05','06','07','08', '11','12','13','14','15','16','17','18', '21','22','23','24','25','26','27','28', '31','32','33','34','35','36','37','38',)
        self.hg_ico={ i:self_ico[str('hg'+j)] for i,j in enumerate(hg_indices) }
        self.hg_ico_len = len(self.hg_ico)

        self.icon_softlink_target=self_ico['softlink_target']
        self.icon_softlink_dir_target=self_ico['softlink_dir_target']

        self.ico_dude = self_ico['dude']
        self.ico_dude_small = self_ico['dude_small']

        self.ico_folder = self_ico['folder']
        self.ico_hardlink = self_ico['hardlink']
        self.ico_softlink = self_ico['softlink']
        self.ico_softlink_dir = self_ico['softlink_dir']
        self.ico_left = self_ico['left']
        self.ico_right = self_ico['right']
        self.ico_warning = self_ico['warning']
        self.ico_search_text = self_ico['search_text']
        self.ico_empty = self_ico['empty']

        self.main_icon_tuple = (self.ico_dude,self.ico_dude_small)

        self_main.iconphoto(True, *self.main_icon_tuple)
        preview.iconphoto(True, *self.main_icon_tuple)

        self.MARK='M'
        self.UPDIR='0'
        self.DIR='1'
        self.DIRLINK='2'
        self.LINK='3'
        self.FILE='4'
        self.SINGLE='5'
        self.SINGLEHARDLINKED='6'
        self.CRC='C'

        self_main_bind = self_main.bind

        #self.defaultFont = font.nametofont("TkDefaultFont")
        #self.defaultFont.configure(family="Monospace regular",size=8,weight=font.BOLD)
        #self.defaultFont.configure(family="Monospace regular",size=10)
        #self_main.option_add("*Font", self.defaultFont)

        self.tooltip = Toplevel(self_main)
        self.tooltip_withdraw = self.tooltip.withdraw
        self.tooltip_withdraw()
        self.tooltip_deiconify = self.tooltip.deiconify
        self.tooltip_wm_geometry = self.tooltip.wm_geometry
        self.main_wm_geometry = self.main.wm_geometry

        self.tooltip.wm_overrideredirect(True)
        self.tooltip_lab=Label(self.tooltip, justify='left', background="#ffffe0", relief='solid', borderwidth=0, wraplength = 1200)
        self.tooltip_lab.pack(ipadx=1)
        self.tooltip_lab_configure = self.tooltip_lab.configure

        ####################################################################
        style = Style()

        #('aqua', 'step', 'clam', 'alt', 'default', 'classic')

        if env_theme:=os_environ.get('DUDE_THEME'):
            print(f'{env_theme=}')
            parent_theme=env_theme
        else:
            parent_theme = 'vista' if windows else 'clam'

        try:
            style.theme_create( "dummy", parent=parent_theme )
        except Exception as e:
            print(e)
            print('Try one of: aqua,step,clam,alt,default,classic')
            sys_exit(1)

        bg_color = self.bg_color = style.lookup('TFrame', 'background')
        preview.configure(bg=bg_color)
        self.preview_frame_txt.configure(bg=bg_color)

        style.theme_use("dummy")
        style_map = style.map

        bg_focus='#90DD90'
        bg_focus_off='#90AA90'
        bg_sel='#AAAAAA'

        if env_theme:
            #bg_color = self.bg_color = 'white'
            pass
        else:
            style_configure = style.configure

            if windows:
                #fix border problem ...
                style_configure("TCombobox",padding=1)

            style_map("TButton",  fg=[('disabled',"gray"),('',"black")] )

            style_configure("Treeview",rowheight=18)

            style_map("TCheckbutton",indicatorbackground=[("disabled",self.bg_color),('','white')],indicatorforeground=[("disabled",'darkgray'),('','black')],relief=[('disabled',"flat"),('',"sunken")],foreground=[('disabled',"gray"),('',"black")])
            style_map("Treeview.Heading",  relief=[('','raised')] )
            style_configure("TCheckbutton",anchor='center',padding=(4, 0, 4, 0) )
            style_configure("TButton", anchor = "center")
            style_map("TButton",  relief=[('disabled',"flat"),('',"raised")] )
            style_map('semi_focus.Treeview', background=[('focus',bg_focus),('selected',bg_focus_off),('','white')])
            style_map('no_focus.Treeview', background=[('focus',bg_focus),('selected',bg_sel),('','white')])

            style_map("TEntry", foreground=[("disabled",'darkgray'),('','black')],relief=[("disabled",'flat'),('','sunken')],borderwidth=[("disabled",0),('',2)],fieldbackground=[("disabled",self.bg_color),('','white')])

            #works but not for every theme
            #style_configure("Treeview", fieldbackground=self.bg_color)

            #else:
                #self.bg_color = 'white'

            style_configure("TButton", background = bg_color)
            style_configure('TRadiobutton', background=bg_color)
            style_configure("TCheckbutton", background = bg_color)
            style_configure("TScale", background=bg_color)
            style_configure('TScale.slider', background=bg_color)
            style_configure('TScale.Horizontal.TScale', background=bg_color)

        style_map('Treeview', background=[('focus',bg_focus),('selected',bg_sel),('','white')])

        #######################################################################
        self.menubar = Menu(self_main,bg=bg_color)
        self_main.config(menu=self.menubar)
        #######################################################################

        self_widget_leave = self.widget_leave

        self.my_next_dict={}
        self.my_prev_dict={}

        self.tooltip_message={}

        self.menubar_config = self.menubar.config
        self.menubar_cget = self.menubar.cget

        self.menubar_entryconfig = self.menubar.entryconfig
        self.menubar_norm = lambda x : self.menubar_entryconfig(x, state="normal")
        self.menubar_disable = lambda x : self.menubar_entryconfig(x, state="disabled")

        self.paned = PanedWindow(self_main,orient='vertical',relief='sunken',showhandle=0,bd=0,bg=bg_color,sashwidth=2,sashrelief='flat')
        self.paned.pack(fill='both',expand=1)

        frame_groups = Frame(self.paned,bg=bg_color)
        frame_groups.pack(fill='both',expand='yes')
        self.paned.add(frame_groups)

        frame_folder = Frame(self.paned,bg=bg_color)
        frame_folder.pack(fill='both',expand='yes')
        self.paned.add(frame_folder)

        (status_frame_groups := Frame(frame_groups,bg=bg_color)).pack(side='bottom', fill='both')

        self.status_all_quant=Label(status_frame_groups,width=10,borderwidth=2,bg=bg_color,relief='groove',foreground='red',anchor='w')
        self.status_all_quant_configure = self.status_all_quant.configure

        self.status_all_quant.pack(fill='x',expand=0,side='right')
        Label(status_frame_groups,width=16,text="All marked files # ",relief='groove',borderwidth=2,bg=bg_color,anchor='e').pack(fill='x',expand=0,side='right')
        self.status_all_size=Label(status_frame_groups,width=10,borderwidth=2,bg=bg_color,relief='groove',foreground='red',anchor='w')
        self.status_all_size.pack(fill='x',expand=0,side='right')
        self.status_all_size_configure=self.status_all_size.configure

        Label(status_frame_groups,width=18,text='All marked files size: ',relief='groove',borderwidth=2,bg=bg_color,anchor='e').pack(fill='x',expand=0,side='right')
        self.status_groups=Label(status_frame_groups,text='0',image=self.ico_empty,width=80,compound='right',borderwidth=2,bg=bg_color,relief='groove',anchor='e')
        self.status_groups_configure = self.status_groups.configure

        self.status_groups.pack(fill='x',expand=0,side='right')

        self.widget_tooltip(self.status_groups,'Number of groups with consideration of "Cross paths" or "Same directory" mode')

        Label(status_frame_groups,width=10,text='Groups: ',relief='groove',borderwidth=2,bg=bg_color,anchor='e').pack(fill='x',expand=0,side='right')

        self.status_path = Label(status_frame_groups,text='',relief='flat',borderwidth=1,bg=bg_color,anchor='w')
        self.status_path.pack(fill='x',expand=1,side='left')
        self.widget_tooltip(self.status_path,'The full path of a directory shown in the bottom panel.')

        self.status_path_configure=self.status_path.configure
        ###############################################################################

        (status_frame_folder := Frame(frame_folder,bg=bg_color)).pack(side='bottom',fill='both')

        self.status_line_lab=Label(status_frame_folder,width=30,image=self_ico['expression'],compound= 'left',text='',borderwidth=2,bg=bg_color,relief='groove',anchor='w')
        self.status_line_lab.pack(fill='x',expand=1,side='left')
        self.status_line_lab_configure = self.status_line_lab.configure
        self.status_line_lab_update = self.status_line_lab.update

        self.status_folder_quant=Label(status_frame_folder,width=10,borderwidth=2,bg=bg_color,relief='groove',foreground='red',anchor='w')
        self.status_folder_quant.pack(fill='x',expand=0,side='right')
        self.status_folder_quant_configure=self.status_folder_quant.configure

        Label(status_frame_folder,width=16,text='Marked files # ',relief='groove',borderwidth=2,bg=bg_color,anchor='e').pack(fill='x',expand=0,side='right')
        self.status_folder_size=Label(status_frame_folder,width=10,borderwidth=2,bg=bg_color,relief='groove',foreground='red',anchor='w')
        self.status_folder_size.pack(expand=0,side='right')
        self.status_folder_size_configure=self.status_folder_size.configure

        Label(status_frame_folder,width=18,text='Marked files size: ',relief='groove',borderwidth=2,bg=bg_color,anchor='e').pack(fill='x',expand=0,side='right')

        self_main_unbind_class = self.main_unbind_class = self_main.unbind_class

        self_main_bind_class = self.main_bind_class = self_main.bind_class

        self_main_unbind_class('Treeview', '<KeyPress-Up>')
        self_main_unbind_class('Treeview', '<KeyPress-Down>')
        self_main_unbind_class('Treeview', '<KeyPress-Next>')
        self_main_unbind_class('Treeview', '<KeyPress-Prior>')
        self_main_unbind_class('Treeview', '<KeyPress-space>')
        self_main_unbind_class('Treeview', '<KeyPress-Return>')
        self_main_unbind_class('Treeview', '<KeyPress-Left>')
        self_main_unbind_class('Treeview', '<KeyPress-Right>')
        self_main_unbind_class('Treeview', '<Double-Button-1>')

        self_main_bind_class('Treeview','<KeyPress>', self.key_press )
        self_main_bind_class('Treeview','<ButtonPress-3>', self.context_menu_show)

        self.groups_tree=Treeview(frame_groups,takefocus=True,selectmode='none',show=('tree','headings') )
        self_groups_tree = self.groups_tree

        self.groups_tree_see = self_groups_tree.see
        self.groups_tree_focus = lambda item : self.groups_tree.focus(item)

        self.tree_children[self.groups_tree]=[]

        self.org_label={}
        self_org_label = self.org_label

        self_org_label['path']='Subpath'
        self_org_label['file']='File'
        self_org_label['size_h']='Size'
        self_org_label['instances_h']='Copies'
        self_org_label['ctime_h']='Change Time'

        self_groups_tree["columns"]=('pathnr','path','file','size','size_h','ctime','dev','inode','crc','instances','instances_h','ctime_h','kind')
        self_groups_tree["displaycolumns"]=('path','file','size_h','instances_h','ctime_h')

        self_groups_tree_column = self_groups_tree.column

        self_groups_tree_column('#0', width=120, minwidth=100, stretch='no')
        self_groups_tree_column('path', width=100, minwidth=10, stretch='yes' )
        self_groups_tree_column('file', width=100, minwidth=10, stretch='yes' )
        self_groups_tree_column('size_h', width=80, minwidth=80, stretch='no')
        self_groups_tree_column('instances_h', width=80, minwidth=80, stretch='no')
        self_groups_tree_column('ctime_h', width=150, minwidth=100, stretch='no')

        self_groups_tree_heading = self_groups_tree.heading

        self_groups_tree_heading('#0',text='CRC / Scan Path',anchor='w')
        self_groups_tree_heading('path',anchor='w' )
        self_groups_tree_heading('file',anchor='w' )
        self_groups_tree_heading('size_h',anchor='w')
        self_groups_tree_heading('ctime_h',anchor='w')
        self_groups_tree_heading('instances_h',anchor='w')
        self_groups_tree_heading('size_h', text='Size \u25BC')

        #bind_class breaks columns resizing
        self_groups_tree.bind('<ButtonPress-1>', self.tree_on_mouse_button_press)
        self_groups_tree.bind('<Control-ButtonPress-1>',  lambda event :self.tree_on_mouse_button_press(event,True) )
        self_main_unbind_class('Treeview', '<<TreeviewClose>>')
        self_main_unbind_class('Treeview', '<<TreeviewOpen>>')

        def mouse_scroll(event):
            if self.block_processing_stack:
                return "break"

        self_groups_tree.bind('<MouseWheel>', mouse_scroll)
        self_groups_tree.bind('<Button-4>', mouse_scroll)
        self_groups_tree.bind('<Button-5>', mouse_scroll)

        def self_groups_tree_yview(*args):
            if self.block_processing_stack:
                return "break"

            self_groups_tree.yview(*args)

        self.vsb1 = Scrollbar(frame_groups, orient='vertical', command=self_groups_tree_yview,takefocus=False)

        self_groups_tree.configure(yscrollcommand=self.vsb1.set)

        self.vsb1.pack(side='right',fill='y',expand=0)
        self_groups_tree.pack(fill='both',expand=1, side='left')

        self_groups_tree.bind('<Double-Button-1>', self.double_left_button)

        self.folder_tree=Treeview(frame_folder,takefocus=True,selectmode='none')
        self_folder_tree = self.folder_tree

        self.tree_children[self.folder_tree]=[]

        self.folder_tree_see = self_folder_tree.see

        self.folder_tree_configure = self_folder_tree.configure
        self.folder_tree_delete = self_folder_tree.delete

        self_folder_tree['columns']=('file','dev','inode','kind','crc','size','size_h','ctime','ctime_h','instances','instances_h')

        self_folder_tree['displaycolumns']=('file','size_h','instances_h','ctime_h')

        self_folder_tree_column = self_folder_tree.column

        self_folder_tree_column('#0', width=120, minwidth=100, stretch='no')
        self_folder_tree_column('file', width=200, minwidth=20, stretch='yes')
        self_folder_tree_column('size_h', width=80, minwidth=80, stretch='no')
        self_folder_tree_column('instances_h', width=80, minwidth=80, stretch='no')
        self_folder_tree_column('ctime_h', width=150, minwidth=100, stretch='no')

        self_folder_tree_heading = self_folder_tree.heading

        self_folder_tree_heading('#0',text='CRC',anchor='w')
        self_folder_tree_heading('file',anchor='w')
        self_folder_tree_heading('size_h',anchor='w')
        self_folder_tree_heading('instances_h',anchor='w')
        self_folder_tree_heading('ctime_h',anchor='w')

        self.tree_index={self.groups_tree:0,self.folder_tree:1}

        for tree in (self_groups_tree,self_folder_tree):
            tree_heading = tree.heading
            for col in tree["displaycolumns"]:
                if col in self_org_label:
                    tree_heading(col,text=self_org_label[col])

        self_folder_tree_heading('file', text='File \u25B2')

        self_folder_tree.bind('<MouseWheel>', mouse_scroll)
        self_folder_tree.bind('<Button-4>', mouse_scroll)
        self_folder_tree.bind('<Button-5>', mouse_scroll)

        def self_folder_tree_yview(*args):
            if self.block_processing_stack:
                return "break"

            self_folder_tree.yview(*args)

        self.vsb2 = Scrollbar(frame_folder, orient='vertical', command=self_folder_tree_yview,takefocus=False)

        self.folder_tree_configure(yscrollcommand=self.vsb2.set)

        self_folder_tree.pack(fill='both',expand=1,side='left')
        self.vsb2.pack(side='right',fill='y',expand=0)

        self_folder_tree.bind('<Double-Button-1>', self.double_left_button)

        self_groups_tree_tag_configure = self_groups_tree.tag_configure

        self_groups_tree_tag_configure(self.MARK, foreground='red')
        self_groups_tree_tag_configure(self.MARK, background='red')
        self_groups_tree_tag_configure(self.CRC, foreground='gray')

        self_folder_tree_tag_configure = self_folder_tree.tag_configure

        self_folder_tree_tag_configure(self.MARK, foreground='red')
        self_folder_tree_tag_configure(self.MARK, background='red')

        self_folder_tree_tag_configure(self.SINGLE, foreground='gray')
        self_folder_tree_tag_configure(self.DIR, foreground='sienna4',font="TkDefaultFont 10 bold")
        self_folder_tree_tag_configure(self.DIRLINK, foreground='sienna4',font="TkDefaultFont 10 bold")
        self_folder_tree_tag_configure(self.LINK, foreground='darkgray')

        #bind_class breaks columns resizing
        self_folder_tree.bind('<ButtonPress-1>', self.tree_on_mouse_button_press)
        self_folder_tree.bind('<Control-ButtonPress-1>',  lambda event :self.tree_on_mouse_button_press(event,True) )

        self.other_tree[self_folder_tree]=self_groups_tree
        self.other_tree[self_groups_tree]=self_folder_tree

        self.biggest_file_of_path={}
        self.biggest_file_of_path_id={}

        self.iid_to_size={}

        try:
            self.main_update()
            cfg_geometry=self.cfg_get('main','',section='geometry')

            if cfg_geometry:
                self_main.geometry(cfg_geometry)
            else:
                x_offset = int(0.5*(self_main.winfo_screenwidth()-self_main.winfo_width()))
                y_offset = int(0.5*(self_main.winfo_screenheight()-self_main.winfo_height()))

                self_main.geometry(f'+{x_offset}+{y_offset}')

        except Exception as e:
            self.status(str(e))
            l_error(e)
            cfg_geometry = None

        self.popup_groups = Menu(self_groups_tree, tearoff=0,bg=bg_color)
        self.popup_groups_unpost = self.popup_groups.unpost
        self.popup_groups.bind("<FocusOut>",lambda event : self.popup_groups_unpost() )

        self.popup_folder = Menu(self_folder_tree, tearoff=0,bg=bg_color)
        self.popup_folder_unpost = self.popup_folder.unpost
        self.popup_folder.bind("<FocusOut>",lambda event : self.popup_folder_unpost() )

        self_main_bind("<FocusOut>",lambda event : self.unpost() )
        self_main_bind("<FocusIn>",lambda event : self.focusin() )

        self.groups_tree.bind("<FocusOut>",lambda event :self.groups_tree_focus_out() )
        self.folder_tree.bind("<FocusOut>",lambda event :self.folder_tree_focus_out() )

        self.groups_tree.bind("<FocusIn>",lambda event :self.groups_tree_focus_in() )
        self.folder_tree.bind("<FocusIn>",lambda event :self.folder_tree_focus_in() )

        self.selected={}
        self.selected[self.groups_tree]=None
        self.selected[self.folder_tree]=None

        self.sel_full_path_to_file=None

        #######################################################################
        #scan dialog

        self_scan_dialog = self.scan_dialog=GenericDialog(self_main,self.main_icon_tuple,bg_color,'Scan',pre_show=self.pre_show,post_close=self.post_close)

        self.log_skipped_var=BooleanVar()
        self.log_skipped_var.set(False)

        self.all_rotations=BooleanVar()
        self.all_rotations.set(rotations)

        self.operation_mode_var=IntVar()
        self.operation_mode_var.set(MODE_SIMILARITY if images else MODE_GPS if igps else MODE_CRC)

        self_scan_dialog_area_main = self_scan_dialog.area_main

        self_scan_dialog_area_main.drop_target_register(DND_FILES)
        self_scan_dialog_area_main.dnd_bind('<<Drop>>', lambda e: self.scan_dialog_drop(e.data) )

        self_scan_dialog_area_main.grid_columnconfigure(0, weight=1)
        self_scan_dialog_area_main.grid_rowconfigure(0, weight=1)
        self_scan_dialog_area_main.grid_rowconfigure(1, weight=1)

        self_scan_dialog_widget_bind = self_scan_dialog.widget.bind
        self_scan_wrapper = self.scan_wrapper

        self_scan_dialog_widget_bind('<Alt_L><a>',lambda event : self.path_to_scan_add_dialog())
        self_scan_dialog_widget_bind('<Alt_L><A>',lambda event : self.path_to_scan_add_dialog())
        self_scan_dialog_widget_bind('<Alt_L><s>',lambda event : self_scan_wrapper())
        self_scan_dialog_widget_bind('<Alt_L><S>',lambda event : self_scan_wrapper())
        self_scan_dialog_widget_bind('<Alt_L><E>',lambda event : self.exclude_mask_add_dialog())
        self_scan_dialog_widget_bind('<Alt_L><e>',lambda event : self.exclude_mask_add_dialog())

        ##############
        temp_frame = LabelFrame(self_scan_dialog_area_main,text='Paths To scan:',borderwidth=2,bg=bg_color,takefocus=False)
        temp_frame.grid(row=0,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        sf_par=SFrame(temp_frame,bg=bg_color)
        sf_par.pack(fill='both',expand=True,side='top')
        self.paths_frame=sf_par.frame()

        buttons_fr = Frame(temp_frame,bg=bg_color,takefocus=False)
        buttons_fr.pack(fill='both',expand=False,side='bottom')

        Label(buttons_fr,relief='flat',text='Specify manually, or drag and drop here, up to 8 paths to scan',bg=bg_color,fg='gray').pack(side='right',pady=4,padx=4, fill='x',expand=True)

        self.add_path_button = Button(buttons_fr,width=18,image = self_ico['open'], command=self.path_to_scan_add_dialog,underline=0)
        self.add_path_button.pack(side='left',pady=4,padx=4)

        self.widget_tooltip(self.add_path_button,"Add path to scan")

        self.paths_frame.grid_columnconfigure(1, weight=1)
        self.paths_frame.grid_rowconfigure(99, weight=1)

        #####################
        self_paths_to_scan_entry_var = self.paths_to_scan_entry_var={}
        self.paths_to_scan_frame={}

        self_paths_frame = self.paths_frame

        self_bg_color = bg_color
        self_icon_nr = self.icon_nr

        self_paths_to_scan_frames = self.paths_to_scan_frames = {}

        self_ico_delete = self.ico['delete']
        self_path_to_scan_remove = self.path_to_scan_remove

        for row in range(self.MAX_PATHS):
            frame = self_paths_to_scan_frames[row] = Frame(self_paths_frame,bg=self_bg_color)

            Label(frame,image=self_icon_nr[row], relief='flat',bg=self_bg_color).pack(side='left',padx=2,pady=2,fill='y')

            self_paths_to_scan_entry_var[row]=StringVar()
            path_to_scan_entry = Entry(frame,textvariable=self_paths_to_scan_entry_var[row])
            path_to_scan_entry.pack(side='left',expand=1,fill='both',pady=1)
            path_to_scan_entry.bind("<KeyPress-Return>", lambda event : self_scan_wrapper())

            remove_path_button=Button(frame,image=self_ico_delete,command=lambda row=row: self_path_to_scan_remove(row),width=3)
            remove_path_button.pack(side='right',padx=2,pady=1,fill='y')

            self.widget_tooltip(remove_path_button,'Remove path from list.')

        ##############
        self.exclude_regexp_scan=BooleanVar()

        temp_frame2 = LabelFrame(self_scan_dialog_area_main,text='Exclude from scan:',borderwidth=2,bg=bg_color,takefocus=False)
        temp_frame2.grid(row=1,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        sf_par2=SFrame(temp_frame2,bg=bg_color)
        sf_par2.pack(fill='both',expand=True,side='top')
        self.exclude_frame=sf_par2.frame()

        buttons_fr2 = Frame(temp_frame2,bg=bg_color,takefocus=False)
        buttons_fr2.pack(fill='both',expand=False,side='bottom')

        self.add_exclude_button_dir = Button(buttons_fr2,width=18,image = self_ico['open'],command=self.exclude_mask_add_dir)
        self.add_exclude_button_dir.pack(side='left',pady=4,padx=4)
        self.widget_tooltip(self.add_exclude_button_dir,"Add path as exclude expression ...")

        self.add_exclude_button = Button(buttons_fr2,width=18,image= self_ico['expression'],command=self.exclude_mask_add_dialog,underline=4)

        tooltip_string = 'Add expression ...\nduring the scan, the entire path is checked \nagainst the specified expression,\ne.g.' + ('*windows* etc. (without regular expression)\nor .*windows.*, etc. (with regular expression)' if windows else '*.git* etc. (without regular expression)\nor .*\\.git.* etc. (with regular expression)')
        self.widget_tooltip(self.add_exclude_button,tooltip_string)

        self.add_exclude_button.pack(side='left',pady=4,padx=4)

        Checkbutton(buttons_fr2,text='treat as a regular expression',variable=self.exclude_regexp_scan,command=self.exclude_regexp_set).pack(side='left',pady=4,padx=4)

        self.exclude_frame.grid_columnconfigure(1, weight=1)
        self.exclude_frame.grid_rowconfigure(99, weight=1)
        ##############

        self.file_min_size_check_var = BooleanVar()
        self.file_max_size_check_var = BooleanVar()

        self.file_min_size_var = StringVar()
        self.file_max_size_var = StringVar()

        self.file_min_size_var.set(size_min_str)
        self.file_max_size_var.set(size_max_str)

        self.file_min_size_check_var.set(bool(size_min_str))
        self.file_max_size_check_var.set(bool(size_max_str))

        operation_mode_frame = LabelFrame(self_scan_dialog_area_main,text='Operation mode',borderwidth=2,bg=bg_color,takefocus=False)
        operation_mode_frame.grid(row=3,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        crc_button = Radiobutton(operation_mode_frame,text='CRC                  ',variable=self.operation_mode_var,value=MODE_CRC,command=self.operation_mode_change )
        crc_button.grid(row=0,column=0,sticky='news',padx=8,pady=3)

        self.widget_tooltip(crc_button,"the classic CRC algorithm is applied\nto groups of files of the same size.")

        similarity_button = Radiobutton(operation_mode_frame,text='Images similarity      ',variable=self.operation_mode_var,value=MODE_SIMILARITY,command=self.operation_mode_change )
        similarity_button.grid(row=0,column=1,sticky='news',padx=8,pady=3)

        self.widget_tooltip(similarity_button,"Only image files are processed\nIdentified groups contain\nimages with similar content")

        gps_button = Radiobutton(operation_mode_frame,text='Images GPS data proximity',variable=self.operation_mode_var,value=MODE_GPS,command=self.operation_mode_change )
        gps_button.grid(row=0,column=2,sticky='news',padx=8,pady=3)

        gps_button.columnconfigure( (0,1,2), weight=1, uniform=2)

        self.widget_tooltip(gps_button,"Only image files with EXIF GPS\ndata are processed. Identified groups\ncontain images with GPS coordinates\nwith close proximity to each other")

        operation_mode_frame.grid_columnconfigure( (0,1,2), weight=1)

        temp_frame3a = LabelFrame(self_scan_dialog_area_main,text='File size range',borderwidth=2,bg=bg_color,takefocus=False)
        temp_frame3a.grid(row=4,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        self.file_min_check = Checkbutton(temp_frame3a, text = 'Min:' , variable=self.file_min_size_check_var,command=self.use_size_min_change_file)
        self.file_min_check.grid(row=0,column=0,padx=4,pady=4, sticky='wens')

        self.file_min_Entry = Entry(temp_frame3a, textvariable=self.file_min_size_var,width=10)
        self.file_min_Entry.grid(row=0,column=1,sticky='news',padx=2,pady=2)

        self.file_min_Space = Label(temp_frame3a)
        self.file_min_Space.grid(row=0,column=2,sticky='news',padx=2,pady=2)

        self.file_max_check = Checkbutton(temp_frame3a, text = 'Max:' , variable=self.file_max_size_check_var,command=self.use_size_max_change_file)
        self.file_max_check.grid(row=0,column=3,padx=4,pady=4, sticky='wens')

        self.file_max_Entry = Entry(temp_frame3a, textvariable=self.file_max_size_var,width=10)
        self.file_max_Entry.grid(row=0,column=4,sticky='news',padx=2,pady=2)

        self.file_max_Space = Label(temp_frame3a)
        self.file_max_Space.grid(row=0,column=5,sticky='news',padx=2,pady=2)

        temp_frame3a.grid_columnconfigure((2,5), weight=1)

        size_min_tooltip = "Limit the search pool to files with\nsize equal or greater to the specified\n (e.g. 112kB, 1MB ...)"
        size_max_tooltip = "Limit the search pool to files with\nsize smaller or equal to the specified\n (e.g. 10MB, 1GB ...)"
        self.widget_tooltip(self.file_min_check,size_min_tooltip)
        self.widget_tooltip(self.file_min_Entry,size_min_tooltip)

        self.widget_tooltip(self.file_max_check,size_max_tooltip)
        self.widget_tooltip(self.file_max_Entry,size_max_tooltip)


        temp_frame3 = LabelFrame(self_scan_dialog_area_main,text='Similarity mode options',borderwidth=2,bg=bg_color,takefocus=False)
        temp_frame3.grid(row=5,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        sf_par3=Frame(temp_frame3,bg=bg_color)
        sf_par3.pack(fill='both',expand=True,side='top')

        sf_par4=Frame(temp_frame3,bg=bg_color)
        sf_par4.pack(fill='both',expand=True,side='top')

        self.similarity_distance_var = IntVar()
        self.similarity_distance_var.set(idivergence)

        self.similarity_distance_var_lab = StringVar()
        self.image_min_size_var = StringVar()
        self.image_max_size_var = StringVar()

        self.image_min_size_check_var = BooleanVar()
        self.image_max_size_check_var = BooleanVar()

        self.image_min_size_var.set(imin)
        self.image_max_size_var.set(imax)

        self.image_min_size_check_var.set(bool(imin))
        self.image_max_size_check_var.set(bool(imax))

        self.similarity_hsize_var = IntVar()
        self.similarity_hsize_varx2 = IntVar()
        self.similarity_hsize_var_lab = StringVar()
        self.similarity_hsize_var.set(ihash//2)
        self.similarity_hsize_varx2.set(ihash)

        similarity_hsize_frame = LabelFrame(sf_par3,text='Hash size',borderwidth=2,bg=bg_color,takefocus=False)
        similarity_hsize_frame.grid(row=0,column=0,padx=2,sticky='news')

        self.similarity_hsize_scale = Scale(similarity_hsize_frame, variable=self.similarity_hsize_var, orient='horizontal',from_=2, to=16,command=lambda x : self.hsize_val_set(),style="TScale",length=160)
        self.similarity_hsize_scale.grid(row=0,column=1,padx=4,sticky='ew')

        self.similarity_hsize_label_val = Label(similarity_hsize_frame, textvariable=self.similarity_hsize_var_lab,bg=bg_color,width=3,height=1,relief='flat')
        self.similarity_hsize_label_val.grid(row=0,column=2,padx=2)
        self.hsize_val_set()

        similarity_hsize_frame.grid_columnconfigure(1, weight=1)

        hash_tooltip = "The larger the hash size value,\nthe more details of the image\nare taken into consideration.\nThe default value is 6"
        self.widget_tooltip(self.similarity_hsize_scale,hash_tooltip)
        self.widget_tooltip(self.similarity_hsize_label_val,hash_tooltip)

        similarity_distance_frame = LabelFrame(sf_par3,text='Relative divergence',borderwidth=2,bg=bg_color,takefocus=False)
        similarity_distance_frame.grid(row=0,column=1,padx=2,sticky='news')

        self.similarity_distance_scale = Scale(similarity_distance_frame, variable=self.similarity_distance_var, orient='horizontal',from_=0, to=9,command=lambda x : self.distance_val_set(),style="TScale",length=160)
        self.similarity_distance_scale.grid(row=0,column=1,padx=4,sticky='ew')

        self.similarity_distance_label_val = Label(similarity_distance_frame, textvariable=self.similarity_distance_var_lab,bg=bg_color,width=3,height=1,relief='flat')
        self.similarity_distance_label_val.grid(row=0,column=2,padx=2)

        similarity_distance_frame.grid_columnconfigure(1, weight=1)

        div_tooltip = "The larger the relative divergence value,\nthe more differences are allowed for\nimages to be identified as similar.\nThe default value is 5"
        self.widget_tooltip(self.similarity_distance_scale,div_tooltip)
        self.widget_tooltip(self.similarity_distance_label_val,div_tooltip)

        size_range_frame = LabelFrame(sf_par3,text='Image size range (pixels)',borderwidth=2,bg=bg_color,takefocus=False)
        size_range_frame.grid(row=2,column=0,padx=2,sticky='news',columnspan=2)

        self.image_min_check = Checkbutton(size_range_frame, text = 'Min:' , variable=self.image_min_size_check_var,command=self.use_size_min_change)
        self.image_min_check.grid(row=0,column=0,padx=4,pady=4, sticky='wens')

        self.image_min_Entry = Entry(size_range_frame, textvariable=self.image_min_size_var,width=10)
        self.image_min_Entry.grid(row=0,column=1,sticky='news',padx=2,pady=2)

        self.image_min_Space = Label(size_range_frame)
        self.image_min_Space.grid(row=0,column=2,sticky='news',padx=2,pady=2)


        self.image_max_check = Checkbutton(size_range_frame, text = 'Max:' , variable=self.image_max_size_check_var,command=self.use_size_max_change)
        self.image_max_check.grid(row=0,column=3,padx=4,pady=4, sticky='wens')

        self.image_max_Entry = Entry(size_range_frame, textvariable=self.image_max_size_var,width=10)
        self.image_max_Entry.grid(row=0,column=4,sticky='news',padx=2,pady=2)

        self.image_min_Space = Label(size_range_frame)
        self.image_min_Space.grid(row=0,column=5,sticky='news',padx=2,pady=2)

        size_range_frame.grid_columnconfigure((2,5), weight=1)


        min_tooltip = "Limit the search pool to images with\nboth dimensions (width and height)\nequal or greater to the specified value\nin pixels (e.g. 512)"
        max_tooltip = "Limit the search pool to images with\nboth dimensions (width and height)\nsmaller or equal to the specified value\nin pixels (e.g. 4096)"
        self.widget_tooltip(self.image_min_check,min_tooltip)
        self.widget_tooltip(self.image_min_Entry,min_tooltip)

        self.widget_tooltip(self.image_max_check,max_tooltip)
        self.widget_tooltip(self.image_max_Entry,max_tooltip)

        self.all_rotations_check = Checkbutton(sf_par3, text = 'Check all rotations' , variable=self.all_rotations)
        self.all_rotations_check.grid(row=3,column=0,padx=4,pady=4, columnspan=4, sticky='wens')

        self.widget_tooltip(self.all_rotations_check,"calculate hashes for all (4) image rotations\nSignificantly increases searching time\nand resources consumption.")

        self.distance_val_set()
        self.operation_mode_change()

        sf_par3.grid_columnconfigure((0,1), weight=1)

        skip_button = Checkbutton(self_scan_dialog_area_main,text='log skipped files',variable=self.log_skipped_var)
        skip_button.grid(row=6,column=0,sticky='news',padx=8,pady=3)

        self.widget_tooltip(skip_button,"log every skipped file (softlinks, hardlinks, excluded, no permissions etc.)")

        self.scan_button = Button(self_scan_dialog.area_buttons,width=12,text="Scan",image=self_ico['scan'],compound='left',command=self_scan_wrapper,underline=0)
        self.scan_button.pack(side='right',padx=4,pady=4)

        self.scan_cancel_button = Button(self_scan_dialog.area_buttons,width=12,text="Cancel",image=self_ico['cancel'],compound='left',command=self.scan_dialog_hide_wrapper,underline=0)
        self.scan_cancel_button.pack(side='left',padx=4,pady=4)

        self_scan_dialog.focus=self.scan_cancel_button

        #######################################################################

        self.info_dialog_on_mark={}
        self.info_dialog_on_find={}

        def file_cascade_post():
            self.hide_tooltip()
            self.popup_groups_unpost()
            self.popup_folder_unpost()

            item_actions_state=('disabled','normal')[self.sel_item is not None]

            self.file_cascade.delete(0,'end')
            if not self.block_processing_stack:
                self_file_cascade_add_command = self.file_cascade.add_command
                self_file_cascade_add_separator = self.file_cascade.add_separator

                item_actions_state=('disabled','normal')[self.sel_item is not None]
                self_file_cascade_add_command(label = 'Scan ...',command = self.scan_dialog_show, accelerator="S",image = self_ico['scan'],compound='left')
                self_file_cascade_add_separator()
                self_file_cascade_add_command(label = 'Settings ...',command=lambda : self.get_settings_dialog().show(), accelerator="F2",image = self_ico['settings'],compound='left')
                self_file_cascade_add_separator()
                self_file_cascade_add_command(label = 'Show/Update Preview',  command = lambda : self.show_preview(),accelerator='F9',image = self.ico_empty,compound='left',state=('disabled','normal')[bool(not self.cfg_get_bool(CFG_KEY_PREVIEW_AUTO_UPDATE) or not self.preview_shown )])
                self_file_cascade_add_command(label = 'Hide Preview window',  command = lambda : self.hide_preview(),accelerator='F11',image = self.ico_empty,compound='left',state=('disabled','normal')[self.preview_shown])
                self_file_cascade_add_separator()
                self_file_cascade_add_command(label = 'Remove empty folders in specified directory ...',command=self.empty_folder_remove_ask,image = self.ico_empty,compound='left')
                self_file_cascade_add_separator()
                self_file_cascade_add_command(label = 'Save CSV',command = self.csv_save,state=item_actions_state,image = self.ico_empty,compound='left')
                self_file_cascade_add_separator()
                self_file_cascade_add_command(label = 'Erase Cache',command = self.cache_clean,image = self.ico_empty,compound='left')
                self_file_cascade_add_separator()
                self_file_cascade_add_command(label = 'Exit',command = self.exit,image = self_ico['exit'],compound='left')

        self.file_cascade= Menu(self.menubar,tearoff=0,bg=bg_color,postcommand=file_cascade_post)
        self.menubar.add_cascade(label = 'File',menu = self.file_cascade,accelerator="Alt+F")

        def navi_cascade_post():
            self.hide_tooltip()
            self.popup_groups_unpost()
            self.popup_folder_unpost()

            self.navi_cascade.delete(0,'end')
            if not self.block_processing_stack:
                item_actions_state=('disabled','normal')[self.sel_item is not None]

                self_navi_cascade_add_command = self.navi_cascade.add_command
                self_navi_cascade_add_separator = self.navi_cascade.add_separator

                self_navi_cascade_add_command(label = 'Go to dominant group (by size sum)',command = lambda : self.goto_max_group(1), accelerator="F7",state=item_actions_state, image = self_ico['dominant_size'],compound='left')
                self_navi_cascade_add_command(label = 'Go to dominant group (by quantity)',command = lambda : self.goto_max_group(0), accelerator="F8",state=item_actions_state, image = self_ico['dominant_quant'],compound='left')
                self_navi_cascade_add_separator()
                self_navi_cascade_add_command(label = 'Go to dominant folder (by size sum)',command = lambda : self.goto_max_folder(1),accelerator="F5",state=item_actions_state, image = self_ico['dominant_size'],compound='left')
                self_navi_cascade_add_command(label = 'Go to dominant folder (by quantity)',command = lambda : self.goto_max_folder(0), accelerator="F6",state=item_actions_state, image = self_ico['dominant_quant'],compound='left')
                self_navi_cascade_add_separator()
                self_navi_cascade_add_command(label = 'Go to next marked file'       ,command = lambda : self.goto_next_mark_menu(1,0),accelerator="Right",state=item_actions_state, image = self_ico['next_marked'],compound='left')
                self_navi_cascade_add_command(label = 'Go to previous marked file'   ,command = lambda : self.goto_next_mark_menu(-1,0), accelerator="Left",state=item_actions_state, image = self_ico['prev_marked'],compound='left')
                self_navi_cascade_add_separator()
                self_navi_cascade_add_command(label = 'Go to next not marked file'       ,command = lambda : self.goto_next_mark_menu(1,1),accelerator="Shift+Right",state=item_actions_state, image = self_ico['next_unmarked'],compound='left')
                self_navi_cascade_add_command(label = 'Go to previous not marked file'   ,command = lambda : self.goto_next_mark_menu(-1,1), accelerator="Shift+Left",state=item_actions_state, image = self_ico['prev_unmarked'],compound='left')

                #self_navi_cascade_add_separator()
                #self_navi_cascade_add_command(label = 'Go to dominant folder (by duplicates/other files size ratio)',command = lambda : self.goto_max_folder(1,1),accelerator="Backspace",state=item_actions_state)
                #self_navi_cascade_add_command(label = 'Go to dominant folder (by duplicates/other files quantity ratio)',command = lambda : self.goto_max_folder(0,1), accelerator="Ctrl+Backspace",state=item_actions_state)

        self.navi_cascade= Menu(self.menubar,tearoff=0,bg=bg_color,postcommand=navi_cascade_post)

        self.menubar.add_cascade(label = 'Navigation',menu = self.navi_cascade)

        def help_cascade_post():
            self.hide_tooltip()
            self.popup_groups_unpost()
            self.popup_folder_unpost()

            self.help_cascade.delete(0,'end')
            if not self.block_processing_stack:

                self_help_cascade_add_command = self.help_cascade.add_command
                self_help_cascade_add_separator = self.help_cascade.add_separator

                self_help_cascade_add_command(label = 'About',command=lambda : self.get_about_dialog().show(),accelerator="F1", image = self_ico['about'],compound='left')
                self_help_cascade_add_command(label = 'License',command=lambda : self.get_license_dialog().show(), image = self_ico['license'],compound='left')
                self_help_cascade_add_separator()
                self_help_cascade_add_command(label = 'Open current Log',command=self.show_log, image = self_ico['log'],compound='left')
                self_help_cascade_add_command(label = 'Open logs directory',command=self.show_logs_dir, image = self_ico['logs'],compound='left')
                self_help_cascade_add_separator()
                self_help_cascade_add_command(label = 'Open homepage',command=self.show_homepage, image = self_ico['home'],compound='left')

        self.help_cascade= Menu(self.menubar,tearoff=0,bg=bg_color,postcommand=help_cascade_post)

        self.menubar.add_cascade(label = 'Help',menu = self.help_cascade)

        #######################################################################
        self.reset_sels()

        self.REAL_SORT_COLUMN={}
        self_REAL_SORT_COLUMN = self.REAL_SORT_COLUMN
        self_REAL_SORT_COLUMN['path'] = 'path'
        self_REAL_SORT_COLUMN['file'] = 'file'
        self_REAL_SORT_COLUMN['size_h'] = 'size'
        self_REAL_SORT_COLUMN['ctime_h'] = 'ctime'
        self_REAL_SORT_COLUMN['instances_h'] = 'instances'

        #self_folder_tree['columns']=('file','dev','inode','kind','crc','size','size_h','ctime','ctime_h','instances','instances_h')
        self.REAL_SORT_COLUMN_INDEX={}
        self_REAL_SORT_COLUMN_INDEX = self.REAL_SORT_COLUMN_INDEX

        self_REAL_SORT_COLUMN_INDEX['path'] = 0
        self_REAL_SORT_COLUMN_INDEX['file'] = 1
        self_REAL_SORT_COLUMN_INDEX['size_h'] = 6
        self_REAL_SORT_COLUMN_INDEX['ctime_h'] = 8
        self_REAL_SORT_COLUMN_INDEX['instances_h'] = 10

        self.REAL_SORT_COLUMN_IS_NUMERIC={}
        self_REAL_SORT_COLUMN_IS_NUMERIC = self.REAL_SORT_COLUMN_IS_NUMERIC

        self_REAL_SORT_COLUMN_IS_NUMERIC['path'] = False
        self_REAL_SORT_COLUMN_IS_NUMERIC['file'] = False
        self_REAL_SORT_COLUMN_IS_NUMERIC['size_h'] = True
        self_REAL_SORT_COLUMN_IS_NUMERIC['ctime_h'] = True
        self_REAL_SORT_COLUMN_IS_NUMERIC['instances_h'] = True

        self.column_sort_last_params={}
        #colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code

        self.column_sort_last_params[self_groups_tree]=self.column_groups_sort_params_default=('size_h',self_REAL_SORT_COLUMN_INDEX['size_h'],self_REAL_SORT_COLUMN_IS_NUMERIC['size_h'],1,2,1,0)
        self.column_sort_last_params[self_folder_tree]=('file',self_REAL_SORT_COLUMN_INDEX['file'],self_REAL_SORT_COLUMN_IS_NUMERIC['file'],0,0,1,2)

        self.groups_show()

        #######################################################################

        self_groups_tree.bind("<Motion>", self.motion_on_groups_tree)
        self_folder_tree.bind("<Motion>", self.motion_on_folder_tree)

        self_groups_tree.bind("<Leave>", lambda event : self_widget_leave())
        self_folder_tree.bind("<Leave>", lambda event : self_widget_leave())

        #######################################################################

        if paths_to_add:
            if len(paths_to_add)>self.MAX_PATHS:
                l_warning('only %s search paths allowed. Following are ignored:\n%s',self.MAX_PATHS, '\n'.join(paths_to_add[8:]))
            for path in paths_to_add[:self.MAX_PATHS]:
                if windows and path[-1]==':':
                    path += '\\'
                self.path_to_scan_add(abspath(path))

        run_scan_condition = bool(paths_to_add and not norun)

        if exclude:
            self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(exclude))
            self.cfg.set_bool(CFG_KEY_EXCLUDE_REGEXP,False)
        elif exclude_regexp:
            self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(exclude_regexp))
            self.cfg.set_bool(CFG_KEY_EXCLUDE_REGEXP,True)
        else:
            if run_scan_condition:
                self.cfg.set(CFG_KEY_EXCLUDE,'')

        self.exclude_regexp_scan.set(self.cfg_get_bool(CFG_KEY_EXCLUDE_REGEXP))

        self.main_locked_by_child = None

        self_main.deiconify()

        self.preview_auto_update_bool = self.cfg_get_bool(CFG_KEY_PREVIEW_AUTO_UPDATE)

        self.paned.update()
        self.paned.sash_place(0,0,self.cfg_get('sash_coord',400,section='geometry'))

        #prevent displacement
        if cfg_geometry :
            self_main.geometry(cfg_geometry)

        self.main_update()

        self.scan_dialog_show(run_scan_condition)

        self_groups_tree.focus_set()

        if self.cfg.get_bool(CFG_KEY_SHOW_PREVIEW):
            self.show_preview()

        gc_collect()
        gc_enable()

        self.processing_on()

        self_main.mainloop()
        #######################################################################

    hg_index = 0

    def get_hg_ico(self):
        self.hg_index=(self.hg_index+1) % self.hg_ico_len
        return self.hg_ico[self.hg_index]

    def use_size_min_change(self):
        self.image_min_Entry.configure(state='normal' if self.image_min_size_check_var.get() else 'disabled')

    def use_size_max_change(self):
        self.image_max_Entry.configure(state='normal' if self.image_max_size_check_var.get() else 'disabled')

    def use_size_min_change_file(self):
        self.file_min_Entry.configure(state='normal' if self.file_min_size_check_var.get() else 'disabled')

    def use_size_max_change_file(self):
        self.file_max_Entry.configure(state='normal' if self.file_max_size_check_var.get() else 'disabled')

    def operation_mode_change(self):
        operation_mode = self.operation_mode_var.get()
        if operation_mode==MODE_CRC:
            self.similarity_hsize_scale.configure(state='disabled')
            self.similarity_distance_scale.configure(state='disabled')

            self.similarity_distance_label_val.configure(state='disabled')

            self.similarity_hsize_label_val.configure(state='disabled')

            self.all_rotations_check.configure(state='disabled')
            self.image_min_Entry.configure(state='disabled')
            self.image_min_check.configure(state='disabled')
            self.image_max_check.configure(state='disabled')
            self.image_max_Entry.configure(state='disabled')
        elif operation_mode==MODE_SIMILARITY:
            self.similarity_hsize_scale.configure(state='normal')
            self.similarity_distance_scale.configure(state='normal')

            self.similarity_distance_label_val.configure(state='normal')

            self.similarity_hsize_label_val.configure(state='normal')

            self.all_rotations_check.configure(state='normal')
            self.image_min_check.configure(state='normal')
            self.image_max_check.configure(state='normal')

            self.use_size_min_change()
            self.use_size_max_change()
        elif operation_mode==MODE_GPS:
            self.similarity_hsize_scale.configure(state='disabled')
            self.similarity_distance_scale.configure(state='normal')

            self.similarity_distance_label_val.configure(state='normal')

            self.similarity_hsize_label_val.configure(state='disabled')

            self.all_rotations_check.configure(state='disabled')
            self.image_min_check.configure(state='normal')
            self.image_max_check.configure(state='normal')

            self.use_size_min_change()
            self.use_size_max_change()
        else:
            print('unknown operation_mode:',operation_mode)

        self.use_size_min_change_file()
        self.use_size_max_change_file()

    def distance_val_set(self):
        self.similarity_distance_var_lab.set(str(self.similarity_distance_var.get())[:4])

    def hsize_val_set(self):
        self.similarity_hsize_varx2.set(self.similarity_hsize_var.get()*2)
        self.similarity_hsize_var_lab.set(str(self.similarity_hsize_varx2.get()))

    def main_drop(self, data):
        self.scan_dialog_drop(data)
        self.main.after_idle(lambda : self.scan_dialog_show())

    def scan_dialog_drop(self, data):
        for path in self.main.splitlist(data):
            p_path = normpath(abspath(path))

            if path_exists(p_path):
                if isdir(p_path):
                    self.path_to_scan_add(p_path)
                else:
                    self.path_to_scan_add(dirname(p_path))
            else:
                self.get_info_dialog_on_main().show('Path does not exist',str(p_path))

    def pre_show(self,on_main_window_dialog=True,new_widget=None):
        self.processing_off(f'pre_show:{new_widget}')

        self.menubar_unpost()
        self.hide_tooltip()
        self.popup_groups_unpost()
        self.popup_folder_unpost()

        if on_main_window_dialog:
            if new_widget:
                self.main_locked_by_child=new_widget

    def post_close(self,on_main_window_dialog=True):
        if on_main_window_dialog:
            self.main_locked_by_child=None

        self.processing_on()

    def pre_show_settings(self,on_main_window_dialog=True,new_widget=None):
        _ = {var.set(self.cfg_get_bool(key)) for var,key in self.settings}
        _ = {var.set(self.cfg_get(key)) for var,key in self.settings_str}
        return self.pre_show(on_main_window_dialog=on_main_window_dialog,new_widget=new_widget)

    type_info_or_help={}
    def widget_tooltip(self,widget,message,type_info_or_help=True):
        self.type_info_or_help[widget,message] = type_info_or_help
        widget.bind("<Motion>", lambda event : self.motion_on_widget(event,message))
        widget.bind("<Leave>", lambda event : self.widget_leave())

    def fix_text_dialog(self,dialog):
        dialog.find_lab.configure(image=self.ico_search_text,text=' Search:',compound='left',bg=self.bg_color)
        dialog.find_prev_butt.configure(image=self.ico_left)
        dialog.find_next_butt.configure(image=self.ico_right)

        self.widget_tooltip(dialog.find_prev_butt,'Find Prev (Shift+F3)')
        self.widget_tooltip(dialog.find_next_butt,'Find Next (F3)')
        self.widget_tooltip(dialog.find_cs,'Case Sensitive')
        self.widget_tooltip(dialog.find_info_lab,'index of the selected search result / search results total ')

        dialog.find_var.set( self.cfg_get(CFG_KEY_SEARCH_TXT_STRING) )
        dialog.find_cs_var.set( self.cfg_get_bool(CFG_KEY_SEARCH_TXT_CS) )

    def store_text_dialog_fields(self,dialog):
        self.cfg.set(CFG_KEY_SEARCH_TXT_STRING,dialog.find_var.get())
        self.cfg.set_bool(CFG_KEY_SEARCH_TXT_CS,dialog.find_cs_var.get())

    #######################################################################
    settings_dialog_created = False
    @restore_status_line
    @block
    def get_settings_dialog(self):
        if not self.settings_dialog_created:
            self.status("Creating dialog ...")

            self.settings_dialog=GenericDialog(self.main,self.main_icon_tuple,self.bg_color,'Settings',pre_show=self.pre_show_settings,post_close=self.post_close)

            self.show_full_crc = BooleanVar()
            self.show_tooltips_info = BooleanVar()
            self.show_tooltips_help = BooleanVar()
            self.preview_auto_update = BooleanVar()

            self.show_full_paths = BooleanVar()
            self.show_mode = StringVar()

            self.create_relative_symlinks = BooleanVar()
            self.erase_empty_directories = BooleanVar()
            self.abort_on_error = BooleanVar()
            self.send_to_trash = BooleanVar()

            self.allow_delete_all = BooleanVar()
            self.skip_incorrect_groups = BooleanVar()
            self.allow_delete_non_duplicates = BooleanVar()

            self.confirm_show_crc_and_size = BooleanVar()

            self.confirm_show_links_targets = BooleanVar()
            self.file_open_wrapper = StringVar()
            self.folders_open_wrapper = StringVar()
            self.folders_open_wrapper_params = StringVar()

            self.settings = [
                (self.show_full_crc,CFG_KEY_FULL_CRC),
                (self.show_tooltips_info,CFG_KEY_SHOW_TOOLTIPS_INFO),
                (self.show_tooltips_help,CFG_KEY_SHOW_TOOLTIPS_HELP),
                (self.preview_auto_update,CFG_KEY_PREVIEW_AUTO_UPDATE),
                (self.show_full_paths,CFG_KEY_FULL_PATHS),
                (self.create_relative_symlinks,CFG_KEY_REL_SYMLINKS),
                (self.erase_empty_directories,CFG_ERASE_EMPTY_DIRS),
                (self.abort_on_error,CFG_ABORT_ON_ERROR),
                (self.send_to_trash,CFG_SEND_TO_TRASH),
                (self.confirm_show_crc_and_size,CFG_CONFIRM_SHOW_CRCSIZE),
                (self.confirm_show_links_targets,CFG_CONFIRM_SHOW_LINKSTARGETS),
                (self.allow_delete_all,CFG_ALLOW_DELETE_ALL),
                (self.skip_incorrect_groups,CFG_SKIP_INCORRECT_GROUPS),
                (self.allow_delete_non_duplicates,CFG_ALLOW_DELETE_NON_DUPLICATES)
            ]
            self.settings_str = [
                (self.show_mode,CFG_KEY_SHOW_MODE),
                (self.file_open_wrapper,CFG_KEY_WRAPPER_FILE),
                (self.folders_open_wrapper,CFG_KEY_WRAPPER_FOLDERS),
                (self.folders_open_wrapper_params,CFG_KEY_WRAPPER_FOLDERS_PARAMS)
            ]

            row = 0

            label_frame=LabelFrame(self.settings_dialog.area_main, text="Results display mode",borderwidth=2,bg=self.bg_color)
            label_frame.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

            self_widget_tooltip = self.widget_tooltip
            (cb_30:=Radiobutton(label_frame, text = 'All (default)', variable=self.show_mode,value='0')).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
            self_widget_tooltip(cb_30,'Show all results')

            (cb_3:=Radiobutton(label_frame, text = 'Cross paths', variable=self.show_mode,value='1')).grid(row=0,column=1,sticky='wens',padx=3,pady=2)
            self_widget_tooltip(cb_3,'Ignore (hide) groups containing duplicates in only one search path.\nShow only groups with files in different search paths.\nIn this mode, you can treat one search path as a "reference"\nand delete duplicates in all other paths with ease')

            (cb_3a:=Radiobutton(label_frame, text = 'Same directory', variable=self.show_mode,value='2')).grid(row=0,column=2,sticky='wens',padx=3,pady=2)
            self_widget_tooltip(cb_3a,'Show only groups with result files in the same directory')

            label_frame.grid_columnconfigure((0,1,2), weight=1)

            label_frame=LabelFrame(self.settings_dialog.area_main, text="Main panels and dialogs",borderwidth=2,bg=self.bg_color)
            label_frame.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

            (cb_1:=Checkbutton(label_frame, text = 'Show full CRC', variable=self.show_full_crc)).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
            self_widget_tooltip(cb_1,'If disabled, shortest necessary prefix of full CRC wil be shown')

            (cb_2:=Checkbutton(label_frame, text = 'Show full scan paths', variable=self.show_full_paths)).grid(row=1,column=0,sticky='wens',padx=3,pady=2)
            self_widget_tooltip(cb_2,'If disabled, scan path symbols will be shown instead of full paths\nfull paths are always displayed as tooltips')

            Checkbutton(label_frame, text = 'Show info tooltips', variable=self.show_tooltips_info).grid(row=2,column=0,sticky='wens',padx=3,pady=2)
            Checkbutton(label_frame, text = 'Show help tooltips', variable=self.show_tooltips_help).grid(row=3,column=0,sticky='wens',padx=3,pady=2)

            (preview_auto_update_cb:=Checkbutton(label_frame, text = 'Preview auto update', variable=self.preview_auto_update)).grid(row=4,column=0,sticky='wens',padx=3,pady=2)
            self_widget_tooltip(preview_auto_update_cb,'If enabled, any change of the selection\nwill automatically update the preview\nwindow (if the format is supported)')

            label_frame=LabelFrame(self.settings_dialog.area_main, text="Confirmation dialogs",borderwidth=2,bg=self.bg_color)
            label_frame.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

            (cb_3:=Checkbutton(label_frame, text = 'Skip groups with invalid selection', variable=self.skip_incorrect_groups)).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
            self_widget_tooltip(cb_3,'Groups with incorrect marks set will abort action.\nEnable this option to skip those groups.\nFor delete or soft-link action, one file in a group \nmust remain unmarked (see below). For hardlink action,\nmore than one file in a group must be marked.')

            (cb_4:=Checkbutton(label_frame, text = 'Allow deletion of all copies', variable=self.allow_delete_all,image=self.ico_warning,compound='right')).grid(row=1,column=0,sticky='wens',padx=3,pady=2)
            self_widget_tooltip(cb_4,'Before deleting selected files, files selection in every CRC \ngroup is checked, at least one file should remain unmarked.\nIf This option is enabled it will be possible to delete all copies')

            Checkbutton(label_frame, text = 'Show soft links targets', variable=self.confirm_show_links_targets ).grid(row=2,column=0,sticky='wens',padx=3,pady=2)
            Checkbutton(label_frame, text = 'Show CRC/GROUP and size', variable=self.confirm_show_crc_and_size ).grid(row=3,column=0,sticky='wens',padx=3,pady=2)

            label_frame=LabelFrame(self.settings_dialog.area_main, text="Processing",borderwidth=2,bg=self.bg_color)
            label_frame.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

            Checkbutton(label_frame, text = 'Create relative symbolic links', variable=self.create_relative_symlinks).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
            Checkbutton(label_frame, text = 'Send Files to %s instead of deleting them' % ('Recycle Bin' if windows else 'Trash'), variable=self.send_to_trash ).grid(row=1,column=0,sticky='wens',padx=3,pady=2)
            Checkbutton(label_frame, text = 'Erase remaining empty directories', variable=self.erase_empty_directories).grid(row=2,column=0,sticky='wens',padx=3,pady=2)
            Checkbutton(label_frame, text = 'Abort on first error', variable=self.abort_on_error).grid(row=3,column=0,sticky='wens',padx=3,pady=2)

            #Checkbutton(fr, text = 'Allow to delete regular files (WARNING!)', variable=self.allow_delete_non_duplicates        ).grid(row=row,column=0,sticky='wens',padx=3,pady=2)

            label_frame=LabelFrame(self.settings_dialog.area_main, text="Opening wrappers",borderwidth=2,bg=self.bg_color)
            label_frame.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

            Label(label_frame,text='parameters #',bg=self.bg_color,anchor='n').grid(row=0, column=2,sticky='news')

            Label(label_frame,text='File: ',bg=self.bg_color,anchor='w').grid(row=1, column=0,sticky='news')
            (en_1:=Entry(label_frame,textvariable=self.file_open_wrapper)).grid(row=1, column=1,sticky='news',padx=3,pady=2)
            self_widget_tooltip(en_1,'Command executed on "Open File" with full file path as parameter.\nIf empty, default os association will be executed.')

            Label(label_frame,text='Folders: ',bg=self.bg_color,anchor='w').grid(row=2, column=0,sticky='news')
            (en_2:=Entry(label_frame,textvariable=self.folders_open_wrapper)).grid(row=2, column=1,sticky='news',padx=3,pady=2)
            self_widget_tooltip(en_2,'Command executed on "Open Folder" with full path as parameter.\nIf empty, default os filemanager will be used.')

            (cb_2:=Combobox(label_frame,values=('1','2','3','4','5','6','7','8','all'),textvariable=self.folders_open_wrapper_params,state='readonly') ).grid(row=2, column=2,sticky='ew',padx=3)
            self_widget_tooltip(cb_2,'Number of parameters (paths) passed to\n"Opening wrapper" (if defined) when action\nis performed on groups\ndefault is 2')

            label_frame.grid_columnconfigure(1, weight=1)

            bfr=Frame(self.settings_dialog.area_main,bg=self.bg_color)
            self.settings_dialog.area_main.grid_rowconfigure(row, weight=1); row+=1

            bfr.grid(row=row,column=0) ; row+=1

            Button(bfr, text='Set defaults',width=14, command=self.settings_reset).pack(side='left', anchor='n',padx=5,pady=5)
            Button(bfr, text='OK', width=14, command=self.settings_ok ).pack(side='left', anchor='n',padx=5,pady=5,fill='both')
            self.cancel_button=Button(bfr, text='Cancel', width=14 ,command=self.settings_dialog.hide )
            self.cancel_button.pack(side='right', anchor='n',padx=5,pady=5)

            self.settings_dialog.area_main.grid_columnconfigure(0, weight=1)

            self.settings_dialog_created = True

        return self.settings_dialog

    info_dialog_on_main_created = False
    @restore_status_line
    @block
    def get_info_dialog_on_main(self):
        if not self.info_dialog_on_main_created:
            self.status("Creating dialog ...")

            self.info_dialog_on_main = LabelDialog(self.main,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)

            self.info_dialog_on_main_created = True

        return self.info_dialog_on_main

    text_ask_dialog_created = False
    @restore_status_line
    @block
    def get_text_ask_dialog(self):
        if not self.text_ask_dialog_created:
            self.status("Creating dialog ...")

            self.text_ask_dialog = TextDialogQuestion(self.main,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close,image=self.ico_warning)
            self.fix_text_dialog(self.text_ask_dialog)

            self.text_ask_dialog_created = True

        return self.text_ask_dialog

    text_info_dialog_created = False
    @restore_status_line
    @block
    def get_text_info_dialog(self):
        if not self.text_info_dialog_created:
            self.status("Creating dialog ...")

            self.text_info_dialog = TextDialogInfo(self.main,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)
            self.fix_text_dialog(self.text_info_dialog)

            self.text_info_dialog_created = True

        return self.text_info_dialog

    info_dialog_on_scan_created = False
    @restore_status_line
    @block
    def get_info_dialog_on_scan(self):
        if not self.info_dialog_on_scan_created:
            self.status("Creating dialog ...")

            self.info_dialog_on_scan = LabelDialog(self.scan_dialog.widget,self.main_icon_tuple,self.bg_color,pre_show=lambda new_widget : self.pre_show(on_main_window_dialog=False,new_widget=new_widget),post_close=lambda : self.post_close(False))

            self.info_dialog_on_scan_created = True

        return self.info_dialog_on_scan

    exclude_dialog_on_scan_created = False
    @restore_status_line
    @block
    def get_exclude_dialog_on_scan(self):
        if not self.exclude_dialog_on_scan_created:
            self.status("Creating dialog ...")

            self.exclude_dialog_on_scan = EntryDialogQuestion(self.scan_dialog.widget,self.main_icon_tuple,self.bg_color,pre_show=lambda new_widget : self.pre_show(on_main_window_dialog=False,new_widget=new_widget),post_close=lambda : self.post_close(False))
            self.exclude_dialog_on_scan_created = True

        return self.exclude_dialog_on_scan

    progress_dialog_on_scan_created = False
    @restore_status_line
    @block
    def get_progress_dialog_on_scan(self):
        if not self.progress_dialog_on_scan_created:
            self.status("Creating dialog ...")

            self.progress_dialog_on_scan = ProgressDialog(self.scan_dialog.widget,self.main_icon_tuple,self.bg_color,pre_show=lambda new_widget : self.pre_show(on_main_window_dialog=False,new_widget=new_widget),post_close=lambda : self.post_close(False))
            self.progress_dialog_on_scan.command_on_close = self.progress_dialog_abort

            self.progress_dialog_on_scan.abort_button.bind("<Leave>", lambda event : self.widget_leave())
            self.progress_dialog_on_scan.abort_button.bind("<Motion>", lambda event : self.motion_on_widget(event) )

            self.progress_dialog_on_scan_created = True

        return self.progress_dialog_on_scan

    progress_dialog_on_main_created = False
    @restore_status_line
    @block
    def get_progress_dialog_on_main(self):
        if not self.progress_dialog_on_main_created:
            self.status("Creating dialog ...")

            self.progress_dialog_on_main = ProgressDialog(self.main,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)
            self.progress_dialog_on_main.command_on_close = self.progress_dialog_abort

            self.progress_dialog_on_main.abort_button.pack_forget()

            #self.progress_dialog_on_main.abort_button.bind("<Leave>", lambda event : self.widget_leave())
            #self.progress_dialog_on_main.abort_button.bind("<Motion>", lambda event : self.motion_on_widget(event,'processing...') )

            self.progress_dialog_on_main_created = True

        return self.progress_dialog_on_main


    mark_dialog_on_groups_created = False
    @restore_status_line
    @block
    def get_mark_dialog_on_groups(self):
        if not self.mark_dialog_on_groups_created:
            self.status("Creating dialog ...")

            self.mark_dialog_on_groups = CheckboxEntryDialogQuestion(self.groups_tree,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)
            self.mark_dialog_on_groups_created = True
            self.get_info_dialog_on_mark_groups()

        return self.mark_dialog_on_groups

    mark_dialog_on_folder_created = False
    @restore_status_line
    @block
    def get_mark_dialog_on_folder(self):
        if not self.mark_dialog_on_folder_created:
            self.status("Creating dialog ...")

            self.mark_dialog_on_folder = CheckboxEntryDialogQuestion(self.folder_tree,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)
            self.mark_dialog_on_folder_created = True
            self.get_info_dialog_on_mark_folder()

        return self.mark_dialog_on_folder

    info_dialog_on_mark_groups_created = False
    @restore_status_line
    @block
    def get_info_dialog_on_mark_groups(self):
        if not self.info_dialog_on_mark_groups_created:
            self.status("Creating dialog ...")

            self.info_dialog_on_mark[self.groups_tree] = LabelDialog(self.mark_dialog_on_groups.widget,self.main_icon_tuple,self.bg_color,pre_show=lambda new_widget: self.pre_show(on_main_window_dialog=False,new_widget=new_widget),post_close=lambda : self.post_close(False))
            self.info_dialog_on_mark_groups_created = True

        return self.info_dialog_on_mark[self.groups_tree]

    info_dialog_on_mark_folder_created = False
    @restore_status_line
    @block
    def get_info_dialog_on_mark_folder(self):
        if not self.info_dialog_on_mark_folder_created:
            self.status("Creating dialog ...")

            self.info_dialog_on_mark[self.folder_tree] = LabelDialog(self.mark_dialog_on_folder.widget,self.main_icon_tuple,self.bg_color,pre_show=lambda new_widget: self.pre_show(on_main_window_dialog=False,new_widget=new_widget),post_close=lambda : self.post_close(False))
            self.info_dialog_on_mark_folder_created = True

        return self.info_dialog_on_mark[self.folder_tree]

    find_dialog_on_groups_created = False
    @restore_status_line
    @block
    def get_find_dialog_on_groups(self):
        if not self.find_dialog_on_groups_created:
            self.status("Creating dialog ...")

            self.find_dialog_on_groups = FindEntryDialog(self.groups_tree,self.main_icon_tuple,self.bg_color,self.find_mod,self.find_prev_from_dialog,self.find_next_from_dialog,pre_show=self.pre_show,post_close=self.post_close)
            self.info_dialog_on_find[self.groups_tree] = LabelDialog(self.find_dialog_on_groups.widget,self.main_icon_tuple,self.bg_color,pre_show=lambda new_widget: self.pre_show(on_main_window_dialog=False,new_widget=new_widget),post_close=lambda : self.post_close(False))
            self.find_dialog_on_groups_created = True

        return self.find_dialog_on_groups

    find_dialog_on_folder_created = False
    @restore_status_line
    @block
    def get_find_dialog_on_folder(self):
        if not self.find_dialog_on_folder_created:
            self.status("Creating dialog ...")

            self.find_dialog_on_folder = FindEntryDialog(self.folder_tree,self.main_icon_tuple,self.bg_color,self.find_mod,self.find_prev_from_dialog,self.find_next_from_dialog,pre_show=self.pre_show,post_close=self.post_close)
            self.info_dialog_on_find[self.folder_tree] = LabelDialog(self.find_dialog_on_folder.widget,self.main_icon_tuple,self.bg_color,pre_show=lambda new_widget: self.pre_show(on_main_window_dialog=False,new_widget=new_widget),post_close=lambda : self.post_close(False))
            self.find_dialog_on_folder_created = True

        return self.find_dialog_on_folder

    about_dialog_created = False
    @restore_status_line
    @block
    def get_about_dialog(self):
        if not self.about_dialog_created:
            self.status("Creating dialog ...")

            self.about_dialog = GenericDialog(self.main,self.main_icon_tuple,self.bg_color,'',pre_show=self.pre_show,post_close=self.post_close)

            frame1 = LabelFrame(self.about_dialog.area_main,text='',bd=2,bg=self.bg_color,takefocus=False)
            frame1.grid(row=0,column=0,sticky='news',padx=4,pady=(4,2))
            self.about_dialog.area_main.grid_rowconfigure(1, weight=1)

            text= f'\n\nDUDE (DUplicates DEtector) {VER_TIMESTAMP}\nAuthor: Piotr Jochymek\n\n{HOMEPAGE}\n\nPJ.soft.dev.x@gmail.com\n\n'

            Label(frame1,text=text,bg=self.bg_color,justify='center').pack(expand=1,fill='both')

            frame2 = LabelFrame(self.about_dialog.area_main,text='',bd=2,bg=self.bg_color,takefocus=False)
            frame2.grid(row=1,column=0,sticky='news',padx=4,pady=(2,4))
            lab2_text=  'LOGS DIRECTORY     :  ' + LOG_DIR + '\n' + \
                        'SETTINGS DIRECTORY :  ' + CONFIG_DIR + '\n' + \
                        'CACHE DIRECTORY    :  ' + CACHE_DIR + '\n\n' + \
                        'Current log file   :  ' + log_file + '\n\n' + distro_info

            lab_courier = Label(frame2,text=lab2_text,bg=self.bg_color,justify='left')
            lab_courier.pack(expand=1,fill='both')

            try:
                lab_courier.configure(font=('Courier', 10))
            except:
                try:
                    lab_courier.configure(font=('TkFixedFont', 10))
                except:
                    pass

            self.about_dialog_created = True

        return self.about_dialog

    license_dialog_created = False
    @restore_status_line
    @block
    def get_license_dialog(self):
        if not self.license_dialog_created:
            self.status("Creating dialog ...")

            try:
                self.license=Path(path_join(DUDE_DIR,'LICENSE')).read_text(encoding='ASCII')
            except Exception as exception_lic:
                l_error(exception_lic)
                try:
                    self.license=Path(path_join(dirname(DUDE_DIR),'LICENSE')).read_text(encoding='ASCII')
                except Exception as exception_2:
                    l_error(exception_2)
                    self.exit()

            self.license_dialog = GenericDialog(self.main,(self.ico['license'],self.ico['license']),self.bg_color,'',pre_show=self.pre_show,post_close=self.post_close,min_width=800,min_height=520)

            frame1 = LabelFrame(self.license_dialog.area_main,text='',bd=2,bg=self.bg_color,takefocus=False)
            frame1.grid(row=0,column=0,sticky='news',padx=4,pady=4)
            self.license_dialog.area_main.grid_rowconfigure(0, weight=1)

            lab_courier=Label(frame1,text=self.license,bg=self.bg_color,justify='center')
            lab_courier.pack(expand=1,fill='both')

            try:
                lab_courier.configure(font=('Courier', 10))
            except:
                try:
                    lab_courier.configure(font=('TkFixedFont', 10))
                except:
                    pass

            self.license_dialog_created = True

        return self.license_dialog

    #########################################

    def semi_selection(self,tree,item):
        #print(f'semi_selection:{tree},{item}')
        if tree==self.main.focus_get():
            tree.focus(item)
        else:
            tree.selection_set(item)

        self.selected[tree]=item
        #print(f'semi_selection:{tree},{item},end')

    @catched
    def groups_tree_focus_out(self):
        tree = self.groups_tree
        item=tree.focus()
        if item:
            tree.selection_set(item)
            self.selected[tree]=item

    @catched
    def folder_tree_focus_out(self):
        tree = self.folder_tree
        item = tree.focus()
        if item:
            tree.selection_set(item)
            self.selected[tree]=item

    def groups_tree_focus_in(self):
        try:
            self.sel_tree = tree = self.groups_tree

            if item:=self.selected[tree]:
                tree.focus(item)
                tree.selection_remove(item)
                self.groups_tree_sel_change(item,True)

                self.preview_preload_groups_tree(item)

            tree.configure(style='semi_focus.Treeview')
            self.other_tree[tree].configure(style='no_focus.Treeview')
        except Exception as e:
            l_error(f'groups_tree_focus_in:{e}')

    def folder_tree_focus_in(self):
        try:
            self.sel_tree = tree = self.folder_tree

            if item:=self.selected[tree]:
                tree.focus(item)
                tree.selection_remove(item)
                self.preview_preload_folder_tree(item)

            tree.configure(style='semi_focus.Treeview')
            self.other_tree[tree].configure(style='no_focus.Treeview')
        except Exception as e:
            l_error(f'folder_tree_focus_in:{e}')

    def focusin(self):
        if self.main_locked_by_child:
            self.main_locked_by_child.focus_set()

        self_main = self.main
        self_main.lift()
        self_main.attributes('-topmost',True)
        self_main.after_idle(self.main.attributes,'-topmost',False)

        if self.preview_shown:
            self_preview = self.preview

            self_preview.lift()
            self_preview.attributes('-topmost',True)
            self_preview.after_idle(self_preview.attributes,'-topmost',False)

    def unpost(self):
        self.hide_tooltip()
        self.menubar_unpost()
        #self.popup_groups_unpost()
        #self.popup_folder_unpost()

    tooltip_show_after_groups=''
    tooltip_show_after_folder=''
    tooltip_show_after_widget=''

    def widget_leave(self):
        self.menubar_unpost()
        self.hide_tooltip()

    def motion_on_widget(self,event,message=None):
        widget = event.widget

        try:
            if self.type_info_or_help[widget,message]==False:
                #info
                allowed=self.cfg_get_bool(CFG_KEY_SHOW_TOOLTIPS_INFO)
            else:
                #help
                allowed=self.cfg_get_bool(CFG_KEY_SHOW_TOOLTIPS_HELP)
        except:
            allowed=False

        if allowed:
            if message:
                self.tooltip_message[str(widget)]=message
            self.tooltip_show_after_widget = widget.after(1, self.show_tooltip_widget(event))

    def motion_on_groups_tree(self,event):
        if not self.block_processing_stack:
            if self.cfg_get_bool(CFG_KEY_SHOW_TOOLTIPS_INFO):
                self.tooltip_show_after_groups = event.widget.after(1, self.show_tooltip_groups(event))

    def motion_on_folder_tree(self,event):
        if not self.block_processing_stack:
            if self.cfg_get_bool(CFG_KEY_SHOW_TOOLTIPS_INFO):
                self.tooltip_show_after_folder = event.widget.after(1, self.show_tooltip_folder(event))

    def configure_tooltip(self,widget):
        self.tooltip_lab_configure(text=self.tooltip_message[str(widget)])

    def adaptive_tooltip_geometry(self,event):
        x,y = self.tooltip_wm_geometry().split('+')[0].split('x')
        x_int=int(x)
        y_int=int(y)

        size_combo,x_main_off,y_main_off = self.main_wm_geometry().split('+')
        x_main_size,y_main_size = size_combo.split('x')

        x_middle = int(x_main_size)/2+int(x_main_off)
        y_middle = int(y_main_size)/2+int(y_main_off)

        if event.x_root>x_middle:
            x_mod = -x_int -20
        else:
            x_mod = 20

        if event.y_root>y_middle:
            y_mod = -y_int -5
        else:
            y_mod = 5

        self.tooltip_wm_geometry("+%d+%d" % (event.x_root + x_mod, event.y_root + y_mod))

    def show_tooltip_widget(self,event):
        self.unschedule_tooltip_widget(event)
        self.menubar_unpost()

        self.configure_tooltip(event.widget)

        self.tooltip_deiconify()
        self.adaptive_tooltip_geometry(event)

    def show_tooltip_groups(self,event):
        self.unschedule_tooltip_groups(event)
        self.menubar_unpost()

        tree = event.widget
        col=tree.identify_column(event.x)
        if col:
            colname=tree.column(col,'id')
            if tree.identify("region", event.x, event.y) == 'heading':
                if colname in ('path','size_h','file','instances_h','ctime_h'):
                    if self.cfg_get_bool(CFG_KEY_SHOW_TOOLTIPS_HELP):
                        self.tooltip_lab_configure(text='Sort by %s' % self.org_label[colname])
                        self.tooltip_deiconify()
                else:
                    self.hide_tooltip()

            elif item := tree.identify('item', event.x, event.y):
                try:
                    kind,size,crc, (pathnr,path,file,ctime,dev,inode) = self.groups_tree_item_to_data[item]

                    if col=="#0" :
                        if pathnr:
                            if kind==self.FILE:
                                self.tooltip_lab_configure(text='%s - %s' % (pathnr+1,dude_core.scanned_paths[pathnr]) )
                                self.tooltip_deiconify()
                        else:
                            if kind==self.FILE:
                                self.tooltip_lab_configure(text=f'{pathnr+1} = {dude_core.scanned_paths[pathnr]}' )
                                self.tooltip_deiconify()
                            else:
                                crc=item
                                if self.operation_mode:
                                    self.tooltip_lab_configure(text='GROUP: %s' % crc )
                                else:
                                    self.tooltip_lab_configure(text='CRC: %s' % crc )

                                self.tooltip_deiconify()

                    elif col:

                        coldata=tree.set(item,col)

                        if coldata:
                            self.tooltip_lab_configure(text=coldata)
                            self.tooltip_deiconify()

                        else:
                            self.hide_tooltip()

                except Exception as mte:
                    print(f'show_tooltip_groups:{mte}')

        self.adaptive_tooltip_geometry(event)

    def show_tooltip_folder(self,event):
        self.unschedule_tooltip_folder(event)
        self.menubar_unpost()

        tree = event.widget
        col=tree.identify_column(event.x)
        if col:
            colname=tree.column(col,'id')
            if tree.identify("region", event.x, event.y) == 'heading':
                if colname in ('size_h','file','instances_h','ctime_h'):
                    if self.cfg_get_bool(CFG_KEY_SHOW_TOOLTIPS_HELP):
                        self.tooltip_lab_configure(text='Sort by %s' % self.org_label[colname])
                        self.tooltip_deiconify()
                else:
                    self.hide_tooltip()
            elif item := tree.identify('item', event.x, event.y):

                coldata=''
                kind=tree.set(item,3)
                if kind==self.LINK:
                    coldata='(soft-link)'
                elif kind==self.DIRLINK:
                    coldata='(directory soft-link)'

                if col=="#0" :
                    pass
                elif col:
                    coldata = coldata + ' ' + tree.set(item,col)

                if coldata:
                    self.tooltip_lab_configure(text=coldata)
                    self.tooltip_deiconify()
                else:
                    self.hide_tooltip()

        self.adaptive_tooltip_geometry(event)

    def unschedule_tooltip_widget(self,event):
        if self.tooltip_show_after_widget:
            event.widget.after_cancel(self.tooltip_show_after_widget)
            self.tooltip_show_after_widget = None

    def unschedule_tooltip_groups(self,event):
        if self.tooltip_show_after_groups:
            event.widget.after_cancel(self.tooltip_show_after_groups)
            self.tooltip_show_after_groups = None

    def unschedule_tooltip_folder(self,event):
        if self.tooltip_show_after_folder:
            event.widget.after_cancel(self.tooltip_show_after_folder)
            self.tooltip_show_after_folder = None

    def hide_tooltip(self):
        self.tooltip_withdraw()

    status_curr_text='-'

    def status_main(self,text='',image='',do_log=True):
        if text != self.status_curr_text:

            self.status_curr_text=text
            self.status_line_lab_configure(text=text,image=image,compound='left')

            if do_log and text:
                l_info('STATUS:%s',text)
            self.status_line_lab_update()

    def status_main_win(self,text='',image='',do_log=True):
        self.status_main(text.replace('\\\\',chr(92)).replace('\\\\',chr(92)),image,do_log)

    status=status_main_win if windows else status_main

    menu_state_stack=[]
    menu_state_stack_pop = menu_state_stack.pop
    menu_state_stack_append = menu_state_stack.append

    def menu_enable(self):
        norm = self.menubar_norm
        try:
            self.menu_state_stack_pop()
            if not self.menu_state_stack:
                norm("File")
                norm("Navigation")
                norm("Help")
        except Exception as e:
            l_error(f'menu_enable error:{e}')

    def menu_disable(self):
        disable = self.menubar_disable

        self.menu_state_stack_append('x')
        disable("File")
        disable("Navigation")
        disable("Help")
        #self.menubar.update()

    def reset_sels(self):
        self.sel_path_full = ''
        self.sel_pathnr = None
        self.sel_path = None
        self.sel_file = None
        self.sel_crc = None
        self.sel_item = None

        self.sel_tree=self.groups_tree

        self.sel_kind = None

    def delete_window_wrapper(self):
        if not self.block_processing_stack:
            self.exit()
        else:
            self.status('WM_DELETE_WINDOW NOT exiting ...')

    def exit(self):
        try:
            self.cfg.set('main',str(self.main.geometry()),section='geometry')
            coords=self.paned.sash_coord(0)
            self.hide_preview(False)
            self.cfg.set('sash_coord',str(coords[1]),section='geometry')
            self.cfg.write()
        except Exception as e:
            l_error(e)

        self.status('exiting ...')
        #self.main.withdraw()
        sys.exit(0)
        #self.main.destroy()

    find_result=()
    find_params_changed=True

    find_by_tree={}
    find_by_tree_re={}

    def finder_wrapper_show(self):
        tree=self.sel_tree

        self.find_dialog_shown=True

        scope_info = 'Scope: All groups.' if self.sel_tree==self.groups_tree else 'Scope: Selected directory.'
        tree_index = self.tree_index[tree]

        cfg_key = CFG_KEY_FIND_STRING_0 if tree_index==0 else CFG_KEY_FIND_STRING_1
        cfg_key_re = CFG_KEY_FIND_RE_0 if tree_index==0 else CFG_KEY_FIND_RE_1

        if tree in self.find_by_tree:
            initialvalue=self.find_by_tree[tree]
        else:
            initialvalue=self.cfg.get(cfg_key)

        if tree in self.find_by_tree_re:
            initialvalue_re=self.find_by_tree_re[tree]
        else:
            initialvalue_re=self.cfg.get(cfg_key_re)

        if self.sel_tree==self.groups_tree:
            self.get_find_dialog_on_groups().show('Find',scope_info,initial=initialvalue,checkbutton_text='treat as a regular expression',checkbutton_initial=initialvalue_re)
            self.find_by_tree[tree]=self.find_dialog_on_groups.entry.get()
            self.find_by_tree_re[tree]=self.find_dialog_on_groups.check_val.get()
        else:
            self.get_find_dialog_on_folder().show('Find',scope_info,initial=initialvalue,checkbutton_text='treat as a regular expression',checkbutton_initial=initialvalue_re)
            self.find_by_tree[tree]=self.find_dialog_on_folder.entry.get()
            self.find_by_tree_re[tree]=self.find_dialog_on_folder.check_val.get()

        self.cfg.set(cfg_key,self.find_by_tree[tree])
        self.cfg.set_bool(cfg_key_re,self.find_by_tree_re[tree])

        self.find_dialog_shown=False
        tree.focus_set()

    def find_prev_from_dialog(self,expression,use_reg_expr):
        self.find_items(expression,use_reg_expr)
        self.select_find_result(-1)

    def find_prev(self):
        if not self.find_result or self.find_tree!=self.sel_tree:
            self.find_params_changed=True
            self.finder_wrapper_show()
        else:
            self.select_find_result(-1)

    def find_next_from_dialog(self,expression,use_reg_expr):
        self.find_items(expression,use_reg_expr)
        self.select_find_result(1)

    def find_next(self):
        if not self.find_result or self.find_tree!=self.sel_tree:
            self.find_params_changed=True
            self.finder_wrapper_show()
        else:
            self.select_find_result(1)

    find_result_index=0
    find_tree=''
    find_dialog_shown=False
    use_reg_expr_prev=''
    find_expression_prev=''

    def find_mod(self,expression,use_reg_expr):
        if self.use_reg_expr_prev!=use_reg_expr or self.find_expression_prev!=expression:
            self.use_reg_expr_prev=use_reg_expr
            self.find_expression_prev=expression
            self.find_params_changed=True
            self.find_result_index=0

    @restore_status_line
    def find_items(self,expression,use_reg_expr):
        self.status('finding ...')

        if self.find_params_changed or self.find_tree != self.sel_tree:
            self.find_tree=self.sel_tree

            items=[]
            items_append = items.append

            self_item_full_path = self.item_full_path

            if expression:
                if self.sel_tree==self.groups_tree:
                    crc_range = self.tree_children[self.groups_tree]

                    try:
                        for crc_item in crc_range:
                            for item in self.tree_children_sub[crc_item]:
                                fullpath = self_item_full_path(item)
                                if (use_reg_expr and search(expression,fullpath)) or (not use_reg_expr and fnmatch(fullpath,expression) ):
                                    items_append(item)
                    except Exception as e:
                        try:
                            self.info_dialog_on_find[self.find_tree].show('Error',str(e))
                        except Exception as e2:
                            print(e2)
                        return
                else:
                    try:
                        for item in self.current_folder_items:
                            file = self.current_folder_items_dict[item][0]

                            if (use_reg_expr and search(expression,file)) or (not use_reg_expr and fnmatch(file,expression) ):
                                items_append(item)
                    except Exception as e:
                        self.info_dialog_on_find[self.find_tree].show('Error',str(e))
                        return
            if items:
                self.find_result=tuple(items)
                self.find_params_changed=False
            else:
                self.find_result=()
                scope_info = 'Scope: All groups.' if self.find_tree==self.groups_tree else 'Scope: Selected directory.'
                self.info_dialog_on_find[self.find_tree].show(scope_info,'No files found.')

    def select_find_result(self,mod):
        if self.find_result:
            items_len=len(self.find_result)
            self.find_result_index+=mod
            next_item=self.find_result[self.find_result_index%items_len]

            if self.find_dialog_shown:
                #focus is still on find dialog
                self.semi_selection(self.find_tree,next_item)
            else:
                self.semi_selection(self.find_tree,next_item)

            self.find_tree.see(next_item)
            self.find_tree.update()

            if self.find_tree==self.groups_tree:
                self.groups_tree_sel_change(next_item)
            else:
                self.folder_tree_sel_change(next_item)

            if mod>0:
                self.status('Find next %s' % self.find_expression_prev)
            else:
                self.status('Find Previous %s' % self.find_expression_prev)

    def tag_toggle_selected(self,tree, *items):
        self_FILE=self.FILE
        self_CRC=self.CRC
        self_invert_mark=self.invert_mark

        self_groups_tree_item=self.groups_tree.item
        self_folder_tree_item=self.folder_tree.item
        tree_set=tree.set

        for item in items:
            if tree_set(item,'kind')==self_FILE:
                self_invert_mark(item, self.groups_tree)
                try:
                    self_folder_tree_item(item,tags=self_groups_tree_item(item)['tags'])
                except Exception :
                    pass
            elif tree_set(item,'kind')==self_CRC:
                self.tag_toggle_selected(tree, *self.tree_children_sub[item] )

        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    KEY_DIRECTION={}
    KEY_DIRECTION['Prior']=-1
    KEY_DIRECTION['Next']=1
    KEY_DIRECTION['Home']=0
    KEY_DIRECTION['End']=-1

    reftuple1=('1','2','3','4','5','6','7')
    reftuple2=('exclam','at','numbersign','dollar','percent','asciicircum','ampersand')

    @block
    def goto_next_prev_crc(self,direction):
        status ='selecting next group' if direction==1 else 'selecting prev group'

        tree=self.groups_tree
        self_sel_item = current_item = self.sel_item

        tree_set = tree.set

        self_CRC = self.CRC

        move_dict = self.my_next_dict[tree] if direction==1 else self.my_prev_dict[tree]

        while current_item:
            current_item = move_dict[current_item]
            if tree_set(current_item,'kind')==self_CRC:
                self.crc_select_and_focus(current_item)
                self.status(status,do_log=False)
                break
            if current_item==self_sel_item:
                self.status('%s ... (no file)' % status,do_log=False)
                break

    @block
    def goto_next_prev_duplicate_in_folder(self,direction):
        status = 'selecting next duplicate in folder' if direction==1 else 'selecting prev duplicate in folder'

        tree=self.folder_tree

        current_item = self.sel_item
        self_sel_item = self.sel_item

        tree_set = tree.set

        self_FILE = self.FILE

        move_dict = self.my_next_dict[tree] if direction==1 else self.my_prev_dict[tree]

        while current_item:
            current_item = move_dict[current_item]

            if tree_set(current_item,'kind')==self_FILE:
                self.semi_selection(tree,current_item)
                tree.see(current_item)
                self.folder_tree_sel_change(current_item)
                self.status(status,do_log=False)
                break

            if current_item==self_sel_item:
                self.status('%s ... (no file)' % status,do_log=False)
                break

    @catched
    def goto_first_last_crc(self,index):
        if children := self.tree_children[self.groups_tree]:
            if next_item:=children[index]:
                self.crc_select_and_focus(next_item,True)

    @catched
    def goto_first_last_dir_entry(self,index):
        if children := self.current_folder_items:
            if next_item:=children[index]:
                self.semi_selection(self.folder_tree,next_item)
                self.folder_tree_sel_change(next_item)
                self.folder_tree_see(next_item)
                self.folder_tree.update()

    @catched
    def key_press(self,event):
        if not self.block_processing_stack:
            self.main_unbind_class('Treeview','<KeyPress>')

            self.hide_tooltip()
            self.menubar_unpost()
            self.popup_groups_unpost()
            self.popup_folder_unpost()

            tree,key=event.widget,event.keysym
            try:
                item=tree.focus()

                if not item:
                    if children:=self.tree_children[tree]:
                        item=children[0]

                if key in ("Up","Down"):
                    if item:
                        new_item = self.my_next_dict[tree][item] if key=='Down' else self.my_prev_dict[tree][item]

                        if new_item:
                            tree.focus(new_item)
                            tree.see(new_item)

                            if tree==self.groups_tree:
                                self.groups_tree_sel_change(new_item)
                            else:
                                self.folder_tree_sel_change(new_item)

                elif key in ("Prior","Next"):
                    if tree==self.groups_tree:
                        self.goto_next_prev_crc(self.KEY_DIRECTION[key])
                    else:
                        self.goto_next_prev_duplicate_in_folder(self.KEY_DIRECTION[key])
                elif key in ("Home","End"):
                    if tree==self.groups_tree:
                        self.goto_first_last_crc(self.KEY_DIRECTION[key])
                    else:
                        self.goto_first_last_dir_entry(self.KEY_DIRECTION[key])
                elif key == "space":
                    if item:
                        if tree==self.groups_tree:
                            if self.sel_kind==self.CRC:
                                self.tag_toggle_selected(tree,*self.tree_children_sub[item])
                            else:
                                self.tag_toggle_selected(tree,item)
                        else:
                            self.tag_toggle_selected(tree,item)
                elif key == "Tab":
                    self.other_tree[tree].focus_set()
                elif key in ('KP_Multiply','asterisk'):
                    self.mark_on_all(self.invert_mark)
                else:
                    event_str=str(event)

                    #print(event.alt)

                    alt_pressed = ('0x20000' in event_str) if windows else ('Mod1' in event_str or 'Mod5' in event_str)
                    ctrl_pressed = 'Control' in event_str
                    shift_pressed = 'Shift' in event_str

                    if key=='F3':
                        if shift_pressed:
                            self.find_prev()
                        else:
                            self.find_next()
                    elif key == "Right":
                        self.goto_next_mark(tree,1,shift_pressed)
                    elif key == "Left":
                        self.goto_next_mark(tree,-1,shift_pressed)
                    elif key in ('KP_Add','plus'):
                        self.mark_expression(self.set_mark,'Mark files',ctrl_pressed)
                    elif key in ('KP_Subtract','minus'):
                        self.mark_expression(self.unset_mark,'Unmark files',ctrl_pressed)
                    elif key == "Delete":
                        if tree==self.groups_tree:
                            self.process_files_in_groups_wrapper(DELETE,ctrl_pressed)
                        else:
                            self.process_files_in_folder_wrapper(DELETE,self.sel_kind in (self.DIR,self.DIRLINK))
                    elif key == "Insert":
                        if not self.operation_mode:
                            action = WIN_LNK if shift_pressed and alt_pressed and windows else HARDLINK if shift_pressed else SOFTLINK

                            if tree==self.groups_tree:
                                self.process_files_in_groups_wrapper(action,ctrl_pressed)
                            else:
                                self.process_files_in_folder_wrapper(action,self.sel_kind in (self.DIR,self.DIRLINK))
                    elif key=='F5':
                        self.goto_max_folder(1,-1 if shift_pressed else 1)
                    elif key=='F6':
                        self.goto_max_folder(0,-1 if shift_pressed else 1)
                    elif key=='F7':
                        self.goto_max_group(1,-1 if shift_pressed else 1)
                    elif key=='F8':
                        self.goto_max_group(0,-1 if shift_pressed else 1)
                    elif key=='F9':
                        self.show_preview()
                    elif key=='F11':
                        self.hide_preview()
                    elif key=='BackSpace':
                        self.go_to_parent_dir()
                    elif key in ('i','I'):
                        if ctrl_pressed:
                            self.mark_on_all(self.invert_mark)
                        else:
                            if tree==self.groups_tree:
                                self.mark_in_group(self.invert_mark)
                            else:
                                self.mark_in_folder(self.invert_mark)
                    elif key in ('s','S'):
                        self.scan_dialog_show()
                    elif key in ('o','O'):
                        if ctrl_pressed:
                            if shift_pressed:
                                self.mark_all_by_ctime('oldest',self.unset_mark)
                            else:
                                self.mark_all_by_ctime('oldest',self.set_mark)
                        else:
                            if tree==self.groups_tree:
                                self.mark_in_group_by_ctime('oldest',self.invert_mark)
                    elif key in ('y','Y'):
                        if ctrl_pressed:
                            if shift_pressed:
                                self.mark_all_by_ctime('youngest',self.unset_mark)
                            else:
                                self.mark_all_by_ctime('youngest',self.set_mark)
                        else:
                            if tree==self.groups_tree:
                                self.mark_in_group_by_ctime('youngest',self.invert_mark)
                    elif key in ('c','C'):
                        if ctrl_pressed:
                            if shift_pressed:
                                self.clip_copy_file()
                            else:
                                self.clip_copy_full_path_with_file()
                        else:
                            self.clip_copy_full()

                    elif key in ('a','A'):
                        if tree==self.groups_tree:
                            if ctrl_pressed:
                                self.mark_on_all(self.set_mark)
                            else:
                                self.mark_in_group(self.set_mark)
                        else:
                            self.mark_in_folder(self.set_mark)

                    elif key in ('n','N'):
                        if tree==self.groups_tree:
                            if ctrl_pressed:
                                self.mark_on_all(self.unset_mark)
                            else:
                                self.mark_in_group(self.unset_mark)
                        else:
                            self.mark_in_folder(self.unset_mark)
                    elif key in ('d','D'):
                        if tree==self.folder_tree:
                            if shift_pressed:
                                self.sel_dir(self.unset_mark)
                            else:
                                self.sel_dir(self.set_mark)

                    elif key in ('r','R'):
                        if tree==self.folder_tree:

                            self.tree_folder_update()
                            self.folder_tree.focus_set()
                            try:
                                self.folder_tree.focus(self.sel_item)
                            except Exception :
                                pass
                    elif key in self.reftuple1:
                        index = self.reftuple1.index(key)

                        if index<len(dude_core.scanned_paths):
                            if tree==self.groups_tree:
                                self.action_on_path(dude_core.scanned_paths[index],self.set_mark,ctrl_pressed)
                    elif key in self.reftuple2:
                        index = self.reftuple2.index(key)

                        if index<len(dude_core.scanned_paths):
                            if tree==self.groups_tree:
                                self.action_on_path(dude_core.scanned_paths[index],self.unset_mark,ctrl_pressed)
                    elif key in ('KP_Divide','slash'):
                        if tree==self.groups_tree:
                            self.mark_subpath(self.set_mark,True)
                    elif key=='question':
                        if tree==self.groups_tree:
                            self.mark_subpath(self.unset_mark,True)
                    elif key in ('f','F'):
                        self.finder_wrapper_show()
                    elif key=='Return':
                        if item:
                            self.tree_action(tree,item,alt_pressed)
                    elif key=='F1':
                        self.get_about_dialog().show()
                    elif key=='F2':
                        self.get_settings_dialog().show()

            except Exception as e:
                l_error(f'key_press error:{e}')
                self.get_info_dialog_on_main().show('INTERNAL ERROR',f'key_press {key}\n' + str(e))

            self.main_bind_class('Treeview','<KeyPress>', self.key_press )

    def go_to_parent_dir(self):
        if self.sel_path_full :
            if self.two_dots_condition(self.sel_path_full):
                self.folder_tree.focus_set()
                head,tail=path_split(self.sel_path_full)
                self.enter_dir(normpath(str(Path(self.sel_path_full).parent.absolute())),tail)

#################################################
    def crc_select_and_focus(self,crc,try_to_show_all=False):
        if try_to_show_all:
            self.groups_tree_see(self.tree_children_sub[crc][-1])
            self.groups_tree.update()

        self.groups_tree.focus_set()
        self.groups_tree_focus(crc)
        self.groups_tree_see(crc)

        self.groups_tree.update()
        self.groups_tree_sel_change(crc)

    def tree_on_mouse_button_press(self,event,toggle=False):
        self.menubar_unpost()
        self.hide_tooltip()
        self.popup_groups_unpost()
        self.popup_folder_unpost()

        if not self.block_processing_stack:
            tree=event.widget

            region = tree.identify("region", event.x, event.y)

            if region == 'separator':
                return None

            if region == 'heading':
                if (colname:=tree.column(tree.identify_column(event.x),'id') ) in self.REAL_SORT_COLUMN:
                    self.column_sort_click(tree,colname)
            elif item:=tree.identify('item',event.x,event.y):
                tree.focus_set()
                tree.selection_remove(*tree.selection())

                self.selected[tree]=item
                tree.focus(item)

                if tree==self.groups_tree:
                    self.groups_tree_sel_change(item)
                else:
                    self.folder_tree_sel_change(item)

                if toggle:
                    self.tag_toggle_selected(tree,item)

                #prevents processing of expanding nodes
                #return "break"

        return "break"

    preview_photo_image_cache=None

    def preview_conf(self,event=None):
        if self.preview_shown:
            #print('preview_conf')

            #z eventu czasami idzie lewizna (start bez obrazka)
            geometry = self.preview.geometry()
            self.cfg.set('preview',str(geometry),section='geometry')

            new_window_size = tuple([int(x) for x in geometry.split('+')[0].split('x')])

            if self.preview_photo_image_cache:
                self.preview_photo_image_cache.set_window_size(new_window_size,self.preview_label_txt.winfo_height())

                self.update_preview()
            else:
                #print('preview_conf - skipped')
                pass

    def preview_focusin(self):
        self.main.focus_set()
        self.sel_tree.focus_set()

    def show_preview(self,user_action=True):
        self_preview = self.preview
        self.preview_photo_image_cache = Image_Cache(self.main)

        if self.preview_shown:
            self_preview.lift()
            self_preview.attributes('-topmost',True)
            self_preview.after_idle(self_preview.attributes,'-topmost',False)
            self_preview.after_idle(self.preview_conf)
        else:
            self.preview_shown=True

            if cfg_geometry:=self.cfg_get('preview','800x600',section='geometry'):
                self_preview.geometry(cfg_geometry)

            self_preview.deiconify()

        if user_action:
            self.cfg.set_bool(CFG_KEY_SHOW_PREVIEW,True)

        self.update_preview()

        self.main.focus_set()
        self.sel_tree.focus_set()

    def update_preview(self):
        if self.preview_shown:
            #from PIL import Image, ImageTk
            #from PIL.ImageTk import PhotoImage as ImageTk_PhotoImage
            #from PIL.Image import BILINEAR,open as image_open

            path = self.sel_full_path_to_file

            if path:
                head,ext = path_splitext(path)
                ext_lower = ext.lower()

                try:
                    file_size = stat(path).st_size
                except:
                    file_size = None

                if isdir(path) or not file_size:
                    self.preview_frame_txt.pack_forget()
                    self.preview_label_img.pack_forget()
                    self.preview_label_txt_configure(text='')
                    self.preview.title('Dude - Preview')

                elif ext_lower in IMAGES_EXTENSIONS:
                    self.preview_frame_txt.pack_forget()

                    try:
                        cache_res = self.preview_photo_image_cache.get_photo_image(path,self.main)

                        self.preview_label_img_configure(image=cache_res[0])
                        self.preview_label_txt_configure(text=cache_res[1])

                    except Exception as e:
                        self.preview_label_txt_configure(text=str(e))
                        self.preview.title(path)
                        self.preview_text.delete(1.0, 'end')
                    else:
                        self.preview_label_img.pack(fill='both',expand=1)
                        self.preview.title(path)

                elif ext_lower in TEXT_EXTENSIONS:
                    self.preview_label_img.pack_forget()
                    self.preview_text.delete(1.0, 'end')
                    try:
                        with open(path,'rt', encoding='utf-8', errors='ignore') as file:

                            cont_lines=file.readlines()
                            self.preview_label_txt_configure(text=f'lines:{fnumber(len(cont_lines))}')
                            self.preview_text.insert('end', ''.join(cont_lines))
                    except Exception as e:
                        self.preview_label_txt_configure(text=str(e))
                        self.preview.title(path)
                        self.preview_frame_txt.pack_forget()
                    else:
                        self.preview_frame_txt.pack(fill='both',expand=1)
                        self.preview.title(path)

                elif file_size<1024*1024*10:
                    self.preview_label_img.pack_forget()
                    self.preview_text.delete(1.0, 'end')

                    try:
                        with open(path,'rt', encoding='utf-8') as file:

                            cont_lines=file.readlines()
                            self.preview_label_txt_configure(text=f'lines:{fnumber(len(cont_lines))}')
                            self.preview_text.insert('end', ''.join(cont_lines))
                    except UnicodeDecodeError:
                        self.preview_label_txt_configure(text='Non-UTF.')
                        self.preview.title(path)
                        self.preview_frame_txt.pack_forget()
                    except Exception as e:
                        self.preview_label_txt_configure(text=str(e))
                        self.preview.title(path)
                        self.preview_frame_txt.pack_forget()
                    else:
                        self.preview_frame_txt.pack(fill='both',expand=1)
                        self.preview.title(path)

                else:
                    self.preview_frame_txt.pack_forget()
                    self.preview_label_img.pack_forget()
                    self.preview_label_txt_configure(text='wrong format')
                    self.preview.title(path)

            else:
                self.preview_frame_txt.pack_forget()
                self.preview_label_img.pack_forget()
                self.preview_label_txt_configure(text='')
                self.preview.title('Dude - Preview (no path)')

    def hide_preview(self,user_action=True):
        self_preview = self.preview

        if self.preview_shown:
            self.cfg.set('preview',str(self_preview.geometry()),section='geometry')

            if user_action:
                self.cfg.set_bool(CFG_KEY_SHOW_PREVIEW,False)

            self.preview_photo_image_cache.end()
            del self.preview_photo_image_cache
            self.preview_photo_image_cache = None

        self.preview_label_txt_configure(text='')
        self.preview_label_img_configure(image='')
        self.preview_text.delete(1.0, 'end')
        self.preview_frame_txt.pack_forget()
        self.preview_label_img.pack_forget()

        self.preview_shown=False

        self_preview.withdraw()

    def set_full_path_to_file_win(self):
        self.sel_full_path_to_file=str(Path(sep.join([self.sel_path_full,self.sel_file]))) if self.sel_path_full and self.sel_file else None

    def set_full_path_to_file_lin(self):
        #print('set_full_path_to_file_lin')
        self.sel_full_path_to_file=(self.sel_path_full+self.sel_file if self.sel_path_full=='/' else sep.join([self.sel_path_full,self.sel_file])) if self.sel_path_full and self.sel_file else None

    set_full_path_to_file = set_full_path_to_file_win if windows else set_full_path_to_file_lin

    def sel_path_set(self,path):
        if self.sel_path_full != path:
            self.sel_path_full = path
            #print('self.sel_path_full')
            self.status_path_configure(text=self.sel_path_full)

            self.dominant_groups_folder={0:-1,1:-1}

    def read_ahead_by_image_cache(self, item,group_tree=True):
        #print('read_ahead_by_image_cache', group_tree)

        if group_tree:
            kind,size,crc, (pathnr,path,file,ctime,dev,inode) = self.groups_tree_item_to_data[item]
        else:
            file,kind,crc = self.current_folder_items_dict[item]

        if file and not isdir(file):
            head,ext = path_splitext(file)
            ext_lower = ext.lower()

            if ext_lower in IMAGES_EXTENSIONS:
                try:
                    if group_tree:
                        path_full = self.item_full_path(item)
                    else:
                        path_full = normpath(abspath(self.sel_path_full + sep + file))

                    self.preview_photo_image_cache.add_image_to_read_ahead(path_full)
                except Exception as e:
                    print('read_ahead_by_image_cache error',e)

    @catched
    def preview_preload_groups_tree(self,item):
        if self.preview_auto_update_bool:
            self.update_preview()

            if self.preview_photo_image_cache:
                self_my_next_dict_groups_tree = self.my_next_dict[self.groups_tree]
                self_my_prev_dict_groups_tree = self.my_prev_dict[self.groups_tree]

                self_read_ahead_by_image_cache = self.read_ahead_by_image_cache
                self.preview_photo_image_cache.reset_read_ahead()

                prev_item = next_item = item
                for i in range(self.preview_photo_image_cache.pre_and_next_range):
                    #print('  ',i)
                    next_item = self_my_next_dict_groups_tree[next_item]
                    self_read_ahead_by_image_cache(next_item)

                    prev_item = self_my_prev_dict_groups_tree[prev_item]
                    self_read_ahead_by_image_cache(prev_item)

    @catched
    def groups_tree_sel_change(self,item,force=False,change_status_line=True):
        gc_disable()

        self.sel_item = item

        if change_status_line :
            self.status()

        kind,size,crc, (pathnr,path,file,ctime,dev,inode) = self.groups_tree_item_to_data[item]

        #print(kind,size,crc,pathnr,path,file,ctime,dev,inode)

        self.sel_file = file

        if self.sel_crc != crc:
            self.sel_crc = crc

            self.dominant_groups_index={0:-1,1:-1}

        if path!=self.sel_path or force or pathnr!=self.sel_pathnr:
            if self.find_tree==self.folder_tree:
                self.find_result=()

            if pathnr!=None: #non crc node , may be 0
                self.sel_pathnr,self.sel_path = pathnr,path
                self.sel_path_set(dude_core.scanned_paths[pathnr]+path)
            else :
                self.sel_pathnr,self.sel_path = None,None
                self.sel_path_set(None)

        self.set_full_path_to_file()

        self.sel_kind = kind

        self.preview_preload_groups_tree(item)


        if kind==self.FILE:
            self.tree_folder_update()
        else:
            self.tree_folder_update_none()

        gc_enable()

    @catched
    def preview_preload_folder_tree(self,item):
        if self.preview_auto_update_bool:
            self.update_preview()

            if self.preview_photo_image_cache:
                self_my_next_dict_folder_tree = self.my_next_dict[self.folder_tree]
                self_my_prev_dict_folder_tree = self.my_prev_dict[self.folder_tree]

                self_read_ahead_by_image_cache = self.read_ahead_by_image_cache
                self.preview_photo_image_cache.reset_read_ahead()

                prev_item = next_item = item
                for i in range(self.preview_photo_image_cache.pre_and_next_range):
                    next_item = self_my_next_dict_folder_tree[next_item]
                    self_read_ahead_by_image_cache(next_item,False)

                    prev_item = self_my_prev_dict_folder_tree[prev_item]
                    self_read_ahead_by_image_cache(prev_item,False)

    @catched
    def folder_tree_sel_change(self,item,change_status_line=True):
        #print('folder_tree_sel_change',item,change_status_line)

        gc_disable()

        self.sel_item = item

        self.sel_file,self.sel_kind,self.sel_crc = self.current_folder_items_dict[item]

        kind = self.sel_kind

        self.set_full_path_to_file()

        if kind==self.FILE:
            if change_status_line: self.status('',do_log=False)
            self.groups_tree_update(item)
        else:
            if change_status_line:
                if kind==self.LINK:
                    self.status(readlink(self.sel_full_path_to_file),self.icon_softlink_target ,do_log=False)
                    #if windows:
                    #    dont work either
                    #    self.status(os.path.realpath(self.sel_full_path_to_file),self.icon_softlink_target ,do_log=False)
                    #else:

                elif kind==self.SINGLEHARDLINKED:
                    self.status('file with hardlinks',do_log=False)
                elif kind==self.DIRLINK:
                    self.status(readlink(self.sel_full_path_to_file),self.icon_softlink_dir_target ,do_log=False)
                else:
                    self.status('',do_log=False)

            self.folder_tree.update()

            self.groups_tree_update_none()

        self.preview_preload_folder_tree(item)

        gc_enable()

    def menubar_unpost(self):
        try:
            self.menubar.unpost()
        except Exception as e:
            l_error(e)

    def context_menu_show(self,event):
        tree=event.widget

        if tree.identify("region", event.x, event.y) == 'heading':
            return

        if self.block_processing_stack:
            return

        tree.focus_set()
        self.tree_on_mouse_button_press(event)
        tree.update()

        item_actions_state=('disabled','normal')[self.sel_item is not None]

        pop=self.popup_groups if tree==self.groups_tree else self.popup_folder

        pop.delete(0,'end')

        pop_add_separator = pop.add_separator
        pop_add_cascade = pop.add_cascade
        pop_add_command = pop.add_command

        file_actions_state=('disabled',item_actions_state)[self.sel_kind in (self.FILE,self.SINGLE,self.SINGLEHARDLINKED) ]
        file_or_dir_actions_state=('disabled',item_actions_state)[self.sel_kind in (self.FILE,self.SINGLE,self.SINGLEHARDLINKED,self.DIR,self.DIRLINK,self.UPDIR,self.CRC) ]

        parent_dir_state = ('disabled','normal')[self.two_dots_condition(self.sel_path_full) and self.sel_kind!=self.CRC]

        crc_mode_only = ('disabled','normal')[self.operation_mode]

        if tree==self.groups_tree:
            self_tagged = self.tagged

            any_mark_in_curr_crc = any( {True for item in self.tree_children_sub[self.sel_crc] if item in self_tagged} ) if self.sel_crc else False
            any_mark_in_curr_crc_state = ('disabled','normal')[any_mark_in_curr_crc]
            any_mark_in_curr_crc_state_and_crc = ('disabled','normal')[any_mark_in_curr_crc and not self.operation_mode]

            any_not_mark_in_curr_crc = any( {True for item in self.tree_children_sub[self.sel_crc] if item not in self_tagged} ) if self.sel_crc else False
            any_not_mark_in_curr_crc_state = ('disabled','normal')[any_not_mark_in_curr_crc]

            c_local = Menu(pop,tearoff=0,bg=self.bg_color)
            c_local_add_command = c_local.add_command
            c_local_add_separator = c_local.add_separator
            c_local_add_cascade = c_local.add_cascade
            c_local_entryconfig = c_local.entryconfig

            c_local_add_command(label = "Toggle Mark",  command = lambda : self.tag_toggle_selected(tree,self.sel_item),accelerator="space", image = self.ico_empty,compound='left')
            c_local_add_separator()
            c_local_add_command(label = "Mark all files",        command = lambda : self.mark_in_group(self.set_mark),accelerator="A", image = self.ico_empty,compound='left',state = any_not_mark_in_curr_crc_state)
            c_local_add_command(label = "Unmark all files",        command = lambda : self.mark_in_group(self.unset_mark),accelerator="N", image = self.ico_empty,compound='left', state = any_mark_in_curr_crc_state)
            c_local_add_separator()
            c_local_add_command(label = 'Mark By expression ...',command = lambda : self.mark_expression(self.set_mark,'Mark files',False),accelerator="+", image = self.ico_empty,compound='left',state = any_not_mark_in_curr_crc_state)
            c_local_add_command(label = 'Unmark By expression ...',command = lambda : self.mark_expression(self.unset_mark,'Unmark files',False),accelerator="-", image = self.ico_empty,compound='left', state = any_mark_in_curr_crc_state)
            c_local_add_separator()
            c_local_add_command(label = "Toggle mark on oldest file",     command = lambda : self.mark_in_group_by_ctime('oldest',self.invert_mark),accelerator="O", image = self.ico_empty,compound='left')
            c_local_add_command(label = "Toggle mark on youngest file",   command = lambda : self.mark_in_group_by_ctime('youngest',self.invert_mark),accelerator="Y", image = self.ico_empty,compound='left')
            c_local_add_separator()
            c_local_add_command(label = "Invert marks",   command = lambda : self.mark_in_group(self.invert_mark),accelerator="I", image = self.ico_empty,compound='left')
            c_local_add_separator()

            mark_cascade_path = Menu(c_local, tearoff = 0,bg=self.bg_color)
            unmark_cascade_path = Menu(c_local, tearoff = 0,bg=self.bg_color)

            row=0
            for path in dude_core.scanned_paths:
                mark_cascade_path.add_command(image=self.icon_nr[row], label = path, compound = 'left',command  = lambda pathpar=path: self.action_on_path(pathpar,self.set_mark,False),accelerator=str(row+1)  )
                unmark_cascade_path.add_command(image=self.icon_nr[row], label = path, compound = 'left', command  = lambda pathpar=path: self.action_on_path(pathpar,self.unset_mark,False),accelerator="Shift+"+str(row+1)  )
                row+=1

            c_local_add_command(label = "Mark on specified directory ...",   command = lambda : self.mark_subpath(self.set_mark,False), image = self.ico_empty,compound='left')
            c_local_add_command(label = "Unmark on specified directory ...",   command = lambda : self.mark_subpath(self.unset_mark,False), image = self.ico_empty,compound='left')
            c_local_add_separator()

            c_local_add_cascade(label = "Mark on scan path",             menu = mark_cascade_path, image = self.ico_empty,compound='left')
            c_local_add_cascade(label = "Unmark on scan path",             menu = unmark_cascade_path, image = self.ico_empty,compound='left')
            c_local_add_separator()


            anything_tagged = bool(self_tagged)
            nothing_tagged = not anything_tagged

            anything_tagged_state=('disabled','normal')[anything_tagged]
            anything_tagged_state_and_crc=('disabled','normal')[anything_tagged and not self.operation_mode]
            nothing_tagged_state=('disabled','normal')[nothing_tagged]

            anything_tagged_state_win=('disabled','normal')[anything_tagged and windows ]
            anything_tagged_state_win_and_crc=('disabled','normal')[anything_tagged and windows and not self.operation_mode]

            anything_not_tagged = any( {} )

            self_tree_children_sub = self.tree_children_sub

            any_not_marked = any( {True for crc in self.tree_children[self.groups_tree] for item in self_tree_children_sub[crc] if item not in self_tagged} )
            any_not_marked_state = ('disabled','normal')[any_not_marked]

            #nothing_tagged_state_local = ('disabled','normal')[no_mark_in_curr_crc]

            anything_tagged_state_win_local=('disabled','normal')[any_mark_in_curr_crc_state and windows ] if self.sel_crc else 'disabled'
            anything_tagged_state_win_local_and_crc=('disabled','normal')[any_mark_in_curr_crc_state and windows and not self.operation_mode] if self.sel_crc else 'disabled'

            c_local_add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(DELETE,0),accelerator="Delete",state=any_mark_in_curr_crc_state, image = self.ico_empty,compound='left')
            c_local_entryconfig(19,foreground='red',activeforeground='red')
            c_local_add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(SOFTLINK,0),accelerator="Insert",state=any_mark_in_curr_crc_state_and_crc, image = self.ico_empty,compound='left')
            c_local_entryconfig(20,foreground='red',activeforeground='red')
            c_local_add_command(label = 'Create *.lnk for Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(WIN_LNK,0),accelerator="Alt+Shift+Insert",state=anything_tagged_state_win_local_and_crc, image = self.ico_empty,compound='left')
            c_local_entryconfig(21,foreground='red',activeforeground='red')
            c_local_add_command(label = 'Hardlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(HARDLINK,0),accelerator="Shift+Insert",state=any_mark_in_curr_crc_state_and_crc, image = self.ico_empty,compound='left')
            c_local_entryconfig(22,foreground='red',activeforeground='red')

            pop_add_cascade(label = 'Local (this group)',menu = c_local,state=item_actions_state, image = self.ico_empty,compound='left')
            pop_add_separator()

            c_all = Menu(pop,tearoff=0,bg=self.bg_color)

            c_all.add_command(label = "Mark all files",        command = lambda : self.mark_on_all(self.set_mark),accelerator="Ctrl+A", image = self.ico_empty,compound='left',state = any_not_marked_state )
            c_all.add_command(label = "Unmark all files",        command = lambda : self.mark_on_all(self.unset_mark),accelerator="Ctrl+N", image = self.ico_empty,compound='left',state = anything_tagged_state)
            c_all.add_separator()
            c_all.add_command(label = 'Mark By expression ...',command = lambda : self.mark_expression(self.set_mark,'Mark files',True),accelerator="Ctrl+", image = self.ico_empty,compound='left',state = any_not_marked_state)
            c_all.add_command(label = 'Unmark By expression ...',command = lambda : self.mark_expression(self.unset_mark,'Unmark files',True),accelerator="Ctrl-", image = self.ico_empty,compound='left',state = anything_tagged_state)
            c_all.add_separator()
            c_all.add_command(label = "Mark Oldest files",     command = lambda : self.mark_all_by_ctime('oldest',self.set_mark),accelerator="Ctrl+O", image = self.ico_empty,compound='left',state = any_not_marked_state)
            c_all.add_command(label = "Unmark Oldest files",     command = lambda : self.mark_all_by_ctime('oldest',self.unset_mark),accelerator="Ctrl+Shift+O", image = self.ico_empty,compound='left',state = anything_tagged_state)
            c_all.add_separator()
            c_all.add_command(label = "Mark Youngest files",   command = lambda : self.mark_all_by_ctime('youngest',self.set_mark),accelerator="Ctrl+Y", image = self.ico_empty,compound='left',state = any_not_marked_state)
            c_all.add_command(label = "Unmark Youngest files",   command = lambda : self.mark_all_by_ctime('youngest',self.unset_mark),accelerator="Ctrl+Shift+Y", image = self.ico_empty,compound='left',state = anything_tagged_state)
            c_all.add_separator()
            c_all.add_command(label = "Invert marks",   command = lambda : self.mark_on_all(self.invert_mark),accelerator="Ctrl+I, *", image = self.ico_empty,compound='left')
            c_all.add_separator()

            mark_cascade_path = Menu(c_all, tearoff = 0,bg=self.bg_color)
            unmark_cascade_path = Menu(c_all, tearoff = 0,bg=self.bg_color)

            row=0
            for path in dude_core.scanned_paths:
                mark_cascade_path.add_command(image=self.icon_nr[row], label = path, compound = 'left', command  = lambda pathpar=path: self.action_on_path(pathpar,self.set_mark,True) ,accelerator="Ctrl+"+str(row+1) )
                unmark_cascade_path.add_command(image=self.icon_nr[row], label = path, compound = 'left',  command  = lambda pathpar=path: self.action_on_path(pathpar,self.unset_mark,True) ,accelerator="Ctrl+Shift+"+str(row+1))
                row+=1

            c_all.add_command(label = "Mark on specified directory ...",   command = lambda : self.mark_subpath(self.set_mark,True), image = self.ico_empty,compound='left')
            c_all.add_command(label = "Unmark on specified directory ...",   command = lambda : self.mark_subpath(self.unset_mark,True), image = self.ico_empty,compound='left',state = anything_tagged_state)
            c_all.add_separator()

            c_all.add_cascade(label = "Mark on scan path",             menu = mark_cascade_path, image = self.ico_empty,compound='left')
            c_all.add_cascade(label = "Unmark on scan path",             menu = unmark_cascade_path, image = self.ico_empty,compound='left',state = anything_tagged_state)
            c_all.add_separator()

            c_all.add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(DELETE,1),accelerator="Ctrl+Delete",state=anything_tagged_state, image = self.ico_empty,compound='left')
            c_all.entryconfig(21,foreground='red',activeforeground='red')
            c_all.add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(SOFTLINK,1),accelerator="Ctrl+Insert",state=anything_tagged_state_and_crc, image = self.ico_empty,compound='left')
            c_all.entryconfig(22,foreground='red',activeforeground='red')
            c_all.add_command(label = 'Create *.lnk for Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(WIN_LNK,1),accelerator="Ctrl+Alt+Shift+Insert",state=anything_tagged_state_win_and_crc, image = self.ico_empty,compound='left')
            c_all.entryconfig(23,foreground='red',activeforeground='red')
            c_all.add_command(label = 'Hardlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(HARDLINK,1),accelerator="Ctrl+Shift+Insert",state=anything_tagged_state_and_crc, image = self.ico_empty,compound='left')
            c_all.entryconfig(24,foreground='red',activeforeground='red')

            pop_add_cascade(label = 'All Files',menu = c_all,state=item_actions_state, image = self.ico_empty,compound='left')

            c_nav = Menu(self.menubar,tearoff=0,bg=self.bg_color)
            c_nav_add_command = c_nav.add_command
            c_nav_add_separator = c_nav.add_separator

            c_nav_add_command(label = 'Go to dominant group (by size sum)',command = lambda : self.goto_max_group(1), accelerator="F7", image = self.ico['dominant_size'],compound='left')
            c_nav_add_command(label = 'Go to dominant group (by quantity)',command = lambda : self.goto_max_group(0), accelerator="F8", image = self.ico['dominant_quant'],compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to next marked file'       ,command = lambda : self.goto_next_mark(self.groups_tree,1,0),accelerator="Right",state='normal', image = self.ico['next_marked'],compound='left')
            c_nav_add_command(label = 'Go to previous marked file'   ,command = lambda : self.goto_next_mark(self.groups_tree,-1,0), accelerator="Left",state='normal', image = self.ico['prev_marked'],compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to next not marked file'       ,command = lambda : self.goto_next_mark(self.groups_tree,1,1),accelerator="Shift+Right",state='normal', image = self.ico['next_unmarked'],compound='left')
            c_nav_add_command(label = 'Go to previous not marked file'   ,command = lambda : self.goto_next_mark(self.groups_tree,-1,1), accelerator="Shift+Left",state='normal', image = self.ico['prev_unmarked'],compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to parent directory'   ,command = self.go_to_parent_dir, accelerator="Backspace",state=parent_dir_state, image = self.ico_empty,compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to next group'       ,command = lambda : self.goto_next_prev_crc(1),accelerator="Pg Down",state='normal', image = self.ico_empty,compound='left')
            c_nav_add_command(label = 'Go to previous group'   ,command = lambda : self.goto_next_prev_crc(-1), accelerator="Pg Up",state='normal', image = self.ico_empty,compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to first group'       ,command = lambda : self.goto_first_last_crc(0),accelerator="Home",state='normal', image = self.ico_empty,compound='left')
            c_nav_add_command(label = 'Go to last group'   ,command = lambda : self.goto_first_last_crc(-1), accelerator="End",state='normal', image = self.ico_empty,compound='left')

        else:
            dir_actions_state=('disabled','normal')[self.sel_kind in (self.DIR,self.DIRLINK)]
            dir_actions_state_and_crc=('disabled','normal')[self.sel_kind in (self.DIR,self.DIRLINK) and not self.operation_mode]
            dir_actions_state_win=('disabled','normal')[(self.sel_kind in (self.DIR,self.DIRLINK)) and windows]
            dir_actions_state_win_and_crc=('disabled','normal')[(self.sel_kind in (self.DIR,self.DIRLINK)) and windows and not self.operation_mode]

            c_local = Menu(pop,tearoff=0,bg=self.bg_color)
            c_local_add_command = c_local.add_command
            c_local_add_separator = c_local.add_separator
            c_local_entryconfig = c_local.entryconfig

            duplicate_file_actions_state=('disabled',item_actions_state)[self.sel_kind==self.FILE]

            self_FILE=self.FILE

            self_current_folder_items=self.current_folder_items

            self_current_folder_items_dict = self.current_folder_items_dict

            markable_files_in_folder = any( { True for item in self_current_folder_items if self_current_folder_items_dict[item][1]==self_FILE } )
            markable_files_in_folder_state = ('disabled','normal')[markable_files_in_folder]

            c_local_add_command(label = "Toggle Mark",  command = lambda : self.tag_toggle_selected(tree,self.sel_item),accelerator="space",state=duplicate_file_actions_state, image = self.ico_empty,compound='left')
            c_local_add_separator()
            c_local_add_command(label = "Mark all files",        command = lambda : self.mark_in_folder(self.set_mark),accelerator="A",state=markable_files_in_folder_state, image = self.ico_empty,compound='left')
            c_local_add_command(label = "Unmark all files",        command = lambda : self.mark_in_folder(self.unset_mark),accelerator="N",state=markable_files_in_folder_state, image = self.ico_empty,compound='left')
            c_local_add_separator()
            c_local_add_command(label = 'Mark By expression',command = lambda : self.mark_expression(self.set_mark,'Mark files'),accelerator="+", image = self.ico_empty,compound='left',state = markable_files_in_folder_state)
            c_local_add_command(label = 'Unmark By expression',command = lambda : self.mark_expression(self.unset_mark,'Unmark files'),accelerator="-", image = self.ico_empty,compound='left', state = markable_files_in_folder_state)
            c_local_add_separator()

            anything_tagged_state=('disabled','normal')[bool(self.current_folder_items_tagged)]
            anything_tagged_state_and_crc=('disabled','normal')[bool(self.current_folder_items_tagged) and not self.operation_mode]

            anything_tagged_state_win=('disabled','normal')[bool(self.current_folder_items_tagged) and windows]
            anything_tagged_state_win_and_crc=('disabled','normal')[bool(self.current_folder_items_tagged) and windows and not self.operation_mode]

            c_local_add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_folder_wrapper(DELETE,0),accelerator="Delete",state=anything_tagged_state, image = self.ico_empty,compound='left')
            c_local_add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_folder_wrapper(SOFTLINK,0),accelerator="Insert",state=anything_tagged_state_and_crc, image = self.ico_empty,compound='left')
            c_local_add_command(label = 'Create *.lnk for Marked Files ...',command=lambda : self.process_files_in_folder_wrapper(WIN_LNK,0),accelerator="Alt+Shift+Insert",state=anything_tagged_state_win_and_crc, image = self.ico_empty,compound='left')

            c_local_entryconfig(8,foreground='red',activeforeground='red')
            c_local_entryconfig(9,foreground='red',activeforeground='red')
            c_local_entryconfig(10,foreground='red',activeforeground='red')

            pop_add_cascade(label = 'Local (this folder)',menu = c_local,state=item_actions_state, image = self.ico_empty,compound='left')
            pop_add_separator()

            c_sel_sub = Menu(pop,tearoff=0,bg=self.bg_color)
            c_sel_sub_add_command = c_sel_sub.add_command
            c_sel_sub_add_command(label = "Mark All Duplicates in Subdirectory",  command = lambda : self.sel_dir(self.set_mark),accelerator="D",state=dir_actions_state, image = self.ico_empty,compound='left')
            c_sel_sub_add_command(label = "Unmark All Duplicates in Subdirectory",  command = lambda : self.sel_dir(self.unset_mark),accelerator="Shift+D",state=dir_actions_state, image = self.ico_empty,compound='left')
            c_sel_sub.add_separator()

            c_sel_sub_add_command(label = 'Remove Marked Files in Subdirectory Tree ...',command=lambda : self.process_files_in_folder_wrapper(DELETE,True),accelerator="Delete",state=dir_actions_state, image = self.ico_empty,compound='left')
            c_sel_sub_add_command(label = 'Softlink Marked Files in Subdirectory Tree ...',command=lambda : self.process_files_in_folder_wrapper(SOFTLINK,True),accelerator="Insert",state=dir_actions_state_and_crc, image = self.ico_empty,compound='left')
            c_sel_sub_add_command(label = 'Create *.lnk for Marked Files in Subdirectory Tree ...',command=lambda : self.process_files_in_folder_wrapper(WIN_LNK,True),accelerator="Alt+Shift+Insert",state=dir_actions_state_win_and_crc, image = self.ico_empty,compound='left')

            c_sel_sub.entryconfig(3,foreground='red',activeforeground='red')
            c_sel_sub.entryconfig(4,foreground='red',activeforeground='red')
            c_sel_sub.entryconfig(5,foreground='red',activeforeground='red')

            pop_add_cascade(label = 'Selected Subdirectory',menu = c_sel_sub,state=dir_actions_state, image = self.ico_empty,compound='left')

            c_nav = Menu(pop,tearoff=0,bg=self.bg_color)
            c_nav_add_command = c_nav.add_command
            c_nav_add_separator = c_nav.add_separator

            c_nav_add_command(label = 'Go to dominant folder (by size sum)',command = lambda : self.goto_max_folder(1),accelerator="F5", image = self.ico['dominant_size'],compound='left')
            c_nav_add_command(label = 'Go to dominant folder (by quantity)',command = lambda : self.goto_max_folder(0) ,accelerator="F6", image = self.ico['dominant_quant'],compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to next marked file'       ,command = lambda : self.goto_next_mark(self.folder_tree,1,0),accelerator="Right",state='normal', image = self.ico['next_marked'],compound='left')
            c_nav_add_command(label = 'Go to previous marked file'   ,command = lambda : self.goto_next_mark(self.folder_tree,-1,0), accelerator="Left",state='normal', image = self.ico['prev_marked'],compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to next not marked file'       ,command = lambda : self.goto_next_mark(self.folder_tree,1,1),accelerator="Shift+Right",state='normal', image = self.ico['next_unmarked'],compound='left')
            c_nav_add_command(label = 'Go to previous not marked file'   ,command = lambda : self.goto_next_mark(self.folder_tree,-1,1), accelerator="Shift+Left",state='normal', image = self.ico['prev_unmarked'],compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to parent directory'       ,command = self.go_to_parent_dir, accelerator="Backspace",state=parent_dir_state, image = self.ico_empty,compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to next duplicate'       ,command = lambda : self.goto_next_prev_duplicate_in_folder(1),accelerator="Pg Down",state='normal', image = self.ico_empty,compound='left')
            c_nav_add_command(label = 'Go to previous duplicate'   ,command = lambda : self.goto_next_prev_duplicate_in_folder(-1), accelerator="Pg Up",state='normal', image = self.ico_empty,compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to first entry'       ,command = lambda : self.goto_first_last_dir_entry(0),accelerator="Home",state='normal', image = self.ico_empty,compound='left')
            c_nav_add_command(label = 'Go to last entry'   ,command = lambda : self.goto_first_last_dir_entry(-1), accelerator="End",state='normal', image = self.ico_empty,compound='left')

        pop_add_separator()
        pop_add_cascade(label = 'Navigation',menu = c_nav,state=item_actions_state, image = self.ico_empty,compound='left')

        pop_add_separator()
        pop_add_command(label = 'Open File',command = self.open_file,accelerator="Return",state=file_actions_state, image = self.ico_empty,compound='left')
        pop_add_command(label = 'Open Folder(s)',command = self.open_folder,accelerator="Alt+Return",state=file_or_dir_actions_state, image = self.ico_empty,compound='left')

        pop_add_separator()
        pop_add_command(label = 'Scan ...',  command = self.scan_dialog_show,accelerator='S',image = self.ico['scan'],compound='left')
        pop_add_command(label = 'Settings ...',  command = lambda : self.get_settings_dialog().show(),accelerator='F2',image = self.ico['settings'],compound='left')
        pop_add_separator()
        pop_add_command(label = 'Show/Update Preview',  command = lambda : self.show_preview(),accelerator='F9',image = self.ico_empty,compound='left',state=('disabled','normal')[bool(not self.cfg_get_bool(CFG_KEY_PREVIEW_AUTO_UPDATE) or not self.preview_shown )])
        pop_add_command(label = 'Hide Preview window',  command = lambda : self.hide_preview(),accelerator='F11',image = self.ico_empty,compound='left',state=('disabled','normal')[self.preview_shown])
        pop_add_separator()
        pop_add_command(label = 'Copy full path',command = self.clip_copy_full_path_with_file,accelerator='Ctrl+C',state = 'normal' if (self.sel_kind and self.sel_kind!=self.CRC) else 'disabled', image = self.ico_empty,compound='left')
        #pop_add_command(label = 'Copy only path',command = self.clip_copy_full,accelerator="C",state = 'normal' if self.sel_item!=None else 'disabled')
        pop_add_separator()
        pop_add_command(label = 'Find ...',command = self.finder_wrapper_show,accelerator="F",state = 'normal' if self.sel_item is not None else 'disabled', image = self.ico_empty,compound='left')
        pop_add_command(label = 'Find next',command = self.find_next,accelerator="F3",state = 'normal' if self.sel_item is not None else 'disabled', image = self.ico_empty,compound='left')
        pop_add_command(label = 'Find prev',command = self.find_prev,accelerator="Shift+F3",state = 'normal' if self.sel_item is not None else 'disabled', image = self.ico_empty,compound='left')
        pop_add_separator()

        pop_add_command(label = 'Exit',  command = self.exit ,image = self.ico['exit'],compound='left')

        try:
            self.hide_tooltip()

            self.menubar.unpost()
            #self.popup_groups_unpost()
            #self.popup_folder_unpost()

            pop.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            print(e)

        pop.grab_release()

    @logwrapper
    def empty_folder_remove_ask(self):
        initialdir = self.last_dir if self.last_dir else self.cwd
        if res:=askdirectory(title='Select Directory',initialdir=initialdir,parent=self.main):
            self.last_dir=res
            final_info = self.empty_dirs_removal(res,True)

            self.get_text_info_dialog().show('Removed empty directories','\n'.join(final_info))
            self.store_text_dialog_fields(self.text_info_dialog)

            self.tree_folder_update(self.sel_path_full)

    @logwrapper
    def sel_dir(self,action):
        self.action_on_path(self.sel_full_path_to_file,action,True)

    @logwrapper
    def column_sort_click(self, tree, colname):
        prev_colname,prev_sort_index,prev_is_numeric,prev_reverse,prev_updir_code,prev_dir_code,prev_non_dir_code=self.column_sort_last_params[tree]
        reverse = not prev_reverse if colname == prev_colname else prev_reverse
        tree.heading(prev_colname, text=self.org_label[prev_colname])

        updir_code,dir_code,non_dir_code = (2,1,0) if reverse else (0,1,2)

        sort_index=self.REAL_SORT_COLUMN_INDEX[colname]
        is_numeric=self.REAL_SORT_COLUMN_IS_NUMERIC[colname]
        self.column_sort_last_params[tree]=(colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code)

        self.column_sort(tree)

    @logwrapper
    def tree_sort_item(self,tree,parent_item,lower_tree):
        colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[tree]

        real_column_to_sort=self.REAL_SORT_COLUMN[colname]

        tlist=[]
        tree_set = tree.set
        tlist_append = tlist.append
        self_UPDIR = self.UPDIR
        dir_or_dirlink = (self.DIR,self.DIRLINK)

        for item in (self.tree_children_sub[parent_item] if parent_item else self.tree_children[tree]):
            sortval_org=tree_set(item,real_column_to_sort)
            sortval=(int(sortval_org) if sortval_org.isdigit() else 0) if is_numeric else sortval_org

            if lower_tree:
                kind = tree_set(item,'kind')
                code=updir_code if kind==self_UPDIR else dir_code if kind in dir_or_dirlink else non_dir_code
                tlist_append( ( (code,sortval),item) )
            else:
                tlist_append( (sortval,item) )

        tlist.sort(reverse=reverse,key=lambda x: x[0])

        if not parent_item:
            parent_item=''

        tree_move = tree.move
        _ = {tree_move(item, parent_item, index) for index,(val_tuple,item) in enumerate(sorted(tlist,reverse=reverse,key=lambda x: x[0]) ) }

        if lower_tree:
            self.current_folder_items = self.tree_children[self.folder_tree]

    @restore_status_line
    @block_and_log
    def column_sort(self, tree):
        self.status('Sorting...')
        colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[tree]

        self.column_sort_set_arrow(tree)

        self_tree_sort_item = self.tree_sort_item

        if tree==self.groups_tree:
            if colname in ('path','file','ctime_h') or (self.operation_mode and colname=='size_h'):
                for crc in self.tree_children[tree]:
                    self_tree_sort_item(tree,crc,False)
            else:
                self_tree_sort_item(tree,None,False)
        else:
            self_tree_sort_item(tree,None,True)

        tree.update()
        self.create_my_prev_next_dicts(tree)

    def column_sort_set_arrow(self, tree):
        colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[tree]
        tree.heading(colname, text=self.org_label[colname] + ' ' + str('\u25BC' if reverse else '\u25B2') )

    def path_to_scan_add(self,path):
        if len(self.paths_to_scan_from_dialog)<self.MAX_PATHS:
            self.paths_to_scan_from_dialog.append(path)
            self.paths_to_scan_update()
        else:
            l_error('can\'t add:%s. limit exceeded',path)

    scanning_in_progress=False
    def scan_wrapper(self):
        if self.scanning_in_progress:
            l_warning('scan_wrapper collision')
            return

        self.scanning_in_progress=True

        try:
            if self.scan():
                self.scan_dialog_hide_wrapper()
        except Exception as e:
            l_error(e)
            self.status(str(e))

        self.scanning_in_progress=False

    def scan_dialog_hide_wrapper(self):
        self.scan_dialog.hide()
        self.groups_tree.focus_set()

    def scan_update_info_path_nr(self):
        self.update_scan_path_nr=True

    prev_status_progress_text=''
    def status_progress(self,text='',do_log=False):
        if text != self.prev_status_progress_text:
            self.progress_dialog_on_scan.lab[1].configure(text=text)
            self.progress_dialog_on_scan.area_main.update()
            self.prev_status_progress_text=text

    @restore_status_line
    @logwrapper
    def scan(self):
        from threading import Thread

        self.status('Scanning...')
        self.cfg.write()

        self.hide_preview(False)
        dude_core.reset()
        self.status_path_configure(text='')
        self.groups_show()

        paths_to_scan_from_entry = [var.get() for var in self.paths_to_scan_entry_var.values() if bool(var.get())]
        exclude_from_entry = [var.get() for var in self.exclude_entry_var.values()]

        if res:=dude_core.set_exclude_masks(self.cfg_get_bool(CFG_KEY_EXCLUDE_REGEXP),exclude_from_entry):
            self.get_info_dialog_on_scan().show('Error. Fix expression.',res)
            return False
        self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(exclude_from_entry))

        if not paths_to_scan_from_entry:
            self.get_info_dialog_on_scan().show('Error. No paths to scan.','Add paths to scan.')
            return False

        if res:=dude_core.set_paths_to_scan(paths_to_scan_from_entry):
            self.get_info_dialog_on_scan().show('Error. Fix paths selection.',res)
            return False

        dude_core.scan_update_info_path_nr=self.scan_update_info_path_nr

        self.main_update()

        #############################
        self_progress_dialog_on_scan = self.get_progress_dialog_on_scan()
        self_progress_dialog_on_scan_lab = self_progress_dialog_on_scan.lab
        self_progress_dialog_on_scan_area_main_update = self_progress_dialog_on_scan.area_main.update

        self_progress_dialog_on_scan_progr1var = self_progress_dialog_on_scan.progr1var
        self_progress_dialog_on_scan_progr2var = self_progress_dialog_on_scan.progr2var

        self_progress_dialog_on_scan_lab_r1_config = self_progress_dialog_on_scan.lab_r1.config
        self_progress_dialog_on_scan_lab_r2_config = self_progress_dialog_on_scan.lab_r2.config

        str_self_progress_dialog_on_scan_abort_button = str(self_progress_dialog_on_scan.abort_button)
        #############################

        self.scan_dialog.widget.update()
        self.tooltip_message[str_self_progress_dialog_on_scan_abort_button]='If you abort at this stage,\nyou will not get any results.'
        self_progress_dialog_on_scan.abort_button.configure(image=self.ico['cancel'],text='Cancel',compound='left')
        self_progress_dialog_on_scan.abort_button.pack(side='bottom', anchor='n',padx=5,pady=5)

        self.action_abort=False
        self_progress_dialog_on_scan.abort_button.configure(state='normal')

        self.update_scan_path_nr=False

        dude_core.log_skipped = self.log_skipped_var.get()
        #self.log_skipped = self.log_skipped_var.get()

        self.operation_mode = operation_mode = self.operation_mode_var.get()

        image_min_size_int = 0
        if self.image_min_size_check_var.get():
            if image_min_size := self.image_min_size_var.get():
                try:
                    image_min_size_int = int(image_min_size)
                except Exception as e:
                    self.get_info_dialog_on_scan().show('Image Min size value error',f'fix: "{image_min_size}"')
                    return

        image_max_size_int = 0
        if self.image_max_size_check_var.get():
            if image_max_size := self.image_max_size_var.get():
                try:
                    image_max_size_int = int(image_max_size)
                except Exception as e:
                    self.get_info_dialog_on_scan().show('Image Max size value error',f'fix: "{image_max_size}"')
                    return

        ##################
        file_min_size_int = 0
        if self.file_min_size_check_var.get():
            if file_min_size := self.file_min_size_var.get():
                file_min_size_int = str_to_bytes(file_min_size)

                if file_min_size_int==-1:
                    self.get_info_dialog_on_scan().show('File Min size value error',f'fix: "{file_min_size}"')
                    return

        file_max_size_int = 0
        if self.file_max_size_check_var.get():
            if file_max_size := self.file_max_size_var.get():
                file_max_size_int = str_to_bytes(file_max_size)

                if file_max_size_int==-1:
                    self.get_info_dialog_on_scan().show('File Max size value error',f'fix: "{file_max_size}"')
                    return
        #################

        scan_thread=Thread(target=lambda : dude_core.scan(operation_mode,file_min_size_int,file_max_size_int),daemon=True)
        scan_thread.start()

        self_progress_dialog_on_scan.lab_l1.configure(text='Total space:')
        self_progress_dialog_on_scan.lab_l2.configure(text='Files number:' )

        self_progress_dialog_on_scan_progr1var.set(0)
        self_progress_dialog_on_scan_progr2var.set(0)

        if self.operation_mode in (MODE_SIMILARITY,MODE_GPS):
            self_progress_dialog_on_scan.show('Scanning for images')
        else:
            self_progress_dialog_on_scan.show('Scanning')

        update_once=True

        prev_data={}
        new_data={}
        prev_path_nr=-1
        for i in range(1,5):
            prev_data[i]=''
            new_data[i]=''

        time_without_busy_sign=0

        self_progress_dialog_on_scan_progr1var.set(0)
        self_progress_dialog_on_scan_lab_r1_config(text='- - - -')
        self_progress_dialog_on_scan_progr2var.set(0)
        self_progress_dialog_on_scan_lab_r2_config(text='- - - -')

        wait_var=BooleanVar()
        wait_var.set(False)

        self_progress_dialog_on_scan_lab[2].configure(image='',text='')

        self_icon_nr = self.icon_nr
        self_tooltip_message = self.tooltip_message
        self_configure_tooltip = self.configure_tooltip

        scan_thread_is_alive = scan_thread.is_alive

        self_get_hg_ico = self.get_hg_ico

        local_bytes_to_str = bytes_to_str

        self_main_after = self.main.after
        self_main_wait_variable = self.main.wait_variable
        wait_var_set = wait_var.set
        wait_var_get = wait_var.get

        while scan_thread_is_alive():
            new_data[3]=local_bytes_to_str(dude_core.info_size_sum)
            new_data[4]=fnumber(dude_core.info_counter)

            anything_changed=False
            for i in (3,4):
                if new_data[i] != prev_data[i]:
                    prev_data[i]=new_data[i]
                    self_progress_dialog_on_scan_lab[i].configure(text=new_data[i])
                    anything_changed=True

            now=time()
            if self.update_scan_path_nr:
                self.update_scan_path_nr=False
                self_progress_dialog_on_scan_lab[0].configure(image=self_icon_nr[dude_core.info_path_nr])
                self_progress_dialog_on_scan_lab[1].configure(text=dude_core.info_path_to_scan)

            if anything_changed:
                time_without_busy_sign=now

                if operation_mode in (MODE_SIMILARITY,MODE_GPS):
                    self_progress_dialog_on_scan_lab_r1_config(text=local_bytes_to_str(dude_core.info_size_sum_images))
                    self_progress_dialog_on_scan_lab_r2_config(text=fnumber(dude_core.info_counter_images))

                if update_once:
                    update_once=False
                    self_tooltip_message[str_self_progress_dialog_on_scan_abort_button]='If you abort at this stage,\nyou will not get any results.'
                    self_configure_tooltip(str_self_progress_dialog_on_scan_abort_button)

                    self_progress_dialog_on_scan_lab[2].configure(image=self.ico_empty)
            else :
                if now>time_without_busy_sign+1.0:
                    self_progress_dialog_on_scan_lab[2].configure(image=self_get_hg_ico(),text = '', compound='left')

                    self_tooltip_message[str_self_progress_dialog_on_scan_abort_button]='currently scanning:\n%s...' % dude_core.info_line
                    self_configure_tooltip(str_self_progress_dialog_on_scan_abort_button)
                    update_once=True

            self_progress_dialog_on_scan_area_main_update()

            if self.action_abort:
                dude_core.abort()
                break

            self_main_after(100,lambda : wait_var_set(not wait_var_get()))
            self_main_wait_variable(wait_var)

        scan_thread.join()

        if self.action_abort:
            self_progress_dialog_on_scan.hide(True)
            return False

        #############################
        if dude_core.sum_size==0:
            self_progress_dialog_on_scan.hide(True)
            self.get_info_dialog_on_scan().show('Cannot Proceed.','No Duplicates.')
            return False
        #############################

        self_status=self.status=self.status_progress

        self_tooltip_message[str_self_progress_dialog_on_scan_abort_button]='If you abort at this stage,\npartial results may be available\n(if any groups are found).'
        self_progress_dialog_on_scan.abort_button.configure(image=self.ico['abort'],text='Abort',compound='left')

        self_progress_dialog_on_scan_progr1var_set = self_progress_dialog_on_scan_progr1var.set
        self_progress_dialog_on_scan_progr2var_set = self_progress_dialog_on_scan_progr2var.set

        prev_progress_size=0
        prev_progress_quant=0

        self_get_hg_ico = self.get_hg_ico

        if operation_mode in (MODE_SIMILARITY,MODE_GPS):
            self_progress_dialog_on_scan_lab[0].configure(image=self.ico_empty,text='')
            self_progress_dialog_on_scan_lab[1].configure(image='',text='')
            self_progress_dialog_on_scan_lab[2].configure(image='',text='')
            self_progress_dialog_on_scan_lab[3].configure(image='',text='')
            self_progress_dialog_on_scan_lab[4].configure(image='',text='')


            self_progress_dialog_on_scan.widget.title('Images hashing')

            self_status('Starting Images hashing ...')

            hash_size = self.similarity_hsize_varx2.get()
            all_rotations = self.all_rotations.get()

            ih_thread=Thread(target=lambda : dude_core.images_processing(operation_mode,hash_size,all_rotations,image_min_size_int,image_max_size_int) ,daemon=True)
            ih_thread.start()

            ih_thread_is_alive = ih_thread.is_alive

            bytes_to_str_dude_core_sum_size = local_bytes_to_str(dude_core.info_size_sum_images)
            fnumber_dude_core_info_counter_images = fnumber(dude_core.info_counter_images)

            aborted=False
            while ih_thread_is_alive():
                anything_changed=False

                size_progress_info=dude_core.info_size_done_perc
                if size_progress_info!=prev_progress_size:
                    prev_progress_size=size_progress_info

                    self_progress_dialog_on_scan_progr1var_set(size_progress_info)
                    self_progress_dialog_on_scan_lab_r1_config(text='%s / %s' % (local_bytes_to_str(dude_core.info_size_done),bytes_to_str_dude_core_sum_size))
                    anything_changed=True

                quant_progress_info=dude_core.info_files_done_perc
                if quant_progress_info!=prev_progress_quant:
                    prev_progress_quant=quant_progress_info

                    self_progress_dialog_on_scan_progr2var_set(quant_progress_info)
                    self_progress_dialog_on_scan_lab_r2_config(text='%s / %s' % (fnumber(dude_core.info_files_done),fnumber_dude_core_info_counter_images))
                    anything_changed=True

                    self_progress_dialog_on_scan_area_main_update()

                if dude_core.can_abort and self.action_abort and not dude_core.abort_action:
                    dude_core.abort_action = True
                    self_progress_dialog_on_scan_lab[3].configure(image='',text='Aborted')
                    self_progress_dialog_on_scan.abort_button.configure(state='disabled',text='',image='')

                self_progress_dialog_on_scan_lab[0].configure(image=self_get_hg_ico(),text='')

                self_status(dude_core.info)

                self_main_after(50,lambda : wait_var_set(not wait_var_get()))
                self_main_wait_variable(wait_var)

            ih_thread.join()

            self_progress_dialog_on_scan_progr1var_set(100)
            self_progress_dialog_on_scan_progr2var_set(100)

            self_progress_dialog_on_scan_lab_r1_config(text='-')
            self_progress_dialog_on_scan_lab_r2_config(text='-')

            self_progress_dialog_on_scan.widget.title('Data clustering')
            self_progress_dialog_on_scan.abort_button.configure(state='disabled',text='',image='')

            ####################################################
            self_progress_dialog_on_scan_lab[0].configure(image=self.ico_empty,text='')
            self_progress_dialog_on_scan_lab[1].configure(text='... Clustering data ...')
            self_progress_dialog_on_scan_lab[2].configure(text='')
            self_progress_dialog_on_scan_lab[3].configure(text='')
            self_progress_dialog_on_scan_lab[4].configure(text='')
            ####################################################

            if operation_mode==MODE_SIMILARITY:
                #clustering
                self_status('Data clustering ...')

                distance = self.similarity_distance_var.get()

                sc_thread=Thread(target=lambda : dude_core.similarity_clustering(hash_size,distance,all_rotations),daemon=True)
                sc_thread.start()

                sc_thread_is_alive = sc_thread.is_alive

                while sc_thread_is_alive():
                    self_progress_dialog_on_scan_lab[0].configure(image=self_get_hg_ico(),text='')

                    self_progress_dialog_on_scan_lab[1].configure(image='',text=dude_core.info_line)

                    self_main_after(50,lambda : wait_var_set(not wait_var_get()))
                    self_main_wait_variable(wait_var)

                sc_thread.join()

            else:
                #gps clustering
                self_status('Data clustering ...')

                distance = self.similarity_distance_var.get()

                gpsc_thread=Thread(target=lambda : dude_core.gps_clustering(distance),daemon=True)
                gpsc_thread.start()

                gpsc_thread_is_alive = gpsc_thread.is_alive

                while gpsc_thread_is_alive():
                    self_progress_dialog_on_scan_lab[0].configure(image=self_get_hg_ico(),text='')

                    self_progress_dialog_on_scan_lab[1].configure(image='',text=dude_core.info_line)

                    self_main_after(50,lambda : wait_var_set(not wait_var_get()))
                    self_main_wait_variable(wait_var)

                gpsc_thread.join()

            self_progress_dialog_on_scan.widget.config(cursor="watch")

            if not self.action_abort:
                self_progress_dialog_on_scan_lab[0].configure(image=self.ico_empty,text='Finished.')
                self_progress_dialog_on_scan_lab[1].configure(image='',text='... Rendering data ...')
                self_progress_dialog_on_scan_lab[2].configure(image='',text='')
                self_progress_dialog_on_scan_lab[3].configure(image='',text='')
                self_progress_dialog_on_scan_lab[4].configure(image='',text='')
                self_progress_dialog_on_scan_area_main_update()

            #############################

            #self_progress_dialog_on_scan.label.configure(text='\n\nrendering data ...\n')
            self_progress_dialog_on_scan.abort_button.pack_forget()
            self_tooltip_message[str_self_progress_dialog_on_scan_abort_button]=''
            self_progress_dialog_on_scan.widget.update()
            self.main.focus_set()

        else:
            self_status('Calculating CRC ...')

            self_progress_dialog_on_scan.widget.title('CRC calculation')

            self_status('Starting CRC threads ...')
            crc_thread=Thread(target=dude_core.crc_calc,daemon=True)
            crc_thread.start()

            update_once=True
            self_progress_dialog_on_scan_lab[0].configure(image=self.ico_empty,text='')
            self_progress_dialog_on_scan_lab[1].configure(image='',text='')
            self_progress_dialog_on_scan_lab[2].configure(image='',text='')
            self_progress_dialog_on_scan_lab[3].configure(image='',text='')
            self_progress_dialog_on_scan_lab[4].configure(image='',text='')

            crc_thread_is_alive = crc_thread.is_alive

            bytes_to_str_dude_core_sum_size = local_bytes_to_str(dude_core.sum_size)

            self_main_after = self.main.after
            wait_var_get = wait_var.get
            wait_var_set = wait_var.set
            self_main_wait_variable = self.main.wait_variable

            #fnumber_dude_core_info_total = fnumber(dude_core.info_total)
            while crc_thread_is_alive():
                anything_changed=False

                size_progress_info=dude_core.info_size_done_perc
                if size_progress_info!=prev_progress_size:
                    prev_progress_size=size_progress_info

                    self_progress_dialog_on_scan_progr1var_set(size_progress_info)
                    self_progress_dialog_on_scan_lab_r1_config(text='%s / %s' % (local_bytes_to_str(dude_core.info_size_done),bytes_to_str_dude_core_sum_size))
                    anything_changed=True

                quant_progress_info=dude_core.info_files_done_perc
                if quant_progress_info!=prev_progress_quant:
                    prev_progress_quant=quant_progress_info

                    self_progress_dialog_on_scan_progr2var_set(quant_progress_info)
                    self_progress_dialog_on_scan_lab_r2_config(text='%s / %s' % (fnumber(dude_core.info_files_done),fnumber(dude_core.info_total)))
                    anything_changed=True

                if anything_changed:
                    if dude_core.info_found_groups:
                        #new_data[1]='Results'
                        new_data[2]='groups: %s' % fnumber(dude_core.info_found_groups)
                        new_data[3]='space: %s' % local_bytes_to_str(dude_core.info_found_dupe_space)
                        new_data[4]='folders: %s' % fnumber(dude_core.info_found_folders)

                        for i in (2,3,4):
                            if new_data[i] != prev_data[i]:
                                prev_data[i]=new_data[i]
                                self_progress_dialog_on_scan_lab[i].configure(text=new_data[i])

                    self_progress_dialog_on_scan_area_main_update()

                now=time()
                if anything_changed:
                    time_without_busy_sign=now
                    #info_line = dude_core.info_line if len(dude_core.info_line)<48 else ('...%s' % dude_core.info_line[-48:])
                    #self_progress_dialog_on_scan_lab[1].configure(text=info_line)

                    if update_once:
                        update_once=False
                        self_tooltip_message[str_self_progress_dialog_on_scan_abort_button]='If you abort at this stage,\npartial results may be available\n(if any groups are found).'
                        self_configure_tooltip(str_self_progress_dialog_on_scan_abort_button)

                        self_progress_dialog_on_scan_lab[0].configure(image=self.ico_empty)
                else :
                    if now>time_without_busy_sign+1.0:
                        self_progress_dialog_on_scan_lab[0].configure(image=self_get_hg_ico(),text='')

                        self_tooltip_message[str_self_progress_dialog_on_scan_abort_button]='crc calculating:\n%s...' % dude_core.info_line
                        self_configure_tooltip(str_self_progress_dialog_on_scan_abort_button)
                        update_once=True

                if dude_core.can_abort:
                    if self.action_abort:
                        self_progress_dialog_on_scan_lab[0].configure(image='',text='Aborted.')
                        self_progress_dialog_on_scan_lab[1].configure(text='... Rendering data ...')
                        self_progress_dialog_on_scan_lab[2].configure(text='')
                        self_progress_dialog_on_scan_lab[3].configure(text='')
                        self_progress_dialog_on_scan_lab[4].configure(text='')
                        self_progress_dialog_on_scan_area_main_update()
                        dude_core.abort()
                        break

                self_status(dude_core.info)

                self_main_after(100,lambda : wait_var_set(not wait_var_get()))
                self_main_wait_variable(wait_var)

            self_progress_dialog_on_scan.widget.config(cursor="watch")

            if not self.action_abort:
                self_progress_dialog_on_scan_lab[0].configure(image='',text='Finished.')
                self_progress_dialog_on_scan_lab[1].configure(image='',text='... Rendering data ...')
                self_progress_dialog_on_scan_lab[2].configure(image='',text='')
                self_progress_dialog_on_scan_lab[3].configure(image='',text='')
                self_progress_dialog_on_scan_lab[4].configure(image='',text='')
                self_progress_dialog_on_scan_area_main_update()

            #self_status('Finishing CRC Thread...')
            #############################

            #self_progress_dialog_on_scan.label.configure(text='\n\nrendering data ...\n')
            self_progress_dialog_on_scan.abort_button.configure(state='disabled',text='',image='')
            self_progress_dialog_on_scan.abort_button.pack_forget()
            self_tooltip_message[str_self_progress_dialog_on_scan_abort_button]=''
            self_progress_dialog_on_scan.widget.update()
            self.main.focus_set()

            crc_thread.join()

        self.groups_show()

        self_progress_dialog_on_scan.widget.config(cursor="")
        self_progress_dialog_on_scan.hide(True)
        self.status=self.status_main_win if windows else self.status_main

        if self.action_abort:
            self.get_info_dialog_on_scan().show('CRC Calculation aborted.','\nResults are partial.\nSome files may remain unidentified as duplicates.')

        if self.cfg.get_bool(CFG_KEY_SHOW_PREVIEW):
            self.show_preview(False)

        return True

    def scan_dialog_show(self,do_scan=False):
        self.exclude_mask_update()
        self.paths_to_scan_update()

        self.scan_dialog.do_command_after_show=self.scan if do_scan else None

        self.scan_dialog.show()

        if dude_core.scanned_paths:
            self.paths_to_scan_from_dialog=dude_core.scanned_paths.copy()

    def paths_to_scan_update(self) :
        self_paths_to_scan_entry_var = self.paths_to_scan_entry_var
        self_paths_to_scan_frames = self.paths_to_scan_frames

        row=0
        for path in self.paths_to_scan_from_dialog:
            self_paths_to_scan_entry_var[row].set(path)
            self_paths_to_scan_frames[row].grid(row=row,column=0,sticky='news',columnspan=3)
            row+=1

        while row<self.MAX_PATHS:
            self_paths_to_scan_entry_var[row].set('')
            self_paths_to_scan_frames[row].grid_remove()
            row+=1

        if len(self.paths_to_scan_from_dialog)==self.MAX_PATHS:
            self.add_path_button.configure(state='disabled',text='')
        else:
            self.add_path_button.configure(state='normal',text='Add path ...')

    def exclude_regexp_set(self):
        self.cfg.set_bool(CFG_KEY_EXCLUDE_REGEXP,self.exclude_regexp_scan.get())

    def exclude_mask_update(self) :
        for subframe in self.exclude_frames:
            subframe.destroy()

        self.exclude_frames=[]
        self.exclude_entry_var={}

        row=0

        for entry in self.cfg_get(CFG_KEY_EXCLUDE,'').split('|'):
            if entry:
                (frame:=Frame(self.exclude_frame,bg=self.bg_color)).grid(row=row,column=0,sticky='news',columnspan=3)
                self.exclude_frames.append(frame)

                self.exclude_entry_var[row]=StringVar(value=entry)
                Entry(frame,textvariable=self.exclude_entry_var[row]).pack(side='left',expand=1,fill='both',pady=1,padx=(2,0))

                remove_expression_button=Button(frame,image=self.ico['delete'],command=lambda entrypar=entry: self.exclude_mask_remove(entrypar),width=3)
                remove_expression_button.pack(side='right',padx=2,pady=1,fill='y')

                self.widget_tooltip(remove_expression_button,'Remove expression from list.')

                row+=1

    def path_to_scan_add_dialog(self):
        initialdir = self.last_dir if self.last_dir else self.cwd
        if res:=askdirectory(title='Select Directory',initialdir=initialdir,parent=self.scan_dialog.area_main):
            self.last_dir=res
            self.path_to_scan_add(normpath(abspath(res)))

    def exclude_mask_add_dir(self):
        initialdir = self.last_dir if self.last_dir else self.cwd
        if res:=askdirectory(title='Select Directory',initialdir=initialdir,parent=self.scan_dialog.area_main):
            self.last_dir=res
            expr = normpath(abspath(res)) + (".*" if self.exclude_regexp_scan.get() else "*")
            self.exclude_mask_string(expr)

    def exclude_mask_add_dialog(self):
        self.get_exclude_dialog_on_scan().show('Specify Exclude expression','expression:','')
        confirmed=self.exclude_dialog_on_scan.res_bool
        mask=self.exclude_dialog_on_scan.res_str

        if confirmed:
            self.exclude_mask_string(mask)

    def exclude_mask_string(self,mask):
        orglist=self.cfg_get(CFG_KEY_EXCLUDE,'').split('|')
        orglist.append(mask)
        self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(orglist))
        self.exclude_mask_update()

    def path_to_scan_remove(self,row) :
        del self.paths_to_scan_from_dialog[row]
        self.paths_to_scan_update()

    def exclude_mask_remove(self,mask) :
        orglist=self.cfg_get(CFG_KEY_EXCLUDE,'').split('|')
        orglist.remove(mask)
        if '' in orglist:
            orglist.remove('')
        self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(orglist))
        self.exclude_mask_update()

    def settings_ok(self):
        update0=False
        update1=False
        update2=False

        if self.cfg_get_bool(CFG_KEY_FULL_CRC)!=self.show_full_crc.get():
            self.cfg.set_bool(CFG_KEY_FULL_CRC,self.show_full_crc.get())
            update1=True
            update2=True

        if self.cfg_get_bool(CFG_KEY_SHOW_TOOLTIPS_HELP)!=self.show_tooltips_help.get():
            self.cfg.set_bool(CFG_KEY_SHOW_TOOLTIPS_HELP,self.show_tooltips_help.get())

        if self.cfg_get_bool(CFG_KEY_SHOW_TOOLTIPS_INFO)!=self.show_tooltips_info.get():
            self.cfg.set_bool(CFG_KEY_SHOW_TOOLTIPS_INFO,self.show_tooltips_info.get())

        if self.cfg_get_bool(CFG_KEY_PREVIEW_AUTO_UPDATE)!=self.preview_auto_update.get():
            self.cfg.set_bool(CFG_KEY_PREVIEW_AUTO_UPDATE,self.preview_auto_update.get())
            self.preview_auto_update_bool = self.cfg_get_bool(CFG_KEY_PREVIEW_AUTO_UPDATE)

        if self.cfg_get_bool(CFG_KEY_FULL_PATHS)!=self.show_full_paths.get():
            self.cfg.set_bool(CFG_KEY_FULL_PATHS,self.show_full_paths.get())
            update1=True
            update2=True

        if self.cfg_get(CFG_KEY_SHOW_MODE)!=self.show_mode.get():
            self.cfg.set(CFG_KEY_SHOW_MODE,self.show_mode.get())
            update0=True

        if self.cfg_get_bool(CFG_KEY_REL_SYMLINKS)!=self.create_relative_symlinks.get():
            self.cfg.set_bool(CFG_KEY_REL_SYMLINKS,self.create_relative_symlinks.get())

        if self.cfg_get_bool(CFG_ERASE_EMPTY_DIRS)!=self.erase_empty_directories.get():
            self.cfg.set_bool(CFG_ERASE_EMPTY_DIRS,self.erase_empty_directories.get())

        if self.cfg_get_bool(CFG_ABORT_ON_ERROR)!=self.abort_on_error.get():
            self.cfg.set_bool(CFG_ABORT_ON_ERROR,self.abort_on_error.get())

        if self.cfg_get_bool(CFG_SEND_TO_TRASH)!=self.send_to_trash.get():
            self.cfg.set_bool(CFG_SEND_TO_TRASH,self.send_to_trash.get())

        if self.cfg_get_bool(CFG_ALLOW_DELETE_ALL)!=self.allow_delete_all.get():
            self.cfg.set_bool(CFG_ALLOW_DELETE_ALL,self.allow_delete_all.get())

        if self.cfg_get_bool(CFG_SKIP_INCORRECT_GROUPS)!=self.skip_incorrect_groups.get():
            self.cfg.set_bool(CFG_SKIP_INCORRECT_GROUPS,self.skip_incorrect_groups.get())

        if self.cfg_get_bool(CFG_ALLOW_DELETE_NON_DUPLICATES)!=self.allow_delete_non_duplicates.get():
            self.cfg.set_bool(CFG_ALLOW_DELETE_NON_DUPLICATES,self.allow_delete_non_duplicates.get())

        if self.cfg_get_bool(CFG_CONFIRM_SHOW_CRCSIZE)!=self.confirm_show_crc_and_size.get():
            self.cfg.set_bool(CFG_CONFIRM_SHOW_CRCSIZE,self.confirm_show_crc_and_size.get())

        if self.cfg_get_bool(CFG_CONFIRM_SHOW_LINKSTARGETS)!=self.confirm_show_links_targets.get():
            self.cfg.set_bool(CFG_CONFIRM_SHOW_LINKSTARGETS,self.confirm_show_links_targets.get())

        if self.cfg_get(CFG_KEY_WRAPPER_FILE)!=self.file_open_wrapper.get():
            self.cfg.set(CFG_KEY_WRAPPER_FILE,self.file_open_wrapper.get())

        if self.cfg_get(CFG_KEY_WRAPPER_FOLDERS)!=self.folders_open_wrapper.get():
            self.cfg.set(CFG_KEY_WRAPPER_FOLDERS,self.folders_open_wrapper.get())

        if self.cfg_get(CFG_KEY_WRAPPER_FOLDERS_PARAMS)!=self.folders_open_wrapper_params.get():
            self.cfg.set(CFG_KEY_WRAPPER_FOLDERS_PARAMS,self.folders_open_wrapper_params.get())

        self.cfg.write()

        self.settings_dialog.hide()

        if update0:
            self.groups_show()

        if update1:
            self.groups_tree_update_crc_and_path()

        if update2:
            if self.sel_crc and self.sel_item and self.sel_path_full:
                self.tree_folder_update()
            else:
                self.tree_folder_update_none()

    def settings_reset(self):
        _ = {var.set(cfg_defaults[key]) for var,key in self.settings}
        _ = {var.set(cfg_defaults[key]) for var,key in self.settings_str}

    def file_remove_callback(self,size,crc,index_tuple):
        #print('file_remove_callback',size,crc,index_tuple)
        #l_info(f'file_remove_callback {size},{crc},{index_tuple}')

        try:
            if self.operation_mode in (MODE_SIMILARITY,MODE_GPS):
                (pathnr,path,file_name,ctime,dev,inode,size_file)=index_tuple
            else:
                (pathnr,path,file_name,ctime,dev,inode)=index_tuple

            item = self.idfunc(inode,dev)

            self.groups_tree.delete(item)
            self.tagged_discard(item)

            if item==self.selected[self.groups_tree]:
                self.selected[self.groups_tree]=None

            #to bedzie przeliczone
            #self.tree_children_sub[crc].remove(item)
        except Exception as e:
            self.selected[self.groups_tree]=None
            l_error(f'file_remove_callback,{size},{crc},{index_tuple},{e}')

        #l_info('file_remove_callback done')

    def crc_remove_callback(self,crc):
        #print('crc_remove_callback',crc)

        try:
            self.groups_tree.delete(crc)

            if item:=self.selected[self.groups_tree]:
                if self.id2crc[item]==crc:
                    self.selected[self.groups_tree]=None

            #to bedzie przeliczone
            #self.tree_children[self.groups_tree].remove(crc)
        except Exception as e:
            self.selected[self.groups_tree]=None
            l_error(f'crc_remove_callback,{crc},{e}')

    @catched
    def create_my_prev_next_dicts(self,tree):
        my_next_dict = self.my_next_dict[tree]={}
        my_prev_dict = self.my_prev_dict[tree]={}
        prev2,prev1 = None,None

        children = self.tree_children[tree]=tree.get_children()

        if tree==self.groups_tree:
            self_tree_children_sub = self.tree_children_sub={}

        if top_nodes := children:
            first=top_nodes[0]
            tree_get_children = tree.get_children
            for top_node in top_nodes:
                prev2,prev1 = prev1,top_node
                my_next_dict[prev2],my_prev_dict[prev1] = prev1,prev2

                if sub_children := tree_get_children(top_node):
                    self_tree_children_sub[top_node] = sub_children

                    for subnode in sub_children:
                        prev2,prev1 = prev1,subnode
                        my_next_dict[prev2],my_prev_dict[prev1] = prev1,prev2

            my_next_dict[prev1],my_prev_dict[first] = first,prev1

    @logwrapper
    def data_precalc(self):
        self.status('Precalculating data...')

        self.create_my_prev_next_dicts(self.groups_tree)
        self_tree_children = self.tree_children

        self.status_groups_configure(text=fnumber(len(self_tree_children[self.groups_tree])) + ' ',image=self.ico['warning' if self.cfg_get(CFG_KEY_SHOW_MODE)!='0' else 'empty'],compound='right',width=80,anchor='w')

        path_stat_size={}
        path_stat_size_get=path_stat_size.get

        path_stat_quant={}
        path_stat_quant_get=path_stat_quant.get

        self_id2crc = self.id2crc = {}

        self.biggest_file_of_path.clear()
        self.biggest_file_of_path_id.clear()
        self_biggest_file_of_path = self.biggest_file_of_path
        self_biggest_file_of_path_get = self_biggest_file_of_path.get
        self_biggest_file_of_path_id = self.biggest_file_of_path_id

        self_idfunc=self.idfunc

        self_crc_to_size = self.crc_to_size
        self_files_of_groups_filtered_by_mode = self.files_of_groups_filtered_by_mode

        if self.operation_mode in (MODE_SIMILARITY,MODE_GPS):
            for group_index,items_set in dude_core.files_of_images_groups.items():
                crc = group_index
                if crc in self_files_of_groups_filtered_by_mode:
                    for pathnr,path,file,ctime,dev,inode,size in items_set:
                        if (dev,inode) in self_files_of_groups_filtered_by_mode[crc]:
                            item_id = self_idfunc(inode,dev)
                            self_id2crc[item_id]=(crc,ctime)
                            path_index=(pathnr,path)
                            path_stat_size[path_index] = path_stat_size_get(path_index,0) + size
                            path_stat_quant[path_index] = path_stat_quant_get(path_index,0) + 1

                            if size>self_biggest_file_of_path_get(path_index,0):
                                self_biggest_file_of_path[path_index]=size
                                self_biggest_file_of_path_id[path_index]=item_id

        else:
            for size,size_dict in dude_core.files_of_size_of_crc_items():
                for crc,crc_dict in size_dict.items():
                    if crc in self_files_of_groups_filtered_by_mode:
                        for pathnr,path,file,ctime,dev,inode in crc_dict:
                            if (dev,inode) in self_files_of_groups_filtered_by_mode[crc]:
                                item_id = self_idfunc(inode,dev)
                                self_id2crc[item_id]=(crc,ctime)
                                path_index=(pathnr,path)
                                path_stat_size[path_index] = path_stat_size_get(path_index,0) + size
                                path_stat_quant[path_index] = path_stat_quant_get(path_index,0) + 1

                                if size>self_biggest_file_of_path_get(path_index,0):
                                    self_biggest_file_of_path[path_index]=size
                                    self_biggest_file_of_path_id[path_index]=item_id

                        if crc not in self_crc_to_size:
                            print('Qriozum !!!',crc,size)

        self_tree_children_sub = self.tree_children_sub

        self_tree_children_self_groups_tree = self_tree_children[self.groups_tree]

        self_groups_tree_item_to_data = self.groups_tree_item_to_data

        self.path_stat_list_size=tuple(sorted([(pathnr,path,number) for (pathnr,path),number in path_stat_size.items()],key=lambda x : x[2],reverse=True))
        self.path_stat_list_quant=tuple(sorted([(pathnr,path,number) for (pathnr,path),number in path_stat_quant.items()],key=lambda x : x[2],reverse=True))
        self.groups_combos_size = tuple(sorted([(crc_item,sum([self_groups_tree_item_to_data[item][1] for item in self_tree_children_sub[crc_item]])) for crc_item in self_tree_children_self_groups_tree],key = lambda x : x[1],reverse = True))

        self.groups_combos_quant = tuple(sorted([(crc_item,len(self_tree_children_sub[crc_item])) for crc_item in self_tree_children_self_groups_tree],key = lambda x : x[1],reverse = True))
        self.status('')

        if not self_tree_children_self_groups_tree:
            self.tree_folder_update_none()
            self.reset_sels()

    @logwrapper
    def initial_focus(self):
        if children := self.tree_children[self.groups_tree]:
            first_node_file=self.tree_children_sub[children[0]][0]
            self.groups_tree.focus_set()
            self.groups_tree_focus(first_node_file)
            self.groups_tree_see(first_node_file)
            self.groups_tree_sel_change(first_node_file)
        else:
            self.tree_folder_update_none()
            self.reset_sels()

    @block_and_log
    def groups_show(self):
        if self.operation_mode in (MODE_SIMILARITY,MODE_GPS):
            self.groups_tree.heading('#0',text='GROUP/Scan Path',anchor='w')
            self.folder_tree.heading('#0',text='GROUP',anchor='w')
        else:
            self.groups_tree.heading('#0',text='CRC/Scan Path',anchor='w')
            self.folder_tree.heading('#0',text='CRC',anchor='w')

        self_idfunc=self.idfunc = (lambda i,d : '%s-%s' % (i,d)) if len(dude_core.devs)>1 else (lambda i,d : str(i))

        self_status=self.status

        self_status('Cleaning tree...')
        self.reset_sels()
        self_groups_tree = self.groups_tree

        self_groups_tree.delete(*self.tree_children[self_groups_tree])

        self.selected[self.groups_tree]=None
        self.sel_full_path_to_file=''

        show_mode = self.cfg_get(CFG_KEY_SHOW_MODE)
        show_full_crc=self.cfg_get_bool(CFG_KEY_FULL_CRC)
        show_full_paths=self.cfg_get_bool(CFG_KEY_FULL_PATHS)

        self_status('Rendering data...')

        show_mode_cross=bool(show_mode=='1')
        show_mode_same_dir=bool(show_mode=='2')

        self.tagged.clear()

        self_CRC = self.CRC
        self_FILE = self.FILE
        self_groups_tree_insert=self_groups_tree.insert
        self_groups_tree_item_to_data = self.groups_tree_item_to_data = {}
        self_iid_to_size=self.iid_to_size
        self.iid_to_size.clear()
        localtime_catched_local = localtime_catched
        dude_core_scanned_paths=dude_core.scanned_paths
        self_icon_nr=self.icon_nr
        local_bytes_to_str = bytes_to_str

        files_of_groups_filtered_by_mode=self.files_of_groups_filtered_by_mode=defaultdict(set)

        if self.operation_mode in (MODE_SIMILARITY,MODE_GPS):
            #####################################################

            for group_index,items_set in dude_core.files_of_images_groups.items():
                crc = group_index
                size_str_group = ''
                size = 0
                size_h_group = ''
                instances_str = len(items_set)

                if show_mode_cross:
                    is_cross_group = bool(len({pathnr for pathnr,path,file,ctime,dev,inode,size in items_set})>1)
                    if not is_cross_group:
                        continue
                elif show_mode_same_dir:
                    hist=defaultdict(int)
                    for pathnr,path,file,ctime,dev,inode,size in items_set:
                        hist[(pathnr,path)]+=1
                    if not any(val for val in hist.values() if val>1):
                        continue

                group_item=self_groups_tree_insert('','end',crc, values=('','','',size_str_group,size_h_group,'','','',crc,instances_str,instances_str,'',self_CRC),tags=self_CRC,open=True,text = crc)
                #kind,crc,(pathnr,path,file,ctime,dev,inode)
                self_groups_tree_item_to_data[group_item]=(self_CRC,size,crc,(None,None,None,None,None,None) )

                for pathnr,path,file,ctime,dev,inode,size in sorted(items_set,key=lambda x : (x[6],x[0],x[1],x[2]),reverse=True):
                    if show_mode_same_dir:
                        if hist[(pathnr,path)]==1:
                            continue

                    files_of_groups_filtered_by_mode[group_index].add( (dev,inode) )

                    #print(pathnr,path,file,mtime,ctime,dev,inode,size)
                    iid=self_idfunc(inode,dev)
                    self_iid_to_size[iid]=size

                    size_str = str(size)
                    size_h = local_bytes_to_str(size)

                    #self_groups_tree["columns"]=('pathnr','path','file','size','size_h','ctime','dev','inode','crc','instances','instances_h','ctime_h','kind')
                    file_item = self_groups_tree_insert(group_item,'end',iid, values=(\
                                str(pathnr),path,file,size_str,\
                                size_h,\
                                str(ctime),str(dev),str(inode),crc,\
                                '','',\
                                strftime('%Y/%m/%d %H:%M:%S',localtime_catched_local(ctime//1000000000)),self_FILE),tags='',text=dude_core_scanned_paths[pathnr] if show_full_paths else '',image=self_icon_nr[pathnr]) #DE_NANO= 1_000_000_000

                    #kind,crc,index_tuple
                    #kind,crc,(pathnr,path,file,ctime,dev,inode)
                    self_groups_tree_item_to_data[file_item]=(self_FILE,size,crc, (pathnr,path,file,ctime,dev,inode) )
        else:
            #####################################################

            sizes_counter=0

            dude_core_crc_cut_len=dude_core.crc_cut_len

            for size,size_dict in dude_core.files_of_size_of_crc_items() :
                size_h = local_bytes_to_str(size)
                size_str = str(size)
                if not sizes_counter%128:
                    self_status('Rendering data... (%s)' % size_h,do_log=False)

                sizes_counter+=1
                for crc,crc_dict in size_dict.items():
                    if show_mode_cross:
                        is_cross_group = bool(len({pathnr for pathnr,path,file,ctime,dev,inode in crc_dict})>1)
                        if not is_cross_group:
                            continue
                    elif show_mode_same_dir:
                        hist=defaultdict(int)
                        for pathnr,path,file,ctime,dev,inode in crc_dict:
                            hist[(pathnr,path)]+=1
                        if not any(val for val in hist.values() if val>1):
                            continue

                    #self_groups_tree["columns"]=('pathnr','path','file','size','size_h','ctime','dev','inode','crc','instances','instances_h','ctime_h','kind')
                    instances_str=str(len(crc_dict))
                    crc_item=self_groups_tree_insert('','end',crc, values=('','','',size_str,size_h,'','','',crc,instances_str,instances_str,'',self_CRC),tags=self_CRC,open=True,text= crc if show_full_crc else crc[:dude_core_crc_cut_len])

                    #kind,crc,index_tuple
                    #kind,crc,(pathnr,path,file,ctime,dev,inode)
                    self_groups_tree_item_to_data[crc_item]=(self_CRC,size,crc,(None,None,None,None,None,None) )

                    for pathnr,path,file,ctime,dev,inode in sorted(crc_dict,key = lambda x : x[0]):
                        if show_mode_same_dir:
                            if hist[(pathnr,path)]==1:
                                continue

                        files_of_groups_filtered_by_mode[crc].add( (dev,inode) )

                        iid=self_idfunc(inode,dev)
                        self_iid_to_size[iid]=size

                        file_item = self_groups_tree_insert(crc_item,'end',iid, values=(\
                                str(pathnr),path,file,size_str,\
                                '',\
                                str(ctime),str(dev),str(inode),crc,\
                                '','',\
                                strftime('%Y/%m/%d %H:%M:%S',localtime_catched_local(ctime//1000000000)),self_FILE),tags='',text=dude_core_scanned_paths[pathnr] if show_full_paths else '',image=self_icon_nr[pathnr]) #DE_NANO= 1_000_000_000

                        #kind,crc,index_tuple
                        #kind,crc,(pathnr,path,file,ctime,dev,inode)
                        self_groups_tree_item_to_data[file_item]=(self_FILE,size,crc, (pathnr,path,file,ctime,dev,inode) )

            self.crc_to_size={crc:size for size,size_dict in dude_core.files_of_size_of_crc.items() for crc in size_dict }

        self.data_precalc()

        #####################################################

        if self.column_sort_last_params[self_groups_tree]!=self.column_groups_sort_params_default:
            #defaultowo po size juz jest, nie trzeba tracic czasu
            self.column_sort(self_groups_tree)
        else:
            self.column_sort_set_arrow(self_groups_tree)
            #self.create_my_prev_next_dicts(self_groups_tree)

        self.initial_focus()
        self.calc_mark_stats_groups()

        #self.menu_enable()
        self_status('')

    @block_and_log
    def groups_tree_update_crc_and_path(self,configure_icon=False):
        self.status('Updating items ...')
        self.main_update()

        show_full_crc=self.cfg_get_bool(CFG_KEY_FULL_CRC)
        show_full_paths=self.cfg_get_bool(CFG_KEY_FULL_PATHS)

        self_idfunc=self.idfunc
        dude_core_crc_cut_len=dude_core.crc_cut_len

        self_groups_tree_item=self.groups_tree.item
        self_icon_nr=self.icon_nr
        dude_core_scanned_paths=dude_core.scanned_paths
        self_crc_to_size=self.crc_to_size
        self_groups_tree_item_to_data = self.groups_tree_item_to_data
        for size,size_dict in dude_core.files_of_size_of_crc_items() :
            for crc,crc_dict in size_dict.items():
                if crc in self_crc_to_size:
                    if crc in self_groups_tree_item_to_data:# dla cross paths moze nie istniec item crc
                        self_groups_tree_item(crc,text=crc if show_full_crc else crc[:dude_core_crc_cut_len])
                        for pathnr,path,file,ctime,dev,inode in crc_dict:
                            if configure_icon:
                                self_groups_tree_item(self_idfunc(inode,dev),image=self_icon_nr[pathnr],text=dude_core_scanned_paths[pathnr] if show_full_paths else '')
                            else:
                                self_groups_tree_item(self_idfunc(inode,dev),text=dude_core_scanned_paths[pathnr] if show_full_paths else '')

        self.status('')

    def groups_tree_update_none(self):
        self.groups_tree.selection_remove(self.groups_tree.selection())

    def groups_tree_update(self,item):
        self_groups_tree = self.groups_tree

        self.semi_selection(self_groups_tree,item)

        self_groups_tree.see(item)
        self_groups_tree.update()

    current_folder_items=()
    current_folder_items_tagged=set()
    current_folder_items_tagged_clear=current_folder_items_tagged.clear

    def tree_folder_update_none(self):
        self.folder_tree_configure(takefocus=False)

        if self.current_folder_items:
            self.folder_tree_delete(*self.current_folder_items)
            self.selected[self.folder_tree]=None

        self.status_folder_size_configure(text='')
        self.status_folder_quant_configure(text='')

        self.status_path_configure(text='')
        self.current_folder_items=()

        self.current_folder_items_tagged_clear()

    @block
    def tree_folder_update(self,arbitrary_path=None):
        ftree = self.folder_tree
        self.folder_tree_configure(takefocus=False)

        current_path=arbitrary_path if arbitrary_path else self.sel_path_full

        #print('current_path:',current_path)

        if not current_path:
            return False

        show_full_crc=self.cfg_get_bool(CFG_KEY_FULL_CRC)

        col_sort,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[ftree]
        sort_index_local=sort_index-1

        i=0
        sort_val_func = int if is_numeric else lambda x : x

        self_idfunc=self.idfunc

        self_id2crc=self.id2crc
        dude_core_crc_cut_len=dude_core.crc_cut_len
        dude_core_files_of_size_of_crc=dude_core.files_of_size_of_crc
        dude_core_files_of_images_groups = dude_core.files_of_images_groups

        NONE_ICON=''
        FOLDER_ICON=self.ico_folder
        HARDLINK_ICON=self.ico_hardlink
        FILE_SOFT_LINK_ICON=self.ico_softlink
        DIR_SOFT_LINK_ICON=self.ico_softlink_dir

        self_DIRLINK = self.DIRLINK
        self_LINK = self.LINK
        self_DIR = self.DIR
        self_SINGLE = self.SINGLE
        self_SINGLEHARDLINKED = self.SINGLEHARDLINKED
        self_FILE = self.FILE
        self_MARK = self.MARK

        local_bytes_to_str = bytes_to_str

        self_tagged=self.tagged
        self_current_folder_items_tagged=self.current_folder_items_tagged
        self_current_folder_items_tagged_add=self_current_folder_items_tagged.add
        self_current_folder_items_tagged.clear()
        current_folder_items_tagged_size=0

        local_strftime = strftime
        local_localtime_catched = localtime_catched
        folder_items=set()
        folder_items_add=folder_items.add

        if self.two_dots_condition(current_path):
            values=('..','','',self.UPDIR,'',0,'',0,'',0,'')
            folder_items_add((updir_code,sort_val_func(values[sort_index_local]),'0UP','',values,self_DIR,''))

        operation_mode = self.operation_mode
        operation_mode_images = bool(operation_mode in (MODE_SIMILARITY,MODE_GPS))
        operation_mode_images_gps = bool(operation_mode==MODE_GPS)
        #############################################
        try:
            with scandir(current_path) as res:
                for entry in res:
                    name,isdir,is_link=entry.name,entry.is_dir(),entry.is_symlink()

                    if is_link:
                        values = (name,'','',self_DIRLINK if isdir else self_LINK,'','0','','0','','1','')
                        folder_items_add((dir_code if isdir else non_dir_code,sort_val_func(values[sort_index_local]),('%sDL' % i) if isdir else ('%sFL' % i),'',values,self_DIR if isdir else self_LINK,DIR_SOFT_LINK_ICON if isdir else FILE_SOFT_LINK_ICON))
                        i+=1
                    else:
                        try:
                            stat_res = stat(entry)
                        except Exception as e:
                            self.status(str(e))
                            continue
                        else:
                            dev,inode = stat_res.st_dev,stat_res.st_ino
                            if isdir:
                                values = (name,str(dev),str(inode),self_DIR,'','0','','0','','1','')
                                folder_items_add((dir_code,sort_val_func(values[sort_index_local]),'%sD' % i,'',values,self_DIR,FOLDER_ICON))

                                i+=1
                            elif entry.is_file():
                                ctime,size_num = stat_res.st_ctime_ns,stat_res.st_size
                                file_id=self_idfunc(inode,dev)

                                ctime_h = local_strftime('%Y/%m/%d %H:%M:%S',local_localtime_catched(ctime//1000000000)) #DE_NANO

                                size_h=local_bytes_to_str(size_num)

                                item_rocognized=True
                                if file_id in self_id2crc:
                                    crc,core_ctime=self_id2crc[file_id]

                                    if ctime != core_ctime:
                                        item_rocognized=False
                                    else:
                                        values = (name,str(dev),str(inode),self_FILE,crc,str(size_num),size_h,str(ctime),ctime_h,instances_both := str(len(dude_core_files_of_images_groups[crc]) if operation_mode_images else len(dude_core_files_of_size_of_crc[size_num][crc])),instances_both)
                                        in_tagged=bool(file_id in self_tagged)
                                        if in_tagged:
                                            self_current_folder_items_tagged_add(file_id)
                                            current_folder_items_tagged_size+=size_num

                                        folder_items_add((non_dir_code,sort_val_func(values[sort_index_local]),file_id,crc if show_full_crc else crc[:dude_core_crc_cut_len],values,self_MARK if in_tagged else '',NONE_ICON))
                                else:
                                    item_rocognized=False

                                if not item_rocognized:
                                    nlink = stat_res.st_nlink
                                    values = (name,str(dev),str(inode),self_SINGLEHARDLINKED if nlink>1 else self_SINGLE,'',str(size_num),size_h,str(ctime),ctime_h,'1','')

                                    folder_items_add((non_dir_code,sort_val_func(values[sort_index_local]),'%sO' % i,'(%s)' % nlink if nlink>1 else '',values,self_SINGLE,HARDLINK_ICON if nlink>1 else NONE_ICON))

                                    i+=1
                            else:
                                l_error('another: %s:%s,%s ?',current_path,name,is_link)
                                continue

        except Exception as e:
            self.status(str(e))
            return False

        ############################################################

        if arbitrary_path:
            self.sel_tree = ftree
            self.sel_pathnr = None
            self.sel_file = None
            self.sel_crc = None
            self.sel_item = None
            self.sel_kind = None

            self.sel_path_set(str(Path(arbitrary_path)))

        ftree_insert=ftree.insert

        if self_current_folder_items := self.current_folder_items:
            self.folder_tree_delete(*self_current_folder_items)
            self.selected[ftree]=None

        try:
            current_folder_items_all=tuple( ( (ftree_insert('','end',iid, text=text, values=values,tags=tag,image=image),values[0],values[3],values[4]) for _,_,iid,text,values,tag,image in sorted(folder_items,reverse=reverse,key=lambda x : (x[0:3]) ) ) )
            self.current_folder_items = tuple([item_tuple[0] for item_tuple in current_folder_items_all])
            #'file','kind','crc'
            self.current_folder_items_dict = { item_tuple[0]:item_tuple[1:4] for item_tuple in current_folder_items_all }

        except Exception as e:
            self.status(str(e))
            l_error(e)

        if not arbitrary_path:
            try:
                self.semi_selection(ftree,self.sel_item)
                ftree.see(self.sel_item)
            except Exception:
                pass

        self.status_folder_quant_configure(text=fnumber(len(self_current_folder_items_tagged)))
        self.status_folder_size_configure(text=bytes_to_str(current_folder_items_tagged_size))

        ftree.update()

        folder_items_len = len(self.current_folder_items)

        self.folder_tree_configure(takefocus=True)

        self.create_my_prev_next_dicts(ftree)

        return True

    def update_marks_folder(self):
        self_folder_tree_item=self.folder_tree.item

        self_tagged = self.tagged

        self_MARK = self.MARK
        self_FILE = self.FILE
        self.current_folder_items_tagged_clear()
        self_current_folder_items_tagged_add=self.current_folder_items_tagged_add

        for item in self.current_folder_items:
            #cant unset other tags !
            kind = self.current_folder_items_dict[item][1]
            if kind==self_FILE:
                in_tagged=bool(item in self_tagged)
                self_folder_tree_item( item,tags=self_MARK if in_tagged else '')
                if in_tagged:
                    self_current_folder_items_tagged_add(item)

    def calc_mark_stats_groups(self):
        self_tagged = self.tagged
        self.status_all_quant_configure(text=fnumber(len(self_tagged)))
        self_iid_to_size=self.iid_to_size
        self.status_all_size_configure(text=bytes_to_str(sum([self_iid_to_size[iid] for iid in self_tagged])))

    def calc_mark_stats_folder(self):
        self_current_folder_items_tagged = self.current_folder_items_tagged
        self.status_folder_quant_configure(text=fnumber(len(self_current_folder_items_tagged)))

        self_iid_to_size = self.iid_to_size
        self.status_folder_size_configure(text=bytes_to_str(sum(self_iid_to_size[iid] for iid in self_current_folder_items_tagged)))

    def mark_in_specified_group_by_ctime(self, action, crc, reverse,select=False):
        self_groups_tree = self.groups_tree
        self_tree_children_sub = self.tree_children_sub
        self_groups_tree_item_to_data = self.groups_tree_item_to_data

        item=sorted([ (item,self_groups_tree_item_to_data[item][3][3] ) for item in self_tree_children_sub[crc]],key=lambda x : int(x[1]),reverse=reverse)[0][0]
        if item:
            action(item,self_groups_tree)
            if select:
                self_groups_tree.see(item)
                self_groups_tree.focus(item)
                self.groups_tree_sel_change(item)
                self_groups_tree.update()

    @block
    def mark_all_by_ctime(self,order_str, action):
        self.status('Un/Setting marking on all files ...')
        reverse=0 if order_str=='oldest' else 1

        self_mark_in_specified_group_by_ctime = self.mark_in_specified_group_by_ctime
        _ = { self_mark_in_specified_group_by_ctime(action, crc, reverse) for crc in self.tree_children[self.groups_tree] }

        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @block
    def mark_in_group_by_ctime(self,order_str,action):
        self.status('Un/Setting marking in group ...')
        reverse=0 if order_str=='oldest' else 1
        self.mark_in_specified_group_by_ctime(action,self.sel_crc,reverse,True)
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    def mark_in_specified_crc_group(self,action,crc):
        self_groups_tree = self.groups_tree
        _ = { action(item,self_groups_tree) for item in self.tree_children_sub[crc] }

    @block
    def mark_in_group(self,action):
        self.status('Un/Setting marking in group ...')
        self.mark_in_specified_crc_group(action,self.sel_crc)
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @block
    def mark_on_all(self,action):
        self.status('Un/Setting marking on all files ...')
        self_mark_in_specified_crc_group = self.mark_in_specified_crc_group
        _ = { self_mark_in_specified_crc_group(action,crc) for crc in self.tree_children[self.groups_tree] }

        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @block
    def mark_in_folder(self,action):
        self.status('Un/Setting marking in folder ...')
        self_groups_tree = self.groups_tree
        self_folder_tree = self.folder_tree
        self_FILE=self.FILE
        self_current_folder_items=self.current_folder_items

        self_current_folder_items_dict = self.current_folder_items_dict

        _ = { (action(item,self_folder_tree),action(item,self_groups_tree)) for item in self_current_folder_items if self_current_folder_items_dict[item][1]==self_FILE }

        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    def set_mark(self,item,tree):
        tree.item(item,tags=self.MARK)
        self.tagged_add(item)
        self_current_folder_items_tagged_add = self.current_folder_items_tagged_add
        if item in self.current_folder_items:
            self_current_folder_items_tagged_add(item)

    def unset_mark(self,item,tree):
        tree.item(item,tags='')
        self.tagged_discard(item)
        self.current_folder_items_tagged_discard(item)

    def invert_mark(self,item,tree):
        if tree.item(item)['tags']:
            tree.item(item,tags='')
            self.tagged_discard(item)
            self.current_folder_items_tagged_discard(item)
        else:
            tree.item(item,tags=self.MARK)
            self.tagged_add(item)
            self.current_folder_items_tagged_add(item)

    @block_and_log
    def action_on_path(self,path_param,action,all_groups=True):
        self.status('Un/Setting marking in subdirectory ...')

        if all_groups:
            crc_range = self.tree_children[self.groups_tree]
        else :
            crc_range = [str(self.sel_crc)]

        sel_count=0
        self_item_full_path = self.item_full_path

        dude_core_name_func = dude_core.name_func
        path_param_abs = dude_core.name_func(normpath(abspath(path_param)).rstrip(sep))

        for crc_item in crc_range:
            for item in self.tree_children_sub[crc_item]:
                fullpath = dude_core_name_func(self_item_full_path(item))

                if fullpath.startswith(path_param_abs + sep):
                    action(item,self.groups_tree)
                    sel_count+=1

        if not sel_count :
            self.get_info_dialog_on_main().show('No files found for specified path',path_param_abs)
        else:
            self.status(f'Subdirectory action. {sel_count} File(s) Found')
            self.update_marks_folder()
            self.calc_mark_stats_groups()
            self.calc_mark_stats_folder()

    expr_by_tree={}
    expr_by_tree_re={}

    def mark_expression(self,action,prompt,all_groups=True):
        tree=self.main.focus_get()
        tree_index = self.tree_index[tree]

        cfg_key = CFG_KEY_MARK_STRING_0 if tree_index==0 else CFG_KEY_MARK_STRING_1
        cfg_key_re = CFG_KEY_MARK_RE_0 if tree_index==0 else CFG_KEY_MARK_RE_1

        if tree in self.expr_by_tree:
            initialvalue=self.expr_by_tree[tree]
        else:
            initialvalue=self.cfg.get(cfg_key)

        if tree in self.expr_by_tree_re:
            initialvalue_re=self.expr_by_tree_re[tree]
        else:
            initialvalue_re=self.cfg.get(cfg_key_re)

        if tree==self.groups_tree:
            range_str = " (all groups)" if all_groups else " (selected group)"
            title='Specify expression for full file path.'
        else:
            range_str = ''
            title='Specify expression for file names in selected directory.'

        if tree==self.groups_tree:
            self.get_mark_dialog_on_groups().show(title,prompt + f'{range_str}', initial=initialvalue,checkbutton_text='treat as a regular expression',checkbutton_initial=initialvalue_re)
            res_code = self.mark_dialog_on_groups.res_bool
            use_reg_expr = self.mark_dialog_on_groups.check_val.get()
            self.expr_by_tree[tree] = expression = self.mark_dialog_on_groups.entry_val.get()
        else:
            self.get_mark_dialog_on_folder().show(title,prompt + f'{range_str}', initial=initialvalue,checkbutton_text='treat as a regular expression',checkbutton_initial=initialvalue_re)
            res_code = self.mark_dialog_on_folder.res_bool
            use_reg_expr = self.mark_dialog_on_folder.check_val.get()
            self.expr_by_tree[tree] = expression = self.mark_dialog_on_folder.entry_val.get()

        items=[]
        items_append = items.append
        use_reg_expr_info = '(regular expression)' if use_reg_expr else ''

        self.cfg.set(cfg_key,expression)
        self.cfg.set_bool(cfg_key_re,use_reg_expr)

        if res_code:
            self_item_full_path = self.item_full_path

            if tree==self.groups_tree:
                crc_range = self.tree_children[tree] if all_groups else [str(self.sel_crc)]

                for crc_item in crc_range:
                    for item in self.tree_children_sub[crc_item]:
                        fullpath = self_item_full_path(item)
                        try:
                            if (use_reg_expr and search(expression,fullpath)) or (not use_reg_expr and fnmatch(fullpath,expression) ):
                                items_append(item)
                        except Exception as e:
                            self.get_info_dialog_on_main().show('expression Error !',f'expression:"{expression}"  {use_reg_expr_info}\n\nERROR:{e}')
                            tree.focus_set()
                            return
            else:
                self_current_folder_items_dict = self.current_folder_items_dict

                for item in self.current_folder_items:
                    if self_current_folder_items_dict[item][1]==self.FILE:
                        file=self_current_folder_items_dict[item][0]
                        try:
                            if (use_reg_expr and search(expression,file)) or (not use_reg_expr and fnmatch(file,expression) ):
                                items_append(item)
                        except Exception as e:
                            self.get_info_dialog_on_main().show('expression Error !',f'expression:"{expression}"  {use_reg_expr_info}\n\nERROR:{e}')
                            tree.focus_set()
                            return

            if items:
                self.main_config(cursor="watch")
                self.menu_disable()
                self.main_update()

                first_item=items[0]

                tree.focus(first_item)
                tree.see(first_item)

                if tree==self.groups_tree:
                    for item in items:
                        action(item,tree)

                    self.groups_tree_sel_change(first_item)
                else:
                    for item in items:
                        action(item,self.groups_tree)
                        action(item,self.folder_tree)

                    self.folder_tree_sel_change(first_item)

                self.update_marks_folder()
                self.calc_mark_stats_groups()
                self.calc_mark_stats_folder()

                self.main_config(cursor="")
                self.menu_enable()
                self.main_update()

            else:
                self.info_dialog_on_mark[self.sel_tree].show('No files found.',f'expression:"{expression}"  {use_reg_expr_info}\n')

        tree.focus_set()

    @logwrapper
    def mark_subpath(self,action,all_groups=True):
        initialdir = self.last_dir if self.last_dir else self.cwd
        if path:=askdirectory(title='Select Directory',initialdir=initialdir,parent=self.main):
            self.last_dir = path
            self.action_on_path(path,action,all_groups)

    def goto_next_mark_menu(self,direction,go_to_no_mark=False):
        tree=self.sel_tree
        self.goto_next_mark(tree,direction,go_to_no_mark)

    @block
    def goto_next_mark(self,tree,direction,go_to_no_mark=False):
        if go_to_no_mark:
            status= 'selecting next not marked item' if direction==1 else 'selecting prev not marked item'
        else:
            status ='selecting next marked item' if direction==1 else 'selecting prev marked item'

        current_item = self.sel_item
        self_sel_item = self.sel_item

        next_dict = self.my_next_dict[tree] if direction==1 else self.my_prev_dict[tree]

        self_crc_to_size = self.crc_to_size
        self_tagged = self.tagged

        while current_item:
            current_item = next_dict[current_item]
            item_taggged = bool(current_item in self_tagged)

            if (item_taggged and not go_to_no_mark) or (go_to_no_mark and not item_taggged and current_item not in self_crc_to_size):
                self.semi_selection(tree,current_item)
                tree.see(current_item)

                if tree==self.groups_tree:
                    self.groups_tree_sel_change(current_item)
                else:
                    self.folder_tree_sel_change(current_item)

                self.status(status,do_log=False)

                break

            if current_item==self_sel_item:
                self.status('%s ... (no file)' % status,do_log=False)
                break

    dominant_groups_index={0:-1,1:-1}
    dominant_groups_folder={0:-1,1:-1}

    BY_WHAT={0:"by quantity",1:"by sum size"}

    @block
    def goto_max_group(self,size_flag=0,direction=1):
        if self.groups_combos_size:
            #self.status(f'Setting dominant group ...')
            working_index = self.dominant_groups_index[size_flag]
            working_index = (working_index+direction) % len(self.groups_combos_size)
            temp=str(working_index)
            working_dict = self.groups_combos_size if size_flag else self.groups_combos_quant

            biggest_crc,biggest_crc_size_sum = working_dict[working_index]

            if biggest_crc:
                self.crc_select_and_focus(biggest_crc,True)

                self.dominant_groups_index[size_flag] = int(temp)
                info = bytes_to_str(biggest_crc_size_sum) if size_flag else str(biggest_crc_size_sum)
                self.status(f'Dominant (index:{working_index}) group ({self.BY_WHAT[size_flag]}: {info})',image=self.ico['dominant_size' if size_flag else 'dominant_quant'])

    @block
    def goto_max_folder(self,size_flag=0,direction=1):
        if self.path_stat_list_size:
            #self.status(f'Setting dominant folder ...')
            working_index = self.dominant_groups_folder[size_flag]
            working_index = (working_index+direction) % len(self.path_stat_list_size)
            temp = str(working_index)
            working_dict = self.path_stat_list_size if size_flag else self.path_stat_list_quant

            pathnr,path,num = working_dict[working_index]

            item=self.biggest_file_of_path_id[(pathnr,path)]

            self.groups_tree_focus(item)
            self.groups_tree_sel_change(item,change_status_line=False)

            try:
                self.groups_tree_see(self.tree_children_sub[self.sel_crc][-1])
                self.groups_tree_see(self.sel_crc)
                self.groups_tree_see(item)
            except Exception :
                pass

            self.folder_tree.update()

            try:
                self.folder_tree.focus_set()
                self.folder_tree.focus(item)
                self.folder_tree_sel_change(item,change_status_line=False)
                self.folder_tree_see(item)
            except Exception :
                pass

            self.groups_tree_update(item)

            self.dominant_groups_folder[size_flag] = int(temp)
            info = bytes_to_str(num) if size_flag else str(num)
            self.status(f'Dominant (index:{working_index}) folder ({self.BY_WHAT[size_flag]}: {info})',image=self.ico['dominant_size' if size_flag else 'dominant_quant'])

    def item_full_path(self,item):
        kind,size,crc, (pathnr,path,file,ctime,dev,inode) = self.groups_tree_item_to_data[item]
        return abspath(dude_core.get_full_path_scanned(pathnr,path,file))

    #@logwrapper
    def file_check_state(self,item):
        fullpath = self.item_full_path(item)
        l_info('checking file: %s',fullpath)
        try:
            stat_res = stat(fullpath)
            ctime_check=int(stat_res.st_ctime_ns)
        except Exception as e:
            self.status(str(e))
            mesage = f'can\'t check file: {fullpath}\n\n{e}'
            l_error(mesage)
            return mesage

        if ctime_check != (ctime:=self.groups_tree_item_to_data[item][3][3] ) :
            message = f'ctime inconsistency {ctime_check} vs {ctime}'
            l_error(mesage)
            return message

        return None

    @block_and_log
    def process_files_in_groups_wrapper(self,action,all_groups):
        processed_items=defaultdict(dict)

        if all_groups:
            scope_title='All marked files.'
        else:
            scope_title='Single group.'

        self_sel_crc = self.sel_crc
        self_tagged = self.tagged

        self_tree_children_sub = self.tree_children_sub

        for crc in self.tree_children[self.groups_tree]:
            index=0
            if all_groups or crc==self_sel_crc:
                for item in self_tree_children_sub[crc]:
                    if item in self_tagged:
                        processed_items[crc][index]=item
                        index+=1

        self.process_files(action,processed_items,scope_title)

    @block_and_log
    def process_files_in_folder_wrapper(self,action,on_dir_action=False):
        processed_items=defaultdict(dict)

        self_item_full_path = self.item_full_path
        self_tree_children_sub = self.tree_children_sub

        if on_dir_action:
            scope_title='All marked files on selected directory sub-tree.'

            self_tagged = self.tagged

            sel_path_with_sep=self.sel_full_path_to_file.rstrip(sep) + sep
            for crc in self.tree_children[self.groups_tree]:
                index=0
                for item in self_tree_children_sub[crc]:
                    if self_item_full_path(item).startswith(sel_path_with_sep):
                        if item in self_tagged:
                            processed_items[crc][index]=item
                            index+=1
        else:
            scope_title='Selected Directory.'

            self_current_folder_items_tagged = self.current_folder_items_tagged
            self_groups_tree_item_to_data = self.groups_tree_item_to_data
            index = defaultdict(int)
            for item in self.current_folder_items:
                if item in self_current_folder_items_tagged:
                    kind,size,crc, (pathnr,path,file,ctime,dev,inode) = self_groups_tree_item_to_data[item]
                    processed_items[crc][index[crc]]=item
                    index[crc]+=1

        return self.process_files(action,processed_items,scope_title)

    CHECK_OK='ok_special_string'
    CHECK_ERR='error_special_string'

    @restore_status_line
    @block_and_log
    def process_files_check_correctness(self,action,processed_items,remaining_items):
        skip_incorrect = self.cfg_get_bool(CFG_SKIP_INCORRECT_GROUPS)
        show_full_crc=self.cfg_get_bool(CFG_KEY_FULL_CRC)

        self.status('checking data consistency with filesystem state ...')

        if self.operation_mode in (MODE_SIMILARITY,MODE_GPS):
            ###############################################################
            self.get_info_dialog_on_main().show('Warning !','Similarity mode !\nFiles in groups are not exact copies !')

            dude_core_check_group_files_state = dude_core.check_group_files_state

            for group in processed_items:
                size = 0

                try:
                    (checkres,tuples_to_remove)=dude_core_check_group_files_state(size,group,True)
                except Exception as e:
                    self.get_text_info_dialog().show('Error. dude_core_check_group_files_state error.',str(e) )
                    return self.CHECK_ERR

                if checkres:
                    self.get_text_info_dialog().show('Error. Inconsistent data.','Current filesystem state is inconsistent with scanned data.\n\n' + '\n'.join(checkres) + '\n\nSelected group will be reduced. For complete results re-scanning is recommended.')
                    self.store_text_dialog_fields(self.text_info_dialog)

                    orglist=self.tree_children[self.groups_tree]

                    dude_core.remove_from_data_pool(size,group,tuples_to_remove,self.file_remove_callback,self.crc_remove_callback)

                    self.data_precalc()

                    newlist=self.tree_children[self.groups_tree]
                    item_to_sel = self.get_closest_in_group(orglist,group,newlist)

                    self.reset_sels()

                    if item_to_sel:
                        #group node moze zniknac - trzeba zupdejtowac SelXxx
                        self.crc_select_and_focus(item_to_sel,True)
                    else:
                        self.initial_focus()

                    self.calc_mark_stats_groups()

                    return self.CHECK_ERR

            self.status('checking selection correctness...')

            incorrect_groups=[]
            incorrect_groups_append = incorrect_groups.append
            if action==HARDLINK:
                for group in processed_items:
                    if len(processed_items[group])==1:
                        incorrect_groups_append(group)
                problem_header = 'Single file marked'
                problem_message = "Mark more files\nor enable option:\n\"Skip groups with invalid selection\""
            else:
                for group in processed_items:
                    if len(remaining_items[group])==0:
                        incorrect_groups_append(group)

                problem_header = 'All files marked'
                if action in (SOFTLINK,WIN_LNK):
                    problem_message = "Keep at least one file unmarked\nor enable option:\n\"Skip groups with invalid selection\""
                else:
                    problem_message = "Keep at least one file unmarked\nor enable option:\n\"Skip groups with invalid selection\"\nor enable option:\n\"Allow deletion of all copies\""

            if incorrect_groups:
                if skip_incorrect:

                    incorrect_group_str='\n'.join([group if show_full_crc else group[:dude_core.crc_cut_len] for group in incorrect_groups ])
                    header = f'Warning ({NAME[action]}). {problem_header}'
                    message = f"Option \"Skip groups with invalid selection\" is enabled.\n\nFollowing groups will NOT be processed and remain with markings:\n\n{incorrect_group_str}"

                    self.get_text_info_dialog().show(header,message)
                    self.store_text_dialog_fields(self.text_info_dialog)

                    self.crc_select_and_focus(incorrect_groups[0],True)

                    for group in incorrect_groups:
                        del processed_items[group]
                        del remaining_items[group]

                else:
                    if action==DELETE and self.cfg_get_bool(CFG_ALLOW_DELETE_ALL):
                        self.get_text_ask_dialog().show('Warning !','Option: \'Allow to delete all copies\' is set.|RED\n\nAll copies may be selected.|RED\n\nProceed ?|RED')
                        self.store_text_dialog_fields(self.text_ask_dialog)
                        if self.text_ask_dialog.res_bool:
                            return self.CHECK_OK
                    else:
                        header = f'Error ({NAME[action]}). {problem_header}'
                        self.get_info_dialog_on_main().show(header,problem_message)

                    self.crc_select_and_focus(incorrect_groups[0],True)
                    return self.CHECK_ERR

            ###############################################################
        else:
            dude_core_check_group_files_state = dude_core.check_group_files_state

            for crc in processed_items:
                size = self.crc_to_size[crc]

                try:
                    (checkres,tuples_to_remove)=dude_core_check_group_files_state(size,crc)
                except Exception as e:
                    self.get_text_info_dialog().show('Error. dude_core_check_group_files_state error.',str(e) )
                    return self.CHECK_ERR

                if checkres:
                    self.get_text_info_dialog().show('Error. Inconsistent data.','Current filesystem state is inconsistent with scanned data.\n\n' + '\n'.join(checkres) + '\n\nSelected group will be reduced. For complete results re-scanning is recommended.')
                    self.store_text_dialog_fields(self.text_info_dialog)

                    orglist=self.tree_children[self.groups_tree]

                    dude_core.remove_from_data_pool(size,crc,tuples_to_remove,self.file_remove_callback,self.crc_remove_callback)

                    self.data_precalc()

                    newlist=self.tree_children[self.groups_tree]
                    item_to_sel = self.get_closest_in_crc(orglist,crc,newlist)

                    self.reset_sels()

                    if item_to_sel:
                        #crc node moze zniknac - trzeba zupdejtowac SelXxx
                        self.crc_select_and_focus(item_to_sel,True)
                    else:
                        self.initial_focus()

                    self.calc_mark_stats_groups()

                    return self.CHECK_ERR

            self.status('checking selection correctness...')

            incorrect_groups=[]
            incorrect_groups_append = incorrect_groups.append
            if action==HARDLINK:
                for crc in processed_items:
                    if len(processed_items[crc])==1:
                        incorrect_groups_append(crc)
                problem_header = 'Single file marked'
                problem_message = "Mark more files\nor enable option:\n\"Skip groups with invalid selection\""
            else:
                for crc in processed_items:
                    if len(remaining_items[crc])==0:
                        incorrect_groups_append(crc)

                problem_header = 'All files marked'
                if action in (SOFTLINK,WIN_LNK):
                    problem_message = "Keep at least one file unmarked\nor enable option:\n\"Skip groups with invalid selection\""
                else:
                    problem_message = "Keep at least one file unmarked\nor enable option:\n\"Skip groups with invalid selection\"\nor enable option:\n\"Allow deletion of all copies\""

            if incorrect_groups:
                if skip_incorrect:

                    incorrect_group_str='\n'.join([crc if show_full_crc else crc[:dude_core.crc_cut_len] for crc in incorrect_groups ])
                    header = f'Warning ({NAME[action]}). {problem_header}'
                    message = f"Option \"Skip groups with invalid selection\" is enabled.\n\nFollowing groups will NOT be processed and remain with markings:\n\n{incorrect_group_str}"

                    self.get_text_info_dialog().show(header,message)
                    self.store_text_dialog_fields(self.text_info_dialog)

                    self.crc_select_and_focus(incorrect_groups[0],True)

                    for crc in incorrect_groups:
                        del processed_items[crc]
                        del remaining_items[crc]

                else:
                    if action==DELETE and self.cfg_get_bool(CFG_ALLOW_DELETE_ALL):
                        self.get_text_ask_dialog().show('Warning !','Option: \'Allow to delete all copies\' is set.|RED\n\nAll copies may be selected.|RED\n\nProceed ?|RED')
                        self.store_text_dialog_fields(self.text_ask_dialog)
                        if self.text_ask_dialog.res_bool:
                            return self.CHECK_OK
                    else:
                        header = f'Error ({NAME[action]}). {problem_header}'
                        self.get_info_dialog_on_main().show(header,problem_message)

                    self.crc_select_and_focus(incorrect_groups[0],True)
                    return self.CHECK_ERR

        return self.CHECK_OK

    @restore_status_line
    @block_and_log
    def process_files_check_correctness_last(self,action,processed_items,remaining_items):
        self.status('final checking selection correctness')
        self.main_update()

        self_file_check_state = self.file_check_state
        self_groups_tree_item_to_data = self.groups_tree_item_to_data

        if self.operation_mode in(MODE_SIMILARITY,MODE_GPS):
            if action==HARDLINK:
                for group,items_dict in processed_items.items():
                    #kind,size,group, (pathnr,path,file,ctime,dev,inode)
                    if len({self_groups_tree_item_to_data[item][3][4] for item in items_dict.values()})>1: #dev
                        title='Can\'t create hardlinks.'
                        message=f"Files on multiple devices selected. Group:{group}"
                        l_error(title)
                        l_error(message)
                        self.get_info_dialog_on_main().show(title,message)
                        return self.CHECK_ERR

            for crc in processed_items:
                for item in remaining_items[crc].values():
                    if res:=self_file_check_state(item):
                        self.get_info_dialog_on_main().show('Error',res+'\n\nNo action was taken.\n\nAborting. Please repeat scanning or unmark all files and groups affected by other programs.')
                        l_error('aborting.')
                        return self.CHECK_ERR
        else:
            if action==HARDLINK:
                for crc,items_dict in processed_items.items():
                    #kind,size,crc, (pathnr,path,file,ctime,dev,inode)
                    if len({self_groups_tree_item_to_data[item][3][4] for item in items_dict.values()})>1: #dev
                        title='Can\'t create hardlinks.'
                        message=f"Files on multiple devices selected. Crc:{crc}"
                        l_error(title)
                        l_error(message)
                        self.get_info_dialog_on_main().show(title,message)
                        return self.CHECK_ERR

            for crc in processed_items:
                for item in remaining_items[crc].values():
                    if res:=self_file_check_state(item):
                        self.get_info_dialog_on_main().show('Error',res+'\n\nNo action was taken.\n\nAborting. Please repeat scanning or unmark all files and groups affected by other programs.')
                        l_error('aborting.')
                        return self.CHECK_ERR

        l_info('remaining files checking complete.')
        return self.CHECK_OK

    @restore_status_line
    @logwrapper
    def process_files_confirm(self,action,processed_items,remaining_items,scope_title):
        self.status('confirmation required...')
        show_full_path=1

        cfg_show_crc_size = self.cfg_get_bool(CFG_CONFIRM_SHOW_CRCSIZE)
        cfg_show_links_targets = self.cfg_get_bool(CFG_CONFIRM_SHOW_LINKSTARGETS)

        message=[]
        message_append = message.append

        action_is_win_lnk = bool(action==WIN_LNK)
        action_is_softlink = bool(action==SOFTLINK)
        softlink_or_win_lnk = bool (action_is_softlink or action_is_win_lnk)

        space_prefix = '  ' if softlink_or_win_lnk and cfg_show_links_targets else ''

        if action_is_win_lnk:
            message_append('Link files will be created with the names of the listed files with the ".lnk" suffix.')
            message_append('Original files will be removed.')
            message_append('')

        self_item_full_path = self.item_full_path

        self_groups_tree_item_to_data = self.groups_tree_item_to_data
        size_sum=0

        if self.operation_mode in (MODE_SIMILARITY,MODE_GPS):
            for group,items_dict in processed_items.items():
                crc = group
                message_append('')

                if cfg_show_crc_size:
                    message_append('GROUP:' + group + '|GRAY')

                for index,item in items_dict.items():
                    kind,size_item,crc_item, (pathnr,path,file,ctime,dev,inode) = self_groups_tree_item_to_data[item]
                    size_sum += size_item

                    if action_is_win_lnk:
                        message_append(space_prefix + (self_item_full_path(item) if show_full_path else file) + '(.lnk)|RED' )
                    else:
                        message_append(space_prefix + (self_item_full_path(item) if show_full_path else file) + '|RED' )

                if softlink_or_win_lnk:
                    if remaining_items[crc]:
                        item = remaining_items[crc][0]
                        if cfg_show_links_targets:
                            message_append('> %s' % (self_item_full_path(item) if show_full_path else self_groups_tree_item_to_data[item][3][2]) ) #file

            size_info = "Processed files size sum : " + bytes_to_str(size_sum) + "\n"

            trash_info =     "\n\nSend to Trash            : " + ("Yes" if self.cfg_get_bool(CFG_SEND_TO_TRASH) else "No") + "|RED"

            head_info = scope_title + trash_info
            if action==DELETE:
                erase_empty_dirs = "\nErase empty directories  : " + ('Yes|RED' if self.cfg_get_bool(CFG_ERASE_EMPTY_DIRS) else 'No')
                self.get_text_ask_dialog().show('Delete marked files ?','Scope: ' + head_info + erase_empty_dirs + '\n\n' + size_info + '\n' + '\n'.join(message))
                self.store_text_dialog_fields(self.text_ask_dialog)
                if not self.text_ask_dialog.res_bool:
                    return True
            elif action_is_softlink:
                self.get_text_ask_dialog().show('Soft-Link marked files to the first unmarked file in the group ?','Scope: ' + head_info + '\n\n' + size_info + '\n'+'\n'.join(message))
                self.store_text_dialog_fields(self.text_ask_dialog)
                if not self.text_ask_dialog.res_bool:
                    return True
            elif action_is_win_lnk:
                self.get_text_ask_dialog().show('replace marked files with .lnk files pointing to the first unmarked file in the group ?','Scope: ' + head_info + '\n\n' + size_info + '\n'+'\n'.join(message))
                self.store_text_dialog_fields(self.text_ask_dialog)
                if not self.text_ask_dialog.res_bool:
                    return True
            elif action==HARDLINK:
                self.get_text_ask_dialog().show('Hard-Link marked files together in groups ?','Scope: ' + head_info + '\n\n' + size_info +'\n'+'\n'.join(message))
                self.store_text_dialog_fields(self.text_ask_dialog)
                if not self.text_ask_dialog.res_bool:
                    return True

            _ = {l_warning(line) for line in message}
            l_warning('###########################################################################################')
            l_warning('Confirmed.')

        else:
            for crc,items_dict in processed_items.items():
                message_append('')

                size=self.crc_to_size[crc]

                if cfg_show_crc_size:
                    message_append('CRC:' + crc + ' size:' + bytes_to_str(size) + '|GRAY')

                for index,item in items_dict.items():
                    size_sum += size
                    kind,size_item,crc_item, (pathnr,path,file,ctime,dev,inode) = self_groups_tree_item_to_data[item]

                    if action_is_win_lnk:
                        message_append(space_prefix + (self_item_full_path(item) if show_full_path else file) + '(.lnk)|RED' )
                    else:
                        message_append(space_prefix + (self_item_full_path(item) if show_full_path else file) + '|RED' )

                if softlink_or_win_lnk:
                    if remaining_items[crc]:
                        item = remaining_items[crc][0]
                        if cfg_show_links_targets:
                            message_append('> %s' % (self_item_full_path(item) if show_full_path else self_groups_tree_item_to_data[item][3][2]) ) #file

            size_info = "Processed files size sum : " + bytes_to_str(size_sum) + "\n"

            trash_info =     "\n\nSend to Trash            : " + ("Yes" if self.cfg_get_bool(CFG_SEND_TO_TRASH) else "No") + "|RED"

            head_info = scope_title + trash_info
            if action==DELETE:
                erase_empty_dirs = "\nErase empty directories  : " + ('Yes|RED' if self.cfg_get_bool(CFG_ERASE_EMPTY_DIRS) else 'No')
                self.get_text_ask_dialog().show('Delete marked files ?','Scope: ' + head_info + erase_empty_dirs + '\n\n' + size_info + '\n' + '\n'.join(message))
                self.store_text_dialog_fields(self.text_ask_dialog)
                if not self.text_ask_dialog.res_bool:
                    return True
            elif action_is_softlink:
                self.get_text_ask_dialog().show('Soft-Link marked files to the first unmarked file in the group ?','Scope: ' + head_info + '\n\n' + size_info + '\n'+'\n'.join(message))
                self.store_text_dialog_fields(self.text_ask_dialog)
                if not self.text_ask_dialog.res_bool:
                    return True
            elif action_is_win_lnk:
                self.get_text_ask_dialog().show('replace marked files with .lnk files pointing to the first unmarked file in the group ?','Scope: ' + head_info + '\n\n' + size_info + '\n'+'\n'.join(message))
                self.store_text_dialog_fields(self.text_ask_dialog)
                if not self.text_ask_dialog.res_bool:
                    return True
            elif action==HARDLINK:
                self.get_text_ask_dialog().show('Hard-Link marked files together in groups ?','Scope: ' + head_info + '\n\n' + size_info +'\n'+'\n'.join(message))
                self.store_text_dialog_fields(self.text_ask_dialog)
                if not self.text_ask_dialog.res_bool:
                    return True

            _ = {l_warning(line) for line in message}
            l_warning('###########################################################################################')
            l_warning('Confirmed.')

        return False

    @block
    def empty_dirs_removal(self,path,report_empty=False):
        removal_func = send2trash if self.cfg_get_bool(CFG_SEND_TO_TRASH) else rmdir

        clean,removed = self.empty_dirs_removal_core(path,removal_func)

        if report_empty and not removed:
            removed.append(f'No empty subdirectories in:\'{path}\'')

        return removed

    def empty_dirs_removal_core(self,path,removal_func):
        result = []
        result_extend = result.extend
        result_append = result.append
        try:
            with scandir(path) as res:
                clean = True
                self_empty_dirs_removal_core = self.empty_dirs_removal_core
                for entry in res:
                    if entry.is_symlink():
                        clean = False
                    elif entry.is_dir():
                        sub_clean,sub_result = self_empty_dirs_removal_core(abspath(path_join(path, entry.name)),removal_func)
                        clean = clean and sub_clean
                        result_extend(sub_result)
                    else:
                        clean = False
            if clean:
                try:
                    l_info('empty_dirs_removal_core %s(%s)',removal_func.__name__,path)
                    removal_func(path)
                    result_append(path)
                except Exception as removal_e:
                    l_error('empty_dirs_removal_core:%s',removal_e)
                    clean = False

            return (clean,result)

        except Exception as e:
            l_error('empty_dirs_removal:%s',e)
            return (False,result)

    def empty_dirs_removal_single(self,path,removal_func):
        try:
            with scandir(path) as res:
                for entry in res:
                    return ''

                try:
                    l_info('empty_dirs_removal_single %s(%s)',removal_func.__name__,path)
                    removal_func(path)
                    return str(path)
                except Exception as removal_e:
                    l_error('empty_dirs_removal_single:%s',removal_e)
                    return f'error (remove {path}): {removal_e}'
        except Exception as e:
            l_error('empty_dirs_removal_single scandir :%s',e)
            return f' error (scandir {path}): {e}'

    def process_files_core(self,action,processed_items,remaining_items):
        to_trash=self.cfg_get_bool(CFG_SEND_TO_TRASH)
        abort_on_error=self.cfg_get_bool(CFG_ABORT_ON_ERROR)
        erase_empty_dirs=self.cfg_get_bool(CFG_ERASE_EMPTY_DIRS)

        self_groups_tree_item_to_data = self.groups_tree_item_to_data
        dude_core_delete_file_wrapper = dude_core.delete_file_wrapper

        dude_core_link_wrapper = dude_core.link_wrapper

        final_info=[]

        self.process_files_counter = 0
        self.process_files_size_sum = 0

        end_message_list=[]
        end_message_list_append = end_message_list.append

        self.process_files_core_info0=''
        self.process_files_core_info1=''
        self.process_files_core_info2='processing files...'

        self.process_files_core_perc_1=0
        self.process_files_core_perc_2=0

        self.process_files_result=('','')

        directories_to_check=set()
        directories_to_check_add = directories_to_check.add

        self_file_remove_callback = self.file_remove_callback
        self_crc_remove_callback = self.crc_remove_callback

        if action==DELETE:
            if self.operation_mode in (MODE_SIMILARITY,MODE_GPS):
                for group,items_dict in processed_items.items():
                    tuples_to_delete=set()
                    tuples_to_delete_add = tuples_to_delete.add

                    #self.process_files_core_info0 = f'size:{bytes_to_str(size)}'
                    self.process_files_core_info1 = f'group:{group}'

                    for item in items_dict.values():
                        kind,size,group, index_tuple = self_groups_tree_item_to_data[item]
                        (pathnr,path,file_name,ctime,dev,inode)=index_tuple

                        index_tuple_extended = pathnr,path,file_name,ctime,dev,inode,size

                        #tuples_to_delete_add(index_tuple)
                        tuples_to_delete_add(index_tuple_extended)

                        self.process_files_core_info2 = f'{path}{sep}{file_name}'

                        self.process_files_core_perc_1 = self.process_files_size_sum*100/self.process_files_total_size
                        self.process_files_core_perc_2 = self.process_files_counter*100/self.process_files_total

                        self.process_files_counter+=1
                        self.process_files_size_sum+=size

                        if erase_empty_dirs:
                            if path:
                                directories_to_check_add( tuple( [pathnr] + path.strip(sep).split(sep) ) )

                    if resmsg:=dude_core_delete_file_wrapper(size,group,tuples_to_delete,to_trash,self_file_remove_callback,self_crc_remove_callback,True):
                        resmsg_str='\n'.join(resmsg)
                        l_error(resmsg_str)
                        end_message_list_append(resmsg_str)

                        if abort_on_error:
                            break
            else:
                for crc,items_dict in processed_items.items():
                    tuples_to_delete=set()
                    tuples_to_delete_add = tuples_to_delete.add
                    size = self.crc_to_size[crc]

                    self.process_files_core_info0 = f'size:{bytes_to_str(size)}'
                    self.process_files_core_info1 = f'crc:{crc}'

                    for item in items_dict.values():
                        index_tuple=self_groups_tree_item_to_data[item][3]
                        tuples_to_delete_add(index_tuple)
                        (pathnr,path,file_name,ctime,dev,inode)=index_tuple

                        self.process_files_core_info2 = f'{path}{sep}{file_name}'

                        self.process_files_core_perc_1 = self.process_files_size_sum*100/self.process_files_total_size
                        self.process_files_core_perc_2 = self.process_files_counter*100/self.process_files_total

                        self.process_files_counter+=1
                        self.process_files_size_sum+=size

                        if erase_empty_dirs:
                            if path:
                                directories_to_check_add( tuple( [pathnr] + path.strip(sep).split(sep) ) )

                    if resmsg:=dude_core_delete_file_wrapper(size,crc,tuples_to_delete,to_trash,self_file_remove_callback,self_crc_remove_callback):
                        resmsg_str='\n'.join(resmsg)
                        l_error(resmsg_str)
                        end_message_list_append(resmsg_str)

                        if abort_on_error:
                            break


            if erase_empty_dirs:

                directories_to_check_expanded=set()
                directories_to_check_expanded_add = directories_to_check_expanded.add

                for dir_tuple in directories_to_check:
                    elems = len(dir_tuple)-1
                    for i in range(elems):
                        combo_to_check = tuple(dir_tuple[0:2+i])
                        directories_to_check_expanded_add( combo_to_check )

                removed=[]
                removed_append=removed.append
                removal_func = send2trash if self.cfg_get_bool(CFG_SEND_TO_TRASH) else rmdir

                for dir_tuple in sorted(directories_to_check_expanded,key=lambda p : len(p),reverse=True):
                    real_path = normpath(abspath(dude_core.scanned_paths[dir_tuple[0]] + sep + sep.join(dir_tuple[1:])))

                    info = self.empty_dirs_removal_single(real_path,removal_func)
                    if info:
                        removed_append(info)

                if removed:
                    final_info.extend(removed)

        elif action==SOFTLINK:
            do_rel_symlink = self.cfg_get_bool(CFG_KEY_REL_SYMLINKS)
            for crc,items_dict in processed_items.items():
                self.process_files_core_perc_1 = self.process_files_size_sum*100/self.process_files_total_size
                self.process_files_core_perc_2 = self.process_files_counter*100/self.process_files_total

                self.process_files_counter+=1

                to_keep_item=remaining_items[crc][0]

                index_tuple_ref=self_groups_tree_item_to_data[to_keep_item][3]
                size=self_groups_tree_item_to_data[to_keep_item][1]
                self.process_files_size_sum+=size

                self.process_files_core_info0 = f'size:{bytes_to_str(size)}'

                self.process_files_core_info1 = f'crc:{crc}'

                if resmsg:=dude_core_link_wrapper(SOFTLINK, do_rel_symlink, size,crc, index_tuple_ref, [self_groups_tree_item_to_data[item][3] for item in items_dict.values() ],to_trash,self_file_remove_callback,self_crc_remove_callback ):
                    l_error(resmsg)

                    end_message_list_append(resmsg)

                    if abort_on_error:
                        break

        elif action==WIN_LNK:
            for crc,items_dict in processed_items.items():
                self.process_files_core_perc_1 = self.process_files_size_sum*100/self.process_files_total_size
                self.process_files_core_perc_2 = self.process_files_counter*100/self.process_files_total

                self.process_files_counter+=1

                to_keep_item=remaining_items[crc][0]

                index_tuple_ref=self_groups_tree_item_to_data[to_keep_item][3]
                size=self_groups_tree_item_to_data[to_keep_item][1]
                self.process_files_size_sum+=size

                self.process_files_core_info0 = f'size:{bytes_to_str(size)}'
                self.process_files_core_info1 = f'crc:{crc}'

                if resmsg:=dude_core_link_wrapper(WIN_LNK, False, size,crc, index_tuple_ref, [self_groups_tree_item_to_data[item][3] for item in items_dict.values() ],to_trash,self_file_remove_callback,self_crc_remove_callback ):
                    l_error(resmsg)

                    end_message_list_append(resmsg)

                    if abort_on_error:
                        break

        elif action==HARDLINK:
            for crc,items_dict in processed_items.items():
                self.process_files_core_perc_1 = self.process_files_size_sum*100/self.process_files_total_size
                self.process_files_core_perc_2 = self.process_files_counter*100/self.process_files_total

                self.process_files_counter+=1

                ref_item=items_dict[0]
                index_tuple_ref=self_groups_tree_item_to_data[ref_item][3]
                size=self_groups_tree_item_to_data[ref_item][1]
                self.process_files_size_sum+=size

                self.process_files_core_info0 = f'size:{bytes_to_str(size)}'
                self.process_files_core_info1 = f'crc:{crc}'

                if resmsg:=dude_core_link_wrapper(HARDLINK, False, size,crc, index_tuple_ref, [self_groups_tree_item_to_data[item][3] for index,item in items_dict.items() if index!=0 ],to_trash,self_file_remove_callback,self_crc_remove_callback ):
                    l_error(resmsg)

                    end_message_list_append(resmsg)

                    if abort_on_error:
                        break

        self.process_files_result=(end_message_list,final_info)

    @logwrapper
    def get_this_or_existing_parent(self,path):
        if path:
            if path_exists(path):
                return path

            return self.get_this_or_existing_parent(Path(path).parent.absolute())

        return None

    @block_and_log
    def process_files(self,action,processed_items,scope_title):
        tree=self.sel_tree

        if not processed_items:
            self.get_info_dialog_on_main().show('No Files Marked For Processing !','Scope: ' + scope_title + '\n\nMark files first.')
            return

        l_info('process_files: %s',action)
        l_info('Scope: %s',scope_title)

        #############################################
        #check remainings

        #remaining_items dla wszystkich (moze byc akcja z folderu)
        #istotna kolejnosc

        self.status('checking remaining items...')
        remaining_items={}

        self_tagged = self.tagged
        self_tree_children_sub = self.tree_children_sub

        for crc in processed_items:
            remaining_items[crc]=dict(enumerate([item for item in self_tree_children_sub[crc] if item not in self_tagged]))
            #{index:item for index,item in enumerate( [item for item in self_tree_children_sub[crc] if item not in self_tagged] ) }

        check=self.process_files_check_correctness(action,processed_items,remaining_items)

        if check == self.CHECK_ERR:
            self.status('action aborted')
            return

        if check!=self.CHECK_OK:
            self.get_info_dialog_on_main().show('INTERNAL ERROR 1 - aborting','got %s from process_files_check_correctness' % check)
            return

        if not processed_items:
            self.get_info_dialog_on_main().show('info','No files left for processing.\nFix files selection.')
            return

        l_warning('###########################################################################################')
        l_warning('action:%s',action)

        self.status('')
        if self.process_files_confirm(action,processed_items,remaining_items,scope_title):
            return

        #after confirmation
        check=self.process_files_check_correctness_last(action,processed_items,remaining_items)
        if check == self.CHECK_ERR:
            self.status('action aborted')
            return

        if check!=self.CHECK_OK:
            self.get_info_dialog_on_main().show('INTERNAL ERROR 2 - aborting','got %s process_files_check_correctness_last' % check)
            return

        #############################################
        #action
        l_info('tree: %s',tree)

        item_to_select=None

        processed_items_list = [item for crc,index_dict in processed_items.items() for index,item in index_dict.items()]

        if tree==self.groups_tree:
            item_to_select = self.sel_crc

            self_my_next_dict_tree = self.my_next_dict[tree]
            while True:
                try:
                    item_to_select = self_my_next_dict_tree[item_to_select]
                except :
                    item_to_select = None

                if not item_to_select:
                    break

                if item_to_select not in processed_items_list:
                    break
        else:
            orglist=self.current_folder_items
            org_sel_item=self.sel_item
            try:
                org_sel_file = self.current_folder_items_dict[org_sel_item][0]

            except :
                org_sel_file=None

        self.process_files_total = len([item for crc,items_dict in processed_items.items() for item in items_dict.values()])

        if self.operation_mode in (MODE_SIMILARITY,MODE_GPS):
            self_groups_tree_item_to_data = self.groups_tree_item_to_data
            #kind,size_item,crc_item, (pathnr,path,file,ctime,dev,inode) = self_groups_tree_item_to_data[item] for index,item in items_dict.items()
            self.process_files_total_size = sum([self_groups_tree_item_to_data[item][1] for group,items_dict in processed_items.items() for item in items_dict.values()])
        else:

            self.process_files_total_size = sum([self.crc_to_size[crc] for crc,items_dict in processed_items.items() for item in items_dict.values()])

        self.process_files_total_size_str = bytes_to_str(self.process_files_total_size)

        dialog = self.get_progress_dialog_on_main()

        self.process_files_core_info='initial'

        dialog.lab_l1.configure(text='Total space:')
        dialog.lab_l2.configure(text='Files number:' )

        dialog.progr1var.set(0)
        dialog.progr2var.set(0)

        dialog_progr1var_set = dialog.progr1var.set
        dialog_progr2var_set = dialog.progr2var.set

        run_processing_thread=Thread(target=lambda : self.process_files_core(action,processed_items,remaining_items) ,daemon=True)
        run_processing_thread_is_alive = run_processing_thread.is_alive
        run_processing_thread.start()

        wait_var=BooleanVar()
        wait_var_set = wait_var.set
        wait_var_set(False)
        wait_var_get = wait_var.get

        dialog.show('Processing',now=False)

        dialog_lab = dialog.lab

        dialog_lab_r1_configure = dialog.lab_r1.configure
        dialog_lab_r2_configure = dialog.lab_r2.configure

        self_main_after = self.main.after
        self_main_wait_variable = self.main.wait_variable

        dialog_update_lab_text = dialog.update_lab_text

        dialog_area_main_update = dialog.area_main.update

        #############################################
        while run_processing_thread_is_alive():

            dialog_update_lab_text(0,self.process_files_core_info0)
            dialog_update_lab_text(1,self.process_files_core_info1)
            dialog_update_lab_text(2, f'...{self.process_files_core_info2[-50:0]}')

            dialog_progr1var_set(self.process_files_core_perc_1)
            dialog_progr2var_set(self.process_files_core_perc_2)

            dialog_lab_r1_configure(text = f'{bytes_to_str(self.process_files_size_sum)} / {self.process_files_total_size_str}')
            dialog_lab_r2_configure(text = f'{self.process_files_counter} / {self.process_files_total}')

            self_main_after(100,lambda : wait_var_set(not wait_var_get()))
            self_main_wait_variable(wait_var)

            dialog_area_main_update()

        #############################################

        end_message_list,final_info = self.process_files_result

        run_processing_thread.join()

        dialog.hide(True)

        if end_message_list:
            self.get_text_info_dialog().show('Error','\n'.join(end_message_list))
            self.store_text_dialog_fields(self.text_info_dialog)

        if final_info:
            self.get_text_info_dialog().show('Removed empty directories','\n'.join(final_info))
            self.store_text_dialog_fields(self.text_info_dialog)

        self.data_precalc()

        l_info('post-update %s',tree)

        self.selected[self.groups_tree]=None
        self.selected[self.folder_tree]=None

        tree.selection_remove(*tree.selection())

        if tree==self.groups_tree:
            if self.sel_crc:
                if tree.exists(self.sel_crc):
                    item_to_select=self.sel_crc

            if item_to_select:
                l_info('updating groups : %s',item_to_select)
                try:

                    self.selected[self.groups_tree] = item_to_select
                    self.groups_tree.focus(item_to_select)
                    self.groups_tree.focus_set()

                    self.groups_tree_sel_change(item_to_select)
                    self.groups_tree_see(item_to_select)
                except :
                    self.initial_focus()
            else:
                self.initial_focus()
        else:
            if parent := self.get_this_or_existing_parent(self.sel_path_full):
                l_info('updating folder %s:',parent)

                if self.tree_folder_update(parent):
                    newlist=self.current_folder_items

                    try:
                        item_to_sel = self.get_closest_in_folder(orglist,org_sel_item,org_sel_file,newlist)
                    except :
                        item_to_sel = None

                    if item_to_sel:
                        try:
                            self.folder_tree.focus_set()
                            self.folder_tree.focus(item_to_sel)
                            self.folder_tree_sel_change(item_to_sel)
                            self.folder_tree_see(item_to_sel)
                            self.folder_tree.update()

                        except :
                            self.initial_focus()
            else:
                self.initial_focus()

        self.calc_mark_stats_groups()

        self.find_result=()

    @logwrapper
    def get_closest_in_folder(self,prev_list,item,item_name,new_list):
        if item in new_list:
            return item

        if not new_list:
            return None

        self_current_folder_items_dict = self.current_folder_items_dict

        new_list_names=[self_current_folder_items_dict[item][0] for item in self.current_folder_items] if self.current_folder_items else []

        if item_name in new_list_names:
            return new_list[new_list_names.index(item_name)]

        if item in prev_list:
            org_index=prev_list.index(item)

            new_list_len=len(new_list)
            for i in range(new_list_len):
                if (index_m_i:=org_index-i) >=0:
                    nearest = prev_list[index_m_i]
                    if nearest in new_list:
                        return nearest
                elif (index_p_i:=org_index+i) < new_list_len:
                    nearest = prev_list[index_p_i]
                    if nearest in new_list:
                        return nearest
                else:
                    return None

        return None

    @logwrapper
    def get_closest_in_crc(self,prev_list,item,new_list):
        if item in new_list:
            return item

        if not new_list:
            return None

        if item in prev_list:
            sel_index=prev_list.index(item)

            new_list_len=len(new_list)
            for i in range(new_list_len):
                if (index_m_i:=sel_index-i) >=0:
                    nearest = prev_list[index_m_i]
                    if nearest in new_list:
                        return nearest
                elif (index_p_i:=sel_index+i) < new_list_len:
                    nearest = prev_list[index_p_i]
                    if nearest in new_list:
                        return nearest
                else:
                    return None

        return None

    @logwrapper
    def csv_save(self):
        if csv_file := asksaveasfilename(parent=self.main,initialfile = 'DUDE_scan.csv',defaultextension=".csv",filetypes=[("All Files","*.*"),("CSV Files","*.csv")]):

            self.status('saving CSV file "%s" ...' % str(csv_file))
            dude_core.write_csv(str(csv_file))
            self.status('CSV file saved: "%s"' % str(csv_file))

    @logwrapper
    def cache_clean(self):
        from shutil import rmtree
        try:
            rmtree(CACHE_DIR)
        except Exception as e:
            l_error(e)

    @logwrapper
    def clip_copy_full_path_with_file(self):
        if self.sel_path_full and self.sel_file:
            self.clip_copy(path_join(self.sel_path_full,self.sel_file))
        elif self.sel_crc:
            self.clip_copy(self.sel_crc)

    @logwrapper
    def clip_copy_full(self):
        if self.sel_path_full:
            self.clip_copy(self.sel_path_full)
        elif self.sel_crc:
            self.clip_copy(self.sel_crc)

    @logwrapper
    def clip_copy_file(self):
        if self.sel_file:
            self.clip_copy(self.sel_file)
        elif self.sel_crc:
            self.clip_copy(self.sel_crc)

    @logwrapper
    def clip_copy(self,what):
        self.main.clipboard_clear()
        self.main.clipboard_append(what)
        self.status('Copied to clipboard: "%s"' % what)

    @block
    def enter_dir(self,fullpath,sel):
        self.main.update() #konieczne !, nie wchodzi akcja z menu,

        if self.find_tree==self.folder_tree:
            self.find_result=()

        if self.tree_folder_update(fullpath):
            children=self.current_folder_items

            res_list=[nodeid for nodeid in children if self.current_folder_items_dict[nodeid][0]==sel]

            if res_list:
                item=res_list[0]
                self.semi_selection(self.folder_tree,item)
                self.folder_tree_sel_change(item)
                self.folder_tree_see(item)

            elif children:
                item=children[0]
                self.folder_tree.focus(item)
                self.semi_selection(self.folder_tree,item)
                self.sel_file = self.groups_tree_item_to_data[item][3][2]
                self.folder_tree_sel_change(item)

    def double_left_button(self,event):
        if not self.block_processing_stack:
            tree=event.widget
            if tree.identify("region", event.x, event.y) != 'heading':
                if item:=tree.identify('item',event.x,event.y):
                    self.main.after_idle(lambda : self.tree_action(tree,item))

        return "break"

    @logwrapper
    def tree_action(self,tree,item,alt_pressed=False):
        if alt_pressed:
            self.open_folder()
        elif self.sel_kind == self.UPDIR:
            head,tail=path_split(self.sel_path_full)
            self.enter_dir(normpath(str(Path(self.sel_path_full).parent.absolute())),tail)
        elif self.sel_kind in (self.DIR,self.DIRLINK):
            self.enter_dir(self.sel_path_full+self.sel_file if self.sel_path_full=='/' else sep.join([self.sel_path_full,self.sel_file]),'..' )
        elif self.sel_kind!=self.CRC:
            self.open_file()

    @logwrapper
    def open_folder(self):
        from subprocess import Popen

        tree=self.sel_tree

        params=[]
        if tree.set(self.sel_item,'kind')==self.CRC:
            self.status('Opening folders(s)')
            for item in self.tree_children_sub[self.sel_item]:
                pathnr=int(tree.set(item,'pathnr'))
                item_path=tree.set(item,'path')
                params.append(dude_core.scanned_paths[int(pathnr)]+item_path)
        elif self.sel_path_full:
            self.status(f'Opening: {self.sel_path_full}')
            params.append(self.sel_path_full)
        else:
            return

        if wrapper:=self.cfg_get(CFG_KEY_WRAPPER_FOLDERS):

            params_num = self.cfg_get(CFG_KEY_WRAPPER_FOLDERS_PARAMS)

            num = 1024 if params_num=='all' else int(params_num)
            run_command = lambda : Popen([wrapper,*params[:num]])
        elif windows:
            run_command = lambda : startfile(params[0])
        else:
            run_command = lambda : Popen(["xdg-open",params[0]])

        Thread(target=run_command,daemon=True).start()

    @logwrapper
    def open_file(self):
        from subprocess import Popen

        if self.sel_path_full and self.sel_file:
            file_to_open = sep.join([self.sel_path_full,self.sel_file])

            if wrapper:=self.cfg_get(CFG_KEY_WRAPPER_FILE) and self.sel_kind in (self.FILE,self.LINK,self.SINGLE,self.SINGLEHARDLINKED):
                self.status('opening: %s' % file_to_open)
                run_command = lambda : Popen([wrapper,file_to_open])
            elif windows:
                self.status('opening: %s' % file_to_open)
                run_command = lambda : startfile(file_to_open)
            else:
                self.status('executing: xdg-open "%s"' % file_to_open)
                run_command = lambda : Popen(["xdg-open",file_to_open])

            Thread(target=run_command,daemon=True).start()

    @logwrapper
    def show_log(self):
        try:
            if windows:
                self.status('opening: %s' % log)
                startfile(log)
            else:
                self.status('executing: xdg-open "%s"' % log)
                system("xdg-open "+ '"' + log + '"')
        except Exception as e:
            l_error(e)
            self.status(str(e))

    @logwrapper
    def show_logs_dir(self):
        try:
            if windows:
                self.status('opening: %s' % LOG_DIR)
                startfile(LOG_DIR)
            else:
                self.status('executing: xdg-open "%s"' % LOG_DIR)
                system("xdg-open " + '"' + LOG_DIR + '"')
        except Exception as e:
            l_error(e)
            self.status(str(e))

    @logwrapper
    def show_homepage(self):
        try:
            if windows:
                self.status('opening: %s' % HOMEPAGE)
                startfile(HOMEPAGE)
            else:
                self.status('executing: xdg-open %s' % HOMEPAGE)
                system("xdg-open " + HOMEPAGE)
        except Exception as e:
            l_error(e)
            self.status(str(e))

if __name__ == "__main__":
    try:
        allocs, g1, g2 = gc_get_threshold()
        gc_set_threshold(100_000, g1*5, g2*10)

        DUDE_FILE = normpath(__file__)
        DUDE_DIR = dirname(DUDE_FILE)

        DUDE_EXECUTABLE_FILE = normpath(abspath(sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]))
        DUDE_EXECUTABLE_DIR = dirname(DUDE_EXECUTABLE_FILE)
        PORTABLE_DIR = sep.join([DUDE_EXECUTABLE_DIR,'dude.data'])

        #######################################################################

        VER_TIMESTAMP = console.get_ver_timestamp()

        p_args = console.parse_args(VER_TIMESTAMP)

        use_appdir=bool(p_args.appdirs)

        if not use_appdir:
            try:
                PORTABLE_DIR_TEST = sep.join([PORTABLE_DIR,'access.test'])
                Path(PORTABLE_DIR_TEST).mkdir(parents=True,exist_ok=False)
                rmdir(PORTABLE_DIR_TEST)
            except Exception as e_portable:
                print('Cannot store files in portable mode:',e_portable)
                use_appdir=True

        if use_appdir:
            try:
                from appdirs import user_cache_dir,user_log_dir,user_config_dir
                CACHE_DIR_DIR = user_cache_dir('dude','PJDude-%s' % VER_TIMESTAMP)
                LOG_DIR = user_log_dir('dude','PJDude')
                CONFIG_DIR = user_config_dir('dude')
            except Exception as e_import:
                print(e_import)

        else:
            CACHE_DIR_DIR = sep.join([PORTABLE_DIR,"cache-%s" % VER_TIMESTAMP])
            LOG_DIR = sep.join([PORTABLE_DIR,"logs"])
            CONFIG_DIR = PORTABLE_DIR

        #dont mix device id for different hosts in portable mode
        CACHE_DIR = sep.join([CACHE_DIR_DIR,node()])

        log_file = strftime('%Y_%m_%d_%H_%M_%S',localtime_catched(time()) ) +'.txt'
        log=abspath(p_args.log[0]) if p_args.log else LOG_DIR + sep + log_file
        #LOG_LEVEL = logging.DEBUG if p_args.debug else logging.INFO

        Path(LOG_DIR).mkdir(parents=True,exist_ok=True)

        #print('DUDE_EXECUTABLE_FILE:',DUDE_EXECUTABLE_FILE,'\nDUDE_EXECUTABLE_DIR:',DUDE_EXECUTABLE_DIR,'\nPORTABLE_DIR:',PORTABLE_DIR)
        print('log:',log)

        logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s', filename=log,filemode='w')

        l_info('DUDE %s',VER_TIMESTAMP)
        l_info('executable: %s',DUDE_EXECUTABLE_FILE)
        #l_debug('DEBUG LEVEL ENABLED')

        try:
            distro_info=Path(path_join(DUDE_DIR,'distro.info.txt')).read_text()
        except Exception as exception_1:
            l_error(exception_1)
            distro_info = 'Error. No distro.info.txt file.'
        else:
            l_info('distro info:\n%s',distro_info)

        dude_core = DudeCore(CACHE_DIR,logging)

        if p_args.csv:
            signal(SIGINT, lambda a, k : dude_core.handle_sigint())

            dude_core.set_paths_to_scan(p_args.paths)

            if p_args.exclude:
                set_exclude_masks_res=dude_core.set_exclude_masks(False,p_args.exclude)
            elif p_args.exclude_regexp:
                set_exclude_masks_res=dude_core.set_exclude_masks(True,p_args.exclude_regexp)
            else:
                set_exclude_masks_res=dude_core.set_exclude_masks(False,[])

            if set_exclude_masks_res:
                print(set_exclude_masks_res)
                sys.exit(2)

            run_scan_thread=Thread(target=dude_core.scan,daemon=True)
            run_scan_thread.start()

            while run_scan_thread.is_alive():
                print('Scanning ...', dude_core.info_counter,end='\r')
                sleep(0.04)

            run_scan_thread.join()

            run_crc_thread=Thread(target=dude_core.crc_calc,daemon=True)
            run_crc_thread.start()

            while run_crc_thread.is_alive():
                print(f'crc_calc...{fnumber(dude_core.info_files_done)}/{fnumber(dude_core.info_total)}                 ',end='\r')
                sleep(0.04)

            run_crc_thread.join()
            print('')
            dude_core.write_csv(p_args.csv[0])
            print('Done')

        else:
            images_mode = bool(p_args.images or p_args.ih or p_args.id or p_args.ir or p_args.imin or p_args.imax)
            #

            images_mode_tuple=[images_mode]

            if p_args.ih:
                images_mode_tuple.append(int(p_args.ih[0]))
            else:
                images_mode_tuple.append(8)

            if p_args.id:
                images_mode_tuple.append(int(p_args.id[0]))
            else:
                images_mode_tuple.append(5)

            images_mode_tuple.append(p_args.ir)

            if p_args.imin:
                images_mode_tuple.append(int(p_args.imin[0]))
            else:
                images_mode_tuple.append(0)

            if p_args.imax:
                images_mode_tuple.append(int(p_args.imax[0]))
            else:
                images_mode_tuple.append(0)

            if p_args.igps:
                images_mode_tuple.append(True)
            else:
                images_mode_tuple.append(False)


            size_min=0
            if p_args.sizemin:
                size_min_cand = str_to_bytes(p_args.sizemin[0])
                if size_min_cand == -1:
                    print(f"cannot parse sizemin value:'{p_args.sizemin[0]}'")
                    sys.exit(2)
                else:
                    size_min=p_args.sizemin[0]

            size_max=0
            if p_args.sizemax:
                size_max_cand = str_to_bytes(p_args.sizemax[0])
                if size_max_cand == -1:
                    print(f"cannot parse sizemax value:'{p_args.sizemax[0]}'")
                    sys.exit(2)
                else:
                    size_max=p_args.sizemax[0]

            Gui( getcwd(),p_args.paths,p_args.exclude,p_args.exclude_regexp,p_args.norun,images_mode_tuple,size_min,size_max )

    except Exception as e_main:
        print(e_main)
        l_error(e_main)
        sys.exit(1)
