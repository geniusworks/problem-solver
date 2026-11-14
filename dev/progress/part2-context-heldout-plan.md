# Plan: does the Part 1 context inform, or cue recall? — registered design on AoC 2026, not yet run

**Status (2026-11-09): approved design; runs during AoC 2026** (opens 2026-12-01). Runs under
the AoC 2026 registration (`aoc2026-registration.md`, a draft), on its experiment account.

## The question

Posing Part 2 with Part 1's statement raised single-draft solves from 6/20 to 19/19 on 2024 d19 p2
(the controlled A/B, `part2-prompt-omits-part1.md`) and from 2/53 to 29/37 on 13 other Part 2s the
reference had failed (`m5pro-rescan-part2-aoc.md`). The added text does two things at once. It
supplies the rules and input format, and it is the puzzle's published wording, which can cue
recall of solutions the model saw in training. The external claim, "missing context looked like a
capability limit", needs the first to carry the effect. The saved d19 drafts show the old prompt
failed for want of information (none of the 54 drafts that guessed the input format wrong was
correct); they do not show that the fix works by information alone.

## Why public puzzles cannot answer it

The first design rewrote Part 1 on ten public Part 2s: a paraphrase (same information, new
wording) and a cue-only version (published wording, information removed). Writing the texts
showed that editing Part 1 cannot separate the two:

- **Part 2 depends on Part 1's text.** Its article uses Part 1's terms ("file", "block",
  "checksum" on 2024 d9) and often refers to, or reproduces, Part 1's worked example ("The first
  example from above now proceeds differently"). A paraphrase that renames the terms or changes
  the example makes the prompt inconsistent, which would lower its score for a reason other than
  recall; one that keeps them keeps the published cues in every arm.
- **Cue-only text is not information-free.** Removing the input format and example still leaves
  Part 1's rules, so a cue-only gain could be information as well as recall.

Rewriting both parts in full would avoid the first problem, but a model could still recognise a
puzzle's structure. Problems published after the model's training cutoff remove the cue entirely,
so the test runs there.

## Design

- **Problems:** the AoC 2026 Part 2s (12 days, opening 2026-12-01; days without a Part 2 are
  skipped), each run once a model's Part 1 answer is accepted on the experiment account, since Part 2's
  text is only visible then. Part 2s unlocked by a Part 1 the maintainer solved are excluded: the
  context arm carries the model's own verified Part 1 program.
- **Arms**, interleaved one trial at a time:
  - **cold:** `problem_context=legacy`, Part 2 posed with its own article only.
  - **with context:** `problem_context=aoc, gate_part_two=false`: Part 2 posed with Part 1's
    statement, its accepted answer, the verified Part 1 program and an input preview, without
    re-solving Part 1 in the trial.
- **Held constant:** `models=qwen3.8:27b, samples_per_model=1, temperature=0.7,
  enable_thinking=false, enable_fallback_models=false, require_oracle=false`, the current
  `example_tests` and `analysis_temperature`, one machine, one Ollama version (recorded in each result file).
- **Trials:** 3 per Part 2 per arm, about 33 per arm.
- **Scoring:** Part 2's accepted answer is unknown until it is submitted, so these runs record
  `unverified` with each attempt's answer; once the accepted answer is cached, the recorded
  answers are scored against it. Nothing is counted solved before then.
- **Primary outcome: the first draft.** A trial counts as solved by its first draft if the first
  implementation attempt produced the accepted answer. Repair rounds differ between the arms in
  more than the context (the example tests read off the page include Part 1's), so solve rates
  with repair are reported beside it, not tested.
- **Time:** about 250 s per single-draft Part 2 trial, so about 4.6 GPU-hours over the event.

## Registered readings

Written before any run; first-draft rates pooled over the Part 2s.

| outcome | reading |
|---|---|
| with context at least 30 points above cold | **confirms** that the context effect does not need recall: the headline stands |
| with context less than 15 points above cold | **undercuts** the headline: on public puzzles the gain was largely recall |
| anything else | inconclusive at this size; report the interval |
| with context solves fewer than 5 first drafts in all | the problem set is too hard for this model to inform; inconclusive |

Trials cluster by problem; per-problem results are reported alongside the pooled rate.
