import pymongo
from pymongo import MongoClient
from marketplace import db, m_db
from marketplace.models import *
from marketplace import bcrypt
import sqlalchemy as sa
import json
from pprint import pprint
from collections import defaultdict
import datetime

for c in m_db.list_collection_names():
    m_db[c].drop()
print(m_db.list_collection_names())

record2dict = lambda r, id_field: {(c.name if c.name!=id_field else '_id'):
                                       str(getattr(r, c.name)) if c.name==id_field else getattr(r, c.name)
                                   for c in r.__table__.columns}

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
users_loc_data = [(str(user.id), user.location) for user in user_query]
users_loc_data=dict(users_loc_data)
users_roles_data = [(str(user.id), user.role) for user in user_query]
users_roles_data=dict(users_roles_data)
user_following_data = defaultdict(list)
for k, v in db.session.query(user_following).all():
    user_following_data[str(k)].append(str(v))


posts_query=Post.query.all()
posts_data = query2dict(posts_query, 'id')
posts_cat_data= [(str(post.id),post.category) for post in posts_query]
posts_cat_data=dict(posts_cat_data)
posts_loc_data=[(str(post.id),post.location) for post in posts_query]
posts_loc_data=dict(posts_loc_data)
user_post_data=[(str(post.author.id), post.id) for post in posts_query]
user_posts = defaultdict(list)
for k, v in user_post_data:
    user_posts[str(k)].append(str(v))
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
    user_id=post_data['user_id']
    related_cat = [cat.name for cat in posts_cat_data[post_id]]
    related_loc = posts_loc_data[post_id]
    posts.update_one({'_id': post_id},
            {'$set': {'user_id': str(user_id),
                      'categories': related_cat,
                      'location.postal_code':str(related_loc.postal_code),
                      'location.city':related_loc.city},
             '$unset':{'location_id':''}})

for user in users_data:
    user_id=user['_id']
    user_role=user['role_id']
    related_loc=users_loc_data[user_id]
    related_role=users_roles_data[user_id]
    related_posts=user_posts.get(user_id,[])
    if user_id in user_following_data:
        related_users=user_following_data[user_id]
    else:
        related_users=[]
    users.update_one({'_id': user_id},
                {'$set': {'location.postal_code':related_loc.postal_code,
                          'location.city': related_loc.city,
                          'role_id':related_role.id,
                          'following':related_users,
                          'post_ids':related_posts,
                          'role_id':str(user_role)},
                 '$unset':{'location_id':''}})


#embed comments in post
for comment_data in comments_data:
    comment_data['user_id']=str(comment_data['user_id'])
    post_id = str(comment_data['post_id'])
    del comment_data['post_id'] #we don't need this in our mongo DB
    posts.update_one({'_id': post_id},
            {'$push': {'comments': comment_data}})



#INDEXES
posts.create_index([('content', pymongo.TEXT), \
                    ('title', pymongo.TEXT), \
                    ('categories', pymongo.TEXT), \
                    ('location.city', pymongo.TEXT)])

users.create_indexes([pymongo.IndexModel([('following', pymongo.ASCENDING)]),
                      pymongo.IndexModel([('location.city', pymongo.TEXT)]) ])