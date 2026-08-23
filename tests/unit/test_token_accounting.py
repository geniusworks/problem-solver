"""Token accounting must be per-call, not carried over.

`improve_solution` (the repair path) called `generate()` and returned without
touching `last_token_usage`, so every repair attempt reported the counts of the
preceding `generate_solution()`. The tell was three attempts logging identical
(4283, 876) while returning different answers -- different generations cannot
have identical token counts
(dev/progress/ollama-0.32.14-runtime-check.md).

This matters because arm 2 of the project's thesis is an ECONOMIC claim
measured in tokens: repair-heavy pass@k costs were understated by however many
repair rounds ran.
"""

import types

import pytest

from shared.llm.local import OllamaProvider


class _Resp:
    def __init__(self, content, prompt_eval_count, eval_count):
        self.content = content
        self.metadata = {
            "prompt_eval_count": prompt_eval_count,
            "eval_count": eval_count,
        }


def _provider(monkeypatch, responses):
    """Provider whose generate() returns queued responses in order."""
    p = OllamaProvider(model="m", temperature=0.7)
    queue = list(responses)

    async def fake_generate(prompt, temperature=None):
        return queue.pop(0)

    monkeypatch.setattr(p, "generate", fake_generate)
    return p


class _Problem:
    description = "desc"
    examples: list = []
    final_question = "q"


@pytest.mark.asyncio
async def test_improve_solution_records_its_own_tokens(monkeypatch):
    p = _provider(monkeypatch, [_Resp("```python\ndef solve():\n    return 1\n```", 111, 22)])
    p.last_token_usage = {"input_tokens": 4283, "output_tokens": 876}  # stale, from a prior call

    await p.improve_solution("def solve():\n    return 0\n", _Problem(), feedback="wrong")

    assert p.last_token_usage == {"input_tokens": 111, "output_tokens": 22}, (
        "repair must report its own tokens, not the previous generation's"
    )


@pytest.mark.asyncio
async def test_consecutive_repairs_report_different_counts(monkeypatch):
    """The exact symptom: identical counts across attempts that differ."""
    p = _provider(monkeypatch, [
        _Resp("```python\ndef solve():\n    return 1\n```", 100, 10),
        _Resp("```python\ndef solve():\n    return 2\n```", 200, 20),
    ])

    await p.improve_solution("x", _Problem(), feedback="a")
    first = dict(p.last_token_usage)
    await p.improve_solution("y", _Problem(), feedback="b")
    second = dict(p.last_token_usage)

    assert first != second
    assert first == {"input_tokens": 100, "output_tokens": 10}
    assert second == {"input_tokens": 200, "output_tokens": 20}


@pytest.mark.asyncio
async def test_repair_honours_the_configured_temperature(monkeypatch):
    """Repair previously called generate() with no temperature, silently using
    the model default while every other call used the configured one."""
    seen = {}
    p = OllamaProvider(model="m", temperature=0.9)

    async def fake_generate(prompt, temperature=None):
        seen["temperature"] = temperature
        return _Resp("```python\ndef solve():\n    return 1\n```", 5, 5)

    monkeypatch.setattr(p, "generate", fake_generate)
    await p.improve_solution("x", _Problem(), feedback="f")

    assert seen["temperature"] == 0.9
