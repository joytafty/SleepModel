import json
import flask
from flask import Flask, url_for, render_template, session
from functools import update_wrapper
from cherrypy import wsgiserver
import argparse
import datetime
import os
from store import redis
import time
import numpy as np
import urlparse

# Load data from local redis
def load():
    # see: http://python-fitbit.readthedocs.org/en/latest/#fitbit-api
    import fitbit
    fb = fitbit.Fitbit(
        os.getenv('CONSUMER_KEY'),
        os.getenv('CONSUMER_SECRET'), 
        user_key=os.getenv('USER_KEY'),
        user_secret=os.getenv('USER_SECRET'))
    
    redis.delete('fitbit')
    
    if True:
        sleepData = dict();
        sl1 = fb.time_series('sleep/startTime', period='max')['sleep-startTime']
        sl2 = fb.time_series('sleep/timeInBed', period='max')['sleep-timeInBed']
        sl3 = fb.time_series('sleep/minutesAsleep', period='max')['sleep-minutesAsleep']
        sl4 = fb.time_series('sleep/minutesAwake', period='max')['sleep-minutesAwake']
        sl5 = fb.time_series('sleep/minutesToFallAsleep', period='max')['sleep-minutesToFallAsleep']
        sl6 = fb.time_series('sleep/minutesAfterWakeup', period='max')['sleep-minutesAfterWakeup']
        sl7 = fb.time_series('sleep/efficiency', period='max')['sleep-efficiency']
        
        for sl in range(len(sl1)-1):            
            if sl1[sl]['value'] != '':                
                tempdate = datetime.datetime.strptime(sl1[sl]['dateTime'], '%Y-%m-%d').timetuple()
                sleepData['date'] = time.mktime(tempdate)
                temptime = time.strptime((sl1[sl]['dateTime'] + '-' + sl1[sl]['value']), '%Y-%m-%d-%H:%M')
                sleepData['startTime'] = time.mktime(temptime)
                sleepData['timeInBed'] = sl2[sl]['value']
                sleepData['minutesAsleep'] = sl3[sl]['value']
                sleepData['minutesAwake'] = sl4[sl]['value']
                sleepData['minutesToFallAsleep'] = sl5[sl]['value']
                sleepData['minutesAfterWakeup'] = sl6[sl]['value']
                sleepData['efficiency'] = sl7[sl]['value']
                s = json.dumps(sleepData)
                redis.sadd('fitbit', s)
                print s


def server():
    from cherrypy import wsgiserver
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/map/")
    def index3():
        return render_template("index3.html")

    @app.route("/login")
    def login():
        print "Start setting oAuth parameters"
        # import urllib2
        # import oauth2 as oauth

        CLIENT_ID = os.getenv("UP_client_id")
        CLIENT_SECRET = os.getenv("UP_client_secret")
        REDIRECT_URI = "https://sleepmodel.herokuapp.com/"
        base_auth_url = 'https://jawbone.com/auth/oauth2/auth'
        auth_params = "response_type=code&client_id=" + CLIENT_ID + "&scope=basic_read&redirect_uri=" + REDIRECT_URI
        base_token_url = 'https://jawbone.com/auth/oauth2/token'
        token_params = "client_id=" + CLIENT_ID + "&client_secret=" + CLIENT_SECRET + "&grant_type=authorization_code"
        # # Get authentication url for request token
        auth_url = base_auth_url + "?" + auth_params
        # resp, content = client.request(base_auth_url)
        token_url = base_token_url + "?" + token_params

        print "Finish setting oAuth parameters"

        # Basic version
        import oauth2 as oa2
        import logging
        consumer = oa2.Consumer(key=os.getenv("UP_client_id"), secret=os.getenv("UP_client_secret"))
        # token = oa2.Token(flask.request.args.get('oauth_token'), flask.request.args.get('oauth_verifier'))
        client = oa2.Client(consumer)
        print consumer
        print client
        # resp, content = client.request(auth_url)
        # print resp

        # return flask.redirect(REDIRECT_URI)

        from flask_oauth import OAuth 
        from flask_oauth import request as rex
        # oa = OAuth()
        # print oa
        sleepUP = OAuth().remote_app('sleepmodel', 
            base_url='https://jawbone.com/auth/oauth2/auth',
            request_token_url=base_auth_url,
            access_token_url=base_token_url,
            authorize_url=base_token_url,
            consumer_key=os.getenv("UP_client_id"),
            consumer_secret=os.getenv("UP_client_secret")
            )
        print sleepUP

        # return render_template("index.html")
        out = sleepUP.authorize(callback=url_for('oauth_authorized', 
            next=flask.request.args.get('next') or None))
        print out
        return out

    def get_UP_token(token=None):
        return session.get('UP_auth_token')

    @app.route("/oauth-authorized")
    # @sleepUP.authorized_handler
    # def oauth_authorized(resp):
    #     next_url = flask.request.args.get('next') or url_for('index')
    #     if resp is None:
    #         flask("Your credential is unrecognized!")
    #         return redirect(next_url)
        
    #     session['UP_token'] = (
    #         resp["oauth_token"], resp["oauth_token_secret"]
    #         )

    @app.route("/bar/")
    def bar():
        return render_template("bar.html")

    @app.route("/sleep/")
    def sleep():
        return render_template("sleep.html")

    @app.route("/up/")
    def up():
        return render_template("dcjsup.html")    

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
    server = wsgiserver.CherryPyWSGIServer(('0.0.0.0', 8001), d)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Do stuff")
    parser.add_argument('command', action="store", choices=['load', 'server'])
    args = parser.parse_args()

    # port = 8000
    # Open a web browser pointing at the app.
    # os.system("open http://localhost:{0}".format(port))

    # Set up the development server on port 8000.
    if args.command == 'load':
        load()
    if args.command == 'server':
        server()