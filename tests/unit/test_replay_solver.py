"""The replay's feedback hashes do not depend on where its temporary workspace happens to be."""

import asyncio
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "replay_solver", Path(__file__).resolve().parents[2] / "dev" / "replay_solver.py")
assert _spec and _spec.loader
replay_solver = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(replay_solver)

ATTEMPTS = [
    {"stage": "generate", "repair_iteration": 0, "draft_index": 0, "code": "def solve(): pass"},
    {"stage": "repair", "repair_iteration": 1, "draft_index": 0, "code": "def solve(): return 1"},
]


def _feedback_hash(workspace: Path) -> str:
    model = replay_solver.RecordedModel(ATTEMPTS, workspace)
    code = asyncio.run(model.generate_solution(None, 2025, 9))
    traceback = f'File "{workspace.resolve()}/tmp/2025_day09_part2.py", line 53, in solve'
    asyncio.run(model.improve_solution(code, None, feedback=traceback))
    return model.feedback[0][2]


def test_a_traceback_hashes_the_same_from_any_workspace(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    first.mkdir()
    second.mkdir()
    assert _feedback_hash(first) == _feedback_hash(second)


def test_the_rest_of_the_feedback_still_counts(tmp_path):
    model = replay_solver.RecordedModel(ATTEMPTS, tmp_path)
    code = asyncio.run(model.generate_solution(None, 2025, 9))
    asyncio.run(model.improve_solution(code, None, feedback=f"{tmp_path}/a.py line 1"))
    other = replay_solver.RecordedModel(ATTEMPTS, tmp_path)
    code = asyncio.run(other.generate_solution(None, 2025, 9))
    asyncio.run(other.improve_solution(code, None, feedback=f"{tmp_path}/a.py line 2"))
    assert model.feedback[0][2] != other.feedback[0][2]
