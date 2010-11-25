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
 
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
import gnome15.g15_driver as g15driver
import subprocess
import time
import os
import feedparser
import gtk
import gconf

from lxml import etree

# Plugin details - All of these must be provided
id="lcdbiff"
name="POP3 / IMAP Email Notification"
description="Periodically checks your email accounts for any waiting messages. Currently supports POP3 and IMAP " + \
        "protocols."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=True

# Constants

POP3 = "pop3"
IMAP = "imap"
TYPES = [ POP3, IMAP ]

def create(gconf_key, gconf_client, screen):
    return G15Biff(gconf_client, gconf_key, screen)

def show_preferences(parent, gconf_client, gconf_key):
    G15BiffPreferences(parent, gconf_client, gconf_key)

def changed(widget, key, gconf_client):
    gconf_client.set_bool(key, widget.get_active())
    
def get_update_time(gconf_client, gconf_key):
    val = gconf_client.get_int(gconf_key + "/update_time")
    if val == 0:
        val = 60
    return val

class G15BiffAccountManager():    
    def __init__(self):
        self._conf_file = os.path.expanduser("~/.gnome2/gnome15/lcdbiff/mailboxes.xml")
        self._load()
            
    def _load(self):
        self.accounts = []
        if not os.path.exists(self._conf_file):
            dir = os.path.dirname(self._conf_file)
            if not os.path.exists(dir):
                os.makedirs(dir)
        else:
            document = etree.parse(self._conf_file)        
            for element in document.getroot().xpath('//mailbox'):
                self.accounts.append(G15BiffAccount(element.text))
            
    def by_name(self, name):
        for acc in self.accounts:
            if acc.name == name:
                return acc
            
    def save(self):        
        root = etree.Element("xml")
        document = etree.ElementTree(root)
        for acc in self.accounts:
            acc_el = etree.SubElement(root, "mailbox")
            acc_el.text = acc.name 
        xml = etree.tostring(document)
        fh = open(self._conf_file, "w")
        try :
            fh.write(xml)
        finally :
            fh.close()

class G15BiffAccount():
    
    def __init__(self, name):
        self.name = name
    
class G15BiffPreferences():
    
    def __init__(self, parent, gconf_client,gconf_key):
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        
        self.account_mgr = G15BiffAccountManager()
        
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "lcdbiff.glade"))
        
        # Widgets
        self.account_type = widget_tree.get_object("TypeCombo")
        self.account_type.connect("changed", self.type_changed)
        
        # Feeds
        self.feed_model = widget_tree.get_object("AccountModel")
        self.reload_model()
        self.feed_list = widget_tree.get_object("AccountList")
        self.url_renderer = widget_tree.get_object("URLRenderer")
        
        # Updates
        self.update_adjustment = widget_tree.get_object("UpdateAdjustment")
        self.update_adjustment.set_value(get_update_time(gconf_client, gconf_key))
        self.update_adjustment.set_value(get_update_time(gconf_client, gconf_key))
        
        # Connect to events
        self.update_adjustment.connect("value-changed", self.update_time_changed)
        self.url_renderer.connect("edited", self.url_edited)
        widget_tree.get_object("NewAccount").connect("clicked", self.new_url)
        widget_tree.get_object("RemoveAccount").connect("clicked", self.remove_url)
        
        # Configure widgets
        self.configure_account_details()
        
        # Show dialog
        dialog = widget_tree.get_object("BiffDialog")
        dialog.set_transient_for(parent)
        
        ah = gconf_client.notify_add(gconf_key + "/urls", self.urls_changed);
        dialog.run()
        dialog.hide()
        gconf_client.notify_remove(ah);
        
    def configure_account_details(self):
        pass
#        type = self.gconf_client.get_string(self.gconf_key + "/")
        
    def update_time_changed(self, widget):
        self.gconf_client.set_int(self.gconf_key + "/update_time", int(widget.get_value()))
        
    def url_edited(self, widget, row_index, value):
        row = self.feed_model[row_index] 
        if value != "":
            acc = self.account_mgr.by_name(row[0])
            if acc == None:
                acc = G15BiffAccount(value)
                self.account_mgr.accounts.append(acc)
            else: 
                acc.name = value
            self.account_mgr.save()
        else:
            self.account_mgr.accounts.remove(self.account_mgr.by_name(row[0]))
        
    def urls_changed(self, client, connection_id, entry, args):
        self.reload_model()
        
    def reload_model(self):
        self.feed_model.clear()
        for account in self.account_mgr.accounts:
            self.feed_model.append([ account.name, True ])
        
    def new_url(self, widget):
        self.feed_model.append(["", True])
        self.feed_list.set_cursor_on_cell(str(len(self.feed_model) - 1), focus_column = self.feed_list.get_column(0), focus_cell = self.url_renderer, start_editing = True)
        self.feed_list.grab_focus()
        
    def remove_url(self, widget):        
        (model, path) = self.feed_list.get_selection().get_selected()
        url = model[path][0]
        self.account_mgr.accounts.remove(self.account_mgr.by_name(url))
        self.account_mgr.save()
        
    def type_changed(self, widget):
        pass   
        
class G15MessagesMenu(g15theme.Menu):
    def __init__(self):
        g15theme.Menu.__init__(self, "menu")
        
    def render_item(self, entry, selected, canvas, properties, attributes, group = False):
        
        element_properties = dict(properties)
        element_properties["ent_selected"] = entry == selected
        element_properties["ent_title"] = entry.title
        element_properties["ent_link"] = entry.link
        element_properties["ent_description"] = entry.description
        
        element_properties["ent_locale_date_time"] = time.strftime("%x %X", entry.date_parsed)            
        element_properties["ent_locale_time"] = time.strftime("%X", entry.date_parsed)            
        element_properties["ent_locale_date"] = time.strftime("%x", entry.date_parsed)
        element_properties["ent_time_24"] = time.strftime("%H:%M", entry.date_parsed) 
        element_properties["ent_full_time_24"] = time.strftime("%H:%M:%S", entry.date_parsed) 
        element_properties["ent_time_12"] = time.strftime("%I:%M %p", entry.date_parsed) 
        element_properties["ent_full_time_12"] = time.strftime("%I:%M:%S %p", entry.date_parsed)
        element_properties["ent_short_date"] = time.strftime("%a %d %b", entry.date_parsed)
        element_properties["ent_full_date"] = time.strftime("%A %d %B", entry.date_parsed)
        element_properties["ent_month_year"] = time.strftime("%m/%y", entry.date_parsed)
                        
        self.entry_theme.draw(canvas, element_properties)
        return self.entry_theme.bounds[3]     
        
class G15AccountPage():
    
    def __init__(self, plugin, url):            
        self.gconf_client = plugin.gconf_client        
        self.gconf_key = plugin.gconf_key
        self.screen = plugin.screen
        self.icon_surface = None
        self.icon_embedded = None
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
        self.url = url
        self.index = -1
        self.selected_entry = None
        self.reload() 
        self.page = self.screen.new_page(self.paint, id="Mail " + str(plugin.page_serial), thumbnail_painter = self.paint_thumbnail)
        plugin.page_serial += 1
        self.page.set_title(self.title)
        self.menu = G15MessagesMenu()
        self.theme.add_component(self.menu)
        self.theme.add_component(g15theme.Scrollbar("viewScrollbar", self.menu.get_scroll_values))
        self.screen.redraw(self.page)
        
    def reload(self):
        self.feed = feedparser.parse(self.url)
        if "icon" in self.feed["feed"]:
            icon = self.feed["feed"]["icon"]
        elif "image" in self.feed["feed"]:
            icon = self.feed["feed"]["image"]["url"]
        else:
            icon = g15util.get_icon_path("application-rss+xml", self.screen.height )
            
        if icon == None:
            self.icon_surface = None
            self.icon_embedded = None
        else:
            icon_surface = g15util.load_surface_from_file(icon)
            self.icon_surface = icon_surface
            self.icon_embedded = g15util.get_embedded_image_url(icon_surface)
        self.title = self.feed["feed"]["title"] if "title" in self.feed["feed"] else self.url
        self.subtitle = self.feed["feed"]["subtitle"] if "subtitle" in self.feed["feed"] else ""
        self.set_properties()
        
    def set_properties(self):
        self.properties = {}
        self.attributes = {}
        self.properties["title"] = self.title
        self.attributes["icon"] = self.icon_surface
        self.properties["icon"] = self.icon_embedded
        self.properties["subtitle"] = self.subtitle
        self.properties["updated"] = "%s %s" % ( time.strftime("%H:%M", self.feed.updated), time.strftime("%a %d %b", self.feed.updated) )
        self.attributes["entries"] = self.feed.entries
        if self.index > -1:
            self.attributes["selected"] = self.selected_entry
            self.attributes["selected_idx"] = self.index
        
    def selection_changed(self):        
        if self.index > -1 and self.index < len(self.feed.entries):
            self.selected_entry = self.feed.entries[self.index]
        else:
            self.index = -1
            self.selected_entry = None
        self.set_properties()
        self.screen.applet.resched_cycle()
        self.screen.redraw(self.page)
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP and self.screen.get_visible_page() == self.page:
            if g15driver.G_KEY_UP in keys or g15driver.G_KEY_L3 in keys:
                if self.index < 0:
                    self.index = len(self.feed.entries) - 1
                else:
                    self.index -= 1
                self.selection_changed()
                return True
            elif g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L4 in keys:
                if self.index >= len(self.feed.entries):
                    self.index = 0
                else:
                    self.index += 1
                self.selection_changed()
                return True
            elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                if self.selected_entry != None:
                    subprocess.Popen(['xdg-open', self.selected_entry.link])
                    
                # Open in browser
                return True
                
        return False
    
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        if "icon" in self.attributes:
            return g15util.paint_thumbnail_image(allocated_size, self.attributes["icon"], canvas)
        
    def paint(self, canvas):
        self.menu.items = self.feed.entries
        self.menu.selected = self.selected_entry
        self.theme.draw(canvas, self.properties, self.attributes)
    
class G15Biff():
    
    def __init__(self, gconf_client,gconf_key, screen):
        self.screen = screen;
        self.gconf_key = gconf_key
        self.gconf_client = gconf_client
        self.page_serial = 1

    def activate(self):
        self.pages = {}       
        self.schedule_refresh() 
        self.update_time_changed_handle = self.gconf_client.notify_add(self.gconf_key + "/update_time", self.update_time_changed)
        self.urls_changed_handle = self.gconf_client.notify_add(self.gconf_key + "/urls", self.urls_changed)
        self.load_feeds()
        
    def handle_key(self, keys, state, post):
        for page in self.pages:
            if self.pages[page].handle_key(keys, state, post):
                return True
        return False
        
    def schedule_refresh(self):        
        self.refresh_timer = g15util.schedule("MailRefreshTimer", get_update_time(self.gconf_client, self.gconf_key) * 60.0, self.refresh)
        
    def refresh(self):
        for page in self.pages:
            self.pages[page].reload()
#            page.set_title(self.feed["feed"]["title"])
            self.screen.redraw(page)
        self.schedule_refresh()
    
    def deactivate(self):
        self.gconf_client.notify_remove(self.update_time_changed_handle);
        self.gconf_client.notify_remove(self.urls_changed_handle);
        for page in self.pages:
            self.screen.del_page(self.pages[page].page)
        self.pages = {}
        
    def destroy(self):
        pass 
    
    def update_time_changed(self, client, connection_id, entry, args):
        self.refresh_timer.cancel()
        self.schedule_refresh()
    
    def urls_changed(self, client, connection_id, entry, args):
        self.load_feeds()
    
    def load_feeds(self):
        feed_list = self.gconf_client.get_list(self.gconf_key + "/urls", gconf.VALUE_STRING)
        
        # Add new pages
        for url in feed_list:
            if not url in self.pages:
                self.pages[url] = G15AccountPage(self, url)
                
        # Remove pages that no longer exist
        to_remove = []
        for page_url in self.pages:
            page = self.pages[page_url]
            if not page.url in feed_list:
                self.screen.del_page(page.page)
                to_remove.append(page_url)
        for page in to_remove:
            del self.pages[page]
            
