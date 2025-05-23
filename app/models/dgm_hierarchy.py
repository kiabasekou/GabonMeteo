# app/models/dgm_hierarchy.py
"""
Modèles de données pour la structure hiérarchique officielle de la DGM
Basé sur le décret n°0768/PR/MERN du 22 août 2008
"""

from app.extensions import db
from datetime import datetime
from enum import Enum

class TypePoste(Enum):
    """Types de postes dans la hiérarchie DGM"""
    DIRECTEUR_GENERAL = "directeur_general"
    DIRECTEUR_ADJOINT = "directeur_adjoint"
    DIRECTEUR_DIVISION = "directeur_division"
    CHEF_SERVICE = "chef_service"
    AGENT_DGM = "agent_dgm"
    TECHNICIEN = "technicien"
    OBSERVATEUR = "observateur"

class NiveauValidation(Enum):
    """Niveaux de validation dans la chaîne hiérarchique"""
    AGENT = 1           # Saisie initiale
    SERVICE = 2         # Validation technique
    DIVISION = 3        # Validation divisionnaire
    DIRECTION = 4       # Validation direction générale

class Division(db.Model):
    """
    Divisions de la DGM selon l'organigramme officiel
    """
    __tablename__ = 'division'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(10), nullable=False, unique=True)
    description = db.Column(db.Text)
    directeur_id = db.Column(db.Integer, db.ForeignKey('agent_dgm.id'))
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    
    # Relations
    services = db.relationship('ServiceDGM', backref='division', lazy='dynamic')
    directeur = db.relationship('AgentDGM', foreign_keys=[directeur_id])
    
    def __repr__(self):
        return f'<Division {self.nom}>'
    
    @property
    def nombre_services(self):
        return self.services.filter_by(active=True).count()
    
    @property
    def nombre_agents(self):
        total = 0
        for service in self.services:
            total += service.nombre_agents
        return total

class ServiceDGM(db.Model):
    """
    Services de la DGM selon l'organigramme officiel
    """
    __tablename__ = 'service_dgm'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    description = db.Column(db.Text)
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'), nullable=False)
    chef_service_id = db.Column(db.Integer, db.ForeignKey('agent_dgm.id'))
    
    # Attributs spécifiques
    mission_principale = db.Column(db.Text)
    attributions = db.Column(db.Text)  # JSON des attributions
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    
    # Relations
    agents = db.relationship('AgentDGM', 
                           foreign_keys='AgentDGM.service_id',
                           backref='service_affectation')
    chef = db.relationship('AgentDGM', foreign_keys=[chef_service_id])
    
    def __repr__(self):
        return f'<Service {self.nom}>'
    
    @property
    def nombre_agents(self):
        return self.agents.filter_by(active=True).count()

class PosteDGM(db.Model):
    """
    Postes et fonctions dans la hiérarchie DGM
    """
    __tablename__ = 'poste_dgm'
    
    id = db.Column(db.Integer, primary_key=True)
    intitule = db.Column(db.String(100), nullable=False)
    type_poste = db.Column(db.Enum(TypePoste), nullable=False)
    niveau_hierarchique = db.Column(db.Integer, nullable=False)  # 1=le plus élevé
    
    # Permissions et responsabilités
    permissions = db.Column(db.Text)  # JSON des permissions
    responsabilites = db.Column(db.Text)  # JSON des responsabilités
    
    # Contraintes organisationnelles
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service_dgm.id'))
    superieur_hierarchique_id = db.Column(db.Integer, db.ForeignKey('poste_dgm.id'))
    
    # Relations
    superieur = db.relationship('PosteDGM', remote_side=[id])
    agents = db.relationship('AgentDGM', backref='poste_actuel')
    
    def __repr__(self):
        return f'<Poste {self.intitule}>'

class CentreRegional(db.Model):
    """
    Centres météorologiques régionaux (services déconcentrés)
    """
    __tablename__ = 'centre_regional'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    region = db.Column(db.String(50), nullable=False)
    ville_siege = db.Column(db.String(50))
    
    # Coordonnées géographiques
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    # Responsable du centre
    responsable_id = db.Column(db.Integer, db.ForeignKey('agent_dgm.id'))
    
    # Zone de compétence
    provinces_couvertes = db.Column(db.Text)  # JSON des provinces
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    
    # Relations
    responsable = db.relationship('AgentDGM')
    stations = db.relationship('WeatherStation', backref='centre_regional')
    
    def __repr__(self):
        return f'<Centre {self.nom}>'

class WorkflowValidation(db.Model):
    """
    Workflow de validation des données selon la hiérarchie DGM
    """
    __tablename__ = 'workflow_validation'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Référence à l'objet validé
    objet_type = db.Column(db.String(50), nullable=False)  # 'prelevement', 'rapport', etc.
    objet_id = db.Column(db.Integer, nullable=False)
    
    # Étape de validation
    niveau_actuel = db.Column(db.Enum(NiveauValidation), nullable=False)
    statut = db.Column(db.String(20), default='en_attente')  # en_attente, valide, rejete
    
    # Agents impliqués
    agent_createur_id = db.Column(db.Integer, db.ForeignKey('agent_dgm.id'), nullable=False)
    validateur_actuel_id = db.Column(db.Integer, db.ForeignKey('agent_dgm.id'))
    
    # Historique des validations
    historique_validations = db.Column(db.Text)  # JSON de l'historique
    
    # Commentaires et notes
    commentaires = db.Column(db.Text)
    motif_rejet = db.Column(db.Text)
    
    # Timestamps
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_derniere_action = db.Column(db.DateTime, default=datetime.utcnow)
    date_validation_finale = db.Column(db.DateTime)
    
    # Relations
    agent_createur = db.relationship('AgentDGM', foreign_keys=[agent_createur_id])
    validateur_actuel = db.relationship('AgentDGM', foreign_keys=[validateur_actuel_id])
    
    def __repr__(self):
        return f'<Workflow {self.objet_type}:{self.objet_id} - {self.statut}>'
    
    def avancer_validation(self, validateur, decision, commentaire=None):
        """Fait avancer le workflow de validation"""
        import json
        from datetime import datetime
        
        # Mettre à jour l'historique
        if self.historique_validations:
            historique = json.loads(self.historique_validations)
        else:
            historique = []
        
        historique.append({
            'niveau': self.niveau_actuel.value,
            'validateur_id': validateur.id,
            'validateur_nom': validateur.user.username,
            'decision': decision,
            'commentaire': commentaire,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        self.historique_validations = json.dumps(historique)
        self.date_derniere_action = datetime.utcnow()
        
        if decision == 'valide':
            # Passer au niveau suivant ou finaliser
            if self.niveau_actuel == NiveauValidation.AGENT:
                self.niveau_actuel = NiveauValidation.SERVICE
                self.validateur_actuel_id = self._get_next_validator()
            elif self.niveau_actuel == NiveauValidation.SERVICE:
                self.niveau_actuel = NiveauValidation.DIVISION
                self.validateur_actuel_id = self._get_next_validator()
            elif self.niveau_actuel == NiveauValidation.DIVISION:
                self.statut = 'valide'
                self.date_validation_finale = datetime.utcnow()
        elif decision == 'rejete':
            self.statut = 'rejete'
            self.motif_rejet = commentaire
        
        if commentaire:
            if self.commentaires:
                self.commentaires += f"\n---\n{commentaire}"
            else:
                self.commentaires = commentaire
    
    def _get_next_validator(self):
        """Détermine le prochain validateur selon la hiérarchie"""
        # Logique pour déterminer le prochain validateur
        # basée sur la hiérarchie et le type d'objet
        pass

class CompetenceDGM(db.Model):
    """
    Compétences et spécialisations des agents DGM
    """
    __tablename__ = 'competence_dgm'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    domaine = db.Column(db.String(50), nullable=False)  # meteorologie, climatologie, etc.
    niveau = db.Column(db.String(20))  # debutant, intermediaire, avance, expert
    
    # Certification
    certifie = db.Column(db.Boolean, default=False)
    organisme_certification = db.Column(db.String(100))
    date_certification = db.Column(db.Date)
    date_expiration = db.Column(db.Date)
    
    description = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Competence {self.nom}>'

# Table d'association pour les compétences des agents
agent_competences = db.Table('agent_competences',
    db.Column('agent_id', db.Integer, db.ForeignKey('agent_dgm.id'), primary_key=True),
    db.Column('competence_id', db.Integer, db.ForeignKey('competence_dgm.id'), primary_key=True),
    db.Column('date_acquisition', db.DateTime, default=datetime.utcnow),
    db.Column('niveau_maitrise', db.String(20), default='intermediaire'),
    db.Column('derniere_evaluation', db.DateTime)
)

class FormationDGM(db.Model):
    """
    Formations et perfectionnements des agents DGM
    """
    __tablename__ = 'formation_dgm'
    
    id = db.Column(db.Integer, primary_key=True)
    intitule = db.Column(db.String(150), nullable=False)
    organisme = db.Column(db.String(100))
    type_formation = db.Column(db.String(50))  # initiale, continue, specialisation
    
    # Durée et modalités
    duree_heures = db.Column(db.Integer)
    modalite = db.Column(db.String(50))  # presentiel, distanciel, mixte
    
    # Dates
    date_debut = db.Column(db.Date)
    date_fin = db.Column(db.Date)
    
    # Compétences visées
    competences_visees = db.Column(db.Text)  # JSON des compétences
    
    # Statut
    statut = db.Column(db.String(20), default='planifiee')  # planifiee, en_cours, terminee, annulee
    
    description = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Formation {self.intitule}>'

# Table d'association pour les formations suivies par les agents
agent_formations = db.Table('agent_formations',
    db.Column('agent_id', db.Integer, db.ForeignKey('agent_dgm.id'), primary_key=True),
    db.Column('formation_id', db.Integer, db.ForeignKey('formation_dgm.id'), primary_key=True),
    db.Column('date_inscription', db.DateTime, default=datetime.utcnow),
    db.Column('statut_participation', db.String(20), default='inscrit'),  # inscrit, presente, absente, certifie
    db.Column('note_evaluation', db.Float),
    db.Column('commentaires', db.Text)
)

class RapportActivite(db.Model):
    """
    Rapports d'activité selon la hiérarchie DGM
    """
    __tablename__ = 'rapport_activite'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Type et niveau du rapport
    type_rapport = db.Column(db.String(50), nullable=False)  # mensuel, trimestriel, annuel
    niveau_hierarchique = db.Column(db.String(50), nullable=False)  # service, division, direction
    
    # Période couverte
    periode_debut = db.Column(db.Date, nullable=False)
    periode_fin = db.Column(db.Date, nullable=False)
    
    # Auteur et validation
    auteur_id = db.Column(db.Integer, db.ForeignKey('agent_dgm.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service_dgm.id'))
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'))
    
    # Contenu
    titre = db.Column(db.String(200), nullable=False)
    resume_executif = db.Column(db.Text)
    activites_realisees = db.Column(db.Text)  # JSON structuré
    indicateurs_performance = db.Column(db.Text)  # JSON des KPI
    difficultes_rencontrees = db.Column(db.Text)
    recommandations = db.Column(db.Text)
    
    # Annexes et documents
    documents_joints = db.Column(db.Text)  # JSON des fichiers joints
    
    # Workflow
    statut = db.Column(db.String(20), default='brouillon')  # brouillon, soumis, valide, publie
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow_validation.id'))
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_soumission = db.Column(db.DateTime)
    date_validation = db.Column(db.DateTime)
    date_publication = db.Column(db.DateTime)
    
    # Relations
    auteur = db.relationship('AgentDGM')
    service = db.relationship('ServiceDGM')
    division = db.relationship('Division')
    workflow = db.relationship('WorkflowValidation')
    
    def __repr__(self):
        return f'<Rapport {self.titre}>'

class PlanificationActivites(db.Model):
    """
    Planification des activités par service/division
    """
    __tablename__ = 'planification_activites'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Identification de l'activité
    nom_activite = db.Column(db.String(150), nullable=False)
    type_activite = db.Column(db.String(50))  # routine, projet, maintenance, formation
    priorite = db.Column(db.String(20), default='normale')  # faible, normale, haute, critique
    
    # Responsabilité
    service_responsable_id = db.Column(db.Integer, db.ForeignKey('service_dgm.id'))
    agent_responsable_id = db.Column(db.Integer, db.ForeignKey('agent_dgm.id'))
    
    # Planification temporelle
    date_debut_prevue = db.Column(db.Date)
    date_fin_prevue = db.Column(db.Date)
    duree_estimee_jours = db.Column(db.Integer)
    
    # Ressources nécessaires
    ressources_humaines = db.Column(db.Text)  # JSON
    ressources_materielles = db.Column(db.Text)  # JSON
    budget_estime = db.Column(db.Float)
    
    # Suivi et réalisation
    statut = db.Column(db.String(20), default='planifiee')  # planifiee, en_cours, terminee, reportee, annulee
    pourcentage_avancement = db.Column(db.Integer, default=0)
    
    date_debut_reelle = db.Column(db.Date)
    date_fin_reelle = db.Column(db.Date)
    
    # Descriptions et objectifs
    description = db.Column(db.Text)
    objectifs = db.Column(db.Text)
    resultats_attendus = db.Column(db.Text)
    indicateurs_succes = db.Column(db.Text)  # JSON
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    createur_id = db.Column(db.Integer, db.ForeignKey('agent_dgm.id'))
    
    # Relations
    service_responsable = db.relationship('ServiceDGM')
    agent_responsable = db.relationship('AgentDGM', foreign_keys=[agent_responsable_id])
    createur = db.relationship('AgentDGM', foreign_keys=[createur_id])
    
    def __repr__(self):
        return f'<Activite {self.nom_activite}>'

# Extension du modèle AgentDGM existant avec les nouvelles relations
class AgentDGMExtension:
    """
    Extension du modèle AgentDGM pour intégrer la nouvelle hiérarchie
    Ces relations doivent être ajoutées au modèle AgentDGM existant
    """
    
    # Hiérarchie et poste
    poste_id = db.Column(db.Integer, db.ForeignKey('poste_dgm.id'))
    superieur_hierarchique_id = db.Column(db.Integer, db.ForeignKey('agent_dgm.id'))
    centre_regional_id = db.Column(db.Integer, db.ForeignKey('centre_regional.id'))
    
    # Statut et carrière
    active = db.Column(db.Boolean, default=True)
    date_prise_fonction = db.Column(db.Date)
    date_fin_fonction = db.Column(db.Date)
    grade = db.Column(db.String(50))
    echelon = db.Column(db.String(20))
    
    # Formations et compétences (relations many-to-many)
    competences = db.relationship('CompetenceDGM', 
                                 secondary=agent_competences,
                                 backref='agents_qualifies')
    
    formations = db.relationship('FormationDGM',
                                secondary=agent_formations,
                                backref='participants')
    
    # Relations hiérarchiques
    superieur_hierarchique = db.relationship('AgentDGM', remote_side='AgentDGM.id')
    subordonnes = db.relationship('AgentDGM', backref='chef_direct')
    
    # Activités et rapports
    rapports_rediges = db.relationship('RapportActivite', backref='redacteur')
    activites_responsable = db.relationship('PlanificationActivites', 
                                          foreign_keys='PlanificationActivites.agent_responsable_id',
                                          backref='responsable')
    
    # Workflows de validation
    workflows_crees = db.relationship('WorkflowValidation',
                                     foreign_keys='WorkflowValidation.agent_createur_id',
                                     backref='createur')
    workflows_a_valider = db.relationship('WorkflowValidation',
                                         foreign_keys='WorkflowValidation.validateur_actuel_id',
                                         backref='validateur')
    
    def get_permissions(self):
        """Retourne les permissions de l'agent selon son poste"""
        if not self.poste_actuel:
            return []
        
        import json
        if self.poste_actuel.permissions:
            return json.loads(self.poste_actuel.permissions)
        return []
    
    def peut_valider(self, niveau_validation):
        """Vérifie si l'agent peut valider à un niveau donné"""
        permissions = self.get_permissions()
        return f'validate_{niveau_validation.value}' in permissions
    
    def get_subordonnes_directs(self):
        """Retourne la liste des subordonnés directs"""
        return AgentDGM.query.filter_by(superieur_hierarchique_id=self.id).all()
    
    def get_competences_par_domaine(self):
        """Retourne les compétences organisées par domaine"""
        competences_par_domaine = {}
        for competence in self.competences:
            if competence.domaine not in competences_par_domaine:
                competences_par_domaine[competence.domaine] = []
            competences_par_domaine[competence.domaine].append(competence)
        return competences_par_domaine