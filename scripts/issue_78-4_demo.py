"""
Regression demo for issue #4 from secret/00_refactor_issue_78.md:
in-place mutation of cached `spatial_metrics` by ScatterplotService.

Use case
--------
The pipeline maintains a per-neuron-type cache populated during
`neuview generate`. ROI ingestion can leave some `(side, region)` cells
unpopulated (e.g., a Tm-style type whose left/right `LO`/`LOP` columns
were never produced because the connector path at
`cache_service.py:162-167` was skipped, or the ROI filter matched
nothing).

A natural diagnostic is "list neuron types whose cache has any
unpopulated `(side, region)` cell, so the operator knows which to
re-ingest."

When issue #4 was present, running scatter first in the same process
silently made the diagnostic certify every type as complete: the old
`_extract_plot_data` aliased `cache_data.spatial_metrics` and wrote
`{}` placeholders + `incl_scatter` annotations through the alias.

This script imports the real `ScatterplotService._extract_plot_data`,
stubs its `cache_manager`, and runs the diagnostic three times. With
the fix in place, all three audits agree. If the alias-and-mutate
pattern is reintroduced, the third audit will diverge.

Run with:  pixi run python scripts/issue_78-4_demo.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from neuview.services.scatterplot_service import ScatterplotService


# Stand-in for NeuronTypeCacheData carrying only what _extract_plot_data reads.
@dataclass
class CacheData:
    neuron_type: str
    total_count: Optional[int] = None
    soma_side_counts: dict = field(default_factory=dict)
    spatial_metrics: Optional[dict] = None


# Mirrors LazyCacheDataDict (cache.py:105-128): hands back the SAME object
# on every access, so any mutation persists for the life of the dict.
class LazyCache:
    def __init__(self, payload):
        self._cache = payload

    def get(self, name):
        return self._cache.get(name)

    def __iter__(self):
        return iter(self._cache)


# _extract_plot_data only calls cache_manager.get_cached_data_lazy().
class StubCacheManager:
    def __init__(self, lazy):
        self._lazy = lazy

    def get_cached_data_lazy(self):
        return self._lazy


def build_cache():
    """Tm5: only ME ingested (L, R). LO/LOP cells absent on every side.
    Mi9: full coverage on all 9 (side, region) cells."""
    return LazyCache({
        "Tm5": CacheData(
            neuron_type="Tm5",
            spatial_metrics={
                "L": {"ME": {"cols_innervated": 12, "coverage": 1.4, "cell_size": 0.7}},
                "R": {"ME": {"cols_innervated": 11, "coverage": 1.3, "cell_size": 0.7}},
            },
        ),
        "Mi9": CacheData(
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


def make_service(cache):
    """Skip ScatterplotService.__init__ — it loads `config.yaml` from CWD
    and mkdirs the scatter directory (issues #3 and #12). Only
    `cache_manager` is needed by `_extract_plot_data`."""
    service = ScatterplotService.__new__(ScatterplotService)
    service.cache_manager = StubCacheManager(cache)
    return service


def audit_missing_cells(cache):
    result = {}
    for name in cache:
        sm = cache.get(name).spatial_metrics or {}
        missing = [
            (s, r)
            for s in ("L", "R", "both")
            for r in ("ME", "LO", "LOP")
            if r not in sm.get(s, {})
        ]
        if missing:
            result[name] = missing
    return result


def show(label, audit):
    print(f"\n{label}")
    print("-" * len(label))
    if not audit:
        print("  no neuron types flagged for re-ingestion")
        return
    for name, missing in audit.items():
        cells = ", ".join(f"{s}/{r}" for s, r in missing)
        print(f"  {name}: needs re-ingestion for [{cells}]")


if __name__ == "__main__":
    cache = build_cache()
    show("Audit BEFORE scatter runs (ground truth)",
         audit_missing_cells(cache))

    show("Audit again, no scatter run (control: audit is idempotent)",
         audit_missing_cells(cache))

    # Same process, same cache: invokes the real production code path.
    service = make_service(cache)
    service._extract_plot_data(["Tm5", "Mi9"])
    show("Audit AFTER scatter runs (should match step 1)",
         audit_missing_cells(cache))
