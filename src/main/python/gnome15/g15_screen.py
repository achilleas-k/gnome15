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
  
PRI_EXCLUSIVE=100
PRI_HIGH=99
PRI_NORMAL=50
PRI_LOW=1

import g15_driver as g15driver
import time
import threading
import jobqueue 
import cairo

class G15Page():
    def __init__(self, painter, id, priority, time, on_shown=None, on_hidden=None, cairo = False):
        self.id = id
        self.time = time
        self.on_shown = on_shown
        self.on_hidden = on_hidden
        self.priority = priority
        self.time = time
        self.value = self.priority * self.time
        self.painter = painter
        self.cairo = cairo
        
    def set_priority(self, priority):
        self.priority = priority
        self.value = self.priority * self.time
        
    def set_time(self, time):
        self.time = time
        self.value = self.priority * self.time
        
    def get_val(self):
        return self.time * self.priority
    
class G15Screen():
    
    def __init__(self, applet):
        self.applet = applet
        
        # The screen may take a little space for its own purposes
        self.width = self.applet.driver.get_size()[0]
        self.height = self.applet.driver.get_size()[1]
        self.size = ( self.width, self.height )
        self.available_size = self.size
        
        self.lock = threading.Lock()
        self.pages = []
        self.current_page = None
        self.old_canvas = None
        self.transition_function = None
        self.background_painter_function = None
        self.foreground_painter_function = None
        self.painter_function = None
        self.driver = applet.driver
        self.timer = None
        self.mkey = 1
        self.reverting = { }
        
        # Draw the splash for when no other pages are visible
        self.jobqueue = jobqueue.JobQueue(name="ScreenRedrawQueue")
           
        self.redraw()   
        
    def set_available_size(self, size):
        self.available_size = size
        self.redraw()
        
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
        self.applet.driver.set_mkey_lights(val)   
    
    def handle_key(self, keys, state, post=False):
        # Requires long press of L1 to cycle
        if not post and state == g15driver.KEY_STATE_UP:
            if g15driver.G_KEY_M1 in keys:
                self.set_mkey(1)
            elif g15driver.G_KEY_M2 in keys:
                self.set_mkey(2)
            elif g15driver.G_KEY_M3 in keys:
                self.set_mkey(3)
                
        return False
            
    def cycle(self, number, transitions = True):
        self.jobqueue.run(self.do_cycle, number, transitions)
        
    def do_cycle(self, number, transitions = True):
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
                    self.do_redraw(direction="down", transitions=transitions)
                else:                         
                    last_time = norms[len(norms) - 1].time
                    for i in range(len(norms) - 1, 0, -1):
                        norms[i].set_time(norms[i - 1].time)
                    norms[0].set_time(last_time)
                    self.do_redraw(direction="up", transitions=transitions)
            else:                    
                self.do_redraw(direction=None, transitions=transitions) 
                
    def index(self, page):
        i = 0
        for p in self.pages:
            if p == page:
                return i
            i = i + 1
        return i
    
    def get_page(self, id):
        for page in self.pages:
            if page.id == id:
                return page
        
    def new_page(self, painter, priority=PRI_NORMAL, on_shown=None, on_hidden=None, id="Unknown", hide_after=0.0, use_cairo=False):
        if priority == PRI_EXCLUSIVE:
            for page in self.pages:
                if page.priority == PRI_EXCLUSIVE:
                    print "WARNING: Another page is already exclusive. Lowering %s to HIGH" % id
                    priority = PRI_HIGH
                    break
        page = G15Page(painter, id, priority, time.time(), on_shown, on_hidden, use_cairo)
        self.pages.append(page)    
        if hide_after != 0.0:
            return (self.hide_after(hide_after, draw), draw)
        return page

    def hide_after(self, hide_after, page):
        timer = threading.Timer(hide_after, self.del_page, ([page]))
        timer.setDaemon(True)
        timer.name = "HideScreenTimer"
        timer.start()
        return timer
    
    def set_priority(self, page, priority, revert_after=0.0, hide_after=0.0, do_redraw = True):
        if page != None:
            old_priority = page.priority
            page.set_priority(priority)
            if do_redraw:
                self.redraw()        
            if revert_after != 0.0:
                # If the page was already reverting, restore the priority and cancel the timer
                if page.id in self.reverting:
                    old_priority = self.reverting[page.id][0]
                    self.reverting[page.id][1].cancel()
                    del self.reverting[page.id]                                        
                    
                # Start a new timer to revert
                timer = threading.Timer(revert_after, self.set_priority, ([page, old_priority]))
                self.reverting[page.id] = (old_priority, timer)
                timer.start()
                return timer
            if hide_after != 0.0:                    
                return self.hide_after(hide_after, page)
    
    def raise_page(self, canvas):
        self.get_page(canvas).set_time(time.time())
        self.redraw()
            
    def del_page(self, page):
        if page != None:
            if page == self.current_page:
                callback = page.on_hidden
                if callback != None:
                    callback()
                self.current_page = None
            if page in self.pages:
                self.pages.remove(page)
            else:
                print "WARNING: Huh, page not in list of known pages. Probably a badly behaving plugin removing a page twice"
            self.redraw()
            
    def is_visible(self, page):
        return self.get_current_page() == page
            
    def get_current_page(self):
        srt = sorted(self.pages, key=lambda key: key.value, reverse = True)
        if len(srt) > 0:
            return srt[0]
        
    def sort(self):
        return sorted(self.pages, key=lambda page: page.value, reverse=True)
    
    def cycle_to(self, page, transitions = True):
        self.jobqueue.run(self.do_cycle_to, page, transitions)
        
    def do_cycle_to(self, page, transitions = True):
        dir = 1
        if self.pages.index(page) > self.pages.index(self.current_page):
            dir = -1
        while page != self.current_page:
            self.do_cycle(dir, transitions)
            
    def redraw(self, page = None, direction="up", transitions = True):
        self.jobqueue.run(self.do_redraw, page, direction, transitions)
                
    def do_redraw(self, page = None, direction="up", transitions = True):
        current_page = self.get_current_page()
        if page == None or page == current_page:
            self.draw_page(current_page, direction, transitions)

    def set_painter(self, painter):
        o_painter = self.painter_function
        self.painter_function = painter
        return o_painter
    
    def set_background_painter(self, background_painter):
        o_background_painter = self.background_painter_function
        self.background_painter_function = background_painter
        return o_background_painter
    
    def set_foreground_painter(self, foreground_painter):
        o_foreground_painter = self.foreground_painter_function
        self.foreground_painter_function = foreground_painter
        return o_foreground_painter
    
    def set_transition(self, transition):
        o_transition = self.transition_function
        self.transition_function = transition
        return o_transition
    
    def get_default_foreground_as_ratios(self):
        return self.get_color_as_ratios(g15driver.HINT_FOREGROUND, ( 255, 255, 255))
    
    def get_color_as_ratios(self, hint, default):
        return self.applet.driver.get_color_as_ratios(hint, default)
        
    def draw_page(self, visible_page, direction="down", transitions = True):        
        # Don't bother trying to paint if the driver is not connected
        if not self.applet.driver.is_connected():
            return
            
        # Everything is painted on top of white background
        surface =  cairo.ImageSurface (cairo.FORMAT_ARGB32, self.width, self.height)
        canvas = cairo.Context (surface)
        canvas.set_antialias(self.applet.driver.get_antialias())
        rgb = self.get_color_as_ratios(g15driver.HINT_BACKGROUND, ( 255, 255, 255 ))
        canvas.set_source_rgb(rgb[0],rgb[1],rgb[2])
        canvas.rectangle(0, 0, self.width, self.height)
        canvas.fill()
        rgb = self.get_color_as_ratios(g15driver.HINT_FOREGROUND, ( 0, 0, 0 ))
        canvas.set_source_rgb(rgb[0],rgb[1],rgb[2])
        
        if self.background_painter_function != None:
            self.background_painter_function(canvas)
                
        old_page = None
        if visible_page != self.current_page:
            old_page = self.current_page
            if self.current_page != None:
                self.current_page = visible_page
                callback = self.current_page.on_hidden
                if callback != None:
                    callback()
            else:                
                self.current_page = visible_page
            if self.current_page != None:
                callback = self.current_page.on_shown
                if callback != None:
                    callback()
        
        # Call the screen's painter
        if self.current_page != None:
            callback = self.current_page.painter
            if callback != None:
                
                # Scale to the available space, and center
                if self.available_size == self.size:
                    callback(canvas)
                else:
                    # Scale to the available space, and center
                    sx = float(self.available_size[0]) / float(self.width)
                    sy = float(self.available_size[1]) / float(self.height)
                    scale = min(sx, sy)
                    canvas.save()
                    tx =  ( float(self.width) - ( float(self.available_size[0] * scale ) ) ) / 2.0
                    ty =  0
                    canvas.translate(tx, ty)
                    canvas.scale(scale, scale)
                    callback(canvas)
                    canvas.restore()
            
            
        # Now paint the screen's foreground
        if self.foreground_painter_function != None:
            self.foreground_painter_function(canvas)
                
        # Run any transitions
        if transitions and self.transition_function != None and self.old_canvas != None:
            self.transition_function(self.old_surface, surface, old_page, self.current_page, direction)
            
        # Now apply any global transformations and paint
        
        if self.painter_function != None:
            self.painter_function(surface)
        else:
            self.applet.driver.paint(surface)
            
        self.old_canvas = canvas
        self.old_surface = surface