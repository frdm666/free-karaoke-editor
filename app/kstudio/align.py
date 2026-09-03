"""Lining the text up with the audio — a timing for every word.

Two engines:
  whisper — forced alignment with the Whisper model (stable-ts). Accurate, but
            it needs torch.
  energy  — no neural nets: words are spread over the “mass” of vocal energy.
            Always available, respects pauses and interludes, coarser per word.
"""

from __future__ import annotations

import difflib
import re
import sys
import warnings
from typing import Callable, Dict, List, Optional

from .i18n import tr
from .lyrics import Lyrics, Word, normalize_token
from .progress import mmss

Log = Callable[[str], None]


def _noop(msg: str) -> None:
    pass


# --------------------------------------------------------------------------- #
#  The loudness engine: find sung phrases and lay the lines out over them
# --------------------------------------------------------------------------- #

def _phrases(env: List[float], dt: float, min_dur: float = 0.18,
             max_gap: float = 0.32) -> List[List[float]]:
    """Stretches of vocal activity [start, end] found by a hysteresis threshold."""
    if not env:
        return []
    ordered = sorted(env)
    floor = ordered[int(len(ordered) * 0.15)]
    peak = ordered[min(int(len(ordered) * 0.98), len(ordered) - 1)]
    rng = max(peak - floor, 1e-6)
    on, off = floor + 0.20 * rng, floor + 0.11 * rng

    lead = max(int(0.20 / dt), 1)        # how far to step back to the quiet phrase start
    segs, start, active = [], 0, False
    for i, e in enumerate(env):
        if not active and e >= on:
            active, start = True, i
            # the threshold trips once the sound is already rising; step back to
            # the real start so the line lights up slightly early, not late
            while start > 0 and i - start < lead and env[start - 1] > off * 0.7:
                start -= 1
        elif active and e < off:
            active = False
            segs.append([start * dt, i * dt])
    if active:
        segs.append([start * dt, len(env) * dt])

    merged: List[List[float]] = []
    for s, e in segs:
        if merged and s - merged[-1][1] <= max_gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [seg for seg in merged if seg[1] - seg[0] >= min_dur]


GAP_PENALTY = 1.5      # how much costlier a gap inside a line is than a length error


def _limit_phrases(segs: List[List[float]], target: int) -> List[List[float]]:
    """Glue an over-fragmented split at its narrowest gaps (or DP gets slow)."""
    while len(segs) > target:
        gaps = [(segs[i + 1][0] - segs[i][1], i) for i in range(len(segs) - 1)]
        _, i = min(gaps)
        segs[i][1] = segs[i + 1][1]
        del segs[i + 1]
    return segs


def _fit_lines_to_phrases(lines, segs) -> None:
    """Lay the lines over the phrases optimally (DP) and set start/end."""
    N, M = len(lines), len(segs)
    voiced = [e - s for s, e in segs]
    pre = [0.0]
    for v in voiced:
        pre.append(pre[-1] + v)
    total_voiced = pre[-1] or 1.0
    total_syl = sum(ln.syllables for ln in lines) or 1
    want = [total_voiced * ln.syllables / total_syl for ln in lines]

    INF = float("inf")

    # without a cap on the group size DP grows as O(N·M²) and takes tens of
    # seconds on a long text; a line almost never spans many phrases in a row
    span_cap = max(8, 2 * -(-M // N), 2 * -(-N // M))

    if M >= N:
        # every line gets a contiguous group of one or more phrases
        dp = [[INF] * (M + 1) for _ in range(N + 1)]
        back = [[0] * (M + 1) for _ in range(N + 1)]
        dp[0][0] = 0.0
        for i in range(1, N + 1):
            for j in range(i, M - (N - i) + 1):
                best, bk = INF, i - 1
                for k in range(max(i - 1, j - span_cap), j):
                    prev = dp[i - 1][k]
                    if prev >= INF:
                        continue
                    gv = pre[j] - pre[k]
                    inner = (segs[j - 1][1] - segs[k][0]) - gv   # gaps inside the group
                    c = prev + (gv - want[i - 1]) ** 2 + GAP_PENALTY * inner ** 2
                    if c < best:
                        best, bk = c, k
                dp[i][j], back[i][j] = best, bk
        j = M
        for i in range(N, 0, -1):
            k = back[i][j]
            lines[i - 1].start, lines[i - 1].end = segs[k][0], segs[j - 1][1]
            j = k
    else:
        # fewer phrases than lines: several lines share one phrase
        dp = [[INF] * (N + 1) for _ in range(M + 1)]
        back = [[0] * (N + 1) for _ in range(M + 1)]
        dp[0][0] = 0.0
        for j in range(1, M + 1):
            for i in range(j, N - (M - j) + 1):
                best, bk = INF, j - 1
                for k in range(max(j - 1, i - span_cap), i):
                    prev = dp[j - 1][k]
                    if prev >= INF:
                        continue
                    c = prev + (voiced[j - 1] - sum(want[k:i])) ** 2
                    if c < best:
                        best, bk = c, k
                dp[j][i], back[j][i] = best, bk
        i = N
        for j in range(M, 0, -1):
            k = back[j][i]
            s, e = segs[j - 1]
            grp = lines[k:i]
            tot = sum(ln.syllables for ln in grp) or 1
            acc = 0.0
            for ln in grp:
                ln.start = s + (e - s) * acc / tot
                acc += ln.syllables
                ln.end = s + (e - s) * acc / tot
            i = k


def spans(value, duration: float = 0.0) -> List[tuple]:
    """Stretches with no words in them, as a person writes them.

    “0:00-0:42, 3:10-3:50”, a list of pairs, seconds or mm:ss — all the same
    thing. Overlapping ones are merged; nonsense is dropped rather than guessed
    at, because a wrong stretch here silently hides a piece of the song.
    """
    raw = []
    if not value:
        return []
    if isinstance(value, str):
        for part in re.split(r"[;,\n]+", value):
            m = re.match(r"^\s*([\d:.,]+)\s*[-–—]{1,2}\s*([\d:.,]+)\s*$", part)
            if m:
                raw.append((clock(m.group(1)), clock(m.group(2))))
    else:
        for item in value:
            if isinstance(item, dict):
                raw.append((clock(item.get("start")), clock(item.get("end"))))
            elif len(item) == 2:
                raw.append((clock(item[0]), clock(item[1])))
    out = []
    for a, b in sorted(raw):
        if duration:
            a, b = max(0.0, min(a, duration)), max(0.0, min(b, duration))
        if b - a < 0.3:
            continue
        if out and a <= out[-1][1] + 0.05:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return [tuple(x) for x in out]


def keep_windows(skip: List[tuple], duration: float) -> List[tuple]:
    """The other side of the coin: where the words are allowed to be."""
    out, at = [], 0.0
    for a, b in skip:
        if a > at:
            out.append((at, a))
        at = max(at, b)
    if at < duration:
        out.append((at, duration))
    return [w for w in out if w[1] - w[0] > 0.2]


def clock(value, duration: float = 0.0) -> float:
    """A moment as a person writes it: 83, “1:23”, “1:23.5”, “0:01:23”.

    Anything that is not a time at all is no time: better to ignore a typo than
    to build the whole song around it.
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        out = float(value)
    else:
        text = str(value).strip().replace(",", ".")
        if not text:
            return 0.0
        try:
            parts = [float(p) for p in text.split(":")]
        except ValueError:
            return 0.0
        out = 0.0
        for p in parts:
            out = out * 60 + p
    if out < 0 or out != out:                 # negative, or a nan
        return 0.0
    return min(out, duration) if duration else out


def align_energy(lyrics: Lyrics, audio_path: str, duration: float,
                 log: Log = _noop, skip=None) -> Lyrics:
    """Lay lines over sung phrases; inside a line, words go by syllable."""
    from . import audio as A

    log(tr("Looking for sung phrases by loudness…", "Ищу вокальные фразы по громкости…"))
    try:
        env, dt = A.rms_envelope(audio_path)
    except Exception as e:                              # pragma: no cover
        log(tr(f"  did not work ({e}) — spreading evenly", f"  не вышло ({e}) — раскладываю равномерно"))
        env, dt = [], 0.02

    # the same rule as the neural path: phrases are for the lead lines, the
    # backing is placed against them afterwards
    lines = [ln for ln in lyrics.lines if ln.words and not ln.backing] \
        or [ln for ln in lyrics.lines if ln.words]
    segs = _phrases(env, dt)
    if not segs or not lines:
        log(tr("  no phrases stood out — spreading the text evenly",
            "  фразы не выделились — раскладываю текст равномерно"))
        segs = [[0.0, duration]]
    # Phrases inside a stretch the person called wordless are not phrases to
    # put text on: a vocalise is as loud as singing, which is the whole trouble.
    skip = spans(skip, duration)
    if skip:
        segs = [g for g in segs
                if not any(g[0] >= a - 0.2 and g[1] <= b + 0.2 for a, b in skip)]
        if not segs:
            segs = [[w[0], w[1]] for w in keep_windows(skip, duration)]
        log(tr(f"  wordless stretches taken out: {len(skip)}",
               f"  выброшено участков без текста: {len(skip)}"))
    segs = _limit_phrases(segs, max(3 * len(lines) + 8, 24))
    log(tr(f"  phrases found: {len(segs)}, lines of text: {len(lines)}",
           f"  найдено фраз: {len(segs)}, строк текста: {len(lines)}"))

    if lines:
        _fit_lines_to_phrases(lines, segs)

    # words inside a line are spread in proportion to syllables.
    # The span must not be widened: on dense text lines are shorter than any
    # threshold, and stretched words would run into the next line.
    for ln in lines:
        span = max(ln.end - ln.start, 1e-3)
        acc = 0.0
        for w in ln.words:
            w.start = ln.start + span * acc / ln.syllables
            acc += w.syllables
            w.end = ln.start + span * acc / ln.syllables

    _fill_lines(lyrics, duration)
    if any(ln.backing for ln in lyrics.lines):
        place_backing(lyrics, duration, log=log)
    if skip:
        enforce_marks(lyrics, skip, duration, log=log)
        _fill_lines(lyrics, duration)
    return lyrics


# --------------------------------------------------------------------------- #
#  Whisper forced alignment
# --------------------------------------------------------------------------- #

def align_whisper(lyrics: Lyrics, audio_path: str, duration: float,
                  model_name: str = "medium", language: str = "ru",
                  device: Optional[str] = None, log: Log = _noop,
                  isolated: bool = False, skip: Optional[List[tuple]] = None,
                  model=None) -> Lyrics:
    lent = model is not None
    import stable_whisper

    from . import sysinfo
    ok, note = sysinfo.check(sysinfo.NEED_WHISPER.get(model_name, 2.2))
    if not ok:
        log("  " + note + tr(" If it crashes, take a smaller model.",
                          " Если упадёт — возьмите модель поменьше."))

    from . import lang as LG
    from . import models as M
    from .progress import Heartbeat

    # “auto” does not mean “let Whisper guess” but “we work it out from the
    # text”: the result is then predictable and visible in the log.
    if not language or language == "auto":
        language = LG.detect(lyrics.plain_text())
        log(tr(f"Language of the lyrics: {LG.label(language)} (worked out from the text)",
           f"Язык текста: {LG.label(language)} (определён по тексту)"))

    # Say what is true: if the model is on disk, promising a download is a lie —
    # the window next to it says “already downloaded”, and one of the two lied.
    if model is not None:
        # Handed in: a song aligned piece by piece must not load gigabytes anew
        # for every piece.
        pass
    else:
        log(M.load_note(model_name))
    try:
        # medium is a gigabyte and a half: both loading from disk and the first
        # download take minutes in silence, and the window looks frozen.
        need = sysinfo.NEED_WHISPER.get(model_name, 2.2)
        with Heartbeat(log, M.step_label(model_name), every=10.0,
                       slow_after=90.0,
                       slow_note=tr(
                           f"longer than usual. The “{model_name}” model needs about "
                           f"{need:.0f} GB of memory; when there is less, the system "
                           f"moves data to the disk and the step stretches out many "
                           f"times over. A smaller model helps: "
                           f"medium → small → base.",
                           f"дольше обычного. Модели «{model_name}» нужно около "
                           f"{need:.0f} ГБ памяти; если её мало, система "
                           f"перекладывает данные на диск, и шаг растягивается "
                           f"в разы. Помогает модель поменьше: "
                           f"medium → small → base.")):
            if model is None:
                model = stable_whisper.load_model(model_name, device=device)
    except Exception as e:
        # Catch a failed download separately: “Connection refused” explains
        # nothing by itself, and the cause is almost always this machine's net.
        low = str(e).lower()
        net = ("urlopen", "connection", "getaddrinfo", "timed out", "ssl",
               "max retries", "name resolution", "unreachable", "httperror")
        if any(k in low for k in net):
            raise RuntimeError(tr(
                f"could not download the Whisper model “{model_name}”. "
                f"Check the internet on this machine — the model downloads once "
                f"and then lives in ~/.cache/whisper. The original error: {e}",
                f"не удалось скачать модель Whisper «{model_name}». "
                f"Проверьте интернет на этой машине — модель качается один раз "
                f"и потом лежит в ~/.cache/whisper. Исходная ошибка: {e}"))
        if "checksum" in low or "sha256" in low:
            raise RuntimeError(tr(
                f"the “{model_name}” model file was damaged while downloading. "
                f"Delete ~/.cache/whisper and try again. The original error: {e}",
                f"файл модели «{model_name}» побился при загрузке. Удалите "
                f"~/.cache/whisper и повторите. Исходная ошибка: {e}"))
        raise

    # Given a file path, Whisper calls `ffmpeg` by name through PATH. When
    # ffmpeg comes from imageio-ffmpeg it has another name and is not found —
    # Windows answers “WinError 2”. So we decode ourselves and hand over ready
    # samples: 16 kHz mono float32 in [-1, 1], exactly what the model expects.
    audio_input = audio_path
    decoded = False
    try:
        import numpy as np
        from . import audio as A
        # On the separated voice the levels are levelled first: a screamed
        # vocal swings from a shout to a rasp, and the quiet half never reaches
        # the model otherwise. Only what the model hears changes — the sound of
        # the karaoke itself is untouched.
        pcm = A.read_pcm_mono(audio_path, 16000, af=A.LEVEL_VOICE if isolated else None)
        audio_input = np.frombuffer(pcm.tobytes(), dtype="<i2").astype("float32") / 32768.0
        decoded = True
        log(tr(f"  audio decoded with our own ffmpeg ({len(audio_input) / 16000:.0f} s)"
               + (", the voice levelled out for the model" if isolated else ""),
               f"  звук декодирован своим ffmpeg ({len(audio_input) / 16000:.0f} с)"
               + (", вокал выровнен по громкости для модели" if isolated else "")))
    except Exception as e:
        log(tr(f"  could not decode in advance ({e}) — handing Whisper the file path",
               f"  не вышло декодировать заранее ({e}) — отдаю Whisper путь к файлу"))

    # A wordless intro, a vocalise, a scream with nothing to write down are all
    # voice: no measurement tells them from singing, and only a person can say
    # which is which. Where they have said it, those stretches are cut out of
    # what the model hears — what it never hears, it cannot lay words on — and
    # the times are put back into the whole song afterwards.
    skip = spans(skip, duration)
    keep = keep_windows(skip, duration) if skip else []
    if skip and decoded and keep:
        import numpy as np
        pieces = [audio_input[int(a * 16000):int(b * 16000)] for a, b in keep]
        audio_input = np.concatenate(pieces)
        log(tr(f"  no words in: {', '.join(mmss(a) + '–' + mmss(b) for a, b in skip)}"
               f" — {sum(b - a for a, b in skip):.0f} s not shown to the model",
               f"  без текста: {', '.join(mmss(a) + '–' + mmss(b) for a, b in skip)}"
               f" — {sum(b - a for a, b in skip):.0f} с модели не показываю"))
    elif skip:
        keep = []
        log(tr("  the wordless stretches cannot be cut out without decoding — "
               "the whole song goes to the model, and they only guide the repairs",
               "  вырезать куски без текста не вышло — модели уходит вся песня, "
               "они учтутся только при ремонте"))

    # The backing never reaches the model. Alignment is linear: asked to place
    # the na-na-na BETWEEN the lead lines, it drags whole choruses into the
    # silence it can hear perfectly well is empty, just to make room. The lead
    # lines anchor cleanly on their own; the backing is placed by rule after.
    main_lines = [ln for ln in lyrics.lines if not ln.backing] or lyrics.lines
    main_words = [w for ln in main_lines for w in ln.words]
    main_text = "\n".join(ln.text for ln in main_lines)
    if len(main_lines) < len(lyrics.lines):
        log(tr(f"  backing lines kept away from the aligner: "
               f"{len(lyrics.lines) - len(main_lines)}",
               f"  бэк-строк не показано разметчику: "
               f"{len(lyrics.lines) - len(main_lines)}"))

    log(tr("Lining the text up with the audio…", "Выравниваю текст по звуку…"))
    try:
        # stable-ts complains through the warnings module — “12/34 segments failed
        # to align” and the like. In a console that scrolls past and is gone; it
        # belongs in the log with everything else, because it names the trouble
        # before any of our repairs even start.
        caught: List[warnings.WarningMessage] = []
        stack = warnings.catch_warnings(record=True)
        caught = stack.__enter__()
        warnings.simplefilter("always")
        # The longest step after the instrumental. stable-ts can report how many
        # seconds it has processed — send that to the log rather than to a
        # console progress bar, which the studio window never shows anyway.
        with Heartbeat(log, tr("alignment", "выравнивание"), slow_after=600.0,
                       slow_note=tr(
                           "is taking a while. On a CPU medium is about five times "
                           "slower than small, and with little memory slower still. "
                           "It can be interrupted, the timing will be recomputed "
                           "with another model.",
                           "идёт долго. На процессоре medium считает примерно "
                           "впятеро дольше small, а при нехватке памяти — ещё "
                           "дольше. Прервать можно, разметка пересчитается "
                           "с другой моделью.")) as hb:
            try:
                # verbose=False, not None: with None the library switches its
                # own counter off, and then the progress it hands us is zero
                # from beginning to end — which is how this step spent minutes
                # saying only how long it had been running.
                result = model.align(audio_input, main_text,
                                     language=language, original_split=True,
                                     progress_callback=hb.progress, verbose=False)
            except TypeError:
                # older stable-ts builds lack these parameters — the elapsed
                # time still shows, it comes from Heartbeat itself
                result = model.align(audio_input, main_text,
                                     language=language, original_split=True)
        stack.__exit__(None, None, None)
        report_warnings(caught, len(lyrics.lines), log)
    except FileNotFoundError as e:
        stack.__exit__(None, None, None)
        raise RuntimeError(tr(
            f"Whisper could not start ffmpeg ({e}). Install it into the system: "
            f"winget install Gyan.FFmpeg — and restart the command line.",
            f"Whisper не смог запустить ffmpeg ({e}). Поставьте его в систему: "
            f"winget install Gyan.FFmpeg — и перезапустите командную строку."))

    rec: List[tuple] = []
    probs: List[float] = []
    for seg in result.segments:
        for w in (seg.words or []):
            key = normalize_token(w.word)
            if key:
                p = getattr(w, "probability", None)
                rec.append((key, float(w.start), float(w.end),
                            float(p) if p is not None else None))
                if p is not None:
                    probs.append(float(p))
    if not rec:
        raise RuntimeError(tr("Whisper returned no timed words at all",
                              "Whisper не вернул ни одного слова с таймингом"))

    if keep:
        def whole(t: float) -> float:
            """From the stitched audio back into the song it was cut from."""
            at = 0.0
            for a, b in keep:
                if t <= at + (b - a):
                    return a + (t - at)
                at += b - a
            return keep[-1][1]

        rec = [(k, whole(a), whole(b), pr) for k, a, b, pr in rec]

    matched = _apply_recognized(main_words, rec)
    # This is NOT a “is it the right text” check: align() forces the given text
    # onto the audio, so the words always match. It catches a tokenisation
    # mismatch between our parser and Whisper's — without it such a failure
    # silently turns the timing into an evenly spread blanket.
    if matched < 0.4:
        raise RuntimeError(tr(
            f"the words could not be matched to Whisper's output "
            f"({matched:.0%} matched) — looks like an incompatible stable-ts version",
            f"слова не удалось сопоставить с выводом Whisper (совпало {matched:.0%}) — "
            f"похоже на несовместимую версию stable-ts"))

    # Low confidence, on the other hand, hints the text does not fit the audio
    if probs:
        probs.sort()
        median = probs[len(probs) // 2]
        log(tr(f"  words matched: {matched:.0%}, confidence: {median:.2f}",
               f"  сопоставлено слов: {matched:.0%}, уверенность: {median:.2f}"))
        if median < 0.08:
            log(tr("  NOTE: the confidence is very low. Check that the text really "
                   "belongs to this recording and that --lang is right; the timing "
                   "may be rubbish.",
                   "  ВНИМАНИЕ: уверенность очень низкая. Проверьте, что текст именно "
                   "от этой записи и что --lang указан верно; разметка может быть мусорной."))
    else:
        log(tr(f"  words matched: {matched:.0%}", f"  сопоставлено слов: {matched:.0%}"))

    # the model weighs gigabytes — let it go at once, it is not needed further.
    # A lent one is its owner's business: pieces of one song share it.
    del result
    if not lent:
        del model
    import gc
    gc.collect()

    _trim_leading_silence(lyrics)
    # Line bounds come from the words — without this step lines have no times
    # yet, and the repairs would compare emptiness with emptiness.
    _fill_lines(lyrics, duration)
    repair_lines(lyrics, log=log)      # Whisper sometimes drops a word far away
    # …and sometimes drops a dozen of them in one spot. Looking at the audio is
    # only worth it once we know there is a pile to spread.
    # The same stretches bound the repairs: spreading a pile over a vocalise is
    # exactly what the person said not to do.
    sung_end = min(last_sound(audio_path, duration), keep[-1][1] if keep else duration)
    text_end = max((ln.end for ln in lyrics.lines if ln.end is not None), default=0.0)
    untexted = max(0.0, sung_end - text_end)
    if pile_runs(lyrics.lines):
        repair_piles(lyrics, duration, log=log,
                     floor=max(first_sound(audio_path), keep[0][0] if keep else 0.0),
                     untexted=untexted)
    # Only on a separated vocal: there silence is silence. On a mix a “quiet”
    # stretch may simply be a quieter verse, and moving lines off it would do
    # the damage it is meant to prevent.
    if isolated or skip:
        repair_silent(lyrics, duration, audio_path, log=log, skip=skip)
    if any(ln.backing for ln in lyrics.lines):
        place_backing(lyrics, duration, log=log)
    if skip:
        # A line may still reach across a hole from the outside: the aligner
        # had to end it somewhere, and the far side of the silence was the
        # nearest thing it could find.
        clip_to_marks(lyrics, skip, log=log)
        # …and whatever is left overlapping after every gentler pass is forced
        # out: the marks are the person's own words, and they win.
        enforce_marks(lyrics, skip, duration, log=log)
    repair_order(lyrics, log=log)
    repair_ragged(lyrics, log=log)
    _fill_lines(lyrics, duration)      # after repairs the bounds may exceed the track

    # What could not be spread stays a pile, and a pile is not a timing: those
    # lines fly past in a blink. Better to name them than to hand over a page
    # that looks finished and is not.
    # A whole stretch of singing with no text under it means the alignment did
    # not just stumble on a line — it lost its place. Worth saying: the fix is
    # not dragging lines one by one.
    if untexted > max(15.0, 0.15 * duration):
        log(tr(f"  NOTE: the text ends at {text_end // 60:.0f}:{text_end % 60:04.1f} while "
               f"the singing goes on to {sung_end // 60:.0f}:{sung_end % 60:04.1f} — "
               f"{sung_end - text_end:.0f} s of song with no lyrics under it. Either the "
               f"text is written out fewer times than it is sung, or the alignment lost "
               f"its place. “Re-time” with the loudness engine spreads the lines over the "
               f"whole song instead.",
               f"  ВНИМАНИЕ: текст кончается на {text_end // 60:.0f}:{text_end % 60:04.1f}, "
               f"а поют до {sung_end // 60:.0f}:{sung_end % 60:04.1f} — "
               f"{sung_end - text_end:.0f} с песни без единой строки. Либо в тексте "
               f"выписано меньше повторов, чем поётся, либо разметка потеряла место. "
               f"«Разметить заново» движком по энергии разложит строки по всей песне."))

    left = pile_share(lyrics)
    if left > 0.02:
        stuck = [i + 1 for a, b in pile_runs(lyrics.lines) for i in range(a, b + 1)]
        spot = lyrics.lines[stuck[0] - 1].start if stuck else 0.0
        log(tr(f"  NOTE: {len(stuck)} of {len(lyrics.lines)} lines could not be timed — "
               f"they are piled at {spot // 60:.0f}:{spot % 60:04.1f} (lines "
               f"{stuck[0]}–{stuck[-1]}). Whisper heard no words there: a quiet or "
               f"whispered patch. Drag them into place in the studio, or press "
               f"“Re-time” with the loudness engine.",
               f"  ВНИМАНИЕ: {len(stuck)} строк из {len(lyrics.lines)} разметить не вышло — "
               f"они свалены в кучу на {spot // 60:.0f}:{spot % 60:04.1f} (строки "
               f"{stuck[0]}–{stuck[-1]}). Whisper не расслышал там слов: тихое или "
               f"шёпотом спетое место. Растащите их в студии мышкой или нажмите "
               f"«Разметить заново» с движком по энергии."))
    return lyrics


def report_warnings(caught, lines: int, log: Log) -> int:
    """Put what stable-ts muttered into the log, and say what it means.

    “12/34 segments failed to align” is the single most useful line the aligner
    ever prints, and it goes to a console window nobody is looking at. Returns
    how many lines the aligner admits it could not place.
    """
    failed = 0
    for w in caught or ():
        text = str(getattr(w, "message", w)).strip()
        if not text:
            continue
        log("  " + text.splitlines()[0])
        m = re.search(r"(\d+)\s*/\s*(\d+)\s+segments failed to align", text)
        if m:
            failed = int(m.group(1))
            total = int(m.group(2)) or lines
            log(tr(f"  that is {failed} of {total} lines with no timing of their own — "
                   f"Whisper heard no words there. They come out piled in one spot; "
                   f"what was done with them is said below.",
                   f"  это {failed} строк из {total} без своего времени — Whisper не "
                   f"расслышал там слов. Они выходят сваленными в одну точку; что с ними "
                   f"сделано, сказано ниже."))
    return failed


def _apply_recognized(words: List[Word], rec: List[tuple]) -> float:
    """Match our words against the recognised ones. Returns the exact-match share."""
    ours = [normalize_token(w.text) for w in words]
    theirs = [r[0] for r in rec]

    exact = 0
    matcher = difflib.SequenceMatcher(a=ours, b=theirs, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            exact += i2 - i1
            for k in range(i2 - i1):
                words[i1 + k].start = rec[j1 + k][1]
                words[i1 + k].end = rec[j1 + k][2]
                if len(rec[j1 + k]) > 3:
                    words[i1 + k].prob = rec[j1 + k][3]
        elif tag == "replace" and (i2 - i1) and (j2 - j1):
            # spread the matched stretch over our words in proportion to syllables
            t0, t1 = rec[j1][1], rec[j2 - 1][2]
            chunk = words[i1:i2]
            total = sum(w.syllables for w in chunk) or 1
            acc = 0.0
            # A stretch the model heard as something else: the words are ours,
            # the confidence is the worst of what it did hear there.
            heard = [r[3] for r in rec[j1:j2] if len(r) > 3 and r[3] is not None]
            for w in chunk:
                w.prob = min(heard) if heard else None
                w.start = t0 + (t1 - t0) * acc / total
                acc += w.syllables
                w.end = t0 + (t1 - t0) * acc / total

    _interpolate_gaps(words)
    return exact / len(words) if words else 0.0


def _trim_leading_silence(lyrics: Lyrics, factor: float = 3.0) -> None:
    """Whisper glues the pause before a phrase onto its first word — trim it.

    Only the first word of a line is touched, and only when it is implausibly
    long: long melismas in the middle and at the end are left alone.
    """
    for ln in lyrics.lines:
        if not ln.words:
            continue
        w = ln.words[0]
        if w.start is None or w.end is None:
            continue
        expect = 0.35 * w.syllables + 0.15
        if (w.end - w.start) > max(1.2, factor * expect):
            w.start = w.end - expect


def _interpolate_gaps(words: List[Word]) -> None:
    """Words left without a time (insertions in the text) are filled in between."""
    i = 0
    n = len(words)
    while i < n:
        if words[i].start is not None:
            i += 1
            continue
        j = i
        while j < n and words[j].start is None:
            j += 1
        left = words[i - 1].end if i > 0 and words[i - 1].end is not None else 0.0
        right = words[j].start if j < n and words[j].start is not None else left + 0.4 * (j - i)
        chunk = words[i:j]
        total = sum(w.syllables for w in chunk) or 1
        acc = 0.0
        for w in chunk:
            w.start = left + (right - left) * acc / total
            acc += w.syllables
            w.end = left + (right - left) * acc / total
        i = j


# --------------------------------------------------------------------------- #

def repair_lines(lyrics: Lyrics, max_word_gap: float = 1.2, log: Log = _noop) -> int:
    """Put back together the lines whose words drifted apart in time.

    Inside one sung line there are no multi-second gaps between words. If one
    is there, alignment missed: a word flew far away from its neighbours. The
    heaviest cluster of words is taken as the line\'s real place, and the strays
    are pulled up against it, leaving the well-placed middle alone.
    """
    fixed = 0
    for idx, ln in enumerate(lyrics.lines):
        ws = ln.words
        # times may not be set yet — then there is nothing to repair
        if len(ws) < 2 or any(w.start is None or w.end is None for w in ws):
            continue

        groups, cur = [], [ws[0]]
        for prev, w in zip(ws, ws[1:]):
            if (w.start or 0) - (prev.end or 0) > max_word_gap:
                groups.append(cur)
                cur = [w]
            else:
                cur.append(w)
        groups.append(cur)
        if len(groups) < 2:
            continue

        # Which cluster counts as the line's real place. Syllable weight alone
        # is not enough: the neighbouring lines define a window this one has to
        # fall into. Otherwise a correct word gets pulled to the wrong ones.
        prev = lyrics.lines[idx - 1] if idx else None
        lo = (prev.end if prev is not None and prev.end is not None else 0.0)
        nxt = next((l for l in lyrics.lines[idx + 1:]
                    if l.words and l.start is not None), None)
        hi = nxt.start if nxt else float("inf")

        def score(g):
            fits = (g[0].start >= lo - 0.5) and (g[-1].end <= hi + 0.5)
            return (1 if fits else 0, sum(x.syllables for x in g))

        best = max(groups, key=score)
        s, e = best[0].start, best[-1].end
        bi = ws.index(best[0])
        before, after = ws[:bi], ws[bi + len(best):]

        floor = lyrics.lines[idx - 1].end if idx else 0.0
        if before:
            need = min(0.35 * sum(w.syllables for w in before), 2.0)
            t0 = max(s - need, floor or 0.0, 0.0)
            _spread(before, t0, s)
        if after:
            need = min(0.35 * sum(w.syllables for w in after), 2.0)
            _spread(after, e, e + need)

        ln.start, ln.end = ws[0].start, ws[-1].end
        fixed += 1

    if fixed:
        log(tr(f"  lines whose words drifted apart, put back together: {fixed}",
               f"  собрал обратно строк с разъехавшимися словами: {fixed}"))
    return fixed


def _spread(words: List[Word], start: float, end: float) -> None:
    total = sum(w.syllables for w in words) or 1
    span = max(end - start, 0.05)
    acc = 0.0
    for w in words:
        w.start = start + span * acc / total
        acc += w.syllables
        w.end = start + span * acc / total


# The shortest a syllable can honestly be sung. Below this the timing is not
# fast singing, it is a pile: the aligner gave up and dropped the words where
# it stopped looking.
_MIN_PER_SYLLABLE = 0.07
# An unhurried pace for a sung syllable — what a spread-out pile is given.
_SUNG_PER_SYLLABLE = 0.45


def _syl(ln) -> int:
    return sum(w.syllables for w in ln.words) or 1


def pile_runs(lines) -> List[tuple]:
    """Runs of lines dumped at one instant, as (first, last) indexes.

    A pile is judged by the run as a whole, not line by line: the aligner drops
    a whole stretch of text at one moment, and the odd line inside it may look
    plausible on its own. A run counts as a pile when several lines together
    take less time than their syllables could possibly be sung in.
    """
    runs = []
    n = len(lines)
    i = 0
    while i < n:
        if lines[i].start is None or lines[i].end is None or not lines[i].words:
            i += 1
            continue
        syl = _syl(lines[i])
        best = i
        j = i + 1
        while j < n and lines[j].start is not None and lines[j].end is not None and lines[j].words:
            syl += _syl(lines[j])
            if (lines[j].end - lines[i].start) < _MIN_PER_SYLLABLE * syl:
                best = j
            elif best > i:
                break                              # the pile has ended
            j += 1
        if best > i:
            runs.append((i, best))
            i = best + 1
        else:
            i += 1
    return runs


def pile_share(lyrics: Lyrics) -> float:
    """What share of the lines is stuck in piles. 0 when the timing is sound."""
    lines = lyrics.lines
    if not lines:
        return 0.0
    return sum(b - a + 1 for a, b in pile_runs(lines)) / len(lines)


def duplicate_of(lines, a: int, b: int) -> Optional[tuple]:
    """Does the run a..b repeat, word for word, a block of lines that IS timed?

    A lyrics file often holds the song written out more times than it is sung —
    a verse pasted twice, a chorus copied “for completeness”. There is no audio
    for the extra copy, so the aligner has nowhere to put it and drops it in a
    pile. Such lines must not be spread over the music: nobody sings them there.
    Naming the block they repeat is the whole answer for the person.
    """
    run = [normalize_token(" ".join(w.text for w in ln.words)) for ln in lines[a:b + 1]]
    n = len(run)
    if n < 2:
        return None
    piled = {i for x, y in pile_runs(lines) for i in range(x, y + 1)}
    for i in range(len(lines) - n + 1):
        if i <= b and i + n - 1 >= a:                 # the run itself
            continue
        if any(k in piled for k in range(i, i + n)):   # a pile is no proof
            continue
        cand = [normalize_token(" ".join(w.text for w in ln.words))
                for ln in lines[i:i + n]]
        if difflib.SequenceMatcher(a=run, b=cand, autojunk=False).ratio() >= 0.8:
            return (i, i + n - 1)
    return None


def first_sound(audio_path: str) -> float:
    """When the singing starts — so a pile at the head is not spread over silence."""
    try:
        from . import audio as AU
        from . import report as R
        env, hop = AU.rms_envelope(audio_path)
        quiet = R.quiet_stretches(env, hop)
    except Exception:
        return 0.0
    for q in quiet:
        if q["start"] <= 0.2:                    # a silence the song opens with
            return float(q["end"])
    return 0.0


def last_sound(audio_path: str, duration: float) -> float:
    """When the singing ends — the tail of a track is usually music or silence."""
    try:
        from . import audio as AU
        from . import report as R
        env, hop = AU.rms_envelope(audio_path)
        quiet = R.quiet_stretches(env, hop)
    except Exception:
        return duration
    for q in quiet:
        if q["end"] >= duration - 0.5:            # the silence the song ends with
            return float(q["start"])
    return duration


def repair_piles(lyrics: Lyrics, duration: float, log: Log = _noop,
                 floor: float = 0.0, untexted: float = 0.0) -> int:
    """Spread out the lines an aligner piled up in one spot.

    On a quiet intro, a long instrumental or a whispered verse Whisper finds
    nothing to hold on to and returns a whole stretch of text at the single
    moment where it did hear something. On screen that is a pile: a dozen lines
    inside a fraction of a second, and the karaoke leaps through half the lyrics
    in one blink.

    The words are lost either way — but their ORDER is not, and neither is the
    free time around the pile. Spreading the run across that free time is much
    closer to the truth than one instant, and every line stays draggable.

    Only the room between the neighbouring sound lines is used, and only as much
    of it as the singing needs: a gap can hold wordless sounds — a breath, an
    intro, humming — and stretching seven lines over half a minute of those
    claims as lyrics what is not. So the run keeps a singable pace and sits
    against the line that follows it, which is where the aligner found its
    footing again.

    When the neighbours themselves contradict each other, the pile is left
    alone: moving it would just stack lines on top of a line that IS timed right.
    """
    lines = lyrics.lines
    fixed = 0
    phantom = []
    for a, b in pile_runs(lines):
        dup = duplicate_of(lines, a, b)
        if dup:
            # Not sung at all — an extra copy in the lyrics file. Spreading it
            # would paint words over music nobody sings there.
            phantom.append((a, b, dup))
            continue
        run = lines[a:b + 1]
        lo = lines[a - 1].end if a and lines[a - 1].end is not None else floor
        hi = lines[b + 1].start if b + 1 < len(lines) and lines[b + 1].start is not None \
            else duration
        lo = max(0.0, min(lo, duration))
        hi = max(0.0, min(hi, duration))
        need = sum(_syl(ln) for ln in run) * _MIN_PER_SYLLABLE
        was = (run[-1].end or 0.0) - (run[0].start or 0.0)
        if hi <= lo or (hi - lo) <= max(need, was) + 0.05:
            continue                               # nowhere to spread it
        total = sum(_syl(ln) for ln in run)
        # An unhurried sung pace. Wider than the “nobody sings that fast” floor,
        # narrower than the whole gap — the rest of the gap may well be music.
        span = min(hi - lo, max(_SUNG_PER_SYLLABLE * total, need))
        # Against the following line when there is one: a pile forms where the
        # aligner lost the text, and it re-locked at the line after it.
        base = hi - span if b + 1 < len(lines) else lo
        acc = 0.0
        for ln in run:
            t0 = base + span * acc / total
            acc += _syl(ln)
            t1 = base + span * acc / total
            _spread(ln.words, t0, max(t1 - 0.05, t0 + 0.05))
            ln.start, ln.end = ln.words[0].start, ln.words[-1].end
        fixed += len(run)

    if fixed:
        log(tr(f"  lines the aligner piled in one spot, spread out: {fixed}",
               f"  разложил строк, сваленных разметчиком в одну точку: {fixed}"))
    for a, b, (c, d) in phantom:
        if untexted > 15.0:
            # The words are sung twice and there is a whole stretch of singing with
            # no text on it: the aligner locked onto the wrong repetition and put
            # both copies of the text on one pass of the song.
            log(tr(f"  NOTE: lines {a + 1}–{b + 1} say the same as lines {c + 1}–{d + 1}, "
                   f"and {untexted:.0f} s of singing has no text at all. The song sings "
                   f"those words twice, and the timing landed on one pass only — it is "
                   f"out by a whole repetition, not by a line. “Re-time” with the "
                   f"loudness engine lays the lines over the whole song instead.",
                   f"  ВНИМАНИЕ: строки {a + 1}–{b + 1} слово в слово повторяют строки "
                   f"{c + 1}–{d + 1}, а {untexted:.0f} с пения остались вообще без текста. "
                   f"Эти слова поются дважды, а разметка легла только на один прогон — "
                   f"она сдвинута на целый повтор, а не на строку. «Разметить заново» "
                   f"движком по энергии разложит строки по всей песне."))
        else:
            log(tr(f"  NOTE: lines {a + 1}–{b + 1} say the same as lines {c + 1}–{d + 1}, "
                   f"which are timed — and there is no audio for them. The lyrics file "
                   f"seems to be written out more times than the song sings it: remove "
                   f"the extra copy and press “Re-time”. Left where they are for now.",
                   f"  ВНИМАНИЕ: строки {a + 1}–{b + 1} слово в слово повторяют строки "
                   f"{c + 1}–{d + 1}, которые размечены, — а в записи их нет. Похоже, в "
                   f"файле с текстом песня выписана больше раз, чем поётся: уберите лишний "
                   f"повтор и нажмите «Разметить заново». Пока оставил их на месте."))
    return fixed


def silent_spans(env: List[float], dt: float, least: float = 2.5) -> List[Dict]:
    """Where there is no voice at all — measured against the loudest it gets.

    The panel's “quiet” is relative to the song's own middle, which is right for
    showing where the singing thins out. For moving lines it is wrong twice
    over: a song loud from end to end comes out “all quiet”, and a whispered
    verse — real singing, with words in it — comes out quiet as well, and its
    lines would be dragged off it.

    The question here is narrower and answerable: is there any voice at all? On
    a separated vocal that is a hundredth of the loudest moment. A whisper
    stands well above that; an interlude does not.
    """
    if not env or dt <= 0:
        return []
    peak = max(env)
    if peak <= 0:
        return []
    thr = peak * 0.02
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


def _voiced_windows(lo: float, hi: float, quiet: List[Dict]) -> List[List[float]]:
    """The parts of [lo, hi] where the voice is heard: the gaps between silences."""
    out, at = [], lo
    for q in sorted(quiet, key=lambda q: q["start"]):
        a, b = max(lo, q["start"]), min(hi, q["end"])
        if a > at:
            out.append([at, min(a, hi)])
        at = max(at, b)
        if at >= hi:
            break
    if at < hi:
        out.append([at, hi])
    return [w for w in out if w[1] - w[0] > 0.2]


def repair_silent(lyrics: Lyrics, duration: float, audio_path: str,
                  log: Log = _noop, skip: Optional[List[tuple]] = None) -> int:
    """Move lines off the stretches where the separated voice is silent.

    The aligner is made to place every word somewhere, and over an interlude or
    a solo it places them on the music: the line looks timed, the karaoke shows
    words, and nobody sings. On the separated vocal such a stretch is real
    silence — so it can be known, not guessed.

    A run of lines sitting wholly inside that silence is moved to the nearest
    stretch of actual singing between its timed neighbours, at a sung pace,
    against the line that follows — the same reasoning as with piles: the exact
    words are lost, but their order is not, and singing beats silence as a place
    to put them. When there is no singing between the neighbours at all, the
    lines stay put and the log names them: perhaps they are simply not sung.
    """
    try:
        from . import audio as AU
        env, hop = AU.rms_envelope(audio_path)
        quiet = silent_spans(env, hop)
    except Exception:
        quiet = []
    # Even so: if what is left counts as silent almost from end to end, that is
    # not knowledge but its absence, and acting on it would drag the whole text
    # somewhere.
    if sum(q["end"] - q["start"] for q in quiet) > 0.85 * duration:
        quiet = []

    # A stretch a person marked as wordless counts as silence, whatever the
    # loudness says: a vocalise is voice, and only they can know it holds no
    # words.
    for a, b in (skip or []):
        quiet.append({"start": a, "end": b})
    quiet.sort(key=lambda q: q["start"])
    if not quiet:
        return 0

    lines = lyrics.lines

    def sits_in_silence(ln) -> bool:
        if ln.start is None or ln.end is None or not ln.words:
            return False
        return any(ln.start >= q["start"] - 0.25 and ln.end <= q["end"] + 0.25
                   for q in quiet)

    flags = [sits_in_silence(ln) for ln in lines]
    moved, stuck = 0, []
    i = 0
    while i < len(lines):
        if not flags[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(lines) and flags[j + 1]:
            j += 1
        run = lines[i:j + 1]
        lo = lines[i - 1].end if i and lines[i - 1].end is not None else 0.0
        hi = lines[j + 1].start if j + 1 < len(lines) and lines[j + 1].start is not None             else duration
        lo, hi = max(0.0, min(lo, duration)), max(0.0, min(hi, duration))
        total = sum(_syl(ln) for ln in run)
        need = total * _MIN_PER_SYLLABLE
        pick = None
        # nearest to the following line: that is where the aligner re-locks
        for w in reversed(_voiced_windows(lo, hi, quiet)):
            if w[1] - w[0] >= need + 0.05:
                pick = w
                break
        if not pick:
            stuck.append((i, j, run[0].start or 0.0))
            i = j + 1
            continue
        span = min(pick[1] - pick[0], max(_SUNG_PER_SYLLABLE * total, need))
        base = (pick[1] - span) if j + 1 < len(lines) else pick[0]
        acc = 0.0
        for ln in run:
            t0 = base + span * acc / total
            acc += _syl(ln)
            t1 = base + span * acc / total
            _spread(ln.words, t0, max(t1 - 0.05, t0 + 0.05))
            ln.start, ln.end = ln.words[0].start, ln.words[-1].end
        moved += len(run)
        i = j + 1

    if moved:
        log(tr(f"  lines that sat where the voice is silent, moved onto singing: {moved}",
               f"  строк, лежавших там, где вокал молчит, перенесено на пение: {moved}"))
    for a, b, at in stuck:
        log(tr(f"  NOTE: lines {a + 1}–{b + 1} sit at {at // 60:.0f}:{at % 60:04.1f}, "
               f"where the voice is silent — and there is no singing between their "
               f"neighbours to move them to. Perhaps they are simply not sung in this "
               f"recording; check them, or remove them from the lyrics.",
               f"  ВНИМАНИЕ: строки {a + 1}–{b + 1} стоят на {at // 60:.0f}:{at % 60:04.1f}, "
               f"где вокал молчит, — а пения между соседями, куда их перенести, нет. "
               f"Возможно, в этой записи они просто не поются; проверьте их или уберите "
               f"из текста."))
    return moved


def clip_to_marks(lyrics: Lyrics, skip: List[tuple], log: Log = _noop) -> int:
    """Keep line spans out of the stretches that hold no words.

    A line next to a marked stretch reaches across it: the aligner has to end a
    line somewhere, and the nearest thing it can find is the far side of the
    silence. On screen a line of five words then lasts a minute and a half, and
    putting that right by hand means dragging its edge across the whole hole.

    The marks already say where the emptiness is, so the span is simply cut
    back to it: a line that ends inside a hole ends where the hole begins, one
    that starts inside it starts where it ends. Words keep their order and are
    squeezed into what is left; a line lying wholly inside a hole is not this
    function's business — that is what moving it onto the singing is for.
    """
    fixed = 0
    for ln in lyrics.lines:
        if ln.start is None or ln.end is None or not ln.words:
            continue
        if ln.keep:
            # A line left to the original LIVES where the person does not
            # sing: the mark says “nothing for you here”, and this line is
            # not theirs. Trimmed out of the hole, its kept voice went with
            # it — and the intro fell silent.
            continue
        a, b = ln.start, ln.end
        for lo, hi in skip:
            if b <= lo or a >= hi:
                continue                      # nowhere near this hole
            if a >= lo and b <= hi:
                continue                      # wholly inside: not ours to trim
            if a < lo < b <= hi:
                b = lo                        # runs into the hole: end sooner
            elif lo <= a < hi < b:
                a = hi                        # starts inside it: begin later
            elif a < lo and hi < b:
                # the line spans the whole hole: keep the longer half
                if lo - a >= b - hi:
                    b = lo
                else:
                    a = hi
        if abs(a - ln.start) < 0.01 and abs(b - ln.end) < 0.01:
            continue
        if b - a < 0.2:
            continue                          # nothing usable would be left
        _spread(ln.words, a, b)
        ln.start, ln.end = ln.words[0].start, ln.words[-1].end
        fixed += 1
    if fixed:
        log(tr(f"  lines trimmed back out of the wordless stretches: {fixed}",
               f"  строк подрезано по краям пустот: {fixed}"))
    return fixed


def _room_after(lines, k: int, want: float, gap: float = 0.05) -> float:
    """How much time the lines from `k` on can give up, without moving one
    that must not move.

    Each line can yield the silence in front of the one after it, less the
    breath they need between them. A line the singer marked as the original's
    own is anchored to a voice on the record and is never pushed.
    """
    have = 0.0
    for idx in range(k, len(lines)):
        ln = lines[idx]
        if ln.start is None or ln.end is None or not ln.words or ln.keep:
            break
        nxt = lines[idx + 1] if idx + 1 < len(lines) else None
        if nxt is None or nxt.start is None:
            return want                    # nothing after: all the room there is
        if nxt.keep:
            have += max(nxt.start - ln.end - gap, 0.0)
            break
        have += max(nxt.start - ln.end - gap, 0.0)
        if have >= want:
            break
    return min(have, want)


def _absorb(lines, k: int, delta: float, gap: float = 0.05) -> None:
    """Push the lines from `k` on later by `delta`, letting the gaps eat it.

    The first line moves the whole way; the next only as far as the silence
    before it failed to cover, and by the third or fourth there is usually
    nothing left to pass on.
    """
    left = delta
    idx = k
    while idx < len(lines) and left > 1e-3:
        ln = lines[idx]
        if ln.start is None or ln.end is None or not ln.words or ln.keep:
            break
        for w in ln.words:
            w.start += left
            w.end += left
        ln.start, ln.end = ln.words[0].start, ln.words[-1].end
        nxt = lines[idx + 1] if idx + 1 < len(lines) else None
        if nxt is None or nxt.start is None:
            break
        left = max(gap - (nxt.start - ln.end), 0.0)
        idx += 1


def enforce_marks(lyrics: Lyrics, skip, duration: float, log: Log = _noop) -> int:
    """No words on a marked stretch — as a guarantee, not an intention.

    The gentler passes move and trim where there is room. When there is none —
    the aligner crowded the following lines right against the hole — a run used
    to be left inside it, with a note in the log. But the marks are the
    person's own words about their song. A line squeezed in tight beside the
    hole is a visible flaw in the right place; a line lying over a vocalise is
    the one thing they explicitly said must not happen.
    """
    marks = spans(skip, duration)
    if not marks:
        return 0
    lines = lyrics.lines

    def hit(ln):
        if ln.start is None or ln.end is None or not ln.words:
            return None
        if ln.keep:
            return None       # the original's own line may stand in the hole
        for a, b in marks:
            if min(ln.end, b) - max(ln.start, a) > 0.05:
                return (a, b)
        return None

    moved, cramped, borrowed = 0, [], []
    i = 0
    while i < len(lines):
        h = hit(lines[i])
        if not h:
            i += 1
            continue
        j = i
        lo_h, hi_h = h
        while j + 1 < len(lines):
            h2 = hit(lines[j + 1])
            if not h2:
                break
            lo_h, hi_h = min(lo_h, h2[0]), max(hi_h, h2[1])
            j += 1
        run = lines[i:j + 1]
        prv = lines[i - 1].end if i and lines[i - 1].end is not None else 0.0
        nxt = lines[j + 1].start if j + 1 < len(lines) and \
            lines[j + 1].start is not None else duration
        total = sum(_syl(ln) for ln in run) or 1
        # The least this run can honestly take: every syllable at its shortest,
        # plus the breath left between one line and the next. The breath used
        # to be left out, so a run given exactly `need` still came out under
        # the floor by a twentieth of a second a line.
        need = total * _MIN_PER_SYLLABLE + 0.05 * len(run)
        # singing between the neighbours, holes taken out; nearest the following
        # line with room to breathe, else simply the widest there is
        wins = _voiced_windows(min(prv, lo_h), max(nxt, hi_h),
                               [{"start": a, "end": b} for a, b in marks])
        wins = [w for w in wins if w[1] > prv and w[0] < max(nxt, hi_h)]
        pick = None
        for w in reversed(wins):
            if w[1] - w[0] >= need + 0.05:
                pick = w
                break
        if not pick and wins:
            pick = max(wins, key=lambda w: w[1] - w[0])
        if not pick or pick[1] - pick[0] < 0.2:
            # no singing anywhere between the neighbours: right against the
            # hole then, and said out loud
            pick = [hi_h, hi_h + max(need, 0.3)]
            cramped.append((i, j, hi_h))
        pick = [pick[0], pick[1]]
        # However that window was chosen, it may be far too small for the words
        # that have to stand in it — and this is where a run came out at a tenth
        # of a second a line, which is not a tight line but the very pile this
        # module exists to undo. The honest floor was worked out above and then
        # never used: `need`, the least these syllables can be sung in. The room
        # for it is borrowed from the lines that follow — only as much as their
        # own silences can spare, and never across another mark.
        if pick[1] - pick[0] < need - 1e-6:
            after = [a for a, _ in marks if a >= pick[1] - 1e-6]
            wall = min(after) if after else duration
            over = min(need - (pick[1] - pick[0]), max(wall - pick[1], 0.0))
            if over > 1e-3:
                if j + 1 >= len(lines):
                    pick[1] += over          # nothing follows: take it all
                    borrowed.append((i, j, over))
                else:
                    got = _room_after(lines, j + 1, over)
                    if got > 1e-3:
                        _absorb(lines, j + 1, got)
                        pick[1] += got
                        borrowed.append((i, j, got))
        span = min(pick[1] - pick[0], max(_SUNG_PER_SYLLABLE * total, need))
        base = (pick[1] - span) if j + 1 < len(lines) else pick[0]
        acc = 0.0
        for ln in run:
            t0 = base + span * acc / total
            acc += _syl(ln)
            t1 = base + span * acc / total
            _spread(ln.words, t0, max(t1 - 0.05, t0 + 0.05))
            ln.start, ln.end = ln.words[0].start, ln.words[-1].end
            moved += 1
        i = j + 1
    if moved:
        log(tr(f"  lines forced off the marked stretches: {moved}",
               f"  строк принудительно убрано с отмеченных пустот: {moved}"))
    for a, b, got in borrowed:
        log(tr(f"  lines {a + 1}–{b + 1} had less room than their syllables can be "
               f"sung in; {got:.1f} s was borrowed from what follows",
               f"  строкам {a + 1}–{b + 1} досталось меньше места, чем их слоги "
               f"можно спеть; {got:.1f} с занято у следующих"))
    for a, b, at in cramped:
        log(tr(f"  NOTE: lines {a + 1}–{b + 1} had nowhere to go and are squeezed in "
               f"right after the mark at {mmss(at)} — cramped on purpose: better a "
               f"tight line in the right place than words over the stretch you "
               f"marked. Spread them out by hand.",
               f"  ВНИМАНИЕ: строкам {a + 1}–{b + 1} некуда было встать, они прижаты "
               f"сразу после отметки на {mmss(at)} — тесно нарочно: лучше тесная "
               f"строка в правильном месте, чем слова поверх куска, который вы "
               f"отметили. Растащите их руками."))
    return moved


def place_backing(lyrics: Lyrics, duration: float, log: Log = _noop) -> int:
    """Put the backing lines where backing is sung: with their lead, not after.

    The aligner is linear — it looks for the na-na-na BETWEEN the lead lines,
    while the record sings it OVER them, so the model has nothing to hold on to
    and scatters them. The lead comes out right for the same reason. So the
    backing is placed by rule instead: a tail split off a lead line lies over
    that line — a duet; a standalone backing line takes the gap after its lead,
    at a sung pace. Both are one drag away from anywhere better.
    """
    lines = lyrics.lines
    placed = 0
    for i, ln in enumerate(lines):
        if not ln.backing or not ln.words:
            continue
        j = i - 1
        while j >= 0 and (lines[j].backing or lines[j].start is None):
            j -= 1
        if j < 0:
            continue                      # nothing to lean on: leave the model's guess
        lead = lines[j]
        k = i + 1
        while k < len(lines) and (lines[k].backing or lines[k].start is None):
            k += 1
        nxt = lines[k].start if k < len(lines) else duration
        if ln.tail:
            t0, t1 = lead.start, lead.end            # a duet with its own line
        else:
            t0 = lead.end
            room = max(nxt - t0, 0.0)
            want = max(_SUNG_PER_SYLLABLE * _syl(ln), 0.8)
            t1 = t0 + (min(room, want) if room > 0.3 else want)
        _spread(ln.words, t0, max(t1 - 0.05, t0 + 0.3))
        ln.start, ln.end = ln.words[0].start, ln.words[-1].end
        placed += 1
    if placed:
        log(tr(f"  backing lines placed with their leads: {placed}",
               f"  бэк-строк поставлено к своим основным: {placed}"))
    return placed


def repair_ragged(lyrics: Lyrics, log: Log = _noop) -> int:
    """Re-lay the words of a line whose insides the model tore up.

    On a fast, dense vocal the model often places the LINE well and mangles
    the words in it: one word swallows two seconds, three others get nothing,
    a couple land out of order. Fixing that by hand, line after line, is the
    work a person gave this program to do. Where the insides are plainly
    torn — a word with no time at all, a word out of order, or one hogging
    the line — the words are re-laid by syllables inside the line's own span.
    The edges do not move; a line whose words look sane is not touched.
    """
    fixed = 0
    for ln in lyrics.lines:
        ws = ln.words
        if len(ws) < 2 or ln.start is None or ln.end is None:
            continue
        if any(w.start is None or w.end is None for w in ws):
            continue
        span = ln.end - ln.start
        if span <= 0.2:
            continue
        durs = sorted(max((w.end or 0) - (w.start or 0), 0.0) for w in ws)
        med = durs[len(durs) // 2]
        torn = (
            # a word left with no time of its own
            any((w.end - w.start) < 0.03 for w in ws)
            # words out of order
            or any(a.start > b.start + 0.01 for a, b in zip(ws, ws[1:]))
            # one word hogging the line while the others are starved to
            # slivers no one could sing. A held note is NOT this: there the
            # long word is long and its neighbours still breathe.
            or (med < 0.15 and durs[-1] > max(5 * med, 0.4 * span)
                and durs[-1] > 1.5)
        )
        if not torn:
            continue
        _spread(ws, ln.start, ln.end)
        fixed += 1
    if fixed:
        log(tr(f"  lines whose words the model tore up, re-laid by syllables: {fixed}",
               f"  строк с рваными словами переложено по слогам: {fixed}"))
    return fixed


def repair_order(lyrics: Lyrics, log: Log = _noop) -> int:
    """Pull overlapping lines apart: a line must not end past the start of the
    next one, or the highlight jumps around."""
    fixed = conflicts = 0
    lines = [ln for ln in lyrics.lines
             if ln.words and ln.start is not None and ln.end is not None]
    for a, b in zip(lines, lines[1:]):
        # Two voices singing at once is a duet, not a defect: the na-na-na
        # behind a lead line is MEANT to overlap it. Only lines of the same
        # voice may not lie on each other.
        if (a.voice or 1) != (b.voice or 1):
            continue
        if b.start < a.start:
            conflicts += 1        # lines are out of order — trimming makes no sense
            continue
        if a.end <= b.start:
            continue
        last_word_end = a.words[-1].end if a.words else a.start
        new_end = b.start - 0.05
        # trim only when it will not cut through words: never maim the timing
        if new_end >= max(a.start + 0.2, last_word_end):
            a.end = new_end
            fixed += 1
        else:
            conflicts += 1
    if fixed:
        log(tr(f"  overlapping lines pulled apart: {fixed}",
               f"  развёл наложившиеся строки: {fixed}"))
    if conflicts:
        log(tr(f"  NOTE: {conflicts} lines clash with their neighbours in time — "
               f"check them in the player, the timing there is unreliable",
               f"  ВНИМАНИЕ: {conflicts} строк конфликтуют с соседями по времени — "
               f"проверьте их в плеере, там разметка ненадёжна"))
    return fixed


def _fill_lines(lyrics: Lyrics, duration: float, min_word: float = 0.12) -> None:
    """Line bounds from the words, plus a sanity pass over the timings."""
    prev_end = 0.0
    for w in lyrics.words:
        if w.start is None:
            w.start = prev_end
        if w.end is None or w.end <= w.start:
            w.end = w.start + max(min_word, 0.16 * w.syllables)
        # Keep the word inside the track. Order matters: first clamp the start
        # so there is room for the minimum length, and only then the end —
        # otherwise stretching to min_word runs past the end of the song.
        w.start = min(max(w.start, 0.0), max(duration - min_word, 0.0))
        w.end = min(max(w.end, w.start + min_word), duration)
        if w.end <= w.start:
            w.end = min(w.start + min_word, duration)
        prev_end = w.end

    # A short word the aligner collapsed onto its neighbour: “A” and
    # “chilling” starting at the same instant. The article was sung just
    # before — give it that sliver back, walking backwards so a chain of
    # squeezed words unfolds one after another. Grabbing a word that occupies
    # no time is impossible in any editor.
    for ln in lyrics.lines:
        ws = ln.words
        for k in range(len(ws) - 1, 0, -1):
            w, nxt = ws[k - 1], ws[k]
            if w.start is not None and nxt.start is not None \
                    and nxt.start - w.start < 0.05:
                w.start = max(0.0, nxt.start - max(min_word, 0.07 * w.syllables))
                w.end = max(nxt.start, w.start + 0.02)

    for ln in lyrics.lines:
        if not ln.words:
            continue
        ln.start = ln.words[0].start
        ln.end = ln.words[-1].end


def align_anchored(lyrics: Lyrics, audio_path: str, duration: float,
                   model_name: str = "medium", language: str = "ru",
                   device: Optional[str] = None, log: Log = _noop,
                   isolated: bool = False, skip=None) -> Lyrics:
    """Align a song whose text carries a few times of its own.

    “[2:27] Remember this day” in the lyrics file says: this line is sung about
    here. It is not a timing — it is a peg. The song is aligned between pegs:
    each stretch of text is shown only the audio between its own two, so a line
    cannot wander into a vocalise three minutes away, which is the one thing
    the model does that no repair can undo.

    A line with no peg is timed as always, inside the stretch it belongs to.
    """
    try:
        import stable_whisper
        have_whisper = True
    except ImportError:
        have_whisper = False

    pegs = []
    for i, ln in enumerate(lyrics.lines):
        if ln.start is None:
            continue
        if pegs and ln.start <= pegs[-1][1]:
            # Later in the text, earlier in the song: one of the two is wrong,
            # and a window that runs backwards would swallow the song whole.
            log(tr(f"  line {i + 1} is pegged at {mmss(ln.start)}, before the peg "
                   f"above it — ignoring this one",
                   f"  строка {i + 1} привязана к {mmss(ln.start)} — раньше, чем "
                   f"привязка выше; эту пропускаю"))
            ln.start = None
            continue
        pegs.append((i, ln.start))
    if not pegs:
        return align_whisper(lyrics, audio_path, duration, model_name, language,
                             device, log, isolated=isolated, skip=skip)

    from . import models as M
    log(tr(f"The text carries {len(pegs)} times of its own — aligning between them",
           f"В тексте {len(pegs)} собственных времён — размечаю между ними"))
    model = None
    if have_whisper:
        log(M.load_note(model_name))
        model = stable_whisper.load_model(model_name, device=device)
    else:
        log(tr("  stable-ts is not installed — each stretch is laid out by loudness, "
               "but still inside its own pegs",
               "  stable-ts не установлен — каждый кусок разложу по громкости, "
               "но в пределах своих привязок"))

    # A peg opens a stretch; the one before the first peg is a stretch too.
    bounds = []
    if pegs[0][0] > 0:
        bounds.append((0, pegs[0][0] - 1, 0.0, pegs[0][1]))
    for k, (i, t) in enumerate(pegs):
        last = (pegs[k + 1][0] - 1) if k + 1 < len(pegs) else len(lyrics.lines) - 1
        end = pegs[k + 1][1] if k + 1 < len(pegs) else duration
        bounds.append((i, last, t, end))

    out: List = []
    for a, b, t0, t1 in bounds:
        piece = Lyrics(lines=lyrics.lines[a:b + 1])
        for ln in piece.lines:
            ln.start = ln.end = None
            for w in ln.words:
                w.start = w.end = None
        outside = ([(0.0, t0)] if t0 > 0.05 else []) + \
                  ([(t1, duration)] if t1 < duration - 0.05 else [])
        holes = spans((skip or []) + outside, duration)
        log(tr(f"  lines {a + 1}–{b + 1}, between {mmss(t0)} and {mmss(t1)}",
               f"  строки {a + 1}–{b + 1}, между {mmss(t0)} и {mmss(t1)}"))
        try:
            if not have_whisper:
                raise RuntimeError("no stable-ts")
            align_whisper(piece, audio_path, duration, model_name, language,
                          device, log, isolated=isolated, skip=holes, model=model)
        except Exception as e:
            log(tr(f"  this stretch would not align ({e}) — spread by loudness instead",
                   f"  этот кусок не разметился ({e}) — раскладываю по громкости"))
            align_energy(piece, audio_path, duration, log, skip=holes)
        out.extend(piece.lines)

    lyrics.lines = out
    lyrics.has_manual_times = False
    _fill_lines(lyrics, duration)
    repair_order(lyrics, log=log)
    repair_ragged(lyrics, log=log)
    return lyrics


def align(lyrics: Lyrics, audio_path: str, duration: float, engine: str = "auto",
          model_name: str = "medium", language: str = "ru",
          device: Optional[str] = None, log: Log = _noop,
          isolated: bool = False, skip=None) -> tuple:
    """Returns (lyrics, engine_used)."""
    timed = sum(1 for ln in lyrics.lines if ln.start is not None)
    if lyrics.has_manual_times and timed == len(lyrics.lines):
        log(tr("The text already has [mm:ss.dd] timings — skipping alignment.",
            "В тексте уже есть тайминги [мм:сс.дд] — выравнивание пропускаю."))
        _spread_manual(lyrics, duration)
        return lyrics, "manual"
    if lyrics.has_manual_times and engine in ("auto", "whisper"):
        # Some lines carry a time and some do not: those are pegs, not a
        # timing. align_anchored copes without stable-ts too — each stretch is
        # laid out by loudness, still inside its own pegs — so the import must
        # not stand between the pegs and their meaning.
        try:
            import stable_whisper  # noqa: F401
            label = "whisper"
        except ImportError:
            label = "energy"
        return align_anchored(lyrics, audio_path, duration, model_name, language,
                              device, log, isolated=isolated, skip=skip), label

    if engine in ("auto", "whisper"):
        try:
            import stable_whisper  # noqa: F401
        except ImportError:
            if engine == "whisper":
                raise SystemExit(tr(
                    "The whisper engine needs dependencies:\n"
                    "    pip install stable-ts\n"
                    "Or run with --align energy (no neural nets).",
                    "Движок whisper требует зависимостей:\n"
                    "    pip install stable-ts\n"
                    "Либо запустите с --align energy (без нейросетей)."))
            log(tr("stable-ts is not installed → using the loudness engine "
                   "(`pip install stable-ts` makes it more accurate).",
                   "stable-ts не установлен → использую энергетический движок "
                   "(точнее будет с `pip install stable-ts`)."))
            engine = "energy"
        else:
            try:
                return align_whisper(lyrics, audio_path, duration, model_name,
                                     language, device, log, isolated=isolated,
                                     skip=skip), "whisper"
            except Exception as e:
                if engine == "whisper":
                    raise
                log(tr(f"Whisper could not cope ({e}) → falling back to the loudness engine.",
                       f"Whisper не справился ({e}) → откатываюсь на энергетический движок."))
                engine = "energy"

    if engine == "none":
        _fill_lines(lyrics, duration)
        return lyrics, "none"

    return align_energy(lyrics, audio_path, duration, log, skip=skip), "energy"


def _spread_manual(lyrics: Lyrics, duration: float) -> None:
    """Line starts are known — spread the words inside each line by syllable."""
    lines = lyrics.lines
    for i, ln in enumerate(lines):
        start = ln.start if ln.start is not None else (lines[i - 1].end if i else 0.0)
        end = ln.end
        if end is None:
            nxt = lines[i + 1].start if i + 1 < len(lines) else None
            end = min(nxt, duration) if nxt else min(start + 0.45 * ln.syllables, duration)
        ln.start, ln.end = start, end
        total = ln.syllables
        acc = 0.0
        for w in ln.words:
            w.start = start + (end - start) * acc / total
            acc += w.syllables
            w.end = start + (end - start) * acc / total
    _fill_lines(lyrics, duration)
