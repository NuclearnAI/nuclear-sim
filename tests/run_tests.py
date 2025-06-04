#!/usr/bin/env python3
"""
Simple Test Runner

A basic test runner that can be used when the full test suite is not available.
This demonstrates the test framework functionality.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tests.base_test import BaseTest, TestAssertions


class SimpleTests(BaseTest):
    """Simple test class to demonstrate the framework"""
    
    def __init__(self):
        super().__init__("Simple Framework Test")
        self.define_tests()
    
    def define_tests(self) -> None:
        """Define simple tests"""
        self.add_test("Basic Assertions", self.test_assertions)
        self.add_test("Math Operations", self.test_math)
        self.add_test("String Operations", self.test_strings)
    
    def test_assertions(self) -> bool:
        """Test basic assertion functionality"""
        TestAssertions.assert_true(True, "True should be true")
        TestAssertions.assert_false(False, "False should be false")
        TestAssertions.assert_equal(1, 1, "1 should equal 1")
        TestAssertions.assert_not_equal(1, 2, "1 should not equal 2")
        TestAssertions.assert_greater(2, 1, "2 should be greater than 1")
        TestAssertions.assert_less(1, 2, "1 should be less than 2")
        TestAssertions.assert_in_range(5, 1, 10, "5 should be in range 1-10")
        TestAssertions.assert_almost_equal(1.0, 1.001, tolerance=0.01, message="Should be approximately equal")
        return True
    
    def test_math(self) -> bool:
        """Test mathematical operations"""
        result = 2 + 2
        TestAssertions.assert_equal(result, 4, "2 + 2 should equal 4")
        
        result = 10 / 2
        TestAssertions.assert_almost_equal(result, 5.0, tolerance=0.001, message="10 / 2 should equal 5")
        
        result = 3 ** 2
        TestAssertions.assert_equal(result, 9, "3^2 should equal 9")
        
        return True
    
    def test_strings(self) -> bool:
        """Test string operations"""
        text = "Hello, World!"
        TestAssertions.assert_equal(len(text), 13, "String should have correct length")
        TestAssertions.assert_true("Hello" in text, "Should contain 'Hello'")
        TestAssertions.assert_true(text.startswith("Hello"), "Should start with 'Hello'")
        TestAssertions.assert_true(text.endswith("!"), "Should end with '!'")
        
        return True


def main():
    """Run simple tests"""
    print("Nuclear Simulator Test Framework Demo")
    print("=" * 50)
    
    # Create and run simple tests
    simple_tests = SimpleTests()
    results = simple_tests.run_all_tests(verbose=True)
    
    print(f"\nTest Results: {results['passed']}/{results['total']} passed")
    
    if results['all_passed']:
        print("✅ All tests passed! Test framework is working correctly.")
        return True
    else:
        print("❌ Some tests failed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
