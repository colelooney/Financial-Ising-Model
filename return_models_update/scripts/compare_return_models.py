"""Which way of turning spins into returns best matches the market?

Five spin-model return mechanisms from the literature run on the same empirical network J. Each is
calibrated by the method of simulated moments (Franke & Westerhoff 2012) to the equal-weight index
of the same stocks, then checked on moments it was not fitted to. A GARCH(1,1)-t fitted by maximum
likelihood and an i.i.d. Gaussian are the statistical yardsticks.

Run from the repository root after scripts/make_figures.py (it reads that run's figdata.pkl):

    uv run python scripts/compare_return_models.py            # about 5-10 minutes
    uv run python scripts/compare_return_models.py --quick    # shorter runs, to check the pipeline
    uv run python scripts/compare_return_models.py --replot   # redraw from the saved numbers

Outputs (in --out, default results/return_models): figR1_tails.png, figR2_clustering.png,
figR3_scorecard.png, figR4_paths.png, figR5_scaling.png, return_models.md (tables) and
compare.pkl (all numbers).

Models (r is the daily return; "ours" is the calibrated Metropolis model at T0 with the volatility
feedback T = T0 (sigma/sigma0)^-alpha, sigma being the 20-day std of the model's own returns):
    level     ours, r = m (current model; excess demand moves the price)
    change    ours, r = m_t - m_{t-1} (market clearing against fundamentalists: log p = log p* +
              lambda m, Kaizoji, Bornholdt & Fujiwara 2002); k is free, as in their one sweep a day
    cluster   ours, r = sum over active Fortuin-Kasteleyn clusters of (cluster spin x size) / N;
              each cluster trades with probability 2a (Cont & Bouchaud 2000 activity on the Ising
              model's own correlated clusters; this combination is ours, not a published model)
    bornholdt heat bath with the frustration field h_i = sum_j J_ij s_j - alpha_B s_i |M|, one
              sweep a day, r = M_t - M_{t-1} (Bornholdt 2001; Kaizoji et al. 2002)
    krawiecki synchronous heat bath with random couplings A xi(t) J_ij / lambda + h noise, r = M_t
              (Krawiecki, Holyst & Helbing 2002, "attractor bubbling")
"""

# ruff: noqa: NPY002  (numba kernels need the legacy np.random API)
import argparse
import datetime
import pickle
import sys
import textwrap
import time
from pathlib import Path

import matplotlib as mpl
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.figure import Figure
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
from numba import njit
from scipy import optimize, stats

# ----------------------------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------------------------

FULL = {"cal_days": 8_000, "cal_seeds": 2, "eval_days": 20_000, "eval_seeds": 4,
        "n_windows": 400, "n_boot": 2_000}
QUICK = {"cal_days": 3_000, "cal_seeds": 1, "eval_days": 6_000, "eval_seeds": 2,
         "n_windows": 120, "n_boot": 500}
WINDOW = 20        # feedback window in days, as in the deployed model
BLOCK = 50         # moving-block length (days) for the bootstrap of the target's moments
HILL_FRAC = 0.05   # Hill estimator on the largest 5% of |r|, as in Franke & Westerhoff
HILL_CAP = 30.0    # bounded or discrete returns can give an infinite Hill index
BURN = {"ours": 500, "bornholdt": 2_000, "krawiecki": 2_000}

TARGETED = ["E|z|", "AC(r,1)", "Hill", "AC|r| 1", "AC|r| 5", "AC|r| 10", "AC|r| 25"]
UNTARGETED = ["kurtosis", "kurtosis 5d", "P(|z|>3)", "AC(r²,1)"]

MODELS = {
    "level": {"n_par": 2, "label": "Level, r = m (current)", "family": "ours", "mapping": "level",
              "grid": {"alpha": [0.0, 0.2, 0.4, 0.55, 0.7, 0.85, 1.0, 1.2], "k": [18, 36, 72]},
              "source": "Excess demand moves the price; Cont & Bouchaud (2000), Krawiecki et al. "
                        "(2002) use the same mapping"},
    "change": {"n_par": 2, "label": "Change, r = Δm", "family": "ours", "mapping": "change",
               "grid": {"alpha": [0.0, 0.4, 0.8, 1.2, 1.6], "k": [1, 2, 4, 8]},
               "source": "Market clearing against fundamentalists: Kaizoji, Bornholdt & Fujiwara "
                         "(2002)"},
    "cluster": {"n_par": 2, "label": "Cluster trading", "family": "ours", "mapping": "cluster",
                "grid": {"alpha": [0.0, 0.4, 0.8, 1.2, 1.6],
                         "a": [0.04, 0.07, 0.1, 0.15, 0.2, 0.3]},
                "fixed": {"k": 36},
                "source": "Cont & Bouchaud (2000) activity on Fortuin-Kasteleyn clusters "
                          "(combination ours)"},
    "cluster_stable": {"n_par": 2, "label": "Cluster trading, α ≤ 0.8", "family": "ours",
                       "mapping": "cluster",
                       "grid": {"alpha": [0.0, 0.2, 0.4, 0.6, 0.8],
                                "a": [0.04, 0.07, 0.1, 0.15, 0.2, 0.3]},
                       "fixed": {"k": 36},
                       "source": "as above, with the feedback kept in the range where T stays "
                                 "near T0"},
    "bornholdt": {"n_par": 2, "label": "Bornholdt frustration", "family": "bornholdt",
                  "mapping": "change",
                  "grid": {"theta": [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
                           "alpha_rel": [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]},
                  "source": "Bornholdt (2001); returns as in Kaizoji, Bornholdt & Fujiwara (2002)"},
    "krawiecki": {"n_par": 2, "label": "Random couplings", "family": "krawiecki",
                  "mapping": "level",
                  "grid": {"A": [1.2, 1.4, 1.6, 1.8, 2.0, 2.4], "h": [0.003, 0.01, 0.03, 0.1]},
                  "source": "Krawiecki, Hołyst & Helbing (2002)"},
    "garch": {"n_par": 4, "label": "GARCH(1,1)-t", "family": "garch",
              "source": "Bollerslev (1986, 1987); fitted by maximum likelihood"},
    "gauss": {"n_par": 0, "label": "Gaussian i.i.d.", "family": "gauss", "source": "null model"},
}

SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SHADE = "#e1e0d9", "#c3c2b7", "#f0efec"
BLUE, ORANGE = "#2a78d6", "#eb6834"
DIVERGING = ["#184f95", "#3987e5", "#9ec5f4", "#f0efec", "#f5a3a2", "#e34948", "#a32c2b"]


# ----------------------------------------------------------------------------------------------
# Simulation kernels
# ----------------------------------------------------------------------------------------------

@njit(cache=False)
def _find(parent, i):
    root = i
    while parent[root] != root:
        root = parent[root]
    while parent[i] != root:
        nxt = parent[i]
        parent[i] = root
        i = nxt
    return root


@njit(cache=False)
def _ours_kernel(J, T0, k, alpha, sigma0, mapping, act, n_days, n_burn, seed, window, T_lo, T_hi):
    """The calibrated model: k Metropolis sweeps a day, then the day's return, then the volatility
    feedback T = T0 (sigma/sigma0)^-alpha with sigma the std of the last `window` daily returns,
    as in _deploy_kernel. The return depends on `mapping`:
      0  level:   r = m
      1  change:  r = m - m_previous_day
      2  cluster: Fortuin-Kasteleyn clusters are built at the current T (bond between aligned
                  i, j with probability 1 - exp(-2 J_ij / T)); each cluster trades its spin x size
                  with probability 2 act; r = the sum over trading clusters / N."""
    np.random.seed(seed)
    N = J.shape[0]
    s = np.empty(N)
    for i in range(N):
        s[i] = 1.0 if np.random.random() < 0.5 else -1.0
    r_out = np.empty(n_days)
    T_out = np.empty(n_days)
    buf = np.zeros(window)
    parent = np.empty(N, np.int64)
    size = np.empty(N, np.int64)
    T = T0
    m_prev = s.sum() / N
    for d in range(n_burn + n_days):
        for _ in range(k * N):
            i = np.random.randint(N)
            f = 0.0
            for j in range(N):
                f += J[i, j] * s[j]
            dE = 2.0 * s[i] * f
            if dE <= 0.0 or np.random.random() < np.exp(-dE / T):
                s[i] = -s[i]
        m = s.sum() / N
        if mapping == 0:
            r = m
        elif mapping == 1:
            r = m - m_prev
        else:
            for i in range(N):
                parent[i] = i
                size[i] = 0
            for i in range(N):
                for j in range(i + 1, N):
                    if J[i, j] > 0.0 and s[i] == s[j]:
                        if np.random.random() < 1.0 - np.exp(-2.0 * J[i, j] / T):
                            ri = _find(parent, i)
                            rj = _find(parent, j)
                            if ri != rj:
                                parent[ri] = rj
            for i in range(N):
                size[_find(parent, i)] += 1
            r = 0.0
            for i in range(N):
                if size[i] > 0 and np.random.random() < 2.0 * act:
                    r += s[i] * size[i]
            r /= N
        m_prev = m
        buf[d % window] = r
        if d >= window - 1:
            sig = buf.std()
            if sig > 0.0:
                T = T0 * (sig / sigma0) ** (-alpha)
            if T < T_lo:
                T = T_lo
            elif T > T_hi:
                T = T_hi
        if d >= n_burn:
            r_out[d - n_burn] = r
            T_out[d - n_burn] = T
    return r_out, T_out


@njit(cache=False)
def _bornholdt_kernel(J, T, alpha_b, n_days, n_burn, seed):
    """Bornholdt (2001), simplified field (his eq. 4): h_i = sum_j J_ij s_j - alpha_b s_i |M|,
    heat-bath updates in random order, one sweep per day. Returns M after each day."""
    np.random.seed(seed)
    N = J.shape[0]
    s = np.empty(N)
    tot = 0.0
    for i in range(N):
        s[i] = 1.0 if np.random.random() < 0.5 else -1.0
        tot += s[i]
    out = np.empty(n_days)
    for d in range(n_burn + n_days):
        for _ in range(N):
            i = np.random.randint(N)
            f = 0.0
            for j in range(N):
                f += J[i, j] * s[j]
            h = f - alpha_b * s[i] * abs(tot / N)
            new = 1.0 if np.random.random() < 1.0 / (1.0 + np.exp(-2.0 * h / T)) else -1.0
            if new != s[i]:
                tot += 2.0 * new
                s[i] = new
        if d >= n_burn:
            out[d - n_burn] = tot / N
    return out


@njit(cache=False)
def _krawiecki_kernel(J, lam, A, h, n_days, n_burn, seed):
    """Krawiecki, Holyst & Helbing (2002): synchronous heat bath with local field
    I_i = A xi(t) (sum_j J_ij s_j) / lambda + h zeta_i(t), xi and zeta uniform on (-1, 1).
    Normalising by lambda_max makes the mean-field map along the market mode x -> A xi x.
    Returns the mean spin x(t)."""
    np.random.seed(seed)
    N = J.shape[0]
    s = np.empty(N)
    new = np.empty(N)
    for i in range(N):
        s[i] = 1.0 if np.random.random() < 0.5 else -1.0
    out = np.empty(n_days)
    for d in range(n_burn + n_days):
        xi = 2.0 * np.random.random() - 1.0
        for i in range(N):
            f = 0.0
            for j in range(N):
                f += J[i, j] * s[j]
            field = A * xi * f / lam + h * (2.0 * np.random.random() - 1.0)
            new[i] = 1.0 if np.random.random() < 1.0 / (1.0 + np.exp(-2.0 * field)) else -1.0
        for i in range(N):
            s[i] = new[i]
        if d >= n_burn:
            out[d - n_burn] = s.sum() / N
    return out


# ----------------------------------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------------------------------

class Context:
    """Everything the simulators need: the network, the calibrated row and cached sigma0(k)."""

    def __init__(self, J, cons):
        self.J = np.ascontiguousarray(J, dtype=np.float64)
        self.lam = float(np.linalg.eigvalsh(J).max())
        self.T0, self.eps = float(cons["T0"]), float(cons["eps"])
        self._sigma0 = {}

    def sigma0(self, k, mapping, act):
        """Baseline 20-day std of the daily returns at alpha = 0 (the feedback's reference)."""
        key = (k, mapping, act)
        if key not in self._sigma0:
            r, _ = _ours_kernel(self.J, self.T0, k, 0.0, 1.0, mapping, act, 4_000, BURN["ours"],
                                99, WINDOW, 0.05 * self.T0, 20 * self.T0)
            win = np.lib.stride_tricks.sliding_window_view(r, WINDOW)
            self._sigma0[key] = float(win.std(axis=1).mean())
        return self._sigma0[key]


MAPPING_CODE = {"level": 0, "change": 1, "cluster": 2}


def simulate(ctx, name, p, n_days, seed, with_T=False):
    """Daily returns of model `name` with parameters p (and, for our model, T/T0 each day)."""
    spec = MODELS[name]
    fam = spec["family"]
    if fam == "ours":
        k, act = int(p["k"]), p.get("a", 0.0)
        code = MAPPING_CODE[spec["mapping"]]
        r, T = _ours_kernel(ctx.J, ctx.T0, k, p["alpha"], ctx.sigma0(k, code, act), code, act,
                            n_days, BURN["ours"], seed, WINDOW, 0.05 * ctx.T0, 20 * ctx.T0)
        return (r, T / ctx.T0) if with_T else r
    if fam == "bornholdt":
        M = _bornholdt_kernel(ctx.J, p["theta"] * ctx.lam, p["alpha_rel"] * ctx.lam, n_days + 1,
                              BURN["bornholdt"], seed)
        return np.diff(M)
    if fam == "krawiecki":
        return _krawiecki_kernel(ctx.J, ctx.lam, p["A"], p["h"], n_days, BURN["krawiecki"], seed)
    if fam == "garch":
        return garch_simulate(p, n_days, seed)
    return np.random.default_rng(seed).standard_normal(n_days)


def grid_points(spec):
    keys = list(spec.get("grid", {}))
    if not keys:
        return [dict(spec.get("fixed", {}))]
    mesh = np.meshgrid(*[spec["grid"][key] for key in keys], indexing="ij")
    return [dict(zip(keys, (float(v.flat[i]) for v in mesh), strict=True)) | spec.get("fixed", {})
            for i in range(mesh[0].size)]


# GARCH(1,1) with unit-variance Student-t innovations ----------------------------------------------

def _garch_nll(theta, z):
    omega, a, b, nu = theta
    if omega <= 0 or a < 0 or b < 0 or a + b >= 0.999 or nu <= 2.05:
        return 1e10
    s2 = np.empty_like(z)
    s2[0] = z.var()
    for t in range(1, len(z)):
        s2[t] = omega + a * z[t - 1] ** 2 + b * s2[t - 1]
    scale = np.sqrt(s2 * (nu - 2) / nu)
    return -np.sum(stats.t.logpdf(z / scale, nu) - np.log(scale))


def garch_fit(r):
    z = (r - r.mean()) / r.std()
    best = None
    for start in ([0.05, 0.08, 0.87, 6.0], [0.1, 0.05, 0.85, 8.0], [0.02, 0.1, 0.88, 4.0]):
        res = optimize.minimize(_garch_nll, start, args=(z,), method="Nelder-Mead",
                                options={"maxiter": 4000, "xatol": 1e-6, "fatol": 1e-6})
        if best is None or res.fun < best.fun:
            best = res
    omega, a, b, nu = best.x
    return {"omega": omega, "a": a, "b": b, "nu": nu, "nll": best.fun}


def garch_simulate(p, n_days, seed, burn=500):
    rng = np.random.default_rng(seed)
    nu = p["nu"]
    eps = rng.standard_t(nu, n_days + burn) * np.sqrt((nu - 2) / nu)
    out = np.empty(n_days + burn)
    s2 = p["omega"] / (1 - p["a"] - p["b"])
    prev = 0.0
    for t in range(n_days + burn):
        s2 = p["omega"] + p["a"] * prev ** 2 + p["b"] * s2
        prev = np.sqrt(s2) * eps[t]
        out[t] = prev
    return out[burn:]


# ----------------------------------------------------------------------------------------------
# Moments
# ----------------------------------------------------------------------------------------------

def _acf(x, max_lag):
    x = x - x.mean()
    n = len(x)
    f = np.fft.rfft(x, 2 * n)
    r = np.fft.irfft(f * np.conj(f), 2 * n)[: max_lag + 1]
    return r / r[0] if r[0] > 0 else np.full(max_lag + 1, np.nan)


def hill(a, frac=HILL_FRAC):
    """Hill (1975) tail index of |returns| from the largest frac of observations."""
    x = np.sort(a)[::-1]
    k = max(int(frac * len(x)), 2)
    if x[k] <= 0:
        return HILL_CAP
    h = np.mean(np.log(x[:k] / x[k]))
    return HILL_CAP if h <= 1 / HILL_CAP else 1 / h


def moments(r):
    """Scale-free stylised facts of a return series (standardised first). Targeted moments follow
    Franke & Westerhoff (2012) with lags that a 753-day sample can support; AC values at lag L are
    averages over lags L-1..L+1 (lags 1-2 for lag 1)."""
    r = np.asarray(r, dtype=float)
    sd = r.std()
    if not np.isfinite(sd) or sd == 0:
        return {key: np.nan for key in TARGETED + UNTARGETED}
    z = (r - r.mean()) / sd
    a = np.abs(z)
    ac, aa, a2 = _acf(z, 30), _acf(a, 30), _acf(z ** 2, 2)
    n5 = len(z) // 5
    z5 = z[: 5 * n5].reshape(n5, 5).sum(axis=1)
    return {
        "E|z|": a.mean(), "AC(r,1)": ac[1], "Hill": hill(a),
        "AC|r| 1": aa[1:3].mean(), "AC|r| 5": aa[4:7].mean(), "AC|r| 10": aa[9:12].mean(),
        "AC|r| 25": aa[24:27].mean(),
        "kurtosis": np.mean(z ** 4), "kurtosis 5d": stats.kurtosis(z5, fisher=False),
        "P(|z|>3)": np.mean(a > 3), "AC(r²,1)": a2[1],
    }


def vec(m, keys=TARGETED):
    return np.array([m[key] for key in keys])


def block_bootstrap(r, n_boot, block, seed=0):
    """Moving-block bootstrap of the target's moments (all of them)."""
    rng = np.random.default_rng(seed)
    n = len(r)
    n_blocks = int(np.ceil(n / block))
    out = []
    for _ in range(n_boot):
        starts = rng.integers(0, n - block + 1, n_blocks)
        sample = np.concatenate([r[s:s + block] for s in starts])[:n]
        out.append(moments(sample))
    return out


def j_stat(m, target, W, keys=TARGETED):
    d = vec(m, keys) - vec(target, keys)
    return float(d @ W @ d)


# ----------------------------------------------------------------------------------------------
# Calibration and evaluation
# ----------------------------------------------------------------------------------------------

def calibrate(ctx, name, target, W, mode, log):
    spec = MODELS[name]
    if spec["family"] in ("garch", "gauss"):
        return None, []
    results = []
    for p in grid_points(spec):
        ms = [moments(simulate(ctx, name, p, mode["cal_days"], 1000 + s))
              for s in range(mode["cal_seeds"])]
        m = {key: float(np.nanmean([x[key] for x in ms])) for key in ms[0]}
        J = j_stat(m, target, W) if np.all(np.isfinite(vec(m))) else np.inf
        results.append((J, p, m))
    results.sort(key=lambda x: x[0])
    # Stage 2: re-score the best few with evaluation-length runs, so the winner isn't a lucky draw
    finalists = []
    for J_grid, p, _ in results[:3]:
        ms = [moments(simulate(ctx, name, p, mode["eval_days"], 3000 + s))
              for s in range(mode["eval_seeds"])]
        m = {key: float(np.nanmean([x[key] for x in ms])) for key in ms[0]}
        J = j_stat(m, target, W) if np.all(np.isfinite(vec(m))) else np.inf
        finalists.append((J, p))
        log.write(f"{name}: grid J = {J_grid:.1f}, re-scored J = {J:.1f} at {p}\n")
    best = min(finalists, key=lambda x: x[0])
    log.write(f"{name}: chosen {best[1]}\n")
    return best[1], [(J, p) for J, p, _ in results]


def evaluate(ctx, name, p, target, W, mode, n_target):
    """Long-run moments, and the distribution of every moment over target-length windows."""
    long_runs = [simulate(ctx, name, p, mode["eval_days"], 5000 + s)
                 for s in range(mode["eval_seeds"])]
    T_rel = None
    if MODELS[name]["family"] == "ours":
        T_rel = simulate(ctx, name, p, mode["eval_days"], 5000, with_T=True)[1]
    ms = [moments(r) for r in long_runs]
    m_long = {key: float(np.nanmean([x[key] for x in ms])) for key in ms[0]}
    J_runs = [j_stat(x, target, W) for x in ms]
    windows, acfs, n_per_run = [], [], max(1, mode["n_windows"] // 20)
    seed = 9000
    while len(windows) < mode["n_windows"]:
        r = simulate(ctx, name, p, n_target * n_per_run, seed)
        seed += 1
        for i in range(n_per_run):
            w = r[i * n_target:(i + 1) * n_target]
            windows.append(moments(w))
            acfs.append(_acf(np.abs(w - w.mean()) / max(w.std(), 1e-12), 30)[1:])
    windows, acfs = windows[: mode["n_windows"]], np.array(acfs[: mode["n_windows"]])
    J_data = j_stat(m_long, target, W)
    J_win = np.array([j_stat(w, m_long, W) for w in windows])
    return {"params": p, "long": m_long, "windows": windows, "acf_windows": acfs,
            "J": J_data, "J_runs": (float(min(J_runs)), float(max(J_runs))),
            "p_J": float(np.mean(J_win >= J_data)),
            "T_mean": None if T_rel is None else float(T_rel.mean()),
            "example": long_runs[0][:n_target], "long_sample": long_runs[0].astype(np.float32)}


def coverage(windows, target, se):
    """Per-moment share of model windows inside the target's 95% CI, and the share with all
    targeted moments inside at once (the moment coverage ratio of Franke & Westerhoff)."""
    inside = {key: np.array([abs(w[key] - target[key]) <= 1.96 * se[key] for w in windows])
              for key in target}
    joint = np.mean(np.all([inside[key] for key in TARGETED], axis=0))
    return {key: float(v.mean()) for key, v in inside.items()}, float(joint)


def lattice(L):
    """Coupling matrix of an L x L periodic square lattice with J = 1 between neighbours."""
    N = L * L
    J = np.zeros((N, N))
    for i in range(L):
        for j in range(L):
            a = i * L + j
            for di, dj in ((1, 0), (0, 1)):
                b = ((i + di) % L) * L + (j + dj) % L
                J[a, b] = J[b, a] = 1.0
    return J


def scaling_checks(mode):
    """The two published dynamics at the published settings, over a range of system sizes:
    Krawiecki et al. all-to-all at A = 1.6, h = 0.01 (their Fig. 1-2), and Bornholdt at T = 1,
    alpha = 8 (his Figs. 3-4) on a square lattice and all-to-all with the same zJ = 4.
    Checks that the kernels reproduce the papers at their scale, and shows what N does."""
    n_days = 20_000 if mode is FULL else 5_000
    out = {"krawiecki": [], "bornholdt_lattice": [], "bornholdt_mf": []}
    for N in (29, 100, 300, 1000):
        J = np.full((N, N), 1.0 / N)
        np.fill_diagonal(J, 0.0)
        x = _krawiecki_kernel(J, (N - 1) / N, 1.6, 0.01, n_days, BURN["krawiecki"], 2)
        out["krawiecki"].append((N, moments(x)))
    for L in (6, 12, 20, 32):
        M = _bornholdt_kernel(lattice(L), 1.0, 8.0, n_days + 1, BURN["bornholdt"], 2)
        out["bornholdt_lattice"].append((L * L, moments(np.diff(M))))
    for N in (36, 144, 400, 1024):
        J = np.full((N, N), 4.0 / N)
        np.fill_diagonal(J, 0.0)
        M = _bornholdt_kernel(J, 1.0, 8.0, n_days + 1, BURN["bornholdt"], 2)
        out["bornholdt_mf"].append((N, moments(np.diff(M))))
    return out


def compute(args, mode):
    with open(args.figdata, "rb") as f:
        fd = pickle.load(f)
    if fd["cons"] is None:
        sys.exit("figdata.pkl has no recommended row: run make_figures.py on data that calibrates")
    ctx = Context(fd["net"]["J"], fd["cons"])
    if args.target_csv:
        r_target = np.loadtxt(args.target_csv, delimiter=",", ndmin=1)
        target_name = Path(args.target_csv).name
    else:
        r_target = np.asarray(fd["index"], dtype=float)
        target_name = (f"equal-weight index of the {fd['net']['N']} stocks, "
                       f"{fd['net']['start']} to {fd['net']['end']}")
    target = moments(r_target)
    print(f"Target: {target_name} ({len(r_target)} days)")

    t0 = time.time()
    boot = block_bootstrap(r_target, mode["n_boot"], BLOCK)
    allkeys = TARGETED + UNTARGETED
    se = {key: float(np.nanstd([b[key] for b in boot])) for key in allkeys}
    cov = np.cov(np.array([vec(b) for b in boot]).T)
    W = np.linalg.inv(cov)
    print(f"Bootstrap of the target's moments: {mode['n_boot']} samples, block {BLOCK} days")

    out_dir = Path(args.out)
    res, grids = {}, {}
    with open(out_dir / "calibration_log.txt", "w") as log:
        for name, spec in MODELS.items():
            t1 = time.time()
            if spec["family"] == "garch":
                p = garch_fit(r_target)
            else:
                p, grids[name] = calibrate(ctx, name, target, W, mode, log)
                p = p or {}
            res[name] = evaluate(ctx, name, p, target, W, mode, len(r_target))
            res[name]["coverage"], res[name]["mcr"] = coverage(res[name]["windows"], target, se)
            print(f"  {name:10s} J = {res[name]['J']:8.1f}  p = {res[name]['p_J']:.3f}  "
                  f"({time.time() - t1:.0f} s)", flush=True)
    t1 = time.time()
    scaling = scaling_checks(mode)
    print(f"  literature checks at larger N ({time.time() - t1:.0f} s)")
    return {
        "scaling": scaling,
        "created": str(datetime.datetime.now().replace(microsecond=0)), "mode": mode,
        "target_name": target_name, "r_target": r_target, "target": target, "se": se,
        "W": W, "res": res, "grids": grids, "T0_lam": ctx.T0 / ctx.lam, "eps": ctx.eps,
        "runtime_s": time.time() - t0,
    }


# ----------------------------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------------------------

def set_style():
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "sans-serif", "font.size": 9.5, "mathtext.fontset": "dejavusans",
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK2,
        "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlecolor": INK,
        "axes.titlelocation": "left", "axes.titlepad": 6,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True,
        "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
        "xtick.color": AXIS, "ytick.color": AXIS, "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "lines.linewidth": 1.6, "lines.markersize": 6,
        "legend.frameon": False, "legend.fontsize": 8.5, "legend.labelcolor": INK2,
        "savefig.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.15,
    })


def new_figure(width, height, title, subtitle):
    title = textwrap.fill(title, int(width * 10.5))
    subtitle = textwrap.fill(subtitle, int(width * 13.5))
    n_t, n_s = title.count("\n") + 1, subtitle.count("\n") + 1
    head = 0.12 + 0.24 * n_t + 0.19 * n_s
    fig = Figure(figsize=(width, height + head), layout="constrained")
    fig.get_layout_engine().set(rect=(0, 0, 1, 1 - head / (height + head)))
    fig.text(0.012, 1 - 0.08 / (height + head), title, ha="left", va="top", fontsize=12,
             fontweight="bold", color=INK)
    fig.text(0.012, 1 - (0.12 + 0.24 * n_t) / (height + head), subtitle, ha="left", va="top",
             fontsize=9, color=INK2)
    return fig


def ranked(d):
    return sorted(d["res"], key=lambda name: d["res"][name]["J"])


def short(name):
    return MODELS[name]["label"]


def param_text(name, p):
    if MODELS[name]["family"] == "garch":
        return f"a = {p['a']:.2f}, b = {p['b']:.2f}, ν = {p['nu']:.1f}"
    if not p:
        return "no parameters"
    fmt = {"alpha": "α = {:g}", "k": "k = {:g}", "a": "a = {:g}", "theta": "T = {:g} λ",
           "alpha_rel": "α_B = {:g} λ", "A": "A = {:g}", "h": "h = {:g}"}
    return ", ".join(fmt[key].format(v) for key, v in p.items())


def survival(z):
    a = np.sort(np.abs(z))[::-1]
    return a, np.arange(1, len(a) + 1) / len(a)


def fig_tails(d):
    order = ranked(d)
    zt = (d["r_target"] - d["r_target"].mean()) / d["r_target"].std()
    xt, yt = survival(zt)
    t = d["target"]
    title = "Tails: which mechanisms can produce market-sized moves"
    subtitle = (f"Probability that |return| exceeds x standard deviations, log-log. Dark: "
                f"{d['target_name']} (Hill index {t['Hill']:.1f}, kurtosis {t['kurtosis']:.1f}). "
                f"Blue: each calibrated model, one {d['mode']['eval_days']:,}-day run. "
                "Grey: Gaussian. Panels ordered by overall fit (J).")
    n = len(order)
    cols = 4
    rows = int(np.ceil(n / cols))
    fig = new_figure(12, 2.9 * rows, title, subtitle)
    axes = fig.subplots(rows, cols, sharex=True, sharey=True).ravel()
    xs = np.logspace(-1, np.log10(8), 200)
    for ax, name in zip(axes, order, strict=False):
        e = d["res"][name]
        zm = e["long_sample"].astype(float)
        zm = (zm - zm.mean()) / zm.std()
        ax.plot(xs, 2 * stats.norm.sf(xs), color=MUTED, lw=1.0)
        xm, ym = survival(zm)
        ax.plot(xm, ym, color=BLUE, lw=1.6)
        ax.plot(xt, yt, color=INK, lw=1.2)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(0.3, 8)
        ax.xaxis.set_major_locator(FixedLocator([0.5, 1, 2, 4, 8]))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_ylim(1 / len(zt) / 1.5, 1.2)
        L = e["long"]
        ax.set_title(f"{short(name)}\nHill {L['Hill']:.1f}, kurtosis {L['kurtosis']:.1f}",
                     fontsize=9)
    for ax in axes[n:]:
        ax.set_visible(False)
    for ax in axes[::cols]:
        ax.set_ylabel("P(|z| > x)")
    for ax in axes[-cols:]:
        ax.set_xlabel("x (standard deviations)")
    return fig


def fig_clustering(d):
    order = ranked(d)
    zt = (d["r_target"] - d["r_target"].mean()) / d["r_target"].std()
    lags = np.arange(1, 31)
    at = _acf(np.abs(zt), 30)[1:]
    band = 2 / np.sqrt(len(zt))
    title = "Volatility clustering: autocorrelation of absolute returns"
    subtitle = ("Dark: target index. Blue: model median over windows as long as the target; band: "
                "its 5-95% range. Grey band: ±2/√n noise around zero for the target's length.")
    n = len(order)
    cols = 4
    rows = int(np.ceil(n / cols))
    fig = new_figure(12, 2.6 * rows, title, subtitle)
    axes = fig.subplots(rows, cols, sharex=True, sharey=True).ravel()
    for ax, name in zip(axes, order, strict=False):
        acs = d["res"][name]["acf_windows"]
        ax.axhspan(-band, band, color=SHADE, lw=0)
        ax.axhline(0, color=INK2, lw=0.8)
        ax.fill_between(lags, np.percentile(acs, 5, axis=0), np.percentile(acs, 95, axis=0),
                        color=BLUE, alpha=0.15, lw=0)
        ax.plot(lags, np.median(acs, axis=0), color=BLUE, lw=1.6)
        ax.plot(lags, at, color=INK, lw=1.2)
        ax.set_title(short(name), fontsize=9)
    for ax in axes[n:]:
        ax.set_visible(False)
    for ax in axes[::cols]:
        ax.set_ylabel("AC(|r|)")
    for ax in axes[-cols:]:
        ax.set_xlabel("lag (days)")
    return fig


def fig_scorecard(d):
    order = ranked(d)
    keys = TARGETED + UNTARGETED
    se, t = d["se"], d["target"]
    dev = np.array([[(d["res"][n]["long"][k] - t[k]) / se[k] for k in keys] for n in order])
    dev = np.nan_to_num(dev, nan=0.0, posinf=999.0, neginf=-999.0)
    shown = np.clip(dev, -10, 10)
    title = "Scorecard: how far each model's moments sit from the market's"
    subtitle = ("Cells: (model − target) / bootstrap standard error of the target, so |value| < 2 "
                "is within sampling noise. Left block: moments used for calibration; right block: "
                "held out. Rows ordered by J; colour clipped at ±10.")
    fig = new_figure(12, 0.42 * len(order) + 1.4, title, subtitle)
    gs = fig.add_gridspec(1, 2, width_ratios=[len(keys), 3.2])
    ax = fig.add_subplot(gs[0, 0])
    cmap = LinearSegmentedColormap.from_list("div", DIVERGING)
    ax.imshow(shown, cmap=cmap, norm=TwoSlopeNorm(0, -10, 10), aspect="auto")
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(len(order)):
        for j in range(len(keys)):
            v = dev[i, j]
            txt = f"{v:+.1f}" if abs(v) < 100 else ("≫ 0" if v > 0 else "≪ 0")
            ax.text(j, i, txt, ha="center", va="center", fontsize=7.5,
                    color="white" if abs(shown[i, j]) > 6 else INK)
    ax.axvline(len(TARGETED) - 0.5, color=SURFACE, lw=4)
    ax.set_xticks(range(len(keys)), keys, rotation=35, ha="right", fontsize=8)
    ax.set_yticks(range(len(order)), [short(n) for n in order], fontsize=8.5)
    ax.tick_params(length=0)
    ax.xaxis.set_ticks_position("top")
    ax.set_title("Standardised distance from the target", pad=40)

    ax = fig.add_subplot(gs[0, 1])
    J = np.array([d["res"][n]["J"] for n in order])
    y = np.arange(len(order))
    ax.barh(y, J, height=0.55, color=BLUE)
    for yi, n in zip(y, order, strict=True):
        e = d["res"][n]
        ax.annotate(f"J = {e['J']:.0f}, p = {e['p_J']:.2f}", (J[yi], yi), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=7.5, color=INK2)
    ax.set_xscale("log")
    ax.set_ylim(len(order) - 0.5, -0.5)
    ax.set_yticks([])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("J (log scale; lower is better)")
    ax.set_title("Overall distance J", pad=40)
    ax.set_xlim(J.min() / 2, J.max() * 30)
    return fig


def fig_paths(d):
    order = ranked(d)
    zt = (d["r_target"] - d["r_target"].mean()) / d["r_target"].std()
    n = len(zt)
    title = "What a market-length sample from each model looks like"
    subtitle = (f"Standardised daily returns, {n} days each. Top: the target index. Below: one "
                "run of each calibrated model, in order of fit.")
    fig = new_figure(12, 1.15 * (len(order) + 1), title, subtitle)
    axes = fig.subplots(len(order) + 1, 1, sharex=True, sharey=True)
    lim = 1.05 * max(np.abs(zt).max(), max(np.abs(
        (d["res"][m]["example"] - d["res"][m]["example"].mean())
        / d["res"][m]["example"].std()).max() for m in order))
    lim = min(lim, 12)
    series = [("Target index", zt, INK)] + [
        (f"{short(m)}  ({param_text(m, d['res'][m]['params'])})",
         (d["res"][m]["example"] - d["res"][m]["example"].mean()) / d["res"][m]["example"].std(),
         BLUE) for m in order]
    for ax, (label, z, colour) in zip(axes, series, strict=True):
        ax.plot(np.arange(len(z)), z, color=colour, lw=0.6)
        ax.set_ylim(-lim, lim)
        ax.set_xlim(0, n)
        ax.set_title(label, fontsize=8.5, pad=2)
        ax.grid(axis="x", visible=False)
    axes[-1].set_xlabel("trading day")
    return fig


def fig_scaling(d):
    sc, t, se = d["scaling"], d["target"], d["se"]
    series = [("krawiecki", "Random couplings, all-to-all (A = 1.6, h = 0.01)", BLUE, "o"),
              ("bornholdt_lattice", "Bornholdt, square lattice (T = 1, α = 8)", ORANGE, "s"),
              ("bornholdt_mf", "Bornholdt, all-to-all (same zJ)", "#1baf7a", "D")]
    title = ("The published mechanisms need many agents, and Bornholdt's also needs local "
             "structure")
    subtitle = ("The two published dynamics at their papers' settings, one long run per size. "
                "Grey band: the target index ± 1.96 bootstrap SE. Hollow markers: the same "
                "dynamics calibrated on your 29-stock network.")
    fig = new_figure(12, 3.8, title, subtitle)
    axes = fig.subplots(1, 3)
    for ax, key, label in zip(axes, ("Hill", "kurtosis", "AC|r| 10"),
                              ("Hill tail index (lower = fatter)", "kurtosis",
                               "AC(|r|) around lag 10"), strict=True):
        lo, hi = t[key] - 1.96 * se[key], t[key] + 1.96 * se[key]
        ax.axhspan(lo, hi, color=SHADE, lw=0)
        ax.axhline(t[key], color=INK2, lw=0.9)
        for name, lab, colour, mk in series:
            Ns = [n for n, _ in sc[name]]
            vals = [m[key] for _, m in sc[name]]
            ax.plot(Ns, vals, mk + "-", color=colour, mec=SURFACE, mew=1, label=lab)
        for name, colour, mk in (("krawiecki", BLUE, "o"), ("bornholdt", ORANGE, "s")):
            if name in d["res"]:
                ax.plot([29], [d["res"][name]["long"][key]], mk, color=SURFACE, mec=colour,
                        mew=1.6, ms=8)
        ax.set_xscale("log")
        ax.set_xlabel("number of agents N")
        ax.set_title(label)
    axes[0].legend(loc="upper right", fontsize=7.5)
    return fig


# ----------------------------------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------------------------------

def write_tables(d, out):
    order = ranked(d)
    t, se = d["target"], d["se"]
    keys = TARGETED + UNTARGETED
    L = [
        "# Return models compared", "",
        f"Generated {d['created']} in {d['runtime_s'] / 60:.1f} min. Target: {d['target_name']} "
        f"({len(d['r_target'])} days). Spin models run on the calibrated network at "
        f"T0 = {d['T0_lam']:.3f} λ_max (ε = {d['eps']:.2f}) where they use it.", "",
        "Calibration: grid search minimising J = (m − m*)' W (m − m*) over the targeted moments, "
        "with W the inverse bootstrap covariance of the target's moments (moving blocks of "
        f"{BLOCK} days). p is the share of model samples of the target's length whose J around the "
        "model's own long-run moments exceeds the target's J. MCR is the share of those samples "
        "with every targeted moment inside the target's 95% interval.", "",
        "## Ranking", "",
        "| rank | model | free parameters | calibrated values | J | J, single runs | p | MCR "
        "| mean T/T0 | source |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, n in enumerate(order, 1):
        e = d["res"][n]
        tt = "" if e["T_mean"] is None else f"{e['T_mean']:.2f}"
        L.append(f"| {i} | {short(n)} | {MODELS[n]['n_par']} | {param_text(n, e['params'])} | "
                 f"{e['J']:.1f} | {e['J_runs'][0]:.0f}-{e['J_runs'][1]:.0f} | "
                 f"{e['p_J']:.3f} | {e['mcr']:.3f} | {tt} | {MODELS[n]['source']} |")
    L += ["", "## Moments (long-run model values; target with bootstrap SE)", "",
          "| moment | target | " + " | ".join(short(n) for n in order) + " |",
          "|---|---|" + "---|" * len(order)]
    for k in keys:
        flag = "" if k in TARGETED else " (held out)"
        L.append(f"| {k}{flag} | {t[k]:.3f} ± {se[k]:.3f} | "
                 + " | ".join(f"{d['res'][n]['long'][k]:.3f}" for n in order) + " |")
    L += ["", "## Coverage: share of model samples inside the target's 95% interval", "",
          "| moment | " + " | ".join(short(n) for n in order) + " |",
          "|---|" + "---|" * len(order)]
    for k in keys:
        L.append(f"| {k} | " + " | ".join(f"{d['res'][n]['coverage'][k]:.2f}" for n in order)
                 + " |")
    (out / "return_models.md").write_text("\n".join(L) + "\n")
    print("  wrote return_models.md")


# ----------------------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--figdata", default="results/figures/figdata.pkl",
                   help="make_figures.py output: J, calibrated row and the target index")
    p.add_argument("--target-csv", default=None,
                   help="optional: a file of daily returns (one per line) to use as the target")
    p.add_argument("--out", default="results/return_models")
    p.add_argument("--quick", action="store_true")
    p.add_argument("--replot", action="store_true")
    p.add_argument("--formats", nargs="+", default=["png"])
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "compare.pkl"
    if args.replot:
        with open(cache, "rb") as f:
            d = pickle.load(f)
    else:
        d = compute(args, QUICK if args.quick else FULL)
        with open(cache, "wb") as f:
            pickle.dump(d, f)
    set_style()
    for name, make in (("figR1_tails", fig_tails), ("figR2_clustering", fig_clustering),
                       ("figR3_scorecard", fig_scorecard), ("figR4_paths", fig_paths),
                       ("figR5_scaling", fig_scaling)):
        fig = make(d)
        for fmt in args.formats:
            fig.savefig(out / f"{name}.{fmt}")
        print(f"  wrote {name}")
    write_tables(d, out)


if __name__ == "__main__":
    main()
