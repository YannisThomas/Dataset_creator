# src/views/dialogs/preferences_dialog.py

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QWidget,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QFormLayout
)
from PyQt6.QtCore import Qt, QEvent
from pathlib import Path
from typing import Dict, Optional, Any

from src.views.dialogs.base_dialog import BaseDialog
from src.utils.config import ConfigManager
from src.controllers.config_controller import ConfigController
from src.controllers.controller_manager import ControllerManager
from src.utils.theme_manager import ThemeManager
from src.utils.translation_manager import TranslationManager
from src.utils.app_utils import tr  # Importation de la fonction de traduction utilitaire

class PreferencesDialog(BaseDialog):
    """
    Dialogue des préférences de l'application.
    Utilise ConfigController pour la logique métier.
    """
    
    def __init__(
        self, 
        config_manager: Optional[ConfigManager] = None,
        config_controller: Optional[ConfigController] = None,
        controller_manager: Optional[ControllerManager] = None,
        theme_manager: Optional[ThemeManager] = None,
        translation_manager: Optional[TranslationManager] = None,
        parent=None
    ):
        """
        Initialise le dialogue des préférences.
        
        Args:
            config_manager: Gestionnaire de configuration
            config_controller: Contrôleur de configuration
            controller_manager: Gestionnaire de contrôleurs
            theme_manager: Gestionnaire de thèmes
            translation_manager: Gestionnaire de traductions
            parent: Widget parent
        """
        super().__init__(
            parent=parent,
            controller_manager=controller_manager,
            title=tr("Dialogs.preferences_title", "Préférences")
        )
        
        # Gestionnaires
        self.theme_manager = theme_manager
        self.translation_manager = translation_manager
        
        # Utiliser le gestionnaire de configuration fourni ou celui du controller_manager
        self.config_manager = config_manager
        if not self.config_manager and self.controller_manager:
            self.config_manager = self.controller_manager.config_manager
        elif not self.config_manager:
            self.config_manager = ConfigManager()
        
        # Utiliser le contrôleur fourni ou celui du gestionnaire
        self.config_controller = config_controller
        if not self.config_controller and self.controller_manager:
            self.config_controller = self.controller_manager.config_controller
        elif not self.config_controller:
            self.config_controller = ConfigController(self.config_manager)
        
        # Récupérer la configuration actuelle
        self.config = self.config_manager.get_config()
        
        # Garder une copie des valeurs originales
        self.original_values = {}
        
        self.resize(600, 400)
        
        # Créer l'interface
        self._create_ui()
        self._load_current_values()
        
    def retranslate_ui(self):
        """
        Retraduit tous les éléments statiques de l'interface.
        """
        # Mettre à jour le titre de la fenêtre
        self.setWindowTitle(tr("Dialogs.preferences_title", "Préférences"))
        
        # Mise à jour des onglets
        self.tab_widget.setTabText(0, tr("Dialogs.interface", "Interface"))
        self.tab_widget.setTabText(1, tr("Dialogs.data", "Données"))
        self.tab_widget.setTabText(2, tr("Dialogs.system", "Système"))
        
        # Interface Tab
        self.ui_group.setTitle(tr("Dialogs.interface_settings", "Paramètres d'interface"))
        self.language_label.setText(tr("Dialogs.language", "Langue:"))
        self.theme_label.setText(tr("Dialogs.theme", "Thème:"))
        self.recent_datasets_label.setText(tr("Dialogs.recent_datasets", "Datasets récents:"))
        
        # Dimensions Group
        self.dimensions_group.setTitle(tr("Dialogs.window_dimensions", "Dimensions de la fenêtre"))
        self.width_label.setText(tr("Dialogs.width", "Largeur:"))
        self.height_label.setText(tr("Dialogs.height", "Hauteur:"))
        
        # Buttons
        self.save_button.setText(tr("Dialogs.save", "Enregistrer"))
        self.cancel_button.setText(tr("Dialogs.cancel", "Annuler"))
    
    def _create_ui(self):
        """Crée l'interface utilisateur du dialogue."""
        layout = QVBoxLayout(self)
        
        # Onglets de préférences
        self.tab_widget = QTabWidget()
        
        # Onglet Interface
        ui_tab = self._create_ui_tab()
        self.tab_widget.addTab(ui_tab, tr("Dialogs.interface", "Interface"))
        
        # Onglet Données
        data_tab = self._create_data_tab()
        self.tab_widget.addTab(data_tab, tr("Dialogs.data", "Données"))
        
        # Onglet Système
        system_tab = self._create_system_tab()
        self.tab_widget.addTab(system_tab, tr("Dialogs.system", "Système"))
        
        layout.addWidget(self.tab_widget)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(tr("Dialogs.save", "Enregistrer"))
        self.save_button.clicked.connect(self._save_preferences)
        self.cancel_button = QPushButton(tr("Dialogs.cancel", "Annuler"))
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
    def _create_ui_tab(self) -> QWidget:
        """Crée l'onglet des paramètres d'interface."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe Interface
        self.ui_group = QGroupBox(tr("Dialogs.interface_settings", "Paramètres d'interface"))
        ui_layout = QFormLayout()
        
        # Langue
        self.language_label = QLabel(tr("Dialogs.language", "Langue:"))
        self.language_combo = QComboBox()
        # Vérifier si le gestionnaire de traduction existe
        if self.translation_manager:
            for code, name in self.translation_manager.get_available_languages().items():
                self.language_combo.addItem(name, code)
        
        ui_layout.addRow(self.language_label, self.language_combo)
        
        # Thème
        self.theme_label = QLabel(tr("Dialogs.theme", "Thème:"))
        self.theme_combo = QComboBox()
        # Vérifier si le gestionnaire de thème existe
        if self.theme_manager:
            for code, name in self.theme_manager.get_available_themes().items():
                self.theme_combo.addItem(name, code)
        
        ui_layout.addRow(self.theme_label, self.theme_combo)
        
        # Nombre de datasets récents
        self.recent_datasets_label = QLabel(tr("Dialogs.recent_datasets", "Datasets récents:"))
        self.recent_datasets_spin = QSpinBox()
        self.recent_datasets_spin.setRange(1, 10)
        ui_layout.addRow(self.recent_datasets_label, self.recent_datasets_spin)
        
        self.ui_group.setLayout(ui_layout)
        layout.addWidget(self.ui_group)
        
        # Groupe Dimensions
        self.dimensions_group = QGroupBox(tr("Dialogs.window_dimensions", "Dimensions de la fenêtre"))
        dimensions_layout = QFormLayout()
        
        # Largeur
        self.width_label = QLabel(tr("Dialogs.width", "Largeur:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(800, 3840)
        dimensions_layout.addRow(self.width_label, self.width_spin)
        
        # Hauteur
        self.height_label = QLabel(tr("Dialogs.height", "Hauteur:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(600, 2160)
        dimensions_layout.addRow(self.height_label, self.height_spin)
        
        self.dimensions_group.setLayout(dimensions_layout)
        layout.addWidget(self.dimensions_group)
        
        layout.addStretch()
        return tab
    
    def _create_data_tab(self) -> QWidget:
        """Crée l'onglet des paramètres de données."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe Stockage
        storage_group = QGroupBox("Stockage")
        storage_layout = QFormLayout()
        
        # Répertoire de base
        self.base_dir_edit = QLineEdit()
        base_dir_browse = QPushButton("Parcourir...")
        base_dir_browse.clicked.connect(lambda: self._browse_directory(self.base_dir_edit))
        
        base_dir_layout = QHBoxLayout()
        base_dir_layout.addWidget(self.base_dir_edit)
        base_dir_layout.addWidget(base_dir_browse)
        storage_layout.addRow("Répertoire de base:", base_dir_layout)
        
        # Taille du cache
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(100, 10000)
        self.cache_size_spin.setSuffix(" Mo")
        storage_layout.addRow("Taille maximale du cache:", self.cache_size_spin)
        
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)
        
        # Groupe formats
        formats_group = QGroupBox("Formats supportés")
        formats_layout = QVBoxLayout()
        
        self.formats_checkboxes = []
        for fmt in ["jpg", "jpeg", "png", "bmp", "tiff"]:
            cb = QCheckBox(fmt)
            self.formats_checkboxes.append(cb)
            formats_layout.addWidget(cb)
        
        formats_group.setLayout(formats_layout)
        layout.addWidget(formats_group)
        
        # Bouton pour nettoyer le cache
        clear_cache_button = QPushButton("Nettoyer le cache")
        clear_cache_button.clicked.connect(self._clear_cache)
        layout.addWidget(clear_cache_button)
        
        layout.addStretch()
        return tab
    
    def _create_system_tab(self) -> QWidget:
        """Crée l'onglet des paramètres système."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Mode débogage
        self.debug_check = QCheckBox("Activer le mode débogage")
        layout.addWidget(self.debug_check)
        
        # Groupe API
        api_group = QGroupBox("Paramètres API")
        api_layout = QFormLayout()
        
        # URL API
        self.api_url = QLineEdit()
        api_layout.addRow("URL API:", self.api_url)
        
        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setSuffix(" secondes")
        api_layout.addRow("Timeout des requêtes:", self.timeout_spin)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Test de connexion
        test_button = QPushButton("Tester la connexion API")
        test_button.clicked.connect(self._test_api_connection)
        layout.addWidget(test_button)
        
        layout.addStretch()
        return tab
    
    def _load_current_values(self):
        """Charge les valeurs actuelles dans l'interface."""
        # Langue
        if self.translation_manager:
            current_language = self.translation_manager.get_current_language()
            current_index = self.language_combo.findData(current_language)
            if current_index >= 0:
                self.language_combo.setCurrentIndex(current_index)
        
        # Thème
        if self.theme_manager:
            current_theme = self.theme_manager.get_current_theme()
            current_index = self.theme_combo.findData(current_theme)
            if current_index >= 0:
                self.theme_combo.setCurrentIndex(current_index)
        
        # Autres paramètres d'interface
        self.recent_datasets_spin.setValue(self.config.ui.max_recent_datasets)
        self.width_spin.setValue(self.config.ui.window_width)
        self.height_spin.setValue(self.config.ui.window_height)
        
        # Sauvegarder les valeurs originales
        self._save_original_values()
    
    def _set_combo_by_data(self, combo: QComboBox, data_value: str):
        """
        Définit la sélection d'une combo box selon la valeur data.
        
        Args:
            combo: Combo box à définir
            data_value: Valeur data à sélectionner
        """
        for i in range(combo.count()):
            if combo.itemData(i) == data_value:
                combo.setCurrentIndex(i)
                return
    
    def _save_original_values(self):
        """Sauvegarde les valeurs originales pour détecter les changements."""
        self.original_values = {
            "ui": {
                "language": self.language_combo.currentData(),
                "theme": self.theme_combo.currentData(),
                "recent_datasets": self.recent_datasets_spin.value(),
                "window_width": self.width_spin.value(),
                "window_height": self.height_spin.value()
            },
            "storage": {
                "base_dir": self.base_dir_edit.text(),
                "cache_size": self.cache_size_spin.value()
            },
            "dataset": {
                "formats": [cb.text() for cb in self.formats_checkboxes if cb.isChecked()]
            },
            "system": {
                "debug": self.debug_check.isChecked(),
                "api_url": self.api_url.text(),
                "timeout": self.timeout_spin.value()
            }
        }
    
    def _browse_directory(self, line_edit: QLineEdit):
        """Ouvre un dialogue pour sélectionner un répertoire."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un répertoire",
            line_edit.text() or str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            line_edit.setText(directory)
    
    def _clear_cache(self):
        """Nettoie le cache de l'application."""
        cache_dir = Path(self.base_dir_edit.text()) / "cache"
        
        if not self.confirm_action(
            "Nettoyer le cache",
            f"Voulez-vous vider le répertoire de cache?\n{cache_dir}"
        ):
            return
            
        try:
            if cache_dir.exists():
                # Supprimer tous les fichiers du cache
                for file in cache_dir.glob("*"):
                    if file.is_file():
                        file.unlink()
                
                self.logger.info(f"Cache nettoyé: {cache_dir}")
                self.show_info(
                    "Cache nettoyé",
                    "Le répertoire de cache a été vidé avec succès."
                )
            else:
                self.show_info(
                    "Cache vide",
                    "Le répertoire de cache n'existe pas."
                )
        except Exception as e:
            self.logger.error(f"Échec du nettoyage du cache: {str(e)}")
            self.show_error(
                "Erreur",
                f"Échec du nettoyage du cache:\n{str(e)}"
            )
    
    def _test_api_connection(self):
        """Teste la connexion à l'API via le contrôleur."""
        try:
            # Collecter les paramètres API actuels
            api_config = {
                "mapillary_token": self.config.api.mapillary_token,  # Utiliser le token existant
                "mapillary_url": self.api_url.text(),
                "request_timeout": self.timeout_spin.value(),
                "max_retries": self.config.api.max_retries,  # Utiliser la valeur existante
                "batch_size": self.config.api.batch_size  # Utiliser la valeur existante
            }
            
            # Exécuter le test
            test_result = self.config_controller.test_api_connection(api_config)
            
            if test_result["success"]:
                self.show_info(
                    "Connexion réussie",
                    test_result["message"]
                )
            else:
                self.show_warning(
                    "Échec de la connexion",
                    test_result["message"]
                )
                
        except Exception as e:
            self.logger.error(f"Erreur lors du test de connexion: {str(e)}")
            self.show_error(
                "Erreur de connexion",
                f"Échec du test de connexion API:\n{str(e)}"
            )
    
    def _save_preferences(self):
        """Sauvegarde les préférences."""
        try:
            # Collecter les mises à jour
            updates = {
                "ui": {
                    "language": self.language_combo.currentData(),
                    "theme": self.theme_combo.currentData(),
                    "max_recent_datasets": self.recent_datasets_spin.value(),
                    "window_width": self.width_spin.value(),
                    "window_height": self.height_spin.value()
                }
            }
            
            # Appliquer la langue
            if self.translation_manager:
                language = updates["ui"]["language"]
                self.translation_manager.apply_language(language)
            
            # Appliquer le thème
            if self.theme_manager:
                theme = updates["ui"]["theme"]
                self.theme_manager.apply_theme(theme)
            
            # Sauvegarder via le contrôleur
            config_path = Path("config.json")
            self.config_controller.save_config(updates, config_path)
            
            # Log
            self.logger.info("Préférences sauvegardées avec succès")
            
            # Accepter le dialogue
            self.accept()
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde des préférences: {str(e)}")
            self.show_error(
                tr("Messages.error", "Erreur"),
                tr("Messages.save_failed", f"Échec de la sauvegarde des préférences:\n{str(e)}")
            )
    
    def has_changes(self) -> bool:
        """
        Vérifie si des modifications ont été apportées.
        
        Returns:
            True si des modifications ont été faites
        """
        current_values = {
            "ui": {
                "language": self.language_combo.currentData(),
                "theme": self.theme_combo.currentData(),
                "recent_datasets": self.recent_datasets_spin.value(),
                "window_width": self.width_spin.value(),
                "window_height": self.height_spin.value()
            },
            "storage": {
                "base_dir": self.base_dir_edit.text(),
                "cache_size": self.cache_size_spin.value()
            },
            "dataset": {
                "formats": [cb.text() for cb in self.formats_checkboxes if cb.isChecked()]
            },
            "system": {
                "debug": self.debug_check.isChecked(),
                "api_url": self.api_url.text(),
                "timeout": self.timeout_spin.value()
            }
        }
        
        # Comparer avec les valeurs originales
        import json
        return json.dumps(current_values, sort_keys=True) != json.dumps(self.original_values, sort_keys=True)
    
    def closeEvent(self, event):
        """Gère la fermeture du dialogue."""
        if self.has_changes():
            reply = self.confirm_action(
                "Sauvegarder les modifications",
                "Des modifications ont été apportées. Voulez-vous les sauvegarder?"
            )
            
            if reply:
                self._save_preferences()
            # Toujours accepter la fermeture, même si pas de sauvegarde
            event.accept()
        else:
            event.accept()

    def changeEvent(self, event):
        """
        Gère les événements de changement.
        Utile pour intercepter les changements de langue.
        """
        if event.type() == QEvent.Type.LanguageChange:
            # Retraduite l'interface
            self.retranslate_ui()
        
        super().changeEvent(event)