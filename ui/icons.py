"""SVG Vector Icon generator and cache. All glyphs are 24x24, 2px stroke."""

from __future__ import annotations

from typing import Dict, Optional
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_STROKE = 'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
_STROKE_BOLD = 'fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"'

SVG_ICONS: Dict[str, str] = {
    "overview": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<rect x="3" y="3" width="7" height="7" rx="1.5"/>'
                '<rect x="14" y="3" width="7" height="7" rx="1.5"/>'
                '<rect x="14" y="14" width="7" height="7" rx="1.5"/>'
                '<rect x="3" y="14" width="7" height="7" rx="1.5"/></svg>',
    "charts": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
              '<line x1="18" y1="20" x2="18" y2="10"/>'
              '<line x1="12" y1="20" x2="12" y2="4"/>'
              '<line x1="6" y1="20" x2="6" y2="14"/>'
              '<line x1="2" y1="20" x2="22" y2="20"/></svg>',
    "files": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
             '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
             '<polyline points="14 2 14 8 20 8"/>'
             '<line x1="16" y1="13" x2="8" y2="13"/>'
             '<line x1="16" y1="17" x2="8" y2="17"/></svg>',
    "folder": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
              '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    "duplicates": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                  '<rect x="9" y="9" width="13" height="13" rx="2"/>'
                  '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
    "insights": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<line x1="9" y1="18" x2="15" y2="18"/>'
                '<line x1="10" y1="22" x2="14" y2="22"/>'
                '<path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/></svg>',
    "export": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
              '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
              '<polyline points="7 10 12 15 17 10"/>'
              '<line x1="12" y1="15" x2="12" y2="3"/></svg>',
    "zap": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
           '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "cancel": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
              '<circle cx="12" cy="12" r="10"/>'
              '<line x1="15" y1="9" x2="9" y2="15"/>'
              '<line x1="9" y1="9" x2="15" y2="15"/></svg>',
    "search": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
              '<circle cx="11" cy="11" r="8"/>'
              '<line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "check": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE_BOLD}>'
             '<polyline points="20 6 9 17 4 12"/></svg>',
    "check-circle": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                    '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
                    '<polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "warning": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
               '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
               '<line x1="12" y1="9" x2="12" y2="13"/>'
               '<line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "alert-circle": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                    '<circle cx="12" cy="12" r="10"/>'
                    '<line x1="12" y1="8" x2="12" y2="12"/>'
                    '<line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    "info": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<circle cx="12" cy="12" r="10"/>'
            '<line x1="12" y1="16" x2="12" y2="12"/>'
            '<line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    "help": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<circle cx="12" cy="12" r="10"/>'
            '<path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>'
            '<line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "sparkles": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<path d="M12 3l1.9 5.6L19.5 10.5 13.9 12.4 12 18l-1.9-5.6L4.5 10.5l5.6-1.9z"/>'
                '<path d="M19 3l.7 2 2 .7-2 .7L19 8.5l-.7-2-2-.7 2-.7z"/></svg>',
    "star": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "shield": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
              '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "shield-check": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                    '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
                    '<polyline points="9 12 11 14 15 10"/></svg>',
    "trash": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
             '<polyline points="3 6 5 6 21 6"/>'
             '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
    "refresh": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
               '<polyline points="23 4 23 10 17 10"/>'
               '<polyline points="1 20 1 14 7 14"/>'
               '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
    "settings": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<circle cx="12" cy="12" r="3"/>'
                '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    "sliders": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
               '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>'
               '<line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>'
               '<line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>'
               '<line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/>'
               '<line x1="17" y1="16" x2="23" y2="16"/></svg>',
    "chevron-down": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                    '<polyline points="6 9 12 15 18 9"/></svg>',
    "chevron-up": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                  '<polyline points="18 15 12 9 6 15"/></svg>',
    "chevron-right": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                     '<polyline points="9 18 15 12 9 6"/></svg>',
    "chevron-left": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                    '<polyline points="15 18 9 12 15 6"/></svg>',
    "arrow-up": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<line x1="12" y1="19" x2="12" y2="5"/>'
                '<polyline points="5 12 12 5 19 12"/></svg>',
    "sort-asc": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<path d="M11 5h10M11 9h7M11 13h4"/>'
                '<path d="M3 17l3 3 3-3"/><path d="M6 18V4"/></svg>',
    "sort-desc": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                 '<path d="M11 5h4M11 9h7M11 13h10"/>'
                 '<path d="M3 7l3-3 3 3"/><path d="M6 6v14"/></svg>',
    "filter": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
              '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>',
    "more": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>'
            '<circle cx="5" cy="12" r="1"/></svg>',
    "external": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
                '<polyline points="15 3 21 3 21 9"/>'
                '<line x1="10" y1="14" x2="21" y2="3"/></svg>',
    "copy": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<rect x="9" y="9" width="13" height="13" rx="2"/>'
            '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
    "download": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
                '<polyline points="7 10 12 15 17 10"/>'
                '<line x1="12" y1="15" x2="12" y2="3"/></svg>',
    "plus": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    "minus": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
             '<line x1="5" y1="12" x2="19" y2="12"/></svg>',
    "home": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
            '<polyline points="9 22 9 12 15 12 15 22"/></svg>',
    "grid": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>'
            '<rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
    "list": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>'
            '<line x1="8" y1="18" x2="21" y2="18"/>'
            '<line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/>'
            '<line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
    "keyboard": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<rect x="2" y="6" width="20" height="12" rx="2"/>'
                '<line x1="6" y1="10" x2="6" y2="10"/><line x1="10" y1="10" x2="10" y2="10"/>'
                '<line x1="14" y1="10" x2="14" y2="10"/><line x1="18" y1="10" x2="18" y2="10"/>'
                '<line x1="8" y1="14" x2="16" y2="14"/></svg>',
    "sun": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
           '<circle cx="12" cy="12" r="4"/>'
           '<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>',
    "moon": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    "database": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
                '<path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>'
                '<path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
    "hard-drive": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                  '<line x1="22" y1="12" x2="2" y2="12"/>'
                  '<path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>'
                  '<line x1="6" y1="16" x2="6.01" y2="16"/><line x1="10" y1="16" x2="10.01" y2="16"/></svg>',
    "activity": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    "trend-up": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>'
                '<polyline points="17 6 23 6 23 12"/></svg>',
    "trend-down": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                  '<polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/>'
                  '<polyline points="17 18 23 18 23 12"/></svg>',
    "layers": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
              '<polygon points="12 2 2 7 12 12 22 7 12 2"/>'
              '<polyline points="2 17 12 22 22 17"/>'
              '<polyline points="2 12 12 17 22 12"/></svg>',
    "clock": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
             '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "calendar": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<rect x="3" y="4" width="18" height="18" rx="2"/>'
                '<line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>'
                '<line x1="3" y1="10" x2="21" y2="10"/></svg>',
    "health": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
              '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
    "image": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
             '<rect x="3" y="3" width="18" height="18" rx="2"/>'
             '<circle cx="8.5" cy="8.5" r="1.5"/>'
             '<polyline points="21 15 16 10 5 21"/></svg>',
    "video": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
             '<polygon points="23 7 16 12 23 17 23 7"/>'
             '<rect x="1" y="5" width="15" height="14" rx="2"/></svg>',
    "audio": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
             '<path d="M9 18V5l12-2v13"/>'
             '<circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
    "document": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
                '<polyline points="14 2 14 8 20 8"/>'
                '<line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    "archive": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
               '<polyline points="21 8 21 21 3 21 3 8"/>'
               '<rect x="1" y="3" width="22" height="5"/>'
               '<line x1="10" y1="12" x2="14" y2="12"/></svg>',
    "code": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<polyline points="16 18 22 12 16 6"/>'
            '<polyline points="8 6 2 12 8 18"/></svg>',
    "executable": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
                  '<circle cx="12" cy="12" r="3"/>'
                  '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    "font": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
            '<polyline points="4 7 4 4 20 4 20 7"/>'
            '<line x1="9" y1="20" x2="15" y2="20"/>'
            '<line x1="12" y1="4" x2="12" y2="20"/></svg>',
    "system": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
              '<rect x="2" y="2" width="20" height="8" rx="2"/>'
              '<rect x="2" y="14" width="20" height="8" rx="2"/>'
              '<line x1="6" y1="6" x2="6.01" y2="6"/>'
              '<line x1="6" y1="18" x2="6.01" y2="18"/></svg>',
    "other": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" {_STROKE}>'
             '<path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>',
}

_PIXMAP_CACHE: Dict[str, QPixmap] = {}
_ICON_CACHE: Dict[str, QIcon] = {}


def get_svg_raw(name: str, color: str = "#60a5fa") -> str:
    template = SVG_ICONS.get(name.lower(), SVG_ICONS["other"])
    return template.format(color=color)


def get_svg_pixmap(name: str, size: int = 20, color: str = "#60a5fa") -> QPixmap:
    key = f"{name}:{size}:{color}"
    if key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[key]
    renderer = QSvgRenderer(QByteArray(get_svg_raw(name, color).encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()
    _PIXMAP_CACHE[key] = pixmap
    return pixmap


def get_svg_icon(name: str, color: str = "#94a3b8",
                 active_color: str = "#60a5fa", size: int = 20) -> QIcon:
    key = f"icon:{name}:{color}:{active_color}:{size}"
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    normal = get_svg_pixmap(name, size, color)
    active = get_svg_pixmap(name, size, active_color)
    icon = QIcon()
    icon.addPixmap(normal, QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(active, QIcon.Mode.Normal, QIcon.State.On)
    icon.addPixmap(active, QIcon.Mode.Active)
    icon.addPixmap(active, QIcon.Mode.Selected)
    _ICON_CACHE[key] = icon
    return icon


def get_category_svg_icon(category: str, color: Optional[str] = None,
                          size: int = 18) -> QIcon:
    cat_map = {
        "Images": ("image", "#f87171"),
        "Videos": ("video", "#22d3ee"),
        "Documents": ("document", "#38bdf8"),
        "Audio": ("audio", "#34d399"),
        "Archives": ("archive", "#fbbf24"),
        "Code": ("code", "#f472b6"),
        "Executables": ("executable", "#cbd5e1"),
        "Fonts": ("font", "#818cf8"),
        "System": ("system", "#c084fc"),
        "Other": ("other", "#94a3b8"),
    }
    icon_name, default_color = cat_map.get(category, ("other", "#94a3b8"))
    return get_svg_icon(icon_name, color=color or default_color,
                        active_color="#ffffff", size=size)