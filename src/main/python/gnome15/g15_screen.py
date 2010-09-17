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
  
PRI_HIGH=99
PRI_NORMAL=50
PRI_LOW=1

import g15_draw as g15draw
import g15_daemon as g15daemon
import g15_driver as g15driver
import time
from operator import itemgetter, attrgetter
import threading

class G15Page():
    def __init__(self, id, priority, time, canvas, on_shown=None, on_hidden=None):
        self.id = id
        self.time = time
        self.canvas = canvas
        self.on_shown = on_shown
        self.on_hidden = on_hidden
        self.priority = priority
        self.time = time
        self.value = self.priority * self.time
        
    def set_priority(self, priority):
        self.priority = priority
        self.value = self.priority * self.time
        
    def set_time(self, time):
        self.time = time
        self.value = self.priority * self.time
        
    def get_val(self):
        return self.time * self.priority

class G15Screen():
    
    def __init__(self, driver):
        self.lock = threading.Lock()
        self.pages = []
        self.current_canvas = None
        self.transition_function = None
        self.painter_function = None
        self.driver = driver
        self.timer = None
        
        # Draw the splash for when no other screens are visible
        self.splash_canvas = g15draw.G15Draw(self.driver)
        self.splash_canvas.set_font_size(g15draw.FONT_LARGE)
        self.splash_canvas.clear(color="Black")
        self.splash_canvas.draw_text("Gnome15", (g15draw.CENTER, g15draw.CENTER), emboss="White")
        
        self.draw_current_canvas()
        
    def get_mkey(self):
        return self.mkey
        
    def set_mkey(self, mkey):
        self.mkey = mkey
        val = 0
        if self.mkey == 1:
            val = g15driver.MKEY_LIGHT_1
        elif self.mkey == 2:
            val = g15driver.MKEY_LIGHT_2
        elif self.mkey == 3:
            val = g15driver.MKEY_LIGHT_3
        self.driver.set_mkey_lights(val)   
    
    def handle_key(self, key, state, post=False):
        # Requires long press of L1 to cycle
        if not post and state == g15driver.KEY_STATE_DOWN:
            if key & g15driver.G15_KEY_L1 != 0:
                self.cycle(1)
                pass
        return False
            
    def cycle(self, number, transitions = True):
        if len(self.pages) > 0:
            
            norms = []
            
            # We only cycle pages of normal priority
            for page in self.sort():
                if page.priority == PRI_NORMAL:
                    norms.append(page)
            
            if len(norms) > 0:
                if number < 0:                    
                    first_time = norms[0].time
                    for i in range(0, len(norms) - 1):
                        norms[i].set_time(norms[i + 1].time)
                    norms[len(norms) - 1].set_time(first_time)
                    self.draw_current_canvas(direction="down", transitions=transitions)
                else:                         
                    last_time = norms[len(norms) - 1].time
                    for i in range(len(norms) - 1, 0, -1):
                        norms[i].set_time(norms[i - 1].time)
                    norms[0].set_time(last_time)
                    self.draw_current_canvas(direction="up", transitions=transitions)
            else:                    
                self.draw_current_canvas(direction=None, transitions=transitions) 
                
    def index(self, canvas):
        i = 0
        for screen in self.pages:
            if screen.canvas== canvas:
                return i
            i = i + 1
        return i
    
    def get_canvas(self, id):
        for page in self.pages:
            if page.id == id:
                return page.canvas
        
    def new_canvas(self, priority=PRI_NORMAL, on_shown=None, on_hidden=None, id="Unknown", hide_after=0.0):
        draw = g15draw.G15Draw(self.driver)
        page = G15Page(id, priority, time.time(), draw, on_shown, on_hidden)
        self.pages.append(page)    
        if hide_after != 0.0:
            return (self.hide_after(hide_after, draw), draw)
        return draw

    def hide_after(self, hide_after, draw):
        timer = threading.Timer(hide_after, self.del_canvas, ([draw]))
        timer.setDaemon(True)
        timer.name = "HideScreenTimer"
        timer.start()
        return timer
    
    def set_priority(self, canvas, priority, revert_after=0.0, hide_after=0.0):
        page = self.get_page(canvas) 
        if page != None:
            old_priority = page.priority
            page.set_priority(priority)
            self.draw_current_canvas()        
            if revert_after != 0.0:                    
                timer = threading.Timer(revert_after, self.set_priority, ([canvas, old_priority]))
                timer.start()
                return timer
            if hide_after != 0.0:                    
                return self.hide_after(hide_after, canvas)
    
    def raise_page(self, canvas):
        self.get_page(canvas).set_time(time.time())
        self.draw_current_canvas()
            
    def del_canvas(self, canvas):
        screen = self.get_page(canvas)
        if screen != None:
            if canvas == self.current_canvas:
                callback = self.get_page(canvas).on_hidden
                if callback != None:
                    callback()
                self.current_canvas = None
            self.pages.remove(screen)
            self.draw_current_canvas()
            
    def get_current_canvas(self):
        if len(self.pages) == 0:
            return self.splash_canvas
        else:
            srt = self.sort()
            screen = srt[0]
            screen_canvas = screen.canvas
            return screen_canvas
        
    def sort(self):
        return sorted(self.pages, key=lambda page: page.value, reverse=True)
                
    def draw(self, canvas, cycle_to = False, transitions = True):
        if canvas == self.current_canvas:
            self.draw_canvas(canvas, transitions)
        elif cycle_to == True:
            dir = 1
            if self.index(canvas) > self.index(self.current_canvas):
                dir = -1
            while canvas != self.current_canvas:
                self.cycle(dir, transitions)

    def get_page(self, canvas):
        for screen in self.pages:
            if canvas == screen.canvas:
                return screen
        return None
    
    def set_painter(self, painter_function):
        o_painter = self.painter_function
        self.painter_function = painter_function
        return o_painter

    def set_transition(self, transition_function):
        o_transition = self.transition_function
        self.transition_function = transition_function
        return o_transition
        
    def draw_current_canvas(self, direction=None, transitions = True):
        visible_canvas = self.get_current_canvas()
        self.draw_canvas(visible_canvas, direction, transitions=transitions)
        
    def draw_canvas(self, visible_canvas, direction="down", transitions = True):        
        # Only send callbacks if not the splash screen
        if visible_canvas != self.current_canvas:
            old_canvas = self.current_canvas
            
            self.lock.acquire()
            try :
                if self.current_canvas != None and self.current_canvas != self.splash_canvas:
                    callback = self.get_page(self.current_canvas).on_hidden
                    if callback != None:
                        callback()
                self.current_canvas = visible_canvas
                if self.current_canvas != self.splash_canvas:
                    callback = self.get_page(self.current_canvas).on_shown
                    if callback != None:
                        callback()
                
                if transitions and self.transition_function != None and old_canvas != None:
                    self.transition_function(self.get_page(old_canvas), self.get_page(self.current_canvas), direction)
            finally:
                self.lock.release()
            
        if self.painter_function != None:
            self.painter_function(self.current_canvas.img)
        else:
            self.driver.paint(self.current_canvas.img)