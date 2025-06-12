"""
Steam Jet Ejector Vacuum System Model

This module implements steam jet ejector models for PWR condenser vacuum systems.
Steam jet ejectors use high-pressure motive steam to entrain and compress air/vapor
mixtures from the condenser.

Parameter Sources:
- Steam Jet Ejector Design Manual (Schutte & Koerting)
- Power Plant Engineering (Black & Veatch)
- EPRI Condenser Performance Guidelines
- Typical PWR steam ejector specifications

Physical Basis:
- Momentum transfer from high-velocity steam jets
- Venturi effect for suction creation
- Multi-stage compression with inter/after condensers
- Steam consumption vs capacity relationships
"""

import warnings
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import numpy as np

warnings.filterwarnings("ignore")


@dataclass
class SteamEjectorConfig:
    """
    Configuration parameters for steam jet ejectors
    
    References:
    - Schutte & Koerting ejector design data
    - Graham Manufacturing ejector specifications
    - Typical PWR vacuum system designs
    """
    
    # Basic ejector parameters
    ejector_id: str = "SJE-001"            # Unique ejector identifier
    ejector_type: str = "two_stage"        # "single_stage", "two_stage", "three_stage"
    design_capacity: float = 25.0          # kg/s air at design conditions
    design_suction_pressure: float = 0.007 # MPa design suction pressure
    design_compression_ratio: float = 14.3 # Discharge/suction pressure ratio
    
    # Motive steam parameters
    motive_steam_pressure: float = 1.0     # MPa motive steam pressure
    motive_steam_temperature: float = 180.0 # °C motive steam temperature
    design_steam_consumption: float = 2.5   # kg steam / kg air removed
    
    # Performance characteristics
    # Steam consumption = base_consumption * (capacity_factor^steam_exponent) * pressure_factor
    base_steam_consumption: float = 2.5     # kg steam / kg air at design
    steam_consumption_exponent: float = 0.8 # Exponent for capacity scaling
    pressure_effect_coefficient: float = 1.5 # Effect of suction pressure on steam consumption
    
    # Operating limits
    min_suction_pressure: float = 0.003    # MPa minimum operating pressure
    max_suction_pressure: float = 0.015    # MPa maximum operating pressure
    min_motive_pressure: float = 0.8       # MPa minimum motive steam pressure
    max_capacity_factor: float = 1.2       # Maximum capacity vs design
    
    # Inter-stage condenser (for multi-stage ejectors)
    has_intercondenser: bool = True        # Inter-stage condenser present
    intercondenser_pressure: float = 0.02  # MPa inter-stage pressure
    intercondenser_cooling_water: float = 50.0 # kg/s cooling water flow
    
    # After-condenser
    has_aftercondenser: bool = True        # After-condenser present
    aftercondenser_cooling_water: float = 25.0 # kg/s cooling water flow
    
    # Degradation and fouling
    nozzle_fouling_rate: float = 0.00001   # Fouling rate per hour
    diffuser_fouling_rate: float = 0.00002 # Diffuser fouling rate per hour
    erosion_rate: float = 0.000001         # Nozzle erosion rate per hour


class SteamJetEjector:
    """
    Steam jet ejector physics model for vacuum service
    
    This model implements:
    1. Steam jet momentum transfer physics
    2. Multi-stage compression with inter-condensers
    3. Steam consumption vs capacity relationships
    4. Fouling and erosion effects
    5. Performance degradation over time
    6. Motive steam condition effects
    
    Physical Models Used:
    - Momentum theory: Conservation of momentum in mixing chamber
    - Venturi effect: Pressure reduction in converging nozzle
    - Steam properties: Real steam properties for motive steam
    - Heat transfer: Inter-condenser and after-condenser performance
    """
    
    def __init__(self, config: SteamEjectorConfig):
        """Initialize steam jet ejector model"""
        self.config = config
        
        # Operating state
        self.is_operating = False
        self.motive_steam_available = True     # Motive steam supply available
        self.operating_hours = 0.0             # Total operating time
        
        # Performance state
        self.current_capacity = 0.0            # kg/s actual air removal
        self.suction_pressure = 0.007          # MPa current suction pressure
        self.discharge_pressure = 0.101        # MPa discharge pressure (atmospheric)
        self.motive_steam_flow = 0.0           # kg/s motive steam consumption
        self.motive_steam_pressure_actual = 1.0 # MPa actual motive steam pressure
        self.motive_steam_temp_actual = 180.0  # °C actual motive steam temperature
        
        # Multi-stage performance (for two-stage ejector)
        if config.ejector_type == "two_stage":
            self.first_stage_capacity = 0.0    # kg/s first stage capacity
            self.second_stage_capacity = 0.0   # kg/s second stage capacity
            self.intercondenser_pressure = config.intercondenser_pressure
            self.intercondenser_load = 0.0     # kW heat removal
        
        # Degradation state
        self.nozzle_fouling_factor = 1.0       # Nozzle performance factor (1.0 = clean)
        self.diffuser_fouling_factor = 1.0     # Diffuser performance factor
        self.nozzle_erosion_factor = 1.0       # Nozzle erosion factor
        self.overall_performance_factor = 1.0  # Combined performance factor
        
        # Condenser performance
        self.intercondenser_effectiveness = 0.85 # Inter-condenser effectiveness
        self.aftercondenser_effectiveness = 0.90 # After-condenser effectiveness
        
        # Performance tracking
        self.steam_consumption_rate = 0.0      # kg steam / kg air actual
        self.compression_ratio_actual = 1.0    # Actual compression ratio achieved
        self.entrainment_ratio = 0.0           # kg air / kg motive steam
        
    def calculate_steam_jet_performance(self,
                                      suction_pressure: float,
                                      required_capacity: float,
                                      motive_steam_pressure: float,
                                      motive_steam_temperature: float) -> Tuple[float, Dict[str, float]]:
        """
        Calculate steam jet ejector performance
        
        Physical Basis:
        - Momentum transfer: High-velocity steam jet entrains air
        - Venturi effect: Steam expansion creates suction
        - Compression: Momentum transfer compresses air/steam mixture
        
        Args:
            suction_pressure: Suction pressure (MPa)
            required_capacity: Required air removal capacity (kg/s)
            motive_steam_pressure: Motive steam pressure (MPa)
            motive_steam_temperature: Motive steam temperature (°C)
            
        Returns:
            tuple: (actual_capacity, performance_details)
        """
        # Check operating limits
        if (suction_pressure < self.config.min_suction_pressure or 
            suction_pressure > self.config.max_suction_pressure):
            return 0.0, {'error': 'suction_pressure_out_of_range'}
        
        if motive_steam_pressure < self.config.min_motive_pressure:
            return 0.0, {'error': 'insufficient_motive_pressure'}
        
        # Calculate available capacity based on motive steam conditions
        # Higher motive pressure = higher jet velocity = more entrainment
        pressure_ratio = motive_steam_pressure / self.config.motive_steam_pressure
        pressure_capacity_factor = pressure_ratio ** 0.5  # Square root relationship
        
        # Temperature effect (higher temperature = lower density = higher velocity)
        temp_ratio = (motive_steam_temperature + 273.15) / (self.config.motive_steam_temperature + 273.15)
        temp_capacity_factor = temp_ratio ** 0.25  # Weak temperature dependence
        
        # Suction pressure effect (higher suction pressure = harder to entrain)
        suction_pressure_ratio = suction_pressure / self.config.design_suction_pressure
        suction_capacity_factor = 1.0 / (1.0 + 0.5 * (suction_pressure_ratio - 1.0))
        
        # Available capacity with degradation effects
        available_capacity = (self.config.design_capacity * 
                            pressure_capacity_factor * 
                            temp_capacity_factor * 
                            suction_capacity_factor * 
                            self.overall_performance_factor)
        
        # Actual capacity is minimum of available and required
        actual_capacity = min(available_capacity, required_capacity)
        actual_capacity = max(0.0, actual_capacity)
        
        # Calculate steam consumption
        # Steam consumption increases with capacity and suction pressure
        if actual_capacity > 0:
            capacity_factor = actual_capacity / self.config.design_capacity
            
            # Base steam consumption scaled by capacity
            base_consumption = (self.config.base_steam_consumption * 
                              (capacity_factor ** self.config.steam_consumption_exponent))
            
            # Pressure effect on steam consumption
            pressure_effect = (suction_pressure_ratio ** self.config.pressure_effect_coefficient)
            
            # Degradation increases steam consumption
            degradation_factor = 1.0 / max(0.5, self.overall_performance_factor)
            
            steam_consumption_rate = base_consumption * pressure_effect * degradation_factor
            motive_steam_flow = actual_capacity * steam_consumption_rate
        else:
            steam_consumption_rate = 0.0
            motive_steam_flow = 0.0
        
        # Calculate compression ratio
        compression_ratio = self.discharge_pressure / suction_pressure
        
        # Entrainment ratio (air entrained per unit motive steam)
        entrainment_ratio = actual_capacity / max(0.001, motive_steam_flow)
        
        details = {
            'available_capacity': available_capacity,
            'actual_capacity': actual_capacity,
            'motive_steam_flow': motive_steam_flow,
            'steam_consumption_rate': steam_consumption_rate,
            'compression_ratio': compression_ratio,
            'entrainment_ratio': entrainment_ratio,
            'pressure_capacity_factor': pressure_capacity_factor,
            'temp_capacity_factor': temp_capacity_factor,
            'suction_capacity_factor': suction_capacity_factor,
            'performance_factor': self.overall_performance_factor
        }
        
        return actual_capacity, details
    
    def calculate_multistage_performance(self,
                                       total_capacity: float,
                                       suction_pressure: float) -> Dict[str, float]:
        """
        Calculate multi-stage ejector performance with inter-condensers
        
        Args:
            total_capacity: Total air removal capacity (kg/s)
            suction_pressure: First stage suction pressure (MPa)
            
        Returns:
            Dictionary with multi-stage performance
        """
        if self.config.ejector_type == "single_stage":
            return {
                'first_stage_capacity': total_capacity,
                'intercondenser_load': 0.0,
                'intercondenser_pressure': suction_pressure
            }
        
        # For two-stage ejector
        # First stage: Low pressure to intermediate pressure
        first_stage_suction = suction_pressure
        first_stage_discharge = self.config.intercondenser_pressure
        first_stage_compression = first_stage_discharge / first_stage_suction
        
        # First stage handles all the air plus steam from condensation
        self.first_stage_capacity = total_capacity
        
        # Inter-condenser condenses steam, reducing load on second stage
        # Assume 90% of steam is condensed in inter-condenser
        steam_condensed_fraction = 0.90
        
        # Second stage: Intermediate pressure to atmospheric
        # Only handles remaining steam + air
        second_stage_load_factor = 1.0 - 0.8 * steam_condensed_fraction
        self.second_stage_capacity = total_capacity * second_stage_load_factor
        
        # Inter-condenser heat load (condensing steam)
        # Approximate latent heat at intermediate pressure
        latent_heat = 2200.0  # kJ/kg approximate
        steam_to_condense = total_capacity * 2.0  # Estimate steam flow
        self.intercondenser_load = (steam_to_condense * steam_condensed_fraction * 
                                  latent_heat)  # kW
        
        return {
            'first_stage_capacity': self.first_stage_capacity,
            'second_stage_capacity': self.second_stage_capacity,
            'first_stage_compression': first_stage_compression,
            'intercondenser_load': self.intercondenser_load,
            'intercondenser_pressure': self.intercondenser_pressure,
            'steam_condensed_fraction': steam_condensed_fraction
        }
    
    def update_degradation(self, dt: float) -> None:
        """
        Update ejector degradation over time
        
        Args:
            dt: Time step (hours)
        """
        if self.is_operating:
            # Nozzle fouling (reduces jet velocity)
            fouling_rate = self.config.nozzle_fouling_rate
            self.nozzle_fouling_factor = max(0.5, 
                self.nozzle_fouling_factor - fouling_rate * dt)
            
            # Diffuser fouling (reduces compression efficiency)
            diffuser_fouling_rate = self.config.diffuser_fouling_rate
            self.diffuser_fouling_factor = max(0.6, 
                self.diffuser_fouling_factor - diffuser_fouling_rate * dt)
            
            # Nozzle erosion (increases nozzle area, reduces velocity)
            erosion_rate = self.config.erosion_rate
            self.nozzle_erosion_factor = max(0.7, 
                self.nozzle_erosion_factor - erosion_rate * dt)
            
            # Operating hours accumulation
            self.operating_hours += dt
        
        # Overall performance factor
        self.overall_performance_factor = (self.nozzle_fouling_factor * 
                                         self.diffuser_fouling_factor * 
                                         self.nozzle_erosion_factor)
    
    def start_ejector(self, motive_steam_pressure: float) -> bool:
        """
        Start the steam jet ejector
        
        Args:
            motive_steam_pressure: Available motive steam pressure (MPa)
            
        Returns:
            True if start successful, False otherwise
        """
        if not self.motive_steam_available:
            return False
        
        if motive_steam_pressure < self.config.min_motive_pressure:
            return False
        
        self.is_operating = True
        self.motive_steam_pressure_actual = motive_steam_pressure
        return True
    
    def stop_ejector(self) -> bool:
        """
        Stop the steam jet ejector
        
        Returns:
            True if stop successful, False otherwise
        """
        self.is_operating = False
        self.current_capacity = 0.0
        self.motive_steam_flow = 0.0
        return True
    
    def perform_cleaning(self, cleaning_type: str = "chemical") -> None:
        """
        Perform cleaning/maintenance on the ejector
        
        Args:
            cleaning_type: Type of cleaning ("chemical", "mechanical", "replacement")
        """
        if cleaning_type == "chemical":
            # Chemical cleaning removes fouling
            self.nozzle_fouling_factor = min(1.0, self.nozzle_fouling_factor + 0.3)
            self.diffuser_fouling_factor = min(1.0, self.diffuser_fouling_factor + 0.4)
            
        elif cleaning_type == "mechanical":
            # Mechanical cleaning removes fouling and some erosion effects
            self.nozzle_fouling_factor = min(1.0, self.nozzle_fouling_factor + 0.4)
            self.diffuser_fouling_factor = min(1.0, self.diffuser_fouling_factor + 0.5)
            self.nozzle_erosion_factor = min(1.0, self.nozzle_erosion_factor + 0.1)
            
        elif cleaning_type == "replacement":
            # Nozzle replacement restores full performance
            self.nozzle_fouling_factor = 1.0
            self.diffuser_fouling_factor = 1.0
            self.nozzle_erosion_factor = 1.0
        
        # Update overall performance
        self.overall_performance_factor = (self.nozzle_fouling_factor * 
                                         self.diffuser_fouling_factor * 
                                         self.nozzle_erosion_factor)
    
    def update_state(self,
                    suction_pressure: float,
                    required_capacity: float,
                    motive_steam_pressure: float,
                    motive_steam_temperature: float,
                    dt: float) -> Dict[str, float]:
        """
        Update ejector state for one time step
        
        Args:
            suction_pressure: Current suction pressure (MPa)
            required_capacity: Required air removal capacity (kg/s)
            motive_steam_pressure: Motive steam pressure (MPa)
            motive_steam_temperature: Motive steam temperature (°C)
            dt: Time step (hours)
            
        Returns:
            Dictionary with ejector performance results
        """
        self.suction_pressure = suction_pressure
        self.motive_steam_pressure_actual = motive_steam_pressure
        self.motive_steam_temp_actual = motive_steam_temperature
        
        if self.is_operating and self.motive_steam_available:
            # Calculate ejector performance
            capacity, performance = self.calculate_steam_jet_performance(
                suction_pressure, required_capacity,
                motive_steam_pressure, motive_steam_temperature
            )
            
            self.current_capacity = capacity
            self.motive_steam_flow = performance.get('motive_steam_flow', 0.0)
            self.steam_consumption_rate = performance.get('steam_consumption_rate', 0.0)
            self.compression_ratio_actual = performance.get('compression_ratio', 1.0)
            self.entrainment_ratio = performance.get('entrainment_ratio', 0.0)
            
            # Calculate multi-stage performance
            multistage = self.calculate_multistage_performance(capacity, suction_pressure)
            
            # Update degradation
            self.update_degradation(dt)
            
        else:
            self.current_capacity = 0.0
            self.motive_steam_flow = 0.0
            self.steam_consumption_rate = 0.0
            multistage = {'first_stage_capacity': 0.0, 'intercondenser_load': 0.0}
        
        return {
            'ejector_id': self.config.ejector_id,
            'is_operating': self.is_operating,
            'capacity': self.current_capacity,
            'motive_steam_flow': self.motive_steam_flow,
            'steam_consumption_rate': self.steam_consumption_rate,
            'compression_ratio': self.compression_ratio_actual,
            'entrainment_ratio': self.entrainment_ratio,
            'suction_pressure': self.suction_pressure,
            'motive_steam_pressure': self.motive_steam_pressure_actual,
            'motive_steam_temperature': self.motive_steam_temp_actual,
            'performance_factor': self.overall_performance_factor,
            'nozzle_fouling': self.nozzle_fouling_factor,
            'diffuser_fouling': self.diffuser_fouling_factor,
            'nozzle_erosion': self.nozzle_erosion_factor,
            'operating_hours': self.operating_hours,
            'first_stage_capacity': multistage.get('first_stage_capacity', 0.0),
            'intercondenser_load': multistage.get('intercondenser_load', 0.0)
        }
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        return {
            f'{self.config.ejector_id}_operating': float(self.is_operating),
            f'{self.config.ejector_id}_capacity': self.current_capacity,
            f'{self.config.ejector_id}_steam_flow': self.motive_steam_flow,
            f'{self.config.ejector_id}_steam_consumption': self.steam_consumption_rate,
            f'{self.config.ejector_id}_performance': self.overall_performance_factor,
            f'{self.config.ejector_id}_operating_hours': self.operating_hours,
            f'{self.config.ejector_id}_nozzle_fouling': self.nozzle_fouling_factor,
            f'{self.config.ejector_id}_compression_ratio': self.compression_ratio_actual
        }
    
    def reset(self) -> None:
        """Reset ejector to initial conditions"""
        self.is_operating = False
        self.motive_steam_available = True
        self.operating_hours = 0.0
        self.current_capacity = 0.0
        self.motive_steam_flow = 0.0
        self.nozzle_fouling_factor = 1.0
        self.diffuser_fouling_factor = 1.0
        self.nozzle_erosion_factor = 1.0
        self.overall_performance_factor = 1.0


# Example usage and testing
if __name__ == "__main__":
    # Create ejector configuration
    config = SteamEjectorConfig(
        ejector_id="SJE-001",
        ejector_type="two_stage",
        design_capacity=25.0,
        motive_steam_pressure=1.0
    )
    
    # Create ejector model
    ejector = SteamJetEjector(config)
    
    print("Steam Jet Ejector Model - Parameter Validation")
    print("=" * 55)
    print(f"Ejector ID: {config.ejector_id}")
    print(f"Type: {config.ejector_type}")
    print(f"Design Capacity: {config.design_capacity} kg/s air")
    print(f"Motive Steam Pressure: {config.motive_steam_pressure} MPa")
    print(f"Steam Consumption: {config.base_steam_consumption} kg steam/kg air")
    print()
    
    # Test ejector operation
    ejector.start_ejector(motive_steam_pressure=1.0)
    
    # Simulate operation over time
    for hour in range(100):
        result = ejector.update_state(
            suction_pressure=0.007,
            required_capacity=20.0,
            motive_steam_pressure=1.0,
            motive_steam_temperature=180.0,
            dt=1.0
        )
        
        if hour % 20 == 0:
            print(f"Hour {hour}:")
            print(f"  Capacity: {result['capacity']:.2f} kg/s")
            print(f"  Steam Flow: {result['motive_steam_flow']:.2f} kg/s")
            print(f"  Steam Consumption: {result['steam_consumption_rate']:.2f} kg/kg")
            print(f"  Performance: {result['performance_factor']:.3f}")
            print(f"  Compression Ratio: {result['compression_ratio']:.1f}")
            print()
