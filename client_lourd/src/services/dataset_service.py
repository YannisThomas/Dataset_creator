# src/services/dataset_service.py

from typing import List, Dict, Optional
from pathlib import Path

from src.models import Dataset, Image
from src.utils.logger import Logger
from src.database.db_manager import DatabaseManager

class DatasetService:
    """Service de gestion des datasets"""
    
    def __init__(
        self, 
        db_manager: Optional[DatabaseManager] = None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le service de dataset
        
        Args:
            db_manager: Gestionnaire de base de données
            logger: Gestionnaire de logs
        """
        self.db_manager = db_manager or DatabaseManager()
        self.logger = logger or Logger()
    
    def create_dataset(
        self, 
        name: str, 
        classes: Dict[int, str], 
        version: Optional[str] = None,
        base_path: Optional[Path] = None
    ) -> Dataset:
        """
        Crée un nouveau dataset
        
        Args:
            name: Nom du dataset
            classes: Dictionnaire des classes
            version: Version du dataset
            base_path: Chemin de base pour le dataset
            
        Returns:
            Dataset créé
        """
        try:
            # Vérifier que le dataset n'existe pas déjà
            existing_dataset = self.get_dataset(name)
            if existing_dataset:
                raise ValueError(f"Dataset {name} existe déjà")
            
            # Créer le dataset
            dataset = Dataset(
                name=name,
                classes=classes,
                path=base_path or Path(f"data/datasets/{name}"),
                version=version or "1.0.0"
            )
            
            # Sauvegarder dans la base de données
            self.db_manager.save_dataset(dataset)
            
            self.logger.info(f"Dataset créé : {name}")
            return dataset
            
        except Exception as e:
            self.logger.error(f"Échec de création du dataset : {str(e)}")
    
    def get_dataset(self, name: str) -> Optional[Dataset]:
        """
        Récupère un dataset par son nom
        
        Args:
            name: Nom du dataset
            
        Returns:
            Dataset ou None si non trouvé
        """
        try:
            return self.db_manager.load_dataset(name)
        except Exception as e:
            self.logger.error(f"Échec de récupération du dataset : {str(e)}")
            return None
    
    def update_dataset(self, dataset: Dataset) -> bool:
        """
        Met à jour un dataset existant
        
        Args:
            dataset: Dataset à mettre à jour
            
        Returns:
            True si la mise à jour a réussi
        """
        try:
            self.db_manager.save_dataset(dataset)
            self.logger.info(f"Dataset mis à jour : {dataset.name}")
            return True
        except Exception as e:
            self.logger.error(f"Échec de mise à jour du dataset : {str(e)}")
            return False
    
    def delete_dataset(self, name: str, delete_files: bool = False) -> bool:
        """
        Supprime un dataset
        
        Args:
            name: Nom du dataset
            delete_files: Supprimer également les fichiers physiques
            
        Returns:
            True si la suppression a réussi
        """
        try:
            # Charger le dataset
            dataset = self.get_dataset(name)
            if not dataset:
                self.logger.warning(f"Dataset non trouvé : {name}")
                return False
            
            # Supprimer de la base de données
            # Note : Implémenter la méthode de suppression dans DatabaseManager
            self.db_manager.delete_dataset(name)
            
            # Supprimer les fichiers si demandé
            if delete_files and dataset.path.exists():
                import shutil
                shutil.rmtree(dataset.path)
            
            self.logger.info(f"Dataset supprimé : {name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Échec de suppression du dataset : {str(e)}")
            return False
    
    def add_image_to_dataset(
        self, 
        dataset_name: str, 
        image: Image
    ) -> Optional[Dataset]:
        """
        Ajoute une image à un dataset existant
        
        Args:
            dataset_name: Nom du dataset
            image: Image à ajouter
            
        Returns:
            Dataset mis à jour ou None
        """
        try:
            # Charger le dataset
            dataset = self.get_dataset(dataset_name)
            if not dataset:
                raise ValueError(f"Dataset {dataset_name} non trouvé")
            
            # Ajouter l'image
            dataset.add_image(image)
            
            # Sauvegarder les modifications
            self.update_dataset(dataset)
            
            return dataset
        
        except Exception as e:
            self.logger.error(f"Échec de l'ajout d'image : {str(e)}")
            return None
    
    def validate_dataset(self, name: str) -> Dict:
        """
        Valide un dataset
        
        Args:
            name: Nom du dataset
            
        Returns:
            Résultat de la validation
        """
        try:
            dataset = self.get_dataset(name)
            if not dataset:
                return {
                    "valid": False,
                    "errors": [f"Dataset {name} non trouvé"]
                }
            
            return dataset.validate_dataset()
        
        except Exception as e:
            self.logger.error(f"Échec de validation du dataset : {str(e)}")
            return {
                "valid": False,
                "errors": [str(e)]
            }
    
    def get_dataset_statistics(self, name: str) -> Optional[Dict]:
        """
        Récupère les statistiques d'un dataset
        
        Args:
            name: Nom du dataset
            
        Returns:
            Statistiques du dataset ou None
        """
        try:
            dataset = self.get_dataset(name)
            if not dataset:
                return None
            
            return dataset.get_stats()
        
        except Exception as e:
            self.logger.error(f"Échec de récupération des statistiques : {str(e)}")
            return None