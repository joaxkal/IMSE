import pymongo
from pymongo import MongoClient
from marketplace import db
from marketplace.models import *
from marketplace import bcrypt
import sqlalchemy as sa
import json
from pprint import pprint

# connetcion
client = MongoClient('mongodb://localhost:27017/',
                     username='user',
                     password='password'
                     )
# clear db from last tests
client.drop_database('nosql_database')
m_db = client.nosql_database

record2dict = lambda r: {c.name: getattr(r, c.name) for c in r.__table__.columns}

def query2dict(query_result):
    # get query results (list of object) and turn them into list of dictionaires
    return [record2dict(record) for record in query_result]

def remove_id(query_dictionary):
    # remove ids assigned by relational db (we keep _id from mongoDB instead
    [record.pop('id', None) for record in query_dictionary]
    return query_dictionary

# query rel db for data from all relational tabels
users_data = query2dict(User.query.all())
locations_data = query2dict(Location.query.all())
categories_data = query2dict(Category.query.all())
posts_data = query2dict(Post.query.all())
roles_data = query2dict(Role.query.all())
comments_data = query2dict(Comment.query.all())

cat_association_data = db.session.query(cat_association_table).all()
user_following_data = db.session.query(user_following).all()

#creating collection in mongoDB
users = m_db.users
posts = m_db.posts
locations = m_db.locations
categories = m_db.categories

# inserting data from reldb to mongodb
locations.insert_many(locations_data)
categories.insert_many(categories_data)
users.insert_many(users_data)
posts.insert_many(posts_data)

#embed comments in post
for comment_data in comments_data:
    post_id = comment_data['post_id']
    del comment_data['post_id'] #we don't need this in our mongo DB
    posts.update_one({'id': post_id},
            {'$push': {'comments': comment_data}})


# reference categories on the N-side
for post_data in posts_data:
    post_id = post_data['id']
    related_cat = Post.query.filter_by(id=post_id).first().category
    related_cat = query2dict(related_cat)

    related_loc = Post.query.filter_by(id=post_id).first().location
    related_loc = record2dict(related_loc)

    posts.update_one({'id': post_id},
            {'$set': {'categories': related_cat}})

    posts.update_one({'id': post_id},
            {'$set': {'location': related_loc}})

pprint(posts.find_one({}))
# reference location by city
