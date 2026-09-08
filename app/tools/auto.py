#!/usr/bin/env python3
"""Automatic mode: drop files onto the .bat, or point at a folder.

    python tools/auto.py song.mp3 lyrics.txt     # one song
    python tools/auto.py D:\\Music               # a whole folder, matched by name
    python tools/auto.py D:\\Music --watch        # watch the folder and build new ones

Pairs are found by name: “Wind.mp3” + “Wind.txt” → “Wind_karaoke.html”.
The settings come from settings.ini next to karaoke.py, if there is one.
"""

from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from kstudio.i18n import tr          # noqa: E402
from kstudio import settings as SET  # noqa: E402

import karaoke  # noqa: E402

AUDIO_EXT = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".opus", ".aac",
             ".wma", ".mp4", ".webm", ".aiff", ".alac"}
TEXT_EXT = {".txt", ".lrc"}
# A Latin name: on a non-Russian Windows, Cyrillic names from an archive often
# arrive as mojibake. The old name is still read if it survived from before.
HOME = os.path.dirname(ROOT)
# Settings live next to the program; earlier locations are read as a fallback.
SETTINGS = SET.path() or os.path.join(ROOT, "settings.ini")

# settings key → command-line option
KEYS = {
    "align": "--align", "движок": "--align",
    "whisper-model": "--whisper-model", "model": "--whisper-model",
    "модель": "--whisper-model",
    "lang": "--lang", "язык": "--lang", "language": "--lang",
    "colors": "--colors", "цвета": "--colors",
    "theme": "--theme", "оформление": "--theme",
    "ui-lang": "--ui-lang", "надписи": "--ui-lang",
    "codec": "--codec", "кодек": "--codec",
    "device": "--device",
    "separator": "--demucs-model", "отделение": "--demucs-model",
}
FLAGS = {  # значение «нет/no/0» → добавить флаг отключения
    "separate": "--no-separate", "минусовка": "--no-separate",
    "instrumental": "--no-separate",
    "embed": "--no-embed", "встраивать": "--no-embed",
}
YES = {"да", "yes", "y", "1", "true", "вкл", "on"}
NO = {"нет", "no", "n", "0", "false", "выкл", "off"}


def read_settings() -> list:
    """settings.ini → a list of command-line arguments."""
    args: list = []
    for key, val in SET.read(SETTINGS).items():
        if key in KEYS:
            # “авто” is how “auto” is written in Russian settings files
            if KEYS[key] in ("--lang", "--ui-lang") and \
                    val.lower() in ("авто", "auto", "сам"):
                val = "auto"
            args += [KEYS[key], val]
        elif key in FLAGS and val.lower() in NO:
            args.append(FLAGS[key])
        elif key == "lrc" and val.lower() in YES:
            args.append("--lrc")
    return args


def find_pairs(paths):
    """Sort the input paths into (audio, lyrics) pairs."""
    audio, texts, missing = [], {}, []

    def take(p):
        ext = os.path.splitext(p)[1].lower()
        if ext in AUDIO_EXT:
            audio.append(p)
        elif ext in TEXT_EXT:
            texts.setdefault(os.path.splitext(os.path.basename(p))[0].lower(), p)

    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                take(os.path.join(p, name))
        elif os.path.isfile(p):
            take(p)
        else:
            print(tr(f"  ! not found: {p}", f"  ! не найдено: {p}"))

    pairs = []
    for a in audio:
        stem = os.path.splitext(os.path.basename(a))[0]
        txt = texts.get(stem.lower())
        if txt is None and len(texts) == 1 and len(audio) == 1:
            txt = next(iter(texts.values()))       # одна песня + один текст
        if txt is None:                            # текст рядом с аудио?
            for ext in (".txt", ".lrc"):
                cand = os.path.splitext(a)[0] + ext
                if os.path.isfile(cand):
                    txt = cand
                    break
        if txt:
            pairs.append((a, txt))
        else:
            missing.append(a)
    return pairs, missing


def out_path(audio: str) -> str:
    return os.path.splitext(audio)[0] + "_karaoke.html"


def is_fresh(audio: str, text: str) -> bool:
    out = out_path(audio)
    if not os.path.isfile(out):
        return False
    t = os.path.getmtime(out)
    return t >= os.path.getmtime(audio) and t >= os.path.getmtime(text)


def process(pairs, extra, force=False) -> int:
    done = failed = skipped = 0
    for i, (audio, text) in enumerate(pairs, 1):
        name = os.path.basename(audio)
        if not force and is_fresh(audio, text):
            print(tr(f"[{i}/{len(pairs)}] {name} — already built, skipping",
                  f"[{i}/{len(pairs)}] {name} — уже собрано, пропускаю"))
            skipped += 1
            continue
        print(f"\n[{i}/{len(pairs)}] {name}")
        print("-" * 60)
        karaoke.T0 = time.time()      # чтобы секунды в логе считались для каждой песни заново
        try:
            code = karaoke.main([audio, text, "-o", out_path(audio)] + extra)
        except Exception as e:                     # одна плохая песня не роняет пачку
            print(tr(f"  error: {e}", f"  ошибка: {e}"))
            code = 1
        if code == 0:
            done += 1
        else:
            failed += 1
    print("\n" + "=" * 60)
    print(tr(f"Done: {done}   skipped: {skipped}   failed: {failed}",
                  f"Готово: {done}   пропущено: {skipped}   с ошибкой: {failed}"))
    return 1 if failed else 0


def main(argv) -> int:
    force = "--force" in argv
    watch = "--watch" in argv
    # Anything that looks like an option is passed straight to karaoke.py,
    # together with its value. Without this, `--align energy` turned “energy”
    # into a path and the run died on “file not found”.
    paths, extra = [], []
    rest = [a for a in argv if a not in ("--force", "--watch")]
    while rest:
        a = rest.pop(0)
        if a.startswith("-"):
            extra.append(a)
            if "=" not in a and rest and not rest[0].startswith("-") \
                    and not os.path.exists(rest[0]):
                extra.append(rest.pop(0))
        else:
            paths.append(a)
    extra = read_settings() + extra

    if not paths:
        print(__doc__)
        print(tr("Drag a song file and a lyrics file onto Make-karaoke.bat.",
                  "Перетащите аудиофайл и файл с текстом на «Make-karaoke.bat»."))
        return 2

    if extra:
        print(tr("Settings:", "Настройки:"), " ".join(extra))

    if watch:
        folder = paths[0]
        print(tr(f"Watching the folder {folder}. Put a song and lyrics with the "
                 f"same name in it — the karaoke builds itself.\nStop with Ctrl+C\n",
                 f"Слежу за папкой {folder}. Кладите туда песню и текст с одинаковым "
                 f"именем — караоке соберётся само.\nОстановить: Ctrl+C\n"))
        seen = set()
        while True:
            pairs, _ = find_pairs([folder])
            new = [p for p in pairs if p not in seen and not is_fresh(*p)]
            if new:
                process(new, extra, force)
                seen.update(new)
                print(tr("\nWaiting for new files…", "\nЖду новые файлы…"))
            time.sleep(5)

    pairs, missing = find_pairs(paths)
    for a in missing:
            print(tr(f"  ! no lyrics for {os.path.basename(a)} — put "
             f"{os.path.splitext(os.path.basename(a))[0]}.txt next to it",
             f"  ! нет текста для {os.path.basename(a)} — положите рядом "
             f"{os.path.splitext(os.path.basename(a))[0]}.txt"))
    if not pairs:
        print(tr("\nNo “audio + lyrics” pair was found.",
                  "\nНе нашёл ни одной пары «аудио + текст»."))
        return 2

    print(tr(f"Songs found: {len(pairs)}", f"Нашёл песен: {len(pairs)}"))
    return process(pairs, extra, force)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print(tr("\nStopped.", "\nОстановлено."))
        sys.exit(130)
