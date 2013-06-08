############################################################################
##
## Copyright (C), all rights reserved:
##      2013 Nuno Araujo <nuno.araujo@russo79.com>
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License version 2
##
## Gnome15 - Suite of GNOME applications that work with the logitech G15
##           keyboard
##
############################################################################

import gobject
import g15util

# Logging
import logging
logger = logging.getLogger("scheduler")

import jobqueue

'''
Default scheduler
'''
scheduler = jobqueue.JobScheduler()

'''
Task scheduler. Tasks may be added to the queue to execute
after a specified interval. The timer is done by the gobject
event loop, which then executes the job on a different thread
'''

def clear_jobs(queue_name = None):
    scheduler.clear_jobs(queue_name)

def execute(queue_name, job_name, function, *args):
    return scheduler.execute(queue_name, job_name, function, *args)

def schedule(job_name, interval, function, *args):
    return scheduler.schedule(job_name, interval, function, *args)

def run_on_gobject(function, *args):
    if g15util.is_gobject_thread():
        return False
    else:
        gobject.idle_add(function, *args)
        return True

def stop_queue(queue_name):
    scheduler.stop_queue(queue_name)

def queue(queue_name, job_name, interval, function, *args):
    return scheduler.queue(queue_name, job_name, interval, function, *args)

def stop_all_schedulers():
    scheduler.stop_all()
