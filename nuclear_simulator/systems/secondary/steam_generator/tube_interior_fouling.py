"""
Tube Interior Fouling Model

This module implements tube interior scaling physics for PWR steam generators,
focusing on primary side scale formation on tube inner surfaces. This is
separate from TSP fouling which occurs on the secondary side.

Key Features:
1. Primary side scale formation (much slower than TSP fouling)
2. Thermal resistance calculation from scale thickness
3. Primary chemistry effects (boric acid, lithium hydroxide)
4. Realistic maintenance with different access requirements
5. Physics-based heat transfer degradation

Physical Basis:
- Scale formation on primary side tube surfaces
- Thermal resistance from scale deposits
- Primary chemistry inhibits scaling (boric acid effect)
- Much slower rates than secondary side TSP fouling
- Different maintenance access and effectiveness

References:
- PWR Primary Chemistry Guidelines
- EPRI Primary Water Chemistry Guidelines
- NRC Primary System Chemistry Requirements
"""

import numpy as np
from typing import Dict, Optional, Tuple, Any
import warnings

# Import base fouling model
from .fouling_model_base import FoulingModelBase

# Import unified water chemistry system
try:
    from ..water_chemistry import WaterChemistry, WaterChemistryConfig
    WATER_CHEMISTRY_AVAILABLE = True
except ImportError:
    WATER_CHEMISTRY_AVAILABLE = False
    WaterChemistry = None
    WaterChemistryConfig = None

warnings.filterwarnings("ignore")


class TubeInteriorFouling(FoulingModelBase):
    """
    Tube interior fouling model for PWR steam generator primary side
    
    This model simulates scale formation on the inner surfaces of steam
    generator tubes (primary side), which is different from TSP fouling
    that occurs on the secondary side.
    
    Key Differences from TSP Fouling:
    - Location: Primary side (tube interior) vs secondary side (TSP crevices)
    - Rate: Much slower (0.001-0.01 mm/year vs 0.1-1.0 mm/year)
    - Chemistry: Primary chemistry (boric acid, lithium) vs secondary chemistry
    - Effect: Direct thermal resistance vs flow restriction + mixing degradation
    - Maintenance: Primary side access (radioactive) vs secondary side access
    """
    
    def __init__(self, config: Optional[Any] = None, water_chemistry: Optional[WaterChemistry] = None):
        """Initialize tube interior fouling model"""
        super().__init__(config, water_chemistry)
        
        # === TUBE INTERIOR SCALE STATE VARIABLES ===
        # Scale physical properties
        self.scale_thickness = 0.0                  # mm - total scale thickness on tube interior
        self.scale_thermal_resistance = 0.0         # m²K/W - thermal resistance from scale
        self.scale_formation_rate = 0.0             # mm/year - current formation rate
        
        # Scale composition (simplified for primary side)
        self.scale_composition = {
            'iron_oxide': 0.0,      # mm - iron oxide scale (magnetite, hematite)
            'crud_deposits': 0.0,   # mm - CRUD (Chalk River Unidentified Deposits)
            'corrosion_products': 0.0  # mm - other corrosion products
        }
        
        # === PRIMARY CHEMISTRY PARAMETERS ===
        # Typical PWR primary chemistry
        self.boric_acid_concentration = 1000.0      # ppm B (as H3BO3)
        self.lithium_concentration = 2.0            # ppm Li (as LiOH)
        self.primary_ph = 7.2                       # Primary pH (controlled by Li/B ratio)
        self.dissolved_hydrogen = 25.0              # cc/kg H2 (for corrosion control)
        self.dissolved_oxygen_primary = 0.005       # ppm O2 (very low in primary)
        
        # === SCALE FORMATION PARAMETERS ===
        # Base formation rates (much slower than secondary side)
        self.base_scale_rate = 0.001                # mm/year base scale formation rate
        self.iron_oxide_rate_factor = 1.0           # Iron oxide formation factor
        self.crud_rate_factor = 0.5                 # CRUD formation factor
        self.corrosion_rate_factor = 0.3            # General corrosion factor
        
        # Chemistry effects on scaling
        self.boric_acid_inhibition_factor = 0.5     # Boric acid inhibits scaling
        self.lithium_effect_factor = 0.8            # Lithium effect on pH and scaling
        self.temperature_activation_energy = 65000.0 # J/mol (PHYSICS CORRECTED - realistic for oxide formation)
        
        # === SCALE PROPERTIES ===
        # Thermal properties of scale deposits (PHYSICS CORRECTED)
        self.scale_thermal_conductivity = 0.2       # W/m/K (realistic CRUD/scale conductivity)
        self.scale_density = 3500.0                 # kg/m³ (typical scale density)
        
        # Component-specific thermal conductivities (W/m/K)
        self.iron_oxide_conductivity = .5          # Magnetite/hematite (higher)
        self.crud_conductivity = 0.15               # CRUD deposits (very low)
        self.corrosion_products_conductivity = 0.3  # Other corrosion products
        
        # === MAINTENANCE PARAMETERS ===
        # Primary side maintenance characteristics
        self.chemical_cleaning_effectiveness = 0.90  # 90% scale removal (better access)
        self.mechanical_cleaning_effectiveness = 0.95 # 95% scale removal
        self.maintenance_radiation_exposure = True   # Primary side is radioactive
        self.maintenance_access_difficulty = "high"  # Requires primary system shutdown
    
    def calculate_scale_formation_rate(self, 
                                     temperature: float,
                                     flow_velocity: float,
                                     primary_chemistry: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate scale formation rate on tube interior surfaces
        
        Args:
            temperature: Primary coolant temperature (°C)
            flow_velocity: Primary flow velocity (m/s)
            primary_chemistry: Primary chemistry parameters (optional)
            
        Returns:
            Scale formation rate (mm/year)
        """
        # Use provided chemistry or defaults
        if primary_chemistry:
            boric_acid = primary_chemistry.get('boric_acid_concentration', self.boric_acid_concentration)
            lithium = primary_chemistry.get('lithium_concentration', self.lithium_concentration)
            ph = primary_chemistry.get('primary_ph', self.primary_ph)
            dissolved_oxygen = primary_chemistry.get('dissolved_oxygen', self.dissolved_oxygen_primary)
        else:
            boric_acid = self.boric_acid_concentration
            lithium = self.lithium_concentration
            ph = self.primary_ph
            dissolved_oxygen = self.dissolved_oxygen_primary
        
        # Temperature effect (Arrhenius relationship)
        temp_factor = self.calculate_temperature_factor(
            temperature, 
            self.temperature_activation_energy, 
            reference_temp=320.0  # Primary side reference temperature
        )
        
        # Boric acid inhibition effect (boric acid strongly inhibits scaling)
        boric_acid_factor = 1.0 / (1.0 + boric_acid / 1000.0 * self.boric_acid_inhibition_factor)
        
        # Lithium effect (affects pH and corrosion)
        lithium_factor = 1.0 + (lithium - 2.0) * 0.1  # Optimal around 2 ppm
        lithium_factor = max(0.5, lithium_factor)
        
        # pH effect (primary side optimal around 7.2)
        ph_factor = self.calculate_ph_factor(ph, optimal_ph=7.2)
        
        # Flow velocity effect (higher velocity reduces scale formation)
        velocity_factor = self.calculate_flow_velocity_factor(
            flow_velocity, 
            reference_velocity=5.0,  # Higher reference for primary side
            exponent=-0.6  # PHYSICS CORRECTED - stronger velocity effect for scale removal
        )
        
        # Dissolved oxygen effect (higher oxygen increases corrosion/scaling)
        oxygen_factor = 1.0 + dissolved_oxygen * 10.0  # Strong effect of oxygen
        
        # Scale saturation effect (PHYSICS IMPROVEMENT - formation slows with thickness)
        saturation_thickness = 2.0  # mm - characteristic saturation thickness
        saturation_factor = np.exp(-self.scale_thickness / saturation_thickness)
        
        # Calculate total formation rate
        formation_rate = (self.base_scale_rate * 
                         temp_factor * 
                         boric_acid_factor * 
                         lithium_factor * 
                         ph_factor * 
                         velocity_factor * 
                         oxygen_factor * 
                         saturation_factor)  # PHYSICS CORRECTED - saturation effect
        
        # Physical limits (scale formation cannot be negative or extremely high)
        formation_rate = np.clip(formation_rate, 0.0, 0.1)  # Max 0.1 mm/year
        
        return formation_rate
    
    def get_effective_thermal_conductivity(self) -> float:
        """
        Calculate effective thermal conductivity based on scale composition
        
        Returns:
            Effective thermal conductivity (W/m/K)
        """
        if self.scale_thickness <= 0:
            return self.scale_thermal_conductivity
        
        # Calculate composition fractions
        total_thickness = max(self.scale_thickness, 0.001)  # Prevent division by zero
        iron_oxide_fraction = self.scale_composition['iron_oxide'] / total_thickness
        crud_fraction = self.scale_composition['crud_deposits'] / total_thickness
        corrosion_fraction = self.scale_composition['corrosion_products'] / total_thickness
        
        # Weighted average thermal conductivity
        effective_k = (iron_oxide_fraction * self.iron_oxide_conductivity +
                      crud_fraction * self.crud_conductivity +
                      corrosion_fraction * self.corrosion_products_conductivity)
        
        # Ensure minimum conductivity (avoid division by zero)
        effective_k = max(effective_k, 0.05)  # Minimum 0.05 W/m/K
        
        return effective_k
    
    def calculate_thermal_resistance(self) -> float:
        """
        Calculate thermal resistance from current scale thickness with composition effects
        
        Returns:
            Thermal resistance (m²K/W)
        """
        if self.scale_thickness <= 0:
            return 0.0
        
        # Convert scale thickness to thermal resistance
        thickness_m = self.scale_thickness / 1000.0  # Convert mm to m
        
        # Use composition-dependent thermal conductivity
        effective_conductivity = self.get_effective_thermal_conductivity()
        
        # Conduction resistance
        R_conduction = thickness_m / effective_conductivity
        
        # Contact resistance at scale-metal interface (PHYSICS IMPROVEMENT)
        R_contact = 1e-5  # m²K/W (typical contact resistance)
        
        # Fouling factor for surface roughness and porosity effects
        R_fouling = thickness_m * 0.001  # Additional resistance factor
        
        total_resistance = R_conduction + R_contact + R_fouling
        
        return total_resistance
    
    def update_scale_buildup(self, dt_seconds: float) -> None:
        """
        Update scale accumulation during normal operation
        
        Args:
            dt_seconds: Time step (seconds)
        """
        dt_years = dt_seconds / (365.25 * 24.0 * 3600.0)  # Convert seconds to years
        
        # Calculate scale increase
        scale_increase = self.scale_formation_rate * dt_years
        
        # Update scale thickness
        self.scale_thickness += scale_increase
        
        # Update scale composition (simplified distribution)
        self.scale_composition['iron_oxide'] += scale_increase * 0.6      # 60% iron oxide
        self.scale_composition['crud_deposits'] += scale_increase * 0.3   # 30% CRUD
        self.scale_composition['corrosion_products'] += scale_increase * 0.1  # 10% other
        
        # Update thermal resistance
        self.scale_thermal_resistance = self.calculate_thermal_resistance()
        
        # Update fouling fraction (for base class compatibility)
        # Scale fouling fraction based on thermal resistance impact
        max_resistance = 0.001  # m²K/W - significant thermal resistance
        self.fouling_fraction = min(self.scale_thermal_resistance / max_resistance, 1.0)
    
    def update_fouling_state(self,
                           primary_conditions: Dict[str, float],
                           dt_seconds: float) -> Dict[str, Any]:
        """
        Update tube interior fouling state for one time step
        
        Args:
            primary_conditions: Primary side operating conditions
            dt_seconds: Time step (seconds)
            
        Returns:
            Dictionary with updated fouling state
        """
        # Update operating time (from base class)
        self.update_operating_time(dt_seconds)
        
        # Extract primary conditions
        temperature = primary_conditions.get('temperature', 320.0)
        flow_velocity = primary_conditions.get('flow_velocity', 5.0)
        primary_chemistry = primary_conditions.get('chemistry', None)
        
        # Calculate current scale formation rate
        self.scale_formation_rate = self.calculate_scale_formation_rate(
            temperature, flow_velocity, primary_chemistry
        )
        
        # Update scale buildup
        self.update_scale_buildup(dt_seconds)
        
        # Calculate performance impact
        thermal_efficiency_loss = self.scale_thermal_resistance * 1000.0  # Simplified calculation
        
        # Update cumulative performance loss
        dt_hours = dt_seconds / 3600.0  # Convert to hours for this calculation
        self.cumulative_performance_loss += thermal_efficiency_loss * dt_hours / 8760.0
        
        # Check replacement recommendation
        max_scale_thickness = 2.0  # mm - maximum acceptable scale thickness
        self.replacement_recommended = (
            self.scale_thickness >= max_scale_thickness or
            self.operating_years > 40.0  # Design life
        )
        
        return {
            'scale_thickness_mm': self.scale_thickness,
            'scale_thermal_resistance': self.scale_thermal_resistance,
            'scale_formation_rate_mm_per_year': self.scale_formation_rate,
            'thermal_efficiency_loss': thermal_efficiency_loss,
            'fouling_fraction': self.fouling_fraction,
            'operating_years': self.operating_years,
            'replacement_recommended': self.replacement_recommended,
            'scale_composition': self.scale_composition.copy()
        }
    
    def perform_maintenance(self, maintenance_type: str, **kwargs) -> Dict[str, Any]:
        """
        Perform tube interior maintenance using dict-in-function approach
        
        Args:
            maintenance_type: Type of maintenance to perform
            **kwargs: Additional maintenance parameters
            
        Returns:
            Dictionary with maintenance results
        """
        # Define maintenance functions in the function
        maintenance_functions = {
            'primary_scale_cleaning': self._primary_scale_cleaning,
            'tube_interior_inspection': self._tube_interior_inspection,
            'primary_chemistry_optimization': self._primary_chemistry_optimization,
            'tube_eddy_current_testing': self._tube_eddy_current_testing
        }
        
        if maintenance_type not in maintenance_functions:
            return {
                'success': False,
                'error': f'Unknown tube interior maintenance: {maintenance_type}',
                'available_types': list(maintenance_functions.keys())
            }
        
        # Execute maintenance function
        result = maintenance_functions[maintenance_type](**kwargs)
        
        # Update maintenance history (from base class)
        self._update_maintenance_history(result, maintenance_type)
        
        return result
    
    def _primary_scale_cleaning(self, **kwargs) -> Dict[str, Any]:
        """
        Perform primary side scale cleaning
        
        This is a major maintenance operation requiring primary system shutdown,
        draining, and radioactive work conditions.
        """
        cleaning_type = kwargs.get('cleaning_type', 'chemical')
        
        if cleaning_type == 'chemical':
            effectiveness = self.chemical_cleaning_effectiveness
            duration_hours = 48.0
            method = 'Chemical cleaning via tube interior access'
        elif cleaning_type == 'mechanical':
            effectiveness = self.mechanical_cleaning_effectiveness
            duration_hours = 72.0
            method = 'Mechanical cleaning with remote tools'
        else:
            effectiveness = 0.85
            duration_hours = 60.0
            method = 'Combined chemical and mechanical cleaning'
        
        # Calculate scale removal
        scale_removed = self.scale_thickness * effectiveness
        self.scale_thickness -= scale_removed
        self.scale_thickness = max(0.0, self.scale_thickness)
        
        # Update scale composition
        for component in self.scale_composition:
            self.scale_composition[component] *= (1.0 - effectiveness)
        
        # Recalculate thermal resistance
        self.scale_thermal_resistance = self.calculate_thermal_resistance()
        self.fouling_fraction = min(self.scale_thermal_resistance / 0.001, 1.0)
        
        return {
            'success': True,
            'duration_hours': duration_hours,
            'work_performed': f'Primary side scale cleaning - {method}',
            'findings': f'Removed {scale_removed:.3f} mm of scale deposits',
            'scale_removed_mm': scale_removed,
            'remaining_scale_mm': self.scale_thickness,
            'thermal_resistance_reduction': scale_removed / 1000.0 / self.scale_thermal_conductivity,
            'effectiveness_score': effectiveness,
            'next_maintenance_due': 35040.0,  # Every 4 years (major outage)
            'radiation_exposure': 'High - primary side work',
            'access_required': 'Primary system shutdown and drain',
            'specialized_equipment': [
                'Remote cleaning tools',
                'Radiation protection equipment',
                'Primary system isolation',
                'Chemical cleaning system'
            ],
            'parts_used': [
                'Chemical cleaning solutions',
                'Remote mechanical tools',
                'Radiation monitoring equipment'
            ]
        }
    
    def _tube_interior_inspection(self, **kwargs) -> Dict[str, Any]:
        """
        Perform tube interior inspection
        
        Comprehensive inspection of tube interior surfaces for scale,
        corrosion, and structural integrity.
        """
        inspection_type = kwargs.get('inspection_type', 'visual_and_measurement')
        
        # Assess current scale condition
        findings = []
        recommendations = []
        
        if self.scale_thickness > 1.0:
            findings.append(f'Significant scale buildup: {self.scale_thickness:.2f} mm')
            recommendations.append('Schedule scale cleaning within next outage')
        
        if self.scale_formation_rate > 0.01:
            findings.append(f'Elevated scale formation rate: {self.scale_formation_rate:.3f} mm/year')
            recommendations.append('Review primary chemistry control')
        
        if self.scale_thermal_resistance > 0.0005:
            findings.append(f'Thermal resistance impact: {self.scale_thermal_resistance:.6f} m²K/W')
            recommendations.append('Consider thermal performance optimization')
        
        # Check scale composition
        iron_oxide_fraction = self.scale_composition['iron_oxide'] / max(self.scale_thickness, 0.001)
        if iron_oxide_fraction > 0.8:
            findings.append('High iron oxide content in scale deposits')
            recommendations.append('Investigate primary system corrosion sources')
        
        if not findings:
            findings.append('Tube interior condition within acceptable limits')
        
        return {
            'success': True,
            'duration_hours': 8.0,
            'work_performed': f'Tube interior inspection - {inspection_type}',
            'findings': '; '.join(findings),
            'recommendations': recommendations,
            'scale_thickness_measured': self.scale_thickness,
            'scale_composition_analysis': self.scale_composition.copy(),
            'thermal_resistance_calculated': self.scale_thermal_resistance,
            'effectiveness_score': 1.0,  # Inspection always successful
            'next_maintenance_due': 8760.0,  # Annual inspection
            'radiation_exposure': 'Moderate - limited primary side access',
            'access_required': 'Primary system access during outage',
            'specialized_equipment': [
                'Tube inspection cameras',
                'Thickness measurement tools',
                'Scale sampling equipment',
                'Radiation monitoring'
            ]
        }
    
    def _primary_chemistry_optimization(self, **kwargs) -> Dict[str, Any]:
        """
        Optimize primary chemistry to reduce scale formation
        
        Adjust boric acid, lithium, and pH to minimize scaling rates.
        """
        target_boric_acid = kwargs.get('target_boric_acid', 1000.0)
        target_lithium = kwargs.get('target_lithium', 2.0)
        target_ph = kwargs.get('target_ph', 7.2)
        
        # Calculate improvement in scale formation rate
        old_rate = max(self.scale_formation_rate, 0.001)  # Prevent division by zero
        
        # Simulate optimized chemistry effects
        boric_acid_improvement = max(0.8, self.boric_acid_concentration / max(target_boric_acid, 1.0))
        lithium_improvement = max(0.9, 2.0 / max(abs(target_lithium - 2.0) + 0.1, 0.1))
        ph_improvement = max(0.9, 1.0 / (1.0 + abs(target_ph - 7.2)))
        
        chemistry_improvement_factor = max(boric_acid_improvement * lithium_improvement * ph_improvement, 0.1)
        new_rate = old_rate / chemistry_improvement_factor
        
        # Update chemistry parameters
        self.boric_acid_concentration = target_boric_acid
        self.lithium_concentration = target_lithium
        self.primary_ph = target_ph
        
        rate_reduction = old_rate - new_rate
        
        return {
            'success': True,
            'duration_hours': 4.0,
            'work_performed': 'Primary chemistry optimization for scale control',
            'findings': f'Reduced scale formation rate by {rate_reduction:.4f} mm/year',
            'chemistry_adjustments': {
                'boric_acid_ppm': target_boric_acid,
                'lithium_ppm': target_lithium,
                'target_ph': target_ph
            },
            'scale_rate_improvement': rate_reduction,
            'effectiveness_score': min(1.0, rate_reduction / old_rate * 10.0),
            'next_maintenance_due': 2190.0,  # Quarterly chemistry review
            'radiation_exposure': 'Low - chemistry control room work',
            'access_required': 'Chemistry control system access',
            'parts_used': [
                'Boric acid solution',
                'Lithium hydroxide solution',
                'Chemistry monitoring equipment'
            ]
        }
    
    def _tube_eddy_current_testing(self, **kwargs) -> Dict[str, Any]:
        """
        Perform eddy current testing of tubes for integrity assessment
        
        Non-destructive testing to assess tube wall thickness and detect
        defects that may be related to scaling or corrosion.
        """
        tube_sample_size = kwargs.get('tube_sample_size', 100)  # Number of tubes tested
        
        # Simulate test results based on current scale condition
        findings = []
        defects_found = 0
        
        # Scale-related findings
        if self.scale_thickness > 0.5:
            scale_affected_tubes = int(tube_sample_size * 0.8)  # 80% of tubes affected
            findings.append(f'Scale deposits detected in {scale_affected_tubes} of {tube_sample_size} tubes tested')
        
        # Simulated defect detection based on operating years and scale
        defect_probability = (self.operating_years / 40.0) * 0.1 + (self.scale_thickness / 2.0) * 0.05
        defects_found = int(tube_sample_size * defect_probability)
        
        if defects_found > 0:
            findings.append(f'Detected {defects_found} tubes with wall thinning or defects')
            recommendations = [
                'Schedule detailed inspection of affected tubes',
                'Consider tube plugging if defects exceed limits',
                'Increase scale cleaning frequency'
            ]
        else:
            findings.append('No significant tube defects detected')
            recommendations = ['Continue normal inspection schedule']
        
        return {
            'success': True,
            'duration_hours': 24.0,
            'work_performed': f'Eddy current testing of {tube_sample_size} tubes',
            'findings': '; '.join(findings),
            'recommendations': recommendations,
            'tubes_tested': tube_sample_size,
            'defects_found': defects_found,
            'scale_affected_tubes': int(tube_sample_size * 0.8) if self.scale_thickness > 0.5 else 0,
            'effectiveness_score': 1.0,  # Testing always successful
            'next_maintenance_due': 8760.0,  # Annual testing
            'radiation_exposure': 'High - primary side tube access',
            'access_required': 'Primary system shutdown and tube access',
            'specialized_equipment': [
                'Eddy current testing equipment',
                'Tube access tools',
                'Data analysis software',
                'Radiation protection equipment'
            ]
        }
    
    def get_state_dict(self) -> Dict[str, float]:
        """
        Get current state as dictionary for logging/monitoring
        Extends base class state with tube interior specific parameters
        
        Returns:
            Dictionary with tube interior fouling state
        """
        # Get base state
        state_dict = super().get_state_dict()
        
        # Add tube interior specific state
        state_dict.update({
            # Scale state
            'tube_scale_thickness_mm': self.scale_thickness,
            'tube_scale_thermal_resistance': self.scale_thermal_resistance,
            'tube_scale_formation_rate_mm_per_year': self.scale_formation_rate,
            
            # Scale composition
            'tube_scale_iron_oxide_mm': self.scale_composition['iron_oxide'],
            'tube_scale_crud_deposits_mm': self.scale_composition['crud_deposits'],
            'tube_scale_corrosion_products_mm': self.scale_composition['corrosion_products'],
            
            # Primary chemistry
            'tube_primary_boric_acid_ppm': self.boric_acid_concentration,
            'tube_primary_lithium_ppm': self.lithium_concentration,
            'tube_primary_ph': self.primary_ph,
            'tube_primary_dissolved_oxygen_ppm': self.dissolved_oxygen_primary,
            
            # Performance impact
            'tube_thermal_efficiency_impact': self.scale_thermal_resistance * 1000.0
        })
        
        return state_dict
    
    def reset(self) -> None:
        """Reset tube interior fouling model to initial conditions"""
        # Reset base class state
        super().reset()
        
        # Reset tube interior specific state
        self.scale_thickness = 0.0
        self.scale_thermal_resistance = 0.0
        self.scale_formation_rate = 0.0
        
        # Reset scale composition
        self.scale_composition = {
            'iron_oxide': 0.0,
            'crud_deposits': 0.0,
            'corrosion_products': 0.0
        }
        
        # Reset primary chemistry to defaults
        self.boric_acid_concentration = 1000.0
        self.lithium_concentration = 2.0
        self.primary_ph = 7.2
        self.dissolved_hydrogen = 25.0
        self.dissolved_oxygen_primary = 0.005


# Example usage and testing
if __name__ == "__main__":
    print("Tube Interior Fouling Model - Test")
    print("=" * 45)
    
    # Create tube interior fouling model
    tube_fouling = TubeInteriorFouling()
    
    print(f"Tube Interior Fouling Model:")
    print(f"  Scale thickness: {tube_fouling.scale_thickness} mm")
    print(f"  Thermal resistance: {tube_fouling.scale_thermal_resistance} m²K/W")
    print(f"  Formation rate: {tube_fouling.scale_formation_rate} mm/year")
    print(f"  Primary pH: {tube_fouling.primary_ph}")
    print(f"  Boric acid: {tube_fouling.boric_acid_concentration} ppm")
    print()
    
    # Test scale formation rate calculation
    print("Scale Formation Rate Test:")
    formation_rate = tube_fouling.calculate_scale_formation_rate(
        temperature=320.0,
        flow_velocity=5.0
    )
    print(f"  Formation rate at 320°C, 5 m/s: {formation_rate:.6f} mm/year")
    
    # Test fouling progression
    print("\nFouling Progression Test:")
    print(f"{'Year':<6} {'Scale (mm)':<12} {'Resistance':<12} {'Rate (mm/yr)':<15}")
    print("-" * 50)
    
    for year in range(0, 21, 5):  # Every 5 years for 20 years
        # Simulate one year of operation
        for _ in range(365):  # Daily updates
            primary_conditions = {
                'temperature': 320.0,
                'flow_velocity': 5.0,
                'chemistry': {
                    'boric_acid_concentration': 1000.0,
                    'lithium_concentration': 2.0,
                    'primary_ph': 7.2,
                    'dissolved_oxygen': 0.005
                }
            }
            
            result = tube_fouling.update_fouling_state(primary_conditions, 24.0)
        
        print(f"{year:<6} {result['scale_thickness_mm']:<12.4f} "
              f"{result['scale_thermal_resistance']:<12.6f} "
              f"{result['scale_formation_rate_mm_per_year']:<15.6f}")
    
    print()
    
    # Test maintenance
    print("Maintenance Test:")
    maintenance_result = tube_fouling.perform_maintenance('primary_scale_cleaning')
    print(f"  Success: {maintenance_result['success']}")
    print(f"  Duration: {maintenance_result['duration_hours']} hours")
    print(f"  Scale removed: {maintenance_result.get('scale_removed_mm', 0):.3f} mm")
    print(f"  Radiation exposure: {maintenance_result.get('radiation_exposure', 'Unknown')}")
    print()
    
    # Test state dictionary
    state_dict = tube_fouling.get_state_dict()
    print("State Dictionary (tube interior parameters):")
    for key, value in state_dict.items():
        if key.startswith('tube_'):
            print(f"  {key}: {value}")
    
    print()
    print("Tube interior fouling model ready for integration!")
