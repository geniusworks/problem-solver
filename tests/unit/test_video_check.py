"""recompute_results.py --check fails when a published video lags its script or scene page."""

import hashlib
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "dev" / "recompute_results.py"
spec = importlib.util.spec_from_file_location("recompute_results", SCRIPT)
recompute = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recompute)

SOURCES = ["dev/video/intro.json", "dev/video/intro.html"]


def video(tmp_path, monkeypatch, script, recorded_script):
    (tmp_path / "dev" / "video").mkdir(parents=True)
    (tmp_path / "assets" / "video").mkdir(parents=True)
    (tmp_path / "dev" / "video" / "intro.json").write_text(script)
    (tmp_path / "dev" / "video" / "intro.html").write_text("<p>6 of 20</p>")
    if recorded_script is not None:
        lines = [f"sha256 {hashlib.sha256(text.encode()).hexdigest()} {path}"
                 for path, text in zip(SOURCES, [recorded_script, "<p>6 of 20</p>"])]
        (tmp_path / "assets" / "video" / "problem-solver-intro.rendered-from").write_text("\n".join(lines) + "\n")
    monkeypatch.setattr(recompute, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(recompute, "VIDEOS", {"intro": SOURCES})
    monkeypatch.setattr(recompute, "THUMBNAILS", [])
    (tmp_path / "assets" / "video" / "thumbnails.rendered-from").write_text("")


def test_a_video_rendered_from_its_current_sources_passes(tmp_path, monkeypatch):
    video(tmp_path, monkeypatch, "[1]", "[1]")
    assert recompute.videos_rendered() == []


def test_an_edited_script_without_a_new_render_fails(tmp_path, monkeypatch):
    video(tmp_path, monkeypatch, "[2]", "[1]")
    assert recompute.videos_rendered()


def test_a_video_never_rendered_fails(tmp_path, monkeypatch):
    video(tmp_path, monkeypatch, "[1]", None)
    assert recompute.videos_rendered()


def thumbnails(tmp_path, monkeypatch, page, recorded_page):
    (tmp_path / "dev" / "video" / "thumbnails").mkdir(parents=True)
    (tmp_path / "assets" / "video").mkdir(parents=True)
    (tmp_path / "dev" / "video" / "thumbnails" / "intro.html").write_text(page)
    if recorded_page is not None:
        digest = hashlib.sha256(recorded_page.encode()).hexdigest()
        (tmp_path / "assets" / "video" / "thumbnails.rendered-from").write_text(
            f"sha256 {digest} dev/video/thumbnails/intro.html\n")
    monkeypatch.setattr(recompute, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(recompute, "VIDEOS", {})
    monkeypatch.setattr(recompute, "THUMBNAILS", ["dev/video/thumbnails/intro.html"])


def test_thumbnails_rendered_from_their_current_pages_pass(tmp_path, monkeypatch):
    thumbnails(tmp_path, monkeypatch, "<h1>2½</h1>", "<h1>2½</h1>")
    assert recompute.videos_rendered() == []


def test_an_edited_thumbnail_page_without_a_new_render_fails(tmp_path, monkeypatch):
    thumbnails(tmp_path, monkeypatch, "<h1>3</h1>", "<h1>2½</h1>")
    assert recompute.videos_rendered()


def test_thumbnails_never_rendered_fail(tmp_path, monkeypatch):
    thumbnails(tmp_path, monkeypatch, "<h1>2½</h1>", None)
    assert recompute.videos_rendered()
