# coding: utf-8

import os
from google.appengine.api import app_identity

from collections import namedtuple

GoogleOAuth2ConfigDB = namedtuple('GoogleOAuth2ConfigDB', ['google_client_id', 'google_client_secret'])

GoogleOAuth2 = GoogleOAuth2ConfigDB(
    'id',
    'pass',
)

APPLICATION_ID = app_identity.get_application_id()

PRODUCTION = os.environ.get('SERVER_SOFTWARE', '').startswith('Google App Eng')
DEBUG = DEVELOPMENT = not PRODUCTION

SECRET_KEY = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
