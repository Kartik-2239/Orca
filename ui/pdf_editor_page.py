from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz
from PySide6.QtCore import QByteArray, Qt, QSize
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QListView,
    QStackedLayout,
    QTabWidget,
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


def pixmap_from_fitz(pix: fitz.Pixmap) -> QPixmap:
    if pix.alpha:
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGBA8888)
    else:
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
    return QPixmap.fromImage(image.copy())


def parse_range_groups(value: str, max_pages: int) -> list[list[int]]:
    groups: list[list[int]] = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            if "-" in token:
                start_s, end_s = token.split("-", 1)
                if not start_s.strip() or not end_s.strip():
                    continue
                start = int(start_s) - 1
                end = int(end_s) - 1
                if start > end:
                    start, end = end, start
                pages = [idx for idx in range(start, end + 1) if 0 <= idx < max_pages]
            else:
                idx = int(token) - 1
                pages = [idx] if 0 <= idx < max_pages else []
        except ValueError:
            continue
        if pages:
            groups.append(pages)
    return groups


@dataclass
class PdfTabState:
    path: Path
    dirty: bool = False


class PdfTab(QWidget):
    def __init__(self, path: Path, state: AppState, on_dirty_change) -> None:
        super().__init__()
        self.state = state
        self.on_dirty_change = on_dirty_change
        self.tab_state = PdfTabState(path=path, dirty=False)
        self.doc = fitz.open(path)
        self._current_pixmap: QPixmap | None = None
        self._zoom = 1.0
        self._page_labels: list[QLabel] = []

        self._build_ui()
        self._refresh_pages()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        left_panel = QFrame(self)
        left_panel.setObjectName("EditorPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        left_panel.setMaximumWidth(200)

        pages_label = QLabel("PAGES")
        pages_label.setObjectName("SectionLabel")
        left_layout.addWidget(pages_label)

        self.page_list = QListWidget()
        self.page_list.setObjectName("PdfPageList")
        self.page_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.page_list.setIconSize(QSize(108, 144))
        self.page_list.setViewMode(QListView.IconMode)
        self.page_list.setResizeMode(QListView.Adjust)
        self.page_list.setMovement(QListView.Static)
        self.page_list.setSpacing(12)
        self.page_list.setUniformItemSizes(True)
        self.page_list.currentRowChanged.connect(self._render_preview)
        left_layout.addWidget(self.page_list, 1)

        list_controls = QHBoxLayout()
        self.move_up_btn = QPushButton("Move Up")
        self.move_down_btn = QPushButton("Move Down")
        list_controls.addWidget(self.move_up_btn)
        list_controls.addWidget(self.move_down_btn)
        left_layout.addLayout(list_controls)

        list_controls_2 = QHBoxLayout()
        self.delete_btn = QPushButton("Delete")
        self.rotate_left_btn = QPushButton("Rotate Left")
        self.rotate_right_btn = QPushButton("Rotate Right")
        list_controls_2.addWidget(self.delete_btn)
        list_controls_2.addWidget(self.rotate_left_btn)
        list_controls_2.addWidget(self.rotate_right_btn)
        left_layout.addLayout(list_controls_2)

        preview_frame = QFrame(self)
        preview_frame.setObjectName("PdfPreview")
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(18, 18, 18, 18)
        preview_layout.setSpacing(8)

        zoom_row = QHBoxLayout()
        zoom_row.addStretch(1)
        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setObjectName("ToolButton")
        self.zoom_out_btn.setText("–")
        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setObjectName("ToolButton")
        self.zoom_in_btn.setText("+")
        self.zoom_fit_btn = QToolButton()
        self.zoom_fit_btn.setObjectName("ToolButton")
        self.zoom_fit_btn.setText("Fit")
        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("FieldLabel")
        zoom_row.addWidget(self.zoom_out_btn)
        zoom_row.addWidget(self.zoom_in_btn)
        zoom_row.addWidget(self.zoom_fit_btn)
        zoom_row.addWidget(self.zoom_label)
        preview_layout.addLayout(zoom_row)

        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setFrameShape(QFrame.NoFrame)
        self.preview_container = QWidget()
        self.preview_container.setObjectName("PdfPreviewContainer")
        self.preview_stack = QVBoxLayout(self.preview_container)
        self.preview_stack.setContentsMargins(0, 0, 0, 0)
        self.preview_stack.setSpacing(12)
        self.preview_stack.addStretch(1)
        self.preview_scroll.setWidget(self.preview_container)

        preview_layout.addWidget(self.preview_scroll)
        actions_frame = QFrame(self)
        actions_frame.setObjectName("EditorOptions")
        actions_frame.setMaximumWidth(260)
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(12, 12, 12, 12)
        actions_layout.setSpacing(8)

        actions_label = QLabel("ACTIONS")
        actions_label.setObjectName("SectionLabel")
        actions_layout.addWidget(actions_label)

        self.split_btn = QPushButton("Extract Pages")
        self.extract_btn = QPushButton("Extract Selection")
        self.compress_btn = QPushButton("Compress Copy")
        self.save_btn = QPushButton("Save As")
        self.save_btn.setObjectName("PrimaryButton")

        actions_layout.addWidget(self.split_btn)
        actions_layout.addWidget(self.extract_btn)
        actions_layout.addWidget(self.compress_btn)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self.save_btn)

        root.addWidget(left_panel, 2)
        root.addWidget(preview_frame, 5)
        root.addWidget(actions_frame, 3)

        self.move_up_btn.clicked.connect(self._move_up)
        self.move_down_btn.clicked.connect(self._move_down)
        self.delete_btn.clicked.connect(self._delete_page)
        self.rotate_left_btn.clicked.connect(lambda: self._rotate_page(-90))
        self.rotate_right_btn.clicked.connect(lambda: self._rotate_page(90))
        self.split_btn.clicked.connect(self._split_pages)
        self.extract_btn.clicked.connect(self._extract_pages)
        self.compress_btn.clicked.connect(self._compress_copy)
        self.save_btn.clicked.connect(self._save_as)
        self.zoom_out_btn.clicked.connect(lambda: self._adjust_zoom(0.85))
        self.zoom_in_btn.clicked.connect(lambda: self._adjust_zoom(1.15))
        self.zoom_fit_btn.clicked.connect(self._reset_zoom)

    def _mark_dirty(self) -> None:
        if not self.tab_state.dirty:
            self.tab_state.dirty = True
            self.on_dirty_change(self)

    def _refresh_pages(self, keep_row: int | None = None, keep_scroll: int | None = None) -> None:
        self.page_list.blockSignals(True)
        self.page_list.clear()
        self._clear_preview_pages()
        for idx in range(self.doc.page_count):
            item = QListWidgetItem(f"Page {idx + 1}")
            item.setData(Qt.UserRole, idx)
            item.setTextAlignment(Qt.AlignHCenter)
            item.setSizeHint(QSize(132, 180))
            try:
                pix = self.doc.load_page(idx).get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
                item.setIcon(QIcon(pixmap_from_fitz(pix)))
            except Exception:
                pass
            self.page_list.addItem(item)
            page_label = QLabel()
            page_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            page_label.setObjectName("PdfPage")
            self.preview_stack.insertWidget(self.preview_stack.count() - 1, page_label)
            self._page_labels.append(page_label)
        self.page_list.blockSignals(False)
        if self.doc.page_count:
            target = 0
            if keep_row is not None and 0 <= keep_row < self.doc.page_count:
                target = keep_row
            self.page_list.setCurrentRow(target)
        self._render_all_pages()
        if keep_scroll is not None:
            self.preview_scroll.verticalScrollBar().setValue(keep_scroll)

    def _render_preview(self, row: int) -> None:
        if row < 0 or row >= len(self._page_labels):
            return
        widget = self._page_labels[row]
        self.preview_scroll.ensureWidgetVisible(widget)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_all_pages()

    def _clear_preview_pages(self) -> None:
        for label in self._page_labels:
            label.deleteLater()
        self._page_labels = []

    def _fit_scale(self) -> float:
        if self.doc.page_count == 0:
            return 1.0
        try:
            page = self.doc.load_page(0)
            width = page.rect.width or 1.0
            viewport_width = max(1, self.preview_scroll.viewport().width() - 16)
            return max(0.1, viewport_width / width)
        except Exception:
            return 1.0

    def _render_all_pages(self) -> None:
        if not self._page_labels:
            return
        scale = self._fit_scale() * self._zoom
        percent = int(self._zoom * 100)
        self.zoom_label.setText(f"{percent}%")
        for idx, label in enumerate(self._page_labels):
            try:
                page = self.doc.load_page(idx)
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                label.setPixmap(pixmap_from_fitz(pix))
            except Exception:
                label.setText("Unable to render page.")

    def _adjust_zoom(self, factor: float) -> None:
        self._zoom = max(0.25, min(4.0, self._zoom * factor))
        self._render_all_pages()

    def _reset_zoom(self) -> None:
        self._zoom = 1.0
        self._render_all_pages()

    def _selected_pages(self) -> list[int]:
        rows = [self.page_list.row(item) for item in self.page_list.selectedItems()]
        if not rows and self.page_list.currentRow() >= 0:
            rows = [self.page_list.currentRow()]
        return sorted(set(rows))

    def _move_up(self) -> None:
        row = self.page_list.currentRow()
        if row <= 0:
            return
        self.doc.move_page(row, row - 1)
        self._mark_dirty()
        self._refresh_pages()
        self.page_list.setCurrentRow(row - 1)

    def _move_down(self) -> None:
        row = self.page_list.currentRow()
        if row < 0 or row >= self.doc.page_count - 1:
            return
        self.doc.move_page(row, row + 1)
        self._mark_dirty()
        self._refresh_pages()
        self.page_list.setCurrentRow(row + 1)

    def _delete_page(self) -> None:
        pages = self._selected_pages()
        if not pages:
            return
        confirm = QMessageBox.question(self, "Delete Pages", f"Delete {len(pages)} page(s)?")
        if confirm != QMessageBox.Yes:
            return
        for idx in sorted(pages, reverse=True):
            self.doc.delete_page(idx)
        self._mark_dirty()
        self._refresh_pages()

    def _rotate_page(self, delta: int) -> None:
        row = self.page_list.currentRow()
        if row < 0:
            return
        page = self.doc.load_page(row)
        page.set_rotation((page.rotation + delta) % 360)
        self._mark_dirty()
        scroll = self.preview_scroll.verticalScrollBar().value()
        self._refresh_pages(keep_row=row, keep_scroll=scroll)


    def _split_pages(self) -> None:
        if self.doc.page_count == 0:
            return
        text, ok = QInputDialog.getText(
            self,
            "Split Pages",
            "Optional page ranges (e.g., 1-3,5). Leave blank to split all pages:",
        )
        if not ok:
            return
        folder = QFileDialog.getExistingDirectory(
            self,
            "Split Pages Into Folder",
            self.state.last_folder_path,
        )
        if not folder:
            return
        base = self.tab_state.path.stem
        ranges = parse_range_groups(text.strip(), self.doc.page_count) if text.strip() else []
        if text.strip() and not ranges:
            QMessageBox.warning(self, "Split Pages", "No valid ranges found.")
            return
        if ranges:
            for pages in ranges:
                out = fitz.open()
                for idx in pages:
                    out.insert_pdf(self.doc, from_page=idx, to_page=idx)
                start = pages[0] + 1
                end = pages[-1] + 1
                label = f"{start}" if start == end else f"{start}-{end}"
                out.save(str(Path(folder) / f"{base}_p{label}.pdf"))
                out.close()
        else:
            for idx in range(self.doc.page_count):
                out = fitz.open()
                out.insert_pdf(self.doc, from_page=idx, to_page=idx)
                out.save(str(Path(folder) / f"{base}_p{idx + 1}.pdf"))
                out.close()
        self.state.last_folder_path = folder
        QMessageBox.information(self, "Split Complete", "Split PDFs saved to the selected folder.")

    def _extract_pages(self) -> None:
        pages = self._selected_pages()
        if not pages:
            QMessageBox.information(self, "Extract Pages", "Select one or more pages to extract.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Extracted PDF",
            str(Path(self.state.last_folder_path) / f"{self.tab_state.path.stem}_extract.pdf"),
            "PDF Files (*.pdf)",
        )
        if not path:
            return
        out = fitz.open()
        for idx in pages:
            out.insert_pdf(self.doc, from_page=idx, to_page=idx)
        out.save(path)
        out.close()
        self.state.last_folder_path = str(Path(path).parent)
        QMessageBox.information(self, "Extract Complete", "Extracted PDF saved.")

    def _compress_copy(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Compressed PDF",
            str(Path(self.state.last_folder_path) / f"{self.tab_state.path.stem}_compressed.pdf"),
            "PDF Files (*.pdf)",
        )
        if not path:
            return
        self.doc.save(path, garbage=4, deflate=True, clean=True)
        self.state.last_folder_path = str(Path(path).parent)
        QMessageBox.information(self, "Compression Complete", "Compressed PDF saved.")

    def _save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF As",
            str(Path(self.state.last_folder_path) / f"{self.tab_state.path.stem}_edited.pdf"),
            "PDF Files (*.pdf)",
        )
        if not path:
            return
        self.doc.save(path)
        self.tab_state.path = Path(path)
        self.state.last_folder_path = str(Path(path).parent)
        self.tab_state.dirty = False
        self.on_dirty_change(self)


class PdfEditorPage(QWidget):
    def __init__(self, state: AppState, on_theme_change, on_navigate) -> None:
        super().__init__()
        self.state = state
        self.on_theme_change = on_theme_change
        self.on_navigate = on_navigate

        self._build_ui()
        self._restore_open_files()

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

        header_row = QHBoxLayout()
        title = QLabel("PDF Editor")
        title.setObjectName("PreviewTitle")
        header_row.addWidget(title)
        header_row.addStretch(1)
        self.close_btn = QPushButton("Close PDF")
        self.close_btn.clicked.connect(self._close_current)
        header_row.addWidget(self.close_btn)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._sync_tab_title)
        self.tabs.tabBar().hide()

        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.addStretch(1)
        empty_center = QHBoxLayout()
        empty_center.addStretch(1)
        empty_controls = QVBoxLayout()
        empty_controls.setSpacing(12)
        empty_controls.setAlignment(Qt.AlignCenter)
        empty_title = QLabel("Open a PDF to get started")
        empty_title.setObjectName("PreviewTitle")
        self.empty_open_btn = QPushButton("Open PDFs")
        self.empty_open_btn.setObjectName("PrimaryButton")
        self.empty_open_btn.clicked.connect(self._open_pdfs)
        self.empty_merge_btn = QPushButton("Merge PDFs")
        self.empty_merge_btn.clicked.connect(self._merge_pdfs_home)
        empty_controls.addWidget(empty_title)
        empty_controls.addWidget(self.empty_open_btn)
        empty_controls.addWidget(self.empty_merge_btn)
        empty_center.addLayout(empty_controls)
        empty_center.addStretch(1)
        empty_layout.addLayout(empty_center)
        empty_layout.addStretch(1)

        self.content_stack = QStackedLayout()
        self.content_stack.addWidget(self.empty_state)
        self.content_stack.addWidget(self.tabs)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addLayout(header_row)
        card_layout.addLayout(self.content_stack)
        root_layout.addWidget(card)

        self.set_theme(self.state.theme)
        self._sync_empty_state()

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

    def update_state(self, state: AppState) -> None:
        state.pdf_open_files = self._current_paths()
        if self.tabs.count() == 0:
            return
        current = self._current_tab()
        if current is not None:
            state.last_folder_path = str(current.tab_state.path.parent)

    def _open_pdfs(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open PDFs",
            self.state.last_folder_path,
            "PDF Files (*.pdf)",
        )
        if not paths:
            return
        self.state.last_folder_path = str(Path(paths[0]).parent)
        for path in paths:
            self._add_tab(Path(path))
        self._sync_empty_state()

    def _merge_pdfs_home(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Merge PDFs or Images",
            self.state.last_folder_path,
            "PDF & Images (*.pdf *.png *.jpg *.jpeg *.bmp *.gif *.webp)",
        )
        if len(paths) < 2:
            return
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Merged PDF",
            str(Path(self.state.last_folder_path) / "merged.pdf"),
            "PDF Files (*.pdf)",
        )
        if not out_path:
            return
        merged = fitz.open()
        for path in paths:
            try:
                src = Path(path)
                if src.suffix.lower() == ".pdf":
                    other = fitz.open(path)
                    merged.insert_pdf(other)
                    other.close()
                else:
                    img_doc = fitz.open()
                    pix = fitz.Pixmap(path)
                    rect = fitz.Rect(0, 0, pix.width, pix.height)
                    page = img_doc.new_page(width=rect.width, height=rect.height)
                    page.insert_image(rect, filename=path)
                    merged.insert_pdf(img_doc)
                    img_doc.close()
            except Exception:
                QMessageBox.warning(self, "Merge Failed", f"Could not merge {path}.")
        merged.save(out_path)
        merged.close()
        self.state.last_folder_path = str(Path(out_path).parent)
        self._add_tab(Path(out_path))
        self._sync_empty_state()

    def _add_tab(self, path: Path) -> None:
        tab = PdfTab(path, self.state, self._on_tab_dirty_change)
        index = self.tabs.addTab(tab, self._tab_title(tab))
        self.tabs.setCurrentIndex(index)
        self._sync_empty_state()

    def _tab_title(self, tab: PdfTab) -> str:
        name = tab.tab_state.path.name
        return f"{name} *" if tab.tab_state.dirty else name

    def _on_tab_dirty_change(self, tab: PdfTab) -> None:
        index = self.tabs.indexOf(tab)
        if index >= 0:
            self.tabs.setTabText(index, self._tab_title(tab))

    def _current_tab(self) -> PdfTab | None:
        widget = self.tabs.currentWidget()
        if isinstance(widget, PdfTab):
            return widget
        return None

    def _sync_tab_title(self, index: int) -> None:
        if index < 0:
            return
        tab = self.tabs.widget(index)
        if isinstance(tab, PdfTab):
            self.tabs.setTabText(index, self._tab_title(tab))

    def _close_tab(self, index: int) -> None:
        tab = self.tabs.widget(index)
        if not isinstance(tab, PdfTab):
            return
        if tab.tab_state.dirty:
            choice = QMessageBox.question(
                self,
                "Unsaved Changes",
                "This PDF has unsaved changes. Close anyway?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if choice != QMessageBox.Yes:
                return
        try:
            tab.doc.close()
        except Exception:
            pass
        self.tabs.removeTab(index)
        self._sync_empty_state()

    def _sync_empty_state(self) -> None:
        if self.tabs.count() == 0:
            self.content_stack.setCurrentWidget(self.empty_state)
            self.close_btn.setEnabled(False)
        else:
            self.content_stack.setCurrentWidget(self.tabs)
            self.close_btn.setEnabled(True)

    def _close_current(self) -> None:
        index = self.tabs.currentIndex()
        if index >= 0:
            self._close_tab(index)

    def _current_paths(self) -> list[str]:
        paths: list[str] = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, PdfTab):
                paths.append(str(tab.tab_state.path))
        return paths

    def _restore_open_files(self) -> None:
        restored = False
        for path in self.state.pdf_open_files:
            if Path(path).exists():
                self._add_tab(Path(path))
                restored = True
        if restored:
            self._sync_empty_state()
