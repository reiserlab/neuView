"""
Tests for Template Context Service

Tests the preparation of template context data, specifically focusing on
the summary statistics calculation methods that were moved from templates.
"""

from unittest.mock import MagicMock, Mock

import pytest

from neuview.services.template_context_service import TemplateContextService


@pytest.fixture
def mock_page_generator():
    """Create a mock page generator with required attributes."""
    mock_gen = Mock()
    mock_gen.text_utils = Mock()
    mock_gen.citations = Mock()
    mock_gen.config = {"test": "config"}
    mock_gen.output_dir = "/tmp/test_output"
    return mock_gen


@pytest.fixture
def service(mock_page_generator):
    """Create a TemplateContextService instance with mocked dependencies."""
    return TemplateContextService(mock_page_generator)


class TestPrepareSideSpecificStats:
    """Tests for side-specific (L/R/M) summary statistics preparation."""

    def test_prepare_side_summary_stats_left(self, service):
        """Test calculation of left side statistics."""
        summary = {
            "total_post_synapses": 1000,
            "total_pre_synapses": 500,
        }

        complete_summary = {
            "left_count": 10,
            "left_pre_synapses": 500,
            "left_post_synapses": 1000,
            "right_count": 8,
            "right_pre_synapses": 400,
            "right_post_synapses": 800,
        }

        connectivity = {
            "total_upstream": 150,
            "total_downstream": 200,
            "avg_connections": 35.0,
            "avg_upstream": 15.0,
            "avg_downstream": 20.0,
        }

        result = service._prepare_side_summary_stats(
            summary, complete_summary, connectivity, "left"
        )

        # Check neuron counts
        assert result["side_neuron_count"] == 10
        assert result["side_pre_synapses"] == 500
        assert result["side_post_synapses"] == 1000

        # Check averages (1500 total synapses / 10 neurons)
        assert result["side_avg_pre"] == 50.0
        assert result["side_avg_post"] == 100.0
        assert result["side_avg_total"] == 150.0

        # Check synapse totals
        assert result["total_synapses"] == 1500
        assert result["total_post_synapses"] == 1000
        assert result["total_pre_synapses"] == 500

        # Check connection statistics
        assert result["total_connections"] == 350
        assert result["upstream_connections"] == 150
        assert result["downstream_connections"] == 200
        assert result["avg_connections"] == 35.0

    def test_prepare_side_summary_stats_right(self, service):
        """Test calculation of right side statistics."""
        summary = {
            "total_post_synapses": 800,
            "total_pre_synapses": 400,
        }

        complete_summary = {
            "left_count": 10,
            "left_pre_synapses": 500,
            "left_post_synapses": 1000,
            "right_count": 8,
            "right_pre_synapses": 400,
            "right_post_synapses": 800,
        }

        connectivity = {
            "total_upstream": 120,
            "total_downstream": 160,
            "avg_connections": 35.0,
            "avg_upstream": 15.0,
            "avg_downstream": 20.0,
        }

        result = service._prepare_side_summary_stats(
            summary, complete_summary, connectivity, "right"
        )

        # Check neuron counts
        assert result["side_neuron_count"] == 8
        assert result["side_pre_synapses"] == 400
        assert result["side_post_synapses"] == 800

        # Check averages (1200 total synapses / 8 neurons)
        assert result["side_avg_pre"] == 50.0
        assert result["side_avg_post"] == 100.0
        assert result["side_avg_total"] == 150.0

    def test_prepare_side_summary_stats_middle(self, service):
        """Test calculation of middle side statistics."""
        summary = {
            "total_post_synapses": 200,
            "total_pre_synapses": 100,
        }

        complete_summary = {
            "middle_count": 5,
            "middle_pre_synapses": 100,
            "middle_post_synapses": 200,
        }

        connectivity = {
            "total_upstream": 50,
            "total_downstream": 75,
            "avg_connections": 25.0,
            "avg_upstream": 10.0,
            "avg_downstream": 15.0,
        }

        result = service._prepare_side_summary_stats(
            summary, complete_summary, connectivity, "middle"
        )

        # Check neuron counts
        assert result["side_neuron_count"] == 5
        assert result["side_pre_synapses"] == 100
        assert result["side_post_synapses"] == 200

        # Check averages (300 total synapses / 5 neurons)
        assert result["side_avg_pre"] == 20.0
        assert result["side_avg_post"] == 40.0
        assert result["side_avg_total"] == 60.0

    def test_prepare_side_summary_stats_zero_neurons(self, service):
        """Test that averages are 0 when neuron count is 0."""
        summary = {
            "total_post_synapses": 0,
            "total_pre_synapses": 0,
        }

        complete_summary = {
            "left_count": 0,
            "left_pre_synapses": 0,
            "left_post_synapses": 0,
        }

        connectivity = {
            "total_upstream": 0,
            "total_downstream": 0,
            "avg_connections": 0,
            "avg_upstream": 0,
            "avg_downstream": 0,
        }

        result = service._prepare_side_summary_stats(
            summary, complete_summary, connectivity, "left"
        )

        # Check that averages are 0, not divide-by-zero errors
        assert result["side_avg_pre"] == 0
        assert result["side_avg_post"] == 0
        assert result["side_avg_total"] == 0

    def test_prepare_side_summary_stats_missing_keys(self, service):
        """Test handling of missing keys in dictionaries."""
        summary = {}
        complete_summary = {}
        connectivity = {}

        result = service._prepare_side_summary_stats(
            summary, complete_summary, connectivity, "left"
        )

        # Should return all zeros for missing keys
        assert result["side_neuron_count"] == 0
        assert result["side_pre_synapses"] == 0
        assert result["side_post_synapses"] == 0
        assert result["side_avg_pre"] == 0
        assert result["side_avg_post"] == 0
        assert result["side_avg_total"] == 0

    def test_prepare_side_summary_stats_invalid_side(self, service):
        """Test handling of invalid soma side."""
        summary = {}
        complete_summary = {}
        connectivity = {}

        result = service._prepare_side_summary_stats(
            summary, complete_summary, connectivity, "invalid"
        )

        # Should return empty dict for invalid side
        assert result == {}


class TestPrepareCombinedStats:
    """Tests for combined (C) page summary statistics preparation."""

    def test_prepare_combined_summary_stats(self, service):
        """Test calculation of combined statistics."""
        complete_summary = {
            "total_count": 25,
            "left_count": 10,
            "right_count": 12,
            "middle_count": 3,
            "total_post_synapses": 2500,
            "total_pre_synapses": 1500,
            "left_pre_synapses": 600,
            "left_post_synapses": 1000,
            "right_pre_synapses": 720,
            "right_post_synapses": 1200,
            "middle_pre_synapses": 180,
            "middle_post_synapses": 300,
            "avg_post_synapses": 100.0,
            "avg_pre_synapses": 60.0,
        }

        connectivity = {
            "total_upstream": 500,
            "total_downstream": 600,
            "avg_connections": 44.0,
            "avg_upstream": 20.0,
            "avg_downstream": 24.0,
        }

        result = service._prepare_combined_summary_stats(complete_summary, connectivity)

        # Check neuron counts
        assert result["left_count"] == 10
        assert result["right_count"] == 12
        assert result["middle_count"] == 3

        # Check total synapses
        assert result["total_synapses"] == 4000

        # Check hemisphere synapse totals
        assert result["right_synapses"] == 1920  # 720 + 1200
        assert result["left_synapses"] == 1600  # 600 + 1000
        assert result["middle_synapses"] == 480  # 180 + 300

        # Check individual components
        assert result["right_pre_synapses"] == 720
        assert result["right_post_synapses"] == 1200
        assert result["left_pre_synapses"] == 600
        assert result["left_post_synapses"] == 1000
        assert result["middle_pre_synapses"] == 180
        assert result["middle_post_synapses"] == 300

        # Check averages per neuron by side
        assert result["right_avg"] == 160.0  # 1920 / 12
        assert result["left_avg"] == 160.0  # 1600 / 10
        assert result["middle_avg"] == 160.0  # 480 / 3
        assert result["avg_synapses"] == 160.0  # 100 + 60

        # Check connection statistics
        assert result["total_connections"] == 1100
        assert result["upstream_connections"] == 500
        assert result["downstream_connections"] == 600
        assert result["avg_connections"] == 44.0

    def test_prepare_combined_summary_stats_zero_counts(self, service):
        """Test combined stats when some side counts are zero."""
        complete_summary = {
            "left_count": 10,
            "right_count": 0,
            "middle_count": 0,
            "total_post_synapses": 1000,
            "total_pre_synapses": 500,
            "left_pre_synapses": 500,
            "left_post_synapses": 1000,
            "right_pre_synapses": 0,
            "right_post_synapses": 0,
            "middle_pre_synapses": 0,
            "middle_post_synapses": 0,
            "avg_post_synapses": 100.0,
            "avg_pre_synapses": 50.0,
        }

        connectivity = {
            "total_upstream": 100,
            "total_downstream": 150,
            "avg_connections": 25.0,
            "avg_upstream": 10.0,
            "avg_downstream": 15.0,
        }

        result = service._prepare_combined_summary_stats(complete_summary, connectivity)

        # Check that zero counts result in zero averages
        assert result["left_avg"] == 150.0  # 1500 / 10
        assert result["right_avg"] == 0  # 0 / 0 (handled)
        assert result["middle_avg"] == 0  # 0 / 0 (handled)

    def test_prepare_combined_summary_stats_missing_keys(self, service):
        """Test handling of missing keys in combined stats."""
        complete_summary = {}
        connectivity = {}

        result = service._prepare_combined_summary_stats(complete_summary, connectivity)

        # Should return zeros for missing keys
        assert result["left_count"] == 0
        assert result["right_count"] == 0
        assert result["middle_count"] == 0
        assert result["total_synapses"] == 0
        assert result["right_synapses"] == 0
        assert result["left_synapses"] == 0


class TestPrepareSummaryStatistics:
    """Tests for the main prepare_summary_statistics method."""

    def test_prepare_summary_statistics_for_left_side(self, service):
        """Test that left side calls the correct preparation method."""
        summary = {"total_post_synapses": 1000, "total_pre_synapses": 500}
        complete_summary = {
            "left_count": 10,
            "left_pre_synapses": 500,
            "left_post_synapses": 1000,
        }
        connectivity = {
            "total_upstream": 100,
            "total_downstream": 150,
            "avg_connections": 25.0,
            "avg_upstream": 10.0,
            "avg_downstream": 15.0,
        }

        result = service.prepare_summary_statistics(
            summary, complete_summary, connectivity, "left"
        )

        # Should have side-specific keys
        assert "side_neuron_count" in result
        assert "side_avg_total" in result
        assert result["side_neuron_count"] == 10

    def test_prepare_summary_statistics_for_combined(self, service):
        """Test that combined side calls the correct preparation method."""
        summary = {}
        complete_summary = {
            "left_count": 10,
            "right_count": 12,
            "middle_count": 3,
            "total_post_synapses": 2500,
            "total_pre_synapses": 1500,
            "left_pre_synapses": 600,
            "left_post_synapses": 1000,
            "right_pre_synapses": 720,
            "right_post_synapses": 1200,
            "middle_pre_synapses": 180,
            "middle_post_synapses": 300,
            "avg_post_synapses": 100.0,
            "avg_pre_synapses": 60.0,
        }
        connectivity = {
            "total_upstream": 500,
            "total_downstream": 600,
            "avg_connections": 44.0,
            "avg_upstream": 20.0,
            "avg_downstream": 24.0,
        }

        result = service.prepare_summary_statistics(
            summary, complete_summary, connectivity, "combined"
        )

        # Should have combined-specific keys
        assert "left_count" in result
        assert "right_count" in result
        assert "middle_count" in result
        assert "right_avg" in result
        assert "left_avg" in result
        assert result["left_count"] == 10
        assert result["right_count"] == 12

    def test_prepare_summary_statistics_invalid_soma_side(self, service):
        """Test handling of invalid soma_side parameter."""
        summary = {}
        complete_summary = {}
        connectivity = {}

        result = service.prepare_summary_statistics(
            summary, complete_summary, connectivity, "invalid"
        )

        # Should return empty dict for invalid soma_side
        assert result == {}

    def test_prepare_summary_statistics_for_all_sides(self, service):
        """Test that all valid sides work correctly."""
        summary = {"total_post_synapses": 100, "total_pre_synapses": 50}
        complete_summary = {
            "left_count": 5,
            "left_pre_synapses": 50,
            "left_post_synapses": 100,
            "right_count": 5,
            "right_pre_synapses": 50,
            "right_post_synapses": 100,
            "middle_count": 5,
            "middle_pre_synapses": 50,
            "middle_post_synapses": 100,
            "total_post_synapses": 300,
            "total_pre_synapses": 150,
            "avg_post_synapses": 20.0,
            "avg_pre_synapses": 10.0,
        }
        connectivity = {
            "total_upstream": 50,
            "total_downstream": 75,
            "avg_connections": 25.0,
            "avg_upstream": 10.0,
            "avg_downstream": 15.0,
        }

        # Test each valid side
        for side in ["left", "right", "middle", "combined"]:
            result = service.prepare_summary_statistics(
                summary, complete_summary, connectivity, side
            )
            assert result is not None
            assert isinstance(result, dict)
            assert len(result) > 0


class TestIntegrationWithPrepareNeuronPageContext:
    """Test that summary statistics are properly integrated into page context."""

    def test_summary_stats_added_to_context(self, service, mock_page_generator):
        """Test that summary_stats is added to the context dictionary."""
        # Mock the page generator methods
        mock_page_generator._find_youtube_video = Mock(return_value=None)

        # Mock the combination services
        service.connectivity_combination_service.process_connectivity_for_display = (
            Mock(return_value={"total_upstream": 100, "total_downstream": 150})
        )
        service.roi_combination_service.process_roi_data_for_display = Mock(
            return_value={}
        )

        neuron_data = {
            "neurons": Mock(empty=True),
            "summary": {
                "total_post_synapses": 1000,
                "total_pre_synapses": 500,
            },
            "complete_summary": {
                "left_count": 10,
                "left_pre_synapses": 500,
                "left_post_synapses": 1000,
                "total_count": 10,
            },
            "connectivity": {
                "total_upstream": 100,
                "total_downstream": 150,
                "avg_connections": 25.0,
                "avg_upstream": 10.0,
                "avg_downstream": 15.0,
            },
        }

        context = service.prepare_neuron_page_context(
            neuron_type="Test",
            neuron_data=neuron_data,
            soma_side="left",
        )

        # Check that summary_stats is in the context
        assert "summary_stats" in context
        assert isinstance(context["summary_stats"], dict)

        # Check that it has the expected keys for a side page
        assert "side_neuron_count" in context["summary_stats"]
        assert "side_avg_total" in context["summary_stats"]
