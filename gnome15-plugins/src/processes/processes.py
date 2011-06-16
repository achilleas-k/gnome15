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
import gnome15.g15plugin as g15plugin
import os
import dbus
import time
import gobject
import gtop

from Xlib import X
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
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_Z10, g15driver.MODEL_G11 ]
reserved_keys = [ g15driver.G_KEY_SETTINGS ]

def create(gconf_key, gconf_client, screen):
    return G15Processes(gconf_client, gconf_key, screen)

class ProcessMenuItem(g15theme.MenuItem):
    
    def __init__(self,  item_id, plugin, process_id, process_name):
        g15theme.MenuItem.__init__(self, item_id)
        self.icon = None
        self.process_id = process_id
        self.process_name = process_name
        self.plugin = plugin
    
    def get_default_theme_dir(self):
        return os.path.join(os.path.dirname(__file__), "default")
        
    def get_theme_properties(self):        
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self.process_name if len(self.process_name) > 0 else "Unamed" 
        if isinstance(self.process_id, int):
            item_properties["item_alt"] = self.process_id
        else:
            item_properties["item_alt"] = ""
        item_properties["item_type"] = ""
        item_properties["item_icon"] = self.icon
        return item_properties
    
    def activate(self):
        kill_name = str(self.process_id) if isinstance(self.process_id, int) else self.process_name 
        g15theme.ConfirmationScreen(self.get_screen(), "Kill Process", "Are you sure you want to kill %s" % kill_name,  
                                    g15util.get_icon_path("utilities-system-monitor"), self.plugin._kill_process, self.process_id)
        
                    
     
class G15Processes(g15plugin.G15MenuPlugin):

    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15MenuPlugin.__init__(self, gconf_client, gconf_key, screen, ["utilities-system-monitor"], id, name)
        self.i = 0
        
        # Can't work out how to kill an application/window given its XID, so only wnck is used for killing
        self.session_bus = dbus.SessionBus()
        self.bamf_matcher = None
#        try :
#            self.bamf_matcher = self.session_bus.get_object("org.ayatana.bamf", '/org/ayatana/bamf/matcher')
#        except:
#            logger.warning("BAMF not available, falling back to WNCK")

    def activate(self):
        self._modes = [ "applications", "all", "user" ]
        self._mode = "applications"
        self._timer = None
        g15plugin.G15MenuPlugin.activate(self)
            
    def deactivate(self):
        g15plugin.G15MenuPlugin.deactivate(self)
        
    def load_menu_items(self):
        pass
        
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_DOWN:              
            if self.screen.get_visible_page() == self.page:                    
                if g15plugin.G15MenuPlugin.handle_key(self, keys, state, post):
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
    
    def create_menu(self):
        menu = g15plugin.G15MenuPlugin.create_menu(self)
        menu.on_move = self._reschedule
        return menu
    
    def create_page(self):
        page = g15plugin.G15MenuPlugin.create_page(self)
        page.on_shown = self._page_shown
        page.on_hidden = self._page_hidden
        return page
    
    def get_theme_properties(self):
        props = g15plugin.G15MenuPlugin.get_theme_properties(self)
        
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
        return props
        
    '''
    Private
    '''

    def _send_event(self, win, ctype, data, mask=None):
        """ Send a ClientMessage event to the root """
        data = (data+[0]*(5-len(data)))[:5]
        ev = Xlib.protocol.event.ClientMessage(window=win, client_type=ctype, data=(32,(data)))
    
        if not mask:
            mask = (X.SubstructureRedirectMask|X.SubstructureNotifyMask)
        
        display = self.screen.service.get_x_display()
        screen = display.screen()
        root = screen.root

        root.send_event(ev, event_mask=mask)
        display.flush()
            
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

    def _get_process_name(self, args, cmd):
        result = cmd
        for i in range(min(2, len(args))):
            basename = os.path.basename(args[i])
            if basename.find(cmd) != -1:
                result = basename
                break
        return result

    def _reload_menu(self):
        gobject.idle_add(self._do_reload_menu)
        
    def _do_reload_menu(self):
        
        # Get the new list of active applications / processes
        current_items = list(self.menu.get_children())
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
                    if pid > 0 and not pid in item_map:
                        item = ProcessMenuItem("process-%d" % len(items), self, pid, window.get_name())
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
                        item = ProcessMenuItem("process-%d" % len(items), self, pid, self._get_process_name(proc_args, proc_state.cmd))
                        items.append(item)
                        item_map[pid] = item
                    elif proc_state.uid == os.getuid():
                        item = ProcessMenuItem("process-%d" % len(items), pid, self._get_process_name(proc_args, proc_state.cmd))
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
        self.menu.set_children(current_items)
        
        # Make sure selected still exists
        if self.menu.selected != None and not self.menu.selected in current_items:
            if len(current_items) > 0:
                self.menu.selected  = current_items[0]
            else:
                self.menu.selected = None

        self.screen.redraw(self.page)
        
    def _on_move(self):
        self._reschedule()
        
    def _on_selected(self):
        self.screen.redraw(self.page)
        
    def _page_shown(self):
        logger.debug("Process list activated")
        self._reload_menu()  
        self._schedule_refresh()
        
    def _page_hidden(self):
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