"""
Unified configuration manager for eyemap generation.

This module provides a centralized configuration management system that consolidates
all configuration objects used by the EyemapGenerator and related components.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any

from .constants import (
    DEFAULT_HEX_SIZE,
    DEFAULT_SPACING_FACTOR,
    DEFAULT_MARGIN,
    MIN_HEX_SIZE,
    MAX_HEX_SIZE,
    MIN_SPACING_FACTOR,
    MAX_SPACING_FACTOR,
    OUTPUT_FORMAT_SVG,
    SUPPORTED_OUTPUT_FORMATS,
    EYEMAPS_SUBDIRECTORY,
)
from .rendering.rendering_config import RenderingConfig

logger = logging.getLogger(__name__)


@dataclass
class EyemapConfiguration:
    """
    Unified configuration for eyemap generation.

    This class consolidates all configuration parameters needed for eyemap
    generation, validation, and rendering operations.
    """

    # Core visualization parameters
    hex_size: int = DEFAULT_HEX_SIZE
    spacing_factor: float = DEFAULT_SPACING_FACTOR
    margin: int = DEFAULT_MARGIN

    # Directory configuration
    output_dir: Optional[Path] = None
    eyemaps_dir: Optional[Path] = None

    # Operation modes
    embed_mode: bool = False
    save_to_files: bool = True

    # Output configuration
    output_format: str = OUTPUT_FORMAT_SVG

    # Performance settings
    enable_caching: bool = True
    cache_size: int = 100
    processing_timeout: int = 300
    max_concurrent_renders: int = 4

    # Validation settings
    strict_validation: bool = True

    # Debug and logging
    debug_mode: bool = False
    log_level: str = "INFO"

    # Advanced settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization validation and setup."""
        self._validate_configuration()
        self._setup_directories()
        self._setup_logging()

    def _validate_configuration(self):
        """Validate configuration parameters."""
        if not MIN_HEX_SIZE <= self.hex_size <= MAX_HEX_SIZE:
            raise ValueError(
                f"hex_size must be between {MIN_HEX_SIZE} and {MAX_HEX_SIZE}, "
                f"got {self.hex_size}"
            )

        if not MIN_SPACING_FACTOR <= self.spacing_factor <= MAX_SPACING_FACTOR:
            raise ValueError(
                f"spacing_factor must be between {MIN_SPACING_FACTOR} and "
                f"{MAX_SPACING_FACTOR}, got {self.spacing_factor}"
            )

        if self.output_format not in SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(
                f"output_format must be one of {SUPPORTED_OUTPUT_FORMATS}, "
                f"got {self.output_format}"
            )

        if self.margin < 0:
            raise ValueError(f"margin must be non-negative, got {self.margin}")

        if self.cache_size < 0:
            raise ValueError(f"cache_size must be non-negative, got {self.cache_size}")

        if self.processing_timeout < 0:
            raise ValueError(
                f"processing_timeout must be non-negative, got {self.processing_timeout}"
            )

        if self.max_concurrent_renders < 1:
            raise ValueError(
                f"max_concurrent_renders must be at least 1, got {self.max_concurrent_renders}"
            )

    def _setup_directories(self):
        """Setup and validate directory paths."""
        if self.eyemaps_dir is None and self.output_dir is not None:
            self.eyemaps_dir = self.output_dir / EYEMAPS_SUBDIRECTORY

        # Convert string paths to Path objects
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        if isinstance(self.eyemaps_dir, str):
            self.eyemaps_dir = Path(self.eyemaps_dir)

        # Create directories if they don't exist and we're saving files
        if self.save_to_files:
            if self.output_dir and not self.output_dir.exists():
                self.output_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created output directory: {self.output_dir}")

            if self.eyemaps_dir and not self.eyemaps_dir.exists():
                self.eyemaps_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created eyemaps directory: {self.eyemaps_dir}")

    def _setup_logging(self):
        """Setup logging configuration."""
        if self.debug_mode and self.log_level == "INFO":
            self.log_level = "DEBUG"

        # Set logger level for the visualization module
        viz_logger = logging.getLogger("neuview.visualization")
        viz_logger.setLevel(getattr(logging, self.log_level.upper()))

    def copy(self, **kwargs) -> "EyemapConfiguration":
        """
        Create a copy of the configuration with optional parameter overrides.

        Args:
            **kwargs: Parameters to override in the copy

        Returns:
            New EyemapConfiguration instance with updated parameters
        """
        # Get current values
        current_values = {
            "hex_size": self.hex_size,
            "spacing_factor": self.spacing_factor,
            "margin": self.margin,
            "output_dir": self.output_dir,
            "eyemaps_dir": self.eyemaps_dir,
            "embed_mode": self.embed_mode,
            "save_to_files": self.save_to_files,
            "output_format": self.output_format,
            "enable_caching": self.enable_caching,
            "cache_size": self.cache_size,
            "processing_timeout": self.processing_timeout,
            "max_concurrent_renders": self.max_concurrent_renders,
            "strict_validation": self.strict_validation,
            "debug_mode": self.debug_mode,
            "log_level": self.log_level,
            "custom_settings": self.custom_settings.copy(),
        }

        # Apply overrides
        current_values.update(kwargs)

        return EyemapConfiguration(**current_values)

    def update(self, **kwargs) -> None:
        """
        Update configuration parameters in-place.

        Args:
            **kwargs: Parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown configuration parameter: {key}")

        # Re-validate after updates
        self._validate_configuration()
        self._setup_directories()
        self._setup_logging()

    def to_rendering_config(self) -> RenderingConfig:
        """
        Convert to RenderingConfig for rendering operations.

        Returns:
            RenderingConfig instance with equivalent settings
        """
        return RenderingConfig(
            hex_size=self.hex_size,
            spacing_factor=self.spacing_factor,
            output_dir=self.output_dir,
            eyemaps_dir=self.eyemaps_dir,
            margin=self.margin,
            save_to_files=self.save_to_files,
            embed_mode=self.embed_mode,
        )

    def get_coordinate_system_params(self) -> Dict[str, Any]:
        """
        Get parameters needed for coordinate system initialization.

        Returns:
            Dictionary of coordinate system parameters
        """
        return {
            "hex_size": self.hex_size,
            "spacing_factor": self.spacing_factor,
            "margin": self.margin,
        }




    def __str__(self) -> str:
        """String representation of configuration."""
        return (
            f"EyemapConfiguration("
            f"hex_size={self.hex_size}, "
            f"spacing_factor={self.spacing_factor}, "
            f"output_format={self.output_format}, "
            f"save_to_files={self.save_to_files}, "
            f"embed_mode={self.embed_mode}"
            f")"
        )

    def __repr__(self) -> str:
        """Detailed representation of configuration."""
        return (
            f"EyemapConfiguration(\n"
            f"  hex_size={self.hex_size},\n"
            f"  spacing_factor={self.spacing_factor},\n"
            f"  margin={self.margin},\n"
            f"  output_dir={self.output_dir},\n"
            f"  eyemaps_dir={self.eyemaps_dir},\n"
            f"  embed_mode={self.embed_mode},\n"
            f"  save_to_files={self.save_to_files},\n"
            f"  output_format={self.output_format},\n"
            f"  enable_caching={self.enable_caching},\n"
            f"  debug_mode={self.debug_mode}\n"
            f")"
        )


class ConfigurationManager:
    """
    Manager for creating and maintaining eyemap configurations.

    This class provides factory methods and utilities for creating
    and managing EyemapConfiguration instances.
    """

    _default_config: Optional[EyemapConfiguration] = None

    @classmethod
    def create_default(cls) -> EyemapConfiguration:
        """
        Create a default configuration instance.

        Returns:
            EyemapConfiguration with default settings
        """
        if cls._default_config is None:
            cls._default_config = EyemapConfiguration()

        return cls._default_config.copy()

    @classmethod
    def create_for_generation(
        cls,
        hex_size: int = DEFAULT_HEX_SIZE,
        spacing_factor: float = DEFAULT_SPACING_FACTOR,
        output_dir: Optional[Path] = None,
        eyemaps_dir: Optional[Path] = None,
        save_to_files: bool = True,
        output_format: str = OUTPUT_FORMAT_SVG,
        **kwargs,
    ) -> EyemapConfiguration:
        """
        Create configuration optimized for eyemap generation.

        Args:
            hex_size: Size of individual hexagons
            spacing_factor: Spacing between hexagons
            output_dir: Directory to save SVG files
            eyemaps_dir: Directory to save eyemap images
            save_to_files: Whether to save files to disk
            output_format: Output format (svg or png)
            **kwargs: Additional configuration parameters

        Returns:
            EyemapConfiguration instance optimized for generation
        """
        config_params = {
            "hex_size": hex_size,
            "spacing_factor": spacing_factor,
            "output_dir": output_dir,
            "eyemaps_dir": eyemaps_dir,
            "save_to_files": save_to_files,
            "output_format": output_format,
            "embed_mode": not save_to_files,
            **kwargs,
        }

        return EyemapConfiguration(**config_params)




