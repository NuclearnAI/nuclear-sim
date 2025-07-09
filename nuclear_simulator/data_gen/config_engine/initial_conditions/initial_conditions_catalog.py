"""
Initial Conditions Catalog

This module provides a centralized catalog of initial conditions for triggering
specific maintenance actions in nuclear plant simulations.

The catalog uses a simple (subsystem, action) key lookup to provide targeted
initial conditions that will naturally trigger maintenance actions through
system degradation during simulation.
"""

from typing import Dict, Optional, Any, List, Tuple
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import subsystem condition modules
from .feedwater_conditions import FEEDWATER_CONDITIONS
from .turbine_conditions import TURBINE_CONDITIONS
from .steam_generator_conditions import STEAM_GENERATOR_CONDITIONS
from .condenser_conditions import CONDENSER_CONDITIONS
from .generic_conditions import GENERIC_CONDITIONS


class InitialConditionsCatalog:
    """
    Centralized catalog of initial conditions for maintenance action triggering
    
    This catalog provides a simple interface: given a subsystem and action,
    it returns the appropriate initial conditions to set up the simulation
    so that the target maintenance action will be triggered through natural
    system degradation.
    """
    
    def __init__(self):
        """Initialize the catalog with all subsystem conditions"""
        self.conditions: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._load_all_conditions()
        
        print(f"✅ Initial Conditions Catalog Initialized")
        print(f"   📊 Total condition sets: {len(self.conditions)}")
        print(f"   🔧 Subsystems covered: {len(self.get_available_subsystems())}")
    
    def _load_all_conditions(self):
        """Load conditions from all subsystem modules"""
        
        # Load feedwater conditions
        for action, conditions in FEEDWATER_CONDITIONS.items():
            self.conditions[("feedwater", action)] = conditions
        
        # Load turbine conditions
        for action, conditions in TURBINE_CONDITIONS.items():
            self.conditions[("turbine", action)] = conditions
        
        # Load steam generator conditions
        for action, conditions in STEAM_GENERATOR_CONDITIONS.items():
            self.conditions[("steam_generator", action)] = conditions
        
        # Load condenser conditions
        for action, conditions in CONDENSER_CONDITIONS.items():
            self.conditions[("condenser", action)] = conditions
        
        # Load generic conditions (can apply to multiple subsystems)
        for action, conditions in GENERIC_CONDITIONS.items():
            # Generic conditions can be used for any subsystem
            # They will be looked up as fallbacks
            self.conditions[("generic", action)] = conditions
    
    def get_conditions(self, subsystem: str, action: str) -> Optional[Dict[str, Any]]:
        """
        Get initial conditions for a specific subsystem and action
        
        Args:
            subsystem: Target subsystem (e.g., "feedwater", "turbine")
            action: Target maintenance action (e.g., "oil_top_off")
            
        Returns:
            Dictionary of initial conditions, or None if not found
        """
        # First try exact subsystem match
        conditions = self.conditions.get((subsystem, action))
        if conditions:
            return conditions.copy()  # Return a copy to avoid modification
        
        # Fallback to generic conditions
        generic_conditions = self.conditions.get(("generic", action))
        if generic_conditions:
            return generic_conditions.copy()
        
        return None
    
    def has_conditions(self, subsystem: str, action: str) -> bool:
        """Check if conditions exist for a subsystem and action"""
        return (subsystem, action) in self.conditions or ("generic", action) in self.conditions
    
    def get_available_subsystems(self) -> List[str]:
        """Get list of all available subsystems"""
        subsystems = set()
        for subsystem, _ in self.conditions.keys():
            if subsystem != "generic":
                subsystems.add(subsystem)
        return sorted(list(subsystems))
    
    def get_actions_for_subsystem(self, subsystem: str) -> List[str]:
        """Get all available actions for a specific subsystem"""
        actions = []
        for (sub, action) in self.conditions.keys():
            if sub == subsystem:
                actions.append(action)
        return sorted(actions)
    
    def get_all_action_keys(self) -> List[Tuple[str, str]]:
        """Get all (subsystem, action) keys in the catalog"""
        return list(self.conditions.keys())
    
    def validate_conditions(self, subsystem: str, action: str) -> Tuple[bool, List[str]]:
        """
        Validate that conditions exist and are properly formatted
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        conditions = self.get_conditions(subsystem, action)
        if not conditions:
            return False, [f"No conditions found for {subsystem}.{action}"]
        
        issues = []
        
        # Check for required fields
        if 'description' not in conditions:
            issues.append("Missing 'description' field")
        
        # Check that we have actual condition parameters (not just metadata)
        condition_params = {k: v for k, v in conditions.items() 
                          if k not in ['description', 'safety_notes', 'threshold_info']}
        if not condition_params:
            issues.append("No actual condition parameters found")
        
        # Validate parameter values
        for param, value in condition_params.items():
            if value is None:
                issues.append(f"Parameter '{param}' is None")
            elif isinstance(value, list) and len(value) == 0:
                issues.append(f"Parameter '{param}' is empty list")
        
        return len(issues) == 0, issues
    
    def get_coverage_report(self) -> Dict[str, Any]:
        """Generate a coverage report showing which actions have conditions"""
        report = {
            'total_conditions': len(self.conditions),
            'subsystems': {},
            'missing_actions': []
        }
        
        for subsystem in self.get_available_subsystems():
            actions = self.get_actions_for_subsystem(subsystem)
            report['subsystems'][subsystem] = {
                'action_count': len(actions),
                'actions': actions
            }
        
        return report
    
    def print_coverage_summary(self):
        """Print a summary of catalog coverage"""
        report = self.get_coverage_report()
        
        print("\n📊 Initial Conditions Catalog Coverage Summary")
        print("=" * 60)
        print(f"Total condition sets: {report['total_conditions']}")
        print()
        
        for subsystem, info in report['subsystems'].items():
            print(f"{subsystem.title()} Subsystem: {info['action_count']} actions")
            for action in info['actions'][:5]:  # Show first 5
                print(f"  ✅ {action}")
            if info['action_count'] > 5:
                print(f"  ... and {info['action_count'] - 5} more")
            print()


# Global catalog instance
_CATALOG_INSTANCE = None


def get_initial_conditions_catalog() -> InitialConditionsCatalog:
    """Get the global initial conditions catalog instance"""
    global _CATALOG_INSTANCE
    if _CATALOG_INSTANCE is None:
        _CATALOG_INSTANCE = InitialConditionsCatalog()
    return _CATALOG_INSTANCE


# Convenience functions
def get_conditions_for_action(subsystem: str, action: str) -> Optional[Dict[str, Any]]:
    """Convenience function to get conditions for an action"""
    catalog = get_initial_conditions_catalog()
    return catalog.get_conditions(subsystem, action)


def has_conditions_for_action(subsystem: str, action: str) -> bool:
    """Convenience function to check if conditions exist"""
    catalog = get_initial_conditions_catalog()
    return catalog.has_conditions(subsystem, action)
