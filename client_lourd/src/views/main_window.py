# src/views/main_window.py

from PyQt6.QtWidgets import (
    QMainWindow, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout,
    QPushButton,
    QLabel,
    QStatusBar,
    QMenuBar,
    QMenu,
    QMessageBox,
    QFileDialog,
    QProgressBar,
    QApplication,
    QTabWidget
)
from PyQt6.QtCore import Qt, QSize
from pathlib import Path

from src.controllers.controller_manager import ControllerManager
from src.utils.logger import Logger
from src.utils.i18n import get_translation_manager, tr
from src.utils.theme_manager import get_theme_manager
from src.core.exceptions import YoloDatasetError
from src.views.dataset_view import DatasetView
from src.views.dashboard_view import DashboardView
from src.views.dialogs.new_dataset_dialog import NewDatasetDialog
from src.views.dialogs.preferences_dialog import PreferencesDialog
from src.views.dialogs.mapillary_import_dialog import MapillaryImportDialog
from src.views.dialogs.config_dialog import ConfigDialog
from src.utils.config import ConfigManager


class MainWindow(QMainWindow):
    """
    Fenêtre principale de l'application.
    Cette classe utilise les contrôleurs pour effectuer les opérations métier.
    """
    
    def __init__(self, controller_manager: ControllerManager = None):
        """
        Initialise la fenêtre principale.
        
        Args:
            controller_manager: Gestionnaire de contrôleurs
        """
        super().__init__()
        
        # Initialisation
        self.logger = Logger()
        self.controller_manager = controller_manager or ControllerManager()
        self.dataset_controller = self.controller_manager.dataset_controller
        self.import_controller = self.controller_manager.import_controller
        self.export_controller = self.controller_manager.export_controller
        self.api_controller = self.controller_manager.api_controller
        
        # Gestionnaire de traductions
        self.translation_manager = get_translation_manager()
        
        # Gestionnaire de thèmes
        self.theme_manager = get_theme_manager()
        
        # Configuration de la fenêtre
        config = self.controller_manager.config_manager.get_config()
        
        # Initialiser la langue depuis la configuration
        self.translation_manager.set_language(config.ui.language)
        
        # Initialiser le thème depuis la configuration
        self.theme_manager.set_theme(config.ui.theme)
        
        # Connecter les signaux
        self.translation_manager.language_changed.connect(self._on_language_changed)
        self.theme_manager.theme_changed.connect(self._on_theme_changed)
        
        self.setWindowTitle(tr("main_window.title"))
        self.resize(config.ui.window_width, config.ui.window_height)
        
        # Création de l'interface
        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()
        
        self.logger.info("Interface principale initialisée")
        
    def _create_menu_bar(self):
        """Crée la barre de menu."""
        self.menubar = self.menuBar()
        self._update_menu_bar()
        
    def _update_menu_bar(self):
        """Met à jour la barre de menu avec les traductions actuelles."""
        self.menubar.clear()
        
        # Menu Fichier
        file_menu = self.menubar.addMenu(tr("main_window.file"))
        
        # Actions du menu Fichier
        new_dataset_action = file_menu.addAction(tr("menu.file.new_dataset"))
        new_dataset_action.triggered.connect(self._on_new_dataset)
        
        open_dataset_action = file_menu.addAction(tr("menu.file.open_dataset"))
        open_dataset_action.triggered.connect(self._on_open_dataset)
        
        save_dataset_action = file_menu.addAction(tr("menu.file.save_dataset"))
        save_dataset_action.triggered.connect(self._on_save_dataset)
        
        file_menu.addSeparator()
        
        # Sous-menu Import
        import_menu = file_menu.addMenu(tr("menu.file.import_mapillary"))
        import_mapillary_action = import_menu.addAction("Mapillary...")
        import_mapillary_action.triggered.connect(self._on_import_mapillary)
        import_local_action = import_menu.addAction(tr("menu.file.import_local"))
        import_local_action.triggered.connect(self._on_import_local)
        
        # Sous-menu Export
        export_menu = file_menu.addMenu(tr("menu.file.export"))
        export_yolo_action = export_menu.addAction(tr("export.format.yolo"))
        export_yolo_action.triggered.connect(lambda: self._on_export("yolo"))
        export_coco_action = export_menu.addAction(tr("export.format.coco"))
        export_coco_action.triggered.connect(lambda: self._on_export("coco"))
        export_voc_action = export_menu.addAction(tr("export.format.voc"))
        export_voc_action.triggered.connect(lambda: self._on_export("voc"))
        
        file_menu.addSeparator()
        
        preferences_action = file_menu.addAction(tr("menu.file.preferences"))
        preferences_action.triggered.connect(self._on_preferences)
        
        file_menu.addSeparator()
        
        quit_action = file_menu.addAction(tr("menu.file.quit"))
        quit_action.triggered.connect(self.close)
        
        # Menu Edit
        edit_menu = self.menubar.addMenu(tr("main_window.edit"))
        
        # Actions d'édition standard
        undo_action = edit_menu.addAction(tr("menu.edit.undo"))
        undo_action.setEnabled(False)  # À implémenter
        
        redo_action = edit_menu.addAction(tr("menu.edit.redo"))
        redo_action.setEnabled(False)  # À implémenter
        
        edit_menu.addSeparator()
        
        select_all_action = edit_menu.addAction(tr("menu.edit.select_all"))
        select_all_action.setEnabled(False)  # À implémenter
        
        # Menu View
        view_menu = self.menubar.addMenu(tr("main_window.view"))
        
        # Sous-menu Langue
        language_menu = view_menu.addMenu(tr("menu.view.language"))
        self._create_language_menu(language_menu)
        
        # Sous-menu Thème  
        theme_menu = view_menu.addMenu(tr("menu.view.theme"))
        self._create_theme_menu(theme_menu)
        
        view_menu.addSeparator()
        
        # Actions du menu View
        zoom_in_action = view_menu.addAction(tr("menu.view.zoom_in"))
        zoom_in_action.setEnabled(False)  # À implémenter
        
        zoom_out_action = view_menu.addAction(tr("menu.view.zoom_out"))
        zoom_out_action.setEnabled(False)  # À implémenter
        
        fit_window_action = view_menu.addAction(tr("menu.view.fit_to_window"))
        fit_window_action.setEnabled(False)  # À implémenter
        
        # Menu Tools
        tools_menu = self.menubar.addMenu(tr("main_window.tools"))
        
        config_action = tools_menu.addAction("Configuration...")
        config_action.triggered.connect(self._on_configuration)
        
        # Menu Help
        help_menu = self.menubar.addMenu(tr("main_window.help"))
        
        about_action = help_menu.addAction("À propos")
        about_action.triggered.connect(self._on_about)
    
    def _create_language_menu(self, language_menu):
        """Crée le sous-menu de sélection de langue."""
        current_language = self.translation_manager.get_current_language()
        available_languages = self.translation_manager.get_available_languages()
        
        for lang_code, lang_name in available_languages.items():
            action = language_menu.addAction(lang_name)
            action.setCheckable(True)
            action.setChecked(lang_code == current_language)
            action.triggered.connect(lambda checked, code=lang_code: self._on_language_changed_menu(code))
    
    def _create_theme_menu(self, theme_menu):
        """Crée le sous-menu de sélection de thème."""
        current_theme = self.theme_manager.get_current_theme()
        available_themes = self.theme_manager.get_available_themes()
        
        for theme_code, theme_name in available_themes.items():
            action = theme_menu.addAction(theme_name)
            action.setCheckable(True)
            action.setChecked(theme_code == current_theme)
            action.triggered.connect(lambda checked, code=theme_code: self._on_theme_changed_menu(code))
    
    def _on_language_changed_menu(self, language_code: str):
        """Gestionnaire pour le changement de langue depuis le menu."""
        try:
            # Mettre à jour la configuration (en mémoire)
            self.controller_manager.config_manager.set_language(language_code)
            
            # Sauvegarder la configuration
            self.controller_manager.config_manager.save_config_default()
            
            # Appliquer la langue
            self.translation_manager.set_language(language_code)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du changement de langue: {e}")
    
    def _on_theme_changed_menu(self, theme_code: str):
        """Gestionnaire pour le changement de thème depuis le menu."""
        try:
            # Mettre à jour la configuration (en mémoire)
            self.controller_manager.config_manager.set_theme(theme_code)
            
            # Sauvegarder la configuration
            self.controller_manager.config_manager.save_config_default()
            
            # Appliquer le thème
            self.theme_manager.set_theme(theme_code)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du changement de thème: {e}")
    
    def _on_theme_changed(self, theme_code: str):
        """Gestionnaire pour le changement de thème."""
        # Mettre à jour la barre de menu pour refléter le nouveau thème
        self._update_menu_bar()
        
        self.logger.info(f"Thème appliqué: {theme_code}")
    
    def _on_language_changed(self, language_code: str):
        """Gestionnaire pour le changement de langue."""
        # Mettre à jour le titre de la fenêtre
        self.setWindowTitle(tr("main_window.title"))
        
        # Mettre à jour la barre de menu
        self._update_menu_bar()
        
        # Mettre à jour la barre de statut
        self._update_status_bar()
        
        self.logger.info(f"Interface mise à jour pour la langue: {language_code}")
    
    def _on_theme_changed(self, theme_code: str):
        """Gestionnaire pour le changement de thème."""
        self.controller_manager.config_manager.set_theme(theme_code)
        # TODO: Appliquer le thème à l'interface
        self.logger.info(f"Thème changé vers: {theme_code}")
    
    def _update_status_bar(self):
        """Met à jour la barre de statut avec les traductions."""
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(tr("status.ready"))
        
    def _create_central_widget(self):
        """Crée le widget central avec onglets."""
        # Créer le widget à onglets
        self.tab_widget = QTabWidget()
        
        # Créer le dashboard
        self.dashboard_view = DashboardView(controller_manager=self.controller_manager)
        self.dashboard_view.dataset_requested.connect(self._on_dashboard_dataset_requested)
        self.dashboard_view.create_dataset_requested.connect(self._on_new_dataset)
        self.dashboard_view.import_requested.connect(self._on_import_mapillary)
        
        # Créer la vue de dataset
        self.dataset_view = DatasetView()
        self.dataset_view.dataset_modified.connect(self._on_dataset_modified)
        
        # Ajouter les onglets
        self.tab_widget.addTab(self.dashboard_view, tr("main_window.dashboard"))
        self.tab_widget.addTab(self.dataset_view, tr("main_window.dataset"))
        
        # Définir comme widget central
        self.setCentralWidget(self.tab_widget)
        
    def _create_status_bar(self):
        """Crée la barre de statut."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage(tr("status.ready"))
        
        # Ajouter des indicateurs permanents
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.hide()
        status_bar.addPermanentWidget(self.progress_bar)
        
    def _on_dataset_modified(self, dataset):
        """Gère la modification du dataset."""
        try:
            # Utiliser le contrôleur pour mettre à jour le dataset
            self.dataset_controller.update_dataset(dataset)
            self.statusBar().showMessage("Dataset sauvegardé avec succès", 3000)
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde du dataset: {str(e)}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Échec de la sauvegarde du dataset: {str(e)}"
            )
    
    def _on_dashboard_dataset_requested(self, dataset_name: str):
        """Gère l'ouverture d'un dataset depuis le dashboard."""
        try:
            # Charger le dataset via le contrôleur
            dataset = self.dataset_controller.get_dataset(dataset_name)
            if dataset:
                # Afficher dans la vue dataset
                self.dataset_view.set_dataset(dataset)
                # Basculer vers l'onglet dataset
                self.tab_widget.setCurrentIndex(1)
                self.statusBar().showMessage(f"Dataset ouvert: {dataset.name}")
            else:
                QMessageBox.warning(
                    self,
                    "Erreur",
                    f"Impossible de charger le dataset: {dataset_name}"
                )
        except Exception as e:
            self.logger.error(f"Échec du chargement du dataset {dataset_name}: {str(e)}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Échec du chargement du dataset: {str(e)}"
            )
            
    def _on_new_dataset(self):
        """Gère la création d'un nouveau dataset."""
        self.logger.debug("Action de nouveau dataset déclenchée")
        
        # Utiliser le dialogue avec le contrôleur
        dialog = NewDatasetDialog(self, self.dataset_controller)
        if dialog.exec():
            try:
                # Récupérer les informations du dataset
                dataset_info = dialog.get_dataset_info()
                if dataset_info:
                    # Créer le dataset via le contrôleur
                    dataset = self.dataset_controller.create_dataset(
                        name=dataset_info["name"],
                        classes=dataset_info["classes"],
                        version=dataset_info["version"],
                        base_path=dataset_info["path"]
                    )
                    
                    # Afficher dans la vue
                    self.dataset_view.set_dataset(dataset)
                    # Basculer vers l'onglet dataset
                    self.tab_widget.setCurrentIndex(1)
                    # Rafraîchir le dashboard
                    self.dashboard_view.refresh_stats()
                    self.statusBar().showMessage(f"Dataset créé: {dataset.name}")
            except Exception as e:
                self.logger.error(f"Échec de la création du dataset: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Échec de la création du dataset: {str(e)}"
                )
                
    def _on_open_dataset(self):
        """Gère l'ouverture d'un dataset existant depuis la base de données."""
        try:
            # Récupérer la liste des datasets depuis la base de données
            datasets = self.dataset_controller.list_datasets()
            
            if not datasets:
                QMessageBox.information(
                    self,
                    "Information",
                    "Aucun dataset trouvé dans la base de données.\nVeuillez d'abord créer ou importer un dataset."
                )
                return
            
            # Créer une liste de choix pour l'utilisateur
            from PyQt6.QtWidgets import QInputDialog
            dataset_names = [f"{d['name']} ({d['image_count']} images)" for d in datasets]
            
            choice, ok = QInputDialog.getItem(
                self,
                "Ouvrir Dataset",
                "Sélectionnez un dataset à ouvrir:",
                dataset_names,
                0,
                False
            )
            
            if ok and choice:
                # Extraire le nom du dataset
                dataset_name = choice.split(' (')[0]
                
                # Charger le dataset via le contrôleur
                dataset = self.dataset_controller.get_dataset(dataset_name)
                if dataset:
                    # Afficher dans la vue
                    self.dataset_view.set_dataset(dataset)
                    self.statusBar().showMessage(f"Dataset ouvert: {dataset.name}")
                else:
                    raise YoloDatasetError("Échec du chargement du dataset")
                    
        except Exception as e:
            self.logger.error(f"Échec de l'ouverture du dataset: {str(e)}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Échec de l'ouverture du dataset: {str(e)}"
            )
    
    def _on_save_dataset(self):
        """Gère la sauvegarde du dataset courant."""
        try:
            current_dataset = self.dataset_view.dataset
            if not current_dataset:
                QMessageBox.warning(
                    self,
                    tr("error.title"),
                    "Aucun dataset ouvert à sauvegarder"
                )
                return
            
            # Sauvegarder via le contrôleur
            success = self.dataset_controller.save_dataset(current_dataset)
            if success:
                self.statusBar().showMessage(tr("status.saving"))
                QMessageBox.information(
                    self,
                    "Succès",
                    f"Dataset '{current_dataset.name}' sauvegardé avec succès"
                )
            else:
                QMessageBox.critical(
                    self,
                    tr("error.title"),
                    "Échec de la sauvegarde du dataset"
                )
                
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde: {str(e)}")
            QMessageBox.critical(
                self,
                tr("error.title"),
                f"Erreur lors de la sauvegarde: {str(e)}"
            )
            
    def _on_import_mapillary(self):
        """Gère l'import depuis Mapillary."""
        try:
            # Récupérer le dataset actuel
            current_dataset = self.dataset_view.dataset
            
            # Utiliser le dialogue avec le contrôleur d'import
            dialog = MapillaryImportDialog(self, current_dataset, self.import_controller, self.api_controller)
            
            if dialog.exec():
                # Récupérer les résultats de l'import
                import_results = dialog.get_import_results()
                
                if import_results and import_results.get("success", False):
                    # Obtenir le dataset importé
                    updated_dataset = import_results.get("dataset")
                    
                    if updated_dataset:
                        if current_dataset and current_dataset.name == updated_dataset.name:
                            # Si c'est le même dataset, forcer un rechargement pour être sûr
                            self.logger.info(f"Rechargement du dataset {updated_dataset.name} depuis la base de données")
                            try:
                                # Essayer de recharger depuis la base de données
                                refreshed_dataset = self.dataset_controller.get_dataset(updated_dataset.name)
                                if refreshed_dataset:
                                    updated_dataset = refreshed_dataset
                            except Exception as e:
                                self.logger.warning(f"Échec du rechargement du dataset depuis la base de données: {str(e)}")
                                # Continuer avec le dataset retourné par le dialogue
                                
                        # Mettre à jour la vue du dataset
                        self.dataset_view.set_dataset(updated_dataset)
                        
                        self.statusBar().showMessage(
                            f"Importé {len(import_results.get('images', []))} images avec succès",
                            3000  # Afficher pendant 3 secondes
                        )
                    else:
                        self.logger.warning("Aucun dataset retourné par l'import")
                        QMessageBox.warning(
                            self,
                            "Avertissement",
                            "L'import a réussi mais aucun dataset n'a été retourné"
                        )
                else:
                    self.logger.warning("Échec de l'import ou résultats invalides")
                    
        except Exception as e:
            self.logger.error(f"Échec de l'import depuis Mapillary: {str(e)}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Échec de l'import depuis Mapillary: {str(e)}"
            )
                
    def _on_import_local(self):
        """Gère l'import depuis des fichiers locaux."""
        try:
            # Vérifier qu'un dataset est ouvert
            current_dataset = self.dataset_view.dataset
            if not current_dataset:
                QMessageBox.warning(
                    self,
                    "Attention",
                    "Veuillez d'abord créer ou ouvrir un dataset"
                )
                return
            
            # Sélectionner les fichiers
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Sélectionner des images",
                str(Path.home()),
                "Images (*.jpg *.jpeg *.png);;Tous les fichiers (*)"
            )
            
            if not files:
                return  # L'utilisateur a annulé la sélection
                
            # Afficher la barre de progression
            self.progress_bar.setMaximum(len(files))
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            
            # Importer les images via le contrôleur
            try:
                imported_count = 0
                failed_count = 0
                
                for i, file_path in enumerate(files, 1):
                    try:
                        # Utiliser le contrôleur d'import
                        success = self.import_controller.import_image_to_dataset(
                            dataset=current_dataset,
                            image_path=file_path
                        )
                        
                        if success:
                            imported_count += 1
                        else:
                            failed_count += 1
                        
                        # Mettre à jour la progression
                        self.progress_bar.setValue(i)
                        QApplication.processEvents()  # Garder l'interface réactive
                        
                    except Exception as e:
                        self.logger.error(f"Échec de l'import du fichier {file_path}: {str(e)}")
                        failed_count += 1
                
                # Masquer la barre de progression
                self.progress_bar.hide()
                
                # Mettre à jour la vue du dataset
                self.dataset_view.set_dataset(current_dataset)
                
                # Afficher un résumé
                summary = f"Importé {imported_count} images avec succès"
                if failed_count > 0:
                    summary += f", {failed_count} fichiers ont échoué"
                
                self.statusBar().showMessage(summary, 3000)
                
            except Exception as e:
                self.progress_bar.hide()
                raise e
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'import local: {str(e)}")
            self.progress_bar.hide()
            QMessageBox.critical(
                self,
                "Erreur",
                f"Échec de l'import des fichiers: {str(e)}"
            )
            
    def _on_export(self, format_name: str):
        """Gère l'export du dataset."""
        try:
            current_dataset = self.dataset_view.dataset
            if not current_dataset:
                QMessageBox.warning(
                    self,
                    "Attention",
                    "Aucun dataset chargé"
                )
                return
                
            # Sélectionner le répertoire de sortie
            config = self.controller_manager.config_manager.get_config()
            export_dir = QFileDialog.getExistingDirectory(
                self,
                "Sélectionner le répertoire d'export",
                str(config.storage.base_dir)
            )
            
            if export_dir:
                # Exporter le dataset via le contrôleur
                export_path = self.export_controller.export_dataset(
                    dataset=current_dataset,
                    export_format=format_name,
                    output_path=Path(export_dir)
                )
                
                self.statusBar().showMessage(
                    f"Dataset exporté vers {export_path}"
                )
                
        except Exception as e:
            self.logger.error(f"Échec de l'export: {str(e)}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Échec de l'export du dataset: {str(e)}"
            )
            
    def _on_preferences(self):
        """Gère l'ouverture des préférences."""
        dialog = PreferencesDialog(self.controller_manager.config_manager, self)
        if dialog.exec():
            # Recharger la configuration et réinitialiser les contrôleurs
            self.controller_manager.config_manager = ConfigManager()
            self.controller_manager.reset_controllers()
            
            # Réassigner les contrôleurs
            self.dataset_controller = self.controller_manager.dataset_controller
            self.import_controller = self.controller_manager.import_controller
            self.export_controller = self.controller_manager.export_controller
            self.api_controller = self.controller_manager.api_controller
            
            self.statusBar().showMessage("Préférences mises à jour")
            
    def _on_validate_dataset(self):
        """Valide le dataset actuel."""
        current_dataset = self.dataset_view.dataset
        if not current_dataset:
            QMessageBox.warning(self, "Attention", "Aucun dataset chargé")
            return
            
        # Valider le dataset via le contrôleur
        validation = self.dataset_controller.validate_dataset(current_dataset)
        
        if validation["valid"]:
            QMessageBox.information(
                self,
                "Validation",
                "Le dataset est valide!"
            )
        else:
            error_text = "La validation du dataset a échoué:\n\n"
            for error in validation["errors"]:
                error_text += f"- {error}\n"
                
            if validation.get("warnings"):
                error_text += "\nAvertissements:\n"
                for warning in validation["warnings"]:
                    error_text += f"- {warning}\n"
                    
            QMessageBox.warning(
                self,
                "Validation",
                error_text
            )
            
    def _on_configuration(self):
        """Ouvre le dialogue de configuration."""
        dialog = ConfigDialog(self.controller_manager.config_manager, self)
        if dialog.exec():
            # Recharger la configuration si nécessaire
            self.controller_manager.config_manager = ConfigManager()
            self.controller_manager.reset_controllers()
            
            # Réassigner les contrôleurs
            self.dataset_controller = self.controller_manager.dataset_controller
            self.import_controller = self.controller_manager.import_controller
            self.export_controller = self.controller_manager.export_controller
            self.api_controller = self.controller_manager.api_controller
            
            self.statusBar().showMessage("Configuration mise à jour", 3000)
            
    def _on_about(self):
        """Affiche la boîte de dialogue À propos."""
        QMessageBox.about(
            self,
            "À propos de YOLO Dataset Manager",
            "YOLO Dataset Manager\n\n"
            "Un outil pour gérer et préparer des datasets pour l'entraînement YOLO.\n\n"
            "Version: 1.0.0"
        )
        
    def closeEvent(self, event):
        """Gère la fermeture de l'application."""
        # Vérifier s'il y a des modifications non sauvegardées
        if self.dataset_view.dataset and self.dataset_view.dataset.modified_at:
            reply = QMessageBox.question(
                self,
                'Sauvegarder les changements',
                "Sauvegarder les changements avant de quitter?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Yes:
                # Sauvegarder les modifications via le contrôleur
                try:
                    self.dataset_controller.update_dataset(self.dataset_view.dataset)
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Erreur",
                        f"Échec de la sauvegarde du dataset:\n{str(e)}"
                    )
                    event.ignore()
                    return
        
        # Confirmation finale
        reply = QMessageBox.question(
            self,
            'Confirmer la sortie',
            "Êtes-vous sûr de vouloir quitter?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.logger.info("Application en cours de fermeture")
            event.accept()
        else:
            event.ignore()
            
    def showEvent(self, event):
        """Gère l'affichage initial de la fenêtre."""
        super().showEvent(event)
        
        # Charger les paramètres de fenêtre depuis la configuration
        config = self.controller_manager.config_manager.get_config()
        if hasattr(config.ui, 'window_geometry'):
            self.restoreGeometry(config.ui.window_geometry)
        else:
            # Centrer la fenêtre sur l'écran
            screen = self.screen().availableGeometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2
            )
            
    def resizeEvent(self, event):
        """Gère le redimensionnement de la fenêtre."""
        super().resizeEvent(event)
        
        # Sauvegarder la nouvelle taille
        config = self.controller_manager.config_manager.get_config()
        if hasattr(config.ui, 'window_width'):
            config.ui.window_width = self.width()
            config.ui.window_height = self.height()
            
    def update_status(self, message: str, timeout: int = 3000):
        """
        Met à jour le message de la barre de statut.
        
        Args:
            message: Message à afficher
            timeout: Durée d'affichage en millisecondes (0 pour permanent)
        """
        self.statusBar().showMessage(message, timeout)
        
    def show_progress(self, visible: bool = True, maximum: int = 100):
        """
        Affiche ou masque la barre de progression.
        
        Args:
            visible: True pour afficher, False pour masquer
            maximum: Valeur maximale de la progression
        """
        if visible:
            self.progress_bar.setMaximum(maximum)
            self.progress_bar.setValue(0)
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
            
    def set_progress(self, value: int):
        """
        Met à jour la valeur de la barre de progression.
        
        Args:
            value: Nouvelle valeur
        """
        self.progress_bar.setValue(value)
        
    def confirm_action(self, title: str, message: str) -> bool:
        """
        Demande une confirmation à l'utilisateur.
        
        Args:
            title: Titre de la boîte de dialogue
            message: Message à afficher
            
        Returns:
            True si l'utilisateur confirme
        """
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes