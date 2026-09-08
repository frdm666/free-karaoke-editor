#!/usr/bin/env python3
"""Diagnosing a built karaoke page: where the timings drifted apart.

    py tools\\diagnose.py "D:\\Music\\Song_karaoke.html"
    py tools\\diagnose.py "...html" "D:\\Music\\Song.mp3"    # also compare with the original

Prints a report — copy the whole of it into the chat.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from kstudio import audio as AU  # noqa: E402
from kstudio.i18n import tr    # noqa: E402

PAYLOAD_RE = re.compile(r'<script id="payload" type="application/json">(.*?)</script>', re.S)


def mmss(t) -> str:
    if t is None:
        return "—"
    return f"{int(t // 60)}:{t % 60:05.2f}"


def load_payload(html_path: str) -> dict:
    with open(html_path, encoding="utf-8") as f:
        m = PAYLOAD_RE.search(f.read())
    if not m:
        raise SystemExit(tr("This does not look like a page built by this program.",
                            "Это не похоже на страницу, собранную этой программой."))
    raw = (m.group(1).replace("\\u003c", "<").replace("\\u003e", ">")
           .replace("\\u0026", "&"))
    return json.loads(raw)


def track_duration(uri: str, tmp: str, name: str):
    """Track length: the audio is inside the page (data:) or in a file next to it."""
    path = AU.from_uri(uri, tmp, name, sys.argv[1])
    if not path:
        return None, 0
    size = os.path.getsize(path)
    try:
        return AU.duration(path), size
    except Exception:
        return None, size


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    html_path = argv[0]
    if not os.path.isfile(html_path):
        print(tr(f"File not found: {html_path}", f"Не найден файл: {html_path}"))
        return 2

    P = load_payload(html_path)
    D = P["data"]
    lines = D["lines"]
    words = [w for ln in lines for w in ln["words"]]

    print("=" * 62)
    print(tr("  KARAOKE DIAGNOSTICS", "  ДИАГНОСТИКА КАРАОКЕ"))
    print("=" * 62)
    print(tr("File       : ", "Файл       : ") + os.path.basename(html_path))
    print(tr("Song       : ", "Песня      : ")
          + f"{D.get('title') or '—'} / {D.get('artist') or '—'}")
    print(tr("Timing     : ", "Разметка   : ") + str(P.get('engineLabel')))
    ver = P.get("player")
    from kstudio import __version__ as cur
    if not ver:
        print(tr(f"Player     : older than 1.4 — the page is worth rebuilding (now {cur})",
                 f"Плеер      : старее 1.4 — страницу стоит пересобрать (сейчас {cur})"))
    elif ver != cur:
        print(tr(f"Player     : {ver}, while the program is already {cur} — worth rebuilding",
                 f"Плеер      : {ver}, а программа уже {cur} — стоит пересобрать"))
    else:
        print(tr(f"Player     : {ver} (current)", f"Плеер      : {ver} (актуальный)"))
    print(tr(f"Lines      : {len(lines)}   words: {len(words)}",
             f"Строк      : {len(lines)}   слов: {len(words)}"))

    dur = D.get("duration") or 0
    print(tr("\nDuration in the timing  : ", "\nДлительность в разметке : ") + mmss(dur))

    tmp = tempfile.mkdtemp(prefix="karaoke_diag_")
    real = {}
    for name, uri in P.get("audio", {}).items():
        d, size = track_duration(uri, tmp, name)
        real[name] = d
        kind = (tr("inside the page", "внутри страницы") if uri.startswith("data:")
                else tr("a file next to it", "файлом рядом"))
        print(tr("Track   ", "Дорожка ") + f"{name:12}: {mmss(d)}  "
              f"({size/1024/1024:.1f} " + tr("MB", "МБ") + f", {kind})")

    if len(argv) > 1 and os.path.isfile(argv[1]):
        try:
            print(tr("Source file             : ", "Исходный файл           : ")
                  + mmss(AU.duration(argv[1])))
        except Exception as e:
            print(tr(f"Source file             : could not be read ({e})",
                     f"Исходный файл           : не прочитался ({e})"))

    if not lines:
        print(tr("\nThe page has no lines of text at all.",
                 "\nВ странице нет ни одной строки текста."))
        return 1

    first, last = lines[0]["start"], lines[-1]["end"]
    print(tr("\nThe first line starts   : ", "\nПервая строка начинается: ") + mmss(first))
    print(tr("The last one ends       : ", "Последняя заканчивается : ") + mmss(last))

    base = max([d for d in real.values() if d] + [dur]) or 1
    cover = last / base
    print(tr("Text covers the song    : ", "Покрытие песни текстом  : ")
          + f"{cover * 100:.0f}%")

    print("\n" + "-" * 62)
    problems = []
    if cover < 0.75:
        problems.append(tr(
            f"The text ends at {cover*100:.0f}% of the song — the timing is squeezed "
            f"about {1/cover:.1f} times. That is what feels like “the text runs faster”.",
            f"Текст кончается на {cover*100:.0f}% песни — разметка сжата примерно "
            f"в {1/cover:.1f} раза. Именно это ощущается как «текст бежит быстрее»."))
    if cover > 1.02:
        problems.append(tr("The timing runs past the end of the song.",
                           "Разметка вылезает за конец песни."))

    durs = [d for d in real.values() if d]
    if durs and dur and abs(max(durs) - dur) > 1.0:
        problems.append(tr(
            f"The audio in the page ({mmss(max(durs))}) does not match the duration "
            f"the timing was computed for ({mmss(dur)}).",
            f"Звук в странице ({mmss(max(durs))}) не совпадает с длительностью, "
            f"под которую считалась разметка ({mmss(dur)})."))
    if len(durs) > 1 and max(durs) - min(durs) > 1.0:
        problems.append(tr(
            f"The tracks are of different lengths: {mmss(min(durs))} and {mmss(max(durs))}.",
            f"Дорожки разной длины: {mmss(min(durs))} и {mmss(max(durs))}."))

    gaps = [lines[i + 1]["start"] - lines[i]["start"] for i in range(len(lines) - 1)]
    if len(gaps) > 3:
        avg = sum(gaps) / len(gaps)
        spread = (sum((g - avg) ** 2 for g in gaps) / len(gaps)) ** 0.5
        print(tr(f"Step between lines: {avg:.2f}s on average, spread {spread:.2f}s",
                 f"Шаг между строками: в среднем {avg:.2f}с, разброс {spread:.2f}с"))
        if spread < 0.15 * avg:
            problems.append(tr(
                "The lines come at even intervals — a sign that the alignment did "
                "not work and the text was laid out mechanically.",
                "Строки идут через равные промежутки — признак того, что "
                "выравнивание не сработало и текст разложен механически."))

    zero = sum(1 for w in words if w.get("d", 0) <= 0.01)
    if zero:
        problems.append(tr(f"{zero} words of zero length.", f"{zero} слов нулевой длины."))

    print()
    if problems:
        print(tr("FOUND:", "НАЙДЕНО:"))
        for p in problems:
            print("  • " + p)
    else:
        print(tr("Nothing suspicious found: the timing covers the whole song,",
                 "Ничего подозрительного не нашёл: разметка покрывает песню целиком,"))
        print(tr("the track lengths agree, the line step is uneven (so it is real).",
                 "длины дорожек сходятся, шаг строк неравномерный (значит, реальный)."))

    print(tr("\nThe first 5 lines:", "\nПервые 5 строк:"))
    for ln in lines[:5]:
        print(f"  [{mmss(ln['start'])}] {ln['text'][:44]}")
    print(tr("The last 3 lines:", "Последние 3 строки:"))
    for ln in lines[-3:]:
        print(f"  [{mmss(ln['start'])}] {ln['text'][:44]}")
    print("=" * 62)

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
