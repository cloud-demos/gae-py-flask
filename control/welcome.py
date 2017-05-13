# coding: utf-8

import flask

import config

from main import app
import auth


###############################################################################
# Welcome
###############################################################################
@app.route('/')
def welcome():
    return flask.render_template('welcome.html', html_class='welcome')


###############################################################################
# index
###############################################################################
@app.route('/index')
@auth.login_required
def index():
    return flask.render_template('index.html')


###############################################################################
# Warmup request
###############################################################################
@app.route('/_ah/warmup')
def warmup():
    # TODO: put your warmup code here
    return 'success'
