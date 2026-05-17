"""
Layout calculator for hexagon grid visualizations.

This module handles the calculation of SVG layout parameters, positioning,
and coordinate transformations for hexagon grid visualizations.
"""

import math
from typing import List, Dict, Any, Optional, Tuple
import logging

from .rendering_config import LayoutConfig, LegendConfig
from .region_config import RegionConfigRegistry
from ..data_processing.data_structures import SomaSide

logger = logging.getLogger(__name__)

# Default layout constants
DEFAULT_LAYER_BUTTON_WIDTH = 40.0
DEFAULT_TOTAL_CONTROL_HEIGHT = 200.0
DEFAULT_LEGEND_WIDTH = 50
DEFAULT_LEGEND_HEIGHT = 60
DEFAULT_LEGEND_OFFSET = 10


class LayoutCalculator:
    """
    Calculator for SVG layout parameters and positioning.

    This class handles all layout-related calculations including:
    - SVG dimensions and viewBox
    - Hexagon positioning
    - Legend placement
    - Title and subtitle positioning
    """

    def __init__(
        self, hex_size: int = 6, spacing_factor: float = 1.1, margin: int = 10
    ):
        """
        Initialize the layout calculator.

        Args:
            hex_size: Size of individual hexagons
            spacing_factor: Spacing factor between hexagons
            margin: Margin around the visualization
        """
        self.hex_size = hex_size
        self.spacing_factor = spacing_factor
        self.margin = margin

        # Calculate derived values
        self.hex_radius = hex_size
        self.hex_width = self.hex_radius * 2
        self.hex_height = self.hex_radius * math.sqrt(3)

    def calculate_layout(
        self,
        hexagons: List[Dict[str, Any]],
        soma_side: Optional[SomaSide] = None,
        region: Optional[str] = None,
    ) -> LayoutConfig:
        """
        Calculate complete layout configuration for hexagon visualization.

        Args:
            hexagons: List of hexagon data dictionaries
            soma_side: Side of soma for orientation (SomaSide enum)
            region: Brain region identifier for layer control configuration

        Returns:
            LayoutConfig object with calculated layout parameters
        """
        if not hexagons:
            return LayoutConfig()

        # Calculate coordinate bounds
        bounds = self._calculate_bounds(hexagons)

        # Calculate base SVG dimensions
        base_width = bounds["max_x"] - bounds["min_x"] + (2 * self.margin)
        base_height = bounds["max_y"] - bounds["min_y"] + (2 * self.margin)

        # Add space for layer controls
        control_dimensions = (
            RegionConfigRegistry.get_control_dimensions(region)
            if region
            else {
                "layer_button_width": DEFAULT_LAYER_BUTTON_WIDTH,
                "total_control_height": DEFAULT_TOTAL_CONTROL_HEIGHT,
            }
        )
        control_space = self._calculate_control_space_from_dimensions(
            control_dimensions
        )
        svg_width = max(base_width, control_space["min_width"])
        svg_height = max(base_height, control_space["min_height"])

        # Enforce a per-region canvas floor so the L and R eyemaps for the
        # same region render at identical SVG dimensions even though the L/R
        # hex coordinate sets aren't strictly symmetric (R extends ~10px
        # wider and ~6px taller for optic-lobe regions). The floor is the
        # observed max plus a small buffer; the underlying hex content
        # positions are unchanged, only the canvas around them grows.
        region_canvas_floor = {
            "ME": (380, 410),
            "LO": (380, 410),
            "LOP": (380, 410),
        }
        if region in region_canvas_floor:
            floor_w, floor_h = region_canvas_floor[region]
            svg_width = max(svg_width, floor_w)
            svg_height = max(svg_height, floor_h)

        # Calculate layer control positioning
        layer_control_x, layer_control_y = self._calculate_layer_control_position(
            svg_width, svg_height, soma_side, control_dimensions
        )

        # Calculate legend position based on soma side (opposite from layer controls)
        legend_width = 50  # Width needed for legend
        legend_x = svg_width - legend_width - self.margin - 10
        legend_y = self.margin

        # Calculate title position
        title_x = svg_width / 2

        # Generate hexagon points string for SVG path
        hex_points = self._generate_hex_points_string()

        # Calculate legend title position relative to legend
        legend_title_x = legend_x + legend_width + DEFAULT_LEGEND_OFFSET
        legend_title_y = legend_y + DEFAULT_LEGEND_HEIGHT // 2

        return LayoutConfig(
            width=int(svg_width),
            height=int(svg_height),
            min_x=bounds["min_x"],
            min_y=bounds["min_y"],
            margin=self.margin,
            legend_x=legend_x,
            title_x=title_x,
            hex_points=hex_points,
            legend_y=legend_y,
            legend_title_x=legend_title_x,
            legend_title_y=legend_title_y,
            layer_control_x=layer_control_x,
            layer_control_y=layer_control_y,
        )

    def calculate_legend_config(
        self,
        hexagons: List[Dict[str, Any]],
        thresholds: Optional[Dict[str, Any]] = None,
        metric_type: str = "synapse_density",
    ) -> Optional[LegendConfig]:
        """
        Calculate legend configuration based on hexagon data.

        Args:
            hexagons: List of hexagon data dictionaries
            thresholds: Threshold values for color scales
            metric_type: Type of metric being displayed

        Returns:
            LegendConfig object or None if no legend needed
        """
        # Filter to hexagons with actual data
        data_hexagons = [h for h in hexagons if h.get("status") == "has_data"]

        if not data_hexagons:
            return None

        # Determine legend labels based on metric type
        if metric_type == "synapse_density":
            legend_title = "Total Synapses"
            legend_type_name = "Synapses"
        else:
            legend_title = "Cell Count"
            legend_type_name = "Cells"

        # Calculate legend positioning
        legend_height = DEFAULT_LEGEND_HEIGHT
        bin_height = legend_height // 5
        title_y = legend_height // 2

        return LegendConfig(
            legend_title=legend_title,
            legend_type_name=legend_type_name,
            title_y=title_y,
            bin_height=bin_height,
            thresholds=thresholds.get("all", []) if thresholds else None,
            layer_thresholds=thresholds.get("layers", {}) if thresholds else None,
        )

    def _calculate_bounds(self, hexagons: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate the bounding box for all hexagons.

        Args:
            hexagons: List of hexagon data dictionaries

        Returns:
            Dictionary with min_x, max_x, min_y, max_y values
        """
        if not hexagons:
            return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0}

        x_coords = [float(h["x"]) for h in hexagons if "x" in h]
        y_coords = [float(h["y"]) for h in hexagons if "y" in h]

        if not x_coords or not y_coords:
            return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0}

        # Add hexagon radius to account for hexagon size
        min_x = min(x_coords) - self.hex_radius
        max_x = max(x_coords) + self.hex_radius
        min_y = min(y_coords) - self.hex_radius
        max_y = max(y_coords) + self.hex_radius

        return {"min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y}

    def _generate_hex_points_string(self) -> str:
        """
        Generate SVG path points string for hexagon shape.

        Returns:
            Space-separated string of hexagon vertex coordinates
        """
        points = []
        for i in range(6):
            angle = math.pi / 3 * i  # 60 degrees in radians
            x = self.hex_radius * math.cos(angle)
            y = self.hex_radius * math.sin(angle)
            points.append(f"{x:.2f},{y:.2f}")

        return " ".join(points)

    def _calculate_control_space_from_dimensions(
        self, control_dimensions: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate the minimum space needed for layer controls from control dimensions.

        Args:
            control_dimensions: Control dimensions from region config

        Returns:
            Dictionary with min_width and min_height values
        """
        layer_button_width = control_dimensions.get("layer_button_width", 40)
        total_control_height = control_dimensions.get("total_control_height", 200)

        # Minimum dimensions to accommodate controls
        min_width = layer_button_width + 4 * self.margin + 50  # Extra space for legend
        min_height = total_control_height + 4 * self.margin

        return {"min_width": min_width, "min_height": min_height}

    def _calculate_layer_control_position(
        self,
        svg_width: float,
        svg_height: float,
        soma_side: Optional[SomaSide] = None,
        control_dimensions: Optional[Dict[str, float]] = None,
    ) -> Tuple[float, float]:
        """
        Calculate the position for layer controls based on soma side and control dimensions.

        Args:
            svg_width: SVG width
            svg_height: SVG height
            soma_side: Side of soma (SomaSide enum)
            control_dimensions: Control dimensions from region config

        Returns:
            Tuple of (control_x, control_y) coordinates
        """
        if not control_dimensions:
            control_dimensions = {
                "layer_button_width": DEFAULT_LAYER_BUTTON_WIDTH,
                "total_control_height": DEFAULT_TOTAL_CONTROL_HEIGHT,
            }

        layer_button_width = control_dimensions.get("layer_button_width", 40)
        total_control_height = control_dimensions.get("total_control_height", 200)

        # Calculate horizontal position based on soma side
        if soma_side == SomaSide.LEFT:
            # Left side eyemap: controls in bottom right corner
            control_x = svg_width - layer_button_width - self.margin
        else:
            # Right side eyemap: controls in bottom left corner
            control_x = self.margin + 15

        # Calculate vertical position (controls at bottom)
        control_y = svg_height - total_control_height / 2 - self.margin

        return control_x, control_y



