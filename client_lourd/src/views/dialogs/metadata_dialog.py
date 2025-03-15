# src/views/dialogs/metadata_dialog.py

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
    QLabel
)
from PyQt6.QtCore import Qt
import json

class MetadataDetailsDialog(QDialog):
    """
    Dialogue pour afficher les métadonnées complètes d'une image.
    """
    
    def __init__(self, image, parent=None):
        """
        Initialise le dialogue des métadonnées.
        
        Args:
            image: Image dont on affiche les métadonnées
            parent: Widget parent
        """
        super().__init__(parent)
        self.image = image
        
        self.setWindowTitle(f"Métadonnées détaillées - {image.path.name}")
        self.resize(600, 500)
        
        self._create_ui()
        
    def _create_ui(self):
        """Crée l'interface utilisateur du dialogue."""
        layout = QVBoxLayout(self)
        
        # En-tête avec les infos basiques
        header = QLabel(f"<h3>Métadonnées pour {self.image.path.name}</h3>")
        header.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header)
        
        # Zone de texte pour les métadonnées
        self.metadata_text = QTextEdit()
        self.metadata_text.setReadOnly(True)
        layout.addWidget(self.metadata_text)
        
        # Remplir les métadonnées
        self._fill_metadata()
        
        # Boutons de commande
        buttons_layout = QHBoxLayout()
        
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)
        
        copy_button = QPushButton("Copier dans le presse-papier")
        copy_button.clicked.connect(self._copy_to_clipboard)
        
        buttons_layout.addWidget(copy_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_button)
        
        layout.addLayout(buttons_layout)
        
    def _fill_metadata(self):
        """Remplit le widget avec les métadonnées formatées."""
        text = f"Fichier: {self.image.path}\n"
        text += f"Dimensions: {self.image.width} × {self.image.height}\n"
        text += f"Source: {self.image.source.value}\n"
        text += f"Créé le: {self.image.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if self.image.modified_at:
            text += f"Modifié le: {self.image.modified_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
        text += "\nMétadonnées complètes:\n"
        
        if self.image.metadata:
            # Formatter le JSON proprement
            formatted_json = json.dumps(self.image.metadata, indent=2, sort_keys=True)
            text += formatted_json
        else:
            text += "Aucune métadonnée supplémentaire disponible."
            
        self.metadata_text.setText(text)
        
    def _copy_to_clipboard(self):
        """Copie les métadonnées dans le presse-papier."""
        clipboard = self.metadata_text.toPlainText()
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(clipboard)
        
        # Afficher un message temporaire
        original_text = self.metadata_text.toPlainText()
        self.metadata_text.setPlainText("Métadonnées copiées dans le presse-papier!")
        
        # Rétablir le texte après 1.5 secondes
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.metadata_text.setPlainText(original_text))