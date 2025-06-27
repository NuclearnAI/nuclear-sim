"""
Threshold analyzer for live simulator analysis.

This module analyzes the current state manager and auto maintenance system
to understand what thresholds are configured and which components can trigger
specific maintenance actions.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import warnings

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from simulator.core.sim import NuclearPlantSimulator


class ThresholdAnalyzer:
    """
    Analyzes live simulator thresholds and component configurations
    
    This class examines the state manager and auto maintenance system
    to understand what maintenance actions can be triggered and by which components.
    """
    
    def __init__(self, simulator: NuclearPlantSimulator):
        """
        Initialize threshold analyzer with a simulator
        
        Args:
            simulator: NuclearPlantSimulator instance with state management enabled
        """
        self.simulator = simulator
        self.state_manager = simulator.state_manager
        self.auto_maintenance = simulator.maintenance_system
        
        if not self.state_manager:
            raise ValueError("Simulator must have state management enabled")
        
        if not self.auto_maintenance:
            warnings.warn("Simulator does not have auto maintenance system - limited analysis available")
        
        # Cache for analysis results
        self._component_cache = None
        self._threshold_cache = None
        self._action_mapping_cache = None
    
    def get_registered_components(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all registered components from the state manager
        
        Returns:
            Dictionary mapping component_id to component information
        """
        if self._component_cache is None:
            self._component_cache = self.state_manager.get_registered_instance_info()
        return self._component_cache
    
    def get_maintenance_thresholds(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all maintenance thresholds from the state manager
        
        Returns:
            Dictionary mapping component_id to threshold configurations
        """
        if self._threshold_cache is None:
            self._threshold_cache = self.state_manager.get_components_with_maintenance_thresholds()
        return self._threshold_cache
    
    def find_components_for_action(self, target_action: str) -> List[str]:
        """
        Find all components that can trigger a specific maintenance action
        
        Args:
            target_action: Maintenance action to search for (e.g., "oil_top_off")
            
        Returns:
            List of component IDs that can trigger this action
        """
        components = []
        thresholds = self.get_maintenance_thresholds()
        
        for component_id, component_thresholds in thresholds.items():
            for param_name, threshold_config in component_thresholds.items():
                if threshold_config.get('action') == target_action:
                    components.append(component_id)
                    break  # Only add component once even if multiple params trigger same action
        
        return list(set(components))  # Remove duplicates
    
    def get_thresholds_for_action(self, target_action: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all thresholds that can trigger a specific maintenance action
        
        Args:
            target_action: Maintenance action to search for
            
        Returns:
            Dictionary mapping component_id to relevant threshold configurations
        """
        action_thresholds = {}
        all_thresholds = self.get_maintenance_thresholds()
        
        for component_id, component_thresholds in all_thresholds.items():
            relevant_thresholds = {}
            for param_name, threshold_config in component_thresholds.items():
                if threshold_config.get('action') == target_action:
                    relevant_thresholds[param_name] = threshold_config
            
            if relevant_thresholds:
                action_thresholds[component_id] = relevant_thresholds
        
        return action_thresholds
    
    def get_component_current_state(self, component_id: str) -> Dict[str, Any]:
        """
        Get current state values for a component
        
        Args:
            component_id: Component ID to analyze
            
        Returns:
            Dictionary of current parameter values
        """
        return self.state_manager.get_component_state_snapshot(component_id)
    
    def analyze_threshold_proximity(self, component_id: str, target_action: str) -> Dict[str, Dict[str, Any]]:
        """
        Analyze how close component parameters are to triggering thresholds
        
        Args:
            component_id: Component ID to analyze
            target_action: Target maintenance action
            
        Returns:
            Dictionary with proximity analysis for each relevant parameter
        """
        # Get current state
        current_state = self.get_component_current_state(component_id)
        
        # Get relevant thresholds
        action_thresholds = self.get_thresholds_for_action(target_action)
        component_thresholds = action_thresholds.get(component_id, {})
        
        proximity_analysis = {}
        
        for param_name, threshold_config in component_thresholds.items():
            current_value = current_state.get(param_name)
            threshold_value = threshold_config.get('threshold')
            comparison = threshold_config.get('comparison', 'greater_than')
            
            if current_value is not None and threshold_value is not None:
                # Calculate proximity metrics
                if comparison == "greater_than":
                    distance_to_threshold = threshold_value - current_value
                    proximity_percent = (current_value / threshold_value) * 100
                elif comparison == "less_than":
                    distance_to_threshold = current_value - threshold_value
                    proximity_percent = (threshold_value / current_value) * 100 if current_value > 0 else 0
                else:
                    distance_to_threshold = abs(current_value - threshold_value)
                    proximity_percent = 100 - (distance_to_threshold / threshold_value) * 100
                
                proximity_analysis[param_name] = {
                    'current_value': current_value,
                    'threshold_value': threshold_value,
                    'comparison': comparison,
                    'distance_to_threshold': distance_to_threshold,
                    'proximity_percent': proximity_percent,
                    'will_trigger': self._will_trigger_threshold(current_value, threshold_config),
                    'action': threshold_config.get('action'),
                    'priority': threshold_config.get('priority', 'MEDIUM')
                }
        
        return proximity_analysis
    
    def _will_trigger_threshold(self, current_value: float, threshold_config: Dict[str, Any]) -> bool:
        """Check if current value will trigger the threshold"""
        threshold = threshold_config.get('threshold')
        comparison = threshold_config.get('comparison', 'greater_than')
        
        if threshold is None:
            return False
        
        if comparison == "greater_than":
            return current_value > threshold
        elif comparison == "less_than":
            return current_value < threshold
        elif comparison == "greater_equal":
            return current_value >= threshold
        elif comparison == "less_equal":
            return current_value <= threshold
        elif comparison == "equals":
            return abs(current_value - threshold) < 0.001
        elif comparison == "not_equals":
            return abs(current_value - threshold) >= 0.001
        
        return False
    
    def get_all_available_actions(self) -> List[str]:
        """
        Get all maintenance actions that can be triggered by current components
        
        Returns:
            List of unique maintenance action names
        """
        actions = set()
        all_thresholds = self.get_maintenance_thresholds()
        
        for component_thresholds in all_thresholds.values():
            for threshold_config in component_thresholds.values():
                action = threshold_config.get('action')
                if action:
                    actions.add(action)
        
        return sorted(list(actions))
    
    def get_action_to_component_mapping(self) -> Dict[str, List[str]]:
        """
        Get mapping of actions to components that can trigger them
        
        Returns:
            Dictionary mapping action names to lists of component IDs
        """
        if self._action_mapping_cache is None:
            mapping = {}
            all_actions = self.get_all_available_actions()
            
            for action in all_actions:
                mapping[action] = self.find_components_for_action(action)
            
            self._action_mapping_cache = mapping
        
        return self._action_mapping_cache
    
    def get_subsystem_for_action(self, target_action: str) -> Optional[str]:
        """
        Determine which subsystem is primarily responsible for an action
        
        Args:
            target_action: Maintenance action to analyze
            
        Returns:
            Subsystem name or None if not determinable
        """
        components = self.find_components_for_action(target_action)
        if not components:
            return None
        
        # Get component metadata to determine subsystem
        registered_components = self.get_registered_components()
        subsystems = set()
        
        for component_id in components:
            component_info = registered_components.get(component_id, {})
            subsystem = component_info.get('subcategory')
            if subsystem:
                subsystems.add(subsystem)
        
        # Return most common subsystem, or first one if tie
        if subsystems:
            return sorted(list(subsystems))[0]
        
        return None
    
    def generate_analysis_report(self, target_action: str = None) -> Dict[str, Any]:
        """
        Generate comprehensive analysis report
        
        Args:
            target_action: Optional specific action to focus on
            
        Returns:
            Comprehensive analysis report
        """
        report = {
            'timestamp': self.state_manager.current_time,
            'total_components': len(self.get_registered_components()),
            'components_with_thresholds': len(self.get_maintenance_thresholds()),
            'available_actions': self.get_all_available_actions(),
            'action_component_mapping': self.get_action_to_component_mapping()
        }
        
        if target_action:
            # Detailed analysis for specific action
            components = self.find_components_for_action(target_action)
            thresholds = self.get_thresholds_for_action(target_action)
            subsystem = self.get_subsystem_for_action(target_action)
            
            report['target_action_analysis'] = {
                'action': target_action,
                'subsystem': subsystem,
                'triggering_components': components,
                'threshold_configurations': thresholds,
                'proximity_analysis': {}
            }
            
            # Analyze proximity for each component
            for component_id in components:
                proximity = self.analyze_threshold_proximity(component_id, target_action)
                report['target_action_analysis']['proximity_analysis'][component_id] = proximity
        
        return report
    
    def clear_cache(self):
        """Clear cached analysis results"""
        self._component_cache = None
        self._threshold_cache = None
        self._action_mapping_cache = None
