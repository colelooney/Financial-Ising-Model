"""Does market breadth predict volatility beyond past returns? A GARCH-X test of the Ising idea.

On day t each stock's spin is the sign of its return, so the magnetisation m_t = mean_i sign(r_it)
is market breadth (share of stocks up minus share down). The test asks whether yesterday's
alignment m_{t-1}^2 predicts the variance of the equal-weight index once yesterday's shock and the
usual GARCH terms are already in:

    r_t = mu + phi r_{t-1} + e_t,   e_t = sigma_t z_t,   z_t ~ unit-variance Student-t(nu)
    sigma_t^2 = omega + (a + g 1[e_{t-1} < 0]) e_{t-1}^2 + b sigma_{t-1}^2
                + gamma m_{t-1}^2 + delta D_{t-1}

g is the GJR asymmetry (Glosten, Jagannathan & Runkle 1993): index volatility rises more after
falls. D is a robust cross-sectional dispersion (scaled median absolute deviation of the day's
stock returns, squared). For a given index move, high alignment means low dispersion, so D is the
control that separates "the stocks moved together" from "the stocks moved apart".

Tests, all on the equal-weight index of the stocks in --rets (returns in percent):
  1. In-sample: likelihood-ratio and robust (sandwich) Wald tests of gamma = 0, delta = 0, both.
  2. Out of sample: parameters fitted before --split, one-day variance forecasts after it, compared
     by QLIKE loss (Patton 2011) with a Diebold-Mariano test using Newey-West standard errors.
  3. Diagnostic: the baseline model's standardised squared residuals e_t^2 / sigma_t^2 by decile of
     m_{t-1}^2. A correct variance model gives 1 in every decile.
--simulate checks the tests on simulated one-factor panels (100 stocks x 5,000 days, 40 runs each).
Breadth given dispersion rejected a true gamma = 0 in 5% of runs (LR; 2% robust Wald), found
gamma = 0.05 in 40% and gamma = 0.15 in 92%, with unbiased estimates. Breadth alone rejected
gamma = 0 in 12%: the index's leftover idiosyncratic risk moves with dispersion, which breadth
partly measures. So the main test is breadth given dispersion.

    uv run python scripts/garch_x_breadth.py --rets data/rets_us100_2005_2024.pkl
    uv run python scripts/garch_x_breadth.py --simulate
"""

# ruff: noqa: NPY002
import argparse
import math
import sys
import time
from pathlib import Path

import matplotlib as mpl
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from numba import njit
from scipy import optimize, stats

NAMES = ["mu", "phi", "omega", "a", "g", "b", "nu", "gamma", "delta"]
MODELS = {   # free parameters on top of mu, phi, omega, a, b, nu
    "GARCH": [],
    "GJR": ["g"],
    "GJR + breadth": ["g", "gamma"],
    "GJR + dispersion": ["g", "delta"],
    "GJR + both": ["g", "gamma", "delta"],
}
BASE = ["mu", "phi", "omega", "a", "b", "nu"]
TESTS = [("GJR", "GJR + breadth", "breadth, gamma"),
         ("GJR", "GJR + dispersion", "dispersion, delta"),
         ("GJR + dispersion", "GJR + both", "breadth given dispersion"),
         ("GJR + breadth", "GJR + both", "dispersion given breadth"),
         ("GARCH", "GJR", "asymmetry, g (sanity check)")]


# ----------------------------------------------------------------------------------------------
# Likelihood
# ----------------------------------------------------------------------------------------------

@njit(cache=True)
def _filter(p, r, m2, D, s2_start):
    """Residuals, variances and per-day log-likelihoods for days 1..n-1 (day 0 is the lag)."""
    mu, phi, omega, a, g, b, nu, gamma, delta = p
    n = len(r)
    e = np.zeros(n)
    s2 = np.zeros(n)
    ll = np.zeros(n)
    c = (math.lgamma((nu + 1) / 2) - math.lgamma(nu / 2) - 0.5 * math.log(math.pi * (nu - 2)))
    s2_prev, e_prev = s2_start, 0.0
    for t in range(1, n):
        e[t] = r[t] - mu - phi * r[t - 1]
        if t == 1:
            v = s2_start
        else:
            neg = 1.0 if e_prev < 0 else 0.0
            v = (omega + (a + g * neg) * e_prev * e_prev + b * s2_prev
                 + gamma * m2[t - 1] + delta * D[t - 1])
        if v <= 1e-8:
            return e, s2, ll, False
        s2[t] = v
        ll[t] = c - 0.5 * math.log(v) - (nu + 1) / 2 * math.log(1 + e[t] ** 2 / ((nu - 2) * v))
        s2_prev, e_prev = v, e[t]
    return e, s2, ll, True


class Fit:
    def __init__(self, name, r, m2, D, start=0, stop=None):
        self.name, self.free = name, BASE + MODELS[name]
        self.r, self.m2, self.D = r, m2, D
        self.sl = slice(max(start, 1), stop)
        self.s2_start = float(np.var(r[start:stop]))

    def full(self, theta):
        p = np.zeros(len(NAMES))
        for name, v in zip(self.free, theta, strict=True):
            p[NAMES.index(name)] = v
        return p

    def loglik_t(self, theta):
        e, s2, ll, ok = _filter(self.full(theta), self.r, self.m2, self.D, self.s2_start)
        return ll[self.sl] if ok else None

    def nll(self, theta):
        p = self.full(theta)
        if p[6] <= 2.05 or p[6] > 200 or p[2] <= 0 or p[3] < 0 or p[5] < 0 \
                or p[3] + p[4] < 0 or p[3] + p[4] / 2 + p[5] >= 0.999:
            return 1e10
        ll = self.loglik_t(theta)
        return 1e10 if ll is None else -float(ll.sum())

    def fit(self, starts):
        best = None
        for s in starts:
            x0 = np.array([s.get(k, 0.0) for k in self.free])
            res = optimize.minimize(self.nll, x0, method="Nelder-Mead",
                                    options={"maxiter": 20_000, "maxfev": 20_000,
                                             "xatol": 1e-7, "fatol": 1e-7, "adaptive": True})
            res = optimize.minimize(self.nll, res.x, method="Powell",
                                    options={"maxiter": 20_000, "xtol": 1e-8, "ftol": 1e-10})
            if best is None or res.fun < best.fun:
                best = res
        self.theta, self.LL = best.x, -best.fun
        return self

    def robust_se(self):
        """Sandwich standard errors H^-1 (sum s_t s_t') H^-1 from numerical derivatives."""
        th, k = self.theta, len(self.theta)
        h = 1e-4 * np.maximum(1.0, np.abs(th))
        scores = np.zeros((len(self.loglik_t(th)), k))
        for j in range(k):
            up, dn = th.copy(), th.copy()
            up[j] += h[j]
            dn[j] -= h[j]
            scores[:, j] = (self.loglik_t(up) - self.loglik_t(dn)) / (2 * h[j])
        def ll_at(i, di, j, dj):
            x = th.copy()
            x[i] += di
            x[j] += dj
            return -self.nll(x)

        H = np.zeros((k, k))
        for i in range(k):
            for j in range(i, k):
                H[i, j] = H[j, i] = (ll_at(i, h[i], j, h[j]) - ll_at(i, h[i], j, -h[j])
                                     - ll_at(i, -h[i], j, h[j]) + ll_at(i, -h[i], j, -h[j])) \
                    / (4 * h[i] * h[j])
        Hinv = np.linalg.inv(-H)
        cov = Hinv @ (scores.T @ scores) @ Hinv
        return np.sqrt(np.clip(np.diag(cov), 0, None)), np.sqrt(np.clip(np.diag(Hinv), 0, None))

    def variances(self, theta=None):
        """Residuals and conditional variances over the whole sample with fitted parameters."""
        e, s2, _, _ = _filter(self.full(self.theta if theta is None else theta), self.r, self.m2,
                              self.D, self.s2_start)
        return e, s2


def starts_for(r):
    v = np.var(r)
    base = {"mu": float(np.mean(r)), "phi": 0.0, "nu": 7.0}
    out = []
    for a, b, g in ((0.03, 0.9, 0.08), (0.06, 0.9, 0.04), (0.01, 0.95, 0.06)):
        out.append(base | {"omega": v * (1 - a - g / 2 - b), "a": a, "b": b, "g": g,
                           "gamma": 0.0, "delta": 0.0})
    return out


def fit_all(r, m2, D, start=0, stop=None):
    fits = {}
    for name in MODELS:
        f = Fit(name, r, m2, D, start, stop)
        warm = [dict(zip(fits[prev].free, fits[prev].theta, strict=True)) for prev in fits
                if set(fits[prev].free) <= set(f.free)]
        fits[name] = f.fit(starts_for(r[start:stop]) + warm)
    return fits


# ----------------------------------------------------------------------------------------------
# Data and tests
# ----------------------------------------------------------------------------------------------

def panel_inputs(rets):
    """Index return, breadth m and robust dispersion D (all in percent units) from stock returns."""
    R = np.asarray(rets, dtype=float) * 100
    r = R.mean(axis=1)
    m = np.sign(R).mean(axis=1)
    med = np.median(R, axis=1, keepdims=True)
    D = (1.4826 * np.median(np.abs(R - med), axis=1)) ** 2
    return r, m, D


def newey_west_t(d):
    n = len(d)
    L = int(np.floor(4 * (n / 100) ** (2 / 9)))
    x = d - d.mean()
    v = x @ x / n
    for lag in range(1, L + 1):
        v += 2 * (1 - lag / (L + 1)) * (x[lag:] @ x[:-lag]) / n
    return d.mean() / np.sqrt(v / n)


def out_of_sample(r, m2, D, split):
    """Fit on days before split, forecast after it; QLIKE losses on a common proxy."""
    fits = fit_all(r, m2, D, 0, split)
    e0, _ = fits["GJR"].variances()
    proxy = e0[split:] ** 2
    loss = {}
    for name, f in fits.items():
        _, s2 = f.variances()
        loss[name] = np.log(s2[split:]) + proxy / s2[split:]
    rows = []
    for base, alt, label in TESTS:
        d = loss[base] - loss[alt]
        t = newey_west_t(d)
        rows.append({"test": label, "base": base, "alt": alt,
                     "QLIKE base": float(loss[base].mean()), "QLIKE alt": float(loss[alt].mean()),
                     "gain": float(d.mean()), "DM t": float(t),
                     "p": float(2 * stats.norm.sf(abs(t)))})
    return fits, rows


def in_sample(fits):
    rows = []
    for base, alt, label in TESTS:
        df = len(fits[alt].free) - len(fits[base].free)
        LR = 2 * (fits[alt].LL - fits[base].LL)
        rows.append({"test": label, "base": base, "alt": alt, "LR": LR, "df": df,
                     "p": float(stats.chi2.sf(max(LR, 0.0), df))})
    return rows


def decile_diagnostic(fit, m2, n_bins=10):
    e, s2 = fit.variances()
    z2 = (e ** 2 / np.where(s2 > 0, s2, np.nan))[1:]
    x = m2[:-1]
    edges = np.quantile(x, np.linspace(0, 1, n_bins + 1))
    idx = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, n_bins - 1)
    out = []
    for k in range(n_bins):
        z = z2[idx == k]
        out.append((float(x[idx == k].mean()), float(z.mean()), float(z.std() / np.sqrt(len(z)))))
    return np.array(out)


def run(r, m, D, dates, split_date, label):
    m2 = m ** 2
    n = len(r)
    t0 = time.time()
    fits = fit_all(r, m2, D)
    ins = in_sample(fits)
    split = int(np.searchsorted(dates, np.datetime64(split_date))) if dates is not None else n // 2
    split = min(max(split, 500), n - 500)
    oos_fits, oos = out_of_sample(r, m2, D, split)
    se = {name: fits[name].robust_se() for name in ("GJR + breadth", "GJR + both")}
    diag = {name: decile_diagnostic(fits[name], m2) for name in ("GJR", "GJR + breadth",
                                                                 "GJR + both")}
    return {"label": label, "n": n, "split": split, "fits": fits, "in_sample": ins,
            "oos": oos, "se": se, "diag": diag, "m": m, "D": D, "r": r, "dates": dates,
            "seconds": time.time() - t0, "oos_fits": oos_fits}


def wald(res, model, par):
    f = res["fits"][model]
    j = f.free.index(par)
    se_rob, se_mle = res["se"][model]
    z = f.theta[j] / se_rob[j]
    return f.theta[j], se_rob[j], se_mle[j], z, float(2 * stats.norm.sf(abs(z)))


# ----------------------------------------------------------------------------------------------
# Simulation check
# ----------------------------------------------------------------------------------------------

def simulate_panel(n_days, n_stocks, gamma, seed, nu=6.0):
    """One-factor panel in percent: r_it = beta_i f_t + 1.4 exp(h_t) eps_it, with market factor
    f_t = sigma_t z_t, sigma_t^2 = 0.02 + 0.09 f_{t-1}^2 + 0.89 sigma_{t-1}^2 + gamma m_{t-1}^2,
    and idiosyncratic log-scale h_t = 0.98 h_{t-1} + 0.1 eta_t. The varying h is what lets breadth
    move independently of the index return; with constant idiosyncratic risk, m is close to a
    fixed function of the day's index return and gamma is barely identified."""
    rng = np.random.default_rng(seed)
    beta = rng.uniform(0.6, 1.4, n_stocks)
    z = rng.standard_t(nu, n_days) * np.sqrt((nu - 2) / nu)
    R = np.empty((n_days, n_stocks))
    s2, f_prev, m_prev, h = 0.02 / (1 - 0.98), 0.0, 0.0, 0.0
    for t in range(n_days):
        s2 = 0.02 + 0.09 * f_prev ** 2 + 0.89 * s2 + gamma * m_prev ** 2
        h = 0.98 * h + 0.1 * rng.standard_normal()
        f = np.sqrt(s2) * z[t]
        R[t] = beta * f + 1.4 * np.exp(h) * rng.standard_normal(n_stocks)
        f_prev, m_prev = f, np.sign(R[t]).mean()
    return R / 100


def simulation_check(reps, n_days, n_stocks):
    """Rejection rates of the two breadth tests on simulated panels. With gamma = 0 breadth has no
    effect on the market factor, but the equal-weight index still carries some idiosyncratic risk
    (about sigma_idio^2 / N), which moves with dispersion, so breadth alone can look significant;
    the test of breadth given dispersion should reject at about the nominal 5%."""
    print(f"Simulated one-factor panels: {n_stocks} stocks x {n_days} days, {reps} per setting")
    out = {}
    for gamma in (0.0, 0.05, 0.15):
        rows = []
        for rep in range(reps):
            r, m, D = panel_inputs(simulate_panel(n_days, n_stocks, gamma, [11, rep]))
            fits = {}
            for name in ("GJR", "GJR + breadth", "GJR + dispersion", "GJR + both"):
                f = Fit(name, r, m ** 2, D)
                warm = [dict(zip(fits[q].free, fits[q].theta, strict=True)) for q in fits
                        if set(fits[q].free) <= set(f.free)]
                fits[name] = f.fit(starts_for(r) + warm)
            alone = stats.chi2.sf(max(2 * (fits["GJR + breadth"].LL - fits["GJR"].LL), 0), 1)
            given = stats.chi2.sf(max(2 * (fits["GJR + both"].LL - fits["GJR + dispersion"].LL),
                                      0), 1)
            f = fits["GJR + both"]
            j = f.free.index("gamma")
            se = f.robust_se()[0][j]
            rows.append((alone, given, f.theta[j], 2 * stats.norm.sf(abs(f.theta[j] / se))))
        a = np.array(rows)
        out[gamma] = a
        print(f"  true gamma = {gamma:.2f}: rejected at 5%: breadth alone "
              f"{np.mean(a[:, 0] < 0.05):.0%}, breadth given dispersion LR "
              f"{np.mean(a[:, 1] < 0.05):.0%} / robust Wald {np.mean(a[:, 3] < 0.05):.0%}; "
              f"gamma estimate (given dispersion) {a[:, 2].mean():.3f} ± {a[:, 2].std():.3f}",
              flush=True)
    return out


# ----------------------------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------------------------

SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", \
    "#c3c2b7"
BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"


def style():
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
        "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "xtick.color": AXIS, "ytick.color": AXIS, "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2, "legend.frameon": False, "legend.fontsize": 8.5,
        "savefig.dpi": 200, "savefig.bbox": "tight",
    })


def figure(res, path):
    style()
    fig = Figure(figsize=(12, 7.6), layout="constrained")
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.1])
    dates = res["dates"] if res["dates"] is not None else np.arange(res["n"])
    m, r = res["m"], res["r"]

    ax = fig.add_subplot(gs[0, :])
    roll_m2 = pd.Series(m ** 2).rolling(20).mean().to_numpy()
    roll_vol = pd.Series(r).rolling(20).std().to_numpy() * np.sqrt(252)
    ax.plot(dates, roll_m2, color=BLUE, lw=1.0, label="breadth², 20-day mean (left)")
    ax.set_ylabel("m²")
    ax2 = ax.twinx()
    ax2.plot(dates, roll_vol, color=ORANGE, lw=1.0, label="index volatility, 20-day, annualised "
             "% (right)")
    ax2.set_ylabel("volatility (%)")
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")
    ax.set_title("Alignment of the stocks (breadth squared) and index volatility")

    for col, name, title in ((0, "GJR", "Baseline GJR-GARCH-t"),
                             (1, "GJR + breadth", "With breadth in the variance")):
        ax = fig.add_subplot(gs[1, col])
        dg = res["diag"][name]
        ax.axhline(1, color=INK2, lw=0.9)
        ax.errorbar(dg[:, 0], dg[:, 1], yerr=2 * dg[:, 2], fmt="o", color=BLUE, mec=SURFACE,
                    ecolor=BLUE, elinewidth=1, capsize=0)
        ax.set_xlabel("yesterday's m², decile mean")
        ax.set_ylabel("mean of e² / σ² today (±2 SE)")
        ax.set_title(f"{title}: forecast error by yesterday's alignment")
    ymax = max(np.max(res["diag"][n][:, 1] + 2 * res["diag"][n][:, 2])
               for n in ("GJR", "GJR + breadth"))
    for a in fig.axes[2:]:
        a.set_ylim(0, max(1.6, ymax * 1.05))
    fig.savefig(path)


def primary(res):
    ins = next(x for x in res["in_sample"] if x["test"] == "breadth given dispersion")
    oos = next(x for x in res["oos"] if x["test"] == "breadth given dispersion")
    est, se_r, _, z, p_w = wald(res, "GJR + both", "gamma")
    return (f"gamma = {est:.4f} (robust SE {se_r:.4f}, z = {z:.2f}, p = {p_w:.4f}); likelihood "
            f"ratio {ins['LR']:.2f} (p = {ins['p']:.4f}); out of sample, QLIKE gain "
            f"{oos['gain']:.4f} (Diebold-Mariano t = {oos['DM t']:.2f}, p = {oos['p']:.4f}).")


def report(res, path):
    f = res["fits"]
    L = [f"# Does breadth predict volatility? ({res['label']})", "",
         f"{res['n']} days. Returns in percent; variance in %². Out-of-sample split at day "
         f"{res['split']}" + (f" ({str(res['dates'][res['split']])[:10]})"
                              if res["dates"] is not None else "") + ".", "",
         "## Main result: does breadth add to a model that already has dispersion?", "",
         primary(res), "",
         "Breadth on its own is not the right test: an equal-weight index of N stocks keeps some "
         "idiosyncratic risk (about the dispersion over N), so low breadth predicts variance "
         "mechanically. On simulated panels where breadth has no effect, breadth alone was "
         "significant in 12% of runs at the 5% level, and breadth given dispersion in 5%.", "",
         "## Fitted models (whole sample)", "",
         "| model | log-lik | " + " | ".join(NAMES) + " |",
         "|---|---|" + "---|" * len(NAMES)]
    for name, fit in f.items():
        p = fit.full(fit.theta)
        L.append(f"| {name} | {fit.LL:.1f} | "
                 + " | ".join(f"{v:.4g}" if k in fit.free else "" for k, v in zip(NAMES, p,
                                                                                    strict=True))
                 + " |")
    L += ["", "## In-sample likelihood-ratio tests", "",
          "| question | base | alternative | LR | df | p |", "|---|---|---|---|---|---|"]
    for row in res["in_sample"]:
        L.append(f"| {row['test']} | {row['base']} | {row['alt']} | {row['LR']:.2f} | "
                 f"{row['df']} | {row['p']:.4f} |")
    L += ["", "## Robust Wald tests (sandwich standard errors)", "",
          "| model | parameter | estimate | robust SE | MLE SE | z | p |",
          "|---|---|---|---|---|---|---|"]
    for model in ("GJR + breadth", "GJR + both"):
        for par in ("gamma", "delta"):
            if par in f[model].free:
                est, se_r, se_m, z, p = wald(res, model, par)
                L.append(f"| {model} | {par} | {est:.4f} | {se_r:.4f} | {se_m:.4f} | {z:.2f} | "
                         f"{p:.4f} |")
    sd_m2 = float(np.std(res["m"] ** 2))
    g = f["GJR + breadth"].full(f["GJR + breadth"].theta)[7]
    e, s2 = f["GJR"].variances()
    L += ["", f"A one-standard-deviation rise in m² ({sd_m2:.3f}) adds gamma x {sd_m2:.3f} = "
          f"{g * sd_m2:.4f} %² to the next day's variance; the median fitted variance is "
          f"{np.median(s2[1:]):.3f} %².", "",
          "## Out of sample (fitted before the split, QLIKE loss after it)", "",
          "Positive gain = the alternative forecasts better. DM t uses Newey-West standard errors.",
          "", "| question | base | alternative | QLIKE base | QLIKE alt | gain | DM t | p |",
          "|---|---|---|---|---|---|---|---|"]
    for row in res["oos"]:
        L.append(f"| {row['test']} | {row['base']} | {row['alt']} | {row['QLIKE base']:.4f} | "
                 f"{row['QLIKE alt']:.4f} | {row['gain']:.4f} | {row['DM t']:.2f} | "
                 f"{row['p']:.4f} |")
    L += ["", "## Baseline forecast errors by yesterday's alignment", "",
          "Mean of e² / σ² (1 if the variance model is right), by decile of m² on the day before.",
          "", "| decile | mean m² | GJR | GJR + breadth | GJR + both |", "|---|---|---|---|---|"]
    for k in range(len(res["diag"]["GJR"])):
        L.append(f"| {k + 1} | {res['diag']['GJR'][k, 0]:.3f} | "
                 + " | ".join(f"{res['diag'][n][k, 1]:.2f} ± {res['diag'][n][k, 2]:.2f}"
                              for n in ("GJR", "GJR + breadth", "GJR + both")) + " |")
    Path(path).write_text("\n".join(L) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--rets", default="data/rets_us100_2005_2024.pkl")
    p.add_argument("--out", default="results/garch_x")
    p.add_argument("--split", default="2015-01-01", help="first out-of-sample day")
    p.add_argument("--simulate", action="store_true", help="check the tests on simulated data")
    p.add_argument("--reps", type=int, default=40)
    p.add_argument("--sim-days", type=int, default=5000)
    p.add_argument("--sim-stocks", type=int, default=100)
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.simulate:
        simulation_check(args.reps, args.sim_days, args.sim_stocks)
        return
    if not Path(args.rets).exists():
        sys.exit(f"{args.rets} not found: freeze it with scripts/freeze_data.py")
    rets = pd.read_pickle(args.rets)
    r, m, D = panel_inputs(rets)
    dates = rets.index.to_numpy()
    label = f"equal-weight index of {rets.shape[1]} stocks, {str(dates[0])[:10]} to " \
            f"{str(dates[-1])[:10]}"
    print(f"{label}: {len(r)} days")
    res = run(r, m, D, dates, args.split, label)
    report(res, out / "garch_x.md")
    figure(res, out / "garch_x.png")
    print((out / "garch_x.md").read_text())
    print(f"Wrote {out}/garch_x.md and garch_x.png ({res['seconds']:.0f} s)")


if __name__ == "__main__":
    main()
