
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Node
from nuclear_simulator.sandbox.plants.edges import LiquidPipe, LiquidPump
from nuclear_simulator.sandbox.plants.vessels import PressurizedLiquidVessel, PressurizerVessel
from nuclear_simulator.sandbox.plants.materials import PWRPrimaryWater


# Get constants
P_PRIMARY = PWRPrimaryWater.P0
T_PRIMARY = PWRPrimaryWater.T0
    

class PrimaryCore(PressurizedLiquidVessel):
    """
    Simplified coolant node for reactor core.
    """
    P: float = P_PRIMARY
    contents: PWRPrimaryWater = Field(
        default_factory=lambda: (
            PWRPrimaryWater.from_temperature(m=12_000.0, T=T_PRIMARY)
        )
    )

class PrimaryHotLeg(PressurizedLiquidVessel):
    """Primary-side hot leg header (reactor core outlet -> SG bundle)."""
    P: float = P_PRIMARY
    contents: PWRPrimaryWater = Field(
        default_factory=lambda:
            PWRPrimaryWater.from_temperature(m=3_000.0, T=T_PRIMARY)
    )


class PrimarySG(PressurizedLiquidVessel):
    """Primary-side Steam Generator U-tube bundle control volume (heat donor)."""
    P: float = P_PRIMARY
    contents: PWRPrimaryWater = Field(
        default_factory=lambda:
            PWRPrimaryWater.from_temperature(m=8_000.0, T=T_PRIMARY)
    )


class PrimaryColdLeg(PressurizedLiquidVessel):
    """Primary-side cold leg header (SG bundle outlet -> reactor core return)."""
    P: float = P_PRIMARY
    contents: PWRPrimaryWater = Field(
        default_factory=lambda:
            PWRPrimaryWater.from_temperature(m=3_000.0, T=T_PRIMARY)
    )


class PrimaryPressurizer(PressurizerVessel):
    """
    Pressurizer vessel for primary loop pressure control.
    """
    P_setpoint: float = P_PRIMARY
    contents: PWRPrimaryWater = Field(
        default_factory=lambda: 
        PWRPrimaryWater.from_temperature(m=4_000.0, T=T_PRIMARY)
    )


# Define Reactor
class PrimaryLoop(Graph):
    """
    Simplified reactor primary loop subsystem.
    Attributes:
        m_dot:  [kg/s] Mass flow rate through the primary loop
    Nodes:
        core:        PrimaryCore
        hot_leg:     PrimaryHotLeg
        sg:          PrimarySG
        cold_leg:    PrimaryColdLeg
        pressurizer: PrimaryPressurizer
    Edges:
        pipe_core_to_hotleg:         LiquidPipe
        pipe_hotleg_to_bundle:       LiquidPipe
        pipe_bundle_to_coldleg:      LiquidPipe
        pump_coldleg_to_pressurizer: LiquidPump
        pipe_pressurizer_to_core:    LiquidPipe
    """

    # Set attributes
    m_dot: float = 100.0

    def __init__(self, **data) -> None:
        """Initialize primary loop graph."""

        # Call super init
        super().__init__(**data)

        # Add nodes
        self.core        = self.add_node(PrimaryCore, name="Core")
        self.hot_leg     = self.add_node(PrimaryHotLeg, name="HotLeg")
        self.sg          = self.add_node(PrimarySG, name="SG")
        self.cold_leg    = self.add_node(PrimaryColdLeg, name="ColdLeg")
        self.pressurizer = self.add_node(PrimaryPressurizer, name="Pressurizer")

        # Add edges
        self.pipe_core_to_hotleg = self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.core,
            node_target=self.hot_leg,
            name="Pipe:[Core->HotLeg]",
            m_dot=self.m_dot,
        )
        self.pipe_hotleg_to_bundle = self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.hot_leg,
            node_target=self.sg,
            name="Pipe:[HotLeg->SG]",
            m_dot=self.m_dot,
        )
        self.pipe_bundle_to_coldleg = self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.sg,
            node_target=self.cold_leg,
            name="Pipe:[SG->ColdLeg]",
            m_dot=self.m_dot,
        )
        self.pump_coldleg_to_pressurizer = self.add_edge(
            edge_type=LiquidPump,
            node_source=self.cold_leg,
            node_target=self.pressurizer,
            name="Pump:[ColdLeg->Pressurizer]",
            m_dot=self.m_dot,
        )
        self.pipe_pressurizer_to_core = self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.pressurizer,
            node_target=self.core,
            name="Pipe:[Pressurizer->Reactor]",
            m_dot=self.m_dot,
        )
        
        # Done
        return
    
    def update(self, dt: float) -> None:
        """Update the graph by one time step.
        Args:
            dt:  [s] Time step for the update.
        """
        try:
            super().update(dt)
        except Exception as e:
            raise RuntimeError(f"Error updating {self.__class__.__name__}: {e}") from e
        return


# Test
def test_file():
    """
    Test subsystem.
    """

    # Import libraries
    import matplotlib.pyplot as plt
    from nuclear_simulator.sandbox.plants.dashboard import Dashboard

    # Create graph
    primary_loop = PrimaryLoop()

    # Initialize dashboard
    dashboard = Dashboard(primary_loop)

    # Simulate for a while
    dt = 1
    n_steps = 1000
    for i in range(n_steps):
        primary_loop.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

