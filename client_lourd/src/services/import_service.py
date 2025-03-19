# src/services/import_service.py

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Union

from src.models import Dataset, Image, Annotation, BoundingBox
from src.models.enums import ImageSource, AnnotationType, DatasetFormat
from src.services.api_service import APIService
from src.utils.logger import Logger
from src.core.exceptions import ImportError, ValidationError

class ImportService:
    """Service d'importation de datasets"""
    
    def __init__(
        self, 
        api_service: Optional[APIService] = None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le service d'import
        
        Args:
            api_service: Service API pour les imports distants
            logger: Gestionnaire de logs
        """
        self.api_service = api_service or APIService()
        self.logger = logger or Logger()
    


    def import_from_mapillary(
        self, 
        dataset: Dataset, 
        bbox: Dict[str, float], 
        max_images: int = 100,
        include_images_without_annotations: bool = False
    ) -> Dataset:
        """
        Importe des images depuis Mapillary avec un meilleur traitement des erreurs.
        """
        try:
            # Vérifier que le dataset n'est pas None
            if dataset is None:
                self.logger.error("Le dataset fourni est None")
                raise ImportError("Dataset invalide pour l'import")
                
            # Vérifier les paramètres bbox
            required_keys = ['min_lat', 'max_lat', 'min_lon', 'max_lon']
            if not all(key in bbox for key in required_keys):
                self.logger.error(f"Bounding box incomplète: {bbox}")
                raise ImportError("Bounding box incomplète, requiert min_lat, max_lat, min_lon, max_lon")
                
            # Récupérer les images de la zone
            self.logger.info(f"Récupération d'images depuis Mapillary dans la zone: {bbox}")
            images = self.api_service.get_images_in_bbox(
                bbox, 
                limit=max_images, 
                force_refresh=True,
                object_types=["regulatory", "warning", "information", "complementary"]
            )
            
            if not images:
                self.logger.warning("Aucune image trouvée dans la zone spécifiée avec des panneaux")
                raise ImportError("Aucune image trouvée dans la zone spécifiée avec des panneaux")
            
            self.logger.info(f"Récupération de {len(images)} images depuis Mapillary")
            
            # Statistiques pour le suivi
            total_annotations = 0
            images_with_annotations = 0
            invalid_coords_count = 0
            total_downloads = 0
            download_failures = 0
            
            # Créer les répertoires nécessaires
            images_dir = dataset.path / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            
            for i, image in enumerate(images):
                self.logger.debug(f"Traitement de l'image {i+1}/{len(images)}: {image.id}")
                
                # Récupérer les détections - avec une meilleure gestion des erreurs
                has_valid_annotations = False
                
                try:
                    annotations = self.api_service.get_image_detections(image.id, force_refresh=True)
                    
                    if annotations:
                        self.logger.info(f"Récupération de {len(annotations)} annotations pour l'image {image.id}")
                        total_annotations += len(annotations)
                        
                        # S'assurer que les annotations sont valides avant de les ajouter
                        valid_annotations = []
                        for annotation in annotations:
                            # Vérification complète des annotations
                            if self._is_valid_annotation(annotation, image.id):
                                valid_annotations.append(annotation)
                            else:
                                invalid_coords_count += 1
                        
                        # Si aucune annotation valide, logger le problème
                        if not valid_annotations and annotations:
                            self.logger.warning(f"Image {image.id}: {len(annotations)} annotations récupérées mais aucune valide")
                        
                        # Ajouter les annotations valides à l'image
                        if valid_annotations:
                            has_valid_annotations = True
                            for annotation in valid_annotations:
                                image.add_annotation(annotation)
                                
                            images_with_annotations += 1
                            self.logger.info(f"Ajout de {len(valid_annotations)} annotations valides à l'image {image.id}")
                        
                    else:
                        self.logger.warning(f"Aucune annotation trouvée pour l'image {image.id}")
                    
                except Exception as e:
                    self.logger.warning(f"Impossible de récupérer les annotations pour {image.id}: {str(e)}")
                
                # Si l'image n'a pas d'annotations valides et qu'on ne veut pas l'inclure, passer
                if not has_valid_annotations and not include_images_without_annotations:
                    self.logger.info(f"Image {image.id} ignorée: pas d'annotations valides")
                    continue
                
                # Télécharger l'image avec une meilleure gestion des erreurs
                download_success = self._download_and_process_image(image, images_dir)
                
                if download_success:
                    total_downloads += 1
                else:
                    download_failures += 1
                    if not has_valid_annotations:
                        # Si l'image n'a pas d'annotations et n'a pas pu être téléchargée, l'ignorer
                        continue
                
                # Ajouter l'image au dataset (que le téléchargement ait réussi ou non si elle a des annotations)
                dataset.add_image(image)
            
            # Validation et journalisation des statistiques complètes
            self.logger.info(f"Import terminé: {len(dataset.images)}/{len(images)} images ajoutées")
            self.logger.info(f"Statistiques d'import:")
            self.logger.info(f"- Images avec annotations: {images_with_annotations}")
            self.logger.info(f"- Total annotations: {total_annotations}")
            self.logger.info(f"- Annotations invalides: {invalid_coords_count}")
            self.logger.info(f"- Téléchargements réussis: {total_downloads}")
            self.logger.info(f"- Téléchargements échoués: {download_failures}")
            
            # Si aucune image n'a d'annotation, c'est probablement un problème
            if images_with_annotations == 0 and len(dataset.images) > 0:
                self.logger.error("AUCUNE IMAGE N'A D'ANNOTATION - Problème avec l'API ou le mapping des classes")
            
            return dataset
                
        except Exception as e:
            self.logger.error(f"Échec de l'import Mapillary : {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise ImportError(f"Échec de l'import Mapillary : {str(e)}")

    def _is_valid_annotation(self, annotation, image_id: str) -> bool:
        """
        Vérifie si une annotation est valide.
        
        Args:
            annotation: L'annotation à vérifier
            image_id: ID de l'image associée
            
        Returns:
            True si l'annotation est valide
        """
        try:
            # Vérifier que les coordonnées sont dans les limites (0-1)
            if not hasattr(annotation, 'bbox'):
                self.logger.warning(f"Annotation sans bbox pour l'image {image_id}")
                return False
                
            if (annotation.bbox.x < 0 or annotation.bbox.x > 1 or
                annotation.bbox.y < 0 or annotation.bbox.y > 1 or
                annotation.bbox.width <= 0 or annotation.bbox.width > 1 or
                annotation.bbox.height <= 0 or annotation.bbox.height > 1 or
                annotation.bbox.x + annotation.bbox.width > 1 or
                annotation.bbox.y + annotation.bbox.height > 1):
                
                self.logger.warning(
                    f"Annotation ignorée pour l'image {image_id} - coordonnées hors limites: "
                    f"x={annotation.bbox.x}, y={annotation.bbox.y}, "
                    f"width={annotation.bbox.width}, height={annotation.bbox.height}"
                )
                return False
                
            # Vérifier la classe
            if not hasattr(annotation, 'class_id'):
                self.logger.warning(f"Annotation sans class_id pour l'image {image_id}")
                return False
            
            return True
        except Exception as e:
            self.logger.warning(f"Erreur lors de la validation de l'annotation: {str(e)}")
            return False

    def _download_and_process_image(self, image: Image, output_dir: Path) -> bool:
        """
        Télécharge et traite une image.
        
        Args:
            image: Image à télécharger
            output_dir: Répertoire de destination
            
        Returns:
            True si le téléchargement et le traitement ont réussi
        """
        try:
            # Vérifier que le chemin d'image est valide
            if not hasattr(image, 'path') or not image.path:
                self.logger.warning(f"Chemin d'image invalide pour {image.id}")
                return False
                
            # S'assurer que l'URL a un préfixe https:// si nécessaire
            image_path = str(image.path)
            if image_path and not image_path.startswith(('http://', 'https://')):
                image_path = f"https://{image_path}"
                
            self.logger.debug(f"Téléchargement de l'image depuis: {image_path}")
            image_data = self.api_service.download_image(image_path)
            
            if not image_data:
                self.logger.warning(f"Échec du téléchargement de l'image {image.id}")
                return False
            
            # Sauvegarder l'image localement
            file_path = output_dir / f"{image.id}.jpg"
            
            # Ne pas réécrire le fichier s'il existe déjà et a la bonne taille
            if file_path.exists() and file_path.stat().st_size > 0:
                self.logger.debug(f"Image déjà téléchargée: {file_path}")
            else:
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                self.logger.debug(f"Image sauvegardée localement: {file_path}")
            
            # Mettre à jour le chemin de l'image vers le chemin local
            image.path = file_path
            
            # Vérifier les dimensions réelles de l'image
            try:
                from PIL import Image as PILImage
                with PILImage.open(file_path) as img:
                    image.width, image.height = img.size
                    self.logger.debug(f"Dimensions réelles de l'image: {image.width}x{image.height}")
            except Exception as e:
                self.logger.warning(f"Impossible de déterminer les dimensions de l'image: {str(e)}")
                # Si on ne peut pas lire les dimensions, garder les valeurs par défaut
            
            return True
        except Exception as e:
            self.logger.warning(f"Impossible de télécharger/traiter l'image {image.id}: {str(e)}")
            import traceback
            self.logger.warning(traceback.format_exc())
            return False
    
    def import_from_local(
        self, 
        dataset: Dataset, 
        images_path: Union[str, Path], 
        annotations_path: Optional[Union[str, Path]] = None,
        format: DatasetFormat = DatasetFormat.YOLO,
        image_config_path: Optional[Union[str, Path]] = None
    ) -> Dataset:
        """
        Importe des images et annotations depuis un répertoire local
        
        Args:
            dataset: Dataset de destination
            images_path: Chemin vers les images
            annotations_path: Chemin vers les annotations (optionnel)
            format: Format des annotations
            image_config_path: Chemin vers le fichier d'information sur les images (optionnel)
            
        Returns:
            Dataset mis à jour
        """
        try:
            # Convertir les chemins en Path
            images_path = Path(images_path)
            annotations_path = Path(annotations_path) if annotations_path else None
            
            # Vérifier que le chemin des images existe
            if not images_path.exists() or not images_path.is_dir():
                raise ImportError(f"Chemin d'images invalide : {images_path}")
            
            # Charger les informations des images si disponibles
            image_info = {}
            if image_config_path and Path(image_config_path).exists():
                with open(image_config_path, 'r', encoding='utf-8') as f:
                    image_info = json.load(f)
                    self.logger.info(f"Informations d'images chargées depuis {image_config_path}")
            elif (images_path.parent / "image_info.json").exists():
                with open(images_path.parent / "image_info.json", 'r', encoding='utf-8') as f:
                    image_info = json.load(f)
                    self.logger.info(f"Informations d'images chargées depuis {images_path.parent / 'image_info.json'}")
            
            # Charger les classes depuis le fichier classes.txt si présent
            classes_path = images_path.parent / "classes.txt"
            if classes_path.exists() and len(dataset.classes) == 0:
                self.logger.info(f"Chargement des classes depuis {classes_path}")
                classes = {}
                with open(classes_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        class_name = line.strip()
                        if class_name:
                            classes[i] = class_name
                if classes:
                    dataset.classes = classes
                    self.logger.info(f"Classes chargées: {classes}")
            
            # Importer les images
            image_files = list(images_path.glob('*.[jJ][pP][gG]')) + \
                        list(images_path.glob('*.[pP][nN][gG]')) + \
                        list(images_path.glob('*.[jJ][pP][eE][gG]'))
            
            self.logger.info(f"Import depuis {images_path}: {len(image_files)} images trouvées")
            
            for image_file in image_files:
                # Charger et valider l'image
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(image_file) as img:
                        width, height = img.size
                except Exception as e:
                    self.logger.warning(f"Impossible de charger l'image {image_file}: {str(e)}")
                    continue
                
                # Récupérer l'ID et les métadonnées depuis image_info si disponible
                image_id = image_file.stem
                source = ImageSource.LOCAL
                
                if image_file.name in image_info:
                    info = image_info[image_file.name]
                    if 'id' in info:
                        image_id = info['id']
                    if 'source' in info:
                        try:
                            source = ImageSource(info['source'])
                        except ValueError:
                            source = ImageSource.LOCAL
                
                # Créer un objet Image
                image = Image(
                    id=image_id,
                    path=image_file,  # Chemin local valide
                    width=width,
                    height=height,
                    source=source
                )
                
                # Importer les annotations si possible
                if annotations_path:
                    annotation_file = annotations_path / f"{image_file.stem}.txt"
                    self._import_annotations_for_image(
                        image, 
                        annotation_file, 
                        format,
                        dataset.classes
                    )
                elif format == DatasetFormat.YOLO and (images_path.parent / "labels").exists():
                    # Chercher automatiquement dans le répertoire labels
                    label_dir = images_path.parent / "labels"
                    annotation_file = label_dir / f"{image_file.stem}.txt"
                    self._import_annotations_for_image(
                        image, 
                        annotation_file, 
                        format,
                        dataset.classes
                    )
                
                # Ajouter l'image au dataset
                dataset.add_image(image)
            
            # Valider le dataset
            validation = dataset.validate_dataset()
            if not validation["valid"]:
                self.logger.warning(f"Validation du dataset échouée : {validation['errors']}")
                # On continue quand même, car certaines images peuvent être valides
            
            self.logger.info(f"Import de {len(dataset.images)} images")
            return dataset
        
        except Exception as e:
            self.logger.error(f"Échec de l'import local : {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise ImportError(f"Échec de l'import local : {str(e)}")
    
    def _import_annotations_for_image(
        self, 
        image: Image, 
        annotation_file: Path, 
        format: DatasetFormat,
        class_mapping: Dict[int, str]
    ):
        """
        Importe les annotations pour une image spécifique
        
        Args:
            image: Image à annoter
            annotation_file: Fichier d'annotations
            format: Format des annotations
            class_mapping: Mapping des classes
        """
        try:
            if not annotation_file.exists():
                return
            
            if format == DatasetFormat.YOLO:
                self._import_yolo_annotations(image, annotation_file, class_mapping)
            elif format == DatasetFormat.COCO:
                self._import_coco_annotations(image, annotation_file, class_mapping)
            elif format == DatasetFormat.VOC:
                self._import_voc_annotations(image, annotation_file, class_mapping)
        
        except Exception as e:
            self.logger.warning(f"Échec de l'import des annotations pour {image.path}: {str(e)}")
    
    def _import_yolo_annotations(
        self, 
        image: Image, 
        annotation_file: Path, 
        class_mapping: Dict[int, str]
    ):
        """
        Importe des annotations au format YOLO
        
        Format YOLO : class_id x_center y_center width height (normalized)
        """
        with open(annotation_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                
                try:
                    class_id = int(parts[0])
                    x_center, y_center, width, height = map(float, parts[1:])
                    
                    # Convertir du centre aux coordonnées normalisées
                    bbox = BoundingBox(
                        x=x_center - width/2,
                        y=y_center - height/2,
                        width=width,
                        height=height
                    )
                    
                    # Vérifier que la classe existe
                    if class_id not in class_mapping:
                        self.logger.warning(f"Classe {class_id} non définie pour l'image {image.path}")
                        continue
                    
                    # Créer l'annotation
                    annotation = Annotation(
                        class_id=class_id,
                        bbox=bbox,
                        type=AnnotationType.BBOX
                    )
                    
                    image.add_annotation(annotation)
                
                except ValueError as e:
                    self.logger.warning(f"Erreur de parsing de l'annotation : {str(e)}")
    
    def _import_coco_annotations(
        self, 
        image: Image, 
        annotation_file: Path, 
        class_mapping: Dict[int, str]
    ):
        """
        Importe des annotations au format COCO
        """
        with open(annotation_file, 'r') as f:
            coco_data = json.load(f)
        
        # Trouver les annotations pour cette image
        for ann in coco_data.get('annotations', []):
            # Vérifier que l'annotation correspond à l'image
            if ann.get('image_id') != image.id:
                continue
            
            # Extraire les informations de la bbox
            bbox = ann.get('bbox', [])
            if len(bbox) != 4:
                continue
            
            x, y, w, h = bbox
            
            # Convertir en coordonnées normalisées
            normalized_bbox = BoundingBox(
                x=x / image.width,
                y=y / image.height,
                width=w / image.width,
                height=h / image.height
            )
            
            # Récupérer l'ID de classe
            class_id = ann.get('category_id')
            if class_id not in class_mapping:
                self.logger.warning(f"Classe {class_id} non définie pour l'image {image.path}")
                continue
            
            # Créer l'annotation
            annotation = Annotation(
                class_id=class_id,
                bbox=normalized_bbox,
                type=AnnotationType.BBOX,
                confidence=ann.get('score', 1.0)
            )
            
            image.add_annotation(annotation)
    
    def _import_voc_annotations(
        self, 
        image: Image, 
        annotation_file: Path, 
        class_mapping: Dict[int, str]
    ):
        """
        Importe des annotations au format VOC (XML)
        """
        try:
            import xml.etree.ElementTree as ET
            
            tree = ET.parse(annotation_file)
            root = tree.getroot()
            
            # Extraire les informations de l'image
            size = root.find('size')
            if size is not None:
                width = int(size.find('width').text)
                height = int(size.find('height').text)
                
                # Vérifier la cohérence avec l'image
                if width != image.width or height != image.height:
                    self.logger.warning(f"Dimensions incohérentes pour {image.path}")
            
            # Parcourir les objets
            for obj in root.findall('object'):
                # Récupérer le nom de la classe
                name = obj.find('name').text
                
                # Trouver l'ID de classe correspondant
                class_id = None
                for id, class_name in class_mapping.items():
                    if class_name == name:
                        class_id = id
                        break
                
                if class_id is None:
                    self.logger.warning(f"Classe '{name}' non définie pour l'image {image.path}")
                    continue
                
                # Extraire les coordonnées de la bbox
                bbox_elem = obj.find('bndbox')
                x_min = int(bbox_elem.find('xmin').text)
                y_min = int(bbox_elem.find('ymin').text)
                x_max = int(bbox_elem.find('xmax').text)
                y_max = int(bbox_elem.find('ymax').text)
                
                # Convertir en coordonnées normalisées
                normalized_bbox = BoundingBox(
                    x=x_min / image.width,
                    y=y_min / image.height,
                    width=(x_max - x_min) / image.width,
                    height=(y_max - y_min) / image.height
                )
                
                # Créer l'annotation
                annotation = Annotation(
                    class_id=class_id,
                    bbox=normalized_bbox,
                    type=AnnotationType.BBOX
                )
                
                image.add_annotation(annotation)
        
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'import des annotations VOC : {str(e)}")
    
    def import_dataset_config(
        self, 
        config_path: Union[str, Path]
    ) -> Dataset:
        """
        Importe un dataset à partir de son fichier de configuration
        
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
            
            # Charger le fichier de configuration
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Créer le dataset
            dataset = Dataset(
                name=config_data.get('name', 'Unnamed Dataset'),
                version=config_data.get('version', '1.0.0'),
                path=config_path.parent,
                classes=config_data.get('classes', {}),
                metadata=config_data.get('metadata', {})
            )
            
            # Importer les images si possible
            images_dir = config_path.parent / 'images'
            if images_dir.exists():
                self.import_from_local(
                    dataset, 
                    images_path=images_dir, 
                    annotations_path=config_path.parent / 'annotations'
                )
            
            self.logger.info(f"Configuration du dataset importée : {config_path}")
            return dataset
        
        except Exception as e:
            self.logger.error(f"Échec de l'import de la configuration : {str(e)}")
            raise ImportError(f"Échec de l'import de la configuration : {str(e)}")