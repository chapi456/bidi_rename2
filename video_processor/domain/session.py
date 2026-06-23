"""
File: session.py
Path: video_processor/domain/session.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

log = logging.getLogger("domain.session")


@dataclass
class SessionEntry:
    """Entrée légère dans la liste de session — VideoFile chargé à la demande."""
    physical_path:  Path
    short_name:     str
    long_name:      str          # enrichi #toCut.txt
    complement:     str = ""     # partie #toCut.txt (vide si aucune)


class VideoSession:
    """Liste ordonnée de fichiers de la session. Aucune logique métier."""

    def __init__(self, entries: list[SessionEntry], config: dict):
        log.debug("BOUCHON VideoSession.__init__(%d entrées)", len(entries))
        self._entries:  list[SessionEntry] = entries
        self._config:   dict               = config
        self._index:    int                = 0

    # ── Navigation ────────────────────────────────────────────────────────

    @property
    def current_entry(self) -> Optional[SessionEntry]:
        if not self._entries:
            return None
        return self._entries[self._index]

    @property
    def current_index(self) -> int:
        return self._index

    @property
    def total(self) -> int:
        return len(self._entries)

    def set_current_by_path(self, path: Path) -> bool:
        """Positionne le curseur sur le fichier correspondant à path.
        Retourne False si non trouvé (l'entrée est ajoutée en tête).
        """
        log.debug("BOUCHON VideoSession.set_current_by_path(%s)", path)
        resolved = path.resolve()
        for i, e in enumerate(self._entries):
            if e.physical_path.resolve() == resolved:
                self._index = i
                return True
        # Fichier absent de la liste → insérer en tête
        log.debug("BOUCHON   → fichier absent, insertion en tête")
        self._entries.insert(0, SessionEntry(
            physical_path=path,
            short_name=path.name,
            long_name=path.name,
        ))
        self._index = 0
        return False

    def advance(self) -> bool:
        """Avance au fichier suivant. Retourne False si déjà au dernier."""
        log.debug("BOUCHON VideoSession.advance() index=%d/%d",
                  self._index, self.total - 1)
        if self._index >= self.total - 1:
            return False
        self._index += 1
        return True

    def go_to(self, index: int) -> bool:
        """Positionne sur l'index donné. Retourne False si hors bornes."""
        log.debug("BOUCHON VideoSession.go_to(%d)", index)
        if 0 <= index < self.total:
            self._index = index
            return True
        return False

    # ── Accès liste ───────────────────────────────────────────────────────

    def all_entries(self) -> list[SessionEntry]:
        log.debug("BOUCHON VideoSession.all_entries()")
        return list(self._entries)

    def refresh(self, scanner) -> None:
        """Rescanne les répertoires et met à jour la liste sans perdre le curseur."""
        log.debug("BOUCHON VideoSession.refresh(scanner)")
        # À implémenter : rescanner, merger avec _entries existants,
        # repositionner _index sur le même fichier physique
