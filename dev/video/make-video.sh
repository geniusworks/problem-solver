#!/usr/bin/env bash
# Makes a narrated Problem Solver video from scratch: dev/video/make-video.sh <intro|overview> [voice]
# The script (<name>.json) is voiced by the local Phonon model in Ollama, its scenes (scenes.html)
# are drawn frame by frame in headless Chrome, and ffmpeg joins picture, narration, captions and
# chapters. A local whisper transcript of the finished soundtrack is compared with the script.
# Needs Ollama with phonon (localhost:11434), Google Chrome, Node 22+, ffmpeg, and whisper-cli with
# its small model for the transcript check. Nothing is installed and nothing leaves the machine.
#
# Writes assets/video/problem-solver-<name>.mp4, .srt, -chapters.txt, -transcript-check.txt and
# .rendered-from: the sources' hashes, which dev/recompute_results.py --check compares with the
# current sources, so an edited script or scene page without a new render fails CI.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
name="${1:?usage: make-video.sh <intro|overview> [voice]}"
voice="${2:-Preston}"
script="$here/$name.json"
[ -f "$script" ] || { echo "no script $script" >&2; exit 1; }
case "$name" in
  intro) title="Problem Solver: what this is" ;;
  overview) title="Problem Solver: the long version" ;;
  *) title="Problem Solver" ;;
esac
out="$repo/assets/video"
base="$out/problem-solver-$name"
mkdir -p "$out"
work="$(mktemp -d)"
trap '[ "${KEEP:-0}" = 1 ] && echo "working files in $work" || rm -rf "$work"' EXIT

echo "1/4 Narration in the voice $voice"
node "$here/voice.mjs" "$script" "$voice" "$work/audio"

echo "2/4 Drawing the scenes"
node "$here/record.mjs" "$script" "$work/audio/durations.json" "$work/frames" "$work/timeline.json"

echo "3/4 Putting picture, narration and captions together"
node "$here/assemble.mjs" "$script" "$title" "$work/frames" "$work/timeline.json" "$work/audio" "$work/video"
cp "$work/video.mp4" "$base.mp4"
cp "$work/video.srt" "$base.srt"
cp "$work/video-chapters.txt" "$base-chapters.txt"
(cd "$repo" && shasum -a 256 "dev/video/$name.json" dev/video/scenes.html | awk '{print "sha256", $1, $2}') > "$base.rendered-from"

echo "4/4 Checking the soundtrack against the script"
model="$HOME/Library/Application Support/superwhisper/ggml-small.bin"
if command -v whisper-cli >/dev/null 2>&1 && [ -f "$model" ]; then
  ffmpeg -v error -y -i "$base.mp4" -vn -ar 16000 -ac 1 "$work/heard.wav"
  whisper-cli -m "$model" -f "$work/heard.wav" -np -otxt -of "$work/heard" >/dev/null 2>&1
  node "$here/compare.mjs" "$script" "$work/heard.txt" > "$base-transcript-check.txt"
  head -1 "$base-transcript-check.txt"
else
  echo "whisper-cli or its model not found; skipped"
fi
echo "Wrote $base.mp4"
