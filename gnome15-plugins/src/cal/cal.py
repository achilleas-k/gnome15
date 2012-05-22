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
_ = g15locale.get_translation("cal", modfile = __file__).ugettext

import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gnome15.g15screen as g15screen
import datetime
import time
import os
import gobject
import calendar
 
id="cal"
name=_("Calendar")
description=_("Provides basic support for calendars. To make this\n\
plugin work, you will also need a second plugin for your calendar\n\
provider. Currently, Gnome15 supports Evolution and Google calendars.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=False
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous day/Event"), 
         g15driver.NEXT_SELECTION : _("Next day/Event"), 
         g15driver.VIEW : _("Toggle between calendar\nand events"),
         g15driver.NEXT_PAGE : _("Next week"),
         g15driver.PREVIOUS_PAGE : _("Previous week")
         }
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_MX5500, g15driver.MODEL_G930 ]

# How often refresh from the evolution calendar. This can be a slow process, so not too often
REFRESH_INTERVAL = 15 * 60

def create(gconf_key, gconf_client, screen):
    return G15Cal(gconf_key, gconf_client, screen)

class CalendarEvent():
    
    def __init__(self):
        self.start_date = None
        self.end_date = None
        self.summary = None

class CalendarBackend():
    
    def __init__(self):
        self.start_date = None
        self.end_date = None
    
    def get_events(self, now):
        raise Exception("Not implemented")
    
class EventMenuItem(g15theme.MenuItem):
    
    def __init__(self,  event, component_id):
        g15theme.MenuItem.__init__(self, component_id)
        self.event = event
    
    def get_default_theme_dir(self):
        return os.path.join(os.path.dirname(__file__), "default")
        
    def get_theme_properties(self):        
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self.event.summary
        item_properties["item_alt"] = "%s-%s" % ( self.event.start_date.strftime("%H:%M"), self.event.end_date.strftime("%H:%M")) 
        try :
            self.event.valarm            
            item_properties["item_icon"] = g15util.get_icon_path([ "stock_alarm", "alarm-clock", "alarm-timer", "dialog-warning" ])
        except AttributeError:
            pass
        return item_properties
    
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
        
class G15Cal():  
    
    def __init__(self, gconf_key, gconf_client, screen):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._timer = None
        self._thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path(["calendar", "evolution-calendar", "office-calendar", "stock_calendar" ]))
        
    def create_backend(self):
        raise Exception("Not implemented")
    
    def activate(self):
        self._active = True
        self._event_days = None
        self._calendar_date = None
        self._page = None
        self._theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), auto_dirty = False)
        self._loaded = 0
        
        # Backend
        self._backend = self.create_backend()
        
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
        self._screen.key_handler.action_listeners.append(self)
        self._calendar.set_focused(True)
        
        def on_redraw():
            self._page.add_child(self._menu)
            self._page.add_child(self._calendar)
            self._page.add_child(g15theme.Scrollbar("viewScrollbar", self._menu.get_scroll_values))
            self._screen.add_page(self._page)
            self._page.redraw()
            
        g15screen.run_on_redraw(on_redraw)
        
        # Must be on GTK thread for python
        gobject.idle_add(self._first_load)
        
    def deactivate(self):
        self._screen.key_handler.action_listeners.remove(self)
        if self._timer != None:
            self._timer.cancel()
        if self._page != None:
            g15screen.run_on_redraw(self._screen.del_page, self._page)
        
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
                    gobject.idle_add(self._load_month_events, self._calendar_date) 
            if binding.action == g15driver.VIEW:
                self._page.next_focus()
    
    """
    Private
    """
                    
    def _adjust_calendar_date(self, amount):
        if self._calendar_date == None:
            self._calendar_date = datetime.datetime.now()
        self._calendar_date = self._calendar_date + datetime.timedelta(amount)
        gobject.idle_add(self._load_month_events, self._calendar_date) 
        
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
        self._event_days = self._backend.get_events(now)
                    
        # Set the events
        def on_redraw():
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
                
            self._page.redraw()
            
        g15screen.run_on_redraw(on_redraw)
            
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
        gobject.idle_add(self._redraw_now)
            
    def _redraw_now(self):
        self._load_month_events(datetime.datetime.now())
        self._screen.redraw(self._page)
        self._schedule_redraw()
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self._page != None and self._thumb_icon != None and self._screen.driver.get_bpp() == 16:
            return g15util.paint_thumbnail_image(allocated_size, self._thumb_icon, canvas)
        

class G15CalAccountManager():  
    
    '''
    Manages the storage and loading of the account list. This is
    stored as an XML file in the Gnome configuration directory
    '''  
    
    def __init__(self):
        self._conf_file = os.path.expanduser("~/.config/gnome15/plugin-data/calendards.xml")
        self.load()
        self.checkers = { POP3 : POP3Checker(), IMAP: IMAPChecker() }
            
    def load(self):
        self.accounts = []
        if not os.path.exists(self._conf_file):
            dir = os.path.dirname(self._conf_file)
            if not os.path.exists(dir):
                os.makedirs(dir)
        else:
            document = etree.parse(self._conf_file)        
            for element in document.getroot().xpath('//mailbox'):
                acc = G15BiffAccount(element.get("name"), element.get("type"))
                for property_element in element:
                    acc.properties[property_element.get("name")] = property_element.get("value") 
                self.accounts.append(acc)
            
    def by_name(self, name):
        for acc in self.accounts:
            if acc.name == name:
                return acc
            
    def check_account(self, account):
        return self.checkers[account.type].check(account)
            
    def save(self):        
        root = etree.Element("xml")
        document = etree.ElementTree(root)
        for acc in self.accounts:
            acc_el = etree.SubElement(root, "mailbox", type=acc.type, name=acc.name)
            for key in acc.properties:
                attr_el = etree.SubElement(acc_el, "property", name=key, value=acc.properties[key])
        xml = etree.tostring(document)
        fh = open(self._conf_file, "w")
        try :
            fh.write(xml)
        finally :
            fh.close()

class G15BiffAccount():
    '''
    A single account. An account has two main attributes,
    a name and a type. All protocol specific details are
    stored in the properties map.
    '''
    
    def __init__(self, name, type=POP3):
        self.name = name
        self.type = type
        self.properties = {}
        
    def get_property(self, key, default_value=None): 
        return self.properties[key] if key in self.properties else default_value
        
class G15CalPreferences():
    '''
    Configuration UI
    '''
     
    
    def __init__(self, parent, driver, gconf_client, gconf_key):
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.visible_options = None
        
        self.account_mgr = G15BiffAccountManager()
        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "cal.glade"))
        
        # Models        
        self.type_model = self.widget_tree.get_object("TypeModel")
        self.feed_model = self.widget_tree.get_object("AccountModel")
        
        # Widgets
        self.account_type = self.widget_tree.get_object("TypeCombo")
        self.feed_list = self.widget_tree.get_object("AccountList")
        self.url_renderer = self.widget_tree.get_object("URLRenderer")
        
        # Updates
        self.update_adjustment = self.widget_tree.get_object("UpdateAdjustment")
        self.update_adjustment.set_value(get_update_time(gconf_client, gconf_key))
        self.update_adjustment.set_value(get_update_time(gconf_client, gconf_key))
        
        # Connect to events
        self.feed_list.connect("cursor-changed", self._select_account)
        self.account_type.connect("changed", self._type_changed)
        self.update_adjustment.connect("value-changed", self._update_time_changed)
        self.url_renderer.connect("edited", self._url_edited)
        self.widget_tree.get_object("NewAccount").connect("clicked", self._new_url)
        self.widget_tree.get_object("RemoveAccount").connect("clicked", self._remove_url)
        
        # Configure widgets 
        self._reload_model()
        self._select_account()
        
        # Show dialog
        dialog = self.widget_tree.get_object("CalDialog")
        dialog.set_transient_for(parent)
        
        ah = gconf_client.notify_add(gconf_key + "/urls", self._urls_changed);
        dialog.run()
        dialog.hide()
        gconf_client.notify_remove(ah);
        
    def _update_time_changed(self, widget):
        self.gconf_client.set_int(self.gconf_key + "/update_time", int(widget.get_value()))
        
    def _url_edited(self, widget, row_index, value):
        row = self.feed_model[row_index] 
        if value != "":
            acc = self.account_mgr.by_name(row[0])
            if acc == None:
                acc = G15BiffAccount(value)
                self.account_mgr.accounts.append(acc)
            else: 
                acc.name = value
            self.account_mgr.save()
            self.feed_list.get_selection().select_path(row_index)
        else:
            self.account_mgr.accounts.remove(self.account_mgr.by_name(row[0]))
        self._reload_model()
        
    def _urls_changed(self, client, connection_id, entry, args):
        self._reload_model()
        
    def _reload_model(self):
        acc = self._get_selected_account()
        self.feed_model.clear()
        for i in range(0, len(self.account_mgr.accounts)):
            account = self.account_mgr.accounts[i]
            row = [ account.name, True ]
            self.feed_model.append(row)
            if account == acc:
                self.feed_list.get_selection().select_path(i)
                
        (model, sel) = self.feed_list.get_selection().get_selected()
        if sel == None:
            self.feed_list.get_selection().select_path(0)
        
    def _new_url(self, widget):
        self.feed_model.append(["", True])
        self.feed_list.set_cursor_on_cell(str(len(self.feed_model) - 1), focus_column=self.feed_list.get_column(0), focus_cell=self.url_renderer, start_editing=True)
        self.feed_list.grab_focus()
        
    def _remove_url(self, widget):        
        (model, path) = self.feed_list.get_selection().get_selected()
        url = model[path][0]
        self.account_mgr.accounts.remove(self.account_mgr.by_name(url))
        self.account_mgr.save()
        self._reload_model()
        
    def _type_changed(self, widget):      
        sel = self._get_selected_type()      
        acc = self._get_selected_account()
        if acc.type != sel:
            acc.type = sel 
            self.account_mgr.save()
            self._load_options_for_type()
        
    def _load_options_for_type(self):
        acc = self._get_selected_account()
        type = self._get_selected_type()
        if type == POP3:
            options = G15BiffPOP3Options(acc, self.account_mgr)
        else:
            options = G15BiffIMAPOptions(acc, self.account_mgr)
            
        if self.visible_options != None:
            self.visible_options.component.destroy()
        self.visible_options = options            
        self.visible_options.component.reparent(self.widget_tree.get_object("PlaceHolder"))
     
    def _select_account(self, widget=None):       
        account = self._get_selected_account()
        if account != None:  
            self.account_type.set_sensitive(True)
            self.widget_tree.get_object("PlaceHolder").set_visible(True)
            for i in range(0, len(self.type_model)):
                if self.type_model[i][0] == account.type:
                    self.account_type.set_active(i)       
            if self.account_type.get_active() == -1:                
                self.account_type.set_active(0)
            self._load_options_for_type()
        else:
            self.account_type.set_sensitive(False)
            self.widget_tree.get_object("PlaceHolder").set_visible(False)
            
    def _get_selected_type(self):
        active = self.account_type.get_active()
        return None if active == -1 else self.type_model[active][0]
            
    def _get_selected_account(self):
        (model, path) = self.feed_list.get_selection().get_selected()
        if path != None:
            return self.account_mgr.by_name(model[path][0])