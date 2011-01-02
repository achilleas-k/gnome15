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
import g15_globals as pglobals
import g15_setup as g15setup
import gconf
import g15_plugins as g15plugins
import g15_driver as g15driver
import g15_driver_manager as g15drivermanager
import g15_util as g15util
import subprocess


# Determine if appindicator is available, this decides that nature
# of the message displayed when the Gnome15 service is not running
HAS_APPINDICATOR=False
try :
    import appindicator
    appindicator.__path__
    HAS_APPINDICATOR=True
except:
    pass

PALE_RED = gtk.gdk.Color(213, 65, 54)

class G15Config:
    
    adjusting = False
    
    ''' GUI for configuring wacom-compatible drawing tablets.
    '''
    def __init__(self, parent_window=None, service=None):
        self.parent_window = parent_window
        
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

        # Widgets
        self.site_label = self.widget_tree.get_object("SiteLabel")
        self.main_window = self.widget_tree.get_object("MainWindow")
        self.cycle_screens = self.widget_tree.get_object("CycleScreens")
        self.cycle_screens_options = self.widget_tree.get_object("CycleScreensOptions")
        self.cycle_seconds = self.widget_tree.get_object("CycleAdjustment")
        self.cycle_seconds_widget = self.widget_tree.get_object("CycleSeconds")
        self.plugin_model = self.widget_tree.get_object("PluginModel")
        self.plugin_tree = self.widget_tree.get_object("PluginTree")
        self.driver_button = self.widget_tree.get_object("DriverButton")
        self.plugin_enabled_renderer = self.widget_tree.get_object("PluginEnabledRenderer")
        self.main_vbox = self.widget_tree.get_object("MainVBox")
        
        # Window 
        self.main_window.set_transient_for(self.parent_window)
        self.main_window.set_icon_from_file(g15util.get_app_icon(self.conf_client, "gnome15"))
        
        # Monitor gconf
        self.conf_client.add_dir("/apps/gnome15", gconf.CLIENT_PRELOAD_NONE)
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/cycle_seconds", self.cycle_seconds_configuration_changed));
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/cycle_screens", self.cycle_screens_configuration_changed));
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/plugins", self.plugins_changed));
        
        # Configure widgets        

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
        
        # Add the custom controls
        self._add_controls()
        
        # Populate model and configure other components
        self.load_model()
        self.set_cycle_seconds_value_from_configuration()
        self.set_cycle_screens_value_from_configuration()
        
        # See if the Gnome15 service is running
        self.infobar = gtk.InfoBar()       
        content = self.infobar.get_content_area()
        self.warning_label = gtk.Label()
        self.warning_image = gtk.Image()  
        content.pack_start(self.warning_image, False, False)
        content.pack_start(self.warning_label, True, True)
        self.start_button = None
        if HAS_APPINDICATOR:
            self.start_button = gtk.Button("Start Service")
            self.start_button.connect("clicked", self.start_service)
            content.pack_start(self.start_button, False, False)  
            self.start_button.show()         
        self.main_vbox.pack_start(self.infobar, True, True)
        self.warning_box_shown = False
        self.infobar.hide_all()
        
        self.gnome15_service = None
        self.check_timer = None        
        self.session_bus = dbus.SessionBus()
        self.check_service_status()
        
    def __del__(self):
        for h in self.notify_handles:
            self.conf_client.notify_remove(h)
        
    def check_service_status(self):
        if self.service == None:
            try :
                if self.gnome15_service == None:
                    self.gnome15_service = self.session_bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Service')
                self.gnome15_service.GetServerInformation()
                if not self.gnome15_service.GetDriverConnected():
                    gobject.idle_add(self.show_message, gtk.MESSAGE_WARNING, "The Gnome15 desktop service is running, but failed to connect " + \
                                      "to the keyboard driver. The error message given was <b>%s</b>" % self.gnome15_service.GetLastError(), False)
                else:
                    gobject.idle_add(self.hide_warning)
            except:
                self.gnome15_service = None
                if HAS_APPINDICATOR:
                    gobject.idle_add(self.show_message, gtk.MESSAGE_WARNING, "The Gnome15 desktop service is not running. It is recommended " + \
                                      "you add <b>g15-indicator</b> as a <i>Startup Application</i>.")                 
                else:
                    gobject.idle_add(self.show_message, gtk.MESSAGE_WARNING, "The Gnome15 desktop service is not running. It is recommended " + \
                                  "you add the <b>Gnome15 Applet</b> to a panel.")
        else:
            if self.service.driver == None or not self.service.driver.is_connected():
                gobject.idle_add(self.show_message, gtk.MESSAGE_WARNING,  ( "The Gnome15 desktop service is running, but failed to connect " + \
                                  "to the keyboard driver. The error message given was <b>%s</b>" % self.service.get_last_error() ), False)
            else:
                gobject.idle_add(self.hide_warning)
        self.check_timer = g15util.schedule("ServiceStatusCheck", 10.0, self.check_service_status)
        
    def hide_warning(self):
        if self.warning_box_shown == None or self.warning_box_shown:
            self.warning_box_shown = False    
            self.infobar.hide_all()
            self.main_window.check_resize()
        
    def start_service(self, widget):
        self.check_timer.cancel()
        widget.set_sensitive(False)
        g15util.run_script("g15-indicator")
        self.check_timer = g15util.schedule("ServiceStatusCheck", 5.0, self.check_service_status)
    
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
        ''' Set up device list and start main window app.
        '''
        self.id = None                
        self.main_window.run()
        self.main_window.hide()
        
    def create_color_icon(self, color):
        draw = gtk.Image()
        pixmap = gtk.gdk.Pixmap(None, 16, 16, 24)
        cr = pixmap.cairo_create()
        cr.set_source_rgb(float(color[0]) / 255.0, float(color[1]) / 255.0, float(color[2]) / 255.0)
        cr.rectangle(0, 0, 16, 16)
        cr.fill()
        draw.set_from_pixmap(pixmap, None)
        return draw
        
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