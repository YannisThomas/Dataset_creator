# src/views/dashboard_view.py

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QGridLayout, QScrollArea, QWidget,
    QListWidget, QListWidgetItem, QFrame, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette
from typing import Optional, List, Dict

from src.views.base_view import BaseView
from src.utils.i18n import get_translation_manager, tr
from src.controllers.controller_manager import ControllerManager

class DashboardView(BaseView):
    """
    Vue du tableau de bord principal.
    Affiche un aperçu des datasets et des actions rapides.
    """
    
    # Signaux
    dataset_requested = pyqtSignal(str)  # Demande d'ouverture d'un dataset
    create_dataset_requested = pyqtSignal()  # Demande de création de dataset
    import_requested = pyqtSignal()  # Demande d'import
    
    def __init__(self, parent=None, controller_manager: Optional[ControllerManager] = None):
        """Initialise la vue du tableau de bord."""
        super().__init__(parent, controller_manager)
        self.stats_labels = {}
        self.datasets_list = None
        self._init_ui()
        self.refresh_stats()
        
    def _init_ui(self):
        """Initialise l'interface utilisateur."""
        layout = self.base_layout
        
        # Titre principal sobre
        title_label = QLabel(tr("view.dashboard.title"))
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("margin: 10px 0;")
        layout.addWidget(title_label)
        
        # Message de bienvenue sobre
        welcome_label = QLabel(tr("view.dashboard.welcome"))
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 12px; margin-bottom: 15px;")
        layout.addWidget(welcome_label)
        
        # Contenu principal dans un scroll area
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Statistiques générales
        self._create_stats_section(scroll_layout)
        
        # Actions rapides
        self._create_quick_actions_section(scroll_layout)
        
        # Gestion des datasets
        self._create_datasets_management_section(scroll_layout)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        layout.addWidget(scroll_area)
        
    def _create_stats_section(self, layout):
        """Crée la section des statistiques."""
        stats_group = QGroupBox(tr("view.dashboard.statistics"))
        stats_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid palette(mid);
                border-radius: 4px;
                margin: 5px 0;
                padding-top: 8px;
                color: palette(text);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                color: palette(text);
            }
        """)
        
        stats_layout = QGridLayout()
        stats_layout.setSpacing(15)
        
        # Statistiques sobres
        self.stats_labels = {}
        stats_items = [
            ("total_datasets", tr("view.dashboard.total_datasets")),
            ("total_images", tr("view.dashboard.total_images")),
            ("total_annotations", tr("view.dashboard.total_annotations")),
            ("storage_used", tr("view.dashboard.storage_used"))
        ]
        
        for i, (key, label) in enumerate(stats_items):
            # Conteneur sobre pour chaque statistique
            stat_frame = QFrame()
            stat_frame.setFrameStyle(QFrame.Shape.StyledPanel)
            stat_frame.setStyleSheet("""
                QFrame {
                    border: 1px solid palette(mid);
                    border-radius: 4px;
                    padding: 8px;
                    background-color: palette(button);
                }
            """)
            stat_layout = QVBoxLayout(stat_frame)
            
            # Valeur
            value_widget = QLabel("0")
            value_widget.setStyleSheet("font-weight: bold; font-size: 16px; color: palette(text);")
            value_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stats_labels[key] = value_widget
            
            # Label
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-size: 11px; color: palette(text);")
            label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            stat_layout.addWidget(value_widget)
            stat_layout.addWidget(label_widget)
            
            row, col = i // 2, i % 2
            stats_layout.addWidget(stat_frame, row, col)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
    def _create_quick_actions_section(self, layout):
        """Crée la section des actions rapides."""
        actions_group = QGroupBox(tr("view.dashboard.quick_actions"))
        actions_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid palette(mid);
                border-radius: 4px;
                margin: 5px 0;
                padding-top: 8px;
                color: palette(text);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                color: palette(text);
            }
        """)
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(15)
        
        # Boutons d'action sobres avec thème
        button_style = """
            QPushButton {
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 10px;
                font-size: 12px;
                background-color: palette(button);
                color: palette(button-text);
            }
            QPushButton:hover {
                background-color: palette(light);
            }
            QPushButton:pressed {
                background-color: palette(dark);
            }
        """
        
        self.create_btn = QPushButton(tr("view.dashboard.create_dataset"))
        self.create_btn.setStyleSheet(button_style)
        self.create_btn.clicked.connect(self.create_dataset_requested.emit)
        
        self.import_btn = QPushButton(tr("view.dashboard.import_data"))
        self.import_btn.setStyleSheet(button_style)
        self.import_btn.clicked.connect(self.import_requested.emit)
        
        self.open_btn = QPushButton(tr("view.dashboard.open_dataset"))
        self.open_btn.setStyleSheet(button_style)
        self.open_btn.clicked.connect(self._on_open_dataset)
        
        actions_layout.addWidget(self.create_btn)
        actions_layout.addWidget(self.import_btn)
        actions_layout.addWidget(self.open_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
    def _create_datasets_management_section(self, layout):
        """Crée la section de gestion des datasets."""
        datasets_group = QGroupBox(tr("view.dashboard.datasets_management"))
        datasets_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid palette(mid);
                border-radius: 4px;
                margin: 5px 0;
                padding-top: 8px;
                color: palette(text);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                color: palette(text);
            }
        """)
        
        datasets_layout = QVBoxLayout()
        
        # Liste des datasets existants
        self.datasets_list = QListWidget()
        self.datasets_list.setMaximumHeight(200)
        self.datasets_list.setStyleSheet("""
            QListWidget {
                border: 1px solid palette(mid);
                border-radius: 4px;
                background-color: palette(base);
                color: palette(text);
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid palette(mid);
            }
            QListWidget::item:selected {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
            QListWidget::item:hover {
                background-color: palette(light);
            }
        """)
        self.datasets_list.itemDoubleClicked.connect(self._on_dataset_double_clicked)
        self.datasets_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.datasets_list.customContextMenuRequested.connect(self._on_dataset_context_menu)
        
        datasets_layout.addWidget(self.datasets_list)
        
        # Boutons de gestion
        buttons_layout = QHBoxLayout()
        
        refresh_btn = QPushButton(tr("view.dashboard.refresh"))
        refresh_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                background-color: palette(button);
                color: palette(button-text);
            }
            QPushButton:hover {
                background-color: palette(light);
            }
        """)
        refresh_btn.clicked.connect(self.refresh_stats)
        
        delete_btn = QPushButton(tr("view.dashboard.delete_dataset"))
        delete_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                background-color: palette(button);
                color: palette(button-text);
            }
            QPushButton:hover {
                background-color: palette(light);
            }
        """)
        delete_btn.clicked.connect(self._on_delete_selected_dataset)
        
        buttons_layout.addWidget(refresh_btn)
        buttons_layout.addWidget(delete_btn)
        buttons_layout.addStretch()
        
        datasets_layout.addLayout(buttons_layout)
        
        # Message si pas de datasets
        self.no_datasets_label = QLabel(tr("view.dashboard.no_datasets"))
        self.no_datasets_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_datasets_label.setStyleSheet("color: palette(mid); padding: 15px; font-style: italic; font-size: 11px;")
        datasets_layout.addWidget(self.no_datasets_label)
        
        datasets_group.setLayout(datasets_layout)
        layout.addWidget(datasets_group)
        
    def _on_open_dataset(self):
        """Gère l'ouverture d'un dataset."""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
        try:
            datasets = self.dataset_controller.list_datasets()
            if not datasets:
                QMessageBox.information(self, "Information", "Aucun dataset trouvé dans la base de données")
                return
            
            dataset_names = [f"{d['name']} ({d['image_count']} images)" for d in datasets]
            choice, ok = QInputDialog.getItem(
                self, "Ouvrir Dataset", 
                "Sélectionnez un dataset à ouvrir:", 
                dataset_names, 0, False
            )
            
            if ok and choice:
                dataset_name = choice.split(' (')[0]
                self.dataset_requested.emit(dataset_name)
                
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'ouverture: {str(e)}")
    
    def _on_dataset_context_menu(self, position):
        """Affiche le menu contextuel pour un dataset."""
        item = self.datasets_list.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        
        open_action = menu.addAction(tr("view.dashboard.open_dataset"))
        delete_action = menu.addAction(tr("view.dashboard.delete_dataset"))
        
        action = menu.exec(self.datasets_list.mapToGlobal(position))
        
        if action == open_action:
            dataset_name = item.text().split(' - ')[0]
            self.dataset_requested.emit(dataset_name)
        elif action == delete_action:
            self._delete_dataset(item.text().split(' - ')[0])
    
    def _on_delete_selected_dataset(self):
        """Supprime le dataset sélectionné."""
        current_item = self.datasets_list.currentItem()
        if not current_item:
            QMessageBox.information(self, tr("view.dashboard.info"), tr("view.dashboard.select_dataset_to_delete"))
            return
            
        dataset_name = current_item.text().split(' - ')[0]
        self._delete_dataset(dataset_name)
    
    def _delete_dataset(self, dataset_name):
        """Supprime un dataset après confirmation."""
        reply = QMessageBox.question(
            self, 
            tr("view.dashboard.confirm_delete"),
            tr("view.dashboard.confirm_delete_message", dataset_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Supprimer le dataset via le contrôleur
                self.dataset_controller.delete_dataset_by_name(dataset_name)
                
                # Actualiser l'affichage
                self.refresh_stats()
                
                QMessageBox.information(
                    self, 
                    tr("view.dashboard.success"), 
                    tr("view.dashboard.dataset_deleted", dataset_name)
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    tr("error.title"), 
                    tr("view.dashboard.delete_error", str(e))
                )
        
    def _on_dataset_double_clicked(self, item):
        """Gère le double-clic sur un dataset récent."""
        dataset_name = item.text().split(' - ')[0]  # Récupérer le nom du dataset
        self.dataset_requested.emit(dataset_name)
        
    def _on_language_changed(self, language_code: str):
        """Gestionnaire pour le changement de langue."""
        # Mettre à jour tous les textes de l'interface
        if hasattr(self, 'create_btn'):
            self.create_btn.setText(tr("view.dashboard.create_dataset"))
        if hasattr(self, 'import_btn'):
            self.import_btn.setText(tr("view.dashboard.import_data"))
        if hasattr(self, 'open_btn'):
            self.open_btn.setText(tr("view.dashboard.open_dataset"))
        if hasattr(self, 'no_datasets_label'):
            self.no_datasets_label.setText(tr("view.dashboard.no_datasets"))
        
        # Actualiser les statistiques pour mettre à jour les labels
        self.refresh_stats()
        
    def refresh_stats(self):
        """Actualise les statistiques du tableau de bord."""
        try:
            # Récupérer les statistiques via les contrôleurs
            datasets = self.dataset_controller.list_datasets()
            total_datasets = len(datasets)
            
            # Calculer les statistiques
            total_images = 0
            total_annotations = 0
            
            for dataset_info in datasets:
                total_images += dataset_info.get('image_count', 0)
                total_annotations += dataset_info.get('annotation_count', 0)
            
            # Mettre à jour l'affichage des statistiques
            if 'total_datasets' in self.stats_labels:
                self.stats_labels['total_datasets'].setText(str(total_datasets))
            if 'total_images' in self.stats_labels:
                self.stats_labels['total_images'].setText(str(total_images))
            if 'total_annotations' in self.stats_labels:
                self.stats_labels['total_annotations'].setText(str(total_annotations))
            if 'storage_used' in self.stats_labels:
                self.stats_labels['storage_used'].setText("N/A")
            
            # Mettre à jour la liste des datasets
            self._update_datasets_list(datasets)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'actualisation des statistiques: {e}")
            # Valeurs par d�faut en cas d'erreur
            for key in self.stats_labels:
                self.stats_labels[key].setText("0")
    
    def _update_datasets_list(self, datasets):
        """Met à jour la liste des datasets."""
        if not hasattr(self, 'datasets_list') or self.datasets_list is None:
            return
        
        # Vérifier si l'objet PyQt est valide
        try:
            self.datasets_list.count()
        except RuntimeError:
            return
            
        self.datasets_list.clear()
        
        if not datasets:
            self.datasets_list.hide()
            self.no_datasets_label.show()
            return
        
        self.datasets_list.show()
        self.no_datasets_label.hide()
        
        # Ajouter tous les datasets
        for dataset_info in datasets:
            name = dataset_info.get('name', 'Unknown')
            image_count = dataset_info.get('image_count', 0)
            annotation_count = dataset_info.get('annotation_count', 0)
            item_text = f"{name} - {image_count} images, {annotation_count} annotations"
            
            item = QListWidgetItem(item_text)
            self.datasets_list.addItem(item)