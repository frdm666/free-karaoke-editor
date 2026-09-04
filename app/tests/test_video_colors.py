#!/usr/bin/env python3
"""The finished video: the voice colours, and that the texts do not overlap.

Проверять только исходники мало: в MP4 всё рисуется своим кодом, и цвета там
однажды оказались одинаковыми, хотя в редакторе были разные.
"""

from __future__ import annotations

import array
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

failures = []


def check(name, cond, extra=""):
    print(("  OK     " if cond else "  FAILED ") + name + (" — " + str(extra) if extra else ""))
    if not cond:
        failures.append(name)


def tone(path, freq=220.0, dur=8.0, sr=22050):
    import math
    import struct
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(
            struct.pack("<h", int(0.3 * math.sin(2 * math.pi * freq * i / sr) * 30000))
            for i in range(int(sr * dur))))
    return path


def main():
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("  skipped: no Pillow, the video cannot be drawn")
        return 0

    spec = importlib.util.spec_from_file_location("video", os.path.join(ROOT, "tools", "video.py"))
    video = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(video)

    tmp = tempfile.mkdtemp(prefix="karaoke_vid_")
    wav = tone(os.path.join(tmp, "a.wav"))
    # Two lines sound at once: the first voice and the second.
    payload = {
        "colors": ["#00ff00", "#ff00ff"],
        "theme": {"bg": "#000000", "text": "#ffffff"},
        "data": {"title": "T", "duration": 8.0, "lines": [
            {"text": "aaa", "start": 1.0, "end": 5.0, "voice": 1,
             "words": [{"w": "aaa", "t": 1.0, "d": 4.0, "s": 1}]},
            {"text": "bbb", "start": 1.2, "end": 5.0, "voice": 2,
             "words": [{"w": "bbb", "t": 1.2, "d": 3.8, "s": 1}]},
        ]}}

    class Args:
        width, height, fps, crf = 640, 360, 5, 30
        preset, font = "ultrafast", None
        intro = False
        intro = False        # these frames measure the song, not the opening
        start, seconds, audio, timings = 0.0, 6.0, "minus", None
        output = os.path.join(tmp, "out.mp4")

    args = Args()
    video.render(payload, wav, args.output, args)
    check("the video was built", os.path.isfile(args.output) and os.path.getsize(args.output) > 1000,
          str(os.path.getsize(args.output)) if os.path.isfile(args.output) else "нет файла")

    from kstudio import audio as AU
    png = os.path.join(tmp, "frame.png")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", "4.0", "-i", args.output,
                    "-frames:v", "1", png], check=True)
    from PIL import Image
    im = Image.open(png).convert("RGB")
    W, H = im.size
    rows = {}
    for y in range(H):
        for x in range(0, W, 2):
            r, g, b = im.getpixel((x, y))
            if g > 150 and r < 90 and b < 90:
                rows.setdefault("v1", set()).add(y)
            elif r > 150 and b > 150 and g < 90:
                rows.setdefault("v2", set()).add(y)
    check("the first voice is drawn in its own colour", "v1" in rows, sorted(rows))
    check("the second in its own", "v2" in rows, sorted(rows))
    if "v1" in rows and "v2" in rows:
        a, b = rows["v1"], rows["v2"]
        check("the colours differ, not one for both", a != b)
        check("the lines do not overlap", not (a & b),
              f"shared pixel rows: {len(a & b)}")
        check("the second line is below the first", min(b) > min(a),
              f"first y={min(a)}, second y={min(b)}")

    print("\nThe cover stands behind the lyrics, dark enough to read over")
    # A red cover: the backdrop must take its colour, stay dark, and blur away
    # every sharp edge — the words are what the frame is for.
    from PIL import Image as _Img
    import base64 as _b64
    import io as _io
    cbuf = _io.BytesIO()
    half = _Img.new("RGB", (320, 180), (230, 20, 20))
    half.paste(_Img.new("RGB", (160, 180), (20, 20, 230)), (160, 0))
    half.save(cbuf, "JPEG")
    cover_uri = "data:image/jpeg;base64," + _b64.b64encode(cbuf.getvalue()).decode()
    bgc = video.make_background(640, 360, cover_uri)
    px_l = bgc.getpixel((80, 180))
    px_r = bgc.getpixel((560, 180))
    check("the backdrop takes the cover's colours",
          px_l[0] > px_l[2] and px_r[2] > px_r[0], (px_l, px_r))
    check("and stays dark enough to read over",
          max(sum(bgc.getpixel((x, y))) for x, y in
              [(80, 60), (320, 180), (560, 300)]) < 330,
          [sum(bgc.getpixel(p2)) for p2 in [(80, 60), (320, 180), (560, 300)]])
    mid = bgc.getpixel((320, 180))
    check("the seam between the halves is blurred away",
          abs(int(mid[0]) - int(mid[2])) < 60, mid)
    check("a broken cover falls back to the gradient without a word",
          video.make_background(64, 36, "data:image/jpeg;base64,AAAA").getpixel((2, 2))
          == video.make_background(64, 36).getpixel((2, 2)))

    print("\nThe countdown aims at the singer's line")
    # A na-na-na in the gap is not the singer's cue: the dots and the pill both
    # skip backing lines when picking their target.
    q_lines = [
        {"text": "lead", "start": 2.0, "end": 4.0, "voice": 1, "words": []},
        {"text": "(na)", "start": 8.0, "end": 9.0, "voice": 2, "backing": True,
         "words": []},
        {"text": "(na again)", "start": 10.0, "end": 11.0, "voice": 2,
         "backing": True, "words": []},
        {"text": "next lead", "start": 20.0, "end": 22.0, "voice": 1, "words": []},
    ]
    check("the dots skip one backing line", video.next_sung(q_lines, 0) == 3)
    check("and a chain of them", video.next_sung(q_lines, 1) == 3)
    check("from before the first line too", video.next_sung(q_lines, -1) == 0)
    check("and past the end they say so", video.next_sung(q_lines, 3) == 4)

    print("\nThe countdown dots burn one per second")
    # Two at once and then the third — how it used to go — reads as a stutter,
    # not a countdown. The staircase must match the player's: 1, 2, 3.
    stair = [video.pips_lit(10.0, left) for left in (2.9, 1.9, 0.9)]
    check("in a long pause: one dot, then two, then three", stair == [1, 2, 3], stair)
    # a short pause is divided into thirds of ITSELF, so no dot is starved
    short = [video.pips_lit(2.6, left) for left in (2.4, 1.5, 0.5)]
    check("a short pause still counts in even thirds", short == [1, 2, 3], short)
    check("the second third begins where it should",
          video.pips_lit(2.6, 1.75) == 1 and video.pips_lit(2.6, 1.70) == 2,
          [video.pips_lit(2.6, 1.75), video.pips_lit(2.6, 1.70)])
    check("outside the window nothing burns",
          video.pips_lit(10.0, 3.4) == 0 and video.pips_lit(10.0, 0.0) == 0
          and video.pips_lit(1.0, 2.0) == 0)
    check("and it never jumps past three", video.pips_lit(10.0, 0.01) == 3)

    print("\nA duet frame: the backing smaller, to the right, off the dots")
    # The second voice used to draw at full size and land on the countdown
    # dots. Now the lead sits where a solo line sits, and the backing is
    # smaller, right-aligned, tucked under it like a reply.
    duet_song = {"colors": ["#00ff00", "#ff00ff"],
                 "theme": {"bg": "#000000", "text": "#ffffff"},
                 "data": {"title": "T", "duration": 20.0, "lines": [
                     {"text": "lead line here", "start": 5.0, "end": 9.0, "voice": 1,
                      "words": [{"w": "lead", "t": 5.0, "d": 1.3, "s": 1},
                                {"w": "line", "t": 6.3, "d": 1.3, "s": 1},
                                {"w": "here", "t": 7.6, "d": 1.3, "s": 1}]},
                     {"text": "(na-na-na)", "start": 5.5, "end": 10.5, "voice": 2,
                      "backing": True,
                      "words": [{"w": "(na-na-na)", "t": 5.5, "d": 5.0, "s": 3}]},
                     {"text": "next lead", "start": 12.0, "end": 14.0, "voice": 1,
                      "words": [{"w": "next", "t": 12.0, "d": 1.0, "s": 1},
                                {"w": "lead", "t": 13.0, "d": 1.0, "s": 1}]}]}}
    wavd = tone(os.path.join(tmp, "d.wav"), 220.0, 20.0)
    class AD:
        width, height, fps, crf = 640, 360, 5, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 5.8, 4.5, "minus", None
        output = os.path.join(tmp, "duet.mp4")
    video.render(duet_song, wavd, AD.output, AD())
    pngd = os.path.join(tmp, "duet.png")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", "1.0", "-i", AD.output,
                    "-frames:v", "1", pngd], check=True)
    imd = Image.open(pngd).convert("RGB")
    Wd, Hd = imd.size

    def ink_at(y0, y1, x0=0.0, x1=1.0):
        return sum(1 for y in range(int(Hd * y0), int(Hd * y1))
                   for x in range(int(Wd * x0), int(Wd * x1), 2)
                   if sum(imd.getpixel((x, y))) > 90)

    lead_ink = ink_at(0.38, 0.50)
    back_left = ink_at(0.50, 0.60, 0.0, 0.5)
    back_right = ink_at(0.50, 0.60, 0.5, 1.0)
    check("the lead is drawn where a solo line sits", lead_ink > 150, lead_ink)
    check("the backing is there, under it", back_left + back_right > 30,
          back_left + back_right)
    check("and it leans right, smaller than the lead",
          back_right > back_left * 1.5 and (back_left + back_right) < lead_ink,
          f"left {back_left}, right {back_right}, lead {lead_ink}")

    # …and when the lead ends but the na-na-na carries on, the backing keeps
    # its side seat instead of being promoted to the main one, full size, in
    # the way of the lead text.
    png_alone = os.path.join(tmp, "duet-alone.png")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", "3.9", "-i", AD.output,
                    "-frames:v", "1", png_alone], check=True)
    ima = Image.open(png_alone).convert("RGB")
    Wa, Ha = ima.size

    def ink_a(y0, y1, x0=0.0, x1=1.0):
        return sum(1 for y in range(int(Ha * y0), int(Ha * y1))
                   for x in range(int(Wa * x0), int(Wa * x1), 2)
                   if sum(ima.getpixel((x, y))) > 90)

    main_seat = ink_a(0.36, 0.48)
    side_left = ink_a(0.46, 0.58, 0.0, 0.5)
    side_right = ink_a(0.46, 0.58, 0.5, 1.0)
    check("with the lead gone, the main seat stays empty",
          main_seat < 40, main_seat)
    check("the lone backing still sits small to the right",
          side_right > 30 and side_right > side_left * 1.5,
          f"left {side_left}, right {side_right}")
    check("and the next lead still waits below",
          ink_a(0.58, 0.70) > 40, ink_a(0.58, 0.70))

    print("\nThe frame reads forward, not back")
    # The sung line is gone from the frame; the current line has the next one
    # under it and the one after that fainter still — a queue, not a history.
    frames_song = {"colors": ["#00ff00", "#ff00ff"],
                   "theme": {"bg": "#000000", "text": "#ffffff"},
                   "data": {"title": "T", "duration": 20.0, "lines": [
                       {"text": "spent line", "start": 1.0, "end": 3.0, "voice": 1,
                        "words": [{"w": "spent", "t": 1.0, "d": 1.0, "s": 1},
                                  {"w": "line", "t": 2.0, "d": 1.0, "s": 1}]},
                       {"text": "current one", "start": 5.0, "end": 8.0, "voice": 1,
                        "words": [{"w": "current", "t": 5.0, "d": 1.5, "s": 2},
                                  {"w": "one", "t": 6.5, "d": 1.5, "s": 1}]},
                       {"text": "coming next", "start": 9.0, "end": 11.0, "voice": 1,
                        "words": [{"w": "coming", "t": 9.0, "d": 1.0, "s": 2},
                                  {"w": "next", "t": 10.0, "d": 1.0, "s": 1}]},
                       {"text": "after that", "start": 12.0, "end": 14.0, "voice": 1,
                        "words": [{"w": "after", "t": 12.0, "d": 1.0, "s": 2},
                                  {"w": "that", "t": 13.0, "d": 1.0, "s": 1}]}]}}
    wavq = tone(os.path.join(tmp, "q.wav"), 220.0, 20.0)
    class AQ:
        width, height, fps, crf = 640, 360, 5, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 5.5, 2.0, "minus", None
        output = os.path.join(tmp, "queue.mp4")
    video.render(frames_song, wavq, AQ.output, AQ())
    pngq = os.path.join(tmp, "queue.png")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", "1.0", "-i", AQ.output,
                    "-frames:v", "1", pngq], check=True)
    imq = Image.open(pngq).convert("RGB")
    Wq, Hq = imq.size
    def band_ink(y0, y1):
        return sum(1 for y in range(int(Hq * y0), int(Hq * y1))
                   for x in range(0, Wq, 2) if sum(imq.getpixel((x, y))) > 90)
    top = band_ink(0.25, 0.40)          # where the spent line used to sit
    mainb = band_ink(0.40, 0.52)
    nextb = band_ink(0.55, 0.66)
    next2b = band_ink(0.67, 0.78)
    check("the sung line is gone from the frame", top < mainb * 0.15,
          f"top {top} vs main {mainb}")
    check("the current line is the brightest thing", mainb > 100, mainb)
    check("the next line waits under it", nextb > 40, nextb)
    check("and the one after that is present but fainter",
          0 < next2b < nextb, f"{next2b} vs {nextb}")

    print("\nThe quiet keep says so beside the line; the loud one stays silent")
    # “Sing along with the original” stands at the top right while a quiet
    # kept line is sung; a full-voice kept line gets no caption — the voice
    # itself says whose line it is.
    def tag_line(text, a, b):
        return {"text": text, "start": a, "end": b, "voice": 1,
                "words": [{"w": text, "t": a, "d": b - a, "s": 1}]}
    tags_song = {"colors": ["#00ff00", "#ff00ff"],
                 "theme": {"bg": "#000000", "text": "#ffffff"},
                 "data": {"title": "T", "duration": 16.0, "lines": [
        tag_line("sing along here", 2.0, 5.0), tag_line("original alone", 8.0, 11.0)]}}
    tags_song["data"]["lines"][0].update(keep=True, keepSoft=True)
    tags_song["data"]["lines"][1].update(keep=True)
    wavt = tone(os.path.join(tmp, "h.wav"), 220.0, 16.0)
    class ATG:
        width, height, fps, crf = 640, 360, 5, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 0.0, 12.0, "minus", None
        output = os.path.join(tmp, "tags.mp4")
    video.render(tags_song, wavt, ATG.output, ATG())

    def corner_ink(at):
        shot = os.path.join(tmp, f"tag-{at}.png")
        subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", str(at),
                        "-i", ATG.output, "-frames:v", "1", shot], check=True)
        imt = Image.open(shot).convert("RGB")
        Wt, Ht = imt.size
        return sum(1 for y in range(int(Ht * 0.28), int(Ht * 0.40))
                   for x in range(int(Wt * 0.55), Wt, 2)
                   if sum(imt.getpixel((x, y))) > 90)
    check("the sing-along caption stands beside the quiet kept line",
          corner_ink(3.0) > 15, corner_ink(3.0))
    check("and a full-voice kept line carries no caption",
          corner_ink(9.5) == 0, corner_ink(9.5))

    print("\nSyllables read as one word in the frame")
    # “ко=ло=ко=ла” is four timed pieces and one word on screen: the frame
    # must show no gaps between them, and never break a line inside a word.
    syl_song = {"colors": ["#00ff00", "#ff00ff"],
                "theme": {"bg": "#000000", "text": "#ffffff"},
                "data": {"title": "T", "duration": 12.0, "lines": [
        {"text": "колокола звенят", "start": 2.0, "end": 6.0, "voice": 1,
         "words": [{"w": "ко", "t": 2.0, "d": 1.0, "s": 1},
                   {"w": "ло", "t": 3.0, "d": 1.0, "s": 1, "g": True},
                   {"w": "ко", "t": 4.0, "d": 1.0, "s": 1, "g": True},
                   {"w": "ла", "t": 5.0, "d": 0.5, "s": 1, "g": True},
                   {"w": "звенят", "t": 5.5, "d": 0.5, "s": 2}]}]}}
    wavs = tone(os.path.join(tmp, "k.wav"), 220.0, 12.0)
    class ASY:
        width, height, fps, crf = 640, 360, 5, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 2.5, 1.0, "minus", None
        output = os.path.join(tmp, "syl.mp4")
    video.render(syl_song, wavs, ASY.output, ASY())
    shot_s = os.path.join(tmp, "syl.png")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", "0.3",
                    "-i", ASY.output, "-frames:v", "1", shot_s], check=True)
    ims = Image.open(shot_s).convert("RGB")
    Ws, Hs = ims.size
    # the gaps between ink columns inside the main line: one word means one
    # run of letters, with only a single wider gap before “звенят”
    cols = [x for x in range(Ws)
            if any(sum(ims.getpixel((x, y))) > 90
                   for y in range(int(Hs * 0.38), int(Hs * 0.52)))]
    gaps = [b - a for a, b in zip(cols, cols[1:]) if b - a > 1]
    wide = [g for g in gaps if g > Ws * 0.02]
    check("the syllables stand as one word, with one space before the next",
          len(wide) <= 1, f"gaps {sorted(gaps)[-4:]}, wide {wide}")

    print("\nEvery letter carries a dark ring, over any picture at all")
    # Until now the words were readable only because the backdrop was tame.
    # Put a near-white picture behind them, darkened barely at all, and the
    # old frame handed the singer grey letters on a grey wall. The ring is
    # what the eye holds on to, so it is measured here and not eyeballed.
    import base64 as _b64
    import io as _io
    bright = Image.new("RGB", (640, 360), (243, 240, 232))
    _bb = _io.BytesIO(); bright.save(_bb, "JPEG", quality=90)
    bright_uri = "data:image/jpeg;base64," + _b64.b64encode(_bb.getvalue()).decode()
    ring_words = "we sing until the glare gives in".split()
    ring_song = {"colors": ["#4de1ff", "#ff8ad1"],
                 "theme": {"bg": "#0a0b14", "text": "#e8ebf5"},
                 "cover": bright_uri, "coverDark": 20,
                 "data": {"title": "Bright", "duration": 12.0,
                          "cover": bright_uri, "coverDark": 20, "lines": [
        {"text": " ".join(ring_words), "start": 2.0, "end": 8.0, "voice": 1,
         "words": [{"w": w, "t": 2.0 + i * 0.75, "d": 0.75, "s": 1}
                   for i, w in enumerate(ring_words)]}]}}
    wav_r = tone(os.path.join(tmp, "r.wav"), 220.0, 12.0)

    class ARING:
        width, height, fps, crf = 640, 360, 5, 30
        preset, font, timings = "ultrafast", None, None
        start, seconds, audio = 0.0, 0.0, "minus"
        intro = False
        still = 4.5                      # mid-line: lit words and unlit ones
        output = os.path.join(tmp, "ring.png")
    video.render(ring_song, wav_r, ARING.output, ARING())
    rim = Image.open(ARING.output).convert("RGB")
    Wr, Hr = rim.size
    rp = rim.load()

    def _lum(c):
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    band = range(int(Hr * 0.36), int(Hr * 0.62))
    letters, around = [], []
    hot = video.COL_HOT
    for y in band:
        for x in range(Wr):
            if all(abs(rp[x, y][i] - hot[i]) < 30 for i in range(3)):
                letters.append((x, y))
    lset = set(letters)
    for x, y in letters:
        for dx in (-3, -2, 2, 3):
            q = (x + dx, y)
            if 0 <= q[0] < Wr and q not in lset:
                around.append(_lum(rp[q]))
    check("the sung words are found on the bright picture",
          len(letters) > 200, len(letters))
    ring_l = sum(around) / max(len(around), 1)
    check("and what touches them is dark, not the picture",
          ring_l < 105, f"{ring_l:.0f} of 255")
    # …and the picture really is bright where no words are, or the check above
    # would pass on a frame that is simply dark all over.
    far = [_lum(rp[x, y]) for y in range(int(Hr * 0.05), int(Hr * 0.16))
           for x in range(int(Wr * 0.55), Wr, 3)]
    open_l = sum(far) / max(len(far), 1)
    check("the picture behind is bright, so the ring earned it",
          open_l > 120, f"{open_l:.0f} of 255")

    print("\nThe beat, shown as a pulse in the corner")
    # A song that keeps one tempo can show it: four dots along the bottom, one
    # to a beat of the bar. It must read as a pulse and not a row of lamps —
    # bright on the beat, faded between two — and it must not appear at all
    # unless the singer asked for it.
    beat_words = "we come in on the beat now".split()
    beat_song = {"colors": ["#4de1ff", "#ff8ad1"],
                 "theme": {"bg": "#0a0b14", "text": "#e8ebf5"},
                 "grid": {"bpm": 120.0, "beat0": 0.0},   # a beat every half second
                 "data": {"title": "Pulse", "duration": 12.0, "lines": [
        {"text": " ".join(beat_words), "start": 2.0, "end": 8.0, "voice": 1,
         "words": [{"w": w, "t": 2.0 + i * 0.85, "d": 0.85, "s": 1}
                   for i, w in enumerate(beat_words)]}]}}
    wav_p = tone(os.path.join(tmp, "p.wav"), 220.0, 12.0)

    def corner(at, with_grid=True):
        class AP:
            width, height, fps, crf = 640, 360, 10, 30
            preset, font, timings = "ultrafast", None, None
            start, seconds, audio = 0.0, 0.0, "minus"
            intro = False
        a = AP(); a.still = at
        a.output = os.path.join(tmp, f"pulse-{at}-{int(with_grid)}.png")
        song = beat_song if with_grid else {k: v for k, v in beat_song.items()
                                            if k != "grid"}
        video.render(song, wav_p, a.output, a)
        im = Image.open(a.output).convert("RGB")
        Wp, Hp = im.size
        # the strip the dots live in: bottom edge, right half
        return im.crop((int(Wp * 0.6), int(Hp * 0.88), Wp, int(Hp * 0.96)))

    def brightest(strip):
        return max(sum(p) for p in strip.getdata())

    on_beat = brightest(corner(4.02))          # a beat has just struck
    off_beat = brightest(corner(4.35))         # well between two
    none_at_all = brightest(corner(4.02, with_grid=False))
    check("on the beat the corner lights up", on_beat > 300, on_beat)
    check("and between beats it falls back", off_beat < on_beat - 90,
          f"{on_beat} -> {off_beat}")
    check("without a tempo of its own the corner stays quiet",
          none_at_all < off_beat + 30, f"{none_at_all} vs {off_beat}")

    print("\nA clip may stand behind the lyrics, and the words still hold")
    # A backdrop that moves is the case a fixed darkening cannot serve: the
    # number that suited a dark shot blows out on the next cut. The clip here
    # cuts from near-black to near-white on purpose.
    clip_mp4 = os.path.join(tmp, "back.mp4")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error",
                    "-f", "lavfi", "-i", "color=c=0x101830:s=320x180:d=4",
                    "-f", "lavfi", "-i", "color=c=0xf6f2e8:s=320x180:d=6",
                    "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
                    "-map", "[v]", "-r", "8", clip_mp4], check=True)
    back_words = "we hold the line through all of it".split()
    back_song = {"colors": ["#4de1ff", "#ff8ad1"],
                 "theme": {"bg": "#0a0b14", "text": "#e8ebf5"},
                 "coverDark": 40,
                 "data": {"title": "Cut", "duration": 10.0, "coverDark": 40,
                          "lines": [
        {"text": " ".join(back_words), "start": 1.0, "end": 9.0, "voice": 1,
         "words": [{"w": w, "t": 1.0 + i * 1.1, "d": 1.1, "s": 1}
                   for i, w in enumerate(back_words)]}]}}
    wav_b = tone(os.path.join(tmp, "b2.wav"), 220.0, 10.0)

    def back_still(at, with_clip=True):
        class AB:
            width, height, fps, crf = 480, 270, 10, 30
            preset, font, timings = "ultrafast", None, None
            start, seconds, audio = 0.0, 0.0, "minus"
            intro = False
        a = AB(); a.still = at
        a.backdrop = clip_mp4 if with_clip else None
        a.output = os.path.join(tmp, f"back-{at}-{int(with_clip)}.png")
        video.render(back_song, wav_b, a.output, a)
        return Image.open(a.output).convert("RGB")

    def band_light(im):
        Wb, Hb = im.size
        strip = im.crop((0, int(Hb * 0.40), Wb, int(Hb * 0.76))).convert("L")
        return sum(strip.getdata()) / (strip.width * strip.height)

    dark_shot, bright_shot = back_still(2.0), back_still(7.0)
    check("the clip is really there: two moments are not the same picture",
          list(dark_shot.getdata()) != list(bright_shot.getdata()))
    lit = band_light(bright_shot)
    check("a white scene does not become a white wall behind the words",
          lit < 95, f"{lit:.0f} of 255")
    check("and a dark scene is not dragged darker still",
          band_light(dark_shot) < lit, f"{band_light(dark_shot):.0f}")
    # a clip that cannot be read is no backdrop, never a failed render
    broken = os.path.join(tmp, "notaclip.mp4")
    open(broken, "wb").write(b"this is not a video at all")
    class ABK:
        width, height, fps, crf = 480, 270, 10, 30
        preset, font, timings = "ultrafast", None, None
        start, seconds, audio = 0.0, 0.0, "minus"
        intro = False
        still = 2.0
        backdrop = broken
        output = os.path.join(tmp, "broken.png")
    try:
        video.render(back_song, wav_b, ABK.output, ABK())
        check("a clip that cannot be read is simply no backdrop",
              os.path.isfile(ABK.output))
    except Exception as e:
        check("a clip that cannot be read is simply no backdrop", False, e)

    print("\nA long line wraps instead of shrinking")
    # The line about the shown video shrank to letters read only from the
    # front row. It wraps onto a second row now — split between words — and
    # the sweep lights row after row; everything below yields.
    long_text = ("a line so long that it can never be laid out in one row "
                 "of a frame this size without shrinking away")
    lws = long_text.split()
    wrap_song = {"colors": ["#00ff00", "#ff00ff"],
                 "theme": {"bg": "#000000", "text": "#ffffff"},
                 "data": {"title": "T", "duration": 16.0, "lines": [
        {"text": long_text, "start": 2.0, "end": 10.0, "voice": 1,
         "words": [{"w": w, "t": 2.0 + i * 8.0 / len(lws), "d": 8.0 / len(lws),
                    "s": 1} for i, w in enumerate(lws)]},
        {"text": "short next", "start": 12.0, "end": 14.0, "voice": 1,
         "words": [{"w": "short next", "t": 12.0, "d": 2.0, "s": 2}]}]}}
    wav7 = tone(os.path.join(tmp, "g.wav"), 220.0, 16.0)
    class AW:
        width, height, fps, crf = 640, 360, 5, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 0.0, 12.0, "minus", None
        output = os.path.join(tmp, "wrap.mp4")
    video.render(wrap_song, wav7, AW.output, AW())
    shotw = os.path.join(tmp, "wrap.png")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", "6.0", "-i", AW.output,
                    "-frames:v", "1", shotw], check=True)
    imw = Image.open(shotw).convert("RGB")
    Ww, Hw = imw.size
    def rows_with_ink(y0, y1, lit=False):
        got = set()
        for y in range(int(Hw * y0), int(Hw * y1)):
            for x in range(0, Ww, 2):
                r, g, b = imw.getpixel((x, y))
                if (g > 120 and r < 90 and b < 90) if lit else (r + g + b > 90):
                    got.add(y)
                    break
        return sorted(got)
    seat = rows_with_ink(0.30, 0.60)
    check("the long line is drawn", len(seat) > 6, len(seat))
    breaks = sum(1 for a, b in zip(seat, seat[1:]) if b - a > 3)
    check("in two rows, with clear air between them", breaks >= 1,
          f"{len(seat)} ink rows, {breaks} gaps")
    # halfway through the line the first row is already lit
    lit_rows = rows_with_ink(0.30, 0.60, lit=True)
    check("and the sweep has lit the upper row by mid-line",
          lit_rows and lit_rows[0] == seat[0], f"lit from {lit_rows[:1]}, seat from {seat[:1]}")
    # nothing runs off the right edge any more
    edge = sum(1 for y in range(int(Hw*0.3), int(Hw*0.6))
               if sum(imw.getpixel((Ww - 4, y))) > 90)
    check("nothing runs off the edge of the frame", edge == 0, edge)

    print("\nAn overlapping line leaves when it is done, not when the next begins")
    # Line 39 dragged its last word past the start of line 40 — and vanished
    # mid-word the moment 40 began. The earlier line now holds the main seat
    # to its own end; the next one waits below, where it already stood.
    overlap_song = {"colors": ["#00ff00", "#ff00ff"],
                    "theme": {"bg": "#000000", "text": "#ffffff"},
                    "data": {"title": "T", "duration": 16.0, "lines": [
        {"text": "a very long first line that drags on", "start": 2.0, "end": 8.0,
         "voice": 1, "words": [
             {"w": "a", "t": 2.0, "d": 0.5, "s": 1},
             {"w": "very", "t": 2.5, "d": 0.5, "s": 1},
             {"w": "long first line that", "t": 3.0, "d": 2.0, "s": 5},
             {"w": "drags on", "t": 5.0, "d": 3.0, "s": 2}]},
        {"text": "tiny", "start": 7.0, "end": 10.0, "voice": 1,
         "words": [{"w": "tiny", "t": 7.0, "d": 3.0, "s": 1}]}]}}
    wav6 = tone(os.path.join(tmp, "f.wav"), 220.0, 16.0)
    class AO:
        width, height, fps, crf = 640, 360, 5, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 0.0, 12.0, "minus", None
        output = os.path.join(tmp, "overlap.mp4")
    video.render(overlap_song, wav6, AO.output, AO())

    def main_ink(at):
        shot = os.path.join(tmp, f"ov-{at}.png")
        subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", str(at),
                        "-i", AO.output, "-frames:v", "1", shot], check=True)
        imv = Image.open(shot).convert("RGB")
        Wv, Hv = imv.size
        return sum(1 for y in range(int(Hv * 0.38), int(Hv * 0.50))
                   for x in range(0, Wv, 2) if sum(imv.getpixel((x, y))) > 90)
    def side_ink(at):
        shot = os.path.join(tmp, f"ov-s-{at}.png")
        subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", str(at),
                        "-i", AO.output, "-frames:v", "1", shot], check=True)
        imv = Image.open(shot).convert("RGB")
        Wv, Hv = imv.size
        return sum(1 for y in range(int(Hv * 0.50), int(Hv * 0.62))
                   for x in range(int(Wv * 0.5), Wv, 2)
                   if sum(imv.getpixel((x, y))) > 90)
    inside = main_ink(7.5)        # both sound: the long one holds the seat
    held = main_ink(9.0)          # the long one ended, the short still sings:
    check("during the overlap the long line holds the main seat",
          inside > 200, inside)
    check("and it stays there to the end of the NEW line — the pair stands",
          held > 200, held)
    check("while the new line fills in the seat below",
          side_ink(9.0) > 15, side_ink(9.0))
    check("once the new line is done the pair breaks up",
          main_ink(11.0) < held // 2, f"{main_ink(11.0)} vs held {held}")
    # The mirror case: the long line CONTAINS the short one — the short must
    # keep its lower seat to the long one's end, not vanish at its own.
    contain_song = {"colors": ["#00ff00", "#ff00ff"],
                    "theme": {"bg": "#000000", "text": "#ffffff"},
                    "data": {"title": "T", "duration": 16.0, "lines": [
        {"text": "a very long line that keeps going and going", "start": 2.0,
         "end": 11.0, "voice": 1, "words": [
             {"w": "a very long line", "t": 2.0, "d": 4.0, "s": 4},
             {"w": "that keeps going and going", "t": 6.0, "d": 5.0, "s": 5}]},
        {"text": "short inside", "start": 6.0, "end": 8.0, "voice": 1,
         "words": [{"w": "short inside", "t": 6.0, "d": 2.0, "s": 2}]}]}}
    AO.output = os.path.join(tmp, "contain.mp4")
    video.render(contain_song, wav6, AO.output, AO())
    check("the contained line still sits below after its own end",
          side_ink(9.0) > 15, side_ink(9.0))
    check("and the long line still holds the main seat then",
          main_ink(9.0) > 200, main_ink(9.0))

    print("\nThree voices, two seats: the leads win, and the side seat wraps")
    # A backing line starting over a runover pair used to break the pair —
    # the first lead vanished mid-word. And a long line in the SIDE seat ran
    # off the edge of the frame: its base font sat below the shrink floor.
    triple = {"colors": ["#00ff00", "#ff00ff"],
              "theme": {"bg": "#000000", "text": "#ffffff"},
              "data": {"title": "T", "duration": 16.0, "lines": [
        {"text": "первый лид тянется и тянется", "start": 2.0, "end": 9.0,
         "voice": 1, "words": [
             {"w": "первый лид", "t": 2.0, "d": 3.0, "s": 2},
             {"w": "тянется и тянется", "t": 5.0, "d": 4.0, "s": 3}]},
        {"text": "второй лид врывается и он очень многословный длинный не влезает",
         "start": 7.0, "end": 12.0, "voice": 1, "words": [
             {"w": w, "t": 7.0 + i * 0.5, "d": 0.5, "s": 1} for i, w in
             enumerate("второй лид врывается и он очень многословный длинный не влезает".split())]},
        {"text": "(на-на)", "start": 8.0, "end": 10.0, "voice": 2,
         "backing": True,
         "words": [{"w": "(на-на)", "t": 8.0, "d": 2.0, "s": 1}]}]}}
    wav8 = tone(os.path.join(tmp, "i.wav"), 220.0, 16.0)
    class AT3:
        width, height, fps, crf = 640, 360, 5, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 0.0, 13.0, "minus", None
        output = os.path.join(tmp, "triple.mp4")
    video.render(triple, wav8, AT3.output, AT3())
    shot3 = os.path.join(tmp, "triple.png")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", "8.5",
                    "-i", AT3.output, "-frames:v", "1", shot3], check=True)
    im8 = Image.open(shot3).convert("RGB")
    W8, H8 = im8.size
    def band8(y0, y1, x0=0.0):
        return sum(1 for y in range(int(H8 * y0), int(H8 * y1))
                   for x in range(int(W8 * x0), W8, 2)
                   if sum(im8.getpixel((x, y))) > 90)
    check("the first lead still holds the main seat over the na-na-na",
          band8(0.30, 0.50) > 200, band8(0.30, 0.50))
    check("the second lead stands below it", band8(0.52, 0.70) > 50,
          band8(0.52, 0.70))
    edge8 = sum(1 for y in range(int(H8 * 0.3), int(H8 * 0.75))
                if sum(im8.getpixel((W8 - 3, y))) > 90)
    check("and nothing runs off the frame's edge", edge8 == 0, edge8)

    print("\nThe frame speaks the language of the song")
    # The countdown stands among the lyrics, not among the program's menus:
    # “END” over a Russian song is somebody else's caption pasted on.
    ru_song = {"data": {"lines": [{"text": "Пожелай мне удачи в бою"}]}}
    en_song = {"data": {"lines": [{"text": "Tear out my heart and soul"}]}}
    check("a Russian song is spoken to in Russian", video.frame_lang(ru_song) == "ru")
    check("an English one in English", video.frame_lang(en_song) == "en")
    check("and the page's own choice does not overrule the letters",
          video.frame_lang({"uiLang": "en",
                            "data": {"lines": [{"text": "Группа крови"}]}}) == "ru")
    check("with no letters to judge by, that choice stands",
          video.frame_lang({"uiLang": "ru", "data": {"lines": [{"text": "..."}]}}) == "ru")
    # A line named in the pill is cut at a word, never inside one.
    check("a long line is cut at a word and says so",
          video.short_line("We'll climb the mountains before we sleep")
          == "We'll climb the mountains before\u2026",
          video.short_line("We'll climb the mountains before we sleep"))
    check("a short line is left whole",
          video.short_line("Короткая строка") == "Короткая строка")
    check("a single endless word still gets its ellipsis",
          video.short_line("Одно" + "-длинное" * 6).endswith("\u2026"),
          video.short_line("Одно" + "-длинное" * 6))
    check("and the pill carries the cut line, not a broken word",
          "before\u2026" in video.pill_text(
              "en", 0, {"text": "We'll climb the mountains before we sleep"}, 5.0),
          video.pill_text("en", 0,
                          {"text": "We'll climb the mountains before we sleep"}, 5.0))
    ru_pill = video.pill_text("ru", -1, {"text": "Пожелай мне"}, 9.4)
    en_pill = video.pill_text("en", 5, None, 4.0)
    check("the intro pill is written the same way",
          ru_pill.startswith("ВСТУПЛЕНИЕ") and "до «Пожелай мне»" in ru_pill
          and "10 с" in ru_pill, ru_pill)
    check("and an English song ends in English",
          en_pill == "END   4 s   until the end", en_pill)

    print("\nThe dots count a wait, and the song ends on an empty stage")
    # Three dots under a line being sung, with the next line already in the
    # queue below, told the singer nothing. They belong to a real wait. And a
    # last line hanging lit to the end of the recording read as a frozen
    # picture: it stays a few seconds, then the stage empties.
    def one_line(text, a, b):
        return {"text": text, "start": a, "end": b, "voice": 1,
                "words": [{"w": text, "t": a, "d": b - a, "s": 1}]}
    ending = {"colors": ["#00ff00", "#ff00ff"],
              "theme": {"bg": "#000000", "text": "#ffffff"},
              "data": {"title": "T", "duration": 24.0, "lines": [
                  one_line("first line here", 1.0, 3.0),
                  one_line("second right after", 3.5, 5.5),
                  one_line("third after a pause", 12.0, 14.0)]}}
    wav3 = tone(os.path.join(tmp, "c.wav"), 220.0, 24.0)
    class A5:
        width, height, fps, crf = 640, 360, 5, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 0.0, 24.0, "minus", None
        output = os.path.join(tmp, "ending.mp4")
    video.render(ending, wav3, A5.output, A5())

    def band(at, y0, y1, lit=False):
        # `lit` counts only the dots that burn: a grey dot and a lit one are
        # both ink, and counting ink alone would call a countdown one that
        # never counts.
        shot = os.path.join(tmp, f"end-{at}.png")
        subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", str(at),
                        "-i", A5.output, "-frames:v", "1", shot], check=True)
        im5 = Image.open(shot).convert("RGB")
        W5, H5 = im5.size
        px = (im5.getpixel((x, y))
              for y in range(int(H5 * y0), int(H5 * y1)) for x in range(0, W5, 2))
        if lit:                       # the main voice's colour, #00ff00 here
            return sum(1 for r, g, b in px if g > 120 and r < 90 and b < 90)
        return sum(1 for c in px if sum(c) > 90)

    DOTS, SEAT = (0.50, 0.56), (0.38, 0.50)
    check("no dots under a line being sung with the next one close behind",
          band(2.0, *DOTS) == 0, band(2.0, *DOTS))
    check("but the singing itself is there", band(2.0, *SEAT) > 150, band(2.0, *SEAT))
    check("in a real wait the dots come up", band(6.5, *DOTS) > 20, band(6.5, *DOTS))
    check("far from the line none of them burns yet",
          band(6.5, *DOTS, lit=True) == 0, band(6.5, *DOTS, lit=True))
    check("and they are lit as the line comes in",
          band(11.5, *DOTS, lit=True) > 10, band(11.5, *DOTS, lit=True))
    check("the last line stays a few seconds after it is sung",
          band(16.0, *SEAT) > 150, band(16.0, *SEAT))
    check("and then the stage empties instead of freezing",
          band(20.0, *SEAT) == 0, band(20.0, *SEAT))

    print("\nThe intro countdown in the video")
    # The wait has to be a real one: a countdown is shown from ten seconds up,
    # because anything shorter is a breath between lines, not an interlude.
    intro = {"colors": ["#00ff00", "#ff00ff"], "theme": {"bg": "#000000", "text": "#ffffff"},
             "data": {"title": "T", "duration": 24.0, "lines": [
                 {"text": "aaa", "start": 13.0, "end": 16.5, "voice": 1,
                  "words": [{"w": "aaa", "t": 13.0, "d": 3.5, "s": 1}]}]}}
    wav2 = tone(os.path.join(tmp, "b.wav"), 220.0, 24.0)
    class A3:
        width, height, fps, crf = 640, 360, 5, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 0.0, 18.0, "minus", None
        output = os.path.join(tmp, "intro.mp4")
    video.render(intro, wav2, A3.output, A3())
    png2 = os.path.join(tmp, "intro.png")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", "3.0", "-i", A3.output,
                    "-frames:v", "1", png2], check=True)
    im2 = Image.open(png2).convert("RGB")
    W2, H2 = im2.size
    top = [im2.getpixel((x, y)) for y in range(int(H2 * 0.06), int(H2 * 0.20))
           for x in range(0, W2, 3)]
    lit = [c for c in top if sum(c) > 90]
    check("something is drawn at the top during the intro", len(lit) > 40, f"bright pixels: {len(lit)}")
    green = [c for c in top if c[1] > 120 and c[0] < 90 and c[2] < 90]
    check("the countdown bar has its own colour", len(green) > 5, f"green pixels: {len(green)}")
    # while singing there must be no pill
    png3 = os.path.join(tmp, "sing.png")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", "14.5", "-i", A3.output,
                    "-frames:v", "1", png3], check=True)
    im3 = Image.open(png3).convert("RGB")
    top3 = [im3.getpixel((x, y)) for y in range(int(H2 * 0.06), int(H2 * 0.20))
            for x in range(0, W2, 3)]
    # The text must sit in the centre of the pill, not cling to an edge.
    # Only the pill's own band is measured: above it, on the left, sits the song
    # title, and with it the centre of the “ink” would drift left.
    y0, y1 = int(H2 * 0.075), int(H2 * 0.155)
    rows = [y for y in range(y0, y1)
            for x in range(0, W2, 2) if sum(im2.getpixel((x, y))) > 90]
    cols = [x for y in range(y0, y1)
            for x in range(0, W2, 2) if sum(im2.getpixel((x, y))) > 90]
    if rows and cols:
        cx_ink = (min(cols) + max(cols)) / 2
        check("the pill is centred in the frame", abs(cx_ink - W2 / 2) <= W2 * 0.03,
              f"ink centre {cx_ink:.0f}, frame centre {W2/2:.0f}")
        # find the pill's own edges by its outline in the same band
        band = int((min(rows) + max(rows)) / 2)
        lit_x = [x for x in range(W2) if sum(im2.getpixel((x, band))) > 60]
        if lit_x:
            left_gap = min(lit_x)
            right_gap = W2 - max(lit_x)
            check("the pill has equal margins", abs(left_gap - right_gap) <= W2 * 0.02,
                  f"left {left_gap}, right {right_gap}")

    check("the pill disappears once singing starts", len([c for c in top3 if sum(c) > 90]) < len(lit) / 3,
          f"was {len(lit)}, now {len([c for c in top3 if sum(c) > 90])}")

    print("\nA line takes its seat in a breath, and the slideshow turns")
    # The queue line right after its arrival is mid-fade — dimmer than the
    # same line half a second later. And with a set of covers the background
    # under an early second differs from the one under a late second.
    fade_song = {"colors": ["#00ff00", "#ff00ff"],
                 "theme": {"bg": "#000000", "text": "#ffffff"},
                 "data": {"title": "T", "duration": 20.0, "lines": [
        {"text": "current", "start": 5.0, "end": 8.0, "voice": 1,
         "words": [{"w": "current", "t": 5.0, "d": 3.0, "s": 1}]},
        {"text": "coming next", "start": 12.0, "end": 14.0, "voice": 1,
         "words": [{"w": "coming next", "t": 12.0, "d": 2.0, "s": 1}]}]}}
    wavf = tone(os.path.join(tmp, "j.wav"), 220.0, 20.0)
    class AF:
        width, height, fps, crf = 640, 360, 10, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 4.8, 3.0, "minus", None
        output = os.path.join(tmp, "fade.mp4")
    video.render(fade_song, wavf, AF.output, AF())

    def next_ink(at):
        shot = os.path.join(tmp, f"fade-{at}.png")
        subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", str(at),
                        "-i", AF.output, "-frames:v", "1", shot], check=True)
        imf = Image.open(shot).convert("RGB")
        Wf, Hf = imf.size
        return sum(sum(imf.getpixel((x, y))) for y in
                   range(int(Hf * 0.55), int(Hf * 0.66))
                   for x in range(0, Wf, 2) if sum(imf.getpixel((x, y))) > 40)
    # The point of the fades is that a line change never blanks the frame:
    # before them both ends started from nothing and the picture flashed.
    def whole_ink(at):
        shot = os.path.join(tmp, f"whole-{at}.png")
        subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", str(at),
                        "-i", AF.output, "-frames:v", "1", shot], check=True)
        imw2 = Image.open(shot).convert("RGB")
        Ww2, Hw2 = imw2.size
        return sum(1 for y in range(int(Hw2 * 0.30), int(Hw2 * 0.80))
                   for x in range(0, Ww2, 2) if sum(imw2.getpixel((x, y))) > 90)
    through = [whole_ink(round(0.2 + i * 0.1, 1)) for i in range(8)]
    check("the frame never goes blank while the lines change over",
          min(through) > 0, through)
    # The column rides: through a line change the text is found at heights it
    # never rests at, and the line leaving the top is gone by the end of it.
    def top_row(at):
        shot = os.path.join(tmp, f"ride-{at}.png")
        subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", str(at),
                        "-i", AF.output, "-frames:v", "1", shot], check=True)
        imr = Image.open(shot).convert("RGB")
        Wr, Hr = imr.size
        for y in range(int(Hr * 0.10), int(Hr * 0.98)):
            if any(sum(imr.getpixel((x, y))) > 110 for x in range(0, Wr, 3)):
                return y
        return -1
    rest = top_row(1.4)                    # long settled
    riding = [top_row(round(0.2 + i * 0.05, 2)) for i in range(4)]
    check("mid-change the column stands where it never rests",
          any(r >= 0 and abs(r - rest) > 4 for r in riding),
          f"settled {rest}, riding {riding}")
    check("and it comes to rest at its own place",
          all(abs(top_row(at) - rest) <= 1 for at in (1.4, 1.8)),
          f"{rest} / {top_row(1.8)}")

    # the slideshow: two covers, two different grounds
    import base64 as _b64
    import io as _io
    def uri_of(rgb):
        b = _io.BytesIO()
        Image.new("RGB", (32, 18), rgb).save(b, "JPEG")
        return "data:image/jpeg;base64," + _b64.b64encode(b.getvalue()).decode()
    slide_song = dict(fade_song)
    slide_song = json.loads(json.dumps(fade_song))
    slide_song["covers"] = [uri_of((200, 30, 30)), uri_of((30, 30, 200))]
    AF.output = os.path.join(tmp, "slide.mp4")
    AF.start, AF.seconds = 0.0, 20.0
    AF.fps = 4
    video.render(slide_song, wavf, AF.output, AF())
    def ground(at):
        shot = os.path.join(tmp, f"slide-{at}.png")
        subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", str(at),
                        "-i", AF.output, "-frames:v", "1", shot], check=True)
        imf = Image.open(shot).convert("RGB")
        return imf.getpixel((imf.width // 2, int(imf.height * 0.9)))
    g1, g2 = ground(2.0), ground(18.0)
    check("the ground turns with the song: red first, blue later",
          g1[0] > g1[2] and g2[2] > g2[0], f"{g1} → {g2}")

    print("\nThe song's name is readable and clear of the countdown")
    # The name grew from caption size to its own font — and the pill moved
    # down. Neither may lean on the other: not one pixel row is shared.
    named = {"colors": ["#00ff00", "#ff00ff"], "theme": {"bg": "#000000", "text": "#ffffff"},
             "title": "Forevermore — Lorna Shore",
             "data": {"title": "Forevermore", "artist": "Lorna Shore",
                      "duration": 24.0, "lines": [
                 {"text": "Первая строка после долгого ожидания",
                  "start": 13.0, "end": 16.5, "voice": 1,
                  "words": [{"w": "Первая", "t": 13.0, "d": 3.5, "s": 1}]}]}}
    class A4:
        width, height, fps, crf = 1280, 720, 5, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 3.0, 1.0, "minus", None
        output = os.path.join(tmp, "named.mp4")
    video.render(named, wav2, A4.output, A4())
    png4 = os.path.join(tmp, "named.png")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", "0.5", "-i", A4.output,
                    "-frames:v", "1", png4], check=True)
    im4 = Image.open(png4).convert("RGB")
    W4, H4 = im4.size
    # The name lives at the left edge, the pill's tail in the right half.
    # The strips stay far apart on the x axis too: a wide pill reaches well
    # into the left third, and must not be mistaken for the name.
    t_rows = [y for y in range(0, int(H4 * 0.12))
              for x in range(int(W4 * 0.04), int(W4 * 0.18), 2)
              if sum(im4.getpixel((x, y))) > 90]
    p_rows = [y for y in range(0, int(H4 * 0.25))
              for x in range(int(W4 * 0.55), int(W4 * 0.96), 2)
              if sum(im4.getpixel((x, y))) > 90]
    check("the name is drawn large enough to read",
          t_rows and (max(t_rows) - min(t_rows)) >= H4 * 0.017,
          f"name rows span {max(t_rows) - min(t_rows) if t_rows else 0}px of {H4}")
    check("the name and the pill do not touch",
          t_rows and p_rows and max(t_rows) < min(p_rows) - H4 * 0.008,
          f"name ends {max(t_rows) if t_rows else '—'}, pill starts {min(p_rows) if p_rows else '—'}")

    print("\nThe clip opens with the name and a count of three")
    # A karaoke that starts on the first frame catches everybody mid-breath.
    class AI:
        width, height, fps, crf = 480, 270, 4, 30
        preset, font = "ultrafast", None
        intro = True
        start, seconds, audio, timings = 0.0, 12.0, "minus", None
        output = os.path.join(tmp, "opening.mp4")
    class NoIntro(AI):
        intro = False
    check("the opening is the card and the count", video.intro_lead(AI(), "Name") == 6.0,
          video.intro_lead(AI(), "Name"))
    check("a nameless song is only counted in", video.intro_lead(AI(), "") == 3.0,
          video.intro_lead(AI(), ""))
    check("and it can be turned off altogether",
          video.intro_lead(NoIntro(), "Name") == 0.0, video.intro_lead(NoIntro(), "Name"))

    # No artist here on purpose: on the card the artist's name rides just
    # under the song's, in the very row where the first waiting line stands
    # during the count — and the two phases could then not be told apart by
    # their bands. That the artist is drawn is plain in any rendered card.
    opening = {"colors": ["#00ff00", "#ff00ff"],
               "theme": {"bg": "#000000", "text": "#ffffff"},
               "data": {"title": "Named Song", "duration": 12.0, "lines": [
                   one_line("the first line of it", 7.0, 10.0)]}}
    wav4 = tone(os.path.join(tmp, "d.wav"), 220.0, 12.0)
    video.render(opening, wav4, AI.output, AI())
    check("the clip grew by the opening, and by exactly that much",
          abs(AU.duration(AI.output) - 18.0) < 0.35, AU.duration(AI.output))

    # Two bands: the seat where the name and then the count stand, and the
    # queue below it where the words wait.
    SEAT_B, WORDS_B = (0.38, 0.50), (0.55, 0.78)

    def mid_ink(at, band=(0.30, 0.75), lit=False):
        # `lit` counts only what is being sung right now: before the song a
        # frame legitimately holds the coming line, dim, in the queue — ink
        # that says nothing about whether anybody has started singing.
        shot = os.path.join(tmp, f"open-{at}.png")
        subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", str(at),
                        "-i", AI.output, "-frames:v", "1", shot], check=True)
        imo = Image.open(shot).convert("RGB")
        Wo, Ho = imo.size
        px = (imo.getpixel((x, y))
              for y in range(int(Ho * band[0]), int(Ho * band[1]))
              for x in range(0, Wo, 2))
        if lit:
            return sum(1 for r, g, b in px if g > 120 and r < 90 and b < 90)
        return sum(1 for c in px if sum(c) > 110)

    check("the name stands large on the opening card",
          mid_ink(1.0, SEAT_B) > 200, mid_ink(1.0, SEAT_B))
    check("and the card holds nothing but the name",
          mid_ink(1.0, WORDS_B) == 0, mid_ink(1.0, WORDS_B))
    check("then the count takes its place", mid_ink(4.5, SEAT_B) > 10,
          mid_ink(4.5, SEAT_B))
    check("small enough to be a figure, not a poster",
          mid_ink(4.5, SEAT_B) * 3 < mid_ink(1.0, SEAT_B),
          f"{mid_ink(4.5, SEAT_B)} against the name's {mid_ink(1.0, SEAT_B)}")
    check("and the words are already there to be read while it counts",
          mid_ink(4.5, WORDS_B) > 40, mid_ink(4.5, WORDS_B))
    # The song itself is pushed back by the opening: what used to happen at 8 s
    # now happens at 14 s, and the sound waits with it.
    check("the singing arrives after the opening, not during it",
          mid_ink(14.0, lit=True) > 20 and mid_ink(8.0, lit=True) == 0,
          f"{mid_ink(14.0, lit=True)} lit at 14 s, {mid_ink(8.0, lit=True)} at 8 s")

    heard = os.path.join(tmp, "opening.wav")
    subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-i", AI.output,
                    "-ac", "1", "-ar", "8000", heard], check=True)
    with wave.open(heard) as fh:
        sr_o = fh.getframerate()
        pcm = array.array("h")
        pcm.frombytes(fh.readframes(fh.getnframes()))

    def loud(t0, t1):
        seg = pcm[int(t0 * sr_o):int(t1 * sr_o)]
        return math.sqrt(sum(x * x for x in seg) / max(len(seg), 1))

    check("the music holds back while the count runs", loud(0.5, 5.5) < 20, loud(0.5, 5.5))
    check("and comes in when the count is done", loud(7.0, 11.0) > 200, loud(7.0, 11.0))

    print("\nThe backing does not keep the ending to itself")
    # The last sound is not always the last line in the list: a na-na-na is
    # written under the lead it answers, and a lead can outlast a backing that
    # started later. Asking the list which line is last left the backing
    # hanging alone at the end — and blanked a lead that was still singing.
    tail = {"colors": ["#00ff00", "#ff00ff"],
            "theme": {"bg": "#000000", "text": "#ffffff"},
            "data": {"title": "T", "duration": 24.0, "lines": [
                dict(one_line("then she said she liked", 7.0, 10.0)),
                dict(one_line("(na-na-na)", 9.0, 12.0), voice=2, backing=True)]}}
    wav5 = tone(os.path.join(tmp, "e.wav"), 220.0, 24.0)
    class AT:
        width, height, fps, crf = 480, 270, 4, 30
        preset, font = "ultrafast", None
        intro = False
        start, seconds, audio, timings = 0.0, 24.0, "minus", None
        output = os.path.join(tmp, "tail.mp4")
    video.render(tail, wav5, AT.output, AT())

    def tail_ink(at):
        shot = os.path.join(tmp, f"tail-{at}.png")
        subprocess.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", str(at),
                        "-i", AT.output, "-frames:v", "1", shot], check=True)
        imt = Image.open(shot).convert("RGB")
        Wt, Ht = imt.size
        return sum(1 for y in range(int(Ht * 0.30), int(Ht * 0.75))
                   for x in range(0, Wt, 2) if sum(imt.getpixel((x, y))) > 110)

    check("the lone backing is still there just after it is sung",
          tail_ink(13.5) > 20, tail_ink(13.5))
    check("and the stage empties five seconds after the backing, not the lead",
          tail_ink(17.5) == 0, tail_ink(17.5))

    # …and the mirror case: the backing is written last but ends first, while
    # the lead sings on. Nothing may be blanked while a voice is sounding.
    outlast = {"colors": ["#00ff00", "#ff00ff"],
               "theme": {"bg": "#000000", "text": "#ffffff"},
               "data": {"title": "T", "duration": 24.0, "lines": [
                   dict(one_line("a lead that carries on and on", 7.0, 20.0)),
                   dict(one_line("(na-na)", 9.0, 11.0), voice=2, backing=True)]}}
    AT.output = os.path.join(tmp, "outlast.mp4")
    video.render(outlast, wav5, AT.output, AT())
    check("a lead that outlasts its backing keeps singing on screen",
          tail_ink(19.0) > 20, tail_ink(19.0))

    print("\nColours do not collapse into an empty frame")
    dark = {"colors": ["#050505", "#0a0a0a"], "theme": {"bg": "#000000", "text": "#050505"},
            "data": payload["data"]}
    video.apply_colors(dark)
    def contrast(c):
        return video._contrast(c, video.BG_TOP)
    check("the first voice is visible against the background", contrast(video.COL_HOT) >= 2.4,
          f"{video.COL_HOT} on {video.BG_TOP}: {contrast(video.COL_HOT):.1f}")
    check("so is the second one", contrast(video.COL_HOT2) >= 2.4,
          f"{video.COL_HOT2}: {contrast(video.COL_HOT2):.1f}")
    check("unsung lines are distinguishable", contrast(video.COL_DIM) >= 2.0,
          f"{video.COL_DIM}: {contrast(video.COL_DIM):.1f}")
    video.apply_colors(payload)          # возвращаем цвета проверки

    print("\nThe report before the video")
    class A2:
        width, height, fps, audio = 1920, 1080, 30, "minus"
    rep = video.video_report(payload, A2(), 8.0, 8.0)
    for what in ("Song", "Lines", "Together", "Original sings", "Colours", "Audio", "Frames"):
        check(f"the report has “{what}”", what in rep, rep.replace("\n", " | ")[:100])
    check("the second voice is mentioned", "second voice: 1" in rep, rep)
    check("it says the voices overlap", "1 place where" in rep, rep)
    check("the colours are named", "#00ff00" in rep and "#ff00ff" in rep, rep)
    from kstudio import i18n
    i18n.set_lang("ru")
    rep_ru = video.video_report(payload, A2(), 8.0, 8.0)
    check("in Russian as well", "Отчёт перед роликом" in rep_ru and "Одновременно" in rep_ru,
          rep_ru.replace("\n", " | ")[:80])
    i18n.set_lang("en")
    plain = {"data": {"lines": [{"text": "a", "start": 0, "end": 1, "words": []}]}}
    warn = video.video_report(plain, A2(), 8.0, 8.0)
    check("without its own colours the report warns", "!" in warn, warn.replace("\n", " | ")[:90])

    shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + ("FAILED: " + ", ".join(failures) if failures else "All checks passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
