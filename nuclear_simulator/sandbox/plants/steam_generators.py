# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Controller
from nuclear_simulator.sandbox.plants.vessels import LiquidVessel, GasLiquidVessel
from nuclear_simulator.sandbox.plants.thermo.heat import HeatExchange
from nuclear_simulator.sandbox.plants.pipes.pipes import LiquidPipe, GasPipe
from nuclear_simulator.sandbox.plants.vessels.environment import Reservoir
from nuclear_simulator.sandbox.plants.materials import (
    PWRPrimaryWater,
    PWRSecondarySteam,
    PWRSecondaryWater,
)

# --- Primary-side nodes

class SGPrimaryHotLeg(LiquidVessel):
    """Primary-side hot leg header (reactor outlet -> SG bundle)."""
    P: float = 15.5e6
    liquid: PWRPrimaryWater = Field(
        default_factory=lambda:
            PWRPrimaryWater.from_temperature(m=3_000.0, T=590.0)
    )


class SGPrimaryBundle(LiquidVessel):
    """Primary-side U-tube bundle control volume (heat donor)."""
    P: float = 15.4e6
    liquid: PWRPrimaryWater = Field(
        default_factory=lambda:
            PWRPrimaryWater.from_temperature(m=4_000.0, T=575.0)
    )


class SGPrimaryColdLeg(LiquidVessel):
    """Primary-side cold leg header (bundle outlet -> reactor return)."""
    P: float = 15.2e6
    liquid: PWRPrimaryWater = Field(
        default_factory=lambda:
            PWRPrimaryWater.from_temperature(m=3_000.0, T=560.0)
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
        default_factory=lambda:
            PWRSecondarySteam.from_temperature_pressure(m=50.0, T=T_DRUM, P=P_DRUM)
    )
    liquid: PWRSecondaryWater = Field(
        default_factory=lambda:
            PWRSecondaryWater.from_temperature(m=5_000.0, T=T_DRUM)
    )


class SGSecondaryWaterSource(Reservoir):
    """Reservoir for secondary feedwater."""
    P: float = P_DRUM * 1.00
    T: float = T_DRUM * 1.00
    material_type: type = PWRSecondaryWater


class SGSecondarySteamSink(Reservoir):
    """Reservoir for secondary steam to environment."""
    P: float = P_DRUM * 1.00
    T: float = T_DRUM * 1.00
    material_type: type = PWRSecondarySteam


# --- Thermal coupling

class SGPrimarySecondaryHeatExchange(HeatExchange):
    """
    Heat exchange between primary bundle and secondary drum liquid.
    Attributes:
        conductance:       [W/K] Primary-secondary conductance
        tag:               [str] Tag of the material to exchange heat between
    """
    conductance: float = 5.0e7
    tag: str = "liquid"


# --- Steam Generator graph

class SteamGenerator(Graph):
    """
    Steam Generator graph.
    Attributes:
        primary_m_dot:    [kg/s] Primary-side mass flow rate
        secondary_m_dot:  [kg/s] Secondary-side mass flow rate
        use_water_source: [-]    Connect secondary feedwater inlet from reservoir
        use_steam_sink:   [-]    Connect secondary steam outlet to environment
    Nodes:
        SGPrimaryHotLeg
        SGPrimaryBundle
        SGPrimaryColdLeg
        SGSecondaryDrum
    Edges:
        LiquidPipe[SGPrimaryHotLeg -> SGPrimaryBundle]
        LiquidPipe[SGPrimaryBundle -> SGPrimaryColdLeg]
        SGPrimarySecondaryHeatExchange[SGPrimaryBundle -> SGSecondaryDrum]
    """

    # Set attributes
    primary_m_dot: float = 5000.0
    secondary_m_dot: float = 10.0
    use_water_source: bool = False
    use_steam_sink: bool = False

    def __init__(self, **data) -> None:
        super().__init__(**data)

        # Nodes
        self.hot_leg  = self.add_node(SGPrimaryHotLeg,  name="SG:Primary:HotLeg")
        self.bundle   = self.add_node(SGPrimaryBundle,  name="SG:Primary:Bundle")
        self.cold_leg = self.add_node(SGPrimaryColdLeg, name="SG:Primary:ColdLeg")
        self.drum     = self.add_node(SGSecondaryDrum,  name="SG:Secondary:Drum")

        # Edges
        # - Hot leg -> Bundle
        self.add_edge(
            edge_type=SGPrimarySecondaryHeatExchange,
            node_source=self.bundle,
            node_target=self.drum,
            name="SG:Thermal:Primary->Secondary",
        )
        # - Hot leg -> Bundle
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.hot_leg,
            node_target=self.bundle,
            name="SG:Pipe:Primary:HotLeg->Bundle",
            m_dot=self.primary_m_dot,
        )
        # - Bundle -> Cold leg
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.bundle,
            node_target=self.cold_leg,
            name="SG:Pipe:Primary:Bundle->ColdLeg",
            m_dot=self.primary_m_dot,
        )

        # Optionally add feedwater source
        if self.use_water_source:
            self.water_source = self.add_node(
                SGSecondaryWaterSource,
                name="Env:Secondary:WaterSource"
            )
            self.add_edge(
                edge_type=LiquidPipe,
                node_source=self.water_source,
                node_target=self.drum,
                name="Pipe:Secondary:Env->Drum",
                m_dot=self.secondary_m_dot,
            )

        # Optionally add steam sink
        if self.use_steam_sink:
            self.steam_sink = self.add_node(
                SGSecondarySteamSink, 
                name="Env:Secondary:SteamSink"
            )
            self.add_edge(
                edge_type=GasPipe,
                node_source=self.drum,
                node_target=self.steam_sink,
                name="Pipe:Secondary:Drum->Env",
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


# Test
def test_file():
    """
    Smoke test for integrated Plant construction and simulation.
    """

    # Import libraries
    import matplotlib.pyplot as plt
    from nuclear_simulator.sandbox.plants.dashboard import Dashboard
    from nuclear_simulator.sandbox.plants.pipes.pumps import LiquidPump
    from nuclear_simulator.sandbox.materials import Material

    # Make steam generator
    sg = SteamGenerator(
        use_steam_sink=True,
        use_water_source=True,
        secondary_m_dot=0.0,
    )
    # Add pump from steam generator cold leg to hot leg
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
    dt = .001
    n_steps = 10000
    for i in range(n_steps):
        sg.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

