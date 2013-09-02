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

import gc
import weakref
import objgraph

#gc.set_debug(gc.DEBUG_LEAK)


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
         