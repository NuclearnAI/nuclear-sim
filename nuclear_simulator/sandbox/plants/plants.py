
# Import libraries
from pydantic import Field
from nuclear_simulator.sandbox.graphs import Graph, Controller
from nuclear_simulator.sandbox.plants.pipes import LiquidPipe, LiquidPump, GasChokedFlow
from nuclear_simulator.sandbox.plants.reactors import Reactor
from nuclear_simulator.sandbox.plants.environment import Reservoir
from nuclear_simulator.sandbox.plants.steam_generators import SteamGenerator
from nuclear_simulator.sandbox.materials.nuclear import (
    PWRPrimaryWater,
    PWRSecondaryWater,
    PWRSecondarySteam,
)


# Define plant
class Plant(Graph):
    """
    Nuclear power plant graph.
    """

    def __init__(
            self,
            *,
            secondary_P: float = 6.0e6,
            secondary_T: float = 510.0,
            env_steam_P: float = 1.0e5,
            env_steam_T: float = 300.0,
            **data,
        ) -> None:
        super().__init__(**data)

        # --- Subgraphs ---
        reactor: Reactor = self.add_graph(Reactor, name="Reactor")
        sg: SteamGenerator = self.add_graph(SteamGenerator, name="SteamGenerator")

        # --- Boundary reservoirs ---
        env_water = self.add_node(
            Reservoir,
            name="Reservoir:SecondaryWater",
            P=secondary_P,
            T=secondary_T,
            material_type=PWRSecondaryWater,
        )
        env_steam = self.add_node(
            Reservoir,
            name="Reservoir:SecondarySteam",
            P=env_steam_P,
            T=env_steam_T,
            material_type=PWRSecondarySteam,
        )

        # --- Primary loop plumbing ---
        # ReactorCoolant → SG:Primary:HotLeg
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=reactor.coolant,
            node_target=sg.primary_in,
            name="Primary:Pipe:Reactor→SG:HotLeg",
        )
        # SG:Primary:ColdLeg → ReactorCoolant (with pump)
        self.add_edge(
            edge_type=LiquidPump,
            node_source=sg.primary_out,
            node_target=reactor.coolant,
            name="Primary:Pump:SG:ColdLeg→Reactor",
        )

        # --- Secondary attachments (outside SG) ---
        # Feedwater in: FW:Reservoir → SG.drum.liquid
        self.add_edge(
            edge_type=LiquidPipe,
            node_source=env_water,
            node_target=sg.drum,
            name="Secondary:Pipe:FW→DrumLiquid",
        )
        # Steam out: SG.drum.gas → Steam:Environment
        self.add_edge(
            edge_type=GasChokedFlow,
            node_source=sg.drum,
            node_target=env_steam,
            name="Secondary:Pipe:DrumGas→SteamEnv",
        )

        # --- Monitoring controller ---

        # Create monitor controller
        monitor = self.add_controller(
            controller_type=Controller,
            name="Plant:Monitor",
        )

        # Connect monitor to key components
        for comp in list(self.get_nodes().values()) + list(self.get_edges().values()):
            monitor.add_read_connection(
                name=comp.name or comp.id, 
                component=comp,
            )

        # Done
        return

    # ------------- Convenience accessors -------------

    @property
    def reactor(self) -> Reactor:
        return self.get_component_from_name("Reactor")

    @property
    def steam_generator(self) -> SteamGenerator:
        return self.get_component_from_name("SteamGenerator")

    @property
    def feedwater_reservoir(self) -> Reservoir:
        return self.get_component_from_name("FW:Reservoir")

    @property
    def steam_environment(self) -> Reservoir:
        return self.get_component_from_name("Steam:Environment")
    
    @property
    def monitor(self) -> Controller:
        return self.get_component_from_name("Plant:Monitor")


# Test
def test_file():
    """
    Smoke test for integrated Plant construction and simulation.
    """

    # Import libraries
    from nuclear_simulator.sandbox.dev.plotting import plot_dict

    # Create plant
    plant = Plant()

    # Initialize time series for monitoring
    monitor = plant.monitor
    monitor.update()
    m_data = {}
    U_data = {}
    V_data = {}
    T_data = {}
    P_data = {}
    # for node_name, node_state in monitor.monitor.items():
    #     if 'P' in node_state:
    #         P_data[f'{node_name}'] = [node_state['P']]
    #     if 'gas' in node_state:
    #         gas = node_state['gas']
    #         m_data[f'{node_name}_gas_m']     = [gas.m]
    #         U_data[f'{node_name}_gas_U']     = [gas.U]
    #         V_data[f'{node_name}_gas_V']     = [gas.V]
    #         T_data[f'{node_name}_gas_T']     = [gas.T]
    #     if 'liquid' in node_state:
    #         liquid = node_state['liquid']
    #         m_data[f'{node_name}_liquid_m']  = [liquid.m]
    #         U_data[f'{node_name}_liquid_U']  = [liquid.U]
    #         V_data[f'{node_name}_liquid_V']  = [liquid.V]
    #         T_data[f'{node_name}_liquid_T']  = [liquid.T]
    for node_name, node_state in monitor.monitor.items():
        if 'P' in node_state:
            P_data[f'{node_name}'] = [node_state['P']]
        for tag in ['gas', 'liquid', 'solid', 'fuel', 'material']:
            if tag in node_state:
                material = node_state[tag]
                m_data[f'{node_name}_{tag}_m']     = [material.m]
                U_data[f'{node_name}_{tag}_U']     = [material.U]
                V_data[f'{node_name}_{tag}_V']     = [material.V]
                T_data[f'{node_name}_{tag}_T']     = [material.T]
                if hasattr(material, 'P'):
                    P_data[f'{node_name}_{tag}_P'] = [material.P]

    # Create plots
    fig_m, _ = plot_dict(m_data, title="Mass (m)")
    fig_U, _ = plot_dict(U_data, title="Energy (U)")
    fig_V, _ = plot_dict(V_data, title="Volume (V)")
    fig_T, _ = plot_dict(T_data, title="Temperature (T)")
    fig_P, _ = plot_dict(P_data, title="Pressure (P)")

    # Simulate for a while
    dt = .001
    n_steps = 10000
    for i in range(n_steps):
        
        # Get current state
        drum = plant.get_component("SG:Secondary:Drum")
        steam  = drum.gas
        water  = drum.liquid
        m_tot  = steam.m + water.m
        U_tot  = steam.U + water.U
        V_tot  = steam.V + water.V

        # Log state
        print(f"{i}/{n_steps}")
        print(f"  -- steam={steam}")
        print(f"  -- water={water}")
        print(f"  -- total=(m={m_tot:.3f} kg, U={U_tot:.6e} J, V={V_tot:.6e} m³)")
        print(f"  -- T_gas={steam.T:.3f} K")
        print(f"  -- T_liq={water.T:.3f} K")
        print(f"  -- P_drum={drum.P:.6e} Pa")

        # Update
        plant.update(dt)

        # Add to time series
        monitor.update()
        for node_name, node_state in monitor.monitor.items():
            if 'P' in node_state:
                P_data[f'{node_name}'].append(node_state['P'])
            for tag in ['gas', 'liquid', 'solid', 'fuel', 'material']:
                if tag in node_state:
                    material = node_state[tag]
                    m_data[f'{node_name}_{tag}_m'].append(material.m)
                    U_data[f'{node_name}_{tag}_U'].append(material.U)
                    V_data[f'{node_name}_{tag}_V'].append(material.V)
                    T_data[f'{node_name}_{tag}_T'].append(material.T)
                    if hasattr(material, 'P'):
                        P_data[f'{node_name}_{tag}_P'].append(material.P)

        # Plot results
        if (i+1) % 10 == 0:
            fig_m, _ = plot_dict(m_data, title="Mass (m)", fig=fig_m)
            fig_U, _ = plot_dict(U_data, title="Energy (U)", fig=fig_U)
            fig_V, _ = plot_dict(V_data, title="Volume (V)", fig=fig_V)
            fig_T, _ = plot_dict(T_data, title="Temperature (T)", fig=fig_T)
            fig_P, _ = plot_dict(P_data, title="Pressure (P)", fig=fig_P)


    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

