
# Import libraries
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
    n_burnin = 100000
    n_steps = 100000

    # Burn-in (stababalize from initial conditions)
    for i in range(n_burnin):
        plant.update(dt)

    # Simulate for a while
    for i in range(n_steps):
        plant.update(dt)

    # Done
    return


# Run simulation
if __name__ == "__main__":
    run_simulation()
    print("Simulation complete.")

