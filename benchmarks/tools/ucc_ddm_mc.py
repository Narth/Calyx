"""
UCC × DDM-MC (Multi-Choice) v1.0 (Safe Mode, append-only).

Frozen diagnostics:
 - Belief: softmax (beta=1.0), categorical entropy, normalized by log2(N)
 - Failure-to-commit: time with H_norm>0.6 after median RT >= 0.25*Tmax or timeout
 - Premature: early dH_norm_min < k_emp_MC (1st percentile from N=2 baseline per mu)
 - No analytic slope; no transients; Wiener noise only

Runs:
 - N in {2,4,8}
 - mu_target in {0.2, 0.4}, other drifts = 0
 - sigma = 1.0
 - Trials: 500 per condition

Outputs:
 - logs/ucc_ddm_mc/v1/trials_N<N>_mu<MU>.jsonl
 - reports/ucc_ddm_mc/summary_v1.md
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LOG_DIR = Path("logs") / "ucc_ddm_mc" / "v1"
REPORT_DIR = Path("reports") / "ucc_ddm_mc"


def now_iso() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def clamp(p: float, eps: float = 1e-12) -> float:
    return min(1.0 - eps, max(eps, p))


def softmax(xs: List[float], beta: float = 1.0) -> List[float]:
    m = max(xs)
    exps = [math.exp(beta * (x - m)) for x in xs]
    s = sum(exps)
    return [e / s for e in exps]


def categorical_entropy(ps: List[float]) -> float:
    h = 0.0
    for p in ps:
        p = clamp(p)
        h -= p * math.log2(p)
    return h


@dataclass
class MCParams:
    N: int
    mu_target: float
    sigma: float = 1.0
    a: float = 1.0
    z: float = 0.0
    dt: float = 0.01
    t_max: float = 5.0


def simulate_mc(params: MCParams, seed: int, downsample: int = 10) -> Tuple[float, int | None, bool, List[float]]:
    random.seed(seed)
    xs = [params.z for _ in range(params.N)]
    dt = params.dt
    steps = int(params.t_max / dt)
    Hnorm_path: List[float] = []
    for step in range(steps):
        t = step * dt
        # update
        for i in range(params.N):
            mu = params.mu_target if i == 0 else 0.0
            xs[i] += mu * dt + params.sigma * math.sqrt(dt) * random.gauss(0, 1)
        # belief and entropy
        ps = softmax(xs, beta=1.0)
        H = categorical_entropy(ps)
        Hnorm = H / math.log2(params.N)
        if step % downsample == 0:
            Hnorm_path.append(Hnorm)
        # absorb
        for i, x in enumerate(xs):
            if x >= params.a:
                return t, i, False, Hnorm_path
    return params.t_max, None, True, Hnorm_path


def compute_dH_min_early(H_path: List[float], dt_sample: float, rt: float, early_frac: float = 0.25) -> Optional[float]:
    if not H_path or rt <= 0:
        return None
    max_idx = max(1, int((early_frac * rt) / dt_sample))
    max_idx = min(max_idx, len(H_path) - 1)
    dH = []
    for i in range(1, max_idx + 1):
        dH.append((H_path[i] - H_path[i - 1]) / dt_sample)
    if not dH:
        return None
    return min(dH)


def rt_stats(rts: List[float]) -> Dict[str, float]:
    if not rts:
        return {"mean": 0, "var": 0, "min": 0, "max": 0, "median": 0, "p10": 0}
    rts_sorted = sorted(rts)
    n = len(rts)
    mean = sum(rts) / n
    var = sum((x - mean) ** 2 for x in rts) / n
    median = rts_sorted[n // 2]
    p10 = rts_sorted[max(0, int(0.10 * n) - 1)]
    return {"mean": mean, "var": var, "min": rts_sorted[0], "max": rts_sorted[-1], "median": median, "p10": p10}


def calibrate_k_emp_mc(params: MCParams, n_trials: int, seed_base: int) -> float:
    dt_sample = params.dt * 10
    dH_vals = []
    for i in range(n_trials):
        rt, choice, timed_out, H_path = simulate_mc(params, seed_base + i)
        dH_min_early = compute_dH_min_early(H_path, dt_sample, rt)
        if dH_min_early is not None and choice is not None and not timed_out and rt > 0:
            dH_vals.append(dH_min_early)
    if not dH_vals:
        return -5.0
    dH_vals.sort()
    idx = max(0, int(0.01 * len(dH_vals)) - 1)
    return dH_vals[idx]


def run_condition(cond: str, params: MCParams, n_trials: int, seed_base: int, k_emp: float) -> Dict[str, any]:
    dt_sample = params.dt * 10
    trials_path = LOG_DIR / f"trials_N{params.N}_mu{params.mu_target}_{cond}.jsonl"
    trials_path.parent.mkdir(parents=True, exist_ok=True)

    sims = []
    all_rts = []
    absorbed_rts = []
    for i in range(n_trials):
        rt, choice, timed_out, H_path = simulate_mc(params, seed_base + i)
        sims.append((rt, choice, timed_out, H_path))
        all_rts.append(rt)
        if choice is not None and not timed_out:
            absorbed_rts.append(rt)

    rt_stats_all = rt_stats(all_rts)
    rt_med_ref = rt_stats(absorbed_rts)["median"] if absorbed_rts else rt_stats_all["median"]
    rt_p10 = rt_stats_all["p10"]

    anomalies = {"fail_entropy": 0, "premature_emp": 0}
    rt_flags_counts = {"rt_timeout": 0, "rt_fast": 0}

    with trials_path.open("w", encoding="utf-8") as f:
        for i, (rt, choice, timed_out, H_path) in enumerate(sims):
            # fail-to-commit
            plateau_time_post_med = 0.0
            if H_path and rt_med_ref > 0:
                for idx, h in enumerate(H_path):
                    t_here = idx * dt_sample
                    if t_here > rt_med_ref and h > 0.6:
                        plateau_time_post_med += dt_sample
            fail_v2 = timed_out or (plateau_time_post_med >= 0.25 * params.t_max)
            if fail_v2:
                anomalies["fail_entropy"] += 1

            dH_min_early = compute_dH_min_early(H_path, dt_sample, rt)
            prem_emp = False
            if dH_min_early is not None and dH_min_early < k_emp and rt > 0:
                prem_emp = True
                anomalies["premature_emp"] += 1

            if timed_out:
                rt_flags_counts["rt_timeout"] += 1
            if rt < rt_p10 and not timed_out:
                rt_flags_counts["rt_fast"] += 1

            feats = {
                "H_norm_min": min(H_path) if H_path else None,
                "plateau_time_post_med": plateau_time_post_med,
                "dH_norm_min_early": dH_min_early,
            }

            record = {
                "timestamp": now_iso(),
                "trial_id": i,
                "N": params.N,
                "mu_target": params.mu_target,
                "sigma": params.sigma,
                "rt": rt,
                "choice": choice,
                "timed_out": timed_out,
                "features": feats,
                "fail_entropy": fail_v2,
                "premature_emp": prem_emp,
                "rt_flags": {
                    "rt_timeout": timed_out,
                    "rt_fast": (rt < rt_p10 and not timed_out),
                },
                "rt_med_ref": rt_med_ref,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "cond": cond,
        "rt_stats": rt_stats_all,
        "anomalies": anomalies,
        "rt_flags": rt_flags_counts,
        "n_trials": n_trials,
        "k_emp": k_emp,
    }


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    seeds = {
        "N2": 12345,
        "N4": 22345,
        "N8": 32345,
    }
    n_trials = 500
    Ns = [2, 4, 8]
    mu_targets = [0.2, 0.4]
    sigma = 1.0

    summaries = []
    k_emp_map: Dict[Tuple[int, float], float] = {}

    # Calibrate k_emp_MC using N=2 baselines for each mu
    for mu in mu_targets:
        base_params = MCParams(N=2, mu_target=mu, sigma=sigma)
        k_emp_map[(2, mu)] = calibrate_k_emp_mc(base_params, n_trials=200, seed_base=99999)

    for N in Ns:
        for mu in mu_targets:
            key = (N, mu)
            if N == 2:
                k_emp = k_emp_map[(2, mu)]
            else:
                # reuse N=2 calibration for same mu
                k_emp = k_emp_map[(2, mu)]
            seed = seeds[f"N{N}"]
            cond_name = f"N{N}_mu{mu}"
            summaries.append(run_condition(cond_name, MCParams(N=N, mu_target=mu, sigma=sigma), n_trials, seed, k_emp))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "summary_v1.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# UCC × DDM-MC v1.0 Summary\n\n")
        f.write(f"Generated: {now_iso()}\n\n")
        for s in summaries:
            f.write(f"## {s['cond']}\n")
            f.write(f"- Trials: {s['n_trials']}\n")
            f.write(f"- k_emp_MC: {s['k_emp']:.3f}\n")
            rt = s["rt_stats"]
            f.write(f"- RT mean={rt['mean']:.3f}, var={rt['var']:.3f}, min={rt['min']:.3f}, max={rt['max']:.3f}, median={rt['median']:.3f}\n")
            f.write(f"- Anomalies (entropy): fail={s['anomalies']['fail_entropy']}, premature_emp={s['anomalies']['premature_emp']}\n")
            f.write(f"- RT-only flags: timeouts={s['rt_flags']['rt_timeout']}, fast={s['rt_flags']['rt_fast']}\n\n")
        f.write("Diagnostics locked: softmax belief (beta=1), H_norm entropy; fail via plateau_time_post_med>0.25*Tmax with H_norm>0.6 or timeout; premature via k_emp_MC (1st percentile early dH_norm from N=2 baselines per mu). No analytic slope, no transients, Wiener noise only.\n")


if __name__ == "__main__":
    main()
