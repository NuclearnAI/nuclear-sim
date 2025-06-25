#!/usr/bin/env python
"""
Test script for the action-targeted configuration composer

This script demonstrates how to use the new dataclass-based composer
to generate action-targeted test scenarios.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_gen.config_engine.composers.comprehensive_composer import (
    ComprehensiveComposer,
    create_action_test_config,
    save_action_test_config
)


def test_basic_functionality():
    """Test basic composer functionality"""
    print("🧪 Testing Action-Targeted Configuration Composer")
    print("=" * 60)
    
    # Initialize composer
    composer = ComprehensiveComposer()
    
    # List available actions
    print("\n📋 Available Actions by Subsystem:")
    for subsystem in ['steam_generator', 'turbine', 'feedwater', 'condenser']:
        actions = composer.get_actions_by_subsystem(subsystem)
        print(f"\n{subsystem.upper()} ({len(actions)} actions):")
        for action in actions[:5]:  # Show first 5
            print(f"  • {action}")
        if len(actions) > 5:
            print(f"  ... and {len(actions) - 5} more")


def test_steam_generator_scenarios():
    """Test steam generator action scenarios"""
    print("\n🔧 Testing Steam Generator Action Scenarios")
    print("-" * 50)
    
    composer = ComprehensiveComposer()
    
    # Test TSP chemical cleaning scenario
    print("\n1. TSP Chemical Cleaning Test:")
    try:
        config = composer.compose_action_test_scenario(
            target_action="tsp_chemical_cleaning",
            duration_hours=1.5,
            aggressive_mode=True
        )
        
        # Save the configuration
        config_file = composer.save_config(config, "tsp_cleaning_test")
        
        print(f"   ✅ Generated config with {len(config)} sections")
        print(f"   💾 Saved to: {config_file}")
        
        # Show key configuration details
        sg_config = config['steam_generator']
        print(f"   🎯 TSP fouling rate: {sg_config['tsp_fouling']['base_fouling_rate']}")
        print(f"   🎯 TSP threshold: {sg_config['maintenance']['tsp_fouling_threshold']} mm")
        print(f"   🎯 Check interval: {sg_config['maintenance']['individual_sg_check_interval_hours']} hours")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test scale removal scenario
    print("\n2. Scale Removal Test:")
    try:
        config = composer.compose_action_test_scenario(
            target_action="scale_removal",
            duration_hours=1.0,
            aggressive_mode=True
        )
        
        config_file = composer.save_config(config, "scale_removal_test")
        
        print(f"   ✅ Generated config with {len(config)} sections")
        print(f"   💾 Saved to: {config_file}")
        
        # Show key configuration details
        sg_config = config['steam_generator']
        print(f"   🎯 Tube temp threshold: {sg_config['maintenance']['tube_wall_temperature_threshold']} °C")
        print(f"   🎯 Check interval: {sg_config['maintenance']['individual_sg_check_interval_hours']} hours")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_feedwater_scenarios():
    """Test feedwater action scenarios"""
    print("\n🔧 Testing Feedwater Action Scenarios")
    print("-" * 50)
    
    composer = ComprehensiveComposer()
    
    # Test oil top-off scenario
    print("\n1. Oil Top-off Test:")
    try:
        config = composer.compose_action_test_scenario(
            target_action="oil_top_off",
            duration_hours=1.0,
            aggressive_mode=True
        )
        
        config_file = composer.save_config(config, "oil_top_off_test")
        
        print(f"   ✅ Generated config with {len(config)} sections")
        print(f"   💾 Saved to: {config_file}")
        
        # Show maintenance configuration
        maint_config = config['maintenance_system']
        print(f"   🎯 Maintenance mode: {maint_config['maintenance_mode']}")
        print(f"   🎯 Check interval: {maint_config['maintenance_default_check_interval_hours']} hours")
        print(f"   🎯 Threshold multiplier: {maint_config['maintenance_threshold_multiplier']}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_convenience_functions():
    """Test convenience functions"""
    print("\n🔧 Testing Convenience Functions")
    print("-" * 50)
    
    # Test create_action_test_config
    print("\n1. create_action_test_config():")
    try:
        config = create_action_test_config("vibration_analysis", duration_hours=0.5)
        print(f"   ✅ Created config with {len(config)} sections")
        print(f"   🎯 Target action: {config['metadata']['target_action']}")
        print(f"   🎯 Target subsystem: {config['metadata']['target_subsystem']}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test save_action_test_config
    print("\n2. save_action_test_config():")
    try:
        config_file = save_action_test_config("efficiency_analysis", duration_hours=0.5)
        print(f"   ✅ Saved config to: {config_file}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_comprehensive_structure():
    """Test that generated configs match comprehensive structure"""
    print("\n🔧 Testing Comprehensive Structure Compliance")
    print("-" * 50)
    
    composer = ComprehensiveComposer()
    
    try:
        config = composer.compose_action_test_scenario("tsp_chemical_cleaning", duration_hours=1.0)
        
        # Check required top-level sections
        required_sections = [
            'plant_name', 'plant_id', 'simulation_config', 'load_profiles',
            'secondary_system', 'steam_generator', 'turbine', 'feedwater', 
            'condenser', 'maintenance_system', 'water_chemistry', 
            'performance_monitoring', 'environmental', 'metadata'
        ]
        
        print("\n📋 Checking required sections:")
        missing_sections = []
        for section in required_sections:
            if section in config:
                print(f"   ✅ {section}")
            else:
                print(f"   ❌ {section} - MISSING")
                missing_sections.append(section)
        
        if not missing_sections:
            print("\n🎉 All required sections present!")
        else:
            print(f"\n⚠️ Missing {len(missing_sections)} sections: {missing_sections}")
        
        # Check secondary system structure
        print("\n📋 Checking secondary system structure:")
        secondary = config.get('secondary_system', {})
        secondary_sections = ['system_id', 'plant_id', 'steam_generator', 'turbine', 'feedwater', 'condenser']
        for section in secondary_sections:
            if section in secondary:
                print(f"   ✅ secondary_system.{section}")
            else:
                print(f"   ❌ secondary_system.{section} - MISSING")
        
        # Check maintenance system structure
        print("\n📋 Checking maintenance system structure:")
        maintenance = config.get('maintenance_system', {})
        maintenance_sections = ['maintenance_mode', 'maintenance_auto_execute', 'component_configs']
        for section in maintenance_sections:
            if section in maintenance:
                print(f"   ✅ maintenance_system.{section}")
            else:
                print(f"   ❌ maintenance_system.{section} - MISSING")
        
        print(f"\n📊 Total config size: {len(str(config))} characters")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("🚀 Action-Targeted Configuration Composer Test Suite")
    print("=" * 60)
    
    try:
        test_basic_functionality()
        test_steam_generator_scenarios()
        test_feedwater_scenarios()
        test_convenience_functions()
        test_comprehensive_structure()
        
        print("\n🎉 Test Suite Complete!")
        print("\nNext steps:")
        print("1. Use generated configs to run simulations")
        print("2. Check state CSV for parameter threshold crossings")
        print("3. Check work orders CSV for maintenance action execution")
        print("4. Verify component restoration in state CSV")
        
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
