
# Import libraries
from pydantic import Field, ConfigDict
from nuclear_simulator.sandbox.plants.thermograph import Node
from nuclear_simulator.sandbox.materials.nuclear import Coolant
from nuclear_simulator.sandbox.physics import calc_pipe_mass_flow


# Helper
def _coolant(m: float, T: float) -> Coolant:
    return Coolant.from_temperature(m=m, T=T)


class SGHotLeg(Node):
    """
    Small control volume representing the hot outlet header from the reactor.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Material
    coolant: Coolant = Field(default_factory=lambda: _coolant(m=500.0, T=580.0))

    # Coolant pressure parameters
    coolant_P: float = 15.4e6
    coolant_P0: float | None = None
    coolant_V0: float | None = None
    coolant_dPdV: float = 1.0e9

    def model_post_init(self, __context) -> None:
        if self.coolant_P0 is None:
            self.coolant_P0 = self.coolant_P
        if self.coolant_V0 is None:
            self.coolant_V0 = self.coolant.V
        self.coolant_P = self.coolant_P0 + self.coolant_dPdV * (self.coolant.V - self.coolant_V0)
        return

    def update_from_state(self, dt: float) -> None:
        # Update pressure from cushion model (absolute, not incremental)
        self.coolant_P = self.coolant_P0 + self.coolant_dPdV * (self.coolant.V - self.coolant_V0)
        return


class SGPrimHot(Node):
    """
    Steam generator primary-side inlet plenum (hot header).
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Material
    coolant: Coolant = Field(default_factory=lambda: _coolant(m=600.0, T=575.0))

    # Coolant pressure parameters
    coolant_P: float = 15.3e6
    coolant_P0: float | None = None
    coolant_V0: float | None = None
    coolant_dPdV: float = 1.0e9

    def model_post_init(self, __context) -> None:
        if self.coolant_P0 is None:
            self.coolant_P0 = self.coolant_P
        if self.coolant_V0 is None:
            self.coolant_V0 = self.coolant.V
        self.coolant_P = self.coolant_P0 + self.coolant_dPdV * (self.coolant.V - self.coolant_V0)
        return

    def update_from_state(self, dt: float) -> None:
        self.coolant_P = self.coolant_P0 + self.coolant_dPdV * (self.coolant.V - self.coolant_V0)
        return


class SGPrimCold(Node):
    """
    Steam generator primary-side outlet plenum (cold header).
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Material
    coolant: Coolant = Field(default_factory=lambda: _coolant(m=700.0, T=540.0))

    # Coolant pressure parameters
    coolant_P: float = 15.1e6
    coolant_P0: float | None = None
    coolant_V0: float | None = None
    coolant_dPdV: float = 1.0e9

    def model_post_init(self, __context) -> None:
        if self.coolant_P0 is None:
            self.coolant_P0 = self.coolant_P
        if self.coolant_V0 is None:
            self.coolant_V0 = self.coolant.V
        self.coolant_P = self.coolant_P0 + self.coolant_dPdV * (self.coolant.V - self.coolant_V0)
        return

    def update_from_state(self, dt: float) -> None:
        self.coolant_P = self.coolant_P0 + self.coolant_dPdV * (self.coolant.V - self.coolant_V0)
        return


class SGColdLeg(Node):
    """
    Small control volume representing the return header to the reactor.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Material
    coolant: Coolant = Field(default_factory=lambda: _coolant(m=500.0, T=545.0))

    # Coolant pressure parameters
    coolant_P: float = 15.0e6
    coolant_P0: float | None = None
    coolant_V0: float | None = None
    coolant_dPdV: float = 1.0e9

    def model_post_init(self, __context) -> None:
        if self.coolant_P0 is None:
            self.coolant_P0 = self.coolant_P
        if self.coolant_V0 is None:
            self.coolant_V0 = self.coolant.V
        self.coolant_P = self.coolant_P0 + self.coolant_dPdV * (self.coolant.V - self.coolant_V0)
        return

    def update_from_state(self, dt: float) -> None:
        self.coolant_P = self.coolant_P0 + self.coolant_dPdV * (self.coolant.V - self.coolant_V0)
        return
    

# Test
def test_file():
    # Import libraries
    from nuclear_simulator.sandbox.graphs import Graph
    from nuclear_simulator.sandbox.plants.pipes import Pipe, Pump
    from nuclear_simulator.sandbox.plants.reactor import Reactor
    # Create graph
    graph = Graph()
    # Create components
    reactor = graph.add_node(Reactor, name="Reactor")
    sg_hot_leg = graph.add_node(SGHotLeg, name="SG Hot Leg")
    sg_prim_hot = graph.add_node(SGPrimHot, name="SG Primary Hot")
    sg_prim_cold = graph.add_node(SGPrimCold, name="SG Primary Cold")
    sg_cold_leg = graph.add_node(SGColdLeg, name="SG Cold Leg")
    pump_cl_r = graph.add_edge(
        Pump, 
        node_source_id=sg_cold_leg.id, 
        node_target_id=reactor.id, 
        name="Reactor Feed Pump",
    )
    pump_r_hl = graph.add_edge(
        Pipe, 
        node_source_id=reactor.id, 
        node_target_id=sg_hot_leg.id, 
        name="Reactor Outlet Pipe"
    )
    pipe_hl_ph = graph.add_edge(
        Pipe, 
        node_source_id=sg_hot_leg.id, 
        node_target_id=sg_prim_hot.id, 
        name="SG Hot Leg Pipe"
    )
    pipe_pc_cl = graph.add_edge(
        Pipe, 
        node_source_id=sg_prim_cold.id, 
        node_target_id=sg_cold_leg.id, 
        name="SG Cold Leg Pipe"
    )
    return