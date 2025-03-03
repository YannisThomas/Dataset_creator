# src/services/export_service.py

import json
import shutil
from pathlib import Path
from typing import Dict, Union, Optional

from src.models import Dataset, Image
from src.models.enums import DatasetFormat
from src.utils.logger import Logger
from src.core.exceptions import ExportError

class ExportService:
    """Service d'exportation des datasets"""
    
    def __init__(self, logger: Optional[Logger] = None):
        """
        Initialise le service d'export
        
        Args:
            logger: Gestionnaire de logs
        """
        self.logger = logger or Logger()
    
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
            # Convertir le format en enum si nécessaire
            if isinstance(export_format, str):
                export_format = DatasetFormat(export_format.lower())
            
            # Définir le chemin de sortie par défaut
            if output_path is None:
                output_path = Path(f"exports/{dataset.name}_{export_format.value}")
            
            # Créer le répertoire de sortie
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Exporter selon le format
            if export_format == DatasetFormat.YOLO:
                return self._export_yolo(dataset, output_path)
            elif export_format == DatasetFormat.COCO:
                return self._export_coco(dataset, output_path)
            elif export_format == DatasetFormat.VOC:
                return self._export_voc(dataset, output_path)
            else:
                raise ExportError(f"Format d'export non supporté : {export_format}")
        
        except Exception as e:
            self.logger.error(f"Échec de l'export du dataset : {str(e)}")
            raise ExportError(f"Échec de l'export : {str(e)}")
    
    def _export_yolo(self, dataset: Dataset, output_path: Path) -> Path:
        """
        Exporte un dataset au format YOLO
        
        Args:
            dataset: Dataset à exporter
            output_path: Chemin de sortie
            
        Returns:
            Chemin du répertoire d'export
        """
        try:
            # Créer les sous-répertoires
            images_dir = output_path / "images"
            labels_dir = output_path / "labels"
            images_dir.mkdir(parents=True, exist_ok=True)
            labels_dir.mkdir(parents=True, exist_ok=True)
            
            # Créer le fichier classes.txt
            with open(output_path / "classes.txt", 'w') as f:
                for class_id, class_name in dataset.classes.items():
                    f.write(f"{class_name}\n")
            
            # Exporter chaque image et ses annotations
            for image in dataset.images:
                # Copier l'image
                dest_image_path = images_dir / image.path.name
                shutil.copy(image.path, dest_image_path)
                
                # Créer le fichier d'annotations
                label_path = labels_dir / f"{image.path.stem}.txt"
                with open(label_path, 'w') as f:
                    for ann in image.annotations:
                        # Format YOLO : class_id x_center y_center width height
                        f.write(
                            f"{ann.class_id} "
                            f"{ann.bbox.x + ann.bbox.width/2} "
                            f"{ann.bbox.y + ann.bbox.height/2} "
                            f"{ann.bbox.width} "
                            f"{ann.bbox.height}\n"
                        )
            
            self.logger.info(f"Export YOLO terminé : {output_path}")
            return output_path
            
        except Exception as e:
            raise ExportError(f"Échec de l'export YOLO : {str(e)}")
    
    def _export_coco(self, dataset: Dataset, output_path: Path) -> Path:
        """
        Exporte un dataset au format COCO
        
        Args:
            dataset: Dataset à exporter
            output_path: Chemin de sortie
            
        Returns:
            Chemin du répertoire d'export
        """
        try:
            # Structure de base COCO
            coco_data = {
                "info": {
                    "description": dataset.name,
                    "version": dataset.version
                },
                "images": [],
                "annotations": [],
                "categories": [
                    {"id": class_id, "name": class_name} 
                    for class_id, class_name in dataset.classes.items()
                ]
            }
            
            # Convertir les images et annotations
            ann_id = 1
            for img_idx, image in enumerate(dataset.images, 1):
                # Ajouter l'image
                coco_data["images"].append({
                    "id": img_idx,
                    "file_name": image.path.name,
                    "width": image.width,
                    "height": image.height
                })
                
                # Ajouter les annotations
                for ann in image.annotations:
                    coco_data["annotations"].append({
                        "id": ann_id,
                        "image_id": img_idx,
                        "category_id": ann.class_id,
                        "bbox": [
                            ann.bbox.x * image.width,
                            ann.bbox.y * image.height,
                            ann.bbox.width * image.width,
                            ann.bbox.height * image.height
                        ],
                        "area": ann.bbox.width * ann.bbox.height * image.width * image.height,
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
    
    def _export_voc(self, dataset: Dataset, output_path: Path) -> Path:
        """
        Exporte un dataset au format VOC
        
        Args:
            dataset: Dataset à exporter
            output_path: Chemin de sortie
            
        Returns:
            Chemin du répertoire d'export
        """
        try:
            # Créer les sous-répertoires
            images_dir = output_path / "JPEGImages"
            annotations_dir = output_path / "Annotations"
            images_dir.mkdir(parents=True, exist_ok=True)
            annotations_dir.mkdir(parents=True, exist_ok=True)
            
            # Créer le fichier classes.txt
            with open(output_path / "classes.txt", 'w') as f:
                for class_name in dataset.classes.values():
                    f.write(f"{class_name}\n")
            
            # Exporter chaque image et ses annotations
            for image in dataset.images:
                # Copier l'image
                dest_image_path = images_dir / image.path.name
                shutil.copy(image.path, dest_image_path)
                
                # Créer le fichier XML d'annotations
                label_path = annotations_dir / f"{image.path.stem}.xml"
                with open(label_path, 'w', encoding='utf-8') as f:
                    f.write(f'''<?xml version="1.0"?>
<annotation>
    <filename>{image.path.name}</filename>
    <size>
        <width>{image.width}</width>
        <height>{image.height}</height>
        <depth>3</depth>
    </size>
    {"".join(f"""
    <object>
        <name>{dataset.classes[ann.class_id]}</name>
        <bndbox>
            <xmin>{int(ann.bbox.x * image.width)}</xmin>
            <ymin>{int(ann.bbox.y * image.height)}</ymin>
            <xmax>{int((ann.bbox.x + ann.bbox.width) * image.width)}</xmax>
            <ymax>{int((ann.bbox.y + ann.bbox.height) * image.height)}</ymax>
        </bndbox>
    </object>""" for ann in image.annotations)}
</annotation>''')
            
            self.logger.info(f"Export VOC terminé : {output_path}")
            return output_path
            
        except Exception as e:
            raise ExportError(f"Échec de l'export VOC : {str(e)}")
    
    def export_dataset_config(self, dataset: Dataset, output_path: Optional[Path] = None) -> Path:
        """
        Exporte la configuration du dataset
        
        Args:
            dataset: Dataset à exporter
            output_path: Chemin de sortie (optionnel)
            
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
                "total_annotations": sum(len(img.annotations) for img in dataset.images)
            }
            
            # Sauvegarder dans un fichier JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, default=str)
                
            self.logger.info(f"Configuration du dataset exportée : {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Échec de l'export de la configuration : {str(e)}")
            raise ExportError(f"Échec de l'export de la configuration : {str(e)}")