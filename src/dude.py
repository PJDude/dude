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

import time
import configparser
import logging
import argparse

import tkinter as tk
from tkinter import *
from tkinter import ttk
#from tkinter import font

from tkinter.filedialog import askdirectory

from collections import defaultdict
from threading import Thread
from sys import exit
from sys import argv

import version
import core
import console
from dialogs import *

log_levels={logging.DEBUG:'DEBUG',logging.INFO:'INFO'}

try:
    from appdirs import *
    CACHE_DIR = os.sep.join([user_cache_dir('dude','PJDude'),"cache"])
    LOG_DIR = user_log_dir('dude','PJDude')
    CONFIG_DIR = user_config_dir('dude')
except Exception as e:
    print(e)
    CONFIG_DIR=LOG_DIR=CACHE_DIR = os.sep.join([os.getcwd(),"dude-no-appdirs"])

windows = (os.name=='nt')

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
    CFG_ALLOW_DELETE_NON_DUPLICATES:False
    }

MARK='M'
UPDIR='0'
DIR='1'
LINK='2'
FILE='3'
SINGLE='4'
SINGLEHARDLINKED='5'
CRC='C'

DELETE=0
SOFTLINK=1
HARDLINK=2

HOMEPAGE='https://github.com/PJDude/dude'

class Config:
    def __init__(self,ConfigDir):
        logging.debug(f'Initializing config: {ConfigDir}')
        self.config = configparser.ConfigParser()
        self.config.add_section('main')
        self.config.add_section('geometry')

        self.path = ConfigDir
        self.file = self.path + '/cfg.ini'

    def write(self):
        logging.debug('writing config')
        pathlib.Path(self.path).mkdir(parents=True,exist_ok=True)
        with open(self.file, 'w') as configfile:
            self.config.write(configfile)

    def read(self):
        logging.debug('reading config')
        if os.path.isfile(self.file):
            try:
                with open(self.file, 'r') as configfile:
                    self.config.read_file(configfile)
            except Exception as e:
                logging.error(e)
        else:
            logging.warning(f'no config file:{self.file}')

    def set(self,key,val,section='main'):
        self.config.set(section,key,val)

    def set_bool(self,key,val,section='main'):
        self.config.set(section,key,('0','1')[val])

    def get(self,key,default=None,section='main'):
        try:
            res=self.config.get(section,key)
        except Exception as e:
            logging.warning(f'gettting config key {key}')
            logging.warning(e)
            res=default
            self.set(key,str(default),section=section)

        return str(res).replace('[','').replace(']','').replace('"','').replace("'",'').replace(',','').replace(' ','')

    def get_bool(self,key,section='main'):
        try:
            res=self.config.get(section,key)
            return res=='1'

        except Exception as e:
            logging.warning(f'gettting config key {key}')
            logging.warning(e)
            res=cfg_defaults[key]
            self.set_bool(key,res,section=section)
            return res

###########################################################

raw = lambda x : x

class Gui:
    NUMBERS='①②③④⑤⑥⑦⑧⑨⑩' if windows else '⓵⓶⓷⓸⓹⓺⓻⓼⓽⓾'

    PROGRESS_SIGNS='◐◓◑◒'

    MAX_PATHS=10

    sel_item_of_tree = {}

    sel_path_full={}
    folder_items_cache={}

    do_process_events=True

    def busy_cursor(f):
        def busy_cursor_wrapp(self,*args,**kwargs):
            prev_process_events=self.do_process_events
            self.do_process_events=False

            prevCursor=self.menubar.cget('cursor')

            a = self.main.after(1000,lambda : self.menubar.config(cursor='watch') or self.main.config(cursor='watch') or self.main.update())

            try:
                res=f(self,*args,**kwargs)
            except Exception as e:
                self.status(str(e))
                res=None
                logging.error(e)

            self.main.after_cancel(a)

            self.main.config(cursor=prevCursor)
            self.menubar.config(cursor=prevCursor)

            self.do_process_events=prev_process_events

            return res
        return busy_cursor_wrapp

    def restore_status_line(f):
        def restore_status_line_wrapp(self,*args,**kwargs):
            prev=self.status_line.get()
            try:
                res=f(self,*args,**kwargs)
            except Exception as e:
                self.status(str(e))
                res=None
                logging.error(e)

            self.status(prev)
            return res
        return restore_status_line_wrapp

    def keep_semi_focus(f):
        def keep_semi_focus_wrapp(self,*args,**kwargs):
            tree=self.main.focus_get()

            try:
                tree.configure(style='semi_focus.Treeview')
            except:
                pass

            try:
                res=f(self,*args,**kwargs)
            except Exception as e:
                self.status(str(e))
                res=None
                logging.error(e)

            try:
                tree.configure(style='default.Treeview')
            except:
                pass

            return res
        return keep_semi_focus_wrapp

    #######################################################################
    action_abort=False
    def crc_progress_dialog_show(self,parent,title,ProgressMode1=None,ProgressMode2=None,Progress1LeftText=None,Progress2LeftText=None):
        self.LADParent=parent

        self.psIndex =0

        self.ProgressMode1=ProgressMode1
        self.ProgressMode2=ProgressMode2

        self.crc_progress_dialog = tk.Toplevel(parent)
        self.crc_progress_dialog.wm_transient(parent)

        self.crc_progress_dialog.protocol("WM_DELETE_WINDOW", self.crc_progress_dialog_abort)
        self.crc_progress_dialog.bind('<Escape>', self.crc_progress_dialog_abort)

        self.crc_progress_dialog.wm_title(title)
        self.crc_progress_dialog.iconphoto(False, self.iconphoto)

        (f0:=tk.Frame(self.crc_progress_dialog,bg=self.bg)).pack(expand=1,fill='both',side='top')
        (f1:=tk.Frame(self.crc_progress_dialog,bg=self.bg)).pack(expand=1,fill='both',side='top')

        self.progr1var = DoubleVar()
        self.progr1=ttk.Progressbar(f0,orient=HORIZONTAL,length=100, mode=ProgressMode1,variable=self.progr1var)

        if ProgressMode1:
            self.progr1.grid(row=0,column=1,padx=1,pady=4,sticky='news')

        self.progr1LabLeft=tk.Label(f0,width=17,bg=self.bg)
        if Progress1LeftText:
            self.progr1LabLeft.grid(row=0,column=0,padx=1,pady=4)
            self.progr1LabLeft.config(text=Progress1LeftText)

        self.progr1LabRight=tk.Label(f0,width=17,bg=self.bg)

        if self.ProgressMode1=='determinate':
            self.progr1LabRight.grid(row=0,column=2,padx=1,pady=4)
            self.Progress1Func=(lambda progress1 : self.progr1var.set(progress1) )
        elif self.ProgressMode1=='indeterminate':
            self.Progress1Func=(lambda progress1 : self.progr1.start())
        else :
            self.Progress1Func=lambda args : None

        self.progr2var = DoubleVar()
        self.progr2=ttk.Progressbar(f0,orient=HORIZONTAL,length=100, mode=ProgressMode2,variable=self.progr2var)
        self.progr2LabRight=tk.Label(f0,width=17,bg=self.bg)

        if ProgressMode2:
            self.crc_progress_dialog.minsize(550, 60)
            self.progr2.grid(row=1,column=1,padx=1,pady=4,sticky='news')

            if Progress2LeftText:
                self.progr2LabLeft=tk.Label(f0,width=17,bg=self.bg)
                self.progr2LabLeft.grid(row=1,column=0,padx=1,pady=4)
                self.progr2LabLeft.config(text=Progress2LeftText)

            self.progr2LabRight.grid(row=1,column=2,padx=1,pady=4)
        else:
            self.crc_progress_dialog.minsize(300, 60)

        f0.grid_columnconfigure(1, weight=1)

        self.message=tk.StringVar()
        tk.Label(f1,textvariable=self.message,anchor='n',justify='center',width=20,bg=self.bg).pack(side='top',padx=8,pady=8,expand=1,fill='x')
        ttk.Button(f1, text='abort', width=10 ,command=self.crc_progress_dialog_abort ).pack(side='bottom',padx=8,pady=8)

        try:
            self.crc_progress_dialog.update()
            self.crc_progress_dialog.grab_set()
            set_geometry_by_parent(self.crc_progress_dialog,parent)
        except Exception :
            pass

        self.prevParentCursor=parent.cget('cursor')
        parent.config(cursor="watch")

        self.action_abort=False

    def crc_progress_dialog_abort(self,event=None):
        self.action_abort=True

    def crc_progress_dialog_end(self):
        self.crc_progress_dialog.grab_release()
        self.crc_progress_dialog.destroy()
        self.LADParent.config(cursor=self.prevParentCursor)

    message_prev=''
    progr_1_right_prev=''
    progr_2_right_prev=''
    time_without_busy_sign=0

    def crc_progress_dialog_update(self,message,progress1=None,progress2=None,progr_1_right=None,progr_2_right=None,StatusInfo=None):
        prefix=''

        if StatusInfo:
            self.status(StatusInfo)
        else:
            self.status('')

        if self.progr_1_right_prev==progr_1_right and self.progr_2_right_prev==progr_2_right and self.message_prev==message:
            if time.time()>self.time_without_busy_sign+1.0:
                prefix=self.PROGRESS_SIGNS[self.psIndex]
                self.psIndex=(self.psIndex+1)%4

        else:
            self.message_prev=message
            self.progr_1_right_prev=progr_1_right
            self.progr_2_right_prev=progr_2_right

            self.time_without_busy_sign=time.time()

            self.Progress1Func(progress1)
            self.progr1LabRight.config(text=progr_1_right)
            self.progr2var.set(progress2)
            self.progr2LabRight.config(text=progr_2_right)

        self.message.set('%s\n%s'%(prefix,message))
        self.crc_progress_dialog.update()
    
    def __init__(self,cwd,pathsToAdd=None,exclude=None,excluderegexp=None,norun=None,debug_mode=False):
        self.D = core.DudeCore(CACHE_DIR,logging)
        self.cwd=cwd
        self.debug_mode=debug_mode

        self.cfg = Config(CONFIG_DIR)
        self.cfg.read()

        self.paths_to_scan_frames=[]
        self.exclude_frames=[]

        self.paths_to_scan_from_dialog=[]

        ####################################################################
        self.main = tk.Tk()
        self.main.title(f'Dude (DUplicates DEtector) v{version.VERSION}')
        self.main.protocol("WM_DELETE_WINDOW", self.exit)
        self.main.withdraw()
        self.main.update()
        
        self.main.minsize(1200, 800)

        self.iconphoto = PhotoImage(file = os.path.join(os.path.dirname(__file__),'icon.png'))
        self.main.iconphoto(False, self.iconphoto)

        self.main.bind('<KeyPress-F2>', lambda event : self.SettingsDialog.show(focus=self.cancel_button))
        self.main.bind('<KeyPress-F1>', lambda event : self.AboutDialog.show())
        self.main.bind('<KeyPress-s>', lambda event : self.scan_dialog_show())
        self.main.bind('<KeyPress-S>', lambda event : self.scan_dialog_show())

        #self.defaultFont = font.nametofont("TkDefaultFont")
        #self.defaultFont.configure(family="Monospace regular",size=8,weight=font.BOLD)
        #self.defaultFont.configure(family="Monospace regular",size=10)
        #self.main.option_add("*Font", self.defaultFont)

        ####################################################################
        style = ttk.Style()

        style.theme_create("dummy", parent='vista' if windows else 'clam' )

        self.bg = style.lookup('TFrame', 'background')

        style.theme_use("dummy")

        style.configure("TButton", anchor = "center")
        style.configure("TButton", background = self.bg)

        style.configure("TCheckbutton", background = self.bg)

        style.map("TButton",  relief=[('disabled',"flat"),('',"raised")] )
        style.map("TButton",  fg=[('disabled',"gray"),('',"black")] )

        style.map("Treeview.Heading",  relief=[('','raised')] )
        style.configure("Treeview",rowheight=18)

        FocusBg='#90DD90'
        SelBg='#AAAAAA'

        #style.map('Treeview', background=[('focus',FocusBg),('selected',SelBg),('',self.bg)])
        style.map('Treeview', background=[('focus',FocusBg),('selected',SelBg),('','white')])

        style.map('semi_focus.Treeview', background=[('focus',FocusBg),('selected',FocusBg),('','white')])
        style.map('default.Treeview', background=[('focus',FocusBg),('selected',SelBg),('','white')])

        #works but not for every theme
        #style.configure("Treeview", fieldbackground=self.bg)

        #######################################################################
        self.menubar = Menu(self.main,bg=self.bg)
        self.main.config(menu=self.menubar)
        #######################################################################

        self.status_var_all_size=tk.StringVar()
        self.status_var_all_quant=tk.StringVar()
        self.status_var_groups=tk.StringVar()
        self.status_var_full_path=tk.StringVar()
        self.status_var_folder_size=tk.StringVar()
        self.status_var_folder_quant=tk.StringVar()

        self.paned = PanedWindow(self.main,orient=tk.VERTICAL,relief='sunken',showhandle=0,bd=0,bg=self.bg,sashwidth=2,sashrelief='flat')
        self.paned.pack(fill='both',expand=1)

        frame_groups = tk.Frame(self.paned,bg=self.bg)
        self.paned.add(frame_groups)
        frame_folder = tk.Frame(self.paned,bg=self.bg)
        self.paned.add(frame_folder)

        frame_groups.grid_columnconfigure(0, weight=1)
        frame_groups.grid_rowconfigure(0, weight=1,minsize=200)

        frame_folder.grid_columnconfigure(0, weight=1)
        frame_folder.grid_rowconfigure(0, weight=1,minsize=200)

        (status_frame_groups := tk.Frame(frame_groups,bg=self.bg)).pack(side='bottom', fill='both')
        self.status_var_groups.set('0')
        self.status_var_full_path.set('')

        tk.Label(status_frame_groups,width=10,textvariable=self.status_var_all_quant,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=16,text="All marked files # ",relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=10,textvariable=self.status_var_all_size,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=18,text='All marked files size: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=10,textvariable=self.status_var_groups,borderwidth=2,bg=self.bg,relief='groove',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=10,text='Groups: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=8,text='Full path: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='left')
        self.status_var_full_path_label = tk.Label(status_frame_groups,textvariable=self.status_var_full_path,relief='flat',borderwidth=2,bg=self.bg,anchor='w')
        self.status_var_full_path_label.pack(fill='x',expand=1,side='left')

        (status_frame_folder := tk.Frame(frame_folder,bg=self.bg)).pack(side='bottom',fill='both')

        self.status_line=tk.StringVar()
        self.status_line.set('')

        self.StatusLineLabel=tk.Label(status_frame_folder,width=30,textvariable=self.status_line,borderwidth=2,bg=self.bg,relief='groove',anchor='w')
        self.StatusLineLabel.pack(fill='x',expand=1,side='left')

        tk.Label(status_frame_folder,width=10,textvariable=self.status_var_folder_quant,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_folder,width=16,text='Marked files # ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_folder,width=10,textvariable=self.status_var_folder_size,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(expand=0,side='right')
        tk.Label(status_frame_folder,width=18,text='Marked files size: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')

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

        self.OrgLabel={}
        self.OrgLabel['path']='Subpath'
        self.OrgLabel['file']='File'
        self.OrgLabel['sizeH']='Size'
        self.OrgLabel['instances']='Copies'
        self.OrgLabel['ctimeH']='Change Time'

        self.groups_tree["columns"]=('pathnr','path','file','size','sizeH','ctime','dev','inode','crc','instances','ctimeH','kind')

        #pathnr,path,file,ctime,dev,inode
        #self.IndexTupleIndexesWithFnCommon=((int,0),(raw,1),(raw,2),(int,5),(int,6),(int,7))

        #'pathnr','path','file','size','sizeH','ctime','dev','inode','crc','instances','ctimeH','kind' ->
        #pathnr,path,file,ctime,dev,inode
        self.IndexTupleIndexesWithFnGroups=((int,0),(raw,1),(raw,2),(int,5),(int,6),(int,7))

        #'file','size','sizeH','ctime','dev','inode','crc','instances','instancesnum','ctimeH','kind' ->
        #file,ctime,dev,inode
        #self.IndexTupleIndexesWithFnFolder=((raw,0),(int,3),(int,4),(int,5))

        self.groups_tree["displaycolumns"]=('path','file','sizeH','instances','ctimeH')

        self.groups_tree.column('#0', width=120, minwidth=100, stretch=tk.NO)
        self.groups_tree.column('path', width=100, minwidth=10, stretch=tk.YES )
        self.groups_tree.column('file', width=100, minwidth=10, stretch=tk.YES )
        self.groups_tree.column('sizeH', width=80, minwidth=80, stretch=tk.NO)
        self.groups_tree.column('instances', width=80, minwidth=80, stretch=tk.NO)
        self.groups_tree.column('ctimeH', width=150, minwidth=100, stretch=tk.NO)

        self.groups_tree.heading('#0',text='CRC / Scan Path',anchor=tk.W)
        self.groups_tree.heading('path',anchor=tk.W )
        self.groups_tree.heading('file',anchor=tk.W )
        self.groups_tree.heading('sizeH',anchor=tk.W)
        self.groups_tree.heading('ctimeH',anchor=tk.W)
        self.groups_tree.heading('instances',anchor=tk.W)

        self.groups_tree.heading('sizeH', text='Size \u25BC')

        #bind_class breaks columns resizing
        self.groups_tree.bind('<ButtonPress-1>', self.tree_on_mouse_button_press)
        self.groups_tree.bind('<Control-ButtonPress-1>',  lambda event :self.tree_on_mouse_button_press(event,True) )
        self.main.unbind_class('Treeview', '<<TreeviewClose>>')

        self.col2sortOf={}
        self.col2sortOf['path'] = 'path'
        self.col2sortOf['file'] = 'file'
        self.col2sortOf['sizeH'] = 'size'
        self.col2sortOf['ctimeH'] = 'ctime'
        self.col2sortOf['instances'] = 'instances'

        self.col2sortNumeric={}
        self.col2sortNumeric['path'] = False
        self.col2sortNumeric['file'] = False
        self.col2sortNumeric['sizeH'] = True
        self.col2sortNumeric['ctimeH'] = True
        self.col2sortNumeric['instances'] = True

        self.col2sortLev2={}
        self.col2sortLev2['path'] = True
        self.col2sortLev2['file'] = True
        self.col2sortLev2['sizeH'] = True
        self.col2sortLev2['ctimeH'] = True
        self.col2sortLev2['instances'] = False

        vsb1 = tk.Scrollbar(frame_groups, orient='vertical', command=self.groups_tree.yview,takefocus=False,bg=self.bg)
        self.groups_tree.configure(yscrollcommand=vsb1.set)

        vsb1.pack(side='right',fill='y',expand=0)
        self.groups_tree.pack(fill='both',expand=1, side='left')

        self.groups_tree.bind('<Double-Button-1>', self.double_left_button)

        self.folder_tree=ttk.Treeview(frame_folder,takefocus=True,selectmode='none')

        self.folder_tree['columns']=('file','size','sizeH','ctime','dev','inode','crc','instances','instancesnum','ctimeH','kind')

        self.folder_tree['displaycolumns']=('file','sizeH','instances','ctimeH')

        self.folder_tree.column('#0', width=120, minwidth=100, stretch=tk.NO)

        self.folder_tree.column('file', width=200, minwidth=100, stretch=tk.YES)
        self.folder_tree.column('sizeH', width=80, minwidth=80, stretch=tk.NO)
        self.folder_tree.column('instances', width=80, minwidth=80, stretch=tk.NO)
        self.folder_tree.column('ctimeH', width=150, minwidth=100, stretch=tk.NO)

        self.folder_tree.heading('#0',text='CRC',anchor=tk.W)
        self.folder_tree.heading('file',anchor=tk.W)
        self.folder_tree.heading('sizeH',anchor=tk.W)
        self.folder_tree.heading('ctimeH',anchor=tk.W)
        self.folder_tree.heading('instances',anchor=tk.W)

        for tree in [self.groups_tree,self.folder_tree]:
            for col in tree["displaycolumns"]:
                if col in self.OrgLabel:
                    tree.heading(col,text=self.OrgLabel[col])

        self.folder_tree.heading('file', text='File \u25B2')

        vsb2 = tk.Scrollbar(frame_folder, orient='vertical', command=self.folder_tree.yview,takefocus=False,bg=self.bg)
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
        self.folder_tree.tag_configure(LINK, foreground='darkgray')

        #bind_class breaks columns resizing
        self.folder_tree.bind('<ButtonPress-1>', self.tree_on_mouse_button_press)
        self.folder_tree.bind('<Control-ButtonPress-1>',  lambda event :self.tree_on_mouse_button_press(event,True) )

        try:
            self.main.update()
            CfgGeometry=self.cfg.get('main','',section='geometry')

            if CfgGeometry:
                self.main.geometry(CfgGeometry)
            else:
                x = int(0.5*(self.main.winfo_screenwidth()-self.main.winfo_width()))
                y = int(0.5*(self.main.winfo_screenheight()-self.main.winfo_height()))

                self.main.geometry(f'+{x}+{y}')
                
        except Exception as e:
            self.status(str(e))
            logging.error(e)
            CfgGeometry = None

        self.main.deiconify()
        
        self.paned.update()
        self.paned.sash_place(0,0,self.cfg.get('sash_coord',400,section='geometry'))
        
        #prevent displacement
        if CfgGeometry :
            self.main.geometry(CfgGeometry)

        self.popup_groups = Menu(self.groups_tree, tearoff=0,bg=self.bg)
        self.popup_groups.bind("<FocusOut>",lambda event : self.popup_groups.unpost() )

        self.PopupFolder = Menu(self.folder_tree, tearoff=0,bg=self.bg)
        self.PopupFolder.bind("<FocusOut>",lambda event : self.PopupFolder.unpost() )

        #######################################################################
        #scan dialog

        def pre_show():
            self.menu_disable()
            self.menubar.config(cursor="watch")
        
        def post_close():
            self.menu_enable()
            self.menubar.config(cursor="")

        self.scan_dialog=GenericDialog(self.main,self.iconphoto,self.bg,'Scan',pre_show=pre_show,post_close=post_close)
        
        self.WriteScanToLog=tk.BooleanVar()
        self.WriteScanToLog.set(False)

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
        self.pathsFrame = tk.LabelFrame(self.scan_dialog.area_main,text='Paths To scan:',borderwidth=2,bg=self.bg)
        self.pathsFrame.grid(row=0,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        self.AddPathButton = ttk.Button(self.pathsFrame,width=18,text="Add Path ...",command=self.path_to_scan_add_dialog,underline=0)
        self.AddPathButton.grid(column=0, row=100,pady=4,padx=4)

        #self.AddDrivesButton = ttk.Button(self.pathsFrame,width=10,text="Add drives",command=self.AddDrives,underline=4)
        #self.AddDrivesButton.grid(column=1, row=100,pady=4,padx=4)

        self.ClearListButton=ttk.Button(self.pathsFrame,width=10,text="Clear List",command=self.scan_paths_clear )
        self.ClearListButton.grid(column=2, row=100,pady=4,padx=4)

        self.pathsFrame.grid_columnconfigure(1, weight=1)
        self.pathsFrame.grid_rowconfigure(99, weight=1)

        ##############
        self.exclude_regexp_scan=tk.BooleanVar()

        self.exclude_frame = tk.LabelFrame(self.scan_dialog.area_main,text='Exclude from scan:',borderwidth=2,bg=self.bg)
        self.exclude_frame.grid(row=1,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        self.AddExckludeMaskButton = ttk.Button(self.exclude_frame,width=18,text="Add Exclude Mask ...",command=self.exclude_mask_add_dialog,underline=4)
        self.AddExckludeMaskButton.grid(column=0, row=100,pady=4,padx=4)

        self.ClearExcludeListButton=ttk.Button(self.exclude_frame,width=10,text="Clear List",command=self.exclude_masks_clear )
        self.ClearExcludeListButton.grid(column=2, row=100,pady=4,padx=4)

        self.exclude_frame.grid_columnconfigure(1, weight=1)
        self.exclude_frame.grid_rowconfigure(99, weight=1)
        ##############

        ttk.Checkbutton(self.scan_dialog.area_main,text='write scan results to application log',variable=self.WriteScanToLog).grid(row=3,column=0,sticky='news',padx=8,pady=3,columnspan=3)

        self.ScanButton = ttk.Button(self.scan_dialog.area_buttons,width=12,text="Scan",command=self.scan_from_button,underline=0)
        self.ScanButton.pack(side='right',padx=4,pady=4)
        
        self.scan_cancel_button = ttk.Button(self.scan_dialog.area_buttons,width=12,text="Cancel",command=self.scan_dialog.hide,underline=0)
        self.scan_cancel_button.pack(side='left',padx=4,pady=4)
        
        def pre_show_settings():
            pre_show()
            {var.set(self.cfg.get_bool(key)) for var,key in self.settings}
            
        #######################################################################
        #Settings Dialog
        self.SettingsDialog=GenericDialog(self.main,self.iconphoto,self.bg,'Settings',pre_show=pre_show_settings,post_close=post_close)
        
        self.FullCRC = tk.BooleanVar()
        self.FullPaths = tk.BooleanVar()
        self.RelSymlinks = tk.BooleanVar()
        self.EraseEmptyDirs = tk.BooleanVar()

        self.AllowDeleteAll = tk.BooleanVar()
        self.SkipIncorrectGroups = tk.BooleanVar()
        self.AllowDeleteNonDuplicates = tk.BooleanVar()

        self.ConfirmShowCrcSize = tk.BooleanVar()
        self.ConfirmShowLinksTargets = tk.BooleanVar()

        self.settings = [
            (self.FullCRC,CFG_KEY_FULL_CRC),
            (self.FullPaths,CFG_KEY_FULL_PATHS),
            (self.RelSymlinks,CFG_KEY_REL_SYMLINKS),
            (self.EraseEmptyDirs,ERASE_EMPTY_DIRS),
            (self.ConfirmShowCrcSize,CFG_CONFIRM_SHOW_CRCSIZE),
            (self.ConfirmShowLinksTargets,CFG_CONFIRM_SHOW_LINKSTARGETS),
            (self.AllowDeleteAll,CFG_ALLOW_DELETE_ALL),
            (self.SkipIncorrectGroups,CFG_SKIP_INCORRECT_GROUPS),
            (self.AllowDeleteNonDuplicates,CFG_ALLOW_DELETE_NON_DUPLICATES)
        ]

        row = 0
        lf=tk.LabelFrame(self.SettingsDialog.area_main, text="Main panels",borderwidth=2,bg=self.bg)
        lf.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

        ttk.Checkbutton(lf, text = 'show full CRC', variable=self.FullCRC                                       ).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
        ttk.Checkbutton(lf, text = 'show full scan paths', variable=self.FullPaths                              ).grid(row=1,column=0,sticky='wens',padx=3,pady=2)
        
        lf=tk.LabelFrame(self.SettingsDialog.area_main, text="Confirmation dialogs",borderwidth=2,bg=self.bg)
        lf.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1
        
        ttk.Checkbutton(lf, text = 'Allow to delete all copies (WARNING!)', variable=self.AllowDeleteAll                  ).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
        ttk.Checkbutton(lf, text = 'Skip groups with invalid selection', variable=self.SkipIncorrectGroups                  ).grid(row=1,column=0,sticky='wens',padx=3,pady=2)
        ttk.Checkbutton(lf, text = 'show soft links targets', variable=self.ConfirmShowLinksTargets                  ).grid(row=2,column=0,sticky='wens',padx=3,pady=2)
        ttk.Checkbutton(lf, text = 'show CRC and size', variable=self.ConfirmShowCrcSize                  ).grid(row=3,column=0,sticky='wens',padx=3,pady=2)
                
        lf=tk.LabelFrame(self.SettingsDialog.area_main, text="Processing",borderwidth=2,bg=self.bg)
        lf.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1
        
        ttk.Checkbutton(lf, text = 'Create relative symbolic links', variable=self.RelSymlinks                  ).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
        ttk.Checkbutton(lf, text = 'Erase remaining empty directories', variable=self.EraseEmptyDirs                  ).grid(row=1,column=0,sticky='wens',padx=3,pady=2)

        #ttk.Checkbutton(fr, text = 'Allow to delete regular files (WARNING!)', variable=self.AllowDeleteNonDuplicates        ).grid(row=row,column=0,sticky='wens',padx=3,pady=2)

        bfr=tk.Frame(self.SettingsDialog.area_main,bg=self.bg)
        self.SettingsDialog.area_main.grid_rowconfigure(row, weight=1); row+=1

        bfr.grid(row=row,column=0) ; row+=1

        ttk.Button(bfr, text='Set defaults',width=14, command=self.settings_reset).pack(side='left', anchor='n',padx=5,pady=5)
        ttk.Button(bfr, text='OK', width=14, command=self.settings_ok ).pack(side='left', anchor='n',padx=5,pady=5)
        self.cancel_button=ttk.Button(bfr, text='Cancel', width=14 ,command=self.SettingsDialog.hide )
        self.cancel_button.pack(side='right', anchor='n',padx=5,pady=5)

        self.SettingsDialog.area_main.grid_columnconfigure(0, weight=1)

        #######################################################################
        self.info_dialog_on_main = LabelDialog(self.main,self.iconphoto,self.bg,pre_show=pre_show,post_close=post_close)
        self.text_ask_dialog = TextDialogQuestion(self.main,self.iconphoto,self.bg,pre_show=pre_show,post_close=post_close)
        self.info_dialog_on_scan = LabelDialog(self.scan_dialog.widget,self.iconphoto,self.bg,pre_show=pre_show,post_close=post_close)
        self.exclude_dialog_on_scan = EntryDialogQuestion(self.scan_dialog.widget,self.iconphoto,self.bg,pre_show=pre_show,post_close=post_close)
        self.mark_dialog_on_main = CheckboxEntryDialogQuestion(self.main,self.iconphoto,self.bg,pre_show=pre_show,post_close=post_close)
        self.find_dialog_on_main = FindEntryDialog(self.main,self.iconphoto,self.bg,self.find_mod,self.find_prev_from_dialog,self.find_next_from_dialog,pre_show=pre_show,post_close=post_close)
        self.info_dialog_on_find = LabelDialog(self.find_dialog_on_main.widget,self.iconphoto,self.bg,pre_show=pre_show,post_close=post_close)
        
       #######################################################################
        #About Dialog
        self.AboutDialog=GenericDialog(self.main,self.iconphoto,self.bg,'About',pre_show=pre_show,post_close=post_close)
        
        frame1 = tk.LabelFrame(self.AboutDialog.area_main,text='',bd=2,bg=self.bg,takefocus=False)
        frame1.grid(row=0,column=0,sticky='news',padx=4,pady=(4,2))
        self.AboutDialog.area_main.grid_rowconfigure(1, weight=1)
        
        text= f'\n\nDUDE (DUplicates DEtector) v{version.VERSION}\nAuthor: Piotr Jochymek\n\n{HOMEPAGE}\n\nPJ.soft.dev.x@gmail.com\n\n' 

        tk.Label(frame1,text=text,bg=self.bg,justify='center').pack(expand=1,fill='both')
        
        AboutFrame2 = tk.LabelFrame(self.AboutDialog.area_main,text='',bd=2,bg=self.bg,takefocus=False)
        AboutFrame2.grid(row=1,column=0,sticky='news',padx=4,pady=(2,4))
        lab2_text=  'LOGS DIRECTORY     :  ' + LOG_DIR + '\n' + \
                    'SETTINGS DIRECTORY :  ' + CONFIG_DIR + '\n' + \
                    'CACHE DIRECTORY    :  ' + CACHE_DIR + '\n\n' + \
                    'LOGGING LEVEL      :  ' + log_levels[log_level] + '\n\n' + \
                    'Current log file   :  ' + log 

        lab_courier = tk.Label(AboutFrame2,text=lab2_text,bg=self.bg,justify='left')
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
        try:
            self.license=pathlib.Path(os.path.join(os.path.dirname(__file__),'LICENSE')).read_text()
        except Exception as e:
            logging.error(e)
            try:
                self.license=pathlib.Path(os.path.join(os.path.dirname(os.path.dirname(__file__)),'LICENSE')).read_text()
            except Exception as e:
                logging.error(e)
                self.exit()
        
        self.LicenseDialog=GenericDialog(self.main,self.iconphoto,self.bg,'License',pre_show=pre_show,post_close=post_close,min_width=800,min_height=520)
        
        frame1 = tk.LabelFrame(self.LicenseDialog.area_main,text='',bd=2,bg=self.bg,takefocus=False)
        frame1.grid(row=0,column=0,sticky='news',padx=4,pady=4)
        self.LicenseDialog.area_main.grid_rowconfigure(0, weight=1)
        
        lab_courier=tk.Label(frame1,text=self.license,bg=self.bg,justify='center')
        lab_courier.pack(expand=1,fill='both')
        
        try:
            lab_courier.configure(font=('Courier', 10))
        except:
            try:
                lab_courier.configure(font=('TkFixedFont', 10))
            except:
                pass
        
        def file_cascade_post():
            self.file_cascade.delete(0,END)
            ItemActionsState=('disabled','normal')[self.sel_item!=None]

            self.file_cascade.add_command(label = 'scan',command = self.scan_dialog_show, accelerator="S")
            self.file_cascade.add_separator()
            self.file_cascade.add_command(label = 'Settings',command= lambda : self.SettingsDialog.show(focus=self.cancel_button), accelerator="F2")
            self.file_cascade.add_separator()
            self.file_cascade.add_command(label = 'Remove empty folders in specified directory ...',command=lambda : self.empty_folder_remove_ask())
            self.file_cascade.add_separator()
            self.file_cascade.add_command(label = 'Erase CRC Cache',command = self.cache_clean)
            self.file_cascade.add_separator()
            self.file_cascade.add_command(label = 'Exit',command = self.exit)

        self.file_cascade= Menu(self.menubar,tearoff=0,bg=self.bg,postcommand=file_cascade_post)
        self.menubar.add_cascade(label = 'File',menu = self.file_cascade,accelerator="Alt+F")

        def navi_cascade_post():
            self.navi_cascade.delete(0,END)
            ItemActionsState=('disabled','normal')[self.sel_item!=None]
            self.navi_cascade.add_command(label = 'Go to dominant group (by size sum)',command = lambda : self.goto_max_group(1), accelerator="F7",state=ItemActionsState)
            self.navi_cascade.add_command(label = 'Go to dominant group (by quantity)',command = lambda : self.goto_max_group(0), accelerator="F8",state=ItemActionsState)
            self.navi_cascade.add_separator()
            self.navi_cascade.add_command(label = 'Go to dominant folder (by size sum)',command = lambda : self.goto_max_folder(1),accelerator="F5",state=ItemActionsState)
            self.navi_cascade.add_command(label = 'Go to dominant folder (by quantity)',command = lambda : self.goto_max_folder(0), accelerator="F6",state=ItemActionsState)
            self.navi_cascade.add_separator()
            self.navi_cascade.add_command(label = 'Go to next marked file'       ,command = lambda : self.goto_next_mark_menu(1,0),accelerator="Right",state=ItemActionsState)
            self.navi_cascade.add_command(label = 'Go to previous marked file'   ,command = lambda : self.goto_next_mark_menu(-1,0), accelerator="Left",state=ItemActionsState)
            self.navi_cascade.add_separator()
            self.navi_cascade.add_command(label = 'Go to next not marked file'       ,command = lambda : self.goto_next_mark_menu(1,1),accelerator="Shift+Right",state=ItemActionsState)
            self.navi_cascade.add_command(label = 'Go to previous not marked file'   ,command = lambda : self.goto_next_mark_menu(-1,1), accelerator="Shift+Left",state=ItemActionsState)

            #self.navi_cascade.add_separator()
            #self.navi_cascade.add_command(label = 'Go to dominant folder (by duplicates/other files size ratio)',command = lambda : self.goto_max_folder(1,1),accelerator="Backspace",state=ItemActionsState)
            #self.navi_cascade.add_command(label = 'Go to dominant folder (by duplicates/other files quantity ratio)',command = lambda : self.goto_max_folder(0,1), accelerator="Ctrl+Backspace",state=ItemActionsState)

        self.navi_cascade= Menu(self.menubar,tearoff=0,bg=self.bg,postcommand=navi_cascade_post)

        self.menubar.add_cascade(label = 'Navigation',menu = self.navi_cascade)

        self.HelpCascade= Menu(self.menubar,tearoff=0,bg=self.bg)
        self.HelpCascade.add_command(label = 'About',command=self.AboutDialog.show,accelerator="F1")
        self.HelpCascade.add_command(label = 'License',command=self.LicenseDialog.show)
        self.HelpCascade.add_separator()
        self.HelpCascade.add_command(label = 'Open current Log',command=self.show_log)
        self.HelpCascade.add_command(label = 'Open logs directory',command=self.show_logs_dir)
        self.HelpCascade.add_separator()
        self.HelpCascade.add_command(label = 'Open homepage',command=self.show_homepage)

        self.menubar.add_cascade(label = 'Help',menu = self.HelpCascade)

        #######################################################################
        self.reset_sels()

        self.column_sort_last_params={}
        self.column_sort_last_params[self.groups_tree]=self.ColumnSortLastParamsDefault=('sizeH',1)
        self.column_sort_last_params[self.folder_tree]=('file',0)

        self.sel_item_of_tree[self.groups_tree]=None
        self.sel_item_of_tree[self.folder_tree]=None
        
        self.groups_show()
        
        #######################################################################
        
        self.tooltip = tk.Toplevel(self.main)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip_lab=tk.Label(self.tooltip, justify='left', background="#ffffe0", relief='solid', borderwidth=0, wraplength = 1200)
        self.tooltip_lab.pack(ipadx=1)
        
        self.tooltip.withdraw()
        
        #self.groups_tree.bind("<Motion>", self.motion_on_groups_tree)
        #self.folder_tree.bind("<Motion>", self.motion_on_folder_tree)
        
        self.groups_tree.bind("<Leave>", self.tree_leave)
        self.folder_tree.bind("<Leave>", self.tree_leave)
        
        #######################################################################
        
        if pathsToAdd:
            for path in pathsToAdd:
                self.path_to_scan_add(os.path.abspath(path))
        
        run_scan_condition = True if (pathsToAdd and not norun) else False
        
        if exclude:
            self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(exclude))
            self.cfg.set_bool(CFG_KEY_EXCLUDE_REGEXP,False)
        elif excluderegexp:
            self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(excluderegexp))
            self.cfg.set_bool(CFG_KEY_EXCLUDE_REGEXP,True)
        else:
            if run_scan_condition:
                self.cfg.set(CFG_KEY_EXCLUDE,'')

        self.exclude_regexp_scan.set(self.cfg.get_bool(CFG_KEY_EXCLUDE_REGEXP))

        self.main.update()
        
        self.scan_dialog_show(True if run_scan_condition else None)
        
        self.groups_tree.focus_set()

        self.main.mainloop()
        #######################################################################
    
    tooltip_show_after_groups=''
    tooltip_show_after_folder=''
    
    def tree_leave(self,event):
        self.menubar_unpost()
        self.hide_tooltip()
        
    def motion_on_groups_tree(self,event):
        self.tooltip_show_after_groups = event.widget.after(10, self.show_tooltip_groups(event))

    def motion_on_folder_tree(self,event):
        self.tooltip_show_after_folder = event.widget.after(10, self.show_tooltip_folder(event))
    
    def show_tooltip_groups(self,event):
        self.unschedule_tooltip_groups()
        self.menubar_unpost()
    
        if item := event.widget.identify('item', event.x, event.y):
            pathnrstr=event.widget.set(item,'pathnr')
            
            if pathnrstr:
                col=event.widget.identify_column(event.x)
                colname=event.widget.column(col,'id')
                
                pathnr=int(pathnrstr)
                path=event.widget.set(item,'path')
                file=event.widget.set(item,'file')
                file_path = os.path.abspath(self.D.get_full_path_scanned(pathnr,path,file))
                
                self.tooltip_lab.configure(text=file_path)
                self.tooltip.deiconify()
                self.tooltip.wm_geometry("+%d+%d" % (event.x_root + 20, event.y_root + 5))
                
                #if col=="#0" :
                #else:
                    
    def show_tooltip_folder(self,event):
        self.unschedule_tooltip_folder()
        self.menubar_unpost()
        
        if item := event.widget.identify('item', event.x, event.y):
            #file_path = self.item_full_path(item)
            
            col=event.widget.identify_column(event.x)
            colname=event.widget.column(col,'id')

            #print(col,colname)
            #values = event.widget.item(item)['values']
            #print(values)
            #if event.widget.identify("region", event.x, event.y) == 'heading':
            
            self.tooltip_lab.configure(text='TODO')
            self.tooltip.deiconify()
            self.tooltip.wm_geometry("+%d+%d" % (event.x_root + 20, event.y_root + 5))
        
    def unschedule_tooltip_groups(self):
        id = self.tooltip_show_after_groups
        self.tooltip_show_after_groups = None
        if id:
            self.widget.after_cancel(id)
    def unschedule_tooltip_folder(self):
        id = self.tooltip_show_after_folder
        self.tooltip_show_after_folder = None
        if id:
            self.widget.after_cancel(id)
            
    def hide_tooltip(self):
        self.tooltip.withdraw()
        
    def status(self,text):
        self.status_line.set(text)
        self.StatusLineLabel.update()

    menu_state_stack=[]
    def menu_enable(self):
        self.menu_state_stack.pop(0)
        if not len(self.menu_state_stack):
            self.menubar.entryconfig("File", state="normal")
            self.menubar.entryconfig("Navigation", state="normal")
            self.menubar.entryconfig("Help", state="normal")

    def menu_disable(self):
        self.menubar.entryconfig("File", state="disabled")
        self.menubar.entryconfig("Navigation", state="disabled")
        self.menubar.entryconfig("Help", state="disabled")
        self.menu_state_stack.append('x')
        #self.menubar.update()

    sel_item_of_tree = {}

    def reset_sels(self):
        self.sel_path_nr = None
        self.sel_path = None
        self.sel_file = None
        self.SelCrc = None
        self.sel_item = None
        self.SelItemIsMarked = False

        self.sel_item_of_tree[self.groups_tree]=None
        self.sel_item_of_tree[self.folder_tree]=None
        self.FullPathToFile = None

        self.SelTreeIndex = 0
        self.SelKind = None

    def get_index_tuple_groups_tree(self,item):
        return tuple([ fn(self.groups_tree.item(item)['values'][index]) for fn,index in self.IndexTupleIndexesWithFnGroups ])

    def exit(self):
        self.main_geometry_store()
        self.splitter_store()
        exit()

    def main_geometry_store(self):
        self.cfg.set('main',str(self.main.geometry()),section='geometry')
        self.cfg.write()

    find_result=()
    find_params_changed=True
    find_tree_index=-1
    
    def finder_wrapper_show(self):
        tree=self.groups_tree if self.SelTreeIndex==0 else self.folder_tree

        tree.configure(style='semi_focus.Treeview')
        self.find_dialog_shown=True
        
        ScopeInfo = 'Scope: All groups.' if self.SelTreeIndex==0 else 'Scope: Selected directory.'
        
        self.find_dialog_on_main.show(ScopeInfo,initial='*',CheckInitial=False)
        
        self.find_dialog_shown=False
        tree.configure(style='default.Treeview')

        selList=tree.selection()

        self.from_tab_switch=True
        tree.focus_set()

    def find_prev_from_dialog(self,expression,use_reg_expr,event=None):
        self.find_items(expression,use_reg_expr)
        self.select_find_result(-1)
    
    def find_prev(self):
        if not self.find_result or self.find_tree_index!=self.SelTreeIndex:
            self.find_params_changed=True
            self.finder_wrapper_show()
        else:
            self.select_find_result(-1)

    def find_next_from_dialog(self,expression,use_reg_expr,event=None):
        self.find_items(expression,use_reg_expr)
        self.select_find_result(1)
        
    def find_next(self):
        if not self.find_result or self.find_tree_index!=self.SelTreeIndex:
            self.find_params_changed=True
            self.finder_wrapper_show()
        else:
            self.select_find_result(1)

    find_result_index=0
    find_tree=''
    find_dialog_shown=False
    use_reg_expr_prev=''
    find_expression_prev=''

    ##################################################
    def find_mod(self,expression,use_reg_expr,event=None):
        if self.use_reg_expr_prev!=use_reg_expr or self.find_expression_prev!=expression:
            self.use_reg_expr_prev=use_reg_expr
            self.find_expression_prev=expression
            self.find_params_changed=True
            self.find_result_index=0

    def find_items(self,expression,use_reg_expr,event=None):
        if self.find_params_changed:
            self.find_tree_index=self.SelTreeIndex

            items=[]

            if expression:
                if self.SelTreeIndex==0:
                    self.find_tree=self.groups_tree
                    CrcRange = self.groups_tree.get_children()

                    try:
                        for crcitem in CrcRange:
                            for item in self.groups_tree.get_children(crcitem):
                                fullpath = self.item_full_path(item)
                                if (use_reg_expr and re.search(expression,fullpath)) or (not use_reg_expr and fnmatch.fnmatch(fullpath,expression) ):
                                    items.append(item)
                    except Exception as e:
                        self.info_dialog_on_find.show('Error',str(e),min_width=400)
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
                        self.info_dialog_on_find.show('Error',str(e),min_width=400)
                        return

            if items:
                self.find_result=tuple(items)
                self.find_params_changed=False
            else:
                ScopeInfo = 'Scope: All groups.' if self.find_tree_index==0 else 'Scope: Selected directory.'
                self.info_dialog_on_find.show(ScopeInfo,'No files found.',min_width=400)

    @busy_cursor
    def select_find_result(self,mod):
        if self.find_result:
            itemsLen=len(self.find_result)
            self.find_result_index+=mod
            NextItem=self.find_result[self.find_result_index%itemsLen]

            if self.find_dialog_shown:
                #focus is still on find dialog
                self.find_tree.selection_set(NextItem)
            else:
                self.find_tree.focus_set()
                self.find_tree.focus(NextItem)

            self.find_tree.see(NextItem)
            self.find_tree.update()

            if self.find_tree==self.groups_tree:
                self.groups_tree_sel_change(NextItem)
            else:
                self.folder_tree_sel_change(NextItem)
            
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
                return self.tag_toggle_selected(tree, *tree.get_children(item) )

        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    KEY_DIRECTION={}
    KEY_DIRECTION['Up']=-1
    KEY_DIRECTION['Down']=1
    KEY_DIRECTION['Prior']=-1
    KEY_DIRECTION['Next']=1

    reftuple1=('1','2','3','4','5','6','7')
    reftuple2=('exclam','at','numbersign','dollar','percent','asciicircum','ampersand')

    #@busy_cursor
    def key_press(self,event):
        if not self.do_process_events:
            return

        self.main.unbind_class('Treeview','<KeyPress>')

        try:
            tree=event.widget
            item=tree.focus()

            if sel:=tree.selection() : tree.selection_remove(sel)

            if event.keysym in ("Up",'Down') :
                (pool,poolLen) = (self.tree_groups_flat_items,len(self.tree_groups_flat_items) ) if self.SelTreeIndex==0 else (self.TreeFolderFlatItemsList,len(self.TreeFolderFlatItemsList))

                if poolLen:
                    index = pool.index(self.sel_item) if self.sel_item in pool else pool.index(self.sel_item_of_tree[tree]) if self.sel_item_of_tree[tree] in pool else pool.index(item) if item in  pool else 0
                    index=(index+self.KEY_DIRECTION[event.keysym])%poolLen
                    NextItem=pool[index]

                    tree.focus(NextItem)
                    tree.see(NextItem)

                    if self.SelTreeIndex==0:
                        self.groups_tree_sel_change(NextItem)
                    else:
                        self.folder_tree_sel_change(NextItem)
            elif event.keysym in ("Prior","Next"):
                if self.SelTreeIndex==0:
                    pool=tree.get_children()
                else:
                    pool=[item for item in tree.get_children() if tree.set(item,'kind')==FILE]

                poolLen=len(pool)
                if poolLen:
                    if self.SelTreeIndex==0:
                        NextItem=pool[(pool.index(tree.set(item,'crc'))+self.KEY_DIRECTION[event.keysym]) % poolLen]
                        self.crc_select_and_focus(NextItem)
                    else:
                        self.goto_next_dupe_file(tree,self.KEY_DIRECTION[event.keysym])
                        tree.update()
            elif event.keysym in ("Home","End"):
                if self.SelTreeIndex==0:
                    if NextItem:=tree.get_children()[0 if event.keysym=="Home" else -1]:
                        self.crc_select_and_focus(NextItem,True)
                else:
                    if NextItem:=tree.get_children()[0 if event.keysym=='Home' else -1]:
                        tree.see(NextItem)
                        tree.focus(NextItem)
                        self.folder_tree_sel_change(NextItem)
                        tree.update()
            elif event.keysym == "space":
                if self.SelTreeIndex==0:
                    if tree.set(item,'kind')==CRC:
                        self.tag_toggle_selected(tree,*tree.get_children(item))
                    else:
                        self.tag_toggle_selected(tree,item)
                else:
                    self.tag_toggle_selected(tree,item)
            elif event.keysym == "Tab":
                tree.selection_set(tree.focus())
                self.from_tab_switch=True
            elif event.keysym=='KP_Multiply' or event.keysym=='asterisk':
                self.mark_on_all(self.invert_mark)
            elif event.keysym=='Return':
                item=tree.focus()
                if item:
                    self.tree_action(tree,item)
            else:
                StrEvent=str(event)

                ctrl_pressed = 'Control' in StrEvent
                shift_pressed = 'Shift' in StrEvent

                if event.keysym=='F3':
                    if shift_pressed:
                        self.find_prev()
                    else:
                        self.find_next()
                elif event.keysym == "Right":
                    self.goto_next_mark(event.widget,1,shift_pressed)
                elif event.keysym == "Left":
                    self.goto_next_mark(event.widget,-1,shift_pressed)
                elif event.keysym=='KP_Add' or event.keysym=='plus':
                    StrEvent=str(event)
                    self.mark_expression(self.set_mark,'Mark files',ctrl_pressed)
                elif event.keysym=='KP_Subtract' or event.keysym=='minus':
                    StrEvent=str(event)
                    self.mark_expression(self.unset_mark,'Unmark files',ctrl_pressed)
                elif event.keysym == "Delete":
                    if self.SelTreeIndex==0:
                        self.process_files_in_groups_wrapper(DELETE,ctrl_pressed)
                    else:
                        self.process_files_in_folder_wrapper(DELETE,self.SelKind==DIR)
                elif event.keysym == "Insert":
                    if self.SelTreeIndex==0:
                        self.process_files_in_groups_wrapper((SOFTLINK,HARDLINK)[shift_pressed],ctrl_pressed)
                    else:
                        self.process_files_in_folder_wrapper((SOFTLINK,HARDLINK)[shift_pressed],self.SelKind==DIR)
                elif event.keysym=='F5':
                    self.goto_max_folder(0,-1 if shift_pressed else 1)
                elif event.keysym=='F6':
                    self.goto_max_folder(1,-1 if shift_pressed else 1)
                elif event.keysym=='F7':
                    self.goto_max_group(0,-1 if shift_pressed else 1)
                elif event.keysym=='F8':
                    self.goto_max_group(1,-1 if shift_pressed else 1)
                elif event.keysym=='BackSpace':
                    self.go_to_parent_dir()
                elif event.keysym=='i' or event.keysym=='I':
                    if ctrl_pressed:
                        self.mark_on_all(self.invert_mark)
                    else:
                        if self.SelTreeIndex==0:
                            self.mark_in_group(self.invert_mark)
                        else:
                            self.mark_in_folder(self.invert_mark)
                elif event.keysym=='o' or event.keysym=='O':
                    if ctrl_pressed:
                        if shift_pressed:
                            self.mark_all_by_ctime('oldest',self.unset_mark)
                        else:
                            self.mark_all_by_ctime('oldest',self.set_mark)
                    else:
                        if self.SelTreeIndex==0:
                            self.mark_in_group_by_ctime('oldest',self.invert_mark)
                elif event.keysym=='y' or event.keysym=='Y':
                    if ctrl_pressed:
                        if shift_pressed:
                            self.mark_all_by_ctime('youngest',self.unset_mark)
                        else:
                            self.mark_all_by_ctime('youngest',self.set_mark)
                    else:
                        if self.SelTreeIndex==0:
                            self.mark_in_group_by_ctime('youngest',self.invert_mark)
                elif event.keysym=='c' or event.keysym=='C':
                    if ctrl_pressed:
                        if shift_pressed:
                            self.clip_copy_file()
                        else:
                            self.clip_copy_full_path_with_file()
                    else:
                        self.clip_copy_full()

                elif event.keysym=='a' or event.keysym=='A':
                    if self.SelTreeIndex==0:
                        if ctrl_pressed:
                            self.mark_on_all(self.set_mark)
                        else:
                            self.mark_in_group(self.set_mark)
                    else:
                        self.mark_in_folder(self.set_mark)

                elif event.keysym=='n' or event.keysym=='N':
                    if self.SelTreeIndex==0:
                        if ctrl_pressed:
                            self.mark_on_all(self.unset_mark)
                        else:
                            self.mark_in_group(self.unset_mark)
                    else:
                        self.mark_in_folder(self.unset_mark)
                elif event.keysym=='r' or event.keysym=='R':
                    if self.SelTreeIndex==1:
                        self.tree_folder_update()
                        self.folder_tree.focus_set()
                        try:
                            self.folder_tree.focus(self.sel_item)
                        except Exception :
                            pass
                elif event.keysym in self.reftuple1:
                    index = self.reftuple1.index(event.keysym)

                    if index<len(self.D.ScannedPaths):
                        if self.SelTreeIndex==0:
                            self.action_on_path(self.D.ScannedPaths[index],self.set_mark,ctrl_pressed)
                elif event.keysym in self.reftuple2:
                    index = self.reftuple2.index(event.keysym)

                    if index<len(self.D.ScannedPaths):
                        if self.SelTreeIndex==0:
                            self.action_on_path(self.D.ScannedPaths[index],self.unset_mark,ctrl_pressed)
                elif event.keysym=='KP_Divide' or event.keysym=='slash':
                    self.mark_subpath(self.set_mark,True)
                elif event.keysym=='question':
                    self.mark_subpath(self.unset_mark,True)
                elif event.keysym=='f' or event.keysym=='F':
                    self.finder_wrapper_show()
        except Exception :
            pass

        self.main.bind_class('Treeview','<KeyPress>', self.key_press )

    def go_to_parent_dir(self):
        if self.sel_path_full :
            if self.two_dots_condition():
                self.folder_tree.focus_set()
                head,tail=os.path.split(self.sel_path_full)
                self.enter_dir(os.path.normpath(str(pathlib.Path(self.sel_path_full).parent.absolute())),tail)
                
#################################################
    def crc_select_and_focus(self,crc,TryToShowAll=False):
        self.groups_tree.focus_set()

        if TryToShowAll:
            lastChild=self.groups_tree.get_children(crc)[-1]
            self.groups_tree.see(lastChild)
            self.groups_tree.update()

        self.groups_tree.see(crc)
        self.groups_tree.focus(crc)
        self.groups_tree.update()
        self.groups_tree_sel_change(crc)

    def tree_on_mouse_button_press(self,event,toggle=False):
        self.menubar_unpost()

        if not self.do_process_events:
            return

        tree=event.widget

        if tree.identify("region", event.x, event.y) == 'heading':
            if (colname:=tree.column(tree.identify_column(event.x),'id') ) in self.col2sortOf:
                self.column_sort_click(tree,colname)

                if self.SelKind==FILE:
                    tree.focus_set()

                    tree.focus(self.sel_item)
                    tree.see(self.sel_item)

                    if tree==self.groups_tree:
                        self.groups_tree_sel_change(self.sel_item)
                    else:
                        self.folder_tree_sel_change(self.sel_item)

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

    from_tab_switch=False
    def tree_on_focus_in(self,event):
        tree=event.widget

        item=None

        if sel:=tree.selection():
            tree.selection_remove(sel)
            item=sel[0]
        
        if self.from_tab_switch:
            self.from_tab_switch=False
            
            if not item:
                item=tree.focus()

            if item:
                tree.focus(item)
                if tree==self.groups_tree:
                    self.groups_tree_sel_change(item,True)
                else:
                    self.folder_tree_sel_change(item)

                tree.see(item)

        if len(self.folder_tree.get_children())==0:
            self.groups_tree.selection_remove(self.groups_tree.selection())
            self.groups_tree.focus_set()

    def tree_focus_out(self,event):
        tree=event.widget
        tree.selection_set(tree.focus())

    def set_full_path_to_file_win(self):
        self.SelFullPathToFile=pathlib.Path(os.sep.join([self.sel_path_full,self.sel_file])) if self.sel_path_full and self.sel_file else None

    def set_full_path_to_file_lin(self):
        self.SelFullPathToFile=(self.sel_path_full+self.sel_file if self.sel_path_full=='/' else os.sep.join([self.sel_path_full,self.sel_file])) if self.sel_path_full and self.sel_file else None

    set_full_path_to_file = set_full_path_to_file_win if windows else set_full_path_to_file_lin

    def sel_path_set(self,path):
        if self.sel_path_full != path:
            self.sel_path_full = path

            self.dominant_groups_folder[0] = -1
            self.dominant_groups_folder[1] = -1

    def groups_tree_sel_change(self,item,force=False,ChangeStatusLine=True):
        if ChangeStatusLine : self.status('')

        pathnr=self.groups_tree.set(item,'pathnr')
        path=self.groups_tree.set(item,'path')

        self.sel_file = self.groups_tree.set(item,'file')
        newCrc = self.groups_tree.set(item,'crc')

        if self.SelCrc != newCrc:
            self.SelCrc = newCrc

            self.dominant_groups_index[0] = -1
            self.dominant_groups_index[1] = -1

        self.sel_item = item
        self.sel_item_of_tree[self.groups_tree]=item
        self.SelTreeIndex=0

        self.SelItemIsMarked = self.groups_tree.tag_has(MARK,item)

        size = int(self.groups_tree.set(item,'size'))

        if path!=self.sel_path or pathnr!=self.sel_path_nr or force:
            self.sel_path_nr = pathnr
            
            if self.find_tree_index==1:
                self.find_result=()
            
            if pathnr: #non crc node
                self.SelPathnrInt= int(pathnr)
                self.SelSearchPath = self.D.ScannedPaths[self.SelPathnrInt]
                self.sel_path = path
                self.sel_path_set(self.SelSearchPath+self.sel_path)
            else :
                self.SelPathnrInt= 0
                self.SelSearchPath = None
                self.sel_path = None
                self.sel_path_set(None)
            self.set_full_path_to_file()

        self.SelKind = self.groups_tree.set(item,'kind')
        if self.SelKind==FILE:
            self.set_status_var()
            self.tree_folder_update()
        else:
            self.tree_folder_update_none()

    def folder_tree_sel_change(self,item,ChangeStatusLine=True):
        self.sel_file = self.folder_tree.set(item,'file')
        self.SelCrc = self.folder_tree.set(item,'crc')
        self.SelKind = self.folder_tree.set(item,'kind')
        self.sel_item = item
        self.sel_item_of_tree[self.folder_tree] = item
        self.SelTreeIndex=1

        self.SelItemIsMarked = self.folder_tree.tag_has(MARK,item)

        self.set_full_path_to_file()

        self.set_status_var()

        kind=self.folder_tree.set(item,'kind')
        if kind==FILE:
            if ChangeStatusLine: self.status('')
            self.groups_tree_update(item)
        else:
            if kind==LINK:
                if ChangeStatusLine: self.status('  🠖  ' + os.readlink(self.SelFullPathToFile))
            elif kind==SINGLEHARDLINKED:
                if ChangeStatusLine: self.status('File with hardlinks')
            elif kind==SINGLE:
                if ChangeStatusLine: self.status('')
            elif kind==DIR:
                if ChangeStatusLine: self.status('Subdirectory')
            elif kind==UPDIR:
                if ChangeStatusLine: self.status('Parent directory')

            self.groups_tree_update_none()

    def menubar_unpost(self):
        try:
            self.menubar.unpost()
        except Exception as e:
            print(e)

    @keep_semi_focus
    def context_menu_show(self,event):
        if not self.do_process_events:
            return

        self.tree_on_mouse_button_press(event)

        tree=event.widget

        ItemActionsState=('disabled','normal')[self.sel_item!=None]

        pop=self.popup_groups if tree==self.groups_tree else self.PopupFolder

        pop.delete(0,END)

        FileActionsState=('disabled',ItemActionsState)[self.SelKind==FILE]
        
        parent_dir_state = ('disabled','normal')[self.two_dots_condition() and self.SelKind!=CRC]
                    
        if tree==self.groups_tree:
            cLocal = Menu(pop,tearoff=0,bg=self.bg)
            cLocal.add_command(label = "Toggle Mark",  command = lambda : self.tag_toggle_selected(tree,self.sel_item),accelerator="space")
            cLocal.add_separator()
            cLocal.add_command(label = "Mark all files",        command = lambda : self.mark_in_group(self.set_mark),accelerator="A")
            cLocal.add_command(label = "Unmark all files",        command = lambda : self.mark_in_group(self.unset_mark),accelerator="N")
            cLocal.add_separator()
            cLocal.add_command(label = 'Mark By expression',command = lambda : self.mark_expression(self.set_mark,'Mark files',False),accelerator="+")
            cLocal.add_command(label = 'Unmark By expression',command = lambda : self.mark_expression(self.unset_mark,'Unmark files',False),accelerator="-")
            cLocal.add_separator()
            cLocal.add_command(label = "Toggle mark on oldest file",     command = lambda : self.mark_in_group_by_ctime('oldest',self.invert_mark),accelerator="O")
            cLocal.add_command(label = "Toggle mark on youngest file",   command = lambda : self.mark_in_group_by_ctime('youngest',self.invert_mark),accelerator="Y")
            cLocal.add_separator()
            cLocal.add_command(label = "Invert marks",   command = lambda : self.mark_in_group(self.invert_mark),accelerator="I")
            cLocal.add_separator()

            MarkCascadePath = Menu(cLocal, tearoff = 0,bg=self.bg)
            UnmarkCascadePath = Menu(cLocal, tearoff = 0,bg=self.bg)

            row=0
            for path in self.D.ScannedPaths:
                MarkCascadePath.add_command(label = self.NUMBERS[row] + '  =  ' + path,    command  = lambda pathpar=path: self.action_on_path(pathpar,self.set_mark,False),accelerator=str(row+1)  )
                UnmarkCascadePath.add_command(label = self.NUMBERS[row] + '  =  ' + path,  command  = lambda pathpar=path: self.action_on_path(pathpar,self.unset_mark,False),accelerator="Shift+"+str(row+1)  )
                row+=1

            cLocal.add_command(label = "Mark on specified directory ...",   command = lambda : self.mark_subpath(self.set_mark,False))
            cLocal.add_command(label = "Unmark on specified directory ...",   command = lambda : self.mark_subpath(self.unset_mark,False))
            cLocal.add_separator()

            cLocal.add_cascade(label = "Mark on scan path",             menu = MarkCascadePath)
            cLocal.add_cascade(label = "Unmark on scan path",             menu = UnmarkCascadePath)
            cLocal.add_separator()

            MarksState=('disabled','normal')[len(tree.tag_has(MARK))!=0]

            cLocal.add_command(label = 'Remove Marked Files',command=lambda : self.process_files_in_groups_wrapper(DELETE,0),accelerator="Delete",state=MarksState)
            cLocal.entryconfig(19,foreground='red',activeforeground='red')
            cLocal.add_command(label = 'Softlink Marked Files',command=lambda : self.process_files_in_groups_wrapper(SOFTLINK,0),accelerator="Insert",state=MarksState)
            cLocal.entryconfig(20,foreground='red',activeforeground='red')
            cLocal.add_command(label = 'Hardlink Marked Files',command=lambda : self.process_files_in_groups_wrapper(HARDLINK,0),accelerator="Shift+Insert",state=MarksState)
            cLocal.entryconfig(21,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'Local (this CRC group)',menu = cLocal,state=ItemActionsState)
            pop.add_separator()

            cAll = Menu(pop,tearoff=0,bg=self.bg)

            cAll.add_command(label = "Mark all files",        command = lambda : self.mark_on_all(self.set_mark),accelerator="Ctrl+A")
            cAll.add_command(label = "Unmark all files",        command = lambda : self.mark_on_all(self.unset_mark),accelerator="Ctrl+N")
            cAll.add_separator()
            cAll.add_command(label = 'Mark By expression',command = lambda : self.mark_expression(self.set_mark,'Mark files',True),accelerator="Ctrl+")
            cAll.add_command(label = 'Unmark By expression',command = lambda : self.mark_expression(self.unset_mark,'Unmark files',True),accelerator="Ctrl-")
            cAll.add_separator()
            cAll.add_command(label = "Mark Oldest files",     command = lambda : self.mark_all_by_ctime('oldest',self.set_mark),accelerator="Ctrl+O")
            cAll.add_command(label = "Unmark Oldest files",     command = lambda : self.mark_all_by_ctime('oldest',self.unset_mark),accelerator="Ctrl+Shift+O")
            cAll.add_separator()
            cAll.add_command(label = "Mark Youngest files",   command = lambda : self.mark_all_by_ctime('youngest',self.set_mark),accelerator="Ctrl+Y")
            cAll.add_command(label = "Unmark Youngest files",   command = lambda : self.mark_all_by_ctime('youngest',self.unset_mark),accelerator="Ctrl+Shift+Y")
            cAll.add_separator()
            cAll.add_command(label = "Invert marks",   command = lambda : self.mark_on_all(self.invert_mark),accelerator="Ctrl+I, *")
            cAll.add_separator()

            MarkCascadePath = Menu(cAll, tearoff = 0,bg=self.bg)
            UnmarkCascadePath = Menu(cAll, tearoff = 0,bg=self.bg)

            row=0
            for path in self.D.ScannedPaths:
                MarkCascadePath.add_command(label = self.NUMBERS[row] + '  =  ' + path,    command  = lambda pathpar=path: self.action_on_path(pathpar,self.set_mark,True) ,accelerator="Ctrl+"+str(row+1) )
                UnmarkCascadePath.add_command(label = self.NUMBERS[row] + '  =  ' + path,  command  = lambda pathpar=path: self.action_on_path(pathpar,self.unset_mark,True) ,accelerator="Ctrl+Shift+"+str(row+1) )
                row+=1

            cAll.add_command(label = "Mark on specified directory ...",   command = lambda : self.mark_subpath(self.set_mark,True))
            cAll.add_command(label = "Unmark on specified directory ...",   command = lambda : self.mark_subpath(self.unset_mark,True))
            cAll.add_separator()

            cAll.add_cascade(label = "Mark on scan path",             menu = MarkCascadePath)
            cAll.add_cascade(label = "Unmark on scan path",             menu = UnmarkCascadePath)
            cAll.add_separator()

            cAll.add_command(label = 'Remove Marked Files',command=lambda : self.process_files_in_groups_wrapper(DELETE,1),accelerator="Ctrl+Delete",state=MarksState)
            cAll.entryconfig(21,foreground='red',activeforeground='red')
            cAll.add_command(label = 'Softlink Marked Files',command=lambda : self.process_files_in_groups_wrapper(SOFTLINK,1),accelerator="Ctrl+Insert",state=MarksState)
            cAll.entryconfig(22,foreground='red',activeforeground='red')
            cAll.add_command(label = 'Hardlink Marked Files',command=lambda : self.process_files_in_groups_wrapper(HARDLINK,1),accelerator="Ctrl+Shift+Insert",state=MarksState)
            cAll.entryconfig(23,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'All Files',menu = cAll,state=ItemActionsState)

            cNav = Menu(self.menubar,tearoff=0,bg=self.bg)
            cNav.add_command(label = 'go to dominant group (by size sum)',command = lambda : self.goto_max_group(1), accelerator="F7")
            cNav.add_command(label = 'go to dominant group (by quantity)',command = lambda : self.goto_max_group(0), accelerator="F8")
            cNav.add_separator()
            cNav.add_command(label = 'Go to next marked file'       ,command = lambda : self.goto_next_mark(self.groups_tree,1,0),accelerator="Right",state='normal')
            cNav.add_command(label = 'Go to previous marked file'   ,command = lambda : self.goto_next_mark(self.groups_tree,-1,0), accelerator="Left",state='normal')
            cNav.add_separator()
            cNav.add_command(label = 'Go to next not marked file'       ,command = lambda : self.goto_next_mark(self.groups_tree,1,1),accelerator="Shift+Right",state='normal')
            cNav.add_command(label = 'Go to previous not marked file'   ,command = lambda : self.goto_next_mark(self.groups_tree,-1,1), accelerator="Shift+Left",state='normal')
            cNav.add_separator()
            cNav.add_command(label = 'Go to parent directory'   ,command = lambda : self.go_to_parent_dir(), accelerator="Backspace",state=parent_dir_state)

        else:
            DirActionsState=('disabled','normal')[self.SelKind==DIR]

            cLocal = Menu(pop,tearoff=0,bg=self.bg)
            cLocal.add_command(label = "Toggle Mark",  command = lambda : self.tag_toggle_selected(tree,self.sel_item),accelerator="space",state=FileActionsState)
            cLocal.add_separator()
            cLocal.add_command(label = "Mark all files",        command = lambda : self.mark_in_folder(self.set_mark),accelerator="A",state=FileActionsState)
            cLocal.add_command(label = "Unmark all files",        command = lambda : self.mark_in_folder(self.unset_mark),accelerator="N",state=FileActionsState)
            cLocal.add_separator()
            cLocal.add_command(label = 'Mark By expression',command = lambda : self.mark_expression(self.set_mark,'Mark files'),accelerator="+")
            cLocal.add_command(label = 'Unmark By expression',command = lambda : self.mark_expression(self.unset_mark,'Unmark files'),accelerator="-")
            cLocal.add_separator()

            MarksState=('disabled','normal')[len(tree.tag_has(MARK))!=0]

            cLocal.add_command(label = 'Remove Marked Files',command=lambda : self.process_files_in_folder_wrapper(DELETE,0),accelerator="Delete",state=MarksState)
            cLocal.add_command(label = 'Softlink Marked Files',command=lambda : self.process_files_in_folder_wrapper(SOFTLINK,0),accelerator="Insert",state=MarksState)
            #cLocal.add_command(label = 'Hardlink Marked Files',command=lambda : self.process_files_in_folder_wrapper(HARDLINK,0),accelerator="Shift+Insert",state=MarksState)

            cLocal.entryconfig(8,foreground='red',activeforeground='red')
            cLocal.entryconfig(9,foreground='red',activeforeground='red')
            #cLocal.entryconfig(10,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'Local (this folder)',menu = cLocal,state=ItemActionsState)
            pop.add_separator()

            cSelSub = Menu(pop,tearoff=0,bg=self.bg)
            cSelSub.add_command(label = "Mark All Duplicates in Subdirectory",  command = lambda : self.sel_dir(self.set_mark),accelerator="D",state=DirActionsState)
            cSelSub.add_command(label = "Unmark All Duplicates in Subdirectory",  command = lambda : self.sel_dir(self.unset_mark),accelerator="Shift+D",state=DirActionsState)
            cSelSub.add_separator()

            cSelSub.add_command(label = 'Remove Marked Files in Subdirectory Tree',command=lambda : self.process_files_in_folder_wrapper(DELETE,True),accelerator="Delete",state=DirActionsState)
            cSelSub.add_command(label = 'Softlink Marked Files in Subdirectory Tree',command=lambda : self.process_files_in_folder_wrapper(SOFTLINK,True),accelerator="Insert",state=DirActionsState)
            #cSelSub.add_command(label = 'Hardlink Marked Files in Subdirectory Tree',command=lambda : self.process_files_in_folder_wrapper(HARDLINK,True),accelerator="Shift+Insert",state=DirActionsState)

            cSelSub.entryconfig(3,foreground='red',activeforeground='red')
            cSelSub.entryconfig(4,foreground='red',activeforeground='red')
            #cSelSub.entryconfig(5,foreground='red',activeforeground='red')
            #cSelSub.add_separator()
            #cSelSub.add_command(label = 'Remove Empty Folders in Subdirectory Tree',command=lambda : self.RemoveEmptyFolders(),state=DirActionsState)

            pop.add_cascade(label = 'Selected Subdirectory',menu = cSelSub,state=DirActionsState)

            cNav = Menu(pop,tearoff=0,bg=self.bg)
            cNav.add_command(label = 'go to dominant folder (by size sum)',command = lambda : self.goto_max_folder(1),accelerator="F5")
            cNav.add_command(label = 'go to dominant folder (by quantity)',command = lambda : self.goto_max_folder(0) ,accelerator="F6")
            cNav.add_separator()
            cNav.add_command(label = 'Go to next marked file'       ,command = lambda : self.goto_next_mark(self.folder_tree,1,0),accelerator="Right",state='normal')
            cNav.add_command(label = 'Go to previous marked file'   ,command = lambda : self.goto_next_mark(self.folder_tree,-1,0), accelerator="Left",state='normal')
            cNav.add_separator()
            cNav.add_command(label = 'Go to next not marked file'       ,command = lambda : self.goto_next_mark(self.folder_tree,1,1),accelerator="Shift+Right",state='normal')
            cNav.add_command(label = 'Go to previous not marked file'   ,command = lambda : self.goto_next_mark(self.folder_tree,-1,1), accelerator="Shift+Left",state='normal')
            cNav.add_separator()
            cNav.add_command(label = 'Go to parent directory'       ,command = lambda : self.go_to_parent_dir(), accelerator="Backspace",state=parent_dir_state)
            
            #cNav.add_separator()
            #cNav.add_command(label = 'Go to dominant folder (by duplicates/other files size ratio)',command = lambda : self.goto_max_folder(1,1),accelerator="Backspace")
            #cNav.add_command(label = 'Go to dominant folder (by duplicates/other files quantity ratio)',command = lambda : self.goto_max_folder(0,1) ,accelerator="Ctrl+Backspace")

        pop.add_separator()
        pop.add_cascade(label = 'Navigation',menu = cNav,state=ItemActionsState)

        pop.add_separator()
        pop.add_command(label = 'Open File',command = self.open_file,accelerator="Return",state=FileActionsState)
        pop.add_command(label = 'Open Folder',command = self.open_folder,state=FileActionsState)

        pop.add_separator()
        pop.add_command(label = "scan",  command = self.scan_dialog_show,accelerator="S")
        pop.add_command(label = "Settings",  command = lambda : self.SettingsDialog.show(focus=self.cancel_button),accelerator="F2")
        pop.add_separator()
        pop.add_command(label = 'Copy',command = self.clip_copy_full_path_with_file,accelerator="Ctrl+C",state = 'normal' if self.sel_item!=None else 'disabled')
        pop.add_command(label = 'Copy only path',command = self.clip_copy_full,accelerator="C",state = 'normal' if self.sel_item!=None else 'disabled')
        pop.add_separator()
        pop.add_command(label = 'Find',command = self.finder_wrapper_show,accelerator="F",state = 'normal' if self.sel_item!=None else 'disabled')
        pop.add_command(label = 'Find next',command = self.find_next,accelerator="F3",state = 'normal' if self.sel_item!=None else 'disabled')
        pop.add_command(label = 'Find prev',command = self.find_prev,accelerator="Shift+F3",state = 'normal' if self.sel_item!=None else 'disabled')
        pop.add_separator()

        pop.add_command(label = "Exit",  command = self.exit)
        
        tree.configure(style='semi_focus.Treeview')
        
        try:
            pop.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            print(e)
        
        tree.configure(style='default.Treeview')

        pop.grab_release()

    def empty_folder_remove_ask(self):
        if res:=tk.filedialog.askdirectory(title='Select Directory',initialdir=self.cwd,parent=self.main):
            FinalInfo = self.empty_dirs_removal(res,True)

            self.info_dialog_on_main.show('Removed empty directories','\n'.join(FinalInfo),min_width=800)

            self.tree_folder_update(self.sel_path_full)

    def sel_dir(self,action):
        self.action_on_path(self.SelFullPathToFile,action,True)

    def column_sort_click(self, tree, colname):
        prev_colname,prev_reverse=self.column_sort_last_params[tree]
        reverse = not prev_reverse if colname == prev_colname else prev_reverse
        tree.heading(prev_colname, text=self.OrgLabel[prev_colname])

        self.column_sort_last_params[tree]=(colname,reverse)

        if tree == self.folder_tree:
            self.folder_items_cache={}

        self.column_sort (tree)

    @busy_cursor
    @restore_status_line
    def column_sort(self, tree):
        self.status('Sorting...')
        colname,reverse = self.column_sort_last_params[tree]

        real_column_to_sort=self.col2sortOf[colname]

        UPDIRCode,DIRCode,NONDIRCode = (2,1,0) if reverse else (0,1,2)

        l = [((UPDIRCode if tree.set(item,'kind')==UPDIR else DIRCode if tree.set(item,'kind')==DIR else NONDIRCode,tree.set(item,real_column_to_sort)), item) for item in tree.get_children('')]
        l.sort(reverse=reverse,key=lambda x: ( (x[0][0],float(x[0][1])) if x[0][1].isdigit() else (x[0][0],0) ) if self.col2sortNumeric[colname] else x[0])

        {tree.move(item, '', index) for index, (val,item) in enumerate(l)}

        if self.col2sortLev2[colname]:
            for topItem in tree.get_children():
                l = [(tree.set(item,real_column_to_sort), item) for item in tree.get_children(topItem)]
                l.sort(reverse=reverse,key=lambda x: (float(x[0]) if x[0].isdigit() else 0) if self.col2sortNumeric[colname] else x[0])

                {tree.move(item, topItem, index) for index, (val,item) in enumerate(l)}

        if item:=tree.focus():
            tree.see(item)
        elif item:=tree.selection():
            tree.see(item)

        tree.update()

        self.column_sort_set_arrow(tree)

        if tree==self.groups_tree:
            self.tree_groups_flat_items_update()

    def column_sort_set_arrow(self, tree):
        colname,reverse = self.column_sort_last_params[tree]
        tree.heading(colname, text=self.OrgLabel[colname] + ' ' + str(u'\u25BC' if reverse else u'\u25B2') )

    def path_to_scan_add(self,path):
        if len(self.paths_to_scan_from_dialog)<10:
            self.paths_to_scan_from_dialog.append(path)
            self.paths_to_scan_update()
        else:
            logging.error(f'can\'t add:{path}. limit exceeded')

    def scan_from_button(self):
        if self.scan():
            self.scan_dialog.hide()
        
    @restore_status_line
    def scan(self):
        self.status('Scanning...')
        self.cfg.write()

        self.D.reset()
        self.status_var_full_path.set('')
        self.groups_show()

        PathsToScanFromEntry = [var.get() for var in self.PathsToScanEntryVar.values()]
        ExcludeVarsFromEntry = [var.get() for var in self.ExcludeEntryVar.values()]

        if res:=self.D.set_exclude_masks(self.cfg.get_bool(CFG_KEY_EXCLUDE_REGEXP),ExcludeVarsFromEntry):
            self.info_dialog_on_scan.show('Error. Fix Exclude masks.',res)
            return False
        self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(ExcludeVarsFromEntry))

        if not PathsToScanFromEntry:
            self.info_dialog_on_scan.show('Error. No paths to scan.','Add paths to scan.',min_width=400)
            return False

        if res:=self.D.set_paths_to_scan(PathsToScanFromEntry):
            self.info_dialog_on_scan.show('Error. Fix paths selection.',res)
            return False

        self.main.update()

        #############################

        self.crc_progress_dialog_show(self.scan_dialog.area_main,'Scanning')

        scan_thread=Thread(target=self.D.scan,daemon=True)
        scan_thread.start()

        while scan_thread.is_alive():
            self.crc_progress_dialog_update(self.NUMBERS[self.D.info_path_nr] + '\n' + self.D.info_path_to_scan + '\n\n' + str(self.D.info_counter) + '\n' + core.bytes_to_str(self.D.info_size_sum))

            if self.action_abort:
                self.D.abort()
                break
            else:
                time.sleep(0.04)

        scan_thread.join()
        self.crc_progress_dialog_end()

        if self.action_abort:
            return False

        #############################
        if self.D.sim_size==0:
            self.info_dialog_on_scan.show('Cannot Proceed.','No Duplicates.')
            return False
        #############################
        self.status('Calculating CRC ...')
        self.crc_progress_dialog_show(self.scan_dialog.area_main,'CRC calculation','determinate','determinate',Progress1LeftText='Total space:',Progress2LeftText='Files number:')

        self.D.writeLog=self.WriteScanToLog.get()

        crc_thread=Thread(target=self.D.crc_calc,daemon=True)
        crc_thread.start()

        self.scan_dialog.widget.config(cursor="watch")

        while crc_thread.is_alive():
            info = ""

            if self.debug_mode:
                info =  'Active Threads: ' + self.D.InfoThreads \
                    + '\nAvarage speed: ' + core.bytes_to_str(self.D.infoSpeed,1) + '/s\n\n'

            info = info + 'Results:' \
                + '\nCRC groups: ' + str(self.D.InfoFoundGroups) \
                + '\nfolders: ' + str(self.D.InfoFoundFolders) \
                + '\nspace: ' + core.bytes_to_str(self.D.InfoDuplicatesSpace)

            InfoProgSize=float(100)*float(self.D.InfoSizeDone)/float(self.D.sim_size)
            InfoProgQuant=float(100)*float(self.D.InfoFileDone)/float(self.D.InfoTotal)

            progr_1_right=core.bytes_to_str(self.D.InfoSizeDone) + '/' + core.bytes_to_str(self.D.sim_size)
            progr_2_right=str(self.D.InfoFileDone) + '/' + str(self.D.InfoTotal)

            self.crc_progress_dialog_update(info,InfoProgSize,InfoProgQuant,progr_1_right,progr_2_right,self.D.InfoLine)

            if self.D.can_abort:
                if self.action_abort:
                    self.D.abort()
            else:
                self.status(self.D.info)

            time.sleep(0.04)

        self.status('Finishing CRC Thread...')
        crc_thread.join()
        #############################

        self.crc_progress_dialog_end()
        self.scan_dialog.widget.config(cursor="")

        self.groups_show()
        
        self.scan_dialog.unlock('scan complete')
        
        if self.action_abort:
            self.info_dialog_on_scan.show('CRC Calculation aborted.','\nResults are partial.\nSome files may remain unidentified as duplicates.',min_width=400)

        return True

    def scan_dialog_show(self,do_scan=False):
        
        self.exclude_mask_update()
        self.paths_to_scan_update()
        
        self.scan_dialog.show(focus=self.scan_cancel_button,do_command=self.scan if do_scan else None)
        
        if self.D.ScannedPaths:
            self.paths_to_scan_from_dialog=self.D.ScannedPaths.copy()

    def paths_to_scan_update(self) :
        for subframe in self.paths_to_scan_frames:
            subframe.destroy()

        self.paths_to_scan_frames=[]
        self.PathsToScanEntryVar={}

        row=0
        for path in self.paths_to_scan_from_dialog:
            (fr:=tk.Frame(self.pathsFrame,bg=self.bg)).grid(row=row,column=0,sticky='news',columnspan=3)
            self.paths_to_scan_frames.append(fr)

            tk.Label(fr,text=' ' + self.NUMBERS[row] + ' ' , relief='groove',bg=self.bg).pack(side='left',padx=2,pady=1,fill='y')

            self.PathsToScanEntryVar[row]=tk.StringVar(value=path)
            ttk.Entry(fr,textvariable=self.PathsToScanEntryVar[row]).pack(side='left',expand=1,fill='both',pady=1)

            ttk.Button(fr,text='❌',command=lambda pathpar=path: self.path_to_scan_remove(pathpar),width=3).pack(side='right',padx=2,pady=1,fill='y')

            row+=1

        if len(self.paths_to_scan_from_dialog)==self.MAX_PATHS:
            self.AddPathButton.configure(state=DISABLED,text='')
            #self.AddDrivesButton.configure(state=DISABLED,text='')
            self.ClearListButton.focus_set()
        else:
            self.AddPathButton.configure(state=NORMAL,text='Add path ...')
            #self.AddDrivesButton.configure(state=NORMAL,text='Add drives ...')

    def exclude_regexp_set(self):
        self.cfg.set_bool(CFG_KEY_EXCLUDE_REGEXP,self.exclude_regexp_scan.get())

    def exclude_mask_update(self) :
        for subframe in self.exclude_frames:
            subframe.destroy()

        self.exclude_frames=[]
        self.ExcludeEntryVar={}

        ttk.Checkbutton(self.exclude_frame,text='Use regular expressions matching',variable=self.exclude_regexp_scan,command=lambda : self.exclude_regexp_set()).grid(row=0,column=0,sticky='news',columnspan=3,padx=5)

        row=1

        for entry in self.cfg.get(CFG_KEY_EXCLUDE,'').split('|'):
            if entry:
                (fr:=tk.Frame(self.exclude_frame,bg=self.bg)).grid(row=row,column=0,sticky='news',columnspan=3)
                self.exclude_frames.append(fr)

                self.ExcludeEntryVar[row]=tk.StringVar(value=entry)
                ttk.Entry(fr,textvariable=self.ExcludeEntryVar[row]).pack(side='left',expand=1,fill='both',pady=1)

                ttk.Button(fr,text='❌',command=lambda entrypar=entry: self.exclude_mask_remove(entrypar),width=3).pack(side='right',padx=2,pady=1,fill='y')

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
        if res:=tk.filedialog.askdirectory(title='Select Directory',initialdir=self.cwd,parent=self.scan_dialog.area_main):
            self.path_to_scan_add(res)

    def exclude_mask_add_dialog(self):
        mask = self.exclude_dialog_on_scan.show(f'Specify Exclude expression','expression:','')
        if mask:
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

        if self.cfg.get_bool(CFG_KEY_FULL_CRC)!=self.FullCRC.get():
            self.cfg.set_bool(CFG_KEY_FULL_CRC,self.FullCRC.get())
            update1=True
            update2=True
            self.folder_items_cache={}

        if self.cfg.get_bool(CFG_KEY_FULL_PATHS)!=self.FullPaths.get():
            self.cfg.set_bool(CFG_KEY_FULL_PATHS,self.FullPaths.get())
            update1=True
            update2=True

        if self.cfg.get_bool(CFG_KEY_REL_SYMLINKS)!=self.RelSymlinks.get():
            self.cfg.set_bool(CFG_KEY_REL_SYMLINKS,self.RelSymlinks.get())

        if self.cfg.get_bool(ERASE_EMPTY_DIRS)!=self.EraseEmptyDirs.get():
            self.cfg.set_bool(ERASE_EMPTY_DIRS,self.EraseEmptyDirs.get())

        if self.cfg.get_bool(CFG_ALLOW_DELETE_ALL)!=self.AllowDeleteAll.get():
            self.cfg.set_bool(CFG_ALLOW_DELETE_ALL,self.AllowDeleteAll.get())

        if self.cfg.get_bool(CFG_SKIP_INCORRECT_GROUPS)!=self.SkipIncorrectGroups.get():
            self.cfg.set_bool(CFG_SKIP_INCORRECT_GROUPS,self.SkipIncorrectGroups.get())

        if self.cfg.get_bool(CFG_ALLOW_DELETE_NON_DUPLICATES)!=self.AllowDeleteNonDuplicates.get():
            self.cfg.set_bool(CFG_ALLOW_DELETE_NON_DUPLICATES,self.AllowDeleteNonDuplicates.get())

        if self.cfg.get_bool(CFG_CONFIRM_SHOW_CRCSIZE)!=self.ConfirmShowCrcSize.get():
            self.cfg.set_bool(CFG_CONFIRM_SHOW_CRCSIZE,self.ConfirmShowCrcSize.get())

        if self.cfg.get_bool(CFG_CONFIRM_SHOW_LINKSTARGETS)!=self.ConfirmShowLinksTargets.get():
            self.cfg.set_bool(CFG_CONFIRM_SHOW_LINKSTARGETS,self.ConfirmShowLinksTargets.get())

        self.cfg.write()

        if update1:
            self.groups_tree_update_crc_and_path()

        if update2:
            if self.SelCrc and self.sel_item and self.sel_path_full:
                self.tree_folder_update()
            else:
                self.tree_folder_update_none()

        self.SettingsDialog.hide()

    def settings_reset(self):
        {var.set(cfg_defaults[key]) for var,key in self.settings}

    def crc_node_update(self,crc):
        size=int(self.groups_tree.set(crc,'size'))

        CrcRemoved=False
        if not size in self.D.files_of_size_of_crc:
            self.groups_tree.delete(crc)
            logging.debug('crc_node_update-1 ' + crc)
            CrcRemoved=True
        elif crc not in self.D.files_of_size_of_crc[size]:
            self.groups_tree.delete(crc)
            logging.debug('crc_node_update-2 ' + crc)
            CrcRemoved=True
        else:
            crcDict=self.D.files_of_size_of_crc[size][crc]
            for item in list(self.groups_tree.get_children(crc)):
                IndexTuple=self.get_index_tuple_groups_tree(item)

                if IndexTuple not in crcDict:
                    self.groups_tree.delete(item)
                    logging.debug('crc_node_update-3 ' + item)

            if not self.groups_tree.get_children(crc):
                self.groups_tree.delete(crc)
                logging.debug('crc_node_update-4 ' + crc)
                CrcRemoved=True

    def data_precalc(self):
        self.status('Precalculating data...')

        self.ByIdCtimeCache = { (self.idfunc(inode,dev),ctime):(crc,self.D.crccut[crc],len(self.D.files_of_size_of_crc[size][crc]) ) for size,sizeDict in self.D.files_of_size_of_crc.items() for crc,crcDict in sizeDict.items() for pathnr,path,file,ctime,dev,inode in crcDict }
        self.status_var_groups.set(len(self.groups_tree.get_children()))

        PathStatSize={}
        PathStatQuant={}

        self.BiggestFileOfPath={}
        self.BiggestFileOfPathId={}

        for size,sizeDict in self.D.files_of_size_of_crc.items() :
            for crc,crcDict in sizeDict.items():
                for pathnr,path,file,ctime,dev,inode in crcDict:
                    pathindex=(pathnr,path)
                    PathStatSize[pathindex] = PathStatSize.get(pathindex,0) + size
                    PathStatQuant[pathindex] = PathStatQuant.get(pathindex,0) + 1

                    if size>self.BiggestFileOfPath.get(pathindex,0):
                        self.BiggestFileOfPath[pathindex]=size
                        self.BiggestFileOfPathId[pathindex]=self.idfunc(inode,dev)

        self.PathStatListSize=tuple(sorted([(pathnr,path,number) for (pathnr,path),number in PathStatSize.items()],key=lambda x : x[2],reverse=True))
        self.PathStatListQuant=tuple(sorted([(pathnr,path,number) for (pathnr,path),number in PathStatQuant.items()],key=lambda x : x[2],reverse=True))
        self.GroupsCombosSize = tuple(sorted([(crcitem,sum([int(self.groups_tree.set(item,'size')) for item in self.groups_tree.get_children(crcitem)])) for crcitem in self.groups_tree.get_children()],key = lambda x : x[1],reverse = True))
        self.GroupsCombosQuant = tuple(sorted([(crcitem,len(self.groups_tree.get_children(crcitem))) for crcitem in self.groups_tree.get_children()],key = lambda x : x[1],reverse = True))

        self.PathsQuant=len(self.PathStatListSize)
        self.GroupsCombosLen=len(self.GroupsCombosSize)

    def tree_groups_flat_items_update(self):
        self.tree_groups_flat_items = tuple([elem for sublist in [ tuple([crc])+tuple(self.groups_tree.get_children(crc)) for crc in self.groups_tree.get_children() ] for elem in sublist])

    def initial_focus(self):
        if self.groups_tree.get_children():
            firstNodeFile=next(iter(self.groups_tree.get_children(next(iter(self.groups_tree.get_children())))))
            self.groups_tree.focus_set()
            self.groups_tree.focus(firstNodeFile)
            self.groups_tree.see(firstNodeFile)
            self.groups_tree_sel_change(firstNodeFile)

            self.groups_tree_update_crc_and_path()
        else:
            self.tree_folder_update_none()
            self.reset_sels()

    @busy_cursor
    def groups_show(self):
        self.status('Rendering data...')

        self.idfunc = (lambda i,d : '%s-%s'%(i,d)) if len(self.D.devs)>1 else (lambda i,d : str(i))

        self.reset_sels()
        self.groups_tree.delete(*self.groups_tree.get_children())

        SizesCounter=0
        for size,sizeDict in self.D.files_of_size_of_crc.items() :
            SizeBytes = core.bytes_to_str(size)
            if not SizesCounter%64:
                self.status('Rendering data... (%s)' % SizeBytes)

            SizesCounter+=1
            for crc,crcDict in sizeDict.items():
                crcitem=self.groups_tree.insert(parent='', index=END,iid=crc, values=('','','',str(size),SizeBytes,'','','',crc,len(crcDict),'',CRC),tags=CRC,open=True)

                for pathnr,path,file,ctime,dev,inode in crcDict:
                    self.groups_tree.insert(parent=crcitem, index=END,iid=self.idfunc(inode,dev), values=(\
                            pathnr,path,file,str(size),\
                            '',\
                            str(ctime),str(dev),str(inode),crc,\
                            '',\
                            time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime)) ,FILE),tags=())
        self.data_precalc()

        if self.column_sort_last_params[self.groups_tree]!=self.ColumnSortLastParamsDefault:
            #defaultowo po size juz jest, nie trzeba tracic czasu
            self.column_sort(self.groups_tree)
        else:
            self.column_sort_set_arrow(self.groups_tree)

        self.tree_groups_flat_items_update() #after sort !
        self.initial_focus()
        self.calc_mark_stats_groups()

        self.status('')

    def groups_tree_update_crc_and_path(self):
        FullCRC=self.cfg.get_bool(CFG_KEY_FULL_CRC)
        FullPaths=self.cfg.get_bool(CFG_KEY_FULL_PATHS)

        for size,sizeDict in self.D.files_of_size_of_crc.items() :
            for crc,crcDict in sizeDict.items():
                self.groups_tree.item(crc,text=crc if FullCRC else self.D.crccut[crc])
                for pathnr,path,file,ctime,dev,inode in crcDict:
                    self.groups_tree.item(self.idfunc(inode,dev),text=self.D.ScannedPaths[pathnr] if FullPaths else self.NUMBERS[pathnr])

    def groups_tree_update_none(self):
        self.groups_tree.selection_remove(self.groups_tree.selection())

    def groups_tree_update(self,item):
        self.groups_tree.see(self.SelCrc)
        self.groups_tree.update()

        self.groups_tree.selection_set(item)
        self.groups_tree.see(item)
        self.groups_tree.update()

    def tree_folder_update_none(self):
        self.folder_tree.delete(*self.folder_tree.get_children())
        self.calc_mark_stats_folder()
        self.status_var_folder_size.set('')
        self.status_var_folder_quant.set('')

        self.status_var_full_path.set('')
        self.status_var_full_path_label.config(fg = 'black')

    sortIndexDict={'file':1,'sizeH':2,'ctimeH':3,'instances':8}
    kindIndex=10

    def two_dots_condition_win(self):
        return True if self.sel_path_full.split(os.sep)[1]!='' else False

    def two_dots_condition_lin(self):
        return True if self.sel_path_full!='/' else False

    two_dots_condition = two_dots_condition_win if windows else two_dots_condition_lin

    @busy_cursor
    def tree_folder_update(self,ArbitraryPath=None):
        CurrentPath=ArbitraryPath if ArbitraryPath else self.sel_path_full

        if not CurrentPath:
            return False

        (DirCtime,ScanDirRes)=self.D.set_scan_dir(CurrentPath)

        if not ScanDirRes:
            return False

        Refresh=True
        if CurrentPath in self.folder_items_cache:
            if DirCtime==self.folder_items_cache[CurrentPath][0]:
                Refresh=False

        if Refresh :
            FolderItems=[]

            FullCRC=self.cfg.get_bool(CFG_KEY_FULL_CRC)

            i=0
            for file,islink,isdir,isfile,mtime,ctime,dev,inode,size,nlink in ScanDirRes:
                if islink :
                    FolderItems.append( ( '\t📁 ⇦',file,0,0,0,0,'','',1,0,DIR,'%sDL' % i,'','' ) if isdir else ( '\t  🠔',file,0,ctime,dev,inode,'','',1,0,LINK,'%sFL' % i,'','' ) )
                elif isdir:
                    FolderItems.append( ('\t📁',file,0,0,0,0,'','',1,0,DIR,'%sD' % i,'','' ) )
                elif isfile:

                    FILEID=self.idfunc(inode,dev)

                    if (FILEID,ctime) in self.ByIdCtimeCache:
                        crc,crccut,instances = self.ByIdCtimeCache[(FILEID,ctime)]

                        FolderItems.append( (crc if FullCRC else crccut, \
                                                    file,\
                                                    size,\
                                                    ctime,\
                                                    dev,\
                                                    inode,\
                                                    crc,\
                                                    instances,\
                                                    instances,\
                                                    FILEID,\
                                                    FILE,\
                                                    FILEID,\
                                                    core.bytes_to_str(size),\
                                                    time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime) ) \
                                            )  )
                    else:
                        if nlink!=1:
                            #hardlinks
                            FolderItems.append( ( '\t ✹',file,size,ctime,dev,inode,'','',1,FILEID,SINGLEHARDLINKED,'%sO' % i,core.bytes_to_str(size),time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime) ) ) )
                        else:
                            FolderItems.append( ( '',file,size,ctime,dev,inode,'','',1,FILEID,SINGLE,'%sO' % i,core.bytes_to_str(size),time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime) ) ) )
                else:
                    logging.error(f'what is it: {file},{islink},{isdir},{isfile} ?')

                i+=1

            ############################################################
            colSort,reverse = self.column_sort_last_params[self.folder_tree]
            sortIndex=self.sortIndexDict[colSort]
            IsNumeric=self.col2sortNumeric[colSort]

            UPDIRCode,DIRCode,NONDIRCode = (2,1,0) if reverse else (0,1,2)
            ############################################################

            FolderItemsSorted=sorted(FolderItems,key=lambda x : (UPDIRCode if x[self.kindIndex]==UPDIR else DIRCode if x[self.kindIndex]==DIR else NONDIRCode,float(x[sortIndex])) if IsNumeric else (UPDIRCode if x[self.kindIndex]==UPDIR else DIRCode if x[self.kindIndex]==DIR else NONDIRCode,x[sortIndex]),reverse=reverse)

            #text,values,FILEID,kind,iid,defaulttag
            self.folder_items_cache[CurrentPath]=(DirCtime,tuple([ (text,(file,str(size),sizeH,str(ctime),str(dev),str(inode),crc,str(instances),str(instancesnum),ctimeH,kind),FILEID,kind,iid,SINGLE if kind in (SINGLE,SINGLEHARDLINKED) else DIR if kind in (DIR,UPDIR) else LINK if kind==LINK else "") for text,file,size,ctime,dev,inode,crc,instances,instancesnum,FILEID,kind,iid,sizeH,ctimeH in FolderItemsSorted] ) )

        if ArbitraryPath:
            #TODO - workaround
            sel_path_prev=self.sel_path
            self.reset_sels()
            self.sel_path=sel_path_prev
            self.sel_path_set(str(pathlib.Path(ArbitraryPath)))

        self.folder_tree.delete(*self.folder_tree.get_children())

        if self.two_dots_condition():
            self.folder_tree.insert(parent="", index=END, iid='0UP' , text='', values=('..','0','','0','0','0','..','','0','',UPDIR),tags=DIR)

        for (text,values,FILEID,kind,iid,defaulttag) in self.folder_items_cache[CurrentPath][1]:
            self.folder_tree.insert(parent="", index=END, iid=iid , text=text, values=values,tags=self.groups_tree.item(FILEID)['tags'] if kind==FILE else defaulttag)

        self.TreeFolderFlatItemsList=self.folder_tree.get_children()

        if not ArbitraryPath:
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
        self.set_status_var_color()

    def calc_mark_stats_folder(self):
        self.calc_mark_stats_core(self.folder_tree,self.status_var_folder_size,self.status_var_folder_quant)

    def calc_mark_stats_core(self,tree,varSize,varQuant):
        marked=tree.tag_has(MARK)
        varQuant.set(len(marked))
        varSize.set(core.bytes_to_str(sum(int(tree.set(item,'size')) for item in marked)))

    def mark_in_specified_group_by_ctime(self, action, crc, reverse,select=False):
        item=sorted([ (item,self.groups_tree.set(item,'ctime') ) for item in self.groups_tree.get_children(crc)],key=lambda x : float(x[1]),reverse=reverse)[0][0]
        if item:
            action(item,self.groups_tree)
            if select:
                self.groups_tree.see(item)
                self.groups_tree.focus(item)
                self.groups_tree_sel_change(item)
                self.groups_tree.update()

    @busy_cursor
    def mark_all_by_ctime(self,orderStr, action):
        self.status('Un/Setting marking on all files ...')
        reverse=1 if orderStr=='oldest' else 0

        { self.mark_in_specified_group_by_ctime(action, crc, reverse) for crc in self.groups_tree.get_children() }
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @busy_cursor
    def mark_in_group_by_ctime(self,orderStr,action):
        self.status('Un/Setting marking in group ...')
        reverse=1 if orderStr=='oldest' else 0
        self.mark_in_specified_group_by_ctime(action,self.SelCrc,reverse,True)
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    def MarkInSpecifiedCRCGroup(self,action,crc):
        { action(item,self.groups_tree) for item in self.groups_tree.get_children(crc) }

    @busy_cursor
    def mark_in_group(self,action):
        self.status('Un/Setting marking in group ...')
        self.MarkInSpecifiedCRCGroup(action,self.SelCrc)
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @busy_cursor
    def mark_on_all(self,action):
        self.status('Un/Setting marking on all files ...')
        { self.MarkInSpecifiedCRCGroup(action,crc) for crc in self.groups_tree.get_children() }
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    #def ActionOnPathPane(self,action,items):
    #    self.status('Un/Setting marking in folder ...')
    #    { (action(item,self.folder_tree),action(item,self.groups_tree)) for item in items if self.folder_tree.set(item,'kind')==FILE }

    #    self.calc_mark_stats_groups()
    #    self.calc_mark_stats_folder()

    @busy_cursor
    def mark_in_folder(self,action):
        self.status('Un/Setting marking in folder ...')
        { (action(item,self.folder_tree),action(item,self.groups_tree)) for item in self.folder_tree.get_children() if self.folder_tree.set(item,'kind')==FILE }

        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    def set_mark(self,item,tree):
        tree.item(item,tags=[MARK])

    def unset_mark(self,item,tree):
        tree.item(item,tags=())

    def invert_mark(self,item,tree):
        tree.item(item,tags=() if tree.item(item)['tags'] else [MARK])

    @busy_cursor
    def action_on_path(self,pathParam,action,AllGroups=True):
        if AllGroups:
            CrcRange = self.groups_tree.get_children()
        else :
            CrcRange = [str(self.SelCrc)]

        selCount=0
        for crcitem in CrcRange:
            for item in self.groups_tree.get_children(crcitem):
                fullpath = self.item_full_path(item)

                if fullpath.startswith(pathParam + os.sep):
                    action(item,self.groups_tree)
                    selCount+=1
        
        if not selCount :
            self.info_dialog_on_main.show('No files found for specified path',pathParam,min_width=400)
        else:
            self.status(f'Subdirectory action. {selCount} File(s) Found')
            self.update_marks_folder()
            self.calc_mark_stats_groups()
            self.calc_mark_stats_folder()

    TreeExpr={}

    @keep_semi_focus
    def mark_expression(self,action,prompt,AllGroups=True):
        tree=self.main.focus_get()

        if tree in self.TreeExpr.keys():
            initialvalue=self.TreeExpr[tree]
        else:
            initialvalue='*'

        if tree==self.groups_tree:
            RangeStr = " (all groups)" if AllGroups else " (selected group)"
            title=f'Specify expression for full file path.'
        else:
            RangeStr = ''
            title='Specify expression for file names in selected directory.'

        (use_reg_expr,expression) = self.mark_dialog_on_main.show(title,prompt + f'{RangeStr}', initialvalue,'Use regular expressions matching',self.cfg.get_bool(CFG_KEY_USE_REG_EXPR))

        items=[]
        UseRegExprInfo = '(regular expression)' if use_reg_expr else ''

        if expression:
            self.cfg.set_bool(CFG_KEY_USE_REG_EXPR,use_reg_expr)
            self.TreeExpr[tree]=expression

            if tree==self.groups_tree:
                CrcRange = self.groups_tree.get_children() if AllGroups else [str(self.SelCrc)]

                for crcitem in CrcRange:
                    for item in self.groups_tree.get_children(crcitem):
                        fullpath = self.item_full_path(item)
                        try:
                            if (use_reg_expr and re.search(expression,fullpath)) or (not use_reg_expr and fnmatch.fnmatch(fullpath,expression) ):
                                items.append(item)
                        except Exception as e:
                            self.info_dialog_on_main.show('expression Error !',f'expression:"{expression}"  {UseRegExprInfo}\n\nERROR:{e}',min_width=400)
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
                            self.info_dialog_on_main.show('expression Error !',f'expression:"{expression}"  {UseRegExprInfo}\n\nERROR:{e}',min_width=400)
                            tree.focus_set()
                            return

            if items:
                self.main.config(cursor="watch")
                self.menu_disable()
                self.main.update()

                FirstItem=items[0]

                tree.focus(FirstItem)
                tree.see(FirstItem)

                if tree==self.groups_tree:
                    for item in items:
                        action(item,tree)

                    self.groups_tree_sel_change(FirstItem)
                else:
                    for item in items:
                        action(item,self.groups_tree)
                        action(item,self.folder_tree)

                    self.folder_tree_sel_change(FirstItem)

                self.update_marks_folder()
                self.calc_mark_stats_groups()
                self.calc_mark_stats_folder()

                self.main.config(cursor="")
                self.menu_enable()
                self.main.update()

            else:
                self.info_dialog_on_main.show('No files found.',f'expression:"{expression}"  {UseRegExprInfo}\n',min_width=400)

        tree.focus_set()

    def mark_subpath(self,action,AllGroups=True):
        if path:=tk.filedialog.askdirectory(title='Select Directory',initialdir=self.cwd):
            self.action_on_path(path,action,AllGroups)

    def goto_next_mark_menu(self,direction,GoToNoMark=False):
        tree=(self.groups_tree,self.folder_tree)[self.SelTreeIndex]
        self.goto_next_mark(tree,direction,GoToNoMark)

    def goto_next_mark(self,tree,direction,GoToNoMark=False):
        marked=[item for item in tree.get_children() if not tree.tag_has(MARK,item)] if GoToNoMark else tree.tag_has(MARK)
        if marked:
            if GoToNoMark:
                #marked if not tree.tag_has(MARK,self.sel_item) else
                pool= self.tree_groups_flat_items if tree==self.groups_tree else self.folder_tree.get_children()
            else:
                pool=marked if tree.tag_has(MARK,self.sel_item) else self.tree_groups_flat_items if tree==self.groups_tree else self.folder_tree.get_children()

            poollen=len(pool)

            if poollen:
                index = pool.index(self.sel_item)

                while True:
                    index=(index+direction)%poollen
                    NextItem=pool[index]
                    if (not GoToNoMark and MARK in tree.item(NextItem)['tags']) or (GoToNoMark and MARK not in tree.item(NextItem)['tags']):
                        tree.focus(NextItem)
                        tree.see(NextItem)

                        if tree==self.groups_tree:
                            self.groups_tree_sel_change(NextItem)
                        else:
                            self.folder_tree_sel_change(NextItem)

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
                    NextItem=pool[index]
                    if tree.set(NextItem,'kind')==FILE:
                        tree.focus(NextItem)
                        tree.see(NextItem)

                        if tree==self.groups_tree:
                            self.groups_tree_sel_change(NextItem)
                        else:
                            self.folder_tree_sel_change(NextItem)

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

    @busy_cursor
    def goto_max_group(self,sizeFlag=0,Direction=1):
        if self.GroupsCombosLen:
            #self.status(f'Setting dominant group ...')
            WorkingIndex = self.dominant_groups_index[sizeFlag]
            WorkingIndex = (WorkingIndex+Direction) % self.GroupsCombosLen
            temp=str(WorkingIndex)
            WorkingDict = self.GroupsCombosSize if sizeFlag else self.GroupsCombosQuant

            biggestcrc,biggestcrcSizeSum = WorkingDict[WorkingIndex]

            if biggestcrc:
                self.crc_select_and_focus(biggestcrc,True)

                self.dominant_groups_index[sizeFlag] = int(temp)
                info = core.bytes_to_str(biggestcrcSizeSum) if sizeFlag else str(biggestcrcSizeSum)
                self.status(f'Dominant (index:{WorkingIndex}) group ({self.BY_WHAT[sizeFlag]}: {info})')

    @busy_cursor
    def goto_max_folder(self,sizeFlag=0,Direction=1):
        if self.PathsQuant:
            #self.status(f'Setting dominant folder ...')
            WorkingIndex = self.dominant_groups_folder[sizeFlag]
            WorkingIndex = (WorkingIndex+Direction) % self.PathsQuant
            temp = str(WorkingIndex)
            WorkingDict = self.PathStatListSize if sizeFlag else self.PathStatListQuant

            pathnr,path,num = WorkingDict[WorkingIndex]

            item=self.BiggestFileOfPathId[(pathnr,path)]

            self.groups_tree.focus(item)
            self.groups_tree_sel_change(item,ChangeStatusLine=False)

            LastCrcChild=self.groups_tree.get_children(self.SelCrc)[-1]
            try:
                self.groups_tree.see(LastCrcChild)
                self.groups_tree.see(self.SelCrc)
                self.groups_tree.see(item)
            except Exception :
                pass

            self.folder_tree.update()

            try:
                self.folder_tree.focus_set()
                self.folder_tree.focus(item)
                self.folder_tree_sel_change(item,ChangeStatusLine=False)
                self.folder_tree.see(item)
            except Exception :
                pass

            self.groups_tree_update(item)

            self.dominant_groups_folder[sizeFlag] = int(temp)
            info = core.bytes_to_str(num) if sizeFlag else str(num)
            self.status(f'Dominant (index:{WorkingIndex}) folder ({self.BY_WHAT[sizeFlag]}: {info})')

    def item_full_path(self,item):
        pathnr=int(self.groups_tree.set(item,'pathnr'))
        path=self.groups_tree.set(item,'path')
        file=self.groups_tree.set(item,'file')
        return os.path.abspath(self.D.get_full_path_scanned(pathnr,path,file))

    def file_check_state(self,item):
        fullpath = self.item_full_path(item)
        logging.info(f'checking file:{fullpath}')
        try:
            stat = os.stat(fullpath)
            ctimeCheck=str(round(stat.st_ctime))
        except Exception as e:
            self.status(str(e))
            mesage = f'can\'t check file: {fullpath}\n\n{e}'
            logging.error(mesage)
            return mesage

        if ctimeCheck != (ctime:=self.groups_tree.set(item,'ctime')) :
            message = {f'ctime inconsistency {ctimeCheck} vs {ctime}'}
            return message

    def process_files_in_groups_wrapper(self,action,AllGroups):
        ProcessedItems=defaultdict(list)
        if AllGroups:
            ScopeTitle='All marked files.'
        else:
            ScopeTitle='Single CRC group.'

        for crc in self.groups_tree.get_children():
            if AllGroups or crc==self.SelCrc:
                for item in self.groups_tree.get_children(crc):
                    if self.groups_tree.tag_has(MARK,item):
                        ProcessedItems[crc].append(item)

        return self.process_files(action,ProcessedItems,ScopeTitle)

    def process_files_in_folder_wrapper(self,action,OnDirAction=False):
        ProcessedItems=defaultdict(list)
        if OnDirAction:
            ScopeTitle='All marked files on selected directory sub-tree.'

            SelPathWithSep=self.SelFullPathToFile + os.sep
            for crc in self.groups_tree.get_children():
                for item in self.groups_tree.get_children(crc):
                    if self.item_full_path(item).startswith(SelPathWithSep):
                        if self.groups_tree.tag_has(MARK,item):
                            ProcessedItems[crc].append(item)
        else:
            ScopeTitle='Selected Directory.'
            #self.sel_path_full
            
            for item in self.folder_tree.get_children():
                if self.folder_tree.tag_has(MARK,item):
                    crc=self.folder_tree.set(item,'crc')
                    ProcessedItems[crc].append(item)

        return self.process_files(action,ProcessedItems,ScopeTitle)

    @restore_status_line
    def process_files_check_correctness(self,action,ProcessedItems,RemainingItems):
        for crc in ProcessedItems:
            size = self.D.Crc2Size[crc]
            (checkres,TuplesToRemove)=self.D.check_group_files_state(size,crc)

            if checkres:
                self.info_dialog_on_main.show('Error. Inconsistent data.','Current filesystem state is inconsistent with scanned data.\n\n' + '\n'.join(checkres) + '\n\nSelected CRC group will be reduced. For complete results re-scanning is recommended.')
                orglist=self.groups_tree.get_children()

                self.D.RemoveFromDataPool(size,crc,TuplesToRemove)

                self.crc_node_update(crc)

                self.tree_groups_flat_items_update()

                self.data_precalc()

                newlist=self.groups_tree.get_children()
                ItemToSel = self.get_closest_in_crc(orglist,crc,newlist)

                self.reset_sels()

                if ItemToSel:
                    #crc node moze zniknac - trzeba zupdejtowac SelXxx
                    self.crc_select_and_focus(ItemToSel,True)
                else:
                    self.initial_focus()

                self.calc_mark_stats_groups()

        self.status('checking selection correctness...')
        if action==HARDLINK:
            for crc in ProcessedItems:
                if len(ProcessedItems[crc])==1:
                    self.info_dialog_on_main.show('Error - Can\'t hardlink single file.',"Mark more files.",min_width=400)

                    self.crc_select_and_focus(crc,True)
                    return True

        elif action==DELETE:
            if self.cfg.get_bool(CFG_SKIP_INCORRECT_GROUPS):
                IncorrectGroups=[]
                for crc in ProcessedItems:
                    if len(RemainingItems[crc])==0:
                        IncorrectGroups.append(crc)
                if IncorrectGroups:
                    IncorrectGroupsStr='\n'.join(IncorrectGroups)
                    self.info_dialog_on_main.show(f'Warning (Delete) - All files marked',f"Option \"Skip groups with invalid selection\" is enabled.\n\nFolowing CRC groups will not be processed and remain with markings:\n\n{IncorrectGroupsStr}")

                    self.crc_select_and_focus(IncorrectGroups[0],True)

                for crc in IncorrectGroups:
                    del ProcessedItems[crc]
                    del RemainingItems[crc]
            else:
                ShowAllDeleteWarning=False
                for crc in ProcessedItems:
                    if len(RemainingItems[crc])==0:
                        if self.cfg.get_bool(CFG_ALLOW_DELETE_ALL):
                            ShowAllDeleteWarning=True
                        else:
                            self.info_dialog_on_main.show(f'Error (Delete) - All files marked',"Keep at least one file unmarked.",min_width=400)
                            
                            self.crc_select_and_focus(crc,True)
                            return True

                if ShowAllDeleteWarning:
                    if not self.text_ask_dialog.show('Warning !','Option: \'Allow to delete all copies\' is set.|RED\n\nAll copies in one or more groups are selected.|RED\n\nProceed ?|RED'):
                        return True

        elif action==SOFTLINK:
            for crc in ProcessedItems:
                if len(RemainingItems[crc])==0:
                    self.info_dialog_on_main.show(f'Error (Softlink) - All files marked',"Keep at least one file unmarked.",min_width=400)

                    self.crc_select_and_focus(crc,True)
                    return True

    @restore_status_line
    def process_files_check_correctness_last(self,action,ProcessedItems,RemainingItems):
        self.status('final checking selection correctness')

        if action==HARDLINK:
            for crc in ProcessedItems:
                if len({int(self.groups_tree.set(item,'dev')) for item in ProcessedItems[crc]})>1:
                    title='Can\'t create hardlinks.'
                    message=f"Files on multiple devices selected. Crc:{crc}"
                    logging.error(title)
                    logging.error(message)
                    self.info_dialog_on_main.show(title,message,min_width=400)
                    return True

        for crc in ProcessedItems:
            for item in RemainingItems[crc]:
                if res:=self.file_check_state(item):
                    self.info_dialog_on_main.show('Error',res+'\n\nNo action was taken.\n\nAborting. Repeat scanning please or unmark all files and groups affected by other programs.')
                    logging.error('aborting.')
                    return True
        logging.info('remaining files checking complete.')

    @restore_status_line
    def process_files_confirm(self,action,ProcessedItems,RemainingItems,ScopeTitle):
        self.status('confirmation required...')
        ShowFullPath=1

        message=[]
        if not self.cfg.get_bool(CFG_CONFIRM_SHOW_CRCSIZE):
            message.append('')

        for crc in ProcessedItems:
            if self.cfg.get_bool(CFG_CONFIRM_SHOW_CRCSIZE):
                size=int(self.groups_tree.set(crc,'size'))
                message.append('')
                message.append('CRC:' + crc + ' size:' + core.bytes_to_str(size) + '|GRAY')

            for item in ProcessedItems[crc]:
                message.append((self.item_full_path(item) if ShowFullPath else tree.set(item,'file')) + '|RED' )

            if action==SOFTLINK:
                if RemainingItems[crc]:
                    item = RemainingItems[crc][0]
                    if self.cfg.get_bool(CFG_CONFIRM_SHOW_LINKSTARGETS):
                        message.append('🠖 ' + (self.item_full_path(item) if ShowFullPath else self.groups_tree.set(item,'file')) )

        if action==DELETE:
            if not self.text_ask_dialog.show('Delete marked files ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message)):
                return True
        elif action==SOFTLINK:
            if not self.text_ask_dialog.show('Soft-Link marked files to first unmarked file in group ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message)):
                return True
        elif action==HARDLINK:
            if not self.text_ask_dialog.show('Hard-Link marked files together in groups ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message)):
                return True

        {logging.warning(line) for line in message}
        logging.warning('###########################################################################################')
        logging.warning('Confirmed.')

    @busy_cursor
    def empty_dirs_removal(self,startpath,ReportEmpty=False):
        string=f'Removing empty directories in:\'{startpath}\''
        self.status(string)
        self.main.update()
        logging.info(string)

        Removed=[]
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
                    logging.info(f'Empty Removed:{path}')
                    Removed.append(path)
                except Exception as e:
                    logging.error(f'empty_dirs_removal:{e}')

        self.status('')

        if ReportEmpty and not Removed:
            Removed.append(f'No empty subdirectories in:\'{startpath}\'')

        return Removed

    def process_files_core(self,action,ProcessedItems,RemainingItems):
        self.main.config(cursor="watch")
        self.menu_disable()
        self.status('processing files ...')
        self.main.update()

        FinalInfo=[]
        if action==DELETE:
            DirectoriesToCheck=set()
            for crc in ProcessedItems:
                TuplesToDelete=set()
                size=int(self.groups_tree.set(ProcessedItems[crc][0],'size'))
                for item in ProcessedItems[crc]:
                    IndexTuple=self.get_index_tuple_groups_tree(item)
                    TuplesToDelete.add(IndexTuple)
                    DirectoriesToCheck.add(self.D.get_path(IndexTuple))

                if resmsg:=self.D.delete_file_wrapper(size,crc,TuplesToDelete):
                    logging.error(resmsg)
                    self.info_dialog_on_main.show('Error',resmsg)

                self.crc_node_update(crc)

            if self.cfg.get_bool(ERASE_EMPTY_DIRS):
                DirectoriesToCheckList=list(DirectoriesToCheck)
                DirectoriesToCheckList.sort(key=lambda d : (len(str(d).split(os.sep)),d),reverse=True )

                Removed=[]
                for directory in DirectoriesToCheckList:
                    Removed.extend(self.empty_dirs_removal(directory))

                FinalInfo.extend(Removed)

        elif action==SOFTLINK:
            RelSymlink = self.cfg.get_bool(CFG_KEY_REL_SYMLINKS)
            for crc in ProcessedItems:
                toKeepItem=list(RemainingItems[crc])[0]
                #self.groups_tree.focus()
                IndexTupleRef=self.get_index_tuple_groups_tree(toKeepItem)
                size=int(self.groups_tree.set(toKeepItem,'size'))

                if resmsg:=self.D.link_wrapper(True, RelSymlink, size,crc, IndexTupleRef, [self.get_index_tuple_groups_tree(item) for item in ProcessedItems[crc] ] ):
                    logging.error(resmsg)
                    self.info_dialog_on_main.show('Error',resmsg)
                self.crc_node_update(crc)

        elif action==HARDLINK:
            for crc in ProcessedItems:
                refItem=ProcessedItems[crc][0]
                IndexTupleRef=self.get_index_tuple_groups_tree(refItem)
                size=int(self.groups_tree.set(refItem,'size'))

                if resmsg:=self.D.link_wrapper(False, False, size,crc, IndexTupleRef, [self.get_index_tuple_groups_tree(item) for item in ProcessedItems[crc][1:] ] ):
                    logging.error(resmsg)
                    self.info_dialog_on_main.show('Error',resmsg)
                self.crc_node_update(crc)

        self.main.config(cursor="")
        self.menu_enable()

        self.data_precalc()
        self.tree_groups_flat_items_update()

        if FinalInfo:
            self.info_dialog_on_main.show('Removed empty directories','\n'.join(FinalInfo),min_width=400)

    def get_this_or_existing_parent(self,path):
        if os.path.exists(path):
            return path
        else:
            return self.get_this_or_existing_parent(pathlib.Path(path).parent.absolute())

    @keep_semi_focus
    def process_files(self,action,ProcessedItems,ScopeTitle):
        tree=(self.groups_tree,self.folder_tree)[self.SelTreeIndex]

        if not ProcessedItems:
            self.info_dialog_on_main.show('No Files Marked For Processing !','Scope: ' + ScopeTitle + '\n\nMark files first.')
            return

        logging.info(f'process_files:{action}')
        logging.info('Scope ' + ScopeTitle)

        #############################################
        #check remainings

        #RemainingItems dla wszystkich (moze byc akcja z folderu)
        #istotna kolejnosc

        AffectedCRCs=ProcessedItems.keys()

        self.status('checking remaining items...')
        RemainingItems={}
        for crc in AffectedCRCs:
            RemainingItems[crc]=[item for item in self.groups_tree.get_children(crc) if not self.groups_tree.tag_has(MARK,item)]

        if self.process_files_check_correctness(action,ProcessedItems,RemainingItems):
            return

        if not ProcessedItems:
            self.info_dialog_on_main.show('info','No files left for processing. Fix files selection.',min_width=400)
            return

        logging.warning('###########################################################################################')
        logging.warning(f'action:{action}')

        self.status('')
        if self.process_files_confirm(action,ProcessedItems,RemainingItems,ScopeTitle):
            return

        #after confirmation
        if self.process_files_check_correctness_last(action,ProcessedItems,RemainingItems):
            return

        #############################################
        #action

        if tree==self.groups_tree:
            #orglist=self.groups_tree.get_children()
            orglist=self.tree_groups_flat_items
        else:
            orgSelItem=self.sel_item
            orglist=self.folder_tree.get_children()
            #orglistNames=[self.folder_tree.item(item)['values'][2] for item in self.folder_tree.get_children()]
            orgSelItemName=self.folder_tree.item(orgSelItem)['values'][2]
            #print(orglistNames)

        #############################################
        self.process_files_core(action,ProcessedItems,RemainingItems)
        #############################################

        if tree==self.groups_tree:
            #newlist=self.groups_tree.get_children()

            sel_item = self.sel_item if self.sel_item else self.SelCrc
            ItemToSel = self.get_closest_in_crc(orglist,sel_item,self.tree_groups_flat_items)

            if ItemToSel:
                self.groups_tree.see(ItemToSel)
                self.groups_tree.focus(ItemToSel)
                self.groups_tree_sel_change(ItemToSel)
            else:
                self.initial_focus()
        else:
            parent = self.get_this_or_existing_parent(self.sel_path_full)

            if self.tree_folder_update(parent):
                newlist=self.folder_tree.get_children()

                ItemToSel = self.get_closest_in_folder(orglist,orgSelItem,orgSelItemName,newlist)

                if ItemToSel:
                    self.folder_tree.focus(ItemToSel)
                    self.folder_tree_sel_change(ItemToSel)
                    self.folder_tree.see(ItemToSel)
                    self.folder_tree.update()

        self.calc_mark_stats_groups()

        self.folder_items_cache={}

        self.find_result=()

    def get_closest_in_folder(self,PrevList,item,itemName,NewList):
        if item in NewList:
            return item
        elif not NewList:
            return None
        else:
            NewlistNames=[self.folder_tree.item(item)['values'][2] for item in self.folder_tree.get_children()]

            if itemName in NewlistNames:
                return NewList[NewlistNames.index(itemName)]
            else:
                OrgIndex=PrevList.index(item)

                NewListLen=len(NewList)
                for i in range(NewListLen):
                    if (IndexM1:=OrgIndex-i) >=0:
                        Nearest = PrevList[IndexM1]
                        if Nearest in NewList:
                            return Nearest
                    elif (IndexP1:=OrgIndex+i) < NewListLen:
                        Nearest = PrevList[IndexP1]
                        if Nearest in NewList:
                            return Nearest
                    else:
                        return None

    def get_closest_in_crc(self,PrevList,item,NewList):
        if item in NewList:
            return item
        elif not NewList:
            return None
        else:
            SelIndex=PrevList.index(item)

            NewListLen=len(NewList)
            for i in range(NewListLen):
                if (IndexM1:=SelIndex-i) >=0:
                    Nearest = PrevList[IndexM1]
                    if Nearest in NewList:
                        return Nearest
                elif (IndexP1:=SelIndex+i) < NewListLen:
                    Nearest = PrevList[IndexP1]
                    if Nearest in NewList:
                        return Nearest
                else:
                    return None

    def cache_clean(self):
        try:
            shutil.rmtree(CACHE_DIR)
        except Exception as e:
            logging.error(e)

    def clip_copy_full_path_with_file(self):
        if self.sel_path_full and self.sel_file:
            self.clip_copy(os.path.join(self.sel_path_full,self.sel_file))
        elif self.SelCrc:
            self.clip_copy(self.SelCrc)

    def clip_copy_full(self):
        if self.sel_path_full:
            self.clip_copy(self.sel_path_full)
        elif self.SelCrc:
            self.clip_copy(self.SelCrc)

    def clip_copy_file(self):
        if self.sel_file:
            self.clip_copy(self.sel_file)
        elif self.SelCrc:
            self.clip_copy(self.SelCrc)

    def clip_copy(self,what):
        self.main.clipboard_clear()
        self.main.clipboard_append(what)
        self.status('Copied to clipboard: "%s"' % what)

    #@busy_cursor
    def enter_dir(self,fullpath,sel):
        if self.find_tree_index==1:
            self.find_result=()
            
        if self.tree_folder_update(fullpath):
            children=self.folder_tree.get_children()
            resList=[nodeid for nodeid in children if self.folder_tree.set(nodeid,'file')==sel]
            if resList:
                item=resList[0]
                self.folder_tree.see(item)
                self.folder_tree.focus(item)
                self.folder_tree_sel_change(item)

            elif children:
                self.folder_tree.focus(children[0])
                self.sel_file = self.groups_tree.set(children[0],'file')
                self.folder_tree_sel_change(children[0])

    def double_left_button(self,event):
        if self.do_process_events:
            tree=event.widget
            if tree.identify("region", event.x, event.y) != 'heading':
                if item:=tree.identify('item',event.x,event.y):
                    self.main.after_idle(lambda : self.tree_action(tree,item))

    def tree_action(self,tree,item):
        if tree.set(item,'kind') == UPDIR:
            head,tail=os.path.split(self.sel_path_full)
            self.enter_dir(os.path.normpath(str(pathlib.Path(self.sel_path_full).parent.absolute())),tail)
        elif tree.set(item,'kind') == DIR:
            self.enter_dir(self.sel_path_full+self.folder_tree.set(item,'file') if self.sel_path_full=='/' else os.sep.join([self.sel_path_full,self.folder_tree.set(item,'file')]),'..' )
        elif tree.set(item,'kind')!=CRC:
            self.open_file()
    
    @busy_cursor
    def open_folder(self):
        if self.sel_path_full:
            self.status(f'Opening {self.sel_path_full}')
            if windows:
                os.startfile(self.sel_path_full)
            else:
                os.system("xdg-open " + '"' + self.sel_path_full.replace("'","\'").replace("`","\`") + '"')

    #@restore_status_line
    @busy_cursor
    def open_file(self):
        if self.SelKind==FILE or self.SelKind==LINK or self.SelKind==SINGLE or self.SelKind==SINGLEHARDLINKED:
            self.status(f'Opening {self.sel_file}')
            if windows:
                os.startfile(os.sep.join([self.sel_path_full,self.sel_file]))
            else:
                os.system("xdg-open "+ '"' + os.sep.join([self.sel_path_full,self.sel_file]).replace("'","\'").replace("`","\`") + '"')
        elif self.SelKind==DIR:
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
    
    def set_status_var(self):
        self.status_var_full_path.set(self.SelFullPathToFile)
        self.set_status_var_color()

    def set_status_var_color(self):
        try:
            self.status_var_full_path_label.config(fg = ('black','red')[self.groups_tree.tag_has(MARK,self.sel_item)] )
        except Exception as e:
            self.status_var_full_path_label.config(fg = 'black')

if __name__ == "__main__":
    try:
        args = console.parse_args(version.VERSION)

        log=os.path.abspath(args.log) if args.log else LOG_DIR + os.sep + time.strftime('%Y_%m_%d_%H_%M_%S',time.localtime(time.time()) ) +'.txt'
        log_level = logging.DEBUG if args.debug else logging.INFO

        pathlib.Path(LOG_DIR).mkdir(parents=True,exist_ok=True)

        print('log:',log)

        logging.basicConfig(level=log_level,format='%(asctime)s %(levelname)s %(message)s', filename=log,filemode='w')

        debug_mode=False
        if args.debug:
            logging.debug('DEBUG LEVEL')
            debug_mode=True

        Gui(os.getcwd(),args.paths,args.exclude,args.excluderegexp,args.norun,debug_mode=debug_mode)

    except Exception as e:
        print(e)
        logging.error(e)
