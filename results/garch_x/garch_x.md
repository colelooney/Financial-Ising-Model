# Does breadth predict volatility? (equal-weight index of 100 stocks, 2005-01-04 to 2024-12-31)

5032 days. Returns in percent; variance in %². Out-of-sample split at day 2516 (2015-01-02).

## Main result: does breadth add to a model that already has dispersion?

gamma = -0.0684 (robust SE 0.0257, z = -2.66, p = 0.0078); likelihood ratio 7.20 (p = 0.0073); out of sample, QLIKE gain -0.0057 (Diebold-Mariano t = -0.96, p = 0.3368).

Breadth on its own is not the right test: an equal-weight index of N stocks keeps some idiosyncratic risk (about the dispersion over N), so low breadth predicts variance mechanically. On simulated panels where breadth has no effect, breadth alone was significant in 12% of runs at the 5% level, and breadth given dispersion in 5%.

## Fitted models (whole sample)

| model | log-lik | mu | phi | omega | a | g | b | nu | gamma | delta |
|---|---|---|---|---|---|---|---|---|---|---|
| GARCH | -6462.1 | 0.08924 | -0.03335 | 0.01569 | 0.1302 |  | 0.8631 | 6.308 |  |  |
| GJR | -6396.6 | 0.06377 | -0.02303 | 0.0162 | 0.004946 | 0.1867 | 0.8842 | 6.927 |  |  |
| GJR + breadth | -6384.7 | 0.0658 | -0.02284 | 0.03392 | 0.02032 | 0.2075 | 0.8743 | 7.012 | -0.1241 |  |
| GJR + dispersion | -6381.8 | 0.06263 | -0.02578 | 0.003238 | 9.673e-15 | 0.2003 | 0.8632 | 7.116 |  | 0.02756 |
| GJR + both | -6378.2 | 0.0634 | -0.02345 | 0.01552 | 6.151e-14 | 0.2178 | 0.8662 | 7.101 | -0.06845 | 0.02231 |

## In-sample likelihood-ratio tests

| question | base | alternative | LR | df | p |
|---|---|---|---|---|---|
| breadth, gamma | GJR | GJR + breadth | 23.83 | 1 | 0.0000 |
| dispersion, delta | GJR | GJR + dispersion | 29.51 | 1 | 0.0000 |
| breadth given dispersion | GJR + dispersion | GJR + both | 7.20 | 1 | 0.0073 |
| dispersion given breadth | GJR + breadth | GJR + both | 12.88 | 1 | 0.0003 |
| asymmetry, g (sanity check) | GARCH | GJR | 131.07 | 1 | 0.0000 |

## Robust Wald tests (sandwich standard errors)

| model | parameter | estimate | robust SE | MLE SE | z | p |
|---|---|---|---|---|---|---|
| GJR + breadth | gamma | -0.1241 | 0.0277 | 0.0259 | -4.49 | 0.0000 |
| GJR + both | gamma | -0.0684 | 0.0257 | 0.0245 | -2.66 | 0.0078 |
| GJR + both | delta | 0.0223 | 0.0071 | 0.0066 | 3.16 | 0.0016 |

A one-standard-deviation rise in m² (0.271) adds gamma x 0.271 = -0.0336 %² to the next day's variance; the median fitted variance is 0.639 %².

## Out of sample (fitted before the split, QLIKE loss after it)

Positive gain = the alternative forecasts better. DM t uses Newey-West standard errors.

| question | base | alternative | QLIKE base | QLIKE alt | gain | DM t | p |
|---|---|---|---|---|---|---|---|
| breadth, gamma | GJR | GJR + breadth | 0.6113 | 0.6218 | -0.0105 | -1.44 | 0.1491 |
| dispersion, delta | GJR | GJR + dispersion | 0.6113 | 0.6158 | -0.0045 | -0.51 | 0.6086 |
| breadth given dispersion | GJR + dispersion | GJR + both | 0.6158 | 0.6215 | -0.0057 | -0.96 | 0.3368 |
| dispersion given breadth | GJR + breadth | GJR + both | 0.6218 | 0.6215 | 0.0003 | 0.05 | 0.9562 |
| asymmetry, g (sanity check) | GARCH | GJR | 0.6338 | 0.6113 | 0.0226 | 2.03 | 0.0423 |

## Baseline forecast errors by yesterday's alignment

Mean of e² / σ² (1 if the variance model is right), by decile of m² on the day before.

| decile | mean m² | GJR | GJR + breadth | GJR + both |
|---|---|---|---|---|
| 1 | 0.001 | 0.97 ± 0.07 | 0.95 ± 0.07 | 0.96 ± 0.07 |
| 2 | 0.012 | 1.23 ± 0.14 | 1.18 ± 0.13 | 1.19 ± 0.13 |
| 3 | 0.033 | 1.07 ± 0.08 | 1.02 ± 0.08 | 1.03 ± 0.08 |
| 4 | 0.065 | 0.97 ± 0.07 | 0.97 ± 0.08 | 0.98 ± 0.08 |
| 5 | 0.116 | 1.15 ± 0.09 | 1.15 ± 0.09 | 1.15 ± 0.09 |
| 6 | 0.183 | 0.87 ± 0.07 | 0.88 ± 0.07 | 0.88 ± 0.07 |
| 7 | 0.279 | 1.10 ± 0.09 | 1.11 ± 0.08 | 1.10 ± 0.08 |
| 8 | 0.411 | 0.88 ± 0.06 | 0.91 ± 0.07 | 0.91 ± 0.07 |
| 9 | 0.578 | 0.92 ± 0.08 | 0.96 ± 0.08 | 0.95 ± 0.08 |
| 10 | 0.832 | 0.78 ± 0.09 | 0.80 ± 0.10 | 0.82 ± 0.10 |
