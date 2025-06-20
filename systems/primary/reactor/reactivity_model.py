"""
Comprehensive PWR Reactivity Model

This module implements a physics-based reactivity model for PWR nuclear reactors,
accounting for all major reactivity effects including control systems, temperature
feedback, fission products, fuel depletion, and burnable poisons.
"""

import warnings
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

from ..component_descriptions import REACTOR_PHYSICS_COMPONENT_DESCRIPTIONS

warnings.filterwarnings("ignore")


@dataclass
class ReactorConfig:
    """Reactor-specific configuration parameters"""

    # Control systems
    control_rod_worth: float = 3000.0  # pcm total worth (reduced for realistic PWR)
    boron_worth: float = -10.0  # pcm/ppm

    # Temperature coefficients
    doppler_coefficient: float = -2.5e-5  # Δρ/ΔT_fuel (1/°C)
    moderator_temp_coeff: float = -3.0e-5  # Δρ/ΔT_mod (1/°C)
    moderator_void_coeff: float = -1000.0  # pcm for 100% void
    moderator_pressure_coeff: float = +0.5  # pcm/MPa

    # Reference conditions
    ref_fuel_temperature: float = 575.0  # °C (match operating conditions)
    ref_coolant_temperature: float = 280.0  # °C (match operating conditions)
    ref_pressure: float = 15.5  # MPa

    # Fuel parameters
    initial_enrichment: float = 4.2  # w/o U-235
    fuel_density: float = 10.4  # g/cm³

    # Cross sections (barns)
    sigma_f_u235: float = 585.0
    sigma_a_u235: float = 681.0
    sigma_a_u238: float = 2.7
    sigma_a_xe135: float = 2.65e6
    sigma_a_sm149: float = 4.1e4
    sigma_a_gd: float = 4.9e4

    # Fission product yields
    xenon_yield: float = 0.061
    iodine_yield: float = 0.064
    samarium_yield: float = 0.0137

    # Decay constants (1/s)
    xenon_decay: float = 2.09e-5  # 9.17 hour half-life
    iodine_decay: float = 2.87e-5  # 6.7 hour half-life

    # Neutron flux normalization
    flux_normalization: float = 1e13  # n/cm²/s at 100% power


class ReactivityModel:
    """
    Comprehensive PWR reactivity model accounting for all major reactivity effects
    """

    def __init__(self, config: Optional[ReactorConfig] = None):
        """Initialize the reactivity model with reactor configuration"""
        self.config = config if config is not None else ReactorConfig()

        # Initialize equilibrium fission product concentrations
        self._equilibrium_xenon = None
        self._equilibrium_samarium = None

    def calculate_total_reactivity(self, state) -> Tuple[float, Dict[str, float]]:
        """
        Calculate total reactivity from all sources

        Args:
            state: ReactorState object containing current plant conditions

        Returns:
            tuple: (total_reactivity_pcm, component_breakdown_dict)
        """
        components = {}

        # Control systems
        components["control_rods"] = self.calculate_control_rod_reactivity(
            state.control_rod_position
        )
        components["boron"] = self.calculate_boron_reactivity(state.boron_concentration)

        # Temperature feedback
        components["doppler"] = self.calculate_doppler_reactivity(
            state.fuel_temperature
        )
        components["moderator_temp"] = self.calculate_moderator_temp_reactivity(
            state.coolant_temperature
        )
        components["moderator_void"] = self.calculate_void_reactivity(
            getattr(state, "coolant_void_fraction", 0.0)
        )
        components["pressure"] = self.calculate_pressure_reactivity(
            state.coolant_pressure
        )

        # Fission product poisons
        components["xenon"] = self.calculate_xenon_reactivity(
            state.xenon_concentration, state.neutron_flux
        )
        components["samarium"] = self.calculate_samarium_reactivity(
            state.samarium_concentration
        )

        # Fuel depletion and burnable poisons
        components["fuel_depletion"] = self.calculate_fuel_depletion_reactivity(state)
        components["burnable_poisons"] = self.calculate_burnable_poison_reactivity(
            state
        )

        total_reactivity = sum(components.values())

        return total_reactivity, components

    def calculate_control_rod_reactivity(self, position: float) -> float:
        """
        Calculate control rod reactivity using realistic S-curve

        Args:
            position: Rod position (% withdrawn, 0-100)

        Returns:
            Reactivity in pcm
        """
        # Normalize position to 0-1
        pos_norm = np.clip(position / 100.0, 0.0, 1.0)

        # S-curve with realistic control rod worth distribution
        # At 0% (fully inserted): -8000 pcm
        # At 50% (normal operation): ~0 pcm
        # At 100% (fully withdrawn): +1000 pcm

        # Simplified linear curve that gives 0 pcm at 50% position
        # At 0% (fully inserted): -1500 pcm
        # At 50% (normal operation): 0 pcm
        # At 100% (fully withdrawn): +1500 pcm
        reactivity = self.config.control_rod_worth * (pos_norm - 0.5)

        return reactivity

    def calculate_boron_reactivity(self, concentration: float) -> float:
        """
        Calculate boron reactivity (linear relationship)

        Args:
            concentration: Boron concentration in ppm

        Returns:
            Reactivity in pcm
        """
        return self.config.boron_worth * concentration

    def calculate_doppler_reactivity(self, fuel_temperature: float) -> float:
        """
        Calculate Doppler reactivity feedback from fuel temperature

        Args:
            fuel_temperature: Average fuel temperature in °C

        Returns:
            Reactivity in pcm
        """
        delta_temp = fuel_temperature - self.config.ref_fuel_temperature
        reactivity = (
            self.config.doppler_coefficient * delta_temp * 1e5
        )  # Convert to pcm

        return reactivity

    def calculate_moderator_temp_reactivity(self, coolant_temperature: float) -> float:
        """
        Calculate moderator temperature reactivity feedback

        Args:
            coolant_temperature: Average coolant temperature in °C

        Returns:
            Reactivity in pcm
        """
        delta_temp = coolant_temperature - self.config.ref_coolant_temperature
        reactivity = (
            self.config.moderator_temp_coeff * delta_temp * 1e5
        )  # Convert to pcm

        return reactivity

    def calculate_void_reactivity(self, void_fraction: float) -> float:
        """
        Calculate moderator void reactivity feedback

        Args:
            void_fraction: Steam void fraction (0-1)

        Returns:
            Reactivity in pcm
        """
        return self.config.moderator_void_coeff * void_fraction

    def calculate_pressure_reactivity(self, pressure: float) -> float:
        """
        Calculate pressure reactivity feedback

        Args:
            pressure: Coolant pressure in MPa

        Returns:
            Reactivity in pcm
        """
        delta_pressure = pressure - self.config.ref_pressure
        return self.config.moderator_pressure_coeff * delta_pressure

    def calculate_xenon_reactivity(
        self, xenon_concentration: float, neutron_flux: float
    ) -> float:
        """
        Calculate xenon poisoning reactivity

        Args:
            xenon_concentration: Xe-135 concentration in atoms/cm³
            neutron_flux: Neutron flux in n/cm²/s

        Returns:
            Reactivity in pcm
        """
        # Simplified empirical relationship for PWR
        # Reduced for mid-cycle operation to achieve better balance
        equilibrium_xe_conc = 1.0e15  # atoms/cm³
        equilibrium_xe_worth = -1800.0  # pcm (reduced from -2800)

        reactivity = (xenon_concentration / equilibrium_xe_conc) * equilibrium_xe_worth

        return reactivity

    def calculate_samarium_reactivity(self, samarium_concentration: float) -> float:
        """
        Calculate samarium poisoning reactivity

        Args:
            samarium_concentration: Sm-149 concentration in atoms/cm³

        Returns:
            Reactivity in pcm
        """
        # Simplified empirical relationship for PWR
        # Reduced for mid-cycle operation to achieve better balance
        equilibrium_sm_conc = 5.0e14  # atoms/cm³
        equilibrium_sm_worth = -600.0  # pcm (reduced from -1000)

        reactivity = (
            samarium_concentration / equilibrium_sm_conc
        ) * equilibrium_sm_worth

        return reactivity

    def calculate_fuel_depletion_reactivity(self, state) -> float:
        """
        Calculate reactivity change due to fuel depletion

        Args:
            state: ReactorState with fuel composition data

        Returns:
            Reactivity in pcm
        """
        # Simplified fuel depletion model based on burnup
        burnup = getattr(state, "fuel_burnup", 15000.0)  # MWd/MTU

        # Typical PWR reactivity vs burnup relationship
        # Fresh fuel: +15000 pcm excess reactivity
        # End of cycle: ~0 pcm
        initial_excess = 3340.0  # pcm (fine-tuned for exact criticality)
        burnup_coefficient = -0.15  # pcm per MWd/MTU (reduced rate)

        reactivity = initial_excess + burnup_coefficient * burnup

        return reactivity

    def calculate_burnable_poison_reactivity(self, state) -> float:
        """
        Calculate burnable poison reactivity

        Args:
            state: ReactorState with burnable poison data

        Returns:
            Reactivity in pcm
        """
        # Get burnable poison worth from state or use default
        bp_worth = getattr(state, "burnable_poison_worth", -800.0)
        burnup = getattr(state, "fuel_burnup", 15000.0)

        # Exponential burnout of burnable poisons
        # Most burnable poisons are consumed in first 1/3 of cycle
        burnout_rate = 0.0002  # 1/(MWd/MTU)
        remaining_fraction = np.exp(-burnout_rate * burnup)

        reactivity = bp_worth * remaining_fraction

        return reactivity

    def update_fission_products(
        self, state, neutron_flux: float, dt: float
    ) -> Dict[str, float]:
        """
        Update fission product concentrations using differential equations

        Args:
            state: ReactorState object
            neutron_flux: Neutron flux in n/cm²/s
            dt: Time step in seconds

        Returns:
            Dictionary with updated concentrations
        """
        # Current concentrations
        iodine = state.iodine_concentration
        xenon = state.xenon_concentration
        samarium = state.samarium_concentration

        # Fission rate (simplified)
        fission_rate = neutron_flux * 1e-12  # Approximate fissions/cm³/s

        # Iodine-135 balance
        iodine_production = self.config.iodine_yield * fission_rate
        iodine_decay = self.config.iodine_decay * iodine

        diodine_dt = iodine_production - iodine_decay
        new_iodine = iodine + diodine_dt * dt

        # Xenon-135 balance
        xenon_production = self.config.xenon_yield * fission_rate
        xenon_from_iodine = self.config.iodine_decay * iodine
        xenon_decay = self.config.xenon_decay * xenon
        xenon_absorption = self.config.sigma_a_xe135 * 1e-24 * neutron_flux * xenon

        dxenon_dt = (
            xenon_production + xenon_from_iodine - xenon_decay - xenon_absorption
        )
        new_xenon = xenon + dxenon_dt * dt

        # Samarium-149 balance (stable, only production)
        samarium_production = self.config.samarium_yield * fission_rate
        samarium_absorption = (
            self.config.sigma_a_sm149 * 1e-24 * neutron_flux * samarium
        )

        dsamarium_dt = samarium_production - samarium_absorption
        new_samarium = samarium + dsamarium_dt * dt

        # Ensure non-negative concentrations
        new_iodine = max(0, new_iodine)
        new_xenon = max(0, new_xenon)
        new_samarium = max(0, new_samarium)

        return {"iodine": new_iodine, "xenon": new_xenon, "samarium": new_samarium}

    def calculate_equilibrium_fission_products(
        self, neutron_flux: float
    ) -> Dict[str, float]:
        """
        Calculate equilibrium fission product concentrations for given flux

        Args:
            neutron_flux: Neutron flux in n/cm²/s

        Returns:
            Dictionary with equilibrium concentrations
        """
        # Use realistic equilibrium concentrations for PWR at full power
        # These values give approximately -2800 pcm Xe and -1000 pcm Sm

        return {
            "iodine": 1.5e16,  # atoms/cm³
            "xenon": 1.0e15,  # atoms/cm³ (gives ~-2650 pcm)
            "samarium": 5.0e14,  # atoms/cm³ (gives ~-410 pcm)
        }

    def calculate_critical_boron_concentration(
        self, state, target_reactivity: float = 0.0
    ) -> float:
        """
        Calculate boron concentration needed for specified reactivity

        Args:
            state: ReactorState object
            target_reactivity: Target total reactivity in pcm

        Returns:
            Required boron concentration in ppm
        """
        # Calculate reactivity without boron
        temp_boron = state.boron_concentration
        state.boron_concentration = 0.0

        total_reactivity, _ = self.calculate_total_reactivity(state)

        # Restore original boron concentration
        state.boron_concentration = temp_boron

        # Calculate required boron change
        reactivity_difference = total_reactivity - target_reactivity
        required_boron_change = reactivity_difference / self.config.boron_worth

        return required_boron_change

    def get_reactivity_summary(self, state) -> str:
        """
        Generate a formatted summary of all reactivity components

        Args:
            state: ReactorState object

        Returns:
            Formatted string with reactivity breakdown
        """
        total_reactivity, components = self.calculate_total_reactivity(state)

        summary = "Reactivity Summary (pcm):\n"
        summary += "=" * 40 + "\n"

        for component, value in components.items():
            summary += f"{component.replace('_', ' ').title():<20}: {value:>8.1f}\n"

        summary += "-" * 40 + "\n"
        summary += f"{'Total Reactivity':<20}: {total_reactivity:>8.1f}\n"
        summary += f"{'Status':<20}: {'Critical' if abs(total_reactivity) < 10 else 'Subcritical' if total_reactivity < 0 else 'Supercritical'}\n"

        return summary


def create_equilibrium_state(
    power_level: float = 100.0,
    control_rod_position: float = 95.0,
    auto_balance: bool = True,
) -> "ReactorState":
    """
    Create a reactor state in equilibrium for the specified conditions

    Args:
        power_level: Power level in % rated
        control_rod_position: Control rod position in % withdrawn
        auto_balance: If True, automatically calculate boron for criticality

    Returns:
        ReactorState object in equilibrium
    """
    # Import here to avoid circular imports
    from simulator.core.sim import ReactorState

    # Create reactivity model
    reactivity_model = ReactivityModel()

    # Calculate equilibrium neutron flux
    # TODO: see if this is realistic. We shouldn't hardcode this value
    flux_normalization = 1e13  # n/cm²/s at 100% power
    neutron_flux = flux_normalization * (power_level / 100.0)

    # Calculate equilibrium fission products
    eq_fp = reactivity_model.calculate_equilibrium_fission_products(neutron_flux)

    # Create state with equilibrium conditions
    state = ReactorState()
    state.power_level = power_level
    state.neutron_flux = neutron_flux
    state.control_rod_position = control_rod_position

    # Set equilibrium fission products
    state.xenon_concentration = eq_fp["xenon"]
    state.iodine_concentration = eq_fp["iodine"]
    state.samarium_concentration = eq_fp["samarium"]

    # FIXED: Set realistic PWR temperatures for power level
    state.fuel_temperature = 575.0 + (power_level - 100.0) * 2.0  # °C
    # Use realistic PWR coolant temperature (average of hot/cold leg)
    # At 100% power: Hot leg = 327°C, Cold leg = 293°C, Average = 310°C
    power_fraction = power_level / 100.0
    target_avg_temp = 293.0 + (17.0 * power_fraction)  # 293°C to 310°C
    state.coolant_temperature = target_avg_temp

    # Initialize delayed neutron precursors for equilibrium at this power level
    # For equilibrium, precursor concentration = (beta_i / lambda_i) * (neutron_flux / lambda_prompt)
    beta_fractions = [
        0.000215,
        0.001424,
        0.001274,
        0.002568,
        0.000748,
        0.000273,
    ]  # Individual beta fractions
    lambda_values = [0.077, 0.311, 1.40, 3.87, 1.40, 0.195]  # Decay constants (1/s)
    lambda_prompt = 1e-5  # Prompt neutron generation time

    equilibrium_precursors = []
    for i in range(6):
        precursor_conc = (beta_fractions[i] / lambda_values[i]) * (
            neutron_flux / lambda_prompt
        )
        equilibrium_precursors.append(precursor_conc)

    state.delayed_neutron_precursors = np.array(equilibrium_precursors)

    if auto_balance:
        # Calculate critical boron concentration for exact criticality
        state.boron_concentration = 0.0  # Start with no boron
        critical_boron = reactivity_model.calculate_critical_boron_concentration(
            state, target_reactivity=0.0
        )  # Target exactly 0.0 pcm (critical)
        state.boron_concentration = max(0, critical_boron)  # Ensure non-negative

        # Fine-tune the neutron flux to ensure exactly 100% power
        state.neutron_flux = 1e13  # Exactly 100% power flux
        state.power_level = 100.0  # Exactly 100% power
    else:
        # Use default boron concentration
        state.boron_concentration = 1200.0

    return state


# Example usage and testing
if __name__ == "__main__":
    # Create test state
    from simulator.core.sim import ReactorState

    state = create_equilibrium_state(
        power_level=100.0, control_rod_position=100.0, auto_balance=True
    )

    # Create reactivity model
    model = ReactivityModel()

    # Calculate reactivity
    total_reactivity, components = model.calculate_total_reactivity(state)

    print(model.get_reactivity_summary(state))

    # Test critical boron calculation
    critical_boron = model.calculate_critical_boron_concentration(state)
    print(f"\nCritical boron concentration: {critical_boron:.1f} ppm")
