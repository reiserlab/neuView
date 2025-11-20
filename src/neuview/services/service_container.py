"""
Service Container for neuView.

This container manages dependency injection and service creation
for the neuView application, providing a centralized way to
access all services with proper dependency management.
"""

import logging
from pathlib import Path

from ..utils import get_templates_dir, get_static_dir

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Simple service container for dependency management."""

    def __init__(self, config, copy_mode: str = "check_exists"):
        """Initialize service container.

        Args:
            config: Configuration object
            copy_mode: Static file copy mode ("check_exists" for pop, "force_all" for generate)
        """
        self.config = config
        self.copy_mode = copy_mode
        self._services = {}
        self._neuprint_connector = None
        self._page_generator = None
        self._page_service = None
        self._discovery_service = None
        self._connection_service = None
        self._queue_service = None
        self._cache_manager = None
        self._index_service = None
        self._queue_file_manager = None
        self._queue_processor = None
        self._cache_service = None
        self._soma_detection_service = None
        self._neuron_statistics_service = None
        self._scatter_service = None

        # Phase 3 managers
        self._template_manager = None
        self._resource_manager_v3 = None
        self._dependency_manager = None

    def _get_or_create_service(self, service_name: str, factory_func):
        """Generic method to get or create a service."""
        if service_name not in self._services:
            self._services[service_name] = factory_func()
        return self._services[service_name]

    @property
    def neuprint_connector(self):
        """Get or create NeuPrint connector."""

        def create():
            from ..neuprint_connector import NeuPrintConnector

            return NeuPrintConnector(self.config)

        return self._get_or_create_service("neuprint_connector", create)

    @property
    def page_generator(self):
        """Get or create page generator using factory."""

        def create():
            from .page_generator_service_factory import PageGeneratorServiceFactory

            return PageGeneratorServiceFactory.create_page_generator(
                self.config,
                self.config.output.directory,
                self.queue_service,
                self.cache_manager,
                self.copy_mode,
            )

        return self._get_or_create_service("page_generator", create)

    @property
    def cache_manager(self):
        """Get or create cache manager."""

        def create():
            from ..cache import create_cache_manager

            return create_cache_manager(self.config.output.directory)

        return self._get_or_create_service("cache_manager", create)

    @property
    def cache_service(self):
        """Get or create cache service."""

        def create():
            from .cache_service import CacheService

            return CacheService(
                self.cache_manager, self.page_generator, None, self.config
            )

        return self._get_or_create_service("cache_service", create)

    @property
    def soma_detection_service(self):
        """Get or create soma detection service."""

        def create():
            from .soma_detection_service import SomaDetectionService

            return SomaDetectionService(
                self.neuprint_connector,
                self.page_generator,
                self.cache_service,
                neuron_statistics_service=self.neuron_statistics_service,
            )

        return self._get_or_create_service("soma_detection_service", create)

    @property
    def template_manager(self):
        """Get or create Phase 3 template manager."""

        def create():
            from ..managers import TemplateManager

            template_config = {
                "cache": {
                    "enabled": True,
                    "type": "composite",
                    "max_size": 1000,
                    "ttl": 3600,
                },
                "template": {"type": "auto"},
            }
            # Use built-in template directory
            return TemplateManager(get_templates_dir(), template_config)

        return self._get_or_create_service("template_manager", create)

    @property
    def resource_manager_v3(self):
        """Get or create Phase 3 resource manager."""

        def create():
            from ..managers import ResourceManager

            # Get project directories for static resources
            base_paths = [
                get_static_dir(),
                get_templates_dir(),
                Path(self.config.output.directory) / "static",
            ]

            resource_config = {
                "cache": {
                    "enabled": True,
                    "type": "composite",
                    "max_size": 500,
                    "ttl": 7200,
                },
                "resource": {
                    "type": "filesystem",
                    "optimize": True,
                    "minify": True,
                    "compress": False,
                    "follow_symlinks": True,
                },
            }
            return ResourceManager(base_paths, resource_config)

        return self._get_or_create_service("resource_manager_v3", create)

    @property
    def dependency_manager(self):
        """Get or create dependency manager."""

        def create():
            from ..managers import DependencyManager

            return DependencyManager(self.template_manager, self.resource_manager_v3)

        return self._get_or_create_service("dependency_manager", create)

    @property
    def page_service(self):
        """Get or create page generation service."""

        def create():
            from .page_generation_service import PageGenerationService

            return PageGenerationService(
                self.neuprint_connector, self.page_generator, self.config
            )

        return self._get_or_create_service("page_service", create)

    @property
    def neuron_statistics_service(self):
        """Get or create neuron statistics service."""

        def create():
            from .neuron_statistics_service import NeuronStatisticsService

            return NeuronStatisticsService(self.neuprint_connector)

        return self._get_or_create_service("neuron_statistics_service", create)

    @property
    def discovery_service(self):
        """Get or create neuron discovery service."""

        def create():
            from . import NeuronDiscoveryService, ROIAnalysisService, NeuronNameService

            # Create ROI analysis service for enriched discovery
            roi_analysis_service = ROIAnalysisService(
                self.page_generator, self.roi_hierarchy_service
            )

            # Create neuron name service for filename conversion
            neuron_name_service = NeuronNameService(self.cache_manager)

            return NeuronDiscoveryService(
                self.neuprint_connector,
                self.config,
                self.neuron_statistics_service,
                roi_analysis_service=roi_analysis_service,
                neuron_name_service=neuron_name_service,
            )

        return self._get_or_create_service("discovery_service", create)

    @property
    def connection_service(self):
        """Get or create connection test service."""

        def create():
            from .connection_test_service import ConnectionTestService

            return ConnectionTestService(self.neuprint_connector)

        return self._get_or_create_service("connection_service", create)

    @property
    def queue_file_manager(self):
        """Get or create queue file manager."""

        def create():
            from .queue_file_manager import QueueFileManager

            return QueueFileManager(self.config)

        return self._get_or_create_service("queue_file_manager", create)

    @property
    def queue_processor(self):
        """Get or create queue processor."""

        def create():
            from .queue_processor import QueueProcessor

            return QueueProcessor(self.config)

        return self._get_or_create_service("queue_processor", create)

    @property
    def queue_service(self):
        """Get or create queue service."""

        def create():
            from ..core_services import QueueService

            return QueueService(self.config)

        return self._get_or_create_service("queue_service", create)

    @property
    def roi_hierarchy_service(self):
        """Get or create ROI hierarchy service."""

        def create():
            from . import ROIHierarchyService

            return ROIHierarchyService(self.config, self.cache_manager)

        return self._get_or_create_service("roi_hierarchy_service", create)

    @property
    def index_service(self):
        """Get or create index service."""

        def create():
            from . import IndexService

            return IndexService(self.config, self.page_generator)

        return self._get_or_create_service("index_service", create)

    @property
    def scatter_service(self):
        """Get or create scatterplot service."""

        def create():
            from .scatterplot_service import ScatterplotService

            return ScatterplotService()

        return self._get_or_create_service("scatter_service", create)

    def cleanup(self):
        """Clean up services and resources."""
        # Close any connections or clean up resources
        if "neuprint_connector" in self._services:
            # Add any cleanup logic for the connector if needed
            pass

        # Clear all service references
        self._services.clear()
