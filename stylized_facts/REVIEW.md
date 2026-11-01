# Review of stylized_facts/: breaking points, edge cases, known comparisons, dependencies

Written 2026-11-01 from reading the code (`src/ising_market/model.py`, all six scripts, `pyproject.toml`, `uv.lock`, the installed environment). Nothing was run, so each item is a hypothesis until a test confirms it. `tests/test_loose.py` was left out of scope. Items REPORT.md already lists are marked *(known)*.

## A. Breaking points and edge cases in the code

### Severity 1: wrong results without an error
1. **Equilibration check passes vacuously with `n_seeds=1`** (`model.py:672-684`). `mean_se` of 1 value
   gives SE = NaN, `abs(diff) > NaN` is False, so `equilibrated` stays True. The same happens when a start
   has fewer than 2 runs. Any quick run with `n_seeds=1` skips this check without warning.
2. **`consensus_row` mixes k across seeds** (`make_figures.py:244-247`). `k` is the median over seeds, but `sigma0`
   and `eps` are means of each seed's `s_mean` and `eps_mean`, each measured at *that seed's* k. When the seeds' k values differ,
   the deployed σ0 was not measured at the deployed k, so the feedback's reference level is off by the
   ratio s(k_seed)/s(k_median). The means also include seeds where that row failed.
3. **Non-zero diagonal or asymmetric J gives wrong ΔE** (all numba kernels, e.g. `model.py:556-558`).
   `f` sums over all j including j = i, so ΔE gets an extra 2·J_ii. Nothing checks this. `build_empirical_J` zeroes the
   diagonal, but `lattice(L)` with L = 1 sets J_aa = 1, and L = 2 double-counts neighbours in the periodic wrap
   (`compare_return_models.py:530-540`). An asymmetric J breaks detailed balance without any error.
4. **Isolated nodes** (degree 0 after thresholding): ΔE = 0, so every attempt flips them. They add pure noise
   to m. This does not happen at threshold 0.3 on the us100 data, but there are 6 isolated stocks at 0.5 and 36 at 0.6
   (`data/freeze_us100_2005_2024.txt`). A higher `--threshold` changes m's statistics in a way that is easy to miss.
5. **`rolling_susceptibility` is not a susceptibility** (`model.py:290-300`). It returns var(m) with no N/T
   factor, despite the docstring. `magnetic_susceptibility` divides by N·T, which is right only if the inputs are total M,
   not m. These are legacy functions, but `early_warning` will likely want χ, so take the formula from here with care.
6. **`calibrate_parameters` docstring says it "derives kappa"**. It doesn't: `target_vol` is unused, and
   `kurtosis_by_T0`/`m_std_by_T0` are dead code *(known: κ not calibrated)*.
7. **`_ours_kernel` sigma0 baseline** (`compare_return_models.py:299-307`) comes from one 4,000-day run at a fixed
   seed of 99. Its sampling error enters every feedback model as a fixed bias that is never reported.

### Severity 2: crashes on unusual input
8. **No edges in J** (threshold too high, or tiny N): `lam = 0` → `np.geomspace(0, 0, 13)` raises an error
   (`model.py:853-855`); `build_empirical_J` with N = 1 divides by zero in `density`.
9. **`calibrate_parameters` returns `T0=None`** when no row passes; `simulate_deployed(..., sigma0=None)` then
   fails at `float(None)`. The `__main__` block guards against this, but other callers don't.
10. **Short pilot runs** (`n_pilot < 100`): `max_lag = n//50 ≤ 1`, the Sokal loop never runs, `tau_int = 0`,
    and `z` divides by `sqrt(0)` → inf (`model.py:614-625`).
11. **Negative τ_int**: for strongly anti-correlated m (e.g. N = 1 at J = 0, where m alternates ±1), `tau_int` < 0,
    and `k = ceil(3·p75)` can be ≤ 0. Then `m[::0]` raises ValueError and a negative k reverses the series
    (`model.py:595, 666`).
12. **Frozen / constant m** (very low T, all spins up): `_acf` gives 0/0 → NaN, `thinned_stats` ac1 NaN,
    `z = inf`. The NaNs are handled downstream (those rows fail), but they come with RuntimeWarnings.
13. **eps OLS degenerate cases** (`model.py:741-752`): if one neighbour row's s values are all non-finite, x has one
    distinct value → `inv(X.T X)` raises LinAlgError; with ≤ 2 points, `len(y)-2 ≤ 0` → inf/negative variance.
14. **Unsorted `T0_search`**: the "neighbour rows" p±1 are neighbours in list order, not in temperature, so the
    slope uses whichever rows happen to sit next to each other.
15. **`moments`/`hill`/`block_bootstrap` on short series** (`compare_return_models.py:396-453`):
    `hill` raises IndexError when len ≤ 2; `_acf(..., 30)` on a series shorter than 31 returns zero-padded values;
    `block_bootstrap` with n < 50 calls `integers(0, negative)`; `kurtosis 5d` is NaN below 5 days.
16. **`decile_diagnostic` with tied m²** (`garch_x_breadth.py:239-249`): m is a mean of signs, so it takes
    at most N+1 values. Repeated quantile edges then leave bins empty, giving NaN means and warnings.
    Zero returns (stale quotes) give `sign = 0` and push m toward 0.
17. **Numerical Hessian near bounds** (`garch_x_breadth.py:132-156`): when a parameter sits near a constraint
    (a ≈ 0, ν near 2.05 or 200, a + g/2 + b near 0.999), a ±h step hits the 1e10 penalty and the Hessian, and so the SEs,
    become meaningless. Nothing detects this.
18. **Legacy class** (`FinancialIsingModel`): an unknown `network_type` leaves `G` undefined (UnboundLocalError);
    `plot_*` with one α fails because `zip(axes, ...)` needs an array of axes; `update_temperature` has no T clip, so
    σ → 0 sends T → ∞; T0 = 0 divides by zero; the "glauber" methods are Metropolis; `plot_susceptibility_vs_returns` resets
    `h_hist` (unused) instead of `m_hist` *(partly known: legacy code)*.
19. **`fetch_market_data`** drops any ticker with a single NaN (`prices.notna().all()`), so one missing quote
    removes a stock. Its `__main__` ticker list has duplicates (`WM`, `TWX`, `CMCSA`). `freeze_data.py` handles
    all this properly; `calibrate_real.py` still uses the old path.
20. **Import side effects**: importing `model.py` creates `results/figures/` in the working directory and imports
    yfinance, networkx and matplotlib.animation, even for pure simulation.

### Severity 3: reproducibility
21. **Seeds tied to grid position**: pilot RNGs are keyed by `i_T0` (`model.py:866`), so adding one T0 value
    changes every later row's random stream.
22. **Seed collisions**: `k_under_feedback.py` seeds with `int(100*G)`, so G = 0.501 and 0.509 share a stream.
23. **Bit-identical runs across machines aren't guaranteed**: the numba kernels use `np.exp`/libm, and a single
    acceptance decision decided by the last bit makes trajectories diverge. "Seed-pinned snapshot" tests (REPORT's next
    steps) should compare statistics within a tolerance, or pin the platform and numba version.

---

## B. Edge cases in the model concept

1. **Finite N means no true phase transition.** With N = 29 or 100 there is only a smooth crossover. λ_max(J) is a
   *mean-field* estimate that overshoots on sparse or heterogeneous networks (2D lattice: λ_max = 4 versus the exact
   T_c ≈ 2.269). On the 87%-dense us100 network the mean-field estimate should be close; on thresholded sparse networks it won't be.
2. **Z₂ symmetry and ergodicity.** With h = 0, ⟨m⟩ = 0 in equilibrium, but below the crossover the time to flip
   between ±m grows roughly like exp(N). The zero-mean z test and the random/all-up comparison detect this,
   but the results depend on run length. This is also why `early_warning`'s "noise-driven flips" are unpredictable by construction.
3. **Feedback breaks detailed balance.** With α > 0, T(t) depends on the trajectory, so the stationary distribution is not
   Boltzmann at any T. Calibration statistics measured at α = 0 (k, σ0, ε) describe the system only to linear order. The
   loop gain G = α|ε| ≥ 1 is the linear stability limit; above it, T is held only by the clip [0.05, 20]·T0.
4. **Returns ∝ level m.** Returns are bounded (|r| ≤ κ), so the kurtosis at α = 0 is the Binder ratio, ≤ 3 in the
   mixed phase, and the Hill index is infinite. Fat tails can only come from the feedback *(known)*.
   Autocorrelated m means autocorrelated returns unless k is long enough, which is why the thinning interval k exists.
5. **σ is the std of the *level* m over 20 days**, not of daily changes. In the "change" and "cluster" mappings it is the
   std of the return. The two give different feedback meanings, and the windowed std has a sharp 20-day memory
   cutoff *(known)*.
6. **Correlation network is static and in-sample.** J is built from the same full period it is compared with
   (look-ahead), and 2005–2024 correlations are not stationary (2008 and 2020 raise them). The noise edge for
   N = 100, T = 5032 is (1+√(N/T))² ≈ 1.30, and the standard error of a single correlation is about 1/√T ≈ 0.014,
   so the 0.3 threshold is well above noise. A shorter window (e.g. `early_warning` rolling J) changes this.
7. **Market mode dominates.** All J ≥ 0 makes the model ferromagnetic, so λ_max is the market mode and there is no
   frustration or anti-correlation. Hedging and sector rotation can't be represented.
8. **Cluster mapping ≠ Cont–Bouchaud.** Here a cluster trades in the direction of its spin. In Cont–Bouchaud the
   direction is random. Also, `act > 0.5` makes the trade probability exceed 1 (it saturates silently).
9. **Bornholdt kernel** picks random sites with replacement, while its docstring says "random order".
10. **Survivorship bias** in the universe *(known)*.

---

## C. Known comparisons (functions with exact or textbook answers)

### Spin dynamics
| Check | Exact answer | Targets |
|---|---|---|
| J = 0 (or T → ∞): m is binomial | ⟨m²⟩ = 1/N, Binder R = 3 − 2/N | `_metropolis_pilot`, `compute_run_stats` |
| J = 0 Metropolis: every attempt flips | lag-1 ACF of m per sweep = (1 − 2/N)^N → e⁻² ≈ 0.135; τ_int = (1+ρ)/(2(1−ρ)) | `_acf`, `compute_run_stats` |
| Small N (≤ 14), any J | Enumerate all 2^N states: exact ⟨m²⟩, ⟨m⁴⟩, R(T) | pilot kernel (strongest correctness test) |
| Curie–Weiss, J_ij = J/N | P(M) ∝ C(N,(N+M)/2)·exp(J(M²−N)/(2NT)), exact for N = 29, 100; T_c → J; λ_max = J(N−1)/N | pilot, crossover location, T0/λ grid |
| 2D periodic lattice | Onsager T_c = 2/ln(1+√2) ≈ 2.269; Binder crossing U* ≈ 0.61 | kernel; shows λ_max = 4 overshoots |
| 1D ring | ⟨s_i s_{i+r}⟩ = (t^r + t^{N−r})/(1+t^N), t = tanh(J/T) | kernel |
| Deploy at α = 0 vs pilot | **bit-identical** given the same spins and seed: deploy day d = pilot sweep (n_burn_d + d + 1)·k − 1 − n_burn_p | `_deploy_kernel` vs `_metropolis_pilot` |
| Swendsen–Wang bonds | p = 1 − e^{−2J/T}: T → ∞ gives all singletons, T → 0 gives aligned components | cluster mapping |
| Krawiecki on complete graph | λ_max = (N−1)/N (used in `scaling_checks`) | `_krawiecki_kernel` |

### Statistics
| Function | Known answer |
|---|---|
| `_acf`, `acf`, `ac`, `_acf(x,L)` | Equal to the direct `np.correlate`; AR(1) gives ρ^L; white noise ≈ 0 ± 1/√n |
| `compute_run_stats` τ_int | AR(1): (1+ρ)/(2(1−ρ)); `converged` ⇔ τ_int < n/300 |
| z test | iid zero-mean: P(z > 3) ≈ 0.0027; AR(1) with the correct τ: same |
| Binder R | Gaussian 3, ±1 coin 1, uniform 9/5 |
| `thinned_stats` | AR(1) thinned by k has lag-1 ρ^k; mean rolling std (ddof 0, w = 20) of iid N(0,σ²) ≈ 0.962σ (c₄ bias, same bias in σ0 and deploy, so it cancels) |
| eps OLS | s = c·T^ε exactly gives ε exactly, with SE ≈ 0 |
| `stylised_facts` / `moments` | Gaussian: kurtosis 3, E\|z\| = √(2/π), P(\|z\|>3) = 0.0027; Student-t ν > 4: kurtosis 3 + 6/(ν−4); Laplace 6; uniform 1.8; 5-day kurtosis of iid = 3 + (κ−3)/5 |
| `hill` | Pareto(α) gives α; Student-t(ν) gives ≈ ν (biased at 5%) |
| `garch_fit`/`garch_simulate` | Recovers (ω, a, b, ν); unconditional var ω/(1−a−b); kurtosis formula when finite |
| GJR `Fit` | Parameter recovery; LR size 5% under γ = 0 (the script's `--simulate` already checks this) |
| `newey_west_t` | iid: t ~ N(0,1) |
| QLIKE | Minimised by the true variance |
| `network_data` mp_edge | iid returns: top eigenvalue of C ≈ (1+√(N/T))² |

---

## D. Dependencies

1. **`requires-python = ">=3.9"` is wrong.** The scripts use `zip(..., strict=True)` (3.10+), so on 3.9 they fail with a
   TypeError. The lock resolves separate 3.9-era forks (numpy 2.0.2, numba 0.60, scipy 1.13) that nobody tests.
   Set `>=3.12` to match `.python-version`, or at least `>=3.10`.
2. **No upper bounds; major versions already crossed.** Installed: numpy 2.5.3, numba 0.67.0, pandas **3.0.6**,
   scipy 1.18.1, matplotlib 3.11.2, yfinance 1.7.0. pandas 3 brings copy-on-write and a default string dtype. The frozen `.pkl` files
   (`rets_*.pkl`, `figdata.pkl`, `compare.pkl`) are pickled DataFrames, and pandas does not guarantee pickles load across
   major versions. Consider also saving returns as parquet/CSV or `.npz`.
3. **numba ↔ numpy coupling.** Each numba release supports a narrow numpy range, so upgrading numpy alone can break the import.
   On-disk caches are tied to the import name *(known)*. numba's `np.random.seed` RNG is separate from NumPy's,
   and its draw sequence may change between numba versions (affects bit-identical tests).
4. **yfinance is a hard runtime dependency** of the package because `model.py` imports it at the top. It needs network
   access, Yahoo's data gets revised, and its output layout has changed across versions (`_close` in `freeze_data.py` handles this;
   `fetch_market_data` does not). Moving it to an optional extra, or into the function, would make simulation-only use
   (e.g. for comparison) lighter. networkx and matplotlib are likewise only needed by legacy code.
5. **No external statistics libraries.** GARCH, Hill, bootstrap and Newey–West are written by hand, so the comparisons in C
   are the only check on them. `arch`/`statsmodels` could be added as *dev-only* reference implementations for tests.
6. **pytest config** points at a nonexistent root `tests/`, and `stylized_facts/tests/` is git-ignored *(known)*.

---

## Suggested next step

Add `stylized_facts/tests/test_known_solutions.py` with one test per row of section C, plus regression tests for A1–A3 and A8–A15. Most can run in seconds with small N and short runs. Fix the Severity 1 items after tests show the problem.
