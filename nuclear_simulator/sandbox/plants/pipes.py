
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.materials.liquids import Liquid

# Import libraries
from nuclear_simulator.sandbox.graphs.edges import Edge
from nuclear_simulator.sandbox.physics import (
    calc_pipe_mass_flow,
    calc_energy_from_temperature,
)


# Create class for pipes
class LiquidPipe(Edge):
    """
    Flows liquid between two nodes based on pressure difference.

    Attributes:
        D:            [m]     Inner diameter
        L:            [m]     Length
        f:            [-]     Darcy friction factor (lumped)
        K_minor:      [-]     Lumped minor-loss coefficient
        tag_liquid:   [str]   Tag of the liquid on each node this pipe moves
        tag_pressure: [str]   Tag of the pressure on each node this pipe uses
    """

    # Geometry / hydraulics
    D: float = 0.7        # [m]     Inner diameter
    L: float = 12.0       # [m]     Length
    f: float = 0.02       # [-]     Darcy friction factor (lumped)
    K_minor: float = 1.0  # [-]     Lumped minor-loss coefficient

    # Which liquid on the node this pipe moves (prefix for fields)
    tag_liquid: str = "liquid"
    tag_pressure: str = "P"

    def calculate_flows(self, dt: float) -> dict[str, Any]:
        """
        Calculates instantaneous mass and energy flow rates (per second).
        Args:
            dt:     [s] Time step for the update. (unused)
        Returns:
            flows:  Dict of flow rates (kg/s, J/s) keyed by field name
        """

        # Get node variables
        P_src = self.get_field_source(self.tag_pressure)
        P_tgt = self.get_field_target(self.tag_pressure)
        liquid_src: Liquid = self.get_field_source(self.tag_liquid)
        liquid_tgt: Liquid = self.get_field_target(self.tag_liquid)

        # Get liquid properties
        rho = liquid_src.rho
        liquid_class = type(liquid_src)

        # Calculate mass flow rate from pressure drop
        m_dot = calc_pipe_mass_flow(
            P_up=P_src, 
            P_dn=P_tgt, 
            rho=rho,
            D=self.D, 
            L=self.L, 
            f=self.f, 
            K_minor=self.K_minor,
        )

        # Calculate energy flow rate based on mass flow and temperature
        if m_dot > 0:
            T = liquid_src.T
            cv = liquid_src.cv
            U_dot = calc_energy_from_temperature(m=m_dot, T=T, cv=cv)
        else:
            T = liquid_tgt.T
            cv = liquid_tgt.cv
            U_dot = calc_energy_from_temperature(m=-m_dot, T=T, cv=cv)

        # Create liquid flow object
        liquid_flow: Liquid = liquid_class(m=m_dot, U=U_dot)

        # Package flows
        flows = {
            self.tag_liquid: liquid_flow,
        }

        # Return output
        return flows


# Create class for pumps
class LiquidPump(Edge):
    """
    Flows liquid between two nodes at a controllable mass flow rate.

    Attributes:
        setpoint_m_dot:  [kg/s]  Commanded mass flow rate
        tag_liquid:      [str]   Tag of the liquid on each node this pipe moves
        tag_pressure:    [str]   Tag of the pressure on each node this pipe uses
    """

    # Control parameters
    setpoint_m_dot: float = 5000.0  # [kg/s] default commanded flow

    # Which liquid on the node this pipe moves (prefix for fields)
    tag_liquid: str = "liquid"

    def calculate_flows(self, dt: float) -> dict[str, Any]:
        """
        Calculates instantaneous mass and energy flow rates (per second).
        Args:
            dt:     [s] Time step for the update. (unused)
        Returns:
            flows:  Dict of flow rates (kg/s, J/s) keyed by field name
        """

        # Get node variables
        liquid_src: Liquid = self.get_field_source(self.tag_liquid)
        liquid_tgt: Liquid = self.get_field_target(self.tag_liquid)

        # Get liquid properties
        liquid_class = type(liquid_src)

        # Get flow rate from setpoint
        m_dot = self.setpoint_m_dot

        # Calculate energy flow rate based on mass flow and temperature
        if m_dot > 0:
            T = liquid_src.T
            cv = liquid_src.cv
            U_dot  = calc_energy_from_temperature(m=m_dot, T=T, cv=cv)
        else:
            T = liquid_tgt.T
            cv = liquid_tgt.cv
            U_dot  = calc_energy_from_temperature(m=-m_dot, T=T, cv=cv)

        # Create liquid flow object
        liquid_flow: Liquid = liquid_class(m=m_dot, U=U_dot)

        # Package flows
        flows = {
            self.tag_liquid: liquid_flow,
        }

        # Return output
        return flows
    

# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.plants.containers import LiquidVessel
    from nuclear_simulator.sandbox.materials.nuclear import PWRPrimaryWater
    # Define a test node class
    class TestNode(LiquidVessel):
        liquid: PWRPrimaryWater
        dPdV: float = 1e9
    # Create nodes and pipe
    node1 = TestNode(liquid=PWRPrimaryWater(m=1000.0, U=1e6), P0=2e7, dPdV=2e7)
    node2 = TestNode(liquid=PWRPrimaryWater(m=1000.0, U=1e6), P0=1e7, dPdV=1e7)
    pipe = LiquidPipe(
        node_source=node1, 
        node_target=node2, 
        tag_liquid="coolant",
    )
    # Calculate flows
    flows = pipe.calculate_flows(dt=1.0)
    print(f"Pipe flows: m_dot={flows['coolant'].m} kg/s, U_dot={flows['coolant'].U} J/s")
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")
