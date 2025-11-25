
# Import libraries
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.materials import Material


# Define base vessel node
class Vessel(Node):
    """
    A node representing a vessel containing some material.
    Attributes:
        contents:      [-]      Material stored in the vessel
    """
    contents: Material | None

    def __init__(self, **data) -> None:
        """Initialize vessel node."""

        # Call super init
        super().__init__(**data)

        # Validate contents
        if isinstance(self.contents, Material):
            try:
                self.contents.validate()
            except Exception as e:
                raise ValueError("Material validation failed during initialization.") from e
        
        # Done
        return

    # Add validation to update
    def update(self, dt):
        """
        Update method with validation.
        Args:
            dt: Time step size (s).
        """
        
        # Update normally
        super().update(dt)

        # Validate contents
        try:
            self.contents.validate()
        except Exception as e:
            raise ValueError("Material validation failed during update.") from e
        
        # Done
        return
    



# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.materials import Liquid
    # Create dummy liquid
    class DummyLiquid(Liquid):
        HEAT_CAPACITY = 500.0
        DENSITY = 8000.0
    # Create vessel
    vessel = Vessel(
        contents=DummyLiquid.from_temperature(m=100.0, T=300.0)
    )
    # Update
    vessel.update(.1)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

