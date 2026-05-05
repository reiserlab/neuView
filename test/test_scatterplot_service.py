"""Regression tests for ScatterplotService.

Covers bug #2 from secret/00_refactor_issue_78.md: ``_prepare`` calls
``min()/max()`` on a generator over ``points`` and crashes with
``ValueError`` whenever ``points`` is empty (line 304-307 of
src/neuview/services/scatterplot_service.py). The same crash repeats on
``coverages = [p['coverage'] for p in points]`` at line 316.

A real-runtime trigger is a subset whose neurons don't innervate the
target ``(side, region)`` slot - e.g. a single-type subset of
``LAL048`` (only ``LO_R`` columns), where the very first plot
``(both, ME)`` ends up with zero points.

After the fix (delete dead lines 304-307, early-return on empty points,
have caller skip writing the SVG) these tests pass.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from neuview.services.scatterplot_service import ScatterplotService  # noqa: E402
from neuview.visualization.rendering.rendering_config import (  # noqa: E402
    ScatterConfig,
)


def _make_service():
    """Build a ScatterplotService without running its filesystem-touching __init__."""
    svc = ScatterplotService.__new__(ScatterplotService)
    svc.scatter_config = ScatterConfig()
    return svc


@pytest.mark.parametrize(
    "side, region",
    [
        ("both", "ME"),
        ("both", "LO"),
        ("both", "LOP"),
        ("L", "ME"),
        ("R", "LOP"),
    ],
)
def test_prepare_handles_empty_points(side, region):
    """``_prepare`` must not crash when ``_extract_points`` returns ``[]``.

    Pre-fix: ``ValueError: min() arg is an empty sequence`` from line 304.
    Post-fix: returns successfully (return value shape is up to the fix --
    this test only asserts no exception).
    """
    svc = _make_service()

    svc._prepare(svc.scatter_config, [], region=region, side=side)


def test_prepare_handles_single_point():
    """Sanity: one valid point should still render (no degenerate-range crash).

    Guards against a fix that over-zealously rejects non-empty inputs.
    """
    svc = _make_service()
    points = [
        {
            "name": "LAL048",
            "x": 10.0,
            "y": 1.0,
            "coverage": 1.0,
            "col_count": 2,
        }
    ]

    svc._prepare(svc.scatter_config, points, region="LO", side="R")
