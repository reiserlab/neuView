"""Tests for statistics calculators.

This module tests the calculator classes that compute statistics from raw data.
"""

import pytest

from neuview.services.statistics_calculator import (
    CombinedStatisticsCalculator,
    SideStatisticsCalculator,
)
from neuview.services.statistics_models import (
    CombinedStatistics,
    ConnectionStatistics,
    HemisphereNeuronCounts,
    HemisphereSynapses,
    SideStatistics,
)


class TestCombinedStatisticsCalculator:
    """Tests for CombinedStatisticsCalculator."""

    def test_calculate_full_statistics(self):
        """Test calculation of complete combined statistics."""
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
            "total_left": 250,
            "total_right": 300,
        }

        calculator = CombinedStatisticsCalculator(complete_summary, connectivity)
        stats = calculator.calculate()

        # Verify it returns a CombinedStatistics object
        assert isinstance(stats, CombinedStatistics)

        # Check neuron counts
        assert stats.neuron_counts.left == 10
        assert stats.neuron_counts.right == 12
        assert stats.neuron_counts.middle == 3

        # Check synapse statistics
        assert stats.left_synapses.pre_synapses == 600
        assert stats.left_synapses.post_synapses == 1000
        assert stats.right_synapses.pre_synapses == 720
        assert stats.right_synapses.post_synapses == 1200
        assert stats.middle_synapses.pre_synapses == 180
        assert stats.middle_synapses.post_synapses == 300

        # Check connections
        assert stats.connections.total_upstream == 500
        assert stats.connections.total_downstream == 600
        assert stats.total_left_connections == 250
        assert stats.total_right_connections == 300

        # Check average synapses
        assert stats.avg_synapses == 160.0  # 100 + 60

    def test_extract_neuron_counts(self):
        """Test extraction of neuron counts."""
        complete_summary = {
            "left_count": 10,
            "right_count": 12,
            "middle_count": 3,
        }
        connectivity = {}

        calculator = CombinedStatisticsCalculator(complete_summary, connectivity)
        counts = calculator._extract_neuron_counts()

        assert isinstance(counts, HemisphereNeuronCounts)
        assert counts.left == 10
        assert counts.right == 12
        assert counts.middle == 3
        assert counts.total == 25

    def test_extract_neuron_counts_missing_keys(self):
        """Test extraction when keys are missing."""
        complete_summary = {}
        connectivity = {}

        calculator = CombinedStatisticsCalculator(complete_summary, connectivity)
        counts = calculator._extract_neuron_counts()

        assert counts.left == 0
        assert counts.right == 0
        assert counts.middle == 0

    def test_calculate_hemisphere_synapses(self):
        """Test calculation of hemisphere-specific synapses."""
        complete_summary = {
            "left_pre_synapses": 600,
            "left_post_synapses": 1000,
            "right_pre_synapses": 720,
            "right_post_synapses": 1200,
            "middle_pre_synapses": 180,
            "middle_post_synapses": 300,
        }
        connectivity = {}

        calculator = CombinedStatisticsCalculator(complete_summary, connectivity)

        left_synapses = calculator._calculate_hemisphere_synapses("left")
        assert isinstance(left_synapses, HemisphereSynapses)
        assert left_synapses.pre_synapses == 600
        assert left_synapses.post_synapses == 1000
        assert left_synapses.total_synapses == 1600

        right_synapses = calculator._calculate_hemisphere_synapses("right")
        assert right_synapses.pre_synapses == 720
        assert right_synapses.post_synapses == 1200
        assert right_synapses.total_synapses == 1920

        middle_synapses = calculator._calculate_hemisphere_synapses("middle")
        assert middle_synapses.pre_synapses == 180
        assert middle_synapses.post_synapses == 300
        assert middle_synapses.total_synapses == 480

    def test_calculate_hemisphere_synapses_missing_keys(self):
        """Test hemisphere synapse calculation with missing keys."""
        complete_summary = {}
        connectivity = {}

        calculator = CombinedStatisticsCalculator(complete_summary, connectivity)
        synapses = calculator._calculate_hemisphere_synapses("left")

        assert synapses.pre_synapses == 0
        assert synapses.post_synapses == 0
        assert synapses.total_synapses == 0

    def test_calculate_connection_stats(self):
        """Test calculation of connection statistics."""
        complete_summary = {}
        connectivity = {
            "total_upstream": 500,
            "total_downstream": 600,
            "avg_connections": 44.0,
            "avg_upstream": 20.0,
            "avg_downstream": 24.0,
        }

        calculator = CombinedStatisticsCalculator(complete_summary, connectivity)
        connections = calculator._calculate_connection_stats()

        assert isinstance(connections, ConnectionStatistics)
        assert connections.total_upstream == 500
        assert connections.total_downstream == 600
        assert connections.avg_connections == 44.0
        assert connections.avg_upstream == 20.0
        assert connections.avg_downstream == 24.0
        assert connections.total_connections == 1100

    def test_calculate_connection_stats_missing_keys(self):
        """Test connection statistics with missing keys."""
        complete_summary = {}
        connectivity = {}

        calculator = CombinedStatisticsCalculator(complete_summary, connectivity)
        connections = calculator._calculate_connection_stats()

        assert connections.total_upstream == 0
        assert connections.total_downstream == 0
        assert connections.avg_connections == 0.0
        assert connections.avg_upstream == 0.0
        assert connections.avg_downstream == 0.0

    def test_calculate_overall_avg_synapses(self):
        """Test calculation of overall average synapses."""
        complete_summary = {
            "avg_pre_synapses": 60.0,
            "avg_post_synapses": 100.0,
        }
        connectivity = {}

        calculator = CombinedStatisticsCalculator(complete_summary, connectivity)
        avg = calculator._calculate_overall_avg_synapses()

        assert avg == 160.0

    def test_calculate_overall_avg_synapses_missing_keys(self):
        """Test overall average synapses with missing keys."""
        complete_summary = {}
        connectivity = {}

        calculator = CombinedStatisticsCalculator(complete_summary, connectivity)
        avg = calculator._calculate_overall_avg_synapses()

        assert avg == 0.0

    def test_calculate_with_zero_counts(self):
        """Test calculation when some hemisphere counts are zero."""
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
            "total_left": 250,
            "total_right": 0,
        }

        calculator = CombinedStatisticsCalculator(complete_summary, connectivity)
        stats = calculator.calculate()

        # Zero counts should still work
        assert stats.neuron_counts.right == 0
        assert stats.right_synapses.total_synapses == 0

        # Convert to dict to verify averages handle zero division
        result = stats.to_template_dict()
        assert result["right_avg"] == 0.0
        assert result["right_avg_connections"] == 0.0


class TestSideStatisticsCalculator:
    """Tests for SideStatisticsCalculator."""

    def test_calculate_left_side(self):
        """Test calculation for left side statistics."""
        summary = {
            "total_post_synapses": 1000,
            "total_pre_synapses": 500,
        }
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

        calculator = SideStatisticsCalculator(
            summary, complete_summary, connectivity, "left"
        )
        stats = calculator.calculate()

        assert isinstance(stats, SideStatistics)
        assert stats.side_neuron_count == 10
        assert stats.side_pre_synapses == 500
        assert stats.side_post_synapses == 1000
        assert stats.total_pre_synapses == 500
        assert stats.total_post_synapses == 1000
        assert stats.connections.total_upstream == 100
        assert stats.connections.total_downstream == 150

    def test_calculate_right_side(self):
        """Test calculation for right side statistics."""
        summary = {
            "total_post_synapses": 1200,
            "total_pre_synapses": 720,
        }
        complete_summary = {
            "right_count": 12,
            "right_pre_synapses": 720,
            "right_post_synapses": 1200,
        }
        connectivity = {
            "total_upstream": 120,
            "total_downstream": 180,
            "avg_connections": 25.0,
            "avg_upstream": 10.0,
            "avg_downstream": 15.0,
        }

        calculator = SideStatisticsCalculator(
            summary, complete_summary, connectivity, "right"
        )
        stats = calculator.calculate()

        assert stats.side_neuron_count == 12
        assert stats.side_pre_synapses == 720
        assert stats.side_post_synapses == 1200

    def test_calculate_middle_side(self):
        """Test calculation for middle side statistics."""
        summary = {
            "total_post_synapses": 300,
            "total_pre_synapses": 180,
        }
        complete_summary = {
            "middle_count": 3,
            "middle_pre_synapses": 180,
            "middle_post_synapses": 300,
        }
        connectivity = {
            "total_upstream": 30,
            "total_downstream": 45,
            "avg_connections": 25.0,
            "avg_upstream": 10.0,
            "avg_downstream": 15.0,
        }

        calculator = SideStatisticsCalculator(
            summary, complete_summary, connectivity, "middle"
        )
        stats = calculator.calculate()

        assert stats.side_neuron_count == 3
        assert stats.side_pre_synapses == 180
        assert stats.side_post_synapses == 300

    def test_calculate_invalid_soma_side(self):
        """Test that invalid soma_side returns empty statistics."""
        summary = {}
        complete_summary = {}
        connectivity = {}

        calculator = SideStatisticsCalculator(
            summary, complete_summary, connectivity, "invalid"
        )
        stats = calculator.calculate()

        # Should return empty/zero statistics
        assert stats.side_neuron_count == 0
        assert stats.side_pre_synapses == 0
        assert stats.side_post_synapses == 0
        assert stats.total_pre_synapses == 0
        assert stats.total_post_synapses == 0

    def test_calculate_missing_keys(self):
        """Test calculation with missing keys in data."""
        summary = {}
        complete_summary = {}
        connectivity = {}

        calculator = SideStatisticsCalculator(
            summary, complete_summary, connectivity, "left"
        )
        stats = calculator.calculate()

        assert stats.side_neuron_count == 0
        assert stats.side_pre_synapses == 0
        assert stats.side_post_synapses == 0
        assert stats.total_pre_synapses == 0
        assert stats.total_post_synapses == 0
        assert stats.connections.total_upstream == 0

    def test_calculate_connection_stats(self):
        """Test extraction of connection statistics."""
        summary = {}
        complete_summary = {"left_count": 10}
        connectivity = {
            "total_upstream": 100,
            "total_downstream": 150,
            "avg_connections": 25.0,
            "avg_upstream": 10.0,
            "avg_downstream": 15.0,
        }

        calculator = SideStatisticsCalculator(
            summary, complete_summary, connectivity, "left"
        )
        connections = calculator._calculate_connection_stats()

        assert isinstance(connections, ConnectionStatistics)
        assert connections.total_upstream == 100
        assert connections.total_downstream == 150
        assert connections.avg_connections == 25.0
        assert connections.avg_upstream == 10.0
        assert connections.avg_downstream == 15.0

    def test_to_template_dict_integration(self):
        """Test full integration with to_template_dict."""
        summary = {
            "total_post_synapses": 1000,
            "total_pre_synapses": 500,
        }
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

        calculator = SideStatisticsCalculator(
            summary, complete_summary, connectivity, "left"
        )
        stats = calculator.calculate()
        result = stats.to_template_dict()

        # Check all expected keys exist
        assert "side_neuron_count" in result
        assert "side_pre_synapses" in result
        assert "side_post_synapses" in result
        assert "side_avg_pre" in result
        assert "side_avg_post" in result
        assert "side_avg_total" in result
        assert "total_synapses" in result
        assert "total_connections" in result

        # Check calculated values
        assert result["side_neuron_count"] == 10
        assert result["side_avg_pre"] == 50.0  # 500 / 10
        assert result["side_avg_post"] == 100.0  # 1000 / 10
        assert result["side_avg_total"] == 150.0  # 50 + 100
        assert result["total_connections"] == 250  # 100 + 150
