"""
Command objects for neuView operations.

This module contains all command dataclasses that encapsulate
the parameters and options for various neuView operations.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from .models import NeuronTypeName


@dataclass
class GeneratePageCommand:
    """Command to generate an HTML page for a neuron type."""

    neuron_type: NeuronTypeName
    output_directory: Optional[str] = None
    image_format: str = "svg"
    embed_images: bool = False
    minify: bool = True
    requested_at: Optional[datetime] = None

    def __post_init__(self):
        if self.requested_at is None:
            self.requested_at = datetime.now()

        # Ensure neuron_type is a NeuronTypeName instance
        if not isinstance(self.neuron_type, NeuronTypeName):
            self.neuron_type = NeuronTypeName(str(self.neuron_type))


@dataclass
class TestConnectionCommand:
    """Command to test NeuPrint connection."""

    detailed: bool = False
    timeout: int = 30


@dataclass
class FillQueueCommand:
    """Command to create a queue YAML file with generate options."""

    neuron_type: Optional[NeuronTypeName] = None
    output_directory: Optional[str] = None
    image_format: str = "svg"
    embed_images: bool = False
    all_types: bool = False
    max_types: int = 10
    config_file: Optional[str] = None
    requested_at: Optional[datetime] = None

    def __post_init__(self):
        if self.requested_at is None:
            self.requested_at = datetime.now()

        # Ensure neuron_type is a NeuronTypeName instance if provided
        if self.neuron_type is not None and not isinstance(
            self.neuron_type, NeuronTypeName
        ):
            self.neuron_type = NeuronTypeName(str(self.neuron_type))


@dataclass
class PopCommand:
    """Command to pop and process a queue file."""

    output_directory: Optional[str] = None
    minify: bool = True
    requested_at: Optional[datetime] = None

    def __post_init__(self):
        if self.requested_at is None:
            self.requested_at = datetime.now()


@dataclass
class CreateListCommand:
    """Command to create an index page listing all neuron types."""

    output_directory: Optional[str] = None
    index_filename: str = "types.html"
    include_roi_analysis: bool = (
        True  # Always include ROI analysis for comprehensive data
    )
    minify: bool = True
    requested_at: Optional[datetime] = None

    def __post_init__(self):
        if self.requested_at is None:
            self.requested_at = datetime.now()


@dataclass
class CreateScatterCommand:
    """Command to create svg scatterplots of spatial metrics."""

    requested_at: Optional[datetime] = None

    def __post_init__(self):
        if self.requested_at is None:
            self.requested_at = datetime.now()


@dataclass
class DatasetInfo:
    """Information about the dataset."""

    name: str
    version: str = "Unknown"
    server_url: str = "Unknown"
    connection_status: str = "Unknown"
