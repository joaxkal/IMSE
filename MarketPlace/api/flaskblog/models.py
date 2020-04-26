from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flaskblog import db, login_manager, app
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


cat_association_table = db.Table('cat_association', db.Model.metadata,
    db.Column('post_id', db.Integer, db.ForeignKey('post.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'))
)


user_following = db.Table(
    'user_following', db.Model.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column('following_id', db.Integer, db.ForeignKey("user.id"), primary_key=True)
)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.postal_code'), nullable=True)
    phone = db.Column(db.String(13), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    following = db.relationship(
        'User', lambda: user_following,
        primaryjoin=lambda: User.id == user_following.c.user_id,
        secondaryjoin=lambda: User.id == user_following.c.following_id,
        backref='followers'
    )

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    users = db.relationship('User', backref='role', lazy=True)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.postal_code'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True)
    category = db.relationship(
        "Category",
        secondary=cat_association_table,
        back_populates="posts")

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.content}', '{self.date_posted}')"


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    posts = db.relationship(
        "Post",
        secondary=cat_association_table,
        back_populates="category")

    def  __str__ (self):
        return str(self.name) +' - ' + str(self.description)
    def __repr__(self):
        return f"Category('{self.name},{self.description}')"


class Location(db.Model):
    postal_code = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(30), nullable=False)
    state = db.Column(db.String(30), nullable=False)
    posts = db.relationship('Post', backref='location', lazy=True)
    users = db.relationship('User', backref='location', lazy=True)


    def __repr__(self):
        return f"Location('{self.postal_code},{self.city},{self.state}')"
