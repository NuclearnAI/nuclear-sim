
# Import libraries
import math
from nuclear_simulator.sandbox.physics.constants import UNIVERSAL_GAS_CONSTANT


def calc_saturation_temperature(
        P: float,
        L: float,
        P0: float,
        T0: float,
        MW: float,
    )-> float:
    """
    Calculate saturation temperature using the Clausius-Clapeyron relation.
    Args:
        P:  [Pa]       Pressure
        L:  [J/kg]     Latent heat of vaporization
        P0: [Pa]       Reference pressure
        T0: [K]        Reference temperature
        MW:  [kg/mol]  Molar weight of the fluid
    Returns:
        T_sat: [K] Saturation temperature at pressure P
    """
    Rv    = UNIVERSAL_GAS_CONSTANT / MW
    C     = math.log(P0) + (L / (Rv * T0))
    T_sat = L / (Rv * (C - math.log(P)))
    return T_sat


def calc_saturation_pressure(
        T: float,
        L: float,
        P0: float,
        T0: float,
        MW: float,
    ) -> float:
    """
    Calculate saturation pressure using the Clausius-Clapeyron relation.
    Args:
        T:  [K]        Temperature
        L:  [J/kg]     Latent heat of vaporization
        P0: [Pa]       Reference pressure
        T0: [K]        Reference temperature
        MW:  [kg/mol]  Molar weight of the fluid
    Returns:
        P_sat: [Pa] Saturation pressure at temperature T
    """
    Rv    = UNIVERSAL_GAS_CONSTANT / MW
    P_sat = P0 * math.exp((L / Rv) * (1.0 / T0 - 1.0 / T))
    return P_sat
