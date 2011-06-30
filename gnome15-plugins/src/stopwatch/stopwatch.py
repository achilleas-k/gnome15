#        +-----------------------------------------------------------------------------+
#        | GPL                                                                         |
#        +-----------------------------------------------------------------------------+
#        | Copyright (c) Nuno Araujo <nuno.araujo@russo79.com>                         |
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
 
import gnome15.g15screen as g15screen 
import gnome15.g15theme as g15theme 
import gnome15.g15util as g15util
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import gnome15.g15text as g15text
import datetime
import pango
import os
import timer

import preferences as g15preferences

# Plugin details - All of these must be provided
id="stopwatch"
name="Stopwatch"
description="Stopwatch/Countdown timer plugin for gnome15.\
Two timers are available. User can select the a mode (stopwatch/countdown) for each of them."
author="Nuno Araujo <nuno.araujo@russo79.com>"
copyright="Copyright (C)2011 Nuno Araujo"
site="http://www.gnome15.org/"
has_preferences=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : "Toggle selected timer (or toggle timer 1)", 
         g15driver.NEXT_SELECTION : "Reset selected timer (or reset timer 1)",
         g15driver.NEXT_PAGE : "Toggle timer 2 (G19 only)",
         g15driver.PREVIOUS_PAGE : "Reset timer 2 (G19 only)",
         g15driver.VIEW : "Switch between timers"
         }


# 
# A stopwatch / timer plugin for gnome15
# 

def create(gconf_key, gconf_client, screen):
    return G15Stopwatch(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    preferences = g15preferences.G15StopwatchPreferences(parent, driver, gconf_client, gconf_key)
    preferences.run()


class G15Stopwatch():

    def __init__(self, gconf_key, gconf_client, screen):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._active_timer = None
        self._message = None
        self._page = None
        self._priority = g15screen.PRI_NORMAL

    def activate(self):
        self._timer = None
        self._text = g15text.new_text(self._screen)
        self._notify_timer = None
        self._timer1 = timer.G15Timer()
        self._timer2 = timer.G15Timer()
        self._load_configuration()

        self._reload_theme()

        self._page = g15theme.G15Page(id, self._screen, thumbnail_painter = self.paint_thumbnail, \
                                     priority = self._priority, \
                                     title = name, theme = self.theme, theme_properties_callback = self._get_properties)
        if self._screen.device.bpp == 16:
            """
            Don't show on the panel for G15, there just isn't enough room
            Long term, this will be configurable per plugin
            """
            self._page.panel_painter = self.paint_thumbnail
        self._screen.add_page(self._page)
        self._screen.redraw(self._page)
        self._screen.action_listeners.append(self)
        self._schedule_redraw()
        self._notify_handle = self._gconf_client.notify_add(self._gconf_key, self._config_changed);

    def deactivate(self):
        self._gconf_client.notify_remove(self._notify_handle);
        self._screen.action_listeners.remove(self)
        self._cancel_refresh()
        self._screen.del_page(self._page)

    def destroy(self):
        pass

    def action_performed(self, binding):
        if self._page and self._page.is_visible():
            # G19 we make use of more keys
            if self._screen.driver.get_model_name() == g15driver.MODEL_G19:                
                if self._timer1.get_enabled():
                    if binding.action == g15driver.PREVIOUS_SELECTION:
                        self._timer1.toggle()                        
                        self._check_page_priority()
                        self._redraw()
                    elif binding.action == g15driver.NEXT_SELECTION:
                        self._timer1.reset()
                                    
                if self._timer2.get_enabled():
                    if binding.action == g15driver.PREVIOUS_PAGE:
                        self._timer2.toggle()                        
                        self._check_page_priority()
                        self._redraw()
                    elif binding.action == g15driver.NEXT_PAGE:
                        self._timer2.reset()
            else:
                # For everything else we allow switching between timers
                if binding.action == g15driver.VIEW:
                    if self._active_timer == self._timer1:
                        self._active_timer = self._timer2
                    else:
                        self._active_timer = self._timer1
                    self._redraw()
                
                if self._active_timer:
                    if binding.action == g15driver.PREVIOUS_SELECTION:
                        self._active_timer.toggle()                        
                        self._check_page_priority()
                        self._redraw()
                    elif binding.action == g15driver.NEXT_SELECTION:
                        self._active_timer.reset()                        
                        self._check_page_priority()
                        self._redraw()

    '''
    Paint the thumbnail. You are given the MAXIMUM amount of space that is allocated for
    the thumbnail, and you must return the amount of space actually take up. Thumbnails
    can be used for example by the panel plugin, or the menu plugin. If you want to
    support monochrome devices such as the G15, you will have to take into account
    the amount of space you have (i.e. 6 pixels high maximum and limited width)
    ''' 
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        if not self._screen.service.text_boxes:
            return
        if not self._page or self._screen.is_visible(self._page):
            return
        if not (self._timer1.get_enabled() or self._timer2.get_enabled()):
            return
        properties = self._get_properties()
        # Don't display the date or seconds on mono displays, not enough room as it is
        if self._screen.driver.get_bpp() == 1:
            if self._timer1.get_enabled() and self._timer2.get_enabled():
                text = "%s %s" % ( properties["timer1"], properties["timer2"] ) 
            else:
                text = properties["timer"]
            font_size = 8
            factor = 2
            font_name = g15globals.fixed_size_font_name
            gap = 1
        else:
            factor = 1 if horizontal else 1.2
            font_name = "Sans"
            if self._timer1.get_enabled() and self._timer2.get_enabled():
                text = "%s\n%s" % (properties["timer1"], properties["timer2"])
                font_size = allocated_size / 3
            else:
                text = properties["timer"]
                font_size = allocated_size / 2
            gap = 8
            
        self._text.set_canvas(canvas)
        self._text.set_attributes(text, align = pango.ALIGN_CENTER, font_desc = font_name, font_absolute_size = font_size * pango.SCALE / factor)
        x, y, width, height = self._text.measure()
        if horizontal:
            if self._screen.driver.get_bpp() == 1:
                y = 0
            else:
                y = (allocated_size / 2) - height / 2
        else:
            x = (allocated_size / 2) - width / 2
            y = 0
        self._text.draw(x, y)
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
        self._load_configuration()
        self._reload_theme()
        self._screen.set_priority(self._page, g15screen.PRI_HIGH, revert_after = 3.0)
        
    def _get_or_default(self, key, default_value):
        v = self._gconf_client.get(key)
        return v.get_int() if v != None else default_value
        
    def _load_timer(self, timer_object, number):        
        timer_object.set_enabled(self._gconf_client.get_bool(self._gconf_key + "/timer%d_enabled"  % number) or False)
        timer_object.label = self._gconf_client.get_string(self._gconf_key + "/timer%d_label" % number) or ""
        if self._gconf_client.get_bool(self._gconf_key + "/timer%d_mode_countdown" % number):
            timer_object.mode = timer.G15Timer.TIMER_MODE_COUNTDOWN
            timer_object.initial_value = datetime.timedelta(hours = self._get_or_default(self._gconf_key + "/timer%d_hours" % number, 0), \
                                                     minutes = self._get_or_default(self._gconf_key + "/timer%d_minutes" % number, 5), \
                                                     seconds = self._get_or_default(self._gconf_key + "/timer%d_seconds" % number, 0))
            timer_object.loop = self._gconf_client.get_bool(self._gconf_key + "/timer%d_loop" % number )
        else:
            timer_object.mode = timer.G15Timer.TIMER_MODE_STOPWATCH
            timer_object.initial_value = datetime.timedelta(0, 0, 0)

    def _load_configuration(self):
        self._load_timer(self._timer1, 1)
        self._load_timer(self._timer2, 2)

        # Set active timer
        if self._active_timer == None and self._timer1.get_enabled() and self._timer2.get_enabled():
            self._active_timer = self._timer1
        elif self._timer1.get_enabled() and self._timer2.get_enabled():
            #Keeps the current timer active
            pass
        elif self._timer1.get_enabled():
            self._active_timer = self._timer1
        elif self._timer2.get_enabled():
            self._active_timer = self._timer2
            
        self._check_page_priority()
            
    def _check_page_priority(self):
        self._priority = g15screen.PRI_EXCLUSIVE if self._is_any_timer_active() and g15util.get_bool_or_default(self._gconf_client, "%s/keep_page_visible" % self._gconf_key, True) \
                                                else g15screen.PRI_NORMAL
        if self._page:
            self._page.set_priority(self._priority)

    def _redraw(self):
        self._screen.redraw(self._page) 
        self._schedule_redraw()

    def _cancel_refresh(self):
        if self._timer != None:
            self._timer.cancel()
            self._timer = None

    def _schedule_redraw(self):
        self._cancel_refresh()
        delay = g15util.total_seconds( datetime.timedelta( seconds = 1 ))
        self._timer = g15util.schedule("StopwatchRedraw", delay, self._redraw)

    def _reload_theme(self):        
        variant = None
        if self._timer1.get_enabled() and self._timer2.get_enabled():
            variant = "two_timers"
        elif self._timer1.get_enabled() or self._timer2.get_enabled():
            variant = "one_timer"
        self.theme = g15theme.G15Theme(self, variant)
        if self._page != None:
            self._page.set_theme(self.theme)

    def _get_properties(self):
        properties = { }
        if self._timer1.get_enabled() and self._timer2.get_enabled():
            properties["timer1_label"] = self._timer1.label
            properties["timer1"] = self._format_time_delta(self._timer1.value())
            if self._active_timer == self._timer1:
                properties["timer1_active"] = True
                properties["timer2_active"] = False
            else:
                properties["timer1_active"] = False
                properties["timer2_active"] = True
            properties["timer2_label"] = self._timer2.label
            properties["timer2"] = self._format_time_delta(self._timer2.value())
        elif self._timer1.get_enabled():
            properties["timer_label"] = self._timer1.label
            properties["timer"] = self._format_time_delta(self._timer1.value())
        elif self._timer2.get_enabled():
            properties["timer_label"] = self._timer2.label
            properties["timer"] = self._format_time_delta(self._timer2.value())

        return properties

    def _format_time_delta(self, td): 
        hours = td.seconds // 3600 
        minutes = (td.seconds % 3600) // 60 
        seconds = td.seconds % 60 
        return '%s:%02d:%02d' % (hours, minutes, seconds)
    
    def _is_any_timer_active(self):
        return ( self._timer1 is not None and self._timer1.is_running() ) or \
                ( self._timer2 is not None and self._timer2.is_running() )

# vim:set ts=4 sw=4 et:
