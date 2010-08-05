Vim Debugger
============

VimDebugger is a dbgp client plugin for vim for debugging php applications with xdebug.  It is currently in early stages, but is already much more advanced than many other options.

Special Thanks
==============

VimDebugger utilizes the ActiveState DBGp library.
VimDebugger borrows code liberally from [the remote PHP debugger](http://www.vim.org/scripts/script.php?script_id=1152) vim plugin by Seung Woo Shin.

Setup
=====

At present, VimDebugger.py must be saved as $VIMRUNTIME."/plugin/VimDebugger.py" in order to work correctly.  I hope to allow more flexible placement of this file in a future release.  VimDebugger.vim should generally be placed in the same directory.

Remote Debugging
================
VimDebugger will listen on localhost:9000.  This could be changed in VimDebugger.vim, but currently is not easily configurable through your .vimrc.  You need to have xdebug already configured to connect to that port.

Debugger functions
==================
The following commands are added by the debugger for all your remote debugging needs:

 * :DbgRun - Starts the listener (listens for 10 seconds) if your script is not already attached.  If it is, continues (will run to the end or until the next breakpoint)
 * :DbgDetach - Detaches the remote debugger and shuts down the listener
 * :DbgToggleBreakpoint - Toggles a breakpoint on the current line of the current file
 * :DbgStepInto - Steps into the next function or include
 * :DbgStepOver - Steps over the next function or include
 * :DbgStepOut - Steps out to the next step up in the stack

Key Bindings
============
The debugger does not automatically bind any hotkeys, but leaves that to you to do in your own .vimrc.  I often use Visual Studio, so I set my key bindings up in a similar way:

    map <F11> :DbgStepInto<CR>
    map <F10> :DbgStepOver<CR>
    map <S-F11> :DbgStepOut<CR>
    map <F5> :DbgRun<CR>
    map <S-F5> :DbgDetach<CR>
    map <F8> :DbgToggleBreakpoint<CR>

Watch
=====
Currently, there are no functions for adding your own watch items, but that is planned for one of the next releases.  For now, the watch window will automatically refresh every step with the current context.  The Watch window utilizes vim code folding on multi-line entries, so if you have an object, be sure to expand it by double clicking, hitting enter, or using the vim code folding keyboard commands to see the introspection at work.  Only three levels are returned, to keep the response from overwhelming the debugger.

For objects, a list of the methods available on that object will be returned with their visibility.  Also, a list of properties will be returned with their visibility and their value.

For arrays, a list of values (up to three nested levels) will be returned.

Stack
=====
The stack window updates every frame. To go to another part of the stack, simply go to the line in question and double click or press enter.
