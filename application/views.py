"""
views.py

URL route handlers

Note that any handler params must match the URL route params.
For example the *say_hello* handler, handling the URL route '/hello/<username>',
  must be passed *username* as the argument.

"""
from google.appengine.api import users
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError

from flask import request, render_template, flash, url_for, redirect, session, g, abort

from flask_cache import Cache

from application import app
from decorators import login_required, admin_required
from forms import ExampleForm
from models import User, Post, Favorite, ExampleModel
from google.appengine.ext import ndb

from google.appengine.api import memcache
from datetime import datetime, date
from uuid import uuid4
import praw
import logging, sys

# Flask-Cache (configured to use App Engine Memcache API)
cache = Cache(app)

def get_reddit():
    reddit = memcache.get('reddit')
    if not reddit:
        reddit = praw.Reddit('Daily3.me by u/orionmelt ver 0.2.')
        reddit.set_oauth_app_info(app.config['CLIENT_ID'], app.config['CLIENT_SECRET'], app.config['REDIRECT_URI'])
        memcache.add('reddit',reddit)
    return reddit
    
def post_to_sub(post):
    reddit = get_reddit()
    try: 
        reddit.set_access_credentials({'identity','submit'}, g.user.access_token, g.user.refresh_token)
    except praw.errors.OAuthInvalidToken:
        logging.info("OAuthInvalidToken exception (token expired) while posting to sub for user %s. Refreshing..." % g.user.username)
        try: 
            access_info = reddit.refresh_access_information(g.user.refresh_token)
            reddit.set_access_credentials(access_info['scope'], access_info['access_token'], access_info['refresh_token'])
        except:
            logging.error("E001: Unknown exception while posting to sub for user %s" % g.user.username)
            logging.error(sys.exc_info())
            flash("Unknown error posting to reddit. Your post was *not* posted on /r/MyDaily3.", 'error')
            return None
    except:
        logging.error("E002: Unknown exception while posting to sub for user %s" % g.user.username)
        logging.error(sys.exc_info())
        flash("Unknown error posting to reddit. Your post was *not* posted on /r/MyDaily3.", 'error')
        return None
    try:
        submission = reddit.submit(
                        app.config['MYDAILY3_SUB'], 
                        post.item1, 
                        text=" * " + post.item1 + "\n * " + post.item2 + "\n * " + post.item3, 
                        raise_captcha_exception=True
                    )
        return submission.url
    except praw.errors.InvalidCaptcha:
        logging.error("E003: Captcha exception for user %s" % g.user.username)
        flash("Reddit requires a captcha challenge before you can post because you have low karma. \
               We can't handle captcha now. Your post was *not* posted on /r/MyDaily3.", 'error')
        return None
    except: 
        logging.error("E004: Unknown exception while posting to sub for user %s" % g.user.username)
        logging.error(sys.exc_info())
        flash("Unknown error posting to reddit. Your post was *not* posted on /r/MyDaily3.", 'error')
        return None
        
def post_to_thread(post):
    reddit = get_reddit()
    try:
        reddit.set_access_credentials({'identity','submit'}, g.user.access_token, g.user.refresh_token)
    except praw.errors.OAuthInvalidToken:
        logging.info("OAuthInvalidToken exception (token expired) while posting to thread for user %s. Refreshing..." % g.user.username)
        try: 
            access_info = reddit.refresh_access_information(g.user.refresh_token)
            reddit.set_access_credentials(access_info['scope'], access_info['access_token'], access_info['refresh_token'])
        except:
            logging.error("E101: Unknown exception while posting to thread for user %s" % g.user.username)
            logging.error(sys.exc_info())
            flash("Unknown error posting to reddit. Your post was *not* posted on /r/MyDaily3.", 'error')
            return None
    except:
        logging.error("E102: Unknown exception while posting to thread for user %s" % g.user.username)
        logging.error(sys.exc_info())
        flash("Unknown error posting to reddit. Your post was *not* posted on /r/MyDaily3.", 'error')
        return None
    try:
        threads = reddit.get_subreddit(app.config['MYDAILY3_SUB']).get_new()
        for t in threads:
            if t.stickied:
                return t.add_comment(" * " + post.item1 + "\n * " + post.item2 + "\n * " + post.item3).permalink
        return None
    except praw.errors.InvalidCaptcha:
        logging.error("E103: Captcha exception for user %s" % g.user.username)
        flash("Reddit requires a captcha challenge before you can post because you have low karma. \
               We can't handle captcha now. Your post was *not* posted on /r/MyDaily3.", 'error')
        return None
    except: 
        logging.error("E104: Unknown exception while posting to thread for user %s" % g.user.username)
        logging.error(sys.exc_info())
        flash("Unknown error posting to reddit. Your post was *not* posted on /r/MyDaily3.", 'error')
        return None


@app.before_request
def load_user():
    """Load currently logged in user and their current (today's) post, or a login URL if user is not logged in"""
    user = None
    user_post = None
    login_url = None
    
    try:
        if session['user']:
            user = User.get_by_id(session['user'])
    except KeyError:
        pass
    
    if user:
        try:
            user_post = Post.query(Post.posted_date==datetime.today(),Post.user==user.key).get()
        except IndexError:
            pass
    else:
        reddit = get_reddit()
        login_url = reddit.get_authorize_url(str(uuid4()),['identity','submit'],refreshable=True)

    g.user = user
    g.user_post = user_post
    g.login_url = login_url
    g.ga_id = app.config['GA_ID']
        

def home(version="default"):
    posts = Post.query().order(-Post.posted).fetch()
    if version=="default":
        return render_template('index.html', posts=posts)
    elif version=="a":
        if g.user:
            for post in posts:
                post.faved = True if Favorite.query(Favorite.user==g.user.key,Favorite.post==post.key).get() else False
        return render_template('index_a.html', posts=posts)
    
def authorize():
    error = request.args.get('error')
    code = request.args.get('code')
    state = request.args.get('state')
    #TODO: Handle state here
    if error:
        flash(error, 'error')
        #TODO: Handle error here
        return redirect(url_for('home'))
    if not code:
        #TODO: No code received, something went wrong
        return redirect(url_for('home'))
    else:
        reddit = get_reddit()
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
        return redirect(url_for('home'))
        
def user_profile(username,version="default"):
    posts = None
    profile = User.get_by_id(username)
    if profile:
        posts = Post.query(Post.user==profile.key).order(-Post.posted).fetch()
        if version=="default":
            return render_template('user_profile.html', profile=profile, posts=posts)
        elif version=="a":
            if g.user:
                for post in posts:
                    post.faved = True if Favorite.query(Favorite.user==g.user.key,Favorite.post==post.key).get() else False

            return render_template('user_profile_a.html', profile=profile, posts=posts)
    else:
        abort(404)

def me(version="default"):
    posts = None
    if g.user:
        profile = g.user
        posts = Post.query(Post.user==profile.key).order(-Post.posted).fetch()
        if version=="default":
            return render_template('user_profile.html', profile=profile, posts=posts)
        elif version=="a":
            return render_template('user_profile_a.html', profile=profile, posts=posts)
    else:
        return redirect(url_for('home'))
        
      
def post_daily3(version="default"):
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
        #post_to_sub(post)
        source_link = post_to_thread(post)
        if source_link:
            post.source_link = source_link
        post.put()
        g.user_post = post
    if version=="default":
        return render_template('user_panel.html')
    elif version=="a":
        return render_template('user_panel_a.html')

def favorite(post_id):
    if not g.user:
        return 'Not faved'
    f = Favorite.query(Favorite.user==g.user.key,Favorite.post==ndb.Key(urlsafe=post_id)).get()
    if f:
        f.key.delete()
        return 'Unfaved!'
    else:
        f = Favorite(
                user=g.user.key,
                post=ndb.Key(urlsafe=post_id)
        )
        f.put()
        return 'Faved!'        

def logout():
    session.pop('user', None)
    return redirect(url_for('home'))
    
def say_hello(username):
    """Contrived example to demonstrate Flask's url routing capabilities"""
    return 'Hello %s' % username


@login_required
def list_examples():
    """List all examples"""
    examples = ExampleModel.query()
    form = ExampleForm()
    if form.validate_on_submit():
        example = ExampleModel(
            example_name=form.example_name.data,
            example_description=form.example_description.data,
            added_by=users.get_current_user()
        )
        try:
            example.put()
            example_id = example.key.id()
            flash(u'Example %s successfully saved.' % example_id, 'success')
            return redirect(url_for('list_examples'))
        except CapabilityDisabledError:
            flash(u'App Engine Datastore is currently in read-only mode.', 'info')
            return redirect(url_for('list_examples'))
    return render_template('list_examples.html', examples=examples, form=form)


@login_required
def edit_example(example_id):
    example = ExampleModel.get_by_id(example_id)
    form = ExampleForm(obj=example)
    if request.method == "POST":
        if form.validate_on_submit():
            example.example_name = form.data.get('example_name')
            example.example_description = form.data.get('example_description')
            example.put()
            flash(u'Example %s successfully saved.' % example_id, 'success')
            return redirect(url_for('list_examples'))
    return render_template('edit_example.html', example=example, form=form)


@login_required
def delete_example(example_id):
    """Delete an example object"""
    example = ExampleModel.get_by_id(example_id)
    try:
        example.key.delete()
        flash(u'Example %s successfully deleted.' % example_id, 'success')
        return redirect(url_for('list_examples'))
    except CapabilityDisabledError:
        flash(u'App Engine Datastore is currently in read-only mode.', 'info')
        return redirect(url_for('list_examples'))


@admin_required
def admin_only():
    """This view requires an admin account"""
    return 'Super-seekrit admin page.'


@cache.cached(timeout=60)
def cached_examples():
    """This view should be cached for 60 sec"""
    examples = ExampleModel.query()
    return render_template('list_examples_cached.html', examples=examples)


def warmup():
    """App Engine warmup handler
    See http://code.google.com/appengine/docs/python/config/appconfig.html#Warming_Requests

    """
    return ''

