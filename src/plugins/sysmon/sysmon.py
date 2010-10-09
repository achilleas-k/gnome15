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
import gnome15.g15_theme as g15theme 
import gnome15.g15_util as g15util
import datetime
import time
import gtk
import os
import sys
import cairo

# Plugin details - All of these must be provided
id = "sysmon"
name = "System Monitor"
description = "Display CPU, Memory, and Network statistics. Currently, only a summary " \
        + " of all CPU cores and Network interfaces are displayed. Future versions will " \
        + " allow detailed statistics to be displayed."        
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = "Copyright (C)2010 Brett Smith"
site = "http://localhost"
has_preferences = False

''' 
This simple plugin displays system statistics
'''

def create(gconf_key, gconf_client, screen):
    return G15SysMon(gconf_key, gconf_client, screen)

class G15SysMon():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.timer = None
    
    def activate(self):
        self.properties = None
        self.cpu_history = []
        self.active = True
        self.last_time_list = None
        self.recv_bps = 0.0
        self.send_bps = 0.0
        self.last_time = 0
        self.total = 1.0
        self.cached = 0
        self.free = 0
        self.used = 0
        self.last_net_list = None
        self.max_send = 1   
        self.max_recv = 1 
                      
        self.reload_theme()
        self.page = self.screen.new_page(self.paint, id="System Monitor", on_shown=self.on_shown, on_hidden=self.on_hidden, use_cairo=True)
        self.screen.redraw(self.page)
            
    def on_shown(self):
        self.cancel_refresh()
        self.refresh()
            
    def on_hidden(self):
        self.cancel_refresh()
        self.schedule_refresh()
        
    def cancel_refresh(self):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None
        
    def schedule_refresh(self):
        refresh_val = None
        if self.screen.is_visible(self.page):
            self.timer = g15util.schedule("SysmonRedraw", 1.0, self.refresh)
    
    def deactivate(self):
        self.cancel_refresh()
        self.screen.del_page(self.page)
        
    def destroy(self):
        pass
    
    ''' Callbacks
    '''
        
    def reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
    
    def paint(self, canvas):
        if self.properties != None:
            size = self.screen.size
            offset = 30
            bar_size = float(size[0]) - float(offset) - 60.0
            self.theme.draw(canvas, self.properties)
            
    def build_properties(self): 
        
        properties = {}
        properties["cpu_pc"] = "%3d" % self.cpu
         
        properties["mem_total"] = "%f" % self.total
        properties["mem_free_k"] = "%f" % self.free
        properties["mem_used_k"] = "%f" % self.used
        properties["mem_cached_k"] = "%f" % self.cached
          
        properties["mem_total_mb"] = "%.2f" % ( self.total / 1024 )
        properties["mem_free_mb"] = "%.2f" % ( self.free / 1024 ) 
        properties["mem_used_mb"] = "%.2f" % ( self.used / 1024 ) 
        properties["mem_cached_mb" ] = "%3d" % ( self.cached / 1024 )
          
        properties["mem_total_gb"] = "%.1f" % ( self.total / 1024  / 1024 )
        properties["mem_free_gb"] = "%.1f" % ( self.free / 1024  / 1024 ) 
        properties["mem_used_gb"] = "%.1f" % ( self.used / 1024  / 1024 ) 
        properties["mem_cached_gb" ] = "%.1f" % ( self.cached / 1024 / 1024 )
        
        properties["mem_used_pc"] = int(self.used * 100.0 / self.total)
        properties["mem_cached_pc"] = int(self.cached * 100.0 / self.total)
        
        properties["net_recv_pc"] = int(self.recv_bps * 100.0 / self.max_recv)
        properties["net_send_pc"] = int(self.send_bps * 100.0 / self.max_send)
        properties["net_recv_mbps"] = "%.2f" % (self.recv_bps / 1024 / 1024)
        properties["net_send_mbps"] = "%.2f" % (self.send_bps / 1024 / 1024)
        
        
        properties["net_icon"] = g15util.get_icon_path(self.gconf_client, "gnome-fs-network", self.screen.height)
        properties["cpu_icon"] = g15util.get_icon_path(self.gconf_client, "utilities-system-monitor",  self.screen.height)
        properties["mem_icon"] = g15util.get_icon_path(self.gconf_client, "media-memory",  self.screen.height)
        
        self.properties = properties
            
    
    ''' Functions specific to plugin
    ''' 
        
    def refresh(self):
        
        this_time_list = self.get_time_list()   
        this_net_list = self.get_net_stats()
        mem = self.get_mem_info()
        now = time.time()  

        '''
        CPU
        '''
        
        self.cpu = 0
        if self.last_time_list != None:
            working_list = list(this_time_list)
            for i in range(len(self.last_time_list))  :
                working_list[i] -= self.last_time_list[i]
            sum_l = sum(working_list)
            if sum_l > 0:
                self.cpu = 100 - (working_list[len(working_list) - 1] * 100.00 / sum_l)
        self.last_time_list = this_time_list
        
        '''
        Net
        '''
     
        self.recv_bps = 0.0
        self.send_bps = 0.0
        if self.last_net_list != None:
            this_total = self.get_net_total(this_net_list)
            last_total = self.get_net_total(self.last_net_list)
            
            # How many bps
            time_taken = now - self.last_time
            self.recv_bps = (this_total[0] - last_total[0]) / time_taken
            self.send_bps = (this_total[1] - last_total[1]) / time_taken
            
        # Adjust the maximums if necessary
        if self.recv_bps > self.max_recv:
            self.max_recv = self.recv_bps
        if self.send_bps > self.max_send:
            self.max_send = self.send_bps
                        
        self.last_net_list = this_net_list
        
        '''
        Memory
        '''
        
        self.total = float(mem['MemTotal'])
        self.free = float(mem['MemFree'])
        self.used = self.total - self.free
        self.cached = float(mem['Cached'])
        
        '''
        Update data sets
        '''
        self.cpu_history.append(self.cpu)

        self.build_properties()
        self.screen.redraw(self.page)
        self.schedule_refresh()  
        self.last_time = now
    
    def get_net_stats(self):        
        stat_file = file("/proc/net/dev", "r")
        stat_file.readline()
        stat_file.readline()
        ifs = { }
        for if_line in stat_file:
            split = if_line.split()
            ifs[split[0][:len(split[0]) - 1]] = [ int(split[1]), int(split[9]) ]
        stat_file.close()
        return ifs
    
    def get_time_list(self):
        stat_file = file("/proc/stat", "r")
        time_list = stat_file.readline().split(" ")[2:6]
        stat_file.close()
        for i in range(len(time_list))  :
            time_list[i] = int(time_list[i])
        return time_list
    
    def get_net_total(self, list):
        totals = (0, 0)
        for l in list:
            card = list[l]
            totals = (totals[0] + card[0], totals[1])
            totals = (totals[0], totals[1] + card[1])
        return totals
    
    def get_mem_info(self):
        mem = { }
        stat_file = file("/proc/meminfo", "r")
        for mem_line in stat_file:
            split = mem_line.split()
            mem[split[0][:len(split[0]) - 1]] = split[1]
        stat_file.close()
        return mem