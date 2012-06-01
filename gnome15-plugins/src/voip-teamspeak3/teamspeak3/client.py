# Copyright (c) 2012 Adam Coddington
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import logging
from multiprocessing import Process, Queue
import socket
from time import sleep

from connection import TeamspeakConnection
from message import Command
from exceptions import TeamspeakConnectionLost, TeamspeakConnectionFailed, \
        TeamspeakConnectionTelnetEOF

__all__ = ['Client']


class Client(object):
    def __init__(self, hostname='127.0.0.1', port=25639, timeout=0.25):
        self.pipe_out = Queue()
        self.pipe_in = Queue()
        self.timeout = timeout

        self.logger = logging.getLogger('teamspeak3.Client')

        self.proc = Process(
                target=self.__class__.start_connection,
                args=(hostname, port, timeout, self.pipe_in, self.pipe_out)
            )
        self.proc._daemonic = True
        self.proc.start()
        self.logger.debug("Spawned subprocess %s" % self.proc.pid)

        self._verify_initial_connection()

    def _verify_initial_connection(self):
        command = Command(
                'whoami',
            )
        self.send_command(command)
        attempts = 25
        for attempt in range(attempts):
            message = self.get_message()
            if message and message.is_response_to(command):
                return True
            sleep(self.timeout)
        self.close()
        raise TeamspeakConnectionFailed()

    def __enter__(self, *args, **kwargs):
        return Client(*args, **kwargs)

    def __exit__(self, type, value, traceback):
        self.proc.terminate()
        return True

    def close(self):
        self.logger.debug("Terminating subprocess %s" % self.proc.pid)
        self.proc.terminate()

    @classmethod
    def start_connection(cls, hostname, port, timeout, pipe_in, pipe_out):
        # Connect the out to the in, and the in to the out.
        try:
            conn = TeamspeakConnection(
                        hostname,
                        port,
                        timeout,
                        pipe_out,
                        pipe_in
                    )
            conn.main_loop()
        except socket.error:
            pipe_in.put('TERM')

    def get_messages(self):
        messages = []
        while True:
            message = self.get_message()
            if not message:
                return messages
            messages.append(message)

    def get_message(self):
        try:
            if not self.pipe_in.empty():
                msg = self.pipe_in.get_nowait()
                if isinstance(msg, Exception):
                    raise msg
                elif msg == 'TERM':
                    self.close()
                else:
                    return msg
        except EOFError:
            self.close()
            raise TeamspeakConnectionTelnetEOF()
        if not self.proc.is_alive():
            self.logger.debug("Subprocess %s terminated" % self.proc.pid)
            raise TeamspeakConnectionLost()
        return None

    def subscribe(self, type='any'):
        """
        Shortcut method to subscribe to all messages received from the client.
        """
        return self.send_command(
                    Command(
                            'clientnotifyregister',
                            schandlerid=0,
                            event=type
                        )
                )

    def send_command(self, command):
        if not self.proc.is_alive():
            raise TeamspeakConnectionLost()
        self.pipe_out.put(command)
