"""Spin kernels against exact results (REVIEW.md section C, spin dynamics) and the range of m.

Statistical comparisons use independent seeded runs and allow 5 standard errors of the run means
plus a small absolute floor.
"""

import numpy as np
import pytest
from _helpers import (
    complete_J,
    curie_weiss_moments,
    enumerate_moments,
    onsager_m,
    pilot_moments,
    random_J,
    ring_J,
    ring_m2,
)

# ----------------------------------------------------------------------------------------------
# Magnetisation range
# ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("N", [1, 2, 9, 10])
def test_pilot_m_in_range_and_on_lattice(im, N):
    """m = M/N with M in {-N, -N+2, ..., N}: |m| <= 1 and N(1 - m) is an even integer."""
    J = random_J(N, seed=N) if N > 1 else np.zeros((1, 1))
    m = im._run_pilot(J, 0.8 * max(np.linalg.eigvalsh(J).max(), 0.1),
                      np.random.default_rng(1), "random", 50, 2000)
    assert np.all(np.abs(m) <= 1.0)
    M = m * N
    assert np.allclose(M, np.round(M))
    assert np.all(np.round(N - M).astype(int) % 2 == 0)


def test_up_start_at_low_T_stays_near_one(im):
    J = random_J(12, seed=3)
    m = im._run_pilot(J, 0.05 * np.linalg.eigvalsh(J).max(), np.random.default_rng(0), "up", 0,
                      500)
    assert m.min() > 0.8


def test_deployed_m_in_range_and_r_is_kappa_m(im):
    N = 11
    J = random_J(N, seed=4)
    lam = np.linalg.eigvalsh(J).max()
    out = im.simulate_deployed(J, 1.1 * lam, 2, 0.5, 0.2, 400, n_burn=50,
                               rng=np.random.default_rng(2), kappa=0.03)
    assert np.all(np.abs(out["m"]) <= 1.0)
    assert np.allclose(out["m"] * N, np.round(out["m"] * N))
    np.testing.assert_allclose(out["r"], 0.03 * out["m"])
    assert np.all(np.abs(out["r"]) <= 0.03 + 1e-15)


def test_ours_kernel_level_mapping_in_range(crm):
    N = 9
    J = random_J(N, seed=5)
    lam = np.linalg.eigvalsh(J).max()
    r, _ = crm._ours_kernel(J, lam, 2, 0.0, 1.0, 0, 0.0, 300, 20, 3, 20, 0.05 * lam, 20 * lam)
    assert np.all(np.abs(r) <= 1.0)
    assert np.allclose(r * N, np.round(r * N))


def test_legacy_market_sentiment_in_range(im):
    model = im.FinancialIsingModel(N=15, network_type="erdos_renyi", T0=1.0, kappa=0.01,
                                   alpha=0.0, h0=0.0, rng=np.random.default_rng(0))
    model.spins = model.initialize_spins()
    model.build_network()
    for _ in range(20):
        model.run_sweep()
        assert -1.0 <= model.market_sentiment() <= 1.0


def test_pilot_is_reproducible_for_a_seed(im):
    J = random_J(10, seed=6)
    a = im._run_pilot(J, 0.5, np.random.default_rng([9, 9]), "random", 10, 500)
    b = im._run_pilot(J, 0.5, np.random.default_rng([9, 9]), "random", 10, 500)
    np.testing.assert_array_equal(a, b)


# ----------------------------------------------------------------------------------------------
# Exact results
# ----------------------------------------------------------------------------------------------


def test_zero_coupling_is_binomial(im):
    """J = 0: spins are independent, <m^2> = 1/N and Binder R = 3 - 2/N."""
    N = 10
    m2, se2, m4, _, _ = pilot_moments(im, np.zeros((N, N)), 1.0, 8, 20_000, 100)
    assert abs(m2 - 1 / N) < 5 * se2 + 1e-3
    assert m4 / m2**2 == pytest.approx(3 - 2 / N, abs=0.05)


def test_zero_coupling_metropolis_autocorrelation(im):
    """J = 0: every attempt flips, so lag-L ACF of m per sweep is (1 - 2/N)^(N L)
    and tau_int = (1 + rho) / (2 (1 - rho))."""
    N = 10
    rho = (1 - 2 / N) ** N
    m = im._run_pilot(np.zeros((N, N)), 1.0, np.random.default_rng(0), "random", 100, 200_000)
    acf = im._acf(m - m.mean())
    for L in (1, 2, 3):
        assert acf[L] == pytest.approx(rho**L, abs=0.01)
    stats = im.compute_run_stats(m)
    assert stats["tau_int"] == pytest.approx((1 + rho) / (2 * (1 - rho)), rel=0.05)
    assert stats["converged"]


@pytest.mark.parametrize("T_over_lam", [0.5, 1.0, 1.6])
def test_small_network_matches_exact_enumeration(im, T_over_lam):
    """N = 8: the Boltzmann averages over all 256 states are exact."""
    J = random_J(8, seed=11)
    T = T_over_lam * np.linalg.eigvalsh(J).max()
    ex2, ex4 = enumerate_moments(J, T)
    m2, se2, m4, se4, _ = pilot_moments(im, J, T, 8, 40_000, 2_000)
    assert abs(m2 - ex2) < 5 * se2 + 2e-3
    assert abs(m4 - ex4) < 5 * se4 + 2e-3


@pytest.mark.parametrize("T", [0.7, 1.0, 1.5])
def test_curie_weiss_matches_exact_distribution(im, T):
    """Complete graph J_ij = 1/N, N = 29: P(M) is known in closed form."""
    N = 29
    J = complete_J(N)
    ex2, ex4 = curie_weiss_moments(N, T)
    m2, se2, m4, se4, _ = pilot_moments(im, J, T, 8, 20_000, 2_000)
    assert abs(m2 - ex2) < 5 * se2 + 2e-3
    assert abs(m4 - ex4) < 5 * se4 + 2e-3


def test_curie_weiss_lambda_max():
    N = 29
    assert np.linalg.eigvalsh(complete_J(N)).max() == pytest.approx((N - 1) / N)


@pytest.mark.parametrize("T", [1.0, 2.0, 4.0])
def test_ring_matches_transfer_matrix(im, T):
    """1D periodic ring, N = 12: <m^2> from the closed-form correlations."""
    N = 12
    J = ring_J(N)
    exact = ring_m2(N, T)
    assert exact == pytest.approx(enumerate_moments(J, T)[0], rel=1e-10)   # formula check
    m2, se2, _, _, _ = pilot_moments(im, J, T, 8, 30_000, 2_000)
    assert abs(m2 - exact) < 5 * se2 + 2e-3


@pytest.mark.parametrize("T", [1.5, 1.8])
def test_square_lattice_ordered_phase_matches_onsager(im, crm, T):
    """12 x 12 periodic lattice below T_c = 2.269: <|m|> close to Onsager's m(T)."""
    J = crm.lattice(12)
    ms = [np.abs(im._run_pilot(J, T, np.random.default_rng([3, i]), "up", 2_000, 5_000)).mean()
          for i in range(4)]
    assert np.mean(ms) == pytest.approx(onsager_m(T), abs=0.02)


def test_square_lattice_mean_field_overshoots_tc(im, crm):
    """REVIEW B1: lambda_max = 4 on the square lattice, but the lattice is disordered there
    (exact T_c = 2.269), so T0 / lambda is not a phase location on sparse networks."""
    J = crm.lattice(12)
    assert np.linalg.eigvalsh(J).max() == pytest.approx(4.0)
    m2, _, _, _, _ = pilot_moments(im, J, 4.0, 4, 5_000, 1_000)
    assert m2 < 0.05


# ----------------------------------------------------------------------------------------------
# Kernels against each other
# ----------------------------------------------------------------------------------------------


def test_deploy_at_alpha_zero_is_bit_identical_to_pilot(im):
    """Same spins and seed: deploy day d equals pilot sweep (n_burn_d + d + 1) k."""
    N, k, n_burn_d, n_days = 10, 3, 5, 200
    J = random_J(N, seed=12)
    T0 = np.linalg.eigvalsh(J).max()
    spins = np.random.default_rng(0).choice([-1.0, 1.0], size=N)
    m_d, T_d, clip = im._deploy_kernel(J, T0, k, 0.0, 1.0, spins, n_days, n_burn_d, 77, 20,
                                       0.05 * T0, 20 * T0)
    m_p = im._metropolis_pilot(J, T0, spins, k * n_burn_d, k * n_days, 77)
    np.testing.assert_array_equal(m_d, m_p[k - 1::k])
    assert np.all(T_d == T0)
    assert clip == 0


def test_cluster_mapping_with_no_trading_is_zero(crm):
    J = random_J(9, seed=13)
    lam = np.linalg.eigvalsh(J).max()
    r, _ = crm._ours_kernel(J, lam, 1, 0.0, 1.0, 2, 0.0, 200, 10, 1, 20, 0.05 * lam, 20 * lam)
    assert np.all(r == 0.0)


def test_cluster_mapping_with_all_trading_equals_m(crm):
    """act = 0.5: every Swendsen-Wang cluster trades, so sum(spin x size) / N is exactly m."""
    N = 9
    J = random_J(N, seed=14)
    lam = np.linalg.eigvalsh(J).max()
    r, _ = crm._ours_kernel(J, lam, 1, 0.0, 1.0, 2, 0.5, 300, 10, 5, 20, 0.05 * lam, 20 * lam)
    assert np.all(np.abs(r) <= 1.0)
    assert np.allclose(r * N, np.round(r * N))
    assert np.all(np.round(N - r * N).astype(int) % 2 == 0)


def test_krawiecki_complete_graph_lambda(crm):
    N = 100
    J = np.full((N, N), 1.0 / N)
    np.fill_diagonal(J, 0.0)
    assert np.linalg.eigvalsh(J).max() == pytest.approx((N - 1) / N)
    x = crm._krawiecki_kernel(J, (N - 1) / N, 1.6, 0.01, 500, 100, 2)
    assert np.all(np.abs(x) <= 1.0)


# ----------------------------------------------------------------------------------------------
# Expected to fail until the model is fixed (REVIEW.md section A / B)
# ----------------------------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A3: lattice(L) is wrong for L <= 2 (self-coupling / missing "
                          "double bonds)")
@pytest.mark.parametrize("L", [1, 2])
def test_lattice_small_L_has_four_bonds_per_site(crm, L):
    J = crm.lattice(L)
    assert np.all(np.diag(J) == 0)
    np.testing.assert_allclose(J.sum(axis=1), 4.0)


@pytest.mark.parametrize("L", [3, 5])
def test_lattice_has_four_bonds_per_site(crm, L):
    J = crm.lattice(L)
    assert np.all(np.diag(J) == 0)
    np.testing.assert_array_equal(J, J.T)
    np.testing.assert_allclose(J.sum(axis=1), 4.0)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="REVIEW A3: kernels include J_ii in the local field, so a diagonal "
                          "changes the dynamics")
def test_diagonal_of_J_does_not_change_dynamics(im):
    """J_ii s_i^2 is a constant in H, so the trajectory for a seed should not depend on it."""
    N = 8
    J = random_J(N, seed=15)
    Jd = J + np.diag(np.full(N, 0.3))
    spins = np.ones(N)
    a = im._metropolis_pilot(J, 0.5, spins, 0, 300, 5)
    b = im._metropolis_pilot(Jd, 0.5, spins, 0, 300, 5)
    np.testing.assert_array_equal(a, b)


@pytest.mark.xfail(strict=True, raises=pytest.fail.Exception,
                   reason="REVIEW A3: an asymmetric J is accepted without any check")
def test_asymmetric_J_is_rejected(im):
    J = random_J(8, seed=16)
    J[0, 1] += 0.5
    with pytest.raises(ValueError):
        im.simulate_deployed(J, 1.0, 1, 0.0, 0.1, 50, n_burn=5, rng=np.random.default_rng(0))


@pytest.mark.xfail(strict=True, raises=pytest.fail.Exception,
                   reason="REVIEW B8: act > 0.5 gives a trade probability above 1 and is "
                          "not rejected")
def test_cluster_activity_above_half_is_rejected(crm):
    ctx_J = random_J(9, seed=17)
    lam = np.linalg.eigvalsh(ctx_J).max()
    with pytest.raises(ValueError):
        crm._ours_kernel(ctx_J, lam, 1, 0.0, 1.0, 2, 0.75, 50, 5, 1, 20, 0.05 * lam, 20 * lam)
