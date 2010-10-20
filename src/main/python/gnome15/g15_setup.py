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
import g15_util as g15util
import gconf

class G15Setup:
    
    adjusting = False
    
    ''' GUI for configuring wacom-compatible drawing tablets.
    '''
    def __init__(self, parent_window=None, heading=None):
        self.parent_window = parent_window        
        self.conf_client = gconf.client_get_default()
        
        # Load main Glade file
        g15setup = os.path.join(pglobals.glade_dir, 'g15-setup.glade')        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(g15setup)
        
        # Change the heading maybe
        if heading != None:
            self.widget_tree.get_object("HeadingLabel").set_text(heading)

        # Widgets
        self.main_window = self.widget_tree.get_object("SetupDialog")
        self.main_window.set_icon_from_file(g15util.get_app_icon(self.conf_client, "gnome15"))
        
        # Set up based on current configuration (if any), or set to defaults
        driver = self.conf_client.get_string("/apps/gnome15/driver")
        if driver == None or driver == "g19":
            driver = "g19"
        self.widget_tree.get_object(driver).set_active(True)

        # GTK driver mode        
        self.mode_model = self.widget_tree.get_object("ModeModel")
        self.mode_combo = self.widget_tree.get_object("ModeCombo")
        mode = self.conf_client.get_string("/apps/gnome15/gtk_mode")
        if mode == None or mode == "":
            mode = "g15v1"
        idx = 0
        for row in self.mode_model:
            if row[0] == mode:
                self.mode_combo.set_active(idx)
            idx += 1
        
    def run(self):
        self.id = None                
        response = self.main_window.run()
        while gtk.events_pending():
            gtk.main_iteration(False)
        try :
            if response == 1:
                driver = "gtk"
                for d in [ "gtk", "g19", "g15" ]:
                    if self.widget_tree.get_object(d).get_active():
                        driver = d
                        
                self.conf_client.set_string("/apps/gnome15/driver", driver)        
                self.conf_client.set_string("/apps/gnome15/gtk_mode", self.mode_model[self.mode_combo.get_active()][0])
                        
                return driver
        finally:            
            self.main_window.destroy()
        
        