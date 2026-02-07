from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

import requests
from bs4 import BeautifulSoup
from PIL import Image

from PySide6.QtCore import QByteArray, Qt, QSize, QObject, QThread, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap, QImage
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
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


class ImageDownloadWorker(QObject):
    progress = Signal(str)
    finished = Signal(int)
    error = Signal(str)

    def __init__(
        self,
        page: "ImageDownloaderPage",
        url: str,
        folder: Path,
        limit: int,
        headers: dict[str, str],
    ) -> None:
        super().__init__()
        self.page = page
        self.url = url
        self.folder = folder
        self.limit = limit
        self.headers = headers

    def run(self) -> None:
        try:
            response = requests.get(self.url, headers=self.headers, timeout=15)
            response.raise_for_status()
        except Exception:
            self.error.emit("Could not download the page.")
            return

        self.progress.emit("Scanning page...")
        soup = BeautifulSoup(response.text, "html.parser")
        candidates = self.page._collect_candidates(soup, self.url)
        if not candidates:
            self.error.emit("No images found on the page.")
            return

        saved = self.page._download_candidates(candidates, self.folder, self.headers, self.limit, self.progress.emit)
        self.finished.emit(saved)


class ImageDownloaderPage(QWidget):
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

        title = QLabel("Image Downloader")
        title.setObjectName("PreviewTitle")
        subtitle = QLabel("Download images from a webpage.")
        subtitle.setObjectName("SubtitleLabel")

        bulk_label = QLabel("SOURCE URL")
        bulk_label.setObjectName("SectionLabel")
        self.bulk_url_input = QLineEdit()
        self.bulk_url_input.setPlaceholderText("Paste a webpage URL...")
        self.bulk_limit = QSpinBox()
        self.bulk_limit.setRange(1, 500)
        self.bulk_limit.setValue(50)
        limit_row = QHBoxLayout()
        limit_title = QLabel("Max images")
        limit_title.setObjectName("FieldLabel")
        limit_row.addWidget(limit_title)
        limit_row.addWidget(self.bulk_limit)
        limit_row.addStretch(1)

        self.bulk_download_btn = QPushButton("Scrape Images")
        self.bulk_download_btn.setObjectName("PrimaryButton")
        self.bulk_download_btn.clicked.connect(self._scrape_images)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("FieldLabel")
        self.progress_label.setVisible(False)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)

        card_layout.addLayout(nav_bar)
        card_layout.addWidget(top_divider)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(12)
        card_layout.addWidget(bulk_label)
        card_layout.addWidget(self.bulk_url_input)
        card_layout.addLayout(limit_row)
        card_layout.addWidget(self.bulk_download_btn)
        card_layout.addWidget(self.progress_label)
        card_layout.addWidget(self.progress_bar)
        card_layout.addStretch(1)

        root_layout.addWidget(card)

    def _on_theme_toggled(self, checked: bool) -> None:
        if checked:
            self.theme_toggle.setIcon(self._moon_icon)
            self.on_theme_change("Dark")
        else:
            self.theme_toggle.setIcon(self._sun_icon)
            self.on_theme_change("Light")

    def set_theme(self, theme: str) -> None:
        return

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self.bulk_download_btn.setEnabled(not busy)
        self.bulk_url_input.setEnabled(not busy)
        self.bulk_limit.setEnabled(not busy)
        self.progress_label.setVisible(busy)
        self.progress_bar.setVisible(busy)
        self.progress_label.setText(message)

    def _on_progress(self, message: str) -> None:
        self.progress_label.setText(message)

    def _on_finished(self, saved: int) -> None:
        self._set_busy(False)
        if saved == 0:
            QMessageBox.information(self, "Done", "No images matched the filters.")
        else:
            QMessageBox.information(self, "Done", f"Saved {saved} images.")

    def _on_error(self, message: str) -> None:
        self._set_busy(False)
        QMessageBox.warning(self, "Image Downloader", message)

    def _scrape_images(self) -> None:
        url = self.bulk_url_input.text().strip()
        if not url:
            QMessageBox.information(self, "Missing URL", "Please paste a URL.")
            return
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(self, "Invalid URL", "Please include http:// or https://")
            return

        folder = QFileDialog.getExistingDirectory(self, "Save Images To", self.state.last_folder_path)
        if not folder:
            return

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": url,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }
        limit = self.bulk_limit.value()

        self.state.last_folder_path = folder
        self._set_busy(True, "Fetching page...")

        self.worker_thread = QThread()
        self.worker = ImageDownloadWorker(self, url, Path(folder), limit, headers)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def _collect_candidates(self, soup: BeautifulSoup, base_url: str) -> list[tuple[str, int]]:
        scored: dict[str, int] = {}

        def add(url: str, score: int) -> None:
            if not url:
                return
            absolute = self._normalize_url(url, base_url)
            if not absolute:
                return
            upgraded = self._upgrade_url(absolute)
            self._score_url(scored, absolute, score)
            if upgraded != absolute:
                self._score_url(scored, upgraded, score + 5)

        # Meta tags
        meta_props = [
            ("property", "og:image"),
            ("property", "og:image:secure_url"),
            ("name", "twitter:image"),
            ("property", "article:image"),
        ]
        for attr, value in meta_props:
            tag = soup.find("meta", attrs={attr: value})
            if tag and tag.get("content"):
                add(tag["content"], 100)

        # Legacy link image
        link_tag = soup.find("link", rel="image_src")
        if link_tag and link_tag.get("href"):
            add(link_tag["href"], 90)

        # Picture sources
        for picture in soup.find_all("picture"):
            for source in picture.find_all("source"):
                srcset = source.get("srcset") or source.get("data-srcset")
                best = self._best_from_srcset(srcset)
                if best:
                    score = 50 if self._srcset_width(srcset) >= 1200 else 30
                    add(best, score)

        # Image tags
        for img in soup.find_all("img"):
            attrs_priority = [
                "data-srcset",
                "srcset",
                "data-src",
                "data-original",
                "data-lazy-src",
                "data-full",
                "data-large",
                "src",
            ]
            for attr in attrs_priority:
                value = img.get(attr)
                if not value:
                    continue
                if "srcset" in attr:
                    best = self._best_from_srcset(value)
                    if best:
                        score = 50 if self._srcset_width(value) >= 1200 else 30
                        add(best, score)
                        break
                else:
                    score = 30 if attr in ("data-original", "data-full", "data-large") else 10
                    add(value, score)
                    break

        # Background images in inline styles
        style_regex = re.compile(r"background-image\s*:\s*url\(([^)]+)\)", re.IGNORECASE)
        for tag in soup.find_all(style=True):
            match = style_regex.search(tag.get("style", ""))
            if match:
                add(match.group(1).strip(" '\""), 20)

        # Data attribute patterns
        for tag in soup.find_all(True):
            for key, value in tag.attrs.items():
                if not key.startswith("data-"):
                    continue
                if not any(token in key.lower() for token in ("image", "img", "photo", "picture")):
                    continue
                if isinstance(value, list):
                    value = " ".join(value)
                if not value:
                    continue
                if "srcset" in key:
                    best = self._best_from_srcset(value)
                    if best:
                        add(best, 30)
                else:
                    add(str(value), 20)

        # Score/penalty adjustments and final list
        scored_final = []
        for url, score in scored.items():
            lowered = url.lower()
            if any(token in lowered for token in ("thumb", "thumbnail", "icon", "avatar", "logo")):
                score -= 20
            if lowered.endswith(".svg") or lowered.endswith(".gif"):
                score -= 30
            scored_final.append((url, score))

        scored_final.sort(key=lambda item: item[1], reverse=True)
        return scored_final

    def _score_url(self, scored: dict[str, int], url: str, score: int) -> None:
        scored[url] = max(scored.get(url, -10**9), score)

    def _normalize_url(self, url: str, base_url: str) -> str | None:
        url = url.strip()
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("data:"):
            return None
        return urljoin(base_url, url)

    def _best_from_srcset(self, srcset: str | None) -> str | None:
        if not srcset:
            return None
        best_url = None
        best_width = -1
        for part in srcset.split(","):
            part = part.strip()
            if not part:
                continue
            bits = part.split()
            if not bits:
                continue
            url = bits[0]
            width = self._extract_width(bits[1] if len(bits) > 1 else "")
            if width > best_width:
                best_width = width
                best_url = url
        return best_url

    def _srcset_width(self, srcset: str | None) -> int:
        if not srcset:
            return 0
        max_width = 0
        for part in srcset.split(","):
            part = part.strip()
            bits = part.split()
            if len(bits) < 2:
                continue
            width = self._extract_width(bits[1])
            max_width = max(max_width, width)
        return max_width

    def _extract_width(self, token: str) -> int:
        match = re.search(r"(\d+)w", token)
        return int(match.group(1)) if match else 0

    def _upgrade_url(self, url: str) -> str:
        upgraded = url
        upgraded = re.sub(r"/s\d+x\d+/", "/s1080x1080/", upgraded)
        upgraded = re.sub(r"(_s|-sm|_small|-small|thumb)", "large", upgraded, flags=re.IGNORECASE)
        upgraded = self._strip_size_params(upgraded)
        return upgraded

    def _strip_size_params(self, url: str) -> str:
        parsed = urlparse(url)
        if not parsed.query:
            return url
        params = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in ("w", "h", "width", "height")]
        query = urlencode(params)
        return urlunparse(parsed._replace(query=query))

    def _download_candidates(
        self,
        candidates: list[tuple[str, int]],
        folder: Path,
        headers: dict[str, str],
        limit: int,
        progress_cb,
    ) -> int:
        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/avif"}
        icon_sizes = {16, 32, 48, 64, 96, 128, 150}
        saved = 0
        seen_hashes: set[str] = set()
        saved_urls: set[str] = set()

        def attempt(min_pixels: int, min_bytes: int, max_ratio: float) -> None:
            nonlocal saved
            for url, _score in candidates:
                if saved >= limit:
                    break
                if url in saved_urls:
                    continue
                progress_cb(f"Downloading {saved + 1}/{limit}")
                try:
                    resp = requests.get(url, headers=headers, timeout=20)
                    if resp.status_code != 200:
                        continue
                    content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
                    if content_type not in allowed_types:
                        continue
                    data = resp.content
                    if len(data) < min_bytes:
                        continue
                    image = Image.open(io.BytesIO(data))
                    width, height = image.size
                    if width * height < min_pixels:
                        continue
                    if width == height and width in icon_sizes:
                        continue
                    ratio = max(width, height) / max(1, min(width, height))
                    if ratio >= max_ratio:
                        continue
                    digest = hashlib.sha256(data).hexdigest()
                    if digest in seen_hashes:
                        continue
                    seen_hashes.add(digest)

                    name = Path(urlparse(url).path).name or f"image_{saved + 1}.jpg"
                    target = self._unique_path(folder, name)
                    with open(target, "wb") as handle:
                        handle.write(data)
                    saved_urls.add(url)
                    saved += 1
                except Exception:
                    continue

        attempt(min_pixels=40000, min_bytes=5 * 1024, max_ratio=10.0)
        if saved < min(3, limit):
            attempt(min_pixels=10000, min_bytes=2 * 1024, max_ratio=20.0)

        return saved

    def _unique_path(self, folder: Path, name: str) -> Path:
        target = folder / name
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix or ".jpg"
        idx = 1
        while True:
            candidate = folder / f"{stem}_{idx}{suffix}"
            if not candidate.exists():
                return candidate
            idx += 1
