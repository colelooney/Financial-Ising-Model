"""Figures and a numbers summary for the calibrated financial Ising model.

Run from the repository root, after scripts/calibrate_real.py has frozen the inputs in data/:

    uv run python scripts/make_figures.py            # full run, a few minutes on a laptop
    uv run python scripts/make_figures.py --quick    # short runs, to check that everything works
    uv run python scripts/make_figures.py --replot   # redraw from results/figures/figdata.pkl

Everything is computed from the frozen returns and J; nothing is downloaded. Outputs (in --out):

    fig1_network.png        correlations kept in J, eigenvalue spectrum, market-mode loadings
    fig2_regimes.png        kurtosis, tau_int, k and the run checks across the T0 scan
    fig3_griffiths.png      why eps > 0 only appears where runs don't mix
    fig4_traces.png         m(t) and its distribution in each regime
    fig5_selection.png      eps per row and seed, and the first check each row failed
    fig6_feedback.png       clustering, operating point and kurtosis against the loop gain
    fig7_model_vs_data.png  model returns next to the equal-weight index of the same stocks
    summary.md              the numbers behind the figures
    figdata.pkl             everything needed to redraw (read by --replot)
    calibration_log.txt     the calibration's own printed reports
"""

import argparse
import contextlib
import datetime
import io
import pickle
import sys
import textwrap
import time
from pathlib import Path

import matplotlib as mpl
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_rgba
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
from scipy import stats

try:
    from ising_market import model as im
except ModuleNotFoundError:  # package not installed: use the src/ layout directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from ising_market import model as im


# ----------------------------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------------------------

# Only used to order the correlation heatmap; tickers not listed here go to "Other".
SECTORS = {
    "Tech": ["AAPL", "MSFT", "INTC", "CSCO", "AMD", "IBM", "ORCL", "TXN"],
    "Financials": ["JPM", "BAC", "GS", "WFC", "C"],
    "Energy": ["XOM", "CVX", "COP"],
    "Health care": ["JNJ", "PFE", "UNH", "MRK"],
    "Consumer": ["AMZN", "WMT", "HD", "MCD", "DIS", "TWX"],
    "Industrials": ["CAT", "GE", "MMM", "BA"],
}

FULL = {"n_pilot": 50_000, "n_burn": 10_000, "n_days": 10_000, "n_reps": 4}
QUICK = {"n_pilot": 10_000, "n_burn": 2_000, "n_days": 3_000, "n_reps": 2}
GAINS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5)  # loop gain G = alpha * |eps|
MAX_LAG = 50  # autocorrelation lags kept for plotting
WINDOW = 20  # rolling volatility window in days, as in the calibration and the deployed model

# Colours: the first three categorical slots of a colour-blind-checked palette, in fixed order,
# plus neutral inks. Every series is also named in a legend or a direct label.
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SHADE, SHADE_DARK = "#e1e0d9", "#c3c2b7", "#f0efec", "#e3e2dc"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GOOD = "#0ca30c"
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

REGIME_FILL = {"frozen": SHADE, "slow": SHADE_DARK, "mixing": None}
FAILURE_LABEL = {
    "equilibrated": "starts disagree",
    "converged": "not converged",
    "s_valid": "s undefined",
    "n_eff": "n_eff too small",
    "thinning": "thinned AC₁ too high",
    "zero_mean": "frozen (z test)",
    "eps_defined": "ε undefined",
    "eps_negative": "ε not below 0",
    "none": "pass",
}


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
        "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
        "legend.frameon": False, "legend.fontsize": 8.5, "legend.labelcolor": INK2,
        "savefig.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.15,
    })


# ----------------------------------------------------------------------------------------------
# Computation
# ----------------------------------------------------------------------------------------------

def acf(x, max_lag):
    """Autocorrelation of x at lags 0..max_lag (same definition as stylised_facts)."""
    x = np.asarray(x, dtype=float) - np.mean(x)
    n = len(x)
    f = np.fft.rfft(x, 2 * n)
    r = np.fft.irfft(f * np.conj(f), 2 * n)[: max_lag + 1]
    return r / r[0]


def return_facts(r):
    """Kurtosis and autocorrelations of a return series, matching im.stylised_facts."""
    a = np.abs(r - np.mean(r))
    acf_r, acf_a = acf(r, MAX_LAG), acf(a, MAX_LAG)
    return {
        "kurtosis": float(stats.kurtosis(r, fisher=False)),
        "ac_r1": float(acf_r[1]),
        "ac_abs_mean": float(acf_a[1:21].mean()),
        "acf_r": acf_r,
        "acf_abs": acf_a,
    }


def first_failure(criteria):
    """The first check each row fails, in select_T0's order ('none' for survivors)."""
    survivors = criteria.all(axis=1)
    ff = (~criteria).idxmax(axis=1)
    ff[survivors] = "none"
    return ff


def classify(tab):
    """Regime of each T0 row: 'slow' (runs don't converge), 'frozen' (zero-mean test fails), or
    'mixing'. Uses the pipeline's own thresholds."""
    conv = tab.frac_converged.to_numpy()
    z_high = tab.frac_z_high.to_numpy()
    return np.where(conv < im.MIN_FRAC_CONVERGED, "slow",
                    np.where(z_high > im.MAX_FRAC_Z_HIGH, "frozen", "mixing"))


def network_data(rets, J, threshold):
    C = rets.corr().to_numpy()
    N, T = C.shape[0], len(rets)
    evals, evecs = np.linalg.eigh(C)
    evals, evecs = evals[::-1], evecs[:, ::-1]
    v1 = evecs[:, 0] * np.sign(evecs[:, 0].sum())
    return {
        "tickers": list(rets.columns), "C": C, "J": J, "N": N, "T": T,
        "start": str(rets.index[0])[:10], "end": str(rets.index[-1])[:10],
        "threshold": threshold, "lam": float(np.linalg.eigvalsh(J).max()),
        "edges": int(np.count_nonzero(np.triu(J, 1))), "pairs": N * (N - 1) // 2,
        "evals": evals, "v1": v1, "mp_edge": (1 + np.sqrt(N / T)) ** 2,
    }


def primary_extras(runs, tab, n_pilot, k_fix, N):
    """Extra per-row numbers from one seed's raw runs: volatility at one fixed k, m histograms
    and one example trace per row (the runs themselves are too large to keep)."""
    s_fixed, hists, traces = [], [], {}
    stride = max(1, n_pilot // 5000)
    for i in sorted(tab.i_T0):
        group = [r for r in runs if r["i_T0"] == i]
        s_fixed.append(np.mean([im.thinned_stats(r["m"], k_fix, WINDOW)[1] for r in group]))
        hists.append(sum(np.histogram(r["m"], bins=hist_edges(N))[0] for r in group))
        trace = next(r for r in group if r["seed_id"] == 0 and r["start"] == "random")
        traces[i] = trace["m"][::stride].astype(np.float32)
    return {"k_fix": k_fix, "s_fixed": np.array(s_fixed), "hists": np.array(hists),
            "hist_N": N, "traces": traces, "trace_stride": stride}


def hist_edges(N):
    """Bin edges centred on the N + 1 values m can take, so each bin holds exactly one value."""
    return np.linspace(-1 - 1 / N, 1 + 1 / N, N + 2)


def run_calibrations(rets, J, seeds, n_pilot, n_burn, log):
    cal = {}
    run_keys = ("i_T0", "T0", "seed_id", "start", "sigma_m", "R", "tau_int", "converged", "z",
                "s_k", "ac1_k")
    for n, seed in enumerate(seeds):
        t0 = time.time()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = im.calibrate_parameters(rets, J, n_pilot=n_pilot, n_burn=n_burn, seed=seed,
                                          window=WINDOW)
        log.write(f"===== seed {seed} =====\n{buf.getvalue()}\n")
        tab = res["T0_table"].copy()
        tab["first_failure"] = first_failure(res["selection"]["criteria"]).to_numpy()
        tab["eps_ucb"] = tab.eps_mean + 2 * tab.eps_se
        entry = {
            "T0": res["T0"], "k": res["k"], "sigma0": res["sigma0"],
            "i_T0": res["selection"]["i_T0"], "table": tab,
            "runs": pd.DataFrame([{key: r[key] for key in run_keys} for r in res["runs"]]),
        }
        if n == 0:
            k_fix = res["k"] if res["k"] is not None else int(np.nanmedian(tab.k))
            entry["extras"] = primary_extras(res["runs"], tab, n_pilot, k_fix, J.shape[0])
        cal[seed] = entry
        win = "none" if res["T0"] is None else \
            f"T0/lam = {res['T0'] / res['lam']:.3f}, k = {res['k']}"
        print(f"  seed {seed}: winner {win}  ({time.time() - t0:.0f} s)", flush=True)
        del res
    return cal


def consensus_row(cal):
    """The row that survives in the most seeds; ties go to the most negative mean eps upper bound.
    k is the median over seeds, sigma0 and eps the means over seeds where they are defined."""
    tabs = [c["table"] for c in cal.values()]
    n_surv = sum((t.first_failure == "none").to_numpy().astype(int) for t in tabs)
    if n_surv.max() == 0:
        return None
    cand = np.flatnonzero(n_surv == n_surv.max())
    ucb = [np.mean([t.eps_ucb.iloc[i] for t in tabs if t.first_failure.iloc[i] == "none"])
           for i in cand]
    i = int(cand[np.argmin(ucb)])
    rows = [t.iloc[i] for t in tabs]
    return {
        "i": i, "T0": float(rows[0].T0), "n_surv": int(n_surv[i]), "n_seeds": len(tabs),
        "k": int(np.nanmedian([r.k for r in rows])),
        "sigma0": float(np.nanmean([r.s_mean for r in rows])),
        "eps": float(np.nanmean([r.eps_mean for r in rows])),
        "eps_by_seed": [float(r.eps_mean) for r in rows],
    }


def run_deployment(J, cons, gains, n_days, n_reps, showcase):
    rows, acfs, series = [], {}, {}
    for ig, G in enumerate(gains):
        alpha = G / abs(cons["eps"])
        for rep in range(n_reps):
            sim = im.simulate_deployed(J, cons["T0"], cons["k"], alpha, cons["sigma0"], n_days,
                                       rng=np.random.default_rng([2026, ig, rep]), window=WINDOW)
            f = return_facts(sim["r"])
            T_rel = sim["T"] / cons["T0"]
            rows.append({"G": G, "alpha": alpha, "rep": rep, "kurtosis": f["kurtosis"],
                         "ac_r1": f["ac_r1"], "ac_abs_mean": f["ac_abs_mean"],
                         "T_mean": float(T_rel.mean()), "T_cv": float(T_rel.std() / T_rel.mean()),
                         "clip": float(sim["clip_frac"])})
            if rep == 0:
                acfs[G] = (f["acf_r"], f["acf_abs"])
                if G in (0.0, showcase):
                    series[G] = (sim["r"].astype(np.float32), T_rel.astype(np.float32))
        print(f"  deployment G = {G:.2f}: done", flush=True)
    return {"table": pd.DataFrame(rows), "acfs": acfs, "series": series, "showcase": showcase}


def compute(args, mode):
    rets = pd.read_pickle(args.rets)
    if Path(args.J).exists():
        J = np.load(args.J)
    else:
        print(f"{args.J} not found: building J from the returns")
        J, _ = im.build_empirical_J(rets, verbose=False)
    if J.shape[0] != rets.shape[1]:
        sys.exit(f"J is {J.shape[0]}x{J.shape[0]} but the returns have {rets.shape[1]} tickers")
    out = Path(args.out)
    t_start = time.time()
    net = network_data(rets, J, args.threshold)
    print(f"{net['N']} stocks, {net['T']} days, lambda_max(J) = {net['lam']:.4f}")

    print(f"Calibrating ({mode['n_pilot']:,} sweeps per run, seeds {args.seeds})")
    with open(out / "calibration_log.txt", "w") as log:
        cal = run_calibrations(rets, J, args.seeds, mode["n_pilot"], mode["n_burn"], log)
    cons = consensus_row(cal)

    gains = sorted(set(GAINS) | {args.showcase_gain})
    dep = None
    if cons is None:
        print("No row survived in any seed: skipping the deployment figures")
    else:
        print(f"Deploying at T0/lam = {cons['T0'] / net['lam']:.3f}, k = {cons['k']}, "
              f"eps = {cons['eps']:.3f} ({mode['n_reps']} x {mode['n_days']:,} days per gain)")
        dep = run_deployment(J, cons, gains, mode["n_days"], mode["n_reps"], args.showcase_gain)

    index = rets.mean(axis=1).to_numpy()
    return {
        "created": str(datetime.datetime.now().replace(microsecond=0)),
        "rets_path": str(args.rets), "mode": mode, "seeds": list(args.seeds),
        "net": net, "cal": cal, "cons": cons, "dep": dep,
        "index": index, "index_facts": return_facts(index),
        "runtime_s": time.time() - t_start,
    }


# ----------------------------------------------------------------------------------------------
# Plot helpers
# ----------------------------------------------------------------------------------------------

def new_figure(width, height, title, subtitle):
    """Constrained-layout figure with a left-aligned headline and a one-line subtitle on top."""
    chars = int(width * 10.5)
    title = textwrap.fill(title, chars)
    subtitle = textwrap.fill(subtitle, int(width * 13.5))
    n_t, n_s = title.count("\n") + 1, subtitle.count("\n") + 1
    head = 0.12 + 0.24 * n_t + 0.19 * n_s
    fig = Figure(figsize=(width, height + head), layout="constrained")
    top = 1 - head / (height + head)
    fig.get_layout_engine().set(rect=(0, 0, 1, top))
    fig.text(0.012, 1 - 0.08 / (height + head), title, ha="left", va="top", fontsize=12,
             fontweight="bold", color=INK)
    fig.text(0.012, 1 - (0.12 + 0.24 * n_t) / (height + head), subtitle, ha="left", va="top",
             fontsize=9, color=INK2)
    return fig


def temperature_axis(ax, x, label=True):
    step = x[1] / x[0]
    ax.set_xscale("log")
    ax.set_xlim(x[0] / step ** 0.5, x[-1] * step ** 0.5)
    ticks = [t for t in (0.35, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.3)
             if x[0] / step ** 0.5 <= t <= x[-1] * step ** 0.5]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_locator(NullLocator())
    if label:
        ax.set_xlabel(r"$T_0 / \lambda_{\max}$")


def regime_spans(x, regimes):
    edges = np.concatenate([[x[0] / np.sqrt(x[1] / x[0])], np.sqrt(x[1:] * x[:-1]),
                            [x[-1] * np.sqrt(x[-1] / x[-2])]])
    spans, start = [], 0
    for i in range(1, len(x) + 1):
        if i == len(x) or regimes[i] != regimes[start]:
            spans.append((edges[start], edges[i], regimes[start], start, i - 1))
            start = i
    return spans


def shade_regimes(ax, spans, label=False):
    for lo, hi, reg, _, _ in spans:
        if REGIME_FILL[reg]:
            ax.axvspan(lo, hi, color=REGIME_FILL[reg], lw=0, zorder=0)
        if label:
            ax.text(np.sqrt(lo * hi), 1.01, reg, transform=ax.get_xaxis_transform(),
                    ha="center", va="bottom", fontsize=8, color=INK2)


def mark_selected(ax, x_sel, label=None):
    if x_sel is None:
        return
    ax.axvline(x_sel, color=INK, lw=0.9, zorder=3)
    if label:
        ax.annotate(label, (x_sel, 1.0), xycoords=("data", "axes fraction"),
                    xytext=(4, -4), textcoords="offset points", ha="left", va="top",
                    fontsize=8, color=INK)


def right_label(ax, y, text, color=INK2, side="right"):
    """Label a horizontal reference line just above it, at the right (or left) edge."""
    x, dx = (1.0, -3) if side == "right" else (0.0, 3)
    ax.annotate(text, (x, y), xycoords=("axes fraction", "data"), xytext=(dx, 3),
                textcoords="offset points", ha=side, va="bottom", fontsize=8, color=color)


def save(fig, out, name, formats):
    for fmt in formats:
        fig.savefig(out / f"{name}.{fmt}")
    print(f"  wrote {name}")


# ----------------------------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------------------------

def sector_order(tickers, v1):
    lookup = {t: s for s, ts in SECTORS.items() for t in ts}
    names = list(SECTORS) + ["Other"]
    order = sorted(range(len(tickers)),
                   key=lambda i: (names.index(lookup.get(tickers[i], "Other")), -v1[i]))
    groups, start = [], 0
    for j in range(1, len(order) + 1):
        if j == len(order) or lookup.get(tickers[order[j]], "Other") != \
                lookup.get(tickers[order[start]], "Other"):
            groups.append((lookup.get(tickers[order[start]], "Other"), start, j))
            start = j
    return order, groups


def fig_network(d):
    net = d["net"]
    N, thr, C, tick = net["N"], net["threshold"], net["C"], net["tickers"]
    ev = net["evals"]
    n_signal = int((ev > net["mp_edge"]).sum())
    dominant = ev[0] > 3 * ev[1]
    title = (f"{net['edges']} of {net['pairs']} stock pairs are kept in J "
             f"({net['edges'] / net['pairs']:.0%}), and "
             + ("one market mode dominates the correlations" if dominant else
                f"{n_signal} modes stand out from noise"))
    subtitle = (f"{N} stocks, daily log returns {net['start']} to {net['end']} ({net['T']} days). "
                f"J keeps correlations above {thr}; its largest eigenvalue "
                f"λ_max(J) = {net['lam']:.3f} sets the temperature scale.")
    fig = new_figure(12, 6.6, title, subtitle)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], height_ratios=[1, 1.6])

    # (a) correlation heatmap, sectors grouped, cells below the threshold greyed out
    ax = fig.add_subplot(gs[:, 0])
    order, groups = sector_order(tick, net["v1"])
    Co = C[np.ix_(order, order)]
    off = ~np.eye(N, dtype=bool)
    norm = Normalize(vmin=thr, vmax=Co[off].max())
    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)
    rgba = cmap(norm(Co))
    rgba[(Co <= thr) & off] = to_rgba(SHADE_DARK)
    rgba[~off] = to_rgba(SURFACE)
    ax.imshow(rgba, interpolation="nearest")
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    labels = [tick[i] for i in order]
    ax.set_xticks(range(N), labels, rotation=90, fontsize=7)
    ax.set_yticks(range(N), labels, fontsize=7)
    ax.tick_params(length=0)
    for name, a, b in groups:
        if a > 0:
            ax.axhline(a - 0.5, color=SURFACE, lw=2)
            ax.axvline(a - 0.5, color=SURFACE, lw=2)
        ax.text((a + b - 1) / 2, -1.0, name, ha="center", va="bottom", fontsize=7.5,
                color=INK2)
    cb = fig.colorbar(ScalarMappable(norm, cmap), ax=ax, shrink=0.6, pad=0.02)
    cb.set_label(f"correlation, kept in J (grey: ≤ {thr}, dropped)", color=INK2)
    cb.outline.set_visible(False)
    cb.ax.tick_params(color=AXIS, labelcolor=INK2, labelsize=8)
    ax.set_title("Return correlations, grouped by sector", pad=26)

    # (b) eigenvalues of C against the random-matrix noise edge
    ax = fig.add_subplot(gs[0, 1])
    rank = np.arange(1, N + 1)
    sig = ev > net["mp_edge"]
    ax.scatter(rank[~sig], ev[~sig], s=22, color=MUTED, zorder=3, edgecolor=SURFACE, lw=1)
    ax.scatter(rank[sig], ev[sig], s=34, color=BLUE, zorder=4, edgecolor=SURFACE, lw=1)
    ax.axhline(net["mp_edge"], color=INK2, lw=0.9)
    right_label(ax, net["mp_edge"], f"noise edge (1+√(N/T))² = {net['mp_edge']:.2f}")
    ax.annotate(f"market mode: {ev[0]:.1f}, {ev[0] / N:.0%} of the variance", (1, ev[0]),
                xytext=(8, -2), textcoords="offset points", fontsize=8, color=INK, va="center")
    ax.set_yscale("log")
    ax.set_xlabel("rank")
    ax.set_ylabel("eigenvalue of C")
    ax.set_title(f"Eigenvalues of C: {n_signal} above the noise edge")

    # (c) loadings of the market mode
    ax = fig.add_subplot(gs[1, 1])
    idx = np.argsort(net["v1"])
    ax.barh(range(N), net["v1"][idx], height=0.62, color=BLUE)
    ax.set_yticks(range(N), [tick[i] for i in idx], fontsize=7)
    ax.tick_params(axis="y", length=0)
    ax.axvline(1 / np.sqrt(N), color=INK2, lw=0.9)
    ax.annotate("equal weight 1/√N", (1 / np.sqrt(N), 0), xytext=(4, -2),
                textcoords="offset points", fontsize=8, color=INK2, va="top")
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("loading on the top eigenvector")
    sign = "the same sign" if (net["v1"] > 0).all() else "mixed signs"
    ax.set_title(f"Market mode: every stock loads with {sign}" if sign == "the same sign"
                 else "Market mode loadings")
    return fig


def fig_regimes(d):
    net, cal, cons = d["net"], d["cal"], d["cons"]
    seed = d["seeds"][0]
    tab, runs = cal[seed]["table"], cal[seed]["runs"]
    x = (tab.T0 / net["lam"]).to_numpy()
    reg = classify(tab)
    spans = regime_spans(x, reg)
    x_sel = None if cons is None else cons["T0"] / net["lam"]
    n_pilot = d["mode"]["n_pilot"]
    not_mixing = np.flatnonzero(reg != "mixing")
    first_mix = 0 if len(not_mixing) == 0 else not_mixing[-1] + 1  # start of the top mixing run
    if first_mix == 0:
        title = "Every temperature in the scan mixes"
    elif first_mix < len(x):
        title = (f"Runs mix only from {x[first_mix]:.2f} λ_max up; below that they freeze in "
                 "one well or are too slow to measure")
    else:
        title = "No temperature at the top of the scan mixes reliably"
    subtitle = (f"Seed {seed}: 13 temperatures × 16 pilot runs ({n_pilot:,} sweeps each, "
                "α = 0, h = 0). Shading marks rows that fail the zero-mean test (frozen) "
                "or the convergence test (slow).")
    fig = new_figure(8, 9.6, title, subtitle)
    axes = fig.subplots(4, 1, sharex=True)
    for ax in axes:
        shade_regimes(ax, spans, label=ax is axes[0])
        temperature_axis(ax, x, label=ax is axes[-1])
        mark_selected(ax, x_sel)

    # (a) Binder ratio = return kurtosis
    ax = axes[0]
    ax.plot(x, tab.R_mean, "o-", color=BLUE, mec=SURFACE, mew=1, zorder=4)
    for y, text in ((3, "Gaussian: 3"), (1, "two sharp peaks: 1")):
        ax.axhline(y, color=INK2, lw=0.9)
        right_label(ax, y, text)
    ax.set_ylim(0.8, 3.3)
    ax.set_ylabel("R = return kurtosis")
    ax.set_title("Binder ratio R = ⟨m⁴⟩/⟨m²⟩², which is the return kurtosis (row mean)", pad=18)
    if x_sel is not None:
        ax.annotate(f"selected T0 = {x_sel:.2f} λ", (x_sel, 0.82),
                    xycoords=("data", "data"), xytext=(4, 2), textcoords="offset points",
                    fontsize=8, color=INK)

    # (b) integrated autocorrelation time
    ax = axes[1]
    g = runs.groupby("i_T0").tau_int
    med, q1, q3 = g.median().to_numpy(), g.quantile(0.25).to_numpy(), g.quantile(0.75).to_numpy()
    ok = tab.frac_converged.to_numpy() >= im.MIN_FRAC_CONVERGED
    ax.vlines(x, q1, q3, color=BLUE, lw=1.2, zorder=3)
    ax.plot(x, med, "-", color=BLUE, zorder=3)
    ax.plot(x[ok], med[ok], "o", color=BLUE, mec=SURFACE, mew=1, zorder=4)
    ax.plot(x[~ok], med[~ok], "o", color=SURFACE, mec=BLUE, mew=1.4, zorder=4)
    ax.axhline(n_pilot / 300, color=INK2, lw=0.9)
    right_label(ax, n_pilot / 300, f"convergence cap n/300 = {n_pilot / 300:.0f}")
    ax.set_yscale("log")
    ax.set_ylabel(r"$\tau_{\mathrm{int}}$ (sweeps)")
    ax.set_title("Autocorrelation time (median and IQR over runs; hollow = row not converged, "
                 "so τ is truncated)")

    # (c) the model's clock
    ax = axes[2]
    k = tab.k.to_numpy(dtype=float)  # NaN where too few runs converged: the line breaks there
    ax.plot(x, k, "o-", color=BLUE, mec=SURFACE, mew=1)
    for xi, ki in zip(x, k, strict=True):
        if x_sel is not None and np.isclose(xi, x_sel) and np.isfinite(ki):
            ax.annotate(f"k = {int(ki)}", (xi, ki), xytext=(6, 4), textcoords="offset points",
                        fontsize=8, color=INK)
    ax.set_yscale("log")
    ax.set_ylabel("k (sweeps per day)")
    ax.set_title("Sweeps per trading day, k = ⌈3 · p75(τ_int)⌉")

    # (d) the run-level checks
    ax = axes[3]
    ax.plot(x, tab.frac_converged, "o-", color=BLUE, mec=SURFACE, mew=1, label="runs converged")
    ax.plot(x, tab.frac_z_high, "s-", color=ORANGE, mec=SURFACE, mew=1,
            label="runs failing the zero-mean test (|z| > 3)")
    for y in (im.MIN_FRAC_CONVERGED, im.MAX_FRAC_Z_HIGH):
        ax.axhline(y, color=INK2, lw=0.9)
        right_label(ax, y, f"threshold {y:g}")
    ax.set_ylim(-0.05, 1.08)
    ax.set_ylabel("fraction of runs")
    ax.legend(loc="center right", frameon=True, facecolor=SURFACE, edgecolor="none",
              framealpha=1)
    ax.set_title("Run checks")
    return fig


def fig_griffiths(d):
    net, cal = d["net"], d["cal"]
    seed = d["seeds"][0]
    tab, ex = cal[seed]["table"], cal[seed]["extras"]
    x = (tab.T0 / net["lam"]).to_numpy()
    sig, s_k = tab.sigma_m_mean.to_numpy(), ex["s_fixed"]
    spans = regime_spans(x, classify(tab))
    xm = np.sqrt(x[1:] * x[:-1])
    dlnT = np.diff(np.log(x))
    eps_eq, eps_s = np.diff(np.log(sig)) / dlnT, np.diff(np.log(s_k)) / dlnT
    if (eps_eq <= 0.02).all() and (eps_s > 0.1).any():
        title = ("Equilibrium volatility falls with T at every temperature; a positive slope "
                 "only appears where runs don't mix")
    else:
        title = "Equilibrium width and 20-day volatility across temperature"
    subtitle = (f"Seed {seed}. σ_m = √⟨m²⟩ over each 16-run row "
                f"(Griffiths: non-increasing in T for J ≥ 0, h = 0); s = mean 20-day "
                f"standard deviation of m sampled every k = {ex['k_fix']} sweeps.")
    fig = new_figure(8, 6.4, title, subtitle)
    axes = fig.subplots(2, 1, sharex=True, height_ratios=[1.2, 1])
    for ax in axes:
        shade_regimes(ax, spans, label=ax is axes[0])
        temperature_axis(ax, x, label=ax is axes[-1])

    ax = axes[0]
    ax.plot(x, sig, "o-", color=BLUE, mec=SURFACE, mew=1,
            label=r"$\sigma_m$: equilibrium width of m")
    ax.plot(x, s_k, "s-", color=ORANGE, mec=SURFACE, mew=1,
            label=f"s: 20-day volatility at k = {ex['k_fix']}")
    ax.set_yscale("log")
    ax.set_ylabel("standard deviation of m")
    ax.legend(loc="lower right")
    ax.set_title("Two measures of volatility", pad=18)

    ax = axes[1]
    ax.axhline(0, color=INK, lw=0.9)
    always = r" (always $\leq 0$)" if (eps_eq <= 0).all() else ""
    ax.plot(xm, eps_eq, "o-", color=BLUE, mec=SURFACE, mew=1, label=r"from $\sigma_m$" + always)
    ax.plot(xm, eps_s, "s-", color=ORANGE, mec=SURFACE, mew=1, label="from s")
    ax.set_ylabel(r"slope $d\,\ln(\cdot)\,/\,d\,\ln T$")
    ax.legend(loc="upper right")
    ax.set_title("Elasticity ε between neighbouring rows")
    return fig


def fig_traces(d):
    net, cal, cons = d["net"], d["cal"], d["cons"]
    seed = d["seeds"][0]
    tab, ex = cal[seed]["table"], cal[seed]["extras"]
    reg = classify(tab)
    picks = []
    for r in ("frozen", "slow"):
        idx = np.flatnonzero(reg == r)
        if len(idx):
            picks.append(int(idx[len(idx) // 2]))
    mixing = np.flatnonzero(reg == "mixing")
    if cons is not None:
        picks.append(cons["i"])
    elif len(mixing):
        picks.append(int(mixing[0]))
    describe = {"frozen": "stays in one well", "slow": "rare jumps between the wells",
                "mixing": "fluctuates around 0"}
    title = "The magnetisation in each regime: stuck, switching rarely, and mixing"
    sampling = "every sweep" if ex["trace_stride"] == 1 else \
        f"sampled every {ex['trace_stride']} sweeps"
    subtitle = (f"Seed {seed}. Left: one random-start run, {sampling}. "
                "Right: distribution of m pooled over all 16 runs at that temperature, "
                "so both wells appear even when a single run sees one.")
    fig = new_figure(11, 2.3 * len(picks), title, subtitle)
    gs = fig.add_gridspec(len(picks), 2, width_ratios=[4, 1])
    centres = 0.5 * (hist_edges(ex["hist_N"])[1:] + hist_edges(ex["hist_N"])[:-1])
    for row, i in enumerate(picks):
        trace = ex["traces"][i]
        t = np.arange(len(trace)) * ex["trace_stride"] / 1000
        ax = fig.add_subplot(gs[row, 0])
        ax.plot(t, trace, color=BLUE, lw=0.6)
        ax.set_ylim(-1.08, 1.08)
        ax.set_xlim(0, t[-1])
        ax.set_ylabel("m")
        if row == len(picks) - 1:
            ax.set_xlabel("sweeps (thousands)")
        xi = tab.T0.iloc[i] / net["lam"]
        ax.set_title(f"T0 = {xi:.2f} λ_max ({reg[i]}): {describe[reg[i]]}; "
                     f"R = {tab.R_mean.iloc[i]:.2f}")
        hx = fig.add_subplot(gs[row, 1], sharey=ax)
        p = ex["hists"][i] / ex["hists"][i].sum()
        hx.barh(centres, p, height=(centres[1] - centres[0]) * 0.8, color=BLUE)
        hx.grid(axis="y", visible=False)
        hx.tick_params(labelleft=False)
        if row == 0:
            hx.set_title("distribution, all runs")
        if row == len(picks) - 1:
            hx.set_xlabel("probability")
    return fig


def fig_selection(d):
    net, cal = d["net"], d["cal"]
    seeds = d["seeds"]
    shown = seeds[:3]  # three colours at most; the grid on the right shows every seed
    colours, markers = [BLUE, ORANGE, AQUA], ["o", "s", "D"]
    tabs = [cal[s]["table"] for s in seeds]
    x = (tabs[0].T0 / net["lam"]).to_numpy()
    winners = [cal[s]["i_T0"] for s in seeds]
    win_x = sorted({f"{x[w]:.3f}" for w in winners if w is not None})
    if not win_x:
        title = "No row survives the selection"
    elif len(win_x) > 1:
        title = "The winning row depends on the seed: ε is nearly flat across the best rows"
    elif len(seeds) == 1:
        title = f"Seed {seeds[0]} selects T0 = {win_x[0]} λ_max"
    else:
        title = f"Every seed picks the same row, T0 = {win_x[0]} λ_max"
    subtitle = ("Left: ε = d ln s / d ln T0 with ±2 SE, at each row's own k. Filled: row "
                "passes every check; hollow: ε defined but another check fails. Right: the "
                "first check each row fails, in select_T0's order.")
    fig = new_figure(12, 6.2, title, subtitle)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.7, 1])

    ax = fig.add_subplot(gs[0, 0])
    offsets = np.exp(np.linspace(-0.018, 0.018, len(shown))) if len(shown) > 1 else [1.0]
    defined = np.flatnonzero(np.any([np.isfinite(t.eps_mean.to_numpy()) for t in tabs], axis=0))
    lo_i = max(0, defined[0] - 1) if len(defined) else 0  # zoom to rows that have an eps
    ax.axhline(0, color=INK, lw=0.9)
    for n, (seed, tab) in enumerate(zip(shown, tabs[:3], strict=True)):
        c, mk = colours[n], markers[n]
        ok = np.isfinite(tab.eps_mean.to_numpy())
        surv = (tab.first_failure == "none").to_numpy()
        xs = x * offsets[n]
        ax.vlines(xs[ok], (tab.eps_mean - 2 * tab.eps_se)[ok], (tab.eps_mean + 2 * tab.eps_se)[ok],
                  color=c, lw=1.2)
        ax.plot(xs[ok & surv], tab.eps_mean[ok & surv], mk, color=c, mec=SURFACE, mew=1,
                label=f"seed {seed}")
        ax.plot(xs[ok & ~surv], tab.eps_mean[ok & ~surv], mk, color=SURFACE, mec=c, mew=1.4)
    temperature_axis(ax, x[lo_i:])
    ax.set_ylabel("ε = d ln s / d ln T0")
    ax.legend(loc="lower right")
    ax.set_title("Elasticity of volatility, by row and seed"
                 + (f" (first {len(shown)} seeds)" if len(seeds) > len(shown) else ""), pad=22)

    ax = fig.add_subplot(gs[0, 1])
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for n, tab in enumerate(tabs):
        for i, ff in enumerate(tab.first_failure):
            is_win = winners[n] is not None and i == winners[n]
            fill = to_rgba(GOOD, 0.35) if is_win else to_rgba(GOOD, 0.14) if ff == "none" \
                else to_rgba(SHADE)
            ax.add_patch(Rectangle((n + 0.04, i + 0.06), 0.92, 0.88, color=fill, lw=0))
            text = "winner" if is_win else FAILURE_LABEL.get(ff, ff)
            ax.text(n + 0.5, i + 0.5, text, ha="center", va="center", fontsize=7.5,
                    color=INK, fontweight="bold" if is_win else "normal")
    ax.set_xlim(0, len(seeds))
    ax.set_ylim(len(x), 0)
    ax.set_xticks(np.arange(len(seeds)) + 0.5, [f"seed {s}" for s in seeds])
    ax.set_yticks(np.arange(len(x)) + 0.5, [f"{v:.3f}" for v in x])
    ax.tick_params(length=0)
    ax.xaxis.set_ticks_position("top")
    ax.set_ylabel(r"$T_0 / \lambda_{\max}$")
    ax.set_title("First failed check", pad=22)
    return fig


def fig_feedback(d):
    dep, cons, net = d["dep"], d["cons"], d["net"]
    t = dep["table"]
    g = t.groupby("G")
    G = np.array(sorted(t.G.unique()))
    mean, lo, hi = g.mean(numeric_only=True), g.min(numeric_only=True), g.max(numeric_only=True)
    drift = [x for x in G if mean.loc[x, "T_mean"] > 1.10]
    tail = (f"mean T leaves T0 by more than 10% from G = {min(drift):g}" if drift
            else f"the operating point holds up to G = {G.max():g}")
    title = f"Volatility clustering grows with the loop gain G = α|ε|; {tail}"
    n_reps, n_days = d["mode"]["n_reps"], d["mode"]["n_days"]
    subtitle = (f"Deployed model at T0 = {cons['T0'] / net['lam']:.3f} λ_max, "
                f"k = {cons['k']} sweeps/day, ε = {cons['eps']:.2f}, T = T0(σ/σ₀)"
                f"^−α with α = G/|ε|. Points: mean of {n_reps} runs × "
                f"{n_days:,} days; bars: range over runs. Grey line: G = 1, the linear "
                "stability limit.")
    fig = new_figure(12, 3.8, title, subtitle)
    axes = fig.subplots(1, 3)

    def series(ax, col, colour, marker, label=None, dx=0.0):
        ax.vlines(G + dx, lo[col], hi[col], color=colour, lw=1.2)
        ax.plot(G + dx, mean[col], marker + "-", color=colour, mec=SURFACE, mew=1, label=label)

    ax = axes[0]
    ax.axhline(0, color=INK, lw=0.9)
    series(ax, "ac_abs_mean", BLUE, "o", "mean AC(|r|), lags 1–20", -0.012)
    series(ax, "ac_r1", ORANGE, "s", "AC(r) at lag 1", 0.012)
    ax.set_ylabel("autocorrelation")
    ax.legend(loc="upper left")
    ax.set_title("Clustering, and leftover return autocorrelation")

    ax = axes[1]
    ax.axhline(1, color=INK2, lw=0.9)
    series(ax, "T_mean", BLUE, "o")
    ax.set_ylabel("mean T / T0")
    ax.set_title("Operating point")

    ax = axes[2]
    ax.axhline(3, color=INK2, lw=0.9)
    right_label(ax, 3, "Gaussian: 3", side="left")
    series(ax, "kurtosis", BLUE, "o")
    ax.set_ylabel("return kurtosis")
    ax.set_title("Tails")

    for ax in axes:
        ax.axvline(1, color=MUTED, lw=0.9)
        ax.set_xlabel("loop gain G = α|ε|")
        ax.set_xticks(G)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    return fig


def fig_model_vs_data(d):
    dep, net = d["dep"], d["net"]
    G = dep["showcase"]
    r_mod, _ = dep["series"][G]
    idx, fi = d["index"], d["index_facts"]
    fm = return_facts(r_mod.astype(float))
    n = len(idx)
    ratio = fm["ac_abs_mean"] / fi["ac_abs_mean"] if fi["ac_abs_mean"] > 0 else np.inf
    clust = ("weaker volatility clustering" if ratio < 0.67 else
             "stronger volatility clustering" if ratio > 1.5 else
             "comparable volatility clustering")
    tails = ("thinner tails than the market" if fm["kurtosis"] < fi["kurtosis"]
             else "tails as heavy as the market's")
    title = f"At G = {G:g}, the model shows {clust} and {tails}"
    subtitle = (f"Market: equal-weight index of the {net['N']} stocks, {net['start']} to "
                f"{net['end']} ({n} days). Model: deployed run at G = {G:g} (r = m, all "
                f"{len(r_mod):,} days for the statistics). Both standardised.")
    fig = new_figure(12, 6.2, title, subtitle)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.4, 1])

    zi = (idx - idx.mean()) / idx.std()
    zm = (r_mod - r_mod.mean()) / r_mod.std()
    lim = 1.08 * max(np.abs(zi).max(), np.abs(zm[:n]).max())
    for row, (z, colour, name) in enumerate(((zi, ORANGE, "Market index"),
                                             (zm[:n], BLUE, f"Model, G = {G:g}, first {n} days"))):
        ax = fig.add_subplot(gs[row, 0])
        ax.plot(np.arange(n), z, color=colour, lw=0.7)
        ax.set_ylim(-lim, lim)
        ax.set_xlim(0, n)
        ax.set_ylabel("return (sd units)")
        ax.set_title(name)
        if row == 1:
            ax.set_xlabel("trading day")

    ax = fig.add_subplot(gs[0, 1])
    lags = np.arange(1, MAX_LAG + 1)
    band = 2 / np.sqrt(n)
    ax.axhspan(-band, band, color=SHADE, lw=0, label=f"±2/√n noise band (n = {n})")
    ax.axhline(0, color=INK, lw=0.9)
    curves = [fi["acf_abs"][1:], fm["acf_abs"][1:]]
    ax.plot(lags, curves[0], "-", color=ORANGE, label="market index")
    ax.plot(lags, curves[1], "-", color=BLUE, label=f"model, G = {G:g}")
    if 0.0 in dep["acfs"] and G != 0.0:
        curves.append(dep["acfs"][0.0][1][1:])
        ax.plot(lags, curves[-1], "-", color=AQUA, label="model, no feedback")
    y_lo, y_hi = min(-band, *(c.min() for c in curves)), max(band, *(c.max() for c in curves))
    ax.set_ylim(y_lo - 0.05 * (y_hi - y_lo), y_hi + 0.6 * (y_hi - y_lo))  # headroom for legend
    ax.set_xlabel("lag (days)")
    ax.set_ylabel("AC(|r|)")
    ax.legend(loc="upper right", ncol=2)
    ax.set_title("Autocorrelation of absolute returns")

    ax = fig.add_subplot(gs[1, 1])
    # m only takes the values (2j - N)/N, so the model's bins are whole groups of those values;
    # bins that split them unevenly would make the histogram saw-toothed
    step = 2 / net["N"] / r_mod.std()
    width = step * max(1, round(0.4 / step))
    lattice = (np.arange(-net["N"], net["N"] + 1, 2) / net["N"] - r_mod.mean()) / r_mod.std()
    model_bins = np.arange(lattice.min() - step / 2, lattice.max() + width, width)
    for z, bins, colour, name, k in (
            (zi, np.arange(-6, 6.001, 0.4), ORANGE, "market index", fi["kurtosis"]),
            (zm, model_bins, BLUE, f"model, G = {G:g}", fm["kurtosis"])):
        h, _ = np.histogram(z, bins=bins, density=True)
        c = 0.5 * (bins[1:] + bins[:-1])
        ax.plot(c, np.where(h > 0, h, np.nan), "-", drawstyle="steps-mid", color=colour,
                label=f"{name} (kurtosis {k:.1f})")
    xs = np.linspace(-6, 6, 400)
    ax.plot(xs, stats.norm.pdf(xs), color=INK, lw=0.9, label="Gaussian (kurtosis 3)")
    ax.set_yscale("log")
    ax.set_ylim(1e-4, 30)
    ax.set_xlim(-6, 6)
    ax.set_xlabel("standardised return")
    ax.set_ylabel("density")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title("Distribution of returns (log scale)")
    return fig


# ----------------------------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------------------------

def write_summary(d, out):
    net, cal, cons, dep, lam = d["net"], d["cal"], d["cons"], d["dep"], d["net"]["lam"]
    mode = d["mode"]
    lines = [
        "# Financial Ising model: figures summary", "",
        f"Generated {d['created']} from `{d['rets_path']}` in {d['runtime_s'] / 60:.1f} min. "
        f"Pilots: {mode['n_pilot']:,} sweeps after {mode['n_burn']:,} burn-in; deployment: "
        f"{mode['n_reps']} runs x {mode['n_days']:,} days per gain.", "",
        "## Network", "",
        f"- {net['N']} stocks, {net['T']} trading days ({net['start']} to {net['end']})",
        f"- J keeps correlations above {net['threshold']}: {net['edges']} of {net['pairs']} pairs "
        f"({net['edges'] / net['pairs']:.1%})",
        f"- lambda_max(J) = {lam:.4f}",
        f"- Largest eigenvalue of C: {net['evals'][0]:.2f} ({net['evals'][0] / net['N']:.0%} of "
        f"the variance); {int((net['evals'] > net['mp_edge']).sum())} eigenvalues above the "
        f"random-matrix edge {net['mp_edge']:.2f}", "",
        "## Calibration by seed", "",
        "| seed | winner T0/lambda | T0 | k | eps +- SE | rows passing every check (T0/lambda) |",
        "|---|---|---|---|---|---|",
    ]
    for s in d["seeds"]:
        c, tab = cal[s], cal[s]["table"]
        surv = ", ".join(f"{v:.3f}" for v in (tab.T0 / lam)[tab.first_failure == "none"])
        if c["T0"] is None:
            lines.append(f"| {s} | none | | | | {surv or 'none'} |")
        else:
            row = tab.iloc[c["i_T0"]]
            lines.append(f"| {s} | {c['T0'] / lam:.3f} | {c['T0']:.4f} | {c['k']} | "
                         f"{row.eps_mean:.3f} +- {row.eps_se:.3f} | {surv} |")
    seed = d["seeds"][0]
    spans = regime_spans((cal[seed]["table"].T0 / lam).to_numpy(), classify(cal[seed]["table"]))
    x = (cal[seed]["table"].T0 / lam).to_numpy()
    lines += ["", f"Regimes (seed {seed}): " + "; ".join(
        f"{r} {x[a]:.2f}-{x[b]:.2f}" for _, _, r, a, b in spans), ""]
    if cons is not None:
        lines += [
            "## Recommended row (survives in the most seeds)", "",
            f"- T0 = {cons['T0']:.4f} = {cons['T0'] / lam:.3f} lambda_max, passing in "
            f"{cons['n_surv']} of {cons['n_seeds']} seeds",
            f"- k = {cons['k']} sweeps/day (median over seeds), sigma0 = {cons['sigma0']:.4f}",
            f"- eps = {cons['eps']:.3f} (by seed: "
            + ", ".join("n/a" if np.isnan(e) else f"{e:.3f}" for e in cons["eps_by_seed"]) + ")",
            "- Linear stability of the feedback needs alpha < 1/|eps| = "
            f"{1 / abs(cons['eps']):.2f}",
            "",
        ]
    if dep is not None:
        t = dep["table"].groupby("G").mean(numeric_only=True)
        lines += ["## Deployment (means over runs)", "",
                  "| G | alpha | kurtosis | mean AC(\\|r\\|) lags 1-20 | AC(r,1) | mean T/T0 "
                  "| CV of T | days clipped |", "|---|---|---|---|---|---|---|---|"]
        for G, r in t.iterrows():
            lines.append(f"| {G:g} | {r['alpha']:.3f} | {r['kurtosis']:.2f} | "
                         f"{r['ac_abs_mean']:.3f} | {r['ac_r1']:.3f} | {r['T_mean']:.3f} | "
                         f"{r['T_cv']:.3f} | {r['clip']:.1%} |")
        fi = d["index_facts"]
        lines += ["", f"Equal-weight index of the same stocks: kurtosis {fi['kurtosis']:.2f}, "
                  f"mean AC(|r|) lags 1-20 {fi['ac_abs_mean']:.3f}, AC(r,1) {fi['ac_r1']:.3f}.",
                  ""]
    lines += [
        "## Figures", "",
        "- fig1_network: return correlations kept in J by sector, eigenvalues of C against the "
        "random-matrix noise edge, and the market-mode loadings.",
        "- fig2_regimes: across the T0 scan, the Binder ratio (= return kurtosis), tau_int, the "
        "clock k and the run checks, with frozen and slow rows shaded.",
        "- fig3_griffiths: the equilibrium width sigma_m falls with T everywhere; the 20-day "
        "volatility s rises with T only where runs don't mix, which is where eps > 0 came from.",
        "- fig4_traces: m(t) and the distribution of m in a frozen, a slow and the selected row.",
        "- fig5_selection: eps with 2 SE for every row and seed, and the first check each row "
        "fails.",
        "- fig6_feedback: clustering, leftover lag-1 autocorrelation, operating point and kurtosis "
        "against the loop gain.",
        "- fig7_model_vs_data: model returns next to the equal-weight index: time series, "
        "AC(|r|) and the distribution on a log scale.",
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("  wrote summary.md")


# ----------------------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--rets", default="data/rets_2005_2007.pkl", help="frozen returns (pickle)")
    p.add_argument("--J", default="data/J_2005_2007.npy", help="frozen J (built if missing)")
    p.add_argument("--out", default="results/figures", help="output folder")
    p.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    p.add_argument("--threshold", type=float, default=0.3, help="correlation cut-off used for J")
    p.add_argument("--showcase-gain", type=float, default=0.5,
                   help="loop gain shown in the model-vs-data figure")
    p.add_argument("--quick", action="store_true", help="short runs to check the pipeline")
    p.add_argument("--replot", action="store_true", help="redraw from figdata.pkl, no simulation")
    p.add_argument("--formats", nargs="+", default=["png"], help="e.g. png pdf")
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "figdata.pkl"
    if args.replot:
        with open(cache, "rb") as f:
            d = pickle.load(f)
        print(f"Loaded {cache} (computed {d['created']})")
    else:
        if not Path(args.rets).exists():
            sys.exit(f"{args.rets} not found: run scripts/calibrate_real.py to freeze the data")
        d = compute(args, QUICK if args.quick else FULL)
        with open(cache, "wb") as f:
            pickle.dump(d, f)

    set_style()
    print("Drawing figures")
    figures = [("fig1_network", fig_network), ("fig2_regimes", fig_regimes),
               ("fig3_griffiths", fig_griffiths), ("fig4_traces", fig_traces),
               ("fig5_selection", fig_selection)]
    if d["dep"] is not None:
        figures += [("fig6_feedback", fig_feedback), ("fig7_model_vs_data", fig_model_vs_data)]
    for name, make in figures:
        save(make(d), out, name, args.formats)
    write_summary(d, out)
    print(f"Done: {out}/")


if __name__ == "__main__":
    main()