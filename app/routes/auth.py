from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        # Vérifier si l'utilisateur existe et si le mot de passe est correct
        if not user or not user.check_password(password):
            flash('Vérifiez votre email et mot de passe et réessayez.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Si tout est bon, connecter l'utilisateur
        login_user(user, remember=remember)
        
        # Rediriger vers la page demandée ou la page d'accueil
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        else:
            # Rediriger vers le tableau de bord si c'est un administrateur
            if user.role == 'admin':
                return redirect(url_for('main.dashboard'))
            else:
                return redirect(url_for('main.index'))
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        # Vérifier si les mots de passe correspondent
        if password != password_confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Vérifier si l'email est déjà utilisé
        user_email = User.query.filter_by(email=email).first()
        if user_email:
            flash('Cet email est déjà utilisé.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Vérifier si le nom d'utilisateur est déjà utilisé
        user_name = User.query.filter_by(username=username).first()
        if user_name:
            flash('Ce nom d\'utilisateur est déjà utilisé.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Créer un nouvel utilisateur
        new_user = User(email=email, username=username)
        new_user.set_password(password)
        
        # Le premier utilisateur est automatiquement un administrateur
        if User.query.count() == 0:
            new_user.role = 'admin'
        
        # Ajouter l'utilisateur à la base de données
        db.session.add(new_user)
        db.session.commit()
        
        flash('Inscription réussie! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('main.index'))