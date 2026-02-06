from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout, QWidget
from PySide6.QtCore import QByteArray

from services.state import AppState


def svg_icon(svg: str, size: int) -> QIcon:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    renderer.render(painter)
    painter.end()
    return QIcon(QPixmap.fromImage(image))


class HomePage(QWidget):
    def __init__(self, state: AppState, on_theme_change, on_navigate) -> None:
        super().__init__()
        self.state = state
        self.on_theme_change = on_theme_change
        self.on_navigate = on_navigate

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

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
        home_btn.setEnabled(False)
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

        title = QLabel("Choose an action")
        title.setObjectName("PreviewTitle")

        btn_row = QHBoxLayout()
        self.download_btn = QToolButton()
        self.download_btn.setObjectName("ActionButton")
        self.download_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.download_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M12 3a1 1 0 0 1 1 1v8.17l2.59-2.58a1 1 0 1 1 1.41 1.42l-4.3 4.29a1 1 0 0 1-1.4 0L6 11.01a1 1 0 1 1 1.41-1.42L10 12.17V4a1 1 0 0 1 1-1Z"/>'
                '<path d="M5 19a1 1 0 0 1 1-1h12a1 1 0 1 1 0 2H6a1 1 0 0 1-1-1Z"/></svg>',
                24,
            )
        )
        self.download_btn.setIconSize(QSize(24, 24))
        self.download_btn.setText("Download")
        self.download_btn.clicked.connect(lambda: self.on_navigate("download"))

        self.editor_btn = QToolButton()
        self.editor_btn.setObjectName("ActionButton")
        self.editor_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.editor_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M4 20h4l9-9-4-4-9 9v4Z"/>'
                '<path d="M14.5 5.5 18.5 9.5 20 8l-4-4-1.5 1.5Z"/></svg>',
                24,
            )
        )
        self.editor_btn.setIconSize(QSize(24, 24))
        self.editor_btn.setText("Editor")
        self.editor_btn.clicked.connect(lambda: self.on_navigate("image_editor"))

        btn_row.addWidget(self.download_btn, 0, Qt.AlignLeft)
        btn_row.addSpacing(12)
        btn_row.addWidget(self.editor_btn, 0, Qt.AlignLeft)

        top_divider = QFrame()
        top_divider.setObjectName("Divider")
        top_divider.setFixedHeight(1)
        top_divider.setFrameShape(QFrame.HLine)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addWidget(title)
        card_layout.addLayout(btn_row)
        card_layout.addStretch(1)

        layout.addWidget(card)
        self.apply_state(state)

    def apply_state(self, state: AppState) -> None:
        self.set_theme(state.theme)

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
