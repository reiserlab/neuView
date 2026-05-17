"""
Page Generation Models

This module contains data models for the modern unified page generation workflow.
These models provide a clean, typed interface for neuron data-based generation.

Key Features:
- Unified PageGenerationRequest for all generation scenarios
- Comprehensive analysis configuration and results containers
- Type-safe response handling with detailed metadata
- Support for both synchronous and asynchronous workflows

Example Usage:
    # Modern unified workflow
    request = PageGenerationRequest(
        neuron_type="LPLC2",
        soma_side="left",
        neuron_data=connector.get_neuron_data("LPLC2", "left"),
        connector=connector,
        run_roi_analysis=True,
        run_layer_analysis=True,
        run_column_analysis=True
    )

    response = generator.generate_page_unified(request)
    if response.success:
        print(f"Generated: {response.output_path}")
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from pathlib import Path


class PageGenerationMode(Enum):
    """Mode for page generation indicating data source."""

    FROM_RAW_DATA = "raw_data"


@dataclass
class PageGenerationRequest:
    """
    Unified request object for page generation in the modern workflow.

    This class replaces the legacy approach of passing multiple parameters
    to different generation methods. It provides a unified interface for
    page generation from raw neuron data.

    The request validates that all required dependencies are available
    for page generation.

    Attributes:
        neuron_type: Name of the neuron type (required)
        soma_side: Soma side filter ('left', 'right', 'middle', 'combined')
        neuron_data: Raw neuron data dictionary
        connector: NeuPrint connector instance (required)
        image_format: Output format for visualizations ('svg' or 'png')
        embed_images: Whether to embed images in HTML or save as separate files
        minify: Whether to enable HTML minification
        run_roi_analysis: Enable ROI-based analysis
        run_layer_analysis: Enable layer-specific analysis
        run_column_analysis: Enable column-based analysis

    """

    # Core identification
    neuron_type: str
    soma_side: str

    # Data source
    neuron_data: Optional[Dict[str, Any]] = None

    # Dependencies
    connector: Any = None  # NeuPrint connector

    # Output options
    image_format: str = "svg"
    embed_images: bool = False
    minify: bool = True

    # Analysis options
    run_roi_analysis: bool = True
    run_layer_analysis: bool = True
    run_column_analysis: bool = True

    @property
    def mode(self) -> PageGenerationMode:
        """Determine the generation mode based on provided data."""
        return PageGenerationMode.FROM_RAW_DATA

    def get_neuron_data(self) -> Dict[str, Any]:
        """Get neuron data."""
        return self.neuron_data or {}

    def get_neuron_name(self) -> str:
        """Get neuron type name."""
        return self.neuron_type

    def get_soma_side(self) -> str:
        """Get soma side."""
        return self.soma_side

    def validate(self) -> bool:
        """Validate that the request has required data."""
        if not self.neuron_type:
            return False

        return self.neuron_data is not None and self.connector is not None


@dataclass
class AnalysisResults:
    """Container for all analysis results."""

    roi_summary: Optional[Dict[str, Any]] = None
    layer_analysis: Optional[Dict[str, Any]] = None
    column_analysis: Optional[Dict[str, Any]] = None


    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template context."""
        # Always provide expected keys to prevent template errors
        result = {
            "roi_summary": self.roi_summary,
            "layer_analysis": self.layer_analysis,
            "column_analysis": self.column_analysis,
        }

        return result


@dataclass
class URLCollection:
    """Container for all generated URLs."""

    neuroglancer_url: Optional[str] = None
    neuprint_url: Optional[str] = None
    soma_side_links: Optional[Dict[str, str]] = None
    youtube_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template context."""
        return {
            "neuroglancer_url": self.neuroglancer_url,
            "neuprint_url": self.neuprint_url,
            "soma_side_links": self.soma_side_links or {},
            "youtube_url": self.youtube_url,
        }


@dataclass
class PageGenerationContext:
    """Complete context for page generation."""

    request: PageGenerationRequest
    analysis_results: AnalysisResults
    urls: URLCollection
    neuroglancer_vars: Optional[Dict[str, Any]] = None
    type_region: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)



@dataclass
class PageGenerationResponse:
    """
    Response object containing the result of page generation.

    This class provides a standardized response format for all page generation
    operations, replacing the previous approach of returning plain file paths
    or raising exceptions.

    The response includes both success/failure status and detailed metadata
    about the generation process, enabling better error handling and
    performance monitoring.

    Attributes:
        output_path: Path to the generated HTML file (empty on failure)
        success: Whether the generation completed successfully
        error_message: Detailed error description (None on success)
        warnings: List of non-fatal warnings encountered during generation
        template_name: Name of the template used for rendering
        generation_time_ms: Time taken for generation in milliseconds
        file_size_bytes: Size of the generated file in bytes
    """

    output_path: str
    success: bool = True
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    # Metadata about the generation
    template_name: str = "neuron_page.html.jinja"
    generation_time_ms: Optional[float] = None
    file_size_bytes: Optional[int] = None

    @classmethod
    def success_response(cls, output_path: str, **kwargs) -> "PageGenerationResponse":
        """Create a successful response."""
        return cls(output_path=output_path, success=True, **kwargs)

    @classmethod
    def error_response(cls, error_message: str, **kwargs) -> "PageGenerationResponse":
        """Create an error response."""
        return cls(output_path="", success=False, error_message=error_message, **kwargs)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def get_output_path(self) -> Optional[Path]:
        """Get output path as Path object if successful."""
        if self.success and self.output_path:
            return Path(self.output_path)
        return None


@dataclass
class AnalysisConfiguration:
    """
    Configuration for controlling which analyses are performed during generation.

    This class allows fine-grained control over the analysis pipeline,
    enabling optimization for different use cases (e.g., fast previews vs
    comprehensive analysis).

    The configuration is automatically derived from PageGenerationRequest
    but can be customized for specific analysis requirements.

    Attributes:
        run_roi_analysis: Whether to perform ROI-based connectivity analysis
        run_layer_analysis: Whether to analyze layer-specific innervation
        run_column_analysis: Whether to generate column-based visualizations
        column_analysis_options: Additional options for column analysis
        layer_analysis_options: Additional options for layer analysis
        roi_analysis_options: Additional options for ROI analysis
    """

    run_roi_analysis: bool = True
    run_layer_analysis: bool = True
    run_column_analysis: bool = True

    # Analysis-specific options
    column_analysis_options: Dict[str, Any] = field(default_factory=dict)
    layer_analysis_options: Dict[str, Any] = field(default_factory=dict)
    roi_analysis_options: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_request(cls, request: PageGenerationRequest) -> "AnalysisConfiguration":
        """Create analysis configuration from page generation request."""
        return cls(
            run_roi_analysis=getattr(request, "run_roi_analysis", True),
            run_layer_analysis=getattr(request, "run_layer_analysis", True),
            run_column_analysis=getattr(request, "run_column_analysis", True),
            column_analysis_options={
                "file_type": request.image_format,
                "save_to_files": not request.embed_images,
            },
        )

    def should_run_any_analysis(self) -> bool:
        """Check if any analysis should be run."""
        return any(
            [self.run_roi_analysis, self.run_layer_analysis, self.run_column_analysis]
        )
