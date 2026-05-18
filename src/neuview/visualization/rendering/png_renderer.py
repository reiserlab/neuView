"""
PNG renderer for hexagon grid visualizations.

This module provides PNG-specific rendering functionality by converting
SVG content to PNG format using cairosvg library.
"""

import base64
import io
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

import cairosvg
from PIL import Image

from .base_renderer import BaseRenderer
from .svg_renderer import SVGRenderer
from .rendering_config import RenderingConfig, LayoutConfig, LegendConfig, OutputFormat

logger = logging.getLogger(__name__)


class PNGRenderer(BaseRenderer):
    """
    PNG renderer for hexagon grid visualizations.

    This renderer generates PNG content by first creating SVG content
    using the SVGRenderer and then converting it to PNG format using cairosvg.
    """

    def __init__(self, config: RenderingConfig, color_mapper=None):
        """
        Initialize the PNG renderer.

        Args:
            config: Rendering configuration object
            color_mapper: Color mapping utility (for SVG generation)
        """
        # Ensure output format is PNG
        if config.output_format != OutputFormat.PNG:
            config = config.copy(output_format=OutputFormat.PNG)

        super().__init__(config)
        self.color_mapper = color_mapper

        # Create SVG renderer for intermediate SVG generation
        svg_config = config.copy(output_format=OutputFormat.SVG)
        self.svg_renderer = SVGRenderer(svg_config, color_mapper)

    def render(
        self,
        hexagons: List[Dict[str, Any]],
        layout_config: LayoutConfig,
        legend_config: Optional[LegendConfig] = None,
    ) -> str:
        """
        Render hexagons to PNG format.

        Args:
            hexagons: List of hexagon data dictionaries
            layout_config: Layout configuration for positioning
            legend_config: Optional legend configuration

        Returns:
            PNG content as base64 data URL string
        """
        self.validate_hexagons(hexagons)

        if not hexagons:
            logger.warning("No hexagons provided for PNG rendering")
            return ""

        try:
            # First generate SVG content
            svg_content = self.svg_renderer.render(
                hexagons, layout_config, legend_config
            )

            if not svg_content:
                logger.warning("SVG renderer returned empty content")
                return ""

            # Convert SVG to PNG
            png_data_url = self._convert_svg_to_png(svg_content)

            logger.debug(f"Successfully rendered PNG with {len(hexagons)} hexagons")
            return png_data_url

        except Exception as e:
            logger.error(f"Failed to render PNG: {e}")
            raise ValueError(f"PNG rendering failed: {e}")

    def get_file_extension(self) -> str:
        """Get the file extension for PNG files."""
        return ".png"

    def supports_interactive_features(self) -> bool:
        """PNG does not support interactive features."""
        return False

    def _write_content_to_file(self, content: str, file_path: Path) -> None:
        """
        Write PNG content to file.

        Args:
            content: PNG data URL content to write
            file_path: Path to write to
        """
        # Extract base64 data from data URL
        if not content.startswith("data:image/png;base64,"):
            raise ValueError("Invalid PNG data URL format")

        base64_data = content.split(",", 1)[1]

        # Write binary PNG data
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(base64_data))

    def _convert_svg_to_png(self, svg_content: str) -> str:
        """
        Convert SVG content to PNG format.

        Args:
            svg_content: SVG content as string

        Returns:
            PNG content as base64 data URL string

        Raises:
            ImportError: If cairosvg is not available
            ValueError: If conversion fails
        """
        try:
            # Create PNG buffer
            png_buffer = io.BytesIO()

            # Convert SVG to PNG with configuration options
            cairosvg.svg2png(
                bytestring=svg_content.encode("utf-8"),
                write_to=png_buffer,
                scale=int(self.config.png_scale),
                output_width=None,  # Maintain aspect ratio
                output_height=None,  # Maintain aspect ratio
            )

            # Get PNG data and encode as base64
            png_buffer.seek(0)
            png_data = png_buffer.getvalue()
            base64_data = base64.b64encode(png_data).decode("utf-8")

            return f"data:image/png;base64,{base64_data}"

        except Exception as e:
            logger.error(f"Failed to convert SVG to PNG: {e}")
            raise ValueError(f"SVG to PNG conversion failed: {e}")




    def update_config(self, **config_updates) -> None:
        """
        Update rendering configuration and reset cached components.

        Args:
            **config_updates: Configuration parameters to update
        """
        self.config = self.config.copy(**config_updates)

        # Update SVG renderer configuration
        svg_config_updates = {
            k: v for k, v in config_updates.items() if k not in ["output_format"]
        }
        if svg_config_updates:
            self.svg_renderer.update_config(**svg_config_updates)

