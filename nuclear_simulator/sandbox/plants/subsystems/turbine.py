
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any
    from nuclear_simulator.sandbox.materials.base import Material

# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Node
from nuclear_simulator.sandbox.materials import Gas, Liquid
from nuclear_simulator.sandbox.plants.vessels import PressurizedGasVessel, PressurizedLiquidVessel
from nuclear_simulator.sandbox.plants.edges.turbines import GasTurbine, LiquidTurbine


# Define Turbine
class Turbine(Graph):
    """
    Simplified turbine system.
    Nodes:
        inlet:   PressurizedGasVessel or PressurizedLiquidVessel
        outlet:  PressurizedGasVessel or PressurizedLiquidVessel
    Edges:
        turbine: TurbineEdge
    """

    # Set attributes
    material_type: type[Gas | Liquid]
    m_dot_setpoint: float
    P_inlet: float
    T_inlet: float
    m_inlet: float
    m_outlet: float
    P_outlet: float
    T_outlet: float

    def __init__(self, **data) -> None:
        """Initialize primary loop graph."""

        # Call super init
        super().__init__(**data)

        # Check material type
        if issubclass(self.material_type, Gas):
            vessel_class = PressurizedGasVessel
            turbine_edge_class = GasTurbine
            contents_inlet = self.material_type.from_temperature_pressure(
                m=self.m_inlet, T=self.T_inlet, P=self.P_inlet
            )
            contents_outlet = self.material_type.from_temperature_pressure(
                m=self.m_outlet, T=self.T_outlet, P=self.P_outlet
            )
        elif issubclass(self.material_type, Liquid):
            vessel_class = PressurizedLiquidVessel
            turbine_edge_class = LiquidTurbine
            contents_inlet = self.material_type.from_temperature(
                m=self.m_inlet, T=self.T_inlet
            )
            contents_outlet = self.material_type.from_temperature(
                m=self.m_outlet, T=self.T_outlet
            )
        else:
            raise ValueError(f"{self.__class__.__name__} material_type must be Gas or Liquid.")
        
        # Create nodes
        self.inlet = self.add_node(
            vessel_class,
            name="Inlet",
            P=self.P_inlet,
            contents=contents_inlet,
        )
        self.outlet = self.add_node(
            vessel_class,
            name="Outlet",
            P=self.P_outlet,
            contents=contents_outlet,
        )
        self.turbine = self.add_edge(
            edge_type=turbine_edge_class,
            node_source=self.inlet,
            node_target=self.outlet,
            name="Edge",
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
    from nuclear_simulator.sandbox.plants.materials import PWRSecondarySteam

    # Create graph
    turbine = Turbine(
        material_type=PWRSecondarySteam,
        m_dot_setpoint=10.0,
        P_inlet=5e6,
        T_inlet=800.0,
        m_inlet=100.0,
        m_outlet=100.0,
        P_outlet=1e6,
        T_outlet=400.0,
    )

    # Initialize dashboard
    dashboard = Dashboard(turbine)

    # Simulate for a while
    dt = 1
    n_steps = 1000
    for i in range(n_steps):
        turbine.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

