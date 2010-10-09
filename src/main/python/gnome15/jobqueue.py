#!/usr/bin/env python
############################################################################
##
## Copyright (C), all rights reserved:
##      2010 Brett Smith <tanktarta@blueyonder.co.uk>
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License version 2
##
## Graphics Tablet Applet
##
############################################################################

    
import Queue
import threading
import traceback
import sys

class JobQueue():
    
    class JobItem():
        def __init__(self, item, args):
            self.args = args
            self.item = item
        
    def __init__(self,number_of_workers=1,name="JobQueue"):
        self.work_queue = Queue.Queue()
        for __ in range(number_of_workers):
            t = threading.Thread(target = self.worker)
            t.name = name
            t.setDaemon(True)
            t.start()
            
    def clear(self):
        self.work_queue.clear()
            
    def run(self, item, *args):
        self.work_queue.put(self.JobItem(item, args))
            
    def worker(self):
        while True:
            item = self.work_queue.get()
            try:
                item.item(*item.args)
            except:
                traceback.print_exc(file=sys.stderr)
            self.work_queue.task_done()
 
