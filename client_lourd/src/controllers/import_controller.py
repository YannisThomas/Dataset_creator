# src/controllers/import_controller.py

import json
from typing import Dict, List, Optional, Union
from pathlib import Path

from src.models.image import Image
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
        classes: Optional[Dict[int, str]] = None,
        overwrite_existing: bool = False
    ) -> Dataset:
        """
        Importe des images depuis Mapillary et gère le mapping des classes.
        
        Args:
            bbox: Bounding box géographique
            dataset_name: Nom du dataset (optionnel)
            max_images: Nombre maximum d'images à importer
            classes: Mapping des classes (optionnel)
            overwrite_existing: Si True, écrase un dataset existant avec le même nom
            
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
            
            # Vérifier si le dataset existe déjà
            existing_dataset = self.dataset_service.get_dataset(dataset_name)
            
            if existing_dataset and not overwrite_existing:
                # Générer un nouveau nom unique
                import time
                timestamp = int(time.time())
                dataset_name = f"{dataset_name}_{timestamp}"
                self.logger.info(f"Dataset existant, utilisation du nouveau nom: {dataset_name}")
            elif existing_dataset and overwrite_existing:
                # Supprimer le dataset existant
                self.logger.info(f"Suppression du dataset existant: {dataset_name}")
                self.dataset_service.delete_dataset(dataset_name)
            
            # Charger la configuration Mapillary pour le mapping des classes
            mapillary_config = self._load_mapillary_config()
            self.logger.info(f"Configuration Mapillary chargée avec {len(mapillary_config.get('class_mapping', {}))} classes")
            
            # Utiliser le mapping des classes spécifié ou celui de la configuration
            if classes is None:
                classes = self._generate_classes_from_mapillary_config(mapillary_config)
                self.logger.info(f"Mapping de classes généré: {len(classes)} classes")
            
            # Créer le dataset avec TOUTES les classes Mapillary
            # Cette modification est cruciale pour résoudre les problèmes de classes manquantes
            dataset = self.dataset_service.create_dataset(
                name=dataset_name, 
                classes=classes
            )
            
            # Enregistrer les classes dans le dataset pour le débogage
            self.logger.info(f"Dataset créé avec {len(dataset.classes)} classes")
            
            # Importer depuis Mapillary
            dataset = self.import_service.import_from_mapillary(
                dataset, 
                bbox=bbox, 
                max_images=max_images
            )
            
            # Validation après import
            validation = dataset.validate_dataset()
            if not validation["valid"]:
                missing_classes = set()
                for image in dataset.images:
                    for ann in image.annotations:
                        if ann.class_id not in dataset.classes:
                            missing_classes.add(ann.class_id)
                
                if missing_classes:
                    self.logger.warning(f"Classes manquantes après import: {missing_classes}")
                    
                    # Résolution automatique: ajouter les classes manquantes
                    for class_id in missing_classes:
                        # Si le class_id est dans le mapping, récupérer son nom
                        class_name = self._find_class_name_for_id(class_id, mapillary_config)
                        dataset.classes[class_id] = class_name
                        self.logger.info(f"Classe manquante ajoutée: {class_id} -> {class_name}")
            
            # Mettre à jour le dataset dans la base de données
            self.dataset_service.update_dataset(dataset)
            
            self.logger.info(f"Import Mapillary terminé pour {dataset_name}")
            return dataset
            
        except Exception as e:
            self.logger.error(f"Échec de l'import Mapillary : {str(e)}")
            raise ImportError(f"Échec de l'import Mapillary : {str(e)}")

    def _find_class_name_for_id(self, class_id: int, config: Dict) -> str:
        """
        Trouve le nom d'une classe à partir de son ID dans la configuration Mapillary.
        
        Args:
            class_id: ID de la classe à rechercher
            config: Configuration Mapillary
            
        Returns:
            Nom de la classe ou un nom générique
        """
        # Rechercher dans le mapping inversé
        if "class_mapping" in config:
            for sign_value, sign_id in config["class_mapping"].items():
                if int(sign_id) == class_id:
                    # Extraction d'un nom plus lisible
                    parts = sign_value.split("--")
                    category = parts[0] if len(parts) > 0 else "Unknown"
                    category_fr = config.get("sign_categories", {}).get(category, category.capitalize())
                    
                    if len(parts) > 1:
                        sign_type = parts[1].replace("-", " ").title()
                        if len(parts) > 2:
                            variant = parts[2].upper()
                            return f"{category_fr}: {sign_type} ({variant})"
                        else:
                            return f"{category_fr}: {sign_type}"
                    
                    return sign_value
        
        # Nom générique pour les autres classes
        return f"Classe {class_id}"

    def _load_mapillary_config(self) -> Dict:
        """
        Charge la configuration Mapillary depuis le fichier.
        
        Returns:
            Dictionnaire de configuration Mapillary
        """
        try:
            import json
            config_dir = Path(__file__).parent.parent / "config"
            config_path = config_dir / "mapillary_config.json"
            
            if not config_path.exists():
                self.logger.warning(f"Fichier de configuration Mapillary non trouvé: {config_path}")
                return {"class_mapping": {}, "sign_categories": {}}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return config
        
        except Exception as e:
            self.logger.warning(f"Échec du chargement de la configuration Mapillary: {str(e)}")
            return {"class_mapping": {}, "sign_categories": {}}

    def _generate_classes_from_mapillary_config(self, config: Dict) -> Dict[int, str]:
        """
        Génère un dictionnaire de classes à partir de la configuration Mapillary.
        Création de noms de classes plus lisibles.
        
        Args:
            config: Configuration Mapillary
            
        Returns:
            Dictionnaire de classes (id -> nom)
        """
        classes = {}
        sign_categories = {
            "regulatory": "Réglementaire",
            "warning": "Danger",
            "information": "Information",
            "complementary": "Complémentaire"
        }
        
        # Récupérer le mapping des classes depuis la configuration
        if "class_mapping" in config:
            for sign_value, class_id in config["class_mapping"].items():
                # Convertir class_id en entier si c'est une chaîne numérique
                if isinstance(class_id, str) and class_id.isdigit():
                    class_id = int(class_id)
                
                # Créer un nom lisible à partir de la valeur du panneau
                # Format typique: "regulatory--stop--g1"
                parts = sign_value.split("--")
                
                if len(parts) >= 2:
                    # Récupérer la catégorie (regulatory, warning, etc.)
                    category = parts[0]
                    category_fr = sign_categories.get(category, category.capitalize())
                    
                    # Récupérer le nom du panneau et le formater joliment
                    sign_type = parts[1].replace("-", " ").title()
                    
                    # Version sans groupe (g1, g2, etc.)
                    if len(parts) >= 3:
                        # On peut ignorer le groupe ou l'inclure selon préférence
                        variant = parts[2].upper()
                        readable_name = f"{category_fr}: {sign_type} ({variant})"
                    else:
                        readable_name = f"{category_fr}: {sign_type}"
                    
                    classes[class_id] = readable_name
                else:
                    # Fallback si le format n'est pas reconnu
                    classes[class_id] = sign_value
        
        # Si aucune classe définie ou mapping vide, ajouter une classe générique
        if not classes:
            classes[0] = "Panneau"
        
        # Loguer le nombre de classes générées pour debugging
        self.logger.info(f"Mapping de classes généré: {len(classes)} classes")
        
        return classes
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
        Prévisualise les images qui seront importées depuis Mapillary.
        
        Args:
            bbox: Bounding box géographique
            max_images: Nombre maximum d'images à prévisualiser
            
        Returns:
            Liste des images prévisualisées
        """
        try:
            # Rechercher les images via l'API
            images = self.api_service.get_images_in_bbox(bbox, limit=max_images)
            
            # Si aucune image trouvée
            if not images:
                self.logger.warning("Aucune image trouvée dans la zone spécifiée")
                return []
            
            # Charger la configuration Mapillary
            mapillary_config = self._load_mapillary_config()
            
            # Accéder au dictionnaire correctement
            detection_config = {}
            min_confidence = 0.5  # Valeur par défaut
            
            # Version corrigée avec notation par crochets et vérifications
            if isinstance(mapillary_config, dict) and 'detection_mapping' in mapillary_config:
                if isinstance(mapillary_config['detection_mapping'], dict) and 'conversion' in mapillary_config['detection_mapping']:
                    detection_config = mapillary_config['detection_mapping']['conversion']
                    if isinstance(detection_config, dict) and 'min_confidence' in detection_config:
                        min_confidence = detection_config['min_confidence']
            
            # Pour chaque image, récupérer quelques annotations à titre d'exemple
            for image in images:
                try:
                    # Récupérer les annotations
                    annotations = self.api_service.get_image_detections(image.id)
                    
                    # Filtrer les annotations valides
                    valid_annotations = []
                    for annotation in annotations:
                        # Vérifier que les coordonnées sont dans les limites (0-1)
                        if (0 <= annotation.bbox.x <= 1 and 
                            0 <= annotation.bbox.y <= 1 and
                            0 < annotation.bbox.width <= 1 and 
                            0 < annotation.bbox.height <= 1 and
                            annotation.bbox.x + annotation.bbox.width <= 1 and
                            annotation.bbox.y + annotation.bbox.height <= 1):
                            
                            # Vérifier la confiance (si elle existe)
                            if hasattr(annotation, 'confidence') and annotation.confidence is not None:
                                if annotation.confidence >= min_confidence:
                                    valid_annotations.append(annotation)
                            else:
                                valid_annotations.append(annotation)
                    
                    # Limiter le nombre d'annotations pour la prévisualisation
                    image.annotations = valid_annotations[:5]  # Limiter à 5 annotations pour l'aperçu
                    
                except Exception as e:
                    self.logger.warning(f"Impossible de récupérer les annotations pour {image.id}: {str(e)}")
            
            self.logger.info(f"Prévisualisation Mapillary : {len(images)} images")
            return images
                
        except Exception as e:
            self.logger.error(f"Échec de la prévisualisation Mapillary : {str(e)}")
            
            # Log de la trace complète pour le débogage
            import traceback
            self.logger.error(traceback.format_exc())
            
            raise ImportError(f"Prévisualisation Mapillary impossible : {str(e)}")

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
        
    def import_yolo_dataset(
        self, 
        export_path: Union[str, Path], 
        new_dataset_name: Optional[str] = None
    ) -> Dataset:
        """
        Importe un dataset précédemment exporté au format YOLO
        
        Args:
            export_path: Chemin vers le répertoire d'export YOLO
            new_dataset_name: Nom à donner au dataset (optionnel)
            
        Returns:
            Dataset importé
        """
        try:
            export_path = Path(export_path)
            self.logger.info(f"Import du dataset YOLO depuis: {export_path}")
            
            # Vérifier que le répertoire existe
            if not export_path.exists() or not export_path.is_dir():
                raise ImportError(f"Répertoire d'export non trouvé : {export_path}")
            
            # Vérifier la présence des éléments essentiels
            images_dir = export_path / "images"
            labels_dir = export_path / "labels" 
            classes_file = export_path / "classes.txt"
            config_file = export_path / "dataset_config.json"
            
            if not images_dir.exists() or not labels_dir.exists():
                self.logger.error(f"Structure de répertoire YOLO invalide: images={images_dir.exists()}, labels={labels_dir.exists()}")
                raise ImportError(f"Structure de répertoire YOLO invalide : images ou labels manquants")
            
            # Charger la configuration si disponible
            dataset_config = {}
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    dataset_config = json.load(f)
                    self.logger.info(f"Configuration chargée depuis {config_file}")
            
            # Charger les classes
            classes = {}
            if classes_file.exists():
                with open(classes_file, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        class_name = line.strip()
                        if class_name:
                            classes[i] = class_name
                self.logger.info(f"Classes chargées depuis {classes_file}: {classes}")
            elif 'classes' in dataset_config:
                # Convertir les clés de chaîne en entiers si nécessaire
                classes = {}
                for key, value in dataset_config['classes'].items():
                    # Convertir key en entier s'il est stocké comme chaîne
                    try:
                        key_int = int(key)
                        classes[key_int] = value
                    except (ValueError, TypeError):
                        classes[key] = value
                self.logger.info(f"Classes chargées depuis la configuration: {classes}")
            
            if not classes:
                raise ImportError("Aucune information de classe trouvée")
            
            # Créer un nouveau dataset
            dataset_name = new_dataset_name or dataset_config.get('name', export_path.name)
            self.logger.info(f"Création du dataset {dataset_name} avec {len(classes)} classes")
            
            dataset = self.dataset_service.create_dataset(
                name=dataset_name,
                classes=classes,
                version=dataset_config.get('version', '1.0.0')
            )
            
            # Importer les images et annotations
            self.logger.info(f"Import des images depuis {images_dir} et annotations depuis {labels_dir}")
            return self.import_service.import_from_local(
                dataset=dataset,
                images_path=images_dir,
                annotations_path=labels_dir,
                format=DatasetFormat.YOLO,
                image_config_path=export_path / "image_info.json"
            )
        
        except Exception as e:
            self.logger.error(f"Échec de l'import du dataset YOLO : {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise ImportError(f"Import du dataset YOLO impossible : {str(e)}")