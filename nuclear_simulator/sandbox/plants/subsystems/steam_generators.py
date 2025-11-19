# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Controller
from nuclear_simulator.sandbox.plants.vessels import PressurizedLiquidVessel, PressurizedGasVessel
from nuclear_simulator.sandbox.plants.edges.heat import HeatExchange
from nuclear_simulator.sandbox.plants.edges.pipes import LiquidPipe, GasPipe
from nuclear_simulator.sandbox.plants.edges.boiling import BoilingEdge
from nuclear_simulator.sandbox.plants.vessels.environment import Reservoir
from nuclear_simulator.sandbox.plants.materials import (
    PWRPrimaryWater,
    PWRSecondarySteam,
    PWRSecondaryWater,
)


# --- Primary-side nodes

class SGPrimaryHotLeg(PressurizedLiquidVessel):
    """Primary-side hot leg header (reactor outlet -> SG bundle)."""
    P: float = PWRPrimaryWater.P0
    contents: PWRPrimaryWater = Field(
        default_factory=lambda:
            PWRPrimaryWater.from_temperature(m=3_000.0, T=PWRPrimaryWater.T0)
    )


class SGPrimaryBundle(PressurizedLiquidVessel):
    """Primary-side U-tube bundle control volume (heat donor)."""
    P: float = PWRPrimaryWater.P0
    contents: PWRPrimaryWater = Field(
        default_factory=lambda:
            PWRPrimaryWater.from_temperature(m=4_000.0, T=PWRPrimaryWater.T0)
    )


class SGPrimaryColdLeg(PressurizedLiquidVessel):
    """Primary-side cold leg header (bundle outlet -> reactor return)."""
    P: float = PWRPrimaryWater.P0
    contents: PWRPrimaryWater = Field(
        default_factory=lambda:
            PWRPrimaryWater.from_temperature(m=3_000.0, T=PWRPrimaryWater.T0)
    )


# --- Secondary-side nodes

class SGSecondaryDrumWater(PressurizedLiquidVessel):
    """Secondary drum liquid volume."""
    P: float = PWRSecondarySteam.P0
    contents: PWRSecondaryWater = Field(
        default_factory=lambda:
            PWRSecondaryWater.from_temperature(m=5_000.0, T=PWRSecondarySteam.T0)
    )

class SGSecondaryDrumSteam(PressurizedGasVessel):
    """Secondary drum steam volume."""
    P: float = PWRSecondarySteam.P0
    contents: PWRSecondarySteam = Field(
        default_factory=lambda:
            PWRSecondarySteam.from_temperature_pressure(
                m=500.0, T=PWRSecondarySteam.T0, P=PWRSecondarySteam.P0
            )
    )



# --- Environment nodes

class SGSecondaryWaterSource(Reservoir):
    """Reservoir for secondary feedwater."""
    material_type: type = PWRSecondaryWater
    P: float = PWRSecondarySteam.P0
    T: float = PWRSecondarySteam.T0


class SGSecondarySteamSink(Reservoir):
    """Reservoir for secondary steam to environment."""
    material_type: type = PWRSecondarySteam
    P: float = PWRSecondarySteam.P0
    T: float = PWRSecondarySteam.T0


# --- Steam Generator graph

class SteamGenerator(Graph):
    """
    Steam Generator graph.
    """

    # Set attributes
    primary_m_dot: float = 5000.0
    secondary_m_dot: float = 1000.0
    conductance_primary_secondary: float = 5.0e7
    use_water_source: bool = False
    use_steam_sink: bool = False

    def __init__(self, **data) -> None:
        super().__init__(**data)

        # Nodes
        self.hot_leg  = self.add_node(SGPrimaryHotLeg,  name=f"{self.name}:Primary:HotLeg")
        self.bundle   = self.add_node(SGPrimaryBundle,  name=f"{self.name}:Primary:Bundle")
        self.cold_leg = self.add_node(SGPrimaryColdLeg, name=f"{self.name}:Primary:ColdLeg")
        self.drum_liq = self.add_node(SGSecondaryDrumWater, name=f"{self.name}:Secondary:Drum:Water")
        self.drum_gas = self.add_node(SGSecondaryDrumSteam, name=f"{self.name}:Secondary:Drum:Steam")
        # Primary Pipes
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.hot_leg,
            node_target=self.bundle,
            name=f"Pipe:{self.name}:Primary:HotLeg->Bundle",
            m_dot=self.primary_m_dot,
        )
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.bundle,
            node_target=self.cold_leg,
            name=f"Pipe:{self.name}:Primary:Bundle->ColdLeg",
            m_dot=self.primary_m_dot,
        )

        # Thermal coupling
        self.add_edge(
            edge_type=HeatExchange,
            node_source=self.bundle,
            node_target=self.drum_liq,
            name=f"Heat:{self.name}:Primary->Secondary",
            conductance=self.conductance_primary_secondary,
        )
        self.add_edge(
            edge_type=BoilingEdge,
            node_source=self.drum_liq,
            node_target=self.drum_gas,
            name=f"Boiling:{self.name}:Secondary:Water->Steam",
        )

        # Optional feedwater source
        if self.use_water_source:
            self.water_source = self.add_node(
                SGSecondaryWaterSource,
                name=f"Env:{self.name}:Secondary:WaterSource"
            )
            self.add_edge(
                edge_type=LiquidPipe,
                node_source=self.water_source,
                node_target=self.drum_liq,
                name=f"Pipe:{self.name}:Secondary:Env->Drum",
                m_dot=self.secondary_m_dot,
            )

        # Optional steam sink
        if self.use_steam_sink:
            self.steam_sink = self.add_node(
                SGSecondarySteamSink, 
                name=f"Env:{self.name}:Secondary:SteamSink"
            )
            self.add_edge(
                edge_type=GasPipe,
                node_source=self.drum_gas,
                node_target=self.steam_sink,
                name=f"Pipe:{self.name}:Secondary:Drum->Env",
                m_dot=self.secondary_m_dot,
            )

        # Done
        return

    # --- Convenience accessors ---

    @property
    def primary_in(self) -> SGPrimaryHotLeg:
        return self.hot_leg

    @property
    def primary_out(self) -> SGPrimaryColdLeg:
        return self.cold_leg
    
    @property
    def secondary_in(self) -> SGSecondaryDrumWater:
        return self.drum_liq
    
    @property
    def secondary_out(self) -> SGSecondaryDrumSteam:
        return self.drum_gas


# Test
def test_file():
    """
    Smoke test for integrated Plant construction and simulation.
    """

    # Import libraries
    import matplotlib.pyplot as plt
    from nuclear_simulator.sandbox.plants.dashboard import Dashboard
    from nuclear_simulator.sandbox.plants.edges.pumps import LiquidPump

    # Make steam generator
    sg = SteamGenerator(
        use_steam_sink=True,
        use_water_source=True,
    )

    # Connect primary in to out with a pump to circulate (just for testing)
    sg.add_edge(
        edge_type=LiquidPump,
        node_source=sg.primary_out,
        node_target=sg.primary_in,
        name="Primary:Pump:SG:ColdLeg->HotLeg",
        m_dot=sg.primary_m_dot,
    )

    # Initialize dashboard
    dashboard = Dashboard(sg)

    # Simulate for a while
    dt = .01
    n_steps = 100000
    dashboard.plot_every = n_steps // 1000
    for i in range(n_steps):
        sg.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

