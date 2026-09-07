"""The report before building: what the song is, what the text is, what to expect.

Building takes minutes, and half the mistakes can be seen beforehand: the
lyrics are not from this song, there are half as many lines as there are
verses, the language came out wrong, the memory will not hold the chosen model.
Saying it before is cheaper than saying it after.
"""

from __future__ import annotations

import math
import os

from .progress import mmss as _mmss
from .i18n import tr
from typing import Dict, List, Optional, Tuple

# Sensible tempo bounds for a song. Below that nobody dances; above it the
# number is usually doubled (the beat counted twice).
BPM_MIN, BPM_MAX = 60.0, 190.0


def _onset_strength(env: List[float]) -> List[float]:
    """How sharply the loudness rises — that is what a beat sounds like."""
    return [max(0.0, env[i] - env[i - 1]) for i in range(1, len(env))]


def bpm(env: List[float], dt: float) -> Tuple[Optional[float], float]:
    """Tempo from the loudness envelope. → (beats per minute, confidence 0..1).

    We take the autocorrelation of the loudness rises and look for the beat
    period with a comb: a real beat answers both at its own period and at every
    multiple, while a bar answers only at half of them. Without that the
    autocorrelation confidently reports a tempo twice as slow, which is exactly
    what happened at 140 beats.
    """
    if not env or dt <= 0 or len(env) < 200:
        return None, 0.0

    o = _onset_strength(env)
    n = len(o)
    mean = sum(o) / n
    o = [x - mean for x in o]                    # drop the constant component

    lo = max(1, int(60.0 / (BPM_MAX * dt)))      # lag of the fastest beat
    hi = int(60.0 / (BPM_MIN * dt))
    if hi <= lo or hi >= n:
        return None, 0.0

    # Go up to four periods: the comb needs multiples of the lag.
    top = min(4 * hi, n - 2)
    corr = [0.0] * (top + 1)
    for lag in range(lo, top + 1):
        s = 0.0
        for i in range(n - lag):
            s += o[i] * o[i + lag]
        corr[lag] = s / (n - lag)

    def at(x: float) -> float:
        """Correlation at a fractional lag — a beat rarely lands on a whole bin."""
        if x < lo or x >= top:
            return 0.0
        k = int(x)
        return corr[k] + (corr[k + 1] - corr[k]) * (x - k)

    # Tempos around 120 are far more common in songs than 60 or 190.
    def prior(t: float) -> float:
        return math.exp(-0.5 * (math.log(t / 120.0, 2) / 0.9) ** 2)

    WEIGHTS = ((1, 1.0), (2, 0.6), (3, 0.4), (4, 0.3))
    best_t, best_s, scores = None, -1e18, []
    t = BPM_MIN
    while t <= BPM_MAX:
        lag = 60.0 / (t * dt)
        comb = sum(w * at(lag * m) for m, w in WEIGHTS)
        # If half the assumed period also has a bump, the beat is twice as fast
        # and we are looking at the bar. A real beat has silence between hits.
        s = (comb - 0.6 * at(lag / 2)) * prior(t)
        scores.append(s)
        if s > best_s:
            best_s, best_t = s, t
        t += 0.25
    if best_t is None or best_s <= 0:
        return None, 0.0

    avg = sum(scores) / len(scores)
    spread = math.sqrt(sum((v - avg) ** 2 for v in scores) / len(scores)) or 1e-9
    conf = max(0.0, min(1.0, (best_s - avg) / (4 * spread)))
    return round(best_t, 1), round(conf, 2)


def runs_below(env: List[float], dt: float, thr: float,
               least: float) -> List[Dict]:
    """Stretches where the sound stays under `thr` for at least `least`.

    Two passes wanted this and each carried its own copy: one asking whether a
    voice is there at all, the other where the song goes quiet. They differ in
    where the line is drawn and in nothing else, so the line is the argument
    and the walk is written once.
    """
    out, run = [], None
    for i, v in enumerate(env):
        if v <= thr:
            if run is None:
                run = i
        else:
            if run is not None and (i - run) * dt >= least:
                out.append({"start": round(run * dt, 1), "end": round(i * dt, 1)})
            run = None
    if run is not None and (len(env) - run) * dt >= least:
        out.append({"start": round(run * dt, 1), "end": round(len(env) * dt, 1)})
    return out


def quiet_stretches(env: List[float], dt: float, least: float = 5.0) -> List[Dict]:
    """Long stretches without singing: intro, interlude, solo, tail.

    For karaoke this matters more than the tempo: the text is silent there,
    and no lines should be dragged into it. We measure by loudness — before the
    tracks are separated we hear the whole mix, so “quiet” means “noticeably
    quieter than the song on average”, not absolute silence.
    """
    if not env or dt <= 0:
        return []
    ordered = sorted(env)
    floor = ordered[int(len(ordered) * 0.35)]
    thr = max(floor * 1.15, ordered[int(len(ordered) * 0.12)])

    return runs_below(env, dt, thr, least)


def loudness(env: List[float]) -> Dict:
    """How loud the recording is and whether the peaks are clipped."""
    if not env:
        return {}
    peak = max(env)
    avg = sum(env) / len(env)
    loud = sum(1 for v in env if v > 0.97) / len(env)
    quiet = sum(1 for v in env if v < 0.02) / len(env)
    return {"peak": round(peak, 3), "avg": round(avg, 3),
            "clipping": round(loud, 4), "silence": round(quiet, 3)}


def text_stats(lyrics) -> Dict:
    lines = [ln for ln in lyrics.lines if ln.words]
    words = [w for ln in lines for w in ln.words]
    seen: Dict[str, int] = {}
    for ln in lines:
        key = ln.text.strip().lower()
        seen[key] = seen.get(key, 0) + 1
    repeats = sum(n - 1 for n in seen.values() if n > 1)
    syl = sum(getattr(ln, "syllables", 0) for ln in lines)
    return {"lines": len(lines), "words": len(words), "syllables": syl,
            "repeats": repeats,
            "sections": sorted({ln.section for ln in lyrics.lines if ln.section}),
            "longest": max((len(ln.words) for ln in lines), default=0)}


# How many times the song's own length a step takes. Measured on an ordinary
# laptop without a graphics card; another machine gives other numbers, which is
# why the report says “about”.
COST = {"separate": 2.2,
        "tiny": 0.6, "base": 0.9, "small": 1.6, "medium": 4.0, "large-v3": 8.0}


def estimate(duration: float, model: str, separate: bool, whisper: bool) -> Dict:
    """Roughly how long to wait. The numbers are crude and say so."""
    secs = 8.0                                  # preparing the audio and writing the file
    if separate:
        secs += duration * COST["separate"]
    if whisper:
        secs += duration * COST.get(model, 1.6)
    return {"seconds": int(secs), "rough": True}


def human_time(sec: float) -> str:
    sec = int(sec)
    if sec < 90:
        return tr(f"about {max(sec, 5)} s", f"около {max(sec, 5)} с")
    m = sec // 60
    if m < 60:
        return tr(f"about {m} min", f"около {m} мин")
    return tr(f"about {m // 60} h {m % 60} min", f"около {m // 60} ч {m % 60} мин")


def build(audio_path: str, lyrics, duration: float, envelope: List[float],
          hop: float, *, model: str = "small", separate: bool = True,
          whisper: bool = True, language: str = "auto") -> Dict:
    """Put the whole report together. Nothing heavy is computed here."""
    from . import lang as LG
    from . import sysinfo

    tempo, conf = bpm(envelope, hop)
    quiet = quiet_stretches(envelope, hop)
    stats = text_stats(lyrics)
    plain = lyrics.plain_text()
    code = LG.resolve(language, plain)
    auto = language in ("", "auto", None)
    # A language chosen by hand outranks the text — but if the two are not even
    # written in the same alphabet, the choice is a slip, and Whisper would time
    # the song against the wrong language without a word of complaint.
    wrong_script = (not auto and LG.text_script(plain)
                    and LG.text_script(plain) != LG.script_of(code))

    # Text and song should be about the same length: too few lines for a long
    # song usually means the wrong text, or repeats left unwritten.
    per_line = duration / stats["lines"] if stats["lines"] else 0
    notes: List[str] = []
    if stats["lines"] == 0:
        notes.append(tr("The text has no lines at all — nothing can be built.",
                        "В тексте нет ни одной строки — сборка не получится."))
    elif per_line > 12:
        notes.append(tr(
            f"There are {per_line:.0f} s of song per line — that is a lot. "
            f"Usually it means the repeats are not written out in the text.",
            f"На строку приходится {per_line:.0f} с песни — это много. "
            f"Обычно так бывает, когда в тексте не выписаны повторы."))
    elif per_line < 1.2:
        notes.append(tr(
            f"Only {per_line:.1f} s of song per line — there are more lines than "
            f"can be sung. Check that this is the right text.",
            f"На строку приходится всего {per_line:.1f} с — строк "
            f"больше, чем успевает прозвучать. Проверьте, тот ли текст."))
    if stats["repeats"] == 0 and stats["lines"] > 12:
        notes.append(tr(
            "Not a single repeated line. If the song has a chorus, write it out "
            "as many times as it is sung.",
            "Ни одной повторяющейся строки. Если в песне есть припев, "
            "выпишите его столько раз, сколько поют."))
    if quiet:
        longest = max(quiet, key=lambda q: q["end"] - q["start"])
        notes.append(tr(
            f"Places without singing: {len(quiet)}, "
            f"{sum(q['end'] - q['start'] for q in quiet):.0f} s in total. The longest "
            f"is {_mmss(longest['start'])}–{_mmss(longest['end'])}. "
            "No lines should land there.",
            f"Мест без пения: {len(quiet)}, всего "
            f"{sum(q['end'] - q['start'] for q in quiet):.0f} с. Самое длинное — "
            f"{_mmss(longest['start'])}–{_mmss(longest['end'])}. "
            f"Строки туда попадать не должны."))
    loud = loudness(envelope)
    if loud.get("clipping", 0) > 0.02:
        notes.append(tr(
            "The recording clips in places — timing by loudness works worse on it. "
            "An instrumental helps.",
            "Запись местами перегружена — разметка по громкости на ней "
            "работает хуже. Минусовка помогает."))
    if loud.get("silence", 0) > 0.5:
        notes.append(tr("More than half the recording is silence. Perhaps the wrong "
                        "file was picked.",
                        "Больше половины записи — тишина. Возможно, взят не тот файл."))

    if wrong_script:
        looks = LG.detect(plain)
        notes.append(tr(
            f"The lyrics are not written in the alphabet of the chosen language "
            f"({LG.label(code)}). They look like {LG.label(looks)}. Whisper times "
            f"a song against the language it is given, so take “detect from the "
            f"text” or pick {LG.label(looks)} by hand.",
            f"Текст написан не тем алфавитом, что выбранный язык "
            f"({LG.label(code)}). Похоже на «{LG.label(looks)}». Whisper "
            f"размечает песню под тот язык, что ему дали, поэтому возьмите "
            f"«определить по тексту» или выберите «{LG.label(looks)}» руками."))

    need = sysinfo.NEED_DEMUCS if separate else sysinfo.NEED_WHISPER.get(model, 2.2)
    free = sysinfo.available_gb()
    if free is not None and free < need:
        notes.append(tr(
            f"{free:.1f} GB of memory is free, and about {need:.0f} GB is needed — "
            f"this will be very slow.",
            f"Свободно {free:.1f} ГБ памяти, а нужно около {need:.0f} ГБ — "
            f"считать будет очень долго."))

    return {
        "audio": {"name": os.path.basename(audio_path),
                  "duration": round(duration, 1),
                  "bpm": tempo, "bpmConfidence": conf,
                  "quiet": quiet,
                  "quietTotal": round(sum(q["end"] - q["start"] for q in quiet), 1),
                  **loud},
        "text": stats,
        "language": {"code": code, "name": LG.label(code),
                     "auto": language in ("", "auto", None)},
        "plan": {"separate": separate, "whisper": whisper, "model": model,
                 **estimate(duration, model, separate, whisper)},
        "notes": notes,
    }


def as_text(rep: Dict) -> str:
    """The report as a few lines — for printing to the console."""
    a, t, plan = rep["audio"], rep["text"], rep["plan"]
    out = [tr("Before we start", "Отчёт перед сборкой"), "─" * 46]
    dur = a["duration"]
    out.append(tr(f"  Song       {a['name']}", f"  Песня      {a['name']}"))
    out.append(tr(f"  Length     {int(dur // 60)}:{int(dur % 60):02d}",
                  f"  Длина      {int(dur // 60)}:{int(dur % 60):02d}"))
    q = a.get("quiet") or []
    if q:
        show = ", ".join(f"{_mmss(x['start'])}–{_mmss(x['end'])}" for x in q[:4])
        if len(q) > 4:
            show += tr(f" and {len(q) - 4} more", f" и ещё {len(q) - 4}")
        out.append(tr(f"  No vocal   {show}", f"  Без пения  {show}"))
    else:
        out.append(tr("  No vocal   no long instrumental stretches",
                      "  Без пения  длинных проигрышей не слышно"))
    out.append(tr(f"  Text       {t['lines']} lines, {t['words']} words, "
                  f"repeats: {t['repeats']}",
                  f"  Текст      {t['lines']} строк, {t['words']} слов, "
                  f"повторов: {t['repeats']}"))
    if t["sections"]:
        out.append(tr(f"  Sections   {', '.join(t['sections'])}",
                      f"  Разделы    {', '.join(t['sections'])}"))
    lang = rep["language"]
    out.append(tr(f"  Language   {lang['name']}", f"  Язык       {lang['name']}")
               + (tr(" (worked out from the text)", " (определён по тексту)")
                  if lang["auto"] else tr(" (set by hand)", " (задан вручную)")))
    steps = []
    if plan["separate"]:
        steps.append(tr("instrumental", "минусовка"))
    steps.append(tr("Whisper timing (" + plan["model"] + ")",
                    "разметка Whisper (" + plan["model"] + ")") if plan["whisper"]
                 else tr("timing by loudness", "разметка по энергии"))
    out.append(tr(f"  Plan       {', '.join(steps)}", f"  Сделаю     {', '.join(steps)}"))
    out.append(tr(f"  Takes      {human_time(plan['seconds'])} (very roughly)",
                  f"  Займёт     {human_time(plan['seconds'])} (очень грубо)"))
    for n in rep["notes"]:
        out.append("")
        for i, chunk in enumerate(_wrap(n, 60)):
            out.append(("  ! " if i == 0 else "    ") + chunk)
    return "\n".join(out)


def _wrap(text: str, width: int) -> List[str]:
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out
