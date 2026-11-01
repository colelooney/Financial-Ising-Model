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
