# coding: utf-8

# [START app]
import flask

import config
import util


app = flask.Flask(__name__)
app.config.from_object(config)
app.request_class = flask.Request


import auth
import control

from api import helpers

api_v1 = helpers.Api(app, prefix='/api/v1')

import api.v1

if config.DEVELOPMENT:
    from werkzeug import debug

    try:
        app.wsgi_app = debug.DebuggedApplication(
            app.wsgi_app, evalex=True, pin_security=False,
        )
    except TypeError:
        app.wsgi_app = debug.DebuggedApplication(app.wsgi_app, evalex=True)
    app.testing = False
# [END app]
