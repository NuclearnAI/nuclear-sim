
# Import libraries
import math
from nuclear_simulator.sandbox.physics.constants import UNIVERSAL_GAS_CONSTANT


def calc_incompressible_mass_flow(
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
        P_up:    [Pa]    Upstream pressure
        P_dn:    [Pa]    Downstream pressure
        rho:     [kg/m3] Fluid density (assumed constant/incompressible)
        D:       [m]     Pipe inner diameter
        L:       [m]     Pipe length
        f:       [-]     Darcy friction factor (lumped/assumed)
        K_minor: [-]     Lumped minor-loss coefficient (bends, valves, etc.)
        eps:     [-]     Small number to avoid divide-by-zero
    Returns:
        m_dot:   [kg/s]  Mass flow rate (positive from upstream → downstream)
    """

    # Handle signs
    if P_up < P_dn:
        P_up, P_dn = P_dn, P_up
        sign = -1.0
    else:
        sign = 1.0

    # Calculate flow
    dP = P_up - P_dn
    A = math.pi * (D**2) / 4.0
    K = f * (L / max(D, eps)) + K_minor
    v = math.sqrt( (2.0 * dP) / (max(rho, eps) * max(K, eps)) )
    m_dot = rho * A * v

    # Apply sign
    m_dot *= sign

    # Return flow
    return m_dot


def calc_compressible_mass_flow(
        P_up: float,
        P_dn: float,
        T_up: float,
        T_dn: float,
        gamma: float,
        R: float,
        D: float,
        Cd: float = 0.8,
        eps: float = 1e-9,
    ) -> float:
    """
    Compute gas mass flow through a short element (orifice/valve/nozzle) with automatic choking.
    Symmetric in endpoints: chooses upstream by higher pressure and returns signed flow.

    Args:
        P_up:    [Pa]       Upstream pressure
        P_dn:    [Pa]       Downstream pressure
        T_up:    [K]        Upstream temperature
        T_dn:    [K]        Downstream temperature
        gamma:   [-]        Heat capacity ratio (cp/cv)
        R:       [J/(kg·K)] Specific gas constant
        D:       [m]        Effective throat/port diameter (area = π D²/4)
        Cd:      [-]        Discharge coefficient (default 0.8)
        eps:     [-]        Small number to avoid divide-by-zero

    Returns:
        m_dot:   [kg/s]   Positive from end 1 → end 2
    """

    # Handle signs
    if P_up < P_dn:
        P_up, P_dn = P_dn, P_up
        T_up, T_dn = T_dn, T_up
        sign = -1.0
    else:
        sign = 1.0

    # Clamp to avoid non-physical ratios
    P_up = max(P_up, eps)
    P_dn = max(P_dn, eps)
    T_up = max(T_up, eps)

    # Geometry
    A = math.pi * (D * D) * 0.25

    # Critical pressure ratios
    P_ratio_critical = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    P_ratio = max(eps, P_dn / P_up)

    # Check for choking
    if P_ratio <= P_ratio_critical:
        # Choked isentropic
        m_dot = (
            Cd * A * P_up
            * math.sqrt(gamma / (R * T_up))
            * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
        )
    else:
        # Subcritical isentropic
        term = (2.0 * gamma / (gamma - 1.0)) * (
            P_ratio ** (2.0 / gamma) - P_ratio ** ((gamma + 1.0) / gamma)
        )
        m_dot = Cd * A * P_up * math.sqrt(max(term, 0.0) / (R * T_up))

    # Apply sign
    m_dot *=  sign

    # Return flow
    return m_dot


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



