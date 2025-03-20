# src/utils/theme_manager.py

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt
from pathlib import Path
import json
import os

from src.utils.logger import Logger

class ThemeManager:
    """
    Gestionnaire de thèmes pour l'application.
    Permet de charger et d'appliquer différents thèmes à l'interface utilisateur.
    """
    
    # Thèmes disponibles
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
    
    def __init__(
        self, 
        config_manager=None, 
        logger=None
    ):
        """
        Initialise le gestionnaire de thèmes.
        
        Args:
            config_manager: Gestionnaire de configuration (optionnel)
            logger: Logger pour les messages de débogage (optionnel)
        """
        self.logger = logger or Logger()
        self.config_manager = config_manager
        self.current_theme = self.LIGHT
        self.custom_stylesheets = {}
        
        # Charger les thèmes disponibles
        self._load_themes()
        
        # Appliquer le thème par défaut (à partir de la configuration)
        if self.config_manager:
            try:
                config = self.config_manager.get_config()
                self.current_theme = config.ui.theme
            except Exception as e:
                self.logger.warning(f"Impossible de charger le thème depuis la configuration: {e}")
        
    def _load_themes(self):
        """Charge les thèmes disponibles depuis les fichiers CSS."""
        try:
            # Chemins possibles pour les thèmes
            theme_paths = [
                Path("src/styles"),
                Path("client_lourd/src/styles"),
                Path("styles")
            ]
            
            # Trouver le premier chemin existant
            base_path = None
            for path in theme_paths:
                if path.exists():
                    base_path = path
                    break
            
            if not base_path:
                # Créer le répertoire s'il n'existe pas
                base_path = Path("src/styles")
                base_path.mkdir(parents=True, exist_ok=True)
                self.logger.warning(f"Répertoire de thèmes créé: {base_path}")
            
            # Chercher les fichiers de thème
            theme_files = list(base_path.glob("*.qss"))
            
            if not theme_files:
                # Créer des thèmes par défaut si aucun n'existe
                self._create_default_themes(base_path)
                theme_files = list(base_path.glob("*.qss"))
            
            # Charger les thèmes
            for theme_file in theme_files:
                theme_name = theme_file.stem
                with open(theme_file, 'r', encoding='utf-8') as f:
                    self.custom_stylesheets[theme_name] = f.read()
                    
            self.logger.info(f"Thèmes chargés: {list(self.custom_stylesheets.keys())}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des thèmes: {e}")
            # Créer un dictionnaire de thèmes vide
            self.custom_stylesheets = {}
    
    def _create_default_themes(self, base_path: Path):
        """
        Crée des fichiers de thème par défaut.
        
        Args:
            base_path: Chemin du répertoire des thèmes
        """
        try:
            # Les contenus des thèmes restent les mêmes que dans la version précédente
            light_theme = """
            /* Thème clair pour YOLO Dataset Manager */
            QMainWindow, QDialog {
                background-color: #f0f0f0;
                color: #303030;
            }
            """
            
            dark_theme = """
            /* Thème sombre pour YOLO Dataset Manager */
            QMainWindow, QDialog {
                background-color: #303030;
                color: #e0e0e0;
            }
            """
            
            # Créer les fichiers de thème
            with open(base_path / "light.qss", 'w', encoding='utf-8') as f:
                f.write(light_theme)
                
            with open(base_path / "dark.qss", 'w', encoding='utf-8') as f:
                f.write(dark_theme)
                
            self.logger.info("Thèmes par défaut créés")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la création des thèmes par défaut: {e}")
    
    def get_available_themes(self) -> dict:
        """
        Retourne la liste des thèmes disponibles.
        
        Returns:
            Dictionnaire de thèmes {code: nom}
        """
        themes = {
            self.LIGHT: "Clair",
            self.DARK: "Sombre",
            self.SYSTEM: "Système"
        }
        
        # Ajouter les thèmes personnalisés
        for theme_name in self.custom_stylesheets.keys():
            if theme_name not in [self.LIGHT, self.DARK, self.SYSTEM]:
                themes[theme_name] = theme_name.capitalize()
                
        return themes
    
    def get_current_theme(self) -> str:
        """
        Retourne le thème actuel.
        
        Returns:
            Code du thème actuel
        """
        return self.current_theme
    
    def apply_theme(self, theme_name: str) -> bool:
        """
        Applique un thème à l'application.
        
        Args:
            theme_name: Nom du thème à appliquer
            
        Returns:
            True si le thème a été appliqué avec succès
        """
        try:
            # Récupérer l'instance de QApplication
            app = QApplication.instance()
            
            if not app:
                if self.logger:
                    self.logger.error("Aucune instance QApplication trouvée")
                return False
            
            # Appliquer le thème
            if theme_name == self.SYSTEM:
                # Utiliser le thème du système
                app.setStyle("fusion")
                app.setPalette(app.style().standardPalette())
                app.setStyleSheet("")
                
            elif theme_name in self.custom_stylesheets:
                # Utiliser le thème personnalisé
                app.setStyle("fusion")
                
                if theme_name == self.DARK:
                    # Appliquer la palette sombre
                    self._apply_dark_palette(app)
                else:
                    # Palette claire par défaut
                    app.setPalette(app.style().standardPalette())
                
                # Appliquer la feuille de style
                app.setStyleSheet(self.custom_stylesheets[theme_name])
                
            else:
                # Thème non trouvé, utiliser le thème clair par défaut
                app.setStyle("fusion")
                app.setPalette(app.style().standardPalette())
                
                if self.LIGHT in self.custom_stylesheets:
                    app.setStyleSheet(self.custom_stylesheets[self.LIGHT])
                else:
                    app.setStyleSheet("")
                    
                if self.logger:
                    self.logger.warning(f"Thème '{theme_name}' non trouvé, utilisation du thème clair")
                theme_name = self.LIGHT
            
            # Mettre à jour le thème courant
            self.current_theme = theme_name
            
            # Mettre à jour la configuration si disponible
            if self.config_manager:
                try:
                    config = self.config_manager.get_config()
                    if config.ui.theme != theme_name:
                        self.config_manager.update_config({"ui": {"theme": theme_name}})
                        if self.logger:
                            self.logger.info(f"Configuration mise à jour avec le thème: {theme_name}")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Erreur lors de la mise à jour de la configuration: {e}")
            
            if self.logger:
                self.logger.info(f"Thème appliqué: {theme_name}")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erreur lors de l'application du thème: {e}")
            return False
    
    def _apply_dark_palette(self, app):
        """
        Applique une palette de couleurs sombre à l'application.
        
        Args:
            app: Instance de QApplication
        """
        palette = QPalette()
        
        # Couleurs principales
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(48, 48, 48))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(60, 60, 60))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(80, 80, 80))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(65, 65, 65))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
        
        # Couleurs désactivées
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(128, 128, 128))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(128, 128, 128))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(128, 128, 128))
        
        app.setPalette(palette)
    
    def refresh_themes(self):
        """Recharge les thèmes disponibles."""
        self._load_themes()
        if self.current_theme:
            self.apply_theme(self.current_theme)