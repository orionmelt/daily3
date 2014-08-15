"""
settings.py

Configuration for Flask app

Important: Place your keys in the secret_keys.py module, 
           which should be kept out of version control.

"""

import os

from local_settings import *

class Config(object):
    # Set secret keys for CSRF protection
    SECRET_KEY = CSRF_SECRET_KEY
    CSRF_SESSION_KEY = SESSION_KEY
    # Flask-Cache settings
    CACHE_TYPE = 'gaememcached'
    FP_DATE_FORMAT = OS_DATE_FORMAT
    

class Development(Config):
    DEBUG = True
    # Flask-DebugToolbar settings
    DEBUG_TB_PROFILER_ENABLED = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    CSRF_ENABLED = True
    
    CLIENT_ID = DEV_CLIENT_ID
    CLIENT_SECRET = DEV_CLIENT_SECRET
    REDIRECT_URI = DEV_REDIRECT_URI
    MYDAILY3_SUB = 'mydaily3_sandbox'
    GA_ID = None

class Testing(Config):
    TESTING = True
    DEBUG = True
    CSRF_ENABLED = True

class Production(Config):
    DEBUG = False
    CSRF_ENABLED = True
    
    CLIENT_ID = PROD_CLIENT_ID
    CLIENT_SECRET = PROD_CLIENT_SECRET
    REDIRECT_URI = PROD_REDIRECT_URI
    MYDAILY3_SUB = 'mydaily3'
    
    GA_ID = PROD_GA_ID