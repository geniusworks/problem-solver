# AoC 2026 registration — draft, not yet registered

**Status (2026-11-12): draft for the maintainer's review.** Nothing here is built or run yet. It
becomes the registration when the open decisions at the end are made and the engineering below
has passed its end-to-end test; from then until the last 2026 trial is scored, nothing it names
changes. It covers the clean contamination test (`PLAN.md` §4b) and the run conditions for the
held-out Part 1 context test (`part2-context-heldout-plan.md`), whose design and readings are
registered there.

## What AoC 2026 measures

AoC 2026 opens 2026-12-01 (midnight EST, 21:00 PST), one puzzle a day to mid-December (12 days in
2025). Its puzzles are published after the training cutoff of every model registered here, so a
solve cannot come from recall. That makes it the clean test of what the 2024–2025 capability
results could not separate: ability from having seen the benchmark. The models are frozen by
digest, so a trial run in January is as clean as one run on the night: freshness depends on the
models, not on the date.

## The account

- **A dedicated experiment account**, created by the maintainer through one of the providers AoC
  offers (GitHub, Google, Twitter or Reddit; AoC stores the provider's ID, names, URL and image,
  so the identity names the project, not a person). It is the default for everything automated,
  in testing and in the event.
- **The maintainer's own account is never used by the harness.** Its inputs and accepted answers
  stay the oracle for the 2024–2025 ledger.
- **Every account has its own inputs**, so each account's data lives in its own workspace (its own
  `years/`) with its own session variable in `.env`. Nothing mixes inputs, answers or submission
  history across accounts.
- **One account for the whole event**, and every wait AoC states is respected. (A second account
  would have different inputs, so it would also be a different measurement.)
- **AoC's FAQ advises people not to use AI to solve the puzzles**, because the point is to learn
  by solving them. This project solves them for no one: it measures models on them, as it has on
  the 2024 and 2025 puzzles, without competing. The account joins
  no leaderboard, and the submission budget below keeps its load to a handful of requests a
  night.
- **Nothing from AoC is redistributed:** puzzle text and inputs stay out of git, as AoC asks.
  Results name puzzles by year, day and part and may link to them.

## Frozen before 2026-12-01

The models by digest, each with its release date and stated training cutoff; prompts,
configurations and fingerprints; Ollama version, machine and `requirements.lock`; the submission
policy below. No model released after 2026-12-01 is added, nothing is upgraded, and no setting is
tuned on a 2026 puzzle, until the last trial of 2026 is scored (possibly in early 2027). An
unplanned change is recorded as an instrument change and the affected results are reported apart.

## The nightly run

Unattended, scheduled each night of the event. It starts at 02:00 PST, five hours after the
puzzle's release: there is no race to run, and the run does not take part in one.

1. Starts at 02:00 PST (the Mac is woken in time). A session check fetches one page that needs a
   login and stops the run, loudly, if the session has expired.
2. Fetches the day's page and input once and caches them. If either is unavailable, the run stops
   and reports it; it never polls.
3. Runs the registered Part 1 trials, recording every attempt's prompt, code and answer
   (`--include-replay`).
4. Runs the submission step (below). If Part 1 is accepted, fetches Part 2 and repeats 3–4 for it,
   with the held-out test's two arms.
5. Writes a log and a one-page summary for the morning, and stops.

## Submitting

Submitting is a separate step after the trials and the only code that posts to AoC. The trials run
exactly as in 2024–2025: same harness, configurations and fingerprints, scored offline; the solve
loop never sees AoC's replies.

1. **Candidates:** every answer recorded for the part, pooled across trials and models,
   deduplicated; answers that passed the worked examples ranked by how many trials gave them.
2. **Per part:** at most 3 wrong submissions over the whole event, shared by all models and trials.
   Never the same answer twice, never inside a stated wait, and a margin on every wait.
3. **"Too high" or "too low"** only removes candidates it rules out; it is never shown to a model.
4. **Per night:** at most 6 submissions across all parts, and a stop on any reply the parser does
   not recognise.
5. **Budget spent:** the part waits, `unverified`. It can be settled later by the maintainer
   solving it on the experiment account, or by one capped later attempt if new trials give a
   clearly supported new candidate.
6. **Accepted:** the answer is cached and nothing is posted for that part again. Every recorded
   answer, from any trial or model, is scored against it locally.
7. **Kill switch:** `SUBMIT_SOLUTIONS=false` stops all posting without touching the trials.

## Scoring

- An answer counts as solved only against the accepted answer. Answers never confirmed stay
  `unverified` and count as not solved, so the reported rates are lower bounds.
- **Part 1 is the headline**: every day has one and every Part 1 is attempted.
- **Part 2 is reported given Part 1 was solved**, and compared with 2024–2025 computed the same
  way (Part 2 over the days where the model solved Part 1), from the existing data.
- **Days unlocked by the maintainer's hand-solved Part 1 are reported apart**, and the held-out
  context test excludes them: its context arm carries the model's own verified Part 1 program.
- Results are published per problem as well as in aggregate. The secondary measures registered in
  `PLAN.md` ("Beyond AoC", step 1), the worked examples' false accepts and false rejects, are
  reported on every attempt.

## Unseen pages, run unattended

AoC's FAQ says the puzzles are designed for humans, with "no consideration … made for whether AI
can or cannot solve a puzzle". Still, a new page can hold text a model misreads, or text the page
does not display, and its code runs unattended. The oracle is unaffected: such text can make a
model fail, never make a wrong answer count, and a failure it causes is itself a result. The run
is protected and audited:

- Generated code runs under a sandbox profile that denies network access, on top of the existing
  limits (`shared/sandbox.py`). Unattended runs of code written against an unseen puzzle are the
  less trusted case PLAN names.
- The parser's handling of text the page hides is decided before the freeze (open decision 2) and
  not changed during the event.
- Every prompt is saved; each day's page is checked for hidden or unusual content, and days with
  any are reported apart.

## Engineering before the freeze

Each with the test that fails without it:

1. The submitter wired as the separate step above: candidate ranking, the per-part and per-night
   budgets, stated waits, no repeat answers, no posting after an acceptance, the kill switch.
2. Workspaces per account: inputs, answers and submission history kept apart.
3. The network-denying sandbox profile; checked by re-verifying the 69-solution ledger and the
   `--trials 3` pre-run check.
4. The hidden-text handling chosen in open decision 2.
5. The nightly driver: schedule, wake, session check, resumable after a restart, log and summary.

## End-to-end test on past puzzles

On the experiment account, before the freeze, with the maintainer's go (it uses the GPU and posts
to AoC). Its inputs and answers are new to the project, as 2026's will be:

- **2024 d1** (6/6 in the recent pre-run checks): read, solve, submit, accepted, Part 2 unlocked,
  solved, cached, and nothing posted afterwards.
- **2025 d9** (Part 2 about one trial in three): the wrong-answer path, with the stated wait parsed
  and respected, a repeated answer refused, and the budget stopping at its cap.
- The schedule and wake are tested at an arbitrary hour on a test night.

## Open decisions

1. **Provider for the experiment account** (maintainer): GitHub, Google, Twitter or Reddit.
2. **Text the page hides:** stripped before the prompt, or kept as the page has it.
3. **Models and trials:** which models besides the reference `qwen3.8:27b`, and trials per part.
4. **The numbers in the budget:** 3 wrong per part and 6 per night are proposals.

The session cookie is refreshed around 2026-11-29 and checked daily through the event.
