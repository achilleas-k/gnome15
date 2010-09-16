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
import pynotify
import g15_draw as g15draw
import g15_profile as g15profile
import g15_daemon as g15daemon
import g15_config as g15config
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

dbus_loop=DBusGMainLoop()
dbus.set_default_main_loop(dbus_loop)

# Determine whether to use XTest for sending key events to X

UseXTest = True
try :
    import Xlib.ext.xtest
except ImportError:
    UseXTest = False
     
local_dpy = display.Display()
record_dpy = display.Display()
window = local_dpy.get_input_focus()._data["focus"];

if UseXTest and not local_dpy.query_extension("XTEST") :
    UseXTest = False
    
NAME="Gnome15"
VERSION="0.0.1"

class RecordThread(Thread):
    def __init__(self, plugin):
        Thread.__init__(self)
        self.setDaemon(True)
        self.name = "RecordThread"
        self.plugin = plugin  
        self.ctx = record_dpy.record_create_context(
                                0,
                                [record.AllClients],
                                [{
                                  'core_requests': (0, 0),
                                  'core_replies': (0, 0),
                                  'ext_requests': (0, 0, 0, 0),
                                  'ext_replies': (0, 0, 0, 0),
                                  'delivered_events': (0, 0),
                                  'device_events': (X.KeyPress, X.MotionNotify),
                                  'errors': (0, 0),
                                  'client_started': False,
                                  'client_died': False,
                                  }])

    def disable_record_context(self):
        if self.ctx != None:            
            local_dpy.record_disable_context(self.ctx)
            local_dpy.flush()
        
    def run(self):      
        record_dpy.record_enable_context(self.ctx, self.plugin.record_callback)
        record_dpy.record_free_context(self.ctx)

class G15Applet(gnomeapplet.Applet):
    
    def __init__(self, applet, iid, parent_window=None):
        self.__gobject_init__()
        
        self.parent_window = parent_window
        self.applet = applet
        self.record_thread = None
        self.active_window = None
        self.timeout_interval = 1000
        self.verbs = [ ( "Props", self.properties ), ( "About", self.about_info ), ("Plugins", self.show_plugins) ]
        self.activate_notify = None
        self.cycle_timer = None
        self.keyboard_backlight = -1
        self.propxml="""
        <popup name="button3">
        <menuitem name="Item 1" verb="Props" label="_Preferences..." pixtype="stock" pixname="gtk-properties"/>
        <menuitem name="Item 2" verb="Plugins" label="Plugins"/>
        <menuitem name="Item 3" verb="About" label="_About..." pixtype="stock" pixname="gnome-stock-about"/>
        </popup>
        """
        
        # Key macro recording
        self.recording_canvas = None
        self.record_key = None
        self.key_down = None
        self.key_field = None
        
        # Load main Glade file
        g15Config = os.path.join(pglobals.glade_dir, 'g15-config.glade')        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(g15Config)
        self.key_field = self.widget_tree.get_object("MacroScript")
#        self.macro_dialog = self.widget_tree.get_object("MacroScriptDialog")
#        self.macro_dialog.set_transient_for(self.parent_window)
        self.script_model = self.widget_tree.get_object("ScriptModel")
        
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
        self.logo_pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(pglobals.image_dir,'g15key.png'))
        self.image = gtk.Image()
        self.size_changed() 
        self.box.add(self.image)
        
        # Monitor gconf and configure keyboard based on values
        self.conf_client = gconf.client_get_default()
        self.conf_client.add_dir("/apps/gnome15", gconf.CLIENT_PRELOAD_NONE)
        self.conf_client.notify_add("/apps/gnome15/keyboard_backlight", self.keyboard_backlight_configuration_changed);
        self.conf_client.notify_add("/apps/gnome15/cycle_screens", self.check_cycle);
        self.conf_client.notify_add("/apps/gnome15/active_profile", self.active_profile_changed);
        self.conf_client.notify_add("/apps/gnome15/profiles", self.profiles_changed);
        
        # Enabled notifications
        pynotify.init("G15 Applet")
             
        # update info from filesystem
        gobject.timeout_add(self.timeout_interval,self.timeout_callback, self)
        
        # Start a client that handles keystrokes
        self.driver = g15daemon.G15Daemon()
        self.set_keyboard_backlight_from_configuration()
        
        # Connect some events   
        self.widget_tree.get_object("CancelMacroButton").connect("clicked", self.cancel_macro)
        self.applet.connect("button-press-event",self.button_clicked)
        self.applet.connect("delete-event",self.cleanup)
        self.applet.connect("change-orient",self.change_orientation)
        self.applet.connect("change-size",self.size_changed)
        self.applet.connect("change-background",self.background_changed)
        self.applet.connect("scroll-event",self.applet_scroll)
#        self.macro_dialog.connect("delete-event", self.cancel_macro)
        
        # Create the screen
        self.screen = g15screen.G15Screen(self.driver)
        self.screen.set_mkey(1)
        self.activate_profile() 
        
        # Start all plugins
        self.plugins = g15plugins.G15Plugins(self.screen)
        self.plugins.start()
        self.plugins.activate()
        
        self.applet.show_all()
        
        # Now start listening for key events and cycle the screen if required
        self.driver.grab_keyboard(self.key_received)
        self.check_cycle()
        
    def __del__(self):
        if self.record_thread != None:
            self.record_thread.disable_record_context()
        if self.plugins.get_active():
            self.plugins.deactivate()
        if self.plugins.get_started():
            self.plugins.destroy()
        del self.key_screen
        del self.driver
        
    def check_cycle(self, client=None, connection_id=None, entry=None, args=None):
        active = self.conf_client.get_bool("/apps/gnome15/cycle_screens")
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
        self.cycle_timer = Timer(time, self.screen_cycle, ())
        self.cycle_timer.name = "CycleTimer"
        self.cycle_timer.start()
            
    def screen_cycle(self):
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
            backlight = self.conf_client.get_int("/apps/gnome15/keyboard_backlight")
            backlight -= 1
            if backlight < 0:
                backlight = 2
            self.conf_client.set_int("/apps/gnome15/keyboard_backlight", backlight)
        elif direction == gtk.gdk.SCROLL_RIGHT:            
            backlight = self.conf_client.get_int("/apps/gnome15/keyboard_backlight")
            backlight += 1
            if backlight > 2:
                backlight = 0
            self.conf_client.set_int("/apps/gnome15/keyboard_backlight", backlight)
        
    def background_changed(self, applet, type, color, pixmap):
        applet.set_style(None)
        rc_style = gtk.RcStyle()
        applet.modify_style(rc_style)
        if (type == gnomeapplet.COLOR_BACKGROUND):
            applet.modify_bg(gtk.STATE_NORMAL, color)
        elif (type == gnomeapplet.PIXMAP_BACKGROUND):
            style = applet.style
            style.bg_pixmap[gtk.STATE_NORMAL] = pixmap
            applet.set_style(style)  
        
    def size_changed(self, arg1=None, arg2=None):
        size = int(self.applet.get_size() * 0.6)
        path = os.path.join(pglobals.image_dir,'g15key.png')
        pixbuf = gtk.gdk.pixbuf_new_from_file(path)
        pixbuf = pixbuf.scale_simple(32, 32, gtk.gdk.INTERP_BILINEAR);
        self.image.set_from_pixbuf(pixbuf)
        
    def profiles_changed(self, client, connection_id, entry, args):
        pass
        
    def redraw_screen(self):
        self.recording_canvas.clear()
        self.recording_canvas.set_font_size(g15draw.FONT_TINY)
        active_profile = g15profile.get_active_profile()  
        self.recording_canvas.fill_box((0, 0, self.driver.get_size()[0], 10), "Black")      
        self.recording_canvas.draw_text(active_profile.name, (g15draw.CENTER, 2), color="White")
        
        if len(self.script_model) == 0:            
            self.recording_canvas.draw_text("RECORDING M" + str(self.screen.get_mkey()), (g15draw.CENTER, 16))
            self.recording_canvas.draw_text("Type macro, then press special", (g15draw.CENTER, 24))
            self.recording_canvas.draw_text("key to assign. MR to cancel.", (g15draw.CENTER, 32))
        else:
            y = 10
            for i in range(len(self.script_model) - 1, -1, -1):
                self.recording_canvas.draw_text(self.script_model[i][0] + " " + self.script_model[i][1], (g15draw.CENTER, y))
                y += 8
                if y > ( self.screen.driver.get_size()[1] - 8 ):
                    break 
            
        self.screen.draw_current_canvas()
        
    def key_received(self, key, state):
        if self.screen.handle_key(key, state, post=False) or self.plugins.handle_key(key, state, post=False):
            return        
        
        if state == g15driver.KEY_STATE_UP:
            if key & g15driver.G15_KEY_LIGHT != 0:
                self.keyboard_backlight = self.keyboard_backlight + 1
                if self.keyboard_backlight == 3:
                    self.keyboard_backlight = 0
                self.conf_client.set_int("/apps/gnome15/keyboard_backlight", self.keyboard_backlight)
            # Memory keys
            elif key & g15driver.G15_KEY_M1 != 0:
                self.screen.set_mkey(1)
                if self.recording_canvas != None:
                    self.redraw_screen()
            elif key & g15driver.G15_KEY_M2 != 0:
                self.screen.set_mkey(2)
                if self.recording_canvas != None:
                    self.redraw_screen()
            elif key & g15driver.G15_KEY_M3 != 0:
                self.screen.set_mkey(3)
                if self.recording_canvas != None:
                    self.redraw_screen()
            # Set recording
            elif key & g15driver.G15_KEY_MR != 0:              
                if self.record_thread != None:
                    self.cancel_macro(None)
                else:
                    self.recording_canvas = self.screen.new_canvas(g15screen.PRI_HIGH)
                    self.redraw_screen()
                    self.screen.draw_current_canvas()                                        
                    self.script_model.clear()
                    
                    #Create a recording context; we only want key and mouse events
                    self.record_thread = RecordThread(self)
                    self.record_thread.start()    
#                    gobject.idle_add(self.macro_dialog.show)
            else:
                self.last_key = key                    
                if self.record_thread != None:
                    self.record_key = g15util.get_key_names(key)
                    self.done_recording()
                else:
                    profile = g15profile.get_active_profile()
                    if profile != None:
                        macro = profile.get_macro(self.screen.get_mkey(), key)
                        if macro != None:
                            self.send_macro(macro)
                            
        self.screen.handle_key(key, state, post=True) or self.plugins.handle_key(key, state, post=True)
                            
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

       
                    
    def set_keyboard_backlight_from_configuration(self):
        backlight = self.conf_client.get_int("/apps/gnome15/keyboard_backlight")
        if backlight != self.keyboard_backlight:
            self.driver.set_keyboard_backlight(backlight)
        self.keyboard_backlight = backlight
        
    def keyboard_backlight_configuration_changed(self, client, connection_id, entry, args):
        self.set_keyboard_backlight_from_configuration()
        
    def timeout_callback(self,event=None):
        # Get the currently active window
        try:
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
        
        if self.activate_notify != None:
            self.activate_notify.close()
            
        if profile != None:
            self.activate_notify = pynotify.Notification("G15", "Current macro profile changed to " + profile.name)
            self.activate_notify.set_urgency(pynotify.URGENCY_CRITICAL)
            self.activate_notify.set_timeout(10000) # 10 seconds - Ignored now
            self.activate_notify.set_category("device")
            self.activate_notify.set_icon_from_pixbuf(self.logo_pixbuf)
            self.activate_notify.show()
    
    def deactivate_profile(self):
        self.screen.set_mkey(0)
        n = pynotify.Notification("G15", "Macros disabled")
        n.set_urgency(pynotify.URGENCY_CRITICAL)
        n.set_timeout(10000) # 10 seconds
        n.set_category("device")
        n.set_icon_from_pixbuf(self.logo_pixbuf)
        n.show()
        
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
        del self.applet  
        del self.daemon

    def create_menu(self):
        self.applet.setup_menu(self.propxml,self.verbs,None)  
        
    def show_plugins(self,event,data=None):
        self.plugins.configure(self.parent_window)
        
    def properties(self,event,data=None):
        a = g15config.G15Config(self.parent_window)
        a.run() 
            
    def cancel_macro(self,event,data=None):
        self.hide_recorder()

    def hide_recorder(self):
        if self.record_thread != None:
            self.record_thread.disable_record_context()
#        self.macro_dialog.hide()
        self.key_down = None
        self.record_key = None
        self.record_thread = None
        self.redraw_screen()
        self.screen.del_canvas(self.recording_canvas)
        self.recording_canvas = None
            
    def done_recording(self):
        if self.record_key != None:     
            active_profile = g15profile.get_active_profile()
            if len(self.script_model) == 0:
                active_profile.delete_macro(self.screen.get_mkey(), self.last_key)
            else:
                key_name = ", ".join(self.record_key)
                str = ""
                for row in self.script_model:
                    if len(str) != 0:                    
                        str += "\n"
                    str += row[0] + " " + row[1]
                active_profile.create_macro(self.screen.get_mkey(), self.last_key, key_name, str)
        self.hide_recorder()     
        
    def about_info(self,event,data=None):
        about = gnome.ui.About("Gnome15",pglobals.version, "GPL",\
                               "GNOME Applet to configre a Logitech G15 keyboard",["Brett Smith <tanktarta@blueyonder.co.uk>"],\
                               ["Brett Smith <tanktarta@blueyonder.co.uk>"],"Brett Smith <tanktarta@blueyonder.co.uk>",self.logo_pixbuf)
        about.show()
        
    def button_clicked(self,widget,event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            pass
        
    def button_press(self,widget,event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            self.create_menu()
            
    def lookup_keysym(self, keysym):
        for name in dir(XK):
                if name[:3] == "XK_" and getattr(XK, name) == keysym:
                    return name[3:]
        return "[%d]" % keysym
    
    def record_callback(self, reply):
        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            return
        if not len(reply.data) or ord(reply.data[0]) < 2:
            # not an event
            return
        
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, record_dpy.display, None, None)
            if event.type in [X.KeyPress, X.KeyRelease]:
                pr = event.type == X.KeyPress and "Press" or "Release"
                delay = 0
                if self.key_down == None:
                    self.key_down = time.time()
                else :
                    now = time.time()
                    delay = time.time() - self.key_down
                    self.script_model.append(["Delay", str(int(delay * 1000))])
                    self.key_down = now
                
                keysym = local_dpy.keycode_to_keysym(event.detail, 0)
                if not keysym:
                    self.script_model.append([pr, event.detail])
                else:
                    self.script_model.append([pr, self.lookup_keysym(keysym)])
                self.redraw_screen()

gobject.type_register(G15Applet)
