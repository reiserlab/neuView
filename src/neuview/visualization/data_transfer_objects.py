"""
Data transfer objects for hexagon grid generation.

This module provides structured data objects to encapsulate related parameters
and reduce method signature complexity in the hexagon grid generator.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from .data_processing.data_structures import ColumnData, SomaSide


@dataclass
class GridGenerationRequest:
    """
    Encapsulates all parameters needed for comprehensive grid generation.

    This replaces the complex parameter list in generate_comprehensive_region_hexagonal_grids.
    """

    column_data: List[ColumnData]
    thresholds_all: Dict
    all_possible_columns: List[Dict]
    region_columns_map: Dict[str, Set]
    neuron_type: str
    soma_side: SomaSide
    output_format: str = "svg"
    save_to_files: bool = True
    min_max_data: Optional[Dict] = None

    @property
    def regions(self) -> List[str]:
        """Map region_columns_map keys to regions list."""
        return list(self.region_columns_map.keys()) if self.region_columns_map else []

    @property
    def sides(self) -> List[str]:
        """Map soma_side to sides list."""
        return [self.soma_side.value] if self.soma_side else []

    @property
    def metrics(self) -> List[str]:
        """Return available metrics for this request."""
        # For now, return common metrics - this could be made configurable
        return ["synapse_density", "cell_count"]

    def __post_init__(self):
        """Validate the request parameters."""
        if not self.neuron_type:
            raise ValueError("neuron_type cannot be empty")

        if self.soma_side not in [
            SomaSide.LEFT,
            SomaSide.RIGHT,
            SomaSide.COMBINED,
            SomaSide.L,
            SomaSide.R,
        ]:
            raise ValueError(f"Invalid soma_side: {self.soma_side}")

        if self.output_format not in ["svg", "png"]:
            raise ValueError(f"Invalid output_format: {self.output_format}")


@dataclass
class SingleRegionGridRequest:
    """
    Encapsulates parameters for single region grid generation.

    This replaces the complex parameter list in generate_comprehensive_single_region_grid.
    """

    all_possible_columns: List[Dict]
    region_column_coords: Set
    data_map: Dict
    metric_type: str
    region_name: str
    thresholds: Optional[Dict] = None
    neuron_type: Optional[str] = None
    soma_side: Optional[SomaSide] = None
    output_format: str = "svg"
    other_regions_coords: Optional[Set] = None
    min_max_data: Optional[Dict] = None

    def __post_init__(self):
        """Validate the request parameters."""
        if self.metric_type not in ["synapse_density", "cell_count"]:
            raise ValueError(f"Invalid metric_type: {self.metric_type}")

        if not self.region_name:
            raise ValueError("region_name cannot be empty")


@dataclass
class RenderingRequest:
    """
    Encapsulates parameters for rendering operations.

    This simplifies rendering method calls and makes them more maintainable.
    """

    hexagons: List[Dict]
    min_val: float
    max_val: float
    thresholds: Dict
    title: str
    subtitle1: str
    subtitle2: str
    metric_type: str
    soma_side: SomaSide
    output_format: str = "svg"
    save_to_file: bool = False
    filename: Optional[str] = None
    min_max_data: Optional[Dict] = None

    def __post_init__(self):
        """Validate the rendering request."""
        if not self.hexagons:
            raise ValueError("hexagons list cannot be empty")

        if self.min_val >= self.max_val:
            raise ValueError("min_val must be less than max_val")


@dataclass
class TooltipGenerationRequest:
    """
    Encapsulates parameters for tooltip generation.

    This simplifies the tooltip generation method signature.
    """

    hexagons: List[Dict]
    soma_side: str
    metric_type: str

    def __post_init__(self):
        """Validate tooltip generation parameters."""
        if self.metric_type not in ["synapse_density", "cell_count"]:
            raise ValueError(f"Invalid metric_type: {self.metric_type}")


@dataclass
class GridGenerationResult:
    """
    Encapsulates the results of grid generation operations.

    This provides a structured way to return generation results with metadata.
    """

    region_grids: Dict[str, Dict[str, str]]
    processing_time: float
    success: bool
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


# Factory functions for creating commonly used data transfer objects


def create_grid_generation_request(
    column_data: List[ColumnData],
    thresholds_all: Dict,
    all_possible_columns: List[Dict],
    region_columns_map: Dict[str, Set],
    neuron_type: str,
    soma_side: SomaSide,
    **kwargs,
) -> GridGenerationRequest:
    """
    Factory function to create a GridGenerationRequest with modern structured format.

    Args:
        column_data: List of structured ColumnData objects
        thresholds_all: Threshold values dictionary
        all_possible_columns: List of all possible columns
        region_columns_map: Region to columns mapping
        neuron_type: Type of neuron
        soma_side: Side of soma (SomaSide enum)
        **kwargs: Additional optional parameters

    Returns:
        GridGenerationRequest object with structured data
    """
    # Validate input types
    if not isinstance(soma_side, SomaSide):
        raise ValueError(f"soma_side must be a SomaSide enum, got {type(soma_side)}")

    return GridGenerationRequest(
        column_data=column_data,
        thresholds_all=thresholds_all,
        all_possible_columns=all_possible_columns,
        region_columns_map=region_columns_map,
        neuron_type=neuron_type,
        soma_side=soma_side,
        **kwargs,
    )


def create_rendering_request(
    hexagons: List[Dict],
    min_val: float,
    max_val: float,
    thresholds: Dict,
    title: str,
    subtitle1: str,
    subtitle2: str,
    metric_type: str,
    soma_side: SomaSide,
    **kwargs,
) -> RenderingRequest:
    """
    Factory function to create a RenderingRequest with modern types.

    Args:
        hexagons: List of hexagon data dictionaries
        min_val: Minimum value for scaling
        max_val: Maximum value for scaling
        thresholds: Threshold values dictionary
        title: Chart title
        subtitle1: Chart subtitle1
        subtitle2: Chart subtitle2
        metric_type: Type of metric being displayed
        soma_side: Side of soma (SomaSide enum)
        **kwargs: Additional optional parameters (including min_max_data)

    Returns:
        RenderingRequest object
    """
    # Validate input types
    if not isinstance(soma_side, SomaSide):
        raise ValueError(f"soma_side must be a SomaSide enum, got {type(soma_side)}")

    return RenderingRequest(
        hexagons=hexagons,
        min_val=min_val,
        max_val=max_val,
        thresholds=thresholds,
        title=title,
        subtitle1=subtitle1,
        subtitle2=subtitle2,
        metric_type=metric_type,
        soma_side=soma_side,
        **kwargs,
    )


def create_single_region_request(
    all_possible_columns: List[Dict],
    region_column_coords: Set,
    data_map: Dict,
    metric_type: str,
    region_name: str,
    soma_side: Optional[SomaSide] = None,
    **kwargs,
) -> SingleRegionGridRequest:
    """
    Factory function to create a SingleRegionGridRequest with modern types.

    Args:
        all_possible_columns: List of all possible columns
        region_column_coords: Region column coordinates
        data_map: Data mapping dictionary
        metric_type: Type of metric
        region_name: Name of the region
        soma_side: Side of soma (SomaSide enum, optional)
        **kwargs: Additional optional parameters

    Returns:
        SingleRegionGridRequest object
    """
    # Validate soma_side if provided
    if soma_side is not None and not isinstance(soma_side, SomaSide):
        raise ValueError(
            f"soma_side must be a SomaSide enum or None, got {type(soma_side)}"
        )

    return SingleRegionGridRequest(
        all_possible_columns=all_possible_columns,
        region_column_coords=region_column_coords,
        data_map=data_map,
        metric_type=metric_type,
        region_name=region_name,
        soma_side=soma_side,
        **kwargs,
    )
