"""
File: web_view.py
Path: video_processor/ui/web_view.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Bouchon — mode web non implémenté, satisfait l'interface BaseView
"""

from __future__ import annotations

import logging
from .base_view import BaseView

log = logging.getLogger("ui.web_view")


class WebView(BaseView):
    """Vue web (Flask/FastAPI) — non implémentée.

    Bouchon qui satisfait l'interface BaseView pour éviter
    l'erreur d'instanciation de classe abstraite.
    """

    def _on_event(self, event: object) -> None:
        """Réception événements contrôleur — non implémenté."""
        log.debug("BOUCHON WebView._on_event(%s)", type(event).__name__)

    def run(self) -> None:
        """Boucle principale — non implémentée."""
        log.warning("WebView non implémentée — mode web indisponible.")
        raise NotImplementedError("WebView non implémentée")