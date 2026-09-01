"""Oracle table comparison package."""
from .models import ComparisonDefinition
from .registry import load_comparison

__all__ = ["ComparisonDefinition", "load_comparison"]
