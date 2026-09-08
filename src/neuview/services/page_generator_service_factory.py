"""
PageGenerator Service Factory - Phase 1 Refactoring

This factory encapsulates the complex service initialization logic that was
previously in PageGenerator.__init__, following the Factory pattern to
improve maintainability and testability.
"""

import logging
from pathlib import Path
from typing import Dict, Any

from ..config import Config
from ..visualization import EyemapGenerator
from ..utils import (
    NumberFormatter,
    PercentageFormatter,
    SynapseFormatter,
    NeurotransmitterFormatter,
    MathematicalFormatter,
    get_templates_dir,
    HTMLUtils,
    TextUtils,
)
from .brain_region_service import BrainRegionService
from .citation_service import CitationService
from .neuron_search_service import NeuronSearchService
from .partner_analysis_service import PartnerAnalysisService
from .connectivity_combination_service import ConnectivityCombinationService
from .roi_combination_service import ROICombinationService
from .jinja_template_service import JinjaTemplateService

logger = logging.getLogger(__name__)


class PageGeneratorServiceFactory:
    """Factory for creating and configuring PageGenerator service dependencies."""

    def __init__(
        self, config: Config, output_dir: str, queue_service=None, cache_manager=None
    ):
        """
        Initialize the service factory.

        Args:
            config: Configuration object with template and output settings
            output_dir: Directory path for generated HTML files
            queue_service: Optional QueueService for checking queued neuron types
            cache_manager: Optional cache manager for accessing cached neuron data
        """
        self.config = config
        self.output_dir = Path(output_dir)
        # Templates are now loaded from the built-in templates directory
        self.queue_service = queue_service
        self.cache_manager = cache_manager

        # Create empty services container
        self.services = {}

    def create_all_services(self) -> Dict[str, Any]:
        """
        Create and configure all services required by PageGenerator.

        Returns:
            Dictionary containing all configured services
        """
        logger.info("Creating PageGenerator services...")

        # Phase 1: Core infrastructure services
        self._create_resource_services()

        # Phase 1.5: Phase 1 extracted services
        self._create_phase1_extracted_services()

        # Phase 2: Data loading services
        self._create_data_services()

        # Phase 3: Utility classes
        self._create_utility_services()

        # Phase 4: Analysis services
        self._create_analysis_services()

        # Phase 5: Template environment
        self._create_template_environment()

        # Phase 6: Processing services
        self._create_processing_services()

        # Phase 7: Final orchestration services
        self._create_orchestration_services()

        logger.info(f"Created {len(self.services)} services for PageGenerator")
        return self.services

    def _create_resource_services(self):
        """Create resource management and file system services."""
        from .resource_manager_service import ResourceManagerService

        # Initialize resource manager service
        self.services["resource_manager"] = ResourceManagerService(
            self.config, self.output_dir
        )

        # Set up output directories using resource manager
        directories = self.services["resource_manager"].setup_output_directories()
        self.services["types_dir"] = directories["types"]
        self.services["eyemaps_dir"] = directories["eyemaps"]

        # Initialize eyemap generator with eyemaps directory and save_to_files=True for page generation
        from ..visualization.config_manager import ConfigurationManager

        eyemap_config = ConfigurationManager.create_for_generation(
            output_dir=self.output_dir,
            eyemaps_dir=self.services["eyemaps_dir"],
            save_to_files=True,
        )
        self.services["hexagon_generator"] = EyemapGenerator(config=eyemap_config)

    def _create_phase1_extracted_services(self):
        """Create Phase 1 extracted services."""
        # Initialize Phase 1 extracted services
        self.services["brain_region_service"] = BrainRegionService()
        self.services["citation_service"] = CitationService()

        # Create connectivity combination service
        self.services["connectivity_combination_service"] = (
            ConnectivityCombinationService()
        )

        # Create ROI combination service
        self.services["roi_combination_service"] = ROICombinationService()

        # Create partner analysis service with connectivity combination service
        self.services["partner_analysis_service"] = PartnerAnalysisService(
            connectivity_combination_service=self.services[
                "connectivity_combination_service"
            ]
        )

        # Initialize Jinja template service (will be configured later)
        # Use default template directory
        template_dir = get_templates_dir()

        self.services["jinja_template_service"] = JinjaTemplateService(
            template_dir, self.config
        )

    def _create_data_services(self):
        """Create data loading and external resource services."""
        # Load brain regions data using the service
        self.services["brain_regions"] = self.services[
            "brain_region_service"
        ].load_brain_regions()

        # Load citations data using the service
        self.services["citations"] = self.services["citation_service"].load_citations()

    def _create_utility_services(self):
        """Create utility classes and formatters."""
        # Initialize utility classes (must be done before Jinja setup)
        self.services["html_utils"] = HTMLUtils()
        self.services["text_utils"] = TextUtils()
        self.services["number_formatter"] = NumberFormatter()
        self.services["percentage_formatter"] = PercentageFormatter()
        self.services["synapse_formatter"] = SynapseFormatter()
        self.services["neurotransmitter_formatter"] = NeurotransmitterFormatter()
        self.services["mathematical_formatter"] = MathematicalFormatter()

    def _create_analysis_services(self):
        """Create analysis and computation services."""
        from .layer_analysis_service import LayerAnalysisService
        from .neuron_selection_service import NeuronSelectionService
        from .file_service import FileService
        from .threshold_service import ThresholdService
        from .youtube_service import YouTubeService

        # Initialize service dependencies
        self.services["layer_analysis_service"] = LayerAnalysisService(self.config)
        self.services["neuron_selection_service"] = NeuronSelectionService(self.config)
        self.services["file_service"] = FileService()
        self.services["threshold_service"] = ThresholdService()
        self.services["youtube_service"] = YouTubeService()

    def _create_template_environment(self):
        """Create and configure Jinja2 template environment."""
        # Prepare utility services for Jinja template service
        utility_services = {
            "number_formatter": self.services["number_formatter"],
            "percentage_formatter": self.services["percentage_formatter"],
            "synapse_formatter": self.services["synapse_formatter"],
            "neurotransmitter_formatter": self.services["neurotransmitter_formatter"],
            "mathematical_formatter": self.services["mathematical_formatter"],
            "html_utils": self.services["html_utils"],
            "text_utils": self.services["text_utils"],
            "roi_abbr_filter": self.services["brain_region_service"].roi_abbr_filter,
            "get_partner_body_ids": self.services[
                "partner_analysis_service"
            ].get_partner_body_ids,
            "queue_service": self.queue_service
            if hasattr(self, "queue_service") and self.queue_service
            else None,
        }

        # Configure Jinja template service
        env = self.services["jinja_template_service"].setup_jinja_env(utility_services)

        # Add ROI data as global variables available to all templates
        from .roi_data_service import ROIDataService

        roi_data_service = ROIDataService(
            output_dir=Path(self.output_dir),
            template_path=get_templates_dir() / self.config.neuroglancer.template,
        )
        roi_data = roi_data_service.get_all_roi_data()
        env.globals.update(roi_data)
        logger.debug(f"Added ROI data to template environment: {list(roi_data.keys())}")

        self.services["template_env"] = env

        # Update resource manager with Jinja environment
        from .neuroglancer_js_service import NeuroglancerJSService

        self.services[
            "resource_manager"
        ].neuroglancer_js_service = NeuroglancerJSService(self.config, env)
        logger.debug(
            f"Assigned neuroglancer_js_service to resource_manager: {self.services['resource_manager'].neuroglancer_js_service is not None}"
        )

        # Create neuron search service after template environment is ready
        self.services["neuron_search_service"] = NeuronSearchService(
            self.output_dir, env, self.queue_service
        )

    def _create_processing_services(self):
        """Create data processing and database services."""
        from .template_context_service import TemplateContextService
        from .data_processing_service import DataProcessingService
        from .database_query_service import DatabaseQueryService
        from .cache_service import CacheService
        from .roi_analysis_service import ROIAnalysisService

        # Note: These services need the PageGenerator instance, so we'll create placeholders
        # that will be properly initialized after PageGenerator creation
        self.services["template_context_service_config"] = {
            "class": TemplateContextService,
            "args": [],  # Will be set to [page_generator] after creation
        }

        self.services["data_processing_service_config"] = {
            "class": DataProcessingService,
            "args": [],  # Will be set to [page_generator] after creation
        }

        self.services["database_query_service"] = DatabaseQueryService(
            self.config,
            self.cache_manager,
            None,  # data_processing_service will be set later
        )

        self.services["cache_service_config"] = {
            "class": CacheService,
            "args": [self.cache_manager],  # Will add page_generator after creation
        }

        self.services["roi_analysis_service_config"] = {
            "class": ROIAnalysisService,
            "args": [],  # Will be set to [page_generator] after creation
        }

    def _create_orchestration_services(self):
        """Create orchestration and coordination services."""
        from .column_analysis_service import ColumnAnalysisService
        from .url_generation_service import URLGenerationService
        from .page_generation_orchestrator import PageGenerationOrchestrator

        # These also need PageGenerator instance, so create configs
        self.services["column_analysis_service_config"] = {
            "class": ColumnAnalysisService,
            "args": [],  # Will be set to [page_generator, config] after creation
        }

        self.services["url_generation_service_config"] = {
            "class": URLGenerationService,
            "args": [
                self.config,
                None,  # env - will be set after creation
                None,  # page_generator - will be set after creation
                None,  # neuron_selection_service - will be set after creation
                None,  # database_query_service - will be set after creation
            ],
        }

        self.services["orchestrator_config"] = {
            "class": PageGenerationOrchestrator,
            "args": [],  # Will be set to [page_generator] after creation
        }

        # Initialize caches for expensive operations
        self.services["all_columns_cache"] = None
        self.services["column_analysis_cache"] = {}

    def finalize_services_with_page_generator(self, page_generator):
        """
        Complete service initialization that requires PageGenerator instance.

        Args:
            page_generator: The PageGenerator instance to inject into services
        """
        logger.info("Finalizing services with PageGenerator instance...")

        # Create services that depend on PageGenerator
        template_context_config = self.services["template_context_service_config"]
        self.services["template_context_service"] = template_context_config["class"](
            page_generator
        )

        data_processing_config = self.services["data_processing_service_config"]
        self.services["data_processing_service"] = data_processing_config["class"](
            page_generator
        )

        # Update database_query_service with data_processing_service
        self.services["database_query_service"].data_processing_service = self.services[
            "data_processing_service"
        ]

        cache_service_config = self.services["cache_service_config"]
        self.services["cache_service"] = cache_service_config["class"](
            cache_service_config["args"][0], page_generator
        )

        roi_analysis_config = self.services["roi_analysis_service_config"]
        self.services["roi_analysis_service"] = roi_analysis_config["class"](
            page_generator
        )

        column_analysis_config = self.services["column_analysis_service_config"]
        self.services["column_analysis_service"] = column_analysis_config["class"](
            page_generator
        )

        # Create URL generation service with all dependencies
        from .url_generation_service import URLGenerationService

        self.services["url_generation_service"] = URLGenerationService(
            self.config,
            self.services["template_env"],
            self.services["neuron_selection_service"],
            self.services["database_query_service"],
        )

        # Don't create orchestrator yet - it needs services to be assigned first
        # Store the config for later creation

        logger.info("Service finalization complete")

    @classmethod
    def create_page_generator(
        cls,
        config: Config,
        output_dir: str,
        queue_service=None,
        cache_manager=None,
        copy_mode: str = "check_exists",
    ):
        """
        Factory method to create a fully configured PageGenerator.

        Args:
            config: Configuration object with template and output settings
            output_dir: Directory path for generated HTML files
            queue_service: Optional QueueService for checking queued neuron types
            cache_manager: Optional cache manager for accessing cached neuron data
            copy_mode: Static file copy mode ("check_exists" for pop, "force_all" for generate)

        Returns:
            Configured PageGenerator instance
        """
        logger.info(f"Creating PageGenerator for output directory: {output_dir}")

        # Create factory instance
        factory = cls(config, output_dir, queue_service, cache_manager)

        # Create all services
        services = factory.create_all_services()

        # Import PageGenerator here to avoid circular imports
        from ..page_generator import PageGenerator

        # Create PageGenerator with services
        page_generator = PageGenerator(
            config=config,
            output_dir=output_dir,
            queue_service=queue_service,
            cache_manager=cache_manager,
            services=services,
        )

        # Finalize services that need PageGenerator reference
        factory.finalize_services_with_page_generator(page_generator)

        # Assign finalized services to PageGenerator
        page_generator.template_context_service = services["template_context_service"]
        page_generator.data_processing_service = services["data_processing_service"]
        page_generator.cache_service = services["cache_service"]
        page_generator.roi_analysis_service = services["roi_analysis_service"]
        page_generator.column_analysis_service = services["column_analysis_service"]
        page_generator.url_generation_service = services["url_generation_service"]

        # Create orchestrator AFTER all services are assigned to PageGenerator
        from .page_generation_orchestrator import PageGenerationOrchestrator

        page_generator.orchestrator = PageGenerationOrchestrator(page_generator)
        services["orchestrator"] = page_generator.orchestrator

        # Clean up config objects
        config_keys = [k for k in services.keys() if k.endswith("_config")]
        for key in config_keys:
            if key in services:
                del services[key]

        # Add PageGenerator-dependent filters to Jinja environment
        page_generator.env.filters["get_partner_body_ids"] = (
            page_generator.partner_analysis_service.get_partner_body_ids
        )

        # Copy static files to output directory
        services["resource_manager"].copy_static_files(copy_mode)

        logger.info("PageGenerator creation complete")
        return page_generator
