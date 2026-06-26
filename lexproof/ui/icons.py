"""SVG icon definitions for the LexProof UI.

Provides a class of static methods returning SVG markup strings,
plus helper functions to retrieve icons by name or create QIcon instances.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QImage, QPixmap


class SvgIcons:
    """SVG icon definitions as Python string-returning class methods."""

    @staticmethod
    def file() -> str:
        """Generic file icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
            '<polyline points="14 2 14 8 20 8"/>'
            '</svg>'
        )

    @staticmethod
    def folder() -> str:
        """Folder icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
            '</svg>'
        )

    @staticmethod
    def image() -> str:
        """Image file icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>'
            '<circle cx="8.5" cy="8.5" r="1.5"/>'
            '<polyline points="21 15 16 10 5 21"/>'
            '</svg>'
        )

    @staticmethod
    def text() -> str:
        """Text file icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
            '<polyline points="14 2 14 8 20 8"/>'
            '<line x1="16" y1="13" x2="8" y2="13"/>'
            '<line x1="16" y1="17" x2="8" y2="17"/>'
            '<polyline points="10 9 9 9 8 9"/>'
            '</svg>'
        )

    @staticmethod
    def pdf() -> str:
        """PDF file icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
            '<polyline points="14 2 14 8 20 8"/>'
            '<path d="M9 15h6"/>'
            '<path d="M9 11h1"/>'
            '<path d="M14 11h1"/>'
            '</svg>'
        )

    @staticmethod
    def video() -> str:
        """Video file icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<polygon points="23 7 16 12 23 17 23 7"/>'
            '<rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>'
            '</svg>'
        )

    @staticmethod
    def archive() -> str:
        """Zip/archive icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M21 8v13H3V3h12"/>'
            '<path d="M14 3v5h7"/>'
            '<line x1="10" y1="12" x2="10" y2="12.01"/>'
            '<line x1="10" y1="16" x2="10" y2="16.01"/>'
            '<line x1="10" y1="20" x2="10" y2="20.01"/>'
            '</svg>'
        )

    @staticmethod
    def hash() -> str:
        """Hash/integrity icon (# symbol)."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<line x1="4" y1="9" x2="20" y2="9"/>'
            '<line x1="4" y1="15" x2="20" y2="15"/>'
            '<line x1="10" y1="3" x2="8" y2="21"/>'
            '<line x1="16" y1="3" x2="14" y2="21"/>'
            '</svg>'
        )

    @staticmethod
    def timeline() -> str:
        """Timeline/clock icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="12" r="10"/>'
            '<polyline points="12 6 12 12 16 14"/>'
            '</svg>'
        )

    @staticmethod
    def ocr() -> str:
        """OCR/text extraction icon (document with magnifying glass)."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
            '<polyline points="14 2 14 8 20 8"/>'
            '<line x1="16" y1="13" x2="8" y2="13"/>'
            '<line x1="16" y1="17" x2="8" y2="17"/>'
            '<circle cx="18" cy="18" r="3"/>'
            '<line x1="20.5" y1="20.5" x2="22" y2="22"/>'
            '</svg>'
        )

    @staticmethod
    def report() -> str:
        """Report/chart icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<line x1="18" y1="20" x2="18" y2="10"/>'
            '<line x1="12" y1="20" x2="12" y2="4"/>'
            '<line x1="6" y1="20" x2="6" y2="14"/>'
            '</svg>'
        )

    @staticmethod
    def shield() -> str:
        """Shield/protection icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
            '</svg>'
        )

    @staticmethod
    def blockchain() -> str:
        """Blockchain/chain icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="1" y="6" width="7" height="7" rx="1"/>'
            '<rect x="16" y="6" width="7" height="7" rx="1"/>'
            '<rect x="8.5" y="6" width="7" height="7" rx="1" transform="rotate(45 12 9.5)"/>'
            '<line x1="8" y1="13" x2="16" y2="13"/>'
            '<line x1="8" y1="6" x2="16" y2="6"/>'
            '</svg>'
        )

    @staticmethod
    def settings() -> str:
        """Gear/settings icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="12" r="3"/>'
            '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
            '</svg>'
        )

    @staticmethod
    def add() -> str:
        """Plus/add icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<line x1="12" y1="5" x2="12" y2="19"/>'
            '<line x1="5" y1="12" x2="19" y2="12"/>'
            '</svg>'
        )

    @staticmethod
    def remove() -> str:
        """Minus/remove icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<line x1="5" y1="12" x2="19" y2="12"/>'
            '</svg>'
        )

    @staticmethod
    def search() -> str:
        """Magnifying glass icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="11" cy="11" r="8"/>'
            '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
            '</svg>'
        )

    @staticmethod
    def close() -> str:
        """X/close icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<line x1="18" y1="6" x2="6" y2="18"/>'
            '<line x1="6" y1="6" x2="18" y2="18"/>'
            '</svg>'
        )

    @staticmethod
    def check() -> str:
        """Checkmark icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<polyline points="20 6 9 17 4 12"/>'
            '</svg>'
        )

    @staticmethod
    def warning() -> str:
        """Warning triangle icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
            '<line x1="12" y1="9" x2="12" y2="13"/>'
            '<line x1="12" y1="17" x2="12.01" y2="17"/>'
            '</svg>'
        )

    @staticmethod
    def error() -> str:
        """Error X icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="12" r="10"/>'
            '<line x1="15" y1="9" x2="9" y2="15"/>'
            '<line x1="9" y1="9" x2="15" y2="15"/>'
            '</svg>'
        )

    @staticmethod
    def info() -> str:
        """Info circle icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="12" r="10"/>'
            '<line x1="12" y1="16" x2="12" y2="12"/>'
            '<line x1="12" y1="8" x2="12.01" y2="8"/>'
            '</svg>'
        )

    @staticmethod
    def drag_handle() -> str:
        """Drag handle dots icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="9" cy="5" r="1"/><circle cx="9" cy="12" r="1"/>'
            '<circle cx="9" cy="19" r="1"/>'
            '<circle cx="15" cy="5" r="1"/><circle cx="15" cy="12" r="1"/>'
            '<circle cx="15" cy="19" r="1"/>'
            '</svg>'
        )

    @staticmethod
    def menu() -> str:
        """Hamburger menu icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<line x1="3" y1="12" x2="21" y2="12"/>'
            '<line x1="3" y1="6" x2="21" y2="6"/>'
            '<line x1="3" y1="18" x2="21" y2="18"/>'
            '</svg>'
        )

    @staticmethod
    def sidebar() -> str:
        """Sidebar toggle icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>'
            '<line x1="9" y1="3" x2="9" y2="21"/>'
            '</svg>'
        )

    @staticmethod
    def log() -> str:
        """Terminal/log icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<polyline points="4 17 10 11 4 5"/>'
            '<line x1="12" y1="19" x2="20" y2="19"/>'
            '</svg>'
        )

    @staticmethod
    def export() -> str:
        """Export/share icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
            '<polyline points="17 8 12 3 7 8"/>'
            '<line x1="12" y1="3" x2="12" y2="15"/>'
            '</svg>'
        )

    @staticmethod
    def import_icon() -> str:
        """Import icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
            '<polyline points="7 10 12 15 17 10"/>'
            '<line x1="12" y1="15" x2="12" y2="3"/>'
            '</svg>'
        )

    @staticmethod
    def case_icon() -> str:
        """Briefcase icon."""
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>'
            '<path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>'
            '</svg>'
        )


_ICON_MAP: dict[str, callable] = {
    "file": SvgIcons.file,
    "folder": SvgIcons.folder,
    "image": SvgIcons.image,
    "text": SvgIcons.text,
    "pdf": SvgIcons.pdf,
    "video": SvgIcons.video,
    "archive": SvgIcons.archive,
    "hash": SvgIcons.hash,
    "timeline": SvgIcons.timeline,
    "ocr": SvgIcons.ocr,
    "report": SvgIcons.report,
    "shield": SvgIcons.shield,
    "blockchain": SvgIcons.blockchain,
    "settings": SvgIcons.settings,
    "add": SvgIcons.add,
    "remove": SvgIcons.remove,
    "search": SvgIcons.search,
    "close": SvgIcons.close,
    "check": SvgIcons.check,
    "warning": SvgIcons.warning,
    "error": SvgIcons.error,
    "info": SvgIcons.info,
    "drag_handle": SvgIcons.drag_handle,
    "menu": SvgIcons.menu,
    "sidebar": SvgIcons.sidebar,
    "log": SvgIcons.log,
    "export": SvgIcons.export,
    "import": SvgIcons.import_icon,
    "case": SvgIcons.case_icon,
}


def get_icon(name: str) -> str:
    """Return the SVG string for the icon with the given name.

    Args:
        name: Icon name (e.g. ``"file"``, ``"settings"``).

    Returns:
        SVG markup string.

    Raises:
        KeyError: If the icon name is not recognized.
    """
    try:
        return _ICON_MAP[name]()
    except KeyError:
        available = ", ".join(sorted(_ICON_MAP))
        raise KeyError(
            f"Unknown icon '{name}'. Available: {available}"
        ) from None


def create_icon(name: str, size: int = 24) -> QIcon:
    """Create a QIcon from the named SVG icon.

    Args:
        name: Icon name (e.g. ``"file"``, ``"settings"``).
        size: Pixel size for the icon.

    Returns:
        A QIcon rendered from the SVG.
    """
    try:
        svg_data = QByteArray(get_icon(name).encode("utf-8"))
        image = QImage.fromData(svg_data)
        if image.isNull():
            return QIcon()
        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            return QIcon()
        return QIcon(pixmap.scaled(size, size))
    except Exception:
        return QIcon()
