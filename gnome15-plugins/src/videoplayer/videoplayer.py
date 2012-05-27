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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("videoplayer", modfile = __file__).ugettext

import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
from threading import Timer
import lcdsink
import gtk
import gst
import cairo
import os
import select
import array
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
unsupported_models = [ g15driver.MODEL_G930, g15driver.MODEL_G35, g15driver.MODEL_G110, g15driver.MODEL_Z10, g15driver.MODEL_G11, g15driver.MODEL_G11, g15driver.MODEL_MX5500 ]
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
        self._thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path(["media-video", "emblem-video", "emblem-videos", "video", "video-player" ]))
        
        # Create GStreamer pipeline
#        self.pipeline = gst.Pipeline("mypipeline")
#        self.videotestsrc = gst.element_factory_make("videotestsrc", "video")
#        self.pipeline.add(self.videotestsrc)
#        self.sink = lcdsink.CairoSurfaceThumbnailSink()
#        self.pipeline.add(self.sink)
#        self.videotestsrc.link(self.sink)


#        self.pipeline = gst.Pipeline("player")
#        
#        self.sink = lcdsink.CairoSurfaceThumbnailSink()
#        source = gst.element_factory_make("filesrc", "file-source")
##        demuxer = gst.element_factory_make("mpegdemux", "demuxer")
#        demuxer = gst.element_factory_make("oggdemux", "demuxer")
#        demuxer.connect("pad-added", self.demuxer_callback)
#        
#                
##        self.video_decoder = gst.element_factory_make("mpeg2dec", "video-decoder") 
#        self.video_decoder = gst.element_factory_make("theoradec", "video-decoder")
#       
##        self.audio_decoder = gst.element_factory_make("mad", "audio-decoder")
#        self.audio_decoder = gst.element_factory_make("vorbisdec", "audio-decoder")
#        
#        audioconv = gst.element_factory_make("audioconvert", "converter")
#        audiosink = gst.element_factory_make("autoaudiosink", "audio-output")
#        self.queuea = gst.element_factory_make("queue", "queuea")
#        self.queuev = gst.element_factory_make("queue", "queuev")
#        colorspace = gst.element_factory_make("ffmpegcolorspace", "colorspace")
#        
#        self.pipeline.add(source, demuxer, self.video_decoder, self.audio_decoder, audioconv,
#            audiosink, self.sink, self.queuea, self.queuev, colorspace)
#        gst.element_link_many(source, demuxer)
#        gst.element_link_many(self.queuev, self.video_decoder, colorspace, self.sink)
#        gst.element_link_many(self.queuea, self.audio_decoder, audioconv, audiosink)
#
#        bus = self.pipeline.get_bus()
#        bus.add_signal_watch()
#        bus.enable_sync_message_emission()
#        bus.connect("message", self.on_message)
#        bus.connect("sync-message::element", self.on_sync_message)


        self.pipeline = gst.Pipeline("player")
        self.sink = lcdsink.CairoSurfaceThumbnailSink()
        
#        source = gst.element_factory_make("filesrc", "file-source")
#        decoder = gst.element_factory_make("decodebin", "decoder")
#        decoder.connect("new-decoded-pad", self.decoder_callback)        
#        self.audio_sink = gst.element_factory_make("autoaudiosink", "audio-output")
        
#        self.pipeline.add(source, decoder, self.audio_sink, self.sink)
#        gst.element_link_many(source, decoder)


        source = gst.element_factory_make("videotestsrc", "video")
        self.pipeline.add(source, self.sink)
        self.pipeline.link(source)
        
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.sink.connect('thumbnail', self._redraw_cb)
        
    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.pipeline.set_state(gst.STATE_NULL)
            print "EOS"
            self._show_sidebar()
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.pipeline.set_state(gst.STATE_NULL)
            self._show_sidebar()
    
    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        
    def decoder_callback(self, decoder, pad, data):
        structure_name = pad.get_caps()[0].get_name()
        if structure_name.startswith("video"):
            fv_pad = self.sink.get_pad("sink")
            pad.link(fv_pad)
        elif structure_name.startswith("audio"):
            fa_pad = self.audio_sink.get_pad("sink")
            pad.link(fa_pad)
    
    def demuxer_callback(self, demuxer, pad):
        typ = pad.get_caps()[0].get_name()
        if typ.startswith("video"):
            print "Link video"
            qv_pad = self.queuev.get_pad("sink")
            pad.link(qv_pad)
        elif typ.startswith("audio"):
            print "Link audio"
            qa_pad = self.queuea.get_pad("sink")
            pad.link(qa_pad)
            
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
        size = self._screen.driver.get_size()
        if self._playing != None:
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
                
    """
    GStreamer callbacks
    """
                
    def _redraw_cb(self, unused_thsink, timestamp):
        print "**REDRAW** %d, %d" % ( len(str(unused_thsink)), timestamp )
        buf = self.sink.data
        width = self.sink.width
        height = self.sink.height
        b = array.array("b")
        b.fromstring(buf)
        print "buf len: %s / %s" % ( str(len(buf)), str(len(b)) )
        self._surface = cairo.ImageSurface.create_for_data(b,
            # We don't use FORMAT_ARGB32 because Cairo uses premultiplied
            # alpha, and gstreamer does not.  Discarding the alpha channel
            # is not ideal, but the alternative would be to compute the
            # conversion in python (slow!).
            cairo.FORMAT_RGB24,
            width,
            height,
            width * 4)
        self.redraw()
    
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
            self._hide_timer = g15util.schedule("HideSidebar", after, self._hide_sidebar)
        
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
            self._playing = self._movie_path
#            self.pipeline.get_by_name("file-source").set_property("location", self._playing)
            self.pipeline.set_state(gst.STATE_PLAYING)
        finally:
            self._lock.release()
            
    def _show_sidebar(self):
        self._sidebar_offset = 0
        self.redraw() 
    
    def _stop(self):
        self._lock.acquire()
        try:
            self.pipeline.set_state(gst.STATE_READY)
            self._playing = None
            self._show_sidebar()
        finally:
            self._lock.release()
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self._thumb_icon != None and self._screen.driver.get_bpp() == 16:
            return g15util.paint_thumbnail_image(allocated_size, self._thumb_icon, canvas)

        
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
