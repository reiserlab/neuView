"""Constants for statistics field names.

This module defines constant field names used in summary and connectivity data
to avoid magic strings throughout the codebase.
"""


class SummaryFields:
    """Field names for summary data dictionaries."""

    # Total counts
    TOTAL_COUNT = "total_count"
    LEFT_COUNT = "left_count"
    RIGHT_COUNT = "right_count"
    MIDDLE_COUNT = "middle_count"

    # Pre-synapses by hemisphere
    LEFT_PRE_SYNAPSES = "left_pre_synapses"
    RIGHT_PRE_SYNAPSES = "right_pre_synapses"
    MIDDLE_PRE_SYNAPSES = "middle_pre_synapses"

    # Post-synapses by hemisphere
    LEFT_POST_SYNAPSES = "left_post_synapses"
    RIGHT_POST_SYNAPSES = "right_post_synapses"
    MIDDLE_POST_SYNAPSES = "middle_post_synapses"

    # Total synapses
    TOTAL_PRE_SYNAPSES = "total_pre_synapses"
    TOTAL_POST_SYNAPSES = "total_post_synapses"

    # Averages
    AVG_PRE_SYNAPSES = "avg_pre_synapses"
    AVG_POST_SYNAPSES = "avg_post_synapses"


class ConnectivityFields:
    """Field names for connectivity data dictionaries."""

    # Total connections
    TOTAL_UPSTREAM = "total_upstream"
    TOTAL_DOWNSTREAM = "total_downstream"

    # Hemisphere-specific totals
    TOTAL_LEFT = "total_left"
    TOTAL_RIGHT = "total_right"

    # Averages
    AVG_CONNECTIONS = "avg_connections"
    AVG_UPSTREAM = "avg_upstream"
    AVG_DOWNSTREAM = "avg_downstream"


class TemplateStatsFields:
    """Field names for template statistics dictionaries."""

    # Neuron counts
    LEFT_COUNT = "left_count"
    RIGHT_COUNT = "right_count"
    MIDDLE_COUNT = "middle_count"
    SIDE_NEURON_COUNT = "side_neuron_count"

    # Synapse totals
    TOTAL_SYNAPSES = "total_synapses"
    TOTAL_PRE_SYNAPSES = "total_pre_synapses"
    TOTAL_POST_SYNAPSES = "total_post_synapses"

    # Hemisphere synapse totals
    LEFT_SYNAPSES = "left_synapses"
    RIGHT_SYNAPSES = "right_synapses"
    MIDDLE_SYNAPSES = "middle_synapses"

    # Individual hemisphere components
    LEFT_PRE_SYNAPSES = "left_pre_synapses"
    LEFT_POST_SYNAPSES = "left_post_synapses"
    RIGHT_PRE_SYNAPSES = "right_pre_synapses"
    RIGHT_POST_SYNAPSES = "right_post_synapses"
    MIDDLE_PRE_SYNAPSES = "middle_pre_synapses"
    MIDDLE_POST_SYNAPSES = "middle_post_synapses"

    # Side-specific synapses
    SIDE_PRE_SYNAPSES = "side_pre_synapses"
    SIDE_POST_SYNAPSES = "side_post_synapses"

    # Averages per neuron
    AVG_SYNAPSES = "avg_synapses"
    LEFT_AVG = "left_avg"
    RIGHT_AVG = "right_avg"
    MIDDLE_AVG = "middle_avg"

    # Side-specific averages
    SIDE_AVG_PRE = "side_avg_pre"
    SIDE_AVG_POST = "side_avg_post"
    SIDE_AVG_TOTAL = "side_avg_total"

    # Connection statistics
    TOTAL_CONNECTIONS = "total_connections"
    UPSTREAM_CONNECTIONS = "upstream_connections"
    DOWNSTREAM_CONNECTIONS = "downstream_connections"
    AVG_CONNECTIONS = "avg_connections"
    AVG_UPSTREAM = "avg_upstream"
    AVG_DOWNSTREAM = "avg_downstream"

    # Hemisphere-specific connection averages
    LEFT_AVG_CONNECTIONS = "left_avg_connections"
    RIGHT_AVG_CONNECTIONS = "right_avg_connections"
