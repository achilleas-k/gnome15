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
import g15screen

class G15RefreshingPlugin():
    
    """
    Base plugin class that may be used for plugins that refresh at set intervals. This
    abstract class will take care of disabling the refresh while the page is not
    visible 
    """
    
    def __init__(self, gconf_client, gconf_key, screen, icon, page_id, title, refresh_interval = 1.0):
        """
        Constructor
        
        Keyword arguments:
        gconf_client            - gconf client
        gconf_key               - gconf key for plugin
        screen                  - screen
        icon                    - icon to use for thumbnail
        title                   - title for page (displayed in menu etc)
        refresh_interval        - how often to refresh the page
        """
        self.page_id = page_id
        self.screen = screen
        self.refresh_interval = refresh_interval
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.session_bus = dbus.SessionBus()
        self._icon_path = g15util.get_icon_path(icon)
        self._title = title
        self.thumb_icon = g15util.load_surface_from_file(self._icon_path)
        self.timer = None
    
    def activate(self):
        self.active = True        
        self.page = self.create_page()
        self.populate_page()
        self.refresh()
        self.screen.add_page(self.page)
        self.screen.redraw(self.page)
        
    def create_page(self):
        return g15theme.G15Page(self.page_id, self.screen, on_shown=self._on_shown, on_hidden=self._on_hidden, \
                                     title = self._title, theme = g15theme.G15Theme(self),
                                     thumbnail_painter = self._paint_thumbnail )
        
    def populate_page(self):
        """
        Populate page. Subclasses may override to create or configure
        additional components.
        """
        pass
    
    def deactivate(self):
        self._cancel_refresh()
        self.screen.del_page(self.page)
        
    def destroy(self):
        pass
    
    def refresh(self):
        """
        Sub-classes should implement and perform the recurring actions. There is no need to 
        to redraw the page, it is done automatically.
        """        
        raise Exception("Not implemented")
    
    def get_next_tick(self):
        """
        Get how long to wait before the next refresh. By default this uses the 'refresh
        interval', but sub-classes may override to provide custom tick logic.
        """
        return self.refresh_interval
    
    ''' Private
    '''
        
    def _on_shown(self):
        self._reschedule_refresh()
            
    def _on_hidden(self):
        self._reschedule_refresh()
            
    def _reschedule_refresh(self):
        self._cancel_refresh()
        self._schedule_refresh()
        
    def _cancel_refresh(self):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None
        
    def _schedule_refresh(self):
        if self.screen.is_visible(self.page):
            self.timer = g15util.schedule("%s-Redraw" % self.page.id, self.get_next_tick(), self._refresh)
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None and self.thumb_icon != None and self.screen.driver.get_bpp() == 16:
            return g15util.paint_thumbnail_image(allocated_size, self.thumb_icon, canvas)
        
    def _refresh(self):
        self.refresh()
        self.screen.redraw(self.page)
        self._schedule_refresh()  
    
class G15MenuPlugin():
    '''
    Base plugin class that may be used when the plugin just displays a single
    menu style component.
    '''
    
    def __init__(self, gconf_client, gconf_key, screen, menu_title_icon, page_id, title):
        """
        Constructor
        
        Keyword arguments:
        gconf_client            - gconf client
        gconf_key               - gconf key for plugin
        screen                  - screen
        menu_title_icon         - icon to use for thumbnail and the menu title
        title                   - title for page (displayed in menu etc)
        refresh_interval        - how often to refresh the page
        """
        self.page_id = page_id
        self.page = None
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.session_bus = dbus.SessionBus()
        self._title = title
        self.set_icon(menu_title_icon)
        
    def set_icon(self, icon):
        self._icon_path = g15util.get_icon_path(icon)
        self.thumb_icon = g15util.load_surface_from_file(self._icon_path)

    def activate(self): 
        self.activated = True       
        self.reload_theme() 
        self.show_menu()
    
    def deactivate(self):
        self.activated = False
        if self.page != None:
            self.hide_menu()

    def destroy(self):
        pass
    
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
        properties["alt_title"] = ""
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
        self.menu.focusable = True
        self.page.on_deleted = self.page_deleted
        self.menu.set_focused(True)
        self.page.add_child(self.menu)
        self.page.add_child(g15theme.Scrollbar("viewScrollbar", self.menu.get_scroll_values))
        self.load_menu_items()
        self.screen.add_page(self.page)     
        self.screen.redraw(self.page)
        
    def create_page(self):
        """
        Create the page. Subclasses may override.
        """
        return g15theme.G15Page(self.page_id, self.screen, priority=g15screen.PRI_NORMAL, title = self._title, theme = self.theme, \
                                     theme_properties_callback = self.get_theme_properties,
                                     thumbnail_painter = self.paint_thumbnail)
        
    def page_deleted(self):
        """
        Invoked when the page is removed from the screen
        """
        self.page = None
        
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
        
    def load_menu_items(self):
        """
        Subclasses should override to set the initial menu items
        """
        pass
    
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None and self.thumb_icon != None and self.screen.driver.get_bpp() == 16:
            return g15util.paint_thumbnail_image(allocated_size, self.thumb_icon, canvas)
    