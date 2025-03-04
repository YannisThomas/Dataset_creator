# src/database/db_manager.py

from typing import Optional, Dict, Any
from pathlib import Path

class DatabaseManager:
    """
    Gestionnaire de base de données pour le stockage persistant des datasets.
    Cette classe gère les interactions avec la base de données SQLite.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialise le gestionnaire de base de données.
        
        Args:
            db_path: Chemin vers le fichier de base de données
        """
        self.db_path = db_path or Path("data/yolo_datasets.db")
        self.engine = None
        self.session = None
        
        # Créer le répertoire parent si nécessaire
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialiser la connexion
        self._init_connection()
        
    def _init_connection(self):
        """Initialise la connexion à la base de données."""
        # Cette méthode devrait normalement initialiser SQLAlchemy
        # Pour l'instant, nous la laissons vide pour débloquer l'importation
        pass
        
    def save_dataset(self, dataset):
        """
        Sauvegarde un dataset dans un fichier JSON.
        
        Args:
            dataset: Dataset à sauvegarder
            
        Returns:
            True si la sauvegarde a réussi
        """
        try:
            # Créer le répertoire de stockage
            storage_dir = Path("data/datasets")
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Convertir le dataset en dictionnaire
            dataset_dict = {
                "name": dataset.name,
                "version": dataset.version,
                "path": str(dataset.path),
                "classes": dataset.classes,
                "created_at": dataset.created_at.isoformat(),
                "modified_at": dataset.modified_at.isoformat() if dataset.modified_at else None,
                "metadata": dataset.metadata
            }
            
            # Sauvegarder les métadonnées du dataset
            meta_file = storage_dir / f"{dataset.name}_meta.json"
            with open(meta_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(dataset_dict, f, indent=2, ensure_ascii=False)
            
            # Sauvegarder les images et annotations
            images_data = []
            for img in dataset.images:
                image_dict = {
                    "id": img.id,
                    "path": str(img.path),
                    "width": img.width,
                    "height": img.height,
                    "source": img.source.value,
                    "created_at": img.created_at.isoformat(),
                    "modified_at": img.modified_at.isoformat() if img.modified_at else None,
                    "metadata": img.metadata,
                    "annotations": []
                }
                
                for ann in img.annotations:
                    ann_dict = {
                        "class_id": ann.class_id,
                        "bbox": {
                            "x": ann.bbox.x,
                            "y": ann.bbox.y,
                            "width": ann.bbox.width,
                            "height": ann.bbox.height
                        },
                        "confidence": ann.confidence,
                        "type": ann.type.value,
                        "metadata": ann.metadata
                    }
                    image_dict["annotations"].append(ann_dict)
                
                images_data.append(image_dict)
            
            # Sauvegarder les données des images
            images_file = storage_dir / f"{dataset.name}_images.json"
            with open(images_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(images_data, f, indent=2, ensure_ascii=False)
            
            print(f"Dataset {dataset.name} sauvegardé")
            return True
        
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du dataset: {str(e)}")
            return False

    def load_dataset(self, name: str):
        """
        Charge un dataset depuis un fichier JSON.
        
        Args:
            name: Nom du dataset à charger
            
        Returns:
            Dataset chargé ou None si non trouvé
        """
        try:
            # Vérifier l'existence des fichiers du dataset
            storage_dir = Path("data/datasets")
            meta_file = storage_dir / f"{name}_meta.json"
            images_file = storage_dir / f"{name}_images.json"
            
            if not meta_file.exists() or not images_file.exists():
                print(f"Dataset {name} non trouvé")
                return None
            
            # Charger les métadonnées
            with open(meta_file, 'r', encoding='utf-8') as f:
                import json
                meta_data = json.load(f)
            
            # Créer le dataset
            from datetime import datetime
            from src.models import Dataset
            
            dataset = Dataset(
                name=meta_data["name"],
                version=meta_data["version"],
                path=Path(meta_data["path"]),
                classes=meta_data["classes"],
                created_at=datetime.fromisoformat(meta_data["created_at"]),
                metadata=meta_data["metadata"]
            )
            
            if meta_data.get("modified_at"):
                dataset.modified_at = datetime.fromisoformat(meta_data["modified_at"])
            
            # Charger les images et annotations
            with open(images_file, 'r', encoding='utf-8') as f:
                import json
                images_data = json.load(f)
            
            # Reconstruire les images et annotations
            from src.models import Image, Annotation, BoundingBox
            from src.models.enums import ImageSource, AnnotationType
            
            for img_data in images_data:
                # Créer l'image
                image = Image(
                    id=img_data["id"],
                    path=Path(img_data["path"]),
                    width=img_data["width"],
                    height=img_data["height"],
                    source=ImageSource(img_data["source"]),
                    created_at=datetime.fromisoformat(img_data["created_at"]),
                    metadata=img_data["metadata"]
                )
                
                if img_data.get("modified_at"):
                    image.modified_at = datetime.fromisoformat(img_data["modified_at"])
                
                # Ajouter les annotations
                for ann_data in img_data.get("annotations", []):
                    bbox = BoundingBox(
                        x=ann_data["bbox"]["x"],
                        y=ann_data["bbox"]["y"],
                        width=ann_data["bbox"]["width"],
                        height=ann_data["bbox"]["height"]
                    )
                    
                    annotation = Annotation(
                        class_id=ann_data["class_id"],
                        bbox=bbox,
                        confidence=ann_data.get("confidence"),
                        type=AnnotationType(ann_data["type"]),
                        metadata=ann_data.get("metadata", {})
                    )
                    
                    image.add_annotation(annotation)
                
                # Ajouter l'image au dataset
                dataset.add_image(image)
            
            print(f"Dataset {name} chargé")
            return dataset
        
        except Exception as e:
            print(f"Erreur lors du chargement du dataset: {str(e)}")
            return None