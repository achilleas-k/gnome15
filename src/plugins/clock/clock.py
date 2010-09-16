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
 
import gnome15.g15_screen as g15screen 
import gnome15.g15_draw as g15draw
import datetime
from threading import Timer
import gtk
import os
import sys

# Plugin details - All of these must be provided
id="clock"
name="Clock"
description="Just displays a simple clock"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://localhost"
has_preferences=True

''' 
This simple plugin displays a digital clock. It also demostates
how to add a preferences dialog for your plugin
'''

''' 
This function must create your plugin instance. You are provided with
a GConf client and a Key prefix to use if your plugin has preferences
'''
def create(gconf_key, gconf_client, screen):
    return G15Clock(gconf_key, gconf_client, screen)

class G15Clock():
    
    ''' Lifecycle functions. You must provide activate and deactivate,
        the constructor and destroy function are optional
    '''
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def activate(self):
        self.active = True
        self.timer = None
        
        ''' 
        The activate function is invoked when the applet no longer needs the screen for itself. In
        practice, this is when the applet is started, after a macro has finished
        recording and when the plugin is enabled
        '''
        
        '''
        Most plugins will usually want to draw on the screen. To do so, a 'canvas' is created.
        In this case we want a low priority screen. We also supply some callbacks here to
        get notified when the screen is actually visible. This isn't striclty required, but
        if the can do optimisations and not paint if the screen is not visible, this is a good
        thing!
        '''        
        self.canvas = self.screen.new_canvas(priority=g15screen.PRI_LOW, on_shown=self.on_shown, on_hidden=self.on_hidden, id="Clock")
        
        ''' 
        Once created, we should always ask for the screen to be drawn (even if another higher
        priority screen is actually active. If the canvas is not displayed immediately,
        the on_shown function will be invoked when it finally is.         
        '''
        self.screen.draw_current_canvas()
    
    def deactivate(self):
        ''' 
        On deactivate, we must remove our canvas
        '''        
        self.screen.del_canvas(self.canvas)
        
    def destroy(self):
        '''
        Invoked when the plugin is disabled or the applet is stopped
        '''
        pass
    
    ''' 
    This function must be provided if you set has_preferences to True. You
    should display a dialog for editing the plugins preferences
    '''
    def show_preferences(self, parent):
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "clock.glade"))
        
        dialog = widget_tree.get_object("ClockDialog")
        dialog.set_transient_for(parent)
        
        display_seconds = widget_tree.get_object("DisplaySecondsCheckbox")
        display_seconds.set_active(self.gconf_client.get_bool(self.gconf_key + "/display_seconds"))
        seconds_h = display_seconds.connect("toggled", self.changed, self.gconf_key + "/display_seconds")
        
        display_date = widget_tree.get_object("DisplayDateCheckbox")
        display_date.set_active(self.gconf_client.get_bool(self.gconf_key + "/display_date"))
        date_h = display_date.connect("toggled", self.changed, self.gconf_key + "/display_date")
        
        dialog.run()
        dialog.hide()
        display_seconds.disconnect(seconds_h)
        display_date.disconnect(date_h)
    
    ''' Callbacks
    '''
    
    def on_shown(self):
        if self.timer != None:
            self.timer.cancel()
        self.hidden = False
        self.redraw()
        
    def on_hidden(self):
        self.hidden = True
        if self.timer != None:
            self.timer.cancel()
    
    def changed(self, widget, key):
        self.gconf_client.set_bool(key, widget.get_active())
        self.redraw()    
        
    ''' Functions specific to plugin
    ''' 
    
    def redraw(self):
        if not self.hidden:
            self.canvas.clear()
            time_format = "%H:%M"
            if self.gconf_client.get_bool(self.gconf_key + "/display_seconds"):
                time_format = "%H:%M:%S"                
            if self.gconf_client.get_bool(self.gconf_key + "/display_date"):
                self.canvas.set_font_size(g15draw.FONT_MEDIUM)
                self.canvas.draw_text(datetime.datetime.now().strftime(time_format), (g15draw.CENTER, g15draw.TOP))
                self.canvas.draw_text(datetime.datetime.now().strftime("%d/%m/%Y"), (g15draw.CENTER, g15draw.BOTTOM))
            else:
                self.canvas.set_font_size(g15draw.FONT_LARGE)
                self.canvas.draw_text(datetime.datetime.now().strftime(time_format), (g15draw.CENTER, g15draw.CENTER))
                
            ''' Ask the screen to draw our canvas
            '''
            self.screen.draw(self.canvas)
            
            ''' Redraw again in one second
            '''
            self.timer = Timer(1, self.redraw, ())
            self.timer.name = "ClockRedrawTimer"
            self.timer.start()
