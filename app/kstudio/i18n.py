"""Language of the program's own messages.

Window labels live in a dictionary in kstudio/ui/00-strings.js; everything the program prints
to the console and to the build log lives right here in the code. Both variants
sit next to each other, so a message is never translated blindly:

    log(tr("Preparing the audio…", "Готовлю звук…"))

The language comes from KARAOKE_UI_LANG, then from settings.ini, then from the
system. English if nothing matched.
"""

from __future__ import annotations

import os

from . import settings as SET

_LANG = None


def _from_settings() -> str:
    # The language of the labels first; failing that, the language of the
    # lyrics — a settings file that says the song is Russian has said enough.
    got = SET.read()
    for name in ("надписи", "ui-lang", "language"):
        val = (got.get(name) or "").lower()
        if val in ("ru", "en"):
            return val
    return ""


def _from_system() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        val = (os.environ.get(var) or "").lower()
        if val.startswith("ru"):
            return "ru"
        if val:
            return "en"
    if os.name == "nt":                       # Windows usually has no such vars
        try:
            import ctypes
            lang = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
            return "ru" if lang == 0x19 else "en"
        except Exception:
            pass
    return "en"


def lang() -> str:
    global _LANG
    if _LANG is None:
        val = (os.environ.get("KARAOKE_UI_LANG") or "").strip().lower()
        if val not in ("ru", "en"):
            val = _from_settings() or _from_system()
        _LANG = val if val in ("ru", "en") else "en"
    return _LANG


def set_lang(code: str) -> None:
    """Set the language by hand — used by --ui-lang and by the tests."""
    global _LANG
    _LANG = code if code in ("ru", "en") else None


def tr(en: str, ru: str) -> str:
    return ru if lang() == "ru" else en
