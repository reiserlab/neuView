"""Tests for DataFrame extraction helpers used by neuron-summary code paths."""

import numpy as np
import pandas as pd
import pytest

from neuview.utils.df_utils import extract_first_non_null, extract_unique_joined

pytestmark = pytest.mark.unit


class TestExtractFirstNonNull:
    def test_first_row_nan_returns_later_non_null(self):
        # Reproduces the synonym bug: a join leaves row 0 NaN while later
        # rows still carry the celltype's synonym string.
        df = pd.DataFrame(
            {
                "type": ["X", "X", "X"],
                "synonyms": [np.nan, "old-name", "old-name"],
            }
        )
        assert (
            extract_first_non_null(df, ("synonyms_y", "synonyms")) == "old-name"
        )

    def test_prefers_first_listed_column_when_present(self):
        df = pd.DataFrame(
            {
                "synonyms_y": ["from-y", np.nan],
                "synonyms": ["from-x", "from-x"],
            }
        )
        assert (
            extract_first_non_null(df, ("synonyms_y", "synonyms")) == "from-y"
        )

    def test_falls_through_to_second_column(self):
        df = pd.DataFrame({"synonyms": ["only-here"]})
        assert (
            extract_first_non_null(df, ("synonyms_y", "synonyms")) == "only-here"
        )

    def test_returns_none_when_all_nan(self):
        df = pd.DataFrame({"synonyms": [np.nan, np.nan]})
        assert extract_first_non_null(df, ("synonyms",)) is None

    def test_returns_none_when_no_listed_column_present(self):
        df = pd.DataFrame({"other": [1, 2]})
        assert extract_first_non_null(df, ("synonyms_y", "synonyms")) is None

    def test_empty_dataframe(self):
        df = pd.DataFrame({"synonyms": pd.Series([], dtype=object)})
        assert extract_first_non_null(df, ("synonyms",)) is None


class TestExtractUniqueJoined:
    def test_aggregates_unique_values_skipping_nan(self):
        # Reproduces the AKA-name bug: row 0's flywireType is NaN, so the
        # old first-row-only approach dropped "MTe05".
        df = pd.DataFrame(
            {"flywireType": [np.nan, "MTe05", "MTe06", "MTe05"]}
        )
        assert (
            extract_unique_joined(df, ("flywireType_y", "flywireType"))
            == "MTe05, MTe06"
        )

    def test_result_is_sorted(self):
        df = pd.DataFrame({"flywireType": ["MTe06", "MTe05", "MTe07"]})
        assert (
            extract_unique_joined(df, ("flywireType",)) == "MTe05, MTe06, MTe07"
        )

    def test_prefers_first_listed_column_when_present(self):
        df = pd.DataFrame(
            {
                "flywireType_y": ["A", "B"],
                "flywireType": ["C", "D"],
            }
        )
        assert (
            extract_unique_joined(df, ("flywireType_y", "flywireType")) == "A, B"
        )

    def test_returns_none_when_all_nan(self):
        df = pd.DataFrame({"flywireType": [np.nan, np.nan]})
        assert extract_unique_joined(df, ("flywireType",)) is None

    def test_returns_none_when_no_listed_column_present(self):
        df = pd.DataFrame({"other": ["x"]})
        assert (
            extract_unique_joined(df, ("flywireType_y", "flywireType")) is None
        )

    def test_custom_separator(self):
        df = pd.DataFrame({"flywireType": ["A", "B"]})
        assert extract_unique_joined(df, ("flywireType",), sep=" | ") == "A | B"
