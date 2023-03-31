#!/usr/bin/python3

####################################################################################
#
#  Copyright (c) 2022-2023 Piotr Jochymek
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

import os

import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import time

def set_geometry_by_parent(widget,parent):
    x_offset = int(parent.winfo_rootx()+0.5*(parent.winfo_width()-widget.winfo_width()))
    y_offset = int(parent.winfo_rooty()+0.5*(parent.winfo_height()-widget.winfo_height()))

    widget.geometry(f'+{x_offset}+{y_offset}')

class GenericDialog:
    locked_by_child={}

    def __init__(self,parent,icon,bg_color,title,pre_show=None,post_close=None,min_width=600,min_height=400):
        self.bg_color=bg_color

        self.widget = tk.Toplevel(parent,bg=self.bg_color,bd=0, relief='flat')
        self.widget.withdraw()
        self.widget.update()
        self.widget.protocol("WM_DELETE_WINDOW", lambda : self.hide())

        self.locked_by_child[self.widget]=False

        self.set_mins(min_width,min_height)

        self.focus=None

        self.widget.iconphoto(False, icon)

        self.widget.title(title)
        self.widget.bind('<Escape>', lambda event : self.hide() )

        self.widget.bind('<KeyPress-Return>', self.return_bind)

        self.parent=parent

        self.pre_show=pre_show
        self.post_close=post_close

        self.area_main = tk.Frame(self.widget,bg=self.bg_color)
        self.area_main.pack(side='top',expand=1,fill='both')

        #only grid here
        self.area_main.grid_columnconfigure(0, weight=1)

        self.area_buttons = tk.Frame(self.widget,bg=self.bg_color)
        self.area_buttons.pack(side='bottom',expand=0,fill='x')

        self.wait_var=tk.BooleanVar()
        self.wait_var.set(False)

        self.do_command_after_show=None
        self.command_on_close=None

    def set_mins(self,min_width,min_height):
        self.widget.minsize(min_width, min_height)

    def return_bind(self,event):
        widget=event.widget
        try:
            widget.invoke()
        except:
            pass

    def unlock(self):
        self.wait_var.set(True)

    def show(self,wait=True):
        if self.pre_show:
            self.pre_show()

        self.widget.wm_transient(self.parent)
        self.locked_by_child[self.parent]=True

        self.focus_restore=True
        self.pre_focus=self.parent.focus_get()

        self.widget.update()
        set_geometry_by_parent(self.widget,self.parent)

        self.wait_var.set(False)
        self.res_bool=False

        try:
            self.widget.deiconify()
            self.widget.update()
            self.widget.grab_set()
        except Exception as e:
            print(e)

        self.parent.config(cursor="watch")

        if self.focus:
            self.focus.focus_set()
            #focus.focus_force()

        set_geometry_by_parent(self.widget,self.parent)

        if self.do_command_after_show:
            commnad_res = self.do_command_after_show()

            if commnad_res:
                self.hide()
                return

        if wait:
            self.widget.wait_variable(self.wait_var)

    def hide(self,force_hide=False):
        if self.locked_by_child[self.widget]:
            return

        if not force_hide and self.command_on_close:
            self.command_on_close()
        else:
            self.widget.grab_release()

            self.widget.withdraw()

            try:
                self.widget.update()
            except Exception as e:
                pass

            self.parent.config(cursor="")

            if self.post_close:
                self.post_close()

            if self.focus_restore:
                if self.pre_focus:
                    self.pre_focus.focus_set()
                else:
                    self.parent.focus_set()

            self.locked_by_child[self.parent]=False

            self.wait_var.set(True)

class LabelDialog(GenericDialog):
    def __init__(self,parent,icon,bg_color,pre_show=None,post_close=None,min_width=300,min_height=120):
        super().__init__(parent,icon,bg_color,'',pre_show,post_close,min_width,min_height)

        self.label = tk.Label(self.area_main, text='',justify='center',bg=self.bg_color)
        self.label.grid(row=0,column=0,padx=5,pady=5)

        self.cancel_button=ttk.Button(self.area_buttons, text='OK', width=14, command=super().hide )
        self.cancel_button.pack(side='bottom', anchor='n',padx=5,pady=5)

        self.focus=self.cancel_button

    def show(self,title='',message=''):
        self.widget.title(title)
        self.label.configure(text=message)

        super().show()

class ProgressDialog(GenericDialog):
    def __init__(self,parent,icon,bg_color,pre_show=None,post_close=None,min_width=550,min_height=120):
        super().__init__(parent,icon,bg_color,'',pre_show,post_close,min_width,min_height)

        self.label_pic = tk.Label(self.area_main, text='',justify='center',bg=self.bg_color)
        self.label_pic.grid(row=1,column=0,padx=5,pady=5)

        self.label = tk.Label(self.area_main, text='',justify='center',bg=self.bg_color)
        self.label.grid(row=2,column=0,padx=5,pady=5)

        self.abort_button=ttk.Button(self.area_buttons, text='Abort', width=10,command=lambda : self.hide() )

        self.abort_button.pack(side='bottom', anchor='n',padx=5,pady=5)

        (frame_0:=tk.Frame(self.area_main,bg=self.bg_color)).grid(row=0, column=0, sticky='news')
        self.progr1var = tk.DoubleVar()
        self.progr1=ttk.Progressbar(frame_0,orient='horizontal',length=100, mode='determinate',variable=self.progr1var)
        self.progr1.grid(row=0,column=1,padx=1,pady=4,sticky='news')

        self.lab_l1=tk.Label(frame_0,width=18,bg=self.bg_color)
        self.lab_l1.grid(row=0,column=0,padx=1,pady=4)
        self.lab_l1.config(text='l1')

        self.lab_r1=tk.Label(frame_0,width=18,bg=self.bg_color)
        self.lab_r1.grid(row=0,column=2,padx=1,pady=4)
        self.lab_r1.config(text='r1')

        self.progr2var = tk.DoubleVar()
        self.progr2=ttk.Progressbar(frame_0,orient='horizontal',length=100, mode='determinate',variable=self.progr2var)
        self.progr2.grid(row=1,column=1,padx=1,pady=4,sticky='news')

        self.lab_l2=tk.Label(frame_0,width=18,bg=self.bg_color)
        self.lab_l2.grid(row=1,column=0,padx=1,pady=4)
        self.lab_l2.config(text='l2')

        self.lab_r2=tk.Label(frame_0,width=18,bg=self.bg_color)
        self.lab_r2.grid(row=1,column=2,padx=1,pady=4)
        self.lab_r2.config(text='r2')

        frame_0.grid_columnconfigure(1, weight=1)

        self.focus=self.abort_button

        self.message_prev=''
        self.lab_r1_str_prev=''
        self.lab_r2_str_prev=''
        self.time_without_busy_sign=0
        self.ps_index=0

    PROGRESS_SIGNS='◐◓◑◒' if os.name=='nt' else '|/-\\'

    def update_fields(self,message,progress1=None,progress2=None,lab_r1_str=None,lab_r2_str=None,status_info=None,image=''):
        prefix=''
        append_status=''

        self.label_pic.configure(image=image)

        if self.lab_r1_str_prev==lab_r1_str and self.lab_r2_str_prev==lab_r2_str and self.message_prev==message:
            if time.time()>self.time_without_busy_sign+1.0:
                prefix=self.PROGRESS_SIGNS[self.ps_index]
                self.ps_index=(self.ps_index+1)%4
                if len(status_info)>30:
                    append_status='%s...' % status_info[0:30]

        else:
            self.message_prev=message
            self.lab_r1_str_prev=lab_r1_str
            self.lab_r2_str_prev=lab_r2_str

            self.time_without_busy_sign=time.time()

            self.progr1var.set(progress1)
            self.lab_r1.config(text=lab_r1_str)
            self.progr2var.set(progress2)
            self.lab_r2.config(text=lab_r2_str)

        self.label.configure(text='%s\n%s\n%s'%(prefix,message,append_status))
        self.area_main.update()

        return prefix

    def show(self,title='',message='',wait=False):
        self.widget.title(title)
        self.label.configure(text=message)

        super().show(wait)

class TextDialogInfo(GenericDialog):
    def __init__(self,parent,icon,bg_color,pre_show=None,post_close=None,min_width=1000,min_height=600):
        super().__init__(parent,icon,bg_color,'',pre_show,post_close,min_width,min_height)

        textwidth=80
        self.text = scrolledtext.ScrolledText(self.area_main,relief='groove' , bd=2,bg='white',width = textwidth,takefocus=True)
        self.text.frame.config(takefocus=False)
        self.text.vbar.config(takefocus=False)

        self.text.tag_configure('RED', foreground='red')
        self.text.tag_configure('GRAY', foreground='gray')

        self.text.grid(row=0,column=0,padx=5,pady=5)

        self.area_main.grid_rowconfigure(0, weight=1)

        self.cancel_button=ttk.Button(self.area_buttons, text='Close', width=14, command=super().hide )
        self.cancel_button.pack(side='bottom', anchor='n',padx=5,pady=5)

        self.focus=self.cancel_button

    def show(self,title='',message=''):
        self.widget.title(title)

        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        for line in message.split('\n'):
            line_splitted=line.split('|')
            tag=line_splitted[1] if len(line_splitted)>1 else None

            self.text.insert('end', line_splitted[0] + "\n", tag)

        self.text.configure(state='disabled')
        self.text.grid(row=0,column=0,sticky='news',padx=5,pady=5)

        super().show()

class TextDialogQuestion(TextDialogInfo):
    def __init__(self,parent,icon,bg_color,pre_show=None,post_close=None,min_width=1000,min_height=600):
        super().__init__(parent,icon,bg_color,pre_show,post_close,min_width,min_height)

        self.cancel_button.configure(text='Cancel')
        self.cancel_button.pack(side='left', anchor='n',padx=5,pady=5)

        self.ok_button=ttk.Button(self.area_buttons, text='OK', width=14, command=self.ok )
        self.ok_button.pack(side='right', anchor='n',padx=5,pady=5)

        self.focus=self.cancel_button

    def ok (self):
        self.res_bool=True
        self.wait_var.set(True)
        super().hide()

    def show(self,title='',message=''):
        super().show(title,message)

class EntryDialogQuestion(LabelDialog):
    def __init__(self,parent,icon,bg_color,pre_show=None,post_close=None,min_width=400,min_height=120):
        super().__init__(parent,icon,bg_color,pre_show,post_close,min_width,min_height)

        self.cancel_button.configure(text='Cancel')

        self.entry_val=tk.StringVar()

        self.entry = ttk.Entry(self.area_main, textvariable=self.entry_val,justify='left')
        self.entry.grid(row=2,column=0,padx=5,pady=5,sticky="wens")

        self.button_ok = ttk.Button(self.area_buttons, text='OK', width=14, command=self.ok )
        self.button_ok.pack(side='left', anchor='n',padx=5,pady=5)

        self.cancel_button.pack(side='right')

        self.focus=self.entry

    def return_bind(self,event):
        widget=event.widget
        if widget==self.entry:
            self.button_ok.invoke()
        else:
            super().return_bind(event)

    def ok(self):
        self.res_bool= True
        self.res_str = self.entry_val.get()
        super().hide()

    def show(self,title='',message='',initial=''):
        self.entry_val.set(initial)

        self.res_str=''
        super().show(title,message)

class CheckboxEntryDialogQuestion(EntryDialogQuestion):
    def __init__(self,parent,icon,bg_color,pre_show=None,post_close=None,min_width=400,min_height=120):
        super().__init__(parent,icon,bg_color,pre_show,post_close,min_width,min_height)

        self.check_val=tk.BooleanVar()

        self.check = ttk.Checkbutton(self.area_main, variable=self.check_val)
        self.check.grid(row=1,column=0,padx=5,pady=5,sticky="wens")
        self.result2=None

        self.focus=self.entry

    def show(self,title='',message='',initial='',checkbutton_text='',checkbutton_initial=False):
        self.check_val.set(checkbutton_initial)
        self.check.configure(text=checkbutton_text)

        self.res_check=checkbutton_initial
        super().show(title,message,initial)
        self.res_check = self.check_val.get()


class FindEntryDialog(CheckboxEntryDialogQuestion):
    def __init__(self,parent,icon,bg_color,mod_cmd,prev_cmd,next_cmd,pre_show=None,post_close=None,min_width=400,min_height=120):
        super().__init__(parent,icon,bg_color,pre_show,post_close,min_width,min_height)

        self.button_prev = ttk.Button(self.area_buttons, text='prev (Shift+F3)', width=14, command=self.prev )
        self.button_prev.pack(side='left', anchor='n',padx=5,pady=5)

        self.button_next = ttk.Button(self.area_buttons, text='next (F3)', width=14, command=self.next )
        self.button_next.pack(side='right', anchor='n',padx=5,pady=5)

        self.mod_cmd=mod_cmd
        self.prev_cmd=prev_cmd
        self.next_cmd=next_cmd

        self.button_ok.pack_forget()

        self.check.configure(command=self.mod)

        self.widget.bind('<KeyRelease>',lambda event : self.mod())

        self.widget.bind('<KeyPress-F3>', self.f3_bind)

        self.focus=self.entry

    def f3_bind(self,event):
        if 'Shift' in str(event):
            self.button_prev.invoke()
        else:
            self.button_next.invoke()

    def return_bind(self,event):
        widget=event.widget
        if widget==self.entry:
            self.button_next.invoke()
        else:
            super().return_bind(event)

    def mod(self):
        self.mod_cmd(self.entry_val.get(),self.check_val.get())

    def prev(self):
        self.prev_cmd(self.entry_val.get(),self.check_val.get())

    def next(self):
        self.next_cmd(self.entry_val.get(),self.check_val.get())

    def show(self,title='',message='',initial='',checkbutton_text='',checkbutton_initial=False):
        self.focus_restore=False
        try:
            super().show(title=title,message=message,initial=initial,checkbutton_text=checkbutton_text,checkbutton_initial=checkbutton_initial)
        except Exception as e:
            print(e)

class SFrame(tk.Frame):
    def __init__(self, parent,bg,relief='flat',width=200,height=100):
        super().__init__(parent)

        self.canvas = tk.Canvas(self, bd=0, bg=bg,highlightcolor=bg,width=width,height=height,relief=relief)
        self.f = tk.Frame(self.canvas, bg=bg,takefocus=False)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas_window = self.canvas.create_window((0,0), window=self.f, anchor="nw")

        self.f.bind("<Configure>", self.frame_conf)
        self.canvas.bind("<Configure>", self.canv_conf)

        self.f.bind('<Enter>', self.on_enter)
        self.f.bind('<Leave>', self.on_leave)

        self.frame_conf(None)

    def frame(self):
        return self.f

    def frame_conf(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def canv_conf(self, event):
        self.canvas.itemconfig(self.canvas_window, width = event.width)

    def wheel(self, event):
        if os.name=='nt':
            self.canvas.yview_scroll(int(-1 * (event.delta/120)), "units")
        else:
            if event.num == 4:
                self.canvas.yview_scroll( -1, "units" )
            elif event.num == 5:
                self.canvas.yview_scroll( 1, "units" )

    def on_enter(self, event):
        if os.name=='nt':
           self.canvas.bind_all("<MouseWheel>", self.wheel)
        else:
            self.canvas.bind_all("<Button-4>", self.wheel)
            self.canvas.bind_all("<Button-5>", self.wheel)

    def on_leave(self, event):
        if os.name=='nt':
            self.canvas.unbind_all("<MouseWheel>")
        else:
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")
