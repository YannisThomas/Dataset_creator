# src/controllers/controller_manager.py

from typing import Dict, Optional, Any

from src.utils.config import ConfigManager
from src.utils.logger import Logger
from src.services.database_service import DatabaseService
from src.services.api_service import APIService
from src.services.dataset_service import DatasetService
from src.services.export_service import ExportService
from src.services.import_service import ImportService

from src.controllers.dataset_controller import DatasetController
from src.controllers.import_controller import ImportController
from src.controllers.export_controller import ExportController
from src.controllers.api_controller import APIController
from src.controllers.config_controller import ConfigController

class ControllerManager:
    """
    Gestionnaire centralisé pour les contrôleurs de l'application.
    
    Cette classe est responsable de:
    - Créer et initialiser les contrôleurs
    - Injecter les services dans les contrôleurs
    - Gérer le cycle de vie des contrôleurs
    - Centraliser les dépendances
    """
    
    def __init__(
        self, 
        config_manager: Optional[ConfigManager] = None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le gestionnaire de contrôleurs.
        
        Args:
            config_manager: Gestionnaire de configuration
            logger: Gestionnaire de logs
        """
        # Services de base
        self.logger = logger or Logger()
        self.config_manager = config_manager or ConfigManager()
        
        # Initialisation des services
        self._init_services()
        
        # Les contrôleurs seront créés à la demande
        self._dataset_controller = None
        self._import_controller = None
        self._export_controller = None
        self._api_controller = None
        self._config_controller = None
        
        self.logger.info("ControllerManager initialized")
    
    def _init_services(self):
        """Initialise les services partagés."""
        self.database_service = DatabaseService()
        self.api_service = APIService(self.config_manager)
        self.dataset_service = DatasetService(self.database_service)
        self.export_service = ExportService()
        self.import_service = ImportService(self.api_service)
    
    @property
    def dataset_controller(self) -> DatasetController:
        """
        Récupère ou crée le contrôleur de dataset.
        
        Returns:
            Instance du DatasetController
        """
        if not self._dataset_controller:
            self._dataset_controller = DatasetController(
                dataset_service=self.dataset_service,
                import_service=self.import_service,
                export_service=self.export_service,
                logger=self.logger
            )
            self.logger.debug("DatasetController created")
        return self._dataset_controller
    
    @property
    def import_controller(self) -> ImportController:
        """
        Récupère ou crée le contrôleur d'import.
        
        Returns:
            Instance du ImportController
        """
        if not self._import_controller:
            self._import_controller = ImportController(
                import_service=self.import_service,
                api_service=self.api_service,
                dataset_service=self.dataset_service,
                logger=self.logger
            )
            self.logger.debug("ImportController created")
        return self._import_controller
    
    @property
    def export_controller(self) -> ExportController:
        """
        Récupère ou crée le contrôleur d'export.
        
        Returns:
            Instance du ExportController
        """
        if not self._export_controller:
            self._export_controller = ExportController(
                export_service=self.export_service,
                dataset_service=self.dataset_service,
                logger=self.logger
            )
            self.logger.debug("ExportController created")
        return self._export_controller
    
    @property
    def api_controller(self) -> APIController:
        """
        Récupère ou crée le contrôleur d'API.
        
        Returns:
            Instance du APIController
        """
        if not self._api_controller:
            self._api_controller = APIController(
                api_service=self.api_service,
                dataset_service=self.dataset_service,
                logger=self.logger
            )
            self.logger.debug("APIController created")
        return self._api_controller
    
    def get_controller(self, controller_type: str) -> Any:
        """
        Récupère un contrôleur par son type.
        
        Args:
            controller_type: Type de contrôleur ("dataset", "import", "export", "api", "config")
            
        Returns:
            Instance du contrôleur demandé
            
        Raises:
            ValueError: Si le type de contrôleur est inconnu
        """
        controller_map = {
            "dataset": self.dataset_controller,
            "import": self.import_controller,
            "export": self.export_controller,
            "api": self.api_controller,
            "config": self.config_controller
        }
        
        if controller_type not in controller_map:
            self.logger.error(f"Unknown controller type: {controller_type}")
            raise ValueError(f"Unknown controller type: {controller_type}")
            
        return controller_map[controller_type]
    
    @property
    def config_controller(self) -> ConfigController:
        """
        Récupère ou crée le contrôleur de configuration.
        
        Returns:
            Instance du ConfigController
        """
        if not self._config_controller:
            self._config_controller = ConfigController(
                config_manager=self.config_manager,
                logger=self.logger
            )
            self.logger.debug("ConfigController created")
        return self._config_controller
        
    def reset_controllers(self):
        """
        Réinitialise tous les contrôleurs.
        Utile pour libérer des ressources ou après un changement de configuration.
        """
        self._dataset_controller = None
        self._import_controller = None
        self._export_controller = None
        self._api_controller = None
        self._config_controller = None
        self.logger.info("All controllers reset")