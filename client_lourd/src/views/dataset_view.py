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
        
        add_images_btn = QPushButton("Ajouter des images")
        add_images_btn.clicked.connect(self._on_add_images)
        
        export_btn = QPushButton("Exporter")
        export_btn.clicked.connect(self._on_export)
        
        validate_btn = QPushButton("Valider")
        validate_btn.clicked.connect(self._on_validate)
        
        toolbar.addWidget(add_images_btn)
        toolbar.addWidget(export_btn)
        toolbar.addWidget(validate_btn)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panneau gauche (liste des images)
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # Panneau central (visualisation)
        center_panel = self._create_center_panel()
        splitter.addWidget(center_panel)
        
        # Panneau droit (métadonnées et annotations)
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        # Définir les proportions du splitter
        splitter.setSizes([200, 600, 200])
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
        stats_group = QGroupBox("Statistiques")
        stats_layout = QVBoxLayout(stats_group)
        
        self.total_images_label = QLabel("Total Images: 0")
        self.total_annotations_label = QLabel("Total Annotations: 0")
        self.classes_label = QLabel("Classes: 0")
        
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
        panel = QGroupBox("Visualisation")
        panel_layout = QVBoxLayout(panel)
        
        # Viewer d'image
        self.image_viewer = ImageViewer()
        self.image_viewer.image_loaded.connect(self._on_image_loaded)
        self.image_viewer.annotation_selected.connect(self._on_viewer_annotation_selected)
        panel_layout.addWidget(self.image_viewer)
        
        return panel
        
    def _create_right_panel(self) -> QGroupBox:
        """
        Crée le panneau droit avec les métadonnées et annotations.
        
        Returns:
            Widget du panneau droit
        """
        panel = QGroupBox("Détails")
        panel_layout = QVBoxLayout(panel)
        
        # Métadonnées de l'image
        metadata_group = QGroupBox("Métadonnées")
        metadata_layout = QVBoxLayout(metadata_group)
        
        self.image_info_label = QLabel()
        self.image_info_label.setTextFormat(Qt.TextFormat.RichText)
        self.image_info_label.setWordWrap(True)
        metadata_layout.addWidget(self.image_info_label)
        
        panel_layout.addWidget(metadata_group)
        
        # Liste des annotations
        annotations_group = QGroupBox("Annotations")
        annotations_layout = QVBoxLayout(annotations_group)
        
        self.annotation_list = QListWidget()
        self.annotation_list.itemSelectionChanged.connect(self._on_annotation_list_selected)
        self.annotation_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.annotation_list.customContextMenuRequested.connect(self._on_annotation_context_menu)
        annotations_layout.addWidget(self.annotation_list)
        
        # Boutons d'édition des annotations
        annotation_buttons = QHBoxLayout()
        
        edit_annotation_btn = QPushButton("Éditer")
        edit_annotation_btn.clicked.connect(self._on_edit_annotation)
        
        delete_annotation_btn = QPushButton("Supprimer")
        delete_annotation_btn.clicked.connect(self._on_delete_annotation)
        
        annotation_buttons.addWidget(edit_annotation_btn)
        annotation_buttons.addWidget(delete_annotation_btn)
        
        annotations_layout.addLayout(annotation_buttons)
        panel_layout.addWidget(annotations_group)
        
        return panel
        
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
                item.setText(image.path.name)
                item.setData(Qt.ItemDataRole.UserRole, image)
                
                # Essayer de charger la miniature
                try:
                    pixmap = QPixmap(str(image.path))
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(
                            64, 64,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        item.setIcon(QIcon(scaled_pixmap))
                    else:
                        self.logger.warning(f"Échec du chargement du pixmap pour {image.path}")
                except Exception as e:
                    self.logger.warning(f"Échec de la création de miniature pour {image.path}: {e}")
                
                self.image_list.addItem(item)
            except Exception as e:
                self.logger.error(f"Erreur lors de l'ajout de l'image {image.path} à la liste: {e}")
        
        # Mettre à jour les statistiques
        stats = self.dataset_controller.get_dataset_statistics(self.dataset)
        if stats:
            self.total_images_label.setText(f"Total Images: {stats['total_images']}")
            self.total_annotations_label.setText(f"Total Annotations: {stats['total_annotations']}")
            self.classes_label.setText(f"Classes: {len(self.dataset.classes)}")
        
        self.logger.debug("Mise à jour de l'UI terminée")
        
    def _on_image_selected(self):
        """Gère la sélection d'une image dans la liste."""
        items = self.image_list.selectedItems()
        if not items:
            return
            
        # Récupérer l'image sélectionnée
        image = items[0].data(Qt.ItemDataRole.UserRole)
        if image != self.current_image:
            self.current_image = image
            
            # Charger l'image dans le viewer
            self.image_viewer.load_image(image)
            
            # Mettre à jour les métadonnées
            self._update_metadata()
            
            # Mettre à jour la liste des annotations
            self._update_annotations()
            
            # Émettre le signal d'image sélectionnée
            self.image_selected.emit(image)
            
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
            
        # Formater les métadonnées en HTML pour une meilleure présentation
        metadata_html = f"""
        <b>Fichier:</b> {self.current_image.path.name}<br>
        <b>Dimensions:</b> {self.current_image.width} × {self.current_image.height}<br>
        <b>Source:</b> {self.current_image.source.value}<br>
        <b>Créé le:</b> {self.current_image.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        if self.current_image.modified_at:
            metadata_html += f"<br><b>Modifié le:</b> {self.current_image.modified_at.strftime('%Y-%m-%d %H:%M:%S')}"
            
        # Ajouter d'autres métadonnées si disponibles
        if self.current_image.metadata:
            metadata_html += "<br><br><b>Métadonnées supplémentaires:</b><br>"
            for key, value in self.current_image.metadata.items():
                metadata_html += f"<b>{key}:</b> {value}<br>"
            
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
        edit_action = menu.addAction("Éditer les annotations")
        delete_action = menu.addAction("Supprimer l'image")
        
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
        edit_action = menu.addAction("Éditer")
        delete_action = menu.addAction("Supprimer")
        
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
        """Gère l'export du dataset."""
        if not self.dataset:
            self.show_warning("Attention", "Aucun dataset chargé")
            return
            
        try:
            # Demander le format d'export
            formats = {
                "YOLO": "yolo",
                "COCO": "coco",
                "VOC": "voc"
            }
            
            format_menu = QMenu()
            for name, format_id in formats.items():
                format_menu.addAction(name).setData(format_id)
            
            # Positionner le menu sous le bouton "Exporter"
            action = format_menu.exec(self.sender().mapToGlobal(
                QPoint(0, self.sender().height())
            ))
            
            if not action:
                return
                
            format_id = action.data()
            
            # Sélectionner le répertoire de sortie
            export_dir = QFileDialog.getExistingDirectory(
                self,
                "Sélectionner le répertoire d'export",
                str(Path.home()),
                QFileDialog.Option.ShowDirsOnly
            )
            
            if not export_dir:
                return
                
            # Exporter le dataset via le contrôleur
            export_path = self.export_controller.export_dataset(
                dataset=self.dataset,
                export_format=format_id,
                output_path=Path(export_dir)
            )
            
            self.show_info(
                "Export terminé",
                f"Dataset exporté au format {format_id.upper()} vers:\n{export_path}"
            )
            
        except Exception as e:
            self.logger.error(f"Échec de l'export: {str(e)}")
            self.show_error(
                "Erreur",
                f"Échec de l'export du dataset: {str(e)}"
            )
            
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