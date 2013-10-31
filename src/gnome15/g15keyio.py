#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2012 Brett Smith <tanktarta@blueyonder.co.uk>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Classes and functions for recording X key presses using either raw X events 
or XTEST as well as injecting such keys
"""  

import gnome15.g15locale as g15locale
import gnome15.g15uinput as g15uinput
_ = g15locale.get_translation("macro-recorder", modfile = __file__).ugettext

import time
import logging
logger = logging.getLogger(__name__)
 
from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.protocol import rq

from threading import Thread

local_dpy = display.Display()
record_dpy = display.Display()
        
def get_keysyms():
    l = []
    for name in dir(XK):
        logger.debug("   %s" % name)
        if name[:3] == "XK_":
            l.append(name[3:])
    return l

class RecordThread(Thread):
    def __init__(self, _record_callback):
        Thread.__init__(self)
        self.setDaemon(True)
        self.name = "RecordThread"
        self._record_callback = _record_callback  
        self.ctx = record_dpy.record_create_context(
                                0,
                                [record.AllClients],
                                [{
                                  'core_requests': (0, 0),
                                  'core_replies': (0, 0),
                                  'ext_requests': (0, 0, 0, 0),
                                  'ext_replies': (0, 0, 0, 0),
                                  'delivered_events': (0, 0),
                                  'device_events': (X.KeyPress, X.MotionNotify),
                                  'errors': (0, 0),
                                  'client_started': False,
                                  'client_died': False,
                                  }])

    def disable_record_context(self):
        if self.ctx != None:            
            local_dpy.record_disable_context(self.ctx)
            local_dpy.flush()
        
    def run(self):      
        record_dpy.record_enable_context(self.ctx, self._record_callback)
        record_dpy.record_free_context(self.ctx)
        
class G15KeyRecorder():
    
    def __init__(self, driver):
        self._driver = driver
        self._record_key = None
        self._record_thread = None
        self._last_keys = None
        self._key_down = None
        
        self.script = []
        self.on_add = None
        self.on_stop = None
        self.single_key = False
        self.output_delays = True
        self.emit_uinput = False
        
    def clear(self):
        del self.script[:]
        
    def is_recording(self):
        return self._record_thread is not None
    
    def start_record(self):
        if self._record_thread is None:
            self._start_recording()
            return True
        else:
            self._cancel_macro(None)
            return True
    
    '''
    Private
    ''' 
    
    def _lookup_keysym(self, keysym):
        logger.debug("Looking up %s" % keysym)
        for name in dir(XK):
            logger.debug("   %s" % name)
            if name[:3] == "XK_" and getattr(XK, name) == keysym:
                return name[3:]
        return "[%d]" % keysym
    
    def _record_callback(self, reply):
        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            return
        if not len(reply.data) or ord(reply.data[0]) < 2:
            # not an event
            return
        
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, record_dpy.display, None, None)
            if event.type in [X.KeyPress, X.KeyRelease]:
                pr = event.type == X.KeyPress and "Press" or "Release"
                logger.debug("Event detail = %s" % event.detail)
                keysym = local_dpy.keycode_to_keysym(event.detail, 0)
                if not keysym:
                    logger.debug("Recorded %s" % event.detail)  
                    self._record_key_callback(event, event.detail)                    
                else:
                    logger.debug("Keysym = %s" % str(keysym))
                    s = self._lookup_keysym(keysym)
                    logger.debug("Recorded %s" % s)
                    self._record_key_callback(event, s)
                    
    def _record_key_callback(self, event, keyname):
        if self._key_down == None:
            self._key_down = time.time()
        else:
            now = time.time()
            delay = time.time() - self._key_down
            if self.output_delays:
                self.script.append(["Delay", str(int(delay * 1000))])
            self._key_down = now

        if self.emit_uinput:            
            pr = event.type == X.KeyPress and "UPress" or "URelease"
            keyname =  g15uinput.get_keysym_to_uinput_mapping(keyname)  + " " + g15uinput.KEYBOARD
            if keyname:
                for c in keyname.split(","):
                    self._add_key(pr, event, c)
        else:
            pr = event.type == X.KeyPress and "Press" or "Release"
            self._add_key(pr, event, keyname)
            

    def _add_key(self, pr, event, keyname):            
        keydown = self._key_state[keyname] if keyname in self._key_state else None
        if keydown is None:
            if event.type == X.KeyPress:
                self._key_state[keyname] = True
                self._add(pr, keyname)
            else:
                # Got a release without getting a press - ignore
                pass
        else:
            if event.type == X.KeyRelease:
                self._add(pr, keyname)
                del self._key_state[keyname]
                
                if self.single_key:
                    self.stop_record()
                    
    def _add(self, pr, keyname):
        self.script.append([pr, keyname])
        if self.on_add:
            self.on_add(pr, keyname)
            
    def _done_recording(self, state):
        if self._record_keys != None:
            self.stop_record()   

    def stop_record(self):        
        if self._record_thread != None:
            self._record_thread.disable_record_context()
        self._key_down = None
        self._record_key = None
        self._record_thread = None
        if self.on_stop is not None:
            self.on_stop(self)
        
    def _start_recording(self):      
        self.script = []
        self._key_state = {}
        self._key_down = None
        self._record_thread = RecordThread(self._record_callback)
        self._record_thread.start()
        
