#!/bin/sh

cd /app/share/dude || exit 1
exec python3 /app/share/dude/dude.py "$@"
