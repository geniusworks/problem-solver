"""AoC answer submission: the separate step of the AoC 2026 registration.

Nothing in the solve loop calls into this package, and the solve loop never sees AoC's
replies. After a night's trials, `submission.step` pools every recorded answer for a part,
ranks the candidates and posts them one at a time within the budget in
`submission.policy`, from a named account only (AOC_ACCOUNT), and only when
SUBMIT_SOLUTIONS is true. `submission.client.post_answer` is the project's only code that
posts to adventofcode.com. See dev/progress/aoc2026-registration.md, "Submitting".
"""
