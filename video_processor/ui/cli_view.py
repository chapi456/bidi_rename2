"""
File: cli_view.py
Path: video_processor/ui/cli_view.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging

from .base_view import BaseView
from video_processor.controller import commands as CMD
from video_processor.controller import events as EVT

log = logging.getLogger("ui.cli_view")


class CliView(BaseView):
    """Vue texte. Boucle stdin → CmdXxx → contrôleur."""

    def _on_event(self, event: object) -> None:
        log.debug("BOUCHON CliView._on_event(%s)", type(event).__name__)
        if isinstance(event, EVT.EvtStatus):
            print(f"  {event.text}")
        elif isinstance(event, EVT.EvtTitle):
            print(f"\n{'\u2550'*58}\n  {event.text}\n{'\u2550'*58}")
        elif isinstance(event, EVT.EvtFrameReady):
            log.debug("BOUCHON CliView: frame ch%d prête (pas d'affichage CLI)",
                      event.chapter_index)
        elif isinstance(event, EVT.EvtThumbReady):
            log.debug("BOUCHON CliView: thumb ch%d prête (ignorée en CLI)",
                      event.chapter_index)

    def run(self) -> None:
        log.debug("BOUCHON CliView.run()")
        print("bidi_rename2 — mode CLI")
        self._repl()

    def _repl(self) -> None:
        """Boucle de lecture stdin → dispatch commandes."""
        log.debug("BOUCHON CliView._repl()")
        while True:
            try:
                raw = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                self._send(CMD.CmdQuit())
                break
            if not raw:
                continue
            cmd = self._parse_input(raw)
            if cmd:
                self._send(cmd)

    def _parse_input(self, raw: str) -> object | None:
        """Convertit une ligne texte en commande.

        Verbes supportés (à implémenter) :
          j <n>           → CmdJump(n)
          s <ts>          → CmdSeekAbs(ts)
          +<n> / -<n>     → CmdSeekDelta(n)
          crop            → CmdAddCrop()
          nocrop          → CmdDelCrop()
          save            → CmdSave()
          next            → CmdNextFile()
          q / quit        → CmdQuit()
        """
        log.debug("BOUCHON CliView._parse_input(%r)", raw)
        toks = raw.split(None, 1)
        verb = toks[0].lower()
        # À implémenter : mapping verb → CmdXxx
        log.debug("BOUCHON   verbe non reconnu : %r", verb)
        return None
