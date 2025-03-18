# src/utils/async_worker.py

import threading
import queue
import time
from typing import Callable, List, Dict, Any, Optional, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, Future
import traceback

from src.utils.logger import Logger

class WorkItem:
    """Représente une tâche à exécuter de manière asynchrone."""
    
    def __init__(
        self, 
        task_id: str, 
        func: Callable, 
        args: List = None, 
        kwargs: Dict = None,
        priority: int = 1,
        callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None
    ):
        """
        Initialise un élément de travail.
        
        Args:
            task_id: Identifiant unique de la tâche
            func: Fonction à exécuter
            args: Arguments positionnels
            kwargs: Arguments nommés
            priority: Priorité de la tâche (plus petit = plus prioritaire)
            callback: Fonction à appeler avec le résultat
            error_callback: Fonction à appeler en cas d'erreur
        """
        self.task_id = task_id
        self.func = func
        self.args = args or []
        self.kwargs = kwargs or {}
        self.priority = priority
        self.callback = callback
        self.error_callback = error_callback
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.is_cancelled = False
        self.result = None
        self.error = None
        
    def execute(self) -> Any:
        """
        Exécute la tâche et gère son résultat.
        
        Returns:
            Résultat de la fonction
        """
        if self.is_cancelled:
            return None
            
        self.started_at = time.time()
        
        try:
            self.result = self.func(*self.args, **self.kwargs)
            self.completed_at = time.time()
            
            # Appeler le callback si défini
            if self.callback:
                self.callback(self.result)
                
            return self.result
            
        except Exception as e:
            self.completed_at = time.time()
            self.error = e
            
            # Appeler le callback d'erreur si défini
            if self.error_callback:
                self.error_callback(e)
            
            return None

    def __lt__(self, other):
        """Comparaison pour la file de priorité."""
        if not isinstance(other, WorkItem):
            return NotImplemented
        return self.priority < other.priority or (
            self.priority == other.priority and self.created_at < other.created_at
        )


class AsyncTaskManager:
    """
    Gestionnaire de tâches asynchrones avec support de priorités et pool de threads.
    """
    
    def __init__(
        self, 
        max_workers: int = 4, 
        queue_size: int = 100,
        logger: Optional[Logger] = None
    ):
        """
        Initialise le gestionnaire de tâches.
        
        Args:
            max_workers: Nombre maximum de threads dans le pool
            queue_size: Taille maximale de la file d'attente
            logger: Gestionnaire de logs
        """
        self.logger = logger or Logger()
        self.max_workers = max_workers
        
        # File d'attente à priorité
        self.task_queue = queue.PriorityQueue(maxsize=queue_size)
        
        # Pool de threads
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Drapeaux de contrôle
        self.running = False
        self.paused = False
        
        # Suivi des tâches
        self.tasks = {}
        self.futures = {}
        
        # Thread pour gérer la file
        self.queue_thread = None
        
        # Verrou pour accès concurrent
        self.lock = threading.RLock()
        
        self.logger.info(f"AsyncTaskManager initialisé avec {max_workers} workers")
    
    def start(self):
        """Démarre le thread de gestion de la file d'attente."""
        with self.lock:
            if self.running:
                return
                
            self.running = True
            self.paused = False
            self.queue_thread = threading.Thread(
                target=self._process_queue, 
                daemon=True,
                name="AsyncTaskManagerThread"
            )
            self.queue_thread.start()
            
            self.logger.info("AsyncTaskManager démarré")
    
    def stop(self, wait: bool = True):
        """
        Arrête le gestionnaire de tâches.
        
        Args:
            wait: Attendre la fin des tâches en cours
        """
        with self.lock:
            if not self.running:
                return
                
            self.running = False
            
            if wait:
                # Attendre la fin des tâches en cours
                if not self.task_queue.empty():
                    self.logger.info("En attente de la fin des tâches...")
                    
                # Vider la file mais traiter les tâches en cours
                while not self.task_queue.empty():
                    try:
                        self.task_queue.get_nowait()
                        self.task_queue.task_done()
                    except queue.Empty:
                        break
            else:
                # Annuler toutes les tâches
                with self.lock:
                    for task_id, task in list(self.tasks.items()):
                        task.is_cancelled = True
                        
                    for future in self.futures.values():
                        future.cancel()
            
            self.executor.shutdown(wait=wait)
            self.logger.info("AsyncTaskManager arrêté")
    
    def pause(self):
        """Met en pause le traitement des tâches."""
        with self.lock:
            self.paused = True
            self.logger.info("AsyncTaskManager mis en pause")
    
    def resume(self):
        """Reprend le traitement des tâches."""
        with self.lock:
            self.paused = False
            self.logger.info("AsyncTaskManager repris")
    
    def _process_queue(self):
        """Traite les tâches en attente dans la file."""
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue
                
            try:
                # Récupérer une tâche
                _, work_item = self.task_queue.get(timeout=0.5)
                
                if work_item.is_cancelled:
                    self.task_queue.task_done()
                    continue
                
                # Soumettre la tâche au pool
                future = self.executor.submit(work_item.execute)
                
                with self.lock:
                    self.futures[work_item.task_id] = future
                
                # Callback quand la tâche est terminée
                future.add_done_callback(
                    lambda f, task_id=work_item.task_id: self._task_completed(task_id, f)
                )
                
                self.task_queue.task_done()
                
            except queue.Empty:
                # Pas de tâche disponible
                pass
            except Exception as e:
                self.logger.error(f"Erreur dans le thread de la file d'attente: {str(e)}")
                self.logger.error(traceback.format_exc())
    
    def _task_completed(self, task_id: str, future: Future):
        """
        Appelé lorsqu'une tâche est terminée.
        
        Args:
            task_id: ID de la tâche
            future: Future associé à la tâche
        """
        with self.lock:
            # Supprimer le future
            if task_id in self.futures:
                del self.futures[task_id]
            
            # Supprimer la tâche
            if task_id in self.tasks:
                task = self.tasks[task_id]
                
                # Log des performances
                if task.completed_at and task.started_at:
                    execution_time = task.completed_at - task.started_at
                    self.logger.debug(f"Tâche {task_id} terminée en {execution_time:.3f}s")
                
                del self.tasks[task_id]
    
    def submit_task(
        self, 
        task_id: str, 
        func: Callable, 
        args: List = None, 
        kwargs: Dict = None,
        priority: int = 1,
        callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None
    ) -> str:
        """
        Soumet une tâche à exécuter de manière asynchrone.
        
        Args:
            task_id: Identifiant unique de la tâche
            func: Fonction à exécuter
            args: Arguments positionnels
            kwargs: Arguments nommés
            priority: Priorité de la tâche (plus petit = plus prioritaire)
            callback: Fonction à appeler avec le résultat
            error_callback: Fonction à appeler en cas d'erreur
            
        Returns:
            ID de la tâche
        """
        work_item = WorkItem(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            callback=callback,
            error_callback=error_callback
        )
        
        with self.lock:
            # Démarrer le gestionnaire si nécessaire
            if not self.running:
                self.start()
            
            # Stocker la tâche
            self.tasks[task_id] = work_item
            
            # Ajouter à la file d'attente
            try:
                self.task_queue.put((priority, work_item), block=False)
                self.logger.debug(f"Tâche {task_id} soumise avec priorité {priority}")
            except queue.Full:
                self.logger.warning(f"File d'attente pleine, tâche {task_id} rejetée")
                del self.tasks[task_id]
                raise RuntimeError("File d'attente pleine")
        
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Annule une tâche si elle n'a pas encore commencé.
        
        Args:
            task_id: ID de la tâche à annuler
            
        Returns:
            True si la tâche a été annulée
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.is_cancelled = True
                
                # Si la tâche est déjà en cours d'exécution, annuler le future
                if task_id in self.futures:
                    future = self.futures[task_id]
                    return future.cancel()
                
                self.logger.debug(f"Tâche {task_id} annulée")
                return True
        
        return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le statut d'une tâche.
        
        Args:
            task_id: ID de la tâche
            
        Returns:
            Dictionnaire avec le statut de la tâche ou None
        """
        with self.lock:
            if task_id not in self.tasks:
                return None
                
            task = self.tasks[task_id]
            future = self.futures.get(task_id)
            
            status = {
                "task_id": task.task_id,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "cancelled": task.is_cancelled,
                "running": future is not None and not future.done() if future else False,
                "done": future is not None and future.done() if future else False,
                "error": str(task.error) if task.error else None,
                "has_result": task.result is not None
            }
            
            return status
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du gestionnaire.
        
        Returns:
            Statistiques d'utilisation
        """
        with self.lock:
            running_count = sum(1 for f in self.futures.values() if not f.done())
            completed_count = sum(1 for task in self.tasks.values() if task.completed_at is not None)
            
            return {
                "queue_size": self.task_queue.qsize(),
                "queue_full": self.task_queue.full(),
                "tasks_total": len(self.tasks),
                "tasks_running": running_count,
                "tasks_completed": completed_count,
                "max_workers": self.max_workers,
                "is_running": self.running,
                "is_paused": self.paused
            }
    
    def wait_all(self, timeout: Optional[float] = None) -> bool:
        """
        Attend que toutes les tâches soient terminées.
        
        Args:
            timeout: Délai d'attente maximum en secondes
            
        Returns:
            True si toutes les tâches sont terminées
        """
        if timeout is not None:
            end_time = time.time() + timeout
        
        # Attendre que la file soit vide
        try:
            while not self.task_queue.empty():
                if timeout is not None and time.time() > end_time:
                    return False
                time.sleep(0.1)
        except:
            return False
        
        # Attendre que tous les futures soient terminés
        with self.lock:
            futures = list(self.futures.values())
        
        for future in futures:
            remaining = None
            if timeout is not None:
                remaining = max(0, end_time - time.time())
                if remaining <= 0:
                    return False
                    
            try:
                future.result(timeout=remaining)
            except:
                return False
        
        return True