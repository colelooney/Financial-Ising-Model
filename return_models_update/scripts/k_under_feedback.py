"""Does re-choosing k under feedback remove the lag-1 return autocorrelation?

Runs the deployed model at the recommended row for several loop gains G and clocks k, and prints
AC(r, 1), mean AC(|r|) over lags 1-20, kurtosis and mean T/T0 (4 runs x 10,000 days each).
Reads results/figures/figdata.pkl from scripts/make_figures.py.

    uv run python scripts/k_under_feedback.py
"""

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy import stats

try:
    from ising_market.model import simulate_deployed
except ModuleNotFoundError:  # package not installed: use the src/ layout directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from ising_market.model import simulate_deployed


def ac(x, lag):
    x = x - x.mean()
    return float(x[:-lag] @ x[lag:] / (x @ x))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--figdata", default="results/figures/figdata.pkl")
    p.add_argument("--gains", type=float, nargs="+", default=[0.0, 0.5, 0.75, 1.0])
    p.add_argument("--ks", type=int, nargs="+", default=[18, 36, 72, 144])
    p.add_argument("--runs", type=int, default=4)
    p.add_argument("--days", type=int, default=10_000)
    args = p.parse_args()

    with open(args.figdata, "rb") as f:
        d = pickle.load(f)
    J, cons = d["net"]["J"], d["cons"]
    print(f"T0 = {cons['T0']:.4f}, calibrated k = {cons['k']}, eps = {cons['eps']:.3f}")
    print("   G     k  AC(r,1)  mean AC|r| 1-20  kurtosis  mean T/T0")
    for G in args.gains:
        for k in args.ks:
            rows = []
            for rep in range(args.runs):
                sim = simulate_deployed(J, cons["T0"], k, G / abs(cons["eps"]), cons["sigma0"],
                                        args.days,
                                        rng=np.random.default_rng([7, int(100 * G), k, rep]))
                r = sim["m"]
                a = np.abs(r - r.mean())
                rows.append((ac(r, 1), np.mean([ac(a, L) for L in range(1, 21)]),
                             stats.kurtosis(r, fisher=False), sim["T"].mean() / cons["T0"]))
            m = np.mean(rows, axis=0)
            print(f"{G:5.2f} {k:5d}  {m[0]:7.3f}  {m[1]:15.3f}  {m[2]:8.2f}  {m[3]:9.3f}",
                  flush=True)


if __name__ == "__main__":
    main()
