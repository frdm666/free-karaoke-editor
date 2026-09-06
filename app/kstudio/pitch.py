"""How high the voice goes, measured from the singer's own track.

The words already know *when* they are sung. This says at what pitch — which
is what turns a text under music into karaoke a game can score, and what lets
a singer see where to take their voice instead of guessing.

It wants two things. The separated vocal: over a whole mix the guitars answer
the question instead of the singer, and the answer is worse than none. And
numpy: a song's worth of autocorrelation in plain Python is minutes, not
seconds. Without either, a song simply has no notes, and everything that
worked before goes on working exactly as it did.

Nothing here is a neural net. A voiced sound repeats itself, and the length of
that repetition is the pitch; the whole method is finding that length and not
being fooled by half of it.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from . import audio as AU
from .i18n import tr

SR = 16000                 # enough for any sung note, cheap to read
FRAME = 1024               # 64 ms — two periods of the lowest voice we look for
HOP = 320                  # 20 ms between measurements
F_LOW, F_HIGH = 70.0, 1000.0     # a bass's low note to a soprano's high one
LAG_MIN = int(SR / F_HIGH)
LAG_MAX = int(SR / F_LOW)
CLEAR = 0.34               # how well a frame must repeat itself to be a note
QUIET = 0.012              # below this the frame is breath or silence


def available() -> bool:
    try:
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


def why_not() -> str:
    return tr("numpy is not installed — notes are not measured "
              "(install it: pip install numpy)",
              "numpy не установлен — высота тона не измеряется "
              "(поставить: pip install numpy)")


def contour(path: str) -> List[Optional[float]]:
    """The pitch of every 20 ms of `path`, in MIDI numbers, None where silent.

    A frame is compared with itself, shifted. The shift that matches best is
    the length of one period of the voice — and half that length matches
    nearly as well, which is how a measurement lands an octave high. So the
    shortest shift that is nearly as good as the best one wins, which is the
    ordinary cure for the ordinary mistake.
    """
    import numpy as np

    raw = AU.read_pcm_mono(path, SR, af=AU.LEVEL_VOICE)
    if len(raw) < FRAME * 2:
        return []
    x = np.frombuffer(memoryview(raw).cast("B"), dtype=np.int16).astype(np.float32)
    x /= 32768.0
    win = np.hanning(FRAME).astype(np.float32)
    n_fft = 2048

    out: List[Optional[float]] = []
    for start in range(0, len(x) - FRAME, HOP):
        frame = x[start:start + FRAME]
        rms = float(np.sqrt(np.mean(frame * frame)))
        if rms < QUIET:
            out.append(None)
            continue
        f = frame * win
        spec = np.fft.rfft(f, n=n_fft)
        ac = np.fft.irfft(spec * np.conj(spec))[:LAG_MAX + 2]
        if ac[0] <= 0:
            out.append(None)
            continue
        ac = ac / ac[0]
        window = ac[LAG_MIN:LAG_MAX + 1]
        if not len(window):
            out.append(None)
            continue
        best = float(window.max())
        if best < CLEAR:
            out.append(None)
            continue
        # the earliest lag that is nearly as good as the best: the real period,
        # not the double of it that scores a hair higher
        good = np.nonzero(window >= best * 0.90)[0]
        lag = int(good[0]) + LAG_MIN
        # a parabola through the three points around the peak, so the answer is
        # not quantised to whole samples
        if 0 < lag - LAG_MIN < len(window) - 1:
            a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
            denom = (a - 2 * b + c)
            if denom != 0:
                lag += float(0.5 * (a - c) / denom)
        freq = SR / max(lag, 1e-6)
        if not (F_LOW <= freq <= F_HIGH):
            out.append(None)
            continue
        out.append(69.0 + 12.0 * float(np.log2(freq / 440.0)))
    return _steady(out)


def _steady(seq: List[Optional[float]]) -> List[Optional[float]]:
    """Take the jitter out: a note is held, a stray reading is not.

    Three frames is sixty milliseconds — shorter than any sung note and longer
    than any single mistake, so the middle of three is the value to trust.
    """
    if len(seq) < 3:
        return seq
    out = list(seq)
    for i in range(1, len(seq) - 1):
        three = [v for v in (seq[i - 1], seq[i], seq[i + 1]) if v is not None]
        if len(three) == 3:
            out[i] = sorted(three)[1]
        elif seq[i] is not None and len(three) == 1:
            out[i] = None            # a lone reading between two silences
    return out


def note_of(seq: List[Optional[float]], t0: float, t1: float) -> Optional[int]:
    """The note a word is sung on: the middle of what was measured inside it."""
    if t1 <= t0 or not seq:
        return None
    a = max(0, int(t0 / (HOP / SR)))
    b = min(len(seq), int(t1 / (HOP / SR)) + 1)
    heard = [v for v in seq[a:b] if v is not None]
    if len(heard) < 2:
        return None
    heard.sort()
    return int(round(heard[len(heard) // 2]))


def put_notes(lines: List[Dict], vocals_path: str,
              log=lambda _m: None) -> Tuple[int, int]:
    """Measure every word of every line. Returns (words given a note, all words).

    A word with nothing measurable in it keeps no note at all, rather than
    being given a plausible one: a wrong note on the screen is worse than no
    note, because a singer will believe it.
    """
    if not available():
        log("  " + why_not())
        return 0, 0
    try:
        seq = contour(vocals_path)
    except Exception as e:                      # a stem that will not decode
        log(tr(f"  the notes could not be measured ({e}) — going on without them",
               f"  высоту тона измерить не вышло ({e}) — продолжаю без неё"))
        return 0, 0
    if not seq:
        return 0, 0
    done = total = 0
    for ln in lines:
        for w in ln.get("words") or []:
            total += 1
            t = float(w.get("t") or 0.0)
            d = float(w.get("d") or 0.0)
            n = note_of(seq, t, t + d)
            if n is None:
                w.pop("n", None)
            else:
                w["n"] = n
                done += 1
    log(tr(f"  notes measured for {done} of {total} words",
           f"  высота измерена у {done} слов из {total}"))
    return done, total
