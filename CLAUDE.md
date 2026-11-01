# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working rules

- Never run git commit or push. I commit by hand; `git mv` staging is fine.
- Don't edit early_warning/DECISIONS.md, or leave placeholders like "[I will fill this in]" unfilled-in.
- Don't claim any result, calibration or finding the code has not produced. State limits plainly.
- early_warning/: tests first; never edit a test or threshold to make it pass.
- early_warning/: seed every simulation, and use only data up to time t in any indicator.
- early_warning/ must not import from stylized_facts/.
- Session log: append commands run, files changed and outputs to PROJECT_LOG.md.

## Layout: two independent projects, one uv environment

- `stylized_facts/`: the original project (paused). A calibrated Ising market model on an empirical stock-correlation network, tested against stylized facts of returns. Full write-up with findings, methods and known limits: `stylized_facts/REPORT.md`.
- `early_warning/`: new project on early-warning signals for regime flips, using the model as a lab. It is an empty scaffold and **must not import from or depend on `stylized_facts/`**.
- Root `pyproject.toml`, `uv.lock` and `.python-version` (3.12) are shared. The installed package `ising_market` comes from `stylized_facts/src` (`[tool.uv.build-backend] module-root`).

## Commands

```bash
uv sync                      # set up the environment
uv run ruff check .          # lint (line length 100; rules E, F, I, B, NPY)
```

`ruff check` already reports about 45 errors in `stylized_facts/` (as of 2026-10-22). Don't mass-fix them unasked; moved files are meant to stay as they are.

Run all `stylized_facts` scripts **from inside `stylized_facts/`**: every script, and `model.py` on import, uses paths relative to the working directory (`data/`, `results/`, `universes/`). `model.py` creates `results/figures/` wherever it is imported from. `REPORT.md`'s commands were written for the old root layout; `cd stylized_facts` first.

```bash
cd stylized_facts
uv run python scripts/make_figures.py --quick          # short pipeline check (29-stock data)
uv run python scripts/make_figures.py --replot         # redraw from results/figures/figdata.pkl
uv run python scripts/compare_return_models.py --replot --out <dir with compare.pkl>
uv run python scripts/garch_x_breadth.py --out <dir>   # ~20 s
uv run python scripts/k_under_feedback.py --gains 0.0 --runs 1 --days 2000
```

When checking that scripts still work, point `--out` at a scratch folder: `results/` is committed, and full runs overwrite it. `calibrate_real.py` has no flags and re-downloads from Yahoo, overwriting `data/` and `results/calibration_real.pkl`; `freeze_data.py` also downloads. The 100-stock `compare_return_models.py --quick` run took about 13 hours. Prefer `--replot` on saved pickles.

**Tests:** there are none yet. `pyproject.toml` sets pytest `testpaths = ["tests"]` at the root, where no `tests/` exists; `stylized_facts/tests/` is git-ignored and `early_warning/tests/` is empty. Pass a path explicitly, e.g. `uv run pytest early_warning/tests/test_x.py::test_name`. `stylized_facts/ising_handover/tests/` holds old, git-ignored check scripts (`t01_…`–`t11_…`) from the original development.

## Data flow (stylized_facts)

1. `freeze_data.py` (or `calibrate_real.py` for the original 29 stocks, 2005–2007) downloads with yfinance and freezes returns, J and sectors into git-ignored `data/` (e.g. `rets_us100_2005_2024.pkl`, `J_us100_2005_2024.npy`). Everything downstream reads these frozen files; a fresh download can differ.
2. `make_figures.py` reruns the calibration for seeds 42–44, picks the row that passes in the most seeds, runs the deployed model across loop gains, and writes fig1–fig7, `summary.md` and **`figdata.pkl`** (network, chosen row, index).
3. `compare_return_models.py` and `k_under_feedback.py` read that `figdata.pkl`, so they need no download. `compare_return_models.py` writes `compare.pkl`, which `--replot` re-scores and redraws (`--weights diag|full` changes scoring without re-simulating).
4. `garch_x_breadth.py` is self-contained: it reads the frozen returns directly and doesn't use `ising_market`.
5. Figures shown in `REPORT.md` are copies in `docs/figures/`, refreshed by hand with `cp` from `results/`.

## Model architecture (`stylized_facts/src/ising_market/model.py`)

- **Network:** `build_empirical_J` keeps correlations above 0.3 and rescales so the mean non-zero coupling is 0.1. Temperatures are quoted as multiples of λ = λ_max(J).
- **Calibration** (`calibrate_parameters`): pilot runs at α = 0 over a T0 grid from 0.35λ to 1.30λ (`_run_pilot` → numba `_metropolis_pilot`), per-run statistics (`compute_run_stats`: Binder ratio, τ_int, zero-mean test), per-temperature aggregation (`aggregate_by_T0`: thinning k, lag-1 check, equilibration check, elasticity ε), then `select_T0`. It returns `T0`, `k` (Metropolis sweeps per trading day) and `sigma0`; `T0` is `None` if no row passes.
- **Deployment:** `simulate_deployed` → numba `_deploy_kernel`: k sweeps a day, then the volatility feedback T = T0·(σ/σ0)^(−α), with σ the std of the last 20 daily m. Returns r = κ·m. `stylised_facts(r)` summarises kurtosis, JB, t dof and autocorrelations.
- **Legacy code:** the `FinancialIsingModel` class, the `plot_*` helpers and the CLI flags in `__main__` predate the calibration and aren't used by the pipeline.
- The return-model variants (level, change, cluster, Bornholdt, Krawiecki) and the GARCH/Gaussian baselines live in `scripts/compare_return_models.py`, not in the package.

## Gotchas

- Run time grows with N² and k; at 100 stocks, k = 248.
- **numba cache:** `@njit(cache=True)` caches are tied to the import name. Importing `model.py` as both `model` and `ising_market.model` gives `ModuleNotFoundError: No module named 'model'`. Fix: `find stylized_facts/src \( -name "*.nbi" -o -name "*.nbc" \) -delete`.
- The scripts fall back to adding `../src` to `sys.path` if `ising_market` isn't installed; `calibrate_real.py` instead inserts `"src"` relative to the working directory.
- Numba kernels use the legacy `np.random` API on purpose (hence `# ruff: noqa: NPY002`).
