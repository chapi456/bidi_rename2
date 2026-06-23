"""
File: tocut_rw.py
Path: video_processor/infra/tocut_rw.py

Version: 1.0.0
Date: 2026-06-23

Changelog:
- 1.0.0 (2026-06-23): Implémentation complète — TocutFile objet avec état
  * TocutFile.load(path) : factory + lecture lazy
  * .get(short_name) : retourne complement ou "" si absent
  * .set(short_name, complement) : upsert en mémoire, retourne self
  * .remove(short_name) : suppression en mémoire, retourne self
  * .save() : écriture atomique (temp + os.replace) format 2 lignes
  * Auto-reload si mtime change entre deux .get()
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Dict

log = logging.getLogger("infra.tocut_rw")


class TocutFile:
    """Représentation en mémoire du fichier #toCut.txt.

    Format physique (2 lignes par entrée) :
        MonFilm.mp4
         - style - CROP(1024x576) - 06-19(81)(Scene)(0x0)

    stem(ligne1) + ligne2 + ext(ligne1) = long_name parseable par FilenameParser.

    Usage :
        tocut = TocutFile.load(path / "#toCut.txt")
        complement = tocut.get("MonFilm.mp4")       # "" si absent
        tocut.set("MonFilm.mp4", " - CROP(...)").save()
    """

    def __init__(self, path: Path) -> None:
        self._path:   Path           = path
        self._data:   Dict[str, str] = {}    # {short_name: complement}
        self._mtime:  float          = 0.0
        self._loaded: bool           = False

    # ── Factory ──────────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: Path) -> "TocutFile":
        """Crée un TocutFile et charge le contenu si le fichier existe."""
        obj = cls(path)
        if path.exists():
            obj._read()
        else:
            obj._loaded = True   # fichier absent = dict vide valide
        return obj

    # ── Accès ─────────────────────────────────────────────────────────────

    def get(self, short_name: str) -> str:
        """Retourne le complement associé à short_name, ou "" si absent.
        Auto-reload si le fichier a été modifié sur disque.
        """
        self._reload_if_needed()
        return self._data.get(short_name, "")

    def set(self, short_name: str, complement: str) -> "TocutFile":
        """Upsert en mémoire. Retourne self pour chaînage."""
        self._reload_if_needed()
        self._data[short_name] = self._normalize(complement)
        log.debug("TocutFile.set(%s)", short_name)
        return self

    def remove(self, short_name: str) -> "TocutFile":
        """Supprime l'entrée en mémoire. Retourne self pour chaînage."""
        self._reload_if_needed()
        self._data.pop(short_name, None)
        log.debug("TocutFile.remove(%s)", short_name)
        return self

    def has(self, short_name: str) -> bool:
        """True si short_name est présent."""
        self._reload_if_needed()
        return short_name in self._data

    def all_entries(self) -> Dict[str, str]:
        """Copie du dict {short_name: complement}."""
        self._reload_if_needed()
        return dict(self._data)

    # ── Persistance ───────────────────────────────────────────────────────

    def save(self) -> None:
        """Écrit en mémoire → disque, format 2 lignes, écriture atomique.

        Ordre alphabétique des short_name pour un diff git lisible.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for short_name in sorted(self._data):
            if lines:
                lines.append("")        # ligne vide séparatrice
            lines.append(short_name)
            lines.append(self._data[short_name])

        content = "\n".join(lines)
        if content:
            content += "\n"

        # Écriture atomique
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
            os.replace(tmp, self._path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

        self._mtime = self._path.stat().st_mtime
        log.debug("TocutFile.save() → %s (%d entrées)", self._path, len(self._data))

    # ── Lecture interne ───────────────────────────────────────────────────

    def _read(self) -> None:
        """Parse le fichier depuis le disque."""
        data: Dict[str, str] = {}
        try:
            raw = self._path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            log.error("Impossible de lire %s : %s", self._path, exc)
            self._loaded = True
            return

        i = 0
        while i < len(raw):
            line = raw[i].strip()

            if not line or line.startswith("#"):
                i += 1
                continue

            # Ligne 1 : short_name (pas de leading " - ", a une extension)
            if not line.startswith(" - ") and "." in line:
                short_name = line
                # Chercher le complément sur la prochaine ligne non vide
                j = i + 1
                while j < len(raw) and raw[j].strip() == "":
                    j += 1
                if j < len(raw) and raw[j].startswith(" - "):
                    data[short_name] = raw[j].rstrip()
                    i = j + 1
                    continue
                else:
                    log.warning("#toCut.txt : pas de complément pour %r", short_name)
                    i += 1
                    continue

            i += 1

        self._data   = data
        self._mtime  = self._path.stat().st_mtime
        self._loaded = True
        log.debug("TocutFile lu : %d entrées (%s)", len(data), self._path)

    def _reload_if_needed(self) -> None:
        if not self._loaded:
            self._read()
            return
        if self._path.exists():
            if self._path.stat().st_mtime > self._mtime:
                log.debug("TocutFile : modifié sur disque, rechargement")
                self._read()

    @staticmethod
    def _normalize(complement: str) -> str:
        """Garantit que complement commence par ' - '."""
        c = complement.strip()
        if not c.startswith("- "):
            return " - " + c
        return " " + c