# GabonMétéo+

Application météorologique intégrée pour la Direction Générale de Météorologie du Gabon.

![Logo GabonMétéo+](app/static/img/logo.png)

## Description

GabonMétéo+ est une plateforme web moderne et complète qui centralise, analyse et présente les données météorologiques du Gabon. Développée pour la Direction Générale de Météorologie du Gabon, cette application offre une interface intuitive et des fonctionnalités avancées pour :

- Visualiser les conditions météorologiques actuelles
- Consulter les prévisions à court terme
- Analyser l'historique des données météorologiques
- Accéder à des informations spécifiques au secteur agricole
- Recevoir des alertes en cas de phénomènes météorologiques importants
- Analyser les statistiques et tendances climatiques
- Accéder aux données via une API RESTful

## Fonctionnalités

### 1. Tableau de bord principal
- Vue d'ensemble des conditions météorologiques actuelles
- Carte interactive des stations météorologiques
- Résumé des alertes et prévisions importantes

### 2. Prévisions météorologiques
- Prévisions sur 3 jours pour chaque station
- Visualisation cartographique des prévisions
- Informations détaillées (température, précipitations, humidité, vent)

### 3. Données historiques
- Consultation et filtrage des données historiques par station
- Graphiques interactifs d'évolution des paramètres météorologiques
- Export des données en format CSV

### 4. Services agricoles
- Calendrier agricole adapté aux conditions climatiques gabonaises
- Recommandations spécifiques par culture et par région
- Alertes pour les périodes de plantation et de récolte

### 5. Système d'alertes
- Visualisation des alertes météorologiques en cours
- Carte des zones concernées par les alertes
- Historique des alertes précédentes

### 6. Statistiques et analyses
- Tendances climatiques à long terme
- Analyse comparative entre stations et régions
- Visualisations avancées des données météorologiques

### 7. API RESTful
- Accès programmatique aux données météorologiques
- Récupération des informations sur les stations
- Données actuelles, historiques et prévisions
- Statistiques climatiques

## Architecture technique

GabonMétéo+ est développé avec les technologies suivantes :

- **Backend** : Flask (Python 3.9+)
- **Base de données** : SQLite (développement) / PostgreSQL (production)
- **Frontend** : HTML5, CSS3, JavaScript, Bootstrap 5
- **Visualisation** : Chart.js, Leaflet.js
- **Authentification** : Flask-Login

## Installation

### Prérequis
- Python 3.9 ou supérieur
- Pip (gestionnaire de paquets Python)
- Git

### Installation locale

1. Cloner le dépôt Git :
```bash
git clone https://github.com/votre-nom/gabonmeteo.git
cd gabonmeteo
```

2. Créer un environnement virtuel Python :
```bash
python -m venv venv
```

3. Activer l'environnement virtuel :
   - Sous Windows :
   ```bash
   venv\Scripts\activate
   ```
   - Sous Linux/MacOS :
   ```bash
   source venv/bin/activate
   ```

4. Installer les dépendances :
```bash
pip install -r requirements.txt
```

5. Lancer l'application :
```bash
python run.py
```

6. Accéder à l'application à l'adresse [http://127.0.0.1:5000](http://127.0.0.1:5000)

### Installation avec Anaconda/Miniconda

1. Créer un environnement Conda :
```bash
conda create -n gabonmeteo python=3.9
conda activate gabonmeteo
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Lancer l'application :
```bash
python run.py
```

## Importation des données

Pour importer des données météorologiques d'exemple :

```bash
python scripts/import_data.py data/sample_weather_data.csv
```

## Utilisation de l'API

GabonMétéo+ propose une API RESTful permettant d'accéder programmatiquement aux données météorologiques.

### Exemples d'utilisation de l'API

#### Python (avec Requests)
```python
import requests

# Récupérer les données météo actuelles
url = "http://localhost:5000/api/current"
response = requests.get(url)
data = response.json()

# Afficher les résultats
for station_data in data["data"]:
    print(f"{station_data['station_name']}: {station_data['temperature']}°C")
```

#### JavaScript (avec Fetch API)
```javascript
// Récupérer les données météo actuelles
fetch('http://localhost:5000/api/current')
  .then(response => response.json())
  .then(data => {
    // Afficher les résultats
    data.data.forEach(station => {
      console.log(`${station.station_name}: ${station.temperature}°C`);
    });
  })
  .catch(error => console.error('Erreur:', error));
```

### Endpoints disponibles

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/status` | GET | Vérifier l'état de l'API |
| `/api/stations` | GET | Liste des stations météo |
| `/api/stations/{id}` | GET | Détails d'une station spécifique |
| `/api/current` | GET | Données météo actuelles pour toutes les stations |
| `/api/stations/{id}/current` | GET | Données actuelles pour une station spécifique |
| `/api/stations/{id}/historical` | GET | Données historiques d'une station |
| `/api/forecast` | GET | Prévisions pour toutes les stations |
| `/api/stations/{id}/forecast` | GET | Prévisions pour une station spécifique |
| `/api/statistics` | GET | Statistiques météorologiques |

Pour une documentation complète de l'API, consultez `/api-docs` dans l'application.

## Structure du projet

```
gabonmeteo/
├── app/                    # Application principale
│   ├── models/             # Modèles de données
│   ├── routes/             # Routes de l'application
│   ├── static/             # Fichiers statiques (CSS, JS, images)
│   ├── templates/          # Templates HTML
│   └── utils/              # Fonctions utilitaires
├── data/                   # Données d'exemple
├── scripts/                # Scripts utilitaires
├── tests/                  # Tests automatisés
├── .gitignore              # Configuration Git
├── README.md               # Documentation
├── requirements.txt        # Dépendances
└── run.py                  # Point d'entrée de l'application
```

## Tests

Pour exécuter les tests automatisés :

```bash
python -m tests.test_app
```

## Déploiement

### Déploiement sur un serveur Linux

1. Installer les dépendances système :
```bash
sudo apt update
sudo apt install python3-pip python3-dev nginx
```

2. Configurer Gunicorn et Nginx (voir documentation complète)

### Déploiement sur Heroku

1. Installer l'outil CLI Heroku
2. Créer une application Heroku :
```bash
heroku create gabonmeteo
```
3. Configurer les fichiers `Procfile` et `requirements.txt`
4. Déployer :
```bash
git push heroku main
```

## Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Forkez le dépôt
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/amazing-feature`)
3. Committez vos changements (`git commit -m 'Add some amazing feature'`)
4. Poussez vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrez une Pull Request

## Licence

Ce projet est la propriété intellectuelle de [Ahmed SOUARE] et ne peut être utilisé sans autorisation explicite.

## Auteur

- **Ahmed SOUARE** - Développeur principal

## Crédits

- Direction Générale de Météorologie du Gabon pour les données météorologiques
- [Bootstrap](https://getbootstrap.com/) pour le framework CSS
- [Chart.js](https://www.chartjs.org/) pour les graphiques
- [Leaflet](https://leafletjs.com/) pour les cartes interactives
- [Flask](https://flask.palletsprojects.com/) pour le framework web

## Version

1.0.0 - Mai 2025