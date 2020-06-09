"""
    twitch_channel_interface.py: A class to interface with the Twitch API
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

import requests

from configuration import add_configuration
import microsecond_logging


def new_followers(previous_followers, current_followers):
    result = list()
    if previous_followers:
        for follower in current_followers:
            if follower not in previous_followers:
                result.append(follower)
    return result


class TwitchChannelInterface(object):
    def __init__(self, channel, client_id):
        self.logger = microsecond_logging.getLogger(__name__)
        self.logger.setLevel(microsecond_logging.DEBUG)
        self.channel = channel
        self.client_id = client_id
        add_configuration(self)
        self.data = None
        self.channel_id = None
        self.follows = None
        self.new_follows = None
        self.access_token = None

    def get_access_token(self):
        api_url = "https://id.twitch.tv/oauth2/token"
        self.logger.debug(f"api_url = {api_url}")
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        self.logger.debug(f"payload = {payload}")
        result = requests.post(api_url, data=payload)
        if result.status_code == requests.codes.ok:
            self.data = result.json()
            self.access_token = self.data['access_token']
        return self.access_token

    def get_id(self):
        api_url = f"{self.twitch_api_base}/users"
        self.logger.debug(f"api_url = {api_url}")
        access_token = self.get_access_token()
        headers = {"Client-ID": self.client_id, "Authorization": f"Bearer {access_token}"}
        self.logger.debug(f"headers = {headers}")
        payload = {"login": self.channel}
        result = requests.get(api_url, params=payload, headers=headers)
        if result.status_code == requests.codes.ok:
            self.data = result.json()
            self.channel_id = self.data['data'][0]['id']
            self.logger.debug(f"self.channel_id = {self.channel_id}")
        return self.channel_id

    def get_follows(self):
        api_url = f"{self.twitch_api_base}/users/follows"
        headers = {"Client-ID": self.client_id}
        payload = {"to_id": f"{self.channel_id}"}
        result = requests.get(api_url, params=payload, headers=headers)
        if result.status_code == requests.codes.ok:
            self.data = result.json()
            previous_follows = self.follows
            self.follows = self.data['data']
            self.new_follows = new_followers(previous_follows, self.follows)
        return self.new_follows
