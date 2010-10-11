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
 
import sys
import pygtk
import asyncore
pygtk.require('2.0')
import gtk
import gtk.glade
import gnomeapplet 
import gnome.ui
import os.path
import re
import gobject
import g15_globals as pglobals
import g15_screen as g15screen
import g15_driver as g15driver
import getopt
import optparse
import wnck
import subprocess
import g15_profile as g15profile
import g15_config as g15config
import g15_macros as g15macros
import g15_theme as g15theme
import traceback
import gconf
import sys
import os
import g15_util as g15util
from threading import Thread
from threading import Timer
from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.protocol import rq
import imp
import time
import g15_plugins as g15plugins
import dbus, dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from g15_exceptions import NotConnectedException

dbus_loop=DBusGMainLoop()
dbus.set_default_main_loop(dbus_loop)

# Determine whether to use XTest for sending key events to X

UseXTest = True
try :
    import Xlib.ext.xtest
except ImportError:
    UseXTest = False
     
local_dpy = display.Display()
window = local_dpy.get_input_focus()._data["focus"];

if UseXTest and not local_dpy.query_extension("XTEST") :
    UseXTest = False
    
NAME="Gnome15"
VERSION=pglobals.version

COLOURS = [(0,0,0), (255, 0, 0),(0, 255, 0),(0, 0, 255),(255, 255, 0), (255, 0, 255), (0, 255, 255), (255, 255, 255)]

class G15Splash():
    
    def __init__(self, screen):
        self.screen = screen        
        self.progress = 0.0
        self.theme = g15theme.G15Theme(pglobals.image_dir, self.screen, "background")
        self.page = self.screen.new_page(self.paint, priority=g15screen.PRI_EXCLUSIVE, id="Splash")
        self.screen.redraw(self.page)
        
    def paint(self, canvas):
        properties = {
                      "version": VERSION,
                      "progress": self.progress
                      }
        self.theme.draw(canvas, properties)
        
    def complete(self):
        self.progress = 100
        self.screen.redraw(self.page)
        self.screen.set_priority(self.page, g15screen.PRI_LOW)
        
    def update_splash(self, value, max):
        self.progress = ( float(value) / float(max) ) * 100.0
        self.screen.redraw(self.page)

class G15Applet(gnomeapplet.Applet):
    
    def __init__(self, applet, iid, parent_window=None, configure = False):
        self.__gobject_init__()
        
        self.parent_window = parent_window
        self.applet = applet
        self.applet_icon = 'g15key.png'
        self.active_window = None
        self.color_no = 1
        self.timeout_interval = 1000
        self.verbs = [ ( "Props", self.properties ), ( "Macros", self.macros ), ( "About", self.about_info ) ]
        self.cycle_timer = None
        self.shutting_down = False
        self.propxml="""
        <popup name="button3">
        <menuitem name="Item 1" verb="Props" label="_Preferences..." pixtype="stock" pixname="gtk-properties"/>
        <menuitem name="Item 2" verb="Macros" label="Macros" pixtype="stock" pixname="input-keyboard"/>
        <menuitem name="Item 3" verb="About" label="_About..." pixtype="stock" pixname="gnome-stock-about"/>
        </popup>
        """
        
        # Key macro recording
        self.defeat_profile_change = False
        
        # Load main Glade file
        g15Config = os.path.join(pglobals.glade_dir, 'g15-config.glade')        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(g15Config)
        
        # Post gnome initialisation
        self.orientation = self.applet.get_orient()
        
        # Containers
        self.container = gtk.EventBox()
        self.container.set_visible_window(False)
        self.container.connect("button-press-event",self.button_press)
        self.box = None
        if self.orientation == gnomeapplet.ORIENT_UP or self.orientation == gnomeapplet.ORIENT_DOWN:
            self.box = gtk.HBox()
        else:
            self.box = gtk.VBox()
        self.container.add(self.box)
        self.applet.add(self.container)      
        
        # Image stuff
        self.image = gtk.Image()
        self.size_changed() 
        self.box.add(self.image)
        
        # Monitor gconf and configure keyboard based on values
        self.conf_client = gconf.client_get_default()
        self.conf_client.add_dir("/apps/gnome15", gconf.CLIENT_PRELOAD_NONE)
        self.conf_client.notify_add("/apps/gnome15/cycle_screens", self.check_cycle);
        self.conf_client.notify_add("/apps/gnome15/active_profile", self.active_profile_changed);
        self.conf_client.notify_add("/apps/gnome15/profiles", self.profiles_changed);
        self.conf_client.notify_add("/apps/gnome15/driver", self.driver_changed);
        
        # update info from filesystem
        gobject.timeout_add(self.timeout_interval,self.timeout_callback, self)
        
        self.driver = g15driver.get_driver(self.conf_client, on_close = self.on_driver_close, configure = configure)
        
        # Listen for gconf events for the drivers controls
        for control in self.driver.get_controls():
            self.conf_client.notify_add("/apps/gnome15/" + control.id, self.control_configuration_changed);
        
        # Connect some events   
        self.applet.connect("button-press-event",self.button_clicked)
        self.applet.connect("destroy",self.cleanup)
#        self.applet.connect("delete-event",self.cleanup)
        self.applet.connect("change-orient",self.change_orientation)
        self.applet.connect("change-size",self.size_changed)
        self.applet.connect("change-background",self.background_changed)
        self.applet.connect("scroll-event",self.applet_scroll)
        
        # Create the screen and pluging manager
        self.screen = g15screen.G15Screen(self) 
        self.plugins = g15plugins.G15Plugins(self.screen)
        self.plugins.start()
        
        # Show the applet
        self.applet.show_all()

        # Start the driver
        self.attempt_connection() 

    def attempt_connection(self, delay = 0.0):
        if self.driver.is_connected():
            print "WARN: Attempt to reconnect when already connected."
            return
        
        if delay != 0.0:
            self.reconnect_timer = g15util.schedule("ReconnectTimer", delay, self.attempt_connection)
            return
                        
        try :
            self.driver.connect()    
            self.splash = G15Splash(self.screen)   
            self.screen.set_mkey(1)
            self.activate_profile()            
            g15util.schedule("ActivatePlugins", 0, self.complete_loading)
        except Exception as e:
            if self.process_exception(e):
                raise
            
    def process_exception(self, exception):
        self.error() 
        if self.should_reconnect(exception):
            self.reconnect_timer = g15util.schedule("ReconnectTimer", 5.0, self.attempt_connection)
        else:
            traceback.print_exc(file=sys.stderr)
            return True
            
    def should_reconnect(self, exception):
        return isinstance(exception, NotConnectedException) or ( len(exception.args) == 2 and isinstance(exception.args[0],int) and exception.args[0] in [ 111, 104 ] )
            
    def complete_loading(self):              
        try :            
            self.plugins.activate(self.splash.update_splash) 
            self.driver.grab_keyboard(self.key_received)
            self.check_cycle()
            self.applet_icon = "g15key.png"
            self.size_changed()
            self.splash.complete()
        except Exception as e:
            if self.process_exception(e):
                raise
            
    def error(self):         
        self.applet_icon = "g15key-error.png"
        self.size_changed()

    def on_driver_close(self):
        if not self.shutting_down:
            self.error()
            self.plugins.deactivate()
            self.check_cycle()
            self.attempt_connection(delay = 5.0)
        
    def __del__(self):
        if self.plugins.get_active():
            self.plugins.deactivate()
        if self.plugins.get_started():
            self.plugins.destroy()
        del self.key_screen
        del self.driver
        
    def check_cycle(self, client=None, connection_id=None, entry=None, args=None):
        active = self.driver.is_connected() and self.conf_client.get_bool("/apps/gnome15/cycle_screens")
        if active and self.cycle_timer == None:
            self.schedule_cycle()
        elif not active and self.cycle_timer != None:
            self.cycle_timer.cancel()
            self.cycle_timer = None
            
    def schedule_cycle(self):
        val = self.conf_client.get("/apps/gnome15/cycle_seconds")
        time = 10
        if val != None:
            time = val.get_int()
        self.cycle_timer = g15util.schedule("CycleTimer", time, self.screen_cycle)
            
    def screen_cycle(self):
        # Don't cycle while recording 
        # TODO change how this works
        if not self.defeat_profile_change:
            self.screen.cycle(1)
            self.schedule_cycle()
        
    def resched_cycle(self):        
        if self.cycle_timer != None:
            self.cycle_timer.cancel()
        self.schedule_cycle()
        
    def applet_scroll(self, widget, event):
        direction = event.direction
        if direction == gtk.gdk.SCROLL_UP:
            self.resched_cycle()
            self.screen.cycle(1)
        elif direction == gtk.gdk.SCROLL_DOWN:
            self.resched_cycle()
            self.screen.cycle(-1)
        elif direction == gtk.gdk.SCROLL_LEFT:
            first_control = self.driver.get_controls()[0]
            if len(first_control.value) > 1:
                self.cycle_color(-1, first_control)
            else:
                self.cycle_level(-1, first_control)
        elif direction == gtk.gdk.SCROLL_RIGHT:     
            first_control = self.driver.get_controls()[0]
            if len(first_control.value) > 1:
                self.cycle_color(1, first_control)
            else:
                self.cycle_level(1, first_control)
            
            
    def cycle_level(self, val, control):
        level = self.conf_client.get_int("/apps/gnome15/" + control.id)
        level += val
        if level > control.upper - 1:
            level = control.lower
        if level < control.lower - 1:
            level = control.upper
        self.conf_client.set_int("/apps/gnome15/" + control.id, level)
        
    def cycle_color(self, val, control):
        self.color_no += val
        if self.color_no < 0:
            self.color_no = len(COLOURS) -1
        if self.color_no >= len(COLOURS):
            self.color_no = 0
        color = COLOURS[self.color_no]
        self.conf_client.set_int("/apps/gnome15/" + control.id + "_red", color[0])
        self.conf_client.set_int("/apps/gnome15/" + control.id + "_green", color[1])
        self.conf_client.set_int("/apps/gnome15/" + control.id + "_blue", color[2])
        
    def background_changed(self, applet, bg_type, color, pixmap):
        rc_style = gtk.RcStyle()
        self.recreate_icon() 
        for c in [ self.applet, self.container, self.image, self.box ]:
            c.set_style(None)
            c.modify_style(rc_style)
            if bg_type == gnomeapplet.PIXMAP_BACKGROUND:
                style = self.applet.get_style()
                style.bg_pixmap[gtk.STATE_NORMAL] = pixmap
                c.set_style(style)
            if bg_type == gnomeapplet.COLOR_BACKGROUND:
                c.modify_bg(gtk.STATE_NORMAL, color)
            
        
    def size_changed(self, arg1=None, arg2=None):
        self.recreate_icon()
        
    def recreate_icon(self):        
        size = int(self.applet.get_size() * 0.68)
        path = os.path.join(pglobals.image_dir,self.applet_icon)
        pixbuf = gtk.gdk.pixbuf_new_from_file(path)
        pixbuf = pixbuf.scale_simple(size, size, gtk.gdk.INTERP_BILINEAR);
        self.image.set_from_pixbuf(pixbuf)
        
    def driver_changed(self, client, connection_id, entry, args):
        if self.driver.is_connected():
            self.driver.disconnect()
        
    def profiles_changed(self, client, connection_id, entry, args):
        pass
        
    def key_received(self, keys, state):
        if self.screen.handle_key(keys, state, post=False) or self.plugins.handle_key(keys, state, post=False):
            return        
        
        if state == g15driver.KEY_STATE_UP:
            if g15driver.G_KEY_LIGHT in keys:
                self.keyboard_backlight = self.keyboard_backlight + 1
                if self.keyboard_backlight == 3:
                    self.keyboard_backlight = 0
                self.conf_client.set_int("/apps/gnome15/keyboard_backlight", self.keyboard_backlight)

            profile = g15profile.get_active_profile()
            if profile != None:
                macro = profile.get_macro(self.screen.get_mkey(), keys)
                if macro != None:
                    self.send_macro(macro)
                            
        self.screen.handle_key(keys, state, post=True) or self.plugins.handle_key(keys, state, post=True)
        
    def send_macro(self, macro):
        macros = macro.macro.split("\n")
        for macro_text in macros:
            split = macro_text.split(" ")
            op = split[0]
            if len(split) > 1:
                val = split[1]
                if op == "Delay" and macro.profile.send_delays:
                    time.sleep(float(val) / 1000.0)
                elif op == "Press":
                    self.send_string(val, True)
                elif op == "Release":
                    self.send_string(val, False)
    
    def get_keysym(self, ch) :
        keysym = Xlib.XK.string_to_keysym(ch)
        if keysym == 0 :
            # Unfortunately, although this works to get the correct keysym
            # i.e. keysym for '#' is returned as "numbersign"
            # the subsequent display.keysym_to_keycode("numbersign") is 0.
            keysym = Xlib.XK.string_to_keysym(special_X_keysyms[ch])
        return keysym
                
    def char_to_keycode(self, ch) :
        keysym = self.get_keysym(ch)
        keycode = local_dpy.keysym_to_keycode(keysym)
        if keycode == 0 :
            print "Sorry, can't map", ch
    
        if False:
            shift_mask = Xlib.X.ShiftMask
        else :
            shift_mask = 0
    
        return keycode, shift_mask

            
    def send_string(self, ch, press) :
        keycode, shift_mask = self.char_to_keycode(ch)
        if (UseXTest) :
            if press:
                if shift_mask != 0 :
                    Xlib.ext.xtest.fake_input(local_dpy, Xlib.X.KeyPress, 50)
                Xlib.ext.xtest.fake_input(local_dpy, Xlib.X.KeyPress, keycode)
            else:
                Xlib.ext.xtest.fake_input(local_dpy, Xlib.X.KeyRelease, keycode)
                if shift_mask != 0 :
                    Xlib.ext.xtest.fake_input(local_dpy, Xlib.X.KeyRelease, 50)
                
            
        else :
            if press:
                event = Xlib.protocol.event.KeyPress(
                                                         time = int(time.time()),
                                                         root = local_dpy.screen().root,
                                                         window = window,
                                                         same_screen = 0, child = Xlib.X.NONE,
                                                         root_x = 0, root_y = 0, event_x = 0, event_y = 0,
                                                         state = shift_mask,
                                                         detail = keycode
                                                         )
                window.send_event(event, propagate = True)
            else:
                event = Xlib.protocol.event.KeyRelease(
                                                           time = int(time.time()),
                                                           root = local_dpy.screen().root,
                                                           window = window,
                                                           same_screen = 0, child = Xlib.X.NONE,
                                                           root_x = 0, root_y = 0, event_x = 0, event_y = 0,
                                                           state = shift_mask,
                                                           detail = keycode
                    )
                window.send_event(event, propagate = True)
                
        local_dpy.sync() 
             
    def control_changed(self, client, connection_id, entry, args):
        self.driver.set_controls_from_configuration(client)
        
    def control_configuration_changed(self, client, connection_id, entry, args):
        key = entry.key.split("_")
        for control in self.driver.get_controls():
            if key[0] == ( "/apps/gnome15/" + control.id ):
                if isinstance(control.value, int):
                    control.value = entry.value.get_int()
                else:
                    rgb = entry.value.get_string().split(",")
                    control.value = (int(rgb[0]),int(rgb[1]),int(rgb[2]))
                    
                # There is a bug where changing keyboard colors can crash the daemon
                # This stops is crashing the UI too
                try :
                    self.driver.update_control(control)
                except:
                    pass
                
                break
        self.screen.redraw()
        
    def set_defeat_profile_change(self, defeat):
        self.defeat_profile_change = defeat
        
    def timeout_callback(self,event=None):
        # Get the currently active window
        try:
            # Don't change profiles while recording
            if not self.defeat_profile_change:
                window = wnck.screen_get_default().get_active_window()
                choose_profile = None
                if window != None:
                    title = window.get_name()                                    
                    # Active window has changed, see if we have a profile that matches it
                    for profile in g15profile.get_profiles():
                        if not profile.get_default() and profile.activate_on_focus and len(profile.window_name) > 0 and title.lower().find(profile.window_name.lower()) != -1:
                            choose_profile = profile 
                            break
                            
                # No applicable profile found. Look for a default profile, and see if it is set to activate by default
                active_profile = g15profile.get_active_profile()
                if choose_profile == None:
                    default_profile = g15profile.get_default_profile()
                    if ( active_profile == None or active_profile.id != default_profile.id ) and default_profile.activate_on_focus:
                        default_profile.make_active()
                elif active_profile == None or choose_profile.id != active_profile.id:
                    choose_profile.make_active()
            
        except Exception as exception:
            traceback.print_exc(file=sys.stdout)
            print "Failed to activate profile for active window"
            print type(exception)
            
        gobject.timeout_add(self.timeout_interval,self.timeout_callback, self)
        
        
    def active_profile_changed(self, client, connection_id, entry, args):
        # Check if the active profile has change
        new_profile = g15profile.get_active_profile()
        if new_profile == None:
            self.deactivate_profile()
        else:
            self.activate_profile()
                
        return 1

    def activate_profile(self):
        profile = g15profile.get_active_profile()
        self.screen.set_mkey(1)
    
    def deactivate_profile(self):
        self.screen.set_mkey(0)
        
    def change_orientation(self,arg1,data):
        self.orientation = self.applet.get_orient()

        if self.orientation == gnomeapplet.ORIENT_UP or self.orientation == gnomeapplet.ORIENT_DOWN:
            tmpbox = gtk.HBox()
        else:
            tmpbox = gtk.VBox()
        
        # reparent all the hboxes to the new tmpbox
        for i in (self.box.get_children()):
            i.reparent(tmpbox)

        # now remove the link between big_evbox and the box
        self.container.remove(self.container.get_children()[0])
        self.box = tmpbox
        self.container.add(self.box)
        self.applet.show_all()
        
    def cleanup(self,event):
        self.shutting_down = True
        self.driver.disconnect()

    def create_menu(self):
        self.applet.setup_menu(self.propxml,self.verbs,None)  
        
    def properties(self,event,data=None):
        a = g15config.G15Config(self.parent_window)
        a.run() 
        
    def macros(self,event,data=None):
        a = g15macros.G15Macros(self.parent_window)
        a.run()
        
    def about_info(self,event,data=None):        
        logo_pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(pglobals.image_dir,'g15key.png'))
        about = gnome.ui.About("Gnome15",pglobals.version, "GPL",\
                               "GNOME Applet providing integration with\nthe Logitech G15 and G19 keyboards.",["Brett Smith <tanktarta@blueyonder.co.uk>"],\
                               ["Brett Smith <tanktarta@blueyonder.co.uk>"],"Brett Smith <tanktarta@blueyonder.co.uk>",logo_pixbuf)
        about.show()
        
    def button_clicked(self,widget,event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            pass
        
    def button_press(self,widget,event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            self.create_menu()

gobject.type_register(G15Applet)
