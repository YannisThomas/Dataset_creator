# src/models/dataset.py

from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field, field_validator

from .image import Image

class Dataset(BaseModel):    
    """Représente un jeu de données complet"""
    name: str
    version: str = "1.0.0"
    path: Path
    classes: Dict[int, str]
    images: List[Image] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: Optional[datetime] = None
    metadata: Dict = Field(default_factory=dict)
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v):
        """Valide et crée le chemin du dataset si nécessaire"""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path
        
    def add_image(self, image: 'Image'):
        """Ajoute une image au jeu de données"""
        self.images.append(image)
        self.modified_at = datetime.now()
        
    def remove_image(self, image: 'Image'):
        """Retire une image du jeu de données"""
        if image in self.images:
            self.images.remove(image)
            self.modified_at = datetime.now()
            
    def get_stats(self) -> Dict:
        """Retourne des statistiques sur le jeu de données"""
        stats = {
            "total_images": len(self.images),
            "total_annotations": sum(len(img.annotations) for img in self.images),
            "annotations_per_class": {},
            "images_per_class": {},
            "avg_annotations_per_image": 0,
            "classes": len(self.classes)
        }
        
        for img in self.images:
            for ann in img.annotations:
                if ann.class_id not in stats["annotations_per_class"]:
                    stats["annotations_per_class"][ann.class_id] = 0
                stats["annotations_per_class"][ann.class_id] += 1
                
                if ann.class_id not in stats["images_per_class"]:
                    stats["images_per_class"][ann.class_id] = set()
                stats["images_per_class"][ann.class_id].add(img.id)
        
        stats["images_per_class"] = {
            k: len(v) for k, v in stats["images_per_class"].items()
        }
        
        if stats["total_images"] > 0:
            stats["avg_annotations_per_image"] = (
                stats["total_annotations"] / stats["total_images"]
            )
            
        return stats
        


    def validate_dataset(self) -> Dict:
        """Valide l'intégrité du jeu de données avec une gestion robuste des chemins"""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 1. Vérifier les classes utilisées
        used_classes = set()
        for img in self.images:
            for ann in img.annotations:
                used_classes.add(ann.class_id)
                
        undefined_classes = used_classes - set(self.classes.keys())
        if undefined_classes:
            validation["valid"] = False
            validation["errors"].append(
                f"Classes non définies utilisées dans les annotations: {undefined_classes}"
            )
        
        # 2. Vérifier l'existence des fichiers d'images
        for img in self.images:
            try:
                # Récupérer le chemin de l'image
                img_path = img.path
                
                # Si c'est une chaîne qui ressemble à une URL, ne pas vérifier l'existence
                if isinstance(img_path, str) and (img_path.startswith('http:') or img_path.startswith('https:')):
                    # Stocker un avertissement et continuer
                    validation["warnings"].append(f"Impossible de vérifier l'existence de l'URL: {img_path}")
                    continue
                    
                # Convertir en Path si c'est une chaîne
                if isinstance(img_path, str):
                    from pathlib import Path
                    img_path = Path(img_path)
                
                # Vérifier l'existence du fichier
                if not img_path.exists():
                    validation["valid"] = False
                    validation["errors"].append(f"Fichier image manquant: {img_path}")
            except Exception as e:
                # En cas d'erreur, ajouter un avertissement et continuer
                validation["warnings"].append(f"Erreur lors de la vérification du chemin pour {img.id}: {str(e)}")
        
        # 3. Vérifier les annotations
        for img in self.images:
            for ann in img.annotations:
                try:
                    bbox = ann.bbox
                    # Vérifier les limites des coordonnées
                    if bbox.x < 0 or bbox.y < 0 or bbox.width <= 0 or bbox.height <= 0:
                        validation["errors"].append(
                            f"Boîte englobante invalide dans l'image {img.id}: coordonnées négatives ou dimensions nulles"
                        )
                        validation["valid"] = False
                    elif bbox.x + bbox.width > 1 or bbox.y + bbox.height > 1:
                        validation["errors"].append(
                            f"Boîte englobante invalide dans l'image {img.id}: dépasse les limites"
                        )
                        validation["valid"] = False
                except Exception as e:
                    validation["errors"].append(
                        f"Erreur lors de la validation de l'annotation dans l'image {img.id}: {str(e)}"
                    )
                    validation["valid"] = False
        
        return validation