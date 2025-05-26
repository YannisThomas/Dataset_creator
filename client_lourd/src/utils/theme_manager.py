# src/utils/theme_manager.py

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Optional
import json
from pathlib import Path

from src.utils.logger import Logger

class ThemeManager(QObject):
    """
    Gestionnaire de thèmes pour l'application.
    Gère le basculement entre thème clair et sombre.
    """
    
    # Signal émis lors du changement de thème
    theme_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = Logger()
        self.current_theme = "light"
        self.themes = {}
        self.load_themes()
        
    def load_themes(self):
        """Charge les définitions de thèmes depuis les fichiers de configuration."""
        try:
            # Définir les thèmes intégrés
            self.themes = {
                "light": self._get_light_theme(),
                "dark": self._get_dark_theme()
            }
            
            # Essayer de charger des thèmes personnalisés depuis un fichier
            themes_file = Path("src/config/themes.json")
            if themes_file.exists():
                with open(themes_file, 'r', encoding='utf-8') as f:
                    custom_themes = json.load(f)
                    self.themes.update(custom_themes)
                    
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des thèmes: {e}")
            # Utiliser les thèmes par défaut
            self.themes = {
                "light": self._get_light_theme(),
                "dark": self._get_dark_theme()
            }
    
    def _get_light_theme(self) -> Dict[str, str]:
        """Retourne la définition du thème clair."""
        return {
            "name": "Clair",
            "background": "#ffffff",
            "background_secondary": "#f5f5f5",
            "background_hover": "#e6e6e6",
            "background_selected": "#0078d4",
            "text": "#000000",
            "text_secondary": "#666666",
            "text_disabled": "#999999",
            "text_selected": "#ffffff",
            "border": "#cccccc",
            "border_focus": "#0078d4",
            "button_background": "#f0f0f0",
            "button_background_hover": "#e1e1e1",
            "button_background_pressed": "#d2d2d2",
            "button_primary": "#0078d4",
            "button_primary_hover": "#106ebe",
            "button_primary_pressed": "#005a9e",
            "input_background": "#ffffff",
            "input_border": "#cccccc",
            "input_border_focus": "#0078d4",
            "scrollbar": "#cccccc",
            "scrollbar_hover": "#999999",
            "success": "#107c10",
            "warning": "#ff8c00",
            "error": "#d13438",
            "info": "#0078d4"
        }
    
    def _get_dark_theme(self) -> Dict[str, str]:
        """Retourne la définition du thème sombre."""
        return {
            "name": "Sombre",
            "background": "#2b2b2b",
            "background_secondary": "#323232",
            "background_hover": "#404040",
            "background_selected": "#0e639c",
            "text": "#ffffff",
            "text_secondary": "#cccccc",
            "text_disabled": "#888888",
            "text_selected": "#ffffff",
            "border": "#555555",
            "border_focus": "#0e639c",
            "button_background": "#404040",
            "button_background_hover": "#4a4a4a",
            "button_background_pressed": "#555555",
            "button_primary": "#0e639c",
            "button_primary_hover": "#1177bb",
            "button_primary_pressed": "#0d5085",
            "input_background": "#404040",
            "input_border": "#555555",
            "input_border_focus": "#0e639c",
            "scrollbar": "#555555",
            "scrollbar_hover": "#777777",
            "success": "#6bb700",
            "warning": "#ffb900",
            "error": "#ff5757",
            "info": "#60cdff"
        }
    
    def get_available_themes(self) -> Dict[str, str]:
        """
        Retourne la liste des thèmes disponibles.
        
        Returns:
            Dictionnaire {theme_id: theme_name}
        """
        return {theme_id: theme_data["name"] for theme_id, theme_data in self.themes.items()}
    
    def get_current_theme(self) -> str:
        """
        Retourne l'ID du thème actuel.
        
        Returns:
            ID du thème actuel
        """
        return self.current_theme
    
    def set_theme(self, theme_id: str):
        """
        Applique un thème à l'application.
        
        Args:
            theme_id: ID du thème à appliquer
        """
        if theme_id not in self.themes:
            self.logger.warning(f"Thème inconnu: {theme_id}")
            return
            
        try:
            self.current_theme = theme_id
            theme_data = self.themes[theme_id]
            
            # Générer et appliquer le stylesheet
            stylesheet = self._generate_stylesheet(theme_data)
            
            app = QApplication.instance()
            if app:
                app.setStyleSheet(stylesheet)
                
            # Émettre le signal de changement
            self.theme_changed.emit(theme_id)
            
            self.logger.info(f"Thème appliqué: {theme_data['name']}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'application du thème {theme_id}: {e}")
    
    def _generate_stylesheet(self, theme: Dict[str, str]) -> str:
        """
        Génère le stylesheet QSS à partir des données du thème.
        
        Args:
            theme: Données du thème
            
        Returns:
            Stylesheet QSS
        """
        return f"""
        /* Style général de l'application */
        QWidget {{
            background-color: {theme['background']};
            color: {theme['text']};
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 9pt;
        }}
        
        /* Fenêtres principales */
        QMainWindow {{
            background-color: {theme['background']};
        }}
        
        /* Boutons */
        QPushButton {{
            background-color: {theme['button_background']};
            border: 1px solid {theme['border']};
            border-radius: 4px;
            padding: 6px 12px;
            color: {theme['text']};
            min-height: 18px;
        }}
        
        QPushButton:hover {{
            background-color: {theme['button_background_hover']};
            border-color: {theme['border_focus']};
        }}
        
        QPushButton:pressed {{
            background-color: {theme['button_background_pressed']};
        }}
        
        QPushButton:disabled {{
            color: {theme['text_disabled']};
            background-color: {theme['background_secondary']};
        }}
        
        /* Boutons primaires */
        QPushButton[primary="true"] {{
            background-color: {theme['button_primary']};
            color: {theme['text_selected']};
            border-color: {theme['button_primary']};
        }}
        
        QPushButton[primary="true"]:hover {{
            background-color: {theme['button_primary_hover']};
        }}
        
        QPushButton[primary="true"]:pressed {{
            background-color: {theme['button_primary_pressed']};
        }}
        
        /* Champs de saisie */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {theme['input_background']};
            border: 1px solid {theme['input_border']};
            border-radius: 4px;
            padding: 4px 8px;
            color: {theme['text']};
            selection-background-color: {theme['background_selected']};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {theme['input_border_focus']};
        }}
        
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
            background-color: {theme['background_secondary']};
            color: {theme['text_disabled']};
        }}
        
        /* SpinBox et ComboBox */
        QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {theme['input_background']};
            border: 1px solid {theme['input_border']};
            border-radius: 4px;
            padding: 4px 8px;
            color: {theme['text']};
            min-height: 18px;
        }}
        
        QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border-color: {theme['input_border_focus']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 4px solid {theme['text']};
            margin-right: 6px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {theme['input_background']};
            border: 1px solid {theme['border']};
            selection-background-color: {theme['background_selected']};
            selection-color: {theme['text_selected']};
        }}
        
        /* Listes */
        QListWidget, QTreeWidget, QTableWidget {{
            background-color: {theme['input_background']};
            border: 1px solid {theme['border']};
            alternate-background-color: {theme['background_secondary']};
            color: {theme['text']};
        }}
        
        QListWidget::item, QTreeWidget::item, QTableWidget::item {{
            padding: 4px;
            border-bottom: 1px solid {theme['background_secondary']};
        }}
        
        QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {{
            background-color: {theme['background_selected']};
            color: {theme['text_selected']};
        }}
        
        QListWidget::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover {{
            background-color: {theme['background_hover']};
        }}
        
        /* GroupBox */
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {theme['border']};
            border-radius: 6px;
            margin: 6px 0px;
            padding-top: 12px;
            background-color: {theme['background_secondary']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px 0 4px;
            color: {theme['text']};
            background-color: {theme['background_secondary']};
        }}
        
        /* Onglets */
        QTabWidget::pane {{
            border: 1px solid {theme['border']};
            background-color: {theme['background']};
        }}
        
        QTabBar::tab {{
            background-color: {theme['background_secondary']};
            border: 1px solid {theme['border']};
            padding: 6px 12px;
            margin-right: 2px;
            color: {theme['text']};
        }}
        
        QTabBar::tab:selected {{
            background-color: {theme['background']};
            border-bottom: 1px solid {theme['background']};
        }}
        
        QTabBar::tab:hover {{
            background-color: {theme['background_hover']};
        }}
        
        /* Barres de défilement */
        QScrollBar:vertical {{
            background-color: {theme['background_secondary']};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {theme['scrollbar']};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {theme['scrollbar_hover']};
        }}
        
        QScrollBar:horizontal {{
            background-color: {theme['background_secondary']};
            height: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {theme['scrollbar']};
            border-radius: 6px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {theme['scrollbar_hover']};
        }}
        
        QScrollBar::add-line, QScrollBar::sub-line {{
            border: none;
            background: none;
        }}
        
        /* Sliders */
        QSlider::groove:horizontal {{
            border: 1px solid {theme['border']};
            height: 6px;
            background: {theme['background_secondary']};
            border-radius: 3px;
        }}
        
        QSlider::handle:horizontal {{
            background: {theme['button_primary']};
            border: 1px solid {theme['border_focus']};
            width: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background: {theme['button_primary_hover']};
        }}
        
        /* CheckBox et RadioButton */
        QCheckBox, QRadioButton {{
            color: {theme['text']};
            spacing: 6px;
        }}
        
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
        }}
        
        QCheckBox::indicator:unchecked {{
            border: 1px solid {theme['border']};
            background-color: {theme['input_background']};
            border-radius: 2px;
        }}
        
        QCheckBox::indicator:checked {{
            border: 1px solid {theme['button_primary']};
            background-color: {theme['button_primary']};
            border-radius: 2px;
        }}
        
        /* Barres de progression */
        QProgressBar {{
            border: 1px solid {theme['border']};
            border-radius: 4px;
            text-align: center;
            background-color: {theme['background_secondary']};
            color: {theme['text']};
        }}
        
        QProgressBar::chunk {{
            background-color: {theme['button_primary']};
            border-radius: 3px;
        }}
        
        /* Barres de statut */
        QStatusBar {{
            background-color: {theme['background_secondary']};
            border-top: 1px solid {theme['border']};
            color: {theme['text']};
        }}
        
        /* Menus */
        QMenuBar {{
            background-color: {theme['background']};
            border-bottom: 1px solid {theme['border']};
            color: {theme['text']};
        }}
        
        QMenuBar::item {{
            padding: 4px 8px;
            background: transparent;
        }}
        
        QMenuBar::item:selected {{
            background-color: {theme['background_hover']};
        }}
        
        QMenu {{
            background-color: {theme['background']};
            border: 1px solid {theme['border']};
            color: {theme['text']};
        }}
        
        QMenu::item {{
            padding: 6px 16px;
        }}
        
        QMenu::item:selected {{
            background-color: {theme['background_selected']};
            color: {theme['text_selected']};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {theme['border']};
            margin: 4px 8px;
        }}
        
        /* Barres d'outils */
        QToolBar {{
            background-color: {theme['background_secondary']};
            border: 1px solid {theme['border']};
            spacing: 2px;
            padding: 2px;
        }}
        
        QToolButton {{
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 4px;
        }}
        
        QToolButton:hover {{
            background-color: {theme['background_hover']};
            border-color: {theme['border']};
        }}
        
        QToolButton:pressed {{
            background-color: {theme['background_selected']};
        }}
        
        /* Dialogues */
        QDialog {{
            background-color: {theme['background']};
        }}
        
        /* Messages spéciaux */
        .success {{
            color: {theme['success']};
        }}
        
        .warning {{
            color: {theme['warning']};
        }}
        
        .error {{
            color: {theme['error']};
        }}
        
        .info {{
            color: {theme['info']};
        }}
        """
    
    def toggle_theme(self):
        """Bascule entre thème clair et sombre."""
        if self.current_theme == "light":
            self.set_theme("dark")
        else:
            self.set_theme("light")
    
    def get_theme_data(self, theme_id: str) -> Optional[Dict[str, str]]:
        """
        Retourne les données d'un thème spécifique.
        
        Args:
            theme_id: ID du thème
            
        Returns:
            Données du thème ou None si non trouvé
        """
        return self.themes.get(theme_id)

# Instance globale du gestionnaire de thèmes
_theme_manager = None

def get_theme_manager() -> ThemeManager:
    """
    Retourne l'instance globale du gestionnaire de thèmes.
    
    Returns:
        Instance du ThemeManager
    """
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager