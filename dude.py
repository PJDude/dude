#!/usr/bin/python3

VERSION='0.90'

from sys import exit

import fnmatch
import shutil
import os
import os.path
import pathlib
from appdirs import *
import re

from collections import defaultdict

import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import scrolledtext
from tkinter.filedialog import askdirectory

import time

import configparser

from threading import Thread

import pyperclip
import logging

import psutil

import core

CACHE_DIR = os.sep.join([user_cache_dir('dude'),"cache"])
LOG_DIR = user_log_dir('dude')
CONFIG_DIR = user_config_dir('dude')

k=1024
M=k*1024
G=M*1024
T=G*1024

multDict={'k':k,'K':k,'M':M,'G':G,'T':T}

windows = (os.name=='nt')

def bytes2str(num):
    kb=num/k

    if kb<k:
        return str(round(kb,2))+'kB'
    elif kb<M:
        return str(round(kb/k,2))+'MB'
    elif kb<G:
        return str(round(kb/M,2))+'GB'
    else:
        return str(round(kb/G,2))+'TB'


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


###########################################################################################################################################

CFG_KEY_STARTUP_ADD_CWD='add_cwd_at_startup'
CFG_KEY_STARTUP_SCAN='scan_at_startup'
CFG_KEY_SHOW_OTHERS='show_other'
CFG_KEY_FULLCRC='show_full_crc'
CFG_KEY_FULLPATHS='show_full_paths'
CFG_KEY_REL_SYMLINKS='relative_symlinks'
CFG_KEY_USE_REG_EXPR='use_reg_expr'

CFG_KEY_GEOMETRY='geometry'
CFG_KEY_GEOMETRY_DIALOG='geometry_dialog'

CFG_KEY_EXCLUDE='exclude'
CFG_KEY_EXCLUDE_REGEXP='excluderegexpp'

MARK='M'
FILE='2'
SINGLE='3'
DIR='0'
LINK='1'
CRC='C'

class Config:
    def __init__(self,ConfigDir):
        logging.debug(f'Initializing config: {ConfigDir}')
        self.config = configparser.ConfigParser()
        self.config.add_section('main')
        self.config.add_section('geometry')

        self.path = ConfigDir
        self.file = self.path + '/cfg.ini'

    def Write(self):
        logging.debug('writing config')
        pathlib.Path(self.path).mkdir(parents=True,exist_ok=True)
        with open(self.file, 'w') as configfile:
            self.config.write(configfile)

    def Read(self):
        logging.debug('reading config')
        if os.path.isfile(self.file):
            try:
                with open(self.file, 'r') as configfile:
                    self.config.read_file(configfile)
            except Exception as e:
                logging.error(e)
        else:
            logging.warning(f'no config file:{self.file}')

    def Set(self,key,val,section='main'):
        self.config.set(section,key,val)

    def Get(self,key,default=None,section='main'):
        try:
            res=self.config.get(section,key)
        except Exception as e:
            logging.warning(f'gettting config key {key}')
            logging.warning(e)
            res=default
            self.Set(key,str(default),section=section)
        return res

def CenterToParentGeometry(widget,parent):
    x = int(parent.winfo_rootx()+0.5*(parent.winfo_width()-widget.winfo_width()))
    y = int(parent.winfo_rooty()+0.5*(parent.winfo_height()-widget.winfo_height()))

    return f'+{x}+{y}'

def CenterToScreenGeometry(widget):
    x = int(0.5*(widget.winfo_screenwidth()-widget.winfo_width()))
    y = int(0.5*(widget.winfo_screenheight()-widget.winfo_height()))

    return f'+{x}+{y}'

###########################################################

raw = lambda x : x

class Gui:
    Numbers='①②③④⑤⑥⑦⑧⑨⑩' if windows else '⓵⓶⓷⓸⓹⓺⓻⓼⓽⓾'
    ProgressSigns='◐◓◑◒'  
    
    MAX_PATHS=10

    pyperclipOperational=True

    def ResetSels(self):
        self.SelPathnr = None
        self.SelPath = None
        self.SelFile = None
        self.SelCrc = None
        self.SelItem = None
        self.SelTreeIndex = 0
        self.SelKind = None

    def WatchCursor(f):
        def wrapp(self,*args,**kwargs):
            if 'parent' in kwargs.keys():
                parent=kwargs['parent']
                prevParentCursor=parent.cget('cursor')
                parent.config(cursor="watch")
                parent.update()

                res=f(self,*args,**kwargs)

                parent.config(cursor=prevParentCursor)
                return res
            else:
                return f(self,*args,**kwargs)

        return wrapp

    def CheckClipboard(self):
        TestString='Dude-TestString'
        logging.info('pyperclip test start.')
        return

        try:
            PrevVal=pyperclip.paste()
            pyperclip.copy(TestString)
        except Exception as e:
            logging.error(e)
            self.pyperclipOperational=False
            logging.error('Clipboard test error. Copy options disabled.')
        else:
            if pyperclip.paste() != TestString:
                self.pyperclipOperational=False
                logging.error('Clipboard test error. Copy options disabled.')
                if not windows :
                    logging.error('try to install xclip or xsel.')
            else:
                pyperclip.copy(PrevVal)
                logging.info('pyperclip test passed.')

    #######################################################################
    #LongActionDialog

    LADPrevMessage=''

    def getNow(self):
        return time.time()*1000.0

    LongActionAbort=False
    def LongActionDialogShow(self,parent,title,ProgressMode1=None,ProgressMode2=None,Progress1LeftText=None,Progress2LeftText=None):
        self.LADParent=parent
        now=self.getNow()
        self.psIndex =0

        self.ProgressMode1=ProgressMode1
        self.ProgressMode2=ProgressMode2

        self.LongActionDialog = tk.Toplevel(parent)
        self.LongActionDialog.wm_transient(parent)

        self.LongActionDialog.protocol("WM_DELETE_WINDOW", self.LongActionDialogAbort)
        self.LongActionDialog.bind('<Escape>', self.LongActionDialogAbort)

        self.LongActionDialog.wm_title(title)
        self.LongActionDialog.iconphoto(False, iconphoto)

        (f0:=tk.Frame(self.LongActionDialog,bg=self.bg)).pack(expand=1,fill='both',side='top')
        (f1:=tk.Frame(self.LongActionDialog,bg=self.bg)).pack(expand=1,fill='both',side='top')

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
            self.LongActionDialog.minsize(550, 60)
            self.progr2.grid(row=1,column=1,padx=1,pady=4,sticky='news')

            if Progress2LeftText:
                self.progr2LabLeft=tk.Label(f0,width=17,bg=self.bg)
                self.progr2LabLeft.grid(row=1,column=0,padx=1,pady=4)
                self.progr2LabLeft.config(text=Progress2LeftText)

            self.progr2LabRight.grid(row=1,column=2,padx=1,pady=4)
        else:
            self.LongActionDialog.minsize(300, 60)

        f0.grid_columnconfigure(1, weight=1)

        self.message=tk.StringVar()
        tk.Label(f1,textvariable=self.message,anchor='n',justify='center',width=20,bg=self.bg).pack(side='top',padx=8,pady=8,expand=1,fill='x')
        ttk.Button(f1, text='Abort', width=10 ,command=self.LongActionDialogAbort ).pack(side='bottom',padx=8,pady=8)

        self.LastTimeNoSign=now

        self.LongActionDialog.grab_set()
        self.LongActionDialog.update()
        self.LongActionDialog.geometry(CenterToParentGeometry(self.LongActionDialog,parent))

        self.prevParentCursor=parent.cget('cursor')
        parent.config(cursor="watch")

        self.LongActionAbort=False

    def LongActionDialogAbort(self,event=None):
        self.LongActionAbort=True

    def LongActionDialogEnd(self):
        self.LongActionDialog.grab_release()
        self.LongActionDialog.destroy()
        self.LADParent.config(cursor=self.prevParentCursor)

    def LongActionDialogUpdate(self,message,progress1=None,progress2=None,progress1Right=None,progress2Right=None):
        now=self.getNow()
        prefix=''
        if self.LADPrevMessage==message:
            if now>self.LastTimeNoSign+1000.0:
                prefix=str(self.ProgressSigns[self.psIndex])
                self.psIndex=(self.psIndex+1)%4
        else:
            self.LADPrevMessage=message
            self.LastTimeNoSign=now

            self.Progress1Func(progress1)
            self.progr1LabRight.config(text=progress1Right)
            self.progr2var.set(progress2)
            self.progr2LabRight.config(text=progress2Right)

        self.message.set(f'{prefix}\n{message}')
        self.LongActionDialog.update()

    def __init__(self,cwd):
        self.ResetSels()

        self.D = core.DudeCore(CACHE_DIR,logging)
        self.cwd=cwd

        self.cfg = Config(CONFIG_DIR)
        self.cfg.Read()

        self.PathsToScanFrames=[]
        self.ExcludeFrames=[]

        self.PathsToScanFromDialog=[]

        self.CheckClipboard()

        ####################################################################
        self.main = tk.Tk()
        self.main.title(f'Dude (DUplicates DEtector) v{VERSION}')
        self.main.protocol("WM_DELETE_WINDOW", self.exit)
        self.main.minsize(1200, 800)
        self.main.bind('<FocusIn>', self.FocusIn)

        global iconphoto
        iconphoto = PhotoImage(file = os.path.join(os.path.dirname(__file__),'icon.png'))
        self.main.iconphoto(False, iconphoto)

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

        #style.map('Treeview', background=[('focus','#90DD90'),('selected','#AAAAAA'),('',self.bg)])
        style.map('Treeview', background=[('focus','#90DD90'),('selected','#AAAAAA'),('','white')])

        #style.map("Treeview.Heading",background = [('pressed', '!focus', 'white'),('active', 'darkgray'),('disabled', '#ffffff'),('',self.bg)])

        #works but not for every theme
        #style.configure("Treeview", fieldbackground=self.bg)

        #######################################################################
        self.menubar = Menu(self.main,bg=self.bg)
        self.main.config(menu=self.menubar)
        #######################################################################

        self.StatusVarAllSize=tk.StringVar()
        self.StatusVarAllQuant=tk.StringVar()
        self.StatusVarGroups=tk.StringVar()
        self.StatusVarFullPath=tk.StringVar()
        self.StatusVarPathSize=tk.StringVar()
        self.StatusVarPathQuant=tk.StringVar()

        self.paned = PanedWindow(self.main,orient=tk.VERTICAL,relief='sunken',showhandle=0,bd=0,bg=self.bg,sashwidth=2,sashrelief='flat')
        self.paned.pack(fill='both',expand=1)

        paned_top = tk.Frame(self.paned,bg=self.bg)
        self.paned.add(paned_top)
        paned_bottom = tk.Frame(self.paned,bg=self.bg)
        self.paned.add(paned_bottom,)

        self.paned.update()
        self.paned.sash_place(0,0,self.cfg.Get('sash_coord',400,section='geometry'))

        FrameTop = tk.Frame(paned_top,bg=self.bg)
        FrameBottom = tk.Frame(paned_bottom,bg=self.bg)

        FrameTop.grid(row=0,column=0,sticky='news')
        FrameBottom.grid(row=0,column=0,sticky='news')

        FrameTop.grid_rowconfigure(0, minsize=400)
        FrameBottom.grid_rowconfigure(0,minsize=400)

        self.main.bind('<KeyPress>', self.KeyPressGlobal )

        (UpperStatusFrame := tk.Frame(FrameTop,bg=self.bg)).pack(side='bottom', fill='both')
        self.StatusVarGroups.set('0')
        self.StatusVarFullPath.set('')

        tk.Label(UpperStatusFrame,width=10,textvariable=self.StatusVarAllQuant,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=16,text="All marked files # ",relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=10,textvariable=self.StatusVarAllSize,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=18,text='All marked files size: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=10,textvariable=self.StatusVarGroups,borderwidth=2,bg=self.bg,relief='groove',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=10,text='Groups: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=12,text='Full file path: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='left')
        self.StatusVarFullPathLabel = tk.Label(UpperStatusFrame,textvariable=self.StatusVarFullPath,relief='flat',borderwidth=2,bg=self.bg,anchor='w')
        self.StatusVarFullPathLabel.pack(fill='x',expand=1,side='left')

        (LowerStatusFrame := tk.Frame(FrameBottom,bg=self.bg)).pack(side='bottom',fill='both')

        self.SelectedSearchPathCode=tk.StringVar()
        self.SelectedSearchPath=tk.StringVar()

        tk.Label(LowerStatusFrame,width=10,text='Scan Path: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='left')
        tk.Label(LowerStatusFrame,width=2,textvariable=self.SelectedSearchPathCode,borderwidth=2,bg=self.bg,relief='groove',anchor='w').pack(expand=0,side='left')
        tk.Label(LowerStatusFrame,width=30,textvariable=self.SelectedSearchPath,borderwidth=2,bg=self.bg,relief='groove',anchor='w').pack(fill='x',expand=1,side='left')

        tk.Label(LowerStatusFrame,width=10,textvariable=self.StatusVarPathQuant,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(LowerStatusFrame,width=16,text='Marked files # ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(LowerStatusFrame,width=10,textvariable=self.StatusVarPathSize,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(expand=0,side='right')
        tk.Label(LowerStatusFrame,width=18,text='Marked files size: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')

        self.main.unbind_class('Treeview', '<KeyPress-Next>')
        self.main.unbind_class('Treeview', '<KeyPress-Prior>')
        self.main.unbind_class('Treeview', '<KeyPress-space>')
        self.main.unbind_class('Treeview', '<KeyPress-Return>')
        self.main.unbind_class('Treeview', '<KeyPress-Left>')
        self.main.unbind_class('Treeview', '<KeyPress-Right>')
        self.main.unbind_class('Treeview', '<Double-Button-1>')

        self.main.bind_class('Treeview','<KeyPress>', self.KeyPressTreeCommon )
        self.main.bind_class('Treeview','<Control-i>',  lambda event : self.MarkOnAll(self.InvertMark) )
        self.main.bind_class('Treeview','<Control-I>',  lambda event : self.MarkOnAll(self.InvertMark) )
        self.main.bind_class('Treeview','<Control-o>',  lambda event : self.MarkOnAllByCTime('oldest',self.SetMark) )
        self.main.bind_class('Treeview','<Control-O>',  lambda event : self.MarkOnAllByCTime('oldest',self.UnsetMark) )
        self.main.bind_class('Treeview','<Control-y>',  lambda event : self.MarkOnAllByCTime('youngest',self.SetMark) )
        self.main.bind_class('Treeview','<Control-Y>',  lambda event : self.MarkOnAllByCTime('youngest',self.UnsetMark) )
        self.main.bind_class('Treeview','<p>',          lambda event : self.MarkLowerPane(self.SetMark) )
        self.main.bind_class('Treeview','<P>',          lambda event : self.MarkLowerPane(self.UnsetMark) )
        self.main.bind_class('Treeview','<Control-j>',  lambda event : self.MarkLowerPane(self.InvertMark) )
        self.main.bind_class('Treeview','<Control-J>',  lambda event : self.MarkLowerPane(self.InvertMark) )
        self.main.bind_class('Treeview','<FocusIn>',    self.TreeEventFocusIn )
        self.main.bind_class('Treeview','<FocusOut>',   self.TreeFocusOut )
        self.main.bind_class('Treeview','<ButtonPress-1>', self.TreeButtonPress)
        self.main.bind_class('Treeview','<Control-ButtonPress-1>',  lambda event :self.TreeButtonPress(event,True) )
        self.main.bind_class('Treeview','<ButtonPress-3>', self.TreeContexMenu)

        self.main.bind_class('Treeview','<Shift-BackSpace>',            lambda event : self.GoToMaxGroup(1) )
        self.main.bind_class('Treeview','<Shift-Control-BackSpace>',    lambda event : self.GoToMaxGroup(0) )
        self.main.bind_class('Treeview','<BackSpace>',                  lambda event : self.GoToMaxFolder(1) )
        self.main.bind_class('Treeview','<Control-BackSpace>',          lambda event : self.GoToMaxFolder(0) )

        if self.pyperclipOperational:
            self.main.bind_class('Treeview','<Control-c>',  lambda event : self.ClipCopy() )
            self.main.bind_class('Treeview','<Control-C>',  lambda event : self.ClipCopy() )

        self.main.bind_class('Treeview','<Delete>',          lambda event : self.ProcessFiles('delete',0) )
        self.main.bind_class('Treeview','<Control-Delete>',  lambda event : self.ProcessFiles('delete',1) )

        self.main.bind_class('Treeview','<Insert>',         lambda event : self.ProcessFiles('softlink',0) )
        self.main.bind_class('Treeview','<Shift-Insert>',   lambda event : self.ProcessFiles('hardlink',0) )

        self.main.bind_class('Treeview','<Control-Insert>',         lambda event : self.ProcessFiles('softlink',1) )
        self.main.bind_class('Treeview','<Control-Shift-Insert>',   lambda event : self.ProcessFiles('hardlink',1) )

        self.main.bind_class('Treeview','<KP_Add>',         lambda event : self.MarkExpression('both',self.SetMark,'Mark files') )
        self.main.bind_class('Treeview','<plus>',           lambda event : self.MarkExpression('both',self.SetMark,'Mark files') )
        self.main.bind_class('Treeview','<KP_Subtract>',    lambda event : self.MarkExpression('both',self.UnsetMark,'Unmark files') )
        self.main.bind_class('Treeview','<minus>',          lambda event : self.MarkExpression('both',self.UnsetMark,'Unmark files') )

        self.tree1=ttk.Treeview(FrameTop,takefocus=True,selectmode='none',show=('tree','headings') )

        self.OrgLabel={}
        self.OrgLabel['path']='Subpath'
        self.OrgLabel['file']='File'
        self.OrgLabel['sizeH']='Size'
        self.OrgLabel['instances']='Copies'
        self.OrgLabel['ctimeH']='Change Time'

        self.tree1["columns"]=('pathnr','path','file','size','sizeH','ctime','dev','inode','crc','instances','ctimeH','kind')

        #pathnr,path,file,ctime,dev,inode
        self.IndexTupleIndexesWithFnCommon=((int,0),(raw,1),(raw,2),(int,5),(int,6),(int,7))

        self.tree1["displaycolumns"]=('path','file','sizeH','instances','ctimeH')

        self.tree1.column('#0', width=120, minwidth=100, stretch=tk.NO)
        self.tree1.column('path', width=100, minwidth=10, stretch=tk.YES )
        self.tree1.column('file', width=100, minwidth=10, stretch=tk.YES )
        self.tree1.column('sizeH', width=80, minwidth=80, stretch=tk.NO)
        self.tree1.column('instances', width=80, minwidth=80, stretch=tk.NO)
        self.tree1.column('ctimeH', width=150, minwidth=100, stretch=tk.NO)

        self.tree1.heading('#0',text='CRC / Scan Path',anchor=tk.W)
        self.tree1.heading('path',anchor=tk.W )
        self.tree1.heading('file',anchor=tk.W )
        self.tree1.heading('sizeH',anchor=tk.W)
        self.tree1.heading('ctimeH',anchor=tk.W)
        self.tree1.heading('instances',anchor=tk.W)
        
        self.tree1.heading('sizeH', text='Size \u25BC')
        
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

        vsb1 = tk.Scrollbar(FrameTop, orient='vertical', command=self.tree1.yview,takefocus=False,bg=self.bg)
        self.tree1.configure(yscrollcommand=vsb1.set)

        vsb1.pack(side='right',fill='y',expand=0)
        self.tree1.pack(fill='both',expand=1, side='left')

        self.tree1.bind('<KeyRelease>',             self.Tree1KeyRelease )
        self.tree1.bind('<Double-Button-1>',        self.TreeEventOpenFileEvent)

        self.tree1.bind('<Control-a>', lambda event : self.MarkOnAll(self.SetMark) )
        self.tree1.bind('<Control-A>', lambda event : self.MarkOnAll(self.SetMark) )
        self.tree1.bind('<Control-n>', lambda event : self.MarkOnAll(self.UnsetMark) )
        self.tree1.bind('<Control-N>', lambda event : self.MarkOnAll(self.UnsetMark) )

        self.tree1.bind('<BackSpace>',          lambda event : self.GoToMaxGroup(1) )
        self.tree1.bind('<Control-BackSpace>',    lambda event : self.GoToMaxGroup(0) )

        self.tree1.bind('<a>', lambda event : self.MarkInCRCGroup(self.SetMark) )
        self.tree1.bind('<A>', lambda event : self.MarkInCRCGroup(self.SetMark) )
        self.tree1.bind('<n>', lambda event : self.MarkInCRCGroup(self.UnsetMark) )
        self.tree1.bind('<N>', lambda event : self.MarkInCRCGroup(self.UnsetMark) )

        self.tree1.bind('<o>', lambda event : self.MarkInCRCGroupByCTime('oldest',self.InvertMark) )
        self.tree1.bind('<O>', lambda event : self.MarkInCRCGroupByCTime('oldest',self.InvertMark) )
        self.tree1.bind('<y>', lambda event : self.MarkInCRCGroupByCTime('youngest',self.InvertMark) )
        self.tree1.bind('<Y>', lambda event : self.MarkInCRCGroupByCTime('youngest',self.InvertMark) )

        self.tree1.bind('<i>', lambda event : self.MarkInCRCGroup(self.InvertMark) )
        self.tree1.bind('<I>', lambda event : self.MarkInCRCGroup(self.InvertMark) )

        self.tree2=ttk.Treeview(FrameBottom,takefocus=True,selectmode='none')

        self.tree2['columns']=('pathnr','path','file','size','sizeH','ctime','dev','inode','crc','instances','instancesnum','ctimeH','kind')

        self.tree2['displaycolumns']=('file','sizeH','instances','ctimeH')

        self.tree2.column('#0', width=120, minwidth=100, stretch=tk.NO)

        self.tree2.column('file', width=200, minwidth=100, stretch=tk.YES)
        self.tree2.column('sizeH', width=80, minwidth=80, stretch=tk.NO)
        self.tree2.column('instances', width=80, minwidth=80, stretch=tk.NO)
        self.tree2.column('ctimeH', width=150, minwidth=100, stretch=tk.NO)

        self.tree2.heading('#0',text='CRC',anchor=tk.W)
        self.tree2.heading('path',anchor=tk.W)
        self.tree2.heading('file',anchor=tk.W)
        self.tree2.heading('sizeH',anchor=tk.W)
        self.tree2.heading('ctimeH',anchor=tk.W)
        self.tree2.heading('instances',anchor=tk.W)

        for tree in [self.tree1,self.tree2]:
            for col in tree["displaycolumns"]:
                if col in self.OrgLabel:
                    tree.heading(col,text=self.OrgLabel[col])

        self.tree2.heading('sizeH', text='Size \u25BC')

        vsb2 = tk.Scrollbar(FrameBottom, orient='vertical', command=self.tree2.yview,takefocus=False,bg=self.bg)
        self.tree2.configure(yscrollcommand=vsb2.set)

        vsb2.pack(side='right',fill='y',expand=0)
        self.tree2.pack(fill='both',expand=1,side='left')

        self.tree2.bind('<KeyRelease>',             self.Tree2KeyRelease )
        self.tree2.bind('<Double-Button-1>',        self.TreeEventOpenFileEvent)

        self.tree2.bind('<a>', lambda event : self.MarkLowerPane(self.SetMark) )
        self.tree2.bind('<A>', lambda event : self.MarkLowerPane(self.SetMark) )
        self.tree2.bind('<n>', lambda event : self.MarkLowerPane(self.UnsetMark) )
        self.tree2.bind('<N>', lambda event : self.MarkLowerPane(self.UnsetMark) )

        self.tree2.bind('<i>', lambda event : self.MarkLowerPane(self.InvertMark) )
        self.tree2.bind('<I>', lambda event : self.MarkLowerPane(self.InvertMark) )

        paned_top.grid_columnconfigure(0, weight=1)
        paned_top.grid_rowconfigure(0, weight=1,minsize=200)

        paned_bottom.grid_columnconfigure(0, weight=1)
        paned_bottom.grid_rowconfigure(0, weight=1,minsize=200)

        self.tree1.tag_configure(MARK, foreground='red')
        self.tree1.tag_configure(MARK, background='red')
        self.tree2.tag_configure(MARK, foreground='red')
        self.tree2.tag_configure(MARK, background='red')

        self.tree1.tag_configure(CRC, foreground='gray')

        self.tree2.tag_configure(SINGLE, foreground='gray')
        self.tree2.tag_configure(DIR, foreground='blue2')
        self.tree2.tag_configure(LINK, foreground='darkgray')

        self.SetDefaultGeometryAndShow(self.main,None)

        self.Popup1 = Menu(self.tree1, tearoff=0,bg=self.bg)
        self.Popup1.bind("<FocusOut>",lambda event : self.Popup1.unpost() )

        self.Popup2 = Menu(self.tree2, tearoff=0,bg=self.bg)
        self.Popup2.bind("<FocusOut>",lambda event : self.Popup2.unpost() )

        #######################################################################
        #scan dialog

        def ScanDialogReturnPressed(event=None):
            focus=self.ScanDialog.focus_get()
            try:
                focus.invoke()
            except:
                pass

        self.ScanDialog = tk.Toplevel(self.main)
        self.ScanDialog.protocol("WM_DELETE_WINDOW", self.ScanDialogClose)
        self.ScanDialog.minsize(600, 400)
        self.ScanDialog.wm_transient(self.main)
        self.ScanDialog.update()
        self.ScanDialog.withdraw()
        self.ScanDialog.iconphoto(False, iconphoto)

        self.ScanDialogMainFrame = tk.Frame(self.ScanDialog,bg=self.bg)
        self.ScanDialogMainFrame.pack(expand=1, fill='both')

        self.ScanDialog.config(bd=0, relief=FLAT)

        self.ScanDialog.title('Scan')

        self.sizeMinVar=tk.StringVar()
        self.sizeMaxVar=tk.StringVar()
        self.ResultsLimitVar=tk.StringVar()
        self.WriteScanToLog=tk.BooleanVar()

        self.ResultsLimitVar.set(self.cfg.Get('resultsLimit','1000'))
        self.WriteScanToLog.set(False)

        self.ScanDialogMainFrame.grid_columnconfigure(0, weight=1)
        self.ScanDialogMainFrame.grid_rowconfigure(0, weight=1)
        self.ScanDialogMainFrame.grid_rowconfigure(1, weight=1)

        self.ScanDialog.bind('<Escape>', self.ScanDialogClose)
        self.ScanDialog.bind('<KeyPress-Return>', ScanDialogReturnPressed)

        self.ScanDialog.bind('<Alt_L><a>',lambda event : self.AddPathDialog())
        self.ScanDialog.bind('<Alt_L><A>',lambda event : self.AddPathDialog())
        self.ScanDialog.bind('<Alt_L><s>',lambda event : self.Scan())
        self.ScanDialog.bind('<Alt_L><S>',lambda event : self.Scan())

        self.ScanDialog.bind('<Alt_L><D>',lambda event : self.AddDrives())
        self.ScanDialog.bind('<Alt_L><d>',lambda event : self.AddDrives())

        self.ScanDialog.bind('<Alt_L><E>',lambda event : self.AddExckludeMaskDialog())
        self.ScanDialog.bind('<Alt_L><e>',lambda event : self.AddExckludeMaskDialog())

        ##############
        self.pathsFrame = tk.LabelFrame(self.ScanDialogMainFrame,text='Paths To Scan:',borderwidth=2,bg=self.bg)
        self.pathsFrame.grid(row=0,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        self.AddPathButton = ttk.Button(self.pathsFrame,width=10,text="Add Path ...",command=self.AddPathDialog,underline=0)
        self.AddPathButton.grid(column=0, row=100,pady=4,padx=4)

        self.AddDrivesButton = ttk.Button(self.pathsFrame,width=10,text="Add drives",command=self.AddDrives,underline=4)
        self.AddDrivesButton.grid(column=1, row=100,pady=4,padx=4)

        self.ClearListButton=ttk.Button(self.pathsFrame,width=10,text="Clear List",command=self.ClearPaths )
        self.ClearListButton.grid(column=2, row=100,pady=4,padx=4)

        self.pathsFrame.grid_columnconfigure(1, weight=1)
        self.pathsFrame.grid_rowconfigure(99, weight=1)

        ##############
        self.ScanExcludeRegExpr=tk.BooleanVar()
        self.ScanExcludeRegExpr.set(self.cfg.Get(CFG_KEY_EXCLUDE_REGEXP,False) == 'True')

        self.ExcludeFRame = tk.LabelFrame(self.ScanDialogMainFrame,text='Exclude from scan:',borderwidth=2,bg=self.bg)
        self.ExcludeFRame.grid(row=1,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        self.AddExckludeMaskButton = ttk.Button(self.ExcludeFRame,width=16,text="Add Exclude Mask ...",command=self.AddExckludeMaskDialog,underline=4)
        self.AddExckludeMaskButton.grid(column=0, row=100,pady=4,padx=4)

        self.ClearExcludeListButton=ttk.Button(self.ExcludeFRame,width=10,text="Clear List",command=self.ClearExcludeMasks )
        self.ClearExcludeListButton.grid(column=2, row=100,pady=4,padx=4)

        self.ExcludeFRame.grid_columnconfigure(1, weight=1)
        self.ExcludeFRame.grid_rowconfigure(99, weight=1)
        ##############

        tk.Label(self.ScanDialogMainFrame,text='Limit scan groups main results number to biggest:',borderwidth=2,anchor='w',bg=self.bg).grid(row=2,column=0,sticky='news',padx=4,pady=4,columnspan=3)
        ttk.Button(self.ScanDialogMainFrame,textvariable=self.ResultsLimitVar,command=self.setResultslimit,width=10).grid(row=2,column=3,sticky='wens',padx=8,pady=3)

        ttk.Checkbutton(self.ScanDialogMainFrame,text='Write scan results to application log',variable=self.WriteScanToLog).grid(row=3,column=0,sticky='news',padx=8,pady=3,columnspan=3)

        frame2 = tk.Frame(self.ScanDialogMainFrame,bg=self.bg)
        frame2.grid(row=6,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        self.ScanButton = ttk.Button(frame2,width=12,text="Scan",command=self.Scan,underline=0)
        self.ScanButton.pack(side='right',padx=4,pady=4)
        ttk.Button(frame2,width=12,text="Cancel",command=self.ScanDialogClose ).pack(side='left',padx=4,pady=4)

        #######################################################################
        #Settings Dialog
        self.SetingsDialog = tk.Toplevel(self.main)
        self.SetingsDialog.protocol("WM_DELETE_WINDOW", self.SettingsDialogClose)
        self.SetingsDialog.minsize(400, 300)
        self.SetingsDialog.wm_transient(self.main)
        self.SetingsDialog.update()
        self.SetingsDialog.withdraw()
        self.SetingsDialog.iconphoto(False, iconphoto)

        self.addCwdAtStartup = tk.BooleanVar()
        self.addCwdAtStartup.set(self.cfg.Get(CFG_KEY_STARTUP_ADD_CWD,True))

        self.scanAtStartup = tk.BooleanVar()
        self.scanAtStartup.set(self.cfg.Get(CFG_KEY_STARTUP_SCAN,False))

        self.showothers = tk.BooleanVar()
        self.showothers.set(self.cfg.Get(CFG_KEY_SHOW_OTHERS,True))

        self.fullCRC = tk.BooleanVar()
        self.fullCRC.set(self.cfg.Get(CFG_KEY_FULLCRC,False))

        self.fullPaths = tk.BooleanVar()
        self.fullPaths.set(self.cfg.Get(CFG_KEY_FULLPATHS,False))

        self.relSymlinks = tk.BooleanVar()
        self.relSymlinks.set(self.cfg.Get(CFG_KEY_REL_SYMLINKS,True))

        self.useRegExpr = tk.BooleanVar()
        self.useRegExpr.set(self.cfg.Get(CFG_KEY_USE_REG_EXPR,False))

        self.SetingsDialog.wm_title('Settings')

        fr=tk.Frame(self.SetingsDialog,bg=self.bg)
        fr.pack(expand=1,fill='both')

        def AddPathAtStartupChange(self):
            if not self.addCwdAtStartup.get():
                self.scanAtStartup.set(False)

        def ScanAtStartupChange(self):
            if self.scanAtStartup.get():
                self.addCwdAtStartup.set(True)

        row = 0
        self.AddCwdCB=ttk.Checkbutton(fr, text = 'At startup add current directory to paths to scan', variable=self.addCwdAtStartup,command=lambda : AddPathAtStartupChange(self) )
        self.AddCwdCB.grid(row=row,column=0,sticky='wens') ; row+=1
        self.StartScanCB=ttk.Checkbutton(fr, text = 'Start scanning at startup', variable=self.scanAtStartup,command=lambda : ScanAtStartupChange(self)                              )
        self.StartScanCB.grid(row=row,column=0,sticky='wens') ; row+=1

        ttk.Checkbutton(fr, text = 'Show non-duplicate items on directory panel', variable=self.showothers      ).grid(row=row,column=0,sticky='wens') ; row+=1
        ttk.Checkbutton(fr, text = 'Show full CRC', variable=self.fullCRC                                       ).grid(row=row,column=0,sticky='wens') ; row+=1
        ttk.Checkbutton(fr, text = 'Show full scan paths', variable=self.fullPaths                              ).grid(row=row,column=0,sticky='wens') ; row+=1
        ttk.Checkbutton(fr, text = 'Create relative symbolic links', variable=self.relSymlinks                  ).grid(row=row,column=0,sticky='wens') ; row+=1
        ttk.Checkbutton(fr, text = 'Use regular expressions matching', variable=self.useRegExpr                 ).grid(row=row,column=0,sticky='wens') ; row+=1

        bfr=tk.Frame(fr,bg=self.bg)
        fr.grid_rowconfigure(row, weight=1); row+=1

        bfr.grid(row=row,column=0) ; row+=1

        ttk.Button(bfr, text=' Set Defaults ', width=14, command=self.SettingsDialogReset).pack(side='left', anchor='n',padx=5,pady=5)
        ttk.Button(bfr, text='OK', width=14, command=self.SettingsDialogOK ).pack(side='left', anchor='n',padx=5,pady=5)

        self.SetingsDialogDefault=ttk.Button(bfr, text='Close', width=14 ,command=self.SettingsDialogClose )
        self.SetingsDialogDefault.pack(side='right', anchor='n',padx=5,pady=5)

        fr.grid_columnconfigure(0, weight=1)

        self.SetingsDialog.bind('<Escape>', self.SettingsDialogClose )

        try:
            self.license=pathlib.Path(os.path.join(os.path.dirname(__file__),'LICENSE')).read_text()
        except Exception as e:
            logging.error(e)
            self.exit()

        try:
            self.keyboardshortcuts=pathlib.Path(os.path.join(os.path.dirname(__file__),'keyboard.shortcuts.txt')).read_text()
        except Exception as e:
            logging.error(e)
            self.exit()
        #######################################################################
        #menu

        def MarkCascadePathFill():
            row=0
            self.MarkCascadePath.delete(0,END)
            for path in self.D.ScannedPaths:
                self.MarkCascadePath.add_command(label = self.Numbers[row] + '  =  ' + path,    command  = lambda pathpar=path: self.ActionOnSpecifiedPath(pathpar,self.SetMark)  )
                row+=1

        def UnmarkCascadePathFill():
            self.UnmarkCascadePath.delete(0,END)
            row=0
            for path in self.D.ScannedPaths:
                self.UnmarkCascadePath.add_command(label = self.Numbers[row] + '  =  ' + path,  command  = lambda pathpar=path: self.ActionOnSpecifiedPath(pathpar,self.UnsetMark)  )
                row+=1

        def FileCascadeFill():
            #self.PopupUnpost()

            self.FileCascade.delete(0,END)
            ItemActionsState=('disabled','normal')[self.SelItem!=None]

            self.FileCascade.add_command(label = 'Scan',command = self.ScanDialogShow, accelerator="S")
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'Settings',command=self.SettingsDialogShow, accelerator="F2")
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'go to dominant folder (by size sum)',command = lambda : self.GoToMaxFolder(1),accelerator="Backspace",state=ItemActionsState)
            self.FileCascade.add_command(label = 'go to dominant folder (by quantity)',command = lambda : self.GoToMaxFolder(0), accelerator="Ctrl+Backspace",state=ItemActionsState)
            self.FileCascade.add_command(label = 'go to dominant group (by size sum)',command = lambda : self.GoToMaxGroup(1), accelerator="Shift+Backspace",state=ItemActionsState)
            self.FileCascade.add_command(label = 'go to dominant group (by quantity)',command = lambda : self.GoToMaxGroup(0), accelerator="Shift+Ctrl+Backspace",state=ItemActionsState)
            self.FileCascade.add_separator()

            self.FileCascade.add_command(label = 'Open File',command = self.TreeEventOpenFile,accelerator="F3, Return",state=ItemActionsState)
            self.FileCascade.add_command(label = 'Open Folder',command = self.OpenFolder,state=ItemActionsState)
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'Copy file with path to clipboard',command = self.ClipCopy,accelerator="Ctrl+C",state = 'normal' if self.pyperclipOperational and self.SelItem!=None else 'disabled')
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'Erase CRC Cache',command = self.CleanCache)
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'Exit',command = self.exit)

        def MarkingCommonCascadeFill():
            #self.PopupUnpost()

            self.MarkingCommonCascade.delete(0,END)
            ItemActionsState=('disabled','normal')[self.SelItem!=None]

            self.MarkingCommonCascade.add_cascade(label = 'Set',menu = self.MarkCascade,state=ItemActionsState)
            self.MarkingCommonCascade.add_cascade(label = 'Unset',menu = self.UnmarkCascade,state=ItemActionsState)
            self.MarkingCommonCascade.add_command(label = 'Invert',command = lambda : self.MarkOnAll(self.InvertMark),accelerator="Ctrl+I, *",state=ItemActionsState)

        self.MarkingCommonCascade= Menu(self.menubar,tearoff=0,bg=self.bg,postcommand=MarkingCommonCascadeFill)

        self.FileCascade= Menu(self.menubar,tearoff=0,bg=self.bg,postcommand=FileCascadeFill)
        self.menubar.add_cascade(label = 'File',menu = self.FileCascade,accelerator="Alt+F")

        self.MarkCascade= Menu(self.MarkingCommonCascade,tearoff=0,bg=self.bg)
        self.MarkCascade.add_command(label = "All files",        command = lambda : self.MarkOnAll(self.SetMark),accelerator="Ctrl+A")
        self.MarkCascade.add_separator()
        self.MarkCascade.add_command(label = "Mark Oldest files",     command = lambda : self.MarkOnAllByCTime('oldest',self.SetMark),accelerator="Ctrl+O")
        self.MarkCascade.add_command(label = "Unmark Oldest files",   command = lambda : self.MarkOnAllByCTime('oldest',self.UnsetMark),accelerator="Ctrl+Shift+O")
        self.MarkCascade.add_separator()
        self.MarkCascade.add_command(label = "Mark Youngest files",   command = lambda : self.MarkOnAllByCTime('youngest',self.SetMark),accelerator="Ctrl+Y")
        self.MarkCascade.add_command(label = "Unmark Youngest files", command = lambda : self.MarkOnAllByCTime('youngest',self.UnsetMark),accelerator="Ctrl+Shift+Y")
        self.MarkCascade.add_separator()
        self.MarkCascade.add_command(label = "Files on the same path",  command = lambda : self.MarkPathOfFile(self.SetMark),accelerator="Ctrl+P")
        self.MarkCascade.add_command(label = "Specified Directory ...",   command = lambda : self.MarkSubpath(self.SetMark))

        self.MarkCascadePath = Menu(self.MarkCascade, tearoff = 0,postcommand=MarkCascadePathFill,bg=self.bg)
        self.MarkCascade.add_cascade(label = "Scan path",             menu = self.MarkCascadePath)
        self.MarkCascade.add_separator()
        self.MarkCascade.add_command(label = "Expression on file  ...",          command = lambda : self.MarkExpression('file',self.SetMark,'Mark files'))
        self.MarkCascade.add_command(label = "Expression on sub-path ...",       command = lambda : self.MarkExpression('path',self.SetMark,'Mark files'))
        self.MarkCascade.add_command(label = "Expression on file with path ...", command = lambda : self.MarkExpression('both',self.SetMark,'Mark files'),accelerator="+")

        self.UnmarkCascade= Menu(self.MarkingCommonCascade,tearoff=0,bg=self.bg)
        self.UnmarkCascade.add_command(label = "All files",   command = lambda : self.MarkOnAll(self.UnsetMark),accelerator="Ctrl+Shift+A / Ctrl+N")
        self.UnmarkCascade.add_separator()
        self.UnmarkCascade.add_command(label = "Oldest files",         command = lambda : self.MarkOnAllByCTime('oldest',self.UnsetMark),accelerator="Ctrl+Shift+O")
        self.UnmarkCascade.add_command(label = "Youngest files",       command = lambda : self.MarkOnAllByCTime('youngest',self.UnsetMark),accelerator="Ctrl+Shift+Y")
        self.UnmarkCascade.add_separator()
        self.UnmarkCascade.add_command(label = "Files on the same path",             command = lambda : self.MarkPathOfFile(self.UnsetMark),accelerator="Ctrl+Shift+P")
        self.UnmarkCascade.add_command(label = "Specified Directory ...",            command = lambda : self.MarkSubpath(self.UnsetMark))

        self.UnmarkCascadePath = Menu(self.UnmarkCascade, tearoff = 0,postcommand=UnmarkCascadePathFill,bg=self.bg)
        self.UnmarkCascade.add_cascade(label = "Scan path",             menu = self.UnmarkCascadePath)
        self.UnmarkCascade.add_separator()
        self.UnmarkCascade.add_command(label = "Expression on file ...",           command = lambda : self.MarkExpression('file',self.UnsetMark,'Unmark files'))
        self.UnmarkCascade.add_command(label = "Expression on sub-path ...",       command = lambda : self.MarkExpression('path',self.UnsetMark,'Unmark files'))
        self.UnmarkCascade.add_command(label = "Expression on file with path ...", command = lambda : self.MarkExpression('both',self.UnsetMark,'Unmark files'),accelerator="-")

        self.menubar.add_cascade(label = 'Mark',menu = self.MarkingCommonCascade)

        def ActionCascadeFill():
            #self.PopupUnpost()

            self.ActionCascade.delete(0,END)
            ItemActionsState=('disabled','normal')[self.SelItem!=None]
            MarksState=('disabled','normal')[len(self.tree1.tag_has(MARK))!=0]

            self.ActionCascade.add_command(label = 'Remove Local Marked Files',command=lambda : self.ProcessFiles('delete',0),accelerator="Delete",state=MarksState)
            self.ActionCascade.entryconfig(3,foreground='red',activeforeground='red')
            self.ActionCascade.add_command(label = 'Remove All Marked Files',command=lambda : self.ProcessFiles('delete',1),accelerator="Ctrl+Delete",state=MarksState)
            self.ActionCascade.entryconfig(4,foreground='red',activeforeground='red')
            self.ActionCascade.add_separator()
            self.ActionCascade.add_command(label = 'Softlink Local Marked Files',command=lambda : self.ProcessFiles('softlink',0),accelerator="Insert",state=MarksState)
            self.ActionCascade.entryconfig(6,foreground='red',activeforeground='red')
            self.ActionCascade.add_command(label = 'Softlink All Marked Files',command=lambda : self.ProcessFiles('softlink',1),accelerator="Ctrl+Insert",state=MarksState)
            self.ActionCascade.entryconfig(7,foreground='red',activeforeground='red')
            self.ActionCascade.add_separator()
            self.ActionCascade.add_command(label = 'Hardlink Local Marked Files',command=lambda : self.ProcessFiles('hardlink',0),accelerator="Shift+Insert",state=MarksState)
            self.ActionCascade.entryconfig(9,foreground='red',activeforeground='red')
            self.ActionCascade.add_command(label = 'Hardlink All Marked Files',command=lambda : self.ProcessFiles('hardlink',1),accelerator="Ctrl+Shift+Insert",state=MarksState)
            self.ActionCascade.entryconfig(10,foreground='red',activeforeground='red')

        self.ActionCascade= Menu(self.menubar,tearoff=0,bg=self.bg,postcommand=ActionCascadeFill)
        self.menubar.add_cascade(label = 'Action',menu = self.ActionCascade)

        self.HelpCascade= Menu(self.menubar,tearoff=0,bg=self.bg)
        self.HelpCascade.add_command(label = 'About',command=self.About)
        self.HelpCascade.add_command(label = 'Keyboard Shortcuts',command=self.KeyboardShortcuts,accelerator="F1")
        self.HelpCascade.add_command(label = 'License',command=self.License)

        self.menubar.add_cascade(label = 'Help',menu = self.HelpCascade)

        #######################################################################

        self.SettingsSetBools()

        if self.AddCwdAtStartup:
            self.addPath(cwd)

        self.ScanDialogShow()

        self.ColumnSortLastParams={}
        self.ColumnSortLastParams[self.tree1]=['sizeH',1]
        self.ColumnSortLastParams[self.tree2]=['sizeH',1]

        self.ShowData()

        if self.ScanAtStarup:
            self.main.update()
            self.Scan()

        self.main.mainloop()

    def GetIndexTupleTree1(self,item):
        return self.GetIndexTuple(item,self.tree1)

    def GetIndexTupleTree2(self,item):
        return self.GetIndexTuple(item,self.tree2)

    def GetIndexTuple(self,item,tree):
        return tuple([ fn(tree.item(item)['values'][index]) for fn,index in self.IndexTupleIndexesWithFnCommon ])

    def exit(self):
        self.GeometryStore(self.main)
        self.ScanDialog.destroy()
        self.SetingsDialog.destroy()
        self.StoreSplitter()
        exit()

    def WidgetId(self,widget):
        wid=widget.wm_title()
        wid=wid.replace(' ','_')
        wid=wid.replace('!','_')
        wid=wid.replace('?','_')
        wid=wid.replace('(','_')
        wid=wid.replace(')','_')
        wid=wid.replace('.','_')
        return wid

    def SetDefaultGeometryAndShow(self,widget,parent):
        CfgGeometry=self.cfg.Get(self.WidgetId(widget),None,section='geometry')

        if CfgGeometry != None and CfgGeometry != 'None':
            widget.geometry(CfgGeometry)
        elif parent :
            widget.geometry(CenterToParentGeometry(widget,parent))
        else:
            widget.geometry(CenterToScreenGeometry(widget))

        widget.deiconify()

        #prevent displacement
        if CfgGeometry != None and CfgGeometry != 'None':
            widget.geometry(CfgGeometry)

    def GeometryStore(self,widget):
        self.cfg.Set(self.WidgetId(widget),str(widget.geometry()),section='geometry')
        self.cfg.Write()

    def DialogWithEntry(self,title,prompt,parent,initialvalue='',OnlyInfo=False,width=400,height=140):
        parent.config(cursor="watch")

        dialog = tk.Toplevel(parent)
        dialog.minsize(width, height)
        dialog.wm_transient(parent)
        dialog.update()
        dialog.withdraw()
        dialog.wm_title(title)
        dialog.config(bd=2, relief=FLAT,bg=self.bg)
        dialog.iconphoto(False, iconphoto)

        res=set()

        EntryVar=tk.StringVar(value=initialvalue)

        def over():
            self.GeometryStore(dialog)
            dialog.destroy()
            parent.config(cursor="")
            try:
                dialog.update()
            except Exception as e:
                pass

        def Yes(event=None):
            over()
            nonlocal res
            nonlocal EntryVar
            res.add(EntryVar.get())

        def No(event=None):
            over()
            nonlocal res
            res.add(False)

        dialog.protocol("WM_DELETE_WINDOW", No)

        def ReturnPressed(event=None):
            nonlocal dialog
            nonlocal ok
            nonlocal entry

            focus=dialog.focus_get()
            if focus==ok or focus==entry:
                Yes()
            else:
                No()

        tk.Label(dialog,text=prompt,anchor='n',justify='center',bg=self.bg).grid(sticky='news',row=0,column=0,padx=5,pady=5)
        if not OnlyInfo:
            (entry:=ttk.Entry(dialog,textvariable=EntryVar)).grid(sticky='news',row=1,column=0,padx=5,pady=5)

        (bfr:=tk.Frame(dialog,bg=self.bg)).grid(sticky='news',row=2,column=0,padx=5,pady=5)

        if OnlyInfo:
            ok=default=ttk.Button(bfr, text='OK', width=10 ,command=No )
            ok.pack()
        else:
            ok=ttk.Button(bfr, text='OK', width=10, command=Yes)
            ok.pack(side='left', anchor='e',padx=5,pady=5)
            default=cancel=ttk.Button(bfr, text='Cancel', width=10 ,command=No )
            cancel.pack(side='right', anchor='w',padx=5,pady=5)

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        dialog.bind('<Escape>', No)
        dialog.bind('<KeyPress-Return>', ReturnPressed)

        PrevGrab = dialog.grab_current()

        self.SetDefaultGeometryAndShow(dialog,parent)

        if OnlyInfo:
            ok.focus_set()
        else:
            entry.focus_set()

        dialog.grab_set()
        parent.wait_window(dialog)

        if PrevGrab:
            PrevGrab.grab_set()
        else:
            dialog.grab_release()

        return next(iter(res))

    def dialog(self,parent,title,message,OnlyInfo=False,textwidth=128,width=800,height=400):
        parent.config(cursor="watch")

        dialog = tk.Toplevel(parent)
        dialog.minsize(width,height)
        dialog.wm_transient(parent)
        dialog.update()
        dialog.withdraw()
        dialog.wm_title(title)
        dialog.config(bd=2, relief=FLAT,bg=self.bg)
        dialog.iconphoto(False, iconphoto)

        res=set()

        def over():
            self.GeometryStore(dialog)
            dialog.destroy()
            parent.config(cursor="")
            try:
                dialog.update()
            except Exception as e:
                pass

        def Yes(event=None):
            over()
            nonlocal res
            res.add(True)

        def No(event=None):
            over()
            nonlocal res
            res.add(False)

        dialog.protocol("WM_DELETE_WINDOW", No)

        def ReturnPressed(event=None):
            nonlocal dialog
            nonlocal default

            focus=dialog.focus_get()
            if focus==default:
                No()
            else:
                Yes()

        st=scrolledtext.ScrolledText(dialog,relief='groove', bd=2,bg='white',width = textwidth,takefocus=True )
        st.frame.config(bg=self.bg,takefocus=False)
        st.vbar.config(bg=self.bg,takefocus=False)

        st.tag_configure('RED', foreground='red')
        st.tag_configure('GRAY', foreground='gray')

        for line in message.split('\n'):
            lineSplitted=line.split('|')
            tag=lineSplitted[1] if len(lineSplitted)>1 else None

            st.insert(END, lineSplitted[0] + "\n", tag)

        st.configure(state=DISABLED)
        st.grid(row=0,column=0,sticky='news',padx=5,pady=5)

        bfr=tk.Frame(dialog,bg=self.bg)
        bfr.grid(row=2,column=0)

        if OnlyInfo:
            default=ttk.Button(bfr, text='OK', width=10 ,command=No )
            default.pack()
        else:
            ttk.Button(bfr, text='OK', width=10, command=Yes).pack(side='left', anchor='e',padx=5,pady=5)
            default=ttk.Button(bfr, text='Cancel', width=10 ,command=No )
            default.pack(side='right', anchor='w',padx=5,pady=5)

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        dialog.bind('<Escape>', No)
        dialog.bind('<KeyPress-Return>', ReturnPressed)

        PrevGrab = dialog.grab_current()

        self.SetDefaultGeometryAndShow(dialog,parent)

        default.focus_set()

        dialog.grab_set()
        parent.wait_window(dialog)

        if PrevGrab:
            PrevGrab.grab_set()
        else:
            dialog.grab_release()

        return next(iter(res))

    def Ask(self,title,message,top,width=1000,height=400):
        return self.dialog(top,title,message,False,width=width,height=height)

    def Info(self,title,message,top,textwidth=128,width=400,height=200):
        return self.dialog(top,title,message,True,textwidth=textwidth,width=width,height=height)

    def ToggleSelectedTag(self,tree, *items):
        for item in items:
            if tree.set(item,'kind')==FILE:
                self.InvertMark(item, self.tree1)
                try:
                    self.tree2.item(item,tags=self.tree1.item(item)['tags'])
                except Exception :
                    pass
            elif tree.set(item,'kind')==CRC:
                return self.ToggleSelectedTag(tree, *tree.get_children(item) )

        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

#################################################
    def KeyPressGlobal(self,event):
        if event.keysym=='F1':
            self.KeyboardShortcuts()
        elif event.keysym=='F2':
            self.SettingsDialogShow()
        elif event.keysym in ('s','S') :
            self.ScanDialogShow()

    def KeyPressTreeCommon(self,event):
        tree=event.widget
        tree.selection_remove(tree.selection())

        if event.keysym in ("Up",'Down') :
            return
        elif event.keysym == "Right":
            self.GotoNextMark(event.widget,1)
        elif event.keysym == "Left":
            self.GotoNextMark(event.widget,-1)
        elif event.keysym == "Tab":
            tree.selection_set(tree.focus())
            self.FromTabSwicth=True
        elif event.keysym=='KP_Multiply' or event.keysym=='asterisk':
            self.MarkOnAll(self.InvertMark)
        elif event.keysym=='F3' or event.keysym=='Return':
            item=tree.focus()
            if item:
                if tree.set(item,'kind')!=CRC:
                    self.TreeEventOpenFile()
        else:
            #print(event.keysym)
            pass

#################################################
    def SelectFocusAndSeeCrcItemTree(self,crc):
        self.tree1.focus_set()
        lastChild=self.tree1.get_children(crc)[-1]
        self.tree1.see(lastChild)
        self.tree1.update()
        self.tree1.see(crc)
        self.tree1.focus(crc)
        self.tree1.update()
        self.Tree1SelChange(crc)

#################################################
    def Tree1KeyRelease(self,event):
        item=self.tree1.focus()

        if event.keysym in ("Up","Down"):
            self.tree1.see(item)
            self.Tree1SelChange(item)
        elif event.keysym in ("Prior","Next"):
            itemsPool=self.tree1.get_children()
            NextItem=itemsPool[(itemsPool.index(self.tree1.set(item,'crc'))+(1 if event.keysym=="Next" else -1)) % len(itemsPool)]

            self.SelectFocusAndSeeCrcItemTree(NextItem)
        elif event.keysym in ("Home","End"):
            if NextItem:=self.tree1.get_children()[0 if event.keysym=="Home" else -1]:
                self.SelectFocusAndSeeCrcItemTree(NextItem)
        elif event.keysym == "space":
            if self.tree1.set(item,'kind')==CRC:
                self.ToggleSelectedTag(self.tree1,*self.tree1.get_children(item))
            else:
                self.ToggleSelectedTag(self.tree1,item)

    def Tree2KeyRelease(self,event):
        item=self.tree2.focus()

        if event.keysym in ("Up",'Down') :
            self.tree2.see(item)
            self.Tree2SelChange(item)
        elif event.keysym in ('Prior','Next'):
            itemsPool=self.tree2.get_children()
            NextItem=itemsPool[(itemsPool.index(item)+(5 if event.keysym=='Next' else -5)) % len(itemsPool)]
            self.tree2.focus(NextItem)
            self.tree2.see(NextItem)
            self.Tree2SelChange(NextItem)
            self.tree2.update()
        elif event.keysym in ("Home","End"):
            if NextItem:=self.tree2.get_children()[0 if event.keysym=='Home' else -1]:
                self.tree2.see(NextItem)
                self.tree2.focus(NextItem)
                self.Tree2SelChange(NextItem)
                self.tree2.update()
        elif event.keysym == "space":
            self.ToggleSelectedTag(self.tree2,item)

    def TreeButtonPress(self,event,toggle=False):
        #self.PopupUnpost()
        self.MenubarUnpost()

        tree=event.widget

        if tree.identify("region", event.x, event.y) == 'heading':
            if (colname:=tree.column(tree.identify_column(event.x),'id') ) in self.col2sortOf:
                tree.focus_set()
                self.ColumnSortClick(tree,colname)

        elif item:=tree.identify('item',event.x,event.y):
            tree.selection_remove(tree.selection())

            tree.focus_set()
            tree.focus(item)

            if tree==self.tree1:
                self.Tree1SelChange(item)
            else:
                self.Tree2SelChange(item)

            if toggle:
                self.ToggleSelectedTag(tree,item)

    FromTabSwicth=False
    def TreeEventFocusIn(self,event):
        tree=event.widget

        item=None

        if sel:=tree.selection():
            tree.selection_remove(sel)
            item=sel[0]

        if not item:
            item=tree.focus()

        if self.FromTabSwicth:
            self.FromTabSwicth=False

            if item:
                tree.focus(item)
                if tree==self.tree1:
                    self.Tree1SelChange(item,True)
                else:
                    self.Tree2SelChange(item)

                tree.see(item)

        if len(self.tree2.get_children())==0:
            self.tree1.selection_remove(self.tree1.selection())
            self.tree1.focus_set()

    def TreeFocusOut(self,event):
        tree=event.widget
        tree.selection_set(tree.focus())

    def Tree1SelChange(self,item,force=False):
        pathnr=self.tree1.set(item,'pathnr')
        path=self.tree1.set(item,'path')

        self.SelFile = self.tree1.set(item,'file')
        self.SelCrc = self.tree1.set(item,'crc')
        self.SelKind = self.tree1.set(item,'kind')
        self.SelItem = item
        self.SelTreeIndex=0

        if path!=self.SelPath or pathnr!=self.SelPathnr or force:
            self.SelPathnr = pathnr

            if pathnr: #non crc node
                self.SelPathnrInt= int(pathnr)
                self.SelSearchPath = self.D.ScannedPaths[self.SelPathnrInt]
                self.SelectedSearchPathCode.set(self.Numbers[self.SelPathnrInt])
                self.SelectedSearchPath.set(self.SelSearchPath)
                self.SelPath = path
                self.SelFullPath=self.SelSearchPath+self.SelPath
            else :
                self.SelPathnrInt= 0
                self.SelSearchPath = None
                self.SelectedSearchPathCode.set(None)
                self.SelectedSearchPath.set(None)
                self.SelPath = None
                self.SelFullPath= None

            UpdateTree2=True
        else:
            UpdateTree2=False

        if self.SelKind==FILE:
            self.SetCommonVar()
            self.UpdatePathTree(item)
        else:
            self.StatusVarFullPath.set("")
            self.UpdatePathTreeNone()
            self.StatusVarFullPathLabel.config(fg = 'black')

    def Tree2SelChange(self,item):
        self.SelFile = self.tree2.set(item,'file')
        self.SelCrc = self.tree2.set(item,'crc')
        self.SelKind = self.tree2.set(item,'kind')
        self.SelItem = item
        self.SelTreeIndex=1

        if self.tree2.set(item,'kind')==FILE:
            self.UpdateMainTree(item)
            self.SetCommonVar()
        else:
            self.UpdateMainTreeNone()
            self.StatusVarFullPath.set("")

    #def PopupUnpost(self):
    #    try:
    #        self.Popup.unpost()
    #    except Exception as e:
    #        print(e)

    def MenubarUnpost(self):
        try:
            self.menubar.unpost()
        except Exception as e:
            print(e)

    def TreeContexMenu(self,event):
        self.TreeButtonPress(event)

        tree=event.widget

        ItemActionsState=('disabled','normal')[self.SelItem!=None]
        FileActionsState=('disabled',ItemActionsState)[self.SelKind==FILE]

        if tree==self.tree1:
            pop=self.Popup1
        else:
            pop=self.Popup2

        pop.delete(0,END)

        if tree==self.tree1:
            cLocal = Menu(pop,tearoff=0,bg=self.bg)
            cLocal.add_command(label = "Toggle Mark",  command = lambda : self.ToggleSelectedTag(tree,self.SelItem),accelerator="space")
            cLocal.add_separator()
            cLocal.add_command(label = "Mark all files",        command = lambda : self.MarkInCRCGroup(self.SetMark),accelerator="A")
            cLocal.add_command(label = "Unmark all files",        command = lambda : self.MarkInCRCGroup(self.UnsetMark),accelerator="N")
            cLocal.add_separator()
            cLocal.add_command(label = "Toggle mark on oldest file",     command = lambda : self.MarkInCRCGroupByCTime('oldest',self.InvertMark),accelerator="O")
            cLocal.add_command(label = "Toggle mark on youngest file",   command = lambda : self.MarkInCRCGroupByCTime('youngest',self.InvertMark),accelerator="Y")
            cLocal.add_separator()
            cLocal.add_command(label = "Invert marks",   command = lambda : self.MarkInCRCGroup(self.InvertMark),accelerator="I")
            cLocal.add_separator()

            MarksState=('disabled','normal')[len(tree.tag_has(MARK))!=0]

            cLocal.add_command(label = 'Remove Marked Files',command=lambda : self.ProcessFiles('delete',0),accelerator="Delete",state=MarksState)
            cLocal.entryconfig(10,foreground='red',activeforeground='red')
            cLocal.add_command(label = 'Softlink Marked Files',command=lambda : self.ProcessFiles('softlink',0),accelerator="Insert",state=MarksState)
            cLocal.entryconfig(11,foreground='red',activeforeground='red')
            cLocal.add_command(label = 'Hardlink Marked Files',command=lambda : self.ProcessFiles('hardlink',0),accelerator="Shift+Insert",state=MarksState)
            cLocal.entryconfig(12,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'Local (this CRC group)',menu = cLocal,state=ItemActionsState)
            pop.add_separator()

            cAll = Menu(pop,tearoff=0,bg=self.bg)

            cAll.add_command(label = "Mark all files",        command = lambda : self.MarkOnAll(self.SetMark),accelerator="Ctrl+A")
            cAll.add_command(label = "Unmark all files",        command = lambda : self.MarkOnAll(self.UnsetMark),accelerator="Ctrl+N")
            cAll.add_separator()
            cAll.add_command(label = "Mark Oldest files",     command = lambda : self.MarkOnAllByCTime('oldest',self.SetMark),accelerator="Ctrl+O")
            cAll.add_command(label = "Unmark Oldest files",     command = lambda : self.MarkOnAllByCTime('oldest',self.UnsetMark),accelerator="Ctrl+Shift+O")
            cAll.add_separator()
            cAll.add_command(label = "Mark Youngest files",   command = lambda : self.MarkOnAllByCTime('youngest',self.SetMark),accelerator="Ctrl+Y")
            cAll.add_command(label = "Unmark Youngest files",   command = lambda : self.MarkOnAllByCTime('youngest',self.UnsetMark),accelerator="Ctrl+Shift+Y")
            cAll.add_separator()
            cAll.add_command(label = "Invert marks",   command = lambda : self.MarkOnAll(self.InvertMark),accelerator="Ctrl+I, *")
            cAll.add_separator()

            cAll.add_command(label = 'Remove Marked Files',command=lambda : self.ProcessFiles('delete',1),accelerator="Ctrl+Delete",state=MarksState)
            cAll.entryconfig(12,foreground='red',activeforeground='red')
            cAll.add_command(label = 'Softlink Marked Files',command=lambda : self.ProcessFiles('softlink',1),accelerator="Ctrl+Insert",state=MarksState)
            cAll.entryconfig(13,foreground='red',activeforeground='red')
            cAll.add_command(label = 'Hardlink Marked Files',command=lambda : self.ProcessFiles('hardlink',1),accelerator="Ctrl+Shift+Insert",state=MarksState)
            cAll.entryconfig(14,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'All Files',menu = cAll,state=ItemActionsState)

            cNav = Menu(self.menubar,tearoff=0,bg=self.bg)
            cNav.add_command(label = 'go to dominant group (by size sum)',command = lambda : self.GoToMaxGroup(1), accelerator="Shift+Backspace")
            cNav.add_command(label = 'go to dominant group (by quantity)',command = lambda : self.GoToMaxGroup(0), accelerator="Shift+Ctrl+Backspace")

        else:
            cLocal = Menu(pop,tearoff=0,bg=self.bg)
            cLocal.add_command(label = "Toggle Mark",  command = lambda : self.ToggleSelectedTag(tree,self.SelItem),accelerator="space",state=FileActionsState)
            cLocal.add_separator()
            cLocal.add_command(label = "Mark all files",        command = lambda : self.MarkLowerPane(self.SetMark),accelerator="A",state=FileActionsState)
            cLocal.add_command(label = "Unmark all files",        command = lambda : self.MarkLowerPane(self.UnsetMark),accelerator="N",state=FileActionsState)
            cLocal.add_separator()

            MarksState=('disabled','normal')[len(tree.tag_has(MARK))!=0]

            cLocal.add_command(label = 'Remove Marked Files',command=lambda : self.ProcessFiles('delete',0),accelerator="Delete",state=MarksState)
            cLocal.entryconfig(5,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'Local (this folder)',menu = cLocal,state=MarksState)

            cNav = Menu(pop,tearoff=0,bg=self.bg)
            cNav.add_command(label = 'go to dominant folder (by size sum)',command = lambda : self.GoToMaxFolder(1),accelerator="Backspace")
            cNav.add_command(label = 'go to dominant folder (by quantity)',command = lambda : self.GoToMaxFolder(0) ,accelerator="Ctrl+Backspace")

        pop.add_separator()
        pop.add_cascade(label = 'Navigation',menu = cNav,state=ItemActionsState)

        pop.add_separator()
        pop.add_command(label = 'Open File',command = self.TreeEventOpenFile,accelerator="F3, Return",state=FileActionsState)
        pop.add_command(label = 'Open Folder',command = self.OpenFolder,state=FileActionsState)

        pop.add_separator()
        pop.add_command(label = "Scan",  command = self.ScanDialogShow,accelerator="S")
        pop.add_command(label = "Settings",  command = self.SettingsDialogShow,accelerator="F2")
        pop.add_separator()
        pop.add_command(label = "Exit",  command = self.exit)

        try:
            pop.tk_popup(event.x_root, event.y_root)
        finally:
            pop.grab_release()

    def ColumnSortClick(self, tree, colname):
        prev_colname,prev_reverse=self.ColumnSortLastParams[tree]
        reverse = not prev_reverse if colname == prev_colname else prev_reverse
        tree.heading(prev_colname, text=self.OrgLabel[prev_colname])
        
        self.ColumnSortLastParams[tree]=[colname,reverse]
        self.ColumnSort(tree)

    def ColumnSort(self, tree):
        colname,reverse = self.ColumnSortLastParams[tree] 
        
        RealSortColumn=self.col2sortOf[colname]

        DIR0,DIR1 = (1,0) if reverse else (0,1)

        l = [((DIR0 if tree.set(item,'kind')==DIR else DIR1,tree.set(item,RealSortColumn)), item) for item in tree.get_children('')]
        l.sort(reverse=reverse,key=lambda x: ( (x[0][0],float(x[0][1])) if x[0][1].isdigit() else (x[0][0],0) ) if self.col2sortNumeric[colname] else x[0])

        {tree.move(item, '', index) for index, (val,item) in enumerate(l)}

        if self.col2sortLev2[colname]:
            for topItem in tree.get_children():
                l = [(tree.set(item,RealSortColumn), item) for item in tree.get_children(topItem)]
                l.sort(reverse=reverse,key=lambda x: (float(x[0]) if x[0].isdigit() else 0) if self.col2sortNumeric[colname] else x[0])

                {tree.move(item, topItem, index) for index, (val,item) in enumerate(l)}

        if item:=tree.focus():
            tree.see(item)
        elif item:=tree.selection():
            tree.see(item)

        tree.update()

        tree.heading(colname, text=self.OrgLabel[colname] + ' ' + str(u'\u25BC' if reverse else u'\u25B2') )

        if tree==self.tree1:
            self.FlatItemsListUpdate()

    def addPath(self,path):
        if len(self.PathsToScanFromDialog)<10:
            self.PathsToScanFromDialog.append(path)
            self.UpdatePathsToScan()
        else:
            logging.error(f'cant add:{path}. limit exceeded')

    def Scan(self):
        resultslimitStr=self.ResultsLimitVar.get()

        try:
            resultslimit = int(resultslimitStr)
        except Exception as e:
            self.DialogWithEntry(title='Error',prompt='Results limit wrong format: \'' + resultslimitStr + '\'\n' + e,parent=self.ScanDialog,OnlyInfo=True)
            return

        self.cfg.Set('resultslimit',resultslimitStr)

        self.cfg.Write()

        self.D.INIT()
        self.StatusVarFullPath.set('')
        self.ShowData()

        self.D.setLimit(resultslimit)

        PathsToScanFromEntry = [var.get() for var in self.PathsToScanEntryVar.values()]
        ExcludeVarsFromEntry = [var.get() for var in self.ExcludeEntryVar.values()]

        if not PathsToScanFromEntry:
            self.DialogWithEntry(title='Error. No paths to scan.',prompt='Add paths to scan.',parent=self.ScanDialog,OnlyInfo=True)

        if res:=self.D.SetPathsToScan(PathsToScanFromEntry):
            self.Info('Error. Fix paths selection.',res,self.ScanDialog)
            return

        if res:=self.D.SetExcludeMasks(self.cfg.Get(CFG_KEY_EXCLUDE_REGEXP,False) == 'True',ExcludeVarsFromEntry):
            self.Info('Error. Fix Exclude masks.',res,self.ScanDialog)
            return

        self.cfg.Set(CFG_KEY_EXCLUDE,'|'.join(ExcludeVarsFromEntry))

        self.main.update()

        #############################
        self.LongActionDialogShow(self.ScanDialogMainFrame,'scanning')

        ScanThread=Thread(target=self.D.Scan,daemon=True)
        ScanThread.start()

        while ScanThread.is_alive():
            self.LongActionDialogUpdate(self.Numbers[self.D.InfoPathNr] + '\n' + self.D.InfoPathToScan + '\n\n' + str(self.D.InfoCounter) + '\n' + bytes2str(self.D.InfoSizeSum))

            if self.LongActionAbort:
                self.D.Abort()
                self.D.INIT()
                break
            else:
                time.sleep(0.04)

        ScanThread.join()
        self.LongActionDialogEnd()

        if self.LongActionAbort:
            return

        #############################
        if self.D.sumSize==0:
            self.DialogWithEntry(title='Cannot Proceed.',prompt='No Duplicates.',parent=self.ScanDialog,OnlyInfo=True)
            return
        #############################
        self.LongActionDialogShow(self.ScanDialogMainFrame,'crc calculation','determinate','determinate',Progress1LeftText='Total size:',Progress2LeftText='Files number:')

        self.D.writeLog=self.WriteScanToLog.get()

        ScanThread=Thread(target=self.D.CrcCalc,daemon=True)
        ScanThread.start()

        while ScanThread.is_alive():
            sumSizeStr='/' + bytes2str(self.D.sumSize)
            progress1Right=bytes2str(self.D.InfoSizeDone) + sumSizeStr
            progress2Right=str(self.D.InfoFileNr) + '/' + str(self.D.InfoTotal)

            InfoProgSize=(100.0/self.D.sumSize)*self.D.InfoSizeDone
            InfoProgQuant=(100.0/self.D.InfoTotal)*self.D.InfoFileNr

            info = '\ngroups found:' + str(self.D.InfoFoundSum) + '\ncurrent size: ' + bytes2str(self.D.InfoCurrentSize)
            self.LongActionDialogUpdate(info,InfoProgSize,InfoProgQuant,progress1Right,progress2Right)

            if self.LongActionAbort:
                self.D.Abort()
                self.D.Kill()
                self.D.INIT()
                break
            else:
                time.sleep(0.04)

        ScanThread.join()
        self.LongActionDialogEnd()
        #############################

        if self.LongActionAbort:
            return

        self.ShowData()
        self.ScanDialogClose()

    def ScanDialogShow(self):
        if self.D.ScannedPaths:
            self.PathsToScanFromDialog=self.D.ScannedPaths.copy()

        self.UpdateExcludeMasks()
        self.UpdatePathsToScan()

        self.ScanDialog.grab_set()
        self.main.config(cursor="watch")

        self.SetDefaultGeometryAndShow(self.ScanDialog,self.main)
        self.ScanButton.focus_set()

    def ScanDialogClose(self,event=None):
        self.ScanDialog.grab_release()
        self.main.config(cursor="")
        self.GeometryStore(self.ScanDialog)

        self.ScanDialog.withdraw()
        try:
            self.ScanDialog.update()
        except Exception as e:
            pass

    def UpdatePathsToScan(self) :
        for subframe in self.PathsToScanFrames:
            subframe.destroy()

        self.PathsToScanFrames=[]
        self.PathsToScanEntryVar={}

        row=0
        for path in self.PathsToScanFromDialog:
            (fr:=tk.Frame(self.pathsFrame,bg=self.bg)).grid(row=row,column=0,sticky='news',columnspan=3)
            self.PathsToScanFrames.append(fr)

            tk.Label(fr,text=' ' + self.Numbers[row] + ' ' , relief='groove',bg=self.bg).pack(side='left',padx=2,pady=1,fill='y')

            self.PathsToScanEntryVar[row]=tk.StringVar(value=path)
            ttk.Entry(fr,textvariable=self.PathsToScanEntryVar[row]).pack(side='left',expand=1,fill='both',pady=1)

            ttk.Button(fr,text='❌',command=lambda pathpar=path: self.RemovePath(pathpar),width=3).pack(side='right',padx=2,pady=1,fill='y')

            row+=1

        if len(self.PathsToScanFromDialog)==self.MAX_PATHS:
            self.AddPathButton.configure(state=DISABLED,text='')
            self.AddDrivesButton.configure(state=DISABLED,text='')
            self.ClearListButton.focus_set()
        else:
            self.AddPathButton.configure(state=NORMAL,text='Add path ...')
            self.AddDrivesButton.configure(state=NORMAL,text='Add drives ...')

    def ScanExcludeRegExprCommand(self):
        self.cfg.Set(CFG_KEY_EXCLUDE_REGEXP,str(self.ScanExcludeRegExpr.get()))

    def UpdateExcludeMasks(self) :
        for subframe in self.ExcludeFrames:
            subframe.destroy()

        self.ExcludeFrames=[]
        self.ExcludeEntryVar={}

        ttk.Checkbutton(self.ExcludeFRame,text='Use regular expressions matching',variable=self.ScanExcludeRegExpr,command=lambda : self.ScanExcludeRegExprCommand()).grid(row=0,column=0,sticky='news',columnspan=3)

        row=1

        for entry in self.cfg.Get(CFG_KEY_EXCLUDE,'').split('|'):
            if entry:
                (fr:=tk.Frame(self.ExcludeFRame,bg=self.bg)).grid(row=row,column=0,sticky='news',columnspan=3)
                self.ExcludeFrames.append(fr)

                self.ExcludeEntryVar[row]=tk.StringVar(value=entry)
                ttk.Entry(fr,textvariable=self.ExcludeEntryVar[row]).pack(side='left',expand=1,fill='both',pady=1)

                ttk.Button(fr,text='❌',command=lambda entrypar=entry: self.RemoveExcludeMask(entrypar),width=3).pack(side='right',padx=2,pady=1,fill='y')

                row+=1

    def AddDrives(self):
        for (device,mountpoint,fstype,opts,maxfile,maxpath) in psutil.disk_partitions():
            if fstype != 'squashfs':
                self.addPath(mountpoint)

    def AddPathDialog(self):
        if res:=tk.filedialog.askdirectory(title='select Directory',initialdir=self.cwd,parent=self.ScanDialogMainFrame):
            self.addPath(res)

    def AddExckludeMaskDialog(self):
        if (mask := self.DialogWithEntry(title=f'Specify Exclude Expression',prompt='Expression:', initialvalue='',parent=self.ScanDialog)):
            orglist=self.cfg.Get(CFG_KEY_EXCLUDE,'').split('|')
            orglist.append(mask)
            self.cfg.Set(CFG_KEY_EXCLUDE,'|'.join(orglist))
            self.UpdateExcludeMasks()

    def RemovePath(self,path) :
        self.PathsToScanFromDialog.remove(path)
        self.UpdatePathsToScan()

    def RemoveExcludeMask(self,mask) :
        orglist=self.cfg.Get(CFG_KEY_EXCLUDE,'').split('|')
        orglist.remove(mask)
        if '' in orglist:
            orglist.remove('')
        self.cfg.Set(CFG_KEY_EXCLUDE,'|'.join(orglist))
        self.UpdateExcludeMasks()

    def FocusIn(self,event):
        self.ScandirCache={}
        self.StatCache={}

    def License(self):
        self.Info('License',self.license,self.main,textwidth=80,width=600)

    def About(self):
        info=[]
        info.append('==============================================================================')
        info.append('                                                                              ')
        info.append(f'                       DUDE (DUplicates DEtector) v{VERSION}                    ')
        info.append('                              Piotr Jochymek                                  ')
        info.append('                          PJ.soft.dev.x@gmail.com                             ')
        info.append('                                                                              ')
        info.append('==============================================================================')
        info.append('                                                                              ')
        info.append('LOGS DIRECTORY     :  '+LOG_DIR)
        info.append('SETTINGS DIRECTORY :  '+CONFIG_DIR)
        info.append('CACHE DIRECTORY    :  '+CACHE_DIR)
        info.append('                                                                              ')
        info.append('MESSAGE_LEVEL      :  '+ (MESSAGE_LEVEL if MESSAGE_LEVEL else 'INFO(Default)') )
        info.append('                                                                              ')
        info.append('Current log file   :  '+log)

        self.Info('About DUDE','\n'.join(info),self.main,textwidth=80,width=600)

    def KeyboardShortcuts(self):
        self.Info('Keyboard Shortcuts',self.keyboardshortcuts,self.main,textwidth=80,width=600)

    def setConfVar(self,title,prompt,parent,tkvar,initialvalue,configkey,validation):
        if (res := self.DialogWithEntry(title,prompt, initialvalue=initialvalue,parent=parent)):
            if (validation(res)):
                tkvar.set(res)
                self.cfg.Set(configkey,res)
                self.cfg.Write()
            else:
                self.setConfVar(title,prompt,parent,tkvar,res,configkey,validation)

    def StoreSplitter(self):
        try:
            coords=self.paned.sash_coord(0)
            self.cfg.Set('sash_coord',str(coords[1]),section='geometry')
            self.cfg.Write()
        except Exception as e:
            logging.error(e)

    def setResultslimit(self):
        self.setConfVar("Results Quantity Limit (0 - 10000)","value:",self.ScanDialog,self.ResultsLimitVar,self.ResultsLimitVar.get(),'resultslimit',lambda x : True if str2bytes(x) and int(x)<10001 and int(x)>0 else False)

    def ClearExcludeMasks(self):
        self.cfg.Set(CFG_KEY_EXCLUDE,'')
        self.UpdateExcludeMasks()

    def ClearPaths(self):
        self.PathsToScanFromDialog.clear()
        self.UpdatePathsToScan()

    def SettingsDialogShow(self):
        self.preFocus=self.main.focus_get()

        self.SetingsDialog.grab_set()
        self.main.config(cursor="watch")

        self.SetDefaultGeometryAndShow(self.SetingsDialog,self.main)

        self.SetingsDialogDefault.focus_set()

    def SettingsDialogClose(self,event=None):
        self.SetingsDialog.grab_release()
        if self.preFocus:
            self.preFocus.focus_set()
        else:
            self.main.focus_set()

        self.main.config(cursor="")
        self.GeometryStore(self.SetingsDialog)

        self.SetingsDialog.withdraw()
        try:
            self.SetingsDialog.update()
        except Exception as e:
            pass

    def SettingsDialogOK(self):
        self.cfg.Set(CFG_KEY_STARTUP_ADD_CWD,str(self.addCwdAtStartup.get()))
        self.cfg.Set(CFG_KEY_STARTUP_SCAN,str(self.scanAtStartup.get()))

        update1=False
        update2=False

        if (self.cfg.Get(CFG_KEY_SHOW_OTHERS,False)!=self.showothers.get()):
            self.cfg.Set(CFG_KEY_SHOW_OTHERS,str(self.showothers.get()))
            update2=True

        if self.cfg.Get(CFG_KEY_FULLCRC,False)!=self.fullCRC.get():
            self.cfg.Set(CFG_KEY_FULLCRC,str(self.fullCRC.get()))
            update1=True
            update2=True

        if self.cfg.Get(CFG_KEY_FULLPATHS,False)!=self.fullPaths.get():
            self.cfg.Set(CFG_KEY_FULLPATHS,str(self.fullPaths.get()))
            update1=True
            update2=True

        if self.cfg.Get(CFG_KEY_REL_SYMLINKS,False)!=self.relSymlinks.get():
            self.cfg.Set(CFG_KEY_REL_SYMLINKS,str(self.relSymlinks.get()))

        if self.cfg.Get(CFG_KEY_USE_REG_EXPR,False)!=self.useRegExpr.get():
            self.cfg.Set(CFG_KEY_USE_REG_EXPR,str(self.useRegExpr.get()))

        self.cfg.Write()

        self.SettingsSetBools()

        if update1:
            self.Tree1CrcAndPathUpdate()

        if update2:
            if self.SelCrc and self.SelItem and self.SelFullPath:
                self.UpdatePathTree(self.SelItem)
            else:
                self.UpdatePathTreeNone()

        self.SettingsDialogClose()

    AddCwdAtStartup = False
    ScanAtStarup = False
    FullCRC = False
    ShowOthers = False
    FullPaths = False

    def SettingsSetBools(self):
        self.AddCwdAtStartup = self.cfg.Get(CFG_KEY_STARTUP_ADD_CWD,'True') == 'True'
        self.ScanAtStarup = self.cfg.Get(CFG_KEY_STARTUP_SCAN,'True') == 'True'
        self.FullCRC = self.cfg.Get(CFG_KEY_FULLCRC,False) == 'True'
        self.ShowOthers = self.cfg.Get(CFG_KEY_SHOW_OTHERS,'False') == 'True'
        self.FullPaths = self.cfg.Get(CFG_KEY_FULLPATHS,False) == 'True'

    def SettingsDialogReset(self):
        self.addCwdAtStartup.set(True)
        self.scanAtStartup.set(True)
        self.showothers.set(False)
        self.fullCRC.set(False)
        self.fullPaths.set(False)
        self.relSymlinks.set(False)
        self.useRegExpr.set(False)

    def UpdateCrcNode(self,crc):
        size=int(self.tree1.set(crc,'size'))

        if not size in self.D.filesOfSizeOfCRC:
            self.tree1.delete(crc)
            logging.debug('UpdateCrcNode-1 ' + crc)
        elif crc not in self.D.filesOfSizeOfCRC[size]:
            self.tree1.delete(crc)
            logging.debug('UpdateCrcNode-2 ' + crc)
        else:
            crcDict=self.D.filesOfSizeOfCRC[size][crc]
            for item in list(self.tree1.get_children(crc)):
                IndexTuple=self.GetIndexTupleTree1(item)

                if IndexTuple not in crcDict:
                    self.tree1.delete(item)
                    logging.debug('UpdateCrcNode-3 ' + item)

            if not self.tree1.get_children(crc):
                self.tree1.delete(crc)
                logging.debug('UpdateCrcNode-4 ' + crc)

    def ByPathCacheUpdate(self):
        self.ByPathCache = { (pathnr,path,file):(size,ctime,dev,inode,crc,self.D.crccut[crc]) for size,sizeDict in self.D.filesOfSizeOfCRC.items() for crc,crcDict in sizeDict.items() for pathnr,path,file,ctime,dev,inode in crcDict }

    def GroupsNumberUpdate(self):
        self.StatusVarGroups.set(len(self.tree1.get_children()))

    FlatItemsList=[]
    def FlatItemsListUpdate(self):
        self.FlatItemsList = [elem for sublist in [ tuple([crc])+tuple(self.tree1.get_children(crc)) for crc in self.tree1.get_children() ] for elem in sublist]

    def InitialFocus(self):
        if self.tree1.get_children():
            firstNodeFile=next(iter(self.tree1.get_children(next(iter(self.tree1.get_children())))))
            self.tree1.focus_set()
            self.tree1.focus(firstNodeFile)
            self.tree1.see(firstNodeFile)
            self.Tree1SelChange(firstNodeFile)

            self.Tree1CrcAndPathUpdate()
        else:
            self.UpdatePathTreeNone()
            self.ResetSels()

    def ShowData(self):
        self.idfunc = (lambda i,d : str(i)+'-'+str(d)) if len(self.D.devs)>1 else (lambda i,d : str(i))

        self.ResetSels()
        self.tree1.delete(*self.tree1.get_children())

        for size,sizeDict in self.D.filesOfSizeOfCRC.items() :
            for crc,crcDict in sizeDict.items():
                crcitem=self.tree1.insert(parent='', index=END,iid=crc, values=('','','',size,bytes2str(size),'','','',crc,len(crcDict),'',CRC),tags=[CRC],open=True)

                for pathnr,path,file,ctime,dev,inode in crcDict:
                    self.tree1.insert(parent=crcitem, index=END,iid=self.idfunc(inode,dev), values=(\
                            pathnr,\
                            path,\
                            file,\
                            size,\
                            '',\
                            ctime,\
                            dev,\
                            inode,\
                            crc,\
                            '',\
                            time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime)) ,FILE),tags=[])

        self.ByPathCacheUpdate()

        self.ColumnSort(self.tree1)
        self.GroupsNumberUpdate()
        self.FlatItemsListUpdate() #after sort !
        self.InitialFocus()
        self.CalcMarkStatsAll()

    def Tree1CrcAndPathUpdate(self):
        for size,sizeDict in self.D.filesOfSizeOfCRC.items() :
            for crc,crcDict in sizeDict.items():
                self.tree1.item(crc,text=crc if self.FullCRC else self.D.crccut[crc])
                for pathnr,path,file,ctime,dev,inode in crcDict:
                    self.tree1.item(self.idfunc(inode,dev),text=self.D.ScannedPaths[pathnr] if self.FullPaths else self.Numbers[pathnr])

    def UpdateMainTreeNone(self):
        self.tree1.selection_remove(self.tree1.selection())

    def UpdateMainTree(self,item):
        self.tree1.update()
        self.tree1.selection_set(item)
        self.tree1.see(item)
        self.tree1.update()

    ScandirCache={}
    StatCache={}

    def UpdatePathTreeNone(self):
        self.tree2.delete(*self.tree2.get_children())
        self.CalcMarkStatsPath()
        self.StatusVarPathSize.set('')
        self.StatusVarPathQuant.set('')
        self.SelectedSearchPath.set('')
        self.SelectedSearchPathCode.set('')

    sortIndexDict={'file':1,'sizeH':2,'ctimeH':3,'instances':8}
    kindIndex=11

    def UpdatePathTree(self,item):
        if CacheIndex:=(self.SelPathnr,self.SelPath) not in self.ScandirCache:
            try:
                self.ScandirCache[CacheIndex]=list(os.scandir(self.SelFullPath))
            except Exception as e:
                logging.error('ERROR:{e}')
                return

        itemsToInsert=[]
        i=0
        for DirEntry in self.ScandirCache[CacheIndex]:
            file=DirEntry.name
            if (self.SelPathnrInt,self.SelPath,file) in self.ByPathCache:
                size,ctime,dev,inode,crc,crccut = self.ByPathCache[(self.SelPathnrInt,self.SelPath,file)]

                itemsToInsert.append( tuple([ crc if self.FullCRC else crccut, \
                                            file\
                                            ,size\
                                            ,ctime\
                                            ,dev\
                                            ,inode\
                                            ,crc\
                                            ,instances:=len(self.D.filesOfSizeOfCRC[size][crc])\
                                            ,instances,FILEID:=self.idfunc(inode,dev),\
                                            self.tree1.item(FILEID)['tags'],\
                                            FILE,\
                                            FILEID,\
                                            bytes2str(size) ]) )

            elif self.ShowOthers:
                istr=str(i)
                if os.path.islink(DirEntry) :
                    itemsToInsert.append( ( '➝',file,size,0,0,0,'','',1,0,LINK,LINK,istr+'L','' ) )
                    i+=1
                elif DirEntry.is_dir():
                    itemsToInsert.append( ('[  ]',file,0,0,0,0,'','',1,0,DIR,DIR,istr+'L','' ) )
                    i+=1
                elif DirEntry.is_file():
                    if (FullFilePath:=os.path.join(self.SelFullPath,file)) in self.StatCache:
                        ctime,dev,inode,size,FILEID = self.StatCache[FullFilePath]
                    else:
                        try:
                            stat = os.stat(FullFilePath)
                        except Exception as e:
                            logging.error(f'ERROR: ,{e}')
                            continue
                        self.StatCache[FullFilePath] = tuple([ ctime:=round(stat.st_ctime) , dev:=stat.st_dev , inode:=stat.st_ino , size:=stat.st_size , FILEID:=self.idfunc(inode,dev) ])

                    itemsToInsert.append( ( '',file,size,ctime,dev,inode,'','',1,FILEID,SINGLE,SINGLE,istr+'O',bytes2str(size) ) )
                    i+=1
                else:
                    logging.error(f'what is it: {DirEntry} ?')

        colSort,reverse = self.ColumnSortLastParams[self.tree2]

        sortIndex=self.sortIndexDict[colSort]

        IsNumeric=self.col2sortNumeric[colSort]
        DIR0,DIR1 = (1,0) if reverse else (0,1)

        self.tree2.delete(*self.tree2.get_children())
        for (text,file,size,ctime,dev,inode,crc,instances,instancesnum,FILEID,tags,kind,iid,sizeH) in sorted(itemsToInsert,key=lambda x : (DIR0 if x[self.kindIndex]==DIR else DIR1,float(x[sortIndex])) if IsNumeric else (DIR0 if x[self.kindIndex]==DIR else DIR1,x[sortIndex]),reverse=reverse):
            self.tree2.insert(parent="", index=END, iid=iid , text=text, values=(self.SelPathnrInt,self.SelPath,file,size,sizeH,ctime,dev,inode,crc,instances,instancesnum,time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime)) if crc or kind==SINGLE else '',kind),tags=tags)

        self.tree2.update()

        if item in self.tree2.get_children():
            self.tree2.selection_set(item)
            self.tree2.see(item)
            self.CalcMarkStatsPath()
            self.tree2.update()

    def PathTreeUpdateMarks(self):
        for item in self.tree2.get_children():
            if self.tree2.set(item,'kind')==FILE:
                self.tree2.item( item,tags=self.tree1.item(item)['tags'] )

    def CalcMarkStatsAll(self):
        self.CalcMarkStatsCore(self.tree1,self.StatusVarAllSize,self.StatusVarAllQuant)
        self.SetCommonVarFg()

    def CalcMarkStatsPath(self):
        self.CalcMarkStatsCore(self.tree2,self.StatusVarPathSize,self.StatusVarPathQuant)

    def CalcMarkStatsCore(self,tree,varSize,varQuant):
        marked=tree.tag_has(MARK)
        varQuant.set(len(marked))
        varSize.set(bytes2str(sum(int(tree.set(item,'size')) for item in marked)))

    def MarkInSpecifiedCRCGroupByCTime(self, action, crc, reverse,select=False):
        item=sorted([ (item,self.tree1.set(item,'ctime') ) for item in self.tree1.get_children(crc)],key=lambda x : float(x[1]),reverse=reverse)[0][0]
        action(item,self.tree1)
        if select:
            self.tree1.see(item)
            self.tree1.focus(item)
            self.Tree1SelChange(item)
            self.tree1.update()

    @WatchCursor
    def MarkOnAllByCTime(self,orderStr, action):
        reverse=1 if orderStr=='oldest' else 0

        { self.MarkInSpecifiedCRCGroupByCTime(action, crc, reverse) for crc in self.tree1.get_children() }
        self.PathTreeUpdateMarks()
        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    @WatchCursor
    def MarkInCRCGroupByCTime(self,orderStr,action):
        reverse=1 if orderStr=='oldest' else 0
        self.MarkInSpecifiedCRCGroupByCTime(action,self.SelCrc,reverse,True)
        self.PathTreeUpdateMarks()
        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    def MarkInSpecifiedCRCGroup(self,action,crc):
        { action(item,self.tree1) for item in self.tree1.get_children(crc) }

    @WatchCursor
    def MarkInCRCGroup(self,action):
        self.MarkInSpecifiedCRCGroup(action,self.SelCrc)
        self.PathTreeUpdateMarks()
        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    @WatchCursor
    def MarkOnAll(self,action):
        { self.MarkInSpecifiedCRCGroup(action,crc) for crc in self.tree1.get_children() }
        self.PathTreeUpdateMarks()
        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    @WatchCursor
    def MarkLowerPane(self,action):
        { (action(item,self.tree2),action(item,self.tree1)) for item in self.tree2.get_children() if self.tree2.set(item,'kind')==FILE }

        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    def MarkPathOfFile(self,action):
        if self.SelSearchPath and self.SelPath:
            self.ActionOnSpecifiedPath(self.SelSearchPath+self.SelPath,action)

    def SetMark(self,item,tree):
        tree.item(item,tags=[MARK])

    def UnsetMark(self,item,tree):
        tree.item(item,tags=[])

    def InvertMark(self,item,tree):
        tree.item(item,tags=[] if tree.item(item)['tags'] else [MARK])

    @WatchCursor
    def ActionOnSpecifiedPath(self,pathParam,action):
        selCount=0
        for crcitem in self.tree1.get_children():
            for item in self.tree1.get_children(crcitem):
                fullpath = self.FullPath1(item)

                if fullpath.startswith(pathParam + os.sep):
                    action(item,self.tree1)
                    selCount+=1

        if selCount==0 :
            self.DialogWithEntry(title='No files found for specified path', prompt=pathParam,parent=self.main,OnlyInfo=True)
        else:
            self.PathTreeUpdateMarks()
            self.CalcMarkStatsAll()
            self.CalcMarkStatsPath()

    regexp={'file':'.','path':'.','both':'.'}
    regexpDesc={'file':'file','path':'subpath','both':'entire file path'}

    def MarkExpression(self,field,action,ActionLabel):
        tree=self.main.focus_get()

        if self.regexp[field]:
            initialvalue=self.regexp[field]
        else:
            initialvalue='.*'

        UseRegExpr = True if self.cfg.Get(CFG_KEY_USE_REG_EXPR,False)=='True' else False

        desc=self.regexpDesc[field]

        prompt=ActionLabel + (' (regular expression syntax)' if UseRegExpr else ' (symplified syntax)')

        if (regexp := self.DialogWithEntry(title=f'Specify Expression for {desc}.',prompt=prompt, initialvalue=initialvalue,parent=self.main)):
            self.regexp[field]=regexp
            selCount=0
            if field=='file':
                for crcitem in self.tree1.get_children():
                    for item in self.tree1.get_children(crcitem):
                        file=self.tree1.set(item,'file')
                        try:
                            if (UseRegExpr and re.search(regexp,file)) or (not UseRegExpr and fnmatch.fnmatch(file,regexp) ):
                                action(item,self.tree1)
                                selCount+=1
                        except Exception as e:
                            self.DialogWithEntry(title='Expression Error !',prompt='                                                                \n' + str(e),parent=self.main,OnlyInfo=True)
                            tree.focus_set()
                            return
            elif field=='path':
                for crcitem in self.tree1.get_children():
                    for item in self.tree1.get_children(crcitem):
                        path=self.tree1.set(item,'path')
                        try:
                            if (UseRegExpr and re.search(regexp,path)) or (not UseRegExpr and fnmatch.fnmatch(path,regexp) ):
                                action(item,self.tree1)
                                selCount+=1
                        except Exception as e:
                            self.DialogWithEntry(title='Expression Error !',prompt='                                                                \n' + str(e),parent=self.main,OnlyInfo=True)
                            tree.focus_set()
                            return
            else:
                for crcitem in self.tree1.get_children():
                    for item in self.tree1.get_children(crcitem):
                        fullpath = self.FullPath1(item)
                        try:
                            if (UseRegExpr and re.search(regexp,fullpath)) or (not UseRegExpr and fnmatch.fnmatch(fullpath,regexp) ):
                                action(item,self.tree1)
                                selCount+=1
                        except Exception as e:
                            self.DialogWithEntry(title='Expression Error !',prompt='                                                                \n' + str(e),parent=self.main,OnlyInfo=True)
                            tree.focus_set()
                            return


            if selCount==0 :
                self.DialogWithEntry(title='No files found.',prompt='                                                     \n'+regexp,parent=self.main,OnlyInfo=True)
            else:
                self.PathTreeUpdateMarks()
                self.CalcMarkStatsAll()
                self.CalcMarkStatsPath()

        tree.focus_set()

    def MarkSubpath(self,action):
        if path:=tk.filedialog.askdirectory(title='Select Directory',initialdir=self.cwd):
            self.ActionOnSpecifiedPath(path,action)

    def GotoNextMark(self,tree,direction):
        marked=tree.tag_has(MARK)
        if marked:
            item=self.SelItem

            pool=marked if tree.tag_has(MARK,item) else self.FlatItemsList if tree==self.tree1 else self.tree2.get_children()
            poollen=len(pool)

            index = pool.index(item)

            while True:
                index=(index+direction)%poollen
                NextItem=pool[index]
                if MARK in tree.item(NextItem)['tags']:
                    tree.focus(NextItem)
                    tree.see(NextItem)

                    if tree==self.tree1:
                        self.Tree1SelChange(NextItem)
                    else:
                        self.Tree2SelChange(NextItem)

                    break

    def GoToMaxGroup(self,sizeFlag=0):
        biggestsizesum=0
        biggestcrc=None
        for crcitem in self.tree1.get_children():
            sizesum=sum([(int(self.tree1.set(item,'size')) if sizeFlag else 1) for item in self.tree1.get_children(crcitem)])
            if sizesum>biggestsizesum:
                biggestsizesum=sizesum
                biggestcrc=crcitem

        if biggestcrc:
            self.SelectFocusAndSeeCrcItemTree(biggestcrc)

    def GoToMaxFolder(self,sizeFlag=0):
        PathStat={}
        Biggest={}
        FileidOfBiggest={}

        for size,sizeDict in self.D.filesOfSizeOfCRC.items() :
            for crc,crcDict in sizeDict.items():
                for pathnr,path,file,ctime,dev,inode in crcDict:
                    pathindex=(pathnr,path)
                    PathStat[pathindex] = PathStat.get(pathindex,0) + (size if sizeFlag else 1)
                    if size>Biggest.get(pathindex,0):
                        Biggest[pathindex]=size
                        FileidOfBiggest[pathindex]=self.idfunc(inode,dev)

        if PathStat:
            PathStatList=[(pathnr,path,number) for (pathnr,path),number in PathStat.items()]
            PathStatList.sort(key=lambda x : x[2],reverse=True)

            [pathnr,path,num] = PathStatList[0]

            item=FileidOfBiggest[(pathnr,path)]

            self.tree1.focus(item)
            self.tree1.see(item)
            self.Tree1SelChange(item)
            self.tree1.update()

            self.UpdatePathTree(item)

            self.tree2.focus_set()
            self.tree2.focus(item)
            self.tree2.see(item)

            self.UpdateMainTree(item)

    def FullPath1(self,item):
        return self.GetFullPath(item,self.tree1)

    def FullPath2(self,item):
        return self.GetFullPath(item,self.tree2)

    def GetFullPath(self,item,tree):
        pathnr=int(tree.set(item,'pathnr'))
        path=tree.set(item,'path')
        file=tree.set(item,'file')
        return os.path.abspath(self.D.ScannedPathFull(pathnr,path,file))

    def CheckFileState(self,item):
        fullpath = self.FullPath1(item)
        logging.info(f'checking file:{fullpath}')
        try:
            stat = os.stat(fullpath)
            ctimeCheck=str(round(stat.st_ctime))
        except Exception as e:
            mesage = f'cant check file: {fullpath}:{e}'
            logging.error(mesage)
            return mesage

        if ctimeCheck != (ctime:=self.tree1.set(item,'ctime')) :
            message = {f'ctime inconsistency {ctimeCheck} vs {ctime}'}
            return message

    def ProcessFiles(self,action,all=0):
        tree=self.main.focus_get()
        if not tree:
            return

        ProcessedItems=defaultdict(list)

        ShowFullPath=1

        if all:
            ScopeTitle='All Marked Files.'
            for crc in self.tree1.get_children():
                if tempList:=[item for item in self.tree1.get_children(crc) if self.tree1.tag_has(MARK,item)]:
                    ProcessedItems[crc]=tempList
        else:
            if tree==self.tree1:
                #tylko na gornym drzewie, na dolnym moze byc inny plik
                crc=self.SelCrc

                if not crc:
                    return
                ScopeTitle='Single CRC group.'
                if templist:= [item for item in tree.get_children(crc) if tree.tag_has(MARK,item)]:
                    ProcessedItems[crc] = templist

            else:
                #jezeli dzialamy na katalogu pozostale markniecia w crc nie sa uwzglednione
                #ale w katalogu moze byc >1 tego samego crc
                ScopeTitle='Selected Directory: ' + self.SelFullPath
                for item in tree.get_children():
                    if tree.tag_has(MARK,item):
                        crc=tree.set(item,'crc')
                        ProcessedItems[crc].append(item)

        if not ProcessedItems:
            self.DialogWithEntry(title='No Files Marked For Processing !',prompt='Scope: ' + ScopeTitle + '\n\nMark files first.',parent=self.main,OnlyInfo=True,width=600,height=200)
            return

        logging.info(f'ProcessFiles:{action},{all}')
        logging.info('Scope ' + ScopeTitle)

        #############################################
        #check remainings

        #RemainingItems dla wszystkich (moze byc akcja z folderu)
        #istotna kolejnosc
        RemainingItems={}
        for crc in self.tree1.get_children():
            RemainingItems[crc]=[item for item in self.tree1.get_children(crc) if not self.tree1.tag_has(MARK,item)]

        if action=="hardlink":
            for crc in ProcessedItems:
                if len(ProcessedItems[crc])==1:
                    self.DialogWithEntry(title='Error - Cant hardlink single file.',prompt="                    Mark more files.                    ",parent=self.main,OnlyInfo=True)

                    self.SelectFocusAndSeeCrcItemTree(crc)
                    return

        elif action in ("delete","softlink"):
            for crc in ProcessedItems:
                if len(RemainingItems[crc])==0:
                    self.DialogWithEntry(title=f'        Error {action} - All files marked        ',prompt="  Keep at least one file unmarked.  ",parent=self.main,OnlyInfo=True)

                    self.SelectFocusAndSeeCrcItemTree(crc)
                    return

        logging.warning('###########################################################################################')
        logging.warning(f'action:{action}')

        message=[]
        for crc in ProcessedItems:
            message.append('')
            size=int(self.tree1.set(crc,'size'))
            message.append('CRC:' + crc + ' size:' + bytes2str(size) + '|GRAY')
            for item in ProcessedItems[crc]:
                message.append((self.FullPath1(item) if ShowFullPath else tree.set(item,'file')) + '|RED' )

            if action=='softlink':
                if RemainingItems[crc]:
                    item = RemainingItems[crc][0]
                    message.append('➝ ' + (self.FullPath1(item) if ShowFullPath else self.tree1.set(item,'file')) )

        if action=='delete':
            if not self.Ask('Delete marked files ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return
        elif action=='softlink':
            if not self.Ask('Soft-Link marked files to first unmarked file in group ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return
        elif action=='hardlink':
            if not self.Ask('Hard-Link marked files together in groups ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return

        {logging.warning(line) for line in message}
        logging.warning('###########################################################################################')
        logging.warning('Confirmed.')

        #############################################
        for crc in ProcessedItems:
            for item in RemainingItems[crc]:
                if res:=self.CheckFileState(item):
                    self.Info(res)
                    logging.error('aborting.')
                    return
        logging.info('remaining files checking complete.')
        #############################################
        if action=='hardlink':
            for crc in ProcessedItems:
                if len({int(self.tree1.set(item,'dev')) for item in ProcessedItems[crc]})>1:
                    message1='Can\'t create hardlinks.'
                    message2=f"Files on multiple devices selected. Crc:{crc}"
                    logging.error(message1)
                    logging.error(message2)
                    self.DialogWithEntry(title=message1,prompt=message2,parent=self.main,OnlyInfo=True)
                    return

        #####################################
        #action

        if action=='delete':
            for crc in ProcessedItems:
                for item in ProcessedItems[crc]:
                    size=int(self.tree1.set(item,'size'))
                    IndexTuple=self.GetIndexTupleTree1(item)

                    if resmsg:=self.D.DeleteFileWrapper(size,crc,IndexTuple):
                        logging.error(resmsg)
                        self.Info('Error',resmsg,self.main)
                        break
                self.UpdateCrcNode(crc)

        if action=='softlink':
            RelSymlink = True if self.cfg.Get(CFG_KEY_REL_SYMLINKS,False)=='True' else False
            for crc in ProcessedItems:

                toKeepItem=list(RemainingItems[crc])[0]
                #self.tree1.focus()
                IndexTupleRef=self.GetIndexTupleTree1(toKeepItem)
                size=int(self.tree1.set(toKeepItem,'size'))

                if resmsg:=self.D.LinkWrapper(True, RelSymlink, size,crc, IndexTupleRef, [self.GetIndexTupleTree1(item) for item in ProcessedItems[crc] ] ):
                    logging.error(resmsg)
                    self.Info('Error',resmsg,self.main)

                self.UpdateCrcNode(crc)

        if action=='hardlink':
            for crc in ProcessedItems:

                refItem=ProcessedItems[crc][0]
                IndexTupleRef=self.GetIndexTupleTree1(refItem)
                size=int(self.tree1.set(refItem,'size'))

                if resmsg:=self.D.LinkWrapper(False, False, size,crc, IndexTupleRef, [self.GetIndexTupleTree1(item) for item in ProcessedItems[crc][1:] ] ):
                    logging.error(resmsg)
                    self.Info('Error',resmsg,self.main)

                self.UpdateCrcNode(crc)

        self.ScandirCache={}
        self.StatCache={}

        self.ByPathCacheUpdate()
        self.GroupsNumberUpdate()
        self.FlatItemsListUpdate()
        self.InitialFocus()
        self.CalcMarkStatsAll()

    def CleanCache(self):
        try:
            shutil.rmtree(CACHE_DIR)
        except Exception as e:
            logging.error(e)

    def ClipCopy(self):
        if self.SelFullPath and self.SelFile:
            pyperclip.copy(os.sep.join([self.SelFullPath,self.SelFile]))
        elif self.SelCrc:
            pyperclip.copy(self.SelCrc)

    def OpenFolder(self):
        if self.SelFullPath:
            if windows:
                os.startfile(self.SelFullPath)
            else:
                os.system("xdg-open " + '"' + self.SelFullPath + '"')

    def TreeEventOpenFileEvent(self,event):
        tree=event.widget
        if tree.identify("region", event.x, event.y) != 'heading':
            self.TreeEventOpenFile()
            
    def TreeEventOpenFile(self):
        if self.SelKind==FILE or self.SelKind==LINK or self.SelKind==SINGLE:
            if windows:
                os.startfile(os.sep.join([self.SelFullPath,self.SelFile]))
            else:
                os.system("xdg-open "+ '"' + os.sep.join([self.SelFullPath,self.SelFile]) + '"')
        elif self.SelKind==DIR:
            self.OpenFolder()

    def SetCommonVar(self,val=None):
        self.StatusVarFullPath.set(os.sep.join([self.SelSearchPath+self.SelPath,self.SelFile]))
        self.SetCommonVarFg()

    def SetCommonVarFg(self):
        if self.SelItem:
            self.StatusVarFullPathLabel.config(fg = 'red' if self.SelItem and (self.tree1,self.tree2)[self.SelTreeIndex].tag_has(MARK,self.SelItem) else 'black')

LoggingLevels={'DEBUG':logging.DEBUG,'INFO':logging.INFO,'WARNING':logging.WARNING,'ERROR':logging.ERROR,'CRITICAL':logging.CRITICAL}

if __name__ == "__main__":
    pathlib.Path(LOG_DIR).mkdir(parents=True,exist_ok=True)
    log=LOG_DIR + os.sep + time.strftime('%Y_%m_%d_%H_%M_%S',time.localtime(time.time()) ) +'.log'

    MESSAGE_LEVEL = os.environ.get('MESSAGE_LEVEL')

    logginLevel = LoggingLevels[MESSAGE_LEVEL] if MESSAGE_LEVEL in LoggingLevels else logging.INFO

    print('log:',log)
    logging.basicConfig(level=logginLevel,format='%(asctime)s %(levelname)s %(message)s', filename=log,filemode='w')

    try:
        Gui(os.getcwd())
    except Exception as e:
        print(e)
        logging.error(e)
