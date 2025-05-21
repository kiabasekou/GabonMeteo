from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    # Rôles: 'user', 'admin', 'superadmin', 'sector_specific'
    role = db.Column(db.String(20), default='user')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        return self.role in ['admin', 'superadmin']
    
    @property
    def is_superadmin(self):
        return self.role == 'superadmin'
    
    def can_access(self, feature):
        """Vérifie si l'utilisateur a accès à une fonctionnalité spécifique
        
        Les fonctionnalités peuvent être:
        - 'user_management': Gestion des utilisateurs (admin et superadmin)
        - 'agent_management': Gestion des agents (admin et superadmin)
        - 'system_config': Configuration du système (superadmin uniquement)
        - 'data_import': Import de données en masse (superadmin uniquement)
        - 'logs': Accès aux journaux du système (superadmin uniquement)
        """
        if self.is_superadmin:
            return True  # Le superadmin a accès à tout
            
        if self.role == 'admin':
            # Les admins ont accès à certaines fonctionnalités
            return feature in ['user_management', 'agent_management']
            
        return False  # Les utilisateurs standards n'ont pas accès aux fonctionnalités admin

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))