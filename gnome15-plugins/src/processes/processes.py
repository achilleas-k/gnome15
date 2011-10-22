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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("processes", modfile = __file__).ugettext

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
name=_("Process List")
description=_("Lists all running processes and allows them to be \
killed. through a menu on the LCD.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_Z10, g15driver.MODEL_G11 ]
reserved_keys = [ g15driver.G_KEY_SETTINGS ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous process"), 
         g15driver.NEXT_SELECTION : _("Next process"),
         g15driver.NEXT_PAGE : _("Next page"),
         g15driver.PREVIOUS_PAGE : _("Previous page"),
         g15driver.SELECT : _("Kill process"),
         g15driver.VIEW : _("Toggle between applications,\nall and user")
         }
 
def create(gconf_key, gconf_client, screen):
    return G15Processes(gconf_client, gconf_key, screen)

class ProcessMenuItem(g15theme.MenuItem):
    """
    MenuItem for individual processes
    """
    
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
        item_properties["item_name"] = self.process_name if self.process_name is not None and len(self.process_name) > 0 else "Unamed" 
        if isinstance(self.process_id, int):
            item_properties["item_alt"] = self.process_id
        else:
            item_properties["item_alt"] = ""
        item_properties["item_type"] = ""
        item_properties["item_icon"] = self.icon
        return item_properties
    
    def activate(self):
        kill_name = str(self.process_id) if isinstance(self.process_id, int) else self.process_name 
        self.plugin.confirm_screen = g15theme.ConfirmationScreen(self.get_screen(), _("Kill Process"), _("Are you sure you want to kill\n%s") % kill_name,  
                                    g15util.get_icon_path("utilities-system-monitor"), self.plugin._kill_process, self.process_id,
                                    cancel_callback = self.plugin._cancel_kill)
                    
     
class G15Processes(g15plugin.G15MenuPlugin):

    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15MenuPlugin.__init__(self, gconf_client, gconf_key, screen, ["utilities-system-monitor"], id, name)
        self.item_id = 0
        self.confirm_screen = None 
        
        # Can't work out how to kill an application/window given its XID, so only wnck is used for killing
        self.session_bus = dbus.SessionBus()
        self.bamf_matcher = None
        try :
            self.bamf_matcher = self.session_bus.get_object("org.ayatana.bamf", '/org/ayatana/bamf/matcher')
        except:
            logger.warning("BAMF not available, falling back to WNCK")

    def activate(self):
        self._modes = [ "applications", "all", "user" ]
        self._mode = "applications"
        self._timer = None
        self._matches = []
        g15plugin.G15MenuPlugin.activate(self)
        self.screen.key_handler.action_listeners.append(self)
        if self.bamf_matcher is not None:        
            self._matches.append(self.bamf_matcher.connect_to_signal("ViewOpened", self._view_opened))
            self._matches.append(self.bamf_matcher.connect_to_signal("ViewClosed", self._view_closed))
            
    def deactivate(self):
        g15plugin.G15MenuPlugin.deactivate(self)
        for m in self._matches:
            m.remove()
        self.screen.key_handler.action_listeners.remove(self)
        if self.confirm_screen is not None:
            self.confirm_screen.delete()
            self.confirm_screen = None
        
    def load_menu_items(self):
        pass
    
    def _get_next_id(self):
        self.item_id += 1
        return self.item_id
                    
    def action_performed(self, binding):        
        if self.page != None and self.page.is_visible(): 
            if binding.action == g15driver.VIEW:
                if self._mode == "applications":
                    self._mode = "all"
                elif self._mode == "all":
                    self._mode = "user"
                elif self._mode == "user":
                    self._mode = "applications"
                self._cancel_timer()
                self._refresh()
    
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
            props["title"] = _("Applications")
            props["list"] = _("All")
        elif self._mode == "all":
            props["title"] = _("All Processes")
            props["list"] = _("Usr")
        elif self._mode == "user":
            props["title"] = _("User Processes")
            props["list"] = _("App")
        return props
        
    '''
    Private
    '''
    def _view_opened(self, window_path, path_type):
        if path_type == "application":
            self._get_item_for_bamf_application(window_path)
        
    def _view_closed(self, window_path, path_type):
        if path_type == "application":
            self._remove_item_for_bamf_application(window_path)

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
    
    def _cancel_kill(self, process_id):
        self.confirmation_screen = None
        
    def _do_kill(self, process_id):
        os.system("kill %d" % process_id)
        time.sleep(0.5)
        if process_id in gtop.proclist():
            time.sleep(5.0)
            if process_id in gtop.proclist():
                os.system("kill -9 %d" % process_id)
            
    def _kill_process(self, process_id):
        if isinstance(process_id, int):
            self._do_kill(process_id)
        else:            
            gobject.idle_add(self._kill_window, process_id)
        self.confirmation_screen = None
        self._reload_menu()
        
    def _kill_window(self, window_path):
        import wnck
        import gtk
        window_names = self._get_window_names(window_path)
        screen = wnck.screen_get_default()
        while gtk.events_pending():
            gtk.main_iteration()
        windows = screen.get_windows()
        for window_name in window_names:
            for w in windows:
                if w.get_name() == window_name:
                    self._do_kill(w.get_pid())
                    return
        
    def _get_window_names(self, path, window_names = []):
        app = self.session_bus.get_object("org.ayatana.bamf", path)
        view = dbus.Interface(app, 'org.ayatana.bamf.view')
        window_names.append(view.Name())
        children = view.Children()
        for c in children:
            self._get_window_names(c, window_names)
        return window_names

    def _get_process_name(self, args, cmd):
        result = cmd
        for i in range(min(2, len(args))):
            basename = os.path.basename(args[i])
            if basename.find(cmd) != -1:
                result = basename
                break
        return result

    def _reload_menu(self):
        g15util.schedule("ReloadProcesses", 0, self._do_reload_menu)
        
    def _get_menu_item(self, pid):
        item = self.menu.get_child_by_id("process-%s" % pid)
        if item == None:
            item = ProcessMenuItem("process-%s" % pid, self, pid, None)
            self.menu.add_child(item)
        return item
    
    def _get_bamf_application_object(self, window):
        app = self.session_bus.get_object("org.ayatana.bamf", window)
        view = dbus.Interface(app, 'org.ayatana.bamf.view')
        return view
    
    def _remove_item_for_bamf_application(self, window):        
        item = self.menu.get_child_by_id("process-%s" % window)
        if item is not None:
            self.menu.remove_child(item)
    
    def _get_item_for_bamf_application(self, window):
        view = self._get_bamf_application_object(window)
        item = self._get_menu_item(window)
        item.process_name = view.Name()
        icon_name = view.Icon()
        if icon_name and len(icon_name) > 0:
            icon_path = g15util.get_icon_path(icon_name, warning = False)
            if icon_path:
                item.icon = g15util.load_surface_from_file(icon_path, 32) 
                
            
        return item
        
    def _do_reload_menu(self):
        this_items = {}        
        if self._mode == "applications":
            if self.bamf_matcher != None:            
                for window in self.bamf_matcher.RunningApplications():
                    item = self._get_item_for_bamf_application(window)                    
                    this_items[item.id] = item
            else:
                import wnck
                screen = wnck.screen_get_default()
                for window in screen.get_windows():
                    pid = window.get_pid()
                    if pid > 0:                        
                        item = self._get_menu_item(pid)
                        item.process_name = window.get_name()
                        this_items[item.id] = item
                        if window.has_icon_name():
                            icon_path = g15util.get_icon_path(window.get_icon_name(), warning = False)
                            if icon_path:
                                item.icon = "file:" + icon_path
                        if item.icon == None:
                            pixbuf = window.get_icon()
                            if pixbuf:               
                                item.icon = g15util.pixbuf_to_surface(pixbuf)
                                
        else:
            for process_id in gtop.proclist():
                process_id = "%d" %  process_id
                try :
                    pid = int(process_id)
                    proc_state = gtop.proc_state(pid)
                    proc_args = gtop.proc_args(pid)
                    if self._mode == "all" or ( self._mode != "all" and proc_state.uid == os.getuid()):                      
                        item = self._get_menu_item(pid)
                        item.icon = None
                        item.process_name = self._get_process_name(proc_args, proc_state.cmd)
                        this_items[item.id] = item
                except :
                    # In case the process disappears
                    pass
 
        # Remove any missing items
        for item in self.menu.get_children():
            if not item.id in this_items:
                self.menu.remove_child(item)
        
        # Make sure selected still exists
        if self.menu.selected != None and self.menu.get_child_by_id(self.menu.selected.id) is None:
            if len(self.menu.get_child_count()) > 0:
                self.menu.selected  = self.menu.get_children()[0]
            else:
                self.menu.selected = None

        self.page.mark_dirty()
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
        """
        When viewing applications, we don't refresh, just rely on BAMF 
        events when BAMF is available
        """
        if not self._mode == "applications" or self.bamf_matcher is None:
            self._timer = g15util.schedule("ProcessesRefresh", 5.0, self._refresh)
