# GabonMétéo+ 🌤️

**Plateforme météorologique intégrée pour la Direction Générale de Météorologie du Gabon**

![License](https://img.shields.io/badge/license-Proprietary-red)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![Flask](https://img.shields.io/badge/flask-2.3.3-green)
![Status](https://img.shields.io/badge/status-Active%20Development-orange)

## 📋 Table des matières

- [À propos](#-à-propos)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [Gestion des utilisateurs](#-gestion-des-utilisateurs)
- [API](#-api)
- [Contribution](#-contribution)
- [Auteur](#-auteur)

## 🎯 À propos

GabonMétéo+ est une application web moderne développée spécifiquement pour la Direction Générale de Météorologie du Gabon. Elle offre une plateforme complète pour la gestion des données météorologiques, des prévisions, et des services sectoriels.

### Objectifs principaux

- Centralisation des données météorologiques du Gabon
- Interface moderne et intuitive pour les agents de la DGM
- Système de validation des prélèvements météorologiques
- Services dédiés aux secteurs (agriculture, aviation, maritime)
- Gestion hiérarchique des utilisateurs et des droits d'accès

## ✨ Fonctionnalités

### 🌡️ Gestion des données météorologiques
- **Prélèvements en temps réel** : Interface de saisie pour les agents DGM
- **Validation des données** : Workflow de validation à plusieurs niveaux
- **Historique complet** : Archivage et consultation des données historiques
- **Visualisations graphiques** : Graphiques interactifs avec Chart.js

### 👥 Gestion des utilisateurs
- **Système de rôles** : SuperAdmin, Admin, Agent DGM, Utilisateur
- **Authentification sécurisée** : Système de connexion avec gestion des sessions
- **Profils personnalisés** : Profils spécifiques selon le type d'utilisateur

### 🏢 Gestion organisationnelle
- **Directions et services** : Gestion de la hiérarchie administrative
- **Affectation des agents** : Attribution des agents aux stations météorologiques
- **Matricules et fonctions** : Gestion complète des données RH

### 🌾 Modules sectoriels
- **Agriculture** : Conseils agricoles basés sur les données météo
- **Aviation** : Informations météorologiques pour l'aviation
- **Maritime** : Données météo spécifiques aux activités maritimes
- **Alertes** : Système d'alertes pour les phénomènes critiques

### ⚙️ Administration système
- **Tableau de bord SuperAdmin** : Vue d'ensemble complète du système
- **Configuration système** : Paramétrage global de l'application
- **Journaux d'activité** : Suivi des actions système
- **Sauvegarde et restauration** : Outils de maintenance

## 🏗️ Architecture

### Stack technique
- **Backend** : Flask (Python 3.9+)
- **Frontend** : Bootstrap 5.3, JavaScript ES6
- **Base de données** : SQLite (développement) / PostgreSQL (production)
- **ORM** : SQLAlchemy
- **Authentification** : Flask-Login
- **Cartes** : Leaflet.js
- **Graphiques** : Chart.js

### Structure du projet
```
GabonMeteo/
├── app/
│   ├── models/           # Modèles de données
│   │   ├── user.py      # Modèle utilisateur
│   │   ├── agent.py     # Modèles agents DGM
│   │   └── weather_data.py # Modèles données météo
│   ├── routes/          # Routes de l'application
│   │   ├── main.py      # Routes principales
│   │   ├── auth.py      # Authentification
│   │   ├── agent.py     # Routes agents DGM
│   │   ├── admin_agent.py # Administration agents
│   │   └── superadmin.py # Routes SuperAdmin
│   ├── templates/       # Templates HTML
│   │   ├── base.html    # Template de base
│   │   ├── agent/       # Templates agents
│   │   ├── admin/       # Templates administration
│   │   └── superadmin/  # Templates SuperAdmin
│   ├── static/          # Fichiers statiques
│   │   ├── css/         # Styles CSS
│   │   ├── js/          # Scripts JavaScript
│   │   └── img/         # Images
│   └── utils/           # Utilitaires
├── data/                # Données de test et configuration
├── scripts/             # Scripts d'import et maintenance
├── tests/               # Tests unitaires
├── requirements.txt     # Dépendances Python
└── run.py              # Point d'entrée de l'application
```

## 🚀 Installation

### Prérequis
- Python 3.9 ou supérieur
- pip (gestionnaire de paquets Python)
- Git

### 1. Cloner le repository
```bash
git clone https://github.com/[votre-username]/GabonMeteo.git
cd GabonMeteo
```

### 2. Créer un environnement virtuel
```bash
# Avec conda
conda create -n gabonmeteo python=3.9
conda activate gabonmeteo

# Ou avec venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Initialiser la base de données
```bash
python run.py
```

La base de données sera créée automatiquement au premier lancement.

## ⚙️ Configuration

### Comptes par défaut

L'application crée automatiquement les comptes suivants :

#### SuperAdmin
- **Email** : `superadmin@gabonmeteo.com`
- **Mot de passe** : `superadmin123`
- **Accès** : Configuration système, gestion des rôles

#### Admin
- **Email** : `admin@gabonmeteo.com`
- **Mot de passe** : `admin123`
- **Accès** : Gestion des agents, validation des prélèvements

### Variables d'environnement (optionnel)
Créez un fichier `.env` pour personnaliser la configuration :
```env
SECRET_KEY=votre_clé_secrète_super_complexe
DATABASE_URL=sqlite:///gabonmeteo.db
DEBUG=True
```

## 🎮 Utilisation

### Démarrage de l'application
```bash
python run.py
```

L'application sera accessible sur `http://localhost:5000`

### Import de données
Pour importer des données météorologiques existantes :
```bash
python scripts/import_data.py data/sample_weather_data.csv
```

### Création d'agents DGM
1. Connectez-vous en tant qu'admin ou superadmin
2. Allez dans "Administration" > "Gestion des agents"
3. Cliquez sur "Ajouter un agent"
4. Associez l'agent à un utilisateur existant

## 👤 Gestion des utilisateurs

### Hiérarchie des rôles

1. **SuperAdmin** 🛡️
   - Accès complet au système
   - Configuration des paramètres globaux
   - Gestion des rôles utilisateurs
   - Journaux système et sauvegardes

2. **Admin** ⚙️
   - Gestion des utilisateurs et agents
   - Validation des prélèvements
   - Gestion des stations météorologiques

3. **Agent DGM** 📊
   - Saisie des prélèvements météorologiques
   - Consultation de ses propres données
   - Profil agent personnalisé

4. **Utilisateur** 👀
   - Consultation des données météorologiques
   - Accès aux prévisions et alertes

### Workflow de validation des prélèvements

1. **Saisie** : L'agent DGM saisit ses prélèvements
2. **Vérification** : Contrôles automatiques de cohérence
3. **Validation** : Un admin valide ou rejette le prélèvement
4. **Intégration** : Les données validées sont intégrées à la base

## 🔧 API

L'application expose des endpoints REST pour l'intégration avec d'autres systèmes :

```
GET /api/stations          # Liste des stations météo
GET /api/weather/latest    # Dernières données météo
GET /api/forecasts         # Prévisions
POST /api/data/upload      # Upload de données (admin requis)
```

## 🤝 Contribution

Ce projet est développé spécifiquement pour la DGM du Gabon. Pour toute contribution :

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 License

Ce projet est sous licence propriétaire. Tous droits réservés à Ahmed SOUARE.

## 👨‍💻 Auteur

**Ahmed SOUARE**
- Développeur principal
- Solution propriétaire pour la DGM Gabon
- Contact : [email-professionnel]

## 📚 Documentation supplémentaire

- [Guide d'installation détaillé](docs/installation.md)
- [Manuel administrateur](docs/admin-guide.md)
- [Guide utilisateur agent DGM](docs/agent-guide.md)
- [API Documentation](docs/api.md)

## 🛣️ Roadmap

### Version 1.1 (À venir)
- [ ] Module d'export avancé
- [ ] Intégration API météo internationales
- [ ] Notifications en temps réel
- [ ] Application mobile compagnon

### Version 1.2 (Planifié)
- [ ] Intelligence artificielle pour prédictions
- [ ] Tableau de bord temps réel
- [ ] Rapports automatisés
- [ ] API publique documentée

---

*Dernière mise à jour : Mai 2025*