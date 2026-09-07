"""Building the standalone HTML page: text + timings + audio in one file."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
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


def _cut_range(trim, duration: float):
    """The piece asked for, or None when the whole song is meant.

    A cut shorter than a second is somebody's slip, not an intention, and a
    pair that covers the whole song is the same as no cut at all.
    """
    if not trim:
        return None
    try:
        a, b = float(trim[0]), float(trim[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None
    a = max(0.0, a)
    b = float(duration) if b <= 0 else min(float(duration), b)
    if b - a < 1.0:
        return None
    if a < 0.01 and b > float(duration) - 0.01:
        return None
    return (a, b)


def _cut_audio(path: str, a: float, b: float, into: str, name: str) -> str:
    """One track, cut to [a, b]. Falls back to the whole file if ffmpeg balks.

    Re-encoded rather than copied: copying cuts at the nearest keyframe, which
    on a compressed track is anywhere up to a second away — and a second is
    exactly the kind of error nobody notices until the first word is missing.
    """
    from . import audio as AU
    out = os.path.join(into, name + ".mp3")
    p = subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", f"{a:.3f}",
                        "-to", f"{b:.3f}", "-i", path, "-vn",
                        "-c:a", "libmp3lame", "-q:a", "3", out],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out if p.returncode == 0 and os.path.isfile(out) else path


def build_html(out_path: str, lyrics: Lyrics, duration: float,
               tracks: Dict[str, tuple], engine: str = "energy",
               embed: bool = True, title: Optional[str] = None,
               artist: Optional[str] = None, ui_lang: str = "auto",
               colors=None, theme=None, keep_spans=None,
               cover_path: Optional[str] = None,
               cover_dark: Optional[int] = None,
               cover_paths: Optional[list] = None,
               grid: Optional[dict] = None,
               dots_long: bool = False,
               melody: bool = False,
               holds: bool = True,
               trim=None) -> str:
    """tracks: {\'mix\'|\'instrumental\'|\'vocals\': (path, mime)} → path to the HTML."""
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        tpl = f.read()

    # A song can hold two minutes of silence, or a hidden track after it, or
    # begin long before anybody sings. What the singer is given is the part
    # they marked: the sound is cut to it and every time in the page moves with
    # the cut, so nobody has to work the same thing out twice. The song itself
    # is untouched — this is a setting, not a knife.
    cut = _cut_range(trim, duration)
    audio = {}
    tmp_cut = tempfile.mkdtemp(prefix="karaoke_trim_") if (cut and embed) else None
    for name, (path, mime) in tracks.items():
        if not path:
            continue
        src, use_mime = path, mime
        if tmp_cut:
            src = _cut_audio(path, cut[0], cut[1], tmp_cut, name)
            use_mime = "audio/mpeg"
        audio[name] = _data_uri(src, use_mime) if embed else _rel(path, out_path)
    if tmp_cut:
        # the bytes are already inside the page; the pieces have no life of
        # their own and should not be left lying about
        shutil.rmtree(tmp_cut, ignore_errors=True)

    # Everything the page counts in seconds moves with the cut: the lines, the
    # words inside them, the stretches where the original is kept, and the
    # length itself. A page whose sound starts at one moment and whose text
    # believes another is worse than no page.
    rows = [ln.to_json() for ln in lyrics.lines]
    spans_out = [[float(a), float(b)] for a, b in (keep_spans or [])]
    dur_out = float(duration)
    if cut:
        lo, hi = cut
        dur_out = hi - lo
        kept = []
        for r in rows:
            if float(r.get("end") or 0) <= lo or float(r.get("start") or 0) >= hi:
                continue                      # wholly outside the piece
            r = dict(r)
            r["start"] = round(max(float(r.get("start") or 0) - lo, 0.0), 3)
            r["end"] = round(min(float(r.get("end") or 0) - lo, dur_out), 3)
            r["words"] = [dict(w, t=round(float(w.get("t") or 0) - lo, 3))
                          for w in (r.get("words") or [])
                          if float(w.get("t") or 0) + float(w.get("d") or 0) > lo
                          and float(w.get("t") or 0) < hi]
            if r["words"]:
                kept.append(r)
        rows = kept
        spans_out = [[max(a - lo, 0.0), min(b - lo, dur_out)]
                     for a, b in spans_out if b > lo and a < hi]

    title = title or lyrics.title or os.path.splitext(os.path.basename(out_path))[0]

    # Key under which edits are kept in the browser. The timings must take part
    # in it: otherwise a rebuilt page with new timing would get the old key and
    # silently pull the old edits over the fresh alignment.
    # The cut takes part in the key too, or a page rebuilt from a different
    # piece of the song would quietly pull in the edits made against the old one.
    sig = "|".join([title, str(round(dur_out, 1))] +
                   [f"{float(r.get('start') or 0):.2f}" for r in rows])
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
        # Whether the three guide dots also count down a wait that already has
        # the panel at the top counting it. One pause, one countdown, unless
        # the singer says otherwise.
        "dotsLong": bool(dots_long),
        # The melody over the words is a strong thing to put next to them, and
        # a singer who wants the words plain should get them plain. Off unless
        # asked for; the notes are measured and kept either way.
        "melody": bool(melody),
        "holds": bool(holds),
        "engineLabel": ENGINE_LABEL.get(engine, engine),
        "audio": audio,
        "data": {
            "title": title,
            "artist": artist or lyrics.artist or "",
            "duration": round(dur_out, 3),
            # Stretches where the original voice is left in: a vocalise or a
            # scream with no words has nothing to sing over, and muting it
            # leaves a hole in the song.
            "keepSpans": [[round(float(a), 3), round(float(b), 3)]
                          for a, b in spans_out],
            "lines": rows,
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
