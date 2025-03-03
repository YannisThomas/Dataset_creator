# src/controllers/config_controller.py

from typing import Dict, Any, Optional, Union
from pathlib import Path

from src.utils.config import ConfigManager
from src.utils.logger import Logger
from src.core.exceptions import ConfigurationError

class ConfigController:
    """
    Contrôleur pour la gestion de la configuration de l'application.
    
    Responsabilités:
    - Modification des paramètres de configuration
    - Validation des entrées de configuration
    - Sauvegarde/Chargement des fichiers de configuration
    """
    
    def __init__(
        self, 
        config_manager: Optional[ConfigManager] = None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le contrôleur de configuration.
        
        Args:
            config_manager: Gestionnaire de configuration
            logger: Gestionnaire de logs
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = logger or Logger()
    
    def load_config(self, config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Charge une configuration depuis un fichier.
        
        Args:
            config_path: Chemin vers le fichier de configuration (optionnel)
            
        Returns:
            Dictionnaire de configuration
            
        Raises:
            ConfigurationError: Si le chargement échoue
        """
        try:
            config = self.config_manager.load_config(config_path)
            return config.model_dump() if hasattr(config, 'model_dump') else vars(config)
        except Exception as e:
            self.logger.error(f"Échec du chargement de la configuration: {str(e)}")
            raise ConfigurationError(f"Impossible de charger la configuration: {str(e)}")
    
    def save_config(self, config_updates: Dict[str, Any], config_path: Optional[Union[str, Path]] = None) -> bool:
        """
        Met à jour et sauvegarde la configuration.
        
        Args:
            config_updates: Dictionnaire des mises à jour de configuration
            config_path: Chemin où sauvegarder la configuration (optionnel)
            
        Returns:
            True si la sauvegarde a réussi
            
        Raises:
            ConfigurationError: Si la sauvegarde échoue
        """
        try:
            # Appliquer les mises à jour
            self.config_manager.update_config(config_updates)
            
            # Sauvegarder dans un fichier si spécifié
            if config_path:
                path = Path(config_path)
                self.config_manager.save_config(path)
            else:
                # Utiliser le chemin par défaut
                path = Path("config.json")
                self.config_manager.save_config(path)
            
            self.logger.info(f"Configuration sauvegardée: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde de la configuration: {str(e)}")
            raise ConfigurationError(f"Impossible de sauvegarder la configuration: {str(e)}")
    
    def validate_api_config(self, api_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide les paramètres de l'API.
        
        Args:
            api_config: Configuration de l'API à valider
            
        Returns:
            Résultat de la validation
        """
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Valider le token
        if not api_config.get('mapillary_token'):
            validation["warnings"].append("Aucun token API défini")
        
        # Valider l'URL de l'API
        api_url = api_config.get('mapillary_url', '')
        if not api_url:
            validation["errors"].append("URL de l'API requise")
            validation["valid"] = False
        elif not api_url.startswith(('http://', 'https://')):
            validation["errors"].append("URL de l'API invalide: doit commencer par http:// ou https://")
            validation["valid"] = False
        
        # Valider le timeout
        timeout = api_config.get('request_timeout')
        if timeout is None:
            validation["warnings"].append("Timeout non défini, la valeur par défaut sera utilisée")
        elif not isinstance(timeout, int) or timeout < 1:
            validation["errors"].append("Timeout invalide: doit être un entier positif")
            validation["valid"] = False
        elif timeout < 5:
            validation["warnings"].append("Timeout très court, peut causer des problèmes de connexion")
        
        # Valider le nombre de tentatives
        retries = api_config.get('max_retries')
        if retries is None:
            validation["warnings"].append("Nombre de tentatives non défini, la valeur par défaut sera utilisée")
        elif not isinstance(retries, int) or retries < 0:
            validation["errors"].append("Nombre de tentatives invalide: doit être un entier non négatif")
            validation["valid"] = False
        
        # Valider la taille des lots
        batch_size = api_config.get('batch_size')
        if batch_size is None:
            validation["warnings"].append("Taille de lot non définie, la valeur par défaut sera utilisée")
        elif not isinstance(batch_size, int) or batch_size < 1 or batch_size > 100:
            validation["errors"].append("Taille de lot invalide: doit être entre 1 et 100")
            validation["valid"] = False
        
        return validation
    
    def validate_storage_config(self, storage_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide les paramètres de stockage.
        
        Args:
            storage_config: Configuration de stockage à valider
            
        Returns:
            Résultat de la validation
        """
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Valider le répertoire de base
        base_dir = storage_config.get('base_dir')
        if not base_dir:
            validation["errors"].append("Répertoire de base requis")
            validation["valid"] = False
        else:
            try:
                path = Path(base_dir)
                if not path.exists() and not path.parent.exists():
                    validation["warnings"].append(f"Le répertoire parent de {path} n'existe pas")
            except Exception:
                validation["errors"].append(f"Chemin invalide: {base_dir}")
                validation["valid"] = False
        
        # Valider le chemin de la base de données
        db_path = storage_config.get('db_path')
        if not db_path:
            validation["warnings"].append("Chemin de base de données non défini, la valeur par défaut sera utilisée")
        else:
            try:
                path = Path(db_path)
                if not path.parent.exists():
                    validation["warnings"].append(f"Le répertoire parent de {path} n'existe pas")
            except Exception:
                validation["errors"].append(f"Chemin de base de données invalide: {db_path}")
                validation["valid"] = False
        
        # Valider la taille du cache
        cache_size = storage_config.get('max_cache_size_mb')
        if cache_size is None:
            validation["warnings"].append("Taille du cache non définie, la valeur par défaut sera utilisée")
        elif not isinstance(cache_size, int) or cache_size < 0:
            validation["errors"].append("Taille du cache invalide: doit être un entier non négatif")
            validation["valid"] = False
        elif cache_size > 10000:  # 10 GB
            validation["warnings"].append("Taille du cache très grande, peut causer des problèmes de stockage")
        
        return validation
    
    def test_api_connection(self, api_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Teste la connexion à l'API avec les paramètres fournis.
        
        Args:
            api_config: Configuration de l'API à tester
            
        Returns:
            Résultat du test
        """
        try:
            # Appliquer temporairement la configuration
            original_config = self.config_manager.get_config()
            self.config_manager.update_config({"api": api_config})
            
            # Créer une instance temporaire du service API
            from src.services.api_service import APIService
            api_service = APIService(self.config_manager)
            
            # Tester la connexion
            result = api_service.verify_token()
            
            if result:
                self.logger.info("Test de connexion à l'API réussi")
                return {
                    "success": True,
                    "message": "Connexion à l'API établie avec succès"
                }
            else:
                self.logger.warning("Échec du test de connexion à l'API: token invalide")
                return {
                    "success": False,
                    "message": "Échec de la vérification du token API"
                }
        except Exception as e:
            self.logger.error(f"Échec du test de connexion à l'API: {str(e)}")
            return {
                "success": False,
                "message": f"Erreur de connexion à l'API: {str(e)}"
            }
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Retourne la liste des langues supportées.
        
        Returns:
            Dictionnaire des langues supportées (code: nom)
        """
        return {
            "fr": "Français",
            "en": "English"
        }
    
    def get_supported_themes(self) -> Dict[str, str]:
        """
        Retourne la liste des thèmes supportés.
        
        Returns:
            Dictionnaire des thèmes supportés (code: nom)
        """
        return {
            "light": "Clair",
            "dark": "Sombre"
        }