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
 
import pygtk
pygtk.require('2.0')
import gtk
import g15util as g15util
import g15drivermanager
import gconf
import subprocess

class G15Setup(gtk.Dialog):
    
    adjusting = False
    
    def __init__(self, parent_window=None, allow_quit = False, first_run = True):
        
        if len(g15drivermanager.imported_drivers) == 0:
            buttons = ( "Quit", gtk.RESPONSE_CLOSE)
            heading = "<b>No Gnome15 drivers were detected. Make sure you have installed the appropriate driver package for your hardware.</b>"
            icon = "error"
        else:
            icon = "input-keyboard"
            if allow_quit:
                buttons = ("Apply", gtk.RESPONSE_APPLY, "Quit", gtk.RESPONSE_CLOSE)
            else:
                buttons = ("Apply", gtk.RESPONSE_APPLY)
            if first_run:
                heading = "<b>This is the first run Gnome15, and you must choose a driver to use. " + \
                        "Select the option below most appropriate to your setup.</b>"
            else:
                heading = "<b>Choose the driver most appropriate for your hardware.</b>"
                
        gtk.Dialog.__init__(self, "Gnome15 Setup", parent_window, gtk.DIALOG_DESTROY_WITH_PARENT | gtk.DIALOG_NO_SEPARATOR, buttons)
                
#        self.set_size_request(760, -1)
        self.conf_client = gconf.client_get_default()
        self.set_icon_from_file(g15util.get_app_icon(self.conf_client, "gnome15"))
        self.selected_driver = None
        self.set_modal(True)
        driver = self.conf_client.get_string("/apps/gnome15/driver")
        if driver == None:
            driver = "driver_g19"
        else:
            driver = "driver_" + driver
        if driver in g15drivermanager.imported_drivers:
            self.selected_driver = g15drivermanager.imported_drivers[driver]
        elif len(g15drivermanager.imported_drivers) > 0:
            self.selected_driver = g15drivermanager.imported_drivers.items()[0][1]
        else:
            self.selected_driver = None
        heading_hbox = gtk.HBox()
        image = gtk.image_new_from_icon_name(icon, 64)
        image.set_pixel_size(64)
        heading_hbox.pack_start(image, False, False, 8)
        heading_label = gtk.Label(heading)
        heading_label.set_line_wrap(True)
        heading_label.set_alignment(0.0, 0.5)
        heading_label.set_line_wrap(True)
        heading_label.set_use_markup(True)
        heading_hbox.pack_start(heading_label, True, True, 8)
        
        self.vbox.add(heading_hbox)
        
        if len(g15drivermanager.imported_drivers) != 0:
            driver_table = gtk.VBox()
            driver_table.set_spacing(8)
            driver_table.set_border_width(8)
            button_group = None
            
            for driver_mod_key in g15drivermanager.imported_drivers:
                driver_mod = g15drivermanager.imported_drivers[driver_mod_key]
                button = gtk.RadioButton(button_group, driver_mod.name)
                button.set_alignment(0.0, 0.5)
                if driver_mod_key == driver:
                    button.set_active(True)
                button.connect("toggled", self.set_driver, driver_mod)
                if button_group == None:
                    button_group = button
                    
                driver_top = gtk.HBox()
                driver_top.set_spacing(4)
                driver_top.pack_start(button, True, True)
                if driver_mod.has_preferences:
                    pref_button = gtk.Button("Preferences", stock = gtk.STOCK_PREFERENCES, use_underline = True)
                    pref_button.connect("clicked", self.driver_preferences, driver_mod)
                    driver_top.pack_start(pref_button, False, False)
                    
                driver_table.pack_start(driver_top, True, True)
                desc_label = gtk.Label(driver_mod.description)
                desc_label.set_size_request(600, -1)
                desc_label.set_alignment(0.0, 0.5)
                desc_label.set_line_wrap(True)
                desc_label.set_use_markup(True)
                driver_table.pack_start(desc_label, True, True)
        
            self.vbox.add(driver_table)
        
        self.show_all()

    def set_driver(self, button, driver_mod):
        if button.get_active():
            self.selected_driver = driver_mod    
        
    def driver_preferences(self, button, driver_mod):
        driver_mod.show_preferences(self, self.conf_client)
        
    def open_site(self, widget):
        subprocess.Popen(['xdg-open',widget.get_uri()])
        
    def setup(self):
        self.id = None                
        response = self.run()
        while gtk.events_pending():
            gtk.main_iteration(False)
        try :
            if response == gtk.RESPONSE_APPLY:
                self.conf_client.set_string("/apps/gnome15/driver", self.selected_driver.id)        
                return self.selected_driver.id
        finally:            
            self.destroy()
        
        