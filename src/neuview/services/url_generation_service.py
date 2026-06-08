"""
URL Generation Service for neuView.

This service handles URL generation logic that was previously part of the
PageGenerator class. It provides methods for generating Neuroglancer and
NeuPrint URLs with proper templating and error handling.
"""

import json
import urllib.parse
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class URLGenerationService:
    """Service for generating URLs for external tools like Neuroglancer and NeuPrint."""

    def __init__(
        self,
        config,
        jinja_env,
        neuron_selection_service=None,
        database_query_service=None,
    ):
        """Initialize URL generation service.

        Args:
            config: Configuration object containing server settings
            jinja_env: Jinja2 environment for template rendering
            neuron_selection_service: Service for neuron selection operations
            database_query_service: Service for database query operations
        """
        self.config = config
        self.env = jinja_env
        self.neuron_selection_service = neuron_selection_service
        self.database_query_service = database_query_service

    def generate_neuroglancer_url(
        self,
        neuron_type: str,
        neuron_data: Dict[str, Any],
        soma_side: Optional[str] = None,
        connector=None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate Neuroglancer URL from template with substituted variables.

        Args:
            neuron_type: The neuron type name
            neuron_data: Data containing neuron information including bodyIDs
            soma_side: Soma side filter ('left', 'right', 'combined', etc.)
            connector: NeuPrint connector instance

        Returns:
            Tuple of (URL-encoded Neuroglancer URL, template variables dict)
        """
        # Initialize variables to ensure they're defined in exception handler
        visible_rois = []
        conn_bids = {"upstream": {}, "downstream": {}}

        try:
            template_name = self.config.neuroglancer.template
            logger.debug(
                f"Using Neuroglancer template: {template_name} for dataset: {self.config.neuprint.dataset}"
            )
            neuroglancer_template = self.env.get_template(template_name)

            # Get bodyID(s) closest to 95th percentile of synapse count
            neurons_df = neuron_data.get("neurons")
            visible_neurons = []
            if neurons_df is not None and not neurons_df.empty:
                bodyids = (
                    neurons_df["bodyId"].tolist()
                    if "bodyId" in neurons_df.columns
                    else []
                )
                if bodyids and self.neuron_selection_service:
                    selected_bodyids = (
                        self.neuron_selection_service.select_bodyids_by_soma_side(
                            neuron_type, neurons_df, soma_side, 95
                        )
                    )
                    visible_neurons = [str(bodyid) for bodyid in selected_bodyids]

            # Get bodyIds of the top cell from each type that connected with the 'visible_neuron'
            if self.database_query_service:
                conn_bids = self.database_query_service.get_connected_bodyids(
                    [int(bid) for bid in visible_neurons], connector
                )

            # Prepare template variables
            template_vars = {
                "website_title": neuron_type,
                "visible_neurons": visible_neurons,
                "neuron_query": neuron_type,
                "visible_rois": visible_rois,
                "connected_bids": conn_bids,
            }

            # Render the template
            neuroglancer_json = neuroglancer_template.render(**template_vars)

            # Parse as JSON to validate and then convert back to string
            neuroglancer_state = json.loads(neuroglancer_json)
            neuroglancer_json_string = json.dumps(
                neuroglancer_state, separators=(",", ":")
            )

            # URL encode the JSON string
            encoded_state = urllib.parse.quote(neuroglancer_json_string, safe="")

            # Create the full Neuroglancer URL
            base_url = self.config.neuroglancer.base_url.rstrip("/")
            neuroglancer_url = f"{base_url}/#!{encoded_state}"

            return neuroglancer_url, template_vars

        except Exception as e:
            # Return a fallback URL if template processing fails
            logger.warning(
                f"Failed to generate Neuroglancer URL for {neuron_type}: {e}"
            )
            fallback_vars = {
                "website_title": neuron_type,
                "visible_neurons": [],
                "neuron_query": neuron_type,
                "visible_rois": visible_rois,
                "connected_bids": conn_bids,
            }
            base_url = self.config.neuroglancer.base_url.rstrip("/")
            return f"{base_url}/", fallback_vars

    def generate_neuprint_url(
        self, neuron_type: str, neuron_data: Dict[str, Any]
    ) -> str:
        """
        Generate NeuPrint URL from template with substituted variables.

        Args:
            neuron_type: The neuron type name
            neuron_data: Data containing neuron information

        Returns:
            NeuPrint URL for searching this neuron type
        """
        try:
            # Build NeuPrint URL with query parameters
            neuprint_url = (
                f"https://{self.config.neuprint.server}"
                f"/results?dataset={self.config.neuprint.dataset}"
                f"&qt=findneurons"
                f"&qr[0][code]=fn"
                f"&qr[0][ds]={self.config.neuprint.dataset}"
                f"&qr[0][pm][dataset]={self.config.neuprint.dataset}"
                f"&qr[0][pm][all_segments]=false"
                f"&qr[0][pm][enable_contains]=true"
                f"&qr[0][visProps][rowsPerPage]=50"
                f"&tab=0"
                f"&qr[0][pm][neuron_name]={urllib.parse.quote(neuron_type)}"
            )

            # Add soma side suffix if applicable
            if neuron_data.get("soma_side", None) in ["left", "right"]:
                soma_side = neuron_data.get("soma_side", "")
                neuprint_url += f"_{soma_side[:1].upper()}"

            return neuprint_url

        except Exception as e:
            # Return a fallback URL if URL generation fails
            logger.warning(f"Failed to generate NeuPrint URL for {neuron_type}: {e}")
            return f"https://{self.config.neuprint.server}/?dataset={self.config.neuprint.dataset}"






