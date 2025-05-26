# src/views/dialogs/base_dialog.py

from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import Qt
from typing import Optional

from src.utils.logger import Logger
from src.utils.i18n import get_translation_manager, tr
from src.controllers.controller_manager import ControllerManager

class BaseDialog(QDialog):
    """
    Classe de base pour tous les dialogues de l'application.
    Fournit des fonctionnalités communes et une gestion cohérente des contrôleurs.
    """
    
    def __init__(
        self, 
        parent=None, 
        controller_manager: Optional[ControllerManager] = None,
        title: str = "Dialog"
    ):
        """
        Initialise le dialogue de base.
        
        Args:
            parent: Widget parent
            controller_manager: Gestionnaire de contrôleurs
            title: Titre du dialogue
        """
        super().__init__(parent)
        
        # Initialisation commune
        self.logger = Logger()
        self.controller_manager = controller_manager
        self.translation_manager = get_translation_manager()
        
        # Si aucun gestionnaire n'est fourni, en créer un nouveau
        if not self.controller_manager:
            self.controller_manager = ControllerManager()
            
        # NE PAS réinitialiser la langue - utiliser celle déjà définie globalement
        # La langue est gérée globalement par MainWindow
            
        # Connecter le signal de changement de langue
        self.translation_manager.language_changed.connect(self._on_language_changed)
            
        # Propriétés du dialogue
        self.setWindowTitle(title)
        self.setModal(True)
        
        # Permettre une initialisation personnalisée avant la création de l'UI
        self._init_dialog()
        
        # Créer l'interface après l'initialisation complète
        self._create_ui()
        
    def _init_dialog(self):
        """Méthode d'initialisation personnalisée à surcharger si nécessaire."""
        pass
    
    def _create_ui(self):
        """Méthode à surcharger pour créer l'interface utilisateur."""
        pass
    
    def _on_language_changed(self, language_code: str):
        """Gestionnaire pour le changement de langue."""
        # Méthode à surcharger si nécessaire
        pass
        
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
    
    def show_error(self, title: str, message: str):
        """
        Affiche une boîte de dialogue d'erreur.
        
        Args:
            title: Titre de la boîte de dialogue
            message: Message à afficher
        """
        QMessageBox.critical(self, title, message)
        
    def show_warning(self, title: str, message: str):
        """
        Affiche une boîte de dialogue d'avertissement.
        
        Args:
            title: Titre de la boîte de dialogue
            message: Message à afficher
        """
        QMessageBox.warning(self, title, message)
        
    def show_info(self, title: str, message: str):
        """
        Affiche une boîte de dialogue d'information.
        
        Args:
            title: Titre de la boîte de dialogue
            message: Message à afficher
        """
        QMessageBox.information(self, title, message)
    
    def confirm_close(self, has_changes: bool) -> bool:
        """
        Demande confirmation avant de fermer si des modifications sont en attente.
        
        Args:
            has_changes: Si des modifications ont été apportées
            
        Returns:
            True si la fermeture est confirmée
        """
        if not has_changes:
            return True
            
        reply = QMessageBox.question(
            self,
            "Confirmer la fermeture",
            "Des modifications sont en attente. Voulez-vous vraiment fermer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    def center_on_parent(self):
        """Centre le dialogue sur le widget parent."""
        if self.parent():
            parent_geo = self.parent().geometry()
            dialog_geo = self.geometry()
            x = parent_geo.x() + (parent_geo.width() - dialog_geo.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - dialog_geo.height()) // 2
            self.move(x, y)
    
    def showEvent(self, event):
        """Gère l'affichage initial du dialogue."""
        super().showEvent(event)
        self.center_on_parent()
        
    def keyPressEvent(self, event):
        """Gère les événements clavier."""
        # Touche Échap ferme le dialogue
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)