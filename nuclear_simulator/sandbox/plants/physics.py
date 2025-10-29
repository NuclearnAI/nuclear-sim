

def calc_temperature_from_energy(U: float, m: float, cp: float, eps=1e-6) -> float:
    """
    Calculate temperature from internal energy, mass, and specific heat capacity.
    Args:
        U:   [J]        Internal energy
        m:   [kg]       Mass
        cp:  [J/(kg·K)] Specific heat capacity
        eps: [unitless] Small value to prevent division by zero
    Returns:
        Temperature [K]
    """
    return U / (max(m, eps) * max(cp, eps))

def calc_energy_from_temperature(T: float, m: float, cp: float) -> float:
    """
    Calculate internal energy from temperature, mass, and specific heat capacity.
    Args:
        T:  [K]        Temperature
        m:  [kg]       Mass
        cp: [J/(kg·K)] Specific heat capacity
    Returns:
        Internal energy [J]
    """
    return T * m * cp

