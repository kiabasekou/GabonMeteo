from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.agent import AgentDGM, Direction, Service, Prelevement
from app.models.weather_data import WeatherStation, WeatherData
from app.models.user import User
from datetime import datetime
from sqlalchemy import func

# Définition du blueprint pour les fonctionnalités des agents
agent_bp = Blueprint('agent', __name__, url_prefix='/agent')

@agent_bp.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord de l'agent connecté"""
    # Vérifier si l'utilisateur est un agent
    agent = AgentDGM.query.filter_by(user_id=current_user.id).first()
    
    if not agent:
        flash("Vous n'êtes pas enregistré comme agent de la DGM.", 'warning')
        return redirect(url_for('main.index'))
    
    # Récupérer les prélèvements récents de l'agent
    recent_prelevements = Prelevement.query.filter_by(agent_id=agent.id).order_by(
        Prelevement.timestamp.desc()).limit(10).all()
    
    # Statistiques des prélèvements
    total_prelevements = Prelevement.query.filter_by(agent_id=agent.id).count()
    validated_prelevements = Prelevement.query.filter_by(agent_id=agent.id, validated=True).count()
    pending_prelevements = total_prelevements - validated_prelevements
    
    # Si l'agent est affecté à une station, récupérer ses données
    station_data = None
    if agent.station_id:
        station = WeatherStation.query.get(agent.station_id)
        latest_data = WeatherData.query.filter_by(station_id=agent.station_id).order_by(
            WeatherData.timestamp.desc()).first()
        station_data = {
            'station': station,
            'latest_data': latest_data
        }
    
    return render_template('agent/dashboard.html', 
                          agent=agent,
                          recent_prelevements=recent_prelevements,
                          total_prelevements=total_prelevements,
                          validated_prelevements=validated_prelevements,
                          pending_prelevements=pending_prelevements,
                          station_data=station_data)

@agent_bp.route('/profile')
@login_required
def profile():
    """Profil de l'agent connecté"""
    agent = AgentDGM.query.filter_by(user_id=current_user.id).first()
    
    if not agent:
        flash("Vous n'êtes pas enregistré comme agent de la DGM.", 'warning')
        return redirect(url_for('main.index'))
    
    return render_template('agent/profile.html', agent=agent)

@agent_bp.route('/prelevements')
@login_required
def prelevements():
    """Liste des prélèvements de l'agent connecté"""
    agent = AgentDGM.query.filter_by(user_id=current_user.id).first()
    
    if not agent:
        flash("Vous n'êtes pas enregistré comme agent de la DGM.", 'warning')
        return redirect(url_for('main.index'))
    
    # Filtres
    station_id = request.args.get('station_id', type=int)
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Pagination des prélèvements
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    prelevements_query = Prelevement.query.filter_by(agent_id=agent.id)
    
    # Appliquer les filtres
    if station_id:
        prelevements_query = prelevements_query.filter_by(station_id=station_id)
    
    if status:
        if status == 'validated':
            prelevements_query = prelevements_query.filter_by(validated=True)
        elif status == 'pending':
            prelevements_query = prelevements_query.filter_by(validated=False)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            prelevements_query = prelevements_query.filter(func.date(Prelevement.date_prelevement) >= from_date)
        except ValueError:
            flash('Format de date invalide pour la date de début.', 'warning')
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            prelevements_query = prelevements_query.filter(func.date(Prelevement.date_prelevement) <= to_date)
        except ValueError:
            flash('Format de date invalide pour la date de fin.', 'warning')
    
    # Trier par date de prélèvement (du plus récent au plus ancien)
    prelevements_query = prelevements_query.order_by(Prelevement.date_prelevement.desc())
    
    pagination = prelevements_query.paginate(page=page, per_page=per_page)
    
    # Si l'agent est affecté à une station, n'afficher que celle-ci
    stations = []
    if agent.station_id:
        stations = [agent.station]
    else:
        # Sinon, afficher toutes les stations
        stations = WeatherStation.query.all()
    
    return render_template('agent/prelevements.html', 
                          agent=agent,
                          pagination=pagination,
                          prelevements=pagination.items,
                          stations=stations)

@agent_bp.route('/prelevement/add', methods=['GET', 'POST'])
@login_required
def add_prelevement():
    """Ajouter un nouveau prélèvement"""
    agent = AgentDGM.query.filter_by(user_id=current_user.id).first()
    
    if not agent:
        flash("Vous n'êtes pas enregistré comme agent de la DGM.", 'warning')
        return redirect(url_for('main.index'))
    
    # Récupérer la station de l'agent
    stations = []
    
    # Si l'agent est affecté à une station, n'afficher que celle-ci
    if agent.station_id:
        stations = [WeatherStation.query.get(agent.station_id)]
    else:
        # Sinon, afficher toutes les stations (pour les superviseurs)
        stations = WeatherStation.query.all()
    
    if request.method == 'POST':
        try:
            # Validation des données du formulaire
            station_id = request.form.get('station_id', type=int)
            date_str = request.form.get('date_prelevement')
            time_str = request.form.get('time_prelevement', '12:00')
            temperature = request.form.get('temperature', type=float)
            humidity = request.form.get('humidity', type=float)
            pressure = request.form.get('pressure', type=float)
            wind_speed = request.form.get('wind_speed', type=float)
            wind_direction = request.form.get('wind_direction', type=float)
            precipitation = request.form.get('precipitation', type=float)
            notes = request.form.get('notes', '')
            
            # Validation des champs obligatoires
            if not station_id or not date_str or temperature is None:
                flash('Veuillez remplir tous les champs obligatoires (station, date, température).', 'danger')
                return redirect(url_for('agent.add_prelevement'))
            
            # Conversion de la date et de l'heure
            try:
                date_time_str = f"{date_str} {time_str}"
                date_prelevement = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
            except ValueError:
                flash('Format de date ou d\'heure invalide.', 'danger')
                return redirect(url_for('agent.add_prelevement'))
            
            # Création du nouveau prélèvement
            new_prelevement = Prelevement(
                agent_id=agent.id,
                station_id=station_id,
                date_prelevement=date_prelevement,
                temperature=temperature,
                humidity=humidity,
                pressure=pressure,
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                precipitation=precipitation,
                notes=notes
            )
            
            db.session.add(new_prelevement)
            db.session.commit()
            
            flash('Prélèvement enregistré avec succès!', 'success')
            return redirect(url_for('agent.prelevements'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Une erreur est survenue: {str(e)}', 'danger')
    
    return render_template('agent/add_prelevement.html', 
                          agent=agent,
                          stations=stations)

@agent_bp.route('/prelevement/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_prelevement(id):
    """Modifier un prélèvement existant"""
    agent = AgentDGM.query.filter_by(user_id=current_user.id).first()
    
    if not agent:
        flash("Vous n'êtes pas enregistré comme agent de la DGM.", 'warning')
        return redirect(url_for('main.index'))
    
    # Récupérer le prélèvement
    prelevement = Prelevement.query.get_or_404(id)
    
    # Vérifier que le prélèvement appartient à l'agent
    if prelevement.agent_id != agent.id and current_user.role != 'admin':
        flash("Vous n'êtes pas autorisé à modifier ce prélèvement.", 'danger')
        return redirect(url_for('agent.prelevements'))
    
    # Vérifier que le prélèvement n'est pas déjà validé
    if prelevement.validated and current_user.role != 'admin':
        flash("Ce prélèvement a déjà été validé et ne peut plus être modifié.", 'warning')
        return redirect(url_for('agent.prelevements'))
    
    stations = WeatherStation.query.all()
    
    if request.method == 'POST':
        try:
            # Validation des données du formulaire
            station_id = request.form.get('station_id', type=int)
            date_str = request.form.get('date_prelevement')
            time_str = request.form.get('time_prelevement', '12:00')
            temperature = request.form.get('temperature', type=float)
            humidity = request.form.get('humidity', type=float)
            pressure = request.form.get('pressure', type=float)
            wind_speed = request.form.get('wind_speed', type=float)
            wind_direction = request.form.get('wind_direction', type=float)
            precipitation = request.form.get('precipitation', type=float)
            notes = request.form.get('notes', '')
            
            # Validation des champs obligatoires
            if not station_id or not date_str or temperature is None:
                flash('Veuillez remplir tous les champs obligatoires (station, date, température).', 'danger')
                return redirect(url_for('agent.edit_prelevement', id=id))
            
            # Conversion de la date et de l'heure
            try:
                date_time_str = f"{date_str} {time_str}"
                date_prelevement = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
            except ValueError:
                flash('Format de date ou d\'heure invalide.', 'danger')
                return redirect(url_for('agent.edit_prelevement', id=id))
            
            # Mise à jour du prélèvement
            prelevement.station_id = station_id
            prelevement.date_prelevement = date_prelevement
            prelevement.temperature = temperature
            prelevement.humidity = humidity
            prelevement.pressure = pressure
            prelevement.wind_speed = wind_speed
            prelevement.wind_direction = wind_direction
            prelevement.precipitation = precipitation
            prelevement.notes = notes
            
            db.session.commit()
            
            flash('Prélèvement mis à jour avec succès!', 'success')
            return redirect(url_for('agent.prelevements'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Une erreur est survenue: {str(e)}', 'danger')
    
    # Pour le formulaire GET, préparer les données de date et heure
    date_str = prelevement.date_prelevement.strftime('%Y-%m-%d')
    time_str = prelevement.date_prelevement.strftime('%H:%M')
    
    return render_template('agent/edit_prelevement.html', 
                          agent=agent,
                          prelevement=prelevement,
                          stations=stations,
                          date_str=date_str,
                          time_str=time_str)

@agent_bp.route('/prelevement/<int:id>/delete', methods=['POST'])
@login_required
def delete_prelevement(id):
    """Supprimer un prélèvement"""
    agent = AgentDGM.query.filter_by(user_id=current_user.id).first()
    
    if not agent:
        flash("Vous n'êtes pas enregistré comme agent de la DGM.", 'warning')
        return redirect(url_for('main.index'))
    
    # Récupérer le prélèvement
    prelevement = Prelevement.query.get_or_404(id)
    
    # Vérifier que le prélèvement appartient à l'agent
    if prelevement.agent_id != agent.id and current_user.role != 'admin':
        flash("Vous n'êtes pas autorisé à supprimer ce prélèvement.", 'danger')
        return redirect(url_for('agent.prelevements'))
    
    # Vérifier que le prélèvement n'est pas déjà validé
    if prelevement.validated and current_user.role != 'admin':
        flash("Ce prélèvement a déjà été validé et ne peut plus être supprimé.", 'warning')
        return redirect(url_for('agent.prelevements'))
    
    try:
        db.session.delete(prelevement)
        db.session.commit()
        flash('Prélèvement supprimé avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Une erreur est survenue: {str(e)}', 'danger')
    
    return redirect(url_for('agent.prelevements'))