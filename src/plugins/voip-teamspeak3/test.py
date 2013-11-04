#!/usr/bin/env python

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

import ts3
import logging
 
if __name__ == "__main__":
    
    logging.basicConfig(format='%(levelname)s:%(asctime)s:%(threadName)s:%(name)s:%(message)s', datefmt='%H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.setLevel(level = logging.INFO)
    
    t = ts3.TS3()
    t.start()
    
    logger.info("schandlerid : %d", t.schandlerid)
    
    
    logger.info("channel: %s", t.send_command(ts3.Command('channelconnectinfo')).args['path'])
    