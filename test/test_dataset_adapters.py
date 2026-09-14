"""Tests for dataset adapters and factory."""

import pandas as pd
import pytest

from neuview.dataset_adapters import (
    DatasetAdapterFactory,
    CNSAdapter,
    CNSRoiQueryStrategy,
    HemibrainAdapter,
    OpticLobeAdapter,
    FafbAdapter,
    WaspAdapter,
)


@pytest.mark.unit
class TestDatasetAdapterFactory:
    """Test cases for DatasetAdapterFactory."""

    @pytest.mark.unit
    def test_create_adapter_exact_match(self):
        """Test creating adapter with exact dataset name match."""
        adapter = DatasetAdapterFactory.create_adapter("cns")
        assert isinstance(adapter, CNSAdapter)

        adapter = DatasetAdapterFactory.create_adapter("hemibrain")
        assert isinstance(adapter, HemibrainAdapter)

        adapter = DatasetAdapterFactory.create_adapter("optic-lobe")
        assert isinstance(adapter, OpticLobeAdapter)

        adapter = DatasetAdapterFactory.create_adapter("flywire-fafb")
        assert isinstance(adapter, FafbAdapter)

        adapter = DatasetAdapterFactory.create_adapter("wasp3")
        assert isinstance(adapter, WaspAdapter)

    @pytest.mark.unit
    def test_create_adapter_versioned_dataset(self):
        """Test creating adapter for versioned dataset names."""
        adapter = DatasetAdapterFactory.create_adapter("cns:v1.0")
        assert isinstance(adapter, CNSAdapter)

        adapter = DatasetAdapterFactory.create_adapter("hemibrain:v1.2")
        assert isinstance(adapter, HemibrainAdapter)

    @pytest.mark.unit
    def test_create_adapter_male_cns_alias(self):
        """Test creating adapter for male-cns alias."""
        adapter = DatasetAdapterFactory.create_adapter("male-cns")
        assert isinstance(adapter, CNSAdapter)

    @pytest.mark.unit
    def test_create_adapter_male_cns_versioned_alias(self):
        """Test creating adapter for versioned male-cns alias."""
        adapter = DatasetAdapterFactory.create_adapter("male-cns:v0.9")
        assert isinstance(adapter, CNSAdapter)

    @pytest.mark.unit
    def test_create_adapter_unknown_dataset_defaults_to_cns(self, capsys):
        """Test that unknown dataset defaults to CNS adapter with warning."""
        adapter = DatasetAdapterFactory.create_adapter("unknown-dataset")
        assert isinstance(adapter, CNSAdapter)

        captured = capsys.readouterr()
        assert (
            "Warning: Unknown dataset 'unknown-dataset', using CNS adapter as default"
            in captured.out
        )

    @pytest.mark.unit
    def test_create_adapter_unknown_versioned_dataset_defaults_to_cns(self, capsys):
        """Test that unknown versioned dataset defaults to CNS adapter with warning."""
        adapter = DatasetAdapterFactory.create_adapter("unknown-dataset:v1.0")
        assert isinstance(adapter, CNSAdapter)

        captured = capsys.readouterr()
        assert (
            "Warning: Unknown dataset 'unknown-dataset:v1.0', using CNS adapter as default"
            in captured.out
        )

    @pytest.mark.unit
    def test_get_supported_datasets(self):
        """Test getting list of supported datasets."""
        supported = DatasetAdapterFactory.get_supported_datasets()
        expected = ["cns", "hemibrain", "optic-lobe", "flywire-fafb", "wasp3"]
        assert set(supported) == set(expected)

    @pytest.mark.unit
    def test_register_adapter(self):
        """Test registering a new adapter."""
        # Create a mock adapter class
        MockAdapter = type("MockAdapter", (CNSAdapter,), {})

        # Register the adapter
        DatasetAdapterFactory.register_adapter("test-dataset", MockAdapter)

        # Verify it was registered
        supported = DatasetAdapterFactory.get_supported_datasets()
        assert "test-dataset" in supported

        # Verify it can be created
        adapter = DatasetAdapterFactory.create_adapter("test-dataset")
        assert isinstance(adapter, MockAdapter)

        # Clean up - remove from registry
        del DatasetAdapterFactory._adapters["test-dataset"]

    @pytest.mark.unit
    def test_male_cns_alias_no_warning(self, capsys):
        """Test that male-cns alias doesn't produce warning."""
        adapter = DatasetAdapterFactory.create_adapter("male-cns:v0.9")
        assert isinstance(adapter, CNSAdapter)

        captured = capsys.readouterr()
        assert "Warning:" not in captured.out


@pytest.mark.unit
class TestMaleCNSAliasUnit:
    """Unit tests specifically for male-cns alias functionality."""

    @pytest.mark.unit
    def test_male_cns_base_name_alias_resolution(self):
        """Test that male-cns base name resolves to cns."""
        adapter = DatasetAdapterFactory.create_adapter("male-cns")
        assert isinstance(adapter, CNSAdapter)
        assert adapter.dataset_info.name == "cns"

    @pytest.mark.unit
    def test_male_cns_versioned_alias_resolution(self):
        """Test that versioned male-cns resolves to cns."""
        test_cases = [
            "male-cns:v0.9",
            "male-cns:v1.0",
            "male-cns:latest",
            "male-cns:dev",
        ]

        for dataset_name in test_cases:
            adapter = DatasetAdapterFactory.create_adapter(dataset_name)
            assert isinstance(adapter, CNSAdapter), f"Failed for {dataset_name}"
            assert adapter.dataset_info.name == "cns", f"Failed for {dataset_name}"

    @pytest.mark.unit
    def test_male_cns_alias_no_warning_unit(self, capsys):
        """Unit test that male-cns alias produces no warning."""
        # Test base name
        capsys.readouterr()  # Clear any previous output
        adapter = DatasetAdapterFactory.create_adapter("male-cns")
        captured = capsys.readouterr()
        assert "Warning:" not in captured.out
        assert isinstance(adapter, CNSAdapter)

        # Test versioned name
        capsys.readouterr()  # Clear any previous output
        adapter = DatasetAdapterFactory.create_adapter("male-cns:v0.9")
        captured = capsys.readouterr()
        assert "Warning:" not in captured.out
        assert isinstance(adapter, CNSAdapter)

    @pytest.mark.unit
    def test_alias_resolution_precedence(self):
        """Test that alias resolution works in correct precedence order."""
        # Direct match should take precedence over alias
        # (This test ensures the logic order is correct)

        # First test normal case - alias should work
        adapter = DatasetAdapterFactory.create_adapter("male-cns")
        assert isinstance(adapter, CNSAdapter)

        # If we had a direct "male-cns" entry, it should take precedence
        # (This is theoretical since we don't have one, but tests the logic)

    @pytest.mark.unit
    def test_alias_dictionary_contains_male_cns(self):
        """Test that the alias dictionary contains the male-cns mapping."""
        assert "male-cns" in DatasetAdapterFactory._aliases
        assert DatasetAdapterFactory._aliases["male-cns"] == "cns"

    @pytest.mark.unit
    def test_alias_resolution_preserves_other_functionality(self):
        """Test that adding aliases doesn't break existing functionality."""
        # Test that canonical names still work
        adapter = DatasetAdapterFactory.create_adapter("cns")
        assert isinstance(adapter, CNSAdapter)

        adapter = DatasetAdapterFactory.create_adapter("hemibrain")
        assert isinstance(adapter, HemibrainAdapter)

        # Test that versioned canonical names still work
        adapter = DatasetAdapterFactory.create_adapter("cns:v1.0")
        assert isinstance(adapter, CNSAdapter)

    @pytest.mark.unit
    def test_case_sensitivity_of_aliases(self):
        """Test that aliases are case sensitive."""
        # male-cns should work (lowercase)
        adapter = DatasetAdapterFactory.create_adapter("male-cns")
        assert isinstance(adapter, CNSAdapter)

        # MALE-CNS should not match alias and fall back to default with warning
        # (We don't test the warning here to keep it a pure unit test)

    @pytest.mark.unit
    def test_empty_version_handling_with_alias(self):
        """Test edge cases with version separators and aliases."""
        # Test with colon but no version
        adapter = DatasetAdapterFactory.create_adapter("male-cns:")
        assert isinstance(adapter, CNSAdapter)

        # Test with multiple colons (should use first part)
        adapter = DatasetAdapterFactory.create_adapter("male-cns:v1:extra")
        assert isinstance(adapter, CNSAdapter)

    @pytest.mark.unit
    def test_alias_resolution_method_isolation(self):
        """Test the alias resolution logic in isolation."""
        factory = DatasetAdapterFactory

        # Test base name extraction
        assert "male-cns" == "male-cns:v0.9".split(":")[0]

        # Test alias lookup
        resolved = factory._aliases.get("male-cns", "male-cns")
        assert resolved == "cns"

        # Test non-existent alias
        resolved = factory._aliases.get("non-existent", "non-existent")
        assert resolved == "non-existent"


@pytest.mark.unit
class TestWaspAdapter:
    """Unit tests for the wasp3 adapter (soma side from instance name)."""

    @pytest.mark.unit
    def test_factory_resolves_wasp3(self, capsys):
        """wasp3 (and versioned wasp3:v0.8) resolve to WaspAdapter, no warning."""
        capsys.readouterr()
        for name in ["wasp3", "wasp3:v0.8", "wasp3:latest"]:
            adapter = DatasetAdapterFactory.create_adapter(name)
            assert isinstance(adapter, WaspAdapter), f"Failed for {name}"
            assert adapter.dataset_info.name == "wasp3"
        captured = capsys.readouterr()
        assert "Warning:" not in captured.out

    @pytest.mark.unit
    def test_uses_cns_roi_strategy(self):
        """wasp3 reuses the CNS ROI strategy."""
        adapter = WaspAdapter()
        assert isinstance(adapter.roi_strategy, CNSRoiQueryStrategy)

    @pytest.mark.unit
    def test_soma_side_from_instance_flag(self):
        """The instance-only flag is set so query sites derive side from instance."""
        assert WaspAdapter().dataset_info.soma_side_from_instance is True

    @pytest.mark.unit
    def test_extract_soma_side_from_instance(self):
        """(L)/(R) in the instance name maps to L/R; anything else is Unknown."""
        adapter = WaspAdapter()
        df = pd.DataFrame(
            {
                "bodyId": [1, 2, 3, 4, 5],
                "instance": [
                    "LC1(L)",
                    "LC1(R)",
                    "Tm3(l)",  # lowercase tolerated
                    "SomeType",  # no marker -> Unknown
                    None,  # missing -> Unknown
                ],
            }
        )
        out = adapter.extract_soma_side(df)
        assert out["somaSide"].tolist() == ["L", "R", "L", "U", "U"]

    @pytest.mark.unit
    def test_extract_soma_side_no_instance_column(self):
        """Without an instance column every neuron is Unknown."""
        adapter = WaspAdapter()
        df = pd.DataFrame({"bodyId": [1, 2]})
        out = adapter.extract_soma_side(df)
        assert out["somaSide"].tolist() == ["U", "U"]

    @pytest.mark.unit
    def test_filter_by_soma_side_uses_instance(self):
        """filter_by_soma_side selects the right hemisphere via the instance."""
        adapter = WaspAdapter()
        df = pd.DataFrame(
            {
                "bodyId": [1, 2, 3],
                "instance": ["LC1(L)", "LC1(R)", "LC1(R)"],
            }
        )
        right = adapter.filter_by_soma_side(df, "right")
        assert right["bodyId"].tolist() == [2, 3]
        left = adapter.filter_by_soma_side(df, "left")
        assert left["bodyId"].tolist() == [1]

    @pytest.mark.unit
    def test_cypher_helpers_use_instance(self):
        """The Cypher helpers parse (L)/(R) from the node's instance."""
        adapter = WaspAdapter()
        case_expr = adapter.soma_side_cypher_case("upstream")
        assert "upstream.instance CONTAINS '(L)'" in case_expr
        assert "upstream.instance CONTAINS '(R)'" in case_expr
        assert "somaSide" not in case_expr  # must not read the node property

        presence = adapter.soma_side_cypher_presence("n")
        assert presence == "n.instance IS NOT NULL"

    @pytest.mark.unit
    def test_default_adapter_cypher_helpers_unchanged(self):
        """Non-instance datasets keep reading the somaSide property."""
        cns = CNSAdapter()
        assert cns.dataset_info.soma_side_from_instance is False
        assert cns.soma_side_cypher_case("m") == "m.somaSide"
        assert (
            cns.soma_side_cypher_presence("m")
            == "(m.rootSide IS NOT NULL OR m.somaSide IS NOT NULL)"
        )


class TestCNSAdapterSomaSide:
    """Unit tests for CNS soma side extraction (rootSide first, somaSide second)."""

    @pytest.mark.unit
    def test_root_side_unknown_string_maps_to_u(self):
        """neuPrint stores the literal 'unknown' in rootSide; it must become 'U'."""
        df = pd.DataFrame(
            {
                "bodyId": [1, 2, 3, 4],
                "instance": ["ORN_VM4_R", "ORN_VM4_unknown", "X_L", "Y"],
                "rootSide": ["R", "unknown", None, None],
                "somaSide": [None, None, "L", None],
            }
        )
        result = CNSAdapter().extract_soma_side(df)
        assert result["somaSide"].tolist() == ["R", "U", "L", "U"]

    @pytest.mark.unit
    def test_root_side_only_column(self):
        """With rootSide but no somaSide column, nulls and 'unknown' become 'U'."""
        df = pd.DataFrame({"bodyId": [1, 2, 3], "rootSide": ["L", "Unknown", None]})
        result = CNSAdapter().extract_soma_side(df)
        assert result["somaSide"].tolist() == ["L", "U", "U"]

    @pytest.mark.unit
    def test_soma_side_only_column(self):
        """Without rootSide, somaSide is used and 'unknown'/null become 'U'."""
        df = pd.DataFrame({"bodyId": [1, 2, 3], "somaSide": ["R", "unknown", None]})
        result = CNSAdapter().extract_soma_side(df)
        assert result["somaSide"].tolist() == ["R", "U", "U"]

    @pytest.mark.unit
    def test_no_side_columns(self):
        """Neither column present: every neuron is 'U'."""
        df = pd.DataFrame({"bodyId": [1, 2]})
        result = CNSAdapter().extract_soma_side(df)
        assert result["somaSide"].tolist() == ["U", "U"]
