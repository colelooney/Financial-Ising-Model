# Early-warning signals for regime flips: Phase 1 spec

Status: DRAFT. Owner: Cole. Date: YYYY-MM-DD.
Scope: the simulation lab only (see Out of scope).

## 1. Question
*One sentence, testable, answerable by simulation alone.
Format: "In the Ising market model, can [indicator type] computed from [observable]
distinguish windows before a [transition type] flip from matched null windows,
and how does that depend on [driver]?"*

## 2. Hypotheses in scope
- The financial Ising Model produces noise-driven tunnelling transitions at fixed T, indicators cannot predict noise-driven flips or shocks. A result of AUC <= 0.55 with 95% confidence will support this..
- A slow drift in the news field h can produce a phase transitions in which the current state dissapears, Indicators can predict these transitions but performance drops as drift slows, expect variance AUC to decrease as drift slows.

## 3. The system under test
- Network 753 trading days; J keeps 206 of 406 pairs (50.7%) and λ_max(J) = 1.814. J and Lambbda mimic the model determined in /stylized_facts/. The mean pairwise correlation is 0.32, so the 0.3 cut-off sits right at the typical correlation.
- Model code: Code will be reconstructed to maximise efficiency and simplicity. It will be similar the code in /stylized_facts/ however it will only maintain features relevent to the early warning tests.
- Observable the indicators see: *aggregate m, sector magnetisations, something else?*
- Observable the target is defined on: *must differ from the one above, or say why not.*

## 4. Transition types (generators)
For each type: *how it is produced, what parameter is driven, the range, and the rate(s).*
- Noise-driven (fixed T, h = 0):
- Drift to a fold (h ramped against the state):
- Approach to criticality (T lowered through the crossover at h = 0):
- Shock (step in h), used as the leak test:
- Feedback-driven (deployment run): *in or out of Phase 1?*

## 5. Defining a flip
- Flip = *state the rule, including any hysteresis and the threshold.*
- Exit time t_exit = *define precisely.*
- Event window = *length, and how far before t_exit it ends (the lead time).*
- Null window = *same length and temperature; what must be true about the next X sweeps.*
- How many events and null windows per scenario: *numbers, and why enough.*

## 6. Indicators
For each: *name, formula in one line, window length, uses data up to time t only.*
- Variance:
- Lag-1 autocorrelation:
- Level baseline (e.g. distance of m from the barrier, or drawdown):
- Trend vs level form: *which one(s), registered now.*
- Any others: *only if justified here.*

## 7. Scoring
- Primary metric: *e.g. ROC-AUC, event vs null.*
- Net-of-baseline method: *how the indicator is judged after the level baseline.*
- Uncertainty: *how many seeds, what interval, how reported.*
- Multiple-testing rule: *the full list of configurations to be tried, fixed before looking.*

## 8. Pass and fail criteria (set before any results)
- Leak test (shock scenario): passes if AUC is within *[band]*. If outside, assume a leak and stop.
- Control (no approaching transition): passes if AUC is within *[band]*.
- H1 supported if: *indicator X adds at least [amount] over the baseline for drift rates up to [rate].*
- H1 not supported if: *[condition].*
- H2 supported if: *[condition].*
- Result is uninformative if: *[e.g. too few events, non-convergent runs].*

## 9. Verification plan
*Known-answer tests, same-seed reproducibility, look-ahead test, deliberate-break check.
List each check and which section it protects.*

## 10. Reproducibility
- Seeds: *how chosen and recorded.*
- Config files: *where they live, one per run.*
- Results layout: *results/<date>_<name>/ holding output and a copy of the config.*

## 11. Out of scope for Phase 1
- H3 (network-resolved indicators):
- H4 (ML detector) and real APAC data:
- *Anything else you will not touch, and why.*

## 12. Done when
*The condition that ends the time-box, in one paragraph. For example:
the warnability map exists, section 8 has been evaluated, and the write-up states
what is and is not supported.*

## 13. Known risks and open questions
*Things you are unsure about. Leave honest blanks; the interview should attack these.*