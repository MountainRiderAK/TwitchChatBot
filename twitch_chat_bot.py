"""
    twitch_bot.py: A Twitch Chat Bot
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

import asyncio
import websockets

from configuration import add_configuration
from twitch_follow_server import start_server_and_subscribe
from twitch_privmsg import is_privmsg
from twitch_privmsg import TwitchPrivmsg
import microsecond_logging


class TwitchChatBot(object):
    twitch_chat_websocket_uri = "wss://irc-ws.chat.twitch.tv:443"

    def __init__(self, logger):
        add_configuration(self)
        self.logger = logger
        self.loop = asyncio.get_event_loop()
        self.websocket = None
        self.new_follower = None
        self.send_caps = False
        self.cap_list = ['commands', 'tags', 'membership']
        self.receive_buffer = ''
        self.backoff_interval = 2
        self.backoff_counter = 1
        self.success_counter = 0
        self.bot_message = "Hello! Welcome to the channel!"
        self.bot_message_interval = 5 * 60
        self.bot_message_counter = 0

    async def send_data(self, data):
        await self.websocket.send(f"{data}\r\n")

    async def send_cap(self, cap):
        await self.send_data(f"CAP REQ :twitch.tv/{cap}")

    async def send_privmsg(self, message):
        channel = self.channel.lower()
        await self.send_data(f"PRIVMSG #{channel} :{message}")

    async def connect(self):
        self.websocket = await websockets.connect(self.twitch_chat_websocket_uri)
        await self.send_data(f"PASS {self.tmi_token}")
        await self.send_data(f"NICK {self.bot_nick}")
        if self.send_caps:
            for cap in self.cap_list:
                await self.send_cap(cap)
        channel = self.channel.lower()
        await self.send_data(f"JOIN #{channel}")
        # Read from the websocket until there is no more data
        result = ''
        while True:
            try:
                result = result + await asyncio.wait_for(self.websocket.recv(), 1.0)
            except asyncio.TimeoutError:
                break
        # Convert the data to a list of lines and print each line
        line_list = result.split('\n')
        for line in line_list:
            self.logger.debug(line)

    async def listen(self):
        try:
            self.receive_buffer = self.receive_buffer + await asyncio.wait_for(self.websocket.recv(), 1.0)
            if self.receive_buffer.endswith('\n'):
                self.receive_buffer = self.receive_buffer.rstrip()
                self.logger.debug(self.receive_buffer)
                await self.handle_ping(self.receive_buffer)
                await self.handle_privmsg(self.receive_buffer)
                self.receive_buffer = ''
        except asyncio.TimeoutError:
            pass

    async def handle_ping(self, message):
        if message.startswith('PING'):
            reply = 'PONG ' + message.split(' ', 1)[1]
            self.logger.debug(f"Sending {reply}")
            await self.send_data(reply)

    async def handle_new_follower_post(self):
        pass

    async def handle_new_follower(self):
        if self.new_follower is not None:
            await self.send_privmsg(self.new_follower)
            await self.handle_new_follower_post()
            self.new_follower = None

    async def handle_privmsg_post(self, privmsg):
        pass

    async def handle_privmsg(self, message):
        if is_privmsg(message):
            privmsg = TwitchPrivmsg(message)
            if privmsg.message.startswith('!'):
                await self.handle_command(privmsg.nick, privmsg.message[1:])
            else:
                await self.handle_privmsg_post(privmsg)
                self.logger.debug(f"Received \"{privmsg.message}\" from {privmsg.nick}")

    async def handle_command(self, nick, command):
        pass

    async def send_periodic_message(self):
        await asyncio.sleep(1.0)
        self.bot_message_counter += 1
        self.logger.debug(f"self.bot_message_counter = {self.bot_message_counter}")
        if self.bot_message_counter >= self.bot_message_interval:
            self.bot_message_counter = 0
            await self.send_privmsg(self.bot_message)

    async def run_tasks(self):
        await self.connect()
        while True:
            try:
                task_list = list()
                task_list.append(asyncio.create_task(self.listen()))
                task_list.append(asyncio.create_task(self.handle_new_follower()))
                task_list.append(asyncio.create_task(self.send_periodic_message()))
                await asyncio.gather(*task_list)
                self.success_counter += 1
                if self.success_counter > self.backoff_counter:
                    self.success_counter = 1
                    self.backoff_counter = 1
            except websockets.ConnectionClosed:
                self.logger.error("Connection was closed. Reconnecting...")
                self.backoff_interval = self.backoff_interval ** self.backoff_counter
                self.backoff_counter += 1
                await asyncio.sleep(self.backoff_interval)
                await self.connect()

    def run(self):
        asyncio.run(self.run_tasks())


def main():
    twitch_follow_server = None
    try:
        logger = microsecond_logging.getLogger(__name__)
        logger.setLevel(microsecond_logging.DEBUG)
        twitch_chat_bot = TwitchChatBot(logger)
        twitch_follow_server = start_server_and_subscribe(chatbot=twitch_chat_bot)
        twitch_chat_bot.run()
    except KeyboardInterrupt:
        if twitch_follow_server is not None:
            twitch_follow_server.stop()


if __name__ == '__main__':
    main()
