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
import gconf

class G15Setup:
    
    adjusting = False
    
    ''' GUI for configuring wacom-compatible drawing tablets.
    '''
    def __init__(self, parent_window=None):
        self.parent_window = parent_window        
        self.conf_client = gconf.client_get_default()
        
        # Load main Glade file
        g15setup = os.path.join(pglobals.glade_dir, 'g15-setup.glade')        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(g15setup)

        # Widgets
        self.main_window = self.widget_tree.get_object("SetupDialog")
        self.main_window.set_icon_from_file(os.path.join(pglobals.image_dir,'g15key.png'))
        
    def run(self):
        self.id = None                
        response = self.main_window.run()
        self.main_window.hide()
        
        if response == 1:
            driver = "gtk"
            if self.widget_tree.get_object("g19daemon").get_active():
                driver = "g19"
            elif self.widget_tree.get_object("g15daemon").get_active():
                driver = "g15"
            self.conf_client.set_string("/apps/gnome15/driver", driver)
            return driver
        
        