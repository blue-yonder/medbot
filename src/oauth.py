# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

import sys
import requests
import urllib.parse

try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser

__author__ = 'Florian Wilhelm'
__copyright__ = 'Blue Yonder'
__license__ = 'new BSD'


OAUTH2_SCOPES = {
    'oauthlogin': 'https://www.google.com/accounts/OAuthLogin',
    'googletalk': 'https://www.googleapis.com/auth/googletalk'
}


class OAuthError(Exception):
    """Raised Exception when authentication fails."""


class OAuth(object):
    def __init__(self, client_id=None, client_secret=None, refresh_token=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.url = 'https://www.googleapis.com/oauth2/v3/token'

    def from_cfg(self, filename):
        parser = SafeConfigParser()
        with open(filename) as fh:
            parser.readfp(fh)
        self.client_id = parser.get('credentials', 'client_id')
        self.client_secret = parser.get('credentials', 'client_secret')
        if parser.has_option('credentials', 'refresh_token'):
            token = parser.get('credentials', 'refresh_token').strip()
            if token:
                self.refresh_token = token

    @property
    def access_token(self):
        params = dict(refresh_token=self.refresh_token,
                      client_id=self.client_id,
                      client_secret=self.client_secret,
                      grant_type='refresh_token')
        resp = requests.post(self.url, data=params)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def get_authorize_scope_url(self, scope):
        url = 'https://accounts.google.com/o/oauth2/auth?{}'.format(
            urllib.parse.urlencode(dict(
                client_id=self.client_id,
                scope=scope,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob',
                response_type='code',
            )))
        return url

    def update_refresh_token(self, auth_code):
        token_request_data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        }
        res = requests.post(self.url, data=token_request_data).json()
        print(res)
        if 'error' in res:
            raise OAuthError('Authorization error: \'{}\''.format(
                res['error']))

        self.refresh_token = res['refresh_token']
        return self.refresh_token


if __name__ == "__main__":
    auth = OAuth()
    auth.from_cfg('oauth.cfg')
    if auth.refresh_token is None:
        url = auth.get_authorize_scope_url(OAUTH2_SCOPES['googletalk'])
        print("Open this website:\n"
              "{}\n"
              "Accept and post the code here:".format(url))
        auth_code = sys.stdin.readline()
        token = auth.update_refresh_token(auth_code)
        print("Your token is:\n{}\nSave it in oauth.cfg".format(token))
