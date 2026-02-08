from __future__ import annotations

import os
import subprocess
import tempfile
import shutil
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QSize, QThread, Signal, QObject
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
    QToolButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
    QPlainTextEdit,
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


class SpeechToTextPage(QWidget):
    def __init__(self, state: AppState, on_theme_change, on_navigate) -> None:
        super().__init__()
        self.state = state
        self.on_theme_change = on_theme_change
        self.on_navigate = on_navigate
        self._input_path: Path | None = None
        self._worker_thread: QThread | None = None
        self._worker: _WhisperWorker | None = None
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
        self.home_btn = QPushButton("Home")
        self.home_btn.setObjectName("NavButton")
        self.home_btn.clicked.connect(lambda: self.on_navigate("home"))
        nav_bar.addWidget(icon_badge)
        nav_bar.addWidget(header_title)
        nav_bar.addWidget(self.home_btn)
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

        title = QLabel("Speech to Text")
        title.setObjectName("PreviewTitle")
        subtitle = QLabel("Whisper small transcription to SRT.")
        subtitle.setObjectName("SubtitleLabel")

        self.content_stack = QStackedLayout()

        missing_page = QWidget()
        missing_layout = QVBoxLayout(missing_page)
        missing_layout.setContentsMargins(16, 16, 16, 16)
        missing_layout.setSpacing(12)
        missing_title = QLabel("Whisper Small Not Found")
        missing_title.setObjectName("SectionLabel")
        missing_hint = QLabel("Install the model to enable speech-to-text.")
        missing_hint.setObjectName("SubtitleLabel")
        self.install_btn = QPushButton("Install Whisper Small")
        self.install_btn.setObjectName("PrimaryButton")
        self.install_btn.clicked.connect(self._install_model)
        self.install_status = QLabel("")
        self.install_status.setObjectName("StatusLabel")
        self.install_status.setVisible(False)
        missing_layout.addStretch(1)
        missing_layout.addWidget(missing_title)
        missing_layout.addWidget(missing_hint)
        missing_layout.addWidget(self.install_btn)
        missing_layout.addWidget(self.install_status)
        missing_layout.addStretch(2)

        main_page = QWidget()
        main_layout = QHBoxLayout(main_page)
        main_layout.setSpacing(16)

        left = QFrame()
        left.setObjectName("OptionsCard")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        header_row = QHBoxLayout()
        source_label = QLabel("Source Media")
        source_label.setObjectName("SectionLabel")
        self.ready_badge = QLabel("READY")
        self.ready_badge.setStyleSheet(
            "QLabel { color: #22c55e; background: rgba(34, 197, 94, 0.12);"
            " padding: 2px 8px; border-radius: 6px; font-size: 10px; font-weight: 700; }"
        )
        header_row.addWidget(source_label)
        header_row.addStretch(1)
        header_row.addWidget(self.ready_badge)
        left_layout.addLayout(header_row)

        upload_box = QFrame()
        upload_box.setStyleSheet(
            "QFrame {"
            " background: #1b1117;"
            " border: 1px dashed #3b2730;"
            " border-radius: 14px;"
            "}"
        )
        upload_layout = QVBoxLayout(upload_box)
        upload_layout.setContentsMargins(16, 16, 16, 16)
        upload_layout.setSpacing(6)
        upload_title = QLabel("Upload new media")
        upload_title.setObjectName("FieldLabel")
        upload_title.setAlignment(Qt.AlignCenter)
        upload_hint = QLabel("MP4, MOV, WAV, MP3")
        upload_hint.setObjectName("SubtitleLabel")
        upload_hint.setAlignment(Qt.AlignCenter)
        upload_layout.addStretch(1)
        upload_layout.addWidget(upload_title)
        upload_layout.addWidget(upload_hint)
        upload_layout.addStretch(1)
        left_layout.addWidget(upload_box)

        self.file_card = QFrame()
        self.file_card.setStyleSheet(
            "QFrame { background: #24151e; border: 1px solid #3b2730; border-radius: 12px; }"
        )
        file_card_layout = QVBoxLayout(self.file_card)
        file_card_layout.setContentsMargins(12, 10, 12, 10)
        file_card_layout.setSpacing(4)
        self.file_name = QLabel("No file selected")
        self.file_name.setObjectName("FieldLabel")
        self.file_meta = QLabel("")
        self.file_meta.setObjectName("SubtitleLabel")
        file_card_layout.addWidget(self.file_name)
        file_card_layout.addWidget(self.file_meta)
        left_layout.addWidget(self.file_card)

        model_label = QLabel("Model Settings")
        model_label.setObjectName("SectionLabel")
        left_layout.addWidget(model_label)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Whisper Small"])
        left_layout.addWidget(self.engine_combo)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["Auto-detect Language", "English", "Spanish", "French", "German"])
        left_layout.addWidget(self.language_combo)

        self.denoise_toggle = QCheckBox("Denoise audio input")
        self.denoise_toggle.setChecked(True)
        left_layout.addWidget(self.denoise_toggle)

        self.speaker_toggle = QCheckBox("Speaker identification")
        self.speaker_toggle.setChecked(False)
        left_layout.addWidget(self.speaker_toggle)

        left_layout.addStretch(1)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        self.pick_btn = QPushButton("Choose File")
        self.pick_btn.setObjectName("ToolButton")
        self.pick_btn.clicked.connect(self._choose_file)
        buttons_row.addWidget(self.pick_btn)

        self.run_btn = QPushButton("Generate")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.clicked.connect(self._run_transcription)
        buttons_row.addWidget(self.run_btn)

        self.save_btn = QPushButton("Save SRT")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self._save_subtitles)
        self.save_btn.setEnabled(False)
        buttons_row.addWidget(self.save_btn)

        left_layout.addLayout(buttons_row)

        self.status = QLabel("")
        self.status.setObjectName("StatusLabel")
        self.status.setVisible(False)
        left_layout.addWidget(self.status)

        right = QFrame()
        right.setObjectName("OptionsCard")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        output_label = QLabel("Live Document")
        output_label.setObjectName("SectionLabel")
        right_layout.addWidget(output_label)

        self.output_text = QPlainTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Subtitles will appear here.")
        self.output_text.setStyleSheet(
            "QPlainTextEdit {"
            " background: #24151e;"
            " color: #e9e1e6;"
            " border: none;"
            " border-radius: 8px;"
            " padding: 8px;"
            "}"
        )
        right_layout.addWidget(self.output_text, 1)

        main_layout.addWidget(left, 3)
        main_layout.addWidget(right, 2)

        self.content_stack.addWidget(missing_page)
        self.content_stack.addWidget(main_page)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addLayout(self.content_stack, 1)
        root_layout.addWidget(card)
        self._sync_model_state()

    def set_theme(self, theme: str) -> None:
        return

    def _choose_file(self) -> None:
        start_dir = self.state.last_folder_path or ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio or Video",
            start_dir,
            "Media Files (*.wav *.mp3 *.m4a *.flac *.aac *.ogg *.mp4 *.mov *.mkv *.webm *.avi);;All Files (*)",
        )
        if not path:
            return
        self._input_path = Path(path)
        self.state.last_folder_path = str(self._input_path.parent)
        self.input_path.setText(str(self._input_path))

    def _run_transcription(self) -> None:
        if not self._input_path:
            self._set_status("Choose a file first.", error=True)
            return
        if not _WhisperWorker.is_model_available():
            self._sync_model_state()
            self._set_status("Model not installed.", error=True)
            return
        if self._worker_thread and self._worker_thread.isRunning():
            self._set_status("Transcription already running.", error=True)
            return
        self.output_text.clear()
        self.save_btn.setEnabled(False)
        self._set_status("Preparing...", error=False)
        self._set_controls_enabled(False)
        self._worker_thread = QThread(self)
        self._worker = _WhisperWorker(self._input_path)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.start()

    def _on_finished(self, srt_text: str) -> None:
        self._set_controls_enabled(True)
        self.output_text.setPlainText(srt_text)
        self.save_btn.setEnabled(bool(srt_text.strip()))
        self._set_status("Subtitles ready.", error=False)

    def _on_error(self, message: str) -> None:
        self._set_controls_enabled(True)
        self._set_status(message, error=True)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.pick_btn.setEnabled(enabled)
        self.run_btn.setEnabled(enabled)
        self.save_btn.setEnabled(enabled and bool(self.output_text.toPlainText().strip()))

    def _set_status(self, message: str, error: bool) -> None:
        self.status.setText(message)
        self.status.setVisible(True)
        color = "#b00020" if error else "#b25574"
        self.status.setStyleSheet(f"color: {color};")

    def _save_subtitles(self) -> None:
        if not self._input_path:
            self._set_status("Choose a file first.", error=True)
            return
        text = self.output_text.toPlainText().strip()
        if not text:
            self._set_status("No subtitles to save.", error=True)
            return
        default_name = self._input_path.with_suffix(".srt").name
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Subtitles",
            str(Path(self.state.last_folder_path or self._input_path.parent) / default_name),
            "SubRip (*.srt);;All Files (*)",
        )
        if not save_path:
            return
        Path(save_path).write_text(text)
        self._set_status(f"Saved subtitles to {save_path}", error=False)

    def _sync_model_state(self) -> None:
        if _WhisperWorker.is_model_available():
            self.content_stack.setCurrentIndex(1)
        else:
            self.content_stack.setCurrentIndex(0)

    def _install_model(self) -> None:
        if self._worker_thread and self._worker_thread.isRunning():
            return
        self.install_btn.setEnabled(False)
        self.install_status.setVisible(True)
        self.install_status.setText("Downloading model...")
        self._worker_thread = QThread(self)
        self._worker = _WhisperInstallWorker()
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_install_finished)
        self._worker.error.connect(self._on_install_error)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.start()

    def _on_install_finished(self) -> None:
        self.install_btn.setEnabled(True)
        self.install_status.setText("Model installed.")
        self._sync_model_state()

    def _on_install_error(self, message: str) -> None:
        self.install_btn.setEnabled(True)
        self.install_status.setText(message or "Install failed.")


class _WhisperWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, input_path: Path) -> None:
        super().__init__()
        self.input_path = input_path

    def run(self) -> None:
        try:
            from transformers import pipeline
        except Exception:
            self.error.emit("Install transformers to run Whisper.")
            return
        if not self.is_model_available():
            self.error.emit("Model not installed.")
            return
        audio_path = self._prepare_audio(self.input_path)
        if not audio_path:
            self.error.emit("Failed to prepare audio (ffmpeg required for video).")
            return
        try:
            pipe = pipeline(
                task="automatic-speech-recognition",
                model="openai/whisper-small",
                device=-1,
            )
            result = pipe(audio_path, return_timestamps=True)
            srt_text = _to_srt(result)
            self.finished.emit(srt_text)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            if audio_path and audio_path != str(self.input_path):
                try:
                    os.remove(audio_path)
                except Exception:
                    pass

    def _prepare_audio(self, path: Path) -> str | None:
        if path.suffix.lower() in {".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg"}:
            return str(path)
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return None
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp.close()
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(path),
            "-ac",
            "1",
            "-ar",
            "16000",
            tmp.name,
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return tmp.name
        except Exception:
            return None

    @staticmethod
    def is_model_available() -> bool:
        cache = os.environ.get("HF_HOME") or os.environ.get("TRANSFORMERS_CACHE")
        if not cache:
            cache = os.path.expanduser("~/.cache/huggingface/hub")
        model_dir = os.path.join(cache, "models--openai--whisper-small")
        return os.path.isdir(model_dir)


def _to_srt(result: dict) -> str:
    chunks = result.get("chunks") or []
    lines = []
    for idx, chunk in enumerate(chunks, start=1):
        start, end = chunk.get("timestamp", (None, None))
        if start is None or end is None:
            continue
        text = (chunk.get("text") or "").strip()
        lines.append(str(idx))
        lines.append(f"{_fmt_time(start)} --> {_fmt_time(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _fmt_time(seconds: float) -> str:
    ms = int((seconds - int(seconds)) * 1000)
    total = int(seconds)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class _WhisperInstallWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def run(self) -> None:
        try:
            from transformers import pipeline
        except Exception:
            self.error.emit("Install transformers to download Whisper.")
            return
        try:
            pipeline(
                task="automatic-speech-recognition",
                model="openai/whisper-small",
                device=-1,
            )
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
