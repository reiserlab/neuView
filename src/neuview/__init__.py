"""
neuView - Simplified architecture for generating HTML pages from neuron data.

This package provides a clean, simplified architecture that maintains all
functionality while reducing complexity and improving maintainability.
"""

__version__ = "0.1.0"

# Page generation models
from .models import (
    PageGenerationRequest,
    PageGenerationResponse,
    AnalysisResults,
    URLCollection,
    PageGenerationMode,
)

# Application services from core services module
from .commands import (
    # Commands
    GeneratePageCommand,
    TestConnectionCommand,
    FillQueueCommand,
    PopCommand,
    CreateListCommand,
    CreateScatterCommand,
    DatasetInfo,
)

from .services import (
    # New refactored services
    PageGenerationService,
    ConnectionTestService,
)

# Commands and services from services package
from .services.neuron_discovery_service import (
    InspectNeuronTypeCommand,
    NeuronDiscoveryService,
)

# Specialized services from services package
from .services import IndexService

# Result pattern for error handling
from .result import Result, Ok, Err

# CLI interface
from .cli import main

__all__ = [
    # Page generation models
    "PageGenerationRequest",
    "PageGenerationResponse",
    "AnalysisResults",
    "URLCollection",
    "PageGenerationMode",
    # Commands
    "GeneratePageCommand",
    "InspectNeuronTypeCommand",
    "TestConnectionCommand",
    "FillQueueCommand",
    "PopCommand",
    "CreateListCommand",
    "CreateScatterCommand",
    # Services
    "PageGenerationService",
    "NeuronDiscoveryService",
    "ConnectionTestService",
    "IndexService",
    # Data transfer objects
    "DatasetInfo",
    # Result pattern
    "Result",
    "Ok",
    "Err",
    # CLI
    "main",
]
