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
 
import gnome15.g15screen as g15screen
import gnome15.g15util as g15util
import gnome15.g15globals as pglobals
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gconf
import time
import dbus
import dbus.service
import dbus.exceptions
import os
import gtk
import gtk.gdk
import Image
import subprocess
import traceback
import tempfile
import lxml.html
import Queue
import gobject

from threading import Timer
from threading import Thread
from threading import RLock
from dbus.exceptions import NameExistsException

# Logging
import logging
logger = logging.getLogger("notify")


# Plugin details - All of these must be provided
id="notify-lcd"
name="Notify"
description="Displays desktop notification messages on the keyboard's screen (when available), and provides " + \
            "various other methods of notification, such as blinking the keyboard backlight, " + \
            "blinking the M-Key lights, or changing the backlight colour. On some desktops, " + \
            "Gnome15 can completely take over the notification service and display messages " + \
            "on the keyboard only."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=True
single_instance=True
actions={ 
         g15driver.CLEAR : "Clear all queued messages", 
         g15driver.NEXT_SELECTION : "Next message",
         g15driver.SELECT : "Perform action (if appropriate)"
         }

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
    return G15NotifyLCD(gconf_client, gconf_key, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "notify-lcd.glade"))
    dialog = widget_tree.get_object("NotifyLCDDialog")
    dialog.set_transient_for(parent)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/respect_timeout", "RespectTimeout", False, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/allow_actions", "AllowActions", False, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/allow_cancel", "AllowCancel", False, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/on_keyboard_screen", "OnKeyboardScreen", True, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/on_desktop", "OnDesktop", False, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/blink_keyboard_backlight", "BlinkKeyboardBacklight", True, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/blink_memory_bank", "BlinkMemoryBank", True, widget_tree, True)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/change_keyboard_backlight_color", "ChangeKeyboardBacklightColor", False, widget_tree, True)
    g15util.configure_adjustment_from_gconf(gconf_client, gconf_key + "/blink_delay", "DelayAdjustment", 500, widget_tree)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/enable_sounds", "EnableSounds", True, widget_tree, True)
    g15util.configure_colorchooser_from_gconf(gconf_client, gconf_key + "/keyboard_backlight_color", "KeyboardBacklightColor", ( 128, 128, 128 ), widget_tree, None)
    
    set_available(None, widget_tree)
    widget_tree.get_object("ChangeKeyboardBacklightColor").connect("toggled", set_available, widget_tree)
    widget_tree.get_object("BlinkKeyboardBacklight").connect("toggled", set_available, widget_tree)
    
    dialog.run()
    dialog.hide()
    
def set_available(widget, widget_tree):
    widget_tree.get_object("KeyboardBacklightColor").set_sensitive(widget_tree.get_object("ChangeKeyboardBacklightColor").get_active())
    widget_tree.get_object("BlinkDelay").set_sensitive(widget_tree.get_object("BlinkKeyboardBacklight").get_active())

       
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
        
        if "image_path" in self.hints:
            self.icon = self.hints["image_path"]
            
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
                
            try :
                pixbuf = gtk.gdk.pixbuf_new_from_data(buf, gtk.gdk.COLORSPACE_RGB, has_alpha, bits_per_sample, img_width, img_height, img_stride)
                fh, self.embedded_image = tempfile.mkstemp(suffix=".png",prefix="notify-lcd")
                file = os.fdopen(fh)
                file.close()
                pixbuf.save(self.embedded_image, "png")
                self.icon = None
            except :
                # Sometimes the image data seems to be bad
                logger.warn("Failed to decode notification image")
                
            if self.embedded_image == None and ( self.icon == None or self.icon == "" ):
                self.icon = g15util.get_icon_path("dialog-information", 1024)
    
    def close(self):
        if self.embedded_image != None:
            os.remove(self.embedded_image)
   
'''
DBus service implementing the freedesktop notification specification
'''     
class G15NotifyService(dbus.service.Object):
    
    def __init__(self, gconf_client, gconf_key, screen, bus_name, plugin):
        dbus.service.Object.__init__(self, bus_name, BUS_NAME)
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._screen = screen
        self._plugin = plugin
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ( pglobals.name, "TT", pglobals.version, "1.1" ) 
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='as')
    def GetCapabilities(self):
        logger.debug("Getting capabilities")
        caps = [ "body", "body-images", "icon-static" ]
        if self._gconf_client.get_bool(self._gconf_key + "/allow_actions"):
            caps.append("actions")
        if self._plugin._get_enable_sounds():
            caps.append("sounds")
            
        logger.debug("Got capabilities %s" % str(caps))
        return caps     
    
    @dbus.service.method(IF_NAME, in_signature='susssasa{sv}i', out_signature='u')
    def Notify(self, app_name, id, icon, summary, body, actions, hints, timeout):
        return self._plugin.notify(app_name, id, icon, summary, body, actions, hints, timeout)
    
    @dbus.service.method(IF_NAME, in_signature='u', out_signature='')
    def CloseNotification(self, id):     
        logger.debug("Close notification %d" % ( id ) )   
        self._plugin.close_notification(id)
        
    @dbus.service.signal(dbus_interface=IF_NAME,
                         signature='us')
    
    def ActionInvoked(self, id, action_key):
        logger.debug("Sending ActionInvoked for %d, %s" % ( id, action_key ) )
    
    @dbus.service.signal(dbus_interface=IF_NAME,
                         signature='uu')
    def NotificationClosed(self, id, reason):
        logger.debug("Sending NotificationClosed for %d, %s" % ( id, reason ) )
    
'''
Gnome15 notification plugin
'''        
class G15NotifyLCD():
    
    def __init__(self, gconf_client,gconf_key, screen):
        self._screen = screen;
        self._gconf_key = gconf_key
        self._session_bus = dbus.SessionBus()
        self._gconf_client = gconf_client
        self._lock = RLock()
        self.id = 1
        
    def _load_configuration(self):
        self.respect_timeout = g15util.get_bool_or_default(self._gconf_client, self._gconf_key + "/respect_timeout", False)
        self.allow_actions = g15util.get_bool_or_default(self._gconf_client, self._gconf_key + "/allow_actions", False)
        self.allow_cancel = g15util.get_bool_or_default(self._gconf_client, self._gconf_key + "/allow_cancel", False)
        self.on_keyboard_screen = g15util.get_bool_or_default(self._gconf_client, self._gconf_key + "/on_keyboard_screen", True)
        self.on_desktop = g15util.get_bool_or_default(self._gconf_client, self._gconf_key + "/on_desktop", False)
        self.blink_keyboard_backlight = g15util.get_bool_or_default(self._gconf_client, self._gconf_key + "/blink_keyboard_backlight", True)
        self.blink_memory_bank = g15util.get_bool_or_default(self._gconf_client, self._gconf_key + "/blink_memory_bank", True)
        self.change_keyboard_backlight_color = g15util.get_bool_or_default(self._gconf_client, self._gconf_key + "/change_keyboard_backlight_color", False)
        self.enable_sounds = g15util.get_bool_or_default(self._gconf_client, self._gconf_key + "/enable_sounds", True)
        self.blink_delay = g15util.get_int_or_default(self._gconf_client, self._gconf_key + "/blink_delay", 500)
        self.keyboard_backlight_color  = g15util.get_rgb_or_default(self._gconf_client, self._gconf_key + "/keyboard_backlight_color", ( 128, 128, 128 ))

    def activate(self):
        self._last_variant = None
        self._displayed_notification = 0
        self._active = True
        self._timer = None
        self._redraw_timer = None
        self._blink_thread = None
        self._control_values = []
        self._message_queue = []
        self._message_map = {}
        self._current_message = None
        self._service = None
        self._bus = dbus.SessionBus()
        self._load_configuration()
        self._notify_handle = None
        self._page = None
        
        if not self.on_desktop:        
            # Already running
            for i in range(0, 6):
                try :            
                    for pn in OTHER_NOTIFY_DAEMON_PROCESS_NAMES:
                        process = subprocess.Popen(['killall', '--quiet', pn])
                        process.wait()
                    self._bus_name = dbus.service.BusName(IF_NAME, bus=self._bus, replace_existing=True, allow_replacement=True, do_not_queue=True)
                    break
                except NameExistsException:
                    time.sleep(1.0)
                    if i == 2:
                        raise
            
            try :
            	self._service = G15NotifyService(self._gconf_client, self._gconf_key, self._screen, self._bus_name, self)
            except KeyError:
                logger.error("DBUS notify service failed to start. May already be started.")
            
        if not self._service:
            # Just monitor raw DBUS events
            self._bus.add_match_string_non_blocking("interface='org.freedesktop.Notifications'")
            self._bus.add_message_filter(self.msg_cb)
            
        self._screen.action_listeners.append(self)
        self._notify_handle = self._gconf_client.notify_add(self._gconf_key, self._configuration_changed)
            
    def msg_cb(self, bus, msg):
        # Only interested in method calls
        if msg.get_type() == 1 and isinstance(msg, dbus.lowlevel.MethodCallMessage):
            if msg.get_member() == "Notify":
                self.notify(*msg.get_args_list())  
            
    def deactivate(self):
        # TODO How do we properly 'unexport' a service? This seems to kind of work, in
        # that notify-osd can take over again, but trying to re-activate the plugin
        # doesn't reclaim the bus name (I think because it is cached)
        if self._notify_handle:
            self._gconf_client.notify_remove(self._notify_handle)
        self._screen.action_listeners.remove(self)
        if self._service:
            if not self._screen.service.shutting_down:
                logger.warn("Deactivated notify service. Currently the service cannot be reactivated once deactivated. You must completely restart Gnome15")
            self._service.active = False
            self._service.remove_from_connection()
            self._bus_name.__del__()
            del self._bus_name
        else:
            # Stop monitoring DBUS
            self._bus.remove_match_string("interface='org.freedesktop.Notifications'")
            self._bus.remove_message_filter(self.msg_cb)
        
    def destroy(self):
        pass 
                    
    def action_performed(self, binding):            
        if self._page != None and self._page.is_visible():            
            if binding.action == g15driver.CLEAR:
                self.clear()  
            elif binding.action == g15driver.NEXT_PAGE:
                self.next()  
            elif binding.action == g15driver.SELECT:
                self.action()
    
    def notify(self, app_name, id, icon, summary, body, actions, hints, timeout):
        logger.info("Notify app=%s id=%s '%s' {%s}", app_name, id, summary, hints)
        try :                
            if self._active:
                timeout = float(timeout) / 1000.0
                if not self.respect_timeout:
                    timeout = 10.0                
                if not self._service or not self.allow_actions:
                    actions = None
                
                # Check if this notification should be ignored, currently we ignore
                # volume change notifications
                if "x-canonical-private-synchronous" in hints and hints["x-canonical-private-synchronous"] == "volume":
                    return
                    
                # Strip markup
                if body:
                    body = g15util.strip_tags(body) 
                if summary:
                    summary  = g15util.strip_tags(summary)
                
                # If a message with this ID is already queued, replace it's details
                if id in self._message_map:
                    logger.debug("Message %s is already in queue, replacing its details" % str(id))
                    message = self._message_map[id]
                    message.set_details(icon, summary, body, timeout, actions, hints) 
                    
                    # If this message is the visible one, then reset the timer
                    if message == self._message_queue[0]:
                        logger.debug("It is the visible message")
                        self._start_timer(message)
                    else:            
                        if self._page != None:
                            self._screen.redraw(self._page)
                else:
                    # Otherwise queue a new message
                    logger.debug("Queuing new message")
                    message = G15Message(self.id, icon, summary, body, timeout, actions, hints)
                    self._message_queue.append(message)
                    self._message_map[self.id] = message                
                    self.id += 1
                    
                    if len(self._message_queue) == 1:
                        self._notify()
                    else:    
                        logger.debug("More than one message in queue, just redrawing")                           
                        if self._page != None:
                            self._screen.redraw(self._page)
                return message.id                         
        except Exception as blah:
            traceback.print_exc()
    
    def close_notification(self, id):        
        logger.info("Closing notification " % id)
        self._lock.acquire()
        try :
            if self.allow_cancel and len(self._message_queue) > 0:
                message = self._message_queue[0]
                if message.id == id:
                    self._cancel_timer()
                    self._move_to_next(NOTIFICATION_CLOSED)
                else:
                    del self._message_map[id]
                    for m in self._message_queue:
                        if m.id == id:
                            self._message_queue.remove(m)
                            if self._service:
                                gobject.idle_add(self._service.NotificationClosed, id, NOTIFICATION_CLOSED)
                            break
        finally :
            self._lock.release()
        
    def clear(self):
        self._lock.acquire()
        try :
            for message in self._message_queue:
                message.close()
            self._message_queue = []
            self._message_map = {}
            self._cancel_timer()
            if self._page != None:
                self._screen.del_page(self._page)  
        finally:
            self._lock.release()
    
    def next(self):
        logger.debug("User is selected next")
        self._cancel_timer()
        self._move_to_next()
    
    def action(self):
        self._cancel_timer()
        if len(self._message_queue) > 0:
            message = self._message_queue[0]
            action = message.actions[0]
            if self._service:
                logger.debug("Action invoked")
                self._service.ActionInvoked(message.id, action[0])
            self._move_to_next()
      
    ''' 
    Private
    '''     
    def _configuration_changed(self, client, connection_id, entry, args):
        self._load_configuration()
          
    def _get_theme_properties(self):
        width_available = self._screen.width
        properties = {}  
        properties["title"] = self._current_message.summary
        properties["message"] = self._current_message.body
        if self._current_message.icon != None and len(self._current_message.icon) > 0:
            icon_path = g15util.get_icon_path(self._current_message.icon)
            
            # Workaround on Natty missing new email notification icon (from Evolution)?
            if icon_path == None and self._current_message.icon == "notification-message-email":
                icon_path = g15util.get_icon_path([ "applications-email-pane", "mail_new", "mail-inbox", "evolution-mail" ])
                
            properties["icon"] = icon_path 
        elif self._current_message.embedded_image != None:
            properties["icon"] = self._current_message.embedded_image            
        if not "icon" in properties or properties["icon"] == None:
            properties["icon"] = g15util.get_icon_path(["dialog-info", "stock_dialog-info", "messagebox_info" ])
                    
        properties["next"] = len(self._message_queue) > 1
        action = 1
        for a in self._current_message.actions:
            properties["action%d" % action] = a[1] 
            action += 1
        if len(self._current_message.actions) > 0:        
            properties["action"] = True
            
        time_displayed = time.time() - self._displayed_notification
        remaining = self._current_message.timeout - time_displayed
        remaining_pc = ( remaining / self._current_message.timeout ) * 100.0
        properties["remaining"] = int(remaining_pc) 
        return properties
    
    def _page_deleted(self):
        self._page = None

    def _notify(self):
        if len(self._message_queue) != 0:            
            logger.debug("Displaying first message in queue of %d" % len(self._message_queue))   
            message = self._message_queue[0] 
            
                
            # Which theme variant should we use
            self._last_variant = ""
            if message.body == None or message.body == "":
                self._last_variant = "nobody"
                
            self._current_message = message
    
            # Get the page
             
            if self._page == None:            
                logger.debug("Creating new notification message page")
                self._control_values = []
                for c in self._screen.driver.get_controls():
                    if c.hint & g15driver.HINT_DIMMABLE != 0:
                        self._control_values.append(c.value)
                        
                if self._screen.driver.get_bpp() != 0:
                    logger.debug("Creating notification message page")
                    self._page = g15theme.G15Page(id, self._screen, priority=g15screen.PRI_HIGH, title = name, \
                                                  theme_properties_callback = self._get_theme_properties, \
                                                  theme = g15theme.G15Theme(self, self._last_variant))
                    self._page.on_deleted = self._page_deleted
                    self._screen.add_page(self._page)
            else:
                logger.debug("Raising notification message page")
                self._page.set_theme(g15theme.G15Theme(self, self._last_variant))
                self._screen.raise_page(self._page)
                
            self._start_timer(message)         
            self._do_redraw()
            
            # Play sound
            if self.enable_sounds and "sound-file" in message.hints and ( not "suppress-sound" in message.hints or not message.hints["suppress-sound"]):
                logger.debug("Will play sound",message.hints["sound-file"]) 
                os.system("aplay '%s' &" % message.hints["sound-file"])
                
            control = self._screen.driver.get_control_for_hint(g15driver.HINT_DIMMABLE)
            if control and self.blink_keyboard_backlight:
                acquired_control = self._screen.driver.acquire_control(control, release_after = 3.0, val = self.keyboard_backlight_color if self.change_keyboard_backlight_color else control.value)
                acquired_control.blink(delay = self.blink_delay / 1000.0)
            elif control and self.change_keyboard_backlight_color:                
                acquired_control = self._screen.driver.acquire_control(control, release_after = 3.0, val = self.keyboard_backlight_color)
                
            if self.blink_memory_bank:
                acquired_control = self._screen.driver.acquire_mkey_lights(release_after = 3.0, val = g15driver.MKEY_LIGHT_1 | g15driver.MKEY_LIGHT_2 | g15driver.MKEY_LIGHT_3 | g15driver.MKEY_LIGHT_MR)
                acquired_control.blink(delay = self.blink_delay / 1000.0)
                
                
    def _do_redraw(self):
        if self._page != None:
            self._screen.redraw(self._page)
            self._redraw_timer = g15util.schedule("Notification", self._screen.service.animation_delay, self._do_redraw)
          
    def _cancel_redraw(self):
        if self._redraw_timer != None:
            self._redraw_timer.cancel()
          
    def _cancel_timer(self):
        if self._timer != None:
            self._timer.cancel()
        
    def _move_to_next(self, reason = NOTIFICATION_DISMISSED):
        logger.debug("Dismissing current message. Reason code %d", reason)  
        self._lock.acquire()
        try :      
            if len(self._message_queue) > 0:
                message = self._message_queue[0]
                message.close()
                del self._message_queue[0]
                del self._message_map[message.id]
                if self._service:
                    self._service.NotificationClosed(message.id, reason)
            if len(self._message_queue) != 0:
                self._notify()  
            else:
                self._screen.del_page(self._page)
                self._page = None
        finally:
            self._lock.release()
                  
    def _hide_notification(self): 
        logger.debug("Hiding notification")
        self._move_to_next(NOTIFICATION_EXPIRED)
        
    def _start_timer(self, message):
        logger.debug("Starting hide timeout")
        self._cancel_timer() 
        self._displayed_notification = time.time()                       
        self._timer = g15util.schedule("Notification", message.timeout, self._hide_notification)
                   
