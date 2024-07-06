import os
import random
import io
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, redirect, request, Response, send_file
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, LargeBinary
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
from datetime import datetime

email = ""
password = ""
name = ""
file_too_large = False
invalid_extension = False
password_incorrect = False
user_not_exist = False
user_already_exist = False
invalid_otp = False
user_login = False
user_registered = False
no_file = False
app = Flask(__name__)
my_email = "pythonersurya@gmail.com"
my_password = "zpgp gdtv bdvg nkgi"
year = datetime.now().year
os.environ["FLASK_KEY"] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")

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
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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


class Img(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    img = db.Column(db.Text, unique=True, nullable=False)
    name = db.Column(db.Text, nullable=False)
    mimetype = db.Column(db.Text, nullable=False)
    subject = db.Column(db.Text, nullable=False)
    date = db.Column(db.Text, nullable=False)
    image_data = db.Column(LargeBinary)


with app.app_context():
    db.create_all()


@app.route("/register", methods=["POST", "GET"])
def hipage():
    global user_already_exist
    if request.method == "POST":
        global email
        email = request.form["email"]
        global password
        password = request.form["password"]
        global name
        name = request.form["name"]
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user:
            user_already_exist = True
            return
        with smtplib.SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()
            connection.login(my_email, my_password)
            connection.sendmail(my_email, email, message.as_string())
        return redirect("/create-account")
    return render_template("register.html", current_user=current_user,user_exists=user_already_exist)


@app.route("/create-account", methods=["POST", "GET"])
def create_user():
    global invalid_otp
    global user_registered

    if request.method == "POST":

        entered_otp = request.form["otp"]
        if int(six_digit_string) == int(entered_otp):
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
            user_registered = True

            login_user(new_user)


            return redirect("/")
        if int(six_digit_string) != int(entered_otp):
            invalid_otp = True
            return

    return render_template("otp.html", current_user=current_user,invalid_otp=invalid_otp)


@app.route('/login', methods=["GET", "POST"])
def login():
    global password_incorrect, user_not_exist
    global user_login
    if request.method == "POST":
        password = request.form["password"]
        email = request.form["email"]
        result = db.session.execute(db.select(User).where(User.email == email))

        user = result.scalar()

        if not user:
            user_not_exist = True

        elif not check_password_hash(user.password, password):
            password_incorrect = True
        else:
            login_user(user)
            user_login = True
            return redirect("/")

    return render_template("login.html", password_incorrect=password_incorrect, no_user=user_not_exist)


@login_required
@app.route('/logout')
def logout():
    logout_user()
    return redirect("/")


@app.route("/")
def homepage():
    images = Img.query.all()
    unique_dates = []
    for image in images:
        unique_dates.append(image.date)

    return render_template("index.html", current_year=year, images=images, date_options=unique_dates, user_login=user_login, user_registered=user_registered)


@app.route('/upload', methods=["GET", "POST"])
def upload_file():
    global file_too_large
    global invalid_extension
    global no_file
    if request.method == 'POST':
        try:
            # Access uploaded file
            file = request.files['file']
            subject = request.form["subject"]
            date = request.form["date"]

            extension = os.path.splitext(file.filename)[1]
            if file:

                if extension not in app.config["ALLOWED_EXTENSIONS"]:
                    invalid_extension = True

                mimetype = file.mimetype

                img = Img(
                    img=file.read(),
                    name=file.filename,
                    mimetype=mimetype,
                    subject=subject,
                    date=date,
                    image_data=file.read()
                )
                db.session.add(img)
                db.session.commit()

                return redirect("/")
            else:
                no_file = True
        except RequestEntityTooLarge:
            file_too_large = True

    return render_template('upload.html', file_too_large=file_too_large, invalid_extension=invalid_extension, no_file=no_file)


@app.route("/serve-image/<int:id>", methods=["GET"])
def serve_image(id):
    img = Img.query.filter_by(id=id).first()
    return Response(img.img, mimetype=img.mimetype)
@app.route('/download/<int:id>')
def download_image(id):
    image = Img.query.filter_by(id=id).first()
    return send_file(
        io.BytesIO(image.image_data),
        download_name=image.name,
        as_attachment=True
    )


if __name__ == "__main__":
    app.run()
