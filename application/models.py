"""
models.py

App Engine datastore models

"""


from google.appengine.ext import ndb

class User(ndb.Model):
    """Models an individual user entry.
    
    Attributes:
        username        - reddit username
        created_reddit  - Date when user joined reddit
        created_daily3  - Date when user joined daily3.me
        access_token    - reddit OAuth access token
        refresh_token   - reddit OAuth refresh token
    """
    
    username = ndb.StringProperty()
    created_reddit = ndb.DateTimeProperty()
    created_daily3 = ndb.DateTimeProperty(auto_now_add=True)
    access_token = ndb.StringProperty(indexed=False)
    refresh_token = ndb.StringProperty(indexed=False)
    

class Post(ndb.Model):
    """Models an individual Daily3 post entry.
    
    Attributes:
        posted       - DateTime when entry was posted
        posted_date  - Date when entry was posted - added despite already 
                       existing posted (DateTime), for ndb query performance
        user         - User who created this post
        item1        - Daily3 item 1
        item2        - Daily3 item 2
        item3        - Daily3 item 3
    """
    
    posted = ndb.DateTimeProperty(auto_now_add=True)
    posted_date = ndb.DateProperty(auto_now_add=True)
    user = ndb.KeyProperty(kind="User")
    item1 = ndb.TextProperty()
    item2 = ndb.TextProperty()
    item3 = ndb.TextProperty()
    source_link = ndb.StringProperty(indexed=False)
    
class Favorite(ndb.Model):
    """Models a user marking a Daily3 post as a favorite. 

    Attributes:
        user        - User who marked post as favorite  
        post        - The Daily3 post that was marked as favorite
        favorited   - DateTime when the post was favorited 
    """

    user = ndb.KeyProperty(kind="User")
    post = ndb.KeyProperty(kind="Post")
    favorited = ndb.DateTimeProperty(auto_now_add=True)

class ExampleModel(ndb.Model):
    """Example Model"""
    example_name = ndb.StringProperty(required=True)
    example_description = ndb.TextProperty(required=True)
    added_by = ndb.UserProperty()
    timestamp = ndb.DateTimeProperty(auto_now_add=True)
