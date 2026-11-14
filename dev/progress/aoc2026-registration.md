# AoC 2026 registration — draft, not yet registered

**Status (2026-11-14): draft for the maintainer's review.** The engineering below is built and
tested offline and has passed its end-to-end test on past puzzles from the experiment account,
test night included (below). Its decisions are made (the end); it becomes the registration once
the `--trials 3` pre-run check has run on the configurations as changed after the test night;
from then until the last 2026 trial is scored, nothing it names
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

- **A dedicated experiment account**, `problem-solver-aoc`, created by the maintainer on GitHub
  and used to log in to AoC (AoC stores the provider's ID, names, URL and image, so the identity
  names the project, not a person). It is the default for everything automated,
  in testing and in the event.
- **The maintainer's own account is never used by the harness.** Its inputs and accepted answers
  stay the oracle for the 2024–2025 ledger.
- **Every account has its own inputs**, so each account's data lives in its own workspace
  (`accounts/<name>/`, selected by `AOC_ACCOUNT`) with its own session variable in `.env`
  (`AOC_SESSION_<NAME>`). Nothing mixes inputs, answers, results, solutions or submission history
  across accounts, and nothing falls back from one account's session to another's.
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

Unattended, scheduled each night of the event (`nightly.py`, run by launchd from
`scripts/com.problem-solver.nightly.plist`, whose header gives the install, test-night and removal
steps). It starts at 02:00 PST, five hours after the
puzzle's release: there is no race to run, and the run does not take part in one. It refuses to
start without the experiment account and the network-denying sandbox.

1. Starts at 02:00 PST (the Mac is woken in time and kept awake while the run lasts). A session check fetches one page that needs a
   login and stops the run, loudly, if the session has expired.
2. Fetches the day's page and input once and caches them. If either is unavailable, the run stops
   and reports it; it never polls. The page is audited for text it hides (below).
3. Runs the registered Part 1 trials, recording every attempt's prompt, code and answer
   (`--include-replay`).
4. Runs the submission step (below). If Part 1 is accepted, scores the recorded Part 1 answers,
   fetches the page once more for Part 2 and repeats 3–4 for it, with the held-out test's two
   arms; the context arm is given a recorded Part 1 program that reproduces the accepted answer.
5. Writes a log and a one-page summary for the morning, and stops.

Each night also does what earlier nights left owed (trials a stopped run did not finish, a part
whose stated wait outlasted the night, a Part 2 unlocked late), and a run restarted the same
night resumes at the trial. A Part 1 accepted outside the submission step does not start Part 2.
A day whose page hides text runs its trials but submits nothing until the maintainer has read the
hidden text and released the day (`nightly.py --release-day N`); text that appears on the page
after a release holds the day again.

## Submitting

Submitting is a separate step after the trials and the only code that posts to AoC. The trials run
exactly as in 2024–2025: same harness, configurations and fingerprints, scored offline; the solve
loop never sees AoC's replies.

1. **Candidates:** every answer recorded for the part, pooled across trials and models,
   deduplicated; answers that passed the worked examples ranked by how many trials gave them.
2. **Per part:** at most 3 wrong submissions over the whole event, shared by all models and trials.
   Never the same answer twice, never inside a stated wait, and a margin on every wait.
3. **"Too high" or "too low"** only removes candidates it rules out; it is never shown to a model.
4. **Per night:** at most 6 submissions across all parts in any 20 hours, so a restarted run
   shares the night's budget. Any reply the parser does not recognise, a reply that never arrived,
   or AoC saying a part is solved when no acceptance is recorded halts every later step until
   the maintainer has looked (`nightly.py --clear-halt`). A wait AoC states gets a 30 s margin; a
   wait longer than 15 minutes ends the step for the night.
5. **Budget spent:** the part waits, `unverified`. It can be settled later by the maintainer
   solving it on the experiment account, or by one capped later attempt if new trials give a
   clearly supported new candidate.
6. **Accepted:** the answer is cached and nothing is posted for that part again. Every recorded
   answer, from any trial or model, is scored against it locally.
7. **Kill switch:** `SUBMIT_SOLUTIONS=false` stops all posting without touching the trials.

## Scoring

- An answer counts as solved only against the accepted answer. Answers never confirmed stay
  `unverified` and count as not solved, so the reported rates are lower bounds.
- No accepted answer is cached while a trial runs, so every configuration sets
  `require_oracle=false`: a part with no worked example to check is still attempted, and an
  attempt whose example fails is run on the full input anyway and its answer kept as
  `unverified`. The examples rank candidates and drive repair; they never discard an answer.
  With an accepted answer cached the setting changes nothing.
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
- Text the page hides never reaches a prompt: every reader of a cached page strips hidden
  elements, comments and invisible characters from the puzzle articles first, so a model sees what
  a reader sees (hover text already never reached it). The cached page keeps what AoC served. On
  the 37 cached 2024–2025 pages every prompt input is byte-identical with and without the
  stripping.
- Every prompt is saved; each day's page is checked for hidden or unusual content, and days with
  any are reported apart, with their submissions held until the maintainer has read it.

## Engineering before the freeze

Built 2026-11-13, each with the test that fails without it:

1. **The submission step** (`submission/`): candidate ranking, the per-part and per-night budgets,
   stated waits, no repeat answers, no posting after an acceptance, the kill switch, and a halt
   on anything unfamiliar; state written before each post and after each reply. Answers are
   posted only from a named account. Recorded answers are scored once one is accepted
   (`shared/experiment/rescore.py`). `tests/unit/test_submission.py`.
2. **Workspaces per account** (`AOC_ACCOUNT`, `shared/paths.py`): inputs, answers, results,
   solutions and submission history kept apart. A fetch is one request; a page served logged out
   raises instead of being cached; the session check is one request.
   `tests/unit/test_accounts.py`.
3. **The network-denying sandbox profile** (`execution.deny_network`, `shared/sandbox.py`), on
   every path that runs generated code, off by default. With it on, the 69-solution ledger
   re-verifies 69/69, and the `--trials 3` pre-run check with it on gave 6/6 (2024 d1, fingerprint
   `1ac712678732`, run `20261113T183412Z_m5pro-precheck-sandbox`).
   `tests/integration/test_network_sandbox.py`.
4. **The hidden-text audit** (`shared/page_audit.py`): hidden elements, comments, invisible
   characters and hover text in the puzzle articles; a day with any but hover text is reported
   apart and its submissions held. All but hover text is stripped before the prompt
   (`strip_hidden`). `tests/unit/test_page_audit.py`, `tests/unit/test_aoc_fetch_cache.py`.
5. **The nightly driver** (`nightly.py`, plan in `config/nightly.yaml`, launchd template in
   `scripts/`): session check, one fetch, trials resumable at the trial, submission, Part 2, log
   and summary. The wake and schedule are tested on the test night. `tests/unit/test_nightly.py`.

## End-to-end test on past puzzles

On the experiment account, 2026-11-13, run as the nightly run itself with the network-denying
sandbox on (`nightly.py --year 2024 --from-day 1 --day 1`, then `--year 2025 --from-day 9 --day 9`).
Its inputs and answers are new to the project, as 2026's will be.

- **2024 d1:** read, solved, posted, accepted, Part 2 unlocked, solved, posted, accepted, and
  nothing posted afterwards. Part 1 3 of 3 trials solved, Part 2 6 of 6; two posts, about 20
  minutes. It found the attempt logs written to the working directory's `years/` rather than the
  account's workspace; fixed the same day (`tests/unit/test_token_accounting.py`), before 2025 d9.
- **2025 d9:** Part 1 3 of 3 trials solved, Part 2 1 of 6, each accepted on its first post (the
  one Part 2 trial with an answer passed the worked example; no other answer was a candidate); about
  an hour. Attempt logs landed in the account's workspace only.
- **The wrong-answer path,** which 2025 d9 did not reach: the submission step posted fixed
  candidates `1` and `0` for 2025 d1 Part 1. AoC replied "That's not the right answer", with a
  one-minute wait and no too-high or too-low, to both; each was parsed as wrong with its wait,
  the second was posted 90 seconds after the first (the wait plus the 30-second margin), and a
  further step stopped at the night's cap of 6 posts. A repeated answer being refused, the bounds
  and the cap of 3 wrong per part are covered by `tests/unit/test_submission.py` only.
- **The test night,** 2026-11-14: launchd started a copy of the job at 11:00 on 2024 d2. Part 1
  3 of 3 trials solved, Part 2 3 of 6, each accepted on its first post; the job exited 0. The
  installed job's own 02:00 run that night found no puzzle open and exited 0. This Mac does not
  sleep (system sleep is off; only the display sleeps), so the 01:50 wake is a backup for a Mac
  that does, and was not exercised.
- **What the test night found:** all 3 cold Part 2 trials ended with no answer. With no accepted
  answer cached, the solver refused a part with no worked example it could check
  (`require_oracle`), and 2024 d2's Part 2 reuses Part 1's example, which the cold arm does not
  see. On the 37 cached 2024–2025 days, read offline, that refusal would have hit 3 Part 1s
  (nothing posted, Part 2 never unlocked) and, of the 35 Part 2s, 15 in the cold arm and 13 in
  the context arm, at least one arm on 20. The same default also dropped the full-input answer of
  any attempt whose worked example failed, so it could neither be posted nor scored. Every
  earlier run had an accepted answer cached, where neither happens. The nightly configurations
  now set `require_oracle=false` (below, "Scoring").

## Decisions

1. **Provider for the experiment account:** *decided 2026-11-13*, GitHub (`problem-solver-aoc`).
2. **Text the page hides:** *decided 2026-11-13*, stripped before the prompt, and the day's
   submissions held until the maintainer has read it (above, "Unseen pages, run unattended").
   Stripping leaves every 2024–2025 prompt unchanged.
3. **Models and trials:** *decided 2026-11-13*, the reference `qwen3.8:27b` alone, 3 trials of
   Part 1 and 3 of each Part 2 arm (`config/nightly.yaml`). A second model is added only if the
   pre-run check shows the night has room for it, and only before the freeze.
4. **The numbers in the budget:** *decided 2026-11-13*, 3 wrong per part and 6 per night
   (`config/resources.yaml`, `submission:`).

The session cookie is refreshed around 2026-11-29 and checked daily through the event.
