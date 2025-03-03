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
        return {
            "api": {
                "mapillary_token": os.getenv("MAPILLARY_TOKEN"),
                "mapillary_url": "https://graph.mapillary.com",
                "request_timeout": 30,
                "max_retries": 3,
                "batch_size": 50
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
            "debug_mode": bool(os.getenv("DEBUG", False))
        }
    
    def _merge_env_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fusionne la configuration avec les variables d'environnement
        
        Args:
            config: Configuration de base
            
        Returns:
            Configuration fusionnée
        """
        # Mapillary Token
        if token := os.getenv("MAPILLARY_TOKEN"):
            config["api"]["mapillary_token"] = token
        
        # Mode débogage
        if debug := os.getenv("DEBUG"):
            config["debug_mode"] = debug.lower() == "true"
        
        # Répertoire de base
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