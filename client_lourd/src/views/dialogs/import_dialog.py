# src/views/dialogs/import_dialog.py

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QFormLayout,
    QCheckBox,
    QSpinBox,
    QProgressBar,
    QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from pathlib import Path
from typing import Optional, List

from src.utils.i18n import get_translation_manager, tr
from src.views.dialogs.base_dialog import BaseDialog
from src.controllers.controller_manager import ControllerManager

class ImportWorker(QThread):
    """Thread worker pour l'importation en arrière-plan."""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, source_path: Path, dataset_name: str, include_subfolders: bool = True):
        super().__init__()
        self.source_path = source_path
        self.dataset_name = dataset_name
        self.include_subfolders = include_subfolders
        
    def run(self):
        """Exécute l'importation."""
        try:
            # Simulation d'import (à remplacer par la vraie logique)
            self.status_updated.emit(tr("dialog.import.scanning"))
            
            # Scanner les fichiers
            files = []
            if self.include_subfolders:
                files = list(self.source_path.rglob("*.*"))
            else:
                files = list(self.source_path.glob("*.*"))
            
            image_files = [f for f in files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']]
            
            total_files = len(image_files)
            
            for i, file_path in enumerate(image_files):
                self.status_updated.emit(f"{tr('dialog.import.processing')} {file_path.name}")
                self.progress_updated.emit(int((i + 1) / total_files * 100))
                
                # Simulation du traitement
                self.msleep(10)
            
            self.finished.emit(True, tr("dialog.import.success", total_files))
            
        except Exception as e:
            self.finished.emit(False, str(e))

class ImportDialog(BaseDialog):
    """
    Dialogue d'importation de fichiers locaux.
    Permet d'importer des images depuis le système de fichiers local.
    """
    
    import_completed = pyqtSignal(str, list)  # dataset_name, imported_files
    
    def __init__(
        self, 
        controller_manager: Optional[ControllerManager] = None,
        parent=None
    ):
        """
        Initialise le dialogue d'importation.
        
        Args:
            controller_manager: Gestionnaire de contrôleurs
            parent: Widget parent
        """
        super().__init__(
            parent=parent,
            controller_manager=controller_manager,
            title=tr("dialog.import.title")
        )
        
        self.import_worker = None
        self.resize(500, 400)
        
        self._create_ui()
        
    def _create_ui(self):
        """Crée l'interface utilisateur."""
        layout = QVBoxLayout(self)
        
        # Groupe Source
        source_group = QGroupBox(tr("dialog.import.source_group"))
        source_layout = QFormLayout()
        
        # Chemin source
        self.source_path_edit = QLineEdit()
        source_browse_btn = QPushButton(tr("button.browse"))
        source_browse_btn.clicked.connect(self._browse_source)
        
        source_path_layout = QHBoxLayout()
        source_path_layout.addWidget(self.source_path_edit)
        source_path_layout.addWidget(source_browse_btn)
        
        source_layout.addRow(tr("dialog.import.source_path"), source_path_layout)
        
        # Options d'importation
        self.include_subfolders_check = QCheckBox(tr("dialog.import.include_subfolders"))
        self.include_subfolders_check.setChecked(True)
        source_layout.addRow(self.include_subfolders_check)
        
        self.copy_files_check = QCheckBox(tr("dialog.import.copy_files"))
        self.copy_files_check.setChecked(True)
        source_layout.addRow(self.copy_files_check)
        
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # Groupe Destination
        dest_group = QGroupBox(tr("dialog.import.destination_group"))
        dest_layout = QFormLayout()
        
        # Nom du dataset
        self.dataset_name_edit = QLineEdit()
        dest_layout.addRow(tr("dialog.import.dataset_name"), self.dataset_name_edit)
        
        # Chemin de destination
        self.dest_path_edit = QLineEdit()
        dest_browse_btn = QPushButton(tr("button.browse"))
        dest_browse_btn.clicked.connect(self._browse_destination)
        
        dest_path_layout = QHBoxLayout()
        dest_path_layout.addWidget(self.dest_path_edit)
        dest_path_layout.addWidget(dest_browse_btn)
        
        dest_layout.addRow(tr("dialog.import.destination_path"), dest_path_layout)
        
        dest_group.setLayout(dest_layout)
        layout.addWidget(dest_group)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Zone de statut
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        self.status_text.setVisible(False)
        layout.addWidget(self.status_text)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        self.import_btn = QPushButton(tr("dialog.import.start_import"))
        self.import_btn.clicked.connect(self._start_import)
        
        self.cancel_btn = QPushButton(tr("button.cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.import_btn)
        buttons_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(buttons_layout)
        
    def _browse_source(self):
        """Ouvre le dialogue de sélection du dossier source."""
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("dialog.import.select_source"),
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.source_path_edit.setText(directory)
            
            # Proposer un nom de dataset basé sur le dossier
            if not self.dataset_name_edit.text():
                folder_name = Path(directory).name
                self.dataset_name_edit.setText(f"import_{folder_name}")
    
    def _browse_destination(self):
        """Ouvre le dialogue de sélection du dossier de destination."""
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("dialog.import.select_destination"),
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.dest_path_edit.setText(directory)
    
    def _start_import(self):
        """Démarre le processus d'importation."""
        # Validation
        source_path = self.source_path_edit.text().strip()
        if not source_path:
            self.show_error(tr("dialog.import.error"), tr("dialog.import.no_source"))
            return
            
        if not Path(source_path).exists():
            self.show_error(tr("dialog.import.error"), tr("dialog.import.source_not_exists"))
            return
            
        dataset_name = self.dataset_name_edit.text().strip()
        if not dataset_name:
            self.show_error(tr("dialog.import.error"), tr("dialog.import.no_dataset_name"))
            return
        
        # Préparer l'interface pour l'importation
        self.import_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_text.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Démarrer le worker
        self.import_worker = ImportWorker(
            Path(source_path),
            dataset_name,
            self.include_subfolders_check.isChecked()
        )
        
        self.import_worker.progress_updated.connect(self.progress_bar.setValue)
        self.import_worker.status_updated.connect(self._update_status)
        self.import_worker.finished.connect(self._on_import_finished)
        
        self.import_worker.start()
    
    def _update_status(self, message: str):
        """Met à jour le statut d'importation."""
        self.status_text.append(message)
        
    def _on_import_finished(self, success: bool, message: str):
        """Gère la fin de l'importation."""
        self.import_btn.setEnabled(True)
        
        if success:
            self.show_info(tr("dialog.import.success_title"), message)
            # Émettre le signal avec les détails
            self.import_completed.emit(self.dataset_name_edit.text(), [])
            self.accept()
        else:
            self.show_error(tr("dialog.import.error"), message)
            
        self.import_worker = None
    
    def closeEvent(self, event):
        """Gère la fermeture du dialogue."""
        if self.import_worker and self.import_worker.isRunning():
            if self.confirm_action(
                tr("dialog.import.cancel_title"),
                tr("dialog.import.cancel_message")
            ):
                self.import_worker.terminate()
                self.import_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()