# CHAT.md

Prompt: ---
Review the codebase, particularly stylized_facts/, and explain in one pass why the model's kurtosis stayed at 1.3-2.5 instead of producing fat tails.

Response: ---
**Short answer:** the return is `r = κ·m`, where `m = Σsᵢ/N` is the net spin of only 29 (or 100) ±1 agents. That quantity is bounded and sub-Gaussian, so no calibration choice and no mild volatility feedback can give it a fat tail. The 1.3–2.5 band is the range of its kurtosis (the Binder ratio) across the temperatures where the model mixes.

**1. Bounded support.** `|m| ≤ 1`, so a standardised return can't exceed `1/σ_m`. At the selected row (29 stocks, T0 = 0.936λ) σ_m = 0.431, a cap of 2.32σ. Over 40,000 deployed days the largest |z| was 2.30 at G = 0 and 0.5, and 2.36 at G = 1. P(|z| > 3) was zero. The index's worst day is −4.5σ.

**2. The shape of m is two-humped, not peaked.** In the mixing regime the system hops between ±M wells. At 0.936λ, 26% of days have |z| < 0.5 (Gaussian: 38%), 42% sit in 1–2σ (Gaussian: 27%) and only 1.2% beyond 2σ (Gaussian: 4.6%). Kurtosis of m is pinned between 1 (pure two-point) and 3 − 2/N (independent spins: 2.93 at N = 29, 2.98 at N = 100). Rerunning `_metropolis_pilot` at α = 0 on your saved networks:

| T/λ | 0.60 | 0.75 | 0.84 | 0.94 | 1.05 | 1.30 | 2.0 | 4.0 |
|---|---|---|---|---|---|---|---|---|
| 29 stocks | 1.17 | 1.42 | 1.64 | 1.89 | 2.12 | 2.46 | 2.78 | 2.88 |
| 100 stocks | (3.74*) | 1.08 | 1.26 | 1.74 | 2.26 | 2.74 | 2.93 | 2.97 |

*The 100-stock run at 0.60λ is stuck in one well (non-ergodic), so ignore it.

The calibration's mixing window (0.60–1.30λ) therefore maps onto roughly 1.2–2.5 by construction, and a different T0 only slides you along this curve. Your 1.3 is the 100-stock calibrated point (0.839λ: 1.26); your 2.5 is the 29-stock top of the window (1.30λ: 2.46).

**3. Feedback can only help through scale mixing, and there is too little of it.** With the shape fixed, fat tails need the scale of m to swing a lot from day to day. Kurtosis ≈ conditional kurtosis × E[s⁴]/E[s²]², where s is the equilibrium σ_m at that day's T. On deployed runs that factor is 1.03 at G = 0.5 (T varies by only 7%), 1.28 at G = 1.0 and 1.63 at G = 1.25. Going from ~1.9 to the index's 18.6 would need about 10. The gain can't be pushed further because the loop is linearly unstable past G = α|ε| = 1 (α > 0.84). Beyond that T runs away upward (mean T/T0 = 1.87 at G = 1.5, per `summary.md`), which moves m toward the Gaussian paramagnet. Kurtosis only reaches 3.11 there, from drift to a hotter, more Gaussian state rather than from tails.

**4. System size, density and missing jump mechanisms.** m is a sum of 29–100 bounded variables. `REPORT.md` already notes that even N = 1,000 reaches only 7.6 with the published dynamics, and the 100-stock J keeps 87% of pairs, so it is nearly all-to-all (mean-field, no avalanches). The deployed kernel (`_deploy_kernel`: h = 0, no leverage) adds no jumps; `leverage_cascade` exists in the class but is switched off.

**Conclusion:** this is structural, not a calibration bug, which matches `REPORT.md`. With r ∝ m and a fixed small N, kurtosis can exceed 3 only through scale mixing, and the feedback loop can't supply enough of it before going unstable. Routes that change that (none tested here): decouple the return from m (e.g. a stochastic scale, or returns from flips/Δm with volume-dependent impact), an exogenous heavy-tailed news field h_t, or a leverage cascade / random-field avalanche on a larger, sparser network.

**What I checked:** I reran the repo's own kernels (`_metropolis_pilot`, `_deploy_kernel`) on the saved J matrices with fresh seeds, outside the repo. I did not rerun the full calibration or the 100-stock deployed model (k = 248), so the 100-stock numbers are equilibrium only.

---

Prompt: ---
Now conduct a second pass: state the mechanism precisely and thoroughly explain why that mechanism caps the fourth moment.

Response: ---
**The mechanism, stated precisely.** On any given day the return is `κ·m`, where `m = M/N` is the magnetisation of an Ising system with three properties:

- every coupling is ≥ 0 (`build_empirical_J` keeps only correlations > 0.3 and zeroes the diagonal);
- the field is zero (`h = 0` in `_deploy_kernel`);
- the Metropolis dynamics has the Boltzmann law at that day's T as its stationary distribution.

For every such system the Lee–Yang theorem forces the characteristic function of M to have only real zeros. That fixes the sign of the fourth cumulant at every T and every N:

    kurt(M) ≤ 3 − 2/N,   with equality only at J = 0 or T = ∞.

So a single day's return law is capped below the Gaussian value. The temperature feedback can only raise the pooled kurtosis by mixing days of different variance, which multiplies the cap by E[σ⁴]/E[σ²]². Inside the calibrated window that factor is tightly limited.

**Corrections to my first pass.**
- I led with bounded support (|m| ≤ 1). That explains why max |z| is 2.3, but it is not what caps the fourth moment. Support alone gives only kurt ≤ 1/σ_m², which is 5.4 at the selected 29-stock row, well above anything observed.
- I blamed a CLT-style small-N effect. The cap holds at any N; larger N only moves it toward 3 from below.
- I listed an exogenous heavy-tailed news field as a possible route to fat tails. Section 4 shows it does not work in a test.

**1. From the zeros to the cumulants.**
- Write φ(t) = E[e^{itM}] = Z(it)/Z(0), where Z(h) = Σ_s exp(½ΣJ_ij s_i s_j / T + hΣs_i).
- With w = e^{2it}, φ is proportional to e^{−iNt}·P(w), where P(w) = Σ_j Prob(M = 2j − N)·w^j has degree N.
- Lee–Yang says every root of P lies on |w| = 1. The zero-field symmetry m → −m makes the roots come in conjugate pairs.
- Each root w_k = e^{iθ_k} contributes a factor `cos t − b_k sin t`, with b_k = cot(θ_k/2).
- Define u_k = 1 + b_k² = 1/sin²(θ_k/2), which is ≥ 1. Writing the factor as cos(t+β)/cos β with b = tan β, its cumulants are κ2 = u and κ4 = −2u(3u − 2).
- Cumulants add over factors and the odd ones cancel in pairs, so:

      Var(M) = Σ u_k,    κ4(M) = −6 Σ u_k² + 4 Σ u_k

- Let U = Σu_k and Q = Σu_k². Then U ≥ N because each u_k ≥ 1, and Q ≥ U²/N by Cauchy–Schwarz. Define N_eff = U²/Q ≤ N, which gives:

      kurt = 3 − 6/N_eff + 4/U ≤ 3 − 6/N + 4/N = 3 − 2/N

The sign comes from the structure. Each zero contributes a negative fourth cumulant, −2u(3u−2) < 0 for u ≥ 1. A Gaussian has no zeros at all, so positive excess kurtosis would need zeros off the real t axis (equivalently, off the unit circle in w). That is exactly what Lee–Yang forbids. This is the same content as the Lebowitz inequality (Ursell function u4 ≤ 0), but the zero picture gives the tight constant 2/N.

**2. What N_eff means.** Roots piled at w = −1 (u = 1) are independent spins: N_eff = N and kurt = 3 − 2/N. Roots spread round the circle are macroscopic order: N_eff → 3 and kurt → 1, which is the two-humped ±M law. Exact enumeration on 13-spin sub-blocks of your real 29-stock J (T in units of the block's λ):

| T/λ | 0.6 | 1.0 | 2.0 | 5.0 |
|---|---|---|---|---|
| exact kurtosis | 1.288 | 1.917 | 2.562 | 2.776 |
| N_eff | 3.41 | 5.10 | 9.63 | 12.45 |

The cap is 2.846. The formula from the zeros reproduces the exact kurtosis to four decimals at every T for N = 12 and 13. Roots sit on the unit circle to within 8×10⁻⁶ (round-off on near-degenerate roots). An all-to-all ferromagnet at T = 3 gives kurtosis 1.0008 and N_eff = 2.96, the ordered limit. So temperature only slides the model along the segment [1, 3 − 2/N]. Your 1.3–2.5 is the part of that segment the calibration's mixing window covers.

**3. Why the feedback cannot lift it.** With T varying day to day, the pooled law is a mixture of per-day laws. Applying the cap to each day gives

    kurt ≤ (3 − 2/N) · E[σ_T⁴] / E[σ_T²]²,

where σ_T² is the equilibrium variance of m at that day's T. The factor depends only on how much the variance of m can swing:

- **29 stocks, 0.60–1.30λ:** var(m) falls from 0.493 to 0.094, a 5.2× range. The most extreme mixture on that range, half the days at each end, gives a factor of 1.86.
- **100 stocks, 0.75–1.30λ:** the range is 0.524 to 0.038, 13.8×, so the factor is at most 3.97. (I started at 0.75λ because the 0.60λ run is non-ergodic.)
- **What the index needs:** its 18.6 needs a factor of at least 6.4 even if every day sat at the paramagnetic cap. With the actual conditional kurtosis of about 1.9, it needs roughly 10.
- **Deployed runs (29 stocks), on the realised T path:**

| G | 0.5 | 1.0 | 1.25 |
|---|---|---|---|
| factor | 1.03 | 1.31 | 1.65 |
| bound | 3.0 | 3.8 | 4.8 |
| observed kurtosis | 1.90 | 2.08 | 2.46 |

The observed values sit well inside the bound because the conditional kurtosis is about 1.9, not 2.9.

This is where |m| ≤ 1 actually matters. It limits how far σ² can swing (between 1/N and 1). Mixing stays in the window anyway, because below about 0.6λ the chain stops mixing and past G = 1 the loop is unstable.

**4. What does not cap it, and what I tested.**
- **Negative couplings break the theorem.** With random-sign couplings (N = 13, 160 draws), kurtosis reached 3.27, above the 2.85 cap.
- **A heavy-tailed random field does not help.** I mixed over a common field h (Laplace and Student-t(3)) with the same J, N = 13. Kurtosis stayed under the cap or fell. At T = 1λ it went from 1.92 to 1.41 as the field scale grew. At 4λ it went from 2.75 to 2.69–2.72. I suspect the magnetisation's concave response to h (the GHS inequality) compresses large shocks. I only tested N = 13, so treat that as a hypothesis. Either way, I withdraw the news-field route I suggested in the first pass.
- **Larger N does not lift the cap.** For this model class the ceiling is 3 at any N. `REPORT.md`'s "the limit is system size" is about the other published dynamics, which I did not examine.
- **Routes that leave the hypotheses, untested:** a return scale decoupled from m (for r = κ_t·m with independent κ_t, kurtosis multiplies by E[κ⁴]/E[κ²]², with no ceiling), frustrated or mixed-sign couplings, and non-equilibrium driven avalanches.

**Limits of what I've shown.**
- The theorem is exact for the stationary Boltzmann law at fixed T.
- For the deployed chain, where T changes daily, the mixture bound assumes quasi-equilibrium. The bound held in every run I made, but I have not proved it.
- Non-ergodic samples fall outside the theorem. The 100-stock run at 0.60λ (kurtosis 3.74) samples one symmetry-broken well.
- I'm citing Lee–Yang (1952), Lebowitz (1974) and Newman (1975) from memory. The algebra and numbers above were checked independently, and the citations don't affect them.
- The exact enumeration only goes up to N = 13.

---
