"""
Index Generator Service

Generates various index and helper pages including JavaScript search files,
README documentation, help pages, and landing pages.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IndexGeneratorService:
    """Service for generating various index and helper pages."""

    def __init__(self, page_generator):
        self.page_generator = page_generator

    async def generate_neuron_search_js(
        self, output_dir: Path, neuron_data: List[Dict[str, Any]], generation_time
    ) -> Optional[str]:
        """
        Generate neuron search files: neuron-search.js, neurons.json, and neurons.js fallback.

        Returns:
            Path to the generated neuron-search.js file, or None if generation failed
        """
        # Prepare neuron types data for JavaScript
        neuron_types_for_js = []

        for neuron in neuron_data:
            # Helper function to remove "types/" prefix from URLs
            def strip_types_prefix(url):
                if url and url.startswith("types/"):
                    return url[6:]  # Remove "types/" prefix
                return url

            # Create an entry with the neuron name and available URLs
            neuron_entry = {
                "name": neuron["name"],
                "urls": {},
            }

            # Add available URLs for this neuron type (without "types/" prefix)
            if neuron.get("combined_url") or neuron.get("both_url"):
                combined_url = neuron.get("combined_url") or neuron.get("both_url")
                neuron_entry["urls"]["combined"] = strip_types_prefix(combined_url)
            if neuron["left_url"]:
                neuron_entry["urls"]["left"] = strip_types_prefix(neuron["left_url"])
            if neuron["right_url"]:
                neuron_entry["urls"]["right"] = strip_types_prefix(neuron["right_url"])
            if neuron["middle_url"]:
                neuron_entry["urls"]["middle"] = strip_types_prefix(
                    neuron["middle_url"]
                )

            # Build types dictionary with flywire and synonyms
            types_dict = {}

            # Add FlyWire types
            if neuron.get("flywire_types"):
                flywire_value = neuron.get("flywire_types")
                # Split by comma if multiple values
                if isinstance(flywire_value, str):
                    flywire_list = [
                        t.strip() for t in flywire_value.split(",") if t.strip()
                    ]
                    if flywire_list:
                        types_dict["flywire"] = flywire_list
                elif isinstance(flywire_value, list):
                    types_dict["flywire"] = flywire_value

            # Add synonyms
            if neuron.get("synonyms"):
                synonyms_value = neuron.get("synonyms")
                # Parse synonyms (format: "Author Year: name; Author Year: name")
                if isinstance(synonyms_value, str):
                    synonym_list = [
                        s.strip() for s in synonyms_value.split(";") if s.strip()
                    ]
                    if synonym_list:
                        types_dict["synonyms"] = synonym_list
                elif isinstance(synonyms_value, list):
                    types_dict["synonyms"] = synonyms_value

            # Only add types field if it has content
            if types_dict:
                neuron_entry["types"] = types_dict

            neuron_types_for_js.append(neuron_entry)

        # Sort neuron types alphabetically
        neuron_types_for_js.sort(key=lambda x: x["name"])

        # Extract just the names for the simple search functionality
        neuron_names = [neuron["name"] for neuron in neuron_types_for_js]

        # Prepare timestamp
        timestamp = (
            generation_time.strftime("%Y-%m-%d %H:%M:%S")
            if generation_time
            else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # Prepare data structure for JSON and JS fallback
        data_structure = {
            "names": neuron_names,
            "neurons": neuron_types_for_js,
            "metadata": {
                "generated": timestamp,
                "total_types": len(neuron_names),
                "version": "2.0",
            },
        }

        # Ensure data directory exists
        data_dir = output_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        # 1. Generate neurons.json (for external services & web servers)
        try:
            json_path = data_dir / "neurons.json"
            json_path.write_text(
                json.dumps(data_structure, separators=(",", ":"), ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info(f"Generated neurons.json at {json_path}")
        except Exception as e:
            logger.error(f"Failed to generate neurons.json: {e}")

        # 2. Generate neurons.js (fallback for CORS-restricted environments)
        try:
            js_fallback_template = self.page_generator.env.get_template(
                "data/neurons.js.jinja"
            )
            js_fallback_content = js_fallback_template.render(
                {
                    "neuron_data": data_structure,
                    "neuron_data_json": json.dumps(
                        data_structure, indent=2, ensure_ascii=False
                    ),
                    "generation_timestamp": timestamp,
                }
            )

            js_fallback_path = data_dir / "neurons.js"
            js_fallback_path.write_text(js_fallback_content, encoding="utf-8")
            logger.info(f"Generated neurons.js fallback at {js_fallback_path}")
        except Exception as e:
            logger.error(f"Failed to generate neurons.js: {e}")

        # 3. Generate neuron-search.js (search logic only, no embedded data)
        try:
            # Prepare template data
            js_template_data = {
                "neuron_types_json": json.dumps(neuron_names, indent=2),
                "neuron_types_data_json": json.dumps(neuron_types_for_js, indent=2),
                "generation_timestamp": timestamp,
                "neuron_types": neuron_types_for_js,
            }

            # Load and render the neuron-search.js template
            js_template = self.page_generator.env.get_template(
                "static/js/neuron-search.js.jinja"
            )
            js_content = js_template.render(js_template_data)

            # Ensure static/js directory exists
            js_dir = output_dir / "static" / "js"
            js_dir.mkdir(parents=True, exist_ok=True)

            # Write the neuron-search.js file
            js_path = js_dir / "neuron-search.js"
            js_path.write_text(js_content, encoding="utf-8")
            logger.info(f"Generated neuron-search.js at {js_path}")
            return str(js_path)
        except Exception as e:
            logger.error(f"Failed to generate neuron-search.js: {e}")
            return None

    async def generate_readme(
        self, output_dir: Path, template_data: Dict[str, Any]
    ) -> Optional[str]:
        """Generate README.md documentation for the generated website."""
        try:
            # Load the README template
            readme_template = self.page_generator.env.get_template("README.md.jinja")
            readme_content = readme_template.render(template_data)

            # Write the README.md file
            readme_path = output_dir / "README.md"
            readme_path.write_text(readme_content, encoding="utf-8")

            logger.info(f"Generated README.md documentation at {readme_path}")
            return str(readme_path)

        except Exception as e:
            logger.warning(f"Failed to generate README.md: {e}")
            return None

    async def generate_help_page(
        self, output_dir: Path, template_data: Dict[str, Any], uncompress: bool = False
    ) -> Optional[str]:
        """Generate the help.html page."""
        try:
            # Load the help template
            help_template = self.page_generator.env.get_template("help.html.jinja")
            help_content = help_template.render(template_data)

            # Minify HTML content to reduce whitespace if not in uncompress mode
            if not uncompress:
                help_content = self.page_generator.html_utils.minify_html(
                    help_content, minify_js=False
                )

            # Write the help.html file
            help_path = output_dir / "help.html"
            help_path.write_text(help_content, encoding="utf-8")

            logger.info(f"Generated help.html page at {help_path}")
            return str(help_path)

        except Exception as e:
            logger.warning(f"Failed to generate help.html: {e}")
            return None

    async def generate_index_page(
        self, output_dir: Path, template_data: Dict[str, Any], uncompress: bool = False
    ) -> Optional[str]:
        """Generate the index.html landing page."""
        try:
            # Load the index template
            index_template = self.page_generator.env.get_template("index.html.jinja")
            index_content = index_template.render(template_data)

            # Minify HTML content to reduce whitespace if not in uncompress mode
            if not uncompress:
                index_content = self.page_generator.html_utils.minify_html(
                    index_content, minify_js=False
                )

            # Write the index.html file
            index_path = output_dir / "index.html"
            index_path.write_text(index_content, encoding="utf-8")

            logger.info(f"Generated index.html landing page at {index_path}")
            return str(index_path)

        except Exception as e:
            logger.warning(f"Failed to generate index.html: {e}")
            return None

    def calculate_totals(
        self, index_data: List[Dict[str, Any]], cached_data_lazy=None
    ) -> Dict[str, int]:
        """Calculate total neurons and synapses across all types."""
        total_neurons = sum(entry.get("total_count", 0) for entry in index_data)
        total_synapses = 0

        # Calculate total synapses from cached synapse stats
        if cached_data_lazy:
            for entry in index_data:
                entry_name = entry.get("name")
                if entry_name and entry_name in cached_data_lazy:
                    cache_entry = cached_data_lazy[entry_name]
                    if (
                        cache_entry
                        and hasattr(cache_entry, "synapse_stats")
                        and cache_entry.synapse_stats
                    ):
                        # Try to get avg_total, fallback to calculating it from avg_pre + avg_post
                        avg_total = cache_entry.synapse_stats.get("avg_total", 0)
                        if avg_total == 0:
                            avg_pre = cache_entry.synapse_stats.get("avg_pre", 0)
                            avg_post = cache_entry.synapse_stats.get("avg_post", 0)
                            avg_total = avg_pre + avg_post

                        neuron_count = entry.get("total_count", 0)
                        if avg_total > 0 and neuron_count > 0:
                            total_synapses += int(avg_total * neuron_count)

        return {"total_neurons": total_neurons, "total_synapses": total_synapses}

    def get_database_metadata(self, connector) -> Dict[str, str]:
        """Get database metadata including lastDatabaseEdit."""
        metadata = {}
        try:
            db_metadata = connector.get_database_metadata()
            logger.debug(f"Database metadata retrieved: {db_metadata}")
            metadata = {
                "version": db_metadata.get("uuid", "Unknown"),
                "uuid": db_metadata.get("uuid", "Unknown"),
                "lastDatabaseEdit": db_metadata.get("lastDatabaseEdit", "Unknown"),
            }
            logger.debug(f"Final metadata for template: {metadata}")
        except Exception as e:
            logger.warning(f"Failed to get database metadata: {e}")
            metadata = {
                "version": "Unknown",
                "uuid": "Unknown",
                "lastDatabaseEdit": "Unknown",
            }

        return metadata
