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

from telnetlib import Telnet
from threading import Thread
from threading import RLock
from message import MessageFactory
from message import Command

# Logging
import logging
logger = logging.getLogger(__name__)

def _receive_message(client):
    while True:
        incoming_message = client.read_until('\n', 10).strip()
        if incoming_message is not None and incoming_message.strip():
            logger.info("Received: %s" % incoming_message)
            message = MessageFactory.get_message(incoming_message)
            if message:
                return message

class TS3CommandException(Exception):
    
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code

class TS3():
    
    class ReceiveThread(Thread):
        def __init__(self, client):
            Thread.__init__(self)
            self._client = client
            self.setDaemon(True)
            self.setName("TS3ReceiveThread")
            self._reply_handler = None
            self._error_handler = None
            self._stop = False
            
        def stop(self):
            self._stop = True
        def run(self):
            try:
                while True:
                    try:
                        if self._stop:
                            raise EOFError()
                        msg = _receive_message(self._client)
                    except TS3CommandException as e:
                        logger.debug("Error while receving message", exc_info = e)
                        self._error_handler(e)
                    else:
                         self._reply_handler(msg)
            except Exception as e:
                logger.debug("Error in main loop", exc_info = e)
                self._error_handler(e)
    
    def __init__(self, hostname="127.0.0.1", port=25639, timeout=10):
        self.timeout = timeout
        self.hostname = hostname
        self.port = port
        
        self._event_client = None
        self._event_thread = None
        self._command_client = None
        self._lock = RLock()
        
        self.schandlerid = None
        
    def change_server(self, schandlerid):
        if self._event_client is not None:
            self._write_command(self._event_client, Command(
                                            'clientnotifyunregister')
                                      )
            
        self.schandlerid = schandlerid
        self._send_command(self._command_client, Command(
                                        'use',
                                        schandlerid=self.schandlerid)
                                  )       
        if self._event_client is not None:    
            self._send_command(self._event_client, Command(
                                            'use',
                                            schandlerid=self.schandlerid)
                                      )        
            self._send_command(self._event_client, Command(
                                            'clientnotifyregister',
                                            schandlerid=self.schandlerid,
                                            event=self._event_type
                                            )
                                      )
        
    def close(self):
        if self._event_thread is not None:
            self._event_thread.stop()
        self._command_client.close()
        self._command_client = None
        if self._event_client is not None:
            self._event_client.close()
            self._event_client = None
    
    def start(self):
        self._create_command_client()
        
        
    def send_event_command(self, command):
        try:   
            self._lock.acquire()
            if self._event_client is not None:
                self._write_command(self._event_client, command)                        
        finally:
            self._lock.release()
        
    def send_command(self, command):  
        try:   
            self._lock.acquire()
            if self._command_client is None:
                self.start()   
            return self._send_command(self._command_client, command)                        
        finally:
            self._lock.release()

    def subscribe(self, reply_handler, type='any', error_handler = None):
        """
        Shortcut method to subscribe to all messages received from the client.
        
        Keyword arguments:
        reply_handler   -- function called with Message as argument
        error_handler   -- function called with TSCommandException as argument
        type            -- type of event to subscribe to
        """
        try:
            self._lock.acquire()
        
            if self._event_client is not None:
                raise Exception("Already subscribed")
            
            self._event_type = type
            self._create_event_client()
            self._event_thread._reply_handler = reply_handler
            self._event_thread._error_handler = error_handler
            self._write_command(self._event_client, Command(
                                            'clientnotifyregister',
                                            schandlerid=self.schandlerid,
                                            event=type
                                            )
                                      )
            
        finally:
            self._lock.release()
                
            
    """
    Private
    """
    def _send_command(self, client, command):  
        try:   
            self._lock.acquire()
            self._write_command(client, command)
            r_reply = None
            while True:
                reply = _receive_message(client)
                if reply.command == 'error':
                    msg = reply.args['msg']
                    if msg != 'ok':
                        raise TS3CommandException(int(reply.args['id']), msg)
                    else:
                        break
                else:
                    if r_reply is None:
                        r_reply = reply
                    else:
                        raise TS3CommandException(9999, "Multiple replies")
                        
                    
            return r_reply
        finally:
            self._lock.release()
        
    def _write_command(self, client, command):
        logger.info("Sending command: %s" % command.output)
        client.write("%s\n" % command.output)
    
    def _create_command_client(self):
        self._command_client = Telnet(host=self.hostname, port=self.port)
        self.schandlerid = int(_receive_message(self._command_client).args['schandlerid'])
    
    def _create_event_client(self):
        self._event_client = Telnet(host=self.hostname, port=self.port)
        _receive_message(self._event_client)
        self._event_thread = self.ReceiveThread(self._event_client)
        self._event_thread.start()