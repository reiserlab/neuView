"""
Neuron Selection Service for handling neuron selection logic.

This service centralizes all neuron selection operations that were previously
in the PageGenerator class, providing algorithms for selecting neurons based
on various criteria like soma side, synapse percentiles, and availability.
"""

import logging
import time
from typing import Dict, Any, Optional, List
import pandas as pd
from .file_service import FileService

logger = logging.getLogger(__name__)


class NeuronSelectionService:
    """
    Service for handling neuron selection operations.

    This service extracts complex neuron selection logic from the PageGenerator
    to provide a centralized, testable interface for neuron selection algorithms.
    """

    def __init__(self, config):
        """
        Initialize the neuron selection service.

        Args:
            config: Configuration object
        """
        self.config = config

    def select_bodyids_by_soma_side(
        self,
        neuron_type: str,
        neurons_df: pd.DataFrame,
        soma_side: Optional[str],
        percentile: float = 95,
    ) -> List[int]:
        """
        Select bodyID(s) based on soma side and synapse count percentiles.

        For 'combined' soma side, selects one neuron from each side (left and right).
        For specific sides, selects one neuron from that side.
        Optimization: If only one neuron exists for a side, selects it directly without synapse queries.

        Args:
            neuron_type: The neuron type name for logging
            neurons_df: DataFrame containing neuron data with bodyId, pre, post, and somaSide columns
            soma_side: Target soma side ('left', 'right', 'combined', 'all', etc.)
            percentile: Target percentile (0-100), defaults to 95

        Returns:
            List of bodyIds selected based on criteria
        """
        if neurons_df.empty:
            logger.warning("Empty neurons DataFrame, no bodyIds selected")
            return []

        # Ensure we have soma side information
        if "somaSide" not in neurons_df.columns:
            logger.warning("No somaSide column found, falling back to single selection")
            # Check if only one neuron exists - skip synapse calculation if so
            if len(neurons_df) == 1:
                bodyid = int(neurons_df.iloc[0]["bodyId"])
                logger.debug(
                    f"Selected single available bodyId {bodyid} (no soma side filtering)"
                )
                return [bodyid]
            return [
                self.select_bodyid_by_synapse_percentile(
                    neuron_type, neurons_df, percentile
                )
            ]

        selected_bodyids = []

        if soma_side == "combined":
            selected_bodyids = self._select_combined_soma_sides(
                neuron_type, neurons_df, percentile
            )
        else:
            selected_bodyids = self._select_specific_soma_side(
                neuron_type, neurons_df, soma_side, percentile
            )

        # Fallback to first available neuron if no selection was made
        if not selected_bodyids and not neurons_df.empty:
            fallback_bodyid = int(neurons_df.iloc[0]["bodyId"])
            selected_bodyids.append(fallback_bodyid)
            logger.info(f"Fallback: selected first available bodyId {fallback_bodyid}")

        return selected_bodyids

    def select_bodyid_by_synapse_percentile(
        self, neuron_type: str, neurons_df: pd.DataFrame, percentile: float = 95
    ) -> int:
        """
        Select a single bodyId based on synapse count percentile.

        Args:
            neuron_type: The neuron type name for logging
            neurons_df: DataFrame containing neuron data with bodyId, pre, post columns
            percentile: Target percentile (0-100), defaults to 95

        Returns:
            Selected bodyId

        Raises:
            ValueError: If no suitable neuron found or invalid data
        """
        if neurons_df.empty:
            raise ValueError("Empty neurons DataFrame provided")

        # Ensure required columns exist
        required_columns = ["bodyId", "pre", "post"]
        missing_columns = [
            col for col in required_columns if col not in neurons_df.columns
        ]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Calculate total synapses (pre + post)
        neurons_with_synapses = neurons_df.copy()
        neurons_with_synapses["total_synapses"] = neurons_with_synapses["pre"].fillna(
            0
        ) + neurons_with_synapses["post"].fillna(0)

        # Filter out neurons with no synapses
        valid_neurons = neurons_with_synapses[
            neurons_with_synapses["total_synapses"] > 0
        ]

        if valid_neurons.empty:
            # If no neurons have synapses, fall back to first neuron
            logger.warning(
                f"No neurons with synapses found for {neuron_type}, selecting first available"
            )
            return int(neurons_df.iloc[0]["bodyId"])

        # Calculate percentile threshold
        threshold = valid_neurons["total_synapses"].quantile(percentile / 100.0)

        # Select neurons at or above the threshold
        candidate_neurons = valid_neurons[valid_neurons["total_synapses"] >= threshold]

        if candidate_neurons.empty:
            # If threshold is too high, select the neuron with maximum synapses
            logger.debug(
                f"No neurons above {percentile}th percentile for {neuron_type}, selecting max"
            )
            max_neuron = valid_neurons.loc[valid_neurons["total_synapses"].idxmax()]
            return int(max_neuron["bodyId"])

        # From candidates, select the one with highest synapse count
        selected_neuron = candidate_neurons.loc[
            candidate_neurons["total_synapses"].idxmax()
        ]
        selected_bodyid = int(selected_neuron["bodyId"])

        logger.debug(
            f"Selected bodyId {selected_bodyid} for {neuron_type} "
            f"(synapse count: {selected_neuron['total_synapses']}, "
            f"{percentile}th percentile threshold: {threshold:.1f})"
        )

        return selected_bodyid

    def get_available_soma_sides(self, neuron_type: str, connector) -> Dict[str, str]:
        """
        Get available soma sides for a neuron type and generate navigation links.

        Args:
            neuron_type: The neuron type to check
            connector: NeuPrint connector instance

        Returns:
            Dictionary mapping soma side names to their URLs/filenames
        """
        soma_side_links = {}

        try:
            # Query to get available soma sides for this neuron type
            # Handle FAFB-specific property names and prioritize rootSide over somaSide
            if connector.dataset_adapter.dataset_info.name == "flywire-fafb":
                # FAFB might use 'side' property instead of 'somaSide'
                query = f"""
                    MATCH (n:Neuron)
                    WHERE n.type = "{neuron_type}" AND (n.rootSide IS NOT NULL OR n.somaSide IS NOT NULL OR n.side IS NOT NULL)
                    RETURN DISTINCT
                        CASE
                            WHEN n.rootSide IS NOT NULL THEN n.rootSide
                            WHEN n.somaSide IS NOT NULL THEN n.somaSide
                            WHEN n.side IS NOT NULL THEN
                                CASE n.side
                                    WHEN 'LEFT' THEN 'L'
                                    WHEN 'RIGHT' THEN 'R'
                                    WHEN 'CENTER' THEN 'C'
                                    WHEN 'MIDDLE' THEN 'C'
                                    WHEN 'left' THEN 'L'
                                    WHEN 'right' THEN 'R'
                                    WHEN 'center' THEN 'C'
                                    WHEN 'middle' THEN 'C'
                                    ELSE n.side
                                END
                            ELSE NULL
                        END as somaSide
                    ORDER BY somaSide
                """
            else:
                # Standard query for other datasets - prioritize rootSide over somaSide
                query = f"""
                    MATCH (n:Neuron)
                    WHERE n.type = "{neuron_type}" AND (n.rootSide IS NOT NULL OR n.somaSide IS NOT NULL)
                    RETURN DISTINCT
                        CASE
                            WHEN n.rootSide IS NOT NULL THEN n.rootSide
                            ELSE n.somaSide
                        END as somaSide
                    ORDER BY somaSide
                """

            result = connector.client.fetch_custom(query)

            if result is None or result.empty:
                return soma_side_links

            available_sides = result["somaSide"].tolist()

            # Map soma side codes to readable names and filenames
            # Note: "C" maps to "middle" (center), not "combined"
            side_mapping = {
                "L": ("left", FileService.generate_filename(neuron_type, "left")),
                "R": ("right", FileService.generate_filename(neuron_type, "right")),
                "M": ("middle", FileService.generate_filename(neuron_type, "middle")),
                "C": ("middle", FileService.generate_filename(neuron_type, "middle")),
            }

            # Generate links for available sides
            for side_code in available_sides:
                if side_code in side_mapping:
                    readable_name, filename = side_mapping[side_code]
                    soma_side_links[readable_name] = filename

            # Apply the same combined page logic as SomaDetectionService
            if available_sides:
                # Count sides with actual data and get soma side distribution
                sides_with_data = 0
                unknown_count = 0

                # Query to get detailed soma side distribution - prioritize rootSide over somaSide
                if connector.dataset_adapter.dataset_info.name == "flywire-fafb":
                    count_query = f"""
                        MATCH (n:Neuron)
                        WHERE n.type = "{neuron_type}"
                        WITH n,
                            CASE
                                WHEN n.rootSide IS NOT NULL THEN n.rootSide
                                WHEN n.somaSide IS NOT NULL THEN n.somaSide
                                WHEN n.side IS NOT NULL THEN
                                    CASE n.side
                                        WHEN 'LEFT' THEN 'L'
                                        WHEN 'RIGHT' THEN 'R'
                                        WHEN 'CENTER' THEN 'M'
                                        WHEN 'MIDDLE' THEN 'M'
                                        WHEN 'left' THEN 'L'
                                        WHEN 'right' THEN 'R'
                                        WHEN 'center' THEN 'M'
                                        WHEN 'middle' THEN 'M'
                                        ELSE n.side
                                    END
                                ELSE NULL
                            END as normalizedSide
                        RETURN
                            COUNT(CASE WHEN normalizedSide = 'L' THEN 1 END) as leftCount,
                            COUNT(CASE WHEN normalizedSide = 'R' THEN 1 END) as rightCount,
                            COUNT(CASE WHEN normalizedSide = 'M' THEN 1 END) as middleCount,
                            COUNT(*) as totalCount
                    """
                else:
                    count_query = f"""
                        MATCH (n:Neuron)
                        WHERE n.type = "{neuron_type}"
                        WITH
                            CASE
                                WHEN n.rootSide IS NOT NULL THEN n.rootSide
                                ELSE n.somaSide
                            END as effectiveSide
                        RETURN
                            COUNT(CASE WHEN effectiveSide = 'L' THEN 1 END) as leftCount,
                            COUNT(CASE WHEN effectiveSide = 'R' THEN 1 END) as rightCount,
                            COUNT(CASE WHEN effectiveSide = 'M' THEN 1 END) as middleCount,
                            COUNT(*) as totalCount
                    """

                try:
                    count_result = connector.client.fetch_custom(count_query)
                    if count_result is not None and not count_result.empty:
                        row = count_result.iloc[0]
                        left_count = int(row.get("leftCount", 0))
                        right_count = int(row.get("rightCount", 0))
                        middle_count = int(row.get("middleCount", 0))
                        total_count = int(row.get("totalCount", 0))

                        sides_with_data = sum(
                            1
                            for count in [left_count, right_count, middle_count]
                            if count > 0
                        )
                        unknown_count = (
                            total_count - left_count - right_count - middle_count
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to get detailed soma side counts for {neuron_type}: {e}"
                    )
                    # Fallback: assume each available side has data
                    sides_with_data = len(available_sides)
                    unknown_count = 0

                # Apply the same logic as SomaDetectionService
                should_add_combined = (
                    sides_with_data > 1
                    or (sides_with_data == 0 and unknown_count > 0)
                    or (unknown_count > 0 and sides_with_data > 0)
                )

                # Override: Don't add combined link for single-side neuron types
                if sides_with_data == 1 and unknown_count == 0:
                    should_add_combined = False

                # Only add combined if it's not already added via 'C' mapping and meets criteria
                if "combined" not in soma_side_links and should_add_combined:
                    soma_side_links["combined"] = FileService.generate_filename(
                        neuron_type, "combined"
                    )

            logger.debug(
                f"Available soma sides for {neuron_type}: {list(soma_side_links.keys())}"
            )

        except Exception as e:
            logger.error(f"Error getting available soma sides for {neuron_type}: {e}")

        return soma_side_links

    def _select_combined_soma_sides(
        self, neuron_type: str, neurons_df: pd.DataFrame, percentile: float
    ) -> List[int]:
        """
        Select one neuron from each available side for 'combined' soma side.

        Args:
            neuron_type: The neuron type name for logging
            neurons_df: DataFrame containing neuron data
            percentile: Target percentile for selection

        Returns:
            List of selected bodyIds
        """
        selected_bodyids = []
        available_sides = neurons_df["somaSide"].unique()

        # Map side codes to readable names for logging
        side_names = {"L": "left", "R": "right", "M": "middle"}

        for side_code in ["L", "R"]:  # Focus on left and right for 'combined'
            if side_code in available_sides:
                side_neurons_mask = neurons_df["somaSide"] == side_code
                side_neurons = neurons_df.loc[side_neurons_mask].copy()
                if not side_neurons.empty:
                    try:
                        # Optimization: If only one neuron for this side, select it directly
                        if len(side_neurons) == 1:
                            start_time = time.time()
                            bodyid = int(side_neurons.iloc[0]["bodyId"])
                            end_time = time.time()
                            side_name = side_names.get(side_code, side_code)
                            logger.debug(
                                f"Selected single available bodyId {bodyid} for {side_name} side "
                                f"(optimization saved synapse calculation, took {end_time - start_time:.4f}s)"
                            )
                        else:
                            bodyid = self.select_bodyid_by_synapse_percentile(
                                neuron_type, side_neurons, percentile
                            )
                            side_name = side_names.get(side_code, side_code)
                            logger.debug(
                                f"Selected bodyId {bodyid} for {side_name} side"
                            )
                        selected_bodyids.append(bodyid)
                    except Exception as e:
                        logger.warning(
                            f"Could not select neuron for side {side_code}: {e}"
                        )

        # If no left/right neurons found, try middle
        if not selected_bodyids and "M" in available_sides:
            middle_neurons_mask = neurons_df["somaSide"] == "M"
            middle_neurons = neurons_df.loc[middle_neurons_mask].copy()
            if not middle_neurons.empty:
                try:
                    # Optimization: If only one middle neuron, select it directly
                    if len(middle_neurons) == 1:
                        start_time = time.time()
                        bodyid = int(middle_neurons.iloc[0]["bodyId"])
                        end_time = time.time()
                        logger.debug(
                            f"Selected single available bodyId {bodyid} for middle side "
                            f"(optimization saved synapse calculation, took {end_time - start_time:.4f}s)"
                        )
                    else:
                        bodyid = self.select_bodyid_by_synapse_percentile(
                            neuron_type, middle_neurons, percentile
                        )
                        logger.debug(
                            f"Selected bodyId {bodyid} for middle side (no left/right available)"
                        )
                    selected_bodyids.append(bodyid)
                except Exception as e:
                    logger.warning(f"Could not select neuron for middle side: {e}")

        return selected_bodyids

    def _select_specific_soma_side(
        self,
        neuron_type: str,
        neurons_df: pd.DataFrame,
        soma_side: str,
        percentile: float,
    ) -> List[int]:
        """
        Select neuron(s) for a specific soma side.

        Args:
            neuron_type: The neuron type name for logging
            neurons_df: DataFrame containing neuron data
            soma_side: Specific soma side to select
            percentile: Target percentile for selection

        Returns:
            List of selected bodyIds
        """
        selected_bodyids = []
        filtered_neurons = neurons_df

        if soma_side in ["left", "right", "middle"]:
            # Map readable names to side codes
            side_mapping = {"left": "L", "right": "R", "middle": "M"}
            side_code = side_mapping.get(soma_side)

            if side_code and "somaSide" in neurons_df.columns:
                side_mask = neurons_df["somaSide"] == side_code
                filtered_neurons = neurons_df.loc[side_mask].copy()

                if filtered_neurons.empty:
                    logger.warning(f"No neurons found for {soma_side} side")
                    return []

        # Optimization: If only one neuron after filtering, select it directly
        if len(filtered_neurons) == 1:
            start_time = time.time()
            bodyid = int(filtered_neurons.iloc[0]["bodyId"])
            end_time = time.time()
            logger.debug(
                f"Selected single available bodyId {bodyid} for {soma_side} side "
                f"(optimization saved synapse calculation, took {end_time - start_time:.4f}s)"
            )
            selected_bodyids.append(bodyid)
        else:
            # Apply percentile selection to filtered neurons
            try:
                bodyid = self.select_bodyid_by_synapse_percentile(
                    neuron_type, filtered_neurons, percentile
                )
                selected_bodyids.append(bodyid)
            except Exception as e:
                logger.warning(f"Could not select neuron: {e}")

        return selected_bodyids


