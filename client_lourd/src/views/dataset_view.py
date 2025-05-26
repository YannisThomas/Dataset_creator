# src/views/dataset_view.py

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QGroupBox,
    QScrollArea,
    QMenu
)
from typing import Any
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QIcon
from pathlib import Path
from typing import Optional, List, Dict

from src.views.base_view import BaseView
from src.models import Dataset, Image
from src.controllers.controller_manager import ControllerManager
from src.views.components.image_viewer import ImageViewer
from src.views.components.annotation_editor import AnnotationEditor
from src.views.dialogs.metadata_dialog import MetadataDetailsDialog
from src.views.dialogs.export_dialog import ExportDialog
from src.utils.i18n import get_translation_manager, tr

class DatasetView(BaseView):
    """
    Vue principale pour l'affichage et l'édition d'un dataset.
    
    Cette vue permet de:
    - Visualiser et naviguer dans les images du dataset
    - Modifier les annotations des images
    - Effectuer des opérations sur le dataset
    """
    
    # Signaux spécifiques à cette vue
    dataset_loaded = pyqtSignal(Dataset)  # Émis quand un dataset est chargé
    dataset_modified = pyqtSignal(Dataset)  # Émis quand le dataset est modifié
    image_selected = pyqtSignal(Image)  # Émis quand une image est sélectionnée
    annotation_selected = pyqtSignal(int)  # Émis quand une annotation est sélectionnée
    
    def __init__(
        self, 
        parent=None, 
        controller_manager: Optional[ControllerManager] = None
    ):
        """
        Initialise la vue du dataset.
        
        Args:
            parent: Widget parent
            controller_manager: Gestionnaire de contrôleurs
        """
        super().__init__(parent, controller_manager)
        
        # État
        self.dataset: Optional[Dataset] = None
        self.current_image: Optional[Image] = None
        
        # Initialiser l'interface
        self._init_ui()
        
    def _init_ui(self):
        """Initialise l'interface utilisateur."""
        # Utiliser le layout de base
        layout = self.base_layout
        
        # Barre d'outils principale
        toolbar = QHBoxLayout()
        
        self.add_images_btn = QPushButton(tr("view.dataset.add_images"))
        self.add_images_btn.clicked.connect(self._on_add_images)
        
        self.export_btn = QPushButton(tr("view.dataset.export"))
        self.export_btn.clicked.connect(self._on_export)
        
        self.validate_btn = QPushButton(tr("view.dataset.validate"))
        self.validate_btn.clicked.connect(self._on_validate)
        
        self.save_btn = QPushButton(tr("view.dataset.save"))
        self.save_btn.clicked.connect(self._on_save)
        
        toolbar.addWidget(self.add_images_btn)
        toolbar.addWidget(self.export_btn)
        toolbar.addWidget(self.validate_btn)
        toolbar.addWidget(self.save_btn)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panneau gauche (liste des images)
        left_panel = self._create_left_panel()
        left_panel.setMinimumWidth(200)
        left_panel.setMaximumWidth(300)
        splitter.addWidget(left_panel)
        
        # Panneau central (visualisation)
        center_panel = self._create_center_panel()
        center_panel.setMinimumWidth(400)
        splitter.addWidget(center_panel)
        
        # Panneau droit (métadonnées et annotations)
        right_panel = self._create_right_panel()
        right_panel.setMinimumWidth(200)
        right_panel.setMaximumWidth(300)
        splitter.addWidget(right_panel)
        
        # Définir les proportions du splitter
        # Les valeurs représentent les pixels pour chaque section (gauche, centre, droite)
        splitter.setSizes([250, 600, 250])
        
        # Définir le stretch factor pour chaque panneau
        # 1 pour les panneaux latéraux, 3 pour le panneau central
        splitter.setStretchFactor(0, 1)  # Panneau gauche
        splitter.setStretchFactor(1, 3)  # Panneau central - plus de stretch
        splitter.setStretchFactor(2, 1)  # Panneau droit
        
        layout.addWidget(splitter)
        
        # Ajouter la barre de progression en bas
        layout.addWidget(self.progress_bar)
        
    def _create_left_panel(self) -> QGroupBox:
        """
        Crée le panneau gauche avec la liste des images.
        
        Returns:
            Widget du panneau gauche
        """
        panel = QGroupBox("Images")
        panel_layout = QVBoxLayout(panel)
        
        # Liste des images
        self.image_list = QListWidget()
        self.image_list.setIconSize(QSize(64, 64))
        self.image_list.itemSelectionChanged.connect(self._on_image_selected)
        self.image_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.image_list.customContextMenuRequested.connect(self._on_image_context_menu)
        panel_layout.addWidget(self.image_list)
        
        # Statistiques des images
        stats_group = QGroupBox(tr("view.dataset.statistics"))
        stats_layout = QVBoxLayout(stats_group)
        
        self.total_images_label = QLabel(tr("view.dataset.total_images", "0"))
        self.total_annotations_label = QLabel(tr("view.dataset.total_annotations", "0"))
        self.classes_label = QLabel(tr("view.dataset.classes", "0"))
        
        stats_layout.addWidget(self.total_images_label)
        stats_layout.addWidget(self.total_annotations_label)
        stats_layout.addWidget(self.classes_label)
        
        panel_layout.addWidget(stats_group)
        
        return panel
        
    def _create_center_panel(self) -> QGroupBox:
        """
        Crée le panneau central avec la visualisation de l'image.
        
        Returns:
            Widget du panneau central
        """
        panel = QGroupBox(tr("view.dataset.visualization"))
        panel_layout = QVBoxLayout(panel)
        
        # Viewer d'image
        self.image_viewer = ImageViewer()
        self.image_viewer.image_loaded.connect(self._on_image_loaded)
        self.image_viewer.annotation_selected.connect(self._on_viewer_annotation_selected)
        self.image_viewer.annotation_created.connect(self._on_annotation_created)
        self.image_viewer.annotation_modified.connect(self._on_annotation_modified)
        panel_layout.addWidget(self.image_viewer)
        
        # Barre d'outils d'édition
        edit_toolbar = QHBoxLayout()
        
        view_mode_btn = QPushButton(tr("view.dataset.view_mode"))
        view_mode_btn.clicked.connect(self.image_viewer.view_mode)
        
        create_mode_btn = QPushButton(tr("view.dataset.create_mode"))
        create_mode_btn.clicked.connect(self.image_viewer.create_annotation_mode)
        
        edit_mode_btn = QPushButton(tr("view.dataset.edit_mode"))
        edit_mode_btn.clicked.connect(self.image_viewer.edit_annotation_mode)
        
        edit_toolbar.addWidget(view_mode_btn)
        edit_toolbar.addWidget(create_mode_btn)
        edit_toolbar.addWidget(edit_mode_btn)
        
        panel_layout.addLayout(edit_toolbar)
        
        return panel
        
    def _create_right_panel(self) -> QGroupBox:
        """
        Crée le panneau droit avec les métadonnées et annotations.
        
        Returns:
            Widget du panneau droit
        """
        panel = QGroupBox(tr("view.dataset.details"))
        panel_layout = QVBoxLayout(panel)
        
        # Métadonnées de l'image
        metadata_group = QGroupBox(tr("view.dataset.metadata"))
        metadata_layout = QVBoxLayout(metadata_group)
        
        self.image_info_label = QLabel()
        self.image_info_label.setTextFormat(Qt.TextFormat.RichText)
        self.image_info_label.setWordWrap(True)
        metadata_layout.addWidget(self.image_info_label)
        
        # Ajouter un bouton pour voir les métadonnées complètes
        view_metadata_btn = QPushButton(tr("view.dataset.view_metadata"))
        view_metadata_btn.clicked.connect(self._on_view_metadata)
        metadata_layout.addWidget(view_metadata_btn)
        
        metadata_group.setLayout(metadata_layout)
        panel_layout.addWidget(metadata_group)
        
        # Liste des annotations
        annotations_group = QGroupBox(tr("view.dataset.annotations"))
        annotations_layout = QVBoxLayout(annotations_group)
        
        self.annotation_list = QListWidget()
        self.annotation_list.itemSelectionChanged.connect(self._on_annotation_list_selected)
        self.annotation_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.annotation_list.customContextMenuRequested.connect(self._on_annotation_context_menu)
        annotations_layout.addWidget(self.annotation_list)
        
        # Boutons d'édition des annotations
        annotation_buttons = QHBoxLayout()
        
        edit_annotation_btn = QPushButton(tr("view.dataset.edit_mode"))
        edit_annotation_btn.clicked.connect(self._on_edit_annotation)
        
        delete_annotation_btn = QPushButton(tr("view.dataset.delete_annotation"))
        delete_annotation_btn.clicked.connect(self._on_delete_annotation)
        
        annotation_buttons.addWidget(edit_annotation_btn)
        annotation_buttons.addWidget(delete_annotation_btn)
        
        annotations_layout.addLayout(annotation_buttons)
        annotations_group.setLayout(annotations_layout)
        panel_layout.addWidget(annotations_group)
        
        return panel
    
    def _on_view_metadata(self):
        """Affiche le dialogue des métadonnées complètes."""
        if not self.current_image:
            return
            
        dialog = MetadataDetailsDialog(self.current_image, self)
        dialog.exec()
        
    def set_dataset(self, dataset: Dataset):
        """
        Définit le dataset à afficher.
        
        Args:
            dataset: Dataset à afficher
        """
        self.dataset = dataset
        self._update_ui()
        self.dataset_loaded.emit(dataset)
        
    def get_dataset(self) -> Optional[Dataset]:
        """
        Récupère le dataset actuel.
        
        Returns:
            Dataset actuel ou None
        """
        return self.dataset
        
    def _update_ui(self):
        """Met à jour l'interface avec les données du dataset."""
        if not self.dataset:
            self.logger.debug("Aucun dataset chargé, pas de mise à jour de l'UI")
            return
            
        # Vider et recharger la liste des images
        self.image_list.clear()
        self.logger.debug(f"Mise à jour de l'UI avec {len(self.dataset.images)} images")
        
        for i, image in enumerate(self.dataset.images):
            try:
                self.logger.debug(f"Ajout de l'image {i}: {image.path}")
                item = QListWidgetItem()
                
                # Gérer correctement le chemin et le nom de fichier
                if isinstance(image.path, Path):
                    file_name = image.path.name
                    path_str = str(image.path)
                else:
                    # Si c'est une chaîne, la traiter correctement
                    path_str = str(image.path)
                    
                    # Corriger les chemins problématiques
                    if path_str.startswith(('http://', 'https://')):
                        # Extraire la partie locale du chemin
                        local_part = path_str.split('://')[-1]
                        
                        # Vérifier si le chemin local existe
                        local_path = Path(local_part)
                        if local_path.exists():
                            path_str = str(local_path)
                            file_name = local_path.name
                        else:
                            # Essayer d'autres chemins possibles
                            filename = local_path.name
                            
                            potential_paths = [
                                Path("data/datasets") / self.dataset.name / "images" / filename,
                                Path(self.dataset.path) / "images" / filename,
                                Path("data/downloads") / filename,
                                Path("downloads") / filename
                            ]
                            
                            for potential_path in potential_paths:
                                if potential_path.exists():
                                    path_str = str(potential_path)
                                    file_name = filename
                                    break
                            else:
                                # Si aucun chemin local n'est trouvé, utiliser le nom de fichier seul
                                file_name = filename
                    else:
                        # Chemin normal, extraire le nom
                        try:
                            file_name = Path(path_str).name
                        except:
                            file_name = path_str.split("/")[-1]
                
                item.setText(file_name)
                item.setData(Qt.ItemDataRole.UserRole, image)
                
                # Essayer de charger la miniature
                try:
                    # Vérifier si le fichier existe localement
                    if Path(path_str).exists():
                        pixmap = QPixmap(path_str)
                        if not pixmap.isNull():
                            scaled_pixmap = pixmap.scaled(
                                64, 64,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation
                            )
                            item.setIcon(QIcon(scaled_pixmap))
                        else:
                            self.logger.warning(f"Échec du chargement du pixmap pour {path_str}")
                    else:
                        self.logger.warning(f"Fichier non trouvé pour la miniature: {path_str}")
                except Exception as e:
                    self.logger.warning(f"Échec de la création de miniature pour {path_str}: {e}")
                
                self.image_list.addItem(item)
            except Exception as e:
                self.logger.error(f"Erreur lors de l'ajout de l'image {getattr(image, 'path', 'N/A')} à la liste: {e}")
        
        # Mettre à jour les statistiques
        try:
            stats = self.dataset_controller.get_dataset_statistics(self.dataset)
            if stats:
                self.total_images_label.setText(tr("view.dataset.total_images", stats["total_images"]))
                self.total_annotations_label.setText(tr("view.dataset.total_annotations", stats["total_annotations"]))
                self.classes_label.setText(f"Classes: {len(self.dataset.classes)}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour des statistiques: {e}")
            # Utiliser des statistiques basiques
            self.total_images_label.setText(f"Total Images: {len(self.dataset.images)}")
            self.total_annotations_label.setText("Total Annotations: N/A")
            self.classes_label.setText(f"Classes: {len(self.dataset.classes)}")
        
        self.logger.debug("Mise à jour de l'UI terminée")

    def _on_image_selected(self):
        """Gère la sélection d'une image dans la liste."""
        items = self.image_list.selectedItems()
        if not items:
            return
            
        try:
            # Récupérer l'image sélectionnée
            image = items[0].data(Qt.ItemDataRole.UserRole)
            
            if image != self.current_image:
                self.current_image = image
                
                # Debug logging pour faciliter la résolution de problèmes
                self.logger.debug(f"Image sélectionnée: {image.id}, path type: {type(image.path)}, path: {image.path}")
                
                # S'assurer que le chemin est correct avant de charger l'image
                path_str = str(image.path)
                
                # Correction des chemins problématiques
                if path_str.startswith(('http://', 'https://')):
                    # Extraire la partie locale du chemin
                    local_part = path_str.split('://')[-1]
                    local_path = Path(local_part)
                    
                    # Vérifier si le chemin local existe
                    if local_path.exists():
                        image.path = local_path
                        self.logger.debug(f"Chemin corrigé: {path_str} -> {local_path}")
                    else:
                        # Essayer d'autres chemins possibles
                        filename = local_path.name
                        
                        potential_paths = [
                            Path("data/datasets") / self.dataset.name / "images" / filename,
                            Path(self.dataset.path) / "images" / filename,
                            Path("data/downloads") / filename,
                            Path("downloads") / filename
                        ]
                        
                        for potential_path in potential_paths:
                            if potential_path.exists():
                                image.path = potential_path
                                self.logger.debug(f"Chemin alternatif trouvé: {path_str} -> {potential_path}")
                                break
                
                # Charger l'image dans le viewer
                try:
                    success = self.image_viewer.load_image(image)
                    if not success:
                        self.show_error(
                            "Erreur",
                            f"Échec du chargement de l'image: {image.path}"
                        )
                except Exception as e:
                    self.logger.error(f"Erreur lors du chargement de l'image dans le viewer: {str(e)}")
                    self.show_error(
                        "Erreur",
                        f"Impossible de charger l'image: {str(e)}"
                    )
                
                # Mettre à jour les métadonnées
                self._update_metadata()
                
                # Mettre à jour la liste des annotations
                self._update_annotations()
                
                # Émettre le signal d'image sélectionnée
                self.image_selected.emit(image)
        except Exception as e:
            self.logger.error(f"Erreur lors de la sélection de l'image: {str(e)}")
            self.show_error(
                "Erreur",
                f"Impossible de sélectionner l'image: {str(e)}"
            )
            
    def _on_viewer_annotation_selected(self, index: int):
        """
        Gère la sélection d'une annotation dans le viewer.
        
        Args:
            index: Index de l'annotation sélectionnée
        """
        if 0 <= index < self.annotation_list.count():
            self.annotation_list.setCurrentRow(index)
            self.annotation_selected.emit(index)
            
    def _on_annotation_list_selected(self):
        """Gère la sélection d'une annotation dans la liste."""
        items = self.annotation_list.selectedItems()
        if items:
            index = self.annotation_list.row(items[0])
            self.image_viewer.select_annotation(index)
            self.annotation_selected.emit(index)
            
    def _update_metadata(self):
        """Met à jour l'affichage des métadonnées."""
        if not self.current_image:
            self.image_info_label.setText("")
            return
            
        # Obtenir le nom de fichier de manière sécurisée
        try:
            if isinstance(self.current_image.path, Path):
                filename = self.current_image.path.name
            else:
                path_str = str(self.current_image.path)
                if path_str.startswith(('http://', 'https://')):
                    # Extraire le nom de fichier de l'URL
                    filename = Path(path_str.split('://')[-1]).name
                else:
                    filename = Path(path_str).name
        except:
            filename = str(self.current_image.path)
        
        # Formater les métadonnées en HTML pour une meilleure présentation
        metadata_html = f"""
        <b>Fichier:</b> {filename}<br>
        <b>Dimensions:</b> {self.current_image.width} × {self.current_image.height}<br>
        <b>Source:</b> {self.current_image.source.value}<br>
        <b>Créé le:</b> {self.current_image.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        if self.current_image.modified_at:
            metadata_html += f"<br><b>Modifié le:</b> {self.current_image.modified_at.strftime('%Y-%m-%d %H:%M:%S')}"
            
        # Ajouter d'autres métadonnées si disponibles, mais de façon limitée
        if self.current_image.metadata:
            metadata_html += "<br><br><b>Métadonnées:</b><br>"
            
            # Limiter le nombre de métadonnées affichées
            important_keys = ['coordinates', 'camera_make', 'camera_model', 'captured_at', 'compass_angle']
            count = 0
            
            # D'abord afficher les clés importantes
            for key in important_keys:
                if key in self.current_image.metadata:
                    value = self.current_image.metadata[key]
                    # Si c'est un dictionnaire, afficher de manière concise
                    if isinstance(value, dict):
                        # Pour les coordonnées, formater de manière spéciale
                        if key == 'coordinates':
                            lat = value.get('latitude', 'N/A')
                            lon = value.get('longitude', 'N/A')
                            if isinstance(lat, (float, int)) and isinstance(lon, (float, int)):
                                metadata_html += f"<b>Position:</b> {lat:.5f}, {lon:.5f}<br>"
                            else:
                                metadata_html += f"<b>Position:</b> {lat}, {lon}<br>"
                        else:
                            # Limiter à 2-3 sous-clés importantes
                            value_str = ", ".join([f"{k}: {v}" for k, v in list(value.items())[:2]])
                            metadata_html += f"<b>{key}:</b> {value_str}<br>"
                    else:
                        metadata_html += f"<b>{key}:</b> {value}<br>"
                    count += 1
            
            # Ensuite, ajouter quelques autres métadonnées si nécessaire
            for key, value in self.current_image.metadata.items():
                if key not in important_keys and count < 5:  # Limiter à 5 métadonnées au total
                    if not isinstance(value, (dict, list)) or len(str(value)) < 50:
                        metadata_html += f"<b>{key}:</b> {value}<br>"
                        count += 1
            
            # Indiquer s'il y a plus de métadonnées non affichées
            remaining = len(self.current_image.metadata) - count
            if remaining > 0:
                metadata_html += f"<i>Et {remaining} autres métadonnées...</i>"
        
        self.image_info_label.setText(metadata_html)
            
    def _update_annotations(self):
        """Met à jour la liste des annotations."""
        self.annotation_list.clear()
        
        if not self.current_image:
            return
            
        for i, annotation in enumerate(self.current_image.annotations):
            item = QListWidgetItem()
            
            # Texte de l'annotation avec plus d'informations
            class_id = annotation.class_id
            class_name = self.dataset.classes.get(class_id, f"Classe {class_id}")
            
            # Format plus lisible
            bbox = annotation.bbox
            bbox_text = f"({bbox.x:.2f}, {bbox.y:.2f}, {bbox.width:.2f}, {bbox.height:.2f})"
            
            confidence_text = ""
            if hasattr(annotation, 'confidence') and annotation.confidence is not None:
                confidence_text = f" {annotation.confidence:.2f}"
                
            text = f"{i+1}: {class_name}{confidence_text} - {bbox_text}"
                
            item.setText(text)
            item.setData(Qt.ItemDataRole.UserRole, annotation)
            
            self.annotation_list.addItem(item)
            
    def _on_image_loaded(self, success: bool):
        """
        Gère le chargement d'une image.
        
        Args:
            success: True si le chargement a réussi
        """
        if not success:
            self.show_error(
                "Erreur",
                f"Échec du chargement de l'image: {self.current_image.path if self.current_image else 'Inconnue'}"
            )
            
    def _on_image_context_menu(self, position):
        """
        Affiche un menu contextuel pour les images.
        
        Args:
            position: Position du clic
        """
        if not self.image_list.selectedItems():
            return
            
        # Créer le menu
        menu = QMenu()
        edit_action = menu.addAction(tr("view.dataset.edit_annotations"))
        delete_action = menu.addAction(tr("view.dataset.delete_image"))
        
        # Exécuter le menu
        action = menu.exec(self.image_list.mapToGlobal(position))
        
        if action == edit_action:
            self._on_edit_annotation()
        elif action == delete_action:
            self._on_delete_image()
            
    def _on_annotation_context_menu(self, position):
        """
        Affiche un menu contextuel pour les annotations.
        
        Args:
            position: Position du clic
        """
        if not self.annotation_list.selectedItems():
            return
            
        # Créer le menu
        menu = QMenu()
        edit_action = menu.addAction(tr("view.dataset.edit_mode"))
        delete_action = menu.addAction(tr("view.dataset.delete_annotation"))
        
        # Exécuter le menu
        action = menu.exec(self.annotation_list.mapToGlobal(position))
        
        if action == edit_action:
            self._on_edit_annotation()
        elif action == delete_action:
            self._on_delete_annotation()
            
    def _on_add_images(self):
        """Gère l'ajout de nouvelles images."""
        if not self.dataset:
            self.show_warning("Attention", "Veuillez d'abord créer ou ouvrir un dataset")
            return
            
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner des images",
            str(Path.home()),
            "Images (*.jpg *.jpeg *.png);;Tous les fichiers (*)"
        )
        
        if files:
            self.show_progress(True, len(files))
            
            try:
                # Utiliser le contrôleur d'import
                imported_count = 0
                failed_count = 0
                
                for i, file_path in enumerate(files, 1):
                    try:
                        # Importer l'image
                        success = self.import_controller.import_image_to_dataset(
                            dataset=self.dataset,
                            image_path=file_path
                        )
                        
                        if success:
                            imported_count += 1
                        else:
                            failed_count += 1
                        
                        # Mettre à jour la progression
                        self.set_progress(i)
                        
                    except Exception as e:
                        self.logger.error(f"Échec de l'import du fichier {file_path}: {str(e)}")
                        failed_count += 1
                
                # Mettre à jour l'interface
                self._update_ui()
                
                # Marquer le dataset comme modifié
                self.mark_as_dirty()
                
                # Afficher un résumé
                self.show_info(
                    "Import terminé",
                    f"Importé {imported_count} images avec succès, {failed_count} échecs"
                )
                
            except Exception as e:
                self.logger.error(f"Erreur lors de l'import des images: {str(e)}")
                self.show_error(
                    "Erreur",
                    f"Échec de l'import des images: {str(e)}"
                )
            finally:
                self.show_progress(False)
                
    def _on_delete_image(self):
        """Supprime l'image sélectionnée."""
        items = self.image_list.selectedItems()
        if not items or not self.dataset:
            return
            
        image = items[0].data(Qt.ItemDataRole.UserRole)
        
        if not self.confirm_action(
            "Confirmer la suppression",
            f"Êtes-vous sûr de vouloir supprimer l'image {image.path.name}?"
        ):
            return
            
        try:
            # Supprimer l'image du dataset
            self.dataset.remove_image(image)
            
            # Mettre à jour l'interface
            self._update_ui()
            
            # Effacer l'image courante si c'était celle-ci
            if self.current_image == image:
                self.current_image = None
                self.image_viewer.clear_image()
                self.image_info_label.setText("")
                self.annotation_list.clear()
            
            # Marquer le dataset comme modifié
            self.mark_as_dirty()
            
            # Émettre le signal de modification du dataset
            self.dataset_modified.emit(self.dataset)
            
        except Exception as e:
            self.logger.error(f"Échec de la suppression de l'image: {str(e)}")
            self.show_error(
                "Erreur",
                f"Échec de la suppression de l'image: {str(e)}"
            )
            
    def _on_edit_annotation(self):
        """Ouvre l'éditeur d'annotations."""
        if not self.current_image or not self.dataset:
            return
            
        # Ouvrir l'éditeur d'annotations
        editor = AnnotationEditor(
            image=self.current_image,
            dataset=self.dataset,
            parent=self
        )
        
        # Si l'édition est acceptée
        if editor.exec():
            # Mettre à jour l'affichage
            self.image_viewer.set_annotations(self.current_image.annotations)
            self._update_annotations()
            
            # Marquer le dataset comme modifié
            self.mark_as_dirty()
            
            # Émettre le signal de modification du dataset
            self.dataset_modified.emit(self.dataset)
            
    def _on_delete_annotation(self):
        """Supprime l'annotation sélectionnée."""
        if not self.current_image:
            return
            
        items = self.annotation_list.selectedItems()
        if not items:
            return
            
        if not self.confirm_action(
            "Confirmer la suppression",
            "Êtes-vous sûr de vouloir supprimer cette annotation?"
        ):
            return
            
        try:
            index = self.annotation_list.row(items[0])
            if 0 <= index < len(self.current_image.annotations):
                del self.current_image.annotations[index]
                self._update_annotations()
                self.image_viewer.set_annotations(self.current_image.annotations)
                
                # Marquer le dataset comme modifié
                self.mark_as_dirty()
                
                # Émettre le signal de modification du dataset
                self.dataset_modified.emit(self.dataset)
                
        except Exception as e:
            self.logger.error(f"Échec de la suppression de l'annotation: {str(e)}")
            self.show_error(
                "Erreur",
                f"Échec de la suppression de l'annotation: {str(e)}"
            )
            
    def _on_export(self):
        """Gère l'export du dataset avec le dialogue avancé."""
        if not self.dataset:
            self.show_warning("Attention", "Aucun dataset chargé")
            return
            
        try:
            # Ouvrir le dialogue d'export avancé
            export_dialog = ExportDialog(
                dataset=self.dataset,
                parent=self,
                controller_manager=self.controller_manager
            )
            
            # Connecter le signal de fin d'export
            export_dialog.export_completed.connect(self._on_export_completed)
            
            # Afficher le dialogue
            export_dialog.exec()
            
        except Exception as e:
            self.logger.error(f"Échec de l'ouverture du dialogue d'export: {str(e)}")
            self.show_error(
                "Erreur",
                f"Échec de l'ouverture du dialogue d'export: {str(e)}"
            )
            
    def _on_export_completed(self, export_path: str):
        """
        Appelé quand l'export est terminé avec succès.
        
        Args:
            export_path: Chemin vers le dossier d'export
        """
        self.logger.info(f"Export terminé avec succès: {export_path}")
        # Le dialogue d'export gère déjà l'affichage du message de succès
            
    def _on_validate(self):
        """Valide le dataset actuel."""
        if not self.dataset:
            self.show_warning("Attention", "Aucun dataset chargé")
            return
            
        # Valider le dataset via le contrôleur
        validation = self.dataset_controller.validate_dataset(self.dataset)
        
        if validation["valid"]:
            self.show_info(
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
                    
            self.show_warning(
                "Validation",
                error_text
            )
    
    def _on_save(self):
        """Sauvegarde le dataset actuel."""
        if not self.dataset:
            self.show_warning("Attention", "Aucun dataset chargé")
            return
            
        try:
            # Sauvegarder le dataset via le contrôleur
            self.dataset_controller.save_dataset(self.dataset)
            
            # Marquer comme propre
            self.mark_as_dirty(False)
            
            self.show_info(
                "Sauvegarde",
                "Le dataset a été sauvegardé avec succès!"
            )
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde du dataset: {str(e)}")
            self.show_error(
                "Erreur",
                f"Échec de la sauvegarde du dataset: {str(e)}"
            )
    
    def save_changes(self) -> bool:
        """
        Sauvegarde les modifications du dataset.
        
        Returns:
            True si la sauvegarde a réussi
        """
        if not self.dataset:
            return True
            
        try:
            # Sauvegarder le dataset via le contrôleur
            self.dataset_controller.update_dataset(self.dataset)
            
            # Marquer comme propre
            self.mark_as_dirty(False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Échec de la sauvegarde du dataset: {str(e)}")
            self.show_error(
                "Erreur",
                f"Échec de la sauvegarde du dataset: {str(e)}"
            )
            return False
            
    def reload_data(self):
        """Recharge les données du dataset."""
        if not self.dataset:
            return
            
        try:
            # Recharger le dataset via le contrôleur
            dataset = self.dataset_controller.get_dataset(self.dataset.name)
            if dataset:
                self.set_dataset(dataset)
        except Exception as e:
            self.logger.error(f"Échec du rechargement du dataset: {str(e)}")
            self.show_error(
                "Erreur",
                f"Échec du rechargement du dataset: {str(e)}"
            )
            
    def reset_view(self):
        """Réinitialise la vue à son état par défaut."""
        self.dataset = None
        self.current_image = None
        self.image_list.clear()
        self.annotation_list.clear()
        self.image_info_label.setText("")
        self.image_viewer.clear_image()
        self.total_images_label.setText("Total Images: 0")
        self.total_annotations_label.setText("Total Annotations: 0")
        self.classes_label.setText("Classes: 0")
        self.mark_as_dirty(False)
        
    def capture_view_state(self) -> Dict[str, Any]:
        """
        Capture l'état actuel de la vue pour restauration ultérieure.
        
        Returns:
            Dictionnaire contenant l'état de la vue
        """
        state = {
            "dataset_name": self.dataset.name if self.dataset else None,
            "current_image_id": self.current_image.id if self.current_image else None,
        }
        return state
        
    def restore_view_state(self, state: Dict[str, Any]):
        """
        Restaure l'état de la vue à partir d'un état capturé.
        
        Args:
            state: État de la vue à restaurer
        """
        if not state:
            return
            
        try:
            # Restaurer le dataset
            dataset_name = state.get("dataset_name")
            if dataset_name:
                dataset = self.dataset_controller.get_dataset(dataset_name)
                if dataset:
                    self.set_dataset(dataset)
                    
                    # Restaurer l'image sélectionnée
                    current_image_id = state.get("current_image_id")
                    if current_image_id:
                        for i in range(self.image_list.count()):
                            item = self.image_list.item(i)
                            image = item.data(Qt.ItemDataRole.UserRole)
                            if image.id == current_image_id:
                                self.image_list.setCurrentItem(item)
                                break
        except Exception as e:
            self.logger.error(f"Échec de la restauration de l'état de la vue: {str(e)}")
            # Ne pas afficher d'erreur à l'utilisateur

    def _on_annotation_created(self, bbox):
        """
        Gère la création d'une annotation depuis le visualiseur.
        
        Args:
            bbox: BoundingBox de l'annotation
        """
        if not self.current_image:
            return
            
        # Créer une nouvelle annotation
        from src.models import Annotation
        from src.models.enums import AnnotationType
        
        annotation = Annotation(
            class_id=0,  # Classe par défaut
            bbox=bbox,
            confidence=1.0,
            type=AnnotationType.BBOX
        )
        
        # Ajouter l'annotation à l'image
        self.current_image.add_annotation(annotation)
        
        # Ouvrir l'éditeur pour spécifier la classe
        editor = AnnotationEditor(
            image=self.current_image,
            dataset=self.dataset,
            annotation=annotation,
            parent=self
        )
        
        if editor.exec():
            # Mettre à jour l'affichage
            self._update_annotations()
            self.image_viewer.set_annotations(self.current_image.annotations)
            
            # Marquer le dataset comme modifié
            self.mark_as_dirty()
            
            # Émettre le signal de modification du dataset
            self.dataset_modified.emit(self.dataset)
        else:
            # Supprimer l'annotation si annulée
            self.current_image.annotations.remove(annotation)

    def _on_annotation_modified(self, index, bbox):
        """
        Gère la modification d'une annotation depuis le visualiseur.
        
        Args:
            index: Index de l'annotation
            bbox: Nouveau rectangle
        """
        if not self.current_image or index < 0 or index >= len(self.current_image.annotations):
            return
        
        # L'annotation a déjà été mise à jour dans le visualiseur
        # Mettre à jour l'affichage des annotations
        self._update_annotations()
        
        # Marquer le dataset comme modifié
        self.mark_as_dirty()
        
        # Émettre le signal de modification du dataset
        self.dataset_modified.emit(self.dataset)
    def _on_language_changed(self, language_code: str):
        """Gestionnaire pour le changement de langue."""
        # Mettre à jour les boutons et labels
        if hasattr(self, 'add_images_btn'):
            self.add_images_btn.setText(tr("view.dataset.add_images"))
        if hasattr(self, 'export_btn'):
            self.export_btn.setText(tr("view.dataset.export"))
        if hasattr(self, 'validate_btn'):
            self.validate_btn.setText(tr("view.dataset.validate"))
        if hasattr(self, 'view_mode_btn'):
            self.view_mode_btn.setText(tr("view.dataset.view_mode"))
        if hasattr(self, 'create_mode_btn'):
            self.create_mode_btn.setText(tr("view.dataset.create_mode"))
        if hasattr(self, 'edit_mode_btn'):
            self.edit_mode_btn.setText(tr("view.dataset.edit_mode"))
        if hasattr(self, 'view_metadata_btn'):
            self.view_metadata_btn.setText(tr("view.dataset.view_metadata"))
        if hasattr(self, 'edit_annotation_btn'):
            self.edit_annotation_btn.setText(tr("view.dataset.edit_annotation"))
        if hasattr(self, 'delete_annotation_btn'):
            self.delete_annotation_btn.setText(tr("view.dataset.delete_annotation"))
        
        # Mettre à jour les statistiques si elles existent
        if hasattr(self, 'dataset') and self.dataset:
            self._update_stats()
