"""
Tests for URL Generation Service

This module tests the URLGenerationService class, particularly the template
selection logic for different datasets.
"""

from unittest.mock import Mock, patch
from jinja2 import Environment, DictLoader

from neuview.services.url_generation_service import URLGenerationService


class MockConfig:
    """Mock configuration object for testing."""

    def __init__(self, dataset="hemibrain:v1.2.1", template="neuroglancer.js.jinja"):
        self.neuprint = Mock()
        self.neuprint.dataset = dataset
        self.neuprint.server = "neuprint.janelia.org"

        self.neuroglancer = Mock()
        self.neuroglancer.base_url = "https://clio-ng.janelia.org/"
        self.neuroglancer.template = template


class TestURLGenerationService:
    """Test cases for URLGenerationService."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create mock templates
        self.templates = {
            "neuroglancer.js.jinja": """{"title": "{{ website_title }}", "dataset": "standard"}""",
            "neuroglancer-fafb.js.jinja": """{"title": "{{ website_title }}", "dataset": "fafb"}""",
        }

        # Create Jinja environment with mock templates
        self.jinja_env = Environment(loader=DictLoader(self.templates))

        # Create mock services
        self.neuron_selection_service = Mock()
        self.database_query_service = Mock()

    def create_service(
        self, dataset="hemibrain:v1.2.1", template="neuroglancer.js.jinja"
    ):
        """Create URLGenerationService with specified dataset."""
        config = MockConfig(dataset, template)
        return URLGenerationService(
            config=config,
            jinja_env=self.jinja_env,
            neuron_selection_service=self.neuron_selection_service,
            database_query_service=self.database_query_service,
        )

    def test_uses_configured_standard_template(self):
        """Standard template is used when configured."""
        service = self.create_service(template="neuroglancer.js.jinja")

        # Mock neuron data
        neuron_data = {"neurons": None}

        # Mock the neuron selection service to return empty list
        self.neuron_selection_service.select_bodyids_by_soma_side.return_value = []

        # Mock the database query service to return empty connections
        self.database_query_service.get_connected_bodyids.return_value = {
            "upstream": {},
            "downstream": {},
        }

        url, template_vars = service.generate_neuroglancer_url("TestType", neuron_data)

        # Verify the URL was generated (not the fallback)
        expected_base = service.config.neuroglancer.base_url.rstrip("/")
        assert url.startswith(f"{expected_base}/#!")

        # Verify template variables indicate standard template was used
        assert template_vars["website_title"] == "TestType"

    def test_uses_configured_fafb_template(self):
        """FAFB template is used when configured."""
        service = self.create_service(
            dataset="flywire-fafb:v783b", template="neuroglancer-fafb.js.jinja"
        )

        # Mock neuron data
        neuron_data = {"neurons": None}

        # Mock the neuron selection service to return empty list
        self.neuron_selection_service.select_bodyids_by_soma_side.return_value = []

        # Mock the database query service to return empty connections
        self.database_query_service.get_connected_bodyids.return_value = {
            "upstream": {},
            "downstream": {},
        }

        url, template_vars = service.generate_neuroglancer_url("TestType", neuron_data)

        # Verify the URL was generated (not the fallback)
        expected_base = service.config.neuroglancer.base_url.rstrip("/")
        assert url.startswith(f"{expected_base}/#!")

        # Verify template variables
        assert template_vars["website_title"] == "TestType"

    @patch("neuview.services.url_generation_service.logger")
    def test_logs_template_selection(self, mock_logger):
        """Test that template selection is logged."""
        service = self.create_service(
            dataset="flywire-fafb:v783b", template="neuroglancer-fafb.js.jinja"
        )

        # Mock dependencies
        neuron_data = {"neurons": None}
        self.neuron_selection_service.select_bodyids_by_soma_side.return_value = []
        self.database_query_service.get_connected_bodyids.return_value = {
            "upstream": {},
            "downstream": {},
        }

        service.generate_neuroglancer_url("TestType", neuron_data)

        # Verify logging was called
        mock_logger.debug.assert_called_with(
            "Using Neuroglancer template: neuroglancer-fafb.js.jinja for dataset: flywire-fafb:v783b"
        )

    def test_fallback_on_template_error(self):
        """Test that fallback URL is returned when template processing fails."""
        # Create service with missing template to trigger error
        service = self.create_service("flywire-fafb:v783b")
        service.env = Environment(loader=DictLoader({}))  # Empty template loader

        neuron_data = {"neurons": None}

        url, template_vars = service.generate_neuroglancer_url("TestType", neuron_data)

        # Should return fallback URL
        expected_base = service.config.neuroglancer.base_url.rstrip("/")
        assert url == f"{expected_base}/"
        assert template_vars["website_title"] == "TestType"
        assert template_vars["visible_neurons"] == []

    def test_template_variables_passed_correctly(self):
        """Test that all required template variables are passed to the template."""
        service = self.create_service(
            dataset="flywire-fafb:v783b", template="neuroglancer-fafb.js.jinja"
        )

        # Create mock neuron DataFrame
        import pandas as pd

        mock_neurons_df = pd.DataFrame(
            {"bodyId": [123, 456, 789], "type": ["TestType", "TestType", "TestType"]}
        )

        neuron_data = {"neurons": mock_neurons_df}

        # Mock services
        self.neuron_selection_service.select_bodyids_by_soma_side.return_value = [
            123,
            456,
        ]
        self.database_query_service.get_connected_bodyids.return_value = {
            "upstream": {"TypeA": [111]},
            "downstream": {"TypeB": [222]},
        }

        url, template_vars = service.generate_neuroglancer_url(
            "TestType", neuron_data, "left"
        )

        # Verify all expected template variables are present
        expected_vars = [
            "website_title",
            "visible_neurons",
            "neuron_query",
            "visible_rois",
            "connected_bids",
        ]
        for var in expected_vars:
            assert var in template_vars

        assert template_vars["website_title"] == "TestType"
        assert template_vars["visible_neurons"] == ["123", "456"]
        assert template_vars["neuron_query"] == "TestType"
        assert template_vars["connected_bids"] == {
            "upstream": {"TypeA": [111]},
            "downstream": {"TypeB": [222]},
        }
