
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Controller
from nuclear_simulator.sandbox.plants.materials import PWRSecondarySteam, PWRSecondaryWater
from nuclear_simulator.sandbox.plants.edges.pipes import LiquidPipe, GasPipe
from nuclear_simulator.sandbox.plants.edges.pumps import LiquidPump
from nuclear_simulator.sandbox.plants.edges.boiling import BoilingEdge, CondensingEdge
from nuclear_simulator.sandbox.plants.edges.turbines import TurbineEdge
# from nuclear_simulator.sandbox.plants.controllers.shared_volume import SharedVolume
from nuclear_simulator.sandbox.plants.vessels import (
    PressurizedLiquidVessel, PressurizedGasVessel, PressurizerVessel, BoilingVessel
)

# Set constants
P_SECONDARY = PWRSecondarySteam.P0
T_SECONDARY = PWRSecondarySteam.T0
# m_drum = 25000
# m_turbine = 10000
# m_condenser = 50000
# m_feedwater = 15000


# class SecondarySGWater(PressurizedLiquidVessel):
#     """Secondary steam generator drum liquid volume."""
#     P: float = PWRSecondarySteam.P0
#     contents: PWRSecondaryWater = Field(
#         default_factory=lambda:
#             PWRSecondaryWater.from_temperature(m=5_000.0, T=PWRSecondarySteam.T0)
#     )

# class SecondarySGSteam(PressurizedGasVessel):
#     """Secondary steam generator drum steam volume."""
#     P: float = PWRSecondarySteam.P0
#     contents: PWRSecondarySteam = Field(
#         default_factory=lambda:
#             PWRSecondarySteam.from_temperature_pressure(
#                 m=3000.0, T=PWRSecondarySteam.T0, P=PWRSecondarySteam.P0
#             )
#     )

class SecondarySG(BoilingVessel):
    """Secondary steam generator drum volume."""
    P: float = PWRSecondarySteam.P0
    liquid: PWRSecondaryWater = Field(
        default_factory=lambda:
            PWRSecondaryWater.from_temperature(m=15_000.0, T=PWRSecondarySteam.T0)
    )
    gas: PWRSecondarySteam = Field(
        default_factory=lambda:
            PWRSecondarySteam.from_temperature_pressure(
                m=10_000.0, T=PWRSecondarySteam.T0, P=PWRSecondarySteam.P0
            )
    )

class TurbineInlet(PressurizedGasVessel):
    """Turbine inlet steam volume."""
    P: float = PWRSecondarySteam.P0
    contents: PWRSecondarySteam = Field(
        default_factory=lambda:
            PWRSecondarySteam.from_temperature_pressure(
                m=3000.0, T=PWRSecondarySteam.T0, P=PWRSecondarySteam.P0
            )
    )

class TurbineOutlet(PressurizedGasVessel):
    """Turbine outlet steam volume."""
    P: float = PWRSecondarySteam.P0
    contents: PWRSecondarySteam = Field(
        default_factory=lambda:
            PWRSecondarySteam.from_temperature_pressure(
                m=3000.0, T=PWRSecondarySteam.T0, P=PWRSecondarySteam.P0
            )
    )

# class SecondaryCondenserSteam(PressurizedGasVessel):
#     """Secondary condenser steam volume."""
#     P: float = PWRSecondarySteam.P0
#     contents: PWRSecondarySteam = Field(
#         default_factory=lambda:
#             PWRSecondarySteam.from_temperature_pressure(
#                 m=300.0, T=PWRSecondarySteam.T0, P=PWRSecondarySteam.P0
#             )
#     )

# class SecondaryCondenserWater(PressurizedLiquidVessel):
#     """Secondary condenser water volume."""
#     P: float = PWRSecondarySteam.P0
#     contents: PWRSecondaryWater = Field(
#         default_factory=lambda:
#             PWRSecondaryWater.from_temperature(m=5_000.0, T=PWRSecondarySteam.T0)
#     )

class SecondaryCondenser(BoilingVessel):

class SecondaryFeedwater(PressurizerVessel):
    """Secondary feedwater volume."""
    P: float = PWRSecondarySteam.P0
    contents: PWRSecondaryWater = Field(
        default_factory=lambda:
            PWRSecondaryWater.from_temperature(m=10_000.0, T=PWRSecondarySteam.T0)
    )



# --- Steam Generator graph

class SecondaryLoop(Graph):
    """
    Simplified steam generator secondary loop.
    Attributes:
        m_dot:  [kg/s] Mass flow rate through the secondary loop
    Nodes:
        sg_water:           SecondarySGWater
        sg_steam:           SecondarySGSteam
        turbine_in:         TurbineInlet
        turbine_out:        TurbineOutlet
        condenser_steam:    SecondaryCondenserSteam
        condenser_water:    SecondaryCondenserWater
        feedwater:          SecondaryFeedwater
    Edges:
        boil_water_to_steam:         BoilingEdge
        pipe_steam_to_turbine:       GasPipe
        turbine_edge:                TurbineEdge
        pipe_turbine_to_condenser:   GasPipe
        condense_steam_to_water:     CondensingEdge
        pump_condenser_to_feedwater: LiquidPump
        pipe_feedwater_to_sg:        LiquidPipe
    """

    # Set attributes
    m_dot: float = 10.0  # kg/s

    def __init__(self, **data) -> None:
        """Initialize secondary loop graph."""

        # Call super init
        super().__init__(**data)
        
        # Get name prefix
        prefix = '' if (self.name is None) else f"{self.name}:"
        
        # Add nodes
        self.sg_water        = self.add_node(SecondarySGWater, name=f"{prefix}SG:Water")
        self.sg_steam        = self.add_node(SecondarySGSteam, name=f"{prefix}SG:Steam")
        self.turbine_in      = self.add_node(TurbineInlet, name=f"{prefix}Turbine:Inlet")
        self.turbine_out     = self.add_node(TurbineOutlet, name=f"{prefix}Turbine:Outlet")
        self.condenser_steam = self.add_node(SecondaryCondenserSteam, name=f"{prefix}Condenser:Steam")
        self.condenser_water = self.add_node(SecondaryCondenserWater, name=f"{prefix}Condenser:Water")
        self.feedwater       = self.add_node(SecondaryFeedwater, name=f"{prefix}Feedwater")

        # Add edges
        self.boil_water_to_steam = self.add_edge(
            edge_type=BoilingEdge,
            node_source=self.sg_water,
            node_target=self.sg_steam,
            name=f"Boiling:{prefix}SG:[Water->Steam]",
            m_dot=self.m_dot,
        )
        self.pipe_steam_to_turbine = self.add_edge(
            edge_type=GasPipe,
            node_source=self.sg_steam,
            node_target=self.turbine_in,
            name=f"Pipe:{prefix}[SG->TurbineIn]",
            m_dot=self.m_dot,
        )
        self.turbine_edge = self.add_edge(
            edge_type=TurbineEdge,
            node_source=self.turbine_in,
            node_target=self.turbine_out,
            name=f"Turbine:{prefix}Turbine:[Inlet->Outlet]",
            m_dot=self.m_dot,
        )
        self.pipe_turbine_to_condenser = self.add_edge(
            edge_type=GasPipe,
            node_source=self.turbine_out,
            node_target=self.condenser_steam,
            name=f"Pipe:{prefix}Turbine:[Outlet->Condenser]",
            m_dot=self.m_dot,
        )
        self.condense_steam_to_water = self.add_edge(
            edge_type=CondensingEdge,
            node_source=self.condenser_steam,
            node_target=self.condenser_water,
            name=f"Condensing:{prefix}Condenser:[Steam->Water]",
            m_dot=self.m_dot,
        )
        self.pump_condenser_to_feedwater = self.add_edge(
            edge_type=LiquidPump,
            node_source=self.condenser_water,
            node_target=self.feedwater,
            name=f"Pump:{prefix}[Condenser->Feedwater]",
            m_dot=self.m_dot,
        )
        self.pipe_feedwater_to_sg = self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.feedwater,
            node_target=self.sg_water,
            name=f"Pipe:{prefix}[Feedwater->SG]",
            m_dot=self.m_dot,
        )

        # # Add controllers
        # self.condenser_volume_constraint = self.add_controller(
        #     controller_type=SharedVolume,
        #     name=f"Controller:{prefix}Condenser:VolumeConstraint",
        #     connections={
        #         'liquid_vessel': self.condenser_water,
        #         'gas_vessel': self.condenser_steam,
        #     }
        # )

        # Done
        return
    
    def update(self, dt: float) -> None:
        """Update the graph by one time step.
        Args:
            dt:  [s] Time step for the update.
        """
        try:
            super().update(dt)
        except Exception as e:
            raise RuntimeError(f"Error updating {self.__class__.__name__}: {e}") from e
        return


# Test
def test_file():
    """
    Test subsystem.
    """

    # Import libraries
    import matplotlib.pyplot as plt
    from nuclear_simulator.sandbox.plants.dashboard import Dashboard

    # Create graph
    secondary_loop = SecondaryLoop(m_dot=0.0)

    # Initialize dashboard
    dashboard = Dashboard(secondary_loop)

    # Simulate for a while
    dt = .001
    n_steps = 10000
    for i in range(n_steps):
        secondary_loop.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")