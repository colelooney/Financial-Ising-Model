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
