
# Import libraries
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.materials.base import Material
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.solids import Solid
from nuclear_simulator.sandbox.materials.liquids import Liquid
    

# Define container for infinite sink/source
class Reservoir(Node):
    """
    A node representing a large reservoir of liquid at fixed P and T.
    Attributes:
        P:             [Pa]    Pressure of the reservoir
        T:             [K]     Temperature of the reservoir
        material:      [-]     Material contained in the reservoir
        material_type: [-]     Type of material contained
    """
    P: float = 1e5
    T: float = 300.0
    material: Material | None = None
    material_type: type[Material] | None = None

    def __init__(self, **data) -> None:
        """Initialize reservoir node."""
        # Call super init
        super().__init__(**data)
        # Set material if not provided
        if self.material is None and self.material_type is not None:
            self.material = self.material_type.from_temperature(m=1e12, T=self.T, V=1e12)
        # Done
        return
    
    # Override update from graph to no-op
    def update_from_graph(self, dt: float) -> None:
        """Update reservoir from graph (no-op)."""
        return
    
    @property
    def gas(self) -> Gas:
        """Get gas material if applicable."""
        if isinstance(self.material, Gas):
            return self.material
        else:
            raise AttributeError("Reservoir.material is not a Gas")
        
    @property
    def liquid(self) -> Liquid:
        """Get liquid material if applicable."""
        if isinstance(self.material, Liquid):
            return self.material
        else:
            raise AttributeError("Reservoir.material is not a Liquid")
        
    @property
    def solid(self) -> Solid:
        """Get solid material if applicable."""
        if isinstance(self.material, Solid):
            return self.material
        else:
            raise AttributeError("Reservoir.material is not a Solid")


# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.plants.materials import PWRPrimaryWater
    # Create liquid environment
    env = Reservoir(material_type=PWRPrimaryWater, T=350.0)
    # Update
    env.update(.1)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

