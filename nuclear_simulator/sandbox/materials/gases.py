# Import libraries
from nuclear_simulator.sandbox.materials.base import Material
from nuclear_simulator.sandbox.physics import (
    UNIVERSAL_GAS_CONSTANT,
    calc_volume_ideal_gas,
    calc_pressure_ideal_gas,
    calc_energy_from_temperature,
)


# Define gas material class
class Gas(Material):
    """
    Gas material that follows ideal gas law behavior.
    
    Attributes:
        m:                [kg]       Mass
        U:                [J]        Internal energy
        V:                [m^3]      Volume
        HEAT_CAPACITY:    [J/(kg·K)] Specific heat capacity
        P0:               [Pa]       Reference pressure for calculations
        T0:               [K]        Reference temperature for calculations
        LATENT_HEAT:      [J/kg]     Latent heat of vaporization at reference T0 and P0
        MOLECULAR_WEIGHT: [kg/mol]   Molecular weight (required for ideal gas calculations)
    """

    @classmethod
    def from_temperature_pressure(cls, m: float, T: float, P: float, **kwargs) -> "Gas":
        """
        Initialize gas from temperature and pressure using ideal gas law.
        
        Args:
            m:      [kg]  Mass
            T:      [K]   Temperature
            P:      [Pa]  Pressure
            kwargs: [-]   Additional arguments for subclass constructor
        
        Returns:
            Gas: New gas instance initialized from temperature and pressure
        """

        # Validate required class attributes
        if cls.HEAT_CAPACITY is None:
            raise ValueError(f"{cls.__name__}: HEAT_CAPACITY must be set.")
        if cls.MOLECULAR_WEIGHT is None:
            raise ValueError(f"{cls.__name__}: MOLECULAR_WEIGHT must be set for ideal gas calculations.")
        
        # Calculate variables
        cv = cls.HEAT_CAPACITY
        T0 = cls.T0 or 0.0
        u0 = cls.u0 or 0.0
        n = m / cls.MOLECULAR_WEIGHT
        V = calc_volume_ideal_gas(n=n, T=T, P=P)
        U = calc_energy_from_temperature(T=T, m=m, cv=cv, T0=T0, u0=u0)

        # Create and return instance
        kwargs['V'] = V
        return cls(m, U, **kwargs)
    
    @property
    def P_ideal(self) -> float:
        """Calculate pressure using ideal gas law."""
        n = self.m / self.MW
        P = calc_pressure_ideal_gas(n=n, T=self.T, V=self.V)
        return P
    
    @property
    def cp(self) -> float:
        """Specific heat at constant pressure."""
        return self.cv + (UNIVERSAL_GAS_CONSTANT / self.MW)
    
    def v_saturation(self, T):
        """Specific volume at saturation (ideal gas assumption)."""
        P_sat = self.P_saturation(T)          # Pa
        R = UNIVERSAL_GAS_CONSTANT             # J/(mol·K)
        MW = self.MW                           # kg/mol
        v_sat = R * T / (P_sat * MW)           # m³/kg  (ideal gas)
        return v_sat


# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Define a dummy gas class
    class DummyGas(Gas):
        HEAT_CAPACITY = 1000.0
        MOLECULAR_WEIGHT = 0.029  # kg/mol (roughly air)
    # Create instance with direct volume specification
    gas_a = DummyGas(m=1.0, U=1e5, V=0.5)
    # Create instance from temperature and pressure
    gas_b = DummyGas.from_temperature_pressure(m=2.0, T=300.0, P=101325.0)
    # Create instance from temperature (inherited from base Material class)
    gas_c = DummyGas.from_temperature(m=1.5, T=350.0, V=0.75)
    # Test addition
    gas_d = gas_a + gas_b
    # Check properties
    assert gas_a.m == 1.0
    assert gas_b.m == 2.0
    assert gas_d.m == 3.0
    assert gas_d.U == gas_a.U + gas_b.U
    assert gas_d.V == gas_a.V + gas_b.V
    # Check that temperature can be computed
    T_a = gas_a.T
    assert T_a > 0
    # Check that density can be computed
    rho_a = gas_a.rho
    assert rho_a > 0
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")

