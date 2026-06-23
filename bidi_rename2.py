"""
File: bidi_rename2.py
Path: bidi_rename2.py

Version: 0.3.0
Date: 2026-06-23

Changelog:
- 0.3.0 (2026-06-23): main() simplifié — plus de câblage manuel, singletons
- 0.2.0 (2026-06-23): Fix import — sys.path injecté avant tout import applicatif
- 0.1.0 (2026-06-23): Squelette initial
"""

# ── Injection sys.path (DOIT être avant tout import applicatif) ──────────────
# Garantit que 'video_processor' est trouvable que le script soit lancé
# depuis son répertoire, depuis un autre répertoire, ou via python -m.
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
# ────────────────────────────────────────────────────────────────────────────

import argparse
import logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("bidi_rename2")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="bidi_rename2 — crop/chapter editor")
    p.add_argument("target", nargs="?", help="Fichier vidéo ou dossier cible")
    p.add_argument("--headless", action="store_true", help="Forcer mode CLI texte")
    p.add_argument("--web",      action="store_true", help="Mode web (futur)")
    p.add_argument("--config",   default=None,        help="Chemin config.yaml alternatif")
    return p.parse_args()


def resolve_target(target_str: str | None) -> Path | None:
    """Résout l'argument cible en Path absolu. None si absent."""
    if target_str is None:
        return None
    p = Path(target_str).resolve()
    if not p.exists():
        log.error("Cible introuvable : %s", p)
        sys.exit(1)
    return p


def build_view(headless: bool, web: bool):
    """Instancie la vue appropriée. Priorité : web > tk > cli."""
    if web:
        try:
            from video_processor.ui.web_view import WebView
            return WebView()
        except ImportError:
            log.warning("web_view non disponible — bascule CLI")
    if not headless:
        try:
            import tkinter  # noqa: F401
            from video_processor.ui.tkinter_view import TkinterView
            log.debug("→ TkinterView")
            return TkinterView()
        except ImportError:
            log.warning("tkinter indisponible — bascule CLI")
    from video_processor.ui.cli_view import CliView
    log.debug("→ CliView")
    return CliView()


def main() -> None:
    args = parse_args()

    # 1. Config en premier (singleton, chemin optionnel CLI)
    from video_processor.infra.config_loader import AppConfig
    AppConfig.load(args.config)     # initialise le singleton

    # 2. Session — se procure scanner et config elle-même
    from video_processor.domain.session import VideoSession
    session = VideoSession.get()

    # 3. Cible optionnelle (argument CLI)
    target = resolve_target(args.target)
    if target:
        session.set_current_by_path(target)

    # 4. Vue + contrôleur
    from video_processor.controller.session_controller import SessionController
    view       = build_view(args.headless, args.web)
    controller = SessionController(session)

    view.bind(controller)
    controller.open_current()
    view.run()


if __name__ == "__main__":
    main()
