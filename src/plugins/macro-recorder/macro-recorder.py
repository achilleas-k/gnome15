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
  
import gnome15.g15_screen as g15screen 
import gnome15.g15_theme as g15theme 
import gnome15.g15_util as g15util
import gnome15.g15_driver as g15driver
import gnome15.g15_profile as g15profile
import datetime
from threading import Timer
import gtk
import os
import sys
import time

from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.protocol import rq

from threading import Thread

# Plugin details - All of these must be provided
id="macro-recorder"
name="Macro Recorder"
description="Allows recording of macros. All feedback is provided on the LCD. " \
    + "You may also delete macros by assigning an empty macro to a key." \
    + "The macro will be recorded on the currently profile and memory bank."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False


local_dpy = display.Display()
record_dpy = display.Display()

def create(gconf_key, gconf_client, screen):
    return G15MacroRecorder(gconf_key, gconf_client, screen)


class RecordThread(Thread):
    def __init__(self, record_callback):
        Thread.__init__(self)
        self.setDaemon(True)
        self.name = "RecordThread"
        self.record_callback = record_callback  
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
        record_dpy.record_enable_context(self.ctx, self.record_callback)
        record_dpy.record_free_context(self.ctx)

class G15MacroRecorder():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.hide_timer = None
        self.record_key = None
        self.record_thread = None
        self.last_keys = None
        self.page = None
        self.key_down = None
        self.script_model = []
    
    def activate(self):
        self.reload_theme()
    
    def deactivate(self):
        pass
        
    def destroy(self):
        if self.record_thread != None:
            self.record_thread.disable_record_context()
    
    def handle_key(self, keys, state, post):    
        if not post and state == g15driver.KEY_STATE_UP:
            # Memory keys
            if self.page != None and ( g15driver.G_KEY_M1 in keys or g15driver.G_KEY_M2 in keys or g15driver.G_KEY_M3 in keys ):
                self.screen.redraw(self.page)
                return False
            # Set recording
            elif g15driver.G_KEY_MR in keys:              
                if self.record_thread != None:
                    self.cancel_macro(None)
                else:
                    self.start_recording()
                return True
            else:
                self.last_keys = keys                    
                if self.record_thread != None:
                    self.record_keys = keys
                    self.done_recording()
                    return True
                
        return False
    
    def start_recording(self):
        if self.hide_timer != None:
            self.hide_timer.cancel()
            self.hide_recorder(0.0)    
            
        self.page = self.screen.new_page(self.paint, priority=g15screen.PRI_EXCLUSIVE,  id="Macro Recorder", use_cairo="True")
        self.icon = "media-record"
        self.message = None
        self.screen.redraw(self.page)
        
        self.record_thread = RecordThread(self.record_callback)
        self.record_thread.start()
        
    def paint(self, canvas):
        
        active_profile = g15profile.get_active_profile()
        
        properties = {}
        properties["icon"] = g15util.get_icon_path(self.gconf_client, self.icon, self.screen.height)
        properties["profile"] = active_profile.name
        properties["profile_icon"] = active_profile.icon
        properties["memory"] = "M%d" % self.screen.get_mkey()
        
        if self.message == None:
            properties["message"] = "Recording on M%s. Type in your macro then press the G-Key to assign it to, or MR to cancel." % self.screen.get_mkey()
        else:
            properties["message"] = self.message
            
        self.theme.draw(canvas, properties)  
        
    def cancel_macro(self,event,data=None):
        self.halt_recorder()
        self.hide_recorder()

    def hide_recorder(self, after = 0.0):
        if after == 0.0:
            self.screen.del_page(self.page)
            self.page = None
            self.hide_timer = None 
        else:
            self.hide_timer = self.screen.hide_after(after, self.page)
            
    def halt_recorder(self):        
        if self.record_thread != None:
            self.record_thread.disable_record_context()
        self.key_down = None
        self.record_key = None
        self.record_thread = None
            
    def done_recording(self):
        if self.record_keys != None:   
            active_profile = g15profile.get_active_profile()
            key_name = ", ".join(g15util.get_key_names(self.record_keys))
            print list(self.script_model)
            if len(self.script_model) == 0:  
                self.icon = "edit-delete"
                self.message = key_name + " deleted"
                active_profile.delete_macro(self.screen.get_mkey(), self.record_keys)
                self.screen.redraw(self.page)                
            else:
                str = ""
                for row in self.script_model:
                    if len(str) != 0:                    
                        str += "\n"
                    str += row[0] + " " + row[1]       
                self.icon = "tag-new"   
                self.message = key_name + " created"                
                active_profile.create_macro(self.screen.get_mkey(), self.record_keys, key_name, str)
                self.screen.redraw(self.page)
            self.halt_recorder()
            self.hide_recorder(3.0)    
        else:
            self.hide_recorder()     
        
    def reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
    
    def lookup_keysym(self, keysym):
        for name in dir(XK):
                if name[:3] == "XK_" and getattr(XK, name) == keysym:
                    return name[3:]
        return "[%d]" % keysym
    
    def record_callback(self, reply):
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
                if self.key_down == None:
                    self.key_down = time.time()
                else :
                    now = time.time()
                    delay = time.time() - self.key_down
                    self.script_model.append(["Delay", str(int(delay * 1000))])
                    self.key_down = now
                
                keysym = local_dpy.keycode_to_keysym(event.detail, 0)
                if not keysym:
                    self.script_model.append([pr, event.detail])
                else:
                    self.script_model.append([pr, self.lookup_keysym(keysym)])
                self.screen.redraw(self.page)