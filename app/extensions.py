# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Extensions globales
db = SQLAlchemy()
login_manager = LoginManager()