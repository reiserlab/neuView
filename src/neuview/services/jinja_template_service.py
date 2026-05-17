"""
Jinja template service for managing Jinja2 environment and template operations.

This service manages the setup and configuration of Jinja2 template environments,
including custom filters, template loading, and rendering operations.
"""

from pathlib import Path
import logging
from typing import Dict, Any, Optional, Callable
from jinja2 import Environment, FileSystemLoader, Template

logger = logging.getLogger(__name__)


class JinjaTemplateService:
    """
    Service for managing Jinja2 template environment and operations.

    This service handles:
    - Jinja2 environment setup and configuration
    - Custom filter registration
    - Template loading and caching
    - Template rendering with context
    - Template directory management
    """

    def __init__(self, template_dir: Path, config=None):
        """
        Initialize the Jinja template service.

        Args:
            template_dir: Directory containing template files
            config: Optional configuration object (for future extensibility)
        """
        self.template_dir = Path(template_dir)
        self.config = config
        self.env: Environment = None  # Will be initialized in setup_jinja_env
        self._custom_filters: Dict[str, Callable] = {}
        self._initialized = False

    def setup_jinja_env(self, utility_services: Dict[str, Any]) -> Environment:
        """
        Set up Jinja2 environment with templates and custom filters.

        Args:
            utility_services: Dictionary containing utility service instances
                Expected keys:
                - number_formatter
                - percentage_formatter
                - synapse_formatter
                - neurotransmitter_formatter
                - html_utils
                - text_utils
                - color_utils
                - roi_abbr_filter (function)
                - get_partner_body_ids (function)

        Returns:
            Configured Jinja2 Environment

        Raises:
            FileNotFoundError: If template directory doesn't exist
            ValueError: If required utility services are missing
        """
        # Create template directory if it doesn't exist
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Register custom filters
        self._register_utility_filters(utility_services)

        self._initialized = True
        logger.info(
            f"Jinja2 environment initialized with template directory: {self.template_dir}"
        )

        return self.env

    def _register_utility_filters(self, utility_services: Dict[str, Any]) -> None:
        """
        Register utility-based custom filters with the Jinja environment.

        Args:
            utility_services: Dictionary containing utility service instances
        """
        # Number and formatting filters
        if "number_formatter" in utility_services:
            formatter = utility_services["number_formatter"]
            self.env.filters["format_number"] = formatter.format_number

        if "percentage_formatter" in utility_services:
            formatter = utility_services["percentage_formatter"]
            self.env.filters["format_percentage"] = formatter.format_percentage
            # Add backward compatibility filter
            if hasattr(formatter, "format_percentage_5"):
                self.env.filters["format_percentage_5"] = formatter.format_percentage_5

        if "synapse_formatter" in utility_services:
            formatter = utility_services["synapse_formatter"]
            self.env.filters["format_synapse_count"] = formatter.format_synapse_count
            self.env.filters["format_conn_count"] = formatter.format_conn_count

        if "neurotransmitter_formatter" in utility_services:
            formatter = utility_services["neurotransmitter_formatter"]
            self.env.filters["abbreviate_neurotransmitter"] = (
                formatter.abbreviate_neurotransmitter
            )

        if "mathematical_formatter" in utility_services:
            formatter = utility_services["mathematical_formatter"]
            self.env.filters["log_ratio"] = formatter.log_ratio
            # Also register as a global function for function-call syntax
            self.env.globals["log_ratio"] = formatter.log_ratio

        # HTML and text utility filters
        if "html_utils" in utility_services:
            html_utils = utility_services["html_utils"]
            self.env.filters["is_png_data"] = html_utils.is_png_data

            # Create neuron link filter with queue service support
            queue_service = utility_services.get("queue_service")
            self.env.filters["neuron_link"] = (
                lambda neuron_type, soma_side: html_utils.create_neuron_link(
                    neuron_type, soma_side, queue_service
                )
            )

        if "text_utils" in utility_services:
            text_utils = utility_services["text_utils"]
            self.env.filters["truncate_neuron_name"] = text_utils.truncate_neuron_name

        # Color utility filters
        if "color_utils" in utility_services:
            color_utils = utility_services["color_utils"]
            self.env.filters["synapses_to_colors"] = color_utils.synapses_to_colors
            self.env.filters["neurons_to_colors"] = color_utils.neurons_to_colors

        # ROI and partner analysis filters
        if "roi_abbr_filter" in utility_services:
            self.env.filters["roi_abbr"] = utility_services["roi_abbr_filter"]

        if "get_partner_body_ids" in utility_services:
            self.env.filters["get_partner_body_ids"] = utility_services[
                "get_partner_body_ids"
            ]

        logger.debug(f"Registered {len(self.env.filters)} custom filters")

    def add_custom_filter(self, name: str, filter_func: Callable) -> None:
        """
        Add a custom filter to the Jinja environment.

        Args:
            name: Name of the filter
            filter_func: Function to use as filter

        Raises:
            RuntimeError: If environment is not initialized
        """
        if not self._initialized:
            # Store for later registration
            self._custom_filters[name] = filter_func
        else:
            self.env.filters[name] = filter_func

        logger.debug(f"Added custom filter: {name}")

    def get_template(self, template_name: str) -> Template:
        """
        Get a template by name.

        Args:
            template_name: Name of the template file (relative to template_dir)

        Returns:
            Jinja2 Template object

        Raises:
            RuntimeError: If environment is not initialized
            TemplateNotFound: If template file doesn't exist
        """
        if not self._initialized or self.env is None:
            raise RuntimeError(
                "Jinja environment not initialized. Call setup_jinja_env() first."
            )

        return self.env.get_template(template_name)

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template file
            context: Dictionary of variables to pass to template

        Returns:
            Rendered template content

        Raises:
            RuntimeError: If environment is not initialized
            TemplateNotFound: If template file doesn't exist
        """
        template = self.get_template(template_name)
        return template.render(**context)



    def list_templates(self) -> list[str]:
        """
        Get a list of all available templates.

        Returns:
            List of template names

        Raises:
            RuntimeError: If environment is not initialized
        """
        if not self._initialized or self.env is None:
            raise RuntimeError(
                "Jinja environment not initialized. Call setup_jinja_env() first."
            )

        return self.env.list_templates()



    def get_environment(self) -> Optional[Environment]:
        """
        Get the Jinja2 environment instance.

        Returns:
            Environment instance if initialized, None otherwise
        """
        return self.env



    def add_global(self, name: str, value: Any) -> None:
        """
        Add a global variable to the template environment.

        Args:
            name: Name of the global variable
            value: Value of the global variable

        Raises:
            RuntimeError: If environment is not initialized
        """
        if not self._initialized or self.env is None:
            raise RuntimeError(
                "Jinja environment not initialized. Call setup_jinja_env() first."
            )

        self.env.globals[name] = value
        logger.debug(f"Added global variable: {name}")

