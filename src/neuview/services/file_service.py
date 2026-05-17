"""
File service for handling file naming and path generation.

This module provides utilities for generating consistent filenames and managing
file paths for the page generation system.
"""

from pathlib import Path


class FileService:
    """
    Handle file naming and path generation for the page generation system.

    This service provides utilities for generating consistent filenames for
    neuron pages and managing file paths throughout the application.
    """

    @staticmethod
    def generate_filename(neuron_type: str, soma_side: str) -> str:
        """
        Generate HTML filename for a neuron type and soma side.

        This is a static utility method that doesn't require FileService instantiation.

        Args:
            neuron_type: The neuron type name
            soma_side: The soma side ('left', 'right', 'middle', 'all', 'combined')

        Returns:
            HTML filename string

        Example:
            >>> FileService.generate_filename("KC/a", "left")
            'KC_a_L.html'
            >>> FileService.generate_filename("Mi1", "all")
            'Mi1.html'
        """
        # Clean neuron type name for filename
        clean_type = neuron_type.replace("/", "_").replace(" ", "_")

        # Handle different soma side formats with new naming scheme
        if soma_side in ["all", "combined", "center"]:
            # General page for neuron type (multiple sides available)
            # FAFB "center" maps to combined page (no suffix)
            return f"{clean_type}.html"
        else:
            # Specific page for single side
            soma_side_suffix = soma_side
            if soma_side_suffix == "left":
                soma_side_suffix = "L"
            elif soma_side_suffix == "right":
                soma_side_suffix = "R"
            elif soma_side_suffix == "middle":
                soma_side_suffix = "M"
            elif soma_side_suffix == "center":
                # FAFB center should go to combined page, not _C.html
                return f"{clean_type}.html"
            return f"{clean_type}_{soma_side_suffix}.html"

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename by replacing problematic characters.

        Args:
            filename: The filename to sanitize

        Returns:
            Sanitized filename string
        """
        # Replace common problematic characters
        sanitized = filename.replace("/", "_").replace("\\", "_")
        sanitized = sanitized.replace(" ", "_").replace(":", "_")
        sanitized = sanitized.replace("?", "_").replace("*", "_")
        sanitized = sanitized.replace("<", "_").replace(">", "_")
        sanitized = sanitized.replace("|", "_").replace('"', "_")

        # Remove multiple consecutive underscores
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")

        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")

        return sanitized




