# Financial Ising Model

Two independent projects sharing one uv environment (`pyproject.toml`, `uv.lock` at the root).

### Note:
The main learning objective for this project is how to effectively use AI Agents, such as claude code, in a research context. the stylized_facts section is an earlier step of this project and thus is a bit messier. Prompts and decisions for the early_warning section and later changes to stylized_facts section are all documented to provide a cleaner reasoning trail in the project.

Claude Code Updates are all documented in PROJECT_LOG.md. Each entry has:
- **Prompts**: the requests as given (long ones quoted in full).
- **Steps**: what was done, in order.
- **Decisions**: choices made, the options considered, and who made them.
- **Verification**: what was run and what it showed.
- **Open items**: anything left undone or uncertain.

General AI prompts, including for discussion and review, can be found in PROJECT_LOG.md and separated in CHAT.md.

**[`stylized_facts/`](stylized_facts/)**: reproducing stylized facts of financial returns with the financial Ising model. Status: paused. See [its README](stylized_facts/README.md).

**[`early_warning/`](early_warning/)**: early warning signals in the financial Ising model. Status: not started; goal to be written. It does not depend on `stylized_facts/`.

Every working session is recorded in [PROJECT_LOG.md](PROJECT_LOG.md): prompts, steps, decisions and checks.

## Module 1 - Task Specification
This module was learning how to construct Claude and Claude Code prompts with these guidelines in mind:
- State what's known and unknown separately. Don't let Claude infer your data availability, budget, or constraints — say them, or it will guess and you won't know it guessed.
- Force assumption-flagging. Explicitly instruct: "flag every assumption you make instead of picking one silently." This is the exact discipline you already wrote into the Kalshi engine's scope — make it a reusable habit, not a one-off.
- Give the shape of a good and bad answer. One example of the output format you want (and one of what you don't want) does more than a paragraph of adjectives.
- Separate instructions from data. Wrap pasted code, data, or context in clear delimiters so Claude doesn't conflate your instructions with the material it's operating on.

Given that at this stage pytest's for the calibration pipeline were unwritten, they were used as a lab exercise for practice.

Two stages were compared: loose prompt and specified prompt

The loose prompt, "add tests ...", with little specification resulted in ```stylized_facts/tests/test_loose.py``` which generated 20 tests on synthetic invariants with zero closed-form grounding and zero coverage of calibration behavior and known failure modes.

The spec'd version, utilizing a plan mode diagnosis followed by specificed tests, resulted in 132 tests across four files in ```stylized_facts/tests/```, testing physics ground truths, 35 explicitly tracked known-failing behaviours, and statistical truths. This spec'd version provided a much more comprehensive testing environment with verifiable background and allows for future test-based programming to fix the known-failing behaviours rather than just ignoring them.
