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

    sel_path_full=''
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
                self.status(str(f) + ':' + str(e))
                res=None
                logging.error(str(f) + ':' + str(e))

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
                self.status(str(f) + ':' + str(e))
                res=None
                logging.error(str(f) + ':' + str(e))

            self.status(prev)
            return res
        return restore_status_line_wrapp

    #######################################################################
    action_abort=False
    def crc_progress_dialog_show(self,parent,title,ProgressMode1=None,ProgressMode2=None,Progress1LeftText=None,Progress2LeftText=None):
        self.LADParent=parent

        self.psIndex =0

        self.ProgressMode1=ProgressMode1
        self.ProgressMode2=ProgressMode2

        self.crc_progress_dialog = tk.Toplevel(parent,bg=self.bg)
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

    def crc_progress_dialog_update(self,message,progress1=None,progress2=None,progress_size_descr=None,progress_quant_descr=None,StatusInfo=None):
        prefix=''

        if StatusInfo:
            self.status(StatusInfo)
        else:
            self.status('')

        if self.progr_1_right_prev==progress_size_descr and self.progr_2_right_prev==progress_quant_descr and self.message_prev==message:
            if time.time()>self.time_without_busy_sign+1.0:
                prefix=self.PROGRESS_SIGNS[self.psIndex]
                self.psIndex=(self.psIndex+1)%4

        else:
            self.message_prev=message
            self.progr_1_right_prev=progress_size_descr
            self.progr_2_right_prev=progress_quant_descr

            self.time_without_busy_sign=time.time()

            self.Progress1Func(progress1)
            self.progr1LabRight.config(text=progress_size_descr)
            self.progr2var.set(progress2)
            self.progr2LabRight.config(text=progress_quant_descr)

        self.message.set('%s\n%s'%(prefix,message))
        self.crc_progress_dialog.update()

    other_tree={}

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
        self.main.title(f'Dude (DUplicates DEtector) {VER_TIMESTAMP}')
        self.main.protocol("WM_DELETE_WINDOW", self.exit)
        self.main.withdraw()
        self.main.update()

        self.main.minsize(1200, 800)

        self.iconphoto = PhotoImage(file = os.path.join(os.path.dirname(DUDE_FILE),'icon.png'))
        self.main.iconphoto(False, self.iconphoto)

        self.main.bind('<KeyPress-F2>', lambda event : self.settings_dialog.show(focus=self.cancel_button))
        self.main.bind('<KeyPress-F1>', lambda event : self.aboout_dialog.show())
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
        self.status_var_path=tk.StringVar()
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
        self.status_var_path.set('')

        tk.Label(status_frame_groups,width=10,textvariable=self.status_var_all_quant,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=16,text="All marked files # ",relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=10,textvariable=self.status_var_all_size,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=18,text='All marked files size: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=10,textvariable=self.status_var_groups,borderwidth=2,bg=self.bg,relief='groove',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(status_frame_groups,width=10,text='Groups: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        #tk.Label(status_frame_groups,width=8,text='Full path: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='left')
        self.status_var_full_path_label = tk.Label(status_frame_groups,textvariable=self.status_var_path,relief='flat',borderwidth=1,bg=self.bg,anchor='w')
        self.status_var_full_path_label.pack(fill='x',expand=1,side='left')
        self.status_var_full_path_label.bind("<Motion>", lambda event : self.motion_on_widget(event,'The full path of a directory shown in the bottom panel.'))
        self.status_var_full_path_label.bind("<Leave>", self.widget_leave)

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

        self.org_label={}
        self.org_label['path']='Subpath'
        self.org_label['file']='File'
        self.org_label['sizeH']='Size'
        self.org_label['instancesH']='Copies'
        self.org_label['ctimeH']='Change Time'

        self.groups_tree["columns"]=('pathnr','path','file','size','sizeH','ctime','dev','inode','crc','instances','instancesH','ctimeH','kind')

        #pathnr,path,file,ctime,dev,inode
        #self.IndexTupleIndexesWithFnCommon=((int,0),(raw,1),(raw,2),(int,5),(int,6),(int,7))

        #'pathnr','path','file','size','sizeH','ctime','dev','inode','crc','instances','ctimeH','kind' ->
        #pathnr,path,file,ctime,dev,inode
        self.IndexTupleIndexesWithFnGroups=((int,0),(raw,1),(raw,2),(int,5),(int,6),(int,7))

        #'file','size','sizeH','ctime','dev','inode','crc','instances','instances','ctimeH','kind' ->
        #file,ctime,dev,inode
        #self.IndexTupleIndexesWithFnFolder=((raw,0),(int,3),(int,4),(int,5))

        self.groups_tree["displaycolumns"]=('path','file','sizeH','instancesH','ctimeH')

        self.groups_tree.column('#0', width=120, minwidth=100, stretch=tk.NO)
        self.groups_tree.column('path', width=100, minwidth=10, stretch=tk.YES )
        self.groups_tree.column('file', width=100, minwidth=10, stretch=tk.YES )
        self.groups_tree.column('sizeH', width=80, minwidth=80, stretch=tk.NO)
        self.groups_tree.column('instancesH', width=80, minwidth=80, stretch=tk.NO)
        self.groups_tree.column('ctimeH', width=150, minwidth=100, stretch=tk.NO)

        self.groups_tree.heading('#0',text='CRC / Scan Path',anchor=tk.W)
        self.groups_tree.heading('path',anchor=tk.W )
        self.groups_tree.heading('file',anchor=tk.W )
        self.groups_tree.heading('sizeH',anchor=tk.W)
        self.groups_tree.heading('ctimeH',anchor=tk.W)
        self.groups_tree.heading('instancesH',anchor=tk.W)

        self.groups_tree.heading('sizeH', text='Size \u25BC')

        #bind_class breaks columns resizing
        self.groups_tree.bind('<ButtonPress-1>', self.tree_on_mouse_button_press)
        self.groups_tree.bind('<Control-ButtonPress-1>',  lambda event :self.tree_on_mouse_button_press(event,True) )
        self.main.unbind_class('Treeview', '<<TreeviewClose>>')

        vsb1 = tk.Scrollbar(frame_groups, orient='vertical', command=self.groups_tree.yview,takefocus=False,bg=self.bg)
        self.groups_tree.configure(yscrollcommand=vsb1.set)

        vsb1.pack(side='right',fill='y',expand=0)
        self.groups_tree.pack(fill='both',expand=1, side='left')

        self.groups_tree.bind('<Double-Button-1>', self.double_left_button)

        self.folder_tree=ttk.Treeview(frame_folder,takefocus=True,selectmode='none')

        self.folder_tree['columns']=('file','dev','inode','kind','crc','size','sizeH','ctime','ctimeH','instances','instancesH')

        self.folder_tree['displaycolumns']=('file','sizeH','instancesH','ctimeH')

        self.folder_tree.column('#0', width=120, minwidth=100, stretch=tk.NO)

        self.folder_tree.column('file', width=200, minwidth=100, stretch=tk.YES)
        self.folder_tree.column('sizeH', width=80, minwidth=80, stretch=tk.NO)
        self.folder_tree.column('instancesH', width=80, minwidth=80, stretch=tk.NO)
        self.folder_tree.column('ctimeH', width=150, minwidth=100, stretch=tk.NO)

        self.folder_tree.heading('#0',text='CRC',anchor=tk.W)
        self.folder_tree.heading('file',anchor=tk.W)
        self.folder_tree.heading('sizeH',anchor=tk.W)
        self.folder_tree.heading('instancesH',anchor=tk.W)
        self.folder_tree.heading('ctimeH',anchor=tk.W)

        for tree in [self.groups_tree,self.folder_tree]:
            for col in tree["displaycolumns"]:
                if col in self.org_label:
                    tree.heading(col,text=self.org_label[col])

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

        self.other_tree[self.folder_tree]=self.groups_tree
        self.other_tree[self.groups_tree]=self.folder_tree

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

        self.popup_folder = Menu(self.folder_tree, tearoff=0,bg=self.bg)
        self.popup_folder.bind("<FocusOut>",lambda event : self.popup_folder.unpost() )

        #######################################################################
        #scan dialog

        def pre_show():
            self.menu_disable()
            self.menubar.config(cursor="watch")
            self.hide_tooltip()
            self.menubar_unpost()

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
        self.settings_dialog=GenericDialog(self.main,self.iconphoto,self.bg,'Settings',pre_show=pre_show_settings,post_close=post_close)

        self.show_full_crc = tk.BooleanVar()
        self.show_full_paths = tk.BooleanVar()
        self.create_relative_symlinks = tk.BooleanVar()
        self.erase_empty_directories = tk.BooleanVar()

        self.allow_delete_all = tk.BooleanVar()
        self.skip_incorrect_groups = tk.BooleanVar()
        self.allow_delete_non_duplicates = tk.BooleanVar()

        self.confirm_show_crc_and_size = tk.BooleanVar()
        self.confirm_show_links_targets = tk.BooleanVar()

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

        row = 0
        lf=tk.LabelFrame(self.settings_dialog.area_main, text="Main panels",borderwidth=2,bg=self.bg)
        lf.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

        (o1:=ttk.Checkbutton(lf, text = 'Show full CRC', variable=self.show_full_crc)).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
        o1.bind("<Motion>", lambda event : self.motion_on_widget(event,'If disabled, shortest necessary prefix of full CRC wil be shown'))
        o1.bind("<Leave>", self.widget_leave)

        (o2:=ttk.Checkbutton(lf, text = 'Show full scan paths', variable=self.show_full_paths)).grid(row=1,column=0,sticky='wens',padx=3,pady=2)
        o2.bind("<Motion>", lambda event : self.motion_on_widget(event,f'If disabled, scan path numbers will be shown (e.g. {self.NUMBERS[0]},{self.NUMBERS[1]}... ) instead of full paths'))
        o2.bind("<Leave>", self.widget_leave)

        lf=tk.LabelFrame(self.settings_dialog.area_main, text="Confirmation dialogs",borderwidth=2,bg=self.bg)
        lf.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

        (o3:=ttk.Checkbutton(lf, text = 'Skip groups with invalid selection', variable=self.skip_incorrect_groups)).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
        o3.bind("<Motion>", lambda event : self.motion_on_widget(event,'Groups with incorrect marks set will abort action.\nEnable this option to skip those groups.\nFor delete or soft-link action, one file in a group \nmust remain unmarked (see below). For hardlink action,\nmore than one file in a group must be marked.'))
        o3.bind("<Leave>", self.widget_leave)

        (o4:=ttk.Checkbutton(lf, text = 'Allow deletion of all copies (WARNING!)', variable=self.allow_delete_all)).grid(row=1,column=0,sticky='wens',padx=3,pady=2)
        o4.bind("<Motion>", lambda event : self.motion_on_widget(event,'Before deleting selected files, files selection in every CRC \ngroup is checked, at least one file should remain unmarked.\nIf This option is enabled it will be possible to delete all copies'))
        o4.bind("<Leave>", self.widget_leave)

        ttk.Checkbutton(lf, text = 'Show soft links targets', variable=self.confirm_show_links_targets ).grid(row=2,column=0,sticky='wens',padx=3,pady=2)
        ttk.Checkbutton(lf, text = 'Show CRC and size', variable=self.confirm_show_crc_and_size ).grid(row=3,column=0,sticky='wens',padx=3,pady=2)

        lf=tk.LabelFrame(self.settings_dialog.area_main, text="Processing",borderwidth=2,bg=self.bg)
        lf.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

        ttk.Checkbutton(lf, text = 'Create relative symbolic links', variable=self.create_relative_symlinks                  ).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
        ttk.Checkbutton(lf, text = 'Erase remaining empty directories', variable=self.erase_empty_directories                  ).grid(row=1,column=0,sticky='wens',padx=3,pady=2)

        #ttk.Checkbutton(fr, text = 'Allow to delete regular files (WARNING!)', variable=self.allow_delete_non_duplicates        ).grid(row=row,column=0,sticky='wens',padx=3,pady=2)

        bfr=tk.Frame(self.settings_dialog.area_main,bg=self.bg)
        self.settings_dialog.area_main.grid_rowconfigure(row, weight=1); row+=1

        bfr.grid(row=row,column=0) ; row+=1

        ttk.Button(bfr, text='Set defaults',width=14, command=self.settings_reset).pack(side='left', anchor='n',padx=5,pady=5)
        ttk.Button(bfr, text='OK', width=14, command=self.settings_ok ).pack(side='left', anchor='n',padx=5,pady=5)
        self.cancel_button=ttk.Button(bfr, text='Cancel', width=14 ,command=self.settings_dialog.hide )
        self.cancel_button.pack(side='right', anchor='n',padx=5,pady=5)

        self.settings_dialog.area_main.grid_columnconfigure(0, weight=1)

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
        self.aboout_dialog=GenericDialog(self.main,self.iconphoto,self.bg,'',pre_show=pre_show,post_close=post_close)

        frame1 = tk.LabelFrame(self.aboout_dialog.area_main,text='',bd=2,bg=self.bg,takefocus=False)
        frame1.grid(row=0,column=0,sticky='news',padx=4,pady=(4,2))
        self.aboout_dialog.area_main.grid_rowconfigure(1, weight=1)

        text= f'\n\nDUDE (DUplicates DEtector) {VER_TIMESTAMP}\nAuthor: Piotr Jochymek\n\n{HOMEPAGE}\n\nPJ.soft.dev.x@gmail.com\n\n'

        tk.Label(frame1,text=text,bg=self.bg,justify='center').pack(expand=1,fill='both')

        frame2 = tk.LabelFrame(self.aboout_dialog.area_main,text='',bd=2,bg=self.bg,takefocus=False)
        frame2.grid(row=1,column=0,sticky='news',padx=4,pady=(2,4))
        lab2_text=  'LOGS DIRECTORY     :  ' + LOG_DIR + '\n' + \
                    'SETTINGS DIRECTORY :  ' + CONFIG_DIR + '\n' + \
                    'CACHE DIRECTORY    :  ' + CACHE_DIR + '\n\n' + \
                    'LOGGING LEVEL      :  ' + log_levels[log_level] + '\n\n' + \
                    'Current log file   :  ' + log

        lab_courier = tk.Label(frame2,text=lab2_text,bg=self.bg,justify='left')
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
        logging.debug('DUDE_FILE:%s' % DUDE_FILE )

        try:
            self.license=pathlib.Path(os.path.join(os.path.dirname(DUDE_FILE),'LICENSE')).read_text()
        except Exception as e:
            logging.error(e)
            try:
                self.license=pathlib.Path(os.path.join(os.path.dirname(os.path.dirname(DUDE_FILE)),'LICENSE')).read_text()
            except Exception as e:
                logging.error(e)
                self.exit()

        self.license_dialog=GenericDialog(self.main,self.iconphoto,self.bg,'',pre_show=pre_show,post_close=post_close,min_width=800,min_height=520)

        frame1 = tk.LabelFrame(self.license_dialog.area_main,text='',bd=2,bg=self.bg,takefocus=False)
        frame1.grid(row=0,column=0,sticky='news',padx=4,pady=4)
        self.license_dialog.area_main.grid_rowconfigure(0, weight=1)

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
            item_actions_state=('disabled','normal')[self.sel_item!=None]

            self.file_cascade.add_command(label = 'Scan ...',command = self.scan_dialog_show, accelerator="S")
            self.file_cascade.add_separator()
            self.file_cascade.add_command(label = 'Settings ...',command= lambda : self.settings_dialog.show(focus=self.cancel_button), accelerator="F2")
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
            item_actions_state=('disabled','normal')[self.sel_item!=None]
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

        self.navi_cascade= Menu(self.menubar,tearoff=0,bg=self.bg,postcommand=navi_cascade_post)

        self.menubar.add_cascade(label = 'Navigation',menu = self.navi_cascade)

        self.HelpCascade= Menu(self.menubar,tearoff=0,bg=self.bg)
        self.HelpCascade.add_command(label = 'About',command=self.aboout_dialog.show,accelerator="F1")
        self.HelpCascade.add_command(label = 'License',command=self.license_dialog.show)
        self.HelpCascade.add_separator()
        self.HelpCascade.add_command(label = 'Open current Log',command=self.show_log)
        self.HelpCascade.add_command(label = 'Open logs directory',command=self.show_logs_dir)
        self.HelpCascade.add_separator()
        self.HelpCascade.add_command(label = 'Open homepage',command=self.show_homepage)

        self.menubar.add_cascade(label = 'Help',menu = self.HelpCascade)

        #######################################################################
        self.reset_sels()

        self.REAL_SORT_COLUMN={}
        self.REAL_SORT_COLUMN['path'] = 'path'
        self.REAL_SORT_COLUMN['file'] = 'file'
        self.REAL_SORT_COLUMN['sizeH'] = 'size'
        self.REAL_SORT_COLUMN['ctimeH'] = 'ctime'
        self.REAL_SORT_COLUMN['instancesH'] = 'instances'
        
        #self.folder_tree['columns']=('file','dev','inode','kind','crc','size','sizeH','ctime','ctimeH','instances','instancesH')
        self.REAL_SORT_COLUMN_INDEX={}
        self.REAL_SORT_COLUMN_INDEX['path'] = 0
        self.REAL_SORT_COLUMN_INDEX['file'] = 1
        self.REAL_SORT_COLUMN_INDEX['sizeH'] = 6
        self.REAL_SORT_COLUMN_INDEX['ctimeH'] = 8
        self.REAL_SORT_COLUMN_INDEX['instancesH'] = 10
        
        self.REAL_SORT_COLUMN_IS_NUMERIC={}
        self.REAL_SORT_COLUMN_IS_NUMERIC['path'] = False
        self.REAL_SORT_COLUMN_IS_NUMERIC['file'] = False
        self.REAL_SORT_COLUMN_IS_NUMERIC['sizeH'] = True
        self.REAL_SORT_COLUMN_IS_NUMERIC['ctimeH'] = True
        self.REAL_SORT_COLUMN_IS_NUMERIC['instancesH'] = True
        
        self.column_sort_last_params={}
        #colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code

        self.column_sort_last_params[self.groups_tree]=self.column_groups_sort_params_default=('sizeH',self.REAL_SORT_COLUMN_INDEX['sizeH'],self.REAL_SORT_COLUMN_IS_NUMERIC['sizeH'],1,2,1,0)
        self.column_sort_last_params[self.folder_tree]=('file',self.REAL_SORT_COLUMN_INDEX['file'],self.REAL_SORT_COLUMN_IS_NUMERIC['file'],0,0,1,2)

        self.sel_item_of_tree[self.groups_tree]=None
        self.sel_item_of_tree[self.folder_tree]=None

        self.groups_show()

        #######################################################################

        self.tooltip = tk.Toplevel(self.main)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip_lab=tk.Label(self.tooltip, justify='left', background="#ffffe0", relief='solid', borderwidth=0, wraplength = 1200)
        self.tooltip_lab.pack(ipadx=1)

        self.tooltip.withdraw()

        self.groups_tree.bind("<Motion>", self.motion_on_groups_tree)
        self.folder_tree.bind("<Motion>", self.motion_on_folder_tree)

        self.groups_tree.bind("<Leave>", self.widget_leave)
        self.folder_tree.bind("<Leave>", self.widget_leave)

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
    tooltip_show_after_widget=''

    def widget_leave(self,event):
        self.menubar_unpost()
        self.hide_tooltip()

    def motion_on_widget(self,event,message):
        self.tooltip_show_after_widget = event.widget.after(1, self.show_tooltip_widet(event,message))

    def motion_on_groups_tree(self,event):
        self.tooltip_show_after_groups = event.widget.after(1, self.show_tooltip_groups(event))

    def motion_on_folder_tree(self,event):
        self.tooltip_show_after_folder = event.widget.after(1, self.show_tooltip_folder(event))

    def show_tooltip_widet(self,event,message):
        self.unschedule_tooltip_widget()
        self.menubar_unpost()

        self.tooltip_lab.configure(text=message)

        self.tooltip.deiconify()
        self.tooltip.wm_geometry("+%d+%d" % (event.x_root + 20, event.y_root + 5))

        #self.hide_tooltip()

    def show_tooltip_groups(self,event):
        self.unschedule_tooltip_groups()
        self.menubar_unpost()

        self.tooltip.wm_geometry("+%d+%d" % (event.x_root + 20, event.y_root + 5))

        tree = event.widget
        col=tree.identify_column(event.x)
        if col:
            colname=tree.column(col,'id')
            if tree.identify("region", event.x, event.y) == 'heading':
                if colname in ('path','sizeH','file','instancesH','ctimeH'):
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
                            self.tooltip_lab.configure(text='%s - %s' % (self.NUMBERS[pathnr],self.D.scanned_paths[pathnr]) )
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
                    #    file_path = os.path.abspath(self.D.get_full_path_scanned(pathnr,path,file))
                    if coldata:
                        self.tooltip_lab.configure(text=coldata)
                        self.tooltip.deiconify()

                    else:
                        self.hide_tooltip()

    def show_tooltip_folder(self,event):
        self.unschedule_tooltip_folder()
        self.menubar_unpost()

        self.tooltip.wm_geometry("+%d+%d" % (event.x_root + 20, event.y_root + 5))

        tree = event.widget
        col=tree.identify_column(event.x)
        if col:
            colname=tree.column(col,'id')
            if tree.identify("region", event.x, event.y) == 'heading':
                if colname in ('sizeH','file','instancesH','ctimeH'):
                    self.tooltip_lab.configure(text='Sort by %s' % self.org_label[colname])
                    self.tooltip.deiconify()
                else:
                    self.hide_tooltip()
            elif item := tree.identify('item', event.x, event.y):
                #pathnrstr=tree.set(item,'pathnr')

                coldata=''

                if col=="#0" :
                    coldata=''
                elif col:
                    coldata=tree.set(item,col)

                #if pathnrstr:
                #    pathnr=int(pathnrstr)
                #    path=tree.set(item,'path')
                #    file=tree.set(item,'file')
                #    file_path = os.path.abspath(self.D.get_full_path_scanned(pathnr,path,file))
                if coldata:
                    self.tooltip_lab.configure(text=coldata)
                    self.tooltip.deiconify()
                else:
                    self.hide_tooltip()

    def unschedule_tooltip_widget(self):
        if self.tooltip_show_after_widget:
            self.widget.after_cancel(self.tooltip_show_after_widget)
            self.tooltip_show_after_widget = None

    def unschedule_tooltip_groups(self):
        #id = self.tooltip_show_after_groups
        if self.tooltip_show_after_groups:
            self.widget.after_cancel(self.tooltip_show_after_groups)
            self.tooltip_show_after_groups = None

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
        self.sel_crc = None
        self.sel_item = None
        #self.SelItemIsMarked = False

        self.sel_item_of_tree[self.groups_tree]=None
        self.sel_item_of_tree[self.folder_tree]=None

        self.sel_tree_index = 0
        self.sel_kind = None

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

    find_by_tree={}

    def finder_wrapper_show(self):
        tree=self.groups_tree if self.sel_tree_index==0 else self.folder_tree

        self.find_dialog_shown=True

        scope_info = 'Scope: All groups.' if self.sel_tree_index==0 else 'Scope: Selected directory.'

        if tree in self.find_by_tree:
            initialvalue=self.find_by_tree[tree]
        else:
            initialvalue='*'

        self.find_dialog_on_main.show(scope_info,initial=initialvalue,checkbutton_initial=False)

        self.find_by_tree[tree]=self.find_dialog_on_main.entry.get()

        self.find_dialog_shown=False

        selList=tree.selection()

        self.from_tab_switch=True
        tree.focus_set()

    def find_prev_from_dialog(self,expression,use_reg_expr,event=None):
        self.find_items(expression,use_reg_expr)
        self.select_find_result(-1)

    def find_prev(self):
        if not self.find_result or self.find_tree_index!=self.sel_tree_index:
            self.find_params_changed=True
            self.finder_wrapper_show()
        else:
            self.select_find_result(-1)

    def find_next_from_dialog(self,expression,use_reg_expr,event=None):
        self.find_items(expression,use_reg_expr)
        self.select_find_result(1)

    def find_next(self):
        if not self.find_result or self.find_tree_index!=self.sel_tree_index:
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
            self.find_tree_index=self.sel_tree_index

            items=[]

            if expression:
                if self.sel_tree_index==0:
                    self.find_tree=self.groups_tree
                    crc_range = self.groups_tree.get_children()

                    try:
                        for crcitem in crc_range:
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
                scope_info = 'Scope: All groups.' if self.find_tree_index==0 else 'Scope: Selected directory.'
                self.info_dialog_on_find.show(scope_info,'No files found.',min_width=400)

    @busy_cursor
    def select_find_result(self,mod):
        if self.find_result:
            itemsLen=len(self.find_result)
            self.find_result_index+=mod
            next_item=self.find_result[self.find_result_index%itemsLen]

            if self.find_dialog_shown:
                #focus is still on find dialog
                self.find_tree.selection_set(next_item)
            else:
                self.find_tree.focus_set()
                self.find_tree.focus(next_item)

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
        self.hide_tooltip()
        self.menubar_unpost()

        try:
            tree=event.widget
            item=tree.focus()

            if sel:=tree.selection() : tree.selection_remove(sel)

            if event.keysym in ("Up",'Down') :
                (pool,poolLen) = (self.tree_groups_flat_items,len(self.tree_groups_flat_items) ) if self.sel_tree_index==0 else (self.TreeFolderFlatItemsList,len(self.TreeFolderFlatItemsList))

                if poolLen:
                    index = pool.index(self.sel_item) if self.sel_item in pool else pool.index(self.sel_item_of_tree[tree]) if self.sel_item_of_tree[tree] in pool else pool.index(item) if item in  pool else 0
                    index=(index+self.KEY_DIRECTION[event.keysym])%poolLen
                    next_item=pool[index]

                    tree.focus(next_item)
                    tree.see(next_item)

                    if self.sel_tree_index==0:
                        self.groups_tree_sel_change(next_item)
                    else:
                        self.folder_tree_sel_change(next_item)
            elif event.keysym in ("Prior","Next"):
                if self.sel_tree_index==0:
                    pool=tree.get_children()
                else:
                    pool=[item for item in tree.get_children() if tree.set(item,'kind')==FILE]

                poolLen=len(pool)
                if poolLen:
                    if self.sel_tree_index==0:
                        next_item=pool[(pool.index(tree.set(item,'crc'))+self.KEY_DIRECTION[event.keysym]) % poolLen]
                        self.crc_select_and_focus(next_item)
                    else:
                        self.goto_next_dupe_file(tree,self.KEY_DIRECTION[event.keysym])
                        tree.update()
            elif event.keysym in ("Home","End"):
                if self.sel_tree_index==0:
                    if next_item:=tree.get_children()[0 if event.keysym=="Home" else -1]:
                        self.crc_select_and_focus(next_item,True)
                else:
                    if next_item:=tree.get_children()[0 if event.keysym=='Home' else -1]:
                        tree.see(next_item)
                        tree.focus(next_item)
                        self.folder_tree_sel_change(next_item)
                        tree.update()
            elif event.keysym == "space":
                if self.sel_tree_index==0:
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
                    if self.sel_tree_index==0:
                        self.process_files_in_groups_wrapper(DELETE,ctrl_pressed)
                    else:
                        self.process_files_in_folder_wrapper(DELETE,self.sel_kind==DIR)
                elif event.keysym == "Insert":
                    if self.sel_tree_index==0:
                        self.process_files_in_groups_wrapper((SOFTLINK,HARDLINK)[shift_pressed],ctrl_pressed)
                    else:
                        self.process_files_in_folder_wrapper((SOFTLINK,HARDLINK)[shift_pressed],self.sel_kind==DIR)
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
                        if self.sel_tree_index==0:
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
                        if self.sel_tree_index==0:
                            self.mark_in_group_by_ctime('oldest',self.invert_mark)
                elif event.keysym=='y' or event.keysym=='Y':
                    if ctrl_pressed:
                        if shift_pressed:
                            self.mark_all_by_ctime('youngest',self.unset_mark)
                        else:
                            self.mark_all_by_ctime('youngest',self.set_mark)
                    else:
                        if self.sel_tree_index==0:
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
                    if self.sel_tree_index==0:
                        if ctrl_pressed:
                            self.mark_on_all(self.set_mark)
                        else:
                            self.mark_in_group(self.set_mark)
                    else:
                        self.mark_in_folder(self.set_mark)

                elif event.keysym=='n' or event.keysym=='N':
                    if self.sel_tree_index==0:
                        if ctrl_pressed:
                            self.mark_on_all(self.unset_mark)
                        else:
                            self.mark_in_group(self.unset_mark)
                    else:
                        self.mark_in_folder(self.unset_mark)
                elif event.keysym=='r' or event.keysym=='R':
                    if self.sel_tree_index==1:
                        self.tree_folder_update()
                        self.folder_tree.focus_set()
                        try:
                            self.folder_tree.focus(self.sel_item)
                        except Exception :
                            pass
                elif event.keysym in self.reftuple1:
                    index = self.reftuple1.index(event.keysym)

                    if index<len(self.D.scanned_paths):
                        if self.sel_tree_index==0:
                            self.action_on_path(self.D.scanned_paths[index],self.set_mark,ctrl_pressed)
                elif event.keysym in self.reftuple2:
                    index = self.reftuple2.index(event.keysym)

                    if index<len(self.D.scanned_paths):
                        if self.sel_tree_index==0:
                            self.action_on_path(self.D.scanned_paths[index],self.unset_mark,ctrl_pressed)
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

    from_tab_switch=False
    def tree_on_focus_in(self,event):
        tree=event.widget

        tree.configure(style='semi_focus.Treeview')
        self.other_tree[tree].configure(style='default.Treeview')

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

    def groups_tree_sel_change(self,item,force=False,ChangeStatusLine=True):
        if ChangeStatusLine : self.status('')

        pathnr=self.groups_tree.set(item,'pathnr')
        path=self.groups_tree.set(item,'path')

        self.sel_file = self.groups_tree.set(item,'file')
        newCrc = self.groups_tree.set(item,'crc')

        if self.sel_crc != newCrc:
            self.sel_crc = newCrc

            self.dominant_groups_index[0] = -1
            self.dominant_groups_index[1] = -1

        self.sel_item = item
        self.sel_item_of_tree[self.groups_tree]=item
        self.sel_tree_index=0

        #self.SelItemIsMarked = self.groups_tree.tag_has(MARK,item)

        size = int(self.groups_tree.set(item,'size'))

        if path!=self.sel_path or pathnr!=self.sel_path_nr or force:
            self.sel_path_nr = pathnr

            if self.find_tree_index==1:
                self.find_result=()

            if pathnr: #non crc node
                self.SelPathnrInt= int(pathnr)
                self.SelSearchPath = self.D.scanned_paths[self.SelPathnrInt]
                self.sel_path = path
                self.sel_path_set(self.SelSearchPath+self.sel_path)
            else :
                self.SelPathnrInt= 0
                self.SelSearchPath = None
                self.sel_path = None
                self.sel_path_set(None)
            self.set_full_path_to_file()

        self.sel_kind = self.groups_tree.set(item,'kind')
        if self.sel_kind==FILE:
            self.tree_folder_update()
        else:
            self.tree_folder_update_none()

    def folder_tree_sel_change(self,item,ChangeStatusLine=True):
        self.sel_file = self.folder_tree.set(item,'file')
        self.sel_crc = self.folder_tree.set(item,'crc')
        self.sel_kind = self.folder_tree.set(item,'kind')
        self.sel_item = item
        self.sel_item_of_tree[self.folder_tree] = item
        self.sel_tree_index=1

        #self.SelItemIsMarked = self.folder_tree.tag_has(MARK,item)

        self.set_full_path_to_file()

        kind=self.folder_tree.set(item,'kind')
        if kind==FILE:
            if ChangeStatusLine: self.status('')
            self.groups_tree_update(item)
        else:
            if kind==LINK:
                if ChangeStatusLine: self.status('  🠖  ' + os.readlink(self.sel_full_path_to_file))
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
            logging.error(e)

    def context_menu_show(self,event):
        if not self.do_process_events:
            return

        tree=event.widget

        if tree.identify("region", event.x, event.y) == 'heading':
            return

        tree.focus_set()
        self.tree_on_mouse_button_press(event)
        tree.update()

        item_actions_state=('disabled','normal')[self.sel_item!=None]

        pop=self.popup_groups if tree==self.groups_tree else self.popup_folder

        pop.delete(0,END)

        FileActionsState=('disabled',item_actions_state)[self.sel_kind==FILE]

        parent_dir_state = ('disabled','normal')[self.two_dots_condition() and self.sel_kind!=CRC]

        if tree==self.groups_tree:
            cLocal = Menu(pop,tearoff=0,bg=self.bg)
            cLocal.add_command(label = "Toggle Mark",  command = lambda : self.tag_toggle_selected(tree,self.sel_item),accelerator="space")
            cLocal.add_separator()
            cLocal.add_command(label = "Mark all files",        command = lambda : self.mark_in_group(self.set_mark),accelerator="A")
            cLocal.add_command(label = "Unmark all files",        command = lambda : self.mark_in_group(self.unset_mark),accelerator="N")
            cLocal.add_separator()
            cLocal.add_command(label = 'Mark By expression ...',command = lambda : self.mark_expression(self.set_mark,'Mark files',False),accelerator="+")
            cLocal.add_command(label = 'Unmark By expression ...',command = lambda : self.mark_expression(self.unset_mark,'Unmark files',False),accelerator="-")
            cLocal.add_separator()
            cLocal.add_command(label = "Toggle mark on oldest file",     command = lambda : self.mark_in_group_by_ctime('oldest',self.invert_mark),accelerator="O")
            cLocal.add_command(label = "Toggle mark on youngest file",   command = lambda : self.mark_in_group_by_ctime('youngest',self.invert_mark),accelerator="Y")
            cLocal.add_separator()
            cLocal.add_command(label = "Invert marks",   command = lambda : self.mark_in_group(self.invert_mark),accelerator="I")
            cLocal.add_separator()

            MarkCascadePath = Menu(cLocal, tearoff = 0,bg=self.bg)
            UnmarkCascadePath = Menu(cLocal, tearoff = 0,bg=self.bg)

            row=0
            for path in self.D.scanned_paths:
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

            cLocal.add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(DELETE,0),accelerator="Delete",state=MarksState)
            cLocal.entryconfig(19,foreground='red',activeforeground='red')
            cLocal.add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(SOFTLINK,0),accelerator="Insert",state=MarksState)
            cLocal.entryconfig(20,foreground='red',activeforeground='red')
            cLocal.add_command(label = 'Hardlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(HARDLINK,0),accelerator="Shift+Insert",state=MarksState)
            cLocal.entryconfig(21,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'Local (this CRC group)',menu = cLocal,state=item_actions_state)
            pop.add_separator()

            cAll = Menu(pop,tearoff=0,bg=self.bg)

            cAll.add_command(label = "Mark all files",        command = lambda : self.mark_on_all(self.set_mark),accelerator="Ctrl+A")
            cAll.add_command(label = "Unmark all files",        command = lambda : self.mark_on_all(self.unset_mark),accelerator="Ctrl+N")
            cAll.add_separator()
            cAll.add_command(label = 'Mark By expression ...',command = lambda : self.mark_expression(self.set_mark,'Mark files',True),accelerator="Ctrl+")
            cAll.add_command(label = 'Unmark By expression ...',command = lambda : self.mark_expression(self.unset_mark,'Unmark files',True),accelerator="Ctrl-")
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
            for path in self.D.scanned_paths:
                MarkCascadePath.add_command(label = self.NUMBERS[row] + '  =  ' + path,    command  = lambda pathpar=path: self.action_on_path(pathpar,self.set_mark,True) ,accelerator="Ctrl+"+str(row+1) )
                UnmarkCascadePath.add_command(label = self.NUMBERS[row] + '  =  ' + path,  command  = lambda pathpar=path: self.action_on_path(pathpar,self.unset_mark,True) ,accelerator="Ctrl+Shift+"+str(row+1) )
                row+=1

            cAll.add_command(label = "Mark on specified directory ...",   command = lambda : self.mark_subpath(self.set_mark,True))
            cAll.add_command(label = "Unmark on specified directory ...",   command = lambda : self.mark_subpath(self.unset_mark,True))
            cAll.add_separator()

            cAll.add_cascade(label = "Mark on scan path",             menu = MarkCascadePath)
            cAll.add_cascade(label = "Unmark on scan path",             menu = UnmarkCascadePath)
            cAll.add_separator()

            cAll.add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(DELETE,1),accelerator="Ctrl+Delete",state=MarksState)
            cAll.entryconfig(21,foreground='red',activeforeground='red')
            cAll.add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(SOFTLINK,1),accelerator="Ctrl+Insert",state=MarksState)
            cAll.entryconfig(22,foreground='red',activeforeground='red')
            cAll.add_command(label = 'Hardlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(HARDLINK,1),accelerator="Ctrl+Shift+Insert",state=MarksState)
            cAll.entryconfig(23,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'All Files',menu = cAll,state=item_actions_state)

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
            DirActionsState=('disabled','normal')[self.sel_kind==DIR]

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

            cLocal.add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_folder_wrapper(DELETE,0),accelerator="Delete",state=MarksState)
            cLocal.add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_folder_wrapper(SOFTLINK,0),accelerator="Insert",state=MarksState)
            #cLocal.add_command(label = 'Hardlink Marked Files',command=lambda : self.process_files_in_folder_wrapper(HARDLINK,0),accelerator="Shift+Insert",state=MarksState)

            cLocal.entryconfig(8,foreground='red',activeforeground='red')
            cLocal.entryconfig(9,foreground='red',activeforeground='red')
            #cLocal.entryconfig(10,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'Local (this folder)',menu = cLocal,state=item_actions_state)
            pop.add_separator()

            cSelSub = Menu(pop,tearoff=0,bg=self.bg)
            cSelSub.add_command(label = "Mark All Duplicates in Subdirectory",  command = lambda : self.sel_dir(self.set_mark),accelerator="D",state=DirActionsState)
            cSelSub.add_command(label = "Unmark All Duplicates in Subdirectory",  command = lambda : self.sel_dir(self.unset_mark),accelerator="Shift+D",state=DirActionsState)
            cSelSub.add_separator()

            cSelSub.add_command(label = 'Remove Marked Files in Subdirectory Tree ...',command=lambda : self.process_files_in_folder_wrapper(DELETE,True),accelerator="Delete",state=DirActionsState)
            cSelSub.add_command(label = 'Softlink Marked Files in Subdirectory Tree ...',command=lambda : self.process_files_in_folder_wrapper(SOFTLINK,True),accelerator="Insert",state=DirActionsState)
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
        pop.add_cascade(label = 'Navigation',menu = cNav,state=item_actions_state)

        pop.add_separator()
        pop.add_command(label = 'Open File',command = self.open_file,accelerator="Return",state=FileActionsState)
        pop.add_command(label = 'Open Folder',command = self.open_folder,state=FileActionsState)

        pop.add_separator()
        pop.add_command(label = 'Scan ...',  command = self.scan_dialog_show,accelerator='S')
        pop.add_command(label = 'Settings ...',  command = lambda : self.settings_dialog.show(focus=self.cancel_button),accelerator='F2')
        pop.add_separator()
        pop.add_command(label = 'Copy full path',command = self.clip_copy_full_path_with_file,accelerator='Ctrl+C',state = 'normal' if (self.sel_kind and self.sel_kind!=CRC) else 'disabled')
        #pop.add_command(label = 'Copy only path',command = self.clip_copy_full,accelerator="C",state = 'normal' if self.sel_item!=None else 'disabled')
        pop.add_separator()
        pop.add_command(label = 'Find ...',command = self.finder_wrapper_show,accelerator="F",state = 'normal' if self.sel_item!=None else 'disabled')
        pop.add_command(label = 'Find next',command = self.find_next,accelerator="F3",state = 'normal' if self.sel_item!=None else 'disabled')
        pop.add_command(label = 'Find prev',command = self.find_prev,accelerator="Shift+F3",state = 'normal' if self.sel_item!=None else 'disabled')
        pop.add_separator()

        pop.add_command(label = "Exit",  command = self.exit)

        try:
            pop.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            print(e)

        pop.grab_release()

    def empty_folder_remove_ask(self):
        if res:=tk.filedialog.askdirectory(title='Select Directory',initialdir=self.cwd,parent=self.main):
            final_info = self.empty_dirs_removal(res,True)

            self.info_dialog_on_main.show('Removed empty directories','\n'.join(final_info),min_width=800)

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

    def tree_sort_item(self,tree,parent_item,TreeWithDirs):
        colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[tree]
        
        real_column_to_sort=self.REAL_SORT_COLUMN[colname]
        
        tlist=[]
        for item in (tree.get_children(parent_item) if parent_item else tree.get_children(parent_item)):
            sortval_org=tree.set(item,real_column_to_sort)
            sortval=(float(sortval_org) if sortval_org.isdigit() else 0) if is_numeric else sortval_org
            
            if TreeWithDirs:
                kind = tree.set(item,'kind')
                code=updir_code if kind==UPDIR else dir_code if kind==DIR else non_dir_code
                tlist.append( ( (code,sortval),item) )
            else:
                tlist.append( (sortval,item) )


        tlist.sort(reverse=reverse,key=lambda x: x[0])
        #tlist.sort(reverse=reverse,key=lambda x: ( (x[0][0],float(x[0][1])) if x[0][1].isdigit() else (x[0][0],0) ) if self.REAL_SORT_COLUMN_IS_NUMERIC[colname] else x[0])
        if parent_item:
            {tree.move(item, parent_item, index) for index,(val_tuple,item) in enumerate(tlist)}
        else :
            {tree.move(item,'', index) for index,(val_tuple,item) in enumerate(tlist)}
        
    @busy_cursor
    @restore_status_line
    def column_sort(self, tree):
        self.status('Sorting...')
        colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[tree]

        self.column_sort_set_arrow(tree)

        if tree==self.groups_tree:
            if colname in ('path','file'):
                for crc in tree.get_children():
                    self.tree_sort_item(tree,crc,False)
            else:
                self.tree_sort_item(tree,None,False)
            
            self.tree_groups_flat_items_update()
        else:
            self.tree_sort_item(tree,0,True)
        
        tree.update()
        
    def column_sort_set_arrow(self, tree):
        colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[tree]
        tree.heading(colname, text=self.org_label[colname] + ' ' + str(u'\u25BC' if reverse else u'\u25B2') )

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
        self.status_var_path.set('')
        self.groups_show()

        paths_to_scan_from_entry = [var.get() for var in self.paths_to_scan_entry_var.values()]
        exclude_from_entry = [var.get() for var in self.exclude_entry_var.values()]

        if res:=self.D.set_exclude_masks(self.cfg.get_bool(CFG_KEY_EXCLUDE_REGEXP),exclude_from_entry):
            self.info_dialog_on_scan.show('Error. Fix Exclude masks.',res)
            return False
        self.cfg.set(CFG_KEY_EXCLUDE,'|'.join(exclude_from_entry))

        if not paths_to_scan_from_entry:
            self.info_dialog_on_scan.show('Error. No paths to scan.','Add paths to scan.',min_width=400)
            return False

        if res:=self.D.set_paths_to_scan(paths_to_scan_from_entry):
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
                info =  'Active Threads: ' + self.D.info_threads \
                    + '\nAvarage speed: ' + core.bytes_to_str(self.D.info_speed,1) + '/s\n\n'

            info = info + 'Results:' \
                + '\nCRC groups: ' + str(self.D.info_found_groups) \
                + '\nfolders: ' + str(self.D.info_found_folders) \
                + '\nspace: ' + core.bytes_to_str(self.D.info_found_dupe_space)

            info_progress_size=float(100)*float(self.D.info_size_done)/float(self.D.sim_size)
            info_progress_quantity=float(100)*float(self.D.info_files_done)/float(self.D.info_total)

            progress_size_descr=core.bytes_to_str(self.D.info_size_done) + '/' + core.bytes_to_str(self.D.sim_size)
            progress_quant_descr=str(self.D.info_files_done) + '/' + str(self.D.info_total)

            self.crc_progress_dialog_update(info,info_progress_size,info_progress_quantity,progress_size_descr,progress_quant_descr,self.D.InfoLine)

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

        if self.D.scanned_paths:
            self.paths_to_scan_from_dialog=self.D.scanned_paths.copy()

    def paths_to_scan_update(self) :
        for subframe in self.paths_to_scan_frames:
            subframe.destroy()

        self.paths_to_scan_frames=[]
        self.paths_to_scan_entry_var={}

        row=0
        for path in self.paths_to_scan_from_dialog:
            (fr:=tk.Frame(self.pathsFrame,bg=self.bg)).grid(row=row,column=0,sticky='news',columnspan=3)
            self.paths_to_scan_frames.append(fr)

            tk.Label(fr,text=' ' + self.NUMBERS[row] + ' ' , relief='groove',bg=self.bg).pack(side='left',padx=2,pady=1,fill='y')

            self.paths_to_scan_entry_var[row]=tk.StringVar(value=path)
            ttk.Entry(fr,textvariable=self.paths_to_scan_entry_var[row]).pack(side='left',expand=1,fill='both',pady=1)

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
        self.exclude_entry_var={}

        ttk.Checkbutton(self.exclude_frame,text='Use regular expressions matching',variable=self.exclude_regexp_scan,command=lambda : self.exclude_regexp_set()).grid(row=0,column=0,sticky='news',columnspan=3,padx=5)

        row=1

        for entry in self.cfg.get(CFG_KEY_EXCLUDE,'').split('|'):
            if entry:
                (fr:=tk.Frame(self.exclude_frame,bg=self.bg)).grid(row=row,column=0,sticky='news',columnspan=3)
                self.exclude_frames.append(fr)

                self.exclude_entry_var[row]=tk.StringVar(value=entry)
                ttk.Entry(fr,textvariable=self.exclude_entry_var[row]).pack(side='left',expand=1,fill='both',pady=1)

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
        {var.set(cfg_defaults[key]) for var,key in self.settings}

    def crc_node_update(self,crc):
        size=int(self.groups_tree.set(crc,'size'))

        crc_removed=False
        if not size in self.D.files_of_size_of_crc:
            self.groups_tree.delete(crc)
            logging.debug('crc_node_update-1 ' + crc)
            crc_removed=True
        elif crc not in self.D.files_of_size_of_crc[size]:
            self.groups_tree.delete(crc)
            logging.debug('crc_node_update-2 ' + crc)
            crc_removed=True
        else:
            crc_dict=self.D.files_of_size_of_crc[size][crc]
            for item in list(self.groups_tree.get_children(crc)):
                IndexTuple=self.get_index_tuple_groups_tree(item)

                if IndexTuple not in crc_dict:
                    self.groups_tree.delete(item)
                    logging.debug('crc_node_update-3 ' + item)

            if not self.groups_tree.get_children(crc):
                self.groups_tree.delete(crc)
                logging.debug('crc_node_update-4 ' + crc)
                crc_removed=True

    def data_precalc(self):
        self.status('Precalculating data...')

        self.cache_by_id_ctime = { (self.idfunc(inode,dev),ctime):(crc,self.D.crccut[crc],len(self.D.files_of_size_of_crc[size][crc]) ) for size,size_dict in self.D.files_of_size_of_crc.items() for crc,crc_dict in size_dict.items() for pathnr,path,file,ctime,dev,inode in crc_dict }
        self.status_var_groups.set(len(self.groups_tree.get_children()))

        path_stat_size={}
        path_stat_quant={}

        self.BiggestFileOfPath={}
        self.biggest_file_of_path_id={}

        for size,size_dict in self.D.files_of_size_of_crc.items() :
            for crc,crc_dict in size_dict.items():
                for pathnr,path,file,ctime,dev,inode in crc_dict:
                    path_index=(pathnr,path)
                    path_stat_size[path_index] = path_stat_size.get(path_index,0) + size
                    path_stat_quant[path_index] = path_stat_quant.get(path_index,0) + 1

                    if size>self.BiggestFileOfPath.get(path_index,0):
                        self.BiggestFileOfPath[path_index]=size
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

    @busy_cursor
    def groups_show(self):
        self.status('Rendering data...')

        self.idfunc = (lambda i,d : '%s-%s'%(i,d)) if len(self.D.devs)>1 else (lambda i,d : str(i))

        self.reset_sels()
        self.groups_tree.delete(*self.groups_tree.get_children())

        sizes_counter=0
        for size,size_dict in self.D.files_of_size_of_crc.items() :
            size_str = core.bytes_to_str(size)
            if not sizes_counter%64:
                self.status('Rendering data... (%s)' % size_str)

            sizes_counter+=1
            for crc,crc_dict in size_dict.items():
                #self.groups_tree["columns"]=('pathnr','path','file','size','sizeH','ctime','dev','inode','crc','instances','instancesH','ctimeH','kind')
                instances=len(crc_dict)
                crcitem=self.groups_tree.insert(parent='', index=END,iid=crc, values=('','','',str(size),size_str,'','','',crc,instances,str(instances),'',CRC),tags=CRC,open=True)

                for pathnr,path,file,ctime,dev,inode in crc_dict:
                    self.groups_tree.insert(parent=crcitem, index=END,iid=self.idfunc(inode,dev), values=(\
                            pathnr,path,file,str(size),\
                            '',\
                            str(ctime),str(dev),str(inode),crc,\
                            '','',\
                            time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime)) ,FILE),tags=())
        self.data_precalc()

        if self.column_sort_last_params[self.groups_tree]!=self.column_groups_sort_params_default:
            #defaultowo po size juz jest, nie trzeba tracic czasu
            self.column_sort(self.groups_tree)
        else:
            self.column_sort_set_arrow(self.groups_tree)

        self.tree_groups_flat_items_update() #after sort !
        self.initial_focus()
        self.calc_mark_stats_groups()

        self.status('')

    def groups_tree_update_crc_and_path(self):
        show_full_crc=self.cfg.get_bool(CFG_KEY_FULL_CRC)
        show_full_paths=self.cfg.get_bool(CFG_KEY_FULL_PATHS)

        for size,size_dict in self.D.files_of_size_of_crc.items() :
            for crc,crc_dict in size_dict.items():
                self.groups_tree.item(crc,text=crc if show_full_crc else self.D.crccut[crc])
                for pathnr,path,file,ctime,dev,inode in crc_dict:
                    self.groups_tree.item(self.idfunc(inode,dev),text=self.D.scanned_paths[pathnr] if show_full_paths else self.NUMBERS[pathnr])

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

    #self.folder_tree['columns']=('file','dev','inode','kind','crc','size','sizeH','ctime','ctimeH','instances','instancesH')
    kindIndex=3

    def two_dots_condition_win(self):
        return True if self.sel_path_full.split(os.sep)[1]!='' else False

    def two_dots_condition_lin(self):
        return True if self.sel_path_full!='/' else False

    two_dots_condition = two_dots_condition_win if windows else two_dots_condition_lin

    @busy_cursor
    def tree_folder_update(self,arbitrary_path=None):
        current_path=arbitrary_path if arbitrary_path else self.sel_path_full

        if not current_path:
            return False

        (dir_ctime,scan_dir_res)=self.D.set_scan_dir(current_path)

        if not scan_dir_res:
            return False

        do_refresh=True
        if current_path in self.folder_items_cache:
            if dir_ctime==self.folder_items_cache[current_path][0]:
                do_refresh=False

        if do_refresh :
            folder_items=[]

            show_full_crc=self.cfg.get_bool(CFG_KEY_FULL_CRC)

            i=0
            for file,islink,isdir,isfile,mtime,ctime,dev,inode,size,nlink in scan_dir_res:
                if islink :
                    text = '\t📁 ⇦' if isdir else '\t📁'
                    iid='%sDL' % i if isdir else '%sFL' % i
                    kind= DIR if isdir else LINK
                    crc=''
                    size=0
                    sizeH=''
                    ctime=0
                    ctimeH=''
                    instances=1
                    instancesH=''
                    #defaulttag=DIR if isdir else LINK
                elif isdir:
                    text = '\t📁'
                    iid='%sD' % i
                    kind= DIR
                    crc=''
                    size=0
                    sizeH=''
                    ctime=0
                    ctimeH=''
                    instances=1
                    instancesH=''

                elif isfile:

                    FILEID=self.idfunc(inode,dev)

                    if (FILEID,ctime) in self.cache_by_id_ctime:
                        crc,crccut,instances = self.cache_by_id_ctime[(FILEID,ctime)]

                        text = crc if show_full_crc else crccut
                        iid=FILEID
                        kind=FILE
                        crc=''
                        sizeH=core.bytes_to_str(size)
                        ctimeH=time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime) )
                        instancesH=instances
                    else:
                        text = '\t ✹' if nlink!=1 else ''
                        iid='%sO' % i
                        crc=''
                        kind = SINGLEHARDLINKED if nlink!=1 else SINGLE
                        sizeH=core.bytes_to_str(size)
                        ctimeH=time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime) )
                        instances=1
                        instancesH=''
                else:
                    logging.error(f'what is it: {file},{islink},{isdir},{isfile} ?')

                    text='????'
                    iid='%sx' % i
                    kind = '?'
                    crc = ''
                    size=0,
                    sizeH='',
                    ctime=0
                    ctimeH=''
                    instances=0
                    instancesH=''

                folder_items.append( (text,iid,(file,dev,inode,kind,crc,size,sizeH,ctime,ctimeH,instances,instancesH)) )

                i+=1

            ############################################################
            col_sort,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[self.folder_tree]

            sort_index_local=sort_index-1
            try:
                FolderItemsSorted=sorted(folder_items,key=lambda x : \
                        (updir_code if x[2][self.kindIndex]==UPDIR else dir_code if x[2][self.kindIndex]==DIR else non_dir_code, float(x[2][sort_index_local])) if is_numeric \
                   else (updir_code if x[2][self.kindIndex]==UPDIR else dir_code if x[2][self.kindIndex]==DIR else non_dir_code, x[2][sort_index_local]),reverse=reverse)
            except Exception as e:
                print(e)
                for item in folder_items:
                    print('\t'.join([str(x) for x in item]))

            else:
                #self.folder_tree['columns']=('file','dev','inode','kind','crc','size','sizeH','ctime','ctimeH','instances','instancesH')
                #text,iid,values,kind
                self.folder_items_cache[current_path]=(dir_ctime,tuple([ \
                (text,iid,(file,str(dev),str(inode),kind,crc,str(size),sizeH,str(ctime),ctimeH,str(instances),str(instancesH)),kind, SINGLE if kind in (SINGLE,SINGLEHARDLINKED) else DIR if kind in (DIR,UPDIR) else LINK if kind==LINK else "") \
                   for text,iid,(file,dev,inode,kind,crc,size,sizeH,ctime,ctimeH,instances,instancesH) in FolderItemsSorted] ) )

        if arbitrary_path:
            #TODO - workaround
            sel_path_prev=self.sel_path
            self.reset_sels()
            self.sel_path=sel_path_prev
            self.sel_path_set(str(pathlib.Path(arbitrary_path)))

        self.folder_tree.delete(*self.folder_tree.get_children())

        if self.two_dots_condition():
            #self.folder_tree['columns']=('file','dev','inode','kind','crc','size','sizeH','ctime','ctimeH','instances','instancesH')
            self.folder_tree.insert(parent="", index=END, iid='0UP' , text='', values=('..','','',UPDIR,'',0,'',0,'',0,''),tags=DIR)

        for (text,iid,values,kind,defaulttag) in self.folder_items_cache[current_path][1]:
            try:
                kind=values[self.kindIndex]
                self.folder_tree.insert(parent="", index=END, iid=iid , text=text, values=values,tags = self.groups_tree.item(iid)['tags'] if kind==FILE else defaulttag)
            except Exception as e:
                print(f'{iid=}')
                print(e)

        self.TreeFolderFlatItemsList=self.folder_tree.get_children()

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
        item=sorted([ (item,self.groups_tree.set(item,'ctime') ) for item in self.groups_tree.get_children(crc)],key=lambda x : float(x[1]),reverse=reverse)[0][0]
        if item:
            action(item,self.groups_tree)
            if select:
                self.groups_tree.see(item)
                self.groups_tree.focus(item)
                self.groups_tree_sel_change(item)
                self.groups_tree.update()

    @busy_cursor
    def mark_all_by_ctime(self,order_str, action):
        self.status('Un/Setting marking on all files ...')
        reverse=1 if order_str=='oldest' else 0

        { self.mark_in_specified_group_by_ctime(action, crc, reverse) for crc in self.groups_tree.get_children() }
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @busy_cursor
    def mark_in_group_by_ctime(self,order_str,action):
        self.status('Un/Setting marking in group ...')
        reverse=1 if order_str=='oldest' else 0
        self.mark_in_specified_group_by_ctime(action,self.sel_crc,reverse,True)
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    def MarkInSpecifiedCRCGroup(self,action,crc):
        { action(item,self.groups_tree) for item in self.groups_tree.get_children(crc) }

    @busy_cursor
    def mark_in_group(self,action):
        self.status('Un/Setting marking in group ...')
        self.MarkInSpecifiedCRCGroup(action,self.sel_crc)
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
    def action_on_path(self,path_param,action,all_groups=True):
        if all_groups:
            crc_range = self.groups_tree.get_children()
        else :
            crc_range = [str(self.sel_crc)]

        selCount=0
        for crcitem in crc_range:
            for item in self.groups_tree.get_children(crcitem):
                fullpath = self.item_full_path(item)

                if fullpath.startswith(path_param + os.sep):
                    action(item,self.groups_tree)
                    selCount+=1

        if not selCount :
            self.info_dialog_on_main.show('No files found for specified path',path_param,min_width=400)
        else:
            self.status(f'Subdirectory action. {selCount} File(s) Found')
            self.update_marks_folder()
            self.calc_mark_stats_groups()
            self.calc_mark_stats_folder()

    expr_by_tree={}

    def mark_expression(self,action,prompt,all_groups=True):
        tree=self.main.focus_get()

        if tree in self.expr_by_tree.keys():
            initialvalue=self.expr_by_tree[tree]
        else:
            initialvalue='*'

        if tree==self.groups_tree:
            range_str = " (all groups)" if all_groups else " (selected group)"
            title=f'Specify expression for full file path.'
        else:
            range_str = ''
            title='Specify expression for file names in selected directory.'

        (use_reg_expr,expression) = self.mark_dialog_on_main.show(title,prompt + f'{range_str}', initialvalue,'Use regular expressions matching',self.cfg.get_bool(CFG_KEY_USE_REG_EXPR),min_width=400)

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
                            self.info_dialog_on_main.show('expression Error !',f'expression:"{expression}"  {use_reg_expr_info}\n\nERROR:{e}',min_width=400)
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
                            self.info_dialog_on_main.show('expression Error !',f'expression:"{expression}"  {use_reg_expr_info}\n\nERROR:{e}',min_width=400)
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
                self.info_dialog_on_main.show('No files found.',f'expression:"{expression}"  {use_reg_expr_info}\n',min_width=400)

        tree.focus_set()

    def mark_subpath(self,action,all_groups=True):
        if path:=tk.filedialog.askdirectory(title='Select Directory',initialdir=self.cwd):
            self.action_on_path(path,action,all_groups)

    def goto_next_mark_menu(self,direction,go_to_no_mark=False):
        tree=(self.groups_tree,self.folder_tree)[self.sel_tree_index]
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

    @busy_cursor
    def goto_max_group(self,size_flag=0,direction=1):
        if self.groups_combos_size:
            #self.status(f'Setting dominant group ...')
            working_index = self.dominant_groups_index[size_flag]
            working_index = (working_index+direction) % len(self.groups_combos_size)
            temp=str(working_index)
            working_dict = self.groups_combos_size if size_flag else self.groups_combos_quant

            biggestcrc,biggestcrcSizeSum = working_dict[working_index]

            if biggestcrc:
                self.crc_select_and_focus(biggestcrc,True)

                self.dominant_groups_index[size_flag] = int(temp)
                info = core.bytes_to_str(biggestcrcSizeSum) if size_flag else str(biggestcrcSizeSum)
                self.status(f'Dominant (index:{working_index}) group ({self.BY_WHAT[size_flag]}: {info})')

    @busy_cursor
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
            self.groups_tree_sel_change(item,ChangeStatusLine=False)

            LastCrcChild=self.groups_tree.get_children(self.sel_crc)[-1]
            try:
                self.groups_tree.see(LastCrcChild)
                self.groups_tree.see(self.sel_crc)
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

            self.dominant_groups_folder[size_flag] = int(temp)
            info = core.bytes_to_str(num) if size_flag else str(num)
            self.status(f'Dominant (index:{working_index}) folder ({self.BY_WHAT[size_flag]}: {info})')

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

    def process_files_in_groups_wrapper(self,action,all_groups):
        processed_items=defaultdict(list)
        if all_groups:
            ScopeTitle='All marked files.'
        else:
            ScopeTitle='Single CRC group.'

        for crc in self.groups_tree.get_children():
            if all_groups or crc==self.sel_crc:
                for item in self.groups_tree.get_children(crc):
                    if self.groups_tree.tag_has(MARK,item):
                        processed_items[crc].append(item)

        return self.process_files(action,processed_items,ScopeTitle)

    def process_files_in_folder_wrapper(self,action,OnDirAction=False):
        processed_items=defaultdict(list)
        if OnDirAction:
            ScopeTitle='All marked files on selected directory sub-tree.'

            sel_path_with_sep=self.sel_full_path_to_file + os.sep
            for crc in self.groups_tree.get_children():
                for item in self.groups_tree.get_children(crc):
                    if self.item_full_path(item).startswith(sel_path_with_sep):
                        if self.groups_tree.tag_has(MARK,item):
                            processed_items[crc].append(item)
        else:
            ScopeTitle='Selected Directory.'
            #self.sel_path_full

            for item in self.folder_tree.get_children():
                if self.folder_tree.tag_has(MARK,item):
                    crc=self.folder_tree.set(item,'crc')
                    processed_items[crc].append(item)

        return self.process_files(action,processed_items,ScopeTitle)

    @restore_status_line
    def process_files_check_correctness(self,action,processed_items,remaining_items):
        for crc in processed_items:
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
            for crc in processed_items:
                if len(processed_items[crc])==1:
                    self.info_dialog_on_main.show('Error - Can\'t hardlink single file.',"Mark more files.",min_width=400)

                    self.crc_select_and_focus(crc,True)
                    return True

        elif action==DELETE:
            if self.cfg.get_bool(CFG_SKIP_INCORRECT_GROUPS):
                IncorrectGroups=[]
                for crc in processed_items:
                    if len(remaining_items[crc])==0:
                        IncorrectGroups.append(crc)
                if IncorrectGroups:
                    IncorrectGroupsStr='\n'.join(IncorrectGroups)
                    self.info_dialog_on_main.show(f'Warning (Delete) - All files marked',f"Option \"Skip groups with invalid selection\" is enabled.\n\nFolowing CRC groups will not be processed and remain with markings:\n\n{IncorrectGroupsStr}")

                    self.crc_select_and_focus(IncorrectGroups[0],True)

                for crc in IncorrectGroups:
                    del processed_items[crc]
                    del remaining_items[crc]
            else:
                ShowAllDeleteWarning=False
                for crc in processed_items:
                    if len(remaining_items[crc])==0:
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
            for crc in processed_items:
                if len(remaining_items[crc])==0:
                    self.info_dialog_on_main.show(f'Error (Softlink) - All files marked',"Keep at least one file unmarked.",min_width=400)

                    self.crc_select_and_focus(crc,True)
                    return True

    @restore_status_line
    def process_files_check_correctness_last(self,action,processed_items,remaining_items):
        self.status('final checking selection correctness')

        if action==HARDLINK:
            for crc in processed_items:
                if len({int(self.groups_tree.set(item,'dev')) for item in processed_items[crc]})>1:
                    title='Can\'t create hardlinks.'
                    message=f"Files on multiple devices selected. Crc:{crc}"
                    logging.error(title)
                    logging.error(message)
                    self.info_dialog_on_main.show(title,message,min_width=400)
                    return True

        for crc in processed_items:
            for item in remaining_items[crc]:
                if res:=self.file_check_state(item):
                    self.info_dialog_on_main.show('Error',res+'\n\nNo action was taken.\n\nAborting. Repeat scanning please or unmark all files and groups affected by other programs.')
                    logging.error('aborting.')
                    return True
        logging.info('remaining files checking complete.')

    @restore_status_line
    def process_files_confirm(self,action,processed_items,remaining_items,ScopeTitle):
        self.status('confirmation required...')
        ShowFullPath=1

        message=[]
        if not self.cfg.get_bool(CFG_CONFIRM_SHOW_CRCSIZE):
            message.append('')

        for crc in processed_items:
            if self.cfg.get_bool(CFG_CONFIRM_SHOW_CRCSIZE):
                size=int(self.groups_tree.set(crc,'size'))
                message.append('')
                message.append('CRC:' + crc + ' size:' + core.bytes_to_str(size) + '|GRAY')

            for item in processed_items[crc]:
                message.append((self.item_full_path(item) if ShowFullPath else tree.set(item,'file')) + '|RED' )

            if action==SOFTLINK:
                if remaining_items[crc]:
                    item = remaining_items[crc][0]
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

    def process_files_core(self,action,processed_items,remaining_items):
        self.main.config(cursor="watch")
        self.menu_disable()
        self.status('processing files ...')
        self.main.update()

        final_info=[]
        if action==DELETE:
            DirectoriesToCheck=set()
            for crc in processed_items:
                TuplesToDelete=set()
                size=int(self.groups_tree.set(processed_items[crc][0],'size'))
                for item in processed_items[crc]:
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

                final_info.extend(Removed)

        elif action==SOFTLINK:
            RelSymlink = self.cfg.get_bool(CFG_KEY_REL_SYMLINKS)
            for crc in processed_items:
                toKeepItem=list(remaining_items[crc])[0]
                #self.groups_tree.focus()
                IndexTupleRef=self.get_index_tuple_groups_tree(toKeepItem)
                size=int(self.groups_tree.set(toKeepItem,'size'))

                if resmsg:=self.D.link_wrapper(True, RelSymlink, size,crc, IndexTupleRef, [self.get_index_tuple_groups_tree(item) for item in processed_items[crc] ] ):
                    logging.error(resmsg)
                    self.info_dialog_on_main.show('Error',resmsg)
                self.crc_node_update(crc)

        elif action==HARDLINK:
            for crc in processed_items:
                refItem=processed_items[crc][0]
                IndexTupleRef=self.get_index_tuple_groups_tree(refItem)
                size=int(self.groups_tree.set(refItem,'size'))

                if resmsg:=self.D.link_wrapper(False, False, size,crc, IndexTupleRef, [self.get_index_tuple_groups_tree(item) for item in processed_items[crc][1:] ] ):
                    logging.error(resmsg)
                    self.info_dialog_on_main.show('Error',resmsg)
                self.crc_node_update(crc)

        self.main.config(cursor="")
        self.menu_enable()

        self.data_precalc()
        self.tree_groups_flat_items_update()

        if final_info:
            self.info_dialog_on_main.show('Removed empty directories','\n'.join(final_info),min_width=400)

    def get_this_or_existing_parent(self,path):
        if os.path.exists(path):
            return path
        else:
            return self.get_this_or_existing_parent(pathlib.Path(path).parent.absolute())

    def process_files(self,action,processed_items,ScopeTitle):
        tree=(self.groups_tree,self.folder_tree)[self.sel_tree_index]

        if not processed_items:
            self.info_dialog_on_main.show('No Files Marked For Processing !','Scope: ' + ScopeTitle + '\n\nMark files first.')
            return

        logging.info(f'process_files:{action}')
        logging.info('Scope ' + ScopeTitle)

        #############################################
        #check remainings

        #remaining_items dla wszystkich (moze byc akcja z folderu)
        #istotna kolejnosc

        AffectedCRCs=processed_items.keys()

        self.status('checking remaining items...')
        remaining_items={}
        for crc in AffectedCRCs:
            remaining_items[crc]=[item for item in self.groups_tree.get_children(crc) if not self.groups_tree.tag_has(MARK,item)]

        if self.process_files_check_correctness(action,processed_items,remaining_items):
            return

        if not processed_items:
            self.info_dialog_on_main.show('info','No files left for processing. Fix files selection.',min_width=400)
            return

        logging.warning('###########################################################################################')
        logging.warning(f'action:{action}')

        self.status('')
        if self.process_files_confirm(action,processed_items,remaining_items,ScopeTitle):
            return

        #after confirmation
        if self.process_files_check_correctness_last(action,processed_items,remaining_items):
            return

        #############################################
        #action

        if tree==self.groups_tree:
            #orglist=self.groups_tree.get_children()
            orglist=self.tree_groups_flat_items
        else:
            org_sel_item=self.sel_item
            orglist=self.folder_tree.get_children()
            #orglistNames=[self.folder_tree.item(item)['values'][2] for item in self.folder_tree.get_children()]
            org_sel_item_name=self.folder_tree.item(org_sel_item)['values'][2]
            #print(orglistNames)

        #############################################
        self.process_files_core(action,processed_items,remaining_items)
        #############################################

        if tree==self.groups_tree:
            #newlist=self.groups_tree.get_children()

            sel_item = self.sel_item if self.sel_item else self.sel_crc
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

                ItemToSel = self.get_closest_in_folder(orglist,org_sel_item,org_sel_item_name,newlist)

                if ItemToSel:
                    self.folder_tree.focus(ItemToSel)
                    self.folder_tree_sel_change(ItemToSel)
                    self.folder_tree.see(ItemToSel)
                    self.folder_tree.update()

        self.calc_mark_stats_groups()

        self.folder_items_cache={}

        self.find_result=()

    def get_closest_in_folder(self,prev_list,item,item_name,new_list):
        if item in new_list:
            return item
        elif not new_list:
            return None
        else:
            new_list_names=[self.folder_tree.item(item)['values'][2] for item in self.folder_tree.get_children()]

            if item_name in new_list_names:
                return new_list[new_list_names.index(item_name)]
            else:
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

    def get_closest_in_crc(self,prev_list,item,new_list):
        if item in new_list:
            return item
        elif not new_list:
            return None
        else:
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
        if self.sel_kind==FILE or self.sel_kind==LINK or self.sel_kind==SINGLE or self.sel_kind==SINGLEHARDLINKED:
            self.status(f'Opening {self.sel_file}')
            if windows:
                os.startfile(os.sep.join([self.sel_path_full,self.sel_file]))
            else:
                os.system("xdg-open "+ '"' + os.sep.join([self.sel_path_full,self.sel_file]).replace("'","\'").replace("`","\`") + '"')
        elif self.sel_kind==DIR:
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

if __name__ == "__main__":
    try:
        #######################################################################
        #timestamp

        VER_TIMESTAMP = console.get_ver_timestamp()

        DUDE_FILE = os.path.normpath(__file__)

        args = console.parse_args(VER_TIMESTAMP)

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
