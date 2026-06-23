"""
File: timestamp.py
Path: video_processor/infra/timestamp.py

Version: 1.0.0
Date: 2026-06-23

Changelog:
- 1.0.0 (2026-06-23): Extraction depuis bidi_rename/utils.py
  * Fonctions pures sans dépendance externe
  * Ajout convert_seconds_to_timestamp() pour round-trip
  * is_timestamp_token() : même logique, même règles
"""

import re
from typing import Optional


def is_timestamp_token(token: str) -> bool:
    """Vérifie si un token est un timestamp valide.

    Formats acceptés (séparateur '-') :
      HH-MM-SS   ex: 01-30-45
      MM-SS      ex: 06-19
      SS         ex: 42

    Règles de validité :
      - Uniquement des chiffres et des tirets
      - 1, 2 ou 3 segments
      - MM < 60  et  SS < 60  (si présents)
    """
    # Tronquer si token composite (ex: "06-19(81)(Scene)")
    clean = token.split('(', 1)[0].strip()

    if not re.match(r'^\d+(-\d+){0,2}$', clean):
        return False

    parts = clean.split('-')
    if len(parts) == 3:
        _, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        return m < 60 and s < 60
    if len(parts) == 2:
        m, s = int(parts[0]), int(parts[1])
        return s < 60
    return True  # len == 1 : secondes brutes, toujours valide


def to_seconds(timestamp: str) -> int:
    """Convertit un timestamp HH-MM-SS / MM-SS / SS en secondes entières.

    Retourne 0 pour un format invalide (ne lève pas d'exception).
    """
    clean = timestamp.strip()
    if not re.match(r'^\d+(-\d+){0,2}$', clean):
        return 0

    parts = clean.split('-')
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(parts[0])
    except ValueError:
        return 0


def to_timestamp(seconds: int) -> str:
    """Convertit des secondes entières en timestamp MM-SS ou HH-MM-SS.

    - Moins de 3600 s → MM-SS  (ex: 379 → "06-19")
    - 3600 s et plus  → HH-MM-SS (ex: 3661 → "01-01-01")
    """
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h:02d}-{m:02d}-{s:02d}"
    return f"{m:02d}-{s:02d}"
