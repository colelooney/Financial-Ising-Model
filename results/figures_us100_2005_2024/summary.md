# Financial Ising model: figures summary

Generated 2026-10-11 20:22:40 from `data/rets_us100_2005_2024.pkl` in 11.2 min. Pilots: 50,000 sweeps after 10,000 burn-in; deployment: 4 runs x 10,000 days per gain.

## Network

- 100 stocks, 5032 trading days (2005-01-04 to 2024-12-31)
- J keeps correlations above 0.3: 4301 of 4950 pairs (86.9%)
- lambda_max(J) = 9.0153
- Largest eigenvalue of C: 41.79 (42% of the variance); 7 eigenvalues above the random-matrix edge 1.30

## Calibration by seed

| seed | winner T0/lambda | T0 | k | eps +- SE | rows passing every check (T0/lambda) |
|---|---|---|---|---|---|
| 42 | 0.839 | 7.5677 | 248 | -3.324 +- 0.076 | 0.839, 0.936 |
| 43 | 1.045 | 9.4177 | 19 | -2.236 +- 0.041 | 1.045, 1.165, 1.300 |
| 44 | 0.839 | 7.5677 | 258 | -3.041 +- 0.067 | 0.839, 0.936, 1.045 |

Regimes (seed 42): frozen 0.35-0.67; slow 0.75-0.75; mixing 0.84-1.30

## Recommended row (survives in the most seeds)

- T0 = 7.5677 = 0.839 lambda_max, passing in 2 of 3 seeds
- k = 248 sweeps/day (median over seeds), sigma0 = 0.5642
- eps = -3.183 (by seed: -3.324, n/a, -3.041)
- Linear stability of the feedback needs alpha < 1/|eps| = 0.31

## Deployment (means over runs)

| G | alpha | kurtosis | mean AC(\|r\|) lags 1-20 | AC(r,1) | mean T/T0 | CV of T | days clipped |
|---|---|---|---|---|---|---|---|
| 0 | 0.000 | 1.26 | 0.001 | 0.035 | 1.000 | 0.000 | 0.0% |
| 0.25 | 0.079 | 1.26 | 0.012 | 0.037 | 1.000 | 0.006 | 0.0% |
| 0.5 | 0.157 | 1.27 | 0.035 | 0.050 | 1.002 | 0.015 | 0.0% |
| 0.75 | 0.236 | 1.30 | 0.106 | 0.072 | 1.008 | 0.031 | 0.0% |
| 1 | 0.314 | 1.82 | 0.412 | 0.064 | 1.133 | 0.116 | 0.0% |
| 1.25 | 0.393 | 2.82 | 0.054 | -0.012 | 1.543 | 0.085 | 0.0% |
| 1.5 | 0.471 | 2.88 | 0.030 | 0.002 | 1.846 | 0.095 | 0.0% |

Equal-weight index of the same stocks: kurtosis 18.62, mean AC(|r|) lags 1-20 0.339, AC(r,1) -0.110.

## Figures

- fig1_network: return correlations kept in J by sector, eigenvalues of C against the random-matrix noise edge, and the market-mode loadings.
- fig2_regimes: across the T0 scan, the Binder ratio (= return kurtosis), tau_int, the clock k and the run checks, with frozen and slow rows shaded.
- fig3_griffiths: the equilibrium width sigma_m falls with T everywhere; the 20-day volatility s rises with T only where runs don't mix, which is where eps > 0 came from.
- fig4_traces: m(t) and the distribution of m in a frozen, a slow and the selected row.
- fig5_selection: eps with 2 SE for every row and seed, and the first check each row fails.
- fig6_feedback: clustering, leftover lag-1 autocorrelation, operating point and kurtosis against the loop gain.
- fig7_model_vs_data: model returns next to the equal-weight index: time series, AC(|r|) and the distribution on a log scale.
