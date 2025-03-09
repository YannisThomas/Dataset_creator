# src/utils/config.py

from typing import Dict, Any, Optional, Union
from pathlib import Path
import json
import os
from dotenv import load_dotenv

from pydantic import BaseModel, Field, field_validator

from src.core.exceptions import ConfigurationError
from src.utils.logger import Logger

class APIConfig(BaseModel):
    """Configuration pour les APIs externes"""
    mapillary_token: Optional[str] = None
    mapillary_url: str = "https://graph.mapillary.com"
    request_timeout: int = Field(30, ge=1)
    max_retries: int = Field(3, ge=0)
    batch_size: int = Field(50, ge=1, le=100)
    fields: Dict[str, str] = Field(default_factory=lambda: {
        "detections": "id,value,geometry,area,properties"
    })

class StorageConfig(BaseModel):
    """Configuration pour le stockage"""
    base_dir: Path = Path("data")
    dataset_dir: Path = Field(default=Path("data/datasets"))
    cache_dir: Path = Field(default=Path("data/cache"))
    db_path: Path = Field(default=Path("data/yolo_datasets.db"))
    max_cache_size_mb: int = Field(1000, ge=0)
    
    @field_validator('base_dir', 'dataset_dir', 'cache_dir')
    @classmethod
    def validate_directory(cls, v):
        """Crée le répertoire s'il n'existe pas"""
        v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v
        
    @field_validator('db_path')
    @classmethod
    def validate_db_path(cls, v):
        """Crée le répertoire parent du fichier de base de données"""
        v = Path(v)
        v.parent.mkdir(parents=True, exist_ok=True)
        return v

class DatasetConfig(BaseModel):
    """Configuration pour les datasets"""
    default_version: str = "1.0.0"
    min_image_size: int = Field(32, ge=16)
    max_image_size: int = Field(4096, le=8192)
    supported_formats: list = ["jpg", "jpeg", "png"]
    default_classes: Dict[int, str] = {0: "Panneau"}
    export_formats: list = ["yolo", "coco", "voc"]

class UIConfig(BaseModel):
    """Configuration pour l'interface utilisateur"""
    window_width: int = Field(1280, ge=800)
    window_height: int = Field(720, ge=600)
    theme: str = "light"
    language: str = "fr"
    max_recent_datasets: int = Field(5, ge=1, le=10)

class Configuration(BaseModel):
    """Configuration globale de l'application"""
    api: APIConfig
    storage: StorageConfig
    dataset: DatasetConfig
    ui: UIConfig
    debug_mode: bool = False
    # Ajouter ces attributs manquants
    mapillary_config: Dict[str, Any] = Field(default_factory=dict)
    class_mapping: Dict[str, Any] = Field(default_factory=dict)

class ConfigManager:
    """
    Gestionnaire de configuration avec support des variables d'environnement
    et des fichiers de configuration
    """
    
    def __init__(
        self, 
        config_path: Optional[Union[str, Path]] = None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le gestionnaire de configuration
        
        Args:
            config_path: Chemin vers un fichier de configuration personnalisé
            logger: Gestionnaire de logs
        """
        self.logger = logger or Logger()
        self.config: Optional[Configuration] = None
        
        # Charger les variables d'environnement
        self._load_env()
        
        # Charger la configuration
        self.load_config(config_path)
    
    def _load_env(self):
        """
        Charge les variables d'environnement
        """
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(env_path)
        
    def load_config(
        self, 
        config_path: Optional[Union[str, Path]] = None
    ) -> Configuration:
        """
        Charge la configuration à partir d'un fichier ou utilise les valeurs par défaut
        
        Args:
            config_path: Chemin vers le fichier de configuration
            
        Returns:
            Configuration chargée
        """
        try:
            # Utiliser un fichier de configuration personnalisé ou le fichier par défaut
            if config_path:
                config_path = Path(config_path)
                if not config_path.exists():
                    raise ConfigurationError(f"Fichier de configuration non trouvé : {config_path}")
                
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
            else:
                # Utiliser les valeurs par défaut
                config_dict = self._get_default_config()
            
            # Fusionner avec les variables d'environnement
            config_dict = self._merge_env_config(config_dict)
            
            # Valider et créer la configuration
            self.config = Configuration(**config_dict)
            
            self.logger.info("Configuration chargée avec succès")
            return self.config
        
        except Exception as e:
            self.logger.error(f"Échec du chargement de la configuration : {str(e)}")
            raise ConfigurationError(f"Erreur de configuration : {str(e)}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Génère une configuration par défaut
        
        Returns:
            Dictionnaire de configuration par défaut
        """
        try:
            # Log détaillé de la source du token
            mapillary_token = None
            
            # Charger depuis mapillary_config.json
            # Utiliser le chemin correct vers le fichier de configuration
            config_dir = Path(__file__).parent.parent / "config"
            mapillary_config_path = config_dir / "mapillary_config.json"
            
            self.logger.debug(f"Chemin du fichier de configuration : {mapillary_config_path}")
            self.logger.debug(f"Le fichier existe : {mapillary_config_path.exists()}")
            
            # Configuration Mapillary par défaut
            default_mapillary_config = {
                "detection_mapping": {
                    "conversion": {
                        "min_confidence": 0.5
                    }
                },
                "class_mapping": {}
            }
            
            # Tenter de charger la configuration Mapillary
            loaded_mapillary_config = {}
            if mapillary_config_path.exists():
                try:
                    with open(mapillary_config_path, 'r', encoding='utf-8') as f:
                        loaded_mapillary_config = json.load(f)
                        
                    self.logger.debug(f"Configuration chargée : {loaded_mapillary_config}")
                    
                    if 'api' in loaded_mapillary_config and 'mapillary_token' in loaded_mapillary_config['api']:
                        mapillary_token = loaded_mapillary_config['api']['mapillary_token']
                        self.logger.info(f"Token Mapillary chargé depuis le fichier. Longueur : {len(mapillary_token)}")
                except Exception as e:
                    self.logger.error(f"Impossible de charger le token Mapillary : {str(e)}")
            
            # Fusionner la configuration chargée avec la configuration par défaut
            merged_mapillary_config = {**default_mapillary_config, **loaded_mapillary_config}
            
            # Fallback sur la variable d'environnement
            if not mapillary_token:
                mapillary_token = os.getenv("MAPILLARY_TOKEN")
                if mapillary_token:
                    self.logger.info("Token chargé depuis la variable d'environnement")
            
            # Log de débogage
            if mapillary_token:
                self.logger.debug(f"Token final - Commence par : {mapillary_token[:10]}")
            else:
                self.logger.error("AUCUN TOKEN MAPILLARY TROUVÉ")
            
            return {
                "api": {
                    "mapillary_token": mapillary_token,
                    "mapillary_url": "https://graph.mapillary.com",
                    "request_timeout": 30,
                    "max_retries": 3,
                    "batch_size": 50,
                    "fields": {
                        "detections": "id,value,geometry,area,properties"
                    }
                },
                "storage": {
                    "base_dir": "data",
                    "dataset_dir": "data/datasets",
                    "cache_dir": "data/cache",
                    "db_path": "data/yolo_datasets.db",
                    "max_cache_size_mb": 1000
                },
                "dataset": {
                    "default_version": "1.0.0",
                    "min_image_size": 32,
                    "max_image_size": 4096,
                    "supported_formats": ["jpg", "jpeg", "png"],
                    "default_classes": {0: "Panneau"},
                    "export_formats": ["yolo", "coco", "voc"]
                },
                "ui": {
                    "window_width": 1280,
                    "window_height": 720,
                    "theme": "light",
                    "language": "fr",
                    "max_recent_datasets": 5
                },
                "debug_mode": bool(os.getenv("DEBUG", False)),
                # Ajouter ces attributs manquants
                "mapillary_config": merged_mapillary_config,
                "class_mapping": merged_mapillary_config.get("class_mapping", {})
            }
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération de la configuration : {str(e)}")
            
            # Configuration par défaut minimale en cas d'erreur
            return {
                "api": {
                    "mapillary_token": None,
                    "mapillary_url": "https://graph.mapillary.com",
                    "request_timeout": 30,
                    "max_retries": 3,
                    "batch_size": 50,
                    "fields": {
                        "detections": "id,value,geometry,area,properties"
                    }
                },
                "storage": {
                    "base_dir": "data",
                    "dataset_dir": "data/datasets",
                    "cache_dir": "data/cache",
                    "db_path": "data/yolo_datasets.db",
                    "max_cache_size_mb": 1000
                },
                "dataset": {
                    "default_version": "1.0.0",
                    "min_image_size": 32,
                    "max_image_size": 4096,
                    "supported_formats": ["jpg", "jpeg", "png"],
                    "default_classes": {0: "Panneau"},
                    "export_formats": ["yolo", "coco", "voc"]
                },
                "ui": {
                    "window_width": 1280,
                    "window_height": 720,
                    "theme": "light",
                    "language": "fr",
                    "max_recent_datasets": 5
                },
                "debug_mode": bool(os.getenv("DEBUG", False)),
                # Ajouter ces attributs manquants dans la config minimale aussi
                "mapillary_config": {
                    "detection_mapping": {
                        "conversion": {
                            "min_confidence": 0.5
                        }
                    },
                    "class_mapping": {}
                },
                "class_mapping": {}
            }
    
    def _merge_env_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fusionne la configuration avec les sources de configuration alternatives
        
        Args:
            config: Configuration de base
            
        Returns:
            Configuration fusionnée
        """
        # Charger le token Mapillary depuis mapillary_config.json
        try:
            config_dir = Path("config")
            mapillary_config_path = config_dir / "mapillary_config.json"
            
            if mapillary_config_path.exists():
                with open(mapillary_config_path, 'r', encoding='utf-8') as f:
                    mapillary_config = json.load(f)
                    
                # Récupérer le token depuis la configuration Mapillary
                if 'api' in mapillary_config and 'mapillary_token' in mapillary_config['api']:
                    config['api']['mapillary_token'] = mapillary_config['api']['mapillary_token']
                    self.logger.info("Token Mapillary chargé depuis mapillary_config.json")
        except Exception as e:
            self.logger.warning(f"Impossible de charger le token Mapillary : {str(e)}")
        
        # Priorité pour le mode débogage
        if debug := os.getenv("DEBUG"):
            config["debug_mode"] = debug.lower() == "true"
        
        # Configuration du répertoire de base
        if base_dir := os.getenv("BASE_DIR"):
            config["storage"]["base_dir"] = base_dir
            config["storage"]["dataset_dir"] = str(Path(base_dir) / "datasets")
            config["storage"]["cache_dir"] = str(Path(base_dir) / "cache")
            config["storage"]["db_path"] = str(Path(base_dir) / "yolo_datasets.db")
        
        return config
    
    def save_config(self, config_path: Path) -> None:
        """
        Sauvegarde la configuration actuelle dans un fichier
        
        Args:
            config_path: Chemin de sauvegarde du fichier de configuration
        """
        if not self.config:
            raise ConfigurationError("Aucune configuration chargée")
        
        try:
            # Créer le répertoire parent si nécessaire
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convertir la configuration en dictionnaire
            config_dict = self.config.model_dump()
            
            # Sauvegarder au format JSON
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration sauvegardée : {config_path}")
        
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde de la configuration : {str(e)}")
            raise ConfigurationError(f"Impossible de sauvegarder la configuration : {str(e)}")
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Met à jour la configuration actuelle
        
        Args:
            updates: Dictionnaire des mises à jour
        """
        if not self.config:
            raise ConfigurationError("Aucune configuration chargée")
        
        try:
            # Convertir la config actuelle en dict
            config_dict = self.config.model_dump()
            
            # Mise à jour récursive
            def update_recursive(base: dict, updates: dict):
                for key, value in updates.items():
                    if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                        update_recursive(base[key], value)
                    else:
                        base[key] = value
            
            update_recursive(config_dict, updates)
            
            # Valider et appliquer la nouvelle configuration
            self.config = Configuration(**config_dict)
            
            self.logger.info("Configuration mise à jour avec succès")
        
        except Exception as e:
            self.logger.error(f"Échec de la mise à jour de la configuration : {str(e)}")
            raise ConfigurationError(f"Impossible de mettre à jour la configuration : {str(e)}")
    
    def get_config(self) -> Configuration:
        """
        Retourne la configuration actuelle
        
        Returns:
            Configuration actuellement chargée
        
        Raises:
            ConfigurationError: Si aucune configuration n'est chargée
        """
        if not self.config:
            raise ConfigurationError("Aucune configuration chargée")
        
        return self.config