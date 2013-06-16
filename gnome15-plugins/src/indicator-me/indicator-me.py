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
_ = g15locale.get_translation("indicator-me", modfile = __file__).ugettext

import gnome15.g15screen as g15screen
import gnome15.g15util as g15util
import gnome15.g15os as g15os
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import time
import dbus
import os
import xdg.Config as config
import gtk
import Image
import gobject
import gnome15.dbusmenu as dbusmenu
from threading import Timer
from dbus.exceptions import DBusException

import logging
logger = logging.getLogger("indicator-me")

# Only works on Ubuntu. Doesn't work on later versions of Ubuntu
if not "Ubuntu" == g15os.get_lsb_distributor():
    raise Exception("Indicator Me only works on Ubuntu")
elif g15os.get_lsb_release() > 11.04:
    raise Exception("Indicator Me only works on Ubuntu up to version 11.04")


# Plugin details - All of these must be provided
id="indicator-me"
name=_("Indicator Me")
description=_("Indicator that shows user information and status.\n\n\
NOTE, this plugin is not required on Ubuntu 11.10 and onwards, as the \
functionality is now provided by Indicator Messages")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous status"), 
         g15driver.NEXT_SELECTION : _("Next status"), 
         g15driver.SELECT : _("Choose status"),
         }

''' This simple plugin displays user information and status
'''

def create(gconf_key, gconf_client, screen):
    return G15IndicatorMe(gconf_client, screen)
        
            
STATUS_ICONS = { "user-available-panel" : _("Available"), 
                 "user-away-panel" : _("Away"), 
                 "user-busy-panel" : _("Busy"), 
                 "user-offline-panel" : _("Offline"), 
                 "user-invisible-panel" : _("Invisible"),
                 "user-indeterminate" : _("Invisible"),
                 "user-available" : _("Available"), 
                 "user-away" : _("Away"), 
                 "user-busy" : _("Busy"), 
                 "user-offline" : _("Offline"), 
                 "user-invisible" : _("Invisible") }
'''
Indicator Messages  DBUSMenu property names
'''

APP_RUNNING = "app-running"
INDICATOR_LABEL = "indicator-label"
INDICATOR_ICON = "indicator-icon"
RIGHT_SIDE_TEXT = "right-side-text"

'''
Indicator Messages DBUSMenu types
'''
TYPE_APPLICATION_ITEM = "application-item"
TYPE_INDICATOR_ITEM = "indicator-item"


class IndicatorMeMenuEntry(dbusmenu.DBUSMenuEntry):
    def __init__(self, id, properties, menu):
        dbusmenu.DBUSMenuEntry.__init__(self, id, properties, menu)
        
    def set_properties(self, properties):
        dbusmenu.DBUSMenuEntry.set_properties(self, properties)        
        if self.type == TYPE_INDICATOR_ITEM and INDICATOR_LABEL in self.properties:
            self.label = self.properties[INDICATOR_LABEL]
        if self.type == TYPE_INDICATOR_ITEM:
            self.icon = self.properties[INDICATOR_ICON] if INDICATOR_ICON in self.properties else None
        
    def get_alt_label(self):
        return self.properties[RIGHT_SIDE_TEXT] if RIGHT_SIDE_TEXT in self.properties else ""
        
    def is_app_running(self):
        return APP_RUNNING in self.properties and self.properties[APP_RUNNING]

class IndicatorMeMenu(dbusmenu.DBUSMenu):
    
    def __init__(self, session_bus, on_change = None):
        try:
            dbusmenu.DBUSMenu.__init__(self, session_bus, "org.ayatana.indicator.me", "/org/ayatana/indicator/me/menu", "org.ayatana.dbusmenu", on_change, False)
        except dbus.DBusException as dbe:
            dbusmenu.DBUSMenu.__init__(self, session_bus, "com.canonical.indicator.me", "/com/canonical/indicator/me/menu", "com.canonical.dbusmenu", on_change, True)

    def create_entry(self, id, properties):
        return IndicatorMeMenuEntry(id, properties, self)
            
class G15IndicatorMe():
    
    def __init__(self, gconf_client, screen):
        self._screen = screen;
        self._hide_timer = None
        self._session_bus = None
        self._me_service = None
        self._gconf_client = gconf_client
        self._session_bus = dbus.SessionBus()
        self._menu = None

    def activate(self):
        self._icon = "user-offline-panel"
        self._natty = False
        self._menu_page = None
        try :
            me_object = self._session_bus.get_object('com.canonical.indicator.me', '/com/canonical/indicator/me/service')
            self._me_service = dbus.Interface(me_object, 'com.canonical.indicator.me.service')
            self._natty = True
        except DBusException as dbe:
            me_object = self._session_bus.get_object('org.ayatana.indicator.me', '/org/ayatana/indicator/me/service')
            self._me_service = dbus.Interface(me_object, 'org.ayatana.indicator.me.service')
            
        self._me_menu = IndicatorMeMenu(self._session_bus)
        
        # Watch for events
        self._status_changed_handle = self._me_service.connect_to_signal("StatusIconsChanged", self._status_icon_changed)
        self._user_changed_handle = self._me_service.connect_to_signal("UserChanged", self._user_changed)
        self._me_menu.on_change = self._menu_changed        
        self._menu_theme = g15theme.G15Theme(self, "menu-screen") 
        self._popup_theme = g15theme.G15Theme(self)

        self._get_details()
        self._create_pages()
    
    def deactivate(self):
        self._session_bus.remove_signal_receiver(self._status_changed_handle)
        self._session_bus.remove_signal_receiver(self._user_changed_handle)
        self._screen.del_page(self._menu_page)
        self._screen.del_page(self._popup_page)
        
    def destroy(self):
        pass
        
    '''
    Private
    '''     
    def _create_pages(self):  
        self._menu_page = g15theme.G15Page(_("Indicator Me Status"), self._screen, priority = g15screen.PRI_NORMAL, \
                                           on_shown = self._on_menu_page_show, title = self._get_status_text(), theme = self._menu_theme,
                                           theme_properties_callback = self._get_menu_properties,
                                           thumbnail_painter = self._paint_popup_thumbnail,
                                           originating_plugin = self)
        self._popup_page = g15theme.G15Page(_("Indicator Me Popup"), self._screen, priority = g15screen.PRI_INVISIBLE, \
                                            panel_painter = self._paint_popup_thumbnail, theme = self._popup_theme,
                                            theme_properties_callback = self._get_popup_properties,
                                            originating_plugin = self)
        self._screen.add_page(self._menu_page)
        self._screen.add_page(self._popup_page)
        
        # Create the menu
        self._menu = g15theme.DBusMenu(self._me_menu)
        self._menu_page.add_child(self._menu)
        self._menu_page.add_child(g15theme.MenuScrollbar("viewScrollbar", self._menu))
        self._screen.redraw(self._menu_page)
        
    def _on_menu_page_show(self):
        for item in self._menu.get_children():
            if isinstance(item, g15theme.DBusMenuItem) and self._icon == item.dbus_menu_entry.get_icon_name():
                self._menu.selected = item
                self._screen.redraw(self._menu_page)
    
    def _status_icon_changed(self, new_icon):
        self._popup()
        
    def _user_changed(self, new_icon):
        self._popup()
            
    def _menu_changed(self, menu = None, property = None, value = None):
        self._get_details()
        self._menu.menu_changed(menu, property, value)
        
    def _popup(self):    
        self._get_details()
        self._screen.set_priority(self._popup_page, g15screen.PRI_HIGH, revert_after = 3.0)
        self._screen.redraw(self._popup_page)
        
    def _get_details(self):
        self._icon = self._me_service.StatusIcons()
        self._icon_image = g15util.load_surface_from_file(g15util.get_icon_path(self._icon))
        self._username = self._me_service.PrettyUserName()
        if self._menu_page != None:
            self._menu_page.set_title(self._get_status_text())
            
    def _get_status_text(self):
        return _("Status - %s") % STATUS_ICONS[self._icon]
        
    def _paint_popup_thumbnail(self, canvas, allocated_size, horizontal):
        if self._popup_page != None:
            if self._icon_image != None and self._screen.driver.get_bpp() != 1:
                return g15util.paint_thumbnail_image(allocated_size, self._icon_image, canvas)
            
    def _get_menu_properties(self):
        props = { "icon" :  g15util.get_icon_path(self._icon),
                 "title" : _("Status"),
                 "alt_title": STATUS_ICONS[self._icon] }
        return props

    def _get_popup_properties(self):     
        properties = { "icon" : g15util.get_icon_path(self._icon, self._screen.width) }
        properties["text"] = _("Unknown")
        if self._icon in STATUS_ICONS:
            properties["text"] = STATUS_ICONS[self._icon]
        else:
            logger.warning("Unknown status icon %s" % self._icon)
        return properties