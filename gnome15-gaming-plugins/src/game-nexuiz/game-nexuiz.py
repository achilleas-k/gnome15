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
 
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15profile as g15profile
import os
import locale

# Plugin details - All of these must be provided
id="game-nexuiz"
name=_("Nexuiz")
description=_("Gaming plugin for Nexuiz")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2011 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]

"""
Register this as a location for profiles
"""
g15profile.add_profile_dir(os.path.dirname(__file__))

def create(gconf_key, gconf_client, screen):
    return GameNexuiz(gconf_key, gconf_client, screen)

class GameNexuiz():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._page = None
    
    def activate(self):
        self._reload_theme()
        self._page = g15theme.G15Page("Nexuiz", self._screen, 
                                     theme_properties_callback = self._get_properties,
                                     theme = self._theme, 
                                     originating_plugin = self)
        self._page.title = "Nexuiz"
        self._screen.add_page(self._page)
        self._redraw()
        
        # Add the right profile for the model
        macro_file = os.path.join(os.path.dirname(__file__), "game-nexuiz.%s.macros")
        if os.path.exists(macro_file):
            profile = g15profile.G15Profile(self._screen.device, file_path = macro_file)
            g15profiles.add_profile(profile)
    
    def deactivate(self):
        self._screen.del_page(self._page)
        
    def destroy(self):
        pass
    
    def _redraw(self):
        self._screen.redraw(self._page) 
        
    def _reload_theme(self):        
        self._theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), None)
        
    def _get_properties(self):
        properties = { }
        return properties
