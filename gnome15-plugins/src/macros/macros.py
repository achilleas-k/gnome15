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
 
import gnome15.g15profile as g15profile
import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
import gnome15.g15screen as g15screen
import gnome15.g15plugin as g15plugin

import os
import logging
logger = logging.getLogger("macros")

# Plugin details - All of these must be provided
id="macros"
name="Macro Information"
description="Displays the currently active macro profile and a summary of available keys." \
    + "Also, the screen will be cycled to when a macro is activated and the key will be " \
    + "highlighted."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_Z10, g15driver.MODEL_G11 ]

def create(gconf_key, gconf_client, screen):
    return G15Macros(gconf_client, gconf_key, screen)


"""
Represents a mount as a single item in a menu
"""
class MacroMenuItem(g15theme.MenuItem):    
    def __init__(self, macro, plugin):
        g15theme.MenuItem.__init__(self)
        self.macro = macro
        self._plugin = plugin
        
    def draw(self, selected, canvas, menu_proties, menu_attributes):       
        item_properties = {}
        item_properties["item_selected"] = selected == self
        item_properties["item_name"] = self.macro.name
        item_properties["item_type"] = ""        
        item_properties["item_key"] = ", ".join(g15util.get_key_names(self.macro.keys))
        self.theme.draw(canvas, item_properties)
        return self.theme.bounds[3]
    
    def get_default_theme_dir(self):
        return os.path.join(os.path.dirname(__file__), "default")
    
    def activate(self):
        pass

"""
Macros plugin class
"""
class G15Macros(g15plugin.G15MenuPlugin):

    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15MenuPlugin.__init__(self, gconf_client, gconf_key, screen, ["preferences-desktop-keyboard-shortcuts"], id, name)
        
    def activate(self):
        self._get_configuration()
        g15plugin.G15MenuPlugin.activate(self)
        self._notify_handle = self.gconf_client.notify_add("/apps/gnome15/%s/active_profile" % self.screen.device.uid, self._profiles_changed)
        g15profile.profile_listeners.append(self._profiles_changed)
        self.listener = MacrosScreenChangeAdapter(self)
        self.screen.add_screen_change_listener(self.listener)
        self._reload()
        
    def deactivate(self):
        g15plugin.G15MenuPlugin.deactivate(self)
        self.gconf_client.notify_remove(self._notify_handle)
        g15profile.profile_listeners.remove(self._profiles_changed)
        self.screen.remove_screen_change_listener(self.listener)
            
    def get_theme_path(self):
        return os.path.join(os.path.dirname(__file__), "default")
    
    def get_theme_properties(self, properties):
        properties = g15plugin.G15MenuPlugin.get_theme_properties(self, properties)
        properties["title"] = self._active_profile.name
        properties["mkey"] = "M%d" % self._mkey
        properties["icon"] = self._get_active_profile_icon_path()
        return properties
        
    def _get_active_profile_icon_path(self):
        if self._active_profile == None:
            return None        
        icon = self._active_profile.icon
        if icon == None or icon == "":
            icon = "preferences-desktop-keyboard-shortcuts"
        return g15util.get_icon_path(icon, self.screen.height)
    
    """
    Screen change listener callbacks
    
    """
    def memory_bank_changed(self):
        self._reload()
        self._popup()
            
    """
    Private functions
    """
    def _profiles_changed(self, arg0 = None, arg1 = None, arg2 = None, arg3 = None):
        self._reload()
        self._popup()
    
    def _reload(self):
        """
        Reload all items for the current profile and bank
        """
        self.menu.clear_items()
        self.page.set_title("Macros - %s" % self._active_profile.name)
        macros = self._active_profile.macros[self._mkey - 1]        
        for macro in sorted(macros, key=lambda key: key.key_list_key):
            self._add_macro(macro)
        self.screen.redraw(self.page)
        
    def _get_configuration(self):
        self._mkey = self.screen.get_mkey()
        self._active_profile = g15profile.get_active_profile(self.screen.device)
                 
    def _popup(self):
        """
        Popup the page
        """
        self._raise_timer = self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 4.0)
        self.screen.redraw(self.page)
        
    def _remove_macro(self, macro):
        """
        Remove a macro from the menu
        """ 
        logger.info("Removing macro %s" % str(macro.name))
        self.menu.remove_item(self._get_item_for_macro(macro))
        self.screen.redraw(self.page)
        
    def _get_item_for_macro(self, macro):
        """
        Get the menu item for the given macro
        """
        for item in self.menu.get_items():
            if isinstance(item, MacroMenuItem) and item.macro == macro:
                return item
    
    def _add_macro(self, macro):
        """
        Add a new macro to the menu
        """ 
        logger.info("Adding macro %s" % str(macro.name))
        item = MacroMenuItem(macro, self)
        self.menu.add_item(item)
        self.screen.redraw(self.page)
        
class MacrosScreenChangeAdapter(g15screen.ScreenChangeAdapter):
    def __init__(self, plugin):
        self.plugin = plugin
        
    def memory_bank_changed(self, new_bank_number):
        self.plugin._get_configuration()
        self.plugin._reload()
        self.plugin._popup()