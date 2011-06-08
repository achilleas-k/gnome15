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
import time

# Can be adjusted to aid debugging
TIME_FACTOR=1.0

# Logging
import logging
logger = logging.getLogger("jobs")
        
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
            
    
    def execute(self, queue_name, name, function, *args):
        logger.debug("Executing on queue %s" % ( queue_name ) )     
        if not queue_name in self.queues:
            self.queues[queue_name] = JobQueue(name=queue_name)   
        return self.queues[queue_name].run(name, function, *args)        
        
    def stop_queue(self, queue_name):
        if not queue_name in self.queues:
            self.queues[queue_name].stop()
    
    def queue(self, queue_name, name, interval, function, *args):
        logger.debug("Queueing %s on %s for execution in %f" % ( name, queue_name, interval ) )
        if not queue_name in self.queues:
            self.queues[queue_name] = JobQueue(name=queue_name)
        job = self.queues[queue_name].queue(name, interval, function, *args)
        logger.debug("Queued %s" % name)
        return job                

class JobQueue():
    
    class JobItem():
        def __init__(self, queue, name, interval, item, args = None):
            self.name = name
            self.queue = queue
            self.args = args
            self.item = item
            self.queued = time.time()
            self.start_at = self.queued + interval
            self.started = None
            self.finished = None
            self.cancel_job = False
            
        def cancel(self):
            self.cancel_job = True
        
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
            self.work_queue.put(self.JobItem(self, "DummyJob", 0, self._dummy))
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
            
    def run(self, name, item, *args):
        return self.queue(name, 0.0, item, *args)
            
    def queue(self, name, interval, item, *args):
        if self.stopping:
            return None
        if item == None:
            raise Exception("Attempt to run empty job.")
        self.lock.acquire()
        try :
            logger.debug("Queued task on %s", self.name)
            job = self.JobItem(self, name, interval, item, args)
            self.work_queue.put(job)
            jobs = self.work_queue.qsize()
            if jobs > 1:
                logger.debug("Queue %s filling, now at %d jobs." % (self.name, jobs ) )
            return job                
        finally :
            self.lock.release()
            
    def worker(self):
        while not self.stopping:
            item = self.work_queue.get()
            try:
                if item != None:
                    logger.debug("Checking task on %s", self.name)
                    now = time.time()
                    if not item.cancel_job:
                        if now >= item.start_at:                    
                            logger.debug("Starting task on %s", self.name)
                            item.started = time.time()
                            if item.args and len(item.args) > 0:
                                item.item(*item.args)
                            else:
                                item.item()
                            item.finished = time.time()
                            logger.debug("Ran task on %s", self.name)
                        else:
                            # Job is not ready to run, put it back on the end of the queue
                            self.work_queue.put(item)
            except:
                logger.error("Error running job %s" % item.name)
                traceback.print_exc(file=sys.stderr)
            self.work_queue.task_done()
            time.sleep(0.1)
            
        if logger:
            logger.info("Exited queue %s" % self.name)
         
def test_job(no):
    print "Started %s!!" % no
    
if __name__ == "__main__":
    s = JobScheduler()
    s.schedule("test1", 5.0, test_job, 1)
    s.schedule("test3", 15.0, test_job, 3)
    s.schedule("test2", 10.0, test_job, 2)
