#!/usr/bin/env bash
# Usage: ./process.sh input.m4a output_dir
# Requires: ffmpeg, python3 with numpy, scipy, noisereduce
set -euo pipefail
IN="$1"; OUT="${2:-output}"; HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT"; NAME="$(basename "${IN%.*}")"
ffmpeg -y -loglevel error -i "$IN" -ac 1 -ar 48000 "$TMP/in.wav"
python3 -W ignore "$HERE/remove_siren.py" "$TMP/in.wav" "$TMP/desiren.wav"
python3 -W ignore "$HERE/denoise.py" "$TMP/desiren.wav" "$TMP/dn.wav"
ffmpeg -y -loglevel error -i "$TMP/dn.wav" \
  -af "highpass=f=60,equalizer=f=3000:t=q:w=1:g=3,dynaudnorm=f=250:g=15:p=0.9:m=40:s=8,alimiter=limit=0.95:level=false" \
  "$TMP/enhanced.wav"
ffmpeg -y -loglevel error -i "$TMP/desiren.wav" -c:a aac -b:a 192k "$OUT/${NAME}_siren_removed_only.m4a"
ffmpeg -y -loglevel error -i "$TMP/enhanced.wav" -c:a aac -b:a 192k "$OUT/${NAME}_siren_removed_enhanced.m4a"
