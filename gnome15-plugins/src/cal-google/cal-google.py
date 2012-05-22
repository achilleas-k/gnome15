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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("cal-evolution", modfile = __file__).ugettext

import cal
 
id="cal-google"
name=_("Calendar (Google support)")
description=_("Adds your Google Calendar as a source for the Gnome15 Calendar plugin")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2012 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=False
requires="cal"
unsupported_models=cal.unsupported_models

# How often refresh from the evolution calendar. This can be a slow process, so not too often
REFRESH_INTERVAL = 15 * 60

def create(gconf_key, gconf_client, screen):
    return G15CalendarGoogle(gconf_key, gconf_client, screen)

class GoogleEvent(cal.CalendarEvent):
    
    def __init__(self, parsed_event):
        CalendarEvent.__init__(self)
        
        self.start_date = parsed_event.dtstart.value
        if parsed_event.dtend:
            self.end_date = parsed_event.dtend.value
        else:
            self.end_date = datetime.datetime(self.start_date.year,self.start_date.month,self.start_date.day, 23, 59, 0)
            
        self.summary = parsed_event.summary.value
        
class GoogleBackend(cal.CalendarBackend):
    
    def __init__(self):
        CalendarBackend.__init__(self)
        
    def get_events(self, now):
        
        import evolution.ecal
        import vobject
        
        event_days = {}
        
        # Get all the events for this month
        for i in evolution.ecal.list_calendars():
            ecal = evolution.ecal.open_calendar_source(i[1], evolution.ecal.CAL_SOURCE_TYPE_EVENT)
            for i in ecal.get_all_objects():
                parsed_event = vobject.readOne(i.get_as_string())
                ve = EvolutionEvent(parsed_event)
                
                if ve.start_date.month == now.month and ve.start_date.year == now.year:
                    day = ve.start_date.day
                    while day <= ve.start_date.day:
                        key = str(day)
                        day_event_list = []
                        if key in event_days:
                            day_event_list = event_days[key]
                        else:
                            event_days[key] = day_event_list
                        list.append(ve)
                        day += 1
                        
        return event_days

class G15CalendarGoogle(cal.G15Cal):  
    
    def __init__(self, gconf_key, gconf_client, screen):
        cal.G15Cal.__init__(self, gconf_key, gconf_client, screen)
        
    def create_backend(self):
        return GoogleBackend()
    