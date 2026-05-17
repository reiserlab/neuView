"""
Unified threshold configuration system for all threshold-related operations.

This module provides a centralized configuration system for managing thresholds
across different components of the application, eliminating hardcoded values
and ensuring consistent threshold behavior.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ThresholdType(Enum):
    """Types of thresholds supported by the system."""

    ROI_FILTERING = "roi_filtering"
    VISUALIZATION = "visualization"
    PERFORMANCE = "performance"
    MEMORY = "memory"
    QUALITY = "quality"
    STATISTICAL = "statistical"


class ThresholdMethod(Enum):
    """Methods for calculating thresholds."""

    LINEAR = "linear"
    PERCENTILE = "percentile"
    DATA_DRIVEN = "data_driven"


@dataclass
class ThresholdProfile:
    """Configuration profile for a specific threshold type."""

    name: str
    threshold_type: ThresholdType
    default_value: float
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    method: ThresholdMethod = ThresholdMethod.LINEAR
    n_bins: int = 5
    adaptive: bool = False
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate the threshold profile configuration."""
        if self.min_value is not None and self.max_value is not None:
            if self.min_value >= self.max_value:
                return False

        if self.min_value is not None and self.default_value < self.min_value:
            return False

        if self.max_value is not None and self.default_value > self.max_value:
            return False

        if self.n_bins < 2:
            return False

        return True

    def clamp_value(self, value: float) -> float:
        """Clamp a value to the profile's valid range."""
        if self.min_value is not None:
            value = max(value, self.min_value)
        if self.max_value is not None:
            value = min(value, self.max_value)
        return value


@dataclass
class ThresholdSettings:
    """Complete threshold settings for a specific context."""

    profile: ThresholdProfile
    current_value: float
    computed_thresholds: List[float] = field(default_factory=list)
    cache_key: Optional[str] = None
    last_computed: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if the current settings are valid."""
        return (
            self.profile.validate()
            and len(self.computed_thresholds) >= 2
            and all(
                self.computed_thresholds[i] <= self.computed_thresholds[i + 1]
                for i in range(len(self.computed_thresholds) - 1)
            )
        )


class ThresholdConfig:
    """
    Centralized threshold configuration manager.

    Manages all threshold configurations across the application,
    providing a single source of truth for threshold values and
    computation methods.
    """

    def __init__(self):
        """Initialize the threshold configuration manager."""
        self._profiles: Dict[str, ThresholdProfile] = {}
        self._settings: Dict[str, ThresholdSettings] = {}
        self._defaults_loaded = False
        self._load_default_profiles()

    def _load_default_profiles(self) -> None:
        """Load default threshold profiles for common use cases."""
        default_profiles = [
            # ROI Filtering Thresholds
            ThresholdProfile(
                name="roi_filtering_default",
                threshold_type=ThresholdType.ROI_FILTERING,
                default_value=1.5,
                min_value=0.0,
                max_value=100.0,
                description="Default ROI significance filtering threshold (percentage)",
            ),
            ThresholdProfile(
                name="roi_filtering_strict",
                threshold_type=ThresholdType.ROI_FILTERING,
                default_value=5.0,
                min_value=0.0,
                max_value=100.0,
                description="Strict ROI significance filtering threshold",
            ),
            ThresholdProfile(
                name="roi_filtering_lenient",
                threshold_type=ThresholdType.ROI_FILTERING,
                default_value=0.5,
                min_value=0.0,
                max_value=100.0,
                description="Lenient ROI significance filtering threshold",
            ),
            # Visualization Thresholds
            ThresholdProfile(
                name="visualization_synapse_density",
                threshold_type=ThresholdType.VISUALIZATION,
                default_value=0.0,
                method=ThresholdMethod.PERCENTILE,
                n_bins=5,
                adaptive=True,
                description="Synapse density visualization thresholds",
            ),
            ThresholdProfile(
                name="visualization_neuron_count",
                threshold_type=ThresholdType.VISUALIZATION,
                default_value=0.0,
                method=ThresholdMethod.LINEAR,
                n_bins=5,
                adaptive=True,
                description="Neuron count visualization thresholds",
            ),
            ThresholdProfile(
                name="visualization_hexagon_grid",
                threshold_type=ThresholdType.VISUALIZATION,
                default_value=0.0,
                method=ThresholdMethod.DATA_DRIVEN,
                n_bins=5,
                adaptive=True,
                description="Hexagon grid visualization thresholds",
            ),
            # Performance Thresholds
            ThresholdProfile(
                name="performance_slow_operation",
                threshold_type=ThresholdType.PERFORMANCE,
                default_value=1.0,
                min_value=0.1,
                max_value=60.0,
                description="Threshold for identifying slow operations (seconds)",
            ),
            ThresholdProfile(
                name="performance_very_slow_operation",
                threshold_type=ThresholdType.PERFORMANCE,
                default_value=5.0,
                min_value=1.0,
                max_value=300.0,
                description="Threshold for identifying very slow operations (seconds)",
            ),
            # Memory Thresholds
            ThresholdProfile(
                name="memory_optimization_trigger",
                threshold_type=ThresholdType.MEMORY,
                default_value=1000.0,
                min_value=100.0,
                max_value=8192.0,
                description="Memory usage threshold for optimization (MB)",
            ),
            ThresholdProfile(
                name="memory_warning_level",
                threshold_type=ThresholdType.MEMORY,
                default_value=2048.0,
                min_value=500.0,
                max_value=16384.0,
                description="Memory usage warning threshold (MB)",
            ),
            # Quality Thresholds
            ThresholdProfile(
                name="quality_data_completeness",
                threshold_type=ThresholdType.QUALITY,
                default_value=95.0,
                min_value=50.0,
                max_value=100.0,
                description="Data completeness quality threshold (percentage)",
            ),
            ThresholdProfile(
                name="quality_confidence_score",
                threshold_type=ThresholdType.QUALITY,
                default_value=0.8,
                min_value=0.0,
                max_value=1.0,
                description="Confidence score quality threshold",
            ),
            # Statistical Thresholds
            ThresholdProfile(
                name="statistical_significance",
                threshold_type=ThresholdType.STATISTICAL,
                default_value=0.05,
                min_value=0.001,
                max_value=0.1,
                description="Statistical significance threshold (p-value)",
            ),
            ThresholdProfile(
                name="statistical_correlation",
                threshold_type=ThresholdType.STATISTICAL,
                default_value=0.5,
                min_value=0.0,
                max_value=1.0,
                description="Correlation significance threshold",
            ),
        ]

        for profile in default_profiles:
            if profile.validate():
                self._profiles[profile.name] = profile
            else:
                logger.warning(f"Invalid default profile: {profile.name}")

        self._defaults_loaded = True
        logger.info(f"Loaded {len(self._profiles)} default threshold profiles")

    def register_profile(self, profile: ThresholdProfile) -> bool:
        """
        Register a new threshold profile.

        Args:
            profile: The threshold profile to register

        Returns:
            True if registration was successful, False otherwise
        """
        if not profile.validate():
            logger.error(f"Invalid threshold profile: {profile.name}")
            return False

        self._profiles[profile.name] = profile
        logger.debug(f"Registered threshold profile: {profile.name}")
        return True

    def get_profile(self, name: str) -> Optional[ThresholdProfile]:
        """
        Get a threshold profile by name.

        Args:
            name: Name of the profile to retrieve

        Returns:
            The threshold profile or None if not found
        """
        return self._profiles.get(name)


    def get_threshold_value(
        self, profile_name: str, context: Optional[str] = None
    ) -> float:
        """
        Get the current threshold value for a profile.

        Args:
            profile_name: Name of the threshold profile
            context: Optional context identifier for settings

        Returns:
            The current threshold value
        """
        settings_key = f"{profile_name}:{context}" if context else profile_name

        if settings_key in self._settings:
            return self._settings[settings_key].current_value

        profile = self.get_profile(profile_name)
        if profile:
            return profile.default_value

        logger.warning(f"Unknown threshold profile: {profile_name}")
        return 0.0

    def set_threshold_value(
        self, profile_name: str, value: float, context: Optional[str] = None
    ) -> bool:
        """
        Set the threshold value for a profile.

        Args:
            profile_name: Name of the threshold profile
            value: New threshold value
            context: Optional context identifier for settings

        Returns:
            True if the value was set successfully, False otherwise
        """
        profile = self.get_profile(profile_name)
        if not profile:
            logger.error(f"Unknown threshold profile: {profile_name}")
            return False

        clamped_value = profile.clamp_value(value)
        if clamped_value != value:
            logger.warning(f"Threshold value clamped from {value} to {clamped_value}")

        settings_key = f"{profile_name}:{context}" if context else profile_name

        if settings_key in self._settings:
            self._settings[settings_key].current_value = clamped_value
        else:
            self._settings[settings_key] = ThresholdSettings(
                profile=profile, current_value=clamped_value
            )

        logger.debug(f"Set threshold {profile_name} to {clamped_value}")
        return True

    def get_settings(
        self, profile_name: str, context: Optional[str] = None
    ) -> Optional[ThresholdSettings]:
        """
        Get complete threshold settings for a profile.

        Args:
            profile_name: Name of the threshold profile
            context: Optional context identifier for settings

        Returns:
            The threshold settings or None if not found
        """
        settings_key = f"{profile_name}:{context}" if context else profile_name

        if settings_key in self._settings:
            return self._settings[settings_key]

        profile = self.get_profile(profile_name)
        if profile:
            # Create default settings
            settings = ThresholdSettings(
                profile=profile, current_value=profile.default_value
            )
            self._settings[settings_key] = settings
            return settings

        return None

    def update_computed_thresholds(
        self,
        profile_name: str,
        thresholds: List[float],
        context: Optional[str] = None,
        cache_key: Optional[str] = None,
    ) -> bool:
        """
        Update computed thresholds for a profile.

        Args:
            profile_name: Name of the threshold profile
            thresholds: List of computed threshold values
            context: Optional context identifier for settings
            cache_key: Optional cache key for the computation

        Returns:
            True if update was successful, False otherwise
        """
        settings = self.get_settings(profile_name, context)
        if not settings:
            return False

        # Validate thresholds are in ascending order
        if not all(
            thresholds[i] <= thresholds[i + 1] for i in range(len(thresholds) - 1)
        ):
            logger.error(f"Thresholds not in ascending order for {profile_name}")
            return False

        settings.computed_thresholds = thresholds
        settings.cache_key = cache_key
        from datetime import datetime

        settings.last_computed = datetime.now().isoformat()

        logger.debug(
            f"Updated computed thresholds for {profile_name}: {len(thresholds)} values"
        )
        return True



    def import_config(self, config: Dict[str, Any]) -> bool:
        """
        Import threshold configuration.

        Args:
            config: Configuration dictionary to import

        Returns:
            True if import was successful, False otherwise
        """
        try:
            # Import profiles
            if "profiles" in config:
                for name, profile_data in config["profiles"].items():
                    profile = ThresholdProfile(
                        name=profile_data["name"],
                        threshold_type=ThresholdType(profile_data["type"]),
                        default_value=profile_data["default_value"],
                        min_value=profile_data.get("min_value"),
                        max_value=profile_data.get("max_value"),
                        method=ThresholdMethod(profile_data.get("method", "linear")),
                        n_bins=profile_data.get("n_bins", 5),
                        adaptive=profile_data.get("adaptive", False),
                        description=profile_data.get("description", ""),
                        metadata=profile_data.get("metadata", {}),
                    )
                    if not self.register_profile(profile):
                        logger.warning(f"Failed to import profile: {name}")

            # Import settings
            if "settings" in config:
                for key, settings_data in config["settings"].items():
                    profile_name = settings_data["profile_name"]
                    profile = self.get_profile(profile_name)
                    if profile:
                        settings = ThresholdSettings(
                            profile=profile,
                            current_value=settings_data["current_value"],
                            computed_thresholds=settings_data.get(
                                "computed_thresholds", []
                            ),
                            cache_key=settings_data.get("cache_key"),
                            last_computed=settings_data.get("last_computed"),
                            metadata=settings_data.get("metadata", {}),
                        )
                        self._settings[key] = settings

            logger.info("Successfully imported threshold configuration")
            return True

        except Exception as e:
            logger.error(f"Failed to import threshold configuration: {e}")
            return False




# Global threshold configuration instance
_global_threshold_config: Optional[ThresholdConfig] = None


def get_threshold_config() -> ThresholdConfig:
    """
    Get the global threshold configuration instance.

    Returns:
        The global ThresholdConfig instance
    """
    global _global_threshold_config
    if _global_threshold_config is None:
        _global_threshold_config = ThresholdConfig()
    return _global_threshold_config


def configure_thresholds(config_dict: Optional[Dict[str, Any]] = None) -> None:
    """
    Configure global thresholds from a configuration dictionary.

    Args:
        config_dict: Optional configuration dictionary to import
    """
    config = get_threshold_config()
    if config_dict:
        config.import_config(config_dict)
    logger.info("Global threshold configuration initialized")
