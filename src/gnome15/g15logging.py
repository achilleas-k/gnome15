#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
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

"""
Initializes and configures the python logging system that is used in Gnome15
"""
import logging

DEFAULT_LEVEL = logging.NOTSET

def configure():
    """
    Configures the logging python module with a basic configuration
    and a logging format.
    """
    logging.basicConfig(format='%(levelname)s\t%(asctime)s-%(threadName)s\t%(name)s - %(message)s',
                        datefmt='%H:%M:%S')

def get_level(level):
    """
    Returns the python logging module level matching the string passed
    as parameter, or the default logging level if the string doesn't
    match any level.
    """
    result = logging.getLevelName(level.upper())
    if result == "Level %s" % level:
        result = DEFAULT_LEVEL
    return result

def get_root_logger():
    """
    Initializes the logging system with a basic configuration, and
    creates a root logger set to the default logging level.
    """
    configure()
    logger = logging.getLogger()
    logger.setLevel(DEFAULT_LEVEL)
    return logger
