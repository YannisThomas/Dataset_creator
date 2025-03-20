# 🚦 YOLO Dataset Manager 

## 🌟 Présentation du Projet

YOLO Dataset Manager est une application de bureau complète conçue pour faciliter la création, l'annotation et la gestion de datasets d'images pour la détection d'objets, en se concentrant particulièrement sur les panneaux de signalisation.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-green.svg)
![Mapillary](https://img.shields.io/badge/API-Mapillary-orange.svg)

## 🏗️ Architecture du Projet

```
client_lourd/
├── src/
│   ├── controllers/        # MVC controllers
│   ├── models/             # Data models
│   ├── services/           # Business logic services
│   ├── utils/              # Utility functions and classes
│   ├── views/              # UI components
│   └── main.py             # Application entry point
├── tests/                  # Unit and integration tests
├── data/                   # Data storage directory
├── config.json             # Configuration file
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## ✨ Fonctionnalités Principales

- 🗺️ Import d'images depuis Mapillary
- 🏷️ Annotation de panneaux de signalisation
- 📦 Export dans différents formats (YOLO, COCO, VOC)
- 💾 Gestion de base de données intégrée
- 🔍 Prévisualisation et filtrage des images

## 🚀 Installation

### Prérequis

- Python 3.8+
- pip
- Environnement virtuel recommandé
- Visual C++ Redistributable pour Python (si nécessaire pour Pyqt)

### Étapes d'Installation

1. Clonez le dépôt
```bash
git clone https://github.com/YannisThomas/Dataset_creator.git
cd votre/emplacement/Dataset_creator
```

2. Créez un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix
venv\Scripts\activate     # Sur Windows
```

3. Installez les dépendances
```bash
pip install -r requirements.txt
```

4. Configurez Mapillary
- Créez un compte sur [Mapillary](https://www.mapillary.com/)
- Générez un token API
- Configurez `src/config/mapillary_config.json`
- Pour l'instant, vous pouvez utiliser le token par défaut.

## 🖥️ Utilisation

### Lancement de l'Application
Se mettre dans le dossier source Dataset_creator/client_lourd
```bash
cd votre/emplacement/Dataset_creator/client_lourd
python main.py
```

### Workflow Typique

1. **Import Mapillary**
   - Sélectionner dans fichier, import depuis Mapillary
   - Sélectionnez une zone géographique
   - Prévisualisez et importez

2. **Annotation**
   - Éditez les bounding boxes
   - Ajustez les classes de panneaux

3. **Export**
   - Choisissez le format (recommandé : YOLO)
   - Sélectionnez un répertoire de destination

## 📦 Formats d'Export Supportés

- [x] YOLO
- [ ] COCO (en développement)
- [ ] VOC (en développement)

## 🛠️ Technologies Utilisées

- Python 3.8+
- PyQt6 (Interface Utilisateur)
- SQLite (Base de données)
- Mapillary API
- Pillow (Traitement d'images)
- Pandas (Analyse de données)


**Note**: Ce projet est en développement actif. Les fonctionnalités et l'API peuvent changer.
```
