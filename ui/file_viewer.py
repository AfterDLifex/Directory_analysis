"""In-app file viewer: text, image, and hex dump preview."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QScrollArea, QVBoxLayout,
    QWidget,
)

from .icons import get_svg_pixmap

MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_HEX_BYTES = 64 * 1024

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico"}
_TEXT_EXTS = {
    ".txt", ".log", ".md", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml",
    ".html", ".htm", ".css", ".scss", ".sass", ".less", ".js", ".ts", ".jsx",
    ".tsx", ".vue", ".svelte", ".py", ".rb", ".go", ".rs", ".java", ".c",
    ".cpp", ".cc", ".h", ".hpp", ".cs", ".php", ".sh", ".bash", ".zsh",
    ".ps1", ".sql", ".ini", ".cfg", ".conf", ".toml", ".env", ".gitignore",
    ".dockerfile", ".makefile", ".cmake", ".bat", ".cmd",
}


class FileViewer(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_path: str | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        self.header = QFrame()
        self.header.setObjectName("InsightCard")
        self.header.setProperty("severity", "info")
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(10)

        self.file_icon = QLabel()
        self.file_icon.setPixmap(get_svg_pixmap("files", size=18, color="#93c5fd"))
        hl.addWidget(self.file_icon)

        info_box = QVBoxLayout()
        info_box.setSpacing(1)
        self.file_name = QLabel("No file selected")
        self.file_name.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 700;")
        self.file_meta = QLabel("Pick any file from the tree or tables to preview it here.")
        self.file_meta.setStyleSheet("color: #8da2c0; font-size: 11px;")
        info_box.addWidget(self.file_name)
        info_box.addWidget(self.file_meta)
        hl.addLayout(info_box, 1)
        outer.addWidget(self.header)

        self.body = QFrame()
        self.body.setObjectName("GlassPanel")
        bl = QVBoxLayout(self.body)
        bl.setContentsMargins(0, 0, 0, 0)

        self.text_view = QPlainTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.text_view.setFont(QFont("JetBrains Mono", 10))
        self.text_view.setStyleSheet(
            "background: rgba(10,15,26,0.9); color: #e2e8f0; "
            "border: none; padding: 12px;")

        self.image_area = QScrollArea()
        self.image_area.setWidgetResizable(True)
        self.image_area.setFrameShape(QFrame.NoFrame)
        self.image_area.setAlignment(Qt.AlignCenter)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_area.setWidget(self.image_label)

        self.message = QLabel("")
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color: #64748b; font-size: 13px; padding: 40px;")

        for w in (self.text_view, self.image_area, self.message):
            bl.addWidget(w)
            w.setVisible(False)

        outer.addWidget(self.body, 1)
        self.clear()

    def clear(self) -> None:
        self._current_path = None
        self.file_name.setText("No file selected")
        self.file_meta.setText("Pick any file from the tree or tables to preview it here.")
        self._show_message("No file selected.")

    def load_file(self, path: str) -> None:
        self._current_path = path
        p = Path(path)

        if not p.exists():
            self._show_message(f"File not found: {path}")
            self._set_header(p.name, "Missing on disk", "warning")
            return
        try:
            st = p.stat()
        except OSError as exc:
            self._show_message(f"Cannot read file: {exc}")
            self._set_header(p.name, str(exc), "warning")
            return

        size = st.st_size
        ext = p.suffix.lower()
        size_str = _human_size(size)
        self._set_header(p.name, f"{size_str}  ·  {p.parent}", "info")

        if ext in _IMAGE_EXTS and size <= MAX_IMAGE_BYTES:
            self._render_image(p)
            return
        if _looks_like_text(p, ext) and size <= MAX_TEXT_BYTES:
            self._render_text(p)
            return
        if size <= MAX_HEX_BYTES:
            self._render_hex(p)
            return

        self._show_message(
            f"Preview not available for this file.\n\n"
            f"Size: {size_str}\nType: {ext or 'unknown'}\n"
            f"Open it externally to view its contents.")

    def _render_text(self, p: Path) -> None:
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                data = fh.read()
        except OSError as exc:
            self._show_message(f"Failed to read text: {exc}")
            return
        self._switch_to(self.text_view)
        self.text_view.setPlainText(data)

    def _render_image(self, p: Path) -> None:
        pix = QPixmap(str(p))
        if pix.isNull():
            self._show_message("Image could not be decoded.")
            return
        max_w = max(self.image_area.viewport().width() - 20, 320)
        if pix.width() > max_w:
            pix = pix.scaledToWidth(max_w, Qt.SmoothTransformation)
        self.image_label.setPixmap(pix)
        self.image_label.resize(pix.size())
        self._switch_to(self.image_area)

    def _render_hex(self, p: Path) -> None:
        try:
            with open(p, "rb") as fh:
                data = fh.read(MAX_HEX_BYTES)
        except OSError as exc:
            self._show_message(f"Failed to read binary: {exc}")
            return
        lines = []
        for off in range(0, len(data), 16):
            chunk = data[off:off + 16]
            hex_part = " ".join(f"{b:02x}" for b in chunk).ljust(16 * 3 - 1)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"{off:08x}  {hex_part}  |{ascii_part}|")
        self._switch_to(self.text_view)
        self.text_view.setPlainText(
            f"[hex preview — first {len(data):,} bytes]\n\n" + "\n".join(lines))

    def _switch_to(self, widget: QWidget) -> None:
        for w in (self.text_view, self.image_area, self.message):
            w.setVisible(w is widget)

    def _show_message(self, text: str) -> None:
        self.message.setText(text)
        self._switch_to(self.message)

    def _set_header(self, name: str, meta: str, kind: str = "info") -> None:
        self.file_name.setText(name)
        self.file_meta.setText(meta)
        self.header.setProperty("severity", kind)
        self.header.style().unpolish(self.header)
        self.header.style().polish(self.header)


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024.0
    return f"{n:.1f} PB"


def _looks_like_text(p: Path, ext: str) -> bool:
    if ext in _TEXT_EXTS:
        return True
    if ext == "":
        return True
    try:
        with open(p, "rb") as fh:
            chunk = fh.read(1024)
    except OSError:
        return False
    if b"\x00" in chunk:
        return False
    printable = sum(1 for b in chunk if 9 <= b <= 13 or 32 <= b < 127 or b >= 128)
    return printable / max(len(chunk), 1) > 0.85