"""Tests for plant-room web moves (``play_go_to_processing_plant``, ``play_go_to_refinery``)."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase

from web.ui import views


class PlayGoToProcessingPlantViewTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.plant = SimpleNamespace(key="TestPlantRoom")
        self.refinery_chamber = SimpleNamespace(key="TestRefineryChamber")

    def _post(self):
        req = self.factory.post("/ui/play/go-to-processing-plant", data=b"{}", content_type="application/json")
        return req

    def test_anonymous_401(self):
        req = self._post()
        req.user = AnonymousUser()
        resp = views.play_go_to_processing_plant(req)
        self.assertEqual(resp.status_code, 401)

    def test_refinery_anonymous_401(self):
        req = self.factory.post("/ui/play/go-to-refinery", data=b"{}", content_type="application/json")
        req.user = AnonymousUser()
        resp = views.play_go_to_refinery(req)
        self.assertEqual(resp.status_code, 401)

    @patch("world.venue_resolve.processing_plant_room_for_venue")
    @patch("world.venues.venue_id_for_object")
    @patch.object(views, "_character_for_web_purchase")
    def test_move_to_plant(self, mock_char_pair, mock_vid, mock_plant_room):
        mock_vid.return_value = "nanomega_core"
        mock_plant_room.return_value = self.plant

        loc = SimpleNamespace(key="Hub")
        char = MagicMock()
        char.location = loc
        char.missions = MagicMock()
        char.quests = MagicMock()

        mock_char_pair.return_value = (char, None)

        req = self._post()
        req.user = MagicMock(is_authenticated=True)

        with patch.object(views, "_web_refresh_bundle", return_value={"dashboard": {}, "play": {}}):
            resp = views.play_go_to_processing_plant(req)

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(data.get("ok"))
        char.move_to.assert_called_once_with(self.plant)

    @patch("world.venue_resolve.refinery_room_for_venue")
    @patch("world.venues.venue_id_for_object")
    @patch.object(views, "_character_for_web_purchase")
    def test_refinery_route_moves_to_refinery_chamber(self, mock_char_pair, mock_vid, mock_refinery_room):
        mock_vid.return_value = "nanomega_core"
        mock_refinery_room.return_value = self.refinery_chamber

        loc = SimpleNamespace(key="Hub")
        char = MagicMock()
        char.location = loc
        char.missions = MagicMock()
        char.quests = MagicMock()

        mock_char_pair.return_value = (char, None)

        req = self.factory.post("/ui/play/go-to-refinery", data=b"{}", content_type="application/json")
        req.user = MagicMock(is_authenticated=True)

        with patch.object(views, "_web_refresh_bundle", return_value={"dashboard": {}, "play": {}}):
            resp = views.play_go_to_refinery(req)

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(data.get("ok"))
        char.move_to.assert_called_once_with(self.refinery_chamber)
