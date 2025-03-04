# src/views/dialogs/mapillary_import_dialog.py

from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout, 
    QHBoxLayout, 
    QLabel, 
    QLineEdit, 
    QPushButton,
    QProgressBar,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
    QListWidget
)
from PyQt6.QtCore import Qt
from typing import Optional, Dict

from src.models import Dataset
from src.controllers.import_controller import ImportController
from src.views.dialogs.base_dialog import BaseDialog

class MapillaryImportDialog(BaseDialog):
    """
    Dialogue pour l'importation de données depuis Mapillary.
    Permet de spécifier une zone géographique et d'importer des images annotées.
    """
    
    def __init__(
        self, 
        parent=None, 
        dataset=None,
        import_controller=None,
        controller_manager=None
    ):
        """
        Initialise le dialogue d'import Mapillary.
        
        Args:
            parent: Widget parent
            dataset: Dataset cible (optionnel)
            import_controller: Contrôleur d'import
            controller_manager: Gestionnaire de contrôleurs
        """
        super().__init__(
            parent=parent,
            controller_manager=controller_manager,
            title="Import depuis Mapillary"
        )
        
        # Récupérer ou créer le contrôleur d'import
        self.import_controller = import_controller
        if not self.import_controller and self.controller_manager:
            self.import_controller = self.controller_manager.import_controller
            
        # Stocker le dataset cible
        self.dataset = dataset
        
        # Résultats de l'import
        self.import_results = None
        
        # Initialiser l'interface
        self.resize(600, 400)
        self._create_ui()
        
    def _create_ui(self):
        """Crée l'interface utilisateur du dialogue."""
        layout = QVBoxLayout(self)
        
        # Groupe Région
        region_group = QGroupBox("Région géographique")
        region_layout = QFormLayout()
        
        # Coordonnées
        self.min_lat_spin = QDoubleSpinBox()
        self.min_lat_spin.setRange(-90.0, 90.0)
        self.min_lat_spin.setDecimals(6)
        
        self.max_lat_spin = QDoubleSpinBox()
        self.max_lat_spin.setRange(-90.0, 90.0)
        self.max_lat_spin.setDecimals(6)
        
        self.min_lon_spin = QDoubleSpinBox()
        self.min_lon_spin.setRange(-180.0, 180.0)
        self.min_lon_spin.setDecimals(6)
        
        self.max_lon_spin = QDoubleSpinBox()
        self.max_lon_spin.setRange(-180.0, 180.0)
        self.max_lon_spin.setDecimals(6)
        
        region_layout.addRow("Latitude min:", self.min_lat_spin)
        region_layout.addRow("Latitude max:", self.max_lat_spin)
        region_layout.addRow("Longitude min:", self.min_lon_spin)
        region_layout.addRow("Longitude max:", self.max_lon_spin)
        
        region_group.setLayout(region_layout)
        layout.addWidget(region_group)
        
        # Groupe Options
        options_group = QGroupBox("Options d'import")
        options_layout = QFormLayout()
        
        self.max_images_spin = QSpinBox()
        self.max_images_spin.setRange(1, 1000)
        self.max_images_spin.setValue(100)
        
        options_layout.addRow("Nombre max d'images:", self.max_images_spin)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Bouton de prévisualisation
        preview_button = QPushButton("Prévisualiser")
        preview_button.clicked.connect(self._on_preview)
        layout.addWidget(preview_button)
        
        # Liste de prévisualisation
        self.preview_list = QListWidget()
        layout.addWidget(self.preview_list)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Boutons de validation
        buttons_layout = QHBoxLayout()
        
        self.import_button = QPushButton("Importer")
        self.import_button.clicked.connect(self._on_import)
        self.import_button.setEnabled(False)  # Désactivé jusqu'à la prévisualisation
        
        cancel_button = QPushButton("Annuler")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.import_button)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        
    def _on_preview(self):
        """Prévisualise les images à importer."""
        # Cette méthode serait plus complexe dans une vraie implémentation
        # Ici nous simulons simplement le succès de la prévisualisation
        
        self.preview_list.clear()
        self.preview_list.addItem("Image 1 (simulated)")
        self.preview_list.addItem("Image 2 (simulated)")
        self.preview_list.addItem("Image 3 (simulated)")
        
        # Activer le bouton d'import
        self.import_button.setEnabled(True)
        
    def _on_import(self):
        """Importe les images depuis Mapillary."""
        # Cette méthode serait plus complexe dans une vraie implémentation
        # Ici nous simulons simplement le succès de l'import
        
        # Afficher la barre de progression
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        
        # Simuler des résultats d'import
        self.import_results = {
            "success": True,
            "images": ["image1", "image2", "image3"],
            "annotations": 12
        }
        
        # Accepter le dialogue
        self.accept()
        
    def get_import_results(self) -> Optional[Dict]:
        """
        Récupère les résultats de l'import.
        
        Returns:
            Dictionnaire des résultats ou None si l'import a échoué
        """
        return self.import_results