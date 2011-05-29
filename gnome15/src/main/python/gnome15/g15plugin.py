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

    def activate(self):
        self.page = None        
        self._reload_theme()
        self._show_menu()
    
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
    
    def get_theme_path(self):
        """
        Get the directory theme files should be loaded from. By default, this
        is the Gnome15 global theme. If a plugin has a customised menu page,
        it should override this function to provide the location of the theme
        files (usually in the same place as the plugin itself)
        """
        return os.path.join(g15globals.themes_dir, "default")
    
    def get_theme_properties(self, properties):
        """
        Get the properties to pass to the SVG theme file for rendering. Sub-classes
        may override to provide more properties if needed.
        
        The subclass may return the same properties object with more properties added,
        or a complete new one if the default properties are to be excluded.
        
        Keyword arguments:
        properties -- properties
        """
        properties["icon"] = self._icon_path
        properties["title"] = self._title
        return properties
    
    """
    Private functions
    """        
    def _paint(self, canvas):
        # Draw the page
        self.theme.draw(canvas, self.get_theme_properties({}),
                        attributes={
                                      "items" : self.menu.get_items(),
                                      "selected" : self.menu.selected
                                      })
        
    def _reload_theme(self):
        """
        Reload the SVG theme and configure it
        """
        
        # Create the menu
        self.menu = g15theme.Menu("menu", self.screen)
        self.menu.on_selected = self._redraw
        self.menu.on_update = self._redraw
        
        # Setup the theme
        self.theme = g15theme.G15Theme(self.get_theme_path(), self.screen, "menu-screen")
        self.theme.add_component(self.menu)
        self.theme.add_component(g15theme.Scrollbar("viewScrollbar", self.menu.get_scroll_values))
        
    def _redraw(self):
        self.screen.redraw(self.page)
        
    def _show_menu(self):  
        """
        Create a new page for the menu and draw it
        """      
        self.page = self.screen.new_page(self._paint, id=self.page_id, priority=g15screen.PRI_NORMAL)
        self.screen.redraw(self.page)
    
    def _hide_menu(self):
        """
        Delete the page
        """     
        self.screen.del_page(self.page)
        self.page = None
