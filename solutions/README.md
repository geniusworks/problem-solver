# Advent of Code Solutions Log

Every row in the verified table below has been **executed against the real puzzle input
and matched against the accepted AoC answer** stored in
`years/<year>/day<NN>/answers.json`.

Re-run the audit at any time:

```bash
venv/bin/python dev/verify_solutions.py
```

It exits non-zero if any recorded solution is wrong, errors, or cannot be verified.

## Verified solutions

| Year | Day | Part | Answer | LLM Model(s) | Recorded (UTC) | Solution File |
|------|-----|------|--------|--------------|----------------|---------------|
|2024|1|1|2970687|deepseek-coder:6.7b|2025-12-08 01:46:55 UTC|solutions/2024_day01_part1.py|
|2024|1|2|23963899|qwen2.5-coder:7b|2025-12-08 01:54:44 UTC|solutions/2024_day01_part2.py|
|2024|2|1|421|llama3.1:8b|2025-12-08 02:09:18 UTC|solutions/2024_day02_part1.py|
|2024|3|1|174561379|deepseek-coder:6.7b|2025-12-08 02:20:18 UTC|solutions/2024_day03_part1.py|
|2024|6|1|5331|qwen2.5-coder:7b|2026-08-12 17:29:53 UTC|solutions/2024_day06_part1.py|
|2024|10|1|482|qwen2.5-coder:7b|2026-08-13 01:35:39 UTC|solutions/2024_day10_part1.py|
|2024|11|1|229043|qwen2.5-coder:7b|2026-08-13 02:01:54 UTC|solutions/2024_day11_part1.py|
|2024|7|1|5702958180383|qwen3.5:9b|2026-08-13 10:28:20 UTC|solutions/2024_day07_part1.py|
|2024|4|1|2401|qwen3.5:9b|2026-08-13 15:50:49 UTC|solutions/2024_day04_part1.py|
|2024|5|1|5747|qwen3.5:9b|2026-08-13 17:44:18 UTC|solutions/2024_day05_part1.py|
|2024|7|2|92612386119138|qwen3.5:9b|2026-08-13 21:48:24 UTC|solutions/2024_day07_part2.py|
|2024|4|2|1822|qwen3.5:9b|2026-08-14 07:17:00 UTC|solutions/2024_day04_part2.py|
|2024|5|2|5502|qwen3-coder:30b|2026-08-16 15:52:34 UTC|solutions/2024_day05_part2.py|
|2024|6|2|1812|qwen3.8:27b|2026-08-16 22:01:27 UTC|solutions/2024_day06_part2.py|
|2024|8|1|423|qwen3.8:27b|2026-08-17 01:00:36 UTC|solutions/2024_day08_part1.py|
|2024|8|2|1287|qwen3.8:27b|2026-08-17 01:13:44 UTC|solutions/2024_day08_part2.py|
|2024|10|2|1094|qwen3.8:27b|2026-08-17 02:05:43 UTC|solutions/2024_day10_part2.py|
|2024|12|1|1546338|qwen3.8:27b|2026-08-17 02:22:25 UTC|solutions/2024_day12_part1.py|
|2024|12|2|978590|qwen3.8:27b|2026-08-17 02:36:20 UTC|solutions/2024_day12_part2.py|
|2024|14|1|228410028|qwen3.8:27b|2026-08-17 03:06:27 UTC|solutions/2024_day14_part1.py|
|2024|15|1|1577255|qwen3.8:27b|2026-08-17 03:17:10 UTC|solutions/2024_day15_part1.py|
|2024|13|1|37680|qwen3.8:27b|2026-08-17 04:02:52 UTC|solutions/2024_day13_part1.py|
|2024|9|1|6340197768906|qwen3.8:27b|2026-08-17 04:43:16 UTC|solutions/2024_day09_part1.py|
|2024|15|2|1597035|qwen3.8:27b|2026-08-17 06:18:23 UTC|solutions/2024_day15_part2.py|
|2024|13|2|87550094242995|qwen3.8:27b|2026-08-17 07:24:28 UTC|solutions/2024_day13_part2.py|
<!-- end verified rows -->

## Rejected — previously recorded as solved, verified wrong

These were accepted by the pre-oracle pipeline, whose acceptance criterion was only
"ran without crashing and printed something". They are kept in `solutions/rejected/`
and under `years/` as failure data for evaluating the verification harness.

| Problem | Claimed | Correct | Failure mode |
|---------|---------|---------|--------------|
| 2024 day 02 part 2 | 86 | 476 | Never removes a level; ignores the 1–3 delta rule entirely |
| 2024 day 03 part 2 | 0 | 106921067 | Hardcoded `if line == "<example>": return 48 else: return 0` |
| 2024 day 04 part 1 | 2344 | 2401 | Searches 4 directions, two of which are the same diagonal; strips `.` from the grid |
| 2024 day 05 part 2 | 0 | 5502 | Hardcoded lookup table over example strings — **now genuinely solved**, see below |

Day 3 Part 2 previously had a row in this table pointing at
`solutions/2024_day03_part2.py`, a file that did not exist. The code behind it is
preserved at `tests/fixtures/overfit/2024_day03_part2.py` (moved there from the
gitignored `years/` tree, which the solver overwrites — see below).

**Day 5 Part 2 has since been solved for real** (2026-08-16, `qwen3-coder:30b`,
a Kahn's-algorithm topological sort — the first model in this project to crack
it). Its row above is retained as the historical pre-oracle failure. The solve
briefly cost us that failure artifact: the stub lived only at
`years/2024/day05/2024_day05_part2.py`, which is gitignored *and* is where the
solver writes its canonical solution, so the successful run overwrote the
regression fixture for the overfit gate. It was **recovered** from a copy of the
pre-solve `years/` tree kept outside the repo, and re-verified as the genuine
artifact (the gate flags all three hardcoded example literals; the oracle scores
it `0` against `5502`). Both overfit fixtures now live under `tests/fixtures/`,
which is committed and outside the solver's write path.
