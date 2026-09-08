"""
ROI data service for fetching ROI information from Google Cloud Storage.

This service handles fetching ROI segment properties from GCS endpoints and
providing them as structured data for template rendering.

The GCS endpoints are not hardcoded. They are derived from the neuroglancer
state template that the site is configured to use: the ``segment_properties``
of the mesh source behind the ``brain-neuropils`` and ``vnc-neuropils`` layers
are the lists of ROI names and segment IDs that the ROI checkboxes need. Taking
them from the template guarantees that every checkbox maps to a segment the
layer can actually render.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jinja2
import requests
from filelock import FileLock

from ..utils import atomic_write

logger = logging.getLogger(__name__)

# Generous timeout for the cache critical section. The work inside is a single
# HTTP GET (bounded by self.timeout) plus a small JSON write; anything longer
# means a peer worker is stuck and we should fetch ourselves.
_CACHE_LOCK_TIMEOUT = 120

# Layer names in the neuroglancer template whose mesh source defines the ROI
# lists. The brain layer accepts a legacy name too; keep in sync with the
# lookup in templates/static/js/neuroglancer-url-generator.js.jinja.
BRAIN_NEUROPIL_LAYERS = ("brain-neuropils", "neuropils")
VNC_NEUROPIL_LAYERS = ("vnc-neuropils",)

_GCS_HTTP_PREFIX = "https://storage.googleapis.com/"
_PRECOMPUTED_PREFIX = "precomputed://"


class _NullUndefined(jinja2.Undefined):
    """Render unknown template variables as JSON ``null``.

    The neuroglancer templates are JSON with a handful of Jinja expressions.
    To read the static layer definitions we render them with placeholder
    values; any variable we did not anticipate must still yield valid JSON.
    """

    def __str__(self) -> str:
        return "null"


def roi_sources_from_template(template_path: Path) -> Dict[str, str]:
    """
    Read the mesh sources of all segmentation layers in a neuroglancer template.

    The template is rendered with placeholder values for its dynamic parts and
    parsed as JSON. Only layers of type ``segmentation`` whose source is a
    ``precomputed://gs://`` URL are returned.

    Args:
        template_path: Path to a ``neuroglancer-*.js.jinja`` state template

    Returns:
        Mapping of layer name to GCS path (``gs://bucket/path``), without the
        ``precomputed://`` scheme.

    Raises:
        OSError: If the template cannot be read
        jinja2.TemplateError: If the template cannot be rendered
        json.JSONDecodeError: If the rendered template is not valid JSON
    """
    text = Path(template_path).read_text(encoding="utf-8")
    env = jinja2.Environment(undefined=_NullUndefined, autoescape=False)
    rendered = env.from_string(text).render(
        website_title="", visible_neurons=[], neuron_query=""
    )
    state = json.loads(rendered)

    sources: Dict[str, str] = {}
    for layer in state.get("layers", []):
        if not isinstance(layer, dict) or layer.get("type") != "segmentation":
            continue
        source = layer.get("source")
        if isinstance(source, dict):
            source = source.get("url")
        if not isinstance(source, str) or not source.startswith(
            _PRECOMPUTED_PREFIX + "gs://"
        ):
            continue
        name = layer.get("name")
        if isinstance(name, str):
            sources[name] = source[len(_PRECOMPUTED_PREFIX) :]
    return sources


def _bare_source(gcs_source: str) -> str:
    """Drop a neuroglancer URL fragment (``#type=mesh``) and trailing slash."""
    return gcs_source.split("#", 1)[0].rstrip("/")


def segment_properties_url(gcs_source: str) -> str:
    """Turn ``gs://bucket/path`` into the HTTPS URL of its segment properties."""
    if not gcs_source.startswith("gs://"):
        raise ValueError(f"Expected a gs:// source, got {gcs_source!r}")
    return (
        _GCS_HTTP_PREFIX + _bare_source(gcs_source)[len("gs://") :]
    ) + "/segment_properties/info"


def cache_filename_for(gcs_source: str) -> str:
    """Cache file name for a GCS source, e.g. ``fullbrain-roi-v5.json``."""
    return _bare_source(gcs_source).rsplit("/", 1)[-1] + ".json"


def _is_not_found(error: Exception) -> bool:
    """True if ``error`` is an HTTP 404, i.e. the source has no such file."""
    response = getattr(error, "response", None)
    return getattr(response, "status_code", None) == 404


def _first_present(sources: Dict[str, str], names: Tuple[str, ...]) -> Optional[str]:
    for name in names:
        if name in sources:
            return sources[name]
    return None


class ROIDataService:
    """
    Service for fetching and managing ROI data from Google Cloud Storage.

    This service handles:
    - Deriving the ROI endpoints from the configured neuroglancer template
    - Fetching ROI segment properties from GCS endpoints
    - Caching ROI data in output/.cache/roi_data/ to avoid repeated network requests
    - Parsing and structuring ROI data for template use
    - Error handling and retry logic for network requests
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        timeout: int = 30,
        template_path: Optional[Path] = None,
    ):
        """
        Initialize the ROI data service.

        Args:
            output_dir: Output directory containing the cache subdirectory (cache will be at output_dir/.cache/roi_data/)
            timeout: Timeout for HTTP requests in seconds
            template_path: Neuroglancer state template to derive the ROI
                sources from. Without it, or if the template has no neuropil
                layers, the service returns empty ROI lists.
        """
        self.timeout = timeout
        if output_dir:
            self.cache_dir = Path(output_dir) / ".cache" / "roi_data"
        else:
            # Fallback to current working directory if no output_dir provided
            self.cache_dir = Path.cwd() / "output" / ".cache" / "roi_data"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # GCS sources of the neuropil layers, taken from the template so the
        # ROI name list always matches the meshes the layer can render.
        self.template_path = Path(template_path) if template_path else None
        self.fullbrain_roi_source: Optional[str] = None
        self.vnc_roi_source: Optional[str] = None
        if self.template_path is None:
            logger.warning(
                "ROIDataService created without a neuroglancer template; "
                "ROI lists will be empty"
            )
        else:
            try:
                sources = roi_sources_from_template(self.template_path)
            except Exception as e:
                logger.error(
                    f"Failed to read ROI sources from {self.template_path}: {e}"
                )
                sources = {}
            self.fullbrain_roi_source = _first_present(sources, BRAIN_NEUROPIL_LAYERS)
            self.vnc_roi_source = _first_present(sources, VNC_NEUROPIL_LAYERS)
            if self.fullbrain_roi_source is None:
                logger.info(
                    f"No {'/'.join(BRAIN_NEUROPIL_LAYERS)} layer in "
                    f"{self.template_path.name}; brain ROI list will be empty"
                )
            if self.vnc_roi_source is None:
                logger.info(
                    f"No {'/'.join(VNC_NEUROPIL_LAYERS)} layer in "
                    f"{self.template_path.name}; VNC ROI list will be empty"
                )

        # Cache for loaded data
        self._fullbrain_data = None
        self._vnc_data = None

    @property
    def fullbrain_roi_url(self) -> Optional[str]:
        """HTTPS URL of the brain neuropil segment properties, if any."""
        if self.fullbrain_roi_source is None:
            return None
        return segment_properties_url(self.fullbrain_roi_source)

    @property
    def vnc_roi_url(self) -> Optional[str]:
        """HTTPS URL of the VNC neuropil segment properties, if any."""
        if self.vnc_roi_source is None:
            return None
        return segment_properties_url(self.vnc_roi_source)

    def _load_roi_data(
        self, gcs_source: Optional[str], label: str
    ) -> Tuple[List[int], List[str]]:
        """Fetch and parse one ROI list, returning empty lists on any failure."""
        if gcs_source is None:
            return [], []
        try:
            raw_data = self._fetch_json_from_gcs(
                segment_properties_url(gcs_source), cache_filename_for(gcs_source)
            )
            return self._extract_roi_ids_and_names(raw_data)
        except Exception as e:
            if _is_not_found(e):
                # A mesh-only source (e.g. the FAFB neuropils) publishes no
                # segment properties; there is simply no ROI list to offer.
                logger.info(
                    f"{gcs_source} has no segment properties; {label} ROI list "
                    "will be empty"
                )
            else:
                logger.error(f"Failed to get {label} ROI data: {e}")
            # Return empty data rather than crashing
            return [], []

    def _fetch_json_from_gcs(self, url: str, cache_filename: str) -> Dict[str, Any]:
        """
        Fetch JSON data from a GCS URL with caching.

        Args:
            url: GCS URL to fetch from
            cache_filename: Filename for local cache roi_data

        Returns:
            Parsed JSON data

        Raises:
            requests.RequestException: If the HTTP request fails
            json.JSONDecodeError: If the response is not valid JSON
        """
        cache_file = self.cache_dir / cache_filename
        lock_file = cache_file.with_suffix(cache_file.suffix + ".lock")

        # Serialize the fetch across workers. The `pop-all` pixi task launches
        # many `neuview` invocations through GNU parallel, all of which try to
        # populate the same cache file at startup; without this only one
        # actually fetches from GCS and the rest wait for the result.
        with FileLock(str(lock_file), timeout=_CACHE_LOCK_TIMEOUT):
            # Try to load from cache first (cache for 1 hour)
            if cache_file.exists():
                cache_age = time.time() - cache_file.stat().st_mtime
                if cache_age < 3600:  # 1 hour cache
                    try:
                        with open(cache_file, "r") as f:
                            data = json.load(f)
                            logger.debug(
                                f"Loaded ROI data from cache: {cache_filename}"
                            )
                            return data
                    except (json.JSONDecodeError, OSError) as e:
                        logger.debug(
                            f"Cache file {cache_filename} unreadable, refetching: {e}"
                        )

            # Fetch from GCS
            logger.info(f"Fetching ROI data from: {url}")
            try:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()

                data = response.json()

                # Validate that we have actual data before caching
                if not data or (isinstance(data, dict) and not any(data.values())):
                    logger.warning(f"Received empty data from {url}, not caching")
                    raise ValueError("Empty data received from GCS endpoint")

                # Atomic write: temp file + rename, so concurrent readers
                # never observe a half-written cache file.
                try:
                    with atomic_write(cache_file) as f:
                        json.dump(data, f, indent=2)
                    logger.debug(f"Cached ROI data to: {cache_filename}")
                except OSError as e:
                    logger.warning(f"Failed to cache data to {cache_filename}: {e}")

                return data

            except requests.RequestException as e:
                if _is_not_found(e):
                    logger.debug(f"No ROI data at {url} (404)")
                else:
                    logger.error(f"Failed to fetch ROI data from {url}: {e}")

                # Try to use stale cache as fallback
                if cache_file.exists():
                    try:
                        with open(cache_file, "r") as f:
                            data = json.load(f)
                            logger.warning(
                                f"Using stale cache for {cache_filename} due to fetch failure"
                            )
                            return data
                    except (json.JSONDecodeError, OSError) as fallback_error:
                        logger.warning(
                            f"Stale cache file is also unreadable for {cache_filename}: {fallback_error}"
                        )

                raise

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response from {url}: {e}")
                raise

    def _extract_roi_ids_and_names(
        self, segment_data: Dict[str, Any]
    ) -> Tuple[List[int], List[str]]:
        """
        Extract ROI IDs and names from Neuroglancer segment properties data.

        Args:
            segment_data: Raw segment properties data from GCS

        Returns:
            Tuple of (roi_ids, roi_names)
        """
        ids = []
        names = []

        # Handle Neuroglancer segment properties format
        if (
            "@type" in segment_data
            and segment_data["@type"] == "neuroglancer_segment_properties"
        ):
            inline_data = segment_data.get("inline", {})

            # Extract IDs
            segment_ids = inline_data.get("ids", [])

            # Extract names from properties
            properties = inline_data.get("properties", [])
            source_property = None

            # Find the "source" property that contains the labels
            for prop in properties:
                if prop.get("id") == "source" and prop.get("type") == "label":
                    source_property = prop
                    break

            if source_property and "values" in source_property:
                segment_names = source_property["values"]

                # Ensure we have the same number of IDs and names
                min_length = min(len(segment_ids), len(segment_names))

                for i in range(min_length):
                    try:
                        roi_id = int(segment_ids[i])
                        roi_name = str(segment_names[i])
                        ids.append(roi_id)
                        names.append(roi_name)
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Could not parse ROI data at index {i}: {e}")

            # Sort by ID to ensure consistent ordering
            if ids and names:
                sorted_pairs = sorted(zip(ids, names), key=lambda x: x[0])
                ids, names = zip(*sorted_pairs)
                return list(ids), list(names)

        else:
            # Fallback to original parsing logic for other formats
            segments = segment_data.get("segments", [])

            for segment in segments:
                if isinstance(segment, dict):
                    segment_id = segment.get("id")
                    segment_name = segment.get(
                        "label", segment.get("name", f"ROI_{segment_id}")
                    )

                    if segment_id is not None:
                        ids.append(int(segment_id))
                        names.append(str(segment_name))
                elif isinstance(segment, (int, str)):
                    # Handle case where segments might be just IDs
                    try:
                        segment_id = int(segment)
                        ids.append(segment_id)
                        names.append(f"ROI_{segment_id}")
                    except ValueError:
                        logger.warning(f"Could not parse segment ID: {segment}")

            # Sort by ID to ensure consistent ordering
            if ids and names:
                sorted_pairs = sorted(zip(ids, names), key=lambda x: x[0])
                ids, names = zip(*sorted_pairs)
                return list(ids), list(names)

        return [], []

    def get_fullbrain_roi_data(self) -> Tuple[List[int], List[str]]:
        """
        Get fullbrain ROI IDs and names.

        Returns:
            Tuple of (roi_ids, roi_names)

        Raises:
            Exception: If fetching or parsing fails
        """
        if self._fullbrain_data is None:
            self._fullbrain_data = self._load_roi_data(
                self.fullbrain_roi_source, "fullbrain"
            )

        return self._fullbrain_data

    def get_vnc_roi_data(self) -> Tuple[List[int], List[str]]:
        """
        Get VNC ROI IDs and names.

        Returns:
            Tuple of (roi_ids, roi_names)

        Raises:
            Exception: If fetching or parsing fails
        """
        if self._vnc_data is None:
            self._vnc_data = self._load_roi_data(self.vnc_roi_source, "VNC")

        return self._vnc_data

    def get_all_roi_data(self) -> Dict[str, Any]:
        """
        Get all ROI data formatted for template use.

        Returns:
            Dictionary containing:
            - roi_ids: List of fullbrain ROI IDs
            - all_rois: List of fullbrain ROI names
            - vnc_ids: List of VNC ROI IDs
            - vnc_names: List of VNC ROI names
        """
        try:
            roi_ids, all_rois = self.get_fullbrain_roi_data()
            vnc_ids, vnc_names = self.get_vnc_roi_data()

            return {
                "roi_ids": roi_ids,
                "all_rois": all_rois,
                "vnc_ids": vnc_ids,
                "vnc_names": vnc_names,
            }
        except Exception as e:
            logger.error(f"Failed to get all ROI data: {e}")
            # Return empty data as fallback
            return {"roi_ids": [], "all_rois": [], "vnc_ids": [], "vnc_names": []}
