"""DataFrame extraction helpers shared across the neuron-summary code paths."""

from typing import Any, Iterable, Optional

import pandas as pd


def extract_first_non_null(
    df: pd.DataFrame, column_names: Iterable[str]
) -> Optional[Any]:
    """Return the first non-NaN value across all rows from the first matching column.

    Iterates ``column_names`` in order, picks the first column present in ``df``,
    and returns the first non-NaN value in that column. Returns ``None`` if no
    listed column is present or every value is NaN.

    Use this for celltype-level attributes where any non-null row carries the
    canonical value (e.g. ``synonyms``).
    """
    for col in column_names:
        if col in df.columns:
            non_null = df[col].dropna()
            return non_null.iloc[0] if not non_null.empty else None
    return None


def extract_unique_joined(
    df: pd.DataFrame, column_names: Iterable[str], sep: str = ", "
) -> Optional[str]:
    """Return a sorted, deduped, joined string of all non-NaN values from the first matching column.

    Iterates ``column_names`` in order, picks the first column present in ``df``,
    and joins the unique non-NaN values with ``sep``. Returns ``None`` if no
    listed column is present or every value is NaN.

    Use this for per-cell attributes that may legitimately differ across rows
    and should be aggregated (e.g. ``flywireType``).
    """
    for col in column_names:
        if col in df.columns:
            unique = df[col].dropna().unique()
            if len(unique) == 0:
                return None
            return sep.join(sorted({str(v) for v in unique}))
    return None
