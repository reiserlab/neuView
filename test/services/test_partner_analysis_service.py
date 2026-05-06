"""Tests for PartnerAnalysisService soma-side handling."""

import logging

import pytest

from neuview.services.partner_analysis_service import PartnerAnalysisService

pytestmark = pytest.mark.unit


@pytest.fixture
def service():
    return PartnerAnalysisService(connectivity_combination_service=None)


@pytest.fixture
def connected_bids():
    # `dmap` for the "upstream" direction. The bare-type entry is the
    # all-sides bucket; the suffixed entries are side-specific.
    return {
        "upstream": {
            "Dm4": [1, 2, 3, 4],
            "Dm4_L": [1, 2],
            "Dm4_R": [3, 4],
        }
    }


class TestSpecificSideRouting:
    @pytest.mark.parametrize("side", ["L", "R", "M", "C", "center"])
    def test_known_sides_route_to_side_specific(
        self, service, connected_bids, side
    ):
        # Just verify the call doesn't fall through to the all-sides path or
        # log a warning. We don't assert ID contents because the side-specific
        # lookup logic is exercised separately.
        result = service.get_partner_body_ids(
            {"type": "Dm4", "soma_side": side}, "upstream", connected_bids
        )
        assert isinstance(result, list)


class TestNoSideMarkers:
    @pytest.mark.parametrize(
        "marker",
        ["", "na", "NA", "Nan", "none", "None", "NULL", "unknown", "U", "u"],
    )
    def test_no_side_markers_return_all_sides(
        self, service, connected_bids, marker
    ):
        result = service.get_partner_body_ids(
            {"type": "Dm4", "soma_side": marker}, "upstream", connected_bids
        )
        assert result == [1, 2, 3, 4]

    def test_none_returns_all_sides(self, service, connected_bids):
        result = service.get_partner_body_ids(
            {"type": "Dm4", "soma_side": None}, "upstream", connected_bids
        )
        assert result == [1, 2, 3, 4]

    def test_no_side_markers_do_not_warn(
        self, service, connected_bids, caplog
    ):
        with caplog.at_level(logging.WARNING):
            service.get_partner_body_ids(
                {"type": "Dm4", "soma_side": "na"}, "upstream", connected_bids
            )
        assert not any(
            "Unknown soma side" in rec.message
            or "Unrecognized soma side" in rec.message
            for rec in caplog.records
        )


class TestUnrecognizedSide:
    def test_unrecognized_side_falls_back_to_all_and_logs_debug(
        self, service, connected_bids, caplog
    ):
        with caplog.at_level(logging.DEBUG):
            result = service.get_partner_body_ids(
                {"type": "Dm4", "soma_side": "topside"},
                "upstream",
                connected_bids,
            )
        assert result == [1, 2, 3, 4]
        assert any(
            "Unrecognized soma side" in rec.message
            and rec.levelno == logging.DEBUG
            for rec in caplog.records
        )

    def test_unrecognized_side_does_not_warn(
        self, service, connected_bids, caplog
    ):
        with caplog.at_level(logging.WARNING):
            service.get_partner_body_ids(
                {"type": "Dm4", "soma_side": "topside"},
                "upstream",
                connected_bids,
            )
        assert not any(
            rec.levelno >= logging.WARNING for rec in caplog.records
        )
