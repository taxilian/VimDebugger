#!/usr/bin/env python
# Copyright (c) 2010 Richard Bateman
#
# The MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#
# NOTE: This software makes use of other libraries, which are inlined in the
# code.  These libraries are included with their original copyright and
# license notice.
#
#
# Authors:
#    Richard Bateman <taxilian@gmail.com>



# simplejson decoder:
#Copyright (c) 2006 Bob Ippolito

#Permission is hereby granted, free of charge, to any person obtaining a copy of
#this software and associated documentation files (the "Software"), to deal in
#the Software without restriction, including without limitation the rights to
#use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
#of the Software, and to permit persons to whom the Software is furnished to do
#so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.

"""Implementation of JSONDecoder
"""
import re
import sys
import struct

import re
__all__ = ['make_scanner']

NUMBER_RE = re.compile(
    r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?',
    (re.VERBOSE | re.MULTILINE | re.DOTALL))

def py_make_scanner(context):
    parse_object = context.parse_object
    parse_array = context.parse_array
    parse_string = context.parse_string
    match_number = NUMBER_RE.match
    encoding = context.encoding
    strict = context.strict
    parse_float = context.parse_float
    parse_int = context.parse_int
    parse_constant = context.parse_constant
    object_hook = context.object_hook
    object_pairs_hook = context.object_pairs_hook
    memo = context.memo

    def _scan_once(string, idx):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration

        if nextchar == '"':
            return parse_string(string, idx + 1, encoding, strict)
        elif nextchar == '{':
            return parse_object((string, idx + 1), encoding, strict,
                _scan_once, object_hook, object_pairs_hook, memo)
        elif nextchar == '[':
            return parse_array((string, idx + 1), _scan_once)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5

        m = match_number(string, idx)
        if m is not None:
            integer, frac, exp = m.groups()
            if frac or exp:
                res = parse_float(integer + (frac or '') + (exp or ''))
            else:
                res = parse_int(integer)
            return res, m.end()
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return parse_constant('-Infinity'), idx + 9
        else:
            raise StopIteration

    def scan_once(string, idx):
        try:
            return _scan_once(string, idx)
        finally:
            memo.clear()

    return scan_once

make_scanner = py_make_scanner

__all__ = ['JSONDecoder']

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    _BYTES = '7FF80000000000007FF0000000000000'.decode('hex')
    # The struct module in Python 2.4 would get frexp() out of range here
    # when an endian is specified in the format string. Fixed in Python 2.5+
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()


class JSONDecodeError(ValueError):
    """Subclass of ValueError with the following additional properties:

    msg: The unformatted error message
    doc: The JSON document being parsed
    pos: The start index of doc where parsing failed
    end: The end index of doc where parsing failed (may be None)
    lineno: The line corresponding to pos
    colno: The column corresponding to pos
    endlineno: The line corresponding to end (may be None)
    endcolno: The column corresponding to end (may be None)

    """
    def __init__(self, msg, doc, pos, end=None):
        ValueError.__init__(self, errmsg(msg, doc, pos, end=end))
        self.msg = msg
        self.doc = doc
        self.pos = pos
        self.end = end
        self.lineno, self.colno = linecol(doc, pos)
        if end is not None:
            self.endlineno, self.endcolno = linecol(doc, end)
        else:
            self.endlineno, self.endcolno = None, None


def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno


def errmsg(msg, doc, pos, end=None):
    # Note that this function is called from _speedups
    lineno, colno = linecol(doc, pos)
    if end is None:
        #fmt = '{0}: line {1} column {2} (char {3})'
        #return fmt.format(msg, lineno, colno, pos)
        fmt = '%s: line %d column %d (char %d)'
        return fmt % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    #fmt = '{0}: line {1} column {2} - line {3} column {4} (char {5} - {6})'
    #return fmt.format(msg, lineno, colno, endlineno, endcolno, pos, end)
    fmt = '%s: line %d column %d - line %d column %d (char %d - %d)'
    return fmt % (msg, lineno, colno, endlineno, endcolno, pos, end)


_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
}

STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
    '"': u'"', '\\': u'\\', '/': u'/',
    'b': u'\b', 'f': u'\f', 'n': u'\n', 'r': u'\r', 't': u'\t',
}

DEFAULT_ENCODING = "utf-8"

def py_scanstring(s, end, encoding=None, strict=True,
        _b=BACKSLASH, _m=STRINGCHUNK.match):
    """Scan the string s for a JSON string. End is the index of the
    character in s after the quote that started the JSON string.
    Unescapes all valid JSON string escape sequences and raises ValueError
    on attempt to decode an invalid string. If strict is False then literal
    control characters are allowed in the string.

    Returns a tuple of the decoded string and the index of the character in s
    after the end quote."""
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise JSONDecodeError(
                "Unterminated string starting at", s, begin)
        end = chunk.end()
        content, terminator = chunk.groups()
        # Content is contains zero or more unescaped string characters
        if content:
            if not isinstance(content, unicode):
                content = unicode(content, encoding)
            _append(content)
        # Terminator is the end of string, a literal control character,
        # or a backslash denoting that an escape sequence follows
        if terminator == '"':
            break
        elif terminator != '\\':
            if strict:
                msg = "Invalid control character %r at" % (terminator,)
                #msg = "Invalid control character {0!r} at".format(terminator)
                raise JSONDecodeError(msg, s, end)
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise JSONDecodeError(
                "Unterminated string starting at", s, begin)
        # If not a unicode escape sequence, must be in the lookup table
        if esc != 'u':
            try:
                char = _b[esc]
            except KeyError:
                msg = "Invalid \\escape: " + repr(esc)
                raise JSONDecodeError(msg, s, end)
            end += 1
        else:
            # Unicode escape sequence
            esc = s[end + 1:end + 5]
            next_end = end + 5
            if len(esc) != 4:
                msg = "Invalid \\uXXXX escape"
                raise JSONDecodeError(msg, s, end)
            uni = int(esc, 16)
            # Check for surrogate pair on UCS-4 systems
            if 0xd800 <= uni <= 0xdbff and sys.maxunicode > 65535:
                msg = "Invalid \\uXXXX\\uXXXX surrogate pair"
                if not s[end + 5:end + 7] == '\\u':
                    raise JSONDecodeError(msg, s, end)
                esc2 = s[end + 7:end + 11]
                if len(esc2) != 4:
                    raise JSONDecodeError(msg, s, end)
                uni2 = int(esc2, 16)
                uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))
                next_end += 6
            char = unichr(uni)
            end = next_end
        # Append the unescaped character
        _append(char)
    return u''.join(chunks), end


# Use speedup if available
scanstring = py_scanstring

WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)
WHITESPACE_STR = ' \t\n\r'

def JSONObject((s, end), encoding, strict, scan_once, object_hook,
        object_pairs_hook, memo=None,
        _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    # Backwards compatibility
    if memo is None:
        memo = {}
    memo_get = memo.setdefault
    pairs = []
    # Use a slice to prevent IndexError from being raised, the following
    # check will raise a more specific ValueError if the string is empty
    nextchar = s[end:end + 1]
    # Normally we expect nextchar == '"'
    if nextchar != '"':
        if nextchar in _ws:
            end = _w(s, end).end()
            nextchar = s[end:end + 1]
        # Trivial empty object
        if nextchar == '}':
            if object_pairs_hook is not None:
                result = object_pairs_hook(pairs)
                return result, end
            pairs = {}
            if object_hook is not None:
                pairs = object_hook(pairs)
            return pairs, end + 1
        elif nextchar != '"':
            raise JSONDecodeError("Expecting property name", s, end)
    end += 1
    while True:
        key, end = scanstring(s, end, encoding, strict)
        key = memo_get(key, key)

        # To skip some function call overhead we optimize the fast paths where
        # the JSON key separator is ": " or just ":".
        if s[end:end + 1] != ':':
            end = _w(s, end).end()
            if s[end:end + 1] != ':':
                raise JSONDecodeError("Expecting : delimiter", s, end)

        end += 1

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise JSONDecodeError("Expecting object", s, end)
        pairs.append((key, value))

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end = _w(s, end + 1).end()
                nextchar = s[end]
        except IndexError:
            nextchar = ''
        end += 1

        if nextchar == '}':
            break
        elif nextchar != ',':
            raise JSONDecodeError("Expecting , delimiter", s, end - 1)

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end += 1
                nextchar = s[end]
                if nextchar in _ws:
                    end = _w(s, end + 1).end()
                    nextchar = s[end]
        except IndexError:
            nextchar = ''

        end += 1
        if nextchar != '"':
            raise JSONDecodeError("Expecting property name", s, end - 1)

    if object_pairs_hook is not None:
        result = object_pairs_hook(pairs)
        return result, end
    pairs = dict(pairs)
    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end

def JSONArray((s, end), scan_once, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    values = []
    nextchar = s[end:end + 1]
    if nextchar in _ws:
        end = _w(s, end + 1).end()
        nextchar = s[end:end + 1]
    # Look-ahead for trivial empty array
    if nextchar == ']':
        return values, end + 1
    _append = values.append
    while True:
        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise JSONDecodeError("Expecting object", s, end)
        _append(value)
        nextchar = s[end:end + 1]
        if nextchar in _ws:
            end = _w(s, end + 1).end()
            nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        elif nextchar != ',':
            raise JSONDecodeError("Expecting , delimiter", s, end)

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

    return values, end

class JSONDecoder(object):
    """Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | unicode           |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.

    """

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True,
            object_pairs_hook=None):
        """
        *encoding* determines the encoding used to interpret any
        :class:`str` objects decoded by this instance (``'utf-8'`` by
        default).  It has no effect when decoding :class:`unicode` objects.

        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as :class:`unicode`.

        *object_hook*, if specified, will be called with the result of every
        JSON object decoded and its return value will be used in place of the
        given :class:`dict`.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        *object_pairs_hook* is an optional function that will be called with
        the result of any object literal decode with an ordered list of pairs.
        The return value of *object_pairs_hook* will be used instead of the
        :class:`dict`.  This feature can be used to implement custom decoders
        that rely on the order that the key and value pairs are decoded (for
        example, :func:`collections.OrderedDict` will remember the order of
        insertion). If *object_hook* is also defined, the *object_pairs_hook*
        takes priority.

        *parse_float*, if specified, will be called with the string of every
        JSON float to be decoded.  By default, this is equivalent to
        ``float(num_str)``. This can be used to use another datatype or parser
        for JSON floats (e.g. :class:`decimal.Decimal`).

        *parse_int*, if specified, will be called with the string of every
        JSON int to be decoded.  By default, this is equivalent to
        ``int(num_str)``.  This can be used to use another datatype or parser
        for JSON integers (e.g. :class:`float`).

        *parse_constant*, if specified, will be called with one of the
        following strings: ``'-Infinity'``, ``'Infinity'``, ``'NaN'``.  This
        can be used to raise an exception if invalid JSON numbers are
        encountered.

        *strict* controls the parser's behavior when it encounters an
        invalid control character in a string. The default setting of
        ``True`` means that unescaped control characters are parse errors, if
        ``False`` then control characters will be allowed in strings.

        """
        self.encoding = encoding
        self.object_hook = object_hook
        self.object_pairs_hook = object_pairs_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.parse_constant = parse_constant or _CONSTANTS.__getitem__
        self.strict = strict
        self.parse_object = JSONObject
        self.parse_array = JSONArray
        self.parse_string = scanstring
        self.memo = {}
        self.scan_once = make_scanner(self)

    def decode(self, s, _w=WHITESPACE.match):
        """Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)

        """
        obj, end = self.raw_decode(s, idx=_w(s, 0).end())
        end = _w(s, end).end()
        if end != len(s):
            raise JSONDecodeError("Extra data", s, end, len(s))
        return obj

    def raw_decode(self, s, idx=0):
        """Decode a JSON document from ``s`` (a ``str`` or ``unicode``
        beginning with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.

        """
        try:
            obj, end = self.scan_once(s, idx)
        except StopIteration:
            raise JSONDecodeError("No JSON object could be decoded", s, idx)
        return obj, end


# Copyright (c) 2003-2006 ActiveState Software Inc.
#
# The MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#
# Authors:
#    Shane Caraveo <ShaneC@ActiveState.com>
#    Trent Mick <TrentM@ActiveState.com>

import socket, string, sys, os, re
import threading, select
import base64
from xml.dom import minidom

try:
    import logging
except ImportError:
    from dbgp import _logging as logging


import sys, os
try:
    import logging
except ImportError:
    from dbgp import _logging as logging

# insert a frame flag for ourselves.  This flag is used to drop frames from
# the stack that we wouldn't want to normally see.  See
# dbgpClient.get_stack
DBGPHide = 1
DBGPFullTraceback = 0

# hide children gets set when writing stdout.  This prevents deeper stack levels
# that stdout uses from showing up in the stack frame and causing breaks in weird
# places
DBGPHideChildren = 0

# if set allows stepping into parts of this file.
#  0 - dont allow (default)
#  1 - allow, but not the io streams
#  2 - allow plus the io streams
DBGPDebugDebugger = 0


# error codes
ERROR_OK                        = 0
ERROR_COMMAND_PARSE             = 1
ERROR_DUPLICATE_ARGS            = 2
ERROR_INVALID_ARGS              = 3
ERROR_COMMAND_NOT_SUPPORTED     = 4
ERROR_COMMAND_NOT_AVAILABLE     = 5
ERROR_FILE_ACCESS               = 100
ERROR_STREAM_REDIRECT_FAILED    = 101
ERROR_BREAKPOINT_INVALID        = 200
ERROR_BREAKPOINT_TYPE           = 201
ERROR_BREAKPOINT_INVALID_LINE   = 202
ERROR_BREAKPOINT_NOT_REACHABLE  = 203
ERROR_BREAKPOINT_STATE          = 204
ERROR_BREAKPOINT_DOES_NOT_EXIST = 205
ERROR_EVAL_FAILED               = 206
ERROR_INVALID_EXPRESSION        = 207
ERROR_PROPERTY_DOES_NOT_EXIST   = 300
ERROR_STACK_DEPTH               = 301
ERROR_CONTEXT_INVALID           = 302
ERROR_ENCODING                  = 900
ERROR_EXCEPTION                 = 998
ERROR_UNKNOWN                   = 999


DBGP_VERSION = '1.0'

MAX_CHILDREN = 10
MAX_DATA     = 2048
MAX_DEPTH    = 1
SHOW_HIDDEN  = 0


# status types
STATUS_STARTING    = 0
STATUS_STOPPING    = 1
STATUS_STOPPED     = 2
STATUS_RUNNING     = 3
STATUS_BREAK       = 4
STATUS_INTERACTIVE = 5

status_names = ['starting', 'stopping', 'stopped', 'running', 'break', 'interactive']

# status reason types
REASON_OK        = 0
REASON_ERROR     = 1
REASON_ABORTED   = 2
REASON_EXCEPTION = 3

reason_names = ['ok' , 'error', 'aborted', 'exception']

RESUME_STOP = 0 # session terminated.
RESUME_STEP_IN = 1 # step into things.
RESUME_STEP_OVER = 2 # step over current thing
RESUME_STEP_OUT = 3 # step out of current thing.
RESUME_GO = 4 # go for it.
RESUME_INTERACTIVE = 5 # go for it.

resume_command_names = ['stop', 'step_into', 'step_over', 'step_out', 'run', 'interact']

def getenv(key, default=None):
    try:
        if not hasattr(os, 'getenv'):
            # on Symbian, getenv doesn't exist! (AttributeError)
            return default
        retval = os.getenv(key)
        if retval is None:
            return default
    except KeyError:
        # on Jython, one gets an exception instead of None back
        return default
    return retval

class DBGPError(Exception):
    pass

class DBGPQuit(Exception):
    """DBGPQuit

    an exception thrown to quit debugging
    """

__log_configured = 0
def configureLogging(log, level = logging.INFO):
    global __log_configured
    if __log_configured:
        return
    __log_configured = 1

    class DBGPFormatter(logging.Formatter):
        """Logging formatter to prefix log level name to all log output
        *except* normal INFO level logs.
        """
        def format(self, record):
            s = logging.Formatter.format(self, record)
            #if record.levelno != logging.INFO:
            s = "%s: %s: %s" % (record.levelname, record.name, s)
            return s

    hdlr = logging.StreamHandler()
    fmtr = DBGPFormatter()
    hdlr.setFormatter(fmtr)
    log.addHandler(hdlr)
    log.setLevel(level)

log = logging.getLogger("dbgp.server")
#log.setLevel(logging.DEBUG)

# the host class implements commands that the host can send
# to the debugger target
class serversession:
    def __init__(self, sessionHost):
        self._socket = None
        self._clientAddr = None
        self._cmdthread = None
        self._stop = 0
        self._transaction_id = 0
        self._sessionHost = sessionHost

    def _cmdloop(self):
        # called periodicaly by the debugger while the script is
        # running.  This checks for data on the socket, responds
        # to it if any, and deals with stream IO.
        try:
            while self._socket and not self._stop:
                try:
                    #log.debug('checking for data on the socket')
                    (input, output, exceptional) = \
                            select.select([self._socket],[],[], .1)
                    if input:
                        log.debug('handling data available on socket')
                        self._handleIncoming()
                except Exception, e:
                    log.debug("session cmdloop exception: %r: %s", e, e)
                    self._socket = None
                    self._stop = 1
        finally:
            self._cmdthread = None
            if self._socket:
                self._socket.close()
                self._socket = None
        log.info("session cmdloop done")

    def start(self, socket, clientAddr):
        if not self._sessionHost.onConnect(self, socket, clientAddr):
            socket.close()
            return 0
        self._socket = socket
        self._clientAddr = clientAddr
        self._socket.settimeout(1)
        # create a new thread and initiate a debugger session
        if not self._cmdthread or not self._cmdthread.isAlive():
            self._cmdthread = threading.Thread(target = self._cmdloop)
            self._cmdthread.start()
        return 1

    def stop(self):
        if self._socket:
            self.sendCommand(['stop'])
        log.debug('received stop command')
        self._stop = 1
        self._cmdthread.join()

    def _dispatch(self, size, response):
        if size != len(response):
            raise "Data length is not correct %d != %d" % (size,len(response))
        dom = minidom.parseString(response)
        root = dom.documentElement
        packetType = root.localName
        if packetType == 'stream':
            type = root.getAttribute('type').lower()
            text = ''
            nodelist = root.childNodes
            for node in nodelist:
                if node.nodeType == node.TEXT_NODE:
                    text = text + node.data
            text = base64.decodestring(text)
            self._sessionHost.outputHandler(self, type,text)
        elif packetType == 'response':
            command = root.getAttribute('command')
            if command == 'stop' or command == 'detach':
                log.debug("command %s recieved", command)
                try:
                    self._socket.close()
                finally:
                    self._socket = None
                    self._stop = 1
            self._sessionHost.responseHandler(self, root)
        elif packetType == 'init':
            # get our init information
            self._sessionHost.initHandler(self, root)
        else:
            print root.ownerDocument.toprettyxml()

    def _handleIncoming(self):
        data = ''
        while self._socket and not self._stop:
            data = data + self._socket.recv(1024)
            log.debug("socket recv: [%s]", data)
            if not data:
                self._stop = 1
                break
            while data:
                eop = data.find('\0')
                if eop < 0:
                    break

                size = long(data[:eop])
                data = data[eop+1:] # skip \0
                sizeLeft = size - len(data) + 1
                while sizeLeft > 0:
                    newdata = self._socket.recv(sizeLeft)
                    log.debug("socket recv: [%s]", newdata)
                    data = data + newdata
                    sizeLeft = sizeLeft - len(newdata)

                response = data[:size]
                data = data[size+1:] # skip \0
                log.debug("dispatch message: %s", response)
                self._dispatch(size,response)
            if not data:
                break

    _re_escape = re.compile(r'(["\'\\])')
    def sendCommand(self, argv, data = None):
        if not self._socket:
            raise DBGPError('Socket disconnected', ERROR_EXCEPTION)
        self._transaction_id = self._transaction_id + 1

        argv += ['-i', str(self._transaction_id)]
        if data:
            argv += ['--', base64.encodestring(data).strip()]

        # if the args need quoting, it will happen here, argv2line doesn't
        # handle it all
        # cmdline = listcmd.argv2line(argv)
        escapedArgs = []
        for arg in argv:
            # we must escape any quotes in the argument
            arg = self._re_escape.sub(r'\\\1', arg)
            if ' ' in arg or '"' in arg or "'" in arg or '\\' in arg:
                arg = '"'+arg+'"'
            escapedArgs.append(str(arg))
        cmdline = ' '.join(escapedArgs)
        try:
            #print "sendCommand: %s"% cmdline
            log.debug("sendCommand: %s", cmdline)
            self._socket.sendall(cmdline+'\0')
            #log.debug("sendCommand: %s DONE", cmdline)
        except socket.error, e:
            log.error("session sendCommand socket error %r", e)
            self._stop = 1
        return self._transaction_id

# this is the host server that accepts connections
# and kicks off host threads to handle those connections
class serverlistener:
    def __init__(self, sessionHost):
        self._address = None
        self._port = None
        self._thread = None
        self._stop = 0
        self._session_host = sessionHost
        self._totalConnections = 0

    def checkListening(self):
        return self._thread and self._thread.isAlive()

    def start(self, address, port):
        # stop any existing listener
        if self.checkListening():
            if self._address == address and self._port == port:
                log.error("Host server already listening")
                return
            self.stop()

        log.info("Start listening on %s:%d.", address or "127.0.0.1", port)
        self._address = address
        self._port = port
        self._stop = 0
        # if bind raises an exception, dont start
        # the listen thread
        self._bind()
        self._thread = threading.Thread(target = self._listen)
        self._thread.start()
        return (self._address, self._port)

    def stop(self):
        if self.checkListening():
            log.debug('listener.stop attempt to close server')
            self._stop = 1
            addr = self._address
            if not addr:
                addr = '127.0.0.1'
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((addr, self._port))
                s.close()
            except socket.error, details:
                log.error("The host listener could not cancel the "+\
                      "listener %d:%r", self._port, details)
        else:
            log.debug('listener.stop was not listening')

    def _bind(self):
        try:
            self._server = socket.socket(socket.AF_INET,
                                         socket.SOCK_STREAM)

            # XXX the below setsocketopt is bad for multiuser
            # systems.  The first server instance will always get
            # all debugger sessions for the defined port.  This is
            # only an issue if the port is not set to zero in prefs

            # try to re-use a server port if possible
            # this is necessary on linux (and solaris)
            # in order to start listening AGAIN on the same
            # socket that we were listening on before, if
            # the listener was stopped.
            #self._server.setsockopt(
            #    socket.SOL_SOCKET, socket.SO_REUSEADDR,
            #    self._server.getsockopt(socket.SOL_SOCKET,
            #                            socket.SO_REUSEADDR) | 1)

            self._server.bind((self._address, self._port))
            if not self._port:
                addr = self._server.getsockname()
                self._port = addr[1]
        except socket.error, details:
            errmsg = "the debugger could not bind on port %d." % self._port
            self._port = 0
            self._server = None
            raise DBGPError(errmsg)

    def _listen(self):
        try:
            self._server.listen(5)
        except socket.error, details:
            raise DBGPError("the debugger could not start listening on port %d." % self._port)
        try:
            while not self._stop:
                (client, addr) = self._server.accept()
                if self._stop:
                    break
                log.info("server connection: %r", addr)
                self.startNewSession(client, addr)
                self._totalConnections = self._totalConnections + 1
        except socket.error, details:
            raise DBGPError("the debugger could not accept new connection.")
        log.debug('listener._listen thread shutting down')
        try:
            self._server.close()
        except socket.error, details:
            raise DBGPError("the debugger could could not be closed.")
        self._server = None
        self._stop = 0
        self._address = None
        self._port = None

    def startNewSession(self, client, addr):
        # start a new thread that is the host connection
        # for this debugger session
        sessionHost = serversession(self._session_host)
        sessionHost.start(client, addr)

# Copyright (c) 2003-2006 ActiveState Software Inc.
#
# The MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#
# Authors:
#    Shane Caraveo <ShaneC@ActiveState.com>
#    Trent Mick <TrentM@ActiveState.com>

"""DBGP Server API module.

Generally this builds upon the lower-level dbgp.serverBase module to provide
a full module interface for a DBGP server. This module interface can be
used to provide a command-line or GUI debugger interface using the DBGP
protocol.
"""

import os
import sys
import socket, string, base64, urllib
import threading
from xml.dom import minidom
import copy

try:
    import logging
except ImportError:
    from dbgp import _logging as logging

#XXX Try to avoid dependence on PyXPCOM infrastructure in this file.
try:
    from xpcom import COMException, ServerException
except ImportError:
    COMException = ServerException = None


#---- globals

log = logging.getLogger("dbgp.server")
#log.setLevel(logging.DEBUG)
proplog = logging.getLogger("dbgp.property")
#proplog.setLevel(logging.DEBUG)
bplog = logging.getLogger("dbgp.breakpoints")
#bplog.setLevel(logging.DEBUG)


#---- internal support routines

#Note: this is not prefixed with "_" because it is being used in koDBGP.py.
def getErrorInfo(ex):
    """Given a DBGPError exception return (errno, errmsg).

    This is a separate method because (1) the assignment of args to DBGPError
    is not consistent and (2) the exception may also be an XPCOM COMException,
    in which case error info is expected to be on koILastErrorService.
    """
    if isinstance(ex, DBGPError):
        #XXX _Try_ to get the error message out of the DBGPError. There
        #   is no good standard for DBGPError args right now though,
        #   hence the pain here.
        if len(ex.args) == 2: # typically this is (errmsg, errno)
            errmsg = ex.args[0]
            try:
                errno = int(ex.args[1]) # sometimes this is a string
            except ValueError:
                errno = 0
        else:
            errmsg = ex.args[0]
            errno = 0
    elif isinstance(ex, COMException):
        from xpcom import components
        lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"].\
                       getService(components.interfaces.koILastErrorService)
        errno, errmsg = lastErrorSvc.getLastError()    
    return (errno, errmsg)


#---- DBGP server class hierarchy

class dataType:
    def __init__(self):
        self.commonType = '';
        self.languageType = '';
        self.schemaType = '';

    def initWithNode(self, node):
        self.commonType = node.getAttribute('type')
        self.languageType = node.getAttribute('name')
        if node.hasAttribute('xsi:type'):
            self.schemaType = node.getAttribute('xsi:type')

    def __repr__(self):
        return "%s:%s:%s" % (self.commonType, self.languageType, self.schemaType)


class breakpoint:
    """A DBGP Breakpoint.

    Mostly this is a "dumb" object that just holds the relevant breakpoint
    attributes. It knows how to update and clone itself, but not much more.
    """
    # List of data attributes relevant for persistence and updating.
    # Note: This last must be kept in sync with the DBGP breakpoint spec.
    _attrs = ["language", "type", "filename", "lineno", "functionName",
              "state", "hitCount", "hitValue", "hitCondition", "temporary",
              "exceptionName", "expression"]

    def __init__(self):
        # Core breakpoint attributes. These should only be modified either
        #   (1) by initializing via one of the .init*() methods; or
        #   (2) via the breakpointManager.
        self.language = ''
        self.type = ''
        self.filename = ''
        self.lineno = -1
        self.functionName = ''
        self.state = 'enabled'
        self.exceptionName = ''
        self.expression = ''
        self.temporary = 0
        self.hitCount = 0
        self.hitValue = 0
        self.hitCondition = None

        # A unique breakpoint id (a number) that is assigned and controlled
        # by the breakpointManager.
        # Note: This is not just called "id" to avoid confusion with the
        #       breakpoint id's assigned by each session.
        # Note: While called a "guid", this is NOT one of those long COM
        #       GUID strings, e.g. {5F7CB810-0AC8-4BBD-B8C1-8470E516EDBC}.
        self._guid = None

        # the breakpoint id as set by the debugger engine
        self._bpid = None

    def getGuid(self):
        return self._guid

    def clone(self):
        """Return a copy of this breakpoint.

        This is required for proper updating of a breakpoint via
        breakpointUpdate.
        """
        return copy.copy(self)

    def update(self, bp):
        """Update with the given breakpoint data and return a list of
        changed attributes.
        """
        attrNames = []
        for attrName in self._attrs:
            try:
                oldValue = getattr(self, attrName)
            except Exception, ex:
                log.error("failed to get old value of '%s' attribute: %s",
                          attrName, ex)
                raise
            try:
                newValue = getattr(bp, attrName)
            except Exception, ex:
                log.error("failed to get new value of '%s' attribute: %s",
                          attrName, ex)
                raise
            if newValue != oldValue:
                attrNames.append(attrName)
                try:
                    setattr(self, attrName, newValue)
                except Exception, ex:
                    log.error("update of '%s' attribute to '%s' failed: %s",
                              attrName, newValue, ex)
                    raise
        return attrNames

    def getName(self):
        if self.type == "line":
            name = "%s, line %s" % (os.path.basename(self.filename), self.lineno)
        elif self.type in ["conditional", "watch"]:
            name = "'%s' watched" % self.expression
            if self.filename:
                name += " in %s" % os.path.basename(self.filename)
            if self.lineno >= 1:
                name += ", line %s" % self.lineno
        elif self.type in ["call", "return"]:
            name = "%s %s" % (self.functionName, self.type)
            if self.filename:
                name += " in %s" % os.path.basename(self.filename)
        elif self.type == "exception":
            name = "Exception %s" % self.exceptionName
            if self.filename:
                name += " in %s" % os.path.basename(self.filename)
        else:
            log.error("unknown breakpoint type: '%s'" % self.type)
            name = "???"
        return name

    #---- Breakpoint initialization methods.
    def initConditional(self, lang, cond, file, line, state, temporary=None,
                        hitValue=None, hitCondition=None):
        self.language = lang
        self.type = 'conditional'
        self.filename = file
        self.lineno = line
        self.state = state
        self.expression = cond
        self.temporary = temporary
        self.hitValue = hitValue
        self.hitCondition = hitCondition

    def initWatch(self, lang, watch, file, line, state, temporary=None,
                        hitValue=None, hitCondition=None):
        self.language = lang
        self.type = 'watch'
        self.filename = file
        self.lineno = line
        self.state = state
        self.expression = watch
        self.temporary = temporary
        self.hitValue = hitValue
        self.hitCondition = hitCondition

    def initLine(self, lang, file, line, state, temporary=None,
                 hitValue=None, hitCondition=None):
        self.language = lang
        self.type = 'line'
        self.filename = file
        self.lineno = line
        self.state = state
        self.temporary = temporary
        self.hitValue = hitValue
        self.hitCondition = hitCondition

    def initException(self, lang, exceptionName, state, temporary=None,
                      hitValue=None, hitCondition=None):
        self.language = lang
        self.type = 'exception'
        self.state = state
        self.exceptionName = exceptionName
        self.temporary = temporary
        self.hitValue = hitValue
        self.hitCondition = hitCondition

    def initCall(self, lang, func, filename, state, temporary=None,
                 hitValue=None, hitCondition=None):
        self.language = lang
        self.type = 'call'
        self.filename = filename
        self.functionName = func
        self.state = state
        self.temporary = temporary
        self.hitValue = hitValue
        self.hitCondition = hitCondition

    def initReturn(self, lang, func, filename, state, temporary=None,
                   hitValue=None, hitCondition=None):
        self.language = lang
        self.type = 'return'
        self.filename = filename
        self.functionName = func
        self.state = state
        self.temporary = temporary
        self.hitValue = hitValue
        self.hitCondition = hitCondition

    def initWithNode(self, node):
        # id="%d" type="%s" filename="%s" lineno="%d" function="%s"
        # state="%s" exception="%s"
        # expression is a child element with name of expression
        self.type = node.getAttribute('type')
        if node.hasAttribute('id'):
            self._bpid = node.getAttribute('id')
        if node.hasAttribute('filename'):
            self.filename = urllib.unquote_plus(node.getAttribute('filename'))
        if node.hasAttribute('lineno'):
            self.lineno = int(node.getAttribute('lineno'))
        if node.hasAttribute('function'):
            self.functionName = node.getAttribute('function')
        if node.hasAttribute('state'):
            self.state = node.getAttribute('state')
        if node.hasAttribute('exception'):
            self.exceptionName = node.getAttribute('exception')
        if node.hasAttribute('temporary'):
            self.temporary = int(node.getAttribute('temporary'))
        if node.hasAttribute('hit_count'):
            self.hitCount = int(node.getAttribute('hit_count'))
        if node.hasAttribute('hit_value'):
            self.hitValue = int(node.getAttribute('hit_value'))
        if node.hasAttribute('hit_condition'):
            self.hitCondition = int(node.getAttribute('hit_condition'))
        if self.type == 'expression':
            try:
                self.expression = base64.decodestring(node.firstChild.firstChild.nodeValue)
            except:
                self.expression = node.firstChild.firstChild.nodeValue

    def __repr__(self):
        data = ("type:%(type)s filename:%(filename)s "
                "lineno:%(lineno)s function:%(functionName)s state:%(state)s "
                "exception:%(exceptionName)s expression:%(expression)s "
                "temporary:%(temporary)s hit_count:%(hitCount)s "
                "hit_value:%(hitValue)s hit_condition:%(hitCondition)s"
                % self.__dict__)
        return "<%s: %s>" % (self.__class__, data)

    def getSetArgs(self):
        """Return a list of options for a 'breakpoint_set' command."""
        args = ['-t', self.type]
        data = None

        if self.filename:
            filename = self.filename
            if filename[8:].startswith('file:/'):
                filename = self.filename[8:]
            args += ['-f', filename]
        if self.type == 'line':
            args += ['-n', self.lineno]
        elif self.type in ['call', 'return']:
            args += ['-m', self.functionName]
        elif self.type == 'exception':
            args += ['-x', self.exceptionName]
        elif self.type in ['conditional', 'watch']:
            if self.lineno:
                args += ['-n', self.lineno]
            data = self.expression
        else:
            raise DBGPError('breakpoint type [%s] not supported' % self.type)

        if self.state:
            args += ['-s', self.state]
        # Add common optional arguments, if necessary.
        args += ['-r', int(self.temporary)]
        if self.hitValue is not None:
            args += ['-h', self.hitValue]
        if self.hitCondition:
            args += ['-o', self.hitCondition]

        args = [str(i) for i in args] # Return a stringified command version.
        return (args, data)


class spawnpoint(breakpoint):
    """A DBGP Spawnpoint.

    XXX Inheriting from koIDBGPBreakpoint is messy (because it is not a
        a proper superset). Should find a common base and use that.
    """
    # List of data attributes relevant for persistence and updating.
    # Note: This last must be kept in sync with the DBGP spawnpoint spec.
    _attrs = ["language", "type", "filename", "lineno", "state"]

    def init(self, lang, filename, line, state):
        self.language = lang
        self.type = 'spawn'
        self.filename = filename
        self.lineno = line
        self.state = state

    def getName(self):
        name = "%s, line %s" % (os.path.basename(self.filename), self.lineno)
        return name

    def __repr__(self):
        data = ("type:%(type)s filename:%(filename)s "
                "lineno:%(lineno)s state:%(state)s "
                % self.__dict__)
        return "<%s: %s>" % (self.__class__, data)

    def getSetArgs(self):
        """Return a list of options for a 'spawnpoint_set' command."""
        # tcl doesn't do any magic for us, we must be explicit
        filename = self.filename
        if filename[8:].startswith('file:/'):
            filename = self.filename[8:]
        args = ['-s', self.state,
                '-n', self.lineno,
                '-f', self.filename]
        args = [str(i) for i in args] # Return a stringified command version.
        return (args, None)


class contextType:
    def __init__(self):
        self.id = -1
        self.name = ''

    def initWithNode(self, node):
        # name="Local" id="0"
        if node.hasAttribute('id'):
            self.id = int(node.getAttribute('id'))
        self.name = node.getAttribute('name')

    def __repr__(self):
        return "%d: %s" %(self.id, self.name)


class stackFrame:
    def __init__(self):
        self.depth = -1
        self.filename = ''
        self.lineno = -1
        self.type = ''
        self.where = ''
        self.beginLine = 0
        self.beginOffset = 0
        self.endLine = 0
        self.endOffset = 0
        self.inputFrame = None

    def initWithNode(self, node):
        # level="%d" type="%s" filename="%s" lineno="%d" where="%s"
        if node.hasAttribute('level'):
            self.depth = int(node.getAttribute('level'))
        if node.hasAttribute('filename'):
            self.filename = urllib.unquote_plus(node.getAttribute('filename'))
        if node.hasAttribute('lineno'):
            self.lineno = int(node.getAttribute('lineno'))
        if node.hasAttribute('type'):
            self.type = node.getAttribute('type')
        if node.hasAttribute('where'):
            self.where = node.getAttribute('where')
        if node.hasAttribute('cmdbegin'):
            begin = node.getAttribute('cmdbegin')
            try:
                (self.beginLine, self.beginOffset) = begin.split(':')
            except:
                # if the attribute is invalid, ignore it
                log.warn('stack cmdbegin attribute is incorrect [%s]', begin)
        if node.hasAttribute('cmdend'):
            end = node.getAttribute('cmdend')
            try:
                (self.endLine, self.endOffset) = end.split(':')
            except:
                # if the attribute is invalid, ignore it
                log.warn('stack cmdend attribute is incorrect [%s]', end)
        input = node.getElementsByTagName('input')
        if len(input) > 0:
            # XXX more than one input frame?
            self.inputFrame = stackFrame()
            self.inputFrame.initWithNode(input[0])

    def __repr__(self):
        return "frame: %d %s(%d) %s %s" % \
            (self.depth, self.filename, self.lineno, self.type, self.where)


class property:
    def __init__(self):
        self.name = ''
        self.id = ''
        self.fullname = ''
        self.type = ''
        self.typeName = ''
        self.typeScheme = ''
        self.classname = ''
        self.facets = ''
        self.size = 0
        self.children = 0
        self.numchildren = 0
        self.address = 0
        self.recursive = 0
        self.encoding = ''
        self.key = ''
        self.value = ''
        self.node = None
        self.childProperties = []
        self.session = None
        self.contextId = 0
        self.depth = 0

    def _getCData(self, node):
        value = ''
        encoding = ''
        if node.hasAttribute('encoding'):
            encoding = node.getAttribute('encoding')
        for child in node.childNodes:
            if child.nodeType in [minidom.Node.TEXT_NODE,
                                  minidom.Node.CDATA_SECTION_NODE]:
                value = value + child.nodeValue
        try:
            if value and (self.encoding == 'base64' or encoding == 'base64'):
                value = base64.decodestring(value)
        except:
            pass
        return value

    def initWithNode(self, session, node, context = 0, depth = 0):
        self.session = session
        # name="%s" fullname="%s" type="%s" children="%d" size="%d"
        # if children:
        #   page="%d" pagesize="%d" numchildren="%d"
        # if string type:
        #   encoding="%s"
        self.contextId = context
        self.depth = depth
        if node.hasAttribute('name'):
            self.name = node.getAttribute('name')
        if node.hasAttribute('fullname'):
            self.fullname = node.getAttribute('fullname')
        if node.hasAttribute('classname'):
            self.classname = node.getAttribute('classname')
        if node.hasAttribute('encoding'):
            self.encoding = node.getAttribute('encoding')
        proplog.debug("property encoding is %s", self.encoding)
        for child in node.childNodes:
            if child.nodeType == minidom.Node.ELEMENT_NODE and \
                   child.tagName == 'name':
                self.name = self._getCData(child)
            elif child.nodeType == minidom.Node.ELEMENT_NODE and \
                   child.tagName == 'fullname':
                self.fullname = self._getCData(child)
            elif child.nodeType == minidom.Node.ELEMENT_NODE and \
                   child.tagName == 'classname':
                self.classname = self._getCData(child)
            elif child.nodeType == minidom.Node.ELEMENT_NODE and \
                   child.tagName == 'value':
                self.value = self._getCData(child)

        self.type = node.getAttribute('type')
        if session and self.type in session._typeMap:
            self.typeName = session._typeMap[self.type].commonType
            self.typeScheme = session._typeMap[self.type].schemaType
        else:
            self.typeName = self.type

        if node.hasAttribute('size'):
            self.size = int(node.getAttribute('size'))
        if node.hasAttribute('children'):
            self.children = int(node.getAttribute('children'))
        if self.children:
            self.numchildren = 0
            page = 0
            pagesize = 0
            if node.hasAttribute('page'):
                page = int(node.getAttribute('page'))
            if node.hasAttribute('pagesize'):
                pagesize = int(node.getAttribute('pagesize'))
            if node.hasAttribute('numchildren'):
                self.numchildren = int(node.getAttribute('numchildren'))
            index = page * pagesize
            for child in node.childNodes:
                if child.nodeType == minidom.Node.ELEMENT_NODE and \
                   child.tagName == 'property':
                    p = property()
                    p.initWithNode(self.session, child, self.contextId, self.depth)
                    self.childProperties.insert(index, p)
                    index = index + 1
        if node.hasAttribute('key'):
            self.key = node.getAttribute('key')
        if node.hasAttribute('address'):
            self.address = node.getAttribute('address')
        # we may have more than one text node, get them all
        if not self.value:
            self.value = self._getCData(node)
        self.node = node

    def __repr__(self):
        return "name: %s type: %s value: %s" % \
                    (self.name, self.type, self.value)

    #void getChildren(in long page,
    #                [array, size_is(count)] out koIDBGPProperty properties,
    #                out PRUint32 count);
    def getChildren(self, page):
        pagesize = self.session.maxChildren
        start = page * pagesize
        end = start + pagesize
        if end >= self.numchildren:
            end = self.numchildren
        proplog.debug("getChildren num %d start %r end %r have %r",
                      self.numchildren, start, end, len(self.childProperties)) 
        if end > len(self.childProperties):
            proplog.debug("getChildren getting children")
            p = self.session.propertyGetEx(self.contextId,
                                                  self.depth,
                                                  self.fullname,
                                                  0,
                                                  '',
                                                  page)
            # property is a duplicate of self.  we need to copy it's
            # children into ours
            s = p.childProperties
            s.reverse()
            index = start
            while s:
                self.childProperties.insert(index, s.pop())
                index = index + 1
        proplog.debug("getChildren returning %d children", len(self.childProperties[start:end]))
        return self.childProperties[start:end]

    def getChildrenNextPage(self):
        if len(self.childProperties) >= self.numchildren:
            return None
        import math
        page = long(math.floor(len(self.childProperties) / self.session.maxChildren))
        return self.getChildren(page)

    def getAvailableChildren(self):
        return self.childProperties

    #void getAllChildren([array, size_is(count)] out koIDBGPProperty properties,
    #                out PRUint32 count);
    def getAllChildren(self):
        page = 0
        # self.childProperties = []
        while len(self.childProperties) < self.numchildren:
            #proplog.debug("getAllChildren getPage %d", page)
            if not self.getChildren(page):
                break
            page = page + 1
        return self.childProperties

    def setValue(self, value, type):
        prop = self.session.propertyUpdate(self, value, type)
        if prop:
            self.type = prop.type
            self.typeName = prop.typeName
            self.typeScheme = prop.typeScheme
            self.classname = prop.classname
            self.facets = prop.facets
            self.size = prop.size
            self.children = prop.children
            self.numchildren = prop.numchildren
            self.address = prop.address
            self.recursive = prop.recursive
            self.encoding = prop.encoding
            self.key = prop.key
            self.value = prop.value
            self.node = prop.node
            self.childProperties = prop.childProperties
            self.contextId = prop.contextId
            self.depth = prop.depth

    def getValue(self):
        if self.size > len(self.value):
            self.value = self.session.propertyValueEx(self.contextId, self.depth, self.fullname)
        return self.value


class session(serversession):
    def __init__(self, sessionHost):
        serversession.__init__(self, sessionHost)

        # setup some event vars
        self._resp_cv = threading.Condition()
        self._responses = {}
        self.statusName = 'stopped'
        self.reason = 'ok'
        self.applicationId = None
        self.threadId = None
        self.parentId = None
        self.hostname = ""
        self._application = None

        self._features = {}
        self._supportedCommands = {}
        self._typeMap = {}

        self.supportsAsync = 0
        self.supportsHiddenVars = 0
        self.supportsPostmortem = 0
        self._resume = 0

        self.languageName = ''
        self.languageVersion = ''
        self.maxChildren = 0

        self.interactivePrompt = ''
        self.interactiveState = 0

    def _dispatch(self, size,response):
        # THREAD WARNING
        # this function is called from the command loop thread.  Do
        # not do anything here that will result in another command
        # being sent to the client, that will result in a lockup
        if size != len(response):
            raise DBGPError("Data length is not correct %d != %d" % (size,len(response)))
        #log.debug(response)
        dom = minidom.parseString(response)
        root = dom.documentElement
        packetType = root.localName
        if packetType == 'stream':
            type = root.getAttribute('type').lower()
            text = ''
            nodelist = root.childNodes
            for node in nodelist:
                if node.nodeType == node.TEXT_NODE:
                    text = text + node.data
            text = base64.decodestring(text)
            self._application.outputHandler(type, text)
        elif packetType == 'response':
            command = root.getAttribute('command')
            self._responseHandler(root)
            if command in ['stop','detach']:
                if command == 'stop':
                    self._application.shutdown()
                else:
                    self._application.releaseSession(self)
                try:
                    self._socket.close()
                finally:
                    self._socket = None
                    self._stop = 1

            if command in ['run', 'step_into', 'step_over',
                           'step_out', 'stop', 'detach', 'interact']:

                # any response command can initiate an interactive prompt
                # if it includes the prompt and more attributes
                if root.hasAttribute('more') and root.hasAttribute('prompt'):
                    self.interactiveState = int(root.getAttribute('more'))
                    self.interactivePrompt = root.getAttribute('prompt')
                else:
                    self.interactivePrompt = ''
                    self.interactiveState = 0

                self._resume = 0
                # XXX notify state change now
                self.stateChange(root)
                return

        elif packetType == 'notify':
            name = root.getAttribute('name').lower()
            text = ''
            encoding = None
            nodelist = root.childNodes
            for node in nodelist:
                if node.nodeType == node.TEXT_NODE:
                    text = text + node.data
            if root.hasAttribute('encoding'):
                encoding = node.getAttribute('encoding')
            try:
                if text and encoding == 'base64':
                    text = base64.decodestring(text)
            except:
                pass
            #print "doing notify %s %s" %(name, text)
            self.notify(name, text, root)
        elif packetType == 'init':
            # we need to do some initialization commands, but we
            # cannot do that from this thread, which is currently
            # the cmdloop thread, because it would cause a deadlock.
            # this is a short lived thread, so should be fine
            log.debug('starting init thread')
            threading.Thread(target = self.initFeatures, args=(root,)).start()

    def initFeatures(self, initNode):
        # get our init information
        self.applicationId = initNode.getAttribute('appid')
        self.threadId = initNode.getAttribute('thread')
        self.parentId = initNode.getAttribute('parent')
        self.cookie = initNode.getAttribute('session')
        self.idekey = initNode.getAttribute('idekey')
        # If the client has set a specific hostname setting, then use it,
        # else we default to the socket connection address.
        if initNode.hasAttribute("hostname"):
            self.hostname = initNode.getAttribute('hostname')
        else:
            self.hostname = self._clientAddr[0]

        # we're now in a starting status.  force feed this
        # so that commands are not queued during startup
        self.statusName = 'starting'
        if initNode.hasAttribute('interactive'):
            self.statusName = 'interactive'
            self.interactivePrompt = initNode.getAttribute('interactive')
            #log.debug("setting initial interactove prompt to %s", self.interactivePrompt)

        # let the world know we're here
        if not self._sessionHost.initHandler(self, initNode):
            # we've closed the session
            return

        # gather some necessary information for this session
        # any information we need during an async operation needs
        # to be retreived prior to async commands being done
        # we can ignore the error that is raised when something
        # is not supported
        log.debug('init thread running')
        try:
            self.supportsAsync = int(self.featureGet('supports_async'))
        except Exception, e:
            log.debug('init thread supportsAsync unknown')
            if self._stop: return
        try:
            self.languageName = self.featureGet('language_name')
        except Exception, e:
            log.debug('init thread languageName unknown')
            if self._stop: return
        try:
            self.languageVersion = self.featureGet('language_version')
        except Exception, e:
            log.debug('init thread languageVersion unknown')
            if self._stop: return
        try:
            self.maxChildren = int(self.featureGet('max_children'))
        except Exception, e:
            self.maxChildren = 0
            log.debug('init thread maxChildren unknown')
            if self._stop: return
        try:
            self.maxData = int(self.featureGet('max_data'))
        except Exception, e:
            self.maxData = 0
            log.debug('init thread maxData unknown')
            if self._stop: return
        try:
            self.maxDepth = int(self.featureGet('max_depth'))
        except Exception, e:
            self.maxDepth = 0
            log.debug('init thread maxDepth unknown')
            if self._stop: return
        try:
            self.featureGet('show_hidden')
            self.supportsHiddenVars = 1
        except Exception, e:
            self.supportsHiddenVars = 0
            log.debug('init supportsHiddenVars false')
            if self._stop: return
        try:
            self.featureGet('supports_postmortem')
            self.supportsPostmortem = 1
        except Exception, e:
            self.supportsPostmortem = 0
            log.debug('init supportsPostmortem false')
            if self._stop: return
        try:
            self.featureSet('multiple_sessions', '1')
        except Exception, e:
            log.debug('init thread multiple_sessions unknown')
            if self._stop: return
        try:
            # let the engine know it can send us notifications
            self.featureSet('notify_ok', '1')
        except Exception, e:
            log.debug('engine does not support notifications')
            if self._stop: return
        try:
            self._supportsOptionalCommand('break')
        except Exception, e:
            log.debug('init thread break unknown')
            if self._stop: return
        try:
            self._supportsOptionalCommand('eval')
        except Exception, e:
            log.debug('init thread eval unknown')
            if self._stop: return
        try:
            self._supportsOptionalCommand('stdin')
        except Exception, e:
            log.debug('init thread stdin unknown')
            if self._stop: return
        try:
            self._supportsOptionalCommand('detach')
        except Exception, e:
            log.debug('init thread detach unknown')
            if self._stop: return
        try:
            self._supportsOptionalCommand('interact')
        except Exception, e:
            log.debug('does not support interactive debugger')
            if self._stop: return
        try:
            self.breakpointLanguages = [l.lower() for l in self.featureGet('breakpoint_languages').split(',')]
        except Exception, e:
            if self._stop: return
            self.breakpointLanguages = [self.languageName]
        log.debug('init thread breakpoint_languages %r', self.breakpointLanguages)
        try:
            self._getTypeMap()
        except Exception, e:
            log.error('unable to retrieve typeMap from client')
            if self._stop: return
        # pass the url mapping to the engine
        try:
            if self._supportsOptionalCommand('urimap'):
                maps = self._sessionHost.getURIMappings()
                for map in maps:
                    self.featureSet('urimap', map)
        except Exception, e:
            log.debug('client does not support urimap feature')
            if self._stop: return

        # grab the breakpoint list now
        try:
            # some languages, eg. Tcl, have to do some processing before
            # breakpoints are set.  This notification allows hooks to be
            # added for that purpose
            if self._application and self._application.sessionCount() == 1:
                self._sessionHost.notifyStartup(self, initNode)

            err = self._sessionHost.breakpointManager.setSessionBreakpoints(self)
            #XXX Should, ideally, show this error to the user somehow. Ideas:
            #    - pop up a dialog and offer to cancel debugging?
            #    - status bar message?
            #    - display the breakpoint/spawnpoint markers slightly
            #      differently and remember this data so that the properties
            #      page for the breakpoint shows that this is not set on
            #      the session
            if err:
                log.error("the following breakpoints/spawnpoints could not "
                          "be set on this session:\n%s" % err)
        except Exception, e:
            log.error('breakpoints failed to be set properly')
            pass
        if not self._stop:
            # are we a new thread in the app?  If so, then just do
            # the run command now
            if self._application and self._application.sessionCount() > 1:
                self.resume(RESUME_GO)
                # no notifyInit for threads in an app
                return

            self._sessionHost.notifyInit(self, initNode)

    def notify(self, name, text, node):
        # "node" is the reponse node from the last continuation command
        #
        # THREAD WARNING
        # this function is called from the command loop thread.  Do
        # not do anything here that will result in another command
        # being sent to the client, that will result in a lockup
        # we were running, now we're at a break, or stopping

        log.info('session notify %s:%s name %s data %s',
                  self.applicationId,
                  self.threadId,
                  name, text)

    def stateChange(self, node):
        # "node" is the reponse node from the last continuation command
        #
        # THREAD WARNING
        # this function is called from the command loop thread.  Do
        # not do anything here that will result in another command
        # being sent to the client, that will result in a lockup
        # we were running, now we're at a break, or stopping
        if node:
            self.statusName = node.getAttribute('status')
            self.reason = node.getAttribute('reason')

        log.info('session %s:%s state %s',
                  self.applicationId,
                  self.threadId,
                  self.statusName)

    def addApplication(self, app):
        log.debug('setting session application')
        self._application = app

    def removeApplication(self):
        # [TM] Basically this is a poorly named session.finalize().
        log.debug('removing session application')
        # Tell the breakpoint manager that this debug session is shutting
        # down.
        self._sessionHost.breakpointManager.releaseSession(self)
        # don't remove the application var, just let the thread
        # know it should stop.
        self._stop = 1

    def _responseHandler(self, node):
        tid = None
        if node.hasAttribute('transaction_id'):
            tid = int(node.getAttribute('transaction_id'))
        if not tid:
            raise DBGPError('response without a transaction id')
        self._responses[tid] = node
        self._resp_cv.acquire()
        self._resp_cv.notify()
        self._resp_cv.release()

    def sendCommandWait(self, argv, data = None):
        if self._stop:
            raise DBGPError('command sent after session stopped')
        tid = self.sendCommand(argv, data)
        node = self._waitResponse(tid)
        err = node.getElementsByTagName('error')
        if err:
            errcode = err[0].getAttribute('code')
            msgnode = err[0].getElementsByTagName('message')
            msg = ''
            if msgnode:
                for child in msgnode[0].childNodes:
                    msg = msg + child.nodeValue
            if errcode:
                errcode = int(errcode)
            raise DBGPError(msg, errcode)
        return node

    def waitResponse(self, tid, timeout=5):
        return self._waitResponse(tid, timeout)

    def _waitResponse(self, tid, timeout=25):
        ticks = 0
        while not timeout or ticks < timeout:
            if tid in self._responses:
                resp = self._responses[tid]
                del self._responses[tid]
                return resp
            # XXX need the timeout here to prevent lockups
            # with tcl 11/25/03
            #if self._stop:
            ticks += 1
            self._resp_cv.acquire()
            self._resp_cv.wait(1)
            self._resp_cv.release()
        raise DBGPError('session timed out while waiting for response')

    def updateStatus(self):
        node = self.sendCommandWait(['status'])
        self.statusName = node.getAttribute('status')
        self.reason = node.getAttribute('reason')

    #/* status values */
    #readonly attribute long status;
    #readonly attribute long reason;
    def getLastError(self):
        pass

    def getBreakpointLanguages(self):
        return self.breakpointLanguages

    #/* feature commands */
    #wstring featureGet(in wstring name);
    def featureGet(self, name):
        self._supportsAsync()
        node = self.sendCommandWait(['feature_get', '-n', name])
        supported = node.getAttribute('supported')
        if not supported or not long(supported):
            raise DBGPError('Feature %s not supported' % name)
        if node.firstChild:
            return node.firstChild.nodeValue
        return 0

    #boolean featureSet(in wstring name, in wstring value);
    def featureSet(self, name, value):
        self._supportsAsync()
        node = self.sendCommandWait(['feature_set', '-n', name, '-v', str(value)])
        if not node.hasAttribute('success') or not int(node.getAttribute('success')):
            raise DBGPError('Unable to set feature %s' % name)
        return 1

    def _supportsAsync(self):
        #if self.supportsAsync is None:
        #    try:
        #        node = self.sendCommandWait(['feature_get', '-n', 'supports_async'])
        #        self.supportsAsync = int(node.getAttribute('supported'))
        #    except DBGPError, e:
        #        self.supportsAsync = 0
        if not self.supportsAsync and self._resume > 0:
            raise DBGPError('Asynchronous commands are not supported')

    def _supportsOptionalCommand(self, commandName):
        if commandName not in self._supportedCommands:
            try:
                self.featureGet(commandName)
                self._supportedCommands[commandName] = 1
            except DBGPError, e:
                log.debug("command [%s] is not supported by debugger", commandName)
                self._supportedCommands[commandName] = 0
        return self._supportedCommands[commandName]

    def _noAsync(self, commandName):
        # Assert that this command is not being called asychronously (i.e.
        # this command is being called in a break state).
        if self._resume > 0:
            raise DBGPError('Cannot issue command [%s] asynchronously' % commandName)

    #/* continuation commands */
    #boolean resume(in long resumeAction);
    def resume(self, action):
        if self._resume > 0:
            raise DBGPError('Session already in resume state %d' % self._resume)

        # Notify breakpoint manager in case it has queue up
        # breakpoint/spawnpoint updates to send on to the session.
        self._sessionHost.breakpointManager.sendUpdatesToSession(self)

        self._resume = action
        self.statusName = 'running'
        self.sendCommand([resume_command_names[self._resume]])
        # set the status to running
        #self.stateChange(None)
        return 1

    def resumeWait(self, action):
        if self._resume > 0:
            raise DBGPError('Session already in resume state %d' % self._resume)

        # Notify breakpoint manager in case it has queue up
        # breakpoint/spawnpoint updates to send on to the session.
        self._sessionHost.breakpointManager.sendUpdatesToSession(self)

        self._resume = action
        self.statusName = 'running'
        resp = self.sendCommandWait([resume_command_names[self._resume]])
        # set the status to running
        #self.stateChange(None)
        return resp

    #boolean break();
    def breakNow(self):
        self._supportsAsync()
        node = self.sendCommandWait(['break'])
        return node.hasAttribute('success') and int(node.getAttribute('success'))

    #boolean stop();
    def stop(self):
        # we cannot wait for a response here, as sometimes apps close
        # before we can read the response off the socket.
        tid = self.sendCommand(['stop'])
        return 1

    #boolean detach();
    def detach(self):
        if not self._supportsOptionalCommand('detach'):
            log.debug('client does not support detach!')
            return 0
        # we cannot wait for a response here, as sometimes apps close
        # before we can read the response off the socket.
        tid = self.sendCommand(['detach'])
        return 1

    #wstring interact(in wstring command);
    def interact(self, command):
        self._supportsAsync()
        if not self._supportsOptionalCommand('interact'):
            log.debug('client does not support interact!')
            return 0
        self.statusName = 'running'

        # turn off interactive mode.  It gets turned on again when we receive
        # the response to this command. It needs to be turned off because we
        # might recieved stdin requests before we receive an interact response.
        # We also must do this before sending the command to avoid the
        # response happening before we turn this off (threads, happy happy joy joy)
        self.interactivePrompt = ''

        if command is None:
            tid = self.sendCommand(['interact', '-m', '0'])
        else:
            tid = self.sendCommand(['interact', '-m', '1'], command)

        return tid

    #/* stack commands */
    #long stackDepth();
    def stackDepth(self):
        self._noAsync('stack_depth')
        node = self.sendCommandWait(['stack_depth'])
        return node.getAttribute('depth')

    #koIDBGPStackFrame stackGet(in long depth);
    def stackGet(self, depth):
        self._noAsync('stack_get')
        node = self.sendCommandWait(['stack_get', '-d', str(depth)])
        for child in node.childNodes:
            if child.nodeType != node.ELEMENT_NODE or child.tagName != 'stack': continue
            frame = stackFrame()
            frame.initWithNode(child)
            return frame
        return None

    #void stackFramesGet([array, size_is(count)] out koIDBGPStackFrame frames,
    #                  out PRUint32 count);
    def stackFramesGet(self):
        self._noAsync('stack_get')
        node = self.sendCommandWait(['stack_get'])
        frames = []
        children = node.getElementsByTagName('stack')
        for child in children:
            frame = stackFrame()
            frame.initWithNode(child)
            frames.append(frame)
        return frames

    #/* context commands */
    #void contextNames([array, size_is(count)] out koIDBGPContextType contextTypes,
    #                  out PRUint32 count);
    def contextNames(self):
        self._noAsync('context_names')
        node = self.sendCommandWait(['context_names'])
        contextList = []
        children = node.getElementsByTagName('context')
        for child in children:
            context = contextType()
            context.initWithNode(child)
            contextList.append(context)
        return contextList

    #void contextGet(in long id,
    #                [array, size_is(count)] out koIDBGPProperty properties,
    #                out PRUint32 count);
    def contextGet(self, contextId, depth):
        self._noAsync('context_get')
        node = self.sendCommandWait(['context_get', '-c', str(contextId), '-d', str(depth)])
        propertyList = []
        for child in node.childNodes:
            if child.nodeType == minidom.Node.ELEMENT_NODE and \
               child.tagName == 'property':
                p = property()
                p.initWithNode(self, child, contextId, depth)
                propertyList.append(p)
        return propertyList

    #/* property commands */
    #koIDBGPProperty propertyGet(in long contextId,
    #                            in long stackDepth,
    #                            in wstring fullname,
    #                            in long maxData,
    #                            in long dataType,
    #                            in long dataPage);
    def propertyGet(self, fullname):
        return self.propertyGetEx(0, 0, fullname, 0, '', 0)

    def propertyGetEx(self, contextId, stackDepth, fullname, maxData, dataType, dataPage, address=""):
        self._noAsync('property_get')
        cmd = ['property_get', '-c', str(contextId),
                '-d', str(stackDepth), '-n', fullname]
        if maxData:
            cmd += ['-m', str(maxData)]
        if dataType:
            cmd += ['-t', dataType]
        if dataPage:
            cmd += ['-p', str(dataPage)]
        if address and len(address) > 0:
            cmd += ['-a', str(address)]
        try:
            node = self.sendCommandWait(cmd)
            p = property()
            p.initWithNode(self, node.firstChild, contextId, stackDepth)
        except DBGPError, e:
            # create an empty var with the exception for the value
            p = property()
            p.session = self
            p.context = contextId
            p.depth = stackDepth
            p.fullname = fullname
            p.name = fullname
            p.value = getErrorInfo(e)[1]
            p.type = 'exception'
        return p

    #koIDBGPProperty propertySet(in long contextId,
    #                    in long stackDepth,
    #                    in wstring name,
    #                    in wstring value);
    def propertySet(self, name, value):
        return self.propertySetEx(0, 0, name, value)

    def propertySetEx(self, contextId, stackDepth, name, value):
        self._noAsync('property_set')
        args = ['property_set', '-c', str(contextId), '-d',
                str(stackDepth), '-n', name]
        node = self.sendCommandWait(args, value)
        if node.hasAttribute('success'):
            if int(node.getAttribute('success')):
                return self.propertyGetEx(contextId, stackDepth, name, 0, '', 0)
            else:
                raise DBGPError("Unable to set the property value.")
        return None

    def propertyUpdate(self, prop, value, type):
        self._noAsync('property_set')
        args = ['property_set', '-c', str(prop.contextId), '-d',
                str(prop.depth), '-n', prop.fullname]
        if prop.key:
            args += ['-k', prop.key]
        if prop.address:
            prop_address = prop.address
            args += ['-a', prop_address]
        else:
            prop_address = ""
        if type:
            args += ['-t', type]
        node = self.sendCommandWait(args, value)
        if node.hasAttribute('success'):
            if int(node.getAttribute('success')):
                return self.propertyGetEx(prop.contextId, prop.depth, prop.fullname, 0, '', 0, prop_address)
            else:
                raise DBGPError("Unable to update the variable.")
        return None

    #wstring propertyValue(in long contextId,
    #                    in long stackDepth,
    #                    in wstring name);
    def propertyValue(self, name):
        return self.propertyValueEx(0, 0, name)

    def propertyValueEx(self, contextId, stackDepth, name):
        self._noAsync('property_value')
        args = ['property_value', '-c', str(contextId), '-d',
                str(stackDepth), '-n', name]
        node = self.sendCommandWait(args)

        encoding = None
        if node.hasAttribute('encoding'):
            encoding = node.getAttribute('encoding')

        value = ''
        # we may have more than one text node, get them all
        for child in node.childNodes:
            if child.nodeType in [minidom.Node.TEXT_NODE,
                                  minidom.Node.CDATA_SECTION_NODE]:
                value = value + child.nodeValue
        try:
            if value and encoding == 'base64':
                value = base64.decodestring(value)
        except:
            pass

        return value


    #---- breakpoint commands
    def breakpointSet(self, bp):
        """Set the given breakpoint on this session.

        Returns the session's assigned ID (a string) for the new breakpoint.
        Raises a DBGPError if the command fails.
        """
        bplog.debug("session.breakpointSet(bp='%s')", bp.getName())
        self._supportsAsync()
        bpargs, bpdata = bp.getSetArgs()
        args = ["breakpoint_set"] + bpargs
        node = self.sendCommandWait(args, bpdata)
        return node.getAttribute("id")

    def breakpointUpdate(self, bpid, bp, attrs=None):
        """Update the given breakpoint.

            "bpid" is the session's ID for this breakpoint.
            "bp" is a breakpoint instance from which to update
            "attrs" (optional) is a list of attributes that are meant to be
                updated. If None (or the empty list), then all attributes
                are updated.

        Raises a DBGPError if the command fails.
        """
        bplog.debug("session.breakpointUpdate(bpid=%r, bp='%s', attrs=%r)",
                    bpid, bp.getName(), attrs)
        self._supportsAsync()
        args = ["breakpoint_update", "-d", str(bpid)]
        if not attrs:  # False means update all supported attributes.
            args += ["-s", bp.state]
            args += ["-n", str(bp.lineno)]
            args += ["-h", str(bp.hitValue)]
            if bp.hitCondition:
                args += ["-o", bp.hitCondition]
            args += ["-r", str(int(bp.temporary))]
        else: # Only update the specified attributes.
            for attr in attrs:
                if attr == "state":
                    args += ["-s", bp.state]
                elif attr == "lineno":
                    args += ["-n", str(bp.lineno)]
                elif attr == "hitValue":
                    args += ["-h", str(bp.hitValue)]
                elif attr == "hitCondition":
                    args += ["-o", bp.hitCondition]
                elif attr == "temporary":
                    args += ["-r", str(int(bp.temporary))]
        if bp.type in 'conditional':
            bpdata = bp.expression
        else:
            bpdata = None
        bplog.debug("session %r: '%r', data='%r'", (self.applicationId, self.threadId), args, bpdata)
        node = self.sendCommandWait(args, bpdata)

    def breakpointGet(self, bpid):
        """Get the breakpoint with the given session breakpoint id.

        Raises a DBGPError if the command fails.
        """
        bplog.debug("session.breakpointGet(bpid=%r)", bpid)
        self._supportsAsync()
        node = self.sendCommandWait(["breakpoint_get", "-d", str(bpid)])
        children = node.getElementsByTagName("breakpoint")
        if not children:
            return None
        bp = breakpoint()
        bp.initWithNode(children[0])
        return bp

    def breakpointEnable(self, bpid):
        """Enable the breakpoint with the given session breakpoint id.

        NOTE: This command is OBSOLETE. Use breakpointUpdate() instead.

        Raises a DBGPError if the command fails.
        """
        bplog.debug("session.breakpointEnable(bpid=%r)", bpid)
        self._supportsAsync()
        self.sendCommandWait(["breakpoint_enable", "-d", str(bpid)])

    def breakpointDisable(self, bpid):
        """Disable the breakpoint with the given session breakpoint id.

        NOTE: This command is OBSOLETE. Use breakpointUpdate() instead.

        Raises a DBGPError if the command fails.
        """
        bplog.debug("session.breakpointDisable(bpid=%r)", bpid)
        self._supportsAsync()
        node = self.sendCommandWait(["breakpoint_disable", "-d", str(bpid)])

    def breakpointRemove(self, bpid):
        """Remove the breakpoint with the given session breakpoint id.

        Raises a DBGPError if the command fails.
        """
        bplog.debug("session.breakpointRemove(bpid=%r)", bpid)
        self._supportsAsync()
        node = self.sendCommandWait(["breakpoint_remove", "-d", str(bpid)])

    def breakpointList(self):
        """Return a list of all breakpoints for this session.

        Raises a DBGPError if the command fails.
        """
        self._supportsAsync()
        node = self.sendCommandWait(["breakpoint_list"])
        children = node.getElementsByTagName("breakpoint")
        breakpoints = []
        for child in children:
            bp = breakpoint()
            bp.initWithNode(child)
            breakpoints.append(bp)
        return breakpoints


    #---- spawnpoint commands
    def spawnpointSet(self, sp):
        """Set the given spawnpoint on this session.

        Returns the session's assigned ID (a string) for the new spawnpoint.
        Raises a DBGPError if the command fails.
        """
        self._noAsync("spawnpoint_set")
        spArgs, spData = sp.getSetArgs()
        args = ["spawnpoint_set"] + spArgs
        node = self.sendCommandWait(args, spData)
        return node.getAttribute("id")

    def spawnpointUpdate(self, spid, sp, attrs=None):
        """Update the given spawnpoint.

            "spid" is the session's ID for this spawnpoint.
            "sp" is a spawnpoint instance from which to update
            "attrs" (optional) is a list of attributes that are meant to be
                updated. If None, then all attributes are updated.

        Raises a DBGPError if the command fails.
        """
        self._noAsync("spawnpoint_update")
        args = ["spawnpoint_update", "-d", spid]
        if attrs is None:  # None means update all supported attributes.
            args += ["-s", str(sp.state)]
            args += ["-n", str(sp.lineno)]
        else: # Only update the specified attributes.
            for attr in attrs:
                if attr == "state":
                    args += ["-s", str(sp.state)]
                elif attr == "lineno":
                    args += ["-n", str(sp.lineno)]
        node = self.sendCommandWait(args)

    def spawnpointGet(self, spid):
        """Get the spawnpoint with the given session spawnpoint id.

        Raises a DBGPError if the command fails.
        """
        self._noAsync("spawnpoint_get")
        node = self.sendCommandWait(["spawnpoint_get", "-d", str(spid)])
        children = node.getElementsByTagName("spawnpoint")
        if not children:
            return None
        sp = spawnpoint()
        sp.initWithNode(children[0])
        return sp

    def spawnpointEnable(self, spid):
        """Enable the spawnpoint with the given session spawnpoint id.

        NOTE: This command is OBSOLETE. Use spawnpointUpdate() instead.

        Raises a DBGPError if the command fails.
        """
        self._noAsync("spawnpoint_enable")
        self.sendCommandWait(["spawnpoint_enable", "-d", str(spid)])

    def spawnpointDisable(self, spid):
        """Disable the spawnpoint with the given session spawnpoint id.

        NOTE: This command is OBSOLETE. Use spawnpointUpdate() instead.

        Raises a DBGPError if the command fails.
        """
        self._noAsync("spawnpoint_disable")
        node = self.sendCommandWait(["spawnpoint_disable", "-d", str(spid)])

    def spawnpointRemove(self, spid):
        """Remove the spawnpoint with the given session spawnpoint id.

        Raises a DBGPError if the command fails.
        """
        self._noAsync("spawnpoint_remove")
        node = self.sendCommandWait(["spawnpoint_remove", "-d", str(spid)])

    def spawnpointList(self):
        """Return a list of all spawnpoints for this session.

        Raises a DBGPError if the command fails.
        """
        self._noAsync("spawnpoint_list")
        node = self.sendCommandWait(["spawnpoint_list"])
        children = node.getElementsByTagName("spawnpoint")
        spawnpoints = []
        for child in children:
            sp = spawnpoint()
            sp.initWithNode(child)
            spawnpoints.append(sp)
        return spawnpoints


    #/* eval */
    #koIDBGPProperty evalString(in wstring expression);
    def evalString(self, expression):
        self._noAsync('eval')
        l = len(expression)
        try:
            node = self.sendCommandWait(['eval', '-l', str(l)], expression)
            pnodes = node.getElementsByTagName('property')
            if pnodes:
                p = property()
                p.initWithNode(self, pnodes[0])
                p.name = expression
                return p
        except DBGPError, e:
            # create an empty var with the exception for the value
            p = property()
            p.session = self
            p.context = 0
            p.depth = 0
            p.fullname = expression
            p.name = expression
            p.value = getErrorInfo(e)[1]
            p.type = 'exception'
            return p
        return None

    def _getTypeMap(self):
        self._noAsync('typemap_get')
        node = self.sendCommandWait(['typemap_get'])
        self._typeMap = {}
        children = node.getElementsByTagName('map')
        for child in children:
            typ = dataType()
            typ.initWithNode(child)
            self._typeMap[typ.languageType] = typ

    #void getTypeMap([array, size_is(count)] out koIDBGPDataType dateTypes,
    #                  out PRUint32 count);
    def getTypeMap(self):
        if not self._typeMap:
            self._getTypeMap()
        return self._typeMap.values()

    def getDataType(self, commonType):
        for typ in self.getTypeMap():
            if typ.commonType == commonType:
                return typ
        return None

    ## Gets the sourcecode for the named file.
    #wstring getSourceCode(in wstring filename);
    def getSourceCode(self, filename, startline, endline):
        self._noAsync('source')
        cmd = ['source']
        if filename:
            cmd += ['-f', filename]
        if startline:
            cmd += ['-b', str(startline)]
        if endline:
            cmd += ['-e', str(endline)]
        node = self.sendCommandWait(cmd)
        text = ''
        for c in node.childNodes:
            text = text + c.nodeValue
        try:
            text = base64.decodestring(text)
        except:
            pass
        return text

    #sendStdin(in wstring data, in long size);
    def sendStdin(self, data, size):
        if not self._supportsOptionalCommand('stdin'):
            log.debug('client does not support stdin!')
            return 0
        log.debug('sending stdin [%s]!', data)
        node = self.sendCommandWait(['stdin'], data)
        return node.getAttribute('success')

    #setStdinHandler(in koIFile file);
    def setStdinHandler(self, file):
        if not self._supportsOptionalCommand('stdin'):
            log.debug('client does not support stdin!')
            return 0
        if file:
            cmd = ['stdin', '-c', '1']
        else:
            cmd = ['stdin', '-c', '0']
        node = self.sendCommandWait(cmd)
        return node.getAttribute('success')

    #setStdoutHandler(in koIFile file, in long mode);
    def setStdoutHandler(self, file, mode):
        node = self.sendCommandWait(['stdout', '-c', str(mode)])
        return node.getAttribute('success')

    #setStderrHandler(in koIFile file, in long mode);
    def setStderrHandler(self, file, mode):
        node = self.sendCommandWait(['stderr', '-c', str(mode)])
        return node.getAttribute('success')

def _sessionSort(a, b):
    return cmp(a.threadId, b.threadId)

class application:
    def __init__(self, appMgr):
        self.appMgr = appMgr
        self._watchedvars = {}
        self._sessions = {}
        self.currentSession = None
        self._stdin = self._stdout = self._stderr = None
        _lock = threading.Lock()

    def addSession(self, session):
        log.debug('pid %r adding thread %r', session.applicationId, session.threadId)
        self._sessions[session.threadId] = session
        session.addApplication(self)
        if not self.currentSession:
            self.currentSession = session

    def haveSession(self, session):
        return session in self._sessions.values()

    def releaseSession(self, session):
        log.debug('removing session')
        session.removeApplication()
        del self._sessions[session.threadId]
        # reset current thread now or quit
        if len(self._sessions) < 1:
            self.shutdown()
            return
        if session == self.currentSession:
            self.currentSession = self._sessions.values()[0]

    def getSessionList(self):
        l = self._sessions.values()
        l.sort(_sessionSort)
        return l

    def shutdown(self):
        if self._stdin:
            self._stdin.close()
        for ses in self._sessions.keys():
            self._sessions[ses].removeApplication()
            if self._sessions.has_key(ses):
                del self._sessions[ses]
        self.appMgr.releaseApplication(self)

    def sessionCount(self):
        return len(self._sessions.keys())

    #sendStdin(in wstring data, in long size);
    def sendStdin(self, data, size):
        return self.currentSession.sendStdin(data, size);

    #setStdinHandler(in koIFile file);
    def setStdinHandler(self, file):
        # XXX need to set for all sessions?
        ok = self.currentSession.setStdinHandler(file)
        if ok:
            self._stdin = file
            threading.Thread(target = self._stdinHandlerThread).start()
        return ok

    def _stdinHandlerThread(self):
        log.debug('starting stdin thread')
        while 1:
            try:
                #log.debug('reading console data...')
                data = self._stdin.read(1024)
                if not data:
                    self.currentSession.setStdinHandler(None)
                    log.debug('empty data from console, stdin closed')
                    break

                log.debug('writing stdin data...[%s]', data)
                self.sendStdin(data, len(data))
            except Exception, e:
                log.exception(e)
                break
        log.debug('quiting stdin thread')

    #setStdoutHandler(in koIFile file, in long mode);
    def setStdoutHandler(self, file, mode):
        # XXX need to set for all sessions?
        ok = self.currentSession.setStdoutHandler(file, mode)
        if ok:
            self._stdout = file
        return ok

    #setStderrHandler(in koIFile file, in long mode);
    def setStderrHandler(self, file, mode):
        # XXX need to set for all sessions?
        ok = self.currentSession.setStderrHandler(file, mode)
        if ok:
            self._stderr = file
        return ok

    def outputHandler(self, stream, text):
        log.debug('outputHandler [%r] [%r]', stream, text)
        if stream == 'stdout' and self._stdout:
            self._stdout.write(text)
        elif stream == 'stderr' and self._stderr:
            self._stderr.write(text)


class appManager:
    appList = {}
    _lock = threading.Lock()

    def __init__(self, debugMgr):
        self.debugMgr = debugMgr

    def getApplication(self, session):
        self._lock.acquire()
        try:
            if session.applicationId not in self.appList:
                log.debug('creating application class for pid %r',session.applicationId)
                self.appList[session.applicationId] = application(self)
            else:
                log.debug('getting application class for pid %r',session.applicationId)
            if not self.appList[session.applicationId].haveSession(session):
                self.appList[session.applicationId].addSession(session)
        finally:
            self._lock.release()
        return self.appList[session.applicationId]

    def releaseApplication(self, appinst):
        # kill command was issued, remove all references
        appid = appinst.currentSession.applicationId
        if appid not in self.appList:
            # XXX raise exception?
            return
        self._lock.acquire()
        try:
            data = self.appList[appid]
            del self.appList[appid]
        finally:
            self._lock.release()

    def shutdown(self):
        for app in self.appList.values():
            app.shutdown()


class listener(serverlistener):
    def startNewSession(self, client, addr):
        # start a new thread that is the host connection
        # for this debugger session
        sessionHost = session(self._session_host)
        sessionHost.start(client, addr)


class breakpointManager:
    _lock = threading.Lock()
    _breakpoints = {} # mapping of breakpoint guid to breakpoint instance

    def __init__(self):
        self._guidCounter = 0 # used to assign a unique self._id to each bp

        # Keep track of what debug sessions have what breakpoints and what
        # ids they have assigned for them. Essentially this information is
        # a cache because _technically_ we could query every debug session
        # for this info every time.
        # - Note: A session id is defined here as the 2-tuple
        #      (session.applicationId, session.threadId)
        #   because I [TrentM] am not sure if threadId's are necessarily
        #   unique across application's.
        self._allSessionBPIDs = {
            # <session id>: {<breakpoint guid>: <session bpid>, ...}
        }
        self._queuedSessionCommands = {
            # <session id>: <FIFO of commands to send on break state>
            #   where each "command" is a 2-tuple:
            #       (<set|remove|update>, <tuple of args>)
            #   e.g.:
            #       ("set",    (<breakpoint instance>,))
            #       ("remove", (<breakpoint instance>,))
            #       ("update", (<breakpoint instance>, <attrs to update>))
        }
        self._sessions = {
            # <session id>: <session instance>
        }

    def _makeBreakpointGuid(self):
        guid = self._guidCounter
        self._guidCounter += 1
        return guid

    # The .addBreakpoint*() methods (and .addSpawnpoint()) are convenience
    # methods for the more general .addBreakpoint() to add breakpoints of
    # specific types.
    def addBreakpointConditional(self, lang, cond, file, line, state,
                                 temporary, hitValue, hitCondition):
        bp = breakpoint()
        bp.initConditional(lang, cond, file, line, state, temporary,
                           hitValue, hitCondition)
        self.addBreakpoint(bp)
        return bp
    def addBreakpointLine(self, lang, file, line, state, temporary = 0,
                          hitValue = None, hitCondition = None):
        bp = breakpoint()
        bp.initLine(lang, file, line, state, temporary, hitValue,
                    hitCondition)
        self.addBreakpoint(bp)
        return bp
    def addBreakpointException(self, lang, exceptionName, state, temporary,
                               hitValue, hitCondition):
        bp = breakpoint()
        bp.initException(lang, exceptionName, state, temporary, hitValue,
                         hitCondition)
        self.addBreakpoint(bp)
        return bp
    def addBreakpointCall(self, lang, func, filename, state, temporary,
                          hitValue, hitCondition):
        bp = breakpoint()
        bp.initCall(lang, func, filename, state, temporary, hitValue,
                    hitCondition)
        self.addBreakpoint(bp)
        return bp
    def addBreakpointReturn(self, lang, func, filename, state, temporary,
                            hitValue, hitCondition):
        bp = breakpoint()
        bp.initReturn(lang, func, filename, state, temporary, hitValue,
                      hitCondition)
        self.addBreakpoint(bp)
        return bp
    def addBreakpointWatch(self, lang, watch, file, line, state,
                            temporary, hitValue, hitCondition):
        bp = breakpoint()
        bp.initWatch(lang, watch, file, line, state, temporary,
                           hitValue, hitCondition)
        self.addBreakpoint(bp)
        return bp
    def addSpawnpoint(self, lang, filename, line, state):
        sp = spawnpoint()
        sp.init(lang, filename, line, state)
        # we just stuff our spawnpoints into the breakpoints
        self.addBreakpoint(sp)
        return sp

    def addBreakpoint(self, bp):
        self._lock.acquire()
        try:
            bp._guid = self._makeBreakpointGuid()
            self._breakpoints[bp.getGuid()] = bp

            # Pass this new breakpoint onto any current debug session for
            # which this is appropriate.
            for session in self._sessions.values():
                try:
                    self._setSessionBreakpointOrQueueIt(session, bp)
                except (DBGPError, COMException), ex:
                    log.exception(ex)
                    pass # XXX should report to user somehow

            self.postAddBreakpoint(bp)
        finally:
            self._lock.release()

    def postAddBreakpoint(self, bp):
        """Method stub to allow subclasses to react to a breakpoint
        addition while the breakpoints lock is held.
        """
        pass

    def removeBreakpoint(self, guid):
        self._lock.acquire()
        try:
            if self._breakpoints.has_key(guid):
                bp = self._breakpoints[guid]
                del self._breakpoints[guid]

                # Remove this breakpoint from any session that currently has it.
                for sessId, sessionBPIDs in self._allSessionBPIDs.items():
                    if guid in sessionBPIDs:
                        session = self._sessions[sessId]
                        self._removeSessionBreakpointOrQueueIt(session, bp)

                self.postRemoveBreakpoint(bp)
        finally:
            self._lock.release()

    def postRemoveBreakpoint(self, bp):
        """Method stub to allow subclasses to react to a breakpoint
        removal while the breakpoints lock is held.
        """
        pass

    def removeAllBreakpoints(self):
        self._lock.acquire()
        try:
            # Remove all breakpoints from all current debug sessions.
            #XXX:PERF _Could_ optimize this if necessary.
            for sessId, sessionBPIDs in self._allSessionBPIDs.items():
                for guid in sessionBPIDs.keys():
                    session = self._sessions[sessId]
                    bp = self._breakpoints[guid]
                    self._removeSessionBreakpointOrQueueIt(session, bp)

            self._breakpoints = {}

            self.postRemoveAllBreakpoints()
        finally:
            self._lock.release()

    def postRemoveAllBreakpoints(self):
        """Method stub to allow subclasses to react to a breakpoint list
        reset while the breakpoints lock is held.
        """
        pass

    def updateBreakpoint(self, guid, newBp):
        self._lock.acquire()
        try:
            bp = self._breakpoints[guid]
            self.preUpdateBreakpoint(bp)
            attrs = bp.update(newBp)

            # Update the breakpoint in all current debug sessions that
            # have this breakpoint.
            # Note: We are presuming here that the breakpoint update did not
            #       all of the sudden make this breakpoint applicable to a
            #       debug session when it previously was not.
            for sessId, sessionBPIDs in self._allSessionBPIDs.items():
                if guid in sessionBPIDs:
                    session = self._sessions[sessId]
                    self._updateSessionBreakpointOrQueueIt(session, bp, attrs)

            self.postUpdateBreakpoint(bp, attrs)
        finally:
            self._lock.release()

    def preUpdateBreakpoint(self, bp):
        """Method stub to allow subclasses to react _before_ a breakpoint
        change while the breakpoints lock is held.

            "bp" is the changed breakpoint.
        """
        pass

    def postUpdateBreakpoint(self, bp, attrs):
        """Method stub to allow subclasses to react to a breakpoint change
        while the breakpoints lock is held.

            "bp" is the changed breakpoint.
            "attrs" is a list of breakpoint attributes that changed.
        """
        pass

    def getBreakpointsForLanguage(self, lang):
        self._lock.acquire()
        try:
            #XXX Currently don't have to allow the "not bp.language": all
            #    breakpoints have their language attribute set.
            return [bp for bp in self._breakpoints.values()
                    if not bp.language or bp.language.lower() == lang.lower()]
        finally:
            self._lock.release()


    #---- Managing session breakpoints.
    # The first three methods are public and are meant to be called by the
    # application (or some other session manager) and the session's.
    # The rest are internal methods used to keep breakpoint info in sync
    # between here and each session.

    def setSessionBreakpoints(self, session):
        """Add the relevant breakpoints to this session.

        Returns a newline-separated list of breakpoints (and reasons) that
        did not get properly set on the session.
        """
        #XXX Breakpoints should only be added once for each
        #    "application" in DBGP-parlance. In DBGP-land there is one
        #    "Session" per thread, yet all threads share the same breakpoints.
        #    At least, that is my understanding of the intention from Shane.
        bplog.debug("breakpointManager.setSessionBreakpoints(session)")
        breakpoints = [bp for bp in self._breakpoints.values()]
        sessId = (session.applicationId, session.threadId)
        self._sessions[sessId] = session
        self._allSessionBPIDs[sessId] = {}
        self._queuedSessionCommands[sessId] = []
        failed = [] # list of bp's that did not get set on the session
        for bp in breakpoints:
            try:
                self.__setSessionBreakpoint(session, bp)
            except (DBGPError, COMException), ex:
                errno, errmsg = getErrorInfo(ex)
                failed.append("%s (%s)" % (bp.getName(), errmsg))
        return '\n'.join(failed)

    def releaseSession(self, session):
        """Release references to this session, it is shutting down."""
        sessId = (session.applicationId, session.threadId)
        if self._allSessionBPIDs.has_key(sessId):
            del self._allSessionBPIDs[sessId]
        if self._queuedSessionCommands.has_key(sessId):
            del self._queuedSessionCommands[sessId]
        if self._sessions.has_key(sessId):
            del self._sessions[sessId]

    def sendUpdatesToSession(self, session):
        """Any queued breakpoint/spawnpoint updates should be forwarded onto
        session.
        """
        self._sendQueuedSessionCommands(session)

    def _setSessionBreakpointOrQueueIt(self, session, bp):
        """Set the given breakpoint on the given session and update local
        cache information on this.

        If the session is not in a break state, this command is queued up
        until it is.
        """
        sessId = (session.applicationId, session.threadId)
        if session.supportsAsync:
            self._sendQueuedSessionCommands(session)
            self.__setSessionBreakpoint(session, bp)
            return

        if session.statusName not in ["break", "starting"]:
            # DBGP client sessions can only accept breakpoint changes when
            # in the break state. We will queue up this command for later.
            command = ("set", (bp,))
            self._queuedSessionCommands[sessId].append(command)
        else:
            self._sendQueuedSessionCommands(session)
            self.__setSessionBreakpoint(session, bp)

    def __setSessionBreakpoint(self, session, bp):
        # We are REALLY setting the breakpoint on the session now.
        sessId = (session.applicationId, session.threadId)
        if bp.type == "spawn":
            bpid = session.spawnpointSet(bp)
        else:
            bpid = session.breakpointSet(bp)
        self._allSessionBPIDs[sessId][bp.getGuid()] = bpid
        bplog.info("set '%s' %spoint on session %s: bpid='%s'",
                   bp.getName(), (bp.type=="spawn" and "spawn" or "break"),
                   sessId, bpid)

    def _removeSessionBreakpointOrQueueIt(self, session, bp):
        """Remove the given breakpoint from the given session and update
        local cache info.

        If the session is not in a break state, this command is queued up
        until it is.
        """
        sessId = (session.applicationId, session.threadId)
        if session.supportsAsync:
            self._sendQueuedSessionCommands(session)
            self.__removeSessionBreakpoint(session, bp)
            return

        if session.statusName != "break":
            # DBGP client sessions can only accept breakpoint changes when
            # in the break state. We will queue up this command for later.
            command = ("remove", (bp,))
            self._queuedSessionCommands[sessId].append(command)
        else:
            self._sendQueuedSessionCommands(session)
            self.__removeSessionBreakpoint(session, bp)

    def __removeSessionBreakpoint(self, session, bp):
        # We are REALLY removing the breakpoint from the session now.
        sessId = (session.applicationId, session.threadId)
        sessionBPIDs = self._allSessionBPIDs[sessId]
        guid = bp.getGuid()
        bpid = sessionBPIDs[guid] # the session's ID for this bp
        if bp.type == "spawn":
            session.spawnpointRemove(bpid)
        else:
            session.breakpointRemove(bpid)
        del sessionBPIDs[guid]
        bplog.info("removed '%s' %spoint from session %s",
                   bp.getName(), (bp.type=="spawn" and "spawn" or "break"),
                   sessId)

    def _updateSessionBreakpointOrQueueIt(self, session, bp, attrs):
        """Update the given attributes of the given breakpoint on the
        given debug session.

        If the session is not in a break state, this command is queued up
        until it is.
        """
        sessId = (session.applicationId, session.threadId)
        if session.supportsAsync:
            self._sendQueuedSessionCommands(session)
            self.__updateSessionBreakpoint(session, bp, attrs)
            return

        if session.statusName != "break":
            # DBGP client sessions can only accept breakpoint changes when
            # in the break state. We will queue up this command for later.
            command = ("update", (bp, attrs))
            self._queuedSessionCommands[sessId].append(command)
        else:
            self._sendQueuedSessionCommands(session)
            self.__updateSessionBreakpoint(session, bp, attrs)

    def __updateSessionBreakpoint(self, session, bp, attrs):
        # We are REALLY updating the breakpoint on the session now.
        sessId = (session.applicationId, session.threadId)
        sessionBPIDs = self._allSessionBPIDs[sessId]
        guid = bp.getGuid()
        bpid = sessionBPIDs[guid] # the session's ID for this bp
        if bp.type == "spawn":
            session.spawnpointUpdate(bpid, bp, attrs)
        else:
            session.breakpointUpdate(bpid, bp, attrs)
        bplog.info("updated '%s' %spoint on session %s: attrs=%s",
                   bp.getName(), (bp.type=="spawn" and "spawn" or "break"),
                   sessId, attrs)

    def _sendQueuedSessionCommands(self, session):
        """Send on any queued up commands for this session."""
        sessId = (session.applicationId, session.threadId)
        queuedCommands = self._queuedSessionCommands.get(sessId, [])
        try:
            for commandType, args in queuedCommands:
                if commandType == "set":
                    bp = args[0]
                    self.__setSessionBreakpoint(session, bp)
                elif commandType == "remove":
                    bp = args[0]
                    self.__removeSessionBreakpoint(session, bp)
                elif commandType == "update":
                    bp, attrs = args
                    self.__updateSessionBreakpoint(session, bp, attrs)
        finally:
            self._queuedSessionCommands[sessId] = []


class manager:
    def __init__(self):
        self._server_key = None
        self._proxyAddr = ''
        self._proxyPort = 0
        self.proxyClientAddress = ''
        self.proxyClientPort = 0
        self.appManager = appManager(self)
        self.breakpointManager = self.getBreakpointManager()
        self._listener = None

    def getBreakpointManager(self):
        # Allow this to be overridden.
        return breakpointManager()

    def getURIMappings(self):
        # overriden by IDE interface to provide url to local path mapping
        # to the debugger engine
        return []

    def setKey(self, key):
        self._server_key = key
        # key change, recycle the proxy if necessary
        if self._proxyAddr and self._listener:
            self._stopProxy()
            self._initProxy()

    def setProxy(self, address, port):
        if self._proxyAddr and self._listener:
            self._stopProxy()
        self._proxyAddr = address
        self._proxyPort = port
        if self._proxyAddr and self._listener:
            self._initProxy()

    def _initProxy(self):
        log.debug('manager starting proxy...')
        if not self._proxyPort:
            self._proxyPort = 9001
        if not self._proxyAddr:
            self._proxyAddr = '127.0.0.1'

        try:
            proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            proxy_socket.connect((self._proxyAddr,self._proxyPort))
            command = u'proxyinit -p %d -k %s -m 1' % \
                        (self._listener._port,
                         self._server_key)
            proxy_socket.send(command.encode('utf-8'))
            resp = proxy_socket.recv(1024)
            proxy_socket.close()
            dom = minidom.parseString(resp)
            root = dom.documentElement
            if root.getAttribute('success') == '1':
                self.proxyClientAddress = root.getAttribute('address')
                self.proxyClientPort = int(root.getAttribute('port'))
        except Exception, e:
            self.stop()
            raise DBGPError("the debugger proxy could not be contacted.")

    def _stopProxy(self):
        log.debug('manager stopping proxy...')
        try:
            proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            proxy_socket.connect((self._proxyAddr,self._proxyPort))
            command = u'proxystop -k %s' % self._server_key
            proxy_socket.send(command.encode('utf-8'))
            resp = proxy_socket.recv(1024)
            proxy_socket.close()
            self.proxyClientAddress = ''
            self.proxyClientPort = 0
        except Exception, e:
            # if we cannot stop the proxy when we're stopping, lets let it go
            log.debug('unable to contact proxy to stop proxying')

    def listen(self, address, port):
        log.debug('manager starting listener...')
        try:
            self._listener.stop()
        except:
            pass
        self._listener = listener(self)
        _address, _port = self._listener.start(address,port)
        if self._proxyAddr:
            self._initProxy()
        return (_address, _port)

    def stop(self):
        if not self._listener:
            log.debug('manager stop called, but no listener')
            return
        if self._proxyAddr:
            self._stopProxy()
        log.debug('manager stopping listener...')
        self._listener.stop()
        self._listener = None

    def shutdown(self):
        self.stop()
        self.appManager.shutdown()

    def getApplicationList(self):
        return self.appManager.appList.values()

    ##################################################################
    # session callback functions
    ##################################################################

    def onConnect(self, session, client, addr):
        # before any communication, we can decide if we want
        # to allow the connection here.  return 0 to deny
        log.info("Connection received from %r:%r",addr[0],addr[1])
        return 1

    def initHandler(self, session, init):
        # this is called once during a session, after the connection
        # to provide initialization information.  initNode is a
        # minidom node.  If we have a session key, it will be validated
        # later, and the key doesn't matter for us.
        if self._server_key and not init.getAttribute('session'):
            idekey = init.getAttribute('idekey')
            if idekey != self._server_key:
                session.stop()
                log.info("Session stopped, incorrect key [%s]", idekey)
                return 0
        self.appManager.getApplication(session)
        # XXX notify init listeners
        return 1

    def notifyInit(self, session, init):
        # should be overridden
        pass

    def notifyStartup(self, session, init):
        # should be overridden
        pass


class VimDebugger(manager):
    init = None
    session = None
    timeout = 10

    language = None
    startFile = None

    def __init__(self, timeout = 10):
        manager.__init__(self)
        self._resp_cv = threading.Condition()
        self.timeout = timeout

    def onConnect(self, session, client, addr):
        # before any communication, we can decide if we want
        # to allow the connection here.  return 0 to deny
        return 1

    def initHandler(self, session, init):
        # this is called once during a session, after the connection
        # to provide initialization information.  initNode is a
        # minidom node.  If we have a session key, it will be validated
        # later, and the key doesn't matter for us.
        self.init = init
        self.session = session
        self.language = init.attributes["language"].value
        self.startFile = init.attributes["fileuri"].value
        if self._server_key and not init.getAttribute('session'):
            idekey = init.getAttribute('idekey')
            if idekey != self._server_key:
                session.stop()
                print "Session stopped, incorrect key [%s]" % idekey
                return 0
        self.appManager.getApplication(session)
        if self.language.upper() == "PHP":
            for key in PHP_FUNCTIONS:
                tmp = self.session.evalString("eval('%s')" % PHP_FUNCTIONS[key])
        self.session.featureSet("max_data", 1048576)
        # XXX notify init listeners
        return 1

    def notifyInit(self, session, init):
        self._resp_cv.acquire()
        self._resp_cv.notify()
        self._resp_cv.release()
        pass

    def notifyStartup(self, session, init):
        pass

    def listenWait(self, address, port):
        self._resp_cv.acquire()
        self.listen(address, port)
        self._resp_cv.wait(self.timeout)
        self._resp_cv.release()
        if self.init == None:
            self.shutdown()
            return False
        else:
            return True

    def getStartPoint(self):
        if self.init != None:
            return (self.startFile, 1)

    def shutdown(self):
        manager.shutdown(self)
        self.init = None
        self.session = None
        self.language = None
        self.startFile = None

    def isConnected(self):
        return self.init != None

    def phpEval(self, evalCode):
        evalText = "json_encode(__xdbg_get_value(%s))" % evalCode

        try:
            strOutput = self.session.evalString(evalText).value
        except Exception, e:
            print e
            return "Could not eval %s: %s" % (evalCode, e.msg)

        d=JSONDecoder()
        try:
            resp = d.decode(strOutput)
        except Exception, e:
            print e
            resp = "Could not eval code: %s" % evalCode

        if resp == 4370448544:
            return "Could not execute"
        return resp

    def phpWatch(self, varList):
        """ Expects a list of $var names (formatted that way)
        """
        list1 = []
        for item in varList:
            list1.append("(isset(%s) ? %s : null)" % (item, item))

        list1txt = ", ".join(list1)
        cmd = "__xdbg_get_objList(array(%s))" % list1txt
        strOutput = self.session.evalString(cmd).value
        d=JSONDecoder()
        try:
            resp = d.decode(strOutput)
        except Exception, e:
            print e
            resp = "Could not get watch list: %s" % e.msg

        return resp

PHP_FUNCTIONS = {
        "var_dump": 'function __xdbg_var_dump($var) { ob_start(); var_dump($var); $tmp = ob_get_contents(); ob_end_clean(); return $tmp; }',
        "print_r": 'function __xdbg_print_r($var) { ob_start(); print_r($var); $tmp = ob_get_contents(); ob_end_clean(); return $tmp; }',
        "run": 'function __xdbg_run($method) { ob_start(); $method(); $tmp = ob_get_contents(); ob_end_clean(); return $tmp; }',
        "get_value": r"""
function __xdbg_get_value($var, $maxDepth=3) {
    $return = null;
    $isObj = is_object($var);

    if ($isObj && in_array("Doctrine\\Common\\Collections\\Collection", class_implements($var))) {
        $var = $var->toArray();
    }

    if ($maxDepth > 0) {
        if (is_array($var)) {
            $return = array();

            foreach ($var as $k => $v) {
                $return[$k] = __xdbg_get_value($v, $maxDepth - 1);
            }
        } else if ($isObj) {
            if ($var instanceof \DateTime) {
                $return = $var->format("c");
            } else {
                $reflClass = new \ReflectionClass(get_class($var));
                $return = new \stdclass();
                $return->{"__CLASS__"} = get_class($var);

                if (is_a($var, "Doctrine\\ORM\\Proxy\\Proxy") && ! $var->__isInitialized__) {
                    $reflProperty = $reflClass->getProperty("_identifier");
                    $reflProperty->setAccessible(true);

                    foreach ($reflProperty->getValue($var) as $name => $value) {
                        $return->$name = __xdbg_get_value($value, $maxDepth - 1);
                    }
                } else {
                    $excludeProperties = array();

                    if (is_a($var, "Doctrine\\ORM\\Proxy\\Proxy")) {
                        $excludeProperties = array("_entityPersister", "__isInitialized__", "_identifier");

                        foreach ($reflClass->getProperties() as $reflProperty) {
                            $name  = $reflProperty->getName();

                            if ( ! in_array($name, $excludeProperties)) {
                                $reflProperty->setAccessible(true);

                                $return->$name = __xdbg_get_value($reflProperty->getValue($var), $maxDepth - 1);
                            }
                        }
                    } else {
                        $return = $var;
                    }
                }
                $return = __xdbg_get_object($return, $maxDepth-1);
            }
        } else {
            $return = $var;
        }
    } else {
        $return = is_object($var) ? get_class($var)
            : (is_array($var) ? "Array(" . count($var) . ")" : $var);
    }

    return $return;
}""",
    "get_propertyList": """
function __xdbg_get_propertyList($propList, $item, $maxDepth=2) {
    $output = array();
    foreach ($propList as $prop) {
        $static = $prop->isStatic() ? "static " : "";
        $vis = $prop->isProtected() ? "protected" : $prop->isPrivate() ? "private" : "public";
        $name = $prop->getName();
        $val = null;
        if (!$prop->isPublic()) {
            $prop->setAccessible(true);
            $val = $prop->getValue($item);
            $prop->setAccessible(false);
        } else {
            $val = $prop->getValue($item);
        }
        $desc = $static."$vis \$$name";
        $output[$desc] = __xdbg_get_value($val, $maxDepth);
    }
    ksort($output);
    return $output;
}""",
    "get_methodList": """
function __xdbg_get_methodList($methodList, $className) {
    $output = array();
    foreach ($methodList as $method) {
        $static = $method->isStatic() ? "static " : "";
        $vis = $method->isPrivate() ? "private" : $method->isProtected() ? "protected" : "public";
        $name = $method->getName();
        $params = array();
        $plist = $method->getParameters();
        foreach ($plist as $param) {
            $params[] = "$" . $param->getName();
        }
        $desc = $static."$vis $name(" . implode(", ", $params) . ");";
        if ($method->getDeclaringClass()->getName() != $className) {
            $desc .= "  // inherited from " . $method->getDeclaringClass()->getName();
        }
        $output[$desc] = array($method->getFileName(), $method->getStartLine());
    }
    ksort($output);
    return $output;
}""",
    "get_object": """
function __xdbg_get_object($var, $maxDepth=3) {
    $entry = array();
    $class = get_class($var);
    $ref = new ReflectionClass($var);
    $entry = array(
        "properties" => __xdbg_get_propertyList($ref->getProperties(), $var, $maxDepth-1),
        "methods" => __xdbg_get_methodList($ref->getMethods(), $ref->getName()),
        "className" => $class,
        "isClass" => true,
    );
    return $entry;
}""",
    "get_objList": """
function __xdbg_get_objList(array $list) {
    $outputFull = array();
    foreach ($list as $item) {
        $outputFull[] = __xdbg_get_value($item);
    }
    return @json_encode($outputFull);
}""",
        "evalWatch": """
function __xdbg_evalWatch($method) {
    ob_start();
    $ret = $method();
    $tmp = ob_get_contents();
    ob_end_clean();
    return empty($tmp) ? $ret : $tmp;
}""",
}
