"""Calibration pipeline: convergence to a known example (Curie-Weiss), plus REVIEW.md items in
aggregate_by_T0, select_T0, calibrate_parameters and make_figures.consensus_row."""

import numpy as np
import pandas as pd
import pytest
from _helpers import ar1, complete_J, curie_weiss_moments, random_J

C4_20 = 0.962   # mean rolling std (ddof 0, window 20) of iid noise, in units of sigma


def fake_rets(N, seed=0):
    return pd.DataFrame(np.random.default_rng(seed).standard_normal((300, N)) * 0.01)


# ----------------------------------------------------------------------------------------------
# Convergence to a known example: Curie-Weiss, N = 29
# ----------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def cw_cal(im):
    N = 29
    J = complete_J(N)
    with np.errstate(all="ignore"):
        res = im.calibrate_parameters(fake_rets(N), J, n_pilot=10_000, n_burn=2_000, n_seeds=8,
                                      seed=42)
    return N, J, res


def test_cw_grid_is_scaled_by_lambda(cw_cal):
    N, J, res = cw_cal
    assert res["lam"] == pytest.approx((N - 1) / N)
    np.testing.assert_allclose(res["T0_search"][[0, -1]], [0.35 * res["lam"], 1.30 * res["lam"]])


def test_cw_rms_magnetisation_and_binder_match_exact(cw_cal):
    """Every row's pooled sigma_m and Binder ratio R converge to the exact Curie-Weiss values.
    m is even under the Z2 symmetry, so this holds even for runs stuck in one well."""
    N, _, res = cw_cal
    tab = res["T0_table"]
    for _, row in tab.iterrows():
        ex2, ex4 = curie_weiss_moments(N, row.T0)
        assert abs(row.sigma_m_mean - np.sqrt(ex2)) < 4 * row.sigma_m_se + 0.01 * np.sqrt(ex2), \
            f"sigma_m at T0 = {row.T0:.3f}"
        assert abs(row.R_mean - ex4 / ex2**2) < 4 * row.R_se + 0.02, f"R at T0 = {row.T0:.3f}"


def test_cw_regimes_are_ordered_in_temperature(cw_cal):
    """Cold rows are frozen (zero-mean test fails), hot rows mix: frac_z_high falls with T."""
    tab = cw_cal[2]["T0_table"]
    assert tab.frac_z_high.iloc[0] > 0.5
    assert tab.frac_z_high.iloc[-1] <= 0.1
    assert tab.R_mean.iloc[0] < 1.2 and tab.R_mean.iloc[-1] > 2.0


def test_cw_selects_a_row_with_the_exact_elasticity(cw_cal):
    """The selected row's eps = d ln s / d ln T0 should match the exact d ln sigma / d ln T,
    and sigma0 the c4-scaled exact sigma, since thinning makes the samples nearly independent."""
    N, _, res = cw_cal
    assert res["T0"] is not None, "no row selected on the Curie-Weiss network"
    row = res["selection"]["row"]
    T, h = row.T0, 1e-4
    lnsig = lambda t: 0.5 * np.log(curie_weiss_moments(N, t)[0])  # noqa: E731
    eps_exact = (lnsig(T * (1 + h)) - lnsig(T * (1 - h))) / (np.log(1 + h) - np.log(1 - h))
    assert eps_exact < 0
    assert abs(row.eps_mean - eps_exact) < 3 * row.eps_se + 0.15
    assert res["sigma0"] == pytest.approx(C4_20 * np.sqrt(curie_weiss_moments(N, T)[0]), rel=0.10)
    assert res["k"] >= 1


def test_cw_calibration_is_reproducible(im, cw_cal):
    N, J, res = cw_cal
    again = im.calibrate_parameters(fake_rets(N), J, T0_search=res["T0_search"][-3:],
                                    n_pilot=3_000, n_burn=500, n_seeds=2, seed=7)
    twice = im.calibrate_parameters(fake_rets(N), J, T0_search=res["T0_search"][-3:],
                                    n_pilot=3_000, n_burn=500, n_seeds=2, seed=7)
    pd.testing.assert_frame_equal(again["T0_table"], twice["T0_table"])


# ----------------------------------------------------------------------------------------------
# Synthetic aggregate_by_T0 inputs
# ----------------------------------------------------------------------------------------------


def run_dict(im, T0, i_T0, seed_id, start, m):
    run = {"T0": T0, "i_T0": i_T0, "seed_id": seed_id, "start": start, "m": m}
    run.update(im.compute_run_stats(m))
    return run


def centred(x):
    return x - x.mean()


def test_equilibration_fails_when_starts_disagree(im):
    """Two runs per start, random and up differing by a factor 5 in scale: flagged."""
    g = np.random.default_rng(0)
    runs = [run_dict(im, 1.0, 0, s, "random", centred(g.standard_normal(20_000)))
            for s in range(2)]
    runs += [run_dict(im, 1.0, 0, s, "up", 5 * centred(g.standard_normal(20_000)))
             for s in range(2)]
    assert not im.aggregate_by_T0(runs, 20_000, 20).equilibrated[0]


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A1: with one run per start the SE is NaN and the check passes")
def test_equilibration_fails_when_starts_disagree_with_one_seed(im):
    g = np.random.default_rng(0)
    runs = [run_dict(im, 1.0, 0, 0, "random", centred(g.standard_normal(20_000))),
            run_dict(im, 1.0, 0, 0, "up", 5 * centred(g.standard_normal(20_000)))]
    with np.errstate(all="ignore"):
        assert not im.aggregate_by_T0(runs, 20_000, 20).equilibrated[0]


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A11: an anti-correlated series gives tau_int < 0")
def test_tau_int_positive_for_alternating_m(im):
    """N = 1, J = 0: the single spin flips on every attempt, so m alternates +1, -1."""
    m = im._run_pilot(np.zeros((1, 1)), 1.0, np.random.default_rng(0), "random", 0, 2_000)
    assert np.all(m[1:] == -m[:-1])
    assert im.compute_run_stats(m)["tau_int"] > 0


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A11: tau_int < 0 gives a thinning interval k <= 0")
def test_thinning_interval_at_least_one_for_alternating_m(im):
    m = np.tile([1.0, -1.0], 5_000)
    runs = [run_dict(im, 1.0, 0, s, st, m.copy()) for s in range(2) for st in ("random", "up")]
    with np.errstate(all="ignore"):
        tab = im.aggregate_by_T0(runs, 10_000, 20)
    assert tab.k[0] >= 1


def test_constant_m_row_is_not_valid(im):
    """REVIEW A12: a frozen run (all spins up) gives NaN ACF and z = inf; the row must fail."""
    runs = [run_dict(im, 0.1, 0, s, st, np.ones(5_000)) for s in range(2)
            for st in ("random", "up")]
    with np.errstate(all="ignore"):
        tab = im.aggregate_by_T0(runs, 5_000, 20)
    assert not tab.valid_run[0]
    sel = im.select_T0(tab, verbose=False)
    assert sel["T0"] is None


@pytest.mark.xfail(strict=True, raises=np.linalg.LinAlgError,
                   reason="REVIEW A13: a valid neighbour whose s is undefined at this row's k "
                          "leaves one x value and a singular OLS")
def test_eps_with_undefined_neighbour_does_not_raise(im):
    # row 0 (T0 = 1, ln T0 = 0): AR(1) rho 0.9, tau ~ 9.5, k ~ 29
    # row 1: short iid runs (400 samples), valid, but m[::29] has fewer than 20 points
    slow = centred(ar1(20_000, 0.9, seed=1))
    fast = centred(np.random.default_rng(2).standard_normal(400))
    runs = [run_dict(im, 1.0, 0, s, st, slow.copy()) for s in range(2) for st in ("random", "up")]
    runs += [run_dict(im, 2.0, 1, s, st, fast.copy()) for s in range(2)
             for st in ("random", "up")]
    with np.errstate(all="ignore"):
        tab = im.aggregate_by_T0(runs, 20_000, 20)
    assert tab.valid_run.all()
    assert np.isnan(tab.eps_mean[0])


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A14: eps neighbours are taken in list order, not by T0")
def test_eps_neighbours_follow_temperature_not_list_order(im):
    """T0 grid given as [1, 4, 2]. s = exp(-(ln T)^2): the row at T = 2 should use T = 1 and 4."""
    T0s = np.array([1.0, 4.0, 2.0])
    scales = np.exp(-np.log(T0s) ** 2)
    base = centred(np.random.default_rng(3).standard_normal(20_000))
    runs = [run_dict(im, T0, i, s, st, c * base) for i, (T0, c) in enumerate(zip(T0s, scales,
                                                                                strict=True))
            for s in range(2) for st in ("random", "up")]
    tab = im.aggregate_by_T0(runs, 20_000, 20)
    x, y = np.log(T0s), np.log(scales)
    slope_all = np.polyfit(x, y, 1)[0]
    assert tab.eps_mean[2] == pytest.approx(slope_all, abs=1e-8)


def test_select_t0_picks_most_negative_upper_bound(im):
    tab = pd.DataFrame({
        "i_T0": [0, 1, 2], "T0": [1.0, 1.2, 1.4], "equilibrated": [True] * 3,
        "frac_converged": [1.0] * 3, "n_s_valid": [4] * 3, "n_eff": [4_000.0] * 3,
        "ac1_mean": [0.0] * 3, "ac1_se": [0.01] * 3, "frac_z_high": [0.0] * 3,
        "eps_mean": [-0.5, -0.9, 0.2], "eps_se": [0.05, 0.05, 0.05], "k": [5.0] * 3,
        "n_runs": [4] * 3})
    sel = im.select_T0(tab, verbose=False)
    assert sel["T0"] == 1.2 and sel["k"] == 5


# ----------------------------------------------------------------------------------------------
# calibrate_parameters inputs and outputs
# ----------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def tiny(im):
    J = random_J(6, seed=21)
    lam = np.linalg.eigvalsh(J).max()
    return J, lam


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A21: pilot seeds are keyed by grid position i_T0")
def test_pilot_runs_do_not_depend_on_the_rest_of_the_grid(im, tiny):
    J, lam = tiny
    kw = dict(n_pilot=2_000, n_burn=200, n_seeds=2, seed=5)
    with np.errstate(all="ignore"):
        a = im.calibrate_parameters(fake_rets(6), J, T0_search=np.array([lam, 1.2 * lam]), **kw)
        b = im.calibrate_parameters(fake_rets(6), J,
                                    T0_search=np.array([0.9 * lam, lam, 1.2 * lam]), **kw)
    ma = [r["m"] for r in a["runs"] if r["T0"] == lam]
    mb = [r["m"] for r in b["runs"] if r["T0"] == lam]
    for x, y in zip(ma, mb, strict=True):
        np.testing.assert_array_equal(x, y)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A6: calibrate_parameters does not return kappa (target_vol is "
                          "unused)")
def test_calibration_returns_kappa(im, tiny):
    J, lam = tiny
    with np.errstate(all="ignore"):
        res = im.calibrate_parameters(fake_rets(6), J, T0_search=np.array([lam, 1.2 * lam]),
                                      n_pilot=2_000, n_burn=200, n_seeds=2)
    assert "kappa" in res


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A8: a J with no edges fails inside np.geomspace with an "
                          "unrelated message")
def test_no_edges_gives_a_clear_error(im):
    with pytest.raises(ValueError, match="edge|lambda|coupling"):
        im.calibrate_parameters(fake_rets(5), np.zeros((5, 5)), n_pilot=500, n_burn=50,
                                n_seeds=2)


def test_build_empirical_J_single_stock(im):
    """REVIEW A8 predicted a ZeroDivisionError here; numpy gives a NaN density (only printed)
    with a RuntimeWarning instead, and J is correct."""
    with np.errstate(all="ignore"):
        J, _ = im.build_empirical_J(fake_rets(1), verbose=False)
    assert J.shape == (1, 1) and J[0, 0] == 0


@pytest.mark.xfail(strict=True, raises=TypeError,
                   reason="REVIEW A9: sigma0=None (no row selected) fails at float(None)")
def test_simulate_deployed_rejects_missing_calibration(im, tiny):
    J, lam = tiny
    with pytest.raises(ValueError):
        im.simulate_deployed(J, lam, 1, 0.5, None, 50, rng=np.random.default_rng(0))


def test_simulate_deployed_alpha_zero_keeps_T_fixed(im, tiny):
    J, lam = tiny
    out = im.simulate_deployed(J, lam, 2, 0.0, 0.3, 300, n_burn=20,
                               rng=np.random.default_rng(1))
    assert np.all(out["T"] == lam)
    assert out["clip_frac"] == 0


def test_simulate_deployed_T_stays_in_clip(im, tiny):
    J, lam = tiny
    out = im.simulate_deployed(J, lam, 1, 5.0, 1e-3, 300, n_burn=20,
                               rng=np.random.default_rng(2), T_clip=(0.5, 2.0))
    assert np.all(out["T"] >= 0.5 * lam - 1e-12) and np.all(out["T"] <= 2.0 * lam + 1e-12)
    assert out["clip_frac"] > 0


# ----------------------------------------------------------------------------------------------
# make_figures.consensus_row
# ----------------------------------------------------------------------------------------------


def seed_table(k, s, eps=-0.6, fail="none"):
    return {"table": pd.DataFrame({
        "T0": [1.0], "k": [float(k)], "s_mean": [s], "eps_mean": [eps],
        "eps_ucb": [eps + 0.1], "first_failure": [fail]})}


def test_consensus_row_single_seed(mf):
    cons = mf.consensus_row({42: seed_table(10, 0.1)})
    assert cons["k"] == 10 and cons["sigma0"] == pytest.approx(0.1)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A2: k is the median over seeds, a clock no seed measured")
def test_consensus_k_is_a_measured_clock(mf):
    cons = mf.consensus_row({42: seed_table(10, 0.1), 43: seed_table(30, 0.3)})
    assert cons["k"] in (10, 30)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A2: sigma0 and eps average in seeds where the row failed")
def test_consensus_ignores_seeds_where_the_row_failed(mf):
    cal = {42: seed_table(10, 0.1), 43: seed_table(10, 0.1),
           44: seed_table(10, 5.0, eps=0.4, fail="eps_negative")}
    cons = mf.consensus_row(cal)
    assert cons["sigma0"] == pytest.approx(0.1)
    assert cons["eps"] == pytest.approx(-0.6)
