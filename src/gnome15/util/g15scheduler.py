#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2010 Brett Smith <tanktarta@blueyonder.co.uk>
#  Copyright (C) 2013 Nuno Araujo <nuno.araujo@russo79.com>
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

import gobject
import g15pythonlang

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
    if g15pythonlang.is_gobject_thread():
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
