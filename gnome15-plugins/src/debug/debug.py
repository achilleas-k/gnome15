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
_ = g15locale.get_translation("clock", modfile = __file__).ugettext

import gnome15.g15text as g15text
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import gnome15.g15plugin as g15plugin
import pango
import os

id="debug"
name=_("Debug")
description=_("Displays some information useful for debugging Gnome15")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]

_proc_status = '/proc/%d/status' % os.getpid()

_scale = {'kB': 1024.0, 'mB': 1024.0*1024.0,
          'KB': 1024.0, 'MB': 1024.0*1024.0}

def _VmB(VmKey):
    '''Private.
    '''
    global _proc_status, _scale
    # get pseudo file  /proc/<pid>/status
    try:
        t = open(_proc_status)
        v = t.read()
        t.close()
    except:
        return 0.0  # non-Linux?
    # get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
    i = v.index(VmKey)
    v = v[i:].split(None, 3)  # whitespace
    if len(v) < 3:
        return 0.0  # invalid format?
    # convert Vm value to bytes
    return float(v[1]) * _scale[v[2]]


def memory(since=0.0):
    '''Return memory usage in bytes.
    '''
    return _VmB('VmSize:') - since


def resident(since=0.0):
    '''Return resident memory usage in bytes.
    '''
    return _VmB('VmRSS:') - since


def stacksize(since=0.0):
    '''Return stack size in bytes.
    '''
    return _VmB('VmStk:') - since

def create(gconf_key, gconf_client, screen):
    return G15Debug(gconf_key, gconf_client, screen)

class G15Debug(g15plugin.G15RefreshingPlugin):
    
    def __init__(self, gconf_key, gconf_client, screen):
        g15plugin.G15RefreshingPlugin.__init__(self, gconf_client, gconf_key, screen, ["dialog-error"], id, name, refresh_interval = 1.0)
    
    def activate(self):
        self.text = g15text.new_text(self.screen)
        self.memory = 0
        self.resident = 0
        self.stack = 0
        self.only_refresh_when_visible = False
        g15plugin.G15RefreshingPlugin.activate(self)
        self.do_refresh()
    
    def deactivate(self):
        g15plugin.G15RefreshingPlugin.deactivate(self)
        
    def refresh(self):
        self.memory = memory()
        self.resident = resident()
        self.stack = stacksize()
    
    def get_theme_properties(self): 
        properties = g15plugin.G15RefreshingPlugin.get_theme_properties(self)
        properties["memory_b"] = "%f" % self.memory
        properties["memory_k"] = "%f" % ( self.memory / 1024 )
        properties["memory_mb"] = "%.2f" % ( self.memory / 1024 / 1024 )
        properties["memory_gb"] = "%.2f" % ( self.memory / 1024 / 1024 / 1024 )
        properties["resident_b"] = "%f" % self.resident
        properties["resident_k"] = "%f" % ( self.resident / 1024 )
        properties["resident_mb"] = "%.2f" % ( self.resident / 1024 / 1024 )
        properties["resident_gb"] = "%.2f" % ( self.memory / 1024 / 1024 / 1024 )
        properties["stack_b"] = "%f" % self.stack
        properties["stack_k"] = "%f" % ( self.stack / 1024 )
        properties["stack_mb"] = "%.2f" % ( self.stack / 1024 / 1024 )
        properties["stack_gb"] = "%.2f" % ( self.stack / 1024 / 1024 / 1024 )
        return properties
        
    def _paint_panel(self, canvas, allocated_size, horizontal):
        if self.page and not self.screen.is_visible(self.page):
            # Don't display the date or seconds on mono displays, not enough room as it is
            mem_mb = self.memory / 1024 / 1024
            res_mb = self.resident / 1024 / 1024
            if self.screen.driver.get_bpp() == 1:
                text = "%.2f %.2f" % ( mem_mb, res_mb ) 
                font_size = 8
                factor = 2
                font_name = g15globals.fixed_size_font_name
                x = 1
                gap = 1
            else:
                factor = 1 if horizontal else 2
                font_name = "Sans"
                text = "%.2f MiB\n%.2f MiB" % ( mem_mb, res_mb ) 
                font_size = allocated_size / 3
                x = 4
                gap = 8
                
            self.text.set_canvas(canvas)
            self.text.set_attributes(text, align = pango.ALIGN_CENTER, font_desc = font_name, \
                                     font_absolute_size = font_size * pango.SCALE / factor)
            x, y, width, height = self.text.measure()
            if horizontal: 
                if self.screen.driver.get_bpp() == 1:
                    y = 0
                else:
                    y = (allocated_size / 2) - height / 2
            else:      
                x = (allocated_size / 2) - width / 2
                y = 0
            self.text.draw(x, y)
            if horizontal:
                return width + gap
            else:
                return height + 4
    
