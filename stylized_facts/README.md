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
| Return-model comparison | `scripts/compare_return_models.py` | Six spin-model variants (`level`: r = m; `change`: r = Δm; `cluster` and `cluster_stable`: trading by Fortuin–Kasteleyn clusters; `bornholdt`; `krawiecki`), plus GARCH(1,1)-t and i.i.d. Gaussian as yardsticks; see *Return-model comparison* below. Each is fitted by simulated moments to the index and scored by J (lower is closer), with p-values and coverage from target-length windows. Also checks the published mechanisms at their own settings for larger N. | `--figdata` (from `make_figures.py`), `--target-csv`, `--models`, `--quick`, `--jobs`, `--add`, `--windows`, `--weights diag\|full`, `--skip-scaling`, `--replot`, `--out` | `figR1…figR5.png`, `return_models.md`, `compare.pkl`, `calibration_log.txt` |
| Clock under feedback | `scripts/k_under_feedback.py` | Re-runs the deployed model at the chosen temperature for several loop gains and clocks k (default 1, 2, 4 and 8 times the calibrated k), to check whether a larger k removes lag-1 return autocorrelation. Prints AC(r, 1), mean AC(\|r\|) over lags 1–20, kurtosis and mean T/T0. | `--figdata`, `--gains`, `--ks`, `--runs`, `--days` | prints only |
| Breadth test | `scripts/garch_x_breadth.py` | Real-data test, independent of the model package. Breadth m_t = mean sign of the day's stock returns. Asks whether m_{t−1}² predicts the index's variance inside a GJR-GARCH-t, controlling for cross-sectional dispersion D. In-sample likelihood-ratio and Wald tests; out-of-sample QLIKE comparison with a Diebold–Mariano test after `--split`; residuals by breadth decile. | `--rets`, `--split` (2015-01-01), `--out`; `--simulate` with `--reps`, `--sim-days`, `--sim-stocks` checks the tests on simulated data | `garch_x.md`, `garch_x.png` |

### Legacy code (not used by the pipeline)

| Feature | Where | What it means | How to use |
|---|---|---|---|
| `FinancialIsingModel` class | `model.py` | Earlier object-based model: random networks (Erdős–Rényi, Barabási–Albert, small world) or an empirical J, Metropolis updates, volatility feedback (`update_temperature`), a trend-following external field (`update_external_field`), forced selling after large losses (`leverage_cascade`), susceptibility and energy. `simulate_deployed` reproduces its dynamics with h = 0 and no leverage. | Not called by any script. |
| `plot_*` helpers | `model.py` | Return distributions, volatility clustering, and susceptibility against returns. They predate the calibration (one sweep per step, no calibrated σ0) and save PNGs to `results/figures/`. | Not called by any script. |

### Symbols and quantities

Every symbol with a physical or model meaning, as the code defines it. "Row" means one temperature in the T0 scan.

#### Network and dynamics

| Symbol | Name | Definition in the code | Meaning | Where |
|---|---|---|---|---|
| N | number of agents | number of stocks kept | One spin per stock. Run time grows with N². | everywhere |
| s_i | spin | ±1 | Stock i's sentiment: +1 buy, −1 sell. | kernels |
| m | magnetisation | Σ s_i / N, takes N + 1 values in [−1, 1] | Net order imbalance: how aligned the market is. The return is built from m. | kernels |
| C | correlation matrix | `rets.corr()` | Empirical co-movement of daily log returns. | `build_empirical_J` |
| J_ij | coupling | C_ij if C_ij > 0.3, else 0; zero diagonal; scaled so the mean non-zero J_ij = 0.1 | How strongly stock j pulls stock i towards its own sign. All couplings are ≥ 0 (ferromagnetic: no stock pushes another the opposite way). | `build_empirical_J` |
| λ | λ_max(J) | largest eigenvalue of J | Mean-field estimate of the temperature where order sets in. Every temperature is quoted as T/λ, so results compare across networks. | `calibrate_parameters` |
| market mode | top eigenvector of C | `eigh(C)`, sign fixed so loadings sum > 0 | The direction in which all stocks move together; fig1 shows its share of variance. | `make_figures.network_data` |
| noise edge | Marchenko–Pastur edge | (1 + √(N/T_days))² | Largest eigenvalue that pure noise would give for N stocks over T_days days; eigenvalues above it are treated as signal in fig1. | `make_figures.network_data` |
| T | temperature | positive scalar | Noise in each agent's decision. Low T: agents copy their neighbours and the market locks into one sign. High T: agents act independently and m stays near 0. | kernels |
| T0 | baseline temperature | chosen by `select_T0` | The operating point: the temperature with no volatility shock (σ = σ0). | calibration |
| ΔE | energy change of a flip | 2 s_i Σ_j J_ij s_j | Cost of agent i disagreeing with its neighbours. Flipping against a strong consensus costs a lot. | kernels |
| Metropolis rule | update rule | flip if ΔE ≤ 0, else with probability e^(−ΔE/T) | Agents tend to align, with mistakes at rate set by T. | `_metropolis_pilot`, `_deploy_kernel` |
| sweep | one sweep | N single-agent update attempts at random sites | One unit of model time: on average every agent gets one chance to change its mind. | kernels |
| k | clock | Metropolis sweeps per trading day | How much the market "thinks" between daily prices. Too small and daily m values are correlated (spurious return autocorrelation); larger k costs run time. | calibration, deployment |
| σ | recent volatility | std of the last 20 daily m (deployed model) | What the volatility feedback reacts to. In `compare_return_models.py` it is the std of the last 20 daily **returns**, which differs from m for the `change` and `cluster` mappings. | `_deploy_kernel`, `_ours_kernel` |
| σ0 | baseline volatility | the chosen row's `s_mean` (mean 20-day rolling std of m at k, no feedback) | The volatility the feedback treats as normal: T = T0 when σ = σ0. | `calibrate_parameters` |
| α | feedback exponent | T = T0·(σ/σ0)^(−α) | How hard temperature reacts to volatility. α > 0: high volatility lowers T, so agents herd more (panic). α = 0 turns feedback off. | `simulate_deployed` |
| G | loop gain | G = α·\|ε\| | The fraction of a volatility shock that comes back after one trip round the loop (see ε below). G < 1: shocks die out (linearly stable). G ≥ 1: they grow until T hits its clip. The scripts set feedback by G and convert with α = G/\|ε\|, so G means the same on every network. | `make_figures`, `compare_return_models` |
| T clip | temperature bounds | T kept in [0.05, 20]·T0 | Stops runaway feedback from sending T to 0 or ∞. `clip_frac` is the share of days at a bound; it should be 0 in a healthy run. | `simulate_deployed` |
| κ | price impact | r = κ·m, default 1.0 | Converts imbalance into a return. Not calibrated, and the scale-free statistics used here don't depend on it. | `simulate_deployed` |
| h, h0 | external field | added to every agent's local field | News or macro pressure pushing everyone one way. Legacy class only; the pipeline uses h = 0. | `FinancialIsingModel` |

#### ε: the elasticity of volatility with respect to temperature

ε = d ln s / d ln T0: the percentage change in the model's day-scale volatility s for a 1% rise in temperature, at the row's own clock k and with no feedback.

- **How it is measured** (`aggregate_by_T0`): each run's ln s at k is regressed on ln T0 across the row and its valid neighbours (rows p−1, p, p+1 that pass the run-quality checks). The slope is ε and its OLS standard error is SE. At least two valid rows are needed, or ε is undefined.
- **What its sign means:** ε < 0 means a hotter market is calmer (more independent agents, smaller swings in m). ε > 0 means hotter is more volatile.
- **Why it matters:** the feedback lowers T when σ rises. With ε < 0, lower T raises volatility, so a volatility shock feeds on itself. A 1% rise in σ lowers T by α%, which raises σ by α·|ε|%. That ratio is the loop gain G. With ε > 0 the same rule would damp volatility instead.
- **How it is used:** `select_T0` requires the upper bound ε + 2·SE < 0 (`eps_sigma = 2`), so the feedback is confidently amplifying. Among the rows that pass every check, it picks the one with the most negative upper bound. `make_figures.py` and `compare_return_models.py` then set the feedback through G and the chosen row's ε.
- **Caveat in the code:** fig3 (`fig3_griffiths`) is described in `make_figures.py` as showing that "eps > 0 only appears where runs don't mix". The code labels such rows `slow` or `frozen` (below).

#### Calibration statistics (per run, per row)

| Symbol | Name | Definition in the code | Meaning | Where |
|---|---|---|---|---|
| σ_m | RMS magnetisation | √⟨m²⟩ over a pilot run | Typical size of the imbalance. Falls as T rises. | `compute_run_stats` |
| R | Binder ratio | ⟨m⁴⟩ / ⟨m²⟩² | Shape of m's distribution: 3 for a Gaussian, 1 for two spikes at ±m, below 3 for a two-humped distribution. With no feedback and r = κ·m, R is the return kurtosis. | `compute_run_stats` |
| q | order parameter | \|⟨m⟩\| / σ_m | Near 1 when the run is stuck on one sign; near 0 when it visits both. | `compute_run_stats` |
| τ_int | integrated autocorrelation time | 0.5 + Σ ACF(m) up to Sokal's window W | Sweeps between effectively independent samples of m. | `compute_run_stats` |
| converged | τ_int reliable | Sokal window found: W ≥ 6·τ_int with W < n/50 (so τ_int < n/300) | Whether the run was long enough to measure its own correlation time. | `compute_run_stats` |
| n_eff | effective samples | Σ over runs of n_pilot / (2τ_int) | How many independent values of m the row really has. | `aggregate_by_T0` |
| z | zero-mean test | \|⟨m⟩\| / (std(m)·√(2τ_int/n)) | With h = 0 the true mean of m is 0. z > 3 means the run is stuck on one sign. | `compute_run_stats` |
| s | day-scale volatility | mean 20-sample rolling std of m sampled every k sweeps | The model's daily volatility at clock k with no feedback. ε is built from it, and σ0 is its value at the chosen row. | `thinned_stats` |
| AC1 at k | thinned lag-1 autocorrelation | lag-1 autocorrelation of m sampled every k sweeps, signed, pooled over runs | Checks that k makes successive days close to independent. | `thinned_stats`, `aggregate_by_T0` |
| equilibrated | equilibration check | random-start and all-up-start runs agree on σ_m, R and s within 2 combined SE | Whether the result depends on the starting state. REPORT.md notes this test is noisy. | `aggregate_by_T0` |
| regime | `slow` / `frozen` / `mixing` | `slow`: fewer than 75% of runs converged. `frozen`: more than 10% have z > 3. `mixing`: neither | How a row behaves: too slow to measure, stuck on one sign, or switching freely. Used to shade and label the figures. | `make_figures.classify` |

### Settings that change the model's behaviour

| Setting | Default | Where | Effect |
|---|---|---|---|
| Correlation cut-off | 0.3 | `build_empirical_J(threshold=)`, `freeze_data.py --threshold`, `make_figures.py --threshold` | Higher: a sparser network, smaller λ, weaker herding. `make_figures.py` stops if an existing J was built at a different value. |
| Coupling scale | mean non-zero J_ij = 0.1 | `build_empirical_J(normalize=True)` | Sets the units of temperature. Changing it rescales every T. |
| T0 grid | 13 log-spaced values, 0.35λ to 1.30λ | `calibrate_parameters(T0_search=)` | The temperatures the calibration can choose from. |
| Seeds per row, starts | 8 seeds × {random, all-up} = 16 runs | `calibrate_parameters(n_seeds=)` | More runs: tighter SEs and a less noisy equilibration check. |
| Pilot length, burn-in | function default 10,000 / 2,000 sweeps; `make_figures.py` and `model.py` use 50,000 / 10,000 (`--quick`: 10,000 / 2,000) | `n_pilot`, `n_burn` | Longer runs give more effective samples and make the convergence check easier to pass. |
| Calibration seed | 42; `make_figures.py` uses 42, 43, 44 | `seed=`, `--seeds` | REPORT.md notes the chosen T0 depends on the seed. |
| Rolling window | 20 days | `window=` | The window for s, σ0 and the feedback's σ. The feedback's memory ends here. |
| Thinning constant | k = ⌈3 · p75(τ_int)⌉ over converged runs | `THIN_C = 3.0` | Larger: more sweeps per day, less autocorrelation, longer runs. |
| Sokal constant | c = 6, window searched up to n/50 | `compute_run_stats` | Stricter values mark more runs as not converged. |
| Converged share | ≥ 0.75 | `MIN_FRAC_CONVERGED` | Row check. |
| Stuck share | ≤ 0.10 of runs with z > 3 | `MAX_FRAC_Z_HIGH` | Row check. |
| Effective samples | ≥ 50 per run | `MIN_N_EFF_PER_RUN` | Row check. |
| Valid s share | ≥ 0.75 of runs | `select_T0(min_frac_s_valid=)` | Row check. |
| Thinning check | \|AC1\| + 2·SE ≤ 0.10 | `select_T0(max_ac1=, ac1_sigma=)` | Row check: k makes days near-independent. |
| ε check | ε + 2·SE < 0 | `select_T0(eps_sigma=)` | Row check: the feedback must amplify. |
| Consensus over seeds | the row that passes in most seeds; ties to the most negative mean ε + 2·SE. k = median over seeds; σ0 and ε = means | `make_figures.consensus_row` | The (T0, k, σ0, ε) every downstream script uses, stored in `figdata.pkl`. |
| Loop gains | 0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5 (plus `--showcase-gain`, 0.5) | `make_figures.GAINS` | Feedback strengths simulated for fig6 and fig7. |
| Deployment runs | 4 runs × 10,000 days, 500-day burn-in (`--quick`: 2 × 3,000) | `make_figures.FULL`, `simulate_deployed(n_burn=)` | Sample size behind each loop gain. Seeds are `[2026, gain index, run]`. |
| T clip | [0.05, 20]·T0 | `simulate_deployed(T_clip=)` | Bounds on runaway feedback. |
| α in `model.py` `__main__` | 0.4 | `model.py` | The one feedback strength that demo run uses. |

### Return-model comparison: parameters and statistics

Settings in `scripts/compare_return_models.py`.

| Symbol or setting | Model or role | Meaning |
|---|---|---|
| `level`: r = m | ours | Price moves with excess demand. Grid: G ∈ {0 … 1.4}, k = 1, 2, 4 × calibrated k. |
| `change`: r = m_t − m_(t−1) | ours | Market clearing against fundamentalists: the price tracks m, so the return is its change. Grid: G ∈ {0 … 1.9}, k ∈ {1, 2, 4, 8} sweeps (absolute, not multiples). |
| `cluster` | ours | Each day, Fortuin–Kasteleyn clusters are built: aligned neighbours are bonded with probability 1 − e^(−2J_ij/T). Each cluster trades its spin × size with probability 2a; r = sum over trading clusters / N. Grid: G ∈ {0 … 1.9}, a ∈ {0.04 … 0.3}, k = 2 × calibrated k. |
| `cluster_stable` | ours | The same as `cluster`, with G kept below 1 (0 to 0.9), where T stays near T0. |
| a | cluster activity | Probability scale for a cluster trading on a given day: each cluster trades with probability 2a (Cont & Bouchaud 2000 activity). |
| `bornholdt`: θ, α_rel | Bornholdt (2001) | Heat-bath dynamics, one sweep a day, with local field h_i = Σ J_ij s_j − α_B·s_i·\|M\|. The second term penalises each agent's current choice more strongly the more aligned the whole market is. T = θ·λ and α_B = α_rel·λ. r = ΔM. |
| `krawiecki`: A, h | Krawiecki, Hołyst & Helbing (2002) | All agents update at once with field A·ξ(t)·Σ J_ij s_j / λ + h·ζ_i(t), with ξ and ζ uniform on (−1, 1). A random common coupling strength each day ("attractor bubbling"); h is individual noise. r = M. |
| GARCH(1,1)-t: ω, a, b, ν | statistical yardstick | σ²_t = ω + a·z²_(t−1) + b·σ²_(t−1) with Student-t(ν) shocks, fitted by maximum likelihood. a + b near 1 means persistent volatility; small ν means fat tails. |
| Gaussian i.i.d. | null model | No tails and no clustering. |
| σ0 (comparison) | feedback reference | 20-day std of the model's daily returns at α = 0 (4,000 days, seed 99), cached per (k, mapping, a). |
| burn-in | per family | 500 days (ours), 2,000 days (Bornholdt, Krawiecki). |
| E\|z\| | targeted moment | Mean absolute standardised return. |
| AC(r,1) | targeted moment | Lag-1 return autocorrelation (should be ≈ 0). |
| Hill | targeted moment | Tail index from the largest 5% of \|z\| (`HILL_FRAC`), capped at 30 (`HILL_CAP`; bounded returns can give an infinite index). Lower means fatter tails. |
| AC\|r\| L | targeted moments | Autocorrelation of \|z\| at lag L (averaged over L−1, L, L+1), for L = 1, 5, 10, 25, and also 50 and 100 when the target has ≥ 2,500 days (`LONG_TARGET`). Measures volatility clustering. |
| kurtosis, kurtosis 5d, P(\|z\|>3), AC(r²,1) | untargeted moments | Checked after fitting, not fitted. Kurtosis 5d uses 5-day sums. |
| J (statistic) | fit score | (model moments − target moments)ᵀ W (…). Lower is closer. Not the same J as the coupling matrix. |
| W | moment weights | `diag` (default): 1 / bootstrap variance of each moment. `full`: inverse of the full bootstrap covariance (Franke & Westerhoff 2012). |
| block bootstrap | target uncertainty | Moving blocks of max(50, n/20) days; 2,000 resamples (`--quick`: 500). Gives the moments' variances and 95% intervals. |
| two-stage fit | `calibrate` | Grid search at 8,000 days × 2 seeds, then the best 3 re-scored at 20,000 days × 4 seeds (`--quick`: 3,000 × 1, then 6,000 × 2). Run lengths grow with the target: at least 2× and 4× its length. |
| p_J | `evaluate` | Share of target-length model windows whose J against the model's own long run is ≥ the data's J. A large p means the data look like a typical draw from the model. |
| coverage | `coverage` | Share of model windows with a moment inside the target's 95% interval; joint coverage = all targeted moments inside at once. |
| scaling checks | `scaling_checks` | The published dynamics at their published settings for larger N: Krawiecki all-to-all at A = 1.6, h = 0.01 for N = 29 to 1,000; Bornholdt at T = 1, α = 8 on square lattices and all-to-all networks up to about 1,000 agents. Tests whether system size limits the tails. |

### Breadth test: symbols

Settings in `scripts/garch_x_breadth.py`. Returns are in percent.

| Symbol | Meaning |
|---|---|
| r_t | Equal-weight index return of the stocks in `--rets`. |
| m_t | Data breadth: mean of sign(r_it) across stocks. The data's own magnetisation (share up minus share down). |
| D_t | Robust dispersion: (1.4826 × median absolute deviation of the day's stock returns)². High alignment usually means low dispersion; D separates "moved together" from "moved apart". |
| μ, φ | Mean and AR(1) term of the index return. |
| ω, a, b | GARCH constant, reaction to yesterday's shock, persistence. |
| g | GJR asymmetry: extra variance after down days. |
| γ | Effect of yesterday's breadth m²_(t−1) on today's variance. γ > 0 would mean alignment raises volatility (the herding idea). |
| δ | Effect of yesterday's dispersion D_(t−1). |
| ν | Student-t degrees of freedom of the shocks. |
| models | GARCH; GJR; GJR + breadth; GJR + dispersion; GJR + both. |
| QLIKE | Forecast loss log σ̂² + proxy/σ̂², with proxy = the GJR baseline's squared residual. Lower is better. |
| DM t | Diebold–Mariano statistic on the loss difference, Newey–West lag ⌊4(n/100)^(2/9)⌋. |
| `--split` | 2015-01-01: parameters fitted before this date, forecasts scored after it. |
| decile check | Baseline squared residuals / forecast variance, by decile of m²_(t−1). Should be 1 in every decile if the model is right. |

### Gaps found while writing this table

- No script in the repo writes `data/rets_2005_2007.pkl` or `data/J_2005_2007.npy`, the default inputs of `make_figures.py`. `calibrate_real.py` writes `data/rets_big.pkl` and `data/J_big.npy` instead. Both pairs exist in the local `data/`, so the 2005–2007 files were made some other way.
- κ is not calibrated: `calibrate_parameters` takes `target_vol` but doesn't use it.
- `model.py`'s command-line flags are parsed but have no effect.
