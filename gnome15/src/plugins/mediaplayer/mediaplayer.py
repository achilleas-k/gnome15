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
import gnome15.util.g15convert as g15convert
import gnome15.util.g15scheduler as g15scheduler
import gnome15.util.g15gconf as g15gconf
import gnome15.util.g15os as g15os
import gnome15.util.g15cairo as g15cairo
import gnome15.util.g15icontools as g15icontools
import gnome15.g15theme as g15theme
import gnome15.g15plugin as g15plugin
import gnome15.g15screen as g15screen
import gnome15.g15devices as g15devices
import gnome15.g15actions as g15actions
import gnome15.lcdsink as lcdsink
import gnome15.g15globals as g15globals
import gtk
import os
import gst
import cairo
import array
import gobject
import gio
import mimetypes
import dbus

from threading import Lock
 
import logging
logger = logging.getLogger("mediaplayer")

# Detect whether we will be able to grab multimedia keys
session_bus = dbus.SessionBus()
can_grab_media_keys = False
try:
    dbus.Interface(session_bus.get_object('org.g.SettingsDaemon',
                        '/org/gnome/SettingsDaemon'), 'org.gnome.SettingsDaemon')
    can_grab_media_keys = True
except dbus.DBusException:
    try:
        dbus.Interface(session_bus.get_object('org.gnome.SettingsDaemon',
                            '/org/gnome/SettingsDaemon/MediaKeys'),
                            'org.gnome.SettingsDaemon.MediaKeys')
        can_grab_media_keys = True
    except dbus.DBusException:
        pass

# Register the custom actions

NEXT_TRACK = "mediaplayer-next-track"
PREV_TRACK = "mediaplayer-previous-track"
PLAY_TRACK = "mediaplayer-play-track"
STOP_TRACK = "mediaplayer-stop-track"

# Register the action with all supported models
g15devices.g15_action_keys[NEXT_TRACK] = g15actions.ActionBinding(NEXT_TRACK, [ g15driver.G_KEY_NEXT ], g15driver.KEY_STATE_UP)
g15devices.z10_action_keys[NEXT_TRACK] = g15actions.ActionBinding(NEXT_TRACK, [ g15driver.G_KEY_NEXT ], g15driver.KEY_STATE_UP)
g15devices.g19_action_keys[NEXT_TRACK] = g15actions.ActionBinding(NEXT_TRACK, [ g15driver.G_KEY_NEXT ], g15driver.KEY_STATE_UP)
g15devices.g15_action_keys[PREV_TRACK] = g15actions.ActionBinding(PREV_TRACK, [ g15driver.G_KEY_PREV ], g15driver.KEY_STATE_UP)
g15devices.z10_action_keys[PREV_TRACK] = g15actions.ActionBinding(PREV_TRACK, [ g15driver.G_KEY_PREV ], g15driver.KEY_STATE_UP)
g15devices.g19_action_keys[PREV_TRACK] = g15actions.ActionBinding(PREV_TRACK, [ g15driver.G_KEY_PREV ], g15driver.KEY_STATE_UP)
g15devices.g15_action_keys[STOP_TRACK] = g15actions.ActionBinding(STOP_TRACK, [ g15driver.G_KEY_STOP ], g15driver.KEY_STATE_UP)
g15devices.z10_action_keys[STOP_TRACK] = g15actions.ActionBinding(STOP_TRACK, [ g15driver.G_KEY_STOP ], g15driver.KEY_STATE_UP)
g15devices.g19_action_keys[STOP_TRACK] = g15actions.ActionBinding(STOP_TRACK, [ g15driver.G_KEY_STOP ], g15driver.KEY_STATE_UP)
g15devices.g15_action_keys[PLAY_TRACK] = g15actions.ActionBinding(PLAY_TRACK, [ g15driver.G_KEY_PLAY ], g15driver.KEY_STATE_UP)
g15devices.z10_action_keys[PLAY_TRACK] = g15actions.ActionBinding(PLAY_TRACK, [ g15driver.G_KEY_PLAY ], g15driver.KEY_STATE_UP)
g15devices.g19_action_keys[PLAY_TRACK] = g15actions.ActionBinding(PLAY_TRACK, [ g15driver.G_KEY_PLAY ], g15driver.KEY_STATE_UP)


# Plugin details - All of these must be provided
id = "mediaplayer"
name = _("Media Player")
description = _("GStreamer based media player and webcam viewer.\n\
Supports audio and video from either DVDs, files, webcams or\n\
pulse sources. The visualisation is displayed on the LCD for audio\n\
sources.")
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = _("Copyright (C)2010 Brett Smith")
site = "http://localhost"
has_preferences = False
unsupported_models = [ g15driver.MODEL_G930, g15driver.MODEL_G35, g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G11, g15driver.MODEL_MX5500 ]

if can_grab_media_keys:
    actions={ 
             PREV_TRACK : _("Skip Backward"), 
             NEXT_TRACK : _("Skip Forward"),
             PLAY_TRACK : _("Play/Pause"),
             STOP_TRACK : _("Stop"),
             g15driver.VIEW : _("Change aspect")
             }
else:
    actions={ 
             g15driver.PREVIOUS_SELECTION : _("Skip Backward"), 
             g15driver.NEXT_SELECTION : _("Skip Forward"),
             g15driver.SELECT : _("Play/Pause"),
             g15driver.CLEAR : _("Stop"),
             g15driver.VIEW : _("Change aspect")
             }
    actions_g19={ 
             g15driver.PREVIOUS_PAGE : _("Skip Backward"), 
             g15driver.NEXT_PAGE : _("Skip Forward"),
             g15driver.SELECT : _("Play/Pause"),
             g15driver.CLEAR : _("Stop"),
             g15driver.VIEW : _("Change aspect")
             }


icon_path = g15icontools.get_icon_path(["media-video", "emblem-video", "emblem-videos", "video", "video-player", "applications-multimedia" ])

def create(gconf_key, gconf_client, screen):
    return G15MediaPlayer(gconf_client, gconf_key, screen)

def get_visualisation(plugin):
    """
    Get the currently configured visualisation.
    
    Keyword arguments:
    plugin        -- plugin instance
    """
    return g15gconf.get_string_or_default(
                    plugin.gconf_client, 
                    "%s/visualisation" % plugin.gconf_key, "goom")
    
class PulseSourceMenuItem(g15theme.MenuItem): 
    """
    Menu item to activate a single pulse source.
    """   
    def __init__(self, device_name, device_description, plugin):
        g15theme.MenuItem.__init__(self, "pulse-%s" % device_name, False, device_description)
        self._plugin = plugin
        self._device_name = device_name
        
    def get_theme_properties(self):       
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self.name
        return item_properties
    
    def activate(self):
        self._plugin._open_source(G15PulseSource(self._device_name, 
                get_visualisation(self._plugin)))
        return True
       
class MountMenuItem(g15theme.MenuItem):    
    """
    Menu item to activate a single mount (DVD etc)
    """
    def __init__(self, id, mount, plugin):
        g15theme.MenuItem.__init__(self, id, False, mount.get_name())
        self._mount = mount
        self._plugin = plugin
        
    def get_theme_properties(self):       
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self._mount.get_name()
        icon = self._mount.get_icon()        
        icon_names = [ icon.get_file().get_path() ] if isinstance(icon, gio.FileIcon) else icon.get_names() 
        icon_names += "gnome-dev-harddisk"
        item_properties["item_icon"] = g15icontools.get_icon_path(icon_names)
        return item_properties
    
    def activate(self):
        self._plugin._open_source(G15RemovableSource(self._mount))
        return True
            
class G15VideoDeviceMenuItem(g15theme.MenuItem):
    """
    Menu item to activate a single V4L2 source (i.e. Webcam etc)
    """
    
    def __init__(self, plugin, video_device_name):
        g15theme.MenuItem.__init__(self, video_device_name, False, video_device_name)
        self.plugin = plugin 
        
    def activate(self):
        self.plugin._open_source(G15WebCamSource(self.id))
            
class G15VisualisationMenuItem(g15theme.MenuItem):
    """
    Menu item to make a single visualisation the current default one
    """
    
    def __init__(self, name, plugin):
        g15theme.MenuItem.__init__(self, "visualisation-%s" % name, False, name)
        self._plugin = plugin
        self.radio = True
        
    def get_theme_properties(self):
        p = g15theme.MenuItem.get_theme_properties(self)
        p["item_radio"] = True
        p["item_radio_selected"] = get_visualisation(self._plugin) == self.name
        return p
        
    def activate(self):
        self._plugin.gconf_client.set_string("%s/visualisation" % self._plugin.gconf_key, self.name)
        self._plugin.page.mark_dirty()
        self._plugin.page.redraw()
        
class G15VideoPainter(g15screen.Painter):
    """
    Painter used to paint video or visualisation on the background of other
    pages.
    """
    
    def __init__(self, video_page):
        g15screen.Painter.__init__(self, g15screen.BACKGROUND_PAINTER, -2500)
        self._video_page = video_page
        
    def paint(self, canvas):
        if not self._video_page.is_visible():
            canvas.save()
            self._video_page._paint_video_image(canvas)
            canvas.restore()
        
class G15MediaPlayerPage(g15theme.G15Page):
    """
    The page used to display video or visualisation
    """
    
    def __init__(self, screen, source, plugin):
        g15theme.G15Page.__init__(self, "videopage-%s" % source.name, screen, \
                                  priority = g15screen.PRI_NORMAL, \
                                  title = source.name, \
                                  theme = g15theme.G15Theme(self, variant = 'mediakeys' if plugin._grabbed_keys else None), thumbnail_painter = self._paint_thumbnail, originating_plugin = plugin)
        self._sidebar_offset = 0
        self._source = source
        self._muted = False
        self._lock = Lock()
        self._plugin = plugin
        self._surface = None
        self._hide_timer = None
        self._screen = screen
        self._full_screen = self._screen.driver.get_size()
        self._aspect = self._full_screen
        self._active = True
        self._frame_index = 1
        self._last_seconds = -1
        self._thumb_icon = g15cairo.load_surface_from_file(icon_path)
        self._setup_gstreamer()
        self.screen.key_handler.action_listeners.append(self) 
        def on_delete():
            self._pipeline.set_state(gst.STATE_NULL)
            self.screen.key_handler.action_listeners.remove(self)
            self.screen.painters.remove(self.background_painter)
            self._plugin.show_menu()
            self._plugin._release_multimedia_keys()
        self.on_deleted = on_delete
        self.background_painter = G15VideoPainter(self)
        self.screen.painters.append(self.background_painter)
        self._plugin.hide_menu()
        
    def _setup_gstreamer(self):
        # Create the video source
        logger.info("Creating audio/visual source")
        self._video_src = self._source.create_source()

        # Create our custom sink that is connected to the LCD
        logger.info("Creating videosink that is connected to the LCD")
        self._video_sink = lcdsink.CairoSurfaceThumbnailSink()
        logger.info("Connecting to video sink")
        self._video_sink.connect('thumbnail', self._redraw_cb)
        
        # Now create the actual pipeline
        self._pipeline = gst.Pipeline("mypipeline")
        logger.info("Building pipeline")
        self._source.build_pipeline(self._video_src, self._video_sink, self._pipeline)
        logger.info("Built pipeline")
        self._connect_signals()
    
    def action_performed(self, binding):
        # The custom actions which can be activated outside of visible page
        if binding.action == PLAY_TRACK:
            gobject.idle_add(self._play)
            return True
        elif binding.action == NEXT_TRACK:
            gobject.idle_add(self._fwd)
            return True
        elif binding.action == PREV_TRACK:
            gobject.idle_add(self._rew)
            return True
        elif binding.action == STOP_TRACK:
            gobject.idle_add(self._stop)
            return True
        
        if self.is_visible():
            if can_grab_media_keys:
                # Default when media keys are available
                if binding.action == g15driver.VIEW:
                    gobject.idle_add(self._change_aspect)
                    return True
            else:
                # Default when media keys are not available
                if binding.action == g15driver.SELECT:
                    gobject.idle_add(self._play)
                elif ( binding.action == g15driver.PREVIOUS_PAGE and self._screen.device.model_id == g15driver.MODEL_G19 ) or \
                     ( binding.action == g15driver.PREVIOUS_SELECTION and self._screen.device.model_id != g15driver.MODEL_G19 ):
                    gobject.idle_add(self._rew)
                elif ( binding.action == g15driver.NEXT_PAGE and self._screen.device.model_id == g15driver.MODEL_G19 ) or \
                     ( binding.action == g15driver.NEXT_SELECTION and self._screen.device.model_id != g15driver.MODEL_G19 ):
                    gobject.idle_add(self._fwd)
                elif binding.action == g15driver.VIEW:
                    gobject.idle_add(self._change_aspect)
                elif binding.action == g15driver.CLEAR:
                    gobject.idle_add(self._stop)
                else:
                    return False
                return True

            
    def get_theme_properties(self):
        properties = {}
        properties["aspect"] = "%d:%d" % self._aspect
        try:
            progress_pc, progress, duration = self._get_track_progress()
        except:
            progress_pc, progress, duration = 0,(0,0,0),(0,0,0)
            
        if self._last_seconds != progress[2]:
            self.mark_dirty()
        self._last_seconds = progress[2]
                    
        if self._plugin._mm_key is not None:
            properties["key_%s" % self._plugin._mm_key] = True
                    
        properties["track_progress_pc"] = str(progress_pc)
        properties["track_progress"] = "%02d:%02d.%02d" % progress
        properties["track_duration"] = "%02d:%02d.%02d" % duration
        properties["track_name"] = "%s" % self._source.name
            
        properties["play_pause"] = _("Pause") if self._is_playing() else _("Play")
        return properties
    
    def paint_theme(self, canvas, properties, attributes):
        g15theme.G15Page.paint_theme(self, canvas, properties, attributes)
    
    def paint(self, canvas):
        self._paint_video_image(canvas)
        canvas.save()        
        if self._sidebar_offset < 0 and self._sidebar_offset > -(self.theme.bounds[2]):
            self._sidebar_offset -= 5
        canvas.translate(self._sidebar_offset, 0)
        g15theme.G15Page.paint(self, canvas)
        canvas.restore()
        if self._sidebar_offset < 0 and self._sidebar_offset > -(self.theme.bounds[2]):
            g15scheduler.schedule("RepaintVideoOverly", 0.1, self.redraw)
                
    """
    GStreamer callbacks
    """
    
    def _on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        logger.debug("Sync. %s" % message)
    
    def _on_message(self, bus, message):
        """
        Handle changes in the playing state.
        """
        t = message.type
        logger.debug("Message. %s" % message)
        if t == gst.MESSAGE_EOS:
            self._pipeline.set_state(gst.STATE_NULL)
            self._show_sidebar()
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            self._pipeline.set_state(gst.STATE_NULL)
            self._show_sidebar()
                
    def _redraw_cb(self, unused_thsink, timestamp):
        if not self._plugin.active:
            return
        buf = self._video_sink.data
        width = self._video_sink.width
        height = self._video_sink.height
        b = array.array("b")
        b.fromstring(buf)
        self._surface = cairo.ImageSurface.create_for_data(b,
            # We don't use FORMAT_ARGB32 because Cairo uses premultiplied
            # alpha, and gstreamer does not.  Discarding the alpha channel
            # is not ideal, but the alternative would be to compute the
            # conversion in python (slow!).
            cairo.FORMAT_RGB24,
            width,
            height,
            width * 4)
        
        if self.is_visible():
            self.redraw()
        else:
            self.get_screen().redraw(redraw_content = False, queue = False)
            
        
    '''
    Private
    '''
    def _get_track_progress(self):
        raw_pos = self._pipeline.query_position(gst.FORMAT_TIME, None)[0]
        raw_dur = self._pipeline.query_duration(gst.FORMAT_TIME, None)[0]
        pos = self._convert_time(int(raw_pos))
        if raw_dur < 0:
            return 100, pos, (0,0,0)
        dur = self._convert_time(int(raw_dur))
        pc = float(raw_pos) / float(raw_dur)
        return int(pc * 100), pos, dur
    
    def _connect_signals(self):
        # Watch signals coming from the bus
        logger.info("Connecting signals")
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self._on_message)
        bus.connect("sync-message::element", self._on_sync_message)
        self._source.connect_signals()
        logger.info("Connected signals")
    
    def _convert_time(self, time):
        time = time / 1000000000
        mins = time % 3600
        time = time - mins
        secs = mins % 60
        mins = mins - secs
        hours = int(time / 3600)
        mins = int(mins / 60)
        secs = int(secs)
        return hours,mins,secs
        
    def _paint_video_image(self, canvas):
        size = self._screen.driver.get_size()
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
    
    def _hide_sidebar(self, after = 0.0):
        if after == 0.0:
            self._sidebar_offset = -1    
            self._hide_timer = None
            self.redraw()
        else:    
            self._sidebar_offset = 0 
            self._cancel_hide()
            self._hide_timer = g15scheduler.schedule("HideSidebar", after, self._hide_sidebar)
            
    def _cancel_hide(self):
        if self._hide_timer != None:
            self._hide_timer.cancel()
            self._hide_timer = None
        
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
        if self._sidebar_offset != 0:
            self._show_sidebar()
            self._hide_sidebar(3.0)
    
    def _rew(self):
        pos_int = self._pipeline.query_position(gst.FORMAT_TIME, None)[0]
        seek_ns = pos_int - (10 * 1000000000)
        self._pipeline.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, seek_ns)
        if self._sidebar_offset != 0:
            self._show_sidebar()
            self._hide_sidebar(3.0)
        
    def _fwd(self):
        pos_int = self._pipeline.query_position(gst.FORMAT_TIME, None)[0]
        seek_ns = pos_int + (10 * 1000000000)
        self._pipeline.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, seek_ns)
        if self._sidebar_offset != 0:
            self._show_sidebar()
            self._hide_sidebar(3.0)
    
    def _is_paused(self):
        return gst.STATE_PAUSED == self._pipeline.get_state()[1]
    
    def _is_playing(self):
        return gst.STATE_PLAYING == self._pipeline.get_state()[1]
    
    def _play(self):
        self._lock.acquire()
        try:   
            if self._is_playing():
                self._pipeline.set_state(gst.STATE_PAUSED)
                self._cancel_hide()
                self._show_sidebar()
            else:
                self._pipeline.set_state(gst.STATE_PLAYING)
                self._hide_sidebar(3.0)
        finally:
            self._lock.release()
            
    def _show_sidebar(self):
        self._sidebar_offset = 0
        self.redraw() 
    
    def _stop(self):
        self._lock.acquire()
        try:
            self._pipeline.set_state(gst.STATE_READY)
            self.delete()
            self.screen.raise_page(self._plugin.page)
        finally:
            self._lock.release()
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self._surface != None and self._screen.driver.get_bpp() == 16:
            return g15cairo.paint_thumbnail_image(allocated_size, self._surface, canvas)


class G15MediaSource():
    """
    Superclass of all media sources
    """
    
    def __init__(self, name):
        self.name = name
        
    def create_source(self):
        raise Exception("Not implemented")
        
    def build_pipeline(self, video_src, video_sink, pipeline):
        raise Exception("Not implemented")
    
    def connect_signals(self):
        pass
        
class G15VideoFileSource(G15MediaSource):
    
    """
    Media source for playing an audio visual movie.
    """
    
    def __init__(self, name, path):
        G15MediaSource.__init__(self, name)
        self._path = path
        
    def create_source(self):
        src = gst.element_factory_make("filesrc", "video-source")
        src.set_property("location", self._path)
        return src
    
    def build_pipeline(self, video_src, video_sink, pipeline):
        
        # Create the pipeline elements
        self._decodebin = gst.element_factory_make("decodebin2")
        self._autoconvert = gst.element_factory_make("autoconvert")
        
        # As a precaution add videio capability filter
        # in the video processing pipeline.
        videocap = gst.Caps("video/x-raw-yuv")
        
        self._filter = gst.element_factory_make("capsfilter")
        self._filter.set_property("caps", videocap)
        
        # Converts the video from one colorspace to another
        self._color_space = gst.element_factory_make("ffmpegcolorspace")

        self._audioconvert = gst.element_factory_make("audioconvert")
        self._audiosink = gst.element_factory_make("autoaudiosink")
        
        # Queues
        self._queue1 = gst.element_factory_make("queue")
        self._queue2 = gst.element_factory_make("queue")
    
        pipeline.add(video_src,
                     self._decodebin,
                     self._autoconvert,
                     self._audioconvert,
                     self._queue1,
                     self._queue2,
                     self._filter,
                     self._color_space,
                     self._audiosink,
                     video_sink)
        
        # Link everything we can link now
        gst.element_link_many(video_src, self._decodebin)
        gst.element_link_many(self._queue1, self._autoconvert,
                              self._filter, self._color_space,
                              video_sink)
        gst.element_link_many(self._queue2, self._audioconvert,
                              self._audiosink)
        
    def connect_signals(self):
        if not self._decodebin is None:
            self._decodebin.connect("pad_added", self._decodebin_pad_added)

    def _decodebin_pad_added(self, decodebin, pad):
        compatible_pad = None
        caps = pad.get_caps()
        name = caps[0].get_name()
        if name[:5] == 'video':
            compatible_pad = self._queue1.get_compatible_pad(pad, caps)
        elif name[:5] == 'audio':
            compatible_pad = self._queue2.get_compatible_pad(pad, caps)

        if compatible_pad:
            pad.link(compatible_pad)
            
        
class G15AudioFileSource(G15MediaSource):
    
    """
    Media source for playing an audio file. Video is provided by the
    currently configured visualisation
    """
    
    def __init__(self, name, path, visualisation):
        G15MediaSource.__init__(self, name)
        self._path = path
        self._visualisation = visualisation
        
    def create_source(self):
        src = gst.element_factory_make("filesrc", "video-source")
        src.set_property("location", self._path)
        return src
    
    def build_pipeline(self, video_src, video_sink, pipeline):
        self._decodebin = gst.element_factory_make("decodebin2")
        self._visualiser = gst.element_factory_make(self._visualisation)
        self._color_space = gst.element_factory_make("ffmpegcolorspace")
        self._audioconvert = gst.element_factory_make("audioconvert")
        self._audiosink = gst.element_factory_make("autoaudiosink")
        self._tee = gst.element_factory_make('tee', "tee")
        self._queue1 = gst.element_factory_make("queue")
        self._queue2 = gst.element_factory_make("queue")
        pipeline.add(video_src,
                     self._decodebin,
                     self._audioconvert,
                     self._tee,
                     self._queue1,
                     self._audiosink,
                     self._queue2,
                     self._visualiser,
                     self._color_space,
                     video_sink)
        gst.element_link_many(video_src, self._decodebin)
        gst.element_link_many(self._audioconvert, self._tee)
        self._tee.link(self._queue1)
        self._queue1.link(self._audiosink)
        self._tee.link(self._queue2)
        gst.element_link_many(self._queue2, self._visualiser,self._color_space, video_sink)
        
    def connect_signals(self):
        if not self._decodebin is None:
            self._decodebin.connect("pad_added", self._decodebin_pad_added)

    def _decodebin_pad_added(self, decodebin, pad):
        self._decodebin.link(self._audioconvert)
            
        
class G15PulseSource(G15MediaSource):
    
    """
    Media source for a pulse audio monitor. Audio is not directed, it is
    just monitored to produce visualisation video
    """
    
    def __init__(self, name, visualisation):
        G15MediaSource.__init__(self, name)
        self._visualisation = visualisation
        
    def create_source(self):
        src = gst.element_factory_make("pulsesrc", "video-source")
        src.set_property("device", self.name)
        return src
    
    def build_pipeline(self, video_src, video_sink, pipeline):
        self._visualiser = gst.element_factory_make(self._visualisation)
        self._color_space = gst.element_factory_make("ffmpegcolorspace")
        self._audioconvert = gst.element_factory_make("audioconvert")
        pipeline.add(video_src,
                     self._audioconvert,
                     self._visualiser,
                     self._color_space,
                     video_sink)
        gst.element_link_many(video_src, self._audioconvert, self._visualiser,self._color_space, video_sink)
    
class G15RemovableSource(G15VideoFileSource):
    
    """
    An audio / video source that reads from removable media such as DVD 
    """
    
    def __init__(self, mount):
        G15MediaSource.__init__(self, mount.get_name(), mount.get_root().get_path())
        self._mount = mount
        
    def create_source(self):
        src = gst.element_factory_make("dvdreadsrc", "video-source")
        return src
        
class G15WebCamSource(G15MediaSource):
    
    """
    Video only source that reads from a V4L2 device such as a webcam
    """
    
    def __init__(self, name):
        G15MediaSource.__init__(self, name)
        
    def create_source(self):
        src = gst.element_factory_make("v4l2src", "video-source")
        device_path = "/dev/%s" % self.name
        logger.info("Opening Video device %s" % device_path)
        src.set_property("device", device_path)
        return src
    
    def build_pipeline(self, video_src, video_sink, pipeline):
        # Create the pipeline elements
        self._decodebin = gst.element_factory_make("decodebin2")
        self._autoconvert = gst.element_factory_make("autoconvert")
        
        videocap = gst.Caps("video/x-raw-yuv")
        self._filter = gst.element_factory_make("capsfilter")
        self._filter.set_property("caps", videocap)
        
        # Converts the video from one colorspace to another
        self._color_space = gst.element_factory_make("ffmpegcolorspace")
        
        self._queue1 = gst.element_factory_make("queue")
        
        pipeline.add(video_src,
                     self._decodebin,
                     self._autoconvert,
                     self._queue1,
                     self._filter,
                     self._color_space,
                     video_sink)
        
        # Link everything we can link now
        gst.element_link_many(video_src, self._decodebin)
        gst.element_link_many(self._queue1, self._autoconvert,
                              self._filter, self._color_space,
                              video_sink)
        
    def connect_signals(self):
        if not self._decodebin is None:
            self._decodebin.connect("pad_added", self._decodebin_pad_added)

    def _decodebin_pad_added(self, decodebin, pad):
        compatible_pad = None
        caps = pad.get_caps()
        name = caps[0].get_name()
        if name[:5] == 'video':
            compatible_pad = self._queue1.get_compatible_pad(pad, caps)

        if compatible_pad:
            pad.link(compatible_pad)


class G15MediaPlayer(g15plugin.G15MenuPlugin):
    """
    The main Media Player plugin class which is presented as a menu of
    video sources and options
    """
        
    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15MenuPlugin.__init__(self, gconf_client, gconf_key, screen, icon_path, id, name)
        self.player_pages = []
        self._grabbed_keys = None
        self._settings = None
        self._app_name = None 
        self._mm_key = None
        self._mm_key_timer = None
        
    def activate(self):
        g15plugin.G15MenuPlugin.activate(self)
    
    def load_menu_items(self):
        items = []
        self.volume_monitor_signals = []
        
        # Webcams etc
        video_devices = []
        for i in os.listdir("/dev"):
            if i.startswith("video"):
                video_devices.append(i)
                
        if len(video_devices) > 0:
            items.append(g15theme.MenuItem("video-devices", True, _("Video Devices"), icon = g15icontools.get_icon_path(["camera-web", "camera-video"]), activatable = False))
            for i in video_devices:
                items.append(G15VideoDeviceMenuItem(self, i))
                
        # Video File
        def activate_video_file():
            gobject.idle_add(self._open_video_file)
        items.append(g15theme.MenuItem("video-file", True, _("Open Audio/Video File"), activate = activate_video_file, icon = g15icontools.get_icon_path("folder")))
        
        # DVD / Mounts
        self.volume_monitor = gio.VolumeMonitor()
        self.volume_monitor_signals.append(self.volume_monitor.connect("mount_added", self._on_mount_added))
        self.volume_monitor_signals.append(self.volume_monitor.connect("mount_removed", self._on_mount_removed))
        removable_media_items = []
        for i, mount in enumerate(self.volume_monitor.get_mounts()):
            drive = mount.get_drive()
            if not mount.is_shadowed() and drive is not None and drive.is_media_removable():
                removable_media_items.append(MountMenuItem('mount-%d' % i, mount, self))
        if len(removable_media_items):
            items.append(g15theme.MenuItem("removable-devices", True, _("Removable Devices"), icon = g15icontools.get_icon_path(["driver-removable-media", "gnome-dev-removable"]), activatable = False))
            items += removable_media_items
            
        # Pulse
        status, output = g15os.get_command_output("pacmd list-sources")
        if status == 0 and len(output) > 0:
            i = 0
            pulse_items = []
            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("name: "):
                    name = line[7:-1]
                elif line.startswith("device.description = "):
                    pulse_items.append(PulseSourceMenuItem(name, line[22:-1], self))
            if len(pulse_items) > 0:
                items.append(g15theme.MenuItem("pulse-sources", True, _("PulseAudio Source"), icon = g15icontools.get_icon_path(["audio-card", "audio-speakers", "audio-volume-high", "audio-x-generic"]), activatable = False))
                items += pulse_items


        # Visualisations - TODO - there must be a better way to list them
        items.append(g15theme.MenuItem("visualisation-mode", True, _("Visualisation Mode"), icon = g15icontools.get_icon_path(["preferences-color", "gtk-select-color", "preferences-desktop-screensaver", "kscreensaver", "xscreensaver"]), activatable = False))
        for c in [ "goom", \
                  "libvisual_bumpscope", \
                  "libvisual_corona", \
                  "libvisual_infinite", \
                  "libvisual_jakdaw", \
                  "libvisual_jess", \
                  "libvisual_lv_analyzer", \
                  "libvisual_lv_scope", \
                  "libvisual_lv_oinksie", \
                  "synaesthesia", \
                  "spacescope", \
                  "spectrascope", \
                  "synaescope", \
                  "wavescope", \
                  "monoscope"]:
            try:
                gst.element_factory_make(c)
                items.append(G15VisualisationMenuItem(c, self))
            except:
                pass            
        
        self.menu.set_children(items)
        if len(items) > 0:
            self.menu.selected = items[0]
        else:
            self.menu.selected = None
            
    def deactivate(self):
        g15plugin.G15MenuPlugin.deactivate(self)
        for p in self.player_pages:
            p.delete()
        for c in self.volume_monitor_signals:
            self.volume_monitor.disconnect(c)
          
    '''
    Private
    '''  
    def _on_mount_added(self, monitor, mount, *args):
        self.load_menu_items()
        
    def _on_mount_removed(self, monitor, mount, *args):
        self.load_menu_items()  
        
    def _open_video_file(self):
        path = self._open_file()
        if path:
            mime_type, _ = mimetypes.guess_type(path)
            if mime_type.startswith("audio"):
                self._open_source(G15AudioFileSource(os.path.basename(path), path, get_visualisation(self)))
            else:
                self._open_source(G15VideoFileSource(os.path.basename(path), path))
                
    def _grab_multimedia_keys(self):
        try:
            if self._grabbed_keys is not None:
                raise Exception("Already grabbed")
            self._app_name = "%s-%s" % ( g15globals.name, name)
            def _on_key(app, key):
                if app == self._app_name:
                    self._mm_key = None
                    if key == "Play":
                        self._mm_key = g15driver.G_KEY_PLAY
                        self._player_page._play()
                    elif key == "Stop":
                        self._mm_key = g15driver.G_KEY_STOP
                        self._player_page._stop()
                    elif key == "Next":
                        self._mm_key = g15driver.G_KEY_NEXT
                        self._player_page._fwd()
                    elif key == "Previous":
                        self._mm_key = g15driver.G_KEY_PREV
                        self._player_page._rew()
                    else:
                        logger.warn("Unsupported media key %s" % key)
                    if self._mm_key_timer is not None:
                        self._mm_key_timer.cancel()
                        self._mm_key_timer = None
                    self._mm_key_timer = g15scheduler.schedule("CancelMMKey", 1.0, self._clear_mm_key)

            try:
                self._settings = dbus.Interface(session_bus.get_object('org.g.SettingsDaemon',
                                    '/org/gnome/SettingsDaemon'), 'org.gnome.SettingsDaemon')
                self._settings.GrabMediaPlayerKeys(self._app_name, 0)
                self._grabbed_keys = self._settings.connect_to_signal('MediaPlayerKeyPressed', _on_key)
            except dbus.DBusException:
                self._settings = dbus.Interface(session_bus.get_object('org.gnome.SettingsDaemon',
                                    '/org/gnome/SettingsDaemon/MediaKeys'),
                                    'org.gnome.SettingsDaemon.MediaKeys')
                self._settings.GrabMediaPlayerKeys(self._app_name, 0)
                self._grabbed_keys = self._settings.connect_to_signal('MediaPlayerKeyPressed', _on_key)
               
            logger.info("Grabbed multimedia keys")
        except dbus.DBusException, error:
            logger.warn("Could not grab multi-media keys. %s" % error)
            
    def _clear_mm_key(self):
        self._mm_key = None
        self.screen.redraw()
        
    def _release_multimedia_keys(self):
        if self._grabbed_keys:
            self._settings.ReleaseMediaPlayerKeys(self._app_name)
            session_bus.remove_signal_receiver(self._grabbed_keys)
            self._grabbed_keys = None
         
    def _open_source(self, source):
        gobject.idle_add(self._do_open_source, source)
        
    def _do_open_source(self, source):
        if can_grab_media_keys:
            self._grab_multimedia_keys()
        self._player_page = G15MediaPlayerPage(self.screen, source, self)
        self.player_pages.append(self._player_page)
        self.screen.add_page(self._player_page)
        self.screen.redraw(self._player_page)
        gobject.idle_add(self._player_page._play)
             
    def _reload_menu(self):
        self.load_menu_items()
        self.screen.redraw(self.page)
        
    def _open_file(self):
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

        # Video        
        filter = gtk.FileFilter()
        filter.set_name(_("Video Files"))
        
        filter.add_mime_type("application/ogg")
        
        filter.add_mime_type("video/ogg")
        filter.add_mime_type("video/mpeg")
        filter.add_mime_type("video/quicktime")
        filter.add_mime_type("video/x-la-asf")
        filter.add_mime_type("video/x-ms-asf")
        filter.add_mime_type("video/x-msvideo")
        filter.add_mime_type("video/x-sgi-movie")
        
        filter.add_pattern("*.ogx")
        filter.add_pattern("*.ogv")
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
        
        # Audio        
        filter = gtk.FileFilter()
        filter.set_name(_("Audio Files"))
        
        filter.add_mime_type("audio/ogg")
        filter.add_mime_type("audio/vorbis")
        filter.add_mime_type("audio/flac")
        filter.add_mime_type("audio/x-ogg")
        filter.add_mime_type("audio/x-vorbis")
        filter.add_mime_type("audio/x-flac")
        filter.add_mime_type("audio/basic")
        filter.add_mime_type("audio/mid")
        filter.add_mime_type("audio/mpeg")
        filter.add_mime_type("audio/aiff")
        filter.add_mime_type("audio/x-aiff")
        filter.add_mime_type("audio/x-mpegurl")
        filter.add_mime_type("audio/x-pn-realaudio")
        filter.add_mime_type("audio/x-realaudio")
        filter.add_mime_type("audio/wav")
        filter.add_mime_type("audio/x-wav")
        filter.add_mime_type("audio/x-au")
        filter.add_mime_type("audio/x-midi")
        filter.add_mime_type("audio/x-mpeg")
        filter.add_mime_type("audio/x-mpeg3")
        filter.add_mime_type("audio/x-mpeg-3")
        filter.add_mime_type("audio/midi")
        filter.add_mime_type("audio/x-mid")
        
        filter.add_pattern("*.flac")
        filter.add_pattern("*.oga")
        filter.add_pattern("*.ogg")
        filter.add_pattern("*.au")
        filter.add_pattern("*.snd")
        filter.add_pattern("*.mid")
        filter.add_pattern("*.rmi")
        filter.add_pattern("*.mp3")
        filter.add_pattern("*.aif")
        filter.add_pattern("*.aifc")
        filter.add_pattern("*.aiff")
        filter.add_pattern("*.m3u")
        filter.add_pattern("*.ra")
        filter.add_pattern("*.ram")
        filter.add_pattern("*.wav")
        dialog.add_filter(filter)
        
        response = dialog.run()
        while gtk.events_pending():
            gtk.main_iteration(False) 
        try:
            if response == gtk.RESPONSE_OK:
                return dialog.get_filename()
        finally:
            dialog.destroy() 