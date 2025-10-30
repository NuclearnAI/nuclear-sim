
# Import libraries
from nuclear_simulator.sandbox.plants.materials.base import Material
from nuclear_simulator.sandbox.plants.physics import (
    GAS_CONSTANT,
    calc_volume_ideal_gas,
    calc_pressure_ideal_gas,
    calc_energy_from_temperature
)


# Define base gas class
class Gas(Material):
    """
    Base class for gases.
    """
    
    # Define class attributes
    MOLECULAR_WEIGHT: float = None  # [kg/mol] Molecular weight
    
    def __init__(self, m: float, U: float, V: float) -> None:
        """
        Initialize isovolumetric ideal gas.
        Args:
            m: [kg] Mass
            U: [J]  Internal energy, referenced to 0K
            V: [m³] Volume (fixed)
        """
        if self.MOLECULAR_WEIGHT is None:
            raise ValueError(f"{type(self).__name__}: MOLECULAR_WEIGHT must be set by subclass")
        super().__init__(m, U, V)
        return
    
    @property
    def cp(self) -> float:
        """
        Specific heat capacity at constant pressure.
        Returns:
            float: Specific heat capacity [J/(kg·K)]
        """
        return self.HEAT_CAPACITY + GAS_CONSTANT / self.MOLECULAR_WEIGHT

    @property
    def mols(self) -> float:
        """
        Number of moles in the gas.
        Returns:
            float: Number of moles [mol]
        """
        return self.m / self.MOLECULAR_WEIGHT
    
    @property
    def P(self) -> float:
        """
        Pressure from ideal gas law.
        Returns:
            float: Pressure computed from ideal gas law [Pa]
        """
        return calc_pressure_ideal_gas(n=self.mols, T=self.T, V=self.V)
    
    @classmethod
    def from_temperature_volume(
            cls,
            m: float,
            T: float,
            V: float
        ) -> 'Gas':
        """
        Initialize isovolumetric gas from temperature and volume.
        Args:
            m: [kg] Mass
            T: [K]  Temperature
            V: [m³] Volume (fixed)
        Returns:
            IsovolumetricGas: New isovolumetric gas instance
        """
        if cls.HEAT_CAPACITY is None:
            raise ValueError(f"{cls.__name__}: HEAT_CAPACITY must be set by subclass")
        if cls.MOLECULAR_WEIGHT is None:
            raise ValueError(f"{cls.__name__}: MOLECULAR_WEIGHT must be set by subclass")
        cv = cls.HEAT_CAPACITY
        U = calc_energy_from_temperature(T=T, m=m, cv=cv)
        return cls(m, U, V)
    
    @classmethod
    def from_temperature_pressure(
            cls,
            m: float,
            T: float,
            P: float
        ) -> 'Gas':
        """
        Initialize isovolumetric gas from temperature and pressure.
        Args:
            m: [kg] Mass
            T: [K]  Temperature
            P: [Pa] Pressure
        Returns:
            IsovolumetricGas: New isovolumetric gas instance
        """
        if cls.HEAT_CAPACITY is None:
            raise ValueError(f"{cls.__name__}: HEAT_CAPACITY must be set by subclass")
        if cls.MOLECULAR_WEIGHT is None:
            raise ValueError(f"{cls.__name__}: MOLECULAR_WEIGHT must be set by subclass")
        n = m / cls.MOLECULAR_WEIGHT
        cv = cls.HEAT_CAPACITY
        V = calc_volume_ideal_gas(n=n, T=T, P=P)
        U = calc_energy_from_temperature(T=T, m=m, cv=cv)
        return cls(m, U, V)
    


# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Define a dummy class
    class DummyGas(Gas):
        HEAT_CAPACITY = 1000.0
        MOLECULAR_WEIGHT = 0.028
    # Create instances
    gasa = DummyGas(m=1.0, U=2e5, V=0.1)
    gasb = DummyGas.from_temperature_volume(m=0.5, T=400.0, V=0.1)
    # Add gases
    gasc = gasa + gasb
    # Validate results
    assert gasc.m == gasa.m + gasb.m
    assert gasc.V == gasa.V
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")
    
