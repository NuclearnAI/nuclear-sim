"""
Water Chemistry and Treatment System

This module provides water quality monitoring and chemical treatment modeling
for the feedwater system, following the modular architecture pattern.

Key Features:
1. Water quality parameter tracking
2. Chemical treatment system modeling
3. Corrosion and scaling index calculations
4. Treatment effectiveness monitoring
5. Impact on pump performance
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import warnings

warnings.filterwarnings("ignore")


@dataclass
class WaterQualityConfig:
    """Configuration for water quality monitoring and treatment"""
    
    # Design water quality parameters
    design_ph: float = 7.5                           # Design pH
    design_hardness: float = 150.0                   # mg/L as CaCO3
    design_tds: float = 500.0                        # mg/L total dissolved solids
    design_chloride: float = 50.0                    # mg/L chloride
    design_dissolved_oxygen: float = 8.0             # mg/L dissolved oxygen
    design_silica: float = 20.0                      # mg/L silica
    
    # Chemical treatment parameters
    chlorine_dose_rate: float = 1.0                  # mg/L target free chlorine
    antiscalant_dose_rate: float = 5.0               # mg/L antiscalant
    corrosion_inhibitor_dose: float = 10.0           # mg/L corrosion inhibitor
    biocide_dose_rate: float = 0.0                   # mg/L biocide (intermittent)
    
    # Water quality limits
    ph_min: float = 6.5                              # Minimum allowable pH
    ph_max: float = 8.5                              # Maximum allowable pH
    hardness_max: float = 300.0                      # mg/L maximum hardness
    chloride_max: float = 200.0                      # mg/L maximum chloride
    tds_max: float = 1000.0                          # mg/L maximum TDS
    
    # Treatment system parameters
    treatment_efficiency: float = 0.95               # Treatment system efficiency
    blowdown_rate: float = 0.02                      # Fraction of flow as blowdown
    makeup_rate: float = 0.05                        # Fraction of flow as makeup


class ChemicalTreatmentSystem:
    """
    Chemical treatment system for feedwater quality control
    
    This system manages:
    1. Chemical dosing and control
    2. Treatment effectiveness monitoring
    3. Chemical consumption tracking
    4. System performance optimization
    """
    
    def __init__(self, config: WaterQualityConfig):
        """Initialize chemical treatment system"""
        self.config = config
        
        # Chemical inventory and dosing
        self.chlorine_inventory = 1000.0                # kg chlorine inventory
        self.antiscalant_inventory = 500.0              # kg antiscalant inventory
        self.corrosion_inhibitor_inventory = 800.0      # kg corrosion inhibitor inventory
        self.biocide_inventory = 200.0                  # kg biocide inventory
        
        # Dosing system status
        self.chlorine_pump_available = True
        self.antiscalant_pump_available = True
        self.corrosion_inhibitor_pump_available = True
        self.biocide_pump_available = True
        
        # Treatment effectiveness
        self.chlorine_effectiveness = 1.0               # Chlorine treatment effectiveness
        self.antiscalant_effectiveness = 1.0            # Antiscalant effectiveness
        self.corrosion_inhibitor_effectiveness = 1.0    # Corrosion inhibitor effectiveness
        
        # Chemical consumption tracking
        self.total_chlorine_consumed = 0.0              # kg total chlorine consumed
        self.total_antiscalant_consumed = 0.0           # kg total antiscalant consumed
        self.total_corrosion_inhibitor_consumed = 0.0   # kg total corrosion inhibitor consumed
        
        # System performance
        self.treatment_system_efficiency = config.treatment_efficiency
        self.last_maintenance_time = 0.0
        
    def calculate_chemical_doses(self,
                               water_flow_rate: float,
                               water_quality: Dict[str, float],
                               dt: float) -> Dict[str, float]:
        """
        Calculate required chemical doses based on water conditions
        
        Args:
            water_flow_rate: Water flow rate (kg/s)
            water_quality: Current water quality parameters
            dt: Time step (hours)
            
        Returns:
            Dictionary with chemical doses
        """
        # Base chemical doses
        chlorine_dose = self.config.chlorine_dose_rate
        antiscalant_dose = self.config.antiscalant_dose_rate
        corrosion_inhibitor_dose = self.config.corrosion_inhibitor_dose
        biocide_dose = self.config.biocide_dose_rate
        
        # Adjust doses based on water quality
        ph = water_quality.get('ph', self.config.design_ph)
        hardness = water_quality.get('hardness', self.config.design_hardness)
        chloride = water_quality.get('chloride', self.config.design_chloride)
        tds = water_quality.get('total_dissolved_solids', self.config.design_tds)
        
        # Chlorine dose adjustment based on organic loading and pH
        if ph < 7.0:
            chlorine_dose *= 1.2  # More chlorine needed at low pH
        elif ph > 8.0:
            chlorine_dose *= 0.8  # Less effective at high pH
        
        # Antiscalant dose adjustment based on hardness and TDS
        hardness_factor = max(1.0, hardness / self.config.design_hardness)
        tds_factor = max(1.0, tds / self.config.design_tds)
        antiscalant_dose *= (hardness_factor * tds_factor) ** 0.5
        
        # Corrosion inhibitor dose adjustment based on chloride and pH
        chloride_factor = max(1.0, chloride / self.config.design_chloride)
        if ph < 7.0 or ph > 8.0:
            ph_factor = 1.3  # More inhibitor needed outside optimal pH range
        else:
            ph_factor = 1.0
        corrosion_inhibitor_dose *= chloride_factor * ph_factor
        
        # Apply treatment system efficiency
        chlorine_dose *= self.treatment_system_efficiency * self.chlorine_effectiveness
        antiscalant_dose *= self.treatment_system_efficiency * self.antiscalant_effectiveness
        corrosion_inhibitor_dose *= self.treatment_system_efficiency * self.corrosion_inhibitor_effectiveness
        
        # Check chemical availability
        if not self.chlorine_pump_available or self.chlorine_inventory < 1.0:
            chlorine_dose = 0.0
        
        if not self.antiscalant_pump_available or self.antiscalant_inventory < 1.0:
            antiscalant_dose = 0.0
        
        if not self.corrosion_inhibitor_pump_available or self.corrosion_inhibitor_inventory < 1.0:
            corrosion_inhibitor_dose = 0.0
        
        # Calculate chemical consumption
        flow_rate_m3h = water_flow_rate * 3.6  # Convert kg/s to m³/h (assuming density = 1000 kg/m³)
        
        chlorine_consumption = chlorine_dose * flow_rate_m3h * dt / 1000.0  # kg
        antiscalant_consumption = antiscalant_dose * flow_rate_m3h * dt / 1000.0  # kg
        corrosion_inhibitor_consumption = corrosion_inhibitor_dose * flow_rate_m3h * dt / 1000.0  # kg
        
        # Update inventories
        self.chlorine_inventory = max(0.0, self.chlorine_inventory - chlorine_consumption)
        self.antiscalant_inventory = max(0.0, self.antiscalant_inventory - antiscalant_consumption)
        self.corrosion_inhibitor_inventory = max(0.0, self.corrosion_inhibitor_inventory - corrosion_inhibitor_consumption)
        
        # Update total consumption
        self.total_chlorine_consumed += chlorine_consumption
        self.total_antiscalant_consumed += antiscalant_consumption
        self.total_corrosion_inhibitor_consumed += corrosion_inhibitor_consumption
        
        return {
            'chlorine': chlorine_dose,
            'antiscalant': antiscalant_dose,
            'corrosion_inhibitor': corrosion_inhibitor_dose,
            'biocide': biocide_dose,
            'chlorine_consumption': chlorine_consumption,
            'antiscalant_consumption': antiscalant_consumption,
            'corrosion_inhibitor_consumption': corrosion_inhibitor_consumption
        }
    
    def perform_treatment_maintenance(self, **kwargs) -> Dict[str, float]:
        """Perform treatment system maintenance"""
        maintenance_type = kwargs.get('maintenance_type', 'standard')
        
        results = {}
        
        if maintenance_type == 'pump_maintenance':
            # Reset pump availability
            self.chlorine_pump_available = True
            self.antiscalant_pump_available = True
            self.corrosion_inhibitor_pump_available = True
            self.biocide_pump_available = True
            results['pump_maintenance'] = True
            
        elif maintenance_type == 'chemical_refill':
            # Refill chemical inventories
            self.chlorine_inventory = 1000.0
            self.antiscalant_inventory = 500.0
            self.corrosion_inhibitor_inventory = 800.0
            self.biocide_inventory = 200.0
            results['chemical_refill'] = True
            
        elif maintenance_type == 'system_calibration':
            # Reset treatment effectiveness
            self.chlorine_effectiveness = 1.0
            self.antiscalant_effectiveness = 1.0
            self.corrosion_inhibitor_effectiveness = 1.0
            self.treatment_system_efficiency = self.config.treatment_efficiency
            results['system_calibration'] = True
            
        else:
            # Full maintenance
            self.chlorine_pump_available = True
            self.antiscalant_pump_available = True
            self.corrosion_inhibitor_pump_available = True
            self.biocide_pump_available = True
            self.chlorine_inventory = 1000.0
            self.antiscalant_inventory = 500.0
            self.corrosion_inhibitor_inventory = 800.0
            self.biocide_inventory = 200.0
            self.chlorine_effectiveness = 1.0
            self.antiscalant_effectiveness = 1.0
            self.corrosion_inhibitor_effectiveness = 1.0
            self.treatment_system_efficiency = self.config.treatment_efficiency
            results['full_maintenance'] = True
        
        self.last_maintenance_time = 0.0
        
        return results


class WaterQualityModel:
    """
    Water quality monitoring and modeling system
    
    This system tracks:
    1. Water quality parameters
    2. Scaling and corrosion indices
    3. Treatment effectiveness
    4. Impact on system performance
    """
    
    def __init__(self, config: WaterQualityConfig):
        """Initialize water quality model"""
        self.config = config
        
        # Current water quality parameters
        self.ph = config.design_ph
        self.hardness = config.design_hardness              # mg/L as CaCO3
        self.total_dissolved_solids = config.design_tds     # mg/L
        self.chloride = config.design_chloride              # mg/L
        self.dissolved_oxygen = config.design_dissolved_oxygen  # mg/L
        self.silica = config.design_silica                  # mg/L
        
        # Chemical treatment levels
        self.chlorine_residual = 0.5                        # mg/L free chlorine
        self.antiscalant_concentration = config.antiscalant_dose_rate
        self.corrosion_inhibitor_level = config.corrosion_inhibitor_dose
        self.biocide_concentration = 0.0                    # mg/L (intermittent)
        
        # Calculated indices
        self.langelier_saturation_index = 0.0              # Scaling tendency
        self.ryznar_stability_index = 0.0                  # Corrosion tendency
        self.biological_growth_potential = 0.0             # Growth risk (0-1)
        self.water_aggressiveness = 0.0                     # Overall aggressiveness factor
        
        # Treatment system
        self.treatment_system = ChemicalTreatmentSystem(config)
        
        # Performance tracking
        self.concentration_factor = 1.0                     # Concentration due to evaporation
        self.treatment_efficiency = 1.0                     # Overall treatment efficiency
        
    def calculate_scaling_indices(self) -> Tuple[float, float]:
        """
        Calculate Langelier Saturation Index and Ryznar Stability Index
        
        Returns:
            Tuple of (LSI, RSI)
        """
        # Simplified LSI calculation
        # LSI = pH - pHs (saturation pH)
        # pHs = (9.3 + A + B) - (C + D)
        
        # Approximate calculations for typical feedwater
        temp_factor = 25.0  # Assume 25°C average
        A = (np.log10(self.total_dissolved_solids) - 1) / 10
        B = -13.12 * np.log10(temp_factor + 273) + 34.55
        C = np.log10(self.hardness) - 0.4
        D = np.log10(120)  # Assume alkalinity = 120 mg/L as CaCO3
        
        ph_saturation = (9.3 + A + B) - (C + D)
        lsi = self.ph - ph_saturation
        
        # RSI = 2 * pHs - pH
        rsi = 2 * ph_saturation - self.ph
        
        return lsi, rsi
    
    def calculate_biological_growth_potential(self, temperature: float = 30.0) -> float:
        """
        Calculate biological growth potential
        
        Args:
            temperature: Water temperature (°C)
            
        Returns:
            Growth potential (0-1, where 1 is high growth risk)
        """
        # Temperature effect (optimal around 30-35°C)
        if temperature < 20:
            temp_factor = 0.1
        elif temperature < 30:
            temp_factor = (temperature - 20) / 10 * 0.5 + 0.1
        elif temperature < 40:
            temp_factor = 0.6 + (temperature - 30) / 10 * 0.4
        else:
            temp_factor = 1.0 - (temperature - 40) / 20 * 0.3
        
        # Chlorine disinfection effect
        chlorine_factor = 1.0 / (1.0 + self.chlorine_residual * 3.0)
        
        # Nutrient availability (simplified - based on TDS)
        nutrient_factor = min(1.0, self.total_dissolved_solids / 1000.0)
        
        # pH effect (optimal around neutral)
        ph_factor = 1.0 - abs(self.ph - 7.0) / 3.0
        ph_factor = max(0.1, ph_factor)
        
        growth_potential = temp_factor * chlorine_factor * nutrient_factor * ph_factor
        return np.clip(growth_potential, 0.0, 1.0)
    
    def update_water_chemistry(self,
                             makeup_water_quality: Dict[str, float],
                             blowdown_rate: float,
                             chemical_doses: Dict[str, float],
                             dt: float) -> Dict[str, float]:
        """
        Update water chemistry based on makeup, blowdown, and chemical addition
        
        Args:
            makeup_water_quality: Makeup water quality parameters
            blowdown_rate: Blowdown rate as fraction of circulation
            chemical_doses: Chemical dose rates
            dt: Time step (hours)
            
        Returns:
            Dictionary with water quality results
        """
        # Concentration factor due to evaporation and blowdown
        self.concentration_factor = 1.0 / (blowdown_rate + 0.01)  # 0.01 for evaporation
        self.concentration_factor = min(self.concentration_factor, 5.0)  # Practical limit
        
        # Update dissolved solids (concentrate due to evaporation)
        makeup_tds = makeup_water_quality.get('tds', 300.0)
        self.total_dissolved_solids = makeup_tds * self.concentration_factor
        
        # Update hardness
        makeup_hardness = makeup_water_quality.get('hardness', 100.0)
        self.hardness = makeup_hardness * self.concentration_factor
        
        # Update chloride
        makeup_chloride = makeup_water_quality.get('chloride', 30.0)
        self.chloride = makeup_chloride * self.concentration_factor
        
        # pH tends toward makeup water pH but is affected by concentration
        makeup_ph = makeup_water_quality.get('ph', 7.2)
        ph_drift = (makeup_ph - self.ph) * 0.1 * dt  # Slow drift
        self.ph += ph_drift
        
        # Dissolved oxygen from makeup and aeration
        makeup_do = makeup_water_quality.get('dissolved_oxygen', 8.0)
        self.dissolved_oxygen = makeup_do * 0.8  # Some loss due to heating
        
        # Update chemical concentrations
        self.chlorine_residual = chemical_doses.get('chlorine', 0.5)
        self.antiscalant_concentration = chemical_doses.get('antiscalant', 5.0)
        self.corrosion_inhibitor_level = chemical_doses.get('corrosion_inhibitor', 10.0)
        self.biocide_concentration = chemical_doses.get('biocide', 0.0)
        
        # Chemical decay over time
        chlorine_decay_rate = 0.1  # 1/hour
        self.chlorine_residual *= np.exp(-chlorine_decay_rate * dt)
        
        # Calculate scaling and corrosion indices
        self.langelier_saturation_index, self.ryznar_stability_index = self.calculate_scaling_indices()
        
        # Calculate biological growth potential
        avg_temp = 30.0  # Approximate average temperature
        self.biological_growth_potential = self.calculate_biological_growth_potential(avg_temp)
        
        # Water quality aggressiveness factor for pump degradation
        # Higher LSI = more scaling, lower RSI = more corrosive
        scaling_aggressiveness = max(0.0, self.langelier_saturation_index)
        corrosion_aggressiveness = max(0.0, 6.0 - self.ryznar_stability_index) / 3.0
        chloride_aggressiveness = self.chloride / 100.0  # Chloride promotes corrosion
        
        self.water_aggressiveness = (scaling_aggressiveness + 
                                   corrosion_aggressiveness + 
                                   chloride_aggressiveness) / 3.0
        
        # Calculate treatment efficiency
        chemical_effectiveness = (
            (1.0 if self.chlorine_residual > 0.2 else 0.5) *
            (1.0 if self.antiscalant_concentration > 2.0 else 0.7) *
            (1.0 if self.corrosion_inhibitor_level > 5.0 else 0.8)
        )
        
        self.treatment_efficiency = chemical_effectiveness * self.treatment_system.treatment_system_efficiency
        
        return {
            'ph': self.ph,
            'hardness': self.hardness,
            'total_dissolved_solids': self.total_dissolved_solids,
            'chloride': self.chloride,
            'dissolved_oxygen': self.dissolved_oxygen,
            'silica': self.silica,
            'chlorine_residual': self.chlorine_residual,
            'antiscalant': self.antiscalant_concentration,
            'corrosion_inhibitor': self.corrosion_inhibitor_level,
            'biocide': self.biocide_concentration,
            'langelier_index': self.langelier_saturation_index,
            'ryznar_index': self.ryznar_stability_index,
            'biological_growth_potential': self.biological_growth_potential,
            'concentration_factor': self.concentration_factor,
            'water_aggressiveness': self.water_aggressiveness,
            'treatment_efficiency': self.treatment_efficiency,
            'nutrient_level': min(2.0, self.total_dissolved_solids / 500.0)
        }
    
    def perform_treatment_maintenance(self, **kwargs) -> Dict[str, float]:
        """Perform water treatment maintenance"""
        return self.treatment_system.perform_treatment_maintenance(**kwargs)
    
    def get_state_dict(self) -> Dict[str, float]:
        """Get current state as dictionary for logging/monitoring"""
        state_dict = {
            'water_quality_ph': self.ph,
            'water_quality_hardness': self.hardness,
            'water_quality_tds': self.total_dissolved_solids,
            'water_quality_chloride': self.chloride,
            'water_quality_dissolved_oxygen': self.dissolved_oxygen,
            'water_quality_chlorine_residual': self.chlorine_residual,
            'water_quality_langelier_index': self.langelier_saturation_index,
            'water_quality_ryznar_index': self.ryznar_stability_index,
            'water_quality_biological_growth': self.biological_growth_potential,
            'water_quality_aggressiveness': self.water_aggressiveness,
            'water_quality_treatment_efficiency': self.treatment_efficiency,
            'water_quality_concentration_factor': self.concentration_factor
        }
        
        # Add chemical treatment system state
        state_dict.update({
            'chemical_chlorine_inventory': self.treatment_system.chlorine_inventory,
            'chemical_antiscalant_inventory': self.treatment_system.antiscalant_inventory,
            'chemical_corrosion_inhibitor_inventory': self.treatment_system.corrosion_inhibitor_inventory,
            'chemical_treatment_efficiency': self.treatment_system.treatment_system_efficiency,
            'chemical_chlorine_consumed': self.treatment_system.total_chlorine_consumed,
            'chemical_antiscalant_consumed': self.treatment_system.total_antiscalant_consumed
        })
        
        return state_dict
    
    def reset(self):
        """Reset water quality model to initial conditions"""
        self.ph = self.config.design_ph
        self.hardness = self.config.design_hardness
        self.total_dissolved_solids = self.config.design_tds
        self.chloride = self.config.design_chloride
        self.dissolved_oxygen = self.config.design_dissolved_oxygen
        self.silica = self.config.design_silica
        
        self.chlorine_residual = 0.5
        self.antiscalant_concentration = self.config.antiscalant_dose_rate
        self.corrosion_inhibitor_level = self.config.corrosion_inhibitor_dose
        self.biocide_concentration = 0.0
        
        self.langelier_saturation_index = 0.0
        self.ryznar_stability_index = 0.0
        self.biological_growth_potential = 0.0
        self.water_aggressiveness = 0.0
        self.concentration_factor = 1.0
        self.treatment_efficiency = 1.0
        
        # Reset treatment system
        self.treatment_system = ChemicalTreatmentSystem(self.config)


# Example usage and testing
if __name__ == "__main__":
    print("Water Chemistry and Treatment System - Test")
    print("=" * 50)
    
    # Create water quality system
    config = WaterQualityConfig()
    water_quality = WaterQualityModel(config)
    
    print(f"Water Quality System Configuration:")
    print(f"  Design pH: {config.design_ph}")
    print(f"  Design Hardness: {config.design_hardness} mg/L")
    print(f"  Design TDS: {config.design_tds} mg/L")
    print(f"  Design Chloride: {config.design_chloride} mg/L")
    print(f"  Chlorine Dose Rate: {config.chlorine_dose_rate} mg/L")
    print(f"  Antiscalant Dose Rate: {config.antiscalant_dose_rate} mg/L")
    print()
    
    # Test water quality monitoring
    print("Water Quality Monitoring Test:")
    print(f"{'Time':<6} {'pH':<6} {'Hardness':<10} {'TDS':<8} {'LSI':<8} {'Aggressiveness':<14}")
    print("-" * 60)
    
    makeup_water = {
        'tds': 300.0,
        'hardness': 100.0,
        'chloride': 30.0,
        'ph': 7.2,
        'dissolved_oxygen': 8.0
    }
    
    chemical_doses = {
        'chlorine': 1.0,
        'antiscalant': 5.0,
        'corrosion_inhibitor': 10.0,
        'biocide': 0.0
    }
    
    for hour in range(24):
        # Simulate varying conditions
        blowdown_rate = 0.02 + 0.005 * np.sin(hour * 0.1)  # Varying blowdown
        
        result = water_quality.update_water_chemistry(
            makeup_water_quality=makeup_water,
            blowdown_rate=blowdown_rate,
            chemical_doses=chemical_doses,
            dt=1.0
        )
        
        if hour % 4 == 0:  # Print every 4 hours
            print(f"{hour:<6} {result['ph']:<6.2f} {result['hardness']:<10.0f} "
                  f"{result['total_dissolved_solids']:<8.0f} {result['langelier_index']:<8.2f} "
                  f"{result['water_aggressiveness']:<14.3f}")
    
    print()
    print("Water chemistry system ready for integration!")
