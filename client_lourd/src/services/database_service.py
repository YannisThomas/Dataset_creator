# src/services/database_service.py

from typing import List, Dict, Optional, Any, Union
from pathlib import Path

from src.models import Dataset, Image, Annotation
from src.database.db_manager import DatabaseManager
from src.utils.logger import Logger
from src.core.exceptions import DatabaseError

class DatabaseService:
    """
    Service d'accès aux données persistantes.
    
    Cette classe encapsule toutes les interactions avec la base de données,
    offrant une couche d'abstraction entre les contrôleurs et la persistance.
    """
    
    def __init__(
        self, 
        db_manager: Optional[DatabaseManager] = None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le service de base de données.
        
        Args:
            db_manager: Gestionnaire de base de données
            logger: Gestionnaire de logs
        """
        self.db_manager = db_manager or DatabaseManager()
        self.logger = logger or Logger()
    
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
            self.db_manager.save_dataset(dataset)
            self.logger.info(f"Dataset sauvegardé: {dataset.name}")
            return True
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
            dataset = self.db_manager.load_dataset(name)
            if dataset:
                self.logger.info(f"Dataset chargé: {name}")
            else:
                self.logger.warning(f"Dataset non trouvé: {name}")
            return dataset
        except Exception as e:
            self.logger.error(f"Échec de chargement du dataset: {str(e)}")
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
            result = self.db_manager.delete_dataset(name)
            self.logger.info(f"Dataset supprimé: {name}")
            return result
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
            datasets = self.db_manager.list_datasets()
            self.logger.debug(f"Récupération de {len(datasets)} datasets")
            return datasets
        except Exception as e:
            self.logger.error(f"Échec de récupération des datasets: {str(e)}")
            raise DatabaseError(f"Impossible de lister les datasets: {str(e)}")
    
    def save_image(self, dataset_name: str, image: Image) -> bool:
        """
        Sauvegarde une image dans un dataset.
        
        Args:
            dataset_name: Nom du dataset
            image: Image à sauvegarder
            
        Returns:
            True si la sauvegarde a réussi
            
        Raises:
            DatabaseError: Si la sauvegarde échoue
        """
        try:
            # Charger le dataset
            dataset = self.load_dataset(dataset_name)
            if not dataset:
                raise DatabaseError(f"Dataset non trouvé: {dataset_name}")
            
            # Vérifier si l'image existe déjà
            existing_image = next((img for img in dataset.images if img.id == image.id), None)
            
            # Mettre à jour l'image existante ou ajouter la nouvelle
            if existing_image:
                dataset.images.remove(existing_image)
                dataset.add_image(image)
            else:
                dataset.add_image(image)
            
            # Sauvegarder le dataset
            self.save_dataset(dataset)
            
            self.logger.info(f"Image sauvegardée: {image.id} dans dataset {dataset_name}")
            return True
        except Exception as e:
            self.logger.error(f"Échec de sauvegarde de l'image: {str(e)}")
            raise DatabaseError(f"Impossible de sauvegarder l'image: {str(e)}")
    
    def load_image(self, dataset_name: str, image_id: str) -> Optional[Image]:
        """
        Charge une image depuis un dataset.
        
        Args:
            dataset_name: Nom du dataset
            image_id: ID de l'image
            
        Returns:
            Image chargée ou None si non trouvée
            
        Raises:
            DatabaseError: Si le chargement échoue
        """
        try:
            # Charger le dataset
            dataset = self.load_dataset(dataset_name)
            if not dataset:
                raise DatabaseError(f"Dataset non trouvé: {dataset_name}")
            
            # Trouver l'image dans le dataset
            image = next((img for img in dataset.images if img.id == image_id), None)
            
            if image:
                self.logger.debug(f"Image chargée: {image_id}")
            else:
                self.logger.warning(f"Image non trouvée: {image_id}")
                
            return image
        except Exception as e:
            self.logger.error(f"Échec de chargement de l'image: {str(e)}")
            raise DatabaseError(f"Impossible de charger l'image: {str(e)}")
    
    def delete_image(self, dataset_name: str, image_id: str) -> bool:
        """
        Supprime une image d'un dataset.
        
        Args:
            dataset_name: Nom du dataset
            image_id: ID de l'image
            
        Returns:
            True si la suppression a réussi
            
        Raises:
            DatabaseError: Si la suppression échoue
        """
        try:
            # Charger le dataset
            dataset = self.load_dataset(dataset_name)
            if not dataset:
                raise DatabaseError(f"Dataset non trouvé: {dataset_name}")
            
            # Trouver l'image dans le dataset
            image = next((img for img in dataset.images if img.id == image_id), None)
            
            if image:
                # Supprimer l'image
                dataset.images.remove(image)
                
                # Sauvegarder le dataset
                self.save_dataset(dataset)
                
                self.logger.info(f"Image supprimée: {image_id}")
                return True
            else:
                self.logger.warning(f"Image non trouvée: {image_id}")
                return False
        except Exception as e:
            self.logger.error(f"Échec de suppression de l'image: {str(e)}")
            raise DatabaseError(f"Impossible de supprimer l'image: {str(e)}")
    
    def get_migration_status(self) -> Dict[str, Any]:
        """
        Récupère le statut des migrations de la base de données.
        
        Returns:
            Statut des migrations
            
        Raises:
            DatabaseError: Si la récupération échoue
        """
        try:
            history = self.db_manager.get_migration_history()
            return {
                "history": history,
                "count": len(history),
                "last_applied": history[-1] if history else None
            }
        except Exception as e:
            self.logger.error(f"Échec de récupération du statut des migrations: {str(e)}")
            raise DatabaseError(f"Impossible de récupérer le statut des migrations: {str(e)}")
    
    def apply_migrations(self) -> bool:
        """
        Applique les migrations de base de données.
        
        Returns:
            True si les migrations ont été appliquées avec succès
            
        Raises:
            DatabaseError: Si l'application des migrations échoue
        """
        try:
            self.db_manager.apply_migrations()
            self.logger.info("Migrations appliquées avec succès")
            return True
        except Exception as e:
            self.logger.error(f"Échec d'application des migrations: {str(e)}")
            raise DatabaseError(f"Impossible d'appliquer les migrations: {str(e)}")
    
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
            from datetime import datetime
            import shutil
            
            # Déterminer le chemin de la base de données
            db_path = Path(str(self.db_manager.engine.url).replace('sqlite:///', ''))
            
            # Générer un nom de sauvegarde si non spécifié
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = db_path.parent / f"backup_{timestamp}_{db_path.name}"
            
            # Créer le répertoire parent si nécessaire
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Effectuer la sauvegarde
            shutil.copy2(db_path, backup_path)
            
            self.logger.info(f"Base de données sauvegardée: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.error(f"Échec de sauvegarde de la base de données: {str(e)}")
            raise DatabaseError(f"Impossible de sauvegarder la base de données: {str(e)}")
    
    def get_dataset_statistics(self, name: str) -> Dict[str, Any]:
        """
        Récupère les statistiques détaillées d'un dataset.
        
        Args:
            name: Nom du dataset
            
        Returns:
            Statistiques du dataset
            
        Raises:
            DatabaseError: Si la récupération échoue
        """
        try:
            stats = self.db_manager.get_dataset_statistics(name)
            self.logger.debug(f"Statistiques récupérées pour le dataset {name}")
            return stats
        except Exception as e:
            self.logger.error(f"Échec de récupération des statistiques: {str(e)}")
            raise DatabaseError(f"Impossible de récupérer les statistiques: {str(e)}")