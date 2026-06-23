"""
File: directory_scanner.py
Path: video_processor/infra/directory_scanner.py

Version: 1.0.0
Date: 2026-06-23

Changelog:
- 1.0.0 (2026-06-23): Réécriture — singleton lazy, property entries, refresh auto
  * DirectoryScanner.get() retourne le singleton (créé si absent)
  * .entries : property lazy — scanne au premier accès, rafraîchit si mtime change
  * .get_entry(index) : accès direct à un SessionEntry par position
  * .get_entry_by_path(path) : recherche par chemin physique
  * Pas de config passé : utilisé AppConfig.instance() en interne
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger("infra.directory_scanner")

VIDEO_EXT = {'.mp4', '.mkv', '.avi', '.mov', '.ts', '.m2ts', '.wmv', '.flv'}

# Singleton module-level
_instance: Optional[DirectoryScanner] = None


class DirectoryScanner:
    """Scanne les répertoires configurés et maintient la liste des SessionEntry.

    Singleton : utiliser DirectoryScanner.get() plutôt que le constructeur.

    La propriété .entries est lazy :
    - Premier accès : scanne tous les répertoires configurés.
    - Accès suivants : vérifie si les répertoires ont changé (mtime) ;
      si oui, rescanne et met à jour la liste.
    """

    def __init__(self) -> None:
        # Import ici pour éviter la dépendance circulaire au niveau module
        from video_processor.domain.session import SessionEntry  # noqa: F401
        self._entries:     list = []          # list[SessionEntry]
        self._dir_mtimes:  dict = {}          # {Path: float}
        self._scanned:     bool = False

    # ── Singleton ─────────────────────────────────────────────────────

    @classmethod
    def get(cls) -> "DirectoryScanner":
        """Retourne le singleton. Crée si absent."""
        global _instance
        if _instance is None:
            _instance = cls()
        return _instance

    # ── Propriété principale ────────────────────────────────────────────

    @property
    def entries(self) -> list:
        """Liste des SessionEntry. Lazy + auto-refresh si les répertoires ont changé."""
        if not self._scanned or self._directories_changed():
            self._scan()
        return list(self._entries)   # copie défensive

    # ── Accès individuels ───────────────────────────────────────────────

    def get_entry(self, index: int) -> Optional[object]:
        """Retourne le SessionEntry à la position index, ou None si hors bornes."""
        entries = self.entries
        if 0 <= index < len(entries):
            return entries[index]
        return None

    def get_entry_by_path(self, path: Path) -> Optional[object]:
        """Retourne le SessionEntry correspondant à path, ou None si absent."""
        resolved = path.resolve()
        for e in self.entries:
            if e.physical_path.resolve() == resolved:
                return e
        return None

    def get_count(self) -> int:
        """Nombre d'entrées dans la liste courante."""
        return len(self.entries)

    def force_refresh(self) -> None:
        """Force un rescan immédiat (ex : après un renommage)."""
        log.debug("DirectoryScanner.force_refresh()")
        self._scanned = False
        self._dir_mtimes.clear()
        self._scan()

    # ── Scan interne ─────────────────────────────────────────────────────

    def _scan(self) -> None:
        """Scanne tous les répertoires configurés.

        Pour chaque répertoire :
        1. Lit #toCut.txt via TocutFile.load(dir)
        2. Itère les fichiers vidéo triés (ordre alphabétique)
        3. Construit un SessionEntry par fichier
        """
        from video_processor.infra.config_loader import AppConfig
        from video_processor.infra.tocut_rw      import TocutFile
        from video_processor.domain.session       import SessionEntry

        cfg  = AppConfig.instance()
        dirs = self._resolve_directories(cfg)

        all_entries: list[SessionEntry] = []
        new_mtimes: dict = {}

        for dir_path in dirs:
            if not dir_path.is_dir():
                log.warning("Répertoire absent, ignoré : %s", dir_path)
                continue

            new_mtimes[dir_path] = dir_path.stat().st_mtime
            tocut = TocutFile.load(dir_path / cfg.tocut_filename)

            for fpath in sorted(dir_path.iterdir()):
                if fpath.suffix.lower() not in VIDEO_EXT:
                    continue
                short_name = fpath.name
                complement = tocut.get(short_name)   # "" si absent
                if complement:
                    # long_name = stem + complement + ext
                    long_name = fpath.stem + complement + fpath.suffix
                else:
                    long_name = short_name

                all_entries.append(SessionEntry(
                    physical_path=fpath,
                    short_name=short_name,
                    long_name=long_name,
                    complement=complement,
                ))

        self._entries    = all_entries
        self._dir_mtimes = new_mtimes
        self._scanned    = True
        log.debug("%d fichiers vidéo trouvés dans %d répertoires",
                  len(all_entries), len(dirs))

    def _directories_changed(self) -> bool:
        """Retourne True si au moins un répertoire a un mtime différent."""
        from video_processor.infra.config_loader import AppConfig
        cfg  = AppConfig.instance()
        dirs = self._resolve_directories(cfg)
        for d in dirs:
            if not d.is_dir():
                continue
            current_mtime = d.stat().st_mtime
            if self._dir_mtimes.get(d, -1) != current_mtime:
                log.debug("Répertoire modifié, rescan nécessaire : %s", d)
                return True
        return False

    @staticmethod
    def _resolve_directories(cfg) -> list:
        """Retourne la liste des Path valides depuis la config."""
        result = []
        for d in cfg.directories:
            p = Path(d)
            if not p.is_absolute():
                p = Path(__file__).resolve().parent.parent.parent / p
            result.append(p)
        return result
