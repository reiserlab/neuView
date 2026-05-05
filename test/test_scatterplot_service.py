"""Regression tests for ScatterplotService.

Covers bug #1 from secret/00_refactor_issue_78.md: the line at
src/neuview/services/scatterplot_service.py:190

    if region_dict["cols_innervated"] > 0:

crashes whenever the cached spatial_metrics is missing or contains None
for cols_innervated. This happens whenever the cache build at
src/neuview/services/cache_service.py skipped the spatial calc block
(empty roi_counts_df, missing page_generator, missing connector, or an
exception). After the fix (use .get("cols_innervated", 0)) the function
must mark every uninnervated cell with incl_scatter=None and never raise.
"""

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from neuview.services.scatterplot_service import ScatterplotService  # noqa: E402


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


def _make_service(cache_mgr):
    svc = ScatterplotService.__new__(ScatterplotService)
    svc.cache_manager = cache_mgr
    return svc


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
    svc = _make_service(cache_mgr)

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
    svc = _make_service(cache_mgr)

    plot_data = svc._extract_plot_data(["TypeC"])

    out = plot_data[0]["spatial_metrics"]
    assert out["L"]["ME"]["incl_scatter"] == 1
    assert out["L"]["LO"]["incl_scatter"] is None
    assert out["R"]["ME"]["incl_scatter"] is None
    assert out["both"]["ME"]["incl_scatter"] is None
