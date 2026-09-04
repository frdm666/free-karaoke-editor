"""Building the standalone HTML page: text + timings + audio in one file."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from typing import Dict, Optional
from urllib.parse import quote

from . import __version__
from .lyrics import Lyrics
from .i18n import tr

TEMPLATE = os.path.join(os.path.dirname(__file__), "player.html")

def ENGINE_NAME(engine: str) -> str:
    return {
        "whisper": tr("Whisper timing", "разметка Whisper"),
        "energy":  tr("timing by loudness", "разметка по энергии"),
        "manual":  tr("timings from the text", "тайминги из текста"),
        "json":    tr("timings from a file", "тайминги из файла"),
        "none":    tr("no timing", "без разметки"),
    }.get(engine, engine)


class _EngineLabel(dict):
    """ENGINE_LABEL.get(x, x) — the familiar shape, translated on the spot."""

    def get(self, key, default=None):
        return ENGINE_NAME(key) if key in ("whisper", "energy", "manual",
                                           "json", "none") else default


ENGINE_LABEL = _EngineLabel()


def _data_uri(path: str, mime: str) -> str:
    with open(path, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode("ascii"))


def _rel(path: str, html_path: str) -> str:
    rel = os.path.relpath(path, os.path.dirname(os.path.abspath(html_path)) or ".")
    # file names can be non-Latin and contain spaces — escape them for src
    return quote(rel.replace(os.sep, "/"))



# --------------------------------------------------------------------------- #
# Colours of the page

def _rgb(color: str):
    """“#rgb” or “#rrggbb” → (r, g, b) in 0..255. Anything else — None."""
    c = (color or "").strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return None
    try:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _lum(rgb) -> float:
    """Luminance the WCAG way — the measure readability is judged by."""
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """How many times lighter one is than the other: 1 — identical, 21 — the limit."""
    ra, rb = _rgb(a), _rgb(b)
    if not ra or not rb:
        return 21.0
    la, lb = _lum(ra), _lum(rb)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def readable(bg: str, text: str, need: float = 4.5):
    """Nudge the text colour so it does not blend into the background.

    Nobody forbids a person to change the colour, but letters that cannot be
    read against their own background are not styling, they are a spoiled page.
    So the hue stays as chosen while the lightness is moved away from the
    background until the text can be told apart.
    """
    rgb_t, rgb_b = _rgb(text), _rgb(bg)
    if not rgb_t or not rgb_b:
        return text, False
    if contrast(bg, text) >= need:
        return text, False
    up = _lum(rgb_b) < 0.5                     # dark background — lighten the text
    r, g, b = rgb_t
    for _ in range(64):
        r, g, b = ((min(255, int(v + (255 - v) * 0.08 + 2)) if up
                    else max(0, int(v - v * 0.08 - 2))) for v in (r, g, b))
        got = "#%02x%02x%02x" % (r, g, b)
        if contrast(bg, got) >= need:
            return got, True
    return ("#ffffff" if up else "#000000"), True


def theme_colors(theme):
    """The “background, text” pair from settings — checked for readability."""
    bg, text = (list(theme or []) + [None, None])[:2]
    bg = bg or "#0a0b14"
    text = text or "#e8ebf5"
    text, fixed = readable(bg, text)
    return {"bg": bg, "text": text}, fixed


def build_html(out_path: str, lyrics: Lyrics, duration: float,
               tracks: Dict[str, tuple], engine: str = "energy",
               embed: bool = True, title: Optional[str] = None,
               artist: Optional[str] = None, ui_lang: str = "auto",
               colors=None, theme=None, keep_spans=None,
               cover_path: Optional[str] = None,
               cover_dark: Optional[int] = None,
               cover_paths: Optional[list] = None,
               grid: Optional[dict] = None) -> str:
    """tracks: {\'mix\'|\'instrumental\'|\'vocals\': (path, mime)} → path to the HTML."""
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        tpl = f.read()

    audio = {}
    for name, (path, mime) in tracks.items():
        if not path:
            continue
        audio[name] = _data_uri(path, mime) if embed else _rel(path, out_path)

    title = title or lyrics.title or os.path.splitext(os.path.basename(out_path))[0]

    # Key under which edits are kept in the browser. The timings must take part
    # in it: otherwise a rebuilt page with new timing would get the old key and
    # silently pull the old edits over the fresh alignment.
    sig = "|".join([title, str(round(duration, 1))] +
                   [f"{ln.start or 0:.2f}" for ln in lyrics.lines])
    payload = {
        # the player lives inside the page, so updating the program does not
        # change already built files — this mark says which code is inside
        "player": __version__,
        # Language of the page labels: “auto” follows the browser of whoever
        # opens it. The page travels to people with any native language.
        "uiLang": ui_lang,
        # Two highlight colours: the main voice and the second one.
        "colors": list(colors or ("#4de1ff", "#ff8ad1")),
        # Background and text. An unreadable pair is corrected: letters that
        # blend into the background are not a style, they are a broken page.
        "theme": theme_colors(theme)[0],
        "id": hashlib.sha1(sig.encode("utf-8")).hexdigest()[:12],
        # the clip's cover, blurred behind the lyrics — on the page and in the
        # video alike. Empty means the woven gradient as always.
        "cover": (_data_uri(cover_path, "image/jpeg")
                  if cover_path and os.path.isfile(cover_path) else ""),
        # how much of the cover is darkened away, percent: the words must stay
        # the brightest thing in the frame, and covers differ
        "coverDark": max(0, min(95, int(cover_dark if cover_dark is not None else 66))),
        # frames cut from the clip: the video plays them as a slow slideshow
        # behind the lyrics; the page keeps its single cover
        "covers": [_data_uri(cp, "image/jpeg") for cp in (cover_paths or [])
                   if cp and os.path.isfile(cp)],
        # The beat, when the song keeps one: the video shows it as four quiet
        # dots along the bottom edge, so a singer can see where the bar is
        # without anything getting between them and the words.
        "grid": ({"bpm": max(20.0, min(300.0, float(grid.get("bpm") or 120))),
                  "beat0": max(0.0, float(grid.get("beat0") or 0.0))}
                 if isinstance(grid, dict) and grid.get("pulse") else None),
        "engineLabel": ENGINE_LABEL.get(engine, engine),
        "audio": audio,
        "data": {
            "title": title,
            "artist": artist or lyrics.artist or "",
            "duration": round(duration, 3),
            # Stretches where the original voice is left in: a vocalise or a
            # scream with no words has nothing to sing over, and muting it
            # leaves a hole in the song.
            "keepSpans": [[round(float(a), 3), round(float(b), 3)]
                          for a, b in (keep_spans or [])],
            "lines": [ln.to_json() for ln in lyrics.lines],
        },
    }

    blob = json.dumps(payload, ensure_ascii=False)
    # so the content cannot break out of <script>…</script>
    blob = blob.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    html = tpl.replace("__TITLE__", _esc(title + (" — " + artist if artist else "")))
    # lang on <html> is set right away: translators and screen readers read it
    # before any script runs.
    html = html.replace("__LANG__", ui_lang if ui_lang in ("ru", "en") else "en")
    html = html.replace("__PAYLOAD__", blob)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


_PAYLOAD_RE = re.compile(r'<script id="payload" type="application/json">(.*?)</script>', re.S)


def read_payload(html_path: str) -> dict:
    """Pull the text, the timings and the audio out of a built page."""
    with open(html_path, encoding="utf-8") as f:
        m = _PAYLOAD_RE.search(f.read())
    if not m:
        raise SystemExit(tr(
            f"{html_path} — this does not look like a page built by this program.",
            f"{html_path} — не похоже на страницу, собранную этой программой."))
    raw = (m.group(1).replace("\\u003c", "<").replace("\\u003e", ">")
           .replace("\\u0026", "&"))
    return json.loads(raw)


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


# --------------------------------------------------------------------------- #
#  Timings from an external JSON (exported from the player's editor)
# --------------------------------------------------------------------------- #

def apply_timings(lyrics: Lyrics, path: str, verbose: bool = True) -> Lyrics:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    src = data.get("lines", data if isinstance(data, list) else [])
    if len(src) != len(lyrics.lines):
        raise SystemExit(tr(
            f"{path} has {len(src)} lines while the text has {len(lyrics.lines)}. "
            "Take the same lyrics file the timing was made from.",
            f"В {path} {len(src)} строк, а в тексте {len(lyrics.lines)}. "
            "Возьмите тот же файл с текстом, из которого делали разметку."))
    for ln, s in zip(lyrics.lines, src):
        ln.start, ln.end = float(s.get("start", 0)), float(s.get("end", 0))
        ws = s.get("words") or []
        for w, sw in zip(ln.words, ws):
            w.start = float(sw.get("t", ln.start))
            w.end = w.start + float(sw.get("d", 0.3))

    # A ready JSON is repaired too: it may still hold lines that drifted apart
    # in an earlier pass, and they would silently move into the new page.
    from .align import repair_lines, repair_order
    log = print if verbose else (lambda m: None)
    repair_lines(lyrics, log=log)
    repair_order(lyrics, log=log)
    return lyrics


def write_lrc(path: str, lyrics: Lyrics) -> str:
    def ts(t: float) -> str:
        t = max(t or 0.0, 0.0)
        return "[%02d:%05.2f]" % (int(t // 60), t % 60)

    out = []
    if lyrics.title:
        out.append("[ti:%s]" % lyrics.title)
    if lyrics.artist:
        out.append("[ar:%s]" % lyrics.artist)
    out += [ts(ln.start) + ln.text for ln in lyrics.lines]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return path
