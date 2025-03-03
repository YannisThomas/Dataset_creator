#!/usr/bin/env python3

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.views.main_window import MainWindow
from src.utils.logger import Logger
from src.utils.config import ConfigManager
from src.controllers.controller_manager import ControllerManager
from src.core.exceptions import ConfigurationError

def main():
    """
    Point d'entrée principal de l'application.
    Utilise l'architecture MVC avec injection des contrôleurs.
    """
    try:
        # Initialiser le logger
        log_dir = Path("data/logs")
        logger = Logger(log_dir=log_dir)
        logger.info("Démarrage de YOLO Dataset Manager...")

        # Initialiser la configuration
        config_manager = ConfigManager()
        logger.info("Configuration chargée avec succès")
        
        # Initialiser le gestionnaire de contrôleurs
        controller_manager = ControllerManager(config_manager=config_manager, logger=logger)
        logger.info("Contrôleurs initialisés")

        # Initialiser l'application Qt
        app = QApplication(sys.argv)
        window = MainWindow(controller_manager=controller_manager)
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