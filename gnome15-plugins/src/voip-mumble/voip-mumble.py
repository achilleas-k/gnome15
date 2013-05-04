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
#

import gnome15.g15locale as g15locale
_ = g15locale.get_translation("voip-mumble", modfile = __file__).ugettext

import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import ts3
import traceback
from threading import Thread
from threading import Lock
from threading import RLock
from threading import Semaphore
import voip
import os
import base64
import socket
import errno

# Plugin details 
id="voip-mumble"
name=_("Mumble")
description=_("Provides integration with Mumble. Note, this plugin also\n\
requires the 'Voip' plugin as well which provides the user interface.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2011 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]

# This plugin only supplies classes to the 'voip' plugin and so is never activated 
passive=True 
global_plugin=True

# Logging
import logging
logger = logging.getLogger("voip-mumble")

"""
Calendar Back-end module functions
"""

def create_backend():
    return MumbleBackend()

"""
Mumble backend
"""

class MumbleBackend(voip.VoipBackend):
    
    def __init__(self):
        voip.VoipBackend.__init__(self)
    
    def get_name(self):
        raise _("Mumble")
    
    def start(self, plugin):
        raise Exception("Not implemented")
    
    def stop(self):
        raise Exception("Not implemented")
    
    def get_current_channel(self):
        """
        Get the current channel
        """
        raise Exception("Not implemented")
    
    def get_talking(self):
        """
        Get who is talking
        """
        raise Exception("Not implemented")
    
    def get_me(self):
        """
        Get the local user's buddy entry
        """
        raise Exception("Not implemented")
    
    def get_channels(self):
        raise Exception("Not implemented")
    
    def get_buddies(self, current_channel=True):
        raise Exception("Not implemented")
    
    def get_icon(self):
        raise Exception("Not implemented")
    
    def set_audio_input(self, mute):
        raise Exception("Not implemented")
    
    def set_audio_output(self, mute):
        raise Exception("Not implemented")
    
    def away(self):
        raise Exception("Not implemented")
    
    def online(self):
        raise Exception("Not implemented")
