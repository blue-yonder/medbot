#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    A chat bot based on SleekXMPP

    Scope parameter is https://www.googleapis.com/auth/googletalk
    Best is the generate the request with the OauthPlayground:
    https://developers.google.com/oauthplayground/
"""

from __future__ import absolute_import, division, print_function

import sys
import logging
import random
from datetime import datetime, timedelta
from time import sleep

from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
from oauth import OAuth


__author__ = 'Florian Wilhelm'
__copyright__ = 'Blue Yonder'
__license__ = 'new BSD'

_logger = logging.getLogger(__name__)

if sys.version_info < (3, 0):
    from sleekxmpp.util.misc_ops import setdefaultencoding
    setdefaultencoding('utf8')
else:
    raw_input = input


class ChatClient(ClientXMPP):
    def __init__(self, jid, oauth):
        ClientXMPP.__init__(self, jid, password=None)
        self.oauth = oauth
        self.msg_callback = None
        self.add_event_handler("session_start", self.session_started, threaded=True)
        self.add_event_handler("message", self.message_received)

        # Plugins
        self.register_plugin('xep_0030')  # Service Discovery
        #self.register_plugin('xep_0199', {'keepalive': True, 'frequency': 60})  # XMPP Ping
        #self.register_plugin('xep_0235')
        #self.register_plugin('google')
        #self.register_plugin('google_auth')

    def add_msg_callback(self, func):
        self.msg_callback = func

    def get_recipient_id(self, recipient):
        for k in self.client_roster.keys():
            if self.client_roster[k]['name'] == recipient:
                recipient_id = k
                break
        else:
            recipient_id = None
        return recipient_id

    def connect(self, *args, **kwargs):
        _logger.info("Connecting...")
        self.credentials['access_token'] = self.oauth.access_token
        return super(ChatClient, self).connect(*args, **kwargs)

    def reconnect(self, *args, **kwargs):
        _logger.info("Reconnecting")
        self.credentials['access_token'] = self.oauth.access_token
        return super(ChatClient, self).reconnect(*args, **kwargs)

    def session_started(self, event):
        self.send_presence()
        try:
            self.get_roster()
        except IqError as err:
            logging.error('There was an error getting the roster')
            logging.error(err.iq['error']['condition'])
            self.disconnect()
        except IqTimeout:
            logging.error('Server is taking too long to respond')
            self.disconnect()

    def send_msg(self, recipient, msg):
        recipient_id = self.get_recipient_id(recipient)
        self.send_message(mto=recipient_id, mbody=msg, mtype='chat')

    def message_received(self, msg):
        _logger.info("Got message from {}".format(msg['from']))
        if self.msg_callback is None:
            _logger.warn("No callback for message received registered")
        else:
            self.msg_callback(msg)


class State(object):
    not_asked = 0
    asked = 1


class MedBot(object):
    alarm = ['Have you taken your long-acting insulin analogue?',
             'Hey buddy, got your insulin?',
             'Have you taken your daily dose of insulin?']
    reminder = ['how about now?',
                'and now?',
                '... maybe now?']
    praise = ['Great!', 'Good for you!', 'Well done']
    give_up = ["Okay, I'am giving up!", "It can't be helped!"]

    def __init__(self, chat_client, recipient, max_retries=5):
        self.chat_client = chat_client
        self.chat_client.add_msg_callback(self.handle_message)
        self.recipient = recipient
        self.positive_reply = False
        self.curr_state = State.not_asked
        self.max_retries = max_retries
        self.retries = 0
        self.retry_sleep = 1200

    def send_alarm(self):
        _logger.info("Alarm triggered")
        self.positive_reply = False
        self.curr_state = State.asked
        self.retries = 0
        self.chat_client.send_msg(self.recipient,
                                  random.choice(self.alarm))
        while not self.positive_reply:
            sleep(self.retry_sleep)
            if not self.ask_again():
                self.curr_state = State.not_asked
                break

    def ask_again(self):
        _logger.info("Asking again?")
        if not self.positive_reply:
            if self.retries < self.max_retries:
                self.retries += 1
                msg = random.choice(self.reminder)
                answer = True
            else:
                msg = random.choice(self.give_up)
                answer = False
            self.chat_client.send_msg(self.recipient, msg)
            return answer

    def handle_message(self, msg):
        recipient_id = self.chat_client.get_recipient_id(self.recipient)
        from_recipient = msg['from'].full.startswith(recipient_id)
        is_positive = msg['body'].lower().startswith('yes')
        was_asked = self.curr_state == State.asked
        if from_recipient and is_positive and was_asked:
            _logger.info("Positive reply received")
            self.positive_reply = True
            self.curr_state = State.not_asked
            self.chat_client.send_msg(self.recipient,
                                      random.choice(self.praise))

    def _get_secs_to(self, timestamp):
        delta = timestamp - datetime.now()
        return delta.total_seconds()

    def _get_next_alarm(self):
        today = datetime.now()
        today_alarm = datetime(today.year, today.month, today.day, 18, 40, 0)
        if (today_alarm - today - timedelta(seconds=15)).days >= 0:
            return today_alarm
        else:
            return today_alarm + timedelta(days=1)

    def run(self):
        if self.chat_client.connect():
            self.chat_client.process(block=False)
            while True:
                sleep(self._get_secs_to(self._get_next_alarm()))
                self.send_alarm()
        else:
            raise RuntimeError("Unable to connect!")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s',
                        stream=sys.stdout)
    oauth = OAuth()
    oauth.read_cfg('oauth.cfg')
    jid = 'your_email@gmail.com'
    chat_client = ChatClient(jid, oauth)
    medbot = MedBot(chat_client, 'Buddy')
    medbot.run()
