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
import sys
import os
import g15_globals as pglobals
import g15_profile as g15profile
import gconf
import g15_driver as g15driver
import g15_util as g15util
import wnck

class G15Config:
    
    adjusting = False
    
    ''' GUI for configuring wacom-compatible drawing tablets.
    '''
    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        
        # How many macro keys are there?
        self.keys = 18
        
        # Load main Glade file
        g15Config = os.path.join(pglobals.glade_dir, 'g15-config.glade')        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(g15Config)
        
        # Monitor gconf
        self.conf_client = gconf.client_get_default()
        self.conf_client.add_dir("/apps/gnome15", gconf.CLIENT_PRELOAD_NONE)
        self.conf_client.notify_add("/apps/gnome15/cycle_seconds", self.cycle_seconds_configuration_changed);
        self.conf_client.notify_add("/apps/gnome15/cycle_screens", self.cycle_screens_configuration_changed);
        self.conf_client.notify_add("/apps/gnome15/keyboard_backlight", self.keyboard_backlight_configuration_changed);
        self.conf_client.notify_add("/apps/gnome15/active_profile", self.active_profile_changed);
        self.conf_client.notify_add("/apps/gnome15/profiles", self.profiles_changed);

        # Widgets
        self.main_window = self.widget_tree.get_object("MainWindow")
        self.profiles_tree = self.widget_tree.get_object("ProfilesTree")
        self.profileNameColumn = self.widget_tree.get_object("ProfileName")
        self.keyNameColumn = self.widget_tree.get_object("KeyName")
        self.macroNameColumn = self.widget_tree.get_object("MacroName")
        self.macroList = self.widget_tree.get_object("MacroList")
        self.application = self.widget_tree.get_object("ApplicationLocation")
        self.m1 = self.widget_tree.get_object("M1") 
        self.m2 = self.widget_tree.get_object("M2") 
        self.m3 = self.widget_tree.get_object("M3")
        self.keyboard_backlight = self.widget_tree.get_object("KeyboardBacklightAdjustment")  
        self.window_name_entry = self.widget_tree.get_object("WindowNameEntry")
        self.remove_button = self.widget_tree.get_object("RemoveButton")
        self.activate_on_focus = self.widget_tree.get_object("ActivateProfileOnFocusCheckbox")
        self.send_delays = self.widget_tree.get_object("SendDelaysCheckbox")
        self.cycle_screens = self.widget_tree.get_object("CycleScreens")
        self.cycle_seconds = self.widget_tree.get_object("CycleAdjustment")
        self.cycle_seconds_widget = self.widget_tree.get_object("CycleSeconds")
        self.macro_name_renderer = self.widget_tree.get_object("MacroNameRenderer")
        self.window_label = self.widget_tree.get_object("WindowLabel")
        self.activate_by_default = self.widget_tree.get_object("ActivateByDefaultCheckbox")
        
        # Window 
        self.main_window.set_transient_for(self.parent_window)
        self.main_window.set_icon_from_file(os.path.join(pglobals.image_dir,'g15key.png'))
        
        # Models        
        self.macrosModel = self.widget_tree.get_object("MacroModel")
        self.profiles_model = self.widget_tree.get_object("ProfileModel")
        
        self.selected_profile = g15profile.get_active_profile()
            
        # Configure widgets
        self.profiles_tree.get_selection().set_mode(gtk.SELECTION_SINGLE)        
        self.macroList.get_selection().set_mode(gtk.SELECTION_SINGLE)
        self.set_keyboard_backlight_value_from_configuration()
        self.set_cycle_seconds_value_from_configuration()
        self.set_cycle_screens_value_from_configuration()
        
        # Bind to events
        self.widget_tree.get_object("AddButton").connect("clicked", self.add_profile)
        self.remove_button.connect("clicked", self.remove_profile)
        self.widget_tree.get_object("ActivateButton").connect("clicked", self.activate)
        self.profiles_tree.connect("cursor-changed", self.select_profile)
        self.m1.connect("toggled", self.memory_changed)
        self.m2.connect("toggled", self.memory_changed)
        self.m3.connect("toggled", self.memory_changed)
        self.keyboard_backlight.connect("value-changed", self.keyboard_backlight_changed)
        self.cycle_seconds.connect("value-changed", self.cycle_seconds_changed)
        self.activate_on_focus.connect("toggled", self.activate_on_focus_changed)
        self.activate_by_default.connect("toggled", self.activate_on_focus_changed)
        self.send_delays.connect("toggled", self.send_delays_changed)
        self.cycle_screens.connect("toggled", self.cycle_screens_changed)
        self.window_name_entry.connect("changed", self.window_name_changed)
        self.macro_name_renderer.connect("edited", self.macro_name_edited)

    def set_keyboard_backlight_value_from_configuration(self):
        val = self.conf_client.get_int("/apps/gnome15/keyboard_backlight")
        if val != self.keyboard_backlight.get_value():
            self.keyboard_backlight.set_value(val)
            
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

    def active_profile_changed(self, client, connection_id, entry, args):
        self.load_configurations()
        
    def keyboard_backlight_configuration_changed(self, client, connection_id, entry, args):
        self.set_keyboard_backlight_value_from_configuration()
        
    def cycle_screens_configuration_changed(self, client, connection_id, entry, args):
        self.set_cycle_screens_value_from_configuration()
        
    def cycle_seconds_configuration_changed(self, client, connection_id, entry, args):
        self.set_cycle_seconds_value_from_configuration()
        
    def cycle_screens_changed(self, widget=None):
        self.conf_client.set_bool("/apps/gnome15/cycle_screens", self.cycle_screens.get_active())
        
    def cycle_seconds_changed(self, widget):
        val = int(self.cycle_seconds.get_value())
        self.conf_client.set_int("/apps/gnome15/cycle_seconds", val)
        
    def send_delays_changed(self, widget=None):
        self.selected_profile.send_delays = self.send_delays.get_active()
        self.selected_profile.save()
        
    def activate_on_focus_changed(self, widget=None):
        self.selected_profile.activate_on_focus = widget.get_active()        
        self.window_name_entry.set_sensitive(self.selected_profile.activate_on_focus)
        self.selected_profile.save()
        
    def window_name_changed(self, widget=None):
        self.selected_profile.window_name = self.window_name_entry.get_text()
        self.selected_profile.save()
        
    def keyboard_backlight_changed(self, widget):
        val = int(self.keyboard_backlight.get_value())
        self.conf_client.set_int("/apps/gnome15/keyboard_backlight", val)
        
    def memory_changed(self, widget):
        self.load_configuration(self.selected_profile)
        
    def select_profile(self, widget):
        (model, path) = self.profiles_tree.get_selection().get_selected()
        self.selected_profile = g15profile.get_profile(model[path][2])
        self.load_configuration(self.selected_profile)
     
    def activate(self, widget):
        (model, path) = self.profiles_tree.get_selection().get_selected()
        self.make_active(g15profile.get_profile(model[path][2]))
        
    def make_active(self, profile): 
        profile.make_active()
        self.load_configurations()
        
    def remove_profile(self, widget):
        dialog = self.widget_tree.get_object("ConfirmRemoveProfileDialog") 
        response = dialog.run()
        dialog.hide()
        if response == 1:
            active_profile = g15profile.get_active_profile()
            if self.selected_profile.id == active_profile.id:
                self.makeActive("Default")
            self.selected_profile.delete()
            self.load_configurations()
        
    def add_profile(self, widget):
        dialog = self.widget_tree.get_object("AddProfileDialog") 
        response = dialog.run()
        dialog.hide()
        if response == 1:
            new_profile_name = self.widget_tree.get_object("NewProfileName").get_text()
            new_profile = g15profile.G15Profile(new_profile_name)
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
            
        
    def profiles_changed(self, client, connection_id, entry, args):
        self.load_configurations()
        
    def macro_name_edited(self, widget, row, value):
        macro = self.get_sorted_list()[int(row)] 
        if value != macro.name:
            macro.name = value
            macro.save()
            self.load_configuration(self.selected_profile)
        
    def get_sorted_list(self):
        return sorted(self.selected_profile.macros[self.get_memory_number() - 1], key=lambda key: key.key)
        
    def load_configuration(self, profile): 
        name = profile.window_name
        if name == None:
            name = ""            
        self.macrosModel.clear()
        for macro in self.get_sorted_list():
            self.macrosModel.append([", ".join(g15util.get_key_names(macro.key)), macro.name, macro.key, True])
        self.activate_on_focus.set_active(profile.activate_on_focus)
        self.activate_by_default.set_active(profile.activate_on_focus)
        if profile.window_name != None:
            self.window_name_entry.set_text(profile.window_name)
        else:
            self.window_name_entry.set_text("")
        self.send_delays.set_active(profile.send_delays)
        self.window_name_entry.set_sensitive(self.activate_on_focus.get_active())
        
        if profile.get_default():
            self.window_name_entry.set_visible(False)
            self.activate_on_focus.set_visible(False)
            self.window_label.set_visible(False)
            self.activate_by_default.set_visible(True)
            self.remove_button.set_sensitive(False)
        else:
            self.window_name_entry.set_visible(True)
            self.activate_on_focus.set_visible(True)
            self.window_label.set_visible(True)
            self.activate_by_default.set_visible(False)
            self.remove_button.set_sensitive(True)
        
#        self.window_name_entry.set_text(name)

    def run(self):
        ''' Set up device list and start main window app.
        '''
        self.id = None                
        self.load_configurations()
        self.update_children()
        self.main_window.run()
        self.main_window.hide()
        

    def update_children(self):
        ''' Update the child widgets to reflect current settings.
        '''
        self.adjusting = True
        self.adjusting = False

################################################################################

if __name__ == '__main__':

    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-l", "--local", action="store_true", dest="runlocal",
        default=False, help="Run from current directory.")
    (options, args) = parser.parse_args()

    if options.runlocal:
        pglobals.image_dir =  os.path.join(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), ".."), "images")
        pglobals.bin_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        pglobals.glade_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        pglobals.font_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
   
    a = G15Config()
    a.run()
