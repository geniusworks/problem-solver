# Plan: does the Part 1 context inform, or cue recall? — registered design, not yet run

**Status (2026-11-09): design only.** No code written, nothing run. Needs the maintainer's go, a
small harness change (below), and hand-checked text variants for ten problems.

## The question

Posing Part 2 with Part 1's statement raised single-draft solves from 6/20 to 19/19 on 2024 d19 p2
(the controlled A/B, `part2-prompt-omits-part1.md`) and from 2/53 to 29/37 on 13 other Part 2s the
reference had failed (`m5pro-rescan-part2-aoc.md`). The added text does two things at once. It
supplies the rules and input format, and it is the puzzle's published wording, which can cue
recall of solutions the model saw in training. The external claim, "missing context looked like a
capability limit", needs the first to carry the effect. The saved d19 drafts show the old prompt
failed for want of information (none of the 54 drafts that guessed the input format wrong was
correct); they do not show that the fix works by information alone.

## Arms

The corrected context is a bundle: Part 1's statement, its accepted answer, a Part 1 program, and
a preview of the input (`shared/problem_context.py`). Only the statement is published wording, so
the arms vary the statement and hold the rest fixed.

| arm | Part 1 statement | rest of the bundle | tests |
|---|---|---|---|
| **A0 cold** | none | none | baseline (`problem_context=legacy`) |
| **A1 verbatim** | published text | yes | the current default |
| **A2 paraphrase** | same rules, input format and worked example; new story, names and wording; example values changed and its answer recomputed with the verified Part 1 solution | yes | information without the published wording |
| **A3 cue only** | published text with the input-format description and worked example removed; title, story and distinctive phrasing kept | no | the recall cue without the information |

The Part 2 article is published wording in every arm, A0 included, so A3 measures the cue that
Part 1's text *adds*.

**Held constant across arms:** model `qwen3.8:27b`, `samples_per_model=1`, `temperature=0.7`,
`enable_thinking=false`, `enable_fallback_models=false`, the current `example_tests` and
`analysis_temperature`, one machine (`m5pro-64`), one Ollama version, arm order rotated within
each trial so drift cannot line up with an arm. Part 2 is posed directly in every arm, with the
verified Part 1 program where the bundle is used, so no arm depends on the trial solving Part 1
first (the rescan lost 5 of 45 trials to that gate).

**Cells (10):** 2024 d9, d11, d14, d16, d18, d19, d20, d22 p2; 2025 d2, d4 p2. Each was solved by
at most one single draft under the old prompt and by most drafts under the new one, so the arms
have room to differ in both directions.

## Size and time

3 trials per cell per arm, 30 Part 2 trials per arm, 120 in all. At the observed rates
(A0 about 5%, A1 about 85%), 30 per arm detects a 30-point difference with about 80% power at
one-sided α = 0.05 (80% against 50% needs 30 per arm; 5% against 30% needs 25). It cannot show
two arms are *equal*: the 95% interval on a difference at n = 30 is roughly ±20 points, so "A2
matches A1" is read as "within that interval", not as equivalence. Trials cluster by problem;
per-cell results are reported alongside the pooled rate.

Time on `m5pro-64`: a single-draft Part 2 trial took 91–250 s in the d19 A/B and the rescan; at
about 200 s, 120 trials is **about 7 GPU-hours**, run in two or three chunks, plus a `--trials 3`
plumbing check of the new arms on one cell first.

## Registered predictions and readings

Written before any run; rates are pooled over the 10 cells.

| outcome | reading |
|---|---|
| A2 within 15 points of A1, and A3 within 15 points of A0 | **information carries the effect.** The headline stands as stated. |
| A3 at least 25 points above A0 | **the published wording alone helps**, so recall contributes; the headline must say so. |
| A2 at least 25 points below A1 | **the wording matters beyond its information**; same consequence. |
| anything else | inconclusive at this size; report the intervals, do not restate the headline. |

## The clean confirmation: AoC 2026

Paraphrase removes the published wording but not the puzzle's structure, which a model may also
recall. Problems published after the model's training cutoff remove both. AoC 2026 opens
2026-12-01 with 12 days: run **A0 against A1** on each day's Part 2, single draft, 3 trials per
arm, once Part 1 is solved on the account (Part 2's text is only visible then). About 36 trials per
arm and about 4 GPU-hours spread over the event. **A1 at least 30 points above A0** on unseen
problems confirms that the context effect does not need recall; a gap under 15 points undercuts
the headline whatever the paraphrase arms showed.

## What it needs before running

- **Harness:** `problem_context` values for A2 and A3 that read a per-problem Part 1 text file,
  and a runner option that poses Part 2 without running Part 1 first. Both enter the fingerprint.
- **Text variants:** ten paraphrases and ten cue-only versions, drafted and then checked by hand
  against the original for preserved (A2) or removed (A3) information. They derive from AoC's
  text, so they live under `years/` (gitignored) like the originals, with their hashes recorded
  in the result write-up.
- **AoC 2026:** the submitter wired, or Part 1 solved by hand each day (`PLAN.md`, §5).
