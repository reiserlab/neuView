"""
Connectivity combination service for handling L/R partner combination in combined pages.

This service modifies connectivity data for combined pages by merging entries
with the same partner type but different soma sides (L/R) into single entries
while preserving the original data for individual side pages.
"""

import logging
from typing import Dict, List, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConnectivityCombinationService:
    """
    Service for combining L/R connectivity entries in combined pages.

    For combined pages (soma_side="combined"), this service:
    1. Merges partner entries with same type but different soma sides (L/R)
    2. Combines weights and connection counts
    3. Preserves most common neurotransmitter
    4. Updates percentages based on combined totals

    For individual side pages (L/R/M), the original data is preserved unchanged.
    """

    def __init__(self):
        """Initialize the connectivity combination service."""
        pass

    def process_connectivity_for_display(
        self, connectivity_data: Dict[str, Any], soma_side: str
    ) -> Dict[str, Any]:
        """
        Process connectivity data for display based on soma side.

        For combined pages, merges L/R entries for the same partner type.
        For individual side pages, returns original data unchanged.

        Args:
            connectivity_data: Raw connectivity data from neuprint connector
            soma_side: Target soma side ("combined", "left", "right", "middle")

        Returns:
            Processed connectivity data appropriate for the soma side
        """
        if not connectivity_data or soma_side != "combined":
            # For individual side pages, return original data
            return connectivity_data

        logger.debug("Combining connectivity data for combined page")

        result = {
            "upstream": self._combine_partner_entries(
                connectivity_data.get("upstream", [])
            ),
            "downstream": self._combine_partner_entries(
                connectivity_data.get("downstream", [])
            ),
            "total_upstream": connectivity_data.get("total_upstream", []),
            "total_downstream": connectivity_data.get("total_downstream", []),
            "total_left": connectivity_data.get("total_left", []),
            "total_right": connectivity_data.get("total_right", []),
            "avg_upstream": connectivity_data.get("avg_upstream", []),
            "avg_downstream": connectivity_data.get("avg_downstream", []),
            "avg_connections": connectivity_data.get("avg_connections", []),
            "regional_connections": connectivity_data.get("regional_connections", {}),
            "note": connectivity_data.get("note", ""),
        }

        return result

    def _combine_partner_entries(
        self, partners: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Combine partner entries with the same type but different soma sides.

        Args:
            partners: List of partner dictionaries

        Returns:
            List of combined partner dictionaries
        """
        if not partners:
            return []

        # Group partners by type (ignoring soma side)
        type_groups = defaultdict(list)

        for partner in partners:
            partner_type = partner.get("type", "Unknown")
            type_groups[partner_type].append(partner)

        combined_partners = []

        for partner_type, group_partners in type_groups.items():
            if len(group_partners) == 1:
                # Only one entry for this type, check if it needs soma side removed
                partner = group_partners[0].copy()
                soma_side = partner.get("soma_side", "")

                # For combined display, remove soma side suffix from display
                if soma_side in ["L", "R"]:
                    partner["soma_side"] = ""  # Remove soma side for display

                combined_partners.append(partner)
            else:
                # Multiple entries for same type - need to combine
                combined_partner = self._merge_partner_group(
                    partner_type, group_partners
                )
                combined_partners.append(combined_partner)

        # Sort by weight descending and recalculate percentages
        combined_partners.sort(key=lambda x: x.get("weight", 0), reverse=True)
        self._recalculate_percentages(combined_partners)

        return combined_partners

    def _merge_partner_group(
        self, partner_type: str, partners: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge multiple partner entries of the same type.

        Args:
            partner_type: The partner type name
            partners: List of partner entries to merge

        Returns:
            Single merged partner entry
        """
        # Initialize combined entry
        combined = {
            "type": partner_type,
            "soma_side": "",  # No soma side for combined entry
            "weight": 0,
            "connections_per_neuron": 0,
            "coefficient_of_variation": 0,  # Will be calculated from combined data
            "percentage": 0,  # Will be recalculated later
            "neurotransmitter": "Unknown",
            "partner_neuron_count": 0,
        }

        # Track neurotransmitters by weight to find most common
        nt_weights = defaultdict(int)
        # Track all CVs weighted by partner neuron count for combined CV calculation
        cv_data = []

        # Combine weights and track neurotransmitters
        for partner in partners:
            weight = partner.get("weight", 0)
            combined["weight"] += weight
            combined["connections_per_neuron"] += partner.get(
                "connections_per_neuron", 0
            )
            combined["partner_neuron_count"] += partner.get("partner_neuron_count", 0)

            # Collect CV data weighted by partner count
            cv = partner.get("coefficient_of_variation", 0)
            partner_count = partner.get("partner_neuron_count", 0)
            if partner_count > 0:
                cv_data.append((cv, partner_count))

            nt = partner.get("neurotransmitter", "Unknown")
            nt_weights[nt] += weight

        # Set most common neurotransmitter (by weight)
        if nt_weights:
            combined["neurotransmitter"] = max(nt_weights.items(), key=lambda x: x[1])[
                0
            ]

        # Calculate combined coefficient of variation (weighted average)
        if cv_data:
            total_weight_for_cv = sum(count for _, count in cv_data)
            if total_weight_for_cv > 0:
                weighted_cv = (
                    sum(cv * count for cv, count in cv_data) / total_weight_for_cv
                )
                combined["coefficient_of_variation"] = round(weighted_cv, 3)
            else:
                combined["coefficient_of_variation"] = 0
        else:
            combined["coefficient_of_variation"] = 0

        logger.debug(
            f"Combined {len(partners)} entries for {partner_type}: "
            f"total weight={combined['weight']}, NT={combined['neurotransmitter']}, "
            f"CV={combined['coefficient_of_variation']}"
        )

        return combined

    def _recalculate_percentages(self, partners: List[Dict[str, Any]]) -> None:
        """
        Recalculate percentages based on combined weights.

        Args:
            partners: List of partner dictionaries to update
        """
        if not partners:
            return

        total_weight = sum(partner.get("weight", 0) for partner in partners)

        if total_weight == 0:
            return

        for partner in partners:
            weight = partner.get("weight", 0)
            percentage = (weight / total_weight * 100) if total_weight > 0 else 0
            partner["percentage"] = percentage

    def get_combined_body_ids(
        self,
        partner_data: Dict[str, Any],
        direction: str,
        connected_bids: Dict[str, Any],
    ) -> List[Any]:
        """
        Get body IDs for combined entries, including both L and R sides.

        This method is used by the partner analysis service to get body IDs
        when a combined entry is selected in the connectivity table.

        Args:
            partner_data: Partner data dictionary with type information
            direction: Connection direction ("upstream" or "downstream")
            connected_bids: Full connected body IDs mapping

        Returns:
            List of body IDs from both L and R sides combined
        """
        if not connected_bids or direction not in connected_bids:
            return []

        partner_type = partner_data.get("type", "")
        if not partner_type:
            return []

        dmap = connected_bids[direction] or {}
        body_ids = []

        # Collect body IDs from both L and R sides
        for side in ["L", "R"]:
            side_key = f"{partner_type}_{side}"
            side_ids = dmap.get(side_key, [])

            if isinstance(side_ids, list):
                body_ids.extend(side_ids)
            elif side_ids:
                body_ids.append(side_ids)

        # Also check for bare type entry
        bare_key = partner_type
        bare_ids = dmap.get(bare_key, [])

        if isinstance(bare_ids, dict):
            # Handle nested dictionary with side information
            for side_key, side_vals in bare_ids.items():
                if isinstance(side_vals, list):
                    body_ids.extend(side_vals)
                elif side_vals:
                    body_ids.append(side_vals)
        elif isinstance(bare_ids, list):
            body_ids.extend(bare_ids)
        elif bare_ids:
            body_ids.append(bare_ids)

        # Remove duplicates while preserving order
        return self._unique_preserving_order(body_ids)

    def _unique_preserving_order(self, sequence: List[Any]) -> List[Any]:
        """
        Remove duplicates from a sequence while preserving order.

        Args:
            sequence: Input sequence with potential duplicates

        Returns:
            List with duplicates removed, order preserved
        """
        if not sequence:
            return []

        seen = set()
        result = []

        for item in sequence:
            # Use string representation for comparison
            str_item = str(item)
            if str_item not in seen:
                seen.add(str_item)
                result.append(item)

        return result

    def is_combined_entry(self, partner_data: Dict[str, Any]) -> bool:
        """
        Check if a partner entry represents a combined L/R entry.

        Args:
            partner_data: Partner data dictionary

        Returns:
            True if this is a combined entry (no soma_side or empty soma_side)
        """
        soma_side = partner_data.get("soma_side", "")
        return not soma_side or soma_side == ""

    def get_statistics(
        self, original_data: Dict[str, Any], combined_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get statistics about the combination process.

        Args:
            original_data: Original connectivity data
            combined_data: Combined connectivity data

        Returns:
            Dictionary with combination statistics
        """

        def count_partners(data):
            upstream = len(data.get("upstream", []))
            downstream = len(data.get("downstream", []))
            return {
                "upstream": upstream,
                "downstream": downstream,
                "total": upstream + downstream,
            }

        original_counts = count_partners(original_data)
        combined_counts = count_partners(combined_data)

        return {
            "original_partners": original_counts,
            "combined_partners": combined_counts,
            "reduction": {
                "upstream": original_counts["upstream"] - combined_counts["upstream"],
                "downstream": original_counts["downstream"]
                - combined_counts["downstream"],
                "total": original_counts["total"] - combined_counts["total"],
            },
        }
