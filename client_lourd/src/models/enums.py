# src/models/enums.py

from enum import Enum, auto

class DatasetFormat(str, Enum):
    """Format d'export du dataset"""
    YOLO = "yolo"
    COCO = "coco"
    VOC = "voc"
    
class AnnotationType(str, Enum):
    """Type d'annotation"""
    BBOX = "bbox"
    SEGMENTATION = "segmentation"
    KEYPOINT = "keypoint"

class ImageSource(str, Enum):
    """Source de l'image"""
    MAPILLARY = "mapillary"
    LOCAL = "local"
    IMPORTED = "imported"
    REMOTE = "remote"