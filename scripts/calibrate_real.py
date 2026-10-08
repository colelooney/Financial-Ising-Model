import sys, pickle, datetime
sys.path.insert(0, "src")
import numpy as np
from ising_market.model import fetch_market_data, build_empirical_J, calibrate_parameters

TICKERS = ['AAPL','MSFT','AMZN','INTC','CSCO','JPM','BAC','GS','WFC','C','XOM','CVX','COP',
           'JNJ','PFE','UNH','MRK','WMT','HD','MCD','CAT','GE','MMM','BA','DIS','TWX',
           'AMD','IBM','ORCL','TXN']

rets, tickers = fetch_market_data(TICKERS, start="2005-01-01", end="2008-01-01")
J, C = build_empirical_J(rets)
lam = np.linalg.eigvalsh(J).max()
rets.to_pickle("data/rets_2005_2007.pkl")      # frozen inputs: reuse these, don't re-download
np.save("data/J_2005_2007.npy", J)

cols = ["T0/lam", "equilibrated", "frac_converged", "k", "ac1_mean", "ac1_se", "R_mean", "eps_mean", "eps_se", "eps_rows"]
results = {}
for seed in (42, 43, 44):
    res = calibrate_parameters(rets, J, n_pilot=50000, n_burn=10000, seed=seed)
    tab = res["T0_table"].assign(**{"T0/lam": res["T0_table"].T0 / lam})
    win = "none" if res["T0"] is None else f"T0/lam={res['T0']/lam:.3f}, k={res['k']}"
    print(f"\n=== seed {seed}: winner {win}")
    print(tab[cols].round(3).to_string(index=False))
    results[seed] = {key: res[key] for key in ("T0", "k", "sigma0", "T0_table")}

with open("results/calibration_real.pkl", "wb") as f:
    pickle.dump({"downloaded": str(datetime.date.today()), "tickers": tickers, "lam": lam, "J": J, "results": results}, f)