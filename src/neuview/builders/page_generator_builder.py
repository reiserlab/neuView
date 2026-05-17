"""
PageGenerator Builder

This builder provides a fluent interface for constructing PageGenerator instances
with different configurations, using dependency injection containers for improved
testability and maintainability.
"""

import logging
from pathlib import Path
from typing import Optional

from ..config import Config
from ..services.page_generation_container import PageGenerationContainer

logger = logging.getLogger(__name__)


class PageGeneratorBuilder:
    """Builder pattern for PageGenerator configuration and creation."""

    def __init__(self):
        """Initialize builder with default values."""
        self._config: Optional[Config] = None
        self._output_dir: Optional[str] = None
        self._queue_service = None
        self._cache_manager = None
        self._use_container: bool = True
        self._validate_config: bool = True
        self._container: Optional[PageGenerationContainer] = None

    def with_config(self, config: Config):
        """
        Set the configuration object.

        Args:
            config: Configuration object with template and output settings

        Returns:
            Self for method chaining
        """
        self._config = config
        return self

    def with_output_directory(self, output_dir: str):
        """
        Set the output directory path.

        Args:
            output_dir: Directory path for generated HTML files

        Returns:
            Self for method chaining
        """
        self._output_dir = output_dir
        return self

    def with_queue_service(self, queue_service):
        """
        Set the queue service.

        Args:
            queue_service: QueueService for checking queued neuron types

        Returns:
            Self for method chaining
        """
        self._queue_service = queue_service
        return self

    def with_cache_manager(self, cache_manager):
        """
        Set the cache manager.

        Args:
            cache_manager: Cache manager for accessing cached neuron data

        Returns:
            Self for method chaining
        """
        self._cache_manager = cache_manager
        return self

    def skip_config_validation(self, skip: bool = True):
        """
        Control whether to validate configuration before building.

        Args:
            skip: If True, skip validation; if False, validate

        Returns:
            Self for method chaining
        """
        self._validate_config = not skip
        return self

    def with_dependency_injection(self, use_container: bool = True):
        """
        Control whether to use dependency injection container.

        Args:
            use_container: If True, use DI container; if False, use factory

        Returns:
            Self for method chaining
        """
        self._use_container = use_container
        return self


    def build(self):
        """
        Build and return configured PageGenerator instance.

        Returns:
            Configured PageGenerator instance

        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If configuration validation fails
        """
        self._validate_required_parameters()

        if self._validate_config:
            self._validate_configuration()

        if self._use_container:
            return self._build_with_container()
        else:
            return self._build_with_factory()


    def build_with_minimal_container(self):
        """
        Build PageGenerator with minimal dependency injection container for testing.

        Returns:
            PageGenerator instance with minimal DI container
        """
        self._validate_required_parameters()

        # Type assertions after validation
        assert self._config is not None
        assert self._output_dir is not None

        logger.info("Building PageGenerator with minimal DI container")

        # Create minimal container
        container = PageGenerationContainer(self._config)

        # Register optional services if provided
        if self._queue_service:
            container.register_singleton("queue_service", self._queue_service)
        if self._cache_manager:
            container.register_singleton("cache_manager", self._cache_manager)

        return self._build_page_generator_with_container(container)

    def _validate_required_parameters(self):
        """Validate that required parameters are set."""
        if self._config is None:
            raise ValueError("Configuration is required. Use with_config() to set it.")

        if self._output_dir is None:
            raise ValueError(
                "Output directory is required. Use with_output_directory() to set it."
            )

    def _validate_configuration(self):
        """Validate that the configuration is suitable for PageGenerator creation."""
        try:
            # Type assertions - these should already be validated by _validate_required_parameters
            assert self._config is not None
            assert self._output_dir is not None

            if not hasattr(self._config, "output"):
                raise RuntimeError("Configuration missing 'output' section")

            if not hasattr(self._config.output, "directory"):
                raise RuntimeError("Configuration missing 'output.directory'")

            # Check that output directory is writable
            output_dir = Path(self._output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            if not output_dir.is_dir():
                raise RuntimeError(f"Cannot create output directory: {output_dir}")

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise RuntimeError(f"Invalid configuration: {e}")

    def _build_with_container(self):
        """Build PageGenerator using dependency injection container."""
        # Type assertions - these should already be validated
        assert self._config is not None
        assert self._output_dir is not None

        logger.info("Building PageGenerator with dependency injection container")

        if self._container:
            # Use provided container
            container = self._container
        else:
            # Create new container
            container = PageGenerationContainer(self._config)

            # Register optional services
            if self._queue_service:
                container.register_singleton("queue_service", self._queue_service)
            if self._cache_manager:
                container.register_singleton("cache_manager", self._cache_manager)

        return self._build_page_generator_with_container(container)

    def _build_page_generator_with_container(self, container: PageGenerationContainer):
        """Build PageGenerator using the provided container."""
        # Type assertions - these should already be validated
        assert self._config is not None
        assert self._output_dir is not None

        # Configure core services
        container.configure_data_services()
        container.configure_template_environment()

        # Create PageGenerator with container services
        from ..page_generator import PageGenerator

        # Create services dict for PageGenerator
        services = {
            "brain_region_service": container.get("brain_region_service"),
            "citation_service": container.get("citation_service"),
            "partner_analysis_service": container.get("partner_analysis_service"),
            "jinja_template_service": container.get("jinja_template_service"),
            "neuron_search_service": container.get("neuron_search_service"),
            "brain_regions": container.get("brain_regions"),
            "citations": container.get("citations"),
            "resource_manager": container.get("resource_manager"),
            "types_dir": container.get("resource_manager").setup_output_directories()[
                "types"
            ],
            "eyemaps_dir": container.get("resource_manager").setup_output_directories()[
                "eyemaps"
            ],
            "hexagon_generator": container.get("hexagon_generator"),
            "template_env": container.get("template_env"),
        }

        # Add utility services
        services.update(
            {
                "color_utils": container.get("color_utils"),
                "html_utils": container.get("html_utils"),
                "text_utils": container.get("text_utils"),
                "number_formatter": container.get("number_formatter"),
                "percentage_formatter": container.get("percentage_formatter"),
                "synapse_formatter": container.get("synapse_formatter"),
                "neurotransmitter_formatter": container.get(
                    "neurotransmitter_formatter"
                ),
                "layer_analysis_service": container.get("layer_analysis_service"),
                "neuron_selection_service": container.get("neuron_selection_service"),
                "file_service": container.get("file_service"),
                "threshold_service": container.get("threshold_service"),
                "youtube_service": container.get("youtube_service"),
                "all_columns_cache": None,
                "column_analysis_cache": {},
            }
        )

        # Create PageGenerator
        page_generator = PageGenerator(
            config=self._config,
            output_dir=self._output_dir,
            queue_service=self._queue_service,
            cache_manager=self._cache_manager,
            services=services,
        )

        # Configure PageGenerator-dependent services
        container.configure_page_generator_services(page_generator)

        # Assign services to PageGenerator
        page_generator.template_context_service = container.get(
            "template_context_service"
        )
        page_generator.data_processing_service = container.get(
            "data_processing_service"
        )
        page_generator.cache_service = container.get("cache_service")
        page_generator.roi_analysis_service = container.get("roi_analysis_service")
        page_generator.column_analysis_service = container.get(
            "column_analysis_service"
        )
        page_generator.url_generation_service = container.get("url_generation_service")
        page_generator.orchestrator = container.get("orchestrator")

        # Copy static files
        container.get("resource_manager").copy_static_files()

        return page_generator

    def _build_with_factory(self):
        """Build PageGenerator using the service factory."""
        # Type assertions - these should already be validated
        assert self._config is not None
        assert self._output_dir is not None

        logger.info("Building PageGenerator with service factory")

        from ..page_generator import PageGenerator

        return PageGenerator.create_with_factory(
            config=self._config,
            output_dir=self._output_dir,
            queue_service=self._queue_service,
            cache_manager=self._cache_manager,
        )

    @classmethod
    def create(cls):
        """
        Create a new builder instance.

        Returns:
            New PageGeneratorBuilder instance
        """
        return cls()

    @classmethod
    def default_config(cls, config: Config, output_dir: str):
        """
        Create a builder with default configuration.

        Args:
            config: Configuration object
            output_dir: Output directory path

        Returns:
            Configured builder ready to build
        """
        return cls().with_config(config).with_output_directory(output_dir)

