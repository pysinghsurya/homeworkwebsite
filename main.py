import os

from os import path
import random
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, redirect, request, send_from_directory, send_file
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from datetime import datetime

email = ""
password = ""
name = ""

app = Flask(__name__)
my_email = "suryapartapsinghdev@gmail.com"
my_password = "cbxv joli gtzg rudj"
year = datetime.now().year
os.environ["FLASK_KEY"] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["ALLOWED_EXTENSIONS"] = [".jpg", ".jpeg", ".docx"]

login_manager = LoginManager()
login_manager.init_app(app)

random_number = random.randrange(1, 1000000)

six_digit_string = f"{random_number:06d}"


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


class Base(DeclarativeBase):
    pass


os.environ["DB_URL"] = 'sqlite:///posts.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URL")
db = SQLAlchemy(model_class=Base)
db.init_app(app)

message = MIMEText(f"This is the OTP for your account creation {six_digit_string}", "plain")
message["Subject"] = "Verify Email"
message["From"] = my_email
message["To"] = email


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))


with app.app_context():
    db.create_all()


@app.route("/register", methods=["POST", "GET"])
def hipage():
    if request.method == "POST":
        global email
        email = request.form["email"]
        global password
        password = request.form["password"]
        global name
        name = request.form["name"]
        with smtplib.SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()
            connection.login(my_email, my_password)
            connection.sendmail(my_email, email, message.as_string())
        return redirect("/create-account")
    return render_template("register.html", current_user=current_user)


@app.route("/create-account", methods=["POST", "GET"])
def create_user():
    if request.method == "POST":

        entered_otp = request.form["otp"]
        if int(six_digit_string) == int(entered_otp):
            result = db.session.execute(db.select(User).where(User.email == email))
            user = result.scalar()
            if user:
                return redirect("/login")

            hash_and_salted_password = generate_password_hash(
                password,
                method='pbkdf2:sha256',
                salt_length=8
            )
            new_user = User(
                email=email,
                name=name,
                password=hash_and_salted_password)

            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)

            return redirect("/")

    return render_template("otp.html", current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form["password"]
        email = request.form["email"]
        result = db.session.execute(db.select(User).where(User.email == email))
        # Note, email in db is unique so will only have one result.
        user = result.scalar()
        # Email doesn't exist
        if not user:
            return redirect("/user-doesn't-exist")
        # Password incorrect
        elif not check_password_hash(user.password, password):
            return redirect("/password-incorrect")
        else:
            login_user(user)
            return redirect("/")

    return render_template("login.html")


@login_required
@app.route('/logout')
def logout():
    logout_user()
    return redirect("/")



@app.route("/")
def homepage():
    files = os.listdir(app.config["UPLOAD_FOLDER"])
    images = []
    unique_dates = set()  # Track unique upload dates for dropdown

    files.sort(key=lambda f: path.getmtime(path.join(app.config["UPLOAD_FOLDER"], f)), reverse=True)
    for file in files:
        extension = os.path.splitext(file)[1].lower()
        if extension in app.config["ALLOWED_EXTENSIONS"]:
            ti_m = os.path.getmtime(f'{app.config["UPLOAD_FOLDER"]}/{file}')
            upload_date = datetime.fromtimestamp(ti_m).strftime('%d-%m-%Y')  # Format date for display
            unique_dates.add(upload_date)  # Add unique date to set
        
            images.append({'filename': f"{file}", 'date': upload_date})

   
    date_options = sorted(list(unique_dates))

    return render_template("index.html", current_year=year, images=images, date_options=date_options)


@app.route('/upload', methods=["GET", "POST"])
def upload_file():
    if request.method == 'POST':
        try:
            # Access uploaded file
            file = request.files['file']


            extension = os.path.splitext(file.filename)[1]
            if file:

                if extension not in app.config["ALLOWED_EXTENSIONS"]:
                    return redirect("/file-extension-unsupported")
                file.save(os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    secure_filename(file.filename)

                ))



                return redirect("/")
            return redirect("/")
        except RequestEntityTooLarge:
            return redirect("/file-is-too-large")

    return render_template('upload.html')


@app.route("/file-is-too-large")
def file_size_too_large():
    return render_template("file-is-too-large.html")


@app.route("/serve-image/<filename>", methods=["GET"])
def serve_image(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/download-image/<filename>")
def download_image(filename):
    return send_file(path.join(app.config["UPLOAD_FOLDER"], filename), as_attachment=True)

@app.route("/file-extension-unsupported")
def extension_unsupported():
    return render_template("file-extension-unsupported.html")

@app.route("/password-incorrect")
def password_incorrect():
    return render_template("password-incorrect.html")

@app.route("/user-doesn't-exist")
def no_user():
    return render_template("no-user.html")

if __name__ == "__main__":
    app.run()
