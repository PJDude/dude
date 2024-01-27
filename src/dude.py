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

from send2trash import send2trash

from fnmatch import fnmatch
from shutil import rmtree

from time import sleep,strftime,localtime,time,perf_counter

from os import sep,stat,scandir,readlink,rmdir,system,getcwd,name as os_name
from gc import disable as gc_disable, enable as gc_enable,collect as gc_collect

windows = bool(os_name=='nt')

if windows:
    from os import startfile

from os.path import abspath,normpath,dirname,join as path_join,isfile as path_isfile,split as path_split,exists as path_exists

from platform import node
from pathlib import Path
from re import search

from signal import signal,SIGINT

from configparser import ConfigParser
from subprocess import Popen

from tkinter import Tk,Toplevel,PhotoImage,Menu,PanedWindow,Label,LabelFrame,Frame,StringVar,BooleanVar

from tkinter.ttk import Checkbutton,Treeview,Scrollbar,Button,Entry,Combobox,Style

from tkinter.filedialog import askdirectory,asksaveasfilename

from collections import defaultdict
from threading import Thread
from traceback import format_stack

import sys
import logging

from core import *
import console
from dialogs import *

from dude_images import dude_image

#l_debug = logging.debug
l_info = logging.info
l_warning = logging.warning
l_error = logging.error

#log_levels={logging.DEBUG:'DEBUG',logging.INFO:'INFO'}

#core_bytes_to_str=core.bytes_to_str

###########################################################################################################################################

CFG_KEY_FULL_CRC='show_full_crc'
CFG_KEY_FULL_PATHS='show_full_paths'
CFG_KEY_CROSS_MODE='cross_mode'
CFG_KEY_REL_SYMLINKS='relative_symlinks'

CFG_KEY_USE_REG_EXPR='use_reg_expr'
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

cfg_defaults={
    CFG_KEY_FULL_CRC:False,
    CFG_KEY_FULL_PATHS:False,
    CFG_KEY_CROSS_MODE:False,
    CFG_KEY_REL_SYMLINKS:True,
    CFG_KEY_USE_REG_EXPR:False,
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
    CFG_KEY_EXCLUDE:''
}

DELETE=0
SOFTLINK=1
HARDLINK=2

NAME={DELETE:'Delete',SOFTLINK:'Softlink',HARDLINK:'Hardlink'}

HOMEPAGE='https://github.com/PJDude/dude'

#DE_NANO = 1_000_000_000

class Config:
    def __init__(self,config_dir):
        #l_debug('Initializing config: %s', config_dir)
        self.config = ConfigParser()
        self.config.add_section('main')
        self.config.add_section('geometry')

        self.path = config_dir
        self.file = self.path + '/cfg.ini'

    def write(self):
        l_info('writing config')
        Path(self.path).mkdir(parents=True,exist_ok=True)
        with open(self.file, 'w', encoding='ASCII') as configfile:
            self.config.write(configfile)

    def read(self):
        l_info('reading config')
        if path_isfile(self.file):
            try:
                with open(self.file, 'r', encoding='ASCII') as configfile:
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
            if not res:
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

class Gui:
    MAX_PATHS=8

    sel_path_full=''
    actions_processing=False

    def block_actions_processing(func):
        def block_actions_processing_wrapp(self,*args,**kwargs):

            prev_active=self.actions_processing
            self.actions_processing=False
            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('block_actions_processing_wrapp func:%s error:%s args:%s kwargs:%s' % (func.__name__,e,args,kwargs) )
                l_error('block_actions_processing_wrapp func:%s error:%s args:%s kwargs: %s',func.__name__,e,args,kwargs)
                l_error(''.join(format_stack()))
                self.get_info_dialog_on_main().show('INTERNAL ERROR block_actions_processing_wrapp',str(e))
                res=None

            self.actions_processing=prev_active

            return res
        return block_actions_processing_wrapp

    def gui_block(func):
        def gui_block_wrapp(self,*args,**kwargs):
            prev_cursor=self.menubar_cget('cursor')
            self_menubar_config = self.menubar_config
            self_main_config = self.main_config

            self.menu_disable()

            self_menubar_config(cursor='watch')
            self_main_config(cursor='watch')

            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('gui_block_wrapp func:%s error:%s args:%s kwargs:%s' % (func.__name__,e,args,kwargs) )
                l_error('gui_block_wrapp func:%s error:%s args:%s kwargs: %s',func.__name__,e,args,kwargs)
                l_error(''.join(format_stack()))
                self.get_info_dialog_on_main().show('INTERNAL ERROR gui_block_wrapp',func.__name__ + '\n' + str(e))
                res=None

            self.menu_enable()
            self_main_config(cursor=prev_cursor)
            self_menubar_config(cursor=prev_cursor)

            return res
        return gui_block_wrapp

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
            start = time()
            try:
                res=func(self,*args,**kwargs)
            except Exception as e:
                self.status('logwrapper_wrapp func:%s error:%s args:%s kwargs:%s' % (func.__name__,e,args,kwargs) )
                l_error('logwrapper_wrapp func:%s error:%s args:%s kwargs: %s',func.__name__,e,args,kwargs)
                l_error(''.join(format_stack()))
                self.get_info_dialog_on_main().show('INTERNAL ERROR logwrapper_wrapp','%s %s' % (func.__name__,str(e)) )
                res=None

            l_info("logwrapper '%s' end. BENCHMARK TIME:%s",func.__name__,time()-start)
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

    def __init__(self,cwd,paths_to_add=None,exclude=None,exclude_regexp=None,norun=None):
        gc_disable()

        self.cwd=cwd
        self.last_dir=self.cwd

        self.cfg = Config(CONFIG_DIR)
        self.cfg.read()

        self.cfg_get_bool=self.cfg.get_bool

        self.paths_to_scan_frames=[]
        self.exclude_frames=[]

        self.paths_to_scan_from_dialog=[]

        signal(SIGINT, lambda a, k : self.handle_sigint())

        self.tree_children={}
        self.tree_children_sub={} #only groups_tree has sub children

        self.two_dots_condition = lambda path : Path(path)!=Path(path).parent if path else False

        self.tagged=set()
        self.tagged_add=self.tagged.add
        self.tagged_discard=self.tagged.discard

        self.current_folder_items_tagged_discard=self.current_folder_items_tagged.discard
        self.current_folder_items_tagged_add=self.current_folder_items_tagged.add

        ####################################################################
        self_main = self.main = Tk()

        self.main_config = self.main.config

        self_main.title(f'Dude (DUplicates DEtector) {VER_TIMESTAMP}')
        self_main.protocol("WM_DELETE_WINDOW", self.delete_window_wrapper)
        self_main.withdraw()

        self.main_update = self_main.update
        self.main_update()

        self_main.minsize(800, 600)

        if self_main.winfo_screenwidth()>=1600 and self_main.winfo_screenheight()>=1024:
            self_main.geometry('1200x800')
        elif self_main.winfo_screenwidth()>=1200 and self_main.winfo_screenheight()>=800:
            self_main.geometry('1024x768')

        self_ico = self.ico = { img:PhotoImage(data = img_data) for img,img_data in dude_image.items() }

        self.icon_nr={ i:self_ico[str(i+1)] for i in range(8) }

        hg_indices=('01','02','03','04','05','06','07','08', '11','12','13','14','15','16','17','18', '21','22','23','24','25','26','27','28', '31','32','33','34','35','36','37','38',)
        self.hg_ico={ i:self_ico[str('hg'+j)] for i,j in enumerate(hg_indices) }

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

        self_main_bind('<KeyPress-F2>', lambda event : self.get_settings_dialog().show())
        self_main_bind('<KeyPress-F1>', lambda event : self.get_about_dialog().show())
        self_main_bind('<KeyPress-s>', lambda event : self.scan_dialog_show())
        self_main_bind('<KeyPress-S>', lambda event : self.scan_dialog_show())

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

        style.theme_create("dummy", parent='vista' if windows else 'clam' )

        self.bg_color = style.lookup('TFrame', 'background')

        style.theme_use("dummy")

        style_configure = style.configure

        style_configure("TButton", anchor = "center")
        style_configure("TButton", background = self.bg_color)

        style_configure("TCheckbutton", background = self.bg_color)
        style_configure("TCombobox", borderwidth=2,highlightthickness=1,bordercolor='darkgray')

        style_map = style.map

        style_map("TButton",  relief=[('disabled',"flat"),('',"raised")] )
        style_map("TButton",  fg=[('disabled',"gray"),('',"black")] )

        style_map("Treeview.Heading",  relief=[('','raised')] )
        style_configure("Treeview",rowheight=18)

        bg_focus='#90DD90'
        bg_focus_off='#90AA90'
        bg_sel='#AAAAAA'

        style_map('Treeview', background=[('focus',bg_focus),('selected',bg_sel),('','white')])

        style_map('semi_focus.Treeview', background=[('focus',bg_focus),('selected',bg_focus_off),('','white')])
        style_map('no_focus.Treeview', background=[('focus',bg_focus),('selected',bg_sel),('','white')])
        #style_map('no_focus.Treeview', background=[('focus',bg_sel),('selected',bg_sel),('','white')])

        #works but not for every theme
        #style_configure("Treeview", fieldbackground=self.bg_color)

        #######################################################################
        self.menubar = Menu(self_main,bg=self.bg_color)
        self_main.config(menu=self.menubar)
        #######################################################################

        self.my_next_dict={}
        self.my_prev_dict={}

        self.tooltip_message={}

        self.menubar_config = self.menubar.config
        self.menubar_cget = self.menubar.cget

        self.menubar_entryconfig = self.menubar.entryconfig
        self.menubar_norm = lambda x : self.menubar_entryconfig(x, state="normal")
        self.menubar_disable = lambda x : self.menubar_entryconfig(x, state="disabled")

        self.paned = PanedWindow(self_main,orient='vertical',relief='sunken',showhandle=0,bd=0,bg=self.bg_color,sashwidth=2,sashrelief='flat')
        self.paned.pack(fill='both',expand=1)

        frame_groups = Frame(self.paned,bg=self.bg_color)
        frame_groups.pack(fill='both',expand='yes')
        self.paned.add(frame_groups)

        frame_folder = Frame(self.paned,bg=self.bg_color)
        frame_folder.pack(fill='both',expand='yes')
        self.paned.add(frame_folder)

        (status_frame_groups := Frame(frame_groups,bg=self.bg_color)).pack(side='bottom', fill='both')

        self.status_all_quant=Label(status_frame_groups,width=10,borderwidth=2,bg=self.bg_color,relief='groove',foreground='red',anchor='w')
        self.status_all_quant_configure = self.status_all_quant.configure

        self.status_all_quant.pack(fill='x',expand=0,side='right')
        Label(status_frame_groups,width=16,text="All marked files # ",relief='groove',borderwidth=2,bg=self.bg_color,anchor='e').pack(fill='x',expand=0,side='right')
        self.status_all_size=Label(status_frame_groups,width=10,borderwidth=2,bg=self.bg_color,relief='groove',foreground='red',anchor='w')
        self.status_all_size.pack(fill='x',expand=0,side='right')
        self.status_all_size_configure=self.status_all_size.configure

        Label(status_frame_groups,width=18,text='All marked files size: ',relief='groove',borderwidth=2,bg=self.bg_color,anchor='e').pack(fill='x',expand=0,side='right')
        self.status_groups=Label(status_frame_groups,text='0',image=self.ico_empty,width=80,compound='right',borderwidth=2,bg=self.bg_color,relief='groove',anchor='e')
        self.status_groups_configure = self.status_groups.configure

        self.status_groups.pack(fill='x',expand=0,side='right')

        self.status_groups.bind("<Motion>", lambda event : self.motion_on_widget(event,'Number of groups with consideration od "cross paths" option'))
        self.status_groups.bind("<Leave>", lambda event : self.widget_leave())

        Label(status_frame_groups,width=10,text='Groups: ',relief='groove',borderwidth=2,bg=self.bg_color,anchor='e').pack(fill='x',expand=0,side='right')

        self.status_path = Label(status_frame_groups,text='',relief='flat',borderwidth=1,bg=self.bg_color,anchor='w')
        self.status_path.pack(fill='x',expand=1,side='left')
        self.status_path.bind("<Motion>", lambda event : self.motion_on_widget(event,'The full path of a directory shown in the bottom panel.'))
        self.status_path.bind("<Leave>", lambda event : self.widget_leave())

        self.status_path_configure=self.status_path.configure
        ###############################################################################

        (status_frame_folder := Frame(frame_folder,bg=self.bg_color)).pack(side='bottom',fill='both')

        self.status_line_lab=Label(status_frame_folder,width=30,image=self_ico['expression'],compound= 'left',text='',borderwidth=2,bg=self.bg_color,relief='groove',anchor='w')
        self.status_line_lab.pack(fill='x',expand=1,side='left')
        self.status_line_lab_configure = self.status_line_lab.configure
        self.status_line_lab_update = self.status_line_lab.update

        self.status_folder_quant=Label(status_frame_folder,width=10,borderwidth=2,bg=self.bg_color,relief='groove',foreground='red',anchor='w')
        self.status_folder_quant.pack(fill='x',expand=0,side='right')
        self.status_folder_quant_configure=self.status_folder_quant.configure

        Label(status_frame_folder,width=16,text='Marked files # ',relief='groove',borderwidth=2,bg=self.bg_color,anchor='e').pack(fill='x',expand=0,side='right')
        self.status_folder_size=Label(status_frame_folder,width=10,borderwidth=2,bg=self.bg_color,relief='groove',foreground='red',anchor='w')
        self.status_folder_size.pack(expand=0,side='right')
        self.status_folder_size_configure=self.status_folder_size.configure

        Label(status_frame_folder,width=18,text='Marked files size: ',relief='groove',borderwidth=2,bg=self.bg_color,anchor='e').pack(fill='x',expand=0,side='right')

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
        self.groups_tree_set = self_groups_tree.set
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

        self.vsb1 = Scrollbar(frame_groups, orient='vertical', command=self_groups_tree.yview,takefocus=False)

        self_groups_tree.configure(yscrollcommand=self.vsb1.set)

        self.vsb1.pack(side='right',fill='y',expand=0)
        self_groups_tree.pack(fill='both',expand=1, side='left')

        self_groups_tree.bind('<Double-Button-1>', self.double_left_button)

        self.folder_tree=Treeview(frame_folder,takefocus=True,selectmode='none')
        self_folder_tree = self.folder_tree

        self.tree_children[self.folder_tree]=[]

        self.folder_tree_see = self_folder_tree.see

        self.folder_tree_set_item = lambda item,x : self_folder_tree.set(item,x)

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

        for tree in (self_groups_tree,self_folder_tree):
            tree_heading = tree.heading
            for col in tree["displaycolumns"]:
                if col in self_org_label:
                    tree_heading(col,text=self_org_label[col])

        self_folder_tree_heading('file', text='File \u25B2')

        self.vsb2 = Scrollbar(frame_folder, orient='vertical', command=self_folder_tree.yview,takefocus=False)
        #,bg=self.bg_color
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
        self_folder_tree_tag_configure(self.DIR, foreground='blue2')
        self_folder_tree_tag_configure(self.DIRLINK, foreground='blue2')
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
            cfg_geometry=self.cfg.get('main','',section='geometry')

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

        self.popup_groups = Menu(self_groups_tree, tearoff=0,bg=self.bg_color)
        self.popup_groups_unpost = self.popup_groups.unpost
        self.popup_groups.bind("<FocusOut>",lambda event : self.popup_groups_unpost() )

        self.popup_folder = Menu(self_folder_tree, tearoff=0,bg=self.bg_color)
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
        #######################################################################
        #scan dialog

        self_scan_dialog = self.scan_dialog=GenericDialog(self_main,self.main_icon_tuple,self.bg_color,'Scan',pre_show=self.pre_show,post_close=self.post_close)

        self.log_skipped_var=BooleanVar()
        self.log_skipped_var.set(False)

        self_scan_dialog_area_main = self_scan_dialog.area_main

        self_scan_dialog_area_main.grid_columnconfigure(0, weight=1)
        self_scan_dialog_area_main.grid_rowconfigure(0, weight=1)
        self_scan_dialog_area_main.grid_rowconfigure(1, weight=1)

        self_scan_dialog_widget_bind = self_scan_dialog.widget.bind

        self_scan_dialog_widget_bind('<Alt_L><a>',lambda event : self.path_to_scan_add_dialog())
        self_scan_dialog_widget_bind('<Alt_L><A>',lambda event : self.path_to_scan_add_dialog())
        self_scan_dialog_widget_bind('<Alt_L><s>',lambda event : self.scan_wrapper())
        self_scan_dialog_widget_bind('<Alt_L><S>',lambda event : self.scan_wrapper())
        self_scan_dialog_widget_bind('<Alt_L><E>',lambda event : self.exclude_mask_add_dialog())
        self_scan_dialog_widget_bind('<Alt_L><e>',lambda event : self.exclude_mask_add_dialog())

        ##############
        temp_frame = LabelFrame(self_scan_dialog_area_main,text='Paths To scan:',borderwidth=2,bg=self.bg_color,takefocus=False)
        temp_frame.grid(row=0,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        sf_par=SFrame(temp_frame,bg=self.bg_color)
        sf_par.pack(fill='both',expand=True,side='top')
        self.paths_frame=sf_par.frame()

        buttons_fr = Frame(temp_frame,bg=self.bg_color,takefocus=False)
        buttons_fr.pack(fill='both',expand=False,side='bottom')

        self.add_path_button = Button(buttons_fr,width=18,image = self_ico['open'], command=self.path_to_scan_add_dialog,underline=0)
        self.add_path_button.pack(side='left',pady=4,padx=4)

        self.add_path_button.bind("<Motion>", lambda event : self.motion_on_widget(event,"Add path to scan.\nA maximum of 8 paths are allowed."))
        self.add_path_button.bind("<Leave>", lambda event : self.widget_leave())

        self.paths_frame.grid_columnconfigure(1, weight=1)
        self.paths_frame.grid_rowconfigure(99, weight=1)

        ##############
        self.exclude_regexp_scan=BooleanVar()

        temp_frame2 = LabelFrame(self_scan_dialog_area_main,text='Exclude from scan:',borderwidth=2,bg=self.bg_color,takefocus=False)
        temp_frame2.grid(row=1,column=0,sticky='news',padx=4,pady=4,columnspan=4)

        sf_par2=SFrame(temp_frame2,bg=self.bg_color)
        sf_par2.pack(fill='both',expand=True,side='top')
        self.exclude_frame=sf_par2.frame()

        buttons_fr2 = Frame(temp_frame2,bg=self.bg_color,takefocus=False)
        buttons_fr2.pack(fill='both',expand=False,side='bottom')

        self.add_exclude_button_dir = Button(buttons_fr2,width=18,image = self_ico['open'],command=self.exclude_mask_add_dir)
        self.add_exclude_button_dir.pack(side='left',pady=4,padx=4)
        self.add_exclude_button_dir.bind("<Motion>", lambda event : self.motion_on_widget(event,"Add path as exclude expression ..."))
        self.add_exclude_button_dir.bind("<Leave>", lambda event : self.widget_leave())

        self.add_exclude_button = Button(buttons_fr2,width=18,image= self_ico['expression'],command=self.exclude_mask_add_dialog,underline=4)

        tooltip_string = 'Add expression ...\nduring the scan, the entire path is checked \nagainst the specified expression,\ne.g.' + ('*windows* etc. (without regular expression)\nor .*windows.*, etc. (with regular expression)' if windows else '*.git* etc. (without regular expression)\nor .*\\.git.* etc. (with regular expression)')
        self.add_exclude_button.bind("<Motion>", lambda event : self.motion_on_widget(event,tooltip_string))
        self.add_exclude_button.bind("<Leave>", lambda event : self.widget_leave())

        self.add_exclude_button.pack(side='left',pady=4,padx=4)

        Checkbutton(buttons_fr2,text='treat as a regular expression',variable=self.exclude_regexp_scan,command=self.exclude_regexp_set).pack(side='left',pady=4,padx=4)

        self.exclude_frame.grid_columnconfigure(1, weight=1)
        self.exclude_frame.grid_rowconfigure(99, weight=1)
        ##############

        skip_button = Checkbutton(self_scan_dialog_area_main,text='log skipped files',variable=self.log_skipped_var)
        skip_button.grid(row=3,column=0,sticky='news',padx=8,pady=3,columnspan=3)

        skip_button.bind("<Motion>", lambda event : self.motion_on_widget(event,"log every skipped file (softlinks, hardlinks, excluded, no permissions etc.)"))
        skip_button.bind("<Leave>", lambda event : self.widget_leave())

        self.scan_button = Button(self_scan_dialog.area_buttons,width=12,text="Scan",image=self_ico['scan'],compound='left',command=self.scan_wrapper,underline=0)
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
            if self.actions_processing:
                self_file_cascade_add_command = self.file_cascade.add_command
                self_file_cascade_add_separator = self.file_cascade.add_separator

                item_actions_state=('disabled','normal')[self.sel_item is not None]
                self_file_cascade_add_command(label = 'Scan ...',command = self.scan_dialog_show, accelerator="S",image = self_ico['scan'],compound='left')
                self_file_cascade_add_separator()
                self_file_cascade_add_command(label = 'Settings ...',command=lambda : self.get_settings_dialog().show(), accelerator="F2",image = self_ico['settings'],compound='left')
                self_file_cascade_add_separator()
                self_file_cascade_add_command(label = 'Remove empty folders in specified directory ...',command=self.empty_folder_remove_ask,image = self.ico_empty,compound='left')
                self_file_cascade_add_separator()
                self_file_cascade_add_command(label = 'Save CSV',command = self.csv_save,state=item_actions_state,image = self.ico_empty,compound='left')
                self_file_cascade_add_separator()
                self_file_cascade_add_command(label = 'Erase CRC Cache',command = self.cache_clean,image = self.ico_empty,compound='left')
                self_file_cascade_add_separator()
                self_file_cascade_add_command(label = 'Exit',command = self.exit,image = self_ico['exit'],compound='left')

        self.file_cascade= Menu(self.menubar,tearoff=0,bg=self.bg_color,postcommand=file_cascade_post)
        self.menubar.add_cascade(label = 'File',menu = self.file_cascade,accelerator="Alt+F")

        def navi_cascade_post():
            self.hide_tooltip()
            self.popup_groups_unpost()
            self.popup_folder_unpost()

            self.navi_cascade.delete(0,'end')
            if self.actions_processing:
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

        self.navi_cascade= Menu(self.menubar,tearoff=0,bg=self.bg_color,postcommand=navi_cascade_post)

        self.menubar.add_cascade(label = 'Navigation',menu = self.navi_cascade)

        def help_cascade_post():
            self.hide_tooltip()
            self.popup_groups_unpost()
            self.popup_folder_unpost()

            self.help_cascade.delete(0,'end')
            if self.actions_processing:

                self_help_cascade_add_command = self.help_cascade.add_command
                self_help_cascade_add_separator = self.help_cascade.add_separator

                self_help_cascade_add_command(label = 'About',command=lambda : self.get_about_dialog().show(),accelerator="F1", image = self_ico['about'],compound='left')
                self_help_cascade_add_command(label = 'License',command=lambda : self.get_license_dialog().show(), image = self_ico['license'],compound='left')
                self_help_cascade_add_separator()
                self_help_cascade_add_command(label = 'Open current Log',command=self.show_log, image = self_ico['log'],compound='left')
                self_help_cascade_add_command(label = 'Open logs directory',command=self.show_logs_dir, image = self_ico['logs'],compound='left')
                self_help_cascade_add_separator()
                self_help_cascade_add_command(label = 'Open homepage',command=self.show_homepage, image = self_ico['home'],compound='left')

        self.help_cascade= Menu(self.menubar,tearoff=0,bg=self.bg_color,postcommand=help_cascade_post)

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

        self_groups_tree.bind("<Leave>", lambda event : self.widget_leave())
        self_folder_tree.bind("<Leave>", lambda event : self.widget_leave())

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

        self.paned.update()
        self.paned.sash_place(0,0,self.cfg.get('sash_coord',400,section='geometry'))

        #prevent displacement
        if cfg_geometry :
            self_main.geometry(cfg_geometry)

        self.main_update()

        self.scan_dialog_show(run_scan_condition)

        self_groups_tree.focus_set()

        gc_collect()
        gc_enable()

        self.actions_processing=True

        self_main.mainloop()
        #######################################################################

    def pre_show(self,on_main_window_dialog=True,new_widget=None):
        self.menubar_unpost()
        self.hide_tooltip()
        self.popup_groups_unpost()
        self.popup_folder_unpost()

        if on_main_window_dialog:
            if new_widget:
                self.main_locked_by_child=new_widget

            self.actions_processing=False
            self.menu_disable()
            self.menubar_config(cursor="watch")

    def post_close(self,on_main_window_dialog=True):
        if on_main_window_dialog:
            self.actions_processing=True
            self.menu_enable()
            self.menubar_config(cursor="")

    def pre_show_settings(self,on_main_window_dialog=True,new_widget=None):
        _ = {var.set(self.cfg_get_bool(key)) for var,key in self.settings}
        _ = {var.set(self.cfg.get(key)) for var,key in self.settings_str}
        return self.pre_show(on_main_window_dialog=on_main_window_dialog,new_widget=new_widget)

    def widget_tooltip(self,widget,tooltip):
        widget.bind("<Motion>", lambda event : self.motion_on_widget(event,tooltip))
        widget.bind("<Leave>", lambda event : self.widget_leave())

    def fix_text_dialog(self,dialog):
        dialog.find_lab.configure(image=self.ico_search_text,text=' Search:',compound='left',bg=self.bg_color)
        dialog.find_prev_butt.configure(image=self.ico_left)
        dialog.find_next_butt.configure(image=self.ico_right)

        self.widget_tooltip(dialog.find_prev_butt,'Find Prev (Shift+F3)')
        self.widget_tooltip(dialog.find_next_butt,'Find Next (F3)')

    #######################################################################
    settings_dialog_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_settings_dialog(self):
        if not self.settings_dialog_created:
            self.status("Creating dialog ...")

            self.settings_dialog=GenericDialog(self.main,self.main_icon_tuple,self.bg_color,'Settings',pre_show=self.pre_show_settings,post_close=self.post_close)

            self.show_full_crc = BooleanVar()
            self.show_full_paths = BooleanVar()
            self.cross_mode = BooleanVar()

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
                (self.show_full_paths,CFG_KEY_FULL_PATHS),
                (self.cross_mode,CFG_KEY_CROSS_MODE),
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
                (self.file_open_wrapper,CFG_KEY_WRAPPER_FILE),
                (self.folders_open_wrapper,CFG_KEY_WRAPPER_FOLDERS),
                (self.folders_open_wrapper_params,CFG_KEY_WRAPPER_FOLDERS_PARAMS)
            ]

            row = 0
            label_frame=LabelFrame(self.settings_dialog.area_main, text="Main panels",borderwidth=2,bg=self.bg_color)
            label_frame.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

            (cb_1:=Checkbutton(label_frame, text = 'Show full CRC', variable=self.show_full_crc)).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
            cb_1.bind("<Motion>", lambda event : self.motion_on_widget(event,'If disabled, shortest necessary prefix of full CRC wil be shown'))
            cb_1.bind("<Leave>", lambda event : self.widget_leave())

            (cb_2:=Checkbutton(label_frame, text = 'Show full scan paths', variable=self.show_full_paths)).grid(row=1,column=0,sticky='wens',padx=3,pady=2)
            cb_2.bind("<Motion>", lambda event : self.motion_on_widget(event,'If disabled, scan path symbols will be shown instead of full paths\nfull paths are always displayed as tooltips'))
            cb_2.bind("<Leave>", lambda event : self.widget_leave())

            (cb_3:=Checkbutton(label_frame, text = '"Cross paths" mode', variable=self.cross_mode)).grid(row=2,column=0,sticky='wens',padx=3,pady=2)
            cb_3.bind("<Motion>", lambda event : self.motion_on_widget(event,'Ignore (hide) CRC groups containing duplicates in only one search path.\nShow only groups with files in different search paths.\nIn this mode, you can treat one search path as a "reference"\nand delete duplicates in all other paths with ease'))
            cb_3.bind("<Leave>", lambda event : self.widget_leave())

            label_frame=LabelFrame(self.settings_dialog.area_main, text="Confirmation dialogs",borderwidth=2,bg=self.bg_color)
            label_frame.grid(row=row,column=0,sticky='wens',padx=3,pady=3) ; row+=1

            (cb_3:=Checkbutton(label_frame, text = 'Skip groups with invalid selection', variable=self.skip_incorrect_groups)).grid(row=0,column=0,sticky='wens',padx=3,pady=2)
            cb_3.bind("<Motion>", lambda event : self.motion_on_widget(event,'Groups with incorrect marks set will abort action.\nEnable this option to skip those groups.\nFor delete or soft-link action, one file in a group \nmust remain unmarked (see below). For hardlink action,\nmore than one file in a group must be marked.'))
            cb_3.bind("<Leave>", lambda event : self.widget_leave())

            (cb_4:=Checkbutton(label_frame, text = 'Allow deletion of all copies', variable=self.allow_delete_all,image=self.ico_warning,compound='right')).grid(row=1,column=0,sticky='wens',padx=3,pady=2)
            cb_4.bind("<Motion>", lambda event : self.motion_on_widget(event,'Before deleting selected files, files selection in every CRC \ngroup is checked, at least one file should remain unmarked.\nIf This option is enabled it will be possible to delete all copies'))
            cb_4.bind("<Leave>", lambda event : self.widget_leave())

            Checkbutton(label_frame, text = 'Show soft links targets', variable=self.confirm_show_links_targets ).grid(row=2,column=0,sticky='wens',padx=3,pady=2)
            Checkbutton(label_frame, text = 'Show CRC and size', variable=self.confirm_show_crc_and_size ).grid(row=3,column=0,sticky='wens',padx=3,pady=2)

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
            en_1.bind("<Motion>", lambda event : self.motion_on_widget(event,'Command executed on "Open File" with full file path as parameter.\nIf empty, default os association will be executed.'))
            en_1.bind("<Leave>", lambda event : self.widget_leave())

            Label(label_frame,text='Folders: ',bg=self.bg_color,anchor='w').grid(row=2, column=0,sticky='news')
            (en_2:=Entry(label_frame,textvariable=self.folders_open_wrapper)).grid(row=2, column=1,sticky='news',padx=3,pady=2)
            en_2.bind("<Motion>", lambda event : self.motion_on_widget(event,'Command executed on "Open Folder" with full path as parameter.\nIf empty, default os filemanager will be used.'))
            en_2.bind("<Leave>", lambda event : self.widget_leave())
            (cb_2:=Combobox(label_frame,values=('1','2','3','4','5','6','7','8','all'),textvariable=self.folders_open_wrapper_params,state='readonly')).grid(row=2, column=2,sticky='ew',padx=3)
            cb_2.bind("<Motion>", lambda event : self.motion_on_widget(event,'Number of parameters (paths) passed to\n"Opening wrapper" (if defined) when action\nis performed on crc groups\ndefault is 2'))
            cb_2.bind("<Leave>", lambda event : self.widget_leave())

            label_frame.grid_columnconfigure(1, weight=1)

            bfr=Frame(self.settings_dialog.area_main,bg=self.bg_color)
            self.settings_dialog.area_main.grid_rowconfigure(row, weight=1); row+=1

            bfr.grid(row=row,column=0) ; row+=1

            Button(bfr, text='Set defaults',width=14, command=self.settings_reset).pack(side='left', anchor='n',padx=5,pady=5)
            Button(bfr, text='OK', width=14, command=self.settings_ok ).pack(side='left', anchor='n',padx=5,pady=5)
            self.cancel_button=Button(bfr, text='Cancel', width=14 ,command=self.settings_dialog.hide )
            self.cancel_button.pack(side='right', anchor='n',padx=5,pady=5)

            self.settings_dialog.area_main.grid_columnconfigure(0, weight=1)

            self.settings_dialog_created = True

        return self.settings_dialog

    info_dialog_on_main_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_info_dialog_on_main(self):
        if not self.info_dialog_on_main_created:
            self.status("Creating dialog ...")

            self.info_dialog_on_main = LabelDialog(self.main,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)

            self.info_dialog_on_main_created = True

        return self.info_dialog_on_main

    text_ask_dialog_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_text_ask_dialog(self):
        if not self.text_ask_dialog_created:
            self.status("Creating dialog ...")

            self.text_ask_dialog = TextDialogQuestion(self.main,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close,image=self.ico_warning)
            self.fix_text_dialog(self.text_ask_dialog)

            self.text_ask_dialog_created = True

        return self.text_ask_dialog

    text_info_dialog_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_text_info_dialog(self):
        if not self.text_info_dialog_created:
            self.status("Creating dialog ...")

            self.text_info_dialog = TextDialogInfo(self.main,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)
            self.fix_text_dialog(self.text_info_dialog)

            self.text_info_dialog_created = True

        return self.text_info_dialog

    info_dialog_on_scan_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_info_dialog_on_scan(self):
        if not self.info_dialog_on_scan_created:
            self.status("Creating dialog ...")

            self.info_dialog_on_scan = LabelDialog(self.scan_dialog.widget,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)

            self.info_dialog_on_scan_created = True

        return self.info_dialog_on_scan

    exclude_dialog_on_scan_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_exclude_dialog_on_scan(self):
        if not self.exclude_dialog_on_scan_created:
            self.status("Creating dialog ...")

            self.exclude_dialog_on_scan = EntryDialogQuestion(self.scan_dialog.widget,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)

            self.exclude_dialog_on_scan_created = True

        return self.exclude_dialog_on_scan


    progress_dialog_on_scan_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_progress_dialog_on_scan(self):
        if not self.progress_dialog_on_scan_created:
            self.status("Creating dialog ...")

            self.progress_dialog_on_scan = ProgressDialog(self.scan_dialog.widget,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)
            self.progress_dialog_on_scan.command_on_close = self.progress_dialog_abort

            self.progress_dialog_on_scan.abort_button.bind("<Leave>", lambda event : self.widget_leave())
            self.progress_dialog_on_scan.abort_button.bind("<Motion>", lambda event : self.motion_on_widget(event) )


            self.progress_dialog_on_scan_created = True

        return self.progress_dialog_on_scan


    mark_dialog_on_groups_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_mark_dialog_on_groups(self):
        if not self.mark_dialog_on_groups_created:
            self.status("Creating dialog ...")

            self.mark_dialog_on_groups = CheckboxEntryDialogQuestion(self.groups_tree,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)

            self.mark_dialog_on_groups_created = True

            self.get_info_dialog_on_mark_groups()

        return self.mark_dialog_on_groups

    mark_dialog_on_folder_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_mark_dialog_on_folder(self):
        if not self.mark_dialog_on_folder_created:
            self.status("Creating dialog ...")

            self.mark_dialog_on_folder = CheckboxEntryDialogQuestion(self.folder_tree,self.main_icon_tuple,self.bg_color,pre_show=self.pre_show,post_close=self.post_close)

            self.mark_dialog_on_folder_created = True

            self.get_info_dialog_on_mark_folder()

        return self.mark_dialog_on_folder

    info_dialog_on_mark_groups_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_info_dialog_on_mark_groups(self):
        if not self.info_dialog_on_mark_groups_created:
            self.status("Creating dialog ...")

            self.info_dialog_on_mark[self.groups_tree] = LabelDialog(self.mark_dialog_on_groups.widget,self.main_icon_tuple,self.bg_color,pre_show=lambda new_widget: self.pre_show(on_main_window_dialog=False,new_widget=new_widget),post_close=lambda : self.post_close(False))

            self.info_dialog_on_mark_groups_created = True

        return self.info_dialog_on_mark[self.groups_tree]

    info_dialog_on_mark_folder_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_info_dialog_on_mark_folder(self):
        if not self.info_dialog_on_mark_folder_created:
            self.status("Creating dialog ...")

            self.info_dialog_on_mark[self.folder_tree] = LabelDialog(self.mark_dialog_on_folder.widget,self.main_icon_tuple,self.bg_color,pre_show=lambda new_widget: self.pre_show(on_main_window_dialog=False,new_widget=new_widget),post_close=lambda : self.post_close(False))

            self.info_dialog_on_mark_folder_created = True

        return self.info_dialog_on_mark[self.folder_tree]


    find_dialog_on_groups_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_find_dialog_on_groups(self):
        if not self.find_dialog_on_groups_created:
            self.status("Creating dialog ...")

            self.find_dialog_on_groups = FindEntryDialog(self.groups_tree,self.main_icon_tuple,self.bg_color,self.find_mod,self.find_prev_from_dialog,self.find_next_from_dialog,pre_show=self.pre_show,post_close=self.post_close)

            self.info_dialog_on_find[self.groups_tree] = LabelDialog(self.find_dialog_on_groups.widget,self.main_icon_tuple,self.bg_color,pre_show=lambda new_widget: self.pre_show(on_main_window_dialog=False,new_widget=new_widget),post_close=lambda : self.post_close(False))

            self.find_dialog_on_groups_created = True

        return self.find_dialog_on_groups

    find_dialog_on_folder_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
    def get_find_dialog_on_folder(self):
        if not self.find_dialog_on_folder_created:
            self.status("Creating dialog ...")

            self.find_dialog_on_folder = FindEntryDialog(self.folder_tree,self.main_icon_tuple,self.bg_color,self.find_mod,self.find_prev_from_dialog,self.find_next_from_dialog,pre_show=self.pre_show,post_close=self.post_close)

            self.info_dialog_on_find[self.folder_tree] = LabelDialog(self.find_dialog_on_folder.widget,self.main_icon_tuple,self.bg_color,pre_show=lambda new_widget: self.pre_show(on_main_window_dialog=False,new_widget=new_widget),post_close=lambda : self.post_close(False))

            self.find_dialog_on_folder_created = True

        return self.find_dialog_on_folder

    about_dialog_created = False
    @restore_status_line
    @block_actions_processing
    @gui_block
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

            #'LOGGING LEVEL      :  ' + log_levels[LOG_LEVEL] + '\n\n' + \

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
    @block_actions_processing
    @gui_block
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
        #print(f'semi_selection:{tree}')
        if tree==self.main.focus_get():
            tree.focus(item)
        else:
            tree.selection_set(item)

        self.selected[tree]=item

    def groups_tree_focus_out(self):
        self_groups_tree = self.groups_tree
        item=self_groups_tree.focus()
        if item:
            self_groups_tree.selection_set(item)
            self.selected[self_groups_tree]=item

    def folder_tree_focus_out(self):
        self_folder_tree = self.folder_tree
        item = self_folder_tree.focus()
        if item:
            self_folder_tree.selection_set(item)
            self.selected[self_folder_tree]=item

    def groups_tree_focus_in(self):
        #print('groups_tree_focus_in',str(event.type),dir(event.type))
        tree=self.groups_tree
        self.sel_tree=tree

        if item:=self.selected[tree]:
            tree.focus(item)
            tree.selection_remove(item)
            self.groups_tree_sel_change(item,True)

        tree.configure(style='semi_focus.Treeview')
        self.other_tree[tree].configure(style='no_focus.Treeview')
        #print('groups_tree_focus_in',str(event.type),'end')

    def folder_tree_focus_in(self):
        #print('folder_tree_focus_in',str(event.type),dir(event.type))
        tree = self.folder_tree
        self.sel_tree=tree

        if item:=self.selected[tree]:
            tree.focus(item)
            tree.selection_remove(item)

        tree.configure(style='semi_focus.Treeview')
        self.other_tree[tree].configure(style='no_focus.Treeview')
        #print('folder_tree_focus_in',str(event.type),'end')

    def focusin(self):
        #print('focusin')
        if self.main_locked_by_child:
            self.main_locked_by_child.focus_set()

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
        if message:
            self.tooltip_message[str(event.widget)]=message
        self.tooltip_show_after_widget = event.widget.after(1, self.show_tooltip_widget(event))

    def motion_on_groups_tree(self,event):
        if self.actions_processing:
            self.tooltip_show_after_groups = event.widget.after(1, self.show_tooltip_groups(event))

    def motion_on_folder_tree(self,event):
        if self.actions_processing:
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
                    self.tooltip_lab_configure(text='Sort by %s' % self.org_label[colname])
                    self.tooltip_deiconify()
                else:
                    self.hide_tooltip()

            elif item := tree.identify('item', event.x, event.y):
                pathnrstr=tree.set(item,'pathnr')
                if col=="#0" :
                    if pathnrstr:
                        pathnr=int(pathnrstr)
                        if tree.set(item,'kind')==self.FILE:
                            self.tooltip_lab_configure(text='%s - %s' % (pathnr+1,dude_core.scanned_paths[pathnr]) )
                            self.tooltip_deiconify()

                    else:
                        crc=item
                        self.tooltip_lab_configure(text='CRC: %s' % crc )
                        self.tooltip_deiconify()

                elif col:

                    coldata=tree.set(item,col)

                    if coldata:
                        self.tooltip_lab_configure(text=coldata)
                        self.tooltip_deiconify()

                    else:
                        self.hide_tooltip()

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
                    self.tooltip_lab_configure(text='Sort by %s' % self.org_label[colname])
                    self.tooltip_deiconify()
                else:
                    self.hide_tooltip()
            elif item := tree.identify('item', event.x, event.y):

                coldata=''
                #KIND_INDEX=3
                kind=tree.set(item,3)
                if kind==self.LINK:
                    coldata='(soft-link)'
                elif kind==self.DIRLINK:
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
                #    file_path = abspath(dude_core.get_full_path_scanned(pathnr,path,file))
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
            l_error(e)

    def menu_disable(self):
        disable = self.menubar_disable

        self.menu_state_stack_append('x')
        disable("File")
        disable("Navigation")
        disable("Help")
        #self.menubar.update()

    def reset_sels(self):
        self.sel_pathnr = None
        self.sel_path = None
        self.sel_file = None
        self.sel_crc = None
        self.sel_item = None

        self.sel_tree=self.groups_tree

        self.sel_kind = None

    def get_index_tuple_groups_tree(self,item):
        self_groups_tree_set = lambda x : self.groups_tree_set(item,x)
        int_self_groups_tree_set = lambda x : int(self_groups_tree_set(x))

        #pathnr,path,file,ctime,dev,inode
        return (\
                int_self_groups_tree_set('pathnr'),\
                self_groups_tree_set('path'),\
                self_groups_tree_set('file'),\
                int_self_groups_tree_set('ctime'),\
                int_self_groups_tree_set('dev'),\
                int_self_groups_tree_set('inode')
        )

    def delete_window_wrapper(self):
        if self.actions_processing:
            self.exit()
        else:
            self.status('WM_DELETE_WINDOW NOT exiting ...')

    def exit(self):
        try:
            self.cfg.set('main',str(self.main.geometry()),section='geometry')
            coords=self.paned.sash_coord(0)
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

        if self.sel_tree==self.groups_tree:
            self.get_find_dialog_on_groups().show('Find',scope_info,initial=initialvalue,checkbutton_text='treat as a regular expression',checkbutton_initial=False)
            self.find_by_tree[tree]=self.find_dialog_on_groups.entry.get()
        else:
            self.get_find_dialog_on_folder().show('Find',scope_info,initial=initialvalue,checkbutton_text='treat as a regular expression',checkbutton_initial=False)
            self.find_by_tree[tree]=self.find_dialog_on_folder.entry.get()

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
            self.cfg.set_bool(CFG_KEY_USE_REG_EXPR,use_reg_expr)
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
                            #if tree.set(item,'kind')==self.FILE:
                            file=self.folder_tree.set(item,'file')
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
                self.tag_toggle_selected(tree, *tree_children_sub[item] )

        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    KEY_DIRECTION={}
    KEY_DIRECTION['Prior']=-1
    KEY_DIRECTION['Next']=1
    KEY_DIRECTION['Home']=0
    KEY_DIRECTION['End']=-1

    reftuple1=('1','2','3','4','5','6','7')
    reftuple2=('exclam','at','numbersign','dollar','percent','asciicircum','ampersand')

    @block_actions_processing
    @gui_block
    def goto_next_prev_crc(self,direction):
        status ='selecting next CRC group' if direction==1 else 'selecting prev CRC group'

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

    @block_actions_processing
    @gui_block
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
                tree.focus(current_item)
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
                self.folder_tree_see(next_item)
                self.folder_tree.focus(next_item)
                self.folder_tree_sel_change(next_item)
                self.folder_tree.update()

    def key_press(self,event):
        if self.actions_processing:
            #t0=perf_counter()

            self.main_unbind_class('Treeview','<KeyPress>')

            self.hide_tooltip()
            self.menubar_unpost()
            self.popup_groups_unpost()
            self.popup_folder_unpost()

            #t1=perf_counter()
            try:
                tree,key=event.widget,event.keysym
                item=tree.focus()

                if not item:
                    #t_children=self.tree_children[tree]
                    #item=self.tree_children[tree][0]
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
                            if tree.set(item,'kind')==self.CRC:
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
                        if tree==self.groups_tree:
                            self.process_files_in_groups_wrapper((SOFTLINK,HARDLINK)[shift_pressed],ctrl_pressed)
                        else:
                            self.process_files_in_folder_wrapper((SOFTLINK,HARDLINK)[shift_pressed],self.sel_kind in (self.DIR,self.DIRLINK))
                    elif key=='F5':
                        self.goto_max_folder(1,-1 if shift_pressed else 1)
                    elif key=='F6':
                        self.goto_max_folder(0,-1 if shift_pressed else 1)
                    elif key=='F7':
                        self.goto_max_group(1,-1 if shift_pressed else 1)
                    elif key=='F8':
                        self.goto_max_group(0,-1 if shift_pressed else 1)
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

            except Exception as e:
                l_error(f'key_press error:{e}')
                self.get_info_dialog_on_main().show('INTERNAL ERROR','key_press\n' + str(e))

            #t2=perf_counter()
            #t3=perf_counter()

            self.main_bind_class('Treeview','<KeyPress>', self.key_press )
            #t4=perf_counter()

            #print(f'key_pres {t1-t0},{t2-t1},{t3-t2},{t4-t3},---,{t4-t0}')

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

        if self.actions_processing:
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

    def set_full_path_to_file_win(self):
        self.sel_full_path_to_file=str(Path(sep.join([self.sel_path_full,self.sel_file]))) if self.sel_path_full and self.sel_file else None

    def set_full_path_to_file_lin(self):
        self.sel_full_path_to_file=(self.sel_path_full+self.sel_file if self.sel_path_full=='/' else sep.join([self.sel_path_full,self.sel_file])) if self.sel_path_full and self.sel_file else None

    set_full_path_to_file = set_full_path_to_file_win if windows else set_full_path_to_file_lin

    def sel_path_set(self,path):
        if self.sel_path_full != path:
            self.sel_path_full = path
            #print('self.sel_path_full')
            self.status_path_configure(text=self.sel_path_full)

            self.dominant_groups_folder={0:-1,1:-1}

    @catched
    def groups_tree_sel_change(self,item,force=False,change_status_line=True):
        #t0=perf_counter()
        gc_disable()

        self.sel_item = item

        if change_status_line :
            self.status()

        kind,crc,file,path,pathnr_int = self.groups_tree_mirror[item]
        pathnr = str(pathnr_int) if pathnr_int!=None else None

        self.sel_file = file

        if self.sel_crc != crc:
            self.sel_crc = crc

            self.dominant_groups_index={0:-1,1:-1}

        if path!=self.sel_path or force or pathnr!=self.sel_pathnr:
            if self.find_tree_index==1:
                self.find_result=()

            if pathnr: #non crc node
                self.sel_pathnr,self.sel_path = pathnr,path
                self.sel_path_set(dude_core.scanned_paths[pathnr_int]+path)
            else :
                self.sel_pathnr,self.sel_path = None,None
                self.sel_path_set(None)
            self.set_full_path_to_file()

        self.sel_kind = kind

        #t1a=perf_counter()

        if kind==self.FILE:
            self.tree_folder_update()
        else:
            self.tree_folder_update_none()

        #gc_collect()

        gc_enable()
        #t1=perf_counter()
        #print(f'groups_tree_sel_change\t{t1a-t0}\t{t1-t1a}')

    @catched
    def folder_tree_sel_change(self,item,change_status_line=True):
        self.sel_item = item

        self_folder_tree_set_item = self.folder_tree_set_item

        self.sel_file,self.sel_crc,self.sel_kind = self_folder_tree_set_item(item,'file'),self_folder_tree_set_item(item,'crc'),self_folder_tree_set_item(item,'kind')
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

            self.groups_tree_update_none()

    def menubar_unpost(self):
        try:
            self.menubar.unpost()
        except Exception as e:
            l_error(e)

    def context_menu_show(self,event):
        tree=event.widget

        if tree.identify("region", event.x, event.y) == 'heading':
            return

        if not self.actions_processing:
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

        duplicate_file_actions_state=('disabled',item_actions_state)[self.sel_kind==self.FILE]
        file_actions_state=('disabled',item_actions_state)[self.sel_kind in (self.FILE,self.SINGLE,self.SINGLEHARDLINKED) ]
        file_or_dir_actions_state=('disabled',item_actions_state)[self.sel_kind in (self.FILE,self.SINGLE,self.SINGLEHARDLINKED,self.DIR,self.DIRLINK,self.UPDIR,self.CRC) ]

        parent_dir_state = ('disabled','normal')[self.two_dots_condition(self.sel_path_full) and self.sel_kind!=self.CRC]

        if tree==self.groups_tree:
            c_local = Menu(pop,tearoff=0,bg=self.bg_color)
            c_local_add_command = c_local.add_command
            c_local_add_separator = c_local.add_separator
            c_local_add_cascade = c_local.add_cascade
            c_local_entryconfig = c_local.entryconfig

            c_local_add_command(label = "Toggle Mark",  command = lambda : self.tag_toggle_selected(tree,self.sel_item),accelerator="space", image = self.ico['empty'],compound='left')
            c_local_add_separator()
            c_local_add_command(label = "Mark all files",        command = lambda : self.mark_in_group(self.set_mark),accelerator="A", image = self.ico['empty'],compound='left')
            c_local_add_command(label = "Unmark all files",        command = lambda : self.mark_in_group(self.unset_mark),accelerator="N", image = self.ico['empty'],compound='left')
            c_local_add_separator()
            c_local_add_command(label = 'Mark By expression ...',command = lambda : self.mark_expression(self.set_mark,'Mark files',False),accelerator="+", image = self.ico['empty'],compound='left')
            c_local_add_command(label = 'Unmark By expression ...',command = lambda : self.mark_expression(self.unset_mark,'Unmark files',False),accelerator="-", image = self.ico['empty'],compound='left')
            c_local_add_separator()
            c_local_add_command(label = "Toggle mark on oldest file",     command = lambda : self.mark_in_group_by_ctime('oldest',self.invert_mark),accelerator="O", image = self.ico['empty'],compound='left')
            c_local_add_command(label = "Toggle mark on youngest file",   command = lambda : self.mark_in_group_by_ctime('youngest',self.invert_mark),accelerator="Y", image = self.ico['empty'],compound='left')
            c_local_add_separator()
            c_local_add_command(label = "Invert marks",   command = lambda : self.mark_in_group(self.invert_mark),accelerator="I", image = self.ico['empty'],compound='left')
            c_local_add_separator()

            mark_cascade_path = Menu(c_local, tearoff = 0,bg=self.bg_color)
            unmark_cascade_path = Menu(c_local, tearoff = 0,bg=self.bg_color)

            row=0
            for path in dude_core.scanned_paths:
                mark_cascade_path.add_command(image=self.icon_nr[row], label = path, compound = 'left',command  = lambda pathpar=path: self.action_on_path(pathpar,self.set_mark,False),accelerator=str(row+1)  )
                unmark_cascade_path.add_command(image=self.icon_nr[row], label = path, compound = 'left', command  = lambda pathpar=path: self.action_on_path(pathpar,self.unset_mark,False),accelerator="Shift+"+str(row+1)  )
                row+=1

            c_local_add_command(label = "Mark on specified directory ...",   command = lambda : self.mark_subpath(self.set_mark,False), image = self.ico['empty'],compound='left')
            c_local_add_command(label = "Unmark on specified directory ...",   command = lambda : self.mark_subpath(self.unset_mark,False), image = self.ico['empty'],compound='left')
            c_local_add_separator()

            c_local_add_cascade(label = "Mark on scan path",             menu = mark_cascade_path, image = self.ico['empty'],compound='left')
            c_local_add_cascade(label = "Unmark on scan path",             menu = unmark_cascade_path, image = self.ico['empty'],compound='left')
            c_local_add_separator()

            #marks_state=('disabled','normal')[len(tree.tag_has(self.MARK))!=0]
            marks_state=('disabled','normal')[bool(self.tagged)]

            c_local_add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(DELETE,0),accelerator="Delete",state=marks_state, image = self.ico['empty'],compound='left')
            c_local_entryconfig(19,foreground='red',activeforeground='red')
            c_local_add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(SOFTLINK,0),accelerator="Insert",state=marks_state, image = self.ico['empty'],compound='left')
            c_local_entryconfig(20,foreground='red',activeforeground='red')
            c_local_add_command(label = 'Hardlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(HARDLINK,0),accelerator="Shift+Insert",state=marks_state, image = self.ico['empty'],compound='left')
            c_local_entryconfig(21,foreground='red',activeforeground='red')

            pop_add_cascade(label = 'Local (this CRC group)',menu = c_local,state=item_actions_state, image = self.ico['empty'],compound='left')
            pop_add_separator()

            c_all = Menu(pop,tearoff=0,bg=self.bg_color)

            c_all.add_command(label = "Mark all files",        command = lambda : self.mark_on_all(self.set_mark),accelerator="Ctrl+A", image = self.ico['empty'],compound='left')
            c_all.add_command(label = "Unmark all files",        command = lambda : self.mark_on_all(self.unset_mark),accelerator="Ctrl+N", image = self.ico['empty'],compound='left')
            c_all.add_separator()
            c_all.add_command(label = 'Mark By expression ...',command = lambda : self.mark_expression(self.set_mark,'Mark files',True),accelerator="Ctrl+", image = self.ico['empty'],compound='left')
            c_all.add_command(label = 'Unmark By expression ...',command = lambda : self.mark_expression(self.unset_mark,'Unmark files',True),accelerator="Ctrl-", image = self.ico['empty'],compound='left')
            c_all.add_separator()
            c_all.add_command(label = "Mark Oldest files",     command = lambda : self.mark_all_by_ctime('oldest',self.set_mark),accelerator="Ctrl+O", image = self.ico['empty'],compound='left')
            c_all.add_command(label = "Unmark Oldest files",     command = lambda : self.mark_all_by_ctime('oldest',self.unset_mark),accelerator="Ctrl+Shift+O", image = self.ico['empty'],compound='left')
            c_all.add_separator()
            c_all.add_command(label = "Mark Youngest files",   command = lambda : self.mark_all_by_ctime('youngest',self.set_mark),accelerator="Ctrl+Y", image = self.ico['empty'],compound='left')
            c_all.add_command(label = "Unmark Youngest files",   command = lambda : self.mark_all_by_ctime('youngest',self.unset_mark),accelerator="Ctrl+Shift+Y", image = self.ico['empty'],compound='left')
            c_all.add_separator()
            c_all.add_command(label = "Invert marks",   command = lambda : self.mark_on_all(self.invert_mark),accelerator="Ctrl+I, *", image = self.ico['empty'],compound='left')
            c_all.add_separator()

            mark_cascade_path = Menu(c_all, tearoff = 0,bg=self.bg_color)
            unmark_cascade_path = Menu(c_all, tearoff = 0,bg=self.bg_color)

            row=0
            for path in dude_core.scanned_paths:
                mark_cascade_path.add_command(image=self.icon_nr[row], label = path, compound = 'left', command  = lambda pathpar=path: self.action_on_path(pathpar,self.set_mark,True) ,accelerator="Ctrl+"+str(row+1) )
                unmark_cascade_path.add_command(image=self.icon_nr[row], label = path, compound = 'left',  command  = lambda pathpar=path: self.action_on_path(pathpar,self.unset_mark,True) ,accelerator="Ctrl+Shift+"+str(row+1))
                row+=1

            c_all.add_command(label = "Mark on specified directory ...",   command = lambda : self.mark_subpath(self.set_mark,True), image = self.ico['empty'],compound='left')
            c_all.add_command(label = "Unmark on specified directory ...",   command = lambda : self.mark_subpath(self.unset_mark,True), image = self.ico['empty'],compound='left')
            c_all.add_separator()

            c_all.add_cascade(label = "Mark on scan path",             menu = mark_cascade_path, image = self.ico['empty'],compound='left')
            c_all.add_cascade(label = "Unmark on scan path",             menu = unmark_cascade_path, image = self.ico['empty'],compound='left')
            c_all.add_separator()

            c_all.add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(DELETE,1),accelerator="Ctrl+Delete",state=marks_state, image = self.ico['empty'],compound='left')
            c_all.entryconfig(21,foreground='red',activeforeground='red')
            c_all.add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(SOFTLINK,1),accelerator="Ctrl+Insert",state=marks_state, image = self.ico['empty'],compound='left')
            c_all.entryconfig(22,foreground='red',activeforeground='red')
            c_all.add_command(label = 'Hardlink Marked Files ...',command=lambda : self.process_files_in_groups_wrapper(HARDLINK,1),accelerator="Ctrl+Shift+Insert",state=marks_state, image = self.ico['empty'],compound='left')
            c_all.entryconfig(23,foreground='red',activeforeground='red')

            pop_add_cascade(label = 'All Files',menu = c_all,state=item_actions_state, image = self.ico['empty'],compound='left')

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
            c_nav_add_command(label = 'Go to parent directory'   ,command = self.go_to_parent_dir, accelerator="Backspace",state=parent_dir_state, image = self.ico['empty'],compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to next crc group'       ,command = lambda : self.goto_next_prev_crc(1),accelerator="Pg Down",state='normal', image = self.ico['empty'],compound='left')
            c_nav_add_command(label = 'Go to previous crc group'   ,command = lambda : self.goto_next_prev_crc(-1), accelerator="Pg Up",state='normal', image = self.ico['empty'],compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to first crc group'       ,command = lambda : self.goto_first_last_crc(0),accelerator="Home",state='normal', image = self.ico['empty'],compound='left')
            c_nav_add_command(label = 'Go to last crc group'   ,command = lambda : self.goto_first_last_crc(-1), accelerator="End",state='normal', image = self.ico['empty'],compound='left')

        else:
            dir_actions_state=('disabled','normal')[self.sel_kind in (self.DIR,self.DIRLINK)]

            c_local = Menu(pop,tearoff=0,bg=self.bg_color)
            c_local_add_command = c_local.add_command
            c_local_add_separator = c_local.add_separator
            c_local_entryconfig = c_local.entryconfig

            c_local_add_command(label = "Toggle Mark",  command = lambda : self.tag_toggle_selected(tree,self.sel_item),accelerator="space",state=duplicate_file_actions_state, image = self.ico['empty'],compound='left')
            c_local_add_separator()
            c_local_add_command(label = "Mark all files",        command = lambda : self.mark_in_folder(self.set_mark),accelerator="A",state=duplicate_file_actions_state, image = self.ico['empty'],compound='left')
            c_local_add_command(label = "Unmark all files",        command = lambda : self.mark_in_folder(self.unset_mark),accelerator="N",state=duplicate_file_actions_state, image = self.ico['empty'],compound='left')
            c_local_add_separator()
            c_local_add_command(label = 'Mark By expression',command = lambda : self.mark_expression(self.set_mark,'Mark files'),accelerator="+", image = self.ico['empty'],compound='left')
            c_local_add_command(label = 'Unmark By expression',command = lambda : self.mark_expression(self.unset_mark,'Unmark files'),accelerator="-", image = self.ico['empty'],compound='left')
            c_local_add_separator()

            #marks_state=('disabled','normal')[len(tree.tag_has(self.MARK))!=0]
            marks_state=('disabled','normal')[bool(self.current_folder_items_tagged)]

            c_local_add_command(label = 'Remove Marked Files ...',command=lambda : self.process_files_in_folder_wrapper(DELETE,0),accelerator="Delete",state=marks_state, image = self.ico['empty'],compound='left')
            c_local_add_command(label = 'Softlink Marked Files ...',command=lambda : self.process_files_in_folder_wrapper(SOFTLINK,0),accelerator="Insert",state=marks_state, image = self.ico['empty'],compound='left')

            c_local_entryconfig(8,foreground='red',activeforeground='red')
            c_local_entryconfig(9,foreground='red',activeforeground='red')
            #c_local_entryconfig(10,foreground='red',activeforeground='red')

            pop_add_cascade(label = 'Local (this folder)',menu = c_local,state=item_actions_state, image = self.ico['empty'],compound='left')
            pop_add_separator()

            c_sel_sub = Menu(pop,tearoff=0,bg=self.bg_color)
            c_sel_sub_add_command = c_sel_sub.add_command
            c_sel_sub_add_command(label = "Mark All Duplicates in Subdirectory",  command = lambda : self.sel_dir(self.set_mark),accelerator="D",state=dir_actions_state, image = self.ico['empty'],compound='left')
            c_sel_sub_add_command(label = "Unmark All Duplicates in Subdirectory",  command = lambda : self.sel_dir(self.unset_mark),accelerator="Shift+D",state=dir_actions_state, image = self.ico['empty'],compound='left')
            c_sel_sub.add_separator()

            c_sel_sub_add_command(label = 'Remove Marked Files in Subdirectory Tree ...',command=lambda : self.process_files_in_folder_wrapper(DELETE,True),accelerator="Delete",state=dir_actions_state, image = self.ico['empty'],compound='left')
            c_sel_sub_add_command(label = 'Softlink Marked Files in Subdirectory Tree ...',command=lambda : self.process_files_in_folder_wrapper(SOFTLINK,True),accelerator="Insert",state=dir_actions_state, image = self.ico['empty'],compound='left')

            c_sel_sub.entryconfig(3,foreground='red',activeforeground='red')
            c_sel_sub.entryconfig(4,foreground='red',activeforeground='red')

            pop_add_cascade(label = 'Selected Subdirectory',menu = c_sel_sub,state=dir_actions_state, image = self.ico['empty'],compound='left')

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
            c_nav_add_command(label = 'Go to parent directory'       ,command = self.go_to_parent_dir, accelerator="Backspace",state=parent_dir_state, image = self.ico['empty'],compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to next duplicate'       ,command = lambda : self.goto_next_prev_duplicate_in_folder(1),accelerator="Pg Down",state='normal', image = self.ico['empty'],compound='left')
            c_nav_add_command(label = 'Go to previous duplicate'   ,command = lambda : self.goto_next_prev_duplicate_in_folder(-1), accelerator="Pg Up",state='normal', image = self.ico['empty'],compound='left')
            c_nav_add_separator()
            c_nav_add_command(label = 'Go to first entry'       ,command = lambda : self.goto_first_last_dir_entry(0),accelerator="Home",state='normal', image = self.ico['empty'],compound='left')
            c_nav_add_command(label = 'Go to last entry'   ,command = lambda : self.goto_first_last_dir_entry(-1), accelerator="End",state='normal', image = self.ico['empty'],compound='left')

        pop_add_separator()
        pop_add_cascade(label = 'Navigation',menu = c_nav,state=item_actions_state, image = self.ico['empty'],compound='left')

        pop_add_separator()
        pop_add_command(label = 'Open File',command = self.open_file,accelerator="Return",state=file_actions_state, image = self.ico['empty'],compound='left')
        pop_add_command(label = 'Open Folder(s)',command = self.open_folder,accelerator="Alt+Return",state=file_or_dir_actions_state, image = self.ico['empty'],compound='left')

        pop_add_separator()
        pop_add_command(label = 'Scan ...',  command = self.scan_dialog_show,accelerator='S',image = self.ico['scan'],compound='left')
        pop_add_command(label = 'Settings ...',  command = lambda : self.get_settings_dialog().show(),accelerator='F2',image = self.ico['settings'],compound='left')
        pop_add_separator()
        pop_add_command(label = 'Copy full path',command = self.clip_copy_full_path_with_file,accelerator='Ctrl+C',state = 'normal' if (self.sel_kind and self.sel_kind!=self.CRC) else 'disabled', image = self.ico['empty'],compound='left')
        #pop_add_command(label = 'Copy only path',command = self.clip_copy_full,accelerator="C",state = 'normal' if self.sel_item!=None else 'disabled')
        pop_add_separator()
        pop_add_command(label = 'Find ...',command = self.finder_wrapper_show,accelerator="F",state = 'normal' if self.sel_item is not None else 'disabled', image = self.ico['empty'],compound='left')
        pop_add_command(label = 'Find next',command = self.find_next,accelerator="F3",state = 'normal' if self.sel_item is not None else 'disabled', image = self.ico['empty'],compound='left')
        pop_add_command(label = 'Find prev',command = self.find_prev,accelerator="Shift+F3",state = 'normal' if self.sel_item is not None else 'disabled', image = self.ico['empty'],compound='left')
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
    @block_actions_processing
    @gui_block
    @logwrapper
    def column_sort(self, tree):
        self.status('Sorting...')
        colname,sort_index,is_numeric,reverse,updir_code,dir_code,non_dir_code = self.column_sort_last_params[tree]

        self.column_sort_set_arrow(tree)

        self_tree_sort_item = self.tree_sort_item

        if tree==self.groups_tree:
            if colname in ('path','file','ctime_h'):
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
        if len(self.paths_to_scan_from_dialog)<10:
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

    def scan_update_info_path_nr(self,info_path_nr):
        self.update_scan_path_nr=True

    prev_status_progress_text=''
    def status_progress(self,text='',image='',do_log=False):
        if text != self.prev_status_progress_text:
            self.progress_dialog_on_scan.lab[1].configure(text=text)
            self.progress_dialog_on_scan.area_main.update()
            self.prev_status_progress_text=text

    @restore_status_line
    @logwrapper
    def scan(self):
        self.status('Scanning...')
        self.cfg.write()

        dude_core.reset()
        self.status_path_configure(text='')
        self.groups_show()

        paths_to_scan_from_entry = [var.get() for var in self.paths_to_scan_entry_var.values()]
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
        self.log_skipped = self.log_skipped_var.get()

        scan_thread=Thread(target=dude_core.scan,daemon=True)
        scan_thread.start()

        self_progress_dialog_on_scan.lab_l1.configure(text='Total space:')
        self_progress_dialog_on_scan.lab_l2.configure(text='Files number:' )

        self_progress_dialog_on_scan_progr1var.set(0)
        self_progress_dialog_on_scan_progr2var.set(0)

        self_progress_dialog_on_scan.show('Scanning')
        #,image=self.ico['empty'],image_text=' '

        update_once=True

        prev_data={}
        new_data={}
        prev_path_nr=-1
        for i in range(1,5):
            prev_data[i]=''
            new_data[i]=''

        time_without_busy_sign=0

        hr_index=0

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

        self_hg_ico = self.hg_ico
        len_self_hg_ico = len(self_hg_ico)

        local_bytes_to_str = bytes_to_str

        while scan_thread_is_alive():
            new_data[3]=local_bytes_to_str(dude_core.info_size_sum)
            new_data[4]='%s files' % fnumber(dude_core.info_counter)

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

                if update_once:
                    update_once=False
                    self_tooltip_message[str_self_progress_dialog_on_scan_abort_button]='If you abort at this stage,\nyou will not get any results.'
                    self_configure_tooltip(str_self_progress_dialog_on_scan_abort_button)

                    self_progress_dialog_on_scan_lab[2].configure(image=self.ico['empty'])
            else :
                if now>time_without_busy_sign+1.0:
                    self_progress_dialog_on_scan_lab[2].configure(image=self_hg_ico[hr_index],text = '', compound='left')
                    hr_index=(hr_index+1) % len_self_hg_ico

                    self_tooltip_message[str_self_progress_dialog_on_scan_abort_button]='currently scanning:\n%s...' % dude_core.info_line
                    self_configure_tooltip(str_self_progress_dialog_on_scan_abort_button)
                    update_once=True

            self_progress_dialog_on_scan_area_main_update()

            if self.action_abort:
                dude_core.abort()
                break

            self.main.after(100,lambda : wait_var.set(not wait_var.get()))
            self.main.wait_variable(wait_var)

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

        self_status('Calculating CRC ...')
        self_progress_dialog_on_scan.widget.title('CRC calculation')

        self_tooltip_message[str_self_progress_dialog_on_scan_abort_button]='If you abort at this stage,\npartial results may be available\n(if any CRC groups are found).'
        self_progress_dialog_on_scan.abort_button.configure(image=self.ico['abort'],text='Abort',compound='left')

        self_status('Starting CRC threads ...')
        crc_thread=Thread(target=dude_core.crc_calc,daemon=True)
        crc_thread.start()

        update_once=True
        self_progress_dialog_on_scan_lab[0].configure(image='',text='')
        self_progress_dialog_on_scan_lab[1].configure(image='',text='')
        self_progress_dialog_on_scan_lab[2].configure(image='',text='')
        self_progress_dialog_on_scan_lab[3].configure(image='',text='')
        self_progress_dialog_on_scan_lab[4].configure(image='',text='')

        prev_progress_size=0
        prev_progress_quant=0

        crc_thread_is_alive = crc_thread.is_alive
        self_progress_dialog_on_scan_progr1var_set = self_progress_dialog_on_scan_progr1var.set
        self_progress_dialog_on_scan_progr2var_set = self_progress_dialog_on_scan_progr2var.set

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
                    new_data[2]='CRC groups: %s' % fnumber(dude_core.info_found_groups)
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
                    self_tooltip_message[str_self_progress_dialog_on_scan_abort_button]='If you abort at this stage,\npartial results may be available\n(if any CRC groups are found).'
                    self_configure_tooltip(str_self_progress_dialog_on_scan_abort_button)

                    self_progress_dialog_on_scan_lab[0].configure(image=self.ico['empty'])
            else :
                if now>time_without_busy_sign+1.0:
                    self_progress_dialog_on_scan_lab[0].configure(image=self_hg_ico[hr_index],text='')
                    hr_index=(hr_index+1) % len_self_hg_ico

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
        #self_progress_dialog_on_scan.label.update()

        self.groups_show()

        self_progress_dialog_on_scan.widget.config(cursor="")
        self_progress_dialog_on_scan.hide(True)
        self.status=self.status_main_win if windows else self.status_main

        if self.action_abort:
            self.get_info_dialog_on_scan().show('CRC Calculation aborted.','\nResults are partial.\nSome files may remain unidentified as duplicates.')

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
            (frame:=Frame(self.paths_frame,bg=self.bg_color)).grid(row=row,column=0,sticky='news',columnspan=3)
            self.paths_to_scan_frames.append(frame)

            Label(frame,image=self.icon_nr[row], relief='flat',bg=self.bg_color).pack(side='left',padx=2,pady=2,fill='y')

            self.paths_to_scan_entry_var[row]=StringVar(value=path)
            path_to_scan_entry = Entry(frame,textvariable=self.paths_to_scan_entry_var[row])
            path_to_scan_entry.pack(side='left',expand=1,fill='both',pady=1)

            path_to_scan_entry.bind("<KeyPress-Return>", lambda event : self.scan_wrapper())

            remove_path_button=Button(frame,image=self.ico['delete'],command=lambda pathpar=path: self.path_to_scan_remove(pathpar),width=3)
            remove_path_button.pack(side='right',padx=2,pady=1,fill='y')

            remove_path_button.bind("<Motion>", lambda event : self.motion_on_widget(event,'Remove path from list.'))
            remove_path_button.bind("<Leave>", lambda event : self.widget_leave())

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

        for entry in self.cfg.get(CFG_KEY_EXCLUDE,'').split('|'):
            if entry:
                (frame:=Frame(self.exclude_frame,bg=self.bg_color)).grid(row=row,column=0,sticky='news',columnspan=3)
                self.exclude_frames.append(frame)

                self.exclude_entry_var[row]=StringVar(value=entry)
                Entry(frame,textvariable=self.exclude_entry_var[row]).pack(side='left',expand=1,fill='both',pady=1,padx=(2,0))

                remove_expression_button=Button(frame,image=self.ico['delete'],command=lambda entrypar=entry: self.exclude_mask_remove(entrypar),width=3)
                remove_expression_button.pack(side='right',padx=2,pady=1,fill='y')

                remove_expression_button.bind("<Motion>", lambda event : self.motion_on_widget(event,'Remove expression from list.'))
                remove_expression_button.bind("<Leave>", lambda event : self.widget_leave())

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

    def settings_ok(self):
        update0=False
        update1=False
        update2=False

        if self.cfg_get_bool(CFG_KEY_FULL_CRC)!=self.show_full_crc.get():
            self.cfg.set_bool(CFG_KEY_FULL_CRC,self.show_full_crc.get())
            update1=True
            update2=True

        if self.cfg_get_bool(CFG_KEY_FULL_PATHS)!=self.show_full_paths.get():
            self.cfg.set_bool(CFG_KEY_FULL_PATHS,self.show_full_paths.get())
            update1=True
            update2=True

        if self.cfg_get_bool(CFG_KEY_CROSS_MODE)!=self.cross_mode.get():
            self.cfg.set_bool(CFG_KEY_CROSS_MODE,self.cross_mode.get())
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

        if self.cfg.get(CFG_KEY_WRAPPER_FILE)!=self.file_open_wrapper.get():
            self.cfg.set(CFG_KEY_WRAPPER_FILE,self.file_open_wrapper.get())

        if self.cfg.get(CFG_KEY_WRAPPER_FOLDERS)!=self.folders_open_wrapper.get():
            self.cfg.set(CFG_KEY_WRAPPER_FOLDERS,self.folders_open_wrapper.get())

        if self.cfg.get(CFG_KEY_WRAPPER_FOLDERS_PARAMS)!=self.folders_open_wrapper_params.get():
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

    @catched
    def crc_node_update(self,crc):
        self_groups_tree = self.groups_tree
        self_groups_tree_delete = self_groups_tree.delete
        self_get_index_tuple_groups_tree = self.get_index_tuple_groups_tree

        size=int(self_groups_tree.set(crc,'size'))

        if size not in dude_core.files_of_size_of_crc:
            self_groups_tree_delete(crc)
            #l_debug('crc_node_update-1 %s',crc)
        elif crc not in dude_core.files_of_size_of_crc[size]:
            self_groups_tree_delete(crc)
            #l_debug('crc_node_update-2 %s',crc)
        else:
            crc_dict=dude_core.files_of_size_of_crc[size][crc]
            for item in self.tree_children_sub[crc]:
                index_tuple=self_get_index_tuple_groups_tree(item)

                if index_tuple not in crc_dict:
                    self_groups_tree_delete(item)
                    #l_debug('crc_node_update-3:%s',item)

            if not self.tree_children_sub[crc]:
                self_groups_tree_delete(crc)
                #l_debug('crc_node_update-4:%s',crc)

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

    @catched
    @logwrapper
    def data_precalc(self):
        self.status('Precalculating data...')

        self.create_my_prev_next_dicts(self.groups_tree)
        self_tree_children = self.tree_children

        self.status_groups_configure(text=fnumber(len(self_tree_children[self.groups_tree])),image=self.ico['warning' if self.cfg_get_bool(CFG_KEY_CROSS_MODE) else 'empty'],compound='right',width=80,anchor='w')

        path_stat_size={}
        path_stat_size_get=path_stat_size.get

        path_stat_quant={}
        path_stat_quant_get=path_stat_quant.get

        self.id2crc = {}
        self_id2crc = self.id2crc

        self.biggest_file_of_path.clear()
        self.biggest_file_of_path_id.clear()
        self_biggest_file_of_path = self.biggest_file_of_path
        self_biggest_file_of_path_get = self_biggest_file_of_path.get
        self_biggest_file_of_path_id = self.biggest_file_of_path_id

        self_idfunc=self.idfunc

        self_active_crcs = self.active_crcs

        for size,size_dict in dude_core.files_of_size_of_crc_items():
            for crc,crc_dict in size_dict.items():
                if crc in self_active_crcs:
                    for pathnr,path,file,ctime,dev,inode in crc_dict:
                        item_id = self_idfunc(inode,dev)
                        self_id2crc[item_id]=(crc,ctime)
                        path_index=(pathnr,path)
                        path_stat_size[path_index] = path_stat_size_get(path_index,0) + size
                        path_stat_quant[path_index] = path_stat_quant_get(path_index,0) + 1

                        if size>self_biggest_file_of_path_get(path_index,0):
                            self_biggest_file_of_path[path_index]=size
                            self_biggest_file_of_path_id[path_index]=item_id

        self_groups_tree_set = self.groups_tree_set
        self_tree_children_sub = self.tree_children_sub

        self_tree_children_self_groups_tree = self_tree_children[self.groups_tree]

        self.path_stat_list_size=tuple(sorted([(pathnr,path,number) for (pathnr,path),number in path_stat_size.items()],key=lambda x : x[2],reverse=True))
        self.path_stat_list_quant=tuple(sorted([(pathnr,path,number) for (pathnr,path),number in path_stat_quant.items()],key=lambda x : x[2],reverse=True))
        self.groups_combos_size = tuple(sorted([(crc_item,sum([int(self_groups_tree_set(item,'size')) for item in self_tree_children_sub[crc_item]])) for crc_item in self_tree_children_self_groups_tree],key = lambda x : x[1],reverse = True))
        self.groups_combos_quant = tuple(sorted([(crc_item,len(self_tree_children_sub[crc_item])) for crc_item in self_tree_children_self_groups_tree],key = lambda x : x[1],reverse = True))
        self.status('')

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

    @block_actions_processing
    @gui_block
    @logwrapper
    def groups_show(self):
        self.menu_disable()

        self_idfunc=self.idfunc = (lambda i,d : '%s-%s' % (i,d)) if len(dude_core.devs)>1 else (lambda i,d : str(i))
        self_status=self.status

        self_status('Cleaning tree...')
        self.reset_sels()
        self_groups_tree = self.groups_tree

        self_groups_tree.delete(*self.tree_children[self_groups_tree])

        self.selected[self.groups_tree]=None

        cross_mode = self.cfg_get_bool(CFG_KEY_CROSS_MODE)
        show_full_crc=self.cfg_get_bool(CFG_KEY_FULL_CRC)
        show_full_paths=self.cfg_get_bool(CFG_KEY_FULL_PATHS)

        self_status('Rendering data...')

        self.tagged.clear()

        sizes_counter=0
        self.iid_to_size.clear()

        self_groups_tree_insert=self_groups_tree.insert

        dude_core_crc_cut_len=dude_core.crc_cut_len

        self_iid_to_size=self.iid_to_size

        self_CRC = self.CRC
        self_FILE = self.FILE

        local_bytes_to_str = bytes_to_str
        self_icon_nr=self.icon_nr

        groups_tree_mirror = self.groups_tree_mirror = {}

        for size,size_dict in dude_core.files_of_size_of_crc_items() :
            size_h = local_bytes_to_str(size)
            size_str = str(size)
            if not sizes_counter%128:
                self_status('Rendering data... (%s)' % size_h,do_log=False)

            sizes_counter+=1
            for crc,crc_dict in size_dict.items():
                if cross_mode:
                    is_cross_group = bool(len({pathnr for pathnr,path,file,ctime,dev,inode in crc_dict})>1)
                    if not is_cross_group:
                        continue

                #self_groups_tree["columns"]=('pathnr','path','file','size','size_h','ctime','dev','inode','crc','instances','instances_h','ctime_h','kind')
                instances_str=str(len(crc_dict))
                crc_item=self_groups_tree_insert('','end',crc, values=('','','',size_str,size_h,'','','',crc,instances_str,instances_str,'',self_CRC),tags=self_CRC,open=True,text= crc if show_full_crc else crc[:dude_core_crc_cut_len])

                #kind,crc,file,path,pathnr
                groups_tree_mirror[crc_item]=(self_CRC,crc,None,None,None)

                for pathnr,path,file,ctime,dev,inode in sorted(crc_dict,key = lambda x : x[0]):
                    iid=self_idfunc(inode,dev)
                    self_iid_to_size[iid]=size

                    file_item = self_groups_tree_insert(crc_item,'end',iid, values=(\
                            str(pathnr),path,file,size_str,\
                            '',\
                            str(ctime),str(dev),str(inode),crc,\
                            '','',\
                            strftime('%Y/%m/%d %H:%M:%S',localtime(ctime//1000000000)),self_FILE),tags='',text=dude_core_scanned_paths[pathnr] if show_full_paths else '',image=self_icon_nr[pathnr]) #DE_NANO= 1_000_000_000

                    #kind,crc,file,path,pathnr
                    groups_tree_mirror[file_item]=(self_FILE,crc,file,path,pathnr)

        self.active_crcs={crc for size_dict in dude_core.files_of_size_of_crc.values() for crc in size_dict }

        self.data_precalc()

        if self.column_sort_last_params[self_groups_tree]!=self.column_groups_sort_params_default:
            #defaultowo po size juz jest, nie trzeba tracic czasu
            self.column_sort(self_groups_tree)
        else:
            self.column_sort_set_arrow(self_groups_tree)
            #self.create_my_prev_next_dicts(self_groups_tree)

        self.initial_focus()
        self.calc_mark_stats_groups()

        self.menu_enable()
        self_status('')

    @block_actions_processing
    @gui_block
    @logwrapper
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
        self_active_crcs=self.active_crcs
        for size,size_dict in dude_core.files_of_size_of_crc_items() :
            for crc,crc_dict in size_dict.items():
                if crc in self_active_crcs:
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

    @block_actions_processing
    def tree_folder_update(self,arbitrary_path=None):
        #t0=perf_counter()

        ftree = self.folder_tree
        self.folder_tree_configure(takefocus=False)

        current_path=arbitrary_path if arbitrary_path else self.sel_path_full

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
        local_localtime = localtime
        folder_items=set()
        folder_items_add=folder_items.add

        if self.two_dots_condition(current_path):
            values=('..','','',self.UPDIR,'',0,'',0,'',0,'')
            folder_items_add((updir_code,sort_val_func(values[sort_index_local]),'0UP','',values,self_DIR,''))

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

                                ctime_h = local_strftime('%Y/%m/%d %H:%M:%S',local_localtime(ctime//1000000000)) #DE_NANO

                                size_h=local_bytes_to_str(size_num)

                                item_rocognized=True
                                if file_id in self_id2crc:
                                    crc,core_ctime=self_id2crc[file_id]

                                    if ctime != core_ctime:
                                        item_rocognized=False
                                    else:
                                        values = (name,str(dev),str(inode),self_FILE,crc,str(size_num),size_h,str(ctime),ctime_h,instances_both := str(len(dude_core_files_of_size_of_crc[size_num][crc])),instances_both)
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

        #t1=perf_counter()
        try:
            self.current_folder_items=tuple( (ftree_insert('','end',iid, text=text, values=values,tags=tag,image=image) for _,_,iid,text,values,tag,image in sorted(folder_items,reverse=reverse,key=lambda x : (x[0:3]) ) ))
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

        #t2=perf_counter()

        folder_items_len = len(self.current_folder_items)

        #fact1 = format((t1-t0)/folder_items_len, '.10f')
        #fact2 = format((t2-t1)/folder_items_len, '.10f')
        #print(f'tree_folder_update:{t1-t0}\t{fact1}\t{fact2}\titems:{folder_items_len}')

        self.folder_tree_configure(takefocus=True)

        self.create_my_prev_next_dicts(ftree)

        return True

    def update_marks_folder(self):
        self_folder_tree_item=self.folder_tree.item
        self_folder_tree_set=self.folder_tree.set
        self_tagged = self.tagged
        self_FILE = self.FILE
        self_MARK = self.MARK
        self.current_folder_items_tagged_clear()
        self_current_folder_items_tagged_add=self.current_folder_items_tagged_add
        for item in self.current_folder_items:
            #cant unset other tags !
            if self_folder_tree_set(item,'kind')==self_FILE:
                in_tagged=bool(item in self_tagged)
                self_folder_tree_item( item,tags=self_MARK if in_tagged else'')
                if in_tagged:
                    self_current_folder_items_tagged_add(item)

    def calc_mark_stats_groups(self):
        self.status_all_quant_configure(text=fnumber(len(self.tagged)))
        self_iid_to_size=self.iid_to_size
        self.status_all_size_configure(text=bytes_to_str(sum([self_iid_to_size[iid] for iid in self.tagged])))

    def calc_mark_stats_folder(self):
        self.status_folder_quant_configure(text=fnumber(len(self.current_folder_items_tagged)))

        self_iid_to_size = self.iid_to_size
        self.status_folder_size_configure(text=bytes_to_str(sum(self_iid_to_size[iid] for iid in self.current_folder_items_tagged)))

    def mark_in_specified_group_by_ctime(self, action, crc, reverse,select=False):
        self_groups_tree = self.groups_tree
        self_groups_tree_set = self_groups_tree.set
        item=sorted([ (item,self_groups_tree_set(item,'ctime') ) for item in self.tree_children_sub[crc]],key=lambda x : int(x[1]),reverse=reverse)[0][0]
        if item:
            action(item,self_groups_tree)
            if select:
                self_groups_tree.see(item)
                self_groups_tree.focus(item)
                self.groups_tree_sel_change(item)
                self_groups_tree.update()

    @block_actions_processing
    @gui_block
    def mark_all_by_ctime(self,order_str, action):
        self.status('Un/Setting marking on all files ...')
        reverse=1 if order_str=='oldest' else 0

        self_mark_in_specified_group_by_ctime = self.mark_in_specified_group_by_ctime
        _ = { self_mark_in_specified_group_by_ctime(action, crc, reverse) for crc in self.tree_children[self.groups_tree] }

        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @block_actions_processing
    @gui_block
    def mark_in_group_by_ctime(self,order_str,action):
        self.status('Un/Setting marking in group ...')
        reverse=1 if order_str=='oldest' else 0
        self.mark_in_specified_group_by_ctime(action,self.sel_crc,reverse,True)
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    def mark_in_specified_crc_group(self,action,crc):
        self_groups_tree = self.groups_tree
        _ = { action(item,self_groups_tree) for item in self.tree_children_sub[crc] }

    @block_actions_processing
    @gui_block
    def mark_in_group(self,action):
        self.status('Un/Setting marking in group ...')
        self.mark_in_specified_crc_group(action,self.sel_crc)
        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @block_actions_processing
    @gui_block
    def mark_on_all(self,action):
        self.status('Un/Setting marking on all files ...')
        self_mark_in_specified_crc_group = self.mark_in_specified_crc_group
        _ = { self_mark_in_specified_crc_group(action,crc) for crc in self.tree_children[self.groups_tree] }

        self.update_marks_folder()
        self.calc_mark_stats_groups()
        self.calc_mark_stats_folder()

    @block_actions_processing
    @gui_block
    def mark_in_folder(self,action):
        self.status('Un/Setting marking in folder ...')
        self_groups_tree = self.groups_tree
        self_folder_tree = self.folder_tree
        self_folder_tree_set = self_folder_tree.set
        self_FILE=self.FILE
        self_current_folder_items=self.current_folder_items
        _ = { (action(item,self_folder_tree),action(item,self_groups_tree)) for item in self_current_folder_items if self_folder_tree_set(item,'kind')==self_FILE }

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

    @block_actions_processing
    @gui_block
    @logwrapper
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

        if tree==self.groups_tree:
            self.get_mark_dialog_on_groups().show(title,prompt + f'{range_str}', initialvalue,'treat as a regular expression',self.cfg_get_bool(CFG_KEY_USE_REG_EXPR))
            use_reg_expr = self.mark_dialog_on_groups.res_check
            expression = self.mark_dialog_on_groups.res_str
        else:
            self.get_mark_dialog_on_folder().show(title,prompt + f'{range_str}', initialvalue,'treat as a regular expression',self.cfg_get_bool(CFG_KEY_USE_REG_EXPR))
            use_reg_expr = self.mark_dialog_on_folder.res_check
            expression = self.mark_dialog_on_folder.res_str

        items=[]
        items_append = items.append
        use_reg_expr_info = '(regular expression)' if use_reg_expr else ''

        if expression:
            self.cfg.set_bool(CFG_KEY_USE_REG_EXPR,use_reg_expr)
            self.expr_by_tree[tree]=expression

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
                self_folder_tree_set = self.folder_tree.set

                tree_set = tree.set

                for item in self.current_folder_items:
                    if tree_set(item,'kind')==self.FILE:
                        file=self_folder_tree_set(item,'file')
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

    @block_actions_processing
    @gui_block
    def goto_next_mark(self,tree,direction,go_to_no_mark=False):
        if go_to_no_mark:
            status= 'selecting next not marked item' if direction==1 else 'selecting prev not marked item'
        else:
            status ='selecting next marked item' if direction==1 else 'selecting prev marked item'

        current_item = self.sel_item
        self_sel_item = self.sel_item

        tree_set = tree.set
        tree_tag_has = tree.tag_has

        next_dict = self.my_next_dict[tree] if direction==1 else self.my_prev_dict[tree]

        self_MARK = self.MARK

        while current_item:
            #current_item = self_my_next[current_item] if direction==1 else self_my_prev[current_item]
            current_item = next_dict[current_item]
            #print(f'{self.tagged=}')

            #item_taggged = tree_tag_has(self_MARK,current_item)
            item_taggged = bool(current_item in self.tagged)

            if (item_taggged and not go_to_no_mark) or (go_to_no_mark and not item_taggged and tree_set(current_item,'kind')!=self.CRC):
                tree.focus(current_item)
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

    @block_actions_processing
    @gui_block
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

    @block_actions_processing
    @gui_block
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
        self_groups_tree_set = self.groups_tree_set

        pathnr=int(self_groups_tree_set(item,'pathnr'))
        path=self_groups_tree_set(item,'path')
        file=self_groups_tree_set(item,'file')
        return abspath(dude_core.get_full_path_scanned(pathnr,path,file))

    def file_check_state(self,item):
        fullpath = self.item_full_path(item)
        l_info('checking file: %s',fullpath)
        try:
            stat_res = stat(fullpath)
            ctime_check=str(stat_res.st_ctime_ns)
        except Exception as e:
            self.status(str(e))
            mesage = f'can\'t check file: {fullpath}\n\n{e}'
            l_error(mesage)
            return mesage

        if ctime_check != (ctime:=self.groups_tree_set(item,'ctime')) :
            message = {f'ctime inconsistency {ctime_check} vs {ctime}'}
            return message

        return None

    @block_actions_processing
    @logwrapper
    def process_files_in_groups_wrapper(self,action,all_groups):
        processed_items=defaultdict(list)
        if all_groups:
            scope_title='All marked files.'
        else:
            scope_title='Single CRC group.'

        self_sel_crc = self.sel_crc

        self_tree_children_sub = self.tree_children_sub

        for crc in self.tree_children[self.groups_tree]:
            if all_groups or crc==self_sel_crc:
                for item in self_tree_children_sub[crc]:
                    if item in self.tagged:
                        processed_items[crc].append(item)

        return self.process_files(action,processed_items,scope_title)

    @block_actions_processing
    @logwrapper
    def process_files_in_folder_wrapper(self,action,on_dir_action=False):
        processed_items=defaultdict(list)

        self_item_full_path = self.item_full_path

        self_tree_children_sub = self.tree_children_sub
        if on_dir_action:
            scope_title='All marked files on selected directory sub-tree.'

            sel_path_with_sep=self.sel_full_path_to_file.rstrip(sep) + sep
            for crc in self.tree_children[self.groups_tree]:
                for item in self_tree_children_sub[crc]:
                    if self_item_full_path(item).startswith(sel_path_with_sep):
                        if item in self.tagged:
                            processed_items[crc].append(item)
        else:
            scope_title='Selected Directory.'

            self_folder_tree_set = self.folder_tree.set
            self_current_folder_items_tagged = self.current_folder_items_tagged
            for item in self.current_folder_items:
                if item in self_current_folder_items_tagged:
                    crc=self_folder_tree_set(item,'crc')
                    processed_items[crc].append(item)

        return self.process_files(action,processed_items,scope_title)

    CHECK_OK='ok_special_string'
    CHECK_ERR='error_special_string'

    @restore_status_line
    @gui_block
    @logwrapper
    def process_files_check_correctness(self,action,processed_items,remaining_items):
        skip_incorrect = self.cfg_get_bool(CFG_SKIP_INCORRECT_GROUPS)
        show_full_crc=self.cfg_get_bool(CFG_KEY_FULL_CRC)

        crc_to_size = {crc:size for size,size_dict in dude_core.files_of_size_of_crc_items() for crc in size_dict}

        self.status('checking data consistency with filesystem state ...')

        dude_core_check_group_files_state = dude_core.check_group_files_state
        self_crc_node_update = self.crc_node_update

        for crc in processed_items:
            size = crc_to_size[crc]
            (checkres,tuples_to_remove)=dude_core_check_group_files_state(size,crc)

            if checkres:
                self.get_text_info_dialog().show('Error. Inconsistent data.','Current filesystem state is inconsistent with scanned data.\n\n' + '\n'.join(checkres) + '\n\nSelected CRC group will be reduced. For complete results re-scanning is recommended.')

                orglist=self.tree_children[self.groups_tree]

                dude_core.remove_from_data_pool(int(size),crc,tuples_to_remove)

                self_crc_node_update(crc)

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
            if action==SOFTLINK:
                problem_message = "Keep at least one file unmarked\nor enable option:\n\"Skip groups with invalid selection\""
            else:
                problem_message = "Keep at least one file unmarked\nor enable option:\n\"Skip groups with invalid selection\"\nor enable option:\n\"Allow deletion of all copies\""

        if incorrect_groups:
            if skip_incorrect:

                incorrect_group_str='\n'.join([crc if show_full_crc else crc[:dude_core.crc_cut_len] for crc in incorrect_groups ])
                header = f'Warning ({NAME[action]}). {problem_header}'
                message = f"Option \"Skip groups with invalid selection\" is enabled.\n\nFollowing CRC groups will NOT be processed and remain with markings:\n\n{incorrect_group_str}"

                self.get_text_info_dialog().show(header,message)

                self.crc_select_and_focus(incorrect_groups[0],True)

                for crc in incorrect_groups:
                    del processed_items[crc]
                    del remaining_items[crc]

            else:
                if action==DELETE and self.cfg_get_bool(CFG_ALLOW_DELETE_ALL):
                    self.get_text_ask_dialog().show('Warning !','Option: \'Allow to delete all copies\' is set.|RED\n\nAll copies may be selected.|RED\n\nProceed ?|RED')
                    if self.text_ask_dialog.res_bool:
                        return self.CHECK_OK
                else:
                    header = f'Error ({NAME[action]}). {problem_header}'
                    self.get_info_dialog_on_main().show(header,problem_message)

                self.crc_select_and_focus(incorrect_groups[0],True)
                return self.CHECK_ERR

        return self.CHECK_OK

    @restore_status_line
    @block_actions_processing
    @gui_block
    @logwrapper
    def process_files_check_correctness_last(self,action,processed_items,remaining_items):
        self.status('final checking selection correctness')
        self.main_update()

        self_groups_tree_set = self.groups_tree_set
        self_file_check_state = self.file_check_state

        if action==HARDLINK:
            for crc,items_list in processed_items.items():
                if len({self_groups_tree_set(item,'dev') for item in items_list})>1:
                    title='Can\'t create hardlinks.'
                    message=f"Files on multiple devices selected. Crc:{crc}"
                    l_error(title)
                    l_error(message)
                    self.get_info_dialog_on_main().show(title,message)
                    return self.CHECK_ERR
        for crc in processed_items:
            for item in remaining_items[crc]:
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

        self_groups_tree_set = self.groups_tree_set
        self_item_full_path = self.item_full_path

        size_sum=0
        for crc in processed_items:
            message_append('')
            size=int(self_groups_tree_set(crc,'size'))
            if cfg_show_crc_size:
                message_append('CRC:' + crc + ' size:' + bytes_to_str(size) + '|GRAY')

            for item in processed_items[crc]:
                size_sum += size
                message_append((self_item_full_path(item) if show_full_path else self_groups_tree_set(item,'file')) + '|RED' )

            if action==SOFTLINK:
                if remaining_items[crc]:
                    item = remaining_items[crc][0]
                    if cfg_show_links_targets:
                        message_append('-> %s' % (self_item_full_path(item) if show_full_path else self_groups_tree_set(item,'file')) )

        size_info = "Processed files size sum : " + bytes_to_str(size_sum) + "\n"
        if action==DELETE:
            trash_info =     "\n\nSend to Trash            : " + ("Yes" if self.cfg_get_bool(CFG_SEND_TO_TRASH) else "No")
            erase_empty_dirs = "\nErase empty directories  : " + ('Yes' if self.cfg_get_bool(CFG_ERASE_EMPTY_DIRS) else 'No')
            self.get_text_ask_dialog().show('Delete marked files ?','Scope: ' + scope_title + trash_info + erase_empty_dirs + '\n\n' + size_info + '\n' + '\n'.join(message))
            if not self.text_ask_dialog.res_bool:
                return True
        elif action==SOFTLINK:
            self.get_text_ask_dialog().show('Soft-Link marked files to first unmarked file in group ?','Scope: ' + scope_title + '\n\n' + size_info + '\n'+'\n'.join(message))
            if not self.text_ask_dialog.res_bool:
                return True
        elif action==HARDLINK:
            self.get_text_ask_dialog().show('Hard-Link marked files together in groups ?','Scope: ' + scope_title + '\n\n' + size_info +'\n'+'\n'.join(message))
            if not self.text_ask_dialog.res_bool:
                return True

        _ = {l_warning(line) for line in message}
        l_warning('###########################################################################################')
        l_warning('Confirmed.')
        return False

    @block_actions_processing
    @gui_block
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

    @block_actions_processing
    @gui_block
    @logwrapper
    def process_files_core(self,action,processed_items,remaining_items):
        self_status = self.status

        self_status('processing files ...')
        self.main_update()

        to_trash=self.cfg_get_bool(CFG_SEND_TO_TRASH)
        abort_on_error=self.cfg_get_bool(CFG_ABORT_ON_ERROR)
        erase_empty_dirs=self.cfg_get_bool(CFG_ERASE_EMPTY_DIRS)

        self_groups_tree_set = self.groups_tree_set
        self_get_index_tuple_groups_tree = self.get_index_tuple_groups_tree

        dude_core_delete_file_wrapper = dude_core.delete_file_wrapper
        self_crc_node_update = self.crc_node_update
        self_empty_dirs_removal = self.empty_dirs_removal
        dude_core_link_wrapper = dude_core.link_wrapper

        final_info=[]

        crc_to_size = {crc:size for size,size_dict in dude_core.files_of_size_of_crc_items() for crc in size_dict}

        counter = 0
        end_message_list=[]
        end_message_list_append = end_message_list.append

        if action==DELETE:
            directories_to_check=set()
            directories_to_check_add = directories_to_check.add
            for crc,items_list in processed_items.items():
                tuples_to_delete=set()
                tuples_to_delete_add = tuples_to_delete.add
                size = crc_to_size[crc]
                for item in items_list:
                    counter+=1
                    index_tuple=self_get_index_tuple_groups_tree(item)
                    tuples_to_delete_add(index_tuple)

                    (pathnr,path,file_name,ctime,dev,inode)=index_tuple

                    if erase_empty_dirs:
                        #print(f'{path=}')
                        if path:
                            #directories_to_check_add(dude_core.scanned_paths[pathnr]+path)
                            directories_to_check_add( tuple( [pathnr] + path.strip(sep).split(sep) ) )
                    if counter%128==0:
                        self_status('processing files %s ...' % counter)

                if resmsg:=dude_core_delete_file_wrapper(size,crc,tuples_to_delete,to_trash):
                    resmsg_str='\n'.join(resmsg)
                    l_error(resmsg_str)
                    end_message_list_append(resmsg_str)

                    if abort_on_error:
                        break

            for crc in processed_items:
                self_crc_node_update(crc)

            if erase_empty_dirs:
                #directories_to_check_list=

                directories_to_check_expanded=set()
                directories_to_check_expanded_add = directories_to_check_expanded.add

                for dir_tuple in directories_to_check:
                    elems = len(dir_tuple)-1
                    for i in range(elems):
                        combo_to_check = tuple(dir_tuple[0:2+i])
                        directories_to_check_expanded_add( combo_to_check )
                        #print(f'{combo_to_check=}')

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
            for crc,items_list in processed_items.items():
                counter+=1
                to_keep_item=list(remaining_items[crc])[0]

                index_tuple_ref=self_get_index_tuple_groups_tree(to_keep_item)
                size=int(self_groups_tree_set(to_keep_item,'size'))

                if resmsg:=dude_core_link_wrapper(True, do_rel_symlink, size,crc, index_tuple_ref, [self_get_index_tuple_groups_tree(item) for item in items_list ] ):
                    l_error(resmsg)

                    end_message_list_append(resmsg)

                    if abort_on_error:
                        break

                if counter%128==0:
                    self_status('processing crc groups %s ...' % counter)

            for crc in processed_items:
                self_crc_node_update(crc)

        elif action==HARDLINK:
            for crc,items_list in processed_items.items():
                counter+=1
                ref_item=items_list[0]
                index_tuple_ref=self_get_index_tuple_groups_tree(ref_item)
                size=int(self_groups_tree_set(ref_item,'size'))

                if resmsg:=dude_core_link_wrapper(False, False, size,crc, index_tuple_ref, [self_get_index_tuple_groups_tree(item) for item in items_list[1:] ] ):
                    l_error(resmsg)

                    end_message_list_append(resmsg)

                    if abort_on_error:
                        break

                if counter%128==0:
                    self_status('processing crc groups %s ...' % counter)

            for crc in processed_items:
                self_crc_node_update(crc)

        self.data_precalc()

        if end_message_list:
            self.get_text_info_dialog().show('Error','\n'.join(end_message_list))

        if final_info:
            self.get_text_info_dialog().show('Removed empty directories','\n'.join(final_info))

    @logwrapper
    def get_this_or_existing_parent(self,path):
        if path:
            if path_exists(path):
                return path

            return self.get_this_or_existing_parent(Path(path).parent.absolute())

    @block_actions_processing
    @gui_block
    @logwrapper
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

        affected_crcs=processed_items.keys()
        #print('affected_crcs:',affected_crcs)

        self.status('checking remaining items...')
        remaining_items={}

        self_MARK = self.MARK

        for crc in affected_crcs:
            remaining_items[crc]=[item for item in self.tree_children_sub[crc] if item not in self.tagged]

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
        if tree==self.groups_tree:
            item_to_select = self.sel_crc

            while True:
                try:
                    item_to_select = tree.next(item_to_select)
                except :
                    item_to_select = None

                if not item_to_select:
                    break

                if item_to_select not in affected_crcs:
                    break
        else:
            orglist=self.current_folder_items
            org_sel_item=self.sel_item
            try:
                org_sel_file=self.folder_tree.set(org_sel_item,'file')
            except :
                org_sel_file=None

        #############################################
        self.process_files_core(action,processed_items,remaining_items)
        #############################################

        #self.tagged.clear()
        #by nie redefiniowac obiektu
        #self_tagged_add = self.tagged.add
        #self_MARK = self.MARK
        #self_groups_tree_tag_has = self.groups_tree.tag_has
        #_ = [self_tagged_add(item) for item in self_groups_tree_tag_has(self_MARK)]

        self.tagged = self.groups_tree.tag_has(self.MARK)

        l_info('post-update %s',tree)

        if tree==self.groups_tree:
            if tree.exists(self.sel_crc):
                item_to_select=self.sel_crc

            l_info('updating groups : %s',item_to_select)

            if item_to_select:
                self.groups_tree.focus_set()
                self.groups_tree.focus(item_to_select)

                self.groups_tree_sel_change(item_to_select)
            else:
                self.initial_focus()
        else:
            parent = self.get_this_or_existing_parent(self.sel_path_full)
            if parent:
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

        self.selected[self.groups_tree]=None
        self.selected[self.folder_tree]=None
        self.find_result=()

    @logwrapper
    def get_closest_in_folder(self,prev_list,item,item_name,new_list):
        if item in new_list:
            return item

        if not new_list:
            return None

        self_folder_tree_set = self.folder_tree.set

        new_list_names=[self_folder_tree_set(item,'file') for item in self.current_folder_items] if self.current_folder_items else []

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

    @block_actions_processing
    def enter_dir(self,fullpath,sel):
        if self.find_tree_index==1:
            self.find_result=()

        if self.tree_folder_update(fullpath):
            children=self.current_folder_items
            res_list=[nodeid for nodeid in children if self.folder_tree.set(nodeid,'file')==sel]
            if res_list:
                item=res_list[0]
                self.folder_tree_see(item)
                self.folder_tree.focus(item)
                self.folder_tree_sel_change(item)

            elif children:
                self.folder_tree.focus(children[0])
                self.sel_file = self.groups_tree_set(children[0],'file')
                self.folder_tree_sel_change(children[0])

    def double_left_button(self,event):
        if self.actions_processing:
            tree=event.widget
            if tree.identify("region", event.x, event.y) != 'heading':
                if item:=tree.identify('item',event.x,event.y):
                    self.main.after_idle(lambda : self.tree_action(tree,item))

        return "break"

    @logwrapper
    def tree_action(self,tree,item,alt_pressed=False):
        if alt_pressed:
            self.open_folder()
        elif tree.set(item,'kind') == self.UPDIR:
            head,tail=path_split(self.sel_path_full)
            self.enter_dir(normpath(str(Path(self.sel_path_full).parent.absolute())),tail)
        elif tree.set(item,'kind') in (self.DIR,self.DIRLINK):
            self.enter_dir(self.sel_path_full+self.folder_tree.set(item,'file') if self.sel_path_full=='/' else sep.join([self.sel_path_full,self.folder_tree.set(item,'file')]),'..' )
        elif tree.set(item,'kind')!=self.CRC:
            self.open_file()

    @logwrapper
    def open_folder(self):
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

        if wrapper:=self.cfg.get(CFG_KEY_WRAPPER_FOLDERS):
            params_num = self.cfg.get(CFG_KEY_WRAPPER_FOLDERS_PARAMS)

            num = 1024 if params_num=='all' else int(params_num)
            run_command = lambda : Popen([wrapper,*params[:num]])
        elif windows:
            run_command = lambda : startfile(params[0])
        else:
            run_command = lambda : Popen(["xdg-open",params[0]])

        Thread(target=run_command,daemon=True).start()

    @logwrapper
    def open_file(self):
        if self.sel_path_full and self.sel_file:
            file_to_open = sep.join([self.sel_path_full,self.sel_file])

            if wrapper:=self.cfg.get(CFG_KEY_WRAPPER_FILE) and self.sel_kind in (self.FILE,self.LINK,self.SINGLE,self.SINGLEHARDLINKED):
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

        log_file = strftime('%Y_%m_%d_%H_%M_%S',localtime(time()) ) +'.txt'
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
            distro_info=Path(path_join(DUDE_DIR,'distro.info.txt')).read_text(encoding='ASCII')
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
            Gui(getcwd(),p_args.paths,p_args.exclude,p_args.exclude_regexp,p_args.norun)

    except Exception as e_main:
        print(e_main)
        l_error(e_main)
        sys.exit(1)
