# src/core/exceptions.py

class YoloDatasetError(Exception):
    """Classe de base pour toutes les exceptions du projet."""
    pass

class DatabaseError(YoloDatasetError):
    """Erreur liée à la base de données."""
    def __init__(self, message: str, error_code: int = None):
        self.error_code = error_code
        super().__init__(message)

class ValidationError(YoloDatasetError):
    """Erreur de validation des données."""
    def __init__(self, message: str, field: str = None, value: str = None):
        self.field = field
        self.value = value
        super().__init__(message)

class DatasetError(YoloDatasetError):
    """Erreur liée au dataset."""
    def __init__(self, message: str, dataset_name: str = None):
        self.dataset_name = dataset_name
        super().__init__(message)

class ImageError(YoloDatasetError):
    """Erreur liée aux images."""
    def __init__(self, message: str, image_path: str = None):
        self.image_path = image_path
        super().__init__(message)

class AnnotationError(YoloDatasetError):
    """Erreur liée aux annotations."""
    def __init__(self, message: str, image_id: str = None, annotation_id: str = None):
        self.image_id = image_id
        self.annotation_id = annotation_id
        super().__init__(message)

class ConfigurationError(YoloDatasetError):
    """Erreur de configuration."""
    def __init__(self, message: str, config_key: str = None):
        self.config_key = config_key
        super().__init__(message)

class APIError(YoloDatasetError):
    """Erreur lors de l'appel à l'API."""
    def __init__(self, message: str, status_code: int = None, response: str = None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)
        
class AuthenticationError(APIError):
    """Erreur d'authentification."""
    def __init__(self, message: str, token: str = None):
        self.token = token
        super().__init__(message)

class RateLimitError(APIError):
    """Erreur de limite de taux d'appel à l'API."""
    def __init__(self, message: str, reset_time: str = None):
        self.reset_time = reset_time
        super().__init__(message)

class ExportError(YoloDatasetError):
    """Erreur lors de l'export du dataset."""
    def __init__(self, message: str, format: str = None, path: str = None):
        self.format = format
        self.path = path
        super().__init__(message)

class ImportError(YoloDatasetError):
    """Erreur lors de l'import de données."""
    def __init__(self, message: str, source: str = None, path: str = None):
        self.source = source
        self.path = path
        super().__init__(message)

class StorageError(YoloDatasetError):
    """Erreur de stockage."""
    def __init__(self, message: str, path: str = None):
        self.path = path
        super().__init__(message)

def handle_database_error(error) -> DatabaseError:
    """
    Convertit une erreur SQLAlchemy en DatabaseError personnalisée.
    
    Args:
        error: Erreur SQLAlchemy d'origine
        
    Returns:
        DatabaseError avec message approprié
    """
    error_code = getattr(error, 'code', None)
    return DatabaseError(str(error), error_code=error_code)

def handle_api_error(response) -> APIError:
    """
    Crée une APIError appropriée à partir d'une réponse d'API.
    
    Args:
        response: Réponse de l'API
        
    Returns:
        APIError avec message approprié
    """
    return APIError(
        message=f"Échec de la requête API: {response.text}",
        status_code=response.status_code,
        response=response.text
    )