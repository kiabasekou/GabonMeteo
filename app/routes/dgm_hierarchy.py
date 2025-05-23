# app/routes/dgm_hierarchy.py
"""
Routes pour la gestion hiérarchique de la DGM
Gestion centralisée des permissions, délégations et workflows
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.agent import AgentDGM, Direction, Service, Prelevement
from app.models.weather_data import WeatherStation, WeatherData
from app.models.user import User
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
import logging

# Configuration du blueprint hiérarchique
dgm_bp = Blueprint('dgm', __name__, url_prefix='/dgm')

# Logging pour traçabilité
logger = logging.getLogger(__name__)

# ================================
# DÉCORATEURS DE PERMISSION
# ================================

def requires_role(*roles):
    """Décorateur pour vérifier les rôles utilisateur"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Connexion requise.', 'warning')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles:
                flash('Accès non autorisé.', 'danger')
                return redirect(url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requires_agent_or_admin(f):
    """Décorateur pour vérifier qu'un utilisateur est agent DGM ou admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Connexion requise.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Vérifier si c'est un admin/superadmin
        if current_user.role in ['admin', 'superadmin']:
            return f(*args, **kwargs)
        
        # Vérifier si c'est un agent DGM
        agent = AgentDGM.query.filter_by(user_id=current_user.id).first()
        if not agent:
            flash('Accès réservé aux agents DGM.', 'danger')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def hierarchy_access_control(f):
    """Contrôle d'accès basé sur la hiérarchie DGM"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Récupérer l'agent connecté
        agent = AgentDGM.query.filter_by(user_id=current_user.id).first()
        
        # Les admins ont accès à tout
        if current_user.role in ['admin', 'superadmin']:
            request.user_permissions = {
                'can_validate': True,
                'can_view_all_services': True,
                'can_manage_agents': True,
                'stations_access': WeatherStation.query.all(),
                'services_access': Service.query.all()
            }
        elif agent:
            # Permissions basées sur la position hiérarchique
            request.user_permissions = calculate_agent_permissions(agent)
        else:
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def calculate_agent_permissions(agent):
    """Calcule les permissions d'un agent selon sa position hiérarchique"""
    permissions = {
        'can_validate': False,
        'can_view_all_services': False,
        'can_manage_agents': False,
        'stations_access': [],
        'services_access': []
    }
    
    # Fonction spécifique = permissions spéciales
    fonction_lower = agent.fonction.lower()
    
    # Chef de service = peut valider dans son service
    if 'chef' in fonction_lower and 'service' in fonction_lower:
        permissions['can_validate'] = True
        permissions['services_access'] = [agent.service]
        permissions['stations_access'] = WeatherStation.query.filter_by(
            region=agent.service.direction.name if agent.service.direction else None
        ).all()
    
    # Directeur = peut tout voir dans sa direction
    elif 'directeur' in fonction_lower:
        permissions['can_validate'] = True
        permissions['can_view_all_services'] = True
        permissions['services_access'] = agent.service.direction.services.all()
        permissions['stations_access'] = WeatherStation.query.all()
    
    # Agent normal = accès limité à sa station
    else:
        permissions['stations_access'] = [agent.station] if agent.station else []
        permissions['services_access'] = [agent.service]
    
    return permissions

# ================================
# TABLEAU DE BORD HIÉRARCHIQUE
# ================================

@dgm_bp.route('/dashboard')
@login_required
@hierarchy_access_control
def hierarchical_dashboard():
    """Tableau de bord adapté au niveau hiérarchique"""
    permissions = request.user_permissions
    agent = AgentDGM.query.filter_by(user_id=current_user.id).first()
    
    # Statistiques personnalisées selon le niveau
    stats = calculate_hierarchical_stats(agent, permissions)
    
    # Données récentes pertinentes
    recent_data = get_relevant_recent_data(agent, permissions)
    
    # Tâches en attente
    pending_tasks = get_pending_tasks(agent, permissions)
    
    return render_template('dgm/hierarchical_dashboard.html',
                          agent=agent,
                          permissions=permissions,
                          stats=stats,
                          recent_data=recent_data,
                          pending_tasks=pending_tasks)

def calculate_hierarchical_stats(agent, permissions):
    """Calcule les statistiques selon le niveau hiérarchique"""
    stats = {}
    
    if permissions['can_view_all_services']:
        # Statistiques directeur/chef de service
        stats.update({
            'agents_sous_supervision': AgentDGM.query.filter(
                AgentDGM.service_id.in_([s.id for s in permissions['services_access']])
            ).count(),
            'prelevements_a_valider': Prelevement.query.filter(
                and_(
                    Prelevement.validated == False,
                    Prelevement.agent.has(
                        AgentDGM.service_id.in_([s.id for s in permissions['services_access']])
                    )
                )
            ).count(),
            'stations_supervisees': len(permissions['stations_access'])
        })
    else:
        # Statistiques agent standard
        if agent:
            stats.update({
                'mes_prelevements': Prelevement.query.filter_by(agent_id=agent.id).count(),
                'prelevements_valides': Prelevement.query.filter_by(
                    agent_id=agent.id, validated=True
                ).count(),
                'prelevements_en_attente': Prelevement.query.filter_by(
                    agent_id=agent.id, validated=False
                ).count()
            })
    
    return stats

def get_relevant_recent_data(agent, permissions):
    """Récupère les données récentes pertinentes selon le niveau"""
    if permissions['can_view_all_services']:
        # Données pour superviseur
        return {
            'recent_prelevements': Prelevement.query.filter(
                Prelevement.agent.has(
                    AgentDGM.service_id.in_([s.id for s in permissions['services_access']])
                )
            ).order_by(Prelevement.timestamp.desc()).limit(10).all(),
            
            'recent_validations': Prelevement.query.filter(
                and_(
                    Prelevement.validated == True,
                    Prelevement.agent.has(
                        AgentDGM.service_id.in_([s.id for s in permissions['services_access']])
                    )
                )
            ).order_by(Prelevement.timestamp.desc()).limit(5).all()
        }
    else:
        # Données pour agent
        if agent:
            return {
                'mes_recent_prelevements': Prelevement.query.filter_by(
                    agent_id=agent.id
                ).order_by(Prelevement.timestamp.desc()).limit(5).all()
            }
    
    return {}

def get_pending_tasks(agent, permissions):
    """Récupère les tâches en attente selon le niveau"""
    tasks = []
    
    if permissions['can_validate']:
        # Tâches de validation
        pending_prelevements = Prelevement.query.filter(
            and_(
                Prelevement.validated == False,
                Prelevement.agent.has(
                    AgentDGM.service_id.in_([s.id for s in permissions['services_access']])
                )
            )
        ).count()
        
        if pending_prelevements > 0:
            tasks.append({
                'type': 'validation',
                'count': pending_prelevements,
                'description': f'{pending_prelevements} prélèvement(s) à valider',
                'priority': 'high' if pending_prelevements > 10 else 'medium',
                'url': url_for('dgm.validation_center')
            })
    
    # Stations sans données récentes
    if permissions['stations_access']:
        yesterday = datetime.now() - timedelta(days=1)
        stations_without_data = []
        
        for station in permissions['stations_access']:
            recent_data = WeatherData.query.filter(
                and_(
                    WeatherData.station_id == station.id,
                    WeatherData.timestamp >= yesterday
                )
            ).first()
            
            if not recent_data:
                stations_without_data.append(station)
        
        if stations_without_data:
            tasks.append({
                'type': 'missing_data',
                'count': len(stations_without_data),
                'description': f'{len(stations_without_data)} station(s) sans données récentes',
                'priority': 'medium',
                'stations': [s.name for s in stations_without_data]
            })
    
    return tasks

# ================================
# CENTRE DE VALIDATION HIÉRARCHIQUE
# ================================

@dgm_bp.route('/validation-center')
@login_required
@hierarchy_access_control
def validation_center():
    """Centre de validation adapté au niveau hiérarchique"""
    permissions = request.user_permissions
    
    if not permissions['can_validate']:
        flash('Vous n\'avez pas les droits de validation.', 'warning')
        return redirect(url_for('dgm.hierarchical_dashboard'))
    
    # Filtres
    service_id = request.args.get('service_id', type=int)
    station_id = request.args.get('station_id', type=int)
    urgency = request.args.get('urgency')  # high, medium, low
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Requête de base selon les permissions
    query = build_validation_query(permissions, service_id, station_id, urgency)
    
    pagination = query.paginate(page=page, per_page=per_page)
    
    return render_template('dgm/validation_center.html',
                          permissions=permissions,
                          pagination=pagination,
                          prelevements=pagination.items,
                          services=permissions['services_access'],
                          stations=permissions['stations_access'])

def build_validation_query(permissions, service_id=None, station_id=None, urgency=None):
    """Construit la requête de validation selon les permissions"""
    query = Prelevement.query.filter(
        and_(
            Prelevement.validated == False,
            Prelevement.agent.has(
                AgentDGM.service_id.in_([s.id for s in permissions['services_access']])
            )
        )
    )
    
    # Filtres supplémentaires
    if service_id:
        query = query.filter(Prelevement.agent.has(AgentDGM.service_id == service_id))
    
    if station_id:
        query = query.filter(Prelevement.station_id == station_id)
    
    if urgency:
        # Logique d'urgence basée sur l'âge du prélèvement
        if urgency == 'high':
            # Prélèvements de plus de 24h
            cutoff = datetime.now() - timedelta(hours=24)
            query = query.filter(Prelevement.timestamp < cutoff)
        elif urgency == 'medium':
            # Prélèvements entre 12h et 24h
            cutoff_max = datetime.now() - timedelta(hours=12)
            cutoff_min = datetime.now() - timedelta(hours=24)
            query = query.filter(and_(
                Prelevement.timestamp < cutoff_max,
                Prelevement.timestamp >= cutoff_min
            ))
        elif urgency == 'low':
            # Prélèvements récents (moins de 12h)
            cutoff = datetime.now() - timedelta(hours=12)
            query = query.filter(Prelevement.timestamp >= cutoff)
    
    return query.order_by(Prelevement.timestamp.asc())

# ================================
# ACTIONS DE VALIDATION
# ================================

@dgm_bp.route('/validate-prelevement/<int:id>', methods=['POST'])
@login_required
@hierarchy_access_control
def validate_prelevement(id):
    """Validation hiérarchique d'un prélèvement"""
    permissions = request.user_permissions
    
    if not permissions['can_validate']:
        return jsonify({'error': 'Permissions insuffisantes'}), 403
    
    prelevement = Prelevement.query.get_or_404(id)
    
    # Vérifier que l'agent appartient aux services supervisés
    if prelevement.agent.service not in permissions['services_access']:
        return jsonify({'error': 'Prélèvement hors de votre périmètre'}), 403
    
    try:
        # Marquer comme validé
        prelevement.validated = True
        
        # Créer l'entrée WeatherData
        weather_data = prelevement.to_weather_data()
        db.session.add(weather_data)
        
        # Log de traçabilité
        logger.info(f'Prélèvement {id} validé par {current_user.username} '
                   f'(Agent: {prelevement.agent.matricule})')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Prélèvement validé avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur validation prélèvement {id}: {str(e)}')
        return jsonify({'error': 'Erreur lors de la validation'}), 500

@dgm_bp.route('/batch-validate', methods=['POST'])
@login_required
@hierarchy_access_control
def batch_validate():
    """Validation en lot pour les superviseurs"""
    permissions = request.user_permissions
    
    if not permissions['can_validate']:
        return jsonify({'error': 'Permissions insuffisantes'}), 403
    
    prelevement_ids = request.json.get('prelevement_ids', [])
    
    if not prelevement_ids:
        return jsonify({'error': 'Aucun prélèvement sélectionné'}), 400
    
    validated_count = 0
    errors = []
    
    for prelevement_id in prelevement_ids:
        try:
            prelevement = Prelevement.query.get(prelevement_id)
            
            if not prelevement:
                errors.append(f'Prélèvement {prelevement_id} non trouvé')
                continue
            
            # Vérifier les permissions
            if prelevement.agent.service not in permissions['services_access']:
                errors.append(f'Prélèvement {prelevement_id} hors périmètre')
                continue
            
            if prelevement.validated:
                errors.append(f'Prélèvement {prelevement_id} déjà validé')
                continue
            
            # Valider
            prelevement.validated = True
            weather_data = prelevement.to_weather_data()
            db.session.add(weather_data)
            validated_count += 1
            
        except Exception as e:
            errors.append(f'Erreur prélèvement {prelevement_id}: {str(e)}')
    
    try:
        db.session.commit()
        logger.info(f'Validation en lot par {current_user.username}: '
                   f'{validated_count} prélèvements validés')
        
        return jsonify({
            'success': True,
            'validated_count': validated_count,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erreur lors de la validation en lot'}), 500

# ================================
# GESTION DES DÉLÉGATIONS
# ================================

@dgm_bp.route('/delegations')
@login_required
@requires_role('admin', 'superadmin')
def manage_delegations():
    """Gestion des délégations de pouvoir"""
    
    # Récupérer les agents avec fonctions de supervision
    supervisors = AgentDGM.query.filter(
        or_(
            AgentDGM.fonction.contains('chef'),
            AgentDGM.fonction.contains('directeur'),
            AgentDGM.fonction.contains('responsable')
        )
    ).all()
    
    # Délégations actives
    active_delegations = get_active_delegations()
    
    return render_template('dgm/delegations.html',
                          supervisors=supervisors,
                          active_delegations=active_delegations)

def get_active_delegations():
    """Récupère les délégations actives (à implémenter selon vos besoins)"""
    # Ici vous pourriez avoir une table Delegation
    # Pour l'instant, retour d'une liste vide
    return []

# ================================
# RAPPORTS HIÉRARCHIQUES
# ================================

@dgm_bp.route('/reports/hierarchical')
@login_required
@hierarchy_access_control
def hierarchical_reports():
    """Rapports adaptés au niveau hiérarchique"""
    permissions = request.user_permissions
    
    # Période de rapport
    period = request.args.get('period', '7days')
    
    # Générer les rapports selon le niveau
    reports = generate_hierarchical_reports(permissions, period)
    
    return render_template('dgm/hierarchical_reports.html',
                          permissions=permissions,
                          reports=reports,
                          period=period)

def generate_hierarchical_reports(permissions, period):
    """Génère les rapports selon le niveau hiérarchique"""
    reports = {}
    
    # Définir la période
    if period == '7days':
        start_date = datetime.now() - timedelta(days=7)
    elif period == '30days':
        start_date = datetime.now() - timedelta(days=30)
    elif period == '90days':
        start_date = datetime.now() - timedelta(days=90)
    else:
        start_date = datetime.now() - timedelta(days=7)
    
    if permissions['can_view_all_services']:
        # Rapports de supervision
        reports.update({
            'productivity_by_agent': get_agent_productivity_report(
                permissions['services_access'], start_date
            ),
            'validation_delays': get_validation_delays_report(
                permissions['services_access'], start_date
            ),
            'data_quality': get_data_quality_report(
                permissions['stations_access'], start_date
            )
        })
    
    return reports

def get_agent_productivity_report(services, start_date):
    """Rapport de productivité des agents"""
    service_ids = [s.id for s in services]
    
    productivity = db.session.query(
        AgentDGM.matricule,
        AgentDGM.fonction,
        func.count(Prelevement.id).label('total_prelevements'),
        func.count(func.nullif(Prelevement.validated, False)).label('validated_prelevements')
    ).join(Prelevement).filter(
        and_(
            AgentDGM.service_id.in_(service_ids),
            Prelevement.timestamp >= start_date
        )
    ).group_by(AgentDGM.id).all()
    
    return [
        {
            'matricule': p.matricule,
            'fonction': p.fonction,
            'total': p.total_prelevements,
            'validated': p.validated_prelevements,
            'rate': round((p.validated_prelevements / p.total_prelevements * 100) if p.total_prelevements > 0 else 0, 1)
        }
        for p in productivity
    ]

def get_validation_delays_report(services, start_date):
    """Rapport des délais de validation"""
    service_ids = [s.id for s in services]
    
    # Calculer les délais moyens
    delays = db.session.query(
        Service.name,
        func.avg(
            func.julianday(func.datetime('now')) - 
            func.julianday(Prelevement.timestamp)
        ).label('avg_delay_days')
    ).join(AgentDGM).join(Prelevement).filter(
        and_(
            Service.id.in_(service_ids),
            Prelevement.timestamp >= start_date,
            Prelevement.validated == False
        )
    ).group_by(Service.id).all()
    
    return [
        {
            'service': d.name,
            'avg_delay_days': round(d.avg_delay_days, 1) if d.avg_delay_days else 0
        }
        for d in delays
    ]

def get_data_quality_report(stations, start_date):
    """Rapport de qualité des données"""
    quality_issues = []
    
    for station in stations:
        # Vérifier la complétude des données
        total_data = WeatherData.query.filter(
            and_(
                WeatherData.station_id == station.id,
                WeatherData.timestamp >= start_date
            )
        ).count()
        
        # Données avec valeurs manquantes
        incomplete_data = WeatherData.query.filter(
            and_(
                WeatherData.station_id == station.id,
                WeatherData.timestamp >= start_date,
                or_(
                    WeatherData.temperature.is_(None),
                    WeatherData.humidity.is_(None),
                    WeatherData.precipitation.is_(None)
                )
            )
        ).count()
        
        quality_issues.append({
            'station': station.name,
            'total_records': total_data,
            'incomplete_records': incomplete_data,
            'completeness_rate': round(
                ((total_data - incomplete_data) / total_data * 100) if total_data > 0 else 0, 1
            )
        })
    
    return quality_issues

# ================================
# API POUR INTERFACES DYNAMIQUES
# ================================

@dgm_bp.route('/api/permissions')
@login_required
@hierarchy_access_control
def get_user_permissions():
    """API pour récupérer les permissions utilisateur"""
    permissions = request.user_permissions
    
    return jsonify({
        'can_validate': permissions['can_validate'],
        'can_view_all_services': permissions['can_view_all_services'],
        'can_manage_agents': permissions['can_manage_agents'],
        'stations_count': len(permissions['stations_access']),
        'services_count': len(permissions['services_access'])
    })

@dgm_bp.route('/api/stats/dashboard')
@login_required
@hierarchy_access_control
def get_dashboard_stats():
    """API pour les statistiques du tableau de bord"""
    permissions = request.user_permissions
    agent = AgentDGM.query.filter_by(user_id=current_user.id).first()
    
    stats = calculate_hierarchical_stats(agent, permissions)
    
    return jsonify(stats)

# ================================
# ROUTES D'EXPORT HIÉRARCHIQUE
# ================================

@dgm_bp.route('/export/my-scope')
@login_required
@hierarchy_access_control
def export_my_scope():
    """Export des données selon le périmètre de l'utilisateur"""
    permissions = request.user_permissions
    
    # Format d'export
    format_type = request.args.get('format', 'csv')  # csv, excel, json
    
    # Période
    period = request.args.get('period', '30days')
    
    if period == '7days':
        start_date = datetime.now() - timedelta(days=7)
    elif period == '30days':
        start_date = datetime.now() - timedelta(days=30)
    elif period == '90days':
        start_date = datetime.now() - timedelta(days=90)
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    # Construire les données d'export
    export_data = build_export_data(permissions, start_date)
    
    # Générer le fichier selon le format
    if format_type == 'json':
        return jsonify(export_data)
    else:
        # Pour CSV/Excel, vous pourriez utiliser pandas ou openpyxl
        return jsonify({
            'message': f'Export {format_type} en cours de développement',
            'data_count': len(export_data.get('prelevements', []))
        })

def build_export_data(permissions, start_date):
    """Construit les données d'export selon les permissions"""
    export_data = {
        'export_date': datetime.now().isoformat(),
        'period_start': start_date.isoformat(),
        'user': current_user.username,
        'scope': 'supervisor' if permissions['can_view_all_services'] else 'agent'
    }
    
    # Prélèvements dans le périmètre
    if permissions['can_view_all_services']:
        prelevements = Prelevement.query.filter(
            and_(
                Prelevement.timestamp >= start_date,
                Prelevement.agent.has(
                    AgentDGM.service_id.in_([s.id for s in permissions['services_access']])
                )
            )
        ).all()
    else:
        agent = AgentDGM.query.filter_by(user_id=current_user.id).first()
        prelevements = Prelevement.query.filter(
            and_(
                Prelevement.agent_id == agent.id,
                Prelevement.timestamp >= start_date
            )
        ).all() if agent else []
    
    export_data['prelevements'] = [
        {
            'id': p.id,
            'agent_matricule': p.agent.matricule,
            'station_name': p.station.name,
            'date_prelevement': p.date_prelevement.isoformat(),
            'temperature': p.temperature,
            'humidity': p.humidity,
            'precipitation': p.precipitation,
            'validated': p.validated
        }
        for p in prelevements
    ]
    
    return export_data