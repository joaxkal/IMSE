from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, \
    SelectMultipleField, widgets
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flaskblog.models import User, Category, Location
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField


class MultiCheckboxField(QuerySelectMultipleField):
    widget = widgets.ListWidget(html_tag='ul', prefix_label=False)
    option_widget = widgets.CheckboxInput()

def loc_choices():
    return Location.query.order_by(Location.city)

def cat_choices():
    return Category.query.order_by(Category.name)

def get_pk(obj):
    return str(obj)

class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])

    phone = StringField('Phone', validators=[DataRequired()])

    location = QuerySelectField('Location', query_factory=loc_choices, validators=[DataRequired()], get_pk=get_pk, get_label='city')

    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

    def validate_phone(form, phone):
        if len(phone.data) > 16 or len(phone.data)<7:
            raise ValidationError('Invalid phone number.')
        try:
            if phone.data[0] != '+':
                int(phone.data[0])
            for n in phone.data[1:]:
                int(n)
        except:
            raise ValidationError('Invalid phone number.')



class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])

    phone = StringField('Phone', validators=[DataRequired()])

    location = QuerySelectField('Location', query_factory=loc_choices, validators=[DataRequired()], get_pk=get_pk, get_label='city')

    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])

    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')

    def validate_phone(form, phone):
        if len(phone.data) > 16 or len(phone.data)<7:
            raise ValidationError('Invalid phone number.')
        try:
            if phone.data[0] != '+':
                int(phone.data[0])
            for n in phone.data[1:]:
                int(n)
        except:
            raise ValidationError('Invalid phone number.')




class PostForm(FlaskForm):

    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    location = QuerySelectField('Location', query_factory=loc_choices, validators=[DataRequired()], get_pk=get_pk, get_label='city')
    category = MultiCheckboxField('Category', query_factory=cat_choices, validators=[DataRequired()], get_pk=get_pk)
    submit = SubmitField('Post')

class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. You must register first.')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class SearchForm(FlaskForm):
    content= StringField('Content')
    location = QuerySelectField('Location', query_factory=loc_choices, get_pk=lambda x: x.postal_code, get_label='city',allow_blank=True)
    category = QuerySelectField('Category', query_factory=cat_choices, get_pk=lambda x: x.id, allow_blank=True)
    submit = SubmitField('Search!')


class AddComment(FlaskForm):
    content= TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Add!')