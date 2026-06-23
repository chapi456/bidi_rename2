"""
File: base_view.py
Path: video_processor/ui/base_view.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from video_processor.controller.session_controller import SessionController

log = logging.getLogger("ui.base_view")


class BaseView(ABC):
    """Interface commune à toutes les vues (CLI, Tkinter, Web)."""

    def bind(self, controller: "SessionController") -> None:
        """Relie la vue au contrôleur. Appelé avant run()."""
        log.debug("BOUCHON BaseView.bind()")
        self._ctrl = controller
        controller.subscribe(self._on_event)

    def _send(self, cmd: object) -> None:
        """Raccourci pour envoyer une commande au contrôleur."""
        self._ctrl.send(cmd)

    @abstractmethod
    def _on_event(self, event: object) -> None:
        """Reçoit tous les événements du contrôleur. Dispatcher interne."""

    @abstractmethod
    def run(self) -> None:
        """Démarre la boucle principale (bloquant)."""
