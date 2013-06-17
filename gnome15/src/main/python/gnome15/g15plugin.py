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
import g15scheduler
import g15cairo
import g15icontools
import g15theme
import g15screen
import sys
import gobject

class G15Plugin():
    
    """
    Generic base plugin class
    """
    def __init__(self, gconf_client, gconf_key, screen):
        """
        Constructor
        
        Keyword arguments:
        gconf_client            - gconf client
        gconf_key               - gconf key for plugin
        screen                  - screen
        """
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.active = False
        self.__notify_handlers = []
            
    def create_theme(self):
        """
        Create a theme, using the currently selected theme for this plugin
        if one is available.
        """
        theme = self.gconf_client.get_string("%s/theme" % self.gconf_key)
        new_theme = None
        if theme:
            theme_def = g15theme.get_theme(theme, sys.modules[self.__module__])
            if theme_def:
                new_theme = g15theme.G15Theme(theme_def)
        if not new_theme:
            new_theme = g15theme.G15Theme(self)
        new_theme.plugin = self
        return new_theme
        
    def watch(self, key, callback):   
        """
        Watch for gconf changes for this plugin on a particular sub-key, calling
        the callback when the value changes. All watches will be removed when
        the plugin deactivates, so these should be added during the activate
        phase.
        
        Keyword arguments:
        key            - sub-key (or None to monitor everything)
        callback       - function to call on change
        """
        if isinstance(key, list):
            for k in key:
                self.watch(k, callback)
            return
        if key is not None and key.startswith("/"):
            k = key
        else:
            k = "%s/%s" % (self.gconf_key, key) if key is not None else self.gconf_key
        self.__notify_handlers.append(self.gconf_client.notify_add(k, callback))
        
    def activate(self):
        self.active = True
        self.watch("theme", self._reactivate)
               
    def deactivate(self):
        for h in self.__notify_handlers:
            self.gconf_client.notify_remove(h);
        self.active = False
        
    def destroy(self):
        pass
            
    def _reactivate(self, client, connection_id, entry, args):
        self.deactivate()
        self.activate()
        
class G15PagePlugin(G15Plugin):
    
    """
    Generic base plugin for plugins that want to contribute a page (most plugins
    will extend this in some way)
    """
    def __init__(self, gconf_client, gconf_key, screen, icon, page_id, title):
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
        G15Plugin.__init__(self, gconf_client, gconf_key, screen)
        self.page_id = page_id
        self.hidden = False
        self._icon_path = g15icontools.get_icon_path(icon)
        self._title = title
        self.page = None
        self.thumb_icon = g15cairo.load_surface_from_file(self._icon_path)
        self.add_page_on_activate = True
        
    def activate(self):
        G15Plugin.activate(self)
        self.page = self.create_page()
        self.populate_page()
        if self.add_page_on_activate:
            self.screen.add_page(self.page)
            self.screen.redraw(self.page)
               
    def deactivate(self):
        if self.page is not None:
            self.screen.del_page(self.page)
            self.page = None
        G15Plugin.deactivate(self)
        
    def create_page(self):
        return g15theme.G15Page(self.page_id, self.screen, 
                                     title = self._title, theme = self.create_theme(),
                                     thumbnail_painter = self._paint_thumbnail,
                                     theme_properties_callback = self.get_theme_properties,
                                     theme_properties_attributes = self.get_theme_attributes,
                                     painter = self._paint,
                                     originating_plugin = self)
        
    def populate_page(self):
        """
        Populate page. Subclasses may override to create or configure
        additional components.
        """
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
        return properties
    
    def reload_theme(self):
        """
        Reload the current theme
        """
        self.page.set_theme(self.create_theme())
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None and self.thumb_icon != None and self.screen.driver.get_bpp() == 16:
            return g15util.paint_thumbnail_image(allocated_size, self.thumb_icon, canvas)
    
    def _paint_panel(self, canvas, allocated_size, horizontal):
        pass
    
    def _paint(self, canvas):
        pass
        
class G15RefreshingPlugin(G15PagePlugin):
    
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
        G15PagePlugin.__init__(self, gconf_client, gconf_key, screen, icon, page_id, title)
        self.refresh_interval = refresh_interval
        self.session_bus = dbus.SessionBus()
        self.timer = None
        self.schedule_on_gobject = False
        self.only_refresh_when_visible = True
    
    def create_page(self):
        return g15theme.G15Page(self.page_id, self.screen, on_shown=self._on_shown, on_hidden=self._on_hidden, \
                                     title = self._title, theme = self.create_theme(),
                                     thumbnail_painter = self._paint_thumbnail,
                                     painter = self._paint,
                                     panel_painter = self._paint_panel,
                                     theme_properties_callback = self.get_theme_properties,
                                     originating_plugin = self)
    
    def deactivate(self):
        self._cancel_refresh()
        G15PagePlugin.deactivate(self)
        
    def populate_page(self):
        G15PagePlugin.populate_page(self)
        self.refresh()
    
    def refresh(self):
        """
        Sub-classes should implement and perform the recurring actions. There is no need to 
        to redraw the page, it is done automatically.
        """        
        pass
    
    def get_next_tick(self):
        """
        Get how long to wait before the next refresh. By default this uses the 'refresh
        interval', but sub-classes may override to provide custom tick logic.
        """
        return self.refresh_interval
    
    def do_refresh(self):
        """
        Programatically refresh. The timer will be reset
        """
        self._cancel_refresh()
        self._refresh()
        
    
    ''' Private
    '''
        
    def _on_shown(self):
        if self.only_refresh_when_visible:
            self._reschedule_refresh()
            
    def _on_hidden(self):
        if self.only_refresh_when_visible:
            self._reschedule_refresh()
            
    def _reschedule_refresh(self):
        self._cancel_refresh()
        self._schedule_refresh()
        
    def _cancel_refresh(self):
        if self.timer != None:
            if isinstance(self.timer, int):
                gobject.source_remove(self.timer)
            else:
                self.timer.cancel()
            self.timer = None
        
    def _schedule_refresh(self):
        if self.page and ( not self.only_refresh_when_visible or self.screen.is_visible(self.page) ):
            if self.schedule_on_gobject:
                self.timer = gobject.timeout_add(int(self.get_next_tick() * 1000), self._refresh)
            else:
                self.timer = g15scheduler.schedule("%s-Redraw" % self.page.id, self.get_next_tick(), self._refresh)
        
    def _refresh(self):
        self.refresh()
        self.screen.redraw(self.page)
        self._reschedule_refresh()  
    
class G15MenuPlugin(G15Plugin):
    '''
    Base plugin class that may be used when the plugin just displays a single
    menu style component.
    '''
    
    def __init__(self, gconf_client, gconf_key, screen, menu_title_icon, page_id, title, show_on_activate = True):
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
        G15Plugin.__init__(self, gconf_client, gconf_key, screen)
        
        self.page_id = page_id
        self.page = None
        self.hidden = False
        self.menu = None
        self.session_bus = dbus.SessionBus()
        self._title = title
        self._show_on_activate = show_on_activate
        self.set_icon(menu_title_icon)
        
    def set_icon(self, icon):
        self._icon_path = g15icontools.get_icon_path(icon)
        self.thumb_icon = g15cairo.load_surface_from_file(self._icon_path)

    def activate(self):         
        G15Plugin.activate(self) 
        self.reload_theme() 
        if self._show_on_activate:
            self.show_menu()
    
    def deactivate(self):
        G15Plugin.deactivate(self) 
        if self.page != None:
            self.hide_menu()

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
        if not self.active:
            return
            
        self.page = self.create_page()
        self.menu = self.create_menu()
        self.page.set_focused_component(self.menu)
        self.menu.focusable = True
        self.page.on_deleted = self.page_deleted
        self.menu.set_focused(True)
        self.page.add_child(self.menu)  
        self.page.add_child(g15theme.MenuScrollbar("viewScrollbar", self.menu))
        self.load_menu_items()
        self.add_to_screen()
        
    def add_to_screen(self):
        """
        Add the page to the screen
        """
        self.screen.add_page(self.page)     
        self.screen.redraw(self.page)
        
    def create_page(self):
        """
        Create the page. Subclasses may override.
        """
        return g15theme.G15Page(self.page_id, self.screen, priority=g15screen.PRI_NORMAL, title = self._title, theme = self.theme, \
                                     theme_properties_callback = self.get_theme_properties,
                                     thumbnail_painter = self.paint_thumbnail,
                                     originating_plugin = self)
        
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
        self.page = None
        
    def load_menu_items(self):
        """
        Subclasses should override to set the initial menu items
        """
        pass
    
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None and self.thumb_icon != None and self.screen.driver.get_bpp() == 16:
            return g15util.paint_thumbnail_image(allocated_size, self.thumb_icon, canvas)
    