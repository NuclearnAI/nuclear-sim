
# Import libraries
import math
from scipy.optimize import brentq
from nuclear_simulator.sandbox.physics.constants import UNIVERSAL_GAS_CONSTANT


def calc_boiling_specific_energy_gas(
        T: float,
        T0: float,
        u0_gas: float,
        u0_liquid: float,
        cv_liquid: float,
    ) -> float:
    """
    Calculate internal specific energy of gas phase at saturation.
    Args:
        T:          [K]        Temperature
        T0:         [K]        Reference temperature
        u0_gas:     [J/kg]     Reference internal specific energy of gas at T0
        u0_liquid:  [J/kg]     Reference internal specific energy of liquid at T0
        cv_liquid:  [J/(kg·K)] Specific heat capacity of liquid phase
    Returns:
        u_gas:  [J/kg]     Internal specific energy of gas phase
    """
    L = u0_gas - u0_liquid
    u_liq = calc_boiling_specific_energy_liquid(
        T=T,
        T0=T0,
        u0_liquid=u0_liquid,
        cv_liquid=cv_liquid,
    )
    u_gas = L + u_liq
    return u_gas


def calc_boiling_specific_energy_liquid(
        T: float,
        T0: float,
        u0_liquid: float,
        cv_liquid: float,
    ) -> float:
    """
    Calculate internal specific energy of liquid phase at saturation.
    Args:
        T:          [K]        Temperature
        T0:         [K]        Reference temperature
        u0_liquid:  [J/kg]     Reference internal specific energy of liquid at T0
        cv_liquid:  [J/(kg·K)] Specific heat capacity of liquid phase
    Returns:
        u_liquid:  [J/kg]     Internal specific energy of liquid phase
    """
    u_liquid = u0_liquid + cv_liquid * (T - T0)
    return u_liquid


def calc_boiling_temperature_from_pressure(
        P: float,
        T0: float,
        P0: float,
        u0_gas: float,
        u0_liquid: float,
        molecular_weight: float,
    ) -> float:
    """
    Calculate saturation temperature at given pressure using Clausius-Clapeyron relation.
    Args:
        P:                  [Pa]        Pressure
        T0:                 [K]         Reference temperature
        P0:                 [Pa]        Reference pressure
        u0_gas:            [J/kg]      Reference internal specific energy of gas at T0
        u0_liquid:         [J/kg]      Reference internal specific energy of liquid at T0
        molecular_weight:  [kg/mol]    Molecular weight (for ideal gas calculations)
    Returns:
        T_sat:  [K]  Saturation temperature
    """
    L = u0_gas - u0_liquid
    R = UNIVERSAL_GAS_CONSTANT / molecular_weight
    T_sat = 1 / ((1 / T0) - (R / L) * math.log(P / P0))
    return T_sat


def calc_boiling_pressure_from_temperature(
        T: float,
        T0: float,
        P0: float,
        u0_gas: float,
        u0_liquid: float,
        molecular_weight: float,
    ) -> float:
    """
    Calculate saturation pressure at given temperature using Clausius-Clapeyron relation.
    Args:
        T:                  [K]         Temperature
        T0:                 [K]         Reference temperature
        P0:                 [Pa]        Reference pressure
        u0_gas:            [J/kg]      Reference internal specific energy of gas at T0
        u0_liquid:         [J/kg]      Reference internal specific energy of liquid at T0
        molecular_weight:  [kg/mol]    Molecular weight (for ideal gas calculations)
    Returns:
        P_sat:  [Pa]  Saturation pressure
    """
    L = u0_gas - u0_liquid
    R = UNIVERSAL_GAS_CONSTANT / molecular_weight
    P_sat = P0 * math.exp((L / R) * ((1 / T0) - (1 / T)))
    return P_sat


def calc_boiling_density_gas(
        T: float,
        T0: float,
        P0: float,
        u0_gas: float,
        u0_liquid: float,
        molecular_weight: float,
    ) -> float:
    """
    Calculate density of gas phase at saturation.
    Args:
        T:                  [K]        Temperature
        T0:                 [K]        Reference temperature
        P0:                 [Pa]       Reference pressure
        u0_gas:            [J/kg]      Reference internal specific energy of gas at T0
        u0_liquid:         [J/kg]      Reference internal specific energy of liquid at T0
        molecular_weight:  [kg/mol]    Molecular weight (for ideal gas calculations)
    Returns:
        rho_gas:  [kg/m^3]  Density of gas phase
    """
    P_sat = calc_boiling_pressure_from_temperature(
        T=T,
        T0=T0,
        P0=P0,
        u0_gas=u0_gas,
        u0_liquid=u0_liquid,
        molecular_weight=molecular_weight,
    )
    R = UNIVERSAL_GAS_CONSTANT / molecular_weight
    rho_gas = P_sat / (R * T)
    return rho_gas


def calc_boiling_temperature(
        m: float,
        U: float,
        V: float,
        T0: float,
        P0: float,
        u0_gas: float,
        u0_liquid: float,
        cv_liquid: float,
        rho_liquid: float,
        molecular_weight: float,
    ) -> float:
    """
    Calculate equilibrium temperature for a boiling system,
    given total mass, internal energy, and volume.

    Args:
        m:                [kg]       Total mass
        U:                [J]        Total internal energy
        V:                [m^3]      Total volume
        T0:               [K]        Reference temperature
        P0:               [Pa]       Reference pressure
        u0_gas:           [J/kg]     Reference gas specific energy at T0
        u0_liquid:        [J/kg]     Reference liquid specific energy at T0
        cv_liquid:        [J/(kg·K)] Liquid specific heat (approx. constant)
        rho_liquid:       [kg/m^3]   Reference saturated liquid density
        molecular_weight: [kg/mol]   Molecular weight (for ideal gas)

    Returns:
        T_eq:  [K]  Equilibrium temperature
    """

    # Define residual function for root finding
    def residual(T: float) -> float:
        """
        Energy residual R(T) = U_model(T) - U_target.
        Uses constraint:
            V = m_liquid * v_liquid + (m - m_liquid) * v_gas
        Args:
            T:  [K]  Temperature
        Returns:
            U_diff:  [J]  Difference in internal energy
        """

        # Saturated energies
        u_liq = calc_boiling_specific_energy_liquid(
            T=T,
            T0=T0,
            u0_liquid=u0_liquid,
            cv_liquid=cv_liquid,
        )
        u_gas = calc_boiling_specific_energy_gas(
            T=T,
            T0=T0,
            u0_gas=u0_gas,
            u0_liquid=u0_liquid,
            cv_liquid=cv_liquid,
        )
        rho_gas = calc_boiling_density_gas(
            T=T,
            T0=T0,
            P0=P0,
            u0_gas=u0_gas,
            u0_liquid=u0_liquid,
            molecular_weight=molecular_weight,
        )
        v_gas = 1.0 / rho_gas
        v_liq = 1.0 / rho_liquid

        # Mass split from volume constraint
        m_l = (V - m * v_gas) / (v_liq - v_gas)

        # Clamp to physical bounds
        m_l = max(0.0, min(m_l, m))
        m_g = m - m_l

        # Get difference in internal energy
        U_model = m_l * u_liq + m_g * u_gas
        U_diff = U_model - U

        # Return difference
        return U_diff

    # Bounds
    T_lo = T0 / 2
    T_hi = T0 * 2
    
    # Solve for equilibrium T
    T_eq = brentq(residual, T_lo, T_hi)

    # Return result
    return T_eq


def calc_boiling_mass_fraction_liquid(
        T: float,
        T0: float,
        P0: float,
        u0_gas: float,
        u0_liquid: float,
        rho_liquid: float,
        rho_average: float,
        molecular_weight: float,
    ) -> float:
    """
    Calculate liquid mass fraction given temperature and densities.
    Args:
        T:                  [K]        Temperature
        T0:                 [K]        Reference temperature
        P0:                 [Pa]       Reference pressure
        u0_gas:            [J/kg]      Reference internal specific energy of gas at T0
        u0_liquid:         [J/kg]      Reference internal specific energy of liquid at T0
        rho_liquid:       [kg/m^3]     Density of liquid phase at saturation
        rho_average:      [kg/m^3]     Average density of the mixture
        molecular_weight:  [kg/mol]    Molecular weight (for ideal gas calculations)
    Returns:
        x:  [-]  Liquid mass fraction
    """

    # Get density of gas phase at saturation
    rho_gas = calc_boiling_density_gas(
        T=T,
        T0=T0,
        P0=P0,
        u0_gas=u0_gas,
        u0_liquid=u0_liquid,
        molecular_weight=molecular_weight,
    )

    # Calculate specific volumes
    v_gas = 1.0 / rho_gas
    v_liq = 1.0 / rho_liquid
    v_avg = 1.0 / rho_average

    # Calculate mass fraction
    x = (v_avg - v_gas) / (v_liq - v_gas)
    
    # Clamp to physical bounds
    x = max(0.0, min(x, 1.0))

    # Return result
    return x


def calc_boiling_energy_fraction_liquid(
        T: float,
        T0: float,
        u0_gas: float,
        u0_liquid: float,
        u_average: float,
        cv_liquid: float,
    ) -> float:
    """
    Calculate liquid energy fraction given temperature and average specific energy.
    Args:
        T:              [K]        Temperature
        T0:             [K]        Reference temperature
        u0_gas:        [J/kg]      Reference internal specific energy of gas at T0
        u0_liquid:     [J/kg]      Reference internal specific energy of liquid at T0
        u_average:     [J/kg]      Average specific internal energy of the mixture
        cv_liquid:    [J/(kg·K)]   Specific heat capacity of liquid phase
    Returns:
        x:  [-]  Liquid energy fraction
    """

    # Get saturated specific energies
    u_liq = calc_boiling_specific_energy_liquid(
        T=T,
        T0=T0,
        u0_liquid=u0_liquid,
        cv_liquid=cv_liquid,
    )
    u_gas = calc_boiling_specific_energy_gas(
        T=T,
        T0=T0,
        u0_gas=u0_gas,
        u0_liquid=u0_liquid,
        cv_liquid=cv_liquid,
    )

    # Calculate energy fraction
    x = (u_average - u_gas) / (u_liq - u_gas)

    # Clamp to physical bounds
    x = max(0.0, min(x, 1.0))

    # Return result
    return x

def calc_boiling_volume_fraction_liquid(
        T: float,
        T0: float,
        P0: float,
        u0_gas: float,
        u0_liquid: float,
        rho_liquid: float,
        rho_average: float,
        molecular_weight: float,
    ) -> float:
    """
    Calculate liquid volume fraction given temperature and average volume.
    Args:
        T:                  [K]        Temperature
        T0:                 [K]        Reference temperature
        P0:                 [Pa]       Reference pressure
        u0_gas:            [J/kg]      Reference internal specific energy of gas at T0
        u0_liquid:         [J/kg]      Reference internal specific energy of liquid at T0
        rho_liquid:       [kg/m^3]     Density of liquid phase at saturation
        rho_average:      [kg/m^3]     Average density of the mixture
        molecular_weight:  [kg/mol]    Molecular weight (for ideal gas calculations)
    Returns:
        x:  [-]  Liquid volume fraction
    """

    # Get density of gas phase at saturation
    rho_gas = calc_boiling_density_gas(
        T=T,
        T0=T0,
        P0=P0,
        u0_gas=u0_gas,
        u0_liquid=u0_liquid,
        molecular_weight=molecular_weight,
    )

    # Get mass fraction
    xm = calc_boiling_mass_fraction_liquid(
        T=T,
        T0=T0,
        P0=P0,
        u0_gas=u0_gas,
        u0_liquid=u0_liquid,
        rho_liquid=rho_liquid,
        rho_average=rho_average,
        molecular_weight=molecular_weight,
    )

    # Get volume fraction from mass fraction
    x = (xm * rho_gas) / ((xm * rho_gas) + ((1 - xm) * rho_liquid))

    # Clamp to physical bounds
    x = max(0.0, min(x, 1.0))

    # Return result
    return x
