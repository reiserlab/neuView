"""
Partner analysis service for handling partner body ID filtering and analysis.

This service manages the analysis of partner connectivity data, including
soma side filtering and body ID extraction from connectivity datasets.
"""

import logging
from typing import Dict, List, Union, Any, Optional

logger = logging.getLogger(__name__)

# Soma-side values that mean "no side assigned". Upstream sources sometimes
# emit "na", "U", "unknown", etc. instead of producing a missing value, so we
# treat them all the same as None and return all sides.
_NO_SIDE_MARKERS = frozenset({"", "na", "nan", "none", "null", "unknown", "u"})


class PartnerAnalysisService:
    """
    Service for analyzing partner connectivity data and extracting body IDs.

    This service handles:
    - Partner body ID extraction from connectivity data
    - Soma side filtering for partner neurons
    - De-duplication while preserving order
    - Handling of different data structures (lists, dicts, mixed)
    - Combined L/R entries for combined pages
    """

    def __init__(self, connectivity_combination_service=None):
        """
        Initialize the partner analysis service.

        Args:
            connectivity_combination_service: Service for handling L/R combination
        """
        self.connectivity_combination_service = connectivity_combination_service

    def get_partner_body_ids(
        self,
        partner_data: Union[Dict[str, Any], str],
        direction: str,
        connected_bids: Dict[str, Any],
    ) -> List[Any]:
        """
        Return a de-duplicated, order-preserving list of partner bodyIds for a given
        direction, optionally restricted to a soma side.

        Behavior:
        - If `partner_data` specifies a `soma_side` ('L' or 'R'), only bodyIds that
          match BOTH the partner `type` and that side are returned. The function looks
          first for keys like ``"{type}_L"`` or ``"{type}_R"`` under
          ``connected_bids[direction]``. If only a bare ``"{type}"`` key exists:
            * if its value is a dict (e.g., ``{'L': [...], 'R': [...]}``), the
              side-specific list is used;
            * if its value is a list (no side information), that list is returned
              as-is.
          If neither a side-specific nor a filterable bare entry is present, an
          empty list is returned.
        - If `soma_side` is missing/None, the result is the union of
          ``"{type}_L"``, ``"{type}_R"``, and the bare ``"{type}"`` entries (when present).

        Parameters:
        - partner_data (dict or str): Partner descriptor. When a dict, should contain:
            - ``'type'`` (str): partner cell type (e.g., "Dm4")
            - ``'soma_side'`` (optional, str): 'L' or 'R'
          When a str, it is treated as the partner type; side is assumed None.
        - direction ({'upstream', 'downstream'}): Which connectivity direction to use.
        - connected_bids (dict): Mapping with shape like:
            {
            'upstream':   { 'Dm4_L': [...], 'Dm4_R': [...], 'Dm4': [...](optional) },
            'downstream': { 'Dm4_L': [...], 'Dm4_R': [...], 'Dm4': [...](optional) }
            }
          Values may be lists (IDs), or for the bare type, optionally a dict
          keyed by side (e.g., ``{'L': [...], 'R': [...]}``).

        Returns:
        - list: A list of bodyIds (as provided by `connected_bids`), de-duplicated while
          preserving first-seen order. Returns an empty list if `direction` is
          absent or no matching entries are found.

        Notes:
        - Item types are not coerced; IDs are returned as stored (e.g., int/str).
          Callers may cast as needed.
        - When a side is explicitly requested but unavailable, the function prefers
          to return an empty list rather than mixing sides.
        - If `partner_data` lacks `soma_side`, all sides (and any bare entry) are
          merged for backward compatibility.
        """
        if not connected_bids or direction not in connected_bids:
            logger.debug(f"No connected body IDs found for direction: {direction}")
            return []

        # Extract partner name and soma side from partner data
        partner_name, soma_side = self._parse_partner_data(partner_data)

        # Check if this is a combined entry (no soma_side specified)
        if (
            self.connectivity_combination_service
            and isinstance(partner_data, dict)
            and self.connectivity_combination_service.is_combined_entry(partner_data)
        ):
            return self.connectivity_combination_service.get_combined_body_ids(
                partner_data, direction, connected_bids
            )

        dmap = connected_bids[direction] or {}

        # Handle soma side filtering
        if soma_side in ("L", "R", "M", "C", "center"):
            return self._get_side_specific_body_ids(partner_name, soma_side, dmap)
        normalized = (
            soma_side.strip().lower() if isinstance(soma_side, str) else soma_side
        )
        if soma_side is None or normalized in _NO_SIDE_MARKERS:
            return self._get_all_sides_body_ids(partner_name, dmap)
        logger.debug(f"Unrecognized soma side {soma_side!r}; returning all sides")
        return self._get_all_sides_body_ids(partner_name, dmap)

    def _parse_partner_data(
        self, partner_data: Union[Dict[str, Any], str]
    ) -> tuple[str, Optional[str]]:
        """
        Parse partner data to extract partner name and soma side.

        Args:
            partner_data: Either a dict with 'type' and optional 'soma_side' keys,
                         or a string representing the partner type

        Returns:
            Tuple of (partner_name, soma_side)
        """
        if isinstance(partner_data, dict):
            partner_name = partner_data.get("type", "Unknown")
            soma_side = partner_data.get("soma_side")
        else:
            # Fallback for string input
            partner_name = str(partner_data)
            soma_side = None

        return partner_name, soma_side

    def _get_side_specific_body_ids(
        self, partner_name: str, soma_side: str, dmap: Dict[str, Any]
    ) -> List[Any]:
        """
        Get body IDs for a specific soma side.

        Args:
            partner_name: Name of the partner type
            soma_side: Specific soma side ('L' or 'R')
            dmap: Direction mapping from connected_bids

        Returns:
            List of body IDs for the specified side
        """
        # First try side-specific key like "Dm4_L"
        side_specific_key = f"{partner_name}_{soma_side}"
        keyed = dmap.get(side_specific_key, [])

        if keyed:
            return self._unique_preserving_order(keyed)

        # Try bare type with side filtering
        bare = dmap.get(partner_name)

        if isinstance(bare, dict):
            # If keys contain side-specific lists (e.g., {'L': [...], 'R': [...]})
            candidate = (
                bare.get(soma_side) or bare.get(f"{partner_name}_{soma_side}") or []
            )
            return self._unique_preserving_order(
                candidate if isinstance(candidate, list) else [candidate]
            )

        if isinstance(bare, list):
            # No side info here; fall back to the bare list
            logger.debug(
                f"No side-specific data for {partner_name}_{soma_side}, using bare list"
            )
            return self._unique_preserving_order(bare)

        # Nothing side-specific; return empty rather than all-sides
        logger.debug(f"No data found for {partner_name}_{soma_side}")
        return []

    def _get_all_sides_body_ids(
        self, partner_name: str, dmap: Dict[str, Any]
    ) -> List[Any]:
        """
        Get body IDs for all sides (legacy behavior).

        Args:
            partner_name: Name of the partner type
            dmap: Direction mapping from connected_bids

        Returns:
            List of body IDs from all sides combined
        """
        vals = []

        # Check all possible side-specific keys and bare type
        for key in (
            f"{partner_name}_L",
            f"{partner_name}_R",
            f"{partner_name}_M",
            f"{partner_name}_C",
            f"{partner_name}_center",
            partner_name,
        ):
            value = dmap.get(key, [])

            if isinstance(value, list):
                vals.extend(value)
            elif isinstance(value, dict):
                # Handle nested dictionaries with side information
                for side_key, side_vals in value.items():
                    if isinstance(side_vals, list):
                        vals.extend(side_vals)
                    elif side_vals:
                        vals.append(side_vals)
            elif value:
                vals.append(value)

        return self._unique_preserving_order(vals)

    def _unique_preserving_order(self, sequence: List[Any]) -> List[Any]:
        """
        Remove duplicates from a sequence while preserving order.

        Uses string representation for comparison to handle mixed types.

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



