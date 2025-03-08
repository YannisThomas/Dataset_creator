# src/database/db_manager.py

from typing import Optional, Dict, Any, List
from pathlib import Path
import sqlite3
import json
from datetime import datetime

from src.models import Dataset, Image, Annotation, BoundingBox
from src.models.enums import ImageSource, AnnotationType
from src.utils.logger import Logger

class DatabaseManager:
    """
    Gestionnaire de base de données pour le stockage persistant des datasets.
    Cette classe gère les interactions avec la base de données SQLite.
    """
    
    def __init__(self, db_path: Optional[Path] = None, logger: Optional[Logger] = None):
        """
        Initialise le gestionnaire de base de données.
        
        Args:
            db_path: Chemin vers le fichier de base de données
            logger: Gestionnaire de logs
        """
        self.db_path = db_path or Path("data/yolo_datasets.db")
        self.logger = logger or Logger()
        
        # Créer le répertoire parent si nécessaire
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialiser la connexion
        self.conn = None
        self._init_connection()
    
    def _init_connection(self):
        """Initialise la connexion à la base de données et crée les tables si nécessaire."""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            # Activer le support des clés étrangères
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Permettre d'accéder aux colonnes par nom
            self.conn.row_factory = sqlite3.Row
            
            # Créer les tables si elles n'existent pas
            self._create_tables()
            
            self.logger.info(f"Connexion à la base de données établie: {self.db_path}")
        except Exception as e:
            self.logger.error(f"Échec de la connexion à la base de données: {str(e)}")
            raise
    
    def _create_tables(self):
        """Crée les tables nécessaires si elles n'existent pas."""
        cursor = self.conn.cursor()
        
        # Table des datasets
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS datasets (
            name TEXT PRIMARY KEY,
            version TEXT NOT NULL,
            path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            modified_at TEXT,
            classes TEXT NOT NULL,
            metadata TEXT
        )
        ''')
        
        # Table des images
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            dataset_name TEXT NOT NULL,
            path TEXT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            modified_at TEXT,
            metadata TEXT,
            FOREIGN KEY (dataset_name) REFERENCES datasets(name) ON DELETE CASCADE
        )
        ''')
        
        # Table des annotations
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT NOT NULL,
            class_id INTEGER NOT NULL,
            bbox_x REAL NOT NULL,
            bbox_y REAL NOT NULL,
            bbox_width REAL NOT NULL,
            bbox_height REAL NOT NULL,
            confidence REAL,
            type TEXT NOT NULL,
            metadata TEXT,
            FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
        )
        ''')
        
        # Table de migration
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            description TEXT,
            applied_at TEXT NOT NULL
        )
        ''')
        
        self.conn.commit()
    
    def save_dataset(self, dataset: Dataset) -> bool:
        """
        Sauvegarde un dataset dans la base de données.
        
        Args:
            dataset: Dataset à sauvegarder
            
        Returns:
            True si la sauvegarde a réussi
        """
        try:
            cursor = self.conn.cursor()
            
            # Sérialiser les classes et métadonnées en JSON
            classes_json = json.dumps(dataset.classes)
            metadata_json = json.dumps(dataset.metadata)
            
            # Vérifier si le dataset existe déjà
            cursor.execute("SELECT name FROM datasets WHERE name = ?", (dataset.name,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # Mettre à jour le dataset existant
                cursor.execute('''
                UPDATE datasets
                SET version = ?, path = ?, modified_at = ?, classes = ?, metadata = ?
                WHERE name = ?
                ''', (
                    dataset.version,
                    str(dataset.path),
                    datetime.now().isoformat(),
                    classes_json,
                    metadata_json,
                    dataset.name
                ))
            else:
                # Insérer un nouveau dataset
                cursor.execute('''
                INSERT INTO datasets (name, version, path, created_at, modified_at, classes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    dataset.name,
                    dataset.version,
                    str(dataset.path),
                    dataset.created_at.isoformat(),
                    datetime.now().isoformat() if dataset.modified_at else None,
                    classes_json,
                    metadata_json
                ))
            
            # Supprimer toutes les anciennes images et annotations (cascade delete)
            if exists:
                cursor.execute("DELETE FROM images WHERE dataset_name = ?", (dataset.name,))
            
            # Sauvegarder les images et annotations
            for image in dataset.images:
                # Sérialiser les métadonnées
                image_metadata_json = json.dumps(image.metadata)
                
                # Insérer l'image
                cursor.execute('''
                INSERT INTO images (id, dataset_name, path, width, height, source, created_at, modified_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    image.id,
                    dataset.name,
                    str(image.path),
                    image.width,
                    image.height,
                    image.source.value,
                    image.created_at.isoformat(),
                    image.modified_at.isoformat() if image.modified_at else None,
                    image_metadata_json
                ))
                
                # Insérer les annotations
                for annotation in image.annotations:
                    annotation_metadata_json = json.dumps(annotation.metadata)
                    
                    cursor.execute('''
                    INSERT INTO annotations (image_id, class_id, bbox_x, bbox_y, bbox_width, bbox_height, confidence, type, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        image.id,
                        annotation.class_id,
                        annotation.bbox.x,
                        annotation.bbox.y,
                        annotation.bbox.width,
                        annotation.bbox.height,
                        annotation.confidence,
                        annotation.type.value,
                        annotation_metadata_json
                    ))
            
            self.conn.commit()
            self.logger.info(f"Dataset {dataset.name} sauvegardé avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde du dataset: {str(e)}")
            self.conn.rollback()
            return False
    
    def load_dataset(self, name: str) -> Optional[Dataset]:
        """
        Charge un dataset depuis la base de données.
        
        Args:
            name: Nom du dataset à charger
            
        Returns:
            Dataset chargé ou None si non trouvé
        """
        try:
            cursor = self.conn.cursor()
            
            # Récupérer les informations du dataset
            cursor.execute("SELECT * FROM datasets WHERE name = ?", (name,))
            dataset_row = cursor.fetchone()
            
            if not dataset_row:
                self.logger.warning(f"Dataset {name} non trouvé dans la base de données")
                return None
            
            # Convertir en dictionnaire
            dataset_dict = dict(dataset_row)
            
            # Désérialiser les classes et métadonnées
            classes = json.loads(dataset_dict['classes'])
            metadata = json.loads(dataset_dict['metadata']) if dataset_dict['metadata'] else {}
            
            # Créer l'objet Dataset
            dataset = Dataset(
                name=dataset_dict['name'],
                version=dataset_dict['version'],
                path=Path(dataset_dict['path']),
                classes=classes,
                created_at=datetime.fromisoformat(dataset_dict['created_at']),
                metadata=metadata
            )
            
            if dataset_dict['modified_at']:
                dataset.modified_at = datetime.fromisoformat(dataset_dict['modified_at'])
            
            # Récupérer les images
            cursor.execute("SELECT * FROM images WHERE dataset_name = ?", (name,))
            image_rows = cursor.fetchall()
            
            for image_row in image_rows:
                image_dict = dict(image_row)
                
                # Désérialiser les métadonnées
                image_metadata = json.loads(image_dict['metadata']) if image_dict['metadata'] else {}
                
                # Créer l'objet Image
                image = Image(
                    id=image_dict['id'],
                    path=Path(image_dict['path']),
                    width=image_dict['width'],
                    height=image_dict['height'],
                    source=ImageSource(image_dict['source']),
                    created_at=datetime.fromisoformat(image_dict['created_at']),
                    metadata=image_metadata
                )
                
                if image_dict['modified_at']:
                    image.modified_at = datetime.fromisoformat(image_dict['modified_at'])
                
                # Récupérer les annotations
                cursor.execute("SELECT * FROM annotations WHERE image_id = ?", (image.id,))
                annotation_rows = cursor.fetchall()
                
                for annotation_row in annotation_rows:
                    anno_dict = dict(annotation_row)
                    
                    # Désérialiser les métadonnées
                    anno_metadata = json.loads(anno_dict['metadata']) if anno_dict['metadata'] else {}
                    
                    # Créer la bounding box
                    bbox = BoundingBox(
                        x=anno_dict['bbox_x'],
                        y=anno_dict['bbox_y'],
                        width=anno_dict['bbox_width'],
                        height=anno_dict['bbox_height']
                    )
                    
                    # Créer l'objet Annotation
                    annotation = Annotation(
                        class_id=anno_dict['class_id'],
                        bbox=bbox,
                        confidence=anno_dict['confidence'],
                        type=AnnotationType(anno_dict['type']),
                        metadata=anno_metadata
                    )
                    
                    # Ajouter l'annotation à l'image
                    image.add_annotation(annotation)
                
                # Ajouter l'image au dataset
                dataset.add_image(image)
            
            self.logger.info(f"Dataset {name} chargé avec succès")
            return dataset
            
        except Exception as e:
            self.logger.error(f"Échec du chargement du dataset: {str(e)}")
            return None
    
    def delete_dataset(self, name: str) -> bool:
        """
        Supprime un dataset de la base de données.
        
        Args:
            name: Nom du dataset à supprimer
            
        Returns:
            True si la suppression a réussi
        """
        try:
            cursor = self.conn.cursor()
            
            # Vérifier si le dataset existe
            cursor.execute("SELECT name FROM datasets WHERE name = ?", (name,))
            if not cursor.fetchone():
                self.logger.warning(f"Dataset {name} non trouvé, impossible de le supprimer")
                return False
            
            # Supprimer le dataset (les images et annotations seront supprimées en cascade)
            cursor.execute("DELETE FROM datasets WHERE name = ?", (name,))
            
            self.conn.commit()
            self.logger.info(f"Dataset {name} supprimé avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Échec de la suppression du dataset: {str(e)}")
            self.conn.rollback()
            return False
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """
        Liste tous les datasets disponibles.
        
        Returns:
            Liste des informations de base des datasets
        """
        try:
            cursor = self.conn.cursor()
            
            # Récupérer les datasets
            cursor.execute('''
            SELECT name, version, path, created_at, modified_at
            FROM datasets
            ORDER BY name
            ''')
            
            datasets = []
            for row in cursor.fetchall():
                # Récupérer le nombre d'images pour chaque dataset
                cursor.execute("SELECT COUNT(*) FROM images WHERE dataset_name = ?", (row['name'],))
                image_count = cursor.fetchone()[0]
                
                # Récupérer le nombre d'annotations pour chaque dataset
                cursor.execute('''
                SELECT COUNT(*) 
                FROM annotations 
                JOIN images ON annotations.image_id = images.id
                WHERE images.dataset_name = ?
                ''', (row['name'],))
                annotation_count = cursor.fetchone()[0]
                
                datasets.append({
                    'name': row['name'],
                    'version': row['version'],
                    'path': row['path'],
                    'created_at': row['created_at'],
                    'modified_at': row['modified_at'],
                    'image_count': image_count,
                    'annotation_count': annotation_count
                })
            
            self.logger.debug(f"Récupération de {len(datasets)} datasets")
            return datasets
            
        except Exception as e:
            self.logger.error(f"Échec de la récupération des datasets: {str(e)}")
            return []
    
    def apply_migrations(self) -> bool:
        """
        Applique les migrations disponibles.
        
        Returns:
            True si les migrations ont été appliquées avec succès
        """
        try:
            cursor = self.conn.cursor()
            
            # Récupérer les migrations déjà appliquées
            cursor.execute("SELECT version FROM migrations ORDER BY id")
            applied_migrations = [row['version'] for row in cursor.fetchall()]
            
            # Liste des migrations disponibles
            migrations = [
                {
                    'version': '1.0.0',
                    'description': 'Création des tables initiales',
                    'script': lambda: None  # Déjà fait dans _create_tables
                },
                {
                    'version': '1.1.0',
                    'description': 'Ajout de l\'index sur les images',
                    'script': lambda: cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_dataset ON images(dataset_name)')
                },
                {
                    'version': '1.2.0',
                    'description': 'Ajout de l\'index sur les annotations',
                    'script': lambda: cursor.execute('CREATE INDEX IF NOT EXISTS idx_annotations_image ON annotations(image_id)')
                }
            ]
            
            # Appliquer les migrations non appliquées
            for migration in migrations:
                if migration['version'] not in applied_migrations:
                    # Exécuter le script de migration
                    migration['script']()
                    
                    # Enregistrer la migration
                    cursor.execute('''
                    INSERT INTO migrations (version, description, applied_at)
                    VALUES (?, ?, ?)
                    ''', (
                        migration['version'],
                        migration['description'],
                        datetime.now().isoformat()
                    ))
                    
                    self.logger.info(f"Migration {migration['version']} appliquée")
            
            self.conn.commit()
            self.logger.info("Migrations appliquées avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Échec de l'application des migrations: {str(e)}")
            self.conn.rollback()
            return False
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des migrations.
        
        Returns:
            Liste des migrations appliquées
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
            SELECT version, description, applied_at
            FROM migrations
            ORDER BY id
            ''')
            
            migrations = []
            for row in cursor.fetchall():
                migrations.append({
                    'version': row['version'],
                    'description': row['description'],
                    'applied_at': row['applied_at']
                })
            
            return migrations
            
        except Exception as e:
            self.logger.error(f"Échec de la récupération de l'historique des migrations: {str(e)}")
            return []
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
            self.logger.debug("Connexion à la base de données fermée")