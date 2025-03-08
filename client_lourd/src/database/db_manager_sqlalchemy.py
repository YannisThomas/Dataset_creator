# src/database/db_manager_sqlalchemy.py

from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import json
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref, Session
from alembic.config import Config
from alembic import command
import os

from src.models import Dataset, Image, Annotation, BoundingBox
from src.models.enums import ImageSource, AnnotationType
from src.utils.logger import Logger
from src.core.exceptions import DatabaseError

# Création du modèle de base SQLAlchemy
Base = declarative_base()

# Définition des modèles SQLAlchemy
class DatasetModel(Base):
    """Modèle SQLAlchemy pour les datasets."""
    __tablename__ = 'datasets'
    
    name = sa.Column(sa.String, primary_key=True)
    version = sa.Column(sa.String, nullable=False)
    path = sa.Column(sa.String, nullable=False)
    classes = sa.Column(sa.JSON, nullable=False)  # Stocké sous forme JSON
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.now)
    modified_at = sa.Column(sa.DateTime, nullable=True)
    metadata = sa.Column(sa.JSON, nullable=True)  # Stocké sous forme JSON
    
    # Relation avec les images
    images = relationship("ImageModel", back_populates="dataset", cascade="all, delete-orphan")


class ImageModel(Base):
    """Modèle SQLAlchemy pour les images."""
    __tablename__ = 'images'
    
    id = sa.Column(sa.String, primary_key=True)
    dataset_name = sa.Column(sa.String, sa.ForeignKey('datasets.name', ondelete='CASCADE'), nullable=False)
    path = sa.Column(sa.String, nullable=False)
    width = sa.Column(sa.Integer, nullable=False)
    height = sa.Column(sa.Integer, nullable=False)
    source = sa.Column(sa.String, nullable=False)
    created_at = sa.Column(sa.DateTime, nullable=False, default=datetime.now)
    modified_at = sa.Column(sa.DateTime, nullable=True)
    metadata = sa.Column(sa.JSON, nullable=True)  # Stocké sous forme JSON
    
    # Relations
    dataset = relationship("DatasetModel", back_populates="images")
    annotations = relationship("AnnotationModel", back_populates="image", cascade="all, delete-orphan")


class AnnotationModel(Base):
    """Modèle SQLAlchemy pour les annotations."""
    __tablename__ = 'annotations'
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    image_id = sa.Column(sa.String, sa.ForeignKey('images.id', ondelete='CASCADE'), nullable=False)
    class_id = sa.Column(sa.Integer, nullable=False)
    bbox_x = sa.Column(sa.Float, nullable=False)
    bbox_y = sa.Column(sa.Float, nullable=False)
    bbox_width = sa.Column(sa.Float, nullable=False)
    bbox_height = sa.Column(sa.Float, nullable=False)
    confidence = sa.Column(sa.Float, nullable=True)
    type = sa.Column(sa.String, nullable=False, default='bbox')
    metadata = sa.Column(sa.JSON, nullable=True)  # Stocké sous forme JSON
    
    # Relation avec l'image
    image = relationship("ImageModel", back_populates="annotations")
    

class MigrationModel(Base):
    """Modèle SQLAlchemy pour les migrations."""
    __tablename__ = 'migrations'
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    version = sa.Column(sa.String, nullable=False)
    description = sa.Column(sa.String, nullable=True)
    applied_at = sa.Column(sa.DateTime, nullable=False, default=datetime.now)


class SQLAlchemyDatabaseManager:
    """
    Gestionnaire de base de données utilisant SQLAlchemy pour la persistance.
    
    Fournit une couche d'abstraction pour interagir avec la base de données
    et gérer les migrations avec Alembic.
    """
    
    def __init__(
        self, 
        db_path: Optional[Path] = None,
        logger: Optional[Logger] = None,
        echo: bool = False
    ):
        """
        Initialise le gestionnaire de base de données.
        
        Args:
            db_path: Chemin vers le fichier de base de données SQLite
            logger: Gestionnaire de logs
            echo: Activer l'affichage des requêtes SQL
        """
        self.logger = logger or Logger()
        
        # Définir le chemin de la base de données
        self.db_path = db_path or Path("data/yolo_datasets.db")
        
        # Créer le répertoire parent si nécessaire
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Créer l'URL de la base de données
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Créer le moteur SQLAlchemy
        self.engine = sa.create_engine(self.db_url, echo=echo)
        
        # Créer une session
        self.Session = sessionmaker(bind=self.engine)
        
        # Créer les tables si elles n'existent pas
        self._create_tables()
        
    def _create_tables(self):
        """Crée les tables de la base de données si elles n'existent pas."""
        Base.metadata.create_all(self.engine)
        self.logger.info("Tables de base de données créées ou vérifiées")
    
    def _get_session(self) -> Session:
        """
        Crée et retourne une nouvelle session.
        
        Returns:
            Session SQLAlchemy
        """
        return self.Session()
    
    def save_dataset(self, dataset: Dataset) -> bool:
        """
        Sauvegarde un dataset dans la base de données.
        
        Args:
            dataset: Dataset à sauvegarder
            
        Returns:
            True si la sauvegarde a réussi
            
        Raises:
            DatabaseError: Si la sauvegarde échoue
        """
        try:
            session = self._get_session()
            
            try:
                # Vérifier si le dataset existe déjà
                existing = session.query(DatasetModel).filter_by(name=dataset.name).first()
                
                if existing:
                    # Mise à jour des champs du dataset
                    existing.version = dataset.version
                    existing.path = str(dataset.path)
                    existing.classes = dataset.classes
                    existing.modified_at = datetime.now()
                    existing.metadata = dataset.metadata
                    
                    # Supprimer toutes les images existantes (cascade sur les annotations)
                    session.query(ImageModel).filter_by(dataset_name=dataset.name).delete()
                else:
                    # Créer un nouveau dataset
                    dataset_model = DatasetModel(
                        name=dataset.name,
                        version=dataset.version,
                        path=str(dataset.path),
                        classes=dataset.classes,
                        created_at=dataset.created_at,
                        modified_at=dataset.modified_at,
                        metadata=dataset.metadata
                    )
                    session.add(dataset_model)
                
                # Ajouter toutes les images et annotations
                for image in dataset.images:
                    # Créer le modèle d'image
                    image_model = ImageModel(
                        id=image.id,
                        dataset_name=dataset.name,
                        path=str(image.path),
                        width=image.width,
                        height=image.height,
                        source=image.source.value,
                        created_at=image.created_at,
                        modified_at=image.modified_at,
                        metadata=image.metadata
                    )
                    
                    # Ajouter les annotations
                    for annotation in image.annotations:
                        # Créer le modèle d'annotation
                        annotation_model = AnnotationModel(
                            image_id=image.id,
                            class_id=annotation.class_id,
                            bbox_x=annotation.bbox.x,
                            bbox_y=annotation.bbox.y,
                            bbox_width=annotation.bbox.width,
                            bbox_height=annotation.bbox.height,
                            confidence=annotation.confidence,
                            type=annotation.type.value,
                            metadata=annotation.metadata
                        )
                        
                        # Ajouter l'annotation à l'image
                        image_model.annotations.append(annotation_model)
                    
                    # Ajouter l'image au dataset (ou à la session directement si mise à jour)
                    if existing:
                        session.add(image_model)
                    else:
                        dataset_model.images.append(image_model)
                
                # Valider les changements
                session.commit()
                
                self.logger.info(f"Dataset {dataset.name} sauvegardé avec succès")
                return True
                
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Échec de sauvegarde du dataset: {str(e)}")
            raise DatabaseError(f"Impossible de sauvegarder le dataset: {str(e)}")
    
    def load_dataset(self, name: str) -> Optional[Dataset]:
        """
        Charge un dataset depuis la base de données.
        
        Args:
            name: Nom du dataset à charger
            
        Returns:
            Dataset chargé ou None si non trouvé
            
        Raises:
            DatabaseError: Si le chargement échoue
        """
        try:
            session = self._get_session()
            
            try:
                # Récupérer le dataset avec ses images et annotations (jointure)
                dataset_model = (
                    session.query(DatasetModel)
                    .filter(DatasetModel.name == name)
                    .first()
                )
                
                if not dataset_model:
                    self.logger.warning(f"Dataset {name} non trouvé")
                    return None
                
                # Créer l'objet Dataset
                dataset = Dataset(
                    name=dataset_model.name,
                    version=dataset_model.version,
                    path=Path(dataset_model.path),
                    classes=dataset_model.classes,
                    created_at=dataset_model.created_at,
                    metadata=dataset_model.metadata or {}
                )
                
                if dataset_model.modified_at:
                    dataset.modified_at = dataset_model.modified_at
                
                # Charger les images et annotations
                image_models = (
                    session.query(ImageModel)
                    .filter(ImageModel.dataset_name == name)
                    .all()
                )
                
                for image_model in image_models:
                    # Créer l'objet Image
                    image = Image(
                        id=image_model.id,
                        path=Path(image_model.path),
                        width=image_model.width,
                        height=image_model.height,
                        source=ImageSource(image_model.source),
                        created_at=image_model.created_at,
                        metadata=image_model.metadata or {}
                    )
                    
                    if image_model.modified_at:
                        image.modified_at = image_model.modified_at
                    
                    # Charger les annotations
                    for annotation_model in image_model.annotations:
                        # Créer la bounding box
                        bbox = BoundingBox(
                            x=annotation_model.bbox_x,
                            y=annotation_model.bbox_y,
                            width=annotation_model.bbox_width,
                            height=annotation_model.bbox_height
                        )
                        
                        # Créer l'annotation
                        annotation = Annotation(
                            class_id=annotation_model.class_id,
                            bbox=bbox,
                            confidence=annotation_model.confidence,
                            type=AnnotationType(annotation_model.type),
                            metadata=annotation_model.metadata or {}
                        )
                        
                        # Ajouter l'annotation à l'image
                        image.add_annotation(annotation)
                    
                    # Ajouter l'image au dataset
                    dataset.add_image(image)
                
                self.logger.info(f"Dataset {name} chargé avec succès")
                return dataset
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Échec du chargement du dataset: {str(e)}")
            raise DatabaseError(f"Impossible de charger le dataset: {str(e)}")
    
    def delete_dataset(self, name: str) -> bool:
        """
        Supprime un dataset de la base de données.
        
        Args:
            name: Nom du dataset à supprimer
            
        Returns:
            True si la suppression a réussi
            
        Raises:
            DatabaseError: Si la suppression échoue
        """
        try:
            session = self._get_session()
            
            try:
                # Vérifier si le dataset existe
                dataset = session.query(DatasetModel).filter_by(name=name).first()
                if not dataset:
                    self.logger.warning(f"Dataset {name} non trouvé, impossible de le supprimer")
                    return False
                
                # Supprimer le dataset (cascade sur les images et annotations)
                session.delete(dataset)
                session.commit()
                
                self.logger.info(f"Dataset {name} supprimé avec succès")
                return True
                
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Échec de suppression du dataset: {str(e)}")
            raise DatabaseError(f"Impossible de supprimer le dataset: {str(e)}")
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """
        Liste tous les datasets disponibles.
        
        Returns:
            Liste des informations de base des datasets
            
        Raises:
            DatabaseError: Si la récupération échoue
        """
        try:
            session = self._get_session()
            
            try:
                # Requête pour compter les images et annotations
                dataset_stats = {}
                
                # Compter les images par dataset
                image_counts = (
                    session.query(
                        ImageModel.dataset_name,
                        sa.func.count(ImageModel.id).label('image_count')
                    )
                    .group_by(ImageModel.dataset_name)
                    .all()
                )
                
                for dataset_name, count in image_counts:
                    if dataset_name not in dataset_stats:
                        dataset_stats[dataset_name] = {'image_count': 0, 'annotation_count': 0}
                    dataset_stats[dataset_name]['image_count'] = count
                
                # Compter les annotations par dataset
                annotation_counts = (
                    session.query(
                        ImageModel.dataset_name,
                        sa.func.count(AnnotationModel.id).label('annotation_count')
                    )
                    .join(AnnotationModel, ImageModel.id == AnnotationModel.image_id)
                    .group_by(ImageModel.dataset_name)
                    .all()
                )
                
                for dataset_name, count in annotation_counts:
                    if dataset_name not in dataset_stats:
                        dataset_stats[dataset_name] = {'image_count': 0, 'annotation_count': 0}
                    dataset_stats[dataset_name]['annotation_count'] = count
                
                # Récupérer les informations des datasets
                datasets = []
                
                dataset_models = session.query(DatasetModel).all()
                for dataset_model in dataset_models:
                    datasets.append({
                        'name': dataset_model.name,
                        'version': dataset_model.version,
                        'path': dataset_model.path,
                        'created_at': dataset_model.created_at.isoformat(),
                        'modified_at': dataset_model.modified_at.isoformat() if dataset_model.modified_at else None,
                        'image_count': dataset_stats.get(dataset_model.name, {}).get('image_count', 0),
                        'annotation_count': dataset_stats.get(dataset_model.name, {}).get('annotation_count', 0),
                        'class_count': len(dataset_model.classes)
                    })
                
                self.logger.info(f"Récupération de {len(datasets)} datasets")
                return datasets
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Échec de récupération des datasets: {str(e)}")
            raise DatabaseError(f"Impossible de lister les datasets: {str(e)}")
    
    def apply_migrations(self) -> bool:
        """
        Applique les migrations disponibles.
        
        Returns:
            True si les migrations ont été appliquées avec succès
            
        Raises:
            DatabaseError: Si l'application des migrations échoue
        """
        try:
            # Créer une configuration Alembic
            alembic_cfg = Config()
            
            # Déterminer le chemin du script de migration
            migrations_dir = Path(__file__).parent / "migrations"
            
            # Vérifier si le répertoire existe
            if not migrations_dir.exists():
                self.logger.error(f"Répertoire de migrations non trouvé: {migrations_dir}")
                return False
            
            # Définir les paramètres de configuration
            alembic_cfg.set_main_option("script_location", str(migrations_dir))
            alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)
            
            # Exécuter les migrations
            command.upgrade(alembic_cfg, "head")
            
            self.logger.info("Migrations appliquées avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Échec de l'application des migrations: {str(e)}")
            raise DatabaseError(f"Impossible d'appliquer les migrations: {str(e)}")
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des migrations.
        
        Returns:
            Liste des migrations appliquées
            
        Raises:
            DatabaseError: Si la récupération échoue
        """
        try:
            session = self._get_session()
            
            try:
                migrations = []
                
                migration_models = (
                    session.query(MigrationModel)
                    .order_by(MigrationModel.id)
                    .all()
                )
                
                for migration in migration_models:
                    migrations.append({
                        'version': migration.version,
                        'description': migration.description,
                        'applied_at': migration.applied_at.isoformat()
                    })
                
                return migrations
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Échec de récupération de l'historique des migrations: {str(e)}")
            raise DatabaseError(f"Impossible de récupérer l'historique des migrations: {str(e)}")
    
    def backup_database(self, backup_path: Optional[Path] = None) -> Path:
        """
        Crée une sauvegarde de la base de données.
        
        Args:
            backup_path: Chemin de la sauvegarde (optionnel)
            
        Returns:
            Chemin de la sauvegarde
            
        Raises:
            DatabaseError: Si la sauvegarde échoue
        """
        try:
            import shutil
            from datetime import datetime
            
            # Générer un nom de sauvegarde si non spécifié
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.db_path.parent / f"backup_{timestamp}_{self.db_path.name}"
            
            # Créer le répertoire parent si nécessaire
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # S'assurer que la base de données est fermée
            self.engine.dispose()
            
            # Effectuer la sauvegarde
            shutil.copy2(self.db_path, backup_path)
            
            self.logger.info(f"Base de données sauvegardée: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde de la base de données: {str(e)}")
            raise DatabaseError(f"Impossible de sauvegarder la base de données: {str(e)}")
    
    def restore_database(self, backup_path: Path) -> bool:
        """
        Restaure la base de données à partir d'une sauvegarde.
        
        Args:
            backup_path: Chemin de la sauvegarde
            
        Returns:
            True si la restauration a réussi
            
        Raises:
            DatabaseError: Si la restauration échoue
        """
        try:
            import shutil
            
            # Vérifier que la sauvegarde existe
            if not backup_path.exists():
                raise ValueError(f"Fichier de sauvegarde non trouvé: {backup_path}")
            
            # S'assurer que la base de données est fermée
            self.engine.dispose()
            
            # Créer une sauvegarde de la base actuelle
            current_backup = self.backup_database()
            
            try:
                # Restaurer la sauvegarde
                shutil.copy2(backup_path, self.db_path)
                
                # Recréer le moteur et la session
                self.engine = sa.create_engine(self.db_url, echo=self.engine.echo)
                self.Session = sessionmaker(bind=self.engine)
                
                self.logger.info(f"Base de données restaurée depuis: {backup_path}")
                return True
                
            except Exception as e:
                # En cas d'erreur, essayer de revenir à la version précédente
                self.logger.warning(f"Échec de la restauration, tentative de retour arrière: {str(e)}")
                
                try:
                    shutil.copy2(current_backup, self.db_path)
                    self.engine = sa.create_engine(self.db_url, echo=self.engine.echo)
                    self.Session = sessionmaker(bind=self.engine)
                    
                    self.logger.info("Retour arrière réussi")
                except Exception as rollback_error:
                    self.logger.error(f"Échec du retour arrière: {str(rollback_error)}")
                
                raise e
                
        except Exception as e:
            self.logger.error(f"Échec de la restauration de la base de données: {str(e)}")
            raise DatabaseError(f"Impossible de restaurer la base de données: {str(e)}")
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if self.engine:
            self.engine.dispose()
            self.logger.debug("Connexion à la base de données fermée")