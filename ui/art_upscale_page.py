from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QFileDialog,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
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


class ArtUpscalePage(QWidget):
    def __init__(self, state: AppState, on_theme_change, on_navigate) -> None:
        super().__init__()
        self.state = state
        self.on_theme_change = on_theme_change
        self.on_navigate = on_navigate
        self._files: list[Path] = []
        self._build_ui()
        self.set_theme(state.theme)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QWidget(self)
        card.setObjectName("MainCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        nav_bar = QHBoxLayout()
        icon_badge = QLabel("DL")
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

        self.settings_icon_btn = QToolButton()
        self.settings_icon_btn.setObjectName("ThemeToggle")
        self.settings_icon_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm8.94 4a7.87 7.87 0 0 0-.13-1.43l2.02-1.58-1.9-3.29-2.45.98a8.2 8.2 0 0 0-2.48-1.44L15.5 2h-3l-.5 2.24a8.2 8.2 0 0 0-2.48 1.44l-2.45-.98-1.9 3.29 2.02 1.58A7.87 7.87 0 0 0 7.06 12c0 .49.05.97.13 1.43l-2.02 1.58 1.9 3.29 2.45-.98a8.2 8.2 0 0 0 2.48 1.44L12.5 22h3l.5-2.24a8.2 8.2 0 0 0 2.48-1.44l2.45.98 1.9-3.29-2.02-1.58c.08-.46.13-.94.13-1.43Z" fill="#f7c6de"/></svg>',
                12,
            )
        )
        self.settings_icon_btn.setIconSize(QSize(12, 12))
        self.settings_icon_btn.clicked.connect(lambda: self.on_navigate("settings"))
        nav_bar.addWidget(self.settings_icon_btn)

        top_divider = QFrame()
        top_divider.setObjectName("Divider")
        top_divider.setFixedHeight(1)
        top_divider.setFrameShape(QFrame.HLine)

        header_row = QHBoxLayout()
        title = QLabel("Art Upscale")
        title.setObjectName("PreviewTitle")
        subtitle = QLabel("Prepare images for upscaling.")
        subtitle.setObjectName("SubtitleLabel")
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(subtitle)

        viewer_row = QHBoxLayout()
        viewer_row.setSpacing(16)

        self.input_view = QLabel("Input Preview")
        self.input_view.setAlignment(Qt.AlignCenter)
        self.input_view.setMinimumSize(320, 240)
        self.input_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.input_view.setStyleSheet(
            "QLabel { background: #24151e; color: #b690a5; border-radius: 10px; }"
        )

        self.output_view = QLabel("Upscaled Output")
        self.output_view.setAlignment(Qt.AlignCenter)
        self.output_view.setMinimumSize(320, 240)
        self.output_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.output_view.setStyleSheet(
            "QLabel { background: #24151e; color: #b690a5; border-radius: 10px; }"
        )

        viewer_row.addWidget(self.input_view, 1)
        viewer_row.addWidget(self.output_view, 1)

        controls_row = QHBoxLayout()
        self.choose_btn = QPushButton("Choose Images")
        self.choose_btn.setObjectName("PrimaryButton")
        self.choose_btn.clicked.connect(self._choose_files)
        self.upscale_btn = QPushButton("Upscale")
        self.upscale_btn.setObjectName("PrimaryButton")
        self.upscale_btn.clicked.connect(self._upscale_stub)
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self._save_stub)
        controls_row.addWidget(self.choose_btn)
        controls_row.addWidget(self.upscale_btn)
        controls_row.addWidget(self.save_btn)
        controls_row.addStretch(1)

        self.status = QLabel("")
        self.status.setObjectName("StatusLabel")
        self.status.setVisible(False)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addLayout(header_row)
        card_layout.addLayout(viewer_row, 1)
        card_layout.addLayout(controls_row)
        card_layout.addWidget(self.status)
        card_layout.addStretch(1)

        root_layout.addWidget(card)

    def set_theme(self, theme: str) -> None:
        return

    def _choose_files(self) -> None:
        start_dir = self.state.last_folder_path or ""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            start_dir,
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif);;All Files (*)",
        )
        if not files:
            return
        self._files = [Path(path) for path in files]
        self.output_view.clear()
        self.output_view.setText("Upscaled Output")
        self.state.last_folder_path = str(Path(files[0]).parent)
        self._load_preview(self._files[0])
        self._set_status(f"Selected {len(self._files)} image(s).", error=False)

    def _load_preview(self, path: Path) -> None:
        image = QImage(str(path))
        if image.isNull():
            self._set_status("Failed to load image.", error=True)
            return
        pixmap = QPixmap.fromImage(image)
        self.input_view.setPixmap(pixmap.scaled(self.input_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._files:
            self._load_preview(self._files[0])

    def _upscale_stub(self) -> None:
        self._set_status("Upscale not implemented yet.", error=True)

    def _save_stub(self) -> None:
        if not self._files:
            self._set_status("Select images before saving.", error=True)
            return
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            self.state.last_folder_path or "",
        )
        if not folder:
            return
        self.state.last_folder_path = folder
        names = []
        for path in self._files:
            stem = path.stem
            ext = path.suffix or ".png"
            names.append(f"{stem}_upscaled{ext}")
        self._set_status(f"Will save to: {folder} ({len(names)} files)", error=False)

    def _set_status(self, message: str, error: bool) -> None:
        self.status.setText(message)
        self.status.setVisible(True)
        color = "#b00020" if error else "#b25574"
        self.status.setStyleSheet(f"color: {color};")
