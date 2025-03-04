# src/controllers/dataset_controller.py

from typing import Dict, Optional, List, Union
from pathlib import Path

from src.models import Dataset, Image
from src.models.enums import DatasetFormat
from src.services.dataset_service import DatasetService
from src.services.export_service import ExportService
from src.services.import_service import ImportService
from src.utils.logger import Logger
from src.core.exceptions import DatasetError, ImportError, ExportError

class DatasetController:
    """
    Contrôleur principal pour les opérations de dataset
    
    Responsabilités :
    - Coordination entre les services
    - Gestion des opérations de haut niveau sur les datasets
    - Validation et transformation des données
    """
    
    def __init__(
        self, 
        dataset_service: Optional[DatasetService] = None,
        import_service: Optional[ImportService] = None,
        export_service: Optional[ExportService] = None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le contrôleur de dataset
        
        Args:
            dataset_service: Service de gestion des datasets
            import_service: Service d'import de datasets
            export_service: Service d'export de datasets
            logger: Gestionnaire de logs
        """
        self.dataset_service = dataset_service or DatasetService()
        self.import_service = import_service or ImportService()
        self.export_service = export_service or ExportService()
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
            # Valider les paramètres
            if not name:
                raise ValueError("Le nom du dataset est requis")
            
            if not classes:
                raise ValueError("Au moins une classe est requise")
            
            # Créer le dataset via le service
            dataset = self.dataset_service.create_dataset(
                name=name, 
                classes=classes, 
                version=version,
                base_path=base_path
            )
            
            self.logger.info(f"Dataset créé : {name}")
            return dataset
        
        except Exception as e:
            self.logger.error(f"Échec de création du dataset : {str(e)}")
            raise DatasetError(f"Création du dataset impossible : {str(e)}")
    
    def import_dataset(
        self, 
        source: Union[str, Path], 
        name: Optional[str] = None,
        source_type: str = 'local',
        **kwargs
    ) -> Dataset:
        """
        Importe un dataset depuis différentes sources
        
        Args:
            source: Chemin ou source de données
            name: Nom optionnel du dataset
            source_type: Type de source (local, mapillary, config)
            **kwargs: Paramètres additionnels d'import
            
        Returns:
            Dataset importé
        """
        try:
            if source_type == 'local':
                # Créer un dataset avec les classes de l'import si non spécifié
                if not name:
                    name = Path(source).stem
                
                # Créer le dataset
                dataset = self.create_dataset(
                    name=name, 
                    classes=kwargs.get('classes', {})
                )
                
                # Importer depuis une source locale
                return self.import_service.import_from_local(
                    dataset, 
                    images_path=source, 
                    **kwargs
                )
            
            elif source_type == 'mapillary':
                # Importer depuis Mapillary
                if not name:
                    name = f"Mapillary_{kwargs.get('bbox', {})}"
                
                # Créer le dataset
                dataset = self.create_dataset(
                    name=name, 
                    classes=kwargs.get('classes', {})
                )
                
                # Importer depuis Mapillary
                return self.import_service.import_from_mapillary(
                    dataset, 
                    **kwargs
                )
            
            elif source_type == 'config':
                # Importer depuis un fichier de configuration
                return self.import_service.import_dataset_config(source)
            
            else:
                raise ValueError(f"Type de source non supporté : {source_type}")
        
        except Exception as e:
            self.logger.error(f"Échec de l'import du dataset : {str(e)}")
            raise ImportError(f"Import du dataset impossible : {str(e)}")
    
    def export_dataset(
        self, 
        dataset: Dataset, 
        export_format: Union[DatasetFormat, str],
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Exporte un dataset dans un format spécifique
        
        Args:
            dataset: Dataset à exporter
            export_format: Format d'export
            output_path: Chemin de sortie (optionnel)
            
        Returns:
            Chemin du répertoire d'export
        """
        try:
            # Exporter le dataset
            export_path = self.export_service.export_dataset(
                dataset, 
                export_format, 
                output_path
            )
            
            # Sauvegarder la configuration du dataset
            self.export_service.export_dataset_config(dataset, export_path / f"{dataset.name}_config.json")
            
            self.logger.info(f"Dataset exporté : {export_path}")
            return export_path
        
        except Exception as e:
            self.logger.error(f"Échec de l'export du dataset : {str(e)}")
            raise ExportError(f"Export du dataset impossible : {str(e)}")
    
    def add_image_to_dataset(
        self, 
        dataset: Dataset, 
        image: Image
    ) -> Dataset:
        """
        Ajoute une image à un dataset existant
        
        Args:
            dataset: Dataset de destination
            image: Image à ajouter
            
        Returns:
            Dataset mis à jour
        """
        try:
            # Ajouter l'image
            dataset.add_image(image)
            
            # Sauvegarder les modifications
            self.dataset_service.update_dataset(dataset)
            
            self.logger.info(f"Image ajoutée au dataset : {dataset.name}")
            return dataset
        
        except Exception as e:
            self.logger.error(f"Échec de l'ajout d'image : {str(e)}")
            raise DatasetError(f"Ajout de l'image impossible : {str(e)}")
    
    def get_dataset_statistics(self, dataset: Dataset) -> Dict:
        """
        Récupère les statistiques détaillées d'un dataset
        
        Args:
            dataset: Dataset à analyser
            
        Returns:
            Dictionnaire de statistiques
        """
        try:
            # Récupérer les statistiques via le service
            stats = self.dataset_service.get_dataset_statistics(dataset.name)
            
            if not stats:
                # Fallback: calculer les statistiques directement
                self.logger.info("Calcul direct des statistiques")
                stats = dataset.get_stats()
            
            if not stats:
                raise DatasetError(f"Impossible de récupérer les statistiques du dataset : {dataset.name}")
            
            return stats
        
        except Exception as e:
            self.logger.error(f"Échec de récupération des statistiques : {str(e)}")
            raise DatasetError(f"Récupération des statistiques impossible : {str(e)}")
    
    def validate_dataset(self, dataset: Dataset) -> Dict:
        """
        Valide un dataset
        
        Args:
            dataset: Dataset à valider
            
        Returns:
            Résultat de la validation
        """
        try:
            # Valider via le service
            validation = self.dataset_service.validate_dataset(dataset.name)
            
            self.logger.info(f"Validation du dataset : {dataset.name}")
            return validation
        
        except Exception as e:
            self.logger.error(f"Échec de validation du dataset : {str(e)}")
            raise DatasetError(f"Validation du dataset impossible : {str(e)}")
    
    def delete_dataset(
        self, 
        dataset: Dataset, 
        delete_files: bool = False
    ) -> bool:
        """
        Supprime un dataset
        
        Args:
            dataset: Dataset à supprimer
            delete_files: Supprimer également les fichiers physiques
            
        Returns:
            True si la suppression a réussi
        """
        try:
            # Supprimer via le service
            result = self.dataset_service.delete_dataset(dataset.name, delete_files)
            
            self.logger.info(f"Dataset supprimé : {dataset.name}")
            return result
        
        except Exception as e:
            self.logger.error(f"Échec de suppression du dataset : {str(e)}")
            raise DatasetError(f"Suppression du dataset impossible : {str(e)}")
    
    def merge_datasets(
        self, 
        source_datasets: List[Dataset], 
        target_dataset_name: str
    ) -> Dataset:
        """
        Fusionne plusieurs datasets
        
        Args:
            source_datasets: Liste des datasets sources
            target_dataset_name: Nom du dataset cible
            
        Returns:
            Dataset fusionné
        """
        try:
            # Fusionner les classes des datasets sources
            merged_classes = {}
            for dataset in source_datasets:
                for class_id, class_name in dataset.classes.items():
                    if class_id not in merged_classes:
                        merged_classes[class_id] = class_name
                    elif merged_classes[class_id] != class_name:
                        # Résoudre les conflits de noms de classes
                        new_class_id = max(merged_classes.keys()) + 1
                        merged_classes[new_class_id] = class_name
            
            # Créer le dataset cible
            target_dataset = self.create_dataset(
                name=target_dataset_name, 
                classes=merged_classes
            )
            
            # Fusionner les images
            for dataset in source_datasets:
                for image in dataset.images:
                    target_dataset.add_image(image)
            
            # Sauvegarder le dataset fusionné
            self.dataset_service.update_dataset(target_dataset)
            
            self.logger.info(f"Datasets fusionnés dans {target_dataset_name}")
            return target_dataset
        
        except Exception as e:
            self.logger.error(f"Échec de la fusion des datasets : {str(e)}")
            raise DatasetError(f"Fusion des datasets impossible : {str(e)}")
        
        # Ajouter cette méthode à la classe DatasetController

    def validate_dataset_info(
        self, 
        name: str, 
        classes: Dict[int, str], 
        version: Optional[str] = None,
        base_path: Optional[Path] = None
    ) -> Dict:
        """
        Valide les informations d'un dataset avant sa création.
        
        Args:
            name: Nom du dataset
            classes: Dictionnaire des classes
            version: Version du dataset
            base_path: Chemin de base pour le dataset
            
        Returns:
            Résultat de la validation
        """
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Valider le nom du dataset
        if not name or not name.strip():
            validation["valid"] = False
            validation["errors"].append("Le nom du dataset est requis")
        elif len(name) < 3:
            validation["warnings"].append("Le nom du dataset est très court")
        
        # Valider le chemin
        if base_path and not isinstance(base_path, Path):
            try:
                base_path = Path(base_path)
            except Exception:
                validation["valid"] = False
                validation["errors"].append("Chemin invalide")
        
        # Vérifier que le dataset n'existe pas déjà
        try:
            existing_dataset = self.get_dataset(name)
            if existing_dataset:
                validation["valid"] = False
                validation["errors"].append(f"Un dataset nommé '{name}' existe déjà")
        except Exception as e:
            self.logger.warning(f"Impossible de vérifier l'existence du dataset: {str(e)}")
        
        # Valider les classes
        if not classes:
            validation["valid"] = False
            validation["errors"].append("Au moins une classe est requise")
        else:
            # Vérifier les ID de classe
            for class_id, class_name in classes.items():
                if not isinstance(class_id, int):
                    validation["valid"] = False
                    validation["errors"].append(f"L'ID de classe doit être un entier: {class_id}")
                
                if not class_name or not class_name.strip():
                    validation["valid"] = False
                    validation["errors"].append(f"Le nom de classe est requis pour l'ID {class_id}")
        
        # Valider la version
        if version and not self._is_valid_version(version):
            validation["warnings"].append(f"Format de version non standard: {version}")
        
        return validation

    def _is_valid_version(self, version: str) -> bool:
        """
        Vérifie si la version suit un format standard (ex: 1.0.0).
        
        Args:
            version: Chaîne de version à vérifier
            
        Returns:
            True si le format est valide
        """
        import re
        return bool(re.match(r"^\d+(\.\d+){0,2}$", version))
    
    def get_dataset(self, name: str) -> Optional[Dataset]:
        """
        Récupère un dataset par son nom
        
        Args:
            name: Nom du dataset
            
        Returns:
            Dataset ou None si non trouvé
        """
        try:
            dataset = self.dataset_service.get_dataset(name)
            self.logger.info(f"Dataset récupéré : {name}")
            return dataset
        except Exception as e:
            self.logger.error(f"Échec de récupération du dataset : {str(e)}")
            raise DatasetError(f"Récupération du dataset impossible : {str(e)}")
        

    def update_dataset(self, dataset: Dataset) -> Dataset:
        """
        Met à jour un dataset existant
        
        Args:
            dataset: Dataset à mettre à jour
            
        Returns:
            Dataset mis à jour
        """
        try:
            # Mettre à jour le dataset via le service
            result = self.dataset_service.update_dataset(dataset)
            
            if not result:
                raise DatasetError(f"Échec de la mise à jour du dataset : {dataset.name}")
            
            self.logger.info(f"Dataset mis à jour : {dataset.name}")
            return dataset
        
        except Exception as e:
            self.logger.error(f"Échec de la mise à jour du dataset : {str(e)}")
            raise DatasetError(f"Mise à jour du dataset impossible : {str(e)}")