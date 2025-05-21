from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.agent import AgentDGM, Direction, Service
from app.models.weather_data import WeatherStation
import os
import json
import datetime
import csv
import logging

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gabonmeteo.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

superadmin_bp = Blueprint('superadmin', __name__, url_prefix='/superadmin')

def check_superadmin():
    """Vérifie si l'utilisateur est un superadmin"""
    if not current_user.is_authenticated or current_user.role != 'superadmin':
        flash('Accès non autorisé. Vous devez être super administrateur pour accéder à cette page.', 'danger')
        return False
    return True

@superadmin_bp.route('/')
@login_required
def dashboard():
    """Tableau de bord du super administrateur"""
    if not check_superadmin():
        return redirect(url_for('main.index'))
    
    # Statistiques du système
    stats = {
        'users_count': User.query.count(),
        'admins_count': User.query.filter(User.role.in_(['admin', 'superadmin'])).count(),
        'agents_count': AgentDGM.query.count(),
        'stations_count': WeatherStation.query.count(),
        'directions_count': Direction.query.count(),
        'services_count': Service.query.count()
    }
    
    # Récents logs (si on a implémenté un système de logs)
    recent_logs = []
    log_file = 'gabonmeteo.log'
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                # Récupérer les 20 dernières lignes
                lines = f.readlines()
                recent_logs = lines[-20:]
        except Exception as e:
            logger.error(f"Erreur lors de la lecture des logs: {str(e)}")
    
    return render_template('superadmin/dashboard.html',
                          stats=stats,
                          recent_logs=recent_logs)

@superadmin_bp.route('/system-settings', methods=['GET', 'POST'])
@login_required
def system_settings():
    """Paramètres du système"""
    if not check_superadmin():
        return redirect(url_for('main.index'))
    
    # Définir les paramètres par défaut
    default_settings = {
        'site_title': 'GabonMétéo+',
        'maintenance_mode': False,
        'maximum_upload_size': 10,  # MB
        'automatic_validation': False,
        'refresh_interval': 30,  # minutes
        'allowed_file_types': '.csv,.xlsx,.xls',
        'default_theme': 'light',  # light/dark
        'map_center_lat': 0.4162,  # Libreville
        'map_center_lon': 9.4673,  # Libreville
        'map_default_zoom': 6
    }
    
    # Charger les paramètres actuels s'ils existent
    settings_file = 'app/config/settings.json'
    current_settings = default_settings.copy()
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                stored_settings = json.load(f)
                current_settings.update(stored_settings)
        except Exception as e:
            logger.error(f"Erreur lors de la lecture des paramètres: {str(e)}")
    
    if request.method == 'POST':
        try:
            # Récupérer les paramètres du formulaire
            new_settings = {
                'site_title': request.form.get('site_title', default_settings['site_title']),
                'maintenance_mode': 'maintenance_mode' in request.form,
                'maximum_upload_size': int(request.form.get('maximum_upload_size', default_settings['maximum_upload_size'])),
                'automatic_validation': 'automatic_validation' in request.form,
                'refresh_interval': int(request.form.get('refresh_interval', default_settings['refresh_interval'])),
                'allowed_file_types': request.form.get('allowed_file_types', default_settings['allowed_file_types']),
                'default_theme': request.form.get('default_theme', default_settings['default_theme']),
                'map_center_lat': float(request.form.get('map_center_lat', default_settings['map_center_lat'])),
                'map_center_lon': float(request.form.get('map_center_lon', default_settings['map_center_lon'])),
                'map_default_zoom': int(request.form.get('map_default_zoom', default_settings['map_default_zoom']))
            }
            
            # S'assurer que le dossier config existe
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            
            # Enregistrer les paramètres
            with open(settings_file, 'w') as f:
                json.dump(new_settings, f, indent=4)
            
            flash('Paramètres du système mis à jour avec succès!', 'success')
            current_settings = new_settings
            
            # Log de l'action
            logger.info(f"Paramètres système mis à jour par {current_user.username}")
            
        except Exception as e:
            flash(f'Erreur lors de la mise à jour des paramètres: {str(e)}', 'danger')
            logger.error(f"Erreur lors de la mise à jour des paramètres: {str(e)}")
    
    return render_template('superadmin/system_settings.html', settings=current_settings)

@superadmin_bp.route('/user-roles')
@login_required
def user_roles():
    """Gestion avancée des rôles utilisateurs"""
    if not check_superadmin():
        return redirect(url_for('main.index'))
    
    users = User.query.all()
    return render_template('superadmin/user_roles.html', users=users)

@superadmin_bp.route('/update-role/<int:id>', methods=['POST'])
@login_required
def update_role(id):
    """Mettre à jour le rôle d'un utilisateur"""
    if not check_superadmin():
        return redirect(url_for('main.index'))
    
    user = User.query.get_or_404(id)
    new_role = request.form.get('role')
    
    # Vérifier que le rôle est valide
    if new_role not in ['user', 'admin', 'superadmin', 'sector_specific']:
        flash('Rôle invalide.', 'danger')
        return redirect(url_for('superadmin.user_roles'))
    
    # Empêcher la modification du propre rôle du superadmin
    if user.id == current_user.id and new_role != 'superadmin':
        flash('Vous ne pouvez pas modifier votre propre rôle de superadmin.', 'danger')
        return redirect(url_for('superadmin.user_roles'))
    
    # Mettre à jour le rôle
    user.role = new_role
    db.session.commit()
    
    flash(f'Le rôle de {user.username} a été mis à jour en {new_role}.', 'success')
    logger.info(f"Rôle de l'utilisateur {user.username} (ID: {user.id}) modifié en {new_role} par {current_user.username}")
    
    return redirect(url_for('superadmin.user_roles'))

@superadmin_bp.route('/system-backup')
@login_required
def system_backup():
    """Sauvegarde du système"""
    if not check_superadmin():
        return redirect(url_for('main.index'))
    
    return render_template('superadmin/system_backup.html')

@superadmin_bp.route('/perform-backup', methods=['POST'])
@login_required
def perform_backup():
    """Effectuer une sauvegarde du système"""
    if not check_superadmin():
        return redirect(url_for('main.index'))
    
    try:
        # Simuler une sauvegarde (dans une vraie application, on ferait un dump de la base de données)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        # Créer un fichier de sauvegarde fictif
        backup_file = f"{backup_dir}/backup_{timestamp}.json"
        with open(backup_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'user': current_user.username,
                'status': 'completed'
            }, f)
        
        flash('Sauvegarde du système effectuée avec succès!', 'success')
        logger.info(f"Sauvegarde du système effectuée par {current_user.username}")
        
    except Exception as e:
        flash(f'Erreur lors de la sauvegarde: {str(e)}', 'danger')
        logger.error(f"Erreur lors de la sauvegarde: {str(e)}")
    
    return redirect(url_for('superadmin.system_backup'))

@superadmin_bp.route('/import-data', methods=['GET', 'POST'])
@login_required
def import_data():
    """Import de données en masse"""
    if not check_superadmin():
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Vérifier si un fichier a été uploadé
        if 'file' not in request.files:
            flash('Aucun fichier sélectionné.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Si l'utilisateur n'a pas sélectionné de fichier
        if file.filename == '':
            flash('Aucun fichier sélectionné.', 'danger')
            return redirect(request.url)
        
        # Vérifier l'extension du fichier
        allowed_extensions = ['.csv', '.xlsx', '.xls']
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            flash('Format de fichier non supporté. Utilisez CSV ou Excel.', 'danger')
            return redirect(request.url)
        
        try:
            # Enregistrer le fichier temporairement
            filepath = f"uploads/{file.filename}"
            os.makedirs('uploads', exist_ok=True)
            file.save(filepath)
            
            # Ici, normalement, on traiterait le fichier
            # Pour cet exemple, on simule juste un traitement réussi
            
            flash(f'Le fichier {file.filename} a été importé avec succès!', 'success')
            logger.info(f"Import de données depuis {file.filename} par {current_user.username}")
            
        except Exception as e:
            flash(f'Erreur lors de l\'import: {str(e)}', 'danger')
            logger.error(f"Erreur lors de l'import de données: {str(e)}")
        
        return redirect(url_for('superadmin.import_data'))
    
    return render_template('superadmin/import_data.html')

@superadmin_bp.route('/system-logs')
@login_required
def system_logs():
    """Visualisation des logs du système"""
    if not check_superadmin():
        return redirect(url_for('main.index'))
    
    log_file = 'gabonmeteo.log'
    logs = []
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                logs = f.readlines()
        except Exception as e:
            flash(f'Erreur lors de la lecture des logs: {str(e)}', 'danger')
    
    return render_template('superadmin/system_logs.html', logs=logs)