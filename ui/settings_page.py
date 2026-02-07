from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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


class SettingsPage(QWidget):
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

        self.settings_icon_btn = QToolButton()
        self.settings_icon_btn.setObjectName("ThemeToggle")
        self.settings_icon_btn.setEnabled(False)
        self.settings_icon_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm8.94 4a7.87 7.87 0 0 0-.13-1.43l2.02-1.58-1.9-3.29-2.45.98a8.2 8.2 0 0 0-2.48-1.44L15.5 2h-3l-.5 2.24a8.2 8.2 0 0 0-2.48 1.44l-2.45-.98-1.9 3.29 2.02 1.58A7.87 7.87 0 0 0 7.06 12c0 .49.05.97.13 1.43l-2.02 1.58 1.9 3.29 2.45-.98a8.2 8.2 0 0 0 2.48 1.44L12.5 22h3l.5-2.24a8.2 8.2 0 0 0 2.48-1.44l2.45.98 1.9-3.29-2.02-1.58c.08-.46.13-.94.13-1.43Z" fill="#f7c6de"/></svg>',
                12,
            )
        )
        self.settings_icon_btn.setIconSize(QSize(12, 12))
        nav_bar.addWidget(self.settings_icon_btn)

        top_divider = QFrame()
        top_divider.setObjectName("Divider")
        top_divider.setFixedHeight(1)
        top_divider.setFrameShape(QFrame.HLine)

        title = QLabel("Settings")
        title.setObjectName("PreviewTitle")
        subtitle = QLabel("Configure Orca.")
        subtitle.setObjectName("SubtitleLabel")

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

        theme_card = QFrame()
        theme_card.setObjectName("OptionsCard")
        theme_layout = QVBoxLayout(theme_card)
        theme_layout.setContentsMargins(16, 16, 16, 16)
        theme_layout.setSpacing(12)

        theme_title = QLabel("Appearance")
        theme_title.setObjectName("SectionLabel")
        theme_layout.addWidget(theme_title)

        theme_row = QHBoxLayout()
        theme_label = QLabel("Theme")
        theme_label.setObjectName("FieldLabel")
        self.theme_toggle = QToolButton()
        self.theme_toggle.setObjectName("ThemeToggle")
        self.theme_toggle.setCheckable(True)
        self.theme_toggle.setIcon(self._sun_icon)
        self.theme_toggle.setIconSize(QSize(12, 12))
        self.theme_toggle.toggled.connect(self._on_theme_toggled)
        theme_row.addWidget(theme_label)
        theme_row.addStretch(1)
        theme_row.addWidget(self.theme_toggle)
        theme_layout.addLayout(theme_row)

        ai_card = QFrame()
        ai_card.setObjectName("OptionsCard")
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(16, 16, 16, 16)
        ai_layout.setSpacing(12)

        ai_title = QLabel("AI")
        ai_title.setObjectName("SectionLabel")
        ai_layout.addWidget(ai_title)

        ai_row = QHBoxLayout()
        ai_label = QLabel("API Key")
        ai_label.setObjectName("FieldLabel")
        self.ai_key_input = QLineEdit()
        self.ai_key_input.setPlaceholderText("Enter API key")
        self.ai_key_input.setEchoMode(QLineEdit.Password)
        self.ai_key_input.editingFinished.connect(self._save_ai_key)
        ai_row.addWidget(ai_label)
        ai_row.addStretch(1)
        ai_row.addWidget(self.ai_key_input)
        ai_layout.addLayout(ai_row)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(theme_card)
        card_layout.addWidget(ai_card)
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
        self.ai_key_input.blockSignals(True)
        self.ai_key_input.setText(self.state.ai_api_key)
        self.ai_key_input.blockSignals(False)

    def _save_ai_key(self) -> None:
        self.state.ai_api_key = self.ai_key_input.text().strip()
