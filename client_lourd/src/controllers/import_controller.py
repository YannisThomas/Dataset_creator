# src/controllers/import_controller.py

from typing import Dict, List, Optional, Union
from pathlib import Path

from client_lourd.src.models.image import Image
from src.models import Dataset
from src.models.enums import DatasetFormat
from src.services.import_service import ImportService
from src.services.api_service import APIService
from src.services.dataset_service import DatasetService
from src.utils.logger import Logger
from src.core.exceptions import ImportError

class ImportController:
    """
    Contrôleur pour la gestion des imports de données
    
    Responsabilités :
    - Coordination des imports depuis différentes sources
    - Validation et prétraitement des données
    - Gestion des imports complexes
    """
    
    def __init__(
        self, 
        import_service: Optional[ImportService] = None,
        api_service: Optional[APIService] = None,
        dataset_service: Optional[DatasetService] = None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le contrôleur d'import
        
        Args:
            import_service: Service d'import de données
            api_service: Service API pour les imports distants
            dataset_service: Service de gestion des datasets
            logger: Gestionnaire de logs
        """
        self.import_service = import_service or ImportService()
        self.api_service = api_service or APIService()
        self.dataset_service = dataset_service or DatasetService()
        self.logger = logger or Logger()
    
    def import_from_local(
        self, 
        source_path: Union[str, Path], 
        dataset_name: Optional[str] = None,
        classes: Optional[Dict[int, str]] = None,
        format: DatasetFormat = DatasetFormat.YOLO
    ) -> Dataset:
        """
        Importe un dataset depuis un répertoire local
        
        Args:
            source_path: Chemin vers le répertoire des images
            dataset_name: Nom du dataset (optionnel)
            classes: Mapping des classes (optionnel)
            format: Format des annotations
            
        Returns:
            Dataset importé
        """
        try:
            # Convertir le chemin
            source_path = Path(source_path)
            
            # Vérifier l'existence du répertoire
            if not source_path.exists() or not source_path.is_dir():
                raise ImportError(f"Chemin source invalide : {source_path}")
            
            # Générer un nom de dataset si non spécifié
            if not dataset_name:
                dataset_name = source_path.name
            
            # Créer un dataset
            dataset = self.dataset_service.create_dataset(
                name=dataset_name,
                classes=classes or {}
            )
            
            # Importer depuis le répertoire local
            return self.import_service.import_from_local(
                dataset, 
                images_path=source_path, 
                format=format,
                classes=classes
            )
        
        except Exception as e:
            self.logger.error(f"Échec de l'import local : {str(e)}")
            raise ImportError(f"Import local impossible : {str(e)}")
    
    def import_from_mapillary(
        self, 
        bbox: Dict[str, float], 
        dataset_name: Optional[str] = None,
        max_images: int = 100,
        classes: Optional[Dict[int, str]] = None
    ) -> Dataset:
        """
        Importe des images depuis Mapillary
        
        Args:
            bbox: Bounding box géographique
            dataset_name: Nom du dataset (optionnel)
            max_images: Nombre maximum d'images à importer
            classes: Mapping des classes (optionnel)
            
        Returns:
            Dataset importé
        """
        try:
            # Valider la bounding box
            required_keys = ['min_lat', 'max_lat', 'min_lon', 'max_lon']
            if not all(key in bbox for key in required_keys):
                raise ValueError("Bounding box incomplète")
            
            # Générer un nom de dataset si non spécifié
            if not dataset_name:
                dataset_name = f"Mapillary_{bbox['min_lat']}_{bbox['max_lat']}_{bbox['min_lon']}_{bbox['max_lon']}"
            
            # Créer un dataset
            dataset = self.dataset_service.create_dataset(
                name=dataset_name,
                classes=classes or {}
            )
            
            # Importer depuis Mapillary
            return self.import_service.import_from_mapillary(
                dataset, 
                bbox=bbox, 
                max_images=max_images
            )
        
        except Exception as e:
            self.logger.error(f"Échec de l'import Mapillary : {str(e)}")
            raise ImportError(f"Import Mapillary impossible : {str(e)}")
    
    def import_from_config(
        self, 
        config_path: Union[str, Path]
    ) -> Dataset:
        """
        Importe un dataset à partir d'un fichier de configuration
        
        Args:
            config_path: Chemin vers le fichier de configuration
            
        Returns:
            Dataset importé
        """
        try:
            # Convertir le chemin
            config_path = Path(config_path)
            
            # Vérifier l'existence du fichier
            if not config_path.exists():
                raise ImportError(f"Fichier de configuration non trouvé : {config_path}")
            
            # Importer depuis le fichier de configuration
            return self.import_service.import_dataset_config(config_path)
        
        except Exception as e:
            self.logger.error(f"Échec de l'import de configuration : {str(e)}")
            raise ImportError(f"Import de configuration impossible : {str(e)}")
    
    def validate_import(
        self, 
        dataset: Dataset
    ) -> Dict:
        """
        Valide les données importées
        
        Args:
            dataset: Dataset à valider
            
        Returns:
            Résultat de la validation
        """
        try:
            # Valider le dataset
            validation = dataset.validate_dataset()
            
            # Journaliser les résultats
            if validation["valid"]:
                self.logger.info(f"Import validé pour le dataset : {dataset.name}")
            else:
                self.logger.warning(f"Validation échouée pour le dataset : {dataset.name}")
                for error in validation.get("errors", []):
                    self.logger.warning(f"Erreur de validation : {error}")
            
            return validation
        
        except Exception as e:
            self.logger.error(f"Échec de la validation d'import : {str(e)}")
            raise ImportError(f"Validation d'import impossible : {str(e)}")
    
    def search_images(
        self, 
        bbox: Optional[Dict[str, float]] = None,
        date_range: Optional[Dict[str, str]] = None,
        max_results: int = 100
    ) -> List[Image]:
        """
        Recherche d'images avec des filtres
        
        Args:
            bbox: Bounding box géographique (optionnel)
            date_range: Plage de dates (optionnel)
            max_results: Nombre maximum de résultats
            
        Returns:
            Liste des images trouvées
        """
        try:
            # Utiliser le service API pour rechercher des images
            images = self.api_service.search_images(
                bbox=bbox,
                date_range=date_range,
                max_results=max_results
            )
            
            self.logger.info(f"Recherche d'images : {len(images)} résultats")
            return images
        
        except Exception as e:
            self.logger.error(f"Échec de la recherche d'images : {str(e)}")
            raise ImportError(f"Recherche d'images impossible : {str(e)}")
    
    def preview_mapillary_import(
        self, 
        bbox: Dict[str, float], 
        max_images: int = 10
    ) -> List[Image]:
        """
        Prévisualise les images qui seront importées
        
        Args:
            bbox: Bounding box géographique
            max_images: Nombre maximum d'images à prévisualiser
            
        Returns:
            Liste des images prévisualisées
        """
        try:
            # Rechercher les images
            images = self.api_service.get_images_in_bbox(bbox, limit=max_images)
            
            # Ajouter les détails de localisation
            for image in images:
                # Récupérer quelques détections pour chaque image
                try:
                    annotations = self.api_service.get_image_detections(image.id)
                    image.annotations = annotations[:3]  # Limiter à 3 annotations
                except Exception as e:
                    self.logger.warning(f"Impossible de récupérer les annotations pour {image.id}: {str(e)}")
            
            self.logger.info(f"Prévisualisation Mapillary : {len(images)} images")
            return images
        
        except Exception as e:
            self.logger.error(f"Échec de la prévisualisation Mapillary : {str(e)}")
            raise ImportError(f"Prévisualisation Mapillary impossible : {str(e)}")
        
        # Ajouter cette méthode à la classe ImportController

    def import_image_to_dataset(
        self, 
        dataset,
        image_path: Union[str, Path]
    ) -> bool:
        """
        Importe une image locale dans un dataset.
        
        Args:
            dataset: Dataset de destination
            image_path: Chemin vers l'image
            
        Returns:
            True si l'import a réussi
        """
        try:
            path = Path(image_path)
            
            # Vérifier que le fichier existe
            if not path.exists() or not path.is_file():
                self.logger.warning(f"Fichier introuvable: {path}")
                return False
            
            # Vérifier l'extension du fichier
            config = self.config_manager.get_config() if hasattr(self, 'config_manager') else None
            supported_formats = config.dataset.supported_formats if config else ["jpg", "jpeg", "png"]
            
            if path.suffix.lower()[1:] not in supported_formats:
                self.logger.warning(f"Format non supporté: {path.suffix}")
                return False
            
            # Créer un identifiant unique pour l'image
            import uuid
            image_id = str(uuid.uuid4())
            
            # Obtenir les dimensions de l'image
            try:
                from PIL import Image as PILImage
                with PILImage.open(path) as pil_img:
                    width, height = pil_img.size
            except Exception as e:
                self.logger.error(f"Impossible de lire l'image {path}: {str(e)}")
                return False
            
            # Créer un objet Image
            from src.models.image import Image
            from src.models.enums import ImageSource
            
            image = Image(
                id=image_id,
                path=path,
                width=width,
                height=height,
                source=ImageSource.LOCAL,
                metadata={"original_filename": path.name}
            )
            
            # Ajouter l'image au dataset
            dataset.add_image(image)
            
            # Si possible, sauvegarder le dataset
            if hasattr(self, 'dataset_service') and hasattr(self.dataset_service, 'update_dataset'):
                self.dataset_service.update_dataset(dataset)
            
            self.logger.info(f"Image importée avec succès: {path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Échec de l'import de l'image {image_path}: {str(e)}")
            return False