"""
Utility modules for neuView.

This package contains utility functions and formatters that were extracted
from the main PageGenerator class to improve code organization and reusability.
"""

from .atomic_write import atomic_write
from .formatters import (
    NumberFormatter,
    PercentageFormatter,
    SynapseFormatter,
    NeurotransmitterFormatter,
    MathematicalFormatter,
)
from .html_utils import HTMLUtils
from .text_utils import TextUtils
from .version_utils import get_git_version, get_git_describe, get_version_info
from .project_paths import (
    get_project_root,
    get_templates_dir,
    get_static_dir,
    get_input_dir,
    get_src_dir,
)


__all__ = [
    "NumberFormatter",
    "PercentageFormatter",
    "SynapseFormatter",
    "NeurotransmitterFormatter",
    "MathematicalFormatter",
    "HTMLUtils",
    "TextUtils",
    "atomic_write",
    "get_git_version",
    "get_git_describe",
    "get_version_info",
    "get_project_root",
    "get_templates_dir",
    "get_static_dir",
    "get_input_dir",
    "get_src_dir",
]
