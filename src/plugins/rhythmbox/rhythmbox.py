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
 
import gnome15.g15_daemon as g15daemon
import gnome15.g15_draw as g15draw
import gnome15.g15_screen as g15screen
import datetime
import time
from threading import Timer
import dbus
import os

# Plugin details - All of these must be provided
id="rhythmbox"
name="Rhythmbox"
description="Display information about currently playing track"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://localhost"
has_preferences=False

''' This simple plugin displays a digital clock
'''

def create(gconf_key, gconf_client, screen):
    return G15RhythmBox(screen)
            
class G15RhythmBox():
    
    ''' Lifecycle functions. You must provide activate and deactivate,
        the constructor and destructors are optional
    '''
    
    def __init__(self, screen):
        self.screen = screen;
        self.active = False
        self.session_bus = None
        self.canvas = None
        self.reset()
        self.hidden = True
        self.timer = None

    def activate(self):
        self.active = True
        self.draw_music()
    
    def deactivate(self):
        ''' 
        On deactivate, we must stop any screens we may have added to let the applet take over.
        This is called when the applet requires the screen for itself 
        '''
        self.active = False
        self.del_canvas()
        
    def stop_timer(self):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None
        
    def destroy(self):
        self.deactivate()
        
    ''' Functions specific to plugin
    ''' 
        
    def on_shown(self):
        self.hidden = False
        self.draw_music()
        
    def on_hidden(self):
        self.hidden = True
    
    def player_changed_handler(self, value):
        self.draw_music()
        
    def reset(self):
        self.playing = False
        self.playing_uri = None
        self.artist = None
        self.album = None
        self.song = None
        self.cover_image = None
        self.duration = None
        
    def del_canvas(self):
        if self.canvas != None:
            self.screen.del_canvas(self.canvas)
            self.canvas = None
    
    def draw_music(self):
        self.do_draw_music()
        
    def do_draw_music(self):
            
        if self.active:
            if self.session_bus == None:
                try:
                    self.session_bus = dbus.SessionBus()
                    self.session_bus.call_on_disconnection(self.dbus_disconnected)
                    self.proxy_obj = self.session_bus.get_object('org.gnome.Rhythmbox', '/org/gnome/Rhythmbox/Player')
        
                    self.session_bus.add_signal_receiver(self.player_changed_handler, dbus_interface = "org.gnome.Rhythmbox.Player", signal_name = "elapsedChanged")
                    self.session_bus.add_signal_receiver(self.player_changed_handler, dbus_interface = "org.gnome.Rhythmbox.Player", signal_name = "playingUriChanged")
                    self.session_bus.add_signal_receiver(self.player_changed_handler, dbus_interface = "org.gnome.Rhythmbox.Player", signal_name = "playingChanged")
            
                    self.shell_obj = self.session_bus.get_object('org.gnome.Rhythmbox', '/org/gnome/Rhythmbox/Shell')
                    self.player = dbus.Interface(self.proxy_obj, 'org.gnome.Rhythmbox.Player')
                    self.shell = dbus.Interface(self.shell_obj, 'org.gnome.Rhythmbox.Shell')
                                
                    timer = Timer(10, self.ping, ())
                    timer.name = "DBUSPing"
                    timer.start()
                    
                except Exception as e:
                    # Rhythmbox probably not running, try again in a bit
                    print "Error. " + str(e) + ", retrying in 10 seconds"
                    self.deactivate_and_retry()
                    
            if self.session_bus != None:                
                playing = False
                path = None
                try :
                    path = self.player.getPlayingUri()
                    playing = self.player.getPlaying()
                except dbus.DBusException:
                    # We have lost connection to Rhytmbox (it was probably closed). Deactivate the plugin and retry in a few seconds
                    if self.playing:
                        self.stop_playing()
                    self.deactivate_and_retry()
                    return
                
                # Determine if we now playing
                if not self.playing and playing:
                    # Now playing
                    self.playing = True
                    self.playing_uri = path                   
                    self.check_canvas()
                    self.load_song_details()                     
                    self.screen.set_priority(self.canvas, g15screen.PRI_HIGH, revert_after = 3.0)
                    return
                elif self.playing and not playing:
                    # Stop playing
                    self.stop_playing()
                    return
                elif self.playing and self.playing_uri != path:
                    self.playing_uri = path                  
                    self.check_canvas()
                    self.load_song_details()
                    self.screen.set_priority(self.canvas, g15screen.PRI_HIGH, revert_after = 3.0)
                    return
                elif self.canvas != None:      
                    try :                        
                        self.canvas.clear()
                                    
                        elapsed = self.player.getElapsed()
                        volume = self.player.getVolume() * 6
                        
                        if self.cover_image != None:
                            self.canvas.draw_image(self.cover_image, (0, 0,30,30))
                            
                        self.canvas.set_font_size(g15draw.FONT_SMALL)
                        
                        
                        if self.artist != None:
                            self.canvas.draw_text(self.artist,(g15draw.CENTER,0), emboss="White")
                        self.canvas.set_font_size(g15draw.FONT_TINY)
                        if self.song != None:
                            self.canvas.draw_text(self.song,(g15draw.CENTER,14), emboss="White")
                        if self.album != None:
                            self.canvas.draw_text(self.album,(g15draw.CENTER,22), emboss="White")  
                            
                        width = self.screen.driver.get_size()[0]    
                        if(self.duration < 1):
                            self.duration = 1
                        pc = float(width - 4) / float(self.duration)
                        val = int(pc * elapsed)
                        height = self.screen.driver.get_size()[1]  
                        
                        self.canvas.draw_box([(0, height - 12),(width - 1, height - 1)])
                        self.canvas.fill_box([(2, height - 10),(val, height - 3)])
                        self.canvas.draw_text(self.get_formatted_time(elapsed) + " of " + self.get_formatted_time(self.duration),(g15draw.CENTER,height - 9), emboss="White")
                        
                        for j in range(0, int(volume) + 1):
                            x = width - 12 + ( j * 2 )
                            self.canvas.draw_line([(x, 12), (x, 12 - ( j * 2 ) )])
                        
                        self.screen.draw(self.canvas)
                    except dbus.DBusException:
                        print "Error"
                
    def ping(self):
        try :
            self.player.getPlaying()            
            timer = Timer(10, self.ping, ())
            timer.setDaemon(True)
            timer.name = "PingTimer"
            timer.start()
        except dbus.DBusException:
            # We have lost connection to Rhytmbox (it was probably closed). Deactivate the plugin and retry in a few seconds
            self.deactivate_and_retry() 
                
    def dbus_disconnected(self, connection):
        print "DBUS Disconnected"
                
    def deactivate_and_retry(self):
        self.session_bus = None
        self.deactivate()
        timer = Timer(5, self.reactivate, ())
        timer.name = "RBRetryTimer"
        timer.start()
        
    def reactivate(self):
        self.activated = True
        self.draw_music()
                
    def stop_playing(self):
        self.playing = False
        self.playing_uri = None
        self.canvas.clear()
        self.canvas.set_font_size(g15draw.FONT_MEDIUM)
        self.canvas.draw_text("No tracks playing",(g15draw.CENTER,10))
        self.screen.set_priority(self.canvas, g15screen.PRI_HIGH)
        time.sleep(2.0)
        self.del_canvas()
        
    def load_song_details(self):
        self.song = self.shell.getSongProperties(self.playing_uri)['title']
        self.album = self.shell.getSongProperties(self.playing_uri)['album']
        self.artist = self.shell.getSongProperties(self.playing_uri)['artist']
        self.duration = self.shell.getSongProperties(self.playing_uri)['duration']
        image = self.shell.getSongProperties(self.playing_uri)['image']    
        cover_file = os.path.expanduser("~/.cache/rhythmbox/covers/" + self.artist + " - " + self.album + ".jpg")                
        if os.path.exists(cover_file):
            self.cover_image = self.canvas.process_image_from_file(cover_file, (30,30))
            
    def check_canvas(self):
        if self.canvas == None:            
            self.canvas = self.screen.new_canvas(on_shown=self.on_shown, on_hidden=self.on_hidden, id="Rhythmbox")
            self.screen.draw_current_canvas()
            
    def get_formatted_time(self, seconds):
        return "%0d.%02d" % ( int (seconds / 60), int( seconds % 60 ) )
        
    def lower(self):  
        print "Lower"
        self.screen.set_priority(self.canvas, g15screen.PRI_NORMAL)
        
