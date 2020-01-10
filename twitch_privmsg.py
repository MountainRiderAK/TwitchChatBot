"""
    twitch_privmsg.py: Code to identify and parse Twitch chat PRIVMSG
    Copyright (C) 2020  MountainRiderAK

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, version 3 of the
    License.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

def is_privmsg(data):
    result = False
    if 'PRIVMSG' in data:
        result = True
    return result


class TwitchPrivmsg(object):
    def __init__(self, data):
        self.data = data
        self.nick = None
        self.user = None
        self.host = None
        self.channel = None
        self.message = None
        self.valid_message = is_privmsg(data)
        if self.valid_message:
            self.parse_data()

    def parse_data(self):
        data = self.data
        if data[0] == ':':
            data = data[1:]
        source, data = data.split(' PRIVMSG ')
        self.nick, source = source.split('!')
        self.user, self.host = source.split('@')
        self.channel, self.message = data.split(' :', 1)
