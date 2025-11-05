
# Import libraries
import math
from nuclear_simulator.sandbox.physics.constants import UNIVERSAL_GAS_CONSTANT


def calc_pipe_mass_flow(
        P_up: float,
        P_dn: float,
        rho: float,
        D: float,
        L: float,
        f: float = 0.0,
        K_minor: float = 0.0,
        eps: float = 1e-6,
    ) -> float:
    """
    Compute mass flow through a pipe from pressure drop using Darcy-Weisbach.
    Args:
        P_up:    [Pa]    Upstream static pressure
        P_dn:    [Pa]    Downstream static pressure
        rho:     [kg/m3] Fluid density (assumed constant/incompressible)
        D:       [m]     Pipe inner diameter
        L:       [m]     Pipe length
        f:       [-]     Darcy friction factor (lumped/assumed)
        K_minor: [-]     Lumped minor-loss coefficient (bends, valves, etc.)
        eps:     [-]     Small number to avoid divide-by-zero
    Returns:
        m_dot:   [kg/s]  Mass flow rate (positive from upstream → downstream)
    """

    # Get pressure drop
    dP = P_up - P_dn
    if dP <= 0.0:
        return 0.0

    # Calculate mass flow
    A = math.pi * (D**2) / 4.0
    K = f * (L / max(D, eps)) + K_minor
    v = math.sqrt( (2.0 * dP) / (max(rho, eps) * max(K, eps)) )
    m_dot = rho * A * v

    # Return mass flow
    return m_dot


def calc_pressure_change_from_mass_temperature(
        m: float,
        dm: float,
        dT: float,
        K: float,
        alpha: float,
        eps: float = 1e-6,
    ) -> float:
    """
    Calculate pressure change for an incompressible fluid node
    from changes in mass and temperature.
    Args:
        m:     [kg]     Current mass
        dm:    [kg]     Change in mass over the timestep
        dT:    [K]      Change in temperature over the timestep
        K:     [Pa]     Bulk modulus (stiffness of fluid)
        alpha: [1/K]    Volumetric thermal expansion coefficient
        eps:   [-]      Small value to prevent divide-by-zero
    Returns:
        dP:    [Pa]     Pressure change for this timestep
    """
    dm_frac = dm / max(m, eps)
    dP = K * (dm_frac - alpha * dT)
    return dP


def calc_saturation_temperature(
        P: float,
        L: float,
        P0: float,
        T0: float,
        M: float,
    )-> float:
    """
    Calculate saturation temperature using the Clausius-Clapeyron relation.
    Args:
        P:  [Pa]      Pressure
        L:  [J/kg]    Latent heat of vaporization
        P0: [Pa]      Reference pressure
        T0: [K]       Reference temperature
        M:  [kg/mol]  Molar mass of the fluid
    Returns:
        T_sat: [K] Saturation temperature at pressure P
    """
    Rv    = UNIVERSAL_GAS_CONSTANT / M
    C     = math.log(P0) + (L / (Rv * T0))
    T_sat = L / (Rv * (C - math.log(P)))
    return T_sat


def calc_saturation_pressure(
        T: float,
        L: float,
        P0: float,
        T0: float,
        M: float,
    ) -> float:
    """
    Calculate saturation pressure using the Clausius-Clapeyron relation.
    Args:
        T:  [K]       Temperature
        L:  [J/kg]    Latent heat of vaporization
        P0: [Pa]      Reference pressure
        T0: [K]       Reference temperature
        M:  [kg/mol]  Molar mass of the fluid
    Returns:
        P_sat: [Pa] Saturation pressure at temperature T
    """
    Rv    = UNIVERSAL_GAS_CONSTANT / M
    P_sat = P0 * math.exp((L / Rv) * (1.0 / T0 - 1.0 / T))
    return P_sat



