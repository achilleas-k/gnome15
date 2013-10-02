#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2012 Brett Smith <tanktarta@blueyonder.co.uk>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 
"""
Calendar backend that retrieves event data from Evolution
"""
 
import gnome15.g15locale as g15locale
import gnome15.g15accounts as g15accounts
_ = g15locale.get_translation("cal-evolution", modfile = __file__).ugettext
import gtk
import urllib
import vobject
import datetime
import dateutil
import sys, os
import re
import cal
 
"""
Plugin definition
"""
id="cal-evolution"
name=_("Calendar (Evolution support)")
description=_("Calendar for Evolution. Adds Evolution as a source for calendars \
to the Calendar plugin")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2012 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=False
global_plugin=True
passive=True
unsupported_models=cal.unsupported_models

"""
Calendar Back-end module functions
"""
def create_options(account, account_ui):
    return EvolutionCalendarOptions(account, account_ui)

def create_backend(account, account_manager):
    return EvolutionBackend()

class EvolutionCalendarOptions(g15accounts.G15AccountOptions):
    def __init__(self, account, account_ui):
        g15accounts.G15AccountOptions.__init__(self, account, account_ui)
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "cal-evolution.ui"))
        self.component = self.widget_tree.get_object("OptionPanel")
        try :
            self.event.valarm
            self.alarm = True
        except AttributeError:
            pass

class EvolutionEvent(cal.CalendarEvent):
    
    def __init__(self, parsed_event):
        cal.CalendarEvent.__init__(self)
        
        self.start_date = parsed_event.dtstart.value
        if parsed_event.dtend:
            self.end_date = parsed_event.dtend.value
        else:
            self.end_date = datetime.datetime(self.start_date.year,self.start_date.month,self.start_date.day, 23, 59, 0)
            
        self.summary = parsed_event.summary.value
        self.alt_icon = os.path.join(os.path.dirname(__file__), "icon.png")
        
class EvolutionBackend(cal.CalendarBackend):
    
    def __init__(self):
        cal.CalendarBackend.__init__(self)
        
    def get_events(self, now):
        calendars = []
        event_days = {}
        
        # Find all the calendar files
        cal_dir = os.path.expanduser("~/.local/share/evolution/calendar")
        if not os.path.exists(cal_dir):
            # Older versions of evolution store their data in ~/.evolution
            cal_dir = os.path.expanduser("~/.evolution/calendar")
        if os.path.exists(cal_dir):
            for root, dirs, files in os.walk(cal_dir):
                for _file in files:
                    if _file.endswith(".ics"):
                        calendars.append(os.path.join(root, _file))
        
        for cal in calendars:
            if not re.search("^webcal://", cal[1]):
                f = open(cal)
                calstring = ''.join(f.readlines())
                f.close()
                try:
                    event_list = vobject.readOne(calstring).vevent_list
                except AttributeError:
                    continue
            else: # evolution library does not support webcal ics
                webcal = urllib.urlopen('http://' + cal[1][9:])
                webcalstring = ''.join(webcal.readlines())
                webcal.close()
                event_list = vobject.readOne(webcalstring).vevent_list
                
            for e in event_list:
                if type(e) != vobject.icalendar.RecurringComponent:
                    parsed_event = vobject.readOne(e.get_as_string())
                else:
                    parsed_event = e
                    
                self.check_and_add(EvolutionEvent(parsed_event), now, event_days)
                
        return event_days