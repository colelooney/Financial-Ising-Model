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
