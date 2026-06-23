"""
File: web_view.py
Path: video_processor/ui/web_view.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Bouchon — mode web non implémenté
"""

from __future__ import annotations
import logging
from .base_view import BaseView

log = logging.getLogger("ui.web_view")


class WebView(BaseView):
    """Vue web (Flask/FastAPI) — non implémentée."""

    def run(self) -> None:
        log.warning("WebView non implémentée — mode web indisponible.")
        raise NotImplementedError("WebView non implémentée")