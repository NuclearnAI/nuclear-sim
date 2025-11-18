
# Import libraries
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.materials.base import Material
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.solids import Solid
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.plants.vessels.base import Vessel
    

# Define container for infinite sink/source
class Reservoir(Vessel):
    """
    A node representing a large reservoir of liquid at fixed P and T.
    Attributes:
        material_type: [-]     Type of material contained
        contents:      [-]     Material contained in the reservoir (allowed to be None)
        P:             [Pa]    Pressure of the reservoir
        T:             [K]     Temperature of the reservoir
    """
    material_type: type[Material] | None = None
    contents: Material | None = None
    P: float = 1e5
    T: float = 300.0

    def __init__(self, **data) -> None:
        """Initialize reservoir node."""

        # Call super init
        super().__init__(**data)
        
        # Set contents if not provided
        if self.contents is None and self.material_type is not None:
            if isinstance(self.contents, Gas):
                self.contents = self.material_type.from_temperature_pressure(
                    m=1e12, T=self.T, P=self.P
                )
            else:
                self.contents = self.material_type.from_temperature(
                    m=1e12, T=self.T, V=1e12
                )
        # Done
        return
    
    # Override update from graph to no-op
    def update_from_graph(self, dt: float) -> None:
        """Update reservoir from graph (no-op)."""
        return


# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.plants.materials import PWRSecondaryWater
    # Create liquid reservoir
    res = Reservoir(
        material_type=PWRSecondaryWater,
        P=PWRSecondaryWater.P0,
        T=PWRSecondaryWater.T0,
    )
    # Update
    res.update(.1)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

