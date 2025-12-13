"""
UCC × DDM Entropy Diagnostics v0.3 (confirmation sweep, Safe Mode, append-only).

Frozen diagnostics:
 - Belief mapping: linear
 - Failure-to-commit: plateau_time_post_med with H>0.6, threshold 0.25*T_max
 - Premature collapse: dH_min_early < k_emp (1st percentile from C0 early window per mu,sigma)
 - Analytic slope: excluded
 - Noise: Wiener + OU (theta=5, xi grid)
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LOG_DIR = Path("logs") / "ucc_ddm" / "v0_3"
REPORT_DIR = Path("reports") / "ucc_ddm"


def now_iso() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def clamp(p: float, eps: float = 1e-12) -> float:
    return min(1.0 - eps, max(eps, p))


def binary_entropy(p: float) -> float:
    p = clamp(p)
    q = 1.0 - p
    return -p * math.log2(p) - q * math.log2(q)


@dataclass
class DDMParams:
    mu: float
    sigma: float
    a: float = 1.0
    z: float = 0.0
    dt: float = 0.01
    t_max: float = 5.0
    ou_theta: Optional[float] = None
    ou_xi: float = 1.0


def belief_linear(x: float, a: float) -> float:
    return clamp((x + a) / (2 * a))


def simulate_ddm(
    params: DDMParams,
    seed: int,
    downsample: int = 10,
) -> Tuple[float, int | None, bool, List[float]]:
    random.seed(seed)
    x = params.z
    eta = 0.0
    dt = params.dt
    t_max = params.t_max
    steps = int(t_max / dt)
    H_path: List[float] = []
    for step in range(steps):
        t = step * dt
        if params.ou_theta is not None:
            eta += params.ou_theta * (0.0 - eta) * dt + params.ou_xi * math.sqrt(dt) * random.gauss(0, 1)
            dx = params.mu * dt + eta * dt
        else:
            dx = params.mu * dt + params.sigma * math.sqrt(dt) * random.gauss(0, 1)
        x += dx
        p = belief_linear(x, params.a)
        H = binary_entropy(p)
        if step % downsample == 0:
            H_path.append(H)
        if x >= params.a:
            return t, +1, False, H_path
        if x <= -params.a:
            return t, -1, False, H_path
    return t_max, None, True, H_path


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


def entropy_features(rt: float, choice: int | None, timed_out: bool, H_path: List[float], dt_sample: float) -> Dict[str, float | int | None]:
    if not H_path:
        return {k: None for k in ["H_min", "t_Hmin", "dH_min", "AUC_H", "plateau_len", "H_at_tau"]}
    H_min = min(H_path)
    idx_min = H_path.index(H_min)
    t_Hmin = idx_min * dt_sample
    dH = []
    for i in range(1, len(H_path)):
        dH.append((H_path[i] - H_path[i - 1]) / dt_sample)
    dH_min = min(dH) if dH else None
    auc = 0.0
    for i in range(1, len(H_path)):
        auc += 0.5 * (H_path[i] + H_path[i - 1]) * dt_sample
    H_plateau = 0.70
    plateau_len = 0.0
    current = 0.0
    for h in H_path:
        if h >= H_plateau:
            current += dt_sample
            plateau_len = max(plateau_len, current)
        else:
            current = 0.0
    H_at_tau = None
    if choice is not None and rt > 0 and len(H_path) > 1:
        tau = 0.25 * rt
        idx_tau = min(len(H_path) - 1, int(tau / dt_sample))
        H_at_tau = H_path[idx_tau]
    return {
        "H_min": H_min,
        "t_Hmin": t_Hmin,
        "dH_min": dH_min,
        "AUC_H": auc,
        "plateau_len": plateau_len,
        "H_at_tau": H_at_tau,
    }


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


def run_condition(
    cond: str,
    params: DDMParams,
    n_trials: int,
    seed_base: int,
    k_emp: float,
) -> Dict[str, any]:
    dt_sample = params.dt * 10
    trials_path = LOG_DIR / f"trials_{cond}.jsonl"
    trials_path.parent.mkdir(parents=True, exist_ok=True)

    sims = []
    all_rts = []
    absorbed_rts = []
    for i in range(n_trials):
        rt, choice, timed_out, H_path = simulate_ddm(params, seed_base + i)
        sims.append((rt, choice, timed_out, H_path))
        all_rts.append(rt)
        if choice is not None and not timed_out:
            absorbed_rts.append(rt)

    rt_stats_all = rt_stats(all_rts)
    rt_med_ref = rt_stats(absorbed_rts)["median"] if absorbed_rts else rt_stats_all["median"]
    rt_p10 = rt_stats_all["p10"]

    anomalies = {"fail_entropy_v2": 0, "premature_emp": 0}
    rt_flags_counts = {"rt_timeout": 0, "rt_fast": 0}

    with trials_path.open("w", encoding="utf-8") as f:
        for i, (rt, choice, timed_out, H_path) in enumerate(sims):
            feats = entropy_features(rt, choice, timed_out, H_path, dt_sample)
            dH_min_early = compute_dH_min_early(H_path, dt_sample, rt)

            plateau_time_post_med = 0.0
            if H_path and rt_med_ref > 0:
                for idx, h in enumerate(H_path):
                    t_here = idx * dt_sample
                    if t_here > rt_med_ref and h > 0.6:
                        plateau_time_post_med += dt_sample
            fail_v2 = timed_out or (plateau_time_post_med >= 0.25 * params.t_max)
            if fail_v2:
                anomalies["fail_entropy_v2"] += 1

            prem_emp = False
            if dH_min_early is not None and dH_min_early < k_emp and rt > 0:
                prem_emp = True
                anomalies["premature_emp"] += 1

            if timed_out:
                rt_flags_counts["rt_timeout"] += 1
            if rt < rt_p10 and not timed_out:
                rt_flags_counts["rt_fast"] += 1

            record = {
                "timestamp": now_iso(),
                "trial_id": i,
                "cond": cond,
                "params": params.__dict__,
                "rt": rt,
                "choice": choice,
                "timed_out": timed_out,
                "entropy_features": feats,
                "plateau_time_post_med": plateau_time_post_med,
                "fail_entropy_v2": fail_v2,
                "premature_emp": prem_emp,
                "rt_flags": {
                    "rt_timeout": timed_out,
                    "rt_fast": (rt < rt_p10 and not timed_out),
                },
                "dH_min_early": dH_min_early,
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
        "rt_med_ref": rt_med_ref,
    }


def calibrate_k_emp(params: DDMParams, n_trials: int, seed_base: int) -> float:
    dt_sample = params.dt * 10
    dH_vals = []
    for i in range(n_trials):
        rt, choice, timed_out, H_path = simulate_ddm(params, seed_base + i)
        dH_min_early = compute_dH_min_early(H_path, dt_sample, rt)
        if dH_min_early is not None and choice is not None and not timed_out and rt > 0:
            dH_vals.append(dH_min_early)
    if not dH_vals:
        return -5.0
    dH_vals.sort()
    idx = max(0, int(0.01 * len(dH_vals)) - 1)
    return dH_vals[idx]


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    seeds = {
        "C0": 12345,
        "C1": 22345,
        "C2": 32345,
        "C3": 42345,
        "C4": 52345,
    }
    n_trials = 500  # keep runtime bounded
    mu_values = [0.15, 0.3, 0.6]
    sigma_values = [0.8, 1.0, 1.3]
    xi_values = [0.5, 1.0, 2.0]
    theta = 5.0

    combos = []
    for mu in mu_values:
        for sigma in sigma_values:
            combos.append((mu, sigma))

    k_emp_map: Dict[Tuple[float, float], float] = {}
    baseline_params: Dict[Tuple[float, float], DDMParams] = {}
    # Calibrate k_emp per (mu,sigma) on baseline C0
    for mu, sigma in combos:
        base = DDMParams(mu=mu, sigma=sigma)
        k_emp_map[(mu, sigma)] = calibrate_k_emp(base, n_trials=200, seed_base=99999)
        baseline_params[(mu, sigma)] = base

    summaries = []

    for mu, sigma in combos:
        base_key = (mu, sigma)
        k_emp = k_emp_map[base_key]
        # C0 baseline
        summaries.append(run_condition(f"C0_mu{mu}_sigma{sigma}", DDMParams(mu=mu, sigma=sigma), n_trials, seeds["C0"], k_emp))
        # C1 (no transient in v0.3; same params)
        summaries.append(run_condition(f"C1_mu{mu}_sigma{sigma}", DDMParams(mu=mu, sigma=sigma), n_trials, seeds["C1"], k_emp))
        # C2 (weak drift not separately modeled; reusing params per grid)
        summaries.append(run_condition(f"C2_mu{mu}_sigma{sigma}", DDMParams(mu=mu, sigma=sigma), n_trials, seeds["C2"], k_emp))
        # C4 (start bias)
        summaries.append(run_condition(f"C4_mu{mu}_sigma{sigma}", DDMParams(mu=mu, sigma=sigma, z=0.2), n_trials, seeds["C4"], k_emp))
        # C3 OU sweep
        for xi in xi_values:
            summaries.append(run_condition(f"C3_mu{mu}_sigma{sigma}_xi{xi}", DDMParams(mu=mu, sigma=sigma, ou_theta=theta, ou_xi=xi), n_trials, seeds["C3"], k_emp))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "summary_v0.3.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# UCC × DDM Entropy Diagnostics v0.3 Summary\n\n")
        f.write(f"Generated: {now_iso()}\n\n")
        for s in summaries:
            f.write(f"## {s['cond']}\n")
            f.write(f"- Trials: {s['n_trials']}\n")
            f.write(f"- k_emp: {s['k_emp']:.3f}\n")
            rt = s["rt_stats"]
            f.write(f"- RT mean={rt['mean']:.3f}, var={rt['var']:.3f}, min={rt['min']:.3f}, max={rt['max']:.3f}, median={rt['median']:.3f}\n")
            f.write(f"- Anomalies (entropy v2): fail={s['anomalies']['fail_entropy_v2']}, premature_emp={s['anomalies']['premature_emp']}\n")
            f.write(f"- RT-only flags: timeouts={s['rt_flags']['rt_timeout']}, fast={s['rt_flags']['rt_fast']}\n\n")
        f.write("Diagnostics locked: linear mapping; failure=plateau_time_post_med>0.25*T_max at H>0.6; premature via k_emp from C0 early dH (1st percentile per mu,sigma); analytic slope excluded; OU implemented with theta=5, xi sweep. No transient noise in v0.3.\n")


if __name__ == "__main__":
    main()
