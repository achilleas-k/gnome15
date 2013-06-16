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
_ = g15locale.get_translation("sysmon", modfile = __file__).ugettext

import gnome15.g15util as g15util
import gnome15.g15ui_gconf as g15ui_gconf
import gnome15.g15gconf as g15gconf
import gnome15.g15cairo as g15cairo
import gnome15.g15driver as g15driver
import gnome15.g15plugin as g15plugin
import time
try:
    import gtop
except:
    # API compatible work around for Ubuntu 12.10
    import gnome15.g15top as gtop
import gtk
import os
import sys
import socket

id = "sysmon"
name = _("System Monitor")
description = _("Display CPU, Memory, and Network statistics. Either a summary of each system's stats is displayed, or \
you may cycle through the CPU and Network interfaces.")        
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = _("Copyright (C)2010 Brett Smith")
site = "http://www.gnome15.org"
default_enabled = True
has_preferences = True
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Toggle Monitored CPU"), 
         g15driver.NEXT_SELECTION : _("Toggle Monitored Network\nInterface") }
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]

# Various constants
GRAPH_SIZE = 50
CPU_ICONS = [ "utilities-system-monitor","gnome-cpu-frequency-applet", "computer" ]
 
''' 
This plugin displays system statistics
'''

def create(gconf_key, gconf_client, screen):
    return G15SysMon(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "sysmon.glade"))    
    dialog = widget_tree.get_object("SysmonDialog")
    dialog.set_transient_for(parent)    
    g15ui_gconf.configure_checkbox_from_gconf(gconf_client, gconf_key + "/show_cpu_on_panel", "ShowCPUUsageOnPanel", True, widget_tree)
    dialog.run()
    dialog.hide()
    
class Net():
    
    def __init__(self, net_no, name):
        self.net_no = net_no
        self.name = name 
        self.recv_bps = 0.0
        self.send_bps = 0.0
        self.last_net_list = None
        self.max_send = 0.0001  
        self.max_recv = 0.0001
        self.send_history = [0] * GRAPH_SIZE
        self.recv_history =  [0] * GRAPH_SIZE
        self.last_net_list = None
        self.last_time = 0
        
    def new_data(self, this_net_list):
        now = time.time() 
            
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
                this_total = self._get_net(this_net_list[self.name])
                last_total = self._get_net(self.last_net_list[self.name])
                    
            # How many bps
            self.recv_bps = (this_total[0] - last_total[0]) / time_taken
            self.send_bps = (this_total[1] - last_total[1]) / time_taken
            
        # Adjust the maximums if necessary
        if self.recv_bps > self.max_recv:
            self.max_recv = self.recv_bps
        if self.send_bps > self.max_send:
            self.max_send = self.send_bps
                        
        # History
        self.send_history.append(self.recv_bps)
        while len(self.send_history) > GRAPH_SIZE:
            del self.send_history[0]
        self.recv_history.append(self.send_bps)
        while len(self.recv_history) > GRAPH_SIZE:
            del self.recv_history[0]
            
        self.last_net_list = this_net_list 
        self.last_time = now
    
    def _get_net(self, card):
        totals = (card[0], card[1])
        return totals  

    def _get_net_total(self, net_list):
        totals = (0, 0)
        for l in net_list:
            card = net_list[l]
            totals = (totals[0] + card[0], totals[1])
            totals = (totals[0], totals[1] + card[1])
        return totals       
    
class CPU():
    
    def __init__(self, number):
        self.number = number 
        self.name = "cpu%d" % number if number >= 0 else "cpu"
        self.history = [0] * GRAPH_SIZE
        self.value = 0
        self.times = None
        self.last_times = None
        
    def new_times(self, time_list):

        if self.last_times is not None:
            working_list = list(time_list)
                    
            ''' Work out the number of time units the CPU has spent on each task type since the last
            time we checked
            '''
            
            for i in range(len(self.last_times)):
                working_list[i] -= self.last_times[i]
                        
            self.pc = self.get_pc(working_list)
        else:
            self.pc = 0
        
        self.last_times = time_list
        
        # Update the history and trim it to the graph data size
        self.history.append(self.pc)
        while len(self.history) > GRAPH_SIZE:
            del self.history[0]       
        
    def get_pc(self, times):
        sum_l = sum(times)
        val = times[len(times)- 1]
        if sum_l > 0:
            return 100 - (val  * 100.00 / sum_l)
        return 0
        
class G15SysMon(g15plugin.G15RefreshingPlugin):
    """
    Plugin implementation
    """    
    def __init__(self, gconf_key, gconf_client, screen):
        g15plugin.G15RefreshingPlugin.__init__(self, gconf_client, gconf_key, screen, CPU_ICONS, id, name)
        self.only_refresh_when_visible = False
    
    def activate(self):
        self._net_icon = g15util.get_icon_path([ "network-transmit-receive", 
                                                "gnome-fs-network",
                                                "network-server" ], 
                                               self.screen.height)
        self._cpu_icon = g15util.get_icon_path( CPU_ICONS,  
                                               self.screen.height)
        self._mem_icon = g15util.get_icon_path( [ "media-memory", 
                                                 "media-flash" ],  
                                               self.screen.height)
        self._thumb_icon = g15cairo.load_surface_from_file(self._cpu_icon)
        
        self.variant = 0
        self.graphs = {}
        self.last_time_list = None
        self.last_times_list = []
        self.last_time = 0
        
        # CPU
        self.selected_cpu = None
        self.cpu_no = 0  
        self.cpu_data = []  
        selected_cpu_name = self.gconf_client.get_string(self.gconf_key + "/cpu")
        cpus = gtop.cpu().cpus
        for i in range(-1, len(cpus)):
            cpu = CPU(i)
            self.cpu_data.append(cpu)
            if cpu.name == selected_cpu_name:
                self.selected_cpu = cpu
        if self.selected_cpu is None:
            self.selected_cpu = self.cpu_data[0]

        # Net
        self.selected_net = None
        _, self.net_list = self._get_net_stats()
        net_name = self.gconf_client.get_string(self.gconf_key + "/net")
        self.net_data = []
        for idx, n in enumerate(self.net_list):
            net = Net(idx, n)
            self.net_data.append(net)
            if net.name == net_name:
                self.selected_net = net
            
        if self.selected_net is None and len(self.net_data) > 0:
            self.selected_net = self.net_data[0] 
            
        
        # Memory
        self.max_total_mem = 0
        self.total = 1.0
        self.cached = 0
        self.free = 0
        self.used = 0
        self.cached_history = [0] * GRAPH_SIZE
        self.used_history =  [0] * GRAPH_SIZE 
        
        g15plugin.G15RefreshingPlugin.activate(self)
        self._set_panel()
        self.watch(["show_cpu_on_panel","theme"], self._config_changed)
        self.screen.key_handler.action_listeners.append(self)
        
        # Start refreshing
        self.do_refresh()
        
    def reload_theme(self):
        g15plugin.G15RefreshingPlugin.reload_theme(self)
        self._set_panel()
    
    def deactivate(self):
        g15plugin.G15RefreshingPlugin.deactivate(self)
        self.screen.key_handler.action_listeners.remove(self)
        
    def action_performed(self, binding):
        if self.page and self.page.is_visible():
            if binding.action == g15driver.PREVIOUS_SELECTION:
                idx = self.cpu_data.index(self.selected_cpu)
                idx += 1
                if idx >= len(self.cpu_data):
                    idx = 0                
                self.gconf_client.set_string(self.gconf_key + "/cpu", self.cpu_data[idx].name)
                self.selected_cpu = self.cpu_data[idx]
                self.do_refresh()
                return True
            elif binding.action == g15driver.NEXT_SELECTION:
                if self.selected_net is not None:
                    idx = self.net_data.index(self.selected_net)
                    idx += 1
                    if idx >= len(self.net_data):
                        idx = 0                
                    self.gconf_client.set_string(self.gconf_key + "/net", self.net_data[idx].name)
                    self.selected_net = self.net_data[idx]
                    self.do_refresh()
                    return True
        
    def refresh(self):
            
        # Memory
        mem = self._get_mem_info()
        now = time.time()

        '''
        CPU
        '''
        for c in self.cpu_data:            
            c.new_times(self._get_time_list(c))
        
        '''
        Net
        '''
        
        # Current net status   
        this_net_list, self.net_list = self._get_net_stats()
        for n in self.net_data:
            n.new_data(this_net_list)
        
        '''
        Memory
        '''
        
        self.total = float(mem.total)
        self.max_total_mem = max(self.max_total_mem, self.total)
        self.free = float(mem.free)
        self.used = self.total - self.free
        self.cached = float(mem.cached)
        self.noncached = self.total - self.free - self.cached
        self.used_history.append(self.used + self.cached)
        
        while len(self.used_history) > GRAPH_SIZE:
            del self.used_history[0]
        self.cached_history.append(self.cached)
        while len(self.cached_history) > GRAPH_SIZE:
            del self.cached_history[0]
        
        self.last_time = now
    
    ''' Private
    '''
    def _config_changed(self, client, connection_id, entry, args):
        self.reload_theme()
        self._reschedule_refresh()
            
    def _set_panel(self, client = None, connection_id = None, entry = None, args = None):        
        self.page.panel_painter = self._paint_panel if g15gconf.get_bool_or_default(self.gconf_client, self.gconf_key + "/show_cpu_on_panel", True) else None
        
    def _refresh(self):
        if self.page is not None:
            if self.screen.is_visible(self.page):
                self.refresh()
                self.screen.redraw(self.page)
            elif self.page.panel_painter is not None:
                self.refresh()
                self.screen.redraw(redraw_content = False)
            self._schedule_refresh()
            
    def get_theme_properties(self): 
        
        properties = {}
        properties["cpu_pc"] = "%3d" % self.selected_cpu.pc
         
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
        
        if self.selected_net is not None:
            properties["net_recv_pc"] = int(self.selected_net.recv_bps * 100.0 / self.selected_net.max_recv)
            properties["net_send_pc"] = int(self.selected_net.send_bps * 100.0 / self.selected_net.max_send)
            properties["net_recv_mbps"] = "%.2f" % (self.selected_net.recv_bps / 1024 / 1024)
            properties["net_send_mbps"] = "%.2f" % (self.selected_net.send_bps / 1024 / 1024)
            properties["net_no"] = self.selected_net.name.upper()
            idx = self.net_data.index(self.selected_net)
            properties["next_net_no"] =  self.net_list[idx + 1].upper() if idx < ( len(self.net_list) - 1) else self.net_list[0].upper()
        else:
            for c in ["net_recv_pc","net_send_pc","net_recv_mbps","net_send_mbps"]:
                properties[c] = ""
        
        # TODO we should ship some more appropriate default icons
        properties["net_icon"] = self._net_icon
        properties["cpu_icon"] = self._cpu_icon
        properties["mem_icon"] = self._mem_icon
        
        try :
            properties["info"] = socket.gethostname()
        except :
            properties["info"] = "System"
        
        properties["cpu_no"] = self.selected_cpu.name.upper()
        idx = self.cpu_data.index(self.selected_cpu)
        properties["next_cpu_no"] =  self.cpu_data[idx + 1].name.upper() if idx < ( len(self.cpu_data) - 1) else self.cpu_data[0].name.upper()
        
        
        return properties
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None and self._thumb_icon != None and self.screen.driver.get_bpp() == 16:
            return g15util.paint_thumbnail_image(allocated_size, self._thumb_icon, canvas)
    
    def _paint_panel(self, canvas, allocated_size, horizontal):
        if self.page != None and self.screen.driver.get_bpp() == 16:
            canvas.save()
            
            no_cpus = len(self.cpu_data) - 1
            if no_cpus < 2:
                bar_width = 16
            elif no_cpus < 3:
                bar_width = 8
            elif no_cpus < 5:
                bar_width = 6
            elif no_cpus < 9:
                bar_width = 4
            else:
                bar_width = 2
                
            total_width = ( bar_width + 1 ) * no_cpus
            available_height = allocated_size - 4
            
            r, g, b = self.screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, (0,0,0))
            
            canvas.set_line_width(1.0)
            canvas.set_source_rgba(r, g, b, 0.3)
            canvas.rectangle(0, 0, total_width + 4, allocated_size )
            canvas.stroke()
            canvas.set_source_rgb(*self.screen.driver.get_color_as_ratios(g15driver.HINT_HIGHLIGHT, (0,0,0)))
            canvas.translate(2, 0)
            for i in self.cpu_data:
                if i.number >= 0:
                    bar_height = float(available_height) * ( float(i.pc) / 100.0 )
                    canvas.rectangle(0, available_height - bar_height + 2, bar_width, bar_height )
                    canvas.fill()
                    canvas.translate(bar_width + 1, 0)
                
            canvas.restore()
            
            return 4 + total_width  
    
    def _get_net_stats(self):
        ifs = { }
        nets = gtop.netlist()
        for net in nets:
            netload = gtop.netload(net)
            ifs[net] = [ netload.bytes_in, netload.bytes_out ]
        nets.insert(0, "Net")
        return ifs, nets

    
    def _get_time_list(self, cpu):
        '''
        Returns a 4 element list containing the amount of time the CPU has 
        spent performing the different types of work
        
        0 user
        1 nice
        2 system
        3 idle
        
        Values are in USER_HZ or Jiffies
        ''' 
        if cpu.number == -1:
            cpu_times = gtop.cpu()
        else:
            cpu_times = gtop.cpu().cpus[cpu.number]
        return [cpu_times.user, cpu_times.nice, cpu_times.sys, cpu_times.idle]
    
    def _get_mem_info(self):
        return gtop.mem()
