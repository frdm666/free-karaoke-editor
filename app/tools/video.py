#!/usr/bin/env python3
"""Rendering a karaoke video to MP4 for YouTube — no OBS, no screen capture.

    py tools\\video.py "D:\\Music\\Pesnya_karaoke.html"
    py tools\\video.py "...html" -o clip.mp4 --audio guide
    py tools\\video.py "...html" --start 60 --seconds 20     # a quick sample

Frames are drawn in code and piped into ffmpeg, which is faster than real
time. The text, the timings and the audio all come from the HTML page itself.
If the timing was edited in the player, export it (“Edit” → “Download timings”)
and pass it with --timings.
"""

from __future__ import annotations

import argparse
import base64
import bisect
import math
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from kstudio.i18n import tr, lang as program_lang   # noqa: E402
from kstudio import audio as AU      # noqa: E402
from kstudio import build as B       # noqa: E402

# ---------------------------------------------------------------- look
# The defaults match the page. When the page carries its own colours and look,
# the video takes them: otherwise everything came out the same colour in the
# finished file while the editor showed two different voices.
BG_TOP = (10, 11, 20)
BG_BOTTOM = (20, 24, 48)
COL_DIM = (93, 100, 128)        # not sung yet
COL_HOT = (77, 225, 255)        # sung, main voice
COL_HOT2 = (255, 138, 209)      # sung, second voice
COL_SIDE = (63, 69, 92)         # neighbouring lines
COL_SECT = (255, 204, 77)       # section label
COL_BAR = (77, 225, 255)
COL_PIP = (52, 58, 82)          # guide dots between lines
# Every letter carries a dark ring. Until now the words were readable only
# because the backdrop was tame — a woven gradient, or a cover the singer had
# darkened by hand. Over a picture nobody chose, and over anything that moves,
# there is always a frame with something bright exactly under a word. The ring
# does not care what is behind it.
COL_EDGE = (5, 6, 12)           # the outline under every letter
SCRIM = 0.42                    # how deep the band under the words goes

# A clip standing behind the lyrics is not there to be watched — it is there
# to move a little colour. So it is taken small and blurred into a field.
# Full frames would cost a decode and a blur apiece and gigabytes to hold; a
# field is a few tens of kilobytes, and the eye cannot tell, because there is
# nothing left in it sharp enough to tell by.
BACKDROP_W = 160                # how wide a field is kept
BACKDROP_EVERY = 0.5            # seconds between the frames sampled from the clip
BACKDROP_HOLD = 3               # frames one stretched field serves
BACKDROP_LIT = 74               # how bright the band under the words may stand
# Darkening follows the clip the way a limiter follows a sound: it clamps
# down the instant a cut brings something bright under the words, and lets go
# slowly afterwards. Easing both ways looked calm on paper and read as a frame
# slowly dimming after every cut.
BACKDROP_DROP = 0.60            # how fast it darkens when the clip flares
BACKDROP_LIFT = 0.05            # how slowly it lets go again


def edged(font):
    """Outline settings for a piece of writing, scaled to its own size.

    Everything the frame says stands over a picture somebody else chose. The
    lyrics carry a ring; so must the name in the corner, the opening card,
    the count and the labels — one of them left bare is the one that
    disappears over a bright frame."""
    return {"stroke_width": max(1, int(round(getattr(font, "size", 20) * 0.055))),
            "stroke_fill": COL_EDGE}

# A wait shorter than this is not counted down: it is a breath between lines,
# and three dots under a line being sung say nothing anyone needs.
PIP_MIN_GAP = 2.5
# How long the last line stays after the song has been sung. Long enough to
# let go of the note, short enough not to look like a frozen picture.
END_HOLD = 5.0
# The opening: the song's name, then a count of three. A karaoke that starts
# on the first frame catches everybody mid-breath — nobody is at the
# microphone yet, and the first line is gone before it is read.
INTRO_CARD = 3.0
INTRO_COUNT = 3.0


def _hex_rgb(value, fallback):
    """“#4de1ff” → (77, 225, 255). Anything unclear is left as it was."""
    c = str(value or "").strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return fallback
    try:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return fallback


def _mix(a, b, k):
    return tuple(int(round(a[i] * (1 - k) + b[i] * k)) for i in range(3))


def _lum(c):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _readable(color, bg, need):
    """Keep a colour off its background: black on black is an empty video."""
    up = _lum(bg) < 0.5
    out = tuple(color)
    for _ in range(40):
        if _contrast(out, bg) >= need:
            return out
        out = tuple(min(255, int(v + (255 - v) * 0.1 + 3)) if up
                    else max(0, int(v - v * 0.1 - 3)) for v in out)
    return (255, 255, 255) if up else (0, 0, 0)


def apply_colors(payload) -> None:
    """Carry the page colours over into the video."""
    global COL_HOT, COL_HOT2, COL_BAR, COL_DIM, COL_SIDE, BG_TOP, BG_BOTTOM
    colors = payload.get("colors") or []
    COL_HOT = _hex_rgb(colors[0] if len(colors) > 0 else None, COL_HOT)
    COL_HOT2 = _hex_rgb(colors[1] if len(colors) > 1 else None, COL_HOT2)
    COL_BAR = COL_HOT
    theme = payload.get("theme") or {}
    bg = _hex_rgb(theme.get("bg"), None)
    text = _hex_rgb(theme.get("text"), None)
    if bg:
        BG_TOP = bg
        BG_BOTTOM = _mix(bg, (255, 255, 255), 0.06)
    if text and bg:
        # Dim lines use the same colour, only muted: on a light background the
        # default grey would not read at all.
        COL_DIM = _readable(_mix(text, bg, 0.45), bg, 2.2)
        COL_SIDE = _readable(_mix(text, bg, 0.68), bg, 1.6)
    COL_HOT = _readable(COL_HOT, BG_TOP, 2.5)
    COL_HOT2 = _readable(COL_HOT2, BG_TOP, 2.5)


def mmss(t) -> str:
    t = max(float(t or 0), 0.0)
    return f"{int(t // 60)}:{t % 60:04.1f}"

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\verdanab.ttf", r"C:\Windows\Fonts\calibrib.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def find_font(explicit=None) -> str:
    if explicit:
        if not os.path.isfile(explicit):
            raise SystemExit(tr(f"Font not found: {explicit}", f"Шрифт не найден: {explicit}"))
        return explicit
    for p in FONT_CANDIDATES:
        if os.path.isfile(p):
            return p
    import glob
    for pat in ("/usr/share/fonts/**/*Bold*.ttf", "C:\\Windows\\Fonts\\*.ttf"):
        found = glob.glob(pat, recursive=True)
        if found:
            return found[0]
    raise SystemExit(tr("No .ttf font found — point to one with --font",
                            "Не нашёл ни одного шрифта .ttf — укажите его ключом --font"))


def next_sung(lines, i: int) -> int:
    """The next line the singer actually sings: backing does not count.

    The countdown — the dots and the pill alike — is the singer's cue. Aimed
    at a na-na-na it told them to breathe in for a line that is not theirs.
    """
    j = i + 1
    while j < len(lines) and lines[j].get("backing"):
        j += 1
    return j


def intro_lead(args, name: str) -> float:
    """Seconds that run before the music: the card, and then the count.

    A song with no name has no card to show — it is counted in, and that is
    all of it.
    """
    if not getattr(args, "intro", True):
        return 0.0
    return (INTRO_CARD if name else 0.0) + INTRO_COUNT


def frame_lang(payload: dict) -> str:
    """The language of the words drawn into the frame.

    They stand among the lyrics, not among the program's menus: “END” over a
    Russian song reads as somebody else's caption pasted on. The letters of
    the song decide; when they say nothing at all, the language chosen for the
    page, and then the program's own.
    """
    data = payload.get("data") or {}
    text = " ".join(str(ln.get("text") or "") for ln in (data.get("lines") or []))
    cyr = sum(1 for ch in text if "\u0400" <= ch <= "\u04ff")
    lat = sum(1 for ch in text if "a" <= ch.lower() <= "z")
    if cyr or lat:
        return "ru" if cyr > lat else "en"
    want = str(payload.get("uiLang") or "").strip().lower()
    return want if want in ("ru", "en") else program_lang()


def short_line(text: str, most: int = 34) -> str:
    """A line named in passing, cut short without cutting a word in half.

    “…before w” told the singer nothing and looked like a fault. The cut now
    falls at the last space that fits, and an ellipsis says plainly that
    there is more.
    """
    text = " ".join(str(text or "").split())
    if len(text) <= most:
        return text
    cut = text[:most]
    space = cut.rfind(" ")
    if space >= most // 2:            # a word boundary near enough to use
        cut = cut[:space]
    return cut.rstrip(" ,.;:—-") + "\u2026"


def pill_text(said: str, idx: int, nxt, left: float) -> str:
    """The line inside the countdown pill, in the song's own language."""
    def t_(en, ru):
        return ru if said == "ru" else en
    head = (t_("INTRO", "ВСТУПЛЕНИЕ") if idx < 0 else
            (t_("INTERLUDE", "ПРОИГРЫШ") if nxt else t_("END", "КОНЕЦ")))
    num = (mmss(left) if left >= 60
           else f"{int(math.ceil(left))} " + t_("s", "с"))
    tail = (t_("until “", "до «") + short_line(nxt["text"]) + t_("”", "»")
            if nxt else t_("until the end", "до конца записи"))
    return f"{head}   {num}   {tail}"


def pips_lit(gap: float, left: float) -> int:
    """How many countdown dots burn, `left` seconds before the next line.

    The wait is divided into three equal thirds of ITSELF — not into fixed
    seconds. A pause of 2.6 s would otherwise give the first dot 0.6 s and the
    others a full second each: a countdown that stutters is worse than none.
    The window is the last three seconds, or the whole pause when it is shorter.
    """
    if gap <= PIP_MIN_GAP or left <= 0 or left > 3:
        return 0
    window = min(3.0, gap)
    done = max(0.0, 1.0 - left / window)
    return min(3, max(1, int(done * 3) + 1))


# ---------------------------------------------------------------- audio
# The quiet keep: the original voice held back to a guide, to be sung along
# with — the same level the “instrumental + quiet vocal” mode uses.
SOFT_KEEP = 0.35
# The edges of a kept line are the model's guesses, and the voice they guard
# is real: a little slack on each side keeps a held note from being clipped.
KEEP_PAD = 0.25
# Two kept lines with a breath between them: the original plainly sings on
# through it, and muting the breath chewed a word in half. Glued — unless the
# person's own line stands in the gap, which is exactly where muting belongs.
KEEP_GLUE = 2.0


def keep_spans(payload: dict) -> list:
    """Stretches where the original voice is deliberately kept, with how loud.

    Two sources say so: “♪ Original” on a line — at full voice, or held back
    to a guide when the line is to be sung along with — and the stretches
    marked as holding no words, where a vocalise has nothing to sing over and
    muting it would put a hole in the video. Returns (start, end, level).
    """
    data = payload.get("data") or {}
    sung = [(float(ln.get("start") or 0), float(ln.get("end") or 0))
            for ln in data.get("lines") or []
            if not ln.get("keep") and ln.get("words")]

    def somebody_sings(a, b):
        return any(min(e, b) - max(s, a) > 0.05 for s, e in sung)

    out = []
    for ln in data.get("lines") or []:
        if ln.get("keep"):
            a = float(ln.get("start") or 0)
            b = float(ln.get("end") or 0)
            if b <= a:
                continue              # no length — nothing to keep, pad or not
            pa, pb = max(0.0, a - KEEP_PAD), b + KEEP_PAD
            # the slack must never reach into the singer's own words: kept
            # voice bleeding over their first word is the mirror of the chew
            for s0, e0 in sung:
                if e0 <= a:
                    pa = max(pa, e0)
                if s0 >= b:
                    pb = min(pb, s0)
            out.append((pa, pb, SOFT_KEEP if ln.get("keepSoft") else 1.0))
    for pair in data.get("keepSpans") or []:
        try:
            a, b = float(pair[0]), float(pair[1])
        except (TypeError, ValueError, IndexError):
            continue
        out.append((a, b, 1.0))
    out.sort()
    merged = []
    for a, b, lv in out:
        if b <= a:
            continue
        # adjacent stretches at the same loudness make one stretch — across a
        # short breath too, as long as nobody else sings in it
        if merged and lv == merged[-1][2] \
                and a - merged[-1][1] <= KEEP_GLUE \
                and not somebody_sings(merged[-1][1], a):
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b, lv])
    return [(a, b, lv) for a, b, lv in merged]


def extract_audio(payload: dict, html_path: str, tmp: str, mode: str) -> str:
    """Pull the needed track out of the page (or a file next to it) into WAV."""
    srcs = {}
    for name, uri in payload.get("audio", {}).items():
        if uri.startswith("data:"):
            head, _, b64 = uri.partition(",")
            ext = ".mp3" if "mpeg" in head else (".ogg" if "ogg" in head else ".m4a")
            path = os.path.join(tmp, name + ext)
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
        else:
            from urllib.parse import unquote
            path = os.path.join(os.path.dirname(os.path.abspath(html_path)), unquote(uri))
            if not os.path.isfile(path):
                continue
        srcs[name] = path

    if not srcs:
        raise SystemExit(tr("The page has no audio.", "В странице нет звука."))

    out = os.path.join(tmp, "track.wav")
    instr, voc, mix = srcs.get("instrumental"), srcs.get("vocals"), srcs.get("mix")

    if mode == "minus":
        spans = keep_spans(payload)
        if spans and instr and voc:
            # On marked lines the voice must stay: at full where it is not
            # yours to sing, held back to a guide where you sing along with it.
            # Everywhere else the vocal is muted. volume's `enable` works along
            # the timeline: where the filter is off, audio passes untouched.
            # The commas inside the expressions are escaped for ffmpeg.
            cond = "+".join("between(t\\,%.3f\\,%.3f)" % (a, b)
                            for a, b, _ in spans)
            soft = [(a, b) for a, b, lv in spans if lv < 1.0]
            chain = ""
            if soft:
                soft_cond = "+".join("between(t\\,%.3f\\,%.3f)" % (a, b)
                                     for a, b in soft)
                chain = f"volume={SOFT_KEEP}:enable='{soft_cond}',"
            total = sum(b - a for a, b, _ in spans)
            quiet_n = len(soft)
            print(tr(f"Video audio: instrumental, the original voice kept on "
                     f"{len(spans)} stretches ({total:.1f} s"
                     + (f", {quiet_n} of them quiet, to sing along" if quiet_n else "")
                     + ")",
                     f"Звук ролика: минусовка, оригинальный голос оставлен "
                     f"на {len(spans)} кусках ({total:.1f} с"
                     + (f", из них {quiet_n} потише — петь вместе" if quiet_n else "")
                     + ")"))
            p = subprocess.run(
                [AU.ffmpeg(), "-y", "-v", "error", "-i", instr, "-i", voc,
                 "-filter_complex",
                 f"[1:a]{chain}volume=0:enable='not({cond})'[v];"
                 f"[0:a][v]amix=inputs=2:normalize=0[a]",
                 "-map", "[a]", "-c:a", "pcm_s16le", out],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if p.returncode == 0:
                return out
            print(tr("Mixing failed, taking the plain instrumental:\n",
                     "Смешать не вышло, беру чистую минусовку:\n") +
                  p.stderr.decode(errors="replace")[-300:])
        src = instr or mix
        if src is instr and instr:
            print(tr("Video audio: instrumental", "Звук ролика: минусовка"))
        else:
            print(tr("Video audio: the original track (the page has no instrumental)",
                  "Звук ролика: исходная дорожка (минусовки в странице нет)"))
        AU.to_wav(src, out)
        return out

    if instr and voc:
        level = "1.0" if mode == "original" else "0.35"
        print(tr(f"Clip audio: instrumental + vocal ({float(level)*100:.0f}%)",
                 f"Звук ролика: минусовка + вокал ({float(level)*100:.0f}%)"))
        p = subprocess.run(
            [AU.ffmpeg(), "-y", "-v", "error", "-i", instr, "-i", voc,
             "-filter_complex", f"[1:a]volume={level}[v];[0:a][v]amix=inputs=2:normalize=0[a]",
             "-map", "[a]", "-c:a", "pcm_s16le", out],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            raise SystemExit(tr("Could not mix the tracks:\n",
                                "Не удалось смешать дорожки:\n") +
                             p.stderr.decode(errors="replace")[-500:])
        return out

    print(tr("Video audio: the original track", "Звук ролика: исходная дорожка"))
    AU.to_wav(mix or instr or voc, out)
    return out


# ---------------------------------------------------------------- layout
class LineArt:
    """Prepared images of a line: dim and lit, plus the word positions.

    A line too long for the frame used to shrink until it fit — down to
    letters read only from the front row. The main line now wraps instead:
    two rows at most, split between words, never inside one; the font gives
    way only when even two rows cannot hold it."""

    def __init__(self, line, font_for, width, margin, main=True, align="center"):
        from PIL import Image, ImageDraw
        raw = line["words"] or []
        words = [w["w"] for w in raw] or [line["text"]]
        # a syllable carries no space before it: “ма ла фи ли” is one word
        glue = [bool(w.get("g")) for w in raw] or [False]
        def joined(items, flags):
            out = ""
            for k, piece in enumerate(items):
                out += ("" if k == 0 or flags[k] else " ") + piece
            return out
        text = joined(words, glue)
        max_w = width - 2 * margin

        # rows hold indices, so a syllable keeps its place in the word
        rows = [list(range(len(words)))]
        row_text_of = lambda idxs: joined([words[i] for i in idxs],
                                          [glue[i] if i != idxs[0] else False
                                           for i in idxs])
        self.font = font_for(text, max_w, main)
        # The main seat wraps, and so does the side one: a long answer in a
        # duet used to run off the edge of the frame — its base font sat
        # below the shrink floor, so it could not even shrink.
        if len(words) > 1 and align in ("center", "right") \
                and font_for(text, 10 ** 9, main).size > self.font.size:
            # It shrank to fit. Balance the words over two rows instead: the
            # break lands where the halves come out most even — and never
            # inside a word, so its syllables stay together.
            probe = font_for(text, 10 ** 9, main)
            best, best_diff = 1, None
            for k in range(1, len(words)):
                if glue[k]:
                    continue                 # not between syllables
                a = probe.getlength(row_text_of(list(range(k))))
                b = probe.getlength(row_text_of(list(range(k, len(words)))))
                if best_diff is None or abs(a - b) < best_diff:
                    best, best_diff = k, abs(a - b)
            if best_diff is not None:
                rows = [list(range(best)), list(range(best, len(words)))]
                longest = max((row_text_of(r) for r in rows),
                              key=lambda rt: probe.getlength(rt))
                self.font = font_for(longest, max_w, main)

        asc, desc = self.font.getmetrics()
        self.row_h = asc + desc + 8
        # Room for the ring. The rows keep their spacing — only the layer
        # grows, by as much as the outline sticks out, so the ring is never
        # shaved off at the top of the first row or the foot of the last.
        self.edge_w = max(1, int(round(self.font.size * 0.055)))
        self.pad = self.edge_w
        self.h = self.row_h * len(rows) + 2 * self.pad

        def row_x(idxs):
            total = self.font.getlength(row_text_of(idxs))
            # the backing sits to the right, tucked under its lead like a reply
            x0 = (width - margin - total) if align == "right" else (width - total) / 2
            return max(x0, margin)

        self.word_x, self.word_w, self.word_row = [], [], []
        for r, row in enumerate(rows):
            x0 = row_x(row)
            prefix = ""
            for k, i in enumerate(row):
                if k and not glue[i]:
                    prefix += " "
                self.word_x.append(x0 + self.font.getlength(prefix))
                prefix += words[i]
                self.word_w.append(x0 + self.font.getlength(prefix) - self.word_x[-1])
                self.word_row.append(r)

        def draw(color):
            img = Image.new("RGBA", (width, self.h), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            for r, row in enumerate(rows):
                d.text((row_x(row), self.pad + 4 + r * self.row_h),
                       row_text_of(row), font=self.font, fill=color + (255,),
                       stroke_width=self.edge_w,
                       stroke_fill=COL_EDGE + (255,))
            return img

        self.dim = draw(COL_DIM if main else COL_SIDE)
        # the line after the next one: present, but clearly further away
        self.faint = self.dim.copy()
        self.faint.putalpha(self.faint.getchannel("A").point(lambda v: v * 45 // 100))
        hot = COL_HOT2 if line.get("voice") == 2 else COL_HOT
        # a duet's backing line fills as it is sung too — only the queue lines
        # (drawn dim ahead of their time) never need a hot layer
        self.hot = draw(hot) if (main or align == "right") else None

    def _fill_at(self, line, t):
        """(row, x) of the sweep at moment t."""
        ws = line["words"]
        if not ws or t < ws[0]["t"]:
            return 0, 0.0
        for i, w in enumerate(ws):
            if i >= len(self.word_x):
                break
            end = w["t"] + max(w["d"], 1e-6)
            if t < w["t"]:
                return self.word_row[i], self.word_x[i]
            if t < end:
                p = (t - w["t"]) / (end - w["t"])
                return self.word_row[i], self.word_x[i] + p * self.word_w[i]
        return self.word_row[-1], self.word_x[-1] + self.word_w[-1]

    def fill_x(self, line, t) -> float:
        """How far the line is filled in at moment t (on its current row)."""
        return self._fill_at(line, t)[1]

    def hot_boxes(self, line, t):
        """Crop boxes of the lit layer: whole rows already sung, then the
        current row up to the sweep."""
        row, x = self._fill_at(line, t)
        out = []
        # The boxes live in the layer's own coordinates, and the layer now
        # begins with a strip of padding. The lit crop is pasted at the same
        # offset the dim layer was, so the two rings land on each other and
        # the sweep leaves no seam.
        top = self.pad
        for r in range(row):
            out.append((0, top + r * self.row_h, self.dim.width,
                        top + (r + 1) * self.row_h))
        if x > 0:
            out.append((0, top + row * self.row_h, int(x),
                        top + (row + 1) * self.row_h))
        return out


# The background is the same picture for every frame of a clip — and for
# every frame the studio's preview asks for, one request at a time. Built
# anew it costs a blur or a million pixel writes; remembered, a copy. The
# copy matters: the render letters the song's name straight into its
# background, and a shared image would collect one name per call.
_BG_MEMO: dict = {}


def make_background(W, H, cover_uri: str = "", dark: int = 66):
    key = (W, H, hash(cover_uri), int(dark))
    hit = _BG_MEMO.get(key)
    if hit is not None:
        return hit.copy()
    img = _draw_background(W, H, cover_uri, dark)
    if len(_BG_MEMO) > 4:
        _BG_MEMO.clear()
    _BG_MEMO[key] = img
    return img.copy()


def backdrop_fields(path, W, H, every=BACKDROP_EVERY, log=None):
    """Small blurred stills taken along a clip: the backdrop, frame by frame.

    ffmpeg does the decoding and the shrinking in one pass, which it is far
    better at than we are, and hands back raw pixels of a size a song's worth
    of them fits in memory. Each is blurred once, here, and never again: the
    render then only has to stretch one.

    A clip that cannot be read gives an empty list, and the caller falls back
    to the still cover. A backdrop is decoration; it must never be the reason
    a render fails.
    """
    from PIL import Image, ImageFilter

    sw = BACKDROP_W
    sh = max(2, int(round(sw * H / max(W, 1))) // 2 * 2)
    every = max(0.1, float(every))
    cmd = [AU.ffmpeg(), "-v", "error", "-i", path,
           "-an", "-sn",
           "-vf", (f"fps={1.0 / every:.6f},"
                   f"scale={sw}:{sh}:force_original_aspect_ratio=increase,"
                   f"crop={sw}:{sh}"),
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    size = sw * sh * 3
    fields = []
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        while True:
            raw = proc.stdout.read(size)
            if not raw or len(raw) < size:
                break
            fields.append(Image.frombytes("RGB", (sw, sh), raw)
                          .filter(ImageFilter.GaussianBlur(radius=3)))
        proc.stdout.close()
        proc.wait(timeout=30)
    except Exception:
        return []
    if log:
        log(tr(f"backdrop: {len(fields)} frames from the clip",
               f"фон: {len(fields)} кадров из клипа"))
    return fields


def _lay_scrim(img):
    """A soft dark band where the words will stand.

    The outline keeps a letter readable against anything; the band keeps the
    whole line from having to fight for it. Only pictures get one — the woven
    gradient is already quiet, and a band on it would show as a band. It is
    laid once, into the background itself, so no frame pays for it.
    """
    from PIL import Image

    W, H = img.size
    # full strength across the seats where lyrics sit, easing away above and
    # below, so the edge of the band is never a line anybody can see
    top, tin, bout, bot = 0.28, 0.40, 0.76, 0.86
    mask = Image.new("L", (1, H))
    mp = mask.load()
    for y in range(H):
        f = y / max(H - 1, 1)
        if f <= top or f >= bot:
            v = 0.0
        elif f < tin:
            v = (f - top) / (tin - top)
        elif f > bout:
            v = (bot - f) / (bot - bout)
        else:
            v = 1.0
        # eased, not linear: a straight ramp still reads as a shape
        v = v * v * (3 - 2 * v)
        mp[0, y] = int(SCRIM * 255 * v)
    return Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img,
                           mask.resize((W, H), Image.BILINEAR))


def _draw_background(W, H, cover_uri: str = "", dark: int = 66):
    from PIL import Image, ImageEnhance, ImageFilter

    if cover_uri.startswith("data:image"):
        # The clip's cover behind the lyrics: blurred hard and darkened, so it
        # sets the mood without competing with the words. A cover that cannot
        # be read falls back to the woven gradient without a word — a broken
        # image must not stop a render.
        try:
            import base64
            import io
            raw = base64.b64decode(cover_uri.partition(",")[2])
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            k = max(W / img.width, H / img.height)
            img = img.resize((max(int(img.width * k), W), max(int(img.height * k), H)))
            x0 = (img.width - W) // 2
            y0 = (img.height - H) // 2
            img = img.crop((x0, y0, x0 + W, y0 + H))
            img = img.filter(ImageFilter.GaussianBlur(radius=max(H // 55, 6)))
            k = (100 - max(0, min(95, int(dark)))) / 100.0
            return _lay_scrim(ImageEnhance.Brightness(img).enhance(k))
        except Exception:
            pass
    # Every row is one colour: a single-pixel-wide column stretched to the
    # full width says the same thing as a million pixel writes, in a
    # thousandth of the time.
    col = Image.new("RGB", (1, H))
    px = col.load()
    for y in range(H):
        f = y / max(H - 1, 1)
        px[0, y] = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * f)
                         for i in range(3))
    return col.resize((W, H), Image.NEAREST)


# ---------------------------------------------------------------- render
def render(payload, audio_wav, out_path, args, on_progress=None):
    from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageStat

    apply_colors(payload)
    if on_progress:
        # Show in the window right away what song and which colours are being
        # drawn: an empty log looks like nothing is happening.
        for row in video_report(payload, args, AU.duration(audio_wav),
                                min(args.seconds or 1e9,
                                    AU.duration(audio_wav) - args.start)).splitlines():
            if row.strip():
                on_progress(row)
    D = payload["data"]
    lines = D["lines"]
    if not lines:
        raise SystemExit(tr("The page has no lyrics.", "В странице нет текста."))
    duration = AU.duration(audio_wav)

    W, H = args.width, args.height
    margin = int(W * 0.06)
    font_path = find_font(args.font)
    base_main = int(H * 0.072)
    base_side = int(H * 0.042)
    cache_font = {}

    def font_for(text, max_w, main):
        size = base_main if main else base_side
        # the width belongs in the key: the same text is measured both against
        # the frame and against nothing at all, to decide whether to wrap
        key = (text, size, max_w)
        if key in cache_font:
            return cache_font[key]
        f = ImageFont.truetype(font_path, size)
        # the floor scales with the seat: a side font can start BELOW a fixed
        # floor, and then a long line simply ran off the edge, unshrunk
        floor = max(10, min(18, size - 2))
        while size > floor and f.getlength(text) > max_w:
            size -= 2
            f = ImageFont.truetype(font_path, size)
        cache_font[key] = f
        return f

    def fitted(text, size, max_w):
        """A font of the asked size, stepped down until the text fits."""
        f = ImageFont.truetype(font_path, size)
        while size > 18 and f.getlength(text) > max_w:
            size -= 2
            f = ImageFont.truetype(font_path, size)
        return f

    # One background — or a slow slideshow of them, when the cover came as
    # frames cut from the clip. Each carries the song's name; the switch is a
    # slow crossfade, timed by the song's own length.
    cover_uris = [u for u in (payload.get("covers") or []) if u]
    if not cover_uris:
        cover_uris = [payload.get("cover") or ""]
    cover_dark = int(payload.get("coverDark") or 66)
    bgs = [make_background(W, H, u, cover_dark) for u in cover_uris]
    bg = bgs[0]
    # A clip may stand behind the lyrics instead of a still. If it cannot be
    # read, the still cover is still there: a backdrop is decoration, never a
    # reason for a render to fail.
    back_path = getattr(args, "backdrop", None)
    fields = (backdrop_fields(back_path, W, H, log=on_progress)
              if back_path and os.path.isfile(back_path) else [])
    small = ImageFont.truetype(font_path, int(H * 0.020))
    # The song's name deserves better than the caption size — and its own
    # font, so growing it does not swell every section heading with it.
    name_font = ImageFont.truetype(font_path, int(H * 0.028))
    # The countdown pill: readable from a couch, which the small caption font
    # was not. It still sits in the top strip where no lyrics are ever drawn,
    # so nothing gets covered — the strip only grows a little.
    pill_font = ImageFont.truetype(font_path, int(H * 0.030))

    art, art_side = {}, {}

    art_duo = {}

    def get(i, main=True, duo_side=False):
        store = art_duo if duo_side else (art if main else art_side)
        if i not in store:
            if len(store) > 10:
                # the oldest goes, not the whole shelf: clearing everything
                # made the very lines on screen be typeset again
                store.pop(next(iter(store)))
            store[i] = LineArt(lines[i], font_for, W, margin, main,
                               align="right" if duo_side else "center")
        return store[i]

    starts = [ln["start"] for ln in lines]
    # The song is over when its last sound has faded — and the last sound is
    # not always the last line: a na-na-na is written after the lead it sings
    # under, and a lead can outlast the backing that started later. Asking the
    # array which line is last cleared the stage while somebody was still
    # singing, or left the backing hanging alone at the end.
    song_end = max(ln["end"] for ln in lines)
    # The line already sung is dead weight on the screen — the eye never goes
    # back to it. The frame holds the current line and the queue ahead: the
    # next line, and the one after it fainter still. Slightly above centre, so
    # the group sits balanced.
    y_main = int(H * 0.44)
    y_next = int(H * 0.60)
    y_next2 = int(H * 0.72)

    # Which line each seat held last, and since when — so a newcomer can fade
    # in. The film walks time forward frame by frame, which makes this honest;
    # a single still frame skips the fade and stands steady.
    # The lines do not swap places, they ride: when the singing moves on, the
    # whole column slides up by one step and the line at the top leaves the
    # frame as it goes. Standing still they sit exactly where they always sat.
    slide = [None, None, 0.0]  # who holds the main seat, who held it, since when
    STEP = y_next - y_main     # one line of the column
    SLIDE = 0.32               # how long the ride takes
    fading = getattr(args, "still", None) is None

    def paste_faded(frame, img, pos, alpha):
        if alpha >= 1.0:
            frame.paste(img, pos, img)
            return
        mask = img.getchannel("A").point(lambda v: int(v * alpha))
        frame.paste(img, pos, mask)

    def draw_queue(frame, n1, duo=-1, off=0, alpha=1.0):
        """The line coming next, and the one after it fainter still — the
        singer reads forward, never back. The count-in shows the same queue,
        so nothing jumps when the music finally starts."""
        nx = get(n1, False)
        paste_faded(frame, nx.dim, (0, y_next - nx.h // 2 + off), alpha)
        n2i = next_sung(lines, n1)
        if n2i < len(lines) and n2i != duo:
            n2 = get(n2i, False)
            paste_faded(frame, n2.faint, (0, y_next2 - n2.h // 2 + off), alpha)

    t_start = args.start
    if t_start >= duration:
        raise SystemExit(tr(
            f"--start {t_start:g} s is past the end of the song "
            f"({int(duration//60)}:{duration%60:05.2f}) — there is nothing to render.",
            f"--start {t_start:g} с выходит за конец песни "
            f"({int(duration//60)}:{duration%60:05.2f}) — рендерить нечего."))
    t_end = min(duration, t_start + args.seconds) if args.seconds else duration
    total_frames = max(int((t_end - t_start) * args.fps), 1)

    # The opening runs before the music, and only when the render begins at the
    # song's own beginning: a piece cut from the middle is a preview, and a
    # title card in front of it would only be in the way.
    card_name = str(D.get("title") or "").strip()
    card_artist = str(D.get("artist") or "").strip()
    lead = intro_lead(args, card_name) if t_start <= 0 else 0.0
    lead_frames = int(lead * args.fps)

    cmd = [AU.ffmpeg(), "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(args.fps), "-i", "-",
           "-ss", f"{t_start}", "-i", audio_wav]
    if lead > 0:
        # The song waits for the opening: the picture starts, the sound joins.
        cmd += ["-af", f"adelay={int(lead * 1000)}:all=1"]
    cmd += ["-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", out_path]
    # The frame speaks the song's language; the log below keeps speaking the
    # program's, because it is read by the person at the keyboard.
    said = frame_lang(payload)
    title = (D.get("title") or "") + ((" — " + D["artist"]) if D.get("artist") else "")

    # The name in the corner never changes, and drawing it anew on each of
    # thousands of frames was pure ceremony: it is painted into the background
    # once, and every frame starts from a copy that already carries it.
    shown_name = ""
    if title:
        shown_name = title
        while len(shown_name) > 8 \
                and name_font.getlength(shown_name) > W - 2 * margin:
            shown_name = shown_name[:-2].rstrip() + "\u2026"

    def stamp_name(img):
        """The name in its corner. Painted into a still background once; on a
        clip, where no two frames are the same picture, painted onto each
        stretched field as it is made — still once per several frames, never
        once per frame."""
        if shown_name:
            ImageDraw.Draw(img).text((margin, int(H * 0.028)), shown_name,
                                     font=name_font, fill=(132, 140, 168),
                                     **edged(name_font))
        return img

    if shown_name and not fields:
        for one in bgs:
            stamp_name(one)

    # The beat, when the song keeps one and the singer asked to see it. Four
    # dots in the bottom corner, one to a beat of the bar: enough to come in on
    # without anything standing between a person and the words. It is drawn
    # from the tempo they typed, so it is exactly as right as that number is.
    beat_at = payload.get("grid") or None
    beat_len = (60.0 / max(20.0, min(300.0, float(beat_at.get("bpm") or 120)))
                if beat_at else 0.0)
    beat_zero = float(beat_at.get("beat0") or 0.0) if beat_at else 0.0

    def furniture(d, prog, at=None):
        """The bar along the bottom: on every frame, the opening included."""
        bar_y, bar_h = int(H * 0.955), max(int(H * 0.004), 2)
        d.rectangle([margin, bar_y, W - margin, bar_y + bar_h], fill=(40, 45, 68))
        if prog > 0:
            d.rectangle([margin, bar_y, margin + (W - 2 * margin) * prog,
                         bar_y + bar_h], fill=COL_BAR)
        if beat_len <= 0 or at is None:
            return
        # Which beat of the bar, and how long ago it struck: the dot flashes
        # and falls back, rather than staying lit for the whole beat, so the
        # eye reads a pulse and not a row of lamps.
        n = int(math.floor((at - beat_zero) / beat_len))
        since = (at - beat_zero) - n * beat_len
        fade = max(0.0, 1.0 - since / max(min(beat_len * 0.55, 0.20), 1e-6))
        r = max(2, int(round(H * 0.0055)))
        gap = max(3 * r, int(H * 0.024))
        y0 = bar_y - int(H * 0.030)
        x0 = W - margin - gap * 3
        for i in range(4):
            lit = (n % 4) == i
            hue = COL_HOT if i == 0 else COL_BAR
            k = fade if lit else 0.0
            col = _mix(COL_PIP, hue, k)
            rr = r + (1 if lit and i == 0 else 0)
            cx = x0 + gap * i
            d.ellipse([cx - rr, y0 - rr, cx + rr, y0 + rr], fill=col)

    # The opening: the name held large, then three, two, one. The music is
    # delayed by exactly as long, so nobody is caught mid-breath.
    card_font = (fitted(card_name, int(H * 0.095), W - 2 * margin)
                 if card_name and lead else None)
    art_font = (fitted(card_artist, int(H * 0.042), W - 2 * margin)
                if card_artist and lead else None)
    num_font = ImageFont.truetype(font_path, int(H * 0.060)) if lead else None

    XFADE = 1.2

    # A clip's field is stretched once and then serves several frames: at
    # that blur nothing moves fast enough for the eye to catch the hold, and
    # the stretch is the whole cost of a moving backdrop.
    held = {"slot": None, "img": None}
    eased = {"k": None}

    def field_at(t):
        """The clip's field due at second `t`, between the two sampled."""
        i = max(0.0, t) / BACKDROP_EVERY
        a = min(len(fields) - 1, max(0, int(i)))
        b = min(len(fields) - 1, a + 1)
        f = i - int(i)
        if a == b or f <= 0.001:
            return fields[a]
        return Image.blend(fields[a], fields[b], min(max(f, 0.0), 1.0))

    def fit_dark(sm):
        """How far to pull this field down.

        A still cover is darkened by the one number the singer chose. A clip
        will not hold still: the number that suited a dark shot blows out on
        the next cut. So the band where the words stand is measured, and the
        darkening is whatever keeps it from going bright — never lighter than
        the singer asked for. It moves slowly, or a cut would pump the whole
        frame.
        """
        base = (100 - max(0, min(95, cover_dark))) / 100.0
        w0, h0 = sm.size
        band = sm.crop((0, int(h0 * 0.40), w0, int(h0 * 0.76))).convert("L")
        lit = ImageStat.Stat(band).mean[0] or 1.0
        want = min(base, BACKDROP_LIT / lit)
        prev = eased["k"]
        if prev is None:
            eased["k"] = want
        else:
            step = BACKDROP_DROP if want < prev else BACKDROP_LIFT
            eased["k"] = prev + (want - prev) * step
        return max(0.04, min(1.0, eased["k"]))

    def clip_bg(t):
        slot = int(max(0.0, t) * max(args.fps, 1)) // BACKDROP_HOLD
        if held["slot"] != slot:
            sm = field_at(t)
            sm = ImageEnhance.Brightness(sm).enhance(fit_dark(sm))
            held["slot"] = slot
            held["img"] = stamp_name(_lay_scrim(sm.resize((W, H), Image.BILINEAR)))
        return held["img"].copy()

    def bg_for(t):
        """The background under second `t` of the song: one picture, the
        slideshow frame due at that moment, or the clip standing behind."""
        if fields:
            return clip_bg(t)
        if len(bgs) < 2:
            return bg.copy()
        step = duration / len(bgs)
        i = min(len(bgs) - 1, max(0, int(t / step)))
        into = t - i * step
        if i + 1 < len(bgs) and into > step - XFADE:
            k = (into - (step - XFADE)) / XFADE
            return Image.blend(bgs[i], bgs[i + 1], min(max(k, 0.0), 1.0))
        return bgs[i].copy()

    def intro_frame(tt):
        """A frame of the opening, `tt` seconds into it."""
        # The opening stands on the clip's first field, not on a still it
        # would then jump away from when the music starts.
        frame = clip_bg(0.0) if fields else bg.copy()
        d = ImageDraw.Draw(frame)
        if card_font and tt < INTRO_CARD:
            d.text((W // 2, int(H * 0.44)), card_name, font=card_font,
                   fill=_mix(COL_HOT, (255, 255, 255), 0.30), anchor="mm",
                   **edged(card_font))
            if art_font:
                d.text((W // 2, int(H * 0.58)), card_artist, font=art_font,
                       fill=COL_DIM, anchor="mm", **edged(art_font))
        else:
            # The count stands small in the seat where the singing will be,
            # and the first words are already below it: a figure filling the
            # frame hid the very text people are about to sing, and there is
            # no reading it in three seconds if it only appears when the music
            # does.
            left = max(lead - tt, 0.0)
            d.text((W // 2, y_main), str(int(math.ceil(left)) or 1),
                   font=num_font, fill=COL_HOT, anchor="mm", **edged(num_font))
            first = next_sung(lines, -1)
            if first < len(lines):
                draw_queue(frame, first)
        # The opening counts in the same beat the song will keep: the intro
        # runs before second zero, so its time is negative here and the beats
        # walk backwards into the song.
        furniture(d, 0.0, at=tt - lead)
        return frame

    def song_frame(t):
        """A frame of the song itself, at second `t` of the recording."""
        frame = bg_for(t)
        d = ImageDraw.Draw(frame)

        idx = bisect.bisect_right(starts, t) - 1

        # A line that runs past the start of the next one keeps the main seat
        # until the NEXT one is finished: the pair stands together like a
        # duet — the older above, the newer smaller below — and nothing jumps
        # seats mid-line. Sung words must not vanish mid-word just because
        # the line after them has begun.
        # The pair is found among the LEADS: a backing line starting over a
        # runover must not break it up — with three voices sounding and two
        # seats in the frame, the words the singer sings win, and the
        # na-na-na waits for a free seat.
        runover = -1
        lead = idx
        while lead > 0 and lines[lead].get("backing"):
            lead -= 1
        if lead > 0 and not lines[lead].get("backing") \
                and t < max(lines[lead]["end"], lines[lead - 1]["end"]) \
                and lines[lead - 1]["end"] > lines[lead]["start"] \
                and not lines[lead - 1].get("backing") \
                and (lines[lead].get("voice") == 2) \
                == (lines[lead - 1].get("voice") == 2):
            runover = lead
            idx = lead - 1

        # The second voice can sound together with the main one. It is drawn
        # on its own row below — otherwise the two texts would overlap.
        duo = runover
        if idx >= 0 and duo < 0:
            for j in (idx - 1, idx + 1):
                if 0 <= j < len(lines) and lines[j]["start"] <= t < lines[j]["end"] \
                        and (lines[j].get("voice") == 2) != (lines[idx].get("voice") == 2):
                    duo = j
                    break

        # The song has been sung: after a few seconds the seat empties. A
        # last line hanging lit to the end of the recording reads as a
        # frozen picture, not as an ending.
        over_k = max(0.0, min(1.0, (t - song_end - END_HOLD) / 0.4))
        over = over_k >= 1.0
        scene_alpha = 1.0 - over_k

        # Who will sit where this frame — decided before a single pixel is
        # laid down, so a seat changing hands can hand its old occupant to
        # the ghosts in the SAME frame. Deciding it afterwards left exactly
        # one blank frame at every line change: the flash.
        if fading:
            occ = {}
            if not over and idx >= 0:
                if lines[idx].get("backing") and duo < 0:
                    occ["side"] = idx
                else:
                    pair0 = [idx] if duo < 0 else sorted(
                        [idx, duo], key=lambda j: lines[j].get("voice") == 2)
                    occ["main"] = pair0[0]
                    if len(pair0) > 1:
                        occ["side"] = pair0[1]
                q1 = next_sung(lines, idx)
                if q1 < len(lines) and q1 != duo:
                    occ["next"] = q1
                    q2 = next_sung(lines, q1)
                    if q2 < len(lines) and q2 != duo:
                        occ["next2"] = q2
            # The column rides: when the main seat changes hands, everything
            # slides up one step over SLIDE seconds and the line leaving the
            # top goes with it, fading as it rises out of the frame.
            if occ.get("main") != slide[0]:
                slide[1] = slide[0]
                slide[0] = occ.get("main")
                slide[2] = t
            ride = (min(1.0, (t - slide[2]) / SLIDE)
                    if slide[0] is not None else 1.0)
            ride = 1.0 - (1.0 - ride) ** 3            # eased: quick, then settling
            off = int(round((1.0 - ride) * STEP))
            # the line that left the main seat, riding up and out
            if slide[1] is not None and ride < 1.0 and not over:
                gpic = get(slide[1], main=True)
                gy = y_main - gpic.h // 2 - int(round(ride * STEP))
                galpha = (1.0 - ride) * scene_alpha
                paste_faded(frame, gpic.dim, (0, gy), galpha)
                if gpic.hot is not None:
                    for bx in gpic.hot_boxes(lines[slide[1]], lines[slide[1]]["end"]):
                        paste_faded(frame, gpic.hot.crop(bx),
                                    (bx[0], gy + bx[1]), galpha)
        else:
            off = 0
        singing = idx >= 0 and (t < lines[idx]["end"]
                                or (runover >= 0
                                    and t < lines[runover]["end"]))

        duo_bottom = 0
        if not over and idx >= 0 and lines[idx].get("backing") and duo < 0:
            # The backing singing alone — the lead has ended, the na-na-na
            # carries on. It used to be promoted to the main seat, full
            # size, in the lead's way. It keeps its side seat instead: the
            # main seat stays empty, and the queue below points at the next
            # lead line as always.
            pic = get(idx, main=False, duo_side=True)
            y_b = y_main + int(H * 0.036) + off
            a_b = scene_alpha
            paste_faded(frame, pic.dim, (0, y_b), a_b)
            for bx in pic.hot_boxes(lines[idx], t):
                piece = pic.hot.crop(bx)
                paste_faded(frame, piece, (bx[0], y_b + bx[1]), a_b)
            duo_bottom = y_b + pic.h
        elif not over and idx >= 0:
            # The lead stays exactly where a solo line sits; the backing is
            # smaller, to the right, tucked under it like a reply — two full
            # rows used to collide with the dots and the queue.
            pair = [idx] if duo < 0 else sorted(
                [idx, duo], key=lambda j: lines[j].get("voice") == 2)
            y_j = 0
            for k, j in enumerate(pair):
                is_back = k == 1
                pic = get(j, main=not is_back, duo_side=is_back)
                if not is_back:
                    y_j = y_main - pic.h // 2 + off
                    # a wrapped line is taller: everything below must yield
                    duo_bottom = max(duo_bottom, y_j + pic.h)
                else:
                    y_j = y_j + get(pair[0]).h + int(H * 0.002)
                    duo_bottom = y_j + pic.h
                a_j = scene_alpha
                paste_faded(frame, pic.dim, (0, y_j), a_j)
                for bx in pic.hot_boxes(lines[j], t):
                    piece = pic.hot.crop(bx)
                    paste_faded(frame, piece, (bx[0], y_j + bx[1]), a_j)
                if k == 0 and lines[j].get("section"):
                    d.text((margin, y_j - int(H * 0.055)),
                           lines[j]["section"].upper(), font=small,
                           fill=COL_SECT, **edged(small))
                if k == 0 and lines[j].get("keep") and lines[j].get("keepSoft"):
                    # A quiet original is an invitation — say so beside the
                    # line. A full-voice one needs no caption: the voice
                    # itself says the line is not yours.
                    tag = ("в унисон с оригиналом" if said == "ru"
                           else "sing along with the original")
                    d.text((W - margin, y_j - int(H * 0.055)), tag,
                           font=small, fill=_mix(COL_DIM, (255, 255, 255), 0.3),
                           anchor="ra", **edged(small))

        # Guide dots: a countdown, not decoration. On the page they are
        # separators in a scrolling list; a frame has no scroll, so here
        # they show up only once the singing has stopped and the wait is
        # long enough to be worth counting.
        def dots(cy, lit=0):
            r = max(int(H * 0.0055), 3)
            for k in range(3):
                x = W // 2 + (k - 1) * r * 5
                d.ellipse([x - r, cy - r, x + r, cy + r],
                          fill=COL_HOT if k < lit else COL_PIP)

        n1 = next_sung(lines, idx)
        if not over and n1 < len(lines) and n1 != duo:
            draw_queue(frame, n1, duo, off, scene_alpha)

            gap = lines[n1]["start"] - (lines[idx]["end"] if idx >= 0 else 0)
            left = lines[n1]["start"] - t
            if not singing and gap > PIP_MIN_GAP:
                dots(max((y_main + y_next) // 2 + off,
                         duo_bottom + int(H * 0.018)), pips_lit(gap, left))

        # While nobody sings the screen is empty and it is unclear whether
        # the song is running. At the top — a countdown to the next line, as
        # in the program itself. Short gaps are not counted: they are obvious.
        nxt = None
        for ln in lines:
            if ln["start"] > t and not ln.get("backing"):
                nxt = ln
                break
        if not singing:
            prev_end = lines[idx]["end"] if idx >= 0 else 0.0
            gap = (nxt["start"] - prev_end) if nxt else (duration - prev_end)
            # Ten seconds, as in the program itself: a shorter gap is a
            # breath between lines, and counting it down is noise.
            if gap >= 10.0:
                left = (nxt["start"] if nxt else duration) - t
                # The pill is built around the text, and the text sits in its
                # centre — horizontally and vertically.
                # Low enough that even a wide pill clears the song's
                # name in the corner above.
                cx, cy = W // 2, int(H * 0.135)
                txt = pill_text(said, idx, nxt, left)
                box = d.textbbox((0, 0), txt, font=pill_font)
                tw, th = box[2] - box[0], box[3] - box[1]
                pad_x, pad_y = int(H * 0.030), int(H * 0.022)
                d.rounded_rectangle(
                    [cx - tw // 2 - pad_x, cy - th // 2 - pad_y,
                     cx + tw // 2 + pad_x, cy + th // 2 + pad_y],
                    radius=int(th // 2 + pad_y),
                    fill=_mix(BG_TOP, (255, 255, 255), 0.10),
                    outline=_mix(BG_TOP, (255, 255, 255), 0.28))
                d.text((cx, cy), txt, font=pill_font,
                       fill=_mix(COL_DIM, (255, 255, 255), 0.35), anchor="mm")
                # The bar is centred too, right under the pill.
                bw = max(int(W * 0.16), tw // 2)
                bx, by = cx - bw // 2, cy + th // 2 + pad_y + int(H * 0.012)
                bh = max(int(H * 0.004), 2)
                done_k = 0.0 if gap <= 0 else min(max((t - prev_end) / gap, 0), 1)
                d.rectangle([bx, by, bx + bw, by + bh],
                            fill=_mix(BG_TOP, (255, 255, 255), 0.18))
                d.rectangle([bx, by, bx + int(bw * done_k), by + bh], fill=COL_HOT)

        furniture(d, min(max(t / duration, 0), 1), at=t)
        return frame

    # One frame to look at, instead of a clip to wait for: the studio shows
    # what a place in the song will look like without encoding anything. The
    # very same drawing, so the preview cannot lie about the result.
    still = getattr(args, "still", None)
    if still is not None:
        at = max(0.0, float(still))
        (intro_frame(at) if at < lead
         else song_frame(min(t_start + at - lead, duration))).save(out_path)
        return

    # The encoder is started only now: a single frame needs no encoder at all,
    # and one left waiting on a pipe that never opens writes a broken file.
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    t0 = time.time()
    try:
        for n in range(lead_frames):
            proc.stdin.write(intro_frame(n / args.fps).tobytes())
        for n in range(total_frames):
            proc.stdin.write(song_frame(t_start + n / args.fps).tobytes())

            if n % (args.fps * 5) == 0 or n == total_frames - 1:
                done = (lead_frames + n + 1) / (lead_frames + total_frames)
                el = time.time() - t0
                eta = el / done - el if done > 0.01 else 0
                msg = (tr("frame ", "кадр ")
                       + f"{lead_frames + n + 1}/{lead_frames + total_frames}"
                       + f"  {done*100:5.1f}%  "
                       + tr("left ~", "осталось ~")
                       + f"{int(eta)//60}:{int(eta)%60:02d}")
                if on_progress:
                    on_progress(msg)
                else:
                    print("\r  " + msg, end="", flush=True)
        print()
    except BrokenPipeError:
        pass
    finally:
        if proc.stdin:
            proc.stdin.close()
        err = proc.stderr.read().decode(errors="replace")
        code = proc.wait()

    if code != 0:
        raise SystemExit(tr("ffmpeg failed:\n", "ffmpeg завершился с ошибкой:\n") + err[-800:])
    return out_path


def apply_timings(payload: dict, path: str) -> None:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    src = data.get("lines", data if isinstance(data, list) else [])
    cur = payload["data"]["lines"]
    if len(src) != len(cur):
        raise SystemExit(tr(f"{path} has {len(src)} lines, the page has {len(cur)}.",
                            f"В {path} {len(src)} строк, а в странице {len(cur)}."))
    for ln, s in zip(cur, src):
        ln["start"], ln["end"] = float(s["start"]), float(s["end"])
        for w, sw in zip(ln["words"], s.get("words") or []):
            w["t"], w["d"] = float(sw["t"]), float(sw["d"])
    print(tr(f"Timings taken from {os.path.basename(path)}",
                  f"Тайминги взяты из {os.path.basename(path)}"))


def list_pages(folder: str) -> list:
    """Karaoke pages in a folder — ours first."""
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    pages = [os.path.join(folder, n) for n in names if n.lower().endswith(".html")]
    pages.sort(key=lambda p: (0 if ("karaoke" in os.path.basename(p).lower()
                                    or "караоке" in os.path.basename(p).lower()) else 1,
                              os.path.basename(p).lower()))
    return pages


def pick_pages() -> list:
    """Nothing was dropped in — show what is around and let one be chosen."""
    seen, pages = set(), []
    for folder in (os.getcwd(), ROOT):
        for p in list_pages(folder):
            key = os.path.abspath(p).lower()
            if key not in seen:
                seen.add(key)
                pages.append(p)

    if not pages:
        print(tr("There is no built karaoke page next to this script.",
                  "Рядом нет ни одной собранной страницы караоке."))
        print(tr("Drag an HTML file onto Make-video.bat — or give the path.",
                  "Перетащите HTML-файл на «Make-video.bat» — или укажите путь."))
        return []
    if len(pages) == 1:
        print(tr(f"Found one page: {os.path.basename(pages[0])}",
                  f"Нашёл одну страницу: {os.path.basename(pages[0])}"))
        return pages

    print(tr("Karaoke pages found:\n", "Нашёл страницы караоке:\n"))
    for i, p in enumerate(pages, 1):
        mb = os.path.getsize(p) / 1024 / 1024
        print(f"  {i:2}. {os.path.basename(p)}  ({mb:.1f} " + tr("MB", "МБ") + ")")
    print(tr("\n   0. all of them", "\n   0. все сразу"))
    try:
        ans = input(tr("\nNumber (Enter — the first one): ",
                       "\nНомер (Enter — первая): ")).strip()
    except EOFError:
        return pages[:1]
    if not ans:
        return pages[:1]
    if ans == "0":
        return pages
    if ans.isdigit() and 1 <= int(ans) <= len(pages):
        return [pages[int(ans) - 1]]
    print(tr("I did not understand the choice.", "Не понял выбор."))
    return []


def find_timings(html_path: str):
    """Timing edits exported from the player and left next to the page."""
    folder = os.path.dirname(os.path.abspath(html_path))
    stem = os.path.splitext(os.path.basename(html_path))[0].lower()
    best = None
    for name in sorted(os.listdir(folder)):
        low = name.lower()
        if not low.endswith(".json"):
            continue
        if "timings" in low or "тайминг" in low:
            # a file named after the song beats a plain timings.json
            if os.path.splitext(low)[0].replace("_timings", "").strip("_ -") in stem:
                return os.path.join(folder, name)
            best = best or os.path.join(folder, name)
    return best


def _try_timings(payload: dict, path: str) -> bool:
    """Apply an edits file found next to the page. If it belongs to another
    song, just skip it: a stray JSON must not abort the render."""
    try:
        apply_timings(payload, path)
        return True
    except SystemExit as e:
        print(f"  {e}")
        print(tr("  This file does not fit the song — taking the timing from the page.",
                      "  Этот файл к песне не подходит — беру разметку из самой страницы."))
        return False


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="video.py", description="An MP4 karaoke clip from a finished HTML page.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("html", nargs="*",
                   help="pages, or a folder with them; with no arguments — pick from a list")
    p.add_argument("-o", "--output", help="where to save the MP4")
    p.add_argument("--audio", choices=["minus", "guide", "original"], default="minus",
                   help="minus — the instrumental (default), guide — with a quiet vocal, "
                        "original — as recorded")
    p.add_argument("--timings", help="a JSON with timing edits from the player")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--crf", type=int, default=20, help="quality: lower is better (18–24)")
    p.add_argument("--preset", default="medium", help="x264 encoding speed")
    p.add_argument("--font", help="path to a .ttf")
    p.add_argument("--backdrop",
                   help="a clip to stand behind the lyrics, blurred to a "
                        "slow field of colour")
    p.add_argument("--start", type=float, default=0.0, help="start from this second")
    p.add_argument("--seconds", type=float, default=0.0, help="render only N seconds (a sample)")
    p.add_argument("--no-intro", dest="intro", action="store_false",
                   help="start with the song instead of the name and a count of three")
    args = p.parse_args(argv)

    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print(tr("The Pillow library is needed:\n    pip install pillow",
                  "Нужна библиотека Pillow:\n    pip install pillow"), file=sys.stderr)
        return 1

    targets = []
    for a in args.html:
        if os.path.isdir(a):
            targets += list_pages(a)
        elif os.path.isfile(a):
            targets.append(a)
        else:
            print(tr(f"Not found: {a}", f"Не найдено: {a}"))
    if not args.html:
        targets = pick_pages()
    if not targets:
        return 2
    if args.output and len(targets) > 1:
        print(tr("-o was given but there are several pages — I will name them after "
                     "the files.",
                     "Ключ -o задан, а страниц несколько — имена сделаю по названиям файлов."))
        args.output = None

    AU.ffmpeg()
    failed = 0
    for k, html_path in enumerate(targets, 1):
        if len(targets) > 1:
            print(f"\n[{k}/{len(targets)}] {os.path.basename(html_path)}\n" + "-" * 60)
        try:
            failed += render_one(html_path, args)
        except SystemExit as e:
            print(tr(f"  error: {e}", f"  ошибка: {e}"))
            failed += 1
    return 1 if failed else 0


def video_report(payload, args, song: float, want: float) -> str:
    """What the song is and what will happen to it — before the long drawing.

    There is such a report before a page is built, but there was none before a
    clip: a mistake — the wrong audio, the wrong colours, forgotten marks —
    could only be seen on the finished file, ten minutes later.
    """
    D = payload.get("data") or {}
    lines = D.get("lines") or []
    v2 = sum(1 for l in lines if l.get("voice") == 2)
    kept = keep_spans(payload)
    kept_s = sum(b - a for a, b, _ in kept)
    colors = payload.get("colors") or []
    theme = payload.get("theme") or {}
    duo = 0
    for i, a in enumerate(lines):
        for b in lines[i + 1:]:
            if b["start"] >= a["end"]:
                break
            if (b.get("voice") == 2) != (a.get("voice") == 2):
                duo += 1
    audio_name = {"minus": tr("instrumental", "минусовка"),
                  "guide": tr("instrumental + quiet vocal", "минусовка + тихий вокал"),
                  "original": tr("the original", "оригинал")}.get(args.audio, args.audio)
    lead = intro_lead(args, str(D.get("title") or "").strip()) if not getattr(args, "start", 0) else 0.0
    fps, frames = args.fps, int((want + lead) * args.fps)
    rows = [
        (tr("Song", "Песня"), (D.get("title") or "—") +
         ((" — " + D["artist"]) if D.get("artist") else "")),
        (tr("Length", "Длина"), mmss(song) +
         (tr(f", rendering {mmss(want)}", f", рисуем {mmss(want)}") if want < song - 0.05 else "")),
        (tr("Lines", "Строк"), f"{len(lines)}" +
         (tr(f", second voice: {v2}", f", второй голос: {v2}") if v2 else "")),
        (tr("Together", "Одновременно"),
         tr(f"{duo} place{'s' if duo != 1 else ''} where two voices sing at once",
            f"{duo} мест, где поют вдвоём")
         if duo else tr("voices do not overlap", "голоса не пересекаются")),
        (tr("Original sings", "Поёт оригинал"),
         tr(f"{len(kept)} stretch{'es' if len(kept) != 1 else ''}, {kept_s:.0f} s",
            f"{len(kept)} кусков, {kept_s:.0f} с")
         if kept else tr("nothing marked", "не отмечено")),
        (tr("Colours", "Цвета"), ", ".join(colors) if colors else tr("default", "по умолчанию")),
        (tr("Look", "Оформление"),
         f"{theme.get('bg')} / {theme.get('text')}" if theme.get("bg")
         else tr("default", "по умолчанию")),
        (tr("Audio", "Звук"), audio_name),
        (tr("Opening", "Заставка"),
         tr(f"the name, then a count of three — {mmss(lead)}",
            f"название и счёт до трёх — {mmss(lead)}")
         if lead else tr("none, the song starts at once",
                         "нет, песня начинается сразу")),
        (tr("Frames", "Кадров"), f"{frames} ({fps} " + tr("fps", "к/с") + ")"),
    ]
    width = max(len(k) for k, _ in rows) + 2
    out = ["", tr("Before rendering", "Отчёт перед роликом"), "─" * 46]
    out += [f"  {k.ljust(width)}{v}" for k, v in rows]
    if not colors:
        out.append(tr("  ! The page has no colours of its own — the video takes the "
                      "defaults.", "  ! В странице нет своих цветов — ролик возьмёт "
                      "стандартные."))
    out.append("")
    return "\n".join(out)


def render_one(html_path: str, args) -> int:
    payload = B.read_payload(html_path)

    timings = args.timings or find_timings(html_path)
    if timings:
        if not args.timings:
            print(tr(f"Timing edits found next to it: {os.path.basename(timings)} — taking them.",
                  f"Рядом лежат правки разметки: {os.path.basename(timings)} — беру их."))
        if not _try_timings(payload, timings):
            timings = None
    elif payload.get("edited"):
        print(tr("The timing comes from the page — it already has your edits.",
                  "Разметка взята из страницы — она уже с вашими правками."))
    else:
        print(tr("The timing comes from the page itself (machine-made).",
                  "Разметка взята из самой страницы (машинная)."))
        print(tr("  If you edited it in the player, note: the edits live in the browser,",
                  "  Если вы правили её в плеере, учтите: правки хранятся в браузере, а не"))
        print(tr("  not in the file, and will not reach the video. In the player press",
                  "  в файле, и в ролик не попадут. Нажмите в плеере «Правка» →"))
        print(tr("  “Edit” → “Save page with edits” and make the video from that page.",
                  "  «Сохранить страницу с правками» и делайте видео из сохранённой страницы."))

    out = args.output or os.path.splitext(html_path)[0] + ".mp4"
    tmp = tempfile.mkdtemp(prefix="karaoke_video_")
    t0 = time.time()
    try:
        wav = extract_audio(payload, html_path, tmp, args.audio)
        song = AU.duration(wav)
        want = min(song - args.start, args.seconds) if args.seconds else song - args.start
        print(video_report(payload, args, song, want))
        print(tr(f"Frame {args.width}×{args.height}, {args.fps} fps, "
                 f"video length {mmss(want)}. Drawing…",
                 f"Кадр {args.width}×{args.height}, {args.fps} к/с, "
                 f"длина ролика {mmss(want)}. Рисую…"))
        render(payload, wav, out, args)

        size = os.path.getsize(out) / 1024 / 1024
        got = None
        try:
            got = AU.duration(out)
        except Exception:
            pass
        # Print the video LENGTH explicitly, not just the build time: the two
        # get confused, and a truncated file is easy to miss.
        spent = int(time.time() - t0)
        print(tr(f"\nDone: {out}", f"\nГотово: {out}"))
        print(tr(f"  video length : {mmss(got) if got else '?'}   ({size:.1f} MB)",
                  f"  длина ролика : {mmss(got) if got else '?'}   ({size:.1f} МБ)"))
        print(tr(f"  built in     : {spent // 60}:{spent % 60:02d}",
                  f"  собрано за   : {spent // 60}:{spent % 60:02d}"))
        if got and abs(got - want) > 1.0:
            print(tr(f"\n  NOTE: {mmss(want)} was expected but {mmss(got)} came out — "
                     f"the video is cut short.\n  Send this output, it is a bug.",
                     f"\n  ВНИМАНИЕ: ожидалась длина {mmss(want)}, а получилось {mmss(got)} — "
                     f"ролик обрезан.\n  Пришлите этот вывод, это ошибка программы."))
        else:
            print(tr("\nThe file can go straight to YouTube.",
                  "\nФайл можно заливать на YouTube как есть."))
        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
