"""Download a ticker universe once, clean it, and freeze the returns and J for the other scripts.

    uv run python scripts/freeze_data.py --core-only     # about 100 stocks: run this first
    uv run python scripts/freeze_data.py                 # the full list, about 200 stocks
    uv run python scripts/freeze_data.py --sector Financials --tag fin

Reads universes/tickers_us_large_cap.csv (ticker,sector,core). Writes, for a tag such as
us101_2005_2024:
    data/rets_<tag>.pkl       daily log returns (DataFrame, tickers in the CSV's sector order)
    data/J_<tag>.npy          the coupling matrix, built exactly as the model builds it
    data/sectors_<tag>.csv    ticker,sector for the kept tickers (for make_figures.py --sectors)
    data/outliers_<tag>.csv   single-day moves above --flag, to look at by hand
    data/freeze_<tag>.txt     what was kept, what was dropped and why, and the network at several
                              thresholds
The download is the only step that needs the internet; everything downstream reads these files, so
results stay reproducible after Yahoo's data changes.
"""

import argparse
import datetime
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

try:
    import ising_market.model as im
except ModuleNotFoundError:  # package not installed: use the src/ layout directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    import ising_market.model as im


def read_universe(path, core_only, sectors, exclude):
    u = pd.read_csv(path, dtype={"ticker": str, "sector": str})
    u["ticker"] = u["ticker"].str.strip().str.upper()
    if core_only:
        u = u[u["core"] == 1]
    if sectors:
        wanted = {s.lower() for s in sectors}
        chosen = u[u["sector"].str.lower().isin(wanted)]
        if chosen.empty:
            sys.exit(f"no tickers in sectors {sectors}; the file has {sorted(set(u['sector']))}")
        u = chosen
    if exclude:
        u = u[~u["ticker"].isin({t.upper() for t in exclude})]
    return u.reset_index(drop=True)


def _close(frame, tickers):
    """The Close prices from a yf.download result as a DataFrame with one column per ticker."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=tickers, dtype=float)
    close = frame["Close"]
    if isinstance(close, pd.Series):  # older yfinance with a single ticker
        close = close.to_frame(tickers[0])
    return close.reindex(columns=tickers)


def download(tickers, start, end, repair, retries=2):
    """Batch download, then retry the tickers that came back empty one at a time."""
    print(f"Downloading {len(tickers)} tickers, {start} to {end} (end date excluded) ...")
    prices = _close(yf.download(tickers, start=start, end=end, auto_adjust=True, repair=repair,
                                progress=False, threads=True), tickers)
    for attempt in range(retries):
        missing = [t for t in tickers if prices[t].notna().sum() == 0]
        if not missing:
            break
        print(f"  retrying {len(missing)} empty tickers one by one (attempt {attempt + 1}): "
              f"{' '.join(missing)}")
        for t in missing:
            time.sleep(1.0)
            one = _close(yf.download(t, start=start, end=end, auto_adjust=True, repair=repair,
                                     progress=False, threads=False), [t])
            if one[t].notna().any():
                prices = prices.reindex(prices.index.union(one.index))
                prices[t] = one[t]
    prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()
    return prices.sort_index()


def clean(prices, grace, max_missing, max_gap):
    """Keep tickers with a price from the first trading day (within `grace` days) to the last,
    with at most `max_missing` missing days, none in a run longer than `max_gap`. Returns the
    cleaned prices and a dict ticker -> reason for each ticker dropped."""
    if prices.notna().sum().sum() == 0:
        sys.exit("nothing downloaded: check the internet connection and the ticker file")
    # Trading days: rows where most tickers have a price (drops stray rows from bad quotes)
    days = prices.notna().mean(axis=1) >= 0.9
    stray = int((~days).sum())
    prices = prices[days]
    empty = [t for t in prices if prices[t].notna().sum() == 0]
    dropped = {t: "no data from Yahoo (delisted, renamed or download failed)" for t in empty}
    prices = prices.drop(columns=empty)
    first, last = prices.index[0], prices.index[-1]
    keep = []
    for t in prices:
        s = prices[t]
        fv, lv = s.first_valid_index(), s.last_valid_index()
        if s.loc[:fv].shape[0] - 1 > grace:
            dropped[t] = f"starts {fv.date()}, after the sample start {first.date()}"
            continue
        if s.loc[lv:].shape[0] - 1 > grace:
            dropped[t] = f"ends {lv.date()}, before the sample end {last.date()}"
            continue
        inside = s.loc[fv:lv]
        n_miss = int(inside.isna().sum())
        run = int(inside.isna().astype(int).groupby(inside.notna().cumsum()).sum().max())
        if n_miss > max_missing or run > max_gap:
            dropped[t] = f"{n_miss} missing days (longest gap {run})"
            continue
        keep.append(t)
    prices = prices[keep].ffill(limit=max_gap)
    prices = prices.iloc[prices.notna().all(axis=1).to_numpy().argmax():]   # common start
    prices = prices.loc[: prices.notna().all(axis=1)[::-1].idxmax()]          # common end
    return prices, dropped, stray


def network_table(rets, thresholds):
    C = rets.corr().to_numpy()
    N = C.shape[0]
    iu = np.triu_indices(N, 1)
    rows = [f"mean pairwise correlation {C[iu].mean():.3f} (median {np.median(C[iu]):.3f})",
            "threshold  density  mean degree  lambda_max(J)  isolated stocks"]
    for th in thresholds:
        J, _ = im.build_empirical_J(rets, threshold=th, verbose=False)
        deg = np.count_nonzero(J, axis=1)
        dens = np.count_nonzero(np.triu(J, 1)) / len(iu[0])
        lam = np.linalg.eigvalsh(J).max() if dens > 0 else 0.0
        rows.append(f"{th:9.2f}  {dens:7.1%}  {deg.mean():11.1f}  {lam:13.3f}  "
                    f"{int((deg == 0).sum()):15d}")
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--tickers", default="universes/tickers_us_large_cap.csv")
    p.add_argument("--start", default="2005-01-01")
    p.add_argument("--end", default="2025-01-01", help="first day NOT included")
    p.add_argument("--core-only", action="store_true", help="only rows with core = 1")
    p.add_argument("--sector", nargs="+", default=None, help="only these sectors")
    p.add_argument("--exclude", nargs="+", default=None, help="tickers to leave out")
    p.add_argument("--tag", default=None, help="file suffix (default: us<N>_<start>_<end>)")
    p.add_argument("--threshold", type=float, default=0.3, help="correlation cut-off for J")
    p.add_argument("--grace", type=int, default=5,
                   help="trading days a ticker may start late or end early")
    p.add_argument("--max-missing", type=int, default=10, help="missing days allowed per ticker")
    p.add_argument("--max-gap", type=int, default=3,
                   help="longest run of missing days that is forward-filled")
    p.add_argument("--flag", type=float, default=0.25,
                   help="report single-day |log return| above this in outliers_<tag>.csv")
    p.add_argument("--repair", action="store_true",
                   help="ask yfinance to repair bad prices (slower; see yfinance's docs)")
    p.add_argument("--out", default="data")
    args = p.parse_args()

    u = read_universe(args.tickers, args.core_only, args.sector, args.exclude)
    tickers = list(u["ticker"])
    raw = download(tickers, args.start, args.end, args.repair)
    prices, dropped, stray = clean(raw, args.grace, args.max_missing, args.max_gap)
    order = [t for t in tickers if t in prices.columns]   # sector blocks, as in the CSV
    prices = prices[order]
    rets = np.log(prices / prices.shift(1)).iloc[1:]
    if rets.isna().any().any() or not np.isfinite(rets.to_numpy()).all():
        sys.exit("non-finite returns after cleaning: check the prices for zeros")

    N = rets.shape[1]
    y0, y1 = str(rets.index[0].year), str(rets.index[-1].year)
    tag = args.tag or f"us{N}_{y0}_{y1}"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    J, _ = im.build_empirical_J(rets, threshold=args.threshold, verbose=False)
    rets.to_pickle(out / f"rets_{tag}.pkl")
    np.save(out / f"J_{tag}.npy", J)
    sec = u.set_index("ticker").loc[order, "sector"]
    sec.reset_index().to_csv(out / f"sectors_{tag}.csv", index=False)

    # Large single-day moves: real news (2008 banks, earnings) or a spin-off Yahoo didn't adjust
    index = rets.mean(axis=1)
    big = rets.stack()
    big = big[big.abs() > args.flag]
    outl = pd.DataFrame({"date": big.index.get_level_values(0).date,
                         "ticker": big.index.get_level_values(1),
                         "sector": sec.reindex(big.index.get_level_values(1)).to_numpy(),
                         "log_return": big.to_numpy().round(4),
                         "index_same_day": index.reindex(big.index.get_level_values(0))
                         .to_numpy().round(4)})
    outl.to_csv(out / f"outliers_{tag}.csv", index=False)

    zero = (rets == 0).mean()
    stale = zero[zero > 0.03]
    eq = index.to_numpy()
    z = (eq - eq.mean()) / eq.std()
    lines = [
        f"Frozen {datetime.date.today()} with yfinance {yf.__version__} from {args.tickers}",
        f"Requested {args.start} to {args.end} (end excluded); returns {rets.index[0].date()} to "
        f"{rets.index[-1].date()}, {len(rets)} trading days",
        f"Kept {N} of {len(tickers)} tickers; {stray} stray rows (fewer than 90% of tickers "
        "quoted) removed",
        f"Equal-weight index: daily std {eq.std():.4f}, kurtosis {np.mean(z ** 4):.1f}, "
        f"largest |move| {np.abs(eq).max():.3f} on {index.abs().idxmax().date()}",
        "", "Kept per sector:",
        *[f"  {s}: {n}" for s, n in sec.value_counts().reindex(u['sector'].unique())
          .dropna().astype(int).items()],
        "", f"Dropped ({len(dropped)}):",
        *([f"  {t}: {why}" for t, why in dropped.items()] or ["  none"]),
        "", f"Single-day moves above {args.flag:.0%} in log terms: {len(outl)} "
        f"(in {outl['ticker'].nunique() if len(outl) else 0} tickers), listed in "
        f"outliers_{tag}.csv. One unadjusted spin-off moves a {N}-stock equal-weight index by "
        f"about {0.25 / N:.2%}, so these matter little for the target, but check any that are "
        "not news.",
        f"Tickers with more than 3% zero-return days (stale quotes?): "
        f"{', '.join(f'{t} {v:.0%}' for t, v in stale.items()) or 'none'}",
        "", f"Network (J saved at threshold {args.threshold}):",
        *network_table(rets, sorted({0.3, 0.4, 0.5, 0.6, args.threshold})),
        "", "Next:",
        f"  uv run python scripts/make_figures.py --rets {out}/rets_{tag}.pkl "
        f"--J {out}/J_{tag}.npy --threshold {args.threshold} --sectors {out}/sectors_{tag}.csv "
        f"--out results/figures_{tag}",
        f"  uv run python scripts/compare_return_models.py --figdata "
        f"results/figures_{tag}/figdata.pkl --out results/return_models_{tag} --quick",
    ]
    (out / f"freeze_{tag}.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWrote {out}/rets_{tag}.pkl, J_{tag}.npy, sectors_{tag}.csv, outliers_{tag}.csv, "
          f"freeze_{tag}.txt")


if __name__ == "__main__":
    main()
