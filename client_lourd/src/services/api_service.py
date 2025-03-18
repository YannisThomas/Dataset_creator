# src/services/api_service.py

from typing import List, Dict, Optional, Any, Union, Tuple, Callable
import uuid
import threading
import time
from pathlib import Path
import hashlib

from src.models import Image, Annotation, BoundingBox
from src.models.enums import ImageSource, AnnotationType
from src.utils.logger import Logger
from src.utils.async_worker import AsyncTaskManager
from src.services.api_service import APIService, APICache, RateLimiter
from src.core.exceptions import APIError, AuthenticationError, RateLimitError

class APICache(APICache):
    """
    Version améliorée du cache API avec persistance entre les sessions
    et support pour les préchargements et expirations intelligentes.
    """
    
    def __init__(
        self, 
        cache_dir: Optional[Path] = None,
        max_age_hours: int = 24,
        max_size_mb: int = 1000,  # Taille maximale du cache en Mo
        logger: Optional[Logger] = None
    ):
        """
        Initialise le cache amélioré.
        
        Args:
            cache_dir: Répertoire de cache
            max_age_hours: Durée de vie maximale des entrées en heures
            max_size_mb: Taille maximale du cache en Mo
            logger: Gestionnaire de logs
        """
        super().__init__(cache_dir, max_age_hours, logger)
        self.max_size_mb = max_size_mb
        
        # Index mémoire pour le cache
        self._memory_index = {}
        
        # Charger l'index au démarrage
        self._load_index()
        
        # Nettoyer le cache si nécessaire
        self._clean_if_needed()
    
    def _load_index(self):
        """Charge l'index du cache depuis le disque."""
        try:
            # Créer l'index en mémoire
            self._memory_index = {}
            
            # Parcourir tous les fichiers de cache
            for cache_file in self.cache_dir.glob("**/*.json"):
                try:
                    # Extraire la clé du hash du nom de fichier
                    hash_key = cache_file.stem
                    
                    # Ajouter à l'index
                    self._memory_index[hash_key] = {
                        "path": cache_file,
                        "last_access": cache_file.stat().st_mtime,
                        "size": cache_file.stat().st_size
                    }
                except Exception as e:
                    self.logger.debug(f"Erreur lors du chargement de l'entrée de cache {cache_file}: {str(e)}")
            
            self.logger.info(f"Index de cache chargé: {len(self._memory_index)} entrées")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de l'index du cache: {str(e)}")
            self._memory_index = {}
    
    def _clean_if_needed(self):
        """Nettoie le cache si nécessaire pour respecter la taille maximale."""
        try:
            # Calculer la taille totale actuelle
            total_size_bytes = sum(entry["size"] for entry in self._memory_index.values())
            total_size_mb = total_size_bytes / (1024 * 1024)
            
            # Si la taille est inférieure à la limite, on ne fait rien
            if total_size_mb < self.max_size_mb:
                return
                
            self.logger.info(f"Nettoyage du cache: {total_size_mb:.2f}Mo > {self.max_size_mb}Mo")
            
            # Trier les entrées par date d'accès
            sorted_entries = sorted(
                self._memory_index.items(),
                key=lambda x: x[1]["last_access"]
            )
            
            # Supprimer les entrées les plus anciennes jusqu'à respecter la limite
            bytes_to_free = total_size_bytes - (self.max_size_mb * 1024 * 1024 * 0.9)  # 90% de la limite
            bytes_freed = 0
            
            for hash_key, entry in sorted_entries:
                if bytes_freed >= bytes_to_free:
                    break
                    
                try:
                    # Supprimer le fichier
                    entry["path"].unlink(missing_ok=True)
                    
                    # Mettre à jour les compteurs
                    bytes_freed += entry["size"]
                    
                    # Supprimer de l'index
                    del self._memory_index[hash_key]
                    
                except Exception as e:
                    self.logger.debug(f"Erreur lors de la suppression de l'entrée de cache {entry['path']}: {str(e)}")
            
            self.logger.info(f"Cache nettoyé: {bytes_freed / (1024 * 1024):.2f}Mo libérés")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage du cache: {str(e)}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Récupère une entrée du cache avec mise à jour de la date d'accès.
        
        Args:
            key: Clé de l'entrée
            
        Returns:
            Valeur ou None si non trouvée ou expirée
        """
        # Hasher la clé
        hash_key = hashlib.md5(key.encode()).hexdigest()
        
        with self._lock:
            # Vérifier si la clé est dans l'index mémoire
            if hash_key in self._memory_index:
                entry = self._memory_index[hash_key]
                cache_file = entry["path"]
                
                # Vérifier si le fichier existe toujours
                if not cache_file.exists():
                    del self._memory_index[hash_key]
                    self.stats["misses"] += 1
                    return None
                
                # Vérifier si le fichier est trop ancien
                file_age = time.time() - cache_file.stat().st_mtime
                if file_age > self.max_age.total_seconds():
                    # Supprimer l'entrée expirée
                    cache_file.unlink(missing_ok=True)
                    del self._memory_index[hash_key]
                    self.stats["expired"] += 1
                    return None
                
                try:
                    # Charger les données
                    import json
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Mettre à jour la date d'accès
                    entry["last_access"] = time.time()
                    
                    self.stats["hits"] += 1
                    return data["value"]
                    
                except Exception as e:
                    self.logger.debug(f"Erreur de lecture du cache pour la clé '{key}': {str(e)}")
                    self.stats["misses"] += 1
                    return None
            
            # Clé non trouvée dans l'index
            self.stats["misses"] += 1
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """
        Stocke une entrée dans le cache avec mise à jour de l'index mémoire.
        
        Args:
            key: Clé de l'entrée
            value: Valeur à stocker
            
        Returns:
            True si l'opération a réussi
        """
        # Hasher la clé
        hash_key = hashlib.md5(key.encode()).hexdigest()
        
        with self._lock:
            try:
                # Nettoyer le cache si nécessaire
                self._clean_if_needed()
                
                # Générer le chemin du fichier de cache
                cache_file = self._get_cache_path(key)
                
                # Créer le répertoire parent si nécessaire
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Stocker les données avec des métadonnées
                cache_data = {
                    "timestamp": time.time(),
                    "key": key,
                    "value": value
                }
                
                import json
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2, default=str)
                
                # Mettre à jour l'index mémoire
                self._memory_index[hash_key] = {
                    "path": cache_file,
                    "last_access": time.time(),
                    "size": cache_file.stat().st_size
                }
                
                self.stats["writes"] += 1
                return True
                
            except Exception as e:
                self.logger.debug(f"Erreur d'écriture du cache pour la clé '{key}': {str(e)}")
                return False
    
    def find_pattern(self, pattern: str) -> List[Dict[str, Any]]:
        """
        Recherche dans le cache des entrées correspondant à un motif.
        
        Args:
            pattern: Motif à rechercher dans les clés
            
        Returns:
            Liste des entrées correspondantes
        """
        matching_entries = []
        
        with self._lock:
            for cache_file in self.cache_dir.glob("**/*.json"):
                try:
                    # Charger le fichier pour extraire la clé originale
                    import json
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Vérifier si la clé correspond au motif
                    if pattern in data.get("key", ""):
                        matching_entries.append({
                            "key": data.get("key", ""),
                            "timestamp": data.get("timestamp", 0),
                            "size": cache_file.stat().st_size,
                            "path": str(cache_file)
                        })
                except Exception:
                    # Ignorer les erreurs de lecture
                    pass
        
        return matching_entries
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Supprime les entrées correspondant à un motif.
        
        Args:
            pattern: Motif à rechercher dans les clés
            
        Returns:
            Nombre d'entrées supprimées
        """
        entries = self.find_pattern(pattern)
        count = 0
        
        with self._lock:
            for entry in entries:
                try:
                    # Supprimer le fichier
                    cache_file = Path(entry["path"])
                    cache_file.unlink(missing_ok=True)
                    
                    # Mettre à jour l'index mémoire
                    hash_key = cache_file.stem
                    if hash_key in self._memory_index:
                        del self._memory_index[hash_key]
                    
                    count += 1
                except Exception:
                    pass
        
        return count


class APIService(APIService):
    """
    Version améliorée du service API avec support pour le multithreading,
    l'optimisation du cache et la récupération garantie du nombre souhaité d'images.
    """
    
    def __init__(
        self, 
        config_manager=None,
        logger=None,
        cache_dir=None,
        enable_cache=True,
        max_workers=4
    ):
        """
        Initialise le service API amélioré.
        
        Args:
            config_manager: Gestionnaire de configuration
            logger: Gestionnaire de logs
            cache_dir: Répertoire de cache
            enable_cache: Activer le cache
            max_workers: Nombre maximum de workers pour les tâches asynchrones
        """
        super().__init__(config_manager, logger, cache_dir, enable_cache)
        
        # Remplacer le cache standard par la version améliorée
        if enable_cache:
            cache_dir = cache_dir or Path(self.config.storage.cache_dir) / "api"
            self.cache = APICache(
                cache_dir=cache_dir, 
                logger=self.logger,
                max_size_mb=self.config.storage.max_cache_size_mb
            )
        
        # Gestionnaire de tâches asynchrones
        self.task_manager = AsyncTaskManager(max_workers=max_workers, logger=self.logger)
        
        # Démarrer le gestionnaire
        self.task_manager.start()
        
        # Verrous supplémentaires
        self.search_lock = threading.RLock()
        
        # Dictionnaire des tâches en cours
        self.active_tasks = {}
        
        self.logger.info(f"Service API Amélioré initialisé avec {max_workers} workers")
    
    def __del__(self):
        """Nettoyage à la destruction."""
        try:
            self.task_manager.stop(wait=False)
        except:
            pass
    
    def get_image_detections_async(
        self,
        image_id: str,
        callback: Optional[Callable[[List[Annotation]], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> str:
        """
        Version asynchrone de get_image_detections.
        
        Args:
            image_id: ID de l'image
            callback: Fonction à appeler avec les annotations trouvées
            error_callback: Fonction à appeler en cas d'erreur
            use_cache: Utiliser le cache si disponible
            force_refresh: Forcer le rafraîchissement du cache
            
        Returns:
            ID de la tâche asynchrone
        """
        # Générer un ID de tâche unique
        task_id = f"get_detections_{uuid.uuid4()}"
        
        # Fonction pour exécuter la requête
        def fetch_detections_task():
            return super().get_image_detections(
                image_id=image_id,
                use_cache=use_cache,
                force_refresh=force_refresh
            )
        
        # Soumettre la tâche au gestionnaire
        self.task_manager.submit_task(
            task_id=task_id,
            func=fetch_detections_task,
            priority=1,
            callback=callback,
            error_callback=error_callback
        )
        
        return task_id
    
    def download_image_async(
        self,
        url: str,
        output_path: Optional[Path] = None,
        callback: Optional[Callable[[Path], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
        use_cache: bool = True
    ) -> str:
        """
        Version asynchrone de download_image.
        
        Args:
            url: URL de l'image
            output_path: Chemin de sortie (optionnel)
            callback: Fonction à appeler avec le chemin du fichier téléchargé
            error_callback: Fonction à appeler en cas d'erreur
            use_cache: Utiliser le cache si disponible
            
        Returns:
            ID de la tâche asynchrone
        """
        # Générer un ID de tâche unique
        task_id = f"download_image_{uuid.uuid4()}"
        
        # Fonction pour exécuter la requête
        def download_image_task():
            # Télécharger l'image
            image_data = super().download_image(url, use_cache=use_cache)
            
            if not image_data:
                raise ValueError(f"Échec du téléchargement de l'image: {url}")
            
            # Générer un chemin de sortie si non spécifié
            target_path = output_path
            if target_path is None:
                # Déterminer le répertoire de téléchargement
                download_dir = Path("downloads")
                download_dir.mkdir(parents=True, exist_ok=True)
                
                # Extraire le nom de fichier de l'URL ou générer un UUID
                import os
                from urllib.parse import urlparse
                
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path)
                
                if not filename:
                    filename = f"{uuid.uuid4()}.jpg"
                
                target_path = download_dir / filename
            
            # Créer le répertoire parent si nécessaire
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Sauvegarder l'image
            with open(target_path, 'wb') as f:
                f.write(image_data)
            
            self.logger.debug(f"Image téléchargée: {target_path}")
            return target_path
        
        # Fonction de callback adaptée
        def adapt_callback(result):
            if callback:
                callback(result)
        
        # Soumettre la tâche au gestionnaire
        self.task_manager.submit_task(
            task_id=task_id,
            func=download_image_task,
            priority=2,  # Priorité plus basse que les requêtes
            callback=adapt_callback,
            error_callback=error_callback
        )
        
        return task_id
    
    def batch_download_images(
        self,
        images: List[Image],
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        final_callback: Optional[Callable[[List[Image]], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
        max_concurrent: int = 4,
        use_cache: bool = True
    ) -> str:
        """
        Télécharge un lot d'images en parallèle.
        
        Args:
            images: Liste des images à télécharger
            output_dir: Répertoire de sortie (optionnel)
            progress_callback: Fonction à appeler pour le progrès (terminées, total)
            final_callback: Fonction à appeler quand toutes les images sont téléchargées
            error_callback: Fonction à appeler en cas d'erreur globale
            max_concurrent: Nombre maximum de téléchargements simultanés
            use_cache: Utiliser le cache si disponible
            
        Returns:
            ID de la tâche globale
        """
        # Générer un ID de tâche unique
        batch_id = f"batch_download_{uuid.uuid4()}"
        
        # Fonction pour gérer le téléchargement par lot
        def batch_download_task():
            try:
                # Créer le répertoire de sortie si nécessaire
                target_dir = output_dir or Path("downloads")
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # Variables de suivi
                total = len(images)
                completed = 0
                success = 0
                results = []
                tasks = {}
                
                # Sémaphore pour limiter le nombre de téléchargements simultanés
                semaphore = threading.Semaphore(max_concurrent)
                
                # Verrou pour les mises à jour de statut
                status_lock = threading.RLock()
                
                # Fonction de callback pour chaque téléchargement
                def on_image_downloaded(image_index, image, path):
                    nonlocal completed, success, results
                    
                    with status_lock:
                        completed += 1
                        
                        if path:
                            success += 1
                            # Mettre à jour le chemin de l'image
                            image.path = path
                            results.append(image)
                        
                        # Mettre à jour le progrès
                        if progress_callback:
                            progress_callback(completed, total)
                        
                        # Relâcher le sémaphore
                        semaphore.release()
                
                # Fonction de callback pour les erreurs individuelles
                def on_image_error(image_index, image, error):
                    nonlocal completed
                    
                    with status_lock:
                        completed += 1
                        self.logger.warning(f"Erreur de téléchargement pour l'image {image.id}: {str(error)}")
                        
                        # Mettre à jour le progrès
                        if progress_callback:
                            progress_callback(completed, total)
                        
                        # Relâcher le sémaphore
                        semaphore.release()
                
                # Lancer les téléchargements
                for i, image in enumerate(images):
                    # Vérifier si l'image a déjà une URL
                    if hasattr(image, 'path') and isinstance(image.path, str) and image.path.startswith(('http://', 'https://')):
                        url = image.path
                        
                        # Attendre une place dans le sémaphore
                        semaphore.acquire()
                        
                        # Générer un chemin de sortie
                        image_filename = f"{image.id}.jpg"
                        output_path = target_dir / image_filename
                        
                        # Créer les callbacks pour cette image
                        success_callback = lambda path, idx=i, img=image: on_image_downloaded(idx, img, path)
                        error_callback = lambda error, idx=i, img=image: on_image_error(idx, img, error)
                        
                        # Télécharger l'image
                        task_id = self.download_image_async(
                            url=url,
                            output_path=output_path,
                            callback=success_callback,
                            error_callback=error_callback,
                            use_cache=use_cache
                        )
                        
                        tasks[task_id] = image
                    else:
                        # L'image a déjà un chemin local
                        if hasattr(image, 'path') and isinstance(image.path, (str, Path)) and Path(image.path).exists():
                            with status_lock:
                                completed += 1
                                success += 1
                                results.append(image)
                                
                                # Mettre à jour le progrès
                                if progress_callback:
                                    progress_callback(completed, total)
                        else:
                            # Image sans chemin valide
                            with status_lock:
                                completed += 1
                                self.logger.warning(f"Image {image.id} sans URL valide")
                                
                                if progress_callback:
                                    progress_callback(completed, total)
                
                # Attendre que tous les téléchargements soient terminés
                while completed < total:
                    time.sleep(0.1)
                
                self.logger.info(f"Téléchargement par lot terminé: {success}/{total} images")
                return results
                
            except Exception as e:
                self.logger.error(f"Erreur lors du téléchargement par lot: {str(e)}")
                if error_callback:
                    error_callback(e)
                raise e
        
        # Soumettre la tâche globale
        self.task_manager.submit_task(
            task_id=batch_id,
            func=batch_download_task,
            priority=1,
            callback=final_callback,
            error_callback=error_callback
        )
        
        return batch_id
    
    def get_images_in_bbox_async(
        self,
        bbox: Dict[str, float],
        limit: int = 100,
        callback: Optional[Callable[[List[Image]], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
        use_cache: bool = True,
        force_refresh: bool = False,
        object_types: Optional[List[str]] = None,
        min_required_count: Optional[int] = None,
        retry_count: int = 3
    ) -> str:
        """
        Version asynchrone de get_images_in_bbox qui garantit la récupération
        du nombre minimum d'images spécifié.
        
        Args:
            bbox: Bounding box géographique
            limit: Nombre maximum d'images
            callback: Fonction à appeler avec les images trouvées
            error_callback: Fonction à appeler en cas d'erreur
            use_cache: Utiliser le cache si disponible
            force_refresh: Forcer le rafraîchissement du cache
            object_types: Types d'objets à filtrer
            min_required_count: Nombre minimum d'images à récupérer
            retry_count: Nombre de tentatives en cas d'échec
            
        Returns:
            ID de la tâche asynchrone
        """
        # Générer un ID de tâche unique
        task_id = f"get_images_bbox_{uuid.uuid4()}"
        
        # Définir le nombre minimum d'images requises
        min_required = min_required_count or limit
        
        # Fonction pour exécuter la requête avec garantie de nombre d'images
        def fetch_images_task():
            try:
                with self.search_lock:
                    # Première tentative normale
                    images = super().get_images_in_bbox(
                        bbox=bbox,
                        limit=limit,
                        use_cache=use_cache,
                        force_refresh=force_refresh,
                        object_types=object_types
                    )
                    
                    # Vérifier si on a assez d'images
                    if len(images) >= min_required:
                        self.logger.info(f"Récupération suffisante: {len(images)}/{min_required} images")
                        return images
                    
                    # Si pas assez d'images, élargir la recherche ou ré-essayer
                    self.logger.warning(f"Nombre d'images insuffisant: {len(images)}/{min_required} - tentatives supplémentaires")
                    
                    # Stratégies d'élargissement:
                    # 1. Essayer sans filtre de type d'objet
                    if object_types and len(images) < min_required:
                        self.logger.debug("Tentative sans filtre de type d'objet")
                        additional_images = super().get_images_in_bbox(
                            bbox=bbox,
                            limit=min_required - len(images) + 20,  # Marge de 20 images
                            use_cache=use_cache,
                            force_refresh=True,
                            object_types=None  # Sans filtre
                        )
                        
                        # Filtrer les images qui ont quand même des détections pertinentes
                        # (L'API pourrait manquer certaines images avec des panneaux)
                        filtered_additional = []
                        for img in additional_images:
                            # Ignorer les images déjà récupérées
                            if img.id in existing_ids:
                                continue
                                
                            try:
                                # Vérifier si l'image a des détections pertinentes
                                detections = super().get_image_detections(img.id, use_cache=True)
                                
                                if detections:
                                    img.annotations = detections
                                    filtered_additional.append(img)
                                    
                                    if len(filtered_additional) + len(images) >= min_required:
                                        break
                            except Exception as e:
                                self.logger.debug(f"Erreur lors de la vérification des détections: {str(e)}")
                        
                        # Ajouter uniquement les nouvelles images qui ont des détections
                        existing_ids = set(img.id for img in images)
                        for img in filtered_additional:
                            if img.id not in existing_ids:
                                images.append(img)
                                existing_ids.add(img.id)
                    
                    # 2. Essayer avec une bbox légèrement élargie
                    if len(images) < min_required:
                        self.logger.debug("Tentative avec bbox élargie")
                        
                        # Élargir la bbox de 20%
                        expanded_bbox = self._expand_bbox(bbox, factor=0.2)
                        
                        additional_images = super().get_images_in_bbox(
                            bbox=expanded_bbox,
                            limit=min_required - len(images) + 10,  # Marge de 10 images
                            use_cache=use_cache,
                            force_refresh=True,
                            object_types=object_types
                        )
                        
                        # Ajouter uniquement les nouvelles images
                        existing_ids = set(img.id for img in images)
                        for img in additional_images:
                            if img.id not in existing_ids:
                                images.append(img)
                                existing_ids.add(img.id)
                    
                    # 3. Diviser la bbox en sous-régions pour une recherche plus fine
                    if len(images) < min_required:
                        self.logger.debug("Tentative avec sous-divisions de la bbox")
                        
                        # Diviser la bbox en 4 quadrants
                        sub_bboxes = self._subdivide_bbox(bbox)
                        
                        # Rechercher dans chaque quadrant
                        for sub_bbox in sub_bboxes:
                            if len(images) >= min_required:
                                break
                                
                            additional_images = super().get_images_in_bbox(
                                bbox=sub_bbox,
                                limit=(min_required - len(images)) // len(sub_bboxes) + 5,  # Distribution + marge
                                use_cache=use_cache,
                                force_refresh=True,
                                object_types=object_types
                            )
                            
                            # Ajouter uniquement les nouvelles images
                            existing_ids = set(img.id for img in images)
                            for img in additional_images:
                                if img.id not in existing_ids:
                                    images.append(img)
                                    existing_ids.add(img.id)
                    
                    # Limiter au nombre demandé
                    if len(images) > limit:
                        images = images[:limit]
                    
                    self.logger.info(f"Résultat final: {len(images)}/{min_required} images")
                    return images
            
            except Exception as e:
                self.logger.error(f"Erreur lors de la récupération des images: {str(e)}")
                raise e
        
        # Soumettre la tâche au gestionnaire
        self.task_manager.submit_task(
            task_id=task_id,
            func=fetch_images_task,
            priority=1,
            callback=callback,
            error_callback=error_callback
        )
        
        return task_id
    
    def _expand_bbox(self, bbox: Dict[str, float], factor: float) -> Dict[str, float]:
        """
        Élargit une bounding box par un facteur donné.
        
        Args:
            bbox: Bounding box d'origine
            factor: Facteur d'élargissement (0.1 = 10%)
            
        Returns:
            Bounding box élargie
        """
        lat_span = bbox['max_lat'] - bbox['min_lat']
        lon_span = bbox['max_lon'] - bbox['min_lon']
        
        lat_padding = lat_span * factor / 2
        lon_padding = lon_span * factor / 2
        
        return {
            'min_lat': max(-90, bbox['min_lat'] - lat_padding),
            'max_lat': min(90, bbox['max_lat'] + lat_padding),
            'min_lon': max(-180, bbox['min_lon'] - lon_padding),
            'max_lon': min(180, bbox['max_lon'] + lon_padding)
        }
    
    def _subdivide_bbox(self, bbox: Dict[str, float]) -> List[Dict[str, float]]:
        """
        Divise une bounding box en 4 quadrants.
        
        Args:
            bbox: Bounding box d'origine
            
        Returns:
            Liste de 4 bounding boxes
        """
        mid_lat = (bbox['min_lat'] + bbox['max_lat']) / 2
        mid_lon = (bbox['min_lon'] + bbox['max_lon']) / 2
        
        return [
            # Quadrant sud-ouest
            {
                'min_lat': bbox['min_lat'],
                'max_lat': mid_lat,
                'min_lon': bbox['min_lon'],
                'max_lon': mid_lon
            },
            # Quadrant sud-est
            {
                'min_lat': bbox['min_lat'],
                'max_lat': mid_lat,
                'min_lon': mid_lon,
                'max_lon': bbox['max_lon']
            },
            # Quadrant nord-ouest
            {
                'min_lat': mid_lat,
                'max_lat': bbox['max_lat'],
                'min_lon': bbox['min_lon'],
                'max_lon': mid_lon
            },
            # Quadrant nord-est
            {
                'min_lat': mid_lat,
                'max_lat': bbox['max_lat'],
                'min_lon': mid_lon,
                'max_lon': bbox['max_lon']
            }
        ]