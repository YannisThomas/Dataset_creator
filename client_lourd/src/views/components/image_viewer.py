# src/views/components/image_viewer.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
from typing import List, Optional

from src.models import Image, Annotation

class ImageViewer(QWidget):
    """
    Composant pour l'affichage et l'interaction avec les images et leurs annotations.
    """
    
    # Signaux
    image_loaded = pyqtSignal(bool)  # Émis quand une image est chargée (succès/échec)
    annotation_selected = pyqtSignal(int)  # Émis quand une annotation est sélectionnée
    
    def __init__(self, parent=None):
        """Initialise le visualiseur d'images."""
        super().__init__(parent)
        
        # État
        self.image = None  # Image actuelle
        self.pixmap = None  # QPixmap de l'image
        self.scale_factor = 1.0  # Facteur de zoom
        self.annotations = []  # Annotations à afficher
        self.selected_annotation_index = -1  # Index de l'annotation sélectionnée
        
        # Configuration de l'interface
        self._init_ui()
        
    def _init_ui(self):
        """Initialise l'interface utilisateur."""
        layout = QVBoxLayout(self)
        
        # Zone de défilement pour l'image
        self.scroll_area = QScrollArea()
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidgetResizable(True)
        
        # Label pour afficher l'image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(200, 200)
        self.image_label.setStyleSheet("background-color: #f0f0f0;")
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
    def load_image(self, image: Image) -> bool:
        """
        Charge une image dans le visualiseur.
        
        Args:
            image: Image à charger
            
        Returns:
            True si le chargement a réussi
        """
        self.image = image
        
        try:
            # Charger le pixmap
            self.pixmap = QPixmap(str(image.path))
            if self.pixmap.isNull():
                self.image_loaded.emit(False)
                return False
                
            # Afficher l'image
            self.image_label.setPixmap(self.pixmap)
            
            # Réinitialiser le zoom
            self.scale_factor = 1.0
            
            # Charger les annotations
            self.set_annotations(image.annotations)
            
            self.image_loaded.emit(True)
            return True
            
        except Exception as e:
            print(f"Erreur lors du chargement de l'image: {str(e)}")
            self.image_loaded.emit(False)
            return False
            
    def set_annotations(self, annotations: List[Annotation]):
        """
        Définit les annotations à afficher.
        
        Args:
            annotations: Liste des annotations
        """
        self.annotations = annotations
        self.selected_annotation_index = -1
        self.update()  # Redessiner avec les nouvelles annotations
        
    def select_annotation(self, index: int):
        """
        Sélectionne une annotation par son index.
        
        Args:
            index: Index de l'annotation
        """
        if 0 <= index < len(self.annotations):
            self.selected_annotation_index = index
            self.update()  # Redessiner pour mettre en évidence la sélection
            
    def clear_image(self):
        """Efface l'image et les annotations."""
        self.image = None
        self.pixmap = None
        self.annotations = []
        self.selected_annotation_index = -1
        self.image_label.clear()