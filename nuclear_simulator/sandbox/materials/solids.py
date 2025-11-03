
# Import libraries
from nuclear_simulator.sandbox.materials.base import Material


# Define solid material class
class Solid(Material):
    """
    Solid material with fixed volume based on reference density.
    """

    # Define class attributes
    DENSITY: float = None  # [kg/m³] Reference density
    
    def __init__(self, m: float, U: float, **kwargs) -> None:
        """
        Initialize solid material with automatic volume calculation.

        Args:
            m:      [kg] Mass
            U:      [J]  Internal energy, referenced to 0K
            kwargs: [-]  Additional keyword arguments for base Material class
        """
        if self.DENSITY is None or self.DENSITY <= 0.0:
            raise ValueError(f"{type(self).__name__}: DENSITY must be set by subclass")
        V = m / self.DENSITY
        super().__init__(m, U, V, **kwargs)
    
    def __add__(self, other: 'Solid') -> 'Solid':
        """
        Add two solid materials together. Conserves mass and energy.
        Args:
            other: Another solid material instance
        Returns:
            Solid: New solid with combined properties
        """
        if type(self) != type(other):
            raise TypeError(
                f"Cannot add materials of different types: "
                f"{type(self).__name__} and {type(other).__name__}"
            )
        m_new = self.m + other.m
        U_new = self.U + other.U
        return type(self)(m_new, U_new)
    
    def __sub__(self, other: 'Solid') -> 'Solid':
        """
        Subtract solid material (simulates outflow). Conserves mass and energy.
        Args:
            other: Another solid material instance to subtract
        Returns:
            Solid: New solid with subtracted properties
        """
        if type(self) != type(other):
            raise TypeError(
                f"Cannot subtract materials of different types: "
                f"{type(self).__name__} and {type(other).__name__}"
            )
        m_new = self.m - other.m
        U_new = self.U - other.U
        return type(self)(m_new, U_new)
    


# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Define a dummy class
    class DummySolid(Solid):
        HEAT_CAPACITY = 500.0
        DENSITY = 8000.0
    # Create instances
    solida = DummySolid(m=10.0, U=2e6)
    solidb = DummySolid.from_temperature(m=5.0, T=400.0)
    # Add solids
    solidc = solida + solidb
    # Check properties
    assert solida.m == 10.0
    assert solidb.m == 5.0
    assert solidc.m == 15.0
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")



