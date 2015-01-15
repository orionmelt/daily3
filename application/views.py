"""
views.py

URL route handlers

"""
from google.appengine.api import memcache
from google.appengine.ext import ndb

from flask import request, render_template, flash, url_for, redirect, session, g, abort
from itsdangerous import URLSafeSerializer
#TODO - flask_cache

from application import app
from models import User, Post, Favorite

import sys, logging
from datetime import datetime, date
from uuid import uuid4
import praw

UNKNOWN_LOGIN_ERROR_TEXT = "Unknown error authenticating with reddit. Please try again after some time."
UNKNOWN_POST_ERROR_TEXT = "Unknown error posting to reddit. Your post was *not* posted on /r/MyDaily3."
CAPTCHA_ERROR_TEXT = "Reddit requires a captcha challenge before you can post because you have low karma. \
                      We can't handle captcha now. Your post was *not* posted on /r/MyDaily3."

BETA_SUFFIX = '_a'

def get_reddit():
    reddit = memcache.get('reddit')
    if not reddit:
        reddit = praw.Reddit('Daily3.me by u/orionmelt ver 0.3.')
        reddit.set_oauth_app_info(app.config['CLIENT_ID'], app.config['CLIENT_SECRET'], app.config['REDIRECT_URI'])
        memcache.add('reddit',reddit)
    return reddit

    
def post_to_sub(post):
    reddit = get_reddit()
    try: 
        reddit.set_access_credentials({'identity','submit'}, g.user.access_token, g.user.refresh_token)
    except praw.errors.OAuthInvalidToken:
        logging.debug("OAuthInvalidToken exception (token expired) while posting to sub for user %s. Refreshing..." % g.user.username)
        try: 
            access_info = reddit.refresh_access_information(g.user.refresh_token)
            reddit.set_access_credentials(access_info['scope'], access_info['access_token'], access_info['refresh_token'])
        except:
            logging.error("E001: Unknown exception while posting to sub for user %s" % g.user.username)
            logging.error(sys.exc_info())
            flash(UNKOWN_ERROR_TEXT, 'error')
            return None
    except:
        logging.debug("E002: Unknown exception while posting to sub for user %s" % g.user.username)
        logging.debug(sys.exc_info())
        flash(UNKOWN_ERROR_TEXT, 'error')
        return None
    try:
        submission = reddit.submit(
                        app.config['MYDAILY3_SUB'], 
                        #TODO - if all items can fit in self title, concatenate and use all three; else just use item1
                        post.item1,
                        text=" * " + post.item1 + "\n * " + post.item2 + "\n * " + post.item3, 
                        raise_captcha_exception=True
                    )
        return submission.url
    except praw.errors.InvalidCaptcha:
        logging.error("E003: Captcha exception for user %s" % g.user.username)
        flash(CAPTCHA_ERROR_TEXT, 'error')
        return None
    except: 
        logging.error("E004: Unknown exception while posting to sub for user %s" % g.user.username)
        logging.error(sys.exc_info())
        flash(UNKNOWN_ERROR_TEXT, 'error')
        return None


def post_to_thread(post):
    reddit = get_reddit()
    logging.debug("@post_to_thread: user=%s" % g.u)
    try:
        reddit.set_access_credentials({'identity','submit'}, g.user.access_token, g.user.refresh_token)
    except praw.errors.OAuthInvalidToken:
        logging.debug("OAuthInvalidToken exception (token expired) while posting to thread for user %s. Refreshing..." % g.user.username)
        try: 
            access_info = reddit.refresh_access_information(g.user.refresh_token)
            reddit.set_access_credentials(access_info['scope'], access_info['access_token'], access_info['refresh_token'])
        except:
            logging.error("E101: Unknown exception while posting to thread for user %s" % g.user.username)
            logging.error(sys.exc_info())
            flash(UNKNOWN_ERROR_TEXT, 'error')
            return None
    except:
        logging.error("E102: Unknown exception while posting to thread for user %s" % g.user.username)
        logging.error(sys.exc_info())
        flash(UNKNOWN_ERROR_TEXT, 'error')
        return None
    try:
        threads = reddit.get_subreddit(app.config['MYDAILY3_SUB']).get_new()
        for t in threads:
            if t.stickied:
                return t.add_comment(" * " + post.item1 + "\n * " + post.item2 + "\n * " + post.item3).permalink
        return None
    except praw.errors.InvalidCaptcha:
        logging.error("E103: Captcha exception for user %s" % g.user.username)
        flash(CAPTCHA_ERROR_TEXT, 'error')
        return None
    except: 
        logging.error("E104: Unknown exception while posting to thread for user %s" % g.user.username)
        logging.error(sys.exc_info())
        flash(UNKNOWN_ERROR_TEXT, 'error')
        return None


@app.before_request
def load_user():
    """Load common items required for every request."""
    u = None
    b = None
    user = None
    user_post = None
    login_url = None
    
    session_u = session.get('user',None)
    signature, cookie_u = URLSafeSerializer(app.config['SECRET_KEY']).loads_unsafe(request.cookies.get('u',None)) \
                          if not session_u and request.cookies.get('u',None) else (False, None)
    
    u = session_u or cookie_u
    b = session.get('beta',False) or request.cookies.get('b',False)
    
    session['user'] = u
    session['beta'] = b
    
    logging.debug("@before_request: user=%s" % u)
    
    if session.get('logout',None):
        session['user'] = None
        u = None
        
    if session.get('beta_off',None):
        session['beta'] = None
        b = None
        
    # By now, we should have username from either session or cookie; if not, user's not logged in.
    if u:
        user = User.get_by_id(u)
    
    if user:
        try:
            user_post = Post.query(Post.posted_date==datetime.today(),Post.user==user.key).get()
        except IndexError:
            pass
    else:
        logging.debug("@before_request: no session['user']")
        reddit = get_reddit()
        login_url = reddit.get_authorize_url(str(uuid4()),['identity','submit'],refreshable=True)
    
    g.u = u
    g.user = user
    g.user_post = user_post
    g.login_url = login_url
    
    g.ga_id = app.config['GA_ID']
    g.beta = b
    
        
@app.after_request
def set_cookies(response):
    u_expires = 2678400
    b_expires = 2678400
    
    if session.get('logout',None):
        session['logout'] = None
        u_expires = 0
    
    if session.get('beta_off',None):
        session['beta_off'] = None
        b_expires = 0
    
    if g.u:
        response.set_cookie('u',URLSafeSerializer(app.config['SECRET_KEY']).dumps(g.u),u_expires)
    if g.beta:
        response.set_cookie('b',g.beta,b_expires)
        
    return response

def home():
    template = 'index'
    posts = memcache.get('posts')
    if not posts:
        posts = Post.query().order(-Post.posted).fetch(50)
        memcache.add('posts', posts)
    if g.user:
        favorites = Favorite.query(Favorite.user==g.user.key).map(lambda f: f.post)
        for post in posts:
            post.faved = post.key in favorites
    if g.beta:
        template += BETA_SUFFIX
    return render_template('%s.html' % template, posts=posts)


def authorize():
    error = request.args.get('error')
    code = request.args.get('code')
    state = request.args.get('state')
    #TODO: Handle state
    if error:
        flash(error, 'error')
        #TODO: Handle error
        return redirect(url_for('home'))
    if not code:
        #TODO: No code received, something went wrong
        return redirect(url_for('home'))
    else:
        reddit = get_reddit()
        try:
            access_info = reddit.get_access_information(code)
            praw_user = reddit.get_me()
            user = User.get_by_id(praw_user.name)
            if not user:
                user = User(
                    id=praw_user.name,
                    username=praw_user.name,
                    created_reddit=datetime.fromtimestamp(praw_user.created)
                    )
            user.access_token = access_info['access_token']
            user.refresh_token = access_info['refresh_token']
            user.put()
            session['user'] = user.username
            logging.debug("@authorize: user=%s" % g.u)
        except:
            logging.error("E201: Unknown exception while authenticating")
            logging.error(sys.exc_info())
            flash(UNKNOWN_LOGIN_ERROR_TEXT, 'error')
            return redirect(url_for('home'))            
        
        return redirect(url_for('home'))

        
def user_profile(username):
    template = 'user_profile'
    posts = None
    profile = User.get_by_id(username)
    if profile:
        posts = Post.query(Post.user==profile.key).order(-Post.posted).fetch()
        if g.user:
            for post in posts:
                post.faved = True if Favorite.query(Favorite.user==g.user.key,Favorite.post==post.key).get() else False
        if g.beta:
            template += BETA_SUFFIX
        return render_template('%s.html' % template, profile=profile, posts=posts)
    else:
        abort(404)


def favorites():
    template = 'favorites' + BETA_SUFFIX
    posts=None
    if g.user:
        posts=ndb.get_multi(Favorite.query(Favorite.user==g.user.key).map(lambda f: f.post))
        for post in posts:
            post.faved = True
        return render_template('%s.html' % template, posts=posts)
    else:
        return redirect(url_for('home'))


def me():
    template = 'user_profile'
    posts = None
    if g.user:
        profile = g.user
        posts = Post.query(Post.user==profile.key).order(-Post.posted).fetch()
        for post in posts:
            post.faved = True if Favorite.query(Favorite.user==g.user.key,Favorite.post==post.key).get() else False
        if g.beta:
            template += BETA_SUFFIX
        return render_template('%s.html' % template, profile=profile, posts=posts)
    else:
        return redirect(url_for('home'))

      
def post_daily3():
    template = 'includes/user_panel'
    if g.user:
        item1 = request.form['item1']
        item2 = request.form['item2']
        item3 = request.form['item3']
        post = Post(
                user=g.user.key,
                item1=item1,
                item2=item2,
                item3=item3
                )
        # Toggle here between posting to sub and thread
        # source_link = post_to_sub(post)
        source_link = post_to_thread(post)
        if source_link:
            post.source_link = source_link
        post.put()
        g.user_post = post
        memcache.delete('posts')
    if g.beta:
        template += BETA_SUFFIX
    return render_template('%s.html' % template)


def favorite(post_id):
    if not g.user:
        return 'User not logged in. Cannot favorite %s.' % post_id
    f = Favorite.query(Favorite.user==g.user.key,Favorite.post==ndb.Key(urlsafe=post_id)).get()
    if f:
        f.key.delete()
        return 'Removed favorite %s for user %s' % (post_id, g.user.username)
    else:
        f = Favorite(
                user=g.user.key,
                post=ndb.Key(urlsafe=post_id)
        )
        f.put()
        return 'Added  favorite %s for user %s' % (post_id, g.user.username)


def logout():
    session.pop('user', None)
    session['logout'] = True
    return redirect(url_for('home'))


def beta_on():
    session['beta'] = True
    g.beta = True
    return redirect(url_for('home'))


def beta_off():
    session.pop('beta', None)
    session['beta_off'] = True
    return redirect(url_for('home'))


def warmup():
    """App Engine warmup handler
    See http://code.google.com/appengine/docs/python/config/appconfig.html#Warming_Requests

    """
    return ''

