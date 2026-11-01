# Stylized facts

Tries to reproduce the stylized facts of financial returns with a financial Ising model calibrated on an empirical stock-correlation network.

**Status:** Paused. Known limits: [I will fill this in]

The full write-up, figures and run commands are in [REPORT.md](REPORT.md). Run the scripts from inside this folder (`cd stylized_facts`), since they use paths relative to it (`data/`, `results/`, `universes/`).

## Features

What each part of the code does and how it is used. Run commands from inside `stylized_facts/`. Each row describes what the code does, not what it found; findings are in [REPORT.md](REPORT.md).

### Data

| Feature | Where | What it means | How to use | Writes |
|---|---|---|---|---|
| Ticker universe | `universes/tickers_us_large_cap.csv` | 202 US large caps (columns `ticker,sector,core`); 101 are marked `core`. | Input to `freeze_data.py`. | — |
| Freeze a universe | `scripts/freeze_data.py` | Downloads prices from Yahoo once, drops tickers that start late, end early or have too many gaps, forward-fills short gaps, flags big single-day moves, and builds J. Everything downstream reads the frozen files, so results don't change when Yahoo's data does. | `--core-only` (about 100 stocks), `--sector …`, `--exclude …`, `--start/--end`, `--threshold` (J cut-off, 0.3), `--grace`, `--max-missing`, `--max-gap`, `--flag`, `--repair`, `--tag`, `--out`. Needs internet. | `data/rets_<tag>.pkl`, `J_<tag>.npy`, `sectors_<tag>.csv`, `outliers_<tag>.csv`, `freeze_<tag>.txt` |
| Download returns | `fetch_market_data` (`model.py`) | Adjusted closes from yfinance turned into daily log returns; tickers that fail are dropped. | Called by `calibrate_real.py` and `model.py`'s `__main__`. | — |
| Coupling network J | `build_empirical_J` (`model.py`) | J_ij = correlation of stocks i and j where it exceeds the threshold (0.3), else 0, rescaled so the mean non-zero coupling is 0.1. Its largest eigenvalue λ sets the temperature scale. | `J, C = build_empirical_J(rets, threshold=0.3)` | — |

### Model core (`src/ising_market/model.py`)

| Feature | Where | What it means | How to use | Writes |
|---|---|---|---|---|
| Spins and magnetisation | throughout | Each stock is a spin s_i = ±1 (buy or sell sentiment). Magnetisation m = Σ s_i / N is the net order imbalance, in [−1, 1]. | — | — |
| Temperature T0 | calibrated | Noise level of the spin updates. Low T: stocks lock into agreement; high T: they flip independently. Quoted as a multiple of λ. | From `calibrate_parameters`. | — |
| Clock k | calibrated | Metropolis sweeps per trading day, chosen so successive days are close to uncorrelated. | From `calibrate_parameters`; pass to `simulate_deployed`. | — |
| Volatility feedback α | `simulate_deployed`, `_deploy_kernel` | Each day T = T0·(σ/σ0)^(−α), with σ the std of the last 20 daily m. High recent volatility lowers T, which increases herding. Loop gain G = α·\|ε\|; G = 1 is the linear stability limit. T is clipped to [0.05, 20]·T0. | `alpha=` in `simulate_deployed`. | — |
| Return | `simulate_deployed` | r = κ·m each day. κ is a scale factor that is not calibrated. | `sim["r"]` | — |
| Compiled kernels | `_metropolis_pilot`, `_deploy_kernel` | numba versions of the Metropolis dynamics, for speed. Cached on disk (see the numba gotcha in REPORT.md). | Internal. | `__pycache__/*.nbi`, `*.nbc` |

### Calibration (`calibrate_parameters` and helpers)

| Feature | Where | What it means | How to use | Writes |
|---|---|---|---|---|
| T0 scan | `calibrate_parameters` | Pilot runs with no feedback (α = 0) at 13 temperatures from 0.35λ to 1.30λ, 8 seeds, from random and all-up starts. | `calibrate_parameters(rets, J, n_pilot=50_000, n_burn=10_000, seed=42)` | — |
| Per-run statistics | `compute_run_stats`, `_acf` | Per run: RMS magnetisation, Binder ratio (equal to the return kurtosis, since r ∝ m), integrated autocorrelation time τ_int, whether the run converged, a zero-mean test. | Internal. | — |
| Per-temperature checks | `aggregate_by_T0`, `thinned_stats` | Per temperature: k = ⌈3·p75(τ_int)⌉, lag-1 autocorrelation at k, rolling volatility s, an equilibration check (random vs all-up starts), and elasticity ε = d ln s / d ln T0. | Read `result["T0_table"]`. | — |
| Choosing T0 | `select_T0` | Keeps temperatures that pass every check and have ε + 2 SE < 0 (volatility falls as T rises), then picks the most negative upper bound. Returns `T0 = None` if none pass. | `result["T0"]`, `["k"]`, `["sigma0"]`, `["selection"]` | — |
| Calibrate the original sample | `scripts/calibrate_real.py` | Downloads a long 2005–2007 ticker list, freezes it, and runs the calibration for seeds 42–44, printing each seed's table. No flags; needs internet; overwrites its outputs. | `uv run python scripts/calibrate_real.py` | `data/rets_big.pkl`, `data/J_big.npy`, `results/calibration_real.pkl` |
| Calibrate from `model.py` | `model.py` `__main__` | Downloads a fixed list of 30 tickers (2005–2007), calibrates, and, if a T0 is chosen, runs the deployed model at α = 0.4 and prints its stylized facts. Saves nothing. Its command-line flags are parsed but not used. | `uv run python -m ising_market.model` | — |

### Simulation and measurement

| Feature | Where | What it means | How to use | Writes |
|---|---|---|---|---|
| Deployed model | `simulate_deployed` | Runs the calibrated model day by day with feedback. Returns daily r, m, T, and the fraction of days T hit its clip. | `simulate_deployed(J, T0, k, alpha, sigma0, n_days=10_000, rng=…)` | — |
| Stylized-fact summary | `stylised_facts` | Kurtosis (3 = Gaussian), Jarque–Bera p-value, Student-t degrees of freedom, AC(r) and AC(\|r\|) up to lag 20. The docstring lists the targets for daily equity returns: kurtosis 5–20, t dof 3–5, AC(r) ≈ 0, AC(\|r\|) positive and slowly decaying. | `stylised_facts(sim["r"])` | — |

### Analysis scripts

| Feature | Where | What it means | How to use | Writes |
|---|---|---|---|---|
| Figures and summary | `scripts/make_figures.py` | Reruns the calibration for each seed, picks the temperature that passes in the most seeds, runs the deployed model across loop gains, and compares it with the equal-weight index of the same stocks. fig1 network, fig2 regimes across T0, fig3 why ε > 0 appears only where runs don't mix, fig4 m(t) traces, fig5 selection, fig6 feedback, fig7 model vs data. | `--rets`, `--J` (built if missing), `--sectors`, `--seeds`, `--threshold`, `--showcase-gain`, `--quick`, `--replot`, `--formats`, `--out` | `fig1…fig7.png`, `summary.md`, `figdata.pkl`, `calibration_log.txt` |
| Return-model comparison | `scripts/compare_return_models.py` | Five ways of turning spins into returns (`level`: r = m; `change`: r = Δm; `cluster`: trading by Fortuin–Kasteleyn clusters; `bornholdt`; `krawiecki`), plus GARCH(1,1)-t and i.i.d. Gaussian as yardsticks. Each is fitted by simulated moments to the index and scored by J (lower is closer), with p-values and coverage from target-length windows. Also checks the published mechanisms at their own settings for larger N. | `--figdata` (from `make_figures.py`), `--target-csv`, `--models`, `--quick`, `--jobs`, `--add`, `--windows`, `--weights diag\|full`, `--skip-scaling`, `--replot`, `--out` | `figR1…figR5.png`, `return_models.md`, `compare.pkl`, `calibration_log.txt` |
| Clock under feedback | `scripts/k_under_feedback.py` | Re-runs the deployed model at the chosen temperature for several loop gains and clocks k (default 1, 2, 4 and 8 times the calibrated k), to check whether a larger k removes lag-1 return autocorrelation. Prints AC(r, 1), mean AC(\|r\|) over lags 1–20, kurtosis and mean T/T0. | `--figdata`, `--gains`, `--ks`, `--runs`, `--days` | prints only |
| Breadth test | `scripts/garch_x_breadth.py` | Real-data test, independent of the model package. Breadth m_t = mean sign of the day's stock returns. Asks whether m_{t−1}² predicts the index's variance inside a GJR-GARCH-t, controlling for cross-sectional dispersion D. In-sample likelihood-ratio and Wald tests; out-of-sample QLIKE comparison with a Diebold–Mariano test after `--split`; residuals by breadth decile. | `--rets`, `--split` (2015-01-01), `--out`; `--simulate` with `--reps`, `--sim-days`, `--sim-stocks` checks the tests on simulated data | `garch_x.md`, `garch_x.png` |

### Legacy code (not used by the pipeline)

| Feature | Where | What it means | How to use |
|---|---|---|---|
| `FinancialIsingModel` class | `model.py` | Earlier object-based model: random networks (Erdős–Rényi, Barabási–Albert, small world) or an empirical J, Metropolis updates, volatility feedback (`update_temperature`), a trend-following external field (`update_external_field`), forced selling after large losses (`leverage_cascade`), susceptibility and energy. `simulate_deployed` reproduces its dynamics with h = 0 and no leverage. | Not called by any script. |
| `plot_*` helpers | `model.py` | Return distributions, volatility clustering, and susceptibility against returns. They predate the calibration (one sweep per step, no calibrated σ0) and save PNGs to `results/figures/`. | Not called by any script. |

### Gaps found while writing this table

- No script in the repo writes `data/rets_2005_2007.pkl` or `data/J_2005_2007.npy`, the default inputs of `make_figures.py`. `calibrate_real.py` writes `data/rets_big.pkl` and `data/J_big.npy` instead. Both pairs exist in the local `data/`, so the 2005–2007 files were made some other way.
- κ is not calibrated: `calibrate_parameters` takes `target_vol` but doesn't use it.
- `model.py`'s command-line flags are parsed but have no effect.
