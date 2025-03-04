# src/utils/advanced_logger.py

import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Union, Dict, Any
import threading
import json
import traceback

class LoggerSingleton(type):
    """Métaclasse pour implémenter un singleton de logger."""
    _instances = {}
    _lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
            return cls._instances[cls]


class AdvancedLogger(metaclass=LoggerSingleton):
    """
    Système de journalisation avancé pour YOLO Dataset Manager.
    
    Caractéristiques:
    - Singleton pour assurer une instance unique
    - Rotation des logs par taille et date
    - Support pour les logs par module
    - Coloration des logs en console
    - Journalisation des exceptions avec traceback
    - Configuration via un fichier ou dictionnaire
    """
    
    # Niveaux de log avec leurs couleurs ANSI
    COLORS = {
        'DEBUG': '\033[94m',    # Bleu
        'INFO': '\033[92m',     # Vert
        'WARNING': '\033[93m',  # Jaune
        'ERROR': '\033[91m',    # Rouge
        'CRITICAL': '\033[1;91m',  # Rouge gras
        'RESET': '\033[0m'      # Reset
    }
    
    DEFAULT_CONFIG = {
        'log_level': 'INFO',
        'console_output': True,
        'console_color': True,
        'file_output': True,
        'max_file_size_mb': 10,
        'max_backup_count': 5,
        'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S'
    }
    
    def __init__(
        self, 
        log_dir: Optional[Union[str, Path]] = None, 
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise le logger avancé.
        
        Args:
            log_dir: Répertoire de sauvegarde des logs
            config: Configuration du logger (dict ou chemin vers JSON)
        """
        # Charger la configuration
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self._load_config(config)
        
        # Mapping des niveaux de logs
        self.level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        # Créer le répertoire de logs si nécessaire
        if log_dir is None:
            log_dir = Path("data/logs")
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Générer un nom de fichier unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"yolo_dataset_manager_{timestamp}.log"
        
        # Dictionnaire pour stocker les loggers par module
        self.loggers = {}
        
        # Créer le logger principal
        self.main_logger = self._setup_logger("YOLODatasetManager")
        
        # Log du démarrage
        self.main_logger.info(f"Logger initialisé - Fichier: {self.log_file}")
    
    def _load_config(self, config):
        """Charge la configuration depuis un dictionnaire ou un fichier JSON."""
        if isinstance(config, dict):
            self.config.update(config)
        elif isinstance(config, (str, Path)):
            try:
                with open(config, 'r') as f:
                    self.config.update(json.load(f))
            except Exception as e:
                print(f"Erreur de chargement du fichier de configuration: {e}")
                
    def _get_console_formatter(self):
        """Crée un formateur pour la sortie console avec couleurs si activées."""
        if self.config['console_color'] and sys.stdout.isatty():
            class ColorFormatter(logging.Formatter):
                def format(self, record):
                    levelname = record.levelname
                    message = super().format(record)
                    return f"{AdvancedLogger.COLORS.get(levelname, '')}{message}{AdvancedLogger.COLORS['RESET']}"
            
            return ColorFormatter(
                fmt=self.config['log_format'],
                datefmt=self.config['date_format']
            )
        else:
            return logging.Formatter(
                fmt=self.config['log_format'],
                datefmt=self.config['date_format']
            )
    
    def _setup_logger(self, name: str) -> logging.Logger:
        """Configure un logger avec les handlers appropriés."""
        logger = logging.getLogger(name)
        
        # Éviter d'ajouter des handlers multiples
        if logger.hasHandlers():
            logger.handlers.clear()
            
        # Définir le niveau de log
        level = self.level_map.get(self.config['log_level'], logging.INFO)
        logger.setLevel(level)
        
        # Formatter standard
        formatter = logging.Formatter(
            fmt=self.config['log_format'],
            datefmt=self.config['date_format']
        )
        
        # Ajouter la sortie fichier si demandée
        if self.config['file_output']:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Ajouter la sortie console si demandée
        if self.config['console_output']:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(self._get_console_formatter())
            logger.addHandler(console_handler)
        
        return logger
    
    def get_logger(self, module_name: str = None) -> logging.Logger:
        """
        Récupère un logger pour un module spécifique.
        
        Args:
            module_name: Nom du module (optionnel)
            
        Returns:
            Logger configuré
        """
        if not module_name:
            return self.main_logger
            
        if module_name not in self.loggers:
            self.loggers[module_name] = self._setup_logger(f"YOLODatasetManager.{module_name}")
            
        return self.loggers[module_name]
    
    def debug(self, message: str, module: str = None):
        """Log un message de débogage."""
        self.get_logger(module).debug(message)
    
    def info(self, message: str, module: str = None):
        """Log un message d'information."""
        self.get_logger(module).info(message)
    
    def warning(self, message: str, module: str = None):
        """Log un message d'avertissement."""
        self.get_logger(module).warning(message)
    
    def error(self, message: str, module: str = None, exc_info: bool = False):
        """
        Log un message d'erreur.
        
        Args:
            message: Message d'erreur
            module: Nom du module (optionnel)
            exc_info: Inclure les informations d'exception (optionnel)
        """
        self.get_logger(module).error(message, exc_info=exc_info)
    
    def critical(self, message: str, module: str = None, exc_info: bool = True):
        """
        Log un message critique.
        
        Args:
            message: Message critique
            module: Nom du module (optionnel)
            exc_info: Inclure les informations d'exception (optionnel)
        """
        self.get_logger(module).critical(message, exc_info=exc_info)
        
    def exception(self, message: str, module: str = None):
        """
        Log une exception avec traceback.
        
        Args:
            message: Message d'erreur
            module: Nom du module (optionnel)
        """
        self.get_logger(module).exception(message)
        
    def log_exception(self, e: Exception, module: str = None, level: str = 'ERROR'):
        """
        Log une exception avec traceback formaté.
        
        Args:
            e: Exception à logger
            module: Nom du module (optionnel)
            level: Niveau de log (ERROR par défaut)
        """
        tb = traceback.format_exc()
        message = f"{type(e).__name__}: {str(e)}\n{tb}"
        
        if level.upper() == 'CRITICAL':
            self.critical(message, module)
        else:
            self.error(message, module)
            
    def set_level(self, level: str):
        """
        Change le niveau de log pour tous les loggers.
        
        Args:
            level: Niveau de log ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        """
        if level.upper() not in self.level_map:
            self.warning(f"Niveau de log invalide: {level}")
            return
            
        log_level = self.level_map[level.upper()]
        self.config['log_level'] = level.upper()
        
        # Mettre à jour tous les loggers existants
        self.main_logger.setLevel(log_level)
        for logger in self.loggers.values():
            logger.setLevel(log_level)
            
        self.info(f"Niveau de log changé à {level.upper()}")

    def archive_log(self):
        """Archive le fichier de log actuel et en commence un nouveau."""
        if not self.log_file.exists():
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = self.log_dir / f"archive_{timestamp}_{self.log_file.name}"
        
        # Fermer les handlers de fichier existants
        for handler in self.main_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.main_logger.removeHandler(handler)
                
        for logger in self.loggers.values():
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    logger.removeHandler(handler)
        
        # Renommer le fichier existant
        os.rename(self.log_file, archive_name)
        
        # Créer un nouveau fichier de log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"yolo_dataset_manager_{timestamp}.log"
        
        # Reconfigurer tous les loggers
        self.main_logger = self._setup_logger("YOLODatasetManager")
        for name, logger in self.loggers.items():
            self.loggers[name] = self._setup_logger(f"YOLODatasetManager.{name}")
            
        self.info(f"Log archivé: {archive_name}")
        
    def get_log_content(self, lines: int = 100) -> str:
        """
        Récupère les dernières lignes du fichier de log.
        
        Args:
            lines: Nombre de lignes à récupérer
            
        Returns:
            Contenu du log
        """
        if not self.log_file.exists():
            return "Fichier de log non trouvé"
            
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception as e:
            return f"Erreur de lecture du log: {str(e)}"