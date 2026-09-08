"""
Tests for ROIDataService.

The ROI endpoints are derived from the configured neuroglancer state template,
so these tests parse the real templates shipped in ``templates/`` and check
that the service picks up the mesh sources of the neuropil layers. No network
access is needed: fetching is mocked or never reached.
"""

import json
import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from neuview.services import roi_data_service as rds
from neuview.services.roi_data_service import ROIDataService

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
CNS_TEMPLATE = TEMPLATES_DIR / "neuroglancer-cns.js.jinja"
FAFB_TEMPLATE = TEMPLATES_DIR / "neuroglancer-fafb.js.jinja"


@pytest.mark.unit
class TestTemplateParsing:
    def test_cns_template_has_both_neuropil_layers(self):
        sources = rds.roi_sources_from_template(CNS_TEMPLATE)

        assert "brain-neuropils" in sources
        assert "vnc-neuropils" in sources
        for value in sources.values():
            assert value.startswith("gs://")
            assert not value.startswith("precomputed://")

    def test_cns_layer_sources_match_template_text(self):
        """The parsed value must be the literal URL written in the template."""
        text = CNS_TEMPLATE.read_text()
        sources = rds.roi_sources_from_template(CNS_TEMPLATE)

        for name in ("brain-neuropils", "vnc-neuropils"):
            assert f'"url": "precomputed://{sources[name]}"' in text

    def test_fafb_template_has_legacy_neuropils_layer_only(self):
        sources = rds.roi_sources_from_template(FAFB_TEMPLATE)

        assert "neuropils" in sources
        assert "brain-neuropils" not in sources
        assert not any(n in sources for n in rds.VNC_NEUROPIL_LAYERS)

    def test_unknown_variables_and_string_sources(self, tmp_path):
        template = tmp_path / "t.js.jinja"
        template.write_text(
            json.dumps(
                {
                    "title": "{{ website_title }}",
                    "extra": "{{ not_a_known_variable }}",
                    "layers": [
                        {
                            "type": "segmentation",
                            "source": "precomputed://gs://bucket/rois/roi-v9",
                            "name": "brain-neuropils",
                        },
                        {
                            "type": "segmentation",
                            "source": {"url": "precomputed://gs://bucket/vnc-v1"},
                            "name": "vnc-neuropils",
                        },
                        {
                            "type": "segmentation",
                            "source": "precomputed://https://example.org/x",
                            "name": "not-gcs",
                        },
                        {
                            "type": "image",
                            "source": "precomputed://gs://bucket/em",
                            "name": "em",
                        },
                    ],
                }
            )
        )

        sources = rds.roi_sources_from_template(template)

        assert sources == {
            "brain-neuropils": "gs://bucket/rois/roi-v9",
            "vnc-neuropils": "gs://bucket/vnc-v1",
        }


@pytest.mark.unit
class TestUrlHelpers:
    def test_segment_properties_url(self):
        assert (
            rds.segment_properties_url("gs://flyem-male-cns/rois/fullbrain-roi-v5")
            == "https://storage.googleapis.com/flyem-male-cns/rois/fullbrain-roi-v5/segment_properties/info"
        )

    def test_segment_properties_url_rejects_non_gcs(self):
        with pytest.raises(ValueError):
            rds.segment_properties_url("https://example.org/rois")

    def test_cache_filename_for(self):
        assert (
            rds.cache_filename_for("gs://flyem-male-cns/rois/fullbrain-roi-v5/")
            == "fullbrain-roi-v5.json"
        )

    def test_url_fragment_is_dropped(self):
        source = "gs://bucket/neuropils/mesh_v6#type=mesh"

        assert (
            rds.segment_properties_url(source)
            == "https://storage.googleapis.com/bucket/neuropils/mesh_v6/segment_properties/info"
        )
        assert rds.cache_filename_for(source) == "mesh_v6.json"


@pytest.mark.unit
class TestROIDataService:
    def test_urls_follow_cns_template(self, tmp_path):
        service = ROIDataService(output_dir=tmp_path, template_path=CNS_TEMPLATE)
        sources = rds.roi_sources_from_template(CNS_TEMPLATE)

        assert service.fullbrain_roi_url == rds.segment_properties_url(
            sources["brain-neuropils"]
        )
        assert service.vnc_roi_url == rds.segment_properties_url(
            sources["vnc-neuropils"]
        )

    def test_fafb_template_uses_legacy_layer_and_tolerates_404(self, tmp_path, caplog):
        """FAFB's mesh-only neuropils source has no segment properties."""
        service = ROIDataService(output_dir=tmp_path, template_path=FAFB_TEMPLATE)
        sources = rds.roi_sources_from_template(FAFB_TEMPLATE)

        response = Mock(status_code=404)
        response.raise_for_status.side_effect = rds.requests.HTTPError(
            "404 Client Error", response=response
        )
        with patch.object(rds.requests, "get", return_value=response) as get:
            with caplog.at_level(logging.ERROR, logger=rds.logger.name):
                data = service.get_all_roi_data()

        assert service.fullbrain_roi_url == rds.segment_properties_url(
            sources["neuropils"]
        )
        assert service.vnc_roi_url is None
        get.assert_called_once()
        assert data == {"roi_ids": [], "all_rois": [], "vnc_ids": [], "vnc_names": []}
        # A missing segment_properties file is expected, not an error.
        assert caplog.records == []

    def test_missing_template_yields_empty_data(self, tmp_path):
        service = ROIDataService(output_dir=tmp_path)

        assert service.get_all_roi_data() == {
            "roi_ids": [],
            "all_rois": [],
            "vnc_ids": [],
            "vnc_names": [],
        }

    def test_unreadable_template_is_tolerated(self, tmp_path):
        broken = tmp_path / "broken.js.jinja"
        broken.write_text("{ not json")

        service = ROIDataService(output_dir=tmp_path, template_path=broken)

        assert service.fullbrain_roi_url is None
        assert service.get_all_roi_data()["roi_ids"] == []

    def test_fetch_uses_template_derived_url_and_cache_name(self, tmp_path):
        service = ROIDataService(output_dir=tmp_path, template_path=CNS_TEMPLATE)
        sources = rds.roi_sources_from_template(CNS_TEMPLATE)
        seen = {}

        def fake_fetch(url, cache_filename):
            seen[cache_filename] = url
            return {
                "@type": "neuroglancer_segment_properties",
                "inline": {
                    "ids": ["7"],
                    "properties": [
                        {"id": "source", "type": "label", "values": ["ME(R)"]}
                    ],
                },
            }

        with patch.object(service, "_fetch_json_from_gcs", side_effect=fake_fetch):
            roi_ids, roi_names = service.get_fullbrain_roi_data()
            service.get_vnc_roi_data()

        brain = sources["brain-neuropils"]
        vnc = sources["vnc-neuropils"]
        assert seen[rds.cache_filename_for(brain)] == rds.segment_properties_url(brain)
        assert seen[rds.cache_filename_for(vnc)] == rds.segment_properties_url(vnc)
        assert roi_ids == [7]
        assert roi_names == ["ME(R)"]
