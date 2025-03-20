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
from PyQt6.QtCore import Qt, QEvent
from pathlib import Path
from typing import Dict, Any, Optional

from src.utils.logger import Logger
from src.utils.config import ConfigManager
from src.controllers.config_controller import ConfigController
from src.core.exceptions import ConfigurationError
from src.utils.theme_manager import ThemeManager
from src.utils.translation_manager import TranslationManager
from src.utils.app_utils import tr  # Importation de la fonction de traduction utilitaire

class ConfigDialog(QDialog):
    """
    Dialogue de configuration générale de l'application.
    Utilise ConfigController pour la logique métier.
    """
    
    def __init__(
        self, 
        config_manager: Optional[ConfigManager] = None,
        config_controller: Optional[ConfigController] = None,
        parent=None,
        theme_manager: Optional[ThemeManager] = None,
        translation_manager: Optional[TranslationManager] = None
    ):
        """
        Initialise le dialogue de configuration.
        
        Args:
            config_manager: Gestionnaire de configuration
            config_controller: Contrôleur de configuration
            parent: Widget parent
            theme_manager: Gestionnaire de thèmes
            translation_manager: Gestionnaire de traductions
        """
        super().__init__(parent)
        
        self.logger = Logger()
        self.config_manager = config_manager or ConfigManager()
        
        # Gestionnaires de thème et de traduction
        self.theme_manager = theme_manager
        self.translation_manager = translation_manager
        
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
        
        self.setWindowTitle(tr("Dialogs.configuration_title", "Configuration"))
        self.setModal(True)
        self.resize(600, 400)
        
        self._create_ui()
        self._load_current_values()
        
    def retranslate_ui(self):
        """
        Retraduit tous les éléments statiques de l'interface.
        """
        # Titre de la fenêtre
        self.setWindowTitle(tr("Dialogs.configuration_title", "Configuration"))
        
        # Mise à jour des onglets
        self.tab_widget.setTabText(0, tr("Dialogs.general", "Général"))
        self.tab_widget.setTabText(1, tr("Dialogs.api", "API"))
        self.tab_widget.setTabText(2, tr("Dialogs.database", "Base de données"))
        
        # Traduction des boutons
        self.save_button.setText(tr("Dialogs.save", "Enregistrer"))
        self.cancel_button.setText(tr("Dialogs.cancel", "Annuler"))
        
        # Onglet Général
        self.ui_group.setTitle(tr("Dialogs.interface_settings", "Paramètres d'interface"))
        self.width_label.setText(tr("Dialogs.window_width", "Largeur de la fenêtre:"))
        self.height_label.setText(tr("Dialogs.window_height", "Hauteur de la fenêtre:"))
        self.debug_mode_check.setText(tr("Dialogs.debug_mode", "Activer le mode débogage"))
        
        # Onglet API
        self.mapillary_group.setTitle(tr("Dialogs.mapillary_api", "API Mapillary"))
        self.api_token_label.setText(tr("Dialogs.api_token", "Token API:"))
        self.api_url_label.setText(tr("Dialogs.api_url", "URL API:"))
        self.request_timeout_label.setText(tr("Dialogs.timeout", "Timeout des requêtes:"))
        self.max_retries_label.setText(tr("Dialogs.retries", "Nombre de tentatives:"))
        self.batch_size_label.setText(tr("Dialogs.batch_size", "Taille des lots:"))
        self.test_connection_button.setText(tr("Dialogs.test_connection", "Tester la connexion"))
        
        # Onglet Base de données
        self.db_path_label.setText(tr("Dialogs.database_file", "Fichier de base de données:"))
        self.db_echo_check.setText(tr("Dialogs.enable_sql_echo", "Activer l'écho SQL"))
        self.backup_database_button.setText(tr("Dialogs.backup_database", "Sauvegarder la base de données"))
        self.run_migrations_button.setText(tr("Dialogs.run_migrations", "Exécuter les migrations"))
    
    def _create_ui(self):
        """Crée l'interface utilisateur."""
        layout = QVBoxLayout(self)
        
        # Onglets de configuration
        self.tab_widget = QTabWidget()
        
        # Onglet Général
        general_tab = self._create_general_tab()
        self.tab_widget.addTab(general_tab, tr("Dialogs.general", "Général"))
        
        # Onglet API
        api_tab = self._create_api_tab()
        self.tab_widget.addTab(api_tab, tr("Dialogs.api", "API"))
        
        # Onglet Base de données
        db_tab = self._create_database_tab()
        self.tab_widget.addTab(db_tab, tr("Dialogs.database", "Base de données"))
        
        layout.addWidget(self.tab_widget)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(tr("Dialogs.save", "Enregistrer"))
        self.save_button.clicked.connect(self._save_config)
        self.cancel_button = QPushButton(tr("Dialogs.cancel", "Annuler"))
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
    def _create_general_tab(self) -> QWidget:
        """Crée l'onglet des paramètres généraux."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe Interface
        self.ui_group = QGroupBox(tr("Dialogs.interface_settings", "Paramètres d'interface"))
        ui_layout = QFormLayout()
        
        # Dimensions de la fenêtre
        self.width_label = QLabel(tr("Dialogs.window_width", "Largeur de la fenêtre:"))
        self.window_width = QSpinBox()
        self.window_width.setRange(800, 3840)
        ui_layout.addRow(self.width_label, self.window_width)
        
        self.height_label = QLabel(tr("Dialogs.window_height", "Hauteur de la fenêtre:"))
        self.window_height = QSpinBox()
        self.window_height.setRange(600, 2160)
        ui_layout.addRow(self.height_label, self.window_height)
        
        # Groupe Logging
        self.debug_mode_check = QCheckBox(tr("Dialogs.debug_mode", "Activer le mode débogage"))
        ui_layout.addRow(self.debug_mode_check)
        
        self.log_path_label = QLabel(tr("Dialogs.log_directory", "Répertoire des logs:"))
        self.log_path = QLineEdit()
        browse_button = QPushButton(tr("Dialogs.browse", "Parcourir..."))
        browse_button.clicked.connect(lambda: self._browse_directory(self.log_path))
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.log_path)
        path_layout.addWidget(browse_button)
        
        ui_layout.addRow(self.log_path_label, path_layout)
        
        self.ui_group.setLayout(ui_layout)
        layout.addWidget(self.ui_group)
        
        layout.addStretch()
        return tab
        
    def _create_api_tab(self) -> QWidget:
        """Crée l'onglet des paramètres API."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe Mapillary
        self.mapillary_group = QGroupBox(tr("Dialogs.mapillary_api", "API Mapillary"))
        mapillary_layout = QFormLayout()
        
        # Token API
        self.api_token_label = QLabel(tr("Dialogs.api_token", "Token API:"))
        self.api_token = QLineEdit()
        self.api_token.setEchoMode(QLineEdit.EchoMode.Password)
        mapillary_layout.addRow(self.api_token_label, self.api_token)
        
        # URL API
        self.api_url_label = QLabel(tr("Dialogs.api_url", "URL API:"))
        self.api_url = QLineEdit()
        mapillary_layout.addRow(self.api_url_label, self.api_url)
        
        # Timeout
        self.request_timeout_label = QLabel(tr("Dialogs.timeout", "Timeout des requêtes:"))
        self.request_timeout = QSpinBox()
        self.request_timeout.setRange(1, 300)
        self.request_timeout.setSuffix(tr("Dialogs.seconds", " secondes"))
        mapillary_layout.addRow(self.request_timeout_label, self.request_timeout)
        
        # Nombre de tentatives
        self.max_retries_label = QLabel(tr("Dialogs.retries", "Nombre de tentatives:"))
        self.max_retries = QSpinBox()
        self.max_retries.setRange(0, 10)
        mapillary_layout.addRow(self.max_retries_label, self.max_retries)
        
        # Taille des lots
        self.batch_size_label = QLabel(tr("Dialogs.batch_size", "Taille des lots:"))
        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 100)
        mapillary_layout.addRow(self.batch_size_label, self.batch_size)
        
        self.mapillary_group.setLayout(mapillary_layout)
        layout.addWidget(self.mapillary_group)
        
        # Test de connexion
        self.test_connection_button = QPushButton(tr("Dialogs.test_connection", "Tester la connexion"))
        self.test_connection_button.clicked.connect(self._test_api_connection)
        layout.addWidget(self.test_connection_button)
        
        layout.addStretch()
        return tab
        
    def _create_database_tab(self) -> QWidget:
        """Crée l'onglet des paramètres de base de données."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe Base de données
        db_group = QGroupBox(tr("Dialogs.database_settings", "Paramètres de la base de données"))
        db_layout = QFormLayout()
        
        # Chemin de la base de données
        self.db_path_label = QLabel(tr("Dialogs.database_file", "Fichier de base de données:"))
        self.db_path = QLineEdit()
        browse_button = QPushButton(tr("Dialogs.browse", "Parcourir..."))
        browse_button.clicked.connect(lambda: self._browse_file(self.db_path, "Base de données SQLite (*.db)"))
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.db_path)
        path_layout.addWidget(browse_button)
        
        db_layout.addRow(self.db_path_label, path_layout)
        
        # Écho SQL
        self.db_echo_check = QCheckBox(tr("Dialogs.enable_sql_echo", "Activer l'écho SQL"))
        db_layout.addRow(self.db_echo_check)
        
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)
        
        # Actions de base de données
        actions_group = QGroupBox(tr("Dialogs.database_actions", "Actions de base de données"))
        actions_layout = QVBoxLayout()
        
        # Bouton de sauvegarde
        self.backup_database_button = QPushButton(tr("Dialogs.backup_database", "Sauvegarder la base de données"))
        self.backup_database_button.clicked.connect(self._backup_database)
        
        # Bouton de migration
        self.run_migrations_button = QPushButton(tr("Dialogs.run_migrations", "Exécuter les migrations"))
        self.run_migrations_button.clicked.connect(self._run_migrations)
        
        actions_layout.addWidget(self.backup_database_button)
        actions_layout.addWidget(self.run_migrations_button)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        layout.addStretch()
        return tab
        
    def _load_current_values(self):
        """Charge les valeurs actuelles dans l'interface."""
        # Paramètres généraux
        self.window_width.setValue(self.config.ui.window_width)
        self.window_height.setValue(self.config.ui.window_height)
        self.debug_mode_check.setChecked(self.config.debug_mode)
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
    
    def _save_config(self):
        """Sauvegarde la configuration via le contrôleur."""
        try:
            # Collecter les mises à jour
            updates = {
                "ui": {
                    "window_width": self.window_width.value(),
                    "window_height": self.window_height.value()
                },
                "debug_mode": self.debug_mode_check.isChecked(),
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
                error_text = tr("Messages.api_validation_error", "Erreurs de validation de l'API:\n\n")
                for error in api_validation["errors"]:
                    error_text += f"- {error}\n"
                QMessageBox.critical(self, tr("Messages.error", "Erreur de validation"), error_text)
                self.tab_widget.setCurrentIndex(1)  # Aller à l'onglet API
                return
            
            storage_validation = self.config_controller.validate_storage_config(updates["storage"])
            if not storage_validation["valid"]:
                error_text = tr("Messages.storage_validation_error", "Erreurs de validation du stockage:\n\n")
                for error in storage_validation["errors"]:
                    error_text += f"- {error}\n"
                QMessageBox.critical(self, tr("Messages.error", "Erreur de validation"), error_text)
                self.tab_widget.setCurrentIndex(2)
                return
            
            # Afficher les avertissements mais permettre la sauvegarde
            warnings = api_validation.get("warnings", []) + storage_validation.get("warnings", [])
            if warnings:
                warning_text = tr("Messages.validation_warnings", "Avertissements de validation:\n\n")
                for warning in warnings:
                    warning_text += f"- {warning}\n"
                warning_text += tr("Messages.continue_confirmation", "\nVoulez-vous continuer quand même?")
                reply = QMessageBox.warning(
                    self, 
                    tr("Messages.warning", "Avertissement"), 
                    warning_text,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Sauvegarder via le contrôleur
            config_path = Path("config.json")
            self.config_controller.save_config(updates, config_path)
            
            # Log
            self.logger.info("Configuration sauvegardée avec succès")
            
            # Accepter le dialogue
            self.accept()
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde de la configuration: {str(e)}")
            self.show_error(
                tr("Messages.error", "Erreur"),
                tr("Messages.save_failed", f"Échec de la sauvegarde de la configuration:\n{str(e)}")
            )
    
    def _save_original_values(self):
        """Sauvegarde les valeurs originales pour détecter les changements."""
        self.original_values = {
            "ui": {
                "window_width": self.window_width.value(),
                "window_height": self.window_height.value()
            },
            "debug": self.debug_mode_check.isChecked(),
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
    
    def _browse_directory(self, line_edit: QLineEdit):
        """Ouvre un dialogue pour sélectionner un répertoire."""
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("Dialogs.select_directory", "Sélectionner un répertoire"),
            line_edit.text() or str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            line_edit.setText(directory)
            
    def _browse_file(self, line_edit: QLineEdit, file_filter: str):
        """Ouvre un dialogue pour sélectionner un fichier."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Dialogs.select_file", "Sélectionner un fichier"),
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
                    tr("Messages.connection_success", "Connexion réussie"),
                    test_result["message"]
                )
            else:
                QMessageBox.warning(
                    self,
                    tr("Messages.connection_failure", "Échec de la connexion"),
                    test_result["message"]
                )
                
        except Exception as e:
            self.logger.error(f"Erreur lors du test de connexion: {str(e)}")
            QMessageBox.critical(
                self,
                tr("Messages.error", "Erreur de connexion"),
                tr("Messages.connection_test_failed", f"Échec du test de connexion API:\n{str(e)}")
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
                tr("Dialogs.backup_database_title", "Sauvegarder la base de données"),
                str(Path.home() / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_yolo_datasets.db"),
                tr("Dialogs.database_file_filter", "Fichiers SQLite (*.db);;Tous les fichiers (*)")
            )
            
            if backup_path:
                # Effectuer la sauvegarde
                backup_file = database_service.backup_database(Path(backup_path))
                
                QMessageBox.information(
                    self,
                    tr("Messages.backup_complete", "Sauvegarde terminée"),
                    tr("Messages.backup_created", f"Sauvegarde de la base de données créée à:\n{backup_file}")
                )
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde de la base de données: {str(e)}")
            QMessageBox.critical(
                self,
                tr("Messages.error", "Erreur de sauvegarde"),
                tr("Messages.backup_failed", f"Échec de la sauvegarde de la base de données:\n{str(e)}")
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
                tr("Dialogs.run_migrations_title", "Exécuter les migrations"),
                tr("Dialogs.run_migrations_confirm", 
                   "Voulez-vous exécuter les migrations de la base de données?\n"
                   "Cette opération peut modifier la structure de la base de données."),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Exécuter les migrations
                database_service.apply_migrations()
                
                # Récupérer l'historique des migrations
                migration_status = database_service.get_migration_status()
                
                # Formater le message de résultat
                history_text = tr("Dialogs.migrations_applied", "Migrations appliquées:\n\n")
                for migration in migration_status["history"]:
                    history_text += f"- {migration['version']}\n"
                    if migration.get('description'):
                        history_text += f"  {migration['description']}\n"
                
                QMessageBox.information(
                    self,
                    tr("Dialogs.migrations_complete", "Migrations terminées"),
                    history_text
                )
            
        except Exception as e:
            self.logger.error(f"Échec des migrations de la base de données: {str(e)}")
            QMessageBox.critical(
                self,
                tr("Messages.error", "Erreur de migration"),
                tr("Messages.migrations_failed", f"Échec de l'exécution des migrations:\n{str(e)}")
            )

    def has_changes(self) -> bool:
        """
        Vérifie si des modifications ont été apportées.
        
        Returns:
            True si des modifications ont été faites
        """
        current_values = {
            "ui": {
                "window_width": self.window_width.value(),
                "window_height": self.window_height.value()
            },
            "debug": self.debug_mode_check.isChecked(),
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

    def changeEvent(self, event):
        """
        Gère les événements de changement.
        Utile pour intercepter les changements de langue.
        """
        if event.type() == QEvent.Type.LanguageChange:
            # Retraduite l'interface
            self.retranslate_ui()
        
        super().changeEvent(event)

    def closeEvent(self, event):
        """Gère la fermeture du dialogue."""
        if self.has_changes():
            reply = QMessageBox.question(
                self,
                tr("Messages.save_changes", "Sauvegarder les modifications"),
                tr("Messages.unsaved_changes", "Des modifications ont été apportées. Voulez-vous les sauvegarder?"),
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