"""
neuView Facade - Phase 2 Refactoring

This facade provides a simplified interface for the neuView system,
hiding the complexity of service creation, dependency injection, and
configuration management behind a clean, easy-to-use API.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..config import Config
from ..builders.page_generator_builder import PageGeneratorBuilder

logger = logging.getLogger(__name__)


class NeuViewFacade:
    """
    Simplified facade for neuView functionality.

    This facade hides the complexity of service initialization, dependency
    injection, and configuration management, providing a clean API for
    external users who want to generate pages without dealing with
    internal implementation details.
    """

    def __init__(
        self, config: Optional[Config] = None, output_dir: Optional[str] = None
    ):
        """
        Initialize the neuView facade.

        Args:
            config: Optional configuration object. If not provided, will be created from defaults
            output_dir: Optional output directory. If not provided, uses config default
        """
        self._config = config
        self._output_dir = output_dir
        self._page_generator = None
        self._container = None
        self._queue_service = None
        self._cache_manager = None
        self._is_initialized = False

    @classmethod
    def create(
        cls, config_file: Optional[str] = None, output_dir: Optional[str] = None
    ) -> "NeuViewFacade":
        """
        Create a neuView facade with automatic configuration.

        Args:
            config_file: Optional path to configuration file
            output_dir: Optional output directory path

        Returns:
            Configured NeuViewFacade instance
        """
        if config_file:
            config = Config.from_file(config_file)
        else:
            config = Config.create_default()

        if not output_dir:
            output_dir = config.output.directory

        return cls(config=config, output_dir=output_dir)


    def with_queue_service(self, queue_service) -> "NeuViewFacade":
        """
        Configure the facade with a queue service.

        Args:
            queue_service: Queue service for checking queued neuron types

        Returns:
            Self for method chaining
        """
        self._queue_service = queue_service
        return self

    def with_cache_manager(self, cache_manager) -> "NeuViewFacade":
        """
        Configure the facade with a cache manager.

        Args:
            cache_manager: Cache manager for accessing cached neuron data

        Returns:
            Self for method chaining
        """
        self._cache_manager = cache_manager
        return self

    def with_config(self, config: Config) -> "NeuViewFacade":
        """
        Set the configuration.

        Args:
            config: Configuration object

        Returns:
            Self for method chaining
        """
        self._config = config
        self._is_initialized = False  # Reset initialization
        return self

    def with_output_directory(self, output_dir: str) -> "NeuViewFacade":
        """
        Set the output directory.

        Args:
            output_dir: Output directory path

        Returns:
            Self for method chaining
        """
        self._output_dir = output_dir
        self._is_initialized = False  # Reset initialization
        return self

    def initialize(self) -> None:
        """
        Initialize the facade and create the page generator.

        This method is called automatically when needed, but can be called
        explicitly for better control over initialization timing.
        """
        if self._is_initialized:
            return

        if not self._config:
            raise ValueError(
                "Configuration is required. Use with_config() or create() to set it."
            )

        if not self._output_dir:
            self._output_dir = self._config.output.directory

        logger.info(
            f"Initializing neuView facade with output directory: {self._output_dir}"
        )

        try:
            # Create PageGenerator using builder with dependency injection
            builder = (
                PageGeneratorBuilder.create()
                .with_config(self._config)
                .with_output_directory(self._output_dir)
                .with_dependency_injection(True)
            )

            if self._queue_service:
                builder.with_queue_service(self._queue_service)

            if self._cache_manager:
                builder.with_cache_manager(self._cache_manager)

            self._page_generator = builder.build()
            self._is_initialized = True

            logger.info("neuView facade initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize neuView facade: {e}")
            raise RuntimeError(f"Initialization failed: {e}")

    def generate_page(self, neuron_type: str, **kwargs) -> Dict[str, Any]:
        """
        Generate a page for the specified neuron type.

        Args:
            neuron_type: Name of the neuron type to generate page for
            **kwargs: Additional parameters for page generation

        Returns:
            Dictionary containing generation results and metadata

        Raises:
            RuntimeError: If generation fails
        """
        self._ensure_initialized()

        try:
            logger.info(f"Generating page for neuron type: {neuron_type}")

            # Use modern unified API
            from ..models.page_generation import PageGenerationRequest

            request = PageGenerationRequest(
                neuron_type=neuron_type,
                soma_side="combined",  # Default soma side
                run_roi_analysis=True,
                run_layer_analysis=True,
                **kwargs,  # Pass any additional parameters
            )

            response = self._page_generator.generate_page_unified(request)

            if response.success:
                return {
                    "success": True,
                    "neuron_type": neuron_type,
                    "output_file": response.output_path,
                    "generation_time": response.generation_time,
                    "metadata": response.metadata,
                    "warnings": response.warnings,
                }
            else:
                return {
                    "success": False,
                    "neuron_type": neuron_type,
                    "error": response.error_message,
                    "metadata": response.metadata,
                }

        except Exception as e:
            logger.error(f"Failed to generate page for {neuron_type}: {e}")
            return {
                "success": False,
                "neuron_type": neuron_type,
                "error": str(e),
                "metadata": {},
            }



    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the current configuration.

        Returns:
            Dictionary containing validation results
        """
        if not self._config:
            return {
                "valid": False,
                "errors": ["No configuration provided"],
                "warnings": [],
            }

        errors = []
        warnings = []

        try:
            # Check required configuration sections
            if not hasattr(self._config, "output"):
                errors.append("Missing 'output' configuration section")
            else:
                if not hasattr(self._config.output, "directory"):
                    errors.append("Missing 'output.directory' configuration")

            # Check output directory
            if self._output_dir:
                output_path = Path(self._output_dir)
                try:
                    output_path.mkdir(parents=True, exist_ok=True)
                    if not output_path.is_dir():
                        errors.append(
                            f"Output directory is not accessible: {self._output_dir}"
                        )
                except Exception as e:
                    errors.append(f"Cannot create output directory: {e}")

            # Additional validation checks
            if hasattr(self._config, "neuprint") and self._config.neuprint:
                if not hasattr(self._config.neuprint, "server"):
                    warnings.append("NeuPrint server not configured")

        except Exception as e:
            errors.append(f"Configuration validation error: {e}")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


    def cleanup(self) -> None:
        """Clean up resources and reset the facade."""
        logger.info("Cleaning up neuView facade")

        if self._container:
            self._container.clear_cache()

        self._page_generator = None
        self._container = None
        self._is_initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure the facade is initialized before use."""
        if not self._is_initialized:
            self.initialize()

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
