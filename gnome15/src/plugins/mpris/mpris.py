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
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
from threading import Lock
import dbus
import os

import xdg.Mime as mime
import urllib

# Plugin details - All of these must be provided
id="mpris"
name="Media Player"
description="Displays information about currently playing media. Requires " + \
    "a player that supports the MPRIS (version 1 or 2) specification. This " + \
    "includes Rhythmbox, Banshee (with a plugin), Audacious, VLC and others." + \
    "Supports multiple media players running at the same time, each gets " + \
    "their own screen."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False

def create(gconf_key, gconf_client, screen):
    return G15MPRIS(gconf_client, screen)


class AbstractMPRISPlayer():
    
    def __init__(self, gconf_client, screen, players, interface_name, session_bus, title):
        self.lock = Lock()
        self.stopped = False
        self.hidden = True
        self.title = title
        self.session_bus = session_bus
        self.page = None
        self.duration = 0
        self.screen = screen
        self.interface_name = interface_name
        self.players = players
        self.gconf_client = gconf_client     
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
        self.status = "Stopped"
        self.status_check_timer = None
        self.cover_image = None
        self.thumb_image = None
        self.song_properties = {}
        
    def check_status(self):        
        try :
            new_status = self.get_new_status()
            if new_status != self.status:
                self.status = new_status
                if self.status == "Playing":
                    self.show_page()
                elif self.status == "Paused":
                    if self.page != None:
                        self.load_song_details()
                        self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)
                    else:
                        self.show_page()
                elif self.status == "Stopped":
                    self.hide_page()
            else:
                if self.status == "Playing":   
                    self.recalc_progress()
                    self.screen.redraw(self.page)
                    
            self.status_check_timer = g15util.schedule(self.interface_name + " Status Check", 1.0, self.check_status)
        except dbus.DBusException:
            print "WARNING: Failed to check status, player must have closed."
            self.stop()
    
    def stop(self):
        self.lock.acquire()
        try :
            self.stopped = True
            self.on_stop()
            if self.status_check_timer != None:
                self.status_check_timer.cancel()
            if self.page != None:
                self.hide_page()
            del self.players[self.interface_name]
        finally:
            self.lock.release()
    
    def show_page(self):
        self.load_song_details()
        self.page = self.screen.get_page(id="MPRIS%s" % self.title)
        if self.page == None:
            self.page = self.screen.new_page(self.paint, on_shown=self.on_shown, on_hidden=self.on_hidden, id="MPRIS%s" % self.title, panel_painter = self.paint_thumbnail, thumbnail_painter = self.paint_thumbnail)
            self.page.set_title(self.title)
            self.screen.redraw(self.page)
        else:
            self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)
        
    def hide_page(self):
        self.screen.del_page(self.page)    
        self.page = None    
        
    def on_shown(self):
        self.hidden = False
        
    def on_hidden(self):
        self.hidden = True
        
    def paint(self, canvas):
        self.lock.acquire()
        try :
            properties = dict(self.song_properties)
            self.theme.draw(canvas, properties) 
        finally:
            self.lock.release()
    
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None:
            if self.thumb_image != None:
                size = g15util.paint_thumbnail_image(allocated_size, self.thumb_image, canvas)
                return size
            
    def process_properties(self):
        self.recalc_progress()
        # Find the best icon for the media
        
        if "art_uri" in self.song_properties and self.song_properties["art_uri"] != "":
            self.cover_uri = self.song_properties["art_uri"]
        else:   
            cover_art = os.path.expanduser("~/.cache/rhythmbox/covers/" + self.song_properties["artist"] + " - " + self.song_properties["album"] + ".jpg")
            self.cover_uri = None
            if cover_art != None and os.path.exists(cover_art):
                self.cover_uri = cover_art
            else:
                mime_type = mime.get_type(self.playing_uri)
                if mime_type != None:
                    mime_icon = g15util.get_icon_path(str(mime_type).replace("/","-"), size=self.screen.height)
                    if mime_icon != None:                    
                        self.cover_uri = mime_icon                    
                if self.cover_uri == None:                      
                    self.cover_uri = g15util.get_icon_path(["audio-player", "applications-multimedia" ], size=self.screen.height)
            if self.cover_uri != None:            
                self.cover_uri = "file://" + urllib.pathname2url(self.cover_uri)
        self.cover_image = None
        self.thumb_image = None
        if self.cover_uri != None:
            self.cover_image = g15util.load_surface_from_file(self.cover_uri)
                  
        # Track status
        if self.status == "Stopped":
            self.song_properties["stopped"] = True
            self.song_properties["icon"] = g15util.get_icon_path("media-stop", self.screen.height)
            self.song_properties["title"] = "No track playing"
            self.song_properties["time_text"] = ""
        else:            
            if self.status == "Playing":
                if self.screen.driver.get_bpp() == 1:
                    self.thumb_image = g15util.load_surface_from_file(os.path.join(os.path.join(os.path.dirname(__file__), "default"), "play.gif"))
                self.song_properties["playing"] = True
            else:
                if self.screen.driver.get_bpp() == 1:
                    self.thumb_image = g15util.load_surface_from_file(os.path.join(os.path.join(os.path.dirname(__file__), "default"), "pause.gif"))                
                self.song_properties["paused"] = True
            self.song_properties["icon"] = self.cover_uri
            
        
    def recalc_progress(self):
        self.get_progress()
        if(self.duration < 1):
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
    
    def on_stop(self):
        raise Exception("Not implemented.")
    
class MPRIS1Player(AbstractMPRISPlayer):
    
    def __init__(self, gconf_client, screen, players, interface_name, session_bus):
        root_obj = session_bus.get_object(interface_name, '/')                    
        root = dbus.Interface(root_obj, 'org.freedesktop.MediaPlayer')
        AbstractMPRISPlayer.__init__(self, gconf_client, screen, players, interface_name, session_bus, root.Identity())
        
        player_obj = session_bus.get_object(interface_name, '/Player')
        self.player = dbus.Interface(player_obj, 'org.freedesktop.MediaPlayer')        
        session_bus.add_signal_receiver(self.track_changed_handler, dbus_interface = "org.freedesktop.MediaPlayer", signal_name = "TrackChange")
        
        # Start checking the status
        self.check_status()
        
    def on_stop(self):
        self.session_bus.remove_signal_receiver(self.track_changed_handler, dbus_interface = "org.freedesktop.MediaPlayer", signal_name = "TrackChange")
        
    def track_changed_handler(self, detail):
        g15util.schedule("LoadTrackDetails", 1.0, self.load_and_draw)
        
    def load_and_draw(self):
        self.load_song_details()
        self.screen.redraw()
        
    def get_new_status(self):        
        status = self.player.GetStatus()
        if status[0] == 0:
            return "Playing"
        elif status[0] == 1:
            return "Paused"
        else:
            return "Stopped"
                     
    def load_song_details(self):        
        self.lock.acquire()
        try :            
            meta_data = self.player.GetMetadata()
            
            # Format properties that need formatting
            bitrate = g15util.value_or_default(meta_data,"audio-bitrate", 0)
            if str(bitrate) == "0":
                bitrate = ""            
            self.playing_uri = g15util.value_or_blank(meta_data,"location")
            self.duration = g15util.value_or_default(meta_data,"time", 0)
            if self.duration == 0:
                self.duration = g15util.value_or_default(meta_data,"mtime", 0) / 1000
                                
            # General properties                    
            self.song_properties = {
                                    "status": self.status,
                                    "uri": self.playing_uri,
                                    "art_uri": g15util.value_or_blank(meta_data,"arturl"),
                                    "title": g15util.value_or_blank(meta_data,"title"),
                                    "genre": g15util.value_or_blank(meta_data,"genre"),
                                    "track_no": g15util.value_or_blank(meta_data,"tracknumber"),
                                    "artist": g15util.value_or_blank(meta_data,"artist"),
                                    "album": g15util.value_or_blank(meta_data,"album"),
                                    "bitrate": bitrate,
                                    "rating": g15util.value_or_default(meta_data,"rating", 0.0),
                                    "album_artist": g15util.value_or_blank(meta_data,"mb album artist"),
                                    }
        
            self.process_properties()
        finally:
            self.lock.release()
            
    def get_progress(self):        
        self.elapsed = float(self.player.PositionGet()) / 1000.0
        self.volume = self.player.VolumeGet()


class MPRIS2Player(AbstractMPRISPlayer):
    
    def __init__(self, gconf_client, screen, players, interface_name, session_bus):
        
        # Connect to DBUS        
        player_obj = session_bus.get_object(interface_name, '/org/mpris/MediaPlayer2')     
        self.player = dbus.Interface(player_obj, 'org.mpris.MediaPlayer2.Player')                   
        self.player_properties = dbus.Interface(player_obj, 'org.freedesktop.DBus.Properties')
        props = self.player_properties.GetAll("org.mpris.MediaPlayer2")
        
        # Configure the initial state 
        AbstractMPRISPlayer.__init__(self, gconf_client, screen, players, interface_name, session_bus, props["Identity"] if "Identity" in props else "MPRIS2")
        
        session_bus.add_signal_receiver(self.properties_changed_handler, dbus_interface = "org.freedesktop.DBus.Properties", signal_name = "PropertiesChanged") 
        session_bus.add_signal_receiver(self.seeked, dbus_interface = "org.mpris.MediaPlayer2.Player", signal_name = "Seeked")
        
        # Start checking the status
        self.check_status()
        
        
    def on_stop(self): 
        self.session_bus.remove_signal_receiver(self.properties_changed_handler, dbus_interface = "org.freedesktop.DBus.Properties", signal_name = "PropertiesChanged") 
        self.session_bus.remove_signal_receiver(self.seeked, dbus_interface = "org.mpris.MediaPlayer2.Player", signal_name = "Seeked")        
        
    def get_new_status(self):
        return self.player_properties.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus")
                                
    def seeked(self, seek_time):
        self.recalc_progress()
        self.screen.redraw()
                
    def properties_changed_handler(self, something, properties, list):
        g15util.schedule("ReloadSongProperties", 0, self._reload)
        
    def _reload(self):
        self.load_song_details()
        self.screen.redraw()
        
    def load_song_details(self):
        self.lock.acquire()
        try :
            if not self.stopped:
                properties = self.player_properties.GetAll("org.mpris.MediaPlayer2.Player")
                meta_data = properties["Metadata"]
                
                # Format properties that need formatting
                bitrate = g15util.value_or_default(meta_data,"xesam:audioBitrate", 0)
                if bitrate == 0:
                    bitrate = ""
                else:
                    bitrate = str(bitrate / 1024)
                
                self.playing_uri = g15util.value_or_blank(meta_data,"xesam:url")            
                                    
                # General properties                    
                self.song_properties = {
                                        "status": self.status,
                                        "uri": self.playing_uri,
                                        "title": g15util.value_or_blank(meta_data,"xesam:title"),
                                        "art_uri": g15util.value_or_blank(meta_data,"mpris:artUrl"),
                                        "genre": ",".join(list(g15util.value_or_empty(meta_data,"xesam:genre"))),
                                        "track_no": g15util.value_or_blank(meta_data,"xesam:trackNumber"),
                                        "artist": ",".join(list(g15util.value_or_empty(meta_data,"xesam:artist"))),
                                        "album": g15util.value_or_blank(meta_data,"xesam:album"),
                                        "bitrate": bitrate,
                                        "rating": g15util.value_or_default(meta_data,"xesam:userRating", 0.0),
                                        "album_artist": ",".join(list(g15util.value_or_empty(meta_data,"xesam:albumArtist"))),
                                        }
            
                self.duration = g15util.value_or_default(meta_data, "mpris:length", 0) / 1000 / 1000
                self.process_properties()
        finally:
            self.lock.release()
            
    def get_progress(self):
        if self.status == "Playing":
            try :
                self.elapsed = self.player_properties.Get("org.mpris.MediaPlayer2.Player", "Position") / 1000 / 1000
            except:
                self.elapsed = 0.0
        else:
            self.elapsed = 0.0                     
        self.volume = self.player_properties.Get("org.mpris.MediaPlayer2.Player", "Volume") * 100
    
            
class G15MPRIS():
    
    def __init__(self, gconf_client, screen):
        self.screen = screen;
        self.gconf_client = gconf_client
        self.active = False
        self.session_bus = None
        self.players = {}

    def activate(self):
        if self.session_bus == None:
            self.session_bus = dbus.SessionBus()
            self.session_bus.call_on_disconnection(self.dbus_disconnected)
        self.discover()
    
    def deactivate(self):
        for key in self.players.keys():
            self.players[key].stop()
        self.discover_timer.cancel()
        
    def destroy(self):
        pass
        
    def discover(self):
        try:
            # Find new players
            active_list = self.session_bus.list_names()
            for name in active_list:        
                # MPRIS 2
                if not name in self.players and name.startswith("org.mpris.MediaPlayer2"):
                    self.players[name] = MPRIS2Player(self.gconf_client, self.screen, self.players, name, self.session_bus)
                # MPRIS 1                
                elif not name in self.players and name.startswith("org.mpris."):
                    self.players[name] = MPRIS1Player(self.gconf_client, self.screen, self.players, name, self.session_bus)

            # Remove old players
            for key in self.players.keys():
                if not key in active_list:
                    self.players[key].stop()
            
        except Exception as e:
            print "Error. " + str(e) + ", retrying in 10 seconds"
            
        self.discover_timer = g15util.schedule("DiscoverPlayers", 5.0, self.discover)
            
    def dbus_disconnected(self, connection):
        print "DBUS Disconnected"
        self.session_bus = None