"""Regression tests for ScatterplotService.

Covers two bugs from secret/00_refactor_issue_78.md:

- Bug #1: ``_extract_plot_data`` raised ``KeyError`` / ``TypeError`` when
  the cached ``spatial_metrics`` was missing, ``{}``, or contained
  ``None`` for ``cols_innervated``. The cache build at
  ``cache_service.py`` skips the spatial calc block whenever
  ``roi_counts_df`` is empty/missing or the connector is unavailable, so
  these states are reachable in practice. The fix (issue #4 cleaner
  variant) drops the back-write of ``incl_scatter`` onto the cache
  entirely and computes it locally inside ``_extract_points`` using
  ``(cols_innervated or 0) > 0`` with defensive ``None``-tolerant
  navigation, so no path through ``_extract_plot_data`` /
  ``_extract_points`` raises and uninnervated cells contribute no
  points.

- Bug #2: ``_prepare`` called ``min()/max()`` on a generator over
  ``points`` and crashed with ``ValueError`` whenever ``points`` was
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
    """The full extract pipeline must not crash on absent / partial spatial_metrics.

    Pre-fix: ``_extract_plot_data`` raised KeyError (paths A) or
    TypeError (path B). Post-fix: ``_extract_plot_data`` returns the raw
    cached structure unmodified and ``_extract_points`` filters
    uninnervated cells out, yielding zero points for every (side,
    region).
    """
    cache_mgr = _StubCacheMgr({"TestType": _fake_cache_data(spatial_metrics)})
    svc = _make_service(cache_mgr=cache_mgr)

    plot_data = svc._extract_plot_data(["TestType"])

    assert len(plot_data) == 1
    for side in ("L", "R", "both"):
        for region in ("ME", "LO", "LOP"):
            points = svc._extract_points(plot_data, side=side, region=region)
            assert points == [], (
                f"{label}: ({side}, {region}) should produce no points, got {points}"
            )


def test_extract_points_includes_innervated_cells():
    """Cells with cols_innervated > 0 produce points; others are skipped."""
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

    assert len(svc._extract_points(plot_data, side="L", region="ME")) == 1
    assert svc._extract_points(plot_data, side="L", region="LO") == []
    assert svc._extract_points(plot_data, side="R", region="ME") == []
    assert svc._extract_points(plot_data, side="both", region="ME") == []


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


# ---------------------------------------------------------------------------
# Pure-math helpers: _scale_log10 and _cov_to_rgb
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v, expected_px",
    [
        # vmin maps to a, vmax maps to b — the boundary contract.
        (1, 0.0),
        (1000, 90.0),
        # Log-uniform spacing: log10 covers [0, 3]; pixel covers [0, 90].
        (10, 30.0),
        (100, 60.0),
    ],
)
def test_scale_log10_endpoints_and_log_spacing(v, expected_px):
    svc = ScatterplotService.__new__(ScatterplotService)
    assert svc._scale_log10(v, 1, 1000, 0, 90) == pytest.approx(expected_px)


def test_scale_log10_degenerate_range():
    """vmin == vmax collapses to the midpoint of the pixel range."""
    svc = ScatterplotService.__new__(ScatterplotService)
    assert svc._scale_log10(5, 5, 5, 0, 100) == pytest.approx(50.0)


@pytest.mark.parametrize(
    "t, expected",
    [
        # White → dark red gradient: t=0 is pure white, t=1 is the
        # endpoint dark red the function defines (rgb(180,0,0)).
        (0.0, "rgb(255,255,255)"),
        (1.0, "rgb(180,0,0)"),
        # Midpoint: linear interpolation of each channel, then int(round).
        # _lerp(255, 180, 0.5) = 217.5 → 218 (banker's rounding).
        # _lerp(255,   0, 0.5) = 127.5 → 128.
        (0.5, "rgb(218,128,128)"),
    ],
)
def test_cov_to_rgb_endpoints_and_midpoint(t, expected):
    svc = ScatterplotService.__new__(ScatterplotService)
    assert svc._cov_to_rgb(t) == expected
