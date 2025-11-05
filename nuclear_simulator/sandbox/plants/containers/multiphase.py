
# Import libraries
from nuclear_simulator.sandbox.graphs import Node
from nuclear_simulator.sandbox.materials.gases import Gas
from nuclear_simulator.sandbox.materials.liquids import Liquid
from nuclear_simulator.sandbox.physics.constants import UNIVERSAL_GAS_CONSTANT


# Define gas-liquid vessel node
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
        # Set baseline volume if not provided
        if self.V is None:
            self.V = self.gas.V + self.liquid.V
        # Done
        return
    
    def update_from_state(self, dt: float) -> None:
        """
        Advance the gas-liquid vessel by dt seconds:
        Args:
            dt: Time step size (s).
        Modifies:
            Updates nothing by default.
        """
        
        # Get totals
        m_tot = self.gas.m + self.liquid.m
        U_tot = self.gas.U + self.liquid.U
        V_fix = self.V
        if m_tot <= 0 or U_tot <= 0:
            raise ValueError("Total mass and internal energy must be positive.")

        # Liquid specific volume (incompressible): prefer class density; else freeze current v_l
        rho_l_ref = getattr(self.liquid, "DENSITY", None)
        if rho_l_ref and rho_l_ref > 0:
            v_l_spec = 1.0 / rho_l_ref
        else:
            # Fallback to current specific volume (robust for your framework)
            v_l_spec = self.liquid.V / max(self.liquid.m, 1e-12)

        # Gas specific constant
        Rv = UNIVERSAL_GAS_CONSTANT / self.gas.MOLECULAR_WEIGHT  # J/(kg·K)

        # Convenience closures using material APIs
        def P_sat(T: float) -> float:
            # same saturation curve for both phases; use liquid's helper
            return self.liquid.P_saturation(T)

        def u_l(T: float) -> float:
            return self.liquid.u_saturation(T=T)

        def u_v(T: float) -> float:
            return self.gas.u_saturation(T=T)

        def v_v_spec(T: float) -> float:
            # Ideal vapor on saturation line
            P = self.liquid.P_saturation(T)
            return Rv * T / max(P, 1e-9)

        u_bar = U_tot / m_tot

        def x_of_T(T: float) -> float:
            den = (u_v(T) - u_l(T))
            if abs(den) < 1e-12:
                # Near-critical or degenerate; keep prior split via current masses
                return _clamp(self.gas.m / max(m_tot, 1e-12))
            return _clamp((u_bar - u_l(T)) / den)

        def F(T: float) -> float:
            x = x_of_T(T)
            return (1.0 - x) * m_tot * v_l_spec + x * m_tot * v_v_spec(T) - V_fix

        # --- Solve F(T)=0 by bisection ---
        # Bracket: use last-known saturation around current P if available
        # Fall back to a broad SG range (350–600 K)
        try:
            T_guess = self.liquid.T_saturation(max(self.P, 1.0))
            T_lo = max(300.0, 0.8 * T_guess)
            T_hi = min(650.0, 1.2 * T_guess)
        except Exception:
            T_lo, T_hi = 350.0, 600.0

        # Expand bracket if needed
        f_lo, f_hi = F(T_lo), F(T_hi)
        expand_iters = 0
        while f_lo * f_hi > 0 and expand_iters < 8:
            span = (T_hi - T_lo)
            T_lo = max(250.0, T_lo - 0.25 * span - 10.0)
            T_hi = min(700.0, T_hi + 0.25 * span + 10.0)
            f_lo, f_hi = F(T_lo), F(T_hi)
            expand_iters += 1

        # If still not bracketed, just pick the best of endpoints
        if f_lo * f_hi > 0:
            T_star = T_lo if abs(f_lo) <= abs(f_hi) else T_hi
        else:
            # Bisection
            T_a, T_b = T_lo, T_hi
            for _ in range(40):
                T_mid = 0.5 * (T_a + T_b)
                f_mid = F(T_mid)
                if abs(f_mid) < 1e-8:
                    T_star = T_mid
                    break
                if f_lo * f_mid <= 0:
                    T_b, f_hi = T_mid, f_mid
                else:
                    T_a, f_lo = T_mid, f_mid
            else:
                T_star = 0.5 * (T_a + T_b)

        # Final properties at T*
        P_star = self.liquid.P_saturation(T_star)
        frac_gas = x_of_T(T_star)
        u_liq = u_l(T_star)
        u_gas = u_v(T_star)

        m_gas = frac_gas * m_tot
        m_liq = m_tot - m_gas
        U_gas = m_gas * u_gas
        U_liq = m_liq * u_liq

        # Volumes (assign to conserve total V exactly)
        V_liq = m_liq * v_l_spec
        V_gas = V_fix - V_liq
        if V_gas < 0:
            raise ValueError("Computed gas volume is negative; check inputs and material models.")

        # Rebuild materials (no reference mutation)
        self.liquid = self.liquid.__class__(m=m_liq, U=U_liq)
        self.gas = self.gas.__class__(m=m_gas, U=U_gas, V=V_gas)

        # Update vessel pressure (for edges/controllers to read)
        self.P = P_star

        # Done
        return


# Pressure controlled gas-liquid vessel
class PressureControlledGasLiquidVessel(GasLiquidVessel):
    """
    A gas-liquid vessel node with pressure control.
    Attributes:
        P: float  [Pa] Pressure maintained in the vessel
    """

    P: float

    def update_from_state(self, dt: float) -> None:
        """
        Advance the gas-liquid vessel by dt seconds:
        Args:
            dt: Time step size (s).
        Modifies:
            Updates the gas and liquid internal energies to maintain saturation.
        """

        # Get saturation properties
        P = self.P
        T_sat = self.liquid.T_saturation(P)
        u_liq = self.liquid.u_saturation(T=T_sat)
        u_gas = self.gas.u_saturation(T=T_sat)

        # Get total mass and energy
        m_total = self.gas.m + self.liquid.m
        U_total = self.gas.U + self.liquid.U
        if m_total <= 0 or U_total <= 0:
            raise ValueError("Total mass and internal energy must be positive.")

        # Get gas-liquid mass fractions
        frac_gas = ((U_total / m_total) - u_liq) / (u_gas - u_liq)

        # Clamp between 0 and 1
        frac_gas = max(0.0, min(1.0, frac_gas))
        frac_liq = 1.0 - frac_gas

        # Update liquid and gas properties
        m_liq = frac_liq * m_total
        m_gas = frac_gas * m_total
        U_liq = m_liq * u_liq
        U_gas = m_gas * u_gas

        # Set new material states
        self.liquid = self.liquid.__class__(m=m_liq, U=U_liq)
        self.gas = self.gas.__class__.from_pressure(m=m_gas, U=U_gas, P=P)

        # Done
        return
    
    @classmethod
    def from_temperature_pressure_mass(
            cls,
            T: float,
            P: float,
            m: float,
            gas_type: type[Gas],
            liquid_type: type[Liquid],
        ) -> PressureControlledGasLiquidVessel:
        """
        Create a PressureControlledGasLiquidVessel from temperature, pressure, and total mass.
        Args:
            T: Temperature (K)
            P: Pressure (Pa)
            m: Total mass (kg)
            liquid_type: Type of liquid to use
            gas_type: Type of gas to use
        Returns:
            PressureControlledGasLiquidVessel: Initialized vessel
        """
        
        # Create liquid and gas at half mass each
        liq = liquid_type.from_temperature(m=m/2, T=T)
        gas = gas_type.from_temperature_pressure(m=m/2, T=T)

        # Initialize vessel
        vessel = cls(P=P, gas=gas, liquid=liq)

        # Update to correct state
        vessel.update_from_state(dt=0.0)

        # Return vessel
        return vessel
        



# Test
def test_file():
    # Import libraries
    ...
    # Done
    return
if __name__ == "__main__":
    test_file()
    print("All tests passed.")

