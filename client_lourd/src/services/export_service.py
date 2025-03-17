# src/services/export_service.py

import json
import shutil
import csv
import os
import zipfile
from pathlib import Path
from typing import Dict, Union, Optional, List, Tuple
import xml.dom.minidom as minidom
from datetime import datetime
import yaml

from src.models import Dataset, Image, Annotation
from src.models.enums import DatasetFormat, AnnotationType
from src.utils.logger import Logger
from src.core.exceptions import ExportError

class ExportService:
    """Service d'exportation des datasets avec options avancées"""
    
    def __init__(self, logger: Optional[Logger] = None):
        """
        Initialise le service d'export amélioré
        
        Args:
            logger: Gestionnaire de logs
        """
        self.logger = logger or Logger()
    
    def export_dataset(
        self, 
        dataset: Dataset, 
        export_format: Union[DatasetFormat, str],
        output_path: Optional[Path] = None,
        options: Optional[Dict] = None
    ) -> Path:
        """
        Exporte un dataset dans un format spécifique avec options avancées
        
        Args:
            dataset: Dataset à exporter
            export_format: Format d'export
            output_path: Chemin de sortie (optionnel)
            options: Options d'export supplémentaires
                - split_ratio: Dict avec les proportions train/val/test
                - include_images: Booléen pour inclure les fichiers images
                - compress: Booléen pour compresser l'export en .zip
                - format_specific: Dict d'options spécifiques au format
            
        Returns:
            Chemin du répertoire ou fichier d'export
        """
        try:
            # Convertir le format en enum si nécessaire
            if isinstance(export_format, str):
                export_format = DatasetFormat(export_format.lower())
            
            # Options par défaut
            default_options = {
                "split_ratio": {"train": 0.8, "val": 0.2, "test": 0.0},
                "include_images": True,
                "compress": False,
                "format_specific": {}
            }
            
            # Fusionner avec les options fournies
            options = {**default_options, **(options or {})}
            
            # Définir le chemin de sortie par défaut
            if output_path is None:
                output_path = Path(f"exports/{dataset.name}_{export_format.value}")
            
            # Créer le répertoire de sortie
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Diviser le dataset si nécessaire
            if sum(options["split_ratio"].values()) > 0:
                subsets = self._split_dataset(dataset, options["split_ratio"])
                export_paths = []
                
                for subset_name, subset_images in subsets.items():
                    subset_path = output_path / subset_name
                    subset_path.mkdir(parents=True, exist_ok=True)
                    
                    # Créer un sous-dataset temporaire
                    subset_dataset = Dataset(
                        name=f"{dataset.name}_{subset_name}",
                        version=dataset.version,
                        path=subset_path,
                        classes=dataset.classes,
                        metadata=dataset.metadata
                    )
                    subset_dataset.images = subset_images
                    
                    # Exporter le sous-dataset
                    self._export_by_format(
                        subset_dataset, 
                        export_format, 
                        subset_path,
                        include_images=options["include_images"],
                        format_specific=options["format_specific"]
                    )
                    
                    export_paths.append(subset_path)
                
                # Créer un fichier de configuration global
                self.export_dataset_config(dataset, output_path / f"{dataset.name}_config.json", options)
                
                # Compresser si demandé
                if options["compress"]:
                    zip_path = self._compress_export(output_path)
                    self.logger.info(f"Export compressé du dataset terminé : {zip_path}")
                    return zip_path
                
                self.logger.info(f"Export divisé du dataset terminé : {output_path}")
                return output_path
            else:
                # Exporter sans division
                self._export_by_format(
                    dataset, 
                    export_format, 
                    output_path,
                    include_images=options["include_images"],
                    format_specific=options["format_specific"]
                )
                
                # Créer un fichier de configuration
                self.export_dataset_config(dataset, output_path / f"{dataset.name}_config.json", options)
                
                # Compresser si demandé
                if options["compress"]:
                    zip_path = self._compress_export(output_path)
                    self.logger.info(f"Export compressé du dataset terminé : {zip_path}")
                    return zip_path
                
                self.logger.info(f"Export du dataset terminé : {output_path}")
                return output_path
                
        except Exception as e:
            self.logger.error(f"Échec de l'export du dataset : {str(e)}")
            raise ExportError(f"Échec de l'export : {str(e)}")
    
    def _export_by_format(
        self, 
        dataset: Dataset, 
        export_format: DatasetFormat,
        output_path: Path,
        include_images: bool = True,
        format_specific: Dict = None
    ) -> Path:
        """
        Exporte un dataset selon le format spécifié
        
        Args:
            dataset: Dataset à exporter
            export_format: Format d'export
            output_path: Chemin de sortie
            include_images: Inclure les fichiers images
            format_specific: Options spécifiques au format
            
        Returns:
            Chemin du répertoire d'export
        """
        if export_format == DatasetFormat.YOLO:
            return self._export_yolo(dataset, output_path, include_images, format_specific)
        elif export_format == DatasetFormat.COCO:
            return self._export_coco(dataset, output_path, include_images, format_specific)
        elif export_format == DatasetFormat.VOC:
            return self._export_voc(dataset, output_path, include_images, format_specific)
        else:
            raise ExportError(f"Format d'export non supporté : {export_format}")
    
    def _split_dataset(
        self, 
        dataset: Dataset, 
        split_ratio: Dict[str, float]
    ) -> Dict[str, List[Image]]:
        """
        Divise le dataset en sous-ensembles selon les ratios spécifiés
        
        Args:
            dataset: Dataset à diviser
            split_ratio: Dictionnaire des ratios (train, val, test)
            
        Returns:
            Dictionnaire des sous-ensembles d'images
        """
        import random
        
        # Vérifier que les ratios sont valides
        if abs(sum(split_ratio.values()) - 1.0) > 0.001:
            self.logger.warning("Les ratios de division ne totalisent pas 1.0, normalisation automatique")
            total = sum(split_ratio.values())
            split_ratio = {k: v/total for k, v in split_ratio.items()}
        
        # Copier la liste des images pour ne pas modifier l'original
        all_images = dataset.images.copy()
        
        # Mélanger les images pour une division aléatoire
        random.shuffle(all_images)
        
        # Calculer les indices de division
        total_images = len(all_images)
        train_end = int(total_images * split_ratio["train"])
        val_end = train_end + int(total_images * split_ratio["val"])
        
        # Créer les sous-ensembles
        subsets = {
            "train": all_images[:train_end],
            "val": all_images[train_end:val_end],
            "test": all_images[val_end:]
        }
        
        # Filtrer les sous-ensembles vides
        subsets = {k: v for k, v in subsets.items() if v}
        
        self.logger.info(f"Dataset divisé en {', '.join([f'{k}:{len(v)}' for k, v in subsets.items()])}")
        return subsets
    
    def _compress_export(self, export_path: Path) -> Path:
        """
        Compresse un dossier d'export en fichier zip
        
        Args:
            export_path: Chemin du dossier à compresser
            
        Returns:
            Chemin du fichier zip
        """
        zip_path = export_path.with_suffix('.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(export_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(export_path.parent)
                    zipf.write(file_path, arcname)
        
        self.logger.info(f"Export compressé : {zip_path}")
        return zip_path
    
    def _export_yolo(
        self, 
        dataset: Dataset, 
        output_path: Path,
        include_images: bool = True,
        format_specific: Dict = None
    ) -> Path:
        """
        Exporte un dataset au format YOLO
        
        Args:
            dataset: Dataset à exporter
            output_path: Chemin de sortie
            include_images: Inclure les fichiers images
            format_specific: Options spécifiques au format YOLO
                - relative_paths: Utiliser des chemins relatifs
                - create_data_yaml: Créer un fichier data.yaml
            
        Returns:
            Chemin du répertoire d'export
        """
        try:
            # Options spécifiques
            format_specific = format_specific or {}
            create_data_yaml = format_specific.get("create_data_yaml", True)
            
            # Créer les sous-répertoires
            images_dir = output_path / "images"
            labels_dir = output_path / "labels"
            images_dir.mkdir(parents=True, exist_ok=True)
            labels_dir.mkdir(parents=True, exist_ok=True)
            
            # Créer le fichier classes.txt
            with open(output_path / "classes.txt", 'w', encoding='utf-8') as f:
                for class_id in sorted(dataset.classes.keys()):
                    f.write(f"{dataset.classes[class_id]}\n")
            
            # Créer le fichier data.yaml pour l'entraînement YOLO
            if create_data_yaml:
                self._create_yolo_data_yaml(dataset, output_path)
            
            # Enregistrer la configuration des images pour faciliter le rechargement
            image_config = {}
            
            # Exporter chaque image et ses annotations
            for image in dataset.images:
                # Préparer le nom de fichier de destination
                # Récupérer le nom de fichier valide
                if hasattr(image.path, 'name'):
                    image_filename = image.path.name
                else:
                    # Gérer le cas où path est une URL ou une chaîne
                    from urllib.parse import urlparse
                    import os
                    parsed_path = urlparse(str(image.path))
                    image_filename = os.path.basename(parsed_path.path)
                    if not image_filename:
                        # Générer un nom unique si impossible d'extraire
                        image_filename = f"{image.id}.jpg"
                
                dest_image_path = images_dir / image_filename
                
                # Copier l'image si demandé
                if include_images:
                    try:
                        # Vérifier si le chemin source est une URL
                        if isinstance(image.path, str) and image.path.startswith(('http://', 'https://')):
                            # C'est une URL, chercher si le fichier a été téléchargé localement
                            from urllib.parse import urlparse
                            import os
                            parsed_url = urlparse(image.path)
                            filename = os.path.basename(parsed_url.path)
                            
                            # Si le nom de fichier est vide, utiliser l'ID de l'image
                            if not filename:
                                filename = f"{image.id}.jpg"
                            
                            # Essayer de trouver le fichier téléchargé localement
                            found = False
                            potential_paths = [
                                Path(f"downloads/{filename}"),
                                Path(f"downloads/{image.id}.jpg"),
                                Path(f"data/downloads/{filename}"),
                                Path(dataset.path) / "images" / filename,
                                Path(dataset.path) / "images" / f"{image.id}.jpg"
                            ]
                            
                            for potential_path in potential_paths:
                                if potential_path.exists():
                                    shutil.copy(potential_path, dest_image_path)
                                    self.logger.info(f"Image copiée depuis {potential_path} vers {dest_image_path}")
                                    found = True
                                    break
                            
                            if not found:
                                self.logger.warning(f"Impossible de trouver l'image localement pour {image.path}")
                        else:
                            # C'est un chemin local
                            path_obj = Path(image.path) if isinstance(image.path, str) else image.path
                            if path_obj.exists():
                                shutil.copy(path_obj, dest_image_path)
                                self.logger.info(f"Image copiée depuis {path_obj} vers {dest_image_path}")
                            else:
                                self.logger.warning(f"Fichier source introuvable: {path_obj}")
                        
                        # Enregistrer les informations importantes de l'image
                        image_config[image_filename] = {
                            'id': image.id,
                            'width': image.width,
                            'height': image.height,
                            'source': image.source.value,
                            'original_path': str(image.path)  # Sauvegarder le chemin original pour référence
                        }
                    except Exception as e:
                        self.logger.warning(f"Impossible de copier l'image {image.path}: {str(e)}")
                
                # Créer le fichier d'annotations
                label_path = labels_dir / f"{image_filename.split('.')[0]}.txt"
                with open(label_path, 'w', encoding='utf-8') as f:
                    for ann in image.annotations:
                        # Format YOLO : class_id x_center y_center width height
                        f.write(
                            f"{ann.class_id} "
                            f"{ann.bbox.x + ann.bbox.width/2:.6f} "
                            f"{ann.bbox.y + ann.bbox.height/2:.6f} "
                            f"{ann.bbox.width:.6f} "
                            f"{ann.bbox.height:.6f}\n"
                        )
            
            # Enregistrer les informations des images dans un fichier JSON
            with open(output_path / "image_info.json", 'w', encoding='utf-8') as f:
                json.dump(image_config, f, indent=2)
            
            # Créer un fichier de configuration supplémentaire pour l'import
            config_data = {
                'name': dataset.name,
                'version': dataset.version,
                'images_dir': 'images',
                'labels_dir': 'labels',
                'classes': dataset.classes,
                'format': 'YOLO'
            }
            
            with open(output_path / "dataset_config.json", 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
            
            self.logger.info(f"Export YOLO terminé : {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Échec de l'export YOLO : {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise ExportError(f"Échec de l'export YOLO : {str(e)}")
    
    def _create_yolo_data_yaml(self, dataset: Dataset, output_path: Path):
        """
        Crée un fichier data.yaml pour l'entraînement YOLO
        
        Args:
            dataset: Dataset source
            output_path: Chemin de sortie
        """
        try:
            # Créer le contenu du fichier data.yaml
            data_yaml = {
                "path": str(output_path.absolute()),
                "train": str((output_path / "images").absolute()),
                "val": str((output_path / "images").absolute()),
                "names": {class_id: name for class_id, name in dataset.classes.items()},
                "nc": len(dataset.classes)
            }
            
            # Écrire le fichier
            with open(output_path / "data.yaml", 'w', encoding='utf-8') as f:
                yaml.dump(data_yaml, f, default_flow_style=False, sort_keys=False)
                
            self.logger.info(f"Fichier data.yaml créé : {output_path / 'data.yaml'}")
        
        except Exception as e:
            self.logger.warning(f"Échec de la création du fichier data.yaml : {str(e)}")
            
    def _export_coco(
        self, 
        dataset: Dataset, 
        output_path: Path,
        include_images: bool = True,
        format_specific: Dict = None
    ) -> Path:
        """
        Exporte un dataset au format COCO
        
        Args:
            dataset: Dataset à exporter
            output_path: Chemin de sortie
            include_images: Inclure les fichiers images
            format_specific: Options spécifiques au format COCO
                - include_licenses: Inclure les infos de licence
                - include_info: Inclure les métadonnées du dataset
                - min_area: Superficie minimale pour les annotations
            
        Returns:
            Chemin du répertoire d'export
        """
        try:
            # Options spécifiques
            format_specific = format_specific or {}
            min_area = format_specific.get("min_area", 0)
            include_licenses = format_specific.get("include_licenses", True)
            include_info = format_specific.get("include_info", True)
            
            # Créer les sous-répertoires
            if include_images:
                images_dir = output_path / "images"
                images_dir.mkdir(parents=True, exist_ok=True)
            
            # Structure de base COCO
            coco_data = {
                "images": [],
                "annotations": [],
                "categories": []
            }
            
            # Ajouter les catégories
            for class_id, class_name in sorted(dataset.classes.items()):
                coco_data["categories"].append({
                    "id": class_id,
                    "name": class_name,
                    "supercategory": "none"
                })
            
            # Ajouter les métadonnées si demandé
            if include_info:
                coco_data["info"] = {
                    "description": dataset.name,
                    "version": dataset.version,
                    "year": dataset.created_at.year,
                    "contributor": dataset.metadata.get("contributor", ""),
                    "date_created": dataset.created_at.isoformat()
                }
            
            # Ajouter les licences si demandé
            if include_licenses:
                coco_data["licenses"] = [{
                    "id": 1,
                    "name": dataset.metadata.get("license_name", "Unknown"),
                    "url": dataset.metadata.get("license_url", "")
                }]
            
            # Convertir les images et annotations
            ann_id = 1
            for img_idx, image in enumerate(dataset.images, 1):
                # Copier l'image si demandé
                if include_images:
                    dest_image_path = images_dir / image.path.name
                    try:
                        shutil.copy(image.path, dest_image_path)
                    except Exception as e:
                        self.logger.warning(f"Impossible de copier l'image {image.path}: {str(e)}")
                
                # Ajouter l'image
                coco_data["images"].append({
                    "id": img_idx,
                    "file_name": image.path.name,
                    "width": image.width,
                    "height": image.height,
                    "date_captured": image.created_at.isoformat() if hasattr(image, 'created_at') else None,
                    "license": 1,
                    "coco_url": "",
                    "flickr_url": ""
                })
                
                # Ajouter les annotations
                for ann in image.annotations:
                    # Calculer les coordonnées absolues
                    x = ann.bbox.x * image.width
                    y = ann.bbox.y * image.height
                    w = ann.bbox.width * image.width
                    h = ann.bbox.height * image.height
                    
                    # Calculer l'aire
                    area = w * h
                    
                    # Ignorer les annotations trop petites si demandé
                    if area < min_area:
                        continue
                    
                    coco_data["annotations"].append({
                        "id": ann_id,
                        "image_id": img_idx,
                        "category_id": ann.class_id,
                        "bbox": [x, y, w, h],
                        "area": area,
                        "segmentation": [],
                        "iscrowd": 0
                    })
                    ann_id += 1
            
            # Sauvegarder le fichier JSON
            output_file = output_path / "annotations.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(coco_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Export COCO terminé : {output_path}")
            return output_path
            
        except Exception as e:
            raise ExportError(f"Échec de l'export COCO : {str(e)}")
    
    def _export_voc(
        self, 
        dataset: Dataset, 
        output_path: Path,
        include_images: bool = True,
        format_specific: Dict = None
    ) -> Path:
        """
        Exporte un dataset au format Pascal VOC
        
        Args:
            dataset: Dataset à exporter
            output_path: Chemin de sortie
            include_images: Inclure les fichiers images
            format_specific: Options spécifiques au format VOC
                - segmentation_masks: Inclure des masques de segmentation vides
                - create_imagesets: Créer les fichiers ImageSets
            
        Returns:
            Chemin du répertoire d'export
        """
        try:
            # Options spécifiques
            format_specific = format_specific or {}
            segmentation_masks = format_specific.get("segmentation_masks", False)
            create_imagesets = format_specific.get("create_imagesets", True)
            
            # Créer les sous-répertoires
            annotations_dir = output_path / "Annotations"
            imagesets_dir = output_path / "ImageSets" / "Main"
            
            if include_images:
                images_dir = output_path / "JPEGImages"
                images_dir.mkdir(parents=True, exist_ok=True)
            
            annotations_dir.mkdir(parents=True, exist_ok=True)
            
            if create_imagesets:
                imagesets_dir.mkdir(parents=True, exist_ok=True)
            
            # Liste des noms de fichiers (sans extension)
            image_names = []
            
            # Exporter chaque image et ses annotations
            for image in dataset.images:
                # Ajouter à la liste des noms
                image_names.append(image.path.stem)
                
                # Copier l'image si demandé
                if include_images:
                    dest_image_path = images_dir / image.path.name
                    try:
                        shutil.copy(image.path, dest_image_path)
                    except Exception as e:
                        self.logger.warning(f"Impossible de copier l'image {image.path}: {str(e)}")
                
                # Créer le fichier XML d'annotations
                self._create_voc_annotation(image, dataset.classes, annotations_dir, segmentation_masks)
            
            # Créer les fichiers ImageSets si demandé
            if create_imagesets and image_names:
                self._create_voc_imagesets(image_names, imagesets_dir)
            
            # Créer le fichier classes.txt
            with open(output_path / "classes.txt", 'w', encoding='utf-8') as f:
                for class_id in sorted(dataset.classes.keys()):
                    f.write(f"{dataset.classes[class_id]}\n")
            
            self.logger.info(f"Export VOC terminé : {output_path}")
            return output_path
            
        except Exception as e:
            raise ExportError(f"Échec de l'export VOC : {str(e)}")
    
    def _create_voc_annotation(
        self, 
        image: Image, 
        classes: Dict[int, str],
        output_dir: Path,
        include_segmentation: bool = False
    ):
        """
        Crée un fichier d'annotation VOC (XML) pour une image
        
        Args:
            image: Image source
            classes: Dictionnaire des classes
            output_dir: Répertoire de destination
            include_segmentation: Inclure des balises de segmentation vides
        """
        try:
            # Créer le document XML
            doc = minidom.getDOMImplementation().createDocument(None, "annotation", None)
            root = doc.documentElement
            
            # Ajouter les informations de base
            folder_elem = doc.createElement("folder")
            folder_elem.appendChild(doc.createTextNode("JPEGImages"))
            root.appendChild(folder_elem)
            
            filename_elem = doc.createElement("filename")
            filename_elem.appendChild(doc.createTextNode(image.path.name))
            root.appendChild(filename_elem)
            
            # Source
            source_elem = doc.createElement("source")
            database_elem = doc.createElement("database")
            database_elem.appendChild(doc.createTextNode("YOLO Dataset Manager"))
            source_elem.appendChild(database_elem)
            root.appendChild(source_elem)
            
            # Taille
            size_elem = doc.createElement("size")
            width_elem = doc.createElement("width")
            width_elem.appendChild(doc.createTextNode(str(image.width)))
            height_elem = doc.createElement("height")
            height_elem.appendChild(doc.createTextNode(str(image.height)))
            depth_elem = doc.createElement("depth")
            depth_elem.appendChild(doc.createTextNode("3"))
            size_elem.appendChild(width_elem)
            size_elem.appendChild(height_elem)
            size_elem.appendChild(depth_elem)
            root.appendChild(size_elem)
            
            # Ajouter les objets (annotations)
            for ann in image.annotations:
                obj_elem = doc.createElement("object")
                
                # Nom de la classe
                name_elem = doc.createElement("name")
                class_name = classes.get(ann.class_id, f"class_{ann.class_id}")
                name_elem.appendChild(doc.createTextNode(class_name))
                obj_elem.appendChild(name_elem)
                
                # Caractéristiques de l'objet
                pose_elem = doc.createElement("pose")
                pose_elem.appendChild(doc.createTextNode("Unspecified"))
                obj_elem.appendChild(pose_elem)
                
                truncated_elem = doc.createElement("truncated")
                truncated_elem.appendChild(doc.createTextNode("0"))
                obj_elem.appendChild(truncated_elem)
                
                difficult_elem = doc.createElement("difficult")
                difficult_elem.appendChild(doc.createTextNode("0"))
                obj_elem.appendChild(difficult_elem)
                
                # Coordonnées de la bounding box
                bbox_elem = doc.createElement("bndbox")
                
                # Convertir les coordonnées normalisées en pixels
                xmin = int(ann.bbox.x * image.width)
                ymin = int(ann.bbox.y * image.height)
                xmax = int((ann.bbox.x + ann.bbox.width) * image.width)
                ymax = int((ann.bbox.y + ann.bbox.height) * image.height)
                
                xmin_elem = doc.createElement("xmin")
                xmin_elem.appendChild(doc.createTextNode(str(xmin)))
                ymin_elem = doc.createElement("ymin")
                ymin_elem.appendChild(doc.createTextNode(str(ymin)))
                xmax_elem = doc.createElement("xmax")
                xmax_elem.appendChild(doc.createTextNode(str(xmax)))
                ymax_elem = doc.createElement("ymax")
                ymax_elem.appendChild(doc.createTextNode(str(ymax)))
                
                bbox_elem.appendChild(xmin_elem)
                bbox_elem.appendChild(ymin_elem)
                bbox_elem.appendChild(xmax_elem)
                bbox_elem.appendChild(ymax_elem)
                obj_elem.appendChild(bbox_elem)
                
                # Ajouter des balises de segmentation vides si demandé
                if include_segmentation:
                    segmented_elem = doc.createElement("segmented")
                    segmented_elem.appendChild(doc.createTextNode("0"))
                    root.appendChild(segmented_elem)
                    
                    segm_elem = doc.createElement("segmentation")
                    obj_elem.appendChild(segm_elem)
                
                root.appendChild(obj_elem)
            
            # Écrire le fichier XML
            xml_str = doc.toprettyxml(indent="  ")
            with open(output_dir / f"{image.path.stem}.xml", 'w', encoding='utf-8') as f:
                f.write(xml_str)
            
        except Exception as e:
            self.logger.warning(f"Échec de création du fichier d'annotation VOC pour {image.path.name}: {str(e)}")
    
    def _create_voc_imagesets(self, image_names: List[str], output_dir: Path):
        """
        Crée les fichiers ImageSets pour VOC
        
        Args:
            image_names: Liste des noms d'images (sans extension)
            output_dir: Répertoire de destination
        """
        try:
            # Créer un fichier avec tous les noms d'images
            with open(output_dir / "trainval.txt", 'w', encoding='utf-8') as f:
                for name in image_names:
                    f.write(f"{name}\n")
            
            # Division standard 80% train, 20% val
            train_count = int(len(image_names) * 0.8)
            
            # Fichier train
            with open(output_dir / "train.txt", 'w', encoding='utf-8') as f:
                for name in image_names[:train_count]:
                    f.write(f"{name}\n")
            
            # Fichier val
            with open(output_dir / "val.txt", 'w', encoding='utf-8') as f:
                for name in image_names[train_count:]:
                    f.write(f"{name}\n")
            
            self.logger.info(f"Fichiers ImageSets créés : {output_dir}")
            
        except Exception as e:
            self.logger.warning(f"Échec de création des fichiers ImageSets: {str(e)}")
    
    def export_dataset_config(
        self, 
        dataset: Dataset, 
        output_path: Optional[Path] = None,
        export_options: Optional[Dict] = None
    ) -> Path:
        """
        Exporte la configuration du dataset
        
        Args:
            dataset: Dataset à exporter
            output_path: Chemin de sortie (optionnel)
            export_options: Options d'export utilisées
            
        Returns:
            Chemin du fichier de configuration
        """
        try:
            # Définir le chemin de sortie par défaut
            if output_path is None:
                output_path = dataset.path / f"{dataset.name}_config.json"
            
            # Préparer les données à sauvegarder
            config_data = {
                "name": dataset.name,
                "version": dataset.version,
                "classes": dataset.classes,
                "metadata": dataset.metadata,
                "created_at": dataset.created_at.isoformat(),
                "modified_at": dataset.modified_at.isoformat() if dataset.modified_at else None,
                "total_images": len(dataset.images),
                "total_annotations": sum(len(img.annotations) for img in dataset.images),
                "export_timestamp": datetime.now().isoformat()
            }
            
            # Ajouter les options d'export si fournies
            if export_options:
                config_data["export_options"] = export_options
            
            # Sauvegarder dans un fichier JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, default=str)
                
            self.logger.info(f"Configuration du dataset exportée : {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Échec de l'export de la configuration : {str(e)}")
            raise ExportError(f"Échec de l'export de la configuration : {str(e)}")

    def export_dataset_summary(self, dataset: Dataset, output_path: Optional[Path] = None) -> Path:
        """
        Exporte un résumé du dataset au format CSV
        
        Args:
            dataset: Dataset à exporter
            output_path: Chemin de sortie (optionnel)
            
        Returns:
            Chemin du fichier CSV
        """
        try:
            # Définir le chemin de sortie par défaut
            if output_path is None:
                output_path = dataset.path / f"{dataset.name}_summary.csv"
            
            # Créer le répertoire parent si nécessaire
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Préparer les données
            summary_data = []
            for image in dataset.images:
                # Compter les annotations par classe
                class_counts = {}
                for ann in image.annotations:
                    class_id = ann.class_id
                    if class_id not in class_counts:
                        class_counts[class_id] = 0
                    class_counts[class_id] += 1
                
                # Créer une ligne pour l'image
                row = {
                    "image_id": image.id,
                    "file_name": image.path.name,
                    "width": image.width,
                    "height": image.height,
                    "source": image.source.value,
                    "annotations_count": len(image.annotations)
                }
                
                # Ajouter le compte de chaque classe
                for class_id, class_name in dataset.classes.items():
                    row[f"class_{class_id}_{class_name}"] = class_counts.get(class_id, 0)
                
                summary_data.append(row)
            
            # Écrire le fichier CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if summary_data:
                    writer = csv.DictWriter(f, fieldnames=summary_data[0].keys())
                    writer.writeheader()
                    writer.writerows(summary_data)
                else:
                    # Si aucune donnée, écrire un en-tête minimal
                    writer = csv.writer(f)
                    writer.writerow(["image_id", "file_name", "annotations_count"])
            
            self.logger.info(f"Résumé du dataset exporté : {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Échec de l'export du résumé : {str(e)}")
            raise ExportError(f"Échec de l'export du résumé : {str(e)}")
            
    def export_class_distribution(self, dataset: Dataset, output_path: Optional[Path] = None) -> Path:
        """
        Exporte la distribution des classes du dataset en format CSV
        
        Args:
            dataset: Dataset à analyser
            output_path: Chemin de sortie (optionnel)
            
        Returns:
            Chemin du fichier CSV
        """
        try:
            # Définir le chemin de sortie par défaut
            if output_path is None:
                output_path = dataset.path / f"{dataset.name}_class_distribution.csv"
            
            # Créer le répertoire parent si nécessaire
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Compter les annotations par classe
            class_stats = {}
            for class_id, class_name in dataset.classes.items():
                class_stats[class_id] = {
                    "class_id": class_id,
                    "class_name": class_name,
                    "annotation_count": 0,
                    "image_count": 0,
                    "images": set()
                }
            
            # Calculer les statistiques
            for image in dataset.images:
                classes_in_image = set()
                
                for ann in image.annotations:
                    class_id = ann.class_id
                    if class_id in class_stats:
                        class_stats[class_id]["annotation_count"] += 1
                        classes_in_image.add(class_id)
                
                # Mettre à jour le nombre d'images par classe
                for class_id in classes_in_image:
                    class_stats[class_id]["image_count"] += 1
                    class_stats[class_id]["images"].add(image.id)
            
            # Préparer les données pour le CSV
            distribution_data = []
            for class_id, stats in class_stats.items():
                distribution_data.append({
                    "class_id": stats["class_id"],
                    "class_name": stats["class_name"],
                    "annotation_count": stats["annotation_count"],
                    "image_count": stats["image_count"],
                    "percentage_of_total": (stats["annotation_count"] / sum(s["annotation_count"] for s in class_stats.values())) * 100 if sum(s["annotation_count"] for s in class_stats.values()) > 0 else 0,
                    "avg_per_image": stats["annotation_count"] / stats["image_count"] if stats["image_count"] > 0 else 0
                })
            
            # Trier par nombre d'annotations
            distribution_data.sort(key=lambda x: x["annotation_count"], reverse=True)
            
            # Écrire le fichier CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if distribution_data:
                    writer = csv.DictWriter(f, fieldnames=distribution_data[0].keys())
                    writer.writeheader()
                    writer.writerows(distribution_data)
                else:
                    writer = csv.writer(f)
                    writer.writerow(["class_id", "class_name", "annotation_count", "image_count", "percentage_of_total", "avg_per_image"])
            
            self.logger.info(f"Distribution des classes exportée : {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Échec de l'export de la distribution des classes : {str(e)}")
            raise ExportError(f"Échec de l'export de la distribution des classes : {str(e)}")
            
    def export_annotation_sizes(self, dataset: Dataset, output_path: Optional[Path] = None) -> Path:
        """
        Exporte les statistiques de taille des annotations en format CSV
        
        Args:
            dataset: Dataset à analyser
            output_path: Chemin de sortie (optionnel)
            
        Returns:
            Chemin du fichier CSV
        """
        try:
            # Définir le chemin de sortie par défaut
            if output_path is None:
                output_path = dataset.path / f"{dataset.name}_annotation_sizes.csv"
            
            # Créer le répertoire parent si nécessaire
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Préparer les données
            size_data = []
            for image in dataset.images:
                for i, ann in enumerate(image.annotations):
                    # Calculer les dimensions en pixels
                    width_px = ann.bbox.width * image.width
                    height_px = ann.bbox.height * image.height
                    area_px = width_px * height_px
                    
                    # Calculer le ratio d'aspect
                    aspect_ratio = width_px / height_px if height_px > 0 else 0
                    
                    # Ajouter les données
                    size_data.append({
                        "image_id": image.id,
                        "annotation_index": i,
                        "class_id": ann.class_id,
                        "class_name": dataset.classes.get(ann.class_id, f"class_{ann.class_id}"),
                        "width_normalized": ann.bbox.width,
                        "height_normalized": ann.bbox.height,
                        "width_px": width_px,
                        "height_px": height_px,
                        "area_px": area_px,
                        "aspect_ratio": aspect_ratio,
                        "relative_size": (ann.bbox.width * ann.bbox.height) * 100  # Pourcentage de l'image
                    })
            
            # Écrire le fichier CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if size_data:
                    writer = csv.DictWriter(f, fieldnames=size_data[0].keys())
                    writer.writeheader()
                    writer.writerows(size_data)
                else:
                    writer = csv.writer(f)
                    writer.writerow(["image_id", "annotation_index", "class_id", "class_name", "width_normalized", "height_normalized", "width_px", "height_px", "area_px", "aspect_ratio", "relative_size"])
            
            self.logger.info(f"Statistiques de taille des annotations exportées : {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Échec de l'export des statistiques de taille : {str(e)}")
            raise ExportError(f"Échec de l'export des statistiques de taille : {str(e)}")