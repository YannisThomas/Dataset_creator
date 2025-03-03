# src/views/base_view.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Optional, Dict, Any

from src.utils.logger import Logger
from src.controllers.controller_manager import ControllerManager

class BaseView(QWidget):
    """
    Classe de base pour toutes les vues principales de l'application.
    Fournit des fonctionnalités communes et une gestion cohérente des contrôleurs.
    """
    
    # Signaux communs
    view_initialized = pyqtSignal()
    view_updated = pyqtSignal()
    view_closed = pyqtSignal()
    
    def __init__(
        self, 
        parent=None, 
        controller_manager: Optional[ControllerManager] = None
    ):
        """
        Initialise la vue de base.
        
        Args:
            parent: Widget parent
            controller_manager: Gestionnaire de contrôleurs
        """
        super().__init__(parent)
        
        # Initialisation commune
        self.logger = Logger()
        self.controller_manager = controller_manager
        
        # Si aucun gestionnaire n'est fourni, en créer un nouveau
        if not self.controller_manager:
            self.controller_manager = ControllerManager()
            
        # Accès direct aux contrôleurs
        self.dataset_controller = self.controller_manager.dataset_controller
        self.import_controller = self.controller_manager.import_controller
        self.export_controller = self.controller_manager.export_controller
        self.api_controller = self.controller_manager.api_controller
        self.config_controller = self.controller_manager.config_controller
        
        # Initialiser les attributs communs
        self.is_dirty = False  # Indique si des modifications non sauvegardées existent
        self.progress_bar = None
        
        # Créer le layout de base
        self._init_base_layout()
        
    def _init_base_layout(self):
        """Initialise le layout de base de la vue."""
        self.base_layout = QVBoxLayout(self)
        
        # Création de la barre de progression, mais pas ajoutée au layout par défaut
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        
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
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setVisible(False)
            
    def set_progress(self, value: int):
        """
        Met à jour la valeur de la barre de progression.
        
        Args:
            value: Nouvelle valeur
        """
        self.progress_bar.setValue(value)
        
    def mark_as_dirty(self, is_dirty: bool = True):
        """
        Marque la vue comme ayant des modifications non sauvegardées.
        
        Args:
            is_dirty: True si la vue a des modifications non sauvegardées
        """
        self.is_dirty = is_dirty
        
        # Si la vue est dans une fenêtre, mettre à jour le titre
        if self.window():
            title = self.window().windowTitle()
            if is_dirty and not title.endswith('*'):
                self.window().setWindowTitle(f"{title} *")
            elif not is_dirty and title.endswith('*'):
                self.window().setWindowTitle(title[:-2])
                
    def has_unsaved_changes(self) -> bool:
        """
        Vérifie si la vue a des modifications non sauvegardées.
        
        Returns:
            True si la vue a des modifications non sauvegardées
        """
        return self.is_dirty
        
    def prompt_for_save(self) -> bool:
        """
        Demande à l'utilisateur s'il souhaite sauvegarder les modifications.
        
        Returns:
            True si l'opération peut continuer, False si elle doit être annulée
        """
        if not self.is_dirty:
            return True
            
        reply = QMessageBox.question(
            self,
            "Sauvegarder les modifications",
            "Il y a des modifications non sauvegardées. Voulez-vous les sauvegarder?",
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No | 
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return False
        elif reply == QMessageBox.StandardButton.Yes:
            return self.save_changes()
        else:  # No
            return True
            
    def save_changes(self) -> bool:
        """
        Sauvegarde les modifications de la vue.
        À implémenter dans les sous-classes.
        
        Returns:
            True si la sauvegarde a réussi
        """
        # Par défaut, marquer comme propre
        self.mark_as_dirty(False)
        return True
    
    def reload_data(self):
        """
        Recharge les données de la vue.
        À implémenter dans les sous-classes.
        """
        pass
        
    def reset_view(self):
        """
        Réinitialise la vue à son état par défaut.
        À implémenter dans les sous-classes.
        """
        pass
        
    def capture_view_state(self) -> Dict[str, Any]:
        """
        Capture l'état actuel de la vue pour restauration ultérieure.
        À implémenter dans les sous-classes.
        
        Returns:
            Dictionnaire contenant l'état de la vue
        """
        return {}
        
    def restore_view_state(self, state: Dict[str, Any]):
        """
        Restaure l'état de la vue à partir d'un état capturé.
        À implémenter dans les sous-classes.
        
        Args:
            state: État de la vue à restaurer
        """
        pass
        
    def update_controllers(self):
        """
        Met à jour les références aux contrôleurs depuis le gestionnaire.
        Utile après une réinitialisation du gestionnaire de contrôleurs.
        """
        if self.controller_manager:
            self.dataset_controller = self.controller_manager.dataset_controller
            self.import_controller = self.controller_manager.import_controller
            self.export_controller = self.controller_manager.export_controller
            self.api_controller = self.controller_manager.api_controller
            self.config_controller = self.controller_manager.config_controller
            
    def on_close(self):
        """
        Méthode appelée lorsque la vue est fermée.
        À implémenter dans les sous-classes si nécessaire.
        """
        self.view_closed.emit()