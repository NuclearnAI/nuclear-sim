
# Import libraries
from nuclear_simulator.sandbox.physics.constants import UNIVERSAL_GAS_CONSTANT


def calc_pressure_ideal_gas(
        n: float,
        T: float,
        V: float,
        eps: float = 1e-6,
    ) -> float:
    """
    Calculate pressure using ideal gas law for isovolumetric gases.
    Args:
        n:   [mol]        Number of moles
        T:   [K]          Temperature
        V:   [m3]         Volume
        eps: [-]          Small value to prevent division by zero
    Returns:
        P:   [Pa]         Pressure
    """
    P = n * T * UNIVERSAL_GAS_CONSTANT / max(V, eps)
    return P


def calc_volume_ideal_gas(
        n: float,
        T: float,
        P: float,
        eps: float = 1e-6,
    ) -> float:
    """
    Calculate volume using ideal gas law for isobaric gases.
    Args:
        n:   [mol]        Number of moles
        T:   [K]          Temperature
        P:   [Pa]         Pressure
        eps: [-]          Small value to prevent division by zero
    Returns:
        V:   [m3]         Volume
    """
    V = n * T * UNIVERSAL_GAS_CONSTANT / max(P, eps)
    return V

