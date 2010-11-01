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
 
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
import gnome15.g15_driver as g15driver
import gnome15.g15_screen as g15screen
import gnome15.g15_globals as g15globals
import gnome15.g15_gtk as g15gtk
import subprocess
import time
import os
import sys
import gtk
import gconf
import cairo
import traceback
import gtkmozembed
import gobject

# Plugin details - All of these must be provided
id="browser"
name="Browser"
description="Adds an HTML browser using pywebkitgtk"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False

def create(gconf_key, gconf_client, screen):
    return G15Browser(gconf_client, gconf_key, screen)


class G15Browser():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.pixbuf = None
    
    def activate(self):
        self.offscreen_window = None
        self.page = self.screen.new_page(self.paint, id="Browser", priority = g15screen.PRI_NORMAL)
        self.screen.redraw(self.page)
        gobject.idle_add(self._create_offscreen_window)
        
    def _create_offscreen_window(self):
        self.moz = gtkmozembed.MozEmbed()        
        self.offscreen_window = g15gtk.G15Window(self.screen, self.page, 0, 0, self.screen.width, self.screen.height)
        self.offscreen_window.content.add(self.moz)
        self.offscreen_window.show_all()
        self.moz.load_url("http://www.google.com")
        self.screen.redraw(self.page)
        
    def deactivate(self):
        self.screen.del_page(self.page)
        
    def destroy(self):
        pass
    
    def paint(self, canvas):
        if self.offscreen_window != None:
            pixbuf = self.offscreen_window.get_as_pixbuf()
            image = g15util.pixbuf_to_surface(pixbuf)
            canvas.set_source_surface(image)
            canvas.paint()