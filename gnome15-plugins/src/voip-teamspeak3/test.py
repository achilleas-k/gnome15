#!/usr/bin/env python

import ts3
import logging
 
if __name__ == "__main__":
    
    logging.basicConfig(format='%(levelname)s:%(asctime)s:%(threadName)s:%(name)s:%(message)s', datefmt='%H:%M:%S')
    logger = logging.getLogger()
    logger.setLevel(level = logging.INFO)
    
    t = ts3.TS3()
    t.start()
    
    logger.info("schandlerid : %d" % t.schandlerid)
    
    
    logger.info("channel: %s"  % ( t.send_command(
                ts3.Command(
                        'channelconnectinfo'
                    ) ).args['path'] ))
    