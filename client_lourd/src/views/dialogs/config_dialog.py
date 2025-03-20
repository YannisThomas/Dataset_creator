# src/views/dialogs/config_dialog.py

from PyQt6.QtWidgets import (
    QDialog,
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
    QMessageBox,
    QGroupBox,
    QFormLayout
)
import datetime
from PyQt6.QtCore import Qt
from pathlib import Path
from typing import Dict, Any, Optional

from src.utils.logger import Logger
from src.utils.config import ConfigManager
from src.controllers.config_controller import ConfigController
from src.core.exceptions import ConfigurationError

class ConfigDialog(QDialog):
    """
    Dialogue de configuration générale de l'application.
    Utilise ConfigController pour la logique métier.
    """
    
    def __init__(
        self, 
        config_manager: Optional[ConfigManager] = None,
        config_controller: Optional[ConfigController] = None,
        parent=None
    ):
        """
        Initialise le dialogue de configuration.
        
        Args:
            config_manager: Gestionnaire de configuration
            config_controller: Contrôleur de configuration
            parent: Widget parent
        """
        super().__init__(parent)
        
        self.logger = Logger()
        self.config_manager = config_manager or ConfigManager()
        
        # Utiliser le contrôleur fourni ou en créer un nouveau
        self.config_controller = config_controller
        if not self.config_controller:
            from src.controllers.controller_manager import ControllerManager
            controller_manager = ControllerManager(config_manager=self.config_manager)
            self.config_controller = controller_manager.config_controller
        
        # Récupérer la configuration actuelle
        self.config = self.config_manager.get_config()
        
        # Garder une copie des valeurs originales
        self.original_values = {}
        
        self.setWindowTitle("Configuration")
        self.setModal(True)
        self.resize(600, 400)
        
        self._create_ui()
        self._load_current_values()
        
    def _create_ui(self):
        """Crée l'interface utilisateur."""
        layout = QVBoxLayout(self)
        
        # Onglets de configuration
        self.tab_widget = QTabWidget()
        
        # Onglet Général
        general_tab = self._create_general_tab()
        self.tab_widget.addTab(general_tab, "Général")
        
        # Onglet API
        api_tab = self._create_api_tab()
        self.tab_widget.addTab(api_tab, "API")
        
        # Onglet Base de données
        db_tab = self._create_database_tab()
        self.tab_widget.addTab(db_tab, "Base de données")
        
        layout.addWidget(self.tab_widget)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Enregistrer")
        save_button.clicked.connect(self._save_config)
        cancel_button = QPushButton("Annuler")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        
    def _create_general_tab(self) -> QWidget:
        """Crée l'onglet des paramètres généraux."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe Interface
        ui_group = QGroupBox("Paramètres d'interface")
        ui_layout = QFormLayout()
        
        # Langue

        #self.language_combo = QComboBox()
        #for code, name in self.config_controller.get_supported_languages().items():
        #    self.language_combo.addItem(name, code)
        #ui_layout.addRow("Langue:", self.language_combo)
        
        # Thème
        #self.theme_combo = QComboBox()
        #for code, name in self.config_controller.get_supported_themes().items():
        #    self.theme_combo.addItem(name, code)
        #ui_layout.addRow("Thème:", self.theme_combo)

        # Dimensions de la fenêtre
        self.window_width = QSpinBox()
        self.window_width.setRange(800, 3840)
        ui_layout.addRow("Largeur de la fenêtre:", self.window_width)
        
        self.window_height = QSpinBox()
        self.window_height.setRange(600, 2160)
        ui_layout.addRow("Hauteur de la fenêtre:", self.window_height)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        # Groupe Logging
        log_group = QGroupBox("Journalisation")
        log_layout = QFormLayout()
        
        self.debug_mode = QCheckBox("Activer le mode débogage")
        log_layout.addRow(self.debug_mode)
        
        self.log_path = QLineEdit()
        browse_button = QPushButton("Parcourir...")
        browse_button.clicked.connect(lambda: self._browse_directory(self.log_path))
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.log_path)
        path_layout.addWidget(browse_button)
        
        log_layout.addRow("Répertoire des logs:", path_layout)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        return tab
        
    def _create_api_tab(self) -> QWidget:
        """Crée l'onglet des paramètres API."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe Mapillary
        mapillary_group = QGroupBox("API Mapillary")
        mapillary_layout = QFormLayout()
        
        self.api_token = QLineEdit()
        self.api_token.setEchoMode(QLineEdit.EchoMode.Password)
        mapillary_layout.addRow("Token API:", self.api_token)
        
        self.api_url = QLineEdit()
        mapillary_layout.addRow("URL API:", self.api_url)
        
        self.request_timeout = QSpinBox()
        self.request_timeout.setRange(1, 300)
        self.request_timeout.setSuffix(" secondes")
        mapillary_layout.addRow("Timeout des requêtes:", self.request_timeout)
        
        self.max_retries = QSpinBox()
        self.max_retries.setRange(0, 10)
        mapillary_layout.addRow("Nombre de tentatives:", self.max_retries)
        
        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 100)
        mapillary_layout.addRow("Taille des lots:", self.batch_size)
        
        mapillary_group.setLayout(mapillary_layout)
        layout.addWidget(mapillary_group)
        
        # Test de connexion
        test_button = QPushButton("Tester la connexion")
        test_button.clicked.connect(self._test_api_connection)
        layout.addWidget(test_button)
        
        layout.addStretch()
        return tab
        
    def _create_database_tab(self) -> QWidget:
        """Crée l'onglet des paramètres de base de données."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe Base de données
        db_group = QGroupBox("Paramètres de la base de données")
        db_layout = QFormLayout()
        
        self.db_path = QLineEdit()
        browse_button = QPushButton("Parcourir...")
        browse_button.clicked.connect(lambda: self._browse_file(self.db_path, "Base de données SQLite (*.db)"))
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.db_path)
        path_layout.addWidget(browse_button)
        
        db_layout.addRow("Fichier de base de données:", path_layout)
        
        self.db_echo = QCheckBox("Activer l'écho SQL")
        db_layout.addRow(self.db_echo)
        
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)
        
        # Actions de base de données
        actions_group = QGroupBox("Actions de base de données")
        actions_layout = QVBoxLayout()
        
        backup_button = QPushButton("Sauvegarder la base de données")
        backup_button.clicked.connect(self._backup_database)
        
        migrate_button = QPushButton("Exécuter les migrations")
        migrate_button.clicked.connect(self._run_migrations)
        
        actions_layout.addWidget(backup_button)
        actions_layout.addWidget(migrate_button)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        layout.addStretch()
        return tab
        
    def _load_current_values(self):
        """Charge les valeurs actuelles dans l'interface."""
        # Paramètres généraux
        #self._set_combo_by_data(self.language_combo, self.config.ui.language)
        #self._set_combo_by_data(self.theme_combo, self.config.ui.theme)
        self.window_width.setValue(self.config.ui.window_width)
        self.window_height.setValue(self.config.ui.window_height)
        self.debug_mode.setChecked(self.config.debug_mode)
        self.log_path.setText(str(Path(self.config.storage.base_dir) / "logs"))
        
        # Paramètres API
        self.api_token.setText(self.config.api.mapillary_token or "")
        self.api_url.setText(self.config.api.mapillary_url)
        self.request_timeout.setValue(self.config.api.request_timeout)
        self.max_retries.setValue(self.config.api.max_retries)
        self.batch_size.setValue(self.config.api.batch_size)
        
        # Paramètres base de données
        self.db_path.setText(str(self.config.storage.db_path))
        
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
                #"language": self.language_combo.currentData(),
                #"theme": self.theme_combo.currentData(),
                "window_width": self.window_width.value(),
                "window_height": self.window_height.value()
            },
            "debug": self.debug_mode.isChecked(),
            "api": {
                "token": self.api_token.text(),
                "url": self.api_url.text(),
                "timeout": self.request_timeout.value(),
                "retries": self.max_retries.value(),
                "batch_size": self.batch_size.value()
            },
            "storage": {
                "db_path": self.db_path.text(),
                "log_path": self.log_path.text()
            }
        }
        
    def _save_config(self):
        """Sauvegarde la configuration via le contrôleur."""
        try:
            # Collecter les mises à jour
            updates = {
                "ui": {
                    #"language": self.language_combo.currentData(),
                    #"theme": self.theme_combo.currentData(),
                    "window_width": self.window_width.value(),
                    "window_height": self.window_height.value()
                },
                "debug_mode": self.debug_mode.isChecked(),
                "api": {
                    "mapillary_token": self.api_token.text(),
                    "mapillary_url": self.api_url.text(),
                    "request_timeout": self.request_timeout.value(),
                    "max_retries": self.max_retries.value(),
                    "batch_size": self.batch_size.value()
                },
                "storage": {
                    "db_path": self.db_path.text(),
                    "base_dir": str(Path(self.log_path.text()).parent)
                }
            }
            
            # Valider la configuration
            api_validation = self.config_controller.validate_api_config(updates["api"])
            if not api_validation["valid"]:
                error_text = "Erreurs de validation de l'API:\n\n"
                for error in api_validation["errors"]:
                    error_text += f"- {error}\n"
                QMessageBox.critical(self, "Erreur de validation", error_text)
                self.tab_widget.setCurrentIndex(1)  # Aller à l'onglet API
                return
            
            storage_validation = self.config_controller.validate_storage_config(updates["storage"])
            if not storage_validation["valid"]:
                error_text = "Erreurs de validation du stockage:\n\n"
                for error in storage_validation["errors"]:
                    error_text += f"- {error}\n"
                QMessageBox.critical(self, "Erreur de validation", error_text)
                self.tab_widget.setCurrentIndex(2)  # Aller à l'onglet Base de données
                return
            
            # Afficher les avertissements mais permettre la sauvegarde
            warnings = api_validation.get("warnings", []) + storage_validation.get("warnings", [])
            if warnings:
                warning_text = "Avertissements de validation:\n\n"
                for warning in warnings:
                    warning_text += f"- {warning}\n"
                warning_text += "\nVoulez-vous continuer quand même?"
                reply = QMessageBox.warning(
                    self, 
                    "Avertissement", 
                    warning_text,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Sauvegarder via le contrôleur
            config_path = Path("config.json")
            self.config_controller.save_config(updates, config_path)
            
            self.logger.info("Configuration sauvegardée avec succès")
            self.accept()
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde de la configuration: {str(e)}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Échec de la sauvegarde de la configuration:\n{str(e)}"
            )
            
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
            
    def _browse_file(self, line_edit: QLineEdit, file_filter: str):
        """Ouvre un dialogue pour sélectionner un fichier."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier",
            str(Path(line_edit.text()).parent) if line_edit.text() else str(Path.home()),
            file_filter
        )
        if file_path:
            line_edit.setText(file_path)
            
    def _test_api_connection(self):
        """Teste la connexion à l'API via le contrôleur."""
        try:
            # Collecter les paramètres API actuels
            api_config = {
                "mapillary_token": self.api_token.text(),
                "mapillary_url": self.api_url.text(),
                "request_timeout": self.request_timeout.value(),
                "max_retries": self.max_retries.value(),
                "batch_size": self.batch_size.value()
            }
            
            # Exécuter le test
            test_result = self.config_controller.test_api_connection(api_config)
            
            if test_result["success"]:
                QMessageBox.information(
                    self,
                    "Connexion réussie",
                    test_result["message"]
                )
            else:
                QMessageBox.warning(
                    self,
                    "Échec de la connexion",
                    test_result["message"]
                )
                
        except Exception as e:
            self.logger.error(f"Erreur lors du test de connexion: {str(e)}")
            QMessageBox.critical(
                self,
                "Erreur de connexion",
                f"Échec du test de connexion API:\n{str(e)}"
            )
            
    def _backup_database(self):
        """Crée une sauvegarde de la base de données."""
        try:
            # Exécuter la sauvegarde via le service approprié
            from src.services.database_service import DatabaseService
            database_service = DatabaseService()
            
            # Choisir l'emplacement de sauvegarde
            backup_path, _ = QFileDialog.getSaveFileName(
                self,
                "Sauvegarder la base de données",
                str(Path.home() / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_yolo_datasets.db"),
                "Fichiers SQLite (*.db);;Tous les fichiers (*)"
            )
            
            if backup_path:
                # Effectuer la sauvegarde
                backup_file = database_service.backup_database(Path(backup_path))
                
                QMessageBox.information(
                    self,
                    "Sauvegarde terminée",
                    f"Sauvegarde de la base de données créée à:\n{backup_file}"
                )
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde de la base de données: {str(e)}")
            QMessageBox.critical(
                self,
                "Erreur de sauvegarde",
                f"Échec de la sauvegarde de la base de données:\n{str(e)}"
            )
            
    def _run_migrations(self):
        """Exécute les migrations de base de données."""
        try:
            # Exécuter les migrations via le service approprié
            from src.services.database_service import DatabaseService
            database_service = DatabaseService()
            
            # Demander confirmation
            reply = QMessageBox.question(
                self,
                "Exécuter les migrations",
                "Voulez-vous exécuter les migrations de la base de données?\n"
                "Cette opération peut modifier la structure de la base de données.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Exécuter les migrations
                database_service.apply_migrations()
                
                # Récupérer l'historique des migrations
                migration_status = database_service.get_migration_status()
                
                # Formater le message de résultat
                history_text = "Migrations appliquées:\n\n"
                for migration in migration_status["history"]:
                    history_text += f"- {migration['version']}\n"
                    if migration.get('description'):
                        history_text += f"  {migration['description']}\n"
                
                QMessageBox.information(
                    self,
                    "Migrations terminées",
                    history_text
                )
            
        except Exception as e:
            self.logger.error(f"Échec des migrations de la base de données: {str(e)}")
            QMessageBox.critical(
                self,
                "Erreur de migration",
                f"Échec de l'exécution des migrations:\n{str(e)}"
            )

    def has_changes(self) -> bool:
        """
        Vérifie si des modifications ont été apportées.
        
        Returns:
            True si des modifications ont été faites
        """
        current_values = {
            "ui": {
                #"language": self.language_combo.currentData(),
                #"theme": self.theme_combo.currentData(),
                "window_width": self.window_width.value(),
                "window_height": self.window_height.value()
            },
            "debug": self.debug_mode.isChecked(),
            "api": {
                "token": self.api_token.text(),
                "url": self.api_url.text(),
                "timeout": self.request_timeout.value(),
                "retries": self.max_retries.value(),
                "batch_size": self.batch_size.value()
            },
            "storage": {
                "db_path": self.db_path.text(),
                "log_path": self.log_path.text()
            }
        }
        
        # Comparer avec les valeurs originales
        import json
        return json.dumps(current_values, sort_keys=True) != json.dumps(self.original_values, sort_keys=True)

    def closeEvent(self, event):
        """Gère la fermeture du dialogue."""
        if self.has_changes():
            reply = QMessageBox.question(
                self,
                "Sauvegarder les modifications",
                "Voulez-vous sauvegarder vos modifications?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._save_config()
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def showEvent(self, event):
        """Gère l'affichage initial du dialogue."""
        super().showEvent(event)
        
        # Centrer le dialogue sur l'écran parent
        if self.parent():
            parent_geo = self.parent().geometry()
            dialog_geo = self.geometry()
            x = parent_geo.x() + (parent_geo.width() - dialog_geo.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - dialog_geo.height()) // 2
            self.move(x, y)

    def keyPressEvent(self, event):
        """Gère les événements clavier."""
        # Touche Échap ferme le dialogue
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            
        # Touche Entrée valide si dans un champ de texte
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if isinstance(self.focusWidget(), QLineEdit):
                self.focusWidget().clearFocus()
            else:
                self._save_config()
                
        else:
            super().keyPressEvent(event)