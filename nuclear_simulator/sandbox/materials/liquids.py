
# Import libraries
from nuclear_simulator.sandbox.materials.base import Material


# Define liquid material class
class Liquid(Material):
    """
    Incompressible liquid material with fixed volume based on reference density.
    Attributes:
        DENSITY:          [kg/m³]  Reference density for volume calculation
        P0:               [Pa]     Reference pressure for calculations
        T0:               [K]      Reference temperature for calculations
        LATENT_HEAT:      [J/kg]   Latent heat of vaporization at reference T0 and P0
        MOLECULAR_WEIGHT: [kg/mol] Molecular weight
    """

    # Define class attributes
    DENSITY: float | None = None
    

    def __init__(self, m: float, U: float, **kwargs) -> None:
        """
        Initialize liquid material with automatic volume calculation.

        Args:
            m: [kg] Mass
            U: [J]  Internal energy, referenced to 0K
        """

        # Check that density is set
        if self.DENSITY is None or self.DENSITY <= 0.0:
            raise ValueError(f"{type(self).__name__}: DENSITY must be set by subclass")
        
        # Calculate volume
        V = m / self.DENSITY

        # Add volume to kwargs
        if 'V' in kwargs and abs(kwargs['V'] - V) > 1e-9:
            raise ValueError(
                f"Volume argument V={kwargs['V']:.6f} m³ does not match calculated volume from mass and density."
            )
        else:
            kwargs['V'] = V

        # Initialize base class
        super().__init__(m, U, **kwargs)

        # Done 
        return


# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Define a dummy class
    class DummyLiquid(Liquid):
        HEAT_CAPACITY = 500.0
        DENSITY = 8000.0
    # Create instances
    solida = DummyLiquid(m=10.0, U=2e6)
    solidb = DummyLiquid.from_temperature(m=5.0, T=400.0)
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



