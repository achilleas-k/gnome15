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
import gnome15.g15_driver as g15driver
import gnome15.g15_util as g15util
import datetime
import time
from threading import Timer
from threading import Thread
import gtk
import os
import sys
import calendar
import evolution.ecal
import vobject

id="cal"
name="Calendar"
description="Clock & Calendar. Integrates with Evolution calendar. " \
    + "You may move around the calendar using the cursor keys near " \
    + "the display on the G19, or using the right most 4 keys under the " \
    + "display (L2-L5)."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False

# How often refresh from the evolution calendar. This can be a slow process, so not too often
REFRESH_INTERVAL = 15 * 60.0

def create(gconf_key, gconf_client, screen):
    return G15Cal(gconf_key, gconf_client, screen)  
    
class StartUp(Thread):
    def __init__(self, plugin):
        Thread.__init__(self)
        self.plugin = plugin
        self.setDaemon(True)
        self.start()
        self.cancelled = False
        
    def cancel(self):
        self.cancelled = True
        
    def run(self):            
        self.plugin.loaded = time.time()
        self.plugin.load_month_events(datetime.datetime.now())
        if not self.cancelled:
            self.plugin.page = self.plugin.screen.new_page(self.plugin.paint, priority=g15screen.PRI_NORMAL, on_shown=self.plugin.on_shown, on_hidden=self.plugin.on_hidden, id="Cal")
            self.plugin.page.set_title("Evolution Calendar")
            self.plugin.screen.redraw(self.plugin.page)
            self.plugin.schedule_redraw()

class G15Cal():  
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.timer = None
    
    def activate(self):
        self.active = True
        self.event_days = None
        self.calendar_date = None
        self.loaded = 0
        self.page = None
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
        
        # Complete startup in a thread as the calendar may take a while to become available
        self.startup = StartUp(self)
        
    def redraw(self):
        t = time.time()
        if t > self.loaded + REFRESH_INTERVAL:
            self.loaded = t
            self.load_month_events(datetime.datetime.now())
            
        self.screen.redraw(self.page)
        self.schedule_redraw()
        
    def schedule_redraw(self):
        if self.screen.is_visible(self.page):
            self.timer = g15util.schedule("CalRedraw", 1.0, self.redraw)
        
    def on_shown(self):
        self.hidden = False
        self.redraw()
        
    def on_hidden(self):
        if self.timer != None:
            self.timer.cancel()
        self.calendar_date = None
        self.loaded_minute = -1
        
    def deactivate(self):
        if self.startup != None:
            self.startup.cancel()
        if self.timer != None:
            self.timer.cancel()
        if self.page != None:
            self.screen.del_page(self.page)
        
    def destroy(self):
        pass
    
    def load_month_events(self, now):
        self.event_days = {}
        print "Loading calendar events"
            
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
                    
        print "Loaded calendar events"
                    
    def adjust_calendar_date(self, amount):
        if self.calendar_date == None:
            self.calendar_date = datetime.datetime.now()
        self.calendar_date = self.calendar_date + datetime.timedelta(amount)
        self.load_month_events(self.calendar_date)
        self.screen.redraw(self.page) 
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP and self.screen.get_visible_page() == self.page:
            if g15driver.G_KEY_UP in keys or g15driver.G_KEY_L3 in keys:
                self.screen.applet.resched_cycle()
                self.adjust_calendar_date(-7)
                return True
            elif g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L4 in keys:
                self.screen.applet.resched_cycle()
                self.adjust_calendar_date(7)
                return True
            elif g15driver.G_KEY_LEFT in keys or g15driver.G_KEY_L2 in keys:
                self.screen.applet.resched_cycle()
                self.adjust_calendar_date(-1)
                return True
            elif g15driver.G_KEY_RIGHT in keys or g15driver.G_KEY_L5 in keys:
                self.screen.applet.resched_cycle()
                self.adjust_calendar_date(1)
                return True
            elif g15driver.G_KEY_BACK in keys:
                self.screen.applet.resched_cycle()
                self.calendar_date = None
                self.loaded_minute =- -1
                self.screen.redraw(self.page)
                return True
                
        return False
        
    def paint(self, canvas):
        time_format = "%H:%M"
        now = datetime.datetime.now()
        
        properties = {}
        properties["time_24"] = now.strftime("%H:%M") 
        properties["full_time_24"] = now.strftime("%H:%M:%S") 
        properties["time_12"] = now.strftime("%I:%M %p") 
        properties["full_time_12"] = now.strftime("%I:%M:%S %p")
        properties["short_date"] = now.strftime("%a %d %b")
        properties["full_date"] = now.strftime("%A %d %B")
        properties["locale_date"] = now.strftime("%x")
        properties["locale_time"] = now.strftime("%X")
        properties["year"] = now.strftime("%Y")
        properties["short_year"] = now.strftime("%y")
        properties["week"] = now.strftime("%W")
        properties["month"] = now.strftime("%m")
        properties["month_name"] = now.strftime("%B")
        properties["short_month_name"] = now.strftime("%b")
        properties["day_name"] = now.strftime("%A")
        properties["short_day_name"] = now.strftime("%a")
        properties["day_of_year"] = now.strftime("%d")
        
        calendar_date = now
        if self.calendar_date != None:
            calendar_date = self.calendar_date
            
        properties["cal_year"] = calendar_date.strftime("%Y")
        properties["cal_month"] = calendar_date.strftime("%m")
        properties["cal_month_name"] = calendar_date.strftime("%B")
        properties["cal_short_month_name"] = calendar_date.strftime("%b")
        properties["cal_year"] = calendar_date.strftime("%Y")
        properties["cal_short_year"] = calendar_date.strftime("%y")
        properties["cal_locale_date"] = calendar_date.strftime("%x")
        
        if not str(calendar_date.day) in self.event_days:
            properties["message"] = "No events"
        else:
            properties["events"] = True
        
        attributes = {
                      "now" : calendar_date,
                      "event_days" : self.event_days
                      }
         
            
        self.theme.draw(canvas, properties, attributes)