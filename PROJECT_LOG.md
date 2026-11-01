# Project log

A running record of every working session on this repo: what was asked, what was done, what was decided, and how it was checked. Newest entry at the bottom.

Each entry has:
- **Prompts**: the requests as given (long ones quoted in full).
- **Steps**: what was done, in order.
- **Decisions**: choices made, the options considered, and who made them.
- **Verification**: what was run and what it showed.
- **Open items**: anything left undone or uncertain.

`early_warning/DECISIONS.md` stays separate. It is the hand-written decision table for the early-warning project.

---

## 2026-10-22: Split the repo into `stylized_facts/` and `early_warning/`

Tool: Claude Code (desktop app). Nothing was committed during this session; the owner commits by hand.

### Prompts

**Prompt 1** (verbatim):

> Reorganize this repo into two independent sections. Work in plan mode first:
> inspect the current layout, then show me the exact list of moves and new files
> before changing anything. Do not make any git commits; I will commit myself.
>
> CONTEXT
> - Section 1, `stylized_facts/`: the current project, which tries to reproduce
>   stylized facts from the financial Ising model. All code that currently exists
>   belongs here.
> - Section 2, `early_warning/`: a new, empty scaffold for a separate project
>   investigating early warning signals in the financial Ising model. It must not
>   import from or depend on `stylized_facts/`.
>
> TARGET STRUCTURE
> ```
> Financial-Ising-Model/
> ├── README.md              # one short paragraph per section, with its status
> ├── pyproject.toml         # shared uv environment (leave in place)
> ├── uv.lock                # leave in place
> ├── .gitignore             # leave in place
> ├── stylized_facts/
> │   ├── README.md          # status and known limits
> │   └── (all existing code, moved as-is)
> └── early_warning/
>     ├── README.md          # placeholder only: "Goal paragraph: to be written"
>     ├── DECISIONS.md       # empty template for me to fill in by hand
>     ├── src/
>     ├── tests/
>     ├── notebooks/
>     └── results/
> ```
>
> RULES
> 1. Move files with `git mv` so history is preserved. Do not edit the contents
>    of any moved file.
> 2. Leave pyproject.toml, uv.lock and .gitignore at the repo root. Add a
>    `.gitkeep` to each empty directory.
> 3. After the move, run each existing entry-point script from its new location.
>    If an import or relative path breaks, report it to me and propose the minimal
>    fix. Do not apply it until I approve.
> 4. Do not add any code, tests or results to `early_warning/`.
> 5. In `stylized_facts/README.md`, write the status as: "Paused. Known limits:
>    [I will fill this in]". Do not invent results or claims.
> 6. `early_warning/DECISIONS.md` should contain only this empty table header:
>    Date | Decision | Alternatives considered | Why | Evidence
>
> When finished, give me the `git status` output and a list of anything you were
> unsure about.

**Prompt 2:** "Yes, add the module-root line to pyproject.toml and run uv sync."

**Prompt 3:** "I would like all you have done, my prompts and your steps to be thoroughly documented throughout the course of this project. Backfill this reorganization step into either DECISION.md or another more clear file so that I can trace through steps in the future." (This led to this file.)

### Steps

1. **Inspected the layout.** Listed tracked files (`git ls-files`), ignored files, `pyproject.toml`, `.gitignore`, the README's path references, and every hard-coded path and `sys.path` line in `scripts/*.py` and `src/ising_market/model.py`. Checked how `.venv` had installed the package (`ising_market.pth` pointed at the old root `src/`).
2. **Found conflicts with the rules before planning** (see Decisions D1, D2) and asked about them.
3. **Wrote the plan and got approval.** The plan file is at `~/.claude/plans/effervescent-mixing-parasol.md` (outside the repo). It listed every move, every new file, the checks to run, and two expected breaks.
4. **Moved tracked files with `git mv`** (63 renames, contents unchanged):
   - `README.md` → `stylized_facts/REPORT.md`
   - `src/`, `scripts/`, `results/`, `docs/`, `universes/` → `stylized_facts/`
5. **Moved ignored or untracked folders with plain `mv`** (git doesn't track them): `data/`, `ising_handover/`, `patches/`, and the empty `notebooks/` and `tests/` → `stylized_facts/`.
6. **Created new files:**
   - `README.md` (root): one paragraph per section with its status.
   - `stylized_facts/README.md`: one-line description, "Paused. Known limits: [I will fill this in]", a link to `REPORT.md`, and a note to run scripts from inside `stylized_facts/`.
   - `early_warning/README.md`: "Goal paragraph: to be written".
   - `early_warning/DECISIONS.md`: the table header and separator row only.
   - `.gitkeep` in `early_warning/{src,tests,notebooks,results}/` and `stylized_facts/notebooks/`.
7. **Edited `.gitignore`** (D2): `tests/` → `/stylized_facts/tests/`.
8. **Ran the entry points from `stylized_facts/`** (see Verification) and reported two breaks (D3, D4).
9. **After approval (Prompt 2), fixed the package location** (D3): added to `pyproject.toml`
   ```toml
   [tool.uv.build-backend]
   module-root = "stylized_facts/src"
   ```
   then ran `uv sync`, which rebuilt and reinstalled only `ising-market`. `uv.lock` did not change.
10. **Started this log** (Prompt 3), linked it from the root README, and recorded the logging preference in Claude's memory so later sessions keep adding entries.

### Decisions

| ID | Decision | Alternatives considered | Why | Decided by |
|---|---|---|---|---|
| D1 | Move the old root README (36 KB stylized-facts write-up) to `stylized_facts/REPORT.md` unchanged, and write a new short `stylized_facts/README.md`. | Move it to `stylized_facts/README.md` and add the status line at the top. | Rule 1 forbids editing moved files, and rule 5 needs a new README with the status line. `REPORT.md` sits next to `docs/`, so its image links still work. | Owner (asked during planning) |
| D2 | Change `.gitignore`'s `tests/` to `/stylized_facts/tests/`. | Force-add `early_warning/tests/.gitkeep` and leave `.gitignore` alone; or leave the folder untracked. | The unanchored `tests/` rule would have ignored `early_warning/tests/` and anything later added to it. | Owner (asked during planning) |
| D3 | Add `module-root = "stylized_facts/src"` to `pyproject.toml` and run `uv sync`. | Leave it broken and use `uv run --no-sync`. | `uv_build` looks for `src/ising_market/` at the root by default, so `uv build` failed after the move and a normal `uv run` would fail on re-sync. | Proposed by Claude, approved by owner (Prompt 2) |
| D4 | No code change for working-directory-relative paths; documented "run from inside `stylized_facts/`" in its README. | Rewrite script paths to be relative to each file. | Rule 1 forbids editing moved files; running from `stylized_facts/` works as is. | Claude (in the approved plan) |
| D5 | Leave `.python-version` at the root. | Move it into `stylized_facts/`. | uv reads it from the project root, and both sections share one environment. | Claude (in the approved plan) |
| D6 | Treat `ising_handover/` and `patches/` as part of the stylized-facts project and move them. | Leave them at the root. | Both hold patches and tests for the existing model. | Claude (in the approved plan) |

### Verification

All runs were from `stylized_facts/`, with output sent to a temporary scratch folder outside the repo so no committed result was overwritten. Before the D3 fix they used `uv run --no-sync`.

| Entry point | What was run | Result |
|---|---|---|
| `scripts/make_figures.py` | Full run on the 29-stock data, `--out` to scratch | Wrote fig1–fig7 and `summary.md` |
| `scripts/garch_x_breadth.py` | Full run, `--out` to scratch | Wrote `garch_x.md` and `.png` in 17 s |
| `scripts/k_under_feedback.py` | `--gains 0.0 --runs 1 --days 2000` | Printed the k table |
| `scripts/compare_return_models.py` | `--replot` on a scratch copy of `results/return_models_us100_2005_2024/` | Redrew figR1–figR5 and `return_models.md` |
| `scripts/freeze_data.py` | `--help` only (a full run downloads from Yahoo and overwrites `data/`) | OK |
| `python -m ising_market.model` | `--help` only | OK |
| `scripts/calibrate_real.py` | Import line only (no flags; a run re-downloads and overwrites `data/` and `results/`) | OK |
| Package build | `uv build --wheel` to scratch | Failed before D3: "Expected a Python module at: src/ising_market/__init__.py" |
| After D3 | `uv sync`; `import ising_market` from `/tmp`; `uv run python scripts/k_under_feedback.py --help` | Package resolves to `stylized_facts/src/ising_market/`; plain `uv run` works |

`git status` afterwards: 63 staged renames; `.gitignore` and `pyproject.toml` modified; `README.md`, `PROJECT_LOG.md`, `early_warning/`, `stylized_facts/README.md` and `stylized_facts/notebooks/` untracked.

### Open items

- `stylized_facts/README.md` known limits: for the owner to fill in.
- `early_warning/README.md` goal paragraph: for the owner to write.
- `REPORT.md`'s run commands still say to run from the repo root. They now need `cd stylized_facts` first. Left unedited (rule 1).
- The `data/`, `patches/` and `ising_handover/` ignore rules aren't tied to a folder, so they would also ignore folders with those names inside `early_warning/`.
- `stylized_facts/tests/` is still ignored, so it has no `.gitkeep`.
- Nothing committed; new files need `git add`.

---

## 2026-10-22: Add CLAUDE.md

Tool: Claude Code (desktop app). Nothing committed.

### Prompts

**Prompt 1:** `/init`, the built-in command that analyzes the codebase and writes a `CLAUDE.md` for future Claude Code sessions (commands, high-level architecture, important parts of the README, no generic advice).

### Steps

1. Checked for existing agent instruction files (`CLAUDE.md`, `.cursorrules`, `.cursor/`, `.github/copilot-instructions.md`, Codex and Gemini configs). None exist.
2. Read the outline of `stylized_facts/src/ising_market/model.py`, the calibration and deployment code, the docstrings of `make_figures.py` and `compare_return_models.py`, and the layout, setup, reproduction, calibration and known-limits sections of `stylized_facts/REPORT.md`.
3. Wrote `CLAUDE.md` at the repo root: working rules (log every session, never commit, leave `DECISIONS.md` and placeholders alone), the two-project layout and the independence rule, commands, the data flow between scripts, the model's architecture, and gotchas.
4. Checked two claims against the code: `uv run ruff check .` runs, and `garch_x_breadth.py` and `compare_return_models.py` don't import `ising_market`.

### Decisions

| ID | Decision | Alternatives considered | Why | Decided by |
|---|---|---|---|---|
| D1 | Put the session-logging and no-commit rules at the top of `CLAUDE.md`. | Rely only on Claude's per-user memory. | `CLAUDE.md` is in the repo, so the rules apply to any Claude Code session on any machine. | Claude |
| D2 | Tell future sessions to run script checks with `--out` pointed at a scratch folder and to prefer `--replot`. | List the full reproduction commands from `REPORT.md`. | `results/` is committed and full runs overwrite it; some runs take hours or download from Yahoo. | Claude |
| D3 | Note the existing ruff errors and say not to mass-fix them unasked. | Fix them; or leave them out. | Fixing would edit moved files, against the reorganization's rules. | Claude |
| D4 | Write a single-test command with an explicit path. | Use bare `uv run pytest`. | `testpaths = ["tests"]` points at a root `tests/` that no longer exists. | Claude |

### Verification

| Check | Result |
|---|---|
| `uv run ruff check .` | Runs; reports 45 existing errors (5 auto-fixable). Nothing fixed. |
| `grep ising_market` in `garch_x_breadth.py`, `compare_return_models.py` | 0 matches in both, matching the data-flow notes |

### Open items

- The pytest `testpaths` setting in `pyproject.toml` points at a root `tests/` that doesn't exist. It could be changed to `["early_warning/tests"]` once early-warning tests exist.
- 45 existing ruff errors in `stylized_facts/`.
- `CLAUDE.md` is untracked; it needs `git add`.

---

## 2026-10-31: Explain why kurtosis stays at 1.3–2.5

Tool: Claude Code (cloud session linked to this computer). Nothing committed.

### Prompts

**Prompt 1:** Review the codebase, particularly `stylized_facts/`, and explain in one pass why the model's kurtosis stayed at 1.3–2.5 instead of producing fat tails.

### Steps

1. Read `CLAUDE.md`, `PROJECT_LOG.md`, `stylized_facts/REPORT.md` (tail, Binder and feedback sections), `model.py` (`compute_return`, `_metropolis_pilot`, `_deploy_kernel`, `simulate_deployed`), `results/figures/summary.md` and `ising_handover/tests/t11_tails.py` with its log.
2. Copied `model.py` and `J_2005_2007.npy`, `J_us100_2005_2024.npy` to a scratch folder outside the repo and reran the repo's own numba kernels there: equilibrium kurtosis of m against T/λ on both networks, the largest standardised |r| in deployed runs at G = 0, 0.5, 1.0, and a scale-mixing decomposition at G = 0.5, 1.0, 1.25.
3. Wrote the exchange to `CHAT.md` (new file) per the project instructions.

### Findings (all from the reruns in step 2)

| Check | Result |
|---|---|
| Equilibrium kurtosis of m, 29 stocks, T/λ 0.60 → 4.0 | 1.17, 1.42, 1.64, 1.89, 2.12, 2.46, 2.78, 2.88 |
| Same, 100 stocks, T/λ 0.75 → 4.0 | 1.08, 1.26 (0.84), 1.74, 2.26, 2.74, 2.93, 2.97; the 0.60λ run (3.74) is stuck in one well |
| Largest standardised \|r\|, 29 stocks, T0 = 0.936λ, k = 18 | 2.30 (G = 0), 2.30 (G = 0.5), 2.36 (G = 1.0); hard cap 1/σ_m = 2.32 |
| Scale-mixing factor E[s⁴]/E[s²]² | 1.03 (G = 0.5), 1.28 (G = 1.0), 1.63 (G = 1.25) |

Not rerun: the full calibration and the 100-stock deployed model (k = 248). The 100-stock numbers are equilibrium only.

### Files changed

- `CHAT.md` (new)
- `PROJECT_LOG.md` (this entry)

No code, test, threshold or result file was edited.

---

## 2026-10-31: Second pass — state and prove the kurtosis cap

Tool: Claude Code (cloud session linked to this computer). Nothing committed.

### Prompts

**Prompt 1:** Now conduct a second pass: state the mechanism precisely and thoroughly explain why that mechanism caps the fourth moment.

### Steps

1. Derived the cap from the Lee–Yang theorem: for a zero-field ferromagnet (J ≥ 0, h = 0) the characteristic function of M has only real zeros, giving kurt(M) = 3 − 6/N_eff + 4/U ≤ 3 − 2/N.
2. Tested it in a scratch folder outside the repo, using copies of `model.py` and the saved J matrices:
   - exact enumeration of all 2^N states on 12- and 13-spin sub-blocks of the 29-stock J, comparing exact kurtosis with the formula from the zeros;
   - an all-to-all ferromagnet in the ordered limit;
   - controls that break the hypotheses: random-sign couplings, and a heavy-tailed common random field;
   - the variance range of m across the calibrated window, for both networks;
   - the deployed 29-stock model at G = 0.5, 1.0, 1.25 against the mixture bound (3 − 2/N)·E[σ⁴]/E[σ²]².
3. Appended the exchange to `CHAT.md`.

### Findings (all from the reruns in step 2)

| Check | Result |
|---|---|
| Exact kurtosis vs formula from zeros, N = 12, 13, T/λ 0.6–5.0 | Agree to 4 decimals; cap 3 − 2/N never exceeded (margin ≥ 0.07); roots on unit circle to ≤ 8e-6 |
| All-to-all ferromagnet, N = 12, T = 3 | kurtosis 1.0008, N_eff = 2.96 |
| Random-sign couplings, N = 13, 160 draws | max kurtosis 3.27 (cap 2.846), so the cap needs J ≥ 0 |
| Heavy-tailed common field, N = 13, T/λ 1–10 | kurtosis stays at or below the h = 0 value; no route to fat tails found |
| var(m) range, 29 stocks 0.60–1.30λ | 0.493 → 0.094 (5.2×); max mixture factor 1.86 |
| var(m) range, 100 stocks 0.75–1.30λ | 0.524 → 0.038 (13.8×); max mixture factor 3.97 |
| Deployed 29 stocks, G = 0.5 / 1.0 / 1.25 | kurtosis 1.90 / 2.08 / 2.46; factor 1.027 / 1.305 / 1.652; bound 3.01 / 3.83 / 4.84 |

### Corrections to the earlier entry

- Bounded support gives only kurt ≤ 1/σ_m² (5.4 at the selected 29-stock row), so it explains the maximum |z| but is not the cap on the fourth moment.
- The suggested exogenous news-field route did not raise kurtosis in the N = 13 test and is withdrawn.

### Not done

- No proof for the deployed chain with time-varying T (only the quasi-equilibrium mixture bound plus numerical checks).
- Exact enumeration only up to N = 13; the field-compression explanation (GHS) is a hypothesis.
- Theorem citations (Lee–Yang, Lebowitz, Newman) are from memory.

### Files changed

- `CHAT.md` (second exchange appended)
- `PROJECT_LOG.md` (this entry)

No code, test, threshold or result file was edited.

---

## 2026-10-31: Feature table for `stylized_facts/README.md`

Tool: Claude Code (desktop app). Nothing committed.

### Prompt

> Review stylized_facts/ and determine the meaning and usage of each feature. Create a table explaining each feature and append this to stylized_facts/README.md.

### Steps

1. Read `stylized_facts/README.md`, each script's docstring and `argparse` options, every function and class docstring in `src/ising_market/model.py` (listed with a small `ast` script), the legacy `FinancialIsingModel` methods, `model.py`'s `__main__` block, and the `MODELS` table in `compare_return_models.py`.
2. Traced where the frozen data files come from (grep for `2005_2007`, `rets_big`, `J_big`).
3. Appended a `## Features` section to `stylized_facts/README.md`: five tables (data, model core, calibration, simulation and measurement, analysis scripts), a legacy-code table, and a short list of gaps found. Each row gives where the feature lives, what it means, how to use it (flags or call) and what it writes. No results or findings are stated; the section points to `REPORT.md` for those.
4. Checked three claims against the code (see Verification).

### Commands run

| Command | Output |
|---|---|
| `grep -n add_argument -A1 scripts/*.py` | Flags and defaults for all six scripts (`calibrate_real.py` has none) |
| `ast` listing of `model.py` | 1 class (19 methods), 17 functions with signatures and docstrings |
| `grep -rn -e 2005_2007 -e rets_big -e J_big scripts src REPORT.md ising_handover` | Only `calibrate_real.py:76–77` writes `rets_big`/`J_big`; only `make_figures.py:972–973` mentions `2005_2007` (as defaults) |
| `grep -n target_vol model.py` | Only in the signature, docstring and one `print` (line 846) |
| `grep -n "args\.(size\|alpha\|mode\|kappa)" model.py` | No matches: the CLI flags are never read |
| `grep -n "ceil\|eps_ucb\|idxmin" model.py` | k = ⌈3·p75(τ_int)⌉ (line 666); winner = `idxmin` of ε + 2 SE among survivors (lines 775, 798) |

### Decisions

| ID | Decision | Alternatives considered | Why | Decided by |
|---|---|---|---|---|
| D1 | Read "feature" as each user-facing capability of the code (scripts, public functions, model parameters), grouped by pipeline stage. | One row per function including private helpers; or one row per stylized fact measured. | Matches "meaning and usage": what it does and how to run it. Private helpers are folded into the row of the feature they serve. | Claude |
| D2 | Describe what the code does, never what it found. | Include headline numbers from `REPORT.md`. | CLAUDE.md: don't state results the code hasn't produced in this session; `REPORT.md` already holds them. | Claude |
| D3 | List the data-file mismatch as a gap instead of guessing its cause. | Assume `rets_2005_2007.pkl` came from `calibrate_real.py`. | The code shows `calibrate_real.py` writes different file names and a much longer ticker list. | Claude |

### Files changed

- `stylized_facts/README.md` (appended `## Features`; the status line and its placeholder are unchanged)
- `PROJECT_LOG.md` (this entry)

### Open items

- Where `data/rets_2005_2007.pkl` and `data/J_2005_2007.npy` came from is unknown. `REPORT.md` says `calibrate_real.py` freezes the data, but its code writes `rets_big.pkl` and `J_big.npy`.
- `stylized_facts/README.md` known limits: still for the owner to fill in.

---

## 2026-10-31: Add symbols, settings and parameters to `stylized_facts/README.md`

Tool: Claude Code (desktop app). Nothing committed.

### Prompt

> Features are missing, for instance epsilon should be explained, any non-trivial feature or symbol that has physical/model meaning should be included in this README.md. Review the repo again and determine which additional features impact the model's behaviour and update the README.md to include these features.

### Steps

1. Read `model.py` lines 499–830 in full: `fetch_market_data`, `build_empirical_J`, `_metropolis_pilot`, `_run_pilot`, `_acf`, the run-quality constants, `thinned_stats`, `compute_run_stats`, `aggregate_by_T0` (including the ε regression) and `select_T0`.
2. Read `compare_return_models.py` lines 60–566: run-length settings, moment lists, the `MODELS` grids, all three spin kernels, `Context.sigma0`, `simulate`, `grid_points`, the GARCH fit, `hill`, `moments`, `block_bootstrap`, `j_stat`, `calibrate`, `evaluate`, `coverage`, `scaling_checks`.
3. Read from `make_figures.py`: `FULL`/`QUICK`, `GAINS`, `classify` (regimes), `network_data` (noise edge), `run_calibrations`, `consensus_row`, `run_deployment`. Read from `garch_x_breadth.py`: `MODELS`, `TESTS`, `panel_inputs`, `newey_west_t`, `out_of_sample`.
4. Inserted five new sections into `stylized_facts/README.md`, before *Gaps found*:
   - *Symbols and quantities: network and dynamics* (21 rows)
   - *ε: the elasticity of volatility with respect to temperature* (definition, measurement, sign, link to the loop gain G, use in selection)
   - *Calibration statistics* (11 rows: σ_m, R, q, τ_int, converged, n_eff, z, s, AC1, equilibrated, regime)
   - *Settings that change the model's behaviour* (20 rows, with defaults and effects)
   - *Return-model comparison: parameters and statistics* (23 rows) and *Breadth test: symbols* (14 rows)
5. Corrected the earlier comparison row: the code has six spin-model variants (including `cluster_stable`), not five.
6. Removed five phrases from the draft that went beyond the code: a typical Hill index for real equity, how a affects tails, a loose description of Bornholdt's term, a claim about pilot length, and which figures use regime shading.

### Commands run

| Command | Output |
|---|---|
| `sed -n 499,830p src/ising_market/model.py` | Calibration internals (source of the ε, Sokal, z and selection rows) |
| `sed -n 60,566p scripts/compare_return_models.py` (in parts) | Settings, grids, kernels, moments and scoring |
| `grep` in `make_figures.py` for `GAINS`, `FULL`, `classify`, `mp_edge`, `consensus_row` | `GAINS = (0.0 … 1.5)`; `FULL` 50,000 / 10,000 / 10,000 days / 4 runs; noise edge `(1 + √(N/T))²` |
| `sed`/`grep` in `garch_x_breadth.py` | Five GARCH variants, five tests, D = (1.4826·MAD)², Newey–West lag ⌊4(n/100)^(2/9)⌋ |
| `grep HILL_CAP\|LONG_TARGET\|BLOCK_MIN` | 30.0, 2,500, 50: match the README |
| `awk` column count per README section | Every table has the same number of columns in all its rows |

### Decisions

| ID | Decision | Alternatives considered | Why | Decided by |
|---|---|---|---|---|
| D1 | Give ε its own subsection, with the loop-gain reasoning written out. | One table row like the other symbols. | ε controls which T0 is chosen and how every feedback strength is set (α = G/\|ε\|); one row can't hold that. | Claude (prompted by the owner's example) |
| D2 | Separate symbols (what a quantity is) from settings (the default values that change behaviour). | One combined table. | Settings carry defaults and effects; symbols carry definitions and meanings. | Claude |
| D3 | Include the comparison and breadth-test parameters. | Only the core model. | They change what each model does and how it is judged. | Claude |
| D4 | Only state what the code defines or computes; leave out typical market values and interpretations not in the code. | Keep explanatory context from general knowledge. | CLAUDE.md: don't claim results or findings the code hasn't produced. | Claude |

### Files changed

- `stylized_facts/README.md` (5 sections inserted; 1 row corrected; status line and placeholder unchanged)
- `PROJECT_LOG.md` (this entry)

### Open items

- The name `fig3_griffiths` isn't explained in the code. The README quotes the code's description instead of guessing.
- The feedback's σ is computed from m in `model.py` but from daily returns in `compare_return_models.py`. The two are the same only for the `level` mapping. The README notes this; whether it was intended isn't recorded.

---

## 2026-11-01: Loose pytest tests for the stylized_facts model

Tool: Claude Code (desktop app). Nothing committed.

### Context (owner's note)

This section is a practice section with learning how to be specific in prompt. Lack of tests was a known open area so I will address this is two separate ways. First, I will prompt a simply "add tests ..." without any specification, this will be in a separate file. The next prompt will be more specific and utilize plan mode to identify weakpoints in the code before prompting for specific tests.

### Prompt

> add some pytest tests for the stylized facts model in stylized_facts/tests/loose_tests.py

### Steps

1. Read `model.py` lines 1–22 (imports, `results/figures` side effect) and 515–968 (`build_empirical_J` through `stylised_facts`).
2. Wrote `stylized_facts/tests/loose_tests.py`: 20 tests on synthetic, seeded inputs (a 10-spin uniform ferromagnet and two blocks of correlated fake returns). No downloads, no frozen data.
3. Ran the tests and ruff.

### What the tests cover

| Function | Checks |
|---|---|
| `build_empirical_J` | shape, symmetry, zero diagonal, mean non-zero coupling = 0.1, threshold keeps C > 0.3 and drops cross-block edges |
| `_acf` | lag 0 = 1; matches `np.correlate` |
| `mean_se`, `thinned_stats` | hand values; white-noise AC1 ≈ 0; NaN std when the series is shorter than the window |
| `compute_run_stats` | Gaussian noise: R ≈ 3, τ_int ≈ 0.5, converged; AR(1) φ = 0.9: τ_int ≈ 9.5 (±25%) |
| `_run_pilot` | same seed → same output; bad `start` raises; 0.2λ stays ordered, 5λ disordered |
| `select_T0` | picks the most negative ε_ucb; rejects ε > 0; no survivors → `None`; missing columns → `KeyError` |
| `simulate_deployed` | same seed → same output; r = κ·m; α = 0 keeps T = T0 with no clipping; T stays inside `T_clip` |
| `stylised_facts` | Gaussian: kurtosis ≈ 3, AC ≈ 0; Student-t(4): kurtosis > 4, fitted dof in 2.5–6 |

Not covered: `aggregate_by_T0`, `calibrate_parameters`, the legacy `FinancialIsingModel` class, plotting, and the scripts.

### Commands run

| Command | Output |
|---|---|
| `uv run python -c "import pytest, ising_market.model"` | pytest 9.1.1; package imports from `stylized_facts/src` |
| `uv run pytest stylized_facts/tests/loose_tests.py -q` | 20 passed in 2.57 s |
| `uv run ruff check stylized_facts/tests/loose_tests.py` | All checks passed |

### Decisions

| ID | Decision | Why | Decided by |
|---|---|---|---|
| D1 | Import `model.py` inside a temp directory (module fixture). | Importing it creates `results/figures/` in the working directory. | Claude |
| D2 | Synthetic inputs only, small N and short runs. | Fast (< 3 s), seeded, no network or git-ignored data needed. | Claude |

### Files changed

- `stylized_facts/tests/loose_tests.py` (new)
- `PROJECT_LOG.md` (this entry)

### Open items

- `stylized_facts/tests/` is git-ignored (`.gitignore` line 19), so the new file won't show in `git status` or be committed unless that rule changes.
- `loose_tests.py` doesn't match pytest's `test_*.py` pattern and the root `testpaths = ["tests"]` doesn't point at it; it only runs when its path is passed explicitly.

## 2026-11-01: Review of stylized_facts/

### Prompt

Review stylized_facts/ and identify breaking points, edge cases, known comparisons (statistical functions with known solutions) and dependency requirements, in the code and in the broader model concept. Ignore tests/test_loose.py.

### Steps

1. Read `src/ising_market/model.py` in full, all six scripts (the statistics and kernel parts of `compare_return_models.py`, `make_figures.py` and `garch_x_breadth.py`), `pyproject.toml`, `uv.lock` and REPORT.md's "Known limitations".
2. Wrote the findings as a plan, which was approved, then saved them as `stylized_facts/REVIEW.md`.

### Commands run (all read-only)

| Command | Output |
|---|---|
| `git ls-files stylized_facts`, `wc -l` | 6 scripts, `model.py` 1,143 lines |
| `uv pip list` | numpy 2.5.3, numba 0.67.0, pandas 3.0.6, scipy 1.18.1, matplotlib 3.11.2, yfinance 1.7.0 |
| `grep strict=True` | `zip(..., strict=True)` in three scripts, so Python ≥ 3.10 is needed despite `requires-python = ">=3.9"` |
| `head data/freeze_us100_2005_2024.txt` | 0 isolated stocks at threshold 0.3, 6 at 0.5, 36 at 0.6 |

### Findings (summary; details in stylized_facts/REVIEW.md)

- Silent errors: the equilibration check passes vacuously with one seed per start; `consensus_row` uses σ0 and ε measured at each seed's own k with the median k; J's diagonal and symmetry are never checked; isolated nodes flip on every attempt.
- Crashes: J with no edges (λ = 0), `T0=None` passed on to `simulate_deployed`, short pilots, τ_int ≤ 0 giving thinning k ≤ 0, degenerate ε fits, short series in `moments`/`hill`/`block_bootstrap`.
- Known comparisons listed for the kernels (J = 0, exact enumeration, Curie–Weiss, Onsager, 1D ring, pilot vs deploy bit-identity at α = 0) and the statistics (ACF, τ_int, Binder, kurtosis, Hill, GARCH, Newey–West, Marchenko–Pastur).
- Dependencies: wrong `requires-python`, pandas 3 vs pickled DataFrames, numba–numpy coupling, yfinance imported by the package core.

None of these were confirmed by running code.

### Files changed

- `stylized_facts/REVIEW.md` (new)
- `PROJECT_LOG.md` (this entry)

### Open items

- Turn section C of REVIEW.md into tests (`stylized_facts/tests/test_known_solutions.py`) and confirm or rule out the section A items.

## 2026-11-01: pytest tests from stylized_facts/REVIEW.md

### Prompt

Using stylized_facts/REVIEW.md, write pytest functions into stylized_facts/tests/. Include the tests detailed in REVIEW.md, plus coverage of the magnetization range and calibration convergence to a known example. Tests for REVIEW items that currently fail should still be written, as grounding for future model fixes.

### Steps

1. Wrote `conftest.py` (imports model.py from a temp folder, loads the scripts by path) and `_helpers.py` (exact references: enumeration, Curie–Weiss, ring, Onsager, AR(1)).
2. Wrote four test files and ran each one. For every xfail, ran `--runxfail` to check it fails for the reason REVIEW.md gives.
3. Fixed problems in the tests themselves (none in the model):
   - `test_converged_means_tau_below_n_over_300`: at n = 20,000 the windowed τ estimate is biased low (64–107 for a true 99.5), so the "not converged" case moved to n = 10,000, where the limit is 33.
   - Kurtosis tests: `stylised_facts` now runs on 100k points with a 10% tolerance instead of 1M points with 5% (t.fit took about 38 s). `moments` is still checked on 1M points.
   - A8 no-edges xfail: pinned to AssertionError, since a regex mismatch raises that, not Failed.
   - A8 one-stock: the test passed unexpectedly, so the xfail was removed (REVIEW was wrong on this point).
   - A17: the first assertion (SE > 0) was too weak. SE(a) collapses to about 0 at the bound, compared with about 0.014 away from it, so the threshold is now SE > 1e-4.
   - Ruff sorted `tomllib` as third-party because `requires-python` says 3.9 (D1), so it is now imported inside the function.
4. Added a "Test status" section to REVIEW.md.

### Commands run

| Command | Output |
|---|---|
| `uv run pytest stylized_facts/tests -q` | 97 passed, 35 xfailed in 13 s (includes test_loose.py) |
| `uv run pytest stylized_facts/tests -q --runxfail` (per file) | every xfail fails with the expected message |
| `uv run ruff check stylized_facts/tests --exclude stylized_facts/tests/test_loose.py` | All checks passed |
| Curie–Weiss calibration (N = 29, seed 42) | T0/λ = 0.839, k = 52, ε = −1.66 ± 0.08 (exact −1.61), σ0 = 0.621 (exact 0.619) |

### Decisions

| ID | Decision | Why | Decided by |
|---|---|---|---|
| D1 | Failing REVIEW items are `xfail(strict=True)` with a pinned `raises=`. | Suite stays green; a fix flips the test to XPASS; a test bug can't hide behind the marker. | Claude |
| D2 | Statistical tolerances are 5 SE of independent seeded run means plus a small floor. | Seeded and deterministic, with an honest margin. | Claude |
| D3 | A7, A23 and B9 were not tested. | No defined target behaviour, or not observable on one machine or from outputs. | Claude |

### Files changed

- `stylized_facts/tests/conftest.py`, `_helpers.py`, `test_spin_known.py`, `test_stats_known.py`, `test_calibration.py`, `test_edge_cases.py` (new)
- `stylized_facts/REVIEW.md` (Test status section added)
- `PROJECT_LOG.md` (this entry)

### Open items

- The root `testpaths = ["tests"]` still doesn't point here (D6), so pass `stylized_facts/tests` explicitly.
- `conftest.py` is shared with `test_loose.py`. It defines only new fixture names (`im`, `crm`, `mf`, `gx`, `kuf`), and test_loose.py still passes.
