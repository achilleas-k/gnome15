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
_ = g15locale.get_translation("voip-teamspeak3", modfile = __file__).ugettext

import gnome15.g15driver as g15driver
import teamspeak3
import traceback
from threading import Thread
from threading import Lock
import voip
import os

# Plugin details 
id="voip-teamspeak3"
name=_("Teamspeak3")
description=_("Provides integration with TeamSpeak3. Note, this plugin also\n\
requires the 'Voip' plugin as well which provides the user interface.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2011 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]

# This plugin only supplies classes to the 'voip' plugin and so is never activated 
passive=True 
global_plugin=True

# Logging
import logging
logger = logging.getLogger("voip-teamspeak3")

"""
Calendar Back-end module functions
"""

def create_backend():
    return Teamspeak3Backend()

"""
Teamspeak3 backend
"""

class Teamspeak3Backend(voip.VoipBackend):
    
    class ReplyThread(Thread):
        def __init__(self, backend):
            Thread.__init__(self)
            self.setDaemon(True)
            self.setName('TS3ReplyThread')
            self.stay_running = True
            self._backend = backend
            
        def run(self):
            try:
                while self.stay_running:
                    messages = self._backend._client.get_messages()
                    for message in messages:
                        if not message.is_response() and message.command == 'notifyclientupdated':
                            self._backend._parse_notifyclientupdated(message)
                        elif message.is_response() and message.origination.command == 'whoami':
                            self._backend._parse_whoami(message)
                        elif message.is_response() and message.origination.command == 'clientlist':
                            self._backend._parse_clientlist_reply(message)
                        elif message.is_response() and message.origination.command == 'clientvariable':
                            self._backend._parse_clientvariable_reply(message)
                        elif not message.is_response() and message.command == 'notifytextmessage':
                            self._backend._parse_notifytextmessage_reply(message)
                        elif not message.is_response() and message.command == 'notifytalkstatuschange':
                            self._backend._parse_notifytalkstatuschange_reply(message)
                            
            except teamspeak3.TeamspeakConnectionTelnetEOF:
                # Disconnected
                traceback.print_exc()
                self._backend._disconnected()
    
    def __init__(self):
        voip.VoipBackend.__init__(self)
        self._lock = Lock()
        self._buddies = []
        self._buddy_map = {}
        self._me = None
        self._clid = None
        self._client = None
    
    def get_buddies(self):
        
        # Get the basic details  
        self._lock.acquire()     
        self._client.send_command(
                    teamspeak3.Command(
                            'clientlist'
                        ))
        self._lock.acquire()
        self._lock.release()
        
        # Fill in the blanks
        for clid in self._buddy_map:
            command = teamspeak3.Command(
                    'clientvariable',              
                    clid=clid,
                    client_input_muted=None,
                    client_output_muted=None,
                    client_away=None,
                    client_away_message=None
                )
            self._lock.acquire()     
            self._client.send_command(command)
            self._lock.acquire()
            self._lock.release()
        
        return self._buddies
    
    def start(self, plugin):
        self._plugin = plugin
        self._thread = self.ReplyThread(self)
        self._client = teamspeak3.Client()
        self._thread.start()
        self._client.subscribe()
        
        # Although python-teamspeak calls whoami, it doesn't store the clid.
        # Neither do we get the chance to add our listener, so we must send a
        # second whoami to find out our own clid 
        command = teamspeak3.Command(
                'whoami',
            )
        self._client.send_command(command)
    
    def stop(self): 
        self._thread.stay_running = False
        
        """
        This seems to send a signal (SIGTERM) to g15-desktop-service as well, causing
        it to think it needs to shutdown. I think this is because teamspeak3 uses
        sub-processes
        """ 
        self._plugin.screen.service.ignore_next_sigint = True
        if self._client is not None:
            self._client.close()
            self._client = None
    
    def get_me(self):
        return self._me
    
    def get_icon(self):
        return os.path.join(os.path.dirname(__file__), "logo.png")
    
    """
    Private
    """
    def _disconnected(self):
        self._plugin._disconnected()
        
    def _parse_clientvariable_reply(self, message):
        self._parse_notifyclientupdated(message)        
        self._lock.release()
        
    def _parse_clientlist_reply(self, message):
        items = []
        item_map = {}
        
        #
        # NOTE: python-teamspeak doesn't return a list when there is only one client, report to author
        #
        for r in message.responses if isinstance(message, teamspeak3.message.MultipartMessage) else [ message ]:
            clid = r.args['clid']
            item = voip.BuddyMenuItem(int(r.args['client_database_id']), 
                                       int(clid), 
                                       r.args['client_nickname'],
                                       int(r.args['client_type']))
            items.append(item)
            item_map[clid] = item
            if clid == self._clid:
                self._me = item
        self._buddies = items    
        self._buddy_map = item_map    
        self._lock.release()
        
    def _parse_whoami(self, message):
        self._clid = message.args['clid']
        logger.info("Your CLID is %s" % self._clid)
        
    def _parse_notifyclientupdated(self, message):
        if 'client_input_muted' in message.args:
            item = self._buddy_map[message.args['clid']]
            item.input_muted = message.args['client_input_muted'] == '1'
            item.mark_dirty()
            self._plugin.page.mark_dirty()
            self._plugin.page.redraw()
        if 'client_output_muted' in message.args:
            item = self._buddy_map[message.args['clid']]
            item.output_muted = message.args['client_output_muted'] == '1'
            item.mark_dirty()
            self._plugin.page.mark_dirty()
            self._plugin.page.redraw()
        if 'client_away' in message.args:
            item = self._buddy_map[message.args['clid']]
            item.away = message.args['client_away'] == '1'
            item.mark_dirty()
            self._plugin.page.mark_dirty()
            self._plugin.page.redraw()
        if 'client_away_message' in message.args:
            item = self._buddy_map[message.args['clid']]
            a = message.args['client_away_message']
            if a and len(a) > 0: 
                item.away = a
                item.mark_dirty()
                self._plugin.page.mark_dirty()
                self._plugin.page.redraw()
            
    def _parse_notifytextmessage_reply(self, message):
        if 'invokername' in message.args and 'msg' in message.args:
            self._plugin.message_received(message.args['invokername'], message.args['msg'])
        else:
            logger.warn("Got text messsage I didn't understand. %s" % str(message))
            
    def _parse_notifytalkstatuschange_reply(self, message):
        item = self._buddy_map[message.args['clid']]
        item.talking = message.args['status'] == '1'
        item.mark_dirty()
                   
        self._plugin.page.mark_dirty()
        self._plugin.page.redraw()
        self._plugin._popup()
        
