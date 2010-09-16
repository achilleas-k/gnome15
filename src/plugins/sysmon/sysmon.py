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
import datetime
from threading import Timer
import time
import gtk
import os
import sys

# Plugin details - All of these must be provided
id = "sysmon"
name = "System Monitor"
description = "Display CPU, Memory, Swap and Net statistics"
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
    
    def activate(self):
        self.timer = None
        self.active = True
        self.last_time_list = None
        self.last_net_list = None    
        self.max_send = 1   
        self.max_recv = 1        
        self.canvas = self.screen.new_canvas(on_shown=self.on_shown, on_hidden=self.on_hidden, id="System Monitor")
        self.screen.draw_current_canvas()
    
    def deactivate(self):
        self.hidden = True
        if self.timer != None:
            self.timer.cancel()
        self.screen.del_canvas(self.canvas)
        
    def destroy(self):
        pass
    
    ''' Callbacks
    '''
    
    def on_shown(self):
        if self.timer != None:
            self.timer.cancel()
        self.hidden = False
        self.redraw()
        
    def on_hidden(self):
        if self.timer != None:
            self.timer.cancel()
        self.hidden = True
    
    ''' Functions specific to plugin
    ''' 
    
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
    
    def redraw(self):
        if not self.hidden:
            
            size = self.screen.driver.get_size()
            
            self.canvas.clear()
            now = time.time()
            offset = 30
            bar_size = float(size[0]) - float(offset) - 60.0
            
            # CPU
            this_time_list = self.get_time_list()
            cpu_w = 0
            cpu = 0
            if self.last_time_list != None:
                working_list = list(this_time_list)
                for i in range(len(self.last_time_list))  :
                    working_list[i] -= self.last_time_list[i]
                cpu = 100 - (working_list[len(working_list) - 1] * 100.00 / sum(working_list))
                cpu_w = ( bar_size / 100) * cpu
                
            self.canvas.draw_text("CPU:", (0, 0))
            self.canvas.fill_box((offset, 3, offset + cpu_w, 10))
            self.canvas.draw_text("%3d%%" % cpu, (g15draw.RIGHT, 0), emboss="White")   
                
            self.last_time_list = this_time_list
            
            # Net
            this_net_list = self.get_net_stats()
            recv_bps = 0.0
            send_bps = 0.0
            if self.last_net_list != None:
                this_total = self.get_net_total(this_net_list)
                last_total = self.get_net_total(self.last_net_list)
                    
                # How many bps
                time_taken = now - self.last_time
                recv_bps = (this_total[0] - last_total[0]) / time_taken
                send_bps = (this_total[1] - last_total[1]) / time_taken
                
            # Adjust the maximums if necessary
            if recv_bps > self.max_recv:
                self.max_recv = recv_bps
            if send_bps > self.max_send:
                self.max_send = send_bps 
                    
            # Calculate the current value as percentage of max
            recv_pc = recv_bps * 100.0 / self.max_recv
            send_pc = send_bps * 100.0 / self.max_send
                
            # Draw the net graph
            net_w = (bar_size / 100) * recv_pc
            self.canvas.draw_text("Net:", (0, 11))
            self.canvas.fill_box((offset, 14, offset + net_w, 17))
            net_w = (bar_size / 100) * send_pc
            self.canvas.fill_box((offset, 18, offset + net_w, 21))
            self.canvas.draw_text("%3.2f / %3.2f" % ((recv_bps / 1024 / 1024), (send_bps / 1024 / 1024)), (g15draw.RIGHT, 11), emboss="White")  
                
            self.last_net_list = this_net_list
            
            # Draw the memory graph
            mem = self.get_mem_info()
            total = float(mem['MemTotal'])
            free = float(mem['MemFree'])
            used = total - free
            cached = float(mem['Cached'])
            used_pc = used * 100.0 / total
            cached_pc = cached * 100.0 / total
            
            self.canvas.draw_text("Mem:", (0, 22))
            mem_w = (bar_size / 100) * used_pc
            self.canvas.fill_box((offset, 25, offset + mem_w, 32))
            mem_w = (bar_size / 100) * cached_pc
            self.canvas.fill_box((offset, 25, offset + mem_w, 32), color="Gray")
            self.canvas.draw_text("%3.2f / %3.2f" % ((used / 1024 / 1024), (total / 1024 / 1024)), (g15draw.RIGHT, 22), emboss="White")
            
            # Draw and cycle         
            self.screen.draw(self.canvas)
            self.last_time = now
            self.timer = Timer(1, self.redraw, ())
            self.timer.name = "SysmonRedrawThread"
            self.timer.setDaemon(True)
            self.timer.start()
