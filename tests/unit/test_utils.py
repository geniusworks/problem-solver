from datetime import datetime as RealDateTime

import shared.utils as utils


class _BaseFixedDateTime(RealDateTime):
    """Helper base class to override now() while preserving datetime API."""

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        # Subclasses must override _NOW
        return cls(*cls._NOW, tzinfo=tz)  # type: ignore[attr-defined]


def _set_now(monkeypatch, year: int, month: int, day: int) -> None:
    class FixedDateTime(_BaseFixedDateTime):  # type: ignore[misc]
        _NOW = (year, month, day, 0, 0, 0)

    monkeypatch.setattr(utils, "datetime", FixedDateTime)


def test_get_problem_year_day_december_2024_before_25(monkeypatch):
    """In Dec 2024, use the real day, capped at 25."""
    _set_now(monkeypatch, 2024, 12, 5)
    year, day = utils.get_problem_year_day()
    assert year == 2024
    assert day == 5


def test_get_problem_year_day_december_2025_before_12(monkeypatch):
    """In Dec 2025, use the real day, capped at 12."""
    _set_now(monkeypatch, 2025, 12, 5)
    year, day = utils.get_problem_year_day()
    assert year == 2025
    assert day == 5


def test_get_problem_year_day_december_2025_after_12(monkeypatch):
    """In late Dec 2025, cap the day at 12 for the 12-day event."""
    _set_now(monkeypatch, 2025, 12, 20)
    year, day = utils.get_problem_year_day()
    assert year == 2025
    assert day == 12


def test_get_problem_year_day_after_2025_uses_2025_with_12_days(monkeypatch):
    """In early 2026, treat most recent December as 2025 with 12 days."""
    _set_now(monkeypatch, 2026, 1, 10)
    year, day = utils.get_problem_year_day()
    assert year == 2025
    assert day == 12


def test_get_problem_year_day_after_2024_uses_full_25_days(monkeypatch):
    """In early 2025, treat most recent December as 2024 with 25 days."""
    _set_now(monkeypatch, 2025, 1, 10)
    year, day = utils.get_problem_year_day()
    assert year == 2024
    assert day == 25
