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


def extract_unique_list(
    df: pd.DataFrame, column_names: Iterable[str]
) -> Optional[list]:
    """Return a sorted list of all unique non-NaN values from the first matching column.

    Iterates ``column_names`` in order, picks the first column present in ``df``,
    and returns a sorted list of unique non-NaN values. Returns ``None`` if no
    listed column is present or every value is NaN.

    Use this for celltype-summary fields whose values may legitimately differ
    across cells in the type (e.g. ``somaNeuromere``, ``cellSubclass``,
    ``trumanHl``) so that downstream filter UI and tag rendering can iterate
    over each distinct value.
    """
    for col in column_names:
        if col in df.columns:
            unique = df[col].dropna().unique()
            if len(unique) == 0:
                return None
            return sorted({str(v) for v in unique})
    return None


def extract_unique_joined(
    df: pd.DataFrame, column_names: Iterable[str], sep: str = ", "
) -> Optional[str]:
    """Return a sorted, deduped, joined string of all non-NaN values from the first matching column.

    Thin wrapper around :func:`extract_unique_list` for callers that want a
    display string (e.g. ``flywireType``) rather than a list to iterate over.
    """
    values = extract_unique_list(df, column_names)
    return sep.join(values) if values else None
