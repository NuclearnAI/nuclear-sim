"""
Base Test Class

Provides common functionality for all test modules in the nuclear simulator test suite.
"""

import sys
import traceback
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))


class BaseTest(ABC):
    """Base class for all test modules"""
    
    def __init__(self, name: str):
        """
        Initialize base test
        
        Args:
            name: Name of the test module
        """
        self.name = name
        self.tests: List[Tuple[str, Callable]] = []
        self.results: Dict[str, bool] = {}
        self.setup_complete = False
    
    def add_test(self, test_name: str, test_function: Callable) -> None:
        """
        Add a test to the module
        
        Args:
            test_name: Name of the test
            test_function: Function to execute for the test
        """
        self.tests.append((test_name, test_function))
    
    def setup(self) -> bool:
        """
        Setup method called before running tests
        Override in subclasses if needed
        
        Returns:
            True if setup successful, False otherwise
        """
        return True
    
    def teardown(self) -> None:
        """
        Teardown method called after running tests
        Override in subclasses if needed
        """
        pass
    
    def run_test(self, test_name: str, test_function: Callable, verbose: bool = True) -> bool:
        """
        Run a single test
        
        Args:
            test_name: Name of the test
            test_function: Test function to execute
            verbose: If True, print detailed output
            
        Returns:
            True if test passes, False otherwise
        """
        try:
            if verbose:
                print(f"  Running: {test_name}...")
            
            result = test_function()
            
            if result is None:
                result = True  # Assume success if no explicit return
            
            if verbose:
                status = "✅ PASSED" if result else "❌ FAILED"
                print(f"    {status}")
            
            return result
            
        except Exception as e:
            if verbose:
                print(f"    ❌ ERROR: {str(e)}")
                print(f"    {traceback.format_exc()}")
            return False
    
    def run_all_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Run all tests in this module
        
        Args:
            verbose: If True, print detailed output
            
        Returns:
            Dictionary with test results
        """
        if verbose:
            print(f"{self.name} Test Module")
            print("=" * 50)
        
        # Setup
        if not self.setup():
            if verbose:
                print("❌ Setup failed, skipping tests")
            return {
                'total': 0,
                'passed': 0,
                'all_passed': False,
                'individual_results': {}
            }
        
        self.setup_complete = True
        
        # Run tests
        passed_count = 0
        total_count = len(self.tests)
        
        for test_name, test_function in self.tests:
            result = self.run_test(test_name, test_function, verbose)
            self.results[test_name] = result
            if result:
                passed_count += 1
        
        # Teardown
        self.teardown()
        
        all_passed = passed_count == total_count
        
        if verbose:
            print(f"\n{self.name} Results: {passed_count}/{total_count} tests passed")
            if not all_passed:
                print("Failed tests:")
                for test_name, result in self.results.items():
                    if not result:
                        print(f"  - {test_name}")
        
        return {
            'total': total_count,
            'passed': passed_count,
            'all_passed': all_passed,
            'individual_results': self.results.copy()
        }
    
    @abstractmethod
    def define_tests(self) -> None:
        """
        Define all tests for this module
        Must be implemented by subclasses
        """
        pass


class TestAssertions:
    """Helper class for test assertions"""
    
    @staticmethod
    def assert_true(condition: bool, message: str = "") -> None:
        """Assert that condition is True"""
        if not condition:
            raise AssertionError(f"Expected True, got False. {message}")
    
    @staticmethod
    def assert_false(condition: bool, message: str = "") -> None:
        """Assert that condition is False"""
        if condition:
            raise AssertionError(f"Expected False, got True. {message}")
    
    @staticmethod
    def assert_equal(actual: Any, expected: Any, message: str = "") -> None:
        """Assert that actual equals expected"""
        if actual != expected:
            raise AssertionError(f"Expected {expected}, got {actual}. {message}")
    
    @staticmethod
    def assert_not_equal(actual: Any, expected: Any, message: str = "") -> None:
        """Assert that actual does not equal expected"""
        if actual == expected:
            raise AssertionError(f"Expected not {expected}, got {actual}. {message}")
    
    @staticmethod
    def assert_almost_equal(actual: float, expected: float, tolerance: float = 1e-6, message: str = "") -> None:
        """Assert that actual is approximately equal to expected"""
        if abs(actual - expected) > tolerance:
            raise AssertionError(f"Expected {expected} ± {tolerance}, got {actual}. {message}")
    
    @staticmethod
    def assert_greater(actual: float, threshold: float, message: str = "") -> None:
        """Assert that actual is greater than threshold"""
        if actual <= threshold:
            raise AssertionError(f"Expected > {threshold}, got {actual}. {message}")
    
    @staticmethod
    def assert_less(actual: float, threshold: float, message: str = "") -> None:
        """Assert that actual is less than threshold"""
        if actual >= threshold:
            raise AssertionError(f"Expected < {threshold}, got {actual}. {message}")
    
    @staticmethod
    def assert_in_range(actual: float, min_val: float, max_val: float, message: str = "") -> None:
        """Assert that actual is within the specified range"""
        if not (min_val <= actual <= max_val):
            raise AssertionError(f"Expected {actual} to be in range [{min_val}, {max_val}]. {message}")
    
    @staticmethod
    def assert_not_none(value: Any, message: str = "") -> None:
        """Assert that value is not None"""
        if value is None:
            raise AssertionError(f"Expected not None, got None. {message}")
    
    @staticmethod
    def assert_is_none(value: Any, message: str = "") -> None:
        """Assert that value is None"""
        if value is not None:
            raise AssertionError(f"Expected None, got {value}. {message}")
