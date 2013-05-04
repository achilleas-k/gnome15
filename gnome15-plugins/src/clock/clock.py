#        +-----------------------------------------------------------------------------+
#        | GPL                                                                         |
#        +-----------------------------------------------------------------------------+
#        | Copyright (c) 2010-2012 Brett Smith <tanktarta@blueyonder.co.uk>            |
#        | Copyright (c) 2013 Nuno Araujo <nuno.araujo@russo79.com>                    |
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
_ = g15locale.get_translation("clock", modfile = __file__).ugettext

import gnome15.g15screen as g15screen 
import gnome15.g15theme as g15theme 
import gnome15.g15util as g15util
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import gnome15.g15text as g15text
import gnome15.g15plugin as g15plugin
import datetime
import gtk
import pango
import os
import locale

# Plugin details - All of these must be provided
id="clock"
name=_("Clock")
description=_("Just displays a simple clock. This is the plugin used in \
the tutorial at the Gnome15 site.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]

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
def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "clock.glade"))
    
    dialog = widget_tree.get_object("ClockDialog")
    dialog.set_transient_for(parent)
    
    display_seconds = widget_tree.get_object("DisplaySecondsCheckbox")
    display_seconds.set_active(gconf_client.get_bool(gconf_key + "/display_seconds"))
    display_seconds.connect("toggled", _changed, gconf_key + "/display_seconds", gconf_client)
    
    display_date = widget_tree.get_object("DisplayDateCheckbox")
    display_date.set_active(gconf_client.get_bool(gconf_key + "/display_date"))
    display_date.connect("toggled", _changed, gconf_key + "/display_date", gconf_client)
    
    use_24hr_format = widget_tree.get_object("TwentFourHourCheckbox")
    use_24hr_format.set_active(gconf_client.get_bool(gconf_key + "/use_24hr_format"))
    use_24hr_format.connect("toggled", _changed, gconf_key + "/use_24hr_format", gconf_client)
    
    dialog.run()
    dialog.hide()

def _changed(widget, key, gconf_client):
    '''
    gconf configuration has changed, redraw our canvas
    '''
    gconf_client.set_bool(key, widget.get_active())

class G15Clock(g15plugin.G15Plugin):
    '''
    You would normally want to extend at least g15plugin.G15Plugin as it
    provides basic plugin functions. 
    
    There are also further specialisations, such as g15plugin.G15PagePlugin
    for plugins that have display a page, or g15plugin.G15MenuPlugin for
    menu like plugins, or g15plugin.G15RefreshingPlugin for plugins that
    refresh their view based on a timer.
    
    This example uses the most basic type to demonstrate how plugins are put
    together, but it could easily use G15RefreshingPlugin and cut out a lot
    of code.
    
    '''
    
    
    ''' 
    ******************************************************************
    * Lifecycle functions. You must provide activate and deactivate, *
    * the constructor and destroy function are optional              *
    ******************************************************************
    '''
    
    def __init__(self, gconf_key, gconf_client, screen):
        g15plugin.G15Plugin.__init__(self, gconf_client, gconf_key, screen)
        self.hidden = False
        self.page = None
    
    def activate(self):
        '''
        The activate function is invoked when gnome15 starts up, or the plugin is re-enabled
        after it has been disabled. When extending any of the provided base plugin classes,
        you nearly always want to call the function in the supoer class as well
        '''
        g15plugin.G15Plugin.activate(self)
        

        '''
        Load our configuration
        '''        
        self.timer = None
        self._load_configuration()
        
        '''
        We will be drawing text manually in the thumbnail, so it is recommended you use the
        G15Text class which simplifies drawing and measuring text in an efficient manner  
        '''
        self.text = g15text.new_text(self.screen)
        
        '''
        Most plugins will delegate their drawing to a 'Theme'. A theme usually consists of an SVG file, one
        for each model that is supported, and optionally a fragment of Python for anything that can't
        be done with SVG and the built in theme facilities
        '''
        self._reload_theme()
        
        '''
        Most plugins will usually want to draw on the screen. To do so, a 'page' is created. We also supply a callback here to
        perform the painting. You can also supply 'on_shown' and 'on_hidden' callbacks here to be notified when your
        page actually gets shown and hidden.
        
        A thumbnail painter function is also provided. This is used by other plugins want a thumbnail representation
        of the current screen. For example, this could be used in the 'panel', or the 'menu' plugins
        '''        
        self.page = g15theme.G15Page("Clock", self.screen, 
                                     theme_properties_callback = self._get_properties,
                                     thumbnail_painter = self.paint_thumbnail, panel_painter = self.paint_thumbnail,
                                     theme = self.theme,
                                     originating_plugin = self)
        self.page.title = "Simple Clock"
        
        '''
        Add the page to the screen
        '''
        self.screen.add_page(self.page)
        
        ''' 
        Once created, we should always ask for the screen to be drawn (even if another higher
        priority screen is actually active. If the canvas is not displayed immediately,
        the on_shown function will be invoked when it finally is.         
        '''
        self.screen.redraw(self.page)
        
        '''
        As this is a Clock, we want to redraw at fixed intervals. So, schedule another redraw
        if appropriate
        '''        
        self._schedule_redraw()
        
        '''
        We want to be notified when the plugin configuration changed, so watch for gconf events.
        The watch function is used, as this will automatically track the monitor handles
        and clean them up when the plugin is deactivated
        '''        
        self.watch(None, self._config_changed)
    
    def deactivate(self):
        g15plugin.G15Plugin.deactivate(self)
        
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
        
    '''
    Paint the thumbnail. You are given the MAXIMUM amount of space that is allocated for
    the thumbnail, and you must return the amount of space actually take up. Thumbnails
    can be used for example by the panel plugin, or the menu plugin. If you want to
    support monochrome devices such as the G15, you will have to take into account
    the amount of space you have (i.e. 6 pixels high maximum and limited width)
    ''' 
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page and not self.screen.is_visible(self.page):
            properties = self._get_properties()
            # Don't display the date or seconds on mono displays, not enough room as it is
            if self.screen.driver.get_bpp() == 1:
                text = properties["time"]
                if self.display_seconds:
                    text = text[:-3]
                font_size = 8
                factor = 2
                font_name = g15globals.fixed_size_font_name
                x = 1
                gap = 1
            else:
                factor = 1 if horizontal else 2
                font_name = "Sans"
                if self.display_date:
                    text = "%s\n%s" % ( properties["time"],properties["date"] ) 
                    font_size = allocated_size / 3
                else:
                    text = properties["time"]
                    font_size = allocated_size / 2
                x = 4
                gap = 8
                
            self.text.set_canvas(canvas)
            self.text.set_attributes(text, align = pango.ALIGN_CENTER, font_desc = font_name, \
                                     font_absolute_size = font_size * pango.SCALE / factor)
            x, y, width, height = self.text.measure()
            if horizontal: 
                if self.screen.driver.get_bpp() == 1:
                    y = 0
                else:
                    y = (allocated_size / 2) - height / 2
            else:      
                x = (allocated_size / 2) - width / 2
                y = 0
            self.text.draw(x, y)
            if horizontal:
                return width + gap
            else:
                return height + 4
    
    ''' 
    ***********************************************************
    * Functions specific to plugin                            *
    ***********************************************************    
    ''' 
        
    def _config_changed(self, client, connection_id, entry, args):
        
        '''
        Load the gconf configuration
        '''
        self._load_configuration()
        
        '''
        This is called when the gconf configuration changes. See add_notify and remove_notify in
        the plugin's activate and deactive functions.
        '''
        
        '''
        Reload the theme as the layout required may have changed (i.e. with the 'show date' 
        option has been change)
        '''
        self._reload_theme()
        self.page.set_theme(self.theme)
        
        '''
        In this case, we temporarily raise the priority of the page. This will force
        the page to be painted (i.e. the paint function invoked). After the specified time,
        the page will revert it's priority. Only one revert timer is active at any one time,
        so it is safe to call this function in quick succession  
        '''
        self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)
        
        
        '''
        Schedule a redraw as well
        '''
        if self.timer is not None:
            self.timer.cancel()
        self._redraw()
        
    def _load_configuration(self):
        self.display_date = self.gconf_client.get_bool(self.gconf_key + "/display_date")
        self.display_seconds = self.gconf_client.get_bool(self.gconf_key + "/display_seconds")
        self.use_24hr_format = self.gconf_client.get_bool(self.gconf_key + "/use_24hr_format")
        
    def _redraw(self):
        '''
        Invoked by the timer once a second to redraw the screen. If your page is currently activem
        then the paint() functions will now get called. When done, we want to schedule the next
        redraw
        '''
        self.screen.redraw(self.page) 
        self._schedule_redraw()
        
    def _schedule_redraw(self):
        if not self.active:
            return
        
        '''
        Determine when to schedule the next redraw for. 
        '''        
        now = datetime.datetime.now()
        if self.display_seconds:
            next_tick = now + datetime.timedelta(0, 1.0)
            next_tick = datetime.datetime(next_tick.year,next_tick.month,next_tick.day,next_tick.hour, next_tick.minute, int(next_tick.second))
        else:
            next_tick = now + datetime.timedelta(0, 60.0)
            next_tick = datetime.datetime(next_tick.year,next_tick.month,next_tick.day,next_tick.hour, next_tick.minute, 0)
        delay = g15util.total_seconds( next_tick - now )
        
        '''
        Try not to create threads or timers if possible. Use g15util.schedule() instead
        '''
        self.timer = g15util.schedule("ClockRedraw", delay, self._redraw)
        
    def _reload_theme(self):        
        variant = None
        if self.display_date:
            variant = "with-date"
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), variant)
        
    '''
    Get the properties dictionary
    '''
    def _get_properties(self):
        properties = { }
        
        '''
        Get the details to display and place them as properties which are passed to
        the theme
        '''
        now = datetime.datetime.now()
        if self.use_24hr_format:
            properties["time"] = g15locale.format_time_24hour(now, self.gconf_client, self.display_seconds)
        else:
            properties["time"] = g15locale.format_time(now, self.gconf_client, self.display_seconds)
        if self.display_date:
            properties["date"] = g15locale.format_date(now, self.gconf_client)
            
        return properties
