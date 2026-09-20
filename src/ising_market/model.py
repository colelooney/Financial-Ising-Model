"""
Ising_model.py

Two-dimensional Ising model Monte Carlo simulation with
Glauber and Kawasaki dynamics.

"""

import numpy as np
import matplotlib.pyplot as plt
import math
import matplotlib.animation as animation
import argparse

class IsingModel:
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

    def __init__(self,N,T,start_temp,end_temp,dynamic,uncertainty, J,save_fig):
        """
        N: size of the grid (N x N)
        T: Boltzmann constant times temperature
        dynamic: 'glauber' or 'kawasaki'
        uncertainty: 'bootstrap' or 'jackknife' for error estimation
        J: interaction energy between neighboring spins - defaults to 1
        k: Boltzmann constant
        save_fig: boolean, whether to save generated plots as PNG files
        """
        self.N = N
        self.T = T
        self.start_temp = start_temp
        self.end_temp = end_temp
        self.dynamic = dynamic
        self.uncertainty = uncertainty
        self.J = J
        self.save_fig = save_fig
        self.grid = None
        # self.k = 1.38e-23 # Boltzmann constant

    def pair_energy(self,i,j):
        """

        calculate the pairwise energy of two atoms
        i,j represent spin of respective particles

        returns:
        energy: pairwise energy between two spins
        """

        return -self.J * i * j

    def initialize_grid(self):
        """
        generate random initial grid of spin states, dimension N x N
        sets spin up as +1 and spin down as -1

        returns:
        grid: N x N numpy array of random spiin states
        """

        grid = np.random.rand(self.N,self.N)
        grid[grid >= 0.5] = 1
        grid[grid < 0.5] = -1

        return grid

    def flip_probability(self,delta_energy):
        """
        calculate the probability of a spin flip occuring based on the change in energy and temperature for metropolis algorithm

        returns:

        P: probability of spin flip
        """
        P = math.exp(-delta_energy/self.T)
        return P

    def find_nearest_neighbors(self,i,j):
        """
        finds the nearest neighbors for a given point in the lattice assuming periodic boundary counditions
        returns as list of neighbors

        returns:

        nearest_neighbors: list of tuples representing nearest neighbor coordinates in grid
        """

        nearest_neighbors = [((i+1)%self.N,j),((i-1)%self.N,j),(i,(j+1)%self.N),(i,(j-1)%self.N)]
        return nearest_neighbors

    def glauber_energy(self):
        """
        Calculate the change in energy for a proposed spin flip at a random site (i,j)

        returns:
        delta_energy: change in energy from proposed spin flip
        (i,j): coordinates of the spin to be flipped
        """
        i = np.random.randint(0,self.N)
        j = np.random.randint(0,self.N)
        energy = 0
        flip_energy = 0

        nearest_neighbors = self.find_nearest_neighbors(i,j)

        delta_energy = 2 * self.J * self.grid[i,j] * sum(self.grid[neighbor] for neighbor in nearest_neighbors)
        return delta_energy, (i,j)
        
    def glauber_update(self):
        """
        Perform a single Glauber dynamics update

        returns:
        None: updates the grid in place
        """
        delta_energy, (i,j) = self.glauber_energy()

        if delta_energy <= 0:
            self.grid[(i,j)] = -self.grid[(i,j)]

        elif self.flip_probability(delta_energy) > np.random.rand():
            self.grid[(i,j)] = -self.grid[(i,j)]
        
    def kawasaki_energy(self):
        """
        Calculate the change in energy for a proposed spin swap between two random sites (i_1,j_1) and (i_2,j_2)

        returns:
        delta_energy: change in energy from proposed spin swap
        (i_1,j_1): coordinates of the first spin to be swapped
        (i_2,j_2): coordinates of the second spin to be swapped
        """
        i_1 = np.random.randint(0,self.N)
        j_1 = np.random.randint(0,self.N)

        i_2 = np.random.randint(0,self.N)
        j_2 = np.random.randint(0,self.N)

        energy = 0
        swap_energy = 0

        if self.grid[i_1,j_1] == self.grid[i_2,j_2]: #skip calculation if spins are the same
            return 0, (i_1,j_1),(i_2,j_2)

        nearest_neighbors_one = self.find_nearest_neighbors(i_1,j_1)
        nearest_neighbors_two = self.find_nearest_neighbors(i_2,j_2)

        if (i_2,j_2) not in nearest_neighbors_one:
            for neighbor in nearest_neighbors_one:
                energy += self.pair_energy(self.grid[i_1,j_1],self.grid[neighbor])
                swap_energy += self.pair_energy(self.grid[i_2,j_2],self.grid[neighbor])

            for neighbor in nearest_neighbors_two:
                energy += self.pair_energy(self.grid[i_2,j_2],self.grid[neighbor])
                swap_energy += self.pair_energy(self.grid[i_1,j_1],self.grid[neighbor])

        else:
            # Can further optimise, check math
            for neighbor in nearest_neighbors_one:
                energy += self.pair_energy(self.grid[i_1,j_1],self.grid[neighbor])
                temp_neighbor = (i_1,j_1) if neighbor ==  (i_2,j_2) else neighbor
                swap_energy += self.pair_energy(self.grid[i_2,j_2],self.grid[temp_neighbor])

            for neighbor in nearest_neighbors_two:
                energy += self.pair_energy(self.grid[i_2,j_2],self.grid[neighbor])
                temp_neighbor = (i_2,j_2) if neighbor ==  (i_1,j_1) else neighbor
                swap_energy += self.pair_energy(self.grid[i_1,j_1],self.grid[temp_neighbor])

        delta_energy = swap_energy - energy

        return delta_energy, (i_1,j_1),(i_2,j_2)

    def kawasaki_update(self):
        """
        Perform a single Kawasaki dynamics update

        returns:
        None: updates the grid in place
        """
        delta_energy, (i_1,j_1),(i_2,j_2) = self.kawasaki_energy()

        if delta_energy <= 0:
            self.grid[(i_1,j_1)],self.grid[(i_2,j_2)] = self.grid[(i_2,j_2)], self.grid[(i_1,j_1)]

        elif self.flip_probability(delta_energy) > np.random.rand():
            self.grid[(i_1,j_1)],self.grid[(i_2,j_2)] = self.grid[(i_2,j_2)], self.grid[(i_1,j_1)]

    def bootstrap(self,data,num_samples=1000):
        """
        Perform bootstrap resampling to estimate the standard error of the mean.

        returns:
        standard_error: estimated standard error of the mean from bootstrap resampling
        """
        n = len(data)
        means = []
        for _ in range(num_samples):
            sample = np.random.choice(data, size=n, replace=True)
            means.append(np.mean(sample))
        return np.std(means)
    
    def jackknife(self,data):
        """
        Perform jackknife resampling to estimate the standard error of the mean.

        returns:
        standard_error: estimated standard error of the mean from jackknife resampling
        """
        n = len(data)
        means = []
        for i in range(n):
            sample = np.delete(data, i)
            means.append(np.mean(sample))
        mean_of_means = np.mean(means)
        variance = (n - 1) / n * np.sum((means - mean_of_means) ** 2)
        return np.sqrt(variance)
    
    def determine_magnetisation(self):
        """
        Calculate the total magnetisation and its square for the current grid configuration

        returns:
        M: total magnetisation of current grid configuration
        M_squared: square of the total magnetisation
        """
        M = np.sum(self.grid)
        M_squared = M**2
        return M, M_squared
    
    def average_magnetisation(self):
        """

        Defunct!

        Calculate the average magnetisation and average square magnetisation over multiple sweeps
        10000 sweeps with sampling every 10 sweeps after 100 warm up sweeps

        returns:
        avg_mag: average total magnetisation over sampled sweeps
        avg_mag_squared: average square total magnestisation over sampled sweeps
        """

        # self.grid = self.initalize_grid()
        
        mags = []
        mags_squared = []
        for j in range(100): # warm up steps
            for _ in range(self.N * self.N):
                if self.dynamic == 'glauber':
                    self.glauber_update()
                elif self.dynamic == 'kawasaki':
                    self.kawasaki_update()
        
        for j in range(10000):
            for _ in range(self.N * self.N):
                if self.dynamic == 'glauber':
                    self.glauber_update()
                elif self.dynamic == 'kawasaki':
                    self.kawasaki_update()
            
            if j % 10 == 0:
                # print(f"Sampling at step {j}") #debugging line
                M,M_squared = self.determine_magnetisation()
                mags.append(M)
                mags_squared.append(M_squared)
        avg_mag = sum(mags)/len(mags)
        avg_mag_squared = sum(mags_squared)/len(mags_squared)

        return avg_mag, avg_mag_squared
    
    def magnetic_susceptibility(self, avg_mag, avg_mag_squared):
        """
        Calculate the magnetic susceptibility of the system

        returns:
        chi: magnetic susceptibility
        """
        chi = (avg_mag_squared - avg_mag**2) / (self.N**2 * self.T)
        return chi
    
    # def total_energy(self):
    #     """
    #     Compute the total energy of the lattice for the current configuration
    #     """
    #     E = 0
    #     for i in range(self.N):
    #         for j in range(self.N):
    #             for ni, nj in self.find_nearest_neighbors(i, j):
    #                 E += -self.J * self.grid[i, j] * self.grid[ni, nj]
    #     return E / 2  # remove double counting

    def total_energy(self):
        """
        Compute the total energy of the lattice for the current configuration vectorized version
        """
        E = -self.J * np.sum(self.grid * np.roll(self.grid, -1, axis = 0)
                             + self.grid * np.roll(self.grid, -1, axis = 1))
        return E

    def heat_capacity_from_energies(self, energies):
        # small helper function to calculate heat capacity from list of energies
        E = np.array(energies)
        E_mean = np.mean(E)
        E2_mean = np.mean(E**2)
        return (E2_mean - E_mean**2) / (self.N**2 * self.T**2)

    def heat_capacity(self,energies):
        """
        Calculate the heat capacity of the system and its uncertainty

        returns:
        C: heat capacity
        C_error: uncertainty in heat capacity
        """
        C = self.heat_capacity_from_energies(energies)

        if self.uncertainty == 'bootstrap':
            C_samples = []
            n = len(energies)

            for _ in range(1000):
                resample = np.random.choice(energies,size=n,replace=True)
                C_samples.append(
                    self.heat_capacity_from_energies(resample)
                    )
            C_error = np.std(C_samples)

        elif self.uncertainty == 'jackknife':
            C_samples = []
            n = len(energies)

            for i in range(n):
                resample = np.delete(energies,i)
                C_samples.append(
                    self.heat_capacity_from_energies(resample)
                )
            C_mean = np.mean(C_samples)
            C_error = np.sqrt((n - 1) / n * np.sum((C_samples - C_mean)**2))

        return C, C_error

    def animate(self):
        """
        Animate the evolution of the ising model grid over time

        returns:
        None: displays an animation of the grid evolution
        """
        self.grid = self.initialize_grid()
    
        fig = plt.figure()
        im = plt.imshow(self.grid, animated=True, cmap='binary')
        
        def update_frame(_):
            for _ in range(self.N * self.N):
                if self.dynamic == 'glauber':
                    self.glauber_update()
                elif self.dynamic == 'kawasaki':
                    self.kawasaki_update()
            im.set_array(self.grid)
            return [im]
        
        ani = animation.FuncAnimation(fig, update_frame, frames=1000, interval=20, blit=True, repeat_delay=1000)
        plt.show()

    def run_data_collection(self):
        """
        Run the simulation over a range of temperatures and collect data for plotting

        returns:
        total_mags: list of average magnetisations at each temperature
        susceptibilities: list of magnetic susceptibilities at each temperature
        energies: list of average energies at each temperature
        heat_capacities: list of heat capacities at each temperature
        heat_capacity_errors: list of uncertainties in heat capacities at each temperature
        temperatures: list of temperatures simulated

        """

        # Determine step size for temperature sweep based on start and end temperatures
        temp_range = self.start_temp - self.end_temp
        step_size = -1 * temp_range / 20

        #Inital Grid Generation
        self.grid = self.initialize_grid()

        # Final lists to store data for all temperatures
        total_average_mags = []
        susceptibilities = []
        avg_energies = []
        heat_capacities = []
        heat_capacity_errors = []
        temperatures = []

        self.T = 3.0

        self.update_fn = self.glauber_update if self.dynamic == 'glauber' else self.kawasaki_update
        for i in range(4900): # equilibration steps, warm up time of 5000 sweeps for first grid. 100 extra sweeps in each temp
            for _ in range(self.N * self.N):
                self.update_fn()
        for T in np.arange(self.start_temp, self.end_temp - 0.1 * temp_range, step_size):
            # Subtract 0.1 * range to ensure we include end_temp in the range due to floating point precision issues
            self.T = T
            print(f"Simulating at Temperature: {self.T} with dynamic: {self.dynamic}")
            # Temporary lists to store data at each temperature, reset every temperature
            temp_mags = []
            temp_mags_squared = []
            temp_energies = []

            for i in range(100): # equilibration steps at each temperatures
                for _ in range(self.N * self.N):
                    self.update_fn()
            for i in range(10000): # data collection steps
                for _ in range(self.N * self.N):
                    self.update_fn()
                if i % 10 == 0:
                    if self.dynamic == 'glauber':
                        temp_mag, temp_mag_squared = self.determine_magnetisation()
                        temp_mags.append(temp_mag)
                        temp_mags_squared.append(temp_mag_squared)

                    temp_energies.append(self.total_energy())

            if self.dynamic == 'glauber':
                #Only calculate magnetisation and susceptibility for glauber dynamics
                avg_mag = np.mean(np.abs(temp_mags))
                avg_mag_squared = np.mean(temp_mags_squared)
                chi = self.magnetic_susceptibility(avg_mag, avg_mag_squared)
                total_average_mags.append(avg_mag)
                susceptibilities.append(chi)
            else:
                total_average_mags.append(np.nan)
                susceptibilities.append(np.nan)

            avg_energy = np.mean(temp_energies)
            C, C_error = self.heat_capacity(temp_energies)
            avg_energies.append(avg_energy)
            heat_capacities.append(C)
            heat_capacity_errors.append(C_error)

            temperatures.append(self.T)

        return total_average_mags, susceptibilities, avg_energies, heat_capacities,heat_capacity_errors, temperatures
        
    def plot_data(self, total_mags, susceptibilities, energies,
                heat_capacities, heat_capacity_errors, temperatures):

        plt.rcParams.update({
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "lines.linewidth": 2,
            "figure.dpi": 300
        })

        if self.dynamic == "glauber":
            fig, axes = plt.subplots(2, 2, figsize=(11, 9))
            axes = axes.flatten()
        else:
            fig, axes = plt.subplots(1, 2, figsize=(11, 4))
            axes = axes.flatten()

        # --- Energy ---
        axes[0].plot(temperatures, energies, marker='o', markersize=4)
        axes[0].set_xlabel(r"Temperature $T$")
        axes[0].set_ylabel(r"Total Energy $E$")
        axes[0].grid(alpha=0.3)
        axes[0].set_title("(a) Energy")

        # --- Heat capacity ---
        axes[1].errorbar(
            temperatures,
            heat_capacities,
            yerr=heat_capacity_errors,
            fmt='o-',
            markersize=4,
            capsize=3
        )
        axes[1].set_xlabel(r"Temperature $T$")
        axes[1].set_ylabel(r"Heat Capacity per Spin $C$")
        axes[1].grid(alpha=0.3)
        if self.dynamic == 'glauber':
            axes[1].axvline(x=2.27,color = 'r', linestyle='--', label='Critical Temperature $T_c$')
        axes[1].set_title("(b) Heat capacity")

        if self.dynamic == "glauber":
            # --- Magnetisation ---
            axes[2].plot(temperatures, total_mags, marker='o', markersize=4)
            axes[2].set_xlabel(r"Temperature $T$")
            axes[2].set_ylabel(r"Average Magnetisation $|M|$")
            axes[2].grid(alpha=0.3)
            axes[2].set_title("(c) Magnetisation")

            # --- Susceptibility ---
            axes[3].plot(temperatures, susceptibilities, marker='o', markersize=4)
            axes[3].set_xlabel(r"Temperature $T$")
            axes[3].set_ylabel(r"Susceptibility $\chi$")
            axes[3].axvline(x=2.27,color = 'r', linestyle='--', label='Critical Temperature $T_c$')
            axes[3].grid(alpha=0.3)
            axes[3].set_title("(d) Susceptibility")

        plt.tight_layout()
        if self.save_fig:
            plt.savefig(
                f"ising_plots_{self.dynamic}_{self.uncertainty}_N{self.N}_T{self.start_temp}.png",
                dpi=300,
                bbox_inches="tight"
            )
        plt.show()

    def plot_stored_data(self):
        """
        Docstring for plot_stored_data
        
        :param self: Description
        """
        try:
            data = np.loadtxt(f'ising_data_{self.dynamic}_N{self.N}_T{self.start_temp}.csv', delimiter=',', skiprows=1)
        except FileNotFoundError:
            raise RuntimeError(
                f"No stored data found for dynamic={self.dynamic}, N={self.N}"
            )
        temperatures = data[:, 0]
        total_mags = data[:, 1]
        susceptibilities = data[:, 2]
        energies = data[:, 3]
        heat_capacities = data[:, 4]
        heat_capacity_errors = data[:,5]

        self.plot_data(total_mags, susceptibilities, energies, heat_capacities, heat_capacity_errors, temperatures)


    def store_data(self, total_mags, susceptibilities, energies, heat_capacities,heat_capacity_uncertainty, temperatures):
        """
        Store the collected data in a CSV file
        ising_data_{dynamic}_N{N}.csv

        returns:
        None: saves data to CSV file
        """
        data = np.array([temperatures, total_mags, susceptibilities, energies, heat_capacities,heat_capacity_uncertainty])
        np.savetxt(f'ising_data_{self.dynamic}_N{self.N}_T{self.start_temp}.csv', data.T, delimiter=',', header='Temperature,Average Magnetisation,Magnetic Susceptibility,Average Energy,Heat Capacity', comments='')

    def run(self):
        """
        Run the full simulation: data collection, plotting, and storing

        returns:
        None: executes the full simulation process
    
        """
        total_mags, susceptibilities, energies, heat_capacities, heat_capacity_errors, temperatures = self.run_data_collection()
        self.plot_data(total_mags, susceptibilities, energies, heat_capacities, heat_capacity_errors, temperatures)
        self.store_data(total_mags, susceptibilities, energies, heat_capacities,heat_capacity_errors, temperatures) 
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=
            "Monte Carlo simulation of the 2D Ising model with periodic boundary conditions.\n\n"
            "Supports Glauber (non-conserved magnetisation) and Kawasaki "
            "(conserved magnetisation) dynamics, with thermodynamic observables "
            "computed via Metropolis sampling."
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

    parser.add_argument(
        "--start_temp", "-tmax",
        type = float,
        default = 3.0,
        metavar = "T_MAX",
        help = "Starting temperature for temperature sweeps (default: 3.0), greater than end temp"
    )
    
    parser.add_argument(
        "--end_temp", "-tmin",
        type = float,
        default = 1.0,
        metavar = "T_MIN",
        help = "Ending temperature for temperature sweeps (default: 1.0), less than start temp"
    )

    parser.add_argument(
        "-J", "--coupling",
        type=float,
        default=1.0,
        metavar="J",
        help=(
            "Nearest-neighbour coupling constant. "
            "Positive J corresponds to the ferromagnetic Ising model."
        )
    )


    # --- Algorithmic choices ---
    parser.add_argument(
        "--dynamic",
        choices=["glauber", "kawasaki"],
        default="glauber",
        help=(
            "Choice of Monte Carlo dynamics:\n"
            "  glauber  – single-spin flips (magnetisation not conserved)\n"
            "  kawasaki – spin exchanges (magnetisation conserved)"
        )
    )

    parser.add_argument(
        "--uncertainty",
        choices=["bootstrap", "jackknife"],
        default="bootstrap",
        help=(
            "Statistical method used to estimate uncertainties "
            "in the heat capacity."
        )
    )

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
    parser.add_argument(
        "--save_fig",
        action="store_true",
        help="Save generated plots as high-resolution PNG files."
    )

    args = parser.parse_args()

    
    model = IsingModel(
        N=args.size,
        T=args.temperature,
        start_temp = args.start_temp,
        end_temp = args.end_temp,
        dynamic=args.dynamic,
        uncertainty=args.uncertainty,
        J=args.coupling,
        save_fig=args.save_fig
    )

    if args.mode == 'run':
        model.run()
    elif args.mode == 'animate':
        model.animate()
    elif args.mode == 'plot':
        model.plot_stored_data()