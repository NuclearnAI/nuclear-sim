
# Import libraries
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.materials.base import Material
    

# Define container for infinite sink/source
class Reservoir(Node):
    """
    A node representing a large reservoir of liquid at fixed P and T.
    """

    # Set attributes
    P: float = 1e5                    # [Pa]  Atmospheric pressure
    T: float = 300.0                  # [K]   Ambient temperature
    material: Material | None = None  # [-]   Material is set in init
    material_type: type               # [-]   Type of material contained

    def __init__(self, **data) -> None:
        """Initialize liquid environment node."""
        # Call super init
        super().__init__(**data)
        # Set material if not provided
        if self.material is None:
            self.material = self.material_type.from_temperature(m=1e12, T=self.T)
        # Done
        return



# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.materials.nuclear import PWRPrimaryWater
    # Create liquid environment
    env = Reservoir(material_type=PWRPrimaryWater, T=350.0)
    # Update
    env.update(.1)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

