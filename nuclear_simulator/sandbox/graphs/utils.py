
# Annotation imports
from typing import Any
from functools import lru_cache


# --- Fast attribute access helpers ---

def getattr_fast(obj: Any, attr: str) -> Any:
    """Get attribute from an object, bypassing Pydantic's checks."""
    try:
        # Try to get attribute directly from object's __dict__
        return object.__getattribute__(obj, attr)
    except Exception:
        # Fall back to normal getattr
        return getattr(obj, attr)
    
def setattr_fast(obj: Any, attr: str, value: Any) -> None:
    """Set attribute on an object, bypassing Pydantic's checks."""
    try:
        # Try to set attribute directly on object's __dict__
        object.__setattr__(obj, attr, value)
    except Exception:
        # Fall back to normal setattr
        setattr(obj, attr, value)
    return

def hasattr_fast(obj: Any, attr: str) -> bool:
    """Check if attribute exists on an object, bypassing Pydantic's checks."""
    try:
        # Try to get attribute directly from object's __dict__
        object.__getattribute__(obj, attr)
        return True
    except Exception:
        return False


# --- Nested attribute helpers ---


# Helper to cache split results
@lru_cache(maxsize=1000)
def split_with_memory(text: str, delimiter: str) -> list[str]:
    """Split a string by a delimiter, caching results for performance."""
    return text.split(delimiter)

def getattr_nested(obj: Any, attr_path: str) -> Any:
    """Get nested attribute from an object using dot notation."""
    attrs = split_with_memory(attr_path, '.')
    for attr in attrs:
        obj = getattr_fast(obj, attr)
    return obj

def setattr_nested(obj: Any, attr_path: str, value: Any) -> None:
    """Set nested attribute on an object using dot notation."""
    attrs = split_with_memory(attr_path, '.')
    for attr in attrs[:-1]:
        obj = getattr_fast(obj, attr)
    setattr_fast(obj, attrs[-1], value)
    return

def hasattr_nested(obj: Any, attr_path: str) -> bool:
    """Check if nested attribute exists on an object using dot notation."""
    attrs = split_with_memory(attr_path, '.')
    for attr in attrs:
        if not hasattr_fast(obj, attr):
            return False
        obj = getattr_fast(obj, attr)
    return True

