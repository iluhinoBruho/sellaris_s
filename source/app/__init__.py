from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_dropzone import Dropzone
import os

app = Flask(__name__)

app.config.from_object(Config)
db = SQLAlchemy(app)
dropzone = Dropzone(app)
migrate = Migrate(app, db, render_as_batch=True)

login = LoginManager(app)
login.login_view = 'login'


#for files uploading
path = os.getcwd()
UPLOAD_FOLDER = os.path.join(path, 'uploads')
#UPLOAD_FOLDER_OFFER = os.path.join(path, 'uploads')
if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 15
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']
app.config['DROPZONE_ALLOWED_FILE_TYPE'] = 'image'
app.config['DROPZONE_MAX_FILE_SIZE'] = 10
app.config['BOT_TEXT'] = "TODO"


from app import routes, models
from app.models import User, Offer


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Offer': Offer}