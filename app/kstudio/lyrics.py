"""Parsing the lyrics: lines, words, syllables, sections, ready LRC timings."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

VOWELS_RU = set("аеёиоуыэюя")
VOWELS_EN = set("aeiouy")

# [00:12.34] line text  (classic LRC)
# “[1:05]”, “[1:05.25]” — where a line starts. A second time after a dash,
# “[1:05.25-1:09.5]”, says where it ends as well: then the line is placed
# exactly as written and nothing re-times it.
# Spaces inside the brackets are forgiven — “[00:45.72 ]” is what a person
# writing forty of these by hand ends up with, and a bracket that lands in the
# words instead of in the timing is a whole line silently unplaced.
LRC_RE = re.compile(r"^\s*\[\s*(\d{1,3}):(\d{1,2}(?:[.:]\d{1,3})?)"
                    r"(?:\s*[-\u2013\u2014]\s*(\d{1,3}):(\d{1,2}(?:[.:]\d{1,3})?))?"
                    r"\s*\]\s*(.*)$")
# [Chorus] on its own line is a section heading — square brackets are what
# people conventionally use for that.
SECTION_RE = re.compile(r"^\s*\[\s*([^\]]{1,40}?)\s*\]\s*$")
# (Chorus) is a heading too, but ONLY if the brackets really hold a section
# name. Round brackets in lyrics almost always mean backing vocals — “(oh-oh)”,
# “(don\'t go)” — and such lines must not be dropped from the singing.
ROUND_RE = re.compile(r"^\s*\(\s*([^)]{1,40}?)\s*\)\s*$")
SECTION_WORDS = (
    "куплет", "припев", "бридж", "проигрыш", "вступление", "концовка", "кода",
    "предприпев", "соло", "инструментал", "речитатив", "читка",
    "verse", "chorus", "bridge", "intro", "outro", "pre-chorus", "prechorus",
    "hook", "refrain", "solo", "interlude", "breakdown", "instrumental",
)


# A heading that carries a time range — “[Guitar solo 3:10-3:50]”, “[нет текста
# 1:02–1:40]”, or the bare “[3:10-3:50]” — says there are no words in that
# stretch of the song. Only a person knows this: a vocalise, a scream with
# nothing to write down and a sung line are all voice, and no measurement tells
# them apart.
NOTEXT_RE = re.compile(
    r"(\d{1,3}:\d{1,2}(?:[.,]\d{1,3})?|\d+(?:[.,]\d+)?)\s*[-–—]{1,2}\s*"
    r"(\d{1,3}:\d{1,2}(?:[.,]\d{1,3})?|\d+(?:[.,]\d+)?)")
# “2: line” — this line is sung by the second voice. “[voice 2]” switches
# every following line until told otherwise.
VOICE_LINE_RE = re.compile(r"^\s*([12])\s*[:>]\s+(.+)$")
VOICE_DIR_RE = re.compile(r"^\s*(?:voice|голос|вокал)\s*([12])\s*$", re.I)
# “Chorus x4” — the line is sung four times in a row. There is no need to
# write it out four times: the repeats are expanded here.
# “Some girls try too hard (Na-na-na)” — a lead line with the backing tacked on
# its tail. The tail is a line of its own, sung by someone else, usually at the
# same time: left inside, the lead singer would be shown na-na-na as their own
# words. Brackets in the MIDDLE of a line stay put — an aside is part of the
# line it interrupts.
TRAIL_RE = re.compile(r"^(.*\S)\s+(\([^()]{1,60}\))$")

REPEAT_RE = re.compile(r"^(.*?)\s*[\(\[]?\s*[x×хХ]\s*(\d{1,2})\s*[\)\]]?\s*$", re.I)


def _split_repeat(text: str):
    """“line x3” → (“line”, 3). Without a mark — (line, 1)."""
    m = REPEAT_RE.match(text)
    if not m:
        return text, 1
    body, times = m.group(1).strip(), int(m.group(2))
    if not body or times < 2 or times > 99:
        return text, 1
    if not _split_words(body):            # “x4” on its own is not a line
        return text, 1
    return body, times


def _is_section_name(text: str) -> bool:
    """“Chorus 2” is a heading, “don\'t go” is a line of the song."""
    first = re.sub(r"[^\w-]+", " ", text.lower()).split()
    return bool(first) and first[0] in SECTION_WORDS
# Metadata at the top of the file: "title: ...", "# artist: ..."
META_RE = re.compile(r"^\s*#?\s*(title|artist|название|исполнитель)\s*[:=]\s*(.+)$", re.I)

_PUNCT = "«»\"'“”„‘’()[]{}—–-…!?.,;:*~/\\|"
# the spaces matter: Whisper returns words with a leading space (" one"), and
# without stripping them no token would match and alignment would fall apart
_STRIP = _PUNCT + " \t\n\r   "


def normalize_token(word: str) -> str:
    """Key for matching a word against the recognised one: no punctuation,
    ё→е, lower case."""
    w = word.lower().replace("ё", "е").replace("’", "'")
    return w.strip(_STRIP).replace("'", "")


def count_syllables(word: str) -> int:
    """Rough estimate of a word\'s length in syllables (ru + en)."""
    w = normalize_token(word)
    if not w:
        return 0
    n = sum(1 for ch in w if ch in VOWELS_RU)
    if n:
        return n
    # Latin script: a run of vowels is one syllable, then the endings that lie.
    # Word length is what spreads the time inside a line, so “beautiful” and “I”
    # must not come out the same — with these three rules an English verse lands
    # close enough to how it is actually sung.
    n, prev_vowel = 0, False
    for ch in w:
        is_vowel = ch in VOWELS_EN
        if is_vowel and not prev_vowel:
            n += 1
        prev_vowel = is_vowel
    # A consonant before the final “le” makes it a syllable of its own:
    # “lit-tle”, “peo-ple”, “un-cle” — but not “smile” or “whole”.
    if len(w) > 2 and w.endswith("le") and w[-3] not in VOWELS_EN:
        pass                                     # that final e already counted
    elif w.endswith("e") and n > 1:
        n -= 1                                   # silent final e: “smile”, “gone”
    # “-ed” is silent unless a t or a d comes before it: “walked” is one,
    # “wanted” is two. After a vowel it is never silent: “agreed”.
    elif (len(w) > 3 and w.endswith("ed") and n > 1
          and w[-3] not in VOWELS_EN and w[-3] not in "td"):
        n -= 1
    # The same for a plural “-es” after most consonants: “makes”, not “mak-es”.
    elif (len(w) > 3 and w.endswith("es") and n > 1
          and w[-3] not in VOWELS_EN and w[-3] not in "sxz"
          and not w.endswith(("ches", "shes"))):
        n -= 1
    return max(n, 1)


@dataclass
class Word:
    text: str
    syllables: int = 0
    start: Optional[float] = None
    end: Optional[float] = None
    # how sure the model was of this word, when a model was involved at all
    prob: Optional[float] = None
    # a syllable of the word before it: timed on its own, read as one word
    glue: bool = False

    def __post_init__(self):
        if not self.syllables:
            self.syllables = count_syllables(self.text)

    def to_json(self):
        # "s" is what the player\'s editor uses to lay words out by syllable
        out = {"w": self.text, "t": round(self.start or 0.0, 3),
               "d": round(max((self.end or 0.0) - (self.start or 0.0), 0.0), 3),
               "s": self.syllables}
        if self.prob is not None:
            out["p"] = round(self.prob, 3)
        if self.glue:
            out["g"] = True
        return out


@dataclass
class Line:
    text: str
    words: List[Word] = field(default_factory=list)
    section: Optional[str] = None      # heading of the section starting here
    start: Optional[float] = None      # from LRC, if set by hand
    end: Optional[float] = None
    backing: bool = False              # whole line in brackets — backing vocals
    voice: int = 1                     # 1 or 2: the second voice gets its own colour
    keep: bool = False                 # keep the original voice on this stretch
    keep_soft: bool = False            # …but quietly, to be sung along with
    lock: bool = False                 # put right by hand: re-timing leaves it alone
    # Both ends written into the text — “[0:05-0:08.5]”. An end filled in from
    # the line below is a guess and may be improved upon; one written by hand
    # is an instruction, and the two must not be confused.
    held: bool = False
    # split off the tail of the line above: a duet with it, not a line after it.
    # Not saved with the song — re-parsing the text derives it again.
    tail: bool = False

    @property
    def syllables(self) -> int:
        return sum(w.syllables for w in self.words) or 1

    @property
    def sure(self) -> Optional[float]:
        """How sure the model was of this line: its least certain word.

        The weakest word is what gives a line away — an average hides one
        unheard word among five clear ones, and it is that one word that drags
        the timing off.
        """
        got = [w.prob for w in self.words if w.prob is not None]
        return min(got) if got else None

    def to_json(self):
        out = {
            "text": self.text,
            "backing": self.backing,
            "voice": self.voice,
            "keep": self.keep,
            "keepSoft": self.keep_soft,
            "lock": self.lock,
            "start": round(self.start or 0.0, 3),
            "end": round(self.end or 0.0, 3),
            "section": self.section,
            "words": [w.to_json() for w in self.words],
        }
        if self.sure is not None:
            out["sure"] = round(self.sure, 3)
        return out


@dataclass
class Lyrics:
    lines: List[Line] = field(default_factory=list)
    title: Optional[str] = None
    artist: Optional[str] = None
    has_manual_times: bool = False
    # stretches the person marked as holding no words: [Solo 3:10-3:50]
    skips: List[tuple] = field(default_factory=list)

    @property
    def words(self) -> List[Word]:
        return [w for ln in self.lines for w in ln.words]

    def plain_text(self) -> str:
        return "\n".join(ln.text for ln in self.lines)


# A syllable break written into the lyrics: “ко=ло=ко=ла”. The mark splits a
# word into pieces that are timed one by one — a held note lights up syllable
# by syllable — and it is never shown: on screen the word is whole again. The
# soft hyphen is understood too, for text pasted from elsewhere.
SYL_MARK = "=\u00ad"


def _split_words(text: str) -> List[Word]:
    """Split a line into words without losing anything.

    A mark on its own — a dash, an ellipsis — is not a word: it cannot be sung
    and does not deserve its own highlight. It must not be dropped either: on
    screen the line has to look the way it was written. So such a mark sticks
    to the neighbouring word.
    """
    out: List[Word] = []
    pending = ""
    for tok in text.split():
        if normalize_token(tok):
            # a word broken into syllables is several timed pieces that read
            # as one word: the first stands on its own, the rest are glued
            parts = [q for q in re.split("[" + SYL_MARK + "]", tok) if q]
            first = (pending + " " + parts[0]).strip() if pending else parts[0]
            out.append(Word(first))
            for extra in parts[1:]:
                w = Word(extra)
                w.glue = True
                out.append(w)
            pending = ""
        elif out:
            out[-1] = Word(out[-1].text + " " + tok)     # a mark after a word
        else:
            pending = tok                                # a mark at the line start
    if pending and not out:
        out.append(Word(pending))
    return out


def _lrc_seconds(mm: str, ss: str) -> float:
    return int(mm) * 60 + float(ss.replace(":", "."))


def _parse_lrc_time(m: re.Match) -> float:
    return _lrc_seconds(m.group(1), m.group(2))


def parse(raw: str) -> Lyrics:
    """Text → Lyrics. Understands LRC timings, bracketed sections and meta headers."""
    lyr = Lyrics()
    pending_section: Optional[str] = None
    saw_content = False
    cur_voice = 1                  # which voice sings until told otherwise

    for raw_line in raw.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()

        if not line:
            continue

        if not saw_content:
            m = META_RE.match(line)
            if m:
                key = m.group(1).lower()
                if key in ("title", "название"):
                    lyr.title = m.group(2).strip()
                else:
                    lyr.artist = m.group(2).strip()
                continue

        m = LRC_RE.match(line)
        start = None
        finish = None
        if m:
            start = _parse_lrc_time(m)
            if m.group(3):
                # A line given both its ends is placed exactly as written; the
                # aligner is only told what stands between such lines.
                finish = _lrc_seconds(m.group(3), m.group(4))
                if finish <= start:
                    finish = None
            line = m.group(5).strip()
            if not line:
                continue

        backing = False
        voice = None
        if start is None:
            m = SECTION_RE.match(line)
            if m and _split_words(m.group(1)):
                d = VOICE_DIR_RE.match(m.group(1))
                if d:                       # [voice 2] switches, it is not a heading
                    cur_voice = int(d.group(1))
                    continue
                span = NOTEXT_RE.search(m.group(1))
                if span:
                    # “[Solo 3:10-3:50]”: a heading and a fact about the song —
                    # keep the heading for the line that follows, and remember
                    # that nothing is sung in between.
                    lyr.skips.append((_clock(span.group(1)), _clock(span.group(2))))
                    rest = NOTEXT_RE.sub("", m.group(1)).strip(" -–—:,")
                    if _is_notext_word(rest):
                        rest = ""       # “[нет текста 1:02-1:40]” is not a heading
                    pending_section = rest or pending_section
                    continue
                # a line like [Chorus] is a heading for the lines that follow
                pending_section = m.group(1).strip()
                continue
            m = ROUND_RE.match(line)
            if m and _split_words(m.group(1)):
                if _is_section_name(m.group(1)):
                    pending_section = m.group(1).strip()
                    continue
                # anything else in round brackets is backing vocals, and it is sung
                backing = True
            m = VOICE_LINE_RE.match(line)
            if m and _split_words(m.group(2)):
                voice = int(m.group(1))     # “2: line” — this line only
                line = m.group(2).strip()

        # “line x4” — a repeat. With manual LRC timings repeats are left alone:
        # every line there has a time of its own.
        times = 1
        if start is None:
            line, times = _split_repeat(line)

        # A backing tail on a lead line becomes a line of its own, second
        # voice: “try too hard (Na-na-na)” is two people singing.
        trail = None
        if start is None and not backing:
            m = TRAIL_RE.match(line)
            if m and _split_words(m.group(2)) and not _is_section_name(
                    m.group(2).strip("() ")):
                line, trail = m.group(1).strip(), m.group(2)

        words = _split_words(line)
        if not words:
            continue
        # the marks split the timing, never the reading: what is shown is the
        # line without them
        shown = re.sub("[" + SYL_MARK + "]", "", line)
        trail_shown = re.sub("[" + SYL_MARK + "]", "", trail) if trail else trail

        saw_content = True
        if start is not None:
            lyr.has_manual_times = True
        # Backing vocals default to the second voice: usually someone else sings
        # them, and a colour of their own helps on screen.
        for k in range(times):
            lyr.lines.append(Line(text=shown, words=_split_words(line),
                                  section=pending_section if k == 0 else None,
                                  start=start, end=finish,
                                  held=finish is not None, backing=backing,
                                  voice=voice or (2 if backing else cur_voice)))
            if trail:
                lyr.lines.append(Line(text=trail_shown, words=_split_words(trail),
                                      section=None, start=None, backing=True,
                                      voice=2, tail=True))
        pending_section = None

    # With manual timings a line ends where the next one begins — unless it was
    # given an end of its own, which is not a guess to be improved upon.
    if lyr.has_manual_times:
        for i, ln in enumerate(lyr.lines):
            if ln.start is None or ln.end is not None:
                continue
            nxt = next((l for l in lyr.lines[i + 1:] if l.start is not None), None)
            ln.end = nxt.start if nxt else None

    return lyr


# What people write when they mean “nothing is sung here”, rather than naming
# a part of the song. Such a marker is not a heading for the lines after it.
NOTEXT_WORDS = ("нет текста", "без текста", "no text", "no lyrics", "нет слов",
                "instrumental", "инструментал", "проигрыш", "без слов")


def _is_notext_word(text: str) -> bool:
    low = re.sub(r"\s+", " ", (text or "").strip().lower())
    return any(low == w or low.startswith(w) for w in NOTEXT_WORDS)


def _clock(text: str) -> float:
    """“3:50”, “230”, “3:50.5” → seconds."""
    out = 0.0
    for part in str(text).replace(",", ".").split(":"):
        try:
            out = out * 60 + float(part)
        except ValueError:
            return out
    return out


def decode_text(raw: bytes) -> str:
    """Work out the encoding of the lyrics file.

    Notepad on a Russian Windows still saves in ANSI (cp1251) and in UTF-16, so
    UTF-8 alone is not enough — otherwise the program dies with a baffling
    error for no visible reason.
    """
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for enc in ("utf-8", "cp1251", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load(path: str) -> Lyrics:
    with open(path, "rb") as f:
        return parse(decode_text(f.read()))
