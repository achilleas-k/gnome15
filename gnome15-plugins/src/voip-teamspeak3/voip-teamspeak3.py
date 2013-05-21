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
id="voip-teamspeak3"
name=_("Teamspeak3")
description=_("Provides integration with TeamSpeak3. Note, this plugin also\n\
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
logger = logging.getLogger("voip-teamspeak3")

"""
Calendar Back-end module functions
"""

def create_backend():
    return Teamspeak3Backend()

def find_avatar(server_unique_identifier, client_unique_identifier):
    decoded = ""
    for c in base64.b64decode(client_unique_identifier):
        decoded += chr(((ord(c) & 0xf0) >> 4) + 97)
        decoded += chr((ord(c) & 0x0f) + 97)
    return os.path.expanduser("~/.ts3client/cache/%s/clients/avatar_%s" % (base64.b64encode(server_unique_identifier), decoded))

"""
Teamspeak3 backend
"""

class Teamspeak3BuddyMenuItem(voip.BuddyMenuItem):
    
    def __init__(self, db_id, clid, nickname, channel, client_type, plugin):
        voip.BuddyMenuItem.__init__(self, "client-%s" % clid, nickname, channel, plugin)
        self.db_id = db_id
        self.clid = clid
        self.client_type = client_type
        self.avatar = None
        self.uid = None
        
    def set_uid(self, server_uid, uid):
        self.uid = uid 
        self.avatar = find_avatar(server_uid, uid)
        
class Teamspeak3ServerMenuItem(voip.ChannelMenuItem):
    
    def __init__(self, schandlerid, name, backend):
        voip.ChannelMenuItem.__init__(self, "server-%s" % schandlerid, name, backend, icon=g15util.get_icon_path(['server', 'redhat-server', 'network-server', 'redhat-network-server', 'gnome-fs-server' ], include_missing=False))
        self.schandlerid = schandlerid
        self.activatable = False
        self.radio = False
        self.path = ""
        
class Teamspeak3ChannelMenuItem(voip.ChannelMenuItem):
    
    def __init__(self, schandlerid, cid, cpid, name, order, backend):
        voip.ChannelMenuItem.__init__(self, "channel-%s-%d" % (cid, schandlerid), name, backend)
        self.group = False
        self.cid = cid
        self.cpid = cpid
        self.order = order
        self._backend = backend
        self.schandlerid = schandlerid

    @property
    def path(self):
        result = self.name
        if self.cpid != 0:
            parent_item = self.backend._channel_map[self.cpid]
            result = parent_item.path + "/" + result
        return result

    @property
    def parent_count(self):
        result = 0
        if self.cpid != 0:
            parent_item = self.backend._channel_map[self.cpid]
            result = 1 + parent_item.parent_count
        return result

    def get_theme_properties(self):
        p = voip.ChannelMenuItem.get_theme_properties(self)
        p["item_name"] = self.parent_count * "  " + p["item_name"]
        return p

    def on_activate(self):
        if self._backend._client.schandlerid != self.schandlerid:
            self._backend._client.change_server(self.schandlerid)
        self._backend.set_current_channel(self)
        return True
        
class Teamspeak3Backend(voip.VoipBackend):
    
    def __init__(self):
        voip.VoipBackend.__init__(self)
        self._buddies = None
        self._buddy_map = {}
        self._channels = None
        self._channels_map = {}
        self._me = None
        self._clid = None
        self._server_uid = None
        self._client = None
        self._current_channel = None
    
    def get_talking(self):
        if self._buddies is not None:
            for d in self._buddies:
                if d.talking:
                    return d
                
    def set_current_channel(self, channel_item):
        try:
            reply = self._client.send_command(ts3.Command(
                    'clientmove',              
                    clid=self._clid,
                    cid=channel_item.cid
                ))

        except ts3.TS3CommandException as e:
            traceback.print_exc()
    
    def get_current_channel(self):
        if self._current_channel is None:
            if self._channels is None:
                self.get_channels()
                
            reply = self._client.send_command(
                        ts3.Command(
                                'channelconnectinfo'
                            ))
            if 'path' in reply.args:
                channel_path = reply.args['path']
                for c in self._channels:
                    if c.path == channel_path:
                        self._current_channel = c
            
        return self._current_channel
    
    def get_buddies(self):
        if self._buddies == None:
            self._buddy_map = {}
            # Get the basic details  
            reply = self._client.send_command(
                        ts3.Command(
                                'clientlist -away -voice -uid'
                            ))
            self._parse_clientlist_reply(reply)
            
        return self._buddies
    
    def get_channels(self):
        if self._channels == None:
            self._channel_map = {}
            self._channels = []

            reply = self._client.send_command(ts3.Command(
                    'serverconnectionhandlerlist'))
            
            for r in reply.responses if isinstance(reply, ts3.message.MultipartMessage) else [ reply ]:
                s = int(r.args['schandlerid'])
                reply = self._client.send_command(ts3.Command(
                        'use', schandlerid = s))

                # Get the server IP and port
                try:
                    reply = self._client.send_command(ts3.Command(
                            'serverconnectinfo'))
                    ip = reply.args['ip']
                    port = int(reply.args['port'])
     
                    # A menu item for the server                
                    item = Teamspeak3ServerMenuItem(s, "%s:%d" % (ip, port), self)
                    self._channels.append(item)
                    
                    reply = self._client.send_command(
                                ts3.Command(
                                        'channellist'
                                    ))
                    self._parse_channellist_reply(reply, s)
                except ts3.TS3CommandException:
                    traceback.print_exc()
                    
        
            # Switch back to the selected server connection
            reply = self._client.send_command(ts3.Command(
                    'use', schandlerid = self._client.schandlerid))
            
        return self._channels
    
    def get_name(self):
        return _("Teamspeak3")
    
    def start(self, plugin):
        self._plugin = plugin
        self._client = ts3.TS3()
        
        # Connect to ClientQuery plugin
        try :
            self._client.start()
        except socket.error, v:
            self._client = None
            error_code = v[0]
            if error_code == errno.ECONNREFUSED:
                return False
            raise v
        
        # Get initial buddy lists, channel lists and other stuff 
        try:        
            self._get_clid()
            self._get_server_uid()
            self.get_channels()
            self.get_current_channel()
            self.get_buddies()
            self._client.subscribe(self._handle_message, "any", self._handle_error)
            
            return True
        except ts3.TS3CommandException as e:
            self._client.close()
            self._client = None
            if e.code == 1794:
                # Not connected to server
                return False
            else:
                raise e
        except Exception as e:
            self._client.close()
            self._client = None
            raise e
        
    def is_connected(self):
        return self._client is not None
    
    def stop(self): 
        if self._client is not None:
            self._client.close()
            self._client = None
    
    def get_me(self):
        return self._me
    
    def get_icon(self):
        return os.path.join(os.path.dirname(__file__), "logo.png")
    
    def kick(self, buddy):
        reply = self._client.send_command(ts3.Command(
            'clientkick', clid = buddy.clid, reasonid = 5, reasonmsg = 'No reason given'))
        logger.info("Kicked %s (%s)" % (buddy.nickname, buddy.clid) )
    
    def ban(self, buddy):
        if buddy.uid is None:
            raise Exception("UID is not known")        
        reply = self._client.send_command(ts3.Command(
            'banadd', banreason = 'No reason given', uid = buddy.uid))
        logger.info("Banned %s (%s)" % (buddy.nickname, buddy.uid) )
        
    def away(self):
        reply = self._client.send_command(ts3.Command(
                    'clientupdate',              
                    client_away=1
                ))
    
    def online(self):
        reply = self._client.send_command(ts3.Command(
                    'clientupdate',              
                    client_away=0
                ))
    
    def set_audio_input(self, mute):
        reply = self._client.send_command(ts3.Command(
                    'clientupdate',              
                    client_input_muted=1 if mute else 0
                ))
    
    def set_audio_output(self, mute):
        reply = self._client.send_command(ts3.Command(
                    'clientupdate',              
                    client_output_muted=1 if mute else 0
                ))
    
    """
    Private
    """
    def _handle_error(self, error):
        print error
        if isinstance(error, EOFError):
            self._disconnected()
        else:
            logger.warn("Teamspeak3 error. %s" % str(error))
        
    def _handle_message(self, message):
        print message.command
        try:
            if message.command == 'notifyclientupdated':
                self._parse_notifyclientupdated(message)
                self._do_redraw()
            elif message.command == 'notifyclientpermlist':
                self._parse_notifyclientpermlist_reply(message)
            elif message.command == 'notifytextmessage':
                self._parse_notifytextmessage_reply(message)
            elif message.command == 'notifytalkstatuschange':
                self._parse_notifytalkstatuschange_reply(message)
            elif message.command == 'notifyclientchannelgroupchanged':
                self._parse_notifyclientchannelgroupchanged_reply(message)
            elif message.command == 'notifycliententerview':
                self._parse_notifycliententerview_reply(message)
            elif message.command == 'notifyclientleftview':
                self._parse_notifyclientleftview_reply(message)
            elif message.command == 'notifyconnectstatuschange':
                self._parse_notifyconnectstatuschange_reply(message)
            elif message.command == 'notifychannelcreated':
                self._parse_notifychannelcreated_reply(message)
            elif message.command == 'notifychanneledited':
                self._parse_notifychanneledited_reply(message)
            elif message.command == 'notifychanneldeleted':
                self._parse_notifychanneldeleted_reply(message)
            elif message.command == 'notifycurrentserverconnectionchanged':
                self._parse_notifycurrentserverconnectionchanged_reply(message)
                
                
                
                
        except:
            logger.error("Possible corrupt reply.")
            traceback.print_exc()
                
    def _disconnected(self):
        print "disconnex"
        self._plugin._disconnected()
        
    def _create_channel_item(self, message, schandlerid):
        item = Teamspeak3ChannelMenuItem(schandlerid, int(message.args['cid']), 
                                   int(message.args['cpid']) if 'cpid' in message.args else int(message.args['pid']),
                                   message.args['channel_name'],
                                   int(message.args['channel_order']), self)
        if 'channel_topic' in message.args:
            item.topic = message.args['channel_topic']
        return item
        
    def _create_menu_item(self, message, channel = None):
        return Teamspeak3BuddyMenuItem(int(message.args['client_database_id']), 
                                   int(message.args['clid']), 
                                   message.args['client_nickname'],
                                   channel,
                                   int(message.args['client_type']),
                                   self._plugin)
        
    def _get_clid(self):
        reply = self._client.send_command(ts3.Command(
            'whoami', virtualserver_unique_identifier=None
        ))
        self._clid = int(reply.args['clid'])
        logger.info("Your CLID is %d" % self._clid)
    
    def _get_server_uid(self):
        reply = self._client.send_command(ts3.Command(
            'servervariable', virtualserver_unique_identifier=None
            
        ))
        self._server_uid = reply.args['virtualserver_unique_identifier']
        
    def _do_redraw(self):
        self._plugin.redraw()
        
    def _update_item_from_message(self, item, message):
        if 'client_input_muted' in message.args:
            item.input_muted = message.args['client_input_muted'] == '1'
        if 'client_output_muted' in message.args:
            item.output_muted = message.args['client_output_muted'] == '1'
        if 'client_away' in message.args:
            item.away = message.args['client_away'] == '1'
        if 'client_away_message' in message.args:
            a = message.args['client_away_message']
            if a and len(a) > 0: 
                item.away = a
        if 'client_unique_identifier' in message.args:
            item.set_uid(self._server_uid, message.args['client_unique_identifier'])
            
    def _my_channel_changed(self):
        self._current_channel = None
        self.get_current_channel()
        self._buddies = None
        self._plugin.reload_buddies()
            
    """
    Reply handlers
    """
    def _parse_notifycurrentserverconnectionchanged_reply(self, message):
        self._client.change_server(int(message.args['schandlerid']))
        self._my_channel_changed()
    
    def _parse_notifychanneledited_reply(self, message):
        item = self._channel_map[int(message.args['cid'])]
        if 'channel_topic' in message.args:
            item.topic = message.args['channel_topic']
        if 'channel_name' in message.args:
            if self._current_channel is not None and item.name == self._current_channel:
                self._current_channel = None 
            item.name = message.args['channel_name']
            if self._current_channel is None:
                self.get_current_channel()
        self._plugin.channel_updated(item)
        
    def _parse_notifyclientpermlist_reply(self, message):
        pass
        
    def _parse_notifychanneldeleted_reply(self, message):
        item = self._channel_map[int(message.args['cid'])]
        position = self._channels.index(item)

        # Update the following item order if necessary
        try:
            next_item = self._channels[position + 1]
            if next_item.cpid == item.cpid:
                next_item.order = item.order
        except IndexError:
            pass

        self._channels.remove(item)
        del self._channel_map[item.cid]
        self._plugin.channel_removed(item)

    def _find_teamspeak3servermenuitem(self, id):
        matching_items = [ x for x in self._channels if x.schandlerid == id and type(x) is Teamspeak3ServerMenuItem ]
        if len(matching_items) > 0:
            return matching_items[0]
        else:
            return None
        
    def _parse_notifychannelcreated_reply(self, message):
        item = self._create_channel_item(message, self._client.schandlerid)
        # Insert the item at the correct position in the menu
        if item.cpid == 0 and item.order == 0:
            # If first channel of server
            position = self._channels.index(self._find_teamspeak3servermenuitem(item.schandlerid)) + 1
        elif item.order == 0:
            # If first sub-channel of a channel
            position = self._channels.index(self._channel_map[item.cpid]) + 1
        else:
            # Other cases
            position = self._channels.index(self._channel_map[item.order]) + 1
        self._channels.insert(position, item)
        self._channel_map[item.cid] = item
        self._plugin.new_channel(item)

        # Update the following item order if necessary
        try:
            next_item = self._channels[position + 1]
            if next_item.cpid == item.cpid:
                next_item.order = item.cid
        except IndexError:
            pass
    
    def _parse_notifyconnectstatuschange_reply(self, message):
        status = message.args['status']
        if status == "disconnected":
            logger.info("Disconnected from server. Stopping client")
            self.stop()
        
    def _parse_notifyclientleftview_reply(self, message):
        clid = int(message.args['clid'])
        if clid in self._buddy_map:
            item = self._buddy_map[clid]
            self._buddies.remove(item)
            del self._buddy_map[clid]
            self._plugin.buddy_left(item)
            self._do_redraw()
        else:
            logger.warning("Client left that we knew nothing about yet (%d)" % clid)
        
    def _parse_notifycliententerview_reply(self, message):
        reply= self._client.send_command(ts3.Command(
                        'clientvariable',              
                        clid=message.args['clid']
                    ))
        item = self._create_menu_item(message, None)
        item.channel = self._channel_map[int(message.args['ctid'])]
        self._buddies.append(item)
        self._buddy_map[item.clid] = item
        self._update_item_from_message(item, message)
        c = self._plugin.new_buddy(item)
        
    def _parse_notifyclientchannelgroupchanged_reply(self, message):
        if int(message.args['clid']) == self._clid:
            self._my_channel_changed()
        else:
            buddy_id = int(message.args['clid'])
            buddy = self._buddy_map[buddy_id]
            new_channel_id = int(message.args['cid'])
            new_channel = self._channel_map[new_channel_id]
            old_channel = buddy.channel
            buddy.channel = new_channel
            self._plugin.moved_channels(buddy, old_channel, new_channel)
        
    def _parse_clientlist_reply(self, message):
        items = []
        item_map = {}
        for r in message.responses if isinstance(message, ts3.message.MultipartMessage) else [ message ]:
            ch = self._channel_map[int(r.args['cid'])]
            item = self._create_menu_item(r, ch)
            self._update_item_from_message(item, r)
            items.append(item)
            item_map[item.clid] = item
            if item.clid == self._clid:
                self._me = item
        self._buddies = items    
        self._buddy_map = item_map    

    def _sort_channellist(self, channels):
        """
        Sort the channel list the same way that it's done in TeamSpeak3
        """
        result = []
        search_stack = []
        # Initialize the search stack with the criteria for the first item (always 0,0)
        search_stack.append((0, 0))
        while len(channels) > len(result):
            search_criteria = search_stack.pop()
            try:
                item = channels[search_criteria]
                result.append(item)
                search_stack.append((item.cpid, item.cid))
                search_stack.append((item.cid, 0))
            except KeyError:
                continue

        return result

    def _parse_channellist_reply(self, message, schandlerid):
        channels = {}
        for r in message.responses if isinstance(message, ts3.message.MultipartMessage) else [ message ]:
            item = self._create_channel_item(r, schandlerid)
            channels[item.cpid, item.order] = item
            self._channel_map[item.cid] = item

        self._channels.extend(self._sort_channellist(channels))

    def _parse_notifyclientupdated(self, message):
        item = self._buddy_map[int(message.args['clid'])]
        self._update_item_from_message(item, message)
        item.mark_dirty()
            
    def _parse_notifytextmessage_reply(self, message):
        if 'invokername' in message.args and 'msg' in message.args:
            self._plugin.message_received(message.args['invokername'], message.args['msg'])
        else:
            logger.warn("Got text messsage I didn't understand. %s" % str(message))
            
    def _parse_notifytalkstatuschange_reply(self, message):
        clid = int(message.args['clid'])
        if clid in self._buddy_map:
            item = self._buddy_map[clid]
            item.talking = message.args['status'] == '1'
            item.mark_dirty()
            if not self._plugin.menu.is_focused():
                self._plugin.menu.selected = item     
                self._plugin.menu.centre_on_selected()
            
            self._plugin.talking_status_changed(self.get_talking())
