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
__all__ = ['Message', 'Command']

class MessageFactory(object):
    @classmethod
    def get_message(cls, incoming_string):
        if incoming_string[0] != incoming_string[0].upper():
            first_item = incoming_string.split(' ')[0]
            if "=" in first_item and "|" in incoming_string:
                return MultipartMessage(incoming_string)
            else:
                return Message(incoming_string)

class MessageBase(object):
    MAPPINGS = {
            '\\\\': '\\',
            '\\/': '/',
            '\\s': ' ',
            '\\p': '|',
            '\\a': '',
            '\\b': '',
            '\\f': '\n',
            '\\n': '\n',
            '\\r': '\n',
            '\\t': '\t',
            '\\v': '',
            }

    def __eq__(self, other):
        if self.__repr__() == other.__repr__():
            return True
        return False

    def __unicode__(self):
        return unicode(self.__str__())

    def __repr__(self):
        return "<%s>" % self.__str__()

    def _clean_incoming_value_multipart(self, value):
        raw_values = value.split('|')

        items = []
        items.append(
                raw_values[0]
            )
        for raw_item in raw_values[1:]:
            items.append(
                    raw_item.split('=')[1]
                )
        return tuple(items)

    def _clean_incoming_value(self, value):
        for fr, to in self.MAPPINGS.items():
            value = value.replace(fr, to)
        return value

    def _clean_outgoing_value(self, value):
        value = str(value)
        for fr, to in self.MAPPINGS.items():
            if to:
                value = value.replace(to, fr)
        return value

    @property
    def ultimate_origination(self):
        if self.is_response():
            return self.origination.command
        else:
            return self.command

class Message(MessageBase):
    def __init__(self, command):
        command = command.strip()
        if not command:
            raise ValueError("No command")

        self.raw_command = command

        self.command = self._get_command_from_string(self.raw_command)
        self.args = self._get_arguments_from_string(self.raw_command)

    def is_reset_message(self):
        if self.command == 'error':
            return True
        return False

    def is_response(self):
        if self.command:
            return False
        return True

    def is_response_to(self, command):
        if self.is_response() and self.origination == command:
            return True
        return False

    def set_origination(self, command):
        self.origination = command

    def _get_command_from_string(self, cmd):
        command = cmd.split(' ')[0]
        if command.find('=') > -1:
            command = None
        return command

    def _get_arguments_from_string(self, cmd):
        args = {}
        raw_args = cmd.split(' ')[1 if self.command else 0:]
        for raw_arg in raw_args:
            arg = raw_arg.split('=', 1)
            attribute = arg[0]
            if len(arg) > 1:
                value = arg[1]
            else:
                value = None
            if value:
                if "|" in value:
                    args[attribute] = self._clean_incoming_value_multipart(value)
                else:
                    args[attribute] = self._clean_incoming_value(value)
            else:
                args[attribute] = None
        return args

    def __getitem__(self, key):
        return self.args[key]

    def keys(self):
        return self.args.keys()

    @property
    def output(self):
        arglist = []
        for param, value in self.args.items():
            arglist.append("%s=%s" % (
                    param,
                    self._clean_outgoing_value(value),
                ))
        if self.is_response():
            return "%s %s" % (
                        self.origination.__repr__(),
                        " ".join(arglist),
                    )
        else:
            return "%s %s" % (
                        self.command,
                        " ".join(arglist),
                    )

    def __str__(self):
        if self.is_response():
            return "%s %s" % (
                        self.origination.__repr__(),
                        self.args
                    )
        else:
            return "%s %s" % (
                        self.command,
                        self.args
                    )

class MultipartMessage(MessageBase):
    def __init__(self, command_string):
        self.command = command_string
        self.origination = None

        self.responses = self.parse_command(
                    self.command
                )

    def parse_command(self, string):
        responses = []
        for string_part in string.split('|'):
            responses.append(
                        Message(
                            string_part
                            )
                    )
        return responses

    def set_origination(self, command):
        self.origination = command
        for response in self.responses:
            response.set_origination(command)

    def __getitem__(self, key):
        return self.responses[key]

    def __str__(self):
        string_list = []
        for response in self.responses:
            string_list.append(repr(response))
        return "[%s]" % (
                ", ".join(string_list)
            )

    def is_response(self):
        return True

    def is_reset_message(self):
        return False

class Command(Message):
    def __init__(self, command, **kwargs):
        self.command = command
        self.args = kwargs
