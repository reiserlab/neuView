"""Regression tests for ScatterplotService.

Covers two bugs from secret/00_refactor_issue_78.md:

- Bug #1: ``_extract_plot_data`` raises ``KeyError`` / ``TypeError`` when
  the cached ``spatial_metrics`` is missing, ``{}``, or contains ``None``
  for ``cols_innervated`` (line 190 pre-fix). The cache build at
  ``cache_service.py`` skips the spatial calc block whenever
  ``roi_counts_df`` is empty/missing or the connector is unavailable, so
  these states are reachable in practice. After the fix (use
  ``.get("cols_innervated", 0)``) every uninnervated cell is marked
  ``incl_scatter=None`` and the function never raises.

- Bug #2: ``_prepare`` calls ``min()/max()`` on a generator over
  ``points`` and crashes with ``ValueError`` whenever ``points`` is
  empty (line 304-307 pre-fix). A real-runtime trigger is a subset
  whose neurons don't innervate every ``(side, region)`` slot -- e.g.
  ``LAL048`` (only ``LO_R`` columns), where 7 of 9 plots end up with
  zero points. After the fix (early-return on empty points, have caller
  skip writing the SVG) these tests pass.
"""

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from neuview.services.scatterplot_service import ScatterplotService  # noqa: E402
from neuview.visualization.rendering.rendering_config import (  # noqa: E402
    ScatterConfig,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


class _StubLazy:
    def __init__(self, data):
        self._data = data

    def get(self, name, default=None):
        return self._data.get(name, default)

    def keys(self):
        return self._data.keys()

    def __iter__(self):
        return iter(self._data)

    def __contains__(self, name):
        return name in self._data


class _StubCacheMgr:
    def __init__(self, data):
        self._data = data

    def get_cached_data_lazy(self):
        return _StubLazy(self._data)


def _fake_cache_data(spatial_metrics):
    return SimpleNamespace(
        total_count=10,
        soma_side_counts={"left": 5, "right": 5, "middle": 0},
        spatial_metrics=spatial_metrics,
    )


def _full_none_metrics():
    return {
        side: {
            region: {
                "cols_innervated": None,
                "coverage": None,
                "cell_size": None,
            }
            for region in ("ME", "LO", "LOP")
        }
        for side in ("L", "R", "both")
    }


def _make_service(cache_mgr=None, scatter_config=None):
    """Build a ScatterplotService without running its filesystem-touching __init__."""
    svc = ScatterplotService.__new__(ScatterplotService)
    if cache_mgr is not None:
        svc.cache_manager = cache_mgr
    if scatter_config is not None:
        svc.scatter_config = scatter_config
    return svc


# ---------------------------------------------------------------------------
# Bug #1: _extract_plot_data on missing / None spatial_metrics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label, spatial_metrics",
    [
        ("path_a_none", None),
        ("path_a_empty_dict", {}),
        ("path_b_cols_innervated_none", _full_none_metrics()),
    ],
)
def test_extract_plot_data_handles_missing_spatial_metrics(label, spatial_metrics):
    """_extract_plot_data must not crash when spatial_metrics is absent or partial.

    Pre-fix: raises KeyError (paths A) or TypeError (path B) from line 190.
    Post-fix: every (side, region) cell is marked incl_scatter = None.
    """
    cache_mgr = _StubCacheMgr({"TestType": _fake_cache_data(spatial_metrics)})
    svc = _make_service(cache_mgr=cache_mgr)

    plot_data = svc._extract_plot_data(["TestType"])

    assert len(plot_data) == 1
    sm = plot_data[0]["spatial_metrics"]
    for side in ("L", "R", "both"):
        for region in ("ME", "LO", "LOP"):
            assert sm[side][region].get("incl_scatter") is None, (
                f"{label}: ({side}, {region}) should be incl_scatter=None, "
                f"got {sm[side][region]}"
            )


def test_extract_plot_data_marks_innervated_cells():
    """Cells with cols_innervated > 0 are marked incl_scatter = 1; others = None."""
    sm = {
        side: {
            region: {
                "cols_innervated": 5 if (side, region) == ("L", "ME") else 0,
                "coverage": 1.5,
                "cell_size": 3.0,
            }
            for region in ("ME", "LO", "LOP")
        }
        for side in ("L", "R", "both")
    }
    cache_mgr = _StubCacheMgr({"TypeC": _fake_cache_data(sm)})
    svc = _make_service(cache_mgr=cache_mgr)

    plot_data = svc._extract_plot_data(["TypeC"])

    out = plot_data[0]["spatial_metrics"]
    assert out["L"]["ME"]["incl_scatter"] == 1
    assert out["L"]["LO"]["incl_scatter"] is None
    assert out["R"]["ME"]["incl_scatter"] is None
    assert out["both"]["ME"]["incl_scatter"] is None


# ---------------------------------------------------------------------------
# Bug #2: _prepare on empty points
# ---------------------------------------------------------------------------


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
    svc = _make_service(scatter_config=ScatterConfig())

    svc._prepare(svc.scatter_config, [], region=region, side=side)


def test_prepare_handles_single_point():
    """Sanity: one valid point should still render (no degenerate-range crash).

    Guards against a fix that over-zealously rejects non-empty inputs.
    """
    svc = _make_service(scatter_config=ScatterConfig())
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
