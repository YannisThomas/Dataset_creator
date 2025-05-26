# src/views/dialogs/export_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QLineEdit, QPushButton, QCheckBox, QSpinBox,
    QDoubleSpinBox, QTextEdit, QProgressBar, QLabel, QFileDialog,
    QTabWidget, QWidget, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont
from pathlib import Path
from typing import Optional, Dict, Any

from src.views.dialogs.base_dialog import BaseDialog
from src.models import Dataset
from src.models.enums import DatasetFormat
from src.controllers.controller_manager import ControllerManager
from src.utils.i18n import tr


class ExportWorker(QThread):
    """Worker thread pour l'export en arrière-plan"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # success, message/path
    
    def __init__(self, export_controller, dataset, export_format, output_path, options):
        super().__init__()
        self.export_controller = export_controller
        self.dataset = dataset
        self.export_format = export_format
        self.output_path = output_path
        self.options = options
        
    def run(self):
        """Exécute l'export"""
        try:
            self.status_updated.emit(tr("dialog.export.exporting"))
            
            result_path = self.export_controller.export_dataset(
                dataset=self.dataset,
                export_format=self.export_format,
                output_path=self.output_path,
                options=self.options
            )
            
            self.finished.emit(True, str(result_path))
            
        except Exception as e:
            self.finished.emit(False, str(e))


class ExportDialog(BaseDialog):
    """
    Dialogue d'export de datasets avec options avancées.
    """
    
    export_completed = pyqtSignal(str)  # Émis quand l'export est terminé avec le chemin
    
    def __init__(self, dataset: Dataset, parent=None, controller_manager: Optional[ControllerManager] = None):
        """
        Initialise le dialogue d'export.
        
        Args:
            dataset: Dataset à exporter
            parent: Widget parent
            controller_manager: Gestionnaire de contrôleurs
        """
        super().__init__(
            parent=parent,
            controller_manager=controller_manager,
            title=tr("dialog.export.title")
        )
        
        self.dataset = dataset
        self.export_worker = None
        self._init_ui()
        self._setup_defaults()
        
    def _init_ui(self):
        """Initialise l'interface utilisateur"""
        # Layout principal
        layout = QVBoxLayout()
        
        # Informations du dataset
        self._create_dataset_info(layout)
        
        # Onglets de configuration
        tabs = QTabWidget()
        
        # Onglet Format
        format_tab = self._create_format_tab()
        tabs.addTab(format_tab, tr("dialog.export.format_tab"))
        
        # Onglet Options
        options_tab = self._create_options_tab()
        tabs.addTab(options_tab, tr("dialog.export.options_tab"))
        
        # Onglet Avancé
        advanced_tab = self._create_advanced_tab()
        tabs.addTab(advanced_tab, tr("dialog.export.advanced_tab"))
        
        layout.addWidget(tabs)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status
        self.status_label = QLabel()
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        self.export_btn = QPushButton(tr("dialog.export.start_export"))
        self.export_btn.clicked.connect(self._start_export)
        
        self.cancel_btn = QPushButton(tr("button.cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.export_btn)
        buttons_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        self.setMinimumSize(600, 500)
        
    def _create_dataset_info(self, layout):
        """Crée la section d'informations du dataset"""
        info_group = QGroupBox(tr("dialog.export.dataset_info"))
        info_layout = QGridLayout()
        
        info_layout.addWidget(QLabel(tr("dialog.export.dataset_name")), 0, 0)
        info_layout.addWidget(QLabel(self.dataset.name), 0, 1)
        
        info_layout.addWidget(QLabel(tr("dialog.export.image_count")), 1, 0)
        info_layout.addWidget(QLabel(str(len(self.dataset.images))), 1, 1)
        
        total_annotations = sum(len(img.annotations) for img in self.dataset.images)
        info_layout.addWidget(QLabel(tr("dialog.export.annotation_count")), 2, 0)
        info_layout.addWidget(QLabel(str(total_annotations)), 2, 1)
        
        info_layout.addWidget(QLabel(tr("dialog.export.classes_count")), 3, 0)
        info_layout.addWidget(QLabel(str(len(self.dataset.classes))), 3, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
    def _create_format_tab(self):
        """Crée l'onglet de sélection du format"""
        tab = QWidget()
        layout = QFormLayout()
        
        # Format d'export
        self.format_combo = QComboBox()
        self.format_combo.addItem("YOLO", DatasetFormat.YOLO)
        self.format_combo.addItem("COCO", DatasetFormat.COCO)
        self.format_combo.addItem("Pascal VOC", DatasetFormat.VOC)
        layout.addRow(tr("dialog.export.format"), self.format_combo)
        
        # Répertoire de sortie
        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_browse_btn = QPushButton(tr("button.browse"))
        self.output_browse_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(self.output_browse_btn)
        layout.addRow(tr("dialog.export.output_path"), output_layout)
        
        tab.setLayout(layout)
        return tab
        
    def _create_options_tab(self):
        """Crée l'onglet des options générales"""
        tab = QWidget()
        layout = QFormLayout()
        
        # Division du dataset
        split_group = QGroupBox(tr("dialog.export.dataset_split"))
        split_layout = QFormLayout()
        
        self.train_spin = QDoubleSpinBox()
        self.train_spin.setRange(0.0, 1.0)
        self.train_spin.setSingleStep(0.1)
        self.train_spin.setValue(0.8)
        split_layout.addRow(tr("dialog.export.train_ratio"), self.train_spin)
        
        self.val_spin = QDoubleSpinBox()
        self.val_spin.setRange(0.0, 1.0)
        self.val_spin.setSingleStep(0.1)
        self.val_spin.setValue(0.2)
        split_layout.addRow(tr("dialog.export.val_ratio"), self.val_spin)
        
        self.test_spin = QDoubleSpinBox()
        self.test_spin.setRange(0.0, 1.0)
        self.test_spin.setSingleStep(0.1)
        self.test_spin.setValue(0.0)
        split_layout.addRow(tr("dialog.export.test_ratio"), self.test_spin)
        
        split_group.setLayout(split_layout)
        layout.addRow(split_group)
        
        # Options de fichiers
        self.include_images_check = QCheckBox(tr("dialog.export.include_images"))
        self.include_images_check.setChecked(True)
        layout.addRow(self.include_images_check)
        
        self.compress_check = QCheckBox(tr("dialog.export.compress_output"))
        self.compress_check.setChecked(False)
        layout.addRow(self.compress_check)
        
        tab.setLayout(layout)
        return tab
        
    def _create_advanced_tab(self):
        """Crée l'onglet des options avancées"""
        tab = QWidget()
        layout = QFormLayout()
        
        # Options spécifiques au format
        format_group = QGroupBox(tr("dialog.export.format_specific"))
        format_layout = QFormLayout()
        
        # Pour YOLO
        self.create_yaml_check = QCheckBox(tr("dialog.export.create_data_yaml"))
        self.create_yaml_check.setChecked(True)
        format_layout.addRow(self.create_yaml_check)
        
        # Pour VOC
        self.create_imagesets_check = QCheckBox(tr("dialog.export.create_imagesets"))
        self.create_imagesets_check.setChecked(True)
        format_layout.addRow(self.create_imagesets_check)
        
        format_group.setLayout(format_layout)
        layout.addRow(format_group)
        
        # Notes personnalisées
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        layout.addRow(tr("dialog.export.export_notes"), self.notes_edit)
        
        tab.setLayout(layout)
        return tab
        
    def _setup_defaults(self):
        """Configure les valeurs par défaut"""
        # Répertoire de sortie par défaut
        default_output = Path.home() / "exports" / f"{self.dataset.name}_export"
        self.output_edit.setText(str(default_output))
        
    def _browse_output(self):
        """Sélectionne le répertoire de sortie"""
        current_path = self.output_edit.text() or str(Path.home())
        
        output_dir = QFileDialog.getExistingDirectory(
            self,
            tr("dialog.export.select_output"),
            current_path
        )
        
        if output_dir:
            self.output_edit.setText(output_dir)
            
    def _start_export(self):
        """Démarre l'export"""
        # Validation
        if not self.output_edit.text():
            self.show_error(tr("dialog.export.error"), tr("dialog.export.no_output_path"))
            return
            
        # Vérifier les ratios
        total_ratio = self.train_spin.value() + self.val_spin.value() + self.test_spin.value()
        if abs(total_ratio - 1.0) > 0.01:
            self.show_error(tr("dialog.export.error"), tr("dialog.export.invalid_ratios"))
            return
            
        # Préparer les options
        options = {
            "split_ratio": {
                "train": self.train_spin.value(),
                "val": self.val_spin.value(), 
                "test": self.test_spin.value()
            },
            "include_images": self.include_images_check.isChecked(),
            "compress": self.compress_check.isChecked(),
            "format_specific": {
                "create_data_yaml": self.create_yaml_check.isChecked(),
                "create_imagesets": self.create_imagesets_check.isChecked()
            }
        }
        
        # Démarrer l'export en arrière-plan
        export_format = self.format_combo.currentData()
        output_path = Path(self.output_edit.text())
        
        self.export_worker = ExportWorker(
            self.controller_manager.export_controller,
            self.dataset,
            export_format,
            output_path,
            options
        )
        
        self.export_worker.progress_updated.connect(self.progress_bar.setValue)
        self.export_worker.status_updated.connect(self.status_label.setText)
        self.export_worker.finished.connect(self._on_export_finished)
        
        # Mise à jour de l'interface
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Mode indéterminé
        
        self.export_worker.start()
        
    def _on_export_finished(self, success: bool, message: str):
        """Appelé quand l'export est terminé"""
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.export_btn.setEnabled(True)
        
        if success:
            self.show_info(
                tr("dialog.export.success_title"),
                tr("dialog.export.success_message", message)
            )
            self.export_completed.emit(message)
            self.accept()
        else:
            self.show_error(
                tr("dialog.export.error"),
                tr("dialog.export.export_failed", message)
            )
            
    def closeEvent(self, event):
        """Gère la fermeture du dialogue"""
        if self.export_worker and self.export_worker.isRunning():
            self.export_worker.terminate()
            self.export_worker.wait()
        super().closeEvent(event)