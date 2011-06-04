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
 
import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15screen as g15screen
import gnome15.g15globals as g15globals
import os
import sys
import dbus
import cairo
import traceback
import base64
import time
import gtop
from cStringIO import StringIO

from Xlib import X, display, error, Xatom, Xutil
import Xlib.protocol.event

import logging
logger = logging.getLogger("processes")

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

class ProcessMenuItem(g15theme.MenuItem):
    
    def __init__(self,  process_id, process_name):
        g15theme.MenuItem.__init__(self, "menuitem")
        self.icon = None
        self.process_id = process_id
        self.process_name = process_name
        
    def draw(self, selected, canvas, menu_properties, menu_attributes):        
        item_properties = {}
        if selected == self:
            item_properties["item_selected"] = True
        item_properties["item_name"] = self.process_name if len(self.process_name) > 0 else "Unamed" 
        if isinstance(self.process_id, int):
            item_properties["item_alt"] = self.process_id
        else:
            item_properties["item_alt"] = ""
        item_properties["item_type"] = ""
        item_properties["item_icon"] = self.icon
        self.theme.draw(canvas, item_properties)
        return self.theme.bounds[3]

class G15Processes():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self._screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.i = 0
        
        # Connection to BAMF for running applications list
        self.bamf_matcher = None
        
        # Can't work out how to kill an application/window given its XID, so only wnck is used for killing
        self.session_bus = dbus.SessionBus()
#        try :
#            self.bamf_matcher = self.session_bus.get_object("org.ayatana.bamf", '/org/ayatana/bamf/matcher')
#        except:
#            logger.warning("BAMF not available, falling back to WNCK")
    
    def activate(self):
        self._modes = [ "applications", "all", "user" ]
        self._mode = "applications"
        self._reload_theme()
        self._timer = None
        self._page = None
        self._menu.selected = None
        self._show_menu()
    
    def deactivate(self):
        if self._page != None:
            self._hide_menu()
        
    def destroy(self):
        pass
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_DOWN:              
            if self._screen.get_visible_page() == self._page:                    
                if self._menu.handle_key(keys, state, post):
                     True  
                elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                    self._reschedule()
                    if self._menu.selected != None:
                        kill_name = str(self._menu.selected.process_id) if isinstance(self._menu.selected.process_id, int) else self._menu.selected.process_name 
                        g15theme.ConfirmationScreen(self._screen, "Kill Process", "Are you sure you want to kill %s" % kill_name,  
                                                    g15util.get_icon_path("utilities-system-monitor"), self._kill_process, self._menu.selected.process_id)
                    
                    return True
                elif g15driver.G_KEY_L3 in keys or g15driver.G_KEY_SETTINGS in keys:
                    if self._mode == "applications":
                        self._mode = "all"
                    elif self._mode == "all":
                        self._mode = "user"
                    elif self._mode == "user":
                        self._mode = "applications"
                    self._cancel_timer()
                    self._refresh()
                
        return False
    
    '''
    Private
    '''

    def _send_event(win, ctype, data, mask=None):
        """ Send a ClientMessage event to the root """
        data = (data+[0]*(5-len(data)))[:5]
        ev = Xlib.protocol.event.ClientMessage(window=win, client_type=ctype, data=(32,(data)))
    
        if not mask:
            mask = (X.SubstructureRedirectMask|X.SubstructureNotifyMask)
        
        display = self._screen.service.get_x_display()
        screen = display.screen()
        root = screen.root

        root.send_event(ev, event_mask=mask)
        display.flush()
    
    def _check_selected(self):
        items = self._menu.get_items()
        if not self._menu.selected in items:
            if self.i > len(items):
                return
            self._menu.selected = items[self.i]
            
    def _do_selected(self):
        self._menu.selected = self._menu.get_items()[self.i]
        self._screen.service.resched_cycle()
        self._screen.redraw(self._page)
        
    def _move_up(self, amount = 1):
        self._reschedule()
        self._check_selected()
        items = self._menu.get_items()
        self.i = items.index(self._menu.selected)
        self.i -= amount
        if self.i < 0:
            self.i = len(items) - 1
        self._do_selected()
        
    def _move_down(self, amount = 1):
        self._reschedule()
        self._check_selected()
        items = self._menu.items
        self.i = items.index(self._menu.selected)
        self.i += amount
        if self.i >= len(items):
            self.i = 0
        self._do_selected()
    
    def _kill_process(self, process_id):
        if isinstance(process_id, int):
            os.system("kill %d" % process_id)
            time.sleep(0.5)
            if process_id in gtop.proclist():
                time.sleep(5.0)
                if process_id in gtop.proclist():
                    os.system("kill -9 %d" % process_id)
        else:
            # TODO kill using XID if possible
            pass
        self._reload_menu()        
    
    def paint(self, canvas):
        props = { "icon" : g15util.get_icon_path("utilities-system-monitor") }
        
        props["mode"] = self._mode
        if self._mode == "applications":
            props["title"] = "Applications"
            props["list"] = "All"
        elif self._mode == "all":
            props["title"] = "All Processes"
            props["list"] = "Usr"
        elif self._mode == "user":
            props["title"] = "User Processes"
            props["list"] = "App"
        
        self._theme.draw(canvas, 
                        props, 
                        attributes = {
                                      "items" : self._menu.get_items(),
                                      "selected" : self._menu.selected
                                      })
        
    '''
    Private
    '''

    def _get_process_name(self, args, cmd):
        result = cmd
        for i in range(min(2, len(args))):
            basename = os.path.basename(args[i])
            if basename.find(cmd) != -1:
                result = basename
                break
        return result

    def _reload_menu(self):
        
        # Get the new list of active applications / processes
        item_map = {}
        current_items = list(self._menu.get_items())
        current_item_map = {}
        for item in current_items:
            current_item_map[item.process_id] = item
        items = []
        item_map = {}
        
        if self._mode == "applications":
            if self.bamf_matcher != None:            
                for window in self.bamf_matcher.RunningApplications():
                    app = self.session_bus.get_object("org.ayatana.bamf", window)
                    view = dbus.Interface(app, 'org.ayatana.bamf.view')
                    application = dbus.Interface(app, 'org.ayatana.bamf.application')
                    xids = []
                    for i in application.Xids():
                        xids.append(int(i))
                    item = ProcessMenuItem(xids, view.Name())
                    icon_name = view.Icon()
                    if icon_name and len(icon_name) > 0:
                        icon_path = g15util.get_icon_path(icon_name, warning = False)
                        if icon_path:
                            item.icon = "file:" + icon_path
                    items.append(item)
                    item_map[str(item.process_id)] = item
            else:
                import wnck
                screen = wnck.screen_get_default()
                for window in screen.get_windows():
                    pid = window.get_pid()
                    if pid > 0:
                        item = ProcessMenuItem(pid, window.get_name())
                        if window.has_icon_name():
                            icon_path = g15util.get_icon_path(window.get_icon_name(), warning = False)
                            if icon_path:
                                item.icon = "file:" + icon_path
                        if item.icon == None:
                            pixbuf = window.get_icon()
                            if pixbuf:               
                                item.icon = g15util.pixbuf_to_surface(pixbuf)
                                
                        items.append(item)
                        item_map[item.process_id] = item
        else:
            for process_id in gtop.proclist():
                process_id = "%d" %  process_id
                try :
                    pid = int(process_id)
                    proc_state = gtop.proc_state(pid)
                    proc_args = gtop.proc_args(pid)

                    if self._mode == "all":
                        item = ProcessMenuItem(pid, self._get_process_name(proc_args, proc_state.cmd))
                        items.append(item)
                        item_map[pid] = item
                    elif proc_state.uid == os.getuid():
                        item = ProcessMenuItem(pid, self._get_process_name(proc_args, proc_state.cmd))
                        item_map[pid] = item
                        items.append(item)
                except :
                    # In case the process disappears
                    pass
 
        # Remove any missing items
        for item in current_items:
            if not item.process_id in item_map:
                current_items.remove(item)
                
        # Insert new items
        for item in items:
            if not item.process_id in current_item_map:
                current_items.append(item)
            else:
                # Update existing items
                current_item = current_item_map[item.process_id]
                current_item.process_name = item.process_name
                current_item.icon = item.icon 
                
        # Sort
        current_items = sorted(current_items, key=lambda item: item.process_name)
        self._menu.set_items(current_items)
        
        # Make sure selected still exists
        if self._menu.selected != None and not self._menu.selected in current_items:
            if len(current_items) > 0:
                self._menu.selected  = current_items[0]
            else:
                self._menu.selected = None

        self._screen.redraw(self._page)
        
    def _reload_theme(self):
        self._theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self._screen)
        self._menu = g15theme.Menu("menu", self._screen)
        self._menu.on_selected = self._on_selected
        self._menu.on_move = self._on_move
        self._theme.add_component(self._menu)
        self._theme.add_component(g15theme.Scrollbar("viewScrollbar", self._menu.get_scroll_values))
        
    def _on_move(self):
        self._reschedule()
        
    def _on_selected(self):
        self._screen.redraw(self._page)
        
    def _show_menu(self):        
        self._page = self._screen.new_page(self.paint, id=name, priority = g15screen.PRI_NORMAL,  on_shown=self._page_shown, on_hidden=self._page_hidden)
        self._screen.redraw(self._page)
        
    def _page_shown(self):
        logger.debug("Process list activated")
        self._reload_menu()  
        self._schedule_refresh()
        
    def _page_hidden(self):
        self._cancel_timer()
    
    def _hide_menu(self):     
        self._screen.del_page(self._page)
        self._page = None
        self._cancel_timer()
        
    def _refresh(self):
        self._reload_menu()
        self._schedule_refresh()
        
    def _cancel_timer(self):
        if self._timer != None:
            logger.debug("Stopping refreshing process list")
            self._timer.cancel()
        
    def _reschedule(self):
        self._cancel_timer()
        self._schedule_refresh()
        
    def _schedule_refresh(self):
        self._timer = g15util.schedule("ProcessesRefresh", 5.0, self._refresh)