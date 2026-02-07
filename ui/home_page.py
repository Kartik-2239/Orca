from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QRect, QPoint
from PySide6.QtGui import QIcon, QPainter, QPixmap, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLayout,
    QLayoutItem,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
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


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []

    def addItem(self, item) -> None:
        self._items.append(item)

    def addWidget(self, widget: QWidget) -> None:
        self.addItem(QWidgetItem(widget))

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0
        space_x = self.spacing()
        space_y = self.spacing()

        for item in self._items:
            widget = item.widget()
            if widget is None:
                continue
            space_x = self.spacing()
            space_y = self.spacing()
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


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

        title = QLabel("Choose an action")
        title.setObjectName("PreviewTitle")

        btn_flow = FlowLayout()
        btn_flow.setSpacing(12)
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
        self.download_btn.setText("Video Downloader")
        self.download_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
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
        self.editor_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.editor_btn.clicked.connect(lambda: self.on_navigate("image_editor"))

        self.pdf_btn = QToolButton()
        self.pdf_btn.setObjectName("ActionButton")
        self.pdf_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.pdf_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M6 2h7l5 5v15a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z"/>'
                '<path d="M13 2v5h5" fill="#f7c6de"/>'
                '<path d="M8 12h8v2H8zm0 4h6v2H8z"/></svg>',
                24,
            )
        )
        self.pdf_btn.setIconSize(QSize(24, 24))
        self.pdf_btn.setText("PDF")
        self.pdf_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.pdf_btn.clicked.connect(lambda: self.on_navigate("pdf_editor"))

        self.bulk_images_btn = QToolButton()
        self.bulk_images_btn.setObjectName("ActionButton")
        self.bulk_images_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.bulk_images_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M4 4h7v7H4z"/><path d="M13 4h7v7h-7z" fill="#f7c6de"/>'
                '<path d="M4 13h7v7H4z" fill="#f7c6de"/><path d="M13 13h7v7h-7z"/>'
                '<path d="M12 9h3v2h-3z"/></svg>',
                24,
            )
        )
        self.bulk_images_btn.setIconSize(QSize(24, 24))
        self.bulk_images_btn.setText("Image Downloader")
        self.bulk_images_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.bulk_images_btn.clicked.connect(lambda: self.on_navigate("image_downloader"))

        self.video_edit_btn = QToolButton()
        self.video_edit_btn.setObjectName("ActionButton")
        self.video_edit_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.video_edit_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M4 5h10a2 2 0 0 1 2 2v1l4-2v10l-4-2v1a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z"/>'
                '<path d="M6 9h4v2H6zM6 13h6v2H6z" fill="#f7c6de"/></svg>',
                24,
            )
        )
        self.video_edit_btn.setIconSize(QSize(24, 24))
        self.video_edit_btn.setText("Video Tools")
        self.video_edit_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.video_edit_btn.clicked.connect(lambda: self.on_navigate("video_edits"))

        buttons = [
            self.download_btn,
            self.pdf_btn,
            self.bulk_images_btn,
            self.video_edit_btn,
            self.editor_btn,
        ]
        for button in buttons:
            btn_flow.addWidget(button)

        ai_title = QLabel("AI Tools")
        ai_title.setObjectName("SectionLabel")

        ai_flow = QHBoxLayout()
        ai_flow.setSpacing(10)

        self.anime_upscale_btn = QToolButton()
        self.anime_upscale_btn.setObjectName("ActionButton")
        self.anime_upscale_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.anime_upscale_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M4 6h16v12H4z"/><path d="M7 9h4v4H7z" fill="#f7c6de"/>'
                '<path d="M14 9h3v3h-3z"/></svg>',
                24,
            )
        )
        self.anime_upscale_btn.setIconSize(QSize(24, 24))
        self.anime_upscale_btn.setText("Art Upscale")
        self.anime_upscale_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.generate_docs_btn = QToolButton()
        self.generate_docs_btn.setObjectName("ActionButton")
        self.generate_docs_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.generate_docs_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M6 2h7l5 5v15a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z"/>'
                '<path d="M13 2v5h5" fill="#f7c6de"/>'
                '<path d="M8 12h8v2H8zm0 4h6v2H8z"/></svg>',
                24,
            )
        )
        self.generate_docs_btn.setIconSize(QSize(24, 24))
        self.generate_docs_btn.setText("Generate Docs")
        self.generate_docs_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.generate_docs_btn.clicked.connect(lambda: self.on_navigate("generate_docs"))

        self.rename_files_btn = QToolButton()
        self.rename_files_btn.setObjectName("ActionButton")
        self.rename_files_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.rename_files_btn.setIcon(
            svg_icon(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
                '<path d="M4 4h16v5H4z"/><path d="M4 10h10v10H4z" fill="#f7c6de"/>'
                '<path d="M16 12h4v2h-4zM16 16h4v2h-4z"/></svg>',
                24,
            )
        )
        self.rename_files_btn.setIconSize(QSize(24, 24))
        self.rename_files_btn.setText("Rename Files")
        self.rename_files_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.rename_files_btn.clicked.connect(lambda: self.on_navigate("rename_files"))

        ai_flow.addWidget(self.anime_upscale_btn)
        ai_flow.addWidget(self.generate_docs_btn)
        ai_flow.addWidget(self.rename_files_btn)
        ai_flow.addStretch(1)

        top_divider = QFrame()
        top_divider.setObjectName("Divider")
        top_divider.setFixedHeight(1)
        top_divider.setFrameShape(QFrame.HLine)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addWidget(title)
        card_layout.addLayout(btn_flow)
        card_layout.addWidget(ai_title)
        card_layout.addLayout(ai_flow)
        card_layout.addStretch(1)

        layout.addWidget(card)
        self.apply_state(state)

    def apply_state(self, state: AppState) -> None:
        self.set_theme(state.theme)

    def _on_theme_toggled(self, checked: bool) -> None:
        if checked:
            self.on_theme_change("Dark")
        else:
            self.on_theme_change("Light")

    def set_theme(self, theme: str) -> None:
        return
