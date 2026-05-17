"""
Citation data service for handling citation information and URL generation.

This service manages the loading of citation data from CSV files and provides
functionality for creating citation links and managing citation metadata.
"""

from pathlib import Path
import csv
import io
import logging
from typing import Dict, Tuple, Optional, List

from ..utils import get_input_dir

logger = logging.getLogger(__name__)


class CitationService:
    """
    Service for managing citation data and generating citation links.

    This service handles:
    - Loading citation mappings from CSV files
    - Converting DOI references to full URLs
    - Managing citation metadata (URLs and titles)
    - Caching citation data for performance
    """

    def __init__(self):
        """
        Initialize the citation service.
        """
        self.citations: Dict[str, Tuple[str, str]] = {}
        self._loaded = False
        self._citation_logger = None

    def _setup_citation_logger(self, output_dir: str):
        """Set up a dedicated logger for missing citations."""
        if self._citation_logger is not None:
            return self._citation_logger

        import logging.handlers

        # Create log directory
        log_dir = Path(output_dir) / ".log"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create dedicated logger for citations
        citation_logger = logging.getLogger("neuview.missing_citations")
        citation_logger.setLevel(logging.WARNING)
        citation_logger.propagate = False  # Don't propagate to parent loggers

        # Remove existing handlers
        for handler in citation_logger.handlers[:]:
            citation_logger.removeHandler(handler)

        # File handler for missing citations
        log_file = log_dir / "missing_citations.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.WARNING)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        citation_logger.addHandler(file_handler)

        self._citation_logger = citation_logger
        return citation_logger

    def load_citations(self) -> Dict[str, Tuple[str, str]]:
        """
        Load citations data from CSV file.

        The CSV file should have format: citation,url,title
        Handles commas in titles by using proper CSV parsing.

        Returns:
            Dictionary mapping citation keys to (url, title) tuples

        Raises:
            FileNotFoundError: If citations file cannot be found
            ValueError: If CSV format is invalid
        """
        if self._loaded:
            return self.citations

        try:
            # Get the input directory
            citations_file = get_input_dir() / "citations.csv"

            if not citations_file.exists():
                logger.warning(f"Citations file not found: {citations_file}")
                self.citations = {}
                self._loaded = True
                return self.citations

            # Load CSV with proper handling of commas in citations
            citations_dict = {}

            with open(citations_file, "r", encoding="utf-8") as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    try:
                        # Use CSV reader to properly handle quoted fields
                        reader = csv.reader(io.StringIO(line))
                        row = next(reader)

                        if len(row) < 2:
                            logger.warning(
                                f"Insufficient columns in citations file at line {line_num}: {line}"
                            )
                            continue

                        citation = row[0].strip()
                        url = row[1].strip()
                        title = row[2].strip().strip('"') if len(row) >= 3 else ""

                        if not citation or not url:
                            logger.warning(
                                f"Empty citation or URL at line {line_num}: {line}"
                            )
                            continue

                        # Convert DOI to full URL if it starts with "10."
                        if url.startswith("10."):
                            url = f"https://doi.org/{url}"

                        # Store as tuple: (url, title)
                        citations_dict[citation] = (url, title)

                    except csv.Error as e:
                        logger.warning(f"CSV parsing error at line {line_num}: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing line {line_num}: {e}")
                        continue

            self.citations = citations_dict
            self._loaded = True

            logger.info(f"Loaded {len(self.citations)} citations from {citations_file}")
            return self.citations

        except NameError:
            # Re-raise NameError to indicate missing imports
            raise
        except Exception as e:
            logger.error(f"Error loading citations data: {e}")
            self.citations = {}
            self._loaded = True
            return self.citations

    def get_citations(self) -> Dict[str, Tuple[str, str]]:
        """
        Get the loaded citations dictionary.

        Loads citations if not already loaded.

        Returns:
            Dictionary mapping citation keys to (url, title) tuples
        """
        if not self._loaded:
            self.load_citations()
        return self.citations.copy()

    def get_citation(self, citation_key: str) -> Optional[Tuple[str, str]]:
        """
        Get citation information for a specific citation key.

        Args:
            citation_key: The citation identifier

        Returns:
            Tuple of (url, title) if found, None otherwise
        """
        if not self._loaded:
            self.load_citations()
        return self.citations.get(citation_key)



    def format_doi_url(self, doi: str) -> str:
        """
        Convert a DOI string to a full URL.

        Args:
            doi: DOI identifier (with or without "https://doi.org/" prefix)

        Returns:
            Full DOI URL

        Examples:
            >>> service.format_doi_url("10.1234/example")
            "https://doi.org/10.1234/example"

            >>> service.format_doi_url("https://doi.org/10.1234/example")
            "https://doi.org/10.1234/example"
        """
        if not doi:
            return ""

        doi = doi.strip()

        # If already a full URL, return as-is
        if doi.startswith("https://doi.org/"):
            return doi

        # If starts with "10.", add the DOI URL prefix
        if doi.startswith("10."):
            return f"https://doi.org/{doi}"

        # Otherwise, return as-is (might be another type of URL)
        return doi

    def create_citation_link(
        self,
        citation_key: str,
        link_text: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> str:
        """
        Create an HTML link for a citation.

        Args:
            citation_key: The citation identifier
            link_text: Optional custom link text (defaults to citation_key)
            output_dir: Optional output directory for citation logging

        Returns:
            HTML anchor tag or plain text if citation not found

        Examples:
            >>> service.create_citation_link("Smith2023")
            '<a href="https://doi.org/10.1234/example" title="Example Paper">Smith2023</a>'
        """
        citation_data = self.get_citation(citation_key)

        if not citation_data:
            logger.debug(f"Citation not found: {citation_key}")

            # Log to dedicated citation log file if output_dir provided
            if output_dir:
                citation_logger = self._setup_citation_logger(output_dir)
                citation_logger.warning(
                    f"Missing citation '{citation_key}' in create_citation_link"
                )

            return link_text or citation_key

        url, title = citation_data
        display_text = link_text or citation_key

        # Escape HTML characters in title and text
        escaped_title = (
            title.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

        escaped_text = (
            display_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

        # Create HTML link with title attribute
        if title:
            return f'<a href="{url}" title="{escaped_title}" target="_blank" rel="noopener">{escaped_text}</a>'
        else:
            return f'<a href="{url}" target="_blank" rel="noopener">{escaped_text}</a>'

    def get_all_citation_keys(self) -> List[str]:
        """
        Get all available citation keys.

        Returns:
            List of citation keys sorted alphabetically
        """
        if not self._loaded:
            self.load_citations()
        return sorted(self.citations.keys())

    def reload_citations(self) -> Dict[str, Tuple[str, str]]:
        """
        Force reload of citations data from file.

        This method clears the cache and reloads the data, useful for
        testing or when the source file has been updated.

        Returns:
            Dictionary mapping citation keys to (url, title) tuples
        """
        self._loaded = False
        self.citations.clear()
        return self.load_citations()

    def add_citation(self, citation_key: str, url: str, title: str = "") -> None:
        """
        Add or update a citation mapping.

        This method allows runtime addition of citation mappings,
        useful for testing or dynamic configuration.

        Args:
            citation_key: The citation identifier
            url: The citation URL
            title: Optional title for the citation
        """
        if not self._loaded:
            self.load_citations()

        # Convert DOI format if needed
        formatted_url = self.format_doi_url(url)
        self.citations[citation_key] = (formatted_url, title)
        logger.debug(f"Added citation: {citation_key} -> {formatted_url}")

    def __len__(self) -> int:
        """Return the number of loaded citations."""
        if not self._loaded:
            self.load_citations()
        return len(self.citations)

    def __contains__(self, citation_key: str) -> bool:
        """Check if a citation key exists in the citations data."""
        if not self._loaded:
            self.load_citations()
        return citation_key in self.citations
