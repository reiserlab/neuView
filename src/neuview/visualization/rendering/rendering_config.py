"""
Configuration classes and enums for the rendering system.

This module defines the configuration structures used by the rendering system
to control output format, layout parameters, and rendering behavior.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from ...utils import get_templates_dir
from ..data_processing.data_structures import SomaSide


class OutputFormat(Enum):
    """Supported output formats for rendering."""

    SVG = "svg"
    PNG = "png"


@dataclass
class RenderingConfig:
    """
    Configuration for rendering operations.

    This class encapsulates all the parameters needed to control
    the rendering process, including output format, layout settings,
    and file management options.
    """

    # Output configuration
    output_format: OutputFormat = OutputFormat.SVG
    embed_mode: bool = False
    save_to_files: bool = True

    # File management
    output_dir: Optional[Path] = None
    eyemaps_dir: Optional[Path] = None

    # Layout configuration
    hex_size: int = 6
    spacing_factor: float = 1.1
    margin: int = 10

    # SVG-specific configuration
    template_name: str = "eyemap.svg.jinja"

    # PNG-specific configuration
    png_quality: int = 90
    png_scale: float = 1.0

    # Content configuration
    plot_desc: str = ""
    neuron_desc: str = ""
    region_desc: str = ""
    metric_type: str = ""
    soma_side: Optional[SomaSide] = None
    neuron_type: Optional[str] = None
    region_name: Optional[str] = None

    # Data configuration
    min_max_data: Optional[Dict[str, Any]] = None
    thresholds: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Post-initialization validation and setup."""
        if self.save_to_files and not self.output_dir:
            raise ValueError("output_dir must be set when save_to_files is True")

        if self.eyemaps_dir is None and self.output_dir:
            self.eyemaps_dir = self.output_dir / "eyemaps"

    @property
    def should_save_files(self) -> bool:
        """Check if files should be saved to disk."""
        return (
            self.save_to_files and not self.embed_mode and self.output_dir is not None
        )

    def get_template_path(self) -> Optional[Path]:
        """Get the full path to the template file."""
        # Templates are now loaded from the built-in templates directory
        return get_templates_dir() / self.template_name

    def get_clean_filename(self, base_filename: str) -> str:
        """Get a cleaned filename suitable for file system use."""
        clean_name = base_filename.replace(" ", "_").replace("(", "").replace(")", "")
        extension = ".svg" if self.output_format == OutputFormat.SVG else ".png"
        return clean_name + extension

    def copy(self, **overrides) -> "RenderingConfig":
        """Create a copy of this config with optional overrides."""
        from dataclasses import replace

        return replace(self, **overrides)


@dataclass
class LayoutConfig:
    """
    Configuration for layout calculations.

    This class contains parameters specific to layout computation
    and coordinate transformations.
    """

    width: int = 0
    height: int = 0
    min_x: float = 0.0
    min_y: float = 0.0
    margin: int = 10
    legend_x: float = 0.0
    title_x: float = 0.0
    hex_points: str = ""

    # Legend configuration
    legend_width: int = 12
    legend_height: int = 60
    legend_y: float = 0.0
    legend_title_x: float = 0.0
    legend_title_y: float = 0.0

    # Layer control configuration
    layer_control_x: float = 0.0
    layer_control_y: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert layout config to dictionary for template rendering."""
        return {
            "width": self.width,
            "height": self.height,
            "min_x": self.min_x,
            "min_y": self.min_y,
            "margin": self.margin,
            "legend_x": self.legend_x,
            "title_x": self.title_x,
            "hex_points": self.hex_points,
            "legend_width": self.legend_width,
            "legend_height": self.legend_height,
            "legend_y": self.legend_y,
            "legend_title_x": self.legend_title_x,
            "legend_title_y": self.legend_title_y,
            "layer_control_x": self.layer_control_x,
            "layer_control_y": self.layer_control_y,
        }


@dataclass
class LegendConfig:
    """
    Configuration for legend rendering.

    This class contains parameters for rendering the color legend
    and associated UI elements.
    """

    legend_title: str = ""
    legend_type_name: str = ""
    title_y: float = 0.0
    bin_height: int = 12
    thresholds: Optional[Dict[str, Any]] = None
    layer_thresholds: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert legend config to dictionary for template rendering."""
        return {
            "legend_title": self.legend_title,
            "legend_type_name": self.legend_type_name,
            "title_y": self.title_y,
            "bin_height": self.bin_height,
            "thresholds": self.thresholds,
            "layer_thresholds": self.layer_thresholds,
        }


@dataclass
class ScatterConfig:
    """
    Configuration for scatterplot rendering.
    """

    # Output configuration
    output_format: str = "svg"
    save_to_files: bool = True

    # File management
    scatter_dir: Optional[Path] = "output/scatter"

    # Layout configuration — margins ordered (top, right, bottom, left)
    margins: tuple[int, int, int, int] = (60, 72, 64, 50)
    width: int = 480
    height: int = 480
    axis_gap_px: int = 10
    legend_w: int = 12

    # Marker features
    marker_size: int = 4
    marker_line_width: float = 0.5

    # SVG-specific configuration
    template_name: str = "scatterplot.svg.jinja"

    # Content configuration
    title: str = ""
    xlabel: str = "Population size"
    xlabel_hover: str = "cells per type per eye"
    ylabel: str = "Cell size"
    ylabel_hover: str = "median columns per cell"
    legend_label: str = "Coverage factor"
    legend_label_hover: str = "mean cells per column"

    # Axis range on log10 scale. Fixed so ME/LO/LOP and L/R plots are
    # directly comparable across regions and hemispheres.
    axis_min: float = 1.0
    axis_max: float = 1000.0

    # Tick marks
    xticks: list[int] = field(default_factory=lambda: [1, 10, 100, 1000])
    yticks: list[int] = field(default_factory=lambda: [1, 10, 100, 1000])

    # Data configuration
    min_max_data: Optional[Dict[str, Any]] = None
    thresholds: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        (
            self.margin_top,
            self.margin_right,
            self.margin_bottom,
            self.margin_left,
        ) = self.margins
        plot_w = self.width - self.margin_left - self.margin_right
        plot_h = self.height - self.margin_top - self.margin_bottom
        # Square plot area so ME/LO/LOP plots line up across pages.
        self.plot_w = self.plot_h = min(plot_w, plot_h)

    def get_template_path(self) -> Optional[Path]:
        """Get the full path to the template file."""
        # Templates are now loaded from the built-in templates directory
        return get_templates_dir() / self.template_name

    def to_dict(self) -> Dict[str, Any]:
        """Convert layout config to dictionary for template rendering."""
        return {
            "width": self.width,
            "height": self.height,
            "xticks": self.xticks,
            "yticks": self.yticks,
            "marker_size": self.marker_size,
            "margin_top": self.margin_top,
            "margin_right": self.margin_right,
            "margin_bottom": self.margin_bottom,
            "margin_left": self.margin_left,
            "legend_w": self.legend_w,
            "xlabel": self.xlabel,
            "xlabel_hover": self.xlabel_hover,
            "ylabel": self.ylabel,
            "ylabel_hover": self.ylabel_hover,
            "legend_label": self.legend_label,
            "legend_label_hover": self.legend_label_hover,
            "axis_gap_px": self.axis_gap_px,
            "plot_h": self.plot_h,
            "plot_w": self.plot_w,
        }

    def copy(self, **overrides) -> "ScatterConfig":
        """Create a copy of this config with optional overrides."""
        from dataclasses import replace

        return replace(self, **overrides)
