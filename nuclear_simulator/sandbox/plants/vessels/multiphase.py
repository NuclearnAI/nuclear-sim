
# Import libraries
from scipy.optimize import root_scalar
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.physics import calc_pressure_ideal_gas, calc_temperature_from_energy
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.liquids import Liquid


class GasLiquidVessel(Node):
    """
    A node representing a fixed volume vessel containing a gas-liquid mixture.
    Attributes:
        V:      [m^3]   Baseline volume for pressure calculation
        P:      [Pa]    Baseline pressure for pressure calculation
        gas:    [-]     Gas stored in the vessel
        liquid: [-]     Liquid stored in the vessel
    """
    V: float | None = None
    P: float
    gas: Gas
    liquid: Liquid

    def __init__(self, **data) -> None:
        """Initialize gas-liquid vessel node."""
        # Call super init
        super().__init__(**data)
        # Set volume if not provided
        if self.V is None:
            self.V = self.gas.V + self.liquid.V
        # Validate
        try:
            self.gas.validate()
            self.liquid.validate()
        except Exception as e:
            raise ValueError("Gas-liquid vessel validation failed during initialization.") from e
        # Done
        return

    def update_from_state(self, dt: float) -> None:
        """
        Advance the gas-liquid vessel by dt.
        """

        # Get materials
        liq = self.liquid
        gas = self.gas

        # Get boiling variables
        T_boil = liq.T0
        u_liq_boil = liq.u_saturation(T_boil)
        u_gas_boil = gas.u_saturation(T_boil)
        U_boil = liq.m * u_liq_boil

        # Check for excess internal energy for boiling
        E_excess = liq.U - U_boil
        if E_excess > 0.0:

            # Internal-energy jump between phases at T_boil
            du = u_gas_boil - u_liq_boil  # J/kg

            # Mass that can boil from this excess internal energy
            m_boil = E_excess / du
            m_boil = min(m_boil, liq.m)

            # Transfer mass and internal energy from liquid -> gas
            liq.m -= m_boil
            gas.m += m_boil
            liq.U -= m_boil * du
            gas.U += m_boil * du

        # Calculate volumes
        V_liq = liq.m / liq.rho
        V_gas = self.V - V_liq

        # Calculate temperature of gas
        T_gas = calc_temperature_from_energy(
            U=gas.U,
            m=gas.m,
            cv=gas.cv,
            T0=gas.T0,
            u0=gas.u0,
        )

        # Calculate pressure from ideal gas law
        n_gas = gas.m / gas.MOLECULAR_WEIGHT
        P = calc_pressure_ideal_gas(
            n=n_gas,
            T=T_gas,
            V=V_gas,
        )

        # Update state
        self.P = P
        self.gas = gas
        self.liquid = liq

        return


# # Define gas-liquid vessel node
# class BoilingVessel(Node):
#     """
#     A node representing a fixed volume vessel containing a boiling gas-liquid mixture.
#     Attributes:
#         V:      [m^3]   Baseline volume for pressure calculation
#         P:      [Pa]    Baseline pressure for pressure calculation
#         gas:    [-]     Gas stored in the vessel
#         liquid: [-]     Liquid stored in the vessel
#     """
#     V: float | None = None
#     P: float
#     gas: Gas
#     liquid: Liquid

#     def __init__(self, **data) -> None:
#         """Initialize gas-liquid vessel node."""
#         # Call super init
#         super().__init__(**data)
#         # Set volume if not provided
#         if self.V is None:
#             self.V = self.gas.V + self.liquid.V
#         # Validate
#         try:
#             self.gas.validate()
#             self.liquid.validate()
#         except Exception as e:
#             raise ValueError("Gas-liquid vessel validation failed during initialization.") from e
#         # Done
#         return
    
#     def update_from_state(self, dt: float, eps=1e-9) -> None:
#         """
#         Advance the gas-liquid vessel by dt seconds.
#         Converts any excess internal energy into phase change between liquid and gas.
#         Uses a root-finding approach to find equilibrium state.
#         Isochoric-isoenergetic two-phase equilibrium (UV flash) using a 1-D root solve.

#         Args:
#             dt:  Time step size (s).
#             eps: Small number to avoid division by zero.

#         Modifies:
#             Updates the gas and liquid internal energies and masses.
#         """

#         # Get state
#         gas   = self.gas
#         liq   = self.liquid
#         V_tot = self.V
#         M_tot = self.liquid.m + self.gas.m
#         U_tot = self.liquid.U + self.gas.U

#         # Define residual to minimize: R(T) = U_calc(T) - U_tot
#         def residual(T: float) -> float:
#             _u_liq = self.liquid.u_saturation(T)
#             _v_liq = self.liquid.v_saturation(T)
#             _u_gas = self.gas.u_saturation(T)
#             _v_gas = self.gas.v_saturation(T)
#             _m_gas = (V_tot - M_tot * _v_liq) / max(_v_gas - _v_liq, eps)
#             _m_liq = M_tot - _m_gas
#             U_calc = _m_liq * _u_liq + _m_gas * _u_gas
#             return U_calc - U_tot

#         # Solve for temperature, T*
#         T_lo = min(self.liquid.T, self.gas.T) * .9
#         T_hi = max(self.liquid.T, self.gas.T) * 1.1
#         sol = root_scalar(residual, bracket=[T_lo, T_hi], method='brentq')
#         T_star = sol.root

#         # Get specific properties at T*
#         u_liq = self.liquid.u_saturation(T_star)
#         v_liq = self.liquid.v_saturation(T_star)
#         u_gas = self.gas.u_saturation(T_star)
#         v_gas = self.gas.v_saturation(T_star)

#         # Recalculate m, U, V
#         m_gas = (V_tot - M_tot * v_liq) / max(v_gas - v_liq, eps)
#         m_liq = M_tot - m_gas
#         U_gas = m_gas * u_gas
#         U_liq = m_liq * u_liq
#         V_gas = m_gas * v_gas
#         V_liq = m_liq * v_liq

#         # Check energy conservation
#         U_star = U_gas + U_liq
#         if not (abs(U_star - U_tot) < 1e-3):
#             raise RuntimeError("Energy not conserved in phase equilibrium calculation.")
#         U_liq = U_tot - U_gas  # Adjust to ensure exact conservation

#         # Recreate materials and validate
#         gas = self.gas.__class__(m=m_gas, U=U_gas, V=V_gas)
#         liq = self.liquid.__class__(m=m_liq, U=U_liq, V=V_liq)
#         try:
#             gas.validate()
#             liq.validate()
#         except Exception as e:
#             raise ValueError("Phase equilibrium resulted in invalid state.") from e

#         # Update pressure from saturation at T*
#         P_star = gas.P_saturation(T_star)

#         # Update state
#         self.P = P_star
#         self.gas = gas
#         self.liquid = liq

#         # Done
#         return


# Test
def test_file():
    """
    Smoke test for integrated Plant construction and simulation.
    """

    # Import libraries
    import matplotlib.pyplot as plt
    from pydantic import Field
    from nuclear_simulator.sandbox.graphs import Graph
    from nuclear_simulator.sandbox.plants.dashboard import Dashboard
    from nuclear_simulator.sandbox.plants.materials import PWRSecondarySteam, PWRSecondaryWater
    from nuclear_simulator.sandbox.plants.pipes.pipes import LiquidPipe, GasPipe
    from nuclear_simulator.sandbox.plants.vessels.environment import Reservoir


    # --- Define test classes ---

    # Constants
    P_DRUM = PWRSecondarySteam.P0  # ~7 MPa saturation
    T_DRUM = PWRSecondarySteam.T0  # ~559 K saturation

    # Test gas-liquid vessel
    class TestGasLiquidVessel(GasLiquidVessel):
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

    # Water source
    class TestWaterRes(Reservoir):
        """Reservoir for secondary feedwater."""
        P: float = P_DRUM
        T: float = T_DRUM
        material_type: type = PWRSecondaryWater

    # Steam sink
    class TestSteamRes(Reservoir):
        """Reservoir for secondary steam to environment."""
        P: float = P_DRUM
        T: float = T_DRUM
        material_type: type = PWRSecondarySteam

    # Make vessel connected to reservoirs graph
    class TestGraph(Graph):
        def __init__(self, **data) -> None:
            super().__init__(**data)
            self.drum = self.add_node(node_type=TestGasLiquidVessel, name="Test:Drum")
            self.srce = self.add_node(node_type=TestWaterRes, name="Env:WaterRes")
            self.sink = self.add_node(node_type=TestSteamRes, name="Env:SteamRes")
            self.add_edge(
                edge_type=LiquidPipe,
                node_source=self.srce,
                node_target=self.drum,
                name="FeedwaterPipe",
                monodirectional=True,
                m_dot=10.0,
            )
            self.add_edge(
                edge_type=GasPipe,
                node_source=self.drum,
                node_target=self.sink,
                name="SteamPipe",
                m_dot=10.0,
            ) 


    # --- Main test ---

    # Initialize graph
    graph = TestGraph()

    # Initialize dashboard
    dashboard = Dashboard(graph, plot_every=10)

    # Simulate for a while
    dt = .001
    n_steps = 10000
    for i in range(n_steps):
        graph.update(dt)
        dashboard.step()

    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

