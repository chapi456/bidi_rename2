"""
File: config_loader.py
Path: video_processor/infra/config_loader.py

Version: 1.0.0
Date: 2026-06-23

Changelog:
- 1.0.0 (2026-06-23): Réécriture orientée objet
  * AppConfig dataclass (styles, directories, ui, system_files, encoding)
  * Chargement lazy : la config n'est lue qu'au premier accès
  * Auto-reload : si config.yaml est modifié sur disque, rechargement transparent
  * Instance singleton via AppConfig.load() / AppConfig.instance()
  * Accès typés : cfg.styles, cfg.directories, cfg.thumb_height, …
  * Résolution du chemin : CLI arg > ./config/config.yaml > ~/.bidi_rename2/config.yaml
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Injection sys.path (sécurité si module importé directement)
_MOD_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_MOD_ROOT) not in sys.path:
    sys.path.insert(0, str(_MOD_ROOT))

try:
    import yaml
except ImportError:
    print("❌ PyYAML non installé — pip install PyYAML")
    sys.exit(1)

log = logging.getLogger("infra.config_loader")

# Singleton module-level
_instance: Optional[AppConfig] = None


@dataclass
class AppConfig:
    """Configuration applicative chargée depuis config.yaml.

    Accès typés aux valeurs courantes. Auto-reload si le fichier est modifié.
    Usage :
        cfg = AppConfig.load()          # première fois ou chemin explicite
        cfg = AppConfig.instance()      # réutilise le singleton
        cfg.styles                      # List[str]
        cfg.directories                 # List[str]
        cfg.thumb_height                # int
    """

    # Chemin résolu du fichier chargé
    config_path: Path

    # Données brutes (source de vérité interne)
    _raw: Dict[str, Any] = field(default_factory=dict, repr=False)
    _mtime: float        = field(default=0.0,          repr=False)

    # ── Propriétés typées ────────────────────────────────────────────────

    @property
    def styles(self) -> List[str]:
        self._reload_if_needed()
        return list(self._raw.get("styles", []))

    @property
    def directories(self) -> List[str]:
        self._reload_if_needed()
        return list(self._raw.get("directories", []))

    @property
    def tocut_filename(self) -> str:
        self._reload_if_needed()
        return self._raw.get("system_files", {}).get("tocut_file", "#toCut.txt")

    @property
    def last_id_file(self) -> Optional[str]:
        self._reload_if_needed()
        return self._raw.get("system_files", {}).get("last_id_file")

    @property
    def encoders_cache_file(self) -> str:
        self._reload_if_needed()
        return self._raw.get("system_files", {}).get(
            "encoders_cache_file", "encoders_available.json"
        )

    @property
    def thumb_height(self) -> int:
        self._reload_if_needed()
        return int(self._raw.get("ui", {}).get("thumb_height", 90))

    @property
    def window_width(self) -> int:
        self._reload_if_needed()
        return int(self._raw.get("ui", {}).get("window_width", 1600))

    @property
    def window_height(self) -> int:
        self._reload_if_needed()
        return int(self._raw.get("ui", {}).get("window_height", 950))

    @property
    def prefer_hevc(self) -> bool:
        self._reload_if_needed()
        return bool(
            self._raw.get("encoding", {}).get("prefer_hevc_when_available", False)
        )

    @property
    def default_codec(self) -> str:
        self._reload_if_needed()
        return self._raw.get("encoding", {}).get("default_codec", "h264")

    @property
    def codec_candidates(self) -> Dict[str, List[str]]:
        self._reload_if_needed()
        return dict(self._raw.get("codec_candidates", {}))

    def get(self, key: str, default: Any = None) -> Any:
        """Accès générique à une clé de la config brute (rétro-compat)."""
        self._reload_if_needed()
        return self._raw.get(key, default)

    def is_valid_style(self, style: str) -> bool:
        """Retourne True si style est dans la liste des styles autorisés."""
        return style in self.styles

    # ── Reload automatique ───────────────────────────────────────────────

    def _reload_if_needed(self) -> None:
        """Recharge config.yaml si le fichier a été modifié depuis le dernier chargement."""
        if not self.config_path.exists():
            return
        mtime = self.config_path.stat().st_mtime
        if mtime > self._mtime:
            self._load()

    def _load(self) -> None:
        """Charge (ou recharge) config.yaml depuis le disque."""
        try:
            raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            log.error("Erreur YAML dans %s : %s", self.config_path, exc)
            return

        if not raw.get("styles"):
            log.warning(
                "config.yaml sans 'styles' — validation de style désactivée (%s)",
                self.config_path,
            )

        self._raw   = raw
        self._mtime = self.config_path.stat().st_mtime
        log.debug(
            "Config chargée : %d styles, %d répertoires (%s)",
            len(raw.get("styles", [])),
            len(raw.get("directories", [])),
            self.config_path,
        )

    # ── Constructeurs ────────────────────────────────────────────────────

    @classmethod
    def load(cls, explicit_path: Optional[str] = None) -> "AppConfig":
        """Charge la config et mémorise le singleton.

        Résolution du chemin (première trouvée) :
          1. explicit_path (argument CLI --config)
          2. <racine_projet>/config/config.yaml
          3. ~/.bidi_rename2/config.yaml
          4. Fichier par défaut vide (dégradation gracieuse)
        """
        global _instance

        resolved = cls._resolve_path(explicit_path)
        cfg = cls(config_path=resolved)
        if resolved.exists():
            cfg._load()
        else:
            log.warning("Aucun config.yaml trouvé — valeurs par défaut utilisées")

        _instance = cfg
        return cfg

    @classmethod
    def instance(cls) -> "AppConfig":
        """Retourne le singleton. Appelle load() si jamais initialisé."""
        global _instance
        if _instance is None:
            _instance = cls.load()
        return _instance

    @staticmethod
    def _resolve_path(explicit: Optional[str]) -> Path:
        """Résout le chemin du fichier config.yaml."""
        if explicit:
            return Path(explicit).resolve()

        # Chemin canonique : racine projet / config / config.yaml
        project_root = Path(__file__).resolve().parent.parent.parent
        candidate = project_root / "config" / "config.yaml"
        if candidate.exists():
            return candidate

        # Chemin utilisateur
        user_candidate = Path.home() / ".bidi_rename2" / "config.yaml"
        if user_candidate.exists():
            return user_candidate

        # Pas trouvé → on retourne le chemin canonique (sera créé plus tard)
        return candidate
