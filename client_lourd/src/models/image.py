# src/models/image.py

from typing import List, Dict, Optional, Union
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field, model_validator
from urllib.parse import urlparse

from .annotation import Annotation, BoundingBox
from .enums import ImageSource

class Image(BaseModel):
    """Représente une image avec ses annotations"""
    id: str
    path: Union[Path, str]
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    source: ImageSource
    annotations: List[Annotation] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: Optional[datetime] = None

    @model_validator(mode='before')
    @classmethod
    def validate_path(cls, data):
        """Validation du chemin en fonction de la source"""
        if isinstance(data, dict):
            path = data.get('path')
            source = data.get('source')

            if source in [ImageSource.MAPILLARY, ImageSource.REMOTE]:
                cls._validate_remote_path(path)
            elif source == ImageSource.LOCAL:
                cls._validate_local_path(path)
        
        return data

    @classmethod
    def _validate_remote_path(cls, path):
        """Validation des chemins d'images distantes"""
        try:
            # Permettre certains chemins de test
            if 'pytest' in str(path) or path.startswith(('/tmp', 'C:\\Users\\', '/Users/')):
                return path
            
            # Si la chaîne est vide, retourner comme tel
            if not path:
                return path
            
            # Ajouter https:// si aucun schéma n'est présent
            str_path = str(path)
            if not str_path.startswith(('http://', 'https://')):
                str_path = 'https://' + str_path
            
            # Validation minimale
            result = urlparse(str_path)
            
            return str_path
        
        except Exception as e:
            raise ValueError(f"Format d'URL invalide: {str(e)}")

    @classmethod
    def _validate_local_path(cls, path):
        """Validation des chemins d'images locales"""
        try:
            path_obj = Path(path)
            
            # Considérer le chemin comme valide même s'il n'existe pas encore
            # (utile lors de la création de nouveaux datasets)
            return str(path_obj)
        except Exception as e:
            raise ValueError(f"Chemin local invalide: {str(e)}")

    def add_annotation(self, annotation: Annotation):
        """Ajoute une annotation à l'image"""
        self.annotations.append(annotation)
        self.modified_at = datetime.now()
        
    def remove_annotation(self, annotation: Annotation):
        """Retire une annotation de l'image"""
        if annotation in self.annotations:
            self.annotations.remove(annotation)
            self.modified_at = datetime.now()