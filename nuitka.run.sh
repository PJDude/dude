CCFLAGS='-Ofast -static'  python3.10 -m nuitka --follow-imports --follow-stdlib --onefile --linux-icon=./icon.ico --show-scons --show-progress --show-modules --include-data-files=./icon.png=./icon.png --include-data-files=./LICENSE=./LICENSE --enable-plugin=tk-inter --output-filename=dude --lto=yes ./dude.py 2>&1 | tee ./nuitka.log

#LDFLAGS='-flinker-output=exec' -s -static-libgcc

#collect2: error: ld returned 1 exit status
#scons: *** [/home/runner/work/dude/dude/dude.dist/dude] Error 1
#scons: internal stack trace:
#  File "/opt/hostedtoolcache/Python/3.10.10/x64/lib/python3.10/site-packages/nuitka/build/inline_copy/lib/scons-3.1.2/SCons/Job.py", line 258, in run
#    task.execute()
#  File "/opt/hostedtoolcache/Python/3.10.10/x64/lib/python3.10/site-packages/nuitka/build/inline_copy/lib/scons-3.1.2/SCons/Script/Main.py", line 206, in execute
#    SCons.Taskmaster.OutOfDateTask.execute(self)
#  File "/opt/hostedtoolcache/Python/3.10.10/x64/lib/python3.10/site-packages/nuitka/build/inline_copy/lib/scons-3.1.2/SCons/Taskmaster.py", line 255, in execute
#    self.targets[0].build()
#  File "/opt/hostedtoolcache/Python/3.10.10/x64/lib/python3.10/site-packages/nuitka/build/inline_copy/lib/scons-3.1.2/SCons/Node/__init__.py", line 766, in build
#    self.get_executor()(self, **kw)
#  File "/opt/hostedtoolcache/Python/3.10.10/x64/lib/python3.10/site-packages/nuitka/build/inline_copy/lib/scons-3.1.2/SCons/Executor.py", line 397, in __call__
#    return _do_execute_map[self._do_execute](self, target, kw)
#  File "/opt/hostedtoolcache/Python/3.10.10/x64/lib/python3.10/site-packages/nuitka/build/inline_copy/lib/scons-3.1.2/SCons/Executor.py", line 131, in execute_action_list
#    raise status    # TODO pylint E0702: raising int not allowed
#scons: building terminated because of errors.
