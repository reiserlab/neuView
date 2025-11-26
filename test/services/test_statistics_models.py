"""Tests for statistics models.

This module tests the dataclasses that represent statistics data structures.
"""

import pytest

from neuview.services.statistics_models import (
    CombinedStatistics,
    ConnectionStatistics,
    HemisphereNeuronCounts,
    HemisphereSynapses,
    SideStatistics,
)


class TestHemisphereSynapses:
    """Tests for HemisphereSynapses dataclass."""

    def test_total_synapses(self):
        """Test calculation of total synapses."""
        synapses = HemisphereSynapses(pre_synapses=100, post_synapses=200)
        assert synapses.total_synapses == 300

    def test_total_synapses_zero(self):
        """Test total synapses when both are zero."""
        synapses = HemisphereSynapses(pre_synapses=0, post_synapses=0)
        assert synapses.total_synapses == 0

    def test_average_per_neuron(self):
        """Test average synapses per neuron calculation."""
        synapses = HemisphereSynapses(pre_synapses=100, post_synapses=200)
        assert synapses.average_per_neuron(10) == 30.0

    def test_average_per_neuron_single_neuron(self):
        """Test average with single neuron."""
        synapses = HemisphereSynapses(pre_synapses=100, post_synapses=200)
        assert synapses.average_per_neuron(1) == 300.0

    def test_average_with_zero_neurons(self):
        """Test that zero neurons returns zero average."""
        synapses = HemisphereSynapses(pre_synapses=100, post_synapses=200)
        assert synapses.average_per_neuron(0) == 0.0

    def test_average_per_neuron_fractional(self):
        """Test average with fractional result."""
        synapses = HemisphereSynapses(pre_synapses=100, post_synapses=150)
        assert synapses.average_per_neuron(3) == pytest.approx(83.333, rel=1e-3)


class TestHemisphereNeuronCounts:
    """Tests for HemisphereNeuronCounts dataclass."""

    def test_total(self):
        """Test total neuron count calculation."""
        counts = HemisphereNeuronCounts(left=10, right=12, middle=3)
        assert counts.total == 25

    def test_total_with_zeros(self):
        """Test total when some counts are zero."""
        counts = HemisphereNeuronCounts(left=10, right=0, middle=0)
        assert counts.total == 10

    def test_total_all_zeros(self):
        """Test total when all counts are zero."""
        counts = HemisphereNeuronCounts(left=0, right=0, middle=0)
        assert counts.total == 0

    def test_individual_counts(self):
        """Test that individual counts are stored correctly."""
        counts = HemisphereNeuronCounts(left=10, right=12, middle=3)
        assert counts.left == 10
        assert counts.right == 12
        assert counts.middle == 3


class TestConnectionStatistics:
    """Tests for ConnectionStatistics dataclass."""

    def test_total_connections(self):
        """Test total connections calculation."""
        connections = ConnectionStatistics(
            total_upstream=500,
            total_downstream=600,
            avg_connections=44.0,
            avg_upstream=20.0,
            avg_downstream=24.0,
        )
        assert connections.total_connections == 1100

    def test_total_connections_zero(self):
        """Test total connections when both are zero."""
        connections = ConnectionStatistics(
            total_upstream=0,
            total_downstream=0,
            avg_connections=0.0,
            avg_upstream=0.0,
            avg_downstream=0.0,
        )
        assert connections.total_connections == 0

    def test_averages_stored(self):
        """Test that averages are stored correctly."""
        connections = ConnectionStatistics(
            total_upstream=500,
            total_downstream=600,
            avg_connections=44.0,
            avg_upstream=20.0,
            avg_downstream=24.0,
        )
        assert connections.avg_connections == 44.0
        assert connections.avg_upstream == 20.0
        assert connections.avg_downstream == 24.0


class TestCombinedStatistics:
    """Tests for CombinedStatistics dataclass."""

    @pytest.fixture
    def sample_stats(self):
        """Create sample combined statistics for testing."""
        return CombinedStatistics(
            neuron_counts=HemisphereNeuronCounts(left=10, right=12, middle=3),
            left_synapses=HemisphereSynapses(pre_synapses=600, post_synapses=1000),
            right_synapses=HemisphereSynapses(pre_synapses=720, post_synapses=1200),
            middle_synapses=HemisphereSynapses(pre_synapses=180, post_synapses=300),
            connections=ConnectionStatistics(
                total_upstream=500,
                total_downstream=600,
                avg_connections=44.0,
                avg_upstream=20.0,
                avg_downstream=24.0,
            ),
            total_left_connections=250,
            total_right_connections=300,
            avg_synapses=160.0,
        )

    def test_to_template_dict_neuron_counts(self, sample_stats):
        """Test that neuron counts are included in template dict."""
        result = sample_stats.to_template_dict()
        assert result["left_count"] == 10
        assert result["right_count"] == 12
        assert result["middle_count"] == 3

    def test_to_template_dict_total_synapses(self, sample_stats):
        """Test that total synapses are calculated correctly."""
        result = sample_stats.to_template_dict()
        # 1600 (left) + 1920 (right) + 480 (middle) = 4000
        assert result["total_synapses"] == 4000

    def test_to_template_dict_hemisphere_synapses(self, sample_stats):
        """Test that hemisphere synapse totals are correct."""
        result = sample_stats.to_template_dict()
        assert result["right_synapses"] == 1920  # 720 + 1200
        assert result["left_synapses"] == 1600  # 600 + 1000
        assert result["middle_synapses"] == 480  # 180 + 300

    def test_to_template_dict_hemisphere_components(self, sample_stats):
        """Test that individual pre/post synapses are included."""
        result = sample_stats.to_template_dict()
        assert result["right_pre_synapses"] == 720
        assert result["right_post_synapses"] == 1200
        assert result["left_pre_synapses"] == 600
        assert result["left_post_synapses"] == 1000
        assert result["middle_pre_synapses"] == 180
        assert result["middle_post_synapses"] == 300

    def test_to_template_dict_averages(self, sample_stats):
        """Test that averages per neuron are calculated correctly."""
        result = sample_stats.to_template_dict()
        assert result["right_avg"] == 160.0  # 1920 / 12
        assert result["left_avg"] == 160.0  # 1600 / 10
        assert result["middle_avg"] == 160.0  # 480 / 3
        assert result["avg_synapses"] == 160.0

    def test_to_template_dict_connections(self, sample_stats):
        """Test that connection statistics are included."""
        result = sample_stats.to_template_dict()
        assert result["total_connections"] == 1100
        assert result["upstream_connections"] == 500
        assert result["downstream_connections"] == 600
        assert result["avg_connections"] == 44.0
        assert result["avg_upstream"] == 20.0
        assert result["avg_downstream"] == 24.0

    def test_to_template_dict_hemisphere_connection_averages(self, sample_stats):
        """Test that hemisphere-specific connection averages are calculated."""
        result = sample_stats.to_template_dict()
        assert result["left_avg_connections"] == 25.0  # 250 / 10
        assert result["right_avg_connections"] == 25.0  # 300 / 12

    def test_to_template_dict_zero_neuron_count(self):
        """Test that zero neuron counts result in zero averages."""
        stats = CombinedStatistics(
            neuron_counts=HemisphereNeuronCounts(left=0, right=0, middle=0),
            left_synapses=HemisphereSynapses(pre_synapses=0, post_synapses=0),
            right_synapses=HemisphereSynapses(pre_synapses=0, post_synapses=0),
            middle_synapses=HemisphereSynapses(pre_synapses=0, post_synapses=0),
            connections=ConnectionStatistics(
                total_upstream=0,
                total_downstream=0,
                avg_connections=0.0,
                avg_upstream=0.0,
                avg_downstream=0.0,
            ),
            total_left_connections=0,
            total_right_connections=0,
            avg_synapses=0.0,
        )
        result = stats.to_template_dict()
        assert result["left_avg"] == 0.0
        assert result["right_avg"] == 0.0
        assert result["middle_avg"] == 0.0
        assert result["left_avg_connections"] == 0.0
        assert result["right_avg_connections"] == 0.0


class TestSideStatistics:
    """Tests for SideStatistics dataclass."""

    @pytest.fixture
    def sample_side_stats(self):
        """Create sample side statistics for testing."""
        return SideStatistics(
            side_neuron_count=10,
            side_pre_synapses=500,
            side_post_synapses=1000,
            total_pre_synapses=1500,
            total_post_synapses=2500,
            connections=ConnectionStatistics(
                total_upstream=100,
                total_downstream=150,
                avg_connections=25.0,
                avg_upstream=10.0,
                avg_downstream=15.0,
            ),
        )

    def test_total_synapses(self, sample_side_stats):
        """Test total synapses calculation."""
        assert sample_side_stats.total_synapses == 4000  # 1500 + 2500

    def test_side_avg_pre(self, sample_side_stats):
        """Test average presynaptic sites per neuron."""
        assert sample_side_stats.side_avg_pre == 50.0  # 500 / 10

    def test_side_avg_post(self, sample_side_stats):
        """Test average postsynaptic sites per neuron."""
        assert sample_side_stats.side_avg_post == 100.0  # 1000 / 10

    def test_side_avg_total(self, sample_side_stats):
        """Test average total synapses per neuron."""
        assert sample_side_stats.side_avg_total == 150.0  # 50 + 100

    def test_side_avg_with_zero_neurons(self):
        """Test that zero neurons returns zero averages."""
        stats = SideStatistics(
            side_neuron_count=0,
            side_pre_synapses=500,
            side_post_synapses=1000,
            total_pre_synapses=1500,
            total_post_synapses=2500,
            connections=ConnectionStatistics(
                total_upstream=100,
                total_downstream=150,
                avg_connections=25.0,
                avg_upstream=10.0,
                avg_downstream=15.0,
            ),
        )
        assert stats.side_avg_pre == 0.0
        assert stats.side_avg_post == 0.0
        assert stats.side_avg_total == 0.0

    def test_to_template_dict_side_counts(self, sample_side_stats):
        """Test that side-specific counts are included."""
        result = sample_side_stats.to_template_dict()
        assert result["side_neuron_count"] == 10
        assert result["side_pre_synapses"] == 500
        assert result["side_post_synapses"] == 1000

    def test_to_template_dict_side_averages(self, sample_side_stats):
        """Test that side-specific averages are included."""
        result = sample_side_stats.to_template_dict()
        assert result["side_avg_pre"] == 50.0
        assert result["side_avg_post"] == 100.0
        assert result["side_avg_total"] == 150.0

    def test_to_template_dict_totals(self, sample_side_stats):
        """Test that total synapses are included."""
        result = sample_side_stats.to_template_dict()
        assert result["total_synapses"] == 4000
        assert result["total_post_synapses"] == 2500
        assert result["total_pre_synapses"] == 1500

    def test_to_template_dict_connections(self, sample_side_stats):
        """Test that connection statistics are included."""
        result = sample_side_stats.to_template_dict()
        assert result["total_connections"] == 250
        assert result["upstream_connections"] == 100
        assert result["downstream_connections"] == 150
        assert result["avg_connections"] == 25.0
        assert result["avg_upstream"] == 10.0
        assert result["avg_downstream"] == 15.0
