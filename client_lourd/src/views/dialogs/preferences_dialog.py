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
from PyQt6.QtCore import Qt
from pathlib import Path
from typing import Dict, Optional, Any

from src.utils.i18n import get_translation_manager, tr
from src.views.dialogs.base_dialog import BaseDialog
from src.utils.config import ConfigManager
from src.controllers.config_controller import ConfigController
from src.controllers.controller_manager import ControllerManager
from src.utils.theme_manager import get_theme_manager

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
        parent=None
    ):
        """
        Initialise le dialogue des préférences.
        
        Args:
            config_manager: Gestionnaire de configuration
            config_controller: Contrôleur de configuration
            controller_manager: Gestionnaire de contrôleurs
            parent: Widget parent
        """
        super().__init__(
            parent=parent,
            controller_manager=controller_manager,
            title=tr("dialog.preferences.title")
        )
        
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
        
        # Gestionnaire de thèmes
        self.theme_manager = get_theme_manager()
        
        # Garder une copie des valeurs originales
        self.original_values = {}
        
        self.resize(600, 400)
        
        self._create_ui()
        self._load_current_values()
        
    def _create_ui(self):
        """Crée l'interface utilisateur du dialogue."""
        layout = QVBoxLayout(self)
        
        # Onglets de préférences
        self.tab_widget = QTabWidget()
        
        # Onglet Interface
        ui_tab = self._create_ui_tab()
        self.tab_widget.addTab(ui_tab, tr("dialog.preferences.interface_tab"))
        
        # Onglet Données
        data_tab = self._create_data_tab()
        self.tab_widget.addTab(data_tab, tr("dialog.preferences.data_tab"))
        
        # Onglet Système
        system_tab = self._create_system_tab()
        self.tab_widget.addTab(system_tab, tr("dialog.preferences.system_tab"))
        
        layout.addWidget(self.tab_widget)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        save_button = QPushButton(tr("button.save"))
        save_button.clicked.connect(self._save_preferences)
        cancel_button = QPushButton(tr("button.cancel"))
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        
    def _create_ui_tab(self) -> QWidget:
        """Crée l'onglet des paramètres d'interface."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe Interface
        ui_group = QGroupBox(tr("dialog.preferences.ui_group"))
        ui_layout = QFormLayout()
        
        # Langue
        self.language_combo = QComboBox()
        for code, name in self.config_controller.get_supported_languages().items():
            self.language_combo.addItem(name, code)
        ui_layout.addRow("Langue:", self.language_combo)
        
        # Thème
        self.theme_combo = QComboBox()
        for code, name in self.config_controller.get_supported_themes().items():
            self.theme_combo.addItem(name, code)
        # Connecter le signal pour changement de thème en temps réel
        self.theme_combo.currentTextChanged.connect(self._on_theme_preview)
        ui_layout.addRow(tr("dialog.preferences.theme_label"), self.theme_combo)
        
        # Nombre de datasets récents
        self.recent_datasets_spin = QSpinBox()
        self.recent_datasets_spin.setRange(1, 10)
        ui_layout.addRow("Datasets récents:", self.recent_datasets_spin)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        # Groupe Dimensions
        dimensions_group = QGroupBox(tr("dialog.preferences.dimensions_group"))
        dimensions_layout = QFormLayout()
        
        # Largeur
        self.width_spin = QSpinBox()
        self.width_spin.setRange(800, 3840)
        dimensions_layout.addRow("Largeur:", self.width_spin)
        
        # Hauteur
        self.height_spin = QSpinBox()
        self.height_spin.setRange(600, 2160)
        dimensions_layout.addRow("Hauteur:", self.height_spin)
        
        dimensions_group.setLayout(dimensions_layout)
        layout.addWidget(dimensions_group)
        
        layout.addStretch()
        return tab
    
    def _create_data_tab(self) -> QWidget:
        """Crée l'onglet des paramètres de données."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe Stockage
        storage_group = QGroupBox(tr("dialog.preferences.storage_group"))
        storage_layout = QFormLayout()
        
        # Répertoire de base
        self.base_dir_edit = QLineEdit()
        base_dir_browse = QPushButton(tr("button.browse"))
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
        formats_group = QGroupBox(tr("dialog.preferences.formats_group"))
        formats_layout = QVBoxLayout()
        
        self.formats_checkboxes = []
        for fmt in ["jpg", "jpeg", "png", "bmp", "tiff"]:
            cb = QCheckBox(fmt)
            self.formats_checkboxes.append(cb)
            formats_layout.addWidget(cb)
        
        formats_group.setLayout(formats_layout)
        layout.addWidget(formats_group)
        
        # Bouton pour nettoyer le cache
        clear_cache_button = QPushButton(tr("dialog.preferences.clear_cache"))
        clear_cache_button.clicked.connect(self._clear_cache)
        layout.addWidget(clear_cache_button)
        
        layout.addStretch()
        return tab
    
    def _create_system_tab(self) -> QWidget:
        """Crée l'onglet des paramètres système."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Mode débogage
        self.debug_check = QCheckBox(tr("dialog.preferences.debug_mode"))
        layout.addWidget(self.debug_check)
        
        # Groupe API
        api_group = QGroupBox(tr("dialog.preferences.api_group"))
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
        test_button = QPushButton(tr("dialog.preferences.test_api"))
        test_button.clicked.connect(self._test_api_connection)
        layout.addWidget(test_button)
        
        layout.addStretch()
        return tab
    
    def _load_current_values(self):
        """Charge les valeurs actuelles dans l'interface."""
        # Interface
        self._set_combo_by_data(self.language_combo, self.config.ui.language)
        self._set_combo_by_data(self.theme_combo, self.config.ui.theme)
        self.recent_datasets_spin.setValue(self.config.ui.max_recent_datasets)
        self.width_spin.setValue(self.config.ui.window_width)
        self.height_spin.setValue(self.config.ui.window_height)
        
        # Données
        self.base_dir_edit.setText(str(self.config.storage.base_dir))
        self.cache_size_spin.setValue(self.config.storage.max_cache_size_mb)
        
        # Cocher les formats supportés
        for cb in self.formats_checkboxes:
            cb.setChecked(cb.text() in self.config.dataset.supported_formats)
        
        # Système
        self.debug_check.setChecked(self.config.debug_mode)
        self.api_url.setText(self.config.api.mapillary_url)
        self.timeout_spin.setValue(self.config.api.request_timeout)
        
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
        """Sauvegarde les préférences via le contrôleur."""
        try:
            # Collecter les mises à jour
            updates = {
                "ui": {
                    "language": self.language_combo.currentData(),
                    "theme": self.theme_combo.currentData(),
                    "max_recent_datasets": self.recent_datasets_spin.value(),
                    "window_width": self.width_spin.value(),
                    "window_height": self.height_spin.value()
                },
                "storage": {
                    "base_dir": self.base_dir_edit.text(),
                    "max_cache_size_mb": self.cache_size_spin.value()
                },
                "dataset": {
                    "supported_formats": [cb.text() for cb in self.formats_checkboxes if cb.isChecked()]
                },
                "debug_mode": self.debug_check.isChecked(),
                "api": {
                    "mapillary_url": self.api_url.text(),
                    "request_timeout": self.timeout_spin.value()
                }
            }
            
            # Valider les paramètres
            api_validation = self.config_controller.validate_api_config(updates["api"])
            if not api_validation["valid"]:
                error_text = "Erreurs de validation de l'API:\n\n"
                for error in api_validation["errors"]:
                    error_text += f"- {error}\n"
                self.show_error("Erreur de validation", error_text)
                self.tab_widget.setCurrentIndex(2)  # Aller à l'onglet Système
                return
            
            storage_validation = self.config_controller.validate_storage_config(updates["storage"])
            if not storage_validation["valid"]:
                error_text = "Erreurs de validation du stockage:\n\n"
                for error in storage_validation["errors"]:
                    error_text += f"- {error}\n"
                self.show_error("Erreur de validation", error_text)
                self.tab_widget.setCurrentIndex(1)  # Aller à l'onglet Données
                return
            
            # Afficher les avertissements mais permettre la sauvegarde
            warnings = api_validation.get("warnings", []) + storage_validation.get("warnings", [])
            if warnings:
                warning_text = "Avertissements de validation:\n\n"
                for warning in warnings:
                    warning_text += f"- {warning}\n"
                warning_text += "\nVoulez-vous continuer quand même?"
                if not self.confirm_action("Avertissement", warning_text):
                    return
            
            # Sauvegarder via le contrôleur
            config_path = Path("config.json")
            self.config_controller.save_config(updates, config_path)
            
            self.logger.info("Préférences sauvegardées avec succès")
            self.accept()
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde des préférences: {str(e)}")
            self.show_error(
                "Erreur",
                f"Échec de la sauvegarde des préférences:\n{str(e)}"
            )
    
    def _on_theme_preview(self):
        """Applique le thème sélectionné en temps réel pour prévisualisation."""
        try:
            theme_code = self.theme_combo.currentData()
            if theme_code:
                self.theme_manager.set_theme(theme_code)
        except Exception as e:
            self.logger.warning(f"Erreur lors de la prévisualisation du thème: {e}")
    
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