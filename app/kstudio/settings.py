"""settings.ini, read in one place.

The file belongs to the person who runs the program; the example next to it
is the reference. Five places used to read it — the launcher, the downloader,
the window, the console messages and the setup — each with a loop of its own
over the lines and its own idea of what a comment is, so a colour written as
#4de1ff was a value to one of them and a comment to another. The rule is one
now: “#” after a space starts a comment unless what follows looks like a
colour, keys are lowered, values keep their case, and the first file found is
the file.
"""

from __future__ import annotations

import os
import re
from typing import Dict, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/
HOME = os.path.dirname(ROOT)                                          # next to it

# “colors = #4de1ff,#ff8ad1  # the two voices”: the second colour is a value,
# the words after it are a comment.
_TAIL = re.compile(r"\s+#(?![0-9A-Fa-f]{3,8}\b).*$")


def places() -> list:
    """Where the file may lie, the current place first. KARAOKE_SETTINGS names
    one outright; the places older versions used are still looked in."""
    named = os.environ.get("KARAOKE_SETTINGS") or ""
    return [p for p in (named,
                        os.path.join(ROOT, "settings.ini"),
                        os.path.join(HOME, "settings.ini"),
                        os.path.join(HOME, "настройки.ini")) if p]


def path() -> Optional[str]:
    """The settings file that exists, or None: the defaults hold then."""
    for p in places():
        if os.path.isfile(p):
            return p
    return None


def read(where: Optional[str] = None) -> Dict[str, str]:
    """Every setting in the file as {name: value} — names lowered, values as
    written without a trailing comment. Empty when there is no file."""
    where = where or path()
    out: Dict[str, str] = {}
    if not where:
        return out
    try:
        with open(where, encoding="utf-8-sig") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                line = _TAIL.sub("", line).strip()
                if "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip().lower(), val.strip()
                if key and val:
                    out[key] = val
    except OSError:
        pass
    return out


def get(*names: str) -> str:
    """One value, by any of the names it goes under — English or Russian."""
    got = read()
    for name in names:
        if got.get(name.lower()):
            return got[name.lower()]
    return ""
