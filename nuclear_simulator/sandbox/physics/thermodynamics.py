
# Import libraries
from nuclear_simulator.sandbox.physics.constants import UNIVERSAL_GAS_CONSTANT


def calc_temperature_from_energy(
        U: float,
        m: float, 
        cv: float, 
        T0: float = 0.0, 
        eps: float = 1e-6,
    ) -> float:
    """
    Calculate temperature from internal energy, mass, and specific heat capacity.
    Args:
        U:   [J]        Internal energy
        m:   [kg]       Mass
        cv:  [J/(kg*K)]  Specific heat capacity
        T0:  [K]        Reference temperature (default 0K)
        eps: [-]        Small value to prevent division by zero
    Returns:
        Temperature [K]
    """
    return U / (max(m, eps) * max(cv, eps)) + T0


def calc_energy_from_temperature(
        T: float, 
        m: float, 
        cv: float, 
        T0: float = 0.0
    ) -> float:
    """
    Calculate internal energy from temperature, mass, and specific heat capacity.
    Args:
        T:  [K]        Temperature
        m:  [kg]       Mass
        cv: [J/(kg*K)] Specific heat capacity
        T0: [K]        Reference temperature (default 0K)
    Returns:
        Internal energy [J]
    """
    return m * cv * (T - T0)

