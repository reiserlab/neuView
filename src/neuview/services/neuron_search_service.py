"""
Neuron search service for generating JavaScript search functionality.

This service manages the generation of neuron-search.js files with embedded
neuron type data for client-side search functionality.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment

logger = logging.getLogger(__name__)


class NeuronSearchService:
    """
    Service for generating JavaScript neuron search files.

    This service handles:
    - Generation of neuron-search.js with embedded neuron types data
    - Template rendering for JavaScript content
    - JSON serialization of neuron data
    - File output management
    """

    def __init__(self, output_dir: Path, template_env: Environment, queue_service=None):
        """
        Initialize the neuron search service.

        Args:
            output_dir: Directory for generated files
            template_env: Jinja2 environment for template rendering
            queue_service: Optional service for getting queued neuron types
        """
        self.output_dir = Path(output_dir)
        self.template_env = template_env
        self.queue_service = queue_service

    def generate_neuron_search_js(self, force_regenerate: bool = False) -> bool:
        """
        Generate neuron-search.js with embedded neuron types data.

        Args:
            force_regenerate: If True, regenerate even if file exists

        Returns:
            True if file was generated, False if skipped or failed

        Raises:
            FileNotFoundError: If template file is not found
            PermissionError: If unable to write output file
        """
        output_js_file = self.output_dir / "static" / "js" / "neuron-search.js"

        # Check if file already exists and we're not forcing regeneration
        if output_js_file.exists() and not force_regenerate:
            logger.debug("neuron-search.js already exists, skipping generation")
            return False

        try:
            # Get neuron types from queue service if available
            neuron_types = self._get_neuron_types()

            # Load the template
            template_path = "static/js/neuron-search.js.jinja"

            if not self._template_exists(template_path):
                logger.warning(f"Neuron search template not found: {template_path}")
                return False

            # Generate JavaScript content
            js_content = self._render_template(template_path, neuron_types)

            # Write to output directory
            self._write_js_file(output_js_file, js_content)

            logger.info(
                f"Generated neuron-search.js with {len(neuron_types)} neuron types"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to generate neuron-search.js: {e}")
            return False

    def _get_neuron_types(self) -> List[str]:
        """
        Get sorted list of neuron types from queue service.

        Returns:
            Sorted list of neuron type names
        """
        neuron_types = []

        if self.queue_service:
            try:
                neuron_types = self.queue_service.get_cached_neuron_types()
            except Exception as e:
                logger.warning(f"Failed to get neuron types from queue service: {e}")

        # Ensure types are sorted for consistent output
        return sorted(neuron_types)

    def _template_exists(self, template_path: str) -> bool:
        """
        Check if the template file exists.

        Args:
            template_path: Relative path to template within template environment

        Returns:
            True if template exists, False otherwise
        """
        try:
            self.template_env.get_template(template_path)
            return True
        except Exception:
            return False

    def _render_template(self, template_path: str, neuron_types: List[str]) -> str:
        """
        Render the JavaScript template with neuron data.

        Args:
            template_path: Path to the template file
            neuron_types: List of neuron type names

        Returns:
            Rendered JavaScript content

        Raises:
            Exception: If template rendering fails
        """
        template = self.template_env.get_template(template_path)

        # Prepare template context
        context = {
            "neuron_types": neuron_types,
            "neuron_types_json": json.dumps(neuron_types, indent=2),
            "neuron_types_data_json": json.dumps(
                [], indent=2
            ),  # Placeholder for future data
            "generation_timestamp": datetime.now().isoformat(),
        }

        # Generate the JavaScript content
        js_content = template.render(**context)

        # Fix HTML entity encoding that Jinja2 applies to JSON
        js_content = self._fix_html_entities(js_content)

        return js_content

    def _fix_html_entities(self, content: str) -> str:
        """
        Fix HTML entity encoding in JavaScript content.

        Jinja2 auto-escaping can convert quotes to HTML entities,
        which breaks JavaScript syntax.

        Args:
            content: JavaScript content with potential HTML entities

        Returns:
            JavaScript content with fixed entities
        """
        # Replace common HTML entities that break JavaScript
        replacements = {
            "&#34;": '"',
            "&quot;": '"',
            "&#39;": "'",
            "&apos;": "'",
            "&lt;": "<",
            "&gt;": ">",
            "&amp;": "&",
        }

        for entity, replacement in replacements.items():
            content = content.replace(entity, replacement)

        return content

    def _write_js_file(self, output_path: Path, content: str) -> None:
        """
        Write JavaScript content to file.

        Args:
            output_path: Path where file should be written
            content: JavaScript content to write

        Raises:
            PermissionError: If unable to write to output path
            OSError: If directory creation fails
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.debug(f"Written neuron search JavaScript to: {output_path}")

    def get_output_path(self) -> Path:
        """
        Get the output path for the neuron search JavaScript file.

        Returns:
            Path object for the output file
        """
        return self.output_dir / "static" / "js" / "neuron-search.js"

    def generate_with_custom_data(
        self,
        neuron_data: List[Dict[str, Any]],
        output_filename: Optional[str] = None,
        template_vars: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Generate neuron search file with custom neuron data.

        This method allows for more flexible generation with custom
        neuron data structures and additional template variables.

        Args:
            neuron_data: List of neuron data dictionaries
            output_filename: Optional custom output filename
            template_vars: Optional additional template variables

        Returns:
            True if generation successful, False otherwise
        """
        try:
            # Extract neuron types from data
            neuron_types = []
            for item in neuron_data:
                if isinstance(item, dict) and "type" in item:
                    neuron_types.append(item["type"])
                elif isinstance(item, str):
                    neuron_types.append(item)

            neuron_types = sorted(set(neuron_types))

            # Determine output path
            if output_filename:
                output_path = self.output_dir / "static" / "js" / output_filename
            else:
                output_path = self.get_output_path()

            # Prepare template context
            context = {
                "neuron_types": neuron_types,
                "neuron_types_json": json.dumps(neuron_types, indent=2),
                "neuron_types_data_json": json.dumps(neuron_data, indent=2),
                "generation_timestamp": datetime.now().isoformat(),
            }

            # Add custom template variables
            if template_vars:
                context.update(template_vars)

            # Load and render template
            template_path = "static/js/neuron-search.js.jinja"

            if not self._template_exists(template_path):
                logger.error(f"Template not found: {template_path}")
                return False

            template = self.template_env.get_template(template_path)
            js_content = template.render(**context)
            js_content = self._fix_html_entities(js_content)

            # Write to file
            self._write_js_file(output_path, js_content)

            logger.info(f"Generated custom neuron search file: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate custom neuron search file: {e}")
            return False

    def cleanup_output_file(self) -> bool:
        """
        Remove the generated neuron search JavaScript file.

        Returns:
            True if file was removed or didn't exist, False if removal failed
        """
        try:
            output_path = self.get_output_path()
            if output_path.exists():
                output_path.unlink()
                logger.debug(f"Removed neuron search file: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove neuron search file: {e}")
            return False
