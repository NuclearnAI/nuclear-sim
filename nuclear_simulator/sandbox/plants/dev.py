
# Import libraries
import time
import pstats
import cProfile
from nuclear_simulator.sandbox.plants.plants import Plant


# Test
def run_simulation():
    """
    Run a powerplant simulation.
    """

    # Create plant
    plant = Plant()

    # Set simulation parameters
    dt = .001
    n_steps = 100_000

    # Simulate for a while
    for i in range(n_steps):
        plant.update(dt)

    # Done
    return


# Run simulation
if __name__ == "__main__":
    with cProfile.Profile() as profiler:
        run_simulation()
    stats = pstats.Stats(profiler)
    stats.sort_stats("tottime")
    stats.print_stats(25)   # print top 25 slowest functions
    print("Simulation complete.")

