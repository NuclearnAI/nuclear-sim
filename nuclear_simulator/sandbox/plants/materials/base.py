
# Import libraries
from nuclear_simulator.sandbox.plants.physics import (
    calc_temperature_from_energy,
    calc_energy_from_temperature,
)


# Define base Material class
class Material:
    """
    Base class for all materials in the nuclear simulation.
    
    This class defines the fundamental thermodynamic properties and operations that all
    materials must support. Subclasses implement specific material behaviors (solid,
    liquid, gas) by overriding the pressure property and providing material constants.
    
    Class Variables (Material Constants):
        cp: Specific heat capacity [J/(kg·K)], must be set by subclasses
    
    Instance Variables (Extrinsic Properties):
        m: Mass [kg]
        U: Internal energy [J], referenced to 0K
        V: Volume [m³]
    """
    
    # Class variables - Material constants (must be set by subclasses)
    HEAT_CAPACITY: float = None
    
    def __init__(self, m: float, U: float, V: float) -> None:
        """
        Initialize material with extrinsic properties directly.
        
        Args:
            m: Mass [kg]
            U: Internal energy [J], referenced to 0K
            V: Volume [m³]
        
        Raises:
            ValueError: If any properties are invalid
        """
        self.m = m
        self.U = U
        self.V = V
        self.validate()
    
    def __repr__(self) -> str:
        """
        String representation for debugging.
        
        Returns:
            str: Human-readable representation showing type and key properties
        """
        return (
            f"{type(self).__name__}(m={self.m:.2f} kg, U={self.U:.2f} J, V={self.V:.6f} m³)"
        )
    
    def __add__(self, other: 'Material') -> 'Material':
        """
        Add two materials together (simulates mixing/flow).
        Mass, energy, and volume are conserved.
        
        Args:
            other: Another material instance to add
        
        Returns:
            Material: New material instance with summed properties
        """
        if type(self) != type(other):
            raise TypeError(
                f"Cannot add materials of different types: "
                f"{type(self).__name__} and {type(other).__name__}"
            )
        m_new = self.m + other.m
        U_new = self.U + other.U
        V_new = self.V + other.V
        return type(self)(m_new, U_new, V_new)
    
    def __sub__(self, other: 'Material') -> 'Material':
        """
        Subtract material (simulates outflow).
        Mass, energy, and volume are conserved.
        
        Args:
            other: Material instance to subtract
        
        Returns:
            Material: New material instance with subtracted properties
        """
        if type(self) != type(other):
            raise TypeError(
                f"Cannot subtract materials of different types: "
                f"{type(self).__name__} and {type(other).__name__}"
            )
        m_new = self.m - other.m
        U_new = self.U - other.U
        V_new = self.V - other.V
        return type(self)(m_new, U_new, V_new)
    
    @classmethod
    def from_temperature(cls, m: float, T: float, **kwargs) -> 'Material':
        """
        Initialize from temperature instead of energy.
        
        Args:
            m:      [kg] Mass
            T:      [K]  Temperature
            kwargs: [-]  Additional arguments for subclass constructor
        
        Returns:
            Material: New material instance initialized from temperature
        """
        if cls.HEAT_CAPACITY is None:
            raise ValueError(f"{cls.__name__}: cp must be set by subclass")
        U = calc_energy_from_temperature(T=T, m=m, cv=cls.HEAT_CAPACITY)
        return cls(m, U, **kwargs)
    
    @property
    def cv(self) -> float:
        """
        Specific heat capacity [J/(kg·K)].
        
        Returns:
            float: Specific heat capacity of the material
        """
        return self.HEAT_CAPACITY

    @property
    def T(self) -> float:
        """
        Temperature [K], computed from internal energy.
        
        Returns:
            float: Temperature computed from U, m, and cp
        """
        return calc_temperature_from_energy(self.U, self.m, self.cv)
    
    @property
    def rho(self) -> float:
        """
        Density [kg/m³], computed from mass and volume.
        
        Returns:
            float: Density computed from m and V
        """
        return self.m / self.V
    
    @property
    def P(self) -> float:
        """
        Pressure [Pa]. Returns None in base class; subclasses override.
        
        Returns:
            None: Base class does not define pressure behavior
        """
        return None
    
    def set_temperature(self, T: float) -> None:
        """
        Set temperature and update energy.
        
        This method updates the material's temperature by computing and setting
        the corresponding internal energy. This is the inverse operation of
        reading the T property.
        
        Args:
            T: Target temperature [K]
        
        Modifies:
            self.U: Updated to correspond to target temperature
        
        Raises:
            ValueError: If temperature is negative or if cp is not set
        """
        if T < 0:
            raise ValueError(f"Temperature cannot be negative: {T:.2f} K")
        if self.cv is None:
            raise ValueError(f"{type(self).__name__}: cp must be set")
        self.U = calc_energy_from_temperature(T=T, m=self.m, cv=self.cv)
        return
    
    def validate(self) -> None:
        """
        Ensure all properties are physically reasonable.
        
        This method checks that the material's state is physically valid:
        - Mass must be positive (can't have negative matter)
        - Internal energy must be non-negative (referenced to 0K)
        - Volume must be positive (can't have negative space)
        """
        if self.HEAT_CAPACITY is None:
            raise ValueError(f"{type(self).__name__}: HEAT_CAPACITY must be set by subclass")
        if self.m <= 0:
            raise ValueError(f"Mass must be positive: {self.m:.2f} kg")
        if self.U < 0:
            raise ValueError(f"Internal energy must be non-negative: {self.U:.2f} J")
        if self.V <= 0:
            raise ValueError(f"Volume must be positive: {self.V:.2f} m³")
        return


# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Define a dummy class
    class DummyMaterial(Material):
        HEAT_CAPACITY = 1000.0
    # Instantiate
    mata = DummyMaterial(m=10.0, U=1e6, V=0.01)
    matb = DummyMaterial(m=10.0, U=2e6, V=0.02)
    # Add materials
    matc = mata + matb
    assert matc.m == 20.0
    assert matc.U == 3e6
    assert matc.V == 0.03
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")

