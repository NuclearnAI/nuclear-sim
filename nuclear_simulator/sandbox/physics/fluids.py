
# Import libraries
import math
import random
from nuclear_simulator.sandbox.physics.constants import UNIVERSAL_GAS_CONSTANT


def calc_incompressible_mass_flow(
        P1: float,
        P2: float,
        rho: float,
        D: float,
        L: float,
        f: float = 0.0,
        K_minor: float = 0.0,
        eps: float = 1e-6,
    ) -> float:
    """
    Compute mass flow through a pipe from pressure drop using incompressible Darcy-Weisbach.
    Automatically handles flow direction based on pressure difference.

    Args:
        P1:      [Pa]    Pressure on first side
        P2:      [Pa]    Pressure on other side
        rho:     [kg/m3] Fluid density (assumed constant/incompressible)
        D:       [m]     Pipe inner diameter
        L:       [m]     Pipe length
        f:       [-]     Darcy friction factor (lumped/assumed)
        K_minor: [-]     Lumped minor-loss coefficient (bends, valves, etc.)
        eps:     [-]     Small number to avoid divide-by-zero

    Returns:
        m_dot:   [kg/s]  Mass flow rate (positive from 1 -> 2)
    """

    # Handle signs
    if P1 < P2:
        P1, P2 = P2, P1
        sign = -1.0
    else:
        sign = 1.0

    # Clamp inputs
    rho = max(rho, eps)
    D   = max(D, eps)

    # Calculate flow
    dP = P1 - P2
    A = math.pi * (D**2) / 4.0
    K = f * (L / D) + K_minor
    K = max(K, eps)
    v = math.sqrt( (2.0 * dP) / (rho * K) )
    m_dot = rho * A * v

    # Apply sign
    m_dot *= sign

    # Return flow
    return m_dot


def calc_compressible_mass_flow(
        P1: float,
        P2: float,
        T1: float,
        T2: float,
        MW: float,
        D: float,
        L: float,
        f: float = 0.0,
        K_minor: float = 0.0,
        eps: float = 1e-6,
    ) -> float:
    """
    Compute mass flow through a pipe from pressure drop using compressible Darcy-Weisbach.
    Automatically handles flow direction based on pressure difference.

    Args:
        P1:      [Pa]     Pressure on first side
        P2:      [Pa]     Pressure on other side
        T1:      [K]      Temperature on first side
        T2:      [K]      Temperature on other side
        MW:      [kg/mol] Molar weight of the gas
        gamma:   [-]      Specific heat ratio (cp/cv) of the gas
        D:       [m]      Pipe inner diameter
        L:       [m]      Pipe length
        f:       [-]      Darcy friction factor (lumped/assumed)
        K_minor: [-]      Lumped minor-loss coefficient (bends, valves, etc.)
        eps:     [-]      Small number to avoid divide-by-zero

    Returns:
        m_dot:   [kg/s]   Positive from end 1 -> end 2
    """

    # Handle signs
    if P1 < P2:
        P1, P2 = P2, P1
        T1, T2 = T2, T1
        sign = -1.0
    else:
        sign = 1.0

    # Clamp to avoid non-physical ratios
    P1 = max(P1, eps)
    P2 = max(P2, eps)
    T1 = max(T1, eps)
    T2 = max(T2, eps)

    # Calculate variables
    T      = (T1 + T2) / 2
    A      = math.pi * (D**2) / 4.0
    K_t    = f * (L / D) + K_minor
    R_spec = UNIVERSAL_GAS_CONSTANT / MW

    # Isothermal compressible Darcy-Weisbach
    dP2 = P1**2 - P2**2
    m_dot = A * math.sqrt(dP2 / max(K_t * R_spec * T, eps))

    # Apply sign
    m_dot *=  sign

    # Return flow
    return m_dot

