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
import datetime
import pango
import os
import timer

import preferences as g15preferences

# Plugin details - All of these must be provided
id="stopwatch"
name="Stopwatch"
description="Stopwatch/Countdown timer plugin for gnome15.\
Two timers are available. User can select the a mode (stopwatch/countdown) for each of them.\
Use the D-pad or the L3-L5 keys to start/pause and reset the timers."
author="Nuno Araujo <nuno.araujo@russo79.com>"
copyright="Copyright (C)2011 Nuno Araujo"
site="http://www.gnome15.org/"
has_preferences=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]


# 
# A stopwatch / timer plugin for gnome15
# 

def create(gconf_key, gconf_client, screen):
    return G15Stopwatch(gconf_key, gconf_client, screen)

def show_preferences(parent, device, gconf_client, gconf_key):
    preferences = g15preferences.G15StopwatchPreferences(parent, device, gconf_client, gconf_key)
    preferences.run()


class G15Stopwatch():

    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.active_timer = None
        self.message = None
        self.page = None

    def activate(self):
        self.timer = None
        self.notify_timer = None
        self.timer1 = timer.G15Timer()
        self.timer2 = timer.G15Timer()
        self.load_configuration()

        self._reload_theme()

        if self.screen.device.bpp == 16:
            self.page = g15theme.G15Page(id, self.screen, thumbnail_painter = self.paint_thumbnail, \
                                         panel_painter = self.paint_thumbnail, title = name,
                                         theme = self.theme, theme_properties_callback = self._get_properties)
        else:
            """
            Don't show on the panel for G15, there just isn't enough room
            Long term, this will be configurable per plugin
            """
            self.page = g15theme.G15Page(id, self.screen, thumbnail_painter = self.paint_thumbnail, \
                                         title = name,
                                         theme = self.theme)
        self.screen.add_page(self.page)
        self.screen.redraw(self.page)
        self._schedule_redraw()
        self.notify_handle = self.gconf_client.notify_add(self.gconf_key, self._config_changed);

    def deactivate(self):
        self.gconf_client.notify_remove(self.notify_handle);
        self._cancel_refresh()
        self.screen.del_page(self.page)

    def destroy(self):
        pass

    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP and self.screen.get_visible_page() == self.page:
            if self.timer1.get_enabled() and self.timer2.get_enabled():
                if g15driver.G_KEY_UP in keys:
                    self.timer1.toggle()
                    self._redraw()
                    return True
                if g15driver.G_KEY_DOWN in keys:
                    self.timer1.reset()
                    self._redraw()
                    return True
                if g15driver.G_KEY_LEFT in keys:
                    self.timer2.toggle()
                    self._redraw()
                    return True
                if g15driver.G_KEY_RIGHT in keys:
                    self.timer2.reset()
                    self._redraw()
                    return True
                if g15driver.G_KEY_L3 in keys:
                    self.active_timer.toggle()
                    self._redraw()
                    return True
                if g15driver.G_KEY_L4 in keys:
                    self.active_timer.reset()
                    self._redraw()
                    return True
                if g15driver.G_KEY_L5 in keys:
                    if self.active_timer == self.timer1:
                        self.active_timer = self.timer2
                    else:
                        self.active_timer = self.timer1
                    self._redraw()
                    return True
            elif self.timer1.get_enabled():
                self.active_timer = self.timer1
                if g15driver.G_KEY_UP in keys or g15driver.G_KEY_L3 in keys:
                    self.active_timer.toggle()
                    self._redraw()
                    return True
                if g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L4 in keys:
                    self.active_timer.reset()
                    self._redraw()
                    return True
            elif self.timer2.get_enabled():
                self.active_timer = self.timer2
                if g15driver.G_KEY_UP in keys or g15driver.G_KEY_L3 in keys:
                    self.active_timer.toggle()
                    self._redraw()
                    return True
                if g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L4 in keys:
                    self.active_timer.reset()
                    self._redraw()
                    return True

    def draw(self, element, theme):
        timer_label = None
        other_timer_label = None
        if self.active_timer == self.timer1:
            timer_label = theme.get_element("timer1_label")
            other_timer_label = theme.get_element("timer2_label")
        elif self.active_timer == self.timer2:
            timer_label = theme.get_element("timer2_label")
            other_timer_label = theme.get_element("timer1_label")
        if timer_label != None:
            styles = theme.parse_css(timer_label.get("style"))
            styles["font-weight"] = "bold"
            timer_label.set("style", theme.format_styles(styles))
        if other_timer_label != None:
            styles = theme.parse_css(other_timer_label.get("style"))
            styles["font-weight"] = "normal"
            other_timer_label.set("style", theme.format_styles(styles))

    '''
    Paint the thumbnail. You are given the MAXIMUM amount of space that is allocated for
    the thumbnail, and you must return the amount of space actually take up. Thumbnails
    can be used for example by the panel plugin, or the menu plugin. If you want to
    support monochrome devices such as the G15, you will have to take into account
    the amount of space you have (i.e. 6 pixels high maximum and limited width)
    ''' 
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        if not self.page or self.screen.is_visible(self.page):
            return
        if not (self.timer1.get_enabled() or self.timer2.get_enabled()):
            return
        properties = self._get_properties()
        # Don't display the date or seconds on mono displays, not enough room as it is
        if self.screen.driver.get_bpp() == 1:
            if self.timer1.get_enabled() and self.timer2.get_enabled():
                text = "%s %s" % ( properties["timer1"], properties["timer2"] ) 
            else:
                text = properties["timer"]
            font_size = 8
            factor = 2
            font_name = g15globals.fixed_size_font_name
            gap = 1
        else:
            factor = 1 if horizontal else 2
            font_name = "Sans"
            if self.timer1.get_enabled() and self.timer2.get_enabled():
                text = "%s\n%s" % (properties["timer1"], properties["timer2"])
                font_size = allocated_size / 3
            else:
                text = properties["timer"]
                font_size = allocated_size / 2
            gap = 8

        pango_context, layout = g15util.create_pango_context(canvas, self.screen, text, align = pango.ALIGN_CENTER, font_desc = font_name, font_absolute_size =  font_size * pango.SCALE / factor)
        x, y, width, height = g15util.get_extents(layout)
        if horizontal:
            if self.screen.driver.get_bpp() == 1:
                y = 0
            else:
                y = (allocated_size / 2) - height / 2
            pango_context.move_to(x, y)
        else:
            pango_context.move_to((allocated_size / 2) - width / 2, 0)
        pango_context.update_layout(layout)
        pango_context.show_layout(layout)
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
        self.load_configuration()
        self._reload_theme()
        self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)
        
    def _get_or_default(self, key, default_value):
        v = self.gconf_client.get(key)
        return v.get_int() if v != None else default_value
        
    def _load_timer(self, timer_object, number):        
        timer_object.set_enabled(self.gconf_client.get_bool(self.gconf_key + "/timer" + str(number) + "_enabled") or False)
        timer_object.label = self.gconf_client.get_string(self.gconf_key + "/timer" + str(number) + "_label") or ""
        if self.gconf_client.get_bool(self.gconf_key + "/timer" + str(number) + "_mode_countdown"):
            timer_object.mode = timer.G15Timer.TIMER_MODE_COUNTDOWN
            timer_object.initial_value = datetime.timedelta(hours = self._get_or_default(self.gconf_key + "/timer1_hours", 0), \
                                                     minutes = self._get_or_default(self.gconf_key + "/timer1_minutes", 5), \
                                                     seconds = self._get_or_default(self.gconf_key + "/timer1_seconds", 0))
            timer_object.loop = self.gconf_client.get_bool(self.gconf_key + "/timer" + number + "_loop")
        else:
            timer_object.mode = timer.G15Timer.TIMER_MODE_STOPWATCH
            timer_object.initial_value = datetime.timedelta(0, 0, 0)

    def load_configuration(self):
        self._load_timer(self.timer1, '1')
        self._load_timer(self.timer2, '2')

        # Set active timer
        if self.active_timer == None and self.timer1.get_enabled() and self.timer2.get_enabled():
            self.active_timer = self.timer1
        elif self.timer1.get_enabled() and self.timer2.get_enabled():
            #Keeps the current timer active
            pass
        elif self.timer1.get_enabled():
            self.active_timer = self.timer1
        elif self.timer2.get_enabled():
            self.active_timer = self.timer2

    def _redraw(self):
        self.screen.redraw(self.page) 
        self._schedule_redraw()

    def _cancel_refresh(self):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None

    def _schedule_redraw(self):
        self._cancel_refresh()
        delay = g15util.total_seconds( datetime.timedelta( seconds = 1 ))
        self.timer = g15util.schedule("StopwatchRedraw", delay, self._redraw)

    def _reload_theme(self):        
        variant = None
        if self.timer1.get_enabled() and self.timer2.get_enabled():
            variant = "two_timers"
        elif self.timer1.get_enabled() or self.timer2.get_enabled():
            variant = "one_timer"
        self.theme = g15theme.G15Theme(self, variant)
        if self.page != None:
            self.page.set_theme(self.theme)

    def _get_properties(self):
        properties = { }
        if self.timer1.get_enabled() and self.timer2.get_enabled():
            properties["timer1_label"] = self.timer1.label
            properties["timer1"] = self.__format_time_delta(self.timer1.value())
            properties["timer2_label"] = self.timer2.label
            properties["timer2"] = self.__format_time_delta(self.timer2.value())
        elif self.timer1.get_enabled():
            properties["timer_label"] = self.timer1.label
            properties["timer"] = self.__format_time_delta(self.timer1.value())
        elif self.timer2.get_enabled():
            properties["timer_label"] = self.timer2.label
            properties["timer"] = self.__format_time_delta(self.timer2.value())

        return properties

    def __format_time_delta(self, td): 
        hours = td.seconds // 3600 
        minutes = (td.seconds % 3600) // 60 
        seconds = td.seconds % 60 
        return '%s:%02d:%02d' % (hours, minutes, seconds) 

# vim:set ts=4 sw=4 et:
