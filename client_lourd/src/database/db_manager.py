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
    
    # Version du schéma - incrémenter à chaque modification de la structure
    SCHEMA_VERSION = "1.0.0"
    
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
        
        # Vérifier les migrations nécessaires
        self._check_migrations()
    
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
        
        # Table des migrations pour suivre les changements de schéma
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            description TEXT,
            applied_at TEXT NOT NULL
        )
        ''')
        
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
        
        self.conn.commit()
    
    def _check_migrations(self):
        """Vérifie si des migrations sont nécessaires et les applique."""
        cursor = self.conn.cursor()
        
        # Vérifier si la table de migrations existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'")
        if not cursor.fetchone():
            # La table n'existe pas, probablement une nouvelle base de données
            self._create_tables()
            # Enregistrer la migration initiale
            cursor.execute('''
            INSERT INTO migrations (version, description, applied_at)
            VALUES (?, ?, ?)
            ''', (self.SCHEMA_VERSION, "Initial schema", datetime.now().isoformat()))
            self.conn.commit()
            return
        
        # Récupérer la dernière version appliquée
        cursor.execute("SELECT version FROM migrations ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            # Aucune migration enregistrée, enregistrer la version actuelle
            cursor.execute('''
            INSERT INTO migrations (version, description, applied_at)
            VALUES (?, ?, ?)
            ''', (self.SCHEMA_VERSION, "Initial schema", datetime.now().isoformat()))
            self.conn.commit()
            return
        
        last_version = row[0]
        
        # Liste des migrations à appliquer
        migrations = [
            {
                "version": "1.0.0",
                "description": "Initial schema",
                "action": lambda: None  # Pas d'action, déjà fait dans _create_tables
            },
            {
                "version": "1.1.0",
                "description": "Add indexes",
                "action": self._migration_add_indexes
            },
            {
                "version": "1.2.0",
                "description": "Add statistics table",
                "action": self._migration_add_stats_table
            }
        ]
        
        # Trouver où nous en sommes dans les migrations
        last_index = -1
        for i, migration in enumerate(migrations):
            if migration["version"] == last_version:
                last_index = i
                break
        
        # Appliquer les migrations suivantes
        if last_index < len(migrations) - 1:
            for migration in migrations[last_index + 1:]:
                self.logger.info(f"Application de la migration {migration['version']}: {migration['description']}")
                
                try:
                    # Exécuter l'action de migration
                    migration["action"]()
                    
                    # Enregistrer la migration
                    cursor.execute('''
                    INSERT INTO migrations (version, description, applied_at)
                    VALUES (?, ?, ?)
                    ''', (migration["version"], migration["description"], datetime.now().isoformat()))
                    
                    self.conn.commit()
                    self.logger.info(f"Migration {migration['version']} appliquée avec succès")
                    
                except Exception as e:
                    self.conn.rollback()
                    self.logger.error(f"Échec de la migration {migration['version']}: {str(e)}")
                    raise
    
    def _migration_add_indexes(self):
        """Migration: Ajoute des index pour améliorer les performances."""
        cursor = self.conn.cursor()
        
        # Ajouter des index pour améliorer les performances des requêtes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_dataset ON images(dataset_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_annotations_image ON annotations(image_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_annotations_class ON annotations(class_id)")
        
        self.conn.commit()
    
    def _migration_add_stats_table(self):
        """Migration: Ajoute une table pour les statistiques."""
        cursor = self.conn.cursor()
        
        # Créer la table des statistiques de dataset
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS dataset_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_name TEXT NOT NULL,
            stat_date TEXT NOT NULL,
            image_count INTEGER NOT NULL DEFAULT 0,
            annotation_count INTEGER NOT NULL DEFAULT 0,
            class_distribution TEXT,
            FOREIGN KEY (dataset_name) REFERENCES datasets(name) ON DELETE CASCADE
        )
        ''')
        
        # Créer un index pour accélérer les recherches par date et dataset
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_dataset_date ON dataset_stats(dataset_name, stat_date)")
        
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
            
            # Mettre à jour les statistiques
            self._update_dataset_stats(dataset)
            
            self.conn.commit()
            self.logger.info(f"Dataset {dataset.name} sauvegardé avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde du dataset: {str(e)}")
            self.conn.rollback()
            return False
    
    def _update_dataset_stats(self, dataset: Dataset):
        """
        Met à jour les statistiques du dataset.
        
        Args:
            dataset: Dataset à analyser
        """
        cursor = self.conn.cursor()
        
        # Calculer les statistiques
        image_count = len(dataset.images)
        annotation_count = sum(len(img.annotations) for img in dataset.images)
        
        # Compter les annotations par classe
        class_distribution = {}
        for image in dataset.images:
            for ann in image.annotations:
                class_id = ann.class_id
                if class_id not in class_distribution:
                    class_distribution[class_id] = 0
                class_distribution[class_id] += 1
        
        # Insérer les statistiques
        cursor.execute('''
        INSERT INTO dataset_stats (dataset_name, stat_date, image_count, annotation_count, class_distribution)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            dataset.name,
            datetime.now().date().isoformat(),
            image_count,
            annotation_count,
            json.dumps(class_distribution)
        ))
    
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
            self._check_migrations()
            self.logger.info("Migrations appliquées avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Échec de l'application des migrations: {str(e)}")
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
    
    def backup_database(self, backup_path: Optional[Path] = None) -> Path:
        """
        Crée une sauvegarde de la base de données.
        
        Args:
            backup_path: Chemin de la sauvegarde (optionnel)
            
        Returns:
            Chemin de la sauvegarde
        """
        try:
            from datetime import datetime
            import shutil
            
            # Déterminer le chemin de sauvegarde
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.db_path.parent / f"backup_{timestamp}_{self.db_path.name}"
            
            # Créer le répertoire parent si nécessaire
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Créer une sauvegarde
            self.conn.close()  # Fermer la connexion pour libérer le fichier
            shutil.copy2(self.db_path, backup_path)
            self._init_connection()  # Ré-ouvrir la connexion
            
            self.logger.info(f"Base de données sauvegardée: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde de la base de données: {str(e)}")
            # Assurer que la connexion est rouverte en cas d'erreur
            self._init_connection()
            raise
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
            self.logger.debug("Connexion à la base de données fermée")