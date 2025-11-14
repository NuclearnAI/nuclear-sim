
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional

# Import libraries
import math
from nuclear_simulator.sandbox.graphs.edges import Edge
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.physics import (
    calc_incompressible_mass_flow,
    calc_compressible_mass_flow,
    calc_energy_from_temperature,
)


# # Class for simple pipe (flow is proportional to pressure difference)
# class SimplePipe(Edge):
#     """
#     Flows fluid between two nodes based on pressure difference using a simple linear model.
#     Attributes:
#         m_dot:              [kg/s]       Last-calculated mass flow rate
#         K:                  [kg/(s*Pa)]  Flow conductance
#         tag_material:       [str]        Tag of the material on each node this pipe moves
#         tag_pressure:       [str]        Tag of the pressure on each node this pipe uses
#     """
#     m_dot: float | None = None
#     K: float = 1e-5
#     tag_material: str = "material"
#     tag_pressure: str = "P"

#     def get_nonstate_fields(self) -> list[str]:
#         """Return list of non-state field names."""
#         return super().get_nonstate_fields() + [
#             "tag_material",
#             "tag_pressure",
#         ]
    
#     def calculate_flows(self, dt: float) -> dict[str, Any]:
#         """
#         Calculates instantaneous mass and energy flow rates (per second).
#         Args:
#             dt:     [s] Time step for the update.
#         Returns:
#             flows:  Dict of flow rates (kg/s, J/s) keyed by field name
#         """

#         # Get node variables
#         fluid_src: Gas | Liquid = self.get_field_source(self.tag_material)
#         fluid_tgt: Gas | Liquid = self.get_field_target(self.tag_material)
#         P_src = self.get_field_source(self.tag_pressure)
#         P_tgt = self.get_field_target(self.tag_pressure)

#         # Calculate mass flow rate from pressure drop
#         dP = P_src - P_tgt
#         m_dot = self.K * dP

#         # Calculate energy flow rate based on mass flow and temperature
#         if m_dot > 0:
#             # Case: src -> tgt
#             T = fluid_src.T
#             cv = fluid_src.cv
#             U_dot = calc_energy_from_temperature(m=m_dot, T=T, cv=cv)
#         else:
#             # Case: tgt -> src
#             T = fluid_tgt.T
#             cv = fluid_tgt.cv
#             U_dot = - calc_energy_from_temperature(m=-m_dot, T=T, cv=cv)

#         # Create fluid flow object
#         if isinstance(fluid_src, Gas):
#             fluid_flow: Gas = type(fluid_src)(m=m_dot, U=U_dot, V=0.0)
#         elif isinstance(fluid_src, Liquid):
#             fluid_flow: Liquid = type(fluid_src)(m=m_dot, U=U_dot)

#         # Package flows
#         flows = {
#             self.tag_material: fluid_flow,
#         }

#         # Store state
#         self.m_dot = m_dot

#         # Return output
#         return flows
    
# class SimpleLiquidPipe(SimplePipe):
#     """Simple pipe for liquid."""
#     tag_material: str = "liquid"

# class SimpleGasPipe(SimplePipe):
#     """Simple pip for gas"""
#     tag_material: str = "gas"
#     K: float = SimpleLiquidPipe.model_fields['K'].default * 20.0


# Class for pipes
class Pipe(Edge):
    """
    Flows fluid between two nodes based on pressure difference using Darcy-Weisbach.
    Attributes:
        m_dot:              [kg/s]  Last-calculated mass flow rate
        D:                  [m]     Inner diameter
        L:                  [m]     Length
        f:                  [-]     Darcy friction factor (lumped)
        K_minor:            [-]     Lumped minor-loss coefficient
        monodirectional:    [-]     If True, flow is only allowed from source to target.
        tag_material:       [str]   Tag of the material on each node this pipe moves
        tag_pressure:       [str]   Tag of the pressure on each node this pipe uses
        MAX_FLOW_FRACTION:  [-]     Maximum fraction of node mass that can flow per time step.
    """
    m_dot: float | None = None
    D: float = 0.90
    L: float = 15.0
    f: float = 0.015
    K_minor: float = 2.0
    monodirectional: bool = False
    tag_material: str = "material"
    tag_pressure: str = "P"
    MAX_FLOW_FRACTION: float = 0.1

    def get_nonstate_fields(self) -> list[str]:
        """Return list of non-state field names."""
        return super().get_nonstate_fields() + [
            "tag_material",
            "tag_pressure",
            "MAX_FLOW_FRACTION",
        ]

    def calculate_flows(self, dt: float) -> dict[str, Any]:
        """
        Calculates instantaneous mass and energy flow rates (per second).
        Args:
            dt:     [s] Time step for the update.
        Returns:
            flows:  Dict of flow rates (kg/s, J/s) keyed by field name
        """

        # Get node variables
        fluid_src: Gas | Liquid = self.get_field_source(self.tag_material)
        fluid_tgt: Gas | Liquid = self.get_field_target(self.tag_material)
        P_src = self.get_field_source(self.tag_pressure)
        P_tgt = self.get_field_target(self.tag_pressure)

        # Get fluid properties
        if isinstance(fluid_src, Gas):
            fluid_type = Gas
        elif isinstance(fluid_src, Liquid):
            fluid_type = Liquid
        else:
            raise TypeError("Pipe material must be Gas or Liquid.")
        fluid_class = type(fluid_src)

        # Get edge parameters
        D = self.D
        L = self.L
        f = self.f
        K_minor = self.K_minor

        # Calculate constants
        A = math.pi * (D**2) / 4.0
        K_t = f * (L / D) + K_minor
        K_t = max(K_t, 1e-6)  # Prevent div by zero
        tau = 2 * A * L / K_t
        assert tau > 0.0, "Pipe inertia time constant must be positive."

        # Calculate mass flow rate from pressure drop
        if fluid_type is Gas:
            gamma = fluid_src.cp / fluid_src.cv
            m_dot = calc_compressible_mass_flow(
                P1=P_src,
                P2=P_tgt,
                T1=fluid_src.T,
                T2=fluid_tgt.T,
                MW=fluid_src.MW, 
                gamma=gamma, 
                D=D, 
                L=L, 
                f=f, 
                K_minor=K_minor,
            )
        elif fluid_type is Liquid:
            rho = (fluid_src.rho + fluid_tgt.rho) / 2
            m_dot = calc_incompressible_mass_flow(
                P1=P_src,
                P2=P_tgt,
                rho=rho,
                D=D, 
                L=L, 
                f=f, 
                K_minor=K_minor,
            )

        # Add inertia
        m_dot_prev = self.m_dot or m_dot  # Use current if None
        alpha = min(dt / tau, 1.0)
        m_dot = alpha * m_dot + (1.0 - alpha) * m_dot_prev

        # Enforce mono-directional flow if specified
        if self.monodirectional:
            m_dot = max(m_dot, 0.0)

        # Calculate energy flow rate based on mass flow and temperature
        if m_dot > 0:
            # Case: src -> tgt
            m_dot = min(m_dot, self.MAX_FLOW_FRACTION * fluid_src.m / dt)
            T = fluid_src.T
            cv = fluid_src.cv
            U_dot = calc_energy_from_temperature(m=m_dot, T=T, cv=cv)
        else:
            # Case: tgt -> src
            m_dot = max(m_dot, -self.MAX_FLOW_FRACTION * fluid_tgt.m / dt)
            T = fluid_tgt.T
            cv = fluid_tgt.cv
            U_dot = - calc_energy_from_temperature(m=-m_dot, T=T, cv=cv)

        # Create liquid flow object
        if fluid_type is Gas:
            fluid_flow: Gas = fluid_class(m=m_dot, U=U_dot, V=0.0)
        elif fluid_type is Liquid:
            fluid_flow: Liquid = fluid_class(m=m_dot, U=U_dot)

        # Package flows
        flows = {
            self.tag_material: fluid_flow,
        }

        # Store state
        self.m_dot = m_dot

        # Return output
        return flows


# Class for liquid pipes
class LiquidPipe(Pipe):
    """A Pipe for liquids."""
    tag_material: str = "liquid"

# Class for gas pipes
class GasPipe(Pipe):
    """A Pipe for gases."""
    tag_material: str = "gas"
    

# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.plants.vessels import LiquidVessel
    from nuclear_simulator.sandbox.plants.materials import PWRPrimaryWater
    # Define a test node class
    class TestNode(LiquidVessel):
        liquid: PWRPrimaryWater
    # Create nodes and pipe
    node1 = TestNode(liquid=PWRPrimaryWater(m=1000.0, U=1e6), P=2e7)
    node2 = TestNode(liquid=PWRPrimaryWater(m=1000.0, U=1e6), P=1e7)
    pipe = LiquidPipe(node_source=node1, node_target=node2)
    # Calculate flows
    flows = pipe.calculate_flows(dt=0.001)
    print(f"Pipe flows: {flows}")
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")
