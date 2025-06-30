"""
Maintenance Orchestrator

This module provides generic maintenance orchestration that works with any component type.
It implements hierarchical maintenance action selection to prevent work order overlap
and optimize maintenance efficiency.

Key Features:
1. Component-agnostic orchestration logic
2. Configurable maintenance hierarchies for different component types
3. Intelligent action promotion and coordination
4. Prevention of redundant maintenance activities
5. Integration with existing component maintenance methods

Architecture:
- Components delegate maintenance decisions to the orchestrator
- Orchestrator analyzes violations and selects optimal actions
- Hierarchy configurations define promotion and coordination rules
- Generic logic works with any component type
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging

from .maintenance_actions import MaintenanceActionType
from .work_orders import Priority


class MaintenanceDecisionType(Enum):
    """Types of maintenance decisions the orchestrator can make"""
    EXECUTE_AS_REQUESTED = "execute_as_requested"
    PROMOTE_TO_COMPREHENSIVE = "promote_to_comprehensive"
    COORDINATE_WITH_OTHERS = "coordinate_with_others"
    DEFER_TO_SCHEDULED = "defer_to_scheduled"
    SUPPRESS_REDUNDANT = "suppress_redundant"


@dataclass
class MaintenanceDecision:
    """Result of orchestrator analysis"""
    decision_type: MaintenanceDecisionType
    selected_action: str
    original_action: str
    reasoning: str
    encompassed_actions: List[str]
    estimated_duration: float
    priority_adjustment: int = 0


class MaintenanceOrchestrator:
    """
    Generic maintenance orchestration system
    
    This orchestrator works with any component type by using configurable
    hierarchy rules and generic analysis logic. It prevents work order
    overlap by intelligently selecting optimal maintenance actions.
    """
    
    _instance = None
    
    def __init__(self):
        """Initialize the maintenance orchestrator"""
        self.hierarchy_configs = self._load_component_hierarchies()
        self.logger = logging.getLogger(__name__)
        
        # Statistics tracking
        self.decisions_made = 0
        self.promotions_made = 0
        self.coordinations_made = 0
        self.suppressions_made = 0
    
    @classmethod
    def get_instance(cls) -> 'MaintenanceOrchestrator':
        """Get singleton instance of the orchestrator"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def orchestrate_maintenance(self, component=None, violations: List[Dict] = None, 
                              requested_action: str = None, component_id: str = None,
                              decision_only: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Main orchestration function that works with any component
        
        Args:
            component: Any component with maintenance capabilities (optional)
            violations: List of threshold violations that triggered maintenance
            requested_action: Specific action requested
            component_id: Component ID when component object not available
            decision_only: If True, return decision without executing
            **kwargs: Additional parameters passed to maintenance function
            
        Returns:
            Maintenance result with optimal action selected, or decision dict if decision_only=True
        """
        violations = violations or []
        
        # Get component type for hierarchy lookup
        if component is not None:
            component_type = self._get_component_type(component)
        elif component_id is not None:
            component_type = self._infer_component_type_from_id(component_id)
        else:
            component_type = 'unknown'
        
        # Make maintenance decision
        decision = self._make_maintenance_decision(
            component_type, requested_action, violations
        )
        
        # Update statistics
        self._update_statistics(decision)
        
        # If decision_only mode, return just the decision
        if decision_only:
            return {
                'orchestration_decision': decision.decision_type.value,
                'original_action': decision.original_action,
                'selected_action': decision.selected_action,
                'reasoning': decision.reasoning,
                'encompassed_actions': decision.encompassed_actions
            }
        
        # Execute the decided action
        result = self._execute_maintenance_decision(
            component, decision, violations, **kwargs
        )
        
        # Add orchestration metadata to result
        result.update({
            'orchestration_decision': decision.decision_type.value,
            'original_action': decision.original_action,
            'selected_action': decision.selected_action,
            'reasoning': decision.reasoning,
            'encompassed_actions': decision.encompassed_actions
        })
        
        return result
    
    def _get_component_type(self, component) -> str:
        """Extract component type from component for hierarchy lookup"""
        # Try multiple ways to determine component type
        if hasattr(component, 'component_type'):
            return component.component_type
        elif hasattr(component, 'config') and hasattr(component.config, 'system_type'):
            return component.config.system_type
        elif hasattr(component, '__class__'):
            class_name = component.__class__.__name__.lower()
            # Map common class names to component types
            if 'feedwater' in class_name and 'lubrication' in class_name:
                return 'feedwater_pump'
            elif 'turbine' in class_name and 'lubrication' in class_name:
                return 'turbine_stage'
            elif 'steam_generator' in class_name:
                return 'steam_generator'
            elif 'condenser' in class_name:
                return 'condenser'
            else:
                return class_name
        else:
            return 'unknown'
    
    def _infer_component_type_from_id(self, component_id: str) -> str:
        """Infer component type from component ID when component object not available"""
        component_id_lower = component_id.lower()
        
        if 'fwp' in component_id_lower or 'feedwater' in component_id_lower:
            return 'feedwater_pump'
        elif 'tb' in component_id_lower or 'turbine' in component_id_lower:
            return 'turbine_stage'
        elif 'sg' in component_id_lower or 'steam_generator' in component_id_lower:
            return 'steam_generator'
        elif 'cd' in component_id_lower or 'condenser' in component_id_lower:
            return 'condenser'
        else:
            return 'unknown'
    
    def _make_maintenance_decision(self, component_type: str, requested_action: str, 
                                 violations: List[Dict]) -> MaintenanceDecision:
        """
        Make intelligent maintenance decision based on component type and violations
        """
        self.decisions_made += 1
        
        # Get hierarchy configuration for this component type
        hierarchy = self.hierarchy_configs.get(component_type, {})
        
        # Extract violation actions for analysis
        violation_actions = [v.get('action') for v in violations if v.get('action')]
        
        # If no specific action requested, select from violations
        if not requested_action:
            if violation_actions:
                requested_action = self._select_primary_action(violation_actions)
            else:
                # No action specified and no violations - default maintenance
                return MaintenanceDecision(
                    decision_type=MaintenanceDecisionType.EXECUTE_AS_REQUESTED,
                    selected_action="routine_maintenance",
                    original_action="routine_maintenance",
                    reasoning="No specific action or violations - performing routine maintenance",
                    encompassed_actions=[],
                    estimated_duration=2.0
                )
        
        # Check for comprehensive action promotion
        comprehensive_decision = self._check_comprehensive_promotion(
            hierarchy, requested_action, violation_actions, violations
        )
        if comprehensive_decision:
            return comprehensive_decision
        
        # Check for action coordination
        coordination_decision = self._check_action_coordination(
            hierarchy, requested_action, violation_actions
        )
        if coordination_decision:
            return coordination_decision
        
        # Check for action promotion
        promotion_decision = self._check_action_promotion(
            hierarchy, requested_action, violations
        )
        if promotion_decision:
            return promotion_decision
        
        # No special handling needed - execute as requested
        return MaintenanceDecision(
            decision_type=MaintenanceDecisionType.EXECUTE_AS_REQUESTED,
            selected_action=requested_action,
            original_action=requested_action,
            reasoning="No promotion or coordination needed",
            encompassed_actions=[],
            estimated_duration=self._estimate_action_duration(requested_action)
        )
    
    def _check_comprehensive_promotion(self, hierarchy: Dict, requested_action: str,
                                     violation_actions: List[str], violations: List[Dict]) -> Optional[MaintenanceDecision]:
        """Check if conditions warrant promotion to comprehensive action"""
        comprehensive_actions = hierarchy.get('comprehensive_actions', {})
        
        for comp_action, config in comprehensive_actions.items():
            if self._meets_comprehensive_criteria(config, violation_actions, violations):
                self.promotions_made += 1
                
                encompassed = config.get('encompasses', [])
                return MaintenanceDecision(
                    decision_type=MaintenanceDecisionType.PROMOTE_TO_COMPREHENSIVE,
                    selected_action=comp_action,
                    original_action=requested_action,
                    reasoning=f"Multiple issues detected - promoting to {comp_action}",
                    encompassed_actions=encompassed,
                    estimated_duration=self._estimate_comprehensive_duration(comp_action, encompassed),
                    priority_adjustment=1  # Boost priority for comprehensive actions
                )
        
        return None
    
    def _check_action_coordination(self, hierarchy: Dict, requested_action: str,
                                 violation_actions: List[str]) -> Optional[MaintenanceDecision]:
        """Check if action should be coordinated with others"""
        coordinated_actions = hierarchy.get('coordinated_actions', {})
        
        for base_action, coordinated_with in coordinated_actions.items():
            if requested_action == base_action:
                # Check if any coordinated actions are also triggered
                triggered_coordinated = [action for action in coordinated_with if action in violation_actions]
                
                if triggered_coordinated:
                    self.coordinations_made += 1
                    
                    return MaintenanceDecision(
                        decision_type=MaintenanceDecisionType.COORDINATE_WITH_OTHERS,
                        selected_action=base_action,
                        original_action=requested_action,
                        reasoning=f"Coordinating {base_action} with {triggered_coordinated}",
                        encompassed_actions=triggered_coordinated,
                        estimated_duration=self._estimate_coordinated_duration(base_action, triggered_coordinated)
                    )
        
        return None
    
    def _check_action_promotion(self, hierarchy: Dict, requested_action: str,
                              violations: List[Dict]) -> Optional[MaintenanceDecision]:
        """Check if action should be promoted based on violation severity"""
        promotion_rules = hierarchy.get('promotion_rules', {})
        
        if requested_action in promotion_rules:
            rule = promotion_rules[requested_action]
            promote_to = rule.get('promote_to')
            conditions = rule.get('when', [])
            
            # Check if promotion conditions are met
            if self._check_promotion_conditions(conditions, violations):
                self.promotions_made += 1
                
                return MaintenanceDecision(
                    decision_type=MaintenanceDecisionType.PROMOTE_TO_COMPREHENSIVE,
                    selected_action=promote_to,
                    original_action=requested_action,
                    reasoning=f"Conditions met for promoting {requested_action} to {promote_to}",
                    encompassed_actions=[requested_action],
                    estimated_duration=self._estimate_action_duration(promote_to)
                )
        
        return None
    
    def _meets_comprehensive_criteria(self, config: Dict, violation_actions: List[str], 
                                    violations: List[Dict]) -> bool:
        """Check if comprehensive action criteria are met"""
        trigger_conditions = config.get('trigger_conditions', {})
        encompasses = config.get('encompasses', [])
        
        # Count how many encompassed actions are triggered
        encompassed_count = sum(1 for action in violation_actions if action in encompasses)
        
        # Check multiple major actions threshold
        if 'multiple_major_actions' in trigger_conditions:
            if encompassed_count >= trigger_conditions['multiple_major_actions']:
                return True
        
        # Check total violations threshold
        if 'total_violations' in trigger_conditions:
            if len(violations) >= trigger_conditions['total_violations']:
                return True
        
        # Check specific parameter thresholds
        for param, threshold in trigger_conditions.items():
            if param.endswith('_threshold'):
                param_name = param.replace('_threshold', '')
                for violation in violations:
                    if violation.get('parameter') == param_name:
                        if violation.get('value', 0) > threshold:
                            return True
        
        return False
    
    def _check_promotion_conditions(self, conditions: List[str], violations: List[Dict]) -> bool:
        """Check if promotion conditions are met"""
        for condition in conditions:
            # Parse condition string (e.g., "bearing_wear > 5.0")
            if '>' in condition:
                param, threshold_str = condition.split('>')
                param = param.strip()
                threshold = float(threshold_str.strip())
                
                # Check if any violation meets this condition
                for violation in violations:
                    if violation.get('parameter') == param:
                        if violation.get('value', 0) > threshold:
                            return True
            
            # Add more condition types as needed (e.g., '<', '==', etc.)
        
        return False
    
    def _select_primary_action(self, violation_actions: List[str]) -> str:
        """Select primary action from list of violation actions"""
        if not violation_actions:
            return "routine_maintenance"
        
        # Priority order for action selection
        action_priority = {
            'component_overhaul': 10,
            'bearing_replacement': 9,
            'impeller_replacement': 8,
            'seal_replacement': 7,
            'motor_inspection': 6,
            'oil_change': 5,
            'bearing_inspection': 4,
            'oil_analysis': 3,
            'lubrication_system_check': 2,  # Lower priority than oil_change
            'oil_top_off': 2,
            'routine_maintenance': 1
        }
        
        # Return highest priority action
        return max(violation_actions, key=lambda x: action_priority.get(x, 0))
    
    def _execute_maintenance_decision(self, component, decision: MaintenanceDecision,
                                    violations: List[Dict], **kwargs) -> Dict[str, Any]:
        """Execute the maintenance decision on the component"""
        try:
            # Clean interface: only pass the decided action to the component
            # The orchestrator has already made the decision, component just executes it
            if hasattr(component, 'perform_maintenance'):
                # Call component's maintenance method with decided action only
                result = component.perform_maintenance(
                    maintenance_type=decision.selected_action,
                    **kwargs
                )
            else:
                # Fallback - create basic result
                result = {
                    'success': True,
                    'duration_hours': decision.estimated_duration,
                    'work_performed': f"Performed {decision.selected_action}",
                    'findings': f"Orchestrated maintenance: {decision.reasoning}",
                    'effectiveness_score': 0.9
                }
            
            # Ensure result has required fields
            if not isinstance(result, dict):
                result = {'success': True, 'duration_hours': decision.estimated_duration}
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing maintenance decision: {e}")
            return {
                'success': False,
                'duration_hours': 0.0,
                'work_performed': f"Failed to execute {decision.selected_action}",
                'error_message': str(e),
                'effectiveness_score': 0.0
            }
    
    def _estimate_action_duration(self, action: str) -> float:
        """Estimate duration for maintenance action"""
        duration_estimates = {
            'component_overhaul': 24.0,
            'bearing_replacement': 8.0,
            'impeller_replacement': 8.0,
            'seal_replacement': 6.0,
            'motor_inspection': 4.0,
            'oil_change': 4.0,
            'bearing_inspection': 4.0,
            'oil_analysis': 2.0,
            'oil_top_off': 0.5,
            'routine_maintenance': 2.0
        }
        return duration_estimates.get(action, 2.0)
    
    def _estimate_comprehensive_duration(self, action: str, encompassed: List[str]) -> float:
        """Estimate duration for comprehensive action"""
        base_duration = self._estimate_action_duration(action)
        # Comprehensive actions are more efficient than sum of parts
        encompassed_duration = sum(self._estimate_action_duration(a) for a in encompassed)
        return min(base_duration, encompassed_duration * 0.7)  # 30% efficiency gain
    
    def _estimate_coordinated_duration(self, base_action: str, coordinated: List[str]) -> float:
        """Estimate duration for coordinated actions"""
        base_duration = self._estimate_action_duration(base_action)
        coordinated_duration = sum(self._estimate_action_duration(a) for a in coordinated)
        return base_duration + coordinated_duration * 0.3  # 70% efficiency gain for coordination
    
    def _update_statistics(self, decision: MaintenanceDecision):
        """Update orchestrator statistics"""
        if decision.decision_type == MaintenanceDecisionType.PROMOTE_TO_COMPREHENSIVE:
            self.promotions_made += 1
        elif decision.decision_type == MaintenanceDecisionType.COORDINATE_WITH_OTHERS:
            self.coordinations_made += 1
        elif decision.decision_type == MaintenanceDecisionType.SUPPRESS_REDUNDANT:
            self.suppressions_made += 1
    
    def _load_component_hierarchies(self) -> Dict:
        """Load maintenance hierarchy configurations for different component types"""
        return {
            'feedwater_pump': {
                'comprehensive_actions': {
                    'component_overhaul': {
                        'encompasses': ['bearing_replacement', 'seal_replacement', 'oil_change', 
                                      'motor_inspection', 'impeller_replacement', 'bearing_inspection',
                                      'oil_analysis', 'vibration_analysis'],
                        'trigger_conditions': {
                            'multiple_major_actions': 2,
                            'total_violations': 4,
                            'bearing_wear_threshold': 15.0,
                            'system_health_factor_threshold': 0.75
                        }
                    },
                    'comprehensive_system_inspection': {
                        'encompasses': ['bearing_inspection', 'motor_inspection', 'impeller_inspection',
                                      'vibration_analysis', 'oil_analysis', 'lubrication_inspection'],
                        'trigger_conditions': {
                            'multiple_major_actions': 3,
                            'total_violations': 5
                        }
                    }
                },
                'coordinated_actions': {
                    'bearing_replacement': ['oil_change', 'oil_analysis', 'vibration_analysis'],
                    'impeller_replacement': ['cavitation_analysis', 'npsh_analysis', 'bearing_inspection'],
                    'seal_replacement': ['oil_analysis', 'lubrication_inspection'],
                    'motor_inspection': ['bearing_inspection', 'vibration_analysis']
                },
                'promotion_rules': {
                    'oil_change': {
                        'promote_to': 'bearing_replacement',
                        'when': ['bearing_wear > 5.0', 'motor_temperature > 80.0', 'vibration_increase > 2.0']
                    },
                    'bearing_inspection': {
                        'promote_to': 'bearing_replacement',
                        'when': ['bearing_wear > 10.0', 'vibration_increase > 5.0']
                    },
                    'oil_top_off': {
                        'promote_to': 'oil_change',
                        'when': ['oil_contamination_level > 12.0', 'oil_acidity_number > 1.4']
                    },
                    'lubrication_system_check': {
                        'promote_to': 'oil_change',
                        'when': ['oil_contamination_level > 12.0']  # Simplified - only need oil contamination for promotion
                    },
                    'oil_analysis': {
                        'promote_to': 'oil_change',
                        'when': ['oil_contamination_level > 15.0', 'oil_acidity_number > 1.4']
                    }
                }
            },
            
            'turbine_stage': {
                'comprehensive_actions': {
                    'turbine_overhaul': {
                        'encompasses': ['blade_replacement', 'bearing_replacement', 'rotor_balancing',
                                      'vibration_analysis', 'turbine_oil_change'],
                        'trigger_conditions': {
                            'multiple_major_actions': 2,
                            'vibration_threshold': 10.0,
                            'efficiency_degradation_threshold': 0.15
                        }
                    }
                },
                'coordinated_actions': {
                    'blade_replacement': ['rotor_balancing', 'vibration_analysis', 'performance_test'],
                    'bearing_replacement': ['turbine_oil_change', 'vibration_analysis'],
                    'rotor_balancing': ['vibration_analysis', 'critical_speed_test']
                },
                'promotion_rules': {
                    'turbine_oil_change': {
                        'promote_to': 'bearing_replacement',
                        'when': ['bearing_wear > 8.0', 'vibration_increase > 3.0']
                    }
                }
            },
            
            'steam_generator': {
                'comprehensive_actions': {
                    'tube_bundle_overhaul': {
                        'encompasses': ['tube_cleaning', 'tube_inspection', 'tsp_cleaning',
                                      'eddy_current_testing', 'scale_removal'],
                        'trigger_conditions': {
                            'multiple_major_actions': 2,
                            'fouling_threshold': 20.0,
                            'tube_plugging_percentage_threshold': 5.0
                        }
                    }
                },
                'coordinated_actions': {
                    'tube_cleaning': ['tube_inspection', 'water_chemistry_adjustment'],
                    'tsp_cleaning': ['tube_bundle_inspection', 'eddy_current_testing'],
                    'scale_removal': ['water_chemistry_adjustment', 'tube_inspection']
                },
                'promotion_rules': {
                    'tube_cleaning': {
                        'promote_to': 'tube_bundle_overhaul',
                        'when': ['fouling_factor > 0.3', 'heat_transfer_degradation > 0.2']
                    }
                }
            },
            
            'condenser': {
                'comprehensive_actions': {
                    'condenser_overhaul': {
                        'encompasses': ['condenser_tube_cleaning', 'condenser_tube_inspection',
                                      'vacuum_system_check', 'condenser_performance_test'],
                        'trigger_conditions': {
                            'multiple_major_actions': 2,
                            'vacuum_degradation_threshold': 5.0,
                            'heat_transfer_degradation_threshold': 0.15
                        }
                    }
                },
                'coordinated_actions': {
                    'condenser_tube_cleaning': ['condenser_tube_inspection', 'vacuum_system_check'],
                    'vacuum_ejector_cleaning': ['vacuum_system_test', 'condenser_performance_test']
                }
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            'decisions_made': self.decisions_made,
            'promotions_made': self.promotions_made,
            'coordinations_made': self.coordinations_made,
            'suppressions_made': self.suppressions_made,
            'promotion_rate': self.promotions_made / max(1, self.decisions_made),
            'coordination_rate': self.coordinations_made / max(1, self.decisions_made)
        }
    
    def add_component_hierarchy(self, component_type: str, hierarchy_config: Dict):
        """Add or update hierarchy configuration for a component type"""
        self.hierarchy_configs[component_type] = hierarchy_config
    
    def reset_statistics(self):
        """Reset orchestrator statistics"""
        self.decisions_made = 0
        self.promotions_made = 0
        self.coordinations_made = 0
        self.suppressions_made = 0


# Convenience function for easy access
def get_maintenance_orchestrator() -> MaintenanceOrchestrator:
    """Get the global maintenance orchestrator instance"""
    return MaintenanceOrchestrator.get_instance()
