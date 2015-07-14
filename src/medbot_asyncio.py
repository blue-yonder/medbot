#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    A chat bot based on asyncio and hangups
"""

import sys
import logging
from datetime import datetime, timedelta

import asyncio
import hangups
from hangups.auth import get_auth_stdin

__author__ = 'Florian Wilhelm'
__copyright__ = 'Blue Yonder'
__license__ = 'new BSD'

_logger = logging.getLogger(__name__)


class MedBot(object):
    def __init__(self, client, recipient):
        self._client = client
        self._recipient = recipient
        self._user_list = None
        self._conv_list = None
        self._asked = False
        self._pos_reply = False

    def run(self):
        self._client.on_connect.add_observer(self._on_connect)
        self._client.on_disconnect.add_observer(self._on_disconnect)
        loop = asyncio.get_event_loop()
        # Set alarm
        wait_time = self._get_secs_to_next_alarm()
        loop.call_later(wait_time, self.set_alarm)
        loop.run_until_complete(self._client.connect())

    @property
    def _recipient_id(self):
        users = [u for u in self._user_list.get_all()
                 if self._recipient.lower() == u.full_name.lower()]
        assert len(users) == 1
        return users[0].id_

    def _get_conv_with_recipient(self):
        for conv in self._conv_list.get_all():
            user_ids = [u.id_ for u in conv.users]
            if len(user_ids) != 2:
                continue
            elif self._recipient_id in user_ids:
                return conv
        raise RuntimeError("No conversation with user id {} found".format(
            self._recipient_id
        ))
        assert len(convs) == 1
        return convs[0]

    @asyncio.coroutine
    def _on_connect(self, initial_data):
        self._user_list = yield from hangups.build_user_list(
            self._client, initial_data)

        self._conv_list = hangups.ConversationList(
            self._client,
            initial_data.conversation_states,
            self._user_list,
            initial_data.sync_timestamp
        )
        self._conv_list.on_event.add_observer(self._on_event)

    @asyncio.coroutine
    def _on_disconnect(self):
        _logger.info("Disconnected")

    @asyncio.coroutine
    def _on_event(self, conv_event):
        _logger.info("Event received...")
        conv = self._conv_list.get(conv_event.conversation_id)
        user = conv.get_user(conv_event.user_id)
        if isinstance(conv_event, hangups.ChatMessageEvent):
            text = conv_event.text.strip()
        else:
            text = ''
        from_recipient = self._recipient_id == user.id_
        is_positive = text.lower().startswith('yes')
        if from_recipient and is_positive and self._asked:
            _logger.info("Positive reply received")
            self._pos_reply = True
            self._asked = False
            yield from self._send_message(conv, "That's great!")

    @asyncio.coroutine
    def _send_message(self, conversation, text):
        segments = hangups.ChatMessageSegment.from_str(text)
        yield from conversation.send_message(segments)

    def _get_secs_to_next_alarm(self):
        now = datetime.now()
        alarm = datetime(now.year, now.month, now.day, 20, 0, 0)
        if (alarm - now - timedelta(seconds=15)).days < 0:
            alarm += timedelta(days=1)
        return (alarm - now).total_seconds()

    @asyncio.coroutine
    def send_alarm(self):
        _logger.info('Sending reminder...')
        msg = 'Hey buddy, did you take your insulin?'
        self._pos_reply = False
        conv = self._get_conv_with_recipient()
        yield from self._send_message(conv, msg)
        self._asked = True
        repeat_timeout = 60*20
        yield from asyncio.sleep(repeat_timeout)
        for _ in range(3):
            if self._pos_reply: break
            yield from self._send_message(conv, 'How about now?')
            yield from asyncio.sleep(repeat_timeout)
        else:
            if not self._pos_reply:
                yield from self._send_message(conv, "I'm giving up!")
        wait_time = self._get_secs_to_next_alarm()
        loop = asyncio.get_event_loop()
        loop.call_later(wait_time, self.set_alarm)
        self._asked = False

    def set_alarm(self):
        _logger.info("Set alarm...")
        asyncio.async(self.send_alarm())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s',
                        stream=sys.stdout)

    cookies = get_auth_stdin('my_refresh_token.txt')
    client = hangups.Client(cookies)
    bot = MedBot(client, "Florian Wilhelm")
    _logger.info("Starting bot...")
    bot.run()
