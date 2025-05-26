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
    SCHEMA_VERSION = "2.0.1"
    
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
        
        # Table des datasets (sans les classes stockées en JSON)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS datasets (
            name TEXT PRIMARY KEY,
            version TEXT NOT NULL,
            path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            modified_at TEXT,
            description TEXT,
            metadata TEXT
        )
        ''')
        
        # Table des classes (séparée pour une meilleure normalisation)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER NOT NULL,
            dataset_name TEXT NOT NULL,
            name TEXT NOT NULL,
            color TEXT,
            metadata TEXT,
            PRIMARY KEY (id, dataset_name),
            FOREIGN KEY (dataset_name) REFERENCES datasets(name) ON DELETE CASCADE
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
        
        # Table des annotations avec référence aux classes
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT NOT NULL,
            class_id INTEGER NOT NULL,
            dataset_name TEXT NOT NULL,
            bbox_x REAL NOT NULL,
            bbox_y REAL NOT NULL,
            bbox_width REAL NOT NULL,
            bbox_height REAL NOT NULL,
            confidence REAL,
            type TEXT NOT NULL,
            metadata TEXT,
            FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
            FOREIGN KEY (class_id, dataset_name) REFERENCES classes(id, dataset_name) ON DELETE CASCADE
        )
        ''')
        
        # Table des statistiques
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
        
        # Index pour optimiser les performances (créés après la migration pour éviter les problèmes)
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_dataset ON images(dataset_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_annotations_image ON annotations(image_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stats_dataset_date ON dataset_stats(dataset_name, stat_date)')
            
            # Index sur annotations avec dataset_name - créé seulement si la colonne existe
            cursor.execute("PRAGMA table_info(annotations)")
            ann_columns = [column[1] for column in cursor.fetchall()]
            if 'dataset_name' in ann_columns:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_annotations_class ON annotations(class_id, dataset_name)')
        except Exception as e:
            self.logger.warning(f"Impossible de créer certains index: {e}")
        
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
        
        current_version = row[0]
        
        # Appliquer les migrations nécessaires
        if current_version in ["1.0.0", "1.1.0", "1.2.0"] and self.SCHEMA_VERSION >= "2.0.0":
            self._migrate_v1_to_v2()
        elif current_version == "2.0.0" and self.SCHEMA_VERSION == "2.0.1":
            self._migrate_v2_0_to_v2_0_1()
        elif current_version != self.SCHEMA_VERSION:
            self.logger.warning(f"Version de schéma non reconnue: {current_version}")
    
    def _migrate_v1_to_v2(self):
        """Migration de la version 1.x vers 2.0.0: Séparer les classes en table distincte."""
        cursor = self.conn.cursor()
        
        try:
            self.logger.info("Début de migration v1.x -> v2.0.0")
            
            # 1. Créer la nouvelle table classes
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER NOT NULL,
                dataset_name TEXT NOT NULL,
                name TEXT NOT NULL,
                color TEXT,
                metadata TEXT,
                PRIMARY KEY (id, dataset_name),
                FOREIGN KEY (dataset_name) REFERENCES datasets(name) ON DELETE CASCADE
            )
            ''')
            
            # 2. Migrer les classes depuis le JSON vers la nouvelle table
            cursor.execute("SELECT name, classes FROM datasets WHERE classes IS NOT NULL")
            datasets_with_classes = cursor.fetchall()
            
            for dataset_name, classes_json in datasets_with_classes:
                if classes_json:
                    import json
                    try:
                        classes = json.loads(classes_json)
                        for class_id, class_name in classes.items():
                            cursor.execute('''
                            INSERT OR REPLACE INTO classes (id, dataset_name, name)
                            VALUES (?, ?, ?)
                            ''', (int(class_id), dataset_name, class_name))
                    except (json.JSONDecodeError, ValueError) as e:
                        self.logger.warning(f"Impossible de migrer les classes pour {dataset_name}: {e}")
            
            # 3. Ajouter dataset_name aux annotations
            cursor.execute("PRAGMA table_info(annotations)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'dataset_name' not in columns:
                # Ajouter la colonne dataset_name
                cursor.execute("ALTER TABLE annotations ADD COLUMN dataset_name TEXT")
                
                # Remplir la colonne avec les valeurs correspondantes
                cursor.execute('''
                UPDATE annotations 
                SET dataset_name = (
                    SELECT i.dataset_name 
                    FROM images i 
                    WHERE i.id = annotations.image_id
                )
                WHERE dataset_name IS NULL
                ''')
            
            # 4. Ajouter description au lieu de classes dans datasets
            cursor.execute("PRAGMA table_info(datasets)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'description' not in columns:
                cursor.execute("ALTER TABLE datasets ADD COLUMN description TEXT")
            
            # 5. Supprimer la colonne classes (SQLite ne supporte pas DROP COLUMN directement)
            # On va créer une nouvelle table et migrer les données
            cursor.execute('''
            CREATE TABLE datasets_new (
                name TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT,
                description TEXT,
                metadata TEXT
            )
            ''')
            
            cursor.execute('''
            INSERT INTO datasets_new (name, version, path, created_at, modified_at, description, metadata)
            SELECT name, version, path, created_at, modified_at, 
                   CASE WHEN description IS NOT NULL THEN description ELSE '' END,
                   metadata
            FROM datasets
            ''')
            
            cursor.execute("DROP TABLE datasets")
            cursor.execute("ALTER TABLE datasets_new RENAME TO datasets")
            
            # 6. Créer les index (après avoir ajouté toutes les colonnes)
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_dataset ON images(dataset_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_annotations_image ON annotations(image_id)')
            
            # Vérifier que dataset_name existe avant de créer l'index
            cursor.execute("PRAGMA table_info(annotations)")
            ann_columns = [column[1] for column in cursor.fetchall()]
            if 'dataset_name' in ann_columns:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_annotations_class ON annotations(class_id, dataset_name)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stats_dataset_date ON dataset_stats(dataset_name, stat_date)')
            
            # 7. Enregistrer la migration
            cursor.execute('''
            INSERT INTO migrations (version, description, applied_at)
            VALUES (?, ?, ?)
            ''', ("2.0.0", "Separate classes table and schema improvements", datetime.now().isoformat()))
            
            self.conn.commit()
            self.logger.info("Migration v1.0.0 -> v2.0.0 terminée avec succès")
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Échec de la migration v1.x -> v2.0.0: {str(e)}")
            raise
    
    def _migrate_v2_0_to_v2_0_1(self):
        """Migration mineure pour corriger les index et colonnes manquantes."""
        cursor = self.conn.cursor()
        
        try:
            self.logger.info("Début de migration v2.0.0 -> v2.0.1")
            
            # Vérifier et ajouter dataset_name aux annotations si manquant
            cursor.execute("PRAGMA table_info(annotations)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'dataset_name' not in columns:
                self.logger.info("Ajout de la colonne dataset_name aux annotations")
                cursor.execute("ALTER TABLE annotations ADD COLUMN dataset_name TEXT")
                
                # Remplir la colonne avec les valeurs correspondantes
                cursor.execute('''
                UPDATE annotations 
                SET dataset_name = (
                    SELECT i.dataset_name 
                    FROM images i 
                    WHERE i.id = annotations.image_id
                )
                WHERE dataset_name IS NULL
                ''')
            
            # Créer les index manquants
            try:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_annotations_class ON annotations(class_id, dataset_name)')
                self.logger.info("Index annotations créé")
            except Exception as e:
                self.logger.warning(f"Impossible de créer l'index annotations: {e}")
            
            # Enregistrer la migration
            cursor.execute('''
            INSERT INTO migrations (version, description, applied_at)
            VALUES (?, ?, ?)
            ''', ("2.0.1", "Fix missing columns and indexes", datetime.now().isoformat()))
            
            self.conn.commit()
            self.logger.info("Migration v2.0.0 -> v2.0.1 terminée avec succès")
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Échec de la migration v2.0.0 -> v2.0.1: {str(e)}")
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
        Sauvegarde un dataset dans la base de données avec la nouvelle structure.
        
        Args:
            dataset: Dataset à sauvegarder
            
        Returns:
            True si la sauvegarde a réussi
        """
        try:
            cursor = self.conn.cursor()
            
            # Sérialiser les métadonnées en JSON (avec gestion des valeurs None)
            metadata_json = json.dumps(dataset.metadata if dataset.metadata else {})
            
            # Vérifier si le dataset existe déjà
            cursor.execute("SELECT name FROM datasets WHERE name = ?", (dataset.name,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # Mettre à jour le dataset existant
                cursor.execute('''
                UPDATE datasets
                SET version = ?, path = ?, modified_at = ?, description = ?, metadata = ?
                WHERE name = ?
                ''', (
                    dataset.version,
                    str(dataset.path),
                    datetime.now().isoformat(),
                    getattr(dataset, 'description', ''),
                    metadata_json,
                    dataset.name
                ))
                
                # Supprimer les anciennes classes, images et annotations (cascade delete)
                cursor.execute("DELETE FROM classes WHERE dataset_name = ?", (dataset.name,))
                cursor.execute("DELETE FROM images WHERE dataset_name = ?", (dataset.name,))
            else:
                # Insérer un nouveau dataset
                cursor.execute('''
                INSERT INTO datasets (name, version, path, created_at, modified_at, description, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    dataset.name,
                    dataset.version,
                    str(dataset.path),
                    dataset.created_at.isoformat(),
                    datetime.now().isoformat() if dataset.modified_at else None,
                    getattr(dataset, 'description', ''),
                    metadata_json
                ))
            
            # Sauvegarder les classes
            for class_id, class_name in dataset.classes.items():
                cursor.execute('''
                INSERT INTO classes (id, dataset_name, name)
                VALUES (?, ?, ?)
                ''', (class_id, dataset.name, class_name))
            
            # Sauvegarder les images et annotations
            for image in dataset.images:
                # Sérialiser les métadonnées (avec gestion des valeurs None)
                image_metadata_json = json.dumps(image.metadata if image.metadata else {})
                
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
                    annotation_metadata_json = json.dumps(annotation.metadata if annotation.metadata else {})
                    
                    cursor.execute('''
                    INSERT INTO annotations (image_id, class_id, dataset_name, bbox_x, bbox_y, bbox_width, bbox_height, confidence, type, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        image.id,
                        annotation.class_id,
                        dataset.name,
                        annotation.bbox.x,
                        annotation.bbox.y,
                        annotation.bbox.width,
                        annotation.bbox.height,
                        annotation.confidence,
                        annotation.type.value,  # Toujours sauvegarder le type enum, les métadonnées vont dans metadata
                        annotation_metadata_json
                    ))
            
            # Mettre à jour les statistiques
            try:
                self._update_dataset_stats(dataset)
            except Exception as e:
                self.logger.warning(f"Impossible de mettre à jour les statistiques: {e}")
            
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
        Charge un dataset depuis la base de données avec la nouvelle structure.
        
        Args:
            name: Nom du dataset à charger
            
        Returns:
            Dataset chargé ou None si non trouvé
        """
        try:
            cursor = self.conn.cursor()
            
            # Récupérer les informations du dataset (ordre explicite des colonnes)
            cursor.execute("SELECT name, version, path, created_at, modified_at, description, metadata FROM datasets WHERE name = ?", (name,))
            dataset_row = cursor.fetchone()
            
            if not dataset_row:
                self.logger.warning(f"Dataset {name} non trouvé dans la base de données")
                return None
            
            # Convertir en dictionnaire (ordre explicite: name, version, path, created_at, modified_at, description, metadata)
            dataset_dict = {
                'name': dataset_row[0],
                'version': dataset_row[1], 
                'path': dataset_row[2],
                'created_at': dataset_row[3],
                'modified_at': dataset_row[4],
                'description': dataset_row[5],
                'metadata': dataset_row[6]
            }
            
            # Récupérer les classes depuis la table classes
            cursor.execute("SELECT id, name FROM classes WHERE dataset_name = ? ORDER BY id", (name,))
            classes_rows = cursor.fetchall()
            classes = {row[0]: row[1] for row in classes_rows}
            
            # Désérialiser les métadonnées (robuste aux valeurs None/vides)
            metadata_str = dataset_dict['metadata']
            if metadata_str and metadata_str.strip():
                try:
                    metadata = json.loads(metadata_str)
                except json.JSONDecodeError:
                    self.logger.warning(f"Métadonnées JSON invalides pour dataset {name}, utilisation d'un dict vide")
                    metadata = {}
            else:
                metadata = {}
            
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
            
            # Ajouter la description si disponible
            if dataset_dict.get('description'):
                dataset.description = dataset_dict['description']
            
            # Récupérer les images
            cursor.execute("SELECT id, dataset_name, path, width, height, source, created_at, modified_at, metadata FROM images WHERE dataset_name = ?", (name,))
            image_rows = cursor.fetchall()
            
            for image_row in image_rows:
                # Ordre explicite: id, dataset_name, path, width, height, source, created_at, modified_at, metadata
                image_dict = {
                    'id': image_row[0],
                    'dataset_name': image_row[1],
                    'path': image_row[2],
                    'width': image_row[3],
                    'height': image_row[4],
                    'source': image_row[5],
                    'created_at': image_row[6],
                    'modified_at': image_row[7],
                    'metadata': image_row[8]
                }
                
                # Désérialiser les métadonnées (robuste aux valeurs None/vides)
                metadata_str = image_dict['metadata']
                if metadata_str and metadata_str.strip():
                    try:
                        image_metadata = json.loads(metadata_str)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Métadonnées JSON invalides pour image {image_dict['id']}, utilisation d'un dict vide")
                        image_metadata = {}
                else:
                    image_metadata = {}
                
                # Récupérer les annotations pour cette image (ordre explicite des colonnes)
                cursor.execute("""
                    SELECT id, image_id, class_id, bbox_x, bbox_y, bbox_width, bbox_height, confidence, type, metadata, dataset_name 
                    FROM annotations WHERE image_id = ?
                """, (image_dict['id'],))
                annotation_rows = cursor.fetchall()
                
                annotations = []
                for ann_row in annotation_rows:
                    # Ordre explicite: id, image_id, class_id, bbox_x, bbox_y, bbox_width, bbox_height, confidence, type, metadata, dataset_name
                    ann_dict = {
                        'id': ann_row[0],
                        'image_id': ann_row[1],
                        'class_id': ann_row[2],
                        'bbox_x': ann_row[3],
                        'bbox_y': ann_row[4],
                        'bbox_width': ann_row[5],
                        'bbox_height': ann_row[6],
                        'confidence': ann_row[7],
                        'type': ann_row[8],
                        'metadata': ann_row[9],
                        'dataset_name': ann_row[10]
                    }
                    
                    from src.models.annotation import BoundingBox, Annotation
                    from src.models.enums import AnnotationType
                    
                    # Créer la bounding box
                    bbox = BoundingBox(
                        x=ann_dict['bbox_x'],
                        y=ann_dict['bbox_y'],
                        width=ann_dict['bbox_width'],
                        height=ann_dict['bbox_height']
                    )
                    
                    # Gérer le type d'annotation - peut contenir des métadonnées Mapillary
                    annotation_type = AnnotationType.BBOX  # Valeur par défaut
                    
                    # Désérialiser les métadonnées (robuste aux valeurs None/vides)
                    metadata_str = ann_dict['metadata']
                    if metadata_str and metadata_str.strip():
                        try:
                            annotation_metadata = json.loads(metadata_str)
                        except json.JSONDecodeError:
                            self.logger.warning(f"Métadonnées JSON invalides pour annotation, utilisation d'un dict vide")
                            annotation_metadata = {}
                    else:
                        annotation_metadata = {}
                    
                    # Si le type contient du JSON (données Mapillary), l'extraire
                    type_value = ann_dict['type']
                    try:
                        # Tenter de parser comme AnnotationType standard
                        annotation_type = AnnotationType(type_value)
                    except ValueError:
                        # Si ça échoue, c'est probablement du JSON Mapillary
                        try:
                            mapillary_data = json.loads(type_value)
                            # Déplacer les données Mapillary vers metadata
                            annotation_metadata.update(mapillary_data)
                            annotation_type = AnnotationType.BBOX  # Type par défaut pour Mapillary
                        except json.JSONDecodeError:
                            # Si ce n'est pas du JSON non plus, utiliser BBOX par défaut
                            self.logger.warning(f"Type d'annotation non reconnu: {type_value}, utilisation de BBOX par défaut")
                            annotation_type = AnnotationType.BBOX
                    
                    # Créer l'annotation
                    annotation = Annotation(
                        class_id=ann_dict['class_id'],
                        bbox=bbox,
                        confidence=ann_dict['confidence'],
                        type=annotation_type,
                        metadata=annotation_metadata
                    )
                    
                    annotations.append(annotation)
                
                # Créer l'image
                from src.models.enums import ImageSource
                
                image = Image(
                    id=image_dict['id'],
                    path=image_dict['path'],
                    width=image_dict['width'],
                    height=image_dict['height'],
                    source=ImageSource(image_dict['source']),
                    annotations=annotations,
                    metadata=image_metadata,
                    created_at=datetime.fromisoformat(image_dict['created_at'])
                )
                
                if image_dict['modified_at']:
                    image.modified_at = datetime.fromisoformat(image_dict['modified_at'])
                
                dataset.add_image(image)
            
            self.logger.info(f"Dataset {name} chargé avec succès ({len(dataset.images)} images)")
            return dataset
            
        except Exception as e:
            self.logger.error(f"Échec du chargement du dataset {name}: {str(e)}")
            return None
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """
        Liste tous les datasets disponibles dans la base de données.
        
        Returns:
            Liste des informations de base des datasets
        """
        try:
            cursor = self.conn.cursor()
            
            # Récupérer les informations de base des datasets avec statistiques
            cursor.execute('''
            SELECT 
                d.name,
                d.version,
                d.description,
                d.created_at,
                d.modified_at,
                COUNT(DISTINCT i.id) as image_count,
                COUNT(a.id) as annotation_count
            FROM datasets d
            LEFT JOIN images i ON d.name = i.dataset_name
            LEFT JOIN annotations a ON i.id = a.image_id
            GROUP BY d.name, d.version, d.description, d.created_at, d.modified_at
            ORDER BY d.modified_at DESC
            ''')
            
            results = []
            for row in cursor.fetchall():
                dataset_info = {
                    'name': row[0],
                    'version': row[1],
                    'description': row[2] or '',
                    'created_at': row[3],
                    'modified_at': row[4],
                    'image_count': row[5],
                    'annotation_count': row[6]
                }
                
                # Récupérer les classes pour ce dataset
                cursor.execute("SELECT id, name FROM classes WHERE dataset_name = ? ORDER BY id", (row[0],))
                classes = {class_row[0]: class_row[1] for class_row in cursor.fetchall()}
                dataset_info['classes'] = classes
                dataset_info['class_count'] = len(classes)
                
                results.append(dataset_info)
            
            self.logger.debug(f"Récupération de {len(results)} datasets")
            return results
            
        except Exception as e:
            self.logger.error(f"Échec de la récupération des datasets: {str(e)}")
            return []
    
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
            
            # Vérifier que le dataset existe
            cursor.execute("SELECT name FROM datasets WHERE name = ?", (name,))
            if not cursor.fetchone():
                self.logger.warning(f"Dataset {name} non trouvé")
                return False
            
            # Supprimer le dataset (les foreign keys CASCADE s'occupent du reste)
            cursor.execute("DELETE FROM datasets WHERE name = ?", (name,))
            
            self.conn.commit()
            self.logger.info(f"Dataset {name} supprimé avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Échec de la suppression du dataset {name}: {str(e)}")
            self.conn.rollback()
            return False
    
    def get_dataset_statistics(self, name: str) -> Dict[str, Any]:
        """
        Récupère les statistiques détaillées d'un dataset.
        
        Args:
            name: Nom du dataset
            
        Returns:
            Dictionnaire des statistiques
        """
        try:
            cursor = self.conn.cursor()
            
            # Statistiques de base
            cursor.execute('''
            SELECT 
                COUNT(DISTINCT i.id) as image_count,
                COUNT(a.id) as annotation_count,
                AVG(i.width) as avg_width,
                AVG(i.height) as avg_height
            FROM images i
            LEFT JOIN annotations a ON i.id = a.image_id
            WHERE i.dataset_name = ?
            ''', (name,))
            
            row = cursor.fetchone()
            stats = {
                'image_count': row[0] if row[0] else 0,
                'annotation_count': row[1] if row[1] else 0,
                'avg_width': float(row[2]) if row[2] else 0,
                'avg_height': float(row[3]) if row[3] else 0
            }
            
            # Distribution par classe
            cursor.execute('''
            SELECT c.id, c.name, COUNT(a.id) as count
            FROM classes c
            LEFT JOIN annotations a ON c.id = a.class_id AND c.dataset_name = a.dataset_name
            WHERE c.dataset_name = ?
            GROUP BY c.id, c.name
            ORDER BY c.id
            ''', (name,))
            
            class_distribution = {}
            for row in cursor.fetchall():
                class_distribution[row[0]] = {
                    'name': row[1],
                    'count': row[2]
                }
            
            stats['class_distribution'] = class_distribution
            stats['class_count'] = len(class_distribution)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Échec de récupération des statistiques pour {name}: {str(e)}")
            return {}
    
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