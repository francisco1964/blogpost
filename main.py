from functools import wraps
from typing import List
from flask import Flask,g,abort, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
from sqlalchemy.orm import lazyload
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor, CKEditorField
from datetime import date
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

from forms import CreatePostForm, RegisterUserForm, LogginForm, ComentPostForm
import os

## Delete this code:
# import requests
# posts = requests.get("https://api.npoint.io/43644ec4f0013682fc0d").json()

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

file_path = os.path.abspath(os.getcwd())+"/posts.db"
login_manager = LoginManager()


login_manager.init_app(app)
##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+ file_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CREATE TABLE IN DB
class User(UserMixin, db.Model):
    # id = db.Column(db.Integer, primary_key=True)
    id =  mapped_column(Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

##CONFIGURE TABLE
class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id =db.Column(db.Integer, db.ForeignKey("user.id"))
    author = relationship("User", back_populates="posts", lazy="joined")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post", lazy="joined")

class Comment(db.Model):
    id =  mapped_column(Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_id = mapped_column(ForeignKey("user.id"))
    blog_id = mapped_column(ForeignKey("blog_post.id"))
    comment_author = relationship("User", back_populates="comments", lazy="joined")
    parent_post = relationship("BlogPost", back_populates="comments")
    

    
    def to_dict(self):
        return {
            'id' : self.id, 'title' : self.title, 'subtitle' : self.subtitle,
            'date' : self.date, 'body' : self.body, 'author': self.author,
            'img_url' : self.img_url
        }
#Line below only required once, when creating DB. 
# with app.app_context():
#     db.create_all()

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

@login_manager.user_loader
def load_user(user_id):
    with app.app_context():
        user = db.session.query(User).filter(User.id == user_id).first()
    return user


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
               abort(403)
        return f(*args, **kwargs)
    return decorated_function




@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()

    return render_template("index.html", all_posts=posts,logged_in=current_user.is_authenticated)

@app.route("/post/<int:index>", methods=["GET", "POST"] )
def show_post(index):
    form = ComentPostForm()
    # requested_post = BlogPost.query.get(index)
    with app.app_context():
        requested_post = db.session.query(BlogPost).\
            filter(BlogPost.id == index).\
            first()

    # return "Hola" + requested_post.author.name
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
        with app.app_context():
            new_comment = Comment(
                text=form.comment.data,
                comment_author=current_user,
                parent_post=requested_post
            )
            local_comment = db.session.merge(new_comment)
            db.session.add(local_comment)
            db.session.commit()

    return render_template("post.html", post=requested_post, form=form, current_user=current_user)
   

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    # with app.app_context():
    #     el_autor = db.session.query(User).filter_by(id=current_user.id).first()
    

    if form.validate_on_submit():
        new_blog_post = BlogPost(
        title=request.form.get("title"),
        subtitle=request.form.get("subtitle"),
        date=date.today().strftime("%B %-d, %Y"),
        body=request.form.get("body"),
        img_url=request.form.get("img_url"),
        author_id = current_user.id,
        author = current_user
    )
        with app.app_context():
            db.session.add(new_blog_post)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
    
    return render_template("make-post.html", form=form,edit=False,logged_in=current_user.is_authenticated)

@app.route("/edit-post/<post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    with app.app_context():
  
        blog_spot : BlogPost = db.session.query(BlogPost).filter(BlogPost.id == post_id).first()
        # form.title = blog_spot.title 
        # form.subtitle = blog_spot.subtitle
        # form.body = blog_spot.body
        # form.author = blog_spot.author
        # form.img_url = blog_spot.img_url
        form = CreatePostForm(obj=blog_spot)

    if form.validate_on_submit():
        with app.app_context():
            blog_spot : BlogPost = db.session.query(BlogPost).filter(BlogPost.id == post_id).first()

            blog_spot.title=request.form.get("title")
            blog_spot.subtitle=request.form.get("subtitle")
            # blog_spot.date= date.today().strftime("%B %-d, %Y")
            blog_spot.body=request.form.get("body")
            blog_spot.author=request.form.get("author")
            blog_spot.img_url=request.form.get("img_url")
    
            db.session.query(BlogPost).filter(BlogPost.id == blog_spot.id).update(blog_spot.to_dict())
            db.session.commit()
        return redirect(url_for("get_all_posts"))
    
    return render_template("make-post.html", form=form,edit=True,logged_in=current_user.is_authenticated)
@app.route('/delete/<post_id>')
@admin_only
def delete_post(post_id):
        with app.app_context():
            db.session.query(BlogPost).filter(BlogPost.id == post_id).delete()
            db.session.commit()
            return redirect(url_for("get_all_posts"))

@app.route('/register', methods=["GET","POST"])
def register():
    form = RegisterUserForm()
    

    error = None  
    if form.validate_on_submit():
        # print(request.form.get("name"))
        hashed_password = generate_password_hash(request.form.get("password"),
                                               method="pbkdf2:sha256",salt_length=8 )
        new_user = User(
            name= request.form.get("name"),
            email= request.form.get("email"),
            password= hashed_password
            )
        with app.app_context():
            user_already_exist = db.session.query(User).filter(User.email == request.form.get("email")).first()
            if user_already_exist != None:
                flash("You've already signed up with that email, log in instead!")
                return redirect(url_for('home'))
            else:
                db.session.add(new_user)
                db.session.commit()
                return redirect(url_for("get_all_posts"))
                # return render_template("post.html")
                # return render_template("post.html",nombre=current_user.name,logged_in=current_user.is_authenticated)
    # return render_template("register.html",logged_in=current_user.is_authenticated)
    return render_template("register.html",form=form)

@app.route('/login',methods=["GET", "POST"])
def login():
    form = LogginForm()
    error = None
    if form.validate_on_submit():
        with app.app_context():
            user = db.session.query(User).filter(User.email == request.form.get("email")).first()
            if user == None:
                flash("Password or email incorrect, please try again.")
            else:
                if check_password_hash(user.password,request.form.get("password")):
                    login_user(user)
                    return redirect(url_for("get_all_posts"))
                else:
                    flash("Password or emain incorrect, please try again.")
    print("error")
    return render_template("login.html", form = form,error = error)




@app.route('/logout')
@login_required
def logout():
    logout_user()
    # if session.get('was_once_logged_in'):
    #     # prevent flashing automatically logged out message
    #     del session['was_once_logged_in']
    # flash('You have successfully logged yourself out.')
    return redirect(url_for('login'))




if __name__ == "__main__":
    # app.run(debug=True,port=5001)
    app.run(host="0.0.0.0",port=5000)