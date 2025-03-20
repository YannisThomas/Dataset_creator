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
    QApplication
)
from PyQt6.QtCore import Qt, QSize, QEvent
from pathlib import Path

from src.controllers.controller_manager import ControllerManager
from src.utils.logger import Logger
from src.utils.theme_manager import ThemeManager
from src.utils.translation_manager import TranslationManager
from src.core.exceptions import YoloDatasetError
from src.views.dataset_view import DatasetView
from src.views.dialogs.new_dataset_dialog import NewDatasetDialog
from src.views.dialogs.preferences_dialog import PreferencesDialog
from src.views.dialogs.mapillary_import_dialog import MapillaryImportDialog
from src.views.dialogs.config_dialog import ConfigDialog
from src.utils.config import ConfigManager
from src.utils.app_utils import tr  # Importation de la fonction de traduction utilitaire

class MainWindow(QMainWindow):
    """
    Fenêtre principale de l'application.
    Cette classe utilise les contrôleurs pour effectuer les opérations métier.
    """
    
    def __init__(
        self, 
        controller_manager: ControllerManager = None,
        theme_manager: ThemeManager = None,
        translation_manager: TranslationManager = None
    ):
        """
        Initialise la fenêtre principale.
        
        Args:
            controller_manager: Gestionnaire de contrôleurs
            theme_manager: Gestionnaire de thèmes
            translation_manager: Gestionnaire de traductions
        """
        super().__init__()
        
        # Initialisation
        self.logger = Logger()
        self.controller_manager = controller_manager or ControllerManager()
        
        # Gestionnaires de thème et de traduction
        self.theme_manager = theme_manager or self.controller_manager.theme_manager
        self.translation_manager = translation_manager or self.controller_manager.translation_manager
        
        # Contrôleurs
        self.dataset_controller = self.controller_manager.dataset_controller
        self.import_controller = self.controller_manager.import_controller
        self.export_controller = self.controller_manager.export_controller
        self.api_controller = self.controller_manager.api_controller
        
        # Configuration de la fenêtre
        config = self.controller_manager.config_manager.get_config()
        self.setWindowTitle(tr("MainWindow.title", "YOLO Dataset Manager"))
        self.resize(config.ui.window_width, config.ui.window_height)
        
        # Création de l'interface
        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()
        
        # Ajouter une méthode de retranslation
        self.retranslate_ui()
        
        self.logger.info("Interface principale initialisée")
        
    def retranslate_ui(self):
        """
        Retraduit tous les éléments statiques de l'interface.
        Cette méthode est appelée lors des changements de langue.
        """
        # Titre de la fenêtre
        self.setWindowTitle(tr("MainWindow.title", "YOLO Dataset Manager"))
        
        # Mise à jour des menus
        self._create_menu_bar()  # Recréer le menu avec les nouvelles traductions
        

    def _create_menu_bar(self):
        """Crée la barre de menu."""
        # Supprimer la barre de menu existante si elle existe
        old_menubar = self.menuBar()
        if old_menubar:
            old_menubar.clear()
        
        menubar = self.menuBar()
        
        # Menu Fichier
        file_menu = menubar.addMenu(tr("MainWindow.file_menu", "&Fichier"))
        
        # Actions du menu Fichier
        new_dataset_action = file_menu.addAction(tr("MainWindow.new_dataset", "&Nouveau Dataset..."))
        new_dataset_action.triggered.connect(self._on_new_dataset)
        
        open_dataset_action = file_menu.addAction(tr("MainWindow.open_dataset", "&Ouvrir Dataset..."))
        open_dataset_action.triggered.connect(self._on_open_dataset)
        
        # Sous-menu Import
        import_menu = file_menu.addMenu(tr("MainWindow.import_menu", "&Importer"))
        import_mapillary_action = import_menu.addAction(tr("MainWindow.import_mapillary", "Depuis &Mapillary..."))
        import_mapillary_action.triggered.connect(self._on_import_mapillary)
        import_local_action = import_menu.addAction(tr("MainWindow.import_local", "Depuis des fichiers &locaux..."))
        import_local_action.triggered.connect(self._on_import_local)
        
        # Sous-menu Export
        export_menu = file_menu.addMenu(tr("MainWindow.export_menu", "&Exporter"))
        export_yolo_action = export_menu.addAction(tr("MainWindow.export_yolo", "Format &YOLO"))
        export_yolo_action.triggered.connect(lambda: self._on_export("yolo"))
        export_coco_action = export_menu.addAction(tr("MainWindow.export_coco", "Format &COCO"))
        export_coco_action.triggered.connect(lambda: self._on_export("coco"))
        export_voc_action = export_menu.addAction(tr("MainWindow.export_voc", "Format &VOC"))
        export_voc_action.triggered.connect(lambda: self._on_export("voc"))
        
        file_menu.addSeparator()
        
        preferences_action = file_menu.addAction(tr("Dialogs.preferences_title", "&Préférences..."))
        preferences_action.triggered.connect(self._on_preferences)
        
        file_menu.addSeparator()
        
        quit_action = file_menu.addAction(tr("Dialogs.cancel", "&Quitter"))
        quit_action.triggered.connect(self.close)
        
        # Menu Edit
        edit_menu = menubar.addMenu(tr("MainWindow.edit_menu", "&Édition"))
        
        validate_action = edit_menu.addAction(tr("MainWindow.validate_dataset", "&Valider Dataset"))
        validate_action.triggered.connect(self._on_validate_dataset)
        
        # Menu View
        view_menu = menubar.addMenu(tr("MainWindow.view_menu", "&Affichage"))
        
        # Actions du menu View
        show_toolbar_action = view_menu.addAction(tr("MainWindow.show_toolbar", "Afficher la barre d'&outils"))
        show_toolbar_action.setCheckable(True)
        show_toolbar_action.setChecked(True)
        
        show_statusbar_action = view_menu.addAction(tr("MainWindow.show_statusbar", "Afficher la barre d'&état"))
        show_statusbar_action.setCheckable(True)
        show_statusbar_action.setChecked(True)
        
        # Menu Tools
        tools_menu = menubar.addMenu(tr("MainWindow.tools_menu", "&Outils"))
        
        config_action = tools_menu.addAction(tr("MainWindow.configuration", "&Configuration..."))
        config_action.triggered.connect(self._on_configuration)
        
        # Menu Help
        help_menu = menubar.addMenu(tr("MainWindow.help_menu", "&Aide"))
        
        about_action = help_menu.addAction(tr("MainWindow.about", "À &propos"))
        about_action.triggered.connect(self._on_about)
        
    def _create_central_widget(self):
        """Crée le widget central."""
        # Créer et configurer la vue de dataset
        self.dataset_view = DatasetView()
        self.dataset_view.dataset_modified.connect(self._on_dataset_modified)
        
        # Définir comme widget central
        self.setCentralWidget(self.dataset_view)
        
    def _create_status_bar(self):
        """Crée la barre de statut."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage("Prêt")
        
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
                    self.statusBar().showMessage(f"Dataset créé: {dataset.name}")
            except Exception as e:
                self.logger.error(f"Échec de la création du dataset: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Échec de la création du dataset: {str(e)}"
                )
                
    def _on_open_dataset(self):
        """Gère l'ouverture d'un dataset existant."""
        try:
            # Récupérer la configuration
            config = self.controller_manager.config_manager.get_config()
            
            # Sélectionner le fichier de configuration du dataset
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Ouvrir Dataset",
                str(config.storage.dataset_dir),
                "Configuration Dataset (*.json);;Tous les fichiers (*)"
            )
            
            if file_path:
                # Extraire le nom du dataset à partir du fichier
                config_path = Path(file_path)
                dataset_name = config_path.stem
                if dataset_name.endswith("_config"):
                    dataset_name = dataset_name[:-7]  # Supprimer "_config" du nom
                    
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
        dialog = PreferencesDialog(
            config_manager=self.controller_manager.config_manager, 
            parent=self,
            theme_manager=self.theme_manager,
            translation_manager=self.translation_manager
        )
        if dialog.exec():
            # Recharger la configuration et réinitialiser les contrôleurs
            self.controller_manager.config_manager = ConfigManager()
            self.controller_manager.reset_controllers()
            
            # Réassigner les contrôleurs
            self.dataset_controller = self.controller_manager.dataset_controller
            self.import_controller = self.controller_manager.import_controller
            self.export_controller = self.controller_manager.export_controller
            self.api_controller = self.controller_manager.api_controller
            
            # Retraduite l'interface
            self.retranslate_ui()
            
            self.statusBar().showMessage(tr("Messages.preferences_success", "Préférences mises à jour"), 3000)
    
            
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
        dialog = ConfigDialog(
            config_manager=self.controller_manager.config_manager, 
            parent=self,
            theme_manager=self.theme_manager,
            translation_manager=self.translation_manager
        )
        if dialog.exec():
            # Recharger la configuration si nécessaire
            self.controller_manager.config_manager = ConfigManager()
            self.controller_manager.reset_controllers()
            
            # Réassigner les contrôleurs
            self.dataset_controller = self.controller_manager.dataset_controller
            self.import_controller = self.controller_manager.import_controller
            self.export_controller = self.controller_manager.export_controller
            self.api_controller = self.controller_manager.api_controller
            
            # Retraduite l'interface
            self.retranslate_ui()
            
            self.statusBar().showMessage(tr("Messages.configuration_success", "Configuration mise à jour"), 3000)
    
            
    def _on_about(self):
        """Affiche la boîte de dialogue À propos."""
        QMessageBox.about(
            self,
            tr("MainWindow.about_title", "À propos de YOLO Dataset Manager"),
            tr("MainWindow.about_text", 
               "YOLO Dataset Manager\n\n"
               "Un outil pour gérer et préparer des datasets pour l'entraînement YOLO.\n\n"
               "Version: 1.0.0")
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
    
    def changeEvent(self, event):
        """
        Gère les événements de changement.
        Utile pour intercepter les changements de langue et de thème.
        """
        if event.type() == QEvent.Type.LanguageChange:
            # Retraduite l'interface
            self.retranslate_ui()
        
        super().changeEvent(event)