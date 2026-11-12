"""Render assets/social-preview.png from its HTML source and record which source it came from.

    venv/bin/python dev/render_social_preview.py

The card states published figures, so it is checked like README and RESULTS
(dev/recompute_results.py). The HTML is checked for the figures; this records
the HTML's hash beside the PNG, so the check also fails when the HTML changed
and the PNG was not rendered again.
"""

import hashlib
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HTML = REPO_ROOT / "assets" / "social-preview.html"
PNG = REPO_ROOT / "assets" / "social-preview.png"
RENDERED_FROM = REPO_ROOT / "assets" / "social-preview.rendered-from"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def source_hash() -> str:
    return hashlib.sha256(HTML.read_bytes()).hexdigest()


def main() -> int:
    subprocess.run(
        [CHROME, "--headless", "--hide-scrollbars", "--window-size=1280,640",
         "--virtual-time-budget=5000", f"--screenshot={PNG}", str(HTML)],
        check=True,
    )
    RENDERED_FROM.write_text(f"sha256 {source_hash()} assets/social-preview.html\n")
    print(f"rendered {PNG.relative_to(REPO_ROOT)} from {HTML.relative_to(REPO_ROOT)}")
    print("GitHub's link preview uses an uploaded copy: after merging, upload this PNG under the "
          "repo's Settings > General > Social preview.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
