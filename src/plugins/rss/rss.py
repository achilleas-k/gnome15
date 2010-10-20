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

# Plugin details - All of these must be provided
id="rss"
name="RSS"
description="A simple RSS reader. Multiple feeds may be added, with a screen being " \
        + "allocated to each one once it has loaded. You may move up and down " \
        + "through the entries using the Up and Down keys on the G19, or L2 and L3 on " \
        + "the G15. The entry may then be viewed in the browser using OK (G19), or L4 (G15)."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=True

def create(gconf_key, gconf_client, screen):
    return G15RSS(gconf_client, gconf_key, screen)

def show_preferences(parent, gconf_client, gconf_key):
    G15RSSPreferences(parent, gconf_client, gconf_key)

def changed(widget, key, gconf_client):
    gconf_client.set_bool(key, widget.get_active())
    
def get_update_time(gconf_client, gconf_key):
    val = gconf_client.get_int(gconf_key + "/update_time")
    if val == 0:
        val = 60
    return val
    
class G15RSSPreferences():
    
    def __init__(self, parent, gconf_client,gconf_key):
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "rss.glade"))
        
        # Feeds
        self.feed_model = widget_tree.get_object("FeedModel")
        self.reload_model()
        self.feed_list = widget_tree.get_object("FeedList")
        self.url_renderer = widget_tree.get_object("URLRenderer")
        
        # Updates
        self.update_adjustment = widget_tree.get_object("UpdateAdjustment")
        self.update_adjustment.set_value(get_update_time(gconf_client, gconf_key))
        self.update_adjustment.set_value(get_update_time(gconf_client, gconf_key))
        
        # Connect to events
        self.update_adjustment.connect("value-changed", self.update_time_changed)
        self.url_renderer.connect("edited", self.url_edited)
        widget_tree.get_object("NewURL").connect("clicked", self.new_url)
        widget_tree.get_object("RemoveURL").connect("clicked", self.remove_url)
        
        # Show dialog
        dialog = widget_tree.get_object("RSSDialog")
        dialog.set_transient_for(parent)
        
        ah = gconf_client.notify_add(gconf_key + "/urls", self.urls_changed);
        dialog.run()
        dialog.hide()
        gconf_client.notify_remove(ah);
        
    def update_time_changed(self, widget):
        self.gconf_client.set_int(self.gconf_key + "/update_time", int(widget.get_value()))
        
    def url_edited(self, widget, row_index, value):
        row = self.feed_model[row_index] 
        if value != "":
            urls = self.gconf_client.get_list(self.gconf_key + "/urls", gconf.VALUE_STRING)
            if row[0] in urls:
                urls.remove(row[0])
            urls.append(value)
            self.gconf_client.set_list(self.gconf_key + "/urls", gconf.VALUE_STRING, urls)
        else:
            self.feed_model.remove(self.feed_model.get_iter(row_index))
        
    def urls_changed(self, client, connection_id, entry, args):
        self.reload_model()
        
    def reload_model(self):
        self.feed_model.clear()
        for url in self.gconf_client.get_list(self.gconf_key + "/urls", gconf.VALUE_STRING):
            self.feed_model.append([ url, True ])
        
    def new_url(self, widget):
        self.feed_model.append(["", True])
        self.feed_list.set_cursor_on_cell(str(len(self.feed_model) - 1), focus_column = self.feed_list.get_column(0), focus_cell = self.url_renderer, start_editing = True)
        self.feed_list.grab_focus()
        
    def remove_url(self, widget):        
        (model, path) = self.feed_list.get_selection().get_selected()
        url = model[path][0]
        urls = self.gconf_client.get_list(self.gconf_key + "/urls", gconf.VALUE_STRING)
        if url in urls:
            urls.remove(url)
            self.gconf_client.set_list(self.gconf_key + "/urls", gconf.VALUE_STRING, urls)        
        
class G15FeedPage():
    
    def __init__(self, plugin, url):            
        self.gconf_client = plugin.gconf_client        
        self.gconf_key = plugin.gconf_key
        self.screen = plugin.screen
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
        self.url = url
        self.index = -1
        self.selected_entry = None
        self.page = self.screen.new_page(self.paint, id="Feed " + url, thumbnail_painter = self.paint_thumbnail)
        self.reload()
        
    def reload(self):
        self.feed = feedparser.parse(self.url)
        
        self.properties = {}
        self.attributes = {}
        
        self.properties["title"] = self.feed["feed"]["title"]
        self.page.set_title(self.feed["feed"]["title"])
        
        if "icon" in self.feed["feed"]:
            icon = self.feed["feed"]["icon"]
        elif "image" in self.feed["feed"]:
            icon = self.feed["feed"]["image"]["url"]
        else:
            icon = g15util.get_icon_path(self.gconf_client, "application-rss+xml", (self.screen.height, self.screen.height) )
            
        # Store the image surface and the PNG encoded embedded image. The thumbnail uses the surface, the SVG uses
        # the embedded link
        icon_surface, ctx = g15util.load_surface_from_file(icon)
        self.attributes["icon"] = icon_surface
        self.properties["icon"] = g15util.get_embedded_image_url(icon_surface)
            
        self.properties["subtitle"] = self.feed["feed"]["subtitle"]
        self.properties["updated"] = "%s %s" % ( time.strftime("%H:%M", self.feed.updated), time.strftime("%a %d %b", self.feed.updated) )
        self.attributes["entries"] = self.feed.entries
        if self.index > -1:
            self.attributes["selected"] = self.selected_entry
            self.attributes["selected_idx"] = self.index
        self.screen.redraw(self.page)
        
    def selection_changed(self):        
        if self.index > -1 and self.index < len(self.feed.entries):
            self.selected_entry = self.feed.entries[self.index]
        else:
            self.index = -1
            self.selected_entry = None
        self.reload()
        self.screen.redraw(self.page)
        self.screen.applet.resched_cycle()
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP and self.screen.get_visible_page() == self.page:
            if g15driver.G_KEY_UP in keys or g15driver.G_KEY_L2 in keys:
                if self.index < 0:
                    self.index = len(self.feed.entries) - 1
                else:
                    self.index -= 1
                self.selection_changed()
                return True
            elif g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L3 in keys:
                if self.index >= len(self.feed.entries):
                    self.index = 0
                else:
                    self.index += 1
                self.selection_changed()
                return True
            elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L4 in keys:
                if self.selected_entry != None:
                    subprocess.Popen(['xdg-open', self.selected_entry.link])
                    
                # Open in browser
                return True
                
        return False
    
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        if "icon" in self.attributes:
            return g15util.paint_thumbnail_image(allocated_size, self.attributes["icon"], canvas)
        
    def paint(self, canvas):
        self.theme.draw(canvas, self.properties, self.attributes)
    
class G15RSS():
    
    def __init__(self, gconf_client,gconf_key, screen):
        self.screen = screen;
        self.gconf_key = gconf_key
        self.gconf_client = gconf_client

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
        self.refresh_timer = g15util.schedule("FeedRefreshTimer", get_update_time(self.gconf_client, self.gconf_key) * 60.0, self.refresh)
        
    def refresh(self):
        for page in self.pages:
            self.pages[page].reload()
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
                self.pages[url] = G15FeedPage(self, url)
                
        # Remove pages that no longer exist
        to_remove = []
        for page_url in self.pages:
            page = self.pages[page_url]
            if not page.url in feed_list:
                self.screen.del_page(page.page)
                to_remove.append(page_url)
        for page in to_remove:
            del self.pages[page]
            
