
# Import libraries
from nuclear_simulator.sandbox.materials.base import Material


# Define liquid material class
class Liquid(Material):
    """
    Incompressible liquid material with fixed volume based on reference density.
    """

    # Define class attributes
    DENSITY: float = None  # [kg/m³] Reference density
    
    def __init__(self, m: float, U: float, **kwargs) -> None:
        """
        Initialize liquid material with automatic volume calculation.

        Args:
            m: [kg] Mass
            U: [J]  Internal energy, referenced to 0K
        """
        if self.DENSITY is None or self.DENSITY <= 0.0:
            raise ValueError(f"{type(self).__name__}: DENSITY must be set by subclass")
        V = m / self.DENSITY
        super().__init__(m, U, **{**kwargs, 'V': V})
    
    # def __add__(self, other: 'Liquid') -> 'Liquid':
    #     """
    #     Add two liquids together. Conserves mass and energy.
    #     Args:
    #         other: Another liquid instance
    #     Returns:
    #         Liquid: New liquid with combined properties
    #     """
    #     if type(self) != type(other):
    #         raise TypeError(
    #             f"Cannot add materials of different types: "
    #             f"{type(self).__name__} and {type(other).__name__}"
    #         )
    #     m_new = self.m + other.m
    #     U_new = self.U + other.U
    #     return type(self)(m_new, U_new)
    
    # def __sub__(self, other: 'Liquid') -> 'Liquid':
    #     """
    #     Subtract liquid material (simulates outflow). Conserves mass and energy.
    #     Args:
    #         other: Another liquid instance to subtract
    #     Returns:
    #         Liquid: New liquid with subtracted properties
    #     """
    #     if type(self) != type(other):
    #         raise TypeError(
    #             f"Cannot subtract materials of different types: "
    #             f"{type(self).__name__} and {type(other).__name__}"
    #         )
    #     m_new = self.m - other.m
    #     U_new = self.U - other.U
    #     return type(self)(m_new, U_new)
    


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



