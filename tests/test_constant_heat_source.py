"""
Simple test for just the constant heat source
"""

import sys

sys.path.append('.')

from primary_system.core.heat_sources.constant_heat_source import ConstantHeatSource


def test_constant_heat_source():
    """Test the constant heat source"""
    print("Testing Constant Heat Source")
    print("=" * 40)
    
    # Create constant heat source
    heat_source = ConstantHeatSource(rated_power_mw=3000.0)
    
    # Test initial state
    print(f"Initial power: {heat_source.get_power_percent():.1f}%")
    print(f"Initial thermal power: {heat_source.get_thermal_power_mw():.1f} MW")
    
    # Test setpoint change
    heat_source.set_power_setpoint(80.0)
    print(f"After setting 80% setpoint: {heat_source.get_power_percent():.1f}%")
    
    # Test update
    result = heat_source.update(dt=1.0)
    print(f"After update: {result['power_percent']:.1f}%")
    print(f"Heat source type: {result['heat_source_type']}")
    print(f"Available: {result['available']}")
    
    print(f"String representation: {heat_source}")
    
    # Test power variation
    heat_source.add_power_variation(5.0)  # Add 5% variation
    print(f"After adding 5% variation: {heat_source.get_power_percent():.1f}%")
    
    # Test efficiency
    print(f"Efficiency: {heat_source.get_efficiency():.1f}")
    
    print("\n✅ Constant heat source test completed successfully!")

if __name__ == "__main__":
    try:
        test_constant_heat_source()
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
