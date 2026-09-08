"""The window's script, in parts.

ui.js grew past four thousand lines, and every change began with a search
through it. It lies here as a file per part of the window — the labels, the
song list, the timeline, the export — numbered in the order they were written
in, because the parts share one scope: the whole is one function, opened in
the first file and closed in the last, and a later part leans on names the
earlier ones declare. The browser still receives one script under the old
name; `script()` is where the parts become it.
"""

from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))


def parts() -> list:
    """The files, in the order they are joined."""
    return sorted(os.path.join(HERE, n) for n in os.listdir(HERE)
                  if n.endswith(".js"))


def script() -> str:
    """The one script the window loads."""
    return "".join(open(p, encoding="utf-8").read() for p in parts())
