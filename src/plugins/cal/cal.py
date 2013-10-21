#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2010 Brett Smith <tanktarta@blueyonder.co.uk>
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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("cal", modfile = __file__).ugettext

import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.util.g15convert as g15convert
import gnome15.util.g15scheduler as g15scheduler
import gnome15.util.g15uigconf as g15uigconf
import gnome15.util.g15gconf as g15gconf
import gnome15.util.g15cairo as g15cairo
import gnome15.util.g15icontools as g15icontools
import gnome15.g15screen as g15screen
import gnome15.g15accounts as g15accounts
import gnome15.g15plugin as g15plugin
import gnome15.g15globals as g15globals
import datetime
import time
import os, os.path
import gtk
import calendar
import traceback

# Logging
import logging
logger = logging.getLogger("cal")

# Plugin data
id="cal"
name=_("Calendar")
description=_("Provides basic support for calendars. To make this\n\
plugin work, you will also need a second plugin for your calendar\n\
provider. Currently, Gnome15 supports Evolution and Google calendars.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=True
actions={ 
     g15driver.PREVIOUS_SELECTION : _("Previous day/Event"), 
     g15driver.NEXT_SELECTION : _("Next day/Event"), 
     g15driver.VIEW : _("Return to today"),
     g15driver.CLEAR : _("Toggle calendar/events"),
     g15driver.NEXT_PAGE : _("Next week"),
     g15driver.PREVIOUS_PAGE : _("Previous week")
}
actions_g19={ 
     g15driver.PREVIOUS_PAGE : _("Previous day/Event"), 
     g15driver.NEXT_PAGE : _("Next day/Event"), 
     g15driver.VIEW : _("Return to today"),
     g15driver.CLEAR : _("Toggle calendar/events"),
     g15driver.NEXT_SELECTION : _("Next week"),
     g15driver.PREVIOUS_SELECTION : _("Previous week")
}
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, \
                      g15driver.MODEL_MX5500, g15driver.MODEL_G930, \
                      g15driver.MODEL_G35 ]

# How often refresh from the evolution calendar. This can be a slow process, so not too often
REFRESH_INTERVAL = 15 * 60

# Configuration
CONFIG_PATH = os.path.join(g15globals.user_config_dir, "plugin-data", "cal", "calendars.xml")
CONFIG_ITEM_NAME = "calendar"

"""
Functions
"""

def create(gconf_key, gconf_client, screen):
    return G15Cal(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    G15CalendarPreferences(parent, gconf_client, gconf_key)

def get_backend(account_type):
    """
    Get the backend plugin module, given the account_type
    
    Keyword arguments:
    account_type          -- account type
    """
    import gnome15.g15pluginmanager as g15pluginmanager
    return g15pluginmanager.get_module_for_id("cal-%s" % account_type)

def get_available_backends():
    """
    Get the "account type" names that are available by listing all of the
    backend plugins that are installed 
    """
    l = []
    import gnome15.g15pluginmanager as g15pluginmanager
    for p in g15pluginmanager.imported_plugins:
        if p.id.startswith("cal-"):
            l.append(p.id[4:])
    return l
    
class CalendarEvent():
    
    def __init__(self):
        self.start_date = None
        self.end_date = None
        self.summary = None
        self.color = None
        self.alarm = False
        self.alt_icon = None
    
    def activate(self):
        raise Exception("Not implemented")

class CalendarBackend():
    
    def __init__(self):
        self.start_date = None
        self.end_date = None
        
    def check_and_add(self, ve, now, event_days):
        if ve.start_date.month == now.month and ve.start_date.year == now.year:
            day = ve.start_date.day
            while day <= ve.end_date.day:
                key = str(day)
                day_event_list = event_days[key] if key is event_days else None
                if day_event_list is None:
                    day_event_list = list()
                    event_days[key] = day_event_list
                day_event_list.append(ve)
                day += 1
    
    def get_events(self, now):
        raise Exception("Not implemented")
    
class EventMenuItem(g15theme.MenuItem):
    
    def __init__(self, plugin, event, component_id):
        g15theme.MenuItem.__init__(self, component_id)
        self.event = event
        self.plugin = plugin
    
    def get_default_theme_dir(self):
        return os.path.join(os.path.dirname(__file__), "default")
    
    def get_theme_properties(self):        
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self.event.summary
        
        start_str = self.event.start_date.strftime("%H:%M")
        end_str = self.event.end_date.strftime("%H:%M")
        
        if not self._same_day(self.event.start_date, self.event.end_date):
            if not self._same_day(self.plugin._calendar_date, self.event.end_date):
                end_str = _(self.event.end_date.strftime("%m/%d"))
            if not self._same_day(self.plugin._calendar_date, self.event.start_date):
                start_str = _(self.event.start_date.strftime("%m/%d"))
        
        
        if self._same_day(self.event.start_date, self.event.end_date) and \
           self.event.start_date.hour == 0 and self.event.start_date.minute == 0 and \
           self.event.end_date.hour == 23 and self.event.end_date.minute == 59:
            item_properties["item_alt"] = _("All Day")
        else:
            item_properties["item_alt"] = "%s-%s" % ( start_str, end_str)
            
        item_properties["item_alarm"] = self.event.alarm  
        if self.event.alarm:          
            if self.get_screen().device.bpp > 1:  
                item_properties["item_icon"] = g15icontools.get_icon_path([ "stock_alarm", "alarm-clock", "alarm-timer", "dialog-warning" ])
            else:  
                item_properties["item_icon"] = os.path.join(os.path.dirname(__file__), 'bell.gif')
        if self.event.alt_icon:
            item_properties["alt_icon"] = self.event.alt_icon
        return item_properties
    
    def activate(self):
        self.event.activate()
    
    def _same_day(self, date1, date2):
        return date1.day == date2.day and date1.month == date2.month and date1.year == date2.year
    
class Cell(g15theme.Component):
    def __init__(self, day, now, event, component_id):
        g15theme.Component.__init__(self, component_id)
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
        properties["event"] = self.event.summary if self.event else ""    
        if self.now.day == self.day.day and self.now.month == self.day.month:
            properties["today"] = True
        return properties
        
    def get_item_attributes(self, selected):
        return {}
    
class Calendar(g15theme.Component):
    
    def __init__(self, component_id="calendar"):
        g15theme.Component.__init__(self, component_id)
        self.layout_manager = g15theme.GridLayoutManager(7)
        self.focusable = True
        
 
class G15CalendarPreferences(g15accounts.G15AccountPreferences):
    '''
    Configuration UI
    '''    
    
    def __init__(self, parent, gconf_client, gconf_key):
        g15accounts.G15AccountPreferences.__init__(self, parent, gconf_client, \
                                                   gconf_key, \
                                                   CONFIG_PATH, \
                                                   CONFIG_ITEM_NAME)
        
    def get_account_types(self):
        return get_available_backends()
    
    def get_account_type_name(self, account_type):
        return _(account_type)
        
    def create_options_for_type(self, account, account_type):
        backend = get_backend(account.type)
        if backend is None:
            logger.warning("No backend for account type %s" % account_type)
            return None
        return backend.create_options(account, self)
    
    def create_general_options(self):
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "cal.ui"))
        g15uigconf.configure_checkbox_from_gconf(self.gconf_client, "%s/twenty_four_hour_times" % self.gconf_key, "TwentyFourHourTimes", True, widget_tree)
        return widget_tree.get_object("OptionPanel")
        
class G15Cal(g15plugin.G15Plugin):  
    
    def __init__(self, gconf_key, gconf_client, screen):
        g15plugin.G15Plugin.__init__(self, gconf_client, gconf_key, screen)
        self._timer = None
        self._icon_path = g15icontools.get_icon_path(["calendar", "evolution-calendar", "office-calendar", "stock_calendar" ])
        self._thumb_icon = g15cairo.load_surface_from_file(self._icon_path)
        
    def activate(self):
        g15plugin.G15Plugin.activate(self)
        
        self._active = True
        self._event_days = None
        self._calendar_date = None
        self._page = None
        self._theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), auto_dirty = False)
        self._loaded = 0
        
        # Backend
        self._account_manager = g15accounts.G15AccountManager(CONFIG_PATH, CONFIG_ITEM_NAME)
        
        # Calendar
        self._calendar = Calendar()
        
        # Menu
        self._menu = g15theme.Menu("menu")
        self._menu.focusable = True
        self._menu.focused_component = True
        
        # Page
        self._page = g15theme.G15Page(name, self.screen, on_shown = self._on_shown, \
                                     on_hidden = self._on_hidden, theme_properties_callback = self._get_properties,
                                     thumbnail_painter = self._paint_thumbnail, 
                                     originating_plugin = self)
        self._page.set_title(_("Calendar"))
        self._page.set_theme(self._theme)
        self._page.focused_component = self._calendar
        self._calendar.set_focused(True)
        
        # List for account changes        
        self._account_manager.add_change_listener(self._accounts_changed)
        self.screen.key_handler.action_listeners.append(self)
        
        # Run first load in thread
        self._page.add_child(self._menu)
        self._page.add_child(self._calendar)
        self._page.add_child(g15theme.MenuScrollbar("viewScrollbar", self._menu))
        self.screen.add_page(self._page)
        g15scheduler.schedule("CalendarFirstLoad", 0, self._redraw)
        
        # Listen for changes in the network state
        self.screen.service.network_manager.listeners.append(self._network_state_changed)
        
        # Config changes
        self.watch("twenty_four_hour_times", self._config_changed)
        
    def deactivate(self):
        g15plugin.G15Plugin.deactivate(self)
        self.screen.service.network_manager.listeners.append(self._network_state_changed)
        self._account_manager.remove_change_listener(self._accounts_changed)
        self.screen.key_handler.action_listeners.remove(self)
        if self._timer != None:
            self._timer.cancel()
        if self._page != None:
            g15screen.run_on_redraw(self.screen.del_page, self._page)
        
    def destroy(self):
        pass
                    
    def action_performed(self, binding):
        if self._page and self._page.is_visible():
            if self._calendar.is_focused():
                if ( binding.action == g15driver.PREVIOUS_PAGE and self.screen.device.model_id == g15driver.MODEL_G19 ) or \
                   ( binding.action == g15driver.PREVIOUS_SELECTION and self.screen.device.model_id != g15driver.MODEL_G19 ):
                    self._adjust_calendar_date(-1)
                    return True
                elif ( binding.action == g15driver.NEXT_PAGE and self.screen.device.model_id == g15driver.MODEL_G19 ) or \
                     ( binding.action == g15driver.NEXT_SELECTION and self.screen.device.model_id != g15driver.MODEL_G19 ):
                    self._adjust_calendar_date(1)
                    return True
                elif ( binding.action == g15driver.PREVIOUS_SELECTION and self.screen.device.model_id == g15driver.MODEL_G19 ) or \
                     ( binding.action == g15driver.PREVIOUS_PAGE and self.screen.device.model_id != g15driver.MODEL_G19 ):
                    self._adjust_calendar_date(-7)
                    return True
                elif ( binding.action == g15driver.NEXT_SELECTION and self.screen.device.model_id == g15driver.MODEL_G19 ) or \
                     ( binding.action == g15driver.NEXT_PAGE and self.screen.device.model_id != g15driver.MODEL_G19 ):
                    self._adjust_calendar_date(7)
                    return True
                elif binding.action == g15driver.VIEW:
                    self._calendar_date = None
                    self._adjust_calendar_date(0)
                    return True
            if binding.action == g15driver.CLEAR:
                self._page.next_focus()
                return True
    
    """
    Private
    """
    
    def _config_changed(self, client, connection_id, entry, args):
        self._loaded = 0
        self._redraw()
        
    def _network_state_changed(self, state):
        self._loaded = 0
        self._redraw()
    
    def _accounts_changed(self, account_manager):
        self._loaded = 0
        self._redraw()
                    
    def _adjust_calendar_date(self, amount):
        o_date = self._get_calendar_date()
        self._calendar_date = o_date + datetime.timedelta(amount)
        if amount == 0 or o_date.month != self._calendar_date.month or o_date.year != self._calendar_date.year:
            self._load_month_events(self._calendar_date)
        else:            
            g15screen.run_on_redraw(self._rebuild_components, self._calendar_date)
        
    def _get_calendar_date(self):
        now = datetime.datetime.now()
        return self._calendar_date if self._calendar_date is not None else now
        
    def _get_properties(self):
        now = datetime.datetime.now()
        calendar_date = self._get_calendar_date()
        properties = {}
        properties["icon"] = self._icon_path 
        properties["title"] = _('Calendar')
        if g15gconf.get_bool_or_default(self.gconf_client, "%s/twenty_four_hour_times" % self.gconf_key, True):
            properties["time"] = g15locale.format_time_24hour(now, self.gconf_client, False)
            properties["full_time"] = g15locale.format_time_24hour(now, self.gconf_client, True)
        else:
            properties["full_time"] = g15locale.format_time(now, self.gconf_client, True)
            properties["time"] = g15locale.format_time(now, self.gconf_client, False)
        properties["time_24"] = now.strftime("%H:%M") 
        properties["full_time_24"] = now.strftime("%H:%M:%S") 
        properties["time_12"] = now.strftime("%I:%M %p") 
        properties["full_time_12"] = now.strftime("%I:%M:%S %p")
        properties["short_date"] = now.strftime("%a %d %b")
        properties["full_date"] = now.strftime("%A %d %B")
        properties["date"] = g15locale.format_date(now, self.gconf_client)
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
            properties["events"] = False
        else:
            properties["events"] = True
            properties["message"] = ""
        return properties
    
    def _load_month_events(self, now):
        self._event_days = {}
        
        for c in self._page.get_children():
            if isinstance(c, Cell):
                pass
            
        # Get all the events for this month
        for acc in self._account_manager.accounts:
            try:
                backend = get_backend(acc.type)
                if backend is None:
                    logger.warn("Could not find a calendar backend for %s" % acc.name)
                else:
                    # Backends may specify if they need a network or not, so check the state
                    import gnome15.g15pluginmanager as g15pluginmanager
                    needs_net = g15pluginmanager.is_needs_network(backend)
                    if not needs_net or ( needs_net and self.screen.service.network_manager.is_network_available() ):
                        backend_events = backend.create_backend(acc, self._account_manager).get_events(now)
                        if backend_events is None:
                            logger.warning("Calendar returned no events, skipping")
                        else:
                            self._event_days = dict(self._event_days.items() + \
                                                    backend_events.items())
                    else:
                        logger.warn("Skipping backend %s because it requires the network, and the network is not availabe" % acc.type)
            except Exception as e:
                if logger.level == logger.debug:
                    logger.warn("Failed to load events for account %s.")
                    traceback.print_exc()   
                else:
                    logger.warn("Failed to load events for account %s. %s" % (acc.name, e))
                    
        g15screen.run_on_redraw(self._rebuild_components, now)
        self._page.mark_dirty()
        
    def _rebuild_components(self, now):
        self._menu.remove_all_children()
        if str(now.day) in self._event_days:
            events = self._event_days[str(now.day)]
            i = 0
            for event in events:
                self._menu.add_child(EventMenuItem(self, event, "menuItem-%d" % i))
                i += 1
            
        # Add the date cell components
        self._calendar.remove_all_children()
        cal = calendar.Calendar()
        i = 0
        for day in cal.itermonthdates(now.year, now.month):
            event = None
            if str(day.day) in self._event_days:
                event = self._event_days[str(day.day)][0]            
            self._calendar.add_child(Cell(day, now, event, "cell-%d" % i))
            i += 1
            
        self._page.mark_dirty()
        self._page.redraw()
        
    def _schedule_redraw(self):
        if self.screen.is_visible(self._page):
            if self._timer is not None:
                self._timer.cancel()
            
            """
            Because the calendar page also displays a clock, we want to
            redraw at second zero of every minute
            """
            self._timer = g15scheduler.schedule("CalRedraw", 60 - time.gmtime().tm_sec, self._redraw)
        
    def _on_shown(self):
        self._hidden = False
        self._redraw()
        
    def _on_hidden(self):
        if self._timer != None:
            self._timer.cancel()
        
    def _redraw(self):
        t = time.time()
        if t > self._loaded + REFRESH_INTERVAL:
            self._loaded = t    
            self._reload_events_now()
        else:
            self._page.mark_dirty()
            self.screen.redraw(self._page)
            self._schedule_redraw()
            
    def _reload_events_now(self):
        self._load_month_events(self._get_calendar_date())
        self.screen.redraw(self._page)
        self._schedule_redraw()
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self._page != None and self._thumb_icon != None and self.screen.driver.get_bpp() == 16:
            return g15cairo.paint_thumbnail_image(allocated_size, self._thumb_icon, canvas)
        

