# src/utils/i18n.py

import json
import os
from pathlib import Path
from typing import Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal

class TranslationManager(QObject):
    """
    Gestionnaire de traductions pour le support multilingue.
    Supporte le français et l'anglais avec changement dynamique.
    """
    
    # Signal émis quand la langue change
    language_changed = pyqtSignal(str)
    
    def __init__(self, default_language: str = "fr"):
        """
        Initialise le gestionnaire de traductions.
        
        Args:
            default_language: Langue par défaut ("fr" ou "en")
        """
        super().__init__()
        self.current_language = default_language
        self.translations: Dict[str, Dict[str, str]] = {}
        self.fallback_language = "en"
        
        # Chemin vers les fichiers de traduction
        self.translations_dir = Path(__file__).parent.parent / "config" / "translations"
        
        # Charger les traductions
        self._load_translations()
    
    def _load_translations(self):
        """Charge tous les fichiers de traduction disponibles."""
        try:
            # Créer le dossier s'il n'existe pas
            self.translations_dir.mkdir(parents=True, exist_ok=True)
            
            # Charger chaque fichier de langue
            for lang_file in self.translations_dir.glob("*.json"):
                lang_code = lang_file.stem
                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                except Exception as e:
                    print(f"Erreur lors du chargement de {lang_file}: {e}")
            
            # Si aucune traduction n'est trouvée, créer les fichiers par défaut
            if not self.translations:
                self._create_default_translations()
                
        except Exception as e:
            print(f"Erreur lors du chargement des traductions: {e}")
            self._create_fallback_translations()
    
    def _create_default_translations(self):
        """Crée les fichiers de traduction par défaut."""
        # Traductions françaises
        fr_translations = {
            # Fenêtre principale
            "main_window.title": "YOLO Dataset Manager",
            "main_window.file": "Fichier",
            "main_window.edit": "Édition",
            "main_window.view": "Affichage",
            "main_window.tools": "Outils",
            "main_window.help": "Aide",
            "main_window.dashboard": "Tableau de bord",
            "main_window.dataset": "Dataset",
            
            # Menu Fichier
            "menu.file.new_dataset": "Nouveau Dataset",
            "menu.file.open_dataset": "Ouvrir Dataset",
            "menu.file.save_dataset": "Sauvegarder Dataset",
            "menu.file.import_mapillary": "Importer depuis Mapillary",
            "menu.file.import_local": "Importer fichiers locaux",
            "menu.file.export": "Exporter",
            "menu.file.preferences": "Préférences",
            "menu.file.quit": "Quitter",
            
            # Menu Édition
            "menu.edit.undo": "Annuler",
            "menu.edit.redo": "Refaire",
            "menu.edit.cut": "Couper",
            "menu.edit.copy": "Copier",
            "menu.edit.paste": "Coller",
            "menu.edit.select_all": "Tout sélectionner",
            
            # Menu Affichage
            "menu.view.theme": "Thème",
            "menu.view.language": "Langue",
            "menu.view.zoom_in": "Zoom avant",
            "menu.view.zoom_out": "Zoom arrière",
            "menu.view.fit_to_window": "Ajuster à la fenêtre",
            
            # Dialogues
            "dialog.new_dataset.title": "Créer un nouveau dataset",
            "dialog.new_dataset.name": "Nom du dataset",
            "dialog.new_dataset.description": "Description",
            "dialog.new_dataset.path": "Chemin de stockage",
            "dialog.new_dataset.classes": "Classes",
            "dialog.new_dataset.create": "Créer",
            "dialog.new_dataset.cancel": "Annuler",
            
            "dialog.mapillary.title": "Import depuis Mapillary",
            "dialog.mapillary.region": "Sélection de région",
            "dialog.mapillary.cities": "Villes",
            "dialog.mapillary.roads": "Axes routiers",
            "dialog.mapillary.landmarks": "Points d'intérêt",
            "dialog.mapillary.manual": "Coordonnées manuelles",
            "dialog.mapillary.radius": "Rayon (km)",
            "dialog.mapillary.max_images": "Nombre max d'images",
            "dialog.mapillary.preview": "Prévisualiser",
            "dialog.mapillary.import": "Importer",
            
            "dialog.preferences.title": "Préférences",
            "dialog.preferences.general": "Général",
            "dialog.preferences.language": "Langue",
            "dialog.preferences.theme": "Thème",
            "dialog.preferences.mapillary": "Mapillary",
            "dialog.preferences.api_key": "Clé API",
            "dialog.preferences.cache": "Cache",
            "dialog.preferences.clear_cache": "Vider le cache",
            
            # Boutons communs
            "button.ok": "OK",
            "button.cancel": "Annuler",
            "button.apply": "Appliquer",
            "button.close": "Fermer",
            "button.save": "Sauvegarder",
            "button.open": "Ouvrir",
            "button.browse": "Parcourir",
            "button.delete": "Supprimer",
            "button.edit": "Modifier",
            "button.add": "Ajouter",
            "button.remove": "Retirer",
            
            # Messages d'état
            "status.ready": "Prêt",
            "status.loading": "Chargement...",
            "status.saving": "Sauvegarde...",
            "status.importing": "Import en cours...",
            "status.exporting": "Export en cours...",
            "status.processing": "Traitement...",
            
            # Messages d'erreur
            "error.title": "Erreur",
            "error.file_not_found": "Fichier non trouvé",
            "error.invalid_format": "Format invalide",
            "error.network": "Erreur réseau",
            "error.api": "Erreur API",
            "error.permission": "Permissions insuffisantes",
            "error.unknown": "Erreur inconnue",
            
            # Formats d'export
            "export.format.yolo": "Format YOLO",
            "export.format.coco": "Format COCO",
            "export.format.voc": "Format Pascal VOC",
            
            # Statistiques
            "stats.total_images": "Total d'images",
            "stats.total_annotations": "Total d'annotations",
            "stats.classes_count": "Nombre de classes",
            "stats.avg_annotations": "Annotations par image",
            
            # Thèmes
            "theme.light": "Clair",
            "theme.dark": "Sombre",
            
            # Langues
            "language.french": "Français",
            "language.english": "English",
            
            # Vue dataset
            "view.dataset.add_images": "Ajouter images",
            "view.dataset.export": "Exporter",
            "view.dataset.validate": "Valider",
            "view.dataset.save": "Sauvegarder",
            "view.dataset.edit_annotations": "Modifier annotations",
            "view.dataset.delete_image": "Supprimer image",
            "view.dataset.statistics": "Statistiques",
            "view.dataset.total_images": "Total images: {0}",
            "view.dataset.total_annotations": "Total annotations: {0}",
            "view.dataset.classes": "Classes: {0}",
            "view.dataset.visualization": "Visualisation",
            "view.dataset.view_mode": "Mode vue",
            "view.dataset.create_mode": "Mode création",
            "view.dataset.edit_mode": "Mode édition",
            "view.dataset.details": "Détails",
            "view.dataset.metadata": "Métadonnées",
            "view.dataset.view_metadata": "Voir métadonnées",
            "view.dataset.annotations": "Annotations",
            "view.dataset.delete_annotation": "Supprimer annotation",
            
            # Vue dashboard
            "view.dashboard.title": "Tableau de bord",
            "view.dashboard.welcome": "Bienvenue dans YOLO Dataset Manager",
            "view.dashboard.statistics": "Statistiques",
            "view.dashboard.total_datasets": "Datasets",
            "view.dashboard.total_images": "Images",
            "view.dashboard.total_annotations": "Annotations",
            "view.dashboard.storage_used": "Stockage",
            "view.dashboard.quick_actions": "Actions rapides",
            "view.dashboard.create_dataset": "Créer Dataset",
            "view.dashboard.import_data": "Importer données",
            "view.dashboard.open_dataset": "Ouvrir Dataset",
            "view.dashboard.recent_datasets": "Datasets récents",
            "view.dashboard.no_datasets": "Aucun dataset trouvé",
            "view.dashboard.datasets_management": "Gestion des datasets",
            "view.dashboard.refresh": "Actualiser",
            "view.dashboard.delete_dataset": "Supprimer dataset",
            "view.dashboard.info": "Information",
            "view.dashboard.select_dataset_to_delete": "Veuillez sélectionner un dataset à supprimer",
            "view.dashboard.confirm_delete": "Confirmer la suppression",
            "view.dashboard.confirm_delete_message": "Êtes-vous sûr de vouloir supprimer le dataset '{0}' ?\n\nCette action est irréversible et supprimera toutes les images et annotations associées.",
            "view.dashboard.success": "Succès",
            "view.dashboard.dataset_deleted": "Dataset '{0}' supprimé avec succès",
            "view.dashboard.delete_error": "Erreur lors de la suppression: {0}",
            
            # Composants
            "component.image_viewer.class_label": "Classe",
            "component.image_viewer.zoom_in": "Zoom +",
            "component.image_viewer.zoom_out": "Zoom -", 
            "component.image_viewer.reset_zoom": "Reset zoom",
            "component.image_viewer.ready": "Prêt",
            "component.image_viewer.create_mode": "Mode création d'annotation",
            "component.image_viewer.edit_mode": "Mode édition d'annotation",
            "component.image_viewer.view_mode": "Mode visualisation",
            
            # Dialogues Import
            "dialog.import.title": "Importer des images",
            "dialog.import.source_group": "Source",
            "dialog.import.source_path": "Dossier source",
            "dialog.import.include_subfolders": "Inclure les sous-dossiers",
            "dialog.import.copy_files": "Copier les fichiers",
            "dialog.import.destination_group": "Destination",
            "dialog.import.dataset_name": "Nom du dataset",
            "dialog.import.destination_path": "Dossier de destination",
            "dialog.import.start_import": "Démarrer l'import",
            "dialog.import.select_source": "Sélectionner le dossier source",
            "dialog.import.select_destination": "Sélectionner le dossier de destination",
            "dialog.import.error": "Erreur d'import",
            "dialog.import.no_source": "Veuillez sélectionner un dossier source",
            "dialog.import.source_not_exists": "Le dossier source n'existe pas",
            "dialog.import.no_dataset_name": "Veuillez saisir un nom de dataset",
            "dialog.import.success_title": "Import réussi",
            "dialog.import.success": "{0} images importées avec succès",
            "dialog.import.cancel_title": "Annuler l'import",
            "dialog.import.cancel_message": "Êtes-vous sûr de vouloir annuler l'import ?",
            "dialog.import.scanning": "Analyse en cours...",
            "dialog.import.processing": "Traitement de",
            
            # Dialogues Mapillary
            "dialog.mapillary.title": "Import depuis Mapillary",
            "dialog.mapillary.region": "Sélection de région",
            "dialog.mapillary.select_city": "Sélectionner une ville",
            "dialog.mapillary.cities": "Villes",
            "dialog.mapillary.radius": "Rayon (km)",
            "dialog.mapillary.select_road": "Sélectionner un axe routier",
            "dialog.mapillary.roads": "Axes routiers",
            "dialog.mapillary.portion": "Portion (km)",
            "dialog.mapillary.corridor_width": "Largeur corridor (m)",
            "dialog.mapillary.select_landmark": "Sélectionner un point d'intérêt",
            "dialog.mapillary.landmarks": "Points d'intérêt",
            "dialog.mapillary.landmark_radius": "Rayon (km)",
            "dialog.mapillary.min_lat": "Latitude min",
            "dialog.mapillary.max_lat": "Latitude max",
            "dialog.mapillary.min_lon": "Longitude min",
            "dialog.mapillary.max_lon": "Longitude max",
            "dialog.mapillary.import_options": "Options d'import",
            "dialog.mapillary.max_images": "Nombre max d'images",
            "dialog.mapillary.preview": "Prévisualiser",
            "dialog.mapillary.available_images": "Images disponibles",
            "dialog.mapillary.import": "Importer",
            "dialog.mapillary.select_city_error": "Veuillez sélectionner une ville",
            
            # Dialogue Export
            "dialog.export.title": "Exporter le dataset",
            "dialog.export.dataset_info": "Informations du dataset",
            "dialog.export.dataset_name": "Nom",
            "dialog.export.image_count": "Images",
            "dialog.export.annotation_count": "Annotations",
            "dialog.export.classes_count": "Classes",
            "dialog.export.format_tab": "Format",
            "dialog.export.options_tab": "Options",
            "dialog.export.advanced_tab": "Avancé",
            "dialog.export.format": "Format d'export",
            "dialog.export.output_path": "Répertoire de sortie",
            "dialog.export.select_output": "Sélectionner le répertoire de sortie",
            "dialog.export.dataset_split": "Division du dataset",
            "dialog.export.train_ratio": "Ratio d'entraînement",
            "dialog.export.val_ratio": "Ratio de validation",
            "dialog.export.test_ratio": "Ratio de test",
            "dialog.export.include_images": "Inclure les images",
            "dialog.export.compress_output": "Compresser la sortie",
            "dialog.export.format_specific": "Options spécifiques au format",
            "dialog.export.create_data_yaml": "Créer data.yaml (YOLO)",
            "dialog.export.create_imagesets": "Créer ImageSets (VOC)",
            "dialog.export.export_notes": "Notes d'export",
            "dialog.export.start_export": "Démarrer l'export",
            "dialog.export.exporting": "Export en cours...",
            "dialog.export.error": "Erreur d'export",
            "dialog.export.no_output_path": "Veuillez sélectionner un répertoire de sortie",
            "dialog.export.invalid_ratios": "La somme des ratios doit être égale à 1.0",
            "dialog.export.success_title": "Export réussi",
            "dialog.export.success_message": "Dataset exporté avec succès vers:\n{0}",
            "dialog.export.export_failed": "Échec de l'export: {0}"
        }
        
        # Traductions anglaises
        en_translations = {
            # Fenêtre principale
            "main_window.title": "YOLO Dataset Manager",
            "main_window.file": "File",
            "main_window.edit": "Edit",
            "main_window.view": "View",
            "main_window.tools": "Tools",
            "main_window.help": "Help",
            "main_window.dashboard": "Dashboard",
            "main_window.dataset": "Dataset",
            
            # Menu Fichier
            "menu.file.new_dataset": "New Dataset",
            "menu.file.open_dataset": "Open Dataset",
            "menu.file.save_dataset": "Save Dataset",
            "menu.file.import_mapillary": "Import from Mapillary",
            "menu.file.import_local": "Import Local Files",
            "menu.file.export": "Export",
            "menu.file.preferences": "Preferences",
            "menu.file.quit": "Quit",
            
            # Menu Édition
            "menu.edit.undo": "Undo",
            "menu.edit.redo": "Redo",
            "menu.edit.cut": "Cut",
            "menu.edit.copy": "Copy",
            "menu.edit.paste": "Paste",
            "menu.edit.select_all": "Select All",
            
            # Menu Affichage
            "menu.view.theme": "Theme",
            "menu.view.language": "Language",
            "menu.view.zoom_in": "Zoom In",
            "menu.view.zoom_out": "Zoom Out",
            "menu.view.fit_to_window": "Fit to Window",
            
            # Dialogues
            "dialog.new_dataset.title": "Create New Dataset",
            "dialog.new_dataset.name": "Dataset Name",
            "dialog.new_dataset.description": "Description",
            "dialog.new_dataset.path": "Storage Path",
            "dialog.new_dataset.classes": "Classes",
            "dialog.new_dataset.create": "Create",
            "dialog.new_dataset.cancel": "Cancel",
            
            "dialog.mapillary.title": "Import from Mapillary",
            "dialog.mapillary.region": "Region Selection",
            "dialog.mapillary.cities": "Cities",
            "dialog.mapillary.roads": "Roads",
            "dialog.mapillary.landmarks": "Landmarks",
            "dialog.mapillary.manual": "Manual Coordinates",
            "dialog.mapillary.radius": "Radius (km)",
            "dialog.mapillary.max_images": "Max Images",
            "dialog.mapillary.preview": "Preview",
            "dialog.mapillary.import": "Import",
            
            "dialog.preferences.title": "Preferences",
            "dialog.preferences.general": "General",
            "dialog.preferences.language": "Language",
            "dialog.preferences.theme": "Theme",
            "dialog.preferences.mapillary": "Mapillary",
            "dialog.preferences.api_key": "API Key",
            "dialog.preferences.cache": "Cache",
            "dialog.preferences.clear_cache": "Clear Cache",
            
            # Boutons communs
            "button.ok": "OK",
            "button.cancel": "Cancel",
            "button.apply": "Apply",
            "button.close": "Close",
            "button.save": "Save",
            "button.open": "Open",
            "button.browse": "Browse",
            "button.delete": "Delete",
            "button.edit": "Edit",
            "button.add": "Add",
            "button.remove": "Remove",
            
            # Messages d'état
            "status.ready": "Ready",
            "status.loading": "Loading...",
            "status.saving": "Saving...",
            "status.importing": "Importing...",
            "status.exporting": "Exporting...",
            "status.processing": "Processing...",
            
            # Messages d'erreur
            "error.title": "Error",
            "error.file_not_found": "File not found",
            "error.invalid_format": "Invalid format",
            "error.network": "Network error",
            "error.api": "API error",
            "error.permission": "Insufficient permissions",
            "error.unknown": "Unknown error",
            
            # Formats d'export
            "export.format.yolo": "YOLO Format",
            "export.format.coco": "COCO Format",
            "export.format.voc": "Pascal VOC Format",
            
            # Statistiques
            "stats.total_images": "Total Images",
            "stats.total_annotations": "Total Annotations",
            "stats.classes_count": "Number of Classes",
            "stats.avg_annotations": "Annotations per Image",
            
            # Thèmes
            "theme.light": "Light",
            "theme.dark": "Dark",
            
            # Langues
            "language.french": "Français",
            "language.english": "English",
            
            # Vue dataset
            "view.dataset.add_images": "Add images",
            "view.dataset.export": "Export",
            "view.dataset.validate": "Validate",
            "view.dataset.save": "Save",
            "view.dataset.edit_annotations": "Edit annotations",
            "view.dataset.delete_image": "Delete image",
            "view.dataset.statistics": "Statistics",
            "view.dataset.total_images": "Total images: {0}",
            "view.dataset.total_annotations": "Total annotations: {0}",
            "view.dataset.classes": "Classes: {0}",
            "view.dataset.visualization": "Visualization",
            "view.dataset.view_mode": "View mode",
            "view.dataset.create_mode": "Create mode",
            "view.dataset.edit_mode": "Edit mode",
            "view.dataset.details": "Details",
            "view.dataset.metadata": "Metadata",
            "view.dataset.view_metadata": "View metadata",
            "view.dataset.annotations": "Annotations",
            "view.dataset.delete_annotation": "Delete annotation",
            
            # Vue dashboard
            "view.dashboard.title": "Dashboard",
            "view.dashboard.welcome": "Welcome to YOLO Dataset Manager",
            "view.dashboard.statistics": "Statistics",
            "view.dashboard.total_datasets": "Datasets",
            "view.dashboard.total_images": "Images",
            "view.dashboard.total_annotations": "Annotations",
            "view.dashboard.storage_used": "Storage",
            "view.dashboard.quick_actions": "Quick actions",
            "view.dashboard.create_dataset": "Create Dataset",
            "view.dashboard.import_data": "Import data",
            "view.dashboard.open_dataset": "Open Dataset",
            "view.dashboard.recent_datasets": "Recent datasets",
            "view.dashboard.no_datasets": "No datasets found",
            "view.dashboard.datasets_management": "Dataset management",
            "view.dashboard.refresh": "Refresh",
            "view.dashboard.delete_dataset": "Delete dataset",
            "view.dashboard.info": "Information",
            "view.dashboard.select_dataset_to_delete": "Please select a dataset to delete",
            "view.dashboard.confirm_delete": "Confirm deletion",
            "view.dashboard.confirm_delete_message": "Are you sure you want to delete the dataset '{0}'?\n\nThis action is irreversible and will delete all associated images and annotations.",
            "view.dashboard.success": "Success",
            "view.dashboard.dataset_deleted": "Dataset '{0}' deleted successfully",
            "view.dashboard.delete_error": "Error during deletion: {0}",
            
            # Composants
            "component.image_viewer.class_label": "Class",
            "component.image_viewer.zoom_in": "Zoom +",
            "component.image_viewer.zoom_out": "Zoom -", 
            "component.image_viewer.reset_zoom": "Reset zoom",
            "component.image_viewer.ready": "Ready",
            "component.image_viewer.create_mode": "Annotation creation mode",
            "component.image_viewer.edit_mode": "Annotation edit mode",
            "component.image_viewer.view_mode": "View mode",
            
            # Dialogues Import
            "dialog.import.title": "Import images",
            "dialog.import.source_group": "Source",
            "dialog.import.source_path": "Source folder",
            "dialog.import.include_subfolders": "Include subfolders",
            "dialog.import.copy_files": "Copy files",
            "dialog.import.destination_group": "Destination",
            "dialog.import.dataset_name": "Dataset name",
            "dialog.import.destination_path": "Destination folder",
            "dialog.import.start_import": "Start import",
            "dialog.import.select_source": "Select source folder",
            "dialog.import.select_destination": "Select destination folder",
            "dialog.import.error": "Import error",
            "dialog.import.no_source": "Please select a source folder",
            "dialog.import.source_not_exists": "Source folder does not exist",
            "dialog.import.no_dataset_name": "Please enter a dataset name",
            "dialog.import.success_title": "Import successful",
            "dialog.import.success": "{0} images imported successfully",
            "dialog.import.cancel_title": "Cancel import",
            "dialog.import.cancel_message": "Are you sure you want to cancel the import?",
            "dialog.import.scanning": "Scanning...",
            "dialog.import.processing": "Processing",
            
            # Dialogues Mapillary
            "dialog.mapillary.title": "Import from Mapillary",
            "dialog.mapillary.region": "Region selection",
            "dialog.mapillary.select_city": "Select a city",
            "dialog.mapillary.cities": "Cities",
            "dialog.mapillary.radius": "Radius (km)",
            "dialog.mapillary.select_road": "Select a road",
            "dialog.mapillary.roads": "Roads",
            "dialog.mapillary.portion": "Portion (km)",
            "dialog.mapillary.corridor_width": "Corridor width (m)",
            "dialog.mapillary.select_landmark": "Select a landmark",
            "dialog.mapillary.landmarks": "Landmarks",
            "dialog.mapillary.landmark_radius": "Radius (km)",
            "dialog.mapillary.min_lat": "Min latitude",
            "dialog.mapillary.max_lat": "Max latitude",
            "dialog.mapillary.min_lon": "Min longitude",
            "dialog.mapillary.max_lon": "Max longitude",
            "dialog.mapillary.import_options": "Import options",
            "dialog.mapillary.max_images": "Max images",
            "dialog.mapillary.preview": "Preview",
            "dialog.mapillary.available_images": "Available images",
            "dialog.mapillary.import": "Import",
            "dialog.mapillary.select_city_error": "Please select a city",
            
            # Dialogue Export
            "dialog.export.title": "Export Dataset",
            "dialog.export.dataset_info": "Dataset Information",
            "dialog.export.dataset_name": "Name",
            "dialog.export.image_count": "Images",
            "dialog.export.annotation_count": "Annotations",
            "dialog.export.classes_count": "Classes",
            "dialog.export.format_tab": "Format",
            "dialog.export.options_tab": "Options",
            "dialog.export.advanced_tab": "Advanced",
            "dialog.export.format": "Export Format",
            "dialog.export.output_path": "Output Directory",
            "dialog.export.select_output": "Select Output Directory",
            "dialog.export.dataset_split": "Dataset Split",
            "dialog.export.train_ratio": "Training Ratio",
            "dialog.export.val_ratio": "Validation Ratio",
            "dialog.export.test_ratio": "Test Ratio",
            "dialog.export.include_images": "Include Images",
            "dialog.export.compress_output": "Compress Output",
            "dialog.export.format_specific": "Format-Specific Options",
            "dialog.export.create_data_yaml": "Create data.yaml (YOLO)",
            "dialog.export.create_imagesets": "Create ImageSets (VOC)",
            "dialog.export.export_notes": "Export Notes",
            "dialog.export.start_export": "Start Export",
            "dialog.export.exporting": "Exporting...",
            "dialog.export.error": "Export Error",
            "dialog.export.no_output_path": "Please select an output directory",
            "dialog.export.invalid_ratios": "Sum of ratios must equal 1.0",
            "dialog.export.success_title": "Export Successful",
            "dialog.export.success_message": "Dataset exported successfully to:\n{0}",
            "dialog.export.export_failed": "Export failed: {0}"
        }
        
        # Sauvegarder les fichiers
        try:
            with open(self.translations_dir / "fr.json", 'w', encoding='utf-8') as f:
                json.dump(fr_translations, f, indent=2, ensure_ascii=False)
            
            with open(self.translations_dir / "en.json", 'w', encoding='utf-8') as f:
                json.dump(en_translations, f, indent=2, ensure_ascii=False)
            
            # Charger en mémoire
            self.translations["fr"] = fr_translations
            self.translations["en"] = en_translations
            
        except Exception as e:
            print(f"Erreur lors de la création des fichiers de traduction: {e}")
    
    def _create_fallback_translations(self):
        """Crée des traductions de secours en cas d'erreur."""
        self.translations = {
            "fr": {"error.title": "Erreur", "button.ok": "OK"},
            "en": {"error.title": "Error", "button.ok": "OK"}
        }
    
    def get_available_languages(self) -> Dict[str, str]:
        """Retourne la liste des langues disponibles."""
        return {
            "fr": self.tr("language.french"),
            "en": self.tr("language.english")
        }
    
    def set_language(self, language_code: str):
        """
        Change la langue actuelle.
        
        Args:
            language_code: Code de langue ("fr" ou "en")
        """
        if language_code in self.translations:
            old_language = self.current_language
            self.current_language = language_code
            if old_language != language_code:
                print(f"Changement de langue: {old_language} → {language_code}")
                self.language_changed.emit(language_code)
        else:
            print(f"Langue non supportée: {language_code}")
    
    def get_current_language(self) -> str:
        """Retourne le code de la langue actuelle."""
        return self.current_language
    
    def tr(self, key: str, *args) -> str:
        """
        Traduit une clé dans la langue actuelle.
        
        Args:
            key: Clé de traduction (ex: "menu.file.open")
            *args: Arguments optionnels pour le formatage
            
        Returns:
            Texte traduit
        """
        # Essayer avec la langue actuelle
        if (self.current_language in self.translations and 
            key in self.translations[self.current_language]):
            text = self.translations[self.current_language][key]
        # Fallback sur la langue de secours
        elif (self.fallback_language in self.translations and 
              key in self.translations[self.fallback_language]):
            text = self.translations[self.fallback_language][key]
        # Dernière option : retourner la clé
        else:
            return key
        
        # Appliquer le formatage si des arguments sont fournis
        if args:
            try:
                return text.format(*args)
            except:
                return text
        
        return text

# Instance globale du gestionnaire de traductions
_translation_manager = None

def get_translation_manager() -> TranslationManager:
    """Retourne l'instance globale du gestionnaire de traductions."""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager

def tr(key: str, *args) -> str:
    """
    Fonction de traduction globale.
    
    Args:
        key: Clé de traduction
        *args: Arguments optionnels
        
    Returns:
        Texte traduit
    """
    return get_translation_manager().tr(key, *args)

def set_language(language_code: str):
    """Change la langue globalement."""
    tm = get_translation_manager()
    print(f"🌐 Changement global de langue vers: {language_code}")
    tm.set_language(language_code)

def get_current_language() -> str:
    """Retourne la langue actuelle."""
    return get_translation_manager().get_current_language()