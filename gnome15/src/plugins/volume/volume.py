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
import gnome15.g15_driver as g15driver

import alsaaudio
import select
import os
from threading import Thread

# Plugin details - All of these must be provided
id="volume"
name="Volume Monitor"
description="Popup the current volume when it changes. Currently only the " \
        + "the master mixer of the default card is displayed."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110 ]


''' 
This plugin displays a high priority screen when the volume is changed for a 
fixed number of seconds
'''

def create(gconf_key, gconf_client, screen):
    return G15Volume(screen, gconf_client)
            
class G15Volume():
    
    def __init__(self, screen, gconf_client):
        self.screen = screen
        self.gconf_client = gconf_client
        self.volume = 0.0
        self.thread = None
        self.mute = False

    def activate(self):
        self.activated = True
        self.thread = VolumeThread(self).start()
    
    def deactivate(self):
        self.activated = False
        if self.thread != None:
            self.thread.stop_monitoring()
        
    def destroy(self):
        pass
        
    ''' Functions specific to plugin
    ''' 
    
    def del_canvas(self):
        self.screen.del_canvas(self.canvas)
        self.canvas = None
        
    def reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
        
    def paint(self, canvas):
                    
        width = self.screen.width
        height = self.screen.height
        
        properties = {}
        
        icon = "audio-volume-muted"
        if not self.mute:
            if self.volume < 34:
                icon = "audio-volume-low"
            elif self.volume < 67:
                icon = "audio-volume-medium"
            else:
                icon = "audio-volume-high"
        else:
            properties [ "muted"] = True
        
        icon_path = g15util.get_icon_path(icon, height)
        
        properties["state"] = icon
        properties["icon"] = icon_path
        properties["vol_pc"] = self.volume
        
        for i in range(0, ( self.volume / 10 ) + 1, 1):            
            properties["bar" + str(i)] = True
        
        self.theme.draw(canvas, properties)
    
    def popup(self):
        page = self.screen.get_page("Volume")
        if page == None:
            self.reload_theme()
            page = self.screen.new_page(self.paint, priority=g15screen.PRI_HIGH, id="Volume")
            self.screen.hide_after(3.0, page)
        else:
            self.screen.raise_page(page)
            self.screen.hide_after(3.0, page)
        
        vol_mixer = alsaaudio.Mixer("Master", cardindex=0)

        # Handle mute        
        mute = False
        mutes = None
        try :
            mutes = vol_mixer.getmute()
        except alsaaudio.ALSAAudioError:
            # Some pulse weirdness maybe?
            mute_mixer = alsaaudio.Mixer("PCM", cardindex=0)
            try :
                mutes = mute_mixer.getmute()
            except alsaaudio.ALSAAudioError:
                print "WARNING: No mute switch found"
        if mutes != None:        
            for ch_mute in mutes:
                if ch_mute:
                    mute = True

        
        # TODO  better way than averaging
        volumes = vol_mixer.getvolume()
        total = 0
        for vol in volumes:
            total += vol
        volume = total / len(volumes)
        
        self.volume = volume                
        self.mute = mute
        
        self.screen.redraw(page)
            
class VolumeThread(Thread):
    def __init__(self, volume):
        Thread.__init__(self)
        self.name = "VolumeThread"
        self.setDaemon(True)
        self.volume = volume
        self.mixer = alsaaudio.Mixer("Master", cardindex=0)
        self.poll_desc = self.mixer.polldescriptors()
        self.poll = select.poll()
        self.fd = self.poll_desc[0][0]
        self.event_mask = self.poll_desc[0][1]
        self.open = os.fdopen(self.fd)
        self.poll.register(self.open, select.POLLIN)
        
    def stop_monitoring(self):
        self.open.close()
        self.mixer.close()
        
    def run(self):
        try :
            while self.volume.activated:
                if self.poll.poll(5):
                    self.volume.popup()
                    if not self.open.read():
                        break
        finally:
            self.poll.unregister(self.open)
            self.open.close()
 