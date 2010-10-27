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
        
    def __init__(self,number_of_workers=1,max_jobs=None,name="JobQueue"):
        self.work_queue = Queue.Queue()
        self.max_jobs = max_jobs
        self.lock = threading.Lock()
        for __ in range(number_of_workers):
            t = threading.Thread(target = self.worker)
            t.name = name
            t.setDaemon(True)
            t.start()
            
    def clear(self):
        try :
            while True:
                self.work_queue.get_nowait()
        except Queue.Empty:
            pass
            
    def run(self, item, *args):
        if item == None:
            sys.stderr.write("WARNING: Attempt to run empty job.")
            traceback.print_stack()
            return
        self.lock.acquire()
        try :
            if self.max_jobs != None:
                try :
                    while True:
                        self.work_queue.get(False)
                except Queue.Empty:
                    pass
            self.work_queue.put(self.JobItem(item, args))
        finally :
            self.lock.release()
            
    def worker(self):
        while True:
            item = self.work_queue.get()
            try:
                if item != None:
                    item.item(*item.args)
            except:
                traceback.print_exc(file=sys.stderr)
            self.work_queue.task_done()
 
