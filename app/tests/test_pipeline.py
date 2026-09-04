#!/usr/bin/env python3
"""Self-check: makes a test “song” and runs the whole pipeline over it.

    python tests/test_pipeline.py

Нужен только ffmpeg. Нейросети не задействуются.
"""

import json
import math
import os
import re
import struct
import sys
import tempfile
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kstudio import align as A
from kstudio import audio as AU
from kstudio import build as B
from kstudio import lyrics as L

# 6 phrases of 2.6 s with pauses between them
PHRASES = [(2.0, 4.6), (5.0, 7.6), (8.0, 10.6), (11.0, 13.6), (16.0, 18.6), (19.0, 21.6)]
TEXT = """title: Тестовая песня
artist: Проверка Связи

[Куплет]
Раз два три четыре пять
Начинаем проверять
Как ложатся тут слова
Закружилась голова

[Припев]
Синий ветер над рекой
Забери меня с собой
"""

failures = []


def check(name, cond, extra=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f" — {extra}" if extra else ""))
    if not cond:
        failures.append(name)


def make_song(path, dur=26.0, sr=22050):
    """A vibrato tone where the phrases are, plus a quiet “instrumental”."""
    frames = bytearray()
    for i in range(int(sr * dur)):
        t = i / sr
        v = 0.06 * math.sin(2 * math.pi * 110 * t) + 0.04 * math.sin(2 * math.pi * 220 * t + 1)
        for a, b in PHRASES:
            if a <= t < b:
                f = 300 + 120 * math.sin(2 * math.pi * 0.9 * (t - a))
                env = min(1.0, (t - a) / 0.08, (b - t) / 0.12)
                v += 0.42 * env * math.sin(2 * math.pi * f * t)
        frames += struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32767))
    w = wave.open(path, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(bytes(frames)); w.close()


def shutil_rm(p):
    import shutil
    shutil.rmtree(p, ignore_errors=True)



def _voc_checks():
    """An official instrumental is almost never mixed like the song itself.

    Проверяем на собранной паре: одна и та же аранжировка, но у «официального»
    минуса другой уровень и другая эквализация. Одной громкостью такое не
    гасится — должно спасать выравнивание по частотам. И, наоборот, чужая
    аранжировка приниматься не должна.
    """
    import importlib.util
    import math
    import tempfile
    import wave
    try:
        import numpy as np
    except ImportError:
        check("numpy is here (no voice extraction without it)", False)
        return

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sp = importlib.util.spec_from_file_location("studio", os.path.join(here, "studio.py"))
    st = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(st)

    tmp = tempfile.mkdtemp(prefix="karaoke_voc_")
    sr = 44100
    t = np.arange(int(sr * 24.0)) / sr
    rng = np.random.default_rng(7)

    click = ((t * 4) % 1 < 0.02).astype(np.float32)
    band = (0.35 * np.sin(2 * np.pi * 82.4 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 2 * t))
            + 0.22 * np.sin(2 * np.pi * 220 * t) + 0.18 * np.sin(2 * np.pi * 329.6 * t)
            + 0.25 * click * rng.standard_normal(len(t))).astype(np.float32)
    voice = np.zeros_like(t, dtype=np.float32)
    for a, b in ((6.0, 11.0), (15.0, 20.0)):
        m = (t >= a) & (t < b)
        tt = t[m] - a
        voice[m] = (0.30 * np.sin(2 * np.pi * (196 + 18 * np.sin(2 * np.pi * 1.3 * tt)) * tt)
                    + 0.12 * np.sin(2 * np.pi * 392 * tt)).astype(np.float32)

    def other_master(x):
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(len(x), 1 / sr)
        g = 1.6 / (1 + (f / 180) ** 2) ** 0.5 + 0.5 + 0.9 * np.exp(-((f - 3000) / 2500) ** 2)
        return (0.8 * np.fft.irfft(X * g, n=len(x))).astype(np.float32)

    def wr(name, x):
        path = os.path.join(tmp, name)
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
        return path

    def rd(path):
        with wave.open(path, "rb") as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768

    def rms(x, spans):
        m = np.zeros(len(x), dtype=bool)
        for a, b in spans:
            m[int(a * sr):int(b * sr)] = True
        return float(np.sqrt((x[m] ** 2).mean()))

    p_mix = wr("mix.wav", band + voice)
    p_off = wr("official.wav", other_master(band))
    alien = (0.3 * np.sin(2 * np.pi * 147 * t) + 0.2 * np.sin(2 * np.pi * 311 * t)
             + 0.05 * rng.standard_normal(len(t))).astype(np.float32)
    p_alien = wr("alien.wav", alien)

    quiet = [{"start": 0.5, "end": 5.5}, {"start": 11.5, "end": 14.5},
             {"start": 20.5, "end": 23.5}]
    spans = [(q["start"], q["end"]) for q in quiet]
    silent = lambda m: None

    got = st.extract_vocals(p_mix, p_off, 0.0, quiet, tmp, silent)
    check("the voice was extracted though the instrumental is mixed differently", bool(got))
    if got:
        v = rd(got)
        n = min(len(v), len(voice))
        drop = 20 * math.log10(rms((band + voice)[:n], spans) / max(rms(v[:n], spans), 1e-9))
        check("the arrangement is suppressed by at least 20 dB", drop > 20, f"{drop:.1f} dB")
        sing = [(6.5, 10.5), (15.5, 19.5)]
        snr = 20 * math.log10(rms(voice[:n], sing) / max(rms(v[:n] - voice[:n], sing), 1e-9))
        check("and the voice itself is intact", snr > 15, f"{snr:.1f} dB")

    check("a foreign arrangement is refused",
          st.extract_vocals(p_mix, p_alien, 0.0, quiet, tmp, silent) is None)
    shutil_rm(tmp)


def main():
    # These checks are written against the Russian messages, and the language
    # now follows the system. Pin Russian; a check below looks at English.
    from kstudio import i18n
    i18n.set_lang("ru")

    print("Parsing the lyrics")
    lyr = L.parse(TEXT)
    check("6 lines", len(lyr.lines) == 6, f"got {len(lyr.lines)}")
    check("the meta fields", lyr.title == "Тестовая песня" and lyr.artist == "Проверка Связи")
    check("sections", [l.section for l in lyr.lines].count(None) == 4)
    check("the first line carries its section", lyr.lines[0].section == "Куплет")
    # for Russian the count is exact — by vowels
    check("syllables: 'четыре' = 3", L.count_syllables("четыре") == 3)
    check("syllables: 'ёж' = 1", L.count_syllables("ёж") == 1)
    check("syllables: 'закружилась' = 4", L.count_syllables("Закружилась") == 4)
    check("syllables: 'с' = 1", L.count_syllables("с") == 1)
    # for English it is a vowel-group heuristic; it lies on loanwords
    check("syllables: 'hello' = 2", L.count_syllables("hello") == 2)
    check("syllables: 'beautiful' = 3", L.count_syllables("beautiful") == 3)
    check("syllables: 'love' = 1 (silent -e)", L.count_syllables("love") == 1)
    # The endings that lie, and they are what a sung line trips over: an even
    # split gives “lit-tle” one beat and “walk-ed” two, both wrong.
    check("syllables: a consonant before -le makes a syllable",
          L.count_syllables("little") == 2 and L.count_syllables("people") == 2
          and L.count_syllables("table") == 2,
          f'little={L.count_syllables("little")} people={L.count_syllables("people")}')
    check("syllables: -ed is silent, except after t and d",
          L.count_syllables("walked") == 1 and L.count_syllables("danced") == 1
          and L.count_syllables("wanted") == 2 and L.count_syllables("agreed") == 2,
          f'walked={L.count_syllables("walked")} wanted={L.count_syllables("wanted")}')
    check("syllables: a plural -es does not add a beat to “makes”",
          L.count_syllables("makes") == 1 and L.count_syllables("houses") == 2
          and L.count_syllables("watches") == 2,
          f'makes={L.count_syllables("makes")} houses={L.count_syllables("houses")}')
    check("syllables: a long word still outweighs a short one",
          L.count_syllables("beautiful") > L.count_syllables("I") * 2)
    check("normalisation", L.normalize_token("«Всё!»") == "все")

    print("\nLines in brackets are backing vocals, not a heading")
    back = L.parse("""[Куплет]
Обычная строка
(а это бэк-вокал)
Припев (эхо) поётся
(ла-ла-ла)
(Припев)
Строка припева
(Chorus 2)
Ещё одна""")
    texts = [ln.text for ln in back.lines]
    check("lines in brackets were not dropped", "(а это бэк-вокал)" in texts, str(texts))
    check("and neither were the sung syllables", "(ла-ла-ла)" in texts)
    check("they are marked as backing vocals",
          [ln.backing for ln in back.lines if ln.text == "(ла-ла-ла)"] == [True])
    check("an ordinary line does not count as backing",
          [ln.backing for ln in back.lines if ln.text == "Обычная строка"] == [False])
    check("brackets inside a line break nothing",
          "Припев (эхо) поётся" in texts)
    check("(Припев) stayed a section heading",
          any(ln.section == "Припев" for ln in back.lines),
          str([ln.section for ln in back.lines]))
    check("(Chorus 2) is a heading too",
          any(ln.section == "Chorus 2" for ln in back.lines))
    check("[Куплет] is still a heading", back.lines[0].section == "Куплет")
    check("the backing flag reaches the player data",
          back.lines[1].to_json().get("backing") is True)
    check("backing counts as the second voice at once",
          back.lines[1].to_json().get("voice") == 2)
    check("an ordinary line is sung by the main voice",
          [ln.voice for ln in back.lines if ln.text == "Обычная строка"] == [1])

    print("\nThe language of the program's messages")
    from kstudio import i18n as _i18n, models as _M, sysinfo as _SI, build as _B
    _i18n.set_lang("en")
    check("the engine label is in English", _B.ENGINE_LABEL.get("energy", "?") ==
          "timing by loudness", _B.ENGINE_LABEL.get("energy", "?"))
    check("the model size in MB", _M.size_label("small") == "480 MB", _M.size_label("small"))
    check("the memory advice is in English",
          "Not enough memory" in _SI.memory_advice(6.0, 2.0),
          _SI.memory_advice(6.0, 2.0)[:40])
    check("no Cyrillic in the English output",
          not re.search("[А-Яа-яЁё]", _SI.memory_advice(6.0, 2.0) + _M.load_note("small")),
          _M.load_note("small"))
    _i18n.set_lang("ru")
    check("in Russian everything comes back", _B.ENGINE_LABEL.get("energy", "?") ==
          "разметка по энергии", _B.ENGINE_LABEL.get("energy", "?"))
    check("and the model size is in МБ again", _M.size_label("small") == "480 МБ",
          _M.size_label("small"))

    print("\nReadability of the chosen colours")
    from kstudio import build as _B
    check("black on white is the limit of contrast",
          round(_B.contrast("#000000", "#ffffff"), 1) == 21.0)
    _t, _fixed = _B.readable("#0a0b14", "#e8ebf5")
    check("a good pair is left alone", _t == "#e8ebf5" and not _fixed, _t)
    _t, _fixed = _B.readable("#fdf6e3", "#f5efdc")
    check("blending letters are corrected", _fixed and _B.contrast("#fdf6e3", _t) >= 4.5,
          f"{_t} → {_B.contrast('#fdf6e3', _t):.1f}")
    _t, _ = _B.readable("#101010", "#202020")
    check("on a dark background the letters lighten", _B.contrast("#101010", _t) >= 4.5,
          f"{_t} → {_B.contrast('#101010', _t):.1f}")
    check("garbage instead of a colour breaks nothing",
          _B.theme_colors(["не цвет", None])[0]["bg"] == "не цвет")

    print("\nMarks in the text: voice and repeats")
    from kstudio.lyrics import parse as _parse
    marked = _parse(
        "title: Проба\n\n[Куплет]\nОбычная строка\n2: Эту поёт второй\n"
        "(а это подпевка)\nПрипев x3\n[голос 2]\nТеперь всё вторым\n"
        "[голос 1]\nИ снова первым\nДва слова х2\nСтрока про x-files\n")
    texts = [l.text for l in marked.lines]
    voices = [l.voice for l in marked.lines]
    check("“2:” sets the voice of a line", voices[1] == 2 and texts[1] == "Эту поёт второй",
          f"{voices[1]} «{texts[1]}»")
    check("the mark itself did not reach the text", not any(t.startswith("2:") for t in texts),
          " | ".join(texts))
    check("backing is still the second voice", voices[2] == 2)
    check("“x3” expanded into three lines",
          texts.count("Припев") == 3, " | ".join(texts))
    check("the repeats take the voice from the switch", set(voices[3:6]) == {1}, str(voices[3:6]))
    check("[голос 2] switches the lines that follow", voices[6] == 2, str(voices[6]))
    check("[голос 1] switches back", voices[7] == 1, str(voices[7]))
    check("the section is not repeated along with the line",
          [l.section for l in marked.lines].count("Куплет") == 1,
          str([l.section for l in marked.lines]))
    check("the Russian “х2” is understood too", texts.count("Два слова") == 2, " | ".join(texts))
    check("“x-files” does not count as a repeat", "Строка про x-files" in texts,
          " | ".join(texts))
    lrc = _parse("[00:10.00] Строка x2\n[00:20.00] Другая\n")
    check("with manual timings repeats are left alone",
          [l.text for l in lrc.lines] == ["Строка x2", "Другая"],
          str([l.text for l in lrc.lines]))

    print("\nExtracting the voice against a foreign master")
    _voc_checks()

    print("\nStretches the original sings")
    import importlib.util as _iu0
    _here0 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _sp0 = _iu0.spec_from_file_location("video", os.path.join(_here0, "tools", "video.py"))
    _vid = _iu0.module_from_spec(_sp0); _sp0.loader.exec_module(_vid)
    pay = {"data": {"lines": [
        {"start": 1.0, "end": 3.0},
        {"start": 3.0, "end": 5.0, "keep": True},
        {"start": 5.1, "end": 7.0, "keep": True},   # рядом — это один кусок
        {"start": 20.0, "end": 22.0, "keep": True},
        {"start": 9.0, "end": 9.0, "keep": True},   # пустая — не кусок
    ]}}
    spans = _vid.keep_spans(pay)
    P0 = _vid.KEEP_PAD
    check("adjacent marked lines are glued into one stretch",
          spans == [(3.0 - P0, 7.0 + P0, 1.0), (20.0 - P0, 22.0 + P0, 1.0)],
          str(spans))
    check("a line with no length is not a stretch",
          all(b > a for a, b, _ in spans), str(spans))
    # …and stretches at different loudness are not glued: a full-voice line
    # and a sing-along one next to it keep their own levels.
    mixed = _vid.keep_spans({"data": {"lines": [
        {"start": 3.0, "end": 5.0, "keep": True},
        {"start": 5.1, "end": 7.0, "keep": True, "keepSoft": True}]}})
    check("a quiet keep is not glued to a loud one",
          [lv for _, _, lv in mixed] == [1.0, _vid.SOFT_KEEP], str(mixed))
    # The breath between two kept lines is kept with them — the ends of lines
    # are the model's guesses, and muting the guess chewed a held word in
    # half. Unless the singer's own line stands in the breath: that mute is
    # the whole point.
    breath = _vid.keep_spans({"data": {"lines": [
        {"start": 10.0, "end": 12.0, "keep": True, "words": [1]},
        {"start": 12.8, "end": 15.0, "keep": True, "words": [1]}]}})
    check("a breath between kept lines is kept with them",
          len(breath) == 1 and breath[0][0] < 10 and breath[0][1] > 15, breath)
    busy = _vid.keep_spans({"data": {"lines": [
        {"start": 10.0, "end": 12.0, "keep": True, "words": [1]},
        {"start": 12.1, "end": 12.7, "words": [1]},
        {"start": 12.8, "end": 15.0, "keep": True, "words": [1]}]}})
    check("but not across the singer's own line", len(busy) == 2, busy)
    # And the slack itself stops at the singer's words: kept voice bleeding
    # over their first word is the chew, mirrored.
    tight = _vid.keep_spans({"data": {"lines": [
        {"start": 8.0, "end": 9.9, "words": [1]},
        {"start": 10.0, "end": 12.0, "keep": True, "words": [1]},
        {"start": 12.1, "end": 13.0, "words": [1]}]}})
    check("the slack never reaches into the singer's own words",
          tight == [(9.9, 12.1, 1.0)], tight)
    check("without marks there are no stretches", _vid.keep_spans({"data": {"lines": [{"start": 0, "end": 2}]}}) == [])

    print("\nSettings: a colour is not a comment")
    import importlib.util as _iu
    import tempfile as _tf
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _sp = _iu.spec_from_file_location("auto", os.path.join(here, "tools", "auto.py"))
    _auto = _iu.module_from_spec(_sp); _sp.loader.exec_module(_auto)
    ini = os.path.join(_tf.mkdtemp(prefix="karaoke_ini_"), "settings.ini")
    open(ini, "w", encoding="utf-8").write(
        "# примечание целой строкой\n"
        "цвета = #4de1ff,#ff8ad1\n"
        "кодек = mp3   # а это уже примечание\n")
    _auto.SETTINGS = ini
    got = _auto.read_settings()
    check("the colours were read whole", got[got.index("--colors") + 1] == "#4de1ff,#ff8ad1",
          " ".join(got))
    check("a comment after the value is cut off",
          got[got.index("--codec") + 1] == "mp3", " ".join(got))

    print("\nEncodings of the lyrics file")
    # Notepad on a Russian Windows saves in ANSI and UTF-16 — without this the
    # program used to die with a baffling error for no visible reason
    sample = "Раз два\nтри четыре"
    for name, raw in (("UTF-8", sample.encode("utf-8")),
                      ("UTF-8 с BOM", sample.encode("utf-8-sig")),
                      ("cp1251 (ANSI)", sample.encode("cp1251")),
                      ("UTF-16", sample.encode("utf-16")),
                      ("UTF-16 BE", b"\xfe\xff" + sample.encode("utf-16-be"))):
        got = L.parse(L.decode_text(raw))
        check(f"{name} is read",
              len(got.lines) == 2 and got.lines[0].text == "Раз два",
              got.lines[0].text if got.lines else "пусто")

    print("\nMatching against the recognised text")
    # Whisper returns words with a leading space. Without trimming it not a
    # single token matches and the timing silently becomes an even blanket.
    check("a leading space is trimmed", L.normalize_token(" Раз") == "раз",
          repr(L.normalize_token(" Раз")))
    check("a non-breaking space too", L.normalize_token(" два ") == "два")

    src = L.parse("Раз два три\nчетыре пять")
    rec = [(" раз", 0.0, 0.4), (" два", 0.4, 0.8), (" три", 0.8, 1.4),
           (" четыре", 2.0, 2.6), (" пять", 2.6, 3.0)]
    rec = [(L.normalize_token(t), a, b) for t, a, b in rec]
    ratio = A._apply_recognized(src.words, rec)
    check("100 % of the words matched", ratio == 1.0, f"{ratio:.0%}")
    check("the times came from what was recognised",
          src.words[3].start == 2.0 and src.words[3].end == 2.6,
          f"{src.words[3].start}–{src.words[3].end}")

    other = L.parse("Совершенно другой текст песни")
    bad = A._apply_recognized(other.words, rec)
    check("a foreign text gives a low match rate", bad < 0.4, f"{bad:.0%}")

    # Whisper glues the pause before a phrase onto its first word
    long_first = L.parse("Раз два три")
    long_first.words[0].start, long_first.words[0].end = 0.0, 2.2
    for w, (a, b) in zip(long_first.words[1:], [(2.2, 2.5), (2.5, 2.8)]):
        w.start, w.end = a, b
    A._trim_leading_silence(long_first)
    check("the silence before the first word is trimmed",
          1.5 < long_first.words[0].start < 1.9, f"{long_first.words[0].start:.2f}s")

    held = L.parse("Раз два")
    held.words[0].start, held.words[0].end = 5.0, 5.9   # обычное слово, не трогаем
    held.words[1].start, held.words[1].end = 5.9, 6.2
    A._trim_leading_silence(held)
    check("a normal first word is left alone", held.words[0].start == 5.0)

    print("\nPutting drifted lines back together")
    # Whisper sometimes drops one word far from the rest of its line.
    # Inside a sung line there can be no multi-second gaps.
    broken = L.parse("Первая строка тут одна\nВторая строка потом")
    for w, (t, d) in zip(broken.lines[0].words,
                         [(150.2, 0.12), (165.8, 0.8), (166.6, 0.4), (167.0, 0.6)]):
        w.start, w.end = t, t + d
    broken.lines[0].start, broken.lines[0].end = 150.2, 167.6
    for w, (t, d) in zip(broken.lines[1].words,
                         [(152.8, 0.6), (153.4, 0.5), (154.0, 0.3)]):
        w.start, w.end = t, t + d
    broken.lines[1].start, broken.lines[1].end = 152.8, 154.3

    A.repair_lines(broken)
    A.repair_order(broken)
    ws = [w for ln in broken.lines for w in ln.words]
    gaps = [b.start - a.end for ln in broken.lines
            for a, b in zip(ln.words, ln.words[1:])]
    check("the gaps inside lines are gone", max(gaps) < 1.2, f"max {max(gaps):.2f}s")
    check("the cluster that fits the neighbours was chosen",
          abs(broken.lines[0].start - 150.2) < 0.01, f"{broken.lines[0].start:.2f}")
    check("the lines do not overlap",
          all(a.end <= b.start + 1e-9
              for a, b in zip(broken.lines, broken.lines[1:])))
    check("the words stayed in order",
          all(a.start <= b.start + 1e-9 for a, b in zip(ws, ws[1:])))
    check("the durations are positive", all(w.end > w.start for w in ws))

    # the repair must not touch sound timing
    healthy = L.parse("Раз два три\nчетыре пять")
    for w, (t, d) in zip(healthy.lines[0].words, [(1.0, .4), (1.4, .4), (1.8, .4)]):
        w.start, w.end = t, t + d
    healthy.lines[0].start, healthy.lines[0].end = 1.0, 2.2
    for w, (t, d) in zip(healthy.lines[1].words, [(3.0, .5), (3.5, .5)]):
        w.start, w.end = t, t + d
    healthy.lines[1].start, healthy.lines[1].end = 3.0, 4.0
    before = [(w.start, w.end) for w in healthy.words]
    A.repair_lines(healthy)
    A.repair_order(healthy)
    check("sound timing is left untouched",
          before == [(w.start, w.end) for w in healthy.words])

    print("\nLRC on the input")
    m = L.parse("[00:12.30]первая\n[01:05.50]вторая")
    check("the timings were recognised", m.has_manual_times)
    check("the line times", abs(m.lines[0].start - 12.3) < 1e-6 and abs(m.lines[1].start - 65.5) < 1e-6,
          f"{m.lines[0].start}, {m.lines[1].start}")

    tmp = tempfile.mkdtemp(prefix="karaoke_test_")
    song = os.path.join(tmp, "song.wav")
    print("\nGenerating the test audio…")
    make_song(song)

    try:
        AU.ffmpeg()
    except AU.AudioError as e:
        print(f"\nSkipping the audio checks: {e}")
        return 1 if failures else 0

    print("\nAlignment by loudness")
    dur = AU.duration(song)
    check("the length is 26 s", abs(dur - 26.0) < 0.2, f"{dur:.2f}")

    lyr = L.parse(TEXT)
    lyr, engine = A.align(lyr, song, dur, engine="energy")
    check("the energy engine", engine == "energy")

    worst = 0.0
    for ln, (want, _) in zip(lyr.lines, PHRASES):
        worst = max(worst, abs(ln.start - want))
        print(f"    “{ln.text[:26]:26}” {ln.start:6.2f}s  (expected {want:5.2f}s)")
    check("every line is within 0.4 s", worst < 0.4, f"worst deviation {worst:.2f}s")

    check("the words are in order",
          all(a.start <= b.start for a, b in zip(lyr.words, lyr.words[1:])))
    check("no word has zero length", all(w.end > w.start for w in lyr.words))
    check("everything is inside the track", all(0 <= w.start and w.end <= dur + 1e-6 for w in lyr.words))

    # The Whisper path differs from the loudness one in the order of steps: the
    # line bounds appear only from the words. Checked without the model itself —
    # ready word times are fed in, as Whisper would have returned them.
    print("\nThe order of steps on the Whisper path")
    wl = L.parse(TEXT)
    t = 2.0
    for line in wl.lines:
        for w in line.words:
            w.start, w.end = t, t + 0.3
            t += 0.35
        t += 0.6
    # this is exactly where it used to fail: the lines had no start/end yet
    A._trim_leading_silence(wl)
    A._fill_lines(wl, dur)
    A.repair_lines(wl)
    A.repair_order(wl)
    A._fill_lines(wl, dur)
    check("the line bounds were filled from the words",
          all(l.start is not None and l.end is not None for l in wl.lines))
    check("the lines are in order",
          all(a.start <= b.start for a, b in zip(wl.lines, wl.lines[1:])))
    check("the words are in order",
          all(a.start <= b.start + 1e-9 for a, b in zip(wl.words, wl.words[1:])))

    env, hop_env = AU.rms_envelope(song)

    print("\nBuilding the HTML")
    track = AU.encode(song, os.path.join(tmp, "a"), "mp3")
    html = os.path.join(tmp, "out.html")
    B.build_html(html, lyr, dur, {"mix": track}, engine, embed=True)
    body = open(html, encoding="utf-8").read()
    check("the file was built", os.path.getsize(html) > 50_000)
    check("the audio is embedded", "data:audio/mpeg;base64," in body)
    check("no external links", "http://" not in body and "https://" not in body)
    check("the template is filled in", "__PAYLOAD__" not in body and "__TITLE__" not in body)
    check("the lyrics are there", "Закружилась" in body)
    check("the syllables reached the player", '"s":' in body)

    lrc = os.path.join(tmp, "out.lrc")
    B.write_lrc(lrc, lyr)
    check("the LRC was written", open(lrc, encoding="utf-8").read().count("\n") >= 8)

    print("\nFeeding the timings back in")
    lyr2 = L.parse(TEXT)
    import json
    tj = os.path.join(tmp, "t.json")
    json.dump({"lines": [{"text": l.text, "start": l.start + 1.5, "end": l.end + 1.5,
                          "words": [{"w": w.text, "t": w.start + 1.5, "d": w.end - w.start}
                                    for w in l.words]} for l in lyr.lines]},
              open(tj, "w"), ensure_ascii=False)
    B.apply_timings(lyr2, tj)
    check("the shift was applied", abs(lyr2.lines[0].start - (lyr.lines[0].start + 1.5)) < 1e-6)

    print("\nHow precise the shift is when the instrumental is swapped")
    # The timing is moved along with the new track, so an error in finding the
    # shift is heard at once. The envelope step is 10 ms, the peak is refined
    # with a parabola.
    import importlib
    import subprocess as _sp
    _studio = importlib.import_module("studio")
    worst = 0.0
    for ms in (250, 507, 1503):
        moved = os.path.join(tmp, f"сдвиг{ms}.wav")
        _sp.run(["ffmpeg", "-y", "-loglevel", "error", "-i", song,
                 "-af", f"adelay={ms}|{ms}", moved], check=True)
        ea, ha = AU.rms_envelope(song, hop_ms=10)
        eb, _hb = AU.rms_envelope(moved, hop_ms=10)
        got = _studio.offset_between(ea, eb, ha) * 1000
        worst = max(worst, abs(got - ms))
        check(f"a shift of {ms} ms was found", abs(got - ms) < 8, f"got {got:.1f} ms")
    check("the worst error is under 8 ms", worst < 8, f"{worst:.1f} ms")
    check("on empty data the shift is zero", _studio.offset_between([], [], 0.01) == 0.0)

    print("\nThe “Check” panel: only real breakage, no matters of taste")
    from kstudio import project as PRJ
    long_note = {"lines": [{"text": "а-а-а", "start": 0.0, "end": 9.0,
                            "words": [{"w": "а-а-а", "t": 0.0, "d": 9.0, "s": 3}]}],
                 "envelope": {}}
    check("a long note does not count as an error", PRJ.problems(long_note) == [],
          str(PRJ.problems(long_note)))
    tail = {"lines": [{"text": "конец строки", "start": 0.0, "end": 6.0,
                       "words": [{"w": "конец", "t": 0.0, "d": 0.5, "s": 2},
                                 {"w": "строки", "t": 0.5, "d": 5.5, "s": 2}]}],
            "envelope": {}}
    check("a tail at the end of a line is not an error either", PRJ.problems(tail) == [],
          str(PRJ.problems(tail)))

    impossible = {"lines": [{"text": "очень много слогов подряд",
                             "start": 0.0, "end": 0.4,
                             "words": [{"w": "очень", "t": 0.0, "d": .1, "s": 2},
                                       {"w": "много", "t": 0.1, "d": .1, "s": 2},
                                       {"w": "слогов", "t": 0.2, "d": .1, "s": 2},
                                       {"w": "подряд", "t": 0.3, "d": .1, "s": 2}]}],
                  "envelope": {}}
    check("but the physically unsingable is", len(PRJ.problems(impossible)) == 1,
          str(PRJ.problems(impossible)))

    overlap = {"lines": [{"text": "первая", "start": 0.0, "end": 5.0,
                          "words": [{"w": "первая", "t": 0.0, "d": 5.0, "s": 3}]},
                         {"text": "вторая", "start": 3.0, "end": 6.0,
                          "words": [{"w": "вторая", "t": 3.0, "d": 3.0, "s": 3}]}],
               "envelope": {}}
    check("overlapping lines are still reported",
          any("налезает" in w for p2 in PRJ.problems(overlap) for w in p2["why"]),
          str(PRJ.problems(overlap)))

    torn = {"lines": [{"text": "слова врозь", "start": 0.0, "end": 6.0,
                       "words": [{"w": "слова", "t": 0.0, "d": 0.4, "s": 2},
                                 {"w": "врозь", "t": 5.0, "d": 1.0, "s": 1}]}],
            "envelope": {}}
    check("words drifted apart inside a line are reported",
          any("разъехались" in w for p2 in PRJ.problems(torn) for w in p2["why"]),
          str(PRJ.problems(torn)))

    print("\nThe report before building")
    from kstudio import report as REP

    def click_track(path, tempo, dur=24.0, sr=22050):
        """Even beats at a known tempo."""
        period, frames = 60.0 / tempo, bytearray()
        for i in range(int(sr * dur)):
            t = i / sr
            v = 0.03 * math.sin(2 * math.pi * 70 * t)
            d = t - round(t / period) * period
            if 0 <= d < 0.06:
                v += 0.8 * math.exp(-d * 60) * math.sin(2 * math.pi * 900 * t)
            frames += struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32767))
        w = wave.open(path, "wb")
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(bytes(frames)); w.close()

    # Plain autocorrelation confidently reports half the tempo — the fast
    # tempos are checked here, because that is where it showed.
    for tempo in (90, 120, 140, 175):
        p2 = os.path.join(tmp, f"click{tempo}.wav")
        click_track(p2, tempo)
        env2, hop2 = AU.rms_envelope(p2)
        got, conf = REP.bpm(env2, hop2)
        check(f"the tempo {tempo} bpm was found",
              got is not None and abs(got - tempo) < 3.5,
              f"got {got}")
        check(f"and the confidence at {tempo} is high", conf > 0.5, f"{conf}")

    check("no tempo is invented out of silence", REP.bpm([0.0] * 400, 0.02)[0] is None)

    # Where nobody sings for a while — intro, interlude, solo. For karaoke that
    # matters more than tempo: no line belongs there.
    gap_song = os.path.join(tmp, "с_проигрышем.wav")
    old_phrases = list(A.__dict__.get("_", []))    # ничего не трогаем, просто пишем свой файл
    import wave as _w
    with _w.open(gap_song, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(22050)
        buf = bytearray()
        for i in range(int(22050 * 30)):
            t2 = i / 22050
            v = 0.02 * math.sin(2 * math.pi * 80 * t2)          # тихий фон
            singing = t2 < 8 or t2 > 20                          # с 8 по 20 — проигрыш
            if singing:
                v += 0.5 * math.sin(2 * math.pi * 350 * t2)
            buf += struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32767))
        f.writeframes(bytes(buf))
    genv, ghop = AU.rms_envelope(gap_song)
    quiet = REP.quiet_stretches(genv, ghop)
    check("the long interlude was found", len(quiet) == 1, str(quiet))
    if quiet:
        check("and found where it actually is",
              abs(quiet[0]["start"] - 8) < 1.0 and abs(quiet[0]["end"] - 20) < 1.0,
              f"{quiet[0]['start']}–{quiet[0]['end']} вместо 8–20")
    check("short gaps between lines are not interludes",
          REP.quiet_stretches(env, hop_env) == [] or
          all(q["end"] - q["start"] >= 5 for q in REP.quiet_stretches(env, hop_env)),
          str(REP.quiet_stretches(env, hop_env)))
    check("an empty envelope does not crash it", REP.quiet_stretches([], 0.02) == [])

    grep = REP.build(gap_song, lyr, 30.0, genv, ghop, separate=False)
    check("the interlude reached the report", len(grep["audio"]["quiet"]) == 1,
          str(grep["audio"]["quiet"]))
    check("and it is spelled out in words",
          any("без пения" in n.lower() for n in grep["notes"]), str(grep["notes"]))
    check("the text report has it too",
          "Без пения" in REP.as_text(grep))
    check("an empty envelope does not crash it", REP.bpm([], 0.02) == (None, 0.0))

    rep = REP.build("песня.mp3", lyr, 26.0, env, hop_env,
                    model="small", separate=False, whisper=True, language="auto")
    check("the report has the length", rep["audio"]["duration"] == 26.0)
    check("the report has the text", rep["text"]["lines"] == 6 and rep["text"]["words"] == 21,
          str(rep["text"]))
    check("the sections are listed", rep["text"]["sections"] == ["Куплет", "Припев"],
          str(rep["text"]["sections"]))
    check("the language was detected and named", rep["language"]["code"] == "ru" and
          rep["language"]["auto"] is True)
    check("the time estimate is positive", rep["plan"]["seconds"] > 0)
    check("the estimate is honestly marked as rough", rep["plan"]["rough"] is True)
    check("the text form assembles", "Отчёт перед сборкой" in REP.as_text(rep))

    # The text belongs to another song: too few lines for a long recording
    short = L.parse("Одна одинокая строка")
    rep2 = REP.build("длинная.mp3", short, 300.0, env, hop_env, separate=False)
    check("few lines for a long song — the warning is there",
          any("повтор" in n or "много" in n for n in rep2["notes"]),
          str(rep2["notes"]))
    check("a bigger song is estimated to take longer",
          rep2["plan"]["seconds"] > rep["plan"]["seconds"])

    print("\nDetecting the language from the text")
    from kstudio import lang as LG
    songs = {
        "ru": "Раз два три четыре пять\nНачинаем проверять",
        "uk": "Ой у лузі червона калина\nПохилилася додолу",
        "en": "Yesterday all my troubles seemed so far away",
        "de": "Über den Wolken muss die Freiheit wohl grenzenlos sein",
        "fr": "Non, je ne regrette rien\nNi le bien qu'on m'a fait",
        "es": "Bésame, bésame mucho\nComo si fuera esta noche",
        "it": "Nel blu dipinto di blu\nfelice di stare lassù",
        "pl": "Hej, sokoły! Omijajcie góry, lasy, doły",
        "ja": "上を向いて歩こう",
        "ko": "아리랑 아리랑 아라리요",
        "zh": "月亮代表我的心",
    }
    for want, text in songs.items():
        got = LG.detect(text)
        check(f"{LG.label(want)} is recognised", got == want, f"detected as {got}")
    check("an empty text does not crash it", LG.detect("") == "en")
    check("punctuation only does not crash it", LG.detect("... !!! ???") in LG.NAMES)
    check("“auto” becomes the language of the text",
          LG.resolve("auto", songs["uk"]) == "uk")
    check("a language set by hand is not replaced",
          LG.resolve("en", songs["ru"]) == "en")
    check("every language has a human-readable name",
          all(LG.label(c) and LG.label(c) != c for c in LG.NAMES))
    # Telling the alphabets apart is the one judgement about a text that is
    # never a guess — it is what catches “English lyrics, Russian picked”.
    check("the alphabet of a text is told apart",
          LG.text_script(songs["en"]) == "lat" and LG.text_script(songs["ru"]) == "cyr"
          and LG.text_script(songs["ja"]) == "cjk" and LG.text_script("123 …") == "",
          LG.text_script(songs["en"]) + "/" + LG.text_script(songs["ru"]))
    check("and the alphabet of a language too",
          LG.script_of("ru") == "cyr" and LG.script_of("uk") == "cyr"
          and LG.script_of("en") == "lat" and LG.script_of("zh") == "cjk")

    print("\nWhat the aligner mutters is put in the log")
    # stable-ts says the single most useful thing through the warnings module,
    # and it scrolls past in a console window nobody is watching.
    import warnings as _w
    told = []
    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always")
        _w.warn("12/34 segments failed to align.", UserWarning)
    failed = A.report_warnings(caught, 34, told.append)
    check("the warning itself reaches the log",
          any("12/34" in m for m in told), " | ".join(told)[:80])
    check("and it is explained in plain words",
          any("не расслышал" in m for m in told), " | ".join(told)[-90:])
    check("the number of unplaced lines is read out", failed == 12, str(failed))
    check("silence is not reported as a problem",
          A.report_warnings([], 34, told.append) == 0)

    print("\nLines the aligner piled in one spot")
    # Straight from a real project: Bjork — Unravel, a quiet intro. Whisper found
    # nothing to hold on to and dropped seven lines at 0:16.7 and six more at
    # 0:39.2 — a fifth of a second for the lot. In the player the karaoke leapt
    # through half the lyrics in a blink.
    rows = [("While you are away", 16.24, 17.06), ("My heart comes undone", 16.74, 17.06),
            ("Slowly unravels", 16.74, 17.22), ("In a ball of yarn", 16.74, 16.90),
            ("The devil collects it", 16.74, 16.90), ("With a grin", 16.74, 16.90),
            ("Our love", 16.74, 16.90), ("In a ball of yarn", 38.00, 39.40),
            ("He'll never return it", 39.24, 39.40), ("So, when you come back", 39.24, 39.40),
            ("We'll have to make new love", 39.24, 39.40),
            ("While you are away", 39.24, 43.66), ("My heart comes undone", 45.20, 47.80),
            ("Slowly unravels", 48.84, 53.54), ("In a ball of yarn", 54.44, 56.84)]
    piled = L.parse("\n".join(t for t, _, _ in rows))
    for ln, (_, a_, b_) in zip(piled.lines, rows):
        A._spread(ln.words, a_, b_)
        ln.start, ln.end = a_, b_

    runs = A.pile_runs(piled.lines)
    check("a pile is seen as a run, not line by line", len(runs) == 2, str(runs))
    check("the first run is the seven lines at 0:16", runs[0] == (0, 6), str(runs[0]))
    check("a sound line is not called a pile",
          all(not (a_ <= 12 <= b_) for a_, b_ in runs), str(runs))
    check("the share of piled lines is counted", 0.6 < A.pile_share(piled) < 0.95,
          f"{A.pile_share(piled):.0%}")

    words_before = [w.text for w in piled.words]
    said = []
    # The singing starts at 0:11 — the pile must not be spread over the silence
    # before it, and must not touch the lines that are timed right.
    A.repair_piles(piled, 200.02, log=said.append, floor=11.0)
    first = piled.lines[:7]
    check("the pile was spread out", said and "7" in said[0], said[0] if said else "silence")
    check("it stops right before the next sound line",
          37.0 < first[-1].end <= 38.0 + 1e-6, f"{first[-1].end:.2f}")
    # A gap can be wordless — a breath, an intro, humming. Filling all of it
    # would claim as lyrics what is not sung, so the run keeps a sung pace and
    # leaves the rest of the gap alone.
    check("the wordless part of the gap is left free",
          first[0].start > 20.0, f"the pile starts at {first[0].start:.1f}, the gap opens at 11.0")
    check("and the pace is a sung one, not a smear",
          all(0.3 < (ln.end - ln.start) / (sum(w.syllables for w in ln.words) or 1) < 0.7
              for ln in first),
          f"{(first[0].end - first[0].start) / 5:.2f} s per syllable")
    check("every line got a singable length",
          all((ln.end - ln.start) / (sum(w.syllables for w in ln.words) or 1) > 0.07
              for ln in first),
          min(f"{(ln.end - ln.start):.2f}" for ln in first))
    check("the order of the lines is intact",
          all(b_.start >= a_.start for a_, b_ in zip(piled.lines, piled.lines[1:])))
    check("the words are still the same words", [w.text for w in piled.words] == words_before)
    check("the lines that were timed right are untouched",
          abs(piled.lines[12].start - 45.20) < 1e-9 and abs(piled.lines[13].start - 48.84) < 1e-9)
    # Its neighbours contradict each other — line 8 ends at 39.40 while line 12
    # starts at 39.24. Moving that pile would stack it on a line that IS right.
    check("a pile with nowhere to go is left alone, not forced",
          any(abs(piled.lines[i].start - 39.24) < 1e-9 for i in (8, 9, 10)))
    check("and it is still reported as a pile", A.pile_share(piled) > 0.1,
          f"{A.pile_share(piled):.0%}")

    # The words are sung twice, the second pass much later. Whisper laid BOTH
    # copies of the text on the first pass, so the early copy has no audio under
    # it and a whole stretch of singing has no text. Spreading that copy over the
    # music would be inventing a performance: it is left alone and explained.
    twice = L.parse("\n".join(
        ["While you are away", "My heart comes undone", "Slowly unravels",
         "In a ball of yarn", "The devil collects it", "With a grin", "Our love"] * 2))
    for i, ln in enumerate(twice.lines):
        a_, b_ = (16.74, 16.90 + i * 0.02) if i < 7 else (39.0 + (i - 7) * 6, 43.0 + (i - 7) * 6)
        A._spread(ln.words, a_, b_)
        ln.start, ln.end = a_, b_
    was = [(ln.start, ln.end) for ln in twice.lines]
    told = []
    A.repair_piles(twice, 200.0, log=told.append, floor=11.0, untexted=60.0)
    check("a repeated block is found in what is timed",
          A.duplicate_of(twice.lines, 0, 6) == (7, 13),
          str(A.duplicate_of(twice.lines, 0, 6)))
    check("text with no audio under it is not spread over the music",
          [(ln.start, ln.end) for ln in twice.lines] == was)
    check("and the reason given is the repetition, not a stray line",
          told and "повтор" in told[-1] and "60" in told[-1],
          told[-1][:90] if told else "silence")
    told2 = []
    A.repair_piles(twice, 200.0, log=told2.append, floor=11.0, untexted=0.0)
    check("with every second of singing covered, the answer is the other one",
          told2 and "выписана больше раз" in told2[-1],
          told2[-1][:90] if told2 else "silence")

    clean = L.parse("one two three\nfour five six\nseven eight nine")
    for i, ln in enumerate(clean.lines):
        A._spread(ln.words, 10.0 + i * 4, 13.0 + i * 4)
        ln.start, ln.end = 10.0 + i * 4, 13.0 + i * 4
    check("sound timing has no piles at all", A.pile_runs(clean.lines) == [],
          str(A.pile_runs(clean.lines)))
    check("and nothing is moved in it",
          A.repair_piles(clean, 100.0) == 0 and abs(clean.lines[0].start - 10.0) < 1e-9)

    print("\nA language picked by hand that the text contradicts")
    from kstudio import report as REP
    eng = L.parse("I walked alone tonight\nThe city lights are cold\n"
                  "You said you would wait for me\nBut all the words got old")
    def notes_for(language):
        return REP.build("s.mp3", eng, 120.0, [0.5] * 600, 0.2, model="small",
                         separate=False, whisper=True, language=language)["notes"]
    said = " ".join(notes_for("ru"))
    check("an English text with “русский” picked is called out",
          "не тем алфавитом" in said, said[-120:] if said else "no notes at all")
    check("and the note names what the text looks like", "english" in said)
    check("the right language raises no such note",
          "не тем алфавитом" not in " ".join(notes_for("en")))
    check("“detect from the text” raises no such note either",
          "не тем алфавитом" not in " ".join(notes_for("auto")))
    check("a Russian text with “русский” picked is left alone",
          "не тем алфавитом" not in " ".join(
              REP.build("s.mp3", L.parse(songs["ru"]), 120.0, [0.5] * 600, 0.2,
                        model="small", separate=False, whisper=True,
                        language="ru")["notes"]))

    print("\nThe window and the log agree about the models")
    import tempfile as _tf

    from kstudio import models as MM
    fake = _tf.mkdtemp(prefix="cache_")
    old_xdg = os.environ.get("XDG_CACHE_HOME")
    os.environ["XDG_CACHE_HOME"] = fake
    try:
        wd = MM.whisper_dir()
        os.makedirs(wd, exist_ok=True)
        check("the model is not there yet", MM.whisper_ready("medium") is False)
        check("a missing one is announced as “downloading”",
              MM.load_note("medium").startswith("Скачиваю") and
              "1,5 ГБ" in MM.load_note("medium"))
        check("and the step is called downloading", "скачивание" in MM.step_label("medium"))

        with open(os.path.join(wd, "medium.pt"), "wb") as f:
            f.write(b"0" * 2_000_000)
        check("the model on disk was found", MM.whisper_ready("medium") is True)
        check("a downloaded one is not promised as a download",
              "уже на диске" in MM.load_note("medium") and
              "Скачиваю" not in MM.load_note("medium"))
        check("and the step is called loading", "загрузка" in MM.step_label("medium"))

        # a half-downloaded stub must not count as a model
        with open(os.path.join(wd, "small.pt"), "wb") as f:
            f.write(b"0" * 1000)
        check("a half-downloaded file does not count as a model",
              MM.whisper_ready("small") is False)
        check("the list for the window matches what the log says",
              MM.whisper_all()["medium"] is True and
              MM.whisper_all()["small"] is False)
    finally:
        if old_xdg is None:
            os.environ.pop("XDG_CACHE_HOME", None)
        else:
            os.environ["XDG_CACHE_HOME"] = old_xdg
        shutil_rm(fake)

    print("\nStretches a person marked as holding no words")
    # A vocalise is voice: nothing measurable tells it from a sung line, so the
    # only source of truth is the person. Marking a stretch must keep words off
    # it — and must claim nothing about the rest of the song.
    check("a written span is read as one",
          A.spans("0:00-0:42, 3:10-3:50", 600) == [(0.0, 42.0), (190.0, 230.0)],
          A.spans("0:00-0:42, 3:10-3:50", 600))
    check("seconds, minutes and a dash all pass",
          A.spans("12-30", 600) == [(12.0, 30.0)]
          and A.spans("0:12–0:30", 600) == [(12.0, 30.0)])
    check("overlapping spans merge", A.spans([(10, 20), (15, 30)], 600) == [(10.0, 30.0)])
    check("nonsense is dropped, not guessed at", A.spans("который час", 600) == [])
    check("a span outside the song is clipped to it", A.spans("0-9999", 600) == [(0.0, 600.0)])
    check("what is left is the other side of it",
          A.keep_windows([(0.0, 42.0), (190.0, 230.0)], 600)
          == [(42.0, 190.0), (230.0, 600)])

    # …and the same thing written in the lyrics file itself
    marked = L.parse("первая строка тут\n[Соло 3:10-3:50]\nвторая строка тут\n"
                     "[нет текста 1:02–1:40]\nтретья строка тут")
    check("a heading with a time range marks a wordless stretch",
          A.spans(marked.skips, 600) == [(62.0, 100.0), (190.0, 230.0)],
          marked.skips)
    check("and it does not eat the lines around it", len(marked.lines) == 3)
    check("a heading keeps being a heading",
          marked.lines[1].section == "Соло", marked.lines[1].section)
    check("while “no text” is not shown as one",
          marked.lines[2].section in (None, ""), marked.lines[2].section)

    print("\nLines that lie where the voice is silent")
    # The aligner must put every word somewhere, and over an interlude it puts
    # them on the music: the line looks timed, and nobody sings. On the
    # separated vocal that stretch is real silence, so it can be known — and
    # where the voice is loud but wordless, the person's own mark says so.
    import wave as _wv

    def _tone_and_silence(path, spans, total=30.0, sr=8000):
        """A wav that is loud inside `spans` and silent elsewhere."""
        import math
        frames = bytearray()
        for i in range(int(total * sr)):
            t = i / sr
            loud = any(a <= t < b for a, b in spans)
            v = int(12000 * math.sin(2 * math.pi * 220 * t)) if loud else 0
            frames += int(v).to_bytes(2, "little", signed=True)
        with _wv.open(path, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sr)
            f.writeframes(bytes(frames))

    # Levelling the voice for the model: a screamed vocal swings from a shout
    # to a rasp, and the quiet half never reaches it. The one thing that must
    # never happen is a change in length — every timing would shift with it.
    steps = os.path.join(tmp, "loud-and-quiet.wav")
    import math as _math
    with _wv.open(steps, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        fr = bytearray()
        for i in range(8000 * 12):
            t = i / 8000
            amp = 12000 if t < 6 else 400          # a shout, then a rasp
            fr += int(amp * _math.sin(2 * _math.pi * 220 * t)).to_bytes(2, "little", signed=True)
        f.writeframes(bytes(fr))
    plain = AU.read_pcm_mono(steps, 16000)
    level = AU.read_pcm_mono(steps, 16000, af=AU.LEVEL_VOICE)
    check("levelling does not change the length by a sample",
          len(plain) == len(level), f"{len(plain)} vs {len(level)}")

    def _loudness(data, a, b):
        part = data[int(a * 16000):int(b * 16000)]
        return sum(abs(v) for v in part[::17]) / max(1, len(part[::17]))

    was = _loudness(plain, 7.0, 11.0) / max(1.0, _loudness(plain, 1.0, 5.0))
    now = _loudness(level, 7.0, 11.0) / max(1.0, _loudness(level, 1.0, 5.0))
    check("and the quiet half comes up towards the loud one", now > was * 3,
          f"{was:.3f} → {now:.3f}")

    # the loudness engine must not lay lines on a marked stretch
    tone = os.path.join(tmp, "vocalise.wav")
    _tone_and_silence(tone, [(0.0, 9.0), (12.0, 30.0)])
    lyr_e = L.parse("раз строка тут\nдва строка тут\nтри строка тут")
    A.align_energy(lyr_e, tone, 30.0, skip=[(0.0, 9.0)])
    check("the loudness engine keeps off the marked stretch",
          all(ln.start >= 8.5 for ln in lyr_e.lines),
          [round(ln.start, 1) for ln in lyr_e.lines])

    # singing at 0–8 s and 20–30 s; 8–20 s is a solo with no voice at all
    voiced_wav = os.path.join(tmp, "voiced.wav")
    _tone_and_silence(voiced_wav, [(0.0, 8.0), (20.0, 30.0)])

    # Silence, asked as a question that can be answered: is there any voice at
    # all? The panel's “quiet” is relative to the song's middle and says yes to
    # a whispered verse — which is singing, with words in it.
    quietish = os.path.join(tmp, "whispered.wav")
    with _wv.open(quietish, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(8000)
        fr = bytearray()
        import math as _m
        for i in range(8000 * 30):
            t = i / 8000
            amp = 12000 if t < 10 else (900 if t < 20 else 0)   # loud, whisper, nothing
            fr += int(amp * _m.sin(2 * _m.pi * 220 * t)).to_bytes(2, "little", signed=True)
        f.writeframes(bytes(fr))
    env_q, hop_q = AU.rms_envelope(quietish)
    silent = A.silent_spans(env_q, hop_q)
    covers = lambda spans, a, b: any(s["start"] <= a + 0.4 and s["end"] >= b - 0.4 for s in spans)
    check("real silence is found", covers(silent, 20.5, 29.5), silent)
    check("a whispered verse is not called silence", not covers(silent, 10.5, 19.5), silent)
    check("and neither is the loud part", not covers(silent, 0.5, 9.5), silent)

    from kstudio import report as R
    older = R.quiet_stretches(env_q, hop_q, least=2.5)
    check("which is what the old measure got wrong", covers(older, 10.5, 19.5), older)

    loud_all = os.path.join(tmp, "loud-all.wav")
    _tone_and_silence(loud_all, [(0.0, 30.0)])
    env_l, hop_l = AU.rms_envelope(loud_all)
    check("a song loud from end to end has no silence in it",
          A.silent_spans(env_l, hop_l) == [], A.silent_spans(env_l, hop_l))

    # a marked stretch counts as silence even where the voice is loud:
    # 0–8 s here is a vocalise, as loud as anything, with no words in it
    msgs4 = []
    lyr_v = L.parse("раз строка тут\nдва строка тут")
    for ln, (a, b) in zip(lyr_v.lines, [(2.0, 5.0), (22.0, 26.0)]):
        A._spread(ln.words, a, b)
        ln.start, ln.end = a, b
    moved4 = A.repair_silent(lyr_v, 30.0, voiced_wav, log=msgs4.append, skip=[(0.0, 8.0)])
    check("a line on a vocalise is moved off it",
          moved4 == 1 and lyr_v.lines[0].start >= 8.0,
          f"{lyr_v.lines[0].start:.1f}")
    check("and the line that was fine is left alone", lyr_v.lines[1].start == 22.0)

    # A song loud from end to end tells us nothing about where the voice is;
    # taking that as “all silent” would drag the whole text somewhere.
    loud = os.path.join(tmp, "wall.wav")
    _tone_and_silence(loud, [(0.0, 30.0)])
    lyr_w = L.parse("раз строка тут\nдва строка тут")
    for ln, (a, b) in zip(lyr_w.lines, [(2.0, 5.0), (20.0, 24.0)]):
        A._spread(ln.words, a, b)
        ln.start, ln.end = a, b
    check("a wall of sound moves nothing",
          A.repair_silent(lyr_w, 30.0, loud) == 0 and lyr_w.lines[0].start == 2.0)

    voiced_wav = os.path.join(tmp, "voiced.wav")
    # singing at 0–8 s and 20–30 s; 8–20 s is a solo with no voice at all
    _tone_and_silence(voiced_wav, [(0.0, 8.0), (20.0, 30.0)])

    def _timed_lyrics():
        lyr = L.parse("первая строка тут\nвторая строка тут\nтретья строка тут\n"
                      "четвёртая строка тут")
        times = [(1.0, 3.0), (4.0, 6.0), (11.0, 13.0), (25.0, 28.0)]
        for ln, (a, b) in zip(lyr.lines, times):
            A._spread(ln.words, a, b)
            ln.start, ln.end = a, b
        return lyr

    msgs = []
    lyr_s = _timed_lyrics()
    n = A.repair_silent(lyr_s, 30.0, voiced_wav, log=msgs.append)
    third = lyr_s.lines[2]
    check("the line on the solo is moved", n == 1, n)
    check("and it lands where the singing is",
          third.start >= 19.5 and third.end <= 25.5,
          f"{third.start:.1f}–{third.end:.1f}")
    check("its neighbours are not touched",
          lyr_s.lines[1].end == 6.0 and lyr_s.lines[3].start == 25.0)
    check("the order of lines survives",
          all(lyr_s.lines[k].start <= lyr_s.lines[k + 1].start for k in range(3)))
    check("and the log says what happened",
          any("перенес" in m or "moved" in m for m in msgs), msgs[:1])

    # nowhere to go: the neighbours press right against the silence, and every
    # second of singing between them is already spoken for
    msgs2 = []
    lyr_n = _timed_lyrics()
    lyr_n.lines[1].start, lyr_n.lines[1].end = 5.0, 8.0
    A._spread(lyr_n.lines[1].words, 5.0, 8.0)
    lyr_n.lines[2].start, lyr_n.lines[2].end = 11.0, 13.0
    lyr_n.lines[3].start, lyr_n.lines[3].end = 20.0, 23.0
    A._spread(lyr_n.lines[3].words, 20.0, 23.0)
    n2 = A.repair_silent(lyr_n, 30.0, voiced_wav, log=msgs2.append)
    check("with no singing to move to, the lines stay put",
          n2 == 0 and lyr_n.lines[2].start == 11.0, n2)
    check("and they are named out loud",
          any("ВНИМАНИЕ" in m or "NOTE" in m for m in msgs2), msgs2[:1])

    # lines that sit on singing are never dragged anywhere
    msgs3 = []
    lyr_ok = _timed_lyrics()
    lyr_ok.lines[2].start, lyr_ok.lines[2].end = 21.0, 23.0
    A._spread(lyr_ok.lines[2].words, 21.0, 23.0)
    check("lines on the singing are left alone",
          A.repair_silent(lyr_ok, 30.0, voiced_wav, log=msgs3.append) == 0
          and lyr_ok.lines[2].start == 21.0)

    print("\nA time written in the text is a peg, not a timing")
    # “[2:27] Remember this day” says: this line is sung about here. A line
    # cannot then wander into a vocalise three minutes away — the model is only
    # ever shown the stretch between two pegs.
    import types

    calls = []

    class _Result:
        segments = []

    class _Model:
        def align(self, audio, text, **kw):
            calls.append({"text": text, "len": len(audio) / 16000})
            return _Result()

    fake = types.ModuleType("stable_whisper")
    fake.load_model = lambda *a, **k: _Model()
    real_mod = sys.modules.get("stable_whisper")
    sys.modules["stable_whisper"] = fake
    try:
        pegged = L.parse("[0:02] раз строка тут\nдва строка тут\n"
                         "[0:16] три строка тут\nчетыре строка тут")
        check("the pegs are read, and the rest left open",
              [ln.start for ln in pegged.lines] == [2.0, None, 16.0, None],
              [ln.start for ln in pegged.lines])
        said = []
        A.align_anchored(pegged, song, 26.0, model_name="small", language="ru",
                         log=said.append)
        check("the song is aligned in as many stretches as there are pegs",
              len(calls) == 2, len(calls))
        check("each stretch gets its own lines and no others",
              calls[0]["text"].count("\n") == 1 and calls[1]["text"].count("\n") == 1,
              [c["text"].replace("\n", " | ") for c in calls])
        check("and hears only the audio between its pegs",
              all(c["len"] < 20 for c in calls), [round(c["len"], 1) for c in calls])
        check("the log says which lines went with which stretch",
              any("строки 1–2" in m for m in said), [m for m in said if "строки" in m][:2])
    finally:
        if real_mod is not None:
            sys.modules["stable_whisper"] = real_mod
        else:
            sys.modules.pop("stable_whisper", None)

    # Without stable-ts the pegs must still mean something: each stretch is
    # laid out by loudness, but inside its own pegs. They used to be dropped
    # on the floor the moment the import failed.
    hidden = sys.modules.get("stable_whisper")
    sys.modules["stable_whisper"] = None
    try:
        pegged2 = L.parse("[0:02] раз строка тут\nдва строка тут\n"
                          "[0:16] три строка тут\nчетыре строка тут")
        got2, engine2 = A.align(pegged2, song, 26.0, engine="auto")
        check("without stable-ts the engine is named honestly",
              engine2 == "energy", engine2)
        check("and the pegs still hold: the late lines start after theirs",
              all(ln.start >= 15.5 for ln in got2.lines[2:]),
              [round(ln.start, 1) for ln in got2.lines])
        check("while the early lines stay inside their own stretch",
              all(ln.end <= 16.5 for ln in got2.lines[:2]),
              [round(ln.end, 1) for ln in got2.lines[:2]])
    finally:
        if hidden is not None:
            sys.modules["stable_whisper"] = hidden
        else:
            sys.modules.pop("stable_whisper", None)

    # …and the window asks for the loudness engine BY NAME on every machine
    # without stable-ts. That was the one word the pegs did not survive: the
    # branch ran for “auto” and “whisper” only, so the people who most needed
    # their pegs were exactly the ones whose pegs were quietly dropped.
    pegged3 = L.parse("[0:02] раз строка тут\nдва строка тут\n"
                      "[0:16] три строка тут\nчетыре строка тут")
    said3 = []
    got3, engine3 = A.align(pegged3, song, 26.0, engine="energy",
                            log=said3.append)
    check("the loudness engine asked for by name still honours the pegs",
          any("собственных времён" in m or "times of its own" in m for m in said3),
          said3[:2])
    check("and it is still the loudness engine that ran", engine3 == "energy",
          engine3)
    check("the late lines start after their own peg",
          all(ln.start >= 15.5 for ln in got3.lines[2:]),
          [round(ln.start, 1) for ln in got3.lines])

    # A time on both sides — “[0:05-0:08.5]” — is not a peg but a placement:
    # somebody who has listened and written down where a line begins AND ends
    # does not want it improved upon. Hundredths are enough; thousandths were
    # never required.
    both = L.parse("[0:02-0:05.25] раз строка тут\nдва строка тут\n"
                   "[0:16] три строка тут\n[0:20] четыре строка тут")
    check("a written end survives the parsing",
          (both.lines[0].start, both.lines[0].end) == (2.0, 5.25),
          (both.lines[0].start, both.lines[0].end))
    check("and a line with no end of its own still has one filled in",
          both.lines[2].end == 20.0 and not both.lines[2].held,
          (both.lines[2].end, both.lines[2].held))
    check("an end before its own start is refused",
          L.parse("[0:40-0:39] строка тут").lines[0].end is None)
    # Somebody writing forty of these by hand leaves a space in one of them,
    # and a bracket that lands in the words instead of in the timing takes a
    # whole line out of the song without saying anything. It also drags the
    # line above it along: that one's end is then filled from the next timed
    # line, which is now much further away.
    loose = L.parse("[ 00:05-00:09.27 ] раз строка тут\n"
                    "[00:45.72 ] два строка тут\n[1:00] три строка тут")
    check("a space inside the brackets is forgiven",
          [ln.start for ln in loose.lines] == [5.0, 45.72, 60.0],
          [(ln.start, ln.text[:12]) for ln in loose.lines])
    check("and the line above keeps the end it should have",
          abs(loose.lines[0].end - 9.27) < 1e-9, loose.lines[0].end)
    said_b = []
    got_b, _ = A.align(both, song, 26.0, engine="energy", log=said_b.append)
    check("the placed line is where it was written, to the hundredth",
          abs(got_b.lines[0].start - 2.0) < 1e-6
          and abs(got_b.lines[0].end - 5.25) < 1e-6,
          (got_b.lines[0].start, got_b.lines[0].end))
    check("and the aligner is told so out loud",
          any("конец" in m or "end as well" in m for m in said_b), said_b[:3])
    check("what follows begins where the placed line ended, not where it began",
          got_b.lines[1].start >= 5.25 - 1e-6, got_b.lines[1].start)

    # A peg written out of order is refused with a word, not obeyed.
    disorder = L.parse("[0:16] раз строка тут\n[0:04] два строка тут\nтри строка тут")
    said_d = []
    sys.modules["stable_whisper"] = None
    try:
        A.align(disorder, song, 26.0, engine="auto", log=said_d.append)
    finally:
        if hidden is not None:
            sys.modules["stable_whisper"] = hidden
        else:
            sys.modules.pop("stable_whisper", None)
    check("a peg earlier than the one above it is dropped and named",
          any("пропускаю" in m or "ignoring" in m for m in said_d),
          [m for m in said_d if "привязан" in m or "pegged" in m][:1])

    # a text where EVERY line is timed is a timing, not pegs — unchanged
    everyone = L.parse("[0:02] раз строка тут\n[0:06] два строка тут")
    got, engine_used = A.align(everyone, song, 26.0, engine="energy")
    check("a fully timed text is still taken as it is", engine_used == "manual",
          engine_used)

    print("\nThe countdown waits for a real pause")
    # A five-second gap between lines is a breath, not an interlude, and a
    # countdown over it pulls the eye off the singing for nothing.
    ui = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "kstudio", "ui.js"), encoding="utf-8").read()
    m = re.search(r"const MIN_GAP = ([\d.]+)", ui)
    check("the studio waits ten seconds before counting down",
          m and float(m.group(1)) >= 10.0, m.group(1) if m else "not found")
    vid = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "tools", "video.py"), encoding="utf-8").read()
    m2 = re.search(r"if gap >= ([\d.]+):", vid)
    check("and the video says the same", m2 and float(m2.group(1)) >= 10.0,
          m2.group(1) if m2 else "not found")

    print("\nLines do not reach across a marked hole")
    # The aligner has to end a line somewhere, and next to a hole the nearest
    # thing it finds is the far side of the silence: five words then last a
    # minute and a half, and putting that right by hand means dragging an edge
    # across the whole emptiness.
    holes_here = [(10.0, 95.0)]

    def _line_at(text, a, b):
        lyr = L.parse(text)
        A._spread(lyr.lines[0].words, a, b)
        lyr.lines[0].start, lyr.lines[0].end = a, b
        return lyr

    over = _line_at("первая строка тут", 5.0, 95.0)
    check("a line running into a hole ends where the hole begins",
          A.clip_to_marks(over, holes_here) == 1
          and abs(over.lines[0].end - 10.0) < 0.05,
          f"{over.lines[0].start:.1f}–{over.lines[0].end:.1f}")
    check("and its words are inside what is left",
          over.lines[0].words[-1].end <= 10.05,
          over.lines[0].words[-1].end)

    after = _line_at("вторая строка тут", 20.0, 99.0)
    check("a line starting inside a hole begins where the hole ends",
          A.clip_to_marks(after, holes_here) == 1
          and abs(after.lines[0].start - 95.0) < 0.05,
          f"{after.lines[0].start:.1f}–{after.lines[0].end:.1f}")

    # A line stretched over the whole hole keeps whichever side is longer:
    # there is no telling which end the words really belong to, so the bigger
    # piece of real singing wins.
    across = _line_at("третья строка тут", 5.0, 99.0)      # 5 s before, 4 s after
    A.clip_to_marks(across, holes_here)
    check("a line spanning the whole hole keeps its longer half",
          abs(across.lines[0].start - 5.0) < 0.05 and abs(across.lines[0].end - 10.0) < 0.05,
          f"{across.lines[0].start:.1f}–{across.lines[0].end:.1f}")
    other_way = _line_at("третья строка тут", 8.0, 110.0)  # 2 s before, 15 s after
    A.clip_to_marks(other_way, holes_here)
    check("and the other way round when the longer half is on the other side",
          abs(other_way.lines[0].start - 95.0) < 0.05,
          f"{other_way.lines[0].start:.1f}–{other_way.lines[0].end:.1f}")

    inside = _line_at("четвёртая строка тут", 30.0, 40.0)
    check("a line wholly inside a hole is left for the moving to deal with",
          A.clip_to_marks(inside, holes_here) == 0
          and inside.lines[0].start == 30.0)

    clear = _line_at("пятая строка тут", 96.0, 98.0)
    check("a line clear of every hole is not touched",
          A.clip_to_marks(clear, holes_here) == 0 and clear.lines[0].end == 98.0)

    tiny = _line_at("шестая строка тут", 9.9, 60.0)
    A.clip_to_marks(tiny, holes_here)
    check("and a trim that would leave nothing usable is not made",
          tiny.lines[0].end > 10.5, f"{tiny.lines[0].start:.1f}–{tiny.lines[0].end:.1f}")

    print("\nA backing tail becomes a line of its own")
    # “Some girls try too hard (Na-na-na)”: the tail is another person singing,
    # usually at the same time. Left inside, the lead would be shown na-na-na
    # as their own words.
    party = L.parse("Лид поёт своё (на-на-на)\n"
                    "(на-на-на, на-на-на)\n"
                    "Скобки (внутри) строки остаются\n"
                    "Повтор в конце (x2)\n"
                    "Хвост-заголовок (Chorus)")
    texts = [(ln.text, ln.voice, ln.backing) for ln in party.lines]
    check("the tail split off as the second voice",
          ("Лид поёт своё", 1, False) in texts and ("(на-на-на)", 2, True) in texts,
          texts[:2])
    check("a whole-bracket line is the second voice as before",
          ("(на-на-на, на-на-на)", 2, True) in texts)
    check("brackets in the middle stay where they are",
          any(t == "Скобки (внутри) строки остаются" and v == 1 for t, v, _ in texts),
          [t for t, v, _ in texts])
    check("a repeat mark is a repeat, not a backing line",
          sum(1 for t, _, _ in texts if t == "Повтор в конце") == 2,
          [t for t, _, _ in texts])
    check("and a section name in the tail is not turned into singing",
          not any(t == "(Chorus)" for t, _, _ in texts),
          [t for t, _, _ in texts])

    print("\nA found text brings its own times along")
    # LRCLIB answers with “[02:27.10] Remember this day” for every line. Those
    # times used to be stripped off and the model left to rediscover them —
    # badly. They come through as pegs now: sparse, so the model still lays
    # out the words and a record from another master cannot bake in its drift.
    from kstudio import findlyrics as FL
    rec = {"syncedLyrics": "\n".join(
        [f"[00:{10 + i * 3:02d}.00] line {i + 1}" for i in range(6)]
        + ["[01:30.00]", "[01:35.00] after the long pause", "[01:38.00] and one more"])}
    pegged = FL.timed(rec)
    lyr_p = L.parse(pegged)
    pegs = [ln.start for ln in lyr_p.lines if ln.start is not None]
    check("every line of the record is kept", len(lyr_p.lines) == 8, len(lyr_p.lines))
    check("but only a few carry a time", 2 <= len(pegs) <= 4, pegs)
    check("the first line is one of them", lyr_p.lines[0].start == 10.0,
          lyr_p.lines[0].start)
    check("and so is the line after a long pause",
          any(abs(p - 95.0) < 0.01 for p in pegs), pegs)
    check("the times run forward", pegs == sorted(pegs), pegs)
    check("a record with no times gives none",
          FL.timed({"plainLyrics": "just words"}) == "")
    check("and the plain words are still the plain words",
          FL.plain(rec).splitlines()[0] == "line 1", FL.plain(rec)[:20])
    # Pegs are what makes the difference: with them the aligner works stretch
    # by stretch, and a line cannot wander across the whole song.
    check("a text with pegs is aligned between them, not spread by hand",
          lyr_p.has_manual_times and len(pegs) < len(lyr_p.lines),
          f"{len(pegs)} pegs on {len(lyr_p.lines)} lines")

    print("\nThe clip's cover becomes the backdrop, when asked")
    # From a link the cover rides along; with the checkbox on it stands behind
    # the lyrics — blurred and darkened — on the page and in the video alike.
    from PIL import Image as _Im

    from kstudio import build as BLD
    from kstudio import project as PRJ
    cover_src = os.path.join(tmp, "cover-src.jpg")
    _Im.new("RGB", (320, 180), (200, 30, 30)).save(cover_src, "JPEG")
    song_for_build = os.path.join(tmp, "for-build.wav")
    text_for_build = os.path.join(tmp, "for-build.txt")
    if not os.path.isfile(song_for_build):
        make_song(song_for_build)
        open(text_for_build, "w", encoding="utf-8").write(TEXT)

    with_cover = PRJ.create(song_for_build, text_for_build, os.path.join(tmp, "cov"),
                          align_engine="energy", separate=False,
                          cover=cover_src, cover_bg=True)
    rec_c = json.load(open(os.path.join(with_cover, "project.json"), encoding="utf-8"))
    check("the cover is copied into the song's folder",
          os.path.isfile(os.path.join(with_cover, "cover.jpg")))
    check("and the song remembers to stand on it",
          rec_c.get("cover") == "cover.jpg" and rec_c.get("coverBg") is True,
          (rec_c.get("cover"), rec_c.get("coverBg")))

    without = PRJ.create(song_for_build, text_for_build, os.path.join(tmp, "cov2"),
                       align_engine="energy", separate=False,
                       cover=cover_src, cover_bg=False)
    rec_n = json.load(open(os.path.join(without, "project.json"), encoding="utf-8"))
    check("without the tick the cover is kept but not used",
          rec_n.get("cover") == "cover.jpg" and rec_n.get("coverBg") is False,
          (rec_n.get("cover"), rec_n.get("coverBg")))

    page_c = os.path.join(tmp, "covered.html")
    lyr_c = L.parse(TEXT)
    A.align_energy(lyr_c, song_for_build, 26.0)
    BLD.build_html(page_c, lyr_c, 26.0, {"mix": (song_for_build, "audio/wav")},
                 "energy", embed=False, cover_path=cover_src)
    pay_c = BLD.read_payload(page_c)
    check("the page carries the cover as its own data",
          (pay_c.get("cover") or "").startswith("data:image"),
          (pay_c.get("cover") or "")[:24])
    plain_c = os.path.join(tmp, "plain.html")
    BLD.build_html(plain_c, lyr_c, 26.0, {"mix": (song_for_build, "audio/wav")},
                 "energy", embed=False)
    check("a page without one carries nothing",
          BLD.read_payload(plain_c).get("cover") == "")
    # How dark the backdrop is rides with the page: covers differ, and the
    # words must stay the brightest thing in the frame.
    check("the darkness default stands at 66",
          BLD.read_payload(plain_c).get("coverDark") == 66)
    dark_c = os.path.join(tmp, "dark.html")
    BLD.build_html(dark_c, lyr_c, 26.0, {"mix": (song_for_build, "audio/wav")},
                 "energy", embed=False, cover_path=cover_src, cover_dark=30)
    check("a chosen darkness rides along",
          BLD.read_payload(dark_c).get("coverDark") == 30)
    rec_d = PRJ.save_lines(with_cover, rec_c["lines"], cover_dark=150)
    check("the saved darkness is clamped, not trusted",
          rec_d.get("coverDark") == 95, rec_d.get("coverDark"))

    print("\nA word can be broken into syllables that nobody sees")
    # “ко=ло=ко=ла”: the pieces are timed one by one — a held note lights up
    # syllable by syllable — and the word reads whole on every screen.
    syl = L.parse("ко=ло=ко=ла звенят\nобычная строка\n(на-на-на)\n")
    first = syl.lines[0]
    check("the line reads without the marks", first.text == "колокола звенят",
          first.text)
    check("but its timing is in five pieces", len(first.words) == 5,
          [w.text for w in first.words])
    check("and the pieces after the first are glued",
          [w.glue for w in first.words] == [False, True, True, True, False],
          [w.glue for w in first.words])
    check("a real hyphen is left alone: it is a word, not a mark",
          syl.lines[2].words[0].text == "(на-на-на)", syl.lines[2].words[0].text)
    soft = L.parse("ко\u00adло\u00adко\u00adла\n")
    check("a soft hyphen splits the same way", len(soft.lines[0].words) == 4,
          [w.text for w in soft.lines[0].words])
    js = first.words[1].to_json()
    check("the glue rides in the saved record", js.get("g") is True, js)
    # …and it reaches the files that leave the house
    from kstudio import interop as IO2
    for i, w in enumerate(first.words):
        w.start, w.end = 1.0 + i * 0.5, 1.5 + i * 0.5
    first.start, first.end = 1.0, 3.5
    rec_syl = {"title": "T", "lines": [first.to_json()]}
    us_syl = IO2.ultrastar_text(rec_syl, "a.mp3")
    notes = [l for l in us_syl.splitlines() if l.startswith("F ")]
    check("UltraStar joins the syllables into one word",
          notes[0].endswith("ко") and notes[3].endswith("ла "), notes[:4])
    ass_syl = IO2.ass_text(rec_syl)
    check("and the subtitles do the same",
          "{\\k50}ко{\\k50}ло" in ass_syl,
          [l for l in ass_syl.splitlines() if l.startswith("Dialogue")])

    print("\nTorn words are re-laid; held notes are left alone")
    # A fast, dense vocal: the model places the LINE well and mangles the
    # words inside — one hogs seconds, the rest get slivers, some run out of
    # order. Fixing that by hand line after line is the program's job now.
    def _mkline(text, times):
        _l = L.parse(text)
        _ln = _l.lines[0]
        _ln.start, _ln.end = times[0][0], times[-1][1]
        for _w, (_a, _b) in zip(_ln.words, times):
            _w.start, _w.end = _a, _b
        return _l
    starved = _mkline("all the pigs are lined",
                      [(2.0, 2.02), (2.02, 2.04), (2.04, 2.06),
                       (2.06, 2.08), (2.08, 8.0)])
    check("a starved line is re-laid by syllables",
          A.repair_ragged(starved) == 1
          and all((w.end - w.start) > 0.5 for w in starved.lines[0].words),
          [round(w.end - w.start, 2) for w in starved.lines[0].words])
    check("its edges do not move",
          starved.lines[0].words[0].start == 2.0
          and abs(starved.lines[0].words[-1].end - 8.0) < 0.01)
    zero = _mkline("a chilling cold", [(1.0, 1.0), (1.0, 2.0), (2.0, 3.0)])
    check("a word with no time at all counts as torn", A.repair_ragged(zero) == 1)
    disorder = _mkline("out of order here", [(5.0, 5.4), (4.0, 4.4),
                                             (5.8, 6.2), (6.2, 6.6)])
    check("words out of order count as torn", A.repair_ragged(disorder) == 1)
    held = _mkline("гудят большие колокола", [(2.0, 2.5), (2.5, 3.0), (3.0, 12.0)])
    check("a held note is NOT torn: the long word stays long",
          A.repair_ragged(held) == 0
          and held.lines[0].words[-1].end - held.lines[0].words[-1].start > 8)
    sane = _mkline("perfectly ordinary words here", [(1.0, 1.5), (1.5, 2.1),
                                                     (2.1, 2.6), (2.6, 3.2)])
    check("a sane line is not touched", A.repair_ragged(sane) == 0)

    print("\nThe original's own lines live inside the marks")
    # An intro sung by the artist: its lines are marked “♪ Original” AND the
    # intro is a “no words here” stretch. The mark passes used to expel those
    # lines — and the kept voice went with them, so the intro fell silent.
    kl = L.parse("интро говорит оригинал\nа это поёт человек\n")
    kl.lines[0].start, kl.lines[0].end, kl.lines[0].keep = 1.0, 5.0, True
    for i, w in enumerate(kl.lines[0].words):
        w.start, w.end = 1.0 + i, 1.9 + i
    kl.lines[1].start, kl.lines[1].end = 8.0, 12.0
    for i, w in enumerate(kl.lines[1].words):
        w.start, w.end = 8.0 + i, 8.9 + i
    A.enforce_marks(kl, [(0.0, 6.0)], 24.0)
    A.clip_to_marks(kl, [(0.0, 6.0)])
    check("a kept line stays in the marked intro",
          kl.lines[0].start == 1.0 and kl.lines[0].end == 5.0,
          (kl.lines[0].start, kl.lines[0].end))
    check("while an ordinary line is still kept out",
          kl.lines[1].start >= 6.0, kl.lines[1].start)

    # And a re-timing must not hand the original's lines back to the singer:
    # the flag survives, like a lock — the fresh times stay the model's.
    old_lines = [{"text": "a", "keep": True, "keepSoft": True, "start": 1.0},
                 {"text": "b", "start": 8.0}]
    fresh_lines = [{"text": "a", "start": 1.2}, {"text": "b", "start": 8.1}]
    PRJ.keep_locked(old_lines, fresh_lines)
    check("the keep marks survive a re-timing",
          fresh_lines[0].get("keep") is True and fresh_lines[0].get("keepSoft") is True
          and fresh_lines[0]["start"] == 1.2, fresh_lines[0])
    check("and lines never marked stay unmarked",
          not fresh_lines[1].get("keep"), fresh_lines[1])

    print("\nThe timing speaks UltraStar and .ass")
    # Months of timing work should not be locked into one player: the same
    # record leaves as an UltraStar duet and as subtitles with the karaoke
    # sweep — and both say exactly what the editor saved.
    from kstudio import interop as IO
    duet_rec = {"title": "Forevermore", "artist": "Lorna Shore",
                "colors": ["#4de1ff", "#ff8ad1"],
                "lines": [
                    {"text": "first line", "start": 12.0, "end": 14.0, "voice": 1,
                     "words": [{"w": "first", "t": 12.0, "d": 0.8},
                               {"w": "line", "t": 13.0, "d": 1.0}]},
                    {"text": "(na-na)", "start": 13.5, "end": 15.0, "voice": 2,
                     "backing": True,
                     "words": [{"w": "(na-na)", "t": 13.5, "d": 1.5}]},
                    {"text": "second", "start": 20.0, "end": 21.0, "voice": 1,
                     "words": [{"w": "second", "t": 20.0, "d": 1.0}]}]}
    us = IO.ultrastar_text(duet_rec, "forevermore.mp3")
    check("the header names the song and its audio",
          "#TITLE:Forevermore" in us and "#MP3:forevermore.mp3" in us)
    check("the gap is the first word, in milliseconds", "#GAP:12000" in us, us[:120])
    check("two voices make a duet file", "P1" in us.split() and "P2" in us.split())
    notes = [l for l in us.splitlines() if l.startswith("F ")]
    check("every note is freestyle: no pitch is invented",
          notes and all(l.split()[3] == "0" for l in notes), notes[:2])
    check("the beats are fifty-millisecond ticks",
          notes[0].split()[1] == "0" and notes[1].split()[1] == "20",
          [l.split()[1] for l in notes])
    check("a note never runs into the word after it",
          int(notes[0].split()[1]) + int(notes[0].split()[2])
          <= int(notes[1].split()[1]))
    check("the file ends the way the games expect", us.rstrip().endswith("E"))
    lone = {"title": "Solo", "lines": duet_rec["lines"][:1]}
    check("one voice stays a plain file", "P1" not in IO.ultrastar_text(lone, "a.mp3"))
    try:
        IO.ultrastar_text({"title": "x", "lines": []}, "a.mp3")
        check("an empty song is refused, not written", False)
    except ValueError:
        check("an empty song is refused, not written", True)

    ass = IO.ass_text(duet_rec)
    check("the colours travel in the subtitle's own order",
          "&H00FFE14D" in ass and "&H00D18AFF" in ass, ass[:0])
    check("each word carries its karaoke tag",
          "{\k100}first" in ass and "{\k100}line" in ass,
          [l for l in ass.splitlines() if "first" in l])
    check("the sweep runs to the start of the next word, not the word's end",
          "{\k100}first" in ass)   # 12.0→13.0 s is 100 cs, though d is 0.8
    check("the second voice has a style of its own",
          any(l.startswith("Dialogue") and ",Voice2," in l for l in ass.splitlines()))
    check("the lines stand in the order they are sung",
          ass.index("first") < ass.index("(na-na)") < ass.index("second"))
    # A word carrying braces or a backslash would break every tag after it:
    # swapped for lookalikes, the singer reads the same thing.
    tricky = {"title": "T", "lines": [
        {"text": "x", "start": 1.0, "end": 2.0, "voice": 1,
         "words": [{"w": "{evil}\\tag", "t": 1.0, "d": 1.0}]}]}
    tricky_ass = IO.ass_text(tricky)
    # Words shuffled out of order in a mangled record would write beats that
    # run backwards — the singing games refuse such a file whole.
    shuffled = {"title": "T", "lines": [
        {"text": "x", "start": 1.0, "end": 3.0, "voice": 1,
         "words": [{"w": "б", "t": 2.0, "d": 0.4}, {"w": "а", "t": 1.0, "d": 0.5}]}]}
    us_sh = IO.ultrastar_text(shuffled, "a.mp3")
    sh_beats = [int(l.split()[1]) for l in us_sh.splitlines()
                if l.startswith(("F ", "- "))]
    check("shuffled words leave in the order they are sung",
          sh_beats == sorted(sh_beats), sh_beats)
    check("a word cannot smuggle subtitle tags in",
          "{evil}" not in tricky_ass and "\\tag" not in tricky_ass
          and "(evil)/tag" in tricky_ass,
          [l for l in tricky_ass.splitlines() if "evil" in l])

    print("\nA clip becomes a slideshow of covers")
    # Six frames spread across the clip: the video plays them as a slow
    # slideshow; a plain picture stays a single cover.
    import subprocess as _sp
    from kstudio import audio as _AU
    import studio as _ST
    clip_src = os.path.join(tmp, "cover-clip.mp4")
    _sp.run([_AU.ffmpeg(), "-y", "-v", "error", "-f", "lavfi",
             "-i", "testsrc2=s=160x90:d=20", "-pix_fmt", "yuv420p", clip_src],
            check=True)
    names = _ST.set_cover(with_cover, clip_src)
    check("a clip yields a set of covers", len(names) == _ST.COVER_SET_N, names)
    check("all of them landed on disk",
          all(os.path.isfile(os.path.join(with_cover, n)) for n in names))
    single = _ST.set_cover(with_cover, cover_src)
    check("a plain picture stays a single cover", single == ["cover.jpg"], single)
    check("and the set's spare frames are cleaned away",
          not [n for n in os.listdir(with_cover)
               if n.startswith("cover-") and n.endswith(".jpg")])
    # the payload carries the set for the video
    names = _ST.set_cover(with_cover, clip_src)
    covers_page = os.path.join(tmp, "covers.html")
    BLD.build_html(covers_page, lyr_c, 26.0, {"mix": (song_for_build, "audio/wav")},
                 "energy", embed=False, cover_path=cover_src,
                 cover_paths=[os.path.join(with_cover, n) for n in names])
    pay_cv = BLD.read_payload(covers_page)
    check("the covers ride into the payload as pictures",
          len(pay_cv.get("covers") or []) == _ST.COVER_SET_N
          and all(u.startswith("data:image") for u in pay_cv["covers"]),
          len(pay_cv.get("covers") or []))

    print("\nThe beat grid belongs to the song")
    # A tempo counted once should still be there tomorrow — and nonsense typed
    # into the field must not reach the record.
    import shutil as _sh
    grid_dir = os.path.join(tmp, "gridsong")
    _sh.copytree(with_cover, grid_dir)
    rec_g = PRJ.save_lines(grid_dir, json.load(
        open(os.path.join(grid_dir, "project.json"), encoding="utf-8"))["lines"],
        grid={"on": True, "bpm": 174.5, "beat0": 1.25, "sub": 4, "pulse": True})
    check("the grid is kept with the song",
          rec_g.get("grid") == {"on": True, "bpm": 174.5, "beat0": 1.25,
                                "sub": 4, "pulse": True},
          rec_g.get("grid"))
    rec_g2 = PRJ.save_lines(grid_dir, rec_g["lines"],
                            grid={"on": True, "bpm": 9000, "beat0": -5, "sub": 7})
    g2 = rec_g2.get("grid") or {}
    check("a tempo nobody can play is brought back into range",
          g2.get("bpm") == 300.0 and g2.get("beat0") == 0.0 and g2.get("sub") == 1,
          g2)
    check("and the pulse is a choice of its own, not part of the grid",
          g2.get("pulse") is False, g2.get("pulse"))

    print("\nA song travels in one file")
    # A project folder stands on its own but does not travel — not to another
    # computer, not into a backup. Packed and unpacked it is the same song.
    packed_dir = os.path.join(tmp, "packed")
    os.makedirs(packed_dir, exist_ok=True)
    # Two .mp4 files in the folder, and only one of them is the song's own: a
    # rendered clip is made again in one press, a backdrop could never be.
    open(os.path.join(with_cover, "backdrop.mp4"), "wb").write(b"clip bytes")
    open(os.path.join(with_cover, "Song_karaoke.mp4"), "wb").write(b"rendered")
    zip_path = PRJ.pack(with_cover, packed_dir)
    check("the song packs into one file", os.path.isfile(zip_path), zip_path)
    import zipfile
    inside = zipfile.ZipFile(zip_path).namelist()
    check("with the record and the sound in it",
          "project.json" in inside and any(n.startswith("mix") or n.startswith("instrumental")
                                           for n in inside), inside)
    check("and the cover it stands on", "cover.jpg" in inside, inside)
    check("the backdrop travels with it", "backdrop.mp4" in inside, inside)
    check("but a rendered clip does not — it weighs more than the song",
          "Song_karaoke.mp4" not in inside, inside)
    back_root = os.path.join(tmp, "unpacked")
    os.makedirs(back_root, exist_ok=True)
    back = PRJ.unpack(zip_path, back_root)
    rec_before = json.load(open(os.path.join(with_cover, "project.json"), encoding="utf-8"))
    rec_after = json.load(open(os.path.join(back, "project.json"), encoding="utf-8"))
    check("and comes back the same song",
          rec_after.get("title") == rec_before.get("title")
          and len(rec_after.get("lines") or []) == len(rec_before.get("lines") or []),
          f"{rec_after.get('title')} / {len(rec_after.get('lines') or [])} lines")
    check("with the sound beside it",
          any(n.endswith((".mp3", ".wav", ".m4a", ".ogg")) for n in os.listdir(back)),
          os.listdir(back))
    # A zip that claims to unpack into a disk's worth is not a song.
    import zipfile as ZF
    bomb = os.path.join(tmp, "bomb.karaoke.zip")
    with ZF.ZipFile(bomb, "w", ZF.ZIP_DEFLATED) as z:
        z.writestr("project.json", "{}")
    # an honest bomb is expensive to build — the claimed size is faked instead
    class FakeInfo:
        file_size = 3 * 1024 ** 3
    real_infolist = ZF.ZipFile.infolist
    ZF.ZipFile.infolist = lambda self: [FakeInfo()]
    try:
        PRJ.unpack(bomb, back_root)
        check("a zip claiming gigabytes is refused", False)
    except ValueError as e:
        check("a zip claiming gigabytes is refused", "MB" in str(e) or "МБ" in str(e),
              str(e)[:60])
    finally:
        ZF.ZipFile.infolist = real_infolist
    # a coverDark that is not a number must not fail the save it rides in
    rec_junk = PRJ.save_lines(with_cover, rec_c["lines"], cover_dark="no")
    check("garbage darkness is ignored, not fatal",
          rec_junk.get("coverDark") in (None, 30, 66, 95), rec_junk.get("coverDark"))

    print("\nThe aligner never hears the backing text")
    # Asked to place na-na-na BETWEEN the lead lines, a linear aligner drags
    # whole choruses into silence to make room. So it is not asked.
    import types as _t

    heard = {}

    class _R2:
        segments = []

    class _M2:
        def align(self, audio, text, **kw):
            heard["text"] = text
            return _R2()

    fake2 = _t.ModuleType("stable_whisper")
    fake2.load_model = lambda *a, **k: _M2()
    real2 = sys.modules.get("stable_whisper")
    sys.modules["stable_whisper"] = fake2
    try:
        withback = L.parse("Лид один тут\nЛид два тут (на-на-на)\n(на-на-на, на-на-на)")
        try:
            A.align_whisper(withback, song, 26.0, model_name="small", language="ru")
        except Exception:
            pass                          # the fake returns no words; the text is the point
    finally:
        if real2 is not None:
            sys.modules["stable_whisper"] = real2
        else:
            sys.modules.pop("stable_whisper", None)
    check("the model hears the lead lines alone",
          "на-на-на" not in heard.get("text", "на-на-на"), heard.get("text"))
    check("and hears both of them", heard.get("text", "").count("\n") == 1,
          heard.get("text"))

    # the loudness engine keeps its phrases for the lead too
    eb = L.parse("Лид один тут\n(на-на-на, на-на-на)\nЛид два тут")
    A.align_energy(eb, song, 26.0)
    mains_eb = [ln for ln in eb.lines if not ln.backing]
    back_eb = next(ln for ln in eb.lines if ln.backing)
    check("the lead lines take the sung phrases",
          all(ln.start is not None and ln.end - ln.start > 0.3 for ln in mains_eb),
          [(round(ln.start, 1), round(ln.end, 1)) for ln in mains_eb])
    check("and the backing sits against its lead, not on a phrase of its own",
          abs(back_eb.start - mains_eb[0].end) < 0.6 or back_eb.start >= mains_eb[0].start,
          f"{back_eb.start:.1f} vs lead end {mains_eb[0].end:.1f}")

    print("\nBacking lands with its lead, not where the model scattered it")
    # The aligner is linear: it hunts the na-na-na BETWEEN the lead lines while
    # the record sings it OVER them — so the leads come out right and the
    # backing lands anywhere. Placement is a rule, not a guess.
    pb = L.parse("Лид номер один тут\nЛид номер два тут (на-на-на)\n"
                 "(на-на-на, на-на-на)\nЛид номер три тут")
    mains = [ln for ln in pb.lines if not ln.backing]
    for ln, (a, b) in zip(mains, [(10.0, 13.0), (15.0, 18.0), (26.0, 29.0)]):
        A._spread(ln.words, a, b)
        ln.start, ln.end = a, b
    # the model's scattered guesses for the backing
    for ln in pb.lines:
        if ln.backing:
            A._spread(ln.words, 2.0, 3.0)
            ln.start, ln.end = 2.0, 3.0
    said_pb = []
    n_pb = A.place_backing(pb, 30.0, log=said_pb.append)
    tail_ln = next(ln for ln in pb.lines if ln.tail)
    solo_ln = next(ln for ln in pb.lines if ln.backing and not ln.tail)
    check("both backing lines were placed", n_pb == 2, n_pb)
    check("the split-off tail lies over its lead — a duet",
          abs(tail_ln.start - 15.0) < 0.05 and abs(tail_ln.end - 18.0) < 0.3,
          f"{tail_ln.start:.1f}–{tail_ln.end:.1f}")
    check("the standalone backing takes the gap after its lead",
          solo_ln.start >= 17.9 and solo_ln.end <= 26.1,
          f"{solo_ln.start:.1f}–{solo_ln.end:.1f}")
    check("the leads themselves are untouched",
          mains[1].start == 15.0 and mains[2].start == 26.0)
    check("and the log says what happened",
          any("бэк-строк" in m or "backing lines" in m for m in said_pb), said_pb)

    lonely = L.parse("(на-на-на)\nЛид после бэка")
    check("a backing line with no lead above it is left to the model",
          A.place_backing(lonely, 30.0) == 0)

    print("\nA duet is not a defect")
    # Blink-182, “The Party Song”: na-na-na behind the lead, two texts at once.
    # The overlap is the point — only same-voice overlaps are trouble.
    duet = L.parse("главная строка тут\n(на на на)\nвторая главная тут")
    for ln, (a, b) in zip(duet.lines, [(10.0, 14.0), (10.5, 13.5), (14.5, 18.0)]):
        A._spread(ln.words, a, b)
        ln.start, ln.end = a, b
    check("the brackets made it the second voice", duet.lines[1].voice == 2,
          duet.lines[1].voice)
    said_d2 = []
    A.repair_order(duet, log=said_d2.append)
    check("the backing line is not pulled off the lead",
          duet.lines[1].start == 10.5 and duet.lines[0].end == 14.0,
          f"{duet.lines[0].end} / {duet.lines[1].start}")
    check("and nobody calls it a conflict", not said_d2, said_d2)

    same_v = L.parse("раз строка тут\nдва строка тут")
    A._spread(same_v.lines[0].words, 10.0, 11.8)     # words end early: a legal trim
    same_v.lines[0].start, same_v.lines[0].end = 10.0, 14.0
    A._spread(same_v.lines[1].words, 12.0, 16.0)
    same_v.lines[1].start, same_v.lines[1].end = 12.0, 16.0
    A.repair_order(same_v)
    check("same-voice overlap is still pulled apart",
          same_v.lines[0].end <= 12.0, same_v.lines[0].end)

    from kstudio import project as PJ3
    duet_lines = [
        {"text": "главная", "start": 10.0, "end": 14.0, "voice": 1,
         "words": [{"w": "главная", "t": 10.0, "d": 4.0, "s": 3}]},
        {"text": "(на на на)", "start": 10.5, "end": 13.5, "voice": 2,
         "words": [{"w": "на", "t": 10.5, "d": 3.0, "s": 1}]},
        {"text": "хвост", "start": 13.0, "end": 15.0, "voice": 1,
         "words": [{"w": "хвост", "t": 13.0, "d": 2.0, "s": 1}]},
    ]
    flagged2 = PJ3.problems({"lines": duet_lines})
    kinds_flat = [k for p2 in flagged2 for k in p2.get("kinds", [])]
    check("the Check panel does not flag the duet",
          "overlap" not in kinds_flat or all(
              p2["text"] != "(на на на)" for p2 in flagged2
              if "overlap" in p2.get("kinds", [])),
          [(p2["text"], p2.get("kinds")) for p2 in flagged2])

    print("\nA dismissed warning stays dismissed")
    # “Ignore”, the way a spell-checker has it. The key is the line's words,
    # not its number: numbers shift when lines are split or joined.
    from kstudio import project as PJ2

    def _slow_line(i, text):
        return {"text": text, "start": i * 5.0, "end": i * 5.0 + 0.2, "sure": None,
                "words": [{"w": w, "t": i * 5.0, "d": 0.05, "s": 3}
                          for w in text.split()]}

    noisy = {"lines": [_slow_line(0, "быстрая строка тут"),
                       _slow_line(1, "другая строка тут")]}
    before_p = PJ2.problems(noisy)
    check("both lines are flagged, with the kind named",
          len(before_p) == 2 and all("fast" in p.get("kinds", []) for p in before_p),
          [(p["line"], p.get("kinds")) for p in before_p])
    noisy["checkOff"] = ["быстрая строка тут|fast"]
    after_p = PJ2.problems(noisy)
    check("the dismissed line is quiet, the other still speaks",
          len(after_p) == 1 and after_p[0]["line"] == 1,
          [(p["line"], p["why"]) for p in after_p])
    # the line moved to another number — the dismissal follows the words
    moved_l = {"lines": [_slow_line(0, "другая строка тут"),
                         _slow_line(1, "быстрая строка тут")],
               "checkOff": ["быстрая строка тут|fast"]}
    moved_p = PJ2.problems(moved_l)
    check("the dismissal follows the words, not the number",
          len(moved_p) == 1 and moved_p[0]["text"] == "другая строка тут",
          [(p["line"], p["text"]) for p in moved_p])
    check("and an emptied list brings every warning back",
          len(PJ2.problems(dict(noisy, checkOff=[]))) == 2)

    print("\nA squeezed article gets its sliver of time back")
    # The aligner collapses a short word onto its neighbour: “A” and “chilling”
    # start at the same instant, the article occupies no time, and no editor
    # can grab what has no span.
    art = L.parse("a chilling cold")
    ws = art.lines[0].words
    ws[0].start, ws[0].end = 5.0, 5.0
    ws[1].start, ws[1].end = 5.0, 5.6
    ws[2].start, ws[2].end = 5.6, 6.4
    A._fill_lines(art, 30.0)
    check("the article starts before its neighbour now",
          ws[0].start < ws[1].start - 0.04,
          f"{ws[0].start:.2f} vs {ws[1].start:.2f}")
    check("and occupies real time", ws[0].end - ws[0].start >= 0.05,
          f"{ws[0].end - ws[0].start:.2f}")
    check("the neighbour did not move", abs(ws[1].start - 5.0) < 0.01, ws[1].start)
    check("and the line begins where the article does",
          abs(art.lines[0].start - ws[0].start) < 0.01, art.lines[0].start)

    # a chain of squeezed words unfolds one after another
    chain = L.parse("а и вот строка")
    cw = chain.lines[0].words
    for w in cw:
        w.start, w.end = 8.0, 8.0
    cw[-1].end = 9.0
    A._fill_lines(chain, 30.0)
    check("a chain of them unfolds in order",
          all(cw[k].start < cw[k + 1].start for k in range(len(cw) - 1)),
          [round(w.start, 2) for w in cw])
    check("without leaving the track", cw[0].start >= 0.0, cw[0].start)

    print("\nThe marks win even when there is no room")
    # The gentler passes leave a run inside a hole when the neighbours press
    # right against it. But the marks are the person's own words: better a
    # cramped line in the right place than words over the marked stretch.
    hole_m = [(10.0, 20.0)]

    def _three(next_at):
        lyr = L.parse("до строка тут\nвнутри строка тут\nпосле строка тут")
        for ln, (a, b) in zip(lyr.lines, [(8.0, 9.9), (12.0, 14.0), (next_at, next_at + 1.0)]):
            A._spread(ln.words, a, b)
            ln.start, ln.end = a, b
        return lyr

    said_e = []
    tight = _three(20.05)                 # no room anywhere between the neighbours
    A.enforce_marks(tight, hole_m, 30.0, log=said_e.append)
    mid = tight.lines[1]
    check("the run leaves the hole even with nowhere to go",
          mid.start >= 19.95, f"{mid.start:.2f}–{mid.end:.2f}")
    check("and the cramp is said out loud",
          any("ВНИМАНИЕ" in m or "NOTE" in m for m in said_e), said_e[-1:])

    # …but “cramped” must still mean a line somebody can read. Four lines
    # dropped in a marked intro with the next one pressing right against it
    # used to come out at a tenth of a second apiece — not a tight line, the
    # very pile the module refuses to leave standing anywhere else. The floor
    # is the module's own: the least these syllables can honestly be sung in.
    pile = L.parse("первая строка этой песни\nвторая строка этой песни\n"
                   "третья строка этой песни\nчетвёртая строка этой песни\n"
                   "пятая строка звучит потом")
    for ln, (a, b) in zip(pile.lines, [(2.0, 5.0), (5.0, 8.0), (8.0, 11.0),
                                       (11.0, 14.0), (20.6, 24.6)]):
        A._spread(ln.words, a, b)
        ln.start, ln.end = a, b
    A.enforce_marks(pile, [(0.0, 20.0)], 60.0, log=lambda m: None)
    short = [(k + 1, round(ln.end - ln.start, 2))
             for k, ln in enumerate(pile.lines)
             # a hundredth of slack: the floor is a design minimum shared out
             # by syllable count, not a bit-exact bound
             if ln.end - ln.start < A._MIN_PER_SYLLABLE * A._syl(ln) - 0.01]
    check("a run with no room is still given time its syllables can be sung in",
          not short, short)
    clash = [(k + 1, round(pile.lines[k - 1].end - ln.start, 2))
             for k, ln in enumerate(pile.lines)
             if k and ln.start < pile.lines[k - 1].end - 1e-6]
    check("and no line of it lands on top of the one before",
          not clash, clash)
    check("nothing was pushed onto the marked stretch to do it",
          all(ln.start >= 19.95 for ln in pile.lines),
          [round(ln.start, 2) for ln in pile.lines])

    roomy = _three(26.0)                  # singing after the hole has room
    said_r = []
    A.enforce_marks(roomy, hole_m, 30.0, log=said_r.append)
    mid2 = roomy.lines[1]
    check("with room, the run lands on the singing at a sung pace",
          mid2.start >= 20.0 and mid2.end <= 26.0, f"{mid2.start:.2f}–{mid2.end:.2f}")
    check("and nothing is called cramped",
          not any("ВНИМАНИЕ" in m or "NOTE" in m for m in said_r), said_r)

    # the case the trimming used to drop: a line starting a hair before the
    # hole, ending deep inside — too little left to trim, so it stayed
    straddle = _three(26.0)
    straddle.lines[1].start, straddle.lines[1].end = 9.9, 15.0
    A._spread(straddle.lines[1].words, 9.9, 15.0)
    A.enforce_marks(straddle, hole_m, 30.0)
    sl = straddle.lines[1]
    check("a line straddling the hole's edge is out of it too",
          min(sl.end, 20.0) - max(sl.start, 10.0) <= 0.05, f"{sl.start:.2f}–{sl.end:.2f}")

    check("a song with no marks is not touched",
          A.enforce_marks(_three(26.0), [], 30.0) == 0)

    print("\nA vocalise is heard, not muted")
    # “♪ Original” keeps the recorded voice on a line — but a vocalise has no
    # lines at all, so there was nothing to put the mark on, and the karaoke
    # came out with a hole where the song is at its loudest.
    from kstudio import project as P
    from kstudio import project as PP

    built_root = os.path.join(tmp, "built")
    song_for_build = os.path.join(tmp, "for-build.wav")
    text_for_build = os.path.join(tmp, "for-build.txt")
    if not os.path.isfile(song_for_build):
        make_song(song_for_build)
        open(text_for_build, "w", encoding="utf-8").write(TEXT)

    marked_song = {"duration": 300.0, "noText": "0:10-0:40, 3:00-3:20"}
    check("a marked stretch keeps the original voice",
          PP.keep_spans(marked_song) == [[10.0, 40.0], [180.0, 200.0]],
          PP.keep_spans(marked_song))
    check("unless the person means to sing it themselves",
          PP.keep_spans(dict(marked_song, keepMarks=False)) == [])
    check("with no marks there is nothing to keep",
          PP.keep_spans({"duration": 300.0}) == [])
    check("and a mark past the end of the song is clipped to it",
          PP.keep_spans({"duration": 30.0, "noText": "0:10-9:99"}) == [[10.0, 30.0]],
          PP.keep_spans({"duration": 30.0, "noText": "0:10-9:99"}))

    built = P.create(song_for_build, text_for_build, os.path.join(tmp, "keeps"),
                     align_engine="energy", separate=False, skip="0:00-0:08")
    rec = json.load(open(os.path.join(built, "project.json"), encoding="utf-8"))
    check("a fresh song carries the stretches into itself",
          rec.get("keepSpans") == [[0.0, 8.0]], rec.get("keepSpans"))
    check("and says the original is kept there", rec.get("keepMarks") is True)

    # and they reach the finished page, which is what a person actually plays
    page = os.path.join(tmp, "with-keeps.html")
    lyr_page = L.parse(TEXT)
    A.align_energy(lyr_page, song_for_build, 26.0)
    B.build_html(page, lyr_page, 26.0, {"mix": (song_for_build, "audio/wav")},
                 "energy", embed=False, keep_spans=[[0.0, 8.0]])
    payload = B.read_payload(page)
    check("the page knows where the original stays",
          payload["data"].get("keepSpans") == [[0.0, 8.0]],
          payload["data"].get("keepSpans"))
    plain = os.path.join(tmp, "no-keeps.html")
    B.build_html(plain, lyr_page, 26.0, {"mix": (song_for_build, "audio/wav")},
                 "energy", embed=False)
    check("and a page with no marks says so plainly",
          B.read_payload(plain)["data"]["keepSpans"] == [],
          B.read_payload(plain)["data"].get("keepSpans"))

    print("\nThe name a song came with")
    # The file a link lands in is called something that survives every file
    # system — “Forevermore_[kBjKqBvbbjM]”. The song is not called that.
    untitled = os.path.join(tmp, "untitled.txt")
    open(untitled, "w", encoding="utf-8").write(
        "\n".join(TEXT.splitlines()[3:]))          # the same lines, no “title:”
    named = P.create(song_for_build, untitled,
                     os.path.join(tmp, "named"), align_engine="energy",
                     separate=False, title="Forevermore", artist="Lorna Shore")
    rec2 = json.load(open(os.path.join(named, "project.json"), encoding="utf-8"))
    check("the song is called what it was called where it came from",
          rec2["title"] == "Forevermore", rec2["title"])
    check("and the artist comes with it", rec2["artist"] == "Lorna Shore", rec2["artist"])
    check("the folder is named after the real title, in Latin letters",
          os.path.basename(named).startswith("forevermore"), os.path.basename(named))

    # what the lyrics file says still wins: it is the most deliberate of the three
    titled = P.create(song_for_build, text_for_build, os.path.join(tmp, "titled"),
                      align_engine="energy", separate=False,
                      title="Что-то из ссылки", artist="Кто-то")
    rec3 = json.load(open(os.path.join(titled, "project.json"), encoding="utf-8"))
    check("a title written in the lyrics file outranks the link",
          rec3["title"] == "Тестовая песня", rec3["title"])

    print("\nA line put right by hand survives a re-timing")
    from kstudio import project as PJ

    def _ln(i, lock=False):
        return {"text": f"строка {i}", "start": i * 2.0, "end": i * 2.0 + 1.5,
                "lock": lock, "words": [{"w": "строка", "t": i * 2.0, "d": 1.5, "s": 2}]}

    old_lines = [_ln(0), _ln(1, lock=True), _ln(2)]
    new_lines = [_ln(0 + 10), _ln(1 + 10), _ln(2 + 10)]
    msgs = []
    kept = PJ.keep_locked(old_lines, new_lines, msgs.append)
    check("the locked line keeps the time it was given by hand",
          kept == 1 and new_lines[1]["start"] == 2.0, new_lines[1]["start"])
    check("and the rest take the new timing",
          new_lines[0]["start"] == 20.0 and new_lines[2]["start"] == 24.0,
          [new_lines[0]["start"], new_lines[2]["start"]])
    check("the log says how many were left alone",
          any("заперт" in m or "locked" in m for m in msgs), msgs[:1])

    # With the text re-split, line seven is not the same line seven any more.
    msgs2 = []
    shorter = [_ln(0 + 10), _ln(1 + 10)]
    kept2 = PJ.keep_locked(old_lines, shorter, msgs2.append)
    check("locks are dropped when the lines no longer answer one for one",
          kept2 == 0 and shorter[1]["start"] == 22.0, shorter[1]["start"])
    check("and that is said out loud, not done quietly",
          any("замки" in m or "locks" in m for m in msgs2), msgs2[:1])

    check("a song with no locks is left entirely to the model",
          PJ.keep_locked([_ln(0), _ln(1)], [_ln(10), _ln(11)]) == 0)

    print("\nHow sure the model was, carried through to the eye")
    # The aligner returns a probability per word. It used to be averaged into a
    # single line in the log and thrown away, though it points straight at the
    # lines whose timing is a guess.
    from kstudio import project as PR

    heard = L.parse("первая строка тут\nвторая строка тут")
    rec = [(A.normalize_token(w.text), 1.0 + i * 0.4, 1.3 + i * 0.4,
            0.9 if i < 3 else 0.02)
           for i, w in enumerate(heard.words)]
    A._apply_recognized(heard.words, rec)
    check("the confidence of a word survives the matching",
          heard.words[0].prob == 0.9 and heard.words[-1].prob == 0.02,
          [w.prob for w in heard.words])
    check("a line is judged by its least certain word",
          heard.lines[1].sure == 0.02, heard.lines[1].sure)
    check("and it reaches the saved song",
          heard.lines[1].to_json().get("sure") == 0.02
          and heard.lines[0].to_json()["words"][0].get("p") == 0.9,
          heard.lines[1].to_json().get("sure"))
    check("a line with nothing heard has nothing claimed about it",
          L.parse("строка").lines[0].sure is None)

    # …and the panel of lines worth checking says so, measured against the song
    def _fake(n, sure):
        return {"text": "строка", "start": 1.0 + n, "end": 1.6 + n, "sure": sure,
                "words": [{"w": "строка", "t": 1.0 + n, "d": 0.6, "s": 2}]}

    even = {"lines": [_fake(i, 0.4) for i in range(10)]}
    check("a song where everything sits equally low is not all “doubtful”",
          not any("едва расслышала" in " ".join(pb["why"]) for pb in PR.problems(even)))
    odd = {"lines": [_fake(i, 0.4) for i in range(9)] + [_fake(9, 0.05)]}
    flagged = [pb for pb in PR.problems(odd) if "едва расслышала" in " ".join(pb["why"])]
    check("but the one line far below its neighbours is named",
          len(flagged) == 1 and flagged[0]["line"] == 9,
          [pb["line"] for pb in flagged])
    short = {"lines": [_fake(i, 0.4) for i in range(3)] + [_fake(3, 0.01)]}
    check("on a song too short to judge, nothing is claimed",
          not any("едва расслышала" in " ".join(pb["why"]) for pb in PR.problems(short)))

    print("\nThe models on offer")
    from kstudio import models as M
    from kstudio import sysinfo as SI

    have = M.whisper_all()
    check("turbo is among the models offered", "large-v3-turbo" in have, list(have))
    check("its size is known, so nobody is promised the wrong wait",
          M.size_label("large-v3-turbo") not in ("", None), M.size_label("large-v3-turbo"))
    check("and so is what it needs of memory",
          0 < SI.NEED_WHISPER.get("large-v3-turbo", 0) < SI.NEED_WHISPER["large-v3"],
          SI.NEED_WHISPER.get("large-v3-turbo"))
    check("every model the window offers has both numbers",
          all(M.size_label(n) and n in SI.NEED_WHISPER for n in have), list(have))
    page = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "kstudio", "studio.html"), encoding="utf-8").read()
    check("the window offers exactly the models the program knows",
          all(f'value="{n}"' in page for n in have),
          [n for n in have if f'value="{n}"' not in page])

    # Which separator ran decides how clean the voice is, and the timing is made
    # from that voice — so the choice has to reach Demucs, not stop halfway.
    from kstudio import separate as S
    seen = {}
    real_sep = S.separate
    S.separate = lambda wav, out, model="htdemucs", device=None, log=None: (
        seen.update(model=model) or (None, None))
    try:
        P.create(song_for_build, text_for_build, os.path.join(tmp, "sep-test"),
                 align_engine="energy", separate=True, separator="htdemucs_ft")
        check("the finer separator reaches Demucs", seen.get("model") == "htdemucs_ft",
              seen.get("model"))
        seen.clear()
        P.create(song_for_build, text_for_build, os.path.join(tmp, "sep-test2"),
                 align_engine="energy", separate=True)
        check("and the plain one is the default", seen.get("model") == "htdemucs",
              seen.get("model"))
    finally:
        S.separate = real_sep

    print("\nA whole song built with wordless stretches marked")
    # The road end to end, without a neural net in it: build a real project and
    # look at where the lines actually landed. The test song sings at 2.0-4.6,
    # 5.0-7.6, 8.0-10.6, 11.0-13.6, 16.0-18.6, 19.0-21.6 — mark the first two
    # phrases as wordless and nothing may be laid on them.
    folder = P.create(song_for_build, text_for_build, built_root,
                      align_engine="energy", separate=False, whisper_model="medium",
                      skip="0:00-0:08")
    made = json.load(open(os.path.join(folder, "project.json"), encoding="utf-8"))
    starts = [ln["start"] for ln in made["lines"]]
    check("no line is laid on the marked stretch",
          all(st >= 7.8 for st in starts), [round(x, 1) for x in starts])
    check("and the song still holds every line",
          len(made["lines"]) == len(L.parse(TEXT).lines), len(made["lines"]))
    check("the marks are written down with the song",
          made.get("noText", "").startswith("0.0-8.0"), made.get("noText"))
    check("and so is the model it was timed with",
          made.get("model") == "medium", made.get("model"))

    # the same thing said in the lyrics file instead of the field
    text_marked = os.path.join(tmp, "for-build-marked.txt")
    open(text_marked, "w", encoding="utf-8").write(
        TEXT.replace("[Куплет]", "[Вступление 0:00-0:08]\n[Куплет]"))
    folder2 = P.create(song_for_build, text_marked, built_root,
                       align_engine="energy", separate=False)
    made2 = json.load(open(os.path.join(folder2, "project.json"), encoding="utf-8"))
    starts2 = [ln["start"] for ln in made2["lines"]]
    check("a mark inside the lyrics file works the same",
          all(st >= 7.8 for st in starts2), [round(x, 1) for x in starts2])
    check("and it does not become a line of the song",
          len(made2["lines"]) == len(made["lines"]), len(made2["lines"]))

    # and with nothing marked the same song uses its whole length
    folder3 = P.create(song_for_build, text_for_build, built_root,
                       align_engine="energy", separate=False)
    made3 = json.load(open(os.path.join(folder3, "project.json"), encoding="utf-8"))
    check("without marks the early phrases are used",
          min(ln["start"] for ln in made3["lines"]) < 7.8,
          round(min(ln["start"] for ln in made3["lines"]), 1))

    print("\nSigns of life during long steps")
    import time

    from kstudio.progress import Heartbeat, mmss
    check("the time reads correctly", (mmss(0), mmss(75)) == ("0:00", "1:15"))
    beats = []
    with Heartbeat(beats.append, "проверка", every=0.2) as hb:
        time.sleep(0.3)
        hb.progress(3, 10)
        hb.note("Demucs: 40%")
        time.sleep(0.3)
    check("the step shows signs of life", len(beats) >= 2)
    check("the fraction done is visible", any("30%" in b for b in beats))
    check("the step's note is visible", any("Demucs: 40%" in b for b in beats))
    before = len(beats)
    time.sleep(0.4)
    check("it goes quiet after leaving", len(beats) == before)

    # The share done, and what it means for the wait. A step that says only how
    # long it has been running tells a person nothing about whether to wait.
    beats_left = []
    with Heartbeat(beats_left.append, "разметка", every=0.15) as hb3:
        time.sleep(0.2)
        hb3.progress(2, 100)
        time.sleep(0.25)
    said = " ".join(beats_left)
    check("the share done is shown", "2%" in said, beats_left[-1] if beats_left else "")
    check("and how long is left, measured at this machine's own pace",
          "осталось примерно" in said or "left" in said, beats_left[-1] if beats_left else "")
    near_end = []
    with Heartbeat(near_end.append, "разметка", every=0.15) as hb4:
        time.sleep(0.2)
        hb4.progress(99, 100)
        time.sleep(0.25)
    check("a couple of seconds left is not worth saying",
          not any("примерно" in b or "left" in b for b in near_end), near_end[-1:])

    # And the call that produces those numbers: the library counts nothing when
    # its own progress bar is switched off, and hands back zeros for minutes.
    import types
    seen_kw = {}

    class _FakeResult:
        segments = []

    class _FakeModel:
        def align(self, audio, text, **kw):
            seen_kw.update(kw)
            cb = kw.get("progress_callback")
            if cb:
                cb(30, 100)          # the library reporting its own progress
            return _FakeResult()

    fake = types.ModuleType("stable_whisper")
    fake.load_model = lambda *a, **k: _FakeModel()
    real_mod = sys.modules.get("stable_whisper")
    sys.modules["stable_whisper"] = fake
    said_lines = []
    try:
        A.align_whisper(L.parse("раз строка тут"), song, 26.0, model_name="small",
                        language="ru", log=said_lines.append)
    except Exception:
        pass                          # the fake returns no words; the call is the point
    finally:
        if real_mod is not None:
            sys.modules["stable_whisper"] = real_mod
        else:
            sys.modules.pop("stable_whisper", None)
    check("the aligner is asked to report its progress",
          callable(seen_kw.get("progress_callback")), sorted(seen_kw))
    check("and its own counter is left switched on, or it reports zeros",
          seen_kw.get("verbose") is False, repr(seen_kw.get("verbose")))

    # A sign of life must never bring the step down: if the log throws, stay quiet.
    def bad_log(_):
        raise RuntimeError("лог сломан")

    with Heartbeat(bad_log, "стойкость", every=0.1):
        time.sleep(0.3)
    check("a broken log does not bring the step down", True)

    # A counter at zero or at the very end says nothing — the fraction is hidden.
    beats2 = []
    with Heartbeat(beats2.append, "без счёта", every=0.15) as hb2:
        hb2.progress(0, 26)
        time.sleep(0.2)
    check("an empty counter is not shown", beats2 and "%" not in beats2[0])

    print("\nA song from a link")
    # Nothing here touches the internet: the downloader is a stand-in that
    # hands over a file, and the lyrics library is a stand-in next door.
    import shutil
    from kstudio import fetch as FE

    check("a name written for a page becomes a name for a song",
          FE.clean_title("Nirvana - Smells Like Teen Spirit (Official Music Video)")
          == "Nirvana - Smells Like Teen Spirit"
          and FE.clean_title("ДДТ — Что такое осень [HD]") == "ДДТ — Что такое осень")
    check("the artist and the song are told apart",
          FE.split_name("Кино - Группа крови (Remastered 2021)") == ("Кино", "Группа крови"))
    check("a name with no dash stays whole",
          FE.split_name("Плачу на техно") == ("", "Плачу на техно"))
    for bad in ("", "   ", "ftp://example.com/x", "file:///etc/passwd", "-x"):
        try:
            FE.check_url(bad)
            check(f"a link that is not a link is refused: {bad!r}", False)
        except FE.FetchError:
            check(f"a link that is not a link is refused: {bad or 'empty'}", True)

    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inbox = os.path.join(tmp, "inbox")
    stub = os.path.join(app_dir, "tests", "stub_ytdlp.py")
    os.environ["KARAOKE_YTDLP"] = stub
    os.environ["KARAOKE_STUB_AUDIO"] = song            # the test song stands in
    check("the downloader is the one we pointed at", FE.tool() == [stub] and FE.available())

    # pip on macOS writes the command into ~/Library/Python/3.x/bin, which a
    # double-clicked window has never heard of. Found there, it still works.
    hidden = os.path.join(tmp, "hidden-bin")
    os.makedirs(hidden, exist_ok=True)
    shutil.copyfile(stub, os.path.join(hidden, "yt-dlp"))
    os.chmod(os.path.join(hidden, "yt-dlp"), 0o755)
    del os.environ["KARAOKE_YTDLP"]
    was_path, was_places = os.environ.get("PATH", ""), FE.places
    os.environ["PATH"] = ""
    FE.places = lambda: [hidden]
    check("a command outside PATH is still found",
          FE.tool() == [os.path.join(hidden, "yt-dlp")], FE.tool())

    # A Python that cannot say where it lives cannot be asked to run a module:
    # handing that emptiness to the command line crashes on NoneType instead of
    # answering about the song.
    FE.places = lambda: []
    was_exe, sys.executable = sys.executable, None
    check("and with nothing to run, nothing is invented", FE.tool() is None)
    try:
        FE.download("https://example.com/watch?v=zzz123", inbox)
        check("the answer is about the downloader, not about NoneType", False)
    except FE.FetchError as e:
        check("the answer is about the downloader, not about NoneType",
              "yt-dlp" in str(e) and "NoneType" not in str(e), str(e)[:70])
    sys.executable = was_exe
    FE.places, os.environ["PATH"] = was_places, was_path
    os.environ["KARAOKE_YTDLP"] = stub

    # The same emptiness used to crash the search for ffmpeg, which is what a
    # link really tripped over: a fault of ours dressed up as a missing file.
    was_exe, sys.executable = sys.executable, None
    AU._FFMPEG = None
    try:
        AU.ffmpeg()
        check("ffmpeg is looked for without falling over", True)
    except AU.AudioError:
        check("ffmpeg is looked for without falling over", True)
    except TypeError as e:
        check("ffmpeg is looked for without falling over", False, str(e))
    sys.executable, AU._FFMPEG = was_exe, None

    # And the window opened by double-clicking has a bare PATH: ffmpeg is
    # installed and works in a terminal, while the program says it is missing.
    was_path, os.environ["PATH"] = os.environ.get("PATH", ""), ""
    AU._FFMPEG = None
    try:
        found_ff = AU.ffmpeg()
    except AU.AudioError:
        found_ff = ""
    os.environ["PATH"], AU._FFMPEG = was_path, None
    check("ffmpeg is found in the usual places, not only through PATH",
          bool(found_ff), found_ff or "not found with an empty PATH")
    got = FE.download("https://example.com/watch?v=zzz123", inbox)
    check("the sound lands next to the projects",
          os.path.isfile(got["path"]) and os.path.dirname(got["path"]) == inbox)
    check("and it is the audio, not an empty file",
          os.path.getsize(got["path"]) == os.path.getsize(song))
    check("the artist and the song came with it",
          (got["artist"], got["track"]) == ("Stub Artist", "Stub Song"),
          got["artist"] + " — " + got["track"])
    check("nothing half-downloaded is left behind",
          all(not n.startswith(".fetch-") for n in os.listdir(inbox)), os.listdir(inbox))
    # The stub lays a junk webp beside the true jpeg, as real downloaders do:
    # the cover that arrives must be the jpeg, by its first bytes and not by
    # the extension someone renamed it to.
    check("the clip's cover came along, and it is a real jpeg",
          bool(got.get("cover")) and os.path.isfile(got["cover"])
          and open(got["cover"], "rb").read(2) == b"\xff\xd8",
          str(got.get("cover")))

    # What ffmpeg is called matters to the downloader: it is handed a folder
    # and looks in it for “ffmpeg” and “ffprobe”. The copy pip installs is one
    # file named after its platform, with no ffprobe beside it — hand that over
    # and yt-dlp falls over an empty path, saying only “not NoneType”.
    odd = os.path.join(tmp, "pip-ffmpeg")
    os.makedirs(odd, exist_ok=True)
    odd_ff = os.path.join(odd, "ffmpeg-macos-arm64-v7.0.2")
    open(odd_ff, "w").close()
    os.chmod(odd_ff, 0o755)
    was_ff, was_fp = AU.ffmpeg, AU.ffprobe
    AU.ffmpeg, AU.ffprobe = (lambda: odd_ff), (lambda: None)
    bin_dir = os.path.join(tmp, "as-yt-dlp-wants")
    os.makedirs(bin_dir, exist_ok=True)
    where, can_extract = FE._tools(bin_dir)
    check("a strangely named ffmpeg is given the name yt-dlp looks for",
          where and os.path.exists(os.path.join(where, "ffmpeg")), where)
    check("and with no ffprobe the sound is not pulled out on the spot",
          can_extract is False)
    args = FE._base_args(["yt-dlp"], bin_dir)
    check("so the video comes down whole instead of failing", "-x" not in args)
    check("and the folder handed over is the one with the right names",
          args[args.index("--ffmpeg-location") + 1] == where)

    AU.ffmpeg, AU.ffprobe = was_ff, was_fp
    try:
        where2, can2 = FE._tools(bin_dir)
        check("an ordinary pair is handed over as it stands",
              can2 and where2 == os.path.dirname(AU.ffmpeg()), where2)
        check("and then the sound is pulled out at once",
              "-x" in FE._base_args(["yt-dlp"], bin_dir))
    except AU.AudioError:
        check("an ordinary pair is handed over as it stands", True, "no ffmpeg here")

    # A refusal aimed at the client, not at the video: YouTube tells one player
    # “the page needs to be reloaded” and hands the sound to the next one.
    attempts = os.path.join(tmp, "attempts.txt")
    os.environ["KARAOKE_STUB_LOG"] = attempts
    again = FE.download("https://example.com/watch?v=reload", inbox)
    tried = open(attempts, encoding="utf-8").read().splitlines()
    check("a client the site turned away is asked again as another one",
          os.path.isfile(again["path"]) and len(tried) == 2, len(tried))
    check("and the one that got through is the android player",
          "player_client=android" in tried[-1], tried[-1][-40:])
    os.remove(attempts)

    try:
        FE.download("https://example.com/watch?v=fail", inbox)
        check("a link that leads nowhere is an error, not a file", False)
    except FE.FetchError as e:
        check("a link that leads nowhere says why",
              "Video unavailable" in str(e) and "ERROR" not in str(e), str(e))
    check("and it leaves no rubbish in the folder",
          all(not n.startswith(".fetch-") for n in os.listdir(inbox)), os.listdir(inbox))
    # “This video is private” is about the video: asking again as another
    # player would only make a person wait for the same answer four times.
    check("a plain refusal is not asked again",
          len(open(attempts, encoding="utf-8").read().splitlines()) == 1
          if os.path.isfile(attempts) else False)
    del os.environ["KARAOKE_STUB_LOG"]

    # Cookies and the like: what the person adds themselves reaches the
    # downloader, whatever the program decided on its own.
    os.environ["KARAOKE_YTDLP_ARGS"] = "--cookies-from-browser chrome"
    check("what the settings add is passed on",
          FE.extra_args() == ["--cookies-from-browser", "chrome"], FE.extra_args())
    os.environ["KARAOKE_STUB_LOG"] = attempts
    FE.download("https://example.com/watch?v=cookie", inbox)
    check("and it really lands in the command line",
          "--cookies-from-browser chrome" in open(attempts, encoding="utf-8").read())
    del os.environ["KARAOKE_YTDLP_ARGS"], os.environ["KARAOKE_STUB_LOG"]
    del os.environ["KARAOKE_YTDLP"]

    print("\nWhen the downloader is nowhere to be found, the words help")
    # “Install it with pip” is useless advice to somebody who just did. A
    # machine holds several Pythons — a terminal reaches one, a double-clicked
    # window finds another — and pip leaves yt-dlp beside whichever it belongs
    # to. The message has to name the one that is doing the looking.
    class _NoYtDlp:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] == "yt_dlp":
                raise ImportError("not for this Python")
            return None
    _blocker = _NoYtDlp()
    sys.meta_path.insert(0, _blocker)
    for _m in [m for m in sys.modules if m.split(".")[0] == "yt_dlp"]:
        del sys.modules[_m]
    try:
        said = FE.how_to_install()
    finally:
        sys.meta_path.remove(_blocker)
    check("the message names the very Python that went looking",
          sys.executable in said, said[:90])
    check("and offers a command bound to it, not a bare “pip install”",
          "-m pip install" in said, said[:90])

    # A person who knows where their copy is should be able to say so without
    # setting an environment variable for a double-clicked window.
    _real_setting = FE._setting
    FE._setting = lambda *names: "/somewhere/of/my/own/yt-dlp"
    was = os.environ.pop("KARAOKE_YTDLP", None)
    try:
        check("a path written in the settings is the one that is used",
              FE.tool() == ["/somewhere/of/my/own/yt-dlp"], FE.tool())
    finally:
        FE._setting = _real_setting
        if was is not None:
            os.environ["KARAOKE_YTDLP"] = was
    folders = FE.places()
    check("and no folder is searched twice",
          len(folders) == len(set(folders)), len(folders))
    # A macOS framework build keeps its user scripts under a scheme of its
    # own. Asking the posix one gives ~/.local/bin and misses
    # ~/Library/Python/3.x/bin entirely — which is exactly where pip puts
    # yt-dlp on a Mac.
    import sysconfig as _sc
    if "osx_framework_user" in _sc.get_scheme_names():
        mac = _sc.get_path("scripts", "osx_framework_user")
        check("the macOS scheme's own scripts folder is among them",
              mac in folders, mac)

    print("\nThe words, looked up by the name of the song")
    import importlib.util
    import threading

    from kstudio import findlyrics as FL
    spec = importlib.util.spec_from_file_location(
        "stub_lyrics", os.path.join(app_dir, "tests", "stub_lyrics.py"))
    stub_lyrics = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stub_lyrics)
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", 0), stub_lyrics.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    FL.BASE = f"http://127.0.0.1:{srv.server_port}"
    try:
        check("timed words are stripped down to words",
              FL.plain({"syncedLyrics": "[00:12.34] раз\n[00:15.00] два"}) == "раз\nдва")
        found = FL.search("Stub Song", "Stub Artist", duration=21)
        check("the nearest recording comes first",
              found and found[0]["duration"] == 21, [f["duration"] for f in found])
        check("a record with no words at all is not offered",
              all(f["text"].strip() for f in found), len(found))
        check("the lines are counted for the person reading",
              found[0]["lines"] == 3, found[0]["lines"])
        check("the source is named", all(f["source"] == "LRCLIB" for f in found))
        check("a song nobody knows finds nothing", FL.search("nothing at all") == [])
        try:
            FL.search("")
            check("a search with no name is refused", False)
        except FL.LyricsError:
            check("a search with no name is refused", True)
    finally:
        srv.shutdown()
    FL.BASE = "http://127.0.0.1:9"       # a port nothing listens on
    try:
        FL.search("Stub Song")
        check("an unreachable library is an error, not a crash", False)
    except FL.LyricsError as e:
        check("an unreachable library is an error, not a crash", True, str(e)[:60])

    shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + ("FAILED: " + ", ".join(failures) if failures else "All checks passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
