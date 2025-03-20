# src/utils/app_utils.py

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QObject, QEvent, QCoreApplication
import sys

from src.utils.logger import Logger
from src.utils.config import ConfigManager
from src.utils.theme_manager import ThemeManager
from src.utils.translation_manager import TranslationManager

# Instances globales des gestionnaires
logger = None
config_manager = None
theme_manager = None
translation_manager = None

def initialize_application():
    """
    Initialise l'application et ses gestionnaires.
    Doit être appelé avant de créer l'application Qt.
    
    Returns:
        (logger, config_manager, theme_manager, translation_manager)
    """
    global logger, config_manager, theme_manager, translation_manager
    
    # Initialiser le logger
    logger = Logger()
    logger.info("Initialisation de l'application")
    
    # Initialiser le gestionnaire de configuration
    config_manager = ConfigManager(logger=logger)
    
    # Initialiser le gestionnaire de thèmes
    theme_manager = ThemeManager(config_manager=config_manager, logger=logger)
    
    # Initialiser le gestionnaire de traductions
    translation_manager = TranslationManager(config_manager=config_manager, logger=logger)
    
    return logger, config_manager, theme_manager, translation_manager

def get_logger():
    """Retourne l'instance du logger."""
    return logger

def get_config_manager():
    """Retourne l'instance du gestionnaire de configuration."""
    return config_manager

def get_theme_manager():
    """Retourne l'instance du gestionnaire de thèmes."""
    return theme_manager

def get_translation_manager():
    """Retourne l'instance du gestionnaire de traductions."""
    return translation_manager

def tr(key, default=None):
    """
    Fonction utilitaire pour traduire une chaîne.
    
    Args:
        key: Clé de traduction
        default: Valeur par défaut si la clé n'est pas trouvée
        
    Returns:
        Chaîne traduite
    """
    if translation_manager:
        return translation_manager.translate(key, default)
    return default or key

class LanguageChangeEventFilter(QObject):
    """
    Filtre d'événements pour intercepter les changements de langue.
    Permet de retraduire automatiquement l'interface utilisateur.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def eventFilter(self, obj, event):
        """Filtre les événements pour intercepter les changements de langue."""
        if event.type() == QEvent.Type.LanguageChange:
            # Appeler la méthode de retranslation si elle existe
            if hasattr(obj, 'retranslate_ui'):
                obj.retranslate_ui()
            
        # Laisser l'événement être traité normalement
        return super().eventFilter(obj, event)

def setup_translation_event_filter(window):
    """
    Configure un filtre d'événements pour les changements de langue.
    
    Args:
        window: Fenêtre à configurer
    """
    event_filter = LanguageChangeEventFilter(window)
    window.installEventFilter(event_filter)
    
    # Propager aux widgets enfants
    for child in window.findChildren(QWidget):
        child.installEventFilter(event_filter)

def apply_initial_settings():
    """
    Applique les paramètres initiaux à l'application.
    Doit être appelé après la création de QApplication.
    """
    app = QApplication.instance()
    if not app:
        raise RuntimeError("QApplication doit être créée avant d'appeler apply_initial_settings")
    
    # Appliquer le thème
    if theme_manager:
        theme_manager.apply_theme(theme_manager.get_current_theme())
    
    # Appliquer la langue
    if translation_manager:
        translation_manager.apply_language(translation_manager.get_current_language())