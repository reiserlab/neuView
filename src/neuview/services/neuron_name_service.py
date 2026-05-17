"""
Neuron Name Service

Handles neuron name to filename conversion, reverse lookup, and database fallback logic.
"""

import logging
import re

logger = logging.getLogger(__name__)


class NeuronNameService:
    """Service for managing neuron name to filename conversion and reverse lookup."""

    def __init__(self, cache_manager=None):
        self.cache_manager = cache_manager

    def neuron_name_to_filename(self, neuron_name: str) -> str:
        """Convert neuron name to filename format (same logic as PageGenerator._generate_filename)."""
        return neuron_name.replace("/", "_").replace(" ", "_")


    def filename_to_neuron_name(self, filename: str, connector=None) -> str:
        """Convert filename back to original neuron name using database lookup."""
        # Since filename conversion is not reliably reversible ('/' and ' ' become '_'),
        # we use a database lookup approach to find the correct neuron name

        if not connector:
            # Fallback to simple heuristic if no connector available
            return self._filename_to_neuron_name_heuristic(filename)

        try:
            # First, try the filename as-is (case where neuron name has no spaces/slashes)
            test_names = [filename]

            # Generate possible original names by trying different combinations of
            # replacing underscores with spaces and slashes

            # Handle special case: "Word._Word" -> "Word. Word"
            if re.search(r"\w+\._\w+", filename):
                test_names.append(re.sub(r"(\w+)\._(\w+)", r"\1. \2", filename))

            # Try replacing all underscores with spaces
            if "_" in filename:
                test_names.append(filename.replace("_", " "))

            # Try combinations of slashes and spaces
            if "_" in filename:
                # Replace first underscore with slash, rest with spaces
                parts = filename.split("_")
                if len(parts) >= 2:
                    test_names.append(parts[0] + "/" + " ".join(parts[1:]))

                # Try replacing some underscores with slashes (for cases like "A/B C")
                for i in range(1, len(parts)):
                    # Try slash at position i, spaces elsewhere
                    result_parts = parts.copy()
                    test_name = (
                        "/".join(result_parts[: i + 1])
                        + " "
                        + " ".join(result_parts[i + 1 :])
                    )
                    test_names.append(test_name.strip())

            # Test each candidate name against the database
            for candidate_name in test_names:
                if not candidate_name.strip():
                    continue

                try:
                    # Quick test: try to fetch neuron data for this name
                    neuron_data = connector.get_neuron_data(
                        candidate_name, soma_side="combined"
                    )
                    if neuron_data and neuron_data.get("neurons") is not None:
                        neurons_df = neuron_data["neurons"]
                        if not neurons_df.empty:
                            # Found a match!
                            return candidate_name
                except Exception:
                    # This candidate doesn't exist, try next one
                    continue

            # If no database match found, fall back to heuristic
            return self._filename_to_neuron_name_heuristic(filename)

        except Exception as e:
            # If anything goes wrong, fall back to heuristic
            logger.debug(f"Database lookup failed for filename '{filename}': {e}")
            return self._filename_to_neuron_name_heuristic(filename)

    def _filename_to_neuron_name_heuristic(self, filename: str) -> str:
        """Heuristic fallback for filename to neuron name conversion."""
        # Handle the "Tergotr._MN" -> "Tergotr. MN" pattern
        dot_underscore_pattern = r"(\w+)\._(\w+)"
        if re.search(dot_underscore_pattern, filename):
            # Replace the first ._  with '. ' (dot space)
            result = re.sub(r"(\w+)\._(\w+)", r"\1. \2", filename)
            # Replace remaining underscores with spaces
            return result.replace("_", " ")

        # For names that already have underscores as part of the name (like PEN_b, AN05B054_a),
        # we need to be more careful. If the filename has no clear space markers,
        # assume underscores are part of the original name.

        # If filename contains parentheses or looks like a code, keep underscores
        if re.search(r"[()]|\w+\d+_[a-z]|\w+_[a-z]\(", filename):
            return filename

        # Otherwise, replace underscores with spaces
        return filename.replace("_", " ")

    def build_filename_to_neuron_map(self, cached_data_lazy):
        """Build a reverse lookup map for efficient filename-to-neuron-name mapping."""
        filename_to_neuron_map = {}
        if cached_data_lazy:
            for neuron_type in cached_data_lazy.keys():
                cache_data = cached_data_lazy.get(neuron_type)
                if cache_data and cache_data.original_neuron_name:
                    generated_filename = self.neuron_name_to_filename(
                        cache_data.original_neuron_name
                    )
                    filename_to_neuron_map[generated_filename] = (
                        cache_data.original_neuron_name
                    )
        return filename_to_neuron_map
