"""
    twitch_bot.py: A Twitch Chat Bot with Text-to-Speech
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

import pyttsx3

from twitch_chat_bot import TwitchChatBot
from twitch_follow_server import start_server_and_subscribe
import microsecond_logging


class TwitchChatBotTTS(TwitchChatBot):

    command_help_dict = {
        "speech": "Enable text to speech",
        "silence": "Disable text to speech",
        "loud": "Set volume to loud",
        "quiet": "Set volume to quiet",
        "whisper": "Set volume to whisper"
    }

    def __init__(self, logger):
        self.logger = logger
        super().__init__(logger)
        self.enable_speech = True
        self.engine = pyttsx3.init()
        self.init_speech()

    def init_speech(self):
        if hasattr(self, 'voice_index'):
            voices = self.engine.getProperty('voices')
            self.engine.setProperty('voice', voices[self.voice_index].id)

    def set_speech_volume(self, volume):
        self.engine.setProperty('volume', float(volume))

    def say(self, message):
        if self.enable_speech:
            self.engine.say(message)
            self.engine.runAndWait()

    async def handle_new_follower_post(self):
        if self.new_follower is not None:
            self.say(self.new_follower)

    async def handle_privmsg_post(self, privmsg):
        self.say(f"{privmsg.nick} said {privmsg.message}")
        self.logger.debug(f"Received \"{privmsg.message}\" from {privmsg.nick}")

    async def handle_command(self, nick, command):
        nick = nick.lower()
        if (nick == 'mountainriderak') or (nick == 'mountainriderbot'):
            await self.handle_speech_command(command)

    async def handle_speech_command(self, command):
        if command == 'speech':
            self.enable_speech = True
            self.say('enabling text to speech')
        elif command == 'silence':
            self.say('disabling text to speech')
            self.enable_speech = False
        elif command == 'loud':
            self.say('setting volume to loud')
            self.set_speech_volume('1.0')
        elif command == 'quiet':
            self.say('setting volume to quiet')
            self.set_speech_volume('0.5')
        elif command == 'whisper':
            self.say('setting volume to whisper')
            self.set_speech_volume('0.2')


def main():
    twitch_follow_server = None
    try:
        logger = microsecond_logging.getLogger(__name__)
        logger.setLevel(microsecond_logging.DEBUG)
        twitch_chat_bot = TwitchChatBotTTS(logger)
        twitch_follow_server = start_server_and_subscribe(chatbot=twitch_chat_bot)
        twitch_chat_bot.run()
    except KeyboardInterrupt:
        if twitch_follow_server is not None:
            twitch_follow_server.stop()


if __name__ == '__main__':
    main()
