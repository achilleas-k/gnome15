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

import alsaaudio
import select
import os
from threading import Thread

# Plugin details - All of these must be provided
id="volume"
name="Volume Monitor"
description="Popup the current volume when it changes"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://localhost"
has_preferences=False


''' 
This plugin displays a high priority screen when the volume is changed for a 
fixed number of seconds
'''

def create(gconf_key, gconf_client, screen):
    return G15Volume(screen)
            
class G15Volume():
    
    def __init__(self, screen):
        self.screen = screen
        self.volume = 0.0
        self.thread = None
        self.canvas = None
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
    
    def redraw(self):
        
        if self.canvas == None:
            self.canvas = self.screen.new_canvas(priority=g15screen.PRI_HIGH, id="Volume", hide_after = 3.0)
            self.screen.draw_current_canvas()
        else:
            self.screen.set_priority(self.canvas, g15screen.PRI_HIGH, hide_after = 3.0)
        
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
        
        self.canvas.clear()
                    
        width = self.screen.driver.get_size()[0]
        height = self.screen.driver.get_size()[1]
        
        gap = ( height - 25 ) / 2
        for j in range(0, int(volume / 4) + 1):
            x = ( width / 2 ) - 25 + ( j * 2 )
            self.canvas.draw_line([(x, height - gap), (x, height - gap - j) ])
            
        if mute:
            self.canvas.set_font_size(size=g15draw.FONT_SMALL)
            self.canvas.draw_text("Mute", (g15draw.CENTER, g15draw.CENTER), emboss="White")
        
        self.screen.draw(self.canvas)
            
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
        
    def run(self):
        try :
            while self.volume.activated:
                if self.poll.poll(5):
                    self.volume.redraw()
                    if not self.open.read():
                        break
        finally:
            self.poll.unregister(self.open)
            self.open.close()
 