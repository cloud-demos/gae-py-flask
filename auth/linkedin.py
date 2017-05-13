# coding: utf-8

import flask
import flask_login

import auth
import config
import util

from util import ndb, profiles
from main import app

linkedin_config = dict(
    access_token_method='POST',
    access_token_url='https://www.linkedin.com/uas/oauth2/accessToken',
    authorize_url='https://www.linkedin.com/uas/oauth2/authorization',
    base_url='https://api.linkedin.com/v1/',
    consumer_key=config.LinkedInOAuth2.linkedin_api_key,
    consumer_secret=config.LinkedInOAuth2.linkedin_secret_key,
    request_token_params={
        'scope': 'r_basicprofile r_emailaddress',
        'state': util.uuid(),
    },
)

linkedin = auth.create_oauth_app(linkedin_config, 'linkedin')

from auth import FlaskUser


def change_linkedin_query(uri, headers, body):
    headers['x-li-format'] = 'json'
    return uri, headers, body


linkedin.pre_request = change_linkedin_query


@app.route('/api/auth/callback/linkedin/')
def linkedin_authorized():
    response = linkedin.authorized_response()
    if response is None:
        flask.flash('You denied the request to sign in.')
        return flask.render_template('welcome.html')

    flask.session['access_token'] = (response['access_token'], '')
    me = linkedin.get('people/~:(id,first-name,last-name,email-address)')
    user_db = retrieve_user_from_linkedin(me.data)

    ndb[user_db.id] = user_db

    flask_user_db = FlaskUser(user_db)

    auth_params = flask.session.get('auth-params', {
        'next': flask.url_for('index'),
        'remember': False,
    })

    flask.session.pop('auth-params', None)
    if flask_login.login_user(flask_user_db, remember=auth_params['remember']):
        return flask.redirect(util.get_next_url(auth_params['next']))


@linkedin.tokengetter
def get_linkedin_oauth_token():
    return flask.session.get('access_token')


@app.route('/signin/linkedin/')
def signin_linkedin():
    return auth.signin_oauth(linkedin)


def retrieve_user_from_linkedin(response):
    auth_id = 'linkedin_%s' % response['id']
    # user_db = model.User.get_by('auth_ids', auth_id)
    # if user_db:
    #   return user_db

    names = [response.get('firstName', ''), response.get('lastName', '')]
    name = ' '.join(names).strip()
    email = response.get('emailAddress', '')

    return profiles[email]
