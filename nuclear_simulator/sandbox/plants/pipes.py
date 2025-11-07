
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Optional
    from nuclear_simulator.sandbox.materials.gases import Gas
    from nuclear_simulator.sandbox.materials.liquids import Liquid

# Import libraries
from nuclear_simulator.sandbox.graphs.edges import Edge
from nuclear_simulator.sandbox.physics import (
    UNIVERSAL_GAS_CONSTANT,
    calc_incompressible_mass_flow,
    calc_compressible_mass_flow,
    calc_energy_from_temperature,
)


# Create class for liquid pipes
class LiquidPipe(Edge):
    """
    Flows liquid between two nodes based on pressure difference using Darcy-Weisbach.

    Attributes:
        D:            [m]     Inner diameter
        L:            [m]     Length
        f:            [-]     Darcy friction factor (lumped)
        K_minor:      [-]     Lumped minor-loss coefficient
        tag_liquid:   [str]   Tag of the liquid on each node this pipe moves
        tag_pressure: [str]   Tag of the pressure on each node this pipe uses

    Class attributes:
        MAX_FLOW_FRACTION:  Maximum fraction of node mass that can flow per time step.
    """

    # Geometry / hydraulics
    D: float = 0.90       # [m] inner diameter (~36"); keeps v ~10 m/s at ~6,000 kg/s
    L: float = 15.0       # [m] representative segment length
    f: float = 0.015      # [-] Darcy friction factor (turbulent, smooth pipe)
    K_minor: float = 2.0  # [-] lumped minor losses (a few bends/tees)

    # Which liquid on the node this pipe moves (prefix for fields)
    tag_liquid: str = "liquid"
    tag_pressure: str = "P"

    # Stability parameters
    MAX_FLOW_FRACTION: float = 0.1

    def get_nonstate_fields(self) -> list[str]:
        """Return list of non-state field names."""
        return super().get_nonstate_fields() + [
            "tag_liquid",
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
        P_src = self.get_field_source(self.tag_pressure)
        P_tgt = self.get_field_target(self.tag_pressure)
        liquid_src: Liquid = self.get_field_source(self.tag_liquid)
        liquid_tgt: Liquid = self.get_field_target(self.tag_liquid)

        # Get liquid properties
        liquid_class = type(liquid_src)
        rho = liquid_src.rho

        # Calculate mass flow rate from pressure drop
        m_dot = calc_incompressible_mass_flow(
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
            m_dot = min(m_dot, self.MAX_FLOW_FRACTION * liquid_src.m / dt)
            T = liquid_src.T
            cv = liquid_src.cv
            U_dot = calc_energy_from_temperature(m=m_dot, T=T, cv=cv)
        else:
            m_dot = max(m_dot, -self.MAX_FLOW_FRACTION * liquid_tgt.m / dt)
            T = liquid_tgt.T
            cv = liquid_tgt.cv
            U_dot = - calc_energy_from_temperature(m=-m_dot, T=T, cv=cv)

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

    Class attributes:
        MAX_FLOW_FRACTION:  Maximum fraction of node mass that can flow per time step.
    """

    # Control parameters
    setpoint_m_dot: float = 6000.0  # [kg/s] per primary loop

    # Which liquid on the node this pipe moves (prefix for fields)
    tag_liquid: str = "liquid"

    # Stability parameters
    MAX_FLOW_FRACTION: float = 0.1

    def get_nonstate_fields(self) -> list[str]:
        """Return list of non-state field names."""
        return super().get_nonstate_fields() + [
            "tag_liquid",
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
        liquid_src: Liquid = self.get_field_source(self.tag_liquid)
        liquid_tgt: Liquid = self.get_field_target(self.tag_liquid)

        # Get liquid properties
        liquid_class = type(liquid_src)

        # Get flow rate from setpoint
        m_dot = self.setpoint_m_dot

        # Calculate energy flow rate based on mass flow and temperature
        if m_dot > 0:
            m_dot = min(m_dot, self.MAX_FLOW_FRACTION * liquid_src.m / dt)
            T = liquid_src.T
            cv = liquid_src.cv
            U_dot = calc_energy_from_temperature(m=m_dot, T=T, cv=cv)
        else:
            m_dot = max(m_dot, -self.MAX_FLOW_FRACTION * liquid_tgt.m / dt)
            T = liquid_tgt.T
            cv = liquid_tgt.cv
            U_dot = - calc_energy_from_temperature(m=-m_dot, T=T, cv=cv)

        # Create liquid flow object
        liquid_flow: Liquid = liquid_class(m=m_dot, U=U_dot)

        # Package flows
        flows = {
            self.tag_liquid: liquid_flow,
        }

        # Return output
        return flows
    

# Create class for choked/isentropic gas flow elements (valves/nozzles/orifices)
class GasChokedFlow(Edge):
    """
    Compressible-flow edge with automatic choking handled in calc_gas_mass_flow.

    Attributes:
        D:                     [m]     Effective throat diameter (area = π D² / 4)
        Cd:                    [-]     Discharge coefficient (0.6-0.9 typical; default 0.8)
        tag_gas:               [str]   Gas field tag (Gas on both nodes)
        tag_pressure:          [str]   Pressure field tag on nodes

    Class attributes:
        MAX_FLOW_FRACTION:     [-]     Max fraction of upstream mass that may leave per step
    """

    # Geometry / discharge
    D: float = 0.12
    Cd: float = 0.80

    # Field tags
    tag_gas: str = "gas"
    tag_pressure: str = "P"

    # Stability clamp
    MAX_FLOW_FRACTION: float = 0.10

    def get_nonstate_fields(self) -> list[str]:
        """Return list of non-state field names."""
        return super().get_nonstate_fields() + [
            "tag_gas",
            "tag_pressure",
            "MAX_FLOW_FRACTION",
        ]

    def calculate_flows(self, dt: float):
        """
        Calculates instantaneous mass and energy flow rates (per second).
        Args:
            dt: [s] time step (used for stability clamp)
        Returns:
            flows: Dict with a Gas object carrying m (kg/s) and U (J/s)
        """
        # Read node states
        P_src = float(self.get_field_source(self.tag_pressure))
        P_tgt = float(self.get_field_target(self.tag_pressure))
        gas_src: Gas = self.get_field_source(self.tag_gas)
        gas_tgt: Gas = self.get_field_target(self.tag_gas)
        T_src = gas_src.T
        T_tgt = gas_tgt.T

        # Get gas properties
        gas_class = type(gas_src)
        gas_R = UNIVERSAL_GAS_CONSTANT / gas_src.MOLECULAR_WEIGHT
        gas_gamma = gas_src.cp / gas_src.cv

        # Compute mass flow via external (to-be-defined) physics helper
        m_dot = calc_compressible_mass_flow(
            P_up=P_src,
            P_dn=P_tgt,
            T_up=T_src,
            T_dn=T_tgt,
            gamma=gas_gamma,
            R=gas_R,
            D=self.D,
            Cd=self.Cd,
        )

        # Compute energy flow based on mass flow and temperature
        if m_dot >= 0.0:
            m_dot = min(m_dot, self.MAX_FLOW_FRACTION * gas_src.m / dt)
            T = gas_src.T
            cv = gas_src.cv
            T0 = gas_src.T0 or 0.0
            u0 = gas_src.u0 or 0.0
            U_dot = calc_energy_from_temperature(m=m_dot, T=T, cv=cv, T0=T0, u0=u0)
        else:
            m_dot = max(m_dot, -self.MAX_FLOW_FRACTION * gas_tgt.m / dt)
            T = gas_tgt.T
            cv = gas_tgt.cv
            T0 = gas_tgt.T0 or 0.0
            u0 = gas_tgt.u0 or 0.0
            U_dot = -calc_energy_from_temperature(m=-m_dot, T=T, cv=cv, T0=T0, u0=u0)

        # Set V_dot to zero (handled by nodes)
        V_dot = 0.0

        # Create gas flow object
        gas_flow: Gas = gas_class(m=m_dot, U=U_dot, V=V_dot)

        # Package flows
        flows = {
            self.tag_gas: gas_flow
        }

        # Return output
        return flows


# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.plants.vessels import LiquidVessel
    from nuclear_simulator.sandbox.materials.nuclear import PWRPrimaryWater
    # Define a test node class
    class TestNode(LiquidVessel):
        liquid: PWRPrimaryWater
        dPdV: float = 1e7
    # Create nodes and pipe
    node1 = TestNode(liquid=PWRPrimaryWater(m=1000.0, U=1e6), P0=2e7, dPdV=2e7)
    node2 = TestNode(liquid=PWRPrimaryWater(m=1000.0, U=1e6), P0=1e7, dPdV=1e7)
    pipe = LiquidPipe(
        node_source=node1, 
        node_target=node2, 
        tag_liquid="coolant",
    )
    # Calculate flows
    flows = pipe.calculate_flows(dt=0.001)
    print(f"Pipe flows: m_dot={flows['coolant'].m} kg/s, U_dot={flows['coolant'].U} J/s")
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")
