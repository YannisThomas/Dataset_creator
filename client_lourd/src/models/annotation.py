# src/models/annotation.py

from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator

from .enums import AnnotationType

class BoundingBox(BaseModel):
    """Représente une boîte englobante au format YOLO (normalisé)"""
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    width: float = Field(..., ge=0.0, le=1.0)
    height: float = Field(..., ge=0.0, le=1.0)
    
    @field_validator('x', 'y', 'width', 'height')
    @classmethod
    def validate_coordinates(cls, v, info):
        """Vérifie et ajuste les coordonnées pour qu'elles soient valides"""
        field_name = info.field_name
        
        # Limiter les valeurs entre 0 et 1
        v = max(0.0, min(v, 1.0))
        
        # Assurer que les dimensions respectent les limites
        if field_name in ['width', 'height'] and v <= 0:
            v = 0.001  # Une valeur minimale positive
            
        # Pour width et height, s'assurer que la somme ne dépasse pas 1
        if field_name == 'width':
            x = info.data.get('x', 0)
            if x + v > 1:
                v = 1.0 - x
        elif field_name == 'height':
            y = info.data.get('y', 0)
            if y + v > 1:
                v = 1.0 - y
                
        return v

class Annotation(BaseModel):
    """Représente une annotation"""
    class_id: int = Field(..., ge=0)
    bbox: BoundingBox
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    type: AnnotationType = AnnotationType.BBOX
    metadata: Dict = Field(default_factory=dict)
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError("La confiance doit être comprise entre 0 et 1")
        return v