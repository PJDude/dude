import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import scrolledtext

def set_geometry_by_parent(widget,parent):
    x = int(parent.winfo_rootx()+0.5*(parent.winfo_width()-widget.winfo_width()))
    y = int(parent.winfo_rooty()+0.5*(parent.winfo_height()-widget.winfo_height()))

    widget.geometry(f'+{x}+{y}')

class GenericDialog :
    def __init__(self,parent,icon,bg,title,pre_show=None,post_close=None,min_width=600,min_height=400):
        self.bg=bg
  
        self.widget = tk.Toplevel(parent)
        self.widget.withdraw()
        self.widget.update()
        self.widget.protocol("WM_DELETE_WINDOW", self.hide)
        self.widget.minsize(min_width, min_height)
        
        self.widget.iconphoto(False, icon)

        self.widget.config(bd=0, relief=FLAT)

        self.widget.title(title)
        self.widget.bind('<Escape>', self.hide)
        
        self.widget.bind('<KeyPress-Return>', self.return_bind)
        
        self.parent=parent
        
        self.pre_show=pre_show
        self.post_close=post_close
        
        self.area_main = tk.Frame(self.widget)
        self.area_main.pack(side='top',expand=1,fill='both')
        
        #only grid here
        self.area_main.grid_columnconfigure(0, weight=1)
        
        self.area_buttons = tk.Frame(self.widget)
        self.area_buttons.pack(side='bottom',expand=0,fill='x')
        
        self.res=tk.StringVar()
        
        self.focus_restore=True
    
    def return_bind(self,event):
        widget=event.widget
        try:
            widget.invoke()
        except:
            pass
    
    def unlock(self,val='unlock'):
        self.res.set(val)
        
    def show(self,focus=None,do_command=None):
        self.widget.wm_transient(self.parent)
        
        self.preFocus=self.parent.focus_get()

        if self.pre_show:
            self.pre_show()
        
        self.parent.config(cursor="watch")
        
        self.parent.lift()
        
        self.widget.update()
        set_geometry_by_parent(self.widget,self.parent)
        self.widget.grab_set()
        
        self.res.set('')
        self.widget.deiconify()
        
        if focus:
            focus.focus_set()
        
        self.widget.update()
        set_geometry_by_parent(self.widget,self.parent)
        self.widget.lift()
        
        if do_command:
            commnad_res = do_command()
            
            if commnad_res:
                self.hide()
                return
            
        self.widget.wait_variable(self.res)
        
        return self.res.get()
        
    def hide(self,event=None,SetRes=True):
        self.widget.grab_release()
        self.parent.config(cursor="")

        self.widget.withdraw()
        
        try:
            self.widget.update()
        except Exception as e:
            pass
        
        if self.post_close:
            self.post_close()
        
        if self.focus_restore:
            if self.preFocus:
                self.preFocus.focus_set()
            else:
                self.parent.focus_set()
        
        if SetRes:
            self.res.set('')

class LabelDialog(GenericDialog):
    def __init__(self,parent,icon,bg,pre_show=None,post_close=None,min_width=300,min_height=120):
        super().__init__(parent,icon,bg,'',pre_show,post_close,min_width=300,min_height=120)
        
        self.label = tk.Label(self.area_main, text='',justify='center',bg=self.bg)
        self.label.grid(row=0,column=0,padx=5,pady=5)
    
        self.cancel_button=ttk.Button(self.area_buttons, text='OK', width=14, command=super().hide )
        self.cancel_button.pack(side='bottom', anchor='n',padx=5,pady=5)
        
    def show(self,title,message,focus=None,min_width=300,min_height=120):
        try:
            if not focus:
                focus=self.cancel_button
            
            self.widget.title(title)
            self.label.configure(text=message)
            self.widget.minsize(min_width, min_height)
            return super().show(focus)
        except Exception as e:
            print(e)
            return ""

class TextDialogQuestion(GenericDialog):
    def __init__(self,parent,icon,bg,pre_show=None,post_close=None,min_width=300,min_height=120):
        super().__init__(parent,icon,bg,'',pre_show,post_close,min_width=300,min_height=120)
        
        textwidth=80
        self.Text = scrolledtext.ScrolledText(self.area_main,relief='groove' , bd=2,bg='white',width = textwidth,takefocus=True)
        self.Text.frame.config(takefocus=False)
        self.Text.vbar.config(takefocus=False)

        self.Text.tag_configure('RED', foreground='red')
        self.Text.tag_configure('GRAY', foreground='gray')
        
        self.Text.grid(row=0,column=0,padx=5,pady=5)
    
        self.cancel_button=ttk.Button(self.area_buttons, text='Cancel', width=14, command=super().hide )
        self.cancel_button.pack(side='left', anchor='n',padx=5,pady=5)
        
        self.ok_button=ttk.Button(self.area_buttons, text='OK', width=14, command=self.ok )
        self.ok_button.pack(side='right', anchor='n',padx=5,pady=5)
    
    def ok (self,event=None):
        self.res.set('1')
        super().hide(SetRes=False)
        
    def show(self,title,message,focus=None,min_width=800,min_height=400):
        try:
            self.widget.title(title)
            
            if not focus:
                focus=self.cancel_button
                
            self.Text.configure(state=NORMAL)
            self.Text.delete('1.0', END)
            for line in message.split('\n'):
                lineSplitted=line.split('|')
                tag=lineSplitted[1] if len(lineSplitted)>1 else None

                self.Text.insert(END, lineSplitted[0] + "\n", tag)

            self.Text.configure(state=DISABLED)
            self.Text.grid(row=0,column=0,sticky='news',padx=5,pady=5)
            
            self.widget.minsize(min_width, min_height)
            res = super().show(focus)
            return True if res else False
            
        except Exception as e:
            print(e)
            return ""
            
class EntryDialogQuestion(LabelDialog):
    def __init__(self,parent,icon,bg,pre_show=None,post_close=None):
        super().__init__(parent,icon,bg,pre_show,post_close,min_width=300,min_height=120)
        
        self.cancel_button.configure(text='Cancel')
        
        self.entry_val=tk.StringVar()
        
        self.entry = ttk.Entry(self.area_main, textvariable=self.entry_val,justify='left')
        self.entry.grid(row=2,column=0,padx=5,pady=5,sticky="wens")
    
        self.button_ok = ttk.Button(self.area_buttons, text='OK', width=14, command=self.ok )
        self.button_ok.pack(side='left', anchor='n',padx=5,pady=5)
    
        self.cancel_button.pack(side='right')
       
    def return_bind(self,event):
        widget=event.widget
        if widget==self.entry:
            self.button_ok.invoke()
        else:
            super().return_bind(event)
    
    def ok(self,event=None):
        self.res.set(str(self.entry_val.get()))
        super().hide(SetRes=False)
        
    def show(self,title,message,initial,min_width=300,min_height=120):
        self.entry_val.set(initial)
        
        res = super().show(title,message,focus=self.entry,min_width=min_width,min_height=min_height)
        
        return res

class CheckboxEntryDialogQuestion(EntryDialogQuestion):
    def __init__(self,parent,icon,bg,pre_show=None,post_close=None):
        super().__init__(parent,icon,bg,pre_show,post_close)
        
        self.check_val=tk.BooleanVar()
        
        self.check = ttk.Checkbutton(self.area_main, variable=self.check_val)
        self.check.grid(row=1,column=0,padx=5,pady=5,sticky="wens")
    
    def show(self,title,message,initial,CheckDescr,CheckInitial,min_width=300,min_height=120):

        self.check_val.set(CheckInitial)
        self.check.configure(text=CheckDescr)

        res = super().show(title,message,initial,min_width=min_width,min_height=min_height)
        
        return(self.check_val.get(),res)

class FindEntryDialog(CheckboxEntryDialogQuestion):
    def __init__(self,parent,icon,bg,mod_cmd,prev_cmd,next_cmd,pre_show=None,post_close=None):
        super().__init__(parent,icon,bg,pre_show,post_close)

        self.button_prev = ttk.Button(self.area_buttons, text='prev (Shift+F3)', width=14, command=self.prev )
        self.button_prev.pack(side='left', anchor='n',padx=5,pady=5)   
        
        self.button_next = ttk.Button(self.area_buttons, text='next (F3)', width=14, command=self.next )
        self.button_next.pack(side='right', anchor='n',padx=5,pady=5)   
        
        self.mod_cmd=mod_cmd
        self.prev_cmd=prev_cmd
        self.next_cmd=next_cmd
        
        self.button_ok.pack_forget()
        
        self.check.configure(command=self.mod)
        
        self.widget.bind('<KeyRelease>',self.mod)
        
        self.widget.bind('<KeyPress-F3>', self.F3_bind)
        self.focus_restore=False
        
    def F3_bind(self,event):
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
    
    def mod(self,event=None):
        self.mod_cmd(self.entry_val.get(),self.check_val.get())
        
    def prev(self,event=None):
        self.prev_cmd(self.entry_val.get(),self.check_val.get())
    
    def next(self,event=None):
        self.next_cmd(self.entry_val.get(),self.check_val.get())

    def show(self,message,initial,CheckInitial=False,min_width=300,min_height=120):
        try:
            super().show(title='Find',message=message,initial=initial,CheckDescr='Use regular expressions matching',CheckInitial=CheckInitial)
        except Exception as e:
            print(e)
        