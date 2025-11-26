
# Import libraries
import math
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Controller
from nuclear_simulator.sandbox.plants.materials import PWRSecondarySteam, PWRSecondaryWater
from nuclear_simulator.sandbox.plants.edges.pipes import LiquidPipe, GasPipe
from nuclear_simulator.sandbox.plants.edges.pumps import LiquidPump
from nuclear_simulator.sandbox.plants.subsystems.turbine import Turbine
from nuclear_simulator.sandbox.plants.vessels import PressurizedLiquidVessel, BoilingVessel, CondenserVessel



# --- Steam Generator graph

class SecondaryLoop(Graph):
    """
    Simplified steam generator secondary loop.
    Nodes:
        sg:            BoilingVessel
        condenser:     CondenserVessel
        feedwater:     PressurizedLiquidVessel
        turbine:       Turbine
    Edges:
        sg_to_turbine:          GasPipe
        turbine_to_condenser:   GasPipe
        condenser_to_feedwater: LiquidPump
        feedwater_to_sg:        LiquidPipe
    """
    power_output_setpoint: float = 20e6
    P_hot:                 float = PWRSecondaryWater.P0
    T_hot:                 float = PWRSecondaryWater.T0
    P_cold:                float = PWRSecondarySteam.P0 * 0.5
    T_cold:                float = PWRSecondarySteam.T0 * 0.9
    m_drum:                float = 25000.0
    m_turbine:             float = 10000.0
    m_condenser:           float = 50000.0
    m_feedwater:           float = 15000.0


    def __init__(self, **data) -> None:
        """Initialize secondary loop graph."""

        # Call super init
        super().__init__(**data)
        
        # Add nodes
        self.sg: BoilingVessel = self.add_node(
            BoilingVessel,
            name="SG",
            P=self.P_hot,
            gas=PWRSecondarySteam.from_temperature_pressure(
                m=self.m_drum * 0.4, T=self.T_hot, P=self.P_hot
            ),
            liquid=PWRSecondaryWater.from_temperature(
                m=self.m_drum * 0.6, T=self.T_hot
            ),
        )
        self.condenser: CondenserVessel = self.add_node(
            CondenserVessel,
            name="Condenser",
            P=self.P_cold,
            gas=PWRSecondarySteam.from_temperature_pressure(
                m=self.m_condenser * 0.1, T=self.T_cold, P=self.P_cold
            ),
            liquid=PWRSecondaryWater.from_temperature(
                m=self.m_condenser * 0.9, T=self.T_cold
            ),
        )
        self.feedwater: PressurizedLiquidVessel = self.add_node(
            PressurizedLiquidVessel,
            name="Feedwater",
            P=self.P_hot,
            contents=PWRSecondaryWater.from_temperature(
                m=self.m_feedwater, T=self.T_hot
            ),
        )

        # Calibrate mass flow rate and turbine conductance
        steam_in  = PWRSecondarySteam.from_temperature_pressure(
            m=1.0, T=self.T_hot,  P=self.P_hot
        )
        steam_out = PWRSecondarySteam.from_temperature_pressure(
            m=1.0, T=self.T_cold, P=self.P_cold
        )
        h_in  = (steam_in.U  + self.P_hot  * steam_in.V)  / steam_in.m
        h_out = (steam_out.U + self.P_cold * steam_out.V) / steam_out.m
        delta_h = h_in - h_out
        eta_turb = 0.9
        m_dot_setpoint = self.power_output_setpoint / (eta_turb * delta_h)
        dP_design = self.P_hot - self.P_cold
        K_turbine = m_dot_setpoint / math.sqrt(abs(dP_design))

        # Add graphs
        self.turbine: Turbine = self.add_graph(
            Turbine,
            name="Turbine",
            material_type=PWRSecondarySteam,
            m_dot_setpoint=m_dot_setpoint,
            K_turbine=K_turbine,
            P_inlet=self.P_hot,
            T_inlet=self.T_hot,
            m_inlet=self.m_turbine * 0.5,
            P_outlet=self.P_cold,
            T_outlet=self.T_cold,
            m_outlet=self.m_turbine * 0.5,
        )

        # Add edges
        self.sg_to_turbine: GasPipe = self.add_edge(
            edge_type=GasPipe,
            node_source=self.sg,
            node_target=self.turbine.inlet,
            name=f"Pipe:[{self.sg.name}->{self.turbine.inlet.name}]",
            alias_source={'contents': 'gas'},
            m_dot=m_dot_setpoint,
        )
        self.turbine_to_condenser: GasPipe = self.add_edge(
            edge_type=GasPipe,
            node_source=self.turbine.outlet,
            node_target=self.condenser,
            name=f"Pipe:[{self.turbine.outlet.name}->{self.condenser.name}]",
            alias_target={'contents': 'gas'},
            m_dot=m_dot_setpoint,
        )
        self.condenser_to_feedwater: LiquidPump = self.add_edge(
            edge_type=LiquidPump,
            node_source=self.condenser,
            node_target=self.feedwater,
            name=f"Pump:[{self.condenser.name}->{self.feedwater.name}]",
            alias_source={'contents': 'liquid'},
            m_dot=m_dot_setpoint,
        )
        self.feedwater_to_sg: LiquidPipe = self.add_edge(
            edge_type=LiquidPipe,
            node_source=self.feedwater,
            node_target=self.sg,
            name=f"Pipe:[{self.feedwater.name}->{self.sg.name}]",
            alias_target={'contents': 'liquid'},
            m_dot=m_dot_setpoint,
        )

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
    secondary_loop = SecondaryLoop()

    # Initialize dashboard
    dashboard = Dashboard(secondary_loop)

    # Simulate for a while
    dt = 1.0
    n_steps = 1000
    for i in range(n_steps):
        secondary_loop.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")