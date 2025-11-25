
# Import libraries
from numbers import Number
from nuclear_simulator.sandbox.materials.base import Material


# Define liquid material class
class Liquid(Material):
    """
    Incompressible liquid material with fixed volume based on reference density.
    Attributes:
        m:                [kg]       Mass
        U:                [J]        Internal energy
        V:                [m^3]      Volume
    Class attributes:
        HEAT_CAPACITY:    [J/(kg·K)] Specific heat capacity
        LATENT_HEAT:      [J/kg]     Latent heat of vaporization at reference T_BOIL and P_BOIL
        MOLECULAR_WEIGHT: [kg/mol]   Molecular weight (required for ideal gas calculations)
        P0:               [Pa]       Reference state pressure
        T0:               [K]        Reference state temperature
        u0:               [J/kg]     Reference internal specific energy at T0
        P_BOIL:           [Pa]       Critical point reference pressure for calculations
        T_BOIL:           [K]        Critical point reference temperature for calculations
        u_BOIL:           [J/kg]     Critical point reference internal specific energy at T_BOIL
    """

    # Define class attributes
    DENSITY: float | None = None
    

    def __init__(self, m: float, U: float, **_) -> None:
        """
        Initialize liquid material with automatic volume calculation.

        Args:
            m: [kg] Mass
            U: [J]  Internal energy, referenced to 0K
            _: [-]  Unused keyword arguments (required for base class initialization which pass V)
        """

        # Check that density is set
        if self.DENSITY is None or self.DENSITY <= 0.0:
            raise ValueError(f"{type(self).__name__}: DENSITY must be set by subclass")
        
        # Calculate volume
        V = m / self.DENSITY

        # Initialize base class
        super().__init__(m=m, U=U, V=V)

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
    liquida = DummyLiquid(m=10.0, U=2e6)
    liquidb = DummyLiquid.from_temperature(m=5.0, T=400.0)
    # Add liquids
    liquidc = liquida + liquidb
    # Check properties
    assert liquida.m == 10.0
    assert liquidb.m == 5.0
    assert liquidc.m == 15.0
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")



