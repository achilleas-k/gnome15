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
 
import gnome15.g15screen as g15screen 
import gnome15.g15theme as g15theme 
import gnome15.g15util as g15util
import gnome15.g15driver as g15driver
import gtk
import os
import sys
import asyncore
import socket
from threading import Thread
import traceback
import ImageMath
import Image
import ImageOps
import array
import struct
import cairo
import gobject
import logging
logger = logging.getLogger("g15daemon")

# Plugin details - All of these must be provided
id="g15daemon-server"
name="G15Daemon Compatibility"
description="Starts a network server compatible with the g15daemon network protocol. " + \
            "This allows you to use g15daemon compatible scripts and applications on the G19."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=True
supported_models = [ g15driver.MODEL_G19 ]

# Client commands
CLIENT_CMD_GET_KEYSTATE=ord('k')
CLIENT_CMD_SWITCH_PRIORITIES=ord('p')
CLIENT_CMD_NEVER_SELECT=ord('n')
CLIENT_CMD_IS_FOREGROUND=ord('v')
CLIENT_CMD_IS_USER_SELECTED=ord('u')
CLIENT_CMD_KB_BACKLIGHT_COLOR=0x79
CLIENT_CMD_BACKLIGHT=0x80
CLIENT_CMD_KB_BACKLIGHT=0x8
CLIENT_CMD_CONTRAST=0x40
CLIENT_CMD_MKEY_LIGHTS=0x20


KEY_MAP = {
        g15driver.G_KEY_G1  : 1<<0,
        g15driver.G_KEY_G2  : 1<<1,
        g15driver.G_KEY_G3  : 1<<2,
        g15driver.G_KEY_G4  : 1<<3,
        g15driver.G_KEY_G5  : 1<<4,
        g15driver.G_KEY_G6  : 1<<5,
        g15driver.G_KEY_G7  : 1<<6,
        g15driver.G_KEY_G8  : 1<<7,
        g15driver.G_KEY_G9  : 1<<8,
        g15driver.G_KEY_G10 : 1<<9,
        g15driver.G_KEY_G11 : 1<<10,
        g15driver.G_KEY_G12 : 1<<11,
        
        g15driver.G_KEY_M1  : 1<<18,
        g15driver.G_KEY_M2  : 1<<19,
        g15driver.G_KEY_M3  : 1<<20,
        g15driver.G_KEY_MR  : 1<<21,
        
        # Map to L1-L5
        g15driver.G_KEY_UP     : 1<<22,
        g15driver.G_KEY_LEFT   : 1<<23,
        g15driver.G_KEY_OK     : 1<<24,
        g15driver.G_KEY_RIGHT  : 1<<25,
        g15driver.G_KEY_DOWN   : 1<<26,
        
        g15driver.G_KEY_LIGHT : 1<<27
        }

def create(gconf_key, gconf_client, screen):
    return G15DaemonServer(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "g15daemon-server.glade"))
    
    dialog = widget_tree.get_object("G15DaemonServerDialog")
    dialog.set_transient_for(parent)
    
    g15util.configure_adjustment_from_gconf(gconf_client, gconf_key + "/port", "PortAdjustment", 15550, widget_tree)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/keep_aspect_ratio", "KeepAspectRatio", False, widget_tree, True)
    
    dialog.run()
    dialog.hide()

class G15DaemonClient(asyncore.dispatcher):
    def __init__(self, conn, plugin):
        asyncore.dispatcher.__init__(self, sock=conn)
        self.out_buffer  = ""
        self.img_buffer = None
        self.buffer_type = None
        self.buffer_len = 0
        self.surface = None
 
        self.enable_keys = False
        self.plugin = plugin
        self.plugin.join(self)
        self.handshake = False
                
        self.page = g15theme.G15Page("G15Daemon%d" % self.plugin.screen_index, plugin.screen, self._paint)
        self.page.set_title("G15Daemon Screen %d" % self.plugin.screen_index)
        self.plugin.screen.add_page(self.page)
        self.plugin.screen_index += 1
        self.plugin.screen.redraw(self.page)
        
        self.out_buffer += "G15 daemon HELLO"
        self.oob_buffer = ""
        
    def handle_close(self):
        self.plugin.screen.del_page(self.page)
        self.plugin.leave(self)
        self.close()
        
    def handle_expt(self):
        data = self.socket.recv(1, socket.MSG_OOB)
        val = ord(data[0])
        
        if val == CLIENT_CMD_SWITCH_PRIORITIES: 
            self.plugin.screen.raise_page(self.page)
        elif val == CLIENT_CMD_NEVER_SELECT: 
            self.plugin.screen.set_priority(self, self.page, g15screen.PRI_LOW)
        elif val == CLIENT_CMD_IS_FOREGROUND:
            self.oob_buffer += "1" if self.plugin.screen.get_visible_page() == self.page else "0"
        elif val == CLIENT_CMD_IS_USER_SELECTED:
            self.oob_buffer += "1" if self.plugin.screen.get_visible_page() == self.page and self.page.priority == g15screen.PRI_NORMAL else "0"
        elif val & CLIENT_CMD_MKEY_LIGHTS > 0:
            self.screen.driver.set_mkey_lights(val - CLIENT_CMD_MKEY_LIGHTS)
        elif val & CLIENT_CMD_KEY_HANDLER > 0:
            # TODO - the semantics are slightly different here. gnome15 is already grabbing the keyboard, always.
            # So instead, we just only send keyboard events if the client requests this.
            self.enable_keys = True
        elif val & CLIENT_CMD_BACKLIGHT:
            level = val - CLIENT_CMD_BACKLIGHT
            if level == 0:
                bl = 0
            elif level == 1:
                bl = self.plugin.default_lcd_brightness / 2
            elif level == 2:
                bl = self.plugin.default_lcd_brightness
                
            control = self.screen.driver.get_control("lcd_brightness")
            control.value = bl            
            self.screen.driver.update_control(control)
        elif val & CLIENT_CMD_KB_BACKLIGHT:
            level = val - CLIENT_CMD_KB_BACKLIGHT
            if level == 0:
                bl = (0, 0, 0)
            elif level == 1:
                bl = ( self.plugin.default_backlight[0] / 2, self.plugin.default_backlight[1] / 2, self.plugin.default_backlight[2] / 2 )
            elif level == 2:
                bl = self.plugin.default_backlight
                
            control = self.screen.driver.get_control("backlight")
            control.value = bl            
            self.screen.driver.update_control(control)
        elif val & CLIENT_CMD_CONTRAST:
            logger.warning("Ignoring contrast command")
            

    def handle_read(self):
        if not self.handshake:
            buf_type = self.recv(4)
            
            self.buffer_type = buf_type[0]
            self.handshake = True
            self.img_buffer = ""
            
            if self.buffer_type == "G":
                self.buffer_len = 6880
            elif self.buffer_type == "R":
                self.buffer_len = 1048
# TODO
#            elif self.buffer_type == "W":
#                self.buffer_len = 865
            else:
                logger.warning("WARNING: Unsupported buffer type. Closing")
                self.handle_close()
                return
        else:        
            recv = self.recv(self.buffer_len - len(self.img_buffer))
            self.img_buffer += recv
            if len(self.img_buffer) == self.buffer_len:
                
                if self.buffer_type == "G":
                    self.img_buffer = self.convert_gbuf(self.img_buffer)
                    
                pil_img = Image.fromstring("1", (160,43), self.img_buffer)
                mask_img = pil_img.copy()                           
                mask_img = mask_img.convert("L")
                pil_img = pil_img.convert("P")
                pil_img.putpalette(self.plugin.palette)                              
                pil_img = pil_img.convert("RGBA")                        
                pil_img.putalpha(mask_img)                    

                # TODO find a quicker way of converting
                pixbuf = g15util.image_to_pixbuf(pil_img, "png")
                self.surface = g15util.pixbuf_to_surface(pixbuf)
                self.plugin.screen.redraw(self.page)
                
                self.img_buffer = ""

            elif len(self.img_buffer) > self.buffer_len:
                logger.warning('Received bad frame (%d bytes), should be %d' % ( len(self.img_buffer), self.buffer_len ) )
                
    def dump_buf(self, buf):
        i = 0
        for y in range(43):
            l = ""
            for x in range(160):
                if buf[ ( y * 160 ) + x ] == chr(0):
                    l += " "
                else:
                    l += "*"
            logger.info(l)
            
    def convert_gbuf(self, g_buffer):
        r_buffer = array.array('c', chr(0)*1048)
        new_buf = ""
        for x in range(160):
            for y in range(43):
                pixel_offset = y * 160 + x
                byte_offset = pixel_offset / 8
                bit_offset = 7 - (pixel_offset % 8)    
                val = ord(g_buffer[x + ( y * 160)])
                if val:
                    r_buffer[byte_offset] = chr(ord(r_buffer[byte_offset]) | 1 << bit_offset)
                else:
                    r_buffer[byte_offset] = chr(ord(r_buffer[byte_offset])  &  ~(1 << bit_offset))
        return r_buffer.tostring()
         
    def convert_rbuf(self, buffer):
        new_buf = ""
        for x in range(160):
            for y in range(43):
                pixel_offset = y * 143 + x
                byte_offset = pixel_offset / 8
                bit_offset = 7 - (pixel_offset % 8)                
                ch = ord(buffer[byte_offset])
                new_buf += chr( ( ch >> bit_offset ) & 0xfe )
                
        return new_buf
             
    def writable(self):
        return len(self.out_buffer) > 0

    def handle_write(self):
        if len(self.out_buffer) > 0:
            sent = self.send(self.out_buffer)
            self.out_buffer = self.out_buffer[sent:]
            
        if len(self.oob_buffer) > 0:
            sent = self.socket.send(self.oob_buffer, socket.MSG_OOB)
            self.oob_buffer = self.oob_buffer[sent:]
            
        
    def _paint(self, canvas):
        if self.surface != None:
            size = self.plugin.screen.driver.get_size()
            
            if self.plugin.gconf_client.get_bool(self.plugin.gconf_key + "/keep_aspect_ratio"):
                canvas.translate(0.0, 77.0)
                canvas.scale(2.0, 2.0)
            else:
                canvas.scale(float(size[0]) / 160, float(size[1]) / 43)
            #canvas.scale(2.0, 3.0)
            canvas.set_source_surface(self.surface)
            canvas.paint()
            
    def handle_key(self, keys, state):
        val = 0
        for key in keys:
            if key in KEY_MAP:
                val += KEY_MAP[key]                
                self.out_buffer += struct.pack("<L",val)                            
                self.out_buffer += struct.pack("<L",0)
            else:
                logger.warning("Unmapped G19 -> G15 key")
        
class G15Async(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.name = "G15Async"
        self.setDaemon(True)
        
    def run(self):  
        try :      
            asyncore.loop(timeout=0.05)
        except:            
            sys.stderr.write("WARNING: Failed to connect to G15Daemon client")
            traceback.print_stack()

class G15DaemonServer():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.daemon = None
    
    def activate(self):
        self.screen_index = 0
        self.clients = []
        self.screen.driver.control_update_listeners.append(self)
        self.load_configuration()                
        self.notify_handle = self.gconf_client.notify_add(self.gconf_key, self._config_changed);
        self.daemon = G15Daemon(self._get_port(), self)
        self.async = G15Async()
        self.async.start()
    
    def deactivate(self):
        self._stop_all_clients()
        self.daemon.close()
        self.screen.driver.control_update_listeners.remove(self)
        self.gconf_client.notify_remove(self.notify_handle);
        self.daemon = None
        
    def destroy(self):
        pass
    
    def control_updated(self, control):
        self.load_configuration()
        self.screen.redraw()
        
    def _get_port(self):
        port_entry = self.gconf_client.get(self.gconf_key + "/port")
        return 15550 if port_entry == None else port_entry.get_int()
    
    def _config_changed(self, client, connection_id, entry, args):
        self.load_configuration()
        self.screen.redraw() 
        port = self._get_port()
        if self.daemon == None or self.daemon.port != port:
            if self.daemon != None:
                logger.warning("Port changed to %d (will restart daemon - clients may have to be reconnected manually" % port)
                self._stop_all_clients()
                self.daemon.close()
            self.daemon = G15Daemon(port, self)
            self.async = G15Async()
            self.async.start()
            
    def _stop_all_clients(self):
        for c in self.clients:
            c.handle_close()
        
    def load_configuration(self):        
        foreground_control = self.screen.driver.get_control("foreground")
        self.palette = [0 for n in range(768)]
        self.palette[765] = foreground_control.value[0]
        self.palette[766] = foreground_control.value[1]
        self.palette[767] = foreground_control.value[2]
        
        backlight_control = self.screen.driver.get_control("backlight_colour")
        self.default_backlight = backlight_control.value 
        
        lcd_brightness_control = self.screen.driver.get_control("lcd_brightness")
        self.default_lcd_brightness = lcd_brightness_control.value
    
    def leave(self, client):
        if client in self.clients:
            self.clients.remove(client)
 
    def join(self, client):
        self.clients.append(client)
                    
    def handle_key(self, keys, state, post):
        if not post:
            visible = self.screen.get_visible_page()    
            for client in self.clients:
                if client.enable_keys and client.page == visible:
                    client.handley_key(keys, state)
    
class G15Daemon(asyncore.dispatcher):
    def __init__(self, port, plugin):
        asyncore.dispatcher.__init__(self)        
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        logger.info('Binding to port %d' % port)
        self.bind(("127.0.0.1", port))
        logger.info('Bound to port %d' % port)
        self.listen(5)
        self.plugin = plugin
        self.port = port
 
    def handle_accept(self):
        sock, addr = self.accept()
        logger.debug('Got client')
        client = G15DaemonClient(sock, self.plugin)
        
    def handle_sig_term(self, arg0, arg1):
        self.close()