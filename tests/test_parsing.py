"""
File: test_parsing.py
Path: tests/test_parsing.py

Version: 1.0.0
Date: 2026-06-23

Changelog:
- 1.0.0 (2026-06-23): Suite de tests basée sur parsing_cases.json
  * Un test par cas JSON (paramétrisé via pytest.mark.parametrize)
  * Vérification de tous les champs expectés
  * Sous-objets chapitres vérifiés champ par champ
  * Lancer : python -m pytest tests/test_parsing.py -v
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

# Injection sys.path — même pattern que bidi_rename2.py
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from video_processor.infra.filename_parser import FilenameParser, ParsedFilename

# ── Chargement des cas ──────────────────────────────────────────────────────

_CASES_PATH = Path(__file__).parent / "parsing_cases.json"
_ALL_CASES  = json.loads(_CASES_PATH.read_text(encoding="utf-8"))
# Filtrer les entrées commentaires (celles sans 'id')
_CASES = [c for c in _ALL_CASES if "id" in c]


# ── Fixture paramétrisée ────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "case",
    _CASES,
    ids=[c["id"] for c in _CASES],
)
def test_should_parse_case(case: Dict[str, Any]) -> None:
    """Vérifie chaque cas défini dans parsing_cases.json."""
    filename: str          = case["input"]
    styles:   list         = case.get("styles", [])
    expect:   Dict         = case["expect"]

    result: Optional[ParsedFilename] = FilenameParser.parse(filename, styles=styles)

    expected_valid: bool = expect["valid"]

    if not expected_valid:
        assert result is None, (
            f"[{case['id']}] Attendu invalide (None), obtenu : {result}"
        )
        return

    assert result is not None, (
        f"[{case['id']}] Attendu valide, obtenu None pour : {filename!r}"
    )

    # ── Champs scalaires ───────────────────────────────────────────────
    _assert_field(case, expect, result, "title",     result.title)
    _assert_field(case, expect, result, "studio",    result.studio)
    _assert_field(case, expect, result, "actors",    result.actors)
    _assert_field(case, expect, result, "styles",    result.styles)
    _assert_field(case, expect, result, "star",      result.star)
    _assert_field(case, expect, result, "date",      result.date)
    _assert_field(case, expect, result, "booleans",  result.booleans)
    _assert_field(case, expect, result, "encode",    result.encode)
    _assert_field(case, expect, result, "resize",    result.resize)
    _assert_field(case, expect, result, "file_id",   result.file_id)
    _assert_field(case, expect, result, "extension", result.extension)

    # ── Crop ────────────────────────────────────────────────────────────
    if "crop" in expect:
        expected_crop = expect["crop"]
        if expected_crop is None:
            assert result.crop is None, (
                f"[{case['id']}] crop attendu None, obtenu {result.crop}"
            )
        else:
            assert result.crop is not None, (
                f"[{case['id']}] crop attendu {expected_crop}, obtenu None"
            )
            assert result.crop.w == expected_crop["w"], (
                f"[{case['id']}] crop.w : {result.crop.w} != {expected_crop['w']}"
            )
            assert result.crop.h == expected_crop["h"], (
                f"[{case['id']}] crop.h : {result.crop.h} != {expected_crop['h']}"
            )

    # ── Thumb ────────────────────────────────────────────────────────────
    if "thumb" in expect:
        expected_thumb = expect["thumb"]
        if expected_thumb is None:
            assert result.thumb is None, (
                f"[{case['id']}] thumb attendu None, obtenu {result.thumb}"
            )
        else:
            assert result.thumb is not None
            assert result.thumb.timestamp_original == expected_thumb["timestamp_original"]
            assert result.thumb.timestamp_seconds  == expected_thumb["timestamp_seconds"]

    # ── Chapitres ─────────────────────────────────────────────────────────
    if "chapters_count" in expect:
        assert len(result.chapters) == expect["chapters_count"], (
            f"[{case['id']}] chapters_count : {len(result.chapters)} != {expect['chapters_count']}"
        )

    if "chapters" in expect:
        for i, exp_ch in enumerate(expect["chapters"]):
            assert i < len(result.chapters), (
                f"[{case['id']}] chapitre index {i} manquant (total: {len(result.chapters)})"
            )
            ch = result.chapters[i]
            for field_name, exp_val in exp_ch.items():
                got_val = getattr(ch, field_name, "__MISSING__")
                assert got_val == exp_val, (
                    f"[{case['id']}] chapitres[{i}].{field_name} : "
                    f"{got_val!r} != {exp_val!r}"
                )


# ── Helper ────────────────────────────────────────────────────────────────

def _assert_field(
    case: Dict, expect: Dict, result: ParsedFilename, field: str, got: Any
) -> None:
    """Vérifie un champ uniquement s'il est présent dans expect."""
    if field not in expect:
        return
    exp = expect[field]
    assert got == exp, (
        f"[{case['id']}] {field} : {got!r} != {exp!r}  (input={case['input']!r})"
    )
