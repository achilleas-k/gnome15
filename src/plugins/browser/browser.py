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
import subprocess
import time
import os
import sys
import gtk
import gconf
import cairo
import traceback
import webkit

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


class BrowserPage(webkit.WebView):

    def __init__(self):
        webkit.WebView.__init__(self)
        settings = self.get_settings()
        settings.set_property("enable-developer-extras", True)

        # scale other content besides from text as well
        self.set_full_content_zoom(True)

class G15Browser():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def activate(self):
        self.page = self.screen.new_page(self.paint, id="Browser", priority = g15screen.PRI_NORMAL)
        self.browser = BrowserPage()
        
        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.props.hscrollbar_policy = gtk.POLICY_AUTOMATIC
        self.scrolled_window.props.vscrollbar_policy = gtk.POLICY_AUTOMATIC
        self.scrolled_window.add(self.browser)
        self.scrolled_window.show_all()
        
        self.screen.redraw(self.page)
    
    def deactivate(self):
        self.screen.del_page(self.page)
        
    def destroy(self):
        pass
    
    def paint(self, canvas):  
        print self.scrolled_window.window
        print self.browser.window
