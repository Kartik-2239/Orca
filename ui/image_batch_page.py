from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
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


class ImageBatchPage(QWidget):
    def __init__(self, state: AppState, on_theme_change, on_navigate) -> None:
        super().__init__()
        self.state = state
        self.on_theme_change = on_theme_change
        self.on_navigate = on_navigate

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

        title = QLabel("Image Batch Tools")
        title.setObjectName("PreviewTitle")
        subtitle = QLabel("Quick shortcuts (coming soon).")
        subtitle.setObjectName("SubtitleLabel")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setAlignment(Qt.AlignLeft)

        self.upscale_btn = QToolButton()
        self.upscale_btn.setObjectName("ActionButton")
        self.upscale_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.upscale_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M4 4h6v2H6v4H4V4Zm10 0h6v6h-2V6h-4V4ZM4 14h2v4h4v2H4v-6Zm14 0h2v6h-6v-2h4v-4Z"/>'
                '<path d="M9 9h6v6H9z" fill="#f7c6de"/></svg>',
                24,
            )
        )
        self.upscale_btn.setIconSize(QSize(24, 24))
        self.upscale_btn.setText("Anime Upscale")

        self.rename_btn = QToolButton()
        self.rename_btn.setObjectName("ActionButton")
        self.rename_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.rename_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M4 5h10v2H4zM4 9h10v2H4zM4 13h6v2H4z"/>'
                '<path d="M14 14.5 18.5 10 20 11.5 15.5 16H14v-1.5Z" fill="#f7c6de"/></svg>',
                24,
            )
        )
        self.rename_btn.setIconSize(QSize(24, 24))
        self.rename_btn.setText("Rename Files")

        self.docs_btn = QToolButton()
        self.docs_btn.setObjectName("ActionButton")
        self.docs_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.docs_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M6 2h7l5 5v15a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z"/>'
                '<path d="M13 2v5h5" fill="#f7c6de"/>'
                '<path d="M8 12h8v2H8zm0 4h6v2H8z"/></svg>',
                24,
            )
        )
        self.docs_btn.setIconSize(QSize(24, 24))
        self.docs_btn.setText("Generate Docs")

        btn_row.addWidget(self.upscale_btn, 0, Qt.AlignLeft)
        btn_row.addWidget(self.rename_btn, 0, Qt.AlignLeft)
        btn_row.addWidget(self.docs_btn, 0, Qt.AlignLeft)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addLayout(btn_row)
        card_layout.addStretch(1)

        root_layout.addWidget(card)

    def _on_theme_toggled(self, checked: bool) -> None:
        if checked:
            self.theme_toggle.setIcon(self._moon_icon)
            self.on_theme_change("Dark")
        else:
            self.theme_toggle.setIcon(self._sun_icon)
            self.on_theme_change("Light")

    def set_theme(self, theme: str) -> None:
        self.theme_toggle.blockSignals(True)
        self.theme_toggle.setChecked(theme == "Dark")
        self.theme_toggle.blockSignals(False)
        self.theme_toggle.setIcon(self._moon_icon if theme == "Dark" else self._sun_icon)
