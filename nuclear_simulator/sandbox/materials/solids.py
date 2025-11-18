
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

        # Check that density is set
        if self.DENSITY is None or self.DENSITY <= 0.0:
            raise ValueError(f"{type(self).__name__}: DENSITY must be set by subclass")
        
        # Calculate volume
        V = m / self.DENSITY
        kwargs['V'] = V

        # Initialize base class
        super().__init__(m, U, **kwargs)

        # Done 
        return
    

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



