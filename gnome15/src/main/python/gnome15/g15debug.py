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

import gc

EXCLUDED = [ 
            "instancemethod", 
            "weakref", 
            "instance",
            "frame",
            "function",
            "builtin_function_or_method",
            "builtin_function_or_method",
            ]

class Snapshot():
    
    def __init__(self):
        self.stats = {}
        self.objects = {} 
    
def take_snapshot():
    snapshot = Snapshot()
    for o in gc.get_objects():
        k = type(o).__name__
        if not k in EXCLUDED:
            snapshot.stats.setdefault(k, 0)
            snapshot.stats[k] += 1
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
                
def _do_types(snapshot1, snapshot2, types, show_removed = True):
    for k in types:
        print "%4s%-30s %10d (was %d)" % ("",k, snapshot2.stats[k], snapshot1.stats[k] if k in snapshot1.stats else 0)
        old_objects = snapshot1.objects[k] if k in snapshot1.objects else []
        new_objects = snapshot2.objects[k] if k in snapshot2.objects else []
        
        # Find any objects removed
        if show_removed:
            try :
                for x in old_objects:
                    in_new = False
                    try:
                        in_new = x in new_objects
                    except:
                        pass
                    if not in_new:
                        try :
                            _do_obj(x, "Removed")
                        except:
                            print "%12Error!" % ""
            except:
                print "%8sError iterating old objects!" % ""
                
        # Find any objects added
        try :
            for x in new_objects:
                in_old = False
                try:
                    in_old = x in old_objects
                except:
                    pass
                if not in_old:
                    try :
                        _do_obj(x, "Added")
                    except:
                        print "        Error!"
        except:
            print "        Error iterating new objects!"
            
def _do_obj(o, s):
    if isinstance(o, list) and len(o) > 0:
        # Ignore the list if it contains excluded items        
        if type(o[0]).__name__ in EXCLUDED:
            return
    elif isinstance(o, dict) and len(o) > 0:
        # Ignore the list if it contains excluded items        
        if type(o.iteritems()[0]).__name__ in EXCLUDED or type(o.iteritems()[1]).__name__ in EXCLUDED:
            return
    elif isinstance(o, tuple) and len(o) > 0:
        # Ignore the list if it contains excluded items        
        for v in o:
            if type(v).__name__ in EXCLUDED:
                return
        
    o_str = _max_len(o, 60)
    print "%12s%8s : %-30s %-60s" % ("",s, type(o).__name__, o_str)
        
def _max_len(o, l):
    o_str = str(o)
    if len(o_str) > l:
        o_str = o_str[:l]
    return o_str

import time            
if __name__ == "__main__":
    print "Creating snapshot1"
    snapshot1 = take_snapshot()    
    print "Creating some objects"    
    l = [ "A", "B", "C", "D", "E" ]  
    print "Creating snapshot2"
    snapshot2 = take_snapshot()  
    print "Comparing"
    compare_snapshots(snapshot1, snapshot2)
         