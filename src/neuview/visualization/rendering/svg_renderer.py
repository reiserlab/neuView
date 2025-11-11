"""
SVG renderer for hexagon grid visualizations.

This module provides SVG-specific rendering functionality using Jinja2 templates
to generate interactive SVG visualizations with tooltips and legends.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from jinja2 import Environment, FileSystemLoader, Template

from .base_renderer import BaseRenderer
from .rendering_config import RenderingConfig, LayoutConfig, LegendConfig, OutputFormat
from .layout_calculator import LayoutCalculator
from ...utils import get_templates_dir

logger = logging.getLogger(__name__)


class SVGRenderer(BaseRenderer):
    """
    SVG renderer for hexagon grid visualizations.

    This renderer generates interactive SVG content using Jinja2 templates,
    supporting features like tooltips, legends, and layer controls.
    """

    def __init__(self, config: RenderingConfig, color_mapper=None):
        """
        Initialize the SVG renderer.

        Args:
            config: Rendering configuration object
            color_mapper: Color mapping utility (for template filters)
        """
        # Ensure output format is SVG
        if config.output_format != OutputFormat.SVG:
            config = config.copy(output_format=OutputFormat.SVG)

        super().__init__(config)
        self.color_mapper = color_mapper
        self.layout_calculator = LayoutCalculator(
            hex_size=config.hex_size,
            spacing_factor=config.spacing_factor,
            margin=config.margin,
        )
        self._template_env = None
        self._template = None

    def render(
        self,
        hexagons: List[Dict[str, Any]],
        layout_config: LayoutConfig,
        legend_config: Optional[LegendConfig] = None,
    ) -> str:
        """
        Render hexagons to SVG format.

        Args:
            hexagons: List of hexagon data dictionaries
            layout_config: Layout configuration for positioning
            legend_config: Optional legend configuration

        Returns:
            SVG content as string
        """
        self.validate_hexagons(hexagons)

        if not hexagons:
            logger.warning("No hexagons provided for SVG rendering")
            return ""

        try:
            # Process hexagons with tooltips
            processed_hexagons = self._add_tooltips_to_hexagons(hexagons)

            # Setup template environment
            template = self._get_template()

            # Prepare template variables
            template_vars = self._prepare_template_variables(
                processed_hexagons, layout_config, legend_config
            )

            # Render SVG content
            svg_content = template.render(**template_vars)

            logger.debug(f"Successfully rendered SVG with {len(hexagons)} hexagons")
            return svg_content

        except Exception as e:
            logger.error(f"Failed to render SVG: {e}")
            raise ValueError(f"SVG rendering failed: {e}")

    def get_file_extension(self) -> str:
        """Get the file extension for SVG files."""
        return ".svg"

    def supports_interactive_features(self) -> bool:
        """SVG supports interactive features like tooltips and hover effects."""
        return True

    def _write_content_to_file(self, content: str, file_path: Path) -> None:
        """
        Write SVG content to file.

        Args:
            content: SVG content to write
            file_path: Path to write to
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _get_template(self) -> Template:
        """
        Get or load the Jinja2 template for SVG rendering.

        Returns:
            Jinja2 Template object

        Raises:
            ValueError: If template cannot be loaded
        """
        if self._template is not None:
            return self._template

        try:
            # Setup template environment
            if not self._template_env:
                template_dir = self._get_template_directory()
                self._template_env = Environment(loader=FileSystemLoader(template_dir))
                self._setup_template_filters()

            # Load template
            self._template = self._template_env.get_template(self.config.template_name)
            return self._template

        except Exception as e:
            logger.error(f"Failed to load SVG template: {e}")
            raise ValueError(f"Template loading failed: {e}")

    def _get_template_directory(self) -> str:
        """
        Get the template directory path.

        Returns:
            Path to template directory

        Raises:
            ValueError: If template directory cannot be found
        """
        # Always use built-in template directory
        pass

        # Use built-in templates directory
        template_dir = get_templates_dir()

        if not template_dir.exists():
            raise ValueError(f"Template directory not found: {template_dir}")

        return str(template_dir)

    def _setup_template_filters(self) -> None:
        """Setup custom Jinja2 filters for the template."""
        if not self._template_env or not self.color_mapper:
            return

        # Create filter functions that capture min_max_data for region-specific normalization
        min_max_data = self.config.min_max_data or {}

        def synapses_to_colors(synapses_list, region):
            """Convert synapses_list to synapse_colors using normalization."""
            if not synapses_list or not min_max_data or not self.color_mapper:
                return ["#ffffff"] * len(synapses_list) if synapses_list else []

            syn_min = float(min_max_data.get("min_syn_region", {}).get(region, 0.0))
            syn_max = float(min_max_data.get("max_syn_region", {}).get(region, 0.0))

            colors = []
            for syn_val in synapses_list:
                if syn_val > 0:
                    color = self.color_mapper.map_value_to_color(
                        float(syn_val), syn_min, syn_max
                    )
                else:
                    color = getattr(self.color_mapper.palette, "white", "#ffffff")
                colors.append(color)

            return colors

        def neurons_to_colors(neurons_list, region):
            """Convert neurons_list to neuron_colors using normalization."""
            if not neurons_list or not min_max_data or not self.color_mapper:
                return ["#ffffff"] * len(neurons_list) if neurons_list else []

            cel_min = float(min_max_data.get("min_cells_region", {}).get(region, 0.0))
            cel_max = float(min_max_data.get("max_cells_region", {}).get(region, 0.0))

            colors = []
            for cel_val in neurons_list:
                if cel_val > 0:
                    color = self.color_mapper.map_value_to_color(
                        float(cel_val), cel_min, cel_max
                    )
                else:
                    color = getattr(self.color_mapper.palette, "white", "#ffffff")
                colors.append(color)

            return colors

        # Register filters
        self._template_env.filters["synapses_to_colors"] = synapses_to_colors
        self._template_env.filters["neurons_to_colors"] = neurons_to_colors

    def _prepare_template_variables(
        self,
        hexagons: List[Dict[str, Any]],
        layout_config: LayoutConfig,
        legend_config: Optional[LegendConfig],
    ) -> Dict[str, Any]:
        """
        Prepare variables for template rendering.

        Args:
            hexagons: Processed hexagon data
            layout_config: Layout configuration
            legend_config: Optional legend configuration

        Returns:
            Dictionary of template variables
        """
        # Get data hexagons for legend
        data_hexagons = [h for h in hexagons if h.get("status") == "has_data"]

        # Prepare template variables
        template_vars = {
            "width": layout_config.width,
            "height": layout_config.height,
            "title": self.config.title,
            "subtitle1": self.config.subtitle1,
            "subtitle2": self.config.subtitle2,
            "hexagons": hexagons,
            "hex_points": layout_config.hex_points.split(),
            "min_x": layout_config.min_x,
            "min_y": layout_config.min_y,
            "margin": layout_config.margin,
            "number_precision": 2,
            "data_hexagons": data_hexagons,
            "legend_x": layout_config.legend_x,
            "legend_y": layout_config.legend_y,
            "legend_width": layout_config.legend_width,
            "legend_height": layout_config.legend_height,
            "legend_title_x": layout_config.legend_title_x,
            "legend_title_y": layout_config.legend_title_y,
            "title_x": layout_config.title_x,
            "layer_control_x": layout_config.layer_control_x,
            "layer_control_y": layout_config.layer_control_y,
            "enumerate": enumerate,
            "soma_side": self.config.soma_side,
            "min_max_data": self.config.min_max_data or {},
        }

        # Add color information if available
        if self.color_mapper and hasattr(self.color_mapper, "palette"):
            template_vars["colors"] = getattr(
                self.color_mapper.palette, "all_colors", lambda: []
            )()

        # Add legend configuration if available
        if legend_config:
            template_vars.update(legend_config.to_dict())

        return template_vars

    def _add_tooltips_to_hexagons(
        self, hexagons: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process tooltip data for hexagons with existing tooltip information.

        Args:
            hexagons: List of hexagon data dictionaries with existing tooltip data

        Returns:
            List of hexagons with tooltip data ready for SVG template processing
        """
        processed_hexagons = []

        for hexagon in hexagons:
            # Create a copy to avoid modifying original data
            processed_hex = hexagon.copy()

            # All hexagons must have tooltip data - no fallback generation
            if "tooltip" not in hexagon or "tooltip_layers" not in hexagon:
                raise ValueError(f"Hexagon missing required tooltip data: {hexagon}")

            # Keep tooltip data as-is for template processing
            # Template will handle JSON serialization using |tojson filter
            processed_hex["base_title"] = hexagon.get("tooltip", "")
            processed_hex["tooltip_layers"] = hexagon.get("tooltip_layers", [])

            processed_hexagons.append(processed_hex)

        return processed_hexagons

    def update_config(self, **config_updates) -> None:
        """
        Update rendering configuration and reset cached components.

        Args:
            **config_updates: Configuration parameters to update
        """
        self.config = self.config.copy(**config_updates)
        self._template = None
        self._template_env = None
        self.layout_calculator = LayoutCalculator(
            hex_size=self.config.hex_size,
            spacing_factor=self.config.spacing_factor,
            margin=self.config.margin,
        )
