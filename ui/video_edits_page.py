from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QSize, QUrl, QProcess
from PySide6.QtGui import QIcon, QPainter, QPixmap, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QFileDialog,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedLayout,
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
    MAX_NAME_CHARS = 32
    VIDEO_CODECS = [
        ("H.264 (libx264)", "libx264", "mp4"),
        ("H.265 (libx265)", "libx265", "mp4"),
        ("VP9 (libvpx-vp9)", "libvpx-vp9", "webm"),
        ("AV1 (libaom-av1)", "libaom-av1", "mkv"),
    ]
    AUDIO_CODECS = [
        ("AAC", "aac"),
        ("Opus", "libopus"),
        ("Copy", "copy"),
    ]
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

        body_layout = QHBoxLayout()
        body_layout.setSpacing(18)

        left_panel = QFrame()
        left_panel.setObjectName("OptionsCard")
        left_panel.setProperty("panel", "video-left")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(14)

        source_row = QHBoxLayout()
        source_label = QLabel("Source Video")
        source_label.setObjectName("SectionLabel")
        self.ready_badge = QLabel("READY")
        self.ready_badge.setStyleSheet(
            "QLabel { color: #22c55e; background: rgba(34, 197, 94, 0.12);"
            " padding: 2px 8px; border-radius: 6px; font-size: 10px; font-weight: 700; }"
        )
        source_row.addWidget(source_label)
        source_row.addStretch(1)
        source_row.addWidget(self.ready_badge)
        left_layout.addLayout(source_row)

        self.upload_box = QFrame()
        self.upload_box.setObjectName("UploadBox")
        self.upload_box.setStyleSheet(
            "QFrame#UploadBox { background: #140c10; border: 1px dashed #3b2730; border-radius: 16px; }"
        )
        self.upload_box.setCursor(Qt.PointingHandCursor)
        self.upload_box.mousePressEvent = self._on_upload_clicked
        upload_layout = QVBoxLayout(self.upload_box)
        upload_layout.setContentsMargins(18, 18, 18, 18)
        upload_layout.setSpacing(6)
        upload_icon = QLabel("UPLOAD")
        upload_icon.setObjectName("FieldLabel")
        upload_icon.setAlignment(Qt.AlignCenter)
        upload_title = QLabel("Drag and drop source media")
        upload_title.setObjectName("FieldLabel")
        upload_title.setAlignment(Qt.AlignCenter)
        upload_hint = QLabel("H.264, ProRes, DNxHR, MKV")
        upload_hint.setObjectName("SubtitleLabel")
        upload_hint.setAlignment(Qt.AlignCenter)
        upload_layout.addStretch(1)
        upload_layout.addWidget(upload_icon)
        upload_layout.addWidget(upload_title)
        upload_layout.addWidget(upload_hint)
        upload_layout.addStretch(1)
        left_layout.addWidget(self.upload_box)

        self.file_card = QFrame()
        self.file_card.setObjectName("VideoFileCard")
        self.file_card.setStyleSheet(
            "QFrame#VideoFileCard { background: #24151e; border: 1px solid #3b2730; border-radius: 14px; }"
        )
        file_card_layout = QHBoxLayout(self.file_card)
        file_card_layout.setContentsMargins(12, 10, 12, 10)
        file_card_layout.setSpacing(10)
        file_icon = QLabel("VID")
        file_icon.setAlignment(Qt.AlignCenter)
        file_icon.setFixedSize(36, 36)
        file_icon.setStyleSheet(
            "QLabel { background: #130c10; border: none; border-radius: 10px;"
            " color: #8c7484; font-size: 10px; font-weight: 700; }"
        )
        file_meta_col = QVBoxLayout()
        file_meta_col.setSpacing(3)
        self.file_name = QLabel("No file selected")
        self.file_name.setObjectName("FieldLabel")
        self.file_meta = QLabel("Select a file to begin.")
        self.file_meta.setObjectName("SubtitleLabel")
        file_meta_col.addWidget(self.file_name)
        file_meta_col.addWidget(self.file_meta)
        file_card_layout.addWidget(file_icon)
        file_card_layout.addLayout(file_meta_col, 1)
        left_layout.addWidget(self.file_card)

        encoding_title = QLabel("Encoding Settings")
        encoding_title.setObjectName("SectionLabel")
        left_layout.addWidget(encoding_title)

        row = QHBoxLayout()
        row.setSpacing(10)

        format_col = QVBoxLayout()
        format_label = QLabel("Output Format")
        format_label.setObjectName("FieldLabel")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mov", "mkv"])
        format_col.addWidget(format_label)
        format_col.addWidget(self.format_combo)

        resolution_col = QVBoxLayout()
        resolution_label = QLabel("Resolution")
        resolution_label.setObjectName("FieldLabel")
        self.resize_combo = QComboBox()
        self.resize_combo.addItems(["Keep", "1920x1080", "1280x720", "854x480", "640x360"])
        resolution_col.addWidget(resolution_label)
        resolution_col.addWidget(self.resize_combo)

        row.addLayout(format_col, 1)
        row.addLayout(resolution_col, 1)
        left_layout.addLayout(row)

        codec_label = QLabel("Video Codec")
        codec_label.setObjectName("FieldLabel")
        left_layout.addWidget(codec_label)
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(
            [
                "H.264 (libx264)",
                "H.265 (libx265)",
                "VP9 (libvpx-vp9)",
                "AV1 (libaom-av1)",
                "Copy (stream copy)",
            ]
        )
        left_layout.addWidget(self.codec_combo)

        compression_row = QHBoxLayout()
        compression_label = QLabel("Compression Strength")
        compression_label.setObjectName("FieldLabel")
        self.compression_value = QLabel("")
        self.compression_value.setObjectName("SubtitleLabel")
        compression_row.addWidget(compression_label)
        compression_row.addStretch(1)
        compression_row.addWidget(self.compression_value)
        left_layout.addLayout(compression_row)

        self.compression_slider = QSlider(Qt.Horizontal)
        self.compression_slider.setRange(18, 30)
        self.compression_slider.setValue(22)
        self.compression_slider.valueChanged.connect(self._on_compression_changed)
        left_layout.addWidget(self.compression_slider)
        self._on_compression_changed(self.compression_slider.value())

        quality_row = QHBoxLayout()
        quality_row.setSpacing(6)
        quality_row.addWidget(self._chip_label("Quality"))
        quality_row.addStretch(1)
        quality_row.addWidget(self._chip_label("Balanced"))
        quality_row.addStretch(1)
        quality_row.addWidget(self._chip_label("File Size"))
        left_layout.addLayout(quality_row)

        self.hw_accel_toggle = QCheckBox("Hardware Acceleration (NVENC)")
        self.hw_accel_toggle.setChecked(True)
        left_layout.addWidget(self.hw_accel_toggle)

        self.metadata_toggle = QCheckBox("Preserve Metadata")
        self.metadata_toggle.setChecked(False)
        left_layout.addWidget(self.metadata_toggle)

        left_layout.addStretch(1)

        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        preview_card = QWidget()
        preview_card.setObjectName("PreviewCard")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(10)

        preview_frame = QFrame()
        preview_frame.setObjectName("EditorCanvas")
        preview_frame.setMinimumSize(320, 220)
        preview_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.preview_stack = QStackedLayout(preview_frame)
        self.preview_stack.setContentsMargins(8, 8, 8, 8)

        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label = QLabel("Load a video to preview output.")
        self.preview_label.setObjectName("PreviewLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)

        self.preview_stack.addWidget(self.video_widget)
        self.preview_stack.addWidget(self.preview_label)
        self.preview_stack.setCurrentWidget(self.preview_label)

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.6)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        preview_layout.addWidget(preview_frame, 1)

        right_col.addWidget(preview_card, 1)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.task_value = self._stat_card(stats_row, "CURRENT TASK", "Idle")
        self.queue_value = self._stat_card(stats_row, "QUEUE SIZE", "0 items")
        self.time_value = self._stat_card(stats_row, "ESTIMATED TIME", "--:--")
        right_col.addLayout(stats_row)

        self.status = QLabel("")
        self.status.setObjectName("StatusLabel")
        self.status.setVisible(False)
        right_col.addWidget(self.status)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        actions_row.addStretch(1)
        self.load_video_btn = QPushButton("Load Video")
        self.load_video_btn.setObjectName("PrimaryButton")
        self.load_video_btn.clicked.connect(self._open_video)
        self.close_video_btn = QPushButton("Close")
        self.close_video_btn.setObjectName("ToolButton")
        self.close_video_btn.clicked.connect(self._close_video)
        self.close_video_btn.setVisible(False)
        self.remux_btn = QPushButton("Remux")
        self.remux_btn.setObjectName("ToolButton")
        self.remux_btn.clicked.connect(self._run_remux)
        self.resize_btn = QPushButton("Resize")
        self.resize_btn.setObjectName("ToolButton")
        self.resize_btn.clicked.connect(self._run_resize)
        self.compress_btn = QPushButton("Compress")
        self.compress_btn.setObjectName("ToolButton")
        self.compress_btn.clicked.connect(self._run_compress)
        actions_row.addWidget(self.load_video_btn)
        actions_row.addWidget(self.close_video_btn)
        actions_row.addWidget(self.remux_btn)
        actions_row.addWidget(self.resize_btn)
        actions_row.addWidget(self.compress_btn)
        right_col.addLayout(actions_row)

        left_scroll = QScrollArea()
        left_scroll.setObjectName("EditorScroll")
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setStyleSheet(
            "QScrollArea { background: transparent; } "
            "QScrollArea > QWidget { background: transparent; }"
        )
        left_scroll.setWidget(left_panel)

        body_layout.addWidget(left_scroll, 2)
        body_layout.addLayout(right_col, 3)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addLayout(body_layout, 1)

        root_layout.addWidget(card)

    def set_theme(self, theme: str) -> None:
        return

    def _chip_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    def _stat_card(self, row: QHBoxLayout, title: str, value: str) -> QLabel:
        card = QFrame()
        card.setObjectName("ControlsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        title_label = QLabel(title)
        title_label.setObjectName("SectionLabel")
        value_label = QLabel(value)
        value_label.setObjectName("FieldLabel")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        row.addWidget(card, 1)
        return value_label

    def _on_upload_clicked(self, _event) -> None:
        self._open_video()

    def _on_compression_changed(self, value: int) -> None:
        label = self._compression_label(value)
        self.compression_value.setText(label)

    def _compression_label(self, value: int) -> str:
        if value <= 20:
            strength = "High"
        elif value <= 23:
            strength = "Medium"
        elif value <= 26:
            strength = "Balanced"
        else:
            strength = "Small"
        return f"{strength} (CRF {value})"

    def _format_bytes(self, value: int) -> str:
        if value <= 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(value)
        unit = 0
        while size >= 1024 and unit < len(units) - 1:
            size /= 1024.0
            unit += 1
        if size >= 100:
            return f"{size:.0f} {units[unit]}"
        if size >= 10:
            return f"{size:.1f} {units[unit]}"
        return f"{size:.2f} {units[unit]}"

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
        self.preview_stack.setCurrentWidget(self.video_widget)
        self.preview_label.setText("Load a video to preview output.")
        self._set_file_details(self._video_path)
        self.close_video_btn.setVisible(True)

    def _close_video(self) -> None:
        self.player.stop()
        self.player.setSource(QUrl())
        self._video_path = None
        self.preview_stack.setCurrentWidget(self.preview_label)
        self._clear_file_details()
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
            *self._metadata_args(),
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
        video_codec = self._selected_video_codec()
        if video_codec == "copy":
            self._set_status("Copy codec cannot be used with resize.", error=True)
            return
        output = self._ask_output_path(self.format_combo.currentText())
        if not output:
            return
        width, height = target.split("x", 1)
        crf = self.compression_slider.value()
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
            video_codec,
            "-preset",
            "fast",
            "-crf",
            str(crf),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            *self._metadata_args(),
            str(output),
        ]
        self._run_ffmpeg(args, output)

    def _run_compress(self) -> None:
        if not self._video_path:
            self._set_status("Load a video first.", error=True)
            return
        crf = self.compression_slider.value()
        video_codec = self._selected_video_codec()
        if video_codec == "copy":
            self._set_status("Copy codec cannot be used with compression.", error=True)
            return
        output = self._ask_output_path(self.format_combo.currentText())
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
            video_codec,
            "-preset",
            "fast",
            "-crf",
            str(crf),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            *self._metadata_args(),
            str(output),
        ]
        self._run_ffmpeg(args, output)

    def _selected_video_codec(self) -> str:
        label = self.codec_combo.currentText().strip()
        if label.startswith("H.265"):
            return "libx265"
        if label.startswith("VP9"):
            return "libvpx-vp9"
        if label.startswith("AV1"):
            return "libaom-av1"
        if label.startswith("Copy"):
            return "copy"
        return "libx264"

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
        self.task_value.setText("Encoding")
        self.process.start(args[0], args[1:])

    def _on_process_output(self) -> None:
        data = self.process.readAllStandardOutput().data().decode(errors="ignore").strip()
        if data:
            self._set_status("Working...", error=False)

    def _on_process_error(self) -> None:
        self._set_controls_enabled(True)
        self.task_value.setText("Idle")
        self._set_status("Failed to start ffmpeg.", error=True)

    def _on_process_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._set_controls_enabled(True)
        self.task_value.setText("Idle")
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

    def _metadata_args(self) -> list[str]:
        if self.metadata_toggle.isChecked():
            return ["-map_metadata", "0"]
        return []

    def _set_file_details(self, path: Path) -> None:
        self.file_name.setText(self._elide_filename(path.name))
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        size_label = self._format_bytes(size)
        suffix = path.suffix.upper().lstrip(".") or "VIDEO"
        self.file_meta.setText(f"{size_label} | {suffix}")

    def _clear_file_details(self) -> None:
        self.file_name.setText("No file selected")
        self.file_meta.setText("Select a file to begin.")

    def _elide_filename(self, name: str) -> str:
        max_len = self.MAX_NAME_CHARS
        if len(name) <= max_len:
            return name
        if "." in name:
            stem, ext = name.rsplit(".", 1)
            ext = f".{ext}"
            available = max_len - len(ext) - 3
            if available <= 0:
                return name[: max_len - 3] + "..."
            return f"{stem[:available]}...{ext}"
        return name[: max_len - 3] + "..."
