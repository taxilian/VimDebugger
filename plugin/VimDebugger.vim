" Copyright (c) 2010 Richard Bateman
"
" The MIT License
"
" Permission is hereby granted, free of charge, to any person obtaining
" a copy of this software and associated documentation files
" (the "Software"), to deal in the Software without restriction,
" including without limitation the rights to use, copy, modify,
" merge, publish, distribute, sublicense, and/or sell copies of the
" Software, and to permit persons to whom the Software is furnished
" to do so, subject to the following conditions:
"
" The above copyright notice and this permission notice shall be included
" in all copies or substantial portions of the Software.
"
" THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
" OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
" MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
" IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
" CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
" TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
" SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"
"
" NOTE: This software makes use of other libraries, which are inlined in the
" code.  These libraries are included with their original copyright and
" license notice.
"
"
" Authors:
"    Richard Bateman <taxilian@gmail.com>
"    Steve Francia <spf13-vim@spf13.com>


if has('python')
	if filereadable($VIMRUNTIME."/bundle/VimDebugger/plugin/VimDebugger.py")
	  pyfile $VIMRUNTIME/bundle/VimDebugger/plugin/VimDebugger.py
	elseif filereadable($HOME."/.vim/bundle/VimDebugger/plugin/VimDebugger.py")
	  pyfile $HOME/.vim/bundle/VimDebugger/plugin/VimDebugger.py
	elseif filereadable($VIMRUNTIME."/plugin/VimDebugger.py")
	  pyfile $VIMRUNTIME/plugin/VimDebugger.py
	elseif filereadable($HOME."/.vim/plugin/VimDebugger.py")
	  pyfile $HOME/.vim/plugin/VimDebugger.py
	elseif filereadable($VIM."/vimfiles/plugin/VimDebugger.py")
	  pyfile $VIM/vimfiles/plugin/VimDebugger.py
	else
	  call confirm('VimDebugger.vim: Unable to find VimDebugger.py. Place it in either your home vim directory or in the Vim runtime directory.', 'OK')
	endif

	sign define _dbg_current text=->  texthl=DbgCurrent linehl=DbgCurrent
	sign define _dbg_stack text==>  texthl=DbgCurrent linehl=DbgCurrent
	sign define _dbg_breakpt text=B>  texthl=DbgBreakPt linehl=DbgBreakPt

	command! -nargs=0 -bar DbgRun               python __debugger.run()
	command! -nargs=0 -bar DbgListen            python __debugger.start_debugger()
	command! -nargs=0 -bar DbgStop              python __debugger.stop()
	command! -nargs=0 -bar DbgDetach            python __debugger.detach()
	command! -nargs=0 -bar DbgToggleBreakpoint  python __debugger.toggleLineBreakpointHere()
	command! -nargs=0 -bar DbgStepInto          python __debugger.stepInto()
	command! -nargs=0 -bar DbgStepOver          python __debugger.stepOver()
	command! -nargs=0 -bar DbgStepOut           python __debugger.stepOut()
	command! -nargs=0 -bar DbgRefreshWatch      python __debugger.updateWatch()
	command! -nargs=0 -bar DbgFlushBreakpoints  python __debugger.removeAllBreakpoints()
	command! -nargs=0 -bar DbgAddWatch          call g:__dbg_addWatchEval()
endif

function! g:__dbg_WatchFoldText()
  let nucolwidth = &fdc + &number*&numberwidth
  let winwd = winwidth(0) - nucolwidth - 5
  let foldlinecount = foldclosedend(v:foldstart) - foldclosed(v:foldstart) + 1
  let prefix = ""
  let fdnfo = prefix . string(v:foldlevel) . "," . string(foldlinecount) . "(+)"
  let line = getline(v:foldstart) 
  let fillcharcount = winwd - len(line) - len(fdnfo)
  return line . repeat(" ",fillcharcount) . fdnfo
endfunction

function! g:__dbg_addWatchEval()
    let g:__dbg_watchEval = inputdialog("Please enter the expression to add to watch:")
    python __debugger.addWatchExpr(vim.eval("g:__dbg_watchEval"))
    python __debugger.updateWatch()
endfunction

if has('python')
  function DefPython()
""" Begin python code for managing the debugger
python <<EOF

import vim, os

class VimWindow:
    """ wrapper class of window of vim """
    def __init__(self, owner, name = 'DEBUG_WINDOW'):
        """ initialize """
        self.name       = name
        self.buffer     = None
        self.firstwrite = True
        self.owner = owner

    def isprepared(self):
        """ check window is OK """
        if self.buffer == None or len(dir(self.buffer)) == 0 or self.getwinnr() == -1:
            return False
        return True

    def prepare(self):
        """ check window is OK (switch to working tab first), if not then create """
        self.owner.gotoWorkingTab()
        if not self.isprepared():
            self.create()

    def on_create(self):
        pass

    def getwinnr(self):
        return int(vim.eval("bufwinnr('"+self.name+"')"))

    def write(self, msg):
        """ append last """
        self.prepare()
        msg = msg.encode("utf-8", "replace")
        if self.firstwrite:
            self.firstwrite = False
            self.buffer[:] = str(msg).split('\n')
        else:
            self.buffer.append(str(msg).split('\n'))
        self.command('normal G')
        #self.window.cursor = (len(self.buffer), 1)

    def create(self, method = 'new'):
        """ create window """
        vim.command('silent ' + method + ' ' + self.name)
        #if self.name != 'LOG___WINDOW':
        vim.command("setlocal buftype=nofile")
        vim.command("setlocal noswapfile")
        vim.command("setlocal nowrap")
        self.buffer = vim.current.buffer
        self.width  = int( vim.eval("winwidth(0)")  )
        self.height = int( vim.eval("winheight(0)") )
        self.on_create()

    def destroy(self):
        """ destroy window """
        if self.buffer == None or len(dir(self.buffer)) == 0:
            return
        #if self.name == 'LOG___WINDOW':
        #  self.command('hide')
        #else:
        self.command('bdelete ' + self.name)
        self.firstwrite = True

    def clean(self):
        """ clean all datas in buffer """
        self.prepare()
        self.buffer[:] = []
        self.firstwrite = True

    def command(self, cmd):
        """ go to my window & execute command """
        self.prepare()
        winnr = self.getwinnr()
        if winnr != int(vim.eval("winnr()")):
            vim.command(str(winnr) + 'wincmd w')
        vim.command(cmd)

#
# class for the window pane that holds the stack trace
#
class StackWindow(VimWindow):
    def __init__(self, owner, name = 'STACK_WINDOW'):
        VimWindow.__init__(self, owner, name)

    def setStack(self, sList):
        maxFileLen = 0
        maxPathLen = 0
        maxWhereLen = 0
        maxDepthLen = len(str(len(sList)))
        self.clean()

        # calculate the correct size of the columns
        for frame in sList:
            filename = frame.filename
            frame.localFileURI = urllib.unquote(filename).replace("file://", "")
            # if this is Windows, remove the initial '/' if needed
            if (os.name.lower() == 'nt' or os.name.lower() == "win" or os.name.lower() == "windows") and filename[0] == "/":
                frame.localFileURI = filename[1:]
            (frame.localPathName, frame.localFileName) = os.path.split(frame.localFileURI)
            frame.localFileName = "%s:%d" % (frame.localFileName, frame.lineno)
            if maxFileLen < len(frame.localFileName):
                maxFileLen = len(frame.localFileName)
            if maxPathLen < len(frame.localPathName):
                maxPathLen = len(frame.localPathName)
            if maxWhereLen < len(frame.where):
                maxWhereLen = len(frame.where)

        header = "%s %s %s %s" % ("#".rjust(maxDepthLen), "File".ljust(maxFileLen), "Loc".ljust(maxWhereLen), "Path".ljust(maxPathLen))
        self.write(header)
        # add the rows
        for frame in sList:
            line = "%s %s %s %s" % (str(frame.depth).rjust(maxDepthLen), frame.localFileName.ljust(maxFileLen), frame.where.ljust(maxWhereLen), frame.localPathName.ljust(maxPathLen))
            self.write(line)

    def on_create(self):
        self.command('highlight CurStack term=reverse ctermfg=White ctermbg=Red gui=reverse')
        self.command('setlocal noai nocin')
        self.command('setlocal nonumber noswapfile')

        # set key mappings for the stack window
        self.command("nnoremap <buffer> <silent> <cr>          :python __debugger.selectStackDepth()<cr>")
        self.command("nnoremap <buffer> <silent> <2-LeftMouse> :python __debugger.selectStackDepth()<cr>")
        self.command("resize 10%")

        self.highlight_stack(0)

    def highlight_stack(self, no):
        self.command('syntax clear')
        self.command('syntax region CurStack start="^%s " end="$"' % no)

#
# class for debugger traces (misc info)
#
class TraceWindow(VimWindow):
    def __init__(self, owner, name = 'TRACE_WINDOW'):
        VimWindow.__init__(self, owner, name)

    def on_create(self):
        self.command('set nowrap fdm=marker fmr={{{,}}} fdl=0')

#
# class for the watch window
#
class WatchWindow(VimWindow):
    SourceList = {}

    def __init__(self, owner, name = 'WATCH_WINDOW'):
        VimWindow.__init__(self, owner, name)

    def clean(self):
        """ clean all datas in buffer """
        VimWindow.clean(self)
        self.write("<?php")
        self.SourceList = {}

    def write(self, msg, file = "", line = -1):
        """ append last """
        VimWindow.write(self, msg)
        lineNo = len(self.buffer)
        if line > -1:
            self.SourceList[lineNo] = (file, line)
        #self.window.cursor = (len(self.buffer), 1)

    def lineEnter(self):
        self.prepare()
        line = vim.current.window.cursor[0]
        if line in self.SourceList:
            file, filePos = self.SourceList[line]
            self.owner.gotoWorkingTab()
            self.owner.gotoSourceWindow()
            vim.command("tabe %s" % file)
            vim.command("normal %dG" % filePos)
        else:
            vim.command("normal za")

    def on_create(self):
        self.write('<?php')
        self.command('setlocal noai nocin ft=php')
        self.command('setlocal foldenable foldmethod=marker foldmarker={,} commentstring=%s foldcolumn=0 foldlevel=0 nonumber noswapfile shiftwidth=2')
        self.command('setlocal foldtext=g:__dbg_WatchFoldText()')
        self.command("nnoremap <buffer> <silent> <cr>          :python __debugger.ui._watchLineEnter()<cr>")
        self.command("nnoremap <buffer> <silent> <2-LeftMouse> :python __debugger.ui._watchLineEnter()<cr>")
        #setlocal foldtext=ProjFoldText() nobuflisted nowrap

    def setPropertyList(self, plist1, plist2, vlist):
        self.clean()
        for i in range(0,len(plist2)):
            line = "%s = " % plist2[i]
            item = vlist[1][i]
            self.writeValue(item, 0, line)
        for i in range(0,len(plist1)):
            line = "%s = " % plist1[i]
            item = vlist[0][i]
            self.writeValue(item, 0, line)

    def writeValue(self, item, level, firstLine):
        if isinstance(item, list):
            if len(item) > 0:
                self.writeArrayValues(item, level, firstLine + "array{")
            else:
                self.write("".ljust(2*level) + firstLine + "array{}")
        elif isinstance(item, dict):
            if "isClass" in item and item["isClass"] and "className" in item:
                self.writeClassValues(item, level, firstLine + "%s object {" % item["className"])
            elif len(item.keys()) > 0:
                self.writeDictValues(item, level, firstLine + "array{")
            else:
                self.write("".ljust(2*level) + firstLine + "array{}")
        elif isinstance(item, basestring):
            self.write("".ljust(2*(level)) + firstLine + '"%s",' % item.replace('"', '\\"'))
        else:
            self.write("".ljust(2*(level)) + firstLine + r'%s,' % item)

    def writeClassValues(self, arr, level, firstLine):
        self.write("".ljust(2*level) + firstLine)
        if len(arr["methods"]) > 0:
            self.write("".ljust(2*(level+1)) + "%d methods {" % len(arr["methods"]))
            for item in sorted(arr["methods"].keys()):
                location = arr["methods"][item]
                self.write("".ljust(2*(level+2)) + item, location[0], location[1])
            self.write("".ljust(2*(level+1)) + "}")
        else:
            self.write("".ljust(2*(level+1)) + "No methods")

        if isinstance(arr["properties"], dict) > 0:
            self.write("".ljust(2*(level+1)) + "%d properties {" % len(arr["properties"].keys()))
            for key in sorted(arr["properties"].keys()):
                item = arr["properties"][key]
                self.writeValue(item, level+2, "%s = " % key)
            self.write("".ljust(2*(level+1)) + "}")
        else:
            self.write("".ljust(2*(level+1)) + "No properties")
        self.write("".ljust(2*level) + "}")

    def writeArrayValues(self, arr, level, firstLine):
        self.write("".ljust(2*level) + firstLine)
        startLine = len(self.buffer)
        for item in arr:
            self.writeValue(item, level + 1, "")
        self.write("".ljust(2*level) + "},")
        endLine = len(self.buffer)

    def writeDictValues(self, arr, level, firstLine):
        self.write("".ljust(2*level) + firstLine)
        startLine = len(self.buffer)
        for item in arr.keys():
            self.writeValue(arr[item], level + 1, '"%s" => ' % item )
        self.write("".ljust(2*level) + "},")
        endLine = len(self.buffer)

# User interface controls
class DBGPDebuggerUI:
    active = False
    filename = ""

    # Window panes for the debugger
    tracewin = None  # Main code window
    stackwin = None  # Stack trace window
    watchwin = None  # Watch window
    helpwin = None   # Help text window

    nextBpMarkNum = 501
    bpList = {}

    debugTab = None
    origTab = None

    filename = ""
    line = 0
    def __init__(self):
        """ set vim highlight of debugger sign """
        vim.command("highlight DbgCurrent term=reverse ctermfg=White ctermbg=Red gui=reverse")
        vim.command("highlight DbgBreakPt term=reverse ctermfg=White ctermbg=Green gui=reverse")

        self.watchwin = WatchWindow(self)
        self.stackwin = StackWindow(self)
        #self.tracewin = TraceWindow(self)

    def activate(self):
        self.origTab = vim.eval("tabpagenr()")
        vim.command("tabnew") # create new tab for the debugger
        self.debugTab = vim.eval("tabpagenr()")

        self.watchwin.create("vertical belowright new")
        self.stackwin.create("belowright new")
        #self.tracewin.create("belowright new")

        self.active = True

    def deactivate(self):
        if self.active:
            self.gotoWorkingTab()

            self.watchwin.destroy()
            self.stackwin.destroy()
            #self.tracewin.destroy()

            vim.command("tabclose")
            vim.command("tabn %s" % self.origTab)
            vim.command("sign unplace 500")
            self.active = False

    def gotoWorkingTab(self):
        if vim.eval('tabpagenr()') != self.debugTab:
            vim.command('tabn ' + self.debugTab)
    def gotoSourceWindow(self):
        vim.command("1wincmd w")

    def setSign(self, filename, line, depth = 0):
        self.gotoWorkingTab()
        self.gotoSourceWindow()
        name = "_dbg_"
        if depth == 0:
            name += "current"
        else:
            name += "stack"
        if filename != self.filename:
            vim.command("silent edit %s" % filename)
            self.filename = filename
        vim.command("silent! sign unplace 500")
        vim.command('sign place 500 name=%s line=%s file=%s' % (name, line, filename))

    def gotoSign(self, filename, line, depth = 0):
        self.gotoWorkingTab()
        self.gotoSourceWindow()
        self.setSign(filename, line, depth)
        vim.command('sign jump 500 file=%s' % filename)

    def setStackList(self, stackList):
        vim.command("silent! sign unplace 500")
        maxLen = {}
        for frame in stackList:
            filename = frame.filename
            frame.localFileURI = urllib.unquote(filename).replace("file://", "")
            # if this is Windows, remove the initial '/' if needed
            if (os.name.lower() == 'nt' or os.name.lower() == "win" or os.name.lower() == "windows") and filename[0] == "/":
                frame.localFileURI = filename[1:]
            (frame.localPathName, frame.localFileName) = os.path.split(frame.localFileURI)
            frame.localFileName = "%s:%d" % (frame.localFileName, frame.lineno)
            if not maxLen.has_key("file") or maxLen["file"] < len(frame.localFileName):
                maxLen["file"] = len(frame.localFileName)
            if not maxLen.has_key("path") or maxLen["path"] < len(frame.localPathName):
                maxLen["path"] = len(frame.localPathName)
            if not maxLen.has_key("where") or maxLen["where"] < len(frame.where):
                maxLen["where"] = len(frame.where)
            self.setSign(frame.localFileURI, frame.lineno, frame.depth)

        self.stackwin.setStack(stackList)
        self.setFrame(stackList[0])

    def setFrame(self, frame):
        self.stackwin.highlight_stack(frame.depth)

        filename = urllib.unquote(frame.filename).replace("file://", "")
        if (os.name.lower() == 'nt' or os.name.lower() == "win" or os.name.lower() == "windows") and filename[0] == "/":
            filename = filename[1:]

        self.gotoSign(filename, frame.lineno, frame.depth)

    def setProperties(self, plist1, plist2, vlist):
        self.watchwin.setPropertyList(plist1, plist2, vlist)
        self.gotoSourceWindow()

    def markBreakpoint(self, file, line, guid):
        bpNo = self.nextBpMarkNum
        self.nextBpMarkNum = bpNo + 1
        self.bpList[guid] = bpNo
        vim.command("sign place %s name=_dbg_breakpt line=%s file=%s" % (bpNo, line, file))

    def unmarkBreakpoint(self, guid):
        bpNo = self.bpList[guid]
        vim.command("sign unplace %s" % bpNo)

    def removeBreakpoints(self):
        for guid, sign in self.bpList.items():
            vim.command("silent! sign unplace %s" % sign)
        self.bpList = {}

    def trace(self, text):
        pass
        #self.tracewin.write(text)

    def _watchLineEnter(self):
        self.watchwin.lineEnter();

class DBGPDebuggerWrapper:
    debugger = None
    ui = None
    lineBreakpointList = {}
    depth = 0
    watchList = []
    watchEvalList = []

    def __init__(self):
        self.debugger = VimDebugger()
        self.ui = DBGPDebuggerUI()

    def activateUI(self):
        self.ui.activate()

    def deactivateUI(self):
        self.ui.deactivate()

    def start_debugger(self):
        try:
            self.debugger.stop()
        except:
            pass
        vim.command("echo 'Waiting for connection...'")
        connected = self.debugger.listenWait("localhost", 9000)
        if connected:
            self.activateUI()
            self.stepInto()
            self.checkPosition()

    def selectStackDepth(self):
        line = vim.current.line.strip()
        if line[0] == "#":
            return

        self.depth = int(line.split(" ")[0])
        self.ui.setFrame(self.debugger.session.stackGet(self.depth))

    def stop_debugger(self):
        try:
            self.debugger.shutdown()
        except:
            print "Couldn't stop debugger"
        self.deactivateUI()

    def detach(self):
        if not self.debugger.isConnected():
            return False

        try:
            self.debugger.session.detach()
        except:
            pass
        self.stop_debugger()

    def stop(self):
        if not self.debugger.isConnected():
            return False

        try:
            self.debugger.session.stop()
        except:
            pass
        self.stop_debugger()

    def run(self):
        if not self.debugger.isConnected():
            self.start_debugger()
        else:
            run = self.debugger.session.resumeWait(RESUME_GO)
            status = self.debugger.session.statusName
            if status == "break":
                self.checkPosition()
                self.updateWatch()
            elif status == "stopping":
                self.detach()
            else:
                print "new status: %s" % run.attributes["status"].value

    def stepInto(self):
        return self.step(RESUME_STEP_IN)

    def stepOver(self):
        return self.step(RESUME_STEP_OVER)

    def stepOut(self):
        return self.step(RESUME_STEP_OUT)

    def step(self, stype):
        if not self.debugger.isConnected():
            self.start_debugger()

        step = self.debugger.session.resumeWait(stype)
        self.checkPosition()

    def checkPosition(self):
        stackList = self.debugger.session.stackFramesGet()
        self.ui.setStackList(stackList)

    def _hasLineBreakpoint(self, file, line):
        bpId = "%s:%s" % (file, line)
        return self.lineBreakpointList.has_key(bpId)

    def _getLineBreakpoint(self, file, line):
        bpId = "%s:%s" % (file, line)
        return self.lineBreakpointList[bpId]

    def _removeLineBreakpoint(self, file, line):
        bpId = "%s:%s" % (file, line)
        del self.lineBreakpointList[bpId]

    def _storeLineBreakpoint(self, file, line, guid):
        bpId = "%s:%s" % (file, line)
        self.lineBreakpointList[bpId] = guid

    def toggleLineBreakpointHere(self):
        mgr = self.debugger.breakpointManager
        line = vim.current.window.cursor[0]
        file = urllib.quote(vim.eval('expand("%:p")'))
        fileuri = "file://%s" % file
        if not self._hasLineBreakpoint(file, line):
            guid = mgr.addBreakpointLine("PHP", fileuri, line, "enabled")
            self._storeLineBreakpoint(file, line, guid)
            self.ui.markBreakpoint(file, line, guid)
        else:
            guid = self._getLineBreakpoint(file, line)
            self._removeLineBreakpoint(file, line)
            mgr.removeBreakpoint(guid)
            self.ui.unmarkBreakpoint(guid)

    def removeAllBreakpoints(self):
        mgr = self.debugger.breakpointManager
        mgr.removeAllBreakpoints()
        self.ui.removeBreakpoints()
        self.lineBreakpointList = {}

    def getDefWatchList(self):
        ctx = self.debugger.session.contextGet(0, self.depth)
        plist = []
        for property in ctx:
            plist.append("$%s" % property.name )
        return plist

    def updateWatch(self):
        localList = self.getDefWatchList()
        resp = []
        resp.append(self.debugger.phpWatch(localList))
        watchVals = []
        for item in self.watchList:
            watchVals.append(self.debugger.phpEval(item))
        resp.append(watchVals)

        self.ui.setProperties(localList, self.watchList, resp)

    def addWatchExpr(self, expr):
        if len(expr) > 1:
            self.watchList.append(expr)

global __debugger
__debugger = DBGPDebuggerWrapper()
EOF
  endfunction
  call DefPython()
endif
