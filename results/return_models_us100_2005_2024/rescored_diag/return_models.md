# Return models compared

Generated 2026-10-12 09:32:39 in 784.8 min. Target: equal-weight index of the 100 stocks, 2005-01-04 to 2024-12-31 (5032 days). Spin models run on the calibrated network at T0 = 0.839 λ_max (ε = -3.18) where they use it.

Calibration: grid search minimising J = (m − m*)' W (m − m*) over the targeted moments, with W diagonal: each moment weighted by its own bootstrap variance. The bootstrap uses moving blocks of 251 days.

Re-scored from a run calibrated with the full weighting: the parameters were chosen under that weighting, J and p are recomputed. p is the share of model samples of the target's length whose J around the model's own long-run moments exceeds the target's J. MCR is the share of those samples with every targeted moment inside the target's 95% interval. The last J column uses the other weighting, for comparison.

## Ranking

| rank | model | free parameters | calibrated values | J | J, single runs | p | MCR | mean T/T0 | J, full W | source |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | GARCH(1,1)-t | 4 | a = 0.13, b = 0.87, ν = 6.6 | 15.2 | – | 0.625 | 0.000 |  | 115.5 | Bollerslev (1986, 1987); fitted by maximum likelihood |
| 2 | Random couplings | 2 | A = 1.2, h = 0.1 | 174.7 | – | 0.000 | 0.000 |  | 465.9 | Krawiecki, Hołyst & Helbing (2002) |
| 3 | Change, r = Δm | 2 | α = 0, k = 1 | 183.6 | – | 0.000 | 0.000 | 1.00 | 204.6 | Market clearing against fundamentalists: Kaizoji, Bornholdt & Fujiwara (2002) |
| 4 | Bornholdt frustration | 2 | T = 0.8 λ, α_B = 0.5 λ | 185.4 | – | 0.000 | 0.000 |  | 166.8 | Bornholdt (2001); returns as in Kaizoji, Bornholdt & Fujiwara (2002) |
| 5 | Level, r = m (current) | 2 | α = 1, k = 992 | 210.6 | – | 0.000 | 0.000 | 5.42 | 111.9 | Excess demand moves the price; Cont & Bouchaud (2000), Krawiecki et al. (2002) use the same mapping |
| 6 | Cluster trading | 2 | α = 1.2, a = 0.3, k = 496 | 214.3 | – | 0.000 | 0.000 | 7.78 | 119.2 | Cont & Bouchaud (2000) activity on Fortuin-Kasteleyn clusters (combination ours) |
| 7 | Cluster trading, α ≤ 0.8 | 2 | α = 0.6, a = 0.2, k = 496 | 214.9 | – | 0.000 | 0.000 | 2.40 | 169.5 | as above, with the feedback exponent α ≤ 0.8 |
| 8 | Gaussian i.i.d. | 0 | no parameters | 225.2 | – | 0.000 | 0.000 |  | 135.0 | null model |

## Moments (long-run model values; target with bootstrap SE)

| moment | target | GARCH(1,1)-t | Random couplings | Change, r = Δm | Bornholdt frustration | Level, r = m (current) | Cluster trading | Cluster trading, α ≤ 0.8 | Gaussian i.i.d. |
|---|---|---|---|---|---|---|---|---|---|
| E|z| | 0.628 ± 0.033 | 0.590 | 0.781 | 0.776 | 0.795 | 0.796 | 0.798 | 0.792 | 0.797 |
| AC(r,1) | -0.110 ± 0.036 | 0.012 | -0.013 | -0.104 | -0.092 | -0.011 | -0.006 | -0.004 | 0.001 |
| Hill | 2.445 ± 0.440 | 2.211 | 5.646 | 5.820 | 5.199 | 5.822 | 5.875 | 6.173 | 6.058 |
| AC|r| 1 | 0.391 ± 0.072 | 0.380 | 0.248 | 0.077 | 0.008 | 0.012 | 0.004 | 0.028 | -0.010 |
| AC|r| 5 | 0.397 ± 0.071 | 0.384 | 0.011 | 0.031 | 0.002 | 0.012 | 0.006 | 0.019 | 0.000 |
| AC|r| 10 | 0.349 ± 0.067 | 0.353 | 0.003 | 0.012 | 0.000 | 0.002 | 0.009 | 0.027 | -0.004 |
| AC|r| 25 | 0.230 ± 0.057 | 0.284 | 0.008 | 0.005 | 0.000 | 0.003 | -0.003 | 0.008 | -0.000 |
| AC|r| 50 | 0.160 ± 0.046 | 0.214 | -0.002 | -0.005 | -0.001 | -0.005 | -0.001 | -0.000 | 0.009 |
| AC|r| 100 | 0.103 ± 0.050 | 0.118 | -0.001 | -0.000 | -0.001 | -0.003 | 0.003 | -0.005 | 0.001 |
| kurtosis (held out) | 18.616 ± 4.581 | 37.012 | 3.436 | 3.663 | 3.046 | 2.997 | 2.998 | 3.200 | 2.994 |
| kurtosis 5d (held out) | 13.437 ± 4.084 | 41.579 | 4.485 | 4.914 | 3.286 | 3.025 | 3.063 | 3.278 | 2.926 |
| P(|z|>3) (held out) | 0.018 ± 0.003 | 0.018 | 0.005 | 0.007 | 0.003 | 0.003 | 0.002 | 0.004 | 0.002 |
| AC(r²,1) (held out) | 0.310 ± 0.077 | 0.193 | 0.414 | 0.097 | 0.005 | 0.012 | 0.002 | 0.029 | -0.008 |

## Coverage: share of model samples inside the target's 95% interval

| moment | GARCH(1,1)-t | Random couplings | Change, r = Δm | Bornholdt frustration | Level, r = m (current) | Cluster trading | Cluster trading, α ≤ 0.8 | Gaussian i.i.d. |
|---|---|---|---|---|---|---|---|---|
| E|z| | 0.68 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC(r,1) | 0.10 | 0.03 | 1.00 | 1.00 | 0.00 | 0.00 | 0.03 | 0.03 |
| Hill | 0.90 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC|r| 1 | 0.80 | 0.53 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC|r| 5 | 0.70 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC|r| 10 | 0.70 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC|r| 25 | 0.90 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC|r| 50 | 0.68 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC|r| 100 | 0.78 | 0.23 | 0.25 | 0.30 | 0.15 | 0.28 | 0.33 | 0.30 |
| kurtosis | 0.60 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| kurtosis 5d | 0.85 | 0.07 | 0.25 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| P(|z|>3) | 0.97 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC(r²,1) | 0.93 | 0.90 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
