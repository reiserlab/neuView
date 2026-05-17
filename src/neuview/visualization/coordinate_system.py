"""
Coordinate system classes for hexagon grid generation.

This module provides coordinate system management for hexagonal grids,
including conversions between different coordinate systems, layout management,
and geometric calculations.
"""

import math
import logging
from typing import Tuple, List, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .data_processing.data_structures import SomaSide

logger = logging.getLogger(__name__)


@dataclass
class HexagonPoint:
    """Represents a point in hexagonal coordinates."""

    hex1: int
    hex2: int

    def to_tuple(self) -> Tuple[int, int]:
        """Convert to tuple for use as dictionary key."""
        return (self.hex1, self.hex2)


@dataclass
class AxialCoordinate:
    """Represents axial coordinates (q, r) in hexagonal grid."""

    q: float
    r: float


@dataclass
class PixelCoordinate:
    """Represents pixel coordinates (x, y) for rendering."""

    x: float
    y: float


@dataclass
class GridBounds:
    """Represents the bounds of a hexagonal grid."""

    min_x: float
    max_x: float
    min_y: float
    max_y: float
    width: float
    height: float


class HexagonCoordinateSystem:
    """
    Handles conversions between different coordinate systems for hexagonal grids.

    Supports conversions between:
    - Hexagon coordinates (hex1, hex2)
    - Axial coordinates (q, r)
    - Pixel coordinates (x, y)
    """

    def __init__(self, hex_size: float = 6, spacing_factor: float = 1.1):
        """
        Initialize the coordinate system.

        Args:
            hex_size: Size of individual hexagons
            spacing_factor: Spacing factor between hexagons
        """
        self.hex_size = hex_size
        self.spacing_factor = spacing_factor
        self.effective_size = hex_size * spacing_factor

    def update_parameters(self, hex_size: float = None, spacing_factor: float = None):
        """
        Update coordinate system parameters in-place.

        Args:
            hex_size: New hexagon size (optional)
            spacing_factor: New spacing factor (optional)
        """
        if hex_size is not None:
            self.hex_size = hex_size
        if spacing_factor is not None:
            self.spacing_factor = spacing_factor

        # Recalculate derived values
        self.effective_size = self.hex_size * self.spacing_factor

    def hex_to_axial(
        self, hex1: int, hex2: int, min_hex1: int = 0, min_hex2: int = 0
    ) -> AxialCoordinate:
        """
        Convert hexagon coordinates to axial coordinates.

        Args:
            hex1: First hexagon coordinate
            hex2: Second hexagon coordinate
            min_hex1: Minimum hex1 value for normalization
            min_hex2: Minimum hex2 value for normalization

        Returns:
            AxialCoordinate object with q and r values
        """
        # Normalize coordinates
        hex1_coord = hex1 - min_hex1
        hex2_coord = hex2 - min_hex2

        # Convert to axial coordinates
        q = -(hex1_coord - hex2_coord) - 3
        r = -hex2_coord

        return AxialCoordinate(q=q, r=r)

    def axial_to_pixel(
        self, axial: AxialCoordinate, mirror_side: Optional[str] = None
    ) -> PixelCoordinate:
        """
        Convert axial coordinates to pixel coordinates.

        Args:
            axial: AxialCoordinate object
            mirror_side: 'left' to mirror x-coordinate, 'right' or None for normal

        Returns:
            PixelCoordinate object with x and y values
        """
        # Convert axial to pixel using hexagonal grid formulas
        x = self.effective_size * (3 / 2 * axial.q)
        y = self.effective_size * (math.sqrt(3) / 2 * axial.q + math.sqrt(3) * axial.r)

        # Apply mirroring if needed
        # Handle both string and SomaSide enum inputs
        if mirror_side:
            if hasattr(mirror_side, "value"):
                # It's a SomaSide enum
                mirror_side_str = mirror_side.value
            else:
                # It's already a string
                mirror_side_str = str(mirror_side)

            if mirror_side_str.lower() in ["left", "l"]:
                x = -x

        return PixelCoordinate(x=x, y=y)

    def hex_to_pixel(
        self,
        hex1: int,
        hex2: int,
        min_hex1: int = 0,
        min_hex2: int = 0,
        mirror_side: Optional[str] = None,
    ) -> PixelCoordinate:
        """
        Convert hexagon coordinates directly to pixel coordinates.

        Args:
            hex1: First hexagon coordinate
            hex2: Second hexagon coordinate
            min_hex1: Minimum hex1 value for normalization
            min_hex2: Minimum hex2 value for normalization
            mirror_side: 'left' to mirror x-coordinate, 'right' or None for normal

        Returns:
            PixelCoordinate object with x and y values
        """
        axial = self.hex_to_axial(hex1, hex2, min_hex1, min_hex2)
        return self.axial_to_pixel(axial, mirror_side)


class HexagonGeometry:
    """
    Handles geometric calculations for hexagons.

    Provides methods for calculating hexagon vertices, bounds, and other
    geometric properties needed for rendering.
    """

    def __init__(self, hex_size: float = 6):
        """
        Initialize hexagon geometry.

        Args:
            hex_size: Size (radius) of hexagons
        """
        self.hex_size = hex_size

    def update_hex_size(self, hex_size: float):
        """
        Update hexagon size in-place.

        Args:
            hex_size: New hexagon size
        """
        self.hex_size = hex_size

    def get_hexagon_vertices(self, precision: int = 2) -> List[str]:
        """
        Calculate hexagon vertex points for SVG path.

        Args:
            precision: Number of decimal places for coordinates

        Returns:
            List of coordinate strings in "x,y" format
        """
        vertices = []
        for i in range(6):
            angle = math.pi / 3 * i
            x = self.hex_size * math.cos(angle)
            y = self.hex_size * math.sin(angle)
            vertices.append(f"{x:.{precision}f},{y:.{precision}f}")
        return vertices

    def get_hexagon_path(self, precision: int = 2) -> str:
        """
        Get SVG path string for hexagon shape.

        Args:
            precision: Number of decimal places for coordinates

        Returns:
            SVG path string
        """
        vertices = self.get_hexagon_vertices(precision)
        return " ".join(vertices)


class HexagonGridLayout:
    """
    Manages the overall layout and dimensions of hexagonal grids.

    Handles calculation of grid bounds, SVG dimensions, legend positioning,
    and other layout-related properties.
    """

    def __init__(self, hex_size: float = 6, margin: float = 10):
        """
        Initialize grid layout manager.

        Args:
            hex_size: Size of individual hexagons
            margin: Margin around the grid
        """
        self.hex_size = hex_size
        self.margin = margin

    def update_parameters(self, hex_size: float = None, margin: float = None):
        """
        Update layout parameters in-place.

        Args:
            hex_size: New hexagon size (optional)
            margin: New margin value (optional)
        """
        if hex_size is not None:
            self.hex_size = hex_size
        if margin is not None:
            self.margin = margin

    def calculate_grid_bounds(
        self, pixel_coordinates: List[PixelCoordinate]
    ) -> GridBounds:
        """
        Calculate the bounds of a grid from pixel coordinates.

        Args:
            pixel_coordinates: List of PixelCoordinate objects

        Returns:
            GridBounds object with calculated dimensions
        """
        if not pixel_coordinates:
            return GridBounds(0, 0, 0, 0, 0, 0)

        min_x = min(coord.x for coord in pixel_coordinates) - self.hex_size
        max_x = max(coord.x for coord in pixel_coordinates) + self.hex_size
        min_y = min(coord.y for coord in pixel_coordinates) - self.hex_size
        max_y = max(coord.y for coord in pixel_coordinates) + self.hex_size

        width = max_x - min_x + 2 * self.margin
        height = max_y - min_y + 2 * self.margin

        return GridBounds(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            width=width,
            height=height,
        )

    def calculate_legend_position(
        self,
        grid_bounds: GridBounds,
        soma_side: "SomaSide" = None,
        legend_width: float = 12,
    ) -> Tuple[float, float]:
        """
        Calculate legend position based on soma side and grid bounds.

        Args:
            grid_bounds: GridBounds object
            soma_side: SomaSide enum to determine legend position (None defaults to right)
            legend_width: Width of the legend

        Returns:
            Tuple of (legend_x, title_x) coordinates
        """
        # Import here to avoid circular imports
        from .data_processing.data_structures import SomaSide

        if soma_side is None:
            soma_side = SomaSide.RIGHT

        # Handle both string and SomaSide enum inputs
        if hasattr(soma_side, "value"):
            # It's a SomaSide enum
            soma_side_str = soma_side.value
        else:
            # It's a string
            soma_side_str = str(soma_side)

        if soma_side_str.lower() in ["right", "r"]:
            legend_x = (
                grid_bounds.width - legend_width - 5 - int(grid_bounds.width * 0.1)
            )
        else:
            legend_x = -20

        title_x = legend_x + legend_width + 15

        return legend_x, title_x

    def calculate_coordinate_ranges(
        self, hex_points: List[HexagonPoint]
    ) -> Tuple[int, int, int, int]:
        """
        Calculate coordinate ranges from hexagon points.

        Args:
            hex_points: List of HexagonPoint objects

        Returns:
            Tuple of (min_hex1, max_hex1, min_hex2, max_hex2)
        """
        if not hex_points:
            return 0, 0, 0, 0

        min_hex1 = min(point.hex1 for point in hex_points)
        max_hex1 = max(point.hex1 for point in hex_points)
        min_hex2 = min(point.hex2 for point in hex_points)
        max_hex2 = max(point.hex2 for point in hex_points)

        return min_hex1, max_hex1, min_hex2, max_hex2


class EyemapCoordinateSystem:
    """
    Main coordinate system manager that combines all coordinate system components.

    This class provides a unified interface for all coordinate system operations
    needed for hexagonal grid generation and rendering.
    """

    def __init__(
        self, hex_size: float = 6, spacing_factor: float = 1.1, margin: float = 10
    ):
        """
        Initialize the complete coordinate system.

        Args:
            hex_size: Size of individual hexagons
            spacing_factor: Spacing factor between hexagons
            margin: Margin around the grid
        """
        self.coordinate_system = HexagonCoordinateSystem(hex_size, spacing_factor)
        self.geometry = HexagonGeometry(hex_size)
        self.layout = HexagonGridLayout(hex_size, margin)


    def convert_column_coordinates(
        self, columns: List[Dict], mirror_side: Optional[str] = None
    ) -> List[Dict]:
        """
        Convert column data with hex1/hex2 coordinates to include pixel coordinates.

        Args:
            columns: List of column dictionaries with 'hex1' and 'hex2' keys
            mirror_side: 'left' to mirror x-coordinate, 'right' or None for normal

        Returns:
            List of column dictionaries with added 'x' and 'y' pixel coordinates
        """
        if not columns:
            return []

        # Calculate coordinate ranges
        hex_points = [HexagonPoint(col["hex1"], col["hex2"]) for col in columns]
        min_hex1, _, min_hex2, _ = self.layout.calculate_coordinate_ranges(hex_points)

        # Convert coordinates
        converted_columns = []
        for col in columns:
            pixel_coord = self.coordinate_system.hex_to_pixel(
                col["hex1"], col["hex2"], min_hex1, min_hex2, mirror_side
            )

            # Create new column dictionary with pixel coordinates
            new_col = col.copy()
            new_col["x"] = pixel_coord.x
            new_col["y"] = pixel_coord.y
            converted_columns.append(new_col)

        return converted_columns

    def calculate_svg_layout(
        self, columns: List[Dict], soma_side: "SomaSide" = None
    ) -> Dict:
        """
        Calculate complete SVG layout information for rendering.

        Args:
            columns: List of column dictionaries with pixel coordinates
            soma_side: SomaSide enum for legend positioning (None defaults to right)

        Returns:
            Dictionary with layout information including bounds, dimensions, and positions
        """
        # Import here to avoid circular imports
        from .data_processing.data_structures import SomaSide

        if soma_side is None:
            soma_side = SomaSide.RIGHT
        if not columns:
            return {}

        # Extract pixel coordinates
        pixel_coords = [PixelCoordinate(col["x"], col["y"]) for col in columns]

        # Calculate grid bounds
        grid_bounds = self.layout.calculate_grid_bounds(pixel_coords)

        # Calculate legend position
        legend_x, title_x = self.layout.calculate_legend_position(
            grid_bounds, soma_side
        )

        # Get hexagon vertex points
        hex_points = self.geometry.get_hexagon_path()

        return {
            "grid_bounds": grid_bounds,
            "legend_x": legend_x,
            "title_x": title_x,
            "hex_points": hex_points,
            "width": grid_bounds.width,
            "height": grid_bounds.height,
            "min_x": grid_bounds.min_x,
            "min_y": grid_bounds.min_y,
            "margin": self.layout.margin,
        }
