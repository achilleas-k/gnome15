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
_ = g15locale.get_translation("mpris", modfile = __file__).ugettext

import gnome15.g15screen as g15screen
import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gnome15.g15scheduler as g15scheduler
import gnome15.g15python_helpers as g15python_helpers
import gnome15.g15cairo as g15cairo
import gnome15.g15theme as g15theme
import gnome15.g15plugin as g15plugin
import gnome15.g15devices as g15devices
import gnome15.g15actions as g15actions
import dbus
import os
import time

import xdg.Mime as mime
import urllib

# Logging
import logging
from dbus.exceptions import DBusException
logger = logging.getLogger("mpris")

# Custom actions
NEXT_TRACK = "mpris-next-track"
PREV_TRACK = "mpris-previous-track"
PLAY_TRACK = "mpris-play-track"
STOP_TRACK = "mpris-stop-track"

# Register the action with all supported models
g15devices.g15_action_keys[NEXT_TRACK] = g15actions.ActionBinding(NEXT_TRACK, [ g15driver.G_KEY_NEXT ], g15driver.KEY_STATE_UP)
g15devices.g19_action_keys[NEXT_TRACK] = g15actions.ActionBinding(NEXT_TRACK, [ g15driver.G_KEY_NEXT ], g15driver.KEY_STATE_UP)
g15devices.g15_action_keys[PREV_TRACK] = g15actions.ActionBinding(PREV_TRACK, [ g15driver.G_KEY_PREV ], g15driver.KEY_STATE_UP)
g15devices.g19_action_keys[PREV_TRACK] = g15actions.ActionBinding(PREV_TRACK, [ g15driver.G_KEY_PREV ], g15driver.KEY_STATE_UP)
g15devices.g15_action_keys[STOP_TRACK] = g15actions.ActionBinding(STOP_TRACK, [ g15driver.G_KEY_STOP ], g15driver.KEY_STATE_UP)
g15devices.g19_action_keys[STOP_TRACK] = g15actions.ActionBinding(STOP_TRACK, [ g15driver.G_KEY_STOP ], g15driver.KEY_STATE_UP)
g15devices.g15_action_keys[PLAY_TRACK] = g15actions.ActionBinding(PLAY_TRACK, [ g15driver.G_KEY_PLAY ], g15driver.KEY_STATE_UP)
g15devices.g19_action_keys[PLAY_TRACK] = g15actions.ActionBinding(PLAY_TRACK, [ g15driver.G_KEY_PLAY ], g15driver.KEY_STATE_UP)

# Plugin details - All of these must be provided
id="mpris"
name=_("Now Playing")
description=_("Displays information about currently playing media. Requires \
a player that supports the MPRIS (version 1 or 2) specification. This \
includes Rhythmbox, Banshee (with a plugin), Audacious, VLC and others. \
Supports multiple media players running at the same time, each gets \
their own screen.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         NEXT_TRACK : "Skip to the next track",
         PREV_TRACK : "Skip to the previous track",
         STOP_TRACK : "Stop the current track",
         PLAY_TRACK : "Play / Pause the current track",
         }

# Players that are not supported
mpris_blacklist = [ "org.mpris.xbmc", "org.mpris.audacious" ]

def create(gconf_key, gconf_client, screen):
    return G15MPRIS(gconf_client,gconf_key, screen)

class AbstractMPRISPlayer():
    
    def __init__(self, gconf_client, screen, players, interface_name, session_bus, title, theme):
        logger.info("Starting player %s" % interface_name)
        self.stopped = False
        self.elapsed = 0
        self.volume = 0
        self.hidden = True
        self.title = title
        self.session_bus = session_bus
        self.page = None
        self.duration = 0
        self.screen = screen
        self.interface_name = interface_name
        self.players = players
        self.playing_uri = None
        self.playback_started = 0
        self.start_elapsed = 0
        self.gconf_client = gconf_client   
        self.cover_image = None
        self.thumb_image = None
        self.cover_uri = None
        self.song_properties = {}
        self.status = "Stopped"      
        self.redraw_timer = None  
        self.theme = theme
        
    def action_performed(self, binding):
        if binding.action == NEXT_TRACK:
            self.next_track()
            return True
        elif binding.action == PREV_TRACK:
            self.prev_track()
            return True
        elif binding.action == PLAY_TRACK:
            self.play_pause_track()
            return True
        elif binding.action == STOP_TRACK:
            self.stop_track()
            return True
        
    def next_track(self):
        logger.warn("Next track not implemented")
        
    def prev_track(self):
        logger.warn("Previous track not implemented")
        
    def play_pause_track(self):
        logger.warn("Play pause track not implemented")
        
    def stop_track(self):
        logger.warn("Stop track not implemented")
        
    def check_status(self):        
        new_status = self.get_new_status()
        self.volume = self.get_volume()   
        if new_status != self.status:            
            self.set_status(new_status)
        else:
            if self.status == "Playing":   
                self.recalc_progress()
                self.screen.redraw(self.page)
                    
    def reset_elapsed(self):
        logger.debug("Reset track elapsed time")
        self.start_elapsed = self.get_progress()
        self.playback_started = time.time()
        
    def set_status(self, new_status):        
        if new_status != self.status:
            logger.info("Playback status changed to %s" % new_status)
            self.status = new_status
            if self.status == "Playing":
                g15scheduler.schedule("playbackStarted", 1.0, self._playback_started)
            elif self.status == "Paused":
                self.cancel_redraw()
                if self.page != None:
                    logger.info("Paused.")
                    self.load_song_details()
                    self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)
                else:
                    self.show_page()
            elif self.status == "Stopped":
                self.cancel_redraw()
                self.hide_page()
                
    def _playback_started(self):        
        self.reset_elapsed()
        logger.info("Now playing, showing page")
        self.show_page()
        self.schedule_redraw()
    
    def stop(self):
        logger.info("Stopping player %s" % self.interface_name)
        self.stopped = True
        self.on_stop()
        if self.redraw_timer != None:
            self.redraw_timer.cancel()
        if self.page != None:
            self.hide_page()
        del self.players[self.interface_name]
    
    def show_page(self):
        self.load_song_details()
        self.page = self.screen.get_page(page_id="MPRIS%s" % self.title)
        if self.page == None:
            self.page = g15theme.G15Page("MPRIS%s" % self.title, self.screen, on_shown=self.on_shown, \
                                         on_hidden=self.on_hidden, theme_properties_callback = self._get_properties, \
                                         panel_painter = self.paint_panel, thumbnail_painter = self.paint_thumbnail, \
                                         theme = self.theme, title = self.title,
                                         originating_plugin = self)
            self.screen.add_page(self.page)
            self.screen.redraw(self.page)
        else:
            self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)
        
    def hide_page(self):
        self.screen.del_page(self.page)
        self.page = None
        
    def redraw(self):
        if self.status == "Playing":
            self.elapsed = time.time() - self.playback_started + self.start_elapsed 
            self.recalc_progress() 
            self.screen.redraw(self.page)
            self.schedule_redraw()
            
    def schedule_redraw(self): 
        self.cancel_redraw()
        self.redraw_timer = g15scheduler.queue("mprisDataQueue-%s" % self.screen.device.uid, "MPRIS2Redraw", 1.0, self.redraw)
        
    def on_shown(self):
        self.hidden = False
        if self.status == "Playing":
            self.schedule_redraw()
        
    def on_hidden(self):
        self.hidden = True      
        self.cancel_redraw()
            
    def cancel_redraw(self):
        if self.redraw_timer != None:
            self.redraw_timer.cancel()
            self.redraw_timer = None
        
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None and self.thumb_image != None:
            size = g15util.paint_thumbnail_image(allocated_size, self.thumb_image, canvas)
            return size
        
    def paint_panel(self, canvas, allocated_size, horizontal):
        if self.page != None and self.thumb_image != None and self.status == "Playing":
            size = g15util.paint_thumbnail_image(allocated_size, self.thumb_image, canvas)
            return size
            
    def process_properties(self):
        
        logger.debug("Processing properties")
                
        self.recalc_progress()
        # Find the best icon for the media
        
        
        if "art_uri" in self.song_properties and self.song_properties["art_uri"] != "":
            new_cover_uri = self.song_properties["art_uri"]
        else:   
            cover_art = os.path.expanduser("~/.cache/rhythmbox/covers/" + self.song_properties["artist"] + " - " + self.song_properties["album"] + ".jpg")
            new_cover_uri = None
            if cover_art != None and os.path.exists(cover_art):
                new_cover_uri = cover_art
                
        if new_cover_uri == None:
            new_cover_uri = self.get_default_cover()
                
        if new_cover_uri != self.cover_uri:
            self.cover_uri = new_cover_uri
            logger.info("Getting cover art from %s" % self.cover_uri)
            self.cover_image = None
            self.thumb_image = None
            if self.cover_uri != None:
                cover_image = g15cairo.load_surface_from_file(self.cover_uri, self.screen.driver.get_size()[0])
                if cover_image:
                    self.cover_image = cover_image
                    
                    # If the cover URI was from HTTP, then we cached it. Use that as the URI
                    if self.cover_uri.startswith("http:") or self.cover_uri.startswith("http:"):
                        self.cover_uri = g15cairo.get_image_cache_file(self.cover_uri, self.screen.driver.get_size()[0])
                else:
                    cover_image = self.get_default_cover()
                    logger.warning("Failed to loaded preferred cover art, falling back to default of %s" % cover_image)
                    if cover_image:
                        self.cover_uri = cover_image
                        self.cover_image = g15cairo.load_surface_from_file(self.cover_uri, self.screen.driver.get_size()[0])
                  
        # Track status
        if self.status == "Stopped":
            self.song_properties["stopped"] = True
            self.song_properties["icon"] = g15util.get_icon_path(["media-stop", "media-playback-stop", "gtk-media-stop", "player_stop" ], self.screen.height)
            self.song_properties["title"] = _("No track playing")
            self.song_properties["time_text"] = ""
        else:            
            if self.status == "Playing":
                if self.screen.driver.get_bpp() == 1:
                    self.thumb_image = g15cairo.load_surface_from_file(os.path.join(os.path.join(os.path.dirname(__file__), "default"), "play.gif"))
                else:
                    self.thumb_image = self.cover_image
                self.song_properties["playing"] = True
            else:
                if self.screen.driver.get_bpp() == 1:
                    self.thumb_image = g15cairo.load_surface_from_file(os.path.join(os.path.join(os.path.dirname(__file__), "default"), "pause.gif"))
                else:
                    self.thumb_image = self.cover_image                
                self.song_properties["paused"] = True
            self.song_properties["icon"] = self.cover_uri
            
    def get_default_cover(self):
        mime_type = mime.get_type(self.playing_uri)
        new_cover_uri = None
        if mime_type != None:
            mime_icon = g15util.get_icon_path(str(mime_type).replace("/","-"), size=self.screen.height)
            if mime_icon != None:                    
                new_cover_uri = mime_icon  
        if new_cover_uri != None:
            try :            
                new_cover_uri = "file://" + urllib.pathname2url(new_cover_uri)
            except :
                new_cover_uri = None
                              
        if new_cover_uri == None:                      
            new_cover_uri = g15util.get_icon_path(["audio-player", "applications-multimedia" ], size=self.screen.height)
            
        return new_cover_uri
        
    def recalc_progress(self):
        logger.debug("Recalculating progress")
        if not self.duration or self.duration < 1:
            self.song_properties["track_progress_pc"] = "0"
            self.song_properties["time_text"] = self.get_formatted_time(self.elapsed)
        else:
            pc = 100 / float(self.duration)
            val = int(pc * self.elapsed)
            self.song_properties["track_progress_pc"] = str(val)
            self.song_properties["time_text"] = self.get_formatted_time(self.elapsed) + " of " + self.get_formatted_time(self.duration)
            
        # Volume Icon
        vol_icon = "audio-volume-muted"
        if self.volume > 0.0 and self.volume < 34.0:
            vol_icon = "audio-volume-low"
        elif self.volume >= 34.0 and self.volume < 67.0:
            vol_icon = "audio-volume-medium"
        elif self.volume >= 67.0:
            vol_icon = "audio-volume-high"
        self.song_properties["vol_icon"] = g15util.get_icon_path(vol_icon, self.screen.height)
        
        # For the bars on the G15 (the icon is too small, bars are better)
        for i in range(0, int( self.volume / 10 ) + 1, 1):            
            self.song_properties["bar" + str(i)] = True
            
            
    def get_formatted_time(self, seconds):
        return "%0d.%02d" % ( int (seconds / 60), int( seconds % 60 ) )
            
    def get_new_status(self):
        raise Exception("Not implemented.")
            
    def load_song_details(self):
        raise Exception("Not implemented.")
    
    def get_progress(self):
        raise Exception("Not implemented.")
    
    def get_volume(self):
        raise Exception("Not implemented.")
    
    def on_stop(self):
        raise Exception("Not implemented.")
    
    def _get_properties(self):
        return dict(self.song_properties)
    
class MPRIS1Player(AbstractMPRISPlayer):
    
    def __init__(self, gconf_client, screen, players, bus_name, session_bus, theme):
        self.timer = None
        root_obj = session_bus.get_object(bus_name, '/')                    
        root = dbus.Interface(root_obj, 'org.freedesktop.MediaPlayer')
        AbstractMPRISPlayer.__init__(self, gconf_client, screen, players, bus_name, session_bus, root.Identity(), theme)
        
        # There is no seek / position changed event in MPRIS1, so we poll        
        player_obj = session_bus.get_object(bus_name, '/Player')
        self.player = dbus.Interface(player_obj, 'org.freedesktop.MediaPlayer')            
        
        # Set the initial status
        self._get_elapsed()
        self.check_status()
        
        # Start polling for status, position and track changes        
        self.timer = g15scheduler.queue("mprisDataQueue-%s" % self.screen.device.uid, "UpdateTrackData", 1.0, self.update_track)
        session_bus.add_signal_receiver(self.track_changed_handler, dbus_interface = "org.freedesktop.MediaPlayer", signal_name = "TrackChange")
        
    def next_track(self):
        self.player.Next()
        
    def prev_track(self):
        self.player.Prev()
        
    def play_pause_track(self):
        status = self.player.GetStatus()
        if status[0] == 0:
            self.player.Pause()
        else:
            self.player.Play()
        
    def stop_track(self):
        self.player.Stop()
        
    def update_track(self):
        self._get_elapsed()
        self.playback_started = time.time()
        self.check_status()
        if self.status == "Playing":        
            self.timer = g15scheduler.queue("mprisDataQueue-%s" % self.screen.device.uid, "UpdateTrackData", 1.0, self.update_track)
        else:        
            self.timer = g15scheduler.queue("mprisDataQueue-%s" % self.screen.device.uid, "UpdateTrackData", 5.0, self.update_track)
        
    def on_stop(self):
        if self.timer != None:
            self.timer.cancel()
        self.session_bus.remove_signal_receiver(self.track_changed_handler, dbus_interface = "org.freedesktop.MediaPlayer", signal_name = "TrackChange")
        
    def track_changed_handler(self, detail):
        g15scheduler.queue("mprisDataQueue-%s" % self.screen.device.uid, "LoadTrackDetails", 1.0, self.load_and_draw)
        
    def load_and_draw(self):
        self.load_song_details()
        self.screen.redraw()
        
    def get_volume(self):
        return 50
        
    def get_new_status(self):        
        logger.debug("Getting status")
        status = self.player.GetStatus()
        if status[0] == 0:
            return "Playing"
        elif status[0] == 1:
            return "Paused"
        else:
            return "Stopped"
                     
    def load_song_details(self):        
        meta_data = self.player.GetMetadata()
        
        # Format properties that need formatting
        bitrate = g15python_helpers.value_or_default(meta_data,"audio-bitrate", 0)
        if str(bitrate) == "0":
            bitrate = ""            
        self.playing_uri = g15python_helpers.value_or_blank(meta_data,"location")
        self.duration = g15python_helpers.value_or_default(meta_data,"time", 0)
        if self.duration == 0:
            self.duration = g15python_helpers.value_or_default(meta_data,"mtime", 0) / 1000
                            
        # General properties                    
        self.song_properties = {
                                "status": self.status,
                                "uri": self.playing_uri,
                                "art_uri": g15python_helpers.value_or_blank(meta_data,"arturl"),
                                "title": g15python_helpers.value_or_blank(meta_data,"title"),
                                "genre": g15python_helpers.value_or_blank(meta_data,"genre"),
                                "track_no": g15python_helpers.value_or_blank(meta_data,"tracknumber"),
                                "artist": g15python_helpers.value_or_blank(meta_data,"artist"),
                                "album": g15python_helpers.value_or_blank(meta_data,"album"),
                                "bitrate": bitrate,
                                "rating": g15python_helpers.value_or_default(meta_data,"rating", 0.0),
                                "album_artist": g15python_helpers.value_or_blank(meta_data,"mb album artist"),
                                }
    
        self.process_properties()
            
    def get_progress(self):  
        return float(self.player.PositionGet()) / 1000.0
        
    def _get_elapsed(self):
        self.start_elapsed = float(self.player.PositionGet()) / float(1000)


class MPRIS2Player(AbstractMPRISPlayer):
    
    def __init__(self, gconf_client, screen, players, bus_name, session_bus, theme):
        self.last_properties = None
        self.tracks = []
        
        # Connect to DBUS        
        player_obj = session_bus.get_object(bus_name, '/org/mpris/MediaPlayer2')     
        self.player = dbus.Interface(player_obj, 'org.mpris.MediaPlayer2.Player')                   
        self.player_properties = dbus.Interface(player_obj, 'org.freedesktop.DBus.Properties')
        try:
            identity = self.player_properties.Get("org.mpris.MediaPlayer2", "Identity")
        except DBusException:
            # Set a default identity if we cannot get players identity
            Identity = "MPRIS2"
        
        # Connect to DBUS     
        self.track_list =  None   
        self.track_list_properties = None
        try:  
            self.track_list = dbus.Interface(player_obj, 'org.mpris.MediaPlayer2.TrackList')                   
            self.track_list_properties = dbus.Interface(self.track_list, 'org.freedesktop.DBus.Properties')
            self.load_track_list()
        except ( dbus.DBusException, KeyError ):
            pass
            
        if self.track_list is None:
            logger.info("No TrackList interface")     
        
        # Configure the initial state 
        AbstractMPRISPlayer.__init__(self, gconf_client, screen, players, bus_name, session_bus, identity, theme)
        
        session_bus.add_signal_receiver(self.properties_changed_handler, dbus_interface = "org.freedesktop.DBus.Properties", signal_name = "PropertiesChanged") 
        session_bus.add_signal_receiver(self.seeked, dbus_interface = "org.mpris.MediaPlayer2.Player", signal_name = "Seeked")
        
        # Set the initial status
        self.check_status()
        
        # Workarounds
        self.timer = None
        
        # xnoise doesn't send seeked signals, so we need to refresh
        if "xnoise" in bus_name:
            self.timer = g15scheduler.queue("mprisDataQueue-%s" % self.screen.device.uid, "UpdateTrackData", 1.0, self.update_track)
        
    def next_track(self):
        self.player.Next()
        
    def prev_track(self):
        self.player.Previous()
        
    def play_pause_track(self):
        self.player.PlayPause()
        
    def stop_track(self):
        self.player.Stop()
        
    def load_track_list(self):
        logger.info("Loading tracklist")        
        track_list_props = self.track_list_properties.GetAll("org.mpris.MediaPlayer2.TrackList")
        self.tracks = []
        for track in track_list_props["Tracks"]:
            logger.info("   Track %s" % track)
        
    def on_stop(self): 
        if self.timer:
            self.timer.cancel()
        self.session_bus.remove_signal_receiver(self.properties_changed_handler, dbus_interface = "org.freedesktop.DBus.Properties", signal_name = "PropertiesChanged") 
        self.session_bus.remove_signal_receiver(self.seeked, dbus_interface = "org.mpris.MediaPlayer2.Player", signal_name = "Seeked")        
        
    def get_new_status(self):        
        logger.debug("Getting status")
        status = self.player_properties.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus")
        logger.debug("Finished geting status")
        return status
                                
    def seeked(self, seek_time):    
        
        """
        This looks like some kind of timing problem with Banshee. It 
        sometimes sends 0 as the seektime, and rreading it immediately
        also sometimes returns 0. Introducing a short delay fixes
        the problem
        """
        if seek_time == 0:
            logger.warn("Received no progress in seeked event, working around problem")
            time.sleep(0.5)
            seek_time = self.get_progress() * 1000 * 1000
            
        self.start_elapsed = seek_time / 1000 / 1000
        
#        self.start_elapsed = self.get_progress()    
        logger.info("Seek changed to %f (%d)" % ( self.start_elapsed, seek_time ) )
        self.playback_started = time.time()
        self.recalc_progress()
        self.screen.redraw()
                
    def properties_changed_handler(self, something, properties, list):
        logger.info("Properties changed, '%s' scheduling a reload", str(properties))
        
        if "PlaybackStatus" in properties:
            self.set_status(properties["PlaybackStatus"])
            
        # Check if the track has changed
        meta = {}
        if "Metadata" in properties:
            meta = properties["Metadata"]
        if ( "xesam:url" in meta and meta["xesam:url"] != self.playing_uri ) or \
            ( "mpris:trackid" in meta and meta["mpris:trackid"] != self.playing_track_id ) or \
            ( "xesam:title" in meta and meta["xesam:title"] != self.playing_track_id ) or \
            ( "xesam:artist" in meta and meta["xesam:artist"] != self.playing_track_id ) or \
            ( "xesam:album" in meta and meta["xesam:album"] != self.playing_track_id ):
            
            """
            This doesn't seem right, but it stops the hanging problem when notify-lcd is enabled and 
            tracks change
            """            
            g15scheduler.schedule("loadMeta", 1.0, self.reset_elapsed)
            
        if "Volume" in properties:
            self.volume = int(properties["Volume"] * 100)
             
        if self.last_properties == None:
            self.last_properties = dict(properties)
        else:
            for key in properties:
                self.last_properties[key] = properties[key]
                
        if "Metadata" in self.last_properties:
            """
            This doesn't seem right, but it stops the hanging problem when notify-lcd is enabled and 
            tracks change
            """            
            g15scheduler.schedule("loadMeta", 1.0, self.load_meta)
            
    def _load_and_redraw(self):
        self.load_meta()
        self.schedule_redraw()
        
    def load_song_details(self):
        if not self.stopped:
            logger.info("Getting all song properties")
            properties = self.player_properties.Get("org.mpris.MediaPlayer2.Player", "Metadata")
            logger.info("Got all song properties")           
            self.last_properties = {"Metadata":properties}
            self.load_meta()
        
    def load_meta(self):
        logger.debug("Loading MPRIS2 meta data")
        meta_data = self.last_properties["Metadata"]
        
        # Format properties that need formatting
        bitrate = g15python_helpers.value_or_default(meta_data,"xesam:audioBitrate", 0)
        if bitrate == 0:
            bitrate = ""
        else:
            bitrate = str(bitrate / 1024)
        
        self.playing_uri = g15python_helpers.value_or_blank(meta_data,"xesam:url")
        self.playing_track_id = g15python_helpers.value_or_blank(meta_data,"mpris:trackid")
        self.playing_title = g15python_helpers.value_or_blank(meta_data,"xesam:title")
        self.playing_artist = g15python_helpers.value_or_blank(meta_data,"xesam:artist")
        self.playing_album = g15python_helpers.value_or_blank(meta_data,"xesam:album")
                            
        # General properties                    
        self.song_properties = {
                                "status": self.status,
                                "tracklist": len(self.tracks) > 0,
                                "uri": self.playing_uri,
                                "track_id": self.playing_track_id,
                                "title": g15python_helpers.value_or_blank(meta_data,"xesam:title"),
                                "art_uri": g15python_helpers.value_or_blank(meta_data,"mpris:artUrl"),
                                "genre": ",".join(list(g15python_helpers.value_or_empty(meta_data,"xesam:genre"))),
                                "track_no": g15python_helpers.value_or_blank(meta_data,"xesam:trackNumber"),
                                "artist": ",".join(list(g15python_helpers.value_or_empty(meta_data,"xesam:artist"))),
                                "album": g15python_helpers.value_or_blank(meta_data,"xesam:album"),
                                "bitrate": bitrate,
                                "rating": g15python_helpers.value_or_default(meta_data,"xesam:userRating", 0.0),
                                "album_artist": ",".join(list(g15python_helpers.value_or_empty(meta_data,"xesam:albumArtist"))),
                                }
    
        self.duration = g15python_helpers.value_or_default(meta_data, "mpris:length", 0) / 1000 / 1000
        self.process_properties()
        
    def get_volume(self):
        try:
            return int(self.player_properties.Get("org.mpris.MediaPlayer2.Player", "Volume") * 100)
        except DBusException as d:
            # Nuvola doesn't support the Volume property
            return 100
            
    def get_progress(self):
        if self.status == "Playing":
            try :
                # This call seems to be where it usually hangs, although not always?????
                return self.player_properties.Get("org.mpris.MediaPlayer2.Player", "Position") / 1000 / 1000
            except:
                pass
        return 0
    
    def update_track(self):
        logger.debug("Updating elapsed time")
        self.reset_elapsed()
        self.timer = g15scheduler.queue("mprisDataQueue-%s" % self.screen.device.uid, "UpdateTrackData", 1.0 if self.status == "Playing" else 5.0, self.update_track)
            
class G15MPRIS(g15plugin.G15Plugin):
    
    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15Plugin.__init__(self, gconf_client, gconf_key, screen)
        self.session_bus = None

    def activate(self):
        self.players = {}
        g15plugin.G15Plugin.activate(self)
        if self.session_bus == None:
            self.session_bus = dbus.SessionBus()
            self.session_bus.call_on_disconnection(self._dbus_disconnected)
            
            
        self.screen.key_handler.action_listeners.append(self) 
        self._discover()
        
        # Watch for players appearing and disappearing
        self.session_bus.add_signal_receiver(self._name_owner_changed,
                                     dbus_interface='org.freedesktop.DBus',
                                     signal_name='NameOwnerChanged')  
    
    def deactivate(self):
        g15plugin.G15Plugin.deactivate(self)
        self.screen.key_handler.action_listeners.remove(self)
        for key in self.players.keys():
            self.players[key].stop()
        g15scheduler.stop_queue("mprisDataQueue-%s" % self.screen.device.uid)
        self.session_bus.remove_signal_receiver(self._name_owner_changed,
                                     dbus_interface='org.freedesktop.DBus',
                                     signal_name='NameOwnerChanged')  
        
    def destroy(self):
        pass
        
    def action_performed(self, binding):
        vis_page = self.screen.get_visible_page()
        
        # First send to the visible player
        for p in self.players.values():
            if vis_page == p.page:                
                return p.action_performed(binding)
            
        # Now send to just the first player
        if len(self.players) > 0:
            return self.players.values()[0].action_performed(binding)
            
    def _name_owner_changed(self, name, old_owner, new_owner):
        logger.debug("Name owner changed for %s from %s to %s", name, old_owner, new_owner)
        if name.startswith("org.mpris.MediaPlayer2"):
            logger.info("MPRIS2 Name owner changed for %s from %s to %s", name, old_owner, new_owner)
            if new_owner == "" and name in self.players:
                self.players[name].stop()
            elif old_owner == "" and not name in self.players:
                self.players[name] = MPRIS2Player(self.gconf_client, self.screen, self.players, name, self.session_bus, self.create_theme())
        elif name.startswith("org.mpris."):
            logger.info("MPRIS1 Name owner changed for %s from %s to %s", name, old_owner, new_owner)
            if new_owner == "" and name in self.players:
                self.players[name].stop()
            elif old_owner == "" and not name in self.players:
                if not name in mpris_blacklist:
                    self.players[name] = MPRIS1Player(self.gconf_client, self.screen, self.players, name, self.session_bus, self.create_theme())
                else:
                    logger.info("%s is a blacklisted player, ignoring" % name)
        
    def _discover(self):
        # Find new players
        active_list = self.session_bus.list_names()
        for name in active_list:  
            if not name in mpris_blacklist:
                # MPRIS 2
                if not name in self.players and name.startswith("org.mpris.MediaPlayer2"):
                    self.players[name] = MPRIS2Player(self.gconf_client, self.screen, self.players, name, self.session_bus, self.create_theme())
                # MPRIS 1
                elif not name in self.players and name.startswith("org.mpris."):
                    self.players[name] = MPRIS1Player(self.gconf_client, self.screen, self.players, name, self.session_bus, self.create_theme())
            
    def _dbus_disconnected(self, connection):
        logger.debug("DBUS Disconnected")
        self.session_bus = None