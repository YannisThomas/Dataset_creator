# src/views/dialogs/new_dataset_dialog.py

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QSpinBox
)
from PyQt6.QtCore import Qt
from pathlib import Path
from typing import Optional, Dict

from src.views.dialogs.base_dialog import BaseDialog
from src.controllers.dataset_controller import DatasetController
from src.controllers.controller_manager import ControllerManager
from src.core.exceptions import DatasetError

class NewDatasetDialog(BaseDialog):
    """
    Dialogue de création d'un nouveau dataset.
    Utilise DatasetController pour la logique métier.
    """
    
    def __init__(
        self, 
        parent=None, 
        dataset_controller: Optional[DatasetController] = None,
        controller_manager: Optional[ControllerManager] = None
    ):
        """
        Initialise le dialogue.
        
        Args:
            parent: Widget parent
            dataset_controller: Contrôleur de dataset
            controller_manager: Gestionnaire de contrôleurs
        """
        super().__init__(
            parent=parent,
            controller_manager=controller_manager,
            title="Créer un nouveau Dataset"
        )
        
        # Utiliser le contrôleur fourni ou celui du gestionnaire
        self.dataset_controller = dataset_controller
        if not self.dataset_controller and self.controller_manager:
            self.dataset_controller = self.controller_manager.dataset_controller
        
        self.resize(500, 400)
        
        # Stocker les classes
        self.classes = {}
        
        # Stocker les informations du dataset
        self.dataset_info = None
        
        self._create_ui()
        
    def _create_ui(self):
        """Crée l'interface utilisateur du dialogue."""
        layout = QVBoxLayout(self)
        
        # Nom du dataset
        name_layout = QHBoxLayout()
        name_label = QLabel("Nom du Dataset:")
        self.name_edit = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Version
        version_layout = QHBoxLayout()
        version_label = QLabel("Version:")
        self.version_edit = QLineEdit()
        self.version_edit.setText("1.0.0")  # Version par défaut
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_edit)
        layout.addLayout(version_layout)
        
        # Répertoire de sortie
        path_layout = QHBoxLayout()
        path_label = QLabel("Répertoire de sortie:")
        self.path_edit = QLineEdit()
        browse_button = QPushButton("Parcourir...")
        browse_button.clicked.connect(self._browse_directory)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)
        
        # Tableau des classes
        layout.addWidget(QLabel("Classes:"))
        
        classes_layout = QHBoxLayout()
        
        # Table des classes
        self.classes_table = QTableWidget(0, 2)
        self.classes_table.setHorizontalHeaderLabels(["ID", "Nom"])
        classes_layout.addWidget(self.classes_table)
        
        # Boutons pour gérer les classes
        class_buttons_layout = QVBoxLayout()
        add_class_button = QPushButton("Ajouter Classe")
        add_class_button.clicked.connect(self._add_class)
        remove_class_button = QPushButton("Supprimer Classe")
        remove_class_button.clicked.connect(self._remove_class)
        class_buttons_layout.addWidget(add_class_button)
        class_buttons_layout.addWidget(remove_class_button)
        class_buttons_layout.addStretch()
        classes_layout.addLayout(class_buttons_layout)
        
        layout.addLayout(classes_layout)
        
        # Boutons de validation
        buttons_layout = QHBoxLayout()
        create_button = QPushButton("Créer")
        create_button.clicked.connect(self._create_dataset)
        cancel_button = QPushButton("Annuler")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(create_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        # Ajouter quelques classes par défaut
        self._add_default_classes()
        
    def _browse_directory(self):
        """Ouvre un dialogue pour sélectionner le répertoire de sortie."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner le répertoire de sortie",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.path_edit.setText(directory)
            
    def _add_class(self):
        """Ajoute une nouvelle classe au tableau."""
        current_row = self.classes_table.rowCount()
        self.classes_table.insertRow(current_row)
        
        # ID de classe
        id_spinbox = QSpinBox()
        id_spinbox.setMinimum(0)
        id_spinbox.setValue(current_row)  # ID par défaut
        self.classes_table.setCellWidget(current_row, 0, id_spinbox)
        
        # Nom de classe
        name_item = QTableWidgetItem("")
        self.classes_table.setItem(current_row, 1, name_item)
        
    def _add_default_classes(self):
        """Ajoute des classes par défaut au tableau."""
        default_classes = {
            0: "person",
            1: "bicycle",
            2: "car",
            3: "motorcycle",
            4: "bus",
            5: "truck"
        }
        
        for class_id, class_name in default_classes.items():
            row = self.classes_table.rowCount()
            self.classes_table.insertRow(row)
            
            # ID de classe
            id_spinbox = QSpinBox()
            id_spinbox.setMinimum(0)
            id_spinbox.setValue(class_id)
            self.classes_table.setCellWidget(row, 0, id_spinbox)
            
            # Nom de classe
            name_item = QTableWidgetItem(class_name)
            self.classes_table.setItem(row, 1, name_item)
        
    def _remove_class(self):
        """Supprime la classe sélectionnée."""
        current_row = self.classes_table.currentRow()
        if current_row >= 0:
            self.classes_table.removeRow(current_row)
            
    def _validate_inputs(self) -> bool:
        """
        Valide les entrées utilisateur.
        
        Returns:
            True si les entrées sont valides
        """
        # Vérifier le nom
        if not self.name_edit.text().strip():
            self.show_warning("Erreur", "Le nom du dataset est obligatoire")
            return False
            
        # Vérifier la version
        if not self.version_edit.text().strip():
            self.show_warning("Erreur", "La version est obligatoire")
            return False
            
        # Vérifier les classes
        class_count = self.classes_table.rowCount()
        if class_count == 0:
            self.show_warning("Erreur", "Au moins une classe est requise")
            return False
            
        # Vérifier que toutes les classes ont un nom
        for row in range(class_count):
            name_item = self.classes_table.item(row, 1)
            if not name_item or not name_item.text().strip():
                self.show_warning(
                    "Erreur", 
                    f"Le nom de classe est obligatoire pour la classe {row}"
                )
                return False
                
        return True
        
    def _create_dataset(self):
        """Crée le nouveau dataset via le contrôleur."""
        if not self._validate_inputs():
            return
            
        try:
            # Collecter les données
            name = self.name_edit.text().strip()
            version = self.version_edit.text().strip()
            path = Path(self.path_edit.text().strip()) if self.path_edit.text().strip() else None
            
            # Collecter les classes
            classes = {}
            for row in range(self.classes_table.rowCount()):
                class_id = self.classes_table.cellWidget(row, 0).value()
                class_name = self.classes_table.item(row, 1).text().strip()
                classes[class_id] = class_name
                
            # Valider les données côté contrôleur
            validation = self.dataset_controller.validate_dataset_info(
                name=name,
                classes=classes
            )
            
            if not validation["valid"]:
                self.show_warning(
                    "Validation",
                    f"Validation échouée: {validation['errors']}"
                )
                return
            
            # Stocker les informations pour la récupération
            self.dataset_info = {
                "name": name,
                "version": version,
                "path": path,
                "classes": classes
            }
            
            self.accept()
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du dataset: {str(e)}")
            self.show_error(
                "Erreur",
                f"Échec de la création du dataset: {str(e)}"
            )
            
    def get_dataset_info(self) -> Optional[Dict]:
        """
        Retourne les informations du dataset.
        
        Returns:
            Dictionnaire contenant les informations du dataset ou None
        """
        return self.dataset_info