# src/controllers/api_controller.py

from typing import Dict, Optional, List, Union
from pathlib import Path

from src.models import Dataset, Image, Annotation
from src.services.api_service import APIService
from src.services.dataset_service import DatasetService
from src.utils.logger import Logger
from src.core.exceptions import APIError, ImportError

class APIController:
    """
    Contrôleur pour la gestion des interactions avec les API externes
    
    Responsabilités :
    - Coordination des requêtes API
    - Gestion des sources de données externes
    - Transformation et validation des données importées
    """
    
    def __init__(
        self, 
        api_service: Optional[APIService] = None,
        dataset_service: Optional[DatasetService] = None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le contrôleur d'API
        
        Args:
            api_service: Service d'interaction avec les API
            dataset_service: Service de gestion des datasets
            logger: Gestionnaire de logs
        """
        self.api_service = api_service or APIService()
        self.dataset_service = dataset_service or DatasetService()
        self.logger = logger or Logger()
    
    def verify_api_connection(self) -> bool:
        """
        Vérifie la connexion à l'API Mapillary
        
        Returns:
            True si la connexion est réussie, False sinon
        """
        try:
            result = self.api_service.verify_token()
            
            if result:
                self.logger.info("Connexion à l'API Mapillary établie avec succès")
            else:
                self.logger.warning("Échec de la connexion à l'API Mapillary")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de l'API : {str(e)}")
            return False
    
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
            # Valider les paramètres d'entrée
            if bbox:
                required_keys = ['min_lat', 'max_lat', 'min_lon', 'max_lon']
                if not all(key in bbox for key in required_keys):
                    raise ValueError("Bounding box incomplète")
            
            # Rechercher les images via le service API
            images = self.api_service.search_images(
                bbox=bbox,
                date_range=date_range,
                max_results=max_results
            )
            
            self.logger.info(f"Recherche d'images terminée : {len(images)} résultats")
            return images
        
        except Exception as e:
            self.logger.error(f"Échec de la recherche d'images : {str(e)}")
            raise APIError(f"Recherche d'images impossible : {str(e)}")
    
    def get_image_annotations(
        self, 
        image_id: str
    ) -> List[Annotation]:
        """
        Récupère les annotations d'une image spécifique
        
        Args:
            image_id: ID de l'image
            
        Returns:
            Liste des annotations
        """
        try:
            # Récupérer les détections via le service API
            annotations = self.api_service.get_image_detections(image_id)
            
            self.logger.info(f"Récupération des annotations pour l'image {image_id} : {len(annotations)} annotations")
            return annotations
        
        except Exception as e:
            self.logger.error(f"Échec de la récupération des annotations : {str(e)}")
            raise APIError(f"Récupération des annotations impossible : {str(e)}")
    
    def download_image(
        self, 
        url: str, 
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Télécharge une image depuis une URL
        
        Args:
            url: URL de l'image
            output_path: Chemin de sortie (optionnel)
            
        Returns:
            Chemin du fichier téléchargé
        """
        try:
            # Télécharger les données de l'image
            image_data = self.api_service.download_image(url)
            
            if not image_data:
                raise ImportError("Échec du téléchargement de l'image")
            
            # Générer un chemin de sortie si non spécifié
            if output_path is None:
                from uuid import uuid4
                
                # Déterminer le répertoire de téléchargement
                if hasattr(self.dataset_service, 'get_download_dir'):
                    download_dir = self.dataset_service.get_download_dir()
                else:
                    download_dir = Path("downloads")
                    
                output_path = download_dir / f"{uuid4()}.jpg"
            
            # Assurer l'existence du répertoire
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Sauvegarder l'image
            with open(output_path, 'wb') as f:
                f.write(image_data)
            
            self.logger.info(f"Image téléchargée : {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Échec du téléchargement de l'image : {str(e)}")
            raise APIError(f"Téléchargement de l'image impossible : {str(e)}")
    
    def import_images_to_dataset(
        self, 
        dataset: Dataset, 
        images: List[Image],
        download_images: bool = True
    ) -> Dataset:
        """
        Importe une liste d'images dans un dataset
        
        Args:
            dataset: Dataset de destination
            images: Liste des images à importer
            download_images: Télécharger les images si nécessaire
            
        Returns:
            Dataset mis à jour
        """
        try:
            # Parcourir les images
            for image in images:
                try:
                    # Télécharger l'image si requis
                    if download_images and hasattr(image, 'path'):
                        path_str = str(image.path)  # Convertir en string pour le test
                        
                        # Vérifier si le chemin est une URL
                        if path_str.startswith('http://') or path_str.startswith('https://'):
                            try:
                                # Télécharger l'image
                                local_path = self.download_image(path_str)
                                image.path = local_path
                                self.logger.info(f"Image téléchargée: {image.id}, chemin: {image.path}")
                            except Exception as e:
                                self.logger.warning(f"Échec du téléchargement de l'image {image.id}: {str(e)}")
                                # Continuer même si le téléchargement échoue
                    
                    # Récupérer les annotations si possible
                    if hasattr(image, 'id'):
                        try:
                            annotations = self.get_image_annotations(image.id)
                            image.annotations.extend(annotations)
                        except Exception as e:
                            self.logger.warning(f"Impossible de récupérer les annotations pour {image.id}: {str(e)}")
                    
                    # Ajouter l'image au dataset
                    dataset.add_image(image)
                
                except Exception as e:
                    self.logger.warning(f"Échec de l'import de l'image {getattr(image, 'id', 'unknown')}: {str(e)}")
            
            # Sauvegarder le dataset
            result = self.dataset_service.update_dataset(dataset)
            
            if not result:
                self.logger.warning("Échec de la mise à jour du dataset dans la base de données")
            
            self.logger.info(f"Import de {len(images)} images terminé")
            return dataset
        
        except Exception as e:
            self.logger.error(f"Échec de l'import des images : {str(e)}")
            raise APIError(f"Import des images impossible : {str(e)}")
    
    def generate_dataset_from_images(
        self, 
        images: List[Image], 
        dataset_name: str,
        classes: Optional[Dict[int, str]] = None,
        download_images: bool = True
    ) -> Dataset:
        """
        Génère un nouveau dataset à partir d'une liste d'images
        
        Args:
            images: Liste des images
            dataset_name: Nom du dataset
            classes: Mapping des classes (optionnel)
            download_images: Télécharger les images si nécessaire
            
        Returns:
            Nouveau dataset
        """
        try:
            # Créer un nouveau dataset
            dataset = self.dataset_service.create_dataset(
                name=dataset_name,
                classes=classes or {}
            )
            
            # Importer les images
            return self.import_images_to_dataset(
                dataset, 
                images, 
                download_images
            )
        
        except Exception as e:
            self.logger.error(f"Échec de la génération du dataset : {str(e)}")
            raise APIError(f"Génération du dataset impossible : {str(e)}")