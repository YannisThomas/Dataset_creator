# src/controllers/export_controller.py

from typing import Dict, Optional, Union, List
from pathlib import Path

from src.models import Dataset
from src.models.enums import DatasetFormat
from src.services.export_service import ExportService
from src.services.dataset_service import DatasetService
from src.utils.logger import Logger
from src.core.exceptions import ExportError

class ExportController:
    """
    Contrôleur pour la gestion des exports de datasets
    
    Responsabilités :
    - Coordination des exports vers différents formats
    - Préparation et validation des données avant export
    - Gestion des exports complexes
    """
    
    def __init__(
        self, 
        export_service: Optional[ExportService] = None,
        dataset_service: Optional[DatasetService] = None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le contrôleur d'export
        
        Args:
            export_service: Service d'export de données
            dataset_service: Service de gestion des datasets
            logger: Gestionnaire de logs
        """
        self.export_service = export_service or ExportService()
        self.dataset_service = dataset_service or DatasetService()
        self.logger = logger or Logger()
    
    def export_dataset(
        self, 
        dataset: Dataset, 
        export_format: Union[DatasetFormat, str],
        output_path: Optional[Path] = None,
        validate_before_export: bool = True,
        options: Optional[Dict] = None
    ) -> Path:
        """
        Exporte un dataset dans un format spécifique
        
        Args:
            dataset: Dataset à exporter
            export_format: Format d'export
            output_path: Chemin de sortie (optionnel)
            validate_before_export: Valider le dataset avant export
            options: Options d'export supplémentaires (split_ratio, include_images, etc.)
            
        Returns:
            Chemin du répertoire d'export
        """
        try:
            # Valider le dataset si demandé
            if validate_before_export:
                validation = dataset.validate_dataset()
                if not validation["valid"]:
                    errors = "\n".join(validation.get("errors", []))
                    raise ExportError(f"Validation du dataset échouée :\n{errors}")
            
            # Générer un chemin de sortie si non spécifié
            if output_path is None:
                output_path = Path(f"exports/{dataset.name}_{export_format}")
            
            # Assurer l'existence du répertoire de sortie
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Exporter le dataset
            export_result = self.export_service.export_dataset(
                dataset, 
                export_format, 
                output_path,
                options
            )
            
            # Exporter la configuration du dataset
            config_path = self.export_service.export_dataset_config(
                dataset, 
                output_path / f"{dataset.name}_config.json"
            )
            
            self.logger.info(f"Export du dataset {dataset.name} terminé : {export_result}")
            return export_result
        
        except Exception as e:
            self.logger.error(f"Échec de l'export du dataset : {str(e)}")
            raise ExportError(f"Export du dataset impossible : {str(e)}")
    
    def batch_export(
        self, 
        datasets: List[Dataset], 
        export_format: Union[DatasetFormat, str],
        base_output_path: Optional[Path] = None
    ) -> List[Path]:
        """
        Exporte plusieurs datasets en batch
        
        Args:
            datasets: Liste des datasets à exporter
            export_format: Format d'export
            base_output_path: Chemin de base pour les exports
            
        Returns:
            Liste des chemins d'export
        """
        try:
            # Créer le répertoire de base si non spécifié
            if base_output_path is None:
                base_output_path = Path("exports/batch")
            base_output_path.mkdir(parents=True, exist_ok=True)
            
            # Stocker les résultats d'export
            export_results = []
            
            # Exporter chaque dataset
            for dataset in datasets:
                try:
                    # Créer un sous-répertoire pour chaque dataset
                    output_path = base_output_path / f"{dataset.name}_{export_format}"
                    
                    # Exporter le dataset
                    result = self.export_dataset(
                        dataset, 
                        export_format, 
                        output_path
                    )
                    export_results.append(result)
                    
                except Exception as e:
                    self.logger.warning(f"Échec de l'export du dataset {dataset.name} : {str(e)}")
            
            self.logger.info(f"Export par lots terminé : {len(export_results)} datasets exportés")
            return export_results
        
        except Exception as e:
            self.logger.error(f"Échec de l'export par lots : {str(e)}")
            raise ExportError(f"Export par lots impossible : {str(e)}")
    
    def export_dataset_statistics(
        self, 
        dataset: Dataset, 
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Exporte les statistiques détaillées d'un dataset
        
        Args:
            dataset: Dataset à analyser
            output_path: Chemin de sortie (optionnel)
            
        Returns:
            Chemin du fichier de statistiques
        """
        try:
            # Récupérer les statistiques
            stats = self.dataset_service.get_dataset_statistics(dataset.name)
            
            # Générer un chemin de sortie si non spécifié
            if output_path is None:
                output_path = Path(f"exports/{dataset.name}_stats.json")
            
            # Assurer l'existence du répertoire
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Sauvegarder les statistiques
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Statistiques du dataset exportées : {output_path}")
            return output_path
        
        except Exception as e:
            self.logger.error(f"Échec de l'export des statistiques : {str(e)}")
            raise ExportError(f"Export des statistiques impossible : {str(e)}")
    
    def generate_dataset_report(
        self, 
        dataset: Dataset, 
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Génère un rapport détaillé sur le dataset
        
        Args:
            dataset: Dataset à analyser
            output_path: Chemin de sortie (optionnel)
            
        Returns:
            Chemin du fichier de rapport
        """
        try:
            # Récupérer les statistiques
            stats = self.dataset_service.get_dataset_statistics(dataset.name)
            
            # Générer un chemin de sortie si non spécifié
            if output_path is None:
                output_path = Path(f"exports/{dataset.name}_report.md")
            
            # Assurer l'existence du répertoire
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Générer le rapport au format Markdown
            report_content = f"""# Rapport du Dataset : {dataset.name}

## Informations Générales
- **Nom** : {dataset.name}
- **Version** : {dataset.version}
- **Date de création** : {dataset.created_at}

## Statistiques Principales
- **Nombre total d'images** : {stats['total_images']}
- **Nombre total d'annotations** : {stats['total_annotations']}
- **Nombre moyen d'annotations par image** : {stats['avg_annotations_per_image']:.2f}

## Répartition des Classes
"""
            
            # Ajouter la répartition des classes
            for class_id, count in stats.get('annotations_per_class', {}).items():
                class_name = dataset.classes.get(class_id, f'Classe {class_id}')
                report_content += f"- **{class_name}** : {count} annotations\n"
            
            # Ajouter la section de validation
            report_content += f"""
## Validation du Dataset
{self._generate_validation_section(dataset)}

## Détails des Images
- **Formats d'images** : {', '.join(set(img.path.suffix.lower() for img in dataset.images))}
- **Dimensions min/max** : {min(img.width for img in dataset.images)}x{min(img.height for img in dataset.images)} / {max(img.width for img in dataset.images)}x{max(img.height for img in dataset.images)}
"""
            
            # Sauvegarder le rapport
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            self.logger.info(f"Rapport du dataset généré : {output_path}")
            return output_path
        
        except Exception as e:
            self.logger.error(f"Échec de la génération du rapport : {str(e)}")
            raise ExportError(f"Génération du rapport impossible : {str(e)}")
    
    def _generate_validation_section(self, dataset: Dataset) -> str:
        """
        Génère une section de validation pour le rapport
        
        Args:
            dataset: Dataset à valider
            
        Returns:
            Section de validation au format Markdown
        """
        validation = dataset.validate_dataset()
        
        if validation["valid"]:
            return "**Statut** : ✅ Validé\n\n*Aucun problème détecté*"
        else:
            error_list = ""
            warning_list = ""
            
            for error in validation.get("errors", []):
                error_list += f"- {error}\n"
                
            for warning in validation.get("warnings", []):
                warning_list += f"- {warning}\n"
                
            result = "**Statut** : ❌ Non Validé\n\n"
            result += "### Erreurs\n"
            result += error_list if error_list else "*Aucune erreur*\n\n"
            result += "### Avertissements\n"
            result += warning_list if warning_list else "*Aucun avertissement*\n"
            
            return result