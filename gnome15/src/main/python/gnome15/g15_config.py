#!/usr/bin/env python
############################################################################
##
## Copyright (C), all rights reserved:
##      2010 Brett Smith <tanktarta@blueyonder.co.uk>
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License version 2
##
## Graphics Tablet Applet
##
############################################################################

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import dbus
import os
import sys
import g15_globals as pglobals
import g15_setup as g15setup
import g15_profile as g15profile
import gconf
import g15_plugins as g15plugins
import g15_driver as g15driver
import g15_driver_manager as g15drivermanager
import g15_util as g15util
import subprocess
import shutil
import logging
logger = logging.getLogger("config")

# Determine if appindicator is available, this decides that nature
# of the message displayed when the Gnome15 service is not running
HAS_APPINDICATOR=False
try :
    import appindicator
    appindicator.__path__
    HAS_APPINDICATOR=True
except:
    pass

# Store the temporary profile icons here (for when the icon comes from a window, the filename is not known
icons_dir = os.path.join(os.path.join(os.path.expanduser("~"),".gnome15"),"profile-icons")
if not os.path.exists(icons_dir):
    os.makedirs(icons_dir)

PALE_RED = gtk.gdk.Color(213, 65, 54)


BUS_NAME="org.gnome15.Configuration"
NAME="/org/gnome15/Config"
IF_NAME="org.gnome15.Config"

class G15ConfigService(dbus.service.Object):
    
    def __init__(self, bus, window):
        bus_name = dbus.service.BusName(BUS_NAME, bus=bus, replace_existing=False, allow_replacement=False, do_not_queue=True)
        dbus.service.Object.__init__(self, bus_name, NAME)
        self.window = window
        
    @dbus.service.method(IF_NAME, in_signature='', out_signature='')
    def Present(self):
        self.window.present()

class G15Config:
    
    adjusting = False
    
    ''' GUI for configuring Logitech "G" Keyboards, Gamepads and Speakers.
    '''
    def __init__(self, parent_window=None, service=None):
        self.parent_window = parent_window
        
        self._signal_handles = []
        self.notify_handles = []
        self.control_notify_handles = []
        self.plugin_key = "/apps/gnome15/plugins"
        self.selected_id = None
        self.service = service
        self.conf_client = gconf.client_get_default()
        
        # Load main Glade file
        g15Config = os.path.join(pglobals.glade_dir, 'g15-config.glade')        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(g15Config)
        self.main_window = self.widget_tree.get_object("MainWindow")
        
        # Make sure there is only one g15config running
        self.session_bus = dbus.SessionBus()
        try :
            G15ConfigService(self.session_bus, self.main_window)
        except dbus.exceptions.NameExistsException:
            self.session_bus.get_object(BUS_NAME, NAME).Present()
            sys.exit(0)

        # Widgets
        self.site_label = self.widget_tree.get_object("SiteLabel")
        self.cycle_screens = self.widget_tree.get_object("CycleScreens")
        self.cycle_screens_options = self.widget_tree.get_object("CycleScreensOptions")
        self.cycle_seconds = self.widget_tree.get_object("CycleAdjustment")
        self.cycle_seconds_widget = self.widget_tree.get_object("CycleSeconds")
        self.plugin_model = self.widget_tree.get_object("PluginModel")
        self.plugin_tree = self.widget_tree.get_object("PluginTree")
        self.driver_button = self.widget_tree.get_object("DriverButton")
        self.plugin_enabled_renderer = self.widget_tree.get_object("PluginEnabledRenderer")
        self.main_vbox = self.widget_tree.get_object("MainVBox")
        self.profiles_tree = self.widget_tree.get_object("ProfilesTree")
        self.profileNameColumn = self.widget_tree.get_object("ProfileName")
        self.keyNameColumn = self.widget_tree.get_object("KeyName")
        self.macroNameColumn = self.widget_tree.get_object("MacroName")
        self.macro_list = self.widget_tree.get_object("MacroList")
        self.application = self.widget_tree.get_object("ApplicationLocation")
        self.m1 = self.widget_tree.get_object("M1") 
        self.m2 = self.widget_tree.get_object("M2") 
        self.m3 = self.widget_tree.get_object("M3")
        self.window_model = self.widget_tree.get_object("WindowModel")
        self.window_combo = self.widget_tree.get_object("WindowCombo")
        self.remove_button = self.widget_tree.get_object("RemoveButton")
        self.activate_on_focus = self.widget_tree.get_object("ActivateProfileOnFocusCheckbox")
        self.macro_name_renderer = self.widget_tree.get_object("MacroNameRenderer")
        self.window_label = self.widget_tree.get_object("WindowLabel")
        self.activate_by_default = self.widget_tree.get_object("ActivateByDefaultCheckbox")
        self.send_delays = self.widget_tree.get_object("SendDelaysCheckbox")
        self.profile_icon = self.widget_tree.get_object("ProfileIcon")
        self.icon_browse_button = self.widget_tree.get_object("BrowseForIcon")
        self.clear_icon_button = self.widget_tree.get_object("ClearIcon")
        self.macro_properties_button = self.widget_tree.get_object("MacroPropertiesButton")
        self.delete_macro_button = self.widget_tree.get_object("DeleteMacroButton")
        self.memory_bank_label = self.widget_tree.get_object("MemoryBankLabel")
        self.macro_keys_label = self.widget_tree.get_object("MacroKeysLabel")
        self.macro_name_field = self.widget_tree.get_object("MacroNameField")
        self.script_model = self.widget_tree.get_object("ScriptModel")
        self.script_label = self.widget_tree.get_object("ScriptLabel")
        self.memory_bank_vbox = self.widget_tree.get_object("MemoryBankVBox")      
        self.macrosModel = self.widget_tree.get_object("MacroModel")
        self.profiles_model = self.widget_tree.get_object("ProfileModel")
        
        # Window 
        self.main_window.set_transient_for(self.parent_window)
        self.main_window.set_icon_from_file(g15util.get_icon_path("gnome15"))
        
        # Monitor gconf
        self.conf_client.add_dir("/apps/gnome15", gconf.CLIENT_PRELOAD_NONE)
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/cycle_seconds", self.cycle_seconds_configuration_changed));
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/cycle_screens", self.cycle_screens_configuration_changed));
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/plugins", self.plugins_changed))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/active_profile", self.active_profile_changed))
        
        # Monitor macro profiles changing
        g15profile.profile_listeners.append(self.profiles_changed)
        
        # Get current state        
        self.selected_profile = g15profile.get_active_profile() 
        
        # Configure widgets    
        self.profiles_tree.get_selection().set_mode(gtk.SELECTION_SINGLE)        
        self.macro_list.get_selection().set_mode(gtk.SELECTION_SINGLE)   

        # Indicator options        
        if HAS_APPINDICATOR:  
            self.notify_handles.append(g15util.configure_checkbox_from_gconf(self.conf_client, "/apps/gnome15/indicate_only_on_error", "OnlyShowIndicatorOnError", False, self.widget_tree, True))
        else:
            self.widget_tree.get_object("OnlyShowIndicatorOnError").destroy()
        
        # Bind to events
        self.cycle_seconds.connect("value-changed", self.cycle_seconds_changed)
        self.cycle_screens.connect("toggled", self.cycle_screens_changed)
        self.site_label.connect("activate", self.open_site)
        self.plugin_tree.connect("cursor-changed", self.select_plugin)
        self.plugin_enabled_renderer.connect("toggled", self.toggle_plugin)
        self.widget_tree.get_object("PreferencesButton").connect("clicked", self.show_preferences)
        self.widget_tree.get_object("DriverButton").connect("clicked", self.show_setup)
        self.widget_tree.get_object("AddButton").connect("clicked", self.add_profile)
        self.widget_tree.get_object("ActivateButton").connect("clicked", self.activate)
        self.activate_on_focus.connect("toggled", self.activate_on_focus_changed)
        self.activate_by_default.connect("toggled", self.activate_on_focus_changed)
        self.clear_icon_button.connect("clicked", self.clear_icon)
        self.delete_macro_button.connect("clicked", self.remove_macro)
        self.icon_browse_button.connect("clicked", self.browse_for_icon)
        self.macro_properties_button.connect("clicked", self.macro_properties)
        self.macro_list.connect("cursor-changed", self.select_macro)
        self.macro_name_renderer.connect("edited", self.macro_name_edited)
        self.m1.connect("toggled", self.memory_changed)
        self.m2.connect("toggled", self.memory_changed)
        self.m3.connect("toggled", self.memory_changed)
        self.profiles_tree.connect("cursor-changed", self.select_profile)
        self.remove_button.connect("clicked", self.remove_profile)
        self.send_delays.connect("toggled", self.send_delays_changed)
        self.window_combo.child.connect("changed", self.window_name_changed)
        self.window_combo.connect("changed", self.window_name_changed)
        
        # Add the custom controls
        self._add_controls()
        
        # Populate model and configure other components
        self.load_model()
        self.set_cycle_seconds_value_from_configuration()
        self.set_cycle_screens_value_from_configuration()
        
        # If the keyboard has a colour dimmer, allow colours to be assigned to memory banks
        control = self.driver.get_control_for_hint(g15driver.HINT_DIMMABLE)
        if control != None and not isinstance(control.value, int):
            hbox = gtk.HBox()
            self.enable_color_for_m_key = gtk.CheckButton("Set backlight colour")
            self.enable_color_for_m_key.connect("toggled", self._color_for_mkey_enabled)
            hbox.pack_start(self.enable_color_for_m_key, True, False)            
            self.color_button = gtk.ColorButton()
            self.color_button.set_sensitive(False)                
            self.color_button.connect("color-set", self._profile_color_changed)
#            color_button.set_color(self.to_color(control.value))
            hbox.pack_start(self.color_button, True, False)
            self.memory_bank_vbox.add(hbox)
            hbox.show_all()
        else:
            self.color_button = None
            self.enable_color_for_m_key = None
        
        # Connection to BAMF for running applications list
        try :
            self.bamf_matcher = self.session_bus.get_object("org.ayatana.bamf", '/org/ayatana/bamf/matcher')
        except:
            logger.warning("BAMF not available, falling back to WNCK")
            self.bamf_matcher = None
        
        # See if the Gnome15 service is running
        self.infobar = gtk.InfoBar()       
        content = self.infobar.get_content_area()
        self.warning_label = gtk.Label()
        self.warning_image = gtk.Image()  
        content.pack_start(self.warning_image, False, False)
        content.pack_start(self.warning_label, True, True)
        self.start_button = None

        self.start_button = gtk.Button("Start Service")
        self.start_button.connect("clicked", self.start_service)
        content.pack_start(self.start_button, False, False)  
        self.start_button.show()         
        self.main_vbox.pack_start(self.infobar, True, True)
        self.warning_box_shown = False
        self.infobar.hide_all()
        
        self.gnome15_service = None

        # Watch for Gnome15 starting and stopping
        try :
            self._connect()
        except dbus.exceptions.DBusException:
            self._disconnect()
        self.session_bus.add_signal_receiver(self._name_owner_changed,
                                     dbus_interface='org.freedesktop.DBus',
                                     signal_name='NameOwnerChanged')  
        
    def _name_owner_changed(self, name, old_owner, new_owner):
        if name == "org.gnome15.Gnome15":
            if old_owner == "":
                self._connect()
            else:
                self._disconnect()
        
    def __del__(self):
        for h in self.notify_handles:
            self.conf_client.notify_remove(h)
            
    def _disconnect(self):
        self.show_message(gtk.MESSAGE_WARNING, "The Gnome15 desktop service is not running. It is recommended " + \
                                  "you add <b>g15-desktop-service</b> as a <i>Startup Application</i>.")
        for sig in self._signal_handles:
            self.session_bus.remove_signal_receiver(sig)
        self._signal_handles = []
        
    def _connect(self):
        self.gnome15_service = self.session_bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Service')
        self.driver_service =  self.session_bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Driver')
        self._status_change()
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._status_change, dbus_interface="org.gnome15.Service", signal_name='StartingUp'))
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._status_change, dbus_interface="org.gnome15.Service", signal_name='StartedUp'))
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._status_change, dbus_interface="org.gnome15.Service", signal_name='ShuttingDown'))  
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._status_change, dbus_interface="org.gnome15.Service", signal_name='ShuttingDown'))  
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._status_change, dbus_interface="org.gnome15.Driver", signal_name='Connected'))  
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._status_change, dbus_interface="org.gnome15.Driver", signal_name='Disconnected'))
        
    def _status_change(self):
        if self.gnome15_service.IsStartingUp():            
            self.show_message(gtk.MESSAGE_WARNING, "The Gnome15 desktop service is starting up. Please wait", False)
        elif self.gnome15_service.IsShuttingDown():            
            self.show_message(gtk.MESSAGE_WARNING, "The Gnome15 desktop service is shutting down.", False)
        else:
            if not self.driver_service.IsConnected():
                self.show_message(gtk.MESSAGE_WARNING, "The Gnome15 desktop service is running, but failed to connect " + \
                                  "to the keyboard driver. The error message given was <b>%s</b>" % self.gnome15_service.GetLastError(), False)
            else:
                self.hide_warning()
        
        
    def hide_warning(self):
        if self.warning_box_shown == None or self.warning_box_shown:
            self.warning_box_shown = False    
            self.infobar.hide_all()
            self.main_window.check_resize()
        
    def start_service(self, widget):
        widget.set_sensitive(False)
        g15util.run_script("g15-desktop-service", ["-f"])
    
    def show_message(self, type, text, start_service_button = True):
        self.infobar.set_message_type(type)
        if self.start_button != None:
            self.start_button.set_sensitive(True)
            self.start_button.set_visible(start_service_button)
        self.warning_label.set_text(text)
        self.warning_label.set_use_markup(True)
        self.warning_label.set_line_wrap(True)
        self.warning_label.set_alignment(0.0, 0.5)

        if type == gtk.MESSAGE_WARNING:
            self.warning_image.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)
            self.warning_label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.Color(0, 0, 0))
        
        self.main_window.check_resize()        
        self.infobar.show_all()
        if self.start_button != None and not start_service_button:
            self.start_button.hide()
        self.warning_box_shown = True
        
    def open_site(self, widget):
        subprocess.Popen(['xdg-open',widget.get_uri()])
        
    def color_from_gconf_value(self, id):
        entry = self.conf_client.get("/apps/gnome15/" + id)
        if entry == None:
            return self.to_color((0,0,0))
        else:            
            return self.to_color(self.to_rgb(entry.get_string()))
        
    def to_rgb(self, string_rgb):
        rgb = string_rgb.split(",")
        return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        
    def to_color(self, rgb):
        return gtk.gdk.Color(rgb[0] <<8, rgb[1] <<8,rgb[2] <<8)
        
    def color_changed(self, widget, control, i):
        if i == None:
            col = widget.get_color()     
            i = ( col.red >> 8, col.green >> 8, col.blue >> 8 )
        self.conf_client.set_string("/apps/gnome15/" + control.id, "%d,%d,%d" % ( i[0],i[1],i[2]))
        
    def control_changed(self, widget, control):
        if control.hint & g15driver.HINT_SWITCH != 0:
            val = 0
            if widget.get_active():
                val = 1
            self.conf_client.set_int("/apps/gnome15/" + control.id, val)
        else:
            self.conf_client.set_int("/apps/gnome15/" + control.id, int(widget.get_value()))
        
    def show_setup(self, widget):        
        setup = g15setup.G15Setup(None, False, False)
        setup.setup()
        self._add_controls()
        self.load_model()
    
    def show_preferences(self, widget):
        plugin = self.get_selected_plugin()
        plugin.show_preferences(self.main_window, self.conf_client, self.plugin_key + "/" + plugin.id)
        
    def load_model(self):
        self.plugin_model.clear()
        for mod in sorted(g15plugins.imported_plugins, key=lambda key: key.name):
            key = self.plugin_key + "/" + mod.id + "/enabled"
            if self.driver.get_model_name() in g15plugins.get_supported_models(mod):
                enabled = self.conf_client.get_bool(key)
                self.plugin_model.append([enabled, mod.name, mod.id])
                if mod.id == self.selected_id:
                    self.plugin_tree.get_selection().select_path(self.plugin_model.get_path(self.plugin_model.get_iter(len(self.plugin_model) - 1)))
        if len(self.plugin_model) > 0 and self.get_selected_plugin() == None:            
            self.plugin_tree.get_selection().select_path(self.plugin_model.get_path(self.plugin_model.get_iter(0)))            
            
        self.select_plugin(None)
        
    def get_index_for_plugin_id(self, id):
        idx = 0
        for row in self.plugin_model:
            if row[2] == id:
                return idx
            idx = idx + 1
        return -1
            
    def get_row_for_plugin_id(self, id):
        for row in self.plugin_model:
            if row[2] == id:
                return row
        
    def get_selected_plugin(self):
        (model, path) = self.plugin_tree.get_selection().get_selected()
        if path != None:
            return g15plugins.get_module_for_id(model[path][2])
            
    def toggle_plugin(self, widget, path):
        plugin = g15plugins.get_module_for_id(self.plugin_model[path][2])
        if plugin != None:
            key = self.plugin_key + "/" + plugin.id + "/enabled"
            self.conf_client.set_bool(key, not self.conf_client.get_bool(key))
            
    def select_plugin(self, widget):       
        plugin = self.get_selected_plugin()
        if plugin != None:
            self.selected_id = plugin.id
            self.widget_tree.get_object("PluginNameLabel").set_text(plugin.name)
            self.widget_tree.get_object("DescriptionLabel").set_text(plugin.description)
            self.widget_tree.get_object("DescriptionLabel").set_use_markup(True)
            self.widget_tree.get_object("AuthorLabel").set_text(plugin.author)
            self.widget_tree.get_object("SupportedLabel").set_text(", ".join(g15plugins.get_supported_models(plugin)).upper())
            self.widget_tree.get_object("CopyrightLabel").set_text(plugin.copyright)
            self.widget_tree.get_object("SiteLabel").set_uri(plugin.site)
            self.widget_tree.get_object("SiteLabel").set_label(plugin.site)
            self.widget_tree.get_object("PreferencesButton").set_sensitive(plugin.has_preferences)
            self.widget_tree.get_object("PluginDetails").set_visible(True)
        else:
            self.widget_tree.get_object("PluginDetails").set_visible(False)

    def set_cycle_seconds_value_from_configuration(self):
        val = self.conf_client.get("/apps/gnome15/cycle_seconds")
        time = 10
        if val != None:
            time = val.get_int()
        if time != self.cycle_seconds.get_value():
            self.cycle_seconds.set_value(time)
            
    def set_cycle_screens_value_from_configuration(self):
        val = self.conf_client.get_bool("/apps/gnome15/cycle_screens")
        self.cycle_seconds_widget.set_sensitive(val)
        if val != self.cycle_screens.get_active():
            self.cycle_screens.set_active(val)
            
    def control_configuration_changed(self, client, connection_id, entry, args):
        widget = args[1]
        control = args[0]
        if isinstance(control.value, int):
            if control.hint & g15driver.HINT_SWITCH != 0:
                widget.set_active(entry.value.get_int() == 1)
            else:
                widget.set_value(entry.value.get_int())
        else:
            widget.set_color(self.to_color(self.to_rgb(entry.value.get_string())))

    def cycle_screens_configuration_changed(self, client, connection_id, entry, args):
        self.set_cycle_screens_value_from_configuration()
        
    def cycle_seconds_configuration_changed(self, client, connection_id, entry, args):
        self.set_cycle_seconds_value_from_configuration()
        
    def plugins_changed(self, client, connection_id, entry, args):
        self.load_model()
        
    def cycle_screens_changed(self, widget=None):
        self.conf_client.set_bool("/apps/gnome15/cycle_screens", self.cycle_screens.get_active())
        
    def cycle_seconds_changed(self, widget):
        val = int(self.cycle_seconds.get_value())
        self.conf_client.set_int("/apps/gnome15/cycle_seconds", val)
        
    def run(self):
        ''' Set up everything and display the window
        '''
        self.id = None                
        self.load_configurations()         
        self.main_window.run()
        self.main_window.hide()
        g15profile.notifier.stop()
        
    def create_color_icon(self, color):
        draw = gtk.Image()
        pixmap = gtk.gdk.Pixmap(None, 16, 16, 24)
        cr = pixmap.cairo_create()
        cr.set_source_rgb(float(color[0]) / 255.0, float(color[1]) / 255.0, float(color[2]) / 255.0)
        cr.rectangle(0, 0, 16, 16)
        cr.fill()
        draw.set_from_pixmap(pixmap, None)
        return draw
    
    def active_profile_changed(self, client, connection_id, entry, args):
        self.load_configurations()
        
    def send_delays_changed(self, widget=None):
        self.selected_profile.send_delays = self.send_delays.get_active()
        self.selected_profile.save()
        
    def activate_on_focus_changed(self, widget=None):
        self.selected_profile.activate_on_focus = widget.get_active()        
        self.window_combo.set_sensitive(self.selected_profile.activate_on_focus)
        self.selected_profile.save()
        
    def window_name_changed(self, widget):
        if isinstance(widget, gtk.ComboBoxEntry):
            active = widget.get_active()
            if active >= 0:
                self.window_combo.child.set_text(self.window_model[active][0])
        else:
            if widget.get_text() != self.selected_profile.window_name: 
                self.selected_profile.window_name = widget.get_text()
                if self.bamf_matcher != None:
                    for window in self.bamf_matcher.RunningApplications():
                        app = self.session_bus.get_object("org.ayatana.bamf", window)
                        view = dbus.Interface(app, 'org.ayatana.bamf.view')
                        if view.Name() == self.selected_profile.window_name:
                            icon = view.Icon()
                            if icon != None:
                                icon_path = g15util.get_icon_path(icon)
                                if icon_path != None:
                                    # We need to copy the icon as it may be temporary
                                    copy_path = os.path.join(icons_dir, os.path.basename(icon_path))
                                    shutil.copy(icon_path, copy_path)
                                    self.selected_profile.icon = copy_path
                else:                    
                    import wnck           
                    for window in wnck.screen_get_default().get_windows():
                        if window.get_name() == self.selected_profile.window_name:
                            icon = window.get_icon()
                            if icon != None:
                                filename = os.path.join(icons_dir,"%d.png" % self.selected_profile.id)
                                icon.save(filename, "png")
                                self.selected_profile.icon = filename    
                            
                self.selected_profile.save()
        
    def memory_changed(self, widget):
        self.load_configuration(self.selected_profile)
        
    def select_profile(self, widget):
        (model, path) = self.profiles_tree.get_selection().get_selected()
        self.selected_profile = g15profile.get_profile(model[path][2])
        self.load_configuration(self.selected_profile)
        
    def select_macro(self, widget):
        self.set_available_actions()
        
    def set_available_actions(self):
        (model, path) = self.macro_list.get_selection().get_selected()
        self.delete_macro_button.set_sensitive(path != None)
        self.macro_properties_button.set_sensitive(path != None)
        
    def activate(self, widget):
        (model, path) = self.profiles_tree.get_selection().get_selected()
        self.make_active(g15profile.get_profile(model[path][2]))
        
    def make_active(self, profile): 
        profile.make_active()
        self.load_configurations()
        
    def clear_icon(self, widget):
        self.selected_profile.icon = ""            
        self.selected_profile.save()
        
    def browse_for_icon(self, widget):
        dialog = gtk.FileChooserDialog("Open..",
                               None,
                               gtk.FILE_CHOOSER_ACTION_OPEN,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_transient_for(self.main_window)
        dialog.set_filename(self.selected_profile.icon)
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        
        dialog.add_filter(filter)
        
        filter = gtk.FileFilter()
        filter.set_name("Images")
        filter.add_mime_type("image/png")
        filter.add_mime_type("image/jpeg")
        filter.add_mime_type("image/gif")
        filter.add_pattern("*.png")
        filter.add_pattern("*.jpg")
        filter.add_pattern("*.jpeg")
        filter.add_pattern("*.gif")
        dialog.add_filter(filter)
        
        response = dialog.run()
        
        if response == gtk.RESPONSE_OK:
            self.selected_profile.icon = dialog.get_filename()            
            self.selected_profile.save()
            
        dialog.destroy()
        
    def remove_profile(self, widget):
        dialog = self.widget_tree.get_object("ConfirmRemoveProfileDialog")  
        dialog.set_transient_for(self.main_window)
        response = dialog.run()
        dialog.hide()
        if response == 1:
            active_profile = g15profile.get_active_profile()
            if self.selected_profile.id == active_profile.id:
                self.make_active(g15profile.get_profile(0))
            self.selected_profile.delete()
            self.load_configurations()
        
    def macro_properties(self, widget):
        memory = self.get_memory_number()
        (model, path) = self.macro_list.get_selection().get_selected()
        key_list_key = model[path][2]
        macro = self.selected_profile.get_macro(memory, g15profile.get_keys_from_key(key_list_key))
        dialog = self.widget_tree.get_object("EditMacroDialog")  
        dialog.set_transient_for(self.main_window)        
        self.memory_bank_label.set_text("M%d" % memory)
        self.macro_keys_label.set_text(",".join(g15util.get_key_names(macro.keys)))
        self.macro_name_field.set_text(macro.name)
        self.script_model.clear()
        script_text = ""
        last = ""
        for line in macro.macro.split("\n"):
            args = line.split()
            self.script_model.append(args)
            if args[0] == "Release":
                if len(args[1]) == 1:
                    if len(last) > 1:
                        script_text += " "
                    script_text += args[1]
                else:
                    if not script_text.endswith(" "):
                        script_text += " "
                    script_text += args[1]
                last = args[1]
        self.script_label.set_text(script_text)
                        
        dialog.run()
        dialog.hide()
        macro.name = self.macro_name_field.get_text()
        self.load_configurations()
        
    def remove_macro(self, widget):
        memory = self.get_memory_number()
        (model, path) = self.macro_list.get_selection().get_selected()
        key_list_key = model[path][2]
        dialog = self.widget_tree.get_object("ConfirmRemoveMacroDialog") 
        dialog.set_transient_for(self.main_window)
        response = dialog.run()
        dialog.hide()
        if response == 1:
            keys = g15profile.get_keys_from_key(key_list_key)
            self.selected_profile.delete_macro(memory, keys)
            self.load_configurations()
        
    def add_profile(self, widget):
        dialog = self.widget_tree.get_object("AddProfileDialog") 
        dialog.set_transient_for(self.main_window) 
        response = dialog.run()
        dialog.hide()
        if response == 1:
            new_profile_name = self.widget_tree.get_object("NewProfileName").get_text()
            new_profile = g15profile.G15Profile(-1)
            new_profile.name = new_profile_name
            g15profile.create_profile(new_profile)
            self.selected_profile = new_profile
            self.load_configurations()
        
    def get_memory_number(self):
        if self.m1.get_active():
            return 1
        elif self.m2.get_active():
            return 2
        elif self.m3.get_active():
            return 3
        
    def load_configurations(self):
        self.profiles_model.clear()
        tree_selection = self.profiles_tree.get_selection()
        active = g15profile.get_active_profile()
        active_id = -1
        if active != None:
            active_id = active.id
        current_selection = self.selected_profile
        self.selected_profile = None
        self.profiles = g15profile.get_profiles()
        for profile in self.profiles: 
            weight = 400
            if profile.id == active_id:
                weight = 700
            self.profiles_model.append([profile.name, weight, profile.id])
            if current_selection != None and profile.id == current_selection.id:
                tree_selection.select_path(self.profiles_model.get_path(self.profiles_model.get_iter(len(self.profiles_model) - 1)))
                self.selected_profile = profile
        if self.selected_profile != None:                             
            self.load_configuration(self.selected_profile)             
        elif len(self.profiles) > 0:            
            tree_selection.select_path(self.profiles_model.get_path(self.profiles_model.get_iter(0)))
        else:
            default_profile = g15profile.G15Profile("Default")
            g15profile.create_profile(default_profile)
            self.load_configurations()
            
        
    def profiles_changed(self, macro_profile_id):        
        gobject.idle_add(self.load_configurations)
        
    def macro_name_edited(self, widget, row, value):
        macro = self.get_sorted_list()[int(row)] 
        if value != macro.name:
            macro.name = value
            macro.save()
            self.load_configuration(self.selected_profile)
        
    def get_sorted_list(self):
        return sorted(self.selected_profile.macros[self.get_memory_number() - 1], key=lambda key: key.key_list_key)
        
    def load_configuration(self, profile): 
        name = profile.window_name
        if name == None:
            name = ""            
        self.macrosModel.clear()
        for macro in self.get_sorted_list():
            self.macrosModel.append([", ".join(g15util.get_key_names(macro.keys)), macro.name, macro.key_list_key, True])
        self.activate_on_focus.set_active(profile.activate_on_focus)
        self.activate_by_default.set_active(profile.activate_on_focus)
        if profile.window_name != None:
            self.window_combo.child.set_text(profile.window_name)
        else:
            self.window_combo.child.set_text("")
        self.send_delays.set_active(profile.send_delays)
        self.window_combo.set_sensitive(self.activate_on_focus.get_active())
        
        if profile.icon == None or profile.icon == "":
            self.profile_icon.set_from_stock(gtk.STOCK_MISSING_IMAGE, gtk.ICON_SIZE_DIALOG)
        else:
            self.profile_icon.set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(profile.icon, 48, 48))
        
        if profile.get_default():
            self.window_combo.set_visible(False)
            self.activate_on_focus.set_visible(False)
            self.window_label.set_visible(False)
            self.activate_by_default.set_visible(True)
            self.remove_button.set_sensitive(False)
        else:
            self.window_combo.set_visible(True)
            self.activate_on_focus.set_visible(True)
            self.window_label.set_visible(True)
            self.activate_by_default.set_visible(False)
            self.remove_button.set_sensitive(True)
            
        if self.color_button != None:
            rgb = profile.get_mkey_color(self.get_memory_number())
            if rgb == None:
                self.enable_color_for_m_key.set_active(False)
                self.color_button.set_sensitive(False)
                self.color_button.set_color(g15util.to_color((255, 255, 255)))
            else:
                self.color_button.set_sensitive(True)
                self.color_button.set_color(g15util.to_color(rgb))
                self.enable_color_for_m_key.set_active(True)
            
        self.load_windows()
        self.set_available_actions()
            
    def load_windows(self):        
        self.window_model.clear()
        if self.bamf_matcher != None:            
            for window in self.bamf_matcher.RunningApplications():
                app = self.session_bus.get_object("org.ayatana.bamf", window)
                view = dbus.Interface(app, 'org.ayatana.bamf.view')
                self.window_model.append([view.Name(), window])
        else:
            import wnck
            for window in wnck.screen_get_default().get_windows():
                self.window_model.append([window.get_name(), window.get_name()])
        
    def _add_controls(self):
                
        # Remove previous notify handles
        for nh in self.control_notify_handles:
            self.conf_client.notify_remove(nh)            
        
        # Driver. We only need this to get the controls. Perhaps they should be moved out of the driver
        # class and the values stored separately
        self.driver = g15drivermanager.get_driver(self.conf_client)
        
        # Controls
        driver_controls = self.driver.get_controls()
        
        # Slider and Color controls
        controls = self.widget_tree.get_object("ControlsBox")
        for c in controls.get_children():
            controls.remove(c)            
        table = gtk.Table(rows = len(driver_controls), columns = 2)
        table.set_row_spacings(4)
        row = 0
        for control in driver_controls:
            val = control.value
            if isinstance(val, int):  
                if control.hint & g15driver.HINT_SWITCH == 0:
                    label = gtk.Label(control.name)
                    label.set_alignment(0.0, 0.5)
                    label.show()
                    table.attach(label, 0, 1, row, row + 1,  xoptions = gtk.FILL, xpadding = 8, ypadding = 4);
                    
                    hscale = gtk.HScale()
                    hscale.set_value_pos(gtk.POS_RIGHT)
                    hscale.set_digits(0)
                    hscale.set_range(control.lower,control.upper)
                    hscale.set_value(control.value)
                    hscale.connect("value-changed", self.control_changed, control)
                    hscale.show()
                    
                    table.attach(hscale, 1, 2, row, row + 1, xoptions = gtk.EXPAND | gtk.FILL);                
                    self.conf_client.notify_add("/apps/gnome15/" + control.id, self.control_configuration_changed, [ control, hscale ]);
            else:  
                label = gtk.Label(control.name)
                label.set_alignment(0.0, 0.5)
                label.show()
                table.attach(label, 0, 1, row, row + 1,  xoptions = gtk.FILL, xpadding = 8, ypadding = 4);
                
                hbox = gtk.Toolbar()
                hbox.set_style(gtk.TOOLBAR_ICONS)
                for i in [(0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255) ]:
                    button = gtk.Button()
                    button.set_image(self.create_color_icon(i))
#                    button.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(i[0] <<8,i[1]  <<8,i[2]  <<8))
#                    button.modify_bg(gtk.STATE_PRELIGHT, gtk.gdk.Color(i[0] <<8,i[1]  <<8,i[2]  <<8))
                    button.connect("clicked", self.color_changed, control, i)
                    hbox.add(button)
                    button.show()
                color_button = gtk.ColorButton()
                
                color_button.connect("color-set", self.color_changed, control, None)
                color_button.show()
                color_button.set_color(self.to_color(control.value))
                hbox.add(color_button)
                self.control_notify_handles.append(self.conf_client.notify_add("/apps/gnome15/" + control.id, self.control_configuration_changed, [ control, color_button]));
                
                hbox.show()
                table.attach(hbox, 1, 2, row, row + 1);
                
            row += 1
        controls.add(table)
          
        # Switch controls  
        controls = self.widget_tree.get_object("SwitchesBox")
        for c in controls.get_children():
            controls.remove(c)
        table.set_row_spacings(4)
        row = 0
        for control in driver_controls:
            val = control.value
            if isinstance(val, int):  
                if control.hint & g15driver.HINT_SWITCH != 0:
                    check_button = gtk.CheckButton(control.name)
                    check_button.set_alignment(0.0, 0.0)
                    check_button.show()
                    controls.pack_start(check_button, False, False, 4)  
                    check_button.connect("toggled", self.control_changed, control)
                    self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/" + control.id, self.control_configuration_changed, [ control, check_button ]));
                    row += 1
        
        # Show everything
        self.main_window.show_all()
        
        if self.driver.get_bpp() == 0:            
            self.cycle_screens.hide()
            self.cycle_screens_options.hide()
            
        if row == 0:
            self.widget_tree.get_object("SwitchesFrame").hide() 
            
    def _profile_color_changed(self, widget):
        self.selected_profile.set_mkey_color(self.get_memory_number(), 
                                             g15util.color_to_rgb(widget.get_color()) if self.enable_color_for_m_key.get_active() else None)
        self.selected_profile.save()
    
    def _color_for_mkey_enabled(self, widget):
        self.color_button.set_sensitive(widget.get_active())        
        self._profile_color_changed(self.color_button)