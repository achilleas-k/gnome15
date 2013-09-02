#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2010 Brett Smith <tanktarta@blueyonder.co.uk>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("videoplayer", modfile = __file__).ugettext

import gnome15.g15driver as g15driver
import gnome15.util.g15convert as g15convert
import gnome15.util.g15scheduler as g15scheduler
import gnome15.util.g15cairo as g15cairo
import gnome15.util.g15icontools as g15icontools
import gnome15.g15theme as g15theme
from threading import Timer
import gtk
import os
import select
import gobject
import tempfile
import subprocess
from threading import Lock
from threading import Thread
 
# Plugin details - All of these must be provided
id = "videoplayer"
name = _("Video Player")
description = _("Plays videos! Very much experimental, this plugin uses \
mplayer to generate JPEG images which are then loaded \
and displayed on the LCD. This means it is very CPU AND \
disk intensive and should only be used as a toy. ")
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = _("Copyright (C)2010 Brett Smith")
site = "http://localhost"
has_preferences = False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G11, g15driver.MODEL_MX5500, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Stop"), 
         g15driver.NEXT_SELECTION : _("Play"),
         g15driver.SELECT : _("Open file"),
         g15driver.CLEAR : _("Toggle Mute"),
         g15driver.VIEW : _("Change aspect")
         }

''' 
This simple plugin displays system statistics
'''

def create(gconf_key, gconf_client, screen):
    return G15VideoPlayer(gconf_key, gconf_client, screen)


class PlayThread(Thread):
    
    def __init__(self, page):
        Thread.__init__(self)
        self.name = "PlayThread" 
        self.setDaemon(True)
        self._page = page
          
        self.temp_dir = tempfile.mkdtemp("g15", "tmp")
        self._process = subprocess.Popen(['mplayer', '-slave', '-noconsolecontrols','-really-quiet', 
                                         '-vo', 'jpeg', self._page._movie_path], cwd=self.temp_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self._page.redraw()
        
    def _playing(self):
        return self._process.poll() == None
        
    def _stop(self):
        try:
            self._process.terminate()
        except OSError:
            # Got killed
            pass
        self._page.redraw()
        
    def _mute(self, mute):
        if mute:
            print self._command("mute", "1")
        else:
            print self._command("mute", "0")
            
    def _readlines(self):
        ret = []
        while any(select.select([self._process.stdout.fileno()], [], [], 0.6)):
            ret.append( self._process.stdout.readline() )
        return ret
    
    def _command(self, name, *args):
        cmd = '%s%s%s\n'%(name,
                ' ' if args else '',
                ' '.join(repr(a) for a in args)
                )
        self._process.stdin.write(cmd)
        if name == 'quit':
            return
        return self.readlines()
        
    def set_aspect(self, aspect):
        pass
#        self.command("switch_ratio",str(float(aspect[0]) / float(aspect[1])))
        
    def run(self):      
        self._process.wait()
        
class G15VideoPage(g15theme.G15Page):
    
    def __init__(self, screen):
        g15theme.G15Page.__init__(self, id, screen, title = name, theme = g15theme.G15Theme(self), thumbnail_painter = self._paint_thumbnail)
        self._sidebar_offset = 0
        self._muted = False
        self._lock = Lock()
        self._surface = None
        self._hide_timer = None
        self._screen = screen
        self._full_screen = self._screen.driver.get_size()
        self._aspect = self._full_screen
        self._playing = None
        self._active = True
        self._frame_index = 1
        self._frame_wait = 0.04
        self._thumb_icon = g15cairo.load_surface_from_file(g15icontools.get_icon_path(["media-video", "emblem-video", "emblem-videos", "video", "video-player" ]))
            
    def get_theme_properties(self):
        properties = g15theme.G15Page.get_theme_properties(self)
        properties["aspect"] = "%d:%d" % self._aspect
        return properties
    
    def paint_theme(self, canvas, properties, attributes):
        canvas.save()        
            
        if self._sidebar_offset < 0 and self._sidebar_offset > -(self.theme.bounds[2]):
            self._sidebar_offset -= 5
            
        canvas.translate(self._sidebar_offset, 0)
        g15theme.G15Page.paint_theme(self, canvas, properties, attributes)
        canvas.restore()
    
    def paint(self, canvas):
        g15theme.G15Page.paint(self, canvas)
        wait = self._frame_wait
        size = self._screen.driver.get_size()
            
        if self._playing != None:
            
            # Process may have been killed
            if not self._playing._playing():
                self._stop()
            
            dir = sorted(os.listdir(self._playing.temp_dir), reverse=True)
            if len(dir) > 1:
                dir = dir[1:]
                file = os.path.join(self._playing.temp_dir, dir[0])
                self._surface = g15cairo.load_surface_from_file(file)
                for path in dir:
                    file = os.path.join(self._playing.temp_dir, path)
                    os.remove(file)
            else:
                wait = 0.1
            
            if self._surface != None:
                target_size = ( float(size[0]), float(size[0]) * (float(self._aspect[1]) ) / float(self._aspect[0]) )
                sx = float(target_size[0]) / float(self._surface.get_width())
                sy = float(target_size[1]) / float(self._surface.get_height())
                canvas.save()
                canvas.translate((size[0] - target_size[0]) / 2.0,(size[1] - target_size[1]) / 2.0)
                canvas.scale(sx, sy)
                canvas.set_source_surface(self._surface)
                canvas.paint()
                canvas.restore()   
        
        if self._playing != None:
            timer = Timer(wait, self.redraw)
            timer.name = "VideoRedrawTimer"
            timer.setDaemon(True)
            timer.start()
    
    ''' Functions specific to plugin
    ''' 
    def _hide_sidebar(self, after = 0.0):
        if after == 0.0:
            self._sidebar_offset = -1    
            self._hide_timer = None
        else:    
            self._sidebar_offset = 0 
            if self._hide_timer != None:
                self._hide_timer.cancel()
            self._hide_timer = g15scheduler.schedule("HideSidebar", after, self._hide_sidebar)
        
    def _open(self):
        dialog = gtk.FileChooserDialog("Open..",
                               None,
                               gtk.FILE_CHOOSER_ACTION_OPEN,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        
        filter = gtk.FileFilter()
        filter.set_name(_("All files"))
        filter.add_pattern("*")
        dialog.add_filter(filter)
        
        filter = gtk.FileFilter()
        filter.set_name(_("Movies"))
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
            self._movie_path = dialog.get_filename()
            if self._playing:
                self._stop()
            self._play()
        dialog.destroy() 
        return False
    
    def _change_aspect(self):
        if self._aspect == (16, 9):
            self._aspect = (4, 3)
        elif self._aspect == (4, 3):
            # Just take up the most room
            self._aspect = (24, 9)
        elif self._aspect == (24, 9):
            self._aspect = self._full_screen
        else:
            self._aspect = (16, 9)
        self._screen.redraw(self._page)
    
    def _play(self):
        self._lock.acquire()
        try:
            self._hide_sidebar(3.0)
            self._playing = PlayThread(self)
            self._playing.set_aspect(self._aspect)
            self._playing.mute(self.muted)
            self._playing.start()
        finally:
            self._lock.release()
    
    def _stop(self):
        self._lock.acquire()
        try:
            if self._hide_timer != None:
                self._hide_timer.cancel()
            self._sidebar_offset = 0
            self._playing._stop()
            self._playing = None
        finally:
            self._lock.release()
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self._thumb_icon != None and self._screen.driver.get_bpp() == 16:
            return g15cairo.paint_thumbnail_image(allocated_size, self._thumb_icon, canvas)

        
class G15VideoPlayer():
    
    
    def __init__(self, gconf_key, gconf_client, screen):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
    
    def activate(self):
        self._page = G15VideoPage(self._screen)
        self._screen.add_page(self._page)
        self._screen.redraw(self._page)
        self._screen.key_handler.action_listeners.append(self)
    
    def deactivate(self):
        if self._page._playing != None:
            self._page._stop()
        self._screen.del_page(self._page)
        self._screen.key_handler.action_listeners.remove(self)
        
    def destroy(self):
        pass
    
    def action_performed(self, binding):
        if self._page is not None and self._page.is_visible():
            if binding.action == g15driver.SELECT:
                gobject.idle_add(self._page._open)
            elif binding.action == g15driver.NEXT_SELECTION:
                if self._page._playing == None:
                    self._page._play()
            elif binding.action == g15driver.PREVIOUS_SELECTION:
                if self._page._playing != None:
                    self._page._stop()
            elif binding.action == g15driver.VIEW:
                if self._page._playing != None:
                    self._page._hide_sidebar(3.0)
                self._change_aspect()
            elif binding.action == g15driver.CLEAR:
                self._page.muted = not self._page.muted
                if self._page._playing != None:
                    self._page._hide_sidebar(3.0)
                    self._playing.mute(self._page.muted)
            else:
                return False
            return True
