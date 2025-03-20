#!/usr/bin/env python3

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.views.main_window import MainWindow
from src.utils.logger import Logger
from src.utils.config import ConfigManager
from src.controllers.controller_manager import ControllerManager
from src.core.exceptions import ConfigurationError
from src.utils.app_utils import initialize_application, apply_initial_settings, setup_translation_event_filter

def main():
    """
    Point d'entrée principal de l'application.
    Utilise l'architecture MVC avec injection des contrôleurs.
    """
    try:
        # Initialiser l'application Qt en premier
        app = QApplication(sys.argv)
        
        # Initialiser les gestionnaires d'application
        logger, config_manager, theme_manager, translation_manager = initialize_application()
        logger.info("Démarrage de YOLO Dataset Manager...")

        # Initialiser le gestionnaire de contrôleurs
        controller_manager = ControllerManager(
            logger=logger, 
            config_manager=config_manager,
            theme_manager=theme_manager,
            translation_manager=translation_manager
        )
        logger.info("Contrôleurs initialisés")
        
        # Appliquer les paramètres initiaux (thème, langue)
        apply_initial_settings()
        
        # Initialiser la fenêtre principale
        window = MainWindow(
            controller_manager=controller_manager
        )
        
        # Configurer le filtre d'événements pour les changements de langue
        setup_translation_event_filter(window)
        
        # Afficher la fenêtre
        window.show()

        return app.exec()

    except ConfigurationError as e:
        logger.error(f"Erreur de configuration: {str(e)}")
        QMessageBox.critical(
            None,
            "Erreur de Configuration",
            f"Impossible de charger la configuration:\n{str(e)}"
        )
        return 1

    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        QMessageBox.critical(
            None,
            "Erreur",
            f"Une erreur inattendue s'est produite:\n{str(e)}"
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())