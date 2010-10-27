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

import os 
import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import g15_service as g15service
import g15_screen as g15screen
import g15_globals as pglobals
import gnomeapplet

'''
This is the Gnome panel applet version of Gnome15. 
'''
class G15Applet(gnomeapplet.Applet):
    
    def __init__(self, applet, iid, parent_window=None):
        self.__gobject_init__()
        self.parent_window = parent_window
        self.applet = applet
        
        self.service = g15service.G15Service(self, parent_window)
        
        self.applet_icon = 'g15key.png'
        self.verbs = [ ( "Props", self.service.properties ), ( "Macros", self.service.macros ), ( "About", self.service.about_info ) ]
        self.propxml="""
        <popup name="button3">
        <menuitem name="Item 1" verb="Props" label="_Preferences..." pixtype="stock" pixname="gtk-properties"/>
        <menuitem name="Item 2" verb="Macros" label="Macros" pixtype="stock" pixname="input-keyboard"/>
        <menuitem name="Item 3" verb="About" label="_About..." pixtype="stock" pixname="gnome-stock-about"/>
        </popup>
        """
        self.orientation = self.applet.get_orient()
        
        # Widgets for showing icon
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
        self.image = gtk.Image()
        self.size_changed() 
        self.box.add(self.image)
        
        # Connect some events   
        self.applet.connect("button-press-event",self.button_clicked)
        self.applet.connect("destroy",self.cleanup)
        self.applet.connect("change-orient",self.change_orientation)
        self.applet.connect("change-size",self.size_changed)
        self.applet.connect("change-background",self.background_changed)
        self.applet.connect("scroll-event",self.applet_scroll)
        
        # Show the applet
        self.applet.show_all()

        # Start everything else
        self.service.start()
        self.service.screen.add_screen_change_listener(self)
        
    def show_page(self,event, page):        
        self.service.screen.raise_page(page)
        
    def page_changed(self, page):
        pass   
        
    def title_changed(self, page, title):
        pass   
        
    def new_page(self, page):
        pass
    
    def del_page(self, page):
        pass
        
    def clear_attention(self):      
        self.applet_icon = "g15key.png"
        self.size_changed()
        
    def attention(self, message = None):       
        self.applet_icon = "g15key-error.png"
        self.size_changed()

    def quit(self):                
        gtk.main_quit()
        
    def applet_scroll(self, widget, event):
        direction = event.direction
        if direction == gtk.gdk.SCROLL_UP:
            if self.service.screen.get_visible_page().priority < g15screen.PRI_HIGH:
                self.service.screen.clear_popup() 
                self.service.screen.cycle(1)
        elif direction == gtk.gdk.SCROLL_DOWN:
            if self.service.screen.get_visible_page().priority < g15screen.PRI_HIGH:
                self.service.screen.clear_popup() 
                self.service.screen.cycle(-1)
        elif direction == gtk.gdk.SCROLL_LEFT:
            first_control = self.service.driver.get_controls()[0]
            if len(first_control.value) > 1:
                self.service.cycle_color(-1, first_control)
            else:
                self.service.cycle_level(-1, first_control)
        elif direction == gtk.gdk.SCROLL_RIGHT:     
            first_control = self.service.driver.get_controls()[0]
            if len(first_control.value) > 1:
                self.service.cycle_color(1, first_control)
            else:
                self.service.cycle_level(1, first_control)
        
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
        
    def change_orientation(self,arg1,data):
        self.orientation = self.applet.get_orient()
        if self.orientation == gnomeapplet.ORIENT_UP or self.orientation == gnomeapplet.ORIENT_DOWN:
            tmpbox = gtk.HBox()
        else:
            tmpbox = gtk.VBox()
        
        for i in (self.box.get_children()):
            i.reparent(tmpbox)

        self.container.remove(self.container.get_children()[0])
        self.box = tmpbox
        self.container.add(self.box)
        self.applet.show_all()
        
    def cleanup(self,event):
        self.shutting_down = True
        self.driver.disconnect()

    def create_menu(self):
        self.applet.setup_menu(self.propxml,self.verbs,None)  
        
    def button_clicked(self,widget,event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            pass
        
    def button_press(self,widget,event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            self.create_menu()