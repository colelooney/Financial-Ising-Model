"""Exact reference values and small builders shared by the tests (not a test module)."""

import itertools

import numpy as np
from scipy.special import gammaln


def random_J(N, seed, density=0.6):
    """Symmetric, non-negative couplings with a zero diagonal."""
    rng = np.random.default_rng(seed)
    A = rng.uniform(0.05, 0.3, (N, N)) * (rng.random((N, N)) < density)
    J = np.triu(A, 1)
    return J + J.T


def ring_J(N, J=1.0):
    out = np.zeros((N, N))
    for i in range(N):
        out[i, (i + 1) % N] = out[(i + 1) % N, i] = J
    return out


def complete_J(N, J=1.0):
    out = np.full((N, N), J / N)
    np.fill_diagonal(out, 0.0)
    return out


def enumerate_moments(J, T):
    """Exact <m^2> and <m^4> for H = -1/2 s.J.s by summing over all 2^N states."""
    N = J.shape[0]
    S = np.array(list(itertools.product([-1.0, 1.0], repeat=N)))
    E = -0.5 * np.einsum("si,ij,sj->s", S, J, S)
    w = np.exp(-(E - E.min()) / T)
    w /= w.sum()
    m = S.mean(axis=1)
    return float(w @ m**2), float(w @ m**4)


def curie_weiss_moments(N, T, J=1.0):
    """Exact <m^2>, <m^4> for J_ij = J/N (i != j): H = -J (M^2 - N) / (2N)."""
    d = np.arange(N + 1)
    M = N - 2 * d
    logw = gammaln(N + 1) - gammaln(d + 1) - gammaln(N - d + 1) + J * (M**2 - N) / (2 * N * T)
    w = np.exp(logw - logw.max())
    w /= w.sum()
    m = M / N
    return float(w @ m**2), float(w @ m**4)


def ring_m2(N, T, J=1.0):
    """Exact <m^2> on a periodic ring: (1/N) sum_r (t^r + t^(N-r)) / (1 + t^N), t = tanh(J/T)."""
    t = np.tanh(J / T)
    r = np.arange(N)
    return float(np.sum((t**r + t ** (N - r)) / (1 + t**N)) / N)


def onsager_m(T):
    """Spontaneous magnetisation of the infinite 2D square lattice (J = 1), T < T_c."""
    return float((1 - np.sinh(2 / T) ** -4) ** 0.125)


def ar1(n, rho, seed, burn=1000):
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n + burn)
    x = np.empty(n + burn)
    x[0] = e[0]
    for t in range(1, n + burn):
        x[t] = rho * x[t - 1] + e[t]
    return x[burn:]


def pilot_moments(im, J, T, n_runs, n_sweeps, n_burn, seed=0, start="random"):
    """Per-run <m^2>, <m^4> from the pilot kernel: (mean m2, se m2, mean m4, se m4, runs)."""
    m2, m4, runs = [], [], []
    for i in range(n_runs):
        m = im._run_pilot(J, T, np.random.default_rng([seed, i]), start, n_burn, n_sweeps)
        runs.append(m)
        m2.append(np.mean(m**2))
        m4.append(np.mean(m**4))
    m2, m4 = np.array(m2), np.array(m4)
    se = lambda x: x.std(ddof=1) / np.sqrt(len(x))  # noqa: E731
    return m2.mean(), se(m2), m4.mean(), se(m4), runs
