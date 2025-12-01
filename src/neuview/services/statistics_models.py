"""Data models for neuron statistics.

This module defines dataclasses that represent statistics data structures,
providing type safety and clear documentation of data flow.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class HemisphereSynapses:
    """Synapse statistics for a single hemisphere.

    Attributes:
        pre_synapses: Number of presynaptic sites (T-bars)
        post_synapses: Number of postsynaptic sites (PSDs)
    """

    pre_synapses: int
    post_synapses: int

    @property
    def total_synapses(self) -> int:
        """Total number of synapses (pre + post)."""
        return self.pre_synapses + self.post_synapses

    def average_per_neuron(self, neuron_count: int) -> float:
        """Calculate average synapses per neuron.

        Args:
            neuron_count: Number of neurons in the hemisphere

        Returns:
            Average synapses per neuron, or 0.0 if neuron_count is 0
        """
        if neuron_count == 0:
            return 0.0
        return self.total_synapses / neuron_count


@dataclass
class HemisphereNeuronCounts:
    """Neuron counts by hemisphere.

    Attributes:
        left: Number of neurons with left soma
        right: Number of neurons with right soma
        middle: Number of neurons with middle soma
    """

    left: int
    right: int
    middle: int

    @property
    def total(self) -> int:
        """Total number of neurons across all hemispheres."""
        return self.left + self.right + self.middle


@dataclass
class ConnectionStatistics:
    """Connection statistics.

    Attributes:
        total_upstream: Total number of upstream connections
        total_downstream: Total number of downstream connections
        avg_connections: Average total connections per neuron
        avg_upstream: Average upstream connections per neuron
        avg_downstream: Average downstream connections per neuron
    """

    total_upstream: int
    total_downstream: int
    avg_connections: float
    avg_upstream: float
    avg_downstream: float

    @property
    def total_connections(self) -> int:
        """Total number of connections (upstream + downstream)."""
        return self.total_upstream + self.total_downstream


@dataclass
class CombinedStatistics:
    """Complete statistics for combined page view (all hemispheres).

    Attributes:
        neuron_counts: Neuron counts by hemisphere
        left_synapses: Synapse statistics for left hemisphere
        right_synapses: Synapse statistics for right hemisphere
        middle_synapses: Synapse statistics for middle hemisphere
        connections: Connection statistics
        total_left_connections: Total connections for left hemisphere
        total_right_connections: Total connections for right hemisphere
        avg_synapses: Average synapses per neuron across all hemispheres
    """

    neuron_counts: HemisphereNeuronCounts
    left_synapses: HemisphereSynapses
    right_synapses: HemisphereSynapses
    middle_synapses: HemisphereSynapses
    connections: ConnectionStatistics
    total_left_connections: int = 0
    total_right_connections: int = 0
    avg_synapses: float = 0.0

    def to_template_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering.

        Returns:
            Flat dictionary with all statistics for template use
        """
        # Calculate hemisphere-specific connection averages
        left_avg_connections = (
            self.total_left_connections / self.neuron_counts.left
            if self.neuron_counts.left > 0
            else 0.0
        )
        right_avg_connections = (
            self.total_right_connections / self.neuron_counts.right
            if self.neuron_counts.right > 0
            else 0.0
        )

        return {
            # Neuron counts by side
            "left_count": self.neuron_counts.left,
            "right_count": self.neuron_counts.right,
            "middle_count": self.neuron_counts.middle,
            # Total synapses
            "total_synapses": (
                self.left_synapses.total_synapses
                + self.right_synapses.total_synapses
                + self.middle_synapses.total_synapses
            ),
            # Hemisphere synapse totals
            "right_synapses": self.right_synapses.total_synapses,
            "left_synapses": self.left_synapses.total_synapses,
            "middle_synapses": self.middle_synapses.total_synapses,
            # Individual hemisphere components
            "right_pre_synapses": self.right_synapses.pre_synapses,
            "right_post_synapses": self.right_synapses.post_synapses,
            "left_pre_synapses": self.left_synapses.pre_synapses,
            "left_post_synapses": self.left_synapses.post_synapses,
            "middle_pre_synapses": self.middle_synapses.pre_synapses,
            "middle_post_synapses": self.middle_synapses.post_synapses,
            # Averages per neuron by side
            "right_avg": self.right_synapses.average_per_neuron(
                self.neuron_counts.right
            ),
            "left_avg": self.left_synapses.average_per_neuron(self.neuron_counts.left),
            "middle_avg": self.middle_synapses.average_per_neuron(
                self.neuron_counts.middle
            ),
            "avg_synapses": self.avg_synapses,
            # Connection statistics
            "total_connections": self.connections.total_connections,
            "upstream_connections": self.connections.total_upstream,
            "downstream_connections": self.connections.total_downstream,
            "avg_connections": self.connections.avg_connections,
            "avg_upstream": self.connections.avg_upstream,
            "avg_downstream": self.connections.avg_downstream,
            # Hemisphere-specific connection averages
            "left_avg_connections": left_avg_connections,
            "right_avg_connections": right_avg_connections,
        }


@dataclass
class SideStatistics:
    """Statistics for individual side page view (single hemisphere).

    Attributes:
        side_neuron_count: Number of neurons on this side
        side_pre_synapses: Number of presynaptic sites on this side
        side_post_synapses: Number of postsynaptic sites on this side
        total_pre_synapses: Total presynaptic sites for the neuron type
        total_post_synapses: Total postsynaptic sites for the neuron type
        connections: Connection statistics
    """

    side_neuron_count: int
    side_pre_synapses: int
    side_post_synapses: int
    total_pre_synapses: int
    total_post_synapses: int
    connections: ConnectionStatistics

    @property
    def total_synapses(self) -> int:
        """Total synapses for the neuron type."""
        return self.total_pre_synapses + self.total_post_synapses

    @property
    def side_avg_pre(self) -> float:
        """Average presynaptic sites per neuron on this side."""
        if self.side_neuron_count == 0:
            return 0.0
        return self.side_pre_synapses / self.side_neuron_count

    @property
    def side_avg_post(self) -> float:
        """Average postsynaptic sites per neuron on this side."""
        if self.side_neuron_count == 0:
            return 0.0
        return self.side_post_synapses / self.side_neuron_count

    @property
    def side_avg_total(self) -> float:
        """Average total synapses per neuron on this side."""
        return self.side_avg_pre + self.side_avg_post

    def to_template_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering.

        Returns:
            Flat dictionary with all statistics for template use
        """
        return {
            # Side-specific neuron counts
            "side_neuron_count": self.side_neuron_count,
            "side_pre_synapses": self.side_pre_synapses,
            "side_post_synapses": self.side_post_synapses,
            # Side-specific averages
            "side_avg_pre": self.side_avg_pre,
            "side_avg_post": self.side_avg_post,
            "side_avg_total": self.side_avg_total,
            # Synapse totals
            "total_synapses": self.total_synapses,
            "total_post_synapses": self.total_post_synapses,
            "total_pre_synapses": self.total_pre_synapses,
            # Connection statistics
            "total_connections": self.connections.total_connections,
            "upstream_connections": self.connections.total_upstream,
            "downstream_connections": self.connections.total_downstream,
            "avg_connections": self.connections.avg_connections,
            "avg_upstream": self.connections.avg_upstream,
            "avg_downstream": self.connections.avg_downstream,
        }
