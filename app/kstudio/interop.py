"""The timing, spoken in other programs' languages.

Months of timing work should not be locked into one player. Two doors out:
UltraStar — the format the singing games read — and .ass subtitles with
karaoke tags, which video editors and players understand.

Both are written from the same saved record the editor keeps, so what was
fixed by hand is what leaves the house.
"""
from __future__ import annotations

import math
from typing import Dict, List

from .i18n import tr

# UltraStar measures time in quarter-beats of the file's own BPM. The number
# is not music, it is a ruler: 300 “BPM” makes one tick 50 ms — fine enough
# for singing, coarse enough that the numbers stay readable.
US_BPM = 300.0
US_TICK = 60.0 / US_BPM / 4.0


def _line_words(ln: Dict) -> List[Dict]:
    # Sorted by their time: a hand-mangled record with words out of order
    # would otherwise write beats that run backwards, which the singing
    # games refuse whole.
    return sorted((w for w in (ln.get("words") or [])
                   if (w.get("w") or "").strip()),
                  key=lambda w: float(w.get("t") or 0))


def _sung_lines(data: Dict) -> List[Dict]:
    return [ln for ln in (data.get("lines") or []) if _line_words(ln)]


def ultrastar_text(data: Dict, audio_name: str) -> str:
    """The song as an UltraStar .txt.

    A word whose pitch was measured from the singer's own track leaves as a
    real note (`:`) at that pitch, and the singing games can score it. A word
    with nothing measurable in it — a consonant, a whisper, a word the
    separation lost — stays freestyle (`F`): shown and timed, not scored,
    because a note nobody measured is a note nobody should be marked against.

    Pitch zero in this format is middle C, so a note is written as its MIDI
    number less sixty. A song with two voices becomes a duet file, the second
    voice standing in the P2 part.
    """
    lines = _sung_lines(data)
    if not lines:
        raise ValueError(tr("There are no timed lines to export.",
                            "Нет размеченных строк для выгрузки."))
    first = min(w["t"] for ln in lines for w in _line_words(ln))
    gap_ms = int(round(first * 1000))

    def beat(t: float) -> int:
        return max(0, int(round((t - first) / US_TICK)))

    duet = any(ln.get("voice") == 2 for ln in lines)
    out = [
        f"#TITLE:{(data.get('title') or 'Karaoke').strip()}",
        f"#ARTIST:{(data.get('artist') or '').strip()}",
        f"#MP3:{audio_name}",
        f"#BPM:{US_BPM:g}",
        f"#GAP:{gap_ms}",
        "#ENCODING:UTF8",
    ]
    if duet:
        out += ["#P1:", "#P2:"]

    def part(voice_lines: List[Dict]) -> List[str]:
        rows: List[str] = []
        for k, ln in enumerate(voice_lines):
            words = _line_words(ln)
            if k:
                rows.append(f"- {beat(words[0]['t'])}")
            for j, w in enumerate(words):
                start = beat(w["t"])
                # a note is never shorter than one tick, and never runs into
                # the word after it
                length = max(1, int(round(max(w.get("d") or 0, US_TICK) / US_TICK)))
                if j + 1 < len(words):
                    length = max(1, min(length, beat(words[j + 1]["t"]) - start))
                nxt = words[j + 1] if j + 1 < len(words) else None
                # a syllable of the same word carries no space before it —
                # UltraStar reads them as one word, sung piece by piece
                text = w["w"] + ("" if nxt is None or nxt.get("g") else " ")
                note = w.get("n")
                if note is None:
                    rows.append(f"F {start} {length} 0 {text}")
                else:
                    rows.append(f": {start} {length} {int(note) - 60} {text}")
        return rows

    if duet:
        out.append("P1")
        out += part([ln for ln in lines if ln.get("voice") != 2])
        out.append("P2")
        out += part([ln for ln in lines if ln.get("voice") == 2])
    else:
        out += part(lines)
    out.append("E")
    return "\n".join(out) + "\n"


def _ass_colour(hex_colour: str, fallback: str) -> str:
    """“#4de1ff” → “&H00FFE14D” — .ass wants blue-green-red, alpha first."""
    c = str(hex_colour or fallback).strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        c = fallback.lstrip("#")
    r, g, b = c[0:2], c[2:4], c[4:6]
    return f"&H00{b}{g}{r}".upper()


def _ass_word(w: str) -> str:
    """Braces open override tags in .ass and a backslash starts an escape:
    a word carrying either would break every tag after it. Swapped for their
    harmless lookalikes — the singer reads the same thing."""
    return w.replace("{", "(").replace("}", ")").replace("\\", "/")


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    return f"{h}:{m:02d}:{t % 60:05.2f}"


def ass_text(data: Dict) -> str:
    """The song as .ass subtitles with karaoke timing.

    Each word carries a `\\k` tag; the sweep runs to the start of the next
    word, so the highlight moves the way it does on the page. The second
    voice gets a style of its own in the second colour, seated higher so the
    two do not land on the same spot when they sound together.
    """
    lines = _sung_lines(data)
    if not lines:
        raise ValueError(tr("There are no timed lines to export.",
                            "Нет размеченных строк для выгрузки."))
    colors = data.get("colors") or []
    c1 = _ass_colour(colors[0] if colors else "", "#4de1ff")
    c2 = _ass_colour(colors[1] if len(colors) > 1 else "", "#ff8ad1")
    dim = "&H00B0A89D"          # the not-yet-sung grey, readable on dark video

    head = [
        "[Script Info]",
        "; Made by the free karaoke editor — the timing is the song's own.",
        f"Title: {(data.get('title') or 'Karaoke').strip()}",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Voice1,Arial,72,{c1},{dim},&H00101018,&H80000000,"
        "-1,0,0,0,100,100,0,0,1,3,0,2,60,60,60,1",
        f"Style: Voice2,Arial,54,{c2},{dim},&H00101018,&H80000000,"
        "-1,0,0,0,100,100,0,0,1,3,0,8,60,60,60,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Text",
    ]

    rows = []
    for ln in lines:
        words = _line_words(ln)
        start = words[0]["t"]
        end = max(ln.get("end") or 0, words[-1]["t"] + (words[-1].get("d") or 0))
        parts = []
        for j, w in enumerate(words):
            until = words[j + 1]["t"] if j + 1 < len(words) else end
            cs = max(1, int(round((until - w["t"]) * 100)))
            nxt = words[j + 1] if j + 1 < len(words) else None
            parts.append("{\\k%d}%s" % (cs, _ass_word(w["w"])
                         + ("" if nxt is None or nxt.get("g") else " ")))
        style = "Voice2" if (ln.get("voice") == 2 or ln.get("backing")) else "Voice1"
        rows.append((start, f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},"
                            f"{style},,0,0,0,,{''.join(parts)}"))
    rows.sort(key=lambda r: r[0])
    return "\n".join(head + [r[1] for r in rows]) + "\n"
