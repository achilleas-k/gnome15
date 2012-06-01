# Copyright (c) 2012 Adam Coddington #
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
from collections import deque
import logging
from telnetlib import Telnet
from time import time, sleep

from message import Command, MessageFactory


class TeamspeakConnection(Telnet):
    def __init__(self, hostname, port, timeout, pipe_in, pipe_out, keep_alive=30, poll_interval=0.125):
        self.pipe_in = pipe_in
        self.pipe_out = pipe_out

        self.logger = logging.getLogger('teamspeak3.TeamspeakConnection')

        self.commands_unresponded = deque()

        self.keep_alive = keep_alive
        self.poll_interval = poll_interval
        Telnet.__init__(self, hostname, port, timeout)

    def write_command(self, command):
        self.logger.info("Sending command %s" % command.__repr__())
        self.commands_unresponded.append(command)
        self.write("%s\n" % command.output)

    def write_keep_alive(self):
        self.logger.debug("Sending keepalive message.")
        self.write("\n")

    def main_loop(self):
        while True:
            incoming = self.receive_message()
            if incoming:
                self.pipe_out.put(incoming)
            else:
                # Only write messages if we have nothing incoming
                if not self.pipe_in.empty():
                    comm = self.pipe_in.get_nowait()
                    if isinstance(comm, Command):
                        self.write_command(comm)
                elif int(time()) % self.keep_alive == 0:
                    self.write_keep_alive()
            sleep(self.poll_interval)

    def receive_message(self):
        try:
            incoming_message = self.read_until('\n', self.timeout).strip()
            if incoming_message.strip():
                self.logger.debug("Incoming string \"%s\"" % incoming_message)
                message = MessageFactory.get_message(incoming_message)
                if message:
                    if message.is_response():
                        message.set_origination(
                                    self.commands_unresponded.popleft()
                                )
                    elif message.is_reset_message():
                        # Command didn't ask for a response
                        if self.commands_unresponded:
                            self.commands_unresponded.popleft()
                    self.logger.info("Received message %s" % message.__repr__())
                    return message
        except ValueError as e:
            pass
        except IndexError as e:
            self.logger.warning(
                    "Unable to create message for \"%s\"; %s" % (
                        incoming_message, 
                        e
                    )
                )
        except Exception as e:
            return e
