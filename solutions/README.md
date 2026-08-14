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
| 2024 day 05 part 2 | 0 | 5502 | Hardcoded lookup table over example strings |

Day 3 Part 2 previously had a row in this table pointing at
`solutions/2024_day03_part2.py`, a file that did not exist. The code behind it is
preserved at `years/2024/day03/2024_day03_part2.py`.
