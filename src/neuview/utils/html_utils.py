"""
HTML utilities module containing utility functions for HTML processing and generation.

This module extracts HTML-related functionality from the PageGenerator class
to improve code organization and reusability.
"""


class HTMLUtils:
    """Utility class for HTML-related operations."""

    @staticmethod
    def is_png_data(content: str) -> bool:
        """Check if content is a PNG data URL."""
        if isinstance(content, str):
            return content.startswith("data:image/png;base64,")
        return False

    @staticmethod
    def create_neuron_link(neuron_type: str, soma_side: str, queue_service=None) -> str:
        """Create HTML link to neuron type page based on type and soma side."""
        # Check if we should create a link (only if neuron type is in queue)
        if queue_service:
            cached_types = queue_service.get_cached_neuron_types()
            if neuron_type not in cached_types:
                # Return just the display text without a link
                soma_side_lbl = ""
                if soma_side:
                    soma_side_lbl = f" ({soma_side})"
                return f"{neuron_type}{soma_side_lbl}"

        # Clean neuron type name for filename
        clean_type = neuron_type.replace("/", "_").replace(" ", "_")

        # Handle different soma side formats with new naming scheme
        if soma_side in ["all", "combined", "center", "C", ""]:
            # General page for neuron type (multiple sides available)
            # FAFB "center" and "C" map to combined page
            filename = f"{clean_type}.html"
        else:
            # Specific page for single side
            soma_side_suffix = soma_side
            if soma_side_suffix == "left":
                soma_side_suffix = "L"
            elif soma_side_suffix == "right":
                soma_side_suffix = "R"
            elif soma_side_suffix == "middle":
                soma_side_suffix = "M"
            filename = f"{clean_type}_{soma_side_suffix}.html#s-c"

        # Create the display text - show (C) for center but link to combined page
        soma_side_lbl = ""
        if soma_side and soma_side not in ["all", "combined", "", None]:
            # Convert center to C for display, keep others as-is
            if soma_side in ["center", "C"]:
                soma_side_lbl = " (C)"
            else:
                soma_side_lbl = f" ({soma_side})"
        display_text = f"{neuron_type}{soma_side_lbl}"

        # Return HTML link
        return f'<a href="{filename}">{display_text}</a>'

    @staticmethod
    def minify_html(html_content: str, minify_js: bool = True) -> str:
        """
        Minify HTML content by removing unnecessary whitespace.

        Args:
            html_content: Raw HTML content to minify
            minify_js: Whether to minify JavaScript content within script tags

        Returns:
            Minified HTML content
        """
        import minify_html
        import re
        import logging

        logger = logging.getLogger(__name__)

        # Preserve <footer> verbatim — minify-html has no per-element opt-out
        # and we want the footer's source whitespace intact so the rendered
        # text stays human-diffable across builds.
        FOOTER_PLACEHOLDER = "__NEUVIEW_PRESERVE_FOOTER_PLACEHOLDER__"
        footer_match = re.search(
            r"<footer\b[^>]*>.*?</footer>",
            html_content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        preserved_footer = None
        if footer_match:
            preserved_footer = footer_match.group(0)
            html_content = (
                html_content[: footer_match.start()]
                + FOOTER_PLACEHOLDER
                + html_content[footer_match.end() :]
            )

        # LEGACY WORKAROUND: minify-js 0.6.0 has bugs with JavaScript control flow
        # This can be removed when upgrading to a newer version of minify-html
        # that doesn't use the problematic minify-js library
        if minify_js:
            # Quick check for JavaScript control flow that crashes minify-js
            script_pattern = r"<script[^>]*>(.*?)</script>"
            scripts = re.findall(
                script_pattern, html_content, re.DOTALL | re.IGNORECASE
            )

            for script_content in scripts:
                if script_content.strip() and any(
                    pattern in script_content
                    for pattern in [
                        "if (",
                        "if(",
                        "for (",
                        "for(",
                        "while (",
                        "while(",
                        "function ",
                        "switch (",
                        "switch(",
                        "try {",
                    ]
                ):
                    logger.debug(
                        "Disabling JS minification due to minify-js library limitations"
                    )
                    minify_js = False
                    break

        minified = minify_html.minify(
            html_content,
            minify_js=minify_js,
            minify_css=True,
            remove_processing_instructions=True,
        )

        if preserved_footer is not None:
            minified = minified.replace(FOOTER_PLACEHOLDER, preserved_footer, 1)

        return minified
