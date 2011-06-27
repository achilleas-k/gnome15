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
 
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import datetime
import time
import os
import evolution.ecal
import vobject
import gobject
import calendar

id="cal"
name="Calendar"
description="Calendar. Integrates with Evolution calendar. " \
    + "You may move around the calendar using the D-Pad on the G19, " \
    + "or using the right most 3 keys under the " \
    + "display (L3-L5) on other models."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_MX5500 ]

# How often refresh from the evolution calendar. This can be a slow process, so not too often
REFRESH_INTERVAL = 15 * 60.0

def create(gconf_key, gconf_client, screen):
    return G15Cal(gconf_key, gconf_client, screen)

class EventMenuItem(g15theme.MenuItem):
    
    def __init__(self,  event, id):
        g15theme.MenuItem.__init__(self, id)
        self.event = event
    
    def get_default_theme_dir(self):
        return os.path.join(os.path.dirname(__file__), "default")
        
    def get_theme_properties(self):        
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self.event.summary.value
        item_properties["item_alt"] = "%s-%s" % ( self.event.dtstart.value.strftime("%H:%M"), self.event.dtend.value.strftime("%H:%M")) 
        try :
            self.event.valarm            
            item_properties["item_icon"] = g15util.get_icon_path([ "stock_alarm", "alarm-clock", "alarm-timer", "dialog-warning" ])
        except AttributeError:
            pass
        return item_properties
    
class Cell(g15theme.Component):
    def __init__(self, day, now, event, id):
        g15theme.Component.__init__(self, id)
        self.day = day
        self.now = now
        self.event = event
        
    def on_configure(self):  
        self.set_theme(g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), "cell"))
        
    def get_theme_properties(self):
        weekday = self.day.weekday()        
        properties = {}
        properties["weekday"] = weekday
        properties["day"] = self.day.day
        properties["event"] = self.event[0].summary.value if self.event else ""    
        if self.now.day == self.day.day and self.now.month == self.day.month:
            properties["today"] = True
        return properties
        
    def get_item_attributes(self, selected):
        return {}
    
class Calendar(g15theme.Component):
    
    def __init__(self, id="calendar"):
        g15theme.Component.__init__(self, id)
        self.layout_manager = g15theme.GridLayoutManager(7)
        self.focusable = True
        
class G15Cal():  
    
    def __init__(self, gconf_key, gconf_client, screen):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._timer = None
        self._thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path(["calendar", "evolution-calendar", "office-calendar", "stock_calendar" ]))
    
    def activate(self):
        self._active = True
        self._event_days = None
        self._calendar_date = None
        self._loaded = 0
        self._page = None
        self._theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), auto_dirty = False)
        self._loaded = time.time()
        
        # Calendar
        self._calendar = Calendar()
        
        # Menu
        self._menu = g15theme.Menu("menu")
        self._menu.focusable = True
        
        # Page
        self._page = g15theme.G15Page(name, self._screen, on_shown = self._on_shown, \
                                     on_hidden = self._on_hidden, theme_properties_callback = self._get_properties,
                                     thumbnail_painter = self._paint_thumbnail)
        self._page.set_title("Evolution Calendar")
        self._page.set_theme(self._theme)
        self._page.add_child(self._menu)
        self._page.add_child(self._calendar)
        self._page.add_child(g15theme.Scrollbar("viewScrollbar", self._menu.get_scroll_values))
        
        # Screen
        self._screen.add_page(self._page)
        self._screen.action_listeners.append(self)
        self._calendar.set_focused(True)
        
        gobject.idle_add(self._first_load)
        
    def deactivate(self):
        self._screen.action_listeners.remove(self)
        if self._timer != None:
            self._timer.cancel()
        if self._page != None:
            self._screen.del_page(self._page)
        
    def destroy(self):
        pass
                    
    def action_performed(self, binding):
        if self._page and self._page.is_visible():
            if self._calendar.is_focused():
                if binding.action == g15driver.PREVIOUS_PAGE:
                    self._adjust_calendar_date(-1)
                elif binding.action == g15driver.NEXT_PAGE:
                    self._adjust_calendar_date(1)
                elif binding.action == g15driver.PREVIOUS_SELECTION:
                    self._adjust_calendar_date(-7)
                elif binding.action == g15driver.NEXT_SELECTION:
                    self._adjust_calendar_date(7)
                elif binding.action == g15driver.CLEAR:
                    self._calendar_date = None
                    self._loaded_minute =- -1
                    self._screen.redraw(self._page)
            if binding.action == g15driver.VIEW:
                self._page.next_focus()
    
    """
    Private
    """
                    
    def _adjust_calendar_date(self, amount):
        if self._calendar_date == None:
            self._calendar_date = datetime.datetime.now()
        self._calendar_date = self._calendar_date + datetime.timedelta(amount)
        self._load_month_events(self._calendar_date)
        self._screen.redraw(self._page) 
        
    def _first_load(self):
        self._load_month_events(datetime.datetime.now())
        self._screen.redraw(self._page)
        self._schedule_redraw()
    
    def _get_calendar_date(self):
        now = datetime.datetime.now()
        return self._calendar_date if self._calendar_date is not None else now
        
    def _get_properties(self):
        now = datetime.datetime.now()
        calendar_date = self._get_calendar_date()
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
        properties["cal_year"] = calendar_date.strftime("%Y")
        properties["cal_month"] = calendar_date.strftime("%m")
        properties["cal_month_name"] = calendar_date.strftime("%B")
        properties["cal_short_month_name"] = calendar_date.strftime("%b")
        properties["cal_year"] = calendar_date.strftime("%Y")
        properties["cal_short_year"] = calendar_date.strftime("%y")
        properties["cal_locale_date"] = calendar_date.strftime("%x")
        if self._event_days is None or not str(calendar_date.day) in self._event_days:
            properties["message"] = "No events"
        else:
            properties["events"] = True
        return properties
    
    def _load_month_events(self, now):
        self._event_days = {}
        
        for c in self._page.get_children():
            if isinstance(c, Cell):
                pass
            
        # Get all the events for this month
        for i in evolution.ecal.list_calendars():
            ecal = evolution.ecal.open_calendar_source(i[1], evolution.ecal.CAL_SOURCE_TYPE_EVENT)
            for i in ecal.get_all_objects():
                parsed_event = vobject.readOne(i.get_as_string())
                event_date = parsed_event.dtstart.value
                if parsed_event.dtend:
                    end_event_date = parsed_event.dtend.value
                else:
                    end_event_date = datetime.datetime(event_date.year,event_date.month,event_date.day, 23, 59, 0)
                
                if event_date.month == now.month and event_date.year == now.year:
                    print "Event %s to %s" % (str(event_date), str(end_event_date))
                    
                    day = event_date.day
                    while day <= end_event_date.day:
                        key = str(day)
                        list = []
                        if key in self._event_days:
                            list = self._event_days[key]
                        else:
                            self._event_days[key] = list
                        list.append(parsed_event)
                        day += 1
                    
        # Set the events
        self._menu.remove_all_children()
        if str(now.day) in self._event_days:
            events = self._event_days[str(now.day)]
            i = 0
            for event in events:
                self._menu.add_child(EventMenuItem(event, id = "menuItem-%d" % i))
                i += 1
            
        # Add the date cell components
        self._calendar.remove_all_children()
        cal = calendar.Calendar()
        i = 0
        for day in cal.itermonthdates(now.year, now.month):
            event = None
            if str(day.day) in self._event_days:
                event = self._event_days[str(day.day)]                
            self._calendar.add_child(Cell(day, now, event, "cell-%d" % i))
            i += 1
            
        self._page.mark_dirty()
        
    def _schedule_redraw(self):
        if self._screen.is_visible(self._page):
            self._timer = g15util.schedule("CalRedraw", 60.0, self._redraw)
        
    def _on_shown(self):
        self._hidden = False
        self._redraw()
        
    def _on_hidden(self):
        if self._timer != None:
            self._timer.cancel()
        self._calendar_date = None
        self._loaded_minute = -1
        
    def _redraw(self):
        t = time.time()
        if t > self._loaded + REFRESH_INTERVAL:
            self._loaded = t
            self._load_month_events(datetime.datetime.now())
        self._screen.redraw(self._page)
        self._schedule_redraw()
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self._page != None and self._thumb_icon != None and self._screen.driver.get_bpp() == 16:
            return g15util.paint_thumbnail_image(allocated_size, self._thumb_icon, canvas)