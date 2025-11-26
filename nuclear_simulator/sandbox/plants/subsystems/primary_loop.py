
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Node
from nuclear_simulator.sandbox.plants.edges import LiquidPipe, LiquidPump
from nuclear_simulator.sandbox.plants.vessels import PressurizedLiquidVessel, PressurizerVessel
from nuclear_simulator.sandbox.plants.materials import PWRPrimaryWater


# Define Reactor
class PrimaryLoop(Graph):
    """
    Simplified reactor primary loop subsystem.
    Nodes:
        core:        PressurizedLiquidVessel
        hot_leg:     PressurizedLiquidVessel
        sg:          PressurizedLiquidVessel
        cold_leg:    PressurizedLiquidVessel
        pressurizer: PressurizerVessel
    Edges:
        pipe_core_to_hotleg:         LiquidPipe
        pipe_hotleg_to_bundle:       LiquidPipe
        pipe_bundle_to_coldleg:      LiquidPipe
        pump_coldleg_to_pressurizer: LiquidPump
        pipe_pressurizer_to_core:    LiquidPipe
    """

    # Set attributes
    P:               float = PWRPrimaryWater.P0
    T:               float = PWRPrimaryWater.T0
    m_core:          float = 12_000.0
    m_hotleg:        float = 3_000.0
    m_sg:            float = 8_000.0
    m_coldleg:       float = 3_000.0
    m_pressurizer:   float = 4_000.0
    m_dot_setpoint:  float = 100.0

    def __init__(self, **data) -> None:
        """Initialize primary loop graph."""

        # Call super init
        super().__init__(**data)

        # Add nodes
        self.core = self.add_node(
            PressurizedLiquidVessel,
            name="Core",
            P=self.P,
            contents=PWRPrimaryWater.from_temperature(m=self.m_core, T=self.T),
        )
        self.hot_leg = self.add_node(
            PressurizedLiquidVessel,
            name="HotLeg",
            P=self.P,
            contents=PWRPrimaryWater.from_temperature(m=self.m_hotleg, T=self.T),
        )
        self.sg = self.add_node(
            PressurizedLiquidVessel,
            name="SG",
            P=self.P,
            contents=PWRPrimaryWater.from_temperature(m=self.m_sg, T=self.T),
        )
        self.cold_leg = self.add_node(
            PressurizedLiquidVessel,
            name="ColdLeg",
            P=self.P,
            contents=PWRPrimaryWater.from_temperature(m=self.m_coldleg, T=self.T),
        )
        self.pressurizer = self.add_node(
            PressurizerVessel,
            name="Pressurizer",
            P=self.P,
            contents=PWRPrimaryWater.from_temperature(m=self.m_pressurizer, T=self.T),
        )

        # Add edges
        self.pipe_core_to_hotleg = self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.core,
            node_target=self.hot_leg,
            name=f"Pipe:[{self.core.name}->{self.hot_leg.name}]",
            m_dot=self.m_dot_setpoint,
        )
        self.pipe_hotleg_to_bundle = self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.hot_leg,
            node_target=self.sg,
            name=f"Pipe:[{self.hot_leg.name}->{self.sg.name}]",
            m_dot=self.m_dot_setpoint,
        )
        self.pipe_bundle_to_coldleg = self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.sg,
            node_target=self.cold_leg,
            name=f"Pipe:[{self.sg.name}->{self.cold_leg.name}]",
            m_dot=self.m_dot_setpoint,
        )
        self.pump_coldleg_to_pressurizer = self.add_edge(
            edge_type=LiquidPump,
            node_source=self.cold_leg,
            node_target=self.pressurizer,
            name=f"Pump:[{self.cold_leg.name}->{self.pressurizer.name}]",
            m_dot=self.m_dot_setpoint,
        )
        self.pipe_pressurizer_to_core = self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.pressurizer,
            node_target=self.core,
            name=f"Pipe:[{self.pressurizer.name}->{self.core.name}]",
            m_dot=self.m_dot_setpoint,
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

