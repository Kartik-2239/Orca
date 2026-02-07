from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFileDialog,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from services.state import AppState
from services.ai_client import generate_text, ai_available


def svg_icon(svg: str, size: int) -> QIcon:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    renderer.render(painter)
    painter.end()
    return QIcon(QPixmap.fromImage(image))


class GenerateDocsPage(QWidget):
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

        title = QLabel("Generate Docs")
        title.setObjectName("PreviewTitle")
        subtitle = QLabel("Create multiple text files from a prompt.")
        subtitle.setObjectName("SubtitleLabel")

        layout_row = QHBoxLayout()
        layout_row.setSpacing(16)

        prompt_card = QFrame()
        prompt_card.setObjectName("OptionsCard")
        prompt_layout = QVBoxLayout(prompt_card)
        prompt_layout.setContentsMargins(16, 16, 16, 16)
        prompt_layout.setSpacing(12)

        prompt_title = QLabel("AI Chat")
        prompt_title.setObjectName("SectionLabel")
        prompt_layout.addWidget(prompt_title)

        self.prompt_input = QPlainTextEdit()
        self.prompt_input.setPlaceholderText("Describe what you want in the docs...")
        self.prompt_input.setFixedHeight(90)
        self.prompt_input.setStyleSheet(
            "QPlainTextEdit {"
            " background: #24151e;"
            " color: #e9e1e6;"
            " border: none;"
            " border-radius: 8px;"
            " padding: 8px;"
            "}"
        )
        prompt_layout.addWidget(self.prompt_input, 0)

        output_title = QLabel("Preview")
        output_title.setObjectName("SectionLabel")
        prompt_layout.addWidget(output_title)

        self.output_preview = QPlainTextEdit()
        self.output_preview.setReadOnly(True)
        self.output_preview.setPlaceholderText("Generated text will appear here.")
        self.output_preview.setFixedHeight(210)
        self.output_preview.setStyleSheet(
            "QPlainTextEdit {"
            " background: #24151e;"
            " color: #e9e1e6;"
            " border: none;"
            " border-radius: 8px;"
            " padding: 8px;"
            "}"
        )
        prompt_layout.addWidget(self.output_preview, 0)

        controls_card = QFrame()
        controls_card.setObjectName("OptionsCard")
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(16, 16, 16, 16)
        controls_layout.setSpacing(12)

        controls_title = QLabel("Settings")
        controls_title.setObjectName("SectionLabel")
        controls_layout.addWidget(controls_title)

        count_row = QHBoxLayout()
        count_label = QLabel("Number of Docs")
        count_label.setObjectName("FieldLabel")
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 20)
        self.count_spin.setValue(5)
        count_row.addWidget(count_label)
        count_row.addStretch(1)
        count_row.addWidget(self.count_spin)
        controls_layout.addLayout(count_row)

        type_row = QHBoxLayout()
        type_label = QLabel("File Type")
        type_label.setObjectName("FieldLabel")
        self.type_combo = QComboBox()
        self.type_combo.addItems([".txt", ".md", ".rtf"])
        type_row.addWidget(type_label)
        type_row.addStretch(1)
        type_row.addWidget(self.type_combo)
        controls_layout.addLayout(type_row)

        name_row = QHBoxLayout()
        name_label = QLabel("Base Name")
        name_label.setObjectName("FieldLabel")
        self.base_name = QLineEdit()
        self.base_name.setPlaceholderText("document")
        self.base_name.setText("file")
        name_row.addWidget(name_label)
        name_row.addStretch(1)
        name_row.addWidget(self.base_name)
        controls_layout.addLayout(name_row)

        self.ai_names_toggle = QCheckBox("Use AI filenames")
        self.ai_names_toggle.stateChanged.connect(self._toggle_ai_names)
        controls_layout.addWidget(self.ai_names_toggle)

        self.generate_btn = QPushButton("Generate Preview")
        self.generate_btn.setObjectName("PrimaryButton")
        self.generate_btn.clicked.connect(self._generate_preview)
        controls_layout.addWidget(self.generate_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self._save_files)
        controls_layout.addWidget(self.save_btn)

        self.status = QLabel("")
        self.status.setObjectName("StatusLabel")
        self.status.setVisible(False)
        controls_layout.addWidget(self.status)

        layout_row.addWidget(prompt_card, 3)
        layout_row.addWidget(controls_card, 2)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addLayout(layout_row, 1)
        card_layout.addStretch(1)

        root_layout.addWidget(card)

    def set_theme(self, theme: str) -> None:
        return

    def _generate_preview(self) -> None:
        count = self.count_spin.value()
        if not ai_available(self.state.ai_api_key):
            self._set_status("Set AI API key in Settings to generate.", error=True)
            return
        sentences = generate_text(
            self.prompt_input.toPlainText(),
            count,
            mode="content",
            api_key=self.state.ai_api_key,
        ).items
        self.output_preview.setPlainText("\n\n".join(sentences))
        self._set_status("Preview ready.", error=False)

    def _save_files(self) -> None:
        count = self.count_spin.value()
        extension = self.type_combo.currentText()
        prompt = self.prompt_input.toPlainText().strip().lower()
        if not ai_available(self.state.ai_api_key):
            self._set_status("Set AI API key in Settings to generate.", error=True)
            return
        sentences = self.output_preview.toPlainText().strip().split("\n\n")
        if not sentences or not sentences[0]:
            sentences = generate_text(
                self.prompt_input.toPlainText(),
                count,
                mode="content",
                api_key=self.state.ai_api_key,
            ).items
            self.output_preview.setPlainText("\n\n".join(sentences))

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Choose Output Folder",
            self.state.last_folder_path or "",
        )
        if not output_dir:
            return
        self.state.last_folder_path = output_dir

        filenames = self._choose_filenames(prompt, count, extension)
        for idx, sentence in enumerate(sentences[:count], start=1):
            filename = filenames[idx - 1]
            Path(output_dir, filename).write_text(sentence)

        self._set_status(f"Saved {count} files.", error=False)

    def _choose_filenames(self, prompt: str, count: int, extension: str) -> list[str]:
        if not self.ai_names_toggle.isChecked():
            base = self.base_name.text().strip() or "file"
            return [f"{base}_{idx:02d}{extension}" for idx in range(1, count + 1)]
        names = generate_text(prompt, count, mode="names", api_key=self.state.ai_api_key).items
        return [f"{name}{extension}" for name in names]

    def _toggle_ai_names(self, _state: int) -> None:
        self.base_name.setEnabled(not self.ai_names_toggle.isChecked())

    def _set_status(self, message: str, error: bool) -> None:
        self.status.setText(message)
        self.status.setVisible(True)
        color = "#b00020" if error else "#b25574"
        self.status.setStyleSheet(f"color: {color};")
