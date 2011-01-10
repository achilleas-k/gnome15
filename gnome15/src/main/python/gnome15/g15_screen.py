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
    
PRI_POPUP=999
PRI_EXCLUSIVE=100
PRI_HIGH=99
PRI_NORMAL=50
PRI_LOW=20
PRI_INVISIBLE=0

import g15_driver as g15driver
import g15_util as g15util
import g15_profile as g15profile
import time
import threading
import jobqueue 
import cairo

class G15Page():
    def __init__(self, plugin, painter, id, priority, time, on_shown=None, on_hidden=None, thumbnail_painter = None, panel_painter = None):
        self.id = id
        self.plugin = plugin
        self.title = self.id
        self.time = time
        self.thumbnail_painter = thumbnail_painter
        self.panel_painter = panel_painter
        self.on_shown = on_shown
        self.on_hidden = on_hidden
        self.priority = priority
        self.time = time
        self.value = self.priority * self.time
        self.painter = painter
        self.cairo = cairo 
        
    def set_title(self, title):
        self.title = title   
        for l in self.plugin.screen_change_listeners:
            l.title_changed(self, title)
        
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
        self.screen_change_listeners = []
        self.local_data = threading.local()
        self.local_data.surface = None
        
        # Draw the splash for when no other pages are visible
        self.jobqueue = jobqueue.JobQueue(name="RedrawQueue")
        self.cyclequeue = jobqueue.JobQueue(name="CycleQueue")
        
    def start(self):
        self.driver = self.applet.driver
        self.content_surface = None
        self.width = self.applet.driver.get_size()[0]
        self.height = self.applet.driver.get_size()[1]
        self.surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, self.width, self.height)
        self.size = ( self.width, self.height )
        self.available_size = (0, 0, self.size[0], self.size[1])
        
        self.page_model_lock = threading.RLock()
        self.pages = []
        self.visible_page = None
        self.old_canvas = None
        self.transition_function = None
        self.background_painter_function = None
        self.foreground_painter_function = None
        self.painter_function = None
        self.mkey = 1
        self.reverting = { }
        self.hiding = { }
           
        self.redraw()   

        
    def add_screen_change_listener(self, screen_change_listener):
        if not screen_change_listener in self.screen_change_listeners:
            self.screen_change_listeners.append(screen_change_listener)
        
    def remove_screen_change_listener(self, screen_change_listener):
        if screen_change_listener in self.screen_change_listeners:
            self.screen_change_listeners.remove(screen_change_listener)
        
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
        self.set_color_for_mkey()     
    
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
            
    def clear_popup(self):
        for page in self.pages:
            if page.priority == PRI_POPUP:
                # Drop the priority of other popups
                page.set_priority(PRI_LOW)
                break
        
    def new_page(self, painter, priority=PRI_NORMAL, on_shown=None, on_hidden=None, 
                 id="Unknown", thumbnail_painter = None, panel_painter = None):
        self.page_model_lock.acquire()
        try :
            self.clear_popup()
            if priority == PRI_EXCLUSIVE:
                for page in self.pages:
                    if page.priority == PRI_EXCLUSIVE:
                        print "WARNING: Another page is already exclusive. Lowering %s to HIGH" % id
                        priority = PRI_HIGH
                        break
            page = G15Page(self, painter, id, priority, time.time(), on_shown, on_hidden, thumbnail_painter, panel_painter)
            self.pages.append(page)   
            for l in self.screen_change_listeners:
                l.new_page(page) 
            return page
        finally:
            self.page_model_lock.release()            

    def hide_after(self, hide_after, page):
        if page.id in self.hiding:
            # If the page was already hiding, cancel previous timer
            self.hiding[page.id].cancel()
            del self.hiding[page.id]       
                      
        timer = g15util.schedule("HideScreen", hide_after, self.del_page, page)
        self.hiding[page.id] = timer
        return timer
    
    def set_priority(self, page, priority, revert_after=0.0, hide_after=0.0, do_redraw = True):
        self.page_model_lock.acquire()
        try :
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
                    timer = g15util.schedule("Revert", revert_after, self.set_priority, page, old_priority)
                    self.reverting[page.id] = (old_priority, timer)
                    return timer
                if hide_after != 0.0:       
                    return self.hide_after(hide_after, page)
        finally:
            self.page_model_lock.release()   
    
    def raise_page(self, page):
        if page.priority == PRI_LOW:
            page.set_priority(PRI_POPUP)
        else:
            page.set_time(time.time())
        self.redraw()
            
    def del_page(self, page):
        self.page_model_lock.acquire()
        try :
            if page != None:                
                # Remove any timers that might be running on this page
                if page.id in self.hiding:
                    self.hiding[page.id].cancel()
                    del self.hiding[page.id]
                if page.id in self.reverting:
                    self.reverting[page.id][1].cancel()
                    del self.reverting[page.id]                                             
            
                if page == self.visible_page:
                    callback = page.on_hidden
                    if callback != None:
                        callback()
                    self.visible_page = None
                self.pages.remove(page)                    
                self.redraw()                   
                for l in self.screen_change_listeners:
                    l.del_page(page) 
        finally:
            self.page_model_lock.release()
            
    def is_visible(self, page):
        return self._get_next_page_to_display() == page
    
    def get_visible_page(self):
        return self.visible_page

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
    
    
    '''
    Queued functions. 
    '''
    
    def cycle_to(self, page, transitions = True):
        self.cyclequeue.clear()
        self.cyclequeue.run(self._do_cycle_to, page, transitions)
            
    def cycle(self, number, transitions = True):
        self.cyclequeue.clear()
        self.cyclequeue.run(self._do_cycle, number, transitions) 
            
    def redraw(self, page = None, direction="up", transitions = True, redraw_content = True):
        current_page = self._get_next_page_to_display()
        if page != None and page == current_page and self.visible_page == page:
            # Drop any redraws that are not required
            self.jobqueue.clear()
        self.jobqueue.run(self._do_redraw, page, direction, transitions, redraw_content)
        
    def set_color_for_mkey(self):
        control = self.driver.get_control_for_hint(g15driver.HINT_DIMMABLE)
        if control != None and not isinstance(control.value, int):
            profile = g15profile.get_active_profile()
            if profile != None:
                rgb = profile.get_mkey_color(self.mkey - 1)
                if rgb != None:                    
                    control.value = rgb
                    self.driver.update_control(control)
                    return
            self.driver.set_control_from_configuration(control, self.applet.conf_client)
            self.driver.update_control(control)
            
    def get_current_surface(self):
        return self.local_data.surface
    
    def get_desktop_surface(self):        
        scale = self.get_desktop_scale()
        surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, self.width * scale, self.height * scale)
        ctx = cairo.Context(surface)
        tx =  ( float(self.width) - ( float(self.available_size[0] * scale ) ) ) / 2.0
        ctx.translate(-tx, 0)
        ctx.set_source_surface(self.surface)
        ctx.paint()
        return surface
    
    def get_desktop_scale(self):
        sx = float(self.available_size[2]) / float(self.width)
        sy = float(self.available_size[3]) / float(self.height)
        return min(sx, sy)
    
    '''
    Private functions
    '''
    
    def _draw_page(self, visible_page, direction="down", transitions = True, redraw_content = True):
        
        if self.applet.driver == None or not self.applet.driver.is_connected():
            return
        
        # Do not paint if the device has no LCD (i.e. G110)
        if self.applet.driver.get_bpp() == 0:
            return
        
        surface =  self.surface
        
        # If the visible page is changing, creating a new surface. Both surfaces are
        # then passed to any transition functions registered
        if visible_page != self.visible_page: 
            if visible_page.priority == PRI_NORMAL:   
                self.applet.conf_client.set_string("/apps/gnome15/last_page", visible_page.id)      
            surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, self.width, self.height)
            
        self.local_data.surface = surface
        canvas = cairo.Context (surface)
        canvas.set_antialias(self.applet.driver.get_antialias())
        rgb = self.applet.driver.get_color_as_ratios(g15driver.HINT_BACKGROUND, ( 255, 255, 255 ))
        canvas.set_source_rgb(rgb[0],rgb[1],rgb[2])
        canvas.rectangle(0, 0, self.width, self.height)
        canvas.fill()
        rgb = self.applet.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, ( 0, 0, 0 ))
        canvas.set_source_rgb(rgb[0],rgb[1],rgb[2])
        
        if self.background_painter_function != None:
            self.background_painter_function(canvas)
                
        old_page = None
        if visible_page != self.visible_page:            
            old_page = self.visible_page
            redraw_content = True
            if self.visible_page != None:
                self.visible_page = visible_page
                callback = self.visible_page.on_hidden
                if callback != None:
                    callback()
            else:                
                self.visible_page = visible_page
            if self.visible_page != None:
                callback = self.visible_page.on_shown
                if callback != None:
                    callback()
                    
            for l in self.screen_change_listeners:
                l.page_changed(self.visible_page)
            
        # Call the screen's painter
        if self.visible_page != None:
            callback = self.visible_page.painter
            if callback != None:
                     
                # Paint the content to a new surface so it can be cached
                if self.content_surface == None or redraw_content:
                    self.content_surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, self.width, self.height)
                    content_canvas = cairo.Context(self.content_surface)
                    callback(content_canvas)
                
                tx =  self.available_size[0]
                ty =  self.available_size[1]
                
                # Scale to the available space, and center
                sx = float(self.available_size[2]) / float(self.width)
                sy = float(self.available_size[3]) / float(self.height)
                scale = min(sx, sy)
                sx = scale
                sy = scale
                
                if tx == 0 and self.available_size[3] != self.size[1]:
                    sx = 1
                
                if ty == 0 and self.available_size[2] != self.size[0]:
                    sy = 1
                
                canvas.save()
                canvas.translate(tx, ty)
                canvas.scale(sx, sy)
                canvas.set_source_surface(self.content_surface)
                canvas.paint()
                canvas.restore()
            
            
        # Now paint the screen's foreground
        if self.foreground_painter_function != None:
            self.foreground_painter_function(canvas)
                
        # Run any transitions
        if transitions and self.transition_function != None and self.old_canvas != None:
            self.transition_function(self.old_surface, surface, old_page, self.visible_page, direction)
            
        # Now apply any global transformations and paint
        
        if self.painter_function != None:
            self.painter_function(surface)
        else:
            self.applet.driver.paint(surface)
            
        self.old_canvas = canvas
        self.old_surface = surface
            
    
    def _do_cycle_to(self, page, transitions = True):            
        self.page_model_lock.acquire()
        try :
            if page.priority == PRI_LOW:
                # Visible until the next popup, or it hides itself
                self.set_priority(page, PRI_POPUP)
            elif page.priority < PRI_LOW:
                self.clear_popup()
                # Up to the page to make itself stay visible
                self._draw_page(page, "down", transitions)
            else: 
                self.clear_popup()
                self._flush_reverts_and_hides()
                # Cycle within pages of the same priority
                page_list = self._get_pages_of_priority(page.priority)
                direction = "up"
                dir = 1
                diff = page_list.index(page)
                if diff >= ( len(page_list) / 2 ):
                    dir *= -1
                    direction = "down"
                self._cycle_pages(diff, page_list)
                self._do_redraw(page, direction=direction, transitions=transitions)
        finally:
            self.page_model_lock.release()
                
    def _do_cycle(self, number, transitions = True):            
        self.page_model_lock.acquire()
        try :
            self._flush_reverts_and_hides()
            self._cycle(number, transitions)
            dir = "up"
            if number < 0:
                dir = "down"
            self._do_redraw(self._get_next_page_to_display(), direction=dir, transitions=transitions)
        finally:
            self.page_model_lock.release()
            
    def _get_pages_of_priority(self, priority):
        p_pages = []
        for page in self._sort():
            if page.priority == PRI_NORMAL:
                p_pages.append(page)
        return p_pages
    
    def _cycle_pages(self, number, pages):
        if len(pages) > 0:                    
            if number < 0:
                for p in range(number, 0):                    
                    first_time = pages[0].time
                    for i in range(0, len(pages) - 1):
                        pages[i].set_time(pages[i + 1].time)
                    pages[len(pages) - 1].set_time(first_time)
            else:                         
                for p in range(0, number):
                    last_time = pages[len(pages) - 1].time
                    for i in range(len(pages) - 1, 0, -1):
                        pages[i].set_time(pages[i - 1].time)
                    pages[0].set_time(last_time)
            
    def _cycle(self, number, transitions = True):
        if len(self.pages) > 0:            
            self._cycle_pages(number,  self._get_pages_of_priority(PRI_NORMAL))
                
    def _do_redraw(self, page = None, direction="up", transitions = True, redraw_content = True):
        self.page_model_lock.acquire()   
        try :           
            current_page = self._get_next_page_to_display()
            if page == None or page == current_page:
                self._draw_page(current_page, direction, transitions, redraw_content)
        finally:
            self.page_model_lock.release()
            
    def _flush_reverts_and_hides(self):        
        self.page_model_lock.acquire()
        try :
            for page_id in self.reverting:
                (old_priority, timer) = self.reverting[page_id]
                timer.cancel()                
                self.set_priority(self.get_page(page_id), old_priority)
            self.reverting = {}
            for page_id in self.hiding:
                timer = self.hiding[page_id]
                timer.cancel()
                self.del_page(self.get_page(page_id))                
            self.hiding = {}
        finally:
            self.page_model_lock.release()   
        
    def _sort(self):
        return sorted(self.pages, key=lambda page: page.value, reverse=True)
    
    def _get_next_page_to_display(self):
        self.page_model_lock.acquire()
        try :
            srt = sorted(self.pages, key=lambda key: key.value, reverse = True)
            if len(srt) > 0 and srt[0].priority != PRI_INVISIBLE:
                return srt[0]
        finally:            
            self.page_model_lock.release()
        