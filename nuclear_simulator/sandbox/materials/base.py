
# Import libraries
from numbers import Number
from nuclear_simulator.sandbox.physics import (
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
            m:        [kg]  Mass
            U:        [J]   Internal energy, referenced to 0K
            V:        [m³]  Volume
            validate: [-]   Whether to validate properties upon initialization
                            Skip for flows where negative mass/energy/volume may occur
        
        Raises:
            ValueError: If any properties are invalid
        """
        self.m = m
        self.U = U
        self.V = V
    
    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(m={self.m:.2f} kg, U={self.U:.2f} J, V={self.V:.6f} m³)"
        )
    
    def __add__(self, other: 'Material' | float) -> 'Material':
        if (type(self) == type(other)) or isinstance(other, Energy):
            # Case: Same material type
            m_new = self.m + other.m
            U_new = self.U + other.U
            V_new = self.V + other.V
            return type(self)(m=m_new, U=U_new, V=V_new)
        elif isinstance(other, Number) and (other == 0.0):
            # Case: Adding zero (no-op)
            return type(self)(m=self.m, U=self.U, V=self.V)
        else:
            # Otherwise raise error
            raise TypeError(
                f"Cannot add materials of different types: "
                f"{type(self).__name__} and {type(other).__name__}"
            )
        
    def __radd__(self, other):
        return self.__add__(other)
    
    def __sub__(self, other: 'Material') -> 'Material':
        if (type(self) == type(other)) or isinstance(other, Energy):
            # Case: Same material type
            m_new = self.m - other.m
            U_new = self.U - other.U
            V_new = self.V - other.V
            return type(self)(m=m_new, U=U_new, V=V_new)
        elif isinstance(other, Number) and other == 0.0:
            # Case: Subtracting zero (no-op)
            return type(self)(m=self.m, U=self.U, V=self.V)
        else:
            # Otherwise raise error
            raise TypeError(
                f"Cannot subtract materials of different types: "
                f"{type(self).__name__} and {type(other).__name__}"
            )
        
    def __rsub__(self, other):
        if (type(self) == type(other)) or isinstance(other, Energy):
            # Case: Same material type
            m_new = other.m - self.m
            U_new = other.U - self.U
            V_new = other.V - self.V
            return type(self)(m=m_new, U=U_new, V=V_new)
        elif isinstance(other, Number) and other == 0.0:
            # Case: Subtracting zero (no-op)
            return type(self)(m=-self.m, U=-self.U, V=-self.V)
        else:
            # Otherwise raise error
            raise TypeError(
                f"Cannot subtract materials of different types: "
                f"{type(other).__name__} and {type(self).__name__}"
            )
    
    def __mul__(self, scalar: Number) -> 'Material':
        m_new = self.m * scalar
        U_new = self.U * scalar
        V_new = self.V * scalar
        return type(self)(m=m_new, U=U_new, V=V_new)
    
    def __rmul__(self, scalar: Number) -> 'Material':
        return self.__mul__(scalar)
    
    def __truediv__(self, scalar: Number) -> 'Material':
        m_new = self.m / scalar
        U_new = self.U / scalar
        V_new = self.V / scalar
        return type(self)(m=m_new, U=U_new, V=V_new)
    
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
            raise ValueError(f"{cls.__name__}: HEAT_CAPACITY must be set by subclass")
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
    

# Define Energy material class
class Energy(Material):
    """
    Material that carries only internal energy (no mass or volume).
    """

    def __init__(self, U: float, **_) -> None:
        """
        Initialize energy-only material.

        Args:
            U: [J] Internal energy
        """
        super().__init__(m=0.0, U=U, V=0.0)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(U={self.U:.2f} J)"
    



# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Define a dummy class
    class DummyMaterial(Material):
        HEAT_CAPACITY = 1000.0
    # Instantiate
    mata = DummyMaterial(m=10.0, U=1e6, V=0.01)
    matb = DummyMaterial(m=10.0, U=2e6, V=0.02)
    # Test addition
    matc = mata + matb
    assert matc.m == 20.0
    assert matc.U == 3e6
    assert matc.V == 0.03
    # Test subtraction
    matd = matc - mata
    assert matd.m == 10.0
    assert matd.U == 2e6
    # Test multiplication
    mate = mata * 2.0
    assert mate.m == 20.0
    assert mate.U == 2e6
    # Test division
    matf = mate / 2.0
    assert matf.m == 10.0
    assert matf.U == 1e6
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")

