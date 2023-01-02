import werkzeug.exceptions
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import Unauthorized
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from sqlalchemy import ForeignKey

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

# GRAVATAR
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    use_ssl=False,
                    base_url=None
                    )

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


# with app.app_context():
#     db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.errorhandler(werkzeug.exceptions.Unauthorized)
def handle_not_authorized(e):
    return 'not authorized!', 403


# ADMIM DECORATOR
def admin_only(function):
    def wrapper():
        func = function()
        if current_user.id == 1:
            return func
        else:
            return abort(403)

    wrapper.__name__ = function.__name__
    return wrapper


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html",
                           all_posts=posts,
                           logged_in=current_user.is_authenticated,
                           user=current_user)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first() is not None:
            return redirect(url_for("login", registered=True))
        else:
            new_user = User(password=generate_password_hash(password=form.password.data,
                                                            method="pbkdf2:sha256",
                                                            salt_length=8),
                            name=form.name.data,
                            email=form.email.data,
                            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            print(f"TEST: User {new_user.name} registered and logged in")
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if request.args.get("registered"):
        print("TEST: Already registered")
        flash("Already registered, please login with your existing email")
    if request.args.get("needs_login"):
        print("TEST: Not logged in ")
        flash("You need to login for posting comments.")
    if form.validate_on_submit():
        login_email = form.email.data
        login_password = form.password.data

        user_to_log = User.query.filter_by(email=login_email).first()

        if user_to_log is not None:
            if check_password_hash(user_to_log.password, login_password):
                login_user(user_to_log)
                print(f"TEST: User {user_to_log.name} logged in")
                return redirect(url_for("get_all_posts"))
            else:
                flash("Invalid password")
        else:
            flash("Invalid user")

    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text=form.body.data,
                comment_author=current_user,
                parent_post=requested_post,
            )
            db.session.add(new_comment)
            db.session.commit()
        else:
            return redirect(url_for("login", needs_login=True))
    return render_template("post.html",
                           post=requested_post,
                           form=form,
                           user=current_user,
                           logged_in=current_user.is_authenticated)


@app.route("/about")
def about():
    return render_template("about.html",
                           logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html",
                           logged_in=current_user.is_authenticated)


@app.route("/new-post", methods=["POST", "GET"])
@login_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html",
                           form=form,
                           logged_in=current_user.is_authenticated)


@app.route("/edit-post", methods=["POST", "GET"])
@admin_only
def edit_post():
    post_id = request.args.get("post_id")
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        print("TEST Post edited")
        return redirect(url_for("show_post", post_id=post_id))

    return render_template("make-post.html",
                           form=edit_form,
                           logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
