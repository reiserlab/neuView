"""Statistics calculators for neuron data.

This module provides calculator classes that encapsulate the logic for computing
statistics from raw neuron data. This separates calculation logic from the service
layer and makes the code more testable and maintainable.
"""

from typing import Any, Dict

from neuview.services.statistics_constants import ConnectivityFields, SummaryFields
from neuview.services.statistics_models import (
    CombinedStatistics,
    ConnectionStatistics,
    HemisphereNeuronCounts,
    HemisphereSynapses,
    SideStatistics,
)


class CombinedStatisticsCalculator:
    """Calculate statistics for combined (all hemispheres) view.

    This calculator processes complete summary and connectivity data to generate
    statistics that show information across all hemispheres (left, right, middle).

    Attributes:
        complete_summary: Complete summary data dictionary
        connectivity: Connectivity data dictionary
    """

    def __init__(self, complete_summary: Dict[str, Any], connectivity: Dict[str, Any]):
        """Initialize calculator with data dictionaries.

        Args:
            complete_summary: Complete summary data with all hemisphere information
            connectivity: Connectivity data with connection statistics
        """
        self.complete_summary = complete_summary
        self.connectivity = connectivity

    def calculate(self) -> CombinedStatistics:
        """Calculate all combined statistics.

        Returns:
            CombinedStatistics object with all calculated values
        """
        neuron_counts = self._extract_neuron_counts()
        avg_synapses = self._calculate_overall_avg_synapses()

        return CombinedStatistics(
            neuron_counts=neuron_counts,
            left_synapses=self._calculate_hemisphere_synapses("left"),
            right_synapses=self._calculate_hemisphere_synapses("right"),
            middle_synapses=self._calculate_hemisphere_synapses("middle"),
            connections=self._calculate_connection_stats(),
            total_left_connections=self.connectivity.get(
                ConnectivityFields.TOTAL_LEFT, 0
            ),
            total_right_connections=self.connectivity.get(
                ConnectivityFields.TOTAL_RIGHT, 0
            ),
            avg_synapses=avg_synapses,
        )

    def _extract_neuron_counts(self) -> HemisphereNeuronCounts:
        """Extract neuron counts from summary data.

        Returns:
            HemisphereNeuronCounts with counts for each hemisphere
        """
        return HemisphereNeuronCounts(
            left=self.complete_summary.get(SummaryFields.LEFT_COUNT, 0),
            right=self.complete_summary.get(SummaryFields.RIGHT_COUNT, 0),
            middle=self.complete_summary.get(SummaryFields.MIDDLE_COUNT, 0),
        )

    def _calculate_hemisphere_synapses(self, hemisphere: str) -> HemisphereSynapses:
        """Calculate synapse statistics for a specific hemisphere.

        Args:
            hemisphere: Hemisphere name ('left', 'right', or 'middle')

        Returns:
            HemisphereSynapses with pre and post synapse counts
        """
        # Construct field names dynamically based on hemisphere
        pre_field = f"{hemisphere}_pre_synapses"
        post_field = f"{hemisphere}_post_synapses"

        return HemisphereSynapses(
            pre_synapses=self.complete_summary.get(pre_field, 0),
            post_synapses=self.complete_summary.get(post_field, 0),
        )

    def _calculate_connection_stats(self) -> ConnectionStatistics:
        """Calculate connection statistics.

        Returns:
            ConnectionStatistics with all connection metrics
        """
        return ConnectionStatistics(
            total_upstream=self.connectivity.get(ConnectivityFields.TOTAL_UPSTREAM, 0),
            total_downstream=self.connectivity.get(
                ConnectivityFields.TOTAL_DOWNSTREAM, 0
            ),
            avg_connections=self.connectivity.get(
                ConnectivityFields.AVG_CONNECTIONS, 0.0
            ),
            avg_upstream=self.connectivity.get(ConnectivityFields.AVG_UPSTREAM, 0.0),
            avg_downstream=self.connectivity.get(
                ConnectivityFields.AVG_DOWNSTREAM, 0.0
            ),
        )

    def _calculate_overall_avg_synapses(self) -> float:
        """Calculate overall average synapses per neuron.

        Returns:
            Average synapses per neuron across all hemispheres
        """
        avg_pre = self.complete_summary.get(SummaryFields.AVG_PRE_SYNAPSES, 0.0)
        avg_post = self.complete_summary.get(SummaryFields.AVG_POST_SYNAPSES, 0.0)
        return avg_pre + avg_post


class SideStatisticsCalculator:
    """Calculate statistics for individual hemisphere view.

    This calculator processes side-specific summary data to generate statistics
    for a single hemisphere (left, right, or middle).

    Attributes:
        summary: Side-specific summary data dictionary
        complete_summary: Complete summary data dictionary
        connectivity: Connectivity data dictionary
        soma_side: The soma side ('left', 'right', or 'middle')
    """

    # Map soma_side to summary field prefixes
    SIDE_PREFIX_MAP = {
        "left": "left",
        "right": "right",
        "middle": "middle",
    }

    def __init__(
        self,
        summary: Dict[str, Any],
        complete_summary: Dict[str, Any],
        connectivity: Dict[str, Any],
        soma_side: str,
    ):
        """Initialize calculator with data dictionaries.

        Args:
            summary: Side-specific summary data
            complete_summary: Complete summary data with all hemisphere information
            connectivity: Connectivity data with connection statistics
            soma_side: The soma side ('left', 'right', 'middle')
        """
        self.summary = summary
        self.complete_summary = complete_summary
        self.connectivity = connectivity
        self.soma_side = soma_side

    def calculate(self) -> SideStatistics:
        """Calculate all side-specific statistics.

        Returns:
            SideStatistics object with all calculated values
        """
        prefix = self.SIDE_PREFIX_MAP.get(self.soma_side)
        if not prefix:
            # Return empty statistics if invalid soma_side
            return SideStatistics(
                side_neuron_count=0,
                side_pre_synapses=0,
                side_post_synapses=0,
                total_pre_synapses=0,
                total_post_synapses=0,
                connections=ConnectionStatistics(
                    total_upstream=0,
                    total_downstream=0,
                    avg_connections=0.0,
                    avg_upstream=0.0,
                    avg_downstream=0.0,
                ),
            )

        # Extract side-specific values
        side_neuron_count = self.complete_summary.get(f"{prefix}_count", 0)
        side_pre_synapses = self.complete_summary.get(f"{prefix}_pre_synapses", 0)
        side_post_synapses = self.complete_summary.get(f"{prefix}_post_synapses", 0)

        # Extract total synapse counts
        total_pre_synapses = self.summary.get(SummaryFields.TOTAL_PRE_SYNAPSES, 0)
        total_post_synapses = self.summary.get(SummaryFields.TOTAL_POST_SYNAPSES, 0)

        return SideStatistics(
            side_neuron_count=side_neuron_count,
            side_pre_synapses=side_pre_synapses,
            side_post_synapses=side_post_synapses,
            total_pre_synapses=total_pre_synapses,
            total_post_synapses=total_post_synapses,
            connections=self._calculate_connection_stats(),
        )

    def _calculate_connection_stats(self) -> ConnectionStatistics:
        """Calculate connection statistics.

        Returns:
            ConnectionStatistics with all connection metrics
        """
        return ConnectionStatistics(
            total_upstream=self.connectivity.get(ConnectivityFields.TOTAL_UPSTREAM, 0),
            total_downstream=self.connectivity.get(
                ConnectivityFields.TOTAL_DOWNSTREAM, 0
            ),
            avg_connections=self.connectivity.get(
                ConnectivityFields.AVG_CONNECTIONS, 0.0
            ),
            avg_upstream=self.connectivity.get(ConnectivityFields.AVG_UPSTREAM, 0.0),
            avg_downstream=self.connectivity.get(
                ConnectivityFields.AVG_DOWNSTREAM, 0.0
            ),
        )
