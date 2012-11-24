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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("stopwatch", modfile = __file__).ugettext

import gnome15.g15screen as g15screen 
import gnome15.g15theme as g15theme 
import gnome15.g15util as g15util
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import gnome15.g15plugin as g15plugin
import gnome15.g15text as g15text
import datetime
import pango
import timer

import preferences as g15preferences

# Plugin details - All of these must be provided
id="stopwatch"
name=_("Stopwatch")
description=_("Stopwatch/Countdown timer plugin for gnome15.\
Two timers are available. User can select the a mode (stopwatch/countdown) for each of them.")
author="Nuno Araujo <nuno.araujo@russo79.com>"
copyright=_("Copyright (C)2011 Nuno Araujo")
site="http://www.gnome15.org/"
has_preferences=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Toggle selected timer"), 
         g15driver.NEXT_SELECTION : _("Reset selected timer"),
         g15driver.VIEW : _("Switch between timers")
         }
actions_g19={ 
         g15driver.PREVIOUS_SELECTION : _("Toggle timer 1"), 
         g15driver.NEXT_SELECTION : _("Reset timer 1"),
         g15driver.NEXT_PAGE : _("Toggle timer 2"),
         g15driver.PREVIOUS_PAGE : _("Reset timer 2")
         }


# 
# A stopwatch / timer plugin for gnome15
# 

def create(gconf_key, gconf_client, screen):
    return G15Stopwatch(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    preferences = g15preferences.G15StopwatchPreferences(parent, driver, gconf_client, gconf_key)
    preferences.run()


class G15Stopwatch(g15plugin.G15RefreshingPlugin):

    def __init__(self, gconf_key, gconf_client, screen):
        g15plugin.G15RefreshingPlugin.__init__(self, gconf_client, gconf_key, \
                                               screen, [ "cairo-clock", "clock", "gnome-panel-clock", "xfce4-clock", "rclock", "player-time" ], id, name)
        self._active_timer = None
        self._message = None
        self._priority = g15screen.PRI_NORMAL

    def activate(self):
        self._timer = None
        self._text = g15text.new_text(self.screen)
        self._notify_timer = None
        self._timer1 = timer.G15Timer()
        self._timer1.on_finish = self._on_finish
        self._timer2 = timer.G15Timer()
        self._timer2.on_finish = self._on_finish
        self._load_configuration()
        
        g15plugin.G15RefreshingPlugin.activate(self)

        self.screen.key_handler.action_listeners.append(self)
        self.watch(None, self._config_changed)

    def deactivate(self):
        if self._timer1.is_running():
            self._timer1.toggle()
        if self._timer2.is_running():
            self._timer2.toggle()
        self.screen.key_handler.action_listeners.remove(self)
        g15plugin.G15RefreshingPlugin.deactivate(self)

    def destroy(self):
        pass
    
    def create_page(self):
        page = g15plugin.G15RefreshingPlugin.create_page(self)
        if self.screen.driver.get_bpp() != 16:
            """
            Don't show on the panel for G15, there just isn't enough room
            Long term, this will be configurable per plugin
            """
            page.panel_painter = None
        return page
    
    def create_theme(self):
        variant = None
        if self._timer1.get_enabled() and self._timer2.get_enabled():
            variant = "two_timers"
        elif self._timer1.get_enabled() or self._timer2.get_enabled():
            variant = "one_timer"
        return g15theme.G15Theme(self, variant)

    def action_performed(self, binding):
        if self.page and self.page.is_visible():
            # G19 we make use of more keys
            if self.screen.driver.get_model_name() == g15driver.MODEL_G19:                
                if self._timer1.get_enabled():
                    if binding.action == g15driver.PREVIOUS_SELECTION:
                        self._timer1.toggle()                        
                        self._check_page_priority()
                        self._refresh()
                    elif binding.action == g15driver.NEXT_SELECTION:
                        self._timer1.reset()
                                    
                if self._timer2.get_enabled():
                    if binding.action == g15driver.PREVIOUS_PAGE:
                        self._timer2.toggle()                        
                        self._check_page_priority()
                        self._refresh()
                    elif binding.action == g15driver.NEXT_PAGE:
                        self._timer2.reset()
            else:
                # For everything else we allow switching between timers
                if binding.action == g15driver.VIEW:
                    if self._active_timer == self._timer1:
                        self._active_timer = self._timer2
                    else:
                        self._active_timer = self._timer1
                    self._refresh()
                
                if self._active_timer:
                    if binding.action == g15driver.PREVIOUS_SELECTION:
                        self._active_timer.toggle()                        
                        self._check_page_priority()
                        self._refresh()
                    elif binding.action == g15driver.NEXT_SELECTION:
                        self._active_timer.reset()                        
                        self._check_page_priority()
                        self._refresh()
                        
    def get_next_tick(self):
        return g15util.total_seconds( datetime.timedelta( seconds = 1 ))
    
    def get_theme_properties(self):
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
    
    def _paint_panel(self, canvas, allocated_size, horizontal):
        if not self.page or self.screen.is_visible(self.page):
            return
        if not (self._timer1.get_enabled() or self._timer2.get_enabled()):
            return
        if not (self._timer1.is_running() or self._timer2.is_running()):
            return
        properties = self.get_theme_properties()
        # Don't display the date or seconds on mono displays, not enough room as it is
        if self.screen.driver.get_bpp() == 1:
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
            if self.screen.driver.get_bpp() == 1:
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
        self.reload_theme()
        self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)
        
    def _get_or_default(self, key, default_value):
        v = self.gconf_client.get(key)
        return v.get_int() if v != None else default_value
        
    def _load_timer(self, timer_object, number):        
        timer_object.set_enabled(self.gconf_client.get_bool(self.gconf_key + "/timer%d_enabled"  % number) or False)
        timer_object.label = self.gconf_client.get_string(self.gconf_key + "/timer%d_label" % number) or ""
        if self.gconf_client.get_bool(self.gconf_key + "/timer%d_mode_countdown" % number):
            timer_object.mode = timer.G15Timer.TIMER_MODE_COUNTDOWN
            timer_object.initial_value = datetime.timedelta(hours = self._get_or_default(self.gconf_key + "/timer%d_hours" % number, 0), \
                                                     minutes = self._get_or_default(self.gconf_key + "/timer%d_minutes" % number, 5), \
                                                     seconds = self._get_or_default(self.gconf_key + "/timer%d_seconds" % number, 0))
            timer_object.loop = self.gconf_client.get_bool(self.gconf_key + "/timer%d_loop" % number )
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
        self._priority = g15screen.PRI_EXCLUSIVE if self._is_any_timer_active() and g15util.get_bool_or_default(self.gconf_client, "%s/keep_page_visible" % self.gconf_key, True) \
                                                else g15screen.PRI_NORMAL
        if self.page:
            self.page.set_priority(self._priority)

    def _format_time_delta(self, td): 
        hours = td.seconds // 3600 
        minutes = (td.seconds % 3600) // 60 
        seconds = td.seconds % 60 
        return '%s:%02d:%02d' % (hours, minutes, seconds)
    
    def _is_any_timer_active(self):
        return ( self._timer1 is not None and self._timer1.is_running() ) or \
                ( self._timer2 is not None and self._timer2.is_running() )
                
    def _on_finish(self):
        self._check_page_priority()

# vim:set ts=4 sw=4 et:
