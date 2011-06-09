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
import gobject
import time

# Can be adjusted to aid debugging
TIME_FACTOR=1.0

# Logging
import logging
logger = logging.getLogger("jobs")

class GTimer:    
    def __init__(self, task_queue, task_name, interval, function, *args):
        if function == None:
            logger.warning("Attempt to run empty job %s on %s" % ( task_name, task_queue.name ) )
            traceback.print_stack()
            return
        
        self.task_queue = task_queue
        self.task_name = task_name
        self.source = gobject.timeout_add(int(float(interval) * 1000.0 * TIME_FACTOR), self.exec_item, function, *args)
        
    def exec_item(self, function, *args):
        logger.debug("Executing GTimer %s" % str(self.task_name))
        self.task_queue.run(function, *args)
        logger.debug("Executed GTimer %s" % str(self.task_name))
        
    def cancel(self, *args):
        gobject.source_remove(self.source)
        logger.debug("Cancelled GTimer %s" % str(self.task_name))
        
'''
Task scheduler. Tasks may be added to the queue to execute
after a specified interval. The timer is done by the gobject
event loop, which then executes the job on a different thread
'''

class JobScheduler():
    
    def __init__(self):
        self.queues = {}
        
    def schedule(self, name, interval, function, *args):
        return self.queue("default", name, interval, function, *args)
    
    def stop_all(self):
        logger.info("Stopping all queues")
        for queue_name in self.queues:
            self.queues[queue_name].stop()
    
    def clear_jobs(self, queue_name):
        if queue_name in self.queues:
            self.queues[queue_name].clear()
            
    def stop_queue(self, queue_name):
        self.queues[queue_name].stop()
    
    def execute(self, queue_name, name, function, *args):
        logger.debug("Executing on queue %s" % ( queue_name ) )     
        if not queue_name in self.queues:
            self.queues[queue_name] = JobQueue(name=queue_name)   
        self.queues[queue_name].run(function, *args)        
    
    def queue(self, queue_name, name, interval, function, *args):
        logger.debug("Queueing %s on %s for execution in %f" % ( name, queue_name, interval ) )
        if not queue_name in self.queues:
            self.queues[queue_name] = JobQueue(name=queue_name)
        timer = GTimer(self.queues[queue_name], name, interval, function, *args)
        logger.debug("Queued %s" % name)
        return timer


class JobQueue():
    
    class JobItem():
        def __init__(self, item, args = None):
            self.args = args
            self.item = item
            self.queued = time.time()
            self.started = None
            self.finished = None
        
    def __init__(self,number_of_workers=1, name="JobQueue"):
        logger.debug("Creating job queue %s with %d workers" % (name, number_of_workers))
        self.work_queue = Queue.Queue()
        self.name = name
        self.stopping = False
        self.lock = threading.Lock()
        self.number_of_workers = number_of_workers
        self.threads = []
        for __ in range(number_of_workers):
            t = threading.Thread(target = self.worker)
            t.name = name
            t.setDaemon(True)
            t.start()
            self.threads.append(t)
            
    def stop(self):
        logger.info("Stopping queue %s" % self.name)
        self.stopping = True
        self.clear()
        for i in range(0, self.number_of_workers):
            self.work_queue.put(self.JobItem(self._dummy))
        logger.info("Stopped queue %s" % self.name)
        
    def _dummy(self):
        pass
            
    def clear(self):
        jobs = self.work_queue.qsize()
        if jobs > 0:
            logger.info("Clearing queue %s as it has %d jobs" % ( self.name, jobs ) )
            try :
                while True:
                    item = self.work_queue.get_nowait()
                    logger.info("Removed func = %s, args = %s, queued = %s, started = %s, finished = %s" % ( str(item.item), str(item.args), str(item.queued), str(item.started), str(item.finished) ) )
            except Queue.Empty:
                pass
            logger.info("Cleared queue %s" % self.name)
            
    def run(self, item, *args):
        if self.stopping:
            return
        if item == None:
            logger.warning("Attempt to run empty job.")
            traceback.print_stack()
            return
        self.lock.acquire()
        try :
            logger.debug("Queued task on %s", self.name)
            self.work_queue.put(self.JobItem(item, args))
            jobs = self.work_queue.qsize()
            if jobs > 1:
                logger.debug("Queue %s filling, now at %d jobs." % (self.name, jobs ) )
                
        finally :
            self.lock.release()
            
    def worker(self):
        while not self.stopping:
            item = self.work_queue.get()
            try:
                if item != None:
                    logger.debug("Running task on %s", self.name)
                    item.started = time.time()
                    if item.args and len(item.args) > 0:
                        item.item(*item.args)
                    else:
                        item.item()
                    item.finished = time.time()
                    logger.debug("Ran task on %s", self.name)
            except:
                traceback.print_exc(file=sys.stderr)
            self.work_queue.task_done()
            
        if logger:
            logger.info("Exited queue %s" % self.name)
 
