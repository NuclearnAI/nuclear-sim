"""
Dataclass-Based Configuration Engine

This package provides a type-safe, dataclass-based system for nuclear plant 
configuration generation that creates action-targeted test scenarios with 
reliable maintenance action triggering.

The system leverages the sophisticated dataclass configurations from the 
secondary systems to generate comprehensive YAML configurations that integrate
seamlessly with the nuclear plant simulation system.
"""

from .composers.comprehensive_composer import (
    ComprehensiveComposer,
    create_single_target_config,
    create_focused_config,
    save_single_target_config
)

__all__ = [
    'ComprehensiveComposer',
    'create_single_target_config', 
    'create_focused_config',
    'save_single_target_config'
]
