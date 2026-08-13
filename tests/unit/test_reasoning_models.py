"""Reasoning models split their output; reading only one field loses answers.

Ollama returns chain-of-thought in `thinking` and the answer in `response`. How
long a model reasons varies a lot run to run -- the same prompt produced 1.7k
characters of thinking once and 17k the next -- and when reasoning exhausts the
output budget, `response` comes back empty with done_reason == "length".

Reading only `response` scored qwen3.5:9b at 0 of 6 problems. That measured this
provider, not the model.
"""

from unittest.mock import patch

import pytest

from shared.llm.local import OllamaProvider


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    async def json(self):
        return self._payload

    async def text(self):
        return ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    def __init__(self, payload, status=200):
        self._payload = payload
        self._status = status

    def post(self, *args, **kwargs):
        return _FakeResponse(self._payload, self._status)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


async def _generate(payload, status=200):
    with patch("aiohttp.ClientSession", lambda **kw: _FakeSession(payload, status)):
        return await OllamaProvider(model="test-model").generate("prompt")


class TestReasoningModels:
    async def test_answer_is_preferred_over_reasoning(self):
        result = await _generate({"response": "the answer", "thinking": "musing"})

        assert result.content == "the answer"
        assert result.metadata["thinking_chars"] == len("musing")

    async def test_reasoning_is_used_when_the_budget_ran_out(self):
        """Models often write the code inside their reasoning; recover it."""
        code = "```python\ndef solve():\n    return 1\n```"

        result = await _generate(
            {"response": "", "thinking": code, "done_reason": "length"}
        )

        assert result.content == code
        assert result.metadata["done_reason"] == "length"

    async def test_extraction_still_works_off_the_reasoning_fallback(self):
        code_block = "```python\ndef solve():\n    return 7\n```"
        result = await _generate({"response": "", "thinking": code_block})

        extracted = OllamaProvider(model="m")._extract_code(result.content)

        assert extracted and "def solve" in extracted

    async def test_both_fields_empty_raises_with_the_reason(self):
        with pytest.raises(RuntimeError, match="done_reason=length"):
            await _generate({"response": "", "thinking": "", "done_reason": "length"})

    async def test_token_counts_are_recorded(self):
        """Cost accounting was stubbed at zero while the CLI was in use."""
        result = await _generate(
            {"response": "x", "eval_count": 110, "prompt_eval_count": 900}
        )

        assert result.metadata["eval_count"] == 110
        assert result.metadata["prompt_eval_count"] == 900

    async def test_tokens_helper_reads_metadata(self):
        result = await _generate(
            {"response": "x", "eval_count": 110, "prompt_eval_count": 900}
        )
        assert OllamaProvider._tokens(result) == (900, 110)

    async def test_tokens_helper_defaults_to_zero_when_absent(self):
        result = await _generate({"response": "x"})
        assert OllamaProvider._tokens(result) == (0, 0)

    async def _capture_payload(self, think):
        """Run generate() and return the JSON payload posted to Ollama."""
        sent = {}

        class _Capturing(_FakeSession):
            def post(self, *args, **kwargs):
                sent.update(kwargs.get("json", {}))
                return _FakeResponse(self._payload, self._status)

        with patch("aiohttp.ClientSession", lambda **kw: _Capturing({"response": "x"})):
            await OllamaProvider(model="m", think=think).generate("prompt")
        return sent

    async def test_think_flag_is_sent_when_disabled(self):
        # Reasoning models over-reason on these prompts; think=False makes them
        # emit code directly, so the flag must reach Ollama.
        sent = await self._capture_payload(think=False)
        assert sent.get("think") is False

    async def test_think_flag_absent_by_default(self):
        sent = await self._capture_payload(think=None)
        assert "think" not in sent

    async def test_non_200_is_reported(self):
        with pytest.raises(RuntimeError, match="HTTP 500"):
            await _generate({}, status=500)


class TestContextSizing:
    """Ollama silently truncates to ~2048 tokens unless num_ctx is set.

    Measured on a 7883-token prompt: prompt_eval_count was 2050 by default and
    7037 with num_ctx set. This solver's prompts run to ~6962 tokens, so every
    generation it ever made was produced from a truncated prompt -- the models
    were answering without having seen most of the problem.
    """

    @pytest.mark.parametrize("chars,minimum", [
        (6930, 8192),    # smallest real prompt
        (13480, 16384),  # median real prompt
        (27849, 16384),  # largest real prompt
    ])
    def test_real_prompt_sizes_get_enough_context(self, chars, minimum):
        size = OllamaProvider._context_size("x" * chars)

        assert size >= minimum
        # must exceed the prompt itself, or the tail is discarded
        assert size > chars // 3

    def test_headroom_is_left_for_the_answer(self):
        """Reasoning models need room to think *after* the prompt."""
        prompt = "x" * 12000
        size = OllamaProvider._context_size(prompt)

        assert size - (len(prompt) // 3) >= 4096

    def test_never_below_the_default_that_caused_truncation(self):
        assert OllamaProvider._context_size("short") >= 8192

    async def test_num_ctx_is_sent_to_ollama(self):
        captured = {}

        class _CapturingSession(_FakeSession):
            def post(self, url, json=None, **kw):
                captured.update(json or {})
                return _FakeResponse({"response": "ok"})

        with patch("aiohttp.ClientSession", lambda **kw: _CapturingSession({})):
            await OllamaProvider(model="m").generate("x" * 12000)

        assert captured["options"]["num_ctx"] >= 8192
