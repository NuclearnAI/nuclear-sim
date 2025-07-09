"""
SCRAM Logic System

This module implements the reactor SCRAM (emergency shutdown) logic,
including safety parameter monitoring and automatic reactor trip conditions.
"""

from typing import List, Dict, Any


class ScramSystem:
    """
    Reactor SCRAM system for emergency shutdown logic
    """

    def __init__(self):
        """Initialize SCRAM system with safety limits"""
        # Safety limits (adjusted for stable operation)
        self.max_fuel_temp = 1200.0  # °C (PWR fuel temperature limit with margin)
        self.max_coolant_pressure = 17.2  # MPa (slightly higher to prevent nuisance trips)
        self.min_coolant_flow = 5000.0  # kg/s (realistic minimum flow)
        self.max_power_level = 118.0  # % rated power (with some margin)

    def check_safety_systems(self, reactor_state) -> bool:
        """
        Check if safety systems should activate
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            True if SCRAM should activate, False otherwise
        """
        scram_conditions = [
            reactor_state.fuel_temperature > self.max_fuel_temp,
            reactor_state.coolant_pressure > self.max_coolant_pressure,
            reactor_state.coolant_flow_rate < self.min_coolant_flow,
            reactor_state.power_level > self.max_power_level,
        ]

        if any(scram_conditions) and not reactor_state.scram_status:
            # Debug: Print which condition triggered the SCRAM
            if reactor_state.fuel_temperature > self.max_fuel_temp:
                print(
                    f"SCRAM: Fuel temperature {reactor_state.fuel_temperature:.1f}°C > {self.max_fuel_temp}°C"
                )
            if reactor_state.coolant_pressure > self.max_coolant_pressure:
                print(
                    f"SCRAM: Coolant pressure {reactor_state.coolant_pressure:.1f} MPa > {self.max_coolant_pressure} MPa"
                )
            if reactor_state.coolant_flow_rate < self.min_coolant_flow:
                print(
                    f"SCRAM: Coolant flow {reactor_state.coolant_flow_rate:.1f} kg/s < {self.min_coolant_flow} kg/s"
                )
            if reactor_state.power_level > self.max_power_level:
                print(f"SCRAM: Power level {reactor_state.power_level:.1f}% > {self.max_power_level}%")

            reactor_state.scram_status = True
            reactor_state.control_rod_position = 0  # All rods in
            return True
        return False

    def get_safety_margins(self, reactor_state) -> Dict[str, float]:
        """
        Calculate safety margins for all monitored parameters
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            Dictionary with safety margins (positive = safe, negative = exceeded)
        """
        return {
            "fuel_temperature_margin": self.max_fuel_temp - reactor_state.fuel_temperature,
            "coolant_pressure_margin": self.max_coolant_pressure - reactor_state.coolant_pressure,
            "coolant_flow_margin": reactor_state.coolant_flow_rate - self.min_coolant_flow,
            "power_level_margin": self.max_power_level - reactor_state.power_level,
        }

    def get_scram_conditions(self, reactor_state) -> List[Dict[str, Any]]:
        """
        Get detailed information about all SCRAM conditions
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            List of dictionaries with condition details
        """
        conditions = [
            {
                "name": "High Fuel Temperature",
                "current_value": reactor_state.fuel_temperature,
                "limit": self.max_fuel_temp,
                "unit": "°C",
                "exceeded": reactor_state.fuel_temperature > self.max_fuel_temp,
                "margin": self.max_fuel_temp - reactor_state.fuel_temperature,
            },
            {
                "name": "High Coolant Pressure",
                "current_value": reactor_state.coolant_pressure,
                "limit": self.max_coolant_pressure,
                "unit": "MPa",
                "exceeded": reactor_state.coolant_pressure > self.max_coolant_pressure,
                "margin": self.max_coolant_pressure - reactor_state.coolant_pressure,
            },
            {
                "name": "Low Coolant Flow",
                "current_value": reactor_state.coolant_flow_rate,
                "limit": self.min_coolant_flow,
                "unit": "kg/s",
                "exceeded": reactor_state.coolant_flow_rate < self.min_coolant_flow,
                "margin": reactor_state.coolant_flow_rate - self.min_coolant_flow,
            },
            {
                "name": "High Power Level",
                "current_value": reactor_state.power_level,
                "limit": self.max_power_level,
                "unit": "%",
                "exceeded": reactor_state.power_level > self.max_power_level,
                "margin": self.max_power_level - reactor_state.power_level,
            },
        ]
        
        return conditions

    def reset_scram(self, reactor_state) -> None:
        """
        Reset SCRAM status (for manual reset after conditions are cleared)
        
        Args:
            reactor_state: Current reactor state
        """
        reactor_state.scram_status = False

    def is_safe_to_operate(self, reactor_state) -> bool:
        """
        Check if reactor is in safe operating condition
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            True if safe to operate, False otherwise
        """
        margins = self.get_safety_margins(reactor_state)
        return all(margin > 0 for margin in margins.values())

    def get_safety_status_summary(self, reactor_state) -> str:
        """
        Generate a formatted summary of safety system status
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            Formatted string with safety status
        """
        conditions = self.get_scram_conditions(reactor_state)
        
        summary = "Safety System Status:\n"
        summary += "=" * 50 + "\n"
        summary += f"SCRAM Status: {'ACTIVE' if reactor_state.scram_status else 'NORMAL'}\n"
        summary += "-" * 50 + "\n"
        
        for condition in conditions:
            status = "EXCEEDED" if condition["exceeded"] else "NORMAL"
            summary += f"{condition['name']:<20}: {condition['current_value']:>8.1f} {condition['unit']:<4} "
            summary += f"(Limit: {condition['limit']:>6.1f}) [{status}]\n"
        
        return summary
