"""Loose pytest checks for the stylized_facts Ising market model.


    uv run pytest stylized_facts/tests/test_loose.py

Importing model.py creates results/figures/ in the working directory, so the
module is imported from inside a temporary folder.
"""

import importlib
import os

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    old = os.getcwd()
    os.chdir(tmp_path_factory.mktemp("import_dir"))
    try:
        return importlib.import_module("ising_market.model")
    finally:
        os.chdir(old)


@pytest.fixture(scope="module")
def small_J():
    """Fully connected 10-spin ferromagnet with uniform coupling 0.1."""
    N = 10
    J = np.full((N, N), 0.1)
    np.fill_diagonal(J, 0.0)
    return J


@pytest.fixture(scope="module")
def fake_returns():
    """Two blocks of correlated synthetic returns (seeded)."""
    rng = np.random.default_rng(0)
    n_days = 500
    f1, f2 = rng.normal(size=(2, n_days))
    cols = {}
    for i in range(4):
        cols[f"A{i}"] = f1 + 0.5 * rng.normal(size=n_days)
    for i in range(4):
        cols[f"B{i}"] = f2 + 0.5 * rng.normal(size=n_days)
    return pd.DataFrame(cols) * 0.01


# --- build_empirical_J -------------------------------------------------------

def test_build_empirical_J_shape_and_symmetry(model, fake_returns):
    J, C = model.build_empirical_J(fake_returns, verbose=False)
    N = fake_returns.shape[1]
    assert J.shape == C.shape == (N, N)
    assert np.allclose(J, J.T)
    assert np.all(np.diag(J) == 0)
    assert np.all(J >= 0)


def test_build_empirical_J_normalises_mean_coupling(model, fake_returns):
    J, _ = model.build_empirical_J(fake_returns, verbose=False)
    assert J[J > 0].mean() == pytest.approx(0.1)


def test_build_empirical_J_threshold_drops_cross_block_edges(model, fake_returns):
    J, C = model.build_empirical_J(fake_returns, threshold=0.3, normalize=False, verbose=False)
    # without normalisation, kept entries equal the correlation and exceed the threshold
    kept = J > 0
    assert np.allclose(J[kept], C[kept])
    assert np.all(C[kept] > 0.3)
    # the two independent blocks should not be linked
    assert np.all(J[:4, 4:] == 0)


# --- _acf, mean_se, thinned_stats -------------------------------------------

def test_acf_matches_direct_correlation(model):
    rng = np.random.default_rng(1)
    x = rng.normal(size=300)
    x = x - x.mean()
    direct = np.correlate(x, x, "full")[len(x) - 1:] / np.sum(x**2)
    acf = model._acf(x)
    assert acf[0] == pytest.approx(1.0)
    assert np.allclose(acf, direct, atol=1e-10)


def test_mean_se(model):
    mean, se = model.mean_se([1.0, 2.0, 3.0, 4.0])
    assert mean == pytest.approx(2.5)
    assert se == pytest.approx(np.std([1, 2, 3, 4], ddof=1) / 2)


def test_thinned_stats_white_noise(model):
    rng = np.random.default_rng(2)
    m = rng.normal(size=20_000)
    ac1, s = model.thinned_stats(m, k=5, window=20)
    assert abs(ac1) < 0.05
    assert 0.8 < s < 1.1  # rolling std of unit-variance noise (slightly biased low)


def test_thinned_stats_short_series_gives_nan_std(model):
    ac1, s = model.thinned_stats(np.arange(10.0), k=1, window=20)
    assert np.isfinite(ac1)
    assert np.isnan(s)


# --- compute_run_stats ------------------------------------------------------

def test_compute_run_stats_gaussian_noise(model):
    rng = np.random.default_rng(3)
    m = rng.normal(size=50_000)
    st = model.compute_run_stats(m)
    assert st["R"] == pytest.approx(3.0, abs=0.1)  # Gaussian kurtosis
    assert st["tau_int"] == pytest.approx(0.5, abs=0.1)  # uncorrelated
    assert st["converged"]
    assert st["z"] < 4
    assert st["q"] < 0.05
    assert set(st) >= {"sigma_m", "R", "q", "mean_m", "acf", "tau_int", "converged", "z"}


def test_compute_run_stats_correlated_series_has_longer_tau(model):
    rng = np.random.default_rng(4)
    n, phi = 50_000, 0.9
    e = rng.normal(size=n)
    m = np.empty(n)
    m[0] = e[0]
    for t in range(1, n):
        m[t] = phi * m[t - 1] + e[t]
    st = model.compute_run_stats(m)
    # AR(1): tau_int = (1 + phi) / (2 (1 - phi)) = 9.5
    assert st["tau_int"] == pytest.approx(9.5, rel=0.25)


# --- pilot dynamics ---------------------------------------------------------

def test_run_pilot_reproducible(model, small_J):
    a = model._run_pilot(small_J, 0.5, np.random.default_rng(7), "random", 50, 200)
    b = model._run_pilot(small_J, 0.5, np.random.default_rng(7), "random", 50, 200)
    assert np.array_equal(a, b)
    assert a.shape == (200,)
    assert np.all(np.abs(a) <= 1)


def test_run_pilot_bad_start(model, small_J):
    with pytest.raises(ValueError):
        model._run_pilot(small_J, 0.5, np.random.default_rng(0), "down", 10, 10)


def test_run_pilot_cold_vs_hot(model, small_J):
    lam = np.linalg.eigvalsh(small_J).max()
    cold = model._run_pilot(small_J, 0.2 * lam, np.random.default_rng(0), "up", 200, 2000)
    hot = model._run_pilot(small_J, 5.0 * lam, np.random.default_rng(0), "up", 200, 2000)
    assert np.mean(np.abs(cold)) > 0.9  # ordered
    assert np.mean(np.abs(hot)) < 0.5  # disordered


# --- select_T0 --------------------------------------------------------------

def _good_row(i, T0, eps_mean):
    return {
        "i_T0": i, "T0": T0, "equilibrated": True, "frac_converged": 1.0,
        "n_s_valid": 16, "n_eff": 16 * 500, "ac1_mean": 0.0, "ac1_se": 0.01,
        "frac_z_high": 0.0, "eps_mean": eps_mean, "eps_se": 0.05, "k": 5, "n_runs": 16,
    }


def test_select_T0_picks_most_negative_eps(model):
    table = pd.DataFrame([
        _good_row(0, 1.0, -0.2),
        _good_row(1, 1.2, -0.8),
        _good_row(2, 1.4, 0.5),  # positive eps -> rejected
    ])
    res = model.select_T0(table, verbose=False)
    assert res["i_T0"] == 1
    assert res["T0"] == pytest.approx(1.2)
    assert res["k"] == 5
    assert not res["criteria"].loc[2, "eps_negative"]


def test_select_T0_no_survivors(model):
    row = _good_row(0, 1.0, -0.5)
    row["equilibrated"] = False
    res = model.select_T0(pd.DataFrame([row]), verbose=False)
    assert res["T0"] is None and res["k"] is None and res["row"] is None


def test_select_T0_missing_columns(model):
    with pytest.raises(KeyError):
        model.select_T0(pd.DataFrame({"T0": [1.0]}), verbose=False)


# --- deployed model ---------------------------------------------------------

def test_simulate_deployed_reproducible_and_shapes(model, small_J):
    kw = dict(T0=1.0, k=2, alpha=0.5, sigma0=0.1, n_days=300, n_burn=50, kappa=0.02)
    a = model.simulate_deployed(small_J, rng=np.random.default_rng(11), **kw)
    b = model.simulate_deployed(small_J, rng=np.random.default_rng(11), **kw)
    assert np.array_equal(a["r"], b["r"])
    assert a["r"].shape == a["m"].shape == a["T"].shape == (300,)
    assert np.allclose(a["r"], 0.02 * a["m"])
    assert np.all(np.abs(a["m"]) <= 1)
    assert 0.0 <= a["clip_frac"] <= 1.0


def test_simulate_deployed_alpha_zero_keeps_T_fixed(model, small_J):
    out = model.simulate_deployed(small_J, T0=0.8, k=1, alpha=0.0, sigma0=0.1,
                                  n_days=200, n_burn=30, rng=np.random.default_rng(5))
    assert np.allclose(out["T"], 0.8)
    assert out["clip_frac"] == 0.0


def test_simulate_deployed_T_stays_within_clip(model, small_J):
    T0 = 1.0
    out = model.simulate_deployed(small_J, T0=T0, k=1, alpha=5.0, sigma0=1e-3,
                                  n_days=300, n_burn=30, rng=np.random.default_rng(6),
                                  T_clip=(0.5, 2.0))
    assert np.all(out["T"] >= 0.5 * T0 - 1e-12)
    assert np.all(out["T"] <= 2.0 * T0 + 1e-12)


# --- stylised_facts ---------------------------------------------------------

def test_stylised_facts_gaussian(model):
    r = np.random.default_rng(8).normal(scale=0.01, size=20_000)
    sf = model.stylised_facts(r)
    assert sf["kurtosis"] == pytest.approx(3.0, abs=0.15)
    assert sf["jb_p"] > 0.001
    assert abs(sf["ac_r1"]) < 0.05
    assert abs(sf["ac_abs_mean"]) < 0.05


def test_stylised_facts_fat_tails(model):
    r = np.random.default_rng(9).standard_t(df=4, size=20_000)
    sf = model.stylised_facts(r)
    assert sf["kurtosis"] > 4
    assert sf["jb_p"] < 1e-6
    assert 2.5 < sf["t_dof"] < 6
