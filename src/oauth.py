# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

import requests
from ConfigParser import SafeConfigParser

__author__ = 'Florian Wilhelm'
__copyright__ = 'Blue Yonder'
__license__ = 'new BSD'


class OAuth(object):
    def __init__(self, client_id=None, client_secret=None, refresh_token=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.url = 'https://www.googleapis.com/oauth2/v3/token'

    def from_cfg(self, filename):
        parser = SafeConfigParser()
        parser.readfp(filename=filename)
        self.client_id = parser.get('credentials', 'client_id')
        self.client_secret = parser.get('credentials', 'client_secret')
        self.refresh_token = parser.get('credentials', 'refresh_token')

    @property
    def access_token(self):
        params = dict(refresh_token=self.refresh_token,
                      client_id=self.client_id,
                      client_secret=self.client_secret,
                      grant_type='refresh_token')
        resp = requests.post(self.url, data=params)
        resp.raise_for_status()
        return resp.json()["access_token"]
