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

import fnmatch
import shutil
import os
import os.path
import pathlib
import re
import signal

import time
import configparser
import logging

import tkinter as tk
from tkinter import PhotoImage
from tkinter import Menu
from tkinter import PanedWindow

from tkinter import ttk

from tkinter.filedialog import askdirectory

from collections import defaultdict
from threading import Thread
import sys

import traceback
import functools

import core
import console
import dialogs


log_levels={logging.DEBUG:'DEBUG',logging.INFO:'INFO'}

try:
    from appdirs import user_cache_dir,user_log_dir,user_config_dir
    CACHE_DIR = os.sep.join([user_cache_dir('dude','PJDude'),"cache"])
    LOG_DIR = user_log_dir('dude','PJDude')
    CONFIG_DIR = user_config_dir('dude')
except Exception as e_import:
    print(e_import)
    CONFIG_DIR=LOG_DIR=CACHE_DIR = os.sep.join([os.getcwd(),"dude-no-appdirs"])

windows = os.name=='nt'

###########################################################################################################################################

CFG_KEY_FULL_CRC='show_full_crc'
CFG_KEY_FULL_PATHS='show_full_paths'
CFG_KEY_REL_SYMLINKS='relative_symlinks'

CFG_KEY_USE_REG_EXPR='use_reg_expr'
CFG_KEY_EXCLUDE_REGEXP='excluderegexpp'

ERASE_EMPTY_DIRS='erase_empty_dirs'
CFG_CONFIRM_SHOW_CRCSIZE='confirm_show_crcsize'
CFG_CONFIRM_SHOW_LINKSTARGETS='confirm_show_links_targets'

CFG_ALLOW_DELETE_ALL='allow_delete_all'
CFG_SKIP_INCORRECT_GROUPS='skip_incorrect_groups'
CFG_ALLOW_DELETE_NON_DUPLICATES='allow_delete_non_duplicates'

CFG_KEY_EXCLUDE='exclude'
CFG_KEY_WRAPPER_FILE = 'file_open_wrapper'
CFG_KEY_WRAPPER_FOLDERS = 'folders_open_wrapper'

cfg_defaults={
    CFG_KEY_FULL_CRC:False,
    CFG_KEY_FULL_PATHS:False,
    CFG_KEY_REL_SYMLINKS:True,
    CFG_KEY_USE_REG_EXPR:False,
    CFG_KEY_EXCLUDE_REGEXP:False,
    ERASE_EMPTY_DIRS:True,
    CFG_CONFIRM_SHOW_CRCSIZE:False,
    CFG_CONFIRM_SHOW_LINKSTARGETS:True,
    CFG_ALLOW_DELETE_ALL:False,
    CFG_SKIP_INCORRECT_GROUPS:True,
    CFG_ALLOW_DELETE_NON_DUPLICATES:False,
    CFG_KEY_WRAPPER_FILE:'',
    CFG_KEY_WRAPPER_FOLDERS:'',
    CFG_KEY_EXCLUDE:''
}

MARK='M'
UPDIR='0'
DIR='1'
DIRLINK='2'
LINK='3'
FILE='4'
SINGLE='5'
SINGLEHARDLINKED='6'
CRC='C'

DELETE=0
SOFTLINK=1
HARDLINK=2

NAME={DELETE:'Delete',SOFTLINK:'Softlink',HARDLINK:'Hardlink'}

HOMEPAGE='https://github.com/PJDude/dude'

FOLDER_LINK = '⇦'
FILE_LINK_LEFT = '🠔'
FILE_LINK_RIGHT = '🠖'

@functools.cache
def get_htime(time_par):
    return time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(int(time_par)))

class Config:
    def __init__(self,config_dir):
        logging.debug('Initializing config: %s', config_dir)
        self.config = configparser.ConfigParser()
        self.config.add_section('main')
        self.config.add_section('geometry')

        self.path = config_dir
        self.file = self.path + '/cfg.ini'

    def write(self):
        logging.debug('writing config')
        pathlib.Path(self.path).mkdir(parents=True,exist_ok=True)
        with open(self.file, 'w', encoding='ASCII') as configfile:
            self.config.write(configfile)

    def read(self):
        logging.debug('reading config')
        if os.path.isfile(self.file):
            try:
                with open(self.file, 'r', encoding='ASCII') as configfile:
                    self.config.read_file(configfile)
            except Exception as e:
                logging.error(e)
        else:
            logging.warning('no config file: %s',self.file)

    def set(self,key,val,section='main'):
        self.config.set(section,key,str(val))

    def set_bool(self,key,val,section='main'):
        self.config.set(section,key,('0','1')[val])

    def get(self,key,default='',section='main'):
        try:
            res=self.config.get(section,key)
        except Exception as e:
            logging.warning('gettting config key: %s',key)
            logging.warning(e)
            res=default
            self.set(key,default,section=section)

        return str(res)

    def get_bool(self,key,section='main'):
        try:
            res=self.config.get(section,key)
            return res=='1'

        except Exception as e:
            logging.warning('gettting config key: %s',key)
            logging.warning(e)
            res=cfg_defaults[key]
            self.set_bool(key,res,section=section)
            return res

###########################################################

class Gui:
    NUMBERS='①②③④⑤⑥⑦⑧⑨⑩' if windows else '⓵⓶⓷⓸⓹⓺⓻⓼⓽⓾'

    PROGRESS_SIGNS='◐◓◑◒'

    MAX_PATHS=10

    sel_item_of_tree = {}

    sel_path_full=''
    folder_items_cache={}

    main_window_active=False

    def block_main_window(func):
        def block_main_window_wrapp(self,*args,**kwargs):
            prev_active=self.main_window_active
            self.main_window_active=False
            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('block_main_window_wrapp:%s:%s:args:%s:kwargs:%s' % (func,e,args,kwargs) )
                self.info_dialog_on_main.show('INTERNAL ERROR block_main_window_wrapp',str(e))
                logging.error('block_main_window_wrapp:%s:%s:args:%s:kwargs: %s',func,e,args,kwargs)
                res=None

            self.main_window_active=prev_active
            return res
        return block_main_window_wrapp

    def busy_cursor(func):
        def busy_cursor_wrapp(self,*args,**kwargs):
            prev_cursor=self.menubar.cget('cursor')

            self.menu_disable()
            self.main.update()

            self.menubar.config(cursor='watch')
            self.main.config(cursor='watch')

            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('busy_cursor_wrapp:%s:%s:args:%s:kwargs:%s' % (func,e,args,kwargs) )
                self.info_dialog_on_main.show('INTERNAL ERROR busy_cursor_wrapp',str(e))
                logging.error('busy_cursor_wrapp:%s:%s:args:%s:kwargs: %s',func,e,args,kwargs)
                res=None

            self.menu_enable()
            self.main.config(cursor=prev_cursor)
            self.menubar.config(cursor=prev_cursor)

            return res
        return busy_cursor_wrapp

    def catched(func):
        def catched_wrapp(self,*args,**kwargs):
            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('catched_wrapp:%s:%s:args:%s:kwargs:%s' % (func,e,args,kwargs) )
                self.info_dialog_on_main.show('INTERNAL ERROR catched_wrapp','%S %s' % (str(func),str(e)) )
                logging.error('catched_wrapp:%s:%s:args:%s:kwargs: %s',func,e,args,kwargs)
                res=None
            return res
        return catched_wrapp

    def restore_status_line(func):
        def restore_status_line_wrapp(self,*args,**kwargs):
            prev=self.status_line.get()
            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('restore_status_line_wrapp:%s:%s:args:%s:kwargs:%s' % (func,e,args,kwargs) )
                self.info_dialog_on_main.show('INTERNAL ERROR restore_status_line_wrapp',str(e))
                logging.error('restore_status_line_wrapp:%s:%s:args:%s:kwargs:%s',func,e,args,kwargs)
                res=None
            else:
                self.status(prev)

            return res
        return restore_status_line_wrapp

    #######################################################################
    action_abort=False
    def progress_dialog_show(self,parent,title,progress_mode1=None,progress_mode2=None,progress1_left_text=None,progress2_left_text=None,abort_tooltip=None):
        self.parent=parent
        self.progres_dialog_shown=True

        self.ps_index =0

        self.progress_mode1=progress_mode1
        self.progress_mode2=progress_mode2

        self.progress_dialog = tk.Toplevel(parent,bg=self.bg_color)
        self.progress_dialog.wm_transient(parent)

        self.progress_dialog.protocol("WM_DELETE_WINDOW", self.progress_dialog_abort)
        self.progress_dialog.bind('<Escape>', lambda event : self.progress_dialog_abort())

        self.progress_dialog.wm_title(title)
        self.progress_dialog.iconphoto(False, self.iconphoto)

        (frame_0:=tk.Frame(self.progress_dialog,bg=self.bg_color)).pack(expand=1,fill='both',side='top')
        (frame_1:=tk.Frame(self.progress_dialog,bg=self.bg_color)).pack(expand=1,fill='both',side='top')

        self.progr1var = tk.DoubleVar()
        self.progr1=ttk.Progressbar(frame_0,orient='horizontal',length=100, mode=progress_mode1,variable=self.progr1var)

        if progress_mode1:
            self.progr1.grid(row=0,column=1,padx=1,pady=4,sticky='news')

        self.progr1_lab_left=tk.Label(frame_0,width=17,bg=self.bg_color)
        if progress1_left_text:
            self.progr1_lab_left.grid(row=0,column=0,padx=1,pady=4)
            self.progr1_lab_left.config(text=progress1_left_text)

        self.progr1_lab_right=tk.Label(frame_0,width=17,bg=self.bg_color)

        if self.progress_mode1=='determinate':
            self.progr1_lab_right.grid(row=0,column=2,padx=1,pady=4)
            self.progress1_func = lambda progress1 : self.progr1var.set(progress1)
        else :
            self.progress1_func = lambda args : None

        self.progr2_var = tk.DoubleVar()
        self.progr2=ttk.Progressbar(frame_0,orient='horizontal',length=100, mode=progress_mode2,variable=self.progr2_var)
        self.progr2_lab_right=tk.Label(frame_0,width=17,bg=self.bg_color)

        if progress_mode2:
            self.progress_dialog.minsize(550, 60)
            self.progr2.grid(row=1,column=1,padx=1,pady=4,sticky='news')

            if progress2_left_text:
                self.progr1_lab_left=tk.Label(frame_0,width=17,bg=self.bg_color)
                self.progr1_lab_left.grid(row=1,column=0,padx=1,pady=4)
                self.progr1_lab_left.config(text=progress2_left_text)

            self.progr2_lab_right.grid(row=1,column=2,padx=1,pady=4)
        else:
            self.progress_dialog.minsize(300, 60)

        frame_0.grid_columnconfigure(1, weight=1)

        self.message=tk.StringVar()
        tk.Label(frame_1,textvariable=self.message,anchor='n',justify='center',width=20,bg=self.bg_color).pack(side='top',padx=8,pady=8,expand=1,fill='x')
        (abort_button:=ttk.Button(frame_1, text='Abort', width=10 ,command=self.progress_dialog_abort ) ).pack(side='bottom',padx=8,pady=8)

        if abort_tooltip:
            abort_button.bind("<Motion>", lambda event : self.motion_on_widget(event,abort_tooltip))
            abort_button.bind("<Leave>", lambda event : self.widget_leave())

        try:
            self.progress_dialog.update()
            self.progress_dialog.grab_set()
            dialogs.set_geometry_by_parent(self.progress_dialog,parent)
        except Exception :
            pass

        self.prev_parent_cursor=parent.cget('cursor')
        parent.config(cursor="watch")

        self.action_abort=False

    def progress_dialog_abort(self):
        self.action_abort=True

    progres_dialog_shown=False
    def progress_dialog_ended(self):
        return not self.progres_dialog_shown

    def progress_dialog_end(self):
        self.progress_dialog.grab_release()
        self.progress_dialog.destroy()
        self.parent.config(cursor=self.prev_parent_cursor)
        self.progres_dialog_shown=False

    message_prev=''
    progr_1_right_prev=''
    progr_2_right_prev=''
    time_without_busy_sign=0

    def progress_dialog_update(self,message,progress1=None,progress2=None,progress_size_descr=None,progress_quant_descr=None,status_info=None):
        prefix=''

        if status_info:
            self.status(status_info)
        else:
            self.status('')

        if self.progr_1_right_prev==progress_size_descr and self.progr_2_right_prev==progress_quant_descr and self.message_prev==message:
            if time.time()>self.time_without_busy_sign+1.0:
                prefix=self.PROGRESS_SIGNS[self.ps_index]
                self.ps_index=(self.ps_index+1)%4

        else:
            self.message_prev=message
            self.progr_1_right_prev=progress_size_descr
            self.progr_2_right_prev=progress_quant_descr

            self.time_without_busy_sign=time.time()

            self.progress1_func(progress1)
            self.progr1_lab_right.config(text=progress_size_descr)
            self.progr2_var.set(progress2)
            self.progr2_lab_right.config(text=progress_quant_descr)

        self.message.set('%s\n%s'%(prefix,message))
        self.progress_dialog.update()

    other_tree={}

    def handle_sigint(self):
        self.status("Received SIGINT signal")
        logging.warning("Received SIGINT signal")
        self.progress_dialog_abort()

    def __init__(self,cwd,paths_to_add=None,exclude=None,exclude_regexp=None,norun=None):
        self.cwd=cwd

        self.cfg = Config(CONFIG_DIR)
        self.cfg.read()

        self.paths_to_scan_frames=[]
        self.exclude_frames=[]

        self.paths_to_scan_from_dialog=[]

        signal.signal(signal.SIGINT, lambda a, k : self.handle_sigint())

        ####################################################################
        self.main = tk.Tk()
        self.main.title(f'Dude (DUplicates DEtector) {VER_TIMESTAMP}')
        self.main.protocol("WM_DELETE_WINDOW", self.delete_window_wrapper)
        self.main.withdraw()
        self.main.update()

        self.main.minsize(1200, 800)

        self.iconphoto = PhotoImage(file = os.path.join(os.path.dirname(DUDE_FILE),'icon.png'))
        self.main.iconphoto(False, self.iconphoto)

        self.main.bind('<KeyPress-F2>', lambda event : self.settings_dialog.show())
        #focus=self.cancel_button
        self.main.bind('<KeyPress-F1>', lambda event : self.aboout_dialog.show())
        self.main.bind('<KeyPress-s>', lambda event : self.scan_dialog_show())
        self.main.bind('<KeyPress-S>', lambda event : self.scan_dialog_show())

        #self.defaultFont = font.nametofont("TkDefaultFont")
        #self.defaultFont.configure(family="Monospace regular",size=8,weight=font.BOLD)
        #self.defaultFont.configure(family="Monospace regular",size=10)
        #self.main.option_add("*Font", self.defaultFont)

        self.tooltip = tk.Toplevel(self.main)
        self.tooltip.withdraw()
        self.tooltip.wm_overrideredirect(True)
        self.tooltip_lab=tk.Label(self.tooltip, justify='left', background="#ffffe0", relief='solid', borderwidth=0, wraplength = 1200)
        self.tooltip_lab.pack(ipadx=1)

        ####################################################################
        style = ttk.Style()

        style.theme_create("dummy", parent='vista' if windows else 'clam' )

        self.bg_color = style.lookup('TFrame', 'background')

        style.theme_use("dummy")

        style.configure("TButton", anchor = "center")
        style.configure("TButton", background = self.bg_color)

        style.configure("TCheckbutton", background = self.bg_color)

        style.map("TButton",  relief=[('disabled',"flat"),('',"raised")] )
        style.map("TButton",  fg=[('disabled',"gray"),('',"black")] )

        style.map("Treeview.Heading",  relief=[('','raised')] )
        style.configure("Treeview",rowheight=18)

        bg_focus='#90DD90'
        bg_focus_off='#90AA90'
        bg_sel='#AAAAAA'

        #style.map('Treeview', background=[('focus',bg_focus),('selected',bg_sel),('',self.bg_color)])
        style.map('Treeview', background=[('focus',bg_focus),('selected',bg_sel),('','white')])

        style.map('semi_focus.Treeview', background=[('focus',bg_focus),('selected',bg_focus),('','white')])
        style.map('semi_focus_off.Treeview', background=[('focus',bg_focus_off),('selected',bg_focus_off),('','white')])
        style.map('default.Treeview', background=[('focus',bg_focus),('selected',bg_sel),('','white')])

        #works but not for every theme
        #style.configure("Treeview", fieldbackground=self.bg_color)

        #######################################################################
        self.menubar = Menu(self.main,bg=self.bg_color)
        self.main.config(menu=self.menubar)
        #######################################################################

        self.status_var_all_size=tk.StringVar()
        self.status_var_all_quant=tk.StringVar()
        self.status_var_groups=tk.StringVar()
        self.status_var_path=tk.StringVar()
        self.status_var_folder_size=tk.StringVar()
        self.status_var_folder_quant=tk.StringVar()

        self.paned = PanedWindow(self.main,orient=tk.VERTICAL,relief='sunken',showhandle=0,bd=0,bg=self.bg_color,sashwidth=2,sashrelief='flat')
        self.paned.pack(fill='both',expand=1)

        frame_groups = tk.Frame(self.paned,bg=self.bg_color)
        self.paned.add(frame_groups)
        frame_folder = tk.Frame(self.paned,bg=self.bg_color)
        self.paned.add(frame_folder)

        frame_groups.grid_columnconfigure(0, weight=1)
        frame_groups.grid_rowconfigure(0, weight=1,minsize=200)

        frame_folder.grid_columnconfigure(0, weight=1)
        frame_folder.grid_rowconfigure(0, weight=1,minsize=200)

        (status_frame_groups := tk.Frame(frame_groups,bg=self.bg_color)).pack(side='bottom', fill='both')
        self.status_var_groups.set('0')
        self.status_var_path.set('')

        tk.Label(status_frame_groups,width=10,textvariable=self.status_var_all_quant,borderwidth=2,bg=self.bg_color,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=16,text="All marked files # ",relief='groove',borderwidth=2,bg=self.bg_color,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=10,textvariable=self.status_var_all_size,borderwidth=2,bg=self.bg_color,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=18,text='All marked files size: ',relief='groove',borderwidth=2,bg=self.bg_color,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=10,textvariable=self.status_var_groups,borderwidth=2,bg=self.bg_color,relief='groove',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=10,text='Groups: ',relief='groove',borderwidth=2,bg=self.bg_color,anchor='e').pack(fill='x',expand=0,side='right')
        #tk.Label(status_frame_groups,width=8,text='Full path: ',relief='groove',borderwidth=2,bg=self.bg_color,anchor='e').pack(fill='x',expand=0,side='left')
        self.status_var_full_path_label = tk.Label(status_frame_groups,textvariable=self.status_var_path,relief='flat',borderwidth=1,bg=self.bg_color,anchor='w')
        self.status_var_full_path_label.pack(fill='x',expand=1,side='left')
        self.status_var_full_path_label.bind("<Motion>", lambda event : self.motion_on_widget(event,'The full path of a directory shown in the bottom panel.'))
        self.status_var_full_path_label.bind("<Leave>", lambda event : self.widget_leave())

        (status_frame_folder := tk.Frame(frame_folder,bg=self.bg_color)).pack(side='bottom',fill='both')

        self.status_line=tk.StringVar()
        self.status_line.set('')

        self.status_line_lab=tk.Label(status_frame_folder,width=30,textvariable=self.status_line,borderwidth=2,bg=self.bg_color,relief='groove',anchor='w')
        self.status_line_lab.pack(fill='x',expand=1,side='left')

        tk.Label(status_frame_folder,width=10,textvariable=self.status_var_folder_quant,borderwidth=2,bg=self.bg_color,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_folder,width=16,text='Marked files # ',relief='groove',borderwidth=2,bg=self.bg_color,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_folder,width=10,textvariable=self.status_var_folder_size,borderwidth=2,bg=self.bg_color,relief='groove',foreground='red',anchor='w').pack(expand=0,side='right')
        tk.Label(status_frame_folder,width=18,text='Marked files size: ',relief='groove',borderwidth=2,bg=self.bg_color,anchor='e').pack(fill='x',expand=0,side='right')

        self.main.unbind_class('Treeview', '<KeyPress-Up>')
        self.main.unbind_class('Treeview', '<KeyPress-Down>')
        self.main.unbind_class('Treeview', '<KeyPress-Next>')
        self.main.unbind_class('Treeview', '<KeyPress-Prior>')
        self.main.unbind_class('Treeview', '<KeyPress-space>')
        self.main.unbind_class('Treeview', '<KeyPress-Return>')
        self.main.unbind_class('Treeview', '<KeyPress-Left>')
        self.main.unbind_class('Treeview', '<KeyPress-Right>')
        self.main.unbind_class('Treeview', '<Double-Button-1>')

        self.main.unbind_class('Treeview', '<ButtonPress-1>')

        self.main.bind_class('Treeview','<KeyPress>', self.key_press )

        self.main.bind_class('Treeview','<FocusIn>',    self.tree_on_focus_in )
        self.main.bind_class('Treeview','<FocusOut>',   self.tree_focus_out )

        self.main.bind_class('Treeview','<ButtonPress-3>', self.context_menu_show)

        self.groups_tree=ttk.Treeview(frame_groups,takefocus=True,selectmode='none',show=('tree','headings') )

        self.org_label={}
        self.org_label['path']='Subpath'
        self.org_label['file']='File'
        self.org_label['size_h']='Size'
        self.org_label['instances_h']='Copies'
        self.org_label['ctime_h']='Change Time'

        self.groups_tree["columns"]=('pathnr','path','file','size','size_h','ctime','dev','inode','crc','instances','instances_h','ctime_h','kind')

        self.groups_tree["displaycolumns"]=('path','file','size_h','instances_h','ctime_h')

        self.groups_tree.column('#0', width=120, minwidth=100, stretch=tk.NO)
        self.groups_tree.column('path', width=100, minwidth=10, stretch=tk.YES )
        self.groups_tree.column('file', width=100, minwidth=10, stretch=tk.YES )
        self.groups_tree.column('size_h', width=80, minwidth=80, stretch=tk.NO)
        self.groups_tree.column('instances_h', width=80, minwidth=80, stretch=tk.NO)
        self.groups_tree.column('ctime_h', width=150, minwidth=100, stretch=tk.NO)

        self.groups_tree.heading('#0',text='CRC / Scan Path',anchor=tk.W)
        self.groups_tree.heading('path',anchor=tk.W )
        self.groups_tree.heading('file',anchor=tk.W )
        self.groups_tree.heading('size_h',anchor=tk.W)
        self.groups_tree.heading('ctime_h',anchor=tk.W)
        self.groups_tree.heading('instances_h',anchor=tk.W)

        self.groups_tree.heading('size_h', text='Size \u25BC')

        self.tree_with_focus=self.groups_tree

        #bind_class breaks columns resizing
        self.groups_tree.bind('<ButtonPress-1>', self.tree_on_mouse_button_press)
        self.groups_tree.bind('<Control-ButtonPress-1>',  lambda event :self.tree_on_mouse_button_press(event,True) )
        self.main.unbind_class('Treeview', '<<TreeviewClose>>')

        vsb1 = ttk.Scrollbar(frame_groups, orient='vertical', command=self.groups_tree.yview,takefocus=False)
        #,bg=self.bg_color
        self.groups_tree.configure(yscrollcommand=vsb1.set)

        vsb1.pack(side='right',fill='y',expand=0)
        self.groups_tree.pack(fill='both',expand=1, side='left')

        self.groups_tree.bind('<Double-Button-1>', self.double_left_button)

        self.folder_tree=ttk.Treeview(frame_folder,takefocus=True,selectmode='none')

        self.folder_tree['columns']=('file','dev','inode','kind','crc','size','size_h','ctime','ctime_h','instances','instances_h')

        self.folder_tree['displaycolumns']=('file','size_h','instances_h','ctime_h')

        self.folder_tree.column('#0', width=120, minwidth=100, stretch=tk.NO)

        self.folder_tree.column('file', width=200, minwidth=100, stretch=tk.YES)
        self.folder_tree.column('size_h', width=80, minwidth=80, stretch=tk.NO)
        self.folder_tree.column('instances_h', width=80, minwidth=80, stretch=tk.NO)
        self.folder_tree.column('ctime_h', width=150, minwidth=100, stretch=tk.NO)

        self.folder_tree.heading('#0',text='CRC',anchor=tk.W)
        self.folder_tree.heading('file',anchor=tk.W)
        self.folder_tree.heading('size_h',anchor=tk.W)
        self.folder_tree.heading('instances_h',anchor=tk.W)
        self.folder_tree.heading('ctime_h',anchor=tk.W)

        for tree in [self.groups_tree,self.folder_tree]:
            for col in tree["displaycolumns"]:
                if col in self.org_label:
                    tree.heading(col,text=self.org_label[col])

        self.folder_tree.heading('file', text='File \u25B2')

        vsb2 = ttk.Scrollbar(frame_folder, orient='vertical', command=self.folder_tree.yview,takefocus=False)
        #,bg=self.bg_color
        self.folder_tree.configure(yscrollcommand=vsb2.set)

        vsb2.pack(side='right',fill='y',expand=0)
        self.folder_tree.pack(fill='both',expand=1,side='left')

        self.folder_tree.bind('<Double-Button-1>', self.double_left_button)

        self.groups_tree.tag_configure(MARK, foreground='red')
        self.groups_tree.tag_configure(MARK, background='red')
        self.folder_tree.tag_configure(MARK, foreground='red')
        self.folder_tree.tag_configure(MARK, background='red')

        self.groups_tree.tag_configure(CRC, foreground='gray')

        self.folder_tree.tag_configure(SINGLE, foreground='gray')
        self.folder_tree.tag_configure(DIR, foreground='blue2')
        self.folder_tree.tag_configure(DIRLINK, foreground='blue2')
        self.folder_tree.tag_configure(LINK, foreground='darkgray')

        #bind_class breaks columns resizing
        self.folder_tree.bind('<ButtonPress-1>', self.tree_on_mouse_button_press)
        self.folder_tree.bind('<Control-ButtonPress-1>',  lambda event :self.tree_on_mouse_button_press(event,True) )

        self.other_tree[self.folder_tree]=self.groups_tree
        self.other_tree[self.groups_tree]=self.folder_tree

        try:
            self.main.update()
            cfg_geometry=self.cfg.get('main','',section='geometry')

            if cfg_geometry:
                self.main.geometry(cfg_geometry)
            else:
                x_offset = int(0.5*(self.main.winfo_screenwidth()-self.main.winfo_width()))
                y_offset = int(0.5*(self.main.winfo_screenheight()-self.main.winfo_height()))

                self.main.geometry(f'+{x_offset}+{y_offset}')

        except Exception as e:
            self.status(str(e))
            logging.error(e)
            cfg_geometry = None

        self.main.deiconify()

        self.paned.update()
        self.paned.sash_place(0,0,self.cfg.get('sash_coord',400,section='geometry'))

        #prevent displacement
        if cfg_geometry :
            self.main.geometry(cfg_geometry)

        self.popup_groups = Menu(self.groups_tree, tearoff=0,bg=self.bg_color)
        self.popup_groups.bind("<FocusOut>",lambda event : self.popup_groups.unpost() )

        self.popup_folder = Menu(self.folder_tree, tearoff=0,bg=self.bg_color)
        self.popup_folder.bind("<FocusOut>",lambda event : self.popup_folder.unpost() )

        #######################################################################
        #scan dialog

        def pre_show(on_main_window_dialog=True):
            self.menubar_unpost()
            self.hide_tooltip()
            self.popup_groups.unpost()
            self.popup_folder.unpost()

            if on_main_window_dialog:
                self.main_window_active=False

                self.menu_disable()
                self.menubar.config(cursor="watch")

            return False

        def post_close(on_main_window_dialog=True):
            self.menu_enable()
            self.menubar.config(cursor="")

            if on_main_window_dialog:
                self.main_window_active=True

        self.scan_dialog=dialogs.GenericDialog(self.main,self.iconphoto,self.bg_color,'Scan',pre_show=pre_show,post_close=post_close)

        self.write_scan_log=tk.BooleanVar()
        self.write_scan_log.set(False)

        self.scan_dialog.area_main.grid_columnconfigure(0, weight=1)
        self.scan_dialog.area_main.grid_rowconfigure(0, weight=1)
        self.scan_dialog.area_main.grid_rowconfigure(1, weight=1)

        self.scan_dialog.widget.bind('<Alt_L><a>',lambda event : self.path_to_scan_add_dialog())
        self.scan_dialog.widget.bind('<Alt_L><A>',lambda event : self.path_to_scan_add_dialog())
        self.scan_dialog.widget.bind('<Alt_L><s>',lambda event : self.scan_from_button())
        self.scan_dialog.widget.bind('<Alt_L><S>',lambda event : self.scan_from_button())

        self.scan_dialog.widget.bind('<Alt_L><E>',lambda event : self.exclude_mask_add_dialog())
        self.scan_dialog.widget.bind('<Alt_L><e>',lambda event : self.exclude_mask_add_dialog())

        ##############
        temp_frame = tk.LabelFrame(self.scan_dialog.area_main,text='Paths To scan:',borderwidth=2,bg=self.bg_color,takefocus=False)
        temp_frame.grid(row=0,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        sf_par=dialogs.SFrame(temp_frame,bg=self.bg_color)
        sf_par.pack(fill='both',expand=True,side='top')
        self.paths_frame=sf_par.frame()

        buttons_fr = tk.Frame(temp_frame,bg=self.bg_color,takefocus=False)
        buttons_fr.pack(fill='both',expand=False,side='bottom')

        self.add_path_button = ttk.Button(buttons_fr,width=18,text="Add Path ...",command=self.path_to_scan_add_dialog,underline=0)
        self.add_path_button.pack(side='left',pady=4,padx=4)

        #self.AddDrivesButton = ttk.Button(buttons_fr,width=10,text="Add drives",command=self.AddDrives,underline=4)
        #self.AddDrivesButton.grid(column=1, row=100,pady=4,padx=4)

        self.clear_paths_list_button=ttk.Button(buttons_fr,width=10,text="Clear List",command=self.scan_paths_clear )
        self.clear_paths_list_button.pack(side='right',pady=4,padx=4)

        self.paths_frame.grid_columnconfigure(1, weight=1)
        self.paths_frame.grid_rowconfigure(99, weight=1)

        ##############
        self.exclude_regexp_scan=tk.BooleanVar()

        temp_frame2 = tk.LabelFrame(self.scan_dialog.area_main,text='Exclude from scan:',borderwidth=2,bg=self.bg_color,takefocus=False)
        temp_frame2.grid(row=1,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        sf_par2=dialogs.SFrame(temp_frame2,bg=self.bg_color)
        sf_par2.pack(fill='both',expand=True,side='top')
        self.exclude_frame=sf_par2.frame()

        buttons_fr2 = tk.Frame(temp_frame2,bg=self.bg_color,takefocus=False)
        buttons_fr2.pack(fill='both',expand=False,side='bottom')

        self.add_exclude_button = ttk.Button(buttons_fr2,width=18,text="Add Expression ...",command=self.exclude_mask_add_dialog,underline=4)
        tooltip_string = 'during the scan, the entire path is checked \nagainst the specified expression,\ne.g.' + ('*windows* etc. (without regular expression)\nor .*windows.*, etc. (with regular expression)' if windows else '*.git* etc. (without regular expression)\nor .*\\.git.* etc. (with regular expression)')
        self.add_exclude_button.bind("<Motion>", lambda event : self.motion_on_widget(event,tooltip_string))
        self.add_exclude_button.bind("<Leave>", lambda event : self.widget_leave())

        self.add_exclude_button.pack(side='left',pady=4,padx=4)

        self.add_exclude_button2 = ttk.Button(buttons_fr2,width=18,text="Add path ...",command=self.exclude_mask_add_dir)
        self.add_exclude_button2.pack(side='left',pady=4,padx=4)

        ttk.Checkbutton(buttons_fr2,text='treat as a regular expression',variable=self.exclude_regexp_scan,command=self.exclude_regexp_set).pack(side='left',pady=4,padx=4)

        self.clear_excludes_list_button=ttk.Button(buttons_fr2,width=10,text="Clear List",command=self.exclude_masks_clear )
        self.clear_excludes_list_button.pack(side='right',pady=4,padx=4)

        self.exclude_frame.grid_columnconfigure(1, weight=1)
        self.exclude_frame.grid_rowconfigure(99, weight=1)
        ##############

        ttk.Checkbutton(self.scan_dialog.area_main,text='write scan results to application log',variable=self.write_scan_log).grid(row=3,column=0,sticky='news',padx=8,pady=3,columnspan=3)

        self.scan_button = ttk.Button(self.scan_dialog.area_buttons,width=12,text="Scan",command=self.scan_from_button,underline=0)
        self.scan_button.pack(side='right',padx=4,pady=4)

        self.scan_cancel_button = ttk.Button(self.scan_dialog.area_buttons,width=12,text="Cancel",command=self.scan_dialog_hide_wrapper,underline=0)
        self.scan_cancel_button.pack(side='left',padx=4,pady=4)

        self.scan_dialog.focus=self.scan_cancel_button

        def pre_show_settings():
            _ = {var.set(self.cfg.get_bool(key)) for var,key in self.settings}
            _ = {var.set(self.cfg.get(key)) for var,key in self.settings_str}
            return pre_show()

        #######################################################################
        #Settings Dialog
        self.settings_dialog=dialogs.GenericDialog(self.main,self.iconphoto,self.bg_color,'Settings',pre_show=pre_show_settings,post_close=post_close)

        self.show_full_crc = tk.BooleanVar()
        self.show_full_paths = tk.BooleanVar()
        self.create_relative_symlinks = tk.BooleanVar()
        self.erase_empty_directories = tk.BooleanVar()

        self.allow_delete_all = tk.BooleanVar()
        self.skip_incorrect_groups = tk.BooleanVar()
        self.allow_delete_non_duplicates = tk.BooleanVar()

        self.confirm_show_crc_and_size = tk.BooleanVar()

        self.confirm_show_links_targets = tk.BooleanVar()
        self.file_open_wrapper = tk.StringVar()
        self.folders_open_wrapper = tk.StringVar()

        self.settings = [
            (self.show_full_crc,CFG_KEY_FULL_CRC),
            (self.show_full_paths,CFG_KEY_FULL_PATHS),
            (self.create_relative_symlinks,CFG_KEY_REL_SYMLINKS),
            (self.erase_empty_directories,ERASE_EMPTY_DIRS),
            (self.confirm_show_crc_and_size,CFG_CONFIRM_SHOW_CRCSIZE),
            (self.confirm_show_links_targets,CFG_CONFIRM_SHOW_LINKSTARGETS),
            (self.allow_delete_all,CFG_ALLOW_DELETE_ALL),
            (self.skip_incorrect_groups,CFG_SKIP_INCORRECT_GROUPS),
            (self.allow_delete_non_duplicates,CFG_ALLOW_DELETE_NON_DUPLICATES)
        ]
        self.settings_str = [
            (self.file_open_wrapper,CFG_KEY_WRAPPER_FILE),
            (self.folders_open_wrapper,CFG_KEY_WRAPPER_FOLDERS),
        ]

        row = 0
        label_frame=tk.LabelFrame(self.settings_dialog.area_main, text="Main panels",borderwidth=2,bg=self.bg_color)
        label_frame.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

        (cb_1:=ttk.Checkbutton(label_frame, text = 'Show full CRC', variable=self.show_full_crc)).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
        cb_1.bind("<Motion>", lambda event : self.motion_on_widget(event,'If disabled, shortest necessary prefix of full CRC wil be shown'))
        cb_1.bind("<Leave>", lambda event : self.widget_leave())

        (cb_2:=ttk.Checkbutton(label_frame, text = 'Show full scan paths', variable=self.show_full_paths)).grid(row=1,column=0,sticky='wens',padx=3,pady=2)
        cb_2.bind("<Motion>", lambda event : self.motion_on_widget(event,f'If disabled, scan path numbers will be shown (e.g. {self.NUMBERS[0]},{self.NUMBERS[1]}... ) instead of full paths'))
        cb_2.bind("<Leave>", lambda event : self.widget_leave())

        label_frame=tk.LabelFrame(self.settings_dialog.area_main, text="Confirmation dialogs",borderwidth=2,bg=self.bg_color)
        label_frame.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

        (cb_3:=ttk.Checkbutton(label_frame, text = 'Skip groups with invalid selection', variable=self.skip_incorrect_groups)).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
        cb_3.bind("<Motion>", lambda event : self.motion_on_widget(event,'Groups with incorrect marks set will abort action.\nEnable this option to skip those groups.\nFor delete or soft-link action, one file in a group \nmust remain unmarked (see below). For hardlink action,\nmore than one file in a group must be marked.'))
        cb_3.bind("<Leave>", lambda event : self.widget_leave())

        (cb_4:=ttk.Checkbutton(label_frame, text = 'Allow deletion of all copies (WARNING!)', variable=self.allow_delete_all)).grid(row=1,column=0,sticky='wens',padx=3,pady=2)
        cb_4.bind("<Motion>", lambda event : self.motion_on_widget(event,'Before deleting selected files, files selection in every CRC \ngroup is checked, at least one file should remain unmarked.\nIf This option is enabled it will be possible to delete all copies'))
        cb_4.bind("<Leave>", lambda event : self.widget_leave())

        ttk.Checkbutton(label_frame, text = 'Show soft links targets', variable=self.confirm_show_links_targets ).grid(row=2,column=0,sticky='wens',padx=3,pady=2)
        ttk.Checkbutton(label_frame, text = 'Show CRC and size', variable=self.confirm_show_crc_and_size ).grid(row=3,column=0,sticky='wens',padx=3,pady=2)

        label_frame=tk.LabelFrame(self.settings_dialog.area_main, text="Processing",borderwidth=2,bg=self.bg_color)
        label_frame.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

        ttk.Checkbutton(label_frame, text = 'Create relative symbolic links', variable=self.create_relative_symlinks                  ).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
        ttk.Checkbutton(label_frame, text = 'Erase remaining empty directories', variable=self.erase_empty_directories                  ).grid(row=1,column=0,sticky='wens',padx=3,pady=2)

        #ttk.Checkbutton(fr, text = 'Allow to delete regular files (WARNING!)', variable=self.allow_delete_non_duplicates        ).grid(row=row,column=0,sticky='wens',padx=3,pady=2)

        label_frame=tk.LabelFrame(self.settings_dialog.area_main, text="Opening wrappers",borderwidth=2,bg=self.bg_color)
        label_frame.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

        tk.Label(label_frame,text='File: ',bg=self.bg_color,anchor='w').grid(row=0, column=0,sticky='news')
        tk.Label(label_frame,text='Folders: ',bg=self.bg_color,anchor='w').grid(row=1, column=0,sticky='news')

        (en_1:=ttk.Entry(label_frame,textvariable=self.file_open_wrapper)).grid(row=0, column=1,sticky='news',padx=3,pady=2)
        (en_2:=ttk.Entry(label_frame,textvariable=self.folders_open_wrapper)).grid(row=1, column=1,sticky='news',padx=3,pady=2)

        en_1.bind("<Motion>", lambda event : self.motion_on_widget(event,'Command executed on "Open File" with full file path as parameter.\nIf empty default os association will be executed.'))
        en_1.bind("<Leave>", lambda event : self.widget_leave())

        en_2.bind("<Motion>", lambda event : self.motion_on_widget(event,'Command executed on "Open Folder" with full path as parameter.\nIf empty default os filemanager will be used.'))
        en_2.bind("<Leave>", lambda event : self.widget_leave())

        label_frame.grid_columnconfigure(1, weight=1)

        bfr=tk.Frame(self.settings_dialog.area_main,bg=self.bg_color)
        self.settings_dialog.area_main.grid_rowconfigure(row, weight=1); row+=1

        bfr.grid(row=row,column=0) ; row+=1

        ttk.Button(bfr, text='Set defaults',width=14, command=self.settings_reset).pack(side='left', anchor='n',padx=5,pady=5)
        ttk.Button(bfr, text='OK', width=14, command=self.settings_ok ).pack(side='left', anchor='n',padx=5,pady=5)
        self.cancel_button=ttk.Button(bfr, text='Cancel', width=14 ,command=self.settings_dialog.hide )
        self.cancel_button.pack(side='right', anchor='n',padx=5,pady=5)

        self.settings_dialog.area_main.grid_columnconfigure(0, weight=1)

        #######################################################################
        self.info_dialog_on_main = dialogs.LabelDialog(self.main,self.iconphoto,self.bg_color,pre_show=pre_show,post_close=post_close)
        self.text_ask_dialog = dialogs.TextDialogQuestion(self.main,self.iconphoto,self.bg_color,pre_show=pre_show,post_close=post_close)
        self.text_info_dialog = dialogs.TextDialogInfo(self.main,self.iconphoto,self.bg_color,pre_show=pre_show,post_close=post_close)
        self.info_dialog_on_scan = dialogs.LabelDialog(self.scan_dialog.widget,self.iconphoto,self.bg_color,pre_show=pre_show,post_close=post_close)
        self.exclude_dialog_on_scan = dialogs.EntryDialogQuestion(self.scan_dialog.widget,self.iconphoto,self.bg_color,pre_show=pre_show,post_close=post_close)

        #self.mark_dialog_on_main = dialogs.CheckboxEntryDialogQuestion(self.main,self.iconphoto,self.bg_color,pre_show=pre_show,post_close=post_close)
        self.mark_dialog_on_groups = dialogs.CheckboxEntryDialogQuestion(self.groups_tree,self.iconphoto,self.bg_color,pre_show=pre_show,post_close=post_close)
        self.mark_dialog_on_folder = dialogs.CheckboxEntryDialogQuestion(self.folder_tree,self.iconphoto,self.bg_color,pre_show=pre_show,post_close=post_close)

        self.info_dialog_on_mark={}

        self.info_dialog_on_mark[self.groups_tree] = dialogs.LabelDialog(self.mark_dialog_on_groups.widget,self.iconphoto,self.bg_color,pre_show=lambda : pre_show(False),post_close=lambda : post_close(False))
        self.info_dialog_on_mark[self.folder_tree] = dialogs.LabelDialog(self.mark_dialog_on_folder.widget,self.iconphoto,self.bg_color,pre_show=lambda : pre_show(False),post_close=lambda : post_close(False))

        #self.find_dialog_on_main = dialogs.FindEntryDialog(self.main,self.iconphoto,self.bg_color,self.find_mod,self.find_prev_from_dialog,self.find_next_from_dialog,pre_show=pre_show,post_close=post_close)

        self.find_dialog_on_groups = dialogs.FindEntryDialog(self.groups_tree,self.iconphoto,self.bg_color,self.find_mod,self.find_prev_from_dialog,self.find_next_from_dialog,pre_show=pre_show,post_close=post_close)
        self.find_dialog_on_folder = dialogs.FindEntryDialog(self.folder_tree,self.iconphoto,self.bg_color,self.find_mod,self.find_prev_from_dialog,self.find_next_from_dialog,pre_show=pre_show,post_close=post_close)

        #self.info_dialog_on_find = dialogs.LabelDialog(self.find_dialog_on_main.widget,self.iconphoto,self.bg_color,pre_show=lambda : pre_show(False),post_close=post_close)

        self.info_dialog_on_find={}

        self.info_dialog_on_find[self.groups_tree] = dialogs.LabelDialog(self.find_dialog_on_groups.widget,self.iconphoto,self.bg_color,pre_show=lambda : pre_show(False),post_close=lambda : post_close(False))
        self.info_dialog_on_find[self.folder_tree] = dialogs.LabelDialog(self.find_dialog_on_folder.widget,self.iconphoto,self.bg_color,pre_show=lambda : pre_show(False),post_close=lambda : post_close(False))

       #######################################################################
        #About Dialog
        self.aboout_dialog=dialogs.GenericDialog(self.main,self.iconphoto,self.bg_color,'',pre_show=pre_show,post_close=post_close)

        frame1 = tk.LabelFrame(self.aboout_dialog.area_main,text='',bd=2,bg=self.bg_color,takefocus=False)
        frame1.grid(row=0,column=0,sticky='news',padx=4,pady=(4,2))
        self.aboout_dialog.area_main.grid_rowconfigure(1, weight=1)

        text= f'\n\nDUDE (DUplicates DEtector) {VER_TIMESTAMP}\nAuthor: Piotr Jochymek\n\n{HOMEPAGE}\n\nPJ.soft.dev.x@gmail.com\n\n'

        tk.Label(frame1,text=text,bg=self.bg_color,justify='center').pack(expand=1,fill='both')

        frame2 = tk.LabelFrame(self.aboout_dialog.area_main,text='',bd=2,bg=self.bg_color,takefocus=False)
        frame2.grid(row=1,column=0,sticky='news',padx=4,pady=(2,4))
        lab2_text=  'LOGS DIRECTORY     :  ' + LOG_DIR + '\n' + \
                    'SETTINGS DIRECTORY :  ' + CONFIG_DIR + '\n' + \
                    'CACHE DIRECTORY    :  ' + CACHE_DIR + '\n\n' + \
                    'LOGGING LEVEL      :  ' + log_levels[LOG_LEVEL] + '\n\n' + \
                    'Current log file   :  ' + log

        lab_courier = tk.Label(frame2,text=lab2_text,bg=self.bg_color,justify='left')
        lab_courier.pack(expand=1,fill='both')

        try:
            lab_courier.configure(font=('Courier', 10))
        except:
            try:
                lab_courier.configure(font=('TkFixedFont', 10))
            except:
                pass

        #######################################################################
        #License Dialog
        logging.debug('DUDE_FILE:%s',DUDE_FILE )

        try:
            self.license=pathlib.Path(os.path.join(os.path.dirname(DUDE_FILE),'LICENSE')).read_text(encoding='ASCII')
        except Exception as exception_1:
            logging.error(exception_1)
            try:
                self.license=pathlib.Path(os.path.join(os.path.dirname(os.path.dirname(DUDE_FILE)),'LICENSE')).read_text(encoding='ASCII')
            except Exception as exception_2:
                logging.error(exception_2)
                self.exit()

        self.license_dialog=dialogs.GenericDialog(self.main,self.iconphoto,self.bg_color,'',pre_show=pre_show,post_close=post_close,min_width=800,min_height=520)

        frame1 = tk.LabelFrame(self.license_dialog.area_main,text='',bd=2,bg=self.bg_color,takefocus=False)
        frame1.grid(row=0,column=0,sticky='news',padx=4,pady=4)
        self.license_dialog.area_main.grid_rowconfigure(0, weight=1)

        lab_courier=tk.Label(frame1,text=self.license,bg=self.bg_color,justify='center')
        lab_courier.pack(expand=1,fill='both')

        try:
            lab_courier.configure(font=('Courier', 10))
        except:
            try:
                lab_courier.configure(font=('TkFixedFont', 10))
            except:
                pass

        def file_cascade_post():
            self.file_cascade.delete(0,'end')
            if self.main_window_active:
                item_actions_state=('disabled','normal')[self.sel_item is not None]
                self.file_cascade.add_command(label = 'Scan ...',command = self.scan_dialog_show, accelerator="S")
                self.file_cascade.add_separator()
                self.file_cascade.add_command(label = 'Settings ...',command=self.settings_dialog.show, accelerator="F2")
                self.file_cascade.add_separator()
                self.file_cascade.add_command(label = 'Remove empty folders in specified directory ...',command=self.empty_folder_remove_ask)
                self.file_cascade.add_separator()
                self.file_cascade.add_command(label = 'Erase CRC Cache',command = self.cache_clean)
                self.file_cascade.add_separator()
                self.file_cascade.add_command(label = 'Exit',command = self.exit)

        self.file_cascade= Menu(self.menubar,tearoff=0,bg=self.bg_color,postcommand=file_cascade_post)
        self.menubar.add_cascade(label = 'File',menu = self.file_cascade,accelerator="Alt+F")

        def navi_cascade_post():
            self.navi_cascade.delete(0,'end')
            if self.main_window_active:
                item_actions_state=('disabled','normal')[self.sel_item is not None]
                self.navi_cascade.add_command(label = 'Go to dominant group (by size sum)',command = lambda : self.goto_max_group(1), accelerator="F7",state=item_actions_state)
                self.navi_cascade.add_command(label = 'Go to dominant group (by quantity)',command = lambda : self.goto_max_group(0), accelerator="F8",state=item_actions_state)
                self.navi_cascade.add_separator()
                self.navi_cascade.add_command(label = 'Go to dominant folder (by size sum)',command = lambda : self.goto_max_folder(1),accelerator="F5",state=item_actions_state)
                self.navi_cascade.add_command(label = 'Go to dominant folder (by quantity)',command = lambda : self.goto_max_folder(0), accelerator="F6",state=item_actions_state)
                self.navi_cascade.add_separator()
                self.navi_cascade.add_command(label = 'Go to next marked file'       ,command = lambda : self.goto_next_mark_menu(1,0),accelerator="Right",state=item_actions_state)
                self.navi_cascade.add_command(label = 'Go to previous marked file'   ,command = lambda : self.goto_next_mark_menu(-1,0), accelerator="Left",state=item_actions_state)
                self.navi_cascade.add_separator()
                self.navi_cascade.add_command(label = 'Go to next not marked file'       ,command = lambda : self.goto_next_mark_menu(1,1),accelerator="Shift+Right",state=item_actions_state)
                self.navi_cascade.add_command(label = 'Go to previous not marked file'   ,command = lambda : self.goto_next_mark_menu(-1,1), accelerator="Shift+Left",state=item_actions_state)

                #self.navi_cascade.add_separator()
                #self.navi_cascade.add_command(label = 'Go to dominant folder (by duplicates/other files size ratio)',command = lambda : self.goto_max_folder(1,1),accelerator="Backspace",state=item_actions_state)
                #self.navi_cascade.add_command(label = 'Go to dominant folder (by duplicates/other files quantity ratio)',command = lambda : self.goto_max_folder(0,1), accelerator="Ctrl+Backspace",state=item_actions_state)

        self.navi_cascade= Menu(self.menubar,tearoff=0,bg=self.bg_color,postcommand=navi_cascade_post)

        self.menubar.add_cascade(label = 'Navigation',menu = self.navi_cascade)

        def help_cascade_post():
            self.help_cascade.delete(0,'end')
            if self.main_window_active:
                self.help_cascade.add_command(label = 'About',command=self.aboout_dialog.show,accelerator="F1")
                self.help_cascade.add_command(label = 'License',command=self.license_dialog.show)
                self.help_cascade.add_separator()
                self.help_cascade.add_command(label = 'Open current Log',command=self.show_log)
                self.help_cascade.add_command(label = 'Open logs directory',command=self.show_logs_dir)
                self.help_cascade.add_separator()
                self.help_cascade.add_command(label = 'Open homepage',command=self.show_homepage)

        self.help_cascade= Menu(self.menubar,tearoff=0,bg=self.bg_color,postcommand=help_cascade_post)

        self.menubar.add_cascade(label = 'Help',menu = self.help_cascade)

        #######################################################################
        self.reset_sels()

        self.REAL_SORT_COLUMN={}
        self.REAL_SORT_COLUMN['path'] = 'path'
        self.REAL_SORT_COLUMN['file'] = 'file'
        self.REAL_SORT_COLUMN['size_h'] = 'size'
        self.REAL_SORT_COLUMN['ctime_h'] = 'ctime'
        self.REAL_SORT_COLUMN['instances_h'] = 'instances'

        #self.folder_tree['columns']=('file','dev','inode','kind','crc','size','size_h','ctime','ctime_h','instances','instances_h')
        self.REAL_SORT_COLUMN_INDEX={}
        self.REAL_SORT_COLUMN_INDEX['path'] = 0
        self.REAL_SORT_COLUMN_INDEX['file'] = 1
        self.REAL_SORT_COLUMN_INDEX['size_h'] = 6
        self.REAL_SORT_COLUMN_INDEX['ctime_h'] = 8
        self.REAL_SORT_COLUMN_INDEX['instances_h'] = 10

        self.REAL_SORT_COLUMN_IS_NUMERIC={}
        self.REAL_SORT_COLUMN_IS_NUMERIC['path'] = False
        self.REAL_SORT_COLUMN_IS_NUMERIC['file'] = False
        self.REAL_SORT_COLUMN_IS_NUMERIC['size_h'] = True
        self.REAL_SORT_COLUMN_IS_NUMERIC['ctime_h'] = True
        self.REAL_SORT_COLUMN_IS_NUMERIC['instances_h'] = True

        self.column_sort_last_params={}
        #colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code

        self.column_sort_last_params[self.groups_tree]=self.column_groups_sort_params_default=('size_h',self.REAL_SORT_COLUMN_INDEX['size_h'],self.REAL_SORT_COLUMN_IS_NUMERIC['size_h'],1,2,1,0)
        self.column_sort_last_params[self.folder_tree]=('file',self.REAL_SORT_COLUMN_INDEX['file'],self.REAL_SORT_COLUMN_IS_NUMERIC['file'],0,0,1,2)

        self.sel_item_of_tree[self.groups_tree]=None
        self.sel_item_of_tree[self.folder_tree]=None

        self.groups_show()

        #######################################################################

        self.groups_tree.bind("<Motion>", self.motion_on_groups_tree)
        self.folder_tree.bind("<Motion>", self.motion_on_folder_tree)

        self.groups_tree.bind("<Leave>", lambda event : self.widget_leave())
        self.folder_tree.bind("<Leave>", lambda event : self.widget_leave())

        #######################################################################

        if paths_to_add:
            for path in paths_to_add:
                if windows and path[-1]==':':
                    path += '\\'
                self.path_to_scan_add(os.path.abspath(path))

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

        self.exclude_regexp_scan.set(self.cfg.get_bool(CFG_KEY_EXCLUDE_REGEXP))

        self.main.update()

        self.scan_dialog_show(run_scan_condition)

        self.main_window_active=True
        self.groups_tree.focus_set()

        self.main.mainloop()
        #######################################################################

    tooltip_show_after_groups=''
    tooltip_show_after_folder=''
    tooltip_show_after_widget=''

    def widget_leave(self):
        self.menubar_unpost()
        self.hide_tooltip()

    def motion_on_widget(self,event,message):
        self.tooltip_show_after_widget = event.widget.after(1, self.show_tooltip_widet(event,message))

    def motion_on_groups_tree(self,event):
        if self.main_window_active:
            self.tooltip_show_after_groups = event.widget.after(1, self.show_tooltip_groups(event))

    def motion_on_folder_tree(self,event):
        if self.main_window_active:
            self.tooltip_show_after_folder = event.widget.after(1, self.show_tooltip_folder(event))

    def show_tooltip_widet(self,event,message):
        self.unschedule_tooltip_widget(event)
        self.menubar_unpost()

        self.tooltip_lab.configure(text=message)

        self.tooltip.deiconify()
        self.tooltip.wm_geometry("+%d+%d" % (event.x_root + 20, event.y_root + 5))

    def show_tooltip_groups(self,event):
        self.unschedule_tooltip_groups(event)
        self.menubar_unpost()

        self.tooltip.wm_geometry("+%d+%d" % (event.x_root + 20, event.y_root + 5))

        tree = event.widget
        col=tree.identify_column(event.x)
        if col:
            colname=tree.column(col,'id')
            if tree.identify("region", event.x, event.y) == 'heading':
                if colname in ('path','size_h','file','instances_h','ctime_h'):
                    self.tooltip_lab.configure(text='Sort by %s' % self.org_label[colname])
                    self.tooltip.deiconify()
                else:
                    self.hide_tooltip()

            elif item := tree.identify('item', event.x, event.y):
                pathnrstr=tree.set(item,'pathnr')
                if col=="#0" :
                    if pathnrstr:
                        pathnr=int(pathnrstr)
                        if tree.set(item,'kind')==FILE:
                            self.tooltip_lab.configure(text='%s - %s' % (self.NUMBERS[pathnr],dude_core.scanned_paths[pathnr]) )
                            self.tooltip.deiconify()

                    else:
                        crc=item
                        self.tooltip_lab.configure(text='CRC: %s' % crc )
                        self.tooltip.deiconify()

                elif col:

                    coldata=tree.set(item,col)

                    #if pathnrstr:
                    #    pathnr=int(pathnrstr)
                    #    path=tree.set(item,'path')
                    #    file=tree.set(item,'file')
                    #    file_path = os.path.abspath(dude_core.get_full_path_scanned(pathnr,path,file))
                    if coldata:
                        self.tooltip_lab.configure(text=coldata)
                        self.tooltip.deiconify()

                    else:
                        self.hide_tooltip()

    def show_tooltip_folder(self,event):
        self.unschedule_tooltip_folder(event)
        self.menubar_unpost()

        self.tooltip.wm_geometry("+%d+%d" % (event.x_root + 20, event.y_root + 5))

        tree = event.widget
        col=tree.identify_column(event.x)
        if col:
            colname=tree.column(col,'id')
            if tree.identify("region", event.x, event.y) == 'heading':
                if colname in ('size_h','file','instances_h','ctime_h'):
                    self.tooltip_lab.configure(text='Sort by %s' % self.org_label[colname])
                    self.tooltip.deiconify()
                else:
                    self.hide_tooltip()
            elif item := tree.identify('item', event.x, event.y):
                #pathnrstr=tree.set(item,'pathnr')

                coldata=''
                kind=tree.set(item,self.kind_index)
                if kind==LINK:
                    coldata='(soft-link)'
                elif kind==DIRLINK:
                    coldata='(directory soft-link)'

                if col=="#0" :
                    pass
                elif col:
                    coldata = coldata + ' ' + tree.set(item,col)

                #islink
                #if pathnrstr:
                #    pathnr=int(pathnrstr)
                #    path=tree.set(item,'path')
                #    file=tree.set(item,'file')
                #    file_path = os.path.abspath(dude_core.get_full_path_scanned(pathnr,path,file))
                if coldata:
                    self.tooltip_lab.configure(text=coldata)
                    self.tooltip.deiconify()
                else:
                    self.hide_tooltip()

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
        self.tooltip.withdraw()

    def status(self,text):
        self.status_line.set(text)
        self.status_line_lab.update()

    menu_state_stack=[]
    def menu_enable(self):
        try:
            self.menu_state_stack.pop()
            if not self.menu_state_stack:
                self.menubar.entryconfig("File", state="normal")
                self.menubar.entryconfig("Navigation", state="normal")
                self.menubar.entryconfig("Help", state="normal")
        except Exception as e:
            logging.error(e)

    def menu_disable(self):
        self.menu_state_stack.append('x')
        self.menubar.entryconfig("File", state="disabled")
        self.menubar.entryconfig("Navigation", state="disabled")
        self.menubar.entryconfig("Help", state="disabled")
        self.menubar.update()

    sel_item_of_tree = {}

    def reset_sels(self):
        self.sel_path_nr = None
        self.sel_path = None
        self.sel_file = None
        self.sel_crc = None
        self.sel_item = None

        self.sel_item_of_tree[self.groups_tree]=None
        self.sel_item_of_tree[self.folder_tree]=None

        self.sel_tree=self.groups_tree

        self.sel_kind = None

    def get_index_tuple_groups_tree(self,item):
        #pathnr,path,file,ctime,dev,inode

        pathnr=int(self.groups_tree.set(item,'pathnr'))
        path=self.groups_tree.set(item,'path')
        file=self.groups_tree.set(item,'file')
        ctime=self.groups_tree.set(item,'ctime')
        dev=self.groups_tree.set(item,'dev')
        inode=self.groups_tree.set(item,'inode')

        return (pathnr,path,file,ctime,dev,inode)

    def delete_window_wrapper(self):
        if self.main_window_active:
            self.exit()

    def exit(self):
        self.main_geometry_store()
        self.splitter_store()
        self.main.destroy()

    def main_geometry_store(self):
        self.cfg.set('main',str(self.main.geometry()),section='geometry')
        self.cfg.write()

    find_result=()
    find_params_changed=True
    find_tree_index=-1

    find_by_tree={}

    def finder_wrapper_show(self):
        tree=self.sel_tree

        self.find_dialog_shown=True

        scope_info = 'Scope: All groups.' if self.sel_tree==self.groups_tree else 'Scope: Selected directory.'

        if tree in self.find_by_tree:
            initialvalue=self.find_by_tree[tree]
        else:
            initialvalue='*'

        #self.find_dialog_on_main.show('Find',scope_info,initial=initialvalue,checkbutton_text='treat as a regular expression',checkbutton_initial=False)
        #self.find_by_tree[tree]=self.find_dialog_on_main.entry.get()

        if self.sel_tree==self.groups_tree:
            self.find_dialog_on_groups.show('Find',scope_info,initial=initialvalue,checkbutton_text='treat as a regular expression',checkbutton_initial=False)
            self.find_by_tree[tree]=self.find_dialog_on_groups.entry.get()
        else:
            self.find_dialog_on_folder.show('Find',scope_info,initial=initialvalue,checkbutton_text='treat as a regular expression',checkbutton_initial=False)
            self.find_by_tree[tree]=self.find_dialog_on_folder.entry.get()

        self.find_dialog_shown=False

        self.set_focus_on_item=True
        tree.focus_set()

    def find_prev_from_dialog(self,expression,use_reg_expr):
        #logging.debug('find_prev_from_dialog %s,%s',expression,use_reg_expr)
        self.find_items(expression,use_reg_expr)
        self.select_find_result(-1)

    def find_prev(self):
        if not self.find_result or self.find_tree!=self.sel_tree:
            self.find_params_changed=True
            self.finder_wrapper_show()
        else:
            self.select_find_result(-1)

    def find_next_from_dialog(self,expression,use_reg_expr):
        #logging.debug('find_next_from_dialog %s,%s',expression,use_reg_expr)
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
            self.cfg.set_bool(CFG_KEY_USE_REG_EXPR,use_reg_expr)
            self.find_result_index=0

    @restore_status_line
    def find_items(self,expression,use_reg_expr):
        self.status('finding ...')

        if self.find_params_changed or self.find_tree != self.sel_tree:
            self.find_tree=self.sel_tree

            items=[]

            if expression:
                if self.sel_tree==self.groups_tree:
                    self.find_tree=self.groups_tree
                    crc_range = self.groups_tree.get_children()

                    try:
                        for crcitem in crc_range:
                            for item in self.groups_tree.get_children(crcitem):
                                fullpath = self.item_full_path(item)
                                if (use_reg_expr and re.search(expression,fullpath)) or (not use_reg_expr and fnmatch.fnmatch(fullpath,expression) ):
                                    items.append(item)
                    except Exception as e:
                        try:
                            self.info_dialog_on_find[self.find_tree].show('Error',str(e))
                        except Exception as e2:
                            print(e2)
                        return
                else:
                    self.find_tree=self.folder_tree
                    try:
                        for item in self.folder_tree.get_children():
                            #if tree.set(item,'kind')==FILE:
                            file=self.folder_tree.set(item,'file')
                            if (use_reg_expr and re.search(expression,file)) or (not use_reg_expr and fnmatch.fnmatch(file,expression) ):
                                items.append(item)
                    except Exception as e:
                        self.info_dialog_on_find[self.find_tree].show('Error',str(e))
                        return
            if items:
                self.find_result=tuple(items)
                self.find_params_changed=False
            else:
                scope_info = 'Scope: All groups.' if self.find_tree==self.groups_tree else 'Scope: Selected directory.'
                self.info_dialog_on_find[self.find_tree].show(scope_info,'No files found.')

    def select_find_result(self,mod):
        if self.find_result:
            items_len=len(self.find_result)
            self.find_result_index+=mod
            next_item=self.find_result[self.find_result_index%items_len]

            self.find_tree.focus(next_item)

            if self.find_dialog_shown:
                #focus is still on find dialog
                self.find_tree.selection_set(next_item)
            else:
                self.find_tree.focus_set()

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
        for item in items:
            if tree.set(item,'kind')==FILE:
                self.invert_mark(item, self.groups_tree)
                try:
                    self.folder_tree.item(item,tags=self.groups_tree.item(item)['tags'])
                except Exception :
                    pass
            elif tree.set(item,'kind')==CRC:
                self.tag_toggle_selected(tree, *tree.get_children(item) )

        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    KEY_DIRECTION={}
    KEY_DIRECTION['Up']=-1
    KEY_DIRECTION['Down']=1
    KEY_DIRECTION['Prior']=-1
    KEY_DIRECTION['Next']=1
    KEY_DIRECTION['Home']=0
    KEY_DIRECTION['End']=-1

    reftuple1=('1','2','3','4','5','6','7')
    reftuple2=('exclam','at','numbersign','dollar','percent','asciicircum','ampersand')

    def goto_next_prev_crc(self,direction):
        pool=self.groups_tree.get_children()
        item=self.groups_tree.focus()

        if pool_len:=len(pool):
            next_item=pool[(pool.index(self.groups_tree.set(item,'crc'))+direction) % pool_len]
            self.crc_select_and_focus(next_item)

    def goto_next_prev_duplicate(self,direction):
        pool=[item for item in self.folder_tree.get_children() if self.folder_tree.set(item,'kind')==FILE]
        item=self.folder_tree.focus()

        if pool_len:=len(pool):
            self.goto_next_dupe_file(self.folder_tree,direction)
            self.folder_tree.update()

    def goto_first_last_crc(self,index):
        if next_item:=self.groups_tree.get_children()[index]:
            self.crc_select_and_focus(next_item,True)

    def goto_first_last_dir_entry(self,index):
        if next_item:=self.folder_tree.get_children()[index]:
            self.folder_tree.see(next_item)
            self.folder_tree.focus(next_item)
            self.folder_tree_sel_change(next_item)
            self.folder_tree.update()

    def key_press(self,event):
        self.hide_tooltip()
        self.menubar_unpost()
        self.popup_groups.unpost()
        self.popup_folder.unpost()

        if not self.main_window_active:
            return

        self.main.unbind_class('Treeview','<KeyPress>')

        try:
            tree=event.widget
            item=tree.focus()
            key=event.keysym
            if sel:=tree.selection() : tree.selection_remove(sel)

            if key in ("Up",'Down') :
                try:
                    if tree==self.groups_tree:
                        (pool,pool_len) = (self.tree_groups_flat_items,len(self.tree_groups_flat_items) )
                    else:
                        (pool,pool_len) = (self.folder_tree_flat_items_list,len(self.folder_tree_flat_items_list))

                    if pool_len:
                        index = pool.index(self.sel_item) if self.sel_item in pool else pool.index(self.sel_item_of_tree[tree]) if self.sel_item_of_tree[tree] in pool else pool.index(item) if item in  pool else 0
                        index=(index+self.KEY_DIRECTION[key])%pool_len
                        next_item=pool[index]

                        tree.focus(next_item)
                        tree.see(next_item)

                        if tree==self.groups_tree:
                            self.groups_tree_sel_change(next_item)
                        else:
                            self.folder_tree_sel_change(next_item)
                except Exception as e:
                    logging.error(e)
                    print('pool:',pool,' pool_len:',pool_len)
                    self.info_dialog_on_main.show('INTERNAL ERROR - Updown',str(e) + '\ntree:' + str(tree) + '\nindex:' + str(index) + '\nnext_item:' + str(next_item))

            elif key in ("Prior","Next"):
                if tree==self.groups_tree:
                    self.goto_next_prev_crc(self.KEY_DIRECTION[key])
                else:
                    self.goto_next_prev_duplicate(self.KEY_DIRECTION[key])
            elif key in ("Home","End"):
                if tree==self.groups_tree:
                    self.goto_first_last_crc(self.KEY_DIRECTION[key])
                else:
                    self.goto_first_last_dir_entry(self.KEY_DIRECTION[key])
            elif key == "space":
                if tree==self.groups_tree:
                    if tree.set(item,'kind')==CRC:
                        self.tag_toggle_selected(tree,*tree.get_children(item))
                    else:
                        self.tag_toggle_selected(tree,item)
                else:
                    self.tag_toggle_selected(tree,item)
            elif key == "Tab":
                tree.selection_set(tree.focus())
                self.set_focus_on_item=True
            elif key in ('KP_Multiply','asterisk'):
                self.mark_on_all(self.invert_mark)
            elif key=='Return':
                item=tree.focus()
                if item:
                    self.tree_action(tree,item)
            else:
                event_str=str(event)

                ctrl_pressed = 'Control' in event_str
                shift_pressed = 'Shift' in event_str

                if key=='F3':
                    if shift_pressed:
                        self.find_prev()
                    else:
                        self.find_next()
                elif key == "Right":
                    self.goto_next_mark(event.widget,1,shift_pressed)
                elif key == "Left":
                    self.goto_next_mark(event.widget,-1,shift_pressed)
                elif key in ('KP_Add','plus'):
                    self.mark_expression(self.set_mark,'Mark files',ctrl_pressed)
                elif key in ('KP_Subtract','minus'):
                    self.mark_expression(self.unset_mark,'Unmark files',ctrl_pressed)
                elif key == "Delete":
                    if tree==self.groups_tree:
                        self.process_files_in_groups_wrapper(DELETE,ctrl_pressed)
                    else:
                        self.process_files_in_folder_wrapper(DELETE,self.sel_kind in (DIR,DIRLINK))
                elif key == "Insert":
                    if tree==self.groups_tree:
                        self.process_files_in_groups_wrapper((SOFTLINK,HARDLINK)[shift_pressed],ctrl_pressed)
                    else:
                        self.process_files_in_folder_wrapper((SOFTLINK,HARDLINK)[shift_pressed],self.sel_kind in (DIR,DIRLINK))
                elif key=='F5':
                    self.goto_max_folder(0,-1 if shift_pressed else 1)
                elif key=='F6':
                    self.goto_max_folder(1,-1 if shift_pressed else 1)
                elif key=='F7':
                    self.goto_max_group(0,-1 if shift_pressed else 1)
                elif key=='F8':
                    self.goto_max_group(1,-1 if shift_pressed else 1)
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
                    self.mark_subpath(self.set_mark,True)
                elif key=='question':
                    self.mark_subpath(self.unset_mark,True)
                elif key in ('f','F'):
                    self.finder_wrapper_show()
        except Exception as e:
            logging.error(e)
            self.info_dialog_on_main.show('INTERNAL ERROR',str(e))

        self.main.bind_class('Treeview','<KeyPress>', self.key_press )

    def go_to_parent_dir(self):
        if self.sel_path_full :
            if self.two_dots_condition():
                self.folder_tree.focus_set()
                head,tail=os.path.split(self.sel_path_full)
                self.enter_dir(os.path.normpath(str(pathlib.Path(self.sel_path_full).parent.absolute())),tail)

#################################################
    def crc_select_and_focus(self,crc,try_to_show_all=False):
        self.groups_tree.focus_set()

        if try_to_show_all:
            self.groups_tree.see(self.groups_tree.get_children(crc)[-1])
            self.groups_tree.update()

        self.groups_tree.see(crc)
        self.groups_tree.focus(crc)
        self.groups_tree.update()
        self.groups_tree_sel_change(crc)

    def tree_on_mouse_button_press(self,event,toggle=False):
        self.menubar_unpost()
        self.hide_tooltip()
        self.popup_groups.unpost()
        self.popup_folder.unpost()

        if not self.main_window_active:
            return

        tree=event.widget

        if tree.identify("region", event.x, event.y) == 'heading':
            if (colname:=tree.column(tree.identify_column(event.x),'id') ) in self.REAL_SORT_COLUMN:
                self.column_sort_click(tree,colname)

                #if self.sel_kind==FILE:
                #    tree.focus_set()

                #    tree.focus(self.sel_item)
                #    tree.see(self.sel_item)

                #    if tree==self.groups_tree:
                #        self.groups_tree_sel_change(self.sel_item)
                #    else:
                #        self.folder_tree_sel_change(self.sel_item)

        elif item:=tree.identify('item',event.x,event.y):
            tree.selection_remove(tree.selection())

            tree.focus_set()
            tree.focus(item)

            if tree==self.groups_tree:
                self.groups_tree_sel_change(item)
            else:
                self.folder_tree_sel_change(item)

            if toggle:
                self.tag_toggle_selected(tree,item)

    set_focus_on_item=False
    def tree_on_focus_in(self,event):
        self.sel_tree=tree=event.widget

        if tree==self.folder_tree:
            if len(self.folder_tree.get_children())==0:
                self.groups_tree.focus_set()
                return

        self.tree_with_focus=tree
        tree.configure(style='semi_focus.Treeview')
        self.other_tree[tree].configure(style='default.Treeview')

        item=None

        if sel:=tree.selection():
            tree.selection_remove(sel)
            item=sel[0]

        if self.set_focus_on_item:
            self.set_focus_on_item=False

            if not item:
                item=tree.focus()

            if tree==self.groups_tree:
                if not item:
                    item = self.tree_groups_flat_items[0]

            else:
                if not item:
                    if items := self.folder_tree.get_children():
                        item=items[0]

            if item:
                tree.focus(item)
                tree.see(item)

            if tree==self.groups_tree:
                self.groups_tree_sel_change(item,True)
            else:
                self.folder_tree_sel_change(item)

    def tree_focus_out(self,event):
        tree=event.widget
        tree.selection_set(tree.focus())
        tree.configure(style='semi_focus_off.Treeview')

    def set_full_path_to_file_win(self):
        self.sel_full_path_to_file=pathlib.Path(os.sep.join([self.sel_path_full,self.sel_file])) if self.sel_path_full and self.sel_file else None

    def set_full_path_to_file_lin(self):
        self.sel_full_path_to_file=(self.sel_path_full+self.sel_file if self.sel_path_full=='/' else os.sep.join([self.sel_path_full,self.sel_file])) if self.sel_path_full and self.sel_file else None

    set_full_path_to_file = set_full_path_to_file_win if windows else set_full_path_to_file_lin

    def sel_path_set(self,path):
        if self.sel_path_full != path:
            self.sel_path_full = path
            self.status_var_path.set(self.sel_path_full)

            self.dominant_groups_folder[0] = -1
            self.dominant_groups_folder[1] = -1

    @catched
    def groups_tree_sel_change(self,item,force=False,change_status_line=True):
        if change_status_line :
            self.status('')

        pathnr=self.groups_tree.set(item,'pathnr')
        path=self.groups_tree.set(item,'path')

        self.sel_file = self.groups_tree.set(item,'file')
        new_crc = self.groups_tree.set(item,'crc')

        if self.sel_crc != new_crc:
            self.sel_crc = new_crc

            self.dominant_groups_index[0] = -1
            self.dominant_groups_index[1] = -1

        self.sel_item = item
        self.sel_item_of_tree[self.groups_tree]=item
        #sel_tree=self.groups_tree

        size = int(self.groups_tree.set(item,'size'))

        if path!=self.sel_path or pathnr!=self.sel_path_nr or force:
            self.sel_path_nr = pathnr

            if self.find_tree_index==1:
                self.find_result=()

            if pathnr: #non crc node
                self.sel_path = path
                self.sel_path_set(dude_core.scanned_paths[int(pathnr)]+self.sel_path)
            else :
                self.sel_path = None
                self.sel_path_set(None)
            self.set_full_path_to_file()

        self.sel_kind = self.groups_tree.set(item,'kind')
        if self.sel_kind==FILE:
            self.tree_folder_update()
        else:
            self.tree_folder_update_none()

    @catched
    def folder_tree_sel_change(self,item,change_status_line=True):
        self.sel_file = self.folder_tree.set(item,'file')
        self.sel_crc = self.folder_tree.set(item,'crc')
        self.sel_kind = self.folder_tree.set(item,'kind')
        self.sel_item = item
        self.sel_item_of_tree[self.folder_tree] = item
        #self.sel_tree=self.folder_tree

        self.set_full_path_to_file()

        kind=self.folder_tree.set(item,'kind')
        if kind==FILE:
            if change_status_line: self.status('')
            self.groups_tree_update(item)
        else:
            if kind==LINK:
                if change_status_line: self.status('  %s  %s' % (FILE_LINK_RIGHT,os.readlink(self.sel_full_path_to_file)) )
            elif kind==SINGLEHARDLINKED:
                if change_status_line: self.status('File with hardlinks')
            elif kind==SINGLE:
                if change_status_line: self.status('')
            elif kind in (DIR,DIRLINK):
                if change_status_line: self.status('Subdirectory')
            elif kind==UPDIR:
                if change_status_line: self.status('Parent directory')

            self.groups_tree_update_none()

    def menubar_unpost(self):
        try:
            self.menubar.unpost()
        except Exception as e:
            logging.error(e)

    def context_menu_show(self,event):
        tree=event.widget

        if tree.identify("region", event.x, event.y) == 'heading':
            return

        if not self.main_window_active:
            return

        tree.focus_set()
        self.tree_on_mouse_button_press(event)
        tree.update()

        item_actions_state=('disabled','normal')[self.sel_item is not None]

        pop=self.popup_groups if tree==self.groups_tree else self.popup_folder

        pop.delete(0,'end')

        duplicate_file_actions_state=('disabled',item_actions_state)[self.sel_kind==FILE]
        file_actions_state=('disabled',item_actions_state)[self.sel_kind in (FILE,SINGLE,SINGLEHARDLINKED) ]
        file_or_dir_actions_state=('disabled',item_actions_state)[self.sel_kind in (FILE,SINGLE,SINGLEHARDLINKED,DIR,DIRLINK,UPDIR) ]

        parent_dir_state = ('disabled','normal')[self.two_dots_condition() and self.sel_kind!=CRC]

        if tree==self.groups_tree:
            c_local = Menu(pop,tearoff=0,bg=self.bg_color)
            c_local.add_command(label = "Toggle Mark",  command = lambda : self.tag_toggle_selected(tree,self.sel_item),accelerator="space")
            c_local.add_separator()
            c_local.add_command(label = "Mark all files",        command = lambda : self.mark_in_group(self.set_mark),accelerator="A")
            c_local.add_command(label = "Unmark all files",        command = lambda : self.mark_in_group(self.unset_mark),accelerator="N")
            c_local.add_separator()
            c_local.add_command(label = 'Mark By expression ...',command = lambda : self.mark_expression(self.set_mark,'Mark files',False),accelerator="+")
            c_local.add_command(label = 'Unmark By expression ...',command = lambda : self.mark_expression(self.unset_mark,'Unmark files',False),accelerator="-")
            c_local.add_separator()
            c_local.add_command(label = "Toggle mark on oldest file",     command = lambda : self.mark_in_group_by_ctime('oldest',self.invert_mark),accelerator="O")
            c_local.add_command(label = "Toggle mark on youngest file",   command = lambda : self.mark_in_group_by_ctime('youngest',self.invert_mark),accelerator="Y")
            c_local.add_separator()
            c_local.add_command(label = "Invert marks",   command = lambda : self.mark_in_group(self.invert_mark),accelerator="I")
            c_local.add_separator()

            mark_cascade_path = Menu(c_local, tearoff = 0,bg=self.bg_color)
            unmark_cascade_path = Menu(c_local, tearoff = 0,bg=self.bg_color)

            row=0
            for path in dude_core.scanned_paths:
                mark_cascade_path.add_command(label = self.NUMBERS[row] + '  =  ' + path,    command  = lambda pathpar=path: self.action_on_path(pathpar,self.set_mark,False),accelerator=str(row+1)  )
                unmark_cascade_path.add_command(label = self.NUMBERS[row] + '  =  ' + path,  command  = lambda pathpar=path: self.action_on_path(pathpar,self.unset_mark,False),accelerator="Shift+"+str(row+1)  )
                row+=1

            c_local.add_command(label = "Mark on specified directory ...",   command = lambda : self.mark_subpath(self.set_mark,False))
            c_local.add_command(label = "Unmark on specified directory ...",   command = lambda : self.mark_subpath(self.unset_mark,False))
            c_local.add_separator()

            c_local.add_cascade(label = "Mark on scan path",             menu = mark_cascade_path)
            c_local.add_cascade(label = "Unmark on scan path",             menu = unmark_cascade_path)
            c_local.add_separator()

            marks_state=('disabled','normal')[len(tree.tag_has(MARK))!=0]

            c_local.add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(DELETE,0),accelerator="Delete",state=marks_state)
            c_local.entryconfig(19,foreground='red',activeforeground='red')
            c_local.add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(SOFTLINK,0),accelerator="Insert",state=marks_state)
            c_local.entryconfig(20,foreground='red',activeforeground='red')
            c_local.add_command(label = 'Hardlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(HARDLINK,0),accelerator="Shift+Insert",state=marks_state)
            c_local.entryconfig(21,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'Local (this CRC group)',menu = c_local,state=item_actions_state)
            pop.add_separator()

            c_all = Menu(pop,tearoff=0,bg=self.bg_color)

            c_all.add_command(label = "Mark all files",        command = lambda : self.mark_on_all(self.set_mark),accelerator="Ctrl+A")
            c_all.add_command(label = "Unmark all files",        command = lambda : self.mark_on_all(self.unset_mark),accelerator="Ctrl+N")
            c_all.add_separator()
            c_all.add_command(label = 'Mark By expression ...',command = lambda : self.mark_expression(self.set_mark,'Mark files',True),accelerator="Ctrl+")
            c_all.add_command(label = 'Unmark By expression ...',command = lambda : self.mark_expression(self.unset_mark,'Unmark files',True),accelerator="Ctrl-")
            c_all.add_separator()
            c_all.add_command(label = "Mark Oldest files",     command = lambda : self.mark_all_by_ctime('oldest',self.set_mark),accelerator="Ctrl+O")
            c_all.add_command(label = "Unmark Oldest files",     command = lambda : self.mark_all_by_ctime('oldest',self.unset_mark),accelerator="Ctrl+Shift+O")
            c_all.add_separator()
            c_all.add_command(label = "Mark Youngest files",   command = lambda : self.mark_all_by_ctime('youngest',self.set_mark),accelerator="Ctrl+Y")
            c_all.add_command(label = "Unmark Youngest files",   command = lambda : self.mark_all_by_ctime('youngest',self.unset_mark),accelerator="Ctrl+Shift+Y")
            c_all.add_separator()
            c_all.add_command(label = "Invert marks",   command = lambda : self.mark_on_all(self.invert_mark),accelerator="Ctrl+I, *")
            c_all.add_separator()

            mark_cascade_path = Menu(c_all, tearoff = 0,bg=self.bg_color)
            unmark_cascade_path = Menu(c_all, tearoff = 0,bg=self.bg_color)

            row=0
            for path in dude_core.scanned_paths:
                mark_cascade_path.add_command(label = self.NUMBERS[row] + '  =  ' + path,    command  = lambda pathpar=path: self.action_on_path(pathpar,self.set_mark,True) ,accelerator="Ctrl+"+str(row+1) )
                unmark_cascade_path.add_command(label = self.NUMBERS[row] + '  =  ' + path,  command  = lambda pathpar=path: self.action_on_path(pathpar,self.unset_mark,True) ,accelerator="Ctrl+Shift+"+str(row+1) )
                row+=1

            c_all.add_command(label = "Mark on specified directory ...",   command = lambda : self.mark_subpath(self.set_mark,True))
            c_all.add_command(label = "Unmark on specified directory ...",   command = lambda : self.mark_subpath(self.unset_mark,True))
            c_all.add_separator()

            c_all.add_cascade(label = "Mark on scan path",             menu = mark_cascade_path)
            c_all.add_cascade(label = "Unmark on scan path",             menu = unmark_cascade_path)
            c_all.add_separator()

            c_all.add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(DELETE,1),accelerator="Ctrl+Delete",state=marks_state)
            c_all.entryconfig(21,foreground='red',activeforeground='red')
            c_all.add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(SOFTLINK,1),accelerator="Ctrl+Insert",state=marks_state)
            c_all.entryconfig(22,foreground='red',activeforeground='red')
            c_all.add_command(label = 'Hardlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(HARDLINK,1),accelerator="Ctrl+Shift+Insert",state=marks_state)
            c_all.entryconfig(23,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'All Files',menu = c_all,state=item_actions_state)

            c_nav = Menu(self.menubar,tearoff=0,bg=self.bg_color)
            c_nav.add_command(label = 'go to dominant group (by size sum)',command = lambda : self.goto_max_group(1), accelerator="F7")
            c_nav.add_command(label = 'go to dominant group (by quantity)',command = lambda : self.goto_max_group(0), accelerator="F8")
            c_nav.add_separator()
            c_nav.add_command(label = 'Go to next marked file'       ,command = lambda : self.goto_next_mark(self.groups_tree,1,0),accelerator="Right",state='normal')
            c_nav.add_command(label = 'Go to previous marked file'   ,command = lambda : self.goto_next_mark(self.groups_tree,-1,0), accelerator="Left",state='normal')
            c_nav.add_separator()
            c_nav.add_command(label = 'Go to next not marked file'       ,command = lambda : self.goto_next_mark(self.groups_tree,1,1),accelerator="Shift+Right",state='normal')
            c_nav.add_command(label = 'Go to previous not marked file'   ,command = lambda : self.goto_next_mark(self.groups_tree,-1,1), accelerator="Shift+Left",state='normal')
            c_nav.add_separator()
            c_nav.add_command(label = 'Go to parent directory'   ,command = self.go_to_parent_dir, accelerator="Backspace",state=parent_dir_state)
            c_nav.add_separator()
            c_nav.add_command(label = 'Go to next crc group'       ,command = lambda : self.goto_next_prev_crc(1),accelerator="Pg Down",state='normal')
            c_nav.add_command(label = 'Go to previous crc group'   ,command = lambda : self.goto_next_prev_crc(-1), accelerator="Pg Up",state='normal')
            c_nav.add_separator()
            c_nav.add_command(label = 'Go to first crc group'       ,command = lambda : self.goto_first_last_crc(0),accelerator="Home",state='normal')
            c_nav.add_command(label = 'Go to last crc group'   ,command = lambda : self.goto_first_last_crc(-1), accelerator="End",state='normal')

        else:
            dir_actions_state=('disabled','normal')[self.sel_kind in (DIR,DIRLINK)]

            c_local = Menu(pop,tearoff=0,bg=self.bg_color)
            c_local.add_command(label = "Toggle Mark",  command = lambda : self.tag_toggle_selected(tree,self.sel_item),accelerator="space",state=duplicate_file_actions_state)
            c_local.add_separator()
            c_local.add_command(label = "Mark all files",        command = lambda : self.mark_in_folder(self.set_mark),accelerator="A",state=duplicate_file_actions_state)
            c_local.add_command(label = "Unmark all files",        command = lambda : self.mark_in_folder(self.unset_mark),accelerator="N",state=duplicate_file_actions_state)
            c_local.add_separator()
            c_local.add_command(label = 'Mark By expression',command = lambda : self.mark_expression(self.set_mark,'Mark files'),accelerator="+")
            c_local.add_command(label = 'Unmark By expression',command = lambda : self.mark_expression(self.unset_mark,'Unmark files'),accelerator="-")
            c_local.add_separator()

            marks_state=('disabled','normal')[len(tree.tag_has(MARK))!=0]

            c_local.add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_folder_wrapper(DELETE,0),accelerator="Delete",state=marks_state)
            c_local.add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_folder_wrapper(SOFTLINK,0),accelerator="Insert",state=marks_state)
            #c_local.add_command(label = 'Hardlink Marked Files',command=lambda : self.process_files_in_folder_wrapper(HARDLINK,0),accelerator="Shift+Insert",state=marks_state)

            c_local.entryconfig(8,foreground='red',activeforeground='red')
            c_local.entryconfig(9,foreground='red',activeforeground='red')
            #c_local.entryconfig(10,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'Local (this folder)',menu = c_local,state=item_actions_state)
            pop.add_separator()

            c_sel_sub = Menu(pop,tearoff=0,bg=self.bg_color)
            c_sel_sub.add_command(label = "Mark All Duplicates in Subdirectory",  command = lambda : self.sel_dir(self.set_mark),accelerator="D",state=dir_actions_state)
            c_sel_sub.add_command(label = "Unmark All Duplicates in Subdirectory",  command = lambda : self.sel_dir(self.unset_mark),accelerator="Shift+D",state=dir_actions_state)
            c_sel_sub.add_separator()

            c_sel_sub.add_command(label = 'Remove Marked Files in Subdirectory Tree ...',command=lambda : self.process_files_in_folder_wrapper(DELETE,True),accelerator="Delete",state=dir_actions_state)
            c_sel_sub.add_command(label = 'Softlink Marked Files in Subdirectory Tree ...',command=lambda : self.process_files_in_folder_wrapper(SOFTLINK,True),accelerator="Insert",state=dir_actions_state)
            #c_sel_sub.add_command(label = 'Hardlink Marked Files in Subdirectory Tree',command=lambda : self.process_files_in_folder_wrapper(HARDLINK,True),accelerator="Shift+Insert",state=dir_actions_state)

            c_sel_sub.entryconfig(3,foreground='red',activeforeground='red')
            c_sel_sub.entryconfig(4,foreground='red',activeforeground='red')
            #c_sel_sub.entryconfig(5,foreground='red',activeforeground='red')
            #c_sel_sub.add_separator()
            #c_sel_sub.add_command(label = 'Remove Empty Folders in Subdirectory Tree',command=lambda : self.RemoveEmptyFolders(),state=dir_actions_state)

            pop.add_cascade(label = 'Selected Subdirectory',menu = c_sel_sub,state=dir_actions_state)

            c_nav = Menu(pop,tearoff=0,bg=self.bg_color)
            c_nav.add_command(label = 'go to dominant folder (by size sum)',command = lambda : self.goto_max_folder(1),accelerator="F5")
            c_nav.add_command(label = 'go to dominant folder (by quantity)',command = lambda : self.goto_max_folder(0) ,accelerator="F6")
            c_nav.add_separator()
            c_nav.add_command(label = 'Go to next marked file'       ,command = lambda : self.goto_next_mark(self.folder_tree,1,0),accelerator="Right",state='normal')
            c_nav.add_command(label = 'Go to previous marked file'   ,command = lambda : self.goto_next_mark(self.folder_tree,-1,0), accelerator="Left",state='normal')
            c_nav.add_separator()
            c_nav.add_command(label = 'Go to next not marked file'       ,command = lambda : self.goto_next_mark(self.folder_tree,1,1),accelerator="Shift+Right",state='normal')
            c_nav.add_command(label = 'Go to previous not marked file'   ,command = lambda : self.goto_next_mark(self.folder_tree,-1,1), accelerator="Shift+Left",state='normal')
            c_nav.add_separator()
            c_nav.add_command(label = 'Go to parent directory'       ,command = self.go_to_parent_dir, accelerator="Backspace",state=parent_dir_state)
            c_nav.add_separator()
            c_nav.add_command(label = 'Go to next duplicate'       ,command = lambda : self.goto_next_prev_duplicate(1),accelerator="Pg Down",state='normal')
            c_nav.add_command(label = 'Go to previous duplicate'   ,command = lambda : self.goto_next_prev_duplicate(-1), accelerator="Pg Up",state='normal')
            c_nav.add_separator()
            c_nav.add_command(label = 'Go to first entry'       ,command = lambda : self.goto_first_last_dir_entry(0),accelerator="Home",state='normal')
            c_nav.add_command(label = 'Go to last entry'   ,command = lambda : self.goto_first_last_dir_entry(-1), accelerator="End",state='normal')

            #c_nav.add_separator()
            #c_nav.add_command(label = 'Go to dominant folder (by duplicates/other files size ratio)',command = lambda : self.goto_max_folder(1,1),accelerator="Backspace")
            #c_nav.add_command(label = 'Go to dominant folder (by duplicates/other files quantity ratio)',command = lambda : self.goto_max_folder(0,1) ,accelerator="Ctrl+Backspace")

        pop.add_separator()
        pop.add_cascade(label = 'Navigation',menu = c_nav,state=item_actions_state)

        pop.add_separator()
        pop.add_command(label = 'Open File',command = self.open_file,accelerator="Return",state=file_actions_state)
        pop.add_command(label = 'Open Folder',command = self.open_folder,state=file_or_dir_actions_state)

        pop.add_separator()
        pop.add_command(label = 'Scan ...',  command = self.scan_dialog_show,accelerator='S')
        pop.add_command(label = 'Settings ...',  command = self.settings_dialog.show,accelerator='F2')
        pop.add_separator()
        pop.add_command(label = 'Copy full path',command = self.clip_copy_full_path_with_file,accelerator='Ctrl+C',state = 'normal' if (self.sel_kind and self.sel_kind!=CRC) else 'disabled')
        #pop.add_command(label = 'Copy only path',command = self.clip_copy_full,accelerator="C",state = 'normal' if self.sel_item!=None else 'disabled')
        pop.add_separator()
        pop.add_command(label = 'Find ...',command = self.finder_wrapper_show,accelerator="F",state = 'normal' if self.sel_item is not None else 'disabled')
        pop.add_command(label = 'Find next',command = self.find_next,accelerator="F3",state = 'normal' if self.sel_item is not None else 'disabled')
        pop.add_command(label = 'Find prev',command = self.find_prev,accelerator="Shift+F3",state = 'normal' if self.sel_item is not None else 'disabled')
        pop.add_separator()

        pop.add_command(label = "Exit",  command = self.exit)

        try:
            pop.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            print(e)

        pop.grab_release()

    def empty_folder_remove_ask(self):
        if res:=askdirectory(title='Select Directory',initialdir=self.cwd,parent=self.main):
            final_info = self.empty_dirs_removal(res,True)

            self.text_info_dialog.show('Removed empty directories','\n'.join(final_info))

            self.tree_folder_update(self.sel_path_full)

    def sel_dir(self,action):
        self.action_on_path(self.sel_full_path_to_file,action,True)

    def column_sort_click(self, tree, colname):
        prev_colname,prev_sort_index,prev_is_numeric,prev_reverse,prev_updir_code,prev_dir_code,prev_non_dir_code=self.column_sort_last_params[tree]
        reverse = not prev_reverse if colname == prev_colname else prev_reverse
        tree.heading(prev_colname, text=self.org_label[prev_colname])

        updir_code,dir_code,non_dir_code = (2,1,0) if reverse else (0,1,2)

        sort_index=self.REAL_SORT_COLUMN_INDEX[colname]
        is_numeric=self.REAL_SORT_COLUMN_IS_NUMERIC[colname]
        self.column_sort_last_params[tree]=(colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code)

        if tree == self.folder_tree:
            self.folder_items_cache={}

        self.column_sort(tree)

    def tree_sort_item(self,tree,parent_item,lower_tree):
        colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[tree]

        real_column_to_sort=self.REAL_SORT_COLUMN[colname]

        tlist=[]
        for item in (tree.get_children(parent_item) if parent_item else tree.get_children(parent_item)):
            sortval_org=tree.set(item,real_column_to_sort)
            sortval=(int(sortval_org) if sortval_org.isdigit() else 0) if is_numeric else sortval_org

            if lower_tree:
                kind = tree.set(item,'kind')
                code=updir_code if kind==UPDIR else dir_code if kind in (DIR,DIRLINK) else non_dir_code
                tlist.append( ( (code,sortval),item) )
            else:
                tlist.append( (sortval,item) )

        tlist.sort(reverse=reverse,key=lambda x: x[0])

        if not parent_item:
            parent_item=''

        _ = {tree.move(item, parent_item, index) for index,(val_tuple,item) in enumerate(sorted(tlist,reverse=reverse,key=lambda x: x[0]) ) }

    @restore_status_line
    @block_main_window
    def column_sort(self, tree):
        self.status('Sorting...')
        colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[tree]

        self.column_sort_set_arrow(tree)

        if tree==self.groups_tree:
            if colname in ('path','file','ctime_h'):
                for crc in tree.get_children():
                    self.tree_sort_item(tree,crc,False)
            else:
                self.tree_sort_item(tree,None,False)

            self.tree_groups_flat_items_update()
        else:
            self.tree_sort_item(tree,None,True)

        tree.update()

    def column_sort_set_arrow(self, tree):
        colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[tree]
        tree.heading(colname, text=self.org_label[colname] + ' ' + str('\u25BC' if reverse else '\u25B2') )

    def path_to_scan_add(self,path):
        if len(self.paths_to_scan_from_dialog)<10:
            self.paths_to_scan_from_dialog.append(path)
            self.paths_to_scan_update()
        else:
            logging.error('can\'t add:%s. limit exceeded',path)

    def scan_from_button(self):
        if self.scan():
            self.scan_dialog_hide_wrapper()

    def scan_dialog_hide_wrapper(self):
        self.scan_dialog.hide()

    @restore_status_line
    def scan(self):
        self.status('Scanning...')
        self.cfg.write()

        dude_core.reset()
        self.status_var_path.set('')
        self.groups_show()

        paths_to_scan_from_entry = [var.get() for var in self.paths_to_scan_entry_var.values()]
        exclude_from_entry = [var.get() for var in self.exclude_entry_var.values()]

        if res:=dude_core.set_exclude_masks(self.cfg.get_bool(CFG_KEY_EXCLUDE_REGEXP),exclude_from_entry):
            self.info_dialog_on_scan.show('Error. Fix expression.',res)
            return False
        self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(exclude_from_entry))

        if not paths_to_scan_from_entry:
            self.info_dialog_on_scan.show('Error. No paths to scan.','Add paths to scan.')
            return False

        if res:=dude_core.set_paths_to_scan(paths_to_scan_from_entry):
            self.info_dialog_on_scan.show('Error. Fix paths selection.',res)
            return False

        self.main.update()

        #############################

        self.progress_dialog_show(self.scan_dialog.area_main,'Scanning',abort_tooltip='If you abort at this stage,\nyou will not get any results.')
        self.scan_dialog.set_external_can_check(self.progress_dialog_ended)

        scan_thread=Thread(target=dude_core.scan,daemon=True)
        scan_thread.start()

        while scan_thread.is_alive():
            self.progress_dialog_update(self.NUMBERS[dude_core.info_path_nr] + '\n' + dude_core.info_path_to_scan + '\n\n' + str(dude_core.info_counter) + '\n' + core.bytes_to_str(dude_core.info_size_sum))

            if self.action_abort:
                dude_core.abort()
                break

            time.sleep(0.04)

        scan_thread.join()
        self.progress_dialog_end()
        self.scan_dialog.set_external_can_check(None)

        if self.action_abort:
            return False

        #############################
        if dude_core.sum_size==0:
            self.info_dialog_on_scan.show('Cannot Proceed.','No Duplicates.')
            return False
        #############################
        self.status('Calculating CRC ...')
        self.progress_dialog_show(self.scan_dialog.area_main,'CRC calculation','determinate','determinate',progress1_left_text='Total space:',progress2_left_text='Files number:',abort_tooltip='If you abort at this stage,\npartial results may be available if any CRC groups are found.')
        self.scan_dialog.set_external_can_check(self.progress_dialog_ended)

        dude_core.writeLog=self.write_scan_log.get()

        crc_thread=Thread(target=dude_core.crc_calc,daemon=True)
        crc_thread.start()

        self.scan_dialog.widget.config(cursor="watch")

        while crc_thread.is_alive():
            info = ""

            if DEBUG_MODE:
                info =  'Active Threads: ' + dude_core.info_threads \
                    + '\nAvarage speed: ' + core.bytes_to_str(dude_core.info_speed,1) + '/s\n\n'

            info = info + 'Results:' \
                + '\nCRC groups: ' + str(dude_core.info_found_groups) \
                + '\nfolders: ' + str(dude_core.info_found_folders) \
                + '\nspace: ' + core.bytes_to_str(dude_core.info_found_dupe_space)

            info_progress_size=100*dude_core.info_size_done/dude_core.sum_size
            info_progress_quantity=100*dude_core.info_files_done/dude_core.info_total

            progress_size_descr=core.bytes_to_str(dude_core.info_size_done) + '/' + core.bytes_to_str(dude_core.sum_size)
            progress_quant_descr=str(dude_core.info_files_done) + '/' + str(dude_core.info_total)

            self.progress_dialog_update(info,info_progress_size,info_progress_quantity,progress_size_descr,progress_quant_descr,dude_core.info_line)

            if dude_core.can_abort:
                if self.action_abort:
                    dude_core.abort()
            else:
                self.status(dude_core.info)

            time.sleep(0.04)

        self.status('Finishing CRC Thread...')
        crc_thread.join()
        #############################

        self.progress_dialog_end()
        #need to wait for rendering

        self.scan_dialog.set_external_can_check(lambda : False)

        self.groups_show()

        if self.action_abort:
            self.info_dialog_on_scan.show('CRC Calculation aborted.','\nResults are partial.\nSome files may remain unidentified as duplicates.')

        self.scan_dialog.widget.config(cursor="")
        #self.scan_dialog.widget.update()
        #self.scan_dialog.unlock()

        return True

    def scan_dialog_show(self,do_scan=False):
        self.exclude_mask_update()
        self.paths_to_scan_update()

        self.scan_dialog.do_command_after_show=self.scan if do_scan else None

        self.scan_dialog.show()

        if dude_core.scanned_paths:
            self.paths_to_scan_from_dialog=dude_core.scanned_paths.copy()

    def paths_to_scan_update(self) :
        for subframe in self.paths_to_scan_frames:
            subframe.destroy()

        self.paths_to_scan_frames=[]
        self.paths_to_scan_entry_var={}

        row=0
        for path in self.paths_to_scan_from_dialog:
            (frame:=tk.Frame(self.paths_frame,bg=self.bg_color)).grid(row=row,column=0,sticky='news',columnspan=3)
            self.paths_to_scan_frames.append(frame)

            tk.Label(frame,text=' ' + self.NUMBERS[row] + ' ' , relief='groove',bg=self.bg_color).pack(side='left',padx=2,pady=1,fill='y')

            self.paths_to_scan_entry_var[row]=tk.StringVar(value=path)
            ttk.Entry(frame,textvariable=self.paths_to_scan_entry_var[row]).pack(side='left',expand=1,fill='both',pady=1)

            remove_path_button=ttk.Button(frame,text='❌',command=lambda pathpar=path: self.path_to_scan_remove(pathpar),width=3)
            remove_path_button.pack(side='right',padx=2,pady=1,fill='y')

            remove_path_button.bind("<Motion>", lambda event : self.motion_on_widget(event,'Remove path from list.'))
            remove_path_button.bind("<Leave>", lambda event : self.widget_leave())

            row+=1

        if len(self.paths_to_scan_from_dialog)==self.MAX_PATHS:
            self.add_path_button.configure(state='disabled',text='')
            #self.AddDrivesButton.configure(state='disabled',text='')
            self.clear_paths_list_button.focus_set()
        else:
            self.add_path_button.configure(state='normal',text='Add path ...')
            #self.AddDrivesButton.configure(state='normal',text='Add drives ...')

    def exclude_regexp_set(self):
        self.cfg.set_bool(CFG_KEY_EXCLUDE_REGEXP,self.exclude_regexp_scan.get())

    def exclude_mask_update(self) :
        for subframe in self.exclude_frames:
            subframe.destroy()

        self.exclude_frames=[]
        self.exclude_entry_var={}

        row=0

        for entry in self.cfg.get(CFG_KEY_EXCLUDE,'').split('|'):
            if entry:
                (frame:=tk.Frame(self.exclude_frame,bg=self.bg_color)).grid(row=row,column=0,sticky='news',columnspan=3)
                self.exclude_frames.append(frame)

                self.exclude_entry_var[row]=tk.StringVar(value=entry)
                ttk.Entry(frame,textvariable=self.exclude_entry_var[row]).pack(side='left',expand=1,fill='both',pady=1)

                remove_expression_button=ttk.Button(frame,text='❌',command=lambda entrypar=entry: self.exclude_mask_remove(entrypar),width=3)
                remove_expression_button.pack(side='right',padx=2,pady=1,fill='y')

                remove_expression_button.bind("<Motion>", lambda event : self.motion_on_widget(event,'Remove expression from list.'))
                remove_expression_button.bind("<Leave>", lambda event : self.widget_leave())

                row+=1

    #def AddDrives(self):

        #for (device,mountpoint,fstype,opts,maxfile,maxpath) in psutil.disk_partitions():
        #    if fstype != 'squashfs':
        #        self.path_to_scan_add(mountpoint)

    #    if windows:
    #        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    #            if os.path.exists(f'{drive_letter}:'):
    #                self.path_to_scan_add(f'{drive_letter}:')
    #    else:
    #        pass

    def path_to_scan_add_dialog(self):
        if res:=askdirectory(title='Select Directory',initialdir=self.cwd,parent=self.scan_dialog.area_main):
            self.path_to_scan_add(res)

    def exclude_mask_add_dir(self):
        if res:=askdirectory(title='Select Directory',initialdir=self.cwd,parent=self.scan_dialog.area_main):
            expr = res + (".*" if self.exclude_regexp_scan.get() else "*")
            self.exclude_mask_string(expr)

    def exclude_mask_add_dialog(self):
        self.exclude_dialog_on_scan.show('Specify Exclude expression','expression:','')
        confirmed=self.exclude_dialog_on_scan.res_bool
        mask=self.exclude_dialog_on_scan.res_str

        if confirmed:
            self.exclude_mask_string(mask)

    def exclude_mask_string(self,mask):
        orglist=self.cfg.get(CFG_KEY_EXCLUDE,'').split('|')
        orglist.append(mask)
        self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(orglist))
        self.exclude_mask_update()

    def path_to_scan_remove(self,path) :
        self.paths_to_scan_from_dialog.remove(path)
        self.paths_to_scan_update()

    def exclude_mask_remove(self,mask) :
        orglist=self.cfg.get(CFG_KEY_EXCLUDE,'').split('|')
        orglist.remove(mask)
        if '' in orglist:
            orglist.remove('')
        self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(orglist))
        self.exclude_mask_update()

    def splitter_store(self):
        try:
            coords=self.paned.sash_coord(0)
            self.cfg.set('sash_coord',str(coords[1]),section='geometry')
            self.cfg.write()
        except Exception as e:
            logging.error(e)

    def exclude_masks_clear(self):
        self.cfg.set(CFG_KEY_EXCLUDE,'')
        self.exclude_mask_update()

    def scan_paths_clear(self):
        self.paths_to_scan_from_dialog.clear()
        self.paths_to_scan_update()

    def settings_ok(self):
        update1=False
        update2=False

        if self.cfg.get_bool(CFG_KEY_FULL_CRC)!=self.show_full_crc.get():
            self.cfg.set_bool(CFG_KEY_FULL_CRC,self.show_full_crc.get())
            update1=True
            update2=True
            self.folder_items_cache={}

        if self.cfg.get_bool(CFG_KEY_FULL_PATHS)!=self.show_full_paths.get():
            self.cfg.set_bool(CFG_KEY_FULL_PATHS,self.show_full_paths.get())
            update1=True
            update2=True

        if self.cfg.get_bool(CFG_KEY_REL_SYMLINKS)!=self.create_relative_symlinks.get():
            self.cfg.set_bool(CFG_KEY_REL_SYMLINKS,self.create_relative_symlinks.get())

        if self.cfg.get_bool(ERASE_EMPTY_DIRS)!=self.erase_empty_directories.get():
            self.cfg.set_bool(ERASE_EMPTY_DIRS,self.erase_empty_directories.get())

        if self.cfg.get_bool(CFG_ALLOW_DELETE_ALL)!=self.allow_delete_all.get():
            self.cfg.set_bool(CFG_ALLOW_DELETE_ALL,self.allow_delete_all.get())

        if self.cfg.get_bool(CFG_SKIP_INCORRECT_GROUPS)!=self.skip_incorrect_groups.get():
            self.cfg.set_bool(CFG_SKIP_INCORRECT_GROUPS,self.skip_incorrect_groups.get())

        if self.cfg.get_bool(CFG_ALLOW_DELETE_NON_DUPLICATES)!=self.allow_delete_non_duplicates.get():
            self.cfg.set_bool(CFG_ALLOW_DELETE_NON_DUPLICATES,self.allow_delete_non_duplicates.get())

        if self.cfg.get_bool(CFG_CONFIRM_SHOW_CRCSIZE)!=self.confirm_show_crc_and_size.get():
            self.cfg.set_bool(CFG_CONFIRM_SHOW_CRCSIZE,self.confirm_show_crc_and_size.get())

        if self.cfg.get_bool(CFG_CONFIRM_SHOW_LINKSTARGETS)!=self.confirm_show_links_targets.get():
            self.cfg.set_bool(CFG_CONFIRM_SHOW_LINKSTARGETS,self.confirm_show_links_targets.get())

        if self.cfg.get(CFG_KEY_WRAPPER_FILE)!=self.file_open_wrapper.get():
            self.cfg.set(CFG_KEY_WRAPPER_FILE,self.file_open_wrapper.get())

        if self.cfg.get(CFG_KEY_WRAPPER_FOLDERS)!=self.folders_open_wrapper.get():
            self.cfg.set(CFG_KEY_WRAPPER_FOLDERS,self.folders_open_wrapper.get())

        self.cfg.write()

        if update1:
            self.groups_tree_update_crc_and_path()

        if update2:
            if self.sel_crc and self.sel_item and self.sel_path_full:
                self.tree_folder_update()
            else:
                self.tree_folder_update_none()

        self.settings_dialog.hide()

    def settings_reset(self):
        _ = {var.set(cfg_defaults[key]) for var,key in self.settings}
        _ = {var.set(cfg_defaults[key]) for var,key in self.settings_str}

    def crc_node_update(self,crc):
        size=int(self.groups_tree.set(crc,'size'))

        crc_removed=False
        if size not in dude_core.files_of_size_of_crc:
            self.groups_tree.delete(crc)
            logging.debug('crc_node_update-1 %s',crc)
            crc_removed=True
        elif crc not in dude_core.files_of_size_of_crc[size]:
            self.groups_tree.delete(crc)
            logging.debug('crc_node_update-2 %s',crc)
            crc_removed=True
        else:
            crc_dict=dude_core.files_of_size_of_crc[size][crc]
            for item in list(self.groups_tree.get_children(crc)):
                index_tuple=self.get_index_tuple_groups_tree(item)

                if index_tuple not in crc_dict:
                    self.groups_tree.delete(item)
                    logging.debug('crc_node_update-3:%s',item)

            if not self.groups_tree.get_children(crc):
                self.groups_tree.delete(crc)
                logging.debug('crc_node_update-4:%s',crc)
                crc_removed=True

    def data_precalc(self):
        self.status('Precalculating data...')

        self.cache_by_id_ctime = { (self.idfunc(inode,dev),ctime):(crc,dude_core.crc_cut[crc],len(size_dict[crc]) ) for size,size_dict in dude_core.files_of_size_of_crc.items() for crc,crc_dict in size_dict.items() for pathnr,path,file,ctime,dev,inode in crc_dict }
        self.status_var_groups.set(len(self.groups_tree.get_children()))

        path_stat_size={}
        path_stat_quant={}

        self.biggest_file_of_path={}
        self.biggest_file_of_path_id={}

        for size,size_dict in dude_core.files_of_size_of_crc.items() :
            for crc,crc_dict in size_dict.items():
                for pathnr,path,file,ctime,dev,inode in crc_dict:
                    path_index=(pathnr,path)
                    path_stat_size[path_index] = path_stat_size.get(path_index,0) + size
                    path_stat_quant[path_index] = path_stat_quant.get(path_index,0) + 1

                    if size>self.biggest_file_of_path.get(path_index,0):
                        self.biggest_file_of_path[path_index]=size
                        self.biggest_file_of_path_id[path_index]=self.idfunc(inode,dev)

        self.path_stat_list_size=tuple(sorted([(pathnr,path,number) for (pathnr,path),number in path_stat_size.items()],key=lambda x : x[2],reverse=True))
        self.path_stat_list_quant=tuple(sorted([(pathnr,path,number) for (pathnr,path),number in path_stat_quant.items()],key=lambda x : x[2],reverse=True))
        self.groups_combos_size = tuple(sorted([(crcitem,sum([int(self.groups_tree.set(item,'size')) for item in self.groups_tree.get_children(crcitem)])) for crcitem in self.groups_tree.get_children()],key = lambda x : x[1],reverse = True))
        self.groups_combos_quant = tuple(sorted([(crcitem,len(self.groups_tree.get_children(crcitem))) for crcitem in self.groups_tree.get_children()],key = lambda x : x[1],reverse = True))

    def tree_groups_flat_items_update(self):
        self.tree_groups_flat_items = tuple([elem for sublist in [ tuple([crc])+tuple(self.groups_tree.get_children(crc)) for crc in self.groups_tree.get_children() ] for elem in sublist])

    def initial_focus(self):
        if self.groups_tree.get_children():
            first_node_file=next(iter(self.groups_tree.get_children(next(iter(self.groups_tree.get_children())))))
            self.groups_tree.focus_set()
            self.groups_tree.focus(first_node_file)
            self.groups_tree.see(first_node_file)
            self.groups_tree_sel_change(first_node_file)

            self.groups_tree_update_crc_and_path()
        else:
            self.tree_folder_update_none()
            self.reset_sels()


    @block_main_window
    def groups_show(self):
        self.status('Rendering data...')
        self.menu_disable()

        self.idfunc = (lambda i,d : '%s-%s'%(i,d)) if len(dude_core.devs)>1 else (lambda i,d : str(i))

        self.reset_sels()
        self.groups_tree.delete(*self.groups_tree.get_children())

        sizes_counter=0
        for size,size_dict in dude_core.files_of_size_of_crc.items() :
            size_h = core.bytes_to_str(size)
            size_str = core.int_to_str(size)
            if not sizes_counter%64:
                self.status('Rendering data... (%s)' % size_h)

            sizes_counter+=1
            for crc,crc_dict in size_dict.items():
                #self.groups_tree["columns"]=('pathnr','path','file','size','size_h','ctime','dev','inode','crc','instances','instances_h','ctime_h','kind')
                instances_str=core.int_to_str(len(crc_dict))
                crcitem=self.groups_tree.insert(parent='', index='end',iid=crc, values=('','','',size_str,size_h,'','','',crc,instances_str,instances_str,'',CRC),tags=CRC,open=True)

                for pathnr,path,file,ctime,dev,inode in crc_dict:
                    self.groups_tree.insert(parent=crcitem, index='end',iid=self.idfunc(inode,dev), values=(\
                            pathnr,path,file,size_str,\
                            '',\
                            ctime,dev,inode,crc,\
                            '','',\
                            get_htime(ctime) ,FILE),tags=())
        self.data_precalc()

        if self.column_sort_last_params[self.groups_tree]!=self.column_groups_sort_params_default:
            #defaultowo po size juz jest, nie trzeba tracic czasu
            self.column_sort(self.groups_tree)
        else:
            self.column_sort_set_arrow(self.groups_tree)

        self.tree_groups_flat_items_update() #after sort !
        self.initial_focus()
        self.calc_mark_stats_groups()

        self.menu_enable()
        self.status('')

    def groups_tree_update_crc_and_path(self):
        show_full_crc=self.cfg.get_bool(CFG_KEY_FULL_CRC)
        show_full_paths=self.cfg.get_bool(CFG_KEY_FULL_PATHS)

        for size,size_dict in dude_core.files_of_size_of_crc.items() :
            for crc,crc_dict in size_dict.items():
                self.groups_tree.item(crc,text=crc if show_full_crc else dude_core.crc_cut[crc])
                for pathnr,path,file,ctime,dev,inode in crc_dict:
                    self.groups_tree.item(self.idfunc(inode,dev),text=dude_core.scanned_paths[pathnr] if show_full_paths else self.NUMBERS[pathnr])

    def groups_tree_update_none(self):
        self.groups_tree.selection_remove(self.groups_tree.selection())

    def groups_tree_update(self,item):
        self.groups_tree.see(self.sel_crc)
        self.groups_tree.update()

        self.groups_tree.selection_set(item)
        self.groups_tree.see(item)
        self.groups_tree.update()

    def tree_folder_update_none(self):
        self.folder_tree.delete(*self.folder_tree.get_children())
        self.calc_mark_stats_folder()
        self.status_var_folder_size.set('')
        self.status_var_folder_quant.set('')

        self.status_var_path.set('')
        #self.status_var_full_path_label.config(fg = 'black')

    #self.folder_tree['columns']=('file','dev','inode','kind','crc','size','size_h','ctime','ctime_h','instances','instances_h')
    kind_index=3

    def two_dots_condition_win(self):
        return bool(self.sel_path_full.split(os.sep)[1]!='')

    def two_dots_condition_lin(self):
        return bool(self.sel_path_full!='/')

    two_dots_condition = two_dots_condition_win if windows else two_dots_condition_lin

    @block_main_window
    def tree_folder_update(self,arbitrary_path=None):
        current_path=arbitrary_path if arbitrary_path else self.sel_path_full

        if not current_path:
            return False

        scan_dir_tuple=dude_core.set_scan_dir(current_path)
        dir_ctime = scan_dir_tuple[0]
        scan_dir_res = scan_dir_tuple[1]

        if not scan_dir_res:
            self.status(scan_dir_tuple[2])
            return False

        do_refresh=True
        if current_path in self.folder_items_cache:
            if dir_ctime==self.folder_items_cache[current_path][0]:
                do_refresh=False

        if do_refresh :
            folder_items_dict={}

            show_full_crc=self.cfg.get_bool(CFG_KEY_FULL_CRC)

            col_sort,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[self.folder_tree]
            sort_index_local=sort_index-1

            i=0
            sort_val_func = int if is_numeric else lambda x : x

            #preallocate
            keys=[None]*len(scan_dir_res)
            keys.clear()

            for file,islink,isdir,isfile,mtime,ctime,dev,inode,size_num,nlink in scan_dir_res:
                if islink :
                    presort_id = dir_code if isdir else non_dir_code
                    text = '\t📁 %s' % FOLDER_LINK if isdir else '\t  %s' % FILE_LINK_LEFT
                    iid=('%sDL' % i) if isdir else ('%sFL' % i)
                    kind= DIRLINK if isdir else LINK
                    defaulttag = DIR if isdir else LINK
                    crc=''
                    size='0'
                    size_h=''
                    ctime='0'
                    ctime_h=''
                    instances='1'
                    instances_h=''
                    i+=1
                elif isdir:
                    presort_id = dir_code
                    text = '\t📁'
                    iid='%sD' % i
                    kind= DIR
                    defaulttag = DIR
                    crc=''
                    size='0'
                    size_h=''
                    ctime='0'
                    ctime_h=''
                    instances='1'
                    instances_h=''
                    i+=1
                elif isfile:
                    presort_id = non_dir_code
                    file_id=self.idfunc(inode,dev)

                    ctime_h=get_htime(ctime)

                    size=core.int_to_str(size_num)
                    size_h=core.bytes_to_str(size_num)

                    if (file_id,ctime) in self.cache_by_id_ctime:
                        crc,crc_cut,instances_num = self.cache_by_id_ctime[(file_id,ctime)]

                        text = crc if show_full_crc else crc_cut
                        iid=file_id
                        kind=FILE
                        instances_h=instances=core.int_to_str(instances_num)
                        defaulttag=None
                    else:
                        text = '\t ✹(%s)' % nlink if nlink!=1 else ''
                        iid='%sO' % i
                        crc=''
                        kind = SINGLEHARDLINKED if nlink!=1 else SINGLE
                        defaulttag = SINGLE

                        instances='1'
                        instances_h=''
                        i+=1
                else:
                    logging.error('what is it: %s:%s,%s,%s,%s ?',current_path,file,islink,isdir,isfile)
                    continue

                values = (file,dev,inode,kind,crc,size,size_h,ctime,ctime_h,instances,instances_h)

                current_sort_key=(presort_id,sort_val_func(values[sort_index_local]),iid)
                #keys[i]=current_sort_key
                keys += current_sort_key,
                folder_items_dict[iid] = (text,values,defaulttag)

            ############################################################
            self.folder_items_cache[current_path]=(dir_ctime, [ (iid,folder_items_dict[iid]) for presort_id,sort_id,iid in sorted(keys,reverse=reverse) ] )

        if arbitrary_path:
            #TODO - workaround
            sel_path_prev=self.sel_path
            self.reset_sels()
            self.sel_path=sel_path_prev
            self.sel_path_set(str(pathlib.Path(arbitrary_path)))

        self.folder_tree.delete(*self.folder_tree.get_children())

        self.folder_tree_flat_items_list=[None]*(len(self.folder_items_cache[current_path][1])+1)
        self.folder_tree_flat_items_list.clear()

        if self.two_dots_condition():
            #self.folder_tree['columns']=('file','dev','inode','kind','crc','size','size_h','ctime','ctime_h','instances','instances_h')
            self.folder_tree.insert(parent="", index='end', iid='0UP' , text='', values=('..','','',UPDIR,'',0,'',0,'',0,''),tags=DIR)
            self.folder_tree_flat_items_list.append('0UP')

        #preallocate
        try:
            #_ = {self.folder_tree.insert(parent="", index='end', iid=iid , text=text, values=values,tags = self.groups_tree.item(iid)['tags'] if values[self.kind_index]==FILE else defaulttag) for (iid,(text,values,defaulttag)) in self.folder_items_cache[current_path][1]}
            for (iid,(text,values,defaulttag)) in self.folder_items_cache[current_path][1]:
                if values[self.kind_index]==FILE:
                    try:
                        tags = self.groups_tree.item(iid)['tags']
                    except Exception as e:
                        self.status(str(e))
                        logging.error(e)
                        tags = defaulttag
                else:
                    tags = defaulttag

                self.folder_tree.insert(parent="", index='end', iid=iid , text=text, values=values,tags = tags)
                self.folder_tree_flat_items_list.append(iid)

        except Exception as e:
            self.status(str(e))
            logging.error(e)
            self.folder_items_cache={}

        if not arbitrary_path:
            if self.sel_item and self.sel_item in self.folder_tree.get_children():
                self.folder_tree.selection_set(self.sel_item)
                self.folder_tree.see(self.sel_item)

        self.calc_mark_stats_folder()

        return True

    def update_marks_folder(self):
        for item in self.folder_tree.get_children():
            if self.folder_tree.set(item,'kind')==FILE:
                self.folder_tree.item( item,tags=self.groups_tree.item(item)['tags'] )

    def calc_mark_stats_groups(self):
        self.calc_mark_stats_core(self.groups_tree,self.status_var_all_size,self.status_var_all_quant)

    def calc_mark_stats_folder(self):
        self.calc_mark_stats_core(self.folder_tree,self.status_var_folder_size,self.status_var_folder_quant)

    def calc_mark_stats_core(self,tree,var_size,var_quant):
        marked=tree.tag_has(MARK)
        var_quant.set(len(marked))
        var_size.set(core.bytes_to_str(sum(int(tree.set(item,'size')) for item in marked)))

    def mark_in_specified_group_by_ctime(self, action, crc, reverse,select=False):
        item=sorted([ (item,self.groups_tree.set(item,'ctime') ) for item in self.groups_tree.get_children(crc)],key=lambda x : int(x[1]),reverse=reverse)[0][0]
        if item:
            action(item,self.groups_tree)
            if select:
                self.groups_tree.see(item)
                self.groups_tree.focus(item)
                self.groups_tree_sel_change(item)
                self.groups_tree.update()

    @block_main_window
    def mark_all_by_ctime(self,order_str, action):
        self.status('Un/Setting marking on all files ...')
        reverse=1 if order_str=='oldest' else 0

        _ = { self.mark_in_specified_group_by_ctime(action, crc, reverse) for crc in self.groups_tree.get_children() }
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @block_main_window
    def mark_in_group_by_ctime(self,order_str,action):
        self.status('Un/Setting marking in group ...')
        reverse=1 if order_str=='oldest' else 0
        self.mark_in_specified_group_by_ctime(action,self.sel_crc,reverse,True)
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    def mark_in_specified_crc_group(self,action,crc):
        _ = { action(item,self.groups_tree) for item in self.groups_tree.get_children(crc) }

    @block_main_window
    def mark_in_group(self,action):
        self.status('Un/Setting marking in group ...')
        self.mark_in_specified_crc_group(action,self.sel_crc)
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @block_main_window
    def mark_on_all(self,action):
        self.status('Un/Setting marking on all files ...')
        _ = { self.mark_in_specified_crc_group(action,crc) for crc in self.groups_tree.get_children() }
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @block_main_window
    def mark_in_folder(self,action):
        self.status('Un/Setting marking in folder ...')
        _ = { (action(item,self.folder_tree),action(item,self.groups_tree)) for item in self.folder_tree.get_children() if self.folder_tree.set(item,'kind')==FILE }

        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    def set_mark(self,item,tree):
        tree.item(item,tags=[MARK])

    def unset_mark(self,item,tree):
        tree.item(item,tags=())

    def invert_mark(self,item,tree):
        tree.item(item,tags=() if tree.item(item)['tags'] else [MARK])

    @block_main_window
    def action_on_path(self,path_param,action,all_groups=True):
        if all_groups:
            crc_range = self.groups_tree.get_children()
        else :
            crc_range = [str(self.sel_crc)]

        sel_count=0
        for crcitem in crc_range:
            for item in self.groups_tree.get_children(crcitem):
                fullpath = self.item_full_path(item)

                if fullpath.startswith(path_param + os.sep):
                    action(item,self.groups_tree)
                    sel_count+=1

        if not sel_count :
            self.info_dialog_on_main.show('No files found for specified path',path_param)
        else:
            self.status(f'Subdirectory action. {sel_count} File(s) Found')
            self.update_marks_folder()
            self.calc_mark_stats_groups()
            self.calc_mark_stats_folder()

    expr_by_tree={}

    def mark_expression(self,action,prompt,all_groups=True):
        tree=self.main.focus_get()

        if tree in self.expr_by_tree:
            initialvalue=self.expr_by_tree[tree]
        else:
            initialvalue='*'

        if tree==self.groups_tree:
            range_str = " (all groups)" if all_groups else " (selected group)"
            title='Specify expression for full file path.'
        else:
            range_str = ''
            title='Specify expression for file names in selected directory.'

        #self.mark_dialog_on_main.show(title,prompt + f'{range_str}', initialvalue,'treat as a regular expression',self.cfg.get_bool(CFG_KEY_USE_REG_EXPR))
        #use_reg_expr = self.mark_dialog_on_main.res_check
        #expression = self.mark_dialog_on_main.res_str

        if tree==self.groups_tree:
            self.mark_dialog_on_groups.show(title,prompt + f'{range_str}', initialvalue,'treat as a regular expression',self.cfg.get_bool(CFG_KEY_USE_REG_EXPR))
            use_reg_expr = self.mark_dialog_on_groups.res_check
            expression = self.mark_dialog_on_groups.res_str
        else:
            self.mark_dialog_on_folder.show(title,prompt + f'{range_str}', initialvalue,'treat as a regular expression',self.cfg.get_bool(CFG_KEY_USE_REG_EXPR))
            use_reg_expr = self.mark_dialog_on_folder.res_check
            expression = self.mark_dialog_on_folder.res_str

        items=[]
        use_reg_expr_info = '(regular expression)' if use_reg_expr else ''

        if expression:
            self.cfg.set_bool(CFG_KEY_USE_REG_EXPR,use_reg_expr)
            self.expr_by_tree[tree]=expression

            if tree==self.groups_tree:
                crc_range = self.groups_tree.get_children() if all_groups else [str(self.sel_crc)]

                for crcitem in crc_range:
                    for item in self.groups_tree.get_children(crcitem):
                        fullpath = self.item_full_path(item)
                        try:
                            if (use_reg_expr and re.search(expression,fullpath)) or (not use_reg_expr and fnmatch.fnmatch(fullpath,expression) ):
                                items.append(item)
                        except Exception as e:
                            self.info_dialog_on_main.show('expression Error !',f'expression:"{expression}"  {use_reg_expr_info}\n\nERROR:{e}')
                            tree.focus_set()
                            return
            else:
                for item in self.folder_tree.get_children():
                    if tree.set(item,'kind')==FILE:
                        file=self.folder_tree.set(item,'file')
                        try:
                            if (use_reg_expr and re.search(expression,file)) or (not use_reg_expr and fnmatch.fnmatch(file,expression) ):
                                items.append(item)
                        except Exception as e:
                            self.info_dialog_on_main.show('expression Error !',f'expression:"{expression}"  {use_reg_expr_info}\n\nERROR:{e}')
                            tree.focus_set()
                            return

            if items:
                self.main.config(cursor="watch")
                self.menu_disable()
                self.main.update()

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

                self.main.config(cursor="")
                self.menu_enable()
                self.main.update()

            else:
                #self.info_dialog_on_main
                self.info_dialog_on_mark[self.sel_tree].show('No files found.',f'expression:"{expression}"  {use_reg_expr_info}\n')

        tree.focus_set()

    def mark_subpath(self,action,all_groups=True):
        if path:=askdirectory(title='Select Directory',initialdir=self.cwd):
            self.action_on_path(path,action,all_groups)

    def goto_next_mark_menu(self,direction,go_to_no_mark=False):
        tree=self.sel_tree
        self.goto_next_mark(tree,direction,go_to_no_mark)

    def goto_next_mark(self,tree,direction,go_to_no_mark=False):
        marked=[item for item in tree.get_children() if not tree.tag_has(MARK,item)] if go_to_no_mark else tree.tag_has(MARK)
        if marked:
            if go_to_no_mark:
                #marked if not tree.tag_has(MARK,self.sel_item) else
                pool= self.tree_groups_flat_items if tree==self.groups_tree else self.folder_tree.get_children()
            else:
                pool=marked if tree.tag_has(MARK,self.sel_item) else self.tree_groups_flat_items if tree==self.groups_tree else self.folder_tree.get_children()

            poollen=len(pool)

            if poollen:
                index = pool.index(self.sel_item)

                while True:
                    index=(index+direction)%poollen
                    next_item=pool[index]
                    if (not go_to_no_mark and MARK in tree.item(next_item)['tags']) or (go_to_no_mark and MARK not in tree.item(next_item)['tags']):
                        tree.focus(next_item)
                        tree.see(next_item)

                        if tree==self.groups_tree:
                            self.groups_tree_sel_change(next_item)
                        else:
                            self.folder_tree_sel_change(next_item)

                        break

    def goto_next_dupe_file(self,tree,direction):
        marked=[item for item in tree.get_children() if tree.set(item,'kind')==FILE]
        if marked:
            pool=marked if tree.set(self.sel_item,'kind')==FILE else self.folder_tree.get_children()
            poollen=len(pool)

            if poollen:
                index = pool.index(self.sel_item)

                while True:
                    index=(index+direction)%poollen
                    next_item=pool[index]
                    if tree.set(next_item,'kind')==FILE:
                        tree.focus(next_item)
                        tree.see(next_item)

                        if tree==self.groups_tree:
                            self.groups_tree_sel_change(next_item)
                        else:
                            self.folder_tree_sel_change(next_item)

                        break

    dominant_groups_index={}
    dominant_groups_index[0] = -1
    dominant_groups_index[1] = -1

    dominant_groups_folder={}
    dominant_groups_folder[0] = -1
    dominant_groups_folder[1] = -1

    BY_WHAT={}
    BY_WHAT[0] = "by quantity"
    BY_WHAT[1] = "by sum size"

    @block_main_window
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
                info = core.bytes_to_str(biggest_crc_size_sum) if size_flag else str(biggest_crc_size_sum)
                self.status(f'Dominant (index:{working_index}) group ({self.BY_WHAT[size_flag]}: {info})')

    @block_main_window
    def goto_max_folder(self,size_flag=0,direction=1):
        if self.path_stat_list_size:
            #self.status(f'Setting dominant folder ...')
            working_index = self.dominant_groups_folder[size_flag]
            working_index = (working_index+direction) % len(self.path_stat_list_size)
            temp = str(working_index)
            working_dict = self.path_stat_list_size if size_flag else self.path_stat_list_quant

            pathnr,path,num = working_dict[working_index]

            item=self.biggest_file_of_path_id[(pathnr,path)]

            self.groups_tree.focus(item)
            self.groups_tree_sel_change(item,change_status_line=False)

            try:
                self.groups_tree.see(self.groups_tree.get_children(self.sel_crc)[-1])
                self.groups_tree.see(self.sel_crc)
                self.groups_tree.see(item)
            except Exception :
                pass

            self.folder_tree.update()

            try:
                self.folder_tree.focus_set()
                self.folder_tree.focus(item)
                self.folder_tree_sel_change(item,change_status_line=False)
                self.folder_tree.see(item)
            except Exception :
                pass

            self.groups_tree_update(item)

            self.dominant_groups_folder[size_flag] = int(temp)
            info = core.bytes_to_str(num) if size_flag else str(num)
            self.status(f'Dominant (index:{working_index}) folder ({self.BY_WHAT[size_flag]}: {info})')

    def item_full_path(self,item):
        pathnr=int(self.groups_tree.set(item,'pathnr'))
        path=self.groups_tree.set(item,'path')
        file=self.groups_tree.set(item,'file')
        return os.path.abspath(dude_core.get_full_path_scanned(pathnr,path,file))

    def file_check_state(self,item):
        fullpath = self.item_full_path(item)
        logging.info('checking file:%s',fullpath)
        try:
            stat = os.stat(fullpath)
            ctime_check=core.int_to_str(int(round(stat.st_ctime)))
        except Exception as e:
            self.status(str(e))
            mesage = f'can\'t check file: {fullpath}\n\n{e}'
            logging.error(mesage)
            return mesage

        if ctime_check != (ctime:=self.groups_tree.set(item,'ctime')) :
            message = {f'ctime inconsistency {ctime_check} vs {ctime}'}
            return message

        return None

    def process_files_in_groups_wrapper(self,action,all_groups):
        processed_items=defaultdict(list)
        if all_groups:
            scope_title='All marked files.'
        else:
            scope_title='Single CRC group.'

        for crc in self.groups_tree.get_children():
            if all_groups or crc==self.sel_crc:
                for item in self.groups_tree.get_children(crc):
                    if self.groups_tree.tag_has(MARK,item):
                        processed_items[crc].append(item)

        return self.process_files(action,processed_items,scope_title)

    def process_files_in_folder_wrapper(self,action,on_dir_action=False):
        processed_items=defaultdict(list)
        if on_dir_action:
            scope_title='All marked files on selected directory sub-tree.'

            sel_path_with_sep=self.sel_full_path_to_file + os.sep
            for crc in self.groups_tree.get_children():
                for item in self.groups_tree.get_children(crc):
                    if self.item_full_path(item).startswith(sel_path_with_sep):
                        if self.groups_tree.tag_has(MARK,item):
                            processed_items[crc].append(item)
        else:
            scope_title='Selected Directory.'
            #self.sel_path_full

            for item in self.folder_tree.get_children():
                if self.folder_tree.tag_has(MARK,item):
                    crc=self.folder_tree.set(item,'crc')
                    processed_items[crc].append(item)

        return self.process_files(action,processed_items,scope_title)

    CHECK_OK='ok_special_string'
    CHECK_ERR='error_special_string'

    @restore_status_line
    def process_files_check_correctness(self,action,processed_items,remaining_items):

        skip_incorrect = self.cfg.get_bool(CFG_SKIP_INCORRECT_GROUPS)
        show_full_crc=self.cfg.get_bool(CFG_KEY_FULL_CRC)

        self.status('checking data consistency with filesystem state ...')
        for crc in processed_items:
            size = dude_core.crc_to_size[crc]
            (checkres,tuples_to_remove)=dude_core.check_group_files_state(size,crc)

            if checkres:
                self.info_dialog_on_main.show('Error. Inconsistent data.','Current filesystem state is inconsistent with scanned data.\n\n' + '\n'.join(checkres) + '\n\nSelected CRC group will be reduced. For complete results re-scanning is recommended.')
                orglist=self.groups_tree.get_children()

                dude_core.remove_from_data_pool(size,crc,tuples_to_remove)

                self.crc_node_update(crc)

                self.tree_groups_flat_items_update()

                self.data_precalc()

                newlist=self.groups_tree.get_children()
                item_to_sel = self.get_closest_in_crc(orglist,crc,newlist)

                self.reset_sels()

                if item_to_sel:
                    #crc node moze zniknac - trzeba zupdejtowac SelXxx
                    self.crc_select_and_focus(item_to_sel,True)
                else:
                    self.initial_focus()

                self.calc_mark_stats_groups()

        self.status('checking selection correctness...')

        incorrect_groups=[]
        if action==HARDLINK:
            for crc in processed_items:
                if len(processed_items[crc])==1:
                    incorrect_groups.append(crc)
            problem_header = 'Single file marked'
            problem_message = "Mark more files\nor enable option:\n\"Skip groups with invalid selection\""
        else:
            for crc in processed_items:
                if len(remaining_items[crc])==0:
                    incorrect_groups.append(crc)

            problem_header = 'All files marked'
            problem_message = "Keep at least one file unmarked\nor enable option:\n\"Skip groups with invalid selection\""

        if incorrect_groups:
            if skip_incorrect:

                incorrect_group_str='\n'.join([crc if show_full_crc else dude_core.crc_cut[crc] for crc in incorrect_groups ])
                header = f'Warning ({NAME[action]}). {problem_header}'
                message = f"Option \"Skip groups with invalid selection\" is enabled.\n\nFollowing CRC groups will NOT be processed and remain with markings:\n\n{incorrect_group_str}"

                self.text_info_dialog.show(header,message)

                self.crc_select_and_focus(incorrect_groups[0],True)

                for crc in incorrect_groups:
                    del processed_items[crc]
                    del remaining_items[crc]

            else:
                if action==DELETE and self.cfg.get_bool(CFG_ALLOW_DELETE_ALL):
                    self.text_ask_dialog.show('Warning !','Option: \'Allow to delete all copies\' is set.|RED\n\nAll copies may be selected.|RED\n\nProceed ?|RED')
                    if self.text_ask_dialog.res_bool:
                        return self.CHECK_OK
                else:
                    header = f'Error ({NAME[action]}). {problem_header}'
                    self.info_dialog_on_main.show(header,problem_message)

                self.crc_select_and_focus(incorrect_groups[0],True)
                return self.CHECK_ERR

        return self.CHECK_OK

    @restore_status_line
    def process_files_check_correctness_last(self,action,processed_items,remaining_items):
        self.status('final checking selection correctness')

        if action==HARDLINK:
            for crc in processed_items:
                if len({self.groups_tree.set(item,'dev') for item in processed_items[crc]})>1:
                    title='Can\'t create hardlinks.'
                    message=f"Files on multiple devices selected. Crc:{crc}"
                    logging.error(title)
                    logging.error(message)
                    self.info_dialog_on_main.show(title,message)
                    return self.CHECK_ERR
        for crc in processed_items:
            for item in remaining_items[crc]:
                if res:=self.file_check_state(item):
                    self.info_dialog_on_main.show('Error',res+'\n\nNo action was taken.\n\nAborting. Repeat scanning please or unmark all files and groups affected by other programs.')
                    logging.error('aborting.')
                    return self.CHECK_ERR

        logging.info('remaining files checking complete.')
        return self.CHECK_OK

    @restore_status_line
    def process_files_confirm(self,action,processed_items,remaining_items,scope_title):
        self.status('confirmation required...')
        show_full_path=1

        message=[]
        if not self.cfg.get_bool(CFG_CONFIRM_SHOW_CRCSIZE):
            message.append('')

        for crc in processed_items:
            if self.cfg.get_bool(CFG_CONFIRM_SHOW_CRCSIZE):
                size=int(self.groups_tree.set(crc,'size'))
                message.append('')
                message.append('CRC:' + crc + ' size:' + core.bytes_to_str(size) + '|GRAY')

            for item in processed_items[crc]:
                message.append((self.item_full_path(item) if show_full_path else self.groups_tree.set(item,'file')) + '|RED' )

            if action==SOFTLINK:
                if remaining_items[crc]:
                    item = remaining_items[crc][0]
                    if self.cfg.get_bool(CFG_CONFIRM_SHOW_LINKSTARGETS):
                        message.append('%s %s' % (FILE_LINK_RIGHT,(self.item_full_path(item) if show_full_path else self.groups_tree.set(item,'file'))) )

        if action==DELETE:
            self.text_ask_dialog.show('Delete marked files ?','Scope - ' + scope_title +'\n'+'\n'.join(message))
            if not self.text_ask_dialog.res_bool:
                return True
        elif action==SOFTLINK:
            self.text_ask_dialog.show('Soft-Link marked files to first unmarked file in group ?','Scope - ' + scope_title +'\n'+'\n'.join(message))
            if not self.text_ask_dialog.res_bool:
                return True
        elif action==HARDLINK:
            self.text_ask_dialog.show('Hard-Link marked files together in groups ?','Scope - ' + scope_title +'\n'+'\n'.join(message))
            if not self.text_ask_dialog.res_bool:
                return True

        _ = {logging.warning(line) for line in message}
        logging.warning('###########################################################################################')
        logging.warning('Confirmed.')
        return False

    @block_main_window
    def empty_dirs_removal(self,startpath,report_empty=False):
        string=f'Removing empty directories in:\'{startpath}\''
        self.status(string)
        self.main.update()
        logging.info(string)

        removed=[]
        index=0
        for (path, dirs, files) in os.walk(startpath, topdown=False, followlinks=False):
            string2=f'{string} {self.PROGRESS_SIGNS[index]}'
            self.status(string2)
            index+=1
            index %= 4
            if not files:
                try:
                    self.main.update()
                    os.rmdir(path)
                    logging.info('Empty removed:%s',path)
                    removed.append(path)
                except Exception as e:
                    logging.error('empty_dirs_removal:%s',e)

        self.status('')

        if report_empty and not removed:
            removed.append(f'No empty subdirectories in:\'{startpath}\'')

        return removed

    def process_files_core(self,action,processed_items,remaining_items):
        self.main.config(cursor="watch")
        self.menu_disable()
        self.status('processing files ...')
        self.main.update()

        final_info=[]
        if action==DELETE:
            directories_to_check=set()
            for crc in processed_items:
                tuples_to_delete=set()
                size=int(self.groups_tree.set(processed_items[crc][0],'size'))
                for item in processed_items[crc]:
                    index_tuple=self.get_index_tuple_groups_tree(item)
                    tuples_to_delete.add(index_tuple)
                    directories_to_check.add(dude_core.get_path(index_tuple))

                if resmsg:=dude_core.delete_file_wrapper(size,crc,tuples_to_delete):
                    logging.error(resmsg)
                    self.info_dialog_on_main.show('Error',resmsg)

                self.crc_node_update(crc)

            if self.cfg.get_bool(ERASE_EMPTY_DIRS):
                directories_to_check_list=list(directories_to_check)
                directories_to_check_list.sort(key=lambda d : (len(str(d).split(os.sep)),d),reverse=True )

                removed=[]
                for directory in directories_to_check_list:
                    removed.extend(self.empty_dirs_removal(directory))

                final_info.extend(removed)

        elif action==SOFTLINK:
            do_rel_symlink = self.cfg.get_bool(CFG_KEY_REL_SYMLINKS)
            for crc in processed_items:
                to_keep_item=list(remaining_items[crc])[0]
                #self.groups_tree.focus()
                index_tuple_ref=self.get_index_tuple_groups_tree(to_keep_item)
                size=int(self.groups_tree.set(to_keep_item,'size'))

                if resmsg:=dude_core.link_wrapper(True, do_rel_symlink, size,crc, index_tuple_ref, [self.get_index_tuple_groups_tree(item) for item in processed_items[crc] ] ):
                    logging.error(resmsg)
                    self.info_dialog_on_main.show('Error',resmsg)
                self.crc_node_update(crc)

        elif action==HARDLINK:
            for crc in processed_items:
                ref_item=processed_items[crc][0]
                index_tuple_ref=self.get_index_tuple_groups_tree(ref_item)
                size=int(self.groups_tree.set(ref_item,'size'))

                if resmsg:=dude_core.link_wrapper(False, False, size,crc, index_tuple_ref, [self.get_index_tuple_groups_tree(item) for item in processed_items[crc][1:] ] ):
                    logging.error(resmsg)
                    self.info_dialog_on_main.show('Error',resmsg)
                self.crc_node_update(crc)

        self.main.config(cursor="")
        self.menu_enable()

        self.data_precalc()
        self.tree_groups_flat_items_update()

        if final_info:
            self.text_info_dialog.show('Removed empty directories','\n'.join(final_info))

    def get_this_or_existing_parent(self,path):
        if os.path.exists(path):
            return path

        return self.get_this_or_existing_parent(pathlib.Path(path).parent.absolute())

    def process_files(self,action,processed_items,scope_title):
        tree=self.sel_tree

        if not processed_items:
            self.info_dialog_on_main.show('No Files Marked For Processing !','Scope: ' + scope_title + '\n\nMark files first.')
            return

        logging.info('process_files: %s',action)
        logging.info('Scope %s',scope_title)

        #############################################
        #check remainings

        #remaining_items dla wszystkich (moze byc akcja z folderu)
        #istotna kolejnosc

        affected_crcs=processed_items.keys()

        self.status('checking remaining items...')
        remaining_items={}
        for crc in affected_crcs:
            remaining_items[crc]=[item for item in self.groups_tree.get_children(crc) if not self.groups_tree.tag_has(MARK,item)]

        check=self.process_files_check_correctness(action,processed_items,remaining_items)

        if check == self.CHECK_ERR:
            return

        if check!=self.CHECK_OK:
            self.info_dialog_on_main.show('INTERNAL ERROR 1 - aborting','got %s from process_files_check_correctness' % check)
            return

        if not processed_items:
            self.info_dialog_on_main.show('info','No files left for processing.\nFix files selection.')
            return

        logging.warning('###########################################################################################')
        logging.warning('action:%s',action)

        self.status('')
        if self.process_files_confirm(action,processed_items,remaining_items,scope_title):
            return

        #after confirmation
        check=self.process_files_check_correctness_last(action,processed_items,remaining_items)
        if check == self.CHECK_ERR:
            return

        if check!=self.CHECK_OK:
            self.info_dialog_on_main.show('INTERNAL ERROR 1 - aborting','got %s process_files_check_correctness_last' % check)
            return

        #############################################
        #action

        if tree==self.groups_tree:
            orglist=self.tree_groups_flat_items
        else:
            org_sel_item=self.sel_item
            orglist=self.folder_tree.get_children()
            org_sel_file=self.folder_tree.set(org_sel_item,'file')

        #############################################
        self.process_files_core(action,processed_items,remaining_items)
        #############################################

        if tree==self.groups_tree:
            #newlist=self.groups_tree.get_children()

            sel_item = self.sel_item if self.sel_item else self.sel_crc
            item_to_sel = self.get_closest_in_crc(orglist,sel_item,self.tree_groups_flat_items)

            if item_to_sel:
                self.groups_tree.see(item_to_sel)
                self.groups_tree.focus(item_to_sel)
                self.groups_tree_sel_change(item_to_sel)
            else:
                self.initial_focus()
        else:
            parent = self.get_this_or_existing_parent(self.sel_path_full)

            if self.tree_folder_update(parent):
                newlist=self.folder_tree.get_children()

                item_to_sel = self.get_closest_in_folder(orglist,org_sel_item,org_sel_file,newlist)

                self.set_focus_on_item=True
                self.folder_tree.focus_set()

                if item_to_sel:
                    self.folder_tree.focus(item_to_sel)
                    self.folder_tree_sel_change(item_to_sel)
                    self.folder_tree.see(item_to_sel)
                    self.folder_tree.update()

        self.calc_mark_stats_groups()

        self.folder_items_cache={}

        self.find_result=()

    def get_closest_in_folder(self,prev_list,item,item_name,new_list):
        if item in new_list:
            return item

        if not new_list:
            return None

        new_list_names=[self.folder_tree.set(item,'file') for item in self.folder_tree.get_children()]

        if item_name in new_list_names:
            return new_list[new_list_names.index(item_name)]

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

    def get_closest_in_crc(self,prev_list,item,new_list):
        if item in new_list:
            return item

        if not new_list:
            return None

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

    def cache_clean(self):
        try:
            shutil.rmtree(CACHE_DIR)
        except Exception as e:
            logging.error(e)

    def clip_copy_full_path_with_file(self):
        if self.sel_path_full and self.sel_file:
            self.clip_copy(os.path.join(self.sel_path_full,self.sel_file))
        elif self.sel_crc:
            self.clip_copy(self.sel_crc)

    def clip_copy_full(self):
        if self.sel_path_full:
            self.clip_copy(self.sel_path_full)
        elif self.sel_crc:
            self.clip_copy(self.sel_crc)

    def clip_copy_file(self):
        if self.sel_file:
            self.clip_copy(self.sel_file)
        elif self.sel_crc:
            self.clip_copy(self.sel_crc)

    def clip_copy(self,what):
        self.main.clipboard_clear()
        self.main.clipboard_append(what)
        self.status('Copied to clipboard: "%s"' % what)

    @block_main_window
    def enter_dir(self,fullpath,sel):
        if self.find_tree_index==1:
            self.find_result=()

        if self.tree_folder_update(fullpath):
            children=self.folder_tree.get_children()
            res_list=[nodeid for nodeid in children if self.folder_tree.set(nodeid,'file')==sel]
            if res_list:
                item=res_list[0]
                self.folder_tree.see(item)
                self.folder_tree.focus(item)
                self.folder_tree_sel_change(item)

            elif children:
                self.folder_tree.focus(children[0])
                self.sel_file = self.groups_tree.set(children[0],'file')
                self.folder_tree_sel_change(children[0])

    def double_left_button(self,event):
        if not self.main_window_active:
            return

        tree=event.widget
        if tree.identify("region", event.x, event.y) != 'heading':
            if item:=tree.identify('item',event.x,event.y):
                self.main.after_idle(lambda : self.tree_action(tree,item))

    def tree_action(self,tree,item):
        if tree.set(item,'kind') == UPDIR:
            head,tail=os.path.split(self.sel_path_full)
            self.enter_dir(os.path.normpath(str(pathlib.Path(self.sel_path_full).parent.absolute())),tail)
        elif tree.set(item,'kind') in (DIR,DIRLINK):
            self.enter_dir(self.sel_path_full+self.folder_tree.set(item,'file') if self.sel_path_full=='/' else os.sep.join([self.sel_path_full,self.folder_tree.set(item,'file')]),'..' )
        elif tree.set(item,'kind')!=CRC:
            self.open_file()

    @busy_cursor
    @block_main_window
    def open_folder(self):
        if self.sel_path_full:

            if wrapper:=self.folders_open_wrapper.get():
                self.status(f'Opening: {wrapper} {self.sel_path_full}')
                if windows:
                    os.startfile(wrapper + ' ' + self.sel_path_full)
                else:
                    os.system(wrapper + ' "' + self.sel_path_full.replace("'","\'").replace("`","\`") + '"')
            else:
                self.status(f'Opening: {self.sel_path_full}')
                if windows:
                    os.startfile(self.sel_path_full)
                else:
                    os.system('xdg-open "' + self.sel_path_full.replace("'","\'").replace("`","\`") + '"')

    #@restore_status_line
    @busy_cursor
    @block_main_window
    def open_file(self):
        if self.sel_kind in (FILE,LINK,SINGLE,SINGLEHARDLINKED):

            if wrapper:=self.file_open_wrapper.get():
                self.status(f'Opening: {wrapper} {self.sel_file}')
                if windows:
                    os.startfile(wrapper + ' ' + os.sep.join([self.sel_path_full,self.sel_file]))
                else:
                    os.system(wrapper + ' "' + os.sep.join([self.sel_path_full,self.sel_file]).replace("'","\'").replace("`","\`") + '"')
            else:
                self.status(f'Opening: {self.sel_file}')
                if windows:
                    os.startfile(os.sep.join([self.sel_path_full,self.sel_file]))
                else:
                    os.system('xdg-open "' + os.sep.join([self.sel_path_full,self.sel_file]).replace("'","\'").replace("`","\`") + '"')

        elif self.sel_kind in (DIR,DIRLINK):
            self.open_folder()

    def show_log(self):
        if windows:
            os.startfile(log)
        else:
            os.system("xdg-open "+ '"' + log + '"')

    def show_logs_dir(self):
        if windows:
            os.startfile(LOG_DIR)
        else:
            os.system("xdg-open " + '"' + LOG_DIR + '"')

    def show_homepage(self):
        if windows:
            os.startfile(HOMEPAGE)
        else:
            os.system("xdg-open " + HOMEPAGE)

if windows:
    import win32gui
    import win32con

if __name__ == "__main__":
    try:
        #######################################################################
        #timestamp

        VER_TIMESTAMP = console.get_ver_timestamp()

        CURRENT_EXECUTABLE = os.path.abspath(sys.argv[0])
        DUDE_FILE = os.path.normpath(__file__)

        p_args = console.parse_args(VER_TIMESTAMP)

        if not p_args.csv:
            foreground_window = win32gui.GetForegroundWindow() if windows and not p_args.nohide else None

            if foreground_window:
                win32gui.ShowWindow(foreground_window, win32con.SW_HIDE)

        log=os.path.abspath(p_args.log[0]) if p_args.log else LOG_DIR + os.sep + time.strftime('%Y_%m_%d_%H_%M_%S',time.localtime(time.time()) ) +'.txt'
        LOG_LEVEL = logging.DEBUG if p_args.debug else logging.INFO

        pathlib.Path(LOG_DIR).mkdir(parents=True,exist_ok=True)

        print('log:',log)

        logging.basicConfig(level=LOG_LEVEL,format='%(asctime)s %(levelname)s %(message)s', filename=log,filemode='w')

        DEBUG_MODE = bool(p_args.debug)

        logging.debug('DEBUG LEVEL')

        dude_core = core.DudeCore(CACHE_DIR,logging,DEBUG_MODE)

        if p_args.csv:
            signal.signal(signal.SIGINT, lambda a, k : dude_core.handle_sigint())

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

            scan_thread=Thread(target=dude_core.scan,daemon=True)
            scan_thread.start()

            while scan_thread.is_alive():
                print('Scanning ...', dude_core.info_counter,end='\r')
                time.sleep(0.04)

            scan_thread.join()

            crc_thread=Thread(target=dude_core.crc_calc,daemon=True)
            crc_thread.start()

            while crc_thread.is_alive():
                print(f'crc_calc...{dude_core.info_files_done}/{dude_core.info_total}                 ',end='\r')
                time.sleep(0.04)

            crc_thread.join()
            print('')
            dude_core.write_csv(p_args.csv[0])
            print('Done')

        else:
            Gui(os.getcwd(),p_args.paths,p_args.exclude,p_args.exclude_regexp,p_args.norun)

            if foreground_window:
                win32gui.ShowWindow(foreground_window, win32con.SW_SHOWDEFAULT)
                win32gui.ShowWindow(foreground_window, win32con.SW_RESTORE)
                win32gui.ShowWindow(foreground_window, win32con.SW_SHOW)

    except Exception as e_main:
        print(e_main)
        logging.error(e_main)
        sys.exit(1)
