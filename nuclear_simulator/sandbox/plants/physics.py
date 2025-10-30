
# Import libraries
import math


# --- Constants ---

GAS_CONSTANT = 8.3145  # [J/(mol*K)] Universal gas constant
RHO_WATER    = 997.0   # [kg/m3]     Density of water at ~25 °C
RHO_COOLANT  = 700.0   # [kg/m3]     Approximate density of reactor coolant


# --- Thermodynamics ---

def calc_temperature_from_energy(U: float, m: float, cv: float, eps=1e-6) -> float:
    """
    Calculate temperature from internal energy, mass, and specific heat capacity.
    Args:
        U:   [J]        Internal energy
        m:   [kg]       Mass
        cv:  [J/(kg*K)]  Specific heat capacity
        eps: [-]        Small value to prevent division by zero
    Returns:
        Temperature [K]
    """
    return U / (max(m, eps) * max(cv, eps))

def calc_energy_from_temperature(T: float, m: float, cv: float) -> float:
    """
    Calculate internal energy from temperature, mass, and specific heat capacity.
    Args:
        T:  [K]        Temperature
        m:  [kg]       Mass
        cv: [J/(kg*K)] Specific heat capacity
    Returns:
        Internal energy [J]
    """
    return T * m * cv

def calc_pressure_change_from_mass_energy(
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
    # Fractional changes
    dm_frac = dm / max(m, eps)
    dP = K * (dm_frac - alpha * dT)
    return dP

def calc_volume_isobaric(
        m: float,
        T: float,
        rho: float,
        alpha: float,
        T_ref: float = 273.15,
    ) -> float:
    """
    Calculate volume for isobaric (constant pressure) liquids accounting for thermal expansion.
    Args:
        m:       [kg]     Mass
        T:       [K]      Temperature
        rho:     [kg/m3]  Reference density
        alpha:   [1/K]    Thermal expansion coefficient
        T_ref:   [K]      Reference temperature (default: 273.15 K)
    Returns:
        V:       [m3]     Volume
    """
    V = (m / rho) * (1 + alpha * (T - T_ref))
    return V

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
        R:   [J/(mol*K)]  Gas constant (default: 8.3145 J/(mol*K))
        eps: [-]          Small value to prevent division by zero
    Returns:
        P:   [Pa]         Pressure
    """
    P = n * T * GAS_CONSTANT / max(V, eps)
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
        R:   [J/(mol*K)]  Gas constant (default: 8.3145 J/(mol*K))
        eps: [-]          Small value to prevent division by zero
    Returns:
        V:   [m3]         Volume
    """
    V = n * T * GAS_CONSTANT / max(P, eps)
    return V

def calc_density(
        m: float,
        V: float,
        eps: float = 1e-6,
    ) -> float:
    """
    Calculate density from mass and volume.
    Args:
        m:   [kg]   Mass
        V:   [m3]   Volume
        eps: [-]    Small value to prevent division by zero
    Returns:
        rho: [kg/m3] Density
    """
    rho = m / max(V, eps)
    return rho


# --- Pipe flow ---

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

