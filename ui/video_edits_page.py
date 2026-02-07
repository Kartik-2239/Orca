from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QSize, QUrl, QProcess
from PySide6.QtGui import QIcon, QPainter, QPixmap, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFileDialog,
    QPushButton,
    QTabWidget,
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


class VideoEditsPage(QWidget):
    def __init__(self, state: AppState, on_theme_change, on_navigate) -> None:
        super().__init__()
        self.state = state
        self.on_theme_change = on_theme_change
        self.on_navigate = on_navigate
        self._video_path: Path | None = None
        self._last_output_path: Path | None = None

        self._build_ui()
        self.set_theme(state.theme)

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_process_output)
        self.process.errorOccurred.connect(self._on_process_error)
        self.process.finished.connect(self._on_process_finished)

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
        header_title = QLabel("Video Tools")
        header_title.setObjectName("PreviewTitle")
        header_subtitle = QLabel("Fast ffmpeg conversions.")
        header_subtitle.setObjectName("SubtitleLabel")
        self.load_video_btn = QPushButton("Load Video")
        self.load_video_btn.setObjectName("PrimaryButton")
        self.load_video_btn.clicked.connect(self._open_video)
        self.close_video_btn = QPushButton("Close")
        self.close_video_btn.setObjectName("ToolButton")
        self.close_video_btn.clicked.connect(self._close_video)
        self.close_video_btn.setVisible(False)
        header_row.addWidget(header_title)
        header_row.addStretch(1)
        header_row.addWidget(header_subtitle)
        header_row.addWidget(self.load_video_btn)
        header_row.addWidget(self.close_video_btn)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        preview_card = QWidget()
        preview_card.setObjectName("PreviewCard")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(10)

        preview_frame = QFrame()
        preview_frame.setObjectName("EditorCanvas")
        preview_frame.setMinimumSize(320, 220)
        preview_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_frame_layout = QVBoxLayout(preview_frame)
        preview_frame_layout.setContentsMargins(8, 8, 8, 8)

        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_frame_layout.addWidget(self.video_widget)

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.6)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        self.preview_label = QLabel("Load a video to preview output.")
        self.preview_label.setObjectName("PreviewLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)

        preview_layout.addWidget(preview_frame, 1)
        preview_layout.addWidget(self.preview_label)

        settings_panel = QFrame()
        settings_panel.setObjectName("EditorPanel")
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(16, 16, 16, 16)
        settings_layout.setSpacing(12)

        self.tabs = QTabWidget()

        format_tab = QWidget()
        format_layout = QVBoxLayout(format_tab)
        format_layout.setSpacing(10)
        format_title = QLabel("Format")
        format_title.setObjectName("SectionLabel")
        format_layout.addWidget(format_title)
        format_hint = QLabel("Change container without re-encoding (fast).")
        format_hint.setObjectName("SubtitleLabel")
        format_layout.addWidget(format_hint)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mov", "mkv", "webm"])
        format_layout.addWidget(self.format_combo)

        self.remux_btn = QPushButton("Remux")
        self.remux_btn.setObjectName("PrimaryButton")
        self.remux_btn.clicked.connect(self._run_remux)
        format_layout.addWidget(self.remux_btn)
        format_layout.addStretch(1)

        resize_tab = QWidget()
        resize_layout = QVBoxLayout(resize_tab)
        resize_layout.setSpacing(10)
        resize_title = QLabel("Resolution")
        resize_title.setObjectName("SectionLabel")
        resize_layout.addWidget(resize_title)
        resize_hint = QLabel("Resize with fast preset.")
        resize_hint.setObjectName("SubtitleLabel")
        resize_layout.addWidget(resize_hint)

        self.resize_combo = QComboBox()
        self.resize_combo.addItems(["Keep", "1920x1080", "1280x720", "854x480", "640x360"])
        resize_layout.addWidget(self.resize_combo)

        self.resize_btn = QPushButton("Resize")
        self.resize_btn.setObjectName("PrimaryButton")
        self.resize_btn.clicked.connect(self._run_resize)
        resize_layout.addWidget(self.resize_btn)
        resize_layout.addStretch(1)

        compress_tab = QWidget()
        compress_layout = QVBoxLayout(compress_tab)
        compress_layout.setSpacing(10)
        compress_title = QLabel("Compress")
        compress_title.setObjectName("SectionLabel")
        compress_layout.addWidget(compress_title)
        compress_hint = QLabel("Lower file size with CRF.")
        compress_hint.setObjectName("SubtitleLabel")
        compress_layout.addWidget(compress_hint)

        self.crf_input = QLineEdit()
        self.crf_input.setPlaceholderText("CRF (18-30)")
        self.crf_input.setText("23")
        compress_layout.addWidget(self.crf_input)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["veryfast", "faster", "fast", "medium"])
        compress_layout.addWidget(self.preset_combo)

        self.compress_btn = QPushButton("Compress")
        self.compress_btn.setObjectName("PrimaryButton")
        self.compress_btn.clicked.connect(self._run_compress)
        compress_layout.addWidget(self.compress_btn)
        compress_layout.addStretch(1)

        self.tabs.addTab(format_tab, "Format")
        self.tabs.addTab(resize_tab, "Resolution")
        self.tabs.addTab(compress_tab, "Compress")

        settings_layout.addWidget(self.tabs)

        self.status = QLabel("")
        self.status.setObjectName("StatusLabel")
        self.status.setVisible(False)
        settings_layout.addWidget(self.status)

        top_row.addWidget(preview_card, 3)
        top_row.addWidget(settings_panel, 2)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addLayout(header_row)
        card_layout.addLayout(top_row, 1)

        root_layout.addWidget(card)

    def set_theme(self, theme: str) -> None:
        return

    def _open_video(self) -> None:
        start_dir = self.state.last_folder_path or ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            start_dir,
            "Video Files (*.mp4 *.mov *.mkv *.webm *.avi);;All Files (*)",
        )
        if not path:
            return
        self.state.last_folder_path = str(Path(path).parent)
        self._video_path = Path(path)
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.preview_label.setText("")
        self.close_video_btn.setVisible(True)

    def _close_video(self) -> None:
        self.player.stop()
        self.player.setSource(QUrl())
        self._video_path = None
        self.preview_label.setText("Load a video to preview output.")
        self.close_video_btn.setVisible(False)

    def _run_remux(self) -> None:
        if not self._video_path:
            self._set_status("Load a video first.", error=True)
            return
        ext = self.format_combo.currentText().strip(".")
        output = self._ask_output_path(ext)
        if not output:
            return
        args = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(self._video_path),
            "-map",
            "0",
            "-c",
            "copy",
            str(output),
        ]
        self._run_ffmpeg(args, output)

    def _run_resize(self) -> None:
        if not self._video_path:
            self._set_status("Load a video first.", error=True)
            return
        target = self.resize_combo.currentText()
        if target == "Keep":
            self._set_status("Select a resolution.", error=True)
            return
        output = self._ask_output_path("mp4")
        if not output:
            return
        width, height = target.split("x", 1)
        args = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(self._video_path),
            "-vf",
            f"scale={width}:{height}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output),
        ]
        self._run_ffmpeg(args, output)

    def _run_compress(self) -> None:
        if not self._video_path:
            self._set_status("Load a video first.", error=True)
            return
        crf = self._parse_int(self.crf_input.text(), default=23)
        preset = self.preset_combo.currentText()
        output = self._ask_output_path("mp4")
        if not output:
            return
        args = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(self._video_path),
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            str(crf),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output),
        ]
        self._run_ffmpeg(args, output)

    def _ask_output_path(self, extension: str) -> Path | None:
        if not self._video_path:
            return None
        base_dir = self.state.last_folder_path or str(self._video_path.parent)
        suffix = extension if extension.startswith(".") else f".{extension}"
        default_name = f"{self._video_path.stem}_out{suffix}"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Output",
            str(Path(base_dir) / default_name),
            f"{extension.upper()} Files (*{suffix});;All Files (*)",
        )
        if not path:
            return None
        self.state.last_folder_path = str(Path(path).parent)
        self._last_output_path = Path(path)
        return Path(path)

    def _run_ffmpeg(self, args: list[str], output: Path) -> None:
        if not shutil.which("ffmpeg"):
            self._set_status("ffmpeg is not available on PATH.", error=True)
            return
        if self.process.state() != QProcess.NotRunning:
            self._set_status("ffmpeg is already running.", error=True)
            return
        self._set_controls_enabled(False)
        self._set_status("Running ffmpeg...", error=False)
        self.process.start(args[0], args[1:])

    def _on_process_output(self) -> None:
        data = self.process.readAllStandardOutput().data().decode(errors="ignore").strip()
        if data:
            self._set_status("Working...", error=False)

    def _on_process_error(self) -> None:
        self._set_controls_enabled(True)
        self._set_status("Failed to start ffmpeg.", error=True)

    def _on_process_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._set_controls_enabled(True)
        if exit_code == 0:
            self._set_status("Done.", error=False)
            if self._last_output_path and self._last_output_path.exists():
                self.player.setSource(QUrl.fromLocalFile(str(self._last_output_path)))
                self.player.play()
        else:
            self._set_status("ffmpeg failed. Check input file.", error=True)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.remux_btn.setEnabled(enabled)
        self.resize_btn.setEnabled(enabled)
        self.compress_btn.setEnabled(enabled)
        self.load_video_btn.setEnabled(enabled)
        self.close_video_btn.setEnabled(enabled)

    def _set_status(self, message: str, error: bool) -> None:
        self.status.setText(message)
        self.status.setVisible(True)
        color = "#b00020" if error else "#b25574"
        self.status.setStyleSheet(f"color: {color};")

    def _parse_int(self, value: str, default: int) -> int:
        try:
            return int(value.strip())
        except ValueError:
            return default
