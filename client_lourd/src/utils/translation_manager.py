# src/utils/translation_manager.py

from PyQt6.QtCore import QTranslator, QLocale, QCoreApplication, QEvent
from PyQt6.QtWidgets import QApplication
from pathlib import Path
import json
import os

from src.utils.logger import Logger

class TranslationManager:
    """
    Gestionnaire de traductions pour l'application.
    Permet de charger et d'appliquer différentes langues.
    """
    
    # Langues disponibles par défaut
    FRENCH = "fr"
    ENGLISH = "en"
    SYSTEM = "system"
    
    def __init__(self, config_manager=None, logger=None):
        """
        Initialise le gestionnaire de traductions.
        
        Args:
            config_manager: Gestionnaire de configuration
            logger: Logger pour les messages de débogage
        """
        self.logger = logger or Logger()
        self.config_manager = config_manager
        self.current_language = self.FRENCH
        self.translations = {}
        self.translators = {}
        self.app_translator = QTranslator()
        
        # Charger les traductions disponibles
        self._load_translations()
        
        # Appliquer la langue par défaut (à partir de la configuration)
        if self.config_manager:
            config = self.config_manager.get_config()
            self.current_language = config.ui.language
            
        # Appliquer la langue par défaut
        self.apply_language(self.current_language)
        
    def _load_translations(self):
        """Charge les traductions disponibles."""
        try:
            # Chemins possibles pour les traductions
            translation_paths = [
                Path("src/translations"),
                Path("client_lourd/src/translations"),
                Path("translations")
            ]
            
            # Trouver le premier chemin existant
            base_path = None
            for path in translation_paths:
                if path.exists():
                    base_path = path
                    break
            
            if not base_path:
                # Créer le répertoire s'il n'existe pas
                base_path = Path("src/translations")
                base_path.mkdir(parents=True, exist_ok=True)
                self.logger.warning(f"Répertoire de traductions créé: {base_path}")
            
            # Chercher les fichiers de traduction
            translation_files = list(base_path.glob("*.json"))
            qm_files = list(base_path.glob("*.qm"))
            
            if not translation_files and not qm_files:
                # Créer des traductions par défaut si aucune n'existe
                self._create_default_translations(base_path)
                translation_files = list(base_path.glob("*.json"))
            
            # Charger les traductions JSON
            for trans_file in translation_files:
                lang_code = trans_file.stem
                with open(trans_file, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
            
            # Charger les traductions QM
            for qm_file in qm_files:
                lang_code = qm_file.stem.split('_')[-1]  # e.g., "yolo_dataset_manager_fr.qm" -> "fr"
                translator = QTranslator()
                if translator.load(str(qm_file)):
                    self.translators[lang_code] = translator
                    self.logger.info(f"Fichier de traduction Qt chargé: {qm_file}")
                else:
                    self.logger.warning(f"Impossible de charger le fichier de traduction Qt: {qm_file}")
                    
            self.logger.info(f"Traductions chargées: {list(self.translations.keys())}")
            self.logger.info(f"Traducteurs Qt chargés: {list(self.translators.keys())}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des traductions: {e}")
            # Créer des dictionnaires vides
            self.translations = {}
            self.translators = {}
    
    def _create_default_translations(self, base_path: Path):
        """
        Crée des fichiers de traduction par défaut.
        
        Args:
            base_path: Chemin du répertoire des traductions
        """
        try:
            # Traduction française (la langue par défaut, donc vide)
            fr_translations = {}
            
            # Traduction anglaise
            en_translations = {
                "MainWindow": {
                    "title": "YOLO Dataset Manager",
                    "file_menu": "&File",
                    "new_dataset": "&New Dataset...",
                    "open_dataset": "&Open Dataset...",
                    "import_menu": "&Import",
                    "import_mapillary": "From &Mapillary...",
                    "import_local": "From &local files...",
                    "export_menu": "&Export",
                    "export_yolo": "&YOLO format",
                    "export_coco": "&COCO format",
                    "export_voc": "&VOC format",
                    "preferences": "&Preferences...",
                    "quit": "&Quit",
                    "edit_menu": "&Edit",
                    "validate_dataset": "&Validate Dataset",
                    "view_menu": "&View",
                    "show_toolbar": "Show &toolbar",
                    "show_statusbar": "Show &status bar",
                    "tools_menu": "&Tools",
                    "configuration": "&Configuration...",
                    "help_menu": "&Help",
                    "about": "&About"
                },
                "DatasetView": {
                    "add_images": "Add images",
                    "export": "Export",
                    "validate": "Validate",
                    "images": "Images",
                    "stats": "Statistics",
                    "total_images": "Total Images",
                    "total_annotations": "Total Annotations",
                    "classes": "Classes",
                    "visualization": "Visualization",
                    "view_mode": "View",
                    "create_mode": "Create",
                    "edit_mode": "Edit",
                    "details": "Details",
                    "metadata": "Metadata",
                    "view_full_metadata": "View full metadata",
                    "annotations": "Annotations",
                    "edit": "Edit",
                    "delete": "Delete"
                },
                "Dialogs": {
                    "preferences_title": "Preferences",
                    "configuration_title": "Configuration",
                    "save": "Save",
                    "cancel": "Cancel",
                    "close": "Close",
                    "interface": "Interface",
                    "language": "Language",
                    "theme": "Theme",
                    "recent_datasets": "Recent datasets",
                    "window_dimensions": "Window dimensions",
                    "width": "Width",
                    "height": "Height",
                    "storage": "Storage",
                    "base_directory": "Base directory",
                    "browse": "Browse...",
                    "max_cache_size": "Maximum cache size",
                    "supported_formats": "Supported formats",
                    "clear_cache": "Clear cache",
                    "system": "System",
                    "debug_mode": "Enable debug mode",
                    "api_settings": "API settings",
                    "api_url": "API URL",
                    "timeout": "Request timeout",
                    "seconds": "seconds",
                    "test_connection": "Test API connection",
                    "database_settings": "Database settings",
                    "database_file": "Database file",
                    "enable_sql_echo": "Enable SQL echo",
                    "backup_database": "Backup database",
                    "run_migrations": "Run migrations"
                },
                "Messages": {
                    "validation_success": "Dataset is valid!",
                    "validation_failure": "Dataset validation failed:",
                    "warnings": "Warnings:",
                    "error": "Error",
                    "warning": "Warning",
                    "information": "Information",
                    "confirmation": "Confirmation",
                    "save_changes": "Save changes",
                    "unsaved_changes": "There are unsaved changes. Do you want to save them?",
                    "confirm_close": "Are you sure you want to close?",
                    "confirm_delete": "Are you sure you want to delete this item?",
                    "import_success": "Import successful",
                    "export_success": "Export successful",
                    "operation_failed": "Operation failed",
                    "no_dataset_loaded": "No dataset loaded",
                    "create_new_dataset": "Create New Dataset",
                    "no_dataset_open": "No dataset is currently open. Do you want to create a new one?",
                    "connection_success": "Connection successful",
                    "connection_failure": "Connection failed"
                }
            }
            
            # Créer les fichiers de traduction
            with open(base_path / "fr.json", 'w', encoding='utf-8') as f:
                json.dump(fr_translations, f, indent=4, ensure_ascii=False)
                
            with open(base_path / "en.json", 'w', encoding='utf-8') as f:
                json.dump(en_translations, f, indent=4, ensure_ascii=False)
                
            self.logger.info("Traductions par défaut créées")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la création des traductions par défaut: {e}")
    
    def get_available_languages(self) -> dict:
        """
        Retourne la liste des langues disponibles.
        
        Returns:
            Dictionnaire de langues {code: nom}
        """
        languages = {
            self.FRENCH: "Français",
            self.ENGLISH: "English",
            self.SYSTEM: "Système"
        }
        
        # Ajouter les langues personnalisées (celles qui ont des traductions)
        for lang_code in self.translations.keys():
            if lang_code != self.FRENCH and lang_code != self.ENGLISH:
                # Essayer de trouver le nom natif de la langue
                locale = QLocale(lang_code)
                name = locale.nativeLanguageName()
                
                if name and name[0].isupper():  # S'assurer qu'il s'agit d'un nom valide
                    languages[lang_code] = name
                else:
                    # Utiliser le code comme nom par défaut
                    languages[lang_code] = lang_code.upper()
                
        return languages
    
    def get_current_language(self) -> str:
        """
        Retourne la langue actuelle.
        
        Returns:
            Code de la langue actuelle
        """
        return self.current_language
    
    def translate(self, key: str, default: str = None) -> str:
        """
        Traduit une clé dans la langue actuelle.
        
        Args:
            key: Clé de traduction (ex: "MainWindow.title")
            default: Valeur par défaut si la clé n'est pas trouvée
            
        Returns:
            Texte traduit ou valeur par défaut
        """
        if not key:
            return default or key
            
        # Si la langue actuelle est la langue par défaut (français), retourner la clé
        if self.current_language == self.FRENCH:
            return default or key
            
        # Diviser la clé en parties
        parts = key.split('.')
        
        # Récupérer la traduction pour la langue actuelle
        translation = self.translations.get(self.current_language, {})
        
        # Parcourir les parties de la clé
        for part in parts:
            if isinstance(translation, dict) and part in translation:
                translation = translation[part]
            else:
                # Clé non trouvée
                return default or key
                
        # Vérifier que la traduction est une chaîne
        if isinstance(translation, str):
            return translation
            
        # Sinon, retourner la valeur par défaut
        return default or key
    
    def apply_language(self, language_code: str) -> bool:
        """
        Applique une langue à l'application.
        
        Args:
            language_code: Code de la langue à appliquer
            
        Returns:
            True si la langue a été appliquée avec succès
        """
        try:
            app = QApplication.instance()
            if not app:
                self.logger.error("Aucune instance QApplication trouvée")
                return False
            
            # Si la langue est "system", utiliser la langue du système
            if language_code == self.SYSTEM:
                system_locale = QLocale.system().name()
                language_code = system_locale.split('_')[0]  # ex: "fr_FR" -> "fr"
                self.logger.info(f"Utilisation de la langue système: {language_code}")
            
            # Retirer le traducteur actuel s'il existe
            app.removeTranslator(self.app_translator)
            
            # Chercher un traducteur QM pour cette langue
            if language_code in self.translators:
                translator = self.translators[language_code]
                # Installer le traducteur
                app.installTranslator(translator)
                self.app_translator = translator
                self.logger.info(f"Traducteur Qt installé pour la langue: {language_code}")
            
            # Mettre à jour la langue courante
            self.current_language = language_code
            
            # Mettre à jour la configuration si disponible
            if self.config_manager:
                try:
                    config = self.config_manager.get_config()
                    if config.ui.language != language_code:
                        self.config_manager.update_config({"ui": {"language": language_code}})
                        self.logger.info(f"Configuration mise à jour avec la langue: {language_code}")
                except Exception as e:
                    self.logger.error(f"Erreur lors de la mise à jour de la configuration: {e}")
            
            # Forcer la mise à jour de l'interface
            if app.activeWindow():
                app.activeWindow().update()
                # Envoyer un événement de changement de langue
                event = QEvent(QEvent.Type.LanguageChange)
                app.sendEvent(app.activeWindow(), event)
            
            self.logger.info(f"Langue appliquée: {language_code}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'application de la langue: {e}")
            return False
    
    def refresh_translations(self):
        """Recharge les traductions disponibles."""
        self._load_translations()
        if self.current_language:
            self.apply_language(self.current_language)
    
    def create_translation(self, language_code: str, translations: dict) -> bool:
        """
        Crée un nouveau fichier de traduction.
        
        Args:
            language_code: Code de la langue
            translations: Dictionnaire de traductions
            
        Returns:
            True si la traduction a été créée avec succès
        """
        try:
            # Chemin des traductions
            translation_paths = [
                Path("src/translations"),
                Path("client_lourd/src/translations"),
                Path("translations")
            ]
            
            # Trouver le premier chemin existant
            base_path = None
            for path in translation_paths:
                if path.exists():
                    base_path = path
                    break
            
            if not base_path:
                # Créer le répertoire s'il n'existe pas
                base_path = Path("src/translations")
                base_path.mkdir(parents=True, exist_ok=True)
            
            # Sauvegarder la traduction
            translation_path = base_path / f"{language_code}.json"
            with open(translation_path, 'w', encoding='utf-8') as f:
                json.dump(translations, f, indent=4, ensure_ascii=False)
                
            # Ajouter au dictionnaire
            self.translations[language_code] = translations
            
            self.logger.info(f"Traduction créée: {language_code}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la création de la traduction: {e}")
            return False
            
    def get_translation(self, language_code: str) -> dict:
        """
        Récupère le dictionnaire de traduction pour une langue.
        
        Args:
            language_code: Code de la langue
            
        Returns:
            Dictionnaire de traductions ou dictionnaire vide si non trouvé
        """
        return self.translations.get(language_code, {})