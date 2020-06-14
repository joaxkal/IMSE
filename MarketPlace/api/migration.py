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
    if len(query_result) == 1:
        query_result = [query_result]
    return [record2dict(record) for record in query_result]

def remove_id(query_dictionary):
    # remove ids assigned by relational db (we keep _id from mongoDB instead
    [record.pop('id', None) for record in query_dictionary]
    return query_dictionary

# query rel db for data from all relational tabels
user_data = query2dict(User.query.all())
location_data = query2dict(Location.query.all())
category_data = query2dict(Category.query.all())
posts_data = query2dict(Post.query.all())
roles_data = query2dict(Role.query.all())
comments_data = query2dict(Comment.query.all())

cat_association_data = db.session.query(cat_association_table).all()
user_following_data = db.session.query(user_following).all()

#creating a users collection in mongoDB
users = m_db.users
# inserting data from reldb to mongodb
users.insert_many(user_data)
