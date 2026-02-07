from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QProcess, Qt, QSize, QUrl
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPixmap, QRegion, QImage
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
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


class RoundedFrame(QFrame):
    def __init__(self, radius: int = 24, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._radius = radius
        self.setAttribute(Qt.WA_StyledBackground, True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        path = QPainterPath()
        rect = self.rect()
        path.addRoundedRect(rect, self._radius, self._radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))


class DownloadPage(QWidget):
    def __init__(self, state: AppState, on_theme_change, on_navigate) -> None:
        super().__init__()
        self.state = state
        self.on_theme_change = on_theme_change
        self.on_navigate = on_navigate

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_process_output)
        self.process.finished.connect(self._on_process_finished)
        self.process.errorOccurred.connect(self._on_process_error)

        self._current_output_path: Path | None = None
        self._last_progress = 0
        self._last_info_line = ""
        self._playlist_requested: int | None = None
        self._playlist_total: int | None = None
        self._last_output_base: str | None = None

        self._build_ui()
        self._sync_container_options()
        self._set_input_heights()
        self.apply_state(state)

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
        self.home_btn = QPushButton("Home")
        self.home_btn.setObjectName("NavButton")
        self.home_btn.clicked.connect(lambda: self.on_navigate("home"))
        nav_bar.addWidget(icon_badge)
        nav_bar.addWidget(header_title)
        nav_bar.addWidget(self.home_btn)
        nav_bar.addStretch(1)

        self.theme_toggle = QToolButton()
        self.theme_toggle.setObjectName("ThemeToggle")
        self.theme_toggle.setCheckable(True)
        self.theme_toggle.setToolTip("Toggle dark theme")
        self._sun_icon = svg_icon(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f01d85">'
            '<circle cx="12" cy="12" r="5"/>'
            '<g stroke="#f01d85" stroke-width="2" stroke-linecap="round">'
            '<line x1="12" y1="1" x2="12" y2="4"/>'
            '<line x1="12" y1="20" x2="12" y2="23"/>'
            '<line x1="1" y1="12" x2="4" y2="12"/>'
            '<line x1="20" y1="12" x2="23" y2="12"/>'
            '<line x1="4" y1="4" x2="6" y2="6"/>'
            '<line x1="18" y1="18" x2="20" y2="20"/>'
            '<line x1="18" y1="6" x2="20" y2="4"/>'
            '<line x1="4" y1="20" x2="6" y2="18"/>'
            "</g></svg>",
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

        content_row = QHBoxLayout()
        content_row.setSpacing(24)

        left = QWidget(card)
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(12)

        url_label = QLabel("VIDEO LINK")
        url_label.setObjectName("SectionLabel")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste URL here...")

        save_label = QLabel("SAVE LOCATION")
        save_label.setObjectName("SectionLabel")
        folder_row = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setReadOnly(True)
        self.browse_btn = QPushButton("Choose Folder")
        self.browse_btn.setObjectName("FolderButton")
        self.browse_btn.clicked.connect(self._choose_folder)
        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(self.browse_btn)

        tweak_group = QWidget()
        tweak_group.setObjectName("OptionsCard")
        tweak_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tweak_layout = QVBoxLayout(tweak_group)
        tweak_layout.setSpacing(10)
        tweak_layout.setContentsMargins(8, 16, 8, 16)

        quality_label = QLabel("QUALITY")
        quality_label.setObjectName("FieldLabel")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best", "Worst"])

        resolution_label = QLabel("RESOLUTION CAP")
        resolution_label.setObjectName("FieldLabel")
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["No cap", "480p", "720p", "1080p", "1440p", "2160p"])

        codec_label = QLabel("PREFER CODEC")
        codec_label.setObjectName("FieldLabel")
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["Any", "AV1", "H.264", "HEVC"])

        container_label = QLabel("FORMAT")
        container_label.setObjectName("FieldLabel")
        self.container_combo = QComboBox()

        audio_label = QLabel("AUDIO")
        audio_label.setObjectName("FieldLabel")
        self.audio_only_toggle = QCheckBox("Audio only")
        self.audio_only_toggle.toggled.connect(self._sync_container_options)

        format_label = QLabel("FORMAT SELECTOR")
        format_label.setObjectName("FieldLabel")
        self.format_input = QLineEdit()
        self.format_input.setPlaceholderText("Optional advanced -f string")

        multi_label = QLabel("IS IT A PLAYLIST?")
        multi_label.setObjectName("FieldLabel")
        multi_row = QHBoxLayout()
        self.multi_files_check = QCheckBox("Enable")
        self.multi_files_count = QSpinBox()
        self.multi_files_count.setRange(1, 9999)
        self.multi_files_count.setValue(5)
        self.multi_files_count.setEnabled(False)
        self.multi_files_check.toggled.connect(lambda checked: self.multi_files_count.setEnabled(checked))
        multi_row.addWidget(self.multi_files_check)
        multi_row.addStretch(1)
        multi_row.addWidget(self.multi_files_count)

        filename_label = QLabel("FILE NAME")
        filename_label.setObjectName("FieldLabel")
        self.filename_input = QLineEdit()
        self.filename_input.setText("%(title)s.%(ext)s")

        row_quality_format = QHBoxLayout()
        quality_box = QVBoxLayout()
        quality_box.setSpacing(6)
        quality_box.addWidget(quality_label)
        quality_box.addWidget(self.quality_combo)
        format_box = QVBoxLayout()
        format_box.setSpacing(6)
        format_box.addWidget(container_label)
        format_box.addWidget(self.container_combo)
        row_quality_format.addLayout(quality_box, 1)
        row_quality_format.addSpacing(12)
        row_quality_format.addLayout(format_box, 1)

        row_res_codec = QHBoxLayout()
        res_box = QVBoxLayout()
        res_box.setSpacing(6)
        res_box.addWidget(resolution_label)
        res_box.addWidget(self.resolution_combo)
        codec_box = QVBoxLayout()
        codec_box.setSpacing(6)
        codec_box.addWidget(codec_label)
        codec_box.addWidget(self.codec_combo)
        row_res_codec.addLayout(res_box, 1)
        row_res_codec.addSpacing(12)
        row_res_codec.addLayout(codec_box, 1)

        tweak_layout.addLayout(row_quality_format)
        tweak_layout.addLayout(row_res_codec)
        tweak_layout.addWidget(audio_label)
        tweak_layout.addWidget(self.audio_only_toggle)
        tweak_layout.addWidget(format_label)
        tweak_layout.addWidget(self.format_input)
        tweak_layout.addWidget(multi_label)
        tweak_layout.addLayout(multi_row)
        tweak_layout.addWidget(filename_label)
        tweak_layout.addWidget(self.filename_input)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("PrimaryButton")
        self.download_btn.clicked.connect(self._start_download)
        action_row.addWidget(self.download_btn, 1)

        self.status = QLabel("")
        self.status.setObjectName("StatusLabel")
        self.status.setWordWrap(True)
        self.status.setVisible(False)

        left_content = QWidget(left)
        left_content.setObjectName("LeftPanel")
        left_content_layout = QVBoxLayout(left_content)
        left_content_layout.setSpacing(14)
        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFixedHeight(1)

        left_content_layout.addWidget(divider)
        left_content_layout.addWidget(url_label)
        left_content_layout.addWidget(self.url_input)
        left_content_layout.addWidget(save_label)
        left_content_layout.addLayout(folder_row)
        left_content_layout.addWidget(tweak_group)
        left_content_layout.addLayout(action_row)
        left_content_layout.addWidget(self.status)
        left_content_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QScrollArea > QWidget { background: transparent; }")
        scroll.setWidget(left_content)

        left_layout.addWidget(scroll)

        right = QWidget(card)
        right.setObjectName("RightPanel")
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(14)

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(160, 200)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setStyleSheet("")

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.6)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.errorOccurred.connect(self._on_player_error)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.playbackStateChanged.connect(self._sync_play_button)
        self.player.positionChanged.connect(self._sync_position)
        self.player.durationChanged.connect(self._sync_duration)

        self.preview_label = QLabel("Preview area")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setObjectName("PreviewLabel")

        phone_frame = RoundedFrame(radius=24)
        phone_frame.setObjectName("PhoneFrame")
        phone_frame.setMinimumSize(160, 200)
        phone_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        phone_layout = QVBoxLayout(phone_frame)
        phone_layout.setContentsMargins(8, 8, 8, 8)
        phone_layout.addWidget(self.video_widget)

        preview_card = QWidget()
        preview_card.setObjectName("PreviewCard")
        preview_card_layout = QVBoxLayout(preview_card)
        preview_card_layout.setContentsMargins(16, 16, 16, 16)
        preview_card_layout.setSpacing(10)
        preview_card_layout.addWidget(phone_frame, 1)
        preview_card_layout.addWidget(self.preview_label)

        controls_card = QWidget()
        controls_card.setObjectName("ControlsCard")
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(16, 12, 16, 12)
        controls_layout.setSpacing(8)

        time_row = QHBoxLayout()
        self.current_time = QLabel("00:00")
        self.current_time.setObjectName("TimeLabel")
        self.total_time = QLabel("00:00")
        self.total_time.setObjectName("TimeLabel")
        time_row.addWidget(self.current_time)
        time_row.addStretch(1)
        time_row.addWidget(self.total_time)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.setObjectName("SeekSlider")
        self.position_slider.sliderMoved.connect(self.player.setPosition)

        controls_row = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.setObjectName("ControlButton")
        self.play_btn.clicked.connect(self._toggle_play)
        self.mute_btn = QPushButton("Mute")
        self.mute_btn.setObjectName("ControlButton")
        self.mute_btn.setCheckable(True)
        self.mute_btn.toggled.connect(self._toggle_mute)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(60)
        self.volume_slider.setObjectName("VolumeSlider")
        self.volume_slider.valueChanged.connect(self._set_volume)
        controls_row.addWidget(self.play_btn)
        controls_row.addWidget(self.mute_btn)
        controls_row.addStretch(1)
        controls_row.addWidget(self.volume_slider, 2)

        controls_layout.addWidget(self.position_slider)
        controls_layout.addLayout(time_row)
        controls_layout.addLayout(controls_row)

        right_layout.addWidget(preview_card, 1)
        right_layout.addWidget(controls_card)
        right_layout.addStretch(1)

        content_row.addWidget(left, 5)
        content_row.addWidget(right, 4)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addLayout(content_row)
        root_layout.addWidget(card)

    def apply_state(self, state: AppState) -> None:
        self.folder_input.setText(state.last_folder_path)
        self.filename_input.setText(state.filename_template or "%(title)s.%(ext)s")
        self.quality_combo.setCurrentText(state.quality)
        self.resolution_combo.setCurrentText(state.resolution_cap)
        self.codec_combo.setCurrentText(state.codec_preference)
        self.audio_only_toggle.setChecked(state.audio_only)
        self._sync_container_options()
        if state.output_container:
            self.container_combo.setCurrentText(state.output_container)
        self.format_input.setText(state.format_selector or "")
        self.multi_files_check.setChecked(state.multi_files_enabled)
        self.multi_files_count.setValue(state.multi_files_count or 5)
        self.volume_slider.setValue(state.volume)
        self.mute_btn.setChecked(state.muted)
        self.set_theme(state.theme)

    def update_state(self, state: AppState) -> None:
        state.last_folder_path = self.folder_input.text().strip() or state.last_folder_path
        state.filename_template = self.filename_input.text().strip() or state.filename_template
        state.quality = self.quality_combo.currentText()
        state.resolution_cap = self.resolution_combo.currentText()
        state.codec_preference = self.codec_combo.currentText()
        state.output_container = self.container_combo.currentText()
        state.audio_only = self.audio_only_toggle.isChecked()
        state.format_selector = self.format_input.text().strip()
        state.volume = self.volume_slider.value()
        state.muted = self.mute_btn.isChecked()
        state.multi_files_enabled = self.multi_files_check.isChecked()
        state.multi_files_count = self.multi_files_count.value()

    def _set_input_heights(self) -> None:
        height = 46
        inputs = [
            self.url_input,
            self.folder_input,
            self.quality_combo,
            self.resolution_combo,
            self.codec_combo,
            self.container_combo,
            self.format_input,
            self.filename_input,
            self.multi_files_count,
        ]
        for widget in inputs:
            widget.setFixedHeight(height)
        self.browse_btn.setFixedHeight(height)

    def _choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Choose download folder", self.folder_input.text().strip() or str(Path(self.state.last_folder_path))
        )
        if path:
            self.folder_input.setText(path)
            self.state.last_folder_path = path

    def _sync_container_options(self) -> None:
        self.container_combo.blockSignals(True)
        self.container_combo.clear()
        if self.audio_only_toggle.isChecked():
            self.container_combo.addItems(["m4a", "mp3", "opus"])
            self.container_combo.setCurrentText("m4a")
        else:
            self.container_combo.addItems(["mp4", "mkv", "webm"])
            self.container_combo.setCurrentText("mp4")
        self.container_combo.blockSignals(False)

    def _start_download(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please paste a video URL.")
            return

        base_folder = Path(self.folder_input.text().strip() or self.state.last_folder_path)
        self.state.last_folder_path = str(base_folder)
        base_folder.mkdir(parents=True, exist_ok=True)

        template_text = self.filename_input.text().strip() or "%(title)s.%(ext)s"
        self._last_output_base = None
        if "%(" not in template_text:
            base = Path(template_text).stem
            base = base or "video"
            suffix = ""
            existing = list(base_folder.glob(f"{base}*.*"))
            if existing:
                max_n = 0
                for file in existing:
                    stem = file.stem
                    if stem == base:
                        max_n = max(max_n, 1)
                    else:
                        match = re.match(rf"^{re.escape(base)}_(\d+)$", stem)
                        if match:
                            max_n = max(max_n, int(match.group(1)))
                if max_n > 0:
                    suffix = f"_{max_n + 1}"
                else:
                    suffix = "_1"
            self._last_output_base = f"{base}{suffix}"
            template_text = f"{base}{suffix}.%(ext)s"
        if "%(ext)" not in template_text:
            template_text = f"{template_text}.%(ext)s"
        output_template = base_folder / template_text
        self._current_output_path = base_folder
        self._last_progress = 0
        self._last_info_line = ""

        args = ["--newline", "-o", str(output_template)]

        format_override = self.format_input.text().strip()
        audio_only = self.audio_only_toggle.isChecked()
        container = self.container_combo.currentText().strip()

        if format_override:
            args += ["-f", format_override]
        else:
            quality = self.quality_combo.currentText()
            res_cap = self.resolution_combo.currentText()
            codec = self.codec_combo.currentText()

            if audio_only:
                args += ["-f", "ba/b"]
            else:
                fmt = "bv*+ba/b"
                if quality == "Worst":
                    fmt = "bv*+ba/b[quality=lowest]"
                if res_cap != "No cap":
                    height = res_cap.replace("p", "")
                    fmt = f"{fmt}[height<={height}]"
                if codec != "Any":
                    codec_map = {"AV1": "av01", "H.264": "avc1", "HEVC": "hev1"}
                    code = codec_map.get(codec, "")
                    if code:
                        fmt = f"{fmt}[vcodec*={code}]"
                args += ["-f", fmt]

        if audio_only:
            args += ["--extract-audio", "--audio-format", container]
        else:
            args += ["--merge-output-format", container]

        if self._is_playlist_url(url):
            if self.multi_files_check.isChecked():
                limit = self.multi_files_count.value()
                args += ["--playlist-end", str(limit)]
                self._playlist_requested = limit
            else:
                self._playlist_requested = 0
            self._playlist_total = None

        if "x.com/" in url or "twitter.com/" in url:
            args += ["--socket-timeout", "30", "--retries", "10", "--fragment-retries", "10", "--ignore-errors"]

        ffmpeg_location = self._ffmpeg_location()
        if ffmpeg_location:
            args += ["--ffmpeg-location", ffmpeg_location]

        args.append(url)

        self._set_running(True)
        self.status.setText(f"Saving to {base_folder}")
        self.status.setVisible(True)
        self._set_status_color(error=False)
        self.preview_label.setText("Downloading... preview will update when ready.")
        self.player.stop()

        self.process.start(self._yt_dlp_cmd(), args)

    def _yt_dlp_cmd(self) -> str:
        if hasattr(sys, "_MEIPASS"):
            base = Path(getattr(sys, "_MEIPASS"))
            bundled = base / "yt-dlp"
            if bundled.exists():
                return str(bundled)
        return "yt-dlp"

    def _ffmpeg_location(self) -> str | None:
        candidates: list[Path] = []
        if hasattr(sys, "_MEIPASS"):
            base = Path(getattr(sys, "_MEIPASS"))
            candidates += [base / "ffmpeg", base / "ffprobe"]
        candidates += [Path("/opt/homebrew/bin/ffmpeg"), Path("/usr/local/bin/ffmpeg")]
        for path in candidates:
            if path.exists():
                return str(path.parent)
        return None

    def _is_playlist_url(self, url: str) -> bool:
        return "list=" in url

    def _maybe_update_playlist_total(self, line: str) -> None:
        if self._playlist_total is not None:
            return
        total = None
        match = re.search(r"of\s+(\d+)", line)
        if match:
            total = int(match.group(1))
        else:
            match = re.search(r"Downloading\s+(\d+)\s+(?:videos|items)", line, re.IGNORECASE)
            if match:
                total = int(match.group(1))
        if total is None:
            return
        self._playlist_total = total
        if self._playlist_requested and self._playlist_requested > total:
            self._playlist_requested = 0
            self.status.setText(f"Playlist has {total} videos. Downloading all.")
            self.status.setVisible(True)

    def _set_running(self, running: bool) -> None:
        self.download_btn.setEnabled(not running)
        self.url_input.setEnabled(not running)

    def _on_process_output(self) -> None:
        data = self.process.readAllStandardOutput().data().decode(errors="ignore")
        for line in data.splitlines():
            self._parse_progress(line)

    def _parse_progress(self, line: str) -> None:
        if not line:
            return

        self._maybe_update_playlist_total(line)

        match = re.search(r"\[download\]\s+(\d{1,3}\.\d+)%", line)
        if match:
            value = int(float(match.group(1)))
            if value != self._last_progress:
                self._last_progress = value
            return

        if "Destination:" in line or "Merging formats into" in line:
            self.status.setText(line.strip())
            self._last_info_line = line.strip()
            self._set_status_color(error=False)
            return

        self._last_info_line = line.strip()

    def _on_process_error(self) -> None:
        self._set_running(False)
        self.status.setText("Failed to start yt-dlp. Is it installed and on PATH?")
        self.status.setVisible(True)
        self._set_status_color(error=True)

    def _on_process_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._set_running(False)
        if exit_code != 0:
            detail = self._last_info_line or "Download failed. Check the URL or yt-dlp output."
            self.status.setText(detail)
            self.status.setVisible(True)
            self._set_status_color(error=True)
            return

        self.status.setText("Download complete.")
        self.status.setVisible(True)
        self._set_status_color(error=False)

        mp4_path = None
        if self._current_output_path:
            if self._last_output_base:
                candidate = self._current_output_path / f"{self._last_output_base}.mp4"
                if candidate.exists():
                    mp4_path = candidate
            else:
                latest = self._find_latest_video()
                if latest:
                    mp4_path = latest

        if mp4_path:
            self._load_preview(mp4_path)
        else:
            self.preview_label.setText("No MP4 found for this download. Try MP4 format.")

    def _find_latest_video(self) -> Path | None:
        if not self._current_output_path or not self._current_output_path.exists():
            return None
        candidates = list(self._current_output_path.glob("*.mp4"))
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

    def _load_preview(self, path: Path) -> None:
        if not path.exists():
            self.preview_label.setText("Video file not found.")
            return
        self.preview_label.setText("")
        url = QUrl.fromLocalFile(str(path))
        self.player.setSource(url)
        self.player.play()

    def _set_status_color(self, error: bool) -> None:
        color = "#b00020" if error else "#2a2a2a"
        self.status.setStyleSheet(f"color: {color};")

    def _toggle_play(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _sync_play_button(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.play_btn.setText("Pause")
        else:
            self.play_btn.setText("Play")

    def _sync_position(self, position: int) -> None:
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)
        self.current_time.setText(self._format_time(position))

    def _sync_duration(self, duration: int) -> None:
        self.position_slider.setRange(0, duration)
        self.total_time.setText(self._format_time(duration))

    def _toggle_mute(self, checked: bool) -> None:
        self.audio_output.setMuted(checked)
        self.mute_btn.setText("Muted" if checked else "Mute")

    def _set_volume(self, value: int) -> None:
        self.audio_output.setVolume(value / 100)

    def _format_time(self, ms: int) -> str:
        total_seconds = max(0, ms // 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        if error == QMediaPlayer.NoError:
            return
        message = error_string or "Playback error."
        self.preview_label.setText(message)
        self.status.setText(message)
        self._set_status_color(error=True)

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.LoadingMedia:
            self.preview_label.setText("Loading video...")
        elif status == QMediaPlayer.BufferingMedia:
            self.preview_label.setText("Buffering...")
        elif status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            self.preview_label.setText("")

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
