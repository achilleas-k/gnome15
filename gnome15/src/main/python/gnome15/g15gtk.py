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
 
'''
A top level GTK windows that draws on the LCD
'''
import gtk
import gobject
import g15driver as g15driver
import g15util as g15util
import g15cairo
from threading import Lock
from threading import Semaphore
import g15theme
import g15screen
import cairo
import ctypes


_initialized = False
def create_cairo_font_face_for_file (filename, faceindex=0, loadoptions=0):
    global _initialized
    global _freetype_so
    global _cairo_so
    global _ft_lib
    global _surface

    CAIRO_STATUS_SUCCESS = 0
    FT_Err_Ok = 0

    if not _initialized:

        # find shared objects
        _freetype_so = ctypes.CDLL ("libfreetype.so.6")
        _cairo_so = ctypes.CDLL ("libcairo.so.2")

        _cairo_so.cairo_ft_font_face_create_for_ft_face.restype = ctypes.c_void_p
        _cairo_so.cairo_ft_font_face_create_for_ft_face.argtypes = [ ctypes.c_void_p, ctypes.c_int ]
        _cairo_so.cairo_set_font_face.argtypes = [ ctypes.c_void_p, ctypes.c_void_p ]
        _cairo_so.cairo_font_face_status.argtypes = [ ctypes.c_void_p ]
        _cairo_so.cairo_status.argtypes = [ ctypes.c_void_p ]

        # initialize freetype
        _ft_lib = ctypes.c_void_p ()
        if FT_Err_Ok != _freetype_so.FT_Init_FreeType (ctypes.byref (_ft_lib)):
            raise "Error initialising FreeType library."

        class PycairoContext(ctypes.Structure):
            _fields_ = [("PyObject_HEAD", ctypes.c_byte * object.__basicsize__),
                ("ctx", ctypes.c_void_p),
                ("base", ctypes.c_void_p)]

        _surface = cairo.ImageSurface (cairo.FORMAT_A8, 0, 0)

        _initialized = True

    # create freetype face
    ft_face = ctypes.c_void_p()
    cairo_ctx = cairo.Context (_surface)
    cairo_t = PycairoContext.from_address(id(cairo_ctx)).ctx

    if FT_Err_Ok != _freetype_so.FT_New_Face (_ft_lib, filename, faceindex, ctypes.byref(ft_face)):
        raise Exception("Error creating FreeType font face for " + filename)

    # create cairo font face for freetype face
    cr_face = _cairo_so.cairo_ft_font_face_create_for_ft_face (ft_face, loadoptions)
    if CAIRO_STATUS_SUCCESS != _cairo_so.cairo_font_face_status (cr_face):
        raise Exception("Error creating cairo font face for " + filename)

    _cairo_so.cairo_set_font_face (cairo_t, cr_face)
    if CAIRO_STATUS_SUCCESS != _cairo_so.cairo_status (cairo_t):
        raise Exception("Error creating cairo font face for " + filename)

    face = cairo_ctx.get_font_face ()

    return face


class G15OffscreenWindow(g15theme.Component):
    
    def __init__(self, component_id):
        g15theme.Component.__init__(self, component_id)
        self.window = None
        self.content = None
        
    def on_configure(self):
        g15theme.Component.on_configure(self)        
        gobject.idle_add(self._create_window)
        self.get_screen().key_handler.action_listeners.append(self)
        
    def notify_remove(self):
        g15theme.Component.notify_remove(self)
        self.get_screen().key_handler.action_listeners.remove(self)
        
    def set_content(self, content):
        self.content = content
        if self.window is not None:
            gobject.idle_add(self._do_set_content)
            
    def action_performed(self, binding):
        if self.is_visible():
            if binding.action == g15driver.NEXT_SELECTION:
                gobject.idle_add(self.window.focus_next)
            elif binding.action == g15driver.PREVIOUS_SELECTION:
                gobject.idle_add(self.window.focus_previous)
            if binding.action == g15driver.NEXT_PAGE:
                gobject.idle_add(self.window.change_widget)
            elif binding.action == g15driver.PREVIOUS_PAGE:
                gobject.idle_add(self.window.change_widget, None, True)
            elif binding.action == g15driver.SELECT:
                pass
            
    def paint(self, canvas):
        g15theme.Component.paint(self, canvas)
        if self.window is not None:
            self.window.paint(canvas)
            
        
    """
    Private
    """
            
    def _do_set_content(self):
        self.window.set_content(self.content)
        
    def _create_window(self):     
        screen = self.get_screen()   
        window = G15Window(screen, self.get_root(), self.view_bounds[0], self.view_bounds[1], \
                           self.view_bounds[2], self.view_bounds[3])
        if self.content is not None:
            self.window.set_content(self.content)
        self.window = window
        screen.redraw(self.get_root())
        
class G15Window(gtk.OffscreenWindow):
    
    def __init__(self, screen, page, area_x, area_y, area_width, area_height):
        gtk.OffscreenWindow.__init__(self)
        self.pixbuf = None
        self.scroller = None
        self.screen = screen
        self.page = page
        self.lock = None      
        self.area_x = int(area_x)
        self.area_y = int(area_y)
        self.area_width = int(area_width)
        self.area_height = int(area_height)
        self.surface = None
        self.content = gtk.EventBox()
        self.set_app_paintable(True)
        self.content.set_app_paintable(True)        
        self.connect("screen-changed", self.screen_changed)
        self.content.connect("expose-event", self._transparent_expose)
        self.content.set_size_request(self.area_width, self.area_height)
        self.add(self.content)
        self.connect("damage_event", self._damage)
        self.connect("expose_event", self._expose)
        self.screen_changed(None, None)
        self.lock = Semaphore()
        
    def set_content(self, content):
        self.content.add(content)
        self.show_all()
        
        # If the content window is a scroller, we send focus events to it
        # moving the scroller position to the focussed component
        if isinstance(content, gtk.ScrolledWindow):
            self.scroller = content
        
    def paint(self, canvas):
        if g15util.is_gobject_thread():
            raise Exception("Painting on mainloop")
        self.start_for_capture()
        gobject.idle_add(self._do_capture)
        self.lock.acquire()
        canvas.save()
        canvas.translate(self.area_x, self.area_y)
        canvas.set_source_surface(self.surface)
        canvas.paint()
        canvas.restore()
            
    def focus_next(self):
        self.content.get_toplevel().child_focus(gtk.DIR_TAB_FORWARD)
        self.scroll_to_focussed()
        self.screen.redraw(self.page)
        
    def focus_previous(self):
        self.content.get_toplevel().child_focus(gtk.DIR_TAB_BACKWARD)
        self.screen.redraw(self.page)
        self.scroll_to_focussed()
        
    def change_widget(self, amount = None, reverse = False):
        focussed = self.get_focus()
        if focussed != None:
            if isinstance(focussed, gtk.HScale):
                adj = focussed.get_adjustment()
                ps = adj.get_page_size() if amount is None else amount
                if ps == 0:
                    ps = 10
                if reverse:
                    adj.set_value(adj.get_value() - ps)
                else:
                    adj.set_value(adj.get_value() + ps)
                self.screen.redraw(self.page)
        
    def show_all(self):
        gtk.OffscreenWindow.show_all(self)
        
    def scroll_to_focussed(self):
        if self.scroller is not None:
            hadj = self.scroller.get_hadjustment()
            vadj = self.scroller.get_vadjustment()
            x, y = self.get_focus().translate_coordinates(self.scroller.get_children()[0], 0, 0)
            max_x = hadj.upper - hadj.page_size
            max_y = vadj.upper - vadj.page_size
            hadj.set_value(min(x, max_x))
            vadj.set_value(min(y, max_y))

    def screen_changed(self, widget, old_screen=None):
        global supports_alpha
        
        # To check if the display supports alpha channels, get the colormap
        screen = self.get_screen()
        colormap = screen.get_rgba_colormap()
        if colormap == None:
            colormap = screen.get_rgb_colormap()
            supports_alpha = False
        else:
            supports_alpha = True
            
        # Now we have a colormap appropriate for the screen, use it
        self.set_colormap(colormap)
    
        return False
        
    def _transparent_expose(self, widget, event = None):
        """
        To overcome inability to set a container component as transparent. I 
        cannot get compositing working (perhaps it just doesn't because we are
        going to an offscreen window). So, to get pseudo-transparency,
        we repaint the background the screen would normally paint, offset by
        the position of this component
        """
        cr = widget.window.cairo_create()
        self.screen.clear_canvas(cr)
        cr.save()
        cr.translate(-self.area_x, -self.area_y)
        for s in self.screen.painters:
            if s.place == g15screen.BACKGROUND_PAINTER:
                s.paint(cr)
        cr.restore()
        return False
        
    def _expose(self, widget, event):
        self.screen.redraw(self.page)
        return False
        
    def _damage(self, widget, event):
#        print "Damage"
#        self.screen.redraw(self.page)
        return False
    
    def start_for_capture(self):
        self.lock = Lock()
        self.lock.acquire()
    
    def _do_capture(self):
        self.content.window.invalidate_rect((0,0,self.area_width,self.area_height), True)
        self.content.window.process_updates(True)
        pixbuf = gtk.gdk.Pixbuf( gtk.gdk.COLORSPACE_RGB, False, 8, self.area_width, self.area_height)
        pixbuf.get_from_drawable(self.content.window, self.content.get_colormap(), 0, 0, 0, 0, self.area_width, self.area_height)
        self.surface = g15cairo.pixbuf_to_surface(pixbuf)
        self.pixbuf = pixbuf        
        self.lock.release()