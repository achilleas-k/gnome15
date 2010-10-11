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
import gnome15.g15_theme as g15theme 
import gnome15.g15_util as g15util
import datetime
import gtk
import os
import sys

# Plugin details - All of these must be provided
id="clock"
name="Clock"
description="Just displays a simple clock. This is the plugin used in " \
    + " the tutorial at the Gnome15 site."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=True

# 
# This simple plugin displays a digital clock. It also demonstrates
# how to add a preferences dialog for your plugin
# 

''' 
This function must create your plugin instance. You are provided with
a GConf client and a Key prefix to use if your plugin has preferences
'''
def create(gconf_key, gconf_client, screen):
    return G15Clock(gconf_key, gconf_client, screen)

''' 
This function must be provided if you set has_preferences to True. You
should display a dialog for editing the plugins preferences
'''
def show_preferences(parent, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "clock.glade"))
    
    dialog = widget_tree.get_object("ClockDialog")
    dialog.set_transient_for(parent)
    
    display_seconds = widget_tree.get_object("DisplaySecondsCheckbox")
    display_seconds.set_active(gconf_client.get_bool(gconf_key + "/display_seconds"))
    display_seconds.connect("toggled", changed, gconf_key + "/display_seconds", gconf_client)
    
    display_date = widget_tree.get_object("DisplayDateCheckbox")
    display_date.set_active(gconf_client.get_bool(gconf_key + "/display_date"))
    display_date.connect("toggled", changed, gconf_key + "/display_date", gconf_client)
    
    dialog.run()
    dialog.hide()

def changed(widget, key, gconf_client):
    '''
    gconf configuration has changed, redraw our canvas
    '''
    gconf_client.set_bool(key, widget.get_active())

class G15Clock():
    
    ''' 
    ******************************************************************
    * Lifecycle functions. You must provide activate and deactivate, *
    * the constructor and destroy function are optional              *
    ******************************************************************
    '''
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        
        '''
        Most plugins will delegate their drawing to a 'Theme'. A theme usually consists of an SVG file, one
        for each model that is supported, and optionally a fragement of Python for anything that can't
        be done with the SVG
        '''
        self.reload_theme()
    
    def activate(self):
        self.timer = None
        
        '''
        The activate function is invoked when gnome15 starts up, or the plugin is re-enabled
        after it has been disabled
        '''
        
        
        '''
        Most plugins will usually want to draw on the screen. To do so, a 'page' is created. We also supply a callback here to
        perform the painting. You can also supply 'on_shown' and 'on_hidden' callbacks here to be notified when your
        page actually gets shown and hidden
        '''        
        self.page = self.screen.new_page(self.paint, id="Clock")
        
        ''' 
        Once created, we should always ask for the screen to be drawn (even if another higher
        priority screen is actually active. If the canvas is not displayed immediately,
        the on_shown function will be invoked when it finally is.         
        '''
        self.screen.redraw(self.page)
        
        '''
        Schedule another redraw if appropriate
        '''        
        self.schedule_redraw()
        
        '''
        We want to be notified when the plugin configuration changed, so watch for gconf events
        '''        
        self.notify_handle = self.gconf_client.notify_add(self.gconf_key, self.config_changed);
    
    def deactivate(self):
        
        '''
        Stop being notified about configuration changes
        '''        
        self.gconf_client.notify_remove(self.notify_handle);
        
        '''
        Stop updating
        '''
        if self.timer != None:
            self.timer.cancel()
            self.timer = None
        
        ''' 
        Deactivation occurs when either the plugin is disabled, or the applet is stopped
        On deactivate, we must remove our canvas.  
        '''        
        self.screen.del_page(self.page)
        
    def destroy(self):
        '''
        Invoked when the plugin is disabled or the applet is stopped
        '''
        pass
    
    ''' 
    **************************************************************
    * Common callback functions. For example, your plugin is more* 
    * than likely to want to draw something on the LCD. Naming   *
    * the function paint() is the convention                     *
    **************************************************************    
    '''
    
    def paint(self, canvas):
        '''
        Invoked when this plugins page is active and needs to be redrawn. You should NOT
        call this function yourself, it is called automatically by the screen manager. 
        The function should draw everything as quickly as possible (i.e. not go off to 
        the internet to gather data or anything like that!)        
        '''
        
        properties = { }
        
        '''
        Get the details to display and place them as properties which are passed to
        the theme
        '''
        time_format = "%H:%M"
        if self.gconf_client.get_bool(self.gconf_key + "/display_seconds"):
            time_format = "%H:%M:%S"
        properties["time"] = datetime.datetime.now().strftime(time_format)
            
        if self.gconf_client.get_bool(self.gconf_key + "/display_date"):
            properties["date"] = datetime.datetime.now().strftime("%d/%m/%Y")
            
        '''
        Now ask the theme to draw the screen
        '''
        self.theme.draw(canvas, properties)
        
    
    ''' 
    ***********************************************************
    * Functions specific to plugin                            *
    ***********************************************************    
    ''' 
        
    def config_changed(self, client, connection_id, entry, args):
        '''
        This is called when the gconf configuration changes. See add_notify and remove_notify in
        the plugin's activate and deactive functions.
        '''
        
        '''
        Reload the theme as the layout required may have changed (i.e. with the 'show date' 
        option has been change)
        '''
        self.reload_theme()
        
        '''
        In this case, we temporarily raise the priority of the page. This will force
        the page to be painted (i.e. the paint function invoked). After the specified time,
        the page will revert it's priority. Only one revert timer is active at any one time,
        so it is safe to call this function in quick succession  
        '''
        self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)
        
    def redraw(self):
        '''
        Invoked by the timer once a second to redraw the screen. If your page is currently activem
        then the paint() functions will now get called. When done, we want to schedule the next
        redraw
        '''
        self.screen.redraw(self.page) 
        self.schedule_redraw()
        
    def schedule_redraw(self):
        '''
        Determine when to schedule the next redraw for. 
        '''        
        now = datetime.datetime.now()
        display_seconds = self.gconf_client.get_bool(self.gconf_key + "/display_seconds")
        if display_seconds:
            next_tick = now + datetime.timedelta(0, 1.0)
            next_tick = datetime.datetime(next_tick.year,next_tick.month,next_tick.day,next_tick.hour, next_tick.minute, int(next_tick.second))
        else:
            next_tick = now + datetime.timedelta(0, 60.0)
            next_tick = datetime.datetime(next_tick.year,next_tick.month,next_tick.day,next_tick.hour, next_tick.minute, 0)
        delay = g15util.total_seconds( next_tick - now )
        
        '''
        Try not to create threads or timers if possible. Use g15util.schedule() instead
        '''
        self.timer = g15util.schedule("ClockRedraw", delay, self.redraw)
        
    def reload_theme(self):        
        variant = None
        if self.gconf_client.get_bool(self.gconf_key + "/display_date"):
            variant = "with-date"
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen, variant)