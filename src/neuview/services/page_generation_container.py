"""
Page Generation Dependency Injection Container - Phase 2 Refactoring

This container provides a comprehensive dependency injection system for the
PageGenerator and all its services, implementing the Dependency Injection pattern
to improve testability, maintainability, and loose coupling.
"""

import logging
from typing import Dict, Any, Type, Callable, List
from pathlib import Path

from ..config import Config
from ..utils import get_templates_dir

logger = logging.getLogger(__name__)


class PageGenerationContainer:
    """
    Dependency injection container for page generation services.

    This container manages the lifecycle and dependencies of all services
    required for page generation, providing a centralized dependency
    resolution system.
    """

    def __init__(self, config: Config):
        """
        Initialize the dependency injection container.

        Args:
            config: Configuration object with application settings
        """
        self.config = config
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._initializing: set = set()  # Prevent circular dependencies

        # Register core dependencies
        self.register_singleton("config", config)

        # Register service factories
        self._register_core_factories()
        self._register_service_factories()
        self._register_utility_factories()
        self._register_analysis_factories()

    def register_singleton(self, name: str, instance: Any) -> None:
        """
        Register a singleton instance.

        Args:
            name: Service name
            instance: Pre-created instance
        """
        self._singletons[name] = instance
        logger.debug(f"Registered singleton: {name}")

    def register_factory(self, name: str, factory: Callable) -> None:
        """
        Register a factory function for creating services.

        Args:
            name: Service name
            factory: Factory function that returns service instance
        """
        self._factories[name] = factory
        logger.debug(f"Registered factory: {name}")

    def register_transient(
        self, name: str, service_class: Type, dependencies: List[str] = None
    ) -> None:
        """
        Register a transient service (new instance each time).

        Args:
            name: Service name
            service_class: Class to instantiate
            dependencies: List of dependency names to inject
        """
        dependencies = dependencies or []

        def factory():
            args = [self.get(dep) for dep in dependencies]
            return service_class(*args)

        self.register_factory(name, factory)


    def get(self, name: str) -> Any:
        """
        Resolve and return a service instance.

        Args:
            name: Service name to resolve

        Returns:
            Service instance

        Raises:
            ValueError: If service is not registered or circular dependency detected
        """
        # Check for circular dependency
        if name in self._initializing:
            raise ValueError(f"Circular dependency detected for service: {name}")

        # Return cached singleton if available
        if name in self._singletons:
            return self._singletons[name]

        # Return cached service if available
        if name in self._services:
            return self._services[name]

        # Create new instance using factory
        if name in self._factories:
            self._initializing.add(name)
            try:
                instance = self._factories[name]()
                self._services[name] = instance
                logger.debug(f"Created service: {name}")
                return instance
            finally:
                self._initializing.discard(name)

        raise ValueError(f"Service not registered: {name}")

    def has(self, name: str) -> bool:
        """
        Check if a service is registered.

        Args:
            name: Service name

        Returns:
            True if service is registered
        """
        return (
            name in self._singletons
            or name in self._services
            or name in self._factories
        )

    def clear_cache(self) -> None:
        """Clear all cached service instances (except singletons)."""
        self._services.clear()
        logger.debug("Cleared service cache")

    def _register_core_factories(self) -> None:
        """Register core infrastructure service factories."""

        def output_dir_factory():
            return Path(self.config.output.directory)

        def template_dir_factory():
            # Return built-in template directory
            return get_templates_dir()

        def resource_manager_factory():
            from .resource_manager_service import ResourceManagerService

            # Pass template_env if available, resource manager will handle lazy creation
            template_env = (
                self.get("template_env") if self.has("template_env") else None
            )
            return ResourceManagerService(
                self.get("config"), self.get("output_dir"), template_env
            )

        def hexagon_generator_factory():
            from ..visualization import EyemapGenerator
            from ..visualization.config_manager import ConfigurationManager

            resource_manager = self.get("resource_manager")
            directories = resource_manager.setup_output_directories()
            eyemap_config = ConfigurationManager.create_for_generation(
                output_dir=self.get("output_dir"),
                eyemaps_dir=directories["eyemaps"],
                save_to_files=True,
            )
            return EyemapGenerator(config=eyemap_config)

        self.register_factory("output_dir", output_dir_factory)
        self.register_factory("template_dir", template_dir_factory)
        self.register_factory("resource_manager", resource_manager_factory)
        self.register_factory("hexagon_generator", hexagon_generator_factory)

    def _register_service_factories(self) -> None:
        """Register Phase 1 extracted service factories."""

        def brain_region_service_factory():
            from .brain_region_service import BrainRegionService

            return BrainRegionService()

        def citation_service_factory():
            from .citation_service import CitationService

            return CitationService()

        def connectivity_combination_service_factory():
            from .connectivity_combination_service import ConnectivityCombinationService

            return ConnectivityCombinationService()

        def roi_combination_service_factory():
            from .roi_combination_service import ROICombinationService

            return ROICombinationService()

        def partner_analysis_service_factory():
            from .partner_analysis_service import PartnerAnalysisService

            connectivity_combination_service = self.get(
                "connectivity_combination_service"
            )
            return PartnerAnalysisService(connectivity_combination_service)

        def jinja_template_service_factory():
            from .jinja_template_service import JinjaTemplateService

            return JinjaTemplateService(self.get("template_dir"), self.get("config"))

        def neuron_search_service_factory():
            from .neuron_search_service import NeuronSearchService

            return NeuronSearchService(
                self.get("output_dir"),
                self.get("template_env"),
                self.get("queue_service") if self.has("queue_service") else None,
            )

        def roi_data_service_factory():
            from .roi_data_service import ROIDataService

            return ROIDataService(output_dir=self.get("output_dir"))

        self.register_factory("brain_region_service", brain_region_service_factory)
        self.register_factory("citation_service", citation_service_factory)
        self.register_factory(
            "connectivity_combination_service", connectivity_combination_service_factory
        )
        self.register_factory(
            "roi_combination_service", roi_combination_service_factory
        )
        self.register_factory(
            "partner_analysis_service", partner_analysis_service_factory
        )
        self.register_factory("jinja_template_service", jinja_template_service_factory)
        self.register_factory("neuron_search_service", neuron_search_service_factory)
        self.register_factory("roi_data_service", roi_data_service_factory)

    def _register_utility_factories(self) -> None:
        """Register utility class factories."""

        def html_utils_factory():
            from ..utils import HTMLUtils

            return HTMLUtils()

        def text_utils_factory():
            from ..utils import TextUtils

            return TextUtils()

        def number_formatter_factory():
            from ..utils import NumberFormatter

            return NumberFormatter()

        def percentage_formatter_factory():
            from ..utils import PercentageFormatter

            return PercentageFormatter()

        def synapse_formatter_factory():
            from ..utils import SynapseFormatter

            return SynapseFormatter()

        def neurotransmitter_formatter_factory():
            from ..utils import NeurotransmitterFormatter

            return NeurotransmitterFormatter()

        def mathematical_formatter_factory():
            from ..utils import MathematicalFormatter

            return MathematicalFormatter()

        self.register_factory("html_utils", html_utils_factory)
        self.register_factory("text_utils", text_utils_factory)
        self.register_factory("number_formatter", number_formatter_factory)
        self.register_factory("percentage_formatter", percentage_formatter_factory)
        self.register_factory("synapse_formatter", synapse_formatter_factory)
        self.register_factory(
            "neurotransmitter_formatter", neurotransmitter_formatter_factory
        )
        self.register_factory("mathematical_formatter", mathematical_formatter_factory)

    def _register_analysis_factories(self) -> None:
        """Register analysis service factories."""

        def layer_analysis_service_factory():
            from .layer_analysis_service import LayerAnalysisService

            return LayerAnalysisService(self.get("config"))

        def neuron_selection_service_factory():
            from .neuron_selection_service import NeuronSelectionService

            return NeuronSelectionService(self.get("config"))

        def file_service_factory():
            from .file_service import FileService

            return FileService()

        def threshold_service_factory():
            from .threshold_service import ThresholdService

            return ThresholdService()

        def youtube_service_factory():
            from .youtube_service import YouTubeService

            return YouTubeService()

        self.register_factory("layer_analysis_service", layer_analysis_service_factory)
        self.register_factory(
            "neuron_selection_service", neuron_selection_service_factory
        )
        self.register_factory("file_service", file_service_factory)
        self.register_factory("threshold_service", threshold_service_factory)
        self.register_factory("youtube_service", youtube_service_factory)

    def configure_template_environment(self) -> None:
        """Configure the Jinja2 template environment with all utilities."""

        # Get utility services
        utility_services = {
            "number_formatter": self.get("number_formatter"),
            "percentage_formatter": self.get("percentage_formatter"),
            "synapse_formatter": self.get("synapse_formatter"),
            "neurotransmitter_formatter": self.get("neurotransmitter_formatter"),
            "mathematical_formatter": self.get("mathematical_formatter"),
            "html_utils": self.get("html_utils"),
            "text_utils": self.get("text_utils"),
            "roi_abbr_filter": self.get("brain_region_service").roi_abbr_filter,
            "get_partner_body_ids": self.get(
                "partner_analysis_service"
            ).get_partner_body_ids,
            "queue_service": self.get("queue_service")
            if self.has("queue_service")
            else None,
        }

        # Configure Jinja template service
        jinja_service = self.get("jinja_template_service")
        env = jinja_service.setup_jinja_env(utility_services)

        # Add ROI data as global variables available to all templates
        roi_data_service = self.get("roi_data_service")
        roi_data = roi_data_service.get_all_roi_data()
        env.globals.update(roi_data)

        self.register_singleton("template_env", env)

        # Update resource manager with the configured template environment
        if self.has("resource_manager"):
            resource_manager = self.get("resource_manager")
            resource_manager.update_template_environment(env)

        logger.debug("Template environment configured")

    def configure_data_services(self) -> None:
        """Configure data loading services."""
        # Load brain regions and citations
        brain_regions = self.get("brain_region_service").load_brain_regions()
        citations = self.get("citation_service").load_citations()

        self.register_singleton("brain_regions", brain_regions)
        self.register_singleton("citations", citations)

        logger.debug("Data services configured")

    def configure_page_generator_services(self, page_generator) -> None:
        """
        Configure services that require PageGenerator instance.

        Args:
            page_generator: The PageGenerator instance
        """
        # Register page generator
        self.register_singleton("page_generator", page_generator)

        # Register services that depend on PageGenerator
        def template_context_service_factory():
            from .template_context_service import TemplateContextService

            return TemplateContextService(page_generator)

        def data_processing_service_factory():
            from .data_processing_service import DataProcessingService

            return DataProcessingService(page_generator)

        def cache_service_factory():
            from .cache_service import CacheService

            cache_manager = (
                self.get("cache_manager") if self.has("cache_manager") else None
            )
            threshold_service = self.get("threshold_service")
            config = self.get("config") if self.has("config") else None
            return CacheService(
                cache_manager, page_generator, threshold_service, config
            )

        def roi_analysis_service_factory():
            from .roi_analysis_service import ROIAnalysisService

            return ROIAnalysisService(page_generator)

        def column_analysis_service_factory():
            from .column_analysis_service import ColumnAnalysisService

            return ColumnAnalysisService(page_generator)

        def database_query_service_factory():
            from .database_query_service import DatabaseQueryService

            cache_manager = (
                self.get("cache_manager") if self.has("cache_manager") else None
            )
            return DatabaseQueryService(
                self.get("config"), cache_manager, self.get("data_processing_service")
            )

        def url_generation_service_factory():
            from .url_generation_service import URLGenerationService

            return URLGenerationService(
                self.get("config"),
                self.get("template_env"),
                self.get("neuron_selection_service"),
                self.get("database_query_service"),
            )

        def orchestrator_factory():
            from .page_generation_orchestrator import PageGenerationOrchestrator

            return PageGenerationOrchestrator(page_generator)

        self.register_factory(
            "template_context_service", template_context_service_factory
        )
        self.register_factory(
            "data_processing_service", data_processing_service_factory
        )
        self.register_factory("cache_service", cache_service_factory)
        self.register_factory("roi_analysis_service", roi_analysis_service_factory)
        self.register_factory(
            "column_analysis_service", column_analysis_service_factory
        )
        self.register_factory("database_query_service", database_query_service_factory)
        self.register_factory("url_generation_service", url_generation_service_factory)
        self.register_factory("orchestrator", orchestrator_factory)

        logger.debug("PageGenerator-dependent services configured")


    def create_service_summary(self) -> Dict[str, str]:
        """
        Create a summary of all registered services.

        Returns:
            Dictionary mapping service names to their types
        """
        summary = {}

        for name in self._singletons:
            summary[name] = f"Singleton: {type(self._singletons[name]).__name__}"

        for name in self._services:
            summary[name] = f"Cached: {type(self._services[name]).__name__}"

        for name in self._factories:
            if name not in self._services and name not in self._singletons:
                summary[name] = f"Factory: {name}"

        return summary
