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
 
import gnome15.g15_screen as g15screen 
import gnome15.g15_draw as g15draw 
import gnome15.g15_driver as g15driver
import datetime
from threading import Timer
import time
import gtk
import os
import sys
import gobject
import tempfile
import subprocess
from threading import Lock
from threading import Thread

# Plugin details - All of these must be provided
id="videoplayer"
name="Video Player"
description="Plays videos!"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://localhost"
has_preferences=False

''' 
This simple plugin displays system statistics
'''

def create(gconf_key, gconf_client, screen):
    return G15VideoPlayer(gconf_key, gconf_client, screen)


class PlayThread(Thread):
    
    def __init__(self, plugin):
        Thread.__init__(self)
        self.name = "PlayThread" 
        self.setDaemon(True)
        self.plugin = plugin
        
    def stop(self):
        self.process.terminate()
        self.plugin.redraw()
        
    def run(self):        
        self.temp_dir = tempfile.mkdtemp("g15", "tmp")
        self.process = subprocess.Popen(['mplayer','-really-quiet','-vo','jpeg',self.plugin.movie_path], cwd = self.temp_dir)
        self.plugin.redraw()
        self.process.wait()
        
class G15VideoPlayer():
    
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.aspect = (16,9)
        self.screen = screen
        self.full_screen = screen.driver.get_size()
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.lock = Lock()
        
    def open(self):
        dialog = gtk.FileChooserDialog("Open..",
                               None,
                               gtk.FILE_CHOOSER_ACTION_OPEN,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        dialog.add_filter(filter)
        
        filter = gtk.FileFilter()
        filter.set_name("Movies")
        filter.add_mime_type("video/mpeg")
        filter.add_mime_type("video/quicktime")
        filter.add_mime_type("video/x-la-asf")
        filter.add_mime_type("video/x-ms-asf")
        filter.add_mime_type("video/x-msvideo")
        filter.add_mime_type("video/x-sgi-movie")
        filter.add_pattern("*.mp2")
        filter.add_pattern("*.mpa")
        filter.add_pattern("*.mpe")
        filter.add_pattern("*.mpeg")
        filter.add_pattern("*.mpg")
        filter.add_pattern("*.mpv2")
        filter.add_pattern("*.mov")
        filter.add_pattern("*.qt")
        filter.add_pattern("*.lsf")
        filter.add_pattern("*.lsx")
        filter.add_pattern("*.asf")
        filter.add_pattern("*.asr")
        filter.add_pattern("*.asx")
        filter.add_pattern("*.avi")
        filter.add_pattern("*.movie")
        dialog.add_filter(filter)
        
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            print dialog.get_filename(), 'selected'
            self.movie_path = dialog.get_filename()
            if self.playing:
                self.stop()
            self.play()
        elif response == gtk.RESPONSE_CANCEL:
            print 'Closed, no files selected'
        print "Closing dialog"
        dialog.destroy()
    
    def change_aspect(self):
        if self.aspect == (16,9):
            self.aspect = (4, 3)
        elif self.aspect == (4,3):
            # Just take up the most room
            self.aspect = (24, 9)
        elif self.aspect == (24,9):
            self.aspect = self.full_screen
        else:
            self.aspect = (16, 9)
        self.canvas.clear()
        self.redraw()
    
    def play(self):
        self.playing = PlayThread(self)
        self.playing.start()
    
    def stop(self):
        self.playing.stop()
        self.playing = None
    
    def activate(self):
        self.playing = None
        self.active = True
        self.frame_index = 1
        self.frame_wait = 0.04
        self.canvas = self.screen.new_canvas(id="Video Player")
        self.canvas.set_font_size(g15draw.FONT_TINY)
        self.redraw()
        self.screen.draw_current_canvas()
    
    def deactivate(self):
        if self.playing != None:
            self.stop()
        self.screen.del_canvas(self.canvas)
        
    def destroy(self):
        pass
    
    def handle_key(self, key, state, post=False):
        # Requires long press of L1 to cycle
        if self.active and self.screen.current_canvas == self.canvas and not post and state == g15driver.KEY_STATE_DOWN:
            if key & g15driver.G15_KEY_L2 != 0:
                gobject.idle_add(self.open)
            if key & g15driver.G15_KEY_L3 != 0:
                if self.playing == None:
                    self.play()
            if key & g15driver.G15_KEY_L4 != 0:
                if self.playing != None:
                    self.stop()
            if key & g15driver.G15_KEY_L5 != 0:
                self.change_aspect()
            return True
        return False
    
    ''' Functions specific to plugin
    ''' 
    
    def get_frame_path(self, idx):
        return os.path.join(self.playing.temp_dir, "%08d.jpg" % self.frame_index)
    
    def frame_exists(self, idx):
        return os.path.exists(get_frame_path(idx))
    
    def redraw(self):
        self.lock.acquire()
        
        try:
            w = self.screen.driver.get_size()[0]
            h = self.screen.driver.get_size()[1]
            vid_w = w
            if self.aspect != self.full_screen:
                vid_w = ( h / self.aspect[1] ) * self.aspect[0]
            wait = self.frame_wait
                
            if self.playing != None:
                
                dir = sorted(os.listdir(self.playing.temp_dir), reverse=True)
                if len(dir) > 1:
                    dir = dir[1:]
                    file = os.path.join(self.playing.temp_dir, dir[0])
                    self.canvas.draw_image_from_file(file , (0, 0, vid_w, h), (vid_w, h))
                    for path in dir:
                        file = os.path.join(self.playing.temp_dir, path)
                        os.remove(file)
                else:
                    wait = 0.1
                
            else:            
                self.canvas.fill_box((0,0, vid_w, h), color="Gray")
                
            if not self.aspect == self.full_screen:        
                self.canvas.draw_text("L2", (w - 50, 4), emboss="White")
                self.canvas.draw_text("Open", (w - 30, 4), emboss="White")
                self.canvas.draw_text("L3", (w - 50, 13), emboss="White")
                self.canvas.draw_text("Play", (w - 30, 13), emboss="White")
                self.canvas.draw_text("L4", (w - 50, 22), emboss="White")
                self.canvas.draw_text("Stop", (w - 30, 22), emboss="White")
                self.canvas.draw_text("L5", (w - 50, 31), emboss="White")
                self.canvas.draw_text("Ratio", (w - 30, 31), emboss="White")
            
            # Draw and cycle         
            self.screen.draw(self.canvas)
            
            if self.playing != None:
                timer = Timer(wait, self.redraw, ())
                timer.name = "VideoRedrawTimer"
                timer.setDaemon(True)
                timer.start()
        finally:
            self.lock.release()