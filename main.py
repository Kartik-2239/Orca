import os
import re
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QProcess, Qt, QSize, QUrl
from PySide6.QtGui import QFont, QIcon, QPainter, QPainterPath, QPixmap, QRegion, QImage
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QSpacerItem,
    QScrollArea,
    QSlider,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def human_path(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


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


class VideoDownloader(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Video downloader")
        self.setMinimumSize(860, 600)

        self.base_dir = Path(__file__).parent
        self.default_downloads = self.base_dir / "downloads"
        self.default_downloads.mkdir(parents=True, exist_ok=True)

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyRead.connect(lambda: self.process.readAll())
        self.process.finished.connect(self.process.deleteLater)
        self.process.finished.connect(self._on_process_finished)
        self.process.errorOccurred.connect(self._on_process_error)
        # self.process.start(program, arguments)


        self._current_output_path: Path | None = None
        self._last_progress = 0
        self._last_info_line = ""

        self._init_ui()
        self._refresh_subfolders()
        self._sync_container_options()
        self._set_input_heights()

    def _init_ui(self) -> None:
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(0)

        card = QWidget(root)
        card.setObjectName("MainCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(24)

        left = QWidget(card)
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(12)

        header_row = QHBoxLayout()
        icon_badge = QLabel("DL")
        icon_badge.setAlignment(Qt.AlignCenter)
        icon_badge.setObjectName("IconBadge")
        header_title = QLabel("Downloader")
        header_title.setObjectName("HeaderTitle")
        header_row.addWidget(icon_badge)
        header_row.addWidget(header_title)
        header_row.addStretch(1)


        url_label = QLabel("VIDEO LINK")
        url_label.setObjectName("SectionLabel")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste URL here...")
        
        save_label = QLabel("SAVE LOCATION")
        save_label.setObjectName("SectionLabel")
        folder_row = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setReadOnly(True)
        self.folder_input.setText(human_path(self.default_downloads))
        self.browse_btn = QPushButton("Choose Folder")
        self.browse_btn.setObjectName("FolderButton")
        self.browse_btn.clicked.connect(self._choose_folder)
        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(self.browse_btn)
        
        subfolder_label = QLabel("SUBFOLDER")
        subfolder_label.setObjectName("SectionLabel")
        name_row = QHBoxLayout()
        self.subfolder_combo = QComboBox()
        self.subfolder_combo.setEditable(False)
        self.subfolder_combo.currentTextChanged.connect(self._on_subfolder_changed)
        self.new_sub_btn = QPushButton("New Folder")
        self.new_sub_btn.setObjectName("FolderButton")
        self.new_sub_btn.clicked.connect(self._create_subfolder)
        name_row.addWidget(self.subfolder_combo, 1)
        name_row.addWidget(self.new_sub_btn)


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
        divider.setFrameShape(QFrame.HLine)

        left_content_layout.addLayout(header_row)
        left_content_layout.addWidget(divider)
        left_content_layout.addWidget(url_label)
        left_content_layout.addWidget(self.url_input)
        left_content_layout.addWidget(save_label)
        left_content_layout.addLayout(folder_row)
        left_content_layout.addWidget(subfolder_label)
        left_content_layout.addLayout(name_row)
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

        theme_row = QHBoxLayout()
        theme_row.addStretch(1)
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
        theme_row.addWidget(self.theme_toggle)

        preview_title = QLabel("Preview")
        preview_title.setObjectName("PreviewTitle")

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

        right_layout.addLayout(theme_row)
        right_layout.addWidget(preview_title)
        right_layout.addWidget(preview_card, 1)
        right_layout.addWidget(controls_card)
        right_layout.addStretch(1)

        card_layout.addWidget(left, 5)
        card_layout.addWidget(right, 4)
        root_layout.addWidget(card)

        self.setCentralWidget(root)
        self._apply_styles("Light")

    def _choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Choose download folder", str(self.default_downloads)
        )
        if path:
            self.folder_input.setText(path)
            self._refresh_subfolders()

    def _create_subfolder(self) -> None:
        base = Path(self.folder_input.text().strip() or self.default_downloads)
        name, ok = QInputDialog.getText(self, "New Folder", "")
        if not ok or not name.strip():
            return
        folder = self._sanitize_folder_name(name)
        target = base / folder
        target.mkdir(parents=True, exist_ok=True)
        self._refresh_subfolders(select=folder)

    def _refresh_subfolders(self, select: str | None = None) -> None:
        base = Path(self.folder_input.text().strip() or self.default_downloads)
        base.mkdir(parents=True, exist_ok=True)
        folders = sorted([p.name for p in base.iterdir() if p.is_dir()])
        self.subfolder_combo.blockSignals(True)
        self.subfolder_combo.clear()
        self.subfolder_combo.addItems(folders)
        if select and select in folders:
            self.subfolder_combo.setCurrentText(select)
        elif folders:
            self.subfolder_combo.setCurrentIndex(0)
        self.subfolder_combo.blockSignals(False)

    def _on_subfolder_changed(self, _text: str) -> None:
        pass

    def _sanitize_folder_name(self, name: str) -> str:
        cleaned = re.sub(r"[^\w\- ]+", "", name).strip()
        cleaned = cleaned.replace(" ", "-")
        return cleaned or "download"

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

    def _set_input_heights(self) -> None:
        height = 46
        inputs = [
            self.url_input,
            self.folder_input,
            self.subfolder_combo,
            self.quality_combo,
            self.resolution_combo,
            self.codec_combo,
            self.container_combo,
            self.format_input,
            self.filename_input,
        ]
        for widget in inputs:
            widget.setFixedHeight(height)
        self.browse_btn.setFixedHeight(height)
        self.new_sub_btn.setFixedHeight(height)

    def _start_download(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please paste a video URL.")
            return

        base_folder = Path(self.folder_input.text().strip() or self.default_downloads)
        subfolder = self.subfolder_combo.currentText().strip()
        if not subfolder:
            subfolder = "download"
        target_folder = base_folder / self._sanitize_folder_name(subfolder)
        target_folder.mkdir(parents=True, exist_ok=True)

        template_text = self.filename_input.text().strip() or "%(title)s.%(ext)s"
        if "%(" not in template_text:
            base = Path(template_text).stem
            base = base or "video"
            suffix = ""
            existing = list(target_folder.glob(f"{base}*.*"))
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
            template_text = f"{base}{suffix}.%(ext)s"
        if "%(ext)" not in template_text:
            template_text = f"{template_text}.%(ext)s"
        output_template = target_folder / template_text
        self._current_output_path = target_folder
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


        if "x.com/" in url or "twitter.com/" in url:
            args += ["--socket-timeout", "30", "--retries", "10", "--fragment-retries", "10", "--ignore-errors"]

        args.append(url)

        self._set_running(True)
        self.status.setText(f"Saving to {human_path(target_folder)}")
        self.status.setVisible(True)
        self._set_status_color(error=False)
        if hasattr(self, "preview_label"):
            self.preview_label.setText("Downloading... preview will update when ready.")
        if hasattr(self, "player"):
            self.player.stop()

        self.process.start(self._yt_dlp_cmd(), args)

    def _yt_dlp_cmd(self) -> str:
        if hasattr(sys, "_MEIPASS"):
            base = Path(getattr(sys, "_MEIPASS"))
            bundled = base / "yt-dlp"
            if bundled.exists():
                return str(bundled)
        return "yt-dlp"

    def _cancel_download(self) -> None:
        if self.process.state() != QProcess.NotRunning:
            self.process.kill()
        self._set_running(False)
        self.status.setText("Download cancelled.")
        self.status.setVisible(True)
        self._set_status_color(error=True)

    def _set_running(self, running: bool) -> None:
        self.download_btn.setEnabled(not running)
        self.url_input.setEnabled(not running)
        self.subfolder_combo.setEnabled(not running)

    def _on_process_output(self) -> None:
        data = self.process.readAllStandardOutput().data().decode(errors="ignore")
        for line in data.splitlines():
            self._parse_progress(line)

    def _parse_progress(self, line: str) -> None:
        if not line:
            return

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

        latest = self._find_latest_video()
        if latest:
            self._load_preview(latest)
        else:
            if hasattr(self, "preview_label"):
                self.preview_label.setText("Download complete, but no playable file found.")

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
        self.status.setVisible(True)

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


    def _apply_styles(self, theme: str) -> None:
        if theme == "Dark":
            self.setStyleSheet(
                """
                QMainWindow { background: #0f0b0d; }
                QWidget#MainCard {
                    background: #1c141a;
                    border: 1px solid #3b2730;
                    border-radius: 28px;
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
                QToolButton#ThemeToggle {
                    background: #26161f;
                    border: 1px solid #38212b;
                    border-radius: 12px;
                    padding: 4px;
                    min-width: 26px;
                    min-height: 26px;
                }
                QToolButton#ThemeToggle:checked {
                    background: #2a1b22;
                    border: 1px solid #3a2430;
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
                QLineEdit, QComboBox {
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
                    border-radius: 28px;
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
                QToolButton#ThemeToggle {
                    background: #ffffff;
                    border: 1px solid #f1d7e6;
                    border-radius: 12px;
                    padding: 4px;
                    min-width: 26px;
                    min-height: 26px;
                }
                QToolButton#ThemeToggle:checked {
                    background: #ffe1ef;
                    border: 1px solid #f1d7e6;
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
                QLineEdit, QComboBox {
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

    def _on_theme_toggled(self, checked: bool) -> None:
        if checked:
            self.theme_toggle.setIcon(self._moon_icon)
            self._apply_styles("Dark")
        else:
            self.theme_toggle.setIcon(self._sun_icon)
            self._apply_styles("Light")


def main() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(app.style().standardIcon(QStyle.SP_MediaPlay))
    window = VideoDownloader()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
