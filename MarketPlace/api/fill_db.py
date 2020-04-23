from flaskblog import db
from flaskblog.models import *

print(db)
db.drop_all()
db.create_all()


for i, l in enumerate(['Wien', 'Warszawa','Barcelona']):
    loc=Location(postal_code=1010+i,city=l, state='EU')
    db.session.add(loc)

for i, n in enumerate(['joaxkal', 'jotde']):
    user=User(username=n, password='test', email=n+'@test.com', image_file='default.jpg')
    db.session.add(user)

k=0
c=0
description = 'Lorem ipsum'

for j, c in enumerate(['kitchen', 'animal', 'books', 'cars']):
    cat = Category(name=c, description=description)
    for i, t in enumerate(['Temat_2', 'Temat1']):
        post=Post(user_id=i+1, title=t, content='Lorem ipsum', location_id=1010)
        k=k+1
        cat.posts=[post]
        post.category=[cat]
        db.session.add(post)
    db.session.add(cat)

db.session.commit()