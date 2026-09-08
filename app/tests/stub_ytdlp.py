#!/usr/bin/env python3
"""A stand-in for yt-dlp, so the checks never touch the internet.

KARAOKE_STUB_AUDIO — the file it pretends to have downloaded.
KARAOKE_STUB_FAIL   — say what a dead link says, and fail the way yt-dlp fails.
KARAOKE_STUB_LOG    — a file to append one line per run to, so the checks can
                      see how many times it was asked and with which arguments.

A link with “fail” in it does the same thing, so that both endings can be
walked through against one running studio. A link with “reload” in it plays
the refusal YouTube gives a client it does not like: it fails for everyone
except the android player, exactly as the real site does. A link with
“locked” in it is refused by every client, the way an age-gated video is.
"""

import json
import os
import shutil
import sys

TITLE = "Stub Artist - Stub Song (Official Video)"


def main() -> int:
    args = sys.argv[1:]
    out = ""
    for i, a in enumerate(args):
        if a == "-o" and i + 1 < len(args):
            out = args[i + 1]
    folder = os.path.dirname(out) or "."
    url = args[-1] if args else ""
    log = os.environ.get("KARAOKE_STUB_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(" ".join(args) + "\n")

    if "reload" in url and "player_client=android" not in " ".join(args):
        print("[youtube] zzz123: Downloading webpage")
        print("ERROR: [youtube] zzz123: The page needs to be reloaded.",
              file=sys.stderr)
        return 1

    if "locked" in url:
        # The refusal an age-gated video gives — the same to every client, so
        # all four are asked and the person is told what to do about it.
        print("[youtube] zzz123: Downloading webpage")
        print("ERROR: [youtube] zzz123: Sign in to confirm your age. "
              "This video may be inappropriate for some users.",
              file=sys.stderr)
        return 1

    if os.environ.get("KARAOKE_STUB_FAIL") or "fail" in url:
        print("[youtube] zzz123: Downloading webpage")
        print("ERROR: [youtube] zzz123: Video unavailable. This video is private",
              file=sys.stderr)
        return 1

    src = os.environ.get("KARAOKE_STUB_AUDIO") or ""
    stem = "Stub_Artist_-_Stub_Song_[zzz123]"
    ext = os.path.splitext(src)[1] or ".m4a"
    dst = os.path.join(folder, stem + ext)
    print("[youtube] zzz123: Downloading webpage")
    print("[download]  50.0% of 3.00MiB at 1.00MiB/s ETA 00:01")
    if src and os.path.isfile(src):
        shutil.copyfile(src, dst)
    else:
        with open(dst, "wb") as f:
            f.write(b"\0" * 4096)
    print("[download] 100% of 3.00MiB in 00:02")
    if "--write-thumbnail" in args:
        # Real downloaders sometimes keep the original webp beside the
        # converted jpeg. Both are laid out, and the picker must not confuse
        # junk under a pretty extension with the picture.
        with open(os.path.join(folder, stem + ".webp"), "wb") as f:
            f.write(b"RIFF\x00\x00\x00\x00WEBPjunk-not-a-jpeg")
        # a 1x1 jpeg is a jpeg: the pipeline only moves it
        import base64
        tiny = base64.b64decode(
            "/9j/4AAQSkZJRgABAQEAAAAAAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
            "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
            "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AVN//2Q==")
        with open(os.path.join(folder, stem + ".jpg"), "wb") as f:
            f.write(tiny)
    if "--write-info-json" in args:
        with open(os.path.join(folder, stem + ".info.json"), "w", encoding="utf-8") as f:
            json.dump({"title": TITLE, "id": "zzz123", "duration": 21,
                       "artist": "Stub Artist", "track": "Stub Song"}, f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
