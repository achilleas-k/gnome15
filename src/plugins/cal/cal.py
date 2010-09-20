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
import calendar
import evolution.ecal
import vobject

id="cal"
name="Calendar"
description="Clock & Calendar. Integrates with Evolution calendar"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://localhost"
has_preferences=True

def create(gconf_key, gconf_client, screen):
    return G15Cal(gconf_key, gconf_client, screen)

class G15Cal():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def activate(self):
        self.active = True 
        self.timer = None
        self.event_days = None
        self.loaded_minute = 0
        self.load_month_events(datetime.datetime.now())
        self.canvas = self.screen.new_canvas(priority=g15screen.PRI_NORMAL, on_shown=self.on_shown, on_hidden=self.on_hidden, id="Cal")
        self.screen.draw_current_canvas()
    
    def deactivate(self):
        self.screen.del_canvas(self.canvas)
        
    def destroy(self):
        pass
    
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
        
    def load_month_events(self, now):
        self.loaded_minute = now.minute
        self.event_days = {}
            
        # Get all the events for this month
        for i in evolution.ecal.list_calendars():
            ecal = evolution.ecal.open_calendar_source(i[1], evolution.ecal.CAL_SOURCE_TYPE_EVENT)
            for i in ecal.get_all_objects():
                parsed_event = vobject.readOne(i.get_as_string())
                event_date = parsed_event.dtstart.value
                if event_date.month == now.month and event_date.year == now.year:
                    key = str(event_date.day)
                    list = []
                    if key in self.event_days:
                        list = self.event_days[key]
                    else:
                        self.event_days[key] = list
                    list.append(parsed_event)
        
    def redraw(self):
        if not self.hidden:
            self.canvas.clear()
            time_format = "%H:%M"
            now = datetime.datetime.now()

            self.canvas.set_font_size(g15draw.FONT_SMALL)
            self.canvas.draw_text(now.strftime("%H:%M"), (22, 0))
            self.canvas.draw_text(now.strftime("%a %d %b"), (8, 9))
            
            # Only load the events every minute
            if self.event_days == None or self.loaded_minute != now.minute:
                self.load_month_events(now)
                
            # Draw calendar
            self.canvas.set_font_size(g15draw.FONT_TINY)
            cal = calendar.Calendar()
            
            y = 1
            self.canvas.fill_box((72, 0, self.screen.driver.get_size()[0], 7), color="Black")
            x = 76
            for day in [ "M", "T", "W", "T", "F", "S", "S"]:
                self.canvas.draw_text("%s" % day, (x, y), color="White")
                x += 12
                
            y = 9
            ld = -1
            for day in cal.itermonthdates(now.year, now.month):
                weekday = day.weekday()
                if weekday < ld:
                    y += 7
                ld = weekday
                x = 72 + ( weekday * 12 )
                color = "Black"
                if str(day.day) in self.event_days:
                    event = self.event_days[str(day.day)]
                    self.canvas.fill_box((x,y - 1, x + 12, y + 6), color = "Black")
                    color = "White"
                self.canvas.draw_text("%2d" % day.day, (x + 1, y), color = color)
                
            # Summary for today
            if str(now.day) in self.event_days:
                y = 23
                for event in self.event_days[str(now.day)]:
                    self.canvas.draw_text(event.summary.value[:14], (0, y))
                    try :
                        event.valarm
                        self.canvas.fill_box((62, y - 1, 69, y + 6), "White")
                        self.canvas.draw_image_from_file(os.path.join(os.path.dirname(__file__), "bell.gif"), (62, y - 1), size=(7,7))
                    except AttributeError:
                        pass
                    y += 7
                    if y > self.screen.driver.get_size()[1]:
                        break
                        
            # Separator line
            self.canvas.draw_line((70, 0, 70, self.screen.driver.get_size()[1]), "Gray")
            self.canvas.draw_line((0, 21, 70, 21), "Gray")
                
                
            self.screen.draw(self.canvas)
            
            self.timer = Timer(1, self.redraw, ())
            self.timer.name = "CalRedrawTimer"
            self.timer.setDaemon(True)
            self.timer.start()
