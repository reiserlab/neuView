"""
Rendering manager for coordinating hexagon grid visualization rendering.

This module provides the main interface for rendering operations, managing
different renderers and coordinating the rendering pipeline from data to output.
"""

import logging
from typing import List, Dict, Any, Optional

from .base_renderer import BaseRenderer
from .svg_renderer import SVGRenderer
from .png_renderer import PNGRenderer
from .rendering_config import RenderingConfig, OutputFormat, LayoutConfig, LegendConfig
from .layout_calculator import LayoutCalculator

logger = logging.getLogger(__name__)


class RenderingManager:
    """
    Manager for coordinating hexagon grid rendering operations.

    This class provides a high-level interface for rendering hexagon grids,
    managing different output formats and coordinating the rendering pipeline.
    """

    def __init__(self, config: RenderingConfig, color_mapper=None):
        """
        Initialize the rendering manager.

        Args:
            config: Rendering configuration object
            color_mapper: Color mapping utility for renderers
        """
        self.config = config
        self.color_mapper = color_mapper
        self.layout_calculator = LayoutCalculator(
            hex_size=config.hex_size,
            spacing_factor=config.spacing_factor,
            margin=config.margin,
        )

        # Initialize renderers
        self._renderers = {}
        self._initialize_renderers()

    def _initialize_renderers(self) -> None:
        """Initialize available renderers based on configuration."""
        # Always initialize SVG renderer as it's required for PNG generation
        svg_config = self.config.copy(output_format=OutputFormat.SVG)
        self._renderers[OutputFormat.SVG] = SVGRenderer(svg_config, self.color_mapper)

        # Initialize PNG renderer
        png_config = self.config.copy(output_format=OutputFormat.PNG)
        self._renderers[OutputFormat.PNG] = PNGRenderer(png_config, self.color_mapper)

    def render(
        self,
        hexagons: List[Dict[str, Any]],
        output_format: Optional[OutputFormat] = None,
        layout_config: Optional[LayoutConfig] = None,
        legend_config: Optional[LegendConfig] = None,
        save_to_file: bool = False,
        filename: Optional[str] = None,
    ) -> str:
        """
        Render hexagons to the specified format.

        Args:
            hexagons: List of hexagon data dictionaries
            output_format: Output format (defaults to config format)
            layout_config: Optional custom layout configuration
            legend_config: Optional legend configuration
            save_to_file: Whether to save to file
            filename: Optional filename for saving

        Returns:
            Rendered content as string or file path if saved

        Raises:
            ValueError: If rendering fails or invalid parameters provided
        """
        if not hexagons:
            logger.warning("No hexagons provided for rendering")
            return ""

        # Use provided format or fall back to config
        format_to_use = output_format or self.config.output_format

        # Get appropriate renderer
        renderer = self._get_renderer(format_to_use)

        # Calculate layout if not provided
        if layout_config is None:
            # Extract region from first hexagon if available
            region = hexagons[0].get("region") if hexagons else None
            # Ensure soma_side is a SomaSide enum
            soma_side = self.config.soma_side
            if isinstance(soma_side, str):
                raise ValueError(
                    f"soma_side must be a SomaSide enum, not string: {soma_side}"
                )
            layout_config = self.layout_calculator.calculate_layout(
                hexagons, soma_side, region
            )

        # Calculate legend if not provided and hexagons have data
        if legend_config is None:
            legend_config = self.layout_calculator.calculate_legend_config(
                hexagons, self.config.thresholds, self.config.metric_type
            )

        # Validate renderer inputs
        renderer.validate_hexagons(hexagons)

        # Render content
        content = renderer.render(hexagons, layout_config, legend_config)

        # Save to file if requested
        if save_to_file and filename and self.config.should_save_files:
            return renderer.save_to_file(content, filename)

        return content

    def _get_renderer(self, output_format: OutputFormat) -> BaseRenderer:
        """
        Get renderer for the specified output format.

        Args:
            output_format: Desired output format

        Returns:
            Appropriate renderer instance

        Raises:
            ValueError: If format is not supported
        """
        if output_format not in self._renderers:
            raise ValueError(f"Unsupported output format: {output_format}")

        return self._renderers[output_format]


    def update_config(self, **config_updates) -> None:
        """
        Update rendering configuration for all renderers.

        Args:
            **config_updates: Configuration parameters to update
        """
        self.config = self.config.copy(**config_updates)

        # Update layout calculator
        self.layout_calculator = LayoutCalculator(
            hex_size=self.config.hex_size,
            spacing_factor=self.config.spacing_factor,
            margin=self.config.margin,
        )

        # Update all renderers
        for renderer in self._renderers.values():
            renderer.update_config(**config_updates)



    def validate_configuration(self) -> List[str]:
        """
        Validate the current configuration and return any issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        try:
            # Basic validation - check if config is valid
            if self.config.save_to_files and not self.config.output_dir:
                errors.append(
                    "Configuration error: output_dir must be set when save_to_files is True"
                )
        except Exception as e:
            errors.append(f"Configuration error: {e}")

        # Check template availability for SVG renderer
        if OutputFormat.SVG in self._renderers:
            svg_renderer = self._renderers[OutputFormat.SVG]
            try:
                svg_renderer._get_template_directory()
            except ValueError as e:
                errors.append(f"SVG template error: {e}")

        # Check if output directories exist when saving is enabled
        if self.config.save_to_files:
            if self.config.output_dir and not self.config.output_dir.exists():
                errors.append(
                    f"Output directory does not exist: {self.config.output_dir}"
                )

        return errors

    def cleanup(self) -> None:
        """Clean up resources used by renderers."""
        # Clear renderer cache
        self._renderers.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
