"""
File output manager for handling eyemap file operations.

This module provides a service class that handles all file-related operations
for eyemap generation, including saving files, managing directories, and
determining output paths.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional, Union

from .rendering import OutputFormat

logger = logging.getLogger(__name__)


class FileOutputManager:
    """
    Service class for managing file output operations in eyemap generation.

    This class encapsulates all file-related operations including directory
    creation, file path generation, and coordinating with renderers for
    file saving operations.
    """

    def __init__(
        self, output_dir: Optional[Path] = None, eyemaps_dir: Optional[Path] = None
    ):
        """
        Initialize the file output manager.

        Args:
            output_dir: Base directory for output files
            eyemaps_dir: Specific directory for eyemap files
        """
        self.output_dir = output_dir
        self.eyemaps_dir = eyemaps_dir
        self._ensure_directories_exist()

    def _ensure_directories_exist(self):
        """Ensure that required directories exist."""
        if self.output_dir and not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created output directory: {self.output_dir}")

        if self.eyemaps_dir and not self.eyemaps_dir.exists():
            self.eyemaps_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created eyemaps directory: {self.eyemaps_dir}")

    def handle_grid_output(
        self,
        request,
        region: str,
        side: str,
        synapse_content: str,
        cell_content: str,
        rendering_manager,
    ) -> Dict:
        """
        Handle saving or returning grid content based on request configuration.

        Args:
            request: GridGenerationRequest containing output configuration
            region: Region name
            side: Side identifier
            synapse_content: Generated synapse grid content
            cell_content: Generated cell grid content
            rendering_manager: RenderingManager instance for file operations

        Returns:
            Dictionary with 'synapse_density' and 'cell_count' keys mapping to
            either file paths (if saving) or content strings (if embedding)
        """
        if self._should_save_to_files(request):
            return self._save_grids_to_files(
                request, region, side, synapse_content, cell_content, rendering_manager
            )
        else:
            return self._return_grid_content(synapse_content, cell_content)

    def _should_generate_eyemap(self, filename: str) -> bool:
        """
        Check if eyemap file should be generated (doesn't exist yet).

        Args:
            filename: The filename to check

        Returns:
            True if file should be generated, False if it already exists
        """
        if not self.eyemaps_dir:
            return True

        file_path = self.eyemaps_dir / filename
        if file_path.exists():
            logger.debug(f"Eyemap already exists, skipping generation: {filename}")
            return False

        return True

    def _should_save_to_files(self, request) -> bool:
        """
        Determine if grids should be saved to files.

        Args:
            request: GridGenerationRequest containing configuration

        Returns:
            True if files should be saved, False otherwise
        """
        return request.save_to_files and self.output_dir is not None

    def _save_grids_to_files(
        self,
        request,
        region: str,
        side: str,
        synapse_content: str,
        cell_content: str,
        rendering_manager,
    ) -> Dict:
        """
        Save grid content to files and return file paths.

        Args:
            request: GridGenerationRequest containing configuration
            region: Region name
            side: Side identifier
            synapse_content: Generated synapse grid content
            cell_content: Generated cell grid content
            rendering_manager: RenderingManager instance for file operations

        Returns:
            Dictionary mapping metric types to file paths
        """
        format_enum = self._get_output_format_enum(request.output_format)

        if request.output_format not in ["svg", "png"]:
            raise ValueError(f"Unsupported output format: {request.output_format}")

        renderer = rendering_manager._get_renderer(format_enum)

        # Generate file names. Contralateral renders go to a distinct
        # filename so combined-page eyemaps and side-page eyemaps (with the
        # mismatched-hemisphere badge) don't collide on disk. The render is
        # contralateral when the page's original soma side differs from the
        # hemisphere being drawn.
        page_soma = getattr(request, "page_soma_side", None)
        is_contralateral = (
            page_soma is not None and page_soma != request.soma_side
        )
        synapse_filename = self._generate_filename(
            region, request.neuron_type, side, "synapse_density", is_contralateral
        )
        cell_filename = self._generate_filename(
            region, request.neuron_type, side, "cell_count", is_contralateral
        )

        # Check if files already exist and return existing paths if so
        synapse_path = None
        cell_path = None

        if self._should_generate_eyemap(synapse_filename):
            synapse_path = renderer.save_to_file(synapse_content, synapse_filename)
        else:
            synapse_path = self.eyemaps_dir / synapse_filename

        if self._should_generate_eyemap(cell_filename):
            cell_path = renderer.save_to_file(cell_content, cell_filename)
        else:
            cell_path = self.eyemaps_dir / cell_filename

        if synapse_path and cell_path:
            logger.debug(
                f"Generated/reused grids for {region}_{side}: {synapse_path}, {cell_path}"
            )

        return {"synapse_density": str(synapse_path), "cell_count": str(cell_path)}

    def _return_grid_content(self, synapse_content: str, cell_content: str) -> Dict:
        """
        Return grid content directly for embedding.

        Args:
            synapse_content: Generated synapse grid content
            cell_content: Generated cell grid content

        Returns:
            Dictionary mapping metric types to content strings
        """
        return {"synapse_density": synapse_content, "cell_count": cell_content}

    def _get_output_format_enum(self, output_format: str) -> OutputFormat:
        """
        Convert string output format to OutputFormat enum.

        Args:
            output_format: String format ('svg' or 'png')

        Returns:
            Corresponding OutputFormat enum value
        """
        if output_format.lower() == "svg":
            return OutputFormat.SVG
        elif output_format.lower() == "png":
            return OutputFormat.PNG
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    def _generate_filename(
        self,
        region: str,
        neuron_type: str,
        side: str,
        metric_type: str,
        is_contralateral: bool = False,
    ) -> str:
        """
        Generate a standardized filename for eyemap files.

        Args:
            region: Region name
            neuron_type: Neuron type identifier
            side: Side identifier
            metric_type: Type of metric ('synapse_density' or 'cell_count')
            is_contralateral: When True, the rendered hemisphere is opposite
                the soma side and the SVG carries a "con" marker. The
                filename gets a "_con" suffix so contralateral and
                ipsilateral renders don't share a path on disk.

        Returns:
            Generated filename (without extension)
        """
        suffix = "_con" if is_contralateral else ""
        return f"{region}_{neuron_type}_{side}_{metric_type}{suffix}"

    def get_output_path(
        self, filename: str, use_eyemaps_dir: bool = True
    ) -> Optional[Path]:
        """
        Get the full output path for a given filename.

        Args:
            filename: Base filename
            use_eyemaps_dir: Whether to use eyemaps directory or base output directory

        Returns:
            Full path where the file should be saved, or None if no output directory is set
        """
        if use_eyemaps_dir and self.eyemaps_dir:
            return self.eyemaps_dir / filename
        elif self.output_dir:
            return self.output_dir / filename
        else:
            return None






class FileOutputManagerFactory:
    """
    Factory class for creating FileOutputManager instances.
    """


    @staticmethod
    def create_from_config(config) -> FileOutputManager:
        """
        Create a FileOutputManager from an EyemapConfiguration.

        Args:
            config: EyemapConfiguration instance

        Returns:
            New FileOutputManager instance
        """
        return FileOutputManager(
            output_dir=config.output_dir, eyemaps_dir=config.eyemaps_dir
        )

