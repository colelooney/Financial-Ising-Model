"""
Ising_model.py

Network-based financial ising model

"""

import numpy as np
import matplotlib.pyplot as plt
import math
import matplotlib.animation as animation
import argparse
import networkx as nx
from scipy import stats
import yfinance as yf
import os

FIGURES_DIR= "results/figures"
os.makedirs(FIGURES_DIR,exist_ok=True)

class FinancialIsingModel:
    """
    Two-dimensional Ising model with periodic boundary conditions.

    Conventions
    -----------
    - Spins s_i ∈ {+1, -1}
    - Hamiltonian: H = -J ∑_{⟨ij⟩} s_i s_j
    - Temperature T is measured in units where k_B = 1
    - Energies returned by `total_energy` are total energies (not per spin)
    - Magnetisation M = ∑ s_i
    """

    def __init__(self, N, network_type, T0, kappa, alpha, h0,rng = None):
        """
        N: Number of Agents
        T: Initial Temperature (Uncertainty)
        self.T0: baseline Temperature
        kappa: Price impact factor
        alpha: Volatility feedback strength
        h0: External field (news/macro pressure)

        """
        self.N = N
        self.T = T0
        self.T0 = T0
        self.kappa = kappa # Price impact factor
        self.alpha = alpha #Volatiltiy feedback strenght
        self.h = h0 # extrenal field (news/macro pressure)
        self.network_type = network_type
        self.sigma0 = None # baseline volatility for feedback scaling
        self.h_trend = 0.0 # sensitivity of external field to recent returns
        self.use_leverage = False
        self.lev_frac     = 0.1
        self.rng = rng if rng is not None else np.random.default_rng()
        self.sweeps_per_step = 1

        self.spins = None
        self.J = None
        self.m_prev = None
        self.neighbors = {} #adjacency list to store neigbors for faster lookup


        self.price = 100.0 # current price level
        self.ret_hist = []          # log-return time series
        self.vol_hist = []          # realised volatility history
        self.T_hist   = []          # effective temperature history
        self.spin_hist= []          # periodic spin snapshots
        self.price_hist = []
        self.m_hist = []


    def initialize_spins(self,start = 'random'):
        if start == 'random':
            spins = self.rng.choice([-1, 1], size=self.N)
        if start == 'up':
            spins = np.ones(self.N, dtype=int)
        self.m_prev = 0
        return spins

    def build_network(self, m=3):
        if self.network_type == 'empirical':
            raise RuntimeError(
                "Use build_empirical_network(J) for empirical network type."
            )
        if self.network_type == 'erdos_renyi':
            G = nx.erdos_renyi_graph(self.N, p=0.1)
        elif self.network_type == 'barabasi_albert':
            G = nx.barabasi_albert_graph(self.N, m=m)
        elif self.network_type == 'small_world':
            G = nx.watts_strogatz_graph(self.N, k=6, p=0.1)

        # Adjacency list: O(1) neighbour lookup during simulation
        self.neighbors = {i: list(G.neighbors(i)) for i in G.nodes}

        # Coupling matrix: J[i,j] for connected pairs
        self.J = np.zeros((self.N, self.N))
        for i, j in G.edges:
            w = self.rng.uniform(0.01, 0.05)   # or from empirical data
            self.J[i, j] = w
            self.J[j, i] = w                   # symmetric (undirected network)

    def build_empirical_network(self, J_empirical):
        """
        Load an empirically-derived coupling matrix instead of a random network.
        J_empirical must be an N×N numpy array.
        """
        assert J_empirical.shape == (self.N, self.N), \
            f"J shape {J_empirical.shape} doesn't match N={self.N}"

        self.J = J_empirical.copy()

        # Rebuild adjacency list from non-zero entries in J
        self.neighbors = {
            i: list(np.where(self.J[i] > 0)[0])
            for i in range(self.N)
        }

        n_edges = np.count_nonzero(self.J) // 2
        print(f"  Empirical network loaded: {n_edges} edges")

    def get_neighbors(self,i):
        return self.neighbors[i]

    def flip_probability(self,delta_energy):
        """
        calculate the probability of a spin flip occuring based on the change in energy and temperature for metropolis algorithm

        returns:

        P: probability of spin flip
        """
        P = math.exp(-delta_energy/self.T)
        return P


    def glauber_energy(self):
        """
        Calculate the change in energy for a proposed spin flip at a random site (i,j)

        returns:
        delta_energy: change in energy from proposed spin flip
        (i): coordinate of the spin to be flipped
        """
        i = self.rng.integers(self.N)

        nbrs = self.get_neighbors(i)
        neighbor_field = np.sum(self.J[i, nbrs] * self.spins[nbrs])

        delta_E = 2 * self.spins[i] * (neighbor_field + self.h)
        return delta_E, (i)
        
    def glauber_update(self):
        """
        Perform a single Glauber dynamics update

        returns:
        None: updates the grid in place
        """
        delta_energy, (i) = self.glauber_energy()

        if delta_energy <= 0:
            self.spins[(i)] = -self.spins[(i)]

        elif self.flip_probability(delta_energy) > self.rng.random():
            self.spins[(i)] = -self.spins[(i)]
        
    def market_sentiment(self):
        """Normalised magnetisation: net order imbalance ∈ [-1, +1]"""
        return np.sum(self.spins) / self.N
        

    def compute_return(self):
        # Net order imbalance = magnetisation / N,  range [-1, +1]
        m = np.sum(self.spins) / self.N

        # Log-return proportional to imbalance
        # kappa is price impact — tune to match target volatility level
        r = self.kappa * (m)

        self.price *= np.exp(r)
        self.price_hist.append(self.price)
        self.ret_hist.append(r)
        self.m_hist.append(m)
        # self.m_prev = m
        return r
        
    def update_temperature(self, window=20):
        if len(self.ret_hist) < window:
            return

        sigma = np.std(self.ret_hist[-window:])

        if self.sigma0 is None:          # first time we have enough history
            self.sigma0 = sigma if sigma > 0 else 1e-6
            return                       # don't update T yet, just set baseline

        self.T = self.T0 * (1.0 + self.alpha * sigma / self.sigma0)
        self.T_hist.append(self.T)
        self.vol_hist.append(sigma)

    def update_external_field(self, window=10):
        if len(self.ret_hist) < window:
            return

        # Positive recent returns → buy pressure → h > 0
        # h_trend controls sensitivity; keep small (0.1–0.5) initially
        trend  = np.mean(self.ret_hist[-window:])
        self.h = self.h_trend * trend

    def leverage_cascade(self, threshold=0.05):
        # If the last return is a large loss, force long agents to sell
        # Models margin calls / stop-losses / risk-limit breaches
        if len(self.ret_hist) < 2:
            return
        if self.ret_hist[-1] < -threshold:
            long_agents = np.where(self.spins == 1)[0]
            n_forced    = int(self.lev_frac * len(long_agents))
            forced      = self.rng.choice(long_agents, n_forced, replace=False)
            self.spins[forced] = -1              # forced sell

    def magnetic_susceptibility(self, avg_mag, avg_mag_squared):
        """
        Calculate the magnetic susceptibility of the system

        returns:
        chi: magnetic susceptibility
        """
        chi = (avg_mag_squared - avg_mag**2) / (self.N * self.T)
        return chi
    
    def system_energy(self):
        """Total system energy: -0.5 * sum_ij J[i,j] * s_i * s_j"""
        return -0.5 * float(self.spins @ self.J @ self.spins)
    
    def run_sweep(self, record_spins=False):
        # N single-agent update attempts = one Monte Carlo sweep
        for _ in range(self.sweeps_per_step):
            for _ in range(self.N):
                delta_E, i = self.glauber_energy()
                if delta_E <= 0 or self.rng.random() < np.exp(-delta_E / self.T):
                    self.spins[i] = -self.spins[i]

        # Financial updates run once per sweep (not per flip)
        r = self.compute_return()
        self.update_temperature()
        self.update_external_field()
        if self.use_leverage:
            self.leverage_cascade()  # gate behind use_leverage flag

        if record_spins:
            self.spin_hist.append(self.spins.copy())

    def analyse_returns(self):
        r = np.array(self.ret_hist)

        # Kurtosis > 3 → fat tails (S&P500: typically 5–20)
        kurt = stats.kurtosis(r, fisher=False)

        # Jarque-Bera: p < 0.05 → reject normality
        jb_stat, jb_p = stats.jarque_bera(r)

        # Fit Student-t: degrees of freedom ν ~ 3–5 for equities
        nu, mu, sigma = stats.t.fit(r)

        # Volatility clustering: AC of |r_t| should be positive for many lags
        abs_r  = np.abs(r)
        vol_ac = [np.corrcoef(abs_r[:-k], abs_r[k:])[0,1] for k in range(1, 21)]

        # AC of raw r_t should be ~0 (efficient markets)
        ret_ac = [np.corrcoef(r[:-k], r[k:])[0,1] for k in range(1, 21)]

        return {'kurtosis': kurt, 'jb_p': jb_p,
                't_dof': nu,   'vol_ac': vol_ac, 'ret_ac': ret_ac}
    
    def rolling_susceptibility(self, window=50):
        # chi = (⟨m²⟩ - ⟨m⟩²) / T   — peaks near the critical point
        # Rising chi = more correlated agents = rising systemic fragility
        chi_ts = []
        m_ts   = [np.mean(s) for s in self.spin_hist]
        for t in range(window, len(m_ts)):
            window_m = m_ts[t-window:t]
            chi = (np.mean(np.array(window_m)**2) -
                np.mean(window_m)**2)
            chi_ts.append(chi)
        return np.array(chi_ts)

def plot_return_distributions(N=50, T0=1.0, kappa=0.2, n_sweeps=5000,
                               network_type='erdos_renyi',
                               alphas=(0.0, 1.0, 3.0, 6.0),J_matrix=None):
    """
    Run the model at several alpha values and plot return distributions
    against a fitted Gaussian. Shows how volatility feedback fattens tails.
    """

    fig, axes = plt.subplots(1, len(alphas), figsize=(4 * len(alphas), 4),
                             sharey=False)
    fig.suptitle("Return distributions: effect of volatility feedback (α)",
                 fontsize=13)

    for ax, alpha in zip(axes, alphas):

        # Fresh model for each alpha
        model = FinancialIsingModel(
            N=N, network_type=network_type,
            T0=T0, kappa=kappa, alpha=alpha, h0=0.0
        )
        model.spins = model.initialize_spins()
        if J_matrix is not None:
            model.build_empirical_network(J_matrix)
        else:
            model.build_network()

        # Burn-in: let the system reach a stationary state before recording
        for _ in range(200):
            model.run_sweep()

        # Reset histories so burn-in returns don't contaminate the sample
        model.ret_hist   = []
        model.vol_hist   = []
        model.T_hist     = []
        model.price      = 100.0
        model.price_hist = []
        model.m_hist     = []
        # model.sigma0    = None   # re-initialise baseline vol on clean data

        for _ in range(n_sweeps):
            model.run_sweep()

        r = np.array(model.ret_hist)

        # --- Histogram (density=True so it integrates to 1) ---
        ax.hist(r, bins=60, density=True, color='steelblue',
                alpha=0.6, label='Simulated returns')

        # --- Fitted Gaussian overlay ---
        mu, sigma = r.mean(), r.std()
        x = np.linspace(r.min(), r.max(), 400)
        ax.plot(x, stats.norm.pdf(x, mu, sigma),
                color='crimson', linewidth=2, label='Fitted Gaussian')

        # --- Annotations ---
        kurt  = stats.kurtosis(r, fisher=False)   # excess = kurt - 3
        _, jb_p = stats.jarque_bera(r)

        ax.set_title(f"α = {alpha}", fontsize=12)
        ax.set_xlabel("Log return")
        ax.set_ylabel("Density")
        textstr = f"Kurtosis: {kurt:.2f}\nJB p: {jb_p:.3f}"
        ax.text(0.97, 0.95, textstr, transform=ax.transAxes,
                fontsize=9, verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        ax.legend(fontsize=8)


    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR,"return_distributions.png"), dpi=300)
    plt.show()

def plot_volatility_clustering(N=50, T0=1.0, kappa=0.2, n_sweeps=5000,
                                network_type='erdos_renyi',
                                alphas=(0.0, 3.0, 6.0),J_matrix=None):
    """
    Tests for volatility clustering: AC(|r_t|) should be positive and slow-decaying.
    AC(r_t) should be ~0. The gap between them is the signature of clustering.
    """
    fig, axes = plt.subplots(1, len(alphas), figsize=(5 * len(alphas), 4))
    fig.suptitle("Volatility clustering: autocorrelation of returns vs |returns|",
                 fontsize=13)

    for ax, alpha in zip(axes, alphas):
        model = FinancialIsingModel(
            N=N, network_type=network_type,
            T0=T0, kappa=kappa, alpha=alpha, h0=0.0
        )
        model.spins = model.initialize_spins()
        if J_matrix is not None:
            model.build_empirical_network(J_matrix)
        else:
            model.build_network()

        for _ in range(500):          # burn-in
            model.run_sweep()

        model.ret_hist   = []
        model.vol_hist   = []
        model.T_hist     = []
        model.price_hist = []
        model.price      = 100.0
        model.m_hist     = []  

        for _ in range(n_sweeps):
            model.run_sweep()

        results = model.analyse_returns()
        lags = range(1, 21)

        ax.plot(lags, results['vol_ac'], 'o-', color='steelblue',
                linewidth=2, markersize=4, label='AC of |rₜ| (vol clustering)')
        ax.plot(lags, results['ret_ac'], 's--', color='crimson',
                linewidth=2, markersize=4, label='AC of rₜ (return)')
        ax.axhline(0, color='black', linewidth=0.8, linestyle=':')

        # Significance bands: ±1.96/√n
        sig = 1.96 / np.sqrt(n_sweeps)
        ax.axhline( sig, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
        ax.axhline(-sig, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)

        ax.set_title(f"α = {alpha}", fontsize=12)
        ax.set_xlabel("Lag (sweeps)")
        ax.set_ylabel("Autocorrelation")
        ax.set_ylim(-0.15, 0.5)
        ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR,"volatility_clustering.png"), dpi=300)
    plt.show()

def plot_susceptibility_vs_returns(N=50, T0=1.0, kappa=0.2,
                                    n_sweeps=2000, alpha=3.0,
                                    network_type='erdos_renyi', J_matrix=None):
    """
    Plots rolling susceptibility aligned with returns.
    Tests whether chi spikes precede large market moves.
    """
    model = FinancialIsingModel(
        N=N, network_type=network_type,
        T0=T0, kappa=kappa, alpha=alpha, h0=0.0
    )
    model.spins = model.initialize_spins()
    if J_matrix is not None:
        model.build_empirical_network(J_matrix)
    else:
        model.build_network()

    for _ in range(500):
        model.run_sweep()

    model.ret_hist   = []
    model.vol_hist   = []
    model.T_hist     = []
    model.spin_hist  = []
    model.price_hist = []
    model.price      = 100.0
    model.h_hist     = []

    # record_spins=True every sweep — needed for rolling_susceptibility
    for _ in range(n_sweeps):
        model.run_sweep(record_spins=True)

    chi = model.rolling_susceptibility(window=50)

    # Align: chi starts at index 50 of spin_hist
    ret_array = np.array(model.ret_hist)
    aligned_rets = ret_array[50:]           # match chi length

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    fig.suptitle(f"Rolling susceptibility vs returns  (α={alpha})", fontsize=13)

    sweeps = np.arange(len(chi))

    ax1.plot(sweeps, chi, color='darkorange', linewidth=1.2)
    ax1.set_ylabel("Susceptibility χ")
    ax1.set_title("Rolling susceptibility — peaks signal fragility")
    ax1.grid(alpha=0.3)

    ax2.plot(sweeps, aligned_rets, color='steelblue', linewidth=0.8)
    ax2.set_ylabel("Log return")
    ax2.set_xlabel("Sweep")
    ax2.set_title("Log returns")
    ax2.grid(alpha=0.3)

    # Shade large negative return events so you can visually check
    # whether chi spikes preceded them
    threshold = np.percentile(aligned_rets, 1)   # bottom 5% = extreme moves
    for i, r in enumerate(aligned_rets):
        if r < threshold:
            ax1.axvline(i, color='red', alpha=0.3, linewidth=0.8)
            ax2.axvline(i, color='red', alpha=0.3, linewidth=0.8)

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR,"susceptibility_vs_returns.png"), dpi=300)
    plt.show()

def fetch_market_data(tickers, start='2005-01-01', end='2008-01-01'):
    """
    Download adjusted close prices and compute log returns.
    Returns the return DataFrame and correlation matrix.
    """
    print(f"Downloading {len(tickers)} tickers from {start} to {end}...")
    prices = yf.download(tickers, start=start, end=end, 
                         auto_adjust=True, progress=False)['Close']
    
    # Drop any tickers that failed to download
    prices = prices.dropna(axis=1, how='all')
    valid_tickers = list(prices.columns)
    if len(valid_tickers) < len(tickers):
        dropped = set(tickers) - set(valid_tickers)
        print(f"  Warning: dropped {dropped} (no data)")

    rets = np.log(prices / prices.shift(1)).dropna()
    print(f"  {len(valid_tickers)} tickers, {len(rets)} trading days")
    return rets, valid_tickers

def build_empirical_J(rets, threshold=0.3,normalize=True,verbose=True):
    """
    Build coupling matrix from return correlations.
    Only keeps pairs with correlation above threshold — sparse financial network.
    Returns J matrix, the full correlation matrix, and edge count.
    """
    C = rets.corr().values
    N = C.shape[0]

    J = np.where(C > threshold, C, 0.0)
    np.fill_diagonal(J, 0.0)

    if normalize:
        nonzero = J[J>0]
        if len(nonzero) > 0:
            J = J * (0.1 / nonzero.mean())


    n_edges = np.count_nonzero(J) // 2
    density = n_edges / (N * (N - 1) / 2)
    if verbose:
        print(f"  Network: N={N}, edges={n_edges}, density={density:.2%}, "
          f"threshold={threshold}")
    return J, C

def _run_pilot(J,T0,rng,start,n_burn,n_pilot):
    N = J.shape[0]
    model = FinancialIsingModel(N=N,network_type='empirical',T0=T0,
                                kappa=1.0,alpha=0.0,h0=0.0,rng=rng)

    model.spins = model.initialize_spins(start=start)
    model.build_empirical_network(J)
    for _ in range(n_burn):
        model.run_sweep()

    model.ret_hist = []
    model.m_hist = []
    for _ in range(n_pilot):
        model.run_sweep()
    return np.array(model.m_hist)

def calibrate_parameters(rets, J_empirical, target_vol=0.01,
                          T0_search=None, n_pilot=10000, n_seeds=8,
                          n_burn=2000,seed=42,window=20):
    """
    Derives kappa and T0 from real return data.

    target_vol: daily vol to match (S&P500 ≈ 0.01 per day)
    T0_search:  list of T0 values to scan; auto-set if None
    n_pilot:    sweeps per pilot run

    Returns dict with calibrated kappa, T0, sigma0, and diagnostics.
    """
    N = J_empirical.shape[0]

    # --- Step 1: measure empirical baseline vol ---
    sigma_empirical = rets.std().mean()   # mean daily vol across tickers
    print(f"\nEmpirical mean daily vol: {sigma_empirical:.4f}")
    print(f"Target vol:               {target_vol:.4f}")

    # --- Step 2: scan T0 to find disordered regime ---
    # At alpha=0, kurtosis should be close to 3 (Gaussian)
    # Too low T0 → kurtosis >> 3 even at alpha=0 (system ordered)
    # Too high T0 → all dynamics wash out

    lam = np.linalg.eigvalsh(J_empirical).max() # mean-field crossover estimate
    if T0_search is None:
        T0_search = np.geomspace(0.3 * lam, 1.3 * lam, 17)
    print(f"lambda_max(J) = {lam:.4f}")
    print(f"Scanning T0 in {T0_search.round(4)}")

    kurtosis_by_T0 = {}
    m_std_by_T0    = {}

    runs = []
    for i_T0,T0 in enumerate(T0_search):
        for seed_id in range(n_seeds):
            for start in ['random','up']:
                run_rng = np.random.default_rng([seed, i_T0, seed_id, 0 if start == 'random' else 1])
                m = _run_pilot(J_empirical, T0, run_rng, start, n_burn, n_pilot)
                runs.append({'T0': T0, 'i_T0': i_T0, 'seed_id': seed_id, 'start': start, 'm': m})

    print(f"\n{len(runs)} pilot runs completed.")

    return {
        'runs':            runs,
        'T0_search':       T0_search,
        'lam':             lam,
        'sigma_empirical': sigma_empirical,
    }

def compute_run_stats(m, window):
    """
    compute RMS magnetisation, fourth moment, order parameter, ACF - autocorrelation, integrated correlation time, thinning interval
    zero-mean test, lag-1 autocorrelation of the thinned returns, mean sliding window volatility,
    """
    sokal_constant = 6
    m_c = m - np.mean(m) # mean centred m
    sigma_m = np.sqrt(np.mean(m**2))
    R = np.mean(m**4)/(np.mean(m**2)**2) # Binder cumulant, essentially the kurtosis of the magnetisation distribution
    q = abs(np.mean(m))/sigma_m # order parameter, essentially the mean magnetisation normalised by the RMS magnetisation
    acf = np.correlate(m_c,m_c,mode='full')[len(m_c)-1:] / np.correlate(m_c,m_c,mode='full')[len(m_c)-1]
    max_lag = min(len(acf)-1,len(m)//50)

    tau_int = 0
    converged = False

    for W in range(1,max_lag):
        tau_int = 0.5 + acf[1:W+1].sum()
        if W >= sokal_constant * tau_int:
            converged = True
            break

    threshold = 0.1
    below = acf[1:] < threshold
    if below.any():
        k_star = np.argmax(below) + 1
    else:
        k_star = None

    z = abs(np.mean(m))/(np.std(m)*np.sqrt(2*tau_int/len(m))) # zero-mean test statistic
    if k_star is not None:
        r = m[::k_star]
        r_c = r - np.mean(r)
        acf_r = np.correlate(r_c,r_c,mode='full')[len(r_c)-1:]/np.correlate(r_c,r_c,mode='full')[len(r_c)-1]
        if len(r) >= window:
            s = np.lib.stride_tricks.sliding_window_view(r,window).std(axis=1).mean()
        else:
            s = None
    else:
        r = None
        acf_r = None
        s = None

    return {
    'sigma_m': sigma_m,
    'R': R,
    'q': q,
    'mean_m': np.mean(m),
    'acf': acf,
    'tau_int': tau_int,
    'converged': converged,
    'k_star': k_star,
    'z': z,
    'r': r,
    'acf_r': acf_r,
    's': s,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=
            "Network-based financial ising model"
        )

    # --- System parameters ---
    parser.add_argument(
        "-N", "--size",
        type=int,
        default=50,
        metavar="N",
        help="Linear lattice size. The system contains N×N spins."
    )

    parser.add_argument(
        "-T", "--temperature",
        type=float,
        default=2.5,
        metavar="T",
        help=(
            "Temperature of the system (Units of K_B T). "
            "For temperature sweeps, this value is used as the initial temperature."
        )
    )

    parser.add_argument("--network", choices=["erdos_renyi","barabasi_albert","small_world"],
                        default="erdos_renyi")
    parser.add_argument("--kappa",  type=float, default=0.01,
                        help="Price impact coefficient")
    parser.add_argument("--alpha",  type=float, default=0.0,
                        help="Volatility feedback strength (0 = no feedback)")
    parser.add_argument("--h0",     type=float, default=0.0,
                        help="Initial external field (news/macro pressure)")

    # --- Execution mode ---
    parser.add_argument(
        "--mode",
        choices=["run", "animate", "plot"],
        default="animate",
        help=(
            "Execution mode:\n"
            "  run     – run simulation, collect data, plot and store results\n"
            "  animate – animate lattice evolution at fixed temperature\n"
            "  plot    – plot previously stored data from CSV files"
        )
    )

    # --- Output options ---

    args = parser.parse_args()

    

    TICKERS = [
        'AAPL','MSFT','AMZN','INTC','CSCO',          # tech (pre-2005)
        'JPM','BAC','GS','WFC','C',                   # financials
        'XOM','CVX','COP',                             # energy
        'JNJ','PFE','UNH','MRK',                       # healthcare
        'WMT','HD','MCD',                              # consumer
        'CAT','GE','MMM','BA',                         # industrials
        'DIS','TWX',                                   # media (TWX = Time Warner)
        'AMD','IBM','ORCL','TXN'                       # semiconductors
    ]

    rets, valid_tickers = fetch_market_data(
        TICKERS, start='2005-01-01', end='2008-01-01'
    )
    N = len(valid_tickers)