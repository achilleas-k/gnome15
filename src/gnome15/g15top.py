#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2012 Brett Smith <tanktarta@blueyonder.co.uk>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This module has been written to be API compatible with the python-gtop bindings, 
which are no longer available as from Ubuntu 12.10. The suggested replacement
is the GObject based bindings, which would be great except it means converting
ALL of Gnome15 to use such bindings.

This class is stop gap until a better solution can be found
"""

import os

class CPU():
    def __init__(self, name):
        self.name = name
        self.user = 0
        self.nice = 0
        self.sys = 0
        self.idle = 0

class CPUS(CPU):
    def __init__(self):
        CPU.__init__(self, "CPUS")
        cpudata = open('/proc/stat')
        self.cpus = []
        try:
            for line in cpudata:
                if line.startswith("cpu"):
                    (name, cuse, cn, csys, idle, tail) = line.split(None, 5)
                    cpu = self if name == "cpu" else CPU(name)
                    self.user = int(cuse)
                    self.nice = int(cn)
                    self.sys = int(csys)
                    self.idle = int(idle)
                    self.cpus.append(cpu)
        finally:
            cpudata.close()
            
class ProcState():
    
    def __init__(self, pid):
        self.uid = 0
        self.cmd = ""
        memdata = open('/proc/%d/status' % pid)
        try:
            for line in memdata:
                if line.startswith("Uid:"):
                    self.uid = int(self._get_value(line)[0])
                elif line.startswith("Name:"):
                    self.cmd = self._get_value(line)[0]
        finally:
            memdata.close()
            
    def _get_value(self, line):
        return line[line.index(':') + 1:].strip().split()
            
class NetworkLoad():
    
    def __init__(self, net, bytes_in, bytes_out):
        self.net = net
        self.bytes_in = bytes_in
        self.bytes_out = bytes_out
        
class Mem():
    
    def __init__(self):
        self.total = 0
        self.free = 0
        self.cached = 0
        memdata = open('/proc/meminfo')
        try:
            for line in memdata:
                if line.startswith("MemTotal"):
                    self.total = self._get_value(line)
                elif line.startswith("MemFree"):
                    self.free = self._get_value(line)
                elif line.startswith("Cached"):
                    self.cached = self._get_value(line)
        finally:
            memdata.close()
            
    def _get_value(self, line):
        return int(line[line.index(':') + 1:line.index('kB')]) * 1024
            
def netload(net):
    """
    Get the network load details for the network interface described by the
    provided network interface name
    
    Keyword arguments:
    net        --    network interface name
    """
    prefix = '%6s:' % net
    netdata = open('/proc/net/dev')
    try:
        for line in netdata:
            if line.startswith(prefix):
                data = line[line.index(':') + 1:].split()
                return NetworkLoad(net, int(data[0]), int(data[8]))
    finally:
        netdata.close()
    
            
def netlist():
    """
    Returns a list of Net objects, one for each available network interface 
    """
    nets = []
    f = open("/proc/net/dev", "r")
    tmp = f.readlines(2000)
    f.close()
    for line in tmp:
        line = line.strip()
        line = line.split(' ')
        if len(line) > 0 and line[0].endswith(":"):
            nets.append(line[0][:-1])
            
    return nets
    
def cpu():
    """
    Return an object containing data about all available CPUS
    """
    return CPUS()

def mem():
    """
    Return an object containing data about all available CPUS
    """
    return Mem()

def proclist():
    """
    Get a list of all process IDs
    """
    n = []
    for d in os.listdir("/proc"):
        if os.path.isdir("/proc/%s" % d):
            try:
                n.append(int(d))
            except ValueError:
                pass
    return n

def proc_state(pid):
    """
    Get an object describing the state of the given process
    
    Keyword arguments:
    pid        --    process ID
    """
    return ProcState(pid)

def proc_args(pid):
    """
    Get the arguments used to launch a process
    
    Keyword arguments:
    pid        --    process ID
    """
    cmddata = open('/proc/%d/cmdline' % pid)
    try:
        for line in cmddata:
            return line.split("\0")
    finally:
        cmddata.close()

if __name__ == "__main__":
    for d in proclist():
        ps = proc_state(d)
        print d,ps.cmd,ps.uid,proc_args(d)