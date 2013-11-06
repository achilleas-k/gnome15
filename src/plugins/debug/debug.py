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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("clock", modfile = __file__).ugettext

import gnome15.g15text as g15text
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import gnome15.g15plugin as g15plugin
import gnome15.g15theme as g15theme
import gnome15.util.g15scheduler as g15scheduler
import pango
import os
import sys
import traceback
import gc
import gnome15.objgraph as objgraph
import dbus.service

# Logging
import logging
logger = logging.getLogger(__name__)

id="debug"
name=_("Debug")
description=_("Displays some information useful for debugging Gnome15.\n \
Also adds additional DBUS functions to inspect internals")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=False
single_instance=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]

_proc_status = '/proc/%d/status' % os.getpid()

_scale = {'kB': 1024.0, 'mB': 1024.0*1024.0,
          'KB': 1024.0, 'MB': 1024.0*1024.0}

DEBUG_NAME="/org/gnome15/Debug"
DEBUG_IF_NAME="org.gnome15.Debug"
EXCLUDED = [ 
            "instancemethod", 
            "weakref", 
            "instance",
            "method_descriptor",
            "member_descriptor",
            "frame",
            "function",
            "intdict",
            "builtin_function_or_method",
            "builtin_function_or_method",
            ]

class intdict(dict):
    
    def __init__(self):
        dict.__init__(self)

class Snapshot():
    
    def __init__(self):
        self.stats = intdict()
        self.objects = intdict() 
        
def referents_count(typename):
    print "%d instances of  type %s. Referents :-" % ( objgraph.count(typename), typename)
    done = {}
    for r in objgraph.by_type(typename):
        for o in gc.get_referents(r):
            name = _get_key(o)
            if name != "type" and name != typename and not name in EXCLUDED and not name in done:
                done[name] = True
                count = objgraph.count(name)
                if count > 1:
                    print "   %s  (%d)" % ( name, count )
                           
def referents(typename, max_depth = 1):
    print "%d instances of  type %s. Referents :-" % ( objgraph.count(typename), typename)
    for r in objgraph.by_type(typename):
        _do_referents(r, 1, max_depth)
             
def _do_referents(r, depth, max_depth = 1):
    dep = ""
    for _ in range(0, depth):
        dep += "    "
    for o in gc.get_referents(r):
        if not _get_key(o) in EXCLUDED:
            if isinstance(o, dict):
                print "%s%s" % (dep, _max_len(o, 120))
                if depth < max_depth:
                    _do_referents(o, depth + 1)

def referrers(typename, max_depth = 1):
    print "%d instances of type %s. Referrers :-" % ( objgraph.count(typename), typename)
    for r in objgraph.by_type(typename):
        _do_referrers(r, 1, max_depth, [])
                
def _do_referrers(r, depth, max_depth, done):
    dep = ""
    for _ in range(0, depth):
        dep += "    "
    l = gc.get_referrers(r)
    for o in l:
        if not o == done and not o == l and not _get_key(o) in EXCLUDED and not o in done:
            print "%s%s" % (dep, _max_len(o, 120))
            done.append(o)
            if depth < max_depth:
                _do_referrers(o, depth + 1, max_depth, done)
                 
def referrers_count(typename):
    print "%d instances of type %s. Referrers :-" % ( objgraph.count(typename), typename)
    done = {}
    for r in objgraph.by_type(typename):
        for o in gc.get_referrers(r):
            name = _get_key(o)
            if name != "type" and name != typename and not name in EXCLUDED and not name in done:
                done[name] = True
                count = objgraph.count(name)
                if count > 1:
                    print "   %s  (%d)" % ( name, count )
    
def take_snapshot(snap_objects = True):
    snapshot = Snapshot()
    for o in gc.get_objects():
        k = _get_key(o)
        if not k in EXCLUDED:
            snapshot.stats.setdefault(k, 0)
            snapshot.stats[k] += 1
            if snap_objects:
                snapshot.objects.setdefault(k, [])
                snapshot.objects[k].append(o)
    return snapshot

def compare_snapshots(snapshot1, snapshot2, show_removed = True):
    new_types = []
    changed_types = []
    removed_types = []
    
    # Find everything that has been removed or changed
    for k, v in snapshot1.stats.iteritems():
        if not k in snapshot2.stats:
            removed_types.append(k)
        else:
            if v != snapshot2.stats[k]:
                changed_types.append(k)
                
    # Find everything that has been added
    for k, v in snapshot2.stats.iteritems():
        if not k in snapshot1.stats:
            new_types.append(k)
            
    # Print some stuff
    print "New types"
    _do_types(snapshot1, snapshot2, new_types)
    
    if show_removed:
        print "Removed types"
        for k in removed_types:
            print "    %-30s" % k
            
    # Find the actual objects that have been added for those that have changed
    print "Changed types"
    _do_types(snapshot1, snapshot2, changed_types, show_removed)
    
def _get_key(o):
    if isinstance(o, object):
        try:
            return o.__class__.__name__
        except:
            return type(o).__name__
    else:
        return type(o).__name__
                
def _do_types(snapshot1, snapshot2, types, show_removed = True):
    for k in types:
        print "%4s%-30s %10d (was %d)" % ("",k, snapshot2.stats[k], snapshot1.stats[k] if k in snapshot1.stats else 0)
        old_objects = snapshot1.objects[k] if k in snapshot1.objects else []
        new_objects = snapshot2.objects[k] if k in snapshot2.objects else []
        
        # Find any objects removed
        removed = 0
        if show_removed:
            for x in old_objects:
                in_new = False
                try:
                    in_new = x in new_objects
                except:
                    pass
                if not in_new:
                    removed += 1
                    try :
                        _do_obj(x, "Removed")
                    except Exception as e:
                        print "%12sError! - %s" % ( "", _max_len(str(e), 80) )
                
        # Find any objects added
        added = 0
        for x in new_objects:
            in_old = False
            try:
                in_old = x in old_objects
            except:
                pass
            if not in_old:
                added += 1
                try :
                    _do_obj(x, "Added")
                except:
                    print "%12sError! - %s" % ( "", _max_len(str(e), 80) )
                    
        if added > 0 or removed > 0:
            print "%4sAdded %d, Removed %d" % ("", added, removed ) 
                    
        
            
def _do_obj(o, s):
    if isinstance(o, list) and len(o) > 0:
        # Ignore the list if it contains excluded items        
        if _get_key(o[0]) in EXCLUDED:
            return
    elif isinstance(o, dict):
        for k, v in dict(o).iteritems():        
            if _get_key(k) in EXCLUDED or _get_key(v) in EXCLUDED:
                return
            break
    elif isinstance(o, tuple) and len(o) > 0:
        # Ignore the list if it contains excluded items        
        for v in o:
            if _get_key(v) in EXCLUDED:
                return
        
    o_str = _max_len(o, 60)
    print "%12s%8s : %-30s %-60s" % ("",s, _get_key(o), o_str)
        
def _max_len(o, l):
    o_str = str(o)
    if len(o_str) > l:
        o_str = o_str[:l]
    return o_str
    
class G15DBUSDebugService(dbus.service.Object):
    
    def __init__(self, dbus_service):
        dbus.service.Object.__init__(self, dbus_service._bus_name, DEBUG_NAME)
        self._service = dbus_service._service
        self._snapshot1 = None
        
    @dbus.service.method(DEBUG_IF_NAME)
    def Snapshot(self):
        logger.info("Collecting garbage")
        gc.collect()
        logger.info("Collected garbage")
        logger.info("Taking snapshot")
        _snapshot2 = take_snapshot(False)
        logger.info("Taken snapshot")
        if self._snapshot1 is not None:
            compare_snapshots(self._snapshot1, _snapshot2, show_removed = True)
        else:
            logger.info("FIRST snapshot taken, take another")
        self._snapshot1 = _snapshot2
        
    @dbus.service.method(DEBUG_IF_NAME)
    def GC(self):
        logger.info("Collecting garbage")
        gc.collect()
        logger.info("Collected garbage")
        
    @dbus.service.method(DEBUG_IF_NAME)
    def ToggleDebugSVG(self):
        g15theme.DEBUG_SVG = not g15theme.DEBUG_SVG
        
    @dbus.service.method(DEBUG_IF_NAME)
    def MostCommonTypes(self):
        print "Most used objects"
        print "-----------------"
        print
        objgraph.show_most_common_types(limit=200)
        print "Job Queues"
        print "----------"
        print
        g15scheduler.scheduler.print_all_jobs()
        print "Threads"
        print "-------"
        for threadId, stack in sys._current_frames().items():
            print "ThreadID: %s" % threadId
            for filename, lineno, name, line in traceback.extract_stack(stack):
                print '    File: "%s", line %d, in %s' % (filename, lineno, name)
        
    @dbus.service.method(DEBUG_IF_NAME)
    def ShowGraph(self):
        objgraph.show_refs(self._service)
        
    @dbus.service.method(DEBUG_IF_NAME, in_signature='s')
    def PluginObject(self, m):
        for scr in self._service.screens:
            print "Screen %s" % scr.device.uid
            for p in scr.plugins.plugin_map:
                pmod = scr.plugins.plugin_map[p]
                if m == '' or m == pmod.id:
                    print "    %s" % pmod.id
                    objgraph.show_backrefs(p, filename='%s-%s' %(scr.device.uid, pmod.id))
        
    @dbus.service.method(DEBUG_IF_NAME, in_signature='s')
    def Objects(self, typename):
        print "%d instances of type %s. Referrers :-" % ( objgraph.count(typename), typename)
        done = {}
        for r in objgraph.by_type(typename):
            if isinstance(r, list):
                print "%s" % str(r[:min(20, len(r))])
            else:
                print "%s" % str(r)
        
    @dbus.service.method(DEBUG_IF_NAME, in_signature='s')
    def SetDebugLevel(self, log_level):
        levels = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}
        logger = logging.getLogger()
        level = levels.get(log_level.lower(), logging.NOTSET)
        logger.setLevel(level = level)
        
    @dbus.service.method(DEBUG_IF_NAME, in_signature='s')
    def Referrers(self, typename):
        referrers(typename, 1)
        
    @dbus.service.method(DEBUG_IF_NAME, in_signature='s')
    def ReferrersCount(self, typename):
        referrers_count(typename)
        
    @dbus.service.method(DEBUG_IF_NAME, in_signature='s')
    def Referents(self, typename):
        referents(typename)
        
    @dbus.service.method(DEBUG_IF_NAME, in_signature='s')
    def ReferentsCount(self, typename):
        referents_count(typename)

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
        self._debug_service = G15DBUSDebugService(self.screen.service.dbus_service)
        self.text = g15text.new_text(self.screen)
        self.memory = 0
        self.resident = 0
        self.stack = 0
        self.only_refresh_when_visible = False
        g15plugin.G15RefreshingPlugin.activate(self)
        self.do_refresh()
    
    def deactivate(self):            
        self._silently_remove_from_connector(self._debug_service)              
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
        
    def _silently_remove_from_connector(self, obj):
        try:
            obj.remove_from_connection()
        except Exception:
            pass
        
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
    
