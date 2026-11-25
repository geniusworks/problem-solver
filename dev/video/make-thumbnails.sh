#!/usr/bin/env bash
# Renders the videos' thumbnails (dev/video/thumbnails/<name>.html, 1280x720) with headless Chrome:
#   dev/video/make-thumbnails.sh
# Writes assets/video/problem-solver-<name>-thumbnail.png and assets/video/thumbnails.rendered-from,
# the sources' hashes, which dev/recompute_results.py --check compares with the current sources.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
profile="$(mktemp -d)"
trap 'rm -rf "$profile"' EXIT
for name in intro overview; do
  # The virtual time budget lets the web fonts load before the screenshot.
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --force-color-profile=srgb \
    --user-data-dir="$profile" --window-size=1280,720 --virtual-time-budget=8000 \
    --screenshot="$repo/assets/video/problem-solver-$name-thumbnail.png" \
    "file://$here/thumbnails/$name.html" >/dev/null 2>&1
  echo "Wrote assets/video/problem-solver-$name-thumbnail.png"
done
(cd "$repo" && shasum -a 256 dev/video/thumbnails/base.css dev/video/thumbnails/intro.html \
  dev/video/thumbnails/overview.html | awk '{print "sha256", $1, $2}') > "$repo/assets/video/thumbnails.rendered-from"
