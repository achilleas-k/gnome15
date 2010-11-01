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
 
import gnome15.g15_screen as g15screen
import gnome15.g15_util as g15util
import gnome15.g15_globals as pglobals
import gnome15.g15_theme as g15theme
import gnome15.g15_driver as g15driver
import time
import dbus
import dbus.service
import dbus.exceptions
import os
import xdg.IconTheme as icons
import xdg.Config as config
import gtk
import gtk.gdk
import Image
import subprocess
import traceback
import tempfile
import lxml.html

from threading import Timer
from threading import Thread
from threading import RLock
from dbus.exceptions import NameExistsException

# Plugin details - All of these must be provided
id="notify-lcd"
name="Notify"
description="Take over as the Notification daemon and display messages on the LCD"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=True

IF_NAME="org.freedesktop.Notifications"
BUS_NAME="/org/freedesktop/Notifications"

def create(gconf_key, gconf_client, screen):
    return G15NotifyLCD(gconf_client, gconf_key, screen)

def show_preferences(parent, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "notify-lcd.glade"))
    
    dialog = widget_tree.get_object("NotifyLCDDialog")
    dialog.set_transient_for(parent)
    
    blink_keyboard_on_alert = widget_tree.get_object("BlinkKeyboardOnAlert")
    blink_keyboard_on_alert.set_active(gconf_client.get_bool(gconf_key + "/blink_keyboard_on_alert"))
    blink_keyboard_on_alert.connect("toggled", changed, gconf_key + "/blink_keyboard_on_alert", gconf_client)
    
    dialog.run()
    dialog.hide()

def changed(widget, key, gconf_client):
    gconf_client.set_bool(key, widget.get_active())
        
class BlinkThread(Thread):
    def __init__(self, gconf_client, screen, control_values):
        self.gconf_client = gconf_client
        self.screen = screen
        self.cancelled = False
        self.control_values = control_values
        Thread.__init__(self)
    
    def cancel(self):
        self.cancelled = True
        
    def run(self):
        controls = []
        for c in self.screen.driver.get_controls():
            if c.hint & g15driver.HINT_DIMMABLE != 0:
                controls.append(c)
        
        for j in range(0, 5):
            # Off
            if self.cancelled:
                break
            for c in controls:
                if isinstance(c.value,int):
                    c.value = c.lower
                else:
                    c.value = (0, 0, 0)
                self.screen.driver.update_control(c)
                
            time.sleep(0.1)
                
            # On
            for c in controls:
                if self.cancelled:
                    break
                if isinstance(c.value,int):
                    c.value = c.upper
                else:
                    c.value = (255, 255, 255)
                self.screen.driver.update_control(c)
                
            time.sleep(0.1)
            
        i = 0
        for c in controls:
            c.value = self.control_values[i]
            self.screen.driver.update_control(c)
            i += 1
        
            

class G15NotifyLCD(dbus.service.Object):
    
    def __init__(self, gconf_client,gconf_key, screen):
        self.screen = screen;
        self.last_variant = None
        self.gconf_key = gconf_key
        self.timer = None
        self.hide_timer = None
        self.session_bus = dbus.SessionBus()
        self.gconf_client = gconf_client
        self.active = False
        self.bus = None
        self.lock = RLock()
        self.blink_thread = None
        self.control_values = []

    def activate(self):
        self.id = 0
        bus = dbus.SessionBus()
        try:
            bus_name = dbus.service.BusName(IF_NAME, bus=bus, replace_existing=True, allow_replacement=True, do_not_queue=True)
        except NameExistsException:
            # Already running
            print "Killing previous notification daemon"
            
            for i in range(0, 6):
                try :            
                    process = subprocess.Popen(['killall','notify-osd'])
                    process.wait()
                    bus_name = dbus.service.BusName(IF_NAME, bus=bus, replace_existing=True, allow_replacement=True, do_not_queue=True)
                except NameExistsException:
                    time.sleep(1.0)
                    if i == 2:
                        raise
        
        try :
            dbus.service.Object.__init__(self, bus_name, BUS_NAME)
        except KeyError:
            print "DBUS notify service failed to start. May already be started."     
            
        self.active = True
    
    def deactivate(self):
        # TODO How do we 'unexport' a service?
        print "Deactivated notify service. Note, the service will not be free until applet process finishes"
        self.active = False
        
    def destroy(self):
        pass 
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP:            
            page = self.screen.get_page("NotifyLCD")
            if page != None:            
                if g15driver.G_KEY_BACK in keys or g15driver.G_KEY_L3 in keys:
                    self.screen.del_page(page)
                    return True
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ( pglobals.name, "TT", pglobals.version, "1.1" ) 
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='as')
    def GetCapabilities(self):
        return [ "body", "body-images", "icon-static"]
    
    @dbus.service.method(IF_NAME, in_signature='susssasa{sv}i', out_signature='u')
    def Notify(self, app_name, id, icon, summary, body, actions, hints, timeout):
        if self.active:
            try :
                self.notify(icon, summary, body, float(timeout) / 1000.0, actions, hints)
            except Exception as blah:
                traceback.print_exc()
            if id == 0:
                self.id += 1
                return self.id
            else:
                return id
    
    @dbus.service.method(IF_NAME, in_signature='u', out_signature='')
    def CloseNotification(self, id):
        self.NotificationClosed(id, 0)
        
    @dbus.service.signal(dbus_interface=IF_NAME, signature='uu')
    def NotificationClosed(self, id, reason):
        pass

    def notify(self, icon, summary, body, timeout, actions, hints):
        self.lock.acquire()
        print actions
        try :
            self.embedded_image = None
            if icon == None or icon == "":
                if "image_data" in hints:
                    image_struct = hints["image_data"]
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
                    icon = g15util.get_icon_path(self.gconf_client, "dialog-info", (self.screen.height, self.screen.height))
                
            
#            if timeout <= 0.0:
#                timeout = 10.0
            timeout = 10.0
                
            # Which theme variant should we use
            self.last_variant = ""
            if body == None or body == "":
                self.last_variant = "nobody"
    
            if summary == None:
                summary = "None"
                
            self.summary = summary
            
            if body != None and len(body) > 0:
                # Strip tags
                body_content = lxml.html.fromstring(body)
                self.body = body_content.text_content()
            else:
                self.body = body
            self.icon = icon
            
            # Get the page
            page = self.screen.get_page("NotifyLCD")
            if page == None:
                self.control_values = []
                for c in self.screen.driver.get_controls():
                    if c.hint & g15driver.HINT_DIMMABLE != 0:
                        self.control_values.append(c.value)
                self.reload_theme()
                page = self.screen.new_page(self.paint, priority=g15screen.PRI_HIGH, id="NotifyLCD")
                self.screen.hide_after(timeout, page)
            else:
                self.reload_theme()
                self.screen.raise_page(page)
                self.screen.hide_after(timeout, page)
            self.screen.redraw(page)
                
            if self.gconf_client.get_bool(self.gconf_key + "/blink_keyboard_on_alert"):
                self.blink_thread = BlinkThread(self.gconf_client, self.screen, list(self.control_values)).start()
        finally:
            self.lock.release()
        
    def reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen, self.last_variant)
        
    def paint(self, canvas):
        width_available = self.screen.width
        
        
        properties = {}        
        properties["title"] = self.summary
        properties["message"] = self.body
        if self.icon != None and len(self.icon) > 0:
            properties["icon"] = g15util.get_icon_path(self.gconf_client, self.icon)
        elif self.embedded_image != None:
            properties["icon"] = self.embedded_image
            
        
        self.theme.draw(canvas, properties)
            