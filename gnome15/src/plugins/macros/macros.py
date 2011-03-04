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
 
import gnome15.g15_profile as g15profile
import gnome15.g15_driver as g15driver
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
import gnome15.g15_screen as g15screen

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
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_Z10 ]


''' 
This plugin displays current macro information
'''

def create(gconf_key, gconf_client, screen):
    return G15Macro(gconf_client, screen)

class G15MacroPage():
    def __init__(self, page_no, number_of_pages, plugin):
        self.page = None
        self.page_no = page_no
        self.number_of_pages = number_of_pages
        self.plugin = plugin
        self.hidden = True
        self.profile = None
        
    def reset(self, profile):
        self.profile = profile
        macros = self.plugin.active_profile.macros[self.plugin.mkey - 1]      
        
        # Get all of the macros for this page from the sorted list
        p_sorted = sorted(macros, key=lambda key: key.key_list_key)
        page_no = 0
        i = 0  
        self.macros = []        
        for macro in p_sorted:
            if self.page_no == page_no:
                self.macros.append(macro)            
            i += 1
            if i == 12:
                i = 0
                page_no += 1
                
        self.icon_path = self.plugin.get_active_profile_icon_path()
        self.icon = g15util.load_surface_from_file(self.icon_path)
        
        if self.page == None:                   
            self.page = self.plugin.screen.new_page(self.paint, id="Macro Info %d" % page_no, 
                                               on_shown=self.on_shown,on_hidden=self.on_hidden, 
                                               thumbnail_painter = self.paint_thumbnail, 
                                               panel_painter = None if self.plugin.screen.driver.get_bpp() == 1 else self.paint_thumbnail)
            self.page.set_title("Macros (page %d)" % ( self.page_no + 1 ) ) 
        
    def on_shown(self):
        self.hidden = False
        
    def on_hidden(self):
        self.hidden = True
        
    def contains_keys(self, keys):
        for macro in self.macros:
            if macro.keys == keys:
                return True
        return False
    
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.icon != None:
            return g15util.paint_thumbnail_image(allocated_size, self.icon, canvas)
    
    def paint(self, canvas):
        
        properties = {}
        properties["profile"] = self.plugin.active_profile.name
        properties["icon"] = self.icon_path
        
        width = self.plugin.screen.width
        
        macros = self.plugin.active_profile.macros[self.plugin.mkey - 1]             
        cycle_to = False        
        k = 1             
        if len(macros) == 0:
            properties["message"] = "No Macros Configured on M" + str(self.plugin.mkey)
        else:
            properties["message"] = ""
            p_sorted = sorted(macros, key=lambda key: key.key_list_key)
            for macro in self.macros:
                if macro.keys == self.plugin.pressed:
                    properties [ "pressed" + str(k)] = True
                properties [ "key" + str(k)] = ", ".join(g15util.get_key_names(macro.keys))
                properties [ "name" + str(k)] = macro.name
                k += 1
                    
        for j in range(k, 13):
            properties["key" + str(j)] = ""
            properties["name" + str(j)] = ""
            
        properties["memory"] = "M%d" % self.plugin.mkey
                    
        self.plugin.theme.draw(canvas, properties)
            
class G15Macro():
    
    def __init__(self, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.macro_pages = []
        self.current_page = 0
        self.pressed = None

    def activate(self):
        self.active_profile = None
        self.hidden = False
        self.current_page_count = 0
        self.mkey = self.screen.get_mkey()
        self.notify_handle_1 = self.gconf_client.notify_add("/apps/gnome15/active_profile", self.profiles_changed)
        
        # Monitor macro profiles changing
        g15profile.profile_listeners.append(self.profiles_changed)
        
        self.reload_theme()        
        self.check_pages()

    def deactivate(self):
        self.close_all_pages()
        g15profile.profile_listeners.remove(self.profiles_changed)
        
    def get_active_profile_icon_path(self):
        if self.active_profile == None:
            return None        
        icon = self.active_profile.icon
        if icon == None or icon == "":
            icon = "preferences-desktop-keyboard-shortcuts"
        return g15util.get_icon_path(icon, self.screen.height)
        
    def reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
    
    def destroy(self):
        pass
    
    def handle_key(self, keys, state, post):
        if post:
            if self.screen.get_mkey() != self.mkey:
                self.mkey = self.screen.get_mkey()
                self.check_pages()
                if len(self.macro_pages) > 0:
                    self.screen.set_priority(self.macro_pages[0].page, g15screen.PRI_HIGH, revert_after = 3.0)
                      
            macro = self.active_profile.get_macro(self.mkey, keys)
            if macro:                    
                if state == g15driver.KEY_STATE_UP:
                    if self.screen.get_mkey() != self.mkey:
                        self.mkey = self.screen.get_mkey()
                        self.check_pages()
                    self.pressed = None
                else:
                    self.pressed = keys            
                    for macro_page in self.macro_pages:
                        if macro_page.contains_keys(keys):
                            self.screen.set_priority(macro_page.page, g15screen.PRI_HIGH, revert_after = 3.0)
                            return
                            
                self.screen.redraw()
                
        
    ''' Functions specific to plugin
    ''' 
        
    def close_all_pages(self):
        for macro_page in self.macro_pages:
            self.screen.del_page(macro_page.page)
        self.macro_pages = []
        self.current_page = 0
        self.current_page_count = 0
    
    def profiles_changed(self, arg0 = None, arg1 = None, arg2 = None, arg3 = None):
        self.check_pages()
        
    def check_pages(self):       
        active_profile = g15profile.get_active_profile()    
        if active_profile == None:    
            self.close_all_pages()
        else:    
            active_profile.load()
            macros = active_profile.macros[self.mkey - 1]
            no_pages = max(self.number_of_pages(len(macros), 12), 1)
            if no_pages != self.current_page_count:
                logger.info("Number of macro pages has changed from %d to %d, reloading" % (no_pages, self.current_page_count))
                self.current_page_count = no_pages
                self.close_all_pages()
                self.current_page = 0
                for i in range(no_pages -1, -1, -1):                
                    macro_page = G15MacroPage(i, no_pages, self)
                    self.macro_pages.append(macro_page)
                    
            self.active_profile = active_profile
            
            for macro_page in self.macro_pages:
                macro_page.reset(active_profile)
                self.screen.redraw(macro_page.page)
                    
    def number_of_pages(self, items, page_size):
        r = items % page_size
        if r == 0:
            return items / page_size
        else:
            return items / page_size + 1
