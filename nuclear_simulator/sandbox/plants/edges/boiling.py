
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
from nuclear_simulator.sandbox.plants.edges.base import TransferEdge


# Boiling edge
class GasLiquidTransitionEdge(TransferEdge):
    """
    Transfers mass and energy from liquid (source) to gas (target) via boiling/condensation.
    
    Also transfers energy via thermal conduction, using conductance such that 
    the time constant for equalizing temperatures is equal to tau_phase.

    Attributes:
        tau_phase:     [s]    Time constant for phase change.
    """
    tau_phase: float = 0.01

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
        src: Liquid = self.get_contents_source()
        tgt: Gas = self.get_contents_target()
        if isinstance(src, Liquid) and isinstance(tgt, Gas):
            liq = src
            gas = tgt
            sign = 1.0
        elif isinstance(src, Gas) and isinstance(tgt, Liquid):
            liq = tgt
            gas = src
            sign = -1.0
        else:
            raise TypeError("BoilingEdge must connect Liquid and Gas materials.")
        
        # Get flows 
        flow_heat = self.calculate_heat_flow(liq, gas)
        flow_boil = self.calculate_boiling_flow(liq, gas)
        flow_cond = self.calculate_condensation_flow(liq, gas)
        flow = flow_heat + flow_boil + flow_cond
        flow = flow * sign  # Ensure correct direction

        # Return flow
        return flow
    
    def calculate_boiling_flow(self, liq: Liquid, gas: Gas) -> MaterialExchange:
        """
        Calculate boiling-driven mass and energy flow from liquid to gas.

        Args:
            liq:  Liquid material
            gas:  Gas material
        Returns:
            flow: MaterialExchange representing boiling flow from liquid -> gas
        """

        # Reference specific internal energies at boiling point
        T = liq.T
        u0_gas = liq.boiling.u_saturation_gas(T)
        u0_liq = liq.boiling.u_saturation_liquid(T)
        du = u0_gas - u0_liq  # [J/kg]

        # Calculate excess energy in liquid
        U_liq_excess = liq.U - liq.m * u0_liq

        # Calculate mass flow rate from liquid to gas
        if U_liq_excess > 0.0:
            m_eq = U_liq_excess / du
            m_dot = m_eq / self.tau_phase
        else:
            m_dot = 0.0

        # Calculate energy flow
        U_dot = m_dot * u0_gas

        # Package flow
        flow = MaterialExchange(m=m_dot, U=U_dot, V=0.0)

        # Return flow
        return flow
    
    def calculate_condensation_flow(self, liq: Liquid, gas: Gas) -> MaterialExchange:
        """
        Calculate condensation-driven mass and energy flow from gas to liquid.

        Args:
            liq:  Liquid material
            gas:  Gas material
        Returns:
            flow: MaterialExchange representing condensation flow from gas -> liquid
        """
        
        # Reference specific internal energies at boiling point
        T = gas.T
        u0_gas = liq.boiling.u_saturation_gas(T)
        u0_liq = liq.boiling.u_saturation_liquid(T)
        du = u0_gas - u0_liq  # [J/kg]

        # Calculate energy deficit in gas
        U_gas_deficit = gas.m * u0_gas - gas.U

        # Calculate mass flow rate from gas to liquid
        if U_gas_deficit > 0.0:
            m_eq = U_gas_deficit / du
            m_dot = m_eq / self.tau_phase
        else:
            m_dot = 0.0

        # Calculate energy flow
        U_dot = m_dot * u0_liq

        # Package flow (note sign: positive m_dot means liquid -> gas)
        flow = MaterialExchange(m=-m_dot, U=-U_dot, V=0.0)

        # Return flow
        return flow
    
    def calculate_heat_flow(self, liq: Liquid, gas: Gas) -> MaterialExchange:
        """
        Calculate conductive heat flow between liquid and gas.

        Args:
            liq:  Liquid material
            gas:  Gas material
        Returns:
            flow: MaterialExchange representing heat flow from liquid -> gas
        """
        
        # Calculate effective conductance for desired time constant
        C_liq = liq.cv * liq.m
        C_gas = gas.cv * gas.m
        G_eff = (C_liq * C_gas) / (self.tau_phase * (C_liq + C_gas))

        # Calculate heat flow rate
        U_dot = G_eff * (liq.T - gas.T)

        # Package flow
        flow = MaterialExchange(m=0.0, U=U_dot, V=0.0)

        # Return flow
        return flow


# Boiling edge
class BoilingEdge(GasLiquidTransitionEdge):
    """
    Transfers mass and energy from liquid (source) to gas (target) via boiling.
    
    Also transfers energy via thermal conduction, using conductance such that 
    the time constant for equalizing temperatures is equal to tau_phase.

    Attributes:
        tau_phase:     [s]    Time constant for phase change.
    """

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
        src: Liquid = self.get_contents_source()
        tgt: Gas = self.get_contents_target()
        if isinstance(src, Liquid) and isinstance(tgt, Gas):
            liq = src
            gas = tgt
            sign = 1.0
        elif isinstance(src, Gas) and isinstance(tgt, Liquid):
            liq = tgt
            gas = src
            sign = -1.0
        else:
            raise TypeError("BoilingEdge must connect Liquid and Gas materials.")
        
        # Get flows from boiling and heat transfer (no condensation)
        flow_heat = self.calculate_heat_flow(liq, gas)
        flow_boil = self.calculate_boiling_flow(liq, gas)
        flow = flow_heat + flow_boil
        flow = flow * sign  # Ensure correct direction

        # Return flow
        return flow
    

class CondensingEdge(GasLiquidTransitionEdge):
    """
    Transfers mass and energy from gas (source) to liquid (target) via condensing.
    Same as BoilingEdge but reverses source and target.

    Attributes:
        tau_phase:     [s]    Time constant for phase change.
    """

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
        src: Liquid = self.get_contents_source()
        tgt: Gas = self.get_contents_target()
        if isinstance(src, Liquid) and isinstance(tgt, Gas):
            liq = src
            gas = tgt
            sign = 1.0
        elif isinstance(src, Gas) and isinstance(tgt, Liquid):
            liq = tgt
            gas = src
            sign = -1.0
        else:
            raise TypeError("BoilingEdge must connect Liquid and Gas materials.")
        
        # Get flows from condensation and heat transfer (no boiling)
        flow_heat = self.calculate_heat_flow(liq, gas)
        flow_cond = self.calculate_condensation_flow(liq, gas)
        flow = flow_heat + flow_cond
        flow = flow * sign  # Ensure correct direction

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
        P=7e6,
        contents=PWRSecondaryWater.from_temperature(m=1000.0, T=550.0),
    )
    node_gas = graph.add_node(
        PressurizedGasVessel,
        name="Node:Gas",
        P=7e6,
        contents=PWRSecondarySteam.from_temperature_pressure(m=100.0, T=550.0, P=7e6),
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
    
