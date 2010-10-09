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
import gnome15.g15_driver as g15driver
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
import datetime
from threading import Timer
import time
import gtk
import os
import sys
import select
import gobject
import tempfile
import subprocess
from threading import Lock
from threading import Thread

# Plugin details - All of these must be provided
id = "videoplayer"
name = "Video Player"
description = "Plays videos! Very much experimental, this plugin uses " \
            + "mplayer to generate JPEG images which are then loaded " \
            + "and displayed on the LCD. This means it is very CPU AND " \
            + "disk intensive and should only be used as a toy. "
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = "Copyright (C)2010 Brett Smith"
site = "http://localhost"
has_preferences = False

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
          
        self.temp_dir = tempfile.mkdtemp("g15", "tmp")
        self.process = subprocess.Popen(['mplayer', '-slave', '-noconsolecontrols','-really-quiet', 
                                         '-vo', 'jpeg', self.plugin.movie_path], cwd=self.temp_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        
        self.plugin.screen.redraw(self.plugin.page)
        
    def playing(self):
        return self.process.poll() == None
        
    def stop(self):
        self.process.terminate()
        self.plugin.screen.redraw(self.plugin.page)
        
    def mute(self, mute):
        if mute:
            print self.command("mute", "1")
        else:
            print self.command("mute", "0")
            
    def readlines(self):
        ret = []
        while any(select.select([self.process.stdout.fileno()], [], [], 0.6)):
            ret.append( self.process.stdout.readline() )
        return ret
    
    def command(self, name, *args):
        cmd = '%s%s%s\n'%(name,
                ' ' if args else '',
                ' '.join(repr(a) for a in args)
                )
        self.process.stdin.write(cmd)
        if name == 'quit':
            return
        return self.readlines()
        
    def set_aspect(self, aspect):
        pass
#        self.command("switch_ratio",str(float(aspect[0]) / float(aspect[1])))
        
    def run(self):      
        self.process.wait()
        
class G15VideoPlayer():
    
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.sidebar_offset = 0
        self.full_screen = screen.driver.get_size()
        self.aspect = self.full_screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.hidden = True
        self.muted = False
        self.lock = Lock()
        self.surface = None
        self.hide_timer = None
        
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
        while gtk.events_pending():
            gtk.main_iteration(False) 
        if response == gtk.RESPONSE_OK:
            print dialog.get_filename(), 'selected'
            self.movie_path = dialog.get_filename()
            if self.playing:
                self.stop()
            self.play()
        dialog.destroy() 
        return False
    
    def change_aspect(self):
        if self.aspect == (16, 9):
            self.aspect = (4, 3)
        elif self.aspect == (4, 3):
            # Just take up the most room
            self.aspect = (24, 9)
        elif self.aspect == (24, 9):
            self.aspect = self.full_screen
        else:
            self.aspect = (16, 9)
        self.screen.redraw(self.page)
    
    def play(self):
        self.lock.acquire()
        try:
            self.hide_sidebar(3.0)
            self.playing = PlayThread(self)
            self.playing.set_aspect(self.aspect)
            self.playing.mute(self.muted)
            self.playing.start()
        finally:
            self.lock.release()
    
    def stop(self):
        self.lock.acquire()
        try:
            if self.hide_timer != None:
                self.hide_timer.cancel()
            self.sidebar_offset = 0
            self.playing.stop()
            self.playing = None
        finally:
            self.lock.release()
    
    def activate(self):
        self.playing = None
        self.active = True
        self.frame_index = 1
        self.frame_wait = 0.04
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
        self.page = self.screen.new_page(self.paint, id="Video Player", on_hidden=self.on_hidden, on_shown=self.on_shown, use_cairo=True)
        self.screen.redraw(self.page)
    
    def deactivate(self):
        if self.playing != None:
            self.stop()
        self.screen.del_page(self.page)
        
    def on_shown(self):
        self.hidden = False
        
    def on_hidden(self):
        self.hidden = True
        
    def destroy(self):
        pass
    
    def handle_key(self, keys, state, post=False):
        # Requires long press of L1 to cycle
        if not self.hidden and not post and state == g15driver.KEY_STATE_UP:
            if g15driver.G_KEY_G1 in keys:
                gobject.idle_add(self.open)
            if g15driver.G_KEY_G2 in keys:
                if self.playing == None:
                    self.play()
            if g15driver.G_KEY_G3 in keys:
                if self.playing != None:
                    self.stop()
            if g15driver.G_KEY_G4 in keys:
                if self.playing != None:
                    self.hide_sidebar(3.0)
                self.change_aspect()
            if g15driver.G_KEY_G5 in keys:
                self.muted = not self.muted
                if self.playing != None:
                    self.hide_sidebar(3.0)
                    self.playing.mute(self.muted)
            return True
        return False
    
    ''' Functions specific to plugin
    ''' 
    def hide_sidebar(self, after = 0.0):
        if after == 0.0:
            self.sidebar_offset = -1    
            self.hide_timer = None
        else:    
            self.sidebar_offset = 0 
            if self.hide_timer != None:
                self.hide_timer.cancel()
            self.hide_timer = g15util.schedule("HideSidebar", after, self.hide_sidebar)
    
    def get_frame_path(self, idx):
        return os.path.join(self.playing.temp_dir, "%08d.jpg" % self.frame_index)
    
    def frame_exists(self, idx):
        return os.path.exists(get_frame_path(idx))
    
    def paint(self, canvas):
        self.lock.acquire()
        try:        
            wait = self.frame_wait
            size = self.screen.driver.get_size()
                
            if self.playing != None:
                
                # Process may have been killed
                if not self.playing.playing():
                    self.stop()
                
                dir = sorted(os.listdir(self.playing.temp_dir), reverse=True)
                if len(dir) > 1:
                    dir = dir[1:]
                    file = os.path.join(self.playing.temp_dir, dir[0])
                    self.surface, context = g15util.load_surface_from_file(file)
                    for path in dir:
                        file = os.path.join(self.playing.temp_dir, path)
                        os.remove(file)
                else:
                    wait = 0.1
                
                if self.surface != None:
                    
#                    target_size = ( float(size[1]) * (float(self.aspect[0]) ) / float(self.aspect[1]), float(size[1]) ) 
                    target_size = ( float(size[0]), float(size[0]) * (float(self.aspect[1]) ) / float(self.aspect[0]) )
                    
                    sx = float(target_size[0]) / float(self.surface.get_width())
                    sy = float(target_size[1]) / float(self.surface.get_height())
#                    scale = max(sx, sy)

                    canvas.save()
                    canvas.translate((size[0] - target_size[0]) / 2.0,(size[1] - target_size[1]) / 2.0)
                    canvas.scale(sx, sy)
                    canvas.set_source_surface(self.surface)
                    canvas.paint()
                    canvas.restore()
                
            properties = {}
            properties["aspect"] = "%d:%d" % self.aspect
            
            canvas.translate(self.sidebar_offset, 0)
            self.theme.draw(canvas, properties)
            
            if self.sidebar_offset < 0 and self.sidebar_offset > -(size[0]):
                self.sidebar_offset -= 5                
                
    #        if not self.aspect == self.full_screen:        
    #            canvas.draw_text("G1", (w - 50, 4), emboss="White")
    #            canvas.draw_text("Open", (w - 30, 4), emboss="White")
    #            canvas.draw_text("G2", (w - 50, 13), emboss="White")
    #            canvas.draw_text("Play", (w - 30, 13), emboss="White")
    #            canvas.draw_text("G3", (w - 50, 22), emboss="White")
    #            canvas.draw_text("Stop", (w - 30, 22), emboss="White")
    #            canvas.draw_text("G4", (w - 50, 31), emboss="White")
    #            canvas.draw_text("Ratio", (w - 30, 31), emboss="White")
            
            if self.playing != None:
                timer = Timer(wait, self.screen.redraw, [self.page])
                timer.name = "VideoRedrawTimer"
                timer.setDaemon(True)
                timer.start()
        finally:
            self.lock.release()
