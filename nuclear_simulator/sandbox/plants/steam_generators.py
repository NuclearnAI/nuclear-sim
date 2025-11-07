# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph
from nuclear_simulator.sandbox.plants.vessels import LiquidVessel, GasLiquidVessel
from nuclear_simulator.sandbox.plants.pipes import LiquidPipe, LiquidPump
from nuclear_simulator.sandbox.plants.thermo import ThermalCoupling
from nuclear_simulator.sandbox.materials.nuclear import (
    PWRPrimaryWater,
    PWRSecondarySteam,
    PWRSecondaryWater,
)

# --- Primary-side nodes

class SGPrimaryHotLeg(LiquidVessel):
    """Primary-side hot leg header (reactor outlet → SG bundle)."""
    P0: float = 15.5e6
    dPdV: float = 2.0e7
    liquid: PWRPrimaryWater = Field(
        default_factory=lambda: PWRPrimaryWater.from_temperature(m=3_000.0, T=590.0)
    )


class SGPrimaryBundle(LiquidVessel):
    """Primary-side U-tube bundle control volume (heat donor)."""
    P0: float = 15.4e6
    dPdV: float = 2.0e7
    liquid: PWRPrimaryWater = Field(
        default_factory=lambda: PWRPrimaryWater.from_temperature(m=4_000.0, T=575.0)
    )


class SGPrimaryColdLeg(LiquidVessel):
    """Primary-side cold leg header (bundle outlet → reactor return)."""
    P0: float = 15.2e6
    dPdV: float = 2.0e7
    liquid: PWRPrimaryWater = Field(
        default_factory=lambda: PWRPrimaryWater.from_temperature(m=3_000.0, T=560.0)
    )


# --- Secondary-side nodes

# Constants
P_DRUM = PWRSecondarySteam.P0  # ~7 MPa saturation
T_DRUM = PWRSecondarySteam.T0  # ~559 K saturation

class SGSecondaryDrum(GasLiquidVessel):
    """
    Secondary drum: gas-liquid vessel holding saturated water + steam.
    """
    P: float = P_DRUM
    gas: PWRSecondarySteam = Field(
        default_factory=lambda: PWRSecondarySteam.from_temperature_pressure(
            m=50.0,
            T=T_DRUM,
            P=P_DRUM
        )
    )
    liquid: PWRSecondaryWater = Field(
        default_factory=lambda: PWRSecondaryWater.from_temperature(
            m=5_000.0,
            T=T_DRUM
        )
    )

# --- Steam Generator graph

class SteamGenerator(Graph):
    """
    Steam generator graph:
      Primary:   HotLeg → Bundle → ColdLeg
      Heat:      Bundle → Drum
      Secondary: Drum
    """

    def __init__(self, UA_primary_secondary: float = 2.0e7, **data) -> None:
        super().__init__(**data)

        # Nodes
        hot_leg   = self.add_node(SGPrimaryHotLeg,  name="SG:Primary:HotLeg")
        bundle    = self.add_node(SGPrimaryBundle,  name="SG:Primary:Bundle")
        cold_leg  = self.add_node(SGPrimaryColdLeg, name="SG:Primary:ColdLeg")
        drum      = self.add_node(SGSecondaryDrum,  name="SG:Secondary:Drum")

        # Primary hydraulics
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=hot_leg,
            node_target=bundle,
            name="SG:Primary:Pipe:HotLeg→Bundle",
            tag_liquid="liquid",
        )
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=bundle,
            node_target=cold_leg,
            name="SG:Primary:Pipe:Bundle→ColdLeg",
            tag_liquid="liquid",
        )

        # Heat transfer (primary → secondary liquid in drum)
        self.add_edge(
            edge_type=ThermalCoupling,
            node_source=bundle,
            node_target=drum,
            conductance=UA_primary_secondary,
            tag="liquid",
            name="SG:Thermal:Bundle→DrumLiquid",
            tag_liquid="liquid",
        )

        # Done
        return

    # Convenience accessors
    @property
    def primary_in(self) -> SGPrimaryHotLeg:
        return self.get_component_from_name("SG:Primary:HotLeg")

    @property
    def bundle(self) -> SGPrimaryBundle:
        return self.get_component_from_name("SG:Primary:Bundle")

    @property
    def primary_out(self) -> SGPrimaryColdLeg:
        return self.get_component_from_name("SG:Primary:ColdLeg")

    @property
    def drum(self) -> SGSecondaryDrum:
        return self.get_component_from_name("SG:Secondary:Drum")


# Test
def test_file():
    """
    Smoke test for integrated Plant construction and simulation.
    """
    # Create plant
    sg = SteamGenerator()
    # Update
    dt = .1
    sg.update(dt)
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")