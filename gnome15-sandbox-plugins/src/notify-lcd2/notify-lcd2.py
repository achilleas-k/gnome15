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

import os
import sys
import time
import dbus
import dbus.service
import dbus.exceptions
import gtk
import gtk.gdk
import Image
import subprocess
import traceback
import tempfile
import lxml.html
import Queue
import gconf

from threading import Timer
from threading import Thread
from threading import RLock
from dbus.exceptions import NameExistsException

# run it in a gtk window
if __name__ == "__main__":

    import gobject     
    from dbus.mainloop.glib import DBusGMainLoop
    from dbus.mainloop.glib import threads_init
                    
    gobject.threads_init()
    dbus.mainloop.glib.threads_init()
    DBusGMainLoop(set_as_default=True)
    loop = gobject.MainLoop()
    
    # Allow running from local path
    path = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), "..", "..", "main", "python")
    if os.path.exists(path):
        print "Adding",path,"to python path"
        sys.path.insert(0, path)
 
import gnome15.g15_screen as g15screen
import gnome15.g15_util as g15util
import gnome15.g15_globals as pglobals
import gnome15.g15_theme as g15theme
import gnome15.g15_driver as g15driver

# Logging
import logging
logging.basicConfig()
logger = logging.getLogger("notify")

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

# Plugin details - All of these must be provided
id="notify-lcd2"
name="Notify 2"
description="Take over as the Notification daemon and display messages on the LCD"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=True
unsupported_models = [ g15driver.MODEL_G110 ]
fork=True

IF_NAME="org.freedesktop.Notifications"
BUS_NAME="/org/freedesktop/Notifications"

# List of processes to try and kill so the notification DBUS server can be replaced
OTHER_NOTIFY_DAEMON_PROCESS_NAMES = [ 'notify-osd', 'notification-daemon', 'knotify4' ]

# NotificationClosed reasons
NOTIFICATION_EXPIRED = 1
NOTIFICATION_DISMISSED = 2
NOTIFICATION_CLOSED = 3
NOTIFICATION_UNDEFINED = 4

def create(gconf_key, gconf_client, screen):
    dbus = dbus.SessionBus()
    return G15NotifyLCD(gconf_client, gconf_key, screen, screen.driver )

def show_preferences(parent, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "notify-lcd.glade"))
    dialog = widget_tree.get_object("NotifyLCDDialog")
    dialog.set_transient_for(parent)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/respect_timeout", "RespectTimeout", False, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/allow_actions", "AllowActions", False, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/allow_cancel", "AllowCancel", False, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/enable_sounds", "EnableSounds", True, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/lcd_only", "LCDOnly", False, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/blink_keyboard", "BlinkKeyboard", False, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/change_keyboard_color", "ChangeKeyboardColor", False, widget_tree, True)
    g15util.configure_adjustment_from_gconf(gconf_client, gconf_key + "/blink_delay", "DelayAdjustment", 500, widget_tree)
    g15util.configure_colorchooser_from_gconf(gconf_client, gconf_key + "/color", "Color", ( 128, 128, 128 ), widget_tree, None)
    
    set_available(None, widget_tree)
    widget_tree.get_object("ChangeKeyboardColor").connect("toggled", set_available, widget_tree)
    widget_tree.get_object("BlinkKeyboard").connect("toggled", set_available, widget_tree)
    
    dialog.run()
    dialog.hide()
    
def set_available(widget, widget_tree):
    widget_tree.get_object("Color").set_sensitive(widget_tree.get_object("ChangeKeyboardColor").get_active())
    widget_tree.get_object("Delay").set_sensitive(widget_tree.get_object("BlinkKeyboard").get_active())

       
'''
Queued notification message
'''     
class G15Message():
    
    def __init__(self, id, icon, summary, body, timeout, actions, hints):
        self.id  = id
        self.set_details(icon, summary, body, timeout, actions, hints)
    
    def set_details(self, icon, summary, body, timeout, actions, hints):
        self.icon = icon
        self.summary = "None" if summary == None else summary
        if body != None and len(body) > 0:
            self.body = lxml.html.fromstring(body).text_content()
        else:
            self.body = body
        self.timeout = timeout
#            if timeout <= 0.0:
#                timeout = 10.0
        self.timeout = 10.0
        self.actions = []
        i = 0
        if actions != None:
            for j in range(0, len(actions), 2):
                self.actions.append((actions[j], actions[j + 1]))
        self.hints = hints
        self.embedded_image = None
        
        if self.icon == None or self.icon == "":
            if "image_data" in self.hints:
                image_struct = self.hints["image_data"]
                img_width = image_struct[0]
                img_height = image_struct[1]
                img_stride = image_struct[2]
                has_alpha = image_struct[3]
                bits_per_sample = image_struct[4]
                channels = image_struct[5]
                buf = ""
                for b in image_struct[6]:
                    buf += chr(b)
                pixbuf = gtk.gdk.pixbuf_new_from_data(buf, gtk.gdk.COLORSPACE_RGB, has_alpha, bits_per_sample, img_width, img_height, img_stride)
                fh, self.embedded_image = tempfile.mkstemp(suffix=".png",prefix="notify-lcd")
                file = os.fdopen(fh)
                file.close()
                pixbuf.save(self.embedded_image, "png")
            else:
                self.icon = g15util.get_icon_path("dialog-info", 1024)
    
    def close(self):
        if self.embedded_image != None:
            os.remove(self.embedded_image)
   
'''
DBus service implementing the freedesktop notification specification
'''     
class G15NotifyService(dbus.service.Object):
    
    def __init__(self, gconf_client, gconf_key, service, driver, bus):
        self.id = 1
        self._gconf_client = gconf_client
        self._driver = driver
        self._bus = bus
        self._gconf_key = gconf_key
        self._displayed_notification = 0
        self._active = True
        self._service = service
        self._timer = None
        self._redraw_timer = None
        self._blink_thread = None
        self._control_values = []
        self._message_queue = []
        self._message_map = {}
        self._current_message = None
        self._page = None
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ( pglobals.name, "TT", pglobals.version, "1.1" ) 
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='as')
    def GetCapabilities(self):
        caps = [ "body", "body-images", "icon-static" ]
        if self._gconf_client.get_bool(self._gconf_key + "/allow_actions"):
            caps.append("actions")
        enable_sounds = self._gconf_client.get(self._gconf_key + "/enable_sounds")
        if self._get_enable_sounds():
            caps.append("sounds")
    
    @dbus.service.method(IF_NAME, in_signature='susssasa{sv}i', out_signature='u')
    def Notify(self, app_name, id, icon, summary, body, actions, hints, timeout):
        try :                
            if self._active:
                timeout = float(timeout) / 1000.0
                if not self._gconf_client.get_bool(self._gconf_key + "/respect_timeout"):
                    timeout = 10.0                
                if not self._gconf_client.get_bool(self._gconf_key + "/allow_actions"):
                    actions = None
                
                # If a message with this ID is already queued, replace it's details
                if id in self._message_map:
                    message = self._message_map[id]
                    message.set_details(icon, summary, body, timeout, actions, hints) 
                    
                    # If this message is the visible one, then reset the timer
                    if message == self._message_queue[0]:
                        self._start_timer(message)
                    else:                     
                        self._do_draw()
                else:
                    # Otherwise queue a new message
                    message = G15Message(self.id, icon, summary, body, timeout, actions, hints)
                    self._message_queue.append(message)
                    self._message_map[self.id] = message                
                    self.id += 1
                    
                    if len(self._message_queue) == 1:
                        try :                
                            self._notify()                         
                        except Exception as blah:
                            traceback.print_exc()
                    else:         
                        self._do_draw()
                        
                return message.id                         
        except Exception as blah:
            traceback.print_exc()
    
    @dbus.service.method(IF_NAME, in_signature='u', out_signature='')
    def CloseNotification(self, id):
        if self._gconf_client.get_bool(self._gconf_key + "/allow_cancel") and len(self._message_queue) > 0:
            message = self._message_queue[0]
            if message.id == id:
                self._cancel_timer()
                self._move_to_next(NOTIFICATION_CLOSED)
            else:
                del self._message_map[id]
                for m in self._message_queue:
                    if m.id == id:
                        self._message_queue.remove(m)
                        self.NotificationClosed(id, NOTIFICATION_CLOSED)
                        break
        
    @dbus.service.signal(dbus_interface=IF_NAME,
                         signature='us')
    def ActionInvoked(self, id, action_key):
        pass
    
    @dbus.service.signal(dbus_interface=IF_NAME,
                         signature='uu')
    def NotificationClosed(self, id, reason):
        pass
    
    def clear(self):
        self._driver.CancelBlink()
        for message in self._message_queue:
            message.close()
        self._message_queue = []
        self._message_map = {}
        self._cancel_timer()
        page = self._screen.get_page("NotifyLCD")
        if page != None:
            self._screen.del_page(page)  
    
    def next(self):
        self._cancel_timer()
        self._move_to_next()
    
    def action(self):
        self._cancel_timer()
        message = self._message_queue[0]
        action = message.actions[0]
        self.ActionInvoked(message.id, action[0])
        self._move_to_next()
      
    ''' 
    Private
    '''       
    def _get_enable_sounds(self):
        enable_sounds = self._gconf_client.get(self._gconf_key + "/enable_sounds")
        return enable_sounds == None or enable_sounds.get_bool()
        
    def _reload_theme(self):
        self._page.LoadTheme(os.path.realpath(os.path.join(os.path.dirname(__file__), "default")), self._last_variant)
        
    def _get_properties(self):
        properties = {}        
        properties["title"] = self._current_message.summary
        properties["message"] = self._current_message.body
        if self._current_message.icon != None and len(self._current_message.icon) > 0:
            properties["icon"] = g15util.get_icon_path(self._current_message.icon)
        elif self._current_message.embedded_image != None:
            properties["icon"] = self._current_message.embedded_image
                    
        if str(len(self._message_queue) > 1):
            properties["next"] = "True"
             
        action = 1
        for a in self._current_message.actions:
            properties["action%d" % action] = a[1] 
            action += 1
        if len(self._current_message.actions) > 0:        
            properties["action"] = "True" 
            
        properties["remaining"] = str(self._get_remaining()) 
        
        return properties
    
    def _get_remaining(self):
        time_displayed = time.time() - self._displayed_notification
        remaining = self._current_message.timeout - time_displayed
        remaining_pc = ( remaining / self._current_message.timeout ) * 100.0
        return remaining_pc
        
    def _get_page(self, id):
        sequence_number = self._service.GetPageSequenceNumber(id)    
        if sequence_number != 0:    
            return self._bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Page%d' % sequence_number)
    
    def _notify(self):
        if len(self._message_queue) != 0:   
            message = self._message_queue[0] 
                
            # Which theme variant should we use
            self._last_variant = ""
            if message.body == None or message.body == "":
                self._last_variant = "nobody"
                
            self._current_message = message
    
            # Get the page
             
            if self._page == None:
                page_sequence_number = self._service.CreatePage("NotifyLCD", "Notification Message", g15screen.PRI_HIGH)
                self._page = self._bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Page%d' % page_sequence_number)
                self._reload_theme()
            else:
                self._reload_theme()
                self._page.Raise()
                
            self._page.SetThemeProperties(self._get_properties())
            self._start_timer(message)
            self._do_redraw()
            
            # Play sound
            if self._get_enable_sounds() and "sound-file" in message.hints and ( not "suppress-sound" in message.hints or not message.hints["suppress-sound"]):
                print "WARNING: Will play sound",message.hints["sound-file"] 
                os.system("aplay '%s' &" % message.hints["sound-file"])
                
            if self._gconf_client.get_bool(self._gconf_key + "/blink_keyboard"):
                delay = gconf_client.get(gconf_key + "/blink_delay")
                blink_delay = delay.get_int() if delay != None else 500
                self._driver.BlinkKeyboard(float(blink_delay) / 1000.0, 3.0, [])
            if self._gconf_client.get_bool(self._gconf_key + "/change_keyboard_color"):
                color = gconf_client.get_string(gconf_key + "/color")
                self._driver.BlinkKeyboard(0.0, 3.0, (128, 128, 128) if color == None else g15util.to_rgb(color))
                
    def _do_redraw(self):
        if self._page != None:
            self._do_draw()
            self._page.SetThemeProperty("remaining", str(self._get_remaining()))
            self._redraw_timer = g15util.schedule("Notification", 0.1, self._do_redraw)
            
    def _do_draw(self):        
        if self._page != None:
            self._page.SetThemeProperties(self._get_properties())
            self._page.Redraw()
            
    def _cancel_redraw(self):
        if self._redraw_timer != None:
            self._redraw_timer.cancel()
          
    def _cancel_timer(self):
        if self._timer != None:
            self._timer.cancel()
        
    def _move_to_next(self, reason = NOTIFICATION_DISMISSED):  
        self._cancel_redraw()      
        message = self._message_queue[0]
        message.close()
        del self._message_queue[0]
        del self._message_map[message.id]
        self.NotificationClosed(message.id, reason)
        if len(self._message_queue) != 0:
            self._notify()  
        else:
            logger.debug("Closing notification page")
            self._page.Destroy()
            self._page = None
                  
    def _hide_notification(self): 
        self._move_to_next(NOTIFICATION_EXPIRED)
        
    def _start_timer(self, message):
        self._cancel_timer() 
        self._displayed_notification = time.time()                       
        self._timer = g15util.schedule("Notification", message.timeout, self._hide_notification)
    
'''
Gnome15 notification plugin
'''        
class G15NotifyLCD():
    
    def __init__(self, gconf_client, gconf_key, service, driver, bus):
        self._service = service;
        self._bus = bus
        self._last_variant = None
        self._driver = driver
        
        self._gconf_key = gconf_key
        self._session_bus = dbus.SessionBus()
        self._gconf_client = gconf_client

    def activate(self):
        # Already running
        for i in range(0, 6):
            try :            
                for pn in OTHER_NOTIFY_DAEMON_PROCESS_NAMES:
                    logger.debug("Killing %s" % pn)
                    process = subprocess.Popen(['killall', '--quiet', pn])
                    process.wait()
                self._bus_name = dbus.service.BusName(IF_NAME, bus=self._bus, replace_existing=True, allow_replacement=True, do_not_queue=True)
                break
            except NameExistsException:
                time.sleep(1.0)
                if i == 2:
                    raise
                
        # Notification Service
        self._notification_service = G15NotifyService(self._gconf_client, self._gconf_key, self._service, self._driver, self._bus)        
        try :
            logger.info("Starting notification service %s" % IF_NAME)
            dbus.service.Object.__init__(self._notification_service, self._bus_name, BUS_NAME)
            logger.info("Started notification service %s" % IF_NAME)
        except KeyError:
            print "DBUS notify service failed to start. May already be started." 
            
    def deactivate(self):
        # TODO How do we properly 'unexport' a service? This seems to kind of work, in
        # that notify-osd can take over again, but trying to re-activate the plugin
        # doesn't reclaim the bus name (I think because it is cached)
        print "WARNING: Deactivated notify service. Note, currently the service cannot be reactivated once deactivated. You must completely restart Gnome15"
        self._notification_service.active = False
        self._notification_service.remove_from_connection()
        self._bus_name.__del__()
        del self._bus_name
        
    def destroy(self):
        pass 
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP:            
            page = self._screen.get_page("NotifyLCD")
            if page != None:            
                if g15driver.G_KEY_BACK in keys or g15driver.G_KEY_L3 in keys:
                    if self._notification_service != None:
                        self._notification_service.clear()
                    return True   
                if g15driver.G_KEY_RIGHT in keys or g15driver.G_KEY_L4 in keys:
                    if self._notification_service != None:
                        self._notification_service.next()
                    return True
                if g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                    if self._notification_service != None:
                        self._notification_service.action()
                    return True                     
                
# run it in a gtk window
if __name__ == "__main__":
    
    try :
        import setproctitle
        setproctitle.setproctitle(os.path.basename(os.path.abspath(sys.argv[0])))
    except:
        pass
    
    
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-l", "--log", dest="log_level", metavar="INFO,DEBUG,WARNING,ERROR,CRITICAL",
        default="warning" , help="Log level")
    (options, args) = parser.parse_args()
    
    level = logging.NOTSET
    if options.log_level != None:      
        level = LEVELS.get(options.log_level, logging.NOTSET)
        logger.setLevel(level = level)
     
    bus = dbus.SessionBus()
    try :
        screen = bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Service')
    except dbus.DBusException:
        logger.error("g15-desktop-service is not running.")
        sys.exit(0)  
        
    plugin = G15NotifyLCD(gconf.client_get_default(), 
                          "/apps/gnome15/plugins/notify-lcd2", screen, 
                          bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Driver'), bus)
    plugin.activate()
    loop.run()