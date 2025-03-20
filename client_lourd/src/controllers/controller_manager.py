# src/controllers/controller_manager.py

from typing import Optional, Any

from src.utils.logger import Logger
from src.utils.config import ConfigManager

# Import services
from src.services.api_service import APIService
from src.services.dataset_service import DatasetService
from src.services.import_service import ImportService
from src.services.export_service import ExportService

# Import controllers
from src.controllers.config_controller import ConfigController
from src.controllers.dataset_controller import DatasetController
from src.controllers.import_controller import ImportController
from src.controllers.export_controller import ExportController
from src.controllers.api_controller import APIController

# Optional imports for theme and translation managers
try:
    from src.utils.theme_manager import ThemeManager
    from src.utils.translation_manager import TranslationManager
except ImportError:
    ThemeManager = None
    TranslationManager = None

class ControllerManager:
    """
    Gestionnaire centralisé des contrôleurs de l'application.
    
    Fournit un accès unique à tous les contrôleurs et assure leur
    configuration cohérente.
    """
    
    def __init__(
        self, 
        logger: Optional[Logger] = None,
        config_manager: Optional[ConfigManager] = None,
        theme_manager: Optional[Any] = None, 
        translation_manager: Optional[Any] = None
    ):
        """
        Initialise le gestionnaire de contrôleurs.
        
        Args:
            logger: Logger pour les messages de débogage
            config_manager: Gestionnaire de configuration
            theme_manager: Gestionnaire de thèmes
            translation_manager: Gestionnaire de traductions
        """
        # Initialiser les dépendances
        self.logger = logger or Logger()
        self.config_manager = config_manager or ConfigManager()
        
        # Initialiser les gestionnaires de thème et de traduction
        self.theme_manager = theme_manager
        self.translation_manager = translation_manager
        
        # Initialiser les services
        self.api_service = APIService(config_manager=self.config_manager)
        self.dataset_service = DatasetService()
        self.import_service = ImportService()
        self.export_service = ExportService()
        
        # Initialiser les contrôleurs
        self._init_controllers()
        
    def _init_controllers(self):
        """Initialise tous les contrôleurs avec les dépendances nécessaires."""
        # Contrôleur de configuration
        self.config_controller = ConfigController(
            config_manager=self.config_manager,
            logger=self.logger
        )
        
        # Contrôleur de dataset
        self.dataset_controller = DatasetController(
            dataset_service=self.dataset_service,
            logger=self.logger
        )
        
        # Contrôleur d'API
        self.api_controller = APIController(
            api_service=self.api_service,
            dataset_service=self.dataset_service,
            logger=self.logger
        )
        
        # Contrôleur d'import
        self.import_controller = ImportController(
            import_service=self.import_service,
            api_service=self.api_service,
            dataset_service=self.dataset_service,
            logger=self.logger
        )
        
        # Contrôleur d'export
        self.export_controller = ExportController(export_service=self.export_service,
            dataset_service=self.dataset_service,
            logger=self.logger
        )
    def reset_controllers(self):
        """
        Réinitialise tous les contrôleurs.
        Utile après un changement de configuration.
        """
        # Recharger la configuration
        self.config_manager = ConfigManager()
        
        # Réinitialiser les services
        self.api_service = APIService(config_manager=self.config_manager)
        
        # Réinitialiser les contrôleurs
        self._init_controllers()
        
        # Appliquer les nouveaux paramètres de thème et de langue si nécessaire
        self._apply_theme_and_language()
        
        return self
    
    def _apply_theme_and_language(self):
        """
        Applique le thème et la langue en gérant les erreurs potentielles.
        """
        # Application du thème
        if self.theme_manager:
            try:
                # Vérifier si la méthode apply_theme existe
                if hasattr(self.theme_manager, 'apply_theme'):
                    current_theme = self.theme_manager.get_current_theme()
                    self.theme_manager.apply_theme(current_theme)
                elif self.logger:
                    self.logger.warning("Le gestionnaire de thème ne possède pas de méthode apply_theme")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Échec de l'application du thème: {e}")
        
        # Application de la langue
        if self.translation_manager:
            try:
                # Vérifier si la méthode apply_language existe
                if hasattr(self.translation_manager, 'apply_language'):
                    current_language = self.translation_manager.get_current_language()
                    self.translation_manager.apply_language(current_language)
                elif self.logger:
                    self.logger.warning("Le gestionnaire de traduction ne possède pas de méthode apply_language")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Échec de l'application de la langue: {e}")