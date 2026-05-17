"""
Region configuration system for visualization rendering.

This module provides a centralized configuration system for region-specific
rendering parameters, replacing hardcoded layer logic throughout the codebase.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class Region(Enum):
    """Supported brain regions."""

    ME = "ME"
    LO = "LO"
    LOP = "LOP"


@dataclass(frozen=True)
class RegionConfig:
    """
    Configuration for a specific brain region.

    This class encapsulates all region-specific parameters needed
    for rendering, including layer counts and display mappings.
    """

    # Region identifier
    region: Region
    # Layer configuration
    layer_count: int
    layer_display_mapping: Optional[Dict[int, str]] = None

    # Control dimensions
    control_square_size: int = 8
    control_gap: int = 0

    def get_display_layer_name(self, layer_num: int) -> str:
        """
        Get the display name for a layer number.

        Args:
            layer_num: Layer number

        Returns:
            Display name for the layer
        """
        if self.layer_display_mapping and layer_num in self.layer_display_mapping:
            display_num = self.layer_display_mapping[layer_num]
            return f"{self.region.value}{display_num}"
        return f"{self.region.value}{layer_num}"

    def calculate_control_dimensions(self) -> Dict[str, float]:
        """
        Calculate control dimensions for this region.

        Returns:
            Dictionary with control dimension parameters
        """
        all_button_width = self.control_square_size * 3
        layer_button_width = self.control_square_size * 5
        all_button_height = self.control_square_size * self.layer_count
        total_control_height = all_button_height + (
            self.control_square_size + self.control_gap
        ) * (self.layer_count - 1)

        return {
            "all_button_width": all_button_width,
            "layer_button_width": layer_button_width,
            "all_button_height": all_button_height,
            "total_control_height": total_control_height,
            "layer_count": self.layer_count,
        }


class RegionConfigRegistry:
    """
    Registry for region-specific configurations.

    This class provides centralized access to region configurations
    and serves as the single source of truth for region parameters.
    """

    _configs: Dict[Region, RegionConfig] = {
        Region.ME: RegionConfig(region=Region.ME, layer_count=10),
        Region.LO: RegionConfig(
            region=Region.LO,
            layer_count=7,
            layer_display_mapping={5: "5A", 6: "5B", 7: "6"},
        ),
        Region.LOP: RegionConfig(region=Region.LOP, layer_count=4),
    }

    # Default configuration for unknown regions
    _default_config = RegionConfig(region=Region.ME, layer_count=10)

    @classmethod
    def get_config(cls, region: str) -> RegionConfig:
        """
        Get configuration for a region.

        Args:
            region: Region identifier string

        Returns:
            RegionConfig for the specified region
        """
        try:
            region_enum = Region(region.upper())
            return cls._configs[region_enum]
        except (ValueError, KeyError):
            # Return default config for unknown regions
            return cls._default_config


    @classmethod
    def get_display_layer_name(cls, region: str, layer_num: int) -> str:
        """
        Get display name for a layer in a specific region.

        Args:
            region: Region identifier string
            layer_num: Layer number

        Returns:
            Display name for the layer
        """
        return cls.get_config(region).get_display_layer_name(layer_num)

    @classmethod
    def get_control_dimensions(cls, region: str) -> Dict[str, float]:
        """
        Get control dimensions for a region.

        Args:
            region: Region identifier string

        Returns:
            Dictionary with control dimension parameters
        """
        return cls.get_config(region).calculate_control_dimensions()



