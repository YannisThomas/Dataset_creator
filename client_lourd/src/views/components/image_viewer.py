# src/views/components/image_viewer.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, 
    QSizePolicy, QFrame, QHBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QBrush, QMouseEvent, QPaintEvent, QWheelEvent
from typing import List, Optional, Dict, Tuple

from src.utils.i18n import get_translation_manager, tr
from src.models import Image, Annotation, BoundingBox
from src.models.enums import AnnotationType
from pathlib import Path
from src.utils.logger import Logger

class ImageViewerWidget(QWidget):
    """
    Widget qui affiche l'image et dessine les annotations directement dessus.
    Gère correctement les transformations de coordonnées pendant le zoom.
    """
    
    # Signaux
    annotation_selected = pyqtSignal(int)
    annotation_created = pyqtSignal(QRect)
    annotation_modified = pyqtSignal(int, QRect)
    
    # États d'édition
    MODE_VIEW = 0
    MODE_CREATE = 1 
    MODE_EDIT = 2
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialiser le logger

        self.logger = Logger()


        # État
        self.original_pixmap = None  # Pixmap original non zoomé
        self.pixmap = None  # Pixmap affiché (potentiellement zoomé)
        self.annotations = []
        self.selected_index = -1
        self.edit_mode = self.MODE_VIEW
        self.scale_factor = 1.0  # Facteur de zoom actuel
        
        # État d'édition
        self.current_rect = None
        self.start_point = None
        self.resize_handles = {}
        self.dragging = False
        self.resizing = False
        self.resize_handle = None
        self.drag_start_pos = None
        self.drag_start_rect = None
        
        # Apparence
        self.setMinimumSize(200, 200)
        
        # Suivi de la souris
        self.setMouseTracking(True)
        
    def set_pixmap(self, original_pixmap, scaled_pixmap=None, scale_factor=1.0):
        """
        Définit l'image à afficher
        
        Args:
            original_pixmap: Pixmap original non zoomé
            scaled_pixmap: Pixmap mis à l'échelle (optionnel)
            scale_factor: Facteur d'échelle actuel
        """
        if original_pixmap and not original_pixmap.isNull():
            self.original_pixmap = original_pixmap
            self.scale_factor = scale_factor
            
            if scaled_pixmap and not scaled_pixmap.isNull():
                self.pixmap = scaled_pixmap
            else:
                self.pixmap = original_pixmap
                
            self.setMinimumSize(self.pixmap.size())
            self.resize(self.pixmap.size())
            self.update()
            
    def set_annotations(self, annotations):
        """Définit les annotations à afficher"""
        self.annotations = annotations
        self.selected_index = -1
        self.update()
        
    def set_selected(self, index):
        """Définit l'annotation sélectionnée"""
        if 0 <= index < len(self.annotations):
            self.selected_index = index
        else:
            self.selected_index = -1
        self.update()
    
    def set_edit_mode(self, mode):
        """Définit le mode d'édition"""
        self.edit_mode = mode
        
        # Mettre à jour le curseur
        if mode == self.MODE_CREATE:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif mode == self.MODE_EDIT:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
        self.update()
        
    def paintEvent(self, event):
        """Dessine l'image et les annotations"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dessiner l'image
        if self.pixmap and not self.pixmap.isNull():
            painter.drawPixmap(0, 0, self.pixmap)
            
            # Dimensions de l'image originale et affichée
            displayed_width = self.pixmap.width()
            displayed_height = self.pixmap.height()
            original_width = self.original_pixmap.width()
            original_height = self.original_pixmap.height()
            
            # Dessiner les annotations
            for i, annotation in enumerate(self.annotations):
                # Convertir les coordonnées normalisées en pixels affichés
                x = int(annotation.bbox.x * displayed_width)
                y = int(annotation.bbox.y * displayed_height)
                width = int(annotation.bbox.width * displayed_width)
                height = int(annotation.bbox.height * displayed_height)
                
                rect = QRect(x, y, width, height)
                
                # Couleur selon la sélection
                if i == self.selected_index:
                    # Rouge pour la sélection
                    pen_color = QColor(255, 0, 0)
                    fill_color = QColor(255, 0, 0, 80)  # Rouge avec alpha
                else:
                    # Vert par défaut
                    pen_color = QColor(0, 255, 0) 
                    fill_color = QColor(0, 255, 0, 60)  # Vert avec alpha
                
                # Dessiner le rectangle rempli
                painter.setPen(QPen(pen_color, 2))
                painter.setBrush(QBrush(fill_color))
                painter.drawRect(rect)
                
                # Afficher la classe
                if hasattr(annotation, 'class_id'):
                    class_text = f"{tr('component.image_viewer.class_label')} {annotation.class_id}"
                    
                    # Ajouter la confiance si disponible
                    if hasattr(annotation, 'confidence') and annotation.confidence is not None:
                        class_text += f" ({annotation.confidence:.2f})"
                    
                    # Créer un fond pour le texte
                    text_rect = painter.fontMetrics().boundingRect(class_text)
                    text_rect.moveTopLeft(rect.topLeft() + QPoint(5, 5))
                    text_rect.adjust(-2, -2, 2, 2)
                    
                    painter.fillRect(text_rect, QColor(0, 0, 0, 180))
                    painter.setPen(QColor(255, 255, 255))
                    painter.drawText(rect.topLeft() + QPoint(5, 15), class_text)
            
            # Dessiner le rectangle en cours de création
            if self.edit_mode == self.MODE_CREATE and self.current_rect:
                painter.setPen(QPen(QColor(0, 0, 255), 2))
                painter.setBrush(QBrush(QColor(0, 0, 255, 60)))
                painter.drawRect(self.current_rect)
                
            # Dessiner les poignées si nécessaire
            if self.edit_mode == self.MODE_EDIT and self.selected_index >= 0:
                annotation = self.annotations[self.selected_index]
                x = int(annotation.bbox.x * displayed_width)
                y = int(annotation.bbox.y * displayed_height)
                width = int(annotation.bbox.width * displayed_width)
                height = int(annotation.bbox.height * displayed_height)
                
                rect = QRect(x, y, width, height)
                self._draw_resize_handles(painter, rect)
    
    def _draw_resize_handles(self, painter, rect):
        """Dessine les poignées de redimensionnement"""
        handle_size = 8
        
        painter.setPen(QPen(QColor(255, 0, 0)))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        
        # Stocker les poignées
        self.resize_handles = {
            "top_left": QRect(rect.left() - handle_size//2, rect.top() - handle_size//2, handle_size, handle_size),
            "top_right": QRect(rect.right() - handle_size//2, rect.top() - handle_size//2, handle_size, handle_size),
            "bottom_left": QRect(rect.left() - handle_size//2, rect.bottom() - handle_size//2, handle_size, handle_size),
            "bottom_right": QRect(rect.right() - handle_size//2, rect.bottom() - handle_size//2, handle_size, handle_size),
            "top_center": QRect(rect.center().x() - handle_size//2, rect.top() - handle_size//2, handle_size, handle_size),
            "bottom_center": QRect(rect.center().x() - handle_size//2, rect.bottom() - handle_size//2, handle_size, handle_size),
            "left_center": QRect(rect.left() - handle_size//2, rect.center().y() - handle_size//2, handle_size, handle_size),
            "right_center": QRect(rect.right() - handle_size//2, rect.center().y() - handle_size//2, handle_size, handle_size)
        }
        
        for handle_rect in self.resize_handles.values():
            painter.drawRect(handle_rect)
    
    def mousePressEvent(self, event):
        """Gère les clics de souris"""
        if not self.pixmap or event.button() != Qt.MouseButton.LeftButton:
            return
            
        if self.edit_mode == self.MODE_CREATE:
            # Démarrer un nouveau rectangle
            self.start_point = event.pos()
            self.current_rect = QRect(self.start_point, QSize(0, 0))
            self.update()
            
        elif self.edit_mode == self.MODE_EDIT:
            # Vérifier si on clique sur une poignée
            for handle_name, handle_rect in self.resize_handles.items():
                if handle_rect.contains(event.pos()):
                    self.resizing = True
                    self.resize_handle = handle_name
                    self.drag_start_pos = event.pos()
                    
                    # Récupérer le rectangle de l'annotation
                    annotation = self.annotations[self.selected_index]
                    display_width = self.pixmap.width()
                    display_height = self.pixmap.height()
                    
                    x = int(annotation.bbox.x * display_width)
                    y = int(annotation.bbox.y * display_height)
                    width = int(annotation.bbox.width * display_width)
                    height = int(annotation.bbox.height * display_height)
                    
                    self.drag_start_rect = QRect(x, y, width, height)
                    return
            
            # Vérifier si on clique sur une annotation pour la sélectionner ou la déplacer
            clicked_index = self._get_annotation_at_position(event.pos())
            
            if clicked_index >= 0:
                # Sélectionner l'annotation
                if clicked_index != self.selected_index:
                    self.selected_index = clicked_index
                    self.annotation_selected.emit(clicked_index)
                    self.update()
                
                # Préparer pour le déplacement
                self.dragging = True
                self.drag_start_pos = event.pos()
                
                # Récupérer le rectangle de l'annotation
                annotation = self.annotations[self.selected_index]
                display_width = self.pixmap.width()
                display_height = self.pixmap.height()
                
                x = int(annotation.bbox.x * display_width)
                y = int(annotation.bbox.y * display_height)
                width = int(annotation.bbox.width * display_width)
                height = int(annotation.bbox.height * display_height)
                
                self.drag_start_rect = QRect(x, y, width, height)
            else:
                # Désélectionner
                self.selected_index = -1
                self.annotation_selected.emit(-1)
                self.update()
                
    def mouseMoveEvent(self, event):
        """Gère les mouvements de souris"""
        if not self.pixmap:
            return
            
        if self.edit_mode == self.MODE_CREATE and self.start_point:
            # Mettre à jour le rectangle en cours de création
            self.current_rect = QRect(self.start_point, event.pos()).normalized()
            self.update()
            
        elif self.edit_mode == self.MODE_EDIT:
            if self.resizing and self.selected_index >= 0 and self.drag_start_rect and self.resize_handle:
                # Redimensionner l'annotation
                dx = event.pos().x() - self.drag_start_pos.x()
                dy = event.pos().y() - self.drag_start_pos.y()
                
                new_rect = QRect(self.drag_start_rect)
                
                if self.resize_handle == "top_left":
                    new_rect.setTopLeft(self.drag_start_rect.topLeft() + QPoint(dx, dy))
                elif self.resize_handle == "top_right":
                    new_rect.setTopRight(self.drag_start_rect.topRight() + QPoint(dx, dy))
                elif self.resize_handle == "bottom_left":
                    new_rect.setBottomLeft(self.drag_start_rect.bottomLeft() + QPoint(dx, dy))
                elif self.resize_handle == "bottom_right":
                    new_rect.setBottomRight(self.drag_start_rect.bottomRight() + QPoint(dx, dy))
                elif self.resize_handle == "top_center":
                    new_rect.setTop(self.drag_start_rect.top() + dy)
                elif self.resize_handle == "bottom_center":
                    new_rect.setBottom(self.drag_start_rect.bottom() + dy)
                elif self.resize_handle == "left_center":
                    new_rect.setLeft(self.drag_start_rect.left() + dx)
                elif self.resize_handle == "right_center":
                    new_rect.setRight(self.drag_start_rect.right() + dx)
                
                # Normaliser et limiter aux dimensions de l'image
                new_rect = new_rect.normalized()
                new_rect = new_rect.intersected(QRect(0, 0, self.pixmap.width(), self.pixmap.height()))
                
                # S'assurer que le rectangle a une taille minimale
                if new_rect.width() > 5 and new_rect.height() > 5:
                    # Mettre à jour l'annotation
                    display_width = self.pixmap.width()
                    display_height = self.pixmap.height()
                    
                    # Convertir le rectangle en bbox (dans les coordonnées affichées)
                    bbox = BoundingBox(
                        x=max(0, min(1, new_rect.x() / display_width)),
                        y=max(0, min(1, new_rect.y() / display_height)),
                        width=max(0, min(1, new_rect.width() / display_width)),
                        height=max(0, min(1, new_rect.height() / display_height))
                    )
                    
                    # Mettre à jour l'annotation
                    self.annotations[self.selected_index].bbox = bbox
                    
                    # Émettre le signal de modification
                    self.annotation_modified.emit(self.selected_index, new_rect)
                    
                    # Mettre à jour l'affichage
                    self.update()
                    
            elif self.dragging and self.selected_index >= 0 and self.drag_start_rect:
                # Déplacer l'annotation
                dx = event.pos().x() - self.drag_start_pos.x()
                dy = event.pos().y() - self.drag_start_pos.y()
                
                # Créer un nouveau rectangle déplacé
                new_rect = QRect(
                    self.drag_start_rect.x() + dx,
                    self.drag_start_rect.y() + dy,
                    self.drag_start_rect.width(),
                    self.drag_start_rect.height()
                )
                
                # Limiter au cadre de l'image
                display_rect = QRect(0, 0, self.pixmap.width(), self.pixmap.height())
                if not display_rect.contains(new_rect):
                    # Ajuster pour rester dans l'image
                    if new_rect.left() < 0:
                        new_rect.moveLeft(0)
                    if new_rect.top() < 0:
                        new_rect.moveTop(0)
                    if new_rect.right() > display_rect.right():
                        new_rect.moveRight(display_rect.right())
                    if new_rect.bottom() > display_rect.bottom():
                        new_rect.moveBottom(display_rect.bottom())
                
                # Convertir le rectangle en bbox (dans les coordonnées affichées)
                display_width = self.pixmap.width()
                display_height = self.pixmap.height()
                
                bbox = BoundingBox(
                    x=max(0, min(1, new_rect.x() / display_width)),
                    y=max(0, min(1, new_rect.y() / display_height)),
                    width=max(0, min(1, new_rect.width() / display_width)),
                    height=max(0, min(1, new_rect.height() / display_height))
                )
                
                # Mettre à jour l'annotation
                self.annotations[self.selected_index].bbox = bbox
                
                # Émettre le signal de modification
                self.annotation_modified.emit(self.selected_index, new_rect)
                
                # Mettre à jour l'affichage
                self.update()
            else:
                # Mettre à jour le curseur en fonction de la position
                if self.edit_mode == self.MODE_EDIT:
                    self._update_cursor(event.pos())
                
    def mouseReleaseEvent(self, event):
        """Gère le relâchement du bouton de la souris"""
        if not self.pixmap or event.button() != Qt.MouseButton.LeftButton:
            return
            
        if self.edit_mode == self.MODE_CREATE and self.start_point and self.current_rect:
            # Vérifier que le rectangle a une taille minimale
            if self.current_rect.width() > 5 and self.current_rect.height() > 5:
                # Émettre le signal de création
                # On envoie les coordonnées par rapport à l'image affichée
                self.annotation_created.emit(self.current_rect)
            
            # Réinitialiser
            self.start_point = None
            self.current_rect = None
            self.update()
            
        elif self.edit_mode == self.MODE_EDIT:
            # Fin du déplacement ou du redimensionnement
            self.dragging = False
            self.resizing = False
            self.resize_handle = None
            self.drag_start_pos = None
            self.drag_start_rect = None
    
    def _update_cursor(self, pos):
        """Met à jour le curseur en fonction de la position"""
        if self.edit_mode != self.MODE_EDIT or self.selected_index < 0:
            return
            
        # Vérifier si on est sur une poignée
        for handle_name, handle_rect in self.resize_handles.items():
            if handle_rect.contains(pos):
                if handle_name in ["top_left", "bottom_right"]:
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif handle_name in ["top_right", "bottom_left"]:
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                elif handle_name in ["top_center", "bottom_center"]:
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                elif handle_name in ["left_center", "right_center"]:
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                return
        
        # Vérifier si on est sur l'annotation sélectionnée
        annotation = self.annotations[self.selected_index]
        display_width = self.pixmap.width()
        display_height = self.pixmap.height()
        
        x = int(annotation.bbox.x * display_width)
        y = int(annotation.bbox.y * display_height)
        width = int(annotation.bbox.width * display_width)
        height = int(annotation.bbox.height * display_height)
        
        rect = QRect(x, y, width, height)
        
        if rect.contains(pos):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def _get_annotation_at_position(self, pos):
        """Détermine quelle annotation est sous le curseur"""
        if not self.pixmap or not self.annotations:
            return -1
            
        display_width = self.pixmap.width()
        display_height = self.pixmap.height()
        
        for i, annotation in enumerate(self.annotations):
            x = int(annotation.bbox.x * display_width)
            y = int(annotation.bbox.y * display_height)
            width = int(annotation.bbox.width * display_width)
            height = int(annotation.bbox.height * display_height)
            
            rect = QRect(x, y, width, height)
            if rect.contains(pos):
                return i
                
        return -1

    def convert_to_original_coordinates(self, rect):
        """
        Convertit un rectangle des coordonnées affichées vers les coordonnées originales
        
        Args:
            rect: QRect dans les coordonnées de l'image affichée
            
        Returns:
            QRect dans les coordonnées de l'image originale
        """
        if not self.pixmap or not self.original_pixmap:
            return rect
            
        # Facteur d'échelle entre l'affichage et l'original
        display_width = self.pixmap.width()
        display_height = self.pixmap.height()
        original_width = self.original_pixmap.width()
        original_height = self.original_pixmap.height()
        
        # Conversion des coordonnées
        original_x = int(rect.x() * original_width / display_width)
        original_y = int(rect.y() * original_height / display_height)
        original_width = int(rect.width() * original_width / display_width)
        original_height = int(rect.height() * original_height / display_height)
        
        return QRect(original_x, original_y, original_width, original_height)


class ImageViewer(QWidget):
    """
    Composant pour l'affichage et l'interaction avec les images et leurs annotations.
    Prend en charge l'édition visuelle des bounding boxes et le zoom.
    """
    
    # Signaux
    image_loaded = pyqtSignal(bool)  # Émis quand une image est chargée (succès/échec)
    annotation_selected = pyqtSignal(int)  # Émis quand une annotation est sélectionnée
    annotation_created = pyqtSignal(BoundingBox)  # Émis quand une nouvelle annotation est créée
    annotation_modified = pyqtSignal(int, BoundingBox)  # Émis quand une annotation est modifiée
    
    # États d'édition
    MODE_VIEW = 0  # Mode visualisation
    MODE_CREATE = 1  # Mode création
    MODE_EDIT = 2  # Mode édition
    
    def __init__(self, parent=None):
        """Initialise le visualiseur d'images."""
        super().__init__(parent)

        # Initialiser le logger
        self.logger = Logger()

        # État
        self.image = None  # Image actuelle
        self.original_pixmap = None  # Pixmap original non zoomé
        self.annotations = []  # Annotations à afficher
        self.selected_annotation_index = -1  # Index de l'annotation sélectionnée
        self.scale_factor = 1.0  # Facteur de zoom
        
        # État d'édition
        self.edit_mode = self.MODE_VIEW
        
        # Configuration de l'interface
        self._init_ui()
        
    def _init_ui(self):
        """Initialise l'interface utilisateur."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Zone de défilement pour l'image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Widget d'affichage de l'image et des annotations
        self.viewer_widget = ImageViewerWidget()
        self.viewer_widget.annotation_selected.connect(self._on_annotation_selected)
        self.viewer_widget.annotation_created.connect(self._on_annotation_created)
        self.viewer_widget.annotation_modified.connect(self._on_annotation_modified)
        
        self.scroll_area.setWidget(self.viewer_widget)
        
        # Ajouter la zone de défilement au layout principal
        layout.addWidget(self.scroll_area)
        
        # Barre d'outils de zoom
        zoom_toolbar = QHBoxLayout()
        
        # Bouton Zoom +
        self.zoom_in_btn = QPushButton(tr("component.image_viewer.zoom_in"))
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        
        # Bouton Zoom -
        self.zoom_out_btn = QPushButton(tr("component.image_viewer.zoom_out"))
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        
        # Bouton Reset Zoom
        self.reset_zoom_btn = QPushButton(tr("component.image_viewer.reset_zoom"))
        self.reset_zoom_btn.clicked.connect(self.reset_zoom)
        
        zoom_toolbar.addWidget(self.zoom_in_btn)
        zoom_toolbar.addWidget(self.zoom_out_btn)
        zoom_toolbar.addWidget(self.reset_zoom_btn)
        zoom_toolbar.addStretch()
        
        layout.addLayout(zoom_toolbar)
        
        # Label d'information
        self.info_label = QLabel(tr("component.image_viewer.ready"))
        layout.addWidget(self.info_label)
    
    def _on_annotation_selected(self, index):
        """Gère la sélection d'une annotation"""
        self.selected_annotation_index = index
        self.annotation_selected.emit(index)
        
    def _on_annotation_created(self, rect):
        """Gère la création d'une annotation"""
        if not self.original_pixmap:
            return
            
        # Convertir le rectangle des coordonnées affichées aux coordonnées originales
        original_rect = self.viewer_widget.convert_to_original_coordinates(rect)
            
        # Convertir en coordonnées normalisées
        original_width = self.original_pixmap.width()
        original_height = self.original_pixmap.height()
        
        bbox = BoundingBox(
            x=max(0, min(1, original_rect.x() / original_width)),
            y=max(0, min(1, original_rect.y() / original_height)),
            width=max(0, min(1, original_rect.width() / original_width)),
            height=max(0, min(1, original_rect.height() / original_height))
        )
        
        # Émettre le signal
        self.annotation_created.emit(bbox)
        
    def _on_annotation_modified(self, index, rect):
        """Gère la modification d'une annotation"""
        if not self.original_pixmap or index < 0 or index >= len(self.annotations):
            return
            
        # Convertir le rectangle des coordonnées affichées aux coordonnées originales
        original_rect = self.viewer_widget.convert_to_original_coordinates(rect)
            
        # Convertir en coordonnées normalisées
        original_width = self.original_pixmap.width()
        original_height = self.original_pixmap.height()
        
        bbox = BoundingBox(
            x=max(0, min(1, original_rect.x() / original_width)),
            y=max(0, min(1, original_rect.y() / original_height)),
            width=max(0, min(1, original_rect.width() / original_width)),
            height=max(0, min(1, original_rect.height() / original_height))
        )
        
        # Émettre le signal
        self.annotation_modified.emit(index, bbox)
    
    def wheelEvent(self, event: QWheelEvent):
        """Gère le zoom avec la molette de la souris"""
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        
        event.accept()
    
    def zoom_in(self):
        """Zoom avant"""
        self.scale_image(1.25)
    
    def zoom_out(self):
        """Zoom arrière"""
        self.scale_image(0.8)
    
    def reset_zoom(self):
        """Réinitialise le zoom"""
        if self.original_pixmap:
            reset_factor = 1.0 / self.scale_factor
            self.scale_image(reset_factor)
    
    def scale_image(self, factor):
        """Met à l'échelle l'image"""
        if not self.original_pixmap:
            return
        
        # Mettre à jour le facteur d'échelle
        self.scale_factor *= factor
        self.scale_factor = max(0.1, min(10.0, self.scale_factor))
        
        # Créer une version mise à l'échelle du pixmap
        scaled_pixmap = self.original_pixmap.scaled(
            self.original_pixmap.size() * self.scale_factor,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Mettre à jour l'image
        self.viewer_widget.set_pixmap(self.original_pixmap, scaled_pixmap, self.scale_factor)
        
        # Mettre à jour l'info
        self.info_label.setText(f"Zoom: {self.scale_factor * 100:.0f}%")
    
    def load_image(self, image: Image) -> bool:
        """Charge une image dans le visualiseur"""
        self.image = image
        
        try:
            # S'assurer que le chemin est une chaîne pour QPixmap
            path_str = str(image.path) if image.path is not None else ""
            
            self.logger.debug(f"Chargement de l'image: {path_str}, type: {type(image.path)}")
            
            # Correction pour les chemins problématiques
            if path_str.startswith(('http://', 'https://')):
                # Extraire la partie locale du chemin (après http:// ou https://)
                local_part = path_str.split('://')[-1]
                
                # Vérifier si le chemin local existe
                if Path(local_part).exists():
                    path_str = local_part
                    self.logger.debug(f"Chemin corrigé pour l'image URL: {path_str}")
                else:
                    # Essayer d'autres variations de chemins
                    filename = Path(local_part).name
                    potential_paths = [
                        Path("data/datasets") / Path(local_part),
                        Path(local_part.replace('\\', '/')),
                        Path("data/downloads") / filename,
                        Path("downloads") / filename
                    ]
                    
                    for potential_path in potential_paths:
                        if potential_path.exists():
                            path_str = str(potential_path)
                            self.logger.debug(f"Chemin alternatif trouvé: {path_str}")
                            break
                    else:
                        self.logger.error(f"Fichier image introuvable: {path_str}")
                        self.image_loaded.emit(False)
                        return False
            
            # Vérifier si le fichier existe
            if not Path(path_str).exists():
                self.logger.error(f"Fichier image introuvable: {path_str}")
                self.image_loaded.emit(False)
                return False
            
            # Charger le pixmap avec la chaîne
            self.original_pixmap = QPixmap(path_str)
            
            if self.original_pixmap.isNull():
                self.logger.error(f"Échec du chargement de l'image (pixmap null): {path_str}")
                self.image_loaded.emit(False)
                return False
                
            # Afficher l'image
            self.viewer_widget.set_pixmap(self.original_pixmap)
            
            # Réinitialiser le zoom
            self.scale_factor = 1.0
            
            # Charger les annotations
            self.annotations = image.annotations
            self.viewer_widget.set_annotations(self.annotations)
            
            # Réinitialiser l'état d'édition
            self.edit_mode = self.MODE_VIEW
            self.viewer_widget.set_edit_mode(self.MODE_VIEW)
            
            self.image_loaded.emit(True)
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de l'image: {str(e)}")
            self.image_loaded.emit(False)
            return False
    
    def set_annotations(self, annotations: List[Annotation]):
        """Définit les annotations à afficher"""
        self.annotations = annotations
        self.selected_annotation_index = -1
        self.viewer_widget.set_annotations(annotations)
        
    def select_annotation(self, index: int):
        """Sélectionne une annotation par son index"""
        if 0 <= index < len(self.annotations):
            self.selected_annotation_index = index
            self.viewer_widget.set_selected(index)
            
    def clear_image(self):
        """Efface l'image et les annotations"""
        self.image = None
        self.original_pixmap = None
        self.annotations = []
        self.selected_annotation_index = -1
        self.viewer_widget.set_pixmap(None)
        self.viewer_widget.set_annotations([])
        
    def set_edit_mode(self, mode: int):
        """Définit le mode d'édition"""
        self.edit_mode = mode
        self.viewer_widget.set_edit_mode(mode)
        
        # Mettre à jour l'info selon le mode
        if mode == self.MODE_CREATE:
            self.info_label.setText(tr("component.image_viewer.create_mode"))
        elif mode == self.MODE_EDIT:
            self.info_label.setText(tr("component.image_viewer.edit_mode"))
        else:
            self.info_label.setText(tr("component.image_viewer.view_mode"))
        
    def create_annotation_mode(self):
        """Active le mode création d'annotation."""
        self.set_edit_mode(self.MODE_CREATE)
        
    def edit_annotation_mode(self):
        """Active le mode édition d'annotation."""
        self.set_edit_mode(self.MODE_EDIT)
        
    def view_mode(self):
        """Active le mode visualisation."""
        self.set_edit_mode(self.MODE_VIEW)