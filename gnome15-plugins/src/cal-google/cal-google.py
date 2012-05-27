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

import gnome15.g15accounts as g15accounts
import gnome15.g15globals as g15globals
import cal
import gtk
import os
import datetime
import gdata.calendar.data
import gdata.calendar.client
import gdata.acl.data
import iso8601
import traceback
import subprocess

# Logging
import logging
logger = logging.getLogger("cal-google")
 
"""
Plugin definition
"""
id="cal-google"
name=_("Calendar (Google support)")
description=_("Adds your Google Calendar as a source for the Gnome15 Calendar plugin")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2012 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=False
passive=True
global_plugin=True
requires="cal"
unsupported_models=cal.unsupported_models

"""
Calendar Back-end module functions
"""
def create_options(account, account_ui):
    return GoogleCalendarOptions(account, account_ui)

def create_backend(account, account_manager):
    return GoogleCalendarBackend(account, account_manager)

# How often refresh from the evolution calendar. This can be a slow process, so not too often
REFRESH_INTERVAL = 15 * 60

class GoogleCalendarOptions(g15accounts.G15AccountOptions):
    def __init__(self, account, account_ui):
        g15accounts.G15AccountOptions.__init__(self, account, account_ui)
                
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "cal-google.glade"))
        self.component = self.widget_tree.get_object("OptionPanel")
        
        username = self.widget_tree.get_object("Username")
        username.connect("changed", self._username_changed)
        username.set_text(self.account.get_property("username", ""))
        
        calendar = self.widget_tree.get_object("Calendar")
        calendar.connect("changed", self._calendar_changed)
        calendar.set_text(self.account.get_property("calendar", ""))
        
    def _username_changed(self, widget):
        self.account.properties["username"] = widget.get_text()
        self.account_ui.save_accounts()
        
    def _calendar_changed(self, widget):
        self.account.properties["calendar"] = widget.get_text()
        self.account_ui.save_accounts()

class GoogleEvent(cal.CalendarEvent):
    
    def __init__(self, when, parsed_event, color, url):
        cal.CalendarEvent.__init__(self)
        self.start_date = iso8601.parse_date(when.start)
        if when.end:
            self.end_date = iso8601.parse_date(when.end)
        else:
            self.end_date = datetime.datetime(self.start_date.year,self.start_date.month,self.start_date.day, 23, 59, 0)
            
        self.link = url
        self.color = color
        self.summary = parsed_event.title.text
        self.alarm = len(when.reminder) > 0
        self.alt_icon = os.path.join(os.path.dirname(__file__), "icon.png")
        
    def _parse_date(self, date_str):
        return calendar.timegm(time.strptime(date_str.split(".")[0]+"UTC", "%Y-%m-%dT%H:%M:%S%Z"))
    
    def activate(self):
        logger.info("xdg-open '%s'" % self.link)
        subprocess.Popen(['xdg-open', self.link])

        
class GoogleCalendarBackend(cal.CalendarBackend):
    
    def __init__(self, account, account_manager):
        cal.CalendarBackend.__init__(self)
        self.account = account
        self.account_manager = account_manager
        
    def get_events(self, now):
        self.cal_client = gdata.calendar.client.CalendarClient(source='%s-%s' % ( g15globals.name, g15globals.version ) )
        
        for i in range(0, 3):
            for j in range(0, 2):
                password = self.account_manager.retrieve_password(self.account, "www.google.com", None, i > 0)
                if password == None or password == "":
                    raise Exception(_("Authentication cancelled"))
                
                try :
                    return self._retrieve_events(now, password)
                except Exception:
                    traceback.print_exc()   
        
        
    def _retrieve_events(self, now, password):
        event_days = {}
        self.cal_client.ClientLogin(self.account.get_property("username", ""), password, self.cal_client.source)
        self.account_manager.store_password(self.account, password, "www.google.com", None) 
        feeds = self.cal_client.GetAllCalendarsFeed()
        for i, a_calendar in zip(xrange(len(feeds.entry)), feeds.entry):
            logger.info('Loading calendar %s' % a_calendar.title.text)
            color = a_calendar.color
            feed = self.cal_client.GetCalendarEventFeed(a_calendar.content.src)
            for i, an_event in zip(xrange(len(feed.entry)), feed.entry):
                logger.info('Adding event %s' % an_event.title.text)
                
                """
                An event may have multiple times. cal doesn't support multiple times, so we add multiple events instead
                """
                for a_when in an_event.when:
                    
                    print '\t\tStart time: %s' % (a_when.start,)
                    print '\t\tEnd time:   %s' % (a_when.end,)
                
                    self.check_and_add(GoogleEvent(a_when, an_event, color, a_calendar.content.src), now, event_days)
                
        return event_days
        

