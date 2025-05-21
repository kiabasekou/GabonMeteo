from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.agent import AgentDGM, Direction, Service, Prelevement
from app.models.weather_data import WeatherStation, WeatherData
from app.models.user import User
from datetime import datetime
from sqlalchemy import func

# Définition du blueprint pour la gestion des agents par l'administrateur
admin_agent_bp = Blueprint('admin_agent', __name__, url_prefix='/admin/agent')

# Vérification du rôle administrateur
def check_admin():
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Accès non autorisé. Vous devez être administrateur pour accéder à cette page.', 'danger')
        return False
    return True

@admin_agent_bp.route('/')
@login_required
def index():
    """Liste des agents DGM"""
    if not check_admin():
        return redirect(url_for('main.index'))
    
    # Pagination des agents
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    agents_query = AgentDGM.query.order_by(AgentDGM.matricule)
    pagination = agents_query.paginate(page=page, per_page=per_page)
    
    return render_template('admin/agents/index.html', 
                          pagination=pagination,
                          agents=pagination.items)

@admin_agent_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_agent():
    """Ajouter un nouvel agent"""
    if not check_admin():
        return redirect(url_for('main.index'))
    
    # Récupérer les utilisateurs, services et stations pour le formulaire
    users = User.query.filter(~User.agent.has()).all()  # Utilisateurs sans agent associé
    services = Service.query.all()
    stations = WeatherStation.query.all()
    
    if request.method == 'POST':
        try:
            # Récupération des données du formulaire
            matricule = request.form.get('matricule')
            user_id = request.form.get('user_id', type=int)
            date_naissance_str = request.form.get('date_naissance')
            fonction = request.form.get('fonction')
            date_embauche_str = request.form.get('date_embauche')
            service_id = request.form.get('service_id', type=int)
            station_id = request.form.get('station_id', type=int)
            
            # Validation des champs obligatoires
            if not matricule or not user_id or not date_naissance_str or not fonction or not service_id:
                flash('Veuillez remplir tous les champs obligatoires.', 'danger')
                return redirect(url_for('admin_agent.add_agent'))
            
            # Vérifier si le matricule existe déjà
            if AgentDGM.query.filter_by(matricule=matricule).first():
                flash('Ce matricule est déjà utilisé.', 'danger')
                return redirect(url_for('admin_agent.add_agent'))
            
            # Conversion des dates
            try:
                date_naissance = datetime.strptime(date_naissance_str, '%Y-%m-%d').date()
                date_embauche = datetime.strptime(date_embauche_str, '%Y-%m-%d').date() if date_embauche_str else None
            except ValueError:
                flash('Format de date invalide.', 'danger')
                return redirect(url_for('admin_agent.add_agent'))
            
            # Création du nouvel agent
            new_agent = AgentDGM(
                matricule=matricule,
                user_id=user_id,
                date_naissance=date_naissance,
                fonction=fonction,
                date_embauche=date_embauche,
                service_id=service_id,
                station_id=station_id if station_id else None
            )
            
            db.session.add(new_agent)
            db.session.commit()
            
            flash('Agent ajouté avec succès!', 'success')
            return redirect(url_for('admin_agent.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Une erreur est survenue: {str(e)}', 'danger')
    
    return render_template('admin/agents/add.html', 
                          users=users,
                          services=services,
                          stations=stations)

@admin_agent_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_agent(id):
    """Modifier un agent existant"""
    if not check_admin():
        return redirect(url_for('main.index'))
    
    # Récupérer l'agent
    agent = AgentDGM.query.get_or_404(id)
    
    # Récupérer tous les utilisateurs et le service et la station actuels
    users = User.query.filter(db.or_(User.id == agent.user_id, ~User.agent.has())).all()
    services = Service.query.all()
    stations = WeatherStation.query.all()
    
    if request.method == 'POST':
        try:
            # Récupération des données du formulaire
            matricule = request.form.get('matricule')
            user_id = request.form.get('user_id', type=int)
            date_naissance_str = request.form.get('date_naissance')
            fonction = request.form.get('fonction')
            date_embauche_str = request.form.get('date_embauche')
            service_id = request.form.get('service_id', type=int)
            station_id = request.form.get('station_id', type=int)
            
            # Validation des champs obligatoires
            if not matricule or not user_id or not date_naissance_str or not fonction or not service_id:
                flash('Veuillez remplir tous les champs obligatoires.', 'danger')
                return redirect(url_for('admin_agent.edit_agent', id=id))
            
            # Vérifier si le matricule existe déjà (sauf pour cet agent)
            existing_agent = AgentDGM.query.filter(AgentDGM.matricule == matricule, AgentDGM.id != id).first()
            if existing_agent:
                flash('Ce matricule est déjà utilisé.', 'danger')
                return redirect(url_for('admin_agent.edit_agent', id=id))
            
            # Conversion des dates
            try:
                date_naissance = datetime.strptime(date_naissance_str, '%Y-%m-%d').date()
                date_embauche = datetime.strptime(date_embauche_str, '%Y-%m-%d').date() if date_embauche_str else None
            except ValueError:
                flash('Format de date invalide.', 'danger')
                return redirect(url_for('admin_agent.edit_agent', id=id))
            
            # Mise à jour de l'agent
            agent.matricule = matricule
            agent.user_id = user_id
            agent.date_naissance = date_naissance
            agent.fonction = fonction
            agent.date_embauche = date_embauche
            agent.service_id = service_id
            agent.station_id = station_id if station_id else None
            
            db.session.commit()
            
            flash('Agent mis à jour avec succès!', 'success')
            return redirect(url_for('admin_agent.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Une erreur est survenue: {str(e)}', 'danger')
    
    # Pour le formulaire GET, préparer les dates
    date_naissance_str = agent.date_naissance.strftime('%Y-%m-%d')
    date_embauche_str = agent.date_embauche.strftime('%Y-%m-%d') if agent.date_embauche else ''
    
    return render_template('admin/agents/edit.html', 
                          agent=agent,
                          users=users,
                          services=services,
                          stations=stations,
                          date_naissance_str=date_naissance_str,
                          date_embauche_str=date_embauche_str)

@admin_agent_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_agent(id):
    """Supprimer un agent"""
    if not check_admin():
        return redirect(url_for('main.index'))
    
    # Récupérer l'agent
    agent = AgentDGM.query.get_or_404(id)
    
    try:
        # Vérifier si l'agent a des prélèvements
        if Prelevement.query.filter_by(agent_id=id).count() > 0:
            flash('Impossible de supprimer cet agent car il a des prélèvements associés.', 'warning')
            return redirect(url_for('admin_agent.index'))
        
        db.session.delete(agent)
        db.session.commit()
        flash('Agent supprimé avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Une erreur est survenue: {str(e)}', 'danger')
    
    return redirect(url_for('admin_agent.index'))

# Gestion des directions et services
@admin_agent_bp.route('/directions')
@login_required
def directions():
    """Liste des directions"""
    if not check_admin():
        return redirect(url_for('main.index'))
    
    directions = Direction.query.all()
    services = Service.query.all()
    
    return render_template('admin/agents/directions.html', 
                          directions=directions,
                          services=services)

@admin_agent_bp.route('/direction/add', methods=['POST'])
@login_required
def add_direction():
    """Ajouter une nouvelle direction"""
    if not check_admin():
        return redirect(url_for('main.index'))
    
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    if not name:
        flash('Le nom de la direction est obligatoire.', 'danger')
        return redirect(url_for('admin_agent.directions'))
    
    try:
        new_direction = Direction(name=name, description=description)
        db.session.add(new_direction)
        db.session.commit()
        flash('Direction ajoutée avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Une erreur est survenue: {str(e)}', 'danger')
    
    return redirect(url_for('admin_agent.directions'))

@admin_agent_bp.route('/service/add', methods=['POST'])
@login_required
def add_service():
    """Ajouter un nouveau service"""
    if not check_admin():
        return redirect(url_for('main.index'))
    
    name = request.form.get('name')
    description = request.form.get('description', '')
    direction_id = request.form.get('direction_id', type=int)
    
    if not name or not direction_id:
        flash('Le nom du service et la direction sont obligatoires.', 'danger')
        return redirect(url_for('admin_agent.directions'))
    
    try:
        new_service = Service(name=name, description=description, direction_id=direction_id)
        db.session.add(new_service)
        db.session.commit()
        flash('Service ajouté avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Une erreur est survenue: {str(e)}', 'danger')
    
    return redirect(url_for('admin_agent.directions'))

# Gestion des prélèvements par l'administrateur
@admin_agent_bp.route('/prelevements')
@login_required
def prelevements():
    """Liste des prélèvements de tous les agents"""
    if not check_admin():
        return redirect(url_for('main.index'))
    
    # Filtres
    station_id = request.args.get('station_id', type=int)
    agent_id = request.args.get('agent_id', type=int)
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Requête de base
    query = Prelevement.query
    
    # Appliquer les filtres
    if station_id:
        query = query.filter_by(station_id=station_id)
    
    if agent_id:
        query = query.filter_by(agent_id=agent_id)
    
    if status:
        if status == 'validated':
            query = query.filter_by(validated=True)
        elif status == 'pending':
            query = query.filter_by(validated=False)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(func.date(Prelevement.date_prelevement) >= from_date)
        except ValueError:
            flash('Format de date invalide pour la date de début.', 'warning')
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(func.date(Prelevement.date_prelevement) <= to_date)
        except ValueError:
            flash('Format de date invalide pour la date de fin.', 'warning')
    
    # Trier par date de prélèvement (du plus récent au plus ancien)
    query = query.order_by(Prelevement.date_prelevement.desc())
    
    # Paginer les résultats
    pagination = query.paginate(page=page, per_page=per_page)
    
    # Récupérer les stations et agents pour les filtres
    stations = WeatherStation.query.all()
    agents = AgentDGM.query.all()
    
    # Calcul du nombre de prélèvements en attente pour les statistiques
    pending_count = Prelevement.query.filter_by(validated=False).count()
    
    return render_template('admin/agents/prelevements.html', 
                          pagination=pagination,
                          prelevements=pagination.items,
                          stations=stations,
                          agents=agents,
                          pending_count=pending_count,
                          current_filters={
                              'station_id': station_id,
                              'agent_id': agent_id,
                              'status': status,
                              'date_from': date_from,
                              'date_to': date_to
                          })

@admin_agent_bp.route('/prelevement/<int:id>')
@login_required
def view_prelevement(id):
    """Voir les détails d'un prélèvement"""
    if not check_admin():
        return redirect(url_for('main.index'))
    
    prelevement = Prelevement.query.get_or_404(id)
    
    # Calcul des moyennes récentes pour comparaison
    recent_data = WeatherData.query.filter_by(station_id=prelevement.station_id).order_by(WeatherData.timestamp.desc()).limit(10).all()
    
    avg_temperature = None
    avg_humidity = None
    avg_precipitation = None
    
    if recent_data:
        avg_temperature = sum(data.temperature for data in recent_data if data.temperature is not None) / len(recent_data)
        
        humidity_values = [data.humidity for data in recent_data if data.humidity is not None]
        if humidity_values:
            avg_humidity = sum(humidity_values) / len(humidity_values)
        
        precip_values = [data.precipitation for data in recent_data if data.precipitation is not None]
        if precip_values:
            avg_precipitation = sum(precip_values) / len(precip_values)
    
    return render_template('admin/agents/view_prelevement.html', 
                          prelevement=prelevement,
                          avg_temperature=avg_temperature,
                          avg_humidity=avg_humidity,
                          avg_precipitation=avg_precipitation)

@admin_agent_bp.route('/prelevement/<int:id>/validate', methods=['POST'])
@login_required
def validate_prelevement(id):
    """Valider un prélèvement et le convertir en donnée météo"""
    if not check_admin():
        return redirect(url_for('main.index'))
    
    prelevement = Prelevement.query.get_or_404(id)
    
    if prelevement.validated:
        flash('Ce prélèvement a déjà été validé.', 'warning')
        return redirect(url_for('admin_agent.prelevements'))
    
    try:
        # Marquer le prélèvement comme validé
        prelevement.validated = True
        
        # Créer une entrée dans WeatherData
        weather_data = prelevement.to_weather_data()
        db.session.add(weather_data)
        
        db.session.commit()
        flash('Prélèvement validé et converti en donnée météo avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Une erreur est survenue: {str(e)}', 'danger')
    
    return redirect(url_for('admin_agent.prelevements'))

@admin_agent_bp.route('/prelevement/<int:id>/reject', methods=['POST'])
@login_required
def reject_prelevement(id):
    """Rejeter un prélèvement"""
    if not check_admin():
        return redirect(url_for('main.index'))
    
    prelevement = Prelevement.query.get_or_404(id)
    
    # Ajouter une note de rejet
    note = request.form.get('reject_reason', '')
    
    if note:
        try:
            if prelevement.notes:
                prelevement.notes += f"\n\nREJET ({datetime.now().strftime('%d/%m/%Y')}): {note}"
            else:
                prelevement.notes = f"REJET ({datetime.now().strftime('%d/%m/%Y')}): {note}"
            
            db.session.commit()
            flash('Prélèvement rejeté avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Une erreur est survenue: {str(e)}', 'danger')
    else:
        flash('Veuillez fournir une raison de rejet.', 'warning')
    
    return redirect(url_for('admin_agent.prelevements'))