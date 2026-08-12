# Runtime-error categories (2024 d1–3, qwen2.5-coder:7b, 2 trials)

Enabled by "persist candidate failure reasons into `AttemptRecord.error`" (PR #7): the
error text is now in the result JSON, so the failures are categorisable from a normal run.
Run 2026-08-11, `dev/experiments/20260812T050958Z_error-diag_a888a46ad995.json` (gitignored).

20 attempts: **6 solved / 4 wrong / 10 error.**

## The 10 errors

| count | signature | nature |
|-------|-----------|--------|
| 3 | "Solution must contain a solve() function" | wrong entrypoint (see below) |
| 3 | `ValueError: invalid literal for int()` | parsing bug |
| 3 | `IndexError` | bounds bug |
| 1 | `NameError` (free variable) | scoping bug |

**None are harness or extraction bugs.** The extractor (D1) returns the model's code
correctly; these are genuine defects in what the model wrote.

### "no solve()" (30% of errors) — correct logic, wrong wrapper

The clearest, most fixable category. On day 3 the model produced *correct* logic but the
wrong shape: it named the function `sum_mul_instructions(corrupted_memory)` instead of
`solve`, and appended a hardcoded `corrupted_memory = "xmul(2,4)..."` **example block**
instead of a `solve()` that reads `input.txt`. The regex and the sum-of-products were
right; the harness contract was ignored. These are convention-following failures, not
reasoning failures — a candidate for prompt hardening ("define a function named exactly
`solve()` that reads `input.txt`; do not include example usage or hardcoded input").

### Parsing / bounds / scoping (70% of errors) — genuine bugs

- `int("90 91 93 96 93")` — read a whole day-2 line as one int instead of splitting it.
- `int("+mul(162,118)...")` — tried to int() day-3's raw corrupted memory instead of
  extracting the `mul()` calls.
- `IndexError`/`NameError` — ordinary implementation slips.

These are real 7B implementation misses. Two levers, both now measurable against the
attempt-level metric:

1. **Repair** — the loop now receives the exact traceback (PR #7). Whether it converts
   these errors into working code is the next thing to measure.
2. **Self-consistency sampling (Milestone E)** — N samples at temperature>0, run each,
   majority-vote on the *executed* answer. Discards the erroring candidates and outvotes
   the wrong ones; a correct candidate need appear only once. The data (candidates are
   produced freely but individually unreliable) is exactly the profile this technique is
   for, and the plan already flags it as the highest-value trick for weak models.

## Takeaway

Milestone D's generation-robustness work is essentially done at the extraction/measurement
layer: candidates are extracted (D1), their cost is counted (D2), and their failures are
legible (PR #7). What remains is candidate *quality*, which is a model problem best
attacked by self-consistency/consensus (Milestone E) — plus a cheap prompt-hardening try
for the wrong-wrapper 30%. Neither is more extraction work.
