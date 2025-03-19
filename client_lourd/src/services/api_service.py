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
    
    def get_images_in_bbox(self, bbox: Dict[str, float], limit: int = 100, use_cache: bool = True, force_refresh: bool = False, object_types: Optional[List[str]] = None) -> List[Image]:
        """
        Récupère les images dans une bounding box donnée avec une meilleure gestion des erreurs.
        """
        try:
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
            
            # Ajouter le filtre par type d'objets si spécifié
            if object_types:
                filter_values = ",".join(object_types)
                params["has_object_detections"] = filter_values
                self.logger.debug(f"Filtrage par types d'objets: {filter_values}")
            
            # Effectuer la requête
            response = self._make_request(
                "images", 
                params, 
                use_cache=use_cache,
                force_refresh=force_refresh
            )
            
            # Validation plus stricte de la réponse
            if not isinstance(response, dict):
                self.logger.warning(f"Réponse API invalide: attendu dict, reçu {type(response)}")
                return []
                
            if "data" not in response:
                self.logger.warning("Clé 'data' manquante dans la réponse API")
                return []
                
            data = response["data"]
            if not isinstance(data, list):
                self.logger.warning(f"Format de données invalide: attendu list, reçu {type(data)}")
                return []
            
            # Log du nombre de données reçues
            self.logger.debug(f"Nombre d'images reçues : {len(data)}")
            
            images = []
            for img_data in data:
                try:
                    if not isinstance(img_data, dict):
                        self.logger.warning(f"Format d'image invalide: {type(img_data)}")
                        continue
                        
                    # Vérifier les champs obligatoires
                    if "id" not in img_data:
                        self.logger.warning("Image sans ID ignorée")
                        continue
                    
                    # Vérification de la géométrie
                    geometry = img_data.get('geometry', {})
                    if not geometry or not isinstance(geometry, dict):
                        self.logger.warning(f"Image {img_data.get('id', 'unknown')} ignorée : géométrie manquante ou invalide")
                        continue
                    
                    coordinates = geometry.get('coordinates', [])
                    if not coordinates or len(coordinates) < 2:
                        self.logger.warning(f"Image {img_data.get('id', 'unknown')} ignorée : coordonnées invalides")
                        continue
                    
                    lon, lat = coordinates
                    
                    # Créer l'objet Image avec des valeurs par défaut sécurisées
                    image = Image(
                        id=img_data["id"],
                        path=img_data.get("thumb_1024_url", ""),
                        width=1024,  # Valeur par défaut pour thumbnail
                        height=1024,
                        source=ImageSource.MAPILLARY,
                        metadata={
                            "captured_at": img_data.get("captured_at"),
                            "coordinates": {
                                "latitude": lat,
                                "longitude": lon
                            },
                            "raw_data": img_data
                        }
                    )
                    images.append(image)
                    
                except Exception as e:
                    self.logger.error(f"Erreur de traitement de l'image {img_data.get('id', 'unknown')}: {str(e)}")
            
            self.logger.info(f"Récupéré {len(images)} images de Mapillary")
            return images
            
        except Exception as e:
            self.logger.error(f"Échec de récupération des images : {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []  # Retourner une liste vide en cas d'erreur plutôt que lever une exception
    
    def get_image_detections(
        self, 
        image_id: str,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> List[Annotation]:
        """
        Récupère les détections de panneaux de signalisation pour une image spécifique et décode 
        correctement les coordonnées.
        
        Args:
            image_id: ID de l'image
            use_cache: Utiliser le cache si disponible
            force_refresh: Forcer le rafraîchissement du cache
            
        Returns:
            Liste des annotations de panneaux de signalisation trouvées
        """
        # Paramètres spécifiques avec les bons champs et filtres
        params = {
            "fields": "id,value,geometry,properties",
            # Filtrer uniquement les panneaux de signalisation
            "values": "regulatory--*,warning--*,information--*,complementary--*"
        }
        
        try:
            # Appel API avec filtrage des valeurs
            self.logger.info(f"Récupération des détections de panneaux pour l'image {image_id}")
            
            response = self._make_request(
                f"{image_id}/detections", 
                params, 
                use_cache=use_cache,
                force_refresh=force_refresh
            )
            
            if not response or "data" not in response:
                self.logger.warning(f"Aucune détection trouvée pour l'image {image_id}")
                return []
            
            # Log pour débogage
            detections_count = len(response.get('data', []))
            self.logger.debug(f"Nombre de détections reçues: {detections_count}")
            
            annotations = []
            config = self.config_manager.get_config()
            
            # Récupérer le mapping des classes et les paramètres
            detection_config = {}
            class_mapping = {}
            
            if hasattr(config, 'mapillary_config'):
                if isinstance(config.mapillary_config, dict):
                    class_mapping = config.mapillary_config.get('class_mapping', {})
                    
                    if 'detection_mapping' in config.mapillary_config:
                        detection_mapping = config.mapillary_config['detection_mapping']
                        if isinstance(detection_mapping, dict) and 'conversion' in detection_mapping:
                            detection_config = detection_mapping['conversion']

            # Valeur de confiance minimale (0.3 par défaut)
            min_confidence = detection_config.get('min_confidence', 0.3)
            
            # Statistiques pour le débogage
            filtered_out_types = {}
            
            # Importer les bibliothèques nécessaires pour le décodage
            import base64
            import mapbox_vector_tile
            
            for detection in response.get("data", []):
                try:
                    # Récupérer la valeur (type de panneau)
                    value = detection.get("value", "")
                    self.logger.debug(f"Traitement de la détection: {value}")
                    
                    # FILTRE SUPPLÉMENTAIRE: Vérifier si c'est un panneau de signalisation
                    valid_prefixes = ["regulatory--", "warning--", "information--", "complementary--"]
                    if not any(value.startswith(prefix) for prefix in valid_prefixes):
                        # Compter les types filtrés pour analyse
                        type_prefix = value.split('--')[0] if '--' in value else value
                        filtered_out_types[type_prefix] = filtered_out_types.get(type_prefix, 0) + 1
                        self.logger.debug(f"Ignorer l'objet non-panneau: {value}")
                        continue
                    
                    # Récupérer la confiance depuis les propriétés
                    properties = detection.get('properties', {})
                    confidence = None
                    
                    # Essayer différentes clés possibles pour la confiance
                    confidence_keys = ['confidence', 'detection_score', 'score', 'probability']
                    for key in confidence_keys:
                        if key in properties and properties[key] is not None:
                            try:
                                confidence = float(properties[key])
                                break
                            except (ValueError, TypeError):
                                pass
                    
                    # Si aucune confiance trouvée, utiliser une valeur par défaut
                    if confidence is None:
                        confidence = 0.8  # Valeur par défaut raisonnable
                        self.logger.debug(f"Confiance non trouvée pour {value}, utilisation de la valeur par défaut: {confidence}")
                    
                    # Ignorer les détections avec une confiance trop basse
                    if confidence < min_confidence:
                        self.logger.debug(f"Détection ignorée: confiance ({confidence}) < seuil ({min_confidence})")
                        continue
                    
                    # Déterminer le class_id à partir du mapping
                    class_id = None
                    
                    # Recherche dans le mapping
                    if value in class_mapping:
                        class_id = int(class_mapping[value]) if isinstance(class_mapping[value], (int, str)) and str(class_mapping[value]).isdigit() else class_mapping[value]
                        self.logger.debug(f"Classe trouvée dans le mapping: '{value}' -> ID {class_id}")
                    else:
                        # Si pas trouvé, utiliser une valeur par défaut
                        class_id = 0
                        self.logger.warning(f"Classe non trouvée pour '{value}', utilisation de la classe par défaut (0)")
                    
                    # Récupérer et décoder les coordonnées de segmentation
                    geometry_base64 = detection.get("geometry")
                    if not geometry_base64:
                        self.logger.warning(f"Détection sans géométrie pour {value}")
                        continue
                    
                    # Décodage selon la documentation Mapillary
                    try:
                        decoded_data = base64.decodebytes(geometry_base64.encode('utf-8'))
                        detection_geometry = mapbox_vector_tile.decode(decoded_data)
                        
                        # Le format est généralement: {'mpy-or': {'extent': 4096, 'features': [{'geometry': ...}]}}
                        if 'mpy-or' not in detection_geometry:
                            self.logger.warning(f"Format inattendu pour la géométrie: {detection_geometry}")
                            continue
                            
                        tile_layer = detection_geometry['mpy-or']
                        extent = tile_layer.get('extent', 4096)  # Valeur par défaut 4096
                        
                        features = tile_layer.get('features', [])
                        if not features:
                            self.logger.warning(f"Pas de fonctionnalités dans la géométrie pour {value}")
                            continue
                            
                        # Prendre la première fonctionnalité
                        feature = features[0]
                        geometry_data = feature.get('geometry', {})
                        
                        if geometry_data.get('type') == 'Polygon':
                            # Récupérer les coordonnées du polygone et normaliser
                            coords = geometry_data.get('coordinates', [[]])[0]
                            
                            if not coords:
                                self.logger.warning(f"Coordonnées vides pour {value}")
                                continue
                                
                            # Normaliser les coordonnées (diviser par l'étendue)
                            normalized_coords = [(x/extent, 1 - (y/extent)) for x, y in coords]

                            # Calculer la bounding box à partir des coordonnées normalisées
                            x_coords = [x for x, y in normalized_coords]
                            y_coords = [y for x, y in normalized_coords]

                            min_x, max_x = min(x_coords), max(x_coords)
                            min_y, max_y = min(y_coords), max(y_coords)

                            width = max_x - min_x
                            height = max_y - min_y

                            # Créer la bounding box
                            bbox = BoundingBox(
                                x=min_x,
                                y=min_y,
                                width=width,
                                height=height
                            )
                            
                            # Créer des métadonnées enrichies pour faciliter l'affichage
                            parts = value.split("--")
                            sign_category = parts[0] if len(parts) > 0 else ""
                            sign_type = parts[1].replace("-", " ").title() if len(parts) > 1 else ""
                            
                            # Créer l'annotation
                            annotation = Annotation(
                                class_id=class_id,
                                bbox=bbox,
                                confidence=confidence,
                                type=AnnotationType.BBOX,
                                metadata={
                                    "mapillary_id": detection.get("id", ""),
                                    "value": value,        # Nom original du panneau
                                    "sign_name": value,    # Duplicate pour assurer la compatibilité
                                    "sign_category": sign_category,
                                    "sign_type": sign_type,
                                    "area": properties.get("area", 0),
                                    "normalized_polygon": normalized_coords,
                                    "detection_id": detection.get("id", "unknown")
                                }
                            )
                            
                            annotations.append(annotation)
                            self.logger.debug(f"Annotation créée avec succès pour {value}")
                        else:
                            self.logger.warning(f"Type de géométrie non pris en charge: {geometry_data.get('type')}")
                            
                    except Exception as e:
                        self.logger.error(f"Erreur lors du décodage de la géométrie: {str(e)}")
                        import traceback
                        self.logger.error(traceback.format_exc())
                    
                except Exception as e:
                    self.logger.error(f"Erreur lors du traitement de la détection: {str(e)}")
                    import traceback
                    self.logger.error(traceback.format_exc())
            
            # Afficher les statistiques de filtrage si disponibles
            if filtered_out_types:
                self.logger.info(f"Types d'objets filtrés: {filtered_out_types}")
            
            self.logger.info(f"Récupéré {len(annotations)} annotations pour l'image {image_id}")
            
            # Ajouter un tri par taille pour les annotations (les plus grandes d'abord)
            # Cela permet de mieux voir les panneaux importants
            annotations.sort(key=lambda a: a.bbox.width * a.bbox.height, reverse=True)
            
            return annotations
            
        except Exception as e:
            self.logger.error(f"Échec de la récupération des détections: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
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
        

    def _extract_bbox_from_detection(self, geometry: Any, detection: Dict) -> Optional[BoundingBox]:
        """
        Extrait une bounding box à partir des données de détection Mapillary.
        Avec priorité sur les données les plus précises et meilleure gestion des erreurs.
        
        Args:
            geometry: Géométrie de la détection
            detection: Données complètes de la détection
            
        Returns:
            BoundingBox normalisée ou None si impossible à extraire
        """
        try:
            detection_id = detection.get('id', 'unknown')
            self.logger.debug(f"Extraction bbox pour détection {detection_id}")
            
            # Fonction utilitaire pour normaliser et valider une bbox
            def normalize_and_validate(x, y, width, height):
                # S'assurer que toutes les valeurs sont des flottants
                try:
                    x = float(x)
                    y = float(y)
                    width = float(width)
                    height = float(height)
                except (ValueError, TypeError):
                    return None
                    
                # S'assurer que les dimensions sont positives
                if width <= 0 or height <= 0:
                    width = max(0.01, width)  # minimum 1% de l'image
                    height = max(0.01, height)
                    
                # S'assurer que tout est dans les limites [0,1]
                x = max(0, min(x, 1.0))
                y = max(0, min(y, 1.0))
                
                # S'assurer que x+width et y+height ne dépassent pas 1
                if x + width > 1.0:
                    width = 1.0 - x
                if y + height > 1.0:
                    height = 1.0 - y
                    
                return BoundingBox(x=x, y=y, width=width, height=height)
            
            # PRIORITÉ 1: Extraction depuis "area" (le plus fiable)
            area = detection.get("area", {})
            if isinstance(area, dict) and all(key in area for key in ["x", "y", "width", "height"]):
                bbox = normalize_and_validate(area["x"], area["y"], area["width"], area["height"])
                if bbox:
                    self.logger.debug(f"BoundingBox extraite de area: {bbox}")
                    return bbox
                
            # PRIORITÉ 2: Extraction depuis "properties"
            properties = detection.get("properties", {})
            if isinstance(properties, dict):
                # Vérifier s'il y a des coordonnées directes
                if all(key in properties for key in ["x", "y", "width", "height"]):
                    bbox = normalize_and_validate(
                        properties["x"], properties["y"], 
                        properties["width"], properties["height"]
                    )
                    if bbox:
                        self.logger.debug(f"BoundingBox extraite de properties: {bbox}")
                        return bbox
                        
                # Vérifier s'il y a un champ 'bbox' ou 'bounding_box'
                bbox_field = properties.get('bbox', properties.get('bounding_box'))
                if isinstance(bbox_field, (list, tuple)) and len(bbox_field) >= 4:
                    # Format [x, y, width, height] ou [x1, y1, x2, y2]
                    if len(bbox_field) == 4:
                        if bbox_field[2] > bbox_field[0] and bbox_field[3] > bbox_field[1]:
                            # C'est probablement [x1, y1, x2, y2]
                            x = bbox_field[0]
                            y = bbox_field[1]
                            width = bbox_field[2] - bbox_field[0]
                            height = bbox_field[3] - bbox_field[1]
                        else:
                            # C'est probablement [x, y, width, height]
                            x = bbox_field[0]
                            y = bbox_field[1]
                            width = bbox_field[2]
                            height = bbox_field[3]
                            
                        bbox = normalize_and_validate(x, y, width, height)
                        if bbox:
                            self.logger.debug(f"BoundingBox extraite du champ bbox: {bbox}")
                            return bbox
            
            # PRIORITÉ 3: Extraction depuis "segmentation" ou "segmentations"
            segmentations = detection.get("segmentations", detection.get("segmentation", []))
            if segmentations and isinstance(segmentations, list) and len(segmentations) > 0:
                all_x = []
                all_y = []
                
                # Traiter toutes les segmentations
                for seg in segmentations:
                    if isinstance(seg, list):
                        for point in seg:
                            if isinstance(point, list) and len(point) >= 2:
                                try:
                                    all_x.append(float(point[0]))
                                    all_y.append(float(point[1]))
                                except (ValueError, TypeError):
                                    continue
                
                if all_x and all_y:
                    min_x = min(all_x)
                    max_x = max(all_x)
                    min_y = min(all_y)
                    max_y = max(all_y)
                    
                    width = max_x - min_x
                    height = max_y - min_y
                    
                    bbox = normalize_and_validate(min_x, min_y, width, height)
                    if bbox:
                        self.logger.debug(f"BoundingBox extraite des segmentations: {bbox}")
                        return bbox
            
            # PRIORITÉ 4: Extraction depuis la géométrie si c'est un polygone
            if isinstance(geometry, dict) and "coordinates" in geometry:
                geo_type = geometry.get("type", "").lower()
                coordinates = geometry.get("coordinates", [])
                
                # Traiter les différents types de géométrie
                if geo_type == "polygon" and coordinates and isinstance(coordinates, list):
                    # Pour un polygone, les points sont dans le premier élément
                    points = coordinates[0] if len(coordinates) > 0 and isinstance(coordinates[0], list) else coordinates
                    
                    x_coords = []
                    y_coords = []
                    
                    for point in points:
                        if isinstance(point, list) and len(point) >= 2:
                            try:
                                x_coords.append(float(point[0]))
                                y_coords.append(float(point[1]))
                            except (ValueError, TypeError):
                                continue
                    
                    if x_coords and y_coords:
                        min_x = min(x_coords)
                        max_x = max(x_coords)
                        min_y = min(y_coords)
                        max_y = max(y_coords)
                        
                        width = max_x - min_x
                        height = max_y - min_y
                        
                        bbox = normalize_and_validate(min_x, min_y, width, height)
                        if bbox:
                            self.logger.debug(f"BoundingBox extraite du polygone: {bbox}")
                            return bbox
                
                # Traiter le cas d'un point (moins précis)
                elif geo_type == "point" and coordinates and isinstance(coordinates, list) and len(coordinates) >= 2:
                    # Pour un point, on crée une bbox autour du point
                    try:
                        x = float(coordinates[0])
                        y = float(coordinates[1])
                        
                        # Créer une boîte de 5% autour du point
                        width = 0.05
                        height = 0.05
                        
                        x = x - width/2
                        y = y - height/2
                        
                        bbox = normalize_and_validate(x, y, width, height)
                        if bbox:
                            self.logger.debug(f"BoundingBox extraite d'un point: {bbox}")
                            return bbox
                    except (ValueError, TypeError, IndexError):
                        pass
            
            # SOLUTION DE REPLI: création d'une bbox au centre de l'image
            size = 0.2  # 20% de l'image, plus petit pour être moins intrusif
            bbox_x = (1 - size) / 2
            bbox_y = (1 - size) / 2
            
            bbox = BoundingBox(x=bbox_x, y=bbox_y, width=size, height=size)
            
            self.logger.warning(f"Création d'une bounding box artificielle pour {detection_id}: {bbox}")
            return bbox
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction de la bounding box: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            # Même en cas d'erreur, créer une bbox par défaut, mais plus petite
            size = 0.15  # 15% de l'image
            bbox_x = (1 - size) / 2
            bbox_y = (1 - size) / 2
            
            return BoundingBox(x=bbox_x, y=bbox_y, width=size, height=size)
            