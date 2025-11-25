
# Annotation imports
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any
    from nuclear_simulator.sandbox.materials import Gas, Liquid
    from nuclear_simulator.sandbox.plants.vessels.pressurized import (
        PressurizedGasVessel, PressurizedLiquidVessel
    )

# Import libraries
from nuclear_simulator.sandbox.graphs.controllers import Controller


# Heat exchange edge
class SharedVolume(Controller):
    """
    Enforces shared volume between two pressurized fluid vessels.
    One vessel must contain a compressible fluid, the other an incompressible fluid.
    """
    REQUIRED_CONNECTIONS_READ = ('liquid_vessel', 'gas_vessel')
    REQUIRED_CONNECTIONS_WRITE = ('liquid_vessel', 'gas_vessel')

    def update(self, dt: float) -> None:
        """
        Redefine volumes of connected vessels to be equal.
        """

        # Read connections
        state_gas = self.connections_read['gas_vessel'].read()
        state_liq = self.connections_read['liquid_vessel'].read()

        # Get contents
        gas: Gas = state_gas['contents']
        liq: Liquid = state_liq['contents']

        # Get vessel properties
        V0_gas = state_gas['V0']
        V0_liq = state_liq['V0']
        P0_liq = state_liq['P0']
        dP_dV_liq = state_liq['dP_dV']
        V0_total = V0_gas + V0_liq

        # Get volumes
        V_liq = liq.V
        V_gas = V0_total - V_liq

        # Calculate new baseline volumes and pressures
        new_V0_gas = max(V_gas, 1e-3)       # Prevent zero volume
        new_V0_liq = V0_total - new_V0_gas  # Conserve total volume
        new_P0_liq = P0_liq + dP_dV_liq * (V_liq - V0_liq)

        # Package payloads
        payload_gas = {'V0': new_V0_gas}
        payload_liq = {'V0': new_V0_liq, 'P0': new_P0_liq}

        # Write new values to vessels
        self.connections_write['gas_vessel'].write(payload=payload_gas)
        self.connections_write['liquid_vessel'].write(payload=payload_liq)

        # Done
        return

# Test
def test_file():
    # Import libraries
    from pydantic import Field
    from nuclear_simulator.sandbox.plants.materials import PWRSecondarySteam, PWRSecondaryWater
    from nuclear_simulator.sandbox.plants.edges.boiling import BoilingEdge
    from nuclear_simulator.sandbox.plants.vessels.pressurized import (
        PressurizedGasVessel, PressurizedLiquidVessel
    )
    # Define dummy vessels
    class DummyGasVessel(PressurizedGasVessel):
        P: float = PWRSecondarySteam.P0 * 1.1
        contents: PWRSecondarySteam = Field(
            default_factory=lambda: PWRSecondarySteam.from_temperature_pressure(
                m=50.0, T=PWRSecondarySteam.T0, P=PWRSecondarySteam.P0
            )
        )
    class DummyLiqVessel(PressurizedLiquidVessel):
        P: float = PWRSecondaryWater.P0 * 0.9
        contents: PWRSecondaryWater = Field(
            default_factory=lambda: PWRSecondaryWater.from_temperature(
                m=5000.0, T=PWRSecondaryWater.T0
            )
        )
        def update_from_state(self, dt: float) -> None:
            """Leak out some water."""
            liq = self.contents
            liq = liq * .9999
            self.contents = liq
            return
    # Create Graph
    node_gas = DummyGasVessel()
    node_liq = DummyLiqVessel()
    edge = BoilingEdge(
        node_source=node_liq,
        node_target=node_gas,
        name="Edge:Boiling",
    )
    controller = SharedVolume(
        connections = {
            'gas_vessel': node_gas,
            'liquid_vessel': node_liq,
        }
    )
    # Simulate
    dt = 0.1
    n_steps = 1000
    print(f'Starting simulation for {n_steps} steps')
    for t in range(n_steps):
        edge.update(dt)
        node_gas.update(dt)
        node_liq.update(dt)
        controller.update(dt)
        if (t % (n_steps // 10) == 0) or (t == n_steps - 1):
            P_gas = node_gas.P
            V_gas = node_gas.contents.V
            P_liq = node_liq.P
            V_liq = node_liq.contents.V
            print(f'- {t}/{n_steps}: P_gas={P_gas:.3e} Pa, V_gas={V_gas:.3e} m3; P_liq={P_liq:.3e} Pa, V_liq={V_liq:.3e} m3')
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed!")
    