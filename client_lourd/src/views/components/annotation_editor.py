# src/views/components/annotation_editor.py

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QCheckBox,
    QSlider,
    QTabWidget,
    QWidget,
    QColorDialog,
    QToolButton,
    QMenu,
    QAction
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter, QTransform
from typing import Optional, Dict, List

from src.models import Image, Dataset, Annotation, BoundingBox
from src.models.enums import AnnotationType
from src.utils.logger import Logger

class EnhancedAnnotationEditor(QDialog):
    """
    Éditeur avancé pour la création/modification d'annotations.
    Ajoute des fonctionnalités de rotation, transformation, duplication, etc.
    """
    
    # Signaux
    annotation_edited = pyqtSignal(Annotation)  # Émis quand une annotation est modifiée
    annotation_added = pyqtSignal(Annotation)   # Émis quand une annotation est ajoutée
    
    def __init__(
        self, 
        image: Image,
        dataset: Dataset,
        annotation: Optional[Annotation] = None,
        parent=None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise l'éditeur d'annotations amélioré.
        
        Args:
            image: Image associée
            dataset: Dataset contenant les classes
            annotation: Annotation à modifier (None pour création)
            parent: Widget parent
            logger: Gestionnaire de logs
        """
        super().__init__(parent)
        
        self.image = image
        self.dataset = dataset
        self.original_annotation = annotation
        self.result_annotation = None
        self.logger = logger or Logger()
        
        # Déterminer si c'est une création ou une modification
        self.is_edit_mode = annotation is not None
        
        # État interne
        self.color = QColor(0, 255, 0)  # Couleur par défaut
        self.opacity = 60  # Opacité par défaut (0-100)
        self.highlight_similar = False  # Surligner des annotations similaires
        self.annotation_history = []  # Historique pour undo/redo
        self.history_position = -1  # Position actuelle dans l'historique
        
        # Configuration de la fenêtre
        title = "Modifier l'annotation" if self.is_edit_mode else "Créer une annotation"
        self.setWindowTitle(title)
        self.resize(600, 500)
        
        # Initialiser l'interface
        self._init_ui()
        
        # Si une annotation est fournie, remplir les champs
        if annotation:
            self._load_annotation(annotation)
            # Sauvegarder l'état initial dans l'historique
            self._save_to_history()
        
    def _init_ui(self):
        """Initialise l'interface utilisateur."""
        main_layout = QVBoxLayout(self)
        
        # Onglets principaux
        tabs = QTabWidget()
        
        # Onglet principal
        main_tab = QWidget()
        main_tab_layout = QVBoxLayout(main_tab)
        
        # Groupe Classes
        class_group = QGroupBox("Classe")
        class_layout = QFormLayout()
        
        # Liste déroulante des classes
        self.class_combo = QComboBox()
        for class_id, class_name in sorted(self.dataset.classes.items()):
            self.class_combo.addItem(class_name, class_id)
        
        class_layout.addRow("Classe:", self.class_combo)
        
        # Créer une nouvelle classe
        new_class_button = QToolButton()
        new_class_button.setText("+")
        new_class_button.setToolTip("Ajouter une nouvelle classe")
        new_class_button.clicked.connect(self._add_new_class)
        
        class_row_layout = QHBoxLayout()
        class_row_layout.addWidget(self.class_combo)
        class_row_layout.addWidget(new_class_button)
        
        class_layout.addRow("Classe:", class_row_layout)
        class_group.setLayout(class_layout)
        main_tab_layout.addWidget(class_group)
        
        # Groupe Bounding Box
        bbox_group = QGroupBox("Bounding Box")
        bbox_layout = QFormLayout()
        
        # Spinners pour les coordonnées
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(0.0, 1.0)
        self.x_spin.setDecimals(6)
        self.x_spin.setSingleStep(0.01)
        
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(0.0, 1.0)
        self.y_spin.setDecimals(6)
        self.y_spin.setSingleStep(0.01)
        
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.001, 1.0)
        self.width_spin.setDecimals(6)
        self.width_spin.setSingleStep(0.01)
        
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0.001, 1.0)
        self.height_spin.setDecimals(6)
        self.height_spin.setSingleStep(0.01)
        
        # Ajouter des labels avec les dimensions en pixels
        pixel_layout_x = QHBoxLayout()
        pixel_layout_x.addWidget(self.x_spin)
        self.x_pixel_label = QLabel("(0px)")
        pixel_layout_x.addWidget(self.x_pixel_label)
        
        pixel_layout_y = QHBoxLayout()
        pixel_layout_y.addWidget(self.y_spin)
        self.y_pixel_label = QLabel("(0px)")
        pixel_layout_y.addWidget(self.y_pixel_label)
        
        pixel_layout_w = QHBoxLayout()
        pixel_layout_w.addWidget(self.width_spin)
        self.width_pixel_label = QLabel("(0px)")
        pixel_layout_w.addWidget(self.width_pixel_label)
        
        pixel_layout_h = QHBoxLayout()
        pixel_layout_h.addWidget(self.height_spin)
        self.height_pixel_label = QLabel("(0px)")
        pixel_layout_h.addWidget(self.height_pixel_label)
        
        bbox_layout.addRow("X:", pixel_layout_x)
        bbox_layout.addRow("Y:", pixel_layout_y)
        bbox_layout.addRow("Largeur:", pixel_layout_w)
        bbox_layout.addRow("Hauteur:", pixel_layout_h)
        
        # Connecter les signaux pour mettre à jour les dimensions en pixels
        self.x_spin.valueChanged.connect(self._update_pixel_labels)
        self.y_spin.valueChanged.connect(self._update_pixel_labels)
        self.width_spin.valueChanged.connect(self._update_pixel_labels)
        self.height_spin.valueChanged.connect(self._update_pixel_labels)
        
        bbox_group.setLayout(bbox_layout)
        main_tab_layout.addWidget(bbox_group)
        
        # Groupe Confiance
        conf_group = QGroupBox("Confiance")
        conf_layout = QFormLayout()
        
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.0, 1.0)
        self.conf_spin.setDecimals(4)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(1.0)  # 100% par défaut
        
        # Slider pour la confiance
        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(0, 100)
        self.conf_slider.setValue(100)
        self.conf_slider.setTickInterval(10)
        self.conf_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        
        # Connecter les contrôles de confiance
        self.conf_spin.valueChanged.connect(lambda val: self.conf_slider.setValue(int(val * 100)))
        self.conf_slider.valueChanged.connect(lambda val: self.conf_spin.setValue(val / 100))
        
        conf_layout.addRow("Confiance:", self.conf_spin)
        conf_layout.addRow("", self.conf_slider)
        conf_group.setLayout(conf_layout)
        main_tab_layout.addWidget(conf_group)
        
        # Ajouter l'onglet principal
        tabs.addTab(main_tab, "Général")
        
        # Onglet de transformation
        transform_tab = QWidget()
        transform_layout = QVBoxLayout(transform_tab)
        
        # Groupe Rotation
        rotation_group = QGroupBox("Rotation")
        rotation_layout = QFormLayout()
        
        self.rotation_spin = QSpinBox()
        self.rotation_spin.setRange(-180, 180)
        self.rotation_spin.setSingleStep(5)
        self.rotation_spin.setValue(0)
        
        # Slider pour la rotation
        self.rotation_slider = QSlider(Qt.Orientation.Horizontal)
        self.rotation_slider.setRange(-180, 180)
        self.rotation_slider.setValue(0)
        self.rotation_slider.setTickInterval(15)
        self.rotation_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        
        # Connecter les contrôles de rotation
        self.rotation_spin.valueChanged.connect(self.rotation_slider.setValue)
        self.rotation_slider.valueChanged.connect(self.rotation_spin.setValue)
        
        rotation_layout.addRow("Rotation (degrés):", self.rotation_spin)
        rotation_layout.addRow("", self.rotation_slider)
        
        # Boutons de rotation prédéfinis
        rotation_buttons_layout = QHBoxLayout()
        
        rotate_left_button = QPushButton("↺ 90°")
        rotate_left_button.clicked.connect(lambda: self.rotation_spin.setValue(-90))
        
        rotate_reset_button = QPushButton("⟲ 0°")
        rotate_reset_button.clicked.connect(lambda: self.rotation_spin.setValue(0))
        
        rotate_right_button = QPushButton("↻ 90°")
        rotate_right_button.clicked.connect(lambda: self.rotation_spin.setValue(90))
        
        rotation_buttons_layout.addWidget(rotate_left_button)
        rotation_buttons_layout.addWidget(rotate_reset_button)
        rotation_buttons_layout.addWidget(rotate_right_button)
        
        rotation_layout.addRow("", rotation_buttons_layout)
        rotation_group.setLayout(rotation_layout)
        transform_layout.addWidget(rotation_group)
        
        # Groupe Redimensionnement
        resize_group = QGroupBox("Redimensionnement")
        resize_layout = QFormLayout()
        
        # Facteur de redimensionnement
        self.scale_factor_spin = QDoubleSpinBox()
        self.scale_factor_spin.setRange(0.1, 10.0)
        self.scale_factor_spin.setDecimals(2)
        self.scale_factor_spin.setSingleStep(0.1)
        self.scale_factor_spin.setValue(1.0)
        
        resize_layout.addRow("Facteur:", self.scale_factor_spin)
        
        # Boutons de redimensionnement prédéfinis
        scale_buttons_layout = QHBoxLayout()
        
        scale_half_button = QPushButton("50%")
        scale_half_button.clicked.connect(lambda: self.scale_factor_spin.setValue(0.5))
        
        scale_reset_button = QPushButton("100%")
        scale_reset_button.clicked.connect(lambda: self.scale_factor_spin.setValue(1.0))
        
        scale_double_button = QPushButton("200%")
        scale_double_button.clicked.connect(lambda: self.scale_factor_spin.setValue(2.0))
        
        scale_buttons_layout.addWidget(scale_half_button)
        scale_buttons_layout.addWidget(scale_reset_button)
        scale_buttons_layout.addWidget(scale_double_button)
        
        resize_layout.addRow("", scale_buttons_layout)
        
        # Maintenir les proportions
        self.maintain_aspect_check = QCheckBox("Maintenir les proportions")
        self.maintain_aspect_check.setChecked(True)
        resize_layout.addRow("", self.maintain_aspect_check)
        
        resize_group.setLayout(resize_layout)
        transform_layout.addWidget(resize_group)
        
        # Groupe Position
        position_group = QGroupBox("Position")
        position_layout = QFormLayout()
        
        # Boutons de positionnement
        positioning_layout = QHBoxLayout()
        
        top_left_button = QPushButton("↖")
        top_left_button.clicked.connect(lambda: self._position_annotation("top_left"))
        
        top_center_button = QPushButton("↑")
        top_center_button.clicked.connect(lambda: self._position_annotation("top_center"))
        
        top_right_button = QPushButton("↗")
        top_right_button.clicked.connect(lambda: self._position_annotation("top_right"))
        
        positioning_layout.addWidget(top_left_button)
        positioning_layout.addWidget(top_center_button)
        positioning_layout.addWidget(top_right_button)
        
        position_layout.addRow("", positioning_layout)
        
        positioning_layout2 = QHBoxLayout()
        
        middle_left_button = QPushButton("←")
        middle_left_button.clicked.connect(lambda: self._position_annotation("middle_left"))
        
        center_button = QPushButton("□")
        center_button.clicked.connect(lambda: self._position_annotation("center"))
        
        middle_right_button = QPushButton("→")
        middle_right_button.clicked.connect(lambda: self._position_annotation("middle_right"))
        
        positioning_layout2.addWidget(middle_left_button)
        positioning_layout2.addWidget(center_button)
        positioning_layout2.addWidget(middle_right_button)
        
        position_layout.addRow("", positioning_layout2)
        
        positioning_layout3 = QHBoxLayout()
        
        bottom_left_button = QPushButton("↙")
        bottom_left_button.clicked.connect(lambda: self._position_annotation("bottom_left"))
        
        bottom_center_button = QPushButton("↓")
        bottom_center_button.clicked.connect(lambda: self._position_annotation("bottom_center"))
        
        bottom_right_button = QPushButton("↘")
        bottom_right_button.clicked.connect(lambda: self._position_annotation("bottom_right"))
        
        positioning_layout3.addWidget(bottom_left_button)
        positioning_layout3.addWidget(bottom_center_button)
        positioning_layout3.addWidget(bottom_right_button)
        
        position_layout.addRow("", positioning_layout3)
        
        position_group.setLayout(position_layout)
        transform_layout.addWidget(position_group)
        
        # Ajouter l'onglet de transformation
        tabs.addTab(transform_tab, "Transformation")
        
        # Onglet Apparence
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)
        
        # Groupe Couleur
        color_group = QGroupBox("Couleur")
        color_layout = QFormLayout()
        
        self.color_button = QPushButton()
        self.color_button.setFixedSize(50, 30)
        self.color_button.setStyleSheet(f"background-color: {self.color.name()};")
        self.color_button.clicked.connect(self._select_color)
        
        color_layout.addRow("Couleur:", self.color_button)
        
        # Options de couleur prédéfinies
        color_presets_layout = QHBoxLayout()
        
        colors = [
            (255, 0, 0),     # Rouge
            (0, 255, 0),     # Vert
            (0, 0, 255),     # Bleu
            (255, 255, 0),   # Jaune
            (255, 0, 255),   # Magenta
            (0, 255, 255)    # Cyan
        ]
        
        for color_rgb in colors:
            preset_button = QPushButton()
            preset_button.setFixedSize(25, 25)
            preset_color = QColor(*color_rgb)
            preset_button.setStyleSheet(f"background-color: {preset_color.name()};")
            preset_button.clicked.connect(lambda checked, c=preset_color: self._set_color(c))
            color_presets_layout.addWidget(preset_button)
        
        color_layout.addRow("Préréglages:", color_presets_layout)
        
        # Slider pour l'opacité
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(self.opacity)
        self.opacity_slider.setTickInterval(10)
        self.opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity_slider.valueChanged.connect(self._update_opacity)
        
        color_layout.addRow("Opacité:", self.opacity_slider)
        
        color_group.setLayout(color_layout)
        appearance_layout.addWidget(color_group)
        
        # Groupe Options d'affichage
        display_group = QGroupBox("Options d'affichage")
        display_layout = QVBoxLayout()
        
        self.show_label_check = QCheckBox("Afficher le label de classe")
        self.show_label_check.setChecked(True)
        
        self.show_confidence_check = QCheckBox("Afficher la valeur de confiance")
        self.show_confidence_check.setChecked(True)
        
        self.highlight_similar_check = QCheckBox("Mettre en évidence les annotations similaires")
        self.highlight_similar_check.setChecked(self.highlight_similar)
        self.highlight_similar_check.stateChanged.connect(self._toggle_highlight_similar)
        
        display_layout.addWidget(self.show_label_check)
        display_layout.addWidget(self.show_confidence_check)
        display_layout.addWidget(self.highlight_similar_check)
        
        display_group.setLayout(display_layout)
        appearance_layout.addWidget(display_group)
        
        # Ajouter l'onglet d'apparence
        tabs.addTab(appearance_tab, "Apparence")
        
        # Ajouter les onglets au layout principal
        main_layout.addWidget(tabs)
        
        # Boutons de contrôle
        control_layout = QHBoxLayout()
        
        # Ajouter des boutons pour annuler/rétablir
        if self.is_edit_mode:
            undo_button = QPushButton("Annuler")
            undo_button.clicked.connect(self._undo)
            undo_button.setEnabled(False)
            self.undo_button = undo_button
            
            redo_button = QPushButton("Rétablir")
            redo_button.clicked.connect(self._redo)
            redo_button.setEnabled(False)
            self.redo_button = redo_button
            
            control_layout.addWidget(undo_button)
            control_layout.addWidget(redo_button)
            
            # Ajouter un bouton de duplication
            duplicate_button = QPushButton("Dupliquer")
            duplicate_button.clicked.connect(self._duplicate_annotation)
            control_layout.addWidget(duplicate_button)
            
            # Bouton de réinitialisation
            reset_button = QPushButton("Réinitialiser")
            reset_button.clicked.connect(self._reset_annotation)
            control_layout.addWidget(reset_button)
        
        # Boutons standard
        save_button = QPushButton("Enregistrer")
        save_button.clicked.connect(self._save_annotation)
        
        cancel_button = QPushButton("Annuler")
        cancel_button.clicked.connect(self.reject)
        
        control_layout.addStretch()
        control_layout.addWidget(save_button)
        control_layout.addWidget(cancel_button)
        
        main_layout.addLayout(control_layout)
        
        # Mettre à jour les labels de pixels
        self._update_pixel_labels()
        
    def _update_pixel_labels(self):
        """Met à jour les labels de dimensions en pixels."""
        self.x_pixel_label.setText(f"({int(self.x_spin.value() * self.image.width)}px)")
        self.y_pixel_label.setText(f"({int(self.y_spin.value() * self.image.height)}px)")
        self.width_pixel_label.setText(f"({int(self.width_spin.value() * self.image.width)}px)")
        self.height_pixel_label.setText(f"({int(self.height_spin.value() * self.image.height)}px)")
        
    def _load_annotation(self, annotation: Annotation):
        """
        Charge une annotation existante dans l'éditeur.
        
        Args:
            annotation: Annotation à charger
        """
        # Définir la classe
        index = self.class_combo.findData(annotation.class_id)
        if index >= 0:
            self.class_combo.setCurrentIndex(index)
            
        # Définir les coordonnées de la bounding box
        self.x_spin.setValue(annotation.bbox.x)
        self.y_spin.setValue(annotation.bbox.y)
        self.width_spin.setValue(annotation.bbox.width)
        self.height_spin.setValue(annotation.bbox.height)
        
        # Définir la confiance
        if annotation.confidence is not None:
            self.conf_spin.setValue(annotation.confidence)
            
    def _save_annotation(self):
        """Enregistre l'annotation et ferme l'éditeur."""
        try:
            # Appliquer les transformations si nécessaires
            if self.is_edit_mode and (self.rotation_spin.value() != 0 or self.scale_factor_spin.value() != 1.0):
                self._apply_transformations()
            
            # Récupérer les valeurs
            class_id = self.class_combo.currentData()
            x = self.x_spin.value()
            y = self.y_spin.value()
            width = self.width_spin.value()
            height = self.height_spin.value()
            confidence = self.conf_spin.value()
            
            # Créer la bounding box
            bbox = BoundingBox(
                x=x,
                y=y,
                width=width,
                height=height
            )
            
            # Créer l'annotation
            if self.original_annotation:
                # Mettre à jour l'annotation existante
                self.original_annotation.class_id = class_id
                self.original_annotation.bbox = bbox
                self.original_annotation.confidence = confidence
                self.result_annotation = self.original_annotation
                self.annotation_edited.emit(self.result_annotation)
            else:
                # Créer une nouvelle annotation
                self.result_annotation = Annotation(
                    class_id=class_id,
                    bbox=bbox,
                    confidence=confidence,
                    type=AnnotationType.BBOX
                )
                
                # Ajouter l'annotation à l'image
                self.image.add_annotation(self.result_annotation)
                self.annotation_added.emit(self.result_annotation)
                
            # Accepter le dialogue
            self.accept()
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de l'annotation: {str(e)}")
            # Afficher une erreur à l'utilisateur
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible de sauvegarder l'annotation: {str(e)}"
            )
            
    def _select_color(self):
        """Ouvre un sélecteur de couleur."""
        color = QColorDialog.getColor(self.color, self, "Sélectionner une couleur")
        if color.isValid():
            self._set_color(color)
            
    def _set_color(self, color: QColor):
        """
        Définit la couleur des annotations.
        
        Args:
            color: Nouvelle couleur
        """
        self.color = color
        self.color_button.setStyleSheet(f"background-color: {color.name()};")
        
    def _update_opacity(self, value: int):
        """
        Met à jour l'opacité des annotations.
        
        Args:
            value: Nouvelle valeur d'opacité (0-100)
        """
        self.opacity = value
        
    def _toggle_highlight_similar(self, state: int):
        """
        Active/désactive la mise en évidence des annotations similaires.
        
        Args:
            state: État de la case à cocher
        """
        self.highlight_similar = state == Qt.CheckState.Checked.value
        
    def _apply_transformations(self):
        """Applique les transformations de rotation et redimensionnement à l'annotation."""
        # Récupérer les valeurs actuelles
        x = self.x_spin.value()
        y = self.y_spin.value()
        width = self.width_spin.value()
        height = self.height_spin.value()
        
        # Calculer le centre de la bounding box
        center_x = x + width / 2
        center_y = y + height / 2
        
        # Appliquer le redimensionnement
        scale_factor = self.scale_factor_spin.value()
        if scale_factor != 1.0:
            new_width = width * scale_factor
            
            # Respecter le ratio d'aspect si demandé
            if self.maintain_aspect_check.isChecked():
                new_height = height * scale_factor
            else:
                new_height = height
            
            # Calculer la nouvelle position pour maintenir le centre
            new_x = center_x - new_width / 2
            new_y = center_y - new_height / 2
            
            # Limiter aux dimensions de l'image
            new_x = max(0, min(1 - new_width, new_x))
            new_y = max(0, min(1 - new_height, new_y))
            
            # Mettre à jour les valeurs
            self.x_spin.setValue(new_x)
            self.y_spin.setValue(new_y)
            self.width_spin.setValue(new_width)
            self.height_spin.setValue(new_height)
            
            # Récupérer les nouvelles valeurs après redimensionnement
            x = new_x
            y = new_y
            width = new_width
            height = new_height
            center_x = x + width / 2
            center_y = y + height / 2
        
        # Appliquer la rotation si nécessaire
        rotation = self.rotation_spin.value()
        if rotation != 0:
            # La rotation nécessiterait des calculs géométriques complexes pour transformer
            # la bounding box avec précision. Dans une implémentation complète, nous devrions:
            # 1. Calculer les 4 coins de la bbox actuelle
            # 2. Appliquer la rotation à chaque coin autour du centre
            # 3. Calculer la nouvelle bbox englobante
            
            # Pour une version simplifiée, nous pouvons approximer en échangeant
            # largeur et hauteur pour les rotations de 90 degrés
            if abs(rotation) == 90 or abs(rotation) == 270:
                # Échanger largeur et hauteur
                new_width = height
                new_height = width
                
                # Calculer la nouvelle position pour maintenir le centre
                new_x = center_x - new_width / 2
                new_y = center_y - new_height / 2
                
                # Limiter aux dimensions de l'image
                new_x = max(0, min(1 - new_width, new_x))
                new_y = max(0, min(1 - new_height, new_y))
                
                # Mettre à jour les valeurs
                self.x_spin.setValue(new_x)
                self.y_spin.setValue(new_y)
                self.width_spin.setValue(new_width)
                self.height_spin.setValue(new_height)
        
        # Réinitialiser les transformations
        self.rotation_spin.setValue(0)
        self.scale_factor_spin.setValue(1.0)
        
    def _position_annotation(self, position: str):
        """
        Positionne l'annotation à un emplacement spécifique dans l'image.
        
        Args:
            position: Position cible ('top_left', 'center', etc.)
        """
        # Récupérer les dimensions actuelles
        width = self.width_spin.value()
        height = self.height_spin.value()
        
        # Définir la nouvelle position selon le cas
        if position == "top_left":
            x, y = 0, 0
        elif position == "top_center":
            x, y = (1 - width) / 2, 0
        elif position == "top_right":
            x, y = 1 - width, 0
        elif position == "middle_left":
            x, y = 0, (1 - height) / 2
        elif position == "center":
            x, y = (1 - width) / 2, (1 - height) / 2
        elif position == "middle_right":
            x, y = 1 - width, (1 - height) / 2
        elif position == "bottom_left":
            x, y = 0, 1 - height
        elif position == "bottom_center":
            x, y = (1 - width) / 2, 1 - height
        elif position == "bottom_right":
            x, y = 1 - width, 1 - height
        else:
            return
        
        # Mettre à jour les coordonnées
        self.x_spin.setValue(x)
        self.y_spin.setValue(y)
        
    def _add_new_class(self):
        """Ajoute une nouvelle classe au dataset."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QPushButton, QHBoxLayout
        
        # Créer un dialogue pour ajouter une classe
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajouter une nouvelle classe")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        # Champ pour l'ID de classe
        class_id_spin = QSpinBox()
        class_id_spin.setRange(0, 999)
        
        # Trouver le prochain ID disponible
        existing_ids = [self.class_combo.itemData(i) for i in range(self.class_combo.count())]
        next_id = 0
        while next_id in existing_ids:
            next_id += 1
        class_id_spin.setValue(next_id)
        
        form_layout.addRow("ID de classe:", class_id_spin)
        
        # Champ pour le nom de classe
        class_name_edit = QLineEdit()
        form_layout.addRow("Nom de classe:", class_name_edit)
        
        layout.addLayout(form_layout)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Ajouter")
        cancel_button = QPushButton("Annuler")
        
        add_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        
        # Exécuter le dialogue
        if dialog.exec():
            class_id = class_id_spin.value()
            class_name = class_name_edit.text().strip()
            
            if not class_name:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Avertissement",
                    "Le nom de classe ne peut pas être vide"
                )
                return
            
            # Ajouter la classe au dictionnaire des classes
            self.dataset.classes[class_id] = class_name
            
            # Ajouter la classe à la liste déroulante
            self.class_combo.addItem(class_name, class_id)
            
            # Sélectionner la nouvelle classe
            index = self.class_combo.findData(class_id)
            if index >= 0:
                self.class_combo.setCurrentIndex(index)
    
    def _save_to_history(self):
        """Sauvegarde l'état actuel dans l'historique."""
        if not self.is_edit_mode or not self.original_annotation:
            return
        
        # Créer un instantané de l'état actuel
        state = {
            "class_id": self.class_combo.currentData(),
            "x": self.x_spin.value(),
            "y": self.y_spin.value(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "confidence": self.conf_spin.value()
        }
        
        # Si nous sommes au milieu de l'historique, supprimer les états après
        if self.history_position < len(self.annotation_history) - 1:
            self.annotation_history = self.annotation_history[:self.history_position + 1]
        
        # Ajouter l'état à l'historique
        self.annotation_history.append(state)
        self.history_position = len(self.annotation_history) - 1
        
        # Mettre à jour les boutons
        if hasattr(self, 'undo_button') and hasattr(self, 'redo_button'):
            self.undo_button.setEnabled(self.history_position > 0)
            self.redo_button.setEnabled(False)
    
    def _undo(self):
        """Annule la dernière modification."""
        if not self.is_edit_mode or self.history_position <= 0:
            return
        
        # Décrémenter la position
        self.history_position -= 1
        
        # Restaurer l'état précédent
        self._restore_state(self.annotation_history[self.history_position])
        
        # Mettre à jour les boutons
        self.undo_button.setEnabled(self.history_position > 0)
        self.redo_button.setEnabled(self.history_position < len(self.annotation_history) - 1)
    
    def _redo(self):
        """Rétablit la dernière modification annulée."""
        if not self.is_edit_mode or self.history_position >= len(self.annotation_history) - 1:
            return
        
        # Incrémenter la position
        self.history_position += 1
        
        # Restaurer l'état suivant
        self._restore_state(self.annotation_history[self.history_position])
        
        # Mettre à jour les boutons
        self.undo_button.setEnabled(self.history_position > 0)
        self.redo_button.setEnabled(self.history_position < len(self.annotation_history) - 1)
    
    def _restore_state(self, state: Dict):
        """
        Restaure l'éditeur à un état spécifique.
        
        Args:
            state: État à restaurer
        """
        # Restaurer la classe
        index = self.class_combo.findData(state["class_id"])
        if index >= 0:
            self.class_combo.setCurrentIndex(index)
        
        # Restaurer les coordonnées
        self.x_spin.setValue(state["x"])
        self.y_spin.setValue(state["y"])
        self.width_spin.setValue(state["width"])
        self.height_spin.setValue(state["height"])
        
        # Restaurer la confiance
        self.conf_spin.setValue(state["confidence"])
    
    def _duplicate_annotation(self):
        """Duplique l'annotation courante avec un léger décalage."""
        # Obtenir les valeurs actuelles
        class_id = self.class_combo.currentData()
        x = self.x_spin.value()
        y = self.y_spin.value()
        width = self.width_spin.value()
        height = self.height_spin.value()
        confidence = self.conf_spin.value()
        
        # Créer une boîte englobante légèrement décalée
        offset = 0.02  # 2% de décalage
        new_x = min(x + offset, 1 - width)
        new_y = min(y + offset, 1 - height)
        
        # Créer une nouvelle annotation
        bbox = BoundingBox(
            x=new_x,
            y=new_y,
            width=width,
            height=height
        )
        
        new_annotation = Annotation(
            class_id=class_id,
            bbox=bbox,
            confidence=confidence,
            type=AnnotationType.BBOX
        )
        
        # Ajouter la nouvelle annotation à l'image
        self.image.add_annotation(new_annotation)
        self.annotation_added.emit(new_annotation)
        
        # Confirmer à l'utilisateur
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Duplication réussie",
            "L'annotation a été dupliquée avec succès"
        )
    
    def _reset_annotation(self):
        """Réinitialise l'annotation à son état d'origine."""
        if self.original_annotation and self.is_edit_mode:
            self._load_annotation(self.original_annotation)
            
            # Réinitialiser l'historique
            self.annotation_history = []
            self._save_to_history()  # Sauvegarder l'état initial
    
    def keyPressEvent(self, event):
        """Gère les événements clavier."""
        from PyQt6.QtCore import Qt
        
        # Touches de raccourci
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if not (isinstance(event.source(), QSpinBox) or isinstance(event.source(), QDoubleSpinBox)):
                self._save_annotation()
        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_S:
                self._save_annotation()
            elif event.key() == Qt.Key.Key_Z and self.is_edit_mode:
                self._undo()
            elif event.key() == Qt.Key.Key_Y and self.is_edit_mode:
                self._redo()
            elif event.key() == Qt.Key.Key_D and self.is_edit_mode:
                self._duplicate_annotation()
            elif event.key() == Qt.Key.Key_R and self.is_edit_mode:
                self._reset_annotation()
        else:
            super().keyPressEvent(event)