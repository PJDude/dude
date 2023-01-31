#!/usr/bin/python3.11

VERSION='0.96'

import fnmatch
import shutil
import os
import os.path
import pathlib
import re

import time
import configparser
import logging
import traceback
import argparse

import tkinter as tk
from tkinter import *
from tkinter import ttk
#from tkinter import font
from tkinter import scrolledtext
from tkinter.filedialog import askdirectory

from collections import defaultdict
from threading import Thread
from sys import exit
from sys import argv

import core

try:
    from appdirs import *
    CACHE_DIR = os.sep.join([user_cache_dir('dude','PJDude'),"cache"])
    LOG_DIR = user_log_dir('dude','PJDude')
    CONFIG_DIR = user_config_dir('dude')
except Exception as e:
    print(e)
    CONFIG_DIR=LOG_DIR=CACHE_DIR = os.sep.join([os.getcwd(),"dude-no-appdirs"])

windows = (os.name=='nt')

def EPrint(e):
    stack = traceback.extract_stack()[:-3] + traceback.extract_tb(e.__traceback__)
    pretty = traceback.format_list(stack)
    return ''.join(pretty) + '\n  {} {}'.format(e.__class__,e)

###########################################################################################################################################

CFG_KEY_STARTUP_ADD_CWD='add_cwd_at_startup'
CFG_KEY_STARTUP_SCAN='scan_at_startup'
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

CFG_KEY_GEOMETRY='geometry'
CFG_KEY_GEOMETRY_DIALOG='geometry_dialog'

CFG_KEY_EXCLUDE='exclude'

CfgDefaults={
    CFG_KEY_STARTUP_ADD_CWD:False,
    CFG_KEY_STARTUP_SCAN:False,
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

    def SetBool(self,key,val,section='main'):
        self.config.set(section,key,('0','1')[val])

    def Get(self,key,default=None,section='main'):
        try:
            res=self.config.get(section,key)
        except Exception as e:
            logging.warning(f'gettting config key {key}')
            logging.warning(e)
            res=default
            self.Set(key,str(default),section=section)

        return str(res).replace('[','').replace(']','').replace('"','').replace("'",'').replace(',','').replace(' ','')

    def GetBool(self,key,section='main'):
        try:
            res=self.config.get(section,key)
            return res=='1'

        except Exception as e:
            logging.warning(f'gettting config key {key}')
            logging.warning(e)
            res=CfgDefaults[key]
            self.SetBool(key,res,section=section)
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

    SelItemTree = {}

    SelFullPath={}
    FolderItemsCache={}
    FolderScandirCache={}

    def MainWatchCursor(f):
        def MainWatchCursorWrapp(self,*args,**kwargs):
            prevCursor=self.main.cget('cursor')
            self.main.config(cursor="watch")
            self.main.update()

            try:
                res=f(self,*args,**kwargs)
            except Exception as e:
                self.StatusLine.set(str(e))
                res=None
                print(EPrint(e))

            self.main.config(cursor=prevCursor)
            return res
        return MainWatchCursorWrapp

    def StatusLineRestore(f):
        def StatusLineRestoreWrapp(self,*args,**kwargs):
            prev=self.StatusLine.get()
            try:
                res=f(self,*args,**kwargs)
            except Exception as e:
                self.StatusLine.set(str(e))
                res=None
                print(EPrint(e))

            self.StatusLine.set(prev)
            return res
        return StatusLineRestoreWrapp

    def KeepSemiFocus(f):
        def KeepSemiFocusWrapp(self,*args,**kwargs):

            tree=self.main.focus_get()

            try:
                tree.configure(style='semi_focus.Treeview')
            except:
                pass

            try:
                res=f(self,*args,**kwargs)
            except Exception as e:
                self.StatusLine.set(str(e))
                res=None
                print(EPrint(e))

            try:
                tree.configure(style='default.Treeview')
            except:
                pass

            return res
        return KeepSemiFocusWrapp

    #######################################################################
    LongActionAbort=False
    def LongActionDialogShow(self,parent,title,ProgressMode1=None,ProgressMode2=None,Progress1LeftText=None,Progress2LeftText=None):
        self.LADParent=parent

        self.psIndex =0

        self.ProgressMode1=ProgressMode1
        self.ProgressMode2=ProgressMode2

        self.LongActionDialog = tk.Toplevel(parent)
        self.LongActionDialog.wm_transient(parent)

        self.LongActionDialog.protocol("WM_DELETE_WINDOW", self.LongActionDialogAbort)
        self.LongActionDialog.bind('<Escape>', self.LongActionDialogAbort)

        self.LongActionDialog.wm_title(title)
        self.LongActionDialog.iconphoto(False, self.iconphoto)

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

        try:
            self.LongActionDialog.update()
            self.LongActionDialog.grab_set()
            self.LongActionDialog.geometry(CenterToParentGeometry(self.LongActionDialog,parent))
        finally:
            pass

        self.prevParentCursor=parent.cget('cursor')
        parent.config(cursor="watch")

        self.LongActionAbort=False

    def LongActionDialogAbort(self,event=None):
        self.LongActionAbort=True

    def LongActionDialogEnd(self):
        self.LongActionDialog.grab_release()
        self.LongActionDialog.destroy()
        self.LADParent.config(cursor=self.prevParentCursor)

    LADPrevMessage=''
    LADPrevProg1=''
    LADPrevProg2=''
    LastTimeNoSign=0

    def LongActionDialogUpdate(self,message,progress1=None,progress2=None,progress1Right=None,progress2Right=None,StatusInfo=None):
        prefix=''

        if StatusInfo:
            self.StatusLine.set(StatusInfo)
        else:
            self.StatusLine.set('')

        if self.LADPrevProg1==progress1Right and self.LADPrevProg2==progress2Right and self.LADPrevMessage==message:
            if time.time()>self.LastTimeNoSign+1.0:
                prefix=self.ProgressSigns[self.psIndex]
                self.psIndex=(self.psIndex+1)%4


        else:

            self.LADPrevMessage=message
            self.LADPrevProg1=progress1Right
            self.LADPrevProg2=progress2Right

            self.LastTimeNoSign=time.time()

            self.Progress1Func(progress1)
            self.progr1LabRight.config(text=progress1Right)
            self.progr2var.set(progress2)
            self.progr2LabRight.config(text=progress2Right)

        self.message.set('%s\n%s'%(prefix,message))
        self.LongActionDialog.update()

    def __init__(self,cwd,pathsToAdd=None,exclude=None,excluderegexp=None,norun=None):
        self.D = core.DudeCore(CACHE_DIR,logging)
        self.cwd=cwd

        self.cfg = Config(CONFIG_DIR)
        self.cfg.Read()

        self.PathsToScanFrames=[]
        self.ExcludeFrames=[]

        self.PathsToScanFromDialog=[]

        ####################################################################
        self.main = tk.Tk()
        self.main.title(f'Dude (DUplicates DEtector) v{VERSION}')
        self.main.protocol("WM_DELETE_WINDOW", self.exit)
        self.main.minsize(1200, 800)
        self.main.bind('<FocusIn>', self.FocusIn)

        self.iconphoto = PhotoImage(file = os.path.join(os.path.dirname(__file__),'icon.png'))
        self.main.iconphoto(False, self.iconphoto)

        self.main.bind('<KeyPress-F2>', lambda event : self.SettingsDialogShow())
        self.main.bind('<KeyPress-F1>', lambda event : self.About())
        self.main.bind('<KeyPress-s>', lambda event : self.ScanDialogShow())
        self.main.bind('<KeyPress-S>', lambda event : self.ScanDialogShow())

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

        self.StatusVarAllSize=tk.StringVar()
        self.StatusVarAllQuant=tk.StringVar()
        self.StatusVarGroups=tk.StringVar()
        self.StatusVarFullPath=tk.StringVar()
        self.StatusVarPathSize=tk.StringVar()
        self.StatusVarPathQuant=tk.StringVar()

        self.paned = PanedWindow(self.main,orient=tk.VERTICAL,relief='sunken',showhandle=0,bd=0,bg=self.bg,sashwidth=2,sashrelief='flat')
        self.paned.pack(fill='both',expand=1)

        FrameTop = tk.Frame(self.paned,bg=self.bg)
        self.paned.add(FrameTop)
        FrameBottom = tk.Frame(self.paned,bg=self.bg)
        self.paned.add(FrameBottom)

        FrameTop.grid_columnconfigure(0, weight=1)
        FrameTop.grid_rowconfigure(0, weight=1,minsize=200)

        FrameBottom.grid_columnconfigure(0, weight=1)
        FrameBottom.grid_rowconfigure(0, weight=1,minsize=200)

        self.paned.update()
        self.paned.sash_place(0,0,self.cfg.Get('sash_coord',400,section='geometry'))

        (UpperStatusFrame := tk.Frame(FrameTop,bg=self.bg)).pack(side='bottom', fill='both')
        self.StatusVarGroups.set('0')
        self.StatusVarFullPath.set('')

        tk.Label(UpperStatusFrame,width=10,textvariable=self.StatusVarAllQuant,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=16,text="All marked files # ",relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=10,textvariable=self.StatusVarAllSize,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=18,text='All marked files size: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=10,textvariable=self.StatusVarGroups,borderwidth=2,bg=self.bg,relief='groove',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=10,text='Groups: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(UpperStatusFrame,width=8,text='Full path: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='left')
        self.StatusVarFullPathLabel = tk.Label(UpperStatusFrame,textvariable=self.StatusVarFullPath,relief='flat',borderwidth=2,bg=self.bg,anchor='w')
        self.StatusVarFullPathLabel.pack(fill='x',expand=1,side='left')

        (LowerStatusFrame := tk.Frame(FrameBottom,bg=self.bg)).pack(side='bottom',fill='both')

        self.StatusLine=tk.StringVar()
        self.StatusLine.set('')

        tk.Label(LowerStatusFrame,width=30,textvariable=self.StatusLine,borderwidth=2,bg=self.bg,relief='groove',anchor='w').pack(fill='x',expand=1,side='left')

        tk.Label(LowerStatusFrame,width=10,textvariable=self.StatusVarPathQuant,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(fill='x',expand=0,side='right')
        tk.Label(LowerStatusFrame,width=16,text='Marked files # ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')
        tk.Label(LowerStatusFrame,width=10,textvariable=self.StatusVarPathSize,borderwidth=2,bg=self.bg,relief='groove',foreground='red',anchor='w').pack(expand=0,side='right')
        tk.Label(LowerStatusFrame,width=18,text='Marked files size: ',relief='groove',borderwidth=2,bg=self.bg,anchor='e').pack(fill='x',expand=0,side='right')

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

        self.main.bind_class('Treeview','<KeyPress>', self.KeyPressTreeCommon )
        #self.main.bind_class('Treeview','<KeyRelease>', self.KeyReleaseTreeCommon )

        self.main.bind_class('Treeview','<FocusIn>',    self.TreeEventFocusIn )
        self.main.bind_class('Treeview','<FocusOut>',   self.TreeFocusOut )

        self.main.bind_class('Treeview','<ButtonPress-3>', self.TreeContexMenu)

        self.TreeGroups=ttk.Treeview(FrameTop,takefocus=True,selectmode='none',show=('tree','headings') )

        self.OrgLabel={}
        self.OrgLabel['path']='Subpath'
        self.OrgLabel['file']='File'
        self.OrgLabel['sizeH']='Size'
        self.OrgLabel['instances']='Copies'
        self.OrgLabel['ctimeH']='Change Time'

        self.TreeGroups["columns"]=('pathnr','path','file','size','sizeH','ctime','dev','inode','crc','instances','ctimeH','kind')

        #pathnr,path,file,ctime,dev,inode
        self.IndexTupleIndexesWithFnCommon=((int,0),(raw,1),(raw,2),(int,5),(int,6),(int,7))

        self.TreeGroups["displaycolumns"]=('path','file','sizeH','instances','ctimeH')

        self.TreeGroups.column('#0', width=120, minwidth=100, stretch=tk.NO)
        self.TreeGroups.column('path', width=100, minwidth=10, stretch=tk.YES )
        self.TreeGroups.column('file', width=100, minwidth=10, stretch=tk.YES )
        self.TreeGroups.column('sizeH', width=80, minwidth=80, stretch=tk.NO)
        self.TreeGroups.column('instances', width=80, minwidth=80, stretch=tk.NO)
        self.TreeGroups.column('ctimeH', width=150, minwidth=100, stretch=tk.NO)

        self.TreeGroups.heading('#0',text='CRC / Scan Path',anchor=tk.W)
        self.TreeGroups.heading('path',anchor=tk.W )
        self.TreeGroups.heading('file',anchor=tk.W )
        self.TreeGroups.heading('sizeH',anchor=tk.W)
        self.TreeGroups.heading('ctimeH',anchor=tk.W)
        self.TreeGroups.heading('instances',anchor=tk.W)

        self.TreeGroups.heading('sizeH', text='Size \u25BC')

        #bind_class breaks columns resizing
        self.TreeGroups.bind('<ButtonPress-1>', self.TreeButtonPress)
        self.TreeGroups.bind('<Control-ButtonPress-1>',  lambda event :self.TreeButtonPress(event,True) )
        self.TreeGroups.bind('<<TreeviewClose>>',  self.TreeClose )

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

        vsb1 = tk.Scrollbar(FrameTop, orient='vertical', command=self.TreeGroups.yview,takefocus=False,bg=self.bg)
        self.TreeGroups.configure(yscrollcommand=vsb1.set)

        vsb1.pack(side='right',fill='y',expand=0)
        self.TreeGroups.pack(fill='both',expand=1, side='left')

        self.TreeGroups.bind('<Double-Button-1>',        self.TreeEventDoubleLeft)

        self.TreeFolder=ttk.Treeview(FrameBottom,takefocus=True,selectmode='none')

        self.TreeFolder['columns']=('pathnr','path','file','size','sizeH','ctime','dev','inode','crc','instances','instancesnum','ctimeH','kind')

        self.TreeFolder['displaycolumns']=('file','sizeH','instances','ctimeH')

        self.TreeFolder.column('#0', width=120, minwidth=100, stretch=tk.NO)

        self.TreeFolder.column('file', width=200, minwidth=100, stretch=tk.YES)
        self.TreeFolder.column('sizeH', width=80, minwidth=80, stretch=tk.NO)
        self.TreeFolder.column('instances', width=80, minwidth=80, stretch=tk.NO)
        self.TreeFolder.column('ctimeH', width=150, minwidth=100, stretch=tk.NO)

        self.TreeFolder.heading('#0',text='CRC',anchor=tk.W)
        self.TreeFolder.heading('path',anchor=tk.W)
        self.TreeFolder.heading('file',anchor=tk.W)
        self.TreeFolder.heading('sizeH',anchor=tk.W)
        self.TreeFolder.heading('ctimeH',anchor=tk.W)
        self.TreeFolder.heading('instances',anchor=tk.W)

        for tree in [self.TreeGroups,self.TreeFolder]:
            for col in tree["displaycolumns"]:
                if col in self.OrgLabel:
                    tree.heading(col,text=self.OrgLabel[col])

        self.TreeFolder.heading('file', text='File \u25B2')

        vsb2 = tk.Scrollbar(FrameBottom, orient='vertical', command=self.TreeFolder.yview,takefocus=False,bg=self.bg)
        self.TreeFolder.configure(yscrollcommand=vsb2.set)

        vsb2.pack(side='right',fill='y',expand=0)
        self.TreeFolder.pack(fill='both',expand=1,side='left')

        self.TreeFolder.bind('<Double-Button-1>',        self.TreeEventDoubleLeft)

        self.TreeGroups.tag_configure(MARK, foreground='red')
        self.TreeGroups.tag_configure(MARK, background='red')
        self.TreeFolder.tag_configure(MARK, foreground='red')
        self.TreeFolder.tag_configure(MARK, background='red')

        self.TreeGroups.tag_configure(CRC, foreground='gray')

        self.TreeFolder.tag_configure(SINGLE, foreground='gray')
        self.TreeFolder.tag_configure(DIR, foreground='blue2')
        self.TreeFolder.tag_configure(LINK, foreground='darkgray')

        #bind_class breaks columns resizing
        self.TreeFolder.bind('<ButtonPress-1>', self.TreeButtonPress)
        self.TreeFolder.bind('<Control-ButtonPress-1>',  lambda event :self.TreeButtonPress(event,True) )

        self.SetDefaultGeometryAndShow(self.main,None)

        self.PopupGroups = Menu(self.TreeGroups, tearoff=0,bg=self.bg)
        self.PopupGroups.bind("<FocusOut>",lambda event : self.PopupGroups.unpost() )

        self.PopupFolder = Menu(self.TreeFolder, tearoff=0,bg=self.bg)
        self.PopupFolder.bind("<FocusOut>",lambda event : self.PopupFolder.unpost() )

        self.FindEntryVar=tk.StringVar(value='')

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
        self.ScanDialog.iconphoto(False, self.iconphoto)

        self.ScanDialogMainFrame = tk.Frame(self.ScanDialog,bg=self.bg)
        self.ScanDialogMainFrame.pack(expand=1, fill='both')

        self.ScanDialog.config(bd=0, relief=FLAT)

        self.ScanDialog.title('Scan')

        self.sizeMinVar=tk.StringVar()
        self.sizeMaxVar=tk.StringVar()
        self.WriteScanToLog=tk.BooleanVar()

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

        self.ScanDialog.bind('<Alt_L><E>',lambda event : self.AddExckludeMaskDialog())
        self.ScanDialog.bind('<Alt_L><e>',lambda event : self.AddExckludeMaskDialog())

        ##############
        self.pathsFrame = tk.LabelFrame(self.ScanDialogMainFrame,text='Paths To Scan:',borderwidth=2,bg=self.bg)
        self.pathsFrame.grid(row=0,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        self.AddPathButton = ttk.Button(self.pathsFrame,width=10,text="Add Path ...",command=self.AddPathDialog,underline=0)
        self.AddPathButton.grid(column=0, row=100,pady=4,padx=4)

        #self.AddDrivesButton = ttk.Button(self.pathsFrame,width=10,text="Add drives",command=self.AddDrives,underline=4)
        #self.AddDrivesButton.grid(column=1, row=100,pady=4,padx=4)

        self.ClearListButton=ttk.Button(self.pathsFrame,width=10,text="Clear List",command=self.ClearPaths )
        self.ClearListButton.grid(column=2, row=100,pady=4,padx=4)

        self.pathsFrame.grid_columnconfigure(1, weight=1)
        self.pathsFrame.grid_rowconfigure(99, weight=1)

        ##############
        self.ScanExcludeRegExpr=tk.BooleanVar()

        self.ExcludeFRame = tk.LabelFrame(self.ScanDialogMainFrame,text='Exclude from scan:',borderwidth=2,bg=self.bg)
        self.ExcludeFRame.grid(row=1,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        self.AddExckludeMaskButton = ttk.Button(self.ExcludeFRame,width=16,text="Add Exclude Mask ...",command=self.AddExckludeMaskDialog,underline=4)
        self.AddExckludeMaskButton.grid(column=0, row=100,pady=4,padx=4)

        self.ClearExcludeListButton=ttk.Button(self.ExcludeFRame,width=10,text="Clear List",command=self.ClearExcludeMasks )
        self.ClearExcludeListButton.grid(column=2, row=100,pady=4,padx=4)

        self.ExcludeFRame.grid_columnconfigure(1, weight=1)
        self.ExcludeFRame.grid_rowconfigure(99, weight=1)
        ##############

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
        self.SetingsDialog.minsize(600, 400)
        self.SetingsDialog.wm_transient(self.main)
        self.SetingsDialog.update()
        self.SetingsDialog.withdraw()
        self.SetingsDialog.iconphoto(False, self.iconphoto)

        self.AddCwdAtStartup = tk.BooleanVar()
        self.ScanAtStartup = tk.BooleanVar()
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
            (self.AddCwdAtStartup,CFG_KEY_STARTUP_ADD_CWD),
            (self.ScanAtStartup,CFG_KEY_STARTUP_SCAN),
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

        self.SetingsDialog.wm_title('Settings')

        fr=tk.Frame(self.SetingsDialog,bg=self.bg)
        fr.pack(expand=1,fill='both')

        def AddPathAtStartupChange(self):
            if not self.AddCwdAtStartup.get():
                self.ScanAtStartup.set(False)

        def ScanAtStartupChange(self):
            if self.ScanAtStartup.get():
                self.AddCwdAtStartup.set(True)

        row = 0
        self.AddCwdCB=ttk.Checkbutton(fr, text = 'At startup add current directory to paths to scan', variable=self.AddCwdAtStartup,command=lambda : AddPathAtStartupChange(self) )
        self.AddCwdCB.grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1
        self.StartScanCB=ttk.Checkbutton(fr, text = 'Start scanning at startup', variable=self.ScanAtStartup,command=lambda : ScanAtStartupChange(self)                              )
        self.StartScanCB.grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1

        ttk.Checkbutton(fr, text = 'Show full CRC', variable=self.FullCRC                                       ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1
        ttk.Checkbutton(fr, text = 'Show full scan paths', variable=self.FullPaths                              ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1
        ttk.Checkbutton(fr, text = 'Create relative symbolic links', variable=self.RelSymlinks                  ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1

        ttk.Checkbutton(fr, text = 'Erase Empty directories', variable=self.EraseEmptyDirs                  ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1

        ttk.Checkbutton(fr, text = 'Allow to delete all copies (WARNING!)', variable=self.AllowDeleteAll                  ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1
        ttk.Checkbutton(fr, text = 'Skip groups with invalid selection', variable=self.SkipIncorrectGroups                  ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1
        #ttk.Checkbutton(fr, text = 'Allow to delete regular files (WARNING!)', variable=self.AllowDeleteNonDuplicates        ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1

        tk.Label(fr, text = '',bg=self.bg).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1
        tk.Label(fr, text = 'Confirmation Dialog Options:',bg=self.bg,anchor='w').grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1

        ttk.Checkbutton(fr, text = 'Show soft links targets', variable=self.ConfirmShowLinksTargets                  ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1
        ttk.Checkbutton(fr, text = 'Show CRC and size', variable=self.ConfirmShowCrcSize                  ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1

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
            self.StatusLine.set(str(e))
            logging.error(e)
            self.exit()

        try:
            self.keyboardshortcuts=pathlib.Path(os.path.join(os.path.dirname(__file__),'keyboard.shortcuts.txt')).read_text()
        except Exception as e:
            self.StatusLine.set(str(e))
            logging.error(e)
            self.exit()

        def FileCascadeFill():
            self.FileCascade.delete(0,END)
            ItemActionsState=('disabled','normal')[self.SelItem!=None]

            self.FileCascade.add_command(label = 'Scan',command = self.ScanDialogShow, accelerator="S")
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'Settings',command=self.SettingsDialogShow, accelerator="F2")
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'Remove empty folders in specified directory ...',command=lambda : self.RemoveEmptyFoldersAsk())
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'Erase CRC Cache',command = self.CleanCache)
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'Exit',command = self.exit)

        self.FileCascade= Menu(self.menubar,tearoff=0,bg=self.bg,postcommand=FileCascadeFill)
        self.menubar.add_cascade(label = 'File',menu = self.FileCascade,accelerator="Alt+F")

        def GoToCascadeFill():
            self.GoToCascade.delete(0,END)
            ItemActionsState=('disabled','normal')[self.SelItem!=None]
            self.GoToCascade.add_command(label = 'Go to dominant group (by size sum)',command = lambda : self.GoToMaxGroup(1), accelerator="F7",state=ItemActionsState)
            self.GoToCascade.add_command(label = 'Go to dominant group (by quantity)',command = lambda : self.GoToMaxGroup(0), accelerator="F8",state=ItemActionsState)
            self.GoToCascade.add_separator()
            self.GoToCascade.add_command(label = 'Go to dominant folder (by size sum)',command = lambda : self.GoToMaxFolder(1),accelerator="F5",state=ItemActionsState)
            self.GoToCascade.add_command(label = 'Go to dominant folder (by quantity)',command = lambda : self.GoToMaxFolder(0), accelerator="F6",state=ItemActionsState)
            #self.GoToCascade.add_separator()
            #self.GoToCascade.add_command(label = 'Go to dominant folder (by duplicates/other files size ratio)',command = lambda : self.GoToMaxFolder(1,1),accelerator="Backspace",state=ItemActionsState)
            #self.GoToCascade.add_command(label = 'Go to dominant folder (by duplicates/other files quantity ratio)',command = lambda : self.GoToMaxFolder(0,1), accelerator="Ctrl+Backspace",state=ItemActionsState)

        self.GoToCascade= Menu(self.menubar,tearoff=0,bg=self.bg,postcommand=GoToCascadeFill)

        self.menubar.add_cascade(label = 'Navigation',menu = self.GoToCascade)

        self.HelpCascade= Menu(self.menubar,tearoff=0,bg=self.bg)
        self.HelpCascade.add_command(label = 'About',command=self.About,accelerator="F1")
        self.HelpCascade.add_command(label = 'Keyboard Shortcuts',command=self.KeyboardShortcuts)
        self.HelpCascade.add_command(label = 'License',command=self.License)

        self.menubar.add_cascade(label = 'Help',menu = self.HelpCascade)

        #######################################################################
        self.ResetSels()

        if pathsToAdd:
            for path in pathsToAdd:
                self.addPath(os.path.abspath(path))
        else:
            if self.AddCwdAtStartup:
                self.addPath(cwd)

        if exclude:
            self.cfg.Set(CFG_KEY_EXCLUDE,'|'.join(exclude))
            self.cfg.SetBool(CFG_KEY_EXCLUDE_REGEXP,False)
        elif excluderegexp:
            self.cfg.Set(CFG_KEY_EXCLUDE,'|'.join(excluderegexp))
            self.cfg.SetBool(CFG_KEY_EXCLUDE_REGEXP,True)

        self.ScanExcludeRegExpr.set(self.cfg.GetBool(CFG_KEY_EXCLUDE_REGEXP))

        self.ScanDialogShow()

        self.ColumnSortLastParams={}
        self.ColumnSortLastParams[self.TreeGroups]=['sizeH',1]
        self.ColumnSortLastParams[self.TreeFolder]=['file',0]

        self.SelItemTree[self.TreeGroups]=None
        self.SelItemTree[self.TreeFolder]=None

        self.ShowGroups()

        if pathsToAdd:
            if not norun:
                self.main.update()
                self.Scan()
        else:
            if self.cfg.GetBool(CFG_KEY_STARTUP_SCAN):
                self.main.update()
                self.Scan()

        self.main.mainloop()

    def TreeClose(self,event):
        tree=event.widget
        item=tree.focus()
        tree.item(item, open=True)

    def ResetSels(self):
        self.SelPathnr = None
        self.SelPath = None
        self.SelFile = None
        self.SelCrc = None
        self.SelItem = None
        self.SelItemTree = {}
        self.SelItemTree[self.TreeGroups]=None
        self.SelItemTree[self.TreeFolder]=None
        self.FullPathToFile = None

        self.SelTreeIndex = 0
        self.SelKind = None

    def GetIndexTupleTreeGroups(self,item):
        return self.GetIndexTuple(item,self.TreeGroups)

    def GetIndexTupleTreeFolder(self,item):
        return self.GetIndexTuple(item,self.TreeFolder)

    def GetIndexTuple(self,item,tree):
        return tuple([ fn(tree.item(item)['values'][index]) for fn,index in self.IndexTupleIndexesWithFnCommon ])

    def exit(self):
        self.GeometryStore(self.main)
        self.ScanDialog.destroy()
        self.SetingsDialog.destroy()
        self.StoreSplitter()
        exit()

    def WidgetId(self,widget):
        return widget.wm_title().split(' ')[0]

    def SetDefaultGeometryAndShow(self,widget,parent):
        try:
            widget.update()
            CfgGeometry=self.cfg.Get(self.WidgetId(widget),None,section='geometry')

            if CfgGeometry != None and CfgGeometry != 'None':
                widget.geometry(CfgGeometry)
            elif parent :
                widget.geometry(CenterToParentGeometry(widget,parent))
            else:
                widget.geometry(CenterToScreenGeometry(widget))
        except Exception as e:
            self.StatusLine.set(str(e))
            print('widget:',widget,'parent:',parent,'error:',e)
            CfgGeometry = None

        widget.deiconify()

        #prevent displacement
        if CfgGeometry != None and CfgGeometry != 'None':
            widget.geometry(CfgGeometry)


    def GeometryStore(self,widget):
        self.cfg.Set(self.WidgetId(widget),str(widget.geometry()),section='geometry')
        self.cfg.Write()

    FindResult=[]
    FindEntryModified=1
    FindTreeIndex=-1

    @MainWatchCursor
    def FindPrev(self):
        if not self.FindResult or self.FindTreeIndex!=self.SelTreeIndex:
            self.FindDialogShow()
        else:
            self.FindSelection(-1)
            self.StatusLine.set('Find Previous')

    @MainWatchCursor
    def FindNext(self):
        if not self.FindResult or self.FindTreeIndex!=self.SelTreeIndex:
            self.FindDialogShow()
        else:
            self.FindSelection(1)
            self.StatusLine.set('Find Next')

    FindModIndex=0
    FindTree=''
    FindDialogShown=0
    FindDialogRegExprPrev=''
    FindEntryVarPrev=''

    @KeepSemiFocus
    def FindDialogShow(self):
        self.main.config(cursor="watch")
        self.FindDialogShown=1
        self.FindEntryModified=1

        self.FindDialog=dialog = tk.Toplevel(self.main)
        PrevGrab = dialog.grab_current()

        dialog.minsize(400, 100)
        dialog.wm_transient(self.main)
        dialog.update()
        dialog.withdraw()
        ScopeInfo = 'all groups.' if self.SelTreeIndex==0 else 'selected directory.'

        dialog.wm_title(f"Find duplicate in {ScopeInfo}")
        dialog.config(bd=2, relief=FLAT,bg=self.bg)
        dialog.iconphoto(False, self.iconphoto)

        tree,otherTree=(self.TreeGroups,self.TreeFolder) if self.SelTreeIndex==0 else (self.TreeFolder,self.TreeGroups)

        self.FindTree=tree

        def over(event=None):
            nonlocal self

            self.FindDialogShown=0

            self.GeometryStore(dialog)
            dialog.destroy()

            self.cfg.SetBool(CFG_KEY_USE_REG_EXPR,self.DialogRegExpr.get())

            try:
                dialog.update()
            except Exception as e:
                pass

            self.FindTree.focus(self.SelItem)
            self.main.config(cursor="")

        def FindModEvent(event=None):
            nonlocal self

            if self.FindDialogRegExprPrev!=self.DialogRegExpr.get() or self.FindEntryVarPrev!=self.FindEntryVar.get():
                self.FindDialogRegExprPrev=self.DialogRegExpr.get()
                self.FindEntryVarPrev=self.FindEntryVar.get()
                self.FindEntryModified=1
                self.FindModIndex=0

        def PrevCmd(event=None):
            nonlocal self
            FindItems()
            self.FindSelection(-1)

        def NextCmd(event=None):
            nonlocal self
            FindItems()
            self.FindSelection(1)

        dialog.protocol("WM_DELETE_WINDOW", over)

        Entry=''
        Close=''
        Next=''
        Prev=''

        def F3Pressed(event=None):
            self.StatusLine.set('')
            StrEvent=str(event)
            ShiftPressed = 'Shift' in StrEvent

            if ShiftPressed:
                PrevCmd()
            else:
                NextCmd()

        def ReturnPressed(event=None):
            self.StatusLine.set('')
            nonlocal dialog
            nonlocal Next
            nonlocal Prev
            nonlocal Close
            nonlocal Entry

            focus=dialog.focus_get()
            if focus==Next or focus==Entry:
                NextCmd()
            elif focus==Prev:
                PrevCmd()
            elif focus==Close:
                over()

        def FindItems(event=None):
            nonlocal self

            if self.FindEntryModified:
                Expression=self.FindEntryVar.get()

                tree=self.FindTree
                self.FindTreeIndex=self.SelTreeIndex

                self.FindResult=items=[]

                UseRegExpr=self.DialogRegExpr.get()

                if Expression:
                    if tree==self.TreeGroups:
                        CrcRange = self.TreeGroups.get_children()

                        try:
                            for crcitem in CrcRange:
                                for item in self.TreeGroups.get_children(crcitem):
                                    fullpath = self.ItemFullPath(item)
                                    if (UseRegExpr and re.search(Expression,fullpath)) or (not UseRegExpr and fnmatch.fnmatch(fullpath,Expression) ):
                                        items.append(item)
                        except Exception as e:
                            self.DialogWithEntry(title='Error',prompt=e,parent=self.FindDialog,OnlyInfo=True,width=300,height=100)
                            return
                    else:
                        try:
                            for item in self.TreeFolder.get_children():
                                #if tree.set(item,'kind')==FILE:
                                file=self.TreeFolder.set(item,'file')
                                if (UseRegExpr and re.search(Expression,file)) or (not UseRegExpr and fnmatch.fnmatch(file,Expression) ):
                                    items.append(item)
                        except Exception as e:
                            self.DialogWithEntry(title='Error',prompt=e,parent=self.FindDialog,OnlyInfo=True,width=300,height=100)
                            return

                if items:
                    self.FindResult=items
                    self.FindEntryModified=0

                if not self.FindResult:
                    ScopeInfo = 'Scope: All groups.' if self.FindTreeIndex==0 else 'Scope: Selected directory.'
                    self.DialogWithEntry(title=ScopeInfo,prompt='No files found.',parent=self.FindDialog,OnlyInfo=True,width=300,height=100)


        tk.Label(dialog,text='',anchor='n',justify='center',bg=self.bg).grid(sticky='news',row=0,column=0,padx=5,pady=5)

        self.DialogRegExpr=tk.BooleanVar()
        self.DialogRegExpr.set(self.cfg.GetBool(CFG_KEY_USE_REG_EXPR))
        ttk.Checkbutton(dialog,text='Use regular expressions matching',variable=self.DialogRegExpr,command=FindModEvent).grid(row=1,column=0,sticky='news',padx=5)

        (Entry:=ttk.Entry(dialog,textvariable=self.FindEntryVar)).grid(sticky='news',row=2,column=0,padx=5,pady=5)
        Entry.bind('<KeyRelease>',FindModEvent)

        (bfr:=tk.Frame(dialog,bg=self.bg)).grid(sticky='news',row=3,column=0,padx=5,pady=5)

        Prev=ttk.Button(bfr, text='Prev (Shift+F3)', width=14, command=PrevCmd)
        Next=ttk.Button(bfr, text='Next (F3)', width=14, command=NextCmd)
        Prev.pack(side='left', anchor='e',padx=5,pady=5)
        Next.pack(side='left', anchor='e',padx=5,pady=5)
        Close=ttk.Button(bfr, text='Close', width=10 ,command=over)
        Close.pack(side='right', anchor='w',padx=5,pady=5)

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        dialog.bind('<Escape>', over)
        dialog.bind('<KeyPress-Return>', ReturnPressed)
        dialog.bind('<KeyPress-F3>', F3Pressed)

        self.SetDefaultGeometryAndShow(dialog,self.main)
        Entry.focus_set()
        dialog.grab_set()
        self.main.wait_window(dialog)

        if PrevGrab:
            PrevGrab.grab_set()
        else:
            dialog.grab_release()

    @MainWatchCursor
    def FindSelection(self,mod):
        if self.FindResult:
            itemsLen=len(self.FindResult)
            self.FindModIndex+=mod
            NextItem=self.FindResult[self.FindModIndex%itemsLen]

            if self.FindDialogShown:
                #focus is still on find dialog
                self.FindTree.selection_set(NextItem)
            else:
                self.FindTree.focus_set()
                self.FindTree.focus(NextItem)

            self.FindTree.see(NextItem)
            self.FindTree.update()

            if self.FindTree==self.TreeGroups:
                self.TreeGroupsSelChange(NextItem)
            else:
                self.TreeFolderSelChange(NextItem)

    def DialogWithEntry(self,title,prompt,parent,initialvalue='',OnlyInfo=False,ShowRegExpCheckButton=False,width=400,height=140):
        parent.config(cursor="watch")

        dialog = tk.Toplevel(parent)
        dialog.minsize(width, height)
        dialog.wm_transient(parent)
        dialog.update()
        dialog.withdraw()
        dialog.wm_title(title)
        dialog.config(bd=2, relief=FLAT,bg=self.bg)
        dialog.iconphoto(False, self.iconphoto)

        res=False

        EntryVar=tk.StringVar(value=initialvalue)

        def over():
            self.GeometryStore(dialog)
            nonlocal ShowRegExpCheckButton
            if ShowRegExpCheckButton:
                self.cfg.SetBool(CFG_KEY_USE_REG_EXPR,self.DialogRegExpr.get())

            dialog.destroy()
            try:
                dialog.update()
            except Exception as e:
                pass
            parent.config(cursor="")

        def Yes(event=None):
            nonlocal res
            nonlocal EntryVar
            res=EntryVar.get()
            over()

        def No(event=None):
            nonlocal res
            res=False
            over()

        dialog.protocol("WM_DELETE_WINDOW", No)

        cancel=''

        def ReturnPressed(event=None):
            nonlocal dialog
            nonlocal cancel

            focus=dialog.focus_get()
            if focus!=cancel:
                Yes()
            else:
                No()

        tk.Label(dialog,text=prompt,anchor='n',justify='center',bg=self.bg).grid(sticky='news',row=0,column=0,padx=5,pady=5)
        if not OnlyInfo:
            if ShowRegExpCheckButton:
                self.DialogRegExpr=tk.BooleanVar()
                self.DialogRegExpr.set(self.cfg.GetBool(CFG_KEY_USE_REG_EXPR))
                ttk.Checkbutton(dialog,text='Use regular expressions matching',variable=self.DialogRegExpr).grid(row=1,column=0,sticky='news',padx=5)

            (entry:=ttk.Entry(dialog,textvariable=EntryVar)).grid(sticky='news',row=2,column=0,padx=5,pady=5)

        (bfr:=tk.Frame(dialog,bg=self.bg)).grid(sticky='news',row=3,column=0,padx=5,pady=5)

        if OnlyInfo:
            ok=default=ttk.Button(bfr, text='OK', width=10 ,command=No)
            ok.pack()
        else:
            ok=default=ttk.Button(bfr, text='OK', width=10, command=Yes)
            ok.pack(side='left', anchor='e',padx=5,pady=5)
            cancel=ttk.Button(bfr, text='Cancel', width=10 ,command=No)
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

        dialog.grab_release()

        if PrevGrab:
            PrevGrab.grab_set()
        else:
            dialog.grab_release()

        if ShowRegExpCheckButton:
            return (res,self.DialogRegExpr.get())
        else:
            return res

    def dialog(self,parent,title,message,OnlyInfo=False,textwidth=128,width=800,height=600):
        parent.config(cursor="watch")

        dialog = tk.Toplevel(parent)
        PrevGrab = dialog.grab_current()

        dialog.minsize(width,height)
        dialog.wm_transient(parent)
        dialog.update()
        dialog.withdraw()
        dialog.wm_title(title)
        dialog.config(bd=2, relief=FLAT,bg=self.bg)
        dialog.iconphoto(False, self.iconphoto)

        res=False

        def over():
            self.GeometryStore(dialog)
            dialog.destroy()
            try:
                dialog.update()
            except Exception as e:
                pass
            parent.config(cursor="")

        def Yes(event=None):
            over()
            nonlocal res
            res=True

        def No(event=None):
            over()
            nonlocal res
            res=False

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

        self.SetDefaultGeometryAndShow(dialog,parent)

        default.focus_set()

        dialog.grab_set()
        parent.wait_window(dialog)

        if PrevGrab:
            PrevGrab.grab_set()
        else:
            dialog.grab_release()

        return res

    def Ask(self,title,message,top,width=800,height=400):
        return self.dialog(top,title,message,False,width=width,height=height)

    def Info(self,title,message,top,textwidth=150,width=800,height=400):
        return self.dialog(top,title,message,True,textwidth=textwidth,width=width,height=height)

    def ToggleSelectedTag(self,tree, *items):
        for item in items:
            if tree.set(item,'kind')==FILE:
                self.InvertMark(item, self.TreeGroups)
                try:
                    self.TreeFolder.item(item,tags=self.TreeGroups.item(item)['tags'])
                except Exception :
                    pass
            elif tree.set(item,'kind')==CRC:
                return self.ToggleSelectedTag(tree, *tree.get_children(item) )

        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    DirectionOfKeysym={}
    DirectionOfKeysym['Up']=-1
    DirectionOfKeysym['Down']=1
    DirectionOfKeysym['Prior']=-1
    DirectionOfKeysym['Next']=1

    reftuple1=('1','2','3','4','5','6','7')
    reftuple2=('exclam','at','numbersign','dollar','percent','asciicircum','ampersand')

    #KeyReleased=True
    #def KeyReleaseTreeCommon(self,event):
    #    self.main.update()
    #    self.KeyReleased=True

    @MainWatchCursor
    def KeyPressTreeCommon(self,event):
        self.main.unbind_class('Treeview','<KeyPress>')

        #if not self.KeyReleased:
            #prevents (?) windows auto-repeat problem
        #    self.main.update()
        try:
            self.KeyReleased=False

            tree=event.widget
            item=tree.focus()

            tree.selection_remove(tree.selection())

            if event.keysym in ("Up",'Down') :
                (pool,poolLen) = (self.TreeGroupsFlatItemsTouple,len(self.TreeGroupsFlatItemsTouple) ) if self.SelTreeIndex==0 else (self.TreeFolderFlatItemsList,len(self.TreeFolderFlatItemsList))

                if poolLen:
                    index = pool.index(self.SelItem) if self.SelItem in pool else pool.index(self.SelItemTree[tree]) if self.SelItemTree[tree] in pool else pool.index(item) if item in  pool else 0
                    index=(index+self.DirectionOfKeysym[event.keysym])%poolLen
                    NextItem=pool[index]

                    tree.focus(NextItem)
                    tree.see(NextItem)

                    if self.SelTreeIndex==0:
                        self.TreeGroupsSelChange(NextItem)
                    else:
                        self.TreeFolderSelChange(NextItem)
            elif event.keysym in ("Prior","Next"):
                if self.SelTreeIndex==0:
                    pool=tree.get_children()
                else:
                    pool=[item for item in tree.get_children() if tree.set(item,'kind')==FILE]

                poolLen=len(pool)
                if poolLen:
                    if self.SelTreeIndex==0:
                        NextItem=pool[(pool.index(tree.set(item,'crc'))+self.DirectionOfKeysym[event.keysym]) % poolLen]
                        self.SelectFocusAndSeeCrcItemTree(NextItem)
                    else:
                        self.GotoNextDupeFile(tree,self.DirectionOfKeysym[event.keysym])
                        tree.update()
            elif event.keysym in ("Home","End"):
                if self.SelTreeIndex==0:
                    if NextItem:=tree.get_children()[0 if event.keysym=="Home" else -1]:
                        self.SelectFocusAndSeeCrcItemTree(NextItem,True)
                else:
                    if NextItem:=tree.get_children()[0 if event.keysym=='Home' else -1]:
                        tree.see(NextItem)
                        tree.focus(NextItem)
                        self.TreeFolderSelChange(NextItem)
                        tree.update()
            elif event.keysym == "space":
                if self.SelTreeIndex==0:
                    if tree.set(item,'kind')==CRC:
                        self.ToggleSelectedTag(tree,*tree.get_children(item))
                    else:
                        self.ToggleSelectedTag(tree,item)
                else:
                    self.ToggleSelectedTag(tree,item)
            elif event.keysym == "Right":
                self.GotoNextMark(event.widget,1)
            elif event.keysym == "Left":
                self.GotoNextMark(event.widget,-1)
            elif event.keysym == "Tab":
                tree.selection_set(tree.focus())
                self.FromTabSwicth=True
            elif event.keysym=='KP_Multiply' or event.keysym=='asterisk':
                self.MarkOnAll(self.InvertMark)
            elif event.keysym=='Return':
                item=tree.focus()
                if item:
                    self.TreeAction(tree,item)
            else:
                StrEvent=str(event)

                CtrPressed = 'Control' in StrEvent
                ShiftPressed = 'Shift' in StrEvent

                if event.keysym=='F3':
                    if ShiftPressed:
                        self.FindPrev()
                    else:
                        self.FindNext()

                elif event.keysym=='KP_Add' or event.keysym=='plus':
                    StrEvent=str(event)
                    self.MarkExpression(self.SetMark,'Mark files',CtrPressed)
                elif event.keysym=='KP_Subtract' or event.keysym=='minus':
                    StrEvent=str(event)
                    self.MarkExpression(self.UnsetMark,'Unmark files',CtrPressed)
                elif event.keysym == "Delete":
                    if self.SelTreeIndex==0:
                        self.ProcessFilesTreeCrcWrapper(DELETE,CtrPressed)
                    else:
                        self.ProcessFilesTreeFolderWrapper(DELETE,self.SelKind==DIR)
                elif event.keysym == "Insert":
                    if self.SelTreeIndex==0:
                        self.ProcessFilesTreeCrcWrapper((SOFTLINK,HARDLINK)[ShiftPressed],CtrPressed)
                    else:
                        self.ProcessFilesTreeFolderWrapper((SOFTLINK,HARDLINK)[ShiftPressed],self.SelKind==DIR)
                elif event.keysym=='F5':
                    self.GoToMaxFolder(0,-1 if ShiftPressed else 1)
                elif event.keysym=='F6':
                    self.GoToMaxFolder(1,-1 if ShiftPressed else 1)
                elif event.keysym=='F7':
                    self.GoToMaxGroup(0,-1 if ShiftPressed else 1)
                elif event.keysym=='F8':
                    self.GoToMaxGroup(1,-1 if ShiftPressed else 1)
                elif event.keysym=='BackSpace':
                    if self.SelFullPath :
                        if self.TwoDotsConditionOS():
                            self.TreeFolder.focus_set()
                            head,tail=os.path.split(self.SelFullPath)
                            self.EnterDir(os.path.normpath(str(pathlib.Path(self.SelFullPath).parent.absolute())),tail)
                elif event.keysym=='i' or event.keysym=='I':
                    if CtrPressed:
                        self.MarkOnAll(self.InvertMark)
                    else:
                        if self.SelTreeIndex==0:
                            self.MarkInCRCGroup(self.InvertMark)
                        else:
                            self.MarkLowerPane(self.InvertMark)
                elif event.keysym=='o' or event.keysym=='O':
                    if CtrPressed:
                        if ShiftPressed:
                            self.MarkOnAllByCTime('oldest',self.UnsetMark)
                        else:
                            self.MarkOnAllByCTime('oldest',self.SetMark)
                    else:
                        if self.SelTreeIndex==0:
                            self.MarkInCRCGroupByCTime('oldest',self.InvertMark)
                elif event.keysym=='y' or event.keysym=='Y':
                    if CtrPressed:
                        if ShiftPressed:
                            self.MarkOnAllByCTime('youngest',self.UnsetMark)
                        else:
                            self.MarkOnAllByCTime('youngest',self.SetMark)
                    else:
                        if self.SelTreeIndex==0:
                            self.MarkInCRCGroupByCTime('youngest',self.InvertMark)
                elif event.keysym=='c' or event.keysym=='C':
                    if CtrPressed:
                        if ShiftPressed:
                            self.ClipCopyFile()
                        else:
                            self.ClipCopyFullWithFile()
                    else:
                        self.ClipCopyFull()

                elif event.keysym=='a' or event.keysym=='A':
                    if self.SelTreeIndex==0:
                        if CtrPressed:
                            self.MarkOnAll(self.SetMark)
                        else:
                            self.MarkInCRCGroup(self.SetMark)
                    else:
                        self.MarkLowerPane(self.SetMark)

                elif event.keysym=='n' or event.keysym=='N':
                    if self.SelTreeIndex==0:
                        if CtrPressed:
                            self.MarkOnAll(self.UnsetMark)
                        else:
                            self.MarkInCRCGroup(self.UnsetMark)
                    else:
                        self.MarkLowerPane(self.UnsetMark)
                elif event.keysym=='r' or event.keysym=='R':
                    if self.SelTreeIndex==1:
                        self.TreeFolderUpdate()
                        self.TreeFolder.focus_set()
                        try:
                            self.TreeFolder.focus(self.SelItem)
                        finally:
                            pass
                elif event.keysym in self.reftuple1:
                    index = self.reftuple1.index(event.keysym)

                    if index<len(self.D.ScannedPaths):
                        if self.SelTreeIndex==0:
                            self.ActionOnSpecifiedPath(self.D.ScannedPaths[index],self.SetMark,CtrPressed)
                elif event.keysym in self.reftuple2:
                    index = self.reftuple2.index(event.keysym)

                    if index<len(self.D.ScannedPaths):
                        if self.SelTreeIndex==0:
                            self.ActionOnSpecifiedPath(self.D.ScannedPaths[index],self.UnsetMark,CtrPressed)
                elif event.keysym=='KP_Divide' or event.keysym=='slash':
                    self.MarkSubpath(self.SetMark,True)
                elif event.keysym=='question':
                    self.MarkSubpath(self.UnsetMark,True)
                elif event.keysym=='f' or event.keysym=='F':
                    self.FindDialogShow()
        finally:
            self.main.bind_class('Treeview','<KeyPress>', self.KeyPressTreeCommon )

#################################################
    def SelectFocusAndSeeCrcItemTree(self,crc,TryToShowAll=False):
        self.TreeGroups.focus_set()

        if TryToShowAll:
            lastChild=self.TreeGroups.get_children(crc)[-1]
            self.TreeGroups.see(lastChild)
            self.TreeGroups.update()

        self.TreeGroups.see(crc)
        self.TreeGroups.focus(crc)
        self.TreeGroups.update()
        self.TreeGroupsSelChange(crc)

    def TreeButtonPress(self,event,toggle=False):
        self.MenubarUnpost()

        tree=event.widget

        if tree.identify("region", event.x, event.y) == 'heading':
            if (colname:=tree.column(tree.identify_column(event.x),'id') ) in self.col2sortOf:
                self.ColumnSortClick(tree,colname)

                if self.SelKind==FILE:
                    tree.focus_set()

                    tree.focus(self.SelItem)
                    tree.see(self.SelItem)

                    if tree==self.TreeGroups:
                        self.TreeGroupsSelChange(self.SelItem)
                    else:
                        self.TreeFolderSelChange(self.SelItem)

        elif item:=tree.identify('item',event.x,event.y):
            tree.selection_remove(tree.selection())

            tree.focus_set()
            tree.focus(item)

            if tree==self.TreeGroups:
                self.TreeGroupsSelChange(item)
            else:
                self.TreeFolderSelChange(item)

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
                if tree==self.TreeGroups:
                    self.TreeGroupsSelChange(item,True)
                else:
                    self.TreeFolderSelChange(item)

                tree.see(item)

        if len(self.TreeFolder.get_children())==0:
            self.TreeGroups.selection_remove(self.TreeGroups.selection())
            self.TreeGroups.focus_set()

    def TreeFocusOut(self,event):
        tree=event.widget
        tree.selection_set(tree.focus())

    def SetFullPathToFileWin(self):
        self.SelFullPathToFile=pathlib.Path(os.sep.join([self.SelFullPath,self.SelFile])) if self.SelFullPath and self.SelFile else None

    def SetFullPathToFileLin(self):
        self.SelFullPathToFile=(self.SelFullPath+self.SelFile if self.SelFullPath=='/' else os.sep.join([self.SelFullPath,self.SelFile])) if self.SelFullPath and self.SelFile else None

    SetFullPathToFile = SetFullPathToFileWin if windows else SetFullPathToFileLin

    def SetSelPath(self,path):
        if self.SelFullPath != path:
            self.SelFullPath = path

            self.DominantIndexFolders[0] = -1
            self.DominantIndexFolders[1] = -1

    def TreeGroupsSelChange(self,item,force=False,ChangeStatusLine=True):
        if ChangeStatusLine : self.StatusLine.set('')

        pathnr=self.TreeGroups.set(item,'pathnr')
        path=self.TreeGroups.set(item,'path')

        self.SelFile = self.TreeGroups.set(item,'file')
        newCrc = self.TreeGroups.set(item,'crc')

        if self.SelCrc != newCrc:
            self.SelCrc = newCrc

            self.DominantIndexGroups[0] = -1
            self.DominantIndexGroups[1] = -1

        self.SelItem = item
        self.SelItemTree[self.TreeGroups]=item
        self.SelTreeIndex=0

        size = int(self.TreeGroups.set(item,'size'))

        if path!=self.SelPath or pathnr!=self.SelPathnr or force:
            self.SelPathnr = pathnr

            if pathnr: #non crc node
                self.SelPathnrInt= int(pathnr)
                self.SelSearchPath = self.D.ScannedPaths[self.SelPathnrInt]
                self.SelPath = path
                self.SetSelPath(self.SelSearchPath+self.SelPath)
            else :
                self.SelPathnrInt= 0
                self.SelSearchPath = None
                self.SelPath = None
                self.SetSelPath(None)
            self.SetFullPathToFile()

        self.SelKind = self.TreeGroups.set(item,'kind')
        if self.SelKind==FILE:
            self.SetCommonVar()
            self.TreeFolderUpdate()
        else:
            self.TreeFolderUpdateNone()

    def TreeFolderSelChange(self,item,ChangeStatusLine=True):
        self.SelFile = self.TreeFolder.set(item,'file')
        self.SelCrc = self.TreeFolder.set(item,'crc')
        self.SelKind = self.TreeFolder.set(item,'kind')
        self.SelItem = item
        self.SelItemTree[self.TreeFolder] = item
        self.SelTreeIndex=1

        self.SetFullPathToFile()

        self.SetCommonVar()

        kind=self.TreeFolder.set(item,'kind')
        if kind==FILE:
            if ChangeStatusLine: self.StatusLine.set('')
            self.UpdateMainTree(item)
        else:
            if kind==LINK:
                if ChangeStatusLine: self.StatusLine.set('  🠖  ' + os.readlink(self.SelFullPathToFile))
            elif kind==SINGLEHARDLINKED:
                if ChangeStatusLine: self.StatusLine.set('File with hardlinks')
            elif kind==SINGLE:
                if ChangeStatusLine: self.StatusLine.set('')
            elif kind==DIR:
                if ChangeStatusLine: self.StatusLine.set('Subdirectory')
            elif kind==UPDIR:
                if ChangeStatusLine: self.StatusLine.set('Parent directory')

            self.UpdateMainTreeNone()

    def MenubarUnpost(self):
        try:
            self.menubar.unpost()
        except Exception as e:
            print(e)

    def TreeContexMenu(self,event):
        self.TreeButtonPress(event)

        tree=event.widget

        ItemActionsState=('disabled','normal')[self.SelItem!=None]

        pop=self.PopupGroups if tree==self.TreeGroups else self.PopupFolder

        pop.delete(0,END)

        FileActionsState=('disabled',ItemActionsState)[self.SelKind==FILE]
        if tree==self.TreeGroups:
            cLocal = Menu(pop,tearoff=0,bg=self.bg)
            cLocal.add_command(label = "Toggle Mark",  command = lambda : self.ToggleSelectedTag(tree,self.SelItem),accelerator="space")
            cLocal.add_separator()
            cLocal.add_command(label = "Mark all files",        command = lambda : self.MarkInCRCGroup(self.SetMark),accelerator="A")
            cLocal.add_command(label = "Unmark all files",        command = lambda : self.MarkInCRCGroup(self.UnsetMark),accelerator="N")
            cLocal.add_separator()
            cLocal.add_command(label = 'Mark By Expression',command = lambda : self.MarkExpression(self.SetMark,'Mark files',False),accelerator="+")
            cLocal.add_command(label = 'Unmark By Expression',command = lambda : self.MarkExpression(self.UnsetMark,'Unmark files',False),accelerator="-")
            cLocal.add_separator()
            cLocal.add_command(label = "Toggle mark on oldest file",     command = lambda : self.MarkInCRCGroupByCTime('oldest',self.InvertMark),accelerator="O")
            cLocal.add_command(label = "Toggle mark on youngest file",   command = lambda : self.MarkInCRCGroupByCTime('youngest',self.InvertMark),accelerator="Y")
            cLocal.add_separator()
            cLocal.add_command(label = "Invert marks",   command = lambda : self.MarkInCRCGroup(self.InvertMark),accelerator="I")
            cLocal.add_separator()

            MarkCascadePath = Menu(cLocal, tearoff = 0,bg=self.bg)
            UnmarkCascadePath = Menu(cLocal, tearoff = 0,bg=self.bg)

            row=0
            for path in self.D.ScannedPaths:
                MarkCascadePath.add_command(label = self.Numbers[row] + '  =  ' + path,    command  = lambda pathpar=path: self.ActionOnSpecifiedPath(pathpar,self.SetMark,False),accelerator=str(row+1)  )
                UnmarkCascadePath.add_command(label = self.Numbers[row] + '  =  ' + path,  command  = lambda pathpar=path: self.ActionOnSpecifiedPath(pathpar,self.UnsetMark,False),accelerator="Shift+"+str(row+1)  )
                row+=1

            cLocal.add_command(label = "Mark on specified directory ...",   command = lambda : self.MarkSubpath(self.SetMark,False))
            cLocal.add_command(label = "Unmark on specified directory ...",   command = lambda : self.MarkSubpath(self.UnsetMark,False))
            cLocal.add_separator()

            cLocal.add_cascade(label = "Mark on scan path",             menu = MarkCascadePath)
            cLocal.add_cascade(label = "Unmark on scan path",             menu = UnmarkCascadePath)
            cLocal.add_separator()

            MarksState=('disabled','normal')[len(tree.tag_has(MARK))!=0]

            cLocal.add_command(label = 'Remove Marked Files',command=lambda : self.ProcessFilesTreeCrcWrapper(DELETE,0),accelerator="Delete",state=MarksState)
            cLocal.entryconfig(19,foreground='red',activeforeground='red')
            cLocal.add_command(label = 'Softlink Marked Files',command=lambda : self.ProcessFilesTreeCrcWrapper(SOFTLINK,0),accelerator="Insert",state=MarksState)
            cLocal.entryconfig(20,foreground='red',activeforeground='red')
            cLocal.add_command(label = 'Hardlink Marked Files',command=lambda : self.ProcessFilesTreeCrcWrapper(HARDLINK,0),accelerator="Shift+Insert",state=MarksState)
            cLocal.entryconfig(21,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'Local (this CRC group)',menu = cLocal,state=ItemActionsState)
            pop.add_separator()

            cAll = Menu(pop,tearoff=0,bg=self.bg)

            cAll.add_command(label = "Mark all files",        command = lambda : self.MarkOnAll(self.SetMark),accelerator="Ctrl+A")
            cAll.add_command(label = "Unmark all files",        command = lambda : self.MarkOnAll(self.UnsetMark),accelerator="Ctrl+N")
            cAll.add_separator()
            cAll.add_command(label = 'Mark By Expression',command = lambda : self.MarkExpression(self.SetMark,'Mark files',True),accelerator="Ctrl+")
            cAll.add_command(label = 'Unmark By Expression',command = lambda : self.MarkExpression(self.UnsetMark,'Unmark files',True),accelerator="Ctrl-")
            cAll.add_separator()
            cAll.add_command(label = "Mark Oldest files",     command = lambda : self.MarkOnAllByCTime('oldest',self.SetMark),accelerator="Ctrl+O")
            cAll.add_command(label = "Unmark Oldest files",     command = lambda : self.MarkOnAllByCTime('oldest',self.UnsetMark),accelerator="Ctrl+Shift+O")
            cAll.add_separator()
            cAll.add_command(label = "Mark Youngest files",   command = lambda : self.MarkOnAllByCTime('youngest',self.SetMark),accelerator="Ctrl+Y")
            cAll.add_command(label = "Unmark Youngest files",   command = lambda : self.MarkOnAllByCTime('youngest',self.UnsetMark),accelerator="Ctrl+Shift+Y")
            cAll.add_separator()
            cAll.add_command(label = "Invert marks",   command = lambda : self.MarkOnAll(self.InvertMark),accelerator="Ctrl+I, *")
            cAll.add_separator()

            MarkCascadePath = Menu(cAll, tearoff = 0,bg=self.bg)
            UnmarkCascadePath = Menu(cAll, tearoff = 0,bg=self.bg)

            row=0
            for path in self.D.ScannedPaths:
                MarkCascadePath.add_command(label = self.Numbers[row] + '  =  ' + path,    command  = lambda pathpar=path: self.ActionOnSpecifiedPath(pathpar,self.SetMark,True) ,accelerator="Ctrl+"+str(row+1) )
                UnmarkCascadePath.add_command(label = self.Numbers[row] + '  =  ' + path,  command  = lambda pathpar=path: self.ActionOnSpecifiedPath(pathpar,self.UnsetMark,True) ,accelerator="Ctrl+Shift+"+str(row+1) )
                row+=1

            cAll.add_command(label = "Mark on specified directory ...",   command = lambda : self.MarkSubpath(self.SetMark,True))
            cAll.add_command(label = "Unmark on specified directory ...",   command = lambda : self.MarkSubpath(self.UnsetMark,True))
            cAll.add_separator()

            cAll.add_cascade(label = "Mark on scan path",             menu = MarkCascadePath)
            cAll.add_cascade(label = "Unmark on scan path",             menu = UnmarkCascadePath)
            cAll.add_separator()

            cAll.add_command(label = 'Remove Marked Files',command=lambda : self.ProcessFilesTreeCrcWrapper(DELETE,1),accelerator="Ctrl+Delete",state=MarksState)
            cAll.entryconfig(21,foreground='red',activeforeground='red')
            cAll.add_command(label = 'Softlink Marked Files',command=lambda : self.ProcessFilesTreeCrcWrapper(SOFTLINK,1),accelerator="Ctrl+Insert",state=MarksState)
            cAll.entryconfig(22,foreground='red',activeforeground='red')
            cAll.add_command(label = 'Hardlink Marked Files',command=lambda : self.ProcessFilesTreeCrcWrapper(HARDLINK,1),accelerator="Ctrl+Shift+Insert",state=MarksState)
            cAll.entryconfig(23,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'All Files',menu = cAll,state=ItemActionsState)

            cNav = Menu(self.menubar,tearoff=0,bg=self.bg)
            cNav.add_command(label = 'go to dominant group (by size sum)',command = lambda : self.GoToMaxGroup(1), accelerator="F7")
            cNav.add_command(label = 'go to dominant group (by quantity)',command = lambda : self.GoToMaxGroup(0), accelerator="F8")

        else:
            DirActionsState=('disabled','normal')[self.SelKind==DIR]

            cLocal = Menu(pop,tearoff=0,bg=self.bg)
            cLocal.add_command(label = "Toggle Mark",  command = lambda : self.ToggleSelectedTag(tree,self.SelItem),accelerator="space",state=FileActionsState)
            cLocal.add_separator()
            cLocal.add_command(label = "Mark all files",        command = lambda : self.MarkLowerPane(self.SetMark),accelerator="A",state=FileActionsState)
            cLocal.add_command(label = "Unmark all files",        command = lambda : self.MarkLowerPane(self.UnsetMark),accelerator="N",state=FileActionsState)
            cLocal.add_separator()
            cLocal.add_command(label = 'Mark By Expression',command = lambda : self.MarkExpression(self.SetMark,'Mark files'),accelerator="+")
            cLocal.add_command(label = 'Unmark By Expression',command = lambda : self.MarkExpression(self.UnsetMark,'Unmark files'),accelerator="-")
            cLocal.add_separator()

            MarksState=('disabled','normal')[len(tree.tag_has(MARK))!=0]

            cLocal.add_command(label = 'Remove Marked Files',command=lambda : self.ProcessFilesTreeFolderWrapper(DELETE,0),accelerator="Delete",state=MarksState)
            cLocal.add_command(label = 'Softlink Marked Files',command=lambda : self.ProcessFilesTreeFolderWrapper(SOFTLINK,0),accelerator="Insert",state=MarksState)
            #cLocal.add_command(label = 'Hardlink Marked Files',command=lambda : self.ProcessFilesTreeFolderWrapper(HARDLINK,0),accelerator="Shift+Insert",state=MarksState)

            cLocal.entryconfig(8,foreground='red',activeforeground='red')
            cLocal.entryconfig(9,foreground='red',activeforeground='red')
            #cLocal.entryconfig(10,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'Local (this folder)',menu = cLocal,state=ItemActionsState)
            pop.add_separator()

            cSelSub = Menu(pop,tearoff=0,bg=self.bg)
            cSelSub.add_command(label = "Mark All Duplicates in Subdirectory",  command = lambda : self.SelDir(self.SetMark),accelerator="D",state=DirActionsState)
            cSelSub.add_command(label = "Unmark All Duplicates in Subdirectory",  command = lambda : self.SelDir(self.UnsetMark),accelerator="Shift+D",state=DirActionsState)
            cSelSub.add_separator()

            cSelSub.add_command(label = 'Remove Marked Files in Subdirectory Tree',command=lambda : self.ProcessFilesTreeFolderWrapper(DELETE,True),accelerator="Delete",state=DirActionsState)
            cSelSub.add_command(label = 'Softlink Marked Files in Subdirectory Tree',command=lambda : self.ProcessFilesTreeFolderWrapper(SOFTLINK,True),accelerator="Insert",state=DirActionsState)
            #cSelSub.add_command(label = 'Hardlink Marked Files in Subdirectory Tree',command=lambda : self.ProcessFilesTreeFolderWrapper(HARDLINK,True),accelerator="Shift+Insert",state=DirActionsState)

            cSelSub.entryconfig(3,foreground='red',activeforeground='red')
            cSelSub.entryconfig(4,foreground='red',activeforeground='red')
            #cSelSub.entryconfig(5,foreground='red',activeforeground='red')
            #cSelSub.add_separator()
            #cSelSub.add_command(label = 'Remove Empty Folders in Subdirectory Tree',command=lambda : self.RemoveEmptyFolders(),state=DirActionsState)

            pop.add_cascade(label = 'Selected Subdirectory',menu = cSelSub,state=DirActionsState)

            cNav = Menu(pop,tearoff=0,bg=self.bg)
            cNav.add_command(label = 'go to dominant folder (by size sum)',command = lambda : self.GoToMaxFolder(1),accelerator="F5")
            cNav.add_command(label = 'go to dominant folder (by quantity)',command = lambda : self.GoToMaxFolder(0) ,accelerator="F6")
            #cNav.add_separator()
            #cNav.add_command(label = 'Go to dominant folder (by duplicates/other files size ratio)',command = lambda : self.GoToMaxFolder(1,1),accelerator="Backspace")
            #cNav.add_command(label = 'Go to dominant folder (by duplicates/other files quantity ratio)',command = lambda : self.GoToMaxFolder(0,1) ,accelerator="Ctrl+Backspace")

        pop.add_separator()
        pop.add_cascade(label = 'Navigation',menu = cNav,state=ItemActionsState)

        pop.add_separator()
        pop.add_command(label = 'Open File',command = self.TreeEventOpenFile,accelerator="Return",state=FileActionsState)
        pop.add_command(label = 'Open Folder',command = self.OpenFolder,state=FileActionsState)

        pop.add_separator()
        pop.add_command(label = "Scan",  command = self.ScanDialogShow,accelerator="S")
        pop.add_command(label = "Settings",  command = self.SettingsDialogShow,accelerator="F2")
        pop.add_separator()
        pop.add_command(label = 'Copy',command = self.ClipCopyFullWithFile,accelerator="Ctrl+C",state = 'normal' if self.SelItem!=None else 'disabled')
        pop.add_command(label = 'Copy only path',command = self.ClipCopyFull,accelerator="C",state = 'normal' if self.SelItem!=None else 'disabled')
        pop.add_separator()
        pop.add_command(label = 'Find',command = self.FindDialogShow,accelerator="F",state = 'normal' if self.SelItem!=None else 'disabled')
        pop.add_command(label = 'Find Next',command = self.FindNext,accelerator="F3",state = 'normal' if self.SelItem!=None else 'disabled')
        pop.add_command(label = 'Find Prev',command = self.FindPrev,accelerator="Shift+F3",state = 'normal' if self.SelItem!=None else 'disabled')
        pop.add_separator()

        pop.add_command(label = "Exit",  command = self.exit)

        try:
            pop.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            print(e)

        pop.grab_release()

    def RemoveEmptyFoldersAsk(self):
        if res:=tk.filedialog.askdirectory(title='Select Directory',initialdir=self.cwd,parent=self.main):
            FinalInfo = self.EmptyDirsRemoval(res,True)

            self.Info('Removed empty directories','\n'.join(FinalInfo),self.main,textwidth=160,width=800)

            self.TreeFolderUpdate(self.SelFullPath)

    def SelDir(self,action):
        self.ActionOnSpecifiedPath(self.SelFullPathToFile,action,True)

    def ColumnSortClick(self, tree, colname):
        prev_colname,prev_reverse=self.ColumnSortLastParams[tree]
        reverse = not prev_reverse if colname == prev_colname else prev_reverse
        tree.heading(prev_colname, text=self.OrgLabel[prev_colname])

        self.ColumnSortLastParams[tree]=[colname,reverse]

        if tree == self.TreeFolder:
            self.FolderItemsCache={}

        self.ColumnSort (tree)

    @MainWatchCursor
    @StatusLineRestore
    def ColumnSort(self, tree):
        self.StatusLine.set('Sorting...')
        colname,reverse = self.ColumnSortLastParams[tree]

        RealSortColumn=self.col2sortOf[colname]

        UPDIRCode,DIRCode,NONDIRCode = (2,1,0) if reverse else (0,1,2)

        l = [((UPDIRCode if tree.set(item,'kind')==UPDIR else DIRCode if tree.set(item,'kind')==DIR else NONDIRCode,tree.set(item,RealSortColumn)), item) for item in tree.get_children('')]
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

        if tree==self.TreeGroups:
            self.TreeGroupsFlatItemsToupleUpdate()

    def addPath(self,path):
        if len(self.PathsToScanFromDialog)<10:
            self.PathsToScanFromDialog.append(path)
            self.UpdatePathsToScan()
        else:
            logging.error(f'can\'t add:{path}. limit exceeded')

    @StatusLineRestore
    def Scan(self):
        self.StatusLine.set('Scanning...')
        self.cfg.Write()

        self.D.INIT()
        self.StatusVarFullPath.set('')
        self.ShowGroups()

        PathsToScanFromEntry = [var.get() for var in self.PathsToScanEntryVar.values()]
        ExcludeVarsFromEntry = [var.get() for var in self.ExcludeEntryVar.values()]

        if not PathsToScanFromEntry:
            self.DialogWithEntry(title='Error. No paths to scan.',prompt='Add paths to scan.',parent=self.ScanDialog,OnlyInfo=True)

        if res:=self.D.SetPathsToScan(PathsToScanFromEntry):
            self.Info('Error. Fix paths selection.',res,self.ScanDialog)
            return

        if res:=self.D.SetExcludeMasks(self.cfg.GetBool(CFG_KEY_EXCLUDE_REGEXP),ExcludeVarsFromEntry):
            self.Info('Error. Fix Exclude masks.',res,self.ScanDialog)
            return

        self.cfg.Set(CFG_KEY_EXCLUDE,'|'.join(ExcludeVarsFromEntry))

        self.main.update()

        #############################

        self.LongActionDialogShow(self.ScanDialogMainFrame,'Scanning')

        ScanThread=Thread(target=self.D.Scan,daemon=True)
        ScanThread.start()

        while ScanThread.is_alive():
            self.LongActionDialogUpdate(self.Numbers[self.D.InfoPathNr] + '\n' + self.D.InfoPathToScan + '\n\n' + str(self.D.InfoCounter) + '\n' + core.bytes2str(self.D.InfoSizeSum))

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
        self.StatusLine.set('Calculating CRC ...')
        self.LongActionDialogShow(self.ScanDialogMainFrame,'CRC calculation','determinate','determinate',Progress1LeftText='Total size:',Progress2LeftText='Files number:')

        self.D.writeLog=self.WriteScanToLog.get()

        CrcThread=Thread(target=self.D.CrcCalc,daemon=True)
        CrcThread.start()

        #+ '\nAvarage file size: ' + core.bytes2str(self.D.InfoAvarageSize) \
        while CrcThread.is_alive():
            info =  'Threads: ' + self.D.InfoThreads \
                    + '\nAvarage speed: ' + core.bytes2str(self.D.infoSpeed,1) + '/s' \
                    + '\n\nFound:' \
                    + '\nCRC groups: ' + str(self.D.InfoFoundGroups) \
                    + '\nfolders: ' + str(self.D.InfoFoundFolders) \
                    + '\nspace: ' + core.bytes2str(self.D.InfoDuplicatesSpace)

            InfoProgSize=float(100)*float(self.D.InfoSizeDone)/float(self.D.sumSize)
            InfoProgQuant=float(100)*float(self.D.InfoFileDone)/float(self.D.InfoTotal)

            progress1Right=core.bytes2str(self.D.InfoSizeDone) + '/' + core.bytes2str(self.D.sumSize)
            progress2Right=str(self.D.InfoFileDone) + '/' + str(self.D.InfoTotal)

            self.LongActionDialogUpdate(info,InfoProgSize,InfoProgQuant,progress1Right,progress2Right,self.D.InfoLine)

            if self.D.CanAbort:
                if self.LongActionAbort:
                    self.D.Abort()
            else:
                self.ScanDialog.config(cursor="watch")
                self.StatusLine.set(self.D.Info)

            time.sleep(0.04)

        CrcThread.join()
        #############################

        if self.LongActionAbort:
            self.DialogWithEntry(title='CRC Calculation aborted.',prompt='\nResults are partial.\nSome files may remain unidentified as duplicates.',parent=self.LongActionDialog,OnlyInfo=True,width=300,height=200)

        self.LongActionDialogEnd()

        self.ScanDialog.config(cursor="watch")
        self.ShowGroups()
        self.ScanDialogClose()
        self.ScanDialog.config(cursor="")

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
            #self.AddDrivesButton.configure(state=DISABLED,text='')
            self.ClearListButton.focus_set()
        else:
            self.AddPathButton.configure(state=NORMAL,text='Add path ...')
            #self.AddDrivesButton.configure(state=NORMAL,text='Add drives ...')

    def ScanExcludeRegExprCommand(self):
        self.cfg.SetBool(CFG_KEY_EXCLUDE_REGEXP,self.ScanExcludeRegExpr.get())

    def UpdateExcludeMasks(self) :
        for subframe in self.ExcludeFrames:
            subframe.destroy()

        self.ExcludeFrames=[]
        self.ExcludeEntryVar={}

        ttk.Checkbutton(self.ExcludeFRame,text='Use regular expressions matching',variable=self.ScanExcludeRegExpr,command=lambda : self.ScanExcludeRegExprCommand()).grid(row=0,column=0,sticky='news',columnspan=3,padx=5)

        row=1

        for entry in self.cfg.Get(CFG_KEY_EXCLUDE,'').split('|'):
            if entry:
                (fr:=tk.Frame(self.ExcludeFRame,bg=self.bg)).grid(row=row,column=0,sticky='news',columnspan=3)
                self.ExcludeFrames.append(fr)

                self.ExcludeEntryVar[row]=tk.StringVar(value=entry)
                ttk.Entry(fr,textvariable=self.ExcludeEntryVar[row]).pack(side='left',expand=1,fill='both',pady=1)

                ttk.Button(fr,text='❌',command=lambda entrypar=entry: self.RemoveExcludeMask(entrypar),width=3).pack(side='right',padx=2,pady=1,fill='y')

                row+=1

    #def AddDrives(self):

        #for (device,mountpoint,fstype,opts,maxfile,maxpath) in psutil.disk_partitions():
        #    if fstype != 'squashfs':
        #        self.addPath(mountpoint)

    #    if windows:
    #        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    #            if os.path.exists(f'{drive_letter}:'):
    #                self.addPath(f'{drive_letter}:')
    #    else:
    #        pass

    def AddPathDialog(self):
        if res:=tk.filedialog.askdirectory(title='Select Directory',initialdir=self.cwd,parent=self.ScanDialogMainFrame):
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
        pass
        #if event.widget==self.main:
            #self.FolderItemsCache={}

    def License(self):
        self.Info('License',self.license,self.main,textwidth=80,width=600)

    def About(self):
        info=[]
        info.append('==============================================================================')
        info.append('                                                                              ')
        info.append(f'                       DUDE (DUplicates DEtector) v{VERSION}                 ')
        info.append('                            Author: Piotr Jochymek                            ')
        info.append('                                                                              ')
        info.append('                        https://github.com/PJDude/dude                        ')
        info.append('                        https://pjdude.github.io/dude/                        ')
        info.append('                                                                              ')
        info.append('                            PJ.soft.dev.x@gmail.com                           ')
        info.append('                                                                              ')
        info.append('==============================================================================')
        info.append('                                                                              ')
        info.append('LOGS DIRECTORY     :  '+LOG_DIR)
        info.append('SETTINGS DIRECTORY :  '+CONFIG_DIR)
        info.append('CACHE DIRECTORY    :  '+CACHE_DIR)
        info.append('                                                                              ')
        info.append('LOGGING LEVEL      :  '+ LoggingLevels[LoggingLevel] )
        info.append('                                                                              ')
        info.append('Current log file   :  '+log)

        self.Info('About DUDE','\n'.join(info),self.main,textwidth=80,width=600)

    def KeyboardShortcuts(self):
        self.Info('Keyboard Shortcuts',self.keyboardshortcuts,self.main,textwidth=80,width=600)

    def StoreSplitter(self):
        try:
            coords=self.paned.sash_coord(0)
            self.cfg.Set('sash_coord',str(coords[1]),section='geometry')
            self.cfg.Write()
        except Exception as e:
            logging.error(e)

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

        {var.set(self.cfg.GetBool(key)) for var,key in self.settings}

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
        self.cfg.SetBool(CFG_KEY_STARTUP_ADD_CWD,self.AddCwdAtStartup.get())
        self.cfg.SetBool(CFG_KEY_STARTUP_SCAN,self.ScanAtStartup.get())

        update1=False
        update2=False

        if self.cfg.GetBool(CFG_KEY_FULL_CRC)!=self.FullCRC.get():
            self.cfg.SetBool(CFG_KEY_FULL_CRC,self.FullCRC.get())
            update1=True
            update2=True
            self.FolderItemsCache={}

        if self.cfg.GetBool(CFG_KEY_FULL_PATHS)!=self.FullPaths.get():
            self.cfg.SetBool(CFG_KEY_FULL_PATHS,self.FullPaths.get())
            update1=True
            update2=True

        if self.cfg.GetBool(CFG_KEY_REL_SYMLINKS)!=self.RelSymlinks.get():
            self.cfg.SetBool(CFG_KEY_REL_SYMLINKS,self.RelSymlinks.get())

        if self.cfg.GetBool(ERASE_EMPTY_DIRS)!=self.EraseEmptyDirs.get():
            self.cfg.SetBool(ERASE_EMPTY_DIRS,self.EraseEmptyDirs.get())

        if self.cfg.GetBool(CFG_ALLOW_DELETE_ALL)!=self.AllowDeleteAll.get():
            self.cfg.SetBool(CFG_ALLOW_DELETE_ALL,self.AllowDeleteAll.get())

        if self.cfg.GetBool(CFG_SKIP_INCORRECT_GROUPS)!=self.SkipIncorrectGroups.get():
            self.cfg.SetBool(CFG_SKIP_INCORRECT_GROUPS,self.SkipIncorrectGroups.get())

        if self.cfg.GetBool(CFG_ALLOW_DELETE_NON_DUPLICATES)!=self.AllowDeleteNonDuplicates.get():
            self.cfg.SetBool(CFG_ALLOW_DELETE_NON_DUPLICATES,self.AllowDeleteNonDuplicates.get())

        if self.cfg.GetBool(CFG_CONFIRM_SHOW_CRCSIZE)!=self.ConfirmShowCrcSize.get():
            self.cfg.SetBool(CFG_CONFIRM_SHOW_CRCSIZE,self.ConfirmShowCrcSize.get())

        if self.cfg.GetBool(CFG_CONFIRM_SHOW_LINKSTARGETS)!=self.ConfirmShowLinksTargets.get():
            self.cfg.SetBool(CFG_CONFIRM_SHOW_LINKSTARGETS,self.ConfirmShowLinksTargets.get())

        self.cfg.Write()

        if update1:
            self.TreeGroupsCrcAndPathUpdate()

        if update2:
            if self.SelCrc and self.SelItem and self.SelFullPath:
                self.TreeFolderUpdate()
            else:
                self.TreeFolderUpdateNone()

        self.SettingsDialogClose()

    def SettingsDialogReset(self):
        {var.set(CfgDefaults[key]) for var,key in self.settings}

    def UpdateCrcNode(self,crc):
        size=int(self.TreeGroups.set(crc,'size'))

        CrcRemoved=False
        if not size in self.D.filesOfSizeOfCRC:
            self.TreeGroups.delete(crc)
            logging.debug('UpdateCrcNode-1 ' + crc)
            CrcRemoved=True
        elif crc not in self.D.filesOfSizeOfCRC[size]:
            self.TreeGroups.delete(crc)
            logging.debug('UpdateCrcNode-2 ' + crc)
            CrcRemoved=True
        else:
            crcDict=self.D.filesOfSizeOfCRC[size][crc]
            for item in list(self.TreeGroups.get_children(crc)):
                IndexTuple=self.GetIndexTupleTreeGroups(item)

                if IndexTuple not in crcDict:
                    self.TreeGroups.delete(item)
                    logging.debug('UpdateCrcNode-3 ' + item)

            if not self.TreeGroups.get_children(crc):
                self.TreeGroups.delete(crc)
                logging.debug('UpdateCrcNode-4 ' + crc)
                CrcRemoved=True

    def DataPrecalc(self):
        self.ByIdCtimeCache = { (self.idfunc(inode,dev),ctime):(crc,self.D.crccut[crc],len(self.D.filesOfSizeOfCRC[size][crc]) ) for size,sizeDict in self.D.filesOfSizeOfCRC.items() for crc,crcDict in sizeDict.items() for pathnr,path,file,ctime,dev,inode in crcDict }
        self.StatusVarGroups.set(len(self.TreeGroups.get_children()))

        PathStatSize={}
        PathStatQuant={}

        self.BiggestFileOfPath={}
        self.BiggestFileOfPathId={}

        for size,sizeDict in self.D.filesOfSizeOfCRC.items() :
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
        self.GroupsCombosSize = tuple(sorted([(crcitem,sum([int(self.TreeGroups.set(item,'size')) for item in self.TreeGroups.get_children(crcitem)])) for crcitem in self.TreeGroups.get_children()],key = lambda x : x[1],reverse = True))
        self.GroupsCombosQuant = tuple(sorted([(crcitem,len(self.TreeGroups.get_children(crcitem))) for crcitem in self.TreeGroups.get_children()],key = lambda x : x[1],reverse = True))

        self.PathsQuant=len(self.PathStatListSize)
        self.GroupsCombosLen=len(self.GroupsCombosSize)

    def TreeGroupsFlatItemsToupleUpdate(self):
        self.TreeGroupsFlatItemsTouple = tuple([elem for sublist in [ tuple([crc])+tuple(self.TreeGroups.get_children(crc)) for crc in self.TreeGroups.get_children() ] for elem in sublist])

    def InitialFocus(self):
        if self.TreeGroups.get_children():
            firstNodeFile=next(iter(self.TreeGroups.get_children(next(iter(self.TreeGroups.get_children())))))
            self.TreeGroups.focus_set()
            self.TreeGroups.focus(firstNodeFile)
            self.TreeGroups.see(firstNodeFile)
            self.TreeGroupsSelChange(firstNodeFile)

            self.TreeGroupsCrcAndPathUpdate()
        else:
            self.TreeFolderUpdateNone()
            self.ResetSels()

    @MainWatchCursor
    @StatusLineRestore
    def ShowGroups(self):
        self.StatusLine.set('Rendering data...')
        self.idfunc = (lambda i,d : '%s-%s'%(i,d)) if len(self.D.devs)>1 else (lambda i,d : str(i))

        self.ResetSels()
        self.TreeGroups.delete(*self.TreeGroups.get_children())

        for size,sizeDict in self.D.filesOfSizeOfCRC.items() :
            SizeBytes = core.bytes2str(size)
            for crc,crcDict in sizeDict.items():
                crcitem=self.TreeGroups.insert(parent='', index=END,iid=crc, values=('','','',size,SizeBytes,'','','',crc,len(crcDict),'',CRC),tags=[CRC],open=True)

                for pathnr,path,file,ctime,dev,inode in crcDict:
                    self.TreeGroups.insert(parent=crcitem, index=END,iid=self.idfunc(inode,dev), values=(\
                            pathnr,path,file,size,\
                            '',\
                            ctime,dev,inode,crc,\
                            '',\
                            time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime)) ,FILE),tags=())

        self.DataPrecalc()

        self.ColumnSort(self.TreeGroups)
        self.TreeGroupsFlatItemsToupleUpdate() #after sort !
        self.InitialFocus()
        self.CalcMarkStatsAll()

    def TreeGroupsCrcAndPathUpdate(self):
        FullCRC=self.cfg.GetBool(CFG_KEY_FULL_CRC)
        FullPaths=self.cfg.GetBool(CFG_KEY_FULL_PATHS)

        for size,sizeDict in self.D.filesOfSizeOfCRC.items() :
            for crc,crcDict in sizeDict.items():
                self.TreeGroups.item(crc,text=crc if FullCRC else self.D.crccut[crc])
                for pathnr,path,file,ctime,dev,inode in crcDict:
                    self.TreeGroups.item(self.idfunc(inode,dev),text=self.D.ScannedPaths[pathnr] if FullPaths else self.Numbers[pathnr])

    def UpdateMainTreeNone(self):
        self.TreeGroups.selection_remove(self.TreeGroups.selection())

    def UpdateMainTree(self,item):
        self.TreeGroups.see(self.SelCrc)
        self.TreeGroups.update()

        self.TreeGroups.selection_set(item)
        self.TreeGroups.see(item)
        self.TreeGroups.update()

    def TreeFolderUpdateNone(self):
        self.TreeFolder.delete(*self.TreeFolder.get_children())
        self.CalcMarkStatsPath()
        self.StatusVarPathSize.set('')
        self.StatusVarPathQuant.set('')

        self.StatusVarFullPath.set("")
        self.StatusVarFullPathLabel.config(fg = 'black')

    sortIndexDict={'file':1,'sizeH':2,'ctimeH':3,'instances':8}
    kindIndex=11

    def TwoDotsConditionWin(self):
        return True if self.SelFullPath.split(os.sep)[1]!='' else  False

    def TwoDotsConditionLin(self):
        return True if self.SelFullPath!='/' else  False

    TwoDotsConditionOS = TwoDotsConditionWin if windows else TwoDotsConditionLin

    @MainWatchCursor
    def TreeFolderUpdate(self,ArbitraryPath=None):
        CurrentPath=ArbitraryPath if ArbitraryPath else self.SelFullPath

        if not CurrentPath:
            return False

        Refresh=True
        DirCtime=0

        try:
            TopStat = os.stat(CurrentPath)
        except Exception as e:
            print(f'{CurrentPath},{file},{e}')
            print(EPrint(e))
            logging.error(f'ERROR: ,{e}')
        else:
            DirCtime=round(TopStat.st_ctime)

            if CurrentPath in self.FolderItemsCache:
                if DirCtime==self.FolderItemsCache[CurrentPath][0]:
                    Refresh=False

        if Refresh :
            RefreshScandir=True

            if CurrentPath in self.FolderScandirCache:
                if DirCtime==self.FolderScandirCache[CurrentPath][0]:
                    RefreshScandir=False

            if RefreshScandir:
                try:
                    ScanDirRes=tuple(os.scandir(CurrentPath))
                except Exception as e:
                    self.StatusLine.set(str(e))
                    logging.error(e)
                    return False
                else:
                    self.FolderScandirCache[CurrentPath]=(DirCtime,ScanDirRes)

            FolderItems=[]

            FullCRC=self.cfg.GetBool(CFG_KEY_FULL_CRC)

            i=0
            for DirEntry in self.FolderScandirCache[CurrentPath][1]:
                file=DirEntry.name

                TopStat

                try:
                    stat = os.stat(os.path.join(CurrentPath,file))
                except Exception as e:
                    self.StatusLine.set(str(e))
                    print(f'{CurrentPath},{file},{e}')
                    print(EPrint(e))
                    logging.error(f'ERROR: ,{e}')
                    continue

                if os.path.islink(DirEntry) :
                    if DirEntry.is_dir():
                        FolderItems.append( ( '\t📁 ⇦',file,0,0,0,0,'','',1,0,DIR,DIR,'%sDL' % i,'','' ) )
                    else:
                        FolderItems.append( ( '\t  🠔',file,0,round(stat.st_ctime),stat.st_dev,stat.st_ino,'','',1,0,LINK,LINK,'%sFL' % i,'','' ) )
                elif DirEntry.is_dir():
                    FolderItems.append( ('\t📁',file,0,0,0,0,'','',1,0,DIR,DIR,'%sD' % i,'','' ) )
                elif DirEntry.is_file():

                    ctime=round(stat.st_ctime)
                    dev=stat.st_dev
                    inode=stat.st_ino
                    size=stat.st_size
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
                                                    None, \
                                                    FILE,\
                                                    FILEID,\
                                                    core.bytes2str(size),\
                                                    time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime) ) \
                                            )  )
                    else:
                        if stat.st_nlink!=1:
                            #hardlink
                            FolderItems.append( ( '\t ✹',file,size,ctime,dev,inode,'','',1,FILEID,SINGLE,SINGLEHARDLINKED,'%sO' % i,core.bytes2str(size),time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime) ) ) )
                        else:
                            FolderItems.append( ( '',file,size,ctime,dev,inode,'','',1,FILEID,SINGLE,SINGLE,'%sO' % i,core.bytes2str(size),time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime) ) ) )
                else:
                    logging.error(f'what is it: {DirEntry} ?')

                i+=1

            ############################################################
            colSort,reverse = self.ColumnSortLastParams[self.TreeFolder]
            sortIndex=self.sortIndexDict[colSort]
            IsNumeric=self.col2sortNumeric[colSort]

            UPDIRCode,DIRCode,NONDIRCode = (2,1,0) if reverse else (0,1,2)
            ############################################################

            self.FolderItemsCache[CurrentPath]=(DirCtime,tuple(sorted(FolderItems,key=lambda x : (UPDIRCode if x[self.kindIndex]==UPDIR else DIRCode if x[self.kindIndex]==DIR else NONDIRCode,float(x[sortIndex])) if IsNumeric else (UPDIRCode if x[self.kindIndex]==UPDIR else DIRCode if x[self.kindIndex]==DIR else NONDIRCode,x[sortIndex]),reverse=reverse)))

#            print('full dir processing:%s %s' % (Refresh,CurrentPath))
#        else :
#            print('using cache !')

        if ArbitraryPath:
            #TODO - workaround
            prevSelPath=self.SelPath
            self.ResetSels()
            self.SelPath=prevSelPath
            self.SetSelPath(str(pathlib.Path(ArbitraryPath)))

        self.TreeFolder.delete(*self.TreeFolder.get_children())

        if self.TwoDotsConditionOS():
            #always at the beginning
            #(text,file,size,ctime,dev,inode,crc,instances,instancesnum,FILEID,tags,kind,iid,sizeH)=('','..',0,0,0,0,'..','',1,0,DIR,UPDIR,'0UP','' )
            #self.TreeFolder.insert(parent="", index=END, iid=iid , text=text, values=(self.SelPathnrInt,self.SelPath,file,size,sizeH,ctime,dev,inode,crc,instances,instancesnum,'',kind),tags=tags)
            #self.SelPathnrInt,self.SelPath,file,size,sizeH,ctime,dev,inode,crc,instances,instancesnum,ctimeH,kind
            self.TreeFolder.insert(parent="", index=END, iid='0UP' , text='', values=(self.SelPathnrInt,self.SelPath,'..',0,'',0,0,0,'..','',0,'',UPDIR),tags=DIR)

        for (text,file,size,ctime,dev,inode,crc,instances,instancesnum,FILEID,tags,kind,iid,sizeH,ctimeH) in self.FolderItemsCache[CurrentPath][1]:
            #cant cache tags!

            #(self.SelPathnrInt,self.SelPath) + (file,size,sizeH,ctime,dev,inode,crc,instances,instancesnum,ctimeH,kind)
            self.TreeFolder.insert(parent="", index=END, iid=iid , text=text, values=('','',file,size,sizeH,ctime,dev,inode,crc,instances,instancesnum,ctimeH,kind),tags=self.TreeGroups.item(FILEID)['tags'] if kind==FILE else tags)

        self.TreeFolderFlatItemsList=self.TreeFolder.get_children()

        if not ArbitraryPath:
            if self.SelItem and self.SelItem in self.TreeFolder.get_children():
                self.TreeFolder.selection_set(self.SelItem)
                self.TreeFolder.see(self.SelItem)

        self.CalcMarkStatsPath()

        return True

    def TreeFolderUpdateMarks(self):
        for item in self.TreeFolder.get_children():
            if self.TreeFolder.set(item,'kind')==FILE:
                self.TreeFolder.item( item,tags=self.TreeGroups.item(item)['tags'] )

    def CalcMarkStatsAll(self):
        self.CalcMarkStatsCore(self.TreeGroups,self.StatusVarAllSize,self.StatusVarAllQuant)
        self.SetCommonVarFg()

    def CalcMarkStatsPath(self):
        self.CalcMarkStatsCore(self.TreeFolder,self.StatusVarPathSize,self.StatusVarPathQuant)

    def CalcMarkStatsCore(self,tree,varSize,varQuant):
        marked=tree.tag_has(MARK)
        varQuant.set(len(marked))
        varSize.set(core.bytes2str(sum(int(tree.set(item,'size')) for item in marked)))

    def MarkInSpecifiedCRCGroupByCTime(self, action, crc, reverse,select=False):
        item=sorted([ (item,self.TreeGroups.set(item,'ctime') ) for item in self.TreeGroups.get_children(crc)],key=lambda x : float(x[1]),reverse=reverse)[0][0]
        if item:
            action(item,self.TreeGroups)
            if select:
                self.TreeGroups.see(item)
                self.TreeGroups.focus(item)
                self.TreeGroupsSelChange(item)
                self.TreeGroups.update()

    @MainWatchCursor
    def MarkOnAllByCTime(self,orderStr, action):
        reverse=1 if orderStr=='oldest' else 0

        { self.MarkInSpecifiedCRCGroupByCTime(action, crc, reverse) for crc in self.TreeGroups.get_children() }
        self.TreeFolderUpdateMarks()
        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    @MainWatchCursor
    def MarkInCRCGroupByCTime(self,orderStr,action):
        reverse=1 if orderStr=='oldest' else 0
        self.MarkInSpecifiedCRCGroupByCTime(action,self.SelCrc,reverse,True)
        self.TreeFolderUpdateMarks()
        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    def MarkInSpecifiedCRCGroup(self,action,crc):
        { action(item,self.TreeGroups) for item in self.TreeGroups.get_children(crc) }

    @MainWatchCursor
    def MarkInCRCGroup(self,action):
        self.MarkInSpecifiedCRCGroup(action,self.SelCrc)
        self.TreeFolderUpdateMarks()
        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    @MainWatchCursor
    def MarkOnAll(self,action):
        { self.MarkInSpecifiedCRCGroup(action,crc) for crc in self.TreeGroups.get_children() }
        self.TreeFolderUpdateMarks()
        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    def ActionOnPathPane(self,action,items):
        { (action(item,self.TreeFolder),action(item,self.TreeGroups)) for item in items if self.TreeFolder.set(item,'kind')==FILE }

        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    @MainWatchCursor
    def MarkLowerPane(self,action):
        { (action(item,self.TreeFolder),action(item,self.TreeGroups)) for item in self.TreeFolder.get_children() if self.TreeFolder.set(item,'kind')==FILE }

        self.CalcMarkStatsAll()
        self.CalcMarkStatsPath()

    def SetMark(self,item,tree):
        tree.item(item,tags=[MARK])

    def UnsetMark(self,item,tree):
        tree.item(item,tags=())

    def InvertMark(self,item,tree):
        tree.item(item,tags=() if tree.item(item)['tags'] else [MARK])

    @MainWatchCursor
    def ActionOnSpecifiedPath(self,pathParam,action,AllGroups=True):
        if AllGroups:
            CrcRange = self.TreeGroups.get_children()
        else :
            CrcRange = [str(self.SelCrc)]

        selCount=0
        for crcitem in CrcRange:
            for item in self.TreeGroups.get_children(crcitem):
                fullpath = self.ItemFullPath(item)

                if fullpath.startswith(pathParam + os.sep):
                    action(item,self.TreeGroups)
                    selCount+=1

        if selCount==0 :
            self.DialogWithEntry(title='No files found for specified path', prompt=pathParam,parent=self.main,OnlyInfo=True)
        else:
            self.StatusLine.set(f'Subdirectory action. {selCount} File(s) Found')
            self.TreeFolderUpdateMarks()
            self.CalcMarkStatsAll()
            self.CalcMarkStatsPath()

    TreeExpr={}

    @KeepSemiFocus
    def MarkExpression(self,action,prompt,AllGroups=True):
        tree=self.main.focus_get()

        if tree in self.TreeExpr.keys():
            initialvalue=self.TreeExpr[tree]
        else:
            initialvalue='.*'

        if tree==self.TreeGroups:
            RangeStr = " (all groups)" if AllGroups else " (selected group)"
            title=f'Specify Expression for full file path.'
        else:
            RangeStr = ''
            title='Specify Expression for file names in selected directory.'

        (Expression,UseRegExpr) = self.DialogWithEntry(title=title,prompt=prompt + f'{RangeStr}', initialvalue=initialvalue,parent=self.main,ShowRegExpCheckButton=True)

        items=[]
        UseRegExprInfo = '(regular expression)' if UseRegExpr else ''

        if Expression:
            self.TreeExpr[tree]=Expression

            if tree==self.TreeGroups:

                CrcRange = self.TreeGroups.get_children() if AllGroups else [str(self.SelCrc)]

                for crcitem in CrcRange:
                    for item in self.TreeGroups.get_children(crcitem):
                        fullpath = self.ItemFullPath(item)
                        try:
                            if (UseRegExpr and re.search(Expression,fullpath)) or (not UseRegExpr and fnmatch.fnmatch(fullpath,Expression) ):
                                items.append(item)
                        except Exception as e:
                            self.DialogWithEntry(title='Expression Error !',prompt=f'expression:"{Expression}"  {UseRegExprInfo}\n\nERROR:{e}',parent=self.main,OnlyInfo=True)
                            tree.focus_set()
                            return
            else:
                for item in self.TreeFolder.get_children():
                    if tree.set(item,'kind')==FILE:
                        file=self.TreeFolder.set(item,'file')
                        try:
                            if (UseRegExpr and re.search(Expression,file)) or (not UseRegExpr and fnmatch.fnmatch(file,Expression) ):
                                items.append(item)
                        except Exception as e:
                            self.DialogWithEntry(title='Expression Error !',prompt=f'expression:"{Expression}"  {UseRegExprInfo}\n\nERROR:{e}',parent=self.main,OnlyInfo=True)
                            tree.focus_set()
                            return

            if items:
                self.main.config(cursor="watch")
                self.main.update()

                FirstItem=items[0]

                tree.focus(FirstItem)
                tree.see(FirstItem)

                if tree==self.TreeGroups:
                    for item in items:
                        action(item,tree)

                    self.TreeGroupsSelChange(FirstItem)
                else:
                    for item in items:
                        action(item,self.TreeGroups)
                        action(item,self.TreeFolder)

                    self.TreeFolderSelChange(FirstItem)

                self.TreeFolderUpdateMarks()
                self.CalcMarkStatsAll()
                self.CalcMarkStatsPath()

                self.main.config(cursor="")
                self.main.update()

            else:
                self.DialogWithEntry(title='No files found.',prompt=f'expression:"{Expression}"  {UseRegExprInfo}\n',parent=self.main,OnlyInfo=True)

        tree.focus_set()

    def MarkSubpath(self,action,AllGroups=True):
        if path:=tk.filedialog.askdirectory(title='Select Directory',initialdir=self.cwd):
            self.ActionOnSpecifiedPath(path,action,AllGroups)

    def GotoNextMark(self,tree,direction):
        marked=tree.tag_has(MARK)
        if marked:
            pool=marked if tree.tag_has(MARK,self.SelItem) else self.TreeGroupsFlatItemsTouple if tree==self.TreeGroups else self.TreeFolder.get_children()
            poollen=len(pool)

            if poollen:
                index = pool.index(self.SelItem)

                while True:
                    index=(index+direction)%poollen
                    NextItem=pool[index]
                    if MARK in tree.item(NextItem)['tags']:
                        tree.focus(NextItem)
                        tree.see(NextItem)

                        if tree==self.TreeGroups:
                            self.TreeGroupsSelChange(NextItem)
                        else:
                            self.TreeFolderSelChange(NextItem)

                        break

    def GotoNextDupeFile(self,tree,direction):
        marked=[item for item in tree.get_children() if tree.set(item,'kind')==FILE]
        if marked:
            pool=marked if tree.set(self.SelItem,'kind')==FILE else self.TreeFolder.get_children()
            poollen=len(pool)

            if poollen:
                index = pool.index(self.SelItem)

                while True:
                    index=(index+direction)%poollen
                    NextItem=pool[index]
                    if tree.set(NextItem,'kind')==FILE:
                        tree.focus(NextItem)
                        tree.see(NextItem)

                        if tree==self.TreeGroups:
                            self.TreeGroupsSelChange(NextItem)
                        else:
                            self.TreeFolderSelChange(NextItem)

                        break
    DominantIndexGroups={}
    DominantIndexGroups[0] = -1
    DominantIndexGroups[1] = -1

    DominantIndexFolders={}
    DominantIndexFolders[0] = -1
    DominantIndexFolders[1] = -1

    byWhat={}
    byWhat[0] = "by quantity"
    byWhat[1] = "by sum size"

    @MainWatchCursor
    def GoToMaxGroup(self,sizeFlag=0,Direction=1):
        if self.GroupsCombosLen:
            self.StatusLine.set(f'Setting dominant group ...')
            WorkingIndex = self.DominantIndexGroups[sizeFlag]
            WorkingIndex = (WorkingIndex+Direction) % self.GroupsCombosLen
            temp=str(WorkingIndex)
            WorkingDict = self.GroupsCombosSize if sizeFlag else self.GroupsCombosQuant

            biggestcrc,biggestcrcSizeSum = WorkingDict[WorkingIndex]

            if biggestcrc:
                self.SelectFocusAndSeeCrcItemTree(biggestcrc,True)

                self.DominantIndexGroups[sizeFlag] = int(temp)
                Info = core.bytes2str(biggestcrcSizeSum) if sizeFlag else str(biggestcrcSizeSum)
                self.StatusLine.set(f'Dominant (index:{WorkingIndex}) group ({self.byWhat[sizeFlag]}: {Info})')

    @MainWatchCursor
    def GoToMaxFolder(self,sizeFlag=0,Direction=1):
        if self.PathsQuant:
            self.StatusLine.set(f'Setting dominant folder ...')
            WorkingIndex = self.DominantIndexFolders[sizeFlag]
            WorkingIndex = (WorkingIndex+Direction) % self.PathsQuant
            temp = str(WorkingIndex)
            WorkingDict = self.PathStatListSize if sizeFlag else self.PathStatListQuant

            pathnr,path,num = WorkingDict[WorkingIndex]

            item=self.BiggestFileOfPathId[(pathnr,path)]

            self.TreeGroups.focus(item)
            self.TreeGroupsSelChange(item,ChangeStatusLine=False)

            LastCrcChild=self.TreeGroups.get_children(self.SelCrc)[-1]
            try:
                self.TreeGroups.see(LastCrcChild)
                self.TreeGroups.see(self.SelCrc)
                self.TreeGroups.see(item)
            except Exception :
                pass
            finally:
                self.TreeFolder.update()

            try:
                self.TreeFolder.focus_set()
                self.TreeFolder.focus(item)
                self.TreeFolderSelChange(item,ChangeStatusLine=False)
                self.TreeFolder.see(item)
            except Exception :
                pass
            finally:
                self.UpdateMainTree(item)

            self.DominantIndexFolders[sizeFlag] = int(temp)
            Info = core.bytes2str(num) if sizeFlag else str(num)
            self.StatusLine.set(f'Dominant (index:{WorkingIndex}) folder ({self.byWhat[sizeFlag]}: {Info})')

    def ItemFullPath(self,item):
        pathnr=int(self.TreeGroups.set(item,'pathnr'))
        path=self.TreeGroups.set(item,'path')
        file=self.TreeGroups.set(item,'file')
        return os.path.abspath(self.D.ScannedPathFull(pathnr,path,file))

    def CheckFileState(self,item):
        fullpath = self.ItemFullPath(item)
        logging.info(f'checking file:{fullpath}')
        try:
            stat = os.stat(fullpath)
            ctimeCheck=str(round(stat.st_ctime))
        except Exception as e:
            self.StatusLine.set(str(e))
            mesage = f'can\'t check file: {fullpath}\n\n{e}'
            logging.error(mesage)
            return mesage

        if ctimeCheck != (ctime:=self.TreeGroups.set(item,'ctime')) :
            message = {f'ctime inconsistency {ctimeCheck} vs {ctime}'}
            return message

    def ProcessFilesTreeCrcWrapper(self,action,AllGroups):
        ProcessedItems=defaultdict(list)
        if AllGroups:
            ScopeTitle='All marked files.'
        else:
            ScopeTitle='Single CRC group.'

        for crc in self.TreeGroups.get_children():
            if AllGroups or crc==self.SelCrc:
                for item in self.TreeGroups.get_children(crc):
                    if self.TreeGroups.tag_has(MARK,item):
                        ProcessedItems[crc].append(item)

        return self.ProcessFiles(action,ProcessedItems,ScopeTitle)

    def ProcessFilesTreeFolderWrapper(self,action,OnDirAction=False):
        ProcessedItems=defaultdict(list)
        if OnDirAction:
            ScopeTitle='All marked files on selected directory sub-tree.'

            SelPathWithSep=self.SelFullPathToFile + os.sep
            for crc in self.TreeGroups.get_children():
                for item in self.TreeGroups.get_children(crc):
                    if self.ItemFullPath(item).startswith(SelPathWithSep):
                        if self.TreeGroups.tag_has(MARK,item):
                            ProcessedItems[crc].append(item)
        else:
            ScopeTitle='Selected Directory: ' + self.SelFullPath
            for item in self.TreeFolder.get_children():
                if self.TreeFolder.tag_has(MARK,item):
                    crc=self.TreeFolder.set(item,'crc')
                    ProcessedItems[crc].append(item)

        return self.ProcessFiles(action,ProcessedItems,ScopeTitle)

    @StatusLineRestore
    def ProcessFilesCheckCorrectness(self,action,ProcessedItems,RemainingItems):
        for crc in ProcessedItems:
            size = self.D.Crc2Size[crc]
            (checkres,TuplesToRemove)=self.D.CheckGroupFilesState(size,crc)

            if checkres:
                self.Info('Error. Inconsistent data.','Current filesystem state is inconsistent with scanned data.\n\n' + '\n'.join(checkres) + '\n\nSelected CRC group will be reduced. For complete results re-scanning is recommended.',self.main)
                orglist=self.TreeGroups.get_children()

                self.D.RemoveFromDataPool(size,crc,TuplesToRemove)

                self.UpdateCrcNode(crc)

                self.TreeGroupsFlatItemsToupleUpdate()

                self.DataPrecalc()

                newlist=self.TreeGroups.get_children()
                ItemToSel = self.GimmeClosestInCrc(orglist,crc,newlist)

                self.ResetSels()

                if ItemToSel:
                    #crc node moze zniknac - trzeba zupdejtowac SelXxx
                    self.SelectFocusAndSeeCrcItemTree(ItemToSel,True)
                else:
                    self.InitialFocus()

                self.CalcMarkStatsAll()

        self.StatusLine.set('checking selection correctness...')
        if action==HARDLINK:
            for crc in ProcessedItems:
                if len(ProcessedItems[crc])==1:
                    self.DialogWithEntry(title='Error - Can\'t hardlink single file.',prompt="                    Mark more files.                    ",parent=self.main,OnlyInfo=True)

                    self.SelectFocusAndSeeCrcItemTree(crc,True)
                    return True


        elif action==DELETE:
            if self.cfg.GetBool(CFG_SKIP_INCORRECT_GROUPS):
                IncorrectGroups=[]
                for crc in ProcessedItems:
                    if len(RemainingItems[crc])==0:
                        IncorrectGroups.append(crc)
                if IncorrectGroups:
                    IncorrectGroupsStr='\n'.join(IncorrectGroups)
                    self.Info(f'Warning (Delete) - All files marked',f"Option \"Skip groups with invalid selection\" is enabled.\n\nFolowing CRC groups will not be processed and remain with markings:\n\n{IncorrectGroupsStr}",self.main)

                self.SelectFocusAndSeeCrcItemTree(IncorrectGroups[0],True)
                for crc in IncorrectGroups:
                    del ProcessedItems[crc]
                    del RemainingItems[crc]
            else:
                ShowAllDeleteWarning=False
                for crc in ProcessedItems:
                    if len(RemainingItems[crc])==0:
                        if self.cfg.GetBool(CFG_ALLOW_DELETE_ALL):
                            ShowAllDeleteWarning=True
                        else:
                            self.DialogWithEntry(title=f'Error (Delete) - All files marked',prompt="          Keep at least one file unmarked.          ",parent=self.main,OnlyInfo=True)

                            self.SelectFocusAndSeeCrcItemTree(crc,True)
                            return True

                if ShowAllDeleteWarning:
                    if not self.Ask('Warning !','Option: \'Allow to delete all copies\' is set.|RED\n\nAll copies in one or more groups are selected.|RED\n\nProceed ?|RED',self.main):
                        return True

        elif action==SOFTLINK:
            for crc in ProcessedItems:
                if len(RemainingItems[crc])==0:
                    self.DialogWithEntry(title=f'Error (Softlink) - All files marked',prompt="          Keep at least one file unmarked.          ",parent=self.main,OnlyInfo=True)

                    self.SelectFocusAndSeeCrcItemTree(crc,True)
                    return True

    @StatusLineRestore
    def ProcessFilesCheckCorrectnessLast(self,action,ProcessedItems,RemainingItems):
        self.StatusLine.set('final checking selection correctness')

        if action==HARDLINK:
            for crc in ProcessedItems:
                if len({int(self.TreeGroups.set(item,'dev')) for item in ProcessedItems[crc]})>1:
                    title='Can\'t create hardlinks.'
                    message=f"Files on multiple devices selected. Crc:{crc}"
                    logging.error(title)
                    logging.error(message)
                    self.DialogWithEntry(title=title,prompt=message,parent=self.main,OnlyInfo=True)
                    return True

        for crc in ProcessedItems:
            for item in RemainingItems[crc]:
                if res:=self.CheckFileState(item):
                    self.Info('Error',res+'\n\nNo action was taken.\n\nAborting. Repeat scanning please or unmark all files and groups affected by other programs.',self.main)
                    logging.error('aborting.')
                    return True
        logging.info('remaining files checking complete.')

    @StatusLineRestore
    def ProcessFilesConfirm(self,action,ProcessedItems,RemainingItems,ScopeTitle):
        self.StatusLine.set('confirmation required...')
        ShowFullPath=1

        message=[]
        if not self.cfg.Get(CFG_CONFIRM_SHOW_CRCSIZE,False)=='True':
            message.append('')

        for crc in ProcessedItems:
            if self.cfg.Get(CFG_CONFIRM_SHOW_CRCSIZE,False)=='True':
                size=int(self.TreeGroups.set(crc,'size'))
                message.append('')
                message.append('CRC:' + crc + ' size:' + core.bytes2str(size) + '|GRAY')

            for item in ProcessedItems[crc]:
                message.append((self.ItemFullPath(item) if ShowFullPath else tree.set(item,'file')) + '|RED' )

            if action==SOFTLINK:
                if RemainingItems[crc]:
                    item = RemainingItems[crc][0]
                    if self.cfg.GetBool(CFG_CONFIRM_SHOW_LINKSTARGETS):
                        message.append('🠖 ' + (self.ItemFullPath(item) if ShowFullPath else self.TreeGroups.set(item,'file')) )

        if action==DELETE:
            if not self.Ask('Delete marked files ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return True
        elif action==SOFTLINK:
            if not self.Ask('Soft-Link marked files to first unmarked file in group ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return True
        elif action==HARDLINK:
            if not self.Ask('Hard-Link marked files together in groups ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return True

        {logging.warning(line) for line in message}
        logging.warning('###########################################################################################')
        logging.warning('Confirmed.')

    @MainWatchCursor
    def EmptyDirsRemoval(self,startpath,ReportEmpty=False):
        string=f'Removing empty directories in:\'{startpath}\''
        self.StatusLine.set(string)
        self.main.update()
        logging.info(string)

        Removed=[]
        index=0
        for (path, dirs, files) in os.walk(startpath, topdown=False, followlinks=False):
            string2=f'{string} {self.ProgressSigns[index]}'
            self.StatusLine.set(string2)
            index+=1
            index %= 4
            if not files:
                try:
                    self.main.update()
                    os.rmdir(path)
                    logging.info(f'Empty Removed:{path}')
                    Removed.append(path)
                except Exception as e:
                    logging.error(f'EmptyDirsRemoval:{e}')

        self.StatusLine.set('')

        if ReportEmpty and not Removed:
            Removed.append(f'No empty subdirectories in:\'{startpath}\'')

        return Removed

    def ProcessFilesCore(self,action,ProcessedItems,RemainingItems):
        self.main.config(cursor="watch")
        self.StatusLine.set('processing files ...')
        self.main.update()

        FinalInfo=[]
        if action==DELETE:
            DirectoriesToCheck=set()
            for crc in ProcessedItems:
                TuplesToDelete=set()
                size=int(self.TreeGroups.set(ProcessedItems[crc][0],'size'))
                for item in ProcessedItems[crc]:
                    IndexTuple=self.GetIndexTupleTreeGroups(item)
                    TuplesToDelete.add(IndexTuple)
                    DirectoriesToCheck.add(self.D.GetPath(IndexTuple))

                if resmsg:=self.D.DeleteFileWrapper(size,crc,TuplesToDelete):
                    logging.error(resmsg)
                    self.Info('Error',resmsg,self.main)

                self.UpdateCrcNode(crc)

            if self.cfg.GetBool(ERASE_EMPTY_DIRS):
                DirectoriesToCheckList=list(DirectoriesToCheck)
                DirectoriesToCheckList.sort(key=lambda d : (len(str(d).split(os.sep)),d),reverse=True )

                Removed=[]
                for directory in DirectoriesToCheckList:
                    Removed.extend(self.EmptyDirsRemoval(directory))

                FinalInfo.extend(Removed)

        elif action==SOFTLINK:
            RelSymlink = self.cfg.GetBool(CFG_KEY_REL_SYMLINKS)
            for crc in ProcessedItems:
                toKeepItem=list(RemainingItems[crc])[0]
                #self.TreeGroups.focus()
                IndexTupleRef=self.GetIndexTupleTreeGroups(toKeepItem)
                size=int(self.TreeGroups.set(toKeepItem,'size'))

                if resmsg:=self.D.LinkWrapper(True, RelSymlink, size,crc, IndexTupleRef, [self.GetIndexTupleTreeGroups(item) for item in ProcessedItems[crc] ] ):
                    logging.error(resmsg)
                    self.Info('Error',resmsg,self.main)
                self.UpdateCrcNode(crc)

        elif action==HARDLINK:
            for crc in ProcessedItems:
                refItem=ProcessedItems[crc][0]
                IndexTupleRef=self.GetIndexTupleTreeGroups(refItem)
                size=int(self.TreeGroups.set(refItem,'size'))

                if resmsg:=self.D.LinkWrapper(False, False, size,crc, IndexTupleRef, [self.GetIndexTupleTreeGroups(item) for item in ProcessedItems[crc][1:] ] ):
                    logging.error(resmsg)
                    self.Info('Error',resmsg,self.main)
                self.UpdateCrcNode(crc)

        self.main.config(cursor="")

        self.DataPrecalc()
        self.TreeGroupsFlatItemsToupleUpdate()

        if FinalInfo:
            self.Info('Removed empty directories','\n'.join(FinalInfo),self.main,textwidth=160,width=800)

    def GetThisOrExistingParent(self,path):
        if os.path.exists(path):
            return path
        else:
            return self.GetThisOrExistingParent(pathlib.Path(path).parent.absolute())

    @KeepSemiFocus
    def ProcessFiles(self,action,ProcessedItems,ScopeTitle):
        tree=(self.TreeGroups,self.TreeFolder)[self.SelTreeIndex]

        if not ProcessedItems:
            self.DialogWithEntry(title='No Files Marked For Processing !',prompt='Scope: ' + ScopeTitle + '\n\nMark files first.',parent=self.main,OnlyInfo=True,width=600,height=200)
            return

        logging.info(f'ProcessFiles:{action}')
        logging.info('Scope ' + ScopeTitle)

        #############################################
        #check remainings

        #RemainingItems dla wszystkich (moze byc akcja z folderu)
        #istotna kolejnosc

        AffectedCRCs=ProcessedItems.keys()

        self.StatusLine.set('checking remaining items...')
        RemainingItems={}
        for crc in AffectedCRCs:
            RemainingItems[crc]=[item for item in self.TreeGroups.get_children(crc) if not self.TreeGroups.tag_has(MARK,item)]

        if self.ProcessFilesCheckCorrectness(action,ProcessedItems,RemainingItems):
            return

        if not ProcessedItems:
            self.DialogWithEntry(title='Info',prompt="          No files left for processing. Fix files selection.          ",parent=self.main,OnlyInfo=True)
            return

        logging.warning('###########################################################################################')
        logging.warning(f'action:{action}')

        self.StatusLine.set('')
        if self.ProcessFilesConfirm(action,ProcessedItems,RemainingItems,ScopeTitle):
            return

        #after confirmation
        if self.ProcessFilesCheckCorrectnessLast(action,ProcessedItems,RemainingItems):
            return

        #############################################
        #action

        if tree==self.TreeGroups:
            #orglist=self.TreeGroups.get_children()
            orglist=self.TreeGroupsFlatItemsTouple
        else:
            orgSelItem=self.SelItem
            orglist=self.TreeFolder.get_children()
            #orglistNames=[self.TreeFolder.item(item)['values'][2] for item in self.TreeFolder.get_children()]
            orgSelItemName=self.TreeFolder.item(orgSelItem)['values'][2]
            #print(orglistNames)

        #############################################
        self.ProcessFilesCore(action,ProcessedItems,RemainingItems)
        #############################################

        if tree==self.TreeGroups:
            #newlist=self.TreeGroups.get_children()

            SelItem = self.SelItem if self.SelItem else self.SelCrc
            ItemToSel = self.GimmeClosestInCrc(orglist,SelItem,self.TreeGroupsFlatItemsTouple)

            if ItemToSel:
                self.TreeGroups.see(ItemToSel)
                self.TreeGroups.focus(ItemToSel)
                self.TreeGroupsSelChange(ItemToSel)
            else:
                self.InitialFocus()
        else:
            parent = self.GetThisOrExistingParent(self.SelFullPath)

            if self.TreeFolderUpdate(parent):
                newlist=self.TreeFolder.get_children()

                ItemToSel = self.GimmeClosestInDir(orglist,orgSelItem,orgSelItemName,newlist)

                if ItemToSel:
                    self.TreeFolder.focus(ItemToSel)
                    self.TreeFolderSelChange(ItemToSel)
                    self.TreeFolder.see(ItemToSel)
                    self.TreeFolder.update()

        self.CalcMarkStatsAll()

        #self.FolderItemsCache={}

        self.FindResult=[]

    def GimmeClosestInDir(self,PrevList,item,itemName,NewList):
        if item in NewList:
            return item
        elif not NewList:
            return None
        else:
            NewlistNames=[self.TreeFolder.item(item)['values'][2] for item in self.TreeFolder.get_children()]
            #print('itemName',itemName,'NewlistNames:',NewlistNames)

            if itemName in NewlistNames:
                #print('found:', NewlistNames.index(itemName),'=',NewList[NewlistNames.index(itemName)])
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

    def GimmeClosestInCrc(self,PrevList,item,NewList):
        #print('diff:',set(PrevList)-set(NewList))
        if item in NewList:
            return item
        elif not NewList:
            return None
        else:
            SelIndex=PrevList.index(item)
            #print('SelIndex:',SelIndex)

            NewListLen=len(NewList)
            for i in range(NewListLen):
                if (IndexM1:=SelIndex-i) >=0:
                    Nearest = PrevList[IndexM1]
                    #print('Nearest1:',Nearest)
                    if Nearest in NewList:
                        return Nearest
                elif (IndexP1:=SelIndex+i) < NewListLen:
                    Nearest = PrevList[IndexP1]
                    #print('Nearest2:',Nearest)
                    if Nearest in NewList:
                        return Nearest
                else:
                    return None

    def CleanCache(self):
        try:
            shutil.rmtree(CACHE_DIR)
        except Exception as e:
            logging.error(e)

    def ClipCopyFullWithFile(self):
        if self.SelFullPath and self.SelFile:
            self.ClipCopy(os.path.join(self.SelFullPath,self.SelFile))
        elif self.SelCrc:
            self.ClipCopy(self.SelCrc)

    def ClipCopyFull(self):
        if self.SelFullPath:
            self.ClipCopy(self.SelFullPath)
        elif self.SelCrc:
            self.ClipCopy(self.SelCrc)

    def ClipCopyFile(self):
        if self.SelFile:
            self.ClipCopy(self.SelFile)
        elif self.SelCrc:
            self.ClipCopy(self.SelCrc)

    def ClipCopy(self,what):
        self.main.clipboard_clear()
        self.main.clipboard_append(what)

    @MainWatchCursor
    def OpenFolder(self):
        if self.SelFullPath:
            self.StatusLine.set(f'Opening {self.SelFullPath}')
            if windows:
                os.startfile(self.SelFullPath)
            else:
                os.system("xdg-open " + '"' + self.SelFullPath.replace("'","\'").replace("`","\`") + '"')

    @MainWatchCursor
    def EnterDir(self,fullpath,sel):
        if self.TreeFolderUpdate(fullpath):
            children=self.TreeFolder.get_children()
            resList=[nodeid for nodeid in children if self.TreeFolder.set(nodeid,'file')==sel]
            if resList:
                item=resList[0]
                self.TreeFolder.see(item)
                self.TreeFolder.focus(item)
                self.TreeFolderSelChange(item)

            elif children:
                self.TreeFolder.focus(children[0])
                self.SelFile = self.TreeGroups.set(children[0],'file')
                self.TreeFolderSelChange(children[0])

    def TreeEventDoubleLeft(self,event):
        tree=event.widget
        if tree.identify("region", event.x, event.y) != 'heading':
            if item:=tree.identify('item',event.x,event.y):
                self.main.after_idle(lambda : self.TreeAction(tree,item))

    def TreeAction(self,tree,item):
        if tree.set(item,'kind') == UPDIR:
            head,tail=os.path.split(self.SelFullPath)
            self.EnterDir(os.path.normpath(str(pathlib.Path(self.SelFullPath).parent.absolute())),tail)
        elif tree.set(item,'kind') == DIR:
            self.EnterDir(self.SelFullPath+self.TreeFolder.set(item,'file') if self.SelFullPath=='/' else os.sep.join([self.SelFullPath,self.TreeFolder.set(item,'file')]),'..' )
        elif tree.set(item,'kind')!=CRC:
            self.TreeEventOpenFile()

    #@StatusLineRestore
    @MainWatchCursor
    def TreeEventOpenFile(self):
        if self.SelKind==FILE or self.SelKind==LINK or self.SelKind==SINGLE or self.SelKind==SINGLEHARDLINKED:
            self.StatusLine.set(f'Opening {self.SelFile}')
            if windows:
                os.startfile(os.sep.join([self.SelFullPath,self.SelFile]))
            else:
                os.system("xdg-open "+ '"' + os.sep.join([self.SelFullPath,self.SelFile]).replace("'","\'").replace("`","\`") + '"')
        elif self.SelKind==DIR:
            self.OpenFolder()

    def SetCommonVarWin(self):
        self.StatusVarFullPath.set(pathlib.Path(os.sep.join([self.SelFullPath,self.SelFile])))

    def SetCommonVarLin(self):
        self.StatusVarFullPath.set(self.SelFullPath+self.SelFile if self.SelFullPath=='/' else os.sep.join([self.SelFullPath,self.SelFile]))

    def SetCommonVar(self):
        self.StatusVarFullPath.set(self.SelFullPathToFile)
        self.SetCommonVarFg()

    def SetCommonVarFg(self):
        try:
            self.StatusVarFullPathLabel.config(fg = 'red' if self.SelItem and (self.TreeGroups,self.TreeFolder)[self.SelTreeIndex].tag_has(MARK,self.SelItem) else 'black')
        except Exception as e:
            print(e)
            pass

LoggingLevels={logging.DEBUG:'DEBUG',logging.INFO:'INFO'}

if __name__ == "__main__":


    try:
        parser = argparse.ArgumentParser(
                formatter_class=argparse.RawTextHelpFormatter,
                prog = 'dude.exe' if windows else 'dude',
                description = f"dude version {VERSION}\nCopyright (c) 2022 Piotr Jochymek\n\nhttps://github.com/PJDude/dude",
                )

        parser.add_argument('paths'                 ,nargs='*'          ,help='path to scan')
        parser.add_argument('-e','--exclude'        ,nargs='*'          ,help='exclude expressions')
        parser.add_argument('-er','--excluderegexp' ,nargs='*'          ,help='exclude regular expressions')
        parser.add_argument('--norun'           ,action='store_true'    ,help='don\'t run scanning, only show scan dialog')
        parser.add_argument('-l','--log' ,nargs='?'                     ,help='specify log file')
        parser.add_argument('-d','--debug' ,action='store_true'         ,help='set debug logging level')

        args = parser.parse_args()

        log=os.path.abspath(args.log) if args.log else LOG_DIR + os.sep + time.strftime('%Y_%m_%d_%H_%M_%S',time.localtime(time.time()) ) +'.log'
        LoggingLevel = logging.DEBUG if args.debug else logging.INFO

        pathlib.Path(LOG_DIR).mkdir(parents=True,exist_ok=True)

        print('log:',log)

        logging.basicConfig(level=LoggingLevel,format='%(asctime)s %(levelname)s %(message)s', filename=log,filemode='w')

        if args.debug:
            logging.debug('DEBUG LEVEL')

        Gui(os.getcwd(),args.paths,args.exclude,args.excluderegexp,args.norun)

    except Exception as e:
        print(e)
        logging.error(e)
