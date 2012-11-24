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
_ = g15locale.get_translation("lcdbiff", modfile = __file__).ugettext

import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15plugin as g15plugin
import gnome15.g15accounts as g15accounts
import os
import pwd
import gtk
import traceback
import re
from poplib import POP3_SSL
from poplib import POP3
from imaplib import IMAP4
from imaplib import IMAP4_SSL
 
# Logging
import logging
logger = logging.getLogger("lcdbiff")

# Plugin details - All of these must be provided
id = "lcdbiff"
name = _("POP3 / IMAP Email Notification")
description = _("Periodically checks your email accounts for any waiting messages. Currently supports POP3 and IMAP \
protocols. For models without a screen, the M-Key lights will be flashed when there is an email \
waiting. For models with a screen, a page showing all unread mail counts will be displayed, and an \
icon added to the panel indicating overall status.")
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = _("Copyright (C)2010 Brett Smith")
site = "http://www.gnome15.org/"
has_preferences = True
needs_network = True
unsupported_models = [ g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous item"), 
         g15driver.NEXT_SELECTION : _("Next item"),
         g15driver.NEXT_PAGE : _("Next page"),
         g15driver.PREVIOUS_PAGE : _("Previous page"),
         g15driver.SELECT : _("Compose new mail"),
         g15driver.VIEW : _("Check mail status")
         }

# Constants
CURRENT_USERNAME=pwd.getpwuid(os.getuid())[0] 
PROTO_POP3 = "pop3"
PROTO_IMAP = "imap"
TYPES = [ PROTO_POP3, PROTO_IMAP ]
CONFIG_PATH = "~/.config/gnome15/plugin-data/lcdbiff/mailboxes.xml"
CONFIG_ITEM_NAME = "mailbox"

def create(gconf_key, gconf_client, screen):
    return G15Biff(gconf_client, gconf_key, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    G15BiffPreferences(parent, gconf_client, gconf_key)

def changed(widget, key, gconf_client):
    gconf_client.set_bool(key, widget.get_active())
    
def get_update_time(gconf_client, gconf_key):
    val = gconf_client.get_int(gconf_key + "/update_time")
    if val == 0:
        val = 10
    return val

'''
Abstract mail checker. Subclasses are responsible for connecting
to mail stores and retrieving the number of unread messages.
'''
class Checker():
    
    def __init__(self, account_manager):
        self.account_manager = account_manager
    
    def get_username(self, account):
        username = account.get_property("username", "")
        return username if username != "" else CURRENT_USERNAME
    
    def get_hostname(self, account):
        hostname = account.get_property("server", "")
        pre, _, _ = hostname.partition(":")
        return pre if pre != "" else "localhost"
        
    def get_port_or_default(self, account, default_port):
        hostname = account.get_property("server", "")
        _, sep, post = hostname.partition(":")
        if sep == "":
            return default_port
        return int(post)
    
    def save_password(self, account, password, default_port):    
        hostname = self.get_hostname(account)
        port = self.get_port_or_default(account, default_port)
        self.account_manager.store_password(account, password, hostname, port)
    
    def get_password(self, account, default_port, force_dialog = False):        
        hostname = self.get_hostname(account)
        port = self.get_port_or_default(account, default_port)
        return self.account_manager.retrieve_password(account, hostname, port, force_dialog)
    
'''
POP3 checker. Does the actual work of checking for emails using
the POP3 protocol.
'''
class POP3Checker(Checker):    
    
    
    def __init__(self, account_manager):
        Checker.__init__(self, account_manager)
    
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
                    raise Exception(_("Authentication cancelled"))
                try :
                    pop.user(username)
                    pop.pass_(password)            
                    self.save_password(account, password, default_port)            
                    return pop.stat()
                except Exception:
                    traceback.print_exc()
                    try :
                        pop.apop(username, password)            
                        self.save_password(account, password, default_port)            
                        return pop.stat()
                    except Exception:
                        traceback.print_exc()
        finally :
            pop.quit()
        return (0, 0)
    
'''
IMAP checker. Does the actual work of checking for emails using
the IMAP protocol.
'''
class IMAPChecker(Checker):   
     
    def __init__(self, account_manager):
        Checker.__init__(self, account_manager)
    
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
                        raise Exception(_("Authentication cancelled"))
                    
                    try :
                        if j == 0:
                            imap.login(username, password)
                        else:
                            imap.login_cram_md5(username, password)                         
                        self.save_password(account, password, default_port) 
                        status = imap.status(folder, "(UNSEEN)")
                        unread  = int(re.search("UNSEEN (\d+)", status[1][0]).group(1))      
                        count = ( unread, count )
                        return count 
                    except Exception:
                        traceback.print_exc()
                          
                finally:
                    imap.logout()   
            
        return count

    
'''
Superclass of the UI mail protocol specific configuration. Currently
all types support server, username and SSL options, although
this may change in future
'''     
class G15BiffOptions(g15accounts.G15AccountOptions):
    def __init__(self, account, account_ui):
        g15accounts.G15AccountOptions.__init__(self, account, account_ui)
                
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
        self.account_ui.save_accounts()
        
    def _ssl_changed(self, widget):
        self.account.properties["ssl"] = "true" if widget.get_active() else "false"
        self.account_ui.save_accounts()
        
    def _username_changed(self, widget):
        self.account.properties["username"] = widget.get_text()
        self.account_ui.save_accounts()
        
'''
POP3 configuration UI
'''    
class G15BiffPOP3Options(G15BiffOptions):
    

    def __init__(self, account, account_ui):
        G15BiffOptions.__init__(self, account, account_ui)
    
'''
IMAP configuration UI. Adds the additional Folder widget
'''
class G15BiffIMAPOptions(G15BiffOptions):
      
    def __init__(self, account, account_ui):
        G15BiffOptions.__init__(self, account, account_ui)
        folder = self.widget_tree.get_object("Folder")
        folder.connect("changed", self._folder_changed)
        folder.set_text(self.account.properties["folder"] if "folder" in self.account.properties else "INBOX")
        
    def _folder_changed(self, widget):
        self.account.properties["folder"] = widget.get_text()
        self.account_ui.save_accounts()
        
'''
Configuration UI
'''    
class G15BiffPreferences(g15accounts.G15AccountPreferences):
    
    
    def __init__(self, parent, gconf_client, gconf_key):
        g15accounts.G15AccountPreferences.__init__(self, parent, gconf_client, \
                                                   gconf_key, \
                                                   CONFIG_PATH, \
                                                   CONFIG_ITEM_NAME, \
                                                   10)
        
    def get_account_types(self):
        return [ PROTO_POP3, PROTO_IMAP ]
    
    def get_account_type_name(self, account_type):
        return _(account_type)
        
    def create_options_for_type(self, account, account_type):
        if account_type == PROTO_POP3:
            return G15BiffPOP3Options(account, self)
        else:
            return G15BiffIMAPOptions(account, self)
            
   
'''
Account menu item
'''
 
class MailItem(g15theme.MenuItem):
    def __init__(self, component_id, gconf_client, account, plugin):
        g15theme.MenuItem.__init__(self, component_id)
        self.account = account
        self.count = 0
        self.gconf_client = gconf_client
        self.status = "Unknown"
        self.error = None
        self.plugin = plugin
        self.refreshing = False
        
    def get_theme_properties(self):        
        item_properties = g15theme.MenuItem.get_theme_properties(self)       
        item_properties["item_name"] = self.account.name
        if self.error != None:
            item_properties["item_alt"] = _("Error")
        else: 
            if self.count > 0:
                item_properties["item_alt"] = "%d" % ( self.count )
            else:
                item_properties["item_alt"] = _("None")
        item_properties["item_type"] = ""
        
        if self.refreshing:
            if self.plugin.screen.driver.get_bpp() == 1:
                item_properties["item_icon"] =  os.path.join(os.path.dirname(__file__), "mono-mail-refresh.gif")
            else:
                item_properties["item_icon"] =  g15util.get_icon_path(["view-refresh", "stock_refresh", "gtk-refresh", "view-refresh-symbolic"])
        elif self.error is not None:            
            if self.plugin.screen.driver.get_bpp() == 1:
                item_properties["item_icon"] = os.path.join(os.path.dirname(__file__), "mono-mail-error.gif")
            else:
                item_properties["item_icon"] =  g15util.get_icon_path("new-messages-red")
        else:
            if self.count > 0:
                if self.plugin.screen.driver.get_bpp() == 1:
                    item_properties["item_icon"] = os.path.join(os.path.dirname(__file__), "mono-mail-new.gif")
                else:                        
                    item_properties["item_icon"] =  g15util.get_icon_path("indicator-messages-new")
            else:
                if self.plugin.screen.driver.get_bpp() == 1:
                    item_properties["item_icon"] = ""
                else:
                    item_properties["item_icon"] =  g15util.get_icon_path("indicator-messages")
        
        return item_properties
    
    def activate(self):
        email_client = self.gconf_client.get_string("/desktop/gnome/url-handlers/mailto/command")
        logger.info("Running email client %s" % email_client)
        if email_client != None:
            call_str = "%s &" % email_client.replace("%s", "").replace("%U", "mailto:")
            os.system(call_str)
         
'''
Gnome15 LCDBiff plugin
'''
            
class G15Biff(g15plugin.G15MenuPlugin):

    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15MenuPlugin.__init__(self, gconf_client, gconf_key, screen, ["mail-inbox", "mail-folder-inbox" ], id, "Email")
        self.refresh_timer = None       

    def activate(self):
        self.total_count = 0
        self.items = []
        self.attention = False
        self.thumb_icon = None
        self.index = 0
        self.light_control = None
        self.account_manager = g15accounts.G15AccountManager(CONFIG_PATH, CONFIG_ITEM_NAME)
        self.account_manager.add_change_listener(self)
        self.checkers = { PROTO_POP3 : POP3Checker(self.account_manager), PROTO_IMAP: IMAPChecker(self.account_manager) }
        if self.screen.driver.get_bpp() > 0:
            g15plugin.G15MenuPlugin.activate(self)
        self.update_time_changed_handle = self.gconf_client.notify_add(self.gconf_key + "/update_time", self._update_time_changed)
        self.schedule_refresh(10.0)
        self.screen.key_handler.action_listeners.append(self)
            
    def deactivate(self):
        self.screen.key_handler.action_listeners.remove(self)
        g15plugin.G15MenuPlugin.deactivate(self)
        self._stop_blink()
        if self.refresh_timer:
            self.refresh_timer.cancel()
            self.refresh_timer.task_queue.stop()
        self.gconf_client.notify_remove(self.update_time_changed_handle)
        
    def action_performed(self, binding):
        if binding.action == g15driver.VIEW:
            if self.refresh_timer:
                self.refresh_timer.cancel()
            self.refresh()
        
    def load_menu_items(self):
        items = []
        self.account_manager.load()
        i = 0
        for account in self.account_manager.accounts:
            items.append(MailItem("mailitem-%d" % i, self.gconf_client, account, self))
            i += 1
        if self.screen.driver.get_bpp() != 0:
            self.menu.selected = items[0] if len(items) > 0 else None
            self.menu.remove_all_children()
            self.menu.set_children(items)
        self.items = items
        
    def create_page(self):
        page = g15plugin.G15MenuPlugin.create_page(self)
        page.panel_painter = self._paint_panel
        page.thumbnail_painter = self._paint_thumbnail
        return page
    
    def schedule_refresh(self, time = - 1):
        if time == -1:
            time = get_update_time(self.gconf_client, self.gconf_key) * 60.0        
        self.refresh_timer = g15util.queue("lcdbiff-%s" % self.screen.device.uid, "MailRefreshTimer", time, self.refresh)
        
    def refresh(self):
        t_count = 0
        t_errors = 0
        for item in self.items:
            try :
                item.refreshing = True
                self.page.redraw()
                status = self._check_account(item.account)
                item.count  = status[0]
                t_count += item.count
                item.error = None
                item.refreshing = False
            except Exception as e:
                item.refreshing = False
                t_errors += 1
                item.error = e
                item.count = 0
                if logger.level < logging.WARN and logger.level != logging.NOTSET:
                    traceback.print_exc()
                
        self.total_count = t_count
        self.total_errors = t_errors
        
        if self.total_errors > 0:
            self._stop_blink()
            self.attention = True   
            if self.screen.driver.get_bpp() == 1:
                self.thumb_icon = g15util.load_surface_from_file(os.path.join(os.path.dirname(__file__), "mono-mail-error.gif"))
            elif self.screen.driver.get_bpp() > 0:
                self.thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path(["new-messages-red","messagebox_critical"]))
        else:
            if self.total_count > 0:
                self._start_blink()
                self.attention = True
                if self.screen.driver.get_bpp() == 1:
                    self.thumb_icon = g15util.load_surface_from_file(os.path.join(os.path.dirname(__file__), "mono-mail-new.gif"))
                elif self.screen.driver.get_bpp() > 0:
                    self.thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path(["indicator-messages-new", "mail-message-new"]))
            else:
                self._stop_blink()
                self.attention = False   
                if self.screen.driver.get_bpp() == 1:
                    self.thumb_icon = None
                elif self.screen.driver.get_bpp() > 0:
                    self.thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path(["indicator-messages", "mail-message"]))

        if self.screen.driver.get_bpp() > 0:        
            self.screen.redraw(self.page)
            
        self.schedule_refresh()
    
    '''
    Private
    '''
    def _accounts_changed(self, account_manager):
        self._reload_menu()
        self.schedule_refresh()
        
    def _check_account(self, account):
        return self.checkers[account.type].check(account)
        
    def _start_blink(self):
        if not self.light_control:
            self.light_control = self.screen.driver.acquire_control_with_hint(g15driver.HINT_MKEYS, val = g15driver.MKEY_LIGHT_1 | g15driver.MKEY_LIGHT_2 | g15driver.MKEY_LIGHT_3)
            self.light_control.blink(off_val = self._get_mkey_value)
            
    def _get_mkey_value(self):
        return g15driver.get_mask_for_memory_bank(self.screen.get_memory_bank())
            
    def _stop_blink(self):
        if self.light_control:
            self.screen.driver.release_control(self.light_control)
            self.light_control = None
            
    def _reload_menu(self):
        self.load_menu_items()
        if self.screen.driver.get_bpp() == 1:
            self.screen.redraw(self.page)
    
    def _update_time_changed(self, client, connection_id, entry, args):
        self.refresh_timer.cancel()
        self.schedule_refresh()
        
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None:
            if self.thumb_icon != None:
                size = g15util.paint_thumbnail_image(allocated_size, self.thumb_icon, canvas)
                return size
    
    def _paint_panel(self, canvas, allocated_size, horizontal):
        if self.page != None:
            if self.thumb_icon != None and self.attention:
                size = g15util.paint_thumbnail_image(allocated_size, self.thumb_icon, canvas)
                return size
            
