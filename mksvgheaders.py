#!/usr/bin/env python2
 
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

from lxml import etree

# Logging
import logging
logging.basicConfig(format='%(levelname)s:%(asctime)s:%(threadName)s:%(name)s:%(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger()

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

nsmap = {
    'sodipodi': 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
    'cc': 'http://web.resource.org/cc/',
    'svg': 'http://www.w3.org/2000/svg',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'xlink': 'http://www.w3.org/1999/xlink',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'inkscape': 'http://www.inkscape.org/namespaces/inkscape',
    }
        
if __name__ == "__main__":
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-l", "--log", dest="log_level", metavar="INFO,DEBUG,WARNING,ERROR,CRITICAL",
        default="warning" , help="Log level")
    (options, args) = parser.parse_args()
    
    level = logging.NOTSET
    if options.log_level != None:      
        level = LEVELS.get(options.log_level.lower(), logging.NOTSET)
        logger.setLevel(level = level)
        
    for f in args:        
        document = etree.parse(f)
        root = document.getroot()
        for text in root.xpath('//text()',namespaces=nsmap):
            text = str(text).strip()
            if len(text) > 0 and text.startswith("_("):
                print "char *s = N_(\"%s\");" % text[2:-1]
