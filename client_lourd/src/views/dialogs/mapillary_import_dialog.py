# src/views/dialogs/mapillary_import_dialog.py

import json
import math
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QWidget,
    QApplication
)
from PyQt6.QtCore import Qt, QThread, QSize
from PyQt6.QtGui import QIcon, QPixmap
import requests

from src.views.dialogs.base_dialog import BaseDialog
from src.models import Dataset, Image, Annotation, BoundingBox
from src.models.enums import ImageSource, AnnotationType
from typing import Dict, Optional, List, Union

class DownloadThread(QThread):
    """Thread pour télécharger une image en arrière-plan."""
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.data = None
        
    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                self.data = response.content
        except Exception as e:
            print(f"Erreur de téléchargement: {str(e)}")


class MapillaryImportDialog(BaseDialog):
    """
    Dialogue pour l'importation de données depuis Mapillary.
    Permet de spécifier une ville ou un axe routier en France.
    """
    
    def __init__(
        self, 
        parent=None, 
        dataset=None,
        import_controller=None,
        api_controller=None,
        controller_manager=None
    ):
        """
        Initialise le dialogue d'import Mapillary.
        
        Args:
            parent: Widget parent
            dataset: Dataset cible (optionnel)
            import_controller: Contrôleur d'import
            api_controller: Contrôleur API
            controller_manager: Gestionnaire de contrôleurs
        """
        super().__init__(
            parent=parent,
            controller_manager=controller_manager,
            title="Import depuis Mapillary"
        )
        
        # Récupérer ou créer les contrôleurs
        self.import_controller = import_controller
        self.api_controller = api_controller
        
        if not self.import_controller and self.controller_manager:
            self.import_controller = self.controller_manager.import_controller
            
        if not self.api_controller and self.controller_manager:
            self.api_controller = self.controller_manager.api_controller
            
        # Stocker le dataset cible
        self.dataset = dataset
        
        # Résultats de l'import
        self.import_results = None
        
        # Charger les configurations
        self._load_config()
        
        # Initialiser l'interface
        self.resize(700, 600)
        self._create_ui()
        
    def _load_config(self):
        """Charge les fichiers de configuration."""
        # Initialize mapillary_config with default values
        self.mapillary_config = {"api": {}, "class_mapping": {}, "import_settings": {}}
        
        try:
            # Chemin vers le dossier de configuration - CORRIGÉ
            config_dir = Path("client_lourd/src/config")  # Chemin correct
            
            # Charger les zones géographiques françaises
            geo_path = config_dir / "french_geo_zones.json"
            if geo_path.exists():
                with open(geo_path, 'r', encoding='utf-8') as f:
                    self.geo_data = json.load(f)
            else:
                # Essayer un chemin alternatif si le premier échoue
                alt_path = Path("client_lourd/src/config/french_geo_zones.json")
                if alt_path.exists():
                    with open(alt_path, 'r', encoding='utf-8') as f:
                        self.geo_data = json.load(f)
                else:
                    self.logger.warning(f"Fichier de zones géographiques non trouvé: {geo_path} ni {alt_path}")
                    self.geo_data = {"cities": {}, "roads": {}, "regions": {}, "landmarks": {}}
                    
            # Optionally load Mapillary configuration
            mapillary_config_path = config_dir / "mapillary_config.json"
            if mapillary_config_path.exists():
                with open(mapillary_config_path, 'r', encoding='utf-8') as f:
                    self.mapillary_config = json.load(f)
                    
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des configurations: {str(e)}")
            self.geo_data = {"cities": {}, "roads": {}, "regions": {}, "landmarks": {}}

        
    def _create_ui(self):
        """Crée l'interface utilisateur du dialogue."""
        layout = QVBoxLayout(self)
        
        # Groupe Sélection de région
        region_group = QGroupBox("Sélection de région en France")
        region_layout = QVBoxLayout()
        
        # Onglets pour différentes méthodes de sélection
        region_tabs = QTabWidget()
        
        # Onglet Villes
        cities_tab = QWidget()
        cities_layout = QVBoxLayout(cities_tab)
        
        # Liste des villes françaises
        cities_label = QLabel("Sélectionnez une ville:")
        cities_layout.addWidget(cities_label)
        
        self.cities_list = QListWidget()
        self.cities_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Remplir la liste des villes depuis le fichier de config
        for city in sorted(self.geo_data.get("cities", {}).keys()):
            self.cities_list.addItem(city)
        
        cities_layout.addWidget(self.cities_list)
        
        # Rayon autour de la ville
        radius_layout = QHBoxLayout()
        radius_label = QLabel("Rayon (km):")
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(1, 30)
        # Valeur par défaut depuis la config ou 5km par défaut
        default_radius = self.mapillary_config.get("import_settings", {}).get("default_radius_km", 5)
        self.radius_spin.setValue(default_radius)
        radius_layout.addWidget(radius_label)
        radius_layout.addWidget(self.radius_spin)
        cities_layout.addLayout(radius_layout)
        
        region_tabs.addTab(cities_tab, "Villes")
        
        # Onglet Axes routiers
        roads_tab = QWidget()
        roads_layout = QVBoxLayout(roads_tab)
        
        roads_label = QLabel("Sélectionnez un axe routier:")
        roads_layout.addWidget(roads_label)
        
        self.roads_list = QListWidget()
        self.roads_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Remplir la liste des axes routiers depuis le fichier de config
        for road in sorted(self.geo_data.get("roads", {}).keys()):
            self.roads_list.addItem(road)
        
        roads_layout.addWidget(self.roads_list)
        
        # Distance le long de la route
        distance_layout = QHBoxLayout()
        distance_label = QLabel("Portion (km depuis le début):")
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(5, 100)
        self.distance_spin.setValue(20)
        distance_layout.addWidget(distance_label)
        distance_layout.addWidget(self.distance_spin)
        roads_layout.addLayout(distance_layout)
        
        # Largeur du corridor
        corridor_layout = QHBoxLayout()
        corridor_label = QLabel("Largeur du corridor (m):")
        self.corridor_spin = QSpinBox()
        self.corridor_spin.setRange(100, 1000)
        # Valeur par défaut depuis la config ou 200m par défaut
        default_width = self.mapillary_config.get("import_settings", {}).get("default_corridor_width_m", 200)
        self.corridor_spin.setValue(default_width)
        self.corridor_spin.setSingleStep(100)
        corridor_layout.addWidget(corridor_label)
        corridor_layout.addWidget(self.corridor_spin)
        roads_layout.addLayout(corridor_layout)
        
        region_tabs.addTab(roads_tab, "Axes routiers")
        
        # Onglet Points d'intérêt
        landmarks_tab = QWidget()
        landmarks_layout = QVBoxLayout(landmarks_tab)
        
        landmarks_label = QLabel("Sélectionnez un point d'intérêt:")
        landmarks_layout.addWidget(landmarks_label)
        
        self.landmarks_list = QListWidget()
        self.landmarks_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Remplir la liste des points d'intérêt depuis le fichier de config
        for landmark in sorted(self.geo_data.get("landmarks", {}).keys()):
            self.landmarks_list.addItem(landmark)
        
        landmarks_layout.addWidget(self.landmarks_list)
        
        # Rayon autour du point d'intérêt
        lm_radius_layout = QHBoxLayout()
        lm_radius_label = QLabel("Rayon (km):")
        self.lm_radius_spin = QSpinBox()
        self.lm_radius_spin.setRange(1, 10)
        self.lm_radius_spin.setValue(2)
        lm_radius_layout.addWidget(lm_radius_label)
        lm_radius_layout.addWidget(self.lm_radius_spin)
        landmarks_layout.addLayout(lm_radius_layout)
        
        region_tabs.addTab(landmarks_tab, "Points d'intérêt")
        
        # Onglet Coordonnées manuelles (pour les utilisateurs avancés)
        manual_tab = QWidget()
        manual_layout = QFormLayout(manual_tab)
        
        # Coordonnées
        self.min_lat_spin = QDoubleSpinBox()
        self.min_lat_spin.setRange(41.0, 51.5)  # Limites de la France
        self.min_lat_spin.setDecimals(6)
        self.min_lat_spin.setValue(48.8)
        
        self.max_lat_spin = QDoubleSpinBox()
        self.max_lat_spin.setRange(41.0, 51.5)
        self.max_lat_spin.setDecimals(6)
        self.max_lat_spin.setValue(48.9)
        
        self.min_lon_spin = QDoubleSpinBox()
        self.min_lon_spin.setRange(-5.5, 9.5)  # Limites de la France
        self.min_lon_spin.setDecimals(6)
        self.min_lon_spin.setValue(2.3)
        
        self.max_lon_spin = QDoubleSpinBox()
        self.max_lon_spin.setRange(-5.5, 9.5)
        self.max_lon_spin.setDecimals(6)
        self.max_lon_spin.setValue(2.4)
        
        manual_layout.addRow("Latitude min:", self.min_lat_spin)
        manual_layout.addRow("Latitude max:", self.max_lat_spin)
        manual_layout.addRow("Longitude min:", self.min_lon_spin)
        manual_layout.addRow("Longitude max:", self.max_lon_spin)
        
        region_tabs.addTab(manual_tab, "Manuel")
        
        region_layout.addWidget(region_tabs)
        region_group.setLayout(region_layout)
        layout.addWidget(region_group)
        
        # Groupe Options
        options_group = QGroupBox("Options d'import")
        options_layout = QFormLayout()
        
        self.max_images_spin = QSpinBox()
        self.max_images_spin.setRange(10, 1000)
        # Valeur par défaut depuis la config ou 100 par défaut
        default_max = self.mapillary_config.get("import_settings", {}).get("max_images_per_import", 100)
        self.max_images_spin.setValue(default_max)
        
        options_layout.addRow("Nombre max d'images:", self.max_images_spin)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Mémoriser l'onglet actif
        self.region_tabs = region_tabs
        
        # Bouton de prévisualisation
        preview_button = QPushButton("Prévisualiser")
        preview_button.clicked.connect(self._on_preview)
        layout.addWidget(preview_button)
        
        # Liste de prévisualisation
        preview_label = QLabel("Images disponibles:")
        layout.addWidget(preview_label)
        
        self.preview_list = QListWidget()
        self.preview_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.preview_list.setIconSize(QSize(64, 64))
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
    
    def _get_bbox_from_selection(self) -> dict:
        """
        Détermine la bounding box à partir de la sélection actuelle.
        
        Returns:
            Dictionnaire avec les coordonnées de la bounding box
        """
        # Déterminer l'onglet actif
        current_tab_index = self.region_tabs.currentIndex()
        
        if current_tab_index == 0:  # Villes
            # Récupérer la ville sélectionnée
            items = self.cities_list.selectedItems()
            if not items:
                raise ValueError("Veuillez sélectionner une ville")
            
            city_name = items[0].text()
            city_data = self.geo_data["cities"][city_name]
            
            # Convertir le rayon de km en degrés (approximation)
            radius_km = self.radius_spin.value()
            radius_lat = radius_km / 111.0  # 1 degré ≈ 111km en latitude
            radius_lon = radius_km / (111.0 * math.cos(math.radians(city_data["lat"])))  # Ajustement longitude
            
            return {
                'min_lat': city_data["lat"] - radius_lat,
                'max_lat': city_data["lat"] + radius_lat,
                'min_lon': city_data["lon"] - radius_lon,
                'max_lon': city_data["lon"] + radius_lon
            }
            
        elif current_tab_index == 1:  # Axes routiers
            # Récupérer l'axe sélectionné
            items = self.roads_list.selectedItems()
            if not items:
                raise ValueError("Veuillez sélectionner un axe routier")
            
            road_name = items[0].text()
            road_data = self.geo_data["roads"][road_name]
            
            # Calculer un point le long de la route
            start = road_data["start"]
            end = road_data["end"]
            
            distance_km = self.distance_spin.value()
            total_distance = self._haversine(
                start["lat"], start["lon"], 
                end["lat"], end["lon"]
            )
            
            # S'assurer que la distance n'est pas supérieure à la longueur totale
            distance_km = min(distance_km, total_distance)
            
            # Calculer le ratio
            ratio = distance_km / total_distance
            
            # Calculer le point le long de la route
            point_lat = start["lat"] + ratio * (end["lat"] - start["lat"])
            point_lon = start["lon"] + ratio * (end["lon"] - start["lon"])
            
            # Calculer une direction perpendiculaire (approximation)
            direction_lat = end["lat"] - start["lat"]
            direction_lon = end["lon"] - start["lon"]
            
            # Vecteur perpendiculaire (rotation de 90 degrés)
            perp_lat = -direction_lon
            perp_lon = direction_lat
            
            # Normaliser le vecteur perpendiculaire
            norm = math.sqrt(perp_lat**2 + perp_lon**2)
            if norm > 0:
                perp_lat /= norm
                perp_lon /= norm
            
            # Largeur du corridor en degrés
            corridor_m = self.corridor_spin.value()
            corridor_lat = corridor_m / 111000.0  # 1 degré ≈ 111000m en latitude
            corridor_lon = corridor_m / (111000.0 * math.cos(math.radians(point_lat)))
            
            # Créer une bounding box autour du point avec la largeur du corridor
            return {
                'min_lat': point_lat - corridor_lat,
                'max_lat': point_lat + corridor_lat,
                'min_lon': point_lon - corridor_lon,
                'max_lon': point_lon + corridor_lon
            }
        
        elif current_tab_index == 2:  # Points d'intérêt
            # Récupérer le point d'intérêt sélectionné
            items = self.landmarks_list.selectedItems()
            if not items:
                raise ValueError("Veuillez sélectionner un point d'intérêt")
            
            landmark_name = items[0].text()
            landmark_data = self.geo_data["landmarks"][landmark_name]
            
            # Convertir le rayon de km en degrés (approximation)
            radius_km = self.lm_radius_spin.value()
            radius_lat = radius_km / 111.0  # 1 degré ≈ 111km en latitude
            radius_lon = radius_km / (111.0 * math.cos(math.radians(landmark_data["lat"])))
            
            return {
                'min_lat': landmark_data["lat"] - radius_lat,
                'max_lat': landmark_data["lat"] + radius_lat,
                'min_lon': landmark_data["lon"] - radius_lon,
                'max_lon': landmark_data["lon"] + radius_lon
            }
            
        else:  # Manuel
            return {
                'min_lat': self.min_lat_spin.value(),
                'max_lat': self.max_lat_spin.value(),
                'min_lon': self.min_lon_spin.value(),
                'max_lon': self.max_lon_spin.value()
            }

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcule la distance en km entre deux points géographiques.
        
        Args:
            lat1, lon1: Coordonnées du premier point
            lat2, lon2: Coordonnées du deuxième point
            
        Returns:
            Distance en km
        """
        # Rayon de la Terre en km
        R = 6371.0
        
        # Conversion en radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Différences de coordonnées
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        
        # Formule de Haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        # Distance
        return R * c
    
    def _on_preview(self):
        """Prévisualise les images à importer."""
        try:
            # Récupérer la bounding box en fonction de la sélection
            bbox = self._get_bbox_from_selection()
            
            max_images = self.max_images_spin.value()
            
            # Afficher la progression
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)  # Indiquer le début
            
            # Prévisualiser les images via le contrôleur
            try:
                preview_images = self.import_controller.preview_mapillary_import(
                    bbox=bbox,
                    max_images=max_images
                )
                
                # Mettre à jour la liste des prévisualisations
                self.preview_list.clear()
                self.progress_bar.setValue(50)
                
                if not preview_images:
                    QMessageBox.warning(
                        self,
                        "Aucune image disponible",
                        "Aucune image n'a été trouvée dans la zone sélectionnée.\n"
                        "Essayez d'élargir la zone ou de choisir une autre région."
                    )
                    self.progress_bar.setVisible(False)
                    return
                
                for i, image in enumerate(preview_images):
                    item = QListWidgetItem()
                    
                    # Créer le texte de l'élément
                    location_info = ""
                    if image.metadata and 'coordinates' in image.metadata:
                        coords = image.metadata['coordinates']
                        location_info = f" ({coords.get('latitude', 0):.4f}, {coords.get('longitude', 0):.4f})"
                        
                    annotations_count = len(image.annotations) if hasattr(image, 'annotations') else 0
                    text = f"Image {i+1}{location_info} - {annotations_count} annotations"
                    
                    item.setText(text)
                    item.setData(Qt.ItemDataRole.UserRole, image)
                    
                    # Essayer de charger une miniature si disponible
                    if hasattr(image, 'path') and isinstance(image.path, str) and image.path:
                        try:
                            # Télécharger une miniature temporaire en asynchrone
                            self._download_image_async(
                                image.path, 
                                lambda pixmap, item=item: self._set_item_thumbnail(item, pixmap)
                            )
                        except Exception as e:
                            print(f"Impossible de charger la miniature: {str(e)}")
                    
                    self.preview_list.addItem(item)
                    
                    # Mise à jour progressive
                    if i % 5 == 0:
                        self.progress_bar.setValue(int(50 + (i / len(preview_images)) * 50))
                        QApplication.processEvents()
                
                self.progress_bar.setValue(100)
                
                # Activer le bouton d'import si des images sont disponibles
                self.import_button.setEnabled(len(preview_images) > 0)
                
            except Exception as e:
                raise Exception(f"Échec de la prévisualisation: {str(e)}")
                
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(
                self,
                "Erreur de prévisualisation",
                f"Impossible de prévisualiser les images: {str(e)}"
            )
    
    def _download_image_async(self, url: str, callback) -> None:
        """
        Télécharge une image depuis une URL de manière asynchrone
        et exécute un callback avec le pixmap résultant.
        
        Args:
            url: URL de l'image
            callback: Fonction à appeler avec le pixmap téléchargé
        """
        thread = DownloadThread(url)
        
        # Connecter le signal finished
        thread.finished.connect(lambda: self._process_downloaded_image(thread, callback))
        
        # Démarrer le thread
        thread.start()
    
    def _process_downloaded_image(self, thread, callback):
        """
        Traite l'image téléchargée et appelle le callback.
        
        Args:
            thread: Thread de téléchargement
            callback: Fonction à appeler avec le pixmap
        """
        if thread.data:
            pixmap = QPixmap()
            pixmap.loadFromData(thread.data)
            
            if not pixmap.isNull():
                callback(pixmap)
        
        # Nettoyer le thread
        thread.deleteLater()
    
    def _set_item_thumbnail(self, item: QListWidgetItem, pixmap: QPixmap):
        """
        Définit la miniature d'un élément de la liste.
        Cette méthode est appelée de manière asynchrone.
        
        Args:
            item: Élément de la liste
            pixmap: Miniature à afficher
        """
        if item and pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                64, 64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            item.setIcon(QIcon(scaled_pixmap))
            # Forcer la mise à jour
            self.preview_list.update()
    
    def _on_import(self):
        """Importe les images depuis Mapillary."""
        try:
            # Vérifier qu'un dataset est ouvert si nécessaire
            if not self.dataset and not self.confirm_action(
                "Créer un nouveau dataset",
                "Aucun dataset n'est actuellement ouvert. Voulez-vous en créer un nouveau?"
            ):
                return
                
            # Récupérer la bounding box
            bbox = self._get_bbox_from_selection()
            
            max_images = self.max_images_spin.value()
            
            # Afficher la progression
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            if not self.dataset:
                # Créer un nom pour le dataset basé sur la sélection
                dataset_name = self._get_dataset_name_from_selection()
                
                # Utiliser les classes de panneaux depuis la configuration
                classes = {}
                for class_id, sign_id in self.mapillary_config.get("class_mapping", {}).items():
                    # Extraire le nom lisible du panneau (ex: "regulatory--stop--g1" -> "Stop")
                    sign_parts = sign_id.split("--")
                    if len(sign_parts) > 1:
                        sign_name = sign_parts[1].replace("-", " ").title()
                        classes[int(class_id)] = sign_name
                    else:
                        classes[int(class_id)] = sign_id
                
                try:
                    # Importer directement depuis Mapillary avec création du dataset
                    self.progress_bar.setValue(10)
                    dataset = self.import_controller.import_from_mapillary(
                        bbox=bbox,
                        dataset_name=dataset_name,
                        max_images=max_images,
                        classes=classes
                    )
                    
                    self.import_results = {
                        "success": True,
                        "dataset": dataset,
                        "images": [img.id for img in dataset.images],
                        "annotations": sum(len(img.annotations) for img in dataset.images)
                    }
                    
                except Exception as e:
                    raise Exception(f"Échec de l'importation depuis Mapillary: {str(e)}")
                    
            else:
                # Utiliser le dataset existant
                try:
                    # Récupérer les images sélectionnées
                    selected_images = []
                    for i in range(self.preview_list.count()):
                        item = self.preview_list.item(i)
                        if item.isSelected():  # Si l'élément est sélectionné
                            image = item.data(Qt.ItemDataRole.UserRole)
                            selected_images.append(image)
                    
                    if not selected_images:
                        # Si aucune image n'est sélectionnée, utiliser toutes les images
                        for i in range(self.preview_list.count()):
                            item = self.preview_list.item(i)
                            image = item.data(Qt.ItemDataRole.UserRole)
                            selected_images.append(image)
                    
                    # Mettre à jour la progression
                    self.progress_bar.setValue(10)
                    
                    # Importer les images dans le dataset existant
                    dataset = self.api_controller.import_images_to_dataset(
                        dataset=self.dataset,
                        images=selected_images,
                        download_images=True
                    )
                    
                    self.import_results = {
                        "success": True,
                        "dataset": dataset,
                        "images": [img.id for img in selected_images],
                        "annotations": sum(len(img.annotations) for img in selected_images)
                    }
                    
                except Exception as e:
                    raise Exception(f"Échec de l'ajout d'images au dataset: {str(e)}")
            
            # Succès
            self.progress_bar.setValue(100)
            
            # Afficher un message de succès
            QMessageBox.information(
                self,
                "Import réussi",
                f"L'importation a réussi!\n\n"
                f"- {len(self.import_results['images'])} images importées\n"
                f"- {self.import_results['annotations']} annotations détectées"
            )
            
            self.accept()
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(
                self,
                "Erreur d'importation",
                f"Impossible d'importer les images: {str(e)}"
            )
    
    def _get_dataset_name_from_selection(self) -> str:
        """
        Génère un nom de dataset basé sur la sélection actuelle.
        
        Returns:
            Nom du dataset
        """
        # Déterminer l'onglet actif
        current_tab_index = self.region_tabs.currentIndex()
        
        if current_tab_index == 0:  # Villes
            # Récupérer la ville sélectionnée
            items = self.cities_list.selectedItems()
            if not items:
                return f"Mapillary_Import_{datetime.now().strftime('%Y%m%d_%H%M')}"
            
            city_name = items[0].text()
            return f"Mapillary_{city_name}_{self.radius_spin.value()}km"
            
        elif current_tab_index == 1:  # Axes routiers
            # Récupérer l'axe sélectionné
            items = self.roads_list.selectedItems()
            if not items:
                return f"Mapillary_Import_{datetime.now().strftime('%Y%m%d_%H%M')}"
            
            road_name = items[0].text()
            road_name_simplified = road_name.split('(')[0].strip()
            return f"Mapillary_{road_name_simplified}_{self.distance_spin.value()}km"
            
        elif current_tab_index == 2:  # Points d'intérêt
            # Récupérer le point d'intérêt sélectionné
            items = self.landmarks_list.selectedItems()
            if not items:
                return f"Mapillary_Import_{datetime.now().strftime('%Y%m%d_%H%M')}"
            
            landmark_name = items[0].text()
            return f"Mapillary_{landmark_name}_{self.lm_radius_spin.value()}km"
            
        else:  # Manuel
            lat = (self.min_lat_spin.value() + self.max_lat_spin.value()) / 2
            lon = (self.min_lon_spin.value() + self.max_lon_spin.value()) / 2
            return f"Mapillary_Coord_{lat:.2f}_{lon:.2f}"
    
    def get_import_results(self) -> Optional[Dict]:
        """
        Récupère les résultats de l'import.
        
        Returns:
            Dictionnaire des résultats ou None si l'import a échoué
        """
        return self.import_results