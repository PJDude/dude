#!/usr/bin/python3

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

import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import scrolledtext
from tkinter.filedialog import askdirectory

from collections import defaultdict
from threading import Thread
from sys import exit


import core

try:
    from appdirs import *
    CACHE_DIR = os.sep.join([user_cache_dir('dude'),"cache"])
    LOG_DIR = user_log_dir('dude')
    CONFIG_DIR = user_config_dir('dude')
except Exception as e:
    print(e)
    CONFIG_DIR=LOG_DIR=CACHE_DIR = os.sep.join([os.getcwd(),"dude-no-appdirs"])

k=1024
M=k*1024
G=M*1024
T=G*1024

multDict={'k':k,'K':k,'M':M,'G':G,'T':T}

windows = (os.name=='nt')

def bytes2str(num,digits=2):
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

    def Get(self,key,default=None,section='main'):
        try:
            res=self.config.get(section,key)
        except Exception as e:
            logging.warning(f'gettting config key {key}')
            logging.warning(e)
            res=default
            self.Set(key,str(default),section=section)
        
        return str(res).replace('[','').replace(']','').replace('"','').replace("'",'').replace(',','').replace(' ','')

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

    def MainWatchCursor(f):
        def wrapp(self,*args,**kwargs):
            prevCursor=self.main.cget('cursor')
            self.main.config(cursor="watch")
            self.main.update()

            res=f(self,*args,**kwargs)

            self.main.config(cursor=prevCursor)
            return res
        return wrapp
    
    def StatusLineRestore(f):
        def wrapp(self,*args,**kwargs):
            prev=self.StatusLine.get()
            
            res=f(self,*args,**kwargs)

            self.StatusLine.set(prev)
            return res
        return wrapp

    def KeepSemiFocus(f):
        def wrapp(self,*args,**kwargs):
            tree=self.main.focus_get()
            tree.configure(style='semi_focus.Treeview')
    
            res=f(self,*args,**kwargs)
    
            tree.configure(style='default.Treeview')
            
            return res
        return wrapp
        
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

    LADPrevMessage=''
    LADPrevProg1=''
    LADPrevProg2=''
    LastTimeNoSign=0

    def LongActionDialogUpdate(self,message,progress1=None,progress2=None,progress1Right=None,progress2Right=None,PrefixInfo=''):
        prefix='\n\n'
        if self.LADPrevProg1==progress1Right and self.LADPrevProg2==progress2Right and self.LADPrevMessage==message:
            if time.time()>self.LastTimeNoSign+1.0:
                prefix=str(self.ProgressSigns[self.psIndex]) + "\n" + PrefixInfo + "\n"
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

        self.message.set(f'{prefix}{message}')
        self.LongActionDialog.update()

    def __init__(self,cwd):
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

        self.main.bind_class('Treeview','<KeyPress>', self.KeyPressTreeCommon )
        self.main.bind_class('Treeview','<KeyRelease>', self.KeyReleaseTreeCommon )

        self.main.bind_class('Treeview','<FocusIn>',    self.TreeEventFocusIn )
        self.main.bind_class('Treeview','<FocusOut>',   self.TreeFocusOut )

        self.main.bind_class('Treeview','<ButtonPress-1>', self.TreeButtonPress)
        self.main.bind_class('Treeview','<Control-ButtonPress-1>',  lambda event :self.TreeButtonPress(event,True) )

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

        self.TreeFolder.heading('sizeH', text='Size \u25BC')

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
        self.SetingsDialog.iconphoto(False, self.iconphoto)

        self.addCwdAtStartup = tk.BooleanVar()
        self.scanAtStartup = tk.BooleanVar()
        self.fullCRC = tk.BooleanVar()
        self.fullPaths = tk.BooleanVar()
        self.relSymlinks = tk.BooleanVar()

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
        self.AddCwdCB.grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1
        self.StartScanCB=ttk.Checkbutton(fr, text = 'Start scanning at startup', variable=self.scanAtStartup,command=lambda : ScanAtStartupChange(self)                              )
        self.StartScanCB.grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1

        ttk.Checkbutton(fr, text = 'Show full CRC', variable=self.fullCRC                                       ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1
        ttk.Checkbutton(fr, text = 'Show full scan paths', variable=self.fullPaths                              ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1
        ttk.Checkbutton(fr, text = 'Create relative symbolic links', variable=self.relSymlinks                  ).grid(row=row,column=0,sticky='wens',padx=3,pady=2) ; row+=1

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

        def FileCascadeFill():
            self.FileCascade.delete(0,END)
            ItemActionsState=('disabled','normal')[self.SelItem!=None]

            self.FileCascade.add_command(label = 'Scan',command = self.ScanDialogShow, accelerator="S")
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'Settings',command=self.SettingsDialogShow, accelerator="F2")
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'Erase CRC Cache',command = self.CleanCache)
            self.FileCascade.add_separator()
            self.FileCascade.add_command(label = 'Exit',command = self.exit)

        self.FileCascade= Menu(self.menubar,tearoff=0,bg=self.bg,postcommand=FileCascadeFill)
        self.menubar.add_cascade(label = 'File',menu = self.FileCascade,accelerator="Alt+F")

        def GoToCascadeFill():
            self.GoToCascade.delete(0,END)
            ItemActionsState=('disabled','normal')[self.SelItem!=None]
            self.GoToCascade.add_command(label = 'dominant group (by size sum)',command = lambda : self.GoToMaxGroup(1), accelerator="Shift+Backspace",state=ItemActionsState)
            self.GoToCascade.add_command(label = 'dominant group (by quantity)',command = lambda : self.GoToMaxGroup(0), accelerator="Shift+Ctrl+Backspace",state=ItemActionsState)
            self.GoToCascade.add_separator()
            self.GoToCascade.add_command(label = 'dominant folder (by size sum)',command = lambda : self.GoToMaxFolder(1),accelerator="Backspace",state=ItemActionsState)
            self.GoToCascade.add_command(label = 'dominant folder (by quantity)',command = lambda : self.GoToMaxFolder(0), accelerator="Ctrl+Backspace",state=ItemActionsState)

        self.GoToCascade= Menu(self.menubar,tearoff=0,bg=self.bg,postcommand=GoToCascadeFill)

        self.menubar.add_cascade(label = 'Go To',menu = self.GoToCascade)

        self.HelpCascade= Menu(self.menubar,tearoff=0,bg=self.bg)
        self.HelpCascade.add_command(label = 'About',command=self.About,accelerator="F1")
        self.HelpCascade.add_command(label = 'Keyboard Shortcuts',command=self.KeyboardShortcuts)
        self.HelpCascade.add_command(label = 'License',command=self.License)

        self.menubar.add_cascade(label = 'Help',menu = self.HelpCascade)

        #######################################################################
        self.ResetSels()

        self.SettingsSetBools()

        if self.AddCwdAtStartup:
            self.addPath(cwd)

        self.ScanDialogShow()

        self.ColumnSortLastParams={}
        self.ColumnSortLastParams[self.TreeGroups]=['sizeH',1]
        self.ColumnSortLastParams[self.TreeFolder]=['sizeH',1]

        self.SelItemTree[self.TreeGroups]=None
        self.SelItemTree[self.TreeFolder]=None

        self.ShowGroups()

        if self.ScanAtStarup:
            self.main.update()
            self.Scan()

        self.main.mainloop()
        
    def ResetSels(self):
        self.SelPathnr = None
        self.SelPath = None
        self.SelFile = None
        self.SelCrc = None
        self.SelItem = None
        self.SelItemTree = {}
        self.SelItemTree[self.TreeGroups]=None
        self.SelItemTree[self.TreeFolder]=None
        
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
    
    @MainWatchCursor            
    def FindNext(self):
        if not self.FindResult or self.FindTreeIndex!=self.SelTreeIndex:
            self.FindDialogShow()
        else:
            self.FindSelection(1)
        
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

            self.cfg.Set(CFG_KEY_USE_REG_EXPR,str(self.DialogRegExpr.get()))

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
            StrEvent=str(event)
            ShiftPressed = 'Shift' in StrEvent
            
            if ShiftPressed:
                PrevCmd()
            else:
                NextCmd()
            
        def ReturnPressed(event=None):
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
                                    fullpath = self.FullPath1(item)
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
        self.DialogRegExpr.set(True if self.cfg.Get(CFG_KEY_USE_REG_EXPR,False)=='True' else False)
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
                self.cfg.Set(CFG_KEY_USE_REG_EXPR,str(self.DialogRegExpr.get()))
            
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
                self.DialogRegExpr.set(True if self.cfg.Get(CFG_KEY_USE_REG_EXPR,False)=='True' else False)
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
            print(f'PrevGrab=')
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

    def KeyReleaseTreeCommon(self,event):
        pass
        
    @MainWatchCursor    
    def KeyPressTreeCommon(self,event):
        tree=event.widget
        item=tree.focus()

        tree.selection_remove(tree.selection())

        if event.keysym in ("Up",'Down') :
            if tree==self.TreeGroups:
                pool=self.FlatItemsList
                poolLen=self.FlatItemsListLen
            else:
                pool=tree.get_children()
                poolLen=len(pool)

            #print(self.SelItem,self.SelItemTree[tree])
            index = pool.index(self.SelItem) if self.SelItem in pool else pool.index(self.SelItemTree[tree]) if self.SelItemTree[tree] in pool else pool.index(item) if item in  pool else 0
            if poolLen:
                index=(index+self.DirectionOfKeysym[event.keysym])%poolLen
                NextItem=pool[index]

                tree.focus(NextItem)
                tree.see(NextItem)

                if tree==self.TreeGroups:
                    self.TreeGroupsSelChange(NextItem)
                else:
                    self.TreeFolderSelChange(NextItem)
        elif event.keysym in ("Prior","Next"):
            if tree==self.TreeGroups:
                pool=tree.get_children()
            else:
                pool=[item for item in tree.get_children() if tree.set(item,'kind')==FILE]
                
            poolLen=len(pool)
            if poolLen:
                if tree==self.TreeGroups:
                    NextItem=pool[(pool.index(tree.set(item,'crc'))+self.DirectionOfKeysym[event.keysym]) % poolLen]
                    self.SelectFocusAndSeeCrcItemTree(NextItem)
                else:
                    self.GotoNextDupeFile(tree,self.DirectionOfKeysym[event.keysym])
                    tree.update()
        elif event.keysym in ("Home","End"):
            if tree==self.TreeGroups:
                if NextItem:=tree.get_children()[0 if event.keysym=="Home" else -1]:
                    self.SelectFocusAndSeeCrcItemTree(NextItem,True)
            else:
                if NextItem:=tree.get_children()[0 if event.keysym=='Home' else -1]:
                    tree.see(NextItem)
                    tree.focus(NextItem)
                    self.TreeFolderSelChange(NextItem)
                    tree.update()
        elif event.keysym == "space":
            if tree==self.TreeGroups:
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
        elif event.keysym=='KP_Add' or event.keysym=='plus':
            StrEvent=str(event)
            CtrPressed = 'Control' in StrEvent
            self.MarkExpression(self.SetMark,'Mark files',CtrPressed)
        elif event.keysym=='KP_Subtract' or event.keysym=='minus':
            StrEvent=str(event)
            CtrPressed = 'Control' in StrEvent
            self.MarkExpression(self.UnsetMark,'Unmark files',CtrPressed)
        else:
            StrEvent=str(event)

            CtrPressed = 'Control' in StrEvent
            ShiftPressed = 'Shift' in StrEvent

            if event.keysym=='F3':
                if ShiftPressed:
                    self.FindPrev()
                else:
                    self.FindNext()
            
            if event.keysym == "Delete":
                self.ProcessFiles(DELETE,CtrPressed)
            elif event.keysym == "Insert":
                if ShiftPressed:
                    self.ProcessFiles(HARDLINK,CtrPressed)
                else:
                    self.ProcessFiles(SOFTLINK,CtrPressed)
            elif event.keysym=='BackSpace':
                if ShiftPressed:
                    self.GoToMaxGroup(not CtrPressed)
                else:
                    self.GoToMaxFolder(not CtrPressed)
            elif event.keysym=='i' or event.keysym=='I':
                if CtrPressed:
                    self.MarkOnAll(self.InvertMark)
                else:
                    if tree==self.TreeGroups:
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
                    if tree==self.TreeGroups:
                        self.MarkInCRCGroupByCTime('oldest',self.InvertMark)
            elif event.keysym=='y' or event.keysym=='Y':
                if CtrPressed:
                    if ShiftPressed:
                        self.MarkOnAllByCTime('youngest',self.UnsetMark)
                    else:
                        self.MarkOnAllByCTime('youngest',self.SetMark)
                else:
                    if tree==self.TreeGroups:
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
                if tree==self.TreeGroups:
                    if CtrPressed:
                        self.MarkOnAll(self.SetMark)
                    else:
                        self.MarkInCRCGroup(self.SetMark)
                else:
                    self.MarkLowerPane(self.SetMark)

            elif event.keysym=='n' or event.keysym=='N':
                if tree==self.TreeGroups:
                    if CtrPressed:
                        self.MarkOnAll(self.UnsetMark)
                    else:
                        self.MarkInCRCGroup(self.UnsetMark)
                else:
                    self.MarkLowerPane(self.UnsetMark)
            elif event.keysym in self.reftuple1:
                index = self.reftuple1.index(event.keysym)

                if index<len(self.D.ScannedPaths):
                    if tree==self.TreeGroups:
                        self.ActionOnSpecifiedPath(self.D.ScannedPaths[index],self.SetMark,CtrPressed)
            elif event.keysym in self.reftuple2:
                index = self.reftuple2.index(event.keysym)

                if index<len(self.D.ScannedPaths):
                    if tree==self.TreeGroups:
                        self.ActionOnSpecifiedPath(self.D.ScannedPaths[index],self.UnsetMark,CtrPressed)
            elif event.keysym=='KP_Divide' or event.keysym=='slash':
                self.MarkSubpath(self.SetMark,True)
            elif event.keysym=='question':
                self.MarkSubpath(self.UnsetMark,True)
            elif event.keysym=='f' or event.keysym=='F':
                self.FindDialogShow()
            else:
                #print(event.keysym)
                pass
                #if windows:

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
                tree.focus_set()
                self.ColumnSortClick(tree,colname)

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
    
    SelChangeInProgress=False
    def TreeGroupsSelChange(self,item,force=False):
        if not self.SelChangeInProgress:
            self.SelChangeInProgress=True
            
            pathnr=self.TreeGroups.set(item,'pathnr')
            path=self.TreeGroups.set(item,'path')

            self.SelFile = self.TreeGroups.set(item,'file')
            self.SelCrc = self.TreeGroups.set(item,'crc')
            self.SelKind = self.TreeGroups.set(item,'kind')
            self.SelItem = item
            self.SelItemTree[self.TreeGroups]=item
            self.SelTreeIndex=0

            size = int(self.TreeGroups.set(item,'size'))
            
            #doskanowac katalogi
            (checkres,TuplesToRemove)=self.D.CheckGroupFilesState(size,self.SelCrc)
            
            if checkres:
                self.Info('Error. Inconsistent data.','Current filesystem state is inconsistent with scanned data.\n\n' + '\n'.join(checkres) + '\n\nSelected CRC group will be reduced. For complete results re-scanning is recommended.',self.main)
                orglist=self.TreeGroups.get_children()
                
                self.D.RemoveTuples(size,self.SelCrc,TuplesToRemove)
                
                self.UpdateCrcNode(self.SelCrc)
                
                self.FlatItemsListUpdate()
                
                self.ByPathCacheUpdate()
                self.GroupsNumberUpdate()
                
                newlist=self.TreeGroups.get_children()
                ItemToSel = self.GimmeClosest(orglist,self.SelCrc,newlist)
                
                self.ResetSels()
                
                self.SelChangeInProgress=False
                if ItemToSel:
                    #crc node moze zniknac - trzeba zupdejtowac SelXxx
                    self.SelectFocusAndSeeCrcItemTree(ItemToSel,True)
                else:
                    self.InitialFocus()
                
                self.CalcMarkStatsAll()
            else :    
                if path!=self.SelPath or pathnr!=self.SelPathnr or force:
                    self.SelPathnr = pathnr

                    if pathnr: #non crc node
                        self.SelPathnrInt= int(pathnr)
                        self.SelSearchPath = self.D.ScannedPaths[self.SelPathnrInt]
                        self.SelPath = path
                        self.SelFullPath=self.SelSearchPath+self.SelPath
                    else :
                        self.SelPathnrInt= 0
                        self.SelSearchPath = None
                        self.SelPath = None
                        self.SelFullPath= None

                    UpdateTreeFolder=True
                else:
                    UpdateTreeFolder=False

                if self.SelKind==FILE:
                    self.SetCommonVar()
                    self.TreeFolderUpdate()
                else:
                    self.TreeFolderUpdateNone()
                
                self.SelChangeInProgress=False
            
    def TreeFolderSelChange(self,item):
        self.SelFile = self.TreeFolder.set(item,'file')
        self.SelCrc = self.TreeFolder.set(item,'crc')
        self.SelKind = self.TreeFolder.set(item,'kind')
        self.SelItem = item
        self.SelItemTree[self.TreeFolder] = item
        self.SelTreeIndex=1

        self.SetCommonVar()
        
        if self.TreeFolder.set(item,'kind')==FILE:
            self.UpdateMainTree(item)
        else:
            self.UpdateMainTreeNone()
            #self.StatusVarFullPath.set("")

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

            cLocal.add_command(label = 'Remove Marked Files',command=lambda : self.ProcessFiles(DELETE,0),accelerator="Delete",state=MarksState)
            cLocal.entryconfig(19,foreground='red',activeforeground='red')
            cLocal.add_command(label = 'Softlink Marked Files',command=lambda : self.ProcessFiles(SOFTLINK,0),accelerator="Insert",state=MarksState)
            cLocal.entryconfig(20,foreground='red',activeforeground='red')
            cLocal.add_command(label = 'Hardlink Marked Files',command=lambda : self.ProcessFiles(HARDLINK,0),accelerator="Shift+Insert",state=MarksState)
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

            cAll.add_command(label = 'Remove Marked Files',command=lambda : self.ProcessFiles(DELETE,1),accelerator="Ctrl+Delete",state=MarksState)
            cAll.entryconfig(21,foreground='red',activeforeground='red')
            cAll.add_command(label = 'Softlink Marked Files',command=lambda : self.ProcessFiles(SOFTLINK,1),accelerator="Ctrl+Insert",state=MarksState)
            cAll.entryconfig(22,foreground='red',activeforeground='red')
            cAll.add_command(label = 'Hardlink Marked Files',command=lambda : self.ProcessFiles(HARDLINK,1),accelerator="Ctrl+Shift+Insert",state=MarksState)
            cAll.entryconfig(23,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'All Files',menu = cAll,state=ItemActionsState)

            cNav = Menu(self.menubar,tearoff=0,bg=self.bg)
            cNav.add_command(label = 'go to dominant group (by size sum)',command = lambda : self.GoToMaxGroup(1), accelerator="Shift+Backspace")
            cNav.add_command(label = 'go to dominant group (by quantity)',command = lambda : self.GoToMaxGroup(0), accelerator="Shift+Ctrl+Backspace")

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

            cLocal.add_command(label = 'Remove Marked Files',command=lambda : self.ProcessFiles(DELETE,0),accelerator="Delete",state=MarksState)
            cLocal.add_command(label = 'Softlink Marked Files',command=lambda : self.ProcessFiles(SOFTLINK,0),accelerator="Insert",state=MarksState)
            cLocal.add_command(label = 'Hardlink Marked Files',command=lambda : self.ProcessFiles(HARDLINK,0),accelerator="Shift+Insert",state=MarksState)
            cLocal.entryconfig(8,foreground='red',activeforeground='red')
            cLocal.entryconfig(9,foreground='red',activeforeground='red')
            cLocal.entryconfig(10,foreground='red',activeforeground='red')

            pop.add_cascade(label = 'Local (this folder)',menu = cLocal,state=ItemActionsState)
            pop.add_separator()
            
            cSelSub = Menu(pop,tearoff=0,bg=self.bg)
            cSelSub.add_command(label = "Mark All Duplicates in Subdirectory",  command = lambda : self.SelDir(self.SetMark),accelerator="D",state=DirActionsState)
            cSelSub.add_command(label = "Unmark All Duplicates in Subdirectory",  command = lambda : self.SelDir(self.UnsetMark),accelerator="Shift+D",state=DirActionsState)
            cSelSub.add_separator()
            
            cSelSub.add_command(label = 'Remove Marked Files in Subdirectory Tree',command=lambda : self.ProcessFiles(DELETE,1,True),accelerator="Delete",state=DirActionsState)
            cSelSub.add_command(label = 'Softlink Marked Files in Subdirectory Tree',command=lambda : self.ProcessFiles(SOFTLINK,1,True),accelerator="Insert",state=DirActionsState)
            cSelSub.add_command(label = 'Hardlink Marked Files in Subdirectory Tree',command=lambda : self.ProcessFiles(HARDLINK,1,True),accelerator="Shift+Insert",state=DirActionsState)
            cSelSub.entryconfig(3,foreground='red',activeforeground='red')
            cSelSub.entryconfig(4,foreground='red',activeforeground='red')
            cSelSub.entryconfig(5,foreground='red',activeforeground='red')
            
            pop.add_cascade(label = 'Selected Subdirectory',menu = cSelSub,state=DirActionsState)

            cNav = Menu(pop,tearoff=0,bg=self.bg)
            cNav.add_command(label = 'go to dominant folder (by size sum)',command = lambda : self.GoToMaxFolder(1),accelerator="Backspace")
            cNav.add_command(label = 'go to dominant folder (by quantity)',command = lambda : self.GoToMaxFolder(0) ,accelerator="Ctrl+Backspace")

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
        
    def SelDir(self,action):
        self.ActionOnSpecifiedPath(self.StatusVarFullPath.get(),action,True)
        
    def ColumnSortClick(self, tree, colname):
        prev_colname,prev_reverse=self.ColumnSortLastParams[tree]
        reverse = not prev_reverse if colname == prev_colname else prev_reverse
        tree.heading(prev_colname, text=self.OrgLabel[prev_colname])

        self.ColumnSortLastParams[tree]=[colname,reverse]
        self.ColumnSort(tree)

    @MainWatchCursor
    @StatusLineRestore
    def ColumnSort(self, tree):
        self.StatusLine.set('Sorting...')
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

        if tree==self.TreeGroups:
            self.FlatItemsListUpdate()

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

        if res:=self.D.SetExcludeMasks(self.cfg.Get(CFG_KEY_EXCLUDE_REGEXP,False) == 'True',ExcludeVarsFromEntry):
            self.Info('Error. Fix Exclude masks.',res,self.ScanDialog)
            return

        self.cfg.Set(CFG_KEY_EXCLUDE,'|'.join(ExcludeVarsFromEntry))

        self.main.update()

        #############################
        
        self.LongActionDialogShow(self.ScanDialogMainFrame,'Scanning')

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
        self.StatusLine.set('Calculating CRC ...')
        self.LongActionDialogShow(self.ScanDialogMainFrame,'CRC calculation','determinate','determinate',Progress1LeftText='Total size:',Progress2LeftText='Files number:')

        self.D.writeLog=self.WriteScanToLog.get()

        ScanThread=Thread(target=self.D.CrcCalc,daemon=True)
        ScanThread.start()

        while ScanThread.is_alive():
            sumSizeStr='/' + bytes2str(self.D.sumSize)
            progress1Right=bytes2str(self.D.InfoSizeDone) + sumSizeStr
            progress2Right=str(self.D.InfoFileNr) + '/' + str(self.D.InfoTotal)

            InfoProgSize=float(100)*float(self.D.InfoSizeDone)/float(self.D.sumSize)
            InfoProgQuant=float(100)*float(self.D.InfoFileNr)/float(self.D.InfoTotal)

            info = 'CRC groups: ' + str(self.D.InfoFoundGroups) \
                    + '\nfolders: ' + str(self.D.InfoFoundFolders) \
                    + '\nspace: ' + bytes2str(self.D.InfoDuplicatesSpace) \
                    + '\n' \
                    + '\ncurrent file size: ' + bytes2str(self.D.InfoCurrentSize) \
                    + '\n\nSpeed:' + bytes2str(self.D.infoSpeed,0) + '/s'
            self.LongActionDialogUpdate(info,InfoProgSize,InfoProgQuant,progress1Right,progress2Right,PrefixInfo=self.D.InfoCurrentFile)

            if self.LongActionAbort:
                self.D.Abort()
                self.D.Kill()
                #self.D.INIT()
                break
            else:
                time.sleep(0.04)

        ScanThread.join()
        self.LongActionDialogEnd()
        #############################

        if self.LongActionAbort:
            self.DialogWithEntry(title='CRC Calculation aborted.',prompt='\nResults are partial.\nSome files may remain unidentified as duplicates.',parent=self.ScanDialog,OnlyInfo=True,width=300,height=200)
        
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
        self.cfg.Set(CFG_KEY_EXCLUDE_REGEXP,str(self.ScanExcludeRegExpr.get()))

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
        pass
        
    def License(self):
        self.Info('License',self.license,self.main,textwidth=80,width=600)

    def About(self):
        info=[]
        info.append('==============================================================================')
        info.append('                                                                              ')
        info.append(f'                       DUDE (DUplicates DEtector) v{VERSION}                    ')
        info.append('                                                                              ')
        info.append('                        https://github.com/PJDude/dude                        ')
        info.append('                                                                              ')
        info.append('                        https://pjdude.github.io/dude/                        ')
        info.append('                                                                              ')
        info.append('                                Piotr Jochymek                                ')
        info.append('                            PJ.soft.dev.x@gmail.com                           ')
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

        settings = [
            (self.addCwdAtStartup,CFG_KEY_STARTUP_ADD_CWD,True),
            (self.scanAtStartup,CFG_KEY_STARTUP_SCAN,False),
            (self.fullCRC,CFG_KEY_FULLCRC,False),
            (self.fullPaths,CFG_KEY_FULLPATHS,False),
            (self.relSymlinks,CFG_KEY_REL_SYMLINKS,True)
        ]
        for var,key,default in settings:
            try:
                var.set(self.cfg.Get(key,default))
            except Exception as e:
                print(e)
        
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

        self.cfg.Write()

        self.SettingsSetBools()

        if update1:
            self.TreeGroupsCrcAndPathUpdate()

        if update2:
            if self.SelCrc and self.SelItem and self.SelFullPath:
                self.TreeFolderUpdate()
            else:
                self.TreeFolderUpdateNone()

        self.SettingsDialogClose()

    AddCwdAtStartup = False
    ScanAtStarup = False
    FullCRC = False
    FullPaths = False

    def SettingsSetBools(self):
        self.AddCwdAtStartup = self.cfg.Get(CFG_KEY_STARTUP_ADD_CWD,'True') == 'True'
        self.ScanAtStarup = self.cfg.Get(CFG_KEY_STARTUP_SCAN,'True') == 'True'
        self.FullCRC = self.cfg.Get(CFG_KEY_FULLCRC,False) == 'True'
        self.FullPaths = self.cfg.Get(CFG_KEY_FULLPATHS,False) == 'True'

    def SettingsDialogReset(self):
        self.addCwdAtStartup.set(True)
        self.scanAtStartup.set(False)
        self.fullCRC.set(False)
        self.fullPaths.set(False)
        self.relSymlinks.set(True)

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

    def ByPathCacheUpdate(self):
        self.ByPathCache = { (pathnr,path,file):(size,ctime,dev,inode,crc,self.D.crccut[crc]) for size,sizeDict in self.D.filesOfSizeOfCRC.items() for crc,crcDict in sizeDict.items() for pathnr,path,file,ctime,dev,inode in crcDict }

    def GroupsNumberUpdate(self):
        self.StatusVarGroups.set(len(self.TreeGroups.get_children()))

    FlatItemsList=[]
    FlatItemsListLen=0
    def FlatItemsListUpdate(self):
        self.FlatItemsList = [elem for sublist in [ tuple([crc])+tuple(self.TreeGroups.get_children(crc)) for crc in self.TreeGroups.get_children() ] for elem in sublist]
        self.FlatItemsListLen=len(self.FlatItemsList)

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
        self.idfunc = (lambda i,d : str(i)+'-'+str(d)) if len(self.D.devs)>1 else (lambda i,d : str(i))

        self.ResetSels()
        self.TreeGroups.delete(*self.TreeGroups.get_children())

        for size,sizeDict in self.D.filesOfSizeOfCRC.items() :
            for crc,crcDict in sizeDict.items():
                crcitem=self.TreeGroups.insert(parent='', index=END,iid=crc, values=('','','',size,bytes2str(size),'','','',crc,len(crcDict),'',CRC),tags=[CRC],open=True)

                for pathnr,path,file,ctime,dev,inode in crcDict:
                    self.TreeGroups.insert(parent=crcitem, index=END,iid=self.idfunc(inode,dev), values=(\
                            pathnr,path,file,size,\
                            '',\
                            ctime,dev,inode,crc,\
                            '',\
                            time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime)) ,FILE),tags=[])

        self.ByPathCacheUpdate()

        self.ColumnSort(self.TreeGroups)
        self.GroupsNumberUpdate()
        self.FlatItemsListUpdate() #after sort !
        self.InitialFocus()
        self.CalcMarkStatsAll()

    def TreeGroupsCrcAndPathUpdate(self):
        for size,sizeDict in self.D.filesOfSizeOfCRC.items() :
            for crc,crcDict in sizeDict.items():
                self.TreeGroups.item(crc,text=crc if self.FullCRC else self.D.crccut[crc])
                for pathnr,path,file,ctime,dev,inode in crcDict:
                    self.TreeGroups.item(self.idfunc(inode,dev),text=self.D.ScannedPaths[pathnr] if self.FullPaths else self.Numbers[pathnr])

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

    @StatusLineRestore
    def TreeFolderUpdate(self,ArbitraryPath=None):
        try:
            if ArbitraryPath:
                ScanDirRes=list(os.scandir(ArbitraryPath))
            else:
                ScanDirRes=list(os.scandir(self.SelFullPath))
        except Exception as e:
            logging.error(e)
            return False
    
        if ArbitraryPath:
            self.ResetSels()
            self.SelFullPath=str(pathlib.Path(ArbitraryPath))
            
        self.StatusLine.set(f'Scanning path:{self.SelFullPath}')
        itemsToInsert=[]
        
        i=0
        for DirEntry in ScanDirRes:
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
                                            self.TreeGroups.item(FILEID)['tags'],\
                                            FILE,\
                                            FILEID,\
                                            bytes2str(size) ]) )

            else:
                istr=str(i)
                if os.path.islink(DirEntry) :
                    itemsToInsert.append( ( '➝',file,0,0,0,0,'','',1,0,LINK,LINK,istr+'L','' ) )
                    i+=1
                elif DirEntry.is_dir():
                    itemsToInsert.append( ('🗀',file,0,0,0,0,'','',1,0,DIR,DIR,istr+'D','' ) )
                    i+=1
                elif DirEntry.is_file():
                    FullFilePath=os.path.join(self.SelFullPath,file)
                    
                    try:
                        stat = os.stat(FullFilePath)
                    except Exception as e:
                        logging.error(f'ERROR: ,{e}')
                        continue
                    
                    ctime=round(stat.st_ctime)
                    dev=stat.st_dev
                    inode=stat.st_ino
                    size=stat.st_size
                    FILEID=self.idfunc(inode,dev)

                    itemsToInsert.append( ( '',file,size,ctime,dev,inode,'','',1,FILEID,SINGLE,SINGLE,istr+'O',bytes2str(size) ) )
                    i+=1
                else:
                    logging.error(f'what is it: {DirEntry} ?')
    
        colSort,reverse = self.ColumnSortLastParams[self.TreeFolder]

        sortIndex=self.sortIndexDict[colSort]

        IsNumeric=self.col2sortNumeric[colSort]
        DIR0,DIR1 = (1,0) if reverse else (0,1)

        self.TreeFolder.delete(*self.TreeFolder.get_children())
        
        if self.TwoDotsConditionOS():
            #always at the beginning
            (text,file,size,ctime,dev,inode,crc,instances,instancesnum,FILEID,tags,kind,iid,sizeH)=('','..',0,0,0,0,'..','',1,0,DIR,DIR,'0UP','' )
            self.TreeFolder.insert(parent="", index=END, iid=iid , text=text, values=(self.SelPathnrInt,self.SelPath,file,size,sizeH,ctime,dev,inode,crc,instances,instancesnum,'',kind),tags=tags)
            
        for (text,file,size,ctime,dev,inode,crc,instances,instancesnum,FILEID,tags,kind,iid,sizeH) in sorted(itemsToInsert,key=lambda x : (DIR0 if x[self.kindIndex]==DIR else DIR1,float(x[sortIndex])) if IsNumeric else (DIR0 if x[self.kindIndex]==DIR else DIR1,x[sortIndex]),reverse=reverse):
            self.TreeFolder.insert(parent="", index=END, iid=iid , text=text, values=(self.SelPathnrInt,self.SelPath,file,size,sizeH,ctime,dev,inode,crc,instances,instancesnum,time.strftime('%Y/%m/%d %H:%M:%S',time.localtime(ctime)) if crc or kind==SINGLE else '',kind),tags=tags)

        #self.TreeFolder.update()
        
        if not ArbitraryPath:
            #wejscie do pod/nad folderu
            #self.SelItem = self.TreeFolder.get_children()[0]
            
            #self.TreeFolder.see(self.SelItem)
            #self.TreeFolder.focus(self.SelItem)
        
            if self.SelItem and self.SelItem in self.TreeFolder.get_children():
                self.TreeFolder.selection_set(self.SelItem)
                self.TreeFolder.see(self.SelItem)
            
        self.CalcMarkStatsPath()
        self.TreeFolder.update()
        
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
        varSize.set(bytes2str(sum(int(tree.set(item,'size')) for item in marked)))

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
        tree.item(item,tags=[])

    def InvertMark(self,item,tree):
        tree.item(item,tags=[] if tree.item(item)['tags'] else [MARK])

    @MainWatchCursor
    def ActionOnSpecifiedPath(self,pathParam,action,AllGroups=True):
        if AllGroups:
            CrcRange = self.TreeGroups.get_children()
        else :
            CrcRange = [str(self.SelCrc)]

        selCount=0
        for crcitem in CrcRange:
            for item in self.TreeGroups.get_children(crcitem):
                fullpath = self.FullPath1(item)

                if fullpath.startswith(pathParam + os.sep):
                    action(item,self.TreeGroups)
                    selCount+=1

        if selCount==0 :
            self.DialogWithEntry(title='No files found for specified path', prompt=pathParam,parent=self.main,OnlyInfo=True)
        else:
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
                if AllGroups:
                    CrcRange = self.TreeGroups.get_children()
                else :
                    CrcRange = [str(self.SelCrc)]

                for crcitem in CrcRange:
                    for item in self.TreeGroups.get_children(crcitem):
                        fullpath = self.FullPath1(item)
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
            pool=marked if tree.tag_has(MARK,self.SelItem) else self.FlatItemsList if tree==self.TreeGroups else self.TreeFolder.get_children()
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
                        
    @MainWatchCursor
    def GoToMaxGroup(self,sizeFlag=0):
        biggestsizesum=0
        biggestcrc=None
        for crcitem in self.TreeGroups.get_children():
            sizesum=sum([(int(self.TreeGroups.set(item,'size')) if sizeFlag else 1) for item in self.TreeGroups.get_children(crcitem)])
            if sizesum>biggestsizesum:
                biggestsizesum=sizesum
                biggestcrc=crcitem

        if biggestcrc:
            self.SelectFocusAndSeeCrcItemTree(biggestcrc,True)
    
    @MainWatchCursor
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

            self.TreeGroups.focus(item)
            self.TreeGroups.see(item)
            self.TreeGroupsSelChange(item)
            self.TreeGroups.update()

            self.TreeFolderUpdate()

            self.TreeFolder.focus_set()
            self.TreeFolder.focus(item)
            self.TreeFolder.see(item)

            self.UpdateMainTree(item)

    def FullPath1(self,item):
        pathnr=int(self.TreeGroups.set(item,'pathnr'))
        path=self.TreeGroups.set(item,'path')
        file=self.TreeGroups.set(item,'file')
        return os.path.abspath(self.D.ScannedPathFull(pathnr,path,file))

    def CheckFileState(self,item):
        fullpath = self.FullPath1(item)
        logging.info(f'checking file:{fullpath}')
        try:
            stat = os.stat(fullpath)
            ctimeCheck=str(round(stat.st_ctime))
        except Exception as e:
            mesage = f'can\'t check file: {fullpath}\n\n{e}'
            logging.error(mesage)
            return mesage

        if ctimeCheck != (ctime:=self.TreeGroups.set(item,'ctime')) :
            message = {f'ctime inconsistency {ctimeCheck} vs {ctime}'}
            return message

    @KeepSemiFocus
    @StatusLineRestore
    def ProcessFiles(self,action,all=0,OnSelPath=False):
        tree=self.main.focus_get()
        if not tree:
            return
        
        ProcessedItems=defaultdict(list)

        ShowFullPath=1

        if all:
            if OnSelPath:
                ScopeTitle='All marked files on selected directory sub-tree.'
                subpath=self.StatusVarFullPath.get()
                
                for crc in self.TreeGroups.get_children():
                    if tempList:=[item for item in self.TreeGroups.get_children(crc) if self.TreeGroups.tag_has(MARK,item) and self.FullPath1(item).startswith(subpath + os.sep)]:
                        ProcessedItems[crc]=tempList
            else:
                ScopeTitle='All marked files.'
                for crc in self.TreeGroups.get_children():
                    if tempList:=[item for item in self.TreeGroups.get_children(crc) if self.TreeGroups.tag_has(MARK,item)]:
                        ProcessedItems[crc]=tempList
        else:
            if tree==self.TreeGroups:
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
        
        self.StatusLine.set('checking remaining items...')
        RemainingItems={}
        for crc in self.TreeGroups.get_children():
            RemainingItems[crc]=[item for item in self.TreeGroups.get_children(crc) if not self.TreeGroups.tag_has(MARK,item)]
        
        self.StatusLine.set('checking selection correctness...')
        if action==HARDLINK:
            for crc in ProcessedItems:
                if len(ProcessedItems[crc])==1:
                    self.DialogWithEntry(title='Error - Can\'t hardlink single file.',prompt="                    Mark more files.                    ",parent=self.main,OnlyInfo=True)

                    self.SelectFocusAndSeeCrcItemTree(crc,True)
                    return

        elif action in (DELETE,SOFTLINK):
            for crc in ProcessedItems:
                if len(RemainingItems[crc])==0:
                    self.DialogWithEntry(title=f'Error {action} - All files marked',prompt="          Keep at least one file unmarked.          ",parent=self.main,OnlyInfo=True)

                    self.SelectFocusAndSeeCrcItemTree(crc,True)
                    return

        logging.warning('###########################################################################################')
        logging.warning(f'action:{action}')

        message=[]
        for crc in ProcessedItems:
            message.append('')
            size=int(self.TreeGroups.set(crc,'size'))
            message.append('CRC:' + crc + ' size:' + bytes2str(size) + '|GRAY')
            for item in ProcessedItems[crc]:
                message.append((self.FullPath1(item) if ShowFullPath else tree.set(item,'file')) + '|RED' )

            if action==SOFTLINK:
                if RemainingItems[crc]:
                    item = RemainingItems[crc][0]
                    message.append('➝ ' + (self.FullPath1(item) if ShowFullPath else self.TreeGroups.set(item,'file')) )

        if action==DELETE:
            if not self.Ask('Delete marked files ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return
        elif action==SOFTLINK:
            if not self.Ask('Soft-Link marked files to first unmarked file in group ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return
        elif action==HARDLINK:
            if not self.Ask('Hard-Link marked files together in groups ?','Scope - ' + ScopeTitle +'\n'+'\n'.join(message),self.main):
                return
        
        {logging.warning(line) for line in message}
        logging.warning('###########################################################################################')
        logging.warning('Confirmed.')

        #############################################
        for crc in ProcessedItems:
            for item in RemainingItems[crc]:
                if res:=self.CheckFileState(item):
                    self.Info('Error',res+'\n\nNo action was taken.\n\nAborting. Repeat scanning please or unmark all files and groups affected by other programs.',self.main)
                    logging.error('aborting.')
                    return
        logging.info('remaining files checking complete.')
        #############################################
        if action==HARDLINK:
            for crc in ProcessedItems:
                if len({int(self.TreeGroups.set(item,'dev')) for item in ProcessedItems[crc]})>1:
                    message1='Can\'t create hardlinks.'
                    message2=f"Files on multiple devices selected. Crc:{crc}"
                    logging.error(message1)
                    logging.error(message2)
                    self.DialogWithEntry(title=message1,prompt=message2,parent=self.main,OnlyInfo=True)
                    return

        #####################################
        #action

        self.main.config(cursor="watch")
        self.main.update()

        orglist=self.TreeGroups.get_children()
        
        self.StatusLine.set('processing files ...')
        if action==DELETE:
            for crc in ProcessedItems:
                for item in ProcessedItems[crc]:
                    size=int(self.TreeGroups.set(item,'size'))
                    IndexTuple=self.GetIndexTupleTreeGroups(item)

                    if resmsg:=self.D.DeleteFileWrapper(size,crc,IndexTuple):
                        logging.error(resmsg)
                        self.Info('Error',resmsg,self.main)
                        break
                self.UpdateCrcNode(crc)

        if action==SOFTLINK:
            RelSymlink = True if self.cfg.Get(CFG_KEY_REL_SYMLINKS,False)=='True' else False
            for crc in ProcessedItems:

                toKeepItem=list(RemainingItems[crc])[0]
                #self.TreeGroups.focus()
                IndexTupleRef=self.GetIndexTupleTreeGroups(toKeepItem)
                size=int(self.TreeGroups.set(toKeepItem,'size'))

                if resmsg:=self.D.LinkWrapper(True, RelSymlink, size,crc, IndexTupleRef, [self.GetIndexTupleTreeGroups(item) for item in ProcessedItems[crc] ] ):
                    logging.error(resmsg)
                    self.Info('Error',resmsg,self.main)

                self.UpdateCrcNode(crc)

        if action==HARDLINK:
            for crc in ProcessedItems:

                refItem=ProcessedItems[crc][0]
                IndexTupleRef=self.GetIndexTupleTreeGroups(refItem)
                size=int(self.TreeGroups.set(refItem,'size'))

                if resmsg:=self.D.LinkWrapper(False, False, size,crc, IndexTupleRef, [self.GetIndexTupleTreeGroups(item) for item in ProcessedItems[crc][1:] ] ):
                    logging.error(resmsg)
                    self.Info('Error',resmsg,self.main)

                self.UpdateCrcNode(crc)

        self.ByPathCacheUpdate()
        self.GroupsNumberUpdate()
        self.FlatItemsListUpdate()
        
        
        if tree==self.TreeGroups:
            newlist=self.TreeGroups.get_children()

            ItemToSel = self.GimmeClosest(orglist,self.SelCrc,newlist)
            
            if ItemToSel:
                self.SelectFocusAndSeeCrcItemTree(ItemToSel,True)
            else:
                self.InitialFocus()
        else:
            self.EnterDir(self.SelFullPath,'..')
        
        self.CalcMarkStatsAll()

        self.main.config(cursor="")
        self.main.update()
        
        self.FindResult=[]
    
    def GimmeClosest(self,PrevList,item,NewList):
        if item in NewList:
            return item
        elif not NewList:
            return None
        else:
            SelCrcIndex=PrevList.index(item)

            NewListLen=len(NewList)
            for i in range(NewListLen):
                if (IndexM1:=SelCrcIndex-i) >=0:
                    Nearest = PrevList[IndexM1]
                    if Nearest in NewList:
                        return Nearest
                elif (IndexP1:=SelCrcIndex+i) < NewListLen:
                    Nearest = PrevList[IndexP1]
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
    
    @StatusLineRestore
    def OpenFolder(self):
        if self.SelFullPath:
            self.StatusLine.set(f'Opening {self.SelFullPath}')
            if windows:
                os.startfile(self.SelFullPath)
            else:
                os.system("xdg-open " + '"' + self.SelFullPath.replace("'","\'").replace("`","\`") + '"')

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
                self.TreeAction(tree,item)
    
    def TreeAction(self,tree,item):
        if tree.set(item,'kind') == DIR:

            if tree.set(item,'file') == '..':
                head,tail=os.path.split(self.SelFullPath)
                self.EnterDir(os.path.normpath(str(pathlib.Path(self.SelFullPath).parent.absolute())),tail)
            else:
                self.EnterDir(self.SelFullPath+self.TreeFolder.set(item,'file') if self.SelFullPath=='/' else os.sep.join([self.SelFullPath,self.TreeFolder.set(item,'file')]),'..' )
                
        elif tree.set(item,'kind')!=CRC:
            self.TreeEventOpenFile()

    @StatusLineRestore
    def TreeEventOpenFile(self):
        if self.SelKind==FILE or self.SelKind==LINK or self.SelKind==SINGLE:
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
        
    SetCommonVarOS = SetCommonVarWin if windows else SetCommonVarLin
    
    def SetCommonVar(self):
        try:
            self.SetCommonVarOS()
        except Exception as e:
            pass

        self.SetCommonVarFg()

    def SetCommonVarFg(self):
        try:
            self.StatusVarFullPathLabel.config(fg = 'red' if self.SelItem and (self.TreeGroups,self.TreeFolder)[self.SelTreeIndex].tag_has(MARK,self.SelItem) else 'black')
        except Exception as e:
            pass
        
LoggingLevels={'DEBUG':logging.DEBUG,'INFO':logging.INFO,'WARNING':logging.WARNING,'ERROR':logging.ERROR,'CRITICAL':logging.CRITICAL}

if __name__ == "__main__":
    pathlib.Path(LOG_DIR).mkdir(parents=True,exist_ok=True)
    log=LOG_DIR + os.sep + time.strftime('%Y_%m_%d_%H_%M_%S',time.localtime(time.time()) ) +'.log'

    MESSAGE_LEVEL = os.environ.get('MESSAGE_LEVEL')

    logginLevel = LoggingLevels[MESSAGE_LEVEL] if MESSAGE_LEVEL in LoggingLevels else logging.INFO

    print('log:',log)
    logging.basicConfig(level=logginLevel,format='%(asctime)s %(levelname)s %(message)s', filename=log,filemode='w')
    
    ArgsQuant = len(sys.argv)
    if ArgsQuant>1:
        for i in range(1,ArgsQuant):
            self.addPath(sys.argv[i])

    try:
        Gui(os.getcwd())
    except Exception as e:
        print(e)
        logging.error(e)
