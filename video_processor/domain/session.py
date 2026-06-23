"""
File: session.py
Path: video_processor/domain/session.py

Version: 1.0.0
Date: 2026-06-23

Changelog:
- 1.0.0 (2026-06-23): Singleton + découplage — VideoSession se procure le scanner seul
  * VideoSession.get() retourne le singleton
  * Plus de passage de config ni de scanner au constructeur
  * .entries : délègue à DirectoryScanner.get().entries (lazy + auto-refresh)
  * .get_entry(index), .get_count() harmonisés avec DirectoryScanner
  * .refresh() force un rescan via DirectoryScanner
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

log = logging.getLogger("domain.session")

# Singleton module-level
_instance: Optional[VideoSession] = None


@dataclass
class SessionEntry:
    """Entrée légère dans la liste de session.

    Quatre noms, chacun avec un rôle précis :

    physical_path  : chemin absolu réel sur le disque (source de vérité FS)
    short_name     : nom de fichier tel qu'il est sur le disque (stem + ext)
                     ex. "MonFilm - style.mp4"
    long_name      : nom enrichi par #toCut.txt si présent, sinon == short_name
                     ex. "MonFilm - style - CROP(1800x800) - 00-00(30)(Intro).mp4"
                     C'est ce nom qui est parsé par FilenameParser.
    complement     : partie ajoutée par #toCut.txt (vide si aucune)
                     ex. " - CROP(1800x800) - 00-00(30)(Intro)"
    target_name    : nom cible après édition (None tant que non modifié)
                     ex. "MonFilm - style - CROP(1920x1080) - 00-00(30)(Intro).mp4"
    """
    physical_path:  Path
    short_name:     str
    long_name:      str
    complement:     str          = ""
    target_name:    Optional[str] = None

    @property
    def display_name(self) -> str:
        """Nom affiché dans l'interface : long_name si enrichi, sinon short_name."""
        return self.long_name

    @property
    def directory(self) -> Path:
        """Répertoire contenant le fichier."""
        return self.physical_path.parent

    @property
    def extension(self) -> str:
        """Extension avec le point : '.mp4'"""
        return self.physical_path.suffix.lower()

    @property
    def is_dirty(self) -> bool:
        """True si target_name est défini et diffère de short_name."""
        return self.target_name is not None and self.target_name != self.short_name


class VideoSession:
    """Liste ordonnée des fichiers de la session. Curseur + navigation.

    Singleton : utiliser VideoSession.get() plutôt que le constructeur.
    La liste est obtenue via DirectoryScanner.get().entries — lazy + auto-refresh.
    """

    def __init__(self) -> None:
        self._index: int = 0

    # ── Singleton ─────────────────────────────────────────────────────

    @classmethod
    def get(cls) -> "VideoSession":
        """Retourne le singleton. Crée si absent."""
        global _instance
        if _instance is None:
            _instance = cls()
        return _instance

    # ── Accès à la liste (délégation au scanner) ─────────────────────────

    @property
    def _scanner(self):
        """Accès lazy au singleton DirectoryScanner (import local = no circular dep)."""
        from video_processor.infra.directory_scanner import DirectoryScanner
        return DirectoryScanner.get()

    @property
    def entries(self) -> list[SessionEntry]:
        """Liste courante des SessionEntry (lazy + auto-refresh via scanner)."""
        return self._scanner.entries

    def get_entry(self, index: int) -> Optional[SessionEntry]:
        """SessionEntry à la position index, ou None si hors bornes."""
        return self._scanner.get_entry(index)

    def get_count(self) -> int:
        """Nombre de fichiers dans la session."""
        return self._scanner.get_count()

    # ── Curseur courant ───────────────────────────────────────────────

    @property
    def current_entry(self) -> Optional[SessionEntry]:
        """SessionEntry courant selon le curseur."""
        return self.get_entry(self._index)

    @property
    def current_index(self) -> int:
        return self._index

    @current_index.setter
    def current_index(self, value: int) -> None:
        count = self.get_count()
        if count == 0:
            self._index = 0
            return
        self._index = max(0, min(value, count - 1))

    # ── Navigation ───────────────────────────────────────────────────

    def set_current_by_path(self, path: Path) -> bool:
        """Positionne le curseur sur le fichier correspondant à path.

        Retourne True si trouvé.
        Si absent de la liste, insère un SessionEntry temporaire en tête
        (utile pour un fichier passé en argument CLI).
        """
        entry = self._scanner.get_entry_by_path(path)
        if entry is not None:
            self._index = self.entries.index(entry)
            return True

        # Fichier absent de la liste : créer une entrée temporaire
        log.debug("Fichier hors session, insertion temporaire : %s", path)
        tmp = SessionEntry(
            physical_path=path.resolve(),
            short_name=path.name,
            long_name=path.name,
        )
        # Injection directe dans le scanner pour cohérence
        self._scanner._entries.insert(0, tmp)
        self._index = 0
        return False

    def advance(self) -> bool:
        """Avance au fichier suivant. Retourne False si déjà au dernier."""
        if self._index >= self.get_count() - 1:
            return False
        self._index += 1
        return True

    def go_back(self) -> bool:
        """Recule au fichier précédent. Retourne False si déjà au premier."""
        if self._index <= 0:
            return False
        self._index -= 1
        return True

    def go_to(self, index: int) -> bool:
        """Positionne sur l'index donné. Retourne False si hors bornes."""
        if 0 <= index < self.get_count():
            self._index = index
            return True
        return False

    def refresh(self) -> None:
        """Force un rescan des répertoires (après un renommage par ex.).
        Repositionne le curseur sur le même fichier physique si possible.
        """
        current = self.current_entry
        self._scanner.force_refresh()
        if current is not None:
            self.set_current_by_path(current.physical_path)
