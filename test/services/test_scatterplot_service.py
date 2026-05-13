"""Tests for ScatterplotService — bug fixes and feature additions.

Covers the regressions tracked in secret/00_refactor_issue_78.md plus
PR #156's axis-range and out-of-range-filter changes.

- Bug #1 (PR #149/#152): ``_extract_plot_data`` raised ``KeyError`` /
  ``TypeError`` when cached ``spatial_metrics`` was missing, ``{}``, or
  contained ``None`` for ``cols_innervated``. Fix drops the back-write
  and computes inclusion locally in ``_extract_points`` with defensive
  ``None``-tolerant navigation.

- Bug #2 (PR #150): ``_prepare`` called ``min()/max()`` on a generator
  over ``points`` and crashed with ``ValueError`` on empty input. Fix
  early-returns ``None`` so the caller can skip rendering.

- Bug #4 (PR #152): ``_extract_plot_data`` aliased
  ``cache_data.spatial_metrics`` and back-wrote ``incl_scatter`` plus
  ``{}`` placeholders through the alias, poisoning other consumers of
  the cache. Fix computes the inclusion check locally without writing.

- PR #156: ``ScatterConfig.axis_min`` / ``axis_max`` replace inline
  ``[1, 1000]`` constants. ``_prepare`` filters out-of-range points
  with a single WARNING per plot. The empty-input guard (PR #150's
  invariant) is preserved AFTER the filter so the new
  "all-points-filtered" case also returns ``None`` cleanly.
"""

from __future__ import annotations

import logging
import os
import sys
from copy import deepcopy
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Optional

import pytest

from neuview.services.scatterplot_service import ScatterplotService  # noqa: E402
from neuview.visualization.rendering.rendering_config import (  # noqa: E402
    ScatterConfig,
)


# ---------------------------------------------------------------------------
# Shared fixtures (helpers)
# ---------------------------------------------------------------------------


class _StubLazy:
    """Fresh-each-call lazy dict — recreated by ``_StubCacheMgr.get_cached_data_lazy``
    on every call, so mutations through one access don't persist across
    calls. Used by the bug #1 tests where mutation isn't the concern."""

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
    """Dict-backed cache manager — returns a fresh ``_StubLazy`` each call."""

    def __init__(self, data):
        self._data = data

    def get_cached_data_lazy(self):
        return _StubLazy(self._data)


class _LazyCache:
    """Same-reference lazy cache — hands back the SAME object reference on
    every ``get(name)``, mirroring real ``LazyCacheDataDict`` (cache.py).
    Used by the bug #4 immutability test so mutations through one access
    would persist for later accesses if the bug were present."""

    def __init__(self, payload):
        self._cache = payload

    def get(self, name):
        return self._cache.get(name)

    def __iter__(self):
        return iter(self._cache)


class _RefStableCacheMgr:
    """Cache manager that always returns the same ``_LazyCache`` reference.
    Used by the bug #4 immutability test."""

    def __init__(self, lazy):
        self._lazy = lazy

    def get_cached_data_lazy(self):
        return self._lazy


@dataclass
class _CacheData:
    """Stand-in for ``NeuronTypeCacheData`` carrying only what
    ``_extract_plot_data`` reads."""

    neuron_type: str
    total_count: Optional[int] = None
    soma_side_counts: dict = field(default_factory=dict)
    spatial_metrics: Optional[dict] = None


def _fake_cache_data(spatial_metrics):
    """``SimpleNamespace`` fake for the bug #1 tests."""
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


def _point(name, x, y, coverage=1.0, col_count=1):
    """Construct a point dict matching what ``_extract_points`` would produce."""
    return {
        "name": name,
        "x": x,
        "y": y,
        "coverage": coverage,
        "col_count": col_count,
    }


def _warnings_about_range(caplog):
    """Filter caplog records to just the out-of-range warnings."""
    return [
        r
        for r in caplog.records
        if r.levelname == "WARNING" and "outside axis range" in r.getMessage()
    ]


# ===========================================================================
# Bug #1 (PR #149/#152): _extract_plot_data on missing / None spatial_metrics
# ===========================================================================


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


# ===========================================================================
# Bug #2 (PR #150): _prepare on empty / single-point input
# ===========================================================================


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
    Post-fix: returns successfully (return value shape is up to the fix —
    this test only asserts no exception). See
    ``TestEmptyInputReturnsNone`` below for the stronger ``is None``
    assertion.
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


# ===========================================================================
# Bug #4 (PR #152): cache immutability
# ===========================================================================


@pytest.fixture
def immutability_cache():
    """Tm5: only ME ingested (L, R) — sparse spatial_metrics, the case
    that exercises the back-write of ``{}`` placeholders.
    Mi9: full coverage on all 9 (side, region) cells."""
    return _LazyCache(
        {
            "Tm5": _CacheData(
                neuron_type="Tm5",
                spatial_metrics={
                    "L": {
                        "ME": {"cols_innervated": 12, "coverage": 1.4, "cell_size": 0.7}
                    },
                    "R": {
                        "ME": {"cols_innervated": 11, "coverage": 1.3, "cell_size": 0.7}
                    },
                },
            ),
            "Mi9": _CacheData(
                neuron_type="Mi9",
                spatial_metrics={
                    side: {
                        region: {
                            "cols_innervated": 30,
                            "coverage": 1.1,
                            "cell_size": 1.0,
                        }
                        for region in ("ME", "LO", "LOP")
                    }
                    for side in ("L", "R", "both")
                },
            ),
        }
    )


class TestScatterplotServiceCacheImmutability:
    """Issue #4: scatter generation must not mutate cached data."""

    @pytest.mark.unit
    def test_extract_plot_data_does_not_mutate_spatial_metrics(
        self, immutability_cache
    ):
        # Mi9 has full (side, region) coverage, so the alias-and-mutate
        # pattern would run to completion and add ``incl_scatter`` keys
        # to every cell — caught here by a direct equality check that
        # doesn't entangle with issue #1's KeyError on sparse Tm5.
        snapshot = {
            n: deepcopy(immutability_cache.get(n).spatial_metrics)
            for n in immutability_cache
        }
        service = _make_service(cache_mgr=_RefStableCacheMgr(immutability_cache))
        service._extract_plot_data(["Mi9"])
        after = {
            n: immutability_cache.get(n).spatial_metrics for n in immutability_cache
        }
        assert after == snapshot


# ===========================================================================
# PR #156: axis range from config (hoist)
# ===========================================================================


@pytest.mark.unit
class TestAxisRangeFromConfig:
    """ScatterConfig now exposes axis_min/axis_max; _prepare reads from there."""

    def test_default_range_is_1_to_1000(self):
        """Defaults preserve the old hardcoded range so downstream plots are unchanged."""
        cfg = ScatterConfig()
        assert cfg.axis_min == 1.0
        assert cfg.axis_max == 1000.0

    def test_custom_range_overrides_via_constructor(self):
        """Constructor args take effect (relies on PR #155's 'actually
        configurable' fix being in place too)."""
        cfg = ScatterConfig(axis_min=10.0, axis_max=2000.0)
        assert cfg.axis_min == 10.0
        assert cfg.axis_max == 2000.0

    def test_default_range_keeps_in_range_point(self):
        """A point at (5, 100) is inside [1, 1000] — should survive _prepare."""
        svc = _make_service(scatter_config=ScatterConfig())
        ctx = svc._prepare(
            svc.scatter_config,
            [_point("p1", 5, 100)],
            region="ME",
            side="L",
        )
        assert ctx is not None
        assert len(ctx["points"]) == 1
        assert ctx["points"][0]["name"] == "p1"

    def test_custom_range_actually_changes_filter_boundary(self):
        """A point at (100, 10) survives default range but is filtered when
        axis_max=50. Demonstrates the config value is plumbed all the way
        through to the filter."""
        svc = _make_service(scatter_config=ScatterConfig(axis_min=1, axis_max=50))
        ctx = svc._prepare(
            svc.scatter_config,
            [
                _point("inside", 10, 10),
                _point("outside", 100, 10),  # x > 50 with custom config
            ],
            region="ME",
            side="L",
        )
        assert ctx is not None
        names = [p["name"] for p in ctx["points"]]
        assert names == ["inside"]


# ===========================================================================
# PR #156: out-of-range filter behavior
# ===========================================================================


@pytest.mark.unit
class TestOutOfRangeFilter:
    """The new filter drops points outside [axis_min, axis_max] with a single
    WARNING per plot."""

    def test_in_range_points_pass_through_with_no_warning(self, caplog):
        """All in-range → no filter, no warning."""
        svc = _make_service(scatter_config=ScatterConfig())
        points = [_point(f"p{i}", 10**i, 10**i) for i in range(4)]
        with caplog.at_level(logging.WARNING):
            ctx = svc._prepare(svc.scatter_config, points, region="ME", side="L")
        assert ctx is not None
        assert len(ctx["points"]) == 4
        assert _warnings_about_range(caplog) == []

    def test_filters_points_above_and_below_range(self):
        """Points outside the range on either axis are dropped."""
        svc = _make_service(scatter_config=ScatterConfig())
        points = [
            _point("ok", 5, 10),
            _point("x_above", 10000, 10),
            _point("y_above", 5, 10000),
            _point("x_below", 0.5, 10),
            _point("y_below", 5, 0.5),
        ]
        ctx = svc._prepare(svc.scatter_config, points, region="ME", side="L")
        assert ctx is not None
        assert [p["name"] for p in ctx["points"]] == ["ok"]

    def test_warning_lists_names_and_truncates_at_10(self, caplog):
        """One warning per plot, region+side in the prefix, up to 10 names
        listed, ``(+N more)`` if truncated."""
        svc = _make_service(scatter_config=ScatterConfig())
        points = [_point("ok", 5, 10)]
        points += [_point(f"out_{i:02d}", 9999, 10) for i in range(12)]
        with caplog.at_level(logging.WARNING):
            svc._prepare(svc.scatter_config, points, region="ME", side="L")
        warnings = _warnings_about_range(caplog)
        assert len(warnings) == 1, "expected exactly one warning per plot"
        msg = warnings[0].getMessage()
        assert "ME/L" in msg, f"expected region/side prefix in: {msg!r}"
        assert "12 point(s)" in msg, f"expected count in: {msg!r}"
        for i in range(10):
            assert f"out_{i:02d}" in msg, f"expected out_{i:02d} in: {msg!r}"
        assert "out_10" not in msg or "(+2 more)" in msg
        assert "(+2 more)" in msg

    def test_no_truncation_tail_when_exactly_10_offenders(self, caplog):
        """Edge case: exactly 10 out-of-range — full list, no ``(+N more)``."""
        svc = _make_service(scatter_config=ScatterConfig())
        points = [_point("ok", 5, 10)]
        points += [_point(f"out_{i:02d}", 9999, 10) for i in range(10)]
        with caplog.at_level(logging.WARNING):
            svc._prepare(svc.scatter_config, points, region="ME", side="L")
        warnings = _warnings_about_range(caplog)
        assert len(warnings) == 1
        msg = warnings[0].getMessage()
        assert "(+0 more)" not in msg
        assert "more)" not in msg


# ===========================================================================
# PR #156: Empty-input safety — restores PR #150's invariant after the filter
# ===========================================================================


@pytest.mark.unit
class TestEmptyInputReturnsNone:
    """The two-line guard at scatterplot_service.py protects against
    ``min(coverages)`` on an empty list. Both the original PR #150 case
    (caller passes []) and the new PR #156 case (everything filtered)
    must return None so the caller's ``if ctx is None: continue`` skips
    the slot.

    These complement ``test_prepare_handles_empty_points`` above by
    asserting the stronger ``is None`` contract (the existing test
    only asserts no exception).
    """

    def test_empty_input_returns_none(self):
        """PR #150 invariant: passing [] should return None, not crash."""
        svc = _make_service(scatter_config=ScatterConfig())
        ctx = svc._prepare(svc.scatter_config, [], region="ME", side="L")
        assert ctx is None, (
            "Expected _prepare([]) to return None so the caller can skip; "
            "got non-None — the empty-input guard has been dropped."
        )

    def test_all_points_filtered_returns_none(self, caplog):
        """PR #156 case: every input point is out of range, so after
        filtering ``points = []``. Same crash as the empty-input case
        unless the guard is placed AFTER the filter (not before)."""
        svc = _make_service(scatter_config=ScatterConfig())
        points = [
            _point("out_a", 9999, 1),
            _point("out_b", 1, 9999),
            _point("out_c", 0.001, 1),
        ]
        with caplog.at_level(logging.WARNING):
            ctx = svc._prepare(svc.scatter_config, points, region="ME", side="L")
        assert _warnings_about_range(caplog), (
            "Expected the out-of-range warning to fire even when everything "
            "is filtered."
        )
        assert ctx is None, (
            "Expected _prepare with all-out-of-range input to return None; "
            "got non-None — the empty-input guard runs before the filter, "
            "not after."
        )


# ===========================================================================
# PR #156: positive regression — normal case still produces a valid context
# ===========================================================================


@pytest.mark.unit
class TestNormalCaseRegression:
    """Confirm that the fix and filter additions don't break the normal
    happy path of mixed in-range / out-of-range input."""

    def test_mixed_input_returns_ctx_with_only_in_range(self, caplog):
        """Some in, some out: ctx returned, warning fires, ctx['points']
        contains only the in-range names."""
        svc = _make_service(scatter_config=ScatterConfig())
        points = [
            _point("kept_a", 5, 10),
            _point("kept_b", 100, 50),
            _point("dropped", 9999, 10),
        ]
        with caplog.at_level(logging.WARNING):
            ctx = svc._prepare(svc.scatter_config, points, region="ME", side="L")
        assert ctx is not None
        assert sorted(p["name"] for p in ctx["points"]) == ["kept_a", "kept_b"]
        assert _warnings_about_range(caplog), (
            "expected an out-of-range warning to fire"
        )

    def test_ctx_has_render_metadata_for_kept_points(self):
        """Each kept point gets sx / sy / color / r / tooltip metadata for the
        SVG template — confirms the post-filter half of _prepare still runs."""
        svc = _make_service(scatter_config=ScatterConfig())
        ctx = svc._prepare(
            svc.scatter_config,
            [_point("p1", 5, 10), _point("p2", 50, 100)],
            region="ME",
            side="L",
        )
        assert ctx is not None
        for p in ctx["points"]:
            assert "sx" in p and isinstance(p["sx"], (int, float))
            assert "sy" in p and isinstance(p["sy"], (int, float))
            assert "color" in p
            assert "r" in p
            assert "tooltip" in p

    def test_single_in_range_point_does_not_crash(self):
        """Edge case: one point. ``coverages = [1.0]``, min/max work fine
        (degenerate range handled by the cmax/cmin fallback)."""
        svc = _make_service(scatter_config=ScatterConfig())
        ctx = svc._prepare(
            svc.scatter_config,
            [_point("only", 5, 10, coverage=1.5)],
            region="ME",
            side="L",
        )
        assert ctx is not None
        assert len(ctx["points"]) == 1


# ===========================================================================
# Cell-count formula in _extract_points for side in {L, R, both}
# ===========================================================================
# `side="both"` used to compute `int(total_count / 2)`, which crashed when
# `total_count` was missing and dropped midline-only types to x=0 (silently
# filtered by the x>0 log-scale guard). The current formula is
#   L     -> left_count
#   R     -> right_count
#   both  -> (left_count + right_count) / 2 + middle_count
# i.e. average of the two hemispheres plus midline cells counted whole, with
# all three count fields defaulting to 0 when absent.


def _rec_with_innervated_cell(name="T", **counts):
    """Build a plot_data record where (L|R|both, ME) is innervated.

    ``counts`` is a subset of {left_count, right_count, middle_count,
    total_count}. Keys not provided are absent from the record so we can
    exercise the .get(..., 0) defaults.
    """
    rec = {
        "name": name,
        "spatial_metrics": {
            side: {
                "ME": {
                    "cols_innervated": 5,
                    "cell_size": 3.0,
                    "coverage": 1.5,
                }
            }
            for side in ("L", "R", "both")
        },
    }
    rec.update(counts)
    return rec


@pytest.mark.parametrize(
    "label, side, counts, expected_x",
    [
        # side="both": new (left+right)/2 + middle formula
        (
            "midline_only_stays_visible",
            "both",
            {"left_count": 0, "right_count": 0, "middle_count": 7},
            7.0,
        ),
        (
            "mixed_left_right_and_midline",
            "both",
            {"left_count": 10, "right_count": 14, "middle_count": 3},
            15.0,  # (10+14)/2 + 3
        ),
        (
            "no_midline_simple_mean",
            "both",
            {"left_count": 10, "right_count": 14, "middle_count": 0},
            12.0,  # (10+14)/2
        ),
        (
            "asymmetric_no_LR_assumption",
            "both",
            {"left_count": 6, "right_count": 18, "middle_count": 0},
            12.0,  # (6+18)/2 -- does not assume L/R symmetry
        ),
        # side="L" / "R" pick their own count directly and ignore the others
        (
            "L_uses_left_count_only",
            "L",
            {"left_count": 20, "right_count": 999, "middle_count": 999},
            20.0,
        ),
        (
            "R_uses_right_count_only",
            "R",
            {"left_count": 999, "right_count": 15, "middle_count": 999},
            15.0,
        ),
    ],
)
def test_extract_points_cell_count_formula(label, side, counts, expected_x):
    """_extract_points uses the side-specific cell-count formula."""
    svc = _make_service()
    points = svc._extract_points(
        [_rec_with_innervated_cell(**counts)], side=side, region="ME"
    )
    assert len(points) == 1, f"{label}: expected exactly one point"
    assert points[0]["x"] == pytest.approx(expected_x), label


def test_extract_points_both_does_not_require_total_count():
    """Regression: the old ``int(total_count / 2)`` formula crashed with
    TypeError when ``total_count`` was missing. The new formula reads
    left/right/middle directly, so a record without ``total_count`` works."""
    svc = _make_service()
    rec = _rec_with_innervated_cell(left_count=4, right_count=6, middle_count=0)
    assert "total_count" not in rec

    points = svc._extract_points([rec], side="both", region="ME")
    assert len(points) == 1
    assert points[0]["x"] == pytest.approx(5.0)


def test_extract_points_both_with_all_counts_absent_filters_out():
    """When no count fields are present, every .get(..., 0) returns 0, so
    x=0 and the x>0 log-scale guard correctly drops the point. This locks
    in the contract that absent counts are a soft skip, not a crash."""
    svc = _make_service()
    rec = {
        "name": "Empty",
        "spatial_metrics": {
            "both": {
                "ME": {
                    "cols_innervated": 5,
                    "cell_size": 3.0,
                    "coverage": 1.5,
                }
            }
        },
    }

    assert svc._extract_points([rec], side="both", region="ME") == []


# ===========================================================================
# PR #162: Pure-math helpers — _scale_log10 and _cov_to_rgb
# ===========================================================================


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
