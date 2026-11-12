"""recompute_results.py --check fails when the social card's PNG lags its HTML."""

import hashlib
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "dev" / "recompute_results.py"
spec = importlib.util.spec_from_file_location("recompute_results", SCRIPT)
recompute = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recompute)


def card(tmp_path, html, recorded):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "social-preview.html").write_text(html)
    if recorded is not None:
        (assets / "social-preview.rendered-from").write_text(f"sha256 {recorded} assets/social-preview.html\n")


def test_a_card_rendered_from_the_current_html_passes(tmp_path, monkeypatch):
    card(tmp_path, "<p>69</p>", hashlib.sha256(b"<p>69</p>").hexdigest())
    monkeypatch.setattr(recompute, "REPO_ROOT", tmp_path)
    assert recompute.social_card_rendered() == []


def test_an_edited_html_without_a_new_render_fails(tmp_path, monkeypatch):
    card(tmp_path, "<p>70</p>", hashlib.sha256(b"<p>69</p>").hexdigest())
    monkeypatch.setattr(recompute, "REPO_ROOT", tmp_path)
    assert recompute.social_card_rendered()


def test_a_card_never_recorded_fails(tmp_path, monkeypatch):
    card(tmp_path, "<p>69</p>", None)
    monkeypatch.setattr(recompute, "REPO_ROOT", tmp_path)
    assert recompute.social_card_rendered()
