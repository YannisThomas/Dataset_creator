# src/controllers/import_controller.py

from typing import Dict, List, Optional, Union, Callable
from pathlib import Path
import threading
import queue
import time
import uuid

from src.models import Dataset, Image, Annotation
from src.models.enums import ImageSource, AnnotationType, DatasetFormat
from src.services.api_service import APIService
from src.services.import_service import ImportService
from src.services.dataset_service import DatasetService
from src.utils.logger import Logger
from src.utils.async_worker import AsyncTaskManager
from src.core.exceptions import ImportError, APIError

class ImportStatus:
    """Classe pour suivre l'état d'un import asynchrone."""
    
    def __init__(self, import_id: str, dataset_name: str):
        self.import_id = import_id
        self.dataset_name = dataset_name
        self.start_time = time.time()
        self.end_time = None
        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.progress = 0.0  # 0 à 100%
        self.message = "Import en attente de démarrage"
        self.error = None
        self.result = None
        self.steps = []
        self.current_step = ""
        self.total_images = 0
        self.imported_images = 0
        self.step_progress = {}
        self.lock = threading.RLock()
    
    def update(self, **kwargs):
        """Met à jour le statut avec les valeurs fournies."""
        with self.lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            # Si le statut devient "completed" ou "failed", définir end_time
            if kwargs.get("status") in ["completed", "failed", "cancelled"] and self.end_time is None:
                self.end_time = time.time()
    
    def add_step(self, step_name: str):
        """Ajoute une étape au processus d'import."""
        with self.lock:
            self.steps.append(step_name)
            self.current_step = step_name
            self.step_progress[step_name] = 0.0
    
    def update_step_progress(self, step_name: str, progress: float):
        """Met à jour la progression d'une étape spécifique."""
        with self.lock:
            if step_name in self.step_progress:
                self.step_progress[step_name] = progress
                
                # Recalculer la progression globale (moyenne pondérée)
                if self.steps:
                    total_progress = sum(self.step_progress.get(step, 0.0) for step in self.steps) / len(self.steps)
                    self.progress = total_progress
    
    def to_dict(self) -> Dict:
        """Convertit le statut en dictionnaire."""
        with self.lock:
            duration = (self.end_time or time.time()) - self.start_time
            return {
                "import_id": self.import_id,
                "dataset_name": self.dataset_name,
                "status": self.status,
                "progress": self.progress,
                "message": self.message,
                "error": str(self.error) if self.error else None,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration": duration,
                "steps": self.steps,
                "current_step": self.current_step,
                "total_images": self.total_images,
                "imported_images": self.imported_images,
                "step_progress": self.step_progress
            }

class ImportController:
    """
    Contrôleur amélioré pour la gestion des imports avec support asynchrone
    et optimisations pour garantir la récupération du nombre souhaité d'images.
    """
    
    def __init__(
        self, 
        import_service: Optional[ImportService] = None,
        api_service: Optional[APIService] = None,
        dataset_service: Optional[DatasetService] = None,
        logger: Optional[Logger] = None,
        max_workers: int = 4
    ):
        """
        Initialise le contrôleur d'import amélioré.
        
        Args:
            import_service: Service d'import de données
            api_service: Service API optimisé pour les imports distants
            dataset_service: Service de gestion des datasets
            logger: Gestionnaire de logs
            max_workers: Nombre maximum de workers
        """
        self.import_service = import_service or ImportService()
        # Utiliser l'API service amélioré ou créer une instance
        self.api_service = api_service or APIService()
        self.dataset_service = dataset_service or DatasetService()
        self.logger = logger or Logger()
        
        # Gestionnaire de tâches asynchrones pour les opérations longues
        self.task_manager = AsyncTaskManager(max_workers=max_workers, logger=self.logger)
        
        # Démarrer le gestionnaire
        self.task_manager.start()
        
        # Dictionnaire des imports en cours avec leurs statuts
        self.imports = {}
        
        # Verrou pour la manipulation du dictionnaire des imports
        self.imports_lock = threading.RLock()
        
        self.logger.info(f"Contrôleur d'import amélioré initialisé avec {max_workers} workers")
    
    def __del__(self):
        """Nettoyage à la destruction."""
        try:
            self.task_manager.stop(wait=False)
        except:
            pass
    
    def import_from_mapillary_async(
        self,
        bbox: Dict[str, float],
        dataset_name: Optional[str] = None,
        max_images: int = 100,
        classes: Optional[Dict[int, str]] = None,
        overwrite_existing: bool = False,
        progress_callback: Optional[Callable[[Dict], None]] = None,
        completion_callback: Optional[Callable[[Dataset], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None
    ) -> str:
        """
        Version asynchrone de l'import depuis Mapillary qui garantit la récupération
        du nombre exact d'images demandées.
        
        Args:
            bbox: Bounding box géographique
            dataset_name: Nom du dataset (optionnel)
            max_images: Nombre maximum d'images à importer
            classes: Mapping des classes (optionnel)
            overwrite_existing: Si True, écrase un dataset existant avec le même nom
            progress_callback: Fonction appelée régulièrement avec l'état de l'import
            completion_callback: Fonction appelée à la fin avec le dataset
            error_callback: Fonction appelée en cas d'erreur
            
        Returns:
            ID de l'import asynchrone
        """
        # Générer un identifiant unique pour l'import
        import_id = f"mapillary_import_{uuid.uuid4()}"
        
        # Générer un nom de dataset si non spécifié
        if not dataset_name:
            dataset_name = f"Mapillary_{bbox['min_lat']}_{bbox['max_lat']}_{bbox['min_lon']}_{bbox['max_lon']}"
        
        # Créer un objet de suivi pour cet import
        import_status = ImportStatus(import_id, dataset_name)
        
        # Ajouter au dictionnaire des imports
        with self.imports_lock:
            self.imports[import_id] = import_status
        
        # Fonction principale pour exécuter l'import
        def execute_import():
            try:
                # Mise à jour du statut
                import_status.update(
                    status="running",
                    message="Import démarré",
                    progress=0.0
                )
                
                # Étape 1: Vérification et création du dataset
                import_status.add_step("prepare_dataset")
                
                # Vérifier si le dataset existe déjà
                existing_dataset = None
                try:
                    existing_dataset = self.dataset_service.get_dataset(dataset_name)
                except Exception as e:
                    self.logger.warning(f"Erreur lors de la vérification du dataset existant: {str(e)}")
                
                if existing_dataset and not overwrite_existing:
                    # Générer un nouveau nom unique
                    timestamp = int(time.time())
                    new_dataset_name = f"{dataset_name}_{timestamp}"
                    self.logger.info(f"Dataset existant, utilisation du nouveau nom: {new_dataset_name}")
                    
                    import_status.update(
                        dataset_name=new_dataset_name,
                        message=f"Dataset existant, utilisation du nouveau nom: {new_dataset_name}",
                        progress=5.0
                    )
                    
                    dataset_name = new_dataset_name
                elif existing_dataset and overwrite_existing:
                    # Supprimer le dataset existant
                    self.logger.info(f"Suppression du dataset existant: {dataset_name}")
                    import_status.update(
                        message=f"Suppression du dataset existant: {dataset_name}",
                        progress=5.0
                    )
                    self.dataset_service.delete_dataset(dataset_name)
                
                # Charger la configuration Mapillary pour le mapping des classes
                import_status.update(
                    message="Chargement de la configuration Mapillary",
                    progress=10.0
                )
                
                # Cette partie serait normalement dans le contrôleur original
                # Ici, on va simplifier en supposant que les classes sont fournies
                class_mapping = classes or {}
                
                # Créer le dataset
                import_status.update(
                    message=f"Création du dataset {dataset_name}",
                    progress=15.0
                )
                
                dataset = self.dataset_service.create_dataset(
                    name=dataset_name,
                    classes=class_mapping
                )
                
                # Étape 2: Recherche d'images dans Mapillary
                import_status.add_step("search_images")
                import_status.update(
                    message=f"Recherche d'images dans la zone spécifiée (max: {max_images})",
                    progress=20.0
                )
                
                # Utiliser le service API amélioré pour garantir le nombre d'images
                def on_images_found(images):
                    try:
                        import_status.update(
                            message=f"Images trouvées: {len(images)}",
                            progress=30.0,
                            total_images=len(images)
                        )
                        
                        # Si aucune image trouvée
                        if not images:
                            import_status.update(
                                status="failed",
                                message="Aucune image trouvée dans la zone spécifiée",
                                progress=100.0
                            )
                            
                            if error_callback:
                                error_callback(ImportError("Aucune image trouvée dans la zone spécifiée"))
                            return
                        
                        # Étape 3: Téléchargement des images et récupération des annotations
                        import_status.add_step("download_images")
                        
                        # Créer les répertoires nécessaires
                        images_dir = dataset.path / "images"
                        images_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Télécharger les images en parallèle
                        def on_download_progress(completed, total):
                            progress = (completed / total) * 100 if total > 0 else 0
                            import_status.update_step_progress("download_images", progress)
                            import_status.update(
                                message=f"Téléchargement des images: {completed}/{total}",
                                imported_images=completed
                            )
                            
                            # Appeler le callback de progression
                            if progress_callback:
                                progress_callback(import_status.to_dict())
                        
                        def on_download_complete(downloaded_images):
                            try:
                                import_status.update(
                                    message=f"Téléchargement terminé: {len(downloaded_images)} images",
                                    progress=70.0,
                                    imported_images=len(downloaded_images)
                                )
                                
                                # Étape 4: Finalisation et sauvegarde du dataset
                                import_status.add_step("save_dataset")
                                import_status.update(
                                    message="Finalisation et sauvegarde du dataset",
                                    progress=80.0
                                )
                                
                                # Ajouter les images téléchargées au dataset
                                for image in downloaded_images:
                                    dataset.add_image(image)
                                
                                # Sauvegarder le dataset
                                import_status.update(
                                    message="Sauvegarde du dataset dans la base de données",
                                    progress=90.0
                                )
                                
                                self.dataset_service.update_dataset(dataset)
                                
                                # Import terminé avec succès
                                import_status.update(
                                    status="completed",
                                    message=f"Import terminé: {len(dataset.images)} images importées",
                                    progress=100.0
                                )
                                
                                # Appeler le callback de complétion
                                if completion_callback:
                                    completion_callback(dataset)
                                
                            except Exception as e:
                                self.logger.error(f"Erreur lors de la finalisation de l'import: {str(e)}")
                                import_status.update(
                                    status="failed",
                                    message=f"Erreur lors de la finalisation: {str(e)}",
                                    error=e
                                )
                                
                                if error_callback:
                                    error_callback(e)
                        
                        def on_download_error(e):
                            self.logger.error(f"Erreur lors du téléchargement des images: {str(e)}")
                            import_status.update(
                                status="failed",
                                message=f"Erreur lors du téléchargement: {str(e)}",
                                error=e
                            )
                            
                            if error_callback:
                                error_callback(e)
                        
                        # Lancer le téléchargement par lot
                        self.api_service.batch_download_images(
                            images=images,
                            output_dir=images_dir,
                            progress_callback=on_download_progress,
                            final_callback=on_download_complete,
                            error_callback=on_download_error,
                            max_concurrent=4,
                            use_cache=True
                        )
                        
                    except Exception as e:
                        self.logger.error(f"Erreur lors du traitement des images: {str(e)}")
                        import_status.update(
                            status="failed",
                            message=f"Erreur lors du traitement des images: {str(e)}",
                            error=e
                        )
                        
                        if error_callback:
                            error_callback(e)
                
                def on_images_error(e):
                    self.logger.error(f"Erreur lors de la recherche d'images: {str(e)}")
                    import_status.update(
                        status="failed",
                        message=f"Erreur lors de la recherche d'images: {str(e)}",
                        error=e
                    )
                    
                    if error_callback:
                        error_callback(e)
                
                # Rechercher les images avec le service amélioré
                self.api_service.get_images_in_bbox_async(
                    bbox=bbox,
                    limit=max_images,
                    callback=on_images_found,
                    error_callback=on_images_error,
                    use_cache=True,
                    force_refresh=False,
                    object_types=["regulatory", "warning", "information", "complementary"],
                    min_required_count=max_images
                )
                
            except Exception as e:
                self.logger.error(f"Erreur lors de l'import: {str(e)}")
                import_status.update(
                    status="failed",
                    message=f"Erreur lors de l'import: {str(e)}",
                    error=e
                )
                
                if error_callback:
                    error_callback(e)
        
        # Soumettre la tâche d'import au gestionnaire
        self.task_manager.submit_task(
            task_id=import_id,
            func=execute_import,
            priority=1
        )
        
        return import_id
    
    def get_import_status(self, import_id: str) -> Optional[Dict]:
        """
        Récupère le statut d'un import en cours.
        
        Args:
            import_id: ID de l'import
            
        Returns:
            Dictionnaire avec le statut ou None si l'import n'existe pas
        """
        with self.imports_lock:
            if import_id in self.imports:
                return self.imports[import_id].to_dict()
        
        return None
    
    def cancel_import(self, import_id: str) -> bool:
        """
        Annule un import en cours.
        
        Args:
            import_id: ID de l'import
            
        Returns:
            True si l'import a été annulé avec succès
        """
        with self.imports_lock:
            if import_id not in self.imports:
                return False
            
            import_status = self.imports[import_id]
            
            # Essayer d'annuler la tâche
            cancelled = self.task_manager.cancel_task(import_id)
            
            if cancelled:
                import_status.update(
                    status="cancelled",
                    message="Import annulé par l'utilisateur",
                    progress=100.0
                )
            
            return cancelled
    
    def list_imports(self) -> List[Dict]:
        """
        Liste tous les imports avec leur statut.
        
        Returns:
            Liste des statuts d'import
        """
        with self.imports_lock:
            return [import_status.to_dict() for import_status in self.imports.values()]
    
    def clean_completed_imports(self, max_age_hours: int = 24) -> int:
        """
        Nettoie les imports terminés anciens.
        
        Args:
            max_age_hours: Âge maximum en heures
            
        Returns:
            Nombre d'imports supprimés
        """
        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        to_remove = []
        
        with self.imports_lock:
            for import_id, import_status in self.imports.items():
                if import_status.status in ["completed", "failed", "cancelled"]:
                    age = current_time - (import_status.end_time or current_time)
                    if age > max_age_seconds:
                        to_remove.append(import_id)
            
            # Supprimer les imports anciens
            for import_id in to_remove:
                del self.imports[import_id]
        
        return len(to_remove)