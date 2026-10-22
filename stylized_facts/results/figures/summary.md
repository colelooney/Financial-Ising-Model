# Financial Ising model: figures summary

Generated 2026-10-10 10:59:39 from `data/rets_2005_2007.pkl` in 0.5 min. Pilots: 50,000 sweeps after 10,000 burn-in; deployment: 4 runs x 10,000 days per gain.

## Network

- 29 stocks, 753 trading days (2005-01-04 to 2007-12-31)
- J keeps correlations above 0.3: 206 of 406 pairs (50.7%)
- lambda_max(J) = 1.8141
- Largest eigenvalue of C: 10.15 (35% of the variance); 3 eigenvalues above the random-matrix edge 1.43

## Calibration by seed

| seed | winner T0/lambda | T0 | k | eps +- SE | rows passing every check (T0/lambda) |
|---|---|---|---|---|---|
| 42 | 0.936 | 1.6988 | 18 | -1.145 +- 0.033 | 0.936, 1.045 |
| 43 | 0.839 | 1.5228 | 31 | -1.245 +- 0.019 | 0.605, 0.675, 0.752, 0.839, 0.936, 1.165, 1.300 |
| 44 | 0.936 | 1.6988 | 18 | -1.210 +- 0.018 | 0.675, 0.752, 0.839, 0.936, 1.045 |

Regimes (seed 42): frozen 0.35-0.39; slow 0.44-0.54; mixing 0.60-1.30

## Recommended row (survives in the most seeds)

- T0 = 1.6988 = 0.936 lambda_max, passing in 3 of 3 seeds
- k = 18 sweeps/day (median over seeds), sigma0 = 0.4149
- eps = -1.193 (by seed: -1.145, -1.226, -1.210)
- Linear stability of the feedback needs alpha < 1/|eps| = 0.84

## Deployment (means over runs)

| G | alpha | kurtosis | mean AC(\|r\|) lags 1-20 | AC(r,1) | mean T/T0 | CV of T | days clipped |
|---|---|---|---|---|---|---|---|
| 0 | 0.000 | 1.87 | 0.001 | 0.043 | 1.000 | 0.000 | 0.0% |
| 0.25 | 0.210 | 1.89 | 0.019 | 0.044 | 1.003 | 0.029 | 0.0% |
| 0.5 | 0.419 | 1.89 | 0.051 | 0.073 | 1.009 | 0.070 | 0.0% |
| 0.75 | 0.629 | 1.96 | 0.122 | 0.106 | 1.044 | 0.141 | 0.0% |
| 1 | 0.838 | 2.04 | 0.292 | 0.256 | 1.111 | 0.263 | 0.0% |
| 1.25 | 1.048 | 2.43 | 0.368 | 0.309 | 1.361 | 0.348 | 0.0% |
| 1.5 | 1.257 | 3.11 | 0.368 | 0.265 | 1.867 | 0.364 | 0.0% |

Equal-weight index of the same stocks: kurtosis 4.68, mean AC(|r|) lags 1-20 0.099, AC(r,1) -0.097.

## Figures

- fig1_network: return correlations kept in J by sector, eigenvalues of C against the random-matrix noise edge, and the market-mode loadings.
- fig2_regimes: across the T0 scan, the Binder ratio (= return kurtosis), tau_int, the clock k and the run checks, with frozen and slow rows shaded.
- fig3_griffiths: the equilibrium width sigma_m falls with T everywhere; the 20-day volatility s rises with T only where runs don't mix, which is where eps > 0 came from.
- fig4_traces: m(t) and the distribution of m in a frozen, a slow and the selected row.
- fig5_selection: eps with 2 SE for every row and seed, and the first check each row fails.
- fig6_feedback: clustering, leftover lag-1 autocorrelation, operating point and kurtosis against the loop gain.
- fig7_model_vs_data: model returns next to the equal-weight index: time series, AC(|r|) and the distribution on a log scale.
