"""
Configuration management for neuView.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


@dataclass
class NeuPrintConfig:
    """NeuPrint server configuration."""

    server: str
    dataset: str
    token: Optional[str] = None


@dataclass
class OutputConfig:
    """Output configuration."""

    directory: str


@dataclass
class DiscoveryConfig:
    """Auto-discovery configuration for neuron types."""

    max_types: int = 10
    type_filter: Optional[str] = None
    exclude_types: list[str] = field(default_factory=list)
    include_only: list[str] = field(default_factory=list)
    randomize: bool = True


# Supported kinds of per-neuron download formats and the file extension the
# browser writes for each. ``swc`` is stored verbatim; ``ngmesh`` (Neuroglancer
# legacy single-resolution mesh, addressed by its ``<body_id>:0`` manifest) is
# converted to Wavefront OBJ in the browser.
DOWNLOAD_FORMAT_KINDS = {"swc": "swc", "ngmesh": "obj"}


@dataclass
class DownloadFormat:
    """One per-neuron file format offered in the "Download" dialog.

    ``url_template`` must contain the ``{body_id}`` placeholder. The host has to
    send CORS headers; for Google Cloud Storage that means the JSON API endpoint
    (``https://www.googleapis.com/storage/v1/b/<bucket>/o/<object>?alt=media``),
    not the plain ``storage.googleapis.com`` path. For ``kind: ngmesh`` the
    template addresses the mesh manifest (``...{body_id}:0``); fragment URLs are
    derived from it by replacing ``{body_id}:0`` with the fragment name.
    """

    key: str
    label: str
    url_template: str
    kind: str = "swc"

    def __post_init__(self):
        if not self.key or not str(self.key).strip():
            raise ValueError("download format needs a non-empty 'key'")
        self.key = str(self.key).strip()
        self.label = str(self.label or self.key).strip()
        self.url_template = str(self.url_template or "").strip()
        if "{body_id}" not in self.url_template:
            raise ValueError(
                f"download format '{self.key}': url_template must contain {{body_id}}"
            )
        if self.kind not in DOWNLOAD_FORMAT_KINDS:
            raise ValueError(
                f"download format '{self.key}': unknown kind '{self.kind}' "
                f"(expected one of {sorted(DOWNLOAD_FORMAT_KINDS)})"
            )

    @property
    def extension(self) -> str:
        return DOWNLOAD_FORMAT_KINDS[self.kind]

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "url_template": self.url_template,
            "kind": self.kind,
            "extension": self.extension,
        }


@dataclass
class NeuroglancerConfig:
    """Neuroglancer configuration."""

    base_url: str = "https://clio-ng.janelia.org/"
    template: str = "neuroglancer.js.jinja"
    # Per-neuron file formats offered by the "Download" link next to the
    # Neuroglancer view (see ``DownloadFormat``). Empty hides the link.
    download_formats: list = field(default_factory=list)

    def __post_init__(self):
        formats = []
        seen = set()
        for entry in self.download_formats or []:
            fmt = (
                entry if isinstance(entry, DownloadFormat) else DownloadFormat(**entry)
            )
            if fmt.key in seen:
                raise ValueError(f"duplicate download format key '{fmt.key}'")
            seen.add(fmt.key)
            formats.append(fmt)
        self.download_formats = formats


@dataclass
class HtmlConfig:
    """HTML generation configuration."""

    title_prefix: str = "Neuron Type Report"
    github_repo: Optional[str] = None
    youtube_channel: Optional[str] = None
    fathom_id: Optional[str] = None


@dataclass
class HideFeaturesConfig:
    """Per-dataset feature visibility.

    Lists name the features to *hide*; anything not listed stays visible, so a
    missing/empty list shows as much as possible. ``neuron`` hides sections of
    the neuron pages; ``list`` hides filters of the types list. See
    ``config/README.md`` for the valid keys. (The YAML key is ``list``; it is
    stored as ``list_`` to avoid shadowing the ``list`` builtin.)
    """

    neuron: list = field(default_factory=list)
    list_: list = field(default_factory=list)
    nav: list = field(default_factory=list)


@dataclass
class Config:
    """Main configuration class."""

    neuprint: NeuPrintConfig
    output: OutputConfig
    discovery: DiscoveryConfig
    neuroglancer: NeuroglancerConfig
    html: HtmlConfig
    hide_features: HideFeaturesConfig = field(default_factory=HideFeaturesConfig)

    @classmethod
    def load(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        # Load environment variables from .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)

        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file, "r") as f:
            data = yaml.safe_load(f)

        # Parse configuration sections
        neuprint_data = data["neuprint"].copy()

        # Override token from environment if available
        env_token = os.getenv("NEUPRINT_TOKEN")
        if env_token:
            neuprint_data["token"] = env_token

        neuprint_config = NeuPrintConfig(**neuprint_data)
        output_config = OutputConfig(**data["output"])
        discovery_config = DiscoveryConfig(**data.get("discovery", {}))
        neuroglancer_config = NeuroglancerConfig(**data.get("neuroglancer", {}))
        html_config = HtmlConfig(**data.get("html", {}))

        return cls(
            neuprint=neuprint_config,
            output=output_config,
            discovery=discovery_config,
            neuroglancer=neuroglancer_config,
            html=html_config,
            hide_features=cls._parse_hide_features(data),
        )

    @staticmethod
    def _parse_hide_features(data: dict) -> HideFeaturesConfig:
        """Parse the optional ``hide_features`` block (YAML key ``list`` -> ``list_``)."""
        hide = data.get("hide_features") or {}
        return HideFeaturesConfig(
            neuron=list(hide.get("neuron") or []),
            list_=list(hide.get("list") or []),
            nav=list(hide.get("nav") or []),
        )

    @classmethod
    def create_minimal_for_testing(cls) -> "Config":
        """Create minimal configuration for testing purposes."""
        neuprint_config = NeuPrintConfig(
            server="test.neuprint.janelia.org", dataset="test", token="test_token"
        )

        output_config = OutputConfig(directory="/tmp/test_output")

        discovery_config = DiscoveryConfig()
        html_config = HtmlConfig()

        return cls(
            neuprint=neuprint_config,
            output=output_config,
            discovery=discovery_config,
            neuroglancer=NeuroglancerConfig(),
            html=html_config,
        )

    @classmethod
    def create_default(cls) -> "Config":
        """Create default configuration."""
        neuprint_config = NeuPrintConfig(
            server="neuprint.janelia.org", dataset="hemibrain:v1.2.1"
        )

        output_config = OutputConfig(directory="output")

        discovery_config = DiscoveryConfig()
        html_config = HtmlConfig()

        return cls(
            neuprint=neuprint_config,
            output=output_config,
            discovery=discovery_config,
            neuroglancer=NeuroglancerConfig(),
            html=html_config,
        )

    @classmethod
    def from_file(cls, config_file: str) -> "Config":
        """Load configuration from file (alias for load method)."""
        return cls.load(config_file)

    @classmethod
    def from_dict(cls, config_dict: dict) -> "Config":
        """Create Config from dictionary."""
        # Initialize from dictionary
        neuprint_data = config_dict["neuprint"].copy()

        # Override token from environment if available
        env_token = os.getenv("NEUPRINT_TOKEN")
        if env_token:
            neuprint_data["token"] = env_token

        neuprint_config = NeuPrintConfig(**neuprint_data)
        output_config = OutputConfig(**config_dict["output"])
        discovery_config = DiscoveryConfig(**config_dict.get("discovery", {}))
        neuroglancer_config = NeuroglancerConfig(**config_dict.get("neuroglancer", {}))
        html_config = HtmlConfig(**config_dict.get("html", {}))
        return cls(
            neuprint=neuprint_config,
            output=output_config,
            discovery=discovery_config,
            neuroglancer=neuroglancer_config,
            html=html_config,
            hide_features=cls._parse_hide_features(config_dict),
        )
