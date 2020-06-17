import pymongo
from pymongo import MongoClient
from marketplace import db, m_db
from marketplace.models import *
from marketplace import bcrypt
import sqlalchemy as sa
import json
from pprint import pprint
from itertools import groupby
from operator import itemgetter


for c in m_db.list_collection_names():
    m_db[c].drop()

record2dict = lambda r, id_field: \
    {(c.name if c.name!=id_field else '_id'): getattr(r, c.name) for c in r.__table__.columns}

def query2dict(query_result, id_field):
    # get query results (list of object) and turn them into list of dictionaires
    return [record2dict(record, id_field) for record in query_result]

def remove_field(query_dictionary, field):
    # remove ids assigned by relational db (we keep _id from mongoDB instead)
    [record.pop(field, None) for record in query_dictionary]
    return query_dictionary

## QUERY DATA FROM POSTGRES

#query locations, categories and roles
locations_data = query2dict(Location.query.all(), 'postal_code')
categories_data = query2dict(Category.query.all(), 'name')
categories_data=remove_field(categories_data, 'id') # quick fix of mistake from M2
roles_data = query2dict(Role.query.all(), 'id')

# query users, posts comments
# together with categories, locations and roles
user_query=User.query.all()
users_data = query2dict(user_query, 'id')
users_loc_data = [(user.id, user.location) for user in user_query]
users_loc_data=dict(users_loc_data)
users_roles_data = [(user.id, user.role) for user in user_query]
users_roles_data=dict(users_roles_data)
user_following_data = db.session.query(user_following).all()
user_following_data = dict([(k, list(list(zip(*g))[1])) for k, g in groupby(user_following_data, itemgetter(0))])

posts_query=Post.query.all()
posts_data = query2dict(posts_query, 'id')
posts_cat_data= [(post.id,post.category) for post in posts_query]
posts_cat_data=dict(posts_cat_data)
posts_loc_data=[(post.id,post.location) for post in posts_query]
posts_loc_data=dict(posts_loc_data)

comments_data=query2dict(Comment.query.all(), 'id')

## DATA INTO MONGO

#creating collection in mongoDB
users = m_db.users
posts = m_db.posts
locations = m_db.locations
categories = m_db.categories
roles=m_db.roles

# inserting data to mongodb collections
locations.insert_many(locations_data)
categories.insert_many(categories_data)
users.insert_many(users_data)
posts.insert_many(posts_data)
roles.insert_many(roles_data)


# reference categories, locations and roles on the N-side
for post_data in posts_data:
    post_id = post_data['_id']
    related_cat = [cat.id for cat in posts_cat_data[post_id]]
    related_loc = posts_loc_data[post_id]
    posts.update_one({'_id': post_id},
            {'$set': {'categories': related_cat,
                      'location.postal_code':related_loc.postal_code,
                      'location.city':related_loc.city},
             '$unset':{'location_id':''}})

for user in users_data:
    user_id=user['_id']
    related_loc=users_loc_data[user_id]
    related_role=users_roles_data[user_id]
    if user_id in user_following_data:
        related_users=user_following_data[user_id]
    else:
        related_users=[]
    users.update_one({'_id': user_id},
                {'$set': {'location.postal_code':related_loc.postal_code,
                          'location.city': related_loc.city,
                          'role_id':related_role.id,
                          'following':related_users},
                 '$unset':{'location_id':''}})


#embed comments in post
for comment_data in comments_data:
    post_id = comment_data['post_id']
    del comment_data['post_id'] #we don't need this in our mongo DB
    posts.update_one({'_id': post_id},
            {'$push': {'comments': comment_data}})

## SET INDEX

# #todo:
# W postach
# multi key na categories
# normalny na locations
# text na content i title

#W userach
# normalny na lcqtions?
