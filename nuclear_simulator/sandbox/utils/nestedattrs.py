
# Annotation imports
from typing import Any

# Helper functions to handle nested attributes
def getattr_nested(obj: Any, attr_path: str) -> Any:
    """Get nested attribute from an object using dot notation."""
    attrs = attr_path.split('.')
    for attr in attrs:
        obj = getattr(obj, attr)
    return obj

def setattr_nested(obj: Any, attr_path: str, value: Any) -> None:
    """Set nested attribute on an object using dot notation."""
    attrs = attr_path.split('.')
    for attr in attrs[:-1]:
        obj = getattr(obj, attr)
    setattr(obj, attrs[-1], value)
    return

def hasattr_nested(obj: Any, attr_path: str) -> bool:
    """Check if nested attribute exists on an object using dot notation."""
    attrs = attr_path.split('.')
    for attr in attrs:
        if not hasattr(obj, attr):
            return False
        obj = getattr(obj, attr)
    return True

