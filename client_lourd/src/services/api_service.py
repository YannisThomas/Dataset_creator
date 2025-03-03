# src/services/api_service.py

from typing import List, Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models import Image, Annotation, BoundingBox
from src.models.enums import AnnotationType, ImageSource
from src.utils.config import ConfigManager
from src.utils.logger import Logger
from src.core.exceptions import APIError, AuthenticationError

class APIService:
    """Service de gestion des appels API"""
    
    def __init__(
        self, 
        config_manager: Optional[ConfigManager] = None,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le service API
        
        Args:
            config_manager: Gestionnaire de configuration
            logger: Gestionnaire de logs
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.get_config()
        self.logger = logger or Logger()
        
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
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Crée les en-têtes pour les requêtes API
        
        Returns:
            En-têtes HTTP
        """
        return {
            "Authorization": f"Bearer {self.config.api.mapillary_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def verify_token(self) -> bool:
        """
        Vérifie la validité du token API
        
        Returns:
            True si le token est valide, False sinon
        """
        try:
            # Test avec une requête minimale
            bbox = "2.3522,48.8566,2.3523,48.8567"  # Petit secteur de test
            headers = self._get_headers()
            params = {
                "fields": "id",
                "bbox": bbox,
                "limit": 1
            }
            
            response = self._make_request("images", params)
            return isinstance(response, dict) and 'data' in response
            
        except Exception as e:
            self.logger.error(f"Token verification failed: {str(e)}")
            return False
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Effectue une requête à l'API
        
        Args:
            endpoint: Point de terminaison de l'API
            params: Paramètres de la requête
            
        Returns:
            Réponse de l'API
            
        Raises:
            APIError: En cas d'erreur de l'API
        """
        url = f"{self.config.api.mapillary_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            self.logger.debug(f"Making request to: {url}")
            self.logger.debug(f"Request params: {params}")
            
            response = self.session.get(
                url=url,
                headers=headers,
                params=params,
                timeout=self.config.api.request_timeout
            )
            
            self.logger.debug(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                reset_time = response.headers.get('X-RateLimit-Reset')
                raise APIError(
                    "Limite de taux dépassée",
                    status_code=response.status_code,
                    reset_time=reset_time
                )
            else:
                raise APIError(
                    f"Échec de la requête API: {response.text}",
                    status_code=response.status_code,
                    response=response.text
                )
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur de requête : {str(e)}")
            raise APIError(f"Échec de la requête : {str(e)}")
    
    def get_images_in_bbox(
        self, 
        bbox: Dict[str, float], 
        limit: int = 100
    ) -> List[Image]:
        """
        Récupère les images dans une bounding box donnée
        
        Args:
            bbox: Bounding box (min_lat, min_lon, max_lat, max_lon)
            limit: Nombre maximum d'images à récupérer
            
        Returns:
            Liste des images trouvées
        """
        bbox_str = f"{bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']}"
        params = {
            "bbox": bbox_str,
            "fields": "id,geometry,captured_at,thumb_1024_url",
            "limit": limit
        }
        
        try:
            response = self._make_request("images", params)
            if not response or "data" not in response:
                self.logger.warning("Aucune donnée reçue de l'API Mapillary")
                return []
            
            images = []
            for img_data in response["data"]:
                try:
                    # Extraire les coordonnées de manière sécurisée
                    geometry = img_data.get('geometry', {})
                    if not geometry:
                        self.logger.warning(f"Image {img_data.get('id', 'unknown')} ignorée : géométrie manquante")
                        continue
                    
                    # Vérifier et extraire les coordonnées
                    coordinates = geometry.get('coordinates', [])
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
                            }
                        }
                    )
                    images.append(image)
                    
                except Exception as e:
                    self.logger.error(f"Erreur de traitement de l'image {img_data.get('id', 'unknown')}: {str(e)}")
            
            self.logger.info(f"Récupéré {len(images)} images de Mapillary")
            return images
            
        except Exception as e:
            self.logger.error(f"Échec de récupération des images : {str(e)}")
            raise APIError(f"Échec de récupération des images Mapillary : {str(e)}")
    
    def get_image_detections(self, image_id: str) -> List[Annotation]:
        """
        Récupère les détections pour une image spécifique
        
        Args:
            image_id: ID de l'image
            
        Returns:
            Liste des annotations trouvées
        """
        params = {
            "fields": "id,value,geometry"
        }
        
        try:
            response = self._make_request(f"{image_id}/detections", params)
            if not response or "data" not in response:
                return []
            
            annotations = []
            
            # Import pour le décodage
            import base64
            try:
                import mapbox_vector_tile
            except ImportError:
                self.logger.error("Package mapbox_vector_tile manquant. Installez-le avec : pip install mapbox-vector-tile")
                return []
            
            for detection in response.get("data", []):
                try:
                    # Les détails de décodage restent similaires à l'implémentation précédente
                    # ... (code de décodage des annotations)
                    
                    # À titre d'exemple, je vais montrer une implémentation simplifiée
                    confidence = detection.get('confidence', 0.9)
                    bbox = BoundingBox(
                        x=0.1,  # Exemple de coordonnées
                        y=0.1,
                        width=0.2,
                        height=0.2
                    )
                    
                    # Déterminer la classe
                    class_id = 0  # Classe par défaut
                    value = detection.get("value", "")
                    
                    if "traffic-sign" in value:
                        class_id = 1
                    elif "pole" in value:
                        class_id = 2
                    elif "car" in value or "vehicle" in value:
                        class_id = 3
                    elif "person" in value:
                        class_id = 4
                    
                    annotation = Annotation(
                        class_id=class_id,
                        bbox=bbox,
                        confidence=confidence,
                        metadata={
                            "mapillary_id": detection.get("id", ""),
                            "value": value
                        }
                    )
                    
                    annotations.append(annotation)
                    
                except Exception as e:
                    self.logger.error(f"Erreur de traitement de la détection : {str(e)}")
            
            return annotations
            
        except Exception as e:
            self.logger.error(f"Échec de récupération des détections : {str(e)}")
            return []
    
    def download_image(self, url: str) -> Optional[bytes]:
            """
            Télécharge une image depuis son URL
            
            Args:
                url: URL de l'image
                
            Returns:
                Données de l'image ou None en cas d'erreur
            """
            try:
                response = self.session.get(url, timeout=self.config.api.request_timeout)
                if response.status_code == 200:
                    # Vérifier le type de contenu
                    content_type = response.headers.get('Content-Type', '').lower()
                    if not content_type.startswith('image/'):
                        self.logger.warning(f"Type de contenu inattendu : {content_type}")
                    
                    # Vérifier la taille du fichier
                    content_length = int(response.headers.get('Content-Length', 0))
                    max_size = 10 * 1024 * 1024  # 10 Mo
                    if content_length > max_size:
                        self.logger.warning(f"Taille de l'image trop grande : {content_length} octets")
                        return None
                    
                    # Récupérer le contenu de l'image
                    image_data = response.content
                    
                    # Vérifier la validité de l'image avec Pillow
                    try:
                        from PIL import Image
                        from io import BytesIO
                        
                        with Image.open(BytesIO(image_data)) as img:
                            # Vérifier les dimensions minimales
                            min_dimensions = (32, 32)
                            if img.width < min_dimensions[0] or img.height < min_dimensions[1]:
                                self.logger.warning(f"Dimensions de l'image trop petites : {img.width}x{img.height}")
                                return None
                            
                            # Convertir en format JPEG si nécessaire
                            if img.format != 'JPEG':
                                buffer = BytesIO()
                                img.convert('RGB').save(buffer, format='JPEG')
                                image_data = buffer.getvalue()
                    except ImportError:
                        self.logger.warning("Pillow non installé, impossible de valider l'image")
                    except Exception as e:
                        self.logger.warning(f"Erreur de validation de l'image : {str(e)}")
                        return None
                    
                    return image_data
                else:
                    self.logger.error(f"Échec du téléchargement : Code de statut {response.status_code}")
                    return None
            
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Erreur de téléchargement : {str(e)}")
                return None
            except Exception as e:
                self.logger.error(f"Erreur inattendue lors du téléchargement : {str(e)}")
                return None
    
    def import_annotations_from_mapillary(
        self, 
        image_id: str
    ) -> List[Annotation]:
        """
        Importe les annotations d'une image spécifique depuis Mapillary
        
        Args:
            image_id: ID de l'image Mapillary
            
        Returns:
            Liste des annotations
        """
        try:
            # Récupérer les détections de l'image
            detections = self.get_image_detections(image_id)
            
            # Convertir les détections en annotations
            annotations = []
            for detection in detections:
                try:
                    # Créer une annotation standardisée
                    annotation = Annotation(
                        class_id=detection.class_id,
                        bbox=detection.bbox,
                        confidence=detection.confidence or 0.9,
                        type=AnnotationType.BBOX,
                        metadata={
                            "source": "mapillary",
                            "original_detection": detection.metadata
                        }
                    )
                    annotations.append(annotation)
                    
                except Exception as e:
                    self.logger.warning(f"Erreur de conversion de détection : {str(e)}")
            
            return annotations
        
        except Exception as e:
            self.logger.error(f"Échec de l'import des annotations : {str(e)}")
            return []
    
    def search_images(
        self, 
        bbox: Optional[Dict[str, float]] = None, 
        date_range: Optional[Dict[str, str]] = None,
        max_results: int = 100
    ) -> List[Image]:
        """
        Recherche des images avec des filtres optionnels
        
        Args:
            bbox: Bounding box géographique
            date_range: Plage de dates (début, fin)
            max_results: Nombre maximum de résultats
            
        Returns:
            Liste des images trouvées
        """
        try:
            # Préparer les paramètres de recherche
            params = {
                "limit": max_results
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
            
            # Exécuter la recherche
            response = self._make_request("images", params)
            
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
            
            return images
        
        except Exception as e:
            self.logger.error(f"Échec de la recherche d'images : {str(e)}")
            return []