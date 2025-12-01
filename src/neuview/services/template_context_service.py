"""
Template Context Service

Handles the preparation of template context data for page generation,
extracting common logic for processing neuron metadata, preparing template
variables, and assembling context dictionaries.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from ..utils import get_git_version
from .statistics_calculator import (
    CombinedStatisticsCalculator,
    SideStatisticsCalculator,
)

logger = logging.getLogger(__name__)


class TemplateContextService:
    """Service for preparing template context data for HTML page generation."""

    def __init__(self, page_generator):
        """Initialize template context service.

        Args:
            page_generator: Page generator instance for accessing utilities and config
        """
        self.page_generator = page_generator
        self.text_utils = page_generator.text_utils
        self.citations = page_generator.citations
        self.config = page_generator.config

        # Initialize connectivity combination service
        from .connectivity_combination_service import ConnectivityCombinationService

        self.connectivity_combination_service = ConnectivityCombinationService()

        # Initialize ROI combination service
        from .roi_combination_service import ROICombinationService

        self.roi_combination_service = ROICombinationService()

    def prepare_neuron_page_context(
        self,
        neuron_type: str,
        neuron_data: Dict[str, Any],
        soma_side: str,
        connectivity_data: Optional[Dict] = None,
        analysis_results: Optional[Dict] = None,
        urls: Optional[Dict] = None,
        additional_context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Prepare complete context for neuron page template.

        Args:
            neuron_type: The neuron type name
            neuron_data: Data returned from NeuPrintConnector
            soma_side: Soma side filter used
            connectivity_data: Optional connectivity data
            analysis_results: Optional analysis results (column_analysis, layer_analysis, etc.)
            urls: Optional URLs (neuroglancer_url, neuprint_url, etc.)
            additional_context: Optional additional context data

        Returns:
            Complete context dictionary for template rendering
        """
        # Process neuron metadata (synonyms, flywire types)
        neurons_df = neuron_data.get("neurons", pd.DataFrame())
        metadata = self.process_neuron_metadata(neurons_df, neuron_type)

        # Find YouTube video for this neuron type (only for right soma side)
        youtube_url = self._get_youtube_url(neuron_type, soma_side)

        # Get available soma sides for navigation
        soma_side_links = urls.get("soma_side_links", []) if urls else []

        # Use summary dictionaries directly
        summary = neuron_data.get("summary", {})
        complete_summary = neuron_data.get(
            "complete_summary", neuron_data.get("summary", {})
        )

        # Process connectivity data for display based on soma side
        raw_connectivity = connectivity_data or neuron_data.get("connectivity", {})
        processed_connectivity = (
            self.connectivity_combination_service.process_connectivity_for_display(
                raw_connectivity, soma_side
            )
        )

        # Process ROI data for display based on soma side
        raw_roi_summary = (
            analysis_results.get("roi_summary") if analysis_results else None
        )
        processed_roi_summary = (
            self.roi_combination_service.process_roi_data_for_display(
                raw_roi_summary, soma_side
            )
        )

        # Prepare summary statistics for display
        summary_stats = self.prepare_summary_statistics(
            summary, complete_summary, processed_connectivity, soma_side
        )

        # Prepare base context
        context = {
            "config": self.config,
            "neuron_data": neuron_data,
            "neuron_type": neuron_type,
            "soma_side": soma_side,
            "summary": summary,
            "complete_summary": complete_summary,
            "neurons_df": neuron_data.get("neurons", pd.DataFrame()),
            "connectivity": processed_connectivity,
            "soma_side_links": soma_side_links,
            "generation_time": datetime.now(),
            "git_version": get_git_version(),
            "youtube_url": youtube_url,
            "processed_synonyms": metadata["processed_synonyms"],
            "processed_flywire_types": metadata["processed_flywire_types"],
            "is_neuron_page": True,
            "summary_stats": summary_stats,
        }

        # Add analysis results if provided
        if analysis_results:
            context.update(analysis_results)
            # Override roi_summary with processed version
            context["roi_summary"] = processed_roi_summary

        # Add URLs if provided
        if urls:
            for url_key, url_value in urls.items():
                if url_key not in context:  # Don't override existing keys
                    context[url_key] = url_value

        # Add any additional context
        if additional_context:
            context.update(additional_context)

        return context

    def process_neuron_metadata(
        self, neurons_df: Optional[pd.DataFrame], neuron_type: str
    ) -> Dict[str, Dict]:
        """Process synonyms and flywire types from neuron DataFrame.

        Args:
            neurons_df: DataFrame containing neuron data
            neuron_type: Name of the neuron type for flywire comparison

        Returns:
            Dictionary containing processed synonyms and flywire types
        """
        processed_synonyms = {}
        processed_flywire_types = {}

        if neurons_df is None or neurons_df.empty:
            return {
                "processed_synonyms": processed_synonyms,
                "processed_flywire_types": processed_flywire_types,
            }

        # Process synonyms
        synonyms_raw = self._extract_column_value(
            neurons_df, ["synonyms_y", "synonyms"]
        )
        if pd.notna(synonyms_raw):
            processed_synonyms = self.text_utils.process_synonyms(
                str(synonyms_raw),
                self.citations,
                neuron_type,
                str(self.page_generator.output_dir),
            )

        # Process flywireType - collect all unique values
        flywire_type_raw = self._extract_flywire_types(neurons_df)
        if flywire_type_raw:
            processed_flywire_types = self.text_utils.process_flywire_types(
                flywire_type_raw, neuron_type
            )

        return {
            "processed_synonyms": processed_synonyms,
            "processed_flywire_types": processed_flywire_types,
        }

    def _extract_column_value(self, df: pd.DataFrame, column_names: list) -> Any:
        """Extract value from first available column in the DataFrame.

        Args:
            df: DataFrame to search
            column_names: List of column names to try in order

        Returns:
            Value from first available column, or None if none found
        """
        for col_name in column_names:
            if col_name in df.columns:
                return df[col_name].iloc[0] if not df.empty else None
        return None

    def _extract_flywire_types(self, df: pd.DataFrame) -> Optional[str]:
        """Extract and combine all unique flywire types from DataFrame.

        Args:
            df: DataFrame containing neuron data

        Returns:
            Comma-separated string of unique flywire types, or None if none found
        """
        flywire_columns = ["flywireType_y", "flywireType"]

        for col_name in flywire_columns:
            if col_name in df.columns:
                # Get all unique flywireType values, excluding NaN
                unique_types = df[col_name].dropna().unique()
                if len(unique_types) > 0:
                    return ", ".join(sorted(set(str(t) for t in unique_types)))

        return None

    def _get_youtube_url(self, neuron_type: str, soma_side: str) -> Optional[str]:
        """Get YouTube URL for neuron type if available.

        Args:
            neuron_type: Name of the neuron type
            soma_side: Soma side (YouTube videos only shown for 'right' side)

        Returns:
            YouTube URL if video found and soma_side is 'right', None otherwise
        """
        if soma_side != "right":
            return None

        youtube_video_id = self.page_generator._find_youtube_video(neuron_type)
        if youtube_video_id:
            return f"https://www.youtube.com/watch?v={youtube_video_id}"

        return None

    def prepare_minimal_context(
        self, neuron_type: str, soma_side: str, **kwargs
    ) -> Dict[str, Any]:
        """Prepare minimal context for simple template rendering.

        Args:
            neuron_type: The neuron type name
            soma_side: Soma side filter used
            **kwargs: Additional context items

        Returns:
            Minimal context dictionary
        """
        context = {
            "config": self.config,
            "neuron_type": neuron_type,
            "soma_side": soma_side,
            "generation_time": datetime.now(),
            "git_version": get_git_version(),
            "is_neuron_page": True,
        }

        # Add any additional items
        context.update(kwargs)

        return context

    def add_neuroglancer_variables(
        self, context: Dict[str, Any], neuroglancer_vars: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add Neuroglancer-specific variables to context.

        Args:
            context: Existing context dictionary
            neuroglancer_vars: Neuroglancer variables from URL generation

        Returns:
            Updated context with Neuroglancer variables
        """
        neuroglancer_keys = [
            "visible_neurons",
            "visible_rois",
            "website_title",
            "neuron_query",
            "connected_bids",
        ]

        for key in neuroglancer_keys:
            if key in neuroglancer_vars:
                context[key] = neuroglancer_vars[key]

        return context

    def validate_context(self, context: Dict[str, Any]) -> bool:
        """Validate that context contains required keys for template rendering.

        Args:
            context: Context dictionary to validate

        Returns:
            True if context is valid, False otherwise
        """
        required_keys = ["config", "neuron_type", "soma_side", "generation_time"]

        for key in required_keys:
            if key not in context:
                logger.warning(f"Missing required context key: {key}")
                return False

        return True

    def prepare_summary_statistics(
        self,
        summary: Dict[str, Any],
        complete_summary: Dict[str, Any],
        connectivity: Dict[str, Any],
        soma_side: str,
    ) -> Dict[str, Any]:
        """
        Prepare all summary statistics for template rendering.

        This method uses specialized calculator classes to compute statistics,
        making templates cleaner and logic more testable.

        Args:
            summary: Side-specific summary data
            complete_summary: Complete summary data (all sides)
            connectivity: Connectivity data
            soma_side: The soma side ('left', 'right', 'middle', 'combined')

        Returns:
            Dictionary with all calculated statistics ready for template use
        """
        if soma_side == "combined":
            return self._prepare_combined_summary_stats(complete_summary, connectivity)
        elif soma_side in ["left", "right", "middle"]:
            return self._prepare_side_summary_stats(
                summary, complete_summary, connectivity, soma_side
            )
        else:
            logger.warning(f"Unknown soma_side: {soma_side}")
            return {}

    def _prepare_side_summary_stats(
        self,
        summary: Dict[str, Any],
        complete_summary: Dict[str, Any],
        connectivity: Dict[str, Any],
        soma_side: str,
    ) -> Dict[str, Any]:
        """
        Prepare summary statistics for individual side pages (L/R/M).

        Uses SideStatisticsCalculator to compute statistics for a single hemisphere.

        Args:
            summary: Side-specific summary data
            complete_summary: Complete summary data
            connectivity: Connectivity data
            soma_side: The soma side ('left', 'right', 'middle')

        Returns:
            Dictionary with side-specific calculated statistics
        """
        calculator = SideStatisticsCalculator(
            summary, complete_summary, connectivity, soma_side
        )
        stats = calculator.calculate()
        return stats.to_template_dict()

    def _prepare_combined_summary_stats(
        self, complete_summary: Dict[str, Any], connectivity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare summary statistics for combined pages (C).

        Uses CombinedStatisticsCalculator to compute statistics across all hemispheres.

        Args:
            complete_summary: Complete summary data
            connectivity: Connectivity data

        Returns:
            Dictionary with combined calculated statistics
        """
        calculator = CombinedStatisticsCalculator(complete_summary, connectivity)
        stats = calculator.calculate()
        return stats.to_template_dict()
