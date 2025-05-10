from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialisation des extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    # Création de l'application Flask
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'votre_clé_secrète_provisoire'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gabonmeteo.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialisation des extensions avec l'application
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Import des modèles (après initialisation de db)
    from app.models import user, weather_data
    
    # Import et enregistrement des blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    
    # Création des tables de la base de données
    with app.app_context():
        db.create_all()
        
        # Création d'un utilisateur administrateur par défaut si aucun n'existe
        if not user.User.query.filter_by(role='admin').first():
            admin = user.User(username='admin', email='admin@gabonmeteo.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    
    return app