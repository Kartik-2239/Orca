from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import (
    QByteArray,
    QBuffer,
    QIODevice,
    QEvent,
    QRect,
    QRectF,
    QTimer,
    Qt,
    QSize,
)
from PySide6.QtGui import (
    QColor,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPixmap,
    QShortcut,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from services.state import AppState


def svg_icon(svg: str, size: int) -> QIcon:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    renderer.render(painter)
    painter.end()
    return QIcon(QPixmap.fromImage(image))


def pixmap_to_bytes(pixmap: QPixmap) -> bytes:
    image = pixmap.toImage()
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def bytes_to_pixmap(data: bytes) -> QPixmap:
    image = QImage.fromData(data, "PNG")
    return QPixmap.fromImage(image)


@dataclass
class EditorImageLayer:
    image_bytes: bytes
    pos: tuple[float, float]
    scale: float
    rotation: float
    opacity: float
    z: float
    is_base: bool = False


@dataclass
class EditorState:
    base_size: tuple[int, int] | None
    image_layers: list[EditorImageLayer]


class CanvasView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene, parent: QWidget | None = None) -> None:
        super().__init__(scene, parent)
        self.setObjectName("CanvasView")
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.grabGesture(Qt.PinchGesture)
        self._zoom = 1.0
        self._min_zoom = 0.2
        self._max_zoom = 5.0
        self._pinch_start = 1.0

    def reset_zoom(self) -> None:
        self._zoom = 1.0
        self.resetTransform()

    def event(self, event) -> bool:
        if event.type() == QEvent.Gesture:
            gesture = event.gesture(Qt.PinchGesture)
            if gesture is not None:
                self._handle_pinch(gesture)
                return True
        return super().event(event)

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return
        factor = 1.0015 ** delta
        self._apply_zoom(factor)
        event.accept()

    def _handle_pinch(self, gesture) -> None:
        if gesture.state() == Qt.GestureStarted:
            self._pinch_start = self._zoom
        scale = gesture.scaleFactor()
        target = self._pinch_start * scale
        target = max(self._min_zoom, min(self._max_zoom, target))
        if self._zoom == 0:
            return
        factor = target / self._zoom
        self._apply_zoom(factor)

    def _apply_zoom(self, factor: float) -> None:
        if factor == 0:
            return
        target = self._zoom * factor
        target = max(self._min_zoom, min(self._max_zoom, target))
        factor = target / self._zoom
        self._zoom = target
        self.scale(factor, factor)

class ImageItem(QGraphicsPixmapItem):
    def __init__(self, pixmap: QPixmap, is_base: bool = False) -> None:
        super().__init__(pixmap)
        self.is_base = is_base
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)


class ImageEditorPage(QWidget):
    def __init__(self, state: AppState, on_theme_change, on_navigate) -> None:
        super().__init__()
        self.state = state
        self.on_theme_change = on_theme_change
        self.on_navigate = on_navigate

        self._base_item: ImageItem | None = None
        self._current_path: Path | None = None
        self._undo_stack: list[EditorState] = []
        self._redo_stack: list[EditorState] = []
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._apply_resize)
        self._resize_base_size: tuple[int, int] | None = None
        self._export_bg_item: QGraphicsRectItem | None = None
        self._export_mask_item: QGraphicsPathItem | None = None
        self._export_base_size: tuple[int, int] | None = None
        self._export_base_rect: QRectF | None = None
        self._export_update_timer = QTimer(self)
        self._export_update_timer.setSingleShot(True)
        self._export_update_timer.timeout.connect(self._update_export_overlay)
        self._layer_up_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
            '<path d="M7 14l5-5 5 5H7Z"/></svg>',
            12,
        )
        self._layer_down_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
            '<path d="M7 10h10l-5 5-5-5Z"/></svg>',
            12,
        )
        self._eye_open_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
            '<path d="M12 5C6.5 5 2 12 2 12s4.5 7 10 7 10-7 10-7-4.5-7-10-7Zm0 11a4 4 0 1 1 0-8 4 4 0 0 1 0 8Z"/>'
            "</svg>",
            12,
        )
        self._eye_closed_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
            '<path d="M3 4.3 4.3 3l16.7 16.7-1.3 1.3-2.4-2.4A10.8 10.8 0 0 1 12 19C6.5 19 2 12 2 12a20 20 0 0 1 4.1-4.9L3 4.3Zm9 3.7a4 4 0 0 1 4 4c0 .6-.1 1.1-.3 1.6l-5.3-5.3c.5-.2 1-.3 1.6-.3Zm-4 4c0-.6.1-1.1.3-1.6l5.3 5.3c-.5.2-1 .3-1.6.3a4 4 0 0 1-4-4Z"/></svg>',
            12,
        )
        self._lock_layer_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
            '<path d="M7 10V7a5 5 0 0 1 10 0v3h-2V7a3 3 0 0 0-6 0v3H7Z"/>'
            '<rect x="5" y="10" width="14" height="10" rx="2"/></svg>',
            12,
        )
        self._lock_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
            '<path d="M7 10V7a5 5 0 0 1 10 0v3h-2V7a3 3 0 0 0-6 0v3H7Z"/>'
            '<rect x="5" y="10" width="14" height="10" rx="2"/></svg>',
            14,
        )
        self._unlock_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
            '<path d="M17 10V7a5 5 0 0 0-9.8-1H9a3 3 0 0 1 6 1v3h-2Z"/>'
            '<rect x="5" y="10" width="14" height="10" rx="2"/></svg>',
            14,
        )

        self._setup_ui()
        self.apply_state(state)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QWidget(self)
        card.setObjectName("MainCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        nav_bar = QHBoxLayout()
        icon_badge = QLabel("IE")
        icon_badge.setAlignment(Qt.AlignCenter)
        icon_badge.setObjectName("IconBadge")
        header_title = QLabel("Orca")
        header_title.setObjectName("HeaderTitle")
        home_btn = QPushButton("Home")
        home_btn.setObjectName("NavButton")
        home_btn.clicked.connect(lambda: self.on_navigate("home"))
        nav_bar.addWidget(icon_badge)
        nav_bar.addWidget(header_title)
        nav_bar.addWidget(home_btn)
        nav_bar.addStretch(1)

        self.theme_toggle = QToolButton()
        self.theme_toggle.setObjectName("ThemeToggle")
        self.theme_toggle.setCheckable(True)
        self._sun_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
            '<circle cx="12" cy="12" r="5"/>'
            "</svg>",
            12,
        )
        self._moon_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f7c6de">'
            '<path d="M21 14.5A8.5 8.5 0 1 1 9.5 3a7 7 0 1 0 11.5 11.5Z"/></svg>',
            12,
        )
        self.theme_toggle.setIcon(self._sun_icon)
        self.theme_toggle.setIconSize(QSize(12, 12))
        self.theme_toggle.toggled.connect(self._on_theme_toggled)
        nav_bar.addWidget(self.theme_toggle)

        top_divider = QFrame()
        top_divider.setObjectName("Divider")
        top_divider.setFixedHeight(1)
        top_divider.setFrameShape(QFrame.HLine)

        content_row = QHBoxLayout()
        content_row.setSpacing(20)

        canvas_frame = QFrame()
        canvas_frame.setObjectName("EditorCanvas")
        canvas_layout = QVBoxLayout(canvas_frame)
        canvas_layout.setContentsMargins(12, 12, 12, 12)

        self.scene = QGraphicsScene(self)
        self.scene.selectionChanged.connect(self._on_selection_changed)
        self.scene.changed.connect(self._schedule_export_overlay_update)
        self.canvas_view = CanvasView(self.scene)
        canvas_layout.addWidget(self.canvas_view, 1)

        right_panel = QFrame()
        right_panel.setObjectName("EditorPanel")
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(0, 0, 0, 0)

        right_scroll = QScrollArea()
        right_scroll.setObjectName("EditorScroll")
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setStyleSheet(
            "QScrollArea { background: transparent; } "
            "QScrollArea > QWidget { background: transparent; }"
        )

        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_scroll.setWidget(right_content)
        right_panel_layout.addWidget(right_scroll)

        self.open_btn = QPushButton("Open Image")
        self.open_btn.setObjectName("ControlButton")
        self.open_btn.clicked.connect(self._open_image)
        right_layout.addWidget(self.open_btn)

        self._build_resize_options()
        self._build_overlay_options()

        controls_card = QFrame()
        controls_card.setObjectName("EditorOptions")
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(12, 12, 12, 12)
        controls_layout.setSpacing(12)

        export_label = QLabel("EXPORT")
        export_label.setObjectName("SectionLabel")

        controls_layout.addWidget(self.overlay_options)

        format_row = QHBoxLayout()
        format_row.setSpacing(8)
        format_label = QLabel("Format")
        format_label.setObjectName("FieldLabel")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPG"])
        self.format_combo.currentTextChanged.connect(self._sync_quality_visibility)
        format_row.addWidget(format_label)
        format_row.addStretch(1)
        format_row.addWidget(self.format_combo)

        quality_row = QHBoxLayout()
        quality_row.setSpacing(8)
        self.quality_label = QLabel("Quality")
        self.quality_label.setObjectName("FieldLabel")
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setObjectName("QualitySlider")
        self.quality_slider.setRange(70, 100)
        self.quality_slider.setValue(95)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)

        quality_row.addWidget(self.quality_label)
        quality_row.addWidget(self.quality_slider, 1)

        controls_layout.addWidget(export_label)
        controls_layout.addLayout(format_row)
        controls_layout.addLayout(quality_row)

        export_button_row = QHBoxLayout()
        export_button_row.setSpacing(8)
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("ControlButton")
        self.save_btn.clicked.connect(self._save_current)
        self.export_btn = QPushButton("Export")
        self.export_btn.setObjectName("PrimaryButton")
        self.export_btn.clicked.connect(self._export_as)
        export_button_row.addStretch(1)
        export_button_row.addWidget(self.save_btn)
        export_button_row.addWidget(self.export_btn)
        controls_layout.addLayout(export_button_row)

        right_layout.addWidget(controls_card)
        right_layout.addStretch(1)

        content_row.addWidget(canvas_frame, 2)
        content_row.addWidget(right_panel, 1)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addLayout(content_row)

        layout.addWidget(card)

        self._sync_quality_visibility(self.format_combo.currentText())
        self._setup_shortcuts()
        self._update_undo_redo_state()

    def _build_resize_options(self) -> None:
        self.resize_options = QWidget()
        layout = QVBoxLayout(self.resize_options)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        scale_row = QHBoxLayout()
        scale_label = QLabel("Scale %")
        scale_label.setObjectName("FieldLabel")
        self.scale_value = QLabel("100%")
        self.scale_value.setObjectName("FieldLabel")
        scale_row.addWidget(scale_label)
        scale_row.addStretch(1)
        scale_row.addWidget(self.scale_value)

        self.resize_scale_slider = QSlider(Qt.Horizontal)
        self.resize_scale_slider.setObjectName("SeekSlider")
        self.resize_scale_slider.setRange(10, 300)
        self.resize_scale_slider.setValue(100)
        self.resize_scale_slider.valueChanged.connect(self._on_resize_scale_changed)

        size_row = QHBoxLayout()
        width_label = QLabel("W")
        width_label.setObjectName("FieldLabel")
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 9999)
        height_label = QLabel("H")
        height_label.setObjectName("FieldLabel")
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 9999)
        size_row.addWidget(width_label)
        size_row.addWidget(self.width_spin)
        size_row.addWidget(height_label)
        size_row.addWidget(self.height_spin)

        self.keep_ratio = QToolButton()
        self.keep_ratio.setObjectName("LockRatioButton")
        self.keep_ratio.setCheckable(True)
        self.keep_ratio.setChecked(True)
        self._lock_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
            '<path d="M7 10V7a5 5 0 0 1 10 0v3h-2V7a3 3 0 0 0-6 0v3H7Z"/>'
            '<rect x="5" y="10" width="14" height="10" rx="2"/></svg>',
            14,
        )
        self._unlock_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
            '<path d="M17 10V7a5 5 0 0 0-9.8-1H9a3 3 0 0 1 6 1v3h-2Z"/>'
            '<rect x="5" y="10" width="14" height="10" rx="2"/></svg>',
            14,
        )
        self.keep_ratio.setIcon(self._lock_icon)
        self.keep_ratio.setIconSize(QSize(14, 14))
        self.keep_ratio.toggled.connect(self._sync_lock_icon)

        self.width_spin.valueChanged.connect(self._queue_resize_apply)
        self.height_spin.valueChanged.connect(self._queue_resize_apply)
        self.width_spin.valueChanged.connect(self._sync_resize_ratio)
        self.height_spin.valueChanged.connect(self._sync_resize_ratio)

        self.apply_resize_btn = QPushButton("Apply Resize")
        self.apply_resize_btn.setObjectName("ControlButton")
        self.apply_resize_btn.clicked.connect(self._apply_resize)

        layout.addLayout(scale_row)
        layout.addWidget(self.resize_scale_slider)
        layout.addLayout(size_row)
        layout.addWidget(self.keep_ratio)
        layout.addWidget(self.apply_resize_btn)

    def _build_overlay_options(self) -> None:
        self.overlay_options = QWidget()
        layout = QVBoxLayout(self.overlay_options)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        layers_label = QLabel("Layers")
        layers_label.setObjectName("FieldLabel")
        self.add_overlay_btn = QToolButton()
        self.add_overlay_btn.setObjectName("LayerAdd")
        self.add_overlay_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M11 5h2v14h-2z"/><path d="M5 11h14v2H5z"/></svg>',
                12,
            )
        )
        self.add_overlay_btn.setIconSize(QSize(12, 12))
        self.add_overlay_btn.clicked.connect(self._add_overlay)
        header_row.addWidget(layers_label)
        header_row.addStretch(1)
        header_row.addWidget(self.add_overlay_btn)
        self.layers_container = QWidget()
        self.layers_layout = QVBoxLayout(self.layers_container)
        self.layers_layout.setContentsMargins(0, 0, 0, 0)
        self.layers_layout.setSpacing(6)
        self.layers_scroll = QScrollArea()
        self.layers_scroll.setObjectName("LayersScroll")
        self.layers_scroll.setWidgetResizable(True)
        self.layers_scroll.setFrameShape(QFrame.NoFrame)
        self.layers_scroll.setStyleSheet(
            "QScrollArea { background: transparent; } "
            "QScrollArea > QWidget { background: transparent; }"
        )
        self.layers_scroll.setFixedHeight(140)
        self.layers_scroll.setWidget(self.layers_container)

        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setObjectName("VolumeSlider")
        self.scale_slider.setRange(10, 300)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self._update_selected_transform)

        self.rotation_slider = QSlider(Qt.Horizontal)
        self.rotation_slider.setObjectName("SeekSlider")
        self.rotation_slider.setRange(-180, 180)
        self.rotation_slider.setValue(0)
        self.rotation_slider.valueChanged.connect(self._update_selected_transform)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setObjectName("VolumeSlider")
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._update_selected_transform)

        layout.addLayout(header_row)
        layout.addWidget(self.layers_scroll)
        layout.addWidget(QLabel("Scale"))
        layout.addWidget(self.scale_slider)
        layout.addWidget(QLabel("Rotate"))
        layout.addWidget(self.rotation_slider)
        layout.addWidget(QLabel("Opacity"))
        layout.addWidget(self.opacity_slider)

        self.delete_layer_btn = QPushButton("Delete Layer")
        self.delete_layer_btn.setObjectName("ControlButton")
        self.delete_layer_btn.clicked.connect(self._delete_layer)

        layout.addWidget(self.delete_layer_btn)

    def apply_state(self, state: AppState) -> None:
        self.set_theme(state.theme)

    def set_theme(self, theme: str) -> None:
        self.theme_toggle.blockSignals(True)
        self.theme_toggle.setChecked(theme == "Dark")
        self.theme_toggle.blockSignals(False)
        self.theme_toggle.setIcon(self._moon_icon if theme == "Dark" else self._sun_icon)

    def _on_theme_toggled(self, checked: bool) -> None:
        if checked:
            self.theme_toggle.setIcon(self._moon_icon)
            self.on_theme_change("Dark")
        else:
            self.theme_toggle.setIcon(self._sun_icon)
            self.on_theme_change("Light")

    def _open_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            self.state.last_folder_path,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)",
        )
        if not file_path:
            return
        self._set_base_image(Path(file_path))

    def _set_base_image(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            QMessageBox.warning(self, "Error", "Could not load image.")
            return
        self.scene.clear()
        self._base_item = ImageItem(pixmap, is_base=True)
        self._base_item.setZValue(0)
        self.scene.addItem(self._base_item)
        self._current_path = path
        self._export_base_size = (pixmap.width(), pixmap.height())
        base_rect = self._base_item.mapToScene(self._base_item.boundingRect()).boundingRect()
        self._export_base_rect = QRectF(base_rect)
        self._fit_canvas_to_base()
        self._push_state()

    def _fit_canvas_to_base(self) -> None:
        if self._base_item is None:
            return
        base_rect = self._base_item.mapToScene(self._base_item.boundingRect()).boundingRect()
        export_rect = self._export_rect() or base_rect
        pad = max(2000, int(max(export_rect.width(), export_rect.height()) * 2.0))
        scene_rect = export_rect.adjusted(-pad, -pad, pad, pad)
        self.scene.setSceneRect(scene_rect)
        self.canvas_view.reset_zoom()
        self.canvas_view.fitInView(scene_rect, Qt.KeepAspectRatio)
        self._sync_resize_inputs()
        self._update_export_overlay()

    def _on_base_size_changed(self) -> None:
        if self._base_item is None:
            return
        new_w = self._base_item.pixmap().width()
        new_h = self._base_item.pixmap().height()
        if self._export_base_rect is not None and self._export_base_size is not None:
            old_w, old_h = self._export_base_size
            scale_x = new_w / max(1, old_w)
            scale_y = new_h / max(1, old_h)
            center = self._export_base_rect.center()
            new_scene_w = self._export_base_rect.width() * scale_x
            new_scene_h = self._export_base_rect.height() * scale_y
            rect = QRectF(0, 0, new_scene_w, new_scene_h)
            rect.moveCenter(center)
            self._export_base_rect = rect
        else:
            base_rect = self._base_item.mapToScene(self._base_item.boundingRect()).boundingRect()
            self._export_base_rect = QRectF(base_rect)
        self._export_base_size = (new_w, new_h)
        self._update_export_overlay()

    def _sync_resize_inputs(self) -> None:
        if self._base_item is None:
            return
        rect = self._base_item.boundingRect()
        self._resize_base_size = (int(rect.width()), int(rect.height()))
        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        self.width_spin.setValue(int(rect.width()))
        self.height_spin.setValue(int(rect.height()))
        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
        self.resize_scale_slider.blockSignals(True)
        self.resize_scale_slider.setValue(100)
        self.scale_value.setText("100%")
        self.resize_scale_slider.blockSignals(False)

    def _sync_resize_ratio(self) -> None:
        if not self.keep_ratio.isChecked() or self._base_item is None:
            return
        rect = self._base_item.boundingRect()
        if rect.width() == 0 or rect.height() == 0:
            return
        sender = self.sender()
        if sender == self.width_spin:
            ratio = rect.height() / rect.width()
            new_height = int(self.width_spin.value() * ratio)
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(new_height)
            self.height_spin.blockSignals(False)
        elif sender == self.height_spin:
            ratio = rect.width() / rect.height()
            new_width = int(self.height_spin.value() * ratio)
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(new_width)
            self.width_spin.blockSignals(False)

    def _sync_lock_icon(self, checked: bool) -> None:
        self.keep_ratio.setIcon(self._lock_icon if checked else self._unlock_icon)

    def _schedule_export_overlay_update(self) -> None:
        if self._export_update_timer.isActive():
            return
        self._export_update_timer.start(0)

    def _export_rect(self) -> QRectF | None:
        if self._base_item is None:
            return None
        if self._export_base_rect is not None:
            return QRectF(self._export_base_rect)
        return self._base_item.mapToScene(self._base_item.boundingRect()).boundingRect()

    def _ensure_export_overlay(self) -> None:
        if self._export_bg_item is None:
            self._export_bg_item = QGraphicsRectItem()
            self._export_bg_item.setZValue(-1000)
            self._export_bg_item.setPen(Qt.NoPen)
            self._export_bg_item.setBrush(QColor("#ffffff"))
            self._export_bg_item.setAcceptedMouseButtons(Qt.NoButton)
            self.scene.addItem(self._export_bg_item)
        if self._export_mask_item is None:
            self._export_mask_item = QGraphicsPathItem()
            self._export_mask_item.setZValue(800)
            self._export_mask_item.setPen(Qt.NoPen)
            self._export_mask_item.setBrush(self._export_mask_brush())
            self._export_mask_item.setAcceptedMouseButtons(Qt.NoButton)
            self.scene.addItem(self._export_mask_item)

    def _export_mask_brush(self) -> QColor:
        if self.state.theme == "Dark":
            return QColor(15, 11, 13, 140)
        return QColor(0, 0, 0, 60)

    def _update_export_overlay(self) -> None:
        export_rect = self._export_rect()
        if export_rect is None:
            return
        self._ensure_export_overlay()
        if self._export_bg_item is not None:
            self._export_bg_item.setRect(export_rect)
        scene_rect = self.scene.sceneRect()
        path = QPainterPath()
        path.addRect(scene_rect)
        path.addRect(export_rect)
        path.setFillRule(Qt.OddEvenFill)
        if self._export_mask_item is not None:
            self._export_mask_item.setPath(path)
            self._export_mask_item.setBrush(self._export_mask_brush())

    def _on_resize_scale_changed(self, value: int) -> None:
        if self._resize_base_size is None:
            return
        self.scale_value.setText(f"{value}%")
        new_w = max(1, int(self._resize_base_size[0] * value / 100))
        new_h = max(1, int(self._resize_base_size[1] * value / 100))
        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        self.width_spin.setValue(new_w)
        self.height_spin.setValue(new_h)
        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
        self._queue_resize_apply()

    def _queue_resize_apply(self) -> None:
        if self._base_item is None:
            return
        self._resize_timer.start(250)

    def _apply_resize(self) -> None:
        item = self._get_target_image_item()
        if item is None:
            return
        new_w = self.width_spin.value()
        new_h = self.height_spin.value()
        if new_w <= 0 or new_h <= 0:
            return
        pixmap = item.pixmap().scaled(new_w, new_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        item.setPixmap(pixmap)
        if item.is_base:
            self._fit_canvas_to_base()
        self._push_state()
        if item.is_base:
            self._on_base_size_changed()


    def _add_overlay(self) -> None:
        if self._base_item is None:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Add Overlay",
            self.state.last_folder_path,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)",
        )
        if not file_path:
            return
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            return
        item = ImageItem(pixmap, is_base=False)
        rect = self.scene.sceneRect()
        item.setPos(rect.center() - item.boundingRect().center())
        item.setZValue(5)
        self.scene.addItem(item)
        item.setSelected(True)
        self.scale_slider.setValue(100)
        self.rotation_slider.setValue(0)
        self.opacity_slider.setValue(100)
        self._push_state()

    def _update_selected_transform(self) -> None:
        item = self._get_selected_image_item()
        if item is None:
            return
        item.setScale(self.scale_slider.value() / 100)
        item.setRotation(self.rotation_slider.value())
        item.setOpacity(self.opacity_slider.value() / 100)

    def _get_selected_image_item(self) -> ImageItem | None:
        for item in self.scene.selectedItems():
            if isinstance(item, ImageItem):
                return item
        return None

    def _get_selected_layer_item(self) -> QGraphicsItem | None:
        for item in self.scene.selectedItems():
            if isinstance(item, ImageItem):
                return item
        return None

    def _get_target_image_item(self) -> ImageItem | None:
        selected = self._get_selected_image_item()
        if selected is not None:
            return selected
        return self._base_item

    def _delete_layer(self) -> None:
        item = self._get_selected_layer_item()
        if item is None:
            return
        if isinstance(item, ImageItem) and item.is_base:
            return
        self.scene.removeItem(item)
        self._push_state()

    def _collect_layers(self) -> list[QGraphicsItem]:
        layers: list[QGraphicsItem] = []
        for item in self.scene.items():
            if isinstance(item, ImageItem):
                layers.append(item)
        layers.sort(key=lambda i: i.zValue())
        return layers

    def _toggle_layer_visibility(self, item: QGraphicsItem, visible: bool, button: QToolButton) -> None:
        item.setVisible(visible)
        button.setIcon(self._eye_open_icon if visible else self._eye_closed_icon)
        self._refresh_layers_panel()

    def _move_layer(self, item: QGraphicsItem, direction: int) -> None:
        layers = self._collect_layers()
        if item not in layers:
            return
        index = layers.index(item)
        new_index = index + direction
        if new_index < 0 or new_index >= len(layers):
            return
        swap_item = layers[new_index]
        item_z = item.zValue()
        item.setZValue(swap_item.zValue())
        swap_item.setZValue(item_z)
        self._push_state()

    def _refresh_layers_panel(self) -> None:
        while self.layers_layout.count():
            item = self.layers_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        layers = self._collect_layers()
        selected = set(self.scene.selectedItems())
        image_count = 0

        index_map = {item: idx for idx, item in enumerate(layers)}
        for item in reversed(layers):
            row_frame = QFrame()
            row_frame.setObjectName("LayerRow")
            is_selected = item in selected
            row_frame.setProperty("active", is_selected)
            row_frame.setProperty("hidden", not item.isVisible())
            row_frame.style().unpolish(row_frame)
            row_frame.style().polish(row_frame)

            row = QHBoxLayout(row_frame)
            row.setContentsMargins(8, 6, 8, 6)
            row.setSpacing(8)

            badge = QLabel("BG" if isinstance(item, ImageItem) and item.is_base else "IMG")
            badge.setObjectName("LayerBadge")

            label = QLabel()
            label.setObjectName("FieldLabel")

            if isinstance(item, ImageItem):
                if item.is_base:
                    name = "Base Image"
                else:
                    image_count += 1
                    name = f"Image {image_count}"

            label.setText(name)

            eye_btn = QToolButton()
            eye_btn.setObjectName("LayerEye")
            eye_btn.setCheckable(True)
            eye_btn.setChecked(item.isVisible())
            eye_btn.setIcon(self._eye_open_icon if item.isVisible() else self._eye_closed_icon)
            eye_btn.setIconSize(QSize(12, 12))
            eye_btn.toggled.connect(lambda checked, it=item, btn=eye_btn: self._toggle_layer_visibility(it, checked, btn))

            lock_btn = QToolButton()
            lock_btn.setObjectName("LayerLock")
            lock_btn.setIcon(self._lock_layer_icon)
            lock_btn.setIconSize(QSize(12, 12))
            lock_btn.setEnabled(False)

            up_btn = QToolButton()
            up_btn.setObjectName("LayerArrow")
            up_btn.setIcon(self._layer_up_icon)
            up_btn.setIconSize(QSize(12, 12))
            pos = index_map.get(item, 0)
            up_btn.setEnabled(pos < len(layers) - 1)
            up_btn.clicked.connect(lambda checked=False, it=item: self._move_layer(it, 1))

            down_btn = QToolButton()
            down_btn.setObjectName("LayerArrow")
            down_btn.setIcon(self._layer_down_icon)
            down_btn.setIconSize(QSize(12, 12))
            down_btn.setEnabled(pos > 0)
            down_btn.clicked.connect(lambda checked=False, it=item: self._move_layer(it, -1))

            row.addWidget(badge)
            row.addWidget(label, 1)
            row.addWidget(up_btn)
            row.addWidget(down_btn)
            if isinstance(item, ImageItem) and item.is_base:
                row.addWidget(lock_btn)
            row.addWidget(eye_btn)

            self.layers_layout.addWidget(row_frame)

    def _on_selection_changed(self) -> None:
        image_item = self._get_selected_image_item()
        if image_item:
            self.scale_slider.blockSignals(True)
            self.rotation_slider.blockSignals(True)
            self.opacity_slider.blockSignals(True)
            self.scale_slider.setValue(int(image_item.scale() * 100))
            self.rotation_slider.setValue(int(image_item.rotation()))
            self.opacity_slider.setValue(int(image_item.opacity() * 100))
            self.scale_slider.blockSignals(False)
            self.rotation_slider.blockSignals(False)
            self.opacity_slider.blockSignals(False)

        self._refresh_layers_panel()

    def _capture_state(self) -> EditorState:
        image_layers: list[EditorImageLayer] = []

        for item in self.scene.items():
            if isinstance(item, ImageItem):
                layer = EditorImageLayer(
                    image_bytes=pixmap_to_bytes(item.pixmap()),
                    pos=(item.pos().x(), item.pos().y()),
                    scale=item.scale(),
                    rotation=item.rotation(),
                    opacity=item.opacity(),
                    z=item.zValue(),
                    is_base=item.is_base,
                )
                image_layers.append(layer)

        base_size = None
        if self._base_item is not None:
            rect = self._base_item.boundingRect()
            base_size = (int(rect.width()), int(rect.height()))

        return EditorState(base_size=base_size, image_layers=image_layers)

    def _restore_state(self, state: EditorState) -> None:
        self.scene.clear()
        self._base_item = None
        for layer in sorted(state.image_layers, key=lambda l: l.z):
            pixmap = bytes_to_pixmap(layer.image_bytes)
            item = ImageItem(pixmap, is_base=layer.is_base)
            item.setPos(layer.pos[0], layer.pos[1])
            item.setScale(layer.scale)
            item.setRotation(layer.rotation)
            item.setOpacity(layer.opacity)
            item.setZValue(layer.z)
            self.scene.addItem(item)
            if layer.is_base:
                self._base_item = item

        self._fit_canvas_to_base()
        self._refresh_layers_panel()

    def _push_state(self) -> None:
        state = self._capture_state()
        self._undo_stack.append(state)
        if len(self._undo_stack) > 30:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_redo_state()
        self._refresh_layers_panel()

    def _undo(self) -> None:
        if len(self._undo_stack) <= 1:
            return
        state = self._undo_stack.pop()
        self._redo_stack.append(state)
        self._restore_state(self._undo_stack[-1])
        self._update_undo_redo_state()

    def _redo(self) -> None:
        if not self._redo_stack:
            return
        state = self._redo_stack.pop()
        self._undo_stack.append(state)
        self._restore_state(state)
        self._update_undo_redo_state()

    def _update_undo_redo_state(self) -> None:
        if hasattr(self, "undo_btn"):
            self.undo_btn.setEnabled(len(self._undo_stack) > 1)
        if hasattr(self, "redo_btn"):
            self.redo_btn.setEnabled(bool(self._redo_stack))

    def _setup_shortcuts(self) -> None:
        self.undo_shortcut = QShortcut(QKeySequence.Undo, self)
        self.undo_shortcut.activated.connect(self._undo)
        self.redo_shortcut = QShortcut(QKeySequence.Redo, self)
        self.redo_shortcut.activated.connect(self._redo)
        self.redo_alt_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self.redo_alt_shortcut.activated.connect(self._redo)

    def _render_scene(self) -> QImage | None:
        if self._base_item is None:
            return None
        source_rect = self._export_rect()
        if source_rect is None:
            return None
        image = QImage(int(source_rect.width()), int(source_rect.height()), QImage.Format_ARGB32)
        image.fill(Qt.white)
        painter = QPainter(image)
        self.scene.render(painter, target=QRectF(image.rect()), source=source_rect)
        painter.end()
        return image

    def _save_current(self) -> None:
        if self._current_path is None:
            self._export_as()
            return
        ext = self._current_path.suffix.lower()
        fmt = "PNG" if ext == ".png" else "JPG"
        self._save_to_path(self._current_path, fmt)

    def _export_as(self) -> None:
        if self._base_item is None:
            return
        fmt = self.format_combo.currentText()
        filter_text = "PNG Files (*.png)" if fmt == "PNG" else "JPG Files (*.jpg *.jpeg)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export", self.state.last_folder_path, filter_text)
        if not file_path:
            return
        self._save_to_path(Path(file_path), fmt)

    def _save_to_path(self, path: Path, fmt: str) -> None:
        image = self._render_scene()
        if image is None:
            return
        if fmt == "JPG":
            quality = self.quality_slider.value()
            image.save(str(path), "JPG", quality)
        else:
            image.save(str(path), "PNG")
        self._current_path = path

    def _sync_quality_visibility(self, fmt: str) -> None:
        is_jpg = fmt == "JPG"
        self.quality_label.setVisible(is_jpg)
        self.quality_slider.setVisible(is_jpg)

    def _on_quality_changed(self, value: int) -> None:
        return
