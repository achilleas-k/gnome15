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
 
import pygtk
pygtk.require('2.0')
import gtk
import g15_globals as g15globals
import g15_service as g15service
import g15_screen as g15screen
import g15_util as g15util
import appindicator
import gconf

icon_theme = gtk.icon_theme_get_default()
if g15globals.dev:
    icon_theme.prepend_search_path(g15globals.icons_dir)


class G15Indicator(appindicator.Indicator):
    
    def __init__(self,  parent_window=None):
        
        appindicator.Indicator.__init__(self, "gnome15",
                               self._get_icon_path("logitech-g-keyboard-panel"), 
                               appindicator.CATEGORY_HARDWARE)
        self.set_status (appindicator.STATUS_ACTIVE)
        self.page_items = {}        
        self._set_icons()
        self.service = g15service.G15Service(self, parent_window)
        self.conf_client = gconf.client_get_default()
        self.conf_client.notify_add("/apps/gnome15/indicate_only_on_error", self._indicator_options_changed)
        self.default_message = "Logitech G Keyboard"
        self.clear_attention()
        
        # Watch for icon theme changes        
        gtk_icon_theme = gtk.icon_theme_get_default()
        gtk_icon_theme.connect("changed", self._theme_changed)
                
        # Indicator menu
        self.menu = gtk.Menu()
        
        item = gtk.MenuItem("Properties")
        item.connect("activate", self.service.properties)
        self.menu.append(item)
        
        item = gtk.MenuItem("Macros")
        item.connect("activate", self.service.macros)
        self.menu.append(item)
        
        item = gtk.MenuItem("About")
        item.connect("activate", self.service.about_info)
        self.menu.append(item)
        
        self.menu.append(gtk.MenuItem())
        
        self.menu.show_all()
        self.set_menu(self.menu)
        
        self.service.start()
        self.service.screen.add_screen_change_listener(self)
        
    def show_page(self,event, page):        
        self.service.screen.cycle_to(page, True)  
        
    def page_changed(self, page):
        pass   
        
    def new_page(self, page):
        if page.priority >= g15screen.PRI_LOW:
            item = gtk.MenuItem(page.title)
            self.page_items[page.id] = item
            item.connect("activate", self.show_page, page)
                
            item.show_all()
            self.menu.append(item)
        
    def title_changed(self, page, title):
        item = self.page_items[page.id]
        item.set_label(title)
    
    def del_page(self, page):
        if page.id in self.page_items:
            item = self.page_items[page.id]
            self.menu.remove(item)
            item.destroy()
            del self.page_items[page.id]
            self.menu.show_all()
        
    def clear_attention(self):
        if self.conf_client.get_bool("/apps/gnome15/indicate_only_on_error"):
            self.set_status (appindicator.STATUS_PASSIVE)
        else:
            self.set_status (appindicator.STATUS_ACTIVE)
        
    def attention(self, message = None):
        self.set_status (appindicator.STATUS_ATTENTION)

    def quit(self):                
        gtk.main_quit()
        
    '''
    Private
    '''
    def _indicator_options_changed(self, client, connection_id, entry, args):
        if self.get_status() == appindicator.STATUS_PASSIVE or self.get_status() == appindicator.STATUS_ACTIVE:
            self.clear_attention()
    
    def _theme_changed(self, theme):
        self._set_icons()
        
    def _set_icons(self):
        self.set_icon(self._get_icon_path("logitech-g-keyboard-panel"))        
        self.set_attention_icon(self._get_icon_path("logitech-g-keyboard-error-panel"))
        
    def _get_icon_path(self, icon_name):
        if g15globals.dev:
            # Because the icons aren't installed in this mode, they must be provided
            # using the full filename. Unfortunately this means scaling may be a bit
            # blurry in the indicator applet
            return g15util.get_icon_path(icon_name, 128)
        else:
            return icon_name