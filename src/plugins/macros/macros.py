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
 
import gnome15.g15_draw as g15draw
import gnome15.g15_profile as g15profile
import gnome15.g15_driver as g15driver
import gnome15.g15_util as g15util

import alsaaudio
import select
import os
from threading import Timer

# Plugin details - All of these must be provided
id="macros"
name="Macro Information"
description="Displays the currently active\nmacro profile and a summary of\navailable keys"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://localhost"
has_preferences=False


''' 
This plugin displays current macro information
'''

def create(gconf_key, gconf_client, screen):
    return G15Macro(gconf_client, screen)

class G15MacroScreen():
    def __init__(self, canvas, page_no, number_of_pages, profile, plugin):
        self.canvas = canvas
        self.page_no = page_no
        self.number_of_pages = number_of_pages
        self.profile = profile
        self.plugin = plugin
        self.redraw()
    
    def redraw(self):
        width = self.plugin.screen.driver.get_size()[0]
        self.canvas.clear()
        self.canvas.set_font_size(g15draw.FONT_TINY)
        self.canvas.fill_box([(0,0),(width + 1, 9)], "Black")
        self.canvas.draw_text("Macros", (2, 2), "White")
        self.canvas.fill_box([(width - 15, 1),(width - 3, 8)], color="White")
        self.canvas.draw_text("M" + str(self.plugin.mkey), (width - 13, 2), "Black")
    
        self.canvas.draw_text(self.profile.name, (g15draw.RIGHT, 2), inset_x=26, color="White")
        macros = self.profile.macros[self.plugin.mkey - 1]             
        cycle_to = False               
        if len(macros) == 0:            
            self.canvas.draw_text("No Macros Configured on M" + str(self.plugin.mkey), (g15draw.CENTER, 14))
            self.canvas.draw_text("Press MR to record", (g15draw.CENTER, 24))
        else:
            x = 0
            y = 13
            self.canvas.set_font_size(g15draw.FONT_TINY)
            col = width / 3
            p_sorted = sorted(macros, key=lambda key: key.key)
            page_no = 0
            i = 0        
            for macro in p_sorted:
                if self.page_no == page_no:
                    color = "Black"
                    clear = "White"
                    if macro.key == self.plugin.pressed:
                        clear = "Black"
                        color = "White"                                                
                        # If any of the macro screens are visible, then cycle to the one with the key
                        cycle_to = True
                        
                    self.canvas.fill_box((x, y - 1, x + col, y + 7), color=clear)                        
                    self.canvas.draw_text(", ".join(g15util.get_key_names(macro.key)) + ":" + macro.name, (x, y), color=color)
                    x += col
                    if x + col > ( width ):
                        x = 0
                        y += 8
                i += 1
                if i == 12:
                    i = 0
                    page_no += 1
        self.plugin.screen.draw(self.canvas, cycle_to = cycle_to and not self.plugin.hidden, transitions=False)
            
class G15Macro():
    
    def __init__(self, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.pages = []
        self.current_page = 0
        self.pressed = None
        self.hidden = True

    def activate(self):
        self.hidden = False
        self.current_page_count = 0
        self.mkey = self.screen.get_mkey()
        self.ap_h = self.gconf_client.notify_add("/apps/gnome15/active_profile", self.profiles_changed);
        self.pr_h = self.gconf_client.notify_add("/apps/gnome15/profiles", self.profiles_changed);
        self.check_pages()
    
    def deactivate(self):
        self.gconf_client.notify_remove(self.ap_h);
        self.gconf_client.notify_remove(self.pr_h);
        self.close_all_pages()
        
    def destroy(self):
        pass
    
    def handle_key(self, key, state, post):
        if post:
            if state == g15driver.KEY_STATE_UP:
                self.mkey = self.screen.get_mkey()
                self.pressed = None
            else:
                self.pressed = key
                
            for page in self.pages:
                page.redraw()
        
    ''' Functions specific to plugin
    ''' 
        
    def on_shown(self):
        self.hidden = False
        
    def on_hidden(self):
        self.hidden = True
        
    def close_all_pages(self):
        for page in self.pages:
            self.screen.del_canvas(page.canvas)
        self.pages = []
    
    def profiles_changed(self, arg0, arg1, arg2, arg3):
        self.check_pages()
        
    def check_pages(self):        
        active_profile = g15profile.get_active_profile()    
        if active_profile == None:
            self.close_all_pages()
        else:
            active_profile.load()
            macros = active_profile.macros[self.mkey - 1]
            no_pages = self.number_of_pages(len(macros), 12)
            if no_pages != self.current_page_count:
                self.current_page_count = no_pages
                self.close_all_pages()
                self.current_page = 0
                for i in range(no_pages -1, -1, -1):                
                    canvas = self.screen.new_canvas(id="Macro Info " + str(i),on_shown=self.on_shown,on_hidden=self.on_hidden)
                    self.pages.append(G15MacroScreen(canvas, i, no_pages, active_profile, self))
            else:
                for page in self.pages:
                    page.profile = active_profile
                    page.redraw()
            if not self.hidden:
                self.screen.draw_current_canvas()
    
    def number_of_pages(self, items, page_size):
        r = items % page_size
        if r == 0:
            return items / page_size
        else:
            return items / page_size + 1
