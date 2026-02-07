from __future__ import annotations

from pathlib import Path
import fnmatch
import re

from PySide6.QtCore import QByteArray, Qt, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFileDialog,
    QPushButton,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from services.state import AppState
from services.ai_client import ai_available, generate_rename_rules, RenameRules


def svg_icon(svg: str, size: int) -> QIcon:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    renderer.render(painter)
    painter.end()
    return QIcon(QPixmap.fromImage(image))


class RenameFilesPage(QWidget):
    def __init__(self, state: AppState, on_theme_change, on_navigate) -> None:
        super().__init__()
        self.state = state
        self.on_theme_change = on_theme_change
        self.on_navigate = on_navigate
        self._folder: Path | None = None
        self._files: list[Path] = []
        self._plan: list[tuple[str, str]] = []
        self._rules: RenameRules | None = None
        self._ignore_patterns = [
            ".DS_Store",
            ".DS_Store?",
            "Thumbs.db",
            "ehthumbs.db",
            "desktop.ini",
            ".vscode/settings.json",
            ".vscode/tasks.json",
            ".vscode/launch.json",
            ".idea/workspace.xml",
            ".idea/tasks.xml",
            ".idea/*.iml",
            "*.swp",
            "*.swo",
            "*.bak",
            "*.tmp",
            "*.log",
            ".env",
            ".env.local",
            ".env.*.local",
            "npm-debug.log",
            "yarn-error.log",
            "pnpm-debug.log",
            "*.out",
            "*.class",
            "*.exe",
            "*.dll",
            "*.so",
            "*.dylib",
            "*.o",
            "*.a",
            "__pycache__/*.pyc",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "*.pid",
            "*.seed",
            "*.tgz",
            "*.zip",
        ]
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

        title = QLabel("Rename Files")
        title.setObjectName("PreviewTitle")
        subtitle = QLabel("Generate a rename plan with AI.")
        subtitle.setObjectName("SubtitleLabel")

        layout_row = QHBoxLayout()
        layout_row.setSpacing(16)

        left_card = QFrame()
        left_card.setObjectName("OptionsCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        prompt_title = QLabel("AI Prompt")
        prompt_title.setObjectName("SectionLabel")
        left_layout.addWidget(prompt_title)

        self.prompt_input = QPlainTextEdit()
        self.prompt_input.setPlaceholderText("Describe how to rename files...")
        self.prompt_input.setFixedHeight(100)
        self.prompt_input.setStyleSheet(
            "QPlainTextEdit {"
            " background: #24151e;"
            " color: #e9e1e6;"
            " border: none;"
            " border-radius: 8px;"
            " padding: 8px;"
            "}"
        )
        left_layout.addWidget(self.prompt_input)

        files_title = QLabel("Files")
        files_title.setObjectName("SectionLabel")
        left_layout.addWidget(files_title)

        files_row = QHBoxLayout()
        files_row.setSpacing(12)

        self.files_list = QPlainTextEdit()
        self.files_list.setReadOnly(True)
        self.files_list.setPlaceholderText("No folder selected.")
        self.files_list.setFixedHeight(160)
        self.files_list.setStyleSheet(
            "QPlainTextEdit {"
            " background: #24151e;"
            " color: #e9e1e6;"
            " border: none;"
            " border-radius: 8px;"
            " padding: 8px;"
            "}"
        )
        files_row.addWidget(self.files_list, 3)

        self.plan_preview = QPlainTextEdit()
        self.plan_preview.setReadOnly(True)
        self.plan_preview.setPlaceholderText("Rename plan will appear here.")
        self.plan_preview.setFixedHeight(160)
        self.plan_preview.setStyleSheet(
            "QPlainTextEdit {"
            " background: #24151e;"
            " color: #e9e1e6;"
            " border: none;"
            " border-radius: 8px;"
            " padding: 8px;"
            "}"
        )
        files_row.addWidget(self.plan_preview, 2)

        left_layout.addLayout(files_row)

        right_card = QFrame()
        right_card.setObjectName("OptionsCard")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        settings_title = QLabel("Settings")
        settings_title.setObjectName("SectionLabel")
        right_layout.addWidget(settings_title)

        folder_row = QHBoxLayout()
        folder_label = QLabel("Folder")
        folder_label.setObjectName("FieldLabel")
        self.folder_path = QLineEdit()
        self.folder_path.setPlaceholderText("Select a folder...")
        self.folder_path.setReadOnly(True)
        folder_row.addWidget(folder_label)
        folder_row.addStretch(1)
        folder_row.addWidget(self.folder_path)
        right_layout.addLayout(folder_row)

        self.pick_folder_btn = QPushButton("Choose Folder")
        self.pick_folder_btn.setObjectName("ToolButton")
        self.pick_folder_btn.clicked.connect(self._choose_folder)
        right_layout.addWidget(self.pick_folder_btn)

        self.generate_btn = QPushButton("Generate Plan")
        self.generate_btn.setObjectName("PrimaryButton")
        self.generate_btn.clicked.connect(self._generate_plan)
        self.generate_btn.setEnabled(False)
        right_layout.addWidget(self.generate_btn)

        self.apply_btn = QPushButton("Apply Rename")
        self.apply_btn.setObjectName("PrimaryButton")
        self.apply_btn.clicked.connect(self._apply_plan)
        self.apply_btn.setEnabled(False)
        right_layout.addWidget(self.apply_btn)

        self.status = QLabel("")
        self.status.setObjectName("StatusLabel")
        self.status.setVisible(False)
        right_layout.addWidget(self.status)

        layout_row.addWidget(left_card, 3)
        layout_row.addWidget(right_card, 2)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addLayout(layout_row, 1)
        card_layout.addStretch(1)

        root_layout.addWidget(card)

    def set_theme(self, theme: str) -> None:
        return

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Folder",
            self.state.last_folder_path or "",
        )
        if not folder:
            return
        self.state.last_folder_path = folder
        self._folder = Path(folder)
        self.folder_path.setText(folder)
        self._load_files()

    def _load_files(self) -> None:
        if not self._folder or not self._folder.exists():
            return
        self._files = [
            p
            for p in self._folder.iterdir()
            if p.is_file() and not self._should_ignore(p)
        ]
        lines = [p.name for p in self._files]
        self.files_list.setPlainText("\n".join(lines))
        self.plan_preview.setPlainText("")
        self._plan = []
        has_files = bool(self._files)
        self.generate_btn.setEnabled(has_files)
        self.apply_btn.setEnabled(False)

    def _generate_plan(self) -> None:
        if not self._files:
            self._set_status("Choose a folder with files.", error=True)
            return
        if not ai_available(self.state.ai_api_key):
            self._set_status("Set AI API key in Settings to generate.", error=True)
            return
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self._set_status("Enter a prompt.", error=True)
            return
        filenames = [p.name for p in self._files]
        self._rules = generate_rename_rules(prompt, filenames, api_key=self.state.ai_api_key)
        self._plan = self._build_plan_from_rules(filenames, self._rules)
        preview_lines = [f"{old}  →  {new}" for old, new in self._plan]
        self.plan_preview.setPlainText("\n".join(preview_lines))
        self._set_status("Plan ready.", error=False)
        self.apply_btn.setEnabled(True)

    def _apply_plan(self) -> None:
        if not self._folder or not self._plan:
            self._set_status("Generate a rename plan first.", error=True)
            return
        rename_pairs = []
        for old, new in self._plan:
            if old == new:
                continue
            src = self._folder / old
            dst = self._folder / new
            if dst.exists():
                self._set_status(f"Target exists: {new}", error=True)
                return
            rename_pairs.append((src, dst))
        for src, dst in rename_pairs:
            src.rename(dst)
        self._load_files()
        self._set_status("Rename complete.", error=False)

    def _build_plan_from_rules(self, filenames: list[str], rules: RenameRules) -> list[tuple[str, str]]:
        used = set(filenames)
        plan: list[tuple[str, str]] = []
        numbering = rules.numbering or {"enabled": False}
        counter = int(numbering.get("start", 1))
        padding = int(numbering.get("padding", 2))
        num_prefix = str(numbering.get("prefix", "") or "")
        num_suffix = str(numbering.get("suffix", "") or "")
        skip_if_numbered = bool(numbering.get("skip_if_numbered", True))

        for name in filenames:
            stem, ext = self._split_name(name)
            if rules.preserve_extensions:
                target_ext = ext
            else:
                target_ext = rules.extension or ext

            if self._should_skip(stem, rules):
                new_name = name
            else:
                new_stem = stem
                if rules.replace:
                    for item in rules.replace:
                        pattern = item.get("pattern", "")
                        replacement = item.get("replacement", "")
                        if pattern:
                            new_stem = re.sub(pattern, replacement, new_stem)
                if rules.case == "lower":
                    new_stem = new_stem.lower()
                elif rules.case == "upper":
                    new_stem = new_stem.upper()
                new_stem = f"{rules.prefix}{new_stem}{rules.suffix}"

                if numbering.get("enabled", False):
                    if skip_if_numbered and re.match(r"^\\d+", stem):
                        new_stem = stem
                    else:
                        new_stem = f"{num_prefix}{str(counter).zfill(padding)}{num_suffix}"
                        counter += 1

                new_name = f"{new_stem}{target_ext}"
            new_name = self._resolve_collision(new_name, used)
            used.add(new_name)
            plan.append((name, new_name))
        return plan

    def _split_name(self, name: str) -> tuple[str, str]:
        path = Path(name)
        return path.stem, path.suffix

    def _resolve_collision(self, name: str, used: set[str]) -> str:
        if name not in used:
            return name
        stem, ext = self._split_name(name)
        index = 2
        while True:
            candidate = f"{stem}_{index}{ext}"
            if candidate not in used:
                return candidate
            index += 1

    def _should_skip(self, stem: str, rules: RenameRules) -> bool:
        if not rules.skip_if_matches:
            return False
        for pattern in rules.skip_if_matches:
            try:
                if re.search(pattern, stem):
                    return True
            except re.error:
                continue
        return False

    def _should_ignore(self, path: Path) -> bool:
        if not self._folder:
            return False
        rel = path.relative_to(self._folder).as_posix()
        for pattern in self._ignore_patterns:
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern):
                return True
        return False

    def _set_status(self, message: str, error: bool) -> None:
        self.status.setText(message)
        self.status.setVisible(True)
        color = "#b00020" if error else "#b25574"
        self.status.setStyleSheet(f"color: {color};")
