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
 
import gnome15.g15theme as g15theme 
import gnome15.g15util as g15util
import gnome15.g15driver as g15driver
import gnome15.g15screen as g15screen
import time
import os
import gtop
import socket

id = "sysmon"
name = "System Monitor"
description = "Display CPU, Memory, and Network statistics. Either a summary of each system's stats is displayed, or " + \
            "you may cycle through the CPU and Network interfaces using Up and Down on the G19, or L3 and L4 on all " + \
            "other supported models."        
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = "Copyright (C)2010 Brett Smith"
site = "http://localhost"
has_preferences = False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]

''' 
This plugin displays system statistics
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
        self._net_icon = g15util.get_icon_path([ "network-transmit-receive", "gnome-fs-network" ], self.screen.height)
        self._cpu_icon = g15util.get_icon_path( [ "utilities-system-monitor", "gnome-cpu-frequency-applet", "computer" ],  self.screen.height)
        self._mem_icon = g15util.get_icon_path( [ "media-memory", "media-flash" ],  self.screen.height)
        self._thumb_icon = g15util.load_surface_from_file(self._cpu_icon)
        
        self.active = True
        self.last_time_list = None
        self.last_time = 0
        
        # CPU
        self.cpu_no = 0
        self.cpu_list = self._get_cpu_list()
        cpu = self.gconf_client.get_string(self.gconf_key + "/cpu")
        if cpu and (cpu in self.cpu_list):
            self.cpu_no = self.cpu_list.index(cpu)
        self.cpu_history = []

        # Net
        ifs, self.net_list = self._get_net_stats()
        net = self.gconf_client.get_string(self.gconf_key + "/net")
        if net and (net in self.net_list):
            self.net_no = self.net_list.index(net)
        else:
            self.net_no = 0
        self.recv_bps = 0.0
        self.send_bps = 0.0
        self.last_net_list = None
        self.max_send = 1   
        self.max_recv = 1
        
        # Memory
        self.total = 1.0
        self.cached = 0
        self.free = 0
        self.used = 0
        
        # Initial stats load and create the page 
        self.page = g15theme.G15Page(id, self.screen, on_shown=self._on_shown, on_hidden=self._on_hidden, \
                                     title = name, theme = g15theme.G15Theme(self),
                                     thumbnail_painter = self._paint_thumbnail )
        self._get_stats()
        self._build_properties()
        self.screen.add_page(self.page)
        self.screen.action_listeners.append(self)
        self.screen.redraw(self.page)
    
    def deactivate(self):
        self.screen.action_listeners.remove(self)
        self._cancel_refresh()
        self.screen.del_page(self.page)
        
    def destroy(self):
        pass
    

    def action_performed(self, binding):
        if self.page and self.page.is_visible():
            if binding.action == g15screen.PREVIOUS_SELECTION:
                self.last_time_list = None
                self.cpu_no += 1
                if self.cpu_no == len(self.cpu_list):
                    self.cpu_no = 0
                self.gconf_client.set_string(self.gconf_key + "/cpu", self.cpu_list[self.cpu_no])
                self._reschedule_refresh()
                return True
            elif binding.action == g15screen.NEXT_SELECTION:
                self.net_no += 1
                if self.net_no == len(self.net_list):
                    self.net_no = 0
                    
                self.gconf_client.set_string(self.gconf_key + "/net", self.net_list[self.net_no])
                self._reschedule_refresh()
                return True
    
    ''' Private
    '''
        
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
            
            ''' Work out the number of time units the CPU has spent on each task type since the last
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
        
        self.total = float(mem.total)
        self.free = float(mem.free)
        self.used = self.total - self.free
        self.cached = float(mem.cached)
        self.noncached = self.total - self.free - self.cached
        
        '''
        Update data sets
        '''
        self.cpu_history.append(self.cpu)
        
        self.last_time = now
            
    def _build_properties(self): 
        
        properties = {}
        properties["cpu_pc"] = "%3d" % self.cpu
         
        properties["mem_total"] = "%f" % ( self.total / 1024 )
        properties["mem_free_k"] = "%f" % ( self.free / 1024 )
        properties["mem_used_k"] = "%f" % ( self.used / 1024 )
        properties["mem_cached_k"] = "%f" % ( self.cached / 1024 )
        properties["mem_noncached_k"] = "%f" % ( self.noncached / 1024 )
          
        properties["mem_total_mb"] = "%.2f" % ( self.total / 1024 / 1024 )
        properties["mem_free_mb"] = "%.2f" % ( self.free / 1024 / 1024 )
        properties["mem_used_mb"] = "%.2f" % ( self.used / 1024 / 1024 )
        properties["mem_cached_mb" ] = "%3d" % ( self.cached / 1024 / 1024 )
        properties["mem_noncached_mb" ] = "%3d" % ( self.noncached / 1024 / 1024 )
          
        properties["mem_total_gb"] = "%.1f" % ( self.total / 1024  / 1024 / 1024 )
        properties["mem_free_gb"] = "%.1f" % ( self.free / 1024  / 1024 / 1024 )
        properties["mem_used_gb"] = "%.1f" % ( self.used / 1024  / 1024 / 1024 )
        properties["mem_cached_gb" ] = "%.1f" % ( self.cached / 1024 / 1024 / 1024 )
        properties["mem_noncached_gb"] = "%.1f" % ( self.noncached / 1024  / 1024 / 1024 )
        
        properties["mem_used_pc"] = int(self.used * 100.0 / self.total)
        properties["mem_cached_pc"] = int(self.cached * 100.0 / self.total)
        properties["mem_noncached_pc"] = int(self.noncached * 100.0 / self.total)
        
        properties["net_recv_pc"] = int(self.recv_bps * 100.0 / self.max_recv)
        properties["net_send_pc"] = int(self.send_bps * 100.0 / self.max_send)
        properties["net_recv_mbps"] = "%.2f" % (self.recv_bps / 1024 / 1024)
        properties["net_send_mbps"] = "%.2f" % (self.send_bps / 1024 / 1024)
        
        # TODO we should ship some more appropriate default icons
        properties["net_icon"] = self._net_icon
        properties["cpu_icon"] = self._cpu_icon
        properties["mem_icon"] = self._mem_icon
        
        try :
            properties["info"] = socket.gethostname()
        except :
            properties["info"] = "System"
        
        properties["cpu_no"] = self.cpu_list[self.cpu_no].upper()
        properties["next_cpu_no"] =  self.cpu_list[self.cpu_no + 1].upper() if self.cpu_no < ( len(self.cpu_list) - 1) else self.cpu_list[0].upper()
        
        properties["net_no"] = self.net_list[self.net_no].upper()
        properties["next_net_no"] =  self.net_list[self.net_no + 1].upper() if self.net_no < ( len(self.net_list) - 1) else self.net_list[0].upper()
        
        self.page.theme_properties = properties
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None and self._thumb_icon != None and self.screen.driver.get_bpp() == 16:
            return g15util.paint_thumbnail_image(allocated_size, self._thumb_icon, canvas)
        
    def _refresh(self):
        self._get_stats()
        self._build_properties()
        self.screen.redraw(self.page)
        self._schedule_refresh()  
    
    def _get_net_stats(self):
        ifs = { }
        nets = gtop.netlist()
        for net in nets:
            netload = gtop.netload(net)
            ifs[net] = [ netload.bytes_in, netload.bytes_out ]
        nets.insert(0, "Net")
        return ifs, nets

    def _get_cpu_list(self):
	cpus = [ "cpu" ]
        for i in range(len(gtop.cpu().cpus)):
            cpus.append("cpu%d" % i)
        return cpus

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
        cpu_no = cpu.lower().replace("cpu","")
        if len(cpu_no) == 0:
            cpu = gtop.cpu()
        else:
            cpu = gtop.cpu().cpus[int(cpu_no)]
        return [cpu.user, cpu.nice, cpu.sys, cpu.idle]

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
        return gtop.mem()