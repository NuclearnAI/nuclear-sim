#!/usr/bin/env python3
"""
Interactive Constant Heat Source Demo

This script demonstrates the decoupled architecture using a constant heat source.
Perfect for testing secondary side systems without reactor physics complexity.
"""

import sys
import time
from typing import Any, Dict

sys.path.append('.')

from systems.primary.reactor.heat_sources import ConstantHeatSource


class InteractiveSecondarySystem:
    """
    Interactive secondary system for demonstration
    """
    
    def __init__(self):
        """Initialize secondary system"""
        self.steam_demand_percent = 100.0  # % of rated steam flow
        self.turbine_efficiency = 0.33     # Thermal to electrical efficiency
        self.electrical_output_mw = 0.0    # Current electrical output
        
        # Grid demand variations
        self.base_demand = 100.0
        self.demand_variation = 0.0
        
        # Secondary side parameters
        self.steam_pressure = 7.0          # MPa
        self.steam_temperature = 285.0     # °C
        self.feedwater_flow = 1000.0       # kg/s
        
    def set_grid_demand(self, demand_percent: float) -> None:
        """Set grid electrical demand"""
        self.base_demand = demand_percent
        
    def add_demand_variation(self, variation_percent: float) -> None:
        """Add demand variation (weather, frequency, etc.)"""
        self.demand_variation = variation_percent
        
    def get_effective_steam_demand(self) -> float:
        """Get effective steam demand including variations"""
        return self.base_demand + self.demand_variation
        
    def update(self, thermal_power_mw: float) -> Dict[str, Any]:
        """Update secondary system"""
        # Convert thermal power to electrical power
        self.electrical_output_mw = thermal_power_mw * self.turbine_efficiency
        
        # Update steam demand based on electrical demand
        required_thermal = (self.base_demand + self.demand_variation) * 10.0  # MW thermal per % demand
        self.steam_demand_percent = required_thermal / 30.0  # Normalize to percentage
        
        # Simple steam cycle dynamics
        self.steam_pressure = 6.5 + (thermal_power_mw / 3000.0) * 1.0  # Pressure varies with power
        self.steam_temperature = 280.0 + (thermal_power_mw / 3000.0) * 10.0  # Temperature varies with power
        self.feedwater_flow = thermal_power_mw * 0.33  # kg/s
        
        return {
            'electrical_output_mw': self.electrical_output_mw,
            'steam_demand_percent': self.steam_demand_percent,
            'steam_pressure_mpa': self.steam_pressure,
            'steam_temperature_c': self.steam_temperature,
            'feedwater_flow_kg_s': self.feedwater_flow,
            'grid_demand_percent': self.base_demand,
            'demand_variation_percent': self.demand_variation,
            'turbine_efficiency': self.turbine_efficiency
        }


class InteractiveConstantHeatDemo:
    """
    Interactive demonstration of constant heat source with secondary system
    """
    
    def __init__(self):
        """Initialize the demo"""
        self.heat_source = ConstantHeatSource(rated_power_mw=3000.0)
        self.secondary_system = InteractiveSecondarySystem()
        self.time = 0.0
        self.running = True
        
        # Control modes
        self.auto_follow_demand = False
        self.target_power_percent = 100.0
        
    def display_status(self) -> None:
        """Display current plant status"""
        # Get current data
        heat_result = self.heat_source.update(dt=1.0)
        secondary_result = self.secondary_system.update(heat_result['thermal_power_mw'])
        
        # Clear screen (works on most terminals)
        print("\033[2J\033[H")
        
        print("🔧 INTERACTIVE CONSTANT HEAT SOURCE DEMO")
        print("=" * 60)
        print(f"Time: {self.time:.0f} seconds")
        print()
        
        # Heat Source Status
        print("🔥 HEAT SOURCE (Primary Side)")
        print("-" * 30)
        print(f"  Type: {heat_result['heat_source_type'].title()}")
        print(f"  Thermal Power: {heat_result['thermal_power_mw']:.1f} MW")
        print(f"  Power Level: {heat_result['power_percent']:.1f}%")
        print(f"  Setpoint: {heat_result['setpoint_percent']:.1f}%")
        print(f"  Available: {'✅ Yes' if heat_result['available'] else '❌ No'}")
        print()
        
        # Secondary System Status
        print("⚡ SECONDARY SYSTEM (Steam Side)")
        print("-" * 30)
        print(f"  Electrical Output: {secondary_result['electrical_output_mw']:.1f} MW")
        print(f"  Steam Pressure: {secondary_result['steam_pressure_mpa']:.1f} MPa")
        print(f"  Steam Temperature: {secondary_result['steam_temperature_c']:.1f} °C")
        print(f"  Feedwater Flow: {secondary_result['feedwater_flow_kg_s']:.1f} kg/s")
        print(f"  Turbine Efficiency: {secondary_result['turbine_efficiency']:.1%}")
        print()
        
        # Grid Interface
        print("🏭 GRID INTERFACE")
        print("-" * 30)
        print(f"  Grid Demand: {secondary_result['grid_demand_percent']:.1f}%")
        print(f"  Demand Variation: {secondary_result['demand_variation_percent']:+.1f}%")
        print(f"  Effective Demand: {secondary_result['grid_demand_percent'] + secondary_result['demand_variation_percent']:.1f}%")
        print()
        
        # Control Status
        print("🎛️  CONTROL STATUS")
        print("-" * 30)
        print(f"  Auto Follow Demand: {'🟢 ON' if self.auto_follow_demand else '🔴 OFF'}")
        print(f"  Target Power: {self.target_power_percent:.1f}%")
        print()
        
        # Performance Metrics
        demand_error = abs((secondary_result['grid_demand_percent'] + secondary_result['demand_variation_percent']) - heat_result['power_percent'])
        print("📊 PERFORMANCE")
        print("-" * 30)
        print(f"  Demand Following Error: {demand_error:.1f}%")
        print(f"  Heat Source Response: Instant (Constant Source)")
        print(f"  System Efficiency: {secondary_result['turbine_efficiency']:.1%}")
        print()
        
    def display_help(self) -> None:
        """Display available commands"""
        print("\n" + "="*60)
        print("🎮 AVAILABLE COMMANDS")
        print("="*60)
        print("Power Control:")
        print("  p <number>     - Set heat source power (e.g., 'p 95' for 95%)")
        print("  +              - Increase power by 5%")
        print("  -              - Decrease power by 5%")
        print()
        print("Grid Demand Simulation:")
        print("  d <number>     - Set grid demand (e.g., 'd 80' for 80%)")
        print("  v <number>     - Add demand variation (e.g., 'v 3' for +3%)")
        print("  spike          - Simulate demand spike (+10% for 30 seconds)")
        print("  drop           - Simulate demand drop (-8% for 20 seconds)")
        print()
        print("Control Modes:")
        print("  auto           - Toggle auto demand following")
        print("  manual         - Manual power control mode")
        print("  maintain       - Maintain current power level")
        print()
        print("Scenarios:")
        print("  weather        - Simulate weather-driven demand changes")
        print("  frequency      - Simulate grid frequency variations")
        print("  peak           - Simulate peak demand period")
        print()
        print("System:")
        print("  status         - Refresh status display")
        print("  help           - Show this help")
        print("  quit           - Exit demo")
        print("="*60)
        
    def handle_command(self, command: str) -> None:
        """Handle user commands"""
        parts = command.strip().lower().split()
        if not parts:
            return
            
        cmd = parts[0]
        
        try:
            if cmd == 'p' and len(parts) > 1:
                # Set power
                power = float(parts[1])
                self.heat_source.set_power_setpoint(power)
                self.target_power_percent = power
                print(f"🔥 Heat source power set to {power:.1f}%")
                
            elif cmd == '+':
                # Increase power
                current = self.heat_source.get_power_percent()
                new_power = min(150.0, current + 5.0)
                self.heat_source.set_power_setpoint(new_power)
                self.target_power_percent = new_power
                print(f"🔥 Power increased to {new_power:.1f}%")
                
            elif cmd == '-':
                # Decrease power
                current = self.heat_source.get_power_percent()
                new_power = max(0.0, current - 5.0)
                self.heat_source.set_power_setpoint(new_power)
                self.target_power_percent = new_power
                print(f"🔥 Power decreased to {new_power:.1f}%")
                
            elif cmd == 'd' and len(parts) > 1:
                # Set grid demand
                demand = float(parts[1])
                self.secondary_system.set_grid_demand(demand)
                print(f"🏭 Grid demand set to {demand:.1f}%")
                
            elif cmd == 'v' and len(parts) > 1:
                # Add demand variation
                variation = float(parts[1])
                self.secondary_system.add_demand_variation(variation)
                print(f"🏭 Demand variation set to {variation:+.1f}%")
                
            elif cmd == 'spike':
                # Demand spike
                self.secondary_system.add_demand_variation(10.0)
                print("🏭 Simulating demand spike (+10%)")
                
            elif cmd == 'drop':
                # Demand drop
                self.secondary_system.add_demand_variation(-8.0)
                print("🏭 Simulating demand drop (-8%)")
                
            elif cmd == 'auto':
                # Toggle auto mode
                self.auto_follow_demand = not self.auto_follow_demand
                status = "enabled" if self.auto_follow_demand else "disabled"
                print(f"🎛️  Auto demand following {status}")
                
            elif cmd == 'manual':
                # Manual mode
                self.auto_follow_demand = False
                print("🎛️  Manual control mode enabled")
                
            elif cmd == 'maintain':
                # Maintain current power
                current = self.heat_source.get_power_percent()
                self.target_power_percent = current
                self.auto_follow_demand = False
                print(f"🎛️  Maintaining power at {current:.1f}%")
                
            elif cmd == 'weather':
                # Weather scenario
                print("🌤️  Simulating weather-driven demand changes...")
                self.run_weather_scenario()
                
            elif cmd == 'frequency':
                # Frequency scenario
                print("⚡ Simulating grid frequency variations...")
                self.run_frequency_scenario()
                
            elif cmd == 'peak':
                # Peak demand scenario
                print("📈 Simulating peak demand period...")
                self.run_peak_demand_scenario()
                
            elif cmd == 'status':
                # Refresh status
                pass  # Status will be displayed in main loop
                
            elif cmd == 'help':
                # Show help
                self.display_help()
                input("\nPress ENTER to continue...")
                
            elif cmd in ['quit', 'exit', 'q']:
                # Quit
                self.running = False
                print("👋 Exiting demo...")
                
            else:
                print(f"❓ Unknown command: {command}")
                print("Type 'help' for available commands")
                
        except ValueError:
            print(f"❌ Invalid number in command: {command}")
        except Exception as e:
            print(f"❌ Error executing command: {e}")
    
    def update_auto_control(self) -> None:
        """Update automatic control if enabled"""
        if self.auto_follow_demand:
            # Get current grid demand
            effective_demand = self.secondary_system.get_effective_steam_demand()
            
            # Set heat source to follow demand
            self.heat_source.set_power_setpoint(effective_demand)
            self.target_power_percent = effective_demand
    
    def run_weather_scenario(self) -> None:
        """Run weather-driven demand scenario"""
        print("Running 60-second weather scenario...")
        original_auto = self.auto_follow_demand
        self.auto_follow_demand = True
        
        for i in range(60):
            # Simulate temperature-driven demand changes
            # Hot day: increased AC load
            temp_factor = 2.0 * (1.0 + 0.5 * (i / 60.0))  # Gradual increase
            self.secondary_system.add_demand_variation(temp_factor)
            
            self.update_auto_control()
            self.time += 1
            
            if i % 10 == 0:
                self.display_status()
                print(f"Weather effect: +{temp_factor:.1f}% demand (hot day)")
                time.sleep(1)
        
        # Return to normal
        self.secondary_system.add_demand_variation(0.0)
        self.auto_follow_demand = original_auto
        print("Weather scenario completed")
    
    def run_frequency_scenario(self) -> None:
        """Run grid frequency variation scenario"""
        print("Running 45-second frequency scenario...")
        original_auto = self.auto_follow_demand
        self.auto_follow_demand = True
        
        import math
        
        for i in range(45):
            # Simulate frequency variations (±1% around nominal)
            freq_variation = 1.0 * math.sin(i * 0.2)  # Oscillating demand
            self.secondary_system.add_demand_variation(freq_variation)
            
            self.update_auto_control()
            self.time += 1
            
            if i % 8 == 0:
                self.display_status()
                print(f"Frequency effect: {freq_variation:+.1f}% demand")
                time.sleep(0.8)
        
        # Return to normal
        self.secondary_system.add_demand_variation(0.0)
        self.auto_follow_demand = original_auto
        print("Frequency scenario completed")
    
    def run_peak_demand_scenario(self) -> None:
        """Run peak demand period scenario"""
        print("Running 90-second peak demand scenario...")
        original_auto = self.auto_follow_demand
        self.auto_follow_demand = True
        
        # Ramp up to peak
        for i in range(30):
            peak_factor = (i / 30.0) * 15.0  # Ramp to +15%
            self.secondary_system.add_demand_variation(peak_factor)
            self.update_auto_control()
            self.time += 1
            
            if i % 10 == 0:
                self.display_status()
                print(f"Peak ramp: +{peak_factor:.1f}% demand")
                time.sleep(0.5)
        
        # Hold at peak
        for i in range(30):
            self.secondary_system.add_demand_variation(15.0)
            self.update_auto_control()
            self.time += 1
            
            if i % 10 == 0:
                self.display_status()
                print("Peak demand period: +15.0% demand")
                time.sleep(0.5)
        
        # Ramp down
        for i in range(30):
            peak_factor = 15.0 * (1.0 - i / 30.0)  # Ramp down
            self.secondary_system.add_demand_variation(peak_factor)
            self.update_auto_control()
            self.time += 1
            
            if i % 10 == 0:
                self.display_status()
                print(f"Peak ramp down: +{peak_factor:.1f}% demand")
                time.sleep(0.5)
        
        # Return to normal
        self.secondary_system.add_demand_variation(0.0)
        self.auto_follow_demand = original_auto
        print("Peak demand scenario completed")
    
    def run(self) -> None:
        """Run the interactive demo"""
        print("🔧 INTERACTIVE CONSTANT HEAT SOURCE DEMO")
        print("=" * 60)
        print("This demo shows the decoupled architecture using a constant heat source.")
        print("Perfect for testing secondary side systems without reactor complexity!")
        print()
        print("Key Features:")
        print("  ✅ Instant heat source response (no reactor physics)")
        print("  ✅ Independent power control")
        print("  ✅ Grid demand simulation")
        print("  ✅ Automatic demand following")
        print("  ✅ Realistic secondary side dynamics")
        print()
        print("Type 'help' for commands or just press ENTER to start...")
        input()
        
        while self.running:
            # Update automatic control
            self.update_auto_control()
            
            # Display current status
            self.display_status()
            
            # Get user command
            try:
                print("Command (or ENTER for next step): ", end="", flush=True)
                command = input().strip()
                
                if command:
                    self.handle_command(command)
                else:
                    # Just advance time
                    self.time += 1
                    
            except KeyboardInterrupt:
                print("\n👋 Demo interrupted by user")
                break
            except EOFError:
                print("\n👋 Demo ended")
                break
        
        print("\n🎯 DEMO SUMMARY")
        print("=" * 40)
        print(f"Total simulation time: {self.time:.0f} seconds")
        print(f"Final heat source power: {self.heat_source.get_power_percent():.1f}%")
        print(f"Final electrical output: {self.secondary_system.electrical_output_mw:.1f} MW")
        print()
        print("✅ Constant heat source benefits demonstrated:")
        print("  • Instant response to power commands")
        print("  • Perfect for testing secondary systems")
        print("  • Easy operator control")
        print("  • Predictable behavior for development")
        print()
        print("🚀 Next steps: Try the reactor heat source for realistic physics!")


def main():
    """Main function"""
    demo = InteractiveConstantHeatDemo()
    demo.run()


if __name__ == "__main__":
    main()
