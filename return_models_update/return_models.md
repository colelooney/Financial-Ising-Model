# Return models compared

Generated 2026-10-10 11:40:39 in 5.0 min. Target: equal-weight index of the 29 stocks, 2005-01-04 to 2007-12-31 (753 days). Spin models run on the calibrated network at T0 = 0.936 λ_max (ε = -1.19) where they use it.

Calibration: grid search minimising J = (m − m*)' W (m − m*) over the targeted moments, with W the inverse bootstrap covariance of the target's moments (moving blocks of 50 days). p is the share of model samples of the target's length whose J around the model's own long-run moments exceeds the target's J. MCR is the share of those samples with every targeted moment inside the target's 95% interval.

## Ranking

| rank | model | free parameters | calibrated values | J | J, single runs | p | MCR | mean T/T0 | source |
|---|---|---|---|---|---|---|---|---|---|
| 1 | GARCH(1,1)-t | 4 | a = 0.06, b = 0.92, ν = 7.4 | 25.2 | 24-28 | 0.160 | 0.030 |  | Bollerslev (1986, 1987); fitted by maximum likelihood |
| 2 | Gaussian i.i.d. | 0 | no parameters | 35.4 | 33-41 | 0.005 | 0.000 |  | null model |
| 3 | Bornholdt frustration | 2 | T = 0.8 λ, α_B = 0.25 λ | 48.9 | 51-82 | 0.055 | 0.000 |  | Bornholdt (2001); returns as in Kaizoji, Bornholdt & Fujiwara (2002) |
| 4 | Change, r = Δm | 2 | α = 0, k = 1 | 61.5 | 59-67 | 0.000 | 0.000 | 1.00 | Market clearing against fundamentalists: Kaizoji, Bornholdt & Fujiwara (2002) |
| 5 | Cluster trading, α ≤ 0.8 | 2 | α = 0, a = 0.2, k = 36 | 76.5 | 73-83 | 0.007 | 0.000 | 1.00 | as above, with the feedback kept in the range where T stays near T0 |
| 6 | Cluster trading | 2 | α = 1.6, a = 0.15, k = 36 | 103.9 | 61-199 | 0.535 | 0.000 | 3.10 | Cont & Bouchaud (2000) activity on Fortuin-Kasteleyn clusters (combination ours) |
| 7 | Random couplings | 2 | A = 1.2, h = 0.1 | 114.0 | 110-120 | 0.000 | 0.000 |  | Krawiecki, Hołyst & Helbing (2002) |
| 8 | Level, r = m (current) | 2 | α = 0.4, k = 36 | 141.4 | 127-153 | 0.050 | 0.000 | 1.00 | Excess demand moves the price; Cont & Bouchaud (2000), Krawiecki et al. (2002) use the same mapping |

## Moments (long-run model values; target with bootstrap SE)

| moment | target | GARCH(1,1)-t | Gaussian i.i.d. | Bornholdt frustration | Change, r = Δm | Cluster trading, α ≤ 0.8 | Cluster trading | Random couplings | Level, r = m (current) |
|---|---|---|---|---|---|---|---|---|---|
| E|z| | 0.739 ± 0.014 | 0.739 | 0.798 | 0.786 | 0.784 | 0.733 | 0.680 | 0.801 | 0.868 |
| AC(r,1) | -0.097 ± 0.034 | -0.004 | 0.002 | -0.123 | -0.147 | 0.000 | 0.107 | -0.000 | 0.008 |
| Hill | 3.885 ± 0.827 | 3.677 | 6.002 | 5.510 | 7.593 | 8.687 | 2.178 | 6.537 | 11.788 |
| AC|r| 1 | 0.070 ± 0.038 | 0.122 | -0.001 | 0.023 | 0.022 | 0.003 | 0.105 | 0.156 | 0.047 |
| AC|r| 5 | 0.148 ± 0.034 | 0.116 | -0.003 | 0.003 | 0.000 | -0.002 | 0.107 | 0.002 | 0.045 |
| AC|r| 10 | 0.133 ± 0.030 | 0.104 | -0.002 | -0.004 | -0.001 | 0.002 | 0.109 | -0.003 | 0.041 |
| AC|r| 25 | 0.033 ± 0.026 | 0.069 | 0.001 | -0.001 | -0.003 | 0.002 | 0.097 | -0.004 | 0.023 |
| kurtosis (held out) | 4.684 ± 0.583 | 6.436 | 2.988 | 3.138 | 3.199 | 3.500 | 11.461 | 2.971 | 1.887 |
| kurtosis 5d (held out) | 3.136 ± 0.560 | 5.720 | 2.985 | 3.205 | 2.893 | 3.114 | 15.600 | 3.674 | 2.909 |
| P(|z|>3) (held out) | 0.012 ± 0.004 | 0.012 | 0.003 | 0.004 | 0.004 | 0.001 | 0.017 | 0.002 | 0.000 |
| AC(r²,1) (held out) | 0.056 ± 0.041 | 0.110 | 0.002 | 0.031 | 0.024 | 0.003 | 0.230 | 0.260 | 0.053 |

## Coverage: share of model samples inside the target's 95% interval

| moment | GARCH(1,1)-t | Gaussian i.i.d. | Bornholdt frustration | Change, r = Δm | Cluster trading, α ≤ 0.8 | Cluster trading | Random couplings | Level, r = m (current) |
|---|---|---|---|---|---|---|---|---|
| E|z| | 0.77 | 0.00 | 0.01 | 0.01 | 1.00 | 0.09 | 0.00 | 0.00 |
| AC(r,1) | 0.21 | 0.21 | 0.83 | 0.73 | 0.21 | 0.14 | 0.24 | 0.15 |
| Hill | 0.95 | 0.28 | 0.63 | 0.37 | 0.00 | 0.52 | 0.27 | 0.00 |
| AC|r| 1 | 0.83 | 0.55 | 0.81 | 0.85 | 0.57 | 0.74 | 0.39 | 0.92 |
| AC|r| 5 | 0.53 | 0.00 | 0.00 | 0.00 | 0.00 | 0.16 | 0.01 | 0.11 |
| AC|r| 10 | 0.40 | 0.00 | 0.00 | 0.01 | 0.00 | 0.13 | 0.01 | 0.12 |
| AC|r| 25 | 0.82 | 0.80 | 0.79 | 0.78 | 0.81 | 0.76 | 0.68 | 0.93 |
| kurtosis | 0.73 | 0.00 | 0.04 | 0.04 | 0.42 | 0.28 | 0.00 | 0.00 |
| kurtosis 5d | 0.67 | 0.99 | 0.99 | 1.00 | 0.98 | 0.80 | 0.86 | 1.00 |
| P(|z|>3) | 0.96 | 0.15 | 0.29 | 0.27 | 0.02 | 0.49 | 0.10 | 0.00 |
| AC(r²,1) | 0.77 | 0.73 | 0.90 | 0.88 | 0.76 | 0.72 | 0.02 | 0.94 |
