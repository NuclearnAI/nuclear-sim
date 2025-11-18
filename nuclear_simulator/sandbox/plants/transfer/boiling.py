
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any
    from nuclear_simulator.sandbox.materials.base import Material

# Import libraries
from nuclear_simulator.sandbox.materials.base import MaterialExchange
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.plants.transfer.base import TransferEdge


# Boiling edge
class BoilingEdge(TransferEdge):
    """
    Transfers mass and energy from liquid (source) to gas (target) via boiling.

    Attributes:
        tau_boil:      [s]  Time constant for boiling from liquid to gas.
        tau_condense:  [s]  Optional time constant for condensation from gas to liquid.
    """
    tau_boil: float = 1.0
    tau_condense: float | None = 1.0

    def calculate_material_flow(self, dt: float) -> MaterialExchange:
        """
        Calculates boiling-driven material transfer from source (liquid) to
        target (gas), per second.

        Args:
            dt:  [s]  Time step (used only to cap flows; we return per-second flows)

        Returns:
            flow: MaterialExchange object representing mass and energy flow
                  from source -> target (kg/s, J/s).
        """

        # Get materials
        liq: Liquid = self.get_contents_source()
        gas: Gas = self.get_contents_target()
        if not isinstance(liq, Liquid):
            raise TypeError("BoilingEdge source material must be Liquid.")
        if not isinstance(gas, Gas):
            raise TypeError("BoilingEdge target material must be Gas.")

        # Reference specific internal energies at boiling point
        u0_liq = liq.u0
        u0_gas = gas.u0
        du = u0_gas - u0_liq  # [J/kg]

        # Boil off excess energy from liquid
        m_boil = 0
        U_liq_excess = liq.U - liq.m * u0_liq
        if U_liq_excess > 0.0:
            m_eq = U_liq_excess / du
            m_boil = m_eq / self.tau_boil

        # Condense gas if target gas is below boiling energy
        m_cond = 0
        U_gas_deficit = gas.m * u0_gas - gas.U
        if (U_gas_deficit > 0.0) and (self.tau_condense is not None):
            m_eq = U_gas_deficit / du
            m_cond = m_eq / self.tau_condense

        # Calcualte mass transfer rate
        m_dot = m_boil - m_cond

        # Calulate energy transfer rate
        if m_dot >= 0:
            # Equation: U_dot = m_dot * u0_liq + m_dot * (u0_gas - u0_liq) = m_dot * u0_gas
            U_dot = m_dot * u0_gas
        else:
            # Equation: U_dot = m_dot * u0_gas - m_dot * (u0_gas - u0_liq) = m_dot * u0_liq
            U_dot = m_dot * u0_liq

        # Package flow (positive m_dot means source -> target)
        flow = MaterialExchange(m=m_dot, U=U_dot, V=0.0)

        # Return flow
        return flow
    

# Test
def test_file():
    """Simple test to verify file loads without errors."""
    # Import libraries
    from nuclear_simulator.sandbox.graphs import Graph
    from nuclear_simulator.sandbox.plants.vessels import PressurizedLiquidVessel, PressurizedGasVessel
    from nuclear_simulator.sandbox.plants.materials import PWRSecondaryWater, PWRSecondarySteam
    # Define graph
    graph = Graph()
    # Create nodes and edge
    node_liq = graph.add_node(
        PressurizedLiquidVessel,
        name="Node:Liquid",
        contents=PWRSecondaryWater.from_temperature(m=1000.0, T=550.0),
        P=7e6,
    )
    node_gas = graph.add_node(
        PressurizedGasVessel,
        name="Node:Gas",
        contents=PWRSecondarySteam.from_temperature_pressure(m=100.0, T=550.0, P=7e6),
        P=7e6,
    )
    graph.add_edge(
        BoilingEdge,
        node_source=node_liq,
        node_target=node_gas,
        name="Edge:Boiling",
        tau_phase=1.0,
    )
    # Simulate
    dt = 0.1
    for t in range(10000):
        graph.update(dt)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")
    
