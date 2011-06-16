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
 
import dbus
import g15util
import g15theme
import g15globals
import g15screen
import g15driver
import os.path
    
class G15MenuPlugin():
    '''
    Base plugin class that may be used when the plugin just displays a single
    menu style component.
    '''
    
    def __init__(self, gconf_client, gconf_key, screen, menu_title_icon, page_id, title):
        self.page_id = page_id
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.session_bus = dbus.SessionBus()
        self._icon_path = g15util.get_icon_path(menu_title_icon)
        self._title = title
        self.thumb_icon = g15util.load_surface_from_file(self._icon_path)

    def activate(self):        
        self.reload_theme() 
        self.show_menu()
    
    def deactivate(self):
        if self.page != None:
            self.hide_menu()

    def destroy(self):
        pass
            
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_DOWN:              
            if self.screen.get_visible_page() == self.page:    
                if self.menu.handle_key(keys, state, post):
                    return True    
                
        return False
    
    def get_theme_properties(self):
        """
        Get the properties to pass to the SVG theme file for rendering. Sub-classes
        may override to provide more properties if needed.
        
        The subclass may return the same properties object with more properties added,
        or a complete new one if the default properties are to be excluded.
        
        Keyword arguments:
        properties -- properties
        """
        properties = {}
        properties["icon"] = self._icon_path
        properties["title"] = self._title
        properties["no_items"] = self.menu.get_child_count() == 0
        return properties
    
    def reload_theme(self):
        """
        Reload the SVG theme and configure it
        """
        self.theme = g15theme.G15Theme(self, "menu-screen")
        
    def show_menu(self):  
        """
        Create the component tree for the menu page and draw it
        """      
        self.page = self.create_page()
        self.menu = self.create_menu()
        self.page.add_child(self.menu)
        self.page.add_child(g15theme.Scrollbar("viewScrollbar", self.menu.get_scroll_values))
        self.screen.add_page(self.page)
        self.load_menu_items()
        self.screen.redraw(self.page)
        
    def create_page(self):
        """
        Create the page. Subclasses may override.
        """
        return g15theme.G15Page(self.page_id, self.screen, priority=g15screen.PRI_NORMAL, title = self._title, theme = self.theme, \
                                     theme_properties_callback = self.get_theme_properties,
                                     thumbnail_painter = self.paint_thumbnail)
        
    def create_menu(self):
        """
        Create the menu component. Subclasses may override to create or configure
        different components.
        """
        return g15theme.Menu("menu")
    
    def hide_menu(self):
        """
        Delete the page
        """     
        self.screen.del_page(self.page)
        self.page = None
        
    def load_menu_items(self):
        """
        Subclasses should override to set the initial menu items
        """
        pass
    
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None and self.thumb_icon != None and self.screen.driver.get_bpp() == 16:
            return g15util.paint_thumbnail_image(allocated_size, self.thumb_icon, canvas)
    