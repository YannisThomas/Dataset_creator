# src/services/api_service.py

from typing import List, Dict, Optional, Any, Union, Tuple
import requests
import json
import time
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading

from src.models import Image, Annotation, BoundingBox
from src.models.enums import AnnotationType, ImageSource
from src.utils.config import ConfigManager
from src.utils.logger import Logger
from src.core.exceptions import APIError, AuthenticationError, RateLimitError

class APICache:
    """
    Système de cache pour les requêtes API.
    
    Permet de stocker les résultats des requêtes pour éviter de refaire les mêmes appels
    et améliorer les performances de l'application.
    """
    
    def __init__(
        self, 
        cache_dir: Optional[Path] = None,
        max_age_hours: int = 24,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le cache.
        
        Args:
            cache_dir: Répertoire de cache
            max_age_hours: Durée de vie maximale des entrées en heures
            logger: Gestionnaire de logs
        """
        self.cache_dir = cache_dir or Path("data/cache/api")
        self.max_age = timedelta(hours=max_age_hours)
        self.logger = logger or Logger()
        
        # Créer le répertoire de cache s'il n'existe pas
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Mutex pour éviter les conflits d'accès
        self._lock = threading.RLock()
        
        # Statistiques du cache
        self.stats = {
            "hits": 0,
            "misses": 0,
            "expired": 0,
            "writes": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        Récupère une entrée du cache.
        
        Args:
            key: Clé de l'entrée
            
        Returns:
            Valeur ou None si non trouvée ou expirée
        """
        with self._lock:
            try:
                # Générer le chemin du fichier de cache
                cache_file = self._get_cache_path(key)
                
                # Vérifier si le fichier existe
                if not cache_file.exists():
                    self.stats["misses"] += 1
                    return None
                
                # Vérifier si le fichier est trop ancien
                file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_age > self.max_age:
                    self.stats["expired"] += 1
                    return None
                
                # Charger les données
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.stats["hits"] += 1
                return data["value"]
                
            except Exception as e:
                self.logger.debug(f"Erreur de lecture du cache pour la clé '{key}': {str(e)}")
                self.stats["misses"] += 1
                return None
    
    def set(self, key: str, value: Any) -> bool:
        """
        Stocke une entrée dans le cache.
        
        Args:
            key: Clé de l'entrée
            value: Valeur à stocker
            
        Returns:
            True si l'opération a réussi
        """
        with self._lock:
            try:
                # Générer le chemin du fichier de cache
                cache_file = self._get_cache_path(key)
                
                # Créer le répertoire parent si nécessaire
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Stocker les données avec des métadonnées
                cache_data = {
                    "timestamp": datetime.now().isoformat(),
                    "key": key,
                    "value": value
                }
                
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2, default=str)
                
                self.stats["writes"] += 1
                return True
                
            except Exception as e:
                self.logger.debug(f"Erreur d'écriture du cache pour la clé '{key}': {str(e)}")
                return False
    
    def delete(self, key: str) -> bool:
        """
        Supprime une entrée du cache.
        
        Args:
            key: Clé de l'entrée
            
        Returns:
            True si l'opération a réussi
        """
        with self._lock:
            try:
                cache_file = self._get_cache_path(key)
                if cache_file.exists():
                    cache_file.unlink()
                return True
            except Exception as e:
                self.logger.debug(f"Erreur de suppression du cache pour la clé '{key}': {str(e)}")
                return False
    
    def clear(self) -> int:
        """
        Vide le cache entièrement.
        
        Returns:
            Nombre de fichiers supprimés
        """
        with self._lock:
            try:
                count = 0
                for cache_file in self.cache_dir.glob("**/*.json"):
                    try:
                        cache_file.unlink()
                        count += 1
                    except:
                        pass
                
                self.logger.info(f"Cache API nettoyé: {count} fichiers supprimés")
                return count
            except Exception as e:
                self.logger.error(f"Erreur lors du nettoyage du cache: {str(e)}")
                return 0
    
    def clear_expired(self) -> int:
        """
        Supprime uniquement les entrées expirées.
        
        Returns:
            Nombre de fichiers expirés supprimés
        """
        with self._lock:
            try:
                count = 0
                for cache_file in self.cache_dir.glob("**/*.json"):
                    try:
                        # Vérifier si le fichier est trop ancien
                        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                        if file_age > self.max_age:
                            cache_file.unlink()
                            count += 1
                    except:
                        pass
                
                self.logger.info(f"Cache API nettoyé: {count} fichiers expirés supprimés")
                return count
            except Exception as e:
                self.logger.error(f"Erreur lors du nettoyage du cache expiré: {str(e)}")
                return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du cache.
        
        Returns:
            Statistiques d'utilisation
        """
        with self._lock:
            # Compter le nombre de fichiers et la taille totale
            file_count = 0
            total_size = 0
            
            try:
                for cache_file in self.cache_dir.glob("**/*.json"):
                    file_count += 1
                    total_size += cache_file.stat().st_size
            except:
                pass
            
            # Convertir en Mo
            total_size_mb = total_size / (1024 * 1024)
            
            return {
                **self.stats,
                "file_count": file_count,
                "total_size_mb": total_size_mb,
                "hit_ratio": self.stats["hits"] / (self.stats["hits"] + self.stats["misses"]) if (self.stats["hits"] + self.stats["misses"]) > 0 else 0
            }
    
    def _get_cache_path(self, key: str) -> Path:
        """
        Génère le chemin du fichier de cache pour une clé.
        
        Args:
            key: Clé à hacher
            
        Returns:
            Chemin du fichier
        """
        # Utiliser un hash pour éviter les problèmes de caractères spéciaux
        hash_key = hashlib.md5(key.encode()).hexdigest()
        
        # Utiliser les 2 premiers caractères comme sous-répertoire
        sub_dir = hash_key[:2]
        
        return self.cache_dir / sub_dir / f"{hash_key}.json"


class RateLimiter:
    """
    Gestionnaire de limites de taux pour les API.
    
    Permet de contrôler le nombre de requêtes par période et d'éviter
    de dépasser les quotas imposés par les API.
    """
    
    def __init__(
        self, 
        requests_per_minute: int = 60,
        requests_per_day: int = 10000,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le gestionnaire de limites.
        
        Args:
            requests_per_minute: Nombre de requêtes autorisées par minute
            requests_per_day: Nombre de requêtes autorisées par jour
            logger: Gestionnaire de logs
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_day = requests_per_day
        self.logger = logger or Logger()
        
        # Historique des requêtes
        self.minute_history = []
        self.day_history = []
        
        # Mutex pour éviter les conflits d'accès
        self._lock = threading.RLock()
    
    def check_and_update(self) -> bool:
        """
        Vérifie si une nouvelle requête est autorisée et met à jour l'historique.
        
        Returns:
            True si la requête est autorisée
        """
        with self._lock:
            now = datetime.now()
            
            # Nettoyer les historiques
            self._clean_history(now)
            
            # Vérifier les limites
            if len(self.minute_history) >= self.requests_per_minute:
                self.logger.warning(f"Limite de requêtes par minute atteinte ({self.requests_per_minute})")
                return False
                
            if len(self.day_history) >= self.requests_per_day:
                self.logger.warning(f"Limite de requêtes par jour atteinte ({self.requests_per_day})")
                return False
            
            # Ajouter l'horodatage actuel aux historiques
            self.minute_history.append(now)
            self.day_history.append(now)
            
            return True
    
    def _clean_history(self, now: datetime):
        """
        Nettoie les historiques en supprimant les entrées trop anciennes.
        
        Args:
            now: Horodatage actuel
        """
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)
        
        # Supprimer les entrées plus anciennes qu'une minute
        self.minute_history = [ts for ts in self.minute_history if ts > minute_ago]
        
        # Supprimer les entrées plus anciennes qu'un jour
        self.day_history = [ts for ts in self.day_history if ts > day_ago]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques d'utilisation.
        
        Returns:
            Statistiques d'utilisation
        """
        with self._lock:
            now = datetime.now()
            self._clean_history(now)
            
            return {
                "minute_usage": len(self.minute_history),
                "minute_limit": self.requests_per_minute,
                "minute_percentage": (len(self.minute_history) / self.requests_per_minute) * 100 if self.requests_per_minute > 0 else 0,
                "day_usage": len(self.day_history),
                "day_limit": self.requests_per_day,
                "day_percentage": (len(self.day_history) / self.requests_per_day) * 100 if self.requests_per_day > 0 else 0
            }
    
    def wait_if_needed(self) -> bool:
        """
        Attend si nécessaire pour respecter les limites.
        
        Returns:
            True si l'attente a été effectuée avec succès
        """
        with self._lock:
            now = datetime.now()
            self._clean_history(now)
            
            # Si pas de problème, retourner immédiatement
            if len(self.minute_history) < self.requests_per_minute and len(self.day_history) < self.requests_per_day:
                return True
            
            # Si limite journalière atteinte, impossible d'attendre
            if len(self.day_history) >= self.requests_per_day:
                self.logger.warning("Limite journalière atteinte, impossible d'attendre")
                return False
            
            # Si limite par minute atteinte, attendre jusqu'à ce qu'une requête expire
            if len(self.minute_history) >= self.requests_per_minute:
                oldest = min(self.minute_history)
                wait_seconds = (oldest + timedelta(minutes=1) - now).total_seconds()
                
                if wait_seconds > 0:
                    self.logger.info(f"Attente de {wait_seconds:.2f} secondes pour respecter la limite de requêtes")
                    time.sleep(wait_seconds + 0.1)  # Ajouter une petite marge
                    
                return True


class APIService:
    """
    Service de gestion des appels API avec cache et gestion des limites de taux.
    """
    
    def __init__(
        self, 
        config_manager: Optional[ConfigManager] = None,
        logger: Optional[Logger] = None,
        cache_dir: Optional[Path] = None,
        enable_cache: bool = True
    ):
        """
        Initialise le service API amélioré.
        
        Args:
            config_manager: Gestionnaire de configuration
            logger: Gestionnaire de logs
            cache_dir: Répertoire de cache
            enable_cache: Activer le cache
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.get_config()
        self.logger = logger or Logger()
        
        # Gestionnaire de cache
        if enable_cache:
            cache_dir = cache_dir or Path(self.config.storage.cache_dir) / "api"
            self.cache = APICache(cache_dir=cache_dir, logger=self.logger)
        else:
            self.cache = None
        
        # Gestionnaire de limites de taux
        self.rate_limiter = RateLimiter(
            requests_per_minute=60,  # Valeur par défaut, à adapter selon l'API
            requests_per_day=10000,
            logger=self.logger
        )
        
        # Configurer la session avec retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.config.api.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Statistiques
        self.request_count = 0
        self.request_errors = 0
        self.last_request_time = None
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Crée les en-têtes pour les requêtes API.
        
        Returns:
            En-têtes HTTP
        """
        # Log détaillé du token
        self.logger.debug(f"Token utilisé : {self.config.api.mapillary_token}")
        
        return {
            "Authorization": f"Bearer {self.config.api.mapillary_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _generate_cache_key(self, endpoint: str, params: Dict = None) -> str:
        """
        Génère une clé de cache unique pour une requête.
        
        Args:
            endpoint: Point de terminaison de l'API
            params: Paramètres de la requête
            
        Returns:
            Clé de cache
        """
        # Convertir params en chaîne triée pour assurer la cohérence
        params_str = ""
        if params:
            params_str = json.dumps(params, sort_keys=True)
        
        return f"{endpoint}:{params_str}"
    
    def _make_request(
        self, 
        endpoint: str, 
        params: Dict = None,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> Dict:
        """
        Effectue une requête à l'API avec gestion du cache et des limites.
        
        Args:
            endpoint: Point de terminaison de l'API
            params: Paramètres de la requête
            use_cache: Utiliser le cache si disponible
            force_refresh: Forcer le rafraîchissement du cache
            
        Returns:
            Réponse de l'API
            
        Raises:
            APIError: En cas d'erreur de l'API
            RateLimitError: En cas de dépassement des limites de taux
        """
        url = f"{self.config.api.mapillary_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        # Générer la clé de cache
        cache_key = self._generate_cache_key(endpoint, params)
        self.logger.debug(f"Token utilisé : {self.config.api.mapillary_token[:10]}...")
        try:
            # Tenter de récupérer depuis le cache si activé
            if self.cache and use_cache and not force_refresh:
                cached_data = self.cache.get(cache_key)
                if cached_data:
                    self.logger.debug(f"Données récupérées depuis le cache pour: {endpoint}")
                    return cached_data
            
            # Vérifier et attendre si nécessaire pour respecter les limites de taux
            if not self.rate_limiter.check_and_update():
                if not self.rate_limiter.wait_if_needed():
                    raise RateLimitError(
                        "Limite de taux atteinte, impossible de faire la requête",
                        reset_time=datetime.now() + timedelta(minutes=1)
                    )
            
            # Faire la requête
            self.logger.debug(f"Requête API: {url}")
            self.last_request_time = datetime.now()
            
            response = self.session.get(
                url=url,
                headers=headers,
                params=params,
                timeout=self.config.api.request_timeout
            )
            
            self.request_count += 1
            
            # Gérer la réponse
            if response.status_code == 200:
                data = response.json()
                
                # Mettre en cache si activé
                if self.cache and use_cache:
                    self.cache.set(cache_key, data)
                
                return data
            elif response.status_code == 429:
                reset_time = response.headers.get('X-RateLimit-Reset')
                self.request_errors += 1
                
                raise RateLimitError(
                    "Limite de taux dépassée",
                    reset_time=reset_time
                )
            elif response.status_code == 401:
                self.request_errors += 1
                
                raise AuthenticationError(
                    f"Erreur d'authentification: {response.text}",
                    token=self.config.api.mapillary_token
                )
            else:
                self.request_errors += 1
                
                raise APIError(
                    f"Échec de la requête API: {response.text}",
                    status_code=response.status_code,
                    response=response.text
                )
                
        except requests.exceptions.RequestException as e:
            self.request_errors += 1
            detailed_error = f"Détails de l'erreur : {str(e)}"
            if hasattr(e, 'response'):
                detailed_error += f"\nRéponse du serveur : {e.response.text}"
            self.logger.error(f"Erreur de requête : {detailed_error}")
            raise APIError(f"Échec de la requête : {detailed_error}")
    
    def verify_token(self, use_cache: bool = True) -> bool:
        """
        Vérifie la validité du token API.
        """
        try:
            # Log détaillé du token
            self.logger.debug(f"Vérification du token. Longueur : {len(self.config.api.mapillary_token)}")
            self.logger.debug(f"Début du token : {self.config.api.mapillary_token[:10]}")
            
            # Paramètres de test
            params = {
                "fields": "id",
                "bbox": "2.3522,48.8566,2.3523,48.8567",  # Petit secteur de Paris
                "limit": 1
            }
            
            # Faire la requête
            response = self._make_request("images", params, use_cache=False)
            
            # Log de la réponse
            self.logger.info(f"Réponse de vérification de token : {response}")
            
            # Vérifier la structure de la réponse
            result = isinstance(response, dict) and 'data' in response
            
            self.logger.info(f"Résultat de la vérification du token : {result}")
            return result
        
        except Exception as e:
            # Journalisation très détaillée de l'exception
            self.logger.error(f"Erreur lors de la vérification du token : {str(e)}")
            return False
    
    def get_images_in_bbox(
        self, 
        bbox: Dict[str, float], 
        limit: int = 100,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> List[Image]:
        """
        Récupère les images dans une bounding box donnée.
        """
        # Log détaillé des paramètres d'entrée
        self.logger.debug(f"Paramètres bbox: {bbox}")
        self.logger.debug(f"Limite: {limit}")
        
        # Génération de la chaîne bbox
        bbox_str = f"{bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']}"
        self.logger.debug(f"Chaîne bbox générée: {bbox_str}")
        
        # Paramètres de la requête
        params = {
            "bbox": bbox_str,
            "fields": "id,geometry,captured_at,thumb_1024_url",
            "limit": limit
        }
        
        try:
            # Log avant la requête
            self.logger.debug("Tentative de requête à l'API Mapillary")
            self.logger.debug(f"URL endpoint: images")
            self.logger.debug(f"Paramètres: {params}")
            
            # Effectuer la requête
            response = self._make_request(
                "images", 
                params, 
                use_cache=use_cache,
                force_refresh=force_refresh
            )
            
            # Log de la réponse
            self.logger.debug(f"Réponse reçue. Clés: {response.keys() if isinstance(response, dict) else 'Non dict'}")
            
            if not response or "data" not in response:
                self.logger.warning("Aucune donnée reçue de l'API Mapillary")
                return []
            
            # Log du nombre de données reçues
            self.logger.debug(f"Nombre d'images reçues : {len(response['data'])}")
            
            images = []
            for img_data in response["data"]:
                try:
                    # Log détaillé de chaque image
                    self.logger.debug(f"Traitement de l'image: {img_data.get('id', 'unknown')}")
                    
                    # Extraire les coordonnées de manière sécurisée
                    geometry = img_data.get('geometry', {})
                    self.logger.debug(f"Géométrie de l'image: {geometry}")
                    
                    if not geometry:
                        self.logger.warning(f"Image {img_data.get('id', 'unknown')} ignorée : géométrie manquante")
                        continue
                    
                    # Vérifier et extraire les coordonnées
                    coordinates = geometry.get('coordinates', [])
                    self.logger.debug(f"Coordonnées: {coordinates}")
                    
                    if not coordinates or len(coordinates) < 2:
                        self.logger.warning(f"Image {img_data.get('id', 'unknown')} ignorée : coordonnées invalides")
                        continue
                    
                    lon, lat = coordinates
                    
                    # Créer un objet Image
                    image = Image(
                        id=img_data["id"],
                        path=img_data.get("thumb_1024_url", ""),
                        width=1024,  # Taille par défaut du thumbnail
                        height=1024,
                        source=ImageSource.MAPILLARY,
                        metadata={
                            "captured_at": img_data.get("captured_at"),
                            "coordinates": {
                                "latitude": lat,
                                "longitude": lon
                            },
                            "raw_data": img_data  # Ajouter les données brutes pour débogage
                        }
                    )
                    images.append(image)
                    
                except Exception as e:
                    self.logger.error(f"Erreur de traitement de l'image {img_data.get('id', 'unknown')}: {str(e)}")
                    # Log de la trace complète
                    import traceback
                    self.logger.error(traceback.format_exc())
            
            self.logger.info(f"Récupéré {len(images)} images de Mapillary")
            return images
            
        except Exception as e:
            # Log détaillé de l'erreur
            self.logger.error(f"Échec de récupération des images : {str(e)}")
            
            # Log de la trace complète
            import traceback
            self.logger.error(traceback.format_exc())
            
            raise APIError(f"Échec de récupération des images Mapillary : {str(e)}")
    
    def get_image_detections(
        self, 
        image_id: str,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> List[Annotation]:
        """
        Récupère les détections pour une image spécifique et les convertit en annotations.
        
        Args:
            image_id: ID de l'image
            use_cache: Utiliser le cache si disponible
            force_refresh: Forcer le rafraîchissement du cache
            
        Returns:
            Liste des annotations trouvées
        """
        params = {
            "fields": self.config.api.fields.get("detections", "id,value,geometry,area,properties")
        }
        
        try:
            response = self._make_request(
                f"{image_id}/detections", 
                params, 
                use_cache=use_cache,
                force_refresh=force_refresh
            )
            
            if not response or "data" not in response:
                self.logger.warning(f"Aucune détection trouvée pour l'image {image_id}")
                return []
            
            annotations = []
            config = self.config_manager.get_config()
            detection_config = config.mapillary_config.detection_mapping.conversion
            min_confidence = detection_config.get("min_confidence", 0.5)
            
            for detection in response.get("data", []):
                try:
                    # Ignorer les détections avec une confiance trop basse
                    confidence = detection.get('properties', {}).get('confidence', 0.9)
                    if confidence < min_confidence:
                        continue
                    
                    # Récupérer la valeur (type de panneau)
                    value = detection.get("value", "")
                    
                    # Déterminer le class_id à partir du mapping
                    class_id = None
                    if hasattr(config, 'mapillary_config') and hasattr(config.mapillary_config, 'class_mapping'):
                        # Récupérer le mapping des classes
                        class_mapping = config.mapillary_config.class_mapping
                        # Chercher une correspondance
                        class_id = class_mapping.get(value)
                    
                    # Si aucune classe correspondante, utiliser une valeur par défaut
                    if class_id is None:
                        # Prendre la première classe disponible par défaut
                        class_id = 0
                    
                    # Extraire la géométrie
                    geometry = detection.get('geometry', {})
                    
                    # Déterminer les coordonnées de la bounding box
                    bbox = self._extract_bbox_from_detection(geometry, detection)
                    
                    # Si la bbox est valide, créer une annotation
                    if bbox:
                        annotation = Annotation(
                            class_id=class_id,
                            bbox=bbox,
                            confidence=confidence,
                            type=AnnotationType.BBOX,
                            metadata={
                                "mapillary_id": detection.get("id", ""),
                                "value": value,
                                "area": detection.get("area", 0)
                            }
                        )
                        
                        annotations.append(annotation)
                    
                except Exception as e:
                    self.logger.error(f"Erreur lors du traitement de la détection : {str(e)}")
            
            self.logger.info(f"Récupéré {len(annotations)} annotations pour l'image {image_id}")
            return annotations
            
        except Exception as e:
            self.logger.error(f"Échec de la récupération des détections : {str(e)}")
            return []
    
    def download_image(
        self, 
        url: str, 
        use_cache: bool = True
    ) -> Optional[bytes]:
        """
        Télécharge une image depuis une URL avec mise en cache.
        
        Args:
            url: URL de l'image
            use_cache: Utiliser le cache si disponible
            
        Returns:
            Données de l'image ou None en cas d'erreur
        """
        try:
            # Clé de cache pour cette URL
            cache_key = f"image:{url}"
            
            # Vérifier le cache si activé
            if self.cache and use_cache:
                cached_data = self.cache.get(cache_key)
                if cached_data:
                    # Si en cache, les données sont encodées en base64
                    import base64
                    return base64.b64decode(cached_data)
            
            # Vérifier et attendre si nécessaire pour respecter les limites de taux
            if not self.rate_limiter.check_and_update():
                if not self.rate_limiter.wait_if_needed():
                    raise RateLimitError(
                        "Limite de taux atteinte, impossible de télécharger l'image",
                        reset_time=datetime.now() + timedelta(minutes=1)
                    )
            
            # Télécharger l'image
            self.last_request_time = datetime.now()
            response = self.session.get(url, timeout=self.config.api.request_timeout)
            self.request_count += 1
            
            if response.status_code == 200:
                # Vérifier le type de contenu
                content_type = response.headers.get('Content-Type', '').lower()
                if not content_type.startswith('image/'):
                    self.logger.warning(f"Type de contenu inattendu : {content_type}")
                
                # Récupérer le contenu de l'image
                image_data = response.content
                
                # Mettre en cache si activé
                if self.cache and use_cache:
                    # Encoder en base64 pour le stockage JSON
                    import base64
                    encoded_data = base64.b64encode(image_data).decode('utf-8')
                    self.cache.set(cache_key, encoded_data)
                
                return image_data
            else:
                self.logger.error(f"Échec du téléchargement de l'image : Code {response.status_code}")
                self.request_errors += 1
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur lors du téléchargement de l'image : {str(e)}")
            self.request_errors += 1
            return None
    
    def search_images(
        self, 
        bbox: Optional[Dict[str, float]] = None, 
        date_range: Optional[Dict[str, str]] = None,
        max_results: int = 100,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> List[Image]:
        """
        Recherche des images avec des filtres optionnels.
        
        Args:
            bbox: Bounding box géographique
            date_range: Plage de dates (début, fin)
            max_results: Nombre maximum de résultats
            use_cache: Utiliser le cache si disponible
            force_refresh: Forcer le rafraîchissement du cache
            
        Returns:
            Liste des images trouvées
        """
        try:
            # Préparer les paramètres de recherche
            params = {
                "limit": min(max_results, self.config.api.batch_size)
            }
            
            # Ajouter la bounding box si spécifiée
            if bbox:
                params["bbox"] = (
                    f"{bbox['min_lon']},{bbox['min_lat']},"
                    f"{bbox['max_lon']},{bbox['max_lat']}"
                )
            
            # Ajouter la plage de dates si spécifiée
            if date_range:
                params["start_time"] = date_range.get('start')
                params["end_time"] = date_range.get('end')
            
            # Exécuter la requête
            response = self._make_request(
                "images", 
                params, 
                use_cache=use_cache,
                force_refresh=force_refresh
            )
            
            # Convertir les résultats en objets Image
            images = []
            for img_data in response.get('data', []):
                try:
                    image = Image(
                        id=img_data['id'],
                        path=img_data.get('thumb_1024_url', ''),
                        width=1024,  # Thumbnail par défaut
                        height=1024,
                        source=ImageSource.MAPILLARY,
                        metadata={
                            "captured_at": img_data.get('captured_at'),
                            "coordinates": img_data.get('geometry', {}).get('coordinates', [])
                        }
                    )
                    images.append(image)
                except Exception as e:
                    self.logger.warning(f"Erreur de traitement de l'image : {str(e)}")
            
            # Si on n'a pas atteint le maximum et qu'il y a un token de pagination
            if (len(images) < max_results and 
                len(images) > 0 and
                response.get('next_page_token')):
                
                # Récupérer la page suivante
                remaining = max_results - len(images)
                next_token = response.get('next_page_token')
                next_params = {**params, "page_token": next_token}
                
                try:
                    next_images = self._paginate_search(
                        "images", 
                        next_params, 
                        remaining,
                        use_cache,
                        force_refresh
                    )
                    images.extend(next_images)
                except Exception as e:
                    self.logger.warning(f"Erreur lors de la pagination : {str(e)}")
            
            return images[:max_results]  # S'assurer de ne pas dépasser le maximum demandé
            
        except Exception as e:
            self.logger.error(f"Échec de la recherche d'images : {str(e)}")
            return []
    
    def _paginate_search(
        self, 
        endpoint: str, 
        params: Dict, 
        max_results: int,
        use_cache: bool,
        force_refresh: bool
    ) -> List[Image]:
        """
        Effectue une pagination pour récupérer plus de résultats.
        
        Args:
            endpoint: Point de terminaison de l'API
            params: Paramètres de la requête
            max_results: Nombre maximum de résultats
            use_cache: Utiliser le cache si disponible
            force_refresh: Forcer le rafraîchissement du cache
            
        Returns:
            Liste des images supplémentaires
        """
        images = []
        
        while len(images) < max_results:
            # Limiter le nombre par page
            page_params = {
                **params,
                "limit": min(max_results - len(images), self.config.api.batch_size)
            }
            
            # Faire la requête
            response = self._make_request(
                endpoint, 
                page_params, 
                use_cache=use_cache,
                force_refresh=force_refresh
            )
            
            # Convertir les résultats
            page_images = []
            for img_data in response.get('data', []):
                try:
                    image = Image(
                        id=img_data['id'],
                        path=img_data.get('thumb_1024_url', ''),
                        width=1024,
                        height=1024,
                        source=ImageSource.MAPILLARY,
                        metadata={
                            "captured_at": img_data.get('captured_at'),
                            "coordinates": img_data.get('geometry', {}).get('coordinates', [])
                        }
                    )
                    page_images.append(image)
                except Exception as e:
                    self.logger.warning(f"Erreur de traitement de l'image : {str(e)}")
            
            # Ajouter les images de cette page
            images.extend(page_images)
            
            # S'il n'y a plus de token de pagination ou pas de résultats, arrêter
            if not response.get('next_page_token') or not page_images:
                break
                
            # Mettre à jour le token pour la page suivante
            params["page_token"] = response.get('next_page_token')
        
        return images
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques d'utilisation du service API.
        
        Returns:
            Statistiques d'utilisation
        """
        stats = {
            "request_count": self.request_count,
            "error_count": self.request_errors,
            "error_rate": (self.request_errors / self.request_count) * 100 if self.request_count > 0 else 0,
            "last_request": self.last_request_time.isoformat() if self.last_request_time else None,
            "cache_enabled": self.cache is not None
        }
        
        # Ajouter les statistiques du gestionnaire de limites
        stats["rate_limits"] = self.rate_limiter.get_stats()
        
        # Ajouter les statistiques du cache si activé
        if self.cache:
            stats["cache"] = self.cache.get_stats()
        
        return stats
    
    def clear_cache(self, expired_only: bool = False) -> int:
        """
        Vide le cache du service.
        
        Args:
            expired_only: Ne supprimer que les entrées expirées
            
        Returns:
            Nombre de fichiers supprimés
        """
        if not self.cache:
            return 0
            
        if expired_only:
            return self.cache.clear_expired()
        else:
            return self.cache.clear()
        
    def _extract_bbox_from_detection(self, geometry: Dict, detection: Dict) -> Optional[BoundingBox]:
        """
        Extrait une bounding box à partir des données de détection Mapillary.
        
        Args:
            geometry: Géométrie de la détection
            detection: Données complètes de la détection
            
        Returns:
            BoundingBox normalisée ou None si impossible à extraire
        """
        try:
            # Vérifier le type de géométrie
            if not geometry or "type" not in geometry:
                return None
            
            # Cas selon le type de géométrie
            geo_type = geometry.get("type", "").lower()
            coordinates = geometry.get("coordinates", [])
            
            if geo_type == "polygon" and coordinates:
                # Pour un polygone, trouver les min/max pour créer la bounding box
                if not coordinates or not coordinates[0]:
                    return None
                    
                # Les coordonnées d'un polygone: [[[lon1, lat1], [lon2, lat2], ...]]
                points = coordinates[0]
                
                # Extraire les points x, y (longitude, latitude) du polygone
                x_coords = [p[0] for p in points if len(p) >= 2]
                y_coords = [p[1] for p in points if len(p) >= 2]
                
                if not x_coords or not y_coords:
                    return None
                    
                # Trouver les min/max
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                
                # Calculer la largeur et la hauteur
                width = max_x - min_x
                height = max_y - min_y
                
                # Créer la bounding box normalisée (0-1)
                bbox = BoundingBox(
                    x=min_x,
                    y=min_y,
                    width=width,
                    height=height
                )
                
                return bbox
                
            elif geo_type == "point" and coordinates:
                # Pour un point, créer une petite bounding box autour
                if len(coordinates) < 2:
                    return None
                    
                x, y = coordinates[0], coordinates[1]
                
                # Utiliser une taille arbitraire pour la bbox autour du point
                # Ces valeurs peuvent être ajustées selon les besoins
                size = 0.02  # 2% de l'image
                
                bbox = BoundingBox(
                    x=x - size/2,
                    y=y - size/2,
                    width=size,
                    height=size
                )
                
                return bbox
            
            # Si nous avons des propriétés avec des valeurs explicites x, y, width, height
            properties = detection.get("properties", {})
            if all(key in properties for key in ["x", "y", "width", "height"]):
                bbox = BoundingBox(
                    x=properties["x"],
                    y=properties["y"],
                    width=properties["width"],
                    height=properties["height"]
                )
                return bbox
                
            # Si nous avons un champ "area" avec une valeur de bbox
            area = detection.get("area", {})
            if isinstance(area, dict) and all(key in area for key in ["x", "y", "width", "height"]):
                bbox = BoundingBox(
                    x=area["x"],
                    y=area["y"],
                    width=area["width"],
                    height=area["height"]
                )
                return bbox
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction de la bounding box: {str(e)}")
            return None