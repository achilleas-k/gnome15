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

"""
Classes that may be used by plugins that require account management, usually
to access some kind of network server such as Email, Calendar or Feeds.

A GTK UI is also provided that subclasses may plug-in their own protocol specific
configuration widgets.

Accounts are stored as simple XML files in .g
"""

import os
from lxml import etree 
import gtk
import g15globals
import g15scheduler
import g15gconf
import g15python_helpers
import pyinotify
import pwd
from threading import Lock
import gobject
import keyring


"""
Functions
"""

"""
Configure monitoring of account files. This allows plugins to get notified
when accounts they are using change
"""
account_listeners = []

watch_manager = pyinotify.WatchManager()
mask = pyinotify.IN_DELETE | pyinotify.IN_MODIFY | pyinotify.IN_CREATE | pyinotify.IN_ATTRIB  # watched events

class EventHandler(pyinotify.ProcessEvent):
    
    def _notify(self, event):
        for a in account_listeners:
            a(event)
        
    def process_IN_MODIFY(self, event):
        self._notify(event)
        
    def process_IN_CREATE(self, event):
        self._notify(event)
        
    def process_IN_ATTRIB(self, event):
        self._notify(event)

    def process_IN_DELETE(self, event):
        self._notify(event)

notifier = pyinotify.ThreadedNotifier(watch_manager, EventHandler())
notifier.name = "AccountsPyInotify"
notifier.setDaemon(True)
notifier.start()

CURRENT_USERNAME=pwd.getpwuid(os.getuid())[0]

class Status():
    def __init__(self):
        self.stopping = False
        
STATUS = Status()

'''
Helper classes for getting a secret from the keyring
'''
class G15Keyring():
    
    def __init__(self):
        self.lock = Lock()
        self.password = None
    
    def get_username(self, account):
        username = account.get_property("username", "")
        return username if username != "" else CURRENT_USERNAME
    
    def get_uri_and_props(self, account, hostname = None, port = None):
        
        username = self.get_username(account)
        name = account.type + "://" + username
        
        props = {
                 'service':account.type,
                 'username':username
                 }
        
        if hostname is not None:
            name = name + "@" + hostname
            props['server'] = hostname
            if port is not None:
                props['port'] = port
                name = name + ":" + str(port)
                
        return props, name
    
    def store_password(self, account, password, hostname = None, port = None):
        _, name = self.get_uri_and_props(account, hostname, port)        
        keyring.set_password(name, self.get_username(account), password)
        
    def find_secret(self, account, name, release_lock = True): 
        username = self.get_username(account) 
        try :
            if STATUS.stopping:
                self.password = None
                return
        
            pw = keyring.get_password(name, username)
            if pw is not None:
                self.password = pw
                return
                
            # Ask for the password
            widget_tree = gtk.Builder()
            widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "password.glade"))
            dialog = widget_tree.get_object("PasswordDialog")
            text_widget = widget_tree.get_object("Text")
            text_widget.set_text(_("The account <b>%s</b> for the user <b>%s</b>.\n\
requires a password, This will be stored in the Gnome Keyring and \n\
and will not be asked for again unless there is some later problem\n\
problem authentication (for example as the result of\n\
a password change).") % (account.name, username))       
            text_widget.set_use_markup(True)     
            password_widget = widget_tree.get_object("Password")
            dialog.show_all()

            response = dialog.run()
            try :    
                if response == 1:
                    self.password = password_widget.get_text()
            finally :         
                dialog.destroy()
                
            return
        finally:
            if release_lock:
                self.lock.release()

    
    def retrieve_password(self, account, hostname = None, port = None, force_dialog = False):
        
        _, name = self.get_uri_and_props(account, hostname, port)
        
        '''
        Find the item. It appears gnome keyring access must be run on the gobject loop? I don't 
        really understand the problem, but doing this seems to fix it
        
        TODO find out what is actually happening
        '''
        if g15python_helpers.is_gobject_thread():
            self.find_secret(account, name, False)            
        else:
            self.lock.acquire()
            self.password = None
            gobject.idle_add(self.find_secret, account, name)
            self.lock.acquire()
            self.lock.release()
        if self.password != None:
            return self.password


class G15AccountManager(G15Keyring):  
    """
    Manages the storage and loading of an account list. This is
    stored as an XML file in the Gnome configuration directory
    """    
    
    def __init__(self, file_path, item_name):
        """
        Constructor
        
        Keyword arguments:
        file_path    --    location accounts are stored. Directory will be created if it does not exist
        item_name    --    name of item in XML file
        """
        G15Keyring.__init__(self)
        
        self._conf_file = os.path.expanduser(file_path)
        self.item_name = item_name
        self.load()
        self.listeners = {}
        self.listener_functions = {}
        
    def add_change_listener(self, listener):
        self.listeners[listener] = watch_manager.add_watch(os.path.dirname(self._conf_file), mask, rec=True)
        def a(event):
            self.load()
            if event.pathname == self._conf_file:
                listener(self)
        self.listener_functions[listener] = a
        account_listeners.append(a)
        
    def remove_change_listener(self, listener):
        wdd = self.listeners[listener]
        account_listeners.remove(self.listener_functions[listener])
        del self.listener_functions[listener]
        for k in wdd:
            try:
                watch_manager.rm_watch(wdd[k],quiet = False)
            except:
                pass
            
    def load(self):
        accounts = []
        if not os.path.exists(self._conf_file):
            dir_path = os.path.dirname(self._conf_file)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        else:
            document = etree.parse(self._conf_file)        
            for element in document.getroot().xpath('//%s' % self.item_name):
                acc = G15Account(element.get("name"), element.get("type"))
                for property_element in element:
                    acc.properties[property_element.get("name")] = property_element.get("value") 
                accounts.append(acc)
                
        self.accounts = accounts
                
    
    def by_name(self, name):
        """
        Get an account given its name.
        
        Keyword arguments:
        name    --    account name
        """
        for acc in self.accounts:
            if acc.name == name:
                return acc
            
        
    def save(self):
        """
        Save all accounts.
        """        
        root = etree.Element("xml")
        document = etree.ElementTree(root)
        for acc in self.accounts:
            acc_el = etree.SubElement(root, self.item_name, type=acc.type, name=acc.name)
            for key in acc.properties:
                etree.SubElement(acc_el, "property", name=key, value=acc.properties[key])
        xml = etree.tostring(document)
        fh = open(self._conf_file, "w")
        try :
            fh.write(xml)
        finally :
            fh.close()
            
class G15Account():
    """
    A single account. An account has two main attributes,
    a name and a type. All protocol specific details are
    stored in the properties map.
    """   
    
    def __init__(self, name, account_type):
        """
        Constructor
        
        Keyword arguments:
        name         --    account name
        account_type --    account type
        """
        self.name = name
        self.type = account_type
        self.properties = {}
        
    def get_property(self, key, default_value=None): 
        return self.properties[key] if key in self.properties else default_value
   

class G15AccountOptions():
    """
    Superclass of the UI protocol specific configuration.
    """
    
    def __init__(self, account, account_ui):
        """
        Constructor
        
        Keyword arguments:
        account         --    account
        account_ui      --    instance of G15AccountPreferences that contains the options widget
        """        
        self.account = account
        self.account_ui = account_ui
       
class G15AccountPreferences(): 
    """
    Configuration UI
    """
    
    
    def __init__(self, parent, gconf_client, gconf_key, file_path, item_name, default_refresh = 60):
        """
        Constructor
        
        Keyword arguments:
        parent          -- parent GTK component (for modality)
        gconf_client    -- gconf client
        gconf_key       -- gconf key prefix for this plugin
        file_path       -- location of accounts file
        item_name       -- name of item in XML files
        """
        
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.visible_options = None
        self._save_timer = None
        self._adjusting = False
        
        self.account_mgr = G15AccountManager(file_path, item_name)
            
        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "accounts.glade"))
        
        # Models        
        self.type_model = self.widget_tree.get_object("TypeModel")
        self.account_model = self.widget_tree.get_object("AccountModel")   
        self.type_model.clear()     
        for t in self.get_account_types():
            self.type_model.append([ t, self.get_account_type_name(t) ])
        
        # Widgets
        self.account_type = self.widget_tree.get_object("TypeCombo")
        self.account_list = self.widget_tree.get_object("AccountList")
        self.url_renderer = self.widget_tree.get_object("URLRenderer")
        
        # Updates
        self.update_adjustment = self.widget_tree.get_object("UpdateAdjustment")
        self.update_adjustment.set_value(g15gconf.get_int_or_default(gconf_client, gconf_key + "/update_time", default_refresh))
        
        # Connect to events
        self.account_list.connect("cursor-changed", self._select_account)
        self.account_type.connect("changed", self._type_changed)
        self.update_adjustment.connect("value-changed", self._update_time_changed)
        self.url_renderer.connect("edited", self._url_edited)
        self.widget_tree.get_object("NewAccount").connect("clicked", self._new_url)
        self.widget_tree.get_object("RemoveAccount").connect("clicked", self._remove_url)
        
        # Configure widgets 
        self._reload_model()
        self._select_account()
        
        # Hide non-relevant stuff
        self.widget_tree.get_object("TypeContainer").set_visible(len(self.get_account_types()) > 1)
        
        # Additional options        
        place_holder = self.widget_tree.get_object("OptionsContainer")
        opts = self.create_general_options()
        if opts:       
            opts.reparent(place_holder)
        
        # Show dialog
        dialog = self.widget_tree.get_object("AccountDialog")
        dialog.set_transient_for(parent)
        
        ah = gconf_client.notify_add(gconf_key + "/urls", self._urls_changed);
        dialog.run()
        dialog.hide()
        gconf_client.notify_remove(ah)
        
    """
    Implement
    """
    def create_general_options(self):
        """
        Create general options for the dialog. These are added to the area
        beneath the refresh interval spinner
        """
        pass
    
    def get_account_type_name(self, account_type):
        """
        Get the localized account type name
        
        Keyword arguments:
        account_type     -- account type (always provided, will be same as account.type if exists)
        """
        raise Exception("Not implemented")
    
    def get_account_types(self):
        """
        Get the account types that are available
        """
        raise Exception("Not implemented")
    
    def create_options_for_type(self, account, account_type):
        """
        Create the concrete G15AccountOptions object given the account type name. 
        
        Keyword arguments:
        account          -- account object (will be None if this is for a new account)
        account_type     -- account type (always provided, will be same as account.type if exists)
        """
        raise Exception("Not implemented")
        
    """
    Private
    """
    def save_accounts(self):
        if not self._adjusting:
            if self._save_timer is not None:
                self._save_timer.cancel()
            self._save_timer = g15scheduler.schedule("SaveAccounts", 2, self._do_save_accounts)
        
    def _do_save_accounts(self):        
        self.account_mgr.save()
        
    def _update_time_changed(self, widget):
        self.gconf_client.set_int(self.gconf_key + "/update_time", int(widget.get_value()))
        
    def _url_edited(self, widget, row_index, value):
        row = self.account_model[row_index] 
        if value != "":
            acc = self.account_mgr.by_name(row[0])
            if acc == None:
                acc = G15Account(value, self.get_account_types()[0])
                self.account_mgr.accounts.append(acc)
            else: 
                acc.name = value
            self.save_accounts()
            self._reload_model()
            self.account_list.get_selection().select_path(row_index)
            self._select_account()
        else:
            acc = self.account_mgr.by_name(row[0])
            if acc is not None:
                self.account_mgr.accounts.remove(acc)
            self._reload_model()
        
    def _urls_changed(self, client, connection_id, entry, args):
        self._reload_model()
        
    def _reload_model(self):
        acc = self._get_selected_account()
        self.account_model.clear()
        for i in range(0, len(self.account_mgr.accounts)):
            account = self.account_mgr.accounts[i]
            row = [ account.name, True ]
            self.account_model.append(row)
            if account == acc:
                self.account_list.get_selection().select_path(i)
                
        (model, sel) = self.account_list.get_selection().get_selected()
        if sel == None:
            self.account_list.get_selection().select_path(0)
        
    def _new_url(self, widget):
        self.account_model.append(["", True])
        self.account_list.set_cursor_on_cell(str(len(self.account_model) - 1), focus_column=self.account_list.get_column(0), focus_cell=self.url_renderer, start_editing=True)
#        self.account_list.grab_focus()
        
    def _remove_url(self, widget):        
        (model, path) = self.account_list.get_selection().get_selected()
        url = model[path][0]
        acc = self.account_mgr.by_name(url)
        if acc is not None:
            self.account_mgr.accounts.remove(acc)
            self.save_accounts()
        self._reload_model()
        self._load_options_for_type()
        
    def _type_changed(self, widget):      
        sel = self._get_selected_type()      
        acc = self._get_selected_account()
        if acc.type != sel:
            acc.type = sel 
            self.save_accounts()
            self._load_options_for_type()
        
    def _load_options_for_type(self):
        account_type = self._get_selected_type()
        acc = self._get_selected_account()
        options = self.create_options_for_type(acc, account_type) if acc is not None else None
        if self.visible_options != None:
            self.visible_options.component.destroy()
        self.visible_options = options
        place_holder = self.widget_tree.get_object("PlaceHolder")
        for c in place_holder.get_children():
            place_holder.remove(c) 
        if self.visible_options is not None:                   
            self.visible_options.component.reparent(place_holder)
        else:                   
            l = gtk.Label("No options found for this account\ntype. Do you have all the required\nplugins installed?")
            l.xalign = 0.5
            l.show()
            place_holder.add(l)
     
    def _select_account(self, widget=None):       
        account = self._get_selected_account()
        self._adjusting = True
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
        self._adjusting = False
            
    def _get_selected_type(self):
        active = self.account_type.get_active()
        return None if active == -1 else self.type_model[active][0]
            
    def _get_selected_account(self):
        (model, path) = self.account_list.get_selection().get_selected()
        if path != None:
            return self.account_mgr.by_name(model[path][0])