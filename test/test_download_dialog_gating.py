"""The neuron download link, dialog and scripts appear only with download formats.

Renders the real templates through the project's Jinja service. Filters that
the macros need but that come from runtime services are stubbed with identity
functions, because only the presence of the markup matters here.
"""

import re
from datetime import datetime
from types import SimpleNamespace

import pytest

from neuview.config import NeuroglancerConfig
from neuview.services.jinja_template_service import JinjaTemplateService
from neuview.utils import get_templates_dir

FORMATS = [
    {"key": "swc", "label": "SWC skeleton", "url_template": "x/{body_id}.swc"},
    {
        "key": "obj",
        "label": "OBJ mesh",
        "kind": "ngmesh",
        "url_template": "x/{body_id}:0",
    },
]

MARKERS = ("swc-download-link", "swc-download-dialog", "swc-url-input")


@pytest.fixture(scope="module")
def env():
    service = JinjaTemplateService(get_templates_dir())
    environment = service.setup_jinja_env({})
    templates_dir = get_templates_dir()
    used = set()
    for name in ("macros.html.jinja", "sections/neuroglancer.html.jinja"):
        used.update(
            re.findall(r"\|\s*([a-z_0-9]+)", (templates_dir / name).read_text())
        )
    for name in used:
        environment.filters.setdefault(name, lambda value, *args, **kwargs: value)
    return environment


def _config(formats):
    return SimpleNamespace(
        neuroglancer=NeuroglancerConfig(download_formats=formats),
        html=SimpleNamespace(github_repo=""),
        neuprint=SimpleNamespace(dataset="test"),
    )


def _features(neuroglancer_visible=True):
    return SimpleNamespace(
        neuron_visible=lambda key: neuroglancer_visible or key != "neuroglancer",
        nav_visible=lambda key: True,
    )


def _render_section(env, **context):
    return env.get_template("sections/neuroglancer.html.jinja").render(
        features=_features(), youtube_url=None, **context
    )


def test_section_shows_link_and_dialog_with_formats(env):
    html = _render_section(env, config=_config(FORMATS))
    for marker in MARKERS:
        assert marker in html
    assert html.count('name="swc-download-format"') == 2
    assert "SWC skeleton" in html and "OBJ mesh" in html


def test_section_has_no_download_markup_with_empty_formats(env):
    html = _render_section(env, config=_config([]))
    assert "swc-" not in html
    assert "neuroglancer-iframe" in html  # the viewer itself stays


def test_section_has_no_download_markup_without_config(env):
    html = _render_section(env)
    assert "swc-" not in html


def _render_scripts(env, formats, neuroglancer_visible=True):
    return env.get_template("sections/neuron_page_scripts.html.jinja").render(
        config=_config(formats),
        features=_features(neuroglancer_visible),
        is_neuron_page=True,
        git_version="test",
        generation_time=datetime(2026, 1, 1),
        website_title="t",
        visible_neurons=[],
        neuron_query="",
        visible_rois=[],
        type_region="",
        neuron_data=SimpleNamespace(type="T"),
        roi_summary=[],
        connectivity=SimpleNamespace(upstream=[], downstream=[]),
    )


def test_scripts_included_only_with_formats(env):
    with_formats = _render_scripts(env, FORMATS)
    assert "static/js/fflate.min.js" in with_formats
    assert "static/js/swc-download.js" in with_formats

    without = _render_scripts(env, [])
    assert "fflate" not in without
    assert "swc-download" not in without


def test_scripts_not_included_when_neuroglancer_hidden(env):
    hidden = _render_scripts(env, FORMATS, neuroglancer_visible=False)
    assert "fflate" not in hidden
    assert "swc-download" not in hidden
