"""
Regression tests for ScatterplotService.

Issue #4 from secret/00_refactor_issue_78.md: an earlier implementation
of `_extract_plot_data` aliased `cache_data.spatial_metrics` and back-
wrote `incl_scatter` annotations plus `{}` placeholders for missing
(side, region) cells. That mutation poisoned any other consumer of the
cache in the same process — for example, a diagnostic that lists
neuron types whose ingestion left some (side, region) cells unpopulated
would falsely certify every type as complete after scatter ran.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Optional

import pytest

from neuview.services.scatterplot_service import ScatterplotService


# Stand-in for NeuronTypeCacheData carrying only what _extract_plot_data reads.
@dataclass
class _CacheData:
    neuron_type: str
    total_count: Optional[int] = None
    soma_side_counts: dict = field(default_factory=dict)
    spatial_metrics: Optional[dict] = None


# Mirrors LazyCacheDataDict (cache.py:105-128): hands back the SAME
# object reference on every access, so any mutation through the alias
# would persist for the life of the dict.
class _LazyCache:
    def __init__(self, payload):
        self._cache = payload

    def get(self, name):
        return self._cache.get(name)

    def __iter__(self):
        return iter(self._cache)


class _StubCacheManager:
    def __init__(self, lazy):
        self._lazy = lazy

    def get_cached_data_lazy(self):
        return self._lazy


def _make_service(cache):
    """Skip ScatterplotService.__init__ — it loads `config.yaml` from CWD
    and mkdirs the scatter directory. `_extract_plot_data` only reads
    `self.cache_manager`."""
    service = ScatterplotService.__new__(ScatterplotService)
    service.cache_manager = _StubCacheManager(cache)
    return service


@pytest.fixture
def cache():
    """Tm5: only ME ingested (L, R) — sparse spatial_metrics, the case
    that exercises the back-write of `{}` placeholders.
    Mi9: full coverage on all 9 (side, region) cells."""
    return _LazyCache({
        "Tm5": _CacheData(
            neuron_type="Tm5",
            spatial_metrics={
                "L": {"ME": {"cols_innervated": 12, "coverage": 1.4, "cell_size": 0.7}},
                "R": {"ME": {"cols_innervated": 11, "coverage": 1.3, "cell_size": 0.7}},
            },
        ),
        "Mi9": _CacheData(
            neuron_type="Mi9",
            spatial_metrics={
                side: {
                    region: {"cols_innervated": 30, "coverage": 1.1, "cell_size": 1.0}
                    for region in ("ME", "LO", "LOP")
                }
                for side in ("L", "R", "both")
            },
        ),
    })


class TestScatterplotServiceCacheImmutability:
    """Issue #4: scatter generation must not mutate cached data."""

    @pytest.mark.unit
    def test_extract_plot_data_does_not_mutate_spatial_metrics(self, cache):
        # Mi9 has full (side, region) coverage, so the alias-and-mutate
        # pattern would run to completion and add `incl_scatter` keys to
        # every cell — caught here by a direct equality check that
        # doesn't entangle with issue #1's KeyError on sparse Tm5.
        snapshot = {n: deepcopy(cache.get(n).spatial_metrics) for n in cache}
        service = _make_service(cache)
        service._extract_plot_data(["Mi9"])
        after = {n: cache.get(n).spatial_metrics for n in cache}
        assert after == snapshot
