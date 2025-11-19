
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph
from nuclear_simulator.sandbox.plants.vessels import PressurizerVessel
from nuclear_simulator.sandbox.plants.materials import PWRPrimaryWater


class PrimaryPressurizer(PressurizerVessel):
    """
    Pressurizer vessel for primary loop pressure control.
    """
    P_setpoint: float = PWRPrimaryWater.P0
    contents: PWRPrimaryWater = Field(
        default_factory=lambda: 
        PWRPrimaryWater.from_temperature(m=500.0, T=PWRPrimaryWater.T0)
    )


# Define Reactor
class PressurizerSystem(Graph):
    """
    Pressurizer system containing the primary pressurizer vessel.
    """

    def __init__(self, **data) -> None:
        """Initialize pressurizer system graph."""

        # Call super init
        super().__init__(**data)

        # Build graph
        self.pressurizer = self.add_node(
            PrimaryPressurizer, name=f"{self.name}:Pressurizer"
        )
        
        # Done
        return
    
    @property
    def primary_in(self) -> PrimaryPressurizer:
        """Convenience accessor for primary inlet (coolant)."""
        return self.pressurizer
    
    @property
    def primary_out(self) -> PrimaryPressurizer:
        """Convenience accessor for primary outlet (coolant)."""
        return self.pressurizer






