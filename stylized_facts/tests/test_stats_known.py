"""Statistical helpers against textbook answers (REVIEW.md section C, statistics)."""

import numpy as np
import pandas as pd
import pytest
from _helpers import ar1
from scipy.special import gammaln


def direct_acf(x, max_lag):
    x = np.asarray(x, float) - np.mean(x)
    full = np.correlate(x, x, "full")[len(x) - 1:]
    return full[: max_lag + 1] / full[0]


# ----------------------------------------------------------------------------------------------
# Autocorrelation, tau_int, z test, Binder ratio
# ----------------------------------------------------------------------------------------------


def test_all_acf_versions_match_direct_correlation(im, crm, mf):
    x = np.random.default_rng(0).standard_normal(500).cumsum()
    ref = direct_acf(x, 40)
    np.testing.assert_allclose(im._acf(x - x.mean())[:41], ref, atol=1e-12)
    np.testing.assert_allclose(crm._acf(x, 40), ref, atol=1e-12)
    np.testing.assert_allclose(mf.acf(x, 40), ref, atol=1e-12)
    np.testing.assert_allclose(mf.acf(x, 40), mf.return_facts(x)["acf_r"][:41], atol=1e-12)


@pytest.mark.parametrize("rho", [0.0, 0.5, 0.9])
def test_acf_of_ar1_is_geometric(im, rho):
    x = ar1(200_000, rho, seed=1)
    acf = im._acf(x - x.mean())
    for L in (1, 2, 5):
        assert acf[L] == pytest.approx(rho**L, abs=0.01)


@pytest.mark.parametrize("rho", [0.5, 0.9])
def test_tau_int_of_ar1(im, rho):
    x = ar1(200_000, rho, seed=2)
    s = im.compute_run_stats(x)
    assert s["converged"]
    assert s["tau_int"] == pytest.approx((1 + rho) / (2 * (1 - rho)), rel=0.08)


def test_converged_means_tau_below_n_over_300(im):
    """AR(1) with rho = 0.99 has tau_int = 99.5: not converged at n = 10,000 (n/300 = 33),
    converged at n = 100,000 (n/300 = 333). (At n = 20,000 the windowed estimate is biased low,
    about 64-107 over seeds, so some runs pass although the true tau exceeds n/300.)"""
    short = im.compute_run_stats(ar1(10_000, 0.99, seed=3))
    long = im.compute_run_stats(ar1(100_000, 0.99, seed=3))
    assert not short["converged"]
    assert long["converged"]
    assert long["tau_int"] < 100_000 / 300


def test_z_test_size_on_iid_noise(im):
    rng = np.random.default_rng(4)
    z = np.array([im.compute_run_stats(rng.standard_normal(2_000))["z"] for _ in range(2_000)])
    assert np.mean(z > 3) < 0.01          # nominal 0.0027
    assert np.mean(z > 1.96) == pytest.approx(0.05, abs=0.02)


def test_z_test_size_on_ar1(im):
    z = np.array([im.compute_run_stats(ar1(5_000, 0.8, seed=[5, i]))["z"] for i in range(400)])
    assert np.mean(z > 1.96) == pytest.approx(0.05, abs=0.035)


@pytest.mark.parametrize(("draw", "R"), [
    (lambda g, n: g.standard_normal(n), 3.0),
    (lambda g, n: g.choice([-1.0, 1.0], n), 1.0),
    (lambda g, n: g.uniform(-1, 1, n), 1.8),
])
def test_binder_ratio_of_known_distributions(im, draw, R):
    x = draw(np.random.default_rng(6), 400_000)
    assert im.compute_run_stats(x)["R"] == pytest.approx(R, abs=0.03)


# ----------------------------------------------------------------------------------------------
# Thinning, rolling volatility, elasticity
# ----------------------------------------------------------------------------------------------


def test_thinned_lag1_of_ar1(im):
    x = ar1(300_000, 0.8, seed=7)
    ac1, _ = im.thinned_stats(x, 3, 20)
    assert ac1 == pytest.approx(0.8**3, abs=0.01)


def test_rolling_std_bias_matches_c4(im):
    """Mean rolling std (ddof 0, window w) of iid N(0, s^2) is s sqrt(2/w) G(w/2) / G((w-1)/2)."""
    w, sigma = 20, 1.7
    factor = np.sqrt(2 / w) * np.exp(gammaln(w / 2) - gammaln((w - 1) / 2))
    x = sigma * np.random.default_rng(8).standard_normal(400_000)
    _, s = im.thinned_stats(x, 1, w)
    assert factor == pytest.approx(0.962, abs=0.001)
    assert s == pytest.approx(factor * sigma, rel=0.005)


def make_runs(im, T0s, scales, n=20_000, seeds=2, seed=0, base=None):
    """Synthetic pilot runs: the same zero-mean base series times a scale per row, so the rolling
    std of every run at every row's k is scale x constant."""
    if base is None:
        base = np.random.default_rng(seed).standard_normal(n)
        base -= base.mean()
    runs = []
    for i, (T0, c) in enumerate(zip(T0s, scales, strict=True)):
        for sid in range(seeds):
            for start in ("random", "up"):
                run = {"T0": T0, "i_T0": i, "seed_id": sid, "start": start, "m": c * base}
                run.update(im.compute_run_stats(run["m"]))
                runs.append(run)
    return runs


def test_eps_recovers_an_exact_power_law(im):
    T0s = np.array([1.0, 1.3, 1.7, 2.2])
    eps = -0.8
    tab = im.aggregate_by_T0(make_runs(im, T0s, T0s**eps), 20_000, 20)
    assert tab.valid_run.all()
    np.testing.assert_allclose(tab.eps_mean, eps, atol=1e-10)
    assert np.all(tab.eps_se < 1e-8)


def test_eps_with_no_residual_degrees_of_freedom_is_nan_not_inf(im):
    """REVIEW A13 (two points): the slope is defined, its SE is not."""
    base = np.random.default_rng(9).standard_normal(20_000)
    base -= base.mean()
    runs = []
    for i, T0 in enumerate((1.0, 2.0)):
        run = {"T0": T0, "i_T0": i, "seed_id": 0, "start": "random", "m": T0**-0.5 * base}
        run.update(im.compute_run_stats(run["m"]))
        runs.append(run)
    with np.errstate(all="ignore"), pytest.warns(RuntimeWarning):
        tab = im.aggregate_by_T0(runs, 20_000, 20)
    assert not np.any(np.isinf(tab.eps_se))


# ----------------------------------------------------------------------------------------------
# Return moments
# ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "kurt"), [
    ("gauss", 3.0), ("t10", 3 + 6 / (10 - 4)), ("laplace", 6.0), ("uniform", 1.8)])
def test_kurtosis_of_known_distributions(im, crm, name, kurt):
    g = np.random.default_rng(10)
    n = 1_000_000
    r = {"gauss": g.standard_normal(n), "t10": g.standard_t(10, n), "laplace": g.laplace(size=n),
         "uniform": g.uniform(-1, 1, n)}[name]
    assert crm.moments(r)["kurtosis"] == pytest.approx(kurt, rel=0.05)
    # stylised_facts also fits a Student-t, which is slow on 1M points
    assert im.stylised_facts(r[:100_000])["kurtosis"] == pytest.approx(kurt, rel=0.10)


def test_gaussian_moments(im, crm):
    r = np.random.default_rng(11).standard_normal(500_000)
    m = crm.moments(r)
    assert m["E|z|"] == pytest.approx(np.sqrt(2 / np.pi), abs=0.005)
    assert m["P(|z|>3)"] == pytest.approx(0.0027, abs=0.0005)
    assert abs(m["AC(r,1)"]) < 0.01
    assert abs(m["AC|r| 1"]) < 0.01
    sf = im.stylised_facts(r[:50_000])
    assert sf["jb_p"] > 0.001
    assert abs(sf["ac_r1"]) < 0.02
    assert sf["t_dof"] > 30


def test_five_day_kurtosis_of_iid_laplace(crm):
    """Sum of 5 iid draws: kurtosis 3 + (6 - 3) / 5 = 3.6."""
    r = np.random.default_rng(12).laplace(size=2_000_000)
    assert crm.moments(r)["kurtosis 5d"] == pytest.approx(3.6, abs=0.06)


def test_student_t_dof_is_recovered(im):
    r = np.random.default_rng(13).standard_t(4, 50_000)
    assert im.stylised_facts(r)["t_dof"] == pytest.approx(4.0, abs=0.4)


def test_hill_on_pareto(crm):
    a = np.random.default_rng(14).pareto(3.0, 400_000) + 1.0     # Pareto with x_min 1, alpha 3
    assert crm.hill(a) == pytest.approx(3.0, abs=0.1)


def test_hill_on_student_t(crm):
    a = np.abs(np.random.default_rng(15).standard_t(4, 400_000))
    assert crm.hill(a) == pytest.approx(4.0, abs=0.8)


def test_hill_cap_for_bounded_returns(crm):
    a = np.abs(np.random.default_rng(16).uniform(-1, 1, 10_000))
    assert crm.hill(a) == crm.HILL_CAP


# ----------------------------------------------------------------------------------------------
# GARCH, GJR, Newey-West, Marchenko-Pastur
# ----------------------------------------------------------------------------------------------


def test_garch_simulation_unconditional_variance_and_kurtosis(crm):
    p = {"omega": 0.05, "a": 0.05, "b": 0.90, "nu": 12.0}
    r = crm.garch_simulate(p, 1_000_000, seed=17)
    assert r.var() == pytest.approx(p["omega"] / (1 - p["a"] - p["b"]), rel=0.03)
    kz = 3 * (p["nu"] - 2) / (p["nu"] - 4)
    s = p["a"] + p["b"]
    kurt = kz * (1 - s**2) / (1 - s**2 - p["a"] ** 2 * (kz - 1))
    assert np.mean((r - r.mean()) ** 4) / r.var() ** 2 == pytest.approx(kurt, rel=0.08)


def test_garch_fit_recovers_parameters(crm):
    p = {"omega": 0.05, "a": 0.08, "b": 0.88, "nu": 6.0}
    r = crm.garch_simulate(p, 4_000, seed=18)
    fit = crm.garch_fit(r)
    assert fit["a"] == pytest.approx(p["a"], abs=0.04)
    assert fit["b"] == pytest.approx(p["b"], abs=0.05)
    assert fit["nu"] == pytest.approx(p["nu"], abs=3.0)


def simulate_gjr(n, seed, mu=0.03, phi=0.05, omega=0.02, a=0.03, g=0.1, b=0.9, nu=7.0):
    rng = np.random.default_rng(seed)
    z = rng.standard_t(nu, n) * np.sqrt((nu - 2) / nu)
    r = np.empty(n)
    s2 = omega / (1 - a - g / 2 - b)
    e_prev, r_prev = 0.0, 0.0
    for t in range(n):
        s2 = omega + (a + g * (e_prev < 0)) * e_prev**2 + b * s2
        e = np.sqrt(s2) * z[t]
        r[t] = mu + phi * r_prev + e
        e_prev, r_prev = e, r[t]
    return r


def test_gjr_fit_recovers_parameters(gx):
    r = simulate_gjr(6_000, seed=19)
    zeros = np.zeros_like(r)
    f = gx.Fit("GJR", r, zeros, zeros).fit(gx.starts_for(r))
    th = dict(zip(f.free, f.theta, strict=True))
    assert th["g"] == pytest.approx(0.1, abs=0.05)
    assert th["b"] == pytest.approx(0.9, abs=0.04)
    assert th["a"] + th["g"] / 2 + th["b"] < 0.999


def test_newey_west_t_is_standard_normal_under_iid(gx):
    rng = np.random.default_rng(20)
    t = np.array([gx.newey_west_t(rng.standard_normal(1_000)) for _ in range(1_000)])
    assert t.std() == pytest.approx(1.0, abs=0.08)
    assert np.mean(np.abs(t) > 1.96) == pytest.approx(0.05, abs=0.025)


def test_marchenko_pastur_edge_for_iid_returns(im, mf):
    N, T = 50, 2_000
    rets = pd.DataFrame(np.random.default_rng(21).standard_normal((T, N)))
    J, _ = im.build_empirical_J(rets, verbose=False)
    net = mf.network_data(rets, J, 0.3)
    assert net["mp_edge"] == pytest.approx((1 + np.sqrt(N / T)) ** 2)
    assert net["evals"][0] == pytest.approx(net["mp_edge"], rel=0.06)
    assert net["edges"] == 0


def test_build_empirical_J_mean_coupling_is_one_tenth(im):
    g = np.random.default_rng(22)
    f = g.standard_normal((1_000, 1))
    rets = pd.DataFrame(f + 0.8 * g.standard_normal((1_000, 12)))
    J, C = im.build_empirical_J(rets, verbose=False)
    np.testing.assert_array_equal(J, J.T)
    assert np.all(np.diag(J) == 0)
    assert J[J > 0].mean() == pytest.approx(0.1)
    np.testing.assert_array_equal(J > 0, (C > 0.3) & ~np.eye(12, dtype=bool))
