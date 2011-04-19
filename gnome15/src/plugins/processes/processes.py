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
 
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
import gnome15.g15_driver as g15driver
import gnome15.g15_screen as g15screen
import gnome15.g15_globals as g15globals
import os
import sys
import dbus
import cairo
import traceback
import base64
import time
from cStringIO import StringIO

from Xlib import X, display, error, Xatom, Xutil
import Xlib.protocol.event

display = Xlib.display.Display()
screen = display.screen()
root = screen.root

# Plugin details - All of these must be provided
id="processes"
name="Process List"
description="Lists all running processes and allows them to be " + \
            "killed. through a menu on the LCD. On the G19 only, it " + \
            "may be activated by the <b>Settings</b> key."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_Z10 ]
reserved_keys = [ g15driver.G_KEY_SETTINGS ]

def create(gconf_key, gconf_client, screen):
    return G15Processes(gconf_client, gconf_key, screen)

def sendEvent(win, ctype, data, mask=None):
    """ Send a ClientMessage event to the root """
    data = (data+[0]*(5-len(data)))[:5]
    ev = Xlib.protocol.event.ClientMessage(window=win, client_type=ctype, data=(32,(data)))

    if not mask:
        mask = (X.SubstructureRedirectMask|X.SubstructureNotifyMask)
    root.send_event(ev, event_mask=mask)
    display.flush()

class MenuItem():
    
    def __init__(self, process_id, process_name):
        self.process_id = process_id
        self.process_name = process_name
        
class G15ProcessesMenu(g15theme.Menu):
    def __init__(self):
        g15theme.Menu.__init__(self, "menu")
        
    def render_item(self, item, selected, canvas, properties, attributes, group = False):        
        item_properties = {}
        if selected == item:
            item_properties["item_selected"] = True
        item_properties["item_name"] = os.path.basename(item.process_name) 
        item_properties["item_alt"] = item.process_id
        item_properties["item_type"] = ""
        item_properties["item_icon"] = ""
        self.entry_theme.draw(canvas, item_properties)
        return self.entry_theme.bounds[3]

class G15Processes():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.i = 0
        
        # Connection to BAMF for running applications list
        self.session_bus = dbus.SessionBus()
        try :
            self.bamf_matcher = self.session_bus.get_object("org.ayatana.bamf", '/org/ayatana/bamf/matcher')
        except:
            logger.warning("BAMF not available, falling back to WNCK")
            self.bamf_matcher = None
    
    def activate(self):
        self.modes = [ "applications", "owner", "all" ]
        self.mode = "applications"
        self._reload_theme()
        self.timer = None
        self.page = None
        self.selected = None
        self._show_menu()
    
    def deactivate(self):
        if self.page != None:
            self._hide_menu()
            
        
    def destroy(self):
        pass
    
    def _check_selected(self):
        if not self.selected in self.items:
            if self.i > len(self.items):
                return
            self.selected = self.items[self.i]
            
    def _do_selected(self):
        self.selected = self.items[self.i]
        self.screen.service.resched_cycle()
        self.screen.redraw(self.page)
        
    def _move_up(self, amount = 1):
        self._reschedule()
        self._check_selected()
        self.i = self.items.index(self.selected)
        self.i -= amount
        if self.i < 0:
            self.i = len(self.items) - 1
        self._do_selected()
        
    def _move_down(self, amount = 1):
        self._reschedule()
        self._check_selected()
        self.i = self.items.index(self.selected)
        self.i += amount
        if self.i >= len(self.items):
            self.i = 0
        self._do_selected()
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_DOWN:              
            if self.screen.get_visible_page() == self.page:                    
                if g15driver.G_KEY_UP in keys or g15driver.G_KEY_L3 in keys:
                    self._move_up(1)
                    return True
                elif g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L4 in keys:
                    self._move_down(1)
                    return True                              
                elif g15driver.G_KEY_RIGHT in keys:
                    self._move_down(10)
                    return True        
                elif g15driver.G_KEY_LEFT in keys:
                    self._move_up(10)
                    return True           
                elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                    self._reschedule()
                    if self.selected != None:
                        kill_name = str(self.selected.process_id) if isinstance(self.selected.process_id, int) else self.selected.process_name 
                        g15theme.ConfirmationScreen(self.screen, "Kill Process", "Are you sure you want to kill %s" % kill_name,  
                                                    g15util.get_icon_path("utilities-system-monitor"), self._kill_process, self.selected.process_id)
                    
                    return True
                elif g15driver.G_KEY_UP in keys or g15driver.G_KEY_SETTINGS in keys:
                    self._reschedule()
                    self.screen.set_priority(self.page, g15screen.PRI_NORMAL)
                
        return False
    
    def _kill_process(self, process_id):
        if isinstance(process_id, int):
            os.system("kill %d" % process_id)
            time.sleep(0.5)
            if os.path.exists("/proc/%d" % process_id):
                time.sleep(5.0)
                if os.path.exists("/proc/%d" % process_id):
                    os.system("kill -9 %d" % process_id)
        else:
            sendEvent(root, display.intern_atom("_NET_CURRENT_DESKTOP"), [1, X.CurrentTime])
        self._reload_menu()        
    
    def paint(self, canvas):
        self.menu.items = self.items
        self.menu.selected = self.selected
        
        self.theme.draw(canvas, 
                        properties = {
                                      "title" : name,
                                      "icon" : g15util.get_icon_path("utilities-system-monitor")
                                      }, 
                        attributes = {
                                      "items" : self.items,
                                      "selected" : self.selected
                                      })
        
    '''
    Private
    '''
            
    def _load_applications(self):        
        if self.bamf_matcher != None:            
            for window in self.bamf_matcher.RunningApplications():
                app = self.session_bus.get_object("org.ayatana.bamf", window)
                view = dbus.Interface(app, 'org.ayatana.bamf.view')
                application = dbus.Interface(app, 'org.ayatana.bamf.application')
                xids = []
                for i in application.Xids():
                    xids.append(int(i))
                self.items.append(MenuItem(xids, view.Name()))
        else:
            import wnck
            for window in wnck.screen_get_default().get_windows():
                self.items.append(MenuItem(window.get_process_id(), window.get_name()))
                
    def _reload_menu(self):
        self.items = []
        
        sel_pid = 0 if self.selected == None else self.selected.process_id 
        
        if self.mode == "applications":
            self._load_applications()
        else:
            for process_id in os.listdir("/proc"):
                if process_id.isdigit():
                    try :
                        stat_file = file("/proc/%s/cmdline" % process_id, "r")
                        try :
                            line = stat_file.readline().split("\0")
                            name = line[0]
                            if name != "":
                                if self.mode == "all":
                                    self.items.append(MenuItem(int(process_id), name))          
                                else:
                                    owner_stat = os.stat("/proc/%s/cmdline" % process_id)
                                    owner_uid = owner_stat[4]
                                    if owner_uid == os.getuid():
                                        pid = int(process_id)
                                        item = MenuItem(pid, name)
                                        self.items.append(item)
                                        if pid == sel_pid:
                                            self.selected = item
                                    
                                    
                        finally :
                            stat_file.close()
                    except :
                        # In case the process disappears
                        pass
                
        self.items = sorted(self.items, key=lambda item: item.process_name)
            
        if self.selected == None:
            self.selected = self.items[0]
        self.screen.redraw(self.page)
        
    def _reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(g15globals.themes_dir, "default"), self.screen, "menu-screen")
        self.menu = G15ProcessesMenu()
        self.theme.add_component(self.menu)
        self.theme.add_component(g15theme.Scrollbar("viewScrollbar", self.menu.get_scroll_values))
        
    def _show_menu(self):        
        self.page = self.screen.new_page(self.paint, id=name, priority = g15screen.PRI_NORMAL)
        self._reload_menu()  
        self._schedule_refresh()          
    
    def _hide_menu(self):     
        self.screen.del_page(self.page)
        self.page = None
        self.timer.cancel()
        
    def _refresh(self):
        self._reload_menu()
        self._schedule_refresh()
        
    def _reschedule(self):
        if self.timer != None:
            self.timer.cancel()
        self._schedule_refresh()
        
    def _schedule_refresh(self):
        self.timer = g15util.schedule("ProcessesRefresh", 5.0, self._refresh)