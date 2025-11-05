# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Node
from nuclear_simulator.sandbox.plants.pipes import LiquidPipe
from nuclear_simulator.sandbox.plants.thermo import ThermalCoupling, BoilingEdge
from nuclear_simulator.sandbox.plants.containers import LiquidVessel
from nuclear_simulator.sandbox.materials.nuclear import PWRPrimaryWater, PWRSecondaryWater, PWRSecondarySteam


# ... Define nodes here


class SteamGenerator(Graph):

    def __init__(self, conductance: float = 2.0e7, **data) -> None:
        super().__init__(**data)

        # Add nodes
        primary_hot_leg  = self.add_node(SGPrimaryHotLeg,  name="SG:Primary:HotLeg")
        primary_cold_leg = self.add_node(SGPrimaryColdLeg, name="SG:Primary:ColdLeg")
        primary_bundle = self.add_node(SGPrimaryBundle, name="SG:Primary:Bundle")
        secondary_water = self.add_node(SGSecondaryWater, name="SG:Secondary:Water")
        secondary_steam = self.add_node(SGSecondarySteam, name="SG:Secondary:Steam")

        # Add pipes along primary
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=primary_hot_leg,
            node_target=primary_bundle,
            name="SG:Primary:HotLeg→BundleIn",
        )
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=primary_bundle,
            node_target=primary_cold_leg,
            name="SG:Primary:BundleOut→ColdLeg",
        )

        # Add thermal coupling between primary bundle and secondary side
        self.add_edge(
            edge_type=ThermalCoupling,
            node_source=primary_bundle,
            node_target=secondary_water,
            name="SG:ThermalCoupling:Primary→Secondary",
            conductance=conductance,
        )

        # Add boiling edge along secondary side of bundle
        self.add_edge(
            edge_type=BoilingEdge,
            node_source=secondary_water,
            node_target=secondary_steam,
            name="SG:Secondary:Water→Steam",
        )

        # Done
        return

    # Convenience accessors
    @property
    def primary_in(self) -> 'Node':
        return self.get_component_from_name("SG:Primary:HotLeg")

    @property
    def primary_out(self) -> 'Node':
        return self.get_component_from_name("SG:Primary:ColdLeg")
    
    @property
    def water_in(self) -> 'Node':
        return self.get_component_from_name("SG:Secondary:Water")
    
    @property
    def steam_out(self) -> 'Node':
        return self.get_component_from_name("SG:Secondary:Steam")


# Test
def test_file():
    """
    Smoke test for SteamGenerator construction and a single update tick.
    """
    sg = SteamGenerator()
    dt = 1.0  # [s]
    sg.update(dt)
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

