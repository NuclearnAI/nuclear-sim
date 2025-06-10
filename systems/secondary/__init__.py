"""
Secondary Reactor Physics System

This module provides the integrated secondary reactor physics system for PWR plants,
combining steam generators, turbines, and condensers into a complete steam cycle model.
"""

from .steam_generator import SteamGeneratorPhysics, SteamGeneratorConfig
from .turbine import TurbinePhysics, TurbineConfig
from .condenser import CondenserPhysics, CondenserConfig

__all__ = [
    'SteamGeneratorPhysics',
    'SteamGeneratorConfig', 
    'TurbinePhysics',
    'TurbineConfig',
    'CondenserPhysics',
    'CondenserConfig',
    'SecondaryReactorPhysics'
]


class SecondaryReactorPhysics:
    """
    Integrated secondary reactor physics system
    
    This class combines steam generators, turbines, and condensers to model
    the complete secondary side of a PWR nuclear power plant.
    
    The system models:
    1. Heat transfer from primary to secondary in steam generators
    2. Steam expansion and power generation in turbines
    3. Steam condensation and heat rejection in condensers
    4. Complete mass and energy balance across the steam cycle
    5. Control system interactions and feedback loops
    """
    
    def __init__(self, 
                 num_steam_generators: int = 3,
                 sg_config: SteamGeneratorConfig = None,
                 turbine_config: TurbineConfig = None,
                 condenser_config: CondenserConfig = None):
        """
        Initialize integrated secondary reactor physics
        
        Args:
            num_steam_generators: Number of steam generators (typically 2-4)
            sg_config: Steam generator configuration
            turbine_config: Turbine configuration  
            condenser_config: Condenser configuration
        """
        self.num_steam_generators = num_steam_generators
        
        # Initialize component physics models
        self.steam_generators = []
        for i in range(num_steam_generators):
            sg = SteamGeneratorPhysics(sg_config)
            self.steam_generators.append(sg)
        
        self.turbine = TurbinePhysics(turbine_config)
        self.condenser = CondenserPhysics(condenser_config)
        
        # System state variables
        self.total_steam_flow = 0.0
        self.total_heat_transfer = 0.0
        self.electrical_power_output = 0.0
        self.thermal_efficiency = 0.0
        
        # Control parameters
        self.load_demand = 100.0  # % rated load
        self.feedwater_temperature = 227.0  # °C
        self.cooling_water_temperature = 25.0  # °C
        
    def update_system(self,
                     primary_conditions: dict,
                     control_inputs: dict,
                     dt: float) -> dict:
        """
        Update the complete secondary system for one time step
        
        Args:
            primary_conditions: Dictionary with primary side conditions for each SG
                - 'sg_X_inlet_temp': Primary inlet temperature for SG X (°C)
                - 'sg_X_outlet_temp': Primary outlet temperature for SG X (°C)
                - 'sg_X_flow': Primary flow rate for SG X (kg/s)
            control_inputs: Dictionary with control system inputs
                - 'load_demand': Electrical load demand (% rated)
                - 'feedwater_temp': Feedwater temperature (°C)
                - 'cooling_water_temp': Cooling water inlet temperature (°C)
                - 'cooling_water_flow': Cooling water flow rate (kg/s)
                - 'vacuum_pump_operation': Vacuum pump operation (0-1)
            dt: Time step (s)
            
        Returns:
            Dictionary with complete system state and performance
        """
        # Extract control inputs
        self.load_demand = control_inputs.get('load_demand', 100.0)
        self.feedwater_temperature = control_inputs.get('feedwater_temp', 227.0)
        self.cooling_water_temperature = control_inputs.get('cooling_water_temp', 25.0)
        cooling_water_flow = control_inputs.get('cooling_water_flow', 45000.0)
        vacuum_pump_operation = control_inputs.get('vacuum_pump_operation', 1.0)
        
        # Update steam generators
        sg_results = []
        total_steam_production = 0.0
        total_heat_transfer = 0.0
        
        for i, sg in enumerate(self.steam_generators):
            # Get primary conditions for this steam generator
            sg_key = f'sg_{i+1}'
            primary_inlet_temp = primary_conditions.get(f'{sg_key}_inlet_temp', 327.0)
            primary_outlet_temp = primary_conditions.get(f'{sg_key}_outlet_temp', 293.0)
            primary_flow = primary_conditions.get(f'{sg_key}_flow', 5700.0)
            
            # Calculate steam flow based on load demand and steam generator capacity
            design_steam_flow = sg.config.secondary_design_flow
            steam_flow_demand = design_steam_flow * (self.load_demand / 100.0)
            
            # Update steam generator
            sg_result = sg.update_state(
                primary_temp_in=primary_inlet_temp,
                primary_temp_out=primary_outlet_temp,
                primary_flow=primary_flow,
                steam_flow_out=steam_flow_demand,
                feedwater_flow_in=steam_flow_demand,  # Mass balance
                feedwater_temp=self.feedwater_temperature,
                dt=dt
            )
            
            sg_results.append(sg_result)
            total_steam_production += sg_result['steam_production_rate']
            total_heat_transfer += sg_result['heat_transfer_rate']
        
        # Calculate average steam conditions entering turbine
        if len(sg_results) > 0:
            avg_steam_pressure = sum(sg.secondary_pressure for sg in self.steam_generators) / len(self.steam_generators)
            avg_steam_temperature = sum(sg.secondary_temperature for sg in self.steam_generators) / len(self.steam_generators)
            avg_steam_quality = sum(sg.steam_quality for sg in self.steam_generators) / len(self.steam_generators)
        else:
            avg_steam_pressure = 6.895
            avg_steam_temperature = 285.8
            avg_steam_quality = 0.99
        
        # Total steam flow to turbine
        total_steam_flow = sum(sg_result['steam_flow_rate'] for sg_result in sg_results)
        
        # Update turbine
        turbine_result = self.turbine.update_state(
            steam_pressure=avg_steam_pressure,
            steam_temperature=avg_steam_temperature,
            steam_flow=total_steam_flow,
            steam_quality=avg_steam_quality,
            load_demand=self.load_demand,
            dt=dt
        )
        
        # Update condenser with turbine exhaust
        # Use the saturation temperature at condenser pressure for steam inlet temperature
        condenser_steam_temp = 39.0  # Saturation temperature at 0.007 MPa
        
        condenser_result = self.condenser.update_state(
            steam_pressure=turbine_result['condenser_pressure'],
            steam_temperature=condenser_steam_temp,
            steam_flow=turbine_result['effective_steam_flow'],
            steam_quality=0.90,  # Typical LP turbine exhaust quality
            cooling_water_flow=cooling_water_flow,
            cooling_water_temp_in=self.cooling_water_temperature,
            vacuum_pump_operation=vacuum_pump_operation,
            dt=dt
        )
        
        # Calculate system performance metrics
        self.total_steam_flow = total_steam_flow
        self.total_heat_transfer = total_heat_transfer
        self.electrical_power_output = turbine_result['electrical_power_net']
        
        # Overall thermal efficiency (electrical output / heat input)
        if total_heat_transfer > 0:
            self.thermal_efficiency = (self.electrical_power_output * 1e6) / total_heat_transfer
        else:
            self.thermal_efficiency = 0.0
        
        # Heat rate (kJ/kWh)
        if self.electrical_power_output > 0:
            heat_rate = (total_heat_transfer / 1000.0) / (self.electrical_power_output * 1000.0) * 3600.0
        else:
            heat_rate = 0.0
        
        # Compile complete system results
        system_result = {
            # Overall system performance
            'electrical_power_mw': self.electrical_power_output,
            'thermal_efficiency': self.thermal_efficiency,
            'heat_rate_kj_kwh': heat_rate,
            'total_steam_flow': self.total_steam_flow,
            'total_heat_transfer': self.total_heat_transfer,
            
            # Steam generator performance
            'sg_avg_pressure': avg_steam_pressure,
            'sg_avg_temperature': avg_steam_temperature,
            'sg_avg_steam_quality': avg_steam_quality,
            'sg_total_heat_transfer': total_heat_transfer,
            'sg_individual_results': sg_results,
            
            # Turbine performance
            'turbine_mechanical_power': turbine_result['mechanical_power'],
            'turbine_electrical_power_gross': turbine_result['electrical_power_gross'],
            'turbine_electrical_power_net': turbine_result['electrical_power_net'],
            'turbine_efficiency': turbine_result['overall_efficiency'],
            'turbine_steam_rate': turbine_result['steam_rate'],
            'turbine_hp_power': turbine_result['hp_power'],
            'turbine_lp_power': turbine_result['lp_power'],
            
            # Condenser performance
            'condenser_heat_rejection': condenser_result['heat_rejection_rate'],
            'condenser_pressure': condenser_result['condenser_pressure'],
            'condenser_cooling_water_temp_rise': condenser_result['cooling_water_temp_rise'],
            'condenser_thermal_performance': condenser_result['thermal_performance'],
            'condenser_vacuum_efficiency': condenser_result['vacuum_pump_efficiency'],
            
            # Control and operating conditions
            'load_demand': self.load_demand,
            'feedwater_temperature': self.feedwater_temperature,
            'cooling_water_inlet_temp': self.cooling_water_temperature,
            'cooling_water_outlet_temp': condenser_result['cooling_water_outlet_temp'],
            
            # Detailed component states
            'steam_generator_states': [sg.get_state_dict() for sg in self.steam_generators],
            'turbine_state': self.turbine.get_state_dict(),
            'condenser_state': self.condenser.get_state_dict()
        }
        
        return system_result
    
    def get_system_state(self) -> dict:
        """Get complete system state for monitoring and logging"""
        return {
            'num_steam_generators': self.num_steam_generators,
            'total_steam_flow': self.total_steam_flow,
            'total_heat_transfer': self.total_heat_transfer,
            'electrical_power_output': self.electrical_power_output,
            'thermal_efficiency': self.thermal_efficiency,
            'load_demand': self.load_demand,
            'feedwater_temperature': self.feedwater_temperature,
            'cooling_water_temperature': self.cooling_water_temperature,
            'steam_generator_states': [sg.get_state_dict() for sg in self.steam_generators],
            'turbine_state': self.turbine.get_state_dict(),
            'condenser_state': self.condenser.get_state_dict()
        }
    
    def reset_system(self) -> None:
        """Reset all components to initial steady-state conditions"""
        for sg in self.steam_generators:
            sg.reset()
        self.turbine.reset()
        self.condenser.reset()
        
        self.total_steam_flow = 0.0
        self.total_heat_transfer = 0.0
        self.electrical_power_output = 0.0
        self.thermal_efficiency = 0.0
        self.load_demand = 100.0
        self.feedwater_temperature = 227.0
        self.cooling_water_temperature = 25.0
    


# Example usage and testing
if __name__ == "__main__":
    print("Secondary Reactor Physics System - Integration Test")
    print("=" * 60)
    
    # Create integrated secondary system
    secondary_system = SecondaryReactorPhysics(num_steam_generators=3)
    
    print(f"Initialized system with {secondary_system.num_steam_generators} steam generators")
    print()
    
    
    # Test transient operation
    print("Transient Operation Test (Load Change):")
    
    # Primary conditions (typical PWR)
    primary_conditions = {
        'sg_1_inlet_temp': 327.0,
        'sg_1_outlet_temp': 293.0,
        'sg_1_flow': 5700.0,
        'sg_2_inlet_temp': 327.0,
        'sg_2_outlet_temp': 293.0,
        'sg_2_flow': 5700.0,
        'sg_3_inlet_temp': 327.0,
        'sg_3_outlet_temp': 293.0,
        'sg_3_flow': 5700.0
    }
    
    # Test load reduction
    for load in [100.0, 75.0, 50.0]:
        control_inputs = {
            'load_demand': load,
            'feedwater_temp': 227.0,
            'cooling_water_temp': 25.0,
            'cooling_water_flow': 45000.0,
            'vacuum_pump_operation': 1.0
        }
        
        result = secondary_system.update_system(
            primary_conditions=primary_conditions,
            control_inputs=control_inputs,
            dt=1.0
        )
        
        print(f"  Load {load:5.1f}%: Power {result['electrical_power_mw']:6.1f} MW, "
              f"Efficiency {result['thermal_efficiency']*100:5.2f}%, "
              f"Steam Flow {result['total_steam_flow']:6.0f} kg/s")
    
    print()
    print("Secondary reactor physics implementation complete!")
    print("Components: Steam Generators, Turbine, Condenser")
    print("Features: Heat transfer, power generation, vacuum systems, control dynamics")
