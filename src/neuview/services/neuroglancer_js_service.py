"""
Neuroglancer JavaScript Generation Service for neuView.

This service generates the neuroglancer-url-generator.js file dynamically,
selecting the appropriate neuroglancer template based on the dataset configuration.
This replaces the static JavaScript file with a template-based approach.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from ..utils import atomic_write

logger = logging.getLogger(__name__)


class NeuroglancerJSService:
    """Service for generating neuroglancer JavaScript files with dynamic template selection."""

    def __init__(self, config, jinja_env):
        """Initialize the service.

        Args:
            config: Configuration object containing server and dataset settings
            jinja_env: Jinja2 environment for template rendering
        """
        self.config = config
        self.env = jinja_env

    def generate_neuroglancer_js(self, output_dir: Path) -> bool:
        """
        Generate the neuroglancer-url-generator.js file with the appropriate template.

        Args:
            output_dir: Base output directory

        Returns:
            True if generation successful, False otherwise
        """
        try:
            # Determine which neuroglancer template to use
            if "fafb" in self.config.neuprint.dataset.lower():
                template_name = "neuroglancer-fafb.js.jinja"
            else:
                template_name = "neuroglancer.js.jinja"

            logger.debug(
                f"Using Neuroglancer template: {template_name} for dataset: {self.config.neuprint.dataset}"
            )

            # Load the neuroglancer template
            neuroglancer_template = self.env.get_template(template_name)
            logger.debug(f"Successfully loaded neuroglancer template: {template_name}")

            # Render the template with placeholder values
            template_vars = {
                "website_title": "WEBSITE_TITLE_PLACEHOLDER",
                "visible_neurons": [],
                "neuron_query": "NEURON_QUERY_PLACEHOLDER",
                "visible_rois": [],
                "connected_bids": {"upstream": {}, "downstream": {}},
                "dataset_name": self.config.neuprint.dataset,
            }

            neuroglancer_json = neuroglancer_template.render(**template_vars)
            logger.debug(
                f"Rendered neuroglancer template, length: {len(neuroglancer_json)} chars"
            )

            # Validate neuroglancer JSON by parsing it
            try:
                json.loads(neuroglancer_json)
                logger.debug("Neuroglancer JSON validation successful")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid neuroglancer JSON: {e}")
                return False

            # Load the JavaScript template and render with the neuroglancer JSON as a string
            js_template = self.env.get_template(
                "static/js/neuroglancer-url-generator.js.jinja"
            )
            logger.debug("Successfully loaded JavaScript template")

            # Get ROI data from Jinja environment globals if available
            template_context = {
                "neuroglancer_json": neuroglancer_json,
                "dataset_name": self.config.neuprint.dataset,
                "neuroglancer_base_url": self.config.neuroglancer.base_url.rstrip("/"),
            }

            # Add ROI data from environment globals if they exist
            roi_globals = ["roi_ids", "all_rois", "vnc_ids", "vnc_names"]
            for roi_key in roi_globals:
                if roi_key in self.env.globals:
                    template_context[roi_key] = self.env.globals[roi_key]
                    logger.debug(f"Added ROI data '{roi_key}' to template context")

            # Generate the JavaScript content with the neuroglancer template embedded
            js_content = js_template.render(**template_context)
            logger.debug(
                f"Rendered JavaScript template, length: {len(js_content)} chars"
            )

            # Ensure output directory exists
            js_dir = output_dir / "static" / "js"
            js_dir.mkdir(parents=True, exist_ok=True)

            output_file = js_dir / "neuroglancer-url-generator.js"
            with atomic_write(output_file) as f:
                f.write(js_content)

            logger.info(f"Generated neuroglancer JavaScript file: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate neuroglancer JavaScript file: {e}")
            logger.debug(f"Exception type: {type(e)}")
            import traceback

            logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def get_neuroglancer_template_name(self) -> str:
        """
        Get the name of the neuroglancer template that would be used.

        Returns:
            Template name string
        """
        if "fafb" in self.config.neuprint.dataset.lower():
            return "neuroglancer-fafb.js.jinja"
        else:
            return "neuroglancer.js.jinja"

    def validate_templates(self) -> Dict[str, bool]:
        """
        Validate that required templates exist and are loadable.

        Returns:
            Dictionary mapping template names to their availability
        """
        results = {}

        # Check neuroglancer templates
        for template_name in ["neuroglancer.js.jinja", "neuroglancer-fafb.js.jinja"]:
            try:
                self.env.get_template(template_name)
                results[template_name] = True
            except Exception as e:
                logger.warning(f"Template {template_name} not available: {e}")
                results[template_name] = False

        # Check JavaScript template
        try:
            self.env.get_template("static/js/neuroglancer-url-generator.js.jinja")
            results["neuroglancer-url-generator.js.jinja"] = True
        except Exception as e:
            logger.warning(f"JavaScript template not available: {e}")
            results["neuroglancer-url-generator.js.jinja"] = False

        return results

    def get_template_info(self) -> Dict[str, Any]:
        """
        Get information about template selection and availability.

        Returns:
            Dictionary with template information
        """
        return {
            "dataset": self.config.neuprint.dataset,
            "selected_template": self.get_neuroglancer_template_name(),
            "template_validation": self.validate_templates(),
        }
