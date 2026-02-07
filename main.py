import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from services.state import AppState, ensure_storage, load_state, save_state
from ui.download_page import DownloadPage
from ui.home_page import HomePage
from ui.image_batch_page import ImageBatchPage
from ui.image_downloader_page import ImageDownloaderPage
from ui.image_editor_page import ImageEditorPage
from ui.pdf_editor_page import PdfEditorPage
from ui.video_edits_page import VideoEditsPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Orca")
        self.setMinimumSize(860, 560)

        base_dir = Path(__file__).parent
        default_downloads = base_dir / "downloads"
        default_downloads.mkdir(parents=True, exist_ok=True)

        self.state_path = Path.home() / ".local" / "state" / "orca" / "state.json"
        self.storage_marker = Path.home() / "Library" / "Application Support" / "orca" / ".storage"
        ensure_storage(self.storage_marker, self.state_path, str(default_downloads))
        self.state: AppState = load_state(self.state_path, str(default_downloads))

        if self.state.window_size and len(self.state.window_size) == 2:
            try:
                self.resize(int(self.state.window_size[0]), int(self.state.window_size[1]))
            except Exception:
                pass
        if self.state.window_pos and len(self.state.window_pos) == 2:
            try:
                self.move(int(self.state.window_pos[0]), int(self.state.window_pos[1]))
            except Exception:
                pass

        self.stack = QStackedWidget(self)

        self.home_page = HomePage(self.state, self.set_theme, self.show_page)
        self.download_page = DownloadPage(self.state, self.set_theme, self.show_page)
        self.image_editor_page = ImageEditorPage(self.state, self.set_theme, self.show_page)
        self.pdf_editor_page = PdfEditorPage(self.state, self.set_theme, self.show_page)
        self.image_batch_page = ImageBatchPage(self.state, self.set_theme, self.show_page)
        self.image_downloader_page = ImageDownloaderPage(self.state, self.set_theme, self.show_page)
        self.video_edits_page = VideoEditsPage(self.state, self.set_theme, self.show_page)

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.download_page)
        self.stack.addWidget(self.image_editor_page)
        self.stack.addWidget(self.pdf_editor_page)
        self.stack.addWidget(self.image_batch_page)
        self.stack.addWidget(self.image_downloader_page)
        self.stack.addWidget(self.video_edits_page)

        self.setCentralWidget(self.stack)
        self.apply_theme(self.state.theme)
        self.show_page(self.state.last_page)

    def show_page(self, page: str) -> None:
        page = page or "home"
        if page == "download":
            self.stack.setCurrentWidget(self.download_page)
        elif page == "image_editor":
            self.stack.setCurrentWidget(self.image_editor_page)
        elif page == "pdf_editor":
            self.stack.setCurrentWidget(self.pdf_editor_page)
        elif page == "image_batch":
            self.stack.setCurrentWidget(self.image_batch_page)
        elif page == "image_downloader":
            self.stack.setCurrentWidget(self.image_downloader_page)
        elif page == "video_edits":
            self.stack.setCurrentWidget(self.video_edits_page)
        else:
            page = "home"
            self.stack.setCurrentWidget(self.home_page)
        self.state.last_page = page

    def set_theme(self, theme: str) -> None:
        self.state.theme = theme
        self.apply_theme(theme)
        self.home_page.set_theme(theme)
        self.download_page.set_theme(theme)
        self.pdf_editor_page.set_theme(theme)
        self.image_batch_page.set_theme(theme)
        self.image_downloader_page.set_theme(theme)
        self.video_edits_page.set_theme(theme)

    def apply_theme(self, theme: str) -> None:
        if theme == "Dark":
            self.setStyleSheet(
                """
                QMainWindow { background: #0f0b0d; }
                QWidget#MainCard {
                    background: #1c141a;
                    border: 1px solid #3b2730;
                    border-radius: 0px;
                }
                QWidget#LeftPanel { background: #1c141a; }
                QWidget#RightPanel { background: #1c141a; }
                QLabel { color: #e9e1e6; }
                QLabel#HeaderTitle { font-size: 18px; font-weight: 700; }
                QLabel#SubtitleLabel { color: #b690a5; }
                QLabel#PreviewTitle { font-size: 14px; font-weight: 700; }
                QLabel#PreviewLabel { color: #b690a5; font-size: 11px; }
                QLabel#TimeLabel { color: #b690a5; font-size: 11px; }
                QLabel#StatusLabel { color: #f7c6de; font-size: 11px; }
                QLabel#TrackTitle { color: #f0e7ed; font-size: 16px; font-weight: 700; }
                QLabel#TrackSubtitle { color: #b690a5; font-size: 12px; }
                QToolButton#ThemeToggle {
                    background: #26161f;
                    border: 1px solid #3b2730;
                    border-radius: 12px;
                    padding: 4px;
                    min-width: 26px;
                    min-height: 26px;
                }
                QToolButton#ActionButton {
                    background: #26161f;
                    border: 1px solid #3b2730;
                    border-radius: 16px;
                    color: #e9e1e6;
                    padding: 10px 14px;
                    min-width: 120px;
                    min-height: 84px;
                    font-weight: 600;
                }
                QToolButton#ThemeToggle:checked {
                    background: #2a1b22;
                    border: 1px solid #3b2730;
                }
                QPushButton#NavButton {
                    background: transparent;
                    border: none;
                    color: #e9e1e6;
                    padding: 0px 6px;
                }
                QLabel#SectionLabel {
                    color: #b25574;
                    font-weight: 700;
                    font-size: 11px;
                }
                QLabel#FieldLabel {
                    color: #8c7484;
                    font-weight: 600;
                    font-size: 11px;
                }
                QLabel#IconBadge {
                    background: #2a1b22;
                    color: #d27fa0;
                    border-radius: 14px;
                    min-width: 36px;
                    min-height: 36px;
                    font-weight: 700;
                }
                QFrame#Divider { background: #1a0f14; }
                QLineEdit, QComboBox, QSpinBox {
                    background: #160e13;
                    color: #e9e1e6;
                    min-height: 46px;
                    padding: 0px 7px;
                    border: 1px solid #3b2730;
                    border-radius: 14px;
                    font-size: 13px;
                }
                QComboBox::drop-down { width: 18px; border: 0px; background: transparent; }
                QComboBox::down-arrow { width: 10px; height: 10px; }
                QComboBox QAbstractItemView { background: #160e13; color: #e9e1e6; }
                QCheckBox { color: #e9e1e6; }
                QPushButton {
                    background: #26161f;
                    color: #e9e1e6;
                    padding: 8px 16px;
                    border-radius: 14px;
                    font-weight: 600;
                    border: 1px solid #3b2730;
                }
                QPushButton#PrimaryButton {
                    background: #5b2138;
                    color: #f5e9ef;
                    border: none;
                    min-height: 43px;
                    font-size: 14px;
                    padding: 6px 12px;
                }
                QPushButton#FolderButton { min-height: 46px; max-height: 46px; padding: 0px 14px; }
                QWidget#OptionsCard {
                    background: #1c141a;
                    border: 1px solid #3b2730;
                    border-radius: 18px;
                }
                QFrame#EditorCanvas {
                    background: #160e13;
                    border: 1px solid #3b2730;
                    border-radius: 18px;
                }
                QFrame#PdfPreview {
                    background: transparent;
                    border: 1px solid #3b2730;
                    border-radius: 18px;
                }
                QFrame#EditorOptions {
                    background: #1c141a;
                    border: 1px solid #3b2730;
                    border-radius: 16px;
                }
                QFrame#EditorOptions QPushButton { color: #b690a5; }
                QFrame#EditorPanel {
                    background: #1c141a;
                    border: none;
                    border-radius: 16px;
                }
                QTabWidget::pane { border: 0px; background: transparent; }
                QFrame#EditorPanel QPushButton {
                    min-height: 32px;
                    padding: 4px 10px;
                }
                QFrame#EditorPanel QPushButton#PrimaryButton {
                    min-height: 36px;
                }
                QFrame#EditorPanel QPushButton#ToolButton {
                    min-height: 30px;
                    padding: 4px 8px;
                }
                QFrame#EditorPanel QLineEdit,
                QFrame#EditorPanel QComboBox,
                QFrame#EditorPanel QSpinBox {
                    min-height: 36px;
                }
                QFrame#LayerRow {
                    background: #22161f;
                    border: 1px solid #3b2730;
                    border-radius: 12px;
                }
                QFrame#LayerRow[active="true"] {
                    border: 1px solid #5b2138;
                    background: #2a1b22;
                }
                QFrame#LayerRow[hidden="true"] {
                    background: #1a1117;
                    border: 1px solid #2a1b22;
                }
                QLabel#LayerBadge {
                    background: #2a1b22;
                    color: #f7c6de;
                    border-radius: 10px;
                    min-width: 34px;
                    min-height: 28px;
                    font-weight: 700;
                    qproperty-alignment: 'AlignCenter';
                }
                QToolButton#LayerEye,
                QToolButton#LayerLock,
                QToolButton#LayerAdd {
                    background: #160e13;
                    border: 1px solid #3b2730;
                    border-radius: 8px;
                    min-width: 24px;
                    min-height: 24px;
                    padding: 0px;
                }
                QToolButton#LockRatioButton {
                    background: #160e13;
                    border: 1px solid #3b2730;
                    border-radius: 10px;
                    min-width: 28px;
                    min-height: 28px;
                    padding: 0px;
                }
                QToolButton#LayerArrow {
                    background: #160e13;
                    border: 1px solid #3b2730;
                    border-radius: 8px;
                    min-width: 22px;
                    min-height: 22px;
                    padding: 0px;
                }
                QToolButton#ToolButton {
                    background: #160e13;
                    border: 1px solid #3b2730;
                    border-radius: 10px;
                    min-width: 32px;
                    min-height: 28px;
                    padding: 0px 8px;
                    color: #b690a5;
                }
                QScrollArea#EditorScroll { background: transparent; border: none; }
                QScrollArea#EditorScroll QWidget { background: transparent; }
                QScrollArea#LayersScroll { background: transparent; border: none; }
                QScrollArea#LayersScroll QWidget { background: transparent; }
                QListWidget#PdfPageList { background: transparent; border: none; }
                QListWidget#PdfPageList::item { color: #b690a5; }
                QListWidget#PdfPageList::item:selected {
                    background: #2a1b22;
                    border: 1px solid #5b2138;
                    border-radius: 10px;
                }
                QScrollBar:vertical {
                    background: transparent;
                    width: 8px;
                    margin: 2px 0 2px 0;
                }
                QScrollBar::handle:vertical {
                    background: #3b2730;
                    border-radius: 4px;
                    min-height: 24px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #5b2138;
                }
                QScrollBar::add-line:vertical,
                QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical,
                QScrollBar::sub-page:vertical {
                    background: transparent;
                }
                QScrollBar:horizontal {
                    background: transparent;
                    height: 8px;
                    margin: 0 2px 0 2px;
                }
                QScrollBar::handle:horizontal {
                    background: #3b2730;
                    border-radius: 4px;
                    min-width: 24px;
                }
                QScrollBar::handle:horizontal:hover {
                    background: #5b2138;
                }
                QScrollBar::add-line:horizontal,
                QScrollBar::sub-line:horizontal {
                    width: 0px;
                }
                QScrollBar::add-page:horizontal,
                QScrollBar::sub-page:horizontal {
                    background: transparent;
                }
                QPushButton#ToolButton {
                    background: #160e13;
                    border: 1px solid #3b2730;
                    border-radius: 12px;
                    padding: 6px 10px;
                    font-weight: 600;
                }
                QPushButton#ToolButton:checked {
                    background: #2a1b22;
                    border: 1px solid #5b2138;
                    color: #f7c6de;
                }
                QGraphicsView#CanvasView { background: transparent; border: none; }
                QFrame#ArtworkFrame {
                    background: #160e13;
                    border: 1px solid #3b2730;
                    border-radius: 22px;
                }
                QListWidget#TrackList {
                    background: #160e13;
                    border: 1px solid #3b2730;
                    border-radius: 16px;
                    padding: 6px;
                }
                QListWidget#TrackList::item {
                    padding: 8px 10px;
                    border-radius: 10px;
                    color: #e9e1e6;
                }
                QListWidget#TrackList::item:selected {
                    background: #2a1b22;
                    color: #f7c6de;
                }
                QWidget#PreviewCard {
                    background: #1c141a;
                    border: 1px solid #3b2730;
                    border-radius: 26px;
                }
                QWidget#ControlsCard {
                    background: #1c141a;
                    border: 1px solid #3b2730;
                    border-radius: 18px;
                }
                QWidget#PhoneFrame {
                    background: transparent;
                    border-radius: 24px;
                }
                QPushButton#ControlButton {
                    background: #160e13;
                    color: #e9e1e6;
                    border: 1px solid #3b2730;
                    border-radius: 12px;
                    min-height: 36px;
                    padding: 6px 12px;
                }
                QSlider#SeekSlider::groove:horizontal {
                    height: 6px;
                    background: #2a1b22;
                    border-radius: 3px;
                }
                QSlider#SeekSlider::handle:horizontal {
                    width: 14px;
                    margin: -6px 0;
                    border-radius: 7px;
                    background: #b25574;
                }
                QSlider#VolumeSlider::groove:horizontal {
                    height: 4px;
                    background: #2a1b22;
                    border-radius: 2px;
                }
                QSlider#VolumeSlider::handle:horizontal {
                    width: 12px;
                    margin: -5px 0;
                    border-radius: 6px;
                    background: #b25574;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QMainWindow { background: #fdeff4; }
                QWidget#MainCard {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 0px;
                }
                QWidget#LeftPanel { background: #ffffff; }
                QWidget#RightPanel { background: #ffffff; }
                QLabel { color: #1f2430; }
                QLabel#HeaderTitle { font-size: 18px; font-weight: 700; }
                QLabel#SubtitleLabel { color: #8a8f9c; }
                QLabel#PreviewTitle { font-size: 14px; font-weight: 700; }
                QLabel#PreviewLabel { color: #7c8190; font-size: 11px; }
                QLabel#TimeLabel { color: #8a8f9c; font-size: 11px; }
                QLabel#StatusLabel { color: #d14c7a; font-size: 11px; }
                QLabel#TrackTitle { color: #1f2430; font-size: 16px; font-weight: 700; }
                QLabel#TrackSubtitle { color: #8a8f9c; font-size: 12px; }
                QToolButton#ThemeToggle {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 12px;
                    padding: 4px;
                    min-width: 26px;
                    min-height: 26px;
                }
                QToolButton#ActionButton {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 16px;
                    color: #1f2430;
                    padding: 10px 14px;
                    min-width: 120px;
                    min-height: 84px;
                    font-weight: 600;
                }
                QToolButton#ThemeToggle:checked {
                    background: #ffe1ef;
                    border: 1px solid #f1d7e6;
                }
                QPushButton#NavButton {
                    background: transparent;
                    border: none;
                    color: #1f2430;
                    padding: 0px 6px;
                }
                QLabel#SectionLabel {
                    color: #f05aa6;
                    font-weight: 700;
                    font-size: 11px;
                }
                QLabel#FieldLabel {
                    color: #a0a4b2;
                    font-weight: 600;
                    font-size: 11px;
                }
                QLabel#IconBadge {
                    background: #ffe1ef;
                    color: #f01d85;
                    border-radius: 14px;
                    min-width: 36px;
                    min-height: 36px;
                    font-weight: 700;
                }
                QFrame#Divider { background: #f1d7e6; }
                QLineEdit, QComboBox, QSpinBox {
                    background: #ffffff;
                    color: #1f2430;
                    min-height: 46px;
                    padding: 0px 7px;
                    border: 1px solid #f1d7e6;
                    border-radius: 14px;
                    font-size: 13px;
                }
                QComboBox::drop-down { width: 18px; border: 0px; background: transparent; }
                QComboBox::down-arrow { width: 10px; height: 10px; }
                QComboBox QAbstractItemView { background: #ffffff; color: #1f2430; }
                QCheckBox { color: #1f2430; }
                QPushButton {
                    background: #f6eff6;
                    color: #1f2430;
                    padding: 8px 16px;
                    border-radius: 14px;
                    font-weight: 600;
                    border: 1px solid #f1d7e6;
                }
                QPushButton#PrimaryButton {
                    background: #f01d85;
                    color: #ffffff;
                    border: none;
                    min-height: 43px;
                    font-size: 14px;
                    padding: 6px 12px;
                }
                QPushButton#GhostButton {
                    background: #ffffff;
                    color: #1f2430;
                    border: 1px solid #f1d7e6;
                }
                QPushButton#FolderButton { min-height: 46px; max-height: 46px; padding: 0px 14px; }
                QWidget#OptionsCard {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 18px;
                }
                QFrame#EditorCanvas {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 18px;
                }
                QFrame#PdfPreview {
                    background: transparent;
                    border: 1px solid #f1d7e6;
                    border-radius: 18px;
                }
                QFrame#EditorOptions {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 16px;
                }
                QFrame#EditorOptions QPushButton { color: #b25574; }
                QFrame#EditorPanel {
                    background: #ffffff;
                    border: none;
                    border-radius: 16px;
                }
                QTabWidget::pane { border: 0px; background: transparent; }
                QFrame#EditorPanel QPushButton {
                    min-height: 32px;
                    padding: 4px 10px;
                }
                QFrame#EditorPanel QPushButton#PrimaryButton {
                    min-height: 36px;
                }
                QFrame#EditorPanel QPushButton#ToolButton {
                    min-height: 30px;
                    padding: 4px 8px;
                }
                QFrame#EditorPanel QLineEdit,
                QFrame#EditorPanel QComboBox,
                QFrame#EditorPanel QSpinBox {
                    min-height: 36px;
                }
                QFrame#LayerRow {
                    background: #f6eff6;
                    border: 1px solid #f1d7e6;
                    border-radius: 12px;
                }
                QFrame#LayerRow[active="true"] {
                    border: 1px solid #f58abf;
                    background: #ffe1ef;
                }
                QFrame#LayerRow[hidden="true"] {
                    background: #f9f1f6;
                    border: 1px solid #f1d7e6;
                }
                QLabel#LayerBadge {
                    background: #ffe1ef;
                    color: #f01d85;
                    border-radius: 10px;
                    min-width: 34px;
                    min-height: 28px;
                    font-weight: 700;
                    qproperty-alignment: 'AlignCenter';
                }
                QToolButton#LayerEye,
                QToolButton#LayerLock,
                QToolButton#LayerAdd {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 8px;
                    min-width: 24px;
                    min-height: 24px;
                    padding: 0px;
                }
                QToolButton#LockRatioButton {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 10px;
                    min-width: 28px;
                    min-height: 28px;
                    padding: 0px;
                }
                QToolButton#LayerArrow {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 8px;
                    min-width: 22px;
                    min-height: 22px;
                    padding: 0px;
                }
                QToolButton#ToolButton {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 10px;
                    min-width: 32px;
                    min-height: 28px;
                    padding: 0px 8px;
                    color: #b25574;
                }
                QScrollArea#EditorScroll { background: transparent; border: none; }
                QScrollArea#EditorScroll QWidget { background: transparent; }
                QScrollArea#LayersScroll { background: transparent; border: none; }
                QScrollArea#LayersScroll QWidget { background: transparent; }
                QListWidget#PdfPageList { background: transparent; border: none; }
                QListWidget#PdfPageList::item { color: #8c7484; }
                QListWidget#PdfPageList::item:selected {
                    background: #f7ddea;
                    border: 1px solid #f1d7e6;
                    border-radius: 10px;
                }
                QScrollBar:vertical {
                    background: transparent;
                    width: 8px;
                    margin: 2px 0 2px 0;
                }
                QScrollBar::handle:vertical {
                    background: #f1d7e6;
                    border-radius: 4px;
                    min-height: 24px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #f58abf;
                }
                QScrollBar::add-line:vertical,
                QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical,
                QScrollBar::sub-page:vertical {
                    background: transparent;
                }
                QScrollBar:horizontal {
                    background: transparent;
                    height: 8px;
                    margin: 0 2px 0 2px;
                }
                QScrollBar::handle:horizontal {
                    background: #f1d7e6;
                    border-radius: 4px;
                    min-width: 24px;
                }
                QScrollBar::handle:horizontal:hover {
                    background: #f58abf;
                }
                QScrollBar::add-line:horizontal,
                QScrollBar::sub-line:horizontal {
                    width: 0px;
                }
                QScrollBar::add-page:horizontal,
                QScrollBar::sub-page:horizontal {
                    background: transparent;
                }
                QPushButton#ToolButton {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 12px;
                    padding: 6px 10px;
                    font-weight: 600;
                }
                QPushButton#ToolButton:checked {
                    background: #ffe1ef;
                    border: 1px solid #f58abf;
                    color: #f01d85;
                }
                QGraphicsView#CanvasView { background: transparent; border: none; }
                QFrame#ArtworkFrame {
                    background: #fff7fb;
                    border: 1px solid #f1d7e6;
                    border-radius: 22px;
                }
                QListWidget#TrackList {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 16px;
                    padding: 6px;
                }
                QListWidget#TrackList::item {
                    padding: 8px 10px;
                    border-radius: 10px;
                    color: #1f2430;
                }
                QListWidget#TrackList::item:selected {
                    background: #ffe1ef;
                    color: #f01d85;
                }
                QWidget#PreviewCard {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 26px;
                }
                QWidget#ControlsCard {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 18px;
                }
                QWidget#PhoneFrame {
                    background: transparent;
                    border-radius: 24px;
                }
                QPushButton#ControlButton {
                    background: #ffffff;
                    color: #1f2430;
                    border: 1px solid #f1d7e6;
                    border-radius: 12px;
                    min-height: 36px;
                    padding: 6px 12px;
                }
                QSlider#SeekSlider::groove:horizontal {
                    height: 6px;
                    background: #f3e6ee;
                    border-radius: 3px;
                }
                QSlider#SeekSlider::handle:horizontal {
                    width: 14px;
                    margin: -6px 0;
                    border-radius: 7px;
                    background: #f01d85;
                }
                QSlider#VolumeSlider::groove:horizontal {
                    height: 4px;
                    background: #f3e6ee;
                    border-radius: 2px;
                }
                QSlider#VolumeSlider::handle:horizontal {
                    width: 12px;
                    margin: -5px 0;
                    border-radius: 6px;
                    background: #f58abf;
                }
                """
            )

    def closeEvent(self, event) -> None:
        self.download_page.update_state(self.state)
        self.pdf_editor_page.update_state(self.state)
        self.home_page.apply_state(self.state)
        self.state.window_size = [self.width(), self.height()]
        self.state.window_pos = [self.x(), self.y()]
        save_state(self.state_path, self.state)
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
