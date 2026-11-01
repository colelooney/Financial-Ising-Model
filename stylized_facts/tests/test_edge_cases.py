"""Edge cases, legacy code, script helpers and dependency checks from REVIEW.md sections A and D.
Tests marked xfail describe the intended behaviour and fail on the current code."""

import ast
import pickle
import subprocess
import sys
import warnings

import numpy as np
import pandas as pd
import pytest
from conftest import REPO_ROOT, SF_ROOT

# ----------------------------------------------------------------------------------------------
# Short or degenerate inputs
# ----------------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A10: a run shorter than 100 samples gives tau_int = 0, z = inf")
def test_short_pilot_run_gives_finite_or_nan_z(im):
    x = np.random.default_rng(0).standard_normal(60)
    with np.errstate(all="ignore"):
        s = im.compute_run_stats(x)
    assert not s["converged"]
    assert not np.isinf(s["z"])


@pytest.mark.xfail(strict=True, raises=IndexError,
                   reason="REVIEW A15: hill indexes past the end for two observations")
def test_hill_on_two_points(crm):
    out = crm.hill(np.array([1.0, 2.0]))
    assert np.isnan(out) or out == crm.HILL_CAP


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A15: lags beyond a short series read zero padding, not NaN")
def test_moments_on_short_series_give_nan_beyond_length(crm):
    m = crm.moments(np.random.default_rng(1).standard_normal(20))
    assert np.isnan(m["AC|r| 25"])


@pytest.mark.xfail(strict=True, raises=ValueError,
                   reason="REVIEW A15: block_bootstrap needs n >= block")
def test_block_bootstrap_shorter_than_block(crm):
    out = crm.block_bootstrap(np.random.default_rng(2).standard_normal(30), 5, 50)
    assert len(out) == 5


def test_moments_of_constant_series_are_nan(crm):
    m = crm.moments(np.ones(100))
    assert all(np.isnan(v) for v in m.values())


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A16: tied breadth values leave decile bins empty")
def test_decile_diagnostic_with_tied_breadth(gx):
    g = np.random.default_rng(3)
    n = 2_000
    m = np.sign(g.standard_normal((n, 10))).mean(axis=1)    # 10 stocks: m^2 takes 6 values

    class FakeFit:
        def variances(self):
            return g.standard_normal(n), np.ones(n)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        out = gx.decile_diagnostic(FakeFit(), m**2)
    assert np.all(np.isfinite(out))


def simulate_gjr(n, seed, omega=0.02, a=0.03, g=0.1, b=0.9, nu=7.0):
    rng = np.random.default_rng(seed)
    z = rng.standard_t(nu, n) * np.sqrt((nu - 2) / nu)
    r = np.empty(n)
    s2, e_prev = omega / (1 - a - g / 2 - b), 0.0
    for t in range(n):
        s2 = omega + (a + g * (e_prev < 0)) * e_prev**2 + b * s2
        r[t] = e_prev = np.sqrt(s2) * z[t]
    return r


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A17: the numerical Hessian steps across a = 0 into the 1e10 "
                          "penalty")
def test_robust_se_near_a_bound(gx):
    r = simulate_gjr(3_000, seed=4)
    zeros = np.zeros_like(r)
    f = gx.Fit("GJR", r, zeros, zeros)
    # mu, phi, omega, a, b, nu, g with a sitting on its lower bound
    f.theta = np.array([0.0, 0.0, 0.02, 1e-6, 0.9, 7.0, 0.1])
    se_rob, se_mle = f.robust_se()
    # Away from the bound (a = 0.03) SE(a) is about 0.014 for 3,000 days; at the bound the -h
    # step returns the 1e10 penalty and SE(a) collapses to ~0. 1e-4 is two orders below.
    assert np.all(np.isfinite(se_rob)) and np.all(se_rob > 1e-4) and np.all(se_rob < 10)


# ----------------------------------------------------------------------------------------------
# Networks
# ----------------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, raises=pytest.fail.Exception,
                   reason="REVIEW A4: isolated stocks (degree 0) are kept silently and then flip "
                          "on every attempt")
def test_isolated_stocks_are_flagged(im):
    g = np.random.default_rng(5)
    f = g.standard_normal((500, 1))
    rets = pd.DataFrame(np.hstack([f + 0.5 * g.standard_normal((500, 6)),
                                   g.standard_normal((500, 2))]))
    J, _ = im.build_empirical_J(rets, verbose=False)
    assert np.any(np.count_nonzero(J, axis=1) == 0)
    with pytest.warns(UserWarning):
        im.build_empirical_J(rets, verbose=False)


# ----------------------------------------------------------------------------------------------
# Legacy FinancialIsingModel and helpers
# ----------------------------------------------------------------------------------------------


def legacy(im, **kw):
    args = dict(N=10, network_type="erdos_renyi", T0=1.0, kappa=0.01, alpha=0.0, h0=0.0,
                rng=np.random.default_rng(0))
    args.update(kw)
    return im.FinancialIsingModel(**args)


@pytest.mark.xfail(strict=True, raises=UnboundLocalError,
                   reason="REVIEW A18: unknown network_type leaves G undefined")
def test_unknown_network_type_raises_value_error(im):
    with pytest.raises(ValueError):
        legacy(im, network_type="lattice").build_network()


@pytest.mark.xfail(strict=True, raises=pytest.fail.Exception,
                   reason="REVIEW A18: T0 = 0 is accepted and divides by zero later")
def test_zero_temperature_is_rejected(im):
    with pytest.raises(ValueError):
        legacy(im, T0=0.0)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A18: update_temperature has no clip, so sigma -> 0 sends T up")
def test_legacy_temperature_is_bounded(im):
    model = legacy(im, alpha=2.0)
    model.sigma0 = 1.0
    model.ret_hist = [0.0] * 25
    model.m_hist = [0.0] * 24 + [1e-6]
    model.update_temperature()
    assert model.T <= 20 * model.T0


@pytest.mark.xfail(strict=True, raises=TypeError,
                   reason="REVIEW A18: plot_* helpers iterate over axes, which fails for one "
                          "alpha")
def test_plot_with_one_alpha(im, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / im.FIGURES_DIR).mkdir(parents=True)
    monkeypatch.setattr(im.plt, "show", lambda: None)
    im.plot_return_distributions(N=10, n_sweeps=30, alphas=(0.0,))


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A5: rolling_susceptibility returns var(m), not N var(m) / T")
def test_rolling_susceptibility_is_n_var_over_T(im):
    model = legacy(im, T0=2.0)
    g = np.random.default_rng(6)
    model.spin_hist = [g.choice([-1, 1], 10) for _ in range(80)]
    chi = model.rolling_susceptibility(window=50)
    m = np.array([s.mean() for s in model.spin_hist])
    expected = [10 * np.var(m[t - 50:t]) / 2.0 for t in range(50, 80)]
    np.testing.assert_allclose(chi, expected)


def test_magnetic_susceptibility_with_total_magnetisation(im):
    """Correct when given total M: (<M^2> - <M>^2) / (N T)."""
    model = legacy(im, T0=2.0)
    M = np.random.default_rng(7).choice([-1, 1], (5_000, 10)).sum(axis=1)
    chi = model.magnetic_susceptibility(M.mean(), np.mean(M**2))
    assert chi == pytest.approx(M.var() / (10 * 2.0))


# ----------------------------------------------------------------------------------------------
# Data download (mocked: no network)
# ----------------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A19: fetch_market_data drops a ticker for one missing quote")
def test_fetch_market_data_keeps_ticker_with_one_gap(im, monkeypatch):
    idx = pd.bdate_range("2006-01-02", periods=60)
    g = np.random.default_rng(8)
    prices = pd.DataFrame(100 * np.exp(g.standard_normal((60, 3)).cumsum(0) * 0.01), index=idx,
                          columns=["AAA", "BBB", "CCC"])
    prices.iloc[30, 1] = np.nan
    monkeypatch.setattr(im.yf, "download",
                        lambda *a, **k: pd.concat({"Close": prices}, axis=1))
    rets, tickers = im.fetch_market_data(["AAA", "BBB", "CCC"])
    assert "BBB" in tickers


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A19: the __main__ ticker list in model.py has duplicates")
def test_model_main_ticker_list_has_no_duplicates():
    tree = ast.parse((SF_ROOT / "src" / "ising_market" / "model.py").read_text())
    lists = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
             and any(getattr(t, "id", None) == "TICKERS" for t in node.targets)]
    tickers = [elt.value for elt in lists[0].elts]
    dupes = sorted({t for t in tickers if tickers.count(t) > 1})
    assert not dupes, dupes


# ----------------------------------------------------------------------------------------------
# Import side effects (fresh interpreter)
# ----------------------------------------------------------------------------------------------


def fresh_import(tmp_path, code):
    return subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True,
                          text=True, check=True).stdout.strip()


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A20: importing model.py creates results/figures/ in the cwd")
def test_import_does_not_create_folders(tmp_path):
    fresh_import(tmp_path, "import ising_market.model")
    assert not (tmp_path / "results").exists()


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A20 / D4: importing model.py imports yfinance")
def test_import_does_not_load_yfinance(tmp_path):
    out = fresh_import(tmp_path, "import sys, ising_market.model; print('yfinance' in sys.modules)")
    assert out == "False"


# ----------------------------------------------------------------------------------------------
# Script seeds
# ----------------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A22: k_under_feedback seeds with int(100 G), so close gains "
                          "share a stream")
def test_k_under_feedback_gains_get_distinct_seeds(kuf, tmp_path, monkeypatch):
    fig = tmp_path / "figdata.pkl"
    with open(fig, "wb") as f:
        pickle.dump({"net": {"J": np.zeros((3, 3))},
                     "cons": {"T0": 1.0, "k": 2, "eps": -0.5, "sigma0": 0.1}}, f)
    draws = []

    def fake_sim(J, T0, k, alpha, sigma0, n_days, rng):
        draws.append(int(rng.integers(2**62)))
        return {"m": np.random.default_rng(len(draws)).standard_normal(n_days),
                "T": np.ones(n_days)}

    monkeypatch.setattr(kuf, "simulate_deployed", fake_sim)
    monkeypatch.setattr(sys, "argv", ["k_under_feedback.py", "--figdata", str(fig), "--gains",
                                      "0.501", "0.509", "--ks", "2", "--runs", "1", "--days",
                                      "50"])
    kuf.main()
    assert len(draws) == 2 and draws[0] != draws[1]


# ----------------------------------------------------------------------------------------------
# Dependencies and configuration
# ----------------------------------------------------------------------------------------------


def pyproject():
    # imported here: ruff reads requires-python >= 3.9 and would sort tomllib (3.11) as third-party
    import tomllib

    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW D1: requires-python allows 3.9, but the scripts use "
                          "zip(strict=True)")
def test_requires_python_matches_the_code():
    spec = pyproject()["project"]["requires-python"]
    assert spec.replace(" ", "") in (">=3.10", ">=3.11", ">=3.12")


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW D6: pytest testpaths points at a folder that doesn't exist")
def test_pytest_testpaths_exist():
    for path in pyproject()["tool"]["pytest"]["ini_options"]["testpaths"]:
        assert (REPO_ROOT / path).is_dir(), path


def test_runtime_dependencies_import():
    """D2/D3: the declared stack imports together (numba with this numpy)."""
    import matplotlib  # noqa: F401
    import networkx  # noqa: F401
    import numba
    import scipy  # noqa: F401
    import yfinance  # noqa: F401

    assert numba.njit(lambda x: x + 1)(1) == 2
