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
 
import gnome15.g15_theme as g15theme 
import gnome15.g15_util as g15util
import gnome15.g15_driver as g15driver
import time
import os
import socket
import shlex

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
unsupported_models = [ g15driver.MODEL_G110 ]

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
        self.cpu_no = 0
        self.cpu_list = self._get_cpu_list()
        self.net_list = []
        self.net_no = 0
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
        self._get_stats()
        self._reload_theme()
        self.page = self.screen.new_page(self._paint, id="System Monitor", on_shown=self._on_shown, on_hidden=self._on_hidden)
        self.page.set_title("System Monitor")
        self.screen.redraw(self.page)
    
    def deactivate(self):
        self._cancel_refresh()
        self.screen.del_page(self.page)
        
    def destroy(self):
        pass
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP and self.screen.get_visible_page() == self.page:
            if g15driver.G_KEY_UP in keys or g15driver.G_KEY_L3 in keys:
                self.last_time_list = None
                self.cpu_no += 1
                if self.cpu_no == len(self.cpu_list):
                    self.cpu_no = 0
                self._reschedule_refresh()
                return True
            if g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L4 in keys:
                self.net_no += 1
                if self.net_no == len(self.net_list):
                    self.net_no = 0
                self._reschedule_refresh()
                return True
    
    ''' Private
    '''
        
    def _reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
    
    def _paint(self, canvas):
        if self.properties != None:
            self.theme.draw(canvas, self.properties) 
            
    def _on_shown(self):
        self._reschedule_refresh()
            
    def _on_hidden(self):
        self._reschedule_refresh()
            
    def _reschedule_refresh(self):
        self._cancel_refresh()
        self._schedule_refresh()
        
    def _cancel_refresh(self):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None
        
    def _schedule_refresh(self):
        if self.screen.is_visible(self.page):
            self.timer = g15util.schedule("SysmonRedraw", 1.0, self._refresh)
        
    def _get_stats(self):
        
        # Get current CPU states
        this_time_list = self._get_time_list(self.cpu_list[self.cpu_no])
        
        # Current net status   
        this_net_list, self.net_list = self._get_net_stats()
        if self.net_no > ( len (self.net_list) - 1):
            self.net_no = 0
            
        # Memory
        mem = self._get_mem_info()
        now = time.time()

        '''
        CPU
        '''
        
        self.cpu = 0
        if self.last_time_list != None:
            working_list = list(this_time_list)
            
            ''' Work out the number of if time units the CPU has spent on each task type since the last
            time we checked
            '''
            for i in range(len(self.last_time_list))  :
                working_list[i] -= self.last_time_list[i]
                
            '''
            Worked out what percentage of the time the CPU was not 'idle' (the last element in the list)
            '''
            sum_l = sum(working_list)
            val = working_list[len(working_list)- 1]
            if sum_l > 0:
                self.cpu = 100 - (val  * 100.00 / sum_l)
                
        self.last_time_list = this_time_list
        
        '''
        Net
        '''
     
        self.recv_bps = 0.0
        self.send_bps = 0.0

        if self.last_net_list != None:
            time_taken = now - self.last_time        
            if self.net_no == 0:
                this_total = self._get_net_total(this_net_list)
                last_total = self._get_net_total(self.last_net_list)            
            else:
                this_total = self._get_net(this_net_list[self.net_list[self.net_no]])
                last_total = self._get_net(self.last_net_list[self.net_list[self.net_no]])
                    
            # How many bps
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
        self.noncached = self.total - self.free - self.cached
        
        '''
        Update data sets
        '''
        self.cpu_history.append(self.cpu)
        
        self.last_time = now
            
    def _build_properties(self): 
        
        properties = {}
        properties["cpu_pc"] = "%3d" % self.cpu
         
        properties["mem_total"] = "%f" % self.total
        properties["mem_free_k"] = "%f" % self.free
        properties["mem_used_k"] = "%f" % self.used
        properties["mem_cached_k"] = "%f" % self.cached
        properties["mem_noncached_k"] = "%f" % self.noncached
          
        properties["mem_total_mb"] = "%.2f" % ( self.total / 1024 )
        properties["mem_free_mb"] = "%.2f" % ( self.free / 1024 ) 
        properties["mem_used_mb"] = "%.2f" % ( self.used / 1024 ) 
        properties["mem_cached_mb" ] = "%3d" % ( self.cached / 1024 ) 
        properties["mem_noncached_mb" ] = "%3d" % ( self.noncached / 1024 )
          
        properties["mem_total_gb"] = "%.1f" % ( self.total / 1024  / 1024 )
        properties["mem_free_gb"] = "%.1f" % ( self.free / 1024  / 1024 ) 
        properties["mem_used_gb"] = "%.1f" % ( self.used / 1024  / 1024 ) 
        properties["mem_cached_gb" ] = "%.1f" % ( self.cached / 1024 / 1024 ) 
        properties["mem_noncached_gb"] = "%.1f" % ( self.noncached / 1024  / 1024 ) 
        
        properties["mem_used_pc"] = int(self.used * 100.0 / self.total)
        properties["mem_cached_pc"] = int(self.cached * 100.0 / self.total)
        properties["mem_noncached_pc"] = int(self.noncached * 100.0 / self.total)
        
        properties["net_recv_pc"] = int(self.recv_bps * 100.0 / self.max_recv)
        properties["net_send_pc"] = int(self.send_bps * 100.0 / self.max_send)
        properties["net_recv_mbps"] = "%.2f" % (self.recv_bps / 1024 / 1024)
        properties["net_send_mbps"] = "%.2f" % (self.send_bps / 1024 / 1024)
        
        
        # TODO we should ship some more appropriate default icons
        properties["net_icon"] = g15util.get_icon_path([ "network-transmit-receive", "gnome-fs-network" ], self.screen.height)
        properties["cpu_icon"] = g15util.get_icon_path( [ "utilities-system-monitor", "gnome-cpu-frequency-applet", "computer" ],  self.screen.height)
        properties["mem_icon"] = g15util.get_icon_path( [ "media-memory", "media-flash" ],  self.screen.height)
        
        try :
            properties["info"] = socket.gethostname()
        except :
            properties["info"] = "System"
        
        properties["cpu_no"] = self.cpu_list[self.cpu_no].upper()
        properties["next_cpu_no"] =  self.cpu_list[self.cpu_no + 1].upper() if self.cpu_no < ( len(self.cpu_list) - 1) else self.cpu_list[0].upper()
        
        properties["net_no"] = self.net_list[self.net_no].upper()
        properties["next_net_no"] =  self.net_list[self.net_no + 1].upper() if self.net_no < ( len(self.net_list) - 1) else self.net_list[0].upper()
        
        self.properties = properties
        
    def _refresh(self):
        self._get_stats()
        self._build_properties()
        self.screen.redraw(self.page)
        self._schedule_refresh()  
    
    def _get_net_stats(self):        
        stat_file = file("/proc/net/dev", "r")
        stat_file.readline()
        stat_file.readline()
        ifs = { }
        nets = [ "Net" ]
        for if_line in stat_file:
            split = if_line.split()
            if_name = split[0][:len(split[0]) - 1]
            ifs[if_name] = [ int(split[1]), int(split[9]) ]
            nets.append(if_name)
        stat_file.close()
        return ifs, nets        
    
    def _get_cpu_list(self):
        stat_file = file("/proc/stat", "r")
        try :
            cpus = []
            for line in stat_file:
                if line.startswith("cpu"):
                    cpus.append(line.split(" ")[0])
            return cpus
        finally :
            stat_file.close()
    
    '''
    Returns a 4 element list containing the amount of time the CPU has 
    spent performing the different types of work
    
    0 user
    1 nice
    2 system
    3 idle
    
    Values are in USER_HZ or Jiffies
    ''' 
    def _get_time_list(self, cpu):
        stat_file = file("/proc/stat", "r")
        try :
            for line in stat_file:
                if line.startswith("%s " % cpu):
                    time_list = shlex.split(line)[1:5]
                    for i in range(len(time_list))  :
                        time_list[i] = int(time_list[i])
                    return time_list
        finally :
            stat_file.close()
    
    def _get_net_total(self, list):
        totals = (0, 0)
        for l in list:
            card = list[l]
            totals = (totals[0] + card[0], totals[1])
            totals = (totals[0], totals[1] + card[1])
        return totals
    
    def _get_net(self, card):
        totals = (card[0], card[1])
        return totals
    
    def _get_mem_info(self):
        mem = { }
        stat_file = file("/proc/meminfo", "r")
        try :
            for mem_line in stat_file:
                split = mem_line.split()
                mem[split[0][:len(split[0]) - 1]] = split[1]
        finally:
            stat_file.close()
            
        return mem