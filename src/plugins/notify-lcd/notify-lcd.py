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
 
import gnome15.g15_daemon as g15daemon
import gnome15.g15_draw as g15draw
import gnome15.g15_screen as g15screen
import gnome15.g15_globals as pglobals
import time
import dbus
import dbus.service
import dbus.exceptions
import os
import xdg.IconTheme as icons
import xdg.Config as config
import gtk
import Image
import subprocess
import traceback
from threading import Timer
from threading import Thread
from dbus.exceptions import NameExistsException

# Plugin details - All of these must be provided
id="notify-lcd"
name="Notify"
description="Take over as the Notification daemon\nand display messages on the LCD"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://localhost"
has_preferences=True

IF_NAME="org.freedesktop.Notifications"
BUS_NAME="/org/freedesktop/Notifications"

def create(gconf_key, gconf_client, screen):
    return G15NotifyLCD(gconf_client, gconf_key, screen)

class BlinkThread(Thread):
    def __init__(self, gconf_client):
        Thread.__init__(self)
        self.gconf_client = gconf_client
    
    def run(self):
        backlight = self.gconf_client.get_int("/apps/gnome15/keyboard_backlight")
        for i in range(1, 5):
            for v in [0,1,2,1]:
                self.gconf_client.set_int("/apps/gnome15/keyboard_backlight", v)
                time.sleep(0.1)              
        self.gconf_client.set_int("/apps/gnome15/keyboard_backlight", backlight)
        
            

class G15NotifyLCD(dbus.service.Object):
    
    def __init__(self, gconf_client,gconf_key, screen):
        self.screen = screen;
        self.gconf_key = gconf_key
        self.timer = None
        self.session_bus = dbus.SessionBus()
        self.gconf_client = gconf_client

    def activate(self):
        self.id = 0
        try:
            bus_name = dbus.service.BusName(IF_NAME, bus=dbus.SessionBus(), replace_existing=True, allow_replacement=True, do_not_queue=True)
        except NameExistsException:
            # Already running            
            process = subprocess.Popen(['killall','notify-osd'])
            process.wait()
            print "Killing previous notification daemon"
            bus_name = dbus.service.BusName(IF_NAME, bus=dbus.SessionBus(), replace_existing=True, allow_replacement=True, do_not_queue=True)
            
        dbus.service.Object.__init__(self, bus_name, BUS_NAME)     
    
    def deactivate(self):
        pass      
        
    def destroy(self):
        pass 
    
    def show_preferences(self, parent):
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "notify-lcd.glade"))
        
        dialog = widget_tree.get_object("NotifyLCDDialog")
        dialog.set_transient_for(parent)
        
        blink_keyboard_on_alert = widget_tree.get_object("BlinkKeyboardOnAlert")
        blink_keyboard_on_alert.set_active(self.gconf_client.get_bool(self.gconf_key + "/blink_keyboard_on_alert"))
        blink_keyboard_on_alert.connect("toggled", self.changed, self.gconf_key + "/blink_keyboard_on_alert")
        
        dialog.run()
        dialog.hide()
    
    def changed(self, widget, key):
        self.gconf_client.set_bool(key, widget.get_active())
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ( pglobals.name, "TT", pglobals.version, "1.1" ) 
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='as')
    def GetCapabilities(self):
        return [ "body", "body-images", "icon-static"]
    
    @dbus.service.method(IF_NAME, in_signature='susssasa{sv}i', out_signature='u')
    def Notify(self, app_name, id, icon, summary, body, actions, hints, timeout):
        print app_name,str(id),icon,summary,body,actions, hints, timeout
        try :
            self.notify(icon, summary, body, float(timeout) / 1000.0)
        except Exception as blah:
            traceback.print_exc()
        if id == 0:
            self.id += 1
            return self.id
        else:
            return id
    
    @dbus.service.method(IF_NAME, in_signature='u', out_signature='')
    def CloseNotification(self, id):
        print "Closing",id
        self.NotificationClosed(id, 0)
        
    @dbus.service.signal(dbus_interface=IF_NAME, signature='uu')
    def NotificationClosed(self, id, reason):
        print "Signal",id,reason

    def notify(self, icon, summary, body, timeout):
        
        if self.gconf_client.get_bool(self.gconf_key + "/blink_keyboard_on_alert"):
            BlinkThread(self.gconf_client).start()
        
        canvas = self.screen.get_canvas("NotifyLCD")
        
        if timeout <= 0.0:
            timeout = 10.0
            
        if canvas == None:
            canvas = self.screen.new_canvas(priority=g15screen.PRI_HIGH, id="NotifyLCD")
            self.hide_timer = self.screen.hide_after(timeout, canvas)
        else:
            self.hide_timer.cancel()
            self.hime_timer = self.screen.set_priority(canvas, g15screen.PRI_HIGH, hide_after = timeout)

        if summary == None:
            summary = "None"
            
        icon_theme = self.gconf_client.get_string("/desktop/gnome/interface/icon_theme")        
        canvas.clear()
        
        width_available = self.screen.driver.get_size()[0]
        if icon != None and len(icon) > 0:
            real_icon_file = icons.getIconPath(icon, theme=icon_theme, size = 32)
            if real_icon_file != None:
                width_available -= 45
                if real_icon_file.endswith(".svg"):
                    pixbuf = gtk.gdk.pixbuf_new_from_file(real_icon_file)
                    image = Image.fromstring("RGBA", (pixbuf.get_width(), pixbuf.get_height()), pixbuf.get_pixels())  
                    canvas.draw_image(image, (self.screen.driver.get_size()[0] - 40, g15draw.CENTER), (40, 40), mask=True)
                else:              
                    canvas.draw_image_from_file(real_icon_file, (self.screen.driver.get_size()[0] - 40, g15draw.CENTER), (40, 40))
        
        canvas.set_font_size(g15draw.FONT_SMALL)
        canvas.draw_text(summary, (0, 2), emboss="White", wrap=False)
        canvas.set_font_size(g15draw.FONT_TINY)
        canvas.draw_text(body, (0, 14, width_available, self.screen.driver.get_size()[1] - 14), emboss="White", wrap=True)        
            
        self.screen.draw_current_canvas()