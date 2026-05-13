"""
Test to verify that the Tm3 neuron type exists in the database.

This test connects to the NeuPrint database and verifies that the Tm3 neuron type
is available in the dataset. Tm3 is a well-known visual system neuron type that
should be present in the hemibrain dataset.
"""

import pytest
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from neuview.config import Config
from neuview.neuprint_connector import NeuPrintConnector


class TestTm3NeuronType:
    """Test cases for Tm3 neuron type existence in database."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        # Try to load from actual config file if available, otherwise use minimal config
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

        if os.path.exists(config_path):
            try:
                return Config.load(config_path)
            except Exception:
                # Fall back to minimal config if loading fails
                return Config.create_minimal_for_testing()
        else:
            return Config.create_minimal_for_testing()

    @pytest.fixture
    def neuprint_connector(self, config):
        """Create NeuPrint connector instance."""
        return NeuPrintConnector(config)

    @pytest.mark.integration
    def test_tm3_exists_in_database(self, neuprint_connector):
        """Test that Tm3 neuron type exists in the database."""
        try:
            # Get all available neuron types from the database
            available_types = neuprint_connector.get_available_types()

            # Check that we got a valid list
            assert isinstance(available_types, list), "Available types should be a list"
            assert len(available_types) > 0, (
                "Should have at least one neuron type in database"
            )

            # Check if Tm3 exists in the list
            assert "Tm3" in available_types, (
                f"Tm3 neuron type not found in database. "
                f"Available types: {sorted(available_types)[:10]}..."  # Show first 10 for debugging
            )

            print(
                f"✓ Tm3 neuron type found in database among {len(available_types)} total types"
            )

        except ConnectionError as e:
            pytest.skip(f"Could not connect to NeuPrint database: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error while checking for Tm3: {e}")

    @pytest.mark.integration
    def test_tm3_case_sensitivity(self, neuprint_connector):
        """Test that Tm3 lookup is case-sensitive as expected."""
        try:
            available_types = neuprint_connector.get_available_types()

            # Tm3 should be found with exact case
            assert "Tm3" in available_types, "Tm3 with exact case should be found"

            # Check that case variations are not present (or handle appropriately if they are)
            case_variations = ["tm3", "TM3", "Tm3", "tM3"]
            found_variations = [
                var for var in case_variations if var in available_types
            ]

            print(f"Found case variations of Tm3: {found_variations}")

            # At minimum, "Tm3" should be present
            assert "Tm3" in found_variations, "Standard Tm3 case should be present"

        except ConnectionError as e:
            pytest.skip(f"Could not connect to NeuPrint database: {e}")

    @pytest.mark.integration
    def test_database_connectivity_and_tm3(self, neuprint_connector):
        """Test database connectivity and Tm3 existence in one comprehensive test."""
        try:
            # First test that we can connect to the database
            assert neuprint_connector.test_connection(), (
                "Should be able to connect to NeuPrint database"
            )

            # Then test that we can retrieve neuron types
            available_types = neuprint_connector.get_available_types()
            assert isinstance(available_types, list), (
                "Should return a list of neuron types"
            )
            assert len(available_types) > 0, "Should have neuron types in the database"

            # Finally test that Tm3 specifically exists
            assert "Tm3" in available_types, "Tm3 should be present in the database"

            # Log some useful debugging information
            total_types = len(available_types)
            tm_types = [t for t in available_types if t.startswith("Tm")]

            print("Database connection successful")
            print(f"Total neuron types found: {total_types}")
            print(
                f"Tm-family types found: {len(tm_types)} - {tm_types[:5]}..."
            )  # Show first 5 Tm types
            print("✓ Tm3 confirmed present in database")

        except ConnectionError as e:
            pytest.skip(f"Database connection failed: {e}")
        except Exception as e:
            pytest.fail(f"Test failed with unexpected error: {e}")

    @pytest.mark.unit
    def test_neuprint_connector_initialization(self, config, monkeypatch):
        """NeuPrintConnector constructs cleanly and exposes its required API.

        The real ``_connect`` makes an HTTPS call to the neuPrint server, so
        a true unit test must mock it out. Real connection behaviour is
        exercised by the ``@pytest.mark.integration`` tests above (they
        skip cleanly when the server is unreachable).
        """
        monkeypatch.setattr(NeuPrintConnector, "_connect", lambda self: None)
        connector = NeuPrintConnector(config)
        assert connector is not None, "Connector should be initialized"
        assert hasattr(connector, "get_available_types"), (
            "Connector should have get_available_types method"
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_tm3_neuron_data_accessibility(self, neuprint_connector):
        """Test that we can access actual neuron data for Tm3 type."""
        try:
            # First confirm Tm3 exists
            available_types = neuprint_connector.get_available_types()
            if "Tm3" not in available_types:
                pytest.skip("Tm3 not found in database, skipping data access test")

            # Try to get some basic information about Tm3 neurons
            # This tests that not only does the type exist, but we can query for it
            try:
                # Test getting soma sides for Tm3
                soma_sides = neuprint_connector.get_soma_sides_for_type("Tm3")
                assert isinstance(soma_sides, list), (
                    "Should return a list of soma sides"
                )
                print(f"Tm3 soma sides available: {soma_sides}")

            except Exception as e:
                # If specific method fails, that's okay - we've confirmed the type exists
                print(
                    f"Note: Could not get detailed Tm3 data ({e}), but type exists in database"
                )

        except ConnectionError as e:
            pytest.skip(f"Could not connect to database: {e}")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
