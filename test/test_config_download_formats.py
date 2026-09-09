"""Tests for the optional ``neuroglancer.download_formats`` config block."""

import tempfile
from pathlib import Path

import pytest

from neuview.config import Config, DownloadFormat, NeuroglancerConfig


def _write_config(tmp: Path, neuroglancer_block: str) -> Path:
    cfg = tmp / "config.yaml"
    cfg.write_text(
        "neuprint:\n"
        '  server: "neuprint.janelia.org"\n'
        '  dataset: "male-cns:v1.0"\n'
        "output:\n"
        '  directory: "output"\n'
        f"{neuroglancer_block}"
    )
    return cfg


def test_download_formats_default_to_empty():
    assert NeuroglancerConfig().download_formats == []


def test_download_formats_loaded_from_yaml():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _write_config(
            Path(tmp),
            "neuroglancer:\n"
            '  base_url: "https://neuroglancer-demo.appspot.com/"\n'
            "  download_formats:\n"
            "    - key: swc\n"
            '      label: "SWC skeleton"\n'
            '      url_template: "https://example.org/swc/{body_id}.swc"\n'
            "    - key: obj\n"
            '      label: "OBJ mesh"\n'
            "      kind: ngmesh\n"
            '      url_template: "https://example.org/mesh/{body_id}:0"\n',
        )
        config = Config.load(str(cfg))
    formats = config.neuroglancer.download_formats
    assert [f.key for f in formats] == ["swc", "obj"]
    assert formats[0].kind == "swc" and formats[0].extension == "swc"
    assert formats[1].kind == "ngmesh" and formats[1].extension == "obj"
    assert formats[1].to_dict()["extension"] == "obj"


def test_download_formats_absent_from_yaml_is_empty():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _write_config(
            Path(tmp),
            'neuroglancer:\n  base_url: "https://clio-ng.janelia.org/"\n',
        )
        config = Config.load(str(cfg))
    assert config.neuroglancer.download_formats == []


def test_download_format_requires_body_id_placeholder():
    with pytest.raises(ValueError, match="body_id"):
        DownloadFormat(key="swc", label="x", url_template="https://example.org/all.swc")


def test_download_format_rejects_unknown_kind():
    with pytest.raises(ValueError, match="unknown kind"):
        DownloadFormat(key="x", label="x", url_template="{body_id}", kind="ply")


def test_duplicate_format_keys_are_rejected():
    entry = {"key": "swc", "label": "x", "url_template": "{body_id}"}
    with pytest.raises(ValueError, match="duplicate"):
        NeuroglancerConfig(download_formats=[entry, dict(entry)])
