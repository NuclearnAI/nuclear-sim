#!/usr/bin/env python3
"""
Comprehensive Test Suite for Nuclear Simulator

This is the main test runner that executes all test modules and provides
a comprehensive assessment of the nuclear simulator functionality.
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import all test modules
from tests.test_control_systems import ControlSystemTests
from tests.test_heat_sources import HeatSourceTests
from tests.test_integration import IntegrationTests
from tests.test_reactivity_model import ReactivityModelTests
from tests.test_reactor_physics import ReactorPhysicsTests
from tests.test_safety_systems import SafetySystemTests
from tests.test_scenarios import ScenarioTests
from tests.test_simulation_core import SimulationCoreTests


class TestSuite:
    """Main test suite coordinator"""
    
    def __init__(self):
        self.test_modules = [
            ("Reactivity Model", ReactivityModelTests),
            ("Reactor Physics", ReactorPhysicsTests),
            ("Heat Sources", HeatSourceTests),
            ("Simulation Core", SimulationCoreTests),
            ("Control Systems", ControlSystemTests),
            ("Safety Systems", SafetySystemTests),
            ("Scenarios", ScenarioTests),
            ("Integration", IntegrationTests),
        ]
        self.results: Dict[str, Dict] = {}
    
    def run_all_tests(self, verbose: bool = True) -> bool:
        """
        Run all test modules
        
        Args:
            verbose: If True, print detailed output
            
        Returns:
            True if all tests pass, False otherwise
        """
        print("Nuclear Simulator Comprehensive Test Suite")
        print("=" * 60)
        print(f"Running {len(self.test_modules)} test modules...")
        print()
        
        start_time = time.time()
        total_tests = 0
        total_passed = 0
        
        for module_name, test_class in self.test_modules:
            if verbose:
                print(f"Running {module_name} Tests...")
                print("-" * 40)
            
            # Initialize and run test module
            test_instance = test_class()
            module_results = test_instance.run_all_tests(verbose=verbose)
            
            # Store results
            self.results[module_name] = module_results
            
            # Update totals
            total_tests += module_results['total']
            total_passed += module_results['passed']
            
            if verbose:
                status = "✅ PASSED" if module_results['all_passed'] else "❌ FAILED"
                print(f"{module_name}: {module_results['passed']}/{module_results['total']} - {status}")
                print()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print summary
        self._print_summary(total_tests, total_passed, duration)
        
        return total_passed == total_tests
    
    def run_specific_module(self, module_name: str, verbose: bool = True) -> bool:
        """
        Run a specific test module
        
        Args:
            module_name: Name of the module to run
            verbose: If True, print detailed output
            
        Returns:
            True if all tests in module pass, False otherwise
        """
        for name, test_class in self.test_modules:
            if name.lower() == module_name.lower():
                print(f"Running {name} Tests Only")
                print("=" * 40)
                
                test_instance = test_class()
                results = test_instance.run_all_tests(verbose=verbose)
                
                status = "✅ PASSED" if results['all_passed'] else "❌ FAILED"
                print(f"\n{name}: {results['passed']}/{results['total']} - {status}")
                
                return results['all_passed']
        
        print(f"Test module '{module_name}' not found!")
        print("Available modules:")
        for name, _ in self.test_modules:
            print(f"  - {name}")
        return False
    
    def _print_summary(self, total_tests: int, total_passed: int, duration: float):
        """Print test summary"""
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        for module_name, results in self.results.items():
            status = "✅ PASSED" if results['all_passed'] else "❌ FAILED"
            print(f"{module_name:<20}: {results['passed']:>3}/{results['total']:<3} - {status}")
        
        print("-" * 60)
        print(f"{'TOTAL':<20}: {total_passed:>3}/{total_tests:<3}")
        print(f"{'SUCCESS RATE':<20}: {(total_passed/total_tests)*100:>6.1f}%")
        print(f"{'DURATION':<20}: {duration:>6.1f}s")
        
        if total_passed == total_tests:
            print("\n🎉 ALL TESTS PASSED! Nuclear simulator is functioning correctly.")
        else:
            failed = total_tests - total_passed
            print(f"\n⚠️  {failed} TEST(S) FAILED. Review failed tests above.")
    
    def get_failed_tests(self) -> List[Tuple[str, List[str]]]:
        """
        Get list of failed tests by module
        
        Returns:
            List of tuples (module_name, failed_test_names)
        """
        failed_tests = []
        for module_name, results in self.results.items():
            if not results['all_passed']:
                failed_in_module = []
                for test_name, passed in results['individual_results'].items():
                    if not passed:
                        failed_in_module.append(test_name)
                failed_tests.append((module_name, failed_in_module))
        return failed_tests


def main():
    """Main entry point for test suite"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nuclear Simulator Test Suite")
    parser.add_argument(
        "--module", 
        type=str, 
        help="Run specific test module only"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true", 
        help="Run tests with minimal output"
    )
    parser.add_argument(
        "--list", 
        action="store_true", 
        help="List available test modules"
    )
    
    args = parser.parse_args()
    
    suite = TestSuite()
    
    if args.list:
        print("Available test modules:")
        for name, _ in suite.test_modules:
            print(f"  - {name}")
        return
    
    verbose = not args.quiet
    
    if args.module:
        success = suite.run_specific_module(args.module, verbose=verbose)
    else:
        success = suite.run_all_tests(verbose=verbose)
    
    # Print failed tests if any
    if not success:
        failed_tests = suite.get_failed_tests()
        if failed_tests:
            print("\nFAILED TESTS DETAIL:")
            print("=" * 40)
            for module_name, failed_list in failed_tests:
                print(f"{module_name}:")
                for test_name in failed_list:
                    print(f"  - {test_name}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
