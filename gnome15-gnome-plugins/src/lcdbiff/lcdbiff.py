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
 
import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15globals  as g15globals
import gnome15.g15screen  as g15screen
import gobject
import subprocess
import time
import os
import re
import feedparser
import gtk
import gconf
import traceback
import gnomekeyring as gk
 
from threading import Lock
from lxml import etree
from poplib import *
from imaplib import *

# Plugin details - All of these must be provided
id = "lcdbiff"
name = "POP3 / IMAP Email Notification"
description = "Periodically checks your email accounts for any waiting messages. Currently supports POP3 and IMAP " + \
        "protocols."
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = "Copyright (C)2010 Brett Smith"
site = "http://www.gnome15.org/"
has_preferences = True
unsupported_models = [ g15driver.MODEL_G110 ]

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
        val = 10
    return val

class Checker():
    '''
    Abstract mail checker. Subclasses are responsible for connecting
    to mail stores and retrieving the number of unread messages
    '''
    
    def __init__(self):
        self.lock = Lock()
        self.password = None
    
    def get_username(self, account):
        username = account.get_property("username", "")
        return username if username != "" else os.environ["LOGNAME"]
    
    def get_hostname(self, account):
        hostname = account.get_property("server", "")
        pre, sep, post = hostname.partition(":")
        return pre if pre != "" else "localhost"
        
    def get_port_or_default(self, account, default_port):
        hostname = account.get_property("server", "")
        pre, sep, post = hostname.partition(":")
        if sep == "":
            return default_port
        return int(post)
    
    def save_password(self, account, password, default_port):    
        # Authenticated, save the password in the keyring
        
        username = self.get_username(account)
        hostname = self.get_hostname(account)
        port = self.get_port_or_default(account, default_port) 
       
        name = account.type + "://" + username + "@" + hostname + ":" + str(port)
        id = gk.item_create_sync("login", gk.ITEM_NETWORK_PASSWORD, name, {'service':account.type,
                                                                           'server':hostname,
                                                                           'username':username,
                                                                           'port':port}, password, True)
        
    def find_secret(self, name):  
        try :
            keyring = "login"
            for id in gk.list_item_ids_sync(keyring):
                item = gk.item_get_info_sync(keyring, id)
                display_name = item.get_display_name()
                if name == display_name:
                    self.password  = item.get_secret() 
                    return  
        finally:
            self.lock.release()

    
    def get_password(self, account, default_port, force_dialog = False):
        username = self.get_username(account)
        hostname = self.get_hostname(account)
        port = self.get_port_or_default(account, default_port) 
        secret = None
        name = account.type + "://" + username + "@" + hostname + ":" + str(port)
        
        '''
        Find the item. It appears gnome keyring access must be run on the gobject loop? I don't 
        really understand the problem, but doing this seems to fix it
        
        TODO find out what is actually happening
        '''
        self.lock.acquire()
        self.password = None
        gobject.idle_add(self.find_secret, name)
        self.lock.acquire()
        self.lock.release()
        if self.password != None:
            return self.password
                
        # Ask for the password
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "password.glade"))
        dialog = widget_tree.get_object("PasswordDialog")
        text_widget = widget_tree.get_object("Text")
        text_widget.set_text("The account <b>" + account.name + "</b> for the user <b>" + username + "</b>.\n" + \
                      "requires a password, This will be stored in the Gnome Keyring and \n" + \
                      "and will not be asked for again unless there is some later problem\n" + \
                      "problem authentication (for example as the result of\n" + \
                      "a password change).")       
        text_widget.set_use_markup(True)     
        password_widget = widget_tree.get_object("Password")
        dialog.show_all()
        
        response = dialog.run()
        try :    
            if response == 1:
                return password_widget.get_text()
        finally :         
            dialog.destroy()
            
        return None

class POP3Checker(Checker):    
    '''
    POP3 checker. Does the actual work of checking for emails using
    the POP3 protocol.
    '''
    
    def __init__(self):
        Checker.__init__(self)
    
    def check(self, account):
        ssl = account.get_property("ssl", "false")
        default_port = 995 if ssl else 110
        port = self.get_port_or_default(account, default_port)
        if ssl:
            pop = POP3_SSL(self.get_hostname(account), port)
        else:
            pop = POP3(self.get_hostname(account), port, 7.0)
        try :
            username = self.get_username(account)
            for i in range(0, 3):
                password = self.get_password(account, default_port, i > 0)
                if password == None or password == "":
                    raise Exception("Authentication cancelled")
                try :
                    pop.user(username)
                    pop.pass_(password)            
                    self.save_password(account, password, default_port)            
                    return pop.stat()
                except Exception as e:
                    traceback.print_exc()
                    try :
                        pop.apop(username, password)            
                        self.save_password(account, password, default_port)            
                        return pop.stat()
                    except Exception as e:
                        traceback.print_exc()
        finally :
            pop.quit()
        return (0, 0)
    
class IMAPChecker(Checker):   
    '''
    IMAP checker. Does the actual work of checking for emails using
    the IMAP protocol.
    '''
     
    def __init__(self):
        Checker.__init__(self)
    
    def check(self, account):
        ssl = account.get_property("ssl", "false")
        folder = account.get_property("folder", "INBOX")
        default_port = 993 if ssl else 143
        port = self.get_port_or_default(account, default_port)
        count = ( 0, 0 )
        username = self.get_username(account)
        for i in range(0, 3):
            
            for j in range(0, 2):
                if ssl:
                    imap = IMAP4_SSL(self.get_hostname(account), port)
                else:
                    imap = IMAP4(self.get_hostname(account), port)
                
                try :
                    password = self.get_password(account, default_port, i > 0)
                    if password == None or password == "":
                        raise Exception("Authentication cancelled")
                    
                    try :
                        if j == 0:
                            imap.login(username, password)
                        else:
                            imap.authenticate(username, password)                         
                        self.save_password(account, password, default_port) 
                        status = imap.status(folder, "(UNSEEN)")
                        unread  = int(re.search("UNSEEN (\d+)", status[1][0]).group(1))      
                        count = ( unread, count )
                        return count 
                    except Exception as e:
                        traceback.print_exc()
                          
                finally:
                    imap.logout()   
            
        return count

class G15BiffAccountManager():  
    
    '''
    Manages the storage and loading of the account list. This is
    stored as an XML file in the Gnome configuration directory
    '''  
    
    def __init__(self):
        self._conf_file = os.path.expanduser("~/.gnome2/gnome15/lcdbiff/mailboxes.xml")
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
   
class G15BiffOptions():
    
    '''
    Superclass of the UI protocol specific configuration. Currently
    all types support server, username and SSL options, although
    this may change in future
    '''     
    def __init__(self, account, account_manager):        
        self.account = account
        self.account_manager = account_manager
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "%s.glade" % account.type))
        self.component = self.widget_tree.get_object("OptionPanel")
        
        # Both currently have server, username and SSL widgets
        server = self.widget_tree.get_object("Server")
        username = self.widget_tree.get_object("Username")
        ssl = self.widget_tree.get_object("SSL")
        
        # Events
        server.connect("changed", self._server_changed)
        username.connect("changed", self._username_changed)
        ssl.connect("toggled", self._ssl_changed)
        
        # Set initial values
        server.set_text(self.account.properties["server"] if "server" in self.account.properties else "")
        username.set_text(self.account.properties["username"] if "username" in self.account.properties else "")
        ssl.set_active(self.account.properties["ssl"] == "true" if "ssl" in self.account.properties else False)
        
    def _server_changed(self, widget):
        self.account.properties["server"] = widget.get_text()
        self.account_manager.save()
        
    def _ssl_changed(self, widget):
        self.account.properties["ssl"] = "true" if widget.get_active() else "false"
        self.account_manager.save()
        
    def _username_changed(self, widget):
        self.account.properties["username"] = widget.get_text()
        self.account_manager.save()
        
        
class G15BiffPOP3Options(G15BiffOptions):
    '''
    POP3 configuration UI
    '''

    def __init__(self, account, account_manager):
        G15BiffOptions.__init__(self, account, account_manager)
    
class G15BiffIMAPOptions(G15BiffOptions):
    '''
    IMAP configuration UI. Adds the additional Folder widget
    '''
      
    def __init__(self, account, account_manager):
        G15BiffOptions.__init__(self, account, account_manager)
        folder = self.widget_tree.get_object("Folder")
        folder.connect("changed", self._folder_changed)
        folder.set_text(self.account.properties["folder"] if "folder" in self.account.properties else "INBOX")
        
    def _folder_changed(self, widget):
        self.account.properties["folder"] = widget.get_text()
        self.account_manager.save()
        
class G15BiffPreferences():
    '''
    Configuration UI
    '''
     
    
    def __init__(self, parent, gconf_client, gconf_key):
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.visible_options = None
        
        self.account_mgr = G15BiffAccountManager()
        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "lcdbiff.glade"))
        
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
        dialog = self.widget_tree.get_object("BiffDialog")
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
   
'''
Account menu item
'''
 
class MailItem(g15theme.MenuItem):
    def __init__(self, account):
        g15theme.MenuItem.__init__(self)
        self.account = account
        self.count = 0
        self.icon_path = g15util.get_icon_path("indicator-messages")
        self.status = "Unknown"
        self.error = None
        
    def draw(self, selected, canvas, menu_properties, menu_attributes):        
        item_properties = {}
        if selected == self:
            item_properties["item_selected"] = True
       
        item_properties["item_name"] = self.account.name
        
        if self.error != None:
            item_properties["item_alt"] = "Error"
        else: 
            if self.count > 0:
                item_properties["item_alt"] = "%d" % ( self.count )
            else:
                item_properties["item_alt"] = "None"
        item_properties["item_type"] = ""
        item_properties["item_icon"] =  g15util.load_surface_from_file(self.icon_path)
        
        self.theme.draw(canvas, item_properties)
        return self.theme.bounds[3]
         
'''
Gnome15 LCDBiff plugin
'''
           
class G15Biff():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self.screen = screen;
        self.gconf_key = gconf_key
        self.gconf_client = gconf_client

    def activate(self):
        gk.is_available()
        keyrings = gk.list_keyring_names_sync()

        self.total_count = 0
        self.attention = False
        self.thumb_icon = None
        self.index = 0
        self.account_manager = G15BiffAccountManager()
        self._reload_theme()
        self.page = self.screen.new_page(self._paint, id="Biff", priority=g15screen.PRI_NORMAL, panel_painter = self._paint_panel, thumbnail_painter = self._paint_thumbnail)
        self.page.set_title("Email")
        self._reload_menu()        
        self.update_time_changed_handle = self.gconf_client.notify_add(self.gconf_key + "/update_time", self._update_time_changed)
        self.schedule_refresh(10.0)
        
    def handle_key(self, keys, state, post):
        for page in self.pages:
            if self.pages[page].handle_key(keys, state, post):
                return True
        return False
        
    def schedule_refresh(self, time = - 1):
        if time == -1:
            time = get_update_time(self.gconf_client, self.gconf_key) * 60.0        
        self.refresh_timer = g15util.queue("lcdbiff", "MailRefreshTimer", time, self.refresh)
        
    def refresh(self):
        self._reload_menu()
        self.total_count = 0
        self.total_errors = 0
        for item in self.menu.get_items():
            try :
                status = self.account_manager.check_account(item.account)
                item.count  = status[0]
                self.total_count += item.count
                if item.count > 0:
                    item.icon_path =  g15util.get_icon_path("indicator-messages-new")
                else:
                    item.icon_path =  g15util.get_icon_path("indicator-messages")
                item.error = None
            except Exception as e:
                self.total_errors += 1
                item.error = e
                item.count = 0
                item.icon_path =  g15util.get_icon_path("new-messages-red")
                traceback.print_exc()
        
        if self.total_errors > 0:
            self.attention = True   
            if self.screen.driver.get_bpp() == 1:
                self.thumb_icon = g15util.load_surface_from_file(os.path.join(os.path.dirname(__file__), "mono-mail-error.gif"))
            else:
                self.thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path("new-messages-red"))
        else:
            if self.total_count > 0:
                self.attention = True
                if self.screen.driver.get_bpp() == 1:
                    self.thumb_icon = g15util.load_surface_from_file(os.path.join(os.path.dirname(__file__), "mono-mail-new.gif"))
                else:
                    self.thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path("indicator-messages-new"))
            else:
                if self.screen.driver.get_bpp() == 1:
                    self.thumb_icon = g15util.load_surface_from_file(os.path.join(os.path.dirname(__file__), "mono-mail-new.gif"))
                else:
                    self.thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path("indicator-messages"))
        
        self.screen.redraw(self.page)
        self.schedule_refresh()
    
    def deactivate(self):
        self.gconf_client.notify_remove(self.update_time_changed_handle)
        self.screen.del_page(self.page)
        self.page = None

    def destroy(self):
        pass
    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP and self.screen.get_visible_page() == self.page:
            if self.menu.handle_key(keys, state, post):
                return True
            elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                if self.index != -1:
                    email_client = self.gconf_client.get_string("/desktop/gnome/url-handlers/mailto/command")
                    if email_client != None:
                        os.system("%s &" % email_client.replace("%s", ""))
                return True
                
        return False
        
    '''
    Private
    '''
    def _selection_changed(self): 
        self.screen.redraw(self.page)
        
    def _reload_menu(self):
        self.menu.clear_items()
        self.account_manager.load()
        for account in self.account_manager.accounts:
            self.menu.add_item(MailItem(account))
        items = self.menu.get_items()
        self.menu.selected = items[0] if len(items) > 0 else None
        self.screen.redraw(self.page)
        
    def _reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(g15globals.themes_dir, "default"), self.screen, "menu-screen")
        self.menu = g15theme.Menu("menu", self.screen)
        self.menu.on_selected = self._selection_changed
        self.theme.add_component(self.menu)
        self.theme.add_component(g15theme.Scrollbar("viewScrollbar", self.menu.get_scroll_values))
    
    def _update_time_changed(self, client, connection_id, entry, args):
        self.refresh_timer.cancel()
        self.schedule_refresh()
        
    def _paint(self, canvas):
        self.theme.draw(canvas,
                        properties={
                                      "title" : "Email",
                                      "icon" : g15util.get_icon_path("mail-inbox")
                                      },
                        attributes={
                                      "items" : self.menu.get_items(),
                                      "selected" : self.menu.selected
                                      })
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None:
            if self.thumb_icon != None:
                size = g15util.paint_thumbnail_image(allocated_size, self.thumb_icon, canvas)
                return size
    
    def _paint_panel(self, canvas, allocated_size, horizontal):
        if self.page != None:
            if self.thumb_icon != None and self.attention == 1:
                size = g15util.paint_thumbnail_image(allocated_size, self.thumb_icon, canvas)
                return size
            
