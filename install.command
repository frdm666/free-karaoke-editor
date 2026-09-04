#!/bin/bash
# One-time setup: checks ffmpeg and installs the Python libraries.
cd "$(dirname "$0")" || exit 1

PY=""
# The setup writes down the Python it installed into. A double-clicked script
# and a terminal do not read the same profile, so “whichever python3 the shell
# offers” could be one interpreter here and another there — and everything
# installed by the setup was invisible to the program. What put the libraries
# on the disk is what opens the program.
MARK="app/.python-path"
if [ -r "$MARK" ]; then
  SAVED="$(head -n 1 "$MARK")"
  if [ -n "$SAVED" ] && "$SAVED" -c "" >/dev/null 2>&1; then PY="$SAVED"; fi
fi
if [ -z "$PY" ]; then
  for c in python3 python; do
    command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }
  done
fi
if [ -z "$PY" ]; then
  echo
  echo "  Python is not installed."
  echo "  Get it from https://python.org — or run:  brew install python"
  echo
  read -r -p "Press Enter to close…" _
  exit 1
fi

"$PY" app/tools/setup_check.py
echo
read -r -p "Press Enter to close…" _
