"""
    twitch_follow_server.py: A server to receive Twitch follow notifications
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

import json
import threading
import traceback
import time

from flask import Flask
from flask import jsonify
from flask import make_response
from flask import request

import wsgiserver
import requests

import microsecond_logging
from twitch_channel_interface import TwitchChannelInterface
from configuration import add_configuration


class TwitchFollowServer(object):
    def __init__(self, logger, chatbot=None):
        self.app = Flask(__name__, static_url_path="")
        add_configuration(self)
        self.logger = logger
        self.chatbot = chatbot
        self.add_url_rules()
        self.server_thread = None
        self.dispatcher = None
        self.server = None

    def bad_request(self, error):
        return make_response(jsonify({'error': 'Bad request'}), 400)

    def unauthorized(self):
        return make_response(jsonify({'error': 'Unauthorized access'}), 401)

    def not_found(self, error):
        return make_response(jsonify({'error': 'Not found'}), 404)

    def internal_server_error(self, error):
        return make_response(jsonify({'error': 'Internal server error'}), 500)

    def add_url_rules(self):
        self.app.add_url_rule('/api/v1.0/new_follower',
                              'new_follower',
                              self.new_follower,
                              methods=['GET', 'POST'])
        self.app.add_url_rule('/auth/twitch/callback',
                              'oauth_handler',
                              self.oauth_handler,
                              methods=['GET', 'POST'])
        self.app.register_error_handler(400, self.bad_request)
        self.app.register_error_handler(404, self.not_found)
        self.app.register_error_handler(500, self.internal_server_error)

    def oauth_handler(self):
        self.logger.debug(f"Handling a request: {request}")
        result = make_response(jsonify({'success': 'OAuth response'}), 202)
        return result

    def new_follower(self):
        self.logger.debug(f"Handling a request: {request}")
        result = make_response(jsonify({'error': 'Bad request'}), 400)
        if request.method == 'GET':
            self.logger.debug("Twitch responded to our subscription request")
            if 'hub.challenge' in request.args:
                self.logger.debug("Sending the challenge response to Twitch")
                result = make_response(request.args['hub.challenge'])
        elif request.method == 'POST':
            self.logger.debug("We received a follower notification from Twitch")
            if hasattr(request, 'data'):
                data = json.loads(request.data)
                data = data['data'][0]
                follow = f"{data['from_name']} is now following {data['to_name']}"
                self.logger.debug(follow)
                if self.chatbot is not None:
                    self.chatbot.new_follower = follow
            result = make_response(jsonify({'success': 'Follower notification'}), 202)
        return result

    def server_function(self):
        self.dispatcher = wsgiserver.WSGIPathInfoDispatcher({'/': self.app})
        self.server = wsgiserver.WSGIServer(self.dispatcher, host=self.host, port=self.port)
        try:
            self.server.start()
        except KeyboardInterrupt:
            self.logger("Stopping server due to keyboard interrupt")
            self.server.stop()

    def start(self):
        try:
            self.server_thread = threading.Thread(target=self.server_function)
            self.server_thread.daemon = True
            self.server_thread.start()
        except:
            self.logger.error(traceback.format_exc())
            return False
        return True

    def stop(self):
        self.server.stop()
        self.server_thread.join()


class TwitchWebhookInterface(object):
    def __init__(self, logger, follow_server):
        self.logger = logger
        self.follow_server = follow_server
        add_configuration(self)
        self.webhooks_url = f"{self.twitch_api_base}/webhooks/hub"
        self.interface = TwitchChannelInterface(self.channel, self.client_id)
        self.user_id = self.interface.get_id()
        self.data = None
        self.access_token = None

    def get_access_token(self):
        api_url = "https://id.twitch.tv/oauth2/token"
        self.logger.debug(f"api_url = {api_url}")
        payload = {
            "client_id": self.client_id,
            "client_secret": "0mhdlly4cxfnhxcbrn4q8ojyangzze",
            "grant_type": "client_credentials",
        }
        self.logger.debug(f"payload = {payload}")
        result = requests.post(api_url, data=payload)
        if result.status_code == requests.codes.ok:
            self.data = result.json()
            self.access_token = self.data['access_token']
        return self.access_token

    def subscribe(self):
        headers = {"Client-ID": self.client_id, "Authorization": f"Bearer {self.interface.access_token}"}
        data = {
            "hub.mode": "subscribe",
            "hub.topic": f"{self.twitch_api_base}/users/follows?first=1&to_id={self.user_id}",
            "hub.callback": self.public_uri,
            "hub.lease_seconds": str(24 * 60 * 60)
        }
        result = requests.post(self.webhooks_url, json=data, headers=headers)
        if result.status_code == requests.codes.accepted:
            self.logger.debug("Our subscription request was accepted by Twitch")
        else:
            self.logger.debug("Failed to subscribe to follower notifications")
            self.logger.debug(f"result.status_code = {result.status_code}")
            self.logger.debug(f"result.text = {result.text}")


def start_server_and_subscribe(logger=None, chatbot=None):
    if logger is None:
        logger = microsecond_logging.getLogger(__name__)
        logger.setLevel(microsecond_logging.DEBUG)
    logger.debug("Starting server...")
    twitch_follow_server = TwitchFollowServer(logger, chatbot)
    twitch_follow_server.start()
    logger.debug("Sleeping to allow server to start...")
    time.sleep(1.0)
    logger.debug("Subscribing to follower notifications...")
    twitch_webhook_interface = TwitchWebhookInterface(logger, twitch_follow_server)
    twitch_webhook_interface.subscribe()
    return twitch_follow_server


def main():
    logger = microsecond_logging.getLogger(__name__)
    logger.setLevel(microsecond_logging.DEBUG)
    logger.debug("Initializing...")
    start_server_and_subscribe(logger)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.debug("Keyboard interrupt")
    logger.debug("Done.")


if __name__ == '__main__':
    main()
