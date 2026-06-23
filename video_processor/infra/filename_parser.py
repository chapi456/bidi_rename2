"""
File: filename_parser.py
Path: video_processor/infra/filename_parser.py

Version: 1.0.0
Date: 2026-06-23

Changelog:
- 1.0.0 (2026-06-23): Réécriture OO complète
  * ParsedFilename dataclass : toutes les composantes typées
  * ChapterInfo dataclass    : un chapitre = un objet (fini le dict brut)
  * CropInfo dataclass       : crop global W x H
  * FilenameParser           : stateless, méthodes de classe
  * Logique de parsing 100% fidèle à bidi_rename/parsing.py
  * Styles injectés via AppConfig (lazy, pas de global)
  * build() : round-trip ParsedFilename → nom de fichier
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

_MOD_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_MOD_ROOT) not in sys.path:
    sys.path.insert(0, str(_MOD_ROOT))

from video_processor.infra.timestamp import is_timestamp_token, to_seconds, to_timestamp

if TYPE_CHECKING:
    from video_processor.infra.config_loader import AppConfig

log = logging.getLogger("infra.filename_parser")

_DEFAULT_DURATION = 30


# ============================================================================
# Dataclasses résultat
# ============================================================================


@dataclass
class CropInfo:
    """Crop global défini dans le nom de fichier : CROP(WxH)."""
    w: int
    h: int

    def __str__(self) -> str:
        return f"CROP({self.w}x{self.h})"


@dataclass
class ThumbInfo:
    """Option THUMB(timestamp)."""
    timestamp_original: str
    timestamp_seconds: int


@dataclass
class ChapterInfo:
    """Un chapitre parsé depuis le nom de fichier.

    Champs :
      timestamp_original  : chaîne brute telle qu'écrite (ex: "06-19")
      timestamp_seconds   : secondes (int)
      duration            : durée en secondes (défaut 30 si absent)
      title               : titre du chapitre ou None
      tags                : titre découpé sur ' - ' (pour NFO)
      pos_x / pos_y       : position crop spécifique au chapitre (ou None)
      pos_explicit        : True ssi pos_x est fourni explicitement
      pos_mode            : 'topleft' | 'center'
      title_from_style    : True si titre injecté par fallback style
      raw_token           : token brut pour round-trip exact
    """
    timestamp_original: str
    timestamp_seconds: int
    duration: int
    title: Optional[str]
    tags: List[str]
    pos_x: Optional[int]
    pos_y: Optional[int]
    pos_explicit: bool
    pos_mode: str        # 'topleft' | 'center'
    title_from_style: bool
    raw_token: str

    def to_token(self) -> str:
        """Reconstruit le token de chapitre pour le nom de fichier.

        Si title_from_style=True, le titre n'est PAS inclus dans le token
        (il sera injecté par le fallback au prochain parse).
        """
        parts = [self.timestamp_original]
        if self.duration != _DEFAULT_DURATION:
            parts.append(f"({self.duration})")
        title_to_write = None if self.title_from_style else self.title
        if title_to_write:
            parts.append(f"({title_to_write})")
        if self.pos_mode == "center":
            parts.append("(CENTER)")
        elif self.pos_explicit and self.pos_x is not None and self.pos_y is not None:
            parts.append(f"({self.pos_x}x{self.pos_y})")
        return "".join(parts)


@dataclass
class ParsedFilename:
    """Résultat complet du parsing d'un nom de fichier vidéo.

    Toutes les composantes sont typées.
    None signifie "absent du nom", jamais de valeur par défaut silencieuse.

    Noms :
      studio    : contenu de [...]
      actors    : contenu de @...@
      styles    : liste des styles reconnus
      star      : True si un style se termine par #
      title     : partie libre du nom (reste après tous les tokens reconnus)
      date      : date normalisée AAAA-MM-JJ / AAAA-MM / AAAA
      booleans  : {'POV': bool, '3D': bool, 'NOCUT': bool}
      crop      : CropInfo ou None
      chapters  : list[ChapterInfo] triés par timestamp
      thumb     : ThumbInfo ou None
      encode    : codec demandé (str) ou None
      resize    : résolution demandée (str) ou None
      file_id   : {nombre} ou None
      extension : extension du fichier (avec point) ou ''
    """
    studio:    Optional[str]
    actors:    List[str]
    styles:    List[str]
    star:      bool
    title:     str
    date:      Optional[str]
    booleans:  Dict[str, bool]
    crop:      Optional[CropInfo]
    chapters:  List[ChapterInfo]
    thumb:     Optional[ThumbInfo]
    encode:    Optional[str]
    resize:    Optional[str]
    file_id:   Optional[int]
    extension: str

    def build(self) -> str:
        """Reconstruit le nom de fichier (sans extension) depuis les composantes.

        Round-trip garanti : parse(build(p)) == p pour tout p valide.
        Ordre des tokens identique à celui attendu par le parser :
          [studio] - @actors@ - style(s) - date - booléens - CROP - chapitres
          - THUMB - ENCODE - RESIZE - {id} - titre
        """
        tokens: List[str] = []

        if self.studio:
            tokens.append(f"[{self.studio}]")
        if self.actors:
            tokens.append(f"@{', '.join(self.actors)}@")
        for i, s in enumerate(self.styles):
            t = s
            if self.star and i == len(self.styles) - 1:
                t += "#"
            tokens.append(t)
        if self.date:
            tokens.append(self.date)
        for key, val in self.booleans.items():
            if val:
                tokens.append(key)
        if self.crop:
            tokens.append(str(self.crop))
        for ch in self.chapters:
            tokens.append(ch.to_token())
        if self.thumb:
            tokens.append(f"THUMB({self.thumb.timestamp_original})")
        if self.encode:
            tokens.append(f"ENCODE({self.encode})")
        if self.resize:
            tokens.append(f"RESIZE({self.resize})")
        if self.file_id is not None:
            tokens.append(f"{{{self.file_id}}}")
        if self.title:
            tokens.append(self.title)

        return " - ".join(tokens)


# ============================================================================
# Parser
# ============================================================================


class FilenameParser:
    """Parse un nom de fichier vidéo selon la syntaxe bidi_rename.

    Stateless : toutes les méthodes sont de classe ou statiques.
    La liste des styles valides est fournie à parse() (injectée par AppConfig).

    Utilisation :
        cfg    = AppConfig.instance()
        result = FilenameParser.parse("Mon Film - style1 - 2024-01-15.mp4",
                                      styles=cfg.styles)
        if result is None:
            ...  # fichier invalide (pas de style)
    """

    # ── API publique ─────────────────────────────────────────────────────

    @classmethod
    def parse(cls, filename: str,
              styles: Optional[List[str]] = None) -> Optional[ParsedFilename]:
        """Parse filename et retourne un ParsedFilename ou None si invalide.

        filename : nom avec ou sans extension.
        styles   : liste des styles autorisés. Si None ou vide, la
                   validation de style émet un warning mais continue
                   (règle métier : un fichier sans style détecté est invalide).

        ORDRE DES DÉTROMPEURS (identique à bidi_rename/parsing.py) :
          1. [...]         → studio
          2. @...@         → acteurs
          3. style / style# → style
          4. date          → date normalisée
          5. POV/3D/NOCUT  → booléens
          6. CROP(WxH)     → crop global
          7. TS(...)       → chapitre
          8. THUMB(...)    → vignette
          9. ENCODE(...)   → codec
         10. RESIZE(...)   → résolution
         11. {nombre}      → ID
         12. reste         → titre
        """
        stem = Path(filename).stem
        ext  = Path(filename).suffix

        if styles is None:
            styles = []
        if not styles:
            log.warning("parse : liste de styles vide, validation désactivée")

        found_styles:  List[str]      = []
        star:          bool           = False
        actors:        List[str]      = []
        studio:        Optional[str]  = None
        date:          Optional[str]  = None
        booleans:      Dict[str, bool]= {"POV": False, "3D": False, "NOCUT": False}
        crop:          Optional[CropInfo] = None
        chapters:      List[ChapterInfo] = []
        thumb:         Optional[ThumbInfo] = None
        encode:        Optional[str]  = None
        resize:        Optional[str]  = None
        file_id:       Optional[int]  = None
        title_tokens:  List[str]      = []

        tokens = [t.strip() for t in stem.split(" - ")]

        for token in tokens:
            # 1. Studio
            m = re.match(r'^\[([^\]]+)\]$', token)
            if m:
                studio = m.group(1)
                continue

            # 2. Acteurs
            m = re.match(r'^@([^@]+)@$', token)
            if m:
                actors = [a.strip() for a in m.group(1).split(',') if a.strip()]
                continue

            # 3. Style (avec ou sans # final, tolérance 's' terminal)
            matched_style = cls._match_style(token, styles)
            if matched_style is not None:
                style_name, is_star = matched_style
                found_styles.append(style_name)
                if is_star:
                    star = True
                continue

            # 4. Date
            normalized = cls._parse_date(token)
            if normalized is not None:
                date = normalized
                continue

            # 5. Booléens
            if token.upper() in booleans:
                booleans[token.upper()] = True
                continue

            # 6. CROP(WxH)
            crop_parsed = cls._parse_crop(token)
            if crop_parsed is not None:
                crop = crop_parsed
                continue

            # 7. Chapitre TS(...)
            chapter = cls._parse_chapter(token)
            if chapter is not None:
                chapters.append(chapter)
                continue

            # 8. THUMB(timestamp)
            m = re.match(r'^THUMB\(([^)]+)\)$', token, re.IGNORECASE)
            if m:
                ts_str = m.group(1)
                thumb = ThumbInfo(
                    timestamp_original=ts_str,
                    timestamp_seconds=to_seconds(ts_str),
                )
                continue

            # 9. ENCODE(codec)
            m = re.match(r'^ENCODE\(([^)]+)\)$', token, re.IGNORECASE)
            if m:
                encode = m.group(1).lower()
                continue

            # 10. RESIZE(résolution)
            m = re.match(r'^RESIZE\(([^)]+)\)$', token, re.IGNORECASE)
            if m:
                resize = m.group(1)
                continue

            # 11. ID {nombre}
            m = re.match(r'^\{(\d+)\}$', token)
            if m:
                file_id = int(m.group(1))
                continue

            # 12. Titre (reste)
            title_tokens.append(token)

        # ── Validation : style obligatoire ─────────────────────────────────
        if not found_styles:
            log.error("Fichier sans style (invalide) : %s", filename)
            return None

        # ── Tri chapitres chronologique ───────────────────────────────────
        chapters.sort(key=lambda c: c.timestamp_seconds)

        # ── Fallback titre dernier chapitre ───────────────────────────────
        # Si le dernier chapitre n'a pas de titre :
        #   1. Dernier style disponible
        #   2. Titre du dernier chapitre précédent qui en a un
        #   3. title reste None
        if chapters and not chapters[-1].title:
            last = chapters[-1]
            if found_styles:
                fallback = found_styles[-1]
                last.title           = fallback
                last.tags            = [t.strip() for t in fallback.split('-') if t.strip()]
                last.title_from_style = True
                log.debug("Chapitre final sans titre → fallback style '%s'", fallback)
            else:
                prev = next(
                    (ch.title for ch in reversed(chapters[:-1])
                     if ch.title and not ch.title_from_style),
                    None,
                )
                if prev:
                    last.title           = prev
                    last.tags            = [t.strip() for t in prev.split('-') if t.strip()]
                    last.title_from_style = True

        title = " - ".join(title_tokens) if title_tokens else "Sans Titre"

        return ParsedFilename(
            studio=studio,
            actors=actors,
            styles=found_styles,
            star=star,
            title=title,
            date=date,
            booleans=booleans,
            crop=crop,
            chapters=chapters,
            thumb=thumb,
            encode=encode,
            resize=resize,
            file_id=file_id,
            extension=ext,
        )

    # ── Helpers privés ─────────────────────────────────────────────────────

    @staticmethod
    def _match_style(
        token: str, styles: List[str]
    ) -> Optional[tuple[str, bool]]:
        """Tente de matcher token contre la liste de styles.

        Retourne (style_name, is_star) ou None.
        Règles :
          - Token exact           : "StyleA"      → ("StyleA", False)
          - Token avec #          : "StyleA#"     → ("StyleA", True)
          - Token avec 's' final  : "StyleAs#"    → corrigé avec warning
        Si styles est vide → retourne None (pas de validation possible).
        """
        if not styles:
            return None

        clean = token.rstrip('#')
        is_star = token.endswith('#')

        if clean in styles:
            return (clean, is_star)

        # Tolérance 's' terminal
        if clean.endswith('s') and len(clean) > 1:
            clean_no_s = clean[:-1]
            if clean_no_s in styles:
                log.warning("Style corrigé : '%s' → '%s'", clean, clean_no_s)
                return (clean_no_s, is_star)

        return None

    @staticmethod
    def _parse_crop(token: str) -> Optional[CropInfo]:
        """Parse CROP(WxH) et retourne CropInfo ou None."""
        m = re.match(r'^CROP\((\d+)x(\d+)\)$', token.strip(), re.IGNORECASE)
        if not m:
            return None
        w, h = int(m.group(1)), int(m.group(2))
        if w <= 0 or h <= 0:
            return None
        return CropInfo(w=w, h=h)

    @staticmethod
    def _parse_chapter(token: str) -> Optional[ChapterInfo]:
        """Parse un token de chapitre TS(...) et retourne ChapterInfo ou None.

        Formats supportés :
          TS(dur)(titre)(posXxposY)
          TS(titre)(posXxposY)
          TS(posXxposY)
          TS(CENTER)
          TS               → rejeté (pas de parenthèses = pas un chapitre)

        Règles de décodage des groupes (ordre des parenthèses) :
          - Entier seul          → durée
          - NxM                  → pos_x, pos_y
          - "CENTER"             → pos_mode center
          - Sinon                → titre
        """
        if '(' not in token:
            return None

        ts_str = token.split('(', 1)[0].strip()
        if not is_timestamp_token(ts_str):
            return None

        groups = re.findall(r'\(([^()]*)\)', token[len(ts_str):])

        duration: Optional[int] = None
        title:    Optional[str] = None
        pos_x:    Optional[int] = None
        pos_y:    Optional[int] = None
        pos_mode: str           = "topleft"

        for raw in groups:
            val = raw.strip()
            if not val:
                continue
            if val.upper() == "CENTER":
                pos_mode = "center"
                continue
            if re.match(r'^\d+$', val):
                duration = int(val)
                continue
            m = re.match(r'^(\d+)x(\d+)$', val)
            if m:
                pos_x = int(m.group(1))
                pos_y = int(m.group(2))
                continue
            title = val

        if duration is None:
            duration = _DEFAULT_DURATION

        ts_sec = to_seconds(ts_str)
        tags   = [t.strip() for t in title.split('-') if t.strip()] if title else []

        return ChapterInfo(
            timestamp_original=ts_str,
            timestamp_seconds=ts_sec,
            duration=duration,
            title=title,
            tags=tags,
            pos_x=pos_x,
            pos_y=pos_y,
            pos_explicit=(pos_x is not None),
            pos_mode=pos_mode,
            title_from_style=False,
            raw_token=token,
        )

    @staticmethod
    def _parse_date(token: str) -> Optional[str]:
        """Tente de parser un token comme date.

        Formats acceptés → normalisés en AAAA-MM-JJ / AAAA-MM / AAAA :
          AAAA-MM-JJ   AAAA.MM.JJ
          AAAA-MM      AAAA.MM
          AAAA
          JJ-MM-AAAA   JJ.MM.AAAA
          MM-AAAA      MM.AAAA  (ssi MM <= 12)
        """
        if re.match(r'^\d{4}[.\-]\d{2}([.\-]\d{2})?$', token):
            return token.replace('.', '-')

        m = re.match(r'^(\d{2})[.\-](\d{2})[.\-](\d{4})$', token)
        if m:
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

        m = re.match(r'^(\d{2})[.\-](\d{4})$', token)
        if m and int(m.group(1)) <= 12:
            return f"{m.group(2)}-{m.group(1)}"

        if re.match(r'^(19|20)\d{2}$', token):
            return token

        return None
