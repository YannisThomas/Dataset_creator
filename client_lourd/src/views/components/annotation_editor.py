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
    QGroupBox
)
from PyQt6.QtCore import Qt
from typing import Optional

from src.models import Image, Dataset, Annotation, BoundingBox
from src.models.enums import AnnotationType

class AnnotationEditor(QDialog):
    """
    Éditeur pour la création/modification d'annotations.
    """
    
    def __init__(
        self, 
        image: Image,
        dataset: Dataset,
        annotation: Optional[Annotation] = None,
        parent=None
    ):
        """
        Initialise l'éditeur d'annotations.
        
        Args:
            image: Image associée
            dataset: Dataset contenant les classes
            annotation: Annotation à modifier (None pour création)
            parent: Widget parent
        """
        super().__init__(parent)
        
        self.image = image
        self.dataset = dataset
        self.annotation = annotation
        self.result_annotation = None
        
        self.setWindowTitle("Éditeur d'annotations")
        self.resize(400, 300)
        
        self._init_ui()
        
        # Si une annotation est fournie, remplir les champs
        if annotation:
            self._load_annotation(annotation)
        
    def _init_ui(self):
        """Initialise l'interface utilisateur."""
        layout = QVBoxLayout(self)
        
        # Groupe Classes
        class_group = QGroupBox("Classe")
        class_layout = QFormLayout()
        
        # Liste déroulante des classes
        self.class_combo = QComboBox()
        for class_id, class_name in self.dataset.classes.items():
            self.class_combo.addItem(class_name, class_id)
        
        class_layout.addRow("Classe:", self.class_combo)
        class_group.setLayout(class_layout)
        layout.addWidget(class_group)
        
        # Groupe Bounding Box
        bbox_group = QGroupBox("Bounding Box")
        bbox_layout = QFormLayout()
        
        # Spinners pour les coordonnées
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(0.0, 1.0)
        self.x_spin.setDecimals(4)
        self.x_spin.setSingleStep(0.01)
        
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(0.0, 1.0)
        self.y_spin.setDecimals(4)
        self.y_spin.setSingleStep(0.01)
        
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.0, 1.0)
        self.width_spin.setDecimals(4)
        self.width_spin.setSingleStep(0.01)
        
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0.0, 1.0)
        self.height_spin.setDecimals(4)
        self.height_spin.setSingleStep(0.01)
        
        bbox_layout.addRow("X:", self.x_spin)
        bbox_layout.addRow("Y:", self.y_spin)
        bbox_layout.addRow("Largeur:", self.width_spin)
        bbox_layout.addRow("Hauteur:", self.height_spin)
        
        bbox_group.setLayout(bbox_layout)
        layout.addWidget(bbox_group)
        
        # Groupe Confiance
        conf_group = QGroupBox("Confiance")
        conf_layout = QFormLayout()
        
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.0, 1.0)
        self.conf_spin.setDecimals(2)
        self.conf_spin.setSingleStep(0.1)
        self.conf_spin.setValue(1.0)  # 100% par défaut
        
        conf_layout.addRow("Confiance:", self.conf_spin)
        conf_group.setLayout(conf_layout)
        layout.addWidget(conf_group)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        save_button = QPushButton("Enregistrer")
        save_button.clicked.connect(self._save_annotation)
        
        cancel_button = QPushButton("Annuler")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        
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
        if self.annotation:
            # Mettre à jour l'annotation existante
            self.annotation.class_id = class_id
            self.annotation.bbox = bbox
            self.annotation.confidence = confidence
            self.result_annotation = self.annotation
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
            
        # Accepter le dialogue
        self.accept()
        
    def get_annotation(self) -> Optional[Annotation]:
        """
        Récupère l'annotation créée ou modifiée.
        
        Returns:
            Annotation ou None si annulée
        """
        return self.result_annotation