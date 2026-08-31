"""Analyse the pass@k A/B.

Compares measured pass@k against the unbiased independent-draw estimator, so we
can separate two different claims:

  1. Does sampling help at the frontier?      (k3/k5 vs k1, measured)
  2. Does OUR harness realise the theoretical gain?
     (measured k3/k5 vs what independent draws predict from the k1 rate)

(2) matters: if measured k5 sits well below theory, our draws are correlated or
the selector is discarding correct candidates -- a finding about the
orchestration, not the model.

Usage: venv/bin/python analyze_passk.py
"""
import glob
import json
from collections import defaultdict


def pass_at_k_unbiased(n: int, c: int, k: int):
    """Unbiased pass@k estimator (Chen et al. 2021, HumanEval).

    Returns None when it cannot be estimated. It DEGENERATES to 1.0 whenever
    n - c < k -- with 3 draws you cannot estimate "at least one of 5", and
    reporting 100% there would be an artifact, not a prediction. Needs at least
    k observed failures to say anything.
    """
    if n < k or n - c < k:
        return None
    p = 1.0
    for i in range(k):
        p *= (n - c - i) / (n - i)
    return 1.0 - p


def pass_at_k_parametric(p_hat: float, k: int) -> float:
    """1 - (1 - p)^k: independent-draw prediction from the observed rate.

    Always defined, so it is the primary theory line at our sample sizes. It
    assumes draws are i.i.d. with the point estimate p_hat and ignores the
    uncertainty in p_hat, so treat it as a reference curve, not a confidence
    interval -- with n=6 and p=0.33 the true rate could plausibly be 0.15-0.6.
    """
    return 1.0 - (1.0 - p_hat) ** k


def load(pattern):
    out = []
    for f in sorted(glob.glob(pattern)):
        with open(f) as fh:
            out.append((f, json.load(fh)))
    return out


def per_problem(doc):
    """-> {problem_id: [outcome per trial]} using ProblemResult rows."""
    got = defaultdict(list)
    for r in doc["results"]:
        got[r["problem_id"]].append(r["outcome"])
    return got


def main():
    # --- pooled samp1 draws: the A/B's k1 arm + the band-classification run,
    #     which share fingerprint 5b33a3519b5d (identical config).
    samp1_docs = load("dev/experiments/*_k1_*.json") + load(
        "dev/experiments/*band-classify*.json"
    )
    k3_docs = load("dev/experiments/*_k3_*.json")
    # parallel3: 3 blind draws, repair disabled -- the middle term that separates
    # sampling from repair (dev/progress/topology-parallel3.md). Absent from the
    # original globs, which is why RESULTS.md's 58% row long had no audit trail.
    par_docs = load("dev/experiments/*parallel3*.json")
    k5_docs = load("dev/experiments/*_k5_*.json")

    print("samp1 sources:", [f.split("/")[-1] for f, _ in samp1_docs])
    print("k3 sources:   ", [f.split("/")[-1] for f, _ in k3_docs])
    print("k5 sources:   ", [f.split("/")[-1] for f, _ in k5_docs])

    base = defaultdict(list)
    for _, d in samp1_docs:
        for pid, outs in per_problem(d).items():
            base[pid].extend(outs)

    problems = sorted(p for p in base if p.startswith(("2024_day13", "2024_day15")))
    if not problems:
        print("\n(no d13/d15 data yet)")
        return

    print(f"\n{'problem':22} {'samp1 draws':>12}  {'p':>6}   "
          f"{'pass@3 thy':>10} {'pass@5 thy':>10}")
    print("(theory = 1-(1-p)^k from the pooled samp1 rate; a reference curve, "
          "not a confidence interval)")
    theory = {}
    for pid in problems:
        outs = base[pid]
        n, c = len(outs), sum(o == "solved" for o in outs)
        p = c / n if n else 0.0
        t3 = pass_at_k_parametric(p, 3)
        t5 = pass_at_k_parametric(p, 5)
        u3, u5 = pass_at_k_unbiased(n, c, 3), pass_at_k_unbiased(n, c, 5)
        theory[pid] = (n, c, p, t3, t5)
        u = ""
        if u3 is not None or u5 is not None:
            u = f"   [unbiased: @3 {u3 if u3 is None else format(u3, '.0%')}, @5 {u5 if u5 is None else format(u5, '.0%')}]"
        print(f"{pid:22} {c:>5}/{n:<6} {p:>6.0%}   {t3:>9.0%} {t5:>10.0%}{u}")

    if par_docs:
        got = defaultdict(list)
        for _, d in par_docs:
            for pid, outs in per_problem(d).items():
                got[pid].extend(outs)
        n = sum(len(v) for v in got.values())
        c = sum(o == "solved" for v in got.values() for o in v)
        print(f"\n=== parallel3 (3 blind draws, repair=0) ===")
        for pid in sorted(got):
            outs = got[pid]
            print(f"{pid:22} {sum(o=='solved' for o in outs)}/{len(outs)}")
        print(f"{'TOTAL':22} {c}/{n} = {c/n:.0%}")

    for label, docs, k in (("k3", k3_docs, 3), ("k5", k5_docs, 5)):
        if not docs:
            print(f"\n{label}: not finished yet")
            continue
        got = defaultdict(list)
        for _, d in docs:
            for pid, outs in per_problem(d).items():
                got[pid].extend(outs)
        print(f"\n=== measured {label} vs theory ===")
        print(f"{'problem':22} {'measured':>10}  {'theory':>7}  delta")
        tot_m = tot_t = tot_n = 0
        for pid in problems:
            outs = got.get(pid, [])
            if not outs:
                continue
            m = sum(o == "solved" for o in outs) / len(outs)
            t = theory[pid][3 if k == 3 else 4]
            tot_m += m * len(outs)
            tot_t += t * len(outs)
            tot_n += len(outs)
            flag = "  <-- below theory" if m < t - 0.25 else ""
            print(f"{pid:22} {m:>9.0%}  {t:>7.0%}  {m - t:+.0%}{flag}")
        if tot_n:
            print(f"{'OVERALL':22} {tot_m / tot_n:>9.0%}  {tot_t / tot_n:>7.0%}  "
                  f"{(tot_m - tot_t) / tot_n:+.0%}")

    print("\n--- headline ---")
    n_tot = sum(theory[p][0] for p in problems)
    c_tot = sum(theory[p][1] for p in problems)
    print(f"pooled samp1 (pass@1): {c_tot}/{n_tot} = {c_tot / n_tot:.0%}")


if __name__ == "__main__":
    main()
