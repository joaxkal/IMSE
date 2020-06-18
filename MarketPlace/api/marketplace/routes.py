import os
from datetime import datetime, timedelta
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from marketplace import app, db, m_db, bcrypt, mail
from marketplace.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                               PostForm, RequestResetForm, ResetPasswordForm, SearchForm, AddComment)
from marketplace.models import User, Post, Location, Category, cat_association_table, Comment
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from sqlalchemy import func, sql, over
from sqlalchemy import or_, and_
import pymongo
from bson.objectid import ObjectId



record2dict = lambda r: {c.name: getattr(r, c.name) for c in r.__table__.columns}


def query2dict(query_result):
    # get query results (list of object) and turn them into list of dictionaires
    return [record2dict(record) for record in query_result]

@app.route("/home_mongo", methods=["GET"])
def home_mongo():
    form = SearchForm()
    posts = m_db.posts.find({}).sort('date_posted', pymongo.DESCENDING)
    posts = list(posts)
    for post in posts:
        post['id'] = post.pop('_id')
        post['category'] = [{'name': cat} for cat in post['categories']]
        post['author'] = m_db.users.find_one({'_id': post['user_id']})
    return render_template('home_mongo.html', posts=posts, form=form)
    # return render_template('test.html', q=res)


@app.route("/", methods=["GET"])
@app.route("/home", methods=["GET"])
def home():
    form = SearchForm()
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('home.html', posts=posts, form=form)


@app.route("/results", methods=["GET"])
def results():
    form = SearchForm()

    content = request.args.get('content')
    cat = request.args.get('category')
    loc = request.args.get('location')

    if cat is None:
        cat = 'None'
    if loc is None:
        loc = 'None'

    form.content.data = content
    form.category.data = Category.query.filter(
        (Category.id == cat) if 'None' not in cat else sql.false()).first()
    form.location.data = Location.query.filter(
        (Location.postal_code == loc) if 'None' not in loc else sql.false()).first()

    page = request.args.get('page', 1, type=int)

    q = db.session.query(Post).filter(or_(func.lower(Post.content).contains(func.lower(content)),
                                          func.lower(Post.title).contains(func.lower(content)))).filter(
        (Post.location_id == loc) if 'None' not in loc else sql.true()).join(cat_association_table).filter(
        (cat_association_table.c.category_id == cat) if 'None' not in cat else sql.true()).distinct().order_by(
        Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('search_results.html', posts=q, form=form, content=content, location=loc, category=cat,
                           page=page)


@app.route("/report")
# ELABORTE REPORTING
def about():
    # count offers per user per category
    q = db.session.query(func.count(Post.id).label('count'),
                         User.username.label('username'),
                         User.image_file.label('image_file'),
                         Category.name.label('cat_name'),
                         Location.city.label('city')).join(User, Post.user_id == User.id).join(
        cat_association_table).join(Category).join(Location, Post.location_id == Location.postal_code).group_by(
        User.username, User.image_file, Category.name, Location.city).filter_by(
        postal_code=current_user.location.postal_code).subquery()

    # get max number of posts in each category
    q2 = db.session.query(func.max(q.c.count).label('max_count'),
                          q.c.cat_name.label('cat_name'),
                          q.c.city.label('city')).group_by(q.c.cat_name, q.c.city).subquery()

    # final query - join users with max number of posts and select one user per each category
    report = db.session.query(q2.c.max_count.label('max_count'), q.c.username.label('username'),
                              q.c.image_file.label('image_file'),
                              q2.c.cat_name.label('cat_name'), q2.c.city.label('city')).join(q, and_(
        q.c.count == q2.c.max_count, q.c.cat_name == q2.c.cat_name, q.c.city == q2.c.city)).distinct(
        q2.c.cat_name).order_by(q2.c.cat_name.asc())

    return render_template('report.html', title='Get Report!', report=report.all())
    # return render_template('test.html', q=report)


@app.route("/report_mongo")
# ELABORTE REPORTING
def about_mongo():
    start_date = datetime.today() - timedelta(30)
    cu_location = str(current_user.location['postal_code'])
    m_db.posts.aggregate([
        {'$match': {"date_posted": {"$gte": start_date}, "location.postal_code": cu_location}},
        {'$unwind': "$categories"},
        {'$group': {'_id': {
            'user': '$user_id',
            'category': '$categories',

        },
            "count": {"$sum": 1}}},

        {'$group': {'_id': {
            'category': '$_id.category'
        },
            "user": {"$first": '$_id.user'},
            "count": {"$max": '$count'}}},
        {'$out': "results"}
    ])

    report = list(m_db.results.find({}))
    for result in report:
        result['city'] = current_user.location['city']
        for k, v in m_db.users.find_one({'_id': result['user']}).items():
            if k != '_id' and k != 'password':
                result[k] = v
        result['cat_name'] = result['_id']['category']
    return render_template('report.html', title='Get Report!', report=report)
    # return render_template('test.html', q=report)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, location=form.location.data,
                    password=hashed_password, phone=form.phone.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/register_mongo", methods=['GET', 'POST'])
def register_mongo():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        loc_dict = record2dict(form.location.data)
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = {'_id':str(ObjectId()),
                'username':form.username.data,
                'email':form.email.data,
                'location': {'city': loc_dict['city'], 'postal_code': str(loc_dict['postal_code'])},
                'password':hashed_password,
                'phone':form.phone.data,
                'role_id':1,
                'post_ids':[],
                'following':[],
                'image_file':'default.jpg'}
        m_db.users.insert_one(user)
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login_mongo'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


class UserDict(dict):
    def __getattr__(self, name):
        return self[name]
    def get_id(self):
        return self['_id']

@app.route("/login_mongo", methods=['GET', 'POST'])
def login_mongo():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = UserDict(m_db.users.find_one({'email':form.email.data}))
        if user and bcrypt.check_password_hash(user['password'], form.password.data):
            user['is_active']=True
            user['is_authenticated']=True
            user['is_anonymous']=False
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home_mongo'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        current_user.location = form.location.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.phone.data = current_user.phone
        form.location.data = current_user.location
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data,
                    location=form.location.data,
                    category=form.category.data,
                    author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@app.route("/post/new_mongo", methods=['GET', 'POST'])
@login_required
def new_post_mongo():
    form = PostForm()
    if form.validate_on_submit():
        loc_dict = record2dict(form.location.data)
        cat_dict = query2dict(form.category.data)
        post = {'_id': str(ObjectId()),
                'title': form.title.data,
                'content': form.content.data,
                'location': {'city': loc_dict['city'], 'postal_code': str(loc_dict['postal_code'])},
                'categories': [cat['name'] for cat in cat_dict],
                'user_id': str(current_user._id),
                'date_posted': datetime.now()}
        m_db.posts.insert_one(post)
        m_db.users.update_one({'_id': str(current_user._id)},
                              {'$push': {'post_ids': post['_id']}})
        flash('Your post has been created!', 'success')
        return redirect(url_for('home_mongo'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@app.route("/post/<post_id>", methods=['GET', 'POST'])
def post(post_id):
    form = AddComment()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data,
                          comment_author=current_user,
                          post_id=post_id
                          )
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been addeed!', 'success')
        return redirect(url_for('post', post_id=post_id))
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post, comments=post.comments, form=form)


@app.route("/post_mongo/<post_id>", methods=['GET', 'POST'])
def post_mongo(post_id):
    form = AddComment()
    if form.validate_on_submit():
        comment = {'_id': str(ObjectId()),
                   'content': form.content.data,
                   'date_posted': datetime.now(),
                   'user_id': str(current_user.id)}
        m_db.posts.update_one({'_id': post_id},
                              {'$push': {'comments': comment}})
        flash('Your comment has been addeed!', 'success')
        return redirect(url_for('post_mongo', post_id=post_id))

    post = m_db.posts.find_one({'_id': post_id})
    post['id'] = post.pop('_id')
    post['category'] = [{'name': cat} for cat in post['categories']]
    post['author'] = m_db.users.find_one({'_id': post['user_id']})
    if 'comments' in post.keys():
        comments = post['comments']
        for comment in comments:
            comment['comment_author'] = m_db.users.find_one({'_id': comment['user_id']})
    else:
        comments = []
    return render_template('post.html', post=post, comments=comments, form=form)
    # return render_template('test.html', q=[post])


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.location = form.location.data
        post.category = form.category.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.location.data = post.location
        form.category.data = post.category
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    for comment in post.comments:
        db.session.delete(comment)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/post/<int:post_id>/comment/<int:comment_id>/delete", methods=['POST'])
@login_required
def delete_comment(post_id, comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.comment_author != current_user:
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash('Your comment has been deleted!', 'success')
    return redirect(url_for('post', post_id=post_id))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user) \
        .order_by(Post.date_posted.desc()) \
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)
