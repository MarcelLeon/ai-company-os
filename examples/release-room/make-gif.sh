#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: bash examples/release-room/make-gif.sh <input.mov|mp4> <output.gif>" >&2
  echo "Optional env: AICO_GIF_FPS=12 AICO_GIF_WIDTH=960" >&2
  exit 2
fi

input=$1
output=$2
fps=${AICO_GIF_FPS:-12}
width=${AICO_GIF_WIDTH:-960}

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required. On this machine it is usually available at /opt/homebrew/bin/ffmpeg." >&2
  exit 1
fi

if [[ ! -f "$input" ]]; then
  echo "Input video not found: $input" >&2
  exit 1
fi

mkdir -p "$(dirname "$output")"
palette=$(mktemp "${TMPDIR:-/tmp}/aico-release-room-palette.XXXXXX.png")
trap 'rm -f "$palette"' EXIT

filters="fps=${fps},scale=${width}:-1:flags=lanczos"

ffmpeg -y -i "$input" -vf "${filters},palettegen=stats_mode=diff" "$palette"
ffmpeg -y -i "$input" -i "$palette" \
  -lavfi "${filters}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  -loop 0 "$output"

echo "Wrote $output"
