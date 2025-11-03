
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.graphs import Node, Edge
    from nuclear_simulator.sandbox.materials.liquids import Liquid

# Import libraries
from nuclear_simulator.sandbox.graphs.edges import Edge
from nuclear_simulator.sandbox.physics import (
    calc_pipe_mass_flow,
    calc_energy_from_temperature,
)


# Create class for pipes
class Pipe(Edge):
    """
    Flows fluid between two nodes based on pressure difference.
    """

    # Geometry / hydraulics
    D: float = 0.7        # [m]     Inner diameter
    L: float = 12.0       # [m]     Length
    f: float = 0.02       # [-]     Darcy friction factor (lumped)
    K_minor: float = 1.0  # [-]     Lumped minor-loss coefficient

    # Which fluid on the node this pipe moves (prefix for fields)
    tag_fluid: str = "coolant"
    tag_pressure: str = "P"

    def calculate_flows(
            self, 
            dt: float, 
            node_source: Node, 
            node_target: Node,

        ) -> dict[str, Any]:
        """
        Calculates instantaneous mass and energy flow rates (per second).
        Args:
            dt:          [s] Time step for the update. (unused)
            node_source: Source node (upstream)
            node_target: Target node (downstream)
        Returns:
            flows:       Dict of flow rates (kg/s, J/s) keyed by field name
        """

        # Get node variables
        P_up = getattr(node_source, self.tag_pressure)
        P_dn = getattr(node_target, self.tag_pressure)
        fluid_up: Liquid = getattr(node_source, self.tag_fluid)
        fluid_dn: Liquid = getattr(node_target, self.tag_fluid)

        # Get fluid properties
        rho = fluid_up.rho
        fluid_class = type(fluid_up)

        # Calculate mass flow rate from pressure drop
        m_dot = calc_pipe_mass_flow(
            P_up=P_up, 
            P_dn=P_dn, 
            rho=rho,
            D=self.D, 
            L=self.L, 
            f=self.f, 
            K_minor=self.K_minor,
        )

        # Calculate energy flow rate based on mass flow and temperature
        if m_dot > 0:
            T = fluid_up.T
            cv = fluid_up.cv
            U_dot  = calc_energy_from_temperature(m=m_dot, T=T, cv=cv)
        else:
            T = fluid_dn.T
            cv = fluid_dn.cv
            U_dot  = calc_energy_from_temperature(m=-m_dot, T=T, cv=cv)

        # Create fluid flow object
        fluid_flow: Liquid = fluid_class(
            m=m_dot, 
            U=U_dot, 
            validate=False,  # Override validation to allow negative mass flows
        )

        # Package flows
        flows = {
            self.tag_fluid: fluid_flow,
        }

        # Return output
        return flows


# Create class for pumps
class Pump(Edge):
    """
    Flows fluid between two nodes at a controllable mass flow rate.
    """

    # Control parameters
    setpoint_m_dot: float = 5000.0  # [kg/s] default commanded flow

    # Which fluid on the node this pipe moves (prefix for fields)
    tag_fluid: str = "coolant"
    tag_pressure: str = "P"

    def calculate_flows(
            self, 
            dt: float, 
            node_source: Node, 
            node_target: Node,

        ) -> dict[str, Any]:
        """
        Calculates instantaneous mass and energy flow rates (per second).
        Args:
            dt:          [s] Time step for the update. (unused)
            node_source: Source node (upstream)
            node_target: Target node (downstream)
        Returns:
            flows:       Dict of flow rates (kg/s, J/s) keyed by field name
        """

        # Get node variables
        fluid_up: Liquid = getattr(node_source, self.tag_fluid)
        fluid_dn: Liquid = getattr(node_target, self.tag_fluid)

        # Get fluid properties
        rho = fluid_up.rho
        fluid_class = type(fluid_up)

        # Get flow rate from setpoint
        m_dot = self.setpoint_m_dot

        # Calculate energy flow rate based on mass flow and temperature
        if m_dot > 0:
            T = fluid_up.T
            cv = fluid_up.cv
            U_dot  = calc_energy_from_temperature(m=m_dot, T=T, cv=cv)
        else:
            T = fluid_dn.T
            cv = fluid_dn.cv
            U_dot  = calc_energy_from_temperature(m=-m_dot, T=T, cv=cv)

        # Create fluid flow object
        fluid_flow: Liquid = fluid_class(
            m=m_dot, 
            U=U_dot, 
            validate=False,  # Override validation to allow negative mass flows
        )

        # Package flows
        flows = {
            self.tag_fluid: fluid_flow,
        }

        # Return output
        return flows
    

# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.graphs.nodes import Node
    from nuclear_simulator.sandbox.materials.nuclear import Coolant
    # Define a test node class
    class TestNode(Node):
        coolant: Coolant
        coolant_P: float
    # Create nodes and pipe
    node1 = TestNode(name="Node1", coolant=Coolant(m=1000.0, U=1e6), coolant_P=2e7)
    node2 = TestNode(name="Node2", coolant=Coolant(m=1000.0, U=1e6), coolant_P=1e7)
    pipe = Pipe(
        node_source=node1, 
        node_target=node2, 
        tag_fluid="coolant",
        tag_pressure="coolant_P", 
    )
    # Calculate flows
    flows = pipe.calculate_flows(dt=1.0, node_source=node1, node_target=node2)
    print(f"Pipe flows: m_dot={flows['coolant'].m} kg/s, U_dot={flows['coolant'].U} J/s")
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")
