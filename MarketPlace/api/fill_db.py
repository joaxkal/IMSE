from flaskblog import db
from flaskblog.models import *
from flaskblog import bcrypt

print(db)
db.drop_all()
db.create_all()

#Creating locations
mock_location = [
    [1010,'Wien', 'Austria'],
    [1011, 'Barcelona', 'Spain'],
    [2010, 'Warszawa', 'Poland'],
    [2011, 'Budapest', 'Hungary'],
    [3010, 'Piastow', 'Poland'],
    [3011, 'Athens', 'Greece'],
    [4011, 'Tomaszow Mazowiecki', 'Poland'],
    [4012, 'Bialystok', 'Poland']
]
for l in mock_location:
    loc=Location(postal_code=l[0],city=l[1], state=l[2])
    db.session.add(loc)

#Creating Users
pswd = bcrypt.generate_password_hash('test').decode('utf-8')

mock_users=[
    ['jotde',796017779],
    ['joaxkal',396717770],
    ['moniszcz',496717719],
    ['rich_walkman',896717279],
    ['WKonicki',420420420]
]

for i, u in enumerate(mock_users):
    user=User(username=u[0], password=pswd, email=u[0]+'@gmail.com', phone=u[1],
              image_file='default.jpg',location_id=mock_location[i][0])
    db.session.add(user)

#Create categories and posts
k=0
c=0
description = 'Lorem ipsum'

mock_cat = [
    ["books", "Books, comics and other paper media"],
    ["sport", "Sport equipment"],
    ["technology", "Computers, phones and other electrical machines"],
    ["services", "Non-physical iteams"],
    ["other", "Offers that do not fit in other category"],
    ["cooking", "Food, cooking and kitchen"],
    ["furniture", "Furniture for home and office"],
    ["clothes", "Clothes and fashion"],
    ["immobilites", "Flats, houses and renting"],
    ["vehicles", "Cars, bicycles and boats"]
]

mock_post = [
    ["500 Shades of Grey", "Intelligent book. " * 10],
    ["Basbell bat", "Never used for playing, perfect condition. " * 2],
    ["Selling IPhone12", "IPhone. "*12],
    ["Will make apps for money", "Even java is ok. " * 10],
    ["Showel", "Selling showel. " * 10],
    ["Pierogi", "Traditioal Polish pierogi with mashrooms" * 10],
    ["Desk", "Desk. Es ist supeerrrr :>>>> " * 10],
    ["CORONAVIRUS MASK",  " KILLS ALL CORONA" * 10],
    ["Nice flat 5m2", "Good conditions, no windows. " * 10],
    ["Big Boat", "BOATifull!! "]
]
cats=[]
for j, c in enumerate(mock_cat):
    cat = Category(name=c[0], description=c[1])
    cats.append(cat)

posts=[]
for i, t in enumerate(mock_post):
    post=Post(user_id=(i)%4+1, title=t[0], content=t[1], location_id=mock_location[i%3][0])
    posts.append(post)

for cat, post in zip(cats,posts):
    cat.posts=[post]
    post.category=[cat]
for cat in cats:
    db.session.add(cat)
for post in posts:
    db.session.add(post)

db.session.commit()