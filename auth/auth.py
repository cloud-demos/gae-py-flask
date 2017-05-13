# coding: utf-8

from __future__ import absolute_import

import functools
import re

from flask_oauthlib import client as oauth
# from google.appengine.ext import ndb
import flask
import flask_login
import unidecode

import config
import util
from util import ndb, profiles

from main import app

_signals = flask.signals.Namespace()

###############################################################################
# Flask Login
###############################################################################
login_manager = flask_login.LoginManager()


class AnonymousUser(flask_login.AnonymousUserMixin):
    id = 0
    admin = False
    name = 'Anonymous'
    user_db = None

    def key(self):
        return None

    def has_permission(self, permission):
        return False


login_manager.anonymous_user = AnonymousUser


class FlaskUser(AnonymousUser):
    def __init__(self, user_db):
        self.user_db = user_db

        self.permissions = user_db.permissions
        self.id = user_db.id
        self.active = user_db.active
        self.key = user_db.key
        self.name = user_db.name
        self.admin = 'Admin' in user_db.permissions

    def key(self):
        return self.key

    def get_id(self):
        return self.id

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def has_permission(self, permission):
        return permission in self.permissions


@login_manager.user_loader
def load_user(key):
    # user_db = ndb.Key(urlsafe=key).get()
    if key in ndb:
        user_db = ndb[key]
        if user_db:
            return FlaskUser(user_db)
        return None
    return None


login_manager.init_app(app)


def current_user_id():
    return flask_login.current_user.id


def current_user_key():
    return flask_login.current_user.key \
        if flask_login.current_user.key \
        else None


def current_user_db():
    return flask_login.current_user.user_db


def is_logged_in():
    return flask_login.current_user.id != 0


###############################################################################
# Decorators
###############################################################################
def login_required(f):
    decorator_order_guard(f, 'auth.login_required')

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if is_logged_in():
            return f(*args, **kwargs)
        if flask.request.path.startswith('/api/'):
            return flask.abort(401)
        return flask.redirect(flask.url_for('welcome', next=flask.request.url))

    return decorated_function


def admin_required(f):
    decorator_order_guard(f, 'auth.admin_required')

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if is_logged_in() and current_user_db().admin:
            return f(*args, **kwargs)
        if not is_logged_in() and flask.request.path.startswith('/api/'):
            return flask.abort(401)
        if not is_logged_in():
            return flask.redirect(flask.url_for('signin', next=flask.request.url))
        return flask.abort(403)

    return decorated_function


# def cron_required(f):
#     decorator_order_guard(f, 'auth.cron_required')
#
#     @functools.wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'X-Appengine-Cron' in flask.request.headers:
#             return f(*args, **kwargs)
#         if is_logged_in() and current_user_db().admin:
#             return f(*args, **kwargs)
#         if not is_logged_in():
#             return flask.redirect(flask.url_for('signin', next=flask.request.url))
#         return flask.abort(403)
#
#     return decorated_function


permission_registered = _signals.signal('permission-registered')


def permission_required(permission=None, methods=None):
    def permission_decorator(f):
        decorator_order_guard(f, 'auth.permission_required')

        # default to decorated function name as permission
        perm = permission or f.func_name
        meths = [m.upper() for m in methods] if methods else None

        permission_registered.send(f, permission=perm)

        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if meths and flask.request.method.upper() not in meths:
                return f(*args, **kwargs)
            if is_logged_in() and current_user_db().has_permission(perm):
                return f(*args, **kwargs)
            if not is_logged_in():
                if flask.request.path.startswith('/api/'):
                    return flask.abort(401)
                return flask.redirect(flask.url_for('signin', next=flask.request.url))
            return flask.abort(403)

        return decorated_function

    return permission_decorator

###############################################################################
# Sign out stuff
###############################################################################
@app.route('/signout/')
def signout():
    flask_login.logout_user()
    return flask.redirect(util.param('next') or flask.url_for('welcome'))


###############################################################################
# Helpers
###############################################################################
def url_for_signin(service_name, next_url):
    return flask.url_for('signin_%s' % service_name, next=next_url)


def urls_for_oauth(next_url):
    return {
        # 'github_signin_url': url_for_signin('github', next_url),
        'google_signin_url': url_for_signin('google', next_url),
        'gae_signin_url': url_for_signin('gae', next_url),
        'linkedin_signin_url': url_for_signin('linkedin', next_url),
    }


def create_oauth_app(service_config, name):
    upper_name = name.upper()
    app.config[upper_name] = service_config
    service_oauth = oauth.OAuth()
    service_app = service_oauth.remote_app(name, app_key=upper_name)
    service_oauth.init_app(app)
    return service_app


def decorator_order_guard(f, decorator_name):
    if f in app.view_functions.values():
        raise SyntaxError(
            'Do not use %s above app.route decorators as it would not be checked. '
            'Instead move the line below the app.route lines.' % decorator_name
        )


def save_request_params():
    flask.session['auth-params'] = {
        'next': util.get_next_url(),
        'remember': util.param('remember'),
    }


def signin_oauth(oauth_app, scheme=None):
    try:
        flask.session.pop('oauth_token', None)
        save_request_params()
        return oauth_app.authorize(callback=flask.url_for(
            '%s_authorized' % oauth_app.name, _external=True, _scheme=scheme
        ))
    except oauth.OAuthException:
        flask.flash(
            'Something went wrong with sign in. Please try again.',
            category='danger',
        )
        return flask.redirect(flask.url_for('welcome', next=util.get_next_url()))
