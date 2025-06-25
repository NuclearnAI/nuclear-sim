"""
Configuration Composers

This module provides composers that leverage the secondary system's dataclass
configurations to generate comprehensive YAML configurations for test scenarios.
"""

from .comprehensive_composer import (
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
