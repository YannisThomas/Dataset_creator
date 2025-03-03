import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Union

class Logger:
    """
    Système de journalisation personnalisé pour le projet YOLO Dataset Manager.
    
    Gère la journalisation avec différents niveaux et supports de sortie.
    """
    
    def __init__(
        self, 
        log_dir: Optional[Union[str, Path]] = None, 
        log_level: int = logging.INFO,
        console_output: bool = True
    ):
        """
        Initialise le logger.
        
        Args:
            log_dir: Répertoire de sauvegarde des logs
            log_level: Niveau de journalisation
            console_output: Activer la sortie console
        """
        # Créer le répertoire de logs si nécessaire
        if log_dir is None:
            log_dir = Path("data/logs")
        
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Générer un nom de fichier unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"yolo_dataset_manager_{timestamp}.log"
        
        # Configuration du logger
        self.logger = logging.getLogger("YOLODatasetManager")
        self.logger.setLevel(log_level)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler de fichier
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        
        # Handler de console
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str):
        """
        Log de message de débogage.
        
        Args:
            message: Message à journaliser
        """
        self.logger.debug(message)
    
    def info(self, message: str):
        """
        Log de message d'information.
        
        Args:
            message: Message à journaliser
        """
        self.logger.info(message)
    
    def warning(self, message: str):
        """
        Log de message d'avertissement.
        
        Args:
            message: Message à journaliser
        """
        self.logger.warning(message)
    
    def error(self, message: str):
        """
        Log de message d'erreur.
        
        Args:
            message: Message à journaliser
        """
        self.logger.error(message)
    
    def critical(self, message: str):
        """
        Log de message critique.
        
        Args:
            message: Message à journaliser
        """
        self.logger.critical(message)