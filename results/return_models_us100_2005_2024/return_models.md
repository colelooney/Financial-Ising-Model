# Return models compared

Generated 2026-10-12 09:32:39 in 784.8 min. Target: equal-weight index of the 100 stocks, 2005-01-04 to 2024-12-31 (5032 days). Spin models run on the calibrated network at T0 = 0.839 λ_max (ε = -3.18) where they use it.

Calibration: grid search minimising J = (m − m*)' W (m − m*) over the targeted moments, with W the inverse bootstrap covariance of the target's moments (moving blocks of 251 days). p is the share of model samples of the target's length whose J around the model's own long-run moments exceeds the target's J. MCR is the share of those samples with every targeted moment inside the target's 95% interval.

## Ranking

| rank | model | free parameters | calibrated values | J | J, single runs | p | MCR | mean T/T0 | source |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Level, r = m (current) | 2 | α = 1, k = 992 | 111.9 | 82-153 | 0.000 | 0.000 | 5.42 | Excess demand moves the price; Cont & Bouchaud (2000), Krawiecki et al. (2002) use the same mapping |
| 2 | GARCH(1,1)-t | 4 | a = 0.13, b = 0.87, ν = 6.6 | 115.5 | 84-167 | 0.100 | 0.000 |  | Bollerslev (1986, 1987); fitted by maximum likelihood |
| 3 | Cluster trading | 2 | α = 1.2, a = 0.3, k = 496 | 119.2 | 86-191 | 0.150 | 0.000 | 7.78 | Cont & Bouchaud (2000) activity on Fortuin-Kasteleyn clusters (combination ours) |
| 4 | Gaussian i.i.d. | 0 | no parameters | 135.0 | 132-140 | 0.000 | 0.000 |  | null model |
| 5 | Bornholdt frustration | 2 | T = 0.8 λ, α_B = 0.5 λ | 166.8 | 164-170 | 0.200 | 0.000 |  | Bornholdt (2001); returns as in Kaizoji, Bornholdt & Fujiwara (2002) |
| 6 | Cluster trading, α ≤ 0.8 | 2 | α = 0.6, a = 0.2, k = 496 | 169.5 | 157-186 | 0.000 | 0.000 | 2.40 | as above, with the feedback kept in the range where T stays near T0 |
| 7 | Change, r = Δm | 2 | α = 0, k = 1 | 204.6 | 196-215 | 0.025 | 0.000 | 1.00 | Market clearing against fundamentalists: Kaizoji, Bornholdt & Fujiwara (2002) |
| 8 | Random couplings | 2 | A = 1.2, h = 0.1 | 465.9 | 385-589 | 0.000 | 0.000 |  | Krawiecki, Hołyst & Helbing (2002) |

## Moments (long-run model values; target with bootstrap SE)

| moment | target | Level, r = m (current) | GARCH(1,1)-t | Cluster trading | Gaussian i.i.d. | Bornholdt frustration | Cluster trading, α ≤ 0.8 | Change, r = Δm | Random couplings |
|---|---|---|---|---|---|---|---|---|---|
| E|z| | 0.628 ± 0.033 | 0.796 | 0.590 | 0.798 | 0.797 | 0.795 | 0.792 | 0.776 | 0.781 |
| AC(r,1) | -0.110 ± 0.036 | -0.011 | 0.012 | -0.006 | 0.001 | -0.092 | -0.004 | -0.104 | -0.013 |
| Hill | 2.445 ± 0.440 | 5.822 | 2.211 | 5.875 | 6.058 | 5.199 | 6.173 | 5.820 | 5.646 |
| AC|r| 1 | 0.391 ± 0.072 | 0.012 | 0.380 | 0.004 | -0.010 | 0.008 | 0.028 | 0.077 | 0.248 |
| AC|r| 5 | 0.397 ± 0.071 | 0.012 | 0.384 | 0.006 | 0.000 | 0.002 | 0.019 | 0.031 | 0.011 |
| AC|r| 10 | 0.349 ± 0.067 | 0.002 | 0.353 | 0.009 | -0.004 | 0.000 | 0.027 | 0.012 | 0.003 |
| AC|r| 25 | 0.230 ± 0.057 | 0.003 | 0.284 | -0.003 | -0.000 | 0.000 | 0.008 | 0.005 | 0.008 |
| AC|r| 50 | 0.160 ± 0.046 | -0.005 | 0.214 | -0.001 | 0.009 | -0.001 | -0.000 | -0.005 | -0.002 |
| AC|r| 100 | 0.103 ± 0.050 | -0.003 | 0.118 | 0.003 | 0.001 | -0.001 | -0.005 | -0.000 | -0.001 |
| kurtosis (held out) | 18.616 ± 4.581 | 2.997 | 37.012 | 2.998 | 2.994 | 3.046 | 3.200 | 3.663 | 3.436 |
| kurtosis 5d (held out) | 13.437 ± 4.084 | 3.025 | 41.579 | 3.063 | 2.926 | 3.286 | 3.278 | 4.914 | 4.485 |
| P(|z|>3) (held out) | 0.018 ± 0.003 | 0.003 | 0.018 | 0.002 | 0.002 | 0.003 | 0.004 | 0.007 | 0.005 |
| AC(r²,1) (held out) | 0.310 ± 0.077 | 0.012 | 0.193 | 0.002 | -0.008 | 0.005 | 0.029 | 0.097 | 0.414 |

## Coverage: share of model samples inside the target's 95% interval

| moment | Level, r = m (current) | GARCH(1,1)-t | Cluster trading | Gaussian i.i.d. | Bornholdt frustration | Cluster trading, α ≤ 0.8 | Change, r = Δm | Random couplings |
|---|---|---|---|---|---|---|---|---|
| E|z| | 0.00 | 0.68 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC(r,1) | 0.00 | 0.10 | 0.00 | 0.03 | 1.00 | 0.03 | 1.00 | 0.03 |
| Hill | 0.00 | 0.90 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC|r| 1 | 0.00 | 0.80 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.53 |
| AC|r| 5 | 0.00 | 0.70 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC|r| 10 | 0.00 | 0.70 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC|r| 25 | 0.00 | 0.90 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC|r| 50 | 0.00 | 0.68 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC|r| 100 | 0.15 | 0.78 | 0.28 | 0.30 | 0.30 | 0.33 | 0.25 | 0.23 |
| kurtosis | 0.00 | 0.60 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| kurtosis 5d | 0.00 | 0.85 | 0.00 | 0.00 | 0.00 | 0.00 | 0.25 | 0.07 |
| P(|z|>3) | 0.00 | 0.97 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| AC(r²,1) | 0.00 | 0.93 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.90 |
