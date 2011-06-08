#!/usr/bin/env python
 
#        +-----------------------------------------------------------------------------+
#        | GPL                                                                         |
#        +-----------------------------------------------------------------------------+
#        | Copyright (c) Brett Smith <tanktarta@blueyonder.co.uk>                      |
#        |                                                                             |
#        | This program is free software; you can redistribute it and/or               |
#        | modify it under the terms of the GNU General Public License                 |
#        | as published by the Free Software Foundation; either version 2              |
#        | of the License, or (at your option) any later version.                      |
#        |                                                                             |
#        | This program is distributed in the hope that it will be useful,             |
#        | but WITHOUT ANY WARRANTY; without even the implied warranty of              |
#        | MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               |
#        | GNU General Public License for more details.                                |
#        |                                                                             |
#        | You should have received a copy of the GNU General Public License           |
#        | along with this program; if not, write to the Free Software                 |
#        | Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA. |
#        +-----------------------------------------------------------------------------+
  
import gnome15.g15screen as g15screen 
import gnome15.g15theme as g15theme 
import gnome15.g15util as g15util
import gnome15.g15driver as g15driver
import gnome15.g15profile as g15profile
import datetime
from threading import Timer
import gtk
import os
import sys
import time
import logging
logger = logging.getLogger("macros")

from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.protocol import rq

from threading import Thread

# Plugin details - All of these must be provided
id="macro-recorder"
name="Macro Recorder"
description="Allows recording of macros. All feedback is provided via the LCD (when available), " \
    + "as well as blinking of memory bank lights when recording. " + \
    "You may also delete macros by assigning an empty macro to a key." \
    + "The macro will be recorded on the currently selected profile and memory bank."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_Z10 ]
reserved_keys = [ g15driver.G_KEY_MR ]


local_dpy = display.Display()
record_dpy = display.Display()

def create(gconf_key, gconf_client, screen):
    return G15MacroRecorder(gconf_key, gconf_client, screen)


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
        
class MacroRecorderScreenChangeListener(g15screen.ScreenChangeAdapter):
    def __init__(self, plugin):
        self._plugin = plugin
        
    def memory_bank_changed(self, new_bank_number):
        self._plugin._redraw()

class G15MacroRecorder():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._record_key = None
        self._record_thread = None
        self._last_keys = None
        self._page = None
        self._key_down = None
        self._message = None
        self._lights_control = None
    
    def activate(self):
        self._reload_theme()
        self._listener = MacroRecorderScreenChangeListener(self)
        self._screen.add_screen_change_listener(self._listener)
    
    def deactivate(self):
        self._cancel_macro()
        self._screen.remove_screen_change_listener(self._listener)
        
    def destroy(self):
        if self._record_thread != None:
            self._record_thread.disable_record_context()
    
    def handle_key(self, keys, state, post):    
        if not post and state == g15driver.KEY_STATE_DOWN:
            # Memory keys
            if g15driver.G_KEY_MR in keys:              
                if self._record_thread != None:
                    self._cancel_macro(None)
                else:
                    self._start_recording()
                return True
            elif g15driver.G_KEY_M1 in keys or g15driver.G_KEY_M2 in keys or g15driver.G_KEY_M3 in keys:
                pass
            else:
                # All other keys end recording
                self._last_keys = keys                    
                if self._record_thread != None:
                    self._record_keys = keys
                    self._done_recording()
                    return True
                
        return False
                
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
                delay = 0
                if self._key_down == None:
                    self._key_down = time.time()
                else :
                    
                    now = time.time()
                    delay = time.time() - self._key_down
                    self._script_model.append(["Delay", str(int(delay * 1000))])
                    self._key_down = now
                
                logger.debug("Event detail = %s" % event.detail)
                keysym = local_dpy.keycode_to_keysym(event.detail, 0)
                if not keysym:
                    logger.debug("Recorded %s" % event.detail)
                    self._script_model.append([pr, event.detail])
                else:
                    logger.debug("Keysym = %s" % str(keysym))
                    s = self._lookup_keysym(keysym)
                    logger.debug("Recorded %s" % s)
                    self._script_model.append([pr, s])
                self._redraw()
            
    def _done_recording(self):
        if self._record_keys != None:
            record_keys = self._record_keys    
            self._halt_recorder()   
              
            active_profile = g15profile.get_active_profile(self._screen.device)
            key_name = ", ".join(g15util.get_key_names(record_keys))
            if len(self._script_model) == 0:  
                self.icon = "edit-delete"
                self._message = key_name + " deleted"
                active_profile.delete_macro(self._screen.get_mkey(), record_keys)  
                self._screen.redraw(self._page)   
            else:
                macro_script = ""
                for row in self._script_model:
                    if len(macro_script) != 0:                    
                        macro_script += "\n"
                    macro_script += row[0] + " " + row[1]       
                self.icon = "tag-new"   
                self._message = key_name + " created"
                memory = self._screen.get_mkey()
                macro = active_profile.get_macro(memory, record_keys)
                if macro:
                    macro.type = g15profile.MACRO_SCRIPT
                    macro.macro = macro_script
                    macro.save()
                else:                
                    active_profile.create_macro(memory, record_keys, key_name, g15profile.MACRO_SCRIPT, macro_script)
                self._redraw()
            self._hide_recorder(3.0)    
        else:
            self._hide_recorder()

    def _hide_recorder(self, after = 0.0):
        if self._lights_control:
            self._screen.release_defeat_profile_change()
            self._screen.driver.release_mkey_lights(self._lights_control)
            self._lights_control = None
        if self._page:
            if after == 0.0:   
                self._screen.del_page(self._page)
            else:
                self._screen.delete_after(after, self._page)
            self._page = None 
            
    def _halt_recorder(self):        
        if self._record_thread != None:
            self._record_thread.disable_record_context()
        self._key_down = None
        self._record_key = None
        self._record_thread = None
        
    def _cancel_macro(self,event = None,data=None):
        self._halt_recorder()
        self._hide_recorder()
        
    def _redraw(self):
        if self._page != None:
            self._screen.redraw(self._page)     
        
    def _reload_theme(self):        
        self._theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self._screen)
    
    def _start_recording(self):      
        self._script_model = []      
        if self._screen.device.bpp > 0:
            self._page = self._screen.get_page("Macro Recorder")
            if self._page == None:
                self._page = self._screen.new_page(self._paint, priority=g15screen.PRI_EXCLUSIVE,  id="Macro Recorder")
            self._page.title = "Macro Recorder"
        self.icon = "media-record"
        self._message = None
        self._redraw()
        self._record_thread = RecordThread(self._record_callback)
        self._record_thread.start()
        self._lights_control = self._screen.driver.acquire_mkey_lights()
        self._lights_control.set_mkey_lights(self._screen.get_mkey() | g15driver.MKEY_LIGHT_MR)
        self._lights_control.blink(0, 0.5)
        self._screen.request_defeat_profile_change()
        
    def _paint(self, canvas):
        
        active_profile = g15profile.get_active_profile(self._screen.device)
        
        properties = {}
        properties["icon"] = g15util.get_icon_path(self.icon, self._screen.height)
        properties["memory"] = "M%d" % self._screen.get_mkey()
            
        if active_profile != None:
            properties["profile"] = active_profile.name
            properties["profile_icon"] = active_profile.icon
            
            if self._message == None:
                properties["message"] = "Recording on M%s. Type in your macro then press the G-Key to assign it to, or MR to cancel." % self._screen.get_mkey()
            else:
                properties["message"] = self._message
        else:
            properties["profile"] = "No Profile"
            properties["profile_icon"] = ""
            properties["message"] = "You have no profiles configured. Configure one now using the Macro tool"
            
        self._theme.draw(canvas, properties)