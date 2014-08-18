"""
urls.py

URL dispatch route mappings and error handlers

"""
from flask import render_template

from application import app
from application import views


## URL dispatch rules
# App Engine warm up handler
# See http://code.google.com/appengine/docs/python/config/appconfig.html#Warming_Requests
app.add_url_rule('/_ah/warmup', 'warmup', view_func=views.warmup)

# Home page
app.add_url_rule('/', 'home', view_func=views.home)

# Authorize page
app.add_url_rule('/authorize', 'authorize', view_func=views.authorize)

# Current user profile page
app.add_url_rule('/me', 'me', view_func=views.me)

# User profile page
app.add_url_rule('/u/<username>', 'user_profile', view_func=views.user_profile)

# Daily3 post
app.add_url_rule('/post_daily3', 'post_daily3', view_func=views.post_daily3, methods=['POST'])

# Add favorite
app.add_url_rule('/favorite/<post_id>', 'favorite', view_func=views.favorite)

# Favorites page
app.add_url_rule('/favorites', 'favorites', view_func=views.favorites)

# Logout
app.add_url_rule('/logout', 'logout', view_func=views.logout)

# Beta testing
app.add_url_rule('/beta', 'beta_on', view_func=views.beta_on)
app.add_url_rule('/beta-off', 'beta_off', view_func=views.beta_off)

# Bootstrap testing
app.add_url_rule('/bootstrap', 'bootstrap', view_func=views.bootstrap)

## Error handlers
# Handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Handle 500 errors
@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500
